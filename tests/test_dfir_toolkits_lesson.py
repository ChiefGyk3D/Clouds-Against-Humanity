# SPDX-License-Identifier: Apache-2.0
"""The DFIR toolkits and live triage lesson: registered, honest about what was run, and dated (issue #478).

docs/wiki/DFIR-Toolkits-and-Live-Triage-SIFT-Velociraptor-KAPE-and-the-Incident-Response-Workflow.md compares six
toolkits from their owners' pages, teaches live triage against dead-box imaging, and runs a triage exercise on a machine
the learner owns. A broken link, a missing registration, a license claim with no status, a real address, or a collection
command that writes outside the learner's own folder would each teach the wrong thing.
"""

import re
from pathlib import Path

from wikitext import page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "DFIR-Toolkits-and-Live-Triage-SIFT-Velociraptor-KAPE-and-the-Incident-Response-Workflow"
PAGE = WIKI / f"{NAME}.md"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
FENCE = re.compile(r"```bash\n(.*?)```", re.DOTALL)
STATUS_WORDS = ("Read", "Run", "Page read", "**est.**")


def text() -> str:
    return page_text(PAGE)


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def heading_slugs(body: str) -> set[str]:
    return {re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-") for h in re.findall(r"^#+ (.+)$", body, re.MULTILINE)}


def test_the_page_exists_and_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# DFIR toolkits and live triage")
    assert "Status: unverified draft" in body
    assert "**Not run:**" in body and "2026-11-07" in body
    assert "Not verified, plainly" in body


def test_every_linked_wiki_page_exists_and_the_four_named_pages_are_linked():
    links = set(LINK.findall(text()))
    assert len(links) >= 8, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing
    for page in ("Build-Your-Own-Mini-SOC", "Logs-SIEM-and-Detection-Basics", "Backups-Recovery-and-Patching", "Careers-Roles-and-What-to-Learn-Next"):
        assert page in links, page


def test_the_lesson_is_registered_everywhere():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    entry = nav.split(f"page: {NAME},")[1].split("\n")[0]
    assert 'status: "draft"' in entry and 'subgroup: "Digital forensics"' in entry
    for special in ("Contents.md", "_Sidebar.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [l for l in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in l]
    assert len(rows) >= 5, "expected glossary rows for the new terms"


def test_glossary_rows_point_at_real_headings():
    heads = heading_slugs(text())
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_no_addresses_and_no_em_dashes():
    body = text()
    assert "—" not in body
    assert not ADDR.findall(body), ADDR.findall(body)
    assert ADDR.findall("ping 192.0.2.7"), "the address guard does not bite"


def test_every_claims_register_row_has_a_status():
    body = text()
    assert len(register_rows(body)) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(body)


def test_the_status_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | Y | trust me |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_toolkit_table_names_every_tool_and_the_closed_ones_are_marked():
    body = text()
    section = body.split("## The toolkits at a glance")[1].split("## Live triage and dead-box imaging")[0]
    for tool in ("SIFT Workstation", "CAINE", "Velociraptor", "KAPE", "FTK Imager", "plaso"):
        assert tool in section, tool
    assert section.count("**not open source**") >= 2
    assert "AGPL-3.0" in section and "Apache-2.0" in section and "2026-11-07" in section


def test_the_nist_account_names_both_revisions():
    section = text().split("## An incident response workflow, and where forensics fits")[1].split("## Mobile and cloud forensics")[0]
    for needle in ("Revision 2", "Revision 3", "April 2025", "Govern", "lessons learned"):
        assert needle.lower() in section.lower(), needle


def test_certifications_carry_no_prices_and_no_affiliate_links():
    section = text().split("## Training and certifications")[1].split("## Free exercise")[0]
    assert not re.search(r"[$€£]\s?\d|\bUSD\b", section)
    assert "http" not in section and "ref=" not in section
    assert "GCFE" in section and "GCFA" in section


def test_the_exercise_collects_only_into_the_learners_own_folder_and_never_removes_a_crontab():
    cmds = "\n".join(FENCE.findall(text()))
    assert "collect.sh" in cmds and "sha256sum -c" in cmds, "the guard collected nothing"
    assert "crontab -r" not in cmds and "sudo rm" not in cmds
    assert "mkdir -p ~/triage-lab" in cmds
    assert not re.search(r">\s*/(etc|usr|var|bin)/", cmds)
