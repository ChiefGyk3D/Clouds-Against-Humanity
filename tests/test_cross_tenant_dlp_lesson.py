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


sys.path.insert(0, str(LAB))


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
    assert names == ["batch/parts.txt:1", "batch/payments.txt:1", "batch/payments.txt:2", "mail/outbox.mbox#msg2", "mail/outbox.mbox#msg4"]
    for hits in found.values():
        for h in hits:
            assert "*" in h["masked"] and len(h["masked"].replace("*", "")) <= 2
    tuned = scan.scan_path(tmp_path, {"QX-123456-ZZ"}, 2)
    assert "batch/parts.txt:1" not in tuned and len(tuned) == 4
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


def run_start(work, *args, env_extra=None):
    import os
    import subprocess

    env = {**os.environ, "LAB_WORK": str(work), **(env_extra or {})}
    return subprocess.run(
        ["bash", str(LAB / "start_tenants.sh"), *args], env=env, check=False, capture_output=True, text=True, timeout=60
    )


def test_start_script_text_has_the_private_folder_checks():
    s = (LAB / "start_tenants.sh").read_text()
    assert "/tmp" not in s and "TMPDIR" not in s
    for needle in ("mkdir -m 700", "-O \"$WORK\"", "-L \"$WORK\"", "group or other writable", "^[0-9]+$", "moto.server"):
        assert needle in s, needle
    assert "pkill" not in s and "pgrep" not in s
    assert "/tmp/" not in PAGE.read_text()


def test_start_script_refuses_a_group_or_other_writable_folder(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    shared.chmod(0o777)
    r = run_start(shared, "status")
    assert r.returncode != 0 and "writable" in r.stderr
    shared.chmod(0o770)
    assert run_start(shared, "status").returncode != 0


def test_start_script_refuses_a_symlink_and_makes_a_private_folder(tmp_path):
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(real)
    r = run_start(link, "status")
    assert r.returncode != 0 and "symlink" in r.stderr
    fresh = tmp_path / "a" / "fresh"
    r = run_start(fresh, "status")
    assert r.returncode == 0 and (fresh.stat().st_mode & 0o777) == 0o700


def test_down_ignores_a_pid_file_that_is_not_a_moto_server(tmp_path):
    import subprocess

    work = tmp_path / "w"
    work.mkdir(mode=0o700)
    victim = subprocess.Popen(["sleep", "60"])
    try:
        (work / "a.pid").write_text(str(victim.pid))
        (work / "b.pid").write_text("123; echo pwned")
        r = run_start(work, "down")
        assert r.returncode == 0
        assert victim.poll() is None  # not killed: its command line is not a moto server
    finally:
        victim.kill()
        victim.wait()


def test_private_dir_helper_refuses_open_folders(tmp_path):
    import pytest

    labdir = load("labdir")
    open_dir = tmp_path / "open"
    open_dir.mkdir()
    open_dir.chmod(0o777)
    with pytest.raises(SystemExit):
        labdir.private_dir(open_dir)
    made = labdir.private_dir(tmp_path / "x" / "new")
    assert (made.stat().st_mode & 0o777) == 0o700


def test_same_file_name_in_two_folders_is_reported_twice(tmp_path):
    scan = load("dlp_scan")
    for d in ("a", "b"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "data.csv").write_text("member QX-111111-ZZ\n")
    assert sorted(scan.scan_path(tmp_path, set(), 2)) == ["a/data.csv:1", "b/data.csv:1"]


def test_transfer_role_is_write_only_in_the_narrow_policy():
    text = (LAB / "tenants_setup.py").read_text()
    stmt = text[text.index("AllowMonthlyTransferWriteOnly"):text.index("AllowDestinationProcessorReadAndPurge")]
    assert "s3:GetObject" not in stmt and "s3:DeleteObject" not in stmt
