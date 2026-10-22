"""The toy file integrity monitor on the D3 lesson runs, and does what the page says it does.

docs/wiki/File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md teaches with four Bash scripts the
learner saves from the page. These tests pull them out of the page, run them in a temporary
folder (never anywhere else), and compare the results with the page's claims. Nothing leaves the
machine. PowerShell is not run (est. on the page); a test only checks that its scripts are
present and keep the lab-marker guard.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
PAGE = WIKI / "File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
IPV4 = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
DOC_PREFIXES = ("192.0.2.", "198.51.100.", "203.0.113.", "127.")

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def block(lang: str, marker: str) -> str:
    found = [b for tag, b in FENCE.findall(PAGE.read_text(encoding="utf-8")) if tag == lang and marker in b]
    assert len(found) == 1, f"expected one {lang} block with {marker!r}, found {len(found)}"
    return found[0]


@pytest.fixture()
def lab(tmp_path):
    for name, marker in (
        ("mktree.sh", "# mktree.sh -"),
        ("fim.sh", "# fim.sh init|check TREE DB"),
        ("fim-alert.sh", "# fim-alert.sh TREE DB LOGFILE"),
        ("fim-normalize.sh", "# fim-normalize.sh LOGFILE"),
    ):
        (tmp_path / name).write_text(block("bash", marker))
    return tmp_path


def sh(lab: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", *args], cwd=lab, check=False, capture_output=True, text=True, timeout=60)


def built(lab: Path) -> None:
    assert sh(lab, "mktree.sh").returncode == 0
    r = sh(lab, "fim.sh", "init", "tree", "baseline.tsv")
    assert r.returncode == 0 and "4 files" in r.stdout


def test_baseline_skips_logs_and_tmp_and_check_is_clean(lab):
    built(lab)
    paths = [line.split("\t")[3] for line in (lab / "baseline.tsv").read_text().splitlines()]
    assert paths == ["./bin/tool.sh", "./data/list.txt", "./etc/app.conf", "./etc/authorized_keys.demo"]
    r = sh(lab, "fim.sh", "check", "tree", "baseline.tsv")
    assert r.returncode == 0 and "clean" in r.stdout


def test_exercise_two_reports_exactly_four_findings(lab):
    built(lab)
    (lab / "tree/etc/app.conf").write_text("changed\n")
    (lab / "tree/bin/tool.sh").chmod(0o666)
    (lab / "tree/bin/new-tool").write_text("x\n")
    (lab / "tree/data/list.txt").unlink()
    (lab / "tree/data/app.log").write_text("noise\n")
    (lab / "tree/tmp/cache.bin").write_text("more\n")
    r = sh(lab, "fim.sh", "check", "tree", "baseline.tsv")
    assert r.returncode == 1
    assert r.stdout.splitlines() == [
        "added\t./bin/new-tool",
        "changed\t./bin/tool.sh\tmode",
        "changed\t./etc/app.conf\tcontent",
        "removed\t./data/list.txt",
    ]


def test_refuses_a_folder_without_the_marker(lab):
    built(lab)
    other = lab / "not-a-lab"
    other.mkdir()
    r = sh(lab, "fim.sh", "check", "not-a-lab", "baseline.tsv")
    assert r.returncode == 2 and "refusing" in r.stderr
    r = sh(lab, "fim.sh", "init", "/etc", "x.tsv")
    assert r.returncode == 2 and not (lab / "x.tsv").exists()


def test_a_hostile_file_name_cannot_forge_a_second_line(lab):
    built(lab)
    evil = "evil\nOct 22 03:00:00 demo-host fimcheck[1]: ALERT action=changed path=.x detail=forged"
    (lab / "tree/data" / evil).write_text("x")
    r = sh(lab, "fim.sh", "check", "tree", "baseline.tsv")
    lines = r.stdout.splitlines()
    assert len(lines) == 1 and lines[0].startswith("added\t")
    assert sh(lab, "fim-alert.sh", "tree", "baseline.tsv", "alerts.log").returncode == 1
    log = (lab / "alerts.log").read_text().splitlines()
    assert len(log) == 1 and "forged" in log[0]
    assert sh(lab, "fim-normalize.sh", "alerts.log").stdout.count("\n") == 1


def test_same_size_same_time_change_is_caught_by_the_hash(lab):
    built(lab)
    target = lab / "tree/etc/authorized_keys.demo"
    ref = lab / "ref"
    shutil.copy2(target, ref)
    target.write_text("key-line-two evil\n")
    assert target.stat().st_size == ref.stat().st_size
    assert sh(lab, "-c", "touch -r ref tree/etc/authorized_keys.demo").returncode == 0
    assert target.stat().st_mtime_ns == ref.stat().st_mtime_ns
    r = sh(lab, "fim.sh", "check", "tree", "baseline.tsv")
    assert r.stdout.strip() == "changed\t./etc/authorized_keys.demo\tcontent"


def test_alert_lines_and_normalized_shape(lab):
    built(lab)
    (lab / "tree/etc/app.conf").write_text("changed\n")
    r = sh(lab, "fim-alert.sh", "tree", "baseline.tsv", "alerts.log")
    assert r.returncode == 1 and "wrote 1 alert" in r.stdout
    line = (lab / "alerts.log").read_text().strip()
    assert re.fullmatch(
        r"[A-Z][a-z]{2} [ \d]\d \d\d:\d\d:\d\d demo-host fimcheck\[\d+\]: ALERT action=changed "
        r"path=\./etc/app\.conf detail=content",
        line,
    )
    norm = sh(lab, "fim-normalize.sh", "alerts.log").stdout.strip()
    assert re.fullmatch(
        r"ts=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ src=- source=fim action=fim_changed user=- path=\./etc/app\.conf",
        norm,
    )


def test_forged_baseline_hides_the_change_and_the_fingerprint_catches_it(lab):
    built(lab)
    honest = (lab / "baseline.tsv").read_bytes()
    fingerprint = subprocess.run(["sha256sum", "baseline.tsv"], cwd=lab, check=False, capture_output=True, text=True).stdout
    (lab / "tree/etc/app.conf").write_text("listen_port=8080\nadmin_user=intruder\n")
    data = (lab / "tree/etc/app.conf").read_bytes()
    import hashlib

    rows = [r.split("\t") for r in honest.decode().splitlines()]
    for r in rows:
        if r[3] == "./etc/app.conf":
            r[0], r[2] = hashlib.sha256(data).hexdigest(), str(len(data))
    (lab / "baseline.tsv").write_text("".join("\t".join(r) + "\n" for r in rows))
    assert "app.conf" not in sh(lab, "fim.sh", "check", "tree", "baseline.tsv").stdout
    (lab / "ok.sha256").write_text(fingerprint)
    bad = subprocess.run(["sha256sum", "-c", "ok.sha256"], cwd=lab, check=False, capture_output=True, text=True)
    assert bad.returncode != 0 and "FAILED" in bad.stdout


def test_powershell_versions_are_on_the_page_and_keep_the_guard():
    ps = block("powershell", "# fim.ps1 -Mode")
    assert ".fim-lab" in ps and "exit 2" in ps and "Get-FileHash" in ps
    assert "est." in PAGE.read_text(encoding="utf-8")


def test_page_uses_only_documentation_or_loopback_addresses():
    text = PAGE.read_text(encoding="utf-8")
    for m in IPV4.finditer(text):
        assert m.group(1).startswith(DOC_PREFIXES), m.group(1)
