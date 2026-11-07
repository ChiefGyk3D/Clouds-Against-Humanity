# SPDX-License-Identifier: Apache-2.0
"""The cron, systemd timers and init scripts lesson: registered, honest about what was run, and safe to follow (issue #457).

docs/wiki/Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd.md teaches a crontab line, a timer pair, a translation table
and a dated account of which distributions install cron. A broken link, a missing registration, a distro claim with no
source or an **est.** mark, a real address, or a weekly translation that is wrong would each teach the wrong thing.
"""

import re
from pathlib import Path

from wikitext import page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd"
PAGE = WIKI / f"{NAME}.md"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
STATUS_WORDS = ("Read", "Run", "Observed", "**est.**", "Statement of opinion")


def text() -> str:
    return page_text(PAGE)


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def heading_slugs(body: str) -> set[str]:
    slugs = set()
    for h in re.findall(r"^#+ (.+)$", body, re.MULTILINE):
        s = re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-")
        slugs.add(s)
    return slugs


def test_the_page_exists_and_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Cron, systemd timers, and init scripts versus systemd")
    assert "Status: unverified draft" in body
    assert "I did not start a timer" in body and "did not edit a crontab" in body
    assert "2026-11-07" in body
    assert "Not verified, plainly" in body


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 5, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_the_lesson_is_registered_everywhere():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    entry = nav.split(f"page: {NAME},")[1].split("\n")[0]
    assert 'status: "draft"' in entry
    for special in ("Contents.md", "_Sidebar.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [l for l in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in l]
    assert len(rows) >= 7, "expected glossary rows for cron, crontab, timer, SysV init, init script, unit file, journald"


def test_glossary_rows_point_at_real_headings():
    heads = heading_slugs(text())
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_lessons_that_mention_cron_or_systemctl_link_the_lesson():
    for lesson in ("Terminal-and-Your-First-Script", "Linux-for-Enterprise-Beginners", "First-Hour-on-a-New-System-Updates-and-Baseline"):
        assert f"{NAME}.md" in page_text(WIKI / f"{lesson}.md"), lesson


def test_no_addresses_and_no_em_dashes():
    body = text()
    assert "—" not in body
    assert not ADDR.findall(body), ADDR.findall(body)
    assert ADDR.findall("ping 192.0.2.7"), "the address guard does not bite"


def test_the_translation_table_gets_weekly_and_the_day_rule_right():
    body = text()
    assert "`weekly` means Monday at midnight in systemd" in body
    assert "`@weekly` | `Sun *-*-* 00:00`" in body
    assert "the 1st and 15th **or** Fridays" in body or "the 1st and 15th **and** on every Friday" in body


def test_the_distro_table_is_dated_and_marks_what_it_did_not_read():
    section = text().split("## Is cron still installed? What I checked")[1].split("## Init scripts versus systemd")[0]
    assert "2026-11-07" in section
    for system in ("Debian", "Ubuntu", "Rocky", "Fedora", "Arch", "openSUSE"):
        assert system in section, system
    assert section.count("**est.**") >= 4, "unverified edges must be marked"


def test_every_claims_register_row_has_a_status():
    body = text()
    rows = register_rows(body)
    assert len(rows) >= 15, "the guard collected too few rows"
    assert not rows_missing_status(body)


def test_the_status_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | Y | trust me |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_exercises_never_use_a_destructive_crontab_command():
    body = text()
    for block in re.findall(r"```bash\n(.*?)```", body, re.DOTALL):
        assert "crontab -r" not in block, block
    assert "crontab -r" in body, "the warning about it is gone"
