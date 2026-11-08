# SPDX-License-Identifier: Apache-2.0
"""The open firmware lesson: registered, dated, honest about what was run, and read-only.

docs/wiki/Open-Firmware-and-Trustworthy-Hardware-...-Disabled.md reports what four hardware vendors claim about
the Intel Management Engine. A claim with no date or status, a vendor named in the table but missing from the
vendor section, a flashing command, an affiliate link, a real address or a stale registration would each teach
the wrong thing.
"""

import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Open-Firmware-and-Trustworthy-Hardware-coreboot-Heads-Nitrokey-and-Vendors-That-Ship-the-Intel-ME-Disabled"
PAGE = WIKI / f"{NAME}.md"
FENCE = re.compile(r"^[ ]*```(\w*)\n(.*?)^[ ]*```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
STATUS_WORDS = ("Read", "Observed", "General knowledge", "**est.**", "**not verified**")
VENDORS = ("Novacustom", "System76", "Purism", "Tuxedo")
WRITE_TOKENS = re.compile(r"\bsudo\b|\bflashrom\b|\bifdtool\b|\bme_cleaner\b|\bnvramtool\b|\bdd\b|\bchmod\b|>\s*/(?:sys|dev|boot)", re.IGNORECASE)
AFFILIATE = re.compile(r"[?&](ref|aff|affiliate|utm_[a-z]+|tag|partner)=", re.IGNORECASE)


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def blocks(tag: str) -> list[str]:
    return [textwrap.dedent(b) for t, b in FENCE.findall(text()) if t == tag]


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1].split("\n## ")[0]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def unsafe_lines(commands: str) -> list[str]:
    return [l for l in commands.splitlines() if WRITE_TOKENS.search(l)]


def vendor_section(body: str, vendor: str) -> str:
    start = body.index(f"### {vendor}")
    first_line_end = body.index("\n", start) + 1
    rest = body[first_line_end:]
    nxt = re.search(r"^#{2,3} ", rest, re.MULTILINE)
    return body[start : first_line_end + (nxt.start() if nxt else len(rest))]


def test_the_page_exists_and_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Open firmware and trustworthy hardware")
    assert "> **Status: unverified draft." in body
    assert "Nothing was flashed" in body
    assert "**Not run:**" in body and "2026-11-07" in body
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
    assert len(rows) >= 6, "expected glossary rows for the new terms"


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-") for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_no_em_dashes_no_addresses_and_no_affiliate_links():
    body = text()
    assert "—" not in body and "–" not in body
    assert not ADDR.findall(body), ADDR.findall(body)
    urls = re.findall(r"\]\((https?://[^)]+)\)", body)
    assert len(urls) >= 20, "the guard collected too few links"
    assert not [u for u in urls if AFFILIATE.search(u)]


def test_the_guards_bite():
    assert ADDR.findall("host 192.0.2.7")
    assert AFFILIATE.search("https://example.com/p?ref=abc")
    assert not AFFILIATE.search("https://example.com/p")


def test_there_are_no_flashing_or_write_commands_in_any_code_block():
    cmds = "\n".join(b for _, b in FENCE.findall(text()))
    assert "curl" in cmds and "fwupdmgr" in cmds, "the guard collected nothing"
    assert not unsafe_lines(cmds)


def test_the_write_guard_bites():
    assert unsafe_lines("sudo flashrom -p internal -w rom.bin")
    assert unsafe_lines("python me_cleaner.py -S image.bin")
    assert unsafe_lines("echo 1 > /sys/class/x")
    assert not unsafe_lines("cat /sys/class/tpm/tpm0/tpm_version_major")


def test_each_vendor_has_a_section_with_a_firmware_and_an_me_line():
    body = text()
    for vendor in VENDORS:
        sec = vendor_section(body, vendor)
        assert "Firmware" in sec or "Tuxedo" in vendor, vendor
        assert "ME" in sec, vendor
    assert "I could not verify a claim" in vendor_section(body, "Tuxedo Computers")


def test_the_vendor_section_helper_bites():
    sample = "### A\nFirmware ME\n### B\nother\n"
    assert "Firmware ME" in vendor_section(sample, "A")
    assert "other" not in vendor_section(sample, "A")


def test_the_four_me_words_and_the_dasharo_modes_are_named():
    body = text()
    for word in ("Absent", "Neutralized", "Soft-disabled", "HAP-disabled"):
        assert f"**{word}**" in body, word
    for mode in ("Enabled", "Disabled (Soft)", "Disabled (HAP)"):
        assert mode in body, mode


def test_every_vendor_page_is_dated_in_the_register():
    body = text()
    assert body.count("2026-11-07") >= 8
    reg = body.split("## Claims register")[1]
    for vendor in VENDORS:
        assert vendor in reg, vendor


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 35, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_heads_key_table_matches_the_heads_prerequisites_wording():
    body = text()
    assert "Heads does NOT support FIDO2 or U2F" in body
    assert "OpenPGP only" in body
    for key in ("YubiKey 5 Series", "Nitrokey Pro 2", "Nitrokey Storage 2", "Nitrokey 3", "Librem Key"):
        assert key in body, key


def test_the_page_ends_by_linking_the_firmware_and_hardware_keys_lessons():
    body = text()  # the page file ends with its own text: the navigation block is added when the wiki is published (issue #521)
    tail = body.split("## Where this goes next")[1]
    for target in ("Device-Firmware-Security-Intel-ME-AMD-PSP-MINIX-and-Kernel-Design", "Hardware-Security-Keys-YubiKey-Nitrokey-Smart-Cards-and-PIV"):
        assert f"]({target}.md)" in tail, target
        assert (WIKI / f"{target}.md").exists(), target
    assert "no link" not in tail and "not written yet" not in text()
    assert "Hardware-Security-Keys-YubiKey-Nitrokey-Smart-Cards-and-PIV.md" in text()


def test_tuxedo_is_a_dated_user_selectable_option_on_one_model_not_a_shipped_default():
    body = text()
    sec = vendor_section(body, "Tuxedo Computers")
    assert "2018-03-14" in sec and "InfinityBook Pro 13" in sec
    assert "TUXEDO-disables-Intels-Management-Engine.tuxedo" in sec
    assert "Ask Tuxedo in writing" not in body
    assert "ships with the ME disabled" not in body.replace('not "ships with the ME disabled"', "")
    reg_rows = [r for r in register_rows(body) if "press release" in r[0] and "Tuxedo" in r[0]]
    assert reg_rows and "2018-03-14" in reg_rows[0][0] and "TUXEDO-disables" in reg_rows[0][1]
