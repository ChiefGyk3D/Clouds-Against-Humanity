"""The ATT&CK Navigator layer must match the techniques the repository cites.

Layer format: https://github.com/mitre-attack/attack-navigator/blob/master/layers/spec/v4.5/layerformat.md
(required: name, domain, versions.navigator and versions.layer).
"""

import json
import re
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / "docs" / "threat-model"
LAYER = json.loads((DIR / "attack-navigator-layer.json").read_text())
REFERENCE = json.loads((DIR / "framework-reference.json").read_text())["attack"]


def test_required_layer_fields():
    assert LAYER["name"]
    assert LAYER["domain"] == "enterprise-attack"
    assert LAYER["versions"]["layer"] == "4.5"
    assert tuple(map(int, LAYER["versions"]["navigator"].split("."))) >= (4, 9, 0)
    assert LAYER["versions"]["attack"] == REFERENCE["version"].split(".")[0]


def test_coloured_techniques_are_exactly_the_cited_ones():
    coloured = {t["techniqueID"] for t in LAYER["techniques"] if t.get("color")}
    assert coloured == set(REFERENCE["techniques"])


def test_technique_ids_are_well_formed_and_unique():
    ids = [t["techniqueID"] for t in LAYER["techniques"]]
    assert all(re.fullmatch(r"T\d{4}(\.\d{3})?", i) for i in ids)
    assert len(ids) == len(set(ids))


def test_colours_are_hex_and_the_legend_explains_them():
    colours = {t["color"] for t in LAYER["techniques"] if t.get("color")}
    assert all(re.fullmatch(r"#[0-9a-f]{6}", c) for c in colours)
    assert colours <= {item["color"] for item in LAYER["legendItems"]}
