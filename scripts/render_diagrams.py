#!/usr/bin/env python3
"""Render every Mermaid diagram in the README and the wiki pages to a dark-mode PNG.

GitHub's mobile app and some viewers show a Mermaid block as raw code, so every
diagram is a picture first, with its Mermaid source kept underneath in a
collapsed section. The pictures are dark (docs/diagrams-theme.json) so they read
the same in light and dark mode. The page is the source of truth; the PNG is
generated from it.

Each diagram in a page looks like this (the script wraps a bare block for you):

    ![alt text](images/NAME.png)

    <details>
    <summary>Diagram source (Mermaid)</summary>

    ```mermaid
    ...
    ```

    </details>

docs/diagrams.json records the SHA-256 of each diagram's source next to the
picture made from it, so --check fails when a diagram was edited and its picture
was not re-rendered.

Usage, from anywhere inside a clone:
  scripts/render_diagrams.py --check     offline; exit 1 on a bare block, a missing picture or a stale hash
  scripts/render_diagrams.py --write     wrap bare blocks, render what changed, update the manifest

--write needs Mermaid CLI (`mmdc`) and a Chromium: set MMDC to its path if it is not on PATH, and
PUPPETEER_CONFIG to a JSON file with {"executablePath": "...", "args": ["--no-sandbox"]} if it needs one.
Pillow shrinks the pictures (at most 2400 px wide, a 128-colour palette).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "diagrams.json"
THEME = ROOT / "docs" / "diagrams-theme.json"
MAX_WIDTH = 2400
SUMMARY = "<summary>Diagram source (Mermaid)</summary>"

WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n" + re.escape(SUMMARY) + r"\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
BARE = re.compile(r"```mermaid\n(?P<src>.*?)\n```", re.DOTALL)


def pages() -> list[Path]:
    return [ROOT / "README.md", *sorted((ROOT / "docs" / "wiki").glob("*.md"))]


def digest(src: str) -> str:
    return hashlib.sha256(src.encode()).hexdigest()


def slug(page: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "-", page.stem.lower()).strip("-")


def picture_dir(page: Path) -> str:
    return "docs/images" if page.name == "README.md" else "images"


def alt_for(src: str, heading: str) -> str:
    labels = re.findall(r'\["([^"\n]+)"\]|\["?([^\]"\n]+)"?\]|participant \w+ as ([^\n]+)', src)
    names = []
    for group in labels:
        text = next(g for g in group if g)
        text = re.sub(r"<br\s*/?>", " ", text).strip()
        if text and text not in names:
            names.append(text)
    kind = "Sequence diagram" if src.lstrip().startswith("sequenceDiagram") else "Diagram"
    body = "; ".join(names[:8])
    alt = f"{kind}, {heading}: {body}" if body else f"{kind}, {heading}"
    return alt[:220].replace("]", ")").replace("[", "(")


def key_for(page: Path) -> str:
    return page.relative_to(ROOT).as_posix()


def blocks(page: Path):
    """Yield (alt, relative path, source) for each wrapped diagram, and the count of bare ones."""
    text = page.read_text()
    wrapped = list(WRAPPED.finditer(text))
    stripped = WRAPPED.sub("", text)
    return wrapped, len(BARE.findall(stripped))


def check() -> list[str]:
    problems = []
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    seen = set()
    for page in pages():
        wrapped, bare = blocks(page)
        if bare:
            problems.append(f"{key_for(page)}: {bare} Mermaid block(s) with no picture above them; run scripts/render_diagrams.py --write")
        for m in wrapped:
            png = (page.parent / m["path"]).resolve()
            rel = png.relative_to(ROOT).as_posix() if ROOT in png.parents else m["path"]
            seen.add(rel)
            if not png.is_file():
                problems.append(f"{key_for(page)}: {m['path']} is missing")
            entry = manifest.get(rel)
            if not entry:
                problems.append(f"{key_for(page)}: {rel} is not in docs/diagrams.json")
            elif entry.get("sha256") != digest(m["src"]):
                problems.append(f"{key_for(page)}: the source of {rel} changed; re-render with --write")
    for rel in sorted(set(manifest) - seen):
        problems.append(f"docs/diagrams.json lists {rel}, which no page uses")
    return problems


def render(src: str, out: Path) -> None:
    from PIL import Image  # imported here: --check needs only the standard library

    mmdc = os.environ.get("MMDC", "mmdc")
    with tempfile.TemporaryDirectory() as tmp:
        mmd, raw = Path(tmp) / "d.mmd", Path(tmp) / "d.png"
        mmd.write_text(src + "\n")
        cmd = ["nice", "-n", "19", mmdc, "-c", str(THEME), "-t", "dark", "-b", "#0d1117", "-w", "1400", "-s", "2", "-i", str(mmd), "-o", str(raw)]
        if os.environ.get("PUPPETEER_CONFIG"):
            cmd += ["-p", os.environ["PUPPETEER_CONFIG"]]
        subprocess.run(cmd, check=True, capture_output=True)
        img = Image.open(raw).convert("RGB")
        if img.width > MAX_WIDTH:
            img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)), Image.LANCZOS)
        img = img.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, optimize=True)
    subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "strip_png_metadata.py"), str(out)], check=True, capture_output=True)


ANY = re.compile("(?P<w>" + WRAPPED.pattern + ")|```mermaid\\n(?P<bsrc>.*?)\\n```", re.DOTALL)


def wrap_bare(page: Path, text: str) -> str:
    """Put a picture above every bare Mermaid block; leave wrapped blocks as they are."""
    position = 0

    def one(m: re.Match) -> str:
        nonlocal position
        position += 1
        if m["w"]:
            return m["w"]
        heads = re.findall(r"^#{1,4} (.+)$", text[: m.start()], re.MULTILINE)
        heading = heads[-1] if heads else page.stem.replace("-", " ")
        name = f"{slug(page)}-diagram-{position}.png"
        alt = alt_for(m["bsrc"], heading)
        return f"![{alt}]({picture_dir(page)}/{name})\n\n<details>\n{SUMMARY}\n\n```mermaid\n{m['bsrc']}\n```\n\n</details>"

    return ANY.sub(one, text)


def write() -> None:
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    live = {}
    for page in pages():
        text = page.read_text()
        new = wrap_bare(page, text)
        if new != text:
            page.write_text(new)
        for m in WRAPPED.finditer(new):
            png = (page.parent / m["path"]).resolve()
            rel = png.relative_to(ROOT).as_posix()
            live[rel] = digest(m["src"])
            if not png.is_file() or manifest.get(rel, {}).get("sha256") != live[rel]:
                print(f"render {rel}")
                render(m["src"], png)
    MANIFEST.write_text(json.dumps({k: {"sha256": v} for k, v in sorted(live.items())}, indent=2) + "\n")


def main(argv: list[str]) -> int:
    if argv == ["--check"]:
        problems = check()
        for p in problems:
            print(p)
        return 1 if problems else 0
    if argv == ["--write"]:
        write()
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
