"""Tests for scripts/identifier_check.py.

Realistic-looking identifiers are assembled at run time from pieces, so this
file does not itself contain one and the check passes over its own tests.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "identifier_check.py"
spec = importlib.util.spec_from_file_location("identifier_check", SCRIPT)
ic = importlib.util.module_from_spec(spec)
sys.modules["identifier_check"] = ic
spec.loader.exec_module(ic)

A = "2109" + "87654321"
KEY = "Q7ZXCV" + "BNMASDFGHJ"  # 16 characters
SUB = "9c1e4b7a-" + "52d3-4f08-" + "a6b1-" + "3d7e90c2f845"
G = "acme-" + "lab-" + "483920"
Z = "00000000-0000-0000-0000-000000000000"

AWS_ARN = "AWS ARN account id"
AWS_ACCT = "AWS account id"
AWS_KEY = "AWS access key id"
AZ = "Azure subscription or tenant id"
AZ_PATH = "Azure subscription id in a resource path"
AZ_URL = "Azure tenant id in a sign-in URL"
GCP = "GCP project id"
GCP_PATH = "GCP project id in a resource path"

REAL = [
    (AWS_ARN, f"arn:aws:iam::{A}:role/deployer"),
    (AWS_ARN, f"  role = arn:aws:s3:eu-west-1:{A}:bucket/x"),
    (AWS_ARN, f"arn:aws:iam::{A}"),
    (AWS_ARN, f"ARN:AWS:IAM::{A}:root"),
    (AWS_ARN, f"<arn:aws:iam::<{A}>:role/x>"),
    (AWS_ACCT, f"account_id = {A}"),
    (AWS_ACCT, f'"aws_account": "{A}"'),
    (AWS_ACCT, f"Account ID: {A}"),
    (AWS_ACCT, f"account_number = {A}"),
    (AWS_ACCT, f"Account #{A}"),
    (AWS_ACCT, f"TF_VAR_aws_account_id={A}"),
    (AWS_ACCT, f"account_id = <{A}>"),
    (AWS_ACCT, f"<!-- account_id: <{A}> -->"),
    (AWS_ACCT, f"<https://console.aws.amazon.com/iam/home?account=<{A}>>"),
    (AWS_ACCT, f'<a href="https://x/?account=<{A}>">'),
    (AWS_ACCT, f"{A}.dkr.ecr.us-east-1.amazonaws.com/app:1"),
    (AWS_ACCT, f"https://{A}.signin.aws.amazon.com/console"),
    (AWS_ACCT, f'"OwnerId": "{A}"'),
    (AWS_KEY, f"key = AKIA{KEY}"),
    (AWS_KEY, f"k: ASIA{KEY}"),
    (AWS_KEY, f"AIDA{KEY}"),
    (AWS_KEY, f"AGPA{KEY}"),
    (AWS_KEY, f"ANPA{KEY}"),
    (AWS_KEY, f"ABIA{KEY}"),
    (AWS_KEY, f"AROA{KEY}"),
    (AWS_KEY, f"x_AKIA{KEY}"),
    (AZ, f'subscription_id = "{SUB}"'),
    (AZ, f"tenant_id: {SUB}"),
    (AZ, f"ARM_SUBSCRIPTION_ID={SUB}"),
    (AZ, f"ARM_TENANT_ID={SUB}"),
    (AZ, f"AZURE_TENANT_ID={SUB}"),
    (AZ, f'"homeTenantId": "{SUB}"'),
    (AZ, f'"id": "{SUB}"'),
    (AZ, f"subscription_id = <{SUB}>"),
    (AZ_PATH, f"/subscriptions/{SUB}/resourceGroups/rg"),
    (AZ_URL, f"https://login.microsoftonline.com/{SUB}/oauth2/v2.0/token"),
    (GCP, f'project_id = "{G}"'),
    (GCP, f"project: {G}"),
    (GCP, f'project = "{G}"'),
    (GCP, f"  project = {G}"),
    (GCP, f"GOOGLE_PROJECT={G}"),
    (GCP, f"GOOGLE_CLOUD_PROJECT={G}"),
    (GCP, f"CLOUDSDK_CORE_PROJECT={G}"),
    (GCP, f"gcloud run deploy --project {G}"),
    (GCP, f"gcloud run deploy --project={G}"),
    (GCP, f"gcloud config set project {G}"),
    (GCP, f"https://console.cloud.google.com/home?project={G}"),
    (GCP_PATH, f"projects/{G}/locations/global"),
]

SYNTHETIC = [
    "arn:aws:iam::123456789012:role/deployer",
    "arn:aws:iam::000000000000:root",
    "arn:aws:iam::<account-id>:role/x",
    "account_id = 111122223333",
    "Account ID: 123456789012",
    "aws_account = 000000000000",
    "account_number = 123456789012",
    "Account #111122223333",
    "TF_VAR_aws_account_id=123456789012",
    "account_id = <account-id>",
    "123456789012.dkr.ecr.us-east-1.amazonaws.com/app:1",
    "https://000000000000.signin.aws.amazon.com/console",
    '"OwnerId": "000000000000"',
    "AKIAIOSFODNN7EXAMPLE",
    "AIDAIOSFODNN7EXAMPLE",
    "AROAEXAMPLEEXAMPLE12",
    f"subscription_id = {Z}",
    "tenant_id = 11111111-1111-1111-1111-111111111111",
    f"ARM_SUBSCRIPTION_ID={Z}",
    f"ARM_TENANT_ID={Z}",
    f"AZURE_TENANT_ID={Z}",
    f'"homeTenantId": "{Z}"',
    f'"id": "{Z}"',
    f"/subscriptions/{Z}/resourceGroups/rg",
    f"https://login.microsoftonline.com/{Z}/oauth2/v2.0/token",
    "subscription_id = 9c1e4b7a-52d3-4f08-a6b1-example00000",
    "project_id = my-project-id",
    'project_id = "your-project-id"',
    "project: project-id",
    'project = "my-project-id"',
    "project = my-project-id",
    "GOOGLE_PROJECT=your-project-id",
    "GOOGLE_CLOUD_PROJECT=my-project-id",
    "CLOUDSDK_CORE_PROJECT=project-id",
    "gcloud run deploy --project my-project-id",
    "gcloud run deploy --project=your-project-id",
    "gcloud config set project my-project-id",
    "https://console.cloud.google.com/home?project=my-project-id",
    "projects/acme-example-123456/locations",
    "project = <your-project>",
    "project_id = var.project_id",
    "project_id = local.project",
    "project = digitalocean_project.main.id",
    "subscription_id = var.subscription_id",
    "Account 12345 is fine, and so is a bare " + "210987654321" + " with no label",
    "account_id = 2109876543210",
    "projects/1234",
]


@pytest.mark.parametrize(("kind", "line"), REAL)
def test_real_form_is_rejected(kind, line):
    assert kind in ic.scan_line(line)


@pytest.mark.parametrize("line", SYNTHETIC)
def test_synthetic_form_passes(line):
    assert ic.scan_line(line) == []


def test_every_rule_has_a_red_fixture():
    """A rule nobody exercises could be deleted without a test noticing."""
    for index, (kind, pattern) in enumerate(ic.PATTERNS):
        hits = [
            line
            for k, line in REAL
            if k == kind
            and any(not ic.is_allowed(m.group("v")) for m in pattern.finditer(line))
        ]
        assert hits, f"no red fixture matches PATTERNS[{index}] ({kind})"


def test_real_id_inside_angle_brackets_is_still_a_finding():
    for line in (f"account_id = <{A}>", f"<{A}>.dkr.ecr.eu-west-1.amazonaws.com"):
        assert ic.scan_line(line)


MARKER_OK = [
    "account_id = {A}  # identifier-check: ignore",
    "account_id = {A}  // identifier-check: ignore because reasons",
    "<p>account_id: {A}</p> <!-- identifier-check: ignore -->",
]


@pytest.mark.parametrize("template", MARKER_OK)
def test_marker_in_a_trailing_comment_skips_the_line(template):
    assert ic.scan_line(template.format(A=A)) == []


def test_marker_outside_a_comment_does_not_skip():
    assert ic.scan_line(f"https://x/identifier-check: ignore?account_id={A}")
    assert ic.scan_line(f"account_id = {A}  identifier-check: ignore")


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


def seed(tmp_path: Path, rel: str, text: str = "", data: bytes | None = None) -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if data is None:
        p.write_text(text, encoding="utf-8")
    else:
        p.write_bytes(data)


def test_walk_reports_file_line_and_kind_without_any_value(tmp_path, capsys):
    seed(tmp_path, "docs/a.md", f"ok\nrole: arn:aws:iam::{A}:role/x\n")
    seed(tmp_path, "main.tf", f'project_id = "{G}"\n')
    seed(tmp_path, "clean.md", "account_id = 123456789012\n")
    assert ic.main(["--root", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert "docs/a.md:2: AWS ARN account id" in out
    assert "main.tf:1: GCP project id" in out
    assert "clean.md" not in out
    for secret in (A, G, SUB, KEY, A[:2] + "..."):
        assert secret not in out


def test_clean_tree_passes_and_reports_counts(tmp_path, capsys):
    seed(tmp_path, "a.md", "account_id = 123456789012\n")
    seed(tmp_path, "b.md", f"account_id = {A} # identifier-check: ignore\n")
    assert ic.main(["--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "passed" in out
    assert "2 files scanned" in out
    assert "1 ignore markers used" in out


def test_plans_directory_and_vendor_dirs_are_skipped(tmp_path):
    line = f"account_id = {A}\n"
    seed(tmp_path, "docs/superpowers/plans/p.md", line)
    seed(tmp_path, ".terraform/x.txt", line)
    seed(tmp_path, ".venv/x.txt", line)
    seed(tmp_path, "ok.md", "nothing\n")
    assert ic.run(tmp_path).problems == []


def test_latin1_file_is_scanned(tmp_path):
    seed(tmp_path, "l.txt", data=b"caf\xe9\naccount_id = " + A.encode() + b"\n")
    assert ic.run(tmp_path).problems == ["l.txt:2: AWS account id"]


def test_invalid_utf8_stray_byte_does_not_hide_ids(tmp_path):
    seed(tmp_path, "s.txt", data=b"\xff\xff\n" + f"arn:aws:iam::{A}:root\n".encode())
    assert ic.run(tmp_path).problems == ["s.txt:2: AWS ARN account id"]


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le", "utf-16-be"])
def test_utf16_file_with_bom_is_scanned(tmp_path, encoding):
    text = f"account_id = {A}\n"
    data = text.encode(encoding)
    if encoding != "utf-16":
        data = (b"\xff\xfe" if encoding.endswith("le") else b"\xfe\xff") + data
    seed(tmp_path, "u.txt", data=data)
    assert ic.run(tmp_path).problems == ["u.txt:1: AWS account id"]


def test_file_over_one_megabyte_is_scanned(tmp_path):
    filler = ("x" * 99 + "\n") * 12000  # about 1.2 MB
    seed(tmp_path, "big.txt", filler + f"account_id = {A}\n")
    assert (tmp_path / "big.txt").stat().st_size > 1_000_000
    assert ic.run(tmp_path).problems == ["big.txt:12001: AWS account id"]


def test_binary_file_is_counted_not_scanned(tmp_path, capsys):
    seed(tmp_path, "b.bin", data=b"\x89PNG\x00\x00" + A.encode())
    seed(tmp_path, "t.md", "hello\n")
    result = ic.run(tmp_path)
    assert result.problems == []
    assert result.binary == 1
    assert result.scanned == 1


def test_oversize_file_fails_instead_of_skipping(tmp_path, monkeypatch):
    monkeypatch.setattr(ic, "MAX_BYTES", 10)
    seed(tmp_path, "huge.txt", "x" * 100)
    seed(tmp_path, "t.md", "hi\n")
    assert ic.main(["--root", str(tmp_path)]) == 1


def test_missing_root_fails(tmp_path, capsys):
    assert ic.main(["--root", str(tmp_path / "nope")]) != 0
    assert "passed" not in capsys.readouterr().out


def test_root_that_is_a_file_fails(tmp_path, capsys):
    seed(tmp_path, "f.txt", "x\n")
    assert ic.main(["--root", str(tmp_path / "f.txt")]) != 0
    assert "passed" not in capsys.readouterr().out


def test_empty_root_fails(tmp_path, capsys):
    assert ic.main(["--root", str(tmp_path)]) != 0
    out = capsys.readouterr().out
    assert "passed" not in out
    assert "no files were scanned" in out


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_tracked_files_are_used_inside_a_repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    seed(tmp_path, "tracked.md", f"account_id = {A}\n")
    seed(tmp_path, "untracked.md", f"account_id = {A}\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "tracked.md"], check=True)
    assert ic.run(tmp_path).problems == ["tracked.md:1: AWS account id"]


@pytest.mark.parametrize(
    "line",
    [
        "account" + " " * 20000,
        " " * 1_000_000,
        "account " * 100000,
        "project" + " " * 20000,
        "account" + " " * 20000 + "x",
        "account_id" + "\t" * 20000,
        "owner_id" + " " * 20000 + ":",
        'project = "' + "a" * 20000,
    ],
)
def test_pathological_line_scans_fast(line):
    start = time.perf_counter()
    ic.find_kinds(line)
    assert time.perf_counter() - start < 1.0


def test_the_repository_itself_is_clean():
    root = SCRIPT.parent.parent
    assert ic.main(["--root", str(root)]) == 0
