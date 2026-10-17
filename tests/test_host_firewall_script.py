"""Hermetic tests for the host-firewall script in the connector cloud-init.

The script is extracted from modules/twingate-bootstrap/cloud-init.yaml.tftpl
(undoing the template's `$$` escaping and the YAML block indentation, and
filling the two template variables) and run with fake `nft` and `ss` binaries
on a PATH that holds nothing else, inside a temporary directory. The real nft
is never invoked for a change: the one optional syntax check runs `nft -c`
(check only) in a throwaway user and network namespace and skips when that is
not possible. Nothing here touches this machine's firewall or any service.
"""

import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "modules/twingate-bootstrap/cloud-init.yaml.tftpl"
SCRIPT_PATH = "/usr/local/sbin/cah-host-firewall"
UNIT_PATH = "/etc/systemd/system/cah-host-firewall.service"
BASH = shutil.which("bash")
DEFAULT_SOURCES = "10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16"

pytestmark = pytest.mark.skipif(BASH is None, reason="bash is not available")


def _run(args, **kwargs):
    """subprocess.run that reports the exit code instead of raising."""
    return subprocess.run(args, check=False, **kwargs)


def extract_file(
    template_text: str, path: str, subs: dict[str, str] | None = None
) -> str:
    """The write_files content for `path`, as it lands on the machine."""
    lines = template_text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == f"- path: {path}"), None
    )
    assert start is not None, f"{path} is not written by the template"
    body: list[str] = []
    in_content = False
    for line in lines[start + 1 :]:
        if not in_content:
            if line.strip() == "content: |":
                in_content = True
            continue
        # The block scalar ends at the first line indented less than 6 spaces
        # that is not blank (the next "  - path:" entry or a %{ directive).
        if line.strip() and not line.startswith("      "):
            break
        body.append(line[6:] if line.startswith("      ") else "")
    assert body, f"{path} has no content"
    text = "\n".join(body).rstrip("\n") + "\n"
    for name, value in (subs or {}).items():
        text = text.replace("${" + name + "}", value)
    # tftpl: "$$" renders as "$"; any other "${...}" would be an interpolation.
    assert "${" not in text, "an unescaped template interpolation reached the script"
    return text.replace("$$", "$")


def extract_script(
    template_text: str,
    sources: str = DEFAULT_SOURCES,
    metrics_port: str = "",
    path: str = SCRIPT_PATH,
) -> str:
    return extract_file(
        template_text,
        path,
        {
            "host_firewall_ssh_sources": sources,
            "host_firewall_metrics_port": metrics_port,
        },
    )


GOOD_LISTING = (
    "table inet cah_host {\n"
    "\tchain input {\n"
    "\t\ttype filter hook input priority filter; policy drop;\n"
    "\t\ttcp dport 22 ip saddr { 10.0.0.0/8 } accept\n"
    "\t}\n"
    "}\n"
)
SSH_LISTENING = "LISTEN 0 128 0.0.0.0:22 0.0.0.0:*\nLISTEN 0 128 [::]:22 [::]:*\n"


def make_fakes(
    tmp: Path,
    *,
    check_rc: int = 0,
    apply_rc: int = 0,
    ss_out: str = SSH_LISTENING,
    listing: str = GOOD_LISTING,
) -> tuple[Path, Path]:
    bindir = tmp / "bin"
    bindir.mkdir()
    calls = tmp / "calls.log"
    (tmp / "ss.out").write_text(ss_out)
    (tmp / "nft.list").write_text(listing)
    # Only shell builtins: PATH holds nothing but these fakes.
    save = (
        'while IFS= read -r line || [ -n "$line" ]; do '
        'printf \'%s\\n\' "$line"; done > "{dest}"\n'
    )
    show = (
        'while IFS= read -r line || [ -n "$line" ]; do '
        'printf \'%s\\n\' "$line"; done < "{src}"\n'
    )
    (bindir / "nft").write_text(
        f"#!{BASH}\n"
        f'echo "nft $*" >> "{calls}"\n'
        'if [ "$1" = "-c" ]; then\n'
        + save.format(dest=tmp / "check.stdin")
        + f"  exit {check_rc}\n"
        'elif [ "$1" = "-f" ]; then\n'
        + save.format(dest=tmp / "apply.stdin")
        + f"  exit {apply_rc}\n"
        'elif [ "$1" = "list" ]; then\n'
        + show.format(src=tmp / "nft.list")
        + "  exit 0\n"
        "fi\n"
        "exit 0\n"
    )
    (bindir / "ss").write_text(
        f"#!{BASH}\n"
        f'echo "ss $*" >> "{calls}"\n' + show.format(src=tmp / "ss.out")
    )
    for f in bindir.iterdir():
        f.chmod(f.stat().st_mode | stat.S_IXUSR)
    return bindir, calls


def run_script(tmp: Path, *, sources=DEFAULT_SOURCES, metrics_port="", **fake_kw):
    script = tmp / "cah-host-firewall"
    script.write_text(
        extract_script(TEMPLATE.read_text(encoding="utf-8"), sources, metrics_port)
    )
    bindir, calls = make_fakes(tmp, **fake_kw)
    env = {"PATH": str(bindir), "HOME": str(tmp)}
    proc = _run([BASH, str(script)], env=env, capture_output=True, text=True, timeout=30)
    call_lines = calls.read_text().splitlines() if calls.exists() else []
    apply_file = tmp / "apply.stdin"
    check_file = tmp / "check.stdin"
    return (
        proc,
        call_lines,
        apply_file.read_text() if apply_file.exists() else "",
        check_file.read_text() if check_file.exists() else "",
    )


# --- extraction guards -------------------------------------------------------


def test_extraction_finds_a_real_script():
    text = extract_script(TEMPLATE.read_text(encoding="utf-8"))
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    assert "policy drop" in text
    assert f'ssh_sources="{DEFAULT_SOURCES}"' in text


def test_extraction_negative_case_missing_path_is_an_error():
    with pytest.raises(AssertionError):
        extract_script(TEMPLATE.read_text(encoding="utf-8"), path="/usr/local/sbin/nope")


def test_extraction_negative_case_rejects_an_unfilled_interpolation():
    with pytest.raises(AssertionError):
        extract_file(TEMPLATE.read_text(encoding="utf-8"), SCRIPT_PATH, {})


def test_the_unit_is_a_oneshot_ordered_after_cloud_final():
    unit = extract_file(TEMPLATE.read_text(encoding="utf-8"), UNIT_PATH)
    for needle in (
        "Type=oneshot",
        "After=cloud-final.service network-online.target",
        "ExecStart=/usr/local/sbin/cah-host-firewall",
    ):
        assert needle in unit


# --- behaviour ---------------------------------------------------------------


def test_success_applies_in_order_check_apply_verify(tmp_path):
    proc, calls, applied, checked = run_script(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert calls == [
        "nft -c -f -",
        "nft -f -",
        "ss -H -ltn",
        "nft list table inet cah_host",
    ]
    # The ruleset that was checked is the one that was applied.
    assert checked == applied and applied != ""


def test_ruleset_is_idempotent_self_contained_and_drops_by_default(tmp_path):
    _proc, _calls, ruleset, _ = run_script(tmp_path)
    lines = [line.strip() for line in ruleset.splitlines()]
    first = lines.index("table inet cah_host")
    delete = lines.index("delete table inet cah_host")
    full = lines.index("table inet cah_host {")
    assert first < delete < full
    assert "type filter hook input priority 0; policy drop;" in lines
    for rule in (
        'iifname "lo" accept',
        "ct state established,related accept",
        "ct state invalid drop",
        "udp sport 67 udp dport 68 accept",
        f"tcp dport 22 ip saddr {{ {DEFAULT_SOURCES} }} accept",
    ):
        assert rule in lines
    # No flush, no other table, no output or forward chain, no extra inbound.
    assert "flush ruleset" not in ruleset
    assert "cah_metadata" not in ruleset
    assert "chain output" not in ruleset and "chain forward" not in ruleset
    assert len(re.findall(r"dport", ruleset)) == 2  # dhcp client port + ssh


def test_no_metrics_rule_without_a_metrics_port(tmp_path):
    _proc, _calls, ruleset, _ = run_script(tmp_path)
    assert len(re.findall(r"tcp dport", ruleset)) == 1


def test_metrics_port_rule_uses_the_same_private_sources(tmp_path):
    _proc, _calls, ruleset, _ = run_script(tmp_path, metrics_port="9999")
    lines = [line.strip() for line in ruleset.splitlines()]
    assert f"tcp dport 9999 ip saddr {{ {DEFAULT_SOURCES} }} accept" in lines
    assert len(re.findall(r"tcp dport", ruleset)) == 2


def test_custom_sources_replace_the_defaults(tmp_path):
    _proc, _calls, ruleset, _ = run_script(
        tmp_path, sources="10.20.0.0/16, 192.0.2.7/32"
    )
    assert "tcp dport 22 ip saddr { 10.20.0.0/16, 192.0.2.7/32 } accept" in ruleset
    assert "172.16.0.0/12" not in ruleset


def test_a_failed_check_exits_nonzero_without_applying(tmp_path):
    proc, calls, applied, _ = run_script(tmp_path, check_rc=1)
    assert proc.returncode != 0
    assert "does not parse" in proc.stderr
    assert calls == ["nft -c -f -"]
    assert applied == ""


def test_a_failed_apply_exits_nonzero_and_never_reports_success(tmp_path):
    proc, calls, _applied, _ = run_script(tmp_path, apply_rc=1)
    assert proc.returncode != 0
    assert "nft -f -" in calls
    assert "cah-host-firewall: loaded" not in proc.stdout


def test_sshd_not_listening_deletes_the_table(tmp_path):
    proc, calls, _a, _c = run_script(tmp_path, ss_out="LISTEN 0 128 0.0.0.0:2222 *\n")
    assert proc.returncode != 0
    assert calls[-1] == "nft delete table inet cah_host"
    assert "verification failed" in proc.stderr


def test_missing_ssh_rule_in_the_loaded_table_deletes_the_table(tmp_path):
    proc, calls, _a, _c = run_script(tmp_path, listing="table inet cah_host {\n}\n")
    assert proc.returncode != 0
    assert calls[-1] == "nft delete table inet cah_host"


def test_a_failing_ss_counts_as_not_listening_and_rolls_back(tmp_path):
    script = tmp_path / "s"
    script.write_text(extract_script(TEMPLATE.read_text(encoding="utf-8")))
    bindir, calls = make_fakes(tmp_path)
    (bindir / "ss").write_text(f"#!{BASH}\nexit 1\n")
    proc = _run(
        [BASH, str(script)],
        env={"PATH": str(bindir)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode != 0
    assert calls.read_text().splitlines()[-1] == "nft delete table inet cah_host"


def test_only_the_fake_nft_and_ss_are_invoked(tmp_path):
    for kw in ({}, {"check_rc": 1}, {"ss_out": ""}):
        sub = tmp_path / str(len(kw)) / (next(iter(kw), "ok"))
        sub.mkdir(parents=True)
        _proc, calls, _a, _c = run_script(sub, **kw)
        assert calls, "the script ran nothing at all"
        assert {c.split()[0] for c in calls} <= {"nft", "ss"}


# --- real nft syntax check, in a throwaway namespace, check-only ---------------


def _can_check_syntax() -> bool:
    nft, unshare = shutil.which("nft"), shutil.which("unshare")
    if not nft or not unshare:
        return False
    probe = _run(
        [unshare, "-rn", nft, "-c", "-f", "-"],
        input="table inet cah_probe\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    return probe.returncode == 0


def _nft_check(ruleset: str):
    return _run(
        [shutil.which("unshare"), "-rn", shutil.which("nft"), "-c", "-f", "-"],
        input=ruleset,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.skipif(not _can_check_syntax(), reason="unshare -rn nft -c is unavailable here")
@pytest.mark.parametrize(
    "kw",
    [
        {},
        {"metrics_port": "9999"},
        {"sources": "10.20.0.0/16, 192.0.2.7/32"},
        {"sources": "10.20.0.0/16", "metrics_port": "1024"},
    ],
    ids=["defaults", "telemetry-port", "custom-sources", "both"],
)
def test_generated_ruleset_passes_nft_syntax_check(tmp_path, kw):
    _proc, _calls, ruleset, _ = run_script(tmp_path, **kw)
    assert ruleset, "no ruleset was captured"
    check = _nft_check(ruleset)
    assert check.returncode == 0, check.stderr


@pytest.mark.skipif(not _can_check_syntax(), reason="unshare -rn nft -c is unavailable here")
def test_syntax_check_negative_cases_the_checker_really_rejects(tmp_path):
    _proc, _calls, ruleset, _ = run_script(tmp_path)
    assert _nft_check(ruleset.replace("policy drop", "policy dropp")).returncode != 0
    assert _nft_check(ruleset.replace("ip saddr {", "ip saddr {{")).returncode != 0
    # A source that is not a CIDR is refused by nft too (belt and braces next to
    # the variable validation).
    (tmp_path / "bad").mkdir()
    _p, _c, bad, _ = run_script(tmp_path / "bad", sources="not-a-cidr")
    assert _nft_check(bad).returncode != 0


# --- template wiring ---------------------------------------------------------


def test_template_gates_the_firewall_on_host_firewall():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert len(re.findall(r"%\{ if host_firewall ~\}", text)) == 2
    assert len(re.findall(r"%\{ if metadata_lock \|\| host_firewall ~\}", text)) == 1
    # nftables is listed exactly once, whichever feature asks for it.
    assert len(re.findall(r"^  - nftables$", text, flags=re.M)) == 1
    assert "--no-block" in text
