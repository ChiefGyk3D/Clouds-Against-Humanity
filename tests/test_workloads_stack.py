"""Guards on the stage 3 workload stack, issue #111.

The stack ships DISABLED and UNAPPLIED: stage 3 is not approved. These tests
keep it that way on purpose and keep its network shape narrow: every block is
behind the switch, the switch defaults to off, the stack is not registered
anywhere that could apply it, the cost manifest prices nothing, the firewall
admits only the connector tag, nothing is published on a wildcard address, and
the Docker API never gets a network socket. Turning the stack on is a deliberate
change that has to edit the tests below in the same reviewed diff.

The checks are functions over text, each with a negative case, so a check that
stops biting fails here.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STACK = ROOT / "stacks/30-workloads"
MODULE = ROOT / "modules/docker-host"

WILDCARDS = ("0.0.0.0", "[::]", '"::"', "::/0", "network_mode: host", "network_mode: \"host\"")


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


# --- checks over text ----------------------------------------------------------


def unswitched(text):
    """Labels of every resource, data and module block without count = local.on."""
    found = blocks(text, "resource") + blocks(text, "data") + blocks(text, "module")
    return [
        labels
        for labels, body in found
        if not re.search(r"(?m)^\s*count\s*=\s*local\.on\s*$", body)
    ]


def firewall_problems(text):
    """Everything in the stack source that could admit more than the connector tag."""
    text = strip_comments(text)
    problems = []
    for needle in (
        "source_addresses",
        "source_droplet_ids",
        "source_load_balancer_uids",
        "source_kubernetes_ids",
        "inbound_from_tag_rules",
        "extra_outbound_rules",
        "outbound_to_tag_rules",
        "outbound_to_other_tags",
    ):
        if needle in text:
            problems.append(f"uses {needle}")
    if "0.0.0.0" in text or "::/0" in text:
        problems.append("names a world address")
    rules = re.findall(r"\{\s*protocol\s*=\s*\"(\w+)\",\s*port_range\s*=\s*([^,]+),\s*tag\s*=\s*([^}\s]+)\s*\}", text)
    if len(rules) != 2:
        problems.append(f"expected two inbound rules, found {len(rules)}")
    for protocol, port, tag in rules:
        if protocol != "tcp":
            problems.append(f"non-tcp inbound rule {protocol}")
        if tag != "var.connector_tag":
            problems.append(f"inbound source is {tag}, not var.connector_tag")
        if port not in ("local.ssh_port", "tostring(local.portainer_port)"):
            problems.append(f"inbound port {port} is neither SSH nor Portainer")
    return problems


def wildcard_problems(text):
    """Wildcard binds and host networking in a cloud-init template or compose text."""
    found = [w for w in WILDCARDS if w in text]
    # A published port needs an address in front of it.
    found += re.findall(r"(?m)^\s+- \"?\d+:\d+\"?\s*$", text)
    return found


def docker_api_problems(text):
    """Any way of giving the Docker daemon a network socket."""
    return [w for w in ('"hosts"', "tcp://", "2375", "2376", "-H tcp", "--host=tcp") if w in text]


# --- the stack ------------------------------------------------------------------


def test_the_switch_defaults_to_off():
    variables = strip_comments(read(STACK / "variables.tf"))
    (_, body), = [b for b in blocks(variables, "variable") if b[0] == ["workload_enabled"]]
    assert re.search(r"(?m)^\s*default\s*=\s*false\s*$", body)
    assert re.search(r"(?m)^\s*nullable\s*=\s*false\s*$", body)


def test_every_block_of_the_stack_is_behind_the_switch():
    main = strip_comments(read(STACK / "main.tf"))
    found = blocks(main, "resource") + blocks(main, "data") + blocks(main, "module")
    assert len(found) >= 7, "the scan lost its targets"
    assert unswitched(main) == []
    assert re.search(r"(?m)^\s*on\s*=\s*var\.workload_enabled\s*\?\s*1\s*:\s*0\s*$", main)


def test_the_switch_check_bites():
    bad = 'resource "digitalocean_tag" "x" {\n  name = "x"\n}\n'
    assert unswitched(bad) == [["digitalocean_tag", "x"]]


def test_the_cost_manifest_prices_nothing_and_the_stage_is_not_approved():
    manifest = json.loads(read(STACK / "cost.json"))
    assert manifest["resources"] == []
    assert manifest["workload_approved"] is False
    assert manifest["planned"]["workload"]["kind"] == "droplet"
    assert manifest["planned"]["workload"]["backups"] is False
    approved = json.loads(read(ROOT / "docs/stages/approved.json"))
    # Stage 3 is the current phase (maintainer approval 2026-10-31), but the
    # stack stays off: the DigitalOcean total is not raised to cover the droplet
    # until the switching-on pull request, which sets workload_approved.
    assert approved["current_phase"] == "stage-3"
    total = approved["providers"]["digitalocean"]["approved_monthly_total"]
    assert total == 12.0  # the two connectors only; the switching-on PR raises it to 24 (29 with the bucket)


def test_the_planned_size_is_priced_in_the_price_table():
    manifest = json.loads(read(STACK / "cost.json"))
    prices = json.loads(read(ROOT / "docs/cost-prices.json"))
    assert manifest["planned"]["workload"]["size"] in prices["droplets"]


def test_the_stack_is_not_registered_for_a_spacelift_apply():
    # A stanza in .spacelift/config.yml is what lets a stack load secrets and
    # apply. It is added in the pull request that approves the stage.
    config = read(ROOT / ".spacelift/config.yml")
    assert "30-workloads" not in config


def test_the_firewall_admits_the_connector_tag_on_two_ports_and_nothing_else():
    assert firewall_problems(read(STACK / "main.tf")) == []


def test_the_firewall_check_bites():
    good = read(STACK / "main.tf")
    for bad in (
        good.replace("tag = var.connector_tag }", "tag = var.baseline_tag }", 1),
        good.replace('protocol = "tcp", port_range = local.ssh_port', 'protocol = "tcp", source_addresses = ["0.0.0.0/0"], port_range = local.ssh_port', 1),
        good + "\n# extra\nmodule \"x\" {\n  inbound_from_tag_rules = []\n}\n",
        good.replace("tostring(local.portainer_port)", '"2375"', 1),
    ):
        assert firewall_problems(bad), "a widened firewall was not noticed"


EXPECTED_TWINGATE = [
    ["twingate_resource", "portainer"],
    ["twingate_resource", "ssh"],
    ["twingate_resource", "workload_web"],
]
# A rule that opens the Docker API ports or every port.
OPEN_PORT_RE = re.compile(r'2375|2376|ALLOW_ALL|\b[01]\s*-\s*65535|"all"|"\*"', re.IGNORECASE)


def stack_texts():
    """{file name: comment-free text} of every .tf file in the stack directory."""
    return {
        path.name: strip_comments(read(path))
        for path in sorted(STACK.glob("*.tf"))
        if ".terraform" not in path.parts
    }


def twingate_problems(texts):
    """Every Twingate resource of every file: the set must be the expected one,
    each narrow (TCP restricted, UDP denied, no ICMP), and no file may name the
    Docker API ports or an all-ports rule."""
    problems = []
    found = []
    for name, text in texts.items():
        for labels, body in blocks(text, "resource"):
            if labels[0] == "twingate_resource":
                found.append(labels)
                for needle in (r'policy\s*=\s*"RESTRICTED"', r'udp\s*=\s*\{\s*policy\s*=\s*"DENY_ALL"', r"allow_icmp\s*=\s*false"):
                    if not re.search(needle, body):
                        problems.append(f"{name}: {labels[1]} lacks {needle}")
        if OPEN_PORT_RE.search(text):
            problems.append(f"{name}: names a Docker API port or an all-ports rule")
    if sorted(found) != EXPECTED_TWINGATE:
        problems.append(f"Twingate resources are {sorted(found)}, expected {EXPECTED_TWINGATE}")
    return problems


def test_the_twingate_resources_of_every_file_are_the_expected_narrow_three():
    texts = stack_texts()
    assert {"main.tf", "workload_web.tf", "variables.tf", "outputs.tf"} <= set(texts), "the scan lost its files"
    assert twingate_problems(texts) == []


def test_the_twingate_check_sees_a_resource_in_any_file_and_open_ports():
    texts = stack_texts()
    extra = 'resource "twingate_resource" "extra" {\n  protocols = {}\n}\n'
    assert twingate_problems({**texts, "another.tf": extra})
    assert twingate_problems({**texts, "main.tf": texts["main.tf"] + extra})
    web = texts["workload_web.tf"]
    for bad in (
        web.replace('policy = "RESTRICTED"', 'policy = "ALLOW_ALL"', 1),
        web.replace("ports  = [each.key]", 'ports  = ["2375"]', 1),
        web.replace("ports  = [each.key]", 'ports  = ["2376"]', 1),
        web.replace("ports  = [each.key]", 'ports  = ["1-65535"]', 1),
        web.replace("ports  = [each.key]", 'ports  = ["0-65535"]', 1),
        web.replace("allow_icmp = false", "allow_icmp = true", 1),
    ):
        assert twingate_problems({**texts, "workload_web.tf": bad}), bad[-200:]
    assert twingate_problems({k: v for k, v in texts.items() if k != "workload_web.tf"})


def test_the_stack_has_no_wildcard_anywhere():
    for path in (STACK / "main.tf", STACK / "variables.tf", STACK / "outputs.tf"):
        assert wildcard_problems(strip_comments(read(path))) == [], path.name


# --- the module -----------------------------------------------------------------


def test_the_cloud_init_publishes_nothing_on_a_wildcard_and_has_no_docker_api_socket():
    template = read(MODULE / "cloud-init.yaml.tftpl")
    assert "portainer/portainer-ce:" in template, "the scan lost its target"
    assert wildcard_problems(template) == []
    assert docker_api_problems(template) == []


def test_the_wildcard_and_docker_api_checks_bite():
    assert wildcard_problems('ports:\n  - "9443:9443"\n')
    assert wildcard_problems('ports:\n  - "0.0.0.0:9443:9443"\n')
    assert wildcard_problems("network_mode: host\n")
    assert wildcard_problems('bind = "[::]:22"\n')
    assert docker_api_problems('{"hosts": ["tcp://0.0.0.0:2375"]}')
    assert not wildcard_problems('ports:\n  - "${PORTAINER_BIND:?}:9443:9443"\n')


def test_the_module_pins_portainer_and_never_pipes_an_installer():
    template = read(MODULE / "cloud-init.yaml.tftpl")
    assert "portainer-ce:latest" not in template
    assert "get.docker.com" not in template
    assert not re.search(r"curl[^\n]*\|\s*(ba)?sh", template)
    assert "cah-apt-key-check /root/docker.gpg.key" in template


PINNED_PORTAINER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+@sha256:[0-9a-f]{64}$")


def portainer_pin_problems(variables):
    """The portainer_version default and validation must both demand tag plus digest."""
    found = [b for b in blocks(strip_comments(variables), "variable") if b[0] == ["portainer_version"]]
    if len(found) != 1:
        return ["portainer_version variable missing"]
    body = found[0][1]
    problems = []
    default = re.search(r'(?m)^\s*default\s*=\s*"([^"]*)"\s*$', body)
    if not default or not PINNED_PORTAINER_RE.match(default.group(1)):
        problems.append("the default is not <version>@sha256:<64 hex>")
    if "@sha256:[0-9a-f]{64}$" not in body:
        problems.append("the validation does not demand a digest")
    return problems


def test_portainer_is_pinned_by_tag_and_digest_in_the_module_and_the_stack():
    for path in (MODULE / "variables.tf", STACK / "variables.tf"):
        assert portainer_pin_problems(read(path)) == [], path.as_posix()


def test_the_portainer_pin_check_bites():
    good = read(MODULE / "variables.tf")
    tag_only = good.replace("@sha256:3609c307943bca8e5c492f69ddd6965df177208b50678a4cff28391c8dd4e96e", "", 1)
    assert portainer_pin_problems(tag_only)
    assert portainer_pin_problems(good.replace("@sha256:[0-9a-f]{64}$", "$", 1))


def test_the_module_droplet_leaves_backups_off_and_has_no_public_v6():
    main = strip_comments(read(MODULE / "main.tf"))
    ((_, body),) = blocks(main, "resource")
    assert re.search(r"(?m)^\s*backups\s*=\s*false\s*$", body)
    assert re.search(r"(?m)^\s*ipv6\s*=\s*false\s*$", body)
    assert "backup_policy" not in body


def test_only_the_workloads_stack_calls_the_module():
    callers = []
    for tf in sorted((ROOT / "stacks").rglob("*.tf")):
        if ".terraform" in tf.parts:
            continue
        if re.search(r'source\s*=\s*"(\.\./)+modules/docker-host"', read(tf)):
            callers.append(tf.relative_to(ROOT).as_posix())
    assert callers == ["stacks/30-workloads/main.tf"]


# --- the optional workload web ports (issue #437) ---------------------------------


def web_port_problems(variables, web):
    """Guards on the web port list: default empty, switch-gated, connector tag only."""
    problems = []
    variables = strip_comments(variables)
    web = strip_comments(web)
    found = [b for b in blocks(variables, "variable") if b[0] == ["workload_web_ports"]]
    if len(found) != 1:
        return ["workload_web_ports variable missing"]
    body = found[0][1]
    if not re.search(r"(?m)^\s*default\s*=\s*\[\]\s*$", body):
        problems.append("the port list does not default to empty")
    if not re.search(r"(?m)^\s*nullable\s*=\s*false\s*$", body):
        problems.append("the port list is nullable")
    resources = [b for b in blocks(web, "resource") if b[0][0] == "twingate_resource"]
    if len(resources) != 1:
        problems.append(f"expected one web Twingate resource, found {len(resources)}")
    for _, rbody in resources:
        if not re.search(r"for_each\s*=\s*local\.workload_web_ports\b", rbody):
            problems.append("the web resource is not driven by local.workload_web_ports")
        for needle in (r'policy\s*=\s*"RESTRICTED"', r'udp\s*=\s*\{\s*policy\s*=\s*"DENY_ALL"', r"allow_icmp\s*=\s*false", r"module\.workload\[0\]\.private_ip"):
            if not re.search(needle, rbody):
                problems.append(f"web resource lacks {needle}")
    if not re.search(r"workload_web_ports\s*=\s*var\.workload_enabled\s*\?", web):
        problems.append("the port map is not gated by the master switch")
    for needle in ("source_addresses", "0.0.0.0", "::/0", "inbound_from_tag_rules"):
        if needle in web:
            problems.append(f"uses {needle}")
    rules = re.findall(r"\{\s*protocol\s*=\s*\"(\w+)\",\s*port_range\s*=\s*([^,]+),\s*tag\s*=\s*([^}\s]+)\s*\}", web)
    if len(rules) != 1:
        problems.append(f"expected one rule template, found {len(rules)}")
    for protocol, port, tag in rules:
        if protocol != "tcp" or tag != "var.connector_tag" or port != "tostring(p)":
            problems.append(f"rule {protocol}/{port}/{tag} is not tcp from the connector tag on a listed port")
    return problems


def test_the_web_ports_are_default_empty_switch_gated_and_connector_tag_only():
    variables = read(STACK / "variables.tf")
    web = read(STACK / "workload_web.tf")
    assert web_port_problems(variables, web) == []
    main = strip_comments(read(STACK / "main.tf"))
    assert "concat(" in main and "local.workload_web_firewall_rules" in main


def test_the_web_port_check_bites():
    variables = read(STACK / "variables.tf")
    web = read(STACK / "workload_web.tf")
    for bad_vars, bad_web in (
        (variables.replace("default     = []", "default     = [8080]", 1), web),
        (variables, web.replace("tag = var.connector_tag", "tag = var.baseline_tag", 1)),
        (variables, web.replace('port_range = tostring(p)', 'port_range = "1-65535"', 1)),
        (variables, web.replace("var.workload_enabled ?", "true ?", 1)),
        (variables, web.replace('policy = "DENY_ALL"', 'policy = "ALLOW_ALL"', 1)),
        (variables, web + "\n# x\nresource \"twingate_resource\" \"extra\" {\n  for_each = local.workload_web_ports\n}\n"),
        (variables, web.replace("module.workload[0].private_ip", '"0.0.0.0"', 1)),
    ):
        assert web_port_problems(bad_vars, bad_web), "a widened web port setup was not noticed"
