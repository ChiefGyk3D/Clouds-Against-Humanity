"""Checks for the importable Grafana dashboards in dashboards/.

The dashboards are shared, so they must carry no real endpoint. These tests
keep that true: every data source is a template variable (no literal uid),
no query holds a URL, no address outside the three documentation ranges
appears anywhere, and every dashboard has the `site` and `instance`
variables. The rules live in `problems()` and `cross_problems()`; a hostile
fixture per rule proves each one fails when it should (a guard that never
fails guards nothing). The panels' queries are not run against a Prometheus or
OpenSearch here: this is a structural check, not proof the queries return data.
"""

import copy
import ipaddress
import json
import re
from pathlib import Path

import pytest

DASHBOARDS = Path(__file__).resolve().parent.parent / "dashboards"
EXPECTED_UIDS = {"cah-sites-overview", "cah-droplet-health", "cah-wazuh-agents"}
DOC_RANGES = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
DS_VAR = re.compile(r"^\$\{DS_[A-Z0-9_]+\}$")
URL = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://")
# The instance variable is itself filtered by site, so either one scopes a query.
SITE_REF = re.compile(r"\$(?:site|instance)\b|\$\{(?:site|instance)[:}]")
MIN_SCHEMA = 41  # Grafana 12.x


def walk_panels(panels):
    for p in panels:
        yield p
        yield from walk_panels(p.get("panels") or [])


def walk_strings(node, path="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def walk_uids(node, path="$"):
    """Yield (path, value) for every key named uid, at any depth."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "uid":
                yield f"{path}.uid", v
            yield from walk_uids(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_uids(v, f"{path}[{i}]")


def problems(d: dict) -> list[str]:
    out = []
    for key in ("uid", "title", "schemaVersion", "panels"):
        if key not in d:
            out.append(f"missing {key}")
    if out:
        return out
    if not isinstance(d["schemaVersion"], int) or d["schemaVersion"] < MIN_SCHEMA:
        out.append(f"schemaVersion {d['schemaVersion']!r} is below {MIN_SCHEMA}")
    if "cah" not in d.get("tags", []):
        out.append("tag cah missing")
    if not d["panels"]:
        out.append("no panels")

    variables = d.get("templating", {}).get("list", [])
    ds_vars = {v["name"] for v in variables if v.get("type") == "datasource"}
    by_name = {v.get("name"): v for v in variables}
    for need in ("site", "instance"):
        if need not in by_name:
            out.append(f"variable {need} missing")
    if "site" in by_name and not by_name["site"].get("multi"):
        out.append("variable site is not multi-value")
    if not ds_vars:
        out.append("no datasource template variable")

    def ds_ok(ds, where):
        if not isinstance(ds, dict) or not isinstance(ds.get("uid"), str) or not DS_VAR.match(ds["uid"]):
            out.append(f"{where}: datasource is not a ${{DS_*}} variable: {ds!r}")
        elif ds["uid"][2:-1] not in ds_vars:
            out.append(f"{where}: datasource variable {ds['uid']} is not declared")

    for v in variables:
        if v.get("type") == "query":
            ds_ok(v.get("datasource"), f"variable {v.get('name')}")

    # A literal uid anywhere (including inside a panel option) is a leak.
    for path, value in walk_uids(d):
        if path == "$.uid":
            continue
        if not (isinstance(value, str) and DS_VAR.match(value)):
            out.append(f"{path}: literal uid {value!r}")

    seen_ids = set()
    for p in walk_panels(d["panels"]):
        title = p.get("title", "?")
        if p.get("id") in seen_ids:
            out.append(f"{title}: duplicate panel id {p.get('id')}")
        seen_ids.add(p.get("id"))
        if p.get("type") == "row":
            continue
        if len((p.get("description") or "").strip()) < 40:
            out.append(f"{title}: description missing or too short")
        ds_ok(p.get("datasource"), title)
        if not p.get("targets"):
            out.append(f"{title}: no targets")
        for t in p.get("targets", []):
            ds_ok(t.get("datasource"), f"{title} target {t.get('refId')}")
            query = t.get("expr") or t.get("query") or ""
            if not query:
                out.append(f"{title} target {t.get('refId')}: empty query")
            elif not SITE_REF.search(query):
                out.append(f"{title} target {t.get('refId')}: query uses neither the site nor the instance variable")

    for path, s in walk_strings(d):
        if URL.search(s):
            out.append(f"{path}: contains a URL")
        for m in IPV4.finditer(s):
            try:
                ip = ipaddress.ip_address(m.group(0))
            except ValueError:
                out.append(f"{path}: malformed address {m.group(0)}")
                continue
            if not any(ip in net for net in DOC_RANGES):
                out.append(f"{path}: address {ip} is outside the documentation ranges")
    return out


def cross_problems(dashboards: list[dict]) -> list[str]:
    out = []
    for key in ("uid", "title"):
        values = [d[key] for d in dashboards]
        out += [f"duplicate {key}: {v}" for v in sorted({v for v in values if values.count(v) > 1})]
    return out


def load_all():
    return {p.name: json.loads(p.read_text()) for p in sorted(DASHBOARDS.glob("*.json"))}


# ---------------------------------------------------------------- the real files


def test_the_expected_dashboards_exist():
    found = {d["uid"] for d in load_all().values()}
    assert found == EXPECTED_UIDS, f"dashboards/ holds {sorted(found)}"


@pytest.mark.parametrize("name", sorted(p.name for p in DASHBOARDS.glob("*.json")) or ["<none collected>"])
def test_each_dashboard_passes_every_rule(name):
    path = DASHBOARDS / name
    assert path.is_file(), "no dashboards collected"
    d = json.loads(path.read_text())  # also proves valid JSON
    assert problems(d) == []
    assert path.stem.replace("_", "-") == d["uid"], "file name should be the uid with underscores"


def test_uids_and_titles_are_unique():
    assert cross_problems(list(load_all().values())) == []


def test_files_are_ascii_without_dashes_used_as_punctuation():
    for name, d in load_all().items():
        text = (DASHBOARDS / name).read_text()
        assert "—" not in text and "–" not in text, f"{name}: em or en dash"


def test_wazuh_panels_with_unverified_fields_say_so():
    d = load_all()["cah_wazuh_agents.json"]
    panels = [p for p in walk_panels(d["panels"]) if p["type"] != "row"]
    assert panels
    for p in panels:
        assert "UNVERIFIED" in p["description"], f"{p['title']}: field names not marked UNVERIFIED"


# ---------------------------------------------------------------- the guard bites

GOOD = {
    "uid": "cah-test",
    "title": "Test",
    "schemaVersion": 41,
    "tags": ["cah"],
    "templating": {"list": [
        {"type": "datasource", "name": "DS_PROMETHEUS", "query": "prometheus"},
        {"type": "query", "name": "site", "multi": True, "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}},
        {"type": "query", "name": "instance", "multi": True, "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}},
    ]},
    "panels": [
        {"id": 1, "type": "row", "title": "Row", "panels": []},
        {"id": 2, "type": "stat", "title": "Up", "description": "Shows how many targets answered the last scrape, per site.",
         "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
         "targets": [{"refId": "A", "expr": 'up{site=~"$site"}',
                      "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}}]},
    ],
}


def mutated(fn):
    d = copy.deepcopy(GOOD)
    fn(d)
    return d


def panel(d):
    return d["panels"][1]


HOSTILE = {
    "literal panel datasource uid": (lambda d: panel(d)["datasource"].update(uid="abc123XYZ"), "not a ${DS_*}"),
    "literal target datasource uid": (lambda d: panel(d)["targets"][0]["datasource"].update(uid="abc123XYZ"), "not a ${DS_*}"),
    "undeclared datasource variable": (lambda d: panel(d)["datasource"].update(uid="${DS_OTHER}"), "not declared"),
    "datasource missing": (lambda d: panel(d).pop("datasource"), "not a ${DS_*}"),
    "literal uid hidden in an option": (lambda d: panel(d).update(options={"x": {"uid": "P1234567"}}), "literal uid"),
    "url in a query": (lambda d: panel(d)["targets"][0].update(expr='up{site=~"$site"} # http://prom.example.net:9090'), "URL"),
    "url in a description": (lambda d: panel(d).update(description="See https://grafana.example.net/d/abc for the live one."), "URL"),
    "real public address": (lambda d: panel(d).update(description="Shows the target at 8.8.8.8 that answered the last scrape."), "outside the documentation"),
    "real private address": (lambda d: panel(d)["targets"][0].update(expr='up{site=~"$site", instance="10.0.0.5:9100"}'), "outside the documentation"),
    "address in a variable": (lambda d: d["templating"]["list"][1].update(query="label_values(up{instance=\"172.16.4.9\"}, site)"), "outside the documentation"),
    "site variable missing": (lambda d: d["templating"]["list"].pop(1), "variable site missing"),
    "instance variable missing": (lambda d: d["templating"]["list"].pop(2), "variable instance missing"),
    "site variable single-value": (lambda d: d["templating"]["list"][1].update(multi=False), "not multi-value"),
    "query ignores site": (lambda d: panel(d)["targets"][0].update(expr="up"), "uses neither the site nor the instance variable"),
    "description missing": (lambda d: panel(d).pop("description"), "description missing"),
    "duplicate panel id": (lambda d: panel(d).update(id=1), "duplicate panel id"),
    "old schema": (lambda d: d.update(schemaVersion=30), "schemaVersion"),
    "cah tag missing": (lambda d: d.update(tags=[]), "tag cah missing"),
    "no panels": (lambda d: d.update(panels=[]), "no panels"),
    "title missing": (lambda d: d.pop("title"), "missing title"),
}


def test_the_good_fixture_passes():
    assert problems(GOOD) == []


def test_documentation_addresses_are_allowed():
    d = mutated(lambda d: panel(d).update(description="Example target 192.0.2.21:9100 in site-tor1; also 198.51.100.7 and 203.0.113.9."))
    assert problems(d) == []


@pytest.mark.parametrize("case", sorted(HOSTILE))
def test_each_rule_bites(case):
    mutate, expect = HOSTILE[case]
    found = problems(mutated(mutate))
    assert any(expect in f for f in found), f"{case}: expected a problem containing {expect!r}, got {found}"


def test_duplicate_uid_and_title_are_caught():
    a, b = copy.deepcopy(GOOD), copy.deepcopy(GOOD)
    found = cross_problems([a, b])
    assert "duplicate uid: cah-test" in found and "duplicate title: Test" in found
    b["uid"], b["title"] = "cah-other", "Other"
    assert cross_problems([a, b]) == []
