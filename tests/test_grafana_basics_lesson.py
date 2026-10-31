# SPDX-License-Identifier: Apache-2.0
"""The Grafana basics lesson keeps the promises it makes (issue #322).

docs/wiki/Grafana-Basics-From-a-Blank-Page.md is written from reading the Grafana
documentation, not from a run. These tests hold what a machine can hold: the honest status
banner, the claims register with a date per Grafana page, no real address or credential
shape, the lab commands it quotes exist, and the registrations (navigation, reading order,
glossary, and the page it extends). Each guard also has a case proving it bites.
"""

import ipaddress
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
PAGE = WIKI / "Grafana-Basics-From-a-Blank-Page.md"
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
SECRET_SHAPE = re.compile(r"(?i)(password|passwd|token|secret)\s*[:=]\s*(?!\$|<|\{|\.\.\.|')[^\s`]{4,}")
GRAFANA_DOC = re.compile(r"https://grafana\.com/docs/[^\s)|]+")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def real_addresses(body: str) -> list[str]:
    bad = []
    for m in IPV4.findall(body):
        try:
            ip = ipaddress.ip_address(m)
        except ValueError:
            continue
        if ip.is_loopback or ip.is_unspecified:
            continue
        if not any(ip in net for net in DOC_NETS):
            bad.append(m)
    return bad


def register_rows(body: str) -> list[str]:
    section = body.split("## Claims register", 1)[1]
    return [l for l in section.splitlines() if l.startswith("|") and "grafana.com/docs" in l]


def test_page_exists_and_opens_with_an_honest_status_banner():
    body = text()
    banner = next(l for l in body.splitlines() if l.startswith("> **"))
    assert "written from reading" in banner.lower()
    assert "not run" in banner.lower()


def test_every_grafana_doc_url_in_the_page_has_a_dated_register_row():
    body = text()
    rows = register_rows(body)
    assert len(rows) >= 8, "the register must cover the pages the lesson leans on"
    for row in rows:
        assert re.search(r"2026-10-30", row), row
        assert "Read" in row, row
    urls = set(GRAFANA_DOC.findall(body))
    registered = set(GRAFANA_DOC.findall("\n".join(rows)))
    assert urls <= registered, urls - registered


def test_no_real_address_and_no_credential_shape():
    body = text()
    assert real_addresses(body) == []
    assert SECRET_SHAPE.findall(body) == []


def test_guards_bite():
    assert real_addresses("host 8.8.8.8 and 192.0.2.5") == ["8.8.8.8"]
    assert SECRET_SHAPE.findall("password: hunter2x") != []
    assert SECRET_SHAPE.findall("password: $DB_PASSWORD") == []


def test_quoted_lab_commands_exist_in_the_lab_script():
    script = (ROOT / "scripts" / "demo_monitoring.sh").read_text()
    for cmd in re.findall(r"scripts/demo_monitoring\.sh ([a-z-]+)", text()):
        assert re.search(rf"\b{re.escape(cmd)}\)", script), cmd


def test_the_query_it_teaches_uses_only_the_labs_job_and_metric():
    body = text()
    assert 'sum by (site) (1 - up{job="twingate-ztna"})' in body
    assert 'job_name: twingate-ztna' in (ROOT / "labs/demo-monitoring/prometheus/prometheus.yml").read_text()


def test_registered_everywhere():
    assert "Grafana-Basics-From-a-Blank-Page.md" in (WIKI / "_Sidebar.md").read_text()
    assert "Grafana-Basics-From-a-Blank-Page.md" in (WIKI / "Contents.md").read_text()
    assert "Grafana-Basics-From-a-Blank-Page.md" in (WIKI / "Reading-Order.md").read_text()
    assert "Grafana-Basics-From-a-Blank-Page.md" in (WIKI / "Grafana-Dashboards.md").read_text()
    glossary = (WIKI / "Glossary.md").read_text()
    for term in ("Contact point", "Pending period", "Provisioning (Grafana)", "Read-only database user", "Save & test"):
        assert f"| **{term}** |" in glossary, term
