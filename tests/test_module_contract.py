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
        for path in sorted(ROOT.glob(f"**/modules/{role}")):
            if ".terraform" in path.parts or not path.is_dir():
                continue
            yield role, path


def outputs(path):
    text = (path / "outputs.tf").read_text()
    return set(re.findall(r'(?m)^output\s+"([A-Za-z0-9_-]+)"', text))


def test_every_role_has_at_least_one_provider():
    roles = {role for role, _ in provider_modules()}
    assert roles == set(CONTRACT), f"no module for: {sorted(set(CONTRACT) - roles)}"


def test_every_provider_module_has_the_contract_outputs():
    for role, path in provider_modules():
        missing = CONTRACT[role] - outputs(path)
        assert not missing, (
            f"{path.relative_to(ROOT)} lacks contract outputs: {sorted(missing)}"
        )


def test_every_provider_module_documents_roles_and_extensions():
    for role, path in provider_modules():
        readme = path / "README.md"
        assert readme.exists(), f"{path.relative_to(ROOT)} has no README.md"
        text = readme.read_text()
        assert "| Role |" in text, f"{readme.relative_to(ROOT)}: no role table"
        assert "## Provider extensions" in text, (
            f"{readme.relative_to(ROOT)}: no extensions section"
        )
        for name in CONTRACT[role]:
            assert name in text, (
                f"{readme.relative_to(ROOT)} does not mention contract output {name}"
            )
