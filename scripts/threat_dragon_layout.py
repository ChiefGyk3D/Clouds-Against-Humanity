#!/usr/bin/env python3
"""Deterministic layout for the Threat Dragon models in docs/threat-model/.

Threat Dragon stores a position and a size for every cell, and a list of
vertices for every flow. Hand-placed values drift as people edit, and a model
that renders as a pile of overlapping labels teaches nothing. This script owns
the geometry: nodes sit in columns by trust zone, each trust boundary is a box
around the nodes it protects, every flow label is at most four words (the full
wording lives in the flow's description), and flows that would cross a node are
routed around it with vertices.

    python3 scripts/threat_dragon_layout.py            # rewrite the models
    python3 scripts/threat_dragon_layout.py --check    # fail if a file differs

A layout is data (LAYOUTS below), so a change of position is a diff of numbers,
not of a drawing. The geometry rules (no overlapping nodes, minimum gaps, nodes
inside their boundary box, no label on a node) are checked by `violations`,
which the tests call as well. The script never reads the network.

Threat Dragon draws a trust boundary box as shape `trust-boundary-box`, a
dashed rectangle whose caption sits at the top (verified in the v2.6.2 source,
td.vue/src/service/x6/shapes/trust-boundary-box.js).
"""

from __future__ import annotations

import argparse
import copy
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "docs" / "threat-model"

COL_PITCH = 600
ROW_PITCH = 340
X0 = 170
VERTEX_X_SHIFT = X0 - 140  # vertices below were authored for X0 = 140
Y0 = 200
SIZES = {"actor": (300, 80), "store": (260, 80), "process": (180, 110)}
BOX_PAD_X = 50
BOX_PAD_TOP = 75
BOX_PAD_BOTTOM = 45
BOX_MIN_W = 440
LABEL_MAX_WORDS = 4
CHAR_W = 6.6
LABEL_H = 20
MIN_COL_GAP = 300
MIN_ROW_GAP = 160
NODE_MARGIN = 8

BOX_STROKE = "#b45309"

# Threat Dragon v2.6.2 draws a node's name on one line and does not wrap it, so
# a long name runs past its shape. Node names stay at about 24 characters; the
# full wording moves to the node's description.
NODE_NAMES = {
    "node-contributor": "Contributor (A2)",
    "node-upstream": "Upstream publishers",
    "node-reviewer": "Hosted AI reviewer",
    "node-local": "Local LLM",
    "store-a-repo": "Repository content",
    "store-a-agentcfg": "Agent config",
    "store-a-secrets": "Secrets (Doppler)",
    "node-maintainer": "Maintainer (A3/A4)",
    "node-gh_repo": "Source repo",
    "node-sl_prop": "Spacelift proposed run",
    "node-sl_track": "Spacelift tracked run",
    "node-state": "OpenTofu state",
    "node-twingate": "Twingate",
    "node-droplets": "Connector droplets",
    "node-resources": "Protected resources",
}
NODE_NAME_MAX = 24


def at(col: float, row: float) -> tuple[float, float]:
    """Centre of a grid cell."""
    return (X0 + COL_PITCH * col, Y0 + ROW_PITCH * row)


# --- the layouts -------------------------------------------------------------

PIPELINE = {
    # node id -> (column, row). Columns run left to right by trust zone:
    # outside parties, GitHub, Spacelift, secrets and the cloud API, the cloud.
    "nodes": {
        "node-contributor": (0, 1),
        "node-upstream": (0, 2),
        "node-maintainer": (0, 3),
        "node-scanner": (0, 4),
        "node-ci": (1, 0),
        "node-gh_repo": (1, 1),
        "node-sl_prop": (2, 0),
        "node-sl_track": (2, 2),
        "node-state": (2, 3),
        "node-doppler": (3, 1),
        "node-cloud_api": (3, 3),
        "node-twingate": (4, 1),
        "node-droplets": (4, 3),
        "node-resources": (4, 4),
    },
    # boundary id -> the nodes the box encloses
    "boxes": {
        "boundary-B1": ["node-droplets", "node-resources"],
        "boundary-B2": ["node-ci"],
        "boundary-B3": ["node-sl_prop"],
        "boundary-B4": ["node-gh_repo"],
        "boundary-B5": ["node-sl_track", "node-state"],
        "boundary-B6": ["node-doppler"],
        "boundary-B7": ["node-cloud_api"],
        "boundary-B8": ["node-twingate"],
    },
    # flow id -> short label (at most four words)
    "labels": {
        "flow-f-scan": "Blocked inbound traffic",
        "flow-f-pr": "Fork pull request",
        "flow-f-ci": "PR code checkout",
        "flow-f-ci-status": "CI status check",
        "flow-f-up-ci": "Action refs by SHA",
        "flow-f-merge": "Review and merge",
        "flow-f-push-prop": "PR push event",
        "flow-f-push-track": "Merged commit",
        "flow-f-up-doppler-cli": "Doppler CLI download",
        "flow-f-tok": "Service token read",
        "flow-f-sec": "Secrets returned",
        "flow-f-state": "State and tokens",
        "flow-f-plan": "Plan for review",
        "flow-f-confirm": "Human confirms apply",
        "flow-f-apply": "Apply with cloud token",
        "flow-f-userdata": "Create droplet",
        "flow-f-tg-api": "Twingate API call",
        "flow-f-login": "IdP sign-in",
        "flow-f-connector-link": "Outbound connector link",
        "flow-f-session": "Relayed session",
        "flow-f-ssh": "SSH to resource",
        "flow-f-up-apt": "Signed apt packages",
    },
    # flow id -> vertices in canvas pixels. A flow with none is drawn straight,
    # or fanned out when it shares its two nodes with another flow.
    "vertices": {
        "flow-f-up-ci": [(400, 880), (400, 200)],
        "flow-f-login": [(140, 1420), (2240, 1420), (2240, 540)],
        "flow-f-scan": [(2100, 1560)],
        "flow-f-up-apt": [(330, 880), (330, 1480), (2160, 1480)],
    },
    # flow id -> position of its label along the path (default 0.5)
    "label_at": {
        "flow-f-up-ci": 0.35,
        "flow-f-login": 0.35,
        "flow-f-scan": 0.4,
        "flow-f-connector-link": 0.3,
        "flow-f-session": 0.3,
    },
}

ATLAS = {
    "nodes": {
        "node-contributor": (0, 0),
        "node-upstream": (0, 2),
        "node-maintainer": (0, 3),
        "node-ci": (1, 0),
        "store-a-repo": (1, 1),
        "node-local": (2, 1),
        "node-agent": (2, 2),
        "store-a-agentcfg": (2, 3),
        "node-reviewer": (3, 0),
        "node-hosted": (3, 2),
        "store-a-secrets": (4, 3),
    },
    "boxes": {
        "boundary-AB1": ["node-ci", "store-a-repo"],
        "boundary-AB2": ["store-a-agentcfg", "node-agent"],
        "boundary-AB3": ["node-hosted", "node-reviewer"],
        "boundary-AB4": ["store-a-secrets"],
        "boundary-AB5": ["node-maintainer"],
    },
    "labels": {
        "flow-a-text": "Untrusted text",
        "flow-a-ctx": "Files into context",
        "flow-a-task": "Task and approvals",
        "flow-a-cfg": "Tool allow-list",
        "flow-a-prompt": "Prompt and context",
        "flow-a-out": "Output and tool calls",
        "flow-a-push": "Agent opens PR",
        "flow-a-secrets": "Visible secrets",
        "flow-a-web": "Fetched web content",
        "flow-a-dep": "Dependency added",
        "flow-a-diff": "Diff for review",
        "flow-a-review": "Advisory review",
        "flow-a-local": "Text for summary",
        "flow-a-summary": "Summary text",
        "flow-a-ci": "PR code checkout",
        "flow-a-merge": "Review and merge",
    },
    "vertices": {
        "flow-a-review": [(1560, 680), (500, 680)],
        "flow-a-secrets": [(1970, 1100)],
    },
    "label_at": {"flow-a-web": 0.7, "flow-a-summary": 0.3},
}

LAYOUTS = {
    "clouds-against-humanity.threat-dragon.json": PIPELINE,
    "clouds-against-humanity.attack.threat-dragon.json": PIPELINE,
    "clouds-against-humanity.atlas.threat-dragon.json": ATLAS,
}


# --- applying a layout -------------------------------------------------------


def cells(model: dict) -> list:
    return model["detail"]["diagrams"][0]["cells"]


def node_rect(cell: dict) -> tuple[float, float, float, float]:
    p, s = cell["position"], cell["size"]
    return (p["x"], p["y"], p["x"] + s["width"], p["y"] + s["height"])


def is_node(cell: dict) -> bool:
    return cell["shape"] in SIZES


def is_box(cell: dict) -> bool:
    return cell["shape"] == "trust-boundary-box"


def box_cell(old: dict, rect: tuple[float, float, float, float], z: int) -> dict:
    name = old["data"]["name"]
    return {
        "position": {"x": rect[0], "y": rect[1]},
        "size": {"width": rect[2] - rect[0], "height": rect[3] - rect[1]},
        "attrs": {
            "body": {
                "stroke": BOX_STROKE,
                "strokeWidth": 3,
                "strokeDasharray": "10 5",
                "fill": "transparent",
                "fillOpacity": 0,
            },
            "label": {"text": name, "refX": 20, "refY": 14, "fontSize": 14},
        },
        "shape": "trust-boundary-box",
        "zIndex": z,
        "id": old["id"],
        "data": {
            "type": "tm.BoundaryBox",
            "name": name,
            "description": old["data"]["description"],
            "isTrustBoundary": True,
            "hasOpenThreats": False,
        },
    }


def apply_layout(model: dict, layout: dict) -> dict:
    model = copy.deepcopy(model)
    all_cells = cells(model)
    by_id = {c["id"]: c for c in all_cells}
    for ident, (col, row) in layout["nodes"].items():
        c = by_id[ident]
        w, h = SIZES[c["shape"]]
        cx, cy = at(col, row)
        c["position"] = {"x": cx - w / 2, "y": cy - h / 2}
        c["size"] = {"width": w, "height": h}
        # The v2.6.2 schema allows no text wrapping attribute, so a long name
        # runs past its shape; keep the label equal to the name.
        data = c["data"]
        short = NODE_NAMES.get(ident)
        if short is not None and data["name"] != short:
            data["description"] = f"Full name: {data['name']}. {data['description']}"
            data["name"] = short
        assert len(data["name"]) <= NODE_NAME_MAX, data["name"]
        text = c["attrs"].setdefault("text", {})
        text.pop("textWrap", None)
        text["text"] = data["name"]
    nodes = {c["id"]: c for c in all_cells if is_node(c)}
    assert set(nodes) == set(layout["nodes"]), set(nodes) ^ set(layout["nodes"])

    out = []
    for c in all_cells:
        if c["shape"] in ("trust-boundary-curve", "trust-boundary-box"):
            members = [node_rect(by_id[m]) for m in layout["boxes"][c["id"]]]
            left = min(m[0] for m in members) - BOX_PAD_X
            right = max(m[2] for m in members) + BOX_PAD_X
            if right - left < BOX_MIN_W:
                mid = (left + right) / 2
                left, right = mid - BOX_MIN_W / 2, mid + BOX_MIN_W / 2
            top = min(m[1] for m in members) - BOX_PAD_TOP
            bottom = max(m[3] for m in members) + BOX_PAD_BOTTOM
            c = box_cell(c, (left, top, right, bottom), -50)
        out.append(c)
    assert set(layout["boxes"]) == {c["id"] for c in out if is_box(c)}
    by_id = {c["id"]: c for c in out}

    pairs: dict = {}
    for c in out:
        if c["shape"] == "flow":
            key = tuple(sorted((c["source"]["cell"], c["target"]["cell"])))
            pairs.setdefault(key, []).append(c["id"])
    for c in out:
        if c["shape"] != "flow":
            continue
        short = layout["labels"][c["id"]]
        assert len(short.split()) <= LABEL_MAX_WORDS, short
        data = c["data"]
        if data["name"] != short:
            data["description"] = f"Full label: {data['name']}. {data['description']}"
        data["name"] = short
        c["labels"] = [
            {
                "position": layout["label_at"].get(c["id"], 0.5),
                "attrs": {"label": {"text": short}},
            }
        ]
        c["connector"] = "normal"
        verts = layout["vertices"].get(c["id"])
        if verts is None:
            verts = auto_vertices(c, by_id, pairs)
        else:
            verts = [(x + VERTEX_X_SHIFT, y) for x, y in verts]
        c["vertices"] = [{"x": round(x), "y": round(y)} for x, y in verts]
    place_labels(out, layout)
    model["detail"]["diagrams"][0]["cells"] = out
    return model


LABEL_TRIES = (0.5, 0.4, 0.6, 0.3, 0.7, 0.25, 0.75, 0.2, 0.8, 0.15, 0.85)


def label_clear(rect, flow, by_id, placed) -> bool:
    """True when a label rectangle sits on no node, caption, other label or other flow."""
    for c in by_id.values():
        if is_node(c) and rects_overlap(rect, node_rect(c), 4):
            return False
        if is_box(c) and rects_overlap(rect, caption_rect(c), 4):
            return False
        if c["shape"] == "flow" and c["id"] != flow["id"]:
            pts = polyline(c, by_id)
            if any(seg_hits_rect(p, q, rect, 2) for p, q in itertools.pairwise(pts)):
                return False
    return not any(rects_overlap(rect, other, 4) for other in placed)


def place_labels(out: list, layout: dict) -> None:
    """Slide each label along its flow to the first spot that overlaps nothing."""
    by_id = {c["id"]: c for c in out}
    placed: list = []
    for c in out:
        if c["shape"] != "flow":
            continue
        tries = LABEL_TRIES
        if c["id"] in layout["label_at"]:
            tries = (layout["label_at"][c["id"]],) + LABEL_TRIES
        chosen = tries[0]
        for t in tries:
            c["labels"][0]["position"] = t
            if label_clear(label_rect(c, by_id), c, by_id, placed):
                chosen = t
                break
        c["labels"][0]["position"] = chosen
        placed.append(label_rect(c, by_id))


def centre(cell: dict) -> tuple[float, float]:
    x0, y0, x1, y1 = node_rect(cell)
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def auto_vertices(flow: dict, by_id: dict, pairs: dict) -> list:
    """Spread flows that share a pair of nodes so they do not lie on one line."""
    a, b = by_id[flow["source"]["cell"]], by_id[flow["target"]["cell"]]
    key = tuple(sorted((a["id"], b["id"])))
    group = pairs[key]
    if len(group) < 2:
        return []
    first, second = by_id[key[0]], by_id[key[1]]
    (ax, ay), (bx, by) = centre(first), centre(second)
    dx, dy = bx - ax, by - ay
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    nx, ny = -dy / length, dx / length
    # opposite directions get opposite sides, so a request and its reply part
    side = 1 if flow["source"]["cell"] == key[0] else -1
    slot = group.index(flow["id"])
    off = 70 * side * (1 + (slot // 2) * 0.5)
    return [((ax + bx) / 2 + nx * off, (ay + by) / 2 + ny * off)]


# --- geometry rules ----------------------------------------------------------


def polyline(flow: dict, by_id: dict) -> list:
    pts = [centre(by_id[flow["source"]["cell"]])]
    pts += [(v["x"], v["y"]) for v in flow.get("vertices", [])]
    pts.append(centre(by_id[flow["target"]["cell"]]))
    return pts


def seg_hits_rect(p, q, rect, margin=0.0) -> bool:
    x0, y0, x1, y1 = (
        rect[0] - margin,
        rect[1] - margin,
        rect[2] + margin,
        rect[3] + margin,
    )
    (px, py), (qx, qy) = p, q
    t0, t1 = 0.0, 1.0
    dx, dy = qx - px, qy - py
    for pp, dd, lo, hi in ((px, dx, x0, x1), (py, dy, y0, y1)):
        if abs(dd) < 1e-9:
            if pp < lo or pp > hi:
                return False
        else:
            ta, tb = (lo - pp) / dd, (hi - pp) / dd
            if ta > tb:
                ta, tb = tb, ta
            t0, t1 = max(t0, ta), min(t1, tb)
            if t0 > t1:
                return False
    return True


def point_at(pts: list, t: float) -> tuple[float, float]:
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    lengths = [((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in segs]
    target = sum(lengths) * t
    for (a, b), ln in zip(segs, lengths):
        if target <= ln or ln == 0:
            f = target / ln if ln else 0
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        target -= ln
    return pts[-1]


def label_rect(flow: dict, by_id: dict) -> tuple[float, float, float, float]:
    text = flow["labels"][0]["attrs"]["label"]["text"]
    cx, cy = point_at(polyline(flow, by_id), flow["labels"][0]["position"])
    w = CHAR_W * len(text) + 12
    return (cx - w / 2, cy - LABEL_H / 2, cx + w / 2, cy + LABEL_H / 2)


def caption_rect(box: dict) -> tuple[float, float, float, float]:
    text = box["attrs"]["label"]["text"]
    x0, y0 = box["position"]["x"], box["position"]["y"]
    lab = box["attrs"]["label"]
    x = x0 + lab["refX"]
    y = y0 + lab["refY"]
    return (x, y, x + 7.2 * len(text), y + 20)


def rects_overlap(a, b, margin=0.0) -> bool:
    return not (
        a[2] + margin <= b[0]
        or b[2] + margin <= a[0]
        or a[3] + margin <= b[1]
        or b[3] + margin <= a[1]
    )


def inside(inner, outer) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def violations(model: dict, layout: dict) -> list[str]:
    """Human-readable list of broken geometry rules; empty when the layout is fine."""
    cs = cells(model)
    by_id = {c["id"]: c for c in cs}
    nodes = [c for c in cs if is_node(c)]
    boxes = [c for c in cs if is_box(c)]
    flows = [c for c in cs if c["shape"] == "flow"]
    bad: list[str] = []
    for i, a in enumerate(nodes):
        for b in nodes[i + 1 :]:
            ra, rb = node_rect(a), node_rect(b)
            if rects_overlap(ra, rb):
                bad.append(f"nodes overlap: {a['id']} {b['id']}")
                continue
            hgap = max(rb[0] - ra[2], ra[0] - rb[2])
            vgap = max(rb[1] - ra[3], ra[1] - rb[3])
            if hgap < MIN_COL_GAP and vgap < MIN_ROW_GAP:
                bad.append(
                    f"nodes too close: {a['id']} {b['id']} ({hgap:.0f}, {vgap:.0f})"
                )
    members = {b["id"]: layout["boxes"][b["id"]] for b in boxes}
    inside_ids = {m for ms in members.values() for m in ms}
    for b in boxes:
        rb = node_rect(b)
        for m in members[b["id"]]:
            if not inside(node_rect(by_id[m]), rb):
                bad.append(f"{m} not inside {b['id']}")
        for n in nodes:
            if n["id"] not in members[b["id"]] and rects_overlap(node_rect(n), rb):
                bad.append(f"{n['id']} overlaps {b['id']}")
        for other in boxes:
            if other["id"] > b["id"] and rects_overlap(rb, node_rect(other), 20):
                bad.append(f"boxes overlap: {b['id']} {other['id']}")
    for n in nodes:
        if n["id"] not in inside_ids:
            continue
    labels = {f["id"]: label_rect(f, by_id) for f in flows}
    for f in flows:
        short = f["labels"][0]["attrs"]["label"]["text"]
        if len(short.split()) > LABEL_MAX_WORDS:
            bad.append(f"label too long: {f['id']}")
        pts = polyline(f, by_id)
        ends = {f["source"]["cell"], f["target"]["cell"]}
        for n in nodes:
            if n["id"] in ends:
                continue
            for p, q in itertools.pairwise(pts):
                if seg_hits_rect(p, q, node_rect(n), NODE_MARGIN):
                    bad.append(f"flow {f['id']} crosses node {n['id']}")
                    break
        for b in boxes:
            if ends & set(members[b["id"]]):
                continue
            if any(
                seg_hits_rect(p, q, node_rect(b)) for p, q in itertools.pairwise(pts)
            ):
                bad.append(f"flow {f['id']} passes through unrelated {b['id']}")
        for n in nodes:
            if rects_overlap(labels[f["id"]], node_rect(n), 4):
                bad.append(f"label of {f['id']} on node {n['id']}")
        for other in flows:
            if other["id"] != f["id"] and any(
                seg_hits_rect(p, q, labels[f["id"]], 2)
                for p, q in itertools.pairwise(polyline(other, by_id))
            ):
                bad.append(f"label of {f['id']} on the line of {other['id']}")
        for b in boxes:
            if rects_overlap(labels[f["id"]], caption_rect(b), 4):
                bad.append(f"label of {f['id']} on caption of {b['id']}")
    ids = sorted(labels)
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            if rects_overlap(labels[a], labels[b], 4):
                bad.append(f"labels overlap: {a} {b}")
    for b in boxes:
        cap = caption_rect(b)
        if cap[2] > b["position"]["x"] + b["size"]["width"]:
            bad.append(f"caption wider than its box: {b['id']}")
    return bad


# --- command line ------------------------------------------------------------


def render(model: dict) -> str:
    return json.dumps(model, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="fail if a file would change")
    ap.add_argument("--root", default=str(MODEL_DIR), help="directory of models")
    args = ap.parse_args(argv)
    root = Path(args.root)
    status = 0
    for name, layout in LAYOUTS.items():
        path = root / name
        model = json.loads(path.read_text(encoding="utf-8"))
        new = apply_layout(model, layout)
        for problem in violations(new, layout):
            print(f"{name}: {problem}", file=sys.stderr)
            status = 1
        text = render(new)
        if args.check:
            if path.read_text(encoding="utf-8") != text:
                print(
                    f"{name}: layout is out of date; run scripts/threat_dragon_layout.py",
                    file=sys.stderr,
                )
                status = 1
        else:
            path.write_text(text, encoding="utf-8")
    return status


if __name__ == "__main__":
    sys.exit(main())
