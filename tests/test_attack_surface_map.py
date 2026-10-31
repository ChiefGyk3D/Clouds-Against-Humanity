"""The attack surface map page: its layers are complete and every file it cites exists.

docs/wiki/Attack-Surface-Map-Layer-by-Layer.md cites repository files, and tests or OpenTofu run blocks
by name (path::name), as the evidence for each row. A cited file that does not exist, or a cited name that
is not in it, teaches the wrong thing.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Attack-Surface-Map-Layer-by-Layer"
PAGE = WIKI / f"{NAME}.md"
LAYERS = [
    "Layer 1: the cloud account",
    "Layer 2: Spacelift and CI",
    "Layer 3: Doppler",
    "Layer 4: Twingate",
    "Layer 5: the droplets",
    "Layer 6: telemetry",
    "Layer 7: the edge",
    "Layer 8: the web tier",
]
CITE = re.compile(r"`((?:stacks|modules|scripts|tests|labs|docs|\.spacelift|\.github)/[A-Za-z0-9_./-]+?)(?:::([A-Za-z0-9_]+))?`")
HEADER = "| What an attacker could aim at |"


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def layer_rows(body: str) -> dict[str, list[list[str]]]:
    """Map each layer heading to its table rows, split into cells."""
    out: dict[str, list[list[str]]] = {}
    current = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = []
        elif current and line.startswith("|") and not line.startswith(HEADER) and not re.match(r"\|[-| ]+\|$", line):
            out[current].append([c.strip() for c in line.strip().strip("|").split("|")])
    return out


def row_problems(cells: list[str], root: Path = ROOT) -> list[str]:
    """What is wrong with one row: not five cells, a blank cell, or a bad citation."""
    if len(cells) != 5:
        return [f"{len(cells)} cells, expected 5"]
    problems = [f"blank cell {i}" for i, c in enumerate(cells) if not c]
    cites = CITE.findall(cells[4])
    if not cites:
        problems.append("the Where cell cites no repository file")
    if not (cells[2].startswith("None") or CITE.search(cells[2])):
        problems.append("the test cell names no test and does not start with None")
    for cell in cells:
        for path, name in CITE.findall(cell):
            target = root / path
            if not target.exists():
                problems.append(f"missing: {path}")
            elif name and name not in target.read_text(encoding="utf-8", errors="replace"):
                problems.append(f"{path} has no {name}")
    return problems


def test_all_eight_layers_are_present_in_order():
    headings = [h for h in layer_rows(text()) if h.startswith("Layer ")]
    assert headings == LAYERS


def test_every_layer_has_rows_and_every_row_is_complete_and_cited():
    rows = layer_rows(text())
    total = 0
    for layer in LAYERS:
        assert rows[layer], f"{layer} has no rows"
        for cells in rows[layer]:
            total += 1
            assert not row_problems(cells), (layer, cells[0][:50], row_problems(cells))
    assert total >= 25, "the guard collected too few rows"


def test_every_citation_anywhere_on_the_page_exists():
    cited = sorted(set(CITE.findall(text())))
    assert len(cited) >= 40, "the guard collected too little"
    bad = [(p, n) for p, n in cited if not (ROOT / p).exists() or (n and n not in (ROOT / p).read_text(encoding="utf-8", errors="replace"))]
    assert not bad, bad


def test_the_guard_bites_on_a_bad_row():
    good = ["aim", "control", "`tests/test_attack_surface_map.py`", "log", "`tests/test_attack_surface_map.py`"]
    assert row_problems(good) == []
    assert row_problems(good[:4])
    assert row_problems(["aim", "", good[2], "log", good[4]])
    assert row_problems(good[:4] + ["`tests/no_such_file.py`"])
    assert row_problems(good[:4] + ["`tests/test_ipv6_closed.py::no_such_test_name_xyz`"])
    assert row_problems(good[:2] + ["it is tested somewhere"] + good[3:])
    assert row_problems(["aim", "control", "None. A setting.", "log", "no citation"])


def test_the_page_states_its_limits():
    body = text()
    assert "built but off by default" in body
    assert "None" in body and "recommendation" in body.lower()
    assert "unverified" in body.lower()


def test_the_page_uses_no_real_address():
    for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text()):
        assert ip == "169.254.169.254", ip


def test_the_page_is_registered_everywhere_pages_are():
    for name in ("Contents.md", "Reading-Order.md", "Glossary.md", "_nav.yaml"):
        assert NAME in (WIKI / name).read_text(encoding="utf-8"), name
