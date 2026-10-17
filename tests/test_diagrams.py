"""Every Mermaid diagram has a dark-mode picture made from its current source.

scripts/render_diagrams.py --check is the rule; these tests run it on the tree
and prove it fails on a bare block, a stale source and a stray manifest entry.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("render_diagrams", ROOT / "scripts" / "render_diagrams.py")
rd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rd)

SRC = "flowchart LR\n    a[\"One\"] --> b[\"Two\"]"
WRAPPED = f"![Diagram, test: One; Two](images/x.png)\n\n<details>\n{rd.SUMMARY}\n\n```mermaid\n{SRC}\n```\n\n</details>\n"


def fixture(tmp_path, monkeypatch, page_text, manifest, make_png=True):
    (tmp_path / "docs" / "wiki" / "images").mkdir(parents=True)
    (tmp_path / "README.md").write_text("# r\n")
    (tmp_path / "docs" / "wiki" / "P.md").write_text(page_text)
    if make_png:
        (tmp_path / "docs" / "wiki" / "images" / "x.png").write_bytes(b"png")
    (tmp_path / "docs" / "diagrams.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(rd, "ROOT", tmp_path)
    monkeypatch.setattr(rd, "MANIFEST", tmp_path / "docs" / "diagrams.json")


def test_the_tree_has_no_bare_stale_or_missing_diagrams():
    assert rd.check() == []


def test_a_wrapped_diagram_with_a_matching_hash_passes(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch, WRAPPED, {"docs/wiki/images/x.png": {"sha256": rd.digest(SRC)}})
    assert rd.check() == []


def test_a_bare_block_fails(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch, f"```mermaid\n{SRC}\n```\n", {})
    assert any("no picture" in p for p in rd.check())


def test_an_edited_source_fails_until_re_rendered(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch, WRAPPED, {"docs/wiki/images/x.png": {"sha256": "0" * 64}})
    assert any("changed" in p for p in rd.check())


def test_a_missing_picture_fails(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch, WRAPPED, {"docs/wiki/images/x.png": {"sha256": rd.digest(SRC)}}, make_png=False)
    assert any("missing" in p for p in rd.check())


def test_a_manifest_entry_no_page_uses_fails(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch, "no diagrams\n", {"docs/wiki/images/old.png": {"sha256": "0" * 64}})
    assert any("no page uses" in p for p in rd.check())


def test_wrapping_adds_a_picture_above_a_bare_block_and_leaves_a_wrapped_one(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch, "## Heading\n\n" + f"```mermaid\n{SRC}\n```\n\n" + WRAPPED, {})
    page = tmp_path / "docs" / "wiki" / "P.md"
    out = rd.wrap_bare(page, page.read_text())
    assert out.count("<details>") == 2
    assert "![Diagram, Heading: One; Two](images/p-diagram-1.png)" in out
    assert out.endswith(WRAPPED)
