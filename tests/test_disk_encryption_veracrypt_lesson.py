# SPDX-License-Identifier: Apache-2.0
"""The disk and file encryption lesson: it is registered, honest about what was run, dated and safe to follow.

docs/wiki/Disk-and-File-Encryption-VeraCrypt-TrueCrypt-History-BitLocker-FileVault-and-LUKS.md teaches encryption at
rest, the three built-in disk encryptions, VeraCrypt, and the dated TrueCrypt history. A broken link, a missing
registration, a real-looking password in a command, an undated history claim or an unfinished placeholder would each
teach the wrong thing.
"""

import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Disk-and-File-Encryption-VeraCrypt-TrueCrypt-History-BitLocker-FileVault-and-LUKS"
PAGE = WIKI / f"{NAME}.md"
FENCE = re.compile(r"^[ ]*```(\w*)\n(.*?)^[ ]*```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
STATUS_WORDS = ("Read", "Observed", "**est.**")
# a literal password handed to the tool: -p 'x', --new-password='x', or PW='x'
LITERAL = re.compile(r"""(?:\s-p\s+|--new-password=|\bPW=)'([^']*)'""")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def blocks(tag: str) -> list[str]:
    return [textwrap.dedent(b) for t, b in FENCE.findall(text()) if t == tag]


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1].split("## Not verified, plainly")[0]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def non_placeholder_passwords(commands: str) -> list[str]:
    return [p for p in LITERAL.findall(commands) if "PLACEHOLDER" not in p]


def test_the_page_exists_and_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Disk and file encryption")
    assert "Status: unverified draft" in body
    assert "**Not run:**" in body and "2026-11-07" in body
    for named in ("a hidden volume", "a keyfile", "BitLocker", "FileVault"):
        assert named in body.split("**Not run:**")[1].split("Vendor and project statements")[0], named
    assert "Not verified, plainly" in body


def test_no_unfinished_placeholder_is_left_in_the_page():
    body = text()
    assert "RESULTS_" not in body and "TODO" not in body and "@@" not in body


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 8, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_the_lesson_is_registered_everywhere():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    entry = nav.split(f"page: {NAME},")[1].split("\n")[0]
    assert 'status: "draft"' in entry
    for special in ("Contents.md", "_Sidebar.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [l for l in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in l]
    assert len(rows) >= 10, "expected glossary rows for the new terms"


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-") for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_no_addresses_no_em_dashes():
    body = text()
    assert "—" not in body
    assert not ADDR.findall(body), ADDR.findall(body)


def test_the_address_guard_bites():
    assert ADDR.findall("ping 192.0.2.7")


def test_every_password_in_a_command_is_a_labeled_placeholder():
    cmds = "\n".join(blocks("bash"))
    literals = LITERAL.findall(cmds)
    assert len(literals) >= 4, "the guard collected too few passwords"
    assert not non_placeholder_passwords(cmds), non_placeholder_passwords(cmds)
    assert "Never type a password you use anywhere real" in text()


def test_the_password_guard_bites():
    assert non_placeholder_passwords("veracrypt -C x -p 'hunter2'") == ["hunter2"]
    assert non_placeholder_passwords("veracrypt -C x -p 'Wrong-PLACEHOLDER-2'") == []


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n\n## Not verified, plainly\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_truecrypt_history_is_dated_and_quotes_the_notice():
    body = text()
    section = body.split("## From TrueCrypt to VeraCrypt: a dated history")[1].split("## Where it fits")[0]
    for date in ("2014-04-14", "2014-05-28", "2014-09-04", "2014-12-30", "2015-04-02", "2015-08-05", "2016-10-17", "2023-10-01", "2026-06-09"):
        assert date in section, date
    assert "WARNING: Using TrueCrypt is not secure as it may contain unfixed security issues" in section
    assert "two High, none Medium, one Low, one Undetermined" in section
    assert "8 critical, 3 medium and 15 low" in section
    assert "(secondary)" in section, "Wikipedia-only rows must be marked secondary"


def test_hidden_volumes_are_given_with_their_honest_limits():
    body = text()
    section = body.split("### Hidden volumes and plausible deniability, with the limits")[1].split("### Use across")[0]
    for needle in ("several points over time", "wear-leveling", "TRIM", "1.18a", "must recreate both the outer and hidden volumes", "legal"):
        assert needle in section, needle


def test_the_three_platform_tools_and_the_comparison_are_present():
    section = text().split("## Full-disk encryption by platform")[1].split("## Three layers")[0]
    for needle in ("BitLocker", "FileVault", "LUKS", "XTS", "recovery key", "TPM"):
        assert needle in section, needle


def test_the_defaults_quoted_match_the_documentation_values():
    body = text()
    assert "500,000 iterations" in body and "200,000" in body
    assert "416 MiB" in body and "6 passes" in body
