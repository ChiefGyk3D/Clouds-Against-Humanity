"""Checks for the pictures in docs/wiki/images/ and the pages that use them.

The rules are in docs/wiki/Screenshots-Policy.md: PNG only, every referenced
image exists and is local, every image is used, alt text says something, files
are small, narrow, regular files (never symlinks) and carry only allowlisted
PNG chunks, and a placeholder callout for a console we cannot capture has its
parts. The checks are functions so the tests can also prove they fail on
hostile fixtures, not just pass on today's tree.
"""

import importlib.util
import re
import struct
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
IMAGES = WIKI / "images"
MAX_BYTES = 600 * 1024
MAX_WIDTH = 2400
MIN_ALT = 10

_spec = importlib.util.spec_from_file_location("strip_png_metadata", ROOT / "scripts" / "strip_png_metadata.py")
stripper = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stripper)

FENCE = re.compile(r"^[ ]*(```|~~~).*?^[ ]*\1[^\n]*$", re.MULTILINE | re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
STRICT_IMAGE = re.compile(r"!\[([^\]\n]*)\]\(images/([a-z0-9]+(?:-[a-z0-9]+)*\.png)\)")
RAW_HTML_MEDIA = re.compile(r"<\s*/?\s*(img|picture|source|video|audio|iframe|object|embed|svg|image)\b", re.IGNORECASE)
REFERENCE_IMAGE = re.compile(r"!\[[^\]\n]*\]\s?\[[^\]\n]*\]")
WIKI_IMAGE_SYNTAX = re.compile(r"\[\[[^\]\n]*\.(png|jpe?g|gif|svg|webp)[^\]\n]*\]\]", re.IGNORECASE)
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\.png")


def prose(text: str) -> str:
    """Page text with fenced blocks and inline code removed, so examples are not counted."""
    return INLINE_CODE.sub("", FENCE.sub("", text))


def page_problems(page: str, text: str) -> list[str]:
    """Policy problems in one page's Markdown: anything but a local, named, described PNG."""
    body = prose(text)
    problems = []
    if RAW_HTML_MEDIA.search(body):
        problems.append(f"{page}: raw HTML media tag; use Markdown image syntax")
    if REFERENCE_IMAGE.search(body):
        problems.append(f"{page}: reference-style image; use ![alt](images/name.png)")
    if WIKI_IMAGE_SYNTAX.search(body):
        problems.append(f"{page}: wiki [[image]] syntax; use Markdown image syntax")
    for m in re.finditer(r"!\[", body):
        ok = STRICT_IMAGE.match(body, m.start())
        if not ok:
            problems.append(f"{page}: image not of the form ![alt](images/lowercase-name.png): {body[m.start():m.start() + 60]!r}")
        elif len(ok.group(1).strip()) < MIN_ALT:
            problems.append(f"{page}: alt text {ok.group(1)!r} is shorter than {MIN_ALT} characters")
    return problems


def referenced(text: str) -> set[str]:
    return {m.group(2) for m in STRICT_IMAGE.finditer(prose(text))}


def png_problems(path: Path) -> list[str]:
    """Problems with one committed image file."""
    name = path.name
    if path.is_symlink():
        return [f"{name}: is a symlink"]
    if not path.is_file():
        return [f"{name}: not a regular file"]
    problems = []
    if not NAME.fullmatch(name):
        problems.append(f"{name}: must be lowercase-dash-name.png (PNG only)")
    size = path.stat().st_size
    if size > MAX_BYTES:
        problems.append(f"{name}: {size} bytes is over {MAX_BYTES}")
    data = path.read_bytes()
    try:
        kinds = stripper.chunk_types(data)
    except stripper.PngError as err:
        return problems + [f"{name}: {err}"]
    extra = sorted({k.decode("latin-1") for k in kinds} - {k.decode() for k in stripper.KEEP})
    if extra:
        problems.append(f"{name}: chunks outside the allowlist {extra}: run scripts/strip_png_metadata.py")
    width = struct.unpack(">I", data[16:20])[0]
    if width > MAX_WIDTH:
        problems.append(f"{name}: {width}px wide is over {MAX_WIDTH}")
    return problems


def image_entries() -> list[Path]:
    return sorted(IMAGES.iterdir())


# -- the real tree ---------------------------------------------------------


def test_there_are_images_and_the_directory_is_not_a_symlink():
    assert not IMAGES.is_symlink()
    assert image_entries()


def test_every_page_follows_the_image_rules_and_references_resolve():
    problems = []
    for page in sorted(WIKI.glob("*.md")):
        text = page.read_text()
        problems += page_problems(page.name, text)
        for name in referenced(text):
            if not (IMAGES / name).is_file():
                problems.append(f"{page.name}: images/{name} does not exist")
    assert not problems, problems


def test_every_image_file_is_referenced():
    used = set()
    for page in WIKI.glob("*.md"):
        used |= referenced(page.read_text())
    unused = [p.name for p in image_entries() if p.name not in used]
    assert not unused, f"in docs/wiki/images/ but on no page: {unused}"


@pytest.mark.parametrize("path", image_entries(), ids=lambda p: p.name)
def test_image_file_rules(path):
    assert not png_problems(path)


def test_placeholders_exist_on_the_vendor_console_pages():
    pages = {p for p, _ in callouts()}
    expected = {
        "Spacelift.md",
        "Doppler-and-Secrets.md",
        "Twingate.md",
        "DigitalOcean-Network-and-Firewalls.md",
        "Provider-AWS-Account-Preparation.md",
        "Build-It-From-Zero-Accounts-to-Stage-1.md",
    }
    assert expected <= pages, f"missing placeholders on {sorted(expected - pages)}"


def callouts() -> list[tuple[str, str]]:
    """Every 'Screenshot to take yourself' blockquote outside code fences, with its page."""
    found = []
    for page in sorted(WIKI.glob("*.md")):
        text = FENCE.sub("", page.read_text())
        block = None
        for line in text.splitlines() + [""]:
            if line.startswith("> **Screenshot to take yourself:**"):
                block = [line]
            elif block is not None and line.startswith(">"):
                block.append(line)
            elif block is not None:
                found.append((page.name, "\n".join(block)))
                block = None
    return found


def test_every_placeholder_has_capture_look_for_and_redact():
    problems = []
    for page, block in callouts():
        lines = [ln.lstrip("> ").strip() for ln in block.splitlines()]
        headline = lines[0].removeprefix("**Screenshot to take yourself:**").strip()
        if len(headline) < 15:
            problems.append(f"{page}: no description of which screen")
        for label in ("Capture:", "Look for:", "Redact:"):
            body = [ln for ln in lines[1:] if ln.startswith(label)]
            if len(body) != 1 or len(body[0]) < len(label) + 15:
                problems.append(f"{page}: needs one substantial '{label}' line")
    assert not problems, problems


def test_policy_page_is_linked_from_sidebar_and_reading_order():
    for name in ("_Sidebar.md", "Reading-Order.md"):
        assert "(Screenshots-Policy.md)" in (WIKI / name).read_text(), name


def test_policy_page_carries_the_manual_review_checklist():
    text = (WIKI / "Screenshots-Policy.md").read_text().lower()
    for item in (
        "address bar", "query string", "tenant", "project name", "username", "avatar",
        "tabs", "bookmarks", "extensions", "local path", "hostname", "account id",
        "email", "ip address", "token", "notification",
    ):
        assert item in text, f"policy checklist lacks {item!r}"


# -- the checks themselves, on hostile fixtures ----------------------------


@pytest.mark.parametrize(
    "text",
    [
        '<img src="https://tracker.example/pixel?id=u">',
        '<IMG SRC="images/a.png">',
        "<picture><source srcset='x'></picture>",
        "![apparently safe diagram][track]\n\n[track]: https://tracker.example/pixel.png",
        "![collapsed reference][]",
        "![a remote picture here](https://tracker.example/p.png)",
        "![a data uri picture](data:image/png;base64,AAAA)",
        "![a spaced target picture](<images/a b.png>)",
        "![an uppercase target here](images/A.png)",
        "![alt text here](images/a.png 'a title')",
        "![alt text here](images/sub/a.png)",
        "![short](images/a.png)",
        "[[picture.png]]",
    ],
)
def test_page_checks_reject_hostile_markdown(text):
    assert page_problems("X.md", text), text


def test_page_checks_ignore_examples_in_code_and_accept_a_good_image():
    good = "![a clear description](images/a-b.png)"
    assert not page_problems("X.md", good)
    assert referenced(good) == {"a-b.png"}
    example = "```markdown\n<img src='x'>\n![bad](https://x/y.png)\n```\n\nUse `<img>` and `![a][b]` never.\n\n~~~\n![bad](http://x)\n~~~\n"
    assert not page_problems("X.md", example)


def test_png_checks_reject_symlinks_bad_names_metadata_and_wide_files(tmp_path):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    def png(width=1, extra=b""):
        ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, 1, 8, 2, 0, 0, 0))
        idat = chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
        return stripper.SIGNATURE + ihdr + extra + idat + chunk(b"IEND", b"")

    ok = tmp_path / "ok-image.png"
    ok.write_bytes(png())
    assert not png_problems(ok)

    link = tmp_path / "link.png"
    link.symlink_to(ok)
    assert png_problems(link) == ["link.png: is a symlink"]

    bad_name = tmp_path / "Bad_Name.png"
    bad_name.write_bytes(png())
    assert any("lowercase" in p for p in png_problems(bad_name))

    for kind in (b"tEXt", b"prIv", b"iCCP", b"bKGD"):
        f = tmp_path / "meta.png"
        f.write_bytes(png(extra=chunk(kind, b"secret\x00value")))
        assert any("allowlist" in p for p in png_problems(f)), kind

    wide = tmp_path / "wide.png"
    wide.write_bytes(png(width=MAX_WIDTH + 1))
    assert any("wide" in p for p in png_problems(wide))

    big = tmp_path / "big.png"
    big.write_bytes(png(extra=chunk(b"IDAT", b"\x00" * (MAX_BYTES + 1))))
    assert any("bytes" in p for p in png_problems(big))

    jpeg = tmp_path / "photo.jpg"
    jpeg.write_bytes(b"\xff\xd8\xff\xe1")
    assert png_problems(jpeg)

    broken = tmp_path / "broken.png"
    broken.write_bytes(png()[:-5])
    assert any("IEND" in p or "truncated" in p for p in png_problems(broken))
