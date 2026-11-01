# SPDX-License-Identifier: Apache-2.0
"""The RAID lesson: it leads with continuity and not backup, its drill runs, its figures are computed, it is registered.

docs/wiki/RAID-Levels-Parity-Rebuilds-and-Why-RAID-Is-Continuity-Not-a-Backup.md teaches RAID as a business continuity
control (issue 421). A page that lets RAID pass for a backup, an exercise answer typed by hand and wrong, a drill whose output
differs from the page, a command that could reach a real disk, a vendor ranking, a dead link, a missing registration, a
diagram with no picture or the wrong shape, or a register row with no URL and no date would each teach the wrong thing.
"""

import json
import math
import re
import struct
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "RAID-Levels-Parity-Rebuilds-and-Why-RAID-Is-Continuity-Not-a-Backup"
PAGE = WIKI / f"{NAME}.md"
BCP = "Business-Continuity-and-Disaster-Recovery-BCP-and-DR"
CIA = "The-CIA-Triad-Confidentiality-Integrity-Availability"
BACKUPS = "Backups-Recovery-and-Patching"
DEEP = "Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing"
DATE = "2026-11-01"
EXERCISE = "## Exercise: size a six-drive shelf on paper"
FRAMING = "## RAID keeps the system running; a backup keeps the data recoverable"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
WRAPPED = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<path>[^)\n]+)\)\n\n<details>\n<summary>Diagram source \(Mermaid\)</summary>\n\n```mermaid\n(?P<src>.*?)\n```\n\n</details>",
    re.DOTALL,
)
URL = re.compile(r"\]\(https?://[^)\s]+\)")
STATUS_WORDS = ("Read", "Observed", "Not run", "**est.**", "General knowledge", "Derived")
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
BRITISH = ("defence", "behaviour", "colour", "organisation", "centre", "licence", "programme", "analyse", "favour", "realise", "offence", "grey")
VENDORS = (
    "seagate",
    "western digital",
    "toshiba",
    "hgst",
    "hitachi",
    "samsung",
    "synology",
    "qnap",
    "broadcom",
    "adaptec",
    "dell",
    "netapp",
    "wd red",
    "ironwolf",
    "barracuda",
)
TOPICS = (
    "## What you will be able to do",
    "## What the wiki already says (and the gap)",
    FRAMING,
    "## The words: striping, mirroring, parity, spares",
    "## The levels, side by side",
    "## Parity in one XOR, and the price of a small write",
    "## When a drive fails: degraded, rebuild and the risk window",
    "## The write hole and power loss",
    "## Hardware, firmware, software and filesystem RAID",
    "## What RAID does not protect against",
    "## Where RAID sits in a continuity plan",
    "## Where this shows up in this project",
    "## Free path: a parity drill on your own computer",
    "## Optional: an array on loopback files (shown, not run)",
    EXERCISE,
    "## Build, break, detect, evade, defend (on paper)",
    "## Checkpoint",
    "## Common mistakes",
    "## Not verified, plainly",
    "## Claims register",
)

# ---- the formulas the exercise answers come from -----------------------------------------------------------------------


def usable_tb(level: str, drives: int, size_tb: float) -> float:
    return {"RAID 0": drives * size_tb, "RAID 10": drives // 2 * size_tb, "RAID 5": (drives - 1) * size_tb, "RAID 6": (drives - 2) * size_tb}[level]


def survive_for_certain(level: str, drives: int) -> int:
    return {"RAID 0": 0, "RAID 10": 1, "RAID 5": 1, "RAID 6": 2}[level]


def survive_best_case(level: str, drives: int) -> int:
    return {"RAID 0": 0, "RAID 10": drives // 2, "RAID 5": 1, "RAID 6": 2}[level]


def small_write_ios(level: str) -> int:
    """Disk operations for one small write: 1 write; 2 writes to two copies; RAID 5 reads old data and old parity and writes both;
    RAID 6 does the same with two parities (derived, not in the sources read)."""
    return {"RAID 0": 1, "RAID 10": 2, "RAID 5": 4, "RAID 6": 6}[level]


def random_writes_per_second(level: str, drives: int, per_drive: int) -> float:
    return drives * per_drive / small_write_ios(level)


def mttf_raid_hours(mttf_disk: float, data_disks: int, group: int, check_per_group: int, mttr: float) -> float:
    """Patterson, Gibson and Katz (1987): MTTF_RAID = MTTF_disk^2 / ((D + C * nG) * (G + C - 1) * MTTR)."""
    groups = data_disks / group
    return mttf_disk**2 / ((data_disks + check_per_group * groups) * (group + check_per_group - 1) * mttr)


def afr_from_drive_days(failures: int, drive_days: int) -> float:
    return failures / (drive_days / 365)


def chance_any_fails(afr: float, drives: int) -> float:
    return 1 - (1 - afr) ** drives


def chance_of_one_or_more_ure(bits_read: float, rate_per_bit: float) -> float:
    return 1 - math.exp(-bits_read * rate_per_bit)


def rebuild_hours(size_tb: float, mb_per_second: float) -> float:
    return size_tb * 1e12 / (mb_per_second * 1e6) / 3600


def xor_bytes(*blocks: bytes) -> bytes:
    out = bytearray(len(blocks[0]))
    for block in blocks:
        for i, b in enumerate(block):
            out[i] ^= b
    return bytes(out)


# ---- helpers on the page -----------------------------------------------------------------------------------------------


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", heading.lower()).strip().replace(" ", "-"))


def headings(body: str) -> set[str]:
    return {slug(h) for h in re.findall(r"^#+ (.+)$", body, re.MULTILINE)}


def section(body: str, heading: str) -> str:
    return body.split(f"\n{heading}\n")[1].split("\n## ")[0]


def table_rows(block: str) -> list[list[str]]:
    rows = [line for line in block.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def register_rows(body: str) -> list[list[str]]:
    return table_rows(body.split("## Claims register")[1])


def rows_missing_status(rows: list[list[str]]) -> list[str]:
    return [r[0] for r in rows if not any(w in r[-1] for w in STATUS_WORDS)]


def sourced_rows_without_url_and_date(rows: list[list[str]]) -> list[str]:
    exempt = ("The maintainer's framing", "General knowledge", "Derived by the author", "The author's own", "Constructed by the author")
    bad = []
    for row in rows:
        if row[1].startswith(exempt):
            continue
        if not URL.search(row[1]) or DATE not in row[2]:
            bad.append(row[0])
    return bad


def british_words(body: str) -> list[str]:
    return sorted(w for w in BRITISH if re.search(rf"\b{w}\b", body))


def vendor_names(body: str) -> list[str]:
    low = body.lower()
    return [v for v in VENDORS if re.search(rf"\b{re.escape(v)}\b", low)]


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", data[16:24])


def too_tall(width: int, height: int) -> bool:
    return height > 1.6 * width


POSTURE = (
    r"required_approving_review_count",
    r"required approving review",
    r"enforce_admins",
    r"branch protection",
    r"branch rule",
    r"stale reviews",
    r"no human approval",
    r"github api",
    r"gh api",
)


def posture_phrases(body: str) -> list[str]:
    """Statements of this repository's own security settings must not be published."""
    return [p for p in POSTURE if re.search(p, body, re.IGNORECASE)]


# ---- the page ----------------------------------------------------------------------------------------------------------


def test_the_banner_says_it_was_written_from_reading_and_names_what_was_not_run():
    body = text()
    assert body.startswith("# RAID: levels, parity, rebuilds, and why it is continuity and not a backup")
    assert "Status: unverified draft" in body
    assert "**Not run:**" in body and "**Not read:**" in body and DATE in body
    assert "issue 421" in body
    assert "defensive and educational" in body.lower()


def test_the_page_leads_with_continuity_and_not_a_backup_and_every_topic_has_a_section():
    body = text()
    opening = body.split("> Unfamiliar word or acronym?")[0]
    assert "business continuity" in opening and "not a backup" in opening
    assert "RAID is not a backup" in body
    missing = [t for t in TOPICS if f"\n{t}\n" not in body]
    assert not missing, missing
    assert body.index(FRAMING) < body.index("## The words: striping"), "the framing comes before the mechanics"
    assert body.index("## What you will be able to do") < body.index(FRAMING)
    abilities = section(body, "## What you will be able to do")
    assert "not a backup" in abilities


def test_the_framing_section_has_the_sources_the_maintainer_framing_rests_on():
    sec = section(text(), FRAMING)
    for needed in (
        "availability",
        "business continuity",
        "at most one copy",
        "SP 800-34",
        "cannot be a replacement for a solid backup strategy",
        "backup, backup, BACK UP",
        "RAID is not a panacea",
        "Patterson, Gibson and Katz",
        "backup versions of all information every night",
        "independent",
    ):
        assert needed in sec, needed
    for link in (BCP, CIA, BACKUPS, DEEP):
        assert f"]({link}.md" in sec, link


def test_the_event_table_says_what_raid_survives_and_what_a_backup_survives():
    sec = section(text(), FRAMING)
    rows = table_rows(sec)
    assert len(rows) >= 9, "the guard collected too few rows"
    events = " ".join(r[0] for r in rows).lower()
    for needed in ("drive", "deleted", "ransomware", "corrupt", "controller", "fire", "theft", "second drive", "power"):
        assert needed in events, needed
    assert "Yes" in rows[0][1] and "drive" in rows[0][0].lower()
    no_raid = sum("**No**" in r[1] for r in rows)
    no_backup = sum("**No**" in r[2] for r in rows)
    assert no_raid >= 6, no_raid
    assert no_backup <= 2, "a backup is not a cure for everything either, but the table must not say so for most rows"
    assert any("not" in r[2].lower() or "only if" in r[2].lower() for r in rows), "the backup column has its own conditions"
    assert not [r[0] for r in rows if len(r) != 3]


def test_the_event_table_guard_bites():
    rows = table_rows("| Event | RAID | Backup |\n|---|---|---|\n| a drive fails | Yes | Yes |\n| ransomware | Yes | Yes |\n")
    assert sum("**No**" in r[1] for r in rows) == 0


def test_every_linked_wiki_page_exists_and_every_anchor_is_a_real_heading():
    found = LINK.findall(text())
    assert len({t for t, _ in found}) >= 8, "the guard collected too few links"
    missing = sorted({t for t, _ in found if not (WIKI / f"{t}.md").exists()})
    assert not missing, missing
    bad = [f"{t}#{a}" for t, a in found if a and a not in headings((WIKI / f"{t}.md").read_text(encoding="utf-8"))]
    assert not bad, bad
    linked = {t for t, _ in found}
    for needed in (BCP, CIA, BACKUPS, DEEP, "Glossary", "Hashing-Encryption-and-Keys", "Terminal-and-Your-First-Script"):
        assert needed in linked, needed


def test_the_blast_radius_lesson_is_named_in_plain_text_so_its_link_cap_holds():
    body = text()
    assert "Plan-for-Failure-Blast-Radius" not in body


def test_the_lesson_is_registered_in_nav_contents_reading_order_home_and_sidebar():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    line = next(row for row in nav.splitlines() if f"page: {NAME}," in row)
    assert 'status: "draft"' in line and "Recovery, patching, virtual machines and Windows" in line
    for special in ("Contents.md", "Reading-Order.md", "Home.md", "_Sidebar.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special


def test_the_backups_deep_dive_links_this_lesson_and_this_lesson_links_it_back():
    assert f"]({NAME}.md" in (WIKI / f"{DEEP}.md").read_text(encoding="utf-8")
    assert f"]({DEEP}.md" in text()


def test_glossary_rows_point_at_real_headings_and_none_repeats_a_term():
    heads = headings(text())
    anchors = set()
    rows = 0
    glossary = (WIKI / "Glossary.md").read_text(encoding="utf-8")
    for line in glossary.splitlines():
        if f"{NAME}.md" in line:
            rows += 1
            anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert rows >= 11, "expected glossary rows for the new terms"
    assert anchors and anchors <= heads, sorted(anchors - heads)
    terms = [m.group(1).lower() for m in re.finditer(r"^\| \*\*([^*]+)\*\* \|", glossary, re.MULTILINE)]
    assert len(terms) > 100, "the guard collected too few glossary terms"
    mine = [m.group(1).lower() for m in re.finditer(rf"^\| \*\*([^*]+)\*\* \|[^\n]*{NAME}\.md", glossary, re.MULTILINE)]
    assert len(mine) == rows, (len(mine), rows)
    repeated = sorted({t for t in mine if terms.count(t) > 1})
    assert not repeated, repeated
    for term in ("raid", "striping", "mirroring", "parity", "hot spare", "degraded array", "write hole"):
        assert any(t.startswith(term) for t in mine), term
    assert sorted({t for t in ["a", "b", "a"] if ["a", "b", "a"].count(t) > 1}) == ["a"], "the repeat guard bites"


def test_american_spelling_no_em_dashes_no_addresses_and_no_vendor_names_outside_the_register():
    body = text()
    low = body.lower()
    assert "—" not in body
    assert not IPV4.findall(body), IPV4.findall(body)
    assert not british_words(low), british_words(low)
    prose = body.split("## Claims register")[0]
    assert not vendor_names(prose), vendor_names(prose)
    assert "raid" in low, "the guard collected nothing"
    for banned in ("most reliable brand", "best brand", "we recommend buying", "buy the"):
        assert banned not in low, banned


def test_the_spelling_and_vendor_guards_bite():
    assert british_words("the organisation's defence and an offence") == ["defence", "offence", "organisation"]
    assert not british_words("the organization's defense and impact analyses")
    assert vendor_names("Seagate and WD Red drives") == ["seagate", "wd red"]
    assert not vendor_names("a NAS line sold for arrays")


def test_every_table_has_a_named_first_header_cell():
    bad = []
    lines = text().splitlines()
    tables = 0
    for i, line in enumerate(lines[:-1]):
        if line.startswith("|") and lines[i + 1].startswith("|---") and (i == 0 or not lines[i - 1].startswith("|")):
            tables += 1
            if not line.strip("|").split("|")[0].strip():
                bad.append(i + 1)
    assert tables >= 8, "the guard collected too few tables"
    assert not bad, bad


def test_no_security_posture_detail_of_this_repository_is_on_the_page_and_the_guard_bites():
    body = text()
    assert "raid" in body.lower(), "the guard collected nothing"
    assert not posture_phrases(body), posture_phrases(body)
    assert posture_phrases("check the branch protection settings")
    assert not posture_phrases("check the settings in your own system")


# ---- diagrams ----------------------------------------------------------------------------------------------------------


def test_every_diagram_has_alt_text_a_source_a_picture_and_a_wide_shape():
    body = text()
    found = list(WRAPPED.finditer(body))
    assert len(found) == 3, "expected three diagrams"
    assert len(re.findall(r"```mermaid", body)) == len(found), "a Mermaid block has no picture above it"
    manifest = json.loads((ROOT / "docs" / "diagrams.json").read_text())
    for m in found:
        alt = m["alt"].strip()
        assert 20 <= len(alt) <= 150, alt
        png = (PAGE.parent / m["path"]).resolve()
        assert png.is_file(), m["path"]
        assert png.relative_to(ROOT).as_posix() in manifest, m["path"]
        assert m["src"].lstrip().startswith("flowchart LR"), m["path"]
        width, height = png_size(png)
        assert not too_tall(width, height), (m["path"], width, height)


def test_the_diagram_guards_bite():
    bare = "![alt text here](images/x.png)\n\nno details block, so no source\n"
    assert not WRAPPED.search(bare)
    good = "![alt text here](images/x.png)\n\n<details>\n<summary>Diagram source (Mermaid)</summary>\n\n```mermaid\nflowchart LR\n  a --> b\n```\n\n</details>"
    assert WRAPPED.search(good)
    assert not WRAPPED.search(good.replace("<details>\n", ""))
    assert too_tall(100, 161) and not too_tall(100, 160)


def test_the_diagrams_cover_what_raid_survives_the_layouts_and_the_risk_window():
    found = list(WRAPPED.finditer(text()))
    alts = " ".join(m["alt"].lower() for m in found)
    for topic in ("backup", "level", "rebuild"):
        assert topic in alts, topic
    sources = " ".join(m["src"] for m in found)
    for needed in ("RAID 0", "RAID 1", "RAID 5", "RAID 6", "RAID 10", "degraded", "ransomware", "deleted"):
        assert needed in sources, needed


# ---- the register ------------------------------------------------------------------------------------------------------


def test_every_claims_register_row_has_a_status_a_url_and_the_read_date():
    rows = register_rows(text())
    assert len(rows) >= 18, "the guard collected too few rows"
    assert not rows_missing_status(rows)
    assert not sourced_rows_without_url_and_date(rows)
    joined = " ".join(r[1] for r in rows)
    for host in (
        "www2.eecs.berkeley.edu/Pubs/TechRpts/1987/CSD-87-391.pdf",
        "nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-34r1.pdf",
        "raid.wiki.kernel.org/index.php/How_to_protect_your_data",
        "raid.wiki.kernel.org/index.php/Scrubbing_the_drives",
        "raid.wiki.kernel.org/index.php/Timeout_Mismatch",
        "raid.wiki.kernel.org/",
        "docs.kernel.org/admin-guide/md.html",
        "docs.kernel.org/driver-api/md/raid5-ppl.html",
        "docs.kernel.org/driver-api/md/raid5-cache.html",
        "man7.org/linux/man-pages/man8/mdadm.8.html",
        "man7.org/linux/man-pages/man8/losetup.8.html",
        "openzfs.github.io/openzfs-docs/Basic%20Concepts/Pool%20Structure/RAIDZ.html",
        "openzfs.github.io/openzfs-docs/man/master/8/zpool-scrub.8.html",
        "learn.microsoft.com/en-us/windows-server/storage/storage-spaces/fault-tolerance",
        "backblaze.com/cloud-storage/resources/hard-drive-test-data",
    ):
        assert host in joined, host
    assert sum(DATE in r[2] for r in rows) >= 14


def test_the_register_guards_bite():
    assert rows_missing_status([["X", "y", "maybe"]]) == ["X"]
    assert sourced_rows_without_url_and_date([["X", "[p](https://example.com/p)", "Read 2026-10-31"]]) == ["X"]
    assert sourced_rows_without_url_and_date([["X", "a page", "Read 2026-11-01"]]) == ["X"]
    assert not sourced_rows_without_url_and_date([["X", "General knowledge", "est."]])


# ---- facts that can be checked on the page -----------------------------------------------------------------------------


def test_the_levels_table_matches_the_formulas():
    sec = section(text(), "## The levels, side by side")
    rows = table_rows(sec)
    names = [r[0] for r in rows]
    assert len(rows) >= 6, "the guard collected too few rows"
    for needed in ("RAID 0", "RAID 1", "RAID 5", "RAID 6", "RAID 10", "RAIDZ"):
        assert any(n.startswith(needed) for n in names), needed
    by = {r[0].split(" (")[0]: r for r in rows}
    assert "(n - 1)" in by["RAID 5"][2] and "(n - 2)" in by["RAID 6"][2]
    assert "n / 2" in by["RAID 10"][2] and "all n" in by["RAID 0"][2]
    assert "one" in by["RAID 5"][3].lower() and "two" in by["RAID 6"][3].lower() and "none" in by["RAID 0"][3].lower()
    assert "Not a backup" in sec or "not a backup" in sec


def test_the_exercise_capacity_table_is_computed_here_and_matches_the_page():
    ex = section(text(), EXERCISE)
    cap = [r for r in table_rows(ex) if r[0].startswith("RAID") and len(r) == 7]
    assert [r[0].split(" (")[0] for r in cap] == ["RAID 0", "RAID 10", "RAID 5", "RAID 6"], [r[0] for r in cap]
    drives, size = 6, 8
    for r in cap:
        level = r[0].split(" (")[0]
        assert int(r[1]) == drives
        assert int(r[2]) == usable_tb(level, drives, size), level
        assert r[3] == f"{usable_tb(level, drives, size) / (drives * size):.0%}", level
        assert int(r[4]) == survive_for_certain(level, drives), level
        assert int(r[5]) == survive_best_case(level, drives), level
        assert int(r[6]) == small_write_ios(level), level


def test_the_exercise_write_table_is_computed_here_and_matches_the_page():
    ex = section(text(), EXERCISE)
    rows = [r for r in table_rows(ex) if r[0].startswith("RAID") and len(r) == 2]
    assert [r[0].split(" (")[0] for r in rows] == ["RAID 0", "RAID 10", "RAID 5", "RAID 6"]
    for r in rows:
        level = r[0].split(" (")[0]
        assert float(r[1].replace(",", "")) == random_writes_per_second(level, 6, 150), level
    assert "150" in ex and "est." in ex


def test_the_exercise_reliability_figures_are_the_ones_the_formulas_give():
    ex = section(text(), EXERCISE)
    one_group = mttf_raid_hours(30_000, 100, 10, 1, 1)
    wide = mttf_raid_hours(30_000, 100, 25, 1, 1)
    day = mttf_raid_hours(30_000, 100, 10, 1, 24)
    assert round(one_group) == 818_182 and round(wide) == 346_154 and round(day) == 34_091
    for needed in (
        f"{one_group:,.0f} hours",
        f"{one_group / 8760:.1f} years",
        f"{wide:,.0f} hours",
        f"{day:,.0f} hours",
        f"{day / 8760:.1f} years",
        "820,000",
        "346,000",
    ):
        assert needed in ex, needed
    # The paper's own table agrees with the formula to the figure it prints.
    assert abs(one_group - 820_000) / 820_000 < 0.005 and abs(wide - 346_000) / 346_000 < 0.005
    assert mttf_raid_hours(30_000, 100, 10, 1, 24) < mttf_raid_hours(30_000, 100, 10, 1, 1) / 20, "a slower repair costs most of the margin"


def test_the_exercise_failure_rate_and_rebuild_figures_are_computed_here():
    ex = section(text(), EXERCISE)
    afr = afr_from_drive_days(1_498, 31_553_350)
    assert f"{afr:.2%}" == "1.73%"
    assert "1,498" in ex and "31,553,350" in ex and "1.73%" in ex
    year = chance_any_fails(0.0173, 6)
    assert f"{year:.1%}" in ex, f"{year:.1%}"
    bits = 5 * 8e12 * 8
    assert bits == 3.2e14
    pessimistic = chance_of_one_or_more_ure(bits, 1e-14)
    better = chance_of_one_or_more_ure(bits, 1e-15)
    assert f"{pessimistic:.0%}" in ex and f"{better:.0%}" in ex, (f"{pessimistic:.0%}", f"{better:.0%}")
    assert f"{rebuild_hours(8, 150):.1f} hours" in ex and f"{rebuild_hours(8, 50):.1f} hours" in ex
    assert "3.2" in ex and "1 in 10^14" in ex and "1 in 10^15" in ex
    assert "I did not read" in ex or "not read" in ex.lower()


def test_the_formula_guards_bite():
    assert usable_tb("RAID 5", 6, 8) != 6 * 8
    assert usable_tb("RAID 5", 6, 8) == 40 and usable_tb("RAID 6", 6, 8) == 32 and usable_tb("RAID 10", 6, 8) == 24
    assert survive_best_case("RAID 10", 6) == 3 and survive_for_certain("RAID 10", 6) == 1
    assert random_writes_per_second("RAID 5", 6, 150) == 225
    assert mttf_raid_hours(30_000, 100, 10, 1, 2) != mttf_raid_hours(30_000, 100, 10, 1, 1)
    assert round(afr_from_drive_days(1_498, 31_553_350), 4) == 0.0173
    assert chance_of_one_or_more_ure(3.2e14, 1e-14) > chance_of_one_or_more_ure(3.2e14, 1e-15)
    assert round(rebuild_hours(8, 150), 1) == 14.8


def test_the_exercise_is_synthetic_and_says_so_and_the_answers_say_what_they_do_not_show():
    ex = section(text(), EXERCISE)
    assert "made-up" in ex and "Example Shelf" in ex
    assert "independent" in ex and "correlated" in ex
    assert "Not run" in ex or "not run" in ex
    assert "worst case" in ex or "maximum" in ex


# ---- the drill ---------------------------------------------------------------------------------------------------------


def script() -> str:
    found = [textwrap.dedent(b) for t, b in FENCE.findall(text()) if t == "python" and "# raid_drill.py - " in b]
    assert len(found) == 1, f"expected one raid_drill.py block, found {len(found)}"
    return found[0]


def test_the_drill_runs_and_its_output_matches_the_page(tmp_path):
    path = tmp_path / "raid_drill.py"
    path.write_text(script())
    done = subprocess.run(
        [sys.executable, "-I", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        cwd=tmp_path,
        env={"TMPDIR": str(tmp_path), "PATH": "/usr/bin:/bin"},
    )
    assert done.returncode == 0, done.stderr
    shown = next(b for t, b in FENCE.findall(text()) if t == "text" and b.startswith("== Parity"))
    got = [line.rstrip() for line in done.stdout.strip().splitlines()]
    want = [line.rstrip() for line in shown.strip().splitlines()]
    assert got == want
    assert not [p for p in tmp_path.iterdir() if p.name.startswith("raid-drill-")], "the script must delete its own lab folder"


def test_the_drill_results_agree_with_an_independent_xor():
    a, b, c = (bytes((i * k + 7) % 256 for i in range(16)) for k in (3, 5, 11))
    parity = xor_bytes(a, b, c)
    assert xor_bytes(a, c, parity) == b, "the lost drive comes back from the others and the parity"
    new_a = bytes((x + 1) % 256 for x in a)
    new_parity = xor_bytes(xor_bytes(a, new_a), parity)
    assert new_parity == xor_bytes(new_a, b, c), "the small-write rule: new parity = (old data xor new data) xor old parity"
    stale = xor_bytes(new_a, b, parity)
    assert stale != c, "a stale parity rebuilds the wrong data"


DRILL_BANNED = ("subprocess", "os.system", "sudo", "/dev/", "socket", "urllib", "requests", "os.remove", "shutil.move", "..\\")


def drill_problems(body: str) -> list[str]:
    found = [b for b in DRILL_BANNED if b in body]
    if re.search(r"open\(\s*[\"']/", body):
        found.append("an absolute path is opened")
    return found


def test_the_drill_never_touches_anything_outside_its_own_folder():
    body = script()
    assert "tempfile.mkdtemp" in body and "shutil.rmtree(lab)" in body and "finally:" in body
    assert not drill_problems(body), drill_problems(body)
    assert body.count("rmtree") == 1


def test_the_drill_guard_bites():
    assert drill_problems('open("/etc/passwd")') == ["an absolute path is opened"]
    assert drill_problems("import subprocess") == ["subprocess"]
    assert drill_problems("path = '/dev/sda'") == ["/dev/"]
    assert not drill_problems("(lab / 'drive1.bin').write_bytes(data)")


def test_the_drill_output_says_the_things_the_lesson_claims():
    shown = next(b for t, b in FENCE.findall(text()) if t == "text" and b.startswith("== Parity"))
    for needed in ("rebuilt drive 2 matches the original: True", "rebuilt drive 3 matches the original: False", "silent", "mirror", "backup"):
        assert needed in shown, needed


# ---- the optional loopback block: shown, never run ---------------------------------------------------------------------

ALLOWED_DEVICE = re.compile(r"^/dev/(?:md/lab|loop<[A-D]>)$")


def mdadm_block() -> str:
    found = [b for t, b in FENCE.findall(text()) if t == "bash" and "mdadm" in b]
    assert len(found) == 1, f"expected one mdadm block, found {len(found)}"
    return found[0]


def device_problems(block: str) -> list[str]:
    return [d for d in re.findall(r"/dev/[A-Za-z0-9_/<>-]+", block) if not ALLOWED_DEVICE.match(d)]


def test_the_loopback_block_is_marked_not_run_and_names_only_the_readers_own_files():
    block = mdadm_block()
    assert block.lstrip().startswith("# NOT RUN"), "the block says it was not run on its first line"
    assert not device_problems(block), device_problems(block)
    for needed in ("truncate -s", "losetup --find --show", "mdadm --create", "--level=5", "--fail", "--remove", "--add", "--stop", "losetup -d", "--zero-superblock"):
        assert needed in block, needed
    assert block.index("--stop") < block.index("losetup -d"), "the array is stopped before the loop devices are released"
    prose = text().split("## Optional: an array on loopback files")[1].split("\n## ")[0]
    assert "Not run" in prose and "root" in prose and "only on files you made" in prose
    assert "mdadm --create" in prose and "existing array" in prose, "the warning about --create on an existing array is there"


def test_the_loopback_guard_bites():
    assert device_problems("mdadm --create /dev/md/lab /dev/sda1 /dev/loop<A>") == ["/dev/sda1"]
    assert device_problems("mdadm --detail /dev/nvme0n1") == ["/dev/nvme0n1"]
    assert not device_problems("mdadm --create /dev/md/lab /dev/loop<A> /dev/loop<B>")


# ---- the rest ----------------------------------------------------------------------------------------------------------


def test_the_project_table_cites_existing_files_or_says_none():
    sec = section(text(), "## Where this shows up in this project")
    rows = table_rows(sec)
    assert len(rows) >= 5, "the guard collected too few rows"
    for r in rows:
        paths = re.findall(r"`((?:modules|stacks|scripts|docs|\.github|tests)/[A-Za-z0-9_./-]+)`", r[2])
        assert all((ROOT / p).exists() for p in paths), r[0]
        assert paths or r[2].startswith("None"), r[0]
    assert sum(r[2].startswith("None") for r in rows) >= 2
    assert "no RAID" in sec or "no word RAID" in sec


def test_what_the_page_did_not_read_is_named():
    part = section(text(), "## Not verified, plainly")
    for needed in (
        "datasheet",
        "hardware RAID",
        "ZFS",
        "Storage Spaces",
        "mdadm --create",
        "RAID 2",
        "Not run",
        "SNIA",
        "Backblaze",
        "level 3",
    ):
        assert needed in part, needed


def test_the_drill_and_exercise_say_run_or_not_run_for_every_command_block():
    body = text()
    blocks = [(t, b) for t, b in FENCE.findall(body) if t in ("bash", "python")]
    assert len(blocks) >= 3, "the guard collected too few code blocks"
    for t, b in blocks:
        first = b.lstrip().splitlines()[0]
        assert first.startswith(("# NOT RUN", "#!/usr/bin/env python3", "python3 -I raid_drill.py")), first
    assert "**Observed**" in body or "Observed" in body.split("## Claims register")[1]
