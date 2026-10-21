"""Every Markdown link with a #fragment must point at a heading that exists.

GitHub builds the fragment from the heading text: lower case, markup and punctuation
dropped, spaces to hyphens, repeats get -1, -2. Links inside code are ignored.
"""

import posixpath
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FENCE_LINE = re.compile(r"^\s*(```|~~~)")
LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\s]*)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
INLINE_CODE = re.compile(r"`[^`\n]*`")


def slug(heading: str) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # link text only
    text = text.replace("`", "")
    text = re.sub(r"[^\w\- ]", "", text.lower())
    return text.replace(" ", "-")


def strip_fences(text: str) -> list[tuple[int, str]]:
    out, in_fence = [], False
    for n, line in enumerate(text.split("\n"), start=1):
        if FENCE_LINE.match(line):
            in_fence = not in_fence
        elif not in_fence:
            out.append((n, line))
    return out


def anchors(text: str) -> set[str]:
    seen: dict[str, int] = {}
    found = set()
    for _, line in strip_fences(text):
        m = HEADING.match(line)
        if not m:
            continue
        base = slug(m.group(2))
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else f"{base}-{count}")
    return found


def broken_links(files: dict[str, str]) -> list[str]:
    """files maps repo-relative path to text; returns 'path:line: target' for each bad fragment."""
    table = {path: anchors(text) for path, text in files.items()}
    problems = []
    for path, text in files.items():
        for n, line in strip_fences(text):
            for m in LINK.finditer(INLINE_CODE.sub("", line)):
                target = m.group(1)
                if "#" not in target or re.match(r"[a-z][a-z0-9+.-]*:", target):
                    continue
                file_part, _, frag = target.partition("#")
                dest = path if not file_part else posixpath.normpath(posixpath.join(posixpath.dirname(path), file_part))
                if dest not in table or not frag:
                    continue
                if frag.lower() not in table[dest]:
                    problems.append(f"{path}:{n}: {target}")
    return problems


def repo_markdown() -> dict[str, str]:
    names = subprocess.run(["git", "-C", str(ROOT), "ls-files", "*.md"], capture_output=True, text=True, check=True).stdout.split()
    return {n: (ROOT / n).read_text(encoding="utf-8") for n in names}


def test_every_fragment_points_at_a_heading():
    files = repo_markdown()
    assert len(files) > 50
    assert not broken_links(files), "\n".join(broken_links(files))


def test_checker_catches_a_broken_fragment_and_accepts_a_good_one():
    files = {"a.md": "# Top\n\n## Security and threat modeling\n\n[x](#security-and-threat-modelling)\n[y](b.md#some-heading)\n",
             "b.md": "# Some heading\n"}
    assert broken_links(files) == ["a.md:5: #security-and-threat-modelling"]
    files["a.md"] = "## Security and threat modeling\n[x](#security-and-threat-modeling)\n[y](b.md#some-heading)\n"
    assert broken_links(files) == []


def test_checker_ignores_fences_and_handles_repeated_headings():
    files = {"a.md": "# A\n# A\n```\n# Fake\n```\n[1](#a) [2](#a-1) [3](#fake)\n"}
    assert broken_links(files) == ["a.md:6: #fake"]
