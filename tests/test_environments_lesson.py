# SPDX-License-Identifier: Apache-2.0
"""The environments and promotion lesson keeps the promises it makes (issue #313).

docs/wiki/Environments-and-Promotion-Dev-Staging-Production.md teaches environments from
this repository's files and marks staging as planned and unbuilt. These tests hold what a
machine can hold: the honest banner, that every repository path it cites exists, that the
numbers it quotes match docs/stages/approved.json, that it stops saying "planned" only when
a staging stack really exists, no real address or credential shape, and the registrations.
Each guard also has a case proving it bites.
"""

import ipaddress
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
PAGE = WIKI / "Environments-and-Promotion-Dev-Staging-Production.md"
NAME = PAGE.name
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
SECRET_SHAPE = re.compile(r"(?i)(password|passwd|token|secret)\s*[:=]\s*(?!\$|<|\{|\.\.\.|')[^\s`]{4,}")
CITED_PATH = re.compile(r"`((?:docs|scripts|stacks|\.spacelift|tests)/[A-Za-z0-9_./*-]+)`")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def real_addresses(body: str) -> list[str]:
    bad = []
    for m in IPV4.findall(body):
        ip = ipaddress.ip_address(m)
        if ip.is_loopback or ip.is_unspecified:
            continue
        if not any(ip in net for net in DOC_NETS):
            bad.append(m)
    return bad


def missing_paths(body: str, root: Path) -> list[str]:
    missing = []
    for p in sorted(set(CITED_PATH.findall(body))):
        if "*" in p:
            if not list(root.glob(p)):
                missing.append(p)
        elif not (root / p).exists():
            missing.append(p)
    return missing


def test_banner_says_written_from_reading_and_staging_is_not_built():
    banner = next(l for l in text().splitlines() if l.startswith("> **"))
    low = banner.lower()
    assert "written from reading" in low
    assert "staging is planned and not built" in low


def test_every_repository_path_it_cites_exists():
    body = text()
    assert len(set(CITED_PATH.findall(body))) >= 8, "the lesson must cite the files it leans on"
    assert missing_paths(body, ROOT) == []


def test_numbers_match_the_cost_file():
    approved = json.loads((ROOT / "docs" / "stages" / "approved.json").read_text())
    body = text()
    current = approved["current_phase"]
    assert f"`{current}`" in body, "the lesson names the current phase"
    assert f"${approved['phases'][current]['ceiling']:.0f} per month" in body
    assert f"${approved['hard_max']:.0f}" in body
    assert "$20 per month" in body


def test_staging_is_still_planned_only_when_no_staging_phase_or_stack_exists():
    approved = json.loads((ROOT / "docs" / "stages" / "approved.json").read_text())
    stacks = [p.name.lower() for p in (ROOT / "stacks").iterdir() if p.is_dir()]
    built = any("staging" in k.lower() for k in approved["phases"]) or any("staging" in s for s in stacks)
    assert not built, "a staging phase or stack now exists: rewrite the lesson's planned-only claims"
    body = text()
    assert "Planned, not built" in body or "**Planned, not built.**" in body
    assert "Staging stack | **Planned, not built**" in body


def test_hook_really_only_trusts_main():
    script = (ROOT / "scripts" / "spacelift" / "doppler-env.sh").read_text()
    assert '"$_branch" != "main"' in script
    assert "is not main; skipping" in script and "is not main; skipping" in text()


def test_no_real_address_and_no_credential_shape():
    body = text()
    assert real_addresses(body) == []
    assert SECRET_SHAPE.findall(body) == []


def test_guards_bite():
    assert real_addresses("host 8.8.8.8 and 192.0.2.5") == ["8.8.8.8"]
    assert SECRET_SHAPE.findall("password: hunter2x") != []
    assert SECRET_SHAPE.findall("token: $DOPPLER_TOKEN") == []
    assert missing_paths("see `docs/does-not-exist.md`", ROOT) == ["docs/does-not-exist.md"]
    assert missing_paths("see `docs/cost.md`", ROOT) == []


def test_registered_everywhere():
    for page in ("_Sidebar.md", "Contents.md", "Reading-Order.md", "Build-and-Destroy-Stack-Per-Service.md"):
        assert NAME in (WIKI / page).read_text(), page
    glossary = (WIKI / "Glossary.md").read_text()
    for term in ("Environment (deployment)", "Promotion", "Staging", "Trunk-based development"):
        assert f"| **{term}** |" in glossary, term
    assert re.search(r"page: Environments-and-Promotion-Dev-Staging-Production,", (WIKI / "_nav.yaml").read_text())
