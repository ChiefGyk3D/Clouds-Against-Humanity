"""Tests for scripts/identifier_check.py.

Realistic-looking identifiers are assembled at run time from pieces, so this
file does not itself contain one and the check passes over its own tests.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "identifier_check.py"
spec = importlib.util.spec_from_file_location("identifier_check", SCRIPT)
ic = importlib.util.module_from_spec(spec)
sys.modules["identifier_check"] = ic
spec.loader.exec_module(ic)

ACCT = "2109" + "87654321"
KEY = "AKIA" + "Q7ZXCVBNMASDFGHJ"
SUB = "9c1e4b7a-" + "52d3-4f08-" + "a6b1-" + "3d7e90c2f845"
GCP = "acme-" + "lab-" + "483920"

REAL = [
    ("AWS ARN account id", f"arn:aws:iam::{ACCT}:role/deployer"),
    ("AWS ARN account id", f"  role = arn:aws:s3:eu-west-1:{ACCT}:bucket/x"),
    ("AWS account id", f"account_id = {ACCT}"),
    ("AWS account id", f'"aws_account": "{ACCT}"'),
    ("AWS account id", f"Account ID: {ACCT}"),
    ("AWS access key id", f"key = {KEY}"),
    ("AWS access key id", "k: " + "ASIA" + "Q7ZXCVBNMASDFGHJ"),
    ("Azure subscription or tenant id", f'subscription_id = "{SUB}"'),
    ("Azure subscription or tenant id", f"tenant_id: {SUB}"),
    (
        "Azure subscription id in a resource path",
        f"/subscriptions/{SUB}/resourceGroups/rg",
    ),
    ("GCP project id", f'project_id = "{GCP}"'),
    ("GCP project id", f"project: {GCP}"),
    ("GCP project id in a resource path", f"projects/{GCP}/locations/global"),
]

SYNTHETIC = [
    "arn:aws:iam::123456789012:role/deployer",
    "arn:aws:iam::000000000000:root",
    "account_id = 111122223333",
    "Account ID: 123456789012",
    "aws_account = 000000000000",
    "AKIAIOSFODNN7EXAMPLE",
    "subscription_id = 00000000-0000-0000-0000-000000000000",
    "tenant_id = 11111111-1111-1111-1111-111111111111",
    "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg",
    "subscription_id = 9c1e4b7a-52d3-4f08-a6b1-example00000",
    "project_id = my-project-id",
    'project_id = "your-project-id"',
    "project: project-id",
    "projects/acme-example-123456/locations",
    "arn:aws:iam::<account-id>:role/x",
    "account_id = <" + "210987654321" + ">",
    "project_id = var.project_id",
    "project_id = local.project",
    "Account 12345 is fine, and so is a bare " + "210987654321" + " with no label",
    "account_id = 2109876543210",
    "projects/1234",
    "subscription_id = var.subscription_id",
]


@pytest.mark.parametrize(("kind", "line"), REAL)
def test_real_form_is_rejected(kind, line):
    assert kind in [k for k, _ in ic.scan_line(line)]


@pytest.mark.parametrize("line", SYNTHETIC)
def test_synthetic_form_passes(line):
    assert ic.scan_line(line) == []


def test_ignore_marker_skips_the_line():
    assert ic.scan_line(f"account_id = {ACCT}  # identifier-check: ignore") == []


def test_allow_list_is_the_documented_set():
    assert ic.ALLOWED_VALUES == {
        "123456789012",
        "000000000000",
        "111122223333",
        "00000000-0000-0000-0000-000000000000",
        "11111111-1111-1111-1111-111111111111",
        "my-project-id",
        "your-project-id",
        "project-id",
    }


def seed(tmp_path: Path, rel: str, text: str) -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_walk_reports_file_line_and_kind_without_the_value(tmp_path, capsys):
    seed(tmp_path, "docs/a.md", f"ok\nrole: arn:aws:iam::{ACCT}:role/x\n")
    seed(tmp_path, "main.tf", f'project_id = "{GCP}"\n')
    seed(tmp_path, "clean.md", "account_id = 123456789012\n")
    assert ic.main(["--root", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "docs/a.md:2: AWS ARN account id" in out
    assert "main.tf:1: GCP project id" in out
    assert "clean.md" not in out
    for secret in (ACCT, GCP, SUB, KEY):
        assert secret not in out
    assert "21..." in out


def test_clean_tree_passes(tmp_path, capsys):
    seed(tmp_path, "a.md", "account_id = 123456789012\n")
    assert ic.main(["--root", str(tmp_path)]) == 0
    assert "passed" in capsys.readouterr().out


def test_plans_directory_and_vendor_dirs_are_skipped(tmp_path):
    line = f"account_id = {ACCT}\n"
    seed(tmp_path, "docs/superpowers/plans/p.md", line)
    seed(tmp_path, ".terraform/x.txt", line)
    seed(tmp_path, ".venv/x.txt", line)
    assert ic.run(tmp_path) == []


def test_binary_file_is_ignored(tmp_path):
    (tmp_path / "b.bin").write_bytes(b"\xff\xfe\x00" + ACCT.encode())
    assert ic.run(tmp_path) == []


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_tracked_files_are_used_inside_a_repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    seed(tmp_path, "tracked.md", f"account_id = {ACCT}\n")
    seed(tmp_path, "untracked.md", f"account_id = {ACCT}\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "tracked.md"], check=True)
    problems = ic.run(tmp_path)
    assert len(problems) == 1
    assert problems[0].startswith("tracked.md:1")


def test_mutation_removing_the_arn_pattern_is_visible(monkeypatch):
    """If the ARN regex stopped matching, an ARN fixture would pass silently."""
    line = f"arn:aws:iam::{ACCT}:role/deployer"
    assert any(k == "AWS ARN account id" for k, _ in ic.scan_line(line))
    mutated = tuple(
        (k, re.compile(r"arn:NEVER")) if k == "AWS ARN account id" else (k, p)
        for k, p in ic.PATTERNS
    )
    monkeypatch.setattr(ic, "PATTERNS", mutated)
    assert not any(k == "AWS ARN account id" for k, _ in ic.scan_line(line))


def test_the_repository_itself_is_clean(capsys):
    root = SCRIPT.parent.parent
    assert ic.main(["--root", str(root)]) == 0
