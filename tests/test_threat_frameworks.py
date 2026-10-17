"""Tests for the framework-mapped Threat Dragon models and their reference data.

docs/threat-model/ holds three importable models of this repository: the STRIDE
model (tested in test_threat_dragon_model.py), a STRIDE model whose threats
cite MITRE ATT&CK techniques, and one for the AI tools that touch the repository
that cites MITRE ATLAS techniques. Threat Dragon has no ATT&CK or ATLAS threat
type, so the technique sits in the threat title and description.

These checks keep three things in step: the model files, the wiki pages that
teach them, and docs/threat-model/framework-reference.json, a small curated
copy of the technique and tactic IDs and names this repository cites. Nothing
here touches the network. They cannot show that a mapping is the best fit, only
that every ID cited exists in the reference and is spelled the way the data
spells it.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "docs" / "threat-model"
WIKI = ROOT / "docs" / "wiki"
REFERENCE = MODEL_DIR / "framework-reference.json"
STRIDE_MODEL = MODEL_DIR / "clouds-against-humanity.threat-dragon.json"
ATTACK_MODEL = MODEL_DIR / "clouds-against-humanity.attack.threat-dragon.json"
ATLAS_MODEL = MODEL_DIR / "clouds-against-humanity.atlas.threat-dragon.json"
PAGE = WIKI / "Threat-Frameworks-STRIDE-ATTACK-ATLAS.md"
MODELS = sorted(MODEL_DIR.glob("*.threat-dragon.json"))

STRIDE = {
    "Spoofing",
    "Tampering",
    "Repudiation",
    "Information disclosure",
    "Denial of service",
    "Elevation of privilege",
}
STATUSES = {"Open", "Mitigated", "NotApplicable"}
SEVERITIES = {"High", "Medium", "Low"}

# The lookbehind keeps a URL path such as /techniques/T1078/004 and a file name
# out of the match. ATLAS IDs always carry the AML. prefix.
ATT_TECH = re.compile(r"(?<![\w./])T1\d{3}(?:\.\d{3})?\b")
ATT_TAC = re.compile(r"(?<![\w./])TA\d{4}\b")
ATL_TECH = re.compile(r"AML\.T\d{4}(?:\.\d{3})?\b")
ATL_TAC = re.compile(r"AML\.TA\d{4}\b")
UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
)


@pytest.fixture(scope="module")
def ref() -> dict:
    return json.loads(REFERENCE.read_text(encoding="utf-8"))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def cells_of(model: dict) -> list:
    return model["detail"]["diagrams"][0]["cells"]


def threats_of(cells):
    for cell in cells:
        for threat in cell["data"].get("threats", []):
            yield cell, threat


def known_names(ref: dict, kind: str) -> dict:
    """ID -> acceptable names (the current one, and a historic one if any)."""
    out: dict = {}
    if kind == "attack_tech":
        block = ref["attack"]
        for i, e in block["techniques"].items():
            out.setdefault(i, set()).add(e["name"])
        for i, e in block["historic_techniques"].items():
            out.setdefault(i, set()).add(e["name"])
    elif kind == "attack_tac":
        block = ref["attack"]
        for i, e in block["tactics"].items():
            out.setdefault(i, set()).add(e["name"])
        for i, e in block["historic_tactics"].items():
            out.setdefault(i, set()).add(e["name"])
    elif kind == "atlas_tech":
        for i, e in ref["atlas"]["techniques"].items():
            out.setdefault(i, set()).add(e["name"])
    else:
        for i, e in ref["atlas"]["tactics"].items():
            out.setdefault(i, set()).add(e["name"])
    return out


KINDS = {
    "attack_tech": ATT_TECH,
    "attack_tac": ATT_TAC,
    "atlas_tech": ATL_TECH,
    "atlas_tac": ATL_TAC,
}


def all_ids(text: str) -> dict:
    return {k: set(rx.findall(text)) for k, rx in KINDS.items()}


def check_text(ref: dict, text: str, where: str) -> None:
    """Every cited ID exists and is immediately followed by its name."""
    for kind, rx in KINDS.items():
        names = known_names(ref, kind)
        for m in rx.finditer(text):
            ident = m.group(0)
            assert ident in names, f"{where}: {ident} is not in the reference file"
            tail = text[m.end() :]
            # The exact name, then a non-name character (or the end): a name
            # that merely extends a valid one ("Cloud Logs" for "Cloud Log")
            # is a misspelling, not a match.
            assert any(
                re.match(rf" {re.escape(n)}(?![\w-])", tail) for n in names[ident]
            ), (
                f"{where}: {ident} is not followed by its name ({sorted(names[ident])})"
            )


def tactic_sets_ok(ref: dict, text: str, where: str) -> None:
    """A technique cited with a tactic list has the tactics the data gives it."""
    pat = re.compile(
        r"((?:AML\.)?T\d{4}(?:\.\d{3})?) ([^\[\]().,;:]+?) [\[(]"
        r"((?:AML\.)?TA\d{4} [^\[\]()]*)[\])]"
    )
    for m in pat.finditer(text):
        ident, _name, listed = m.groups()
        if ident.startswith("AML."):
            entry = ref["atlas"]["techniques"].get(ident)
        else:
            entry = ref["attack"]["techniques"].get(ident)
        if entry is None:
            continue
        got = {item.strip().split(" ")[0] for item in listed.split(",")}
        assert got == set(entry["tactics"]), f"{where}: {ident} tactics {sorted(got)}"


# --- structure, for every model in the directory --------------------------


def test_the_expected_models_exist():
    assert STRIDE_MODEL in MODELS
    assert ATTACK_MODEL in MODELS
    assert ATLAS_MODEL in MODELS


@pytest.mark.parametrize("path", MODELS, ids=lambda p: p.name)
class TestEveryModel:
    def test_top_level_keys(self, path):
        model = load(path)
        assert {"version", "summary", "detail"} <= model.keys()
        assert model["version"].startswith("2.")
        assert model["summary"]["title"]
        detail = model["detail"]
        assert {"contributors", "diagrams", "diagramTop", "reviewer", "threatTop"} <= (
            detail.keys()
        )
        diagram = detail["diagrams"][0]
        assert {"diagramType", "id", "thumbnail", "title", "version", "cells"} <= (
            diagram.keys()
        )
        assert diagram["diagramType"] == "STRIDE"

    def test_ids_are_unique_and_readable(self, path):
        model = load(path)
        cells = cells_of(model)
        ids = [c["id"] for c in cells]
        assert len(ids) == len(set(ids))
        tids = [t["id"] for _, t in threats_of(cells)]
        numbers = [t["number"] for _, t in threats_of(cells)]
        assert len(tids) == len(set(tids))
        assert len(numbers) == len(set(numbers))
        assert model["detail"]["threatTop"] == max(numbers)
        assert not UUID.search(path.read_text(encoding="utf-8")), "UUID-looking id"

    def test_flows_connect_existing_elements(self, path):
        cells = cells_of(load(path))
        kinds = {c["id"]: c["shape"] for c in cells}
        flows = [c for c in cells if c["shape"] == "flow"]
        assert flows
        for flow in flows:
            assert flow["data"]["name"].strip(), "unlabelled flow"
            for end in ("source", "target"):
                target = flow[end]["cell"]
                assert target in kinds, f"{flow['id']}: {end}"
                assert kinds[target] not in {
                    "flow",
                    "trust-boundary-curve",
                    "trust-boundary-box",
                }
            assert flow["source"]["cell"] != flow["target"]["cell"]

    def test_boundaries_hold_no_threats(self, path):
        cells = cells_of(load(path))
        boundaries = [c for c in cells if c["data"].get("isTrustBoundary") is True]
        assert boundaries
        for c in boundaries:
            assert c["shape"].startswith("trust-boundary"), c["id"]
            assert not c["data"].get("threats"), c["id"]
        names = [c["data"]["name"] for c in boundaries]
        assert len(names) == len(set(names))
        for c in cells:
            if not c["data"].get("isTrustBoundary") and c["shape"] != "flow":
                assert "threats" in c["data"], c["id"]

    def test_threat_fields_are_valid(self, path):
        cells = cells_of(load(path))
        found = list(threats_of(cells))
        assert found
        for cell, t in found:
            where = f"{path.name}: {cell['data']['name']}"
            assert t["modelType"] == "STRIDE", where
            assert t["type"] in STRIDE, where
            assert t["status"] in STATUSES, where
            assert t["severity"] in SEVERITIES, where
            for field in ("title", "description", "mitigation"):
                assert t[field].strip(), (where, field)

    def test_has_open_threats_flag_matches(self, path):
        for cell in cells_of(load(path)):
            if "threats" not in cell["data"]:
                continue
            expected = any(t["status"] == "Open" for t in cell["data"]["threats"])
            assert cell["data"]["hasOpenThreats"] is expected, cell["data"]["name"]

    def test_no_addresses_urls_or_private_identifiers(self, path):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text), "IPv4 address"
        assert not re.search(
            r"\b[0-9a-f]{1,4}(?::[0-9a-f]{0,4}){3,}\b", text, re.IGNORECASE
        )
        assert not re.search(r"https?://", text), "URL in model"
        assert not re.search(r"\b[\w.+-]+@[\w-]+\.\w+", text), "email address"

    def test_every_cited_id_exists_with_its_name(self, path, ref):
        text = path.read_text(encoding="utf-8")
        check_text(ref, text, path.name)
        tactic_sets_ok(ref, text, path.name)


# --- the ATT&CK model ------------------------------------------------------


def test_attack_model_is_the_same_diagram_as_the_stride_model():
    stride = {c["id"]: c for c in cells_of(load(STRIDE_MODEL))}
    attack = {c["id"]: c for c in cells_of(load(ATTACK_MODEL))}
    assert stride.keys() == attack.keys()
    for ident, cell in stride.items():
        other = attack[ident]
        assert other["shape"] == cell["shape"], ident
        assert other["data"]["name"] == cell["data"]["name"], ident
        for end in ("source", "target"):
            assert other.get(end) == cell.get(end), (ident, end)


def test_attack_threats_cite_attack_ids_only_and_lead_with_one(ref):
    cells = cells_of(load(ATTACK_MODEL))
    for _, t in threats_of(cells):
        assert ATT_TECH.match(t["title"]), t["id"]
        body = t["title"] + " " + t["description"]
        assert ATT_TECH.search(t["description"]), t["id"]
        assert not ATL_TECH.search(body), t["id"]
        assert "ATT&CK v20.0" in t["description"], t["id"]
        assert "Detection:" in t["mitigation"], t["id"]


def test_attack_model_keeps_the_stride_model_numbers_and_t_numbers():
    stride = {t["id"]: t for _, t in threats_of(cells_of(load(STRIDE_MODEL)))}
    attack = list(threats_of(cells_of(load(ATTACK_MODEL))))
    assert attack
    for _, t in attack:
        original = stride[t["id"]]
        for field in ("number", "type", "severity", "status"):
            assert t[field] == original[field], (t["id"], field)
    page = (WIKI / "Threat-Model.md").read_text(encoding="utf-8")
    defined = set(re.findall(r"^\| (T\d+) \|", page, flags=re.MULTILINE))
    used = set(re.findall(r"\bT\d{1,2}\b", json.dumps(load(ATTACK_MODEL))))
    assert defined <= used, sorted(defined - used)
    assert used <= defined, sorted(used - defined)


def test_attack_model_cites_cloud_and_enterprise_techniques_with_iaas(ref):
    text = ATTACK_MODEL.read_text(encoding="utf-8")
    cited = set(ATT_TECH.findall(text))
    techniques = ref["attack"]["techniques"]
    assert cited <= techniques.keys()
    # The brief asks for the cloud/IaaS matrix: several cited techniques must
    # list IaaS among their platforms in the data.
    assert sum(1 for i in cited if techniques[i]["iaas"]) >= 10


# --- the ATLAS model -------------------------------------------------------


def test_atlas_threats_cite_atlas_ids_only_and_lead_with_one():
    cells = cells_of(load(ATLAS_MODEL))
    found = list(threats_of(cells))
    assert len(found) >= 10
    for _, t in found:
        assert t["title"].startswith("AML.T"), t["id"]
        assert ATL_TECH.search(t["description"]), t["id"]
        assert "ATLAS 2026.09" in t["description"], t["id"]
        assert not ATT_TECH.search(t["title"] + t["description"]), t["id"]


def test_atlas_boundaries_use_their_own_numbering():
    names = [
        c["data"]["name"]
        for c in cells_of(load(ATLAS_MODEL))
        if c["data"].get("isTrustBoundary") is True
    ]
    assert [n.split(":")[0] for n in names] == [f"AB{i}" for i in range(1, 6)]


def test_stride_model_cites_no_framework_ids():
    text = STRIDE_MODEL.read_text(encoding="utf-8")
    for kind, ids in all_ids(text).items():
        assert not ids, (kind, sorted(ids))


# --- the reference file ----------------------------------------------------


def test_reference_has_source_version_and_date_for_each_framework(ref):
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", ref["retrieved"])
    for name in ("attack", "atlas"):
        block = ref[name]
        assert block["version"]
        assert block["source"].startswith("https://")
        assert block["release"].startswith("https://")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", block["retrieved"])
        assert block["techniques"] and block["tactics"]
    assert ref["attack"]["version"] == "20.0"
    assert ref["atlas"]["version"] == "2026.09"
    for entry in ref["attack"]["techniques"].values():
        assert entry["url"].startswith("https://attack.mitre.org/")
        assert entry["name"].strip() and entry["tactics"]
    for entry in ref["attack"]["historic_techniques"].values():
        assert entry["version"] and entry["source"].startswith("https://")


def test_reference_tactics_resolve(ref):
    for block, prefix in ((ref["attack"], "TA"), (ref["atlas"], "AML.TA")):
        for ident, entry in block["techniques"].items():
            assert entry["name"].strip(), ident
            for tactic in entry["tactics"]:
                assert tactic in block["tactics"], (ident, tactic)
        for tactic in block["tactics"]:
            assert tactic.startswith(prefix)
    for ident, entry in ref["attack"]["historic_techniques"].items():
        assert entry["superseded_by"] in ref["attack"]["techniques"], ident


def test_reference_lists_only_ids_this_repository_cites(ref):
    text = "\n".join(
        p.read_text(encoding="utf-8") for p in [*MODELS, *sorted(WIKI.glob("*.md"))]
    )
    cited = all_ids(text)
    listed = {
        "attack_tech": set(ref["attack"]["techniques"])
        | set(ref["attack"]["historic_techniques"]),
        "attack_tac": set(ref["attack"]["tactics"])
        | set(ref["attack"]["historic_tactics"]),
        "atlas_tech": set(ref["atlas"]["techniques"]),
        "atlas_tac": set(ref["atlas"]["tactics"]),
    }
    for kind in KINDS:
        # Tactics are listed for the techniques that carry them even where no
        # text names the tactic, so only techniques must all be cited.
        if kind.endswith("tech"):
            assert listed[kind] == cited[kind], (kind, listed[kind] ^ cited[kind])
        else:
            assert cited[kind] <= listed[kind], (kind, cited[kind] - listed[kind])


# --- the wiki pages --------------------------------------------------------


@pytest.mark.parametrize("path", sorted(WIKI.glob("*.md")), ids=lambda p: p.name)
def test_wiki_pages_cite_only_verified_ids_with_their_names(path, ref):
    text = path.read_text(encoding="utf-8")
    check_text(ref, text, path.name)
    tactic_sets_ok(ref, text, path.name)


def test_wiki_page_counts_match_the_models():
    page = PAGE.read_text(encoding="utf-8")
    attack_cells = cells_of(load(ATTACK_MODEL))
    atlas_cells = cells_of(load(ATLAS_MODEL))
    attack_threats = len(list(threats_of(attack_cells)))
    atlas_threats = len(list(threats_of(atlas_cells)))
    attack_ids = set(ATT_TECH.findall(ATTACK_MODEL.read_text(encoding="utf-8")))
    atlas_ids = set(ATL_TECH.findall(ATLAS_MODEL.read_text(encoding="utf-8")))
    assert f"{attack_threats} threats" in page
    assert f"{len(attack_ids)} distinct techniques" in page
    assert (
        f"{atlas_threats} threats, {len(atlas_ids)} distinct ATLAS techniques" in page
    )
    assert f"{len(attack_cells)} for the ATT&CK model" in page
    assert f"{len(atlas_cells)} for the ATLAS model" in page


def test_wiki_mapping_table_covers_every_t_number():
    page = PAGE.read_text(encoding="utf-8")
    defined = re.findall(
        r"^\| (T\d+) \|",
        (WIKI / "Threat-Model.md").read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    rows = re.findall(r"^\| (T\d{1,2}) \|", page, flags=re.MULTILINE)
    assert rows == defined


def test_wiki_pages_link_the_frameworks_page():
    target = "(Threat-Frameworks-STRIDE-ATTACK-ATLAS.md)"
    for name in (
        "_Sidebar.md",
        "Home.md",
        "Threat-Dragon-Exercise.md",
        "Threat-Model-Exercise.md",
    ):
        assert target in (WIKI / name).read_text(encoding="utf-8"), name


def test_wiki_page_says_threat_dragon_has_no_attack_or_atlas_type():
    page = PAGE.read_text(encoding="utf-8")
    assert "There is no ATT&CK or ATLAS type" in page
    for model in ("STRIDE", "LINDDUN", "CIA", "PLOT4ai"):
        assert model in page
    for path in (ATTACK_MODEL, ATLAS_MODEL):
        assert "no" in load(path)["summary"]["description"].lower()
        assert "threat type" in load(path)["summary"]["description"]
