"""The Wazuh agents dashboard, run against synthetic Wazuh documents.

No Grafana, OpenSearch or Wazuh runs here. This reads dashboards/cah_wazuh_agents.json,
expands its template variables the way Grafana does, evaluates every panel's
Lucene query with a small evaluator against tests/fixtures/wazuh_alerts_synthetic.json
(two invented sites, two connectors each), and checks that:

- every field a panel, variable or table column names exists in the fixture,
  in particular agent.labels.site, the field the agent's <labels> block writes;
- the site variable lists exactly the two sites, and the instance variable
  follows the chosen site;
- choosing one site returns only that site's documents on every panel, and
  "All" returns both, so a second site needs no second dashboard.

What it does NOT prove: that Grafana imports the file, that the OpenSearch
data source plugin sends these queries unchanged, that real OpenSearch parses
them as this evaluator does (it implements only the subset the dashboard uses:
field:value, quoted values, trailing wildcards, AND, OR, parentheses), that
real Wazuh alerts have these field names or types (the fixture is written from
the dashboard's own assumptions plus the Wazuh alert layout as remembered), or
that a real agent produces agent.labels.site. The agent half is covered
separately by tests/test_log_shipping_script.py and the tofu tests.
"""

import copy
import fnmatch
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "dashboards" / "cah_wazuh_agents.json"
FIXTURE = ROOT / "tests" / "fixtures" / "wazuh_alerts_synthetic.json"
SITES = ["site-tor1", "site-tor2"]
SITE_FIELD = "agent.labels.site"

TOKEN = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+)')


def load_dashboard():
    return json.loads(DASHBOARD.read_text(encoding="utf-8"))


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def values_at(doc, path):
    """Every value at a dotted path; lists are searched element by element."""
    nodes = [doc]
    for part in path.split("."):
        nxt = []
        for n in nodes:
            if isinstance(n, list):
                nxt.extend(x.get(part) for x in n if isinstance(x, dict) and part in x)
            elif isinstance(n, dict) and part in n:
                nxt.append(n[part])
        nodes = nxt
    out = []
    for n in nodes:
        out.extend(n if isinstance(n, list) else [n])
    return out


def has_field(docs, path):
    return any(values_at(d, path) for d in docs)


def tokenize(query):
    pos, out = 0, []
    while pos < len(query):
        m = TOKEN.match(query, pos)
        if not m:
            break
        out.append(m.group(1))
        pos = m.end()
    return out


def unquote(tok):
    if tok.startswith('"'):
        return re.sub(r"\\(.)", r"\1", tok[1:-1])
    return re.sub(r"\\(.)", r"\1", tok)


class Parser:
    """field:value, AND, OR and parentheses. AND binds tighter than OR."""

    def __init__(self, query):
        self.t = tokenize(query)
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def parse(self):
        node = self.or_expr()
        assert self.peek() is None, f"unparsed tail: {self.t[self.i:]}"
        return node

    def or_expr(self):
        parts = [self.and_expr()]
        while self.peek() == "OR":
            self.take()
            parts.append(self.and_expr())
        return ("or", parts) if len(parts) > 1 else parts[0]

    def and_expr(self):
        parts = [self.atom()]
        while self.peek() == "AND":
            self.take()
            parts.append(self.atom())
        return ("and", parts) if len(parts) > 1 else parts[0]

    def atom(self):
        if self.peek() == "(":
            self.take()
            node = self.or_expr()
            assert self.take() == ")", "missing )"
            return node
        tok = self.take()
        assert tok is not None and ":" in tok, f"expected field:value, got {tok!r}"
        field, _, rest = tok.partition(":")
        if rest == "":
            # field:( "a" OR "b" ) as Grafana's lucene format writes a multi-value
            assert self.take() == "(", "expected ( after field:"
            vals = [unquote(self.take())]
            while self.peek() == "OR":
                self.take()
                vals.append(unquote(self.take()))
            assert self.take() == ")", "missing ) after value list"
            return ("field", field, vals)
        return ("field", field, [unquote(rest)])


def matches(node, doc):
    kind = node[0]
    if kind == "and":
        return all(matches(n, doc) for n in node[1])
    if kind == "or":
        return any(matches(n, doc) for n in node[1])
    _, field, pats = node
    found = values_at(doc, field)
    return any(fnmatch.fnmatchcase(str(v), p) for v in found for p in pats)


def run_query(query, docs):
    node = Parser(query).parse()
    return [d for d in docs if matches(node, d)]


def lucene(values):
    """Grafana's :lucene format: one quoted value, or ("a" OR "b")."""
    q = ['"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"' for v in values]
    return q[0] if len(q) == 1 else "(" + " OR ".join(q) + ")"


def expand(query, selected):
    def sub(m):
        return lucene(selected[m.group(1)])

    return re.sub(r"\$\{(\w+):lucene\}", sub, query)


def terms(docs, field, query="*"):
    pool = docs if query == "*" else run_query(query, docs)
    return sorted({str(v) for d in pool for v in values_at(d, field)})


def variable_terms(var, alerts, monitoring, selected):
    """What a `find: terms` variable returns, including its optional filter."""
    spec = json.loads(var["query"])
    docs = monitoring if "MONITORING" in var["datasource"]["uid"] else alerts
    q = expand(spec["query"], selected) if "query" in spec else "*"
    return terms(docs, spec["field"], q)


def panel_targets(dash):
    for p in dash["panels"]:
        for t in p.get("targets", []):
            yield p, t


def all_selected(dash, alerts, monitoring):
    sel = {}
    for var in dash["templating"]["list"]:
        if var["type"] == "query":
            sel[var["name"]] = variable_terms(var, alerts, monitoring, sel)
    return sel


def field_refs(dash):
    """(panel id, field) for every field the dashboard reads."""
    refs = set()
    field = re.compile(r"(?<![\w.{$])([A-Za-z@][\w@.]*):(?=[\"(\\$A-Za-z0-9*])")
    for p, t in panel_targets(dash):
        for f in field.findall(t["query"]):
            refs.add((p["id"], f))
        for m in t.get("metrics", []):
            if m.get("field"):
                refs.add((p["id"], m["field"]))
        for b in t.get("bucketAggs", []):
            if b.get("field"):
                refs.add((p["id"], b["field"]))
        for tr in p.get("transformations", []):
            for k in tr.get("options", {}).get("includeByName", {}):
                refs.add((p["id"], k))
    for var in dash["templating"]["list"]:
        if var["type"] == "query":
            spec = json.loads(var["query"])
            refs.add((var["name"], spec["field"]))
            for f in field.findall(spec.get("query", "")):
                refs.add((var["name"], f))
    return refs


def monitoring_panel(p):
    return any("MONITORING" in t["datasource"]["uid"] for t in p.get("targets", []))


def field_problems(dash, alerts, monitoring):
    out = []
    for owner, f in sorted(field_refs(dash), key=str):
        mon = (
            monitoring_panel(next(p for p in dash["panels"] if p["id"] == owner))
            if isinstance(owner, int)
            else owner == "monitored_agent"
        )
        if not has_field(monitoring if mon else alerts, f):
            out.append(f"{owner}: field {f!r} is in no {'monitoring' if mon else 'alert'} document")
    return out


# --- tests ---------------------------------------------------------------------


def test_the_fixture_has_two_synthetic_sites_and_the_site_field():
    fx = load_fixture()
    assert terms(fx["alerts"], SITE_FIELD) == SITES
    assert all(values_at(a, SITE_FIELD) for a in fx["alerts"]), "an alert without the site label"


def test_every_field_the_dashboard_reads_exists_in_the_synthetic_documents():
    dash, fx = load_dashboard(), load_fixture()
    refs = field_refs(dash)
    assert (2, SITE_FIELD) in refs
    assert {"agent.name", "rule.groups", "syscheck.path", "syscheck.event", "rule.level", "lastKeepAlive", "status"} <= {
        f for _, f in refs
    }, "the field collector found too little"
    assert field_problems(dash, fx["alerts"], fx["monitoring"]) == []


def test_the_site_variable_lists_both_sites_and_the_instance_variable_follows_it():
    dash, fx = load_dashboard(), load_fixture()
    variables = {v["name"]: v for v in dash["templating"]["list"]}
    assert variable_terms(variables["site"], fx["alerts"], fx["monitoring"], {}) == SITES
    for site in SITES:
        inst = variable_terms(variables["instance"], fx["alerts"], fx["monitoring"], {"site": [site]})
        assert inst == [f"{site}-connector-a", f"{site}-connector-b"]
    assert "allValue" not in variables["site"] and "allValue" not in variables["instance"], (
        "an allValue would change what All expands to; this evaluator assumes Grafana's default"
    )


def test_every_alert_panel_returns_data_for_each_site_and_only_that_site():
    dash, fx = load_dashboard(), load_fixture()
    alerts, mon = fx["alerts"], fx["monitoring"]
    allsel = all_selected(dash, alerts, mon)
    checked = 0
    for p, t in panel_targets(dash):
        if monitoring_panel(p):
            continue
        for site in SITES:
            sel = dict(allsel, site=[site], instance=terms(alerts, "agent.name", f"{SITE_FIELD}:{lucene([site])}"))
            rows = run_query(expand(t["query"], sel), alerts)
            assert rows, f"panel {p['id']} ({p['title']}) returns nothing for {site}"
            assert {values_at(r, SITE_FIELD)[0] for r in rows} == {site}, f"panel {p['id']} leaks another site"
            checked += 1
        both = run_query(expand(t["query"], allsel), alerts)
        assert {values_at(r, SITE_FIELD)[0] for r in both} == set(SITES), f"panel {p['id']}: All misses a site"
    assert checked >= 16, f"only {checked} panel/site checks ran"


def test_a_site_filter_with_an_instance_of_another_site_returns_nothing():
    dash, fx = load_dashboard(), load_fixture()
    t = next(t for p, t in panel_targets(dash) if p["id"] == 4)
    sel = {"site": ["site-tor1"], "instance": ["site-tor2-connector-a"]}
    assert run_query(expand(t["query"], sel), fx["alerts"]) == []


def test_the_file_integrity_panels_keep_only_paths_under_etc_twingate():
    dash, fx = load_dashboard(), load_fixture()
    allsel = all_selected(dash, fx["alerts"], fx["monitoring"])
    t = next(t for p, t in panel_targets(dash) if p["id"] == 12)
    rows = run_query(expand(t["query"], allsel), fx["alerts"])
    assert rows and all(values_at(r, "syscheck.path")[0].startswith("/etc/twingate/") for r in rows)
    assert any(values_at(a, "syscheck.path") == ["/etc/hosts"] for a in fx["alerts"]), "no decoy path in the fixture"


def test_the_monitoring_panel_reads_the_monitoring_documents():
    dash, fx = load_dashboard(), load_fixture()
    mon = fx["monitoring"]
    var = next(v for v in dash["templating"]["list"] if v["name"] == "monitored_agent")
    names = variable_terms(var, fx["alerts"], mon, {})
    assert len(names) == 4
    t = next(t for p, t in panel_targets(dash) if p["id"] == 3)
    rows = run_query(expand(t["query"], {"monitored_agent": names}), mon)
    assert {r["status"] for r in rows} == {"active", "disconnected"}


# --- negative cases: the checks above bite -------------------------------------


def test_negative_alerts_without_the_site_label_are_reported_and_return_nothing():
    dash, fx = load_dashboard(), load_fixture()
    bare = copy.deepcopy(fx["alerts"])
    for a in bare:
        del a["agent"]["labels"]
    assert any("agent.labels.site" in p for p in field_problems(dash, bare, fx["monitoring"]))
    t = next(t for p, t in panel_targets(dash) if p["id"] == 2)
    assert run_query(expand(t["query"], {"site": SITES, "instance": ["x"]}), bare) == []


def test_negative_a_panel_on_a_renamed_field_is_reported():
    dash, fx = load_dashboard(), load_fixture()
    broken = copy.deepcopy(dash)
    for _, t in panel_targets(broken):
        t["query"] = t["query"].replace(SITE_FIELD, "agent.labels.siteX")
    problems = field_problems(broken, fx["alerts"], fx["monitoring"])
    assert any("siteX" in p for p in problems)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ('agent.labels.site:"site-tor1"', 10),
        ('agent.labels.site:("site-tor1" OR "site-tor2")', 20),
        ('agent.labels.site:"site-tor1" AND rule.groups:sudo', 2),
        ("rule.groups:sshd OR rule.groups:sudo", 12),
        ('syscheck.path:\\/etc\\/twingate\\/*', 4),
        ('agent.labels.site:"nope"', 0),
    ],
)
def test_the_lucene_evaluator_behaves_on_known_queries(query, expected):
    assert len(run_query(query, load_fixture()["alerts"])) == expected
