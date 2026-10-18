"""Checks for the importable Grafana dashboards in dashboards/.

The dashboards are shared, so they must carry no real endpoint. These tests
keep that true: every data source is a template variable (no literal uid or
data source name anywhere in the model), no query holds a URL, no address
outside the documentation ranges (IPv4 or IPv6) appears, no host:port string
or bare host name appears, and every dashboard has the `site` and `instance`
variables. The rules live in `problems()` and `cross_problems()`; a hostile
fixture per rule proves each one fails when it should (a guard that never
fails guards nothing).

What this proves and what it does not: the checks are structural and offline.
They cannot prove a file imports into Grafana (no Grafana runs here), that a
query is valid PromQL or Lucene, or that it returns data. `schemaVersion` is
only a floor that says "not an ancient export"; the panel type allowlist and
the gridPos, refId and query checks catch common breakage, nothing more.
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
DOC_V6 = ipaddress.ip_network("2001:db8::/32")
IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
DS_VAR = re.compile(r"^\$\{DS_[A-Z0-9_]+\}$")
URL = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://")
MIN_SCHEMA = 41  # a structural floor for Grafana 12.x exports, not proof of importability
# Panel types the dashboards use. A type outside this list is a typo or an
# unreviewed plugin (a plugin panel would also fail an import without it).
PANEL_TYPES = {"row", "stat", "gauge", "table", "timeseries", "state-timeline", "piechart", "bargauge", "text"}
# Variables a query may use to scope itself. `instance` is itself filtered by
# site; `monitored_agent` is the Wazuh monitoring index's own agent list.
SCOPE_VARS = ("site", "instance", "monitored_agent")
_SCOPE_ALT = "|".join(SCOPE_VARS)
SITE_REF = re.compile(rf"\$(?:{_SCOPE_ALT})\b|\$\{{(?:{_SCOPE_ALT})[:}}]")
# Names that may appear in text: documentation hosts and loopback.
ALLOWED_HOST = re.compile(r"(?:^|\.)(?:example\.(?:com|net|org)|localhost)$", re.IGNORECASE)
# A bare host name: dotted labels ending in a TLD a real host would use.
# Dotted field names (agent.name, rule.groups, syscheck.path) are not hosts.
TLDS = "com|net|org|io|co|uk|dev|app|cloud|local|lan|internal|home|corp|intranet|ca|us|de|eu|info|biz|xyz|ai|me|tv"
HOSTNAME = re.compile(rf"(?<![\w.-])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+(?:{TLDS})(?![\w-])", re.IGNORECASE)
HOST_PORT = re.compile(r"(?<![\w.-])(?=[\w.-]*[A-Za-z.])[\w.-]+:\d{2,5}(?![\w])")
IPV6_CANDIDATE = re.compile(r"(?<![\w:])[0-9A-Fa-f:]{3,}(?![\w:])")
BY_LIST = re.compile(r"\bby\s*\(([^)]*)\)")
RATE_PLUS_RATE = re.compile(r"\)\s*\+\s*rate\(")


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


def walk_keys(node, key, path="$"):
    """Yield (path, value) for every key with this name, at any depth."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                yield f"{path}.{k}", v
            yield from walk_keys(v, key, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_keys(v, key, f"{path}[{i}]")


def ds_error(ds):
    """None when ds is a {type, uid: ${DS_*}} reference, else why not."""
    if not isinstance(ds, dict) or not isinstance(ds.get("uid"), str) or not DS_VAR.match(ds["uid"]):
        return f"datasource is not a ${{DS_*}} variable: {ds!r}"
    return None


def address_findings(path, s):
    out = []
    for m in IPV4.finditer(s):
        try:
            ip = ipaddress.ip_address(m.group(0))
        except ValueError:
            out.append(f"{path}: malformed address {m.group(0)}")
            continue
        if not any(ip in net for net in DOC_RANGES):
            out.append(f"{path}: address {ip} is outside the documentation ranges")
    for m in IPV6_CANDIDATE.finditer(s):
        if m.group(0).count(":") < 2:
            continue
        try:
            ip = ipaddress.ip_address(m.group(0))
        except ValueError:
            continue  # a time such as 12:30:45 is not an address
        if ip.version == 6 and ip not in DOC_V6:
            out.append(f"{path}: IPv6 address {ip} is outside 2001:db8::/32")
    for m in HOST_PORT.finditer(s):
        host = m.group(0).rsplit(":", 1)[0]
        try:
            ipaddress.ip_address(host)
            continue  # an address:port is judged by the address rules above
        except ValueError:
            pass
        if not ALLOWED_HOST.search(host):
            out.append(f"{path}: host:port string {m.group(0)!r}")
    for m in HOSTNAME.finditer(s):
        if not ALLOWED_HOST.search(m.group(0)):
            out.append(f"{path}: host name {m.group(0)!r} (only example.com, example.net, example.org and localhost are allowed)")
    return out


def problems(d: dict) -> list[str]:
    out = []
    for key in ("uid", "title", "schemaVersion", "panels"):
        if key not in d:
            out.append(f"missing {key}")
    if out:
        return out
    if not isinstance(d["schemaVersion"], int) or d["schemaVersion"] < MIN_SCHEMA:
        out.append(f"schemaVersion {d['schemaVersion']!r} is below the floor {MIN_SCHEMA}")
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
        err = ds_error(ds)
        if err:
            out.append(f"{where}: {err}")
        elif ds["uid"][2:-1] not in ds_vars:
            out.append(f"{where}: datasource variable {ds['uid']} is not declared")

    for v in variables:
        if v.get("type") == "query":
            ds_ok(v.get("datasource"), f"variable {v.get('name')}")

    # A literal uid anywhere (including inside a panel option) is a leak.
    for path, value in walk_keys(d, "uid"):
        if path == "$.uid":
            continue
        if not (isinstance(value, str) and DS_VAR.match(value)):
            out.append(f"{path}: literal uid {value!r}")
    # So is a literal data source reference of any shape, at any depth.
    for path, value in walk_keys(d, "datasource"):
        if isinstance(value, dict):
            err = ds_error(value)
            if err:
                out.append(f"{path}: {err}")
        elif not (isinstance(value, str) and DS_VAR.match(value)):
            out.append(f"{path}: literal datasource {value!r}")
    # A `name` key only belongs to a template variable (a data source or host
    # name hides in one of these); elsewhere in the model it is a leak.
    var_paths = {f"$.templating.list[{i}].name" for i in range(len(variables))}
    for path, value in walk_keys(d, "name"):
        if path not in var_paths:
            out.append(f"{path}: literal name {value!r} outside a template variable")

    seen_ids = set()
    for p in walk_panels(d["panels"]):
        title = p.get("title", "?")
        if p.get("id") in seen_ids:
            out.append(f"{title}: duplicate panel id {p.get('id')}")
        seen_ids.add(p.get("id"))
        if p.get("type") not in PANEL_TYPES:
            out.append(f"{title}: panel type {p.get('type')!r} is not in the allowlist")
        gp = p.get("gridPos")
        if not (isinstance(gp, dict) and all(isinstance(gp.get(k), int) and gp[k] >= 0 for k in ("h", "w", "x", "y"))
                and gp["w"] >= 1 and gp["h"] >= 1 and gp["x"] + gp["w"] <= 24):
            out.append(f"{title}: gridPos missing or out of the 24 column grid: {gp!r}")
        if p.get("type") == "row":
            continue
        if len((p.get("description") or "").strip()) < 40:
            out.append(f"{title}: description missing or too short")
        ds_ok(p.get("datasource"), title)
        if not p.get("targets"):
            out.append(f"{title}: no targets")
        refs = [t.get("refId") for t in p.get("targets", [])]
        if len(set(refs)) != len(refs):
            out.append(f"{title}: duplicate refIds {refs}")
        for t in p.get("targets", []):
            where = f"{title} target {t.get('refId')}"
            if not t.get("refId"):
                out.append(f"{where}: no refId")
            ds_ok(t.get("datasource"), where)
            query = t.get("expr") or t.get("query") or ""
            if not query:
                out.append(f"{where}: empty query")
            elif not SITE_REF.search(query):
                out.append(f"{where}: query uses none of the scoping variables {SCOPE_VARS}")
            if RATE_PLUS_RATE.search(query):
                out.append(f"{where}: adds two rate() vectors directly; aggregate each side first (unmatched series vanish silently)")
            # Two scrape endpoints of one host share site and instance, so
            # anything per instance must also keep the endpoint label.
            legend = t.get("legendFormat") or ""
            if "{{instance}}" in legend and "{{endpoint}}" not in legend:
                out.append(f"{where}: legend names the instance but not the endpoint")
            for by in BY_LIST.findall(query):
                labels = [x.strip() for x in by.split(",")]
                if "instance" in labels and "endpoint" not in labels:
                    out.append(f"{where}: aggregates by instance without endpoint")

    for path, s in walk_strings(d):
        if URL.search(s):
            out.append(f"{path}: contains a URL")
        out += address_findings(path, s)
    return out


def cross_problems(dashboards: list[dict]) -> list[str]:
    out = []
    for key in ("uid", "title"):
        values = [d[key] for d in dashboards]
        out += [f"duplicate {key}: {v}" for v in sorted({v for v in values if values.count(v) > 1})]
    return out


def load_all():
    return {p.name: json.loads(p.read_text()) for p in sorted(DASHBOARDS.glob("*.json"))}


def queries(d, title):
    return [t.get("expr") or t.get("query") or "" for p in walk_panels(d["panels"]) if p.get("title") == title
            for t in p.get("targets", [])]


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


def test_files_use_no_em_or_en_dash():
    for name in load_all():
        text = (DASHBOARDS / name).read_text()
        assert "—" not in text and "–" not in text, f"{name}: em or en dash"


def test_wazuh_panels_with_unverified_fields_say_so():
    d = load_all()["cah_wazuh_agents.json"]
    panels = [p for p in walk_panels(d["panels"]) if p["type"] != "row"]
    assert panels
    for p in panels:
        assert "UNVERIFIED" in p["description"], f"{p['title']}: field names not marked UNVERIFIED"


def test_wazuh_status_panel_is_not_filtered_by_alert_derived_agents():
    """Quiet or never-reporting agents are only in the monitoring index, so that
    panel must not use the instance variable (built from alerts)."""
    d = load_all()["cah_wazuh_agents.json"]
    qs = queries(d, "Agent status and last keepalive")
    assert qs, "status panel not found"
    for q in qs:
        assert "monitored_agent" in q and "instance" not in q and "agent.labels.site" not in q
    var = {v["name"]: v for v in d["templating"]["list"]}["monitored_agent"]
    assert var["datasource"]["uid"] == "${DS_OPENSEARCH_MONITORING}"


def test_sites_up_and_down_start_from_the_expected_target_inventory():
    d = load_all()["cah_sites_overview.json"]
    for title in ("Targets up per site", "Targets down per site"):
        qs = queries(d, title)
        assert qs and all("cah_expected_targets" in q for q in qs), f"{title}: does not use the inventory"
    assert "or on (site)" in queries(d, "Targets up per site")[0], "a fully down site needs an explicit 0"


def test_relay_share_aggregates_each_direction_before_combining():
    d = load_all()["cah_sites_overview.json"]
    (q,) = queries(d, "Share of traffic through a relay")
    assert not RATE_PLUS_RATE.search(q)
    assert q.count("sum by (site) (rate(") == 4, "inbound and outbound, relay and total, each summed by site"
    assert q.count("or on (site)") >= 4, "each side needs explicit missing-series handling"


def test_every_prometheus_panel_scopes_node_series_to_their_endpoint():
    d = load_all()["cah_droplet_health.json"]
    for p in walk_panels(d["panels"]):
        for t in p.get("targets", []):
            assert 'endpoint="node-exporter"' in t["expr"], f"{p['title']}: node series not scoped to the node exporter endpoint"


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
        {"id": 1, "type": "row", "title": "Row", "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0}, "panels": []},
        {"id": 2, "type": "stat", "title": "Up", "description": "Shows how many targets answered the last scrape, per site.",
         "gridPos": {"h": 8, "w": 12, "x": 0, "y": 1},
         "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
         "targets": [{"refId": "A", "expr": 'sum by (site, instance, endpoint) (up{site=~"$site"})',
                      "legendFormat": "{{site}} / {{instance}} / {{endpoint}}",
                      "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"}}]},
    ],
}


def mutated(fn):
    d = copy.deepcopy(GOOD)
    fn(d)
    return d


def panel(d):
    return d["panels"][1]


def with_option(d, key, value):
    panel(d).setdefault("options", {})[key] = value


HOSTILE = {
    "literal panel datasource uid": (lambda d: panel(d)["datasource"].update(uid="abc123XYZ"), "not a ${DS_*}"),
    "literal target datasource uid": (lambda d: panel(d)["targets"][0]["datasource"].update(uid="abc123XYZ"), "not a ${DS_*}"),
    "undeclared datasource variable": (lambda d: panel(d)["datasource"].update(uid="${DS_OTHER}"), "not declared"),
    "datasource missing": (lambda d: panel(d).pop("datasource"), "not a ${DS_*}"),
    "literal uid hidden in an option": (lambda d: with_option(d, "x", {"uid": "P1234567"}), "literal uid"),
    "literal datasource name string in an option": (lambda d: with_option(d, "datasource", "Prometheus-Main"), "literal datasource"),
    "literal datasource object nested in an override": (
        lambda d: panel(d).update(fieldConfig={"overrides": [{"properties": [{"id": "x", "value": {"datasource": {"type": "prometheus", "uid": "zzz"}}}]}]}),
        "not a ${DS_*}"),
    "literal name hidden in an option": (lambda d: with_option(d, "source", {"name": "siem-prod"}), "literal name"),
    "url in a query": (lambda d: panel(d)["targets"][0].update(expr='up{site=~"$site"} # http://prom.example.net:9090'), "URL"),
    "url in a description": (lambda d: panel(d).update(description="See https://grafana.example.net/d/abc for the live one."), "URL"),
    "real public address": (lambda d: panel(d).update(description="Shows the target at 8.8.8.8 that answered the last scrape."), "outside the documentation"),
    "real private address": (lambda d: panel(d)["targets"][0].update(expr='up{site=~"$site", instance="10.0.0.5"}'), "outside the documentation"),
    "address in a variable": (lambda d: d["templating"]["list"][1].update(query="label_values(up{instance=\"172.16.4.9\"}, site)"), "outside the documentation"),
    "real ipv6 address": (lambda d: panel(d).update(description="Shows the target at 2001:4860:4860::8888 that answered the last scrape."), "IPv6"),
    "ipv6 loopback": (lambda d: panel(d).update(description="Shows the target at ::1 that answered the last scrape, per site."), "IPv6"),
    "host:port with a name": (lambda d: panel(d)["targets"][0].update(expr='up{site=~"$site", instance="grafana-prod:3000"}'), "host:port"),
    "host:port with a real host": (lambda d: panel(d).update(description="Scrape of prom01.mylab.net:9090 answered the last scrape, per site."), "host"),
    "bare host name": (lambda d: panel(d).update(description="Shows how siem.mylab.net answered the last scrape, per site and instance."), "host name"),
    "bare internal host name": (lambda d: panel(d).update(description="Shows how nas01.home answered the last scrape, per site and instance."), "host name"),
    "site variable missing": (lambda d: d["templating"]["list"].pop(1), "variable site missing"),
    "instance variable missing": (lambda d: d["templating"]["list"].pop(2), "variable instance missing"),
    "site variable single-value": (lambda d: d["templating"]["list"][1].update(multi=False), "not multi-value"),
    "query ignores scoping variables": (lambda d: panel(d)["targets"][0].update(expr="up"), "none of the scoping variables"),
    "description missing": (lambda d: panel(d).pop("description"), "description missing"),
    "duplicate panel id": (lambda d: panel(d).update(id=1), "duplicate panel id"),
    "old schema": (lambda d: d.update(schemaVersion=30), "schemaVersion"),
    "cah tag missing": (lambda d: d.update(tags=[]), "tag cah missing"),
    "no panels": (lambda d: d.update(panels=[]), "no panels"),
    "title missing": (lambda d: d.pop("title"), "missing title"),
    "panel type outside the allowlist": (lambda d: panel(d).update(type="vendor-fancy-panel"), "allowlist"),
    "gridPos missing": (lambda d: panel(d).pop("gridPos"), "gridPos"),
    "gridPos off the grid": (lambda d: panel(d)["gridPos"].update(x=20, w=12), "gridPos"),
    "target without refId": (lambda d: panel(d)["targets"][0].pop("refId"), "no refId"),
    "target without a query": (lambda d: panel(d)["targets"][0].pop("expr"), "empty query"),
    "duplicate refIds in a panel": (lambda d: panel(d)["targets"].append(copy.deepcopy(panel(d)["targets"][0])), "duplicate refIds"),
    "two rates added before aggregating": (
        lambda d: panel(d)["targets"][0].update(expr='sum by (site) (rate(a{site=~"$site"}[5m]) + rate(b{site=~"$site"}[5m]))'),
        "adds two rate()"),
    "legend names the instance without the endpoint": (lambda d: panel(d)["targets"][0].update(legendFormat="{{site}} / {{instance}}"), "not the endpoint"),
    "aggregation by instance drops the endpoint": (
        lambda d: panel(d)["targets"][0].update(expr='sum by (site, instance) (up{site=~"$site"})'), "without endpoint"),
}


def test_the_good_fixture_passes():
    assert problems(GOOD) == []


def test_documentation_values_are_allowed():
    d = mutated(lambda d: panel(d).update(
        description="Example target 192.0.2.21:9100 in site-tor1; also 198.51.100.7, 203.0.113.9, 2001:db8::21 and "
                    "prom.example.com or grafana.example.net or localhost, at 12:30:45 on a quiet day."))
    assert problems(d) == []


def test_dotted_field_names_are_not_host_names():
    d = mutated(lambda d: panel(d).update(
        description="Filters on agent.labels.site, rule.groups, syscheck.path and agent.name, which are field names."))
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
