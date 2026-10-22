"""Guards on the public edge (DMZ) stack, issue #122.

The edge ships DISABLED and UNAPPLIED: the stage is not approved and the cost
gate cannot price a reserved IP yet. These tests keep it that way on purpose:
every resource is behind the switch, the switch defaults to off, the stack is
not registered anywhere that could apply it, the cost manifest prices nothing,
and the cloud-init carries no admin path, no unpinned service package and no
secret-shaped value. Turning the edge on is a deliberate change that has to
edit the tests below in the same reviewed diff.
"""

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import cost_check

STACK = ROOT / "stacks/50-edge"
MODULE = ROOT / "modules/edge-host"


def read(path):
    return path.read_text(encoding="utf-8")


def strip_comments(text):
    return re.sub(r"(?m)(#|//).*$", "", text)


def blocks(text, kind):
    """(labels, body) of each top-level `kind` block; bodies are brace-balanced."""
    out = []
    for m in re.finditer(rf'(?m)^{kind}((?:\s+"[^"]+")+)\s*\{{', text):
        depth, i = 1, m.end()
        while depth and i < len(text):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        out.append((re.findall(r'"([^"]+)"', m.group(1)), text[m.end() : i - 1]))
    return out


def test_the_switch_defaults_to_off():
    variables = strip_comments(read(STACK / "variables.tf"))
    (_, body), = [b for b in blocks(variables, "variable") if b[0] == ["edge_enabled"]]
    assert re.search(r"(?m)^\s*default\s*=\s*false\s*$", body)
    assert re.search(r"(?m)^\s*nullable\s*=\s*false\s*$", body)


def test_every_resource_and_module_of_the_stack_is_behind_the_switch():
    main = strip_comments(read(STACK / "main.tf"))
    found = blocks(main, "resource") + blocks(main, "module")
    assert len(found) >= 5, "the scan lost its targets"
    for labels, body in found:
        assert re.search(r"(?m)^\s*count\s*=\s*local\.on\s*$", body), (
            f"{labels}: count = local.on is missing, so it would exist with the switch off"
        )
    assert re.search(r"(?m)^\s*on\s*=\s*var\.edge_enabled\s*\?\s*1\s*:\s*0\s*$", main)


def test_the_cost_manifest_prices_nothing_and_the_stage_is_not_approved():
    manifest = json.loads(read(STACK / "cost.json"))
    assert manifest["resources"] == []
    approved = json.loads(read(ROOT / "docs/stages/approved.json"))
    assert approved["current_phase"] != "edge"
    assert approved["phases"]["edge"]["status"] == "planned"
    assert approved["providers"]["digitalocean"]["approved_monthly_total"] == 12.0


def test_the_stack_is_not_registered_for_a_spacelift_apply():
    # A stanza in .spacelift/config.yml is what lets a stack load secrets and
    # apply. It is added in the pull request that approves the stage.
    config = read(ROOT / ".spacelift/config.yml")
    assert "50-edge" not in config
    assert "edge" not in config


def test_the_iperf3_sources_variable_keeps_its_ipv4_only_validation():
    # tests/test_ipv6_closed.py accepts var.iperf3_allowed_sources as an inbound
    # source only because this validation rejects IPv6 and the whole internet.
    variables = strip_comments(read(STACK / "variables.tf"))
    (_, body), = [b for b in blocks(variables, "variable") if b[0] == ["iperf3_allowed_sources"]]
    assert 'strcontains(s, ":")' in body
    assert 's != "0.0.0.0/0"' in body
    assert "can(cidrnetmask(s))" in body
    module_vars = strip_comments(read(MODULE / "variables.tf"))
    (_, body), = [b for b in blocks(module_vars, "variable") if b[0] == ["restricted_ports"]]
    assert 'strcontains(s, ":")' in body and 's != "0.0.0.0/0"' in body


def test_the_default_vpc_range_is_disjoint_from_the_core_default():
    import ipaddress

    def default_of(name):
        variables = strip_comments(read(STACK / "variables.tf"))
        (_, body), = [b for b in blocks(variables, "variable") if b[0] == [name]]
        return ipaddress.ip_network(re.search(r'default\s*=\s*"([^"]+)"', body).group(1))

    core = re.search(
        r'variable "vpc_ip_range".*?default\s*=\s*"([^"]+)"',
        read(ROOT / "stacks/00-foundation/variables.tf"),
        re.DOTALL,
    ).group(1)
    assert str(default_of("core_vpc_ip_range")) == core
    assert not default_of("vpc_ip_range").overlaps(ipaddress.ip_network(core))


def test_no_peering_and_no_core_tag_in_the_edge_code():
    peering = re.compile(r"digitalocean_vpc_peering|peering", re.IGNORECASE)
    core_tags = re.compile(r"cah-baseline|cah-access|cah-connector")
    for path in [*STACK.glob("*.tf"), *MODULE.glob("*.tf")]:
        text = strip_comments(read(path))
        assert not peering.search(text), f"{path.name}: VPC peering must never exist"
        assert not core_tags.search(text), f"{path.name}: references a core tag"


def test_the_droplet_has_no_admin_path():
    main = strip_comments(read(MODULE / "main.tf"))
    ((_, droplet),) = [b for b in blocks(main, "resource") if b[0][0] == "digitalocean_droplet"]
    assert not re.search(r"(?m)^\s*ssh_keys\s*=", droplet)
    assert re.search(r"(?m)^\s*ipv6\s*=\s*false\s*$", droplet)
    assert re.search(r"(?m)^\s*backups\s*=\s*false\s*$", droplet)
    template = read(MODULE / "cloud-init.yaml.tftpl")
    body = "\n".join(l for l in template.splitlines() if not l.lstrip().startswith("#") or l.startswith("#cloud-config"))
    assert "ssh_authorized_keys" not in body
    assert not re.search(r"(?m)^users:", body)
    assert "dport 22" not in body
    assert "mask, ssh.service, ssh.socket" in body
    assert "passwd, -l, root" in body
    assert "disable_root: true" in body


def packages_section(template):
    m = re.search(r"(?ms)^packages:\n(.*?)^[a-z_]+:", template)
    assert m, "no packages: section"
    return [l.strip() for l in m.group(1).splitlines() if l.strip() and not l.strip().startswith("#")]


def test_no_unpinned_service_package_in_the_cloud_init():
    template = read(MODULE / "cloud-init.yaml.tftpl")
    entries = packages_section(template)
    os_packages = {"- unattended-upgrades", "- chrony", "- nftables"}
    template_lines = {e for e in entries if e.startswith("%{")}
    pinned = [e for e in entries if e not in os_packages and e not in template_lines]
    # Anything beyond the OS packages is the one pinned [name, version] line the
    # service_packages loop renders.
    assert pinned == ["- [${name}, ${version}]"], pinned
    variables = strip_comments(read(MODULE / "variables.tf"))
    (_, body), = [b for b in blocks(variables, "variable") if b[0] == ["service_packages"]]
    assert re.search(r"(?m)^\s*default\s*=\s*\{\}\s*$", body)
    assert "latest" in body


SECRET_SHAPED = re.compile(r"token|secret|password|passwd|api[_-]?key|private[_-]?key|credential", re.IGNORECASE)
# The design allows exactly one secret-shaped field in user-data, a short-lived
# read-only Doppler bootstrap token (risk 6). It is NOT built yet, so none today.
ALLOWED_SECRET_FIELDS: set[str] = set()


def test_the_user_data_carries_no_secret_shaped_field():
    main = strip_comments(read(MODULE / "main.tf"))
    call = re.search(r"templatefile\([^,]+,\s*\{(.*?)\n\s*\}\)", main, re.DOTALL).group(1)
    names = set(re.findall(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", call))
    assert names, "the scan lost the templatefile arguments"
    assert {n for n in names if SECRET_SHAPED.search(n)} <= ALLOWED_SECRET_FIELDS
    # A fetched credential's name must not appear in the template either.
    template = read(MODULE / "cloud-init.yaml.tftpl")
    for needle in ("iperf3_key", "mqtt_password", "TWINGATE_", "authorized-users", "rsa-private-key", "DOPPLER"):
        assert needle not in template
    # No variable of the module is secret-shaped.
    for (name,), _ in blocks(strip_comments(read(MODULE / "variables.tf")), "variable"):
        assert not SECRET_SHAPED.search(name), name


def test_the_user_data_is_never_an_output():
    for path in (MODULE / "outputs.tf", STACK / "outputs.tf"):
        assert "user_data" not in strip_comments(read(path))


def test_the_host_firewall_is_default_drop_and_mirrors_the_cloud_firewall_input():
    template = read(MODULE / "cloud-init.yaml.tftpl")
    assert "policy drop;" in template
    stack = strip_comments(read(STACK / "main.tf"))
    # Both layers are built from the same two lists.
    assert re.search(r"public_ports\s*=\s*local\.public_ports", stack)
    assert re.search(r"restricted_ports\s*=\s*local\.restricted_ports", stack)
    assert re.search(r"for_each\s*=\s*local\.public_ports", stack)


@pytest.fixture()
def tree(tmp_path):
    """A copy of what the gate reads, to be edited on purpose."""
    for top in ("stacks", "modules", "docs"):
        shutil.copytree(
            ROOT / top,
            tmp_path / top,
            ignore=shutil.ignore_patterns(".terraform", "wiki", "images", "superpowers", "threat-model"),
        )
    shutil.copytree(ROOT / ".spacelift", tmp_path / ".spacelift")
    return tmp_path


def test_the_repository_gate_is_green_with_the_edge_present(tree):
    approved = json.loads(read(tree / "docs/stages/approved.json"))
    problems, _ = cost_check.gate_problems(tree, approved)
    assert problems == []


def test_pricing_a_droplet_for_the_edge_still_needs_approval_and_a_reserved_ip(tree):
    # With one droplet priced the edge-host reconciliation passes, but the total
    # ($18) is above the approved $12, and the missing reserved_ip is not priceable.
    manifest = tree / "stacks/50-edge/cost.json"
    manifest.write_text(
        json.dumps({"stage": 5, "resources": [{"name": "edge", "kind": "droplet", "size": "s-1vcpu-1gb", "backups": False}]})
    )
    approved = json.loads(read(tree / "docs/stages/approved.json"))
    problems, _ = cost_check.gate_problems(tree, approved)
    assert any("above approved" in p for p in problems), problems
    assert not any("twingate-connector module block" in p for p in problems), problems


def test_a_reserved_ip_entry_cannot_be_priced_yet(tree):
    manifest = tree / "stacks/50-edge/cost.json"
    manifest.write_text(json.dumps({"stage": 5, "resources": [{"name": "edge-ip", "kind": "reserved_ip", "assigned_to": "edge"}]}))
    approved = json.loads(read(tree / "docs/stages/approved.json"))
    with pytest.raises(ValueError, match="no price model for kind 'reserved_ip'"):
        cost_check.gate_problems(tree, approved)


def test_turning_the_switch_on_in_the_stack_is_refused_by_its_own_guard():
    outputs = strip_comments(read(STACK / "outputs.tf"))
    assert "!var.edge_enabled ||" in outputs
    assert 'r.kind == "reserved_ip"' in outputs and 'r.kind == "droplet"' in outputs


# --- edge-host module calls are held to the connector's rules -----------------

CALL = 'module "edge_host" {\n  source = "../../modules/edge-host"\n%s}\n'


def edge_tree(tree, body, entries=()):
    (tree / "stacks/50-edge/main.tf").write_text(CALL % body)
    (tree / "stacks/50-edge/cost.json").write_text(json.dumps({"stage": 5, "resources": list(entries)}))
    return cost_check.edge_module_problems(tree)[0]


GOOD_BODY = "  count = local.on\n  size  = local.edge_droplet.size\n"
DROP = {"name": "edge", "kind": "droplet", "size": "s-1vcpu-1gb", "backups": False}
RIP = {"name": "ip", "kind": "reserved_ip", "assigned_to": "edge"}


def test_a_conforming_call_passes(tree):
    assert edge_tree(tree, GOOD_BODY) == []
    assert edge_tree(tree, GOOD_BODY, [DROP, RIP]) == []


@pytest.mark.parametrize(
    "body",
    [
        "  count = 2\n  size = local.edge_droplet.size\n",
        "  count = var.n\n  size = local.edge_droplet.size\n",
        '  for_each = toset(["a"])\n  size = local.edge_droplet.size\n',
    ],
)
def test_count_other_than_the_switch_and_for_each_are_refused(tree, body):
    assert any("uses" in p for p in edge_tree(tree, body))


@pytest.mark.parametrize("size", ['"s-1vcpu-1gb"', "var.droplet_size", "lower(local.edge_droplet.size)"])
def test_a_size_that_is_not_a_plain_local_reference_is_refused(tree, size):
    assert any("plain reference" in p for p in edge_tree(tree, f"  count = local.on\n  size = {size}\n"))


def test_a_missing_size_is_refused(tree):
    assert any("plain reference" in p for p in edge_tree(tree, "  count = local.on\n"))


def test_manifest_entries_must_match_the_module_calls(tree):
    assert any("2 droplet" in p for p in edge_tree(tree, GOOD_BODY, [DROP, {**DROP, "name": "b"}]))
    assert any("2 reserved_ip" in p for p in edge_tree(tree, GOOD_BODY, [RIP, {**RIP, "name": "b"}]))
