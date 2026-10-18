"""Review-round hardening of the log-shipping first boot (stage 2 step 7).

Each test pins one finding from the review of PR 151:
- the agent must never start before it is enrolled (policy-rc.d and a mask that
  are lifted only on the success path);
- a stale token or password file (SIGKILL, power loss) is swept at the start of
  the first-boot script and at every boot, and the agent unit removes a stale
  password file before it starts;
- the downloaded Wazuh key file must hold exactly one key whose primary
  fingerprint is the pinned one (hostile-bundle tests with a fake gpg);
- a failed `augenrules --load` fails closed like a failed enrollment.

Same harness as test_log_shipping_script.py: the scripts come out of the template
and run in a temporary directory with fake binaries.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml
from test_host_firewall_script import TEMPLATE, extract_file
from test_log_shipping_script import (
    BASH,
    OTHER_SECRET,
    Box,
    assert_closed,
)

GUARD_PATH = "/usr/local/sbin/cah-agent-guard"
KEYCHECK_PATH = "/usr/local/sbin/cah-wazuh-key-check"
SWEEP_UNIT_PATH = "/etc/systemd/system/cah-log-shipping-sweep.service"
DROPIN_PATH = "/etc/systemd/system/wazuh-agent.service.d/10-cah-no-stale-password.conf"


def render(flags: set[str]) -> str:
    """The template with the `%{ if flag ~}` lines at column 0 evaluated.

    Only the directive shapes this template uses are understood (a flag, or
    `a || b`); `${name}` becomes a placeholder and `$$` becomes `$`. Anything
    else raises, so the renderer cannot quietly skip a construct.
    """
    out: list[str] = []
    stack: list[bool] = []
    for line in TEMPLATE.read_text(encoding="utf-8").splitlines():
        # One line carries the telemetry lines and the next directive together.
        line = re.sub(r"^\$\{telemetry_conf\}(%\{ if .* ~\})$", r"\1", line)
        m = re.fullmatch(r"%\{ if ([a-z_ |]+) ~\}", line)
        if m:
            stack.append(any(f.strip() in flags for f in m.group(1).split("||")))
            continue
        if line == "%{ endif ~}":
            stack.pop()
            continue
        assert not line.startswith("%{"), f"unsupported directive: {line}"
        if all(stack):
            out.append(line)
    assert not stack
    text = "\n".join(out).replace("$$", "\0")
    text = re.sub(r"\$\{[A-Za-z_]+\}", "X", text)
    assert "${" not in text
    return text.replace("\0", "$")


def runcmd_entries(flags: set[str] | None = None) -> list[str]:
    """Each parsed runcmd entry as one string (a list entry is joined)."""
    on = flags if flags is not None else {"log_shipping", "metadata_lock", "host_firewall", "node_exporter"}
    doc = yaml.safe_load(render(on))
    return [" ".join(e) if isinstance(e, list) else str(e) for e in doc["runcmd"]]


# --- finding 1: denied and masked until enrolled ------------------------------


def test_the_agent_is_denied_and_masked_before_the_package_is_installed():
    entries = runcmd_entries()
    install = next(i for i, e in enumerate(entries) if 'apt-get install -yq "$AGENT_PACKAGE"' in e)
    guard = entries[install].index("cah-agent-guard deny")
    assert guard < entries[install].index('apt-get install -yq "$AGENT_PACKAGE"')
    # A failed guard stops the install rather than carrying on.
    line = next(x for x in entries[install].splitlines() if "cah-agent-guard deny" in x)
    assert "||" in line and "exit 1" in line


def test_the_guard_denies_only_the_agent_and_masks_it(tmp_path):
    box = Box(tmp_path)
    assert "cah-wazuh-deny" in box.policy.read_text()
    assert subprocess.run([BASH, str(box.policy), "wazuh-agent", "start"], check=False).returncode == 101
    assert subprocess.run([BASH, str(box.policy), "auditd", "start"], check=False).returncode == 0


def test_the_guard_delegates_other_requests_to_a_preserved_original_policy(tmp_path):
    original = "#!/bin/sh\nexit 7\n"
    box = Box(tmp_path, orig_policy=original)
    assert box.policy_orig.read_text() == original
    assert subprocess.run([BASH, str(box.policy), "auditd", "start"], check=False).returncode == 7
    assert subprocess.run([BASH, str(box.policy), "wazuh-agent", "start"], check=False).returncode == 101


def test_success_restores_the_original_policy_byte_for_byte(tmp_path):
    original = "#!/bin/sh\nexit 7\n"
    box = Box(tmp_path, orig_policy=original)
    assert box.run().returncode == 0
    assert box.policy.read_text() == original
    assert not box.policy_orig.exists()


def test_success_without_an_original_leaves_no_policy_file(tmp_path):
    box = Box(tmp_path)
    assert box.run().returncode == 0
    assert not box.policy.exists() and not box.policy_orig.exists()


def test_deny_twice_is_idempotent_and_keeps_the_original(tmp_path):
    original = "#!/bin/sh\nexit 7\n"
    box = Box(tmp_path, orig_policy=original)
    assert box.run_guard("deny").returncode == 0
    assert box.policy_orig.read_text() == original
    assert "cah-wazuh-deny" in box.policy.read_text()


def test_deny_refuses_to_clobber_a_saved_original(tmp_path):
    box = Box(tmp_path)
    box.policy.write_text("#!/bin/sh\nexit 9\n")  # a different, unmanaged policy appears
    box.policy_orig.write_text("#!/bin/sh\nexit 7\n")
    proc = box.run_guard("deny")
    assert proc.returncode != 0 and "refusing" in proc.stderr
    assert box.policy_orig.read_text() == "#!/bin/sh\nexit 7\n"


def test_guard_rejects_an_unknown_action(tmp_path):
    assert Box(tmp_path).run_guard("bogus").returncode != 0


def test_success_unmasks_only_after_enrollment(tmp_path):
    box = Box(tmp_path)
    assert box.run().returncode == 0
    log = box.log()
    assert (
        log.index("agent-auth")
        < log.index("systemctl unmask wazuh-agent")
        < log.index("systemctl enable --now wazuh-agent")
    )
    assert "systemctl mask" not in log


def test_every_failure_leaves_the_policy_in_place_and_the_agent_masked(tmp_path):
    box = Box(tmp_path)
    box.agent_auth_rc = 1
    proc = box.run()
    assert proc.returncode != 0
    assert "cah-wazuh-deny" in box.policy.read_text()
    assert "systemctl unmask" not in box.log()
    assert "systemctl mask wazuh-agent" in box.log()


def test_a_failed_unmask_keeps_the_policy_and_never_enables(tmp_path):
    box = Box(tmp_path)
    box.unmask_rc = 1
    proc = box.run()
    assert_closed(box, proc, "could not lift the guards")
    assert "enable" not in box.log()


def test_a_failed_start_puts_both_guards_back(tmp_path):
    original = "#!/bin/sh\nexit 7\n"
    box = Box(tmp_path, orig_policy=original)
    box.systemctl_rc = 1
    proc = box.run()
    assert proc.returncode != 0
    assert "did not start" in proc.stderr
    log = box.log().splitlines()
    assert log.index("systemctl enable --now wazuh-agent") < len(log) - 1
    assert log[-1] == "systemctl mask wazuh-agent"
    # The deny policy is back, delegating to the restored original.
    assert "cah-wazuh-deny" in box.policy.read_text()
    assert subprocess.run([BASH, str(box.policy), "wazuh-agent", "start"], check=False).returncode == 101
    assert subprocess.run([BASH, str(box.policy), "auditd", "start"], check=False).returncode == 7
    assert box.policy_orig.read_text() == original


# --- finding 2: sweeps ---------------------------------------------------------


def test_a_stale_password_file_is_swept_before_the_network_is_touched(tmp_path):
    box = Box(tmp_path)
    box.pass_file.write_text("stale-from-a-killed-run")
    assert box.run().returncode == 0
    assert (tmp_path / "pass.at.curl").read_text().strip() == "absent"


def test_stale_pulled_config_is_swept_at_the_start(tmp_path):
    box = Box(tmp_path)
    stale = box.run_dir / "cah-log-shipping"
    stale.mkdir()
    (stale / "stale").write_text(json.dumps({"x": OTHER_SECRET}))
    assert box.run().returncode == 0
    assert (tmp_path / "work.at.curl").read_text().strip() == "absent"


def test_boot_sweep_unit_and_agent_dropin_remove_the_files():
    template = TEMPLATE.read_text(encoding="utf-8")
    unit = extract_file(template, SWEEP_UNIT_PATH)
    assert "Before=wazuh-agent.service" in unit
    assert "/etc/cah/hostboot.token" in unit and "/var/ossec/etc/authd.pass" in unit
    assert "rm -f" in unit and "Type=oneshot" in unit
    dropin = extract_file(template, DROPIN_PATH)
    assert "ExecStartPre=-" in dropin and "/var/ossec/etc/authd.pass" in dropin


def test_the_sweep_unit_is_enabled_for_the_next_boot_only():
    # --now would delete the token before the first-boot script has used it.
    entries = runcmd_entries()
    sweep = [i for i, e in enumerate(entries) if "cah-log-shipping-sweep" in e]
    assert len(sweep) == 1
    assert "--now" not in entries[sweep[0]] and "start" not in entries[sweep[0]]
    first = [i for i, e in enumerate(entries) if "cah-log-shipping-firstboot" in e]
    assert len(first) == 1 and sweep[0] < first[0]


# --- finding 4: augenrules fails closed ----------------------------------------


def test_a_failed_augenrules_fails_closed(tmp_path):
    box = Box(tmp_path)
    box.augenrules_rc = 1
    proc = box.run()
    assert_closed(box, proc, "augenrules --load failed")
    assert "curl" not in box.log()
    assert "agent-auth" not in box.log()


def test_augenrules_runs_on_success(tmp_path):
    box = Box(tmp_path)
    assert box.run().returncode == 0
    assert "augenrules --load" in box.log()


def test_augenrules_is_not_a_loose_runcmd_that_only_warns():
    # Parsed runcmd entries, not a text search (a comment would match the text).
    assert not [e for e in runcmd_entries() if "augenrules" in e]
    first = next(e for e in runcmd_entries() if "cah-log-shipping-firstboot" in e)
    assert first.strip() == "/usr/local/sbin/cah-log-shipping-firstboot"


def test_the_runcmd_renderer_is_not_vacuous():
    entries = runcmd_entries()
    assert len(entries) > 8
    assert any("twingate-connector" in e for e in entries)
    # With the feature off the log-shipping entries are not rendered at all.
    assert not [e for e in runcmd_entries(set()) if "wazuh" in e]


# --- finding 3: hostile key bundles --------------------------------------------

# Built in pieces so no committed file holds a 40-digit hex string.
PIN = "".join(["0123456789", "ABCDEF0123", "456789ABCD", "EF01234567"])  # noqa: FLY002 (joined on purpose: a 40-hex literal trips gitleaks)
ATTACKER = "".join(["FEDCBA9876", "543210FEDC", "BA98765432", "10FEDCBA98"])  # noqa: FLY002
PUB = "pub:-:4096:1:AAAAAAAAAAAAAAAA:1:::-:::scESC::::::23::0:"
SUB = "sub:-:4096:1:BBBBBBBBBBBBBBBB:1::::::e::::::23:"
UID = "uid:-::::1::HASH::Example Signing Key::::::::::0:"


def colons(*records: str) -> str:
    return "".join(r + "\n" for r in records)


def fpr(value: str) -> str:
    return f"fpr:::::::::{value}:"


GOOD_KEY = colons(PUB, fpr(PIN), UID, SUB, fpr(ATTACKER))  # a bound subkey has its own fpr
BAD = {
    "two-pubs-pinned-first": colons(PUB, fpr(PIN), PUB, fpr(ATTACKER)),
    "two-pubs-pinned-second": colons(PUB, fpr(ATTACKER), PUB, fpr(PIN)),
    "matching-fpr-plus-a-second-fpr": colons(PUB, fpr(PIN), fpr(ATTACKER)),
    "two-pubs-second-without-fpr": colons(PUB, fpr(PIN), PUB),
    "wrong-primary": colons(PUB, fpr(ATTACKER)),
    "no-pub": colons(fpr(PIN)),
    "empty": "",
    "secret-key": colons("sec:-:4096:1:AAAAAAAAAAAAAAAA:1::::::scESC::::::23::0:", fpr(PIN)),
}


def keycheck_script(tmp: Path) -> Path:
    script = tmp / "keycheck.sh"
    script.write_text(extract_file(TEMPLATE.read_text(encoding="utf-8"), KEYCHECK_PATH))
    return script


def run_keycheck(tmp: Path, gpg_out: str, gpg_rc: int = 0, pin: str = PIN):
    bindir = tmp / "kbin"
    bindir.mkdir()
    for name in ("cat", "grep"):
        (bindir / name).symlink_to(shutil.which(name))
    (tmp / "gpg.out").write_text(gpg_out)
    (bindir / "gpg").write_text(f'#!{BASH}\ncat "{tmp}/gpg.out"\nexit {gpg_rc}\n')
    (bindir / "gpg").chmod(0o755)
    keyfile = tmp / "key.asc"
    keyfile.write_text("not used by the fake")
    return subprocess.run(
        [BASH, str(keycheck_script(tmp)), str(keyfile), pin],
        env={"PATH": str(bindir)},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_key_check_accepts_exactly_the_pinned_key_with_a_bound_subkey(tmp_path):
    proc = run_keycheck(tmp_path, GOOD_KEY)
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("name", sorted(BAD))
def test_key_check_refuses_a_hostile_or_malformed_bundle(tmp_path, name):
    proc = run_keycheck(tmp_path, BAD[name])
    assert proc.returncode != 0, name
    assert "refusing" in proc.stderr


def test_key_check_refuses_when_gpg_fails(tmp_path):
    assert run_keycheck(tmp_path, GOOD_KEY, gpg_rc=2).returncode != 0


def test_key_check_refuses_a_different_pin(tmp_path):
    assert run_keycheck(tmp_path, GOOD_KEY, pin=ATTACKER).returncode != 0


def test_key_check_refuses_a_missing_argument(tmp_path):
    proc = subprocess.run(
        [BASH, str(keycheck_script(tmp_path))],
        env={"PATH": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def test_the_install_block_uses_the_key_check_not_a_grep():
    text = TEMPLATE.read_text(encoding="utf-8")
    block = next(e for e in runcmd_entries() if "packages.wazuh.com" in e)
    assert re.search(r'cah-wazuh-key-check /root/wazuh\.gpg\.key "\$FPR"', block)
    assert 'grep -q "^fpr' not in block
    assert block.index("cah-wazuh-key-check") < block.index("gpg --dearmor")
    assert text.count("cah-wazuh-key-check") >= 2


# --- real gpg: the check against real key files ---------------------------------

REAL_GPG = shutil.which("gpg")


@pytest.fixture
def real_keys():
    """Two real keys (the second with a subkey), exported armored, in a short GNUPGHOME."""
    home = Path(tempfile.mkdtemp(prefix="cahgpg", dir="/tmp"))
    home.chmod(0o700)
    env = {"PATH": os.environ["PATH"], "GNUPGHOME": str(home), "HOME": str(home)}

    def gpg(*args):
        return subprocess.run(
            [REAL_GPG, "--batch", "--yes", "--pinentry-mode", "loopback", "--passphrase", "", *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        ).stdout

    def make(uid, subkey):
        gpg("--quick-generate-key", uid, "ed25519", "cert", "never")
        listing = gpg("--list-keys", "--with-colons", uid)
        fpr_line = next(x for x in listing.splitlines() if x.startswith("fpr:"))
        fpr_value = fpr_line.split(":")[9]
        if subkey:
            gpg("--quick-add-key", fpr_value, "cv25519", "encr", "never")
        return fpr_value, gpg("--armor", "--export", fpr_value)

    try:
        yield {
            "a": make("cah test key a <a@example.com>", subkey=False),
            "b": make("cah test key b <b@example.com>", subkey=True),
        }
    finally:
        subprocess.run(["gpgconf", "--homedir", str(home), "--kill", "all"], check=False, capture_output=True)
        shutil.rmtree(home, ignore_errors=True)


def real_check(tmp: Path, armored: str, pin: str):
    tmp.mkdir(exist_ok=True)
    bindir = tmp / "rbin"
    bindir.mkdir()
    (bindir / "gpg").symlink_to(REAL_GPG)
    keyfile = tmp / "bundle.asc"
    keyfile.write_text(armored)
    home = Path(tempfile.mkdtemp(prefix="cahgpg", dir="/tmp"))
    home.chmod(0o700)
    try:
        return subprocess.run(
            [BASH, str(keycheck_script(tmp)), str(keyfile), pin],
            env={"PATH": str(bindir), "GNUPGHOME": str(home), "HOME": str(home)},
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    finally:
        subprocess.run(["gpgconf", "--homedir", str(home), "--kill", "all"], check=False, capture_output=True)
        shutil.rmtree(home, ignore_errors=True)


@pytest.mark.skipif(REAL_GPG is None, reason="gpg is not installed, so the real-key tests cannot run")
class TestRealGpg:
    def test_a_single_key_with_the_right_pin_is_accepted(self, tmp_path, real_keys):
        fpr_a, armor_a = real_keys["a"]
        proc = real_check(tmp_path / "x", armor_a, fpr_a)
        assert proc.returncode == 0, proc.stderr

    def test_a_key_with_a_subkey_is_accepted(self, tmp_path, real_keys):
        fpr_b, armor_b = real_keys["b"]
        proc = real_check(tmp_path / "x", armor_b, fpr_b)
        assert proc.returncode == 0, proc.stderr

    def test_the_pinned_key_plus_another_key_is_refused_in_both_orders(self, tmp_path, real_keys):
        (fpr_a, armor_a), (fpr_b, armor_b) = real_keys["a"], real_keys["b"]
        cases = [
            (fpr_a, armor_a + armor_b),
            (fpr_a, armor_b + armor_a),
            (fpr_b, armor_a + armor_b),
            (fpr_b, armor_b + armor_a),
        ]
        for n, (pin, bundle) in enumerate(cases):
            proc = real_check(tmp_path / f"case{n}", bundle, pin)
            assert proc.returncode != 0, n
            assert "refusing" in proc.stderr, n

    def test_the_wrong_pin_is_refused(self, tmp_path, real_keys):
        _, armor_a = real_keys["a"]
        fpr_b, _ = real_keys["b"]
        assert real_check(tmp_path / "x", armor_a, fpr_b).returncode != 0

    def test_garbage_is_refused(self, tmp_path, real_keys):
        fpr_a, _ = real_keys["a"]
        assert real_check(tmp_path / "x", "not a key at all\n", fpr_a).returncode != 0


# --- the log sources go inside the existing root element ------------------------


def test_the_log_sources_land_inside_a_single_root_element(tmp_path):
    box = Box(tmp_path)
    assert box.run().returncode == 0
    root = ET.fromstring(box.conf)  # raises if there are two top-level elements
    assert root.tag == "ossec_config"
    assert root.find("client/server/address").text == "192.0.2.10"
    assert len(root.findall("localfile")) >= 4
    assert box.conf.count("<ossec_config>") == 1


def test_the_log_sources_go_into_the_last_root_when_there_are_several(tmp_path):
    box = Box(tmp_path)
    (box.ossec / "etc" / "ossec.conf").write_text(
        "<ossec_config>\n  <client><server><address>MANAGER_IP</address><port>1514</port></server></client>\n"
        "</ossec_config>\n<ossec_config>\n  <syscheck/>\n</ossec_config>\n"
    )
    assert box.run().returncode == 0
    roots = ET.fromstring("<all>" + box.conf + "</all>").findall("ossec_config")
    assert len(roots) == 2
    assert not roots[0].findall("localfile") and roots[1].findall("localfile")


def test_a_config_with_no_root_element_fails_closed(tmp_path):
    box = Box(tmp_path)
    (box.ossec / "etc" / "ossec.conf").write_text("<address>MANAGER_IP</address><port>1514</port>\n")
    proc = box.run()
    assert_closed(box, proc, "could not add the log sources")
