"""Per-cloud secret separation, repository side (phase 2c-iii of issue #22).

Design section 4, point 4: each cloud gets its own Doppler config and Spacelift
context, and a stack may only ask for its own cloud's secrets. Doppler cannot be
called from CI, so these tests prove only what the repository declares: which
secret NAMES each stack requests. They cannot prove that a Doppler token is
narrow or that a context is attached to the right stacks. See "More than one
cloud" in docs/spacelift-secrets.md.

The config is parsed with PyYAML (a pinned CI test dependency) and validated
fail-closed: any shape this file does not understand is a violation, never a
silent skip.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".spacelift" / "config.yml"
SCRIPT = ROOT / "scripts" / "spacelift" / "doppler-env.sh"

HOOKS = ("before_init", "before_apply")
SOURCE_LINE = ". /mnt/workspace/source/scripts/spacelift/doppler-env.sh"
NAME = r"[A-Za-z_][A-Za-z0-9_]*"
CALL_RE = re.compile(rf"cah_doppler_env( {NAME}(={NAME})?)+")

# Every accepted stack name matches exactly one of these. Anything else fails.
STACK_PATTERNS = {
    "digitalocean": re.compile(r"cah-00-foundation|cah-10-access|cah-20-telemetry"),
    "aws": re.compile(r"cah-aws-[a-z0-9]+(-[a-z0-9]+)*"),
    "azure": re.compile(r"cah-azure-[a-z0-9]+(-[a-z0-9]+)*"),
    "gcp": re.compile(r"cah-gcp-[a-z0-9]+(-[a-z0-9]+)*"),
}

# Prefixes that identify a cloud's own credentials and settings.
CLOUD_PREFIXES = {
    "digitalocean": ("DIGITALOCEAN_",),
    "aws": ("AWS_",),
    "azure": ("ARM_", "AZURE_"),
    "gcp": ("GOOGLE_", "GCP_"),
}
# Non-cloud names any stack may request: exact names, not prefixes, so a cloud
# credential cannot hide behind an allowed prefix (ADMIN_AWS_SECRET_...).
SHARED_NAMES = frozenset(
    {
        "TWINGATE_API_TOKEN",
        "TWINGATE_NETWORK",
        "ADMIN_SSH_PUBLIC_KEY",
        "ADMIN_SSH_KEY_NAME",
        "ADMIN_USER_IDS",
    }
)


def provider_for(stack):
    """The provider of a stack name, or None when it matches no pattern."""
    hits = [p for p, rx in STACK_PATTERNS.items() if rx.fullmatch(str(stack))]
    return hits[0] if len(hits) == 1 else None


class _Strict(yaml.SafeLoader):
    """SafeLoader that rejects duplicate keys."""


def _no_dupes(loader, node, deep=False):
    keys = [loader.construct_object(k, deep=True) for k, _ in node.value]
    if len(keys) != len(set(map(repr, keys))):
        raise yaml.constructor.ConstructorError(
            None, None, "duplicate key", node.start_mark
        )
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dupes)


def load(text):
    """Parse the config. Returns (data, problems); aliases and anchors are refused."""
    try:
        for event in yaml.parse(text, Loader=yaml.SafeLoader):
            if isinstance(event, yaml.AliasEvent) or getattr(event, "anchor", None):
                return None, ["config: anchors and aliases are not allowed"]
        return yaml.load(text, Loader=_Strict), []  # _Strict is a SafeLoader subclass
    except yaml.YAMLError as err:
        return None, [f"config: invalid YAML ({type(err).__name__})"]


def validate(text):
    """Return (stacks, problems): stacks maps each validated stack to its call args."""
    data, problems = load(text)
    if problems:
        return {}, problems
    if not isinstance(data, dict) or set(data) != {"version", "stacks"}:
        return {}, ["config: top level must be exactly version and stacks"]
    if not isinstance(data["stacks"], dict) or not data["stacks"]:
        return {}, ["config: stacks must be a non-empty mapping"]
    validated = {}
    for stack, hooks in data["stacks"].items():
        found = _check_stack(stack, hooks, problems)
        if found is not None:
            validated[stack] = found
    return validated, sorted(set(problems))


def _check_stack(stack, hooks, problems):
    provider = provider_for(stack) if isinstance(stack, str) else None
    if provider is None:
        problems.append(f"{stack!r}: not a known stack name or cloud pattern")
        return None
    if not isinstance(hooks, dict) or set(hooks) != set(HOOKS):
        problems.append(f"{stack}: needs exactly before_init and before_apply")
        return None
    per_hook = {}
    for hook in HOOKS:
        before = len(problems)
        args = _check_hook(stack, provider, hook, hooks[hook], problems)
        if args is None or len(problems) != before:
            return None
        per_hook[hook] = args
    if per_hook["before_init"] != per_hook["before_apply"]:
        problems.append(f"{stack}: before_init and before_apply differ")
        return None
    return per_hook["before_init"]


def _check_hook(stack, provider, hook, entries, problems):
    where = f"{stack}.{hook}"
    if not isinstance(entries, list) or len(entries) != 2:
        problems.append(
            f"{where}: must be the source line then one cah_doppler_env call"
        )
        return None
    source, call = entries
    if source != SOURCE_LINE:
        problems.append(f"{where}: first entry must be the doppler-env source line")
        return None
    if not isinstance(call, str) or not CALL_RE.fullmatch(call):
        problems.append(f"{where}: second entry is not a plain cah_doppler_env call")
        return None
    args = call.split()[1:]
    own = CLOUD_PREFIXES[provider]
    foreign = tuple(p for k, v in CLOUD_PREFIXES.items() if k != provider for p in v)
    for arg in args:
        var, _, src = arg.partition("=")
        src = src or var
        if var != src and not var.startswith("TF_VAR_"):
            problems.append(f"{where}: {var} is not TF_VAR_ or the secret's own name")
        for name in (var, src):
            bare = name.removeprefix("TF_VAR_").upper()
            if bare.startswith(foreign):
                problems.append(f"{where} ({provider}) requests {name}")
        if not (src.startswith(own) or src in SHARED_NAMES):
            problems.append(f"{where} ({provider}) requests unlisted {src}")
    return args


def config_text(stacks, *, extra_top=""):
    """Build a config from {stack: [call, ...]}; each hook repeats the calls."""
    lines = ['version: "1"', extra_top, "stacks:"]
    for stack, calls in stacks.items():
        lines.append(f"  {stack}:")
        for hook in HOOKS:
            lines += [f"    {hook}:", f"      - {SOURCE_LINE}"]
            lines += [f"      - {call}" for call in calls]
    return "\n".join(lines) + "\n"


def problems_for(stacks):
    return validate(config_text(stacks))[1]


def code_lines(path):
    return "\n".join(
        line
        for line in path.read_text().splitlines()
        if not line.lstrip().startswith("#")
    )


def test_real_config_passes_and_every_stack_was_validated():
    validated, problems = validate(CONFIG.read_text())
    assert problems == []
    raw = yaml.safe_load(CONFIG.read_text())["stacks"]
    assert set(validated) == set(raw) == {
        "cah-00-foundation",
        "cah-10-access",
        "cah-20-telemetry",
    }


def test_stack_classification_is_explicit_and_fail_closed():
    assert provider_for("cah-00-foundation") == "digitalocean"
    assert provider_for("cah-aws-00-foundation") == "aws"
    assert provider_for("cah-azure-00-foundation") == "azure"
    assert provider_for("cah-gcp-00-foundation") == "gcp"
    for bad in (
        "cah-awsx-00",
        "cah-AWS-00",
        "CAH-AWS-00",
        "unrelated-stack",
        "aws-00",
        "cah-aws-",
        "cah-30-new",
    ):
        assert provider_for(bad) is None, bad
        assert any(
            "not a known stack name" in p
            for p in problems_for({bad: ["cah_doppler_env DIGITALOCEAN_TOKEN"]})
        )


def test_cloud_prefixes_and_shared_names_are_disjoint():
    prefixes = [p for v in CLOUD_PREFIXES.values() for p in v]
    for name in SHARED_NAMES:
        assert not name.startswith(tuple(prefixes)), name
        for p in prefixes:
            assert p not in name, (name, p)
    for a in prefixes:
        for b in prefixes:
            assert a == b or not a.startswith(b), (a, b)


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
        ("cah-00-foundation", "ADMIN_AWS_SECRET_ACCESS_KEY", "unlisted ADMIN_AWS"),
        (
            "cah-aws-00-foundation",
            "ADMIN_DIGITALOCEAN_TOKEN",
            "unlisted ADMIN_DIGITALOCEAN",
        ),
        (
            "cah-00-foundation",
            "TWINGATE_AWS_SECRET_ACCESS_KEY",
            "unlisted TWINGATE_AWS",
        ),
        ("cah-00-foundation", "SLACK_WEBHOOK", "unlisted SLACK_WEBHOOK"),
    ],
)
def test_requesting_another_clouds_or_unlisted_secret_fails(stack, args, expect):
    found = problems_for({stack: [f"cah_doppler_env {args}"]})
    assert any(expect in p for p in found), found


AWS_CALL = (
    "cah_doppler_env AWS_ACCESS_KEY_ID TWINGATE_API_TOKEN"
    " TF_VAR_admin_ssh_public_key=ADMIN_SSH_PUBLIC_KEY"
)


AWS_CALL = (
    "cah_doppler_env AWS_ACCESS_KEY_ID TWINGATE_API_TOKEN"
    " TF_VAR_admin_ssh_public_key=ADMIN_SSH_PUBLIC_KEY"
)


def test_own_and_shared_names_pass():
    assert (
        problems_for(
            {
                "cah-aws-10-access": [AWS_CALL],
                "cah-gcp-10-access": [
                    "cah_doppler_env GOOGLE_CREDENTIALS TWINGATE_NETWORK"
                ],
            }
        )
        == []
    )


def test_a_second_call_in_a_hook_is_not_hidden_by_the_last_one():
    found = problems_for(
        {
            "cah-aws-00-foundation": [
                "cah_doppler_env DIGITALOCEAN_TOKEN",
                "cah_doppler_env AWS_ACCESS_KEY_ID",
            ]
        }
    )
    assert any("must be the source line then one" in p for p in found), found


def test_folded_scalar_call_is_parsed_not_skipped():
    text = 'version: "1"\nstacks:\n  cah-aws-00-foundation:\n' + "".join(
        f"    {h}:\n      - {SOURCE_LINE}\n      - >-\n"
        "        cah_doppler_env\n        DIGITALOCEAN_TOKEN\n"
        for h in HOOKS
    )
    assert any("DIGITALOCEAN" in p for p in validate(text)[1])


def test_folded_scalar_plus_second_call_is_refused():
    text = 'version: "1"\nstacks:\n  cah-aws-00-foundation:\n' + "".join(
        f"    {h}:\n      - {SOURCE_LINE}\n      - >-\n"
        "        cah_doppler_env\n        DIGITALOCEAN_TOKEN\n"
        "      - cah_doppler_env AWS_ACCESS_KEY_ID\n"
        for h in HOOKS
    )
    assert validate(text)[1]


def test_anchor_and_alias_are_refused():
    text = (
        'version: "1"\nx-evil: &evil cah_doppler_env DIGITALOCEAN_TOKEN\nstacks:\n'
        "  cah-aws-00-foundation:\n"
        + "".join(f"    {h}:\n      - {SOURCE_LINE}\n      - *evil\n" for h in HOOKS)
    )
    assert validate(text)[1] == ["config: anchors and aliases are not allowed"]


@pytest.mark.parametrize("key", ['"CAH-AWS-00"', '"cah-aws-00"x', "  cah-AWS-00"])
def test_quoted_uppercase_or_odd_stack_keys_are_not_skipped(key):
    text = f'version: "1"\nstacks:\n  {key.strip()}:\n' + "".join(
        f"    {h}:\n      - {SOURCE_LINE}\n      - cah_doppler_env DIGITALOCEAN_TOKEN\n"
        for h in HOOKS
    )
    assert validate(text)[1], key


def test_deeper_indentation_still_parsed_structurally():
    text = 'version: "1"\nstacks:\n    cah-aws-00-foundation:\n' + "".join(
        f"        {h}:\n            - {SOURCE_LINE}\n            - cah_doppler_env DIGITALOCEAN_TOKEN\n"
        for h in HOOKS
    )
    validated, problems = validate(text)
    assert any("DIGITALOCEAN" in p for p in problems)
    assert "cah-aws-00-foundation" not in validated


def test_duplicate_stack_keys_are_refused():
    call = "cah_doppler_env DIGITALOCEAN_TOKEN"
    block = "".join(f"    {h}:\n      - {SOURCE_LINE}\n      - {call}\n" for h in HOOKS)
    text = f'version: "1"\nstacks:\n  cah-00-foundation:\n{block}  cah-00-foundation:\n{block}'
    assert validate(text)[1]


@pytest.mark.parametrize(
    "entry",
    [
        "cah_doppler_env DIGITALOCEAN_TOKEN; cah_doppler_env AWS_ACCESS_KEY_ID",
        "cah_doppler_env DIGITALOCEAN_TOKEN && echo $DOPPLER_TOKEN",
        "echo $DOPPLER_TOKEN",
        "cah_doppler_env",
        "cah_doppler_env 'DIGITALOCEAN_TOKEN'",
        "cah_doppler_env $X",
    ],
)
def test_unsupported_command_shapes_fail_closed(entry):
    assert problems_for({"cah-00-foundation": [entry]}), entry


def test_non_string_and_missing_hooks_are_refused():
    for body in (
        "    before_init: [1, 2]\n    before_apply: [1, 2]\n",
        "    before_init: []\n    before_apply: []\n",
        f"    before_init: [{SOURCE_LINE!r}]\n",
        "    before_init: x\n    before_apply: x\n",
    ):
        text = f'version: "1"\nstacks:\n  cah-00-foundation:\n{body}'
        assert validate(text)[1], body


def test_differing_hooks_and_extra_top_level_keys_are_refused():
    text = config_text({"cah-00-foundation": ["cah_doppler_env DIGITALOCEAN_TOKEN"]})
    parts = text.rsplit("cah_doppler_env DIGITALOCEAN_TOKEN", 1)
    assert any(
        "differ" in p
        for p in validate("cah_doppler_env TWINGATE_API_TOKEN".join(parts))[1]
    )
    assert validate(config_text({}, extra_top="x: 1"))[1]


@pytest.mark.parametrize(
    ("stack", "old", "new"),
    [
        (
            "cah-00-foundation",
            "DIGITALOCEAN_TOKEN",
            "DIGITALOCEAN_TOKEN AWS_ACCESS_KEY_ID",
        ),
        (
            "cah-10-access",
            "DIGITALOCEAN_TOKEN",
            "DIGITALOCEAN_TOKEN GOOGLE_CREDENTIALS",
        ),
        ("cah-10-access", "ADMIN_USER_IDS", "ADMIN_USER_IDS ARM_CLIENT_SECRET"),
    ],
)
def test_mutating_the_real_config_text_is_caught(stack, old, new):
    text = CONFIG.read_text()
    start = text.index(f"  {stack}:")
    end = text.find("\n  cah-", start + 1)
    block = text[start : end if end != -1 else len(text)]
    mutated = text.replace(block, block.replace(old, new))
    assert mutated != text
    assert validate(mutated)[1]


def test_script_takes_project_and_config_only_from_the_environment():
    code = code_lines(SCRIPT)
    assert not re.search(r"\bDOPPLER_(PROJECT|CONFIG|TOKEN)=", code)
    assert re.search(r'--project "\$DOPPLER_PROJECT"', code)
    assert re.search(r'--config "\$DOPPLER_CONFIG"', code)
    assert not re.search(r"--(project|config)\s+(?!\"\$DOPPLER_)\S", code)
    assert not re.search(r"(?<![/\w])(dev|prd)(_[a-z]+)?(?![/\w])", code)


def test_config_does_not_set_doppler_context_variables():
    assert not re.search(r"DOPPLER_(PROJECT|CONFIG|TOKEN)", code_lines(CONFIG))
