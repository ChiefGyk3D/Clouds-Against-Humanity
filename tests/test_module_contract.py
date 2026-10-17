"""The provider module contract, checked structurally.

Every provider supplies the same module roles with the same output names, and
documents what differs in a README. A new provider's modules are found by their
directory name, so adding one without the contract fails here.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONTRACT = {
    "vpc": {"id", "ip_range", "name"},
    "firewall": {"id", "name", "rule_targets", "source_members", "destination_members"},
    "twingate-connector": {"instance_id", "instance_name", "private_ip", "size"},
}


def provider_modules():
    for role in CONTRACT:
        for path in sorted((ROOT / "modules").glob(f"**/{role}")):
            if ".terraform" in path.parts or not path.is_dir():
                continue
            yield role, path


def outputs(path):
    text = (path / "outputs.tf").read_text()
    return set(re.findall(r'(?m)^output\s+"([A-Za-z0-9_-]+)"', text))


def providers():
    """Map provider (modules/<provider>/<role>; DigitalOcean is modules/<role>) to its roles."""
    found = {}
    for role, path in provider_modules():
        # DigitalOcean sits directly under modules/; others under modules/<provider>/.
        provider = "digitalocean" if path.parent.name == "modules" else path.parent.name
        found.setdefault(provider, {})[role] = path
    return found


def test_every_provider_supplies_every_role():
    assert providers(), "no provider modules found"
    for provider, roles in providers().items():
        missing = set(CONTRACT) - set(roles)
        assert not missing, f"provider {provider} lacks modules: {sorted(missing)}"


def test_every_provider_module_has_the_contract_outputs():
    for role, path in provider_modules():
        missing = CONTRACT[role] - outputs(path)
        assert not missing, (
            f"{path.relative_to(ROOT)} lacks contract outputs: {sorted(missing)}"
        )


def test_no_output_exposes_boot_data_or_tokens():
    # The connector's user_data holds the Twingate tokens. A contract output
    # name proves nothing about its value, so look at every output expression.
    for _, path in provider_modules():
        text = (path / "outputs.tf").read_text()
        for needle in (
            "user_data",
            "custom_data",
            "metadata_startup_script",
            "token",
            "bootstrap",
        ):
            assert needle not in text, (
                f"{path.relative_to(ROOT)}/outputs.tf mentions {needle!r}"
            )


def test_every_provider_module_documents_roles_and_extensions():
    for role, path in provider_modules():
        readme = path / "README.md"
        assert readme.exists(), f"{path.relative_to(ROOT)} has no README.md"
        text = readme.read_text()
        rows = re.findall(r"(?m)^\| Role \|.*\n\|[-| ]+\|\n((?:\|.*\n)+)", text)
        assert rows and len(rows[0].strip().splitlines()) >= 1, (
            f"{readme.relative_to(ROOT)}: role table has no rows"
        )
        ext = re.search(r"## Provider extensions\n+(.+)", text, re.DOTALL)
        assert ext and len(ext.group(1).strip()) >= 40, (
            f"{readme.relative_to(ROOT)}: empty extensions section"
        )
        for name in CONTRACT[role]:
            assert f"`{name}`" in text, (
                f"{readme.relative_to(ROOT)} does not describe contract output `{name}`"
            )
