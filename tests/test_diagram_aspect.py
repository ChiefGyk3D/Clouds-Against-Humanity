"""No diagram picture is a tall, narrow strip.

GitHub shows a wiki picture at its native pixel width up to the column width, so a
picture taller than 1.6 times its width fills several screens with oversized text
(issue #280: three flowcharts rendered 2 to 4.7 times taller than wide). Lay such
a diagram out wide (flowchart LR, or subgraph rows) instead of raising the limit.
Only generated diagrams are checked: those listed in docs/diagrams.json.
"""

import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_RATIO = 1.6
# Diagram pictures allowed to exceed MAX_RATIO, each with a reason. Empty: none needed.
ALLOWLIST: dict[str, str] = {}
FIXED = (
    "docs/wiki/images/droplet-hardening-diagram-1.png",
    "docs/wiki/images/ci-tests-and-cost-gate-diagram-2.png",
    "docs/wiki/images/spacelift-diagram-1.png",
)


def png_size(path: Path) -> tuple[int, int]:
    """Width and height from the PNG IHDR chunk (standard library only; Pillow is not a test dependency)."""
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR", f"{path} is not a PNG"
    return struct.unpack(">II", head[16:24])


def ratio(rel: str) -> float:
    width, height = png_size(ROOT / rel)
    return height / width


def test_no_diagram_picture_is_taller_than_the_limit():
    manifest = json.loads((ROOT / "docs" / "diagrams.json").read_text())
    tall = {rel: round(ratio(rel), 2) for rel in manifest if rel not in ALLOWLIST and ratio(rel) > MAX_RATIO}
    assert not tall, f"diagram pictures taller than {MAX_RATIO} x their width (re-lay them out wide): {tall}"


def test_the_allowlist_names_only_live_pictures_and_gives_reasons():
    manifest = json.loads((ROOT / "docs" / "diagrams.json").read_text())
    for rel, reason in ALLOWLIST.items():
        assert rel in manifest and reason.strip()


def test_the_three_reported_diagrams_are_now_wide_enough():
    for rel in FIXED:
        assert ratio(rel) <= MAX_RATIO, rel


def test_the_reader_sees_a_tall_picture(tmp_path):
    ihdr = struct.pack(">II", 100, 200) + b"\x08\x02\x00\x00\x00"
    tall = tmp_path / "t.png"
    tall.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + ihdr)
    width, height = png_size(tall)
    assert height / width > MAX_RATIO
