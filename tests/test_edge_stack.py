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
    assert len(found) >= 4, "the scan lost its targets"
    for labels, body in found:
        assert re.search(r"(?m)^\s*count\s*=\s*local\.on\s*$", body), (
            f"{labels}: count = local.on is missing, so it would exist with the switch off"
        )
    assert re.search(r"(?m)^\s*on\s*=\s*var\.edge_enabled\s*\?\s*1\s*:\s*0\s*$", main)


def test_the_cost_manifest_prices_nothing_and_the_stage_is_not_approved():
    manifest = json.loads(read(STACK / "cost.json"))
    assert manifest["resources"] == []
    assert manifest["edge_network_approved"] is False
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


def test_i2pd_and_iperf3_are_closed_to_everyone_in_the_network_stack():
    # Both stay closed until their own stacks exist: no variable, no rule, no port.
    code = strip_comments(read(STACK / "main.tf") + read(STACK / "variables.tf") + read(STACK / "outputs.tf"))
    for needle in ("i2pd", "iperf3", "5201", "source_addresses = var."):
        assert needle not in code, needle
    assert 'source_addresses = ["0.0.0.0/0"]' in code
    # The module's restricted ports stay IPv4-only whenever a service stack uses them.
    module_vars = strip_comments(read(MODULE / "variables.tf"))
    ((_, body),) = [b for b in blocks(module_vars, "variable") if b[0] == ["restricted_ports"]]
    assert 'strcontains(s, ":")' in body and 's != "0.0.0.0/0"' in body


def test_no_edge_service_stack_exists_yet():
    # Each service is its own stack, built and approved later. Until then nothing
    # calls modules/edge-host, no service is installed and no droplet is declared.
    for path in (ROOT / "stacks").rglob("*.tf"):
        if ".terraform" in path.parts:
            continue
        code = strip_comments(read(path))
        assert "modules/edge-host" not in code, f"{path}: a service stack appeared"
        assert 'resource "digitalocean_droplet"' not in code, path


def test_the_module_attaches_droplet_and_reserved_ip_to_the_project():
    main = strip_comments(read(MODULE / "main.tf"))
    assert re.search(r'resource "digitalocean_project_resources" "edge"', main)
    assert "digitalocean_droplet.edge.urn" in main and "digitalocean_reserved_ip.edge.urn" in main
    assert "var.project_id" in main


def parse_slots():
    data = json.loads(read(MODULE / "reboot-slots.json"))
    return data["timezone"], data["slots"]


def minutes(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def test_reboot_slots_are_unique_staggered_and_clear_of_the_connectors():
    tz, slots = parse_slots()
    assert len(slots) == 5
    times = [minutes(v) for v in slots.values()]
    assert len(set(times)) == len(times), "two edge droplets share a reboot minute"
    assert all(60 <= t <= 180 for t in times), "slots are 01:00 to 03:00 Eastern"
    access = read(ROOT / "stacks/10-access/variables.tf")
    connectors = [minutes(m) for m in re.findall(r'(?m)^\s*[ab]\s*=\s*"(\d\d:\d\d)"', access)]
    assert sorted(connectors) == [240, 300], "the connectors' reboot defaults changed; revisit the slots"
    assert not set(times) & set(connectors)
    assert tz == "America/New_York"
    assert re.search(r'variable "timezone".*?default\s*=\s*"America/New_York"', access, re.DOTALL)
    module_vars = read(MODULE / "variables.tf")
    assert re.search(r'variable "timezone".*?default\s*=\s*"America/New_York"', module_vars, re.DOTALL)


def test_every_slot_service_has_its_own_doppler_config_name():
    _, slots = parse_slots()
    variables = read(MODULE / "variables.tf")
    listed = re.search(r'contains\(\[([^\]]*)\], var\.service\)', variables).group(1)
    assert sorted(re.findall(r'"([a-z0-9]+)"', listed)) == sorted(slots)
    main = read(MODULE / "main.tf")
    assert 'doppler_config = "cah-edge-${var.service}"' in main
    names = {f"cah-edge-{svc}" for svc in slots}
    assert len(names) == len(slots)


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


def test_the_cloud_init_installs_only_os_packages_and_no_service():
    template = read(MODULE / "cloud-init.yaml.tftpl")
    assert packages_section(template) == ["- unattended-upgrades", "- chrony", "- nftables"]
    variables = strip_comments(read(MODULE / "variables.tf"))
    assert "service_packages" not in variables and "service_packages" not in read(MODULE / "main.tf")
    for needle in ("rnsd", "lxmd", "i2pd", "mosquitto", "iperf3", "%{ for"):
        assert needle not in template, needle


SECRET_SHAPED = re.compile(r"token|secret|password|passwd|api[_-]?key|private[_-]?key|credential", re.IGNORECASE)
# The design allows exactly one secret-shaped field in user-data, a short-lived
# read-only Doppler token for the service's own config (risk 6). It arrives with
# each service stack, not with this module, so none today.
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
    # The Cloud Firewall is built from one list; a service stack passes the same
    # list to the module so the host firewall mirrors it (the module's tests).
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


def test_a_droplet_in_the_network_stack_is_refused(tree):
    # The shared network stack owns no droplet; one priced there has no connector
    # module block and no edge-host call to match.
    manifest = tree / "stacks/50-edge/cost.json"
    manifest.write_text(
        json.dumps({"stage": 5, "resources": [{"name": "edge", "kind": "droplet", "size": "s-1vcpu-1gb", "backups": False}]})
    )
    approved = json.loads(read(tree / "docs/stages/approved.json"))
    problems, _ = cost_check.gate_problems(tree, approved)
    assert any("stacks/50-edge" in p and "twingate-connector module block" in p for p in problems), problems


def test_a_reserved_ip_entry_cannot_be_priced_yet(tree):
    manifest = tree / "stacks/50-edge/cost.json"
    manifest.write_text(json.dumps({"stage": 5, "resources": [{"name": "edge-ip", "kind": "reserved_ip", "assigned_to": "edge"}]}))
    approved = json.loads(read(tree / "docs/stages/approved.json"))
    with pytest.raises(ValueError, match="no price model for kind 'reserved_ip'"):
        cost_check.gate_problems(tree, approved)


def test_turning_the_switch_on_is_refused_by_the_stacks_own_guard():
    outputs = strip_comments(read(STACK / "outputs.tf"))
    assert "!var.edge_enabled || try(local.cost.edge_network_approved, false) == true" in outputs


# --- edge-host module calls are held to the connector's rules -----------------

CALL = 'module "edge_host" {\n  source = "../../modules/edge-host"\n%s}\n'


SYN = "stacks/51-edge-example"
SYN_LOCALS = (
    "locals {\n  on = var.edge_enabled ? 1 : 0\n"
    '  cost = jsondecode(file("${path.module}/cost.json"))\n'
    "  edge_droplet = { size = var.droplet_size }\n}\n"
)
SYN_OUT = (
    'output "edge_enabled" {\n  value = var.edge_enabled\n  precondition {\n'
    "    condition = !var.edge_enabled || (\n"
    '      length([for r in local.cost.resources : r if r.kind == "droplet"]) == 1 &&\n'
    '      length([for r in local.cost.resources : r if r.kind == "reserved_ip"]) == 1\n    )\n'
    '    error_message = "price it"\n  }\n}\n'
)


def syn_stack(tree, body="__good__", entries=(), main=None, outputs=None):
    """A stand-in service stack (none exists yet) that calls modules/edge-host."""
    d = tree / SYN
    d.mkdir(exist_ok=True)
    body = GOOD_BODY if body == "__good__" else body
    (d / "main.tf").write_text(main if main is not None else SYN_LOCALS + CALL % body)
    (d / "outputs.tf").write_text(outputs if outputs is not None else SYN_OUT)
    (d / "cost.json").write_text(json.dumps({"stage": 5, "resources": list(entries)}))


def edge_tree(tree, body, entries=()):
    syn_stack(tree, body, entries)
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


# --- zero manifest entries need a verified switch; other droplets still count --


def test_the_stand_in_stack_has_a_verified_switch(tree):
    syn_stack(tree)
    assert cost_check.edge_switch_verified(tree, SYN)
    assert cost_check.edge_module_problems(tree)[0] == []


def test_zero_entries_are_refused_when_the_call_has_no_switch(tree):
    syn_stack(tree, body="  size = local.edge_droplet.size\n")
    assert any("0 droplet" in p for p in cost_check.edge_module_problems(tree)[0])


def test_zero_entries_are_refused_when_the_switch_is_not_a_variable_ternary(tree):
    syn_stack(tree, main=(SYN_LOCALS + CALL % GOOD_BODY).replace("on = var.edge_enabled ? 1 : 0", "on = 0"))
    assert any("0 droplet" in p for p in cost_check.edge_module_problems(tree)[0])


def test_zero_entries_are_refused_when_the_precondition_is_gone(tree):
    syn_stack(tree, outputs=SYN_OUT.replace("!var.edge_enabled ||", "true ||"))
    assert any("0 droplet" in p for p in cost_check.edge_module_problems(tree)[0])


def test_a_non_edge_droplet_in_a_service_manifest_is_still_counted(tree):
    # One droplet is the service's and is subtracted; the second has no connector
    # module block, so the connector reconciliation still reports it.
    syn_stack(tree, entries=[DROP, {**DROP, "name": "stray"}, RIP])
    problems = cost_check.structure_problems(tree)
    assert any(f"{SYN}: 0 twingate-connector module block(s) but 1 machine" in p for p in problems), problems
