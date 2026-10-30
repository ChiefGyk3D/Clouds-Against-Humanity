"""The one placeholder rule for required secrets, and everywhere it is used.

scripts/secret_rule.py is the single definition. The shell scripts call it, the
Spacelift hook script carries a case-statement copy that these tests pin to it,
and the OpenTofu validations carry its RE2 pattern, pinned here by text.
"""

import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "secret_rule.py"
DOPPLER_ENV = ROOT / "scripts" / "spacelift" / "doppler-env.sh"
DEMO = ROOT / "scripts" / "demo_monitoring.sh"
WP_LAB = ROOT / "labs" / "wordpress-at-scale"

spec = importlib.util.spec_from_file_location("secret_rule", SCRIPT)
sr = importlib.util.module_from_spec(spec)
sys.modules["secret_rule"] = sr
spec.loader.exec_module(sr)

# Real-looking values are assembled at import time so no token-shaped literal sits
# in the source for a secret scanner to flag. The pieces are short on purpose.
REAL_SECRET = "k3Jf9Qw2" + "Zr8LmN4p" + "Xs7Tv1Ye"
HEX_SECRET = "3f9a1c07" + "be52d648" + "1a0c7e93" + "d5b2f814"
DOPPLER_TOKEN = ".".join(["dp", "st", "cah-ctx", "Zm9vYmFy" + "YmF6cXV4"])
DOPPLER_SITE_TOKEN = ".".join(["dp", "st", "cah-site-hostboot", "Zm9vYmFy" + "YmF6cXV4"])

PLACEHOLDERS = [
    "",
    "   ",
    "your_token",
    "YOUR_TOKEN_HERE",
    "Your-Password",
    "changeme",
    "ChangeMe123",
    "change-me-please",
    "replace-with-your-token",
    "REPLACE_WITH_VALUE",
    "<token>",
    "<paste the token here>",
    "example",
    "my-example-secret-value",
    "placeholder",
    "A-PLACEHOLDER-value",
    "xxx",
    "xxxxxxxxxxxxxxxx",
    "dp.st.your-config.abcdefgh",
    "todo",
    "admin",
    "Password",
    "secret",
    "test",
]
REAL_LOOKING = [
    REAL_SECRET,
    HEX_SECRET,
    DOPPLER_SITE_TOKEN,
    "fixture-bootstrap-token-0001",
    "correct-horse-battery-staple-9",
]


@pytest.mark.parametrize("value", PLACEHOLDERS)
def test_placeholders_and_empty_are_rejected(value):
    assert sr.is_placeholder(value)
    with pytest.raises(sr.SecretError):
        sr.require_secret("SOME_TOKEN", value)


def test_unset_is_rejected():
    assert sr.is_placeholder(None)
    with pytest.raises(sr.SecretError):
        sr.require_secret("SOME_TOKEN", None)


@pytest.mark.parametrize("value", REAL_LOOKING)
def test_real_looking_values_are_accepted(value):
    assert not sr.is_placeholder(value)
    assert sr.require_secret("SOME_TOKEN", value) == value


def message_for(value):
    with pytest.raises(sr.SecretError) as err:
        sr.require_secret("SOME_TOKEN", value)
    return str(err.value)


@pytest.mark.parametrize("value", [v for v in PLACEHOLDERS if v.strip()])
def test_the_value_never_appears_in_the_error(value):
    # The message is the same whatever the value is, so it cannot carry it.
    assert "SOME_TOKEN" in message_for(value)
    assert message_for(value) == message_for("")


def run_cli(name, value):
    env = {k: v for k, v in os.environ.items() if k != name}
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), name],
        input=value, env=env, capture_output=True, text=True, check=False,
    )


@pytest.mark.parametrize("value", ["", "changeme-now-please", "your_password_here"])
def test_cli_rejects_and_names_the_variable_without_the_value(value):
    out = run_cli("GRAFANA_ADMIN_PASSWORD", value)
    assert out.returncode == 1
    assert "GRAFANA_ADMIN_PASSWORD" in out.stderr
    if value:
        assert value not in out.stderr and value not in out.stdout


def test_cli_accepts_a_real_value_and_prints_nothing():
    value = REAL_SECRET
    out = run_cli("GRAFANA_ADMIN_PASSWORD", value)
    assert out.returncode == 0
    assert value not in out.stdout + out.stderr


def test_cli_guard_bites_on_a_missing_name():
    out = subprocess.run([sys.executable, "-I", str(SCRIPT)], input="x", capture_output=True, text=True, check=False)
    assert out.returncode == 2


# --- The OpenTofu validations carry the same pattern, byte for byte. ---

TOKEN_VARIABLES = [
    ROOT / "stacks" / "10-access" / "variables.tf",
    ROOT / "modules" / "twingate-connector" / "variables.tf",
    ROOT / "modules" / "twingate-bootstrap" / "variables.tf",
]


def token_block(path):
    text = path.read_text()
    start = text.index('variable "log_shipping_bootstrap_token"')
    return text[start : text.index("\nvariable ", start + 1)] if "\nvariable " in text[start + 1 :] else text[start:]


@pytest.mark.parametrize("path", [p for p in TOKEN_VARIABLES if "stacks" in str(p) or "twingate-bootstrap" in str(p)])
def test_tofu_token_validation_uses_the_one_pattern(path):
    block = token_block(path)
    assert sr.PLACEHOLDER_RE2 in block, f"{path.relative_to(ROOT)} must carry the pattern from scripts/secret_rule.py"


def test_the_pattern_is_re2_safe_and_matches_the_python_rule():
    assert '"' not in sr.PLACEHOLDER_RE2 and "\\" not in sr.PLACEHOLDER_RE2
    for v in PLACEHOLDERS:
        if v.strip():
            assert re.search(sr.PLACEHOLDER_RE2, v), v
    for v in REAL_LOOKING:
        assert not re.search(sr.PLACEHOLDER_RE2, v), v


# --- The Spacelift hook script uses a shell copy, pinned to the Python rule. ---


def shell_is_placeholder(value):
    cmd = f'. "{DOPPLER_ENV}"; cah_doppler_is_placeholder "$V" && echo placeholder || echo ok'
    out = subprocess.run(["/bin/sh", "-c", cmd], env={"PATH": os.environ["PATH"], "V": value},
                         capture_output=True, text=True, check=True)
    return out.stdout.strip() == "placeholder"


@pytest.mark.parametrize("value", PLACEHOLDERS + REAL_LOOKING)
def test_shell_copy_agrees_with_the_python_rule(value):
    assert shell_is_placeholder(value) == sr.is_placeholder(value), repr(value)


TOOLS = ["uname", "sed", "mkdir", "rm", "sha256sum", "tar", "cat", "env", "printf", "mktemp", "tr"]


def hook(tmp_path, name, value, doppler_token=DOPPLER_TOKEN):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for tool in TOOLS:
        found = shutil.which(tool)
        if found and not (bin_dir / tool).exists():
            (bin_dir / tool).symlink_to(found)
    stub = bin_dir / "doppler"
    stub.write_text(
        '#!/bin/sh\nif [ "$1" = "--version" ]; then echo v3.77.0; exit 0; fi\nprintf \'%s\' "$STUB_VALUE"\n'
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    env = {
        "PATH": str(bin_dir), "CAH_DOPPLER_DIR": str(tmp_path / "dl"),
        "DOPPLER_TOKEN": doppler_token, "DOPPLER_PROJECT": "proj", "DOPPLER_CONFIG": "prd",
        "TF_VAR_spacelift_run_type": "TRACKED", "TF_VAR_spacelift_commit_branch": "main",
        "STUB_VALUE": value,
    }
    cmd = f'. "{DOPPLER_ENV}"; cah_doppler_env {name}; echo "rc=$?"; echo "GOT=${{{name}:-unset}}"'
    return subprocess.run(["/bin/sh", "-c", cmd], env=env, capture_output=True, text=True, check=False)


@pytest.mark.parametrize("value", ["changeme-changeme", "your_token_value", "<token>", "xxxxxxxx"])
def test_hook_refuses_a_placeholder_secret_and_never_prints_it(tmp_path, value):
    out = hook(tmp_path, "TWINGATE_API_TOKEN", value)
    assert "rc=1" in out.stdout and "GOT=unset" in out.stdout
    assert "TWINGATE_API_TOKEN" in out.stdout
    assert value not in out.stdout + out.stderr


def test_hook_accepts_a_real_looking_secret(tmp_path):
    out = hook(tmp_path, "TWINGATE_API_TOKEN", REAL_SECRET)
    assert "rc=0" in out.stdout and f"GOT={REAL_SECRET}" in out.stdout


def test_hook_does_not_apply_the_rule_to_a_public_value(tmp_path):
    # A public SSH key may carry a comment such as example.com; it is not a secret.
    key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIexample user@example.com"
    out = hook(tmp_path, "ADMIN_SSH_PUBLIC_KEY", key)
    assert "rc=0" in out.stdout


def test_hook_refuses_a_placeholder_doppler_token(tmp_path):
    out = hook(tmp_path, "TWINGATE_API_TOKEN", REAL_SECRET, doppler_token="dp.st.your-token")
    assert "rc=1" in out.stdout
    assert "DOPPLER_TOKEN" in out.stdout
    assert "dp.st.your-token" not in out.stdout + out.stderr


# --- scripts/demo_monitoring.sh: the Grafana admin password ---


def demo_env(tmp_path, shell_value=None, env_file=None):
    lab = tmp_path / "lab"
    lab.mkdir(exist_ok=True)
    shutil.copy(ROOT / "labs" / "demo-monitoring" / "env.example", lab / "env.example")
    if env_file is not None:
        (lab / ".env").write_text(env_file)
    env = {k: v for k, v in os.environ.items() if k != "GRAFANA_ADMIN_PASSWORD"}
    if shell_value is not None:
        env["GRAFANA_ADMIN_PASSWORD"] = shell_value
    out = subprocess.run(
        ["bash", "-c", f'source "{DEMO}"; LAB="{lab}"; ensure_env'],
        env=env, capture_output=True, text=True, check=False,
    )
    return lab, out


@pytest.mark.parametrize("value", ["changeme", "your_password_here", "admin", "<password>"])
def test_demo_refuses_a_placeholder_from_the_shell(tmp_path, value):
    _, out = demo_env(tmp_path, shell_value=value)
    assert out.returncode != 0
    assert "GRAFANA_ADMIN_PASSWORD" in out.stderr
    assert value not in out.stdout + out.stderr


@pytest.mark.parametrize("value", ["changeme", "your_password_here", "password"])
def test_demo_refuses_a_placeholder_in_the_env_file_and_leaves_the_file_alone(tmp_path, value):
    body = f"GRAFANA_ADMIN_PASSWORD={value}\nDEMO_GRAFANA_PORT=3999\n"
    lab, out = demo_env(tmp_path, env_file=body)
    assert out.returncode != 0
    assert "GRAFANA_ADMIN_PASSWORD" in out.stderr
    assert value not in out.stdout + out.stderr
    assert (lab / ".env").read_text() == body


def test_demo_accepts_a_real_password_and_does_not_rewrite_the_file(tmp_path):
    body = f"GRAFANA_ADMIN_PASSWORD={REAL_SECRET}\n"
    lab, out = demo_env(tmp_path, env_file=body)
    assert out.returncode == 0
    assert (lab / ".env").read_text() == body


def test_demo_generates_a_password_for_an_empty_value_and_keeps_other_settings(tmp_path):
    lab, out = demo_env(tmp_path, env_file="GRAFANA_ADMIN_PASSWORD=\nDEMO_GRAFANA_PORT=3999\n")
    assert out.returncode == 0
    text = (lab / ".env").read_text()
    assert "DEMO_GRAFANA_PORT=3999" in text, "an existing .env must not be overwritten"
    value = re.search(r"^GRAFANA_ADMIN_PASSWORD=(.+)$", text, re.MULTILINE).group(1)
    assert len(value) >= 20 and not sr.is_placeholder(value)
    assert value not in out.stdout + out.stderr


def test_demo_generates_a_file_when_there_is_none(tmp_path):
    lab, out = demo_env(tmp_path)
    assert out.returncode == 0
    value = re.search(r"^GRAFANA_ADMIN_PASSWORD=(.+)$", (lab / ".env").read_text(), re.MULTILINE).group(1)
    assert len(value) >= 20 and value not in out.stdout + out.stderr


def test_demo_env_example_carries_no_value_and_says_required():
    text = (ROOT / "labs" / "demo-monitoring" / "env.example").read_text()
    assert re.search(r"^GRAFANA_ADMIN_PASSWORD=$", text, re.MULTILINE)
    assert "required" in text.lower()


# --- labs/wordpress-at-scale/lab.sh: the origin secret ---


def wp_check(tmp_path, env_file):
    lab = tmp_path / "wp"
    lab.mkdir(exist_ok=True)
    if env_file is not None:
        (lab / ".env").write_text(env_file)
    env = {k: v for k, v in os.environ.items() if k != "ORIGIN_SECRET"}
    out = subprocess.run(
        ["bash", "-c", f'source "{WP_LAB / "lab.sh"}"; LAB="{lab}"; ensure_origin_secret'],
        env=env, capture_output=True, text=True, check=False,
    )
    return lab, out


@pytest.mark.parametrize("value", ["changeme", "your_secret_here", "example"])
def test_wp_lab_refuses_a_placeholder_origin_secret(tmp_path, value):
    _lab, out = wp_check(tmp_path, f"ORIGIN_SECRET={value}\n")
    assert out.returncode != 0
    assert "ORIGIN_SECRET" in out.stderr
    assert value not in out.stdout + out.stderr


def test_wp_lab_generates_for_missing_or_empty_and_accepts_a_real_one(tmp_path):
    for body in (None, "ORIGIN_SECRET=\n"):
        lab, out = wp_check(tmp_path, body)
        assert out.returncode == 0, out.stderr
        value = re.search(r"^ORIGIN_SECRET=(.+)$", (lab / ".env").read_text(), re.MULTILINE).group(1)
        assert re.fullmatch(r"[0-9a-f]{32}", value) and value not in out.stdout + out.stderr
    real = HEX_SECRET
    lab, out = wp_check(tmp_path, f"ORIGIN_SECRET={real}\n")
    assert out.returncode == 0
    assert (lab / ".env").read_text() == f"ORIGIN_SECRET={real}\n"


def test_wp_lab_powershell_twin_carries_the_one_pattern():
    text = (WP_LAB / "lab.ps1").read_text()
    assert sr.PLACEHOLDER_RE2 in text
    assert "refusing to start: ORIGIN_SECRET" in text


def test_wp_lab_bash_refuses_before_compose_runs():
    text = (WP_LAB / "lab.sh").read_text()
    up = text.split("  up)")[1].split("compose --env-file")[0]
    assert "ensure_origin_secret" in up
