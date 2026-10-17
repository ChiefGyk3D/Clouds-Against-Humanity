"""Tests for scripts/threat_dragon_layout.py and the layout of the three models.

The committed models are generated from the layout script, so a position is a
number in that script and not a hand-drawn guess. These tests check the
geometry rules on the committed files themselves (no node overlaps another, the
gaps hold, every node sits inside the boundary box that claims it, labels are
short and sit on nothing) and that the files are exactly what the script writes.
"""

import importlib.util
import itertools
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "threat_dragon_layout.py"
MODEL_DIR = ROOT / "docs" / "threat-model"

spec = importlib.util.spec_from_file_location("threat_dragon_layout", SCRIPT)
layout_mod = importlib.util.module_from_spec(spec)
sys.modules["threat_dragon_layout"] = layout_mod
spec.loader.exec_module(layout_mod)

NAMES = sorted(layout_mod.LAYOUTS)


def load(name: str) -> dict:
    return json.loads((MODEL_DIR / name).read_text(encoding="utf-8"))


def parts(model):
    cs = layout_mod.cells(model)
    nodes = [c for c in cs if layout_mod.is_node(c)]
    boxes = [c for c in cs if layout_mod.is_box(c)]
    flows = [c for c in cs if c["shape"] == "flow"]
    return cs, nodes, boxes, flows


def test_every_model_in_the_directory_has_a_layout():
    on_disk = {p.name for p in MODEL_DIR.glob("*.threat-dragon.json")}
    assert on_disk == set(NAMES)


@pytest.mark.parametrize("name", NAMES)
class TestLayout:
    def test_committed_file_is_what_the_script_writes(self, name):
        model = load(name)
        regenerated = layout_mod.apply_layout(model, layout_mod.LAYOUTS[name])
        assert layout_mod.render(regenerated) == (MODEL_DIR / name).read_text(
            encoding="utf-8"
        )

    def test_no_geometry_violations(self, name):
        model = load(name)
        assert layout_mod.violations(model, layout_mod.LAYOUTS[name]) == []

    def test_no_two_nodes_overlap_and_gaps_hold(self, name):
        _, nodes, _, _ = parts(load(name))
        for i, a in enumerate(nodes):
            for b in nodes[i + 1 :]:
                ra, rb = layout_mod.node_rect(a), layout_mod.node_rect(b)
                assert not layout_mod.rects_overlap(ra, rb), (a["id"], b["id"])
                hgap = max(rb[0] - ra[2], ra[0] - rb[2])
                vgap = max(rb[1] - ra[3], ra[1] - rb[3])
                # two nodes are either a column apart or a row apart
                assert (
                    hgap >= layout_mod.MIN_COL_GAP or vgap >= layout_mod.MIN_ROW_GAP
                ), (
                    a["id"],
                    b["id"],
                    hgap,
                    vgap,
                )

    def test_columns_are_at_least_the_minimum_apart(self, name):
        _, nodes, _, _ = parts(load(name))
        centres = sorted({round(layout_mod.centre(n)[0]) for n in nodes})
        for left, right in itertools.pairwise(centres):
            assert right - left >= 300 + 300, (left, right)

    def test_every_node_lies_inside_its_declared_boundary_box(self, name):
        model = load(name)
        cs, nodes, boxes, _ = parts(model)
        by_id = {c["id"]: c for c in cs}
        declared = layout_mod.LAYOUTS[name]["boxes"]
        assert set(declared) == {b["id"] for b in boxes}
        for box_id, members in declared.items():
            assert members
            for m in members:
                assert layout_mod.inside(
                    layout_mod.node_rect(by_id[m]), layout_mod.node_rect(by_id[box_id])
                ), (m, box_id)
        # a node is in at most one box and no box swallows a stranger
        owner = {}
        for box_id, members in declared.items():
            for m in members:
                assert m not in owner, m
                owner[m] = box_id
        for box in boxes:
            for n in nodes:
                if owner.get(n["id"]) != box["id"]:
                    assert not layout_mod.rects_overlap(
                        layout_mod.node_rect(n), layout_mod.node_rect(box)
                    ), (n["id"], box["id"])

    def test_boundaries_are_boxes_not_curves(self, name):
        cs, _, boxes, _ = parts(load(name))
        assert boxes
        assert not [c for c in cs if c["shape"] == "trust-boundary-curve"]
        for box in boxes:
            assert box["data"]["isTrustBoundary"] is True
            assert box["data"]["type"] == "tm.BoundaryBox"
            assert box["attrs"]["label"]["text"] == box["data"]["name"]
            assert not box["data"].get("threats")

    def test_flow_labels_are_short_and_keep_the_long_wording(self, name):
        _, _, _, flows = parts(load(name))
        assert flows
        for flow in flows:
            label = flow["labels"][0]["attrs"]["label"]["text"]
            assert label == flow["data"]["name"]
            assert 1 <= len(label.split()) <= 4, (flow["id"], label)
            assert len(label) <= 28, (flow["id"], label)
            assert 0 < flow["labels"][0]["position"] < 1
        # the original wording moved into the description
        assert any("Full label:" in f["data"]["description"] for f in flows)

    def test_node_names_fit_their_shapes(self, name):
        # Threat Dragon v2.6.2 does not wrap a node's name, so a long one runs
        # past the shape; the wording lives in the description instead.
        _, nodes, _, _ = parts(load(name))
        for node in nodes:
            label = node["attrs"]["text"]["text"]
            assert label == node["data"]["name"]
            assert len(label) <= layout_mod.NODE_NAME_MAX, label

    def test_flows_avoid_nodes_labels_and_each_other(self, name):
        model = load(name)
        cs, nodes, _boxes, flows = parts(model)
        by_id = {c["id"]: c for c in cs}
        rects = {f["id"]: layout_mod.label_rect(f, by_id) for f in flows}
        for f in flows:
            pts = layout_mod.polyline(f, by_id)
            ends = {f["source"]["cell"], f["target"]["cell"]}
            for n in nodes:
                assert not layout_mod.rects_overlap(
                    rects[f["id"]], layout_mod.node_rect(n)
                ), (
                    f["id"],
                    n["id"],
                )
                if n["id"] not in ends:
                    for p, q in itertools.pairwise(pts):
                        assert not layout_mod.seg_hits_rect(
                            p, q, layout_mod.node_rect(n), layout_mod.NODE_MARGIN
                        ), (f["id"], n["id"])
        ids = sorted(rects)
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                assert not layout_mod.rects_overlap(rects[a], rects[b]), (a, b)

    def test_flows_that_share_two_nodes_are_fanned_out(self, name):
        _, _, _, flows = parts(load(name))
        seen: dict = {}
        for f in flows:
            key = tuple(sorted((f["source"]["cell"], f["target"]["cell"])))
            seen.setdefault(key, []).append(f)
        pairs = [group for group in seen.values() if len(group) > 1]
        for group in pairs:
            assert all(f["vertices"] for f in group), [f["id"] for f in group]
            starts = {json.dumps(f["vertices"]) for f in group}
            assert len(starts) == len(group)


def test_zones_run_left_to_right_in_the_pipeline_models():
    for name in (
        "clouds-against-humanity.threat-dragon.json",
        "clouds-against-humanity.attack.threat-dragon.json",
    ):
        nodes = {n["id"]: n for n in parts(load(name))[1]}
        x = {k: layout_mod.centre(v)[0] for k, v in nodes.items()}
        assert (
            x["node-contributor"]
            < x["node-gh_repo"]
            < x["node-sl_track"]
            < x["node-doppler"]
            < x["node-droplets"]
        )
        assert x["node-doppler"] == x["node-cloud_api"]
        assert x["node-twingate"] == x["node-droplets"]


def test_layout_script_check_passes_from_the_command_line():
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--check"],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_layout_check_fails_when_a_position_is_changed(tmp_path):
    for name in NAMES:
        (tmp_path / name).write_text(
            (MODEL_DIR / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    victim = tmp_path / NAMES[0]
    model = json.loads(victim.read_text(encoding="utf-8"))
    for cell in layout_mod.cells(model):
        if layout_mod.is_node(cell):
            cell["position"]["x"] += 7
            break
    victim.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--check", "--root", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 1
    assert "out of date" in result.stderr


def test_a_label_over_four_words_is_rejected():
    layout = json.loads(
        json.dumps(
            layout_mod.LAYOUTS["clouds-against-humanity.threat-dragon.json"],
            default=list,
        )
    )
    layout["nodes"] = {k: tuple(v) for k, v in layout["nodes"].items()}
    layout["vertices"] = {
        k: [tuple(p) for p in v] for k, v in layout["vertices"].items()
    }
    layout["labels"]["flow-f-tok"] = "one two three four five"
    with pytest.raises(AssertionError):
        layout_mod.apply_layout(
            load("clouds-against-humanity.threat-dragon.json"), layout
        )
