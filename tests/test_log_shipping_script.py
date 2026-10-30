"""Hermetic tests for the log-shipping first-boot script in the connector cloud-init.

Stage 2 step 7 (design 2026-10-16, section 2.8): the Wazuh agent is enrolled by a
script that pulls its secret from Doppler with a short-lived token. The script is
extracted from modules/twingate-bootstrap/cloud-init.yaml.tftpl (the same
extraction as the host-firewall and node-exporter tests) and run in a temporary
directory with fake `curl`, `systemctl` and `agent-auth` binaries on a PATH that
holds nothing else but a few coreutils and python3. All paths the script uses are
rewritten into that directory. No network, no service and no file outside the
temporary directory is touched. Fixture secrets are built at run time and are
obviously fake.

What is proved: the success path, a failed pull, a missing secret, a failed
enrollment, a missing agent and a missing token each fail closed (the agent is
never enabled or started), the token file and the enrollment password file are
gone afterwards in every case, the token travels on stdin and never in an
argument, and no secret appears in the script's output.
"""

import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from test_host_firewall_script import TEMPLATE, extract_file

BASH = shutil.which("bash")
PYTHON3 = shutil.which("python3")
SCRIPT_PATH = "/usr/local/sbin/cah-log-shipping-firstboot"
TOKEN_PATH = "/etc/cah/hostboot.token"
LOCALFILE_PATH = "/etc/cah/wazuh-localfile.xml"
RULES_PATH = "/etc/audit/rules.d/60-cah.rules"
GUARD_PATH = "/usr/local/sbin/cah-agent-guard"
INSERT_PATH = "/usr/local/sbin/cah-ossec-insert"
KEYCHECK_PATH = "/usr/local/sbin/cah-apt-key-check"
SWEEP_UNIT_PATH = "/etc/systemd/system/cah-log-shipping-sweep.service"
DROPIN_PATH = "/etc/systemd/system/wazuh-agent.service.d/10-cah-no-stale-password.conf"

pytestmark = pytest.mark.skipif(BASH is None or PYTHON3 is None, reason="bash and python3 are required")

# Obviously fake fixture values, none of them shaped like a real credential.
TOKEN = "fixture-bootstrap-token-0001"
PASSWORD = "fixture-wazuh-enroll-password-0001"
OTHER_SECRET = "fixture-twingate-service-key-0001"

SUBS = {
    "log_shipping_manager_address": "192.0.2.10",
    "log_shipping_manager_port": "1514",
    "log_shipping_enroll_port": "1515",
    "log_shipping_agent_name": "site-tor1-connector-a",
    "log_shipping_agent_group": "site-tor1",
    "log_shipping_site": "site-tor1",
    "log_shipping_hostboot_config": "cah-tor1-hostboot",
}

# The part of the Wazuh agent's stock ossec.conf the script edits.
STOCK_OSSEC = """\
<ossec_config>
  <client>
    <server>
      <address>MANAGER_IP</address>
      <port>1514</port>
      <protocol>tcp</protocol>
    </server>
  </client>
</ossec_config>
"""

COREUTILS = ("env", "bash", "cat", "rm", "mv", "mkdir", "mktemp", "chmod", "grep", "sed", "dirname", "stat", "sha256sum")


def extract(**over: str) -> str:
    subs = dict(SUBS)
    subs.update(over)
    return extract_file(TEMPLATE.read_text(encoding="utf-8"), SCRIPT_PATH, subs)


def extract_localfile_text(**over: str) -> str:
    return extract_file(TEMPLATE.read_text(encoding="utf-8"), LOCALFILE_PATH, dict(SUBS, **over))


class Box:
    """A throwaway filesystem and PATH for one run of the script."""

    def __init__(self, tmp: Path, orig_policy: str | None = None, **over: str):
        self.tmp = tmp
        self.bin = tmp / "bin"
        self.bin.mkdir()
        self.etc = tmp / "sb-cah"
        self.etc.mkdir()
        self.ossec = tmp / "sb-ossec"
        (self.ossec / "bin").mkdir(parents=True)
        (self.ossec / "etc").mkdir()
        self.run_dir = tmp / "sb-run"
        self.run_dir.mkdir()
        self.calls = tmp / "calls.log"
        self.over = over
        for name in COREUTILS:
            src = shutil.which(name)
            if src:
                (self.bin / name).symlink_to(src)
        (self.bin / "python3").symlink_to(PYTHON3)
        (self.etc / "wazuh-localfile.xml").write_text(extract_localfile_text(), encoding="utf-8")
        self.token_file.write_text(TOKEN)
        (self.ossec / "etc" / "ossec.conf").write_text(STOCK_OSSEC)
        self.set_secrets({"WAZUH_ENROLLMENT_PASSWORD": PASSWORD, "OTHER": OTHER_SECRET})
        self.curl_rc = 0
        self.agent_auth_rc = 0
        self.systemctl_rc = 0
        self.augenrules_rc = 0
        self.unmask_rc = 0
        self.mask_rc = 0
        self.state_dir = tmp / "sb-state"
        self.ossec_insert = tmp / "sb-ossec-insert.py"
        self.policy = tmp / "sb-policy-rc.d"
        self.policy_orig = tmp / "sb-policy-rc.d.cah-orig"
        if orig_policy is not None:
            self.policy.write_text(orig_policy)
            self.policy.chmod(0o755)
        self.guard = tmp / "sb-guard.sh"
        self.guard.write_text(self.sandboxed(extract_file(TEMPLATE.read_text(encoding="utf-8"), GUARD_PATH)))
        self.guard.chmod(0o755)
        self.ossec_insert.write_text(self.sandboxed(extract_file(TEMPLATE.read_text(encoding="utf-8"), INSERT_PATH)))
        self.ossec_insert.chmod(0o755)
        self.install_agent_auth()
        self.write_fakes()
        # What the install step of runcmd does before the package is installed.
        (tmp / "systemctl.rc").write_text("0")
        (tmp / "unmask.rc").write_text("0")
        (tmp / "mask.rc").write_text("0")
        done = self.run_guard("deny")
        assert done.returncode == 0, done.stderr
        self.calls.unlink()

    def sandboxed(self, text: str) -> str:
        text = text.replace("/run/cah-log-shipping", str(self.run_dir / "cah-log-shipping"))
        text = text.replace("/etc/cah", str(self.etc))
        text = text.replace("/var/ossec", str(self.ossec))
        text = text.replace("/usr/sbin/policy-rc.d", str(self.policy))
        text = text.replace("/var/lib/cah", str(self.state_dir))
        text = text.replace(GUARD_PATH, str(self.guard))
        text = text.replace(INSERT_PATH, str(self.ossec_insert))
        for root in ("/etc/cah", "/var/ossec", "/run/cah-log-shipping", "/usr/sbin/policy-rc.d"):
            assert root not in text
        return text

    def swap_policy_on_enable(self, unmanaged: str, with_saved_original: bool) -> None:
        """When the agent is enabled, replace policy-rc.d with an unmanaged file."""
        lines = [f"rm -f '{self.policy}'", f"printf '%s' '{unmanaged}' > '{self.policy}'"]
        if with_saved_original:
            lines.append(f"printf '%s' 'saved' > '{self.policy_orig}'")
        (self.tmp / "swap.sh").write_text("\n".join(lines) + "\n")

    def run_guard(self, action: str):
        return subprocess.run(
            [BASH, str(self.guard), action],
            env={"PATH": str(self.bin), "HOME": str(self.tmp)},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    @property
    def token_file(self) -> Path:
        return self.etc / "hostboot.token"

    @property
    def pass_file(self) -> Path:
        return self.ossec / "etc" / "authd.pass"

    @property
    def conf(self) -> str:
        return (self.ossec / "etc" / "ossec.conf").read_text()

    def set_secrets(self, secrets: dict) -> None:
        (self.tmp / "secrets.json").write_text(json.dumps(secrets))

    def install_agent_auth(self) -> None:
        fake = self.ossec / "bin" / "agent-auth"
        fake.write_text(
            f"#!{BASH}\n"
            f'echo "agent-auth $*" >> "{self.calls}"\n'
            f'p="{self.pass_file}"\n'
            'if [ -e "$p" ]; then\n'
            f'  echo "present $(stat -c %a "$p") $(cat "$p")" > "{self.tmp}/enroll.seen"\n'
            "else\n"
            f'  echo "absent" > "{self.tmp}/enroll.seen"\n'
            "fi\n"
            f'exit "$(cat "{self.tmp}/agent_auth.rc")"\n'
        )
        fake.chmod(0o755)

    def write_fakes(self) -> None:
        tmp = self.tmp
        (self.bin / "curl").write_text(
            f"#!{BASH}\n"
            f'echo "curl $*" >> "{self.calls}"\n'
            f'if [ -e "{self.token_file}" ]; then echo present > "{tmp}/token.at.curl"; '
            f'else echo absent > "{tmp}/token.at.curl"; fi\n'
            f'if [ -e "{self.pass_file}" ]; then echo present > "{tmp}/pass.at.curl"; '
            f'else echo absent > "{tmp}/pass.at.curl"; fi\n'
            f'[ -e "{self.run_dir}/cah-log-shipping/stale" ] && echo present > "{tmp}/work.at.curl" || echo absent > "{tmp}/work.at.curl"\n'
            # -K - : the credential config arrives on stdin.
            f'cat > "{tmp}/curl.stdin"\n'
            'out=""\nwhile [ $# -gt 0 ]; do [ "$1" = "-o" ] && out="$2"; shift; done\n'
            f'rc="$(cat "{tmp}/curl.rc")"\n'
            '[ "$rc" = 0 ] || exit "$rc"\n'
            f'cat "{tmp}/secrets.json" > "$out"\n'
        )
        (self.bin / "systemctl").write_text(
            f"#!{BASH}\n" f'echo "systemctl $*" >> "{self.calls}"\n'
            f'if [ "$1" = enable ] && [ -e "{tmp}/swap.sh" ]; then {BASH} "{tmp}/swap.sh"; fi\n'
            'case "$1" in stop|disable) exit 0 ;; esac\n'
            f'if [ "$1" = mask ]; then exit "$(cat "{tmp}/mask.rc")"; fi\n'
            f'if [ "$1" = unmask ]; then exit "$(cat "{tmp}/unmask.rc")"; fi\n'
            f'exit "$(cat "{tmp}/systemctl.rc")"\n'
        )
        (self.bin / "augenrules").write_text(
            f"#!{BASH}\n" f'echo "augenrules $*" >> "{self.calls}"\n'
            f'exit "$(cat "{tmp}/augenrules.rc")"\n'
        )
        for name in ("curl", "systemctl", "augenrules"):
            (self.bin / name).chmod(0o755)

    def run(self):
        (self.tmp / "curl.rc").write_text(str(self.curl_rc))
        (self.tmp / "agent_auth.rc").write_text(str(self.agent_auth_rc))
        (self.tmp / "systemctl.rc").write_text(str(self.systemctl_rc))
        (self.tmp / "unmask.rc").write_text(str(self.unmask_rc))
        (self.tmp / "mask.rc").write_text(str(self.mask_rc))
        (self.tmp / "augenrules.rc").write_text(str(self.augenrules_rc))
        text = extract(**self.over)
        text = self.sandboxed(text)
        script = self.tmp / "firstboot.sh"
        script.write_text(text)
        return subprocess.run(
            [BASH, str(script)],
            env={"PATH": str(self.bin), "HOME": str(self.tmp)},
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def log(self) -> str:
        return self.calls.read_text() if self.calls.exists() else ""

    def work_files(self) -> list[Path]:
        work = self.run_dir / "cah-log-shipping"
        return [p for p in work.rglob("*") if p.is_file()] if work.exists() else []


def never_started(log: str) -> bool:
    return not re.search(r"systemctl (enable|start|restart)", log)


# --- extraction ------------------------------------------------------------


def test_extraction_finds_the_script():
    assert extract().startswith("#!/usr/bin/env bash\n")


def test_extraction_negative_case_missing_path_is_an_error():
    with pytest.raises(AssertionError):
        extract_file(TEMPLATE.read_text(encoding="utf-8"), "/usr/local/sbin/not-written")


# --- success ---------------------------------------------------------------


def test_success_enrolls_with_the_pulled_password_then_starts_the_agent(tmp_path):
    box = Box(tmp_path)
    proc = box.run()
    assert proc.returncode == 0, proc.stderr
    log = box.log()
    assert "agent-auth -m 192.0.2.10 -p 1515 -A site-tor1-connector-a -G site-tor1" in log
    # The password file existed, root-only, with exactly the pulled value, when
    # the enrollment ran.
    assert (tmp_path / "enroll.seen").read_text().strip() == f"present 600 {PASSWORD}"
    assert "systemctl enable --now wazuh-agent" in log
    # enrollment happens before the agent starts
    assert log.index("agent-auth") < log.index("systemctl enable --now wazuh-agent")


def test_success_deletes_the_token_the_password_and_the_pulled_json(tmp_path):
    box = Box(tmp_path)
    assert box.run().returncode == 0
    assert not box.token_file.exists()
    assert not box.pass_file.exists()
    assert box.work_files() == []


def test_the_token_is_gone_before_the_network_is_touched(tmp_path):
    box = Box(tmp_path)
    assert box.run().returncode == 0
    assert (tmp_path / "token.at.curl").read_text().strip() == "absent"


def test_the_token_travels_on_stdin_never_in_an_argument(tmp_path):
    box = Box(tmp_path)
    assert box.run().returncode == 0
    assert TOKEN not in box.log()
    stdin = (tmp_path / "curl.stdin").read_text()
    assert TOKEN in stdin
    assert "https://api.doppler.com/" in box.log()
    assert "--proto =https" in box.log() and "--tlsv1.2" in box.log()


def test_no_secret_reaches_stdout_or_stderr(tmp_path):
    box = Box(tmp_path)
    proc = box.run()
    for secret in (TOKEN, PASSWORD, OTHER_SECRET):
        assert secret not in proc.stdout
        assert secret not in proc.stderr


def test_only_the_wazuh_secret_is_kept_not_the_rest_of_the_config(tmp_path):
    box = Box(tmp_path)
    assert box.run().returncode == 0
    for path in tmp_path.rglob("*"):
        if path.is_file() and path.name not in ("secrets.json", "firstboot.sh"):
            assert OTHER_SECRET not in path.read_text(errors="ignore"), path


def test_the_manager_address_and_port_are_written_into_the_agent_config(tmp_path):
    box = Box(tmp_path, log_shipping_manager_port="1600")
    assert box.run().returncode == 0
    conf = box.conf
    assert "<address>192.0.2.10</address>" in conf
    assert "<port>1600</port>" in conf
    assert "MANAGER_IP" not in conf


def test_the_localfile_block_is_appended_once(tmp_path):
    box = Box(tmp_path)
    assert box.run().returncode == 0
    assert box.conf.count("twingate-connector") == 1
    # A second first-boot run (token supplied again) does not append it again.
    box.token_file.write_text(TOKEN)
    assert box.run().returncode == 0
    assert box.conf.count("twingate-connector") == 1


def test_an_empty_agent_group_leaves_out_the_group_flag(tmp_path):
    box = Box(tmp_path, log_shipping_agent_group="")
    assert box.run().returncode == 0
    call = next(line for line in box.log().splitlines() if line.startswith("agent-auth"))
    assert call == "agent-auth -m 192.0.2.10 -p 1515 -A site-tor1-connector-a"


# --- fail closed -----------------------------------------------------------


def assert_closed(box: Box, proc, reason: str) -> None:
    assert proc.returncode != 0
    assert never_started(box.log()), box.log()
    # The agent stays masked and denied by policy-rc.d.
    assert box.policy.exists() and "cah-wazuh-deny" in box.policy.read_text()
    assert "systemctl mask wazuh-agent" in box.log()
    assert not box.token_file.exists()
    assert not box.pass_file.exists()
    assert box.work_files() == []
    assert reason in proc.stderr
    for secret in (TOKEN, PASSWORD, OTHER_SECRET):
        assert secret not in proc.stdout and secret not in proc.stderr
    assert "failing closed, the Wazuh agent is not started" in proc.stderr


def test_a_failed_pull_does_not_start_the_agent_and_says_why(tmp_path):
    box = Box(tmp_path)
    box.curl_rc = 22
    proc = box.run()
    assert_closed(box, proc, "pull from Doppler failed")
    assert "agent-auth" not in box.log()


def test_a_pull_without_the_wazuh_secret_fails_closed(tmp_path):
    box = Box(tmp_path)
    box.set_secrets({"OTHER": OTHER_SECRET})
    proc = box.run()
    assert_closed(box, proc, "WAZUH_ENROLLMENT_PASSWORD")
    assert "agent-auth" not in box.log()


@pytest.mark.parametrize("value", ["", "two\nlines"], ids=["empty", "newline"])
def test_an_unusable_secret_value_fails_closed(tmp_path, value):
    box = Box(tmp_path)
    box.set_secrets({"WAZUH_ENROLLMENT_PASSWORD": value})
    proc = box.run()
    assert_closed(box, proc, "WAZUH_ENROLLMENT_PASSWORD")
    assert "agent-auth" not in box.log()


def test_a_failed_enrollment_removes_the_password_and_does_not_start_the_agent(tmp_path):
    box = Box(tmp_path)
    box.agent_auth_rc = 1
    proc = box.run()
    # The enrollment did run, with the password present, and it was removed anyway.
    assert (tmp_path / "enroll.seen").read_text().strip() == f"present 600 {PASSWORD}"
    assert_closed(box, proc, "enrollment failed")


def test_a_missing_token_file_fails_closed(tmp_path):
    box = Box(tmp_path)
    box.token_file.unlink()
    proc = box.run()
    assert_closed(box, proc, "no bootstrap token")
    assert "curl" not in box.log()


def test_an_empty_token_file_fails_closed(tmp_path):
    box = Box(tmp_path)
    box.token_file.write_text("")
    proc = box.run()
    assert_closed(box, proc, "bootstrap token")
    assert "curl" not in box.log()


def test_a_missing_agent_fails_closed_and_still_deletes_the_token(tmp_path):
    box = Box(tmp_path)
    (box.ossec / "bin" / "agent-auth").unlink()
    proc = box.run()
    assert_closed(box, proc, "not installed")
    assert "curl" not in box.log()


def test_a_failed_start_is_reported_not_swallowed(tmp_path):
    box = Box(tmp_path)
    box.systemctl_rc = 1
    proc = box.run()
    assert proc.returncode != 0
    assert "did not start" in proc.stderr
    assert not box.token_file.exists() and not box.pass_file.exists()


# --- the script text -------------------------------------------------------


def test_the_script_has_no_literal_fallback_and_writes_only_the_pulled_value():
    text = extract()
    assert "set -euo pipefail" in text
    assert "trap cleanup EXIT" in text
    # The only thing written to the password file is the pulled variable.
    assert len(re.findall(r'>\s*"\$PASS_FILE"', text)) == 1
    assert "printf '%s' \"$password\" > \"$PASS_FILE\"" in text
    # No password flag on a command line (it would show in ps), no tracing.
    assert not re.search(r"\s-P\s", text)
    assert "set -x" not in text and "bash -x" not in text


def test_the_bootstrap_token_variable_is_rendered_only_into_its_own_file():
    template = TEMPLATE.read_text(encoding="utf-8")
    hits = [m.start() for m in re.finditer(r"\$\{log_shipping_bootstrap_token\}", template)]
    assert len(hits) == 1
    body = extract_file(template, TOKEN_PATH, {"log_shipping_bootstrap_token": TOKEN})
    assert body == TOKEN + "\n"
    paths = re.findall(r"- path: (\S+)", template[: hits[0]])
    assert paths[-1] == TOKEN_PATH


def test_the_token_file_is_root_only():
    lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    i = lines.index(f"  - path: {TOKEN_PATH}")
    assert lines[i + 1].strip() == 'permissions: "0600"'
    assert lines[i + 2].strip() == "owner: root:root"


# --- the other fragments ---------------------------------------------------


def test_localfile_block_is_well_formed_and_collects_the_named_sources():
    text = extract_localfile_text()
    root = ET.fromstring(f"<root>{text}</root>")
    localfiles = root.findall("localfile")
    # Only <localfile> blocks: no second <ossec_config> wrapper in the fragment.
    assert root.find("ossec_config") is None
    assert localfiles, "no <localfile> entries"
    journald = [lf for lf in localfiles if lf.findtext("log_format") == "journald"]
    filters = " ".join((f.text or "") for lf in journald for f in lf.findall("filter"))
    for needle in ("twingate-connector", "ssh", "sudo"):
        assert needle in filters, needle
    files = [
        lf.findtext("location") for lf in localfiles if lf.findtext("log_format") != "journald"
    ]
    assert "/var/log/auth.log" in files
    assert "cah-log-shipping-localfiles" in text


def test_localfile_fragment_sets_the_site_label_the_wazuh_dashboard_filters_on():
    # The dashboard filters on agent.labels.site; Wazuh writes that field from a
    # <labels><label key="site"> block in the agent's ossec.conf.
    for site in ("site-tor1", "site-tor2"):
        root = ET.fromstring(f"<root>{extract_localfile_text(log_shipping_site=site)}</root>")
        labels = root.findall("labels/label")
        assert [(lb.get("key"), lb.text) for lb in labels] == [("site", site)]


def test_the_site_label_is_inserted_inside_the_single_root_element(tmp_path):
    box = Box(tmp_path)
    assert box.run().returncode == 0
    root = ET.fromstring(box.conf)
    assert [(lb.get("key"), lb.text) for lb in root.findall("labels/label")] == [("site", "site-tor1")]
    assert box.conf.count("<ossec_config>") == 1


def test_audit_rules_cover_identity_sudo_and_twingate_and_never_execve():
    rules = extract_file(TEMPLATE.read_text(encoding="utf-8"), RULES_PATH)
    # The deprecated -w watch form is gone (#235); each path is an -a always,exit rule.
    assert not re.search(r"(?m)^\s*-w\s", rules)
    lines = [ln for ln in rules.splitlines() if ln.strip()]
    pat = re.compile(r"^-a always,exit -F arch=b64 -F (path|dir)=(\S+) -F perm=(\S+) -F key=(\S+)$")
    parsed = [pat.match(ln) for ln in lines]
    assert lines and all(parsed), f"every rule must be an exact watch-equivalent -a rule: {lines}"
    watched = {m.group(2): (m.group(1), m.group(3), m.group(4)) for m in parsed}
    for f in ("/etc/passwd", "/etc/group", "/etc/shadow", "/etc/gshadow"):
        assert watched[f] == ("path", "wa", "cah_identity")
    assert watched["/etc/sudoers"] == ("path", "wa", "cah_sudo")
    # A directory keeps the recursive meaning of the old -w on a directory.
    assert watched["/etc/sudoers.d/"] == ("dir", "wa", "cah_sudo")
    assert watched["/etc/twingate/"] == ("dir", "wa", "cah_twingate")
    assert len(watched) == 7
    # File rules only: no syscall filter (-S) and no execve, whatever the spelling.
    assert "execve" not in rules
    assert not re.search(r"(?m)\s-S\s", rules)


def test_audit_rule_check_bites_on_the_old_watch_form():
    old = "-w /etc/passwd -p wa -k cah_identity\n"
    assert re.search(r"(?m)^\s*-w\s", old)

def test_template_gates_every_log_shipping_piece_on_the_flag():
    text = TEMPLATE.read_text(encoding="utf-8")
    needles = (
        "- auditd",
        SCRIPT_PATH,
        TOKEN_PATH,
        LOCALFILE_PATH,
        RULES_PATH,
        "packages.wazuh.com",
        "log_shipping_key_fingerprint",
        "augenrules",
        GUARD_PATH,
        INSERT_PATH,
        "/var/lib/cah/agent-guard.state",
        "/etc/systemd/system/cah-log-shipping-sweep.service",
        "/etc/systemd/system/wazuh-agent.service.d/10-cah-no-stale-password.conf",
        "systemctl mask wazuh-agent",
    )
    for needle in needles:
        found = list(re.finditer(re.escape(needle), text))
        assert found, f"{needle} is not in the template"
        for m in found:
            before = text[: m.start()]
            assert before.rfind("%{ if log_shipping ~}") > before.rfind("%{ endif ~}"), (
                f"{needle} is outside a log_shipping conditional"
            )


def test_the_apt_key_is_checked_against_the_pinned_fingerprint_before_it_is_trusted():
    text = TEMPLATE.read_text(encoding="utf-8")
    start = text.index("packages.wazuh.com/key")
    block = text[start - 900 : start + 1400]
    check = block.index('/usr/local/sbin/cah-apt-key-check /root/wazuh.gpg.key "$FPR"')
    dearmor = block.index("gpg --dearmor")
    sources = block.index("sources.list.d/wazuh.list")
    assert check < dearmor < sources
    assert "FPR=${log_shipping_key_fingerprint}" in block
    # The fingerprint is an input: the only 40-hex literal in the template is
    # Twingate's, which was there before this feature.
    assert len(re.findall(r"\b[0-9A-Fa-f]{40}\b", text)) == 1


def test_the_agent_install_runs_after_the_connector_and_the_script_after_the_agent():
    text = TEMPLATE.read_text(encoding="utf-8")
    connector = text.index("&& apt-get install -yq twingate-connector \\\n")
    wazuh = text.index('apt-get install -yq "$AGENT_PACKAGE"')
    firstboot = text.index("[/usr/local/sbin/cah-log-shipping-firstboot]")
    status = text.index("cah-connector-install.log")
    assert connector < wazuh < firstboot < status
