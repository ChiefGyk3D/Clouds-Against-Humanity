"""Tests for the OWASP Threat Dragon model that goes with the wiki exercise.

The model is a teaching artefact: it records the data flow diagram of this
repository, with the trust boundaries B1 to B8 from Threat-Model-Exercise.md
and the T-numbers from Threat-Model.md. These checks keep the three in step.
They cannot show that the model is true of the running system.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "docs" / "threat-model" / "clouds-against-humanity.threat-dragon.json"
WIKI = ROOT / "docs" / "wiki"
STRIDE = {
    "Spoofing",
    "Tampering",
    "Repudiation",
    "Information disclosure",
    "Denial of service",
    "Elevation of privilege",
}
# Threat Dragon v2.6.2 (ThreatEditDialog.vue) offers only these three statuses.
STATUSES = {"Open", "Mitigated", "NotApplicable"}
SEVERITIES = {"High", "Medium", "Low"}


@pytest.fixture(scope="module")
def model() -> dict:
    return json.loads(MODEL.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cells(model) -> list:
    return model["detail"]["diagrams"][0]["cells"]


def threats_of(cells):
    for cell in cells:
        for threat in cell["data"].get("threats", []):
            yield cell, threat


def test_top_level_keys(model):
    assert {"version", "summary", "detail"} <= model.keys()
    assert model["version"].startswith("2.")
    assert model["summary"]["title"]
    detail = model["detail"]
    assert {"contributors", "diagrams", "diagramTop", "reviewer", "threatTop"} <= (
        detail.keys()
    )
    assert detail["diagrams"], "no diagram"
    diagram = detail["diagrams"][0]
    assert {"diagramType", "id", "thumbnail", "title", "version", "cells"} <= (
        diagram.keys()
    )
    assert diagram["diagramType"] == "STRIDE"


def test_cell_ids_are_unique(cells):
    ids = [c["id"] for c in cells]
    assert len(ids) == len(set(ids))


def test_threat_ids_and_numbers_are_unique(model, cells):
    found = [t for _, t in threats_of(cells)]
    ids = [t["id"] for t in found]
    numbers = [t["number"] for t in found]
    assert len(ids) == len(set(ids))
    assert len(numbers) == len(set(numbers))
    assert model["detail"]["threatTop"] == max(numbers)


def test_flow_endpoints_exist(cells):
    ids = {c["id"] for c in cells}
    flows = [c for c in cells if c["shape"] == "flow"]
    assert flows
    for flow in flows:
        for end in ("source", "target"):
            assert flow[end]["cell"] in ids, f"{flow['data']['name']}: {end}"
        assert flow["source"]["cell"] != flow["target"]["cell"]
        assert flow["data"]["name"].strip(), "unlabelled flow"


def test_flows_connect_elements_not_boundaries(cells):
    kinds = {c["id"]: c["shape"] for c in cells}
    for flow in (c for c in cells if c["shape"] == "flow"):
        assert kinds[flow["source"]["cell"]] not in {
            "flow",
            "trust-boundary-curve",
            "trust-boundary-box",
        }
        assert kinds[flow["target"]["cell"]] not in {
            "flow",
            "trust-boundary-curve",
            "trust-boundary-box",
        }


def test_threats_sit_on_elements_that_exist_and_can_hold_them(cells):
    # Threat Dragon stores a threat inside the element it is about, and its
    # documentation says trust boundaries cannot have threats.
    for cell in cells:
        if cell["data"].get("isTrustBoundary"):
            assert not cell["data"].get("threats"), cell["data"]["name"]
        elif cell["shape"] != "flow":
            assert "threats" in cell["data"]
    assert list(threats_of(cells))


def test_threat_fields_are_valid(cells):
    for cell, t in threats_of(cells):
        where = cell["data"]["name"]
        assert t["modelType"] == "STRIDE", where
        assert t["type"] in STRIDE, where
        assert t["status"] in STATUSES, where
        assert t["severity"] in SEVERITIES, where
        for field in ("title", "description", "mitigation"):
            assert t[field].strip(), (where, field)


def test_has_open_threats_flag_matches(cells):
    for cell in cells:
        if "threats" not in cell["data"]:
            continue
        expected = any(t["status"] == "Open" for t in cell["data"]["threats"])
        assert cell["data"]["hasOpenThreats"] is expected, cell["data"]["name"]


def test_every_stride_letter_is_used(cells):
    used = {t["type"] for _, t in threats_of(cells)}
    assert used == STRIDE


def exercise_boundaries() -> dict:
    text = (WIKI / "Threat-Model-Exercise.md").read_text(encoding="utf-8")
    text = text.replace("<br/>", " ")
    found = dict(re.findall(r'"(B\d+): ([^"]+)"', text))
    assert found, "no boundaries parsed from the exercise page"
    return found


def test_boundaries_in_exercise_page_exist_in_model(cells):
    names = [
        c["data"]["name"] for c in cells if c["data"].get("isTrustBoundary") is True
    ]
    for ident in exercise_boundaries():
        assert any(n.startswith(f"{ident}:") for n in names), ident
    assert len(names) == len(set(names))
    assert len(names) == len(exercise_boundaries())
    for c in cells:
        if c["data"].get("isTrustBoundary") is True:
            assert c["shape"].startswith("trust-boundary")


def test_boundary_wording_matches_exercise_page(cells):
    names = {
        n.split(":")[0]: n
        for n in (
            c["data"]["name"] for c in cells if c["data"].get("isTrustBoundary") is True
        )
    }
    for ident, text in exercise_boundaries().items():
        first = " ".join(text.lower().split()[:2]).rstrip(",;")
        assert first in names[ident].lower(), (ident, text, names[ident])


def model_text(model) -> str:
    return json.dumps(model)


def test_t_numbers_in_model_exist_in_threat_model_page(model):
    page = (WIKI / "Threat-Model.md").read_text(encoding="utf-8")
    defined = set(re.findall(r"^\| (T\d+) \|", page, flags=re.MULTILINE))
    assert defined
    used = set(re.findall(r"\bT\d+\b", model_text(model)))
    assert used, "model cites no T-numbers"
    assert used <= defined, sorted(used - defined)


def test_every_documented_threat_is_modelled(model):
    page = (WIKI / "Threat-Model.md").read_text(encoding="utf-8")
    defined = set(re.findall(r"^\| (T\d+) \|", page, flags=re.MULTILINE))
    used = set(re.findall(r"\bT\d+\b", model_text(model)))
    assert defined <= used, sorted(defined - used)


def test_no_addresses_or_private_identifiers(model):
    text = model_text(model)
    assert not re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text), "IPv4 address"
    assert not re.search(
        r"\b[0-9a-f]{1,4}(?::[0-9a-f]{0,4}){3,}\b", text, re.IGNORECASE
    )
    assert not re.search(r"https?://", text), "URL in model"
    assert not re.search(r"\b[\w.+-]+@[\w-]+\.\w+", text), "email address"


def test_exercise_page_points_at_the_model():
    page = (WIKI / "Threat-Dragon-Exercise.md").read_text(encoding="utf-8")
    assert "docs/threat-model/clouds-against-humanity.threat-dragon.json" in page
    for ident in exercise_boundaries():
        assert ident in page


def test_wiki_pages_link_the_exercise():
    for name in ("_Sidebar.md", "Home.md"):
        text = (WIKI / name).read_text(encoding="utf-8")
        assert "(Threat-Dragon-Exercise.md)" in text, name


def test_flow_count_matches_exercise_page(cells):
    page = (WIKI / "Threat-Dragon-Exercise.md").read_text(encoding="utf-8")
    flows = [c for c in cells if c["shape"] == "flow"]
    assert f"{len(flows)} labelled flows" in page


def test_flows_are_unidirectional_and_connector_link_is_split(cells):
    # A flow in the model runs one way; a link that carries a token out and
    # a session back is two flows.
    by_id = {c["id"]: c for c in cells}
    for flow in (c for c in cells if c["shape"] == "flow"):
        if flow["data"].get("isBidirectional"):
            assert flow["id"] == "flow-f-state", flow["data"]["name"]
    link, session = by_id["flow-f-connector-link"], by_id["flow-f-session"]
    assert (link["source"]["cell"], link["target"]["cell"]) == (
        "node-droplets",
        "node-twingate",
    )
    assert (session["source"]["cell"], session["target"]["cell"]) == (
        "node-twingate",
        "node-droplets",
    )
    assert "flow-f-relay" not in by_id


def test_accepted_risks_stay_open_and_say_so(cells):
    # The app has no Accepted status, so an accepted risk is Open and its
    # mitigation text says "Accepted".
    accepted = [t for _, t in threats_of(cells) if "Accepted" in t["mitigation"]]
    assert accepted
    for t in accepted:
        assert t["status"] == "Open", t["id"]


def test_proposed_run_is_not_described_as_credential_free(cells):
    node = next(c for c in cells if c["id"] == "node-sl_prop")
    text = node["data"]["description"]
    assert "no credentials" not in text.lower()
    assert "DOPPLER_TOKEN" in text


def test_exercise_reference_answer_matches_read_request_flow(cells):
    flow = next(c for c in cells if c["id"] == "flow-f-tok")
    types = {t["type"] for t in flow["data"]["threats"]}
    assert {"Spoofing", "Information disclosure"} <= types
