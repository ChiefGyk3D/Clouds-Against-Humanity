"""Tests for scripts/spacelift/doppler-env.sh.

The script is sourced by Spacelift hooks under busybox ash, so it runs here
under plain /bin/sh. `doppler` and `curl` are stubs, and PATH holds only
symlinks to the few tools the script uses, so the real Doppler CLI on the
developer machine can never be picked up.
"""

import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "spacelift" / "doppler-env.sh"
TOOLS = ["uname", "sed", "mkdir", "rm", "sha256sum", "tar", "cat", "env", "printf"]
SECRET = "dp_test_SECRET_VALUE_123"

DOPPLER_STUB = """#!/bin/sh
# Stub: `doppler --version` and `doppler secrets get NAME --plain ...`.
if [ "$1" = "--version" ]; then echo "v3.77.0"; exit 0; fi
if [ "$1" = "secrets" ] && [ "$2" = "get" ]; then
  [ -n "$STUB_FAIL" ] && exit 1
  eval "printf '%s' \\"\\${STUB_$3:-}\\""
  exit 0
fi
exit 2
"""

CURL_STUB = """#!/bin/sh
# Stub: writes a bogus archive to the -o target, so the checksum must fail.
while [ "$#" -gt 0 ]; do
  if [ "$1" = "-o" ]; then printf 'not a real archive' > "$2"; fi
  shift
done
exit 0
"""


def _write_exec(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture()
def sandbox(tmp_path):
    """A PATH directory with only the tools the script needs."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in TOOLS:
        found = shutil.which(tool)
        if found:
            (bin_dir / tool).symlink_to(found)
    return tmp_path, bin_dir


def run(sandbox, args, env_extra=None, with_doppler=True):
    tmp_path, bin_dir = sandbox
    if with_doppler:
        _write_exec(bin_dir / "doppler", DOPPLER_STUB)
    else:
        _write_exec(bin_dir / "curl", CURL_STUB)
    env = {
        "PATH": str(bin_dir),
        "CAH_DOPPLER_DIR": str(tmp_path / "dl"),
        "DOPPLER_TOKEN": "dp.st.test",
        "DOPPLER_PROJECT": "proj",
        "DOPPLER_CONFIG": "prd",
        "TF_VAR_spacelift_run_type": "TRACKED",
        "TF_VAR_spacelift_commit_branch": "main",
        "STUB_DIGITALOCEAN_TOKEN": SECRET,
    }
    env.update(env_extra or {})
    # Source the script, then print what a following phase would see.
    cmd = f'. "{SCRIPT}"; cah_doppler_env {args}; rc=$?; echo "rc=$rc"; echo "TOKEN=${{DIGITALOCEAN_TOKEN:-unset}}"'
    return subprocess.run(
        ["/bin/sh", "-c", cmd], env=env, capture_output=True, text=True, check=False
    )


def test_tracked_main_exports_and_masks(sandbox):
    out = run(sandbox, "DIGITALOCEAN_TOKEN").stdout
    assert "rc=0" in out
    assert f"TOKEN={SECRET}" in out
    assert f"::add-mask {SECRET}" in out
    assert "loaded DIGITALOCEAN_TOKEN" in out


def test_value_only_appears_in_mask_line_and_phase_env(sandbox):
    out = run(sandbox, "DIGITALOCEAN_TOKEN").stdout
    # The log line that announces the load must not carry the value.
    log_lines = [ln for ln in out.splitlines() if ln.startswith("doppler-env:")]
    assert log_lines and all(SECRET not in ln for ln in log_lines)


@pytest.mark.parametrize("run_type", ["PROPOSED", "TASK", "TESTING", "PARSE", ""])
def test_other_run_types_get_nothing(sandbox, run_type):
    result = run(sandbox, "DIGITALOCEAN_TOKEN", {"TF_VAR_spacelift_run_type": run_type})
    assert "rc=0" in result.stdout
    assert "TOKEN=unset" in result.stdout
    assert SECRET not in result.stdout
    assert "skipping" in result.stdout


def test_destroy_run_on_main_is_allowed(sandbox):
    result = run(sandbox, "DIGITALOCEAN_TOKEN", {"TF_VAR_spacelift_run_type": "DESTROY"})
    assert f"TOKEN={SECRET}" in result.stdout


@pytest.mark.parametrize("branch", ["feature/x", "mainline", ""])
def test_non_main_branch_gets_nothing(sandbox, branch):
    result = run(sandbox, "DIGITALOCEAN_TOKEN", {"TF_VAR_spacelift_commit_branch": branch})
    assert "rc=0" in result.stdout
    assert "TOKEN=unset" in result.stdout
    assert SECRET not in result.stdout


@pytest.mark.parametrize("missing", ["DOPPLER_TOKEN", "DOPPLER_PROJECT", "DOPPLER_CONFIG"])
def test_missing_doppler_setting_fails(sandbox, missing):
    result = run(sandbox, "DIGITALOCEAN_TOKEN", {missing: ""})
    assert "rc=1" in result.stdout
    assert f"{missing} is not set" in result.stdout
    assert "TOKEN=unset" in result.stdout


def test_no_names_fails(sandbox):
    result = run(sandbox, "")
    assert "rc=1" in result.stdout
    assert "no secret names" in result.stdout


@pytest.mark.parametrize("bad", ["1ABC", "A-B", "A;B", "=B", "A=", "A=B=C", "$(id)"])
def test_invalid_name_fails_before_anything_runs(sandbox, bad):
    result = run(sandbox, f"'{bad}'")
    assert "rc=1" in result.stdout
    assert "invalid secret name" in result.stdout
    assert "TOKEN=unset" in result.stdout


def test_doppler_failure_fails_closed(sandbox):
    result = run(sandbox, "DIGITALOCEAN_TOKEN", {"STUB_FAIL": "1"})
    assert "rc=1" in result.stdout
    assert "could not read DIGITALOCEAN_TOKEN" in result.stdout
    assert "TOKEN=unset" in result.stdout


def test_empty_secret_fails_closed(sandbox):
    result = run(sandbox, "DIGITALOCEAN_TOKEN", {"STUB_DIGITALOCEAN_TOKEN": ""})
    assert "rc=1" in result.stdout
    assert "is empty in Doppler" in result.stdout


def test_multiple_names_all_loaded(sandbox):
    result = run(
        sandbox,
        "DIGITALOCEAN_TOKEN TWINGATE_API_TOKEN",
        {"STUB_TWINGATE_API_TOKEN": "tw_secret_456"},
    )
    assert "rc=0" in result.stdout
    assert "::add-mask tw_secret_456" in result.stdout


def test_var_equals_name_maps_doppler_name_to_env_var(sandbox):
    result = run(
        sandbox,
        "TF_VAR_admin_user_ids=ADMIN_USER_IDS",
        {"STUB_ADMIN_USER_IDS": '["abc"]'},
    )
    out = result.stdout
    assert "rc=0" in out
    assert "loaded ADMIN_USER_IDS as TF_VAR_admin_user_ids" in out
    assert '::add-mask ["abc"]' in out


def test_mapped_var_is_what_the_phase_sees(sandbox):
    _, bin_dir = sandbox
    _write_exec(bin_dir / "doppler", DOPPLER_STUB)
    env = {
        "PATH": str(bin_dir),
        "DOPPLER_TOKEN": "t",
        "DOPPLER_PROJECT": "p",
        "DOPPLER_CONFIG": "prd",
        "TF_VAR_spacelift_run_type": "TRACKED",
        "TF_VAR_spacelift_commit_branch": "main",
        "STUB_ADMIN_USER_IDS": '["abc"]',
    }
    cmd = f'. "{SCRIPT}"; cah_doppler_env TF_VAR_admin_user_ids=ADMIN_USER_IDS; env'
    result = subprocess.run(
        ["/bin/sh", "-c", cmd], env=env, capture_output=True, text=True, check=False
    )
    out = result.stdout
    assert 'TF_VAR_admin_user_ids=["abc"]' in out
    assert "\nADMIN_USER_IDS=" not in out


def test_bad_checksum_refuses_to_run_downloaded_cli(sandbox):
    result = run(sandbox, "DIGITALOCEAN_TOKEN", with_doppler=False)
    assert "rc=1" in result.stdout
    assert "checksum mismatch" in result.stdout
    assert "TOKEN=unset" in result.stdout
    tmp_path, _ = sandbox
    assert not any((tmp_path / "dl").glob("*.tar.gz"))


def test_script_has_no_trace_or_unsafe_echo():
    text = SCRIPT.read_text()
    assert "set -x" not in text
    assert not re.search(r"\|\s*(ba|da|a)?sh\b", text), "never pipe a download into a shell"


CONFIG = Path(__file__).resolve().parent.parent / ".spacelift" / "config.yml"


def _config_calls():
    """Map stack -> hook -> the cah_doppler_env argument line, without a YAML parser."""
    calls, stack, hook = {}, None, None
    for line in CONFIG.read_text().splitlines():
        if re.match(r"^  [a-z0-9-]+:\s*$", line):
            stack = line.strip().rstrip(":")
            calls[stack] = {}
        elif re.match(r"^    (before|after)_[a-z]+:\s*$", line):
            hook = line.strip().rstrip(":")
        elif "cah_doppler_env" in line and stack and hook:
            calls[stack][hook] = line.split("cah_doppler_env", 1)[1].split()
    return calls


def test_config_loads_same_names_at_init_and_apply():
    calls = _config_calls()
    assert calls, "no stacks found in .spacelift/config.yml"
    for stack, hooks in calls.items():
        assert set(hooks) == {"before_init", "before_apply"}, stack
        assert hooks["before_init"] == hooks["before_apply"], stack


def test_config_names_are_valid_and_carry_no_values():
    for stack, hooks in _config_calls().items():
        for names in hooks.values():
            assert names, stack
            for arg in names:
                var, _, src = arg.partition("=")
                for name in (var, src or var):
                    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name), (stack, arg)
