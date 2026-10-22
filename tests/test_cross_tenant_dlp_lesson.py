"""Checks for the cross-tenant data flows lesson and its lab (no network, no moto needed).

The scanner and the fake-data builder are pure Python, so the page's claims about them are
tested directly: the Luhn validator, the threshold, the allowlist, masking, and that no
card-shaped literal is committed anywhere in the lab folder.
"""

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "labs" / "cross-tenant-dlp"
PAGE = ROOT / "docs" / "wiki" / "Cross-Tenant-Data-Governance-Retention-and-DLP.md"


def load(name):
    spec = importlib.util.spec_from_file_location(name, LAB / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_luhn_accepts_built_numbers_and_rejects_a_near_miss(tmp_path):
    import random

    fake = load("make_fake_data")
    scan = load("dlp_scan")
    good = fake.fake_card(random.Random(1), "411111")
    assert len(good) == 16 and scan.luhn_ok(good)
    bad = good[:-1] + str((int(good[-1]) + 1) % 10)
    assert not scan.luhn_ok(bad)


def test_scan_expected_findings_and_masking(tmp_path, monkeypatch):
    fake = load("make_fake_data")
    scan = load("dlp_scan")
    monkeypatch.setattr(sys, "argv", ["x", "--out", str(tmp_path)])
    fake.main()
    found = scan.scan_path(tmp_path, set(), 2)
    names = sorted(found)
    assert names == ["outbox.mbox#msg2", "outbox.mbox#msg4", "parts.txt:1", "payments.txt:1", "payments.txt:2"]
    for hits in found.values():
        for h in hits:
            assert "*" in h["masked"] and len(h["masked"].replace("*", "")) <= 2
    tuned = scan.scan_path(tmp_path, {"QX-123456-ZZ"}, 2)
    assert "parts.txt:1" not in tuned and len(tuned) == 4
    assert len(scan.scan_path(tmp_path, set(), 1)) > len(found)


def test_no_card_or_secret_shaped_literal_in_the_lab_or_page():
    card = re.compile(r"\b(?:4\d{15}|5[1-5]\d{14})\b")
    for p in [*(f for f in LAB.glob("*") if f.is_file()), PAGE]:
        assert not card.search(p.read_text()), p.name


def test_lab_files_carry_spdx_and_the_page_links_the_lab():
    for p in (f for f in LAB.glob("*") if f.is_file()):
        if p.suffix in {".py", ".sh", ".txt"}:
            assert "SPDX-License-Identifier: Apache-2.0" in p.read_text()[:300], p.name
    text = PAGE.read_text()
    assert "labs/cross-tenant-dlp" in text and "Next:" in text.splitlines()[2]
    assert "Zscaler" in text and "Twingate" in text and "does not claim it replaces" in text
