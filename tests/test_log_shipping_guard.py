"""Round 3 review: the agent guard and the ossec.conf edit must fail safe.

- fail() leaves the unit masked and the agent stopped even when the guard cannot
  restore the policy-rc.d denial, says so loudly and exits non-zero;
- the guard owns policy-rc.d only through a state file plus a content hash, never
  because a file mentions a marker, and refuses a symlink;
- the ossec.conf edit is atomic: a failed write leaves the original byte for byte,
  the mode is kept, and a result that is not well-formed is never installed.
Same harness as test_log_shipping_script.py (scripts out of the template, fake
binaries, a temporary directory).
"""

import os
import resource
import signal
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from test_host_firewall_script import TEMPLATE, extract_file
from test_log_shipping_script import INSERT_PATH, PYTHON3, STOCK_OSSEC, Box

UNMANAGED = "#!/bin/sh\n# a policy from another tool\nexit 9\n"
MENTIONS_MARKER = "#!/bin/sh\n# cah-wazuh-deny is only mentioned here\nexit 7\n"


# --- finding 1: fail() guarantees at least mask + stop/disable ----------------


def test_a_policy_swapped_in_after_allow_is_left_alone_and_the_unit_is_masked_loudly(tmp_path):
    box = Box(tmp_path, orig_policy="#!/bin/sh\nexit 7\n")
    box.systemctl_rc = 1  # enable --now fails
    box.swap_policy_on_enable(UNMANAGED, with_saved_original=True)
    proc = box.run()
    log = box.log().splitlines()
    assert proc.returncode != 0
    # The unit is masked directly after the failed enable, the agent stopped/disabled.
    after = log[log.index("systemctl enable --now wazuh-agent") :]
    assert "systemctl stop wazuh-agent" in after
    assert "systemctl disable wazuh-agent" in after
    assert "systemctl mask wazuh-agent" in after
    # The guard could not restore the denial, and says so loudly instead of hiding it.
    assert "CRITICAL" in proc.stderr and "refusing" in proc.stderr
    # The unmanaged policy was not clobbered.
    assert box.policy.read_text() == UNMANAGED
    assert box.policy_orig.read_text() == "saved"


def test_a_mask_that_fails_is_reported_loudly_and_still_exits_non_zero(tmp_path):
    box = Box(tmp_path)
    box.systemctl_rc = 1
    box.mask_rc = 1
    proc = box.run()
    assert proc.returncode != 0
    assert "CRITICAL: could not mask wazuh-agent" in proc.stderr
    assert "systemctl stop wazuh-agent" in box.log()


def test_the_guard_masks_even_when_it_cannot_install_the_policy(tmp_path):
    box = Box(tmp_path)
    box.policy.unlink()
    box.policy.symlink_to(tmp_path / "elsewhere")
    box.calls.unlink(missing_ok=True)
    proc = box.run_guard("deny")
    assert proc.returncode != 0
    assert "systemctl mask wazuh-agent" in box.log()


def test_the_guard_reports_a_failed_mask_and_exits_non_zero(tmp_path):
    box = Box(tmp_path)
    (tmp_path / "mask.rc").write_text("1")
    proc = box.run_guard("deny")
    assert proc.returncode != 0 and "could not mask" in proc.stderr


# --- finding 3: ownership by state + hash, not by a marker -----------------------


def test_an_unrelated_policy_that_mentions_the_marker_is_preserved_not_clobbered(tmp_path):
    box = Box(tmp_path, orig_policy=MENTIONS_MARKER)
    assert box.policy_orig.read_text() == MENTIONS_MARKER
    assert box.run().returncode == 0
    assert box.policy.read_text() == MENTIONS_MARKER
    assert not box.policy_orig.exists()


def test_allow_never_deletes_a_policy_it_does_not_own(tmp_path):
    box = Box(tmp_path)
    box.policy.write_text(MENTIONS_MARKER)  # replaced behind the guard's back
    assert box.run_guard("allow").returncode == 0
    assert box.policy.read_text() == MENTIONS_MARKER


def test_a_tampered_policy_is_no_longer_ours(tmp_path):
    box = Box(tmp_path)
    box.policy.write_text(box.policy.read_text() + "# edited\n")
    assert box.run_guard("allow").returncode == 0
    assert box.policy.exists(), "a policy whose hash differs from the state must not be deleted"


def test_the_state_file_is_written_only_by_deny(tmp_path):
    box = Box(tmp_path)
    state = box.state_dir / "agent-guard.state"
    assert state.is_file()
    assert box.run_guard("allow").returncode == 0
    assert not state.exists()


def test_no_state_file_means_nothing_is_ours(tmp_path):
    box = Box(tmp_path)
    (box.state_dir / "agent-guard.state").unlink()
    assert box.run_guard("allow").returncode == 0
    assert box.policy.exists()


# --- finding 4: no symlink, atomic install ---------------------------------------


def test_deny_refuses_a_symlinked_policy_and_does_not_write_through_it(tmp_path):
    box = Box(tmp_path)
    box.policy.unlink()
    target = tmp_path / "victim"
    target.write_text("victim content\n")
    box.policy.symlink_to(target)
    proc = box.run_guard("deny")
    assert proc.returncode != 0 and "symlink" in proc.stderr
    assert target.read_text() == "victim content\n"
    assert box.policy.is_symlink()


def test_allow_leaves_a_symlinked_policy_alone(tmp_path):
    box = Box(tmp_path)
    box.policy.unlink()
    target = tmp_path / "victim"
    target.write_text("victim content\n")
    box.policy.symlink_to(target)
    box.run_guard("allow")
    assert box.policy.is_symlink() and target.read_text() == "victim content\n"


def test_the_policy_is_installed_by_rename_and_leaves_no_temporary_file(tmp_path):
    box = Box(tmp_path)
    assert box.run_guard("deny").returncode == 0
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".cah-policy")] == []
    assert box.policy.is_file() and not box.policy.is_symlink()
    assert os.access(box.policy, os.X_OK)


def test_the_guard_script_writes_through_a_temporary_file_in_the_same_directory():
    text = extract_file(TEMPLATE.read_text(encoding="utf-8"), "/usr/local/sbin/cah-agent-guard")
    assert 'mktemp "$dir/.cah-policy' in text
    assert 'mv -T -f "$tmp" "$POLICY_RC"' in text
    assert "cat > \"$POLICY_RC\"" not in text


# --- finding 2: the ossec.conf edit is atomic -------------------------------------


def insert_script(tmp: Path) -> Path:
    script = tmp / "insert.py"
    script.write_text(extract_file(TEMPLATE.read_text(encoding="utf-8"), INSERT_PATH))
    script.chmod(0o755)
    return script


def fragment(tmp: Path, text: str = "<localfile><location>/x</location></localfile>\n") -> Path:
    f = tmp / "frag.xml"
    f.write_text(text)
    return f


def run_insert(tmp: Path, conf: Path, frag: Path, preexec=None):
    return subprocess.run(
        [PYTHON3, str(insert_script(tmp)), str(conf), str(frag)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        preexec_fn=preexec,
    )


def test_insert_puts_the_sources_inside_the_one_root_and_keeps_the_mode(tmp_path):
    conf = tmp_path / "ossec.conf"
    conf.write_text(STOCK_OSSEC)
    conf.chmod(0o640)
    proc = run_insert(tmp_path, conf, fragment(tmp_path))
    assert proc.returncode == 0, proc.stderr
    root = ET.fromstring(conf.read_text())
    assert root.tag == "ossec_config" and root.find("localfile/location").text == "/x"
    assert (conf.stat().st_mode & 0o7777) == 0o640
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".ossec")] == []


def test_a_write_failure_leaves_the_original_byte_for_byte(tmp_path):
    conf = tmp_path / "ossec.conf"
    conf.write_text(STOCK_OSSEC)
    before = conf.read_bytes()

    def limit_file_size():
        # A write past 100 bytes fails with EFBIG (like ENOSPC); ignore the signal.
        signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
        resource.setrlimit(resource.RLIMIT_FSIZE, (100, 100))

    proc = run_insert(tmp_path, conf, fragment(tmp_path, "<localfile>" + "x" * 500 + "</localfile>\n"), limit_file_size)
    assert proc.returncode != 0
    assert conf.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith(".ossec")] == []


def test_an_unwritable_directory_leaves_the_original_alone(tmp_path):
    d = tmp_path / "etc"
    d.mkdir()
    conf = d / "ossec.conf"
    conf.write_text(STOCK_OSSEC)
    d.chmod(0o555)
    try:
        if os.access(d, os.W_OK):
            pytest.skip("directory permissions are not enforced for this user")
        proc = run_insert(tmp_path, conf, fragment(tmp_path))
    finally:
        d.chmod(0o755)
    assert proc.returncode != 0 and conf.read_text() == STOCK_OSSEC


def test_a_fragment_that_breaks_the_xml_is_never_installed(tmp_path):
    conf = tmp_path / "ossec.conf"
    conf.write_text(STOCK_OSSEC)
    proc = run_insert(tmp_path, conf, fragment(tmp_path, "<localfile><location>oops</localfile>\n"))
    assert proc.returncode != 0 and "refusing" in proc.stderr
    assert conf.read_text() == STOCK_OSSEC


def test_a_fragment_that_adds_a_second_root_is_never_installed(tmp_path):
    conf = tmp_path / "ossec.conf"
    conf.write_text(STOCK_OSSEC)
    proc = run_insert(tmp_path, conf, fragment(tmp_path, "</ossec_config><ossec_config><localfile/>\n"))
    assert proc.returncode != 0 and "refusing" in proc.stderr
    assert conf.read_text() == STOCK_OSSEC


def test_no_root_element_is_refused_with_a_message(tmp_path):
    conf = tmp_path / "ossec.conf"
    conf.write_text("<address>x</address>\n")
    proc = run_insert(tmp_path, conf, fragment(tmp_path))
    assert proc.returncode != 0 and "refusing" in proc.stderr
    assert conf.read_text() == "<address>x</address>\n"


def test_the_insert_script_uses_a_temp_file_fsync_and_replace():
    text = extract_file(TEMPLATE.read_text(encoding="utf-8"), INSERT_PATH)
    assert "mkstemp" in text and "os.fsync" in text and "os.replace" in text
    assert "open(path, \"w\")" not in text
