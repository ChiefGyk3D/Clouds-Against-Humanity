# SPDX-License-Identifier: Apache-2.0
"""The radio and off-grid communication lesson: its script runs, its citations exist, it is registered and it stays safe.

docs/wiki/Radio-Off-Grid-Communication-LoRa-Meshtastic-Reticulum-Ham-and-SIGINT.md teaches radio as a continuity fallback
and tells this project's own story honestly (no radio code exists). A script whose output differs from the page, a cited
file that does not exist, a missing registration, a real callsign or grid square, a command that would configure a radio
or a link that pushes another lesson over its link cap would each teach the wrong thing.
"""

import importlib.util
import math
import re
import subprocess
import sys
from pathlib import Path

from wikitext import page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Radio-Off-Grid-Communication-LoRa-Meshtastic-Reticulum-Ham-and-SIGINT"
PAGE = WIKI / f"{NAME}.md"
FENCE = re.compile(r"^[ ]*```(\w*)\n(.*?)^[ ]*```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PATH_TOKEN = re.compile(r"`((?:modules|stacks|scripts|docs|\.github|\.spacelift|tests)/[A-Za-z0-9_./-]+)`")
STATUS_WORDS = ("Read", "Observed", "Not read", "Not run", "General knowledge", "**est.**", "Stated by the maintainer")
CALLSIGN = re.compile(r"\b(?:[AKNW][A-Z]?)\d[A-Z]{1,3}\b")
GRID = re.compile(r"\b[A-R]{2}\d{2}(?:[a-x]{2})?\b")
RADIO_TOOLS = re.compile(r"\b(?:meshtastic|rnodeconf|rnsd|rnstatus|lxmd|rtl_fm|hackrf_transfer|flrig|rigctl|fldigi|direwolf)\b")
BLAST = "Plan-for-Failure-Blast-Radius-and-Assuming-Breach"
TOPICS = (
    "## When the internet and the power go out: what still works",
    "## Wi-Fi, and why it is not the only radio",
    "## LoRa, Meshtastic, MeshCore and Reticulum",
    "## Amateur (ham) radio",
    "## GMRS and FRS",
    "## Citizens band (CB)",
    "## Signals intelligence (SIGINT): a careful overview",
    "## Why radio is a common hobby among security people",
    "## Radio in a continuity plan for this project",
    "## Free exercises: offline, listen-only and simulation",
    "## Claims register",
)


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def section(body: str, start: str, end: str) -> str:
    return body.split(start)[1].split(end)[0]


def table_rows(block: str) -> list[list[str]]:
    rows = [line for line in block.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def cited_paths(cell: str) -> list[str]:
    return PATH_TOKEN.findall(cell)


def register_rows(body: str) -> list[list[str]]:
    return table_rows(body.split("## Claims register")[1])


def rows_missing_status(rows: list[list[str]]) -> list[str]:
    return [r[0] for r in rows if not any(w in r[-1] for w in STATUS_WORDS)]


def rows_missing_citation(rows: list[list[str]]) -> list[str]:
    """A project row cites files that exist, or its file column starts with None and its status says None."""
    bad = []
    for r in rows:
        files, status = r[4], r[5]
        paths = cited_paths(files)
        if any(not (ROOT / p).exists() for p in paths):
            bad.append(r[0])
        elif files.startswith("None"):
            if "None" not in status:
                bad.append(r[0])
        elif not paths:
            bad.append(r[0])
    return bad


def foreign_callsigns(body: str) -> list[str]:
    return sorted(set(CALLSIGN.findall(body)) - {"N0CALL", "N0TST"})


def foreign_grids(body: str) -> list[str]:
    return sorted(set(GRID.findall(body)) - {"FN31pr"})


def radio_commands_in_shell_blocks(body: str) -> list[str]:
    return [b for t, b in FENCE.findall(body) if t in ("bash", "sh", "shell", "console") and RADIO_TOOLS.search(b)]


def script_source() -> str:
    found = [b for t, b in FENCE.findall(text()) if t == "python" and "# lora_budget.py - " in b]
    assert len(found) == 1, f"expected one lora_budget.py block, found {len(found)}"
    return found[0]


def run_script(tmp: Path, *args: str) -> subprocess.CompletedProcess:
    path = tmp / "lora_budget.py"
    path.write_text(script_source(), encoding="utf-8")
    return subprocess.run([sys.executable, "-I", str(path), *args], capture_output=True, text=True, timeout=60, check=False, cwd=tmp)


def load_functions(tmp: Path) -> dict:
    """Import the page's script as a module, with its final main() call removed so importing it prints nothing."""
    path = tmp / "lora_budget_under_test.py"
    path.write_text(script_source().rsplit("\nmain()", 1)[0] + "\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("lora_budget_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return vars(module)


def same_lines(got: str, want: str) -> bool:
    return [line.rstrip() for line in got.strip().splitlines()] == [line.rstrip() for line in want.strip().splitlines()]


def test_the_banner_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Radio and off-grid communication")
    assert "Status: unverified draft" in body
    assert "**Not run:**" in body and "2026-10-31" in body
    assert "no transmitter was keyed" in body and "no radio was configured" in body
    assert "General class" in body


def test_every_topic_the_issue_asked_for_has_a_section():
    body = text()
    missing = [t for t in TOPICS if f"\n{t}\n" not in body]
    assert not missing, missing


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 6, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_the_continuity_and_cryptography_lessons_are_linked_and_the_capped_one_is_plain_text():
    body = page_text(PAGE)  # the author's text, without the generated navigation blocks (issue #417)
    assert "Business-Continuity-and-Disaster-Recovery-BCP-and-DR.md" in body
    assert "The-CIA-Triad-Confidentiality-Integrity-Availability.md" in body
    # the cryptography lesson (issue 360) is in the wiki, so it is linked; the blast radius lesson has a link cap that is full
    assert "cryptography lesson" in body
    crypto = "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys"
    assert f"]({crypto}.md)" in body and (WIKI / f"{crypto}.md").is_file()
    assert "may not be merged yet" not in body
    assert f"{BLAST}.md" not in body
    assert "blast radius and assuming breach" in body


def test_the_lesson_is_registered_in_contents_and_reading_order_not_the_sidebar():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    entry = nav.split(f"page: {NAME},")[1].split("\n")[0]
    assert 'status: "draft"' in entry
    assert "sidebar" not in entry, "new lessons are reached from Contents and Reading Order, not the sidebar"
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [line for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in line]
    assert len(rows) >= 8, "expected glossary rows for the new terms"


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9-]", "", h.lower().replace(" ", "-")) for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors: set[str] = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_related_lessons_link_the_new_one():
    skip = {"Glossary.md", "_Sidebar.md", "Reading-Order.md", "Contents.md", PAGE.name}
    inbound = [p.name for p in WIKI.glob("*.md") if p.name not in skip and f"{NAME}.md" in p.read_text(encoding="utf-8")]
    assert len(inbound) >= 2, inbound


def test_no_addresses_and_no_em_dashes():
    body = text()
    assert not ADDR.findall(body), set(ADDR.findall(body))
    assert "—" not in body
    assert "Meshtastic" in body, "the guard collected nothing"


def test_the_address_guard_bites():
    assert ADDR.findall("ping 192.0.2.7")


def test_only_placeholder_callsigns_and_grids_appear_anywhere_in_the_lesson_files():
    body = text()
    assert "N0CALL" in body and "N0TST" in body and "FN31pr" in body, "the guard collected nothing"
    assert not foreign_callsigns(body), foreign_callsigns(body)
    assert not foreign_grids(body), foreign_grids(body)
    code = script_source()
    assert not foreign_callsigns(code) and not foreign_grids(code)


def test_the_callsign_and_grid_guards_bite():
    assert foreign_callsigns("de W1ABC and N0CALL") == ["W1ABC"]
    assert foreign_callsigns("KD9XYZ") == ["KD9XYZ"]
    assert foreign_grids("grid FN42ab and FN31pr") == ["FN42ab"]
    assert foreign_callsigns("N0CALL N0TST") == [] and foreign_grids("FN31pr") == []


def test_no_exercise_runs_a_radio_tool():
    body = text()
    assert not radio_commands_in_shell_blocks(body), radio_commands_in_shell_blocks(body)
    section_ex = body.split("## Free exercises: offline, listen-only and simulation")[1].split("## Checkpoint")[0]
    assert "never transmit" in section_ex.lower() or "no exercise transmits" in section_ex.lower()
    assert "do not key a transmitter" in body.lower() or "never key a transmitter" in body.lower()


def test_the_radio_tool_guard_bites():
    bad = "```bash\nmeshtastic --set lora.region US\n```\n"
    assert radio_commands_in_shell_blocks(bad)
    assert not radio_commands_in_shell_blocks("```text\nlora.region: US\n```\n")


def test_the_script_output_on_the_page_matches_a_real_run(tmp_path):
    body = text()
    shown = [b for t, b in FENCE.findall(body) if t == "text" and b.startswith("== 1. Bit rate")]
    assert len(shown) == 1, "expected the full report once"
    done = run_script(tmp_path)
    assert done.returncode == 0, done.stderr
    assert same_lines(done.stdout, shown[0])
    assert not [p for p in tmp_path.iterdir() if p.name != "lora_budget.py"], "the script must write nothing"


def test_the_one_packet_example_matches_a_real_run(tmp_path):
    body = text()
    done = run_script(tmp_path, "--sf", "8", "--bw", "125", "--cr", "5", "--payload", "100")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "SF8 BW125 CR4/5, 100 bytes: 324 ms on air, raw rate 3125 bps"
    assert done.stdout.strip() in body
    again = run_script(tmp_path, "--sf", "11", "--bw", "250", "--cr", "5", "--payload", "100")
    assert again.stdout.strip() == "SF11 BW250 CR4/5, 100 bytes: 1010 ms on air, raw rate 1074 bps"
    assert again.stdout.strip() in body


def test_the_comparison_guard_bites():
    assert same_lines("a\nb ", "a\nb")
    assert not same_lines("a\nb", "a\nc")


def test_the_script_matches_the_published_preset_table_and_the_semtech_formula(tmp_path):
    ns = load_functions(tmp_path)
    for name, (sf, bw, cr, pub, _) in ns["PRESETS"].items():
        assert abs(ns["bit_rate"](sf, bw, cr) / 1000 - pub) < 0.01, name
    # The datasheet form of the formula, written independently with floats and math.ceil.
    for sf in range(7, 13):
        for bw in (125, 250, 500):
            for cr in (5, 6, 7, 8):
                for total in (1, 20, 55, 100, 255):
                    t_sym = 2**sf / (bw * 1000)
                    de = 1 if t_sym > 0.016 else 0
                    sym = 16 + 4.25 + 8 + max(math.ceil((8 * total - 4 * sf + 28 + 16) / (4 * (sf - 2 * de))) * cr, 0)
                    assert abs(ns["airtime_ms"](sf, bw, cr, total) - sym * t_sym * 1000) < 1e-6, (sf, bw, cr, total)


def test_the_script_refuses_half_an_override(tmp_path):
    done = run_script(tmp_path, "--sf", "8")
    assert done.returncode != 0 and "--sf needs" in done.stderr


def test_the_script_cannot_reach_a_radio_or_the_network():
    code = script_source()
    for banned in ("import socket", "import subprocess", "import serial", "import os", "open(", "urllib", "requests", "sys.argv"):
        assert banned not in code, banned


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 28, "the guard collected too few rows"
    assert not rows_missing_status(rows)
    joined = " ".join(r[1] for r in rows)
    for needle in ("meshtastic.org", "reticulum.network", "ecfr.gov", "law.cornell.edu", "arrl.org", "ready.gov", "intelligence.gov", "hamvillage.org", "meshcore"):
        assert needle in joined, needle
    assert sum("2026-10-31" in r[-1] for r in rows) >= 15


def test_the_register_guard_bites():
    assert rows_missing_status([["X", "y", "maybe"]]) == ["X"]


def test_the_unread_sources_are_named_as_unread():
    reg = text().split("## Claims register")[1]
    for needle in ("fcc.gov", "nsa.gov"):
        row = next((line for line in reg.splitlines() if needle in line), "")
        assert "Not read" in row, needle
        assert "Access Denied" in row or "403" in row, needle


def test_project_rows_cite_existing_files_or_say_none():
    block = section(text(), "## Radio in a continuity plan for this project", "Honest summary")
    rows = table_rows(block)
    assert len(rows) >= 8, "the guard collected too few rows"
    assert not rows_missing_citation(rows)
    assert sum(r[4].startswith("None") for r in rows) >= 4, "the table must say None where nothing exists"
    joined = " ".join(r[0] for r in rows)
    for want in ("repository", "secret store", "Spacelift", "Twingate", "connectors", "wiki", "home logging", "edge"):
        assert want in joined, want


def test_the_citation_guard_bites():
    rows = [
        ["a", "x", "x", "x", "`scripts/does_not_exist.py`", "Built"],
        ["b", "x", "x", "x", "`scripts/secret_rule.py`", "Built"],
        ["c", "x", "x", "x", "None here", "Built"],
        ["d", "x", "x", "x", "None; the design is in `docs/does/not/exist.md`", "None"],
        ["e", "x", "x", "x", "no path at all", "Built"],
    ]
    assert rows_missing_citation(rows) == ["a", "c", "d", "e"]


def test_every_repository_path_the_page_names_exists():
    paths = set(cited_paths(text()))
    assert len(paths) >= 6, "the guard collected too few paths"
    assert not [p for p in sorted(paths) if not (ROOT / p).exists()]


def test_the_page_says_this_project_has_no_radio_integration():
    section_text = text().split("## Radio in a continuity plan for this project")[1].split("## Free exercises")[0]
    assert "no radio" in section_text.lower()
    assert "None" in section_text
    assert "TCP" in section_text, "the edge design carries Reticulum over TCP, which is not radio"


def test_the_legal_rules_come_before_the_overview_in_the_sigint_section():
    sec = text().split("## Signals intelligence (SIGINT): a careful overview")[1].split("## Why radio is a common hobby")[0]
    legal = sec.index("### The legal rules first")
    what = sec.index("### What SIGINT is")
    assert legal < what
    for needle in ("2511", "605", "check your own jurisdiction", "not legal advice", "readily accessible"):
        assert needle in sec, needle


def test_the_maintainer_facts_are_only_the_allowed_ones_and_no_to_do_list_is_published():
    body = text()
    assert "Maintainer notes to add" not in body
    assert "beyond the license class and the five services" in body
    assert "Meshtastic, MeshCore, Reticulum, ham radio and GMRS" in body
    assert "General class" in body
    assert not re.search(r"\b(?:my|his) (?:node|radio|repeater|antenna|rig)s?\b", body, re.IGNORECASE)


def test_us_rules_are_dated_and_other_countries_are_pointed_to_their_regulator():
    body = text()
    assert "check your own regulator" in body.lower() or "check your own country's regulator" in body.lower()
    assert "2026-10-29" in body, "the eCFR edition date must be stated"


HALOW = "## Wi-Fi HaLow (IEEE 802.11ah) next to LoRa"
HALOW_HEADS = (
    "### What HaLow is, and what it is not",
    "### HaLow compared with LoRa and the other radios on this page",
    "### Which to choose for off-grid and continuity use",
    "### HaLow rules: legal first",
)
HALOW_ROWS = ("Wi-Fi HaLow", "LoRa (physical layer)", "LoRaWAN", "Meshtastic", "MeshCore", "Wi-Fi at 2.4 and 5 GHz", "Amateur radio", "GMRS and FRS", "CB")


def halow_section(body: str) -> str:
    return body.split(f"\n{HALOW}\n")[1].split("\n## Amateur (ham) radio\n")[0]


def tables_in(block: str) -> list[list[str]]:
    """Each table's header row, found by the line before a |---| separator."""
    lines = block.splitlines()
    return [[c.strip() for c in lines[i - 1].strip("|").split("|")] for i, line in enumerate(lines) if line.startswith("|---") and i]


def first_cells(block: str) -> list[str]:
    return [r[0].replace("**", "") for r in table_rows(block)]


def test_halow_has_its_own_section_and_subsections_before_the_ham_section():
    body = page_text(PAGE)
    assert f"\n{HALOW}\n" in body
    assert body.index("## LoRa, Meshtastic, MeshCore and Reticulum") < body.index(HALOW) < body.index("\n## Amateur (ham) radio\n")
    sec = halow_section(body)
    for head in HALOW_HEADS:
        assert f"\n{head}\n" in f"\n{sec}", head


def test_the_banner_and_intro_say_halow_was_added_and_what_was_not_run():
    body = page_text(PAGE)
    banner = body.split("> **Status: unverified draft.")[1].split("\n\n")[0]
    assert "HaLow" in banner and "2026-11-01" in banner
    assert "no transmitter was keyed" in banner
    assert "HaLow" in body.split("## What you will be able to do")[0]
    assert any("HaLow" in line for line in body.split("## What you will be able to do")[1].split("##")[0].splitlines())
    assert "Wi-Fi HaLow" in section(body, "## When the internet and the power go out: what still works", "Satellite messengers")


def test_the_comparison_tables_name_their_first_cell_and_cover_every_technology_the_issue_named():
    sec = halow_section(page_text(PAGE))
    tables = tables_in(sec)
    assert len(tables) >= 3, "expected two comparison tables and a decision table"
    assert all(t[0] for t in tables), "every table needs a named first header cell"
    comparison = sec.split("### HaLow compared with LoRa and the other radios on this page")[1].split("### Which to choose")[0]
    header_text = " ".join(" ".join(t) for t in tables_in(comparison)).lower()
    for want in ("range", "throughput", "power", "topology", "licens", "encryption", "typical use", "equipment cost class"):
        assert want in header_text, want
    got = first_cells(comparison)
    for want in HALOW_ROWS:
        assert want in got, want


def test_every_halow_figure_carries_a_source_or_a_marker_and_no_price_appears():
    sec = halow_section(page_text(PAGE))
    assert "1 km" in sec and "100 kb/s" in sec
    for line in sec.splitlines():
        if "1 km" in line or "100 kb/s" in line or "15 km" in line:
            assert any(w in line for w in ("vendor", "design", "theoretical", "alliance", "Alliance", "IEEE")), line
    assert "$" not in sec and "USD" not in sec and "dollar" not in sec.lower()
    assert "qualitative" in sec.lower()


def test_halow_is_described_as_newer_and_less_common_and_no_vendor_is_ranked():
    sec = halow_section(page_text(PAGE))
    lowered = sec.lower()
    assert "newer" in lowered and "less common" in lowered
    for ranking in ("best", "recommended vendor", "top pick", "fastest chip"):
        assert ranking not in lowered, ranking


def test_the_halow_legal_section_reads_the_rule_text_and_adds_no_transmission_steps():
    sec = halow_section(page_text(PAGE))
    legal = sec.split("### HaLow rules: legal first")[1]
    for needle in ("15.247", "902", "928", "other regions", "not legal advice", "equipment authorization"):
        assert needle in legal, needle
    assert not radio_commands_in_shell_blocks(sec)
    assert not re.search(r"\b(?:set|configure|enable|flash)\b[^.\n]*\b(?:transmit|power|channel|region)\b", legal, re.IGNORECASE), "no configuration steps"
    assert not foreign_callsigns(sec) and not foreign_grids(sec)


def test_the_register_lists_the_halow_sources_read_and_the_ones_not_read():
    reg = page_text(PAGE).split("## Claims register")[1]
    for needle in ("wi-fi.org", "standards.ieee.org", "lora-alliance.org", "MorseMicro", "15.247"):
        row = next((line for line in reg.splitlines() if needle in line and "2026-11-01" in line), "")
        assert row, needle
        assert "Read 2026-11-01" in row, needle
    assert any("HaLow" in line and "Not read" in line for line in reg.splitlines()), "unread HaLow facts must be named"
    assert "Not verified" in page_text(PAGE) or "Not read" in page_text(PAGE)


def test_the_glossary_defines_halow_once_and_sub_ghz_once_and_points_at_real_headings():
    glossary = (WIKI / "Glossary.md").read_text(encoding="utf-8")
    for term in ("Wi-Fi HaLow (IEEE 802.11ah)", "Sub-GHz band"):
        rows = [line for line in glossary.splitlines() if line.startswith(f"| **{term}**")]
        assert len(rows) == 1, (term, len(rows))
        assert f"{NAME}.md#" in rows[0], term
    assert "802.11ah" not in "".join(line for line in glossary.splitlines() if line.startswith("| **802.11ah"))


def test_the_halow_table_guards_bite():
    assert tables_in("| A | B |\n|---|---|\n| x | y |") == [["A", "B"]]
    assert tables_in("|  | B |\n|---|---|\n| x | y |")[0][0] == ""
    assert first_cells("| T | U |\n|---|---|\n| **LoRaWAN** | y |") == ["LoRaWAN"]
