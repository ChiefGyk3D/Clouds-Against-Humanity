# SPDX-License-Identifier: Apache-2.0
"""The hardware security modules lesson: it is registered, honest about what was run, and safe to follow.

docs/wiki/Hardware-Security-Modules-What-They-Are-and-Building-Your-Own-with-pico2hsm.md teaches what an HSM is and
walks a learner through an untested pico2hsm exercise. A missing registration, a broken link, a published sample PIN,
a claim with no status, or the untested marking going missing would each teach the wrong thing.
"""

import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Hardware-Security-Modules-What-They-Are-and-Building-Your-Own-with-pico2hsm"
PAGE = WIKI / f"{NAME}.md"
FENCE = re.compile(r"^[ ]*```(\w*)\n(.*?)^[ ]*```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
STATUS_WORDS = ("Read", "Observed", "General knowledge", "**est.**")
SAMPLE_PINS = ("648219", "3537363231383830", "57621880")  # the values the project's own docs publish


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def test_the_page_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Hardware security modules")
    assert "Status: unverified draft" in body
    assert "**Not run:**" in body and "2026-11-07" in body
    assert "no Pico 2 was available" in body


def test_part_b_is_marked_untested_and_the_maintainer_checks_exist():
    body = text()
    assert "Part B: the same on a Pico 2 (UNTESTED)" in body
    assert "**Untested.**" in body
    checks = body.split("## For the maintainer: checks to run when you build it")[1].split("## Checkpoint")[0]
    assert len(re.findall(r"^\d+\. ", checks, re.MULTILINE)) >= 10


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 6, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_the_lesson_is_registered_everywhere():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav and 'status: "draft"' in nav.split(f"page: {NAME},")[1].split("\n")[0]
    for special in ("Contents.md", "_Sidebar.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [row for row in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in row]
    assert len(rows) >= 5, "expected glossary rows for the new terms"


def test_glossary_rows_point_at_real_headings():
    def slug(h: str) -> str:
        return re.sub(r"[^a-z0-9-]", "", h.lower().replace(" ", "-"))

    heads = {slug(h) for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_no_em_dashes_and_no_published_sample_pins():
    body = text()
    assert "—" not in body
    found = [p for p in SAMPLE_PINS if p in body]
    assert not found, found


def test_the_pin_guard_bites():
    assert [p for p in SAMPLE_PINS if p in "sc-hsm-tool --pin 648219"] == ["648219"]


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_page_quotes_the_projects_own_limits():
    body = text()
    assert "not a certified secure element" in body
    assert "Never deploy either: the development storage key is public." in body
    assert "A4" in body and "RP2350-E24" in body


@pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl is not installed")
def test_part_a_signs_verifies_and_fails_on_a_changed_message(tmp_path):
    block = next(textwrap.dedent(b) for t, b in FENCE.findall(text()) if t == "bash" and "ecparam" in b)
    steps = block.replace("mkdir -p ~/hsmlab && cd ~/hsmlab", f"cd {tmp_path}")
    steps = steps.split("# 4.")[0]  # up to and including the first verify
    ok = subprocess.run(["bash", "-eu", "-c", steps], capture_output=True, text=True, timeout=60, check=False)
    assert ok.returncode == 0, ok.stderr
    assert "Verified OK" in ok.stdout + ok.stderr
    bad = subprocess.run(
        ["bash", "-c", f"cd {tmp_path} && echo tamper >> msg.txt && openssl dgst -sha256 -verify pub.der -keyform DER -signature sig.bin msg.txt"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert bad.returncode != 0
