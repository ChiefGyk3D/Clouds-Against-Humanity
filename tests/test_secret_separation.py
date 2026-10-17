"""Per-cloud secret separation, repository side (phase 2c-iii of issue #22).

Design section 4, point 4: each cloud gets its own Doppler config and Spacelift
context, and a stack may only ask for its own cloud's secrets. Doppler cannot be
called from CI, so these tests prove only what the repository declares: which
secret NAMES each stack requests. They cannot prove that a Doppler token is
narrow or that a context is attached to the right stacks. See "More than one
cloud" in docs/spacelift-secrets.md.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".spacelift" / "config.yml"
SCRIPT = ROOT / "scripts" / "spacelift" / "doppler-env.sh"

# Stack name pattern -> provider. First match wins; everything else is DigitalOcean.
STACK_PROVIDERS = [
    (re.compile(r"^cah-aws-"), "aws"),
    (re.compile(r"^cah-azure-"), "azure"),
    (re.compile(r"^cah-gcp-"), "gcp"),
]
DEFAULT_PROVIDER = "digitalocean"

# Prefixes that identify a cloud's own credentials and settings.
CLOUD_PREFIXES = {
    "digitalocean": ("DIGITALOCEAN_",),
    "aws": ("AWS_",),
    "azure": ("ARM_", "AZURE_"),
    "gcp": ("GOOGLE_", "GCP_"),
}
# Non-cloud names any stack may request.
SHARED_PREFIXES = ("TWINGATE_", "ADMIN_")


def provider_for(stack):
    for pattern, provider in STACK_PROVIDERS:
        if pattern.match(stack):
            return provider
    return DEFAULT_PROVIDER


def parse_calls(text):
    """Map stack -> hook -> arguments of EVERY cah_doppler_env call. Stdlib only, no YAML parser."""
    calls, stack, hook = {}, None, None
    for line in text.splitlines():
        if re.match(r"^  [a-z0-9-]+:\s*$", line):
            stack = line.strip().rstrip(":")
            calls[stack] = {}
            hook = None
        elif re.match(r"^    (before|after)_[a-z]+:\s*$", line):
            hook = line.strip().rstrip(":")
        elif "cah_doppler_env" in line and stack and hook:
            args = line.split("cah_doppler_env", 1)[1].split()
            calls[stack].setdefault(hook, []).extend(args)
    return calls


def secret_names(args):
    """The Doppler source names of a call: NAME, or the NAME in VAR=NAME."""
    return [a.partition("=")[2] or a for a in args]


def violations(calls):
    """Return 'stack: reason' strings; empty when the config is clean."""
    problems = []
    for stack, hooks in calls.items():
        provider = provider_for(stack)
        own = CLOUD_PREFIXES[provider]
        foreign = tuple(
            p for k, v in CLOUD_PREFIXES.items() if k != provider for p in v
        )
        if set(hooks) != {"before_init", "before_apply"}:
            problems.append(f"{stack}: needs exactly before_init and before_apply")
        elif hooks["before_init"] != hooks["before_apply"]:
            problems.append(f"{stack}: before_init and before_apply differ")
        for args in hooks.values():
            for arg in args:
                var, _, src = arg.partition("=")
                for name in {var, src or var}:
                    if name.startswith(foreign):
                        problems.append(f"{stack} ({provider}) requests {name}")
            for name in secret_names(args):
                if not name.startswith(own + SHARED_PREFIXES):
                    problems.append(f"{stack} ({provider}) requests unlisted {name}")
    return sorted(set(problems))


def write_config(path, stacks):
    lines = ['version: "1"', "", "stacks:"]
    for stack, args in stacks.items():
        calls = [args] if isinstance(args, str) else args
        lines.append(f"  {stack}:")
        for hook in ("before_init", "before_apply"):
            lines += [
                f"    {hook}:",
                "      - . /mnt/workspace/source/scripts/spacelift/doppler-env.sh",
            ]
            lines += [f"      - cah_doppler_env {call}" for call in calls]
    path.write_text("\n".join(lines) + "\n")
    return path


def code_lines(path):
    return "\n".join(
        line
        for line in path.read_text().splitlines()
        if not line.lstrip().startswith("#")
    )


def test_real_config_has_stacks_and_passes():
    calls = parse_calls(CONFIG.read_text())
    assert calls, "no stacks found in .spacelift/config.yml"
    assert violations(calls) == []


def test_stacks_map_to_the_expected_provider():
    for stack in ("cah-00-foundation", "cah-10-access"):
        assert provider_for(stack) == "digitalocean", stack
    assert provider_for("cah-aws-00-foundation") == "aws"
    assert provider_for("cah-azure-00-foundation") == "azure"
    assert provider_for("cah-gcp-00-foundation") == "gcp"


@pytest.mark.parametrize(
    ("stack", "args", "expect"),
    [
        ("cah-00-foundation", "DIGITALOCEAN_TOKEN AWS_SECRET_ACCESS_KEY", "AWS_SECRET"),
        (
            "cah-aws-00-foundation",
            "AWS_ACCESS_KEY_ID DIGITALOCEAN_TOKEN",
            "DIGITALOCEAN",
        ),
        ("cah-azure-00-foundation", "ARM_CLIENT_SECRET GOOGLE_CREDENTIALS", "GOOGLE_"),
        ("cah-gcp-00-foundation", "GOOGLE_CREDENTIALS ARM_CLIENT_SECRET", "ARM_"),
        ("cah-aws-00-foundation", "TF_VAR_x=DIGITALOCEAN_TOKEN", "DIGITALOCEAN"),
        ("cah-aws-00-foundation", "AWS_X=GOOGLE_CREDENTIALS", "GOOGLE_"),
    ],
)
def test_fixture_requesting_another_clouds_secret_fails(tmp_path, stack, args, expect):
    path = write_config(tmp_path / "config.yml", {stack: args})
    found = violations(parse_calls(path.read_text()))
    assert any(expect in p for p in found), found


def test_fixture_with_only_own_and_shared_names_passes(tmp_path):
    path = write_config(
        tmp_path / "config.yml",
        {
            "cah-aws-10-access": "AWS_ACCESS_KEY_ID TWINGATE_API_TOKEN "
            "TF_VAR_admin_ssh_public_key=ADMIN_SSH_PUBLIC_KEY",
            "cah-gcp-10-access": "GOOGLE_CREDENTIALS TWINGATE_NETWORK",
        },
    )
    assert violations(parse_calls(path.read_text())) == []


def test_unlisted_non_cloud_name_is_refused(tmp_path):
    path = write_config(tmp_path / "config.yml", {"cah-00-foundation": "SLACK_WEBHOOK"})
    found = violations(parse_calls(path.read_text()))
    assert any("unlisted SLACK_WEBHOOK" in p for p in found), found


def test_hooks_that_differ_or_are_missing_are_refused():
    calls = {"cah-00-foundation": {"before_init": ["DIGITALOCEAN_TOKEN"]}}
    assert any("exactly" in p for p in violations(calls))
    calls = {
        "cah-00-foundation": {
            "before_init": ["DIGITALOCEAN_TOKEN"],
            "before_apply": ["DIGITALOCEAN_TOKEN", "TWINGATE_API_TOKEN"],
        }
    }
    assert any("differ" in p for p in violations(calls))


@pytest.mark.parametrize(
    ("stack", "extra"),
    [
        ("cah-00-foundation", "AWS_ACCESS_KEY_ID"),
        ("cah-10-access", "GOOGLE_CREDENTIALS"),
        ("cah-10-access", "TF_VAR_k=ARM_CLIENT_SECRET"),
    ],
)
def test_mutating_the_real_config_in_memory_is_caught(stack, extra):
    calls = parse_calls(CONFIG.read_text())
    calls[stack]["before_init"] = calls[stack]["before_init"] + [extra]
    calls[stack]["before_apply"] = list(calls[stack]["before_init"])
    found = violations(calls)
    assert found
    assert all(p.startswith(stack) for p in found), found


def test_script_takes_project_and_config_only_from_the_environment():
    code = code_lines(SCRIPT)
    # Never assigned in the script: they come from the Spacelift context.
    assert not re.search(r"\bDOPPLER_(PROJECT|CONFIG|TOKEN)=", code)
    # Passed to the CLI as environment expansions, not literals.
    assert re.search(r'--project "\$DOPPLER_PROJECT"', code)
    assert re.search(r'--config "\$DOPPLER_CONFIG"', code)
    assert not re.search(r"--(project|config)\s+(?!\"\$DOPPLER_)\S", code)
    # No literal config name, including the conventions the docs suggest.
    assert not re.search(r"(?<![/\w])(dev|prd)(_[a-z]+)?(?![/\w])", code)


def test_config_does_not_set_doppler_context_variables():
    assert not re.search(r"DOPPLER_(PROJECT|CONFIG|TOKEN)", code_lines(CONFIG))


def test_every_call_in_a_hook_is_checked_not_just_the_last(tmp_path):
    path = write_config(
        tmp_path / "config.yml",
        {"cah-00-foundation": ["AWS_SECRET_ACCESS_KEY", "DIGITALOCEAN_TOKEN"]},
    )
    calls = parse_calls(path.read_text())
    assert calls["cah-00-foundation"]["before_init"] == [
        "AWS_SECRET_ACCESS_KEY",
        "DIGITALOCEAN_TOKEN",
    ]
    assert any("AWS_SECRET" in p for p in violations(calls))
