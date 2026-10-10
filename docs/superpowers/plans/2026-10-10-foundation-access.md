# Foundation and Access (Stages 0-1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the cost gate, the OpenTofu modules and the two Spacelift-managed stacks (foundation, access) that put one Twingate connector in a deny-all DigitalOcean VPC.

**Architecture:** Layered stacks (`00-foundation`, `10-access`) composed from small modules. Every stack takes `region` as a variable. Costs are declared in a per-stack `cost.json` manifest, which is the single source the droplet size is read from, and a stdlib Python script totals the manifests against an approved stage total. CI is thin GYST callers plus one local `tofu test` job.

**Tech Stack:** OpenTofu 1.12.x (`tofu test` with `mock_provider`), providers `digitalocean/digitalocean` and `twingate/twingate`, Spacelift (state and runs), Doppler (secrets), Python 3.12+ stdlib and pytest (cost script), GitHub Actions via git-your-ship-together (GYST).

**Spec:** `docs/superpowers/specs/2026-10-10-foundation-access-design.md`

## Global Constraints

- OpenTofu, not Terraform. Nothing applies from CI; Spacelift plans and applies.
- Working ceiling $30/month for stages 0-4; stage 1 approved total is $6.00.
- Every stack and module takes `region` as a variable. Names follow `<layer>-<region>-<role>`. VPCs are per region.
- Default deny: the baseline firewall has zero inbound rules. No public SSH. Droplets are created with the baseline tag already set.
- No secrets, tenant IDs, hostnames, machine serials, callsign or grid, employer name, or raw corpus data in any file, commit or doc.
- Secrets come from Doppler. No user-scoped PAT anywhere.
- CI calls GYST reusable workflows pinned by commit with a `# vX.Y.Z` comment; the gate job is named `CI green`.
- Commits end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` and use the personal noreply identity `19499446+ChiefGyk3D@users.noreply.github.com`.
- AI routing: local model (`llm-local`) first for doc drafts and digests; code does counting and cost math; Codex only at the stage-gate security review (Plus plan, spend sparingly); Copilot credits are limited (20K/month, about 9K already used), so no Copilot-driven steps in this plan; Opus or Mythos only with explicit approval.

## Review Focus

1. A droplet is created before the firewall covers it. Expected: the tag is set at creation (Task 5 test) and the baseline firewall has zero inbound rules (Task 3 test).
2. A droplet size with no price entry. Expected: the cost check fails closed, never treats it as free (Task 1 test).
3. Backups requested while the price fraction is unverified. Expected: the cost check refuses (Task 1 test).
4. A costed resource (droplet, volume, load balancer, cluster) added outside the allowed file, so it escapes the manifest. Expected: the cost check fails and names the file (Task 1 test).
5. A VPC range that is public or malformed. Expected: plan fails validation (Task 2 test).
6. The Twingate connector tokens leaking through an output. Expected: no output exposes them (Task 5 test).

## File Structure

```
Clouds-Against-Humanity/
  scripts/cost_check.py                    cost gate (Task 1)
  tests/test_cost_check.py                 pytest for the gate (Task 1)
  docs/cost-prices.json                    price table from the DO sizes API (Task 1)
  docs/stages/approved.json                approved totals + allowed sources (Task 1)
  modules/vpc/                             per-region VPC (Task 2)
  modules/firewall/                        tag-based deny-inbound firewall (Task 3)
  modules/twingate-connector/              remote network, connector, droplet (Task 5)
  stacks/00-foundation/                    project, tag, VPC, baseline firewall (Task 4)
  stacks/10-access/                        connector, connector firewall, group, SSH resource (Task 6)
  .github/workflows/ci.yml                 GYST callers + tofu-test + CI green (Task 7)
  docs/stages/00-foundation.md, 01-access.md, cost.md   guides (Task 8)
```

Each module folder holds `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` and `tests/*.tftest.hcl`. Run module tests with `tofu -chdir=modules/<name> init -backend=false && tofu -chdir=modules/<name> test`.

---

### Task 1: Cost gate (script, price table, approved totals)

**Files:**
- Create: `scripts/cost_check.py`
- Create: `tests/test_cost_check.py`
- Create: `docs/cost-prices.json`
- Create: `docs/stages/approved.json`
- Create: `stacks/00-foundation/cost.json`
- Create: `stacks/10-access/cost.json`
- Create: `.gitignore`

**Interfaces:**
- Produces: `cost_check.total_cost(root, prices) -> float`, `cost_check.resource_cost(res, prices) -> float` (raises `ValueError`), `cost_check.uncosted_sources(root, allowed) -> list[str]`, `cost_check.main(argv) -> int` (0 pass, 1 fail). Manifest shape `{"stage": int, "resources": [{"name": str, "kind": "droplet", "size": str, "backups": bool}]}`.

- [ ] **Step 1: Write the data files**

`.gitignore`:
```
.terraform/
*.tfstate
*.tfstate.*
crash.log
*.tfvars
!*.tftest.hcl
__pycache__/
.pytest_cache/
```

`docs/cost-prices.json` (list prices returned by the DO sizes API on 2026-10-10; backups fraction is NOT verified):
```json
{
  "retrieved": "2026-10-10",
  "source": "DigitalOcean sizes API, regular (non-s5) droplets",
  "backups_fraction": 0.2,
  "backups_fraction_verified": false,
  "droplets": {
    "s-1vcpu-512mb-10gb": 4,
    "s-1vcpu-1gb": 6,
    "s-1vcpu-1gb-intel": 7,
    "s-1vcpu-2gb": 12,
    "s-2vcpu-2gb": 18,
    "s-2vcpu-4gb": 24,
    "s-4vcpu-8gb": 48
  }
}
```

`docs/stages/approved.json`:
```json
{
  "stage": 1,
  "approved_monthly_total": 6.0,
  "ceiling": 30.0,
  "allowed_sources": {
    "digitalocean_droplet": ["modules/twingate-connector/main.tf"]
  }
}
```

`stacks/00-foundation/cost.json`:
```json
{ "stage": 0, "resources": [] }
```

`stacks/10-access/cost.json`:
```json
{
  "stage": 1,
  "resources": [
    { "name": "connector", "kind": "droplet", "size": "s-1vcpu-1gb", "backups": false }
  ]
}
```

- [ ] **Step 2: Write the failing tests**

`tests/test_cost_check.py`:
```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cost_check  # noqa: E402

PRICES = {
    "backups_fraction": 0.2,
    "backups_fraction_verified": False,
    "droplets": {"s-1vcpu-1gb": 6, "s-1vcpu-2gb": 12},
}


def make_repo(tmp_path, resources, approved_total=6.0, tf_files=None, ceiling=30.0, prices=None):
    (tmp_path / "docs/stages").mkdir(parents=True)
    (tmp_path / "stacks/10-access").mkdir(parents=True)
    (tmp_path / "docs/cost-prices.json").write_text(json.dumps(prices or PRICES))
    (tmp_path / "docs/stages/approved.json").write_text(json.dumps({
        "approved_monthly_total": approved_total,
        "ceiling": ceiling,
        "allowed_sources": {"digitalocean_droplet": ["modules/ok/main.tf"]},
    }))
    (tmp_path / "stacks/10-access/cost.json").write_text(
        json.dumps({"stage": 1, "resources": resources}))
    for rel, text in (tf_files or {}).items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return tmp_path


def droplet(size="s-1vcpu-1gb", backups=False):
    return {"name": "connector", "kind": "droplet", "size": size, "backups": backups}


def test_total_sums_manifests(tmp_path):
    root = make_repo(tmp_path, [droplet(), droplet("s-1vcpu-2gb")], approved_total=18)
    assert cost_check.total_cost(root, PRICES) == 18.0


def test_unknown_size_fails_closed(tmp_path):
    root = make_repo(tmp_path, [droplet("s-99vcpu-1tb")])
    with pytest.raises(ValueError, match="no price for size"):
        cost_check.total_cost(root, PRICES)


def test_backups_refused_while_fraction_unverified(tmp_path):
    root = make_repo(tmp_path, [droplet(backups=True)])
    with pytest.raises(ValueError, match="unverified"):
        cost_check.total_cost(root, PRICES)


def test_backups_priced_once_verified(tmp_path):
    prices = {**PRICES, "backups_fraction_verified": True}
    root = make_repo(tmp_path, [droplet(backups=True)], prices=prices)
    assert cost_check.total_cost(root, prices) == 7.2


def test_non_droplet_kind_has_no_price_model(tmp_path):
    root = make_repo(tmp_path, [{"name": "lb", "kind": "loadbalancer"}])
    with pytest.raises(ValueError, match="no price model"):
        cost_check.total_cost(root, PRICES)


def test_costed_resource_outside_allowed_file_is_flagged(tmp_path):
    root = make_repo(tmp_path, [droplet()], tf_files={
        "modules/ok/main.tf": 'resource "digitalocean_droplet" "a" {}\n',
        "stacks/10-access/sneaky.tf": 'resource "digitalocean_volume" "v" {}\n',
    })
    found = cost_check.uncosted_sources(root, {"digitalocean_droplet": ["modules/ok/main.tf"]})
    assert found == ["stacks/10-access/sneaky.tf: digitalocean_volume"]


def test_provider_cache_directories_are_ignored(tmp_path):
    root = make_repo(tmp_path, [droplet()], tf_files={
        "stacks/10-access/.terraform/x.tf": 'resource "digitalocean_droplet" "a" {}\n',
    })
    assert cost_check.uncosted_sources(root, {}) == []


def test_main_passes_at_approved_total(tmp_path, capsys):
    root = make_repo(tmp_path, [droplet()], tf_files={
        "modules/ok/main.tf": 'resource "digitalocean_droplet" "a" {}\n'})
    assert cost_check.main(["--root", str(root)]) == 0
    assert "planned $6.00/mo" in capsys.readouterr().out


def test_main_fails_over_approved_total(tmp_path):
    root = make_repo(tmp_path, [droplet("s-1vcpu-2gb")], approved_total=6.0)
    assert cost_check.main(["--root", str(root)]) == 1


def test_main_fails_when_approval_exceeds_ceiling(tmp_path):
    root = make_repo(tmp_path, [droplet()], approved_total=40.0, ceiling=30.0)
    assert cost_check.main(["--root", str(root)]) == 1


def test_main_reports_value_errors_as_failure(tmp_path):
    root = make_repo(tmp_path, [droplet("s-99vcpu-1tb")])
    assert cost_check.main(["--root", str(root)]) == 1
```

- [ ] **Step 3: Run the tests and confirm they fail**

Run: `cd /home/chiefgyk3d/src/Clouds-Against-Humanity && python3 -I -m pytest tests -q 2>&1 | tail -5`
Expected: collection error `ModuleNotFoundError: No module named 'cost_check'`.

- [ ] **Step 4: Write the implementation**

`scripts/cost_check.py`:
```python
#!/usr/bin/env python3
"""Monthly cost gate for Clouds Against Humanity.

Totals every stacks/*/cost.json manifest against docs/cost-prices.json and
fails when the total is above docs/stages/approved.json, when a size has no
price, when backups are priced from an unverified fraction, or when a costed
resource type appears in HCL outside the allowed files.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

COSTED_TYPES = (
    "digitalocean_droplet",
    "digitalocean_volume",
    "digitalocean_loadbalancer",
    "digitalocean_kubernetes_cluster",
    "digitalocean_database_cluster",
    "digitalocean_reserved_ip",
    "digitalocean_floating_ip",
    "digitalocean_spaces_bucket",
)
RESOURCE_RE = re.compile(r'^\s*resource\s+"(?P<type>[a-z0-9_]+)"', re.MULTILINE)


def load_json(path):
    return json.loads(Path(path).read_text())


def resource_cost(res, prices):
    if res.get("kind") != "droplet":
        raise ValueError(f"no price model for kind {res.get('kind')!r} ({res.get('name')})")
    size = res["size"]
    table = prices["droplets"]
    if size not in table:
        raise ValueError(f"no price for size {size!r} ({res['name']})")
    cost = float(table[size])
    if res.get("backups"):
        if not prices.get("backups_fraction_verified"):
            raise ValueError("backups requested but the backup price fraction is unverified")
        cost += cost * float(prices["backups_fraction"])
    return cost


def total_cost(root, prices):
    total = 0.0
    for manifest in sorted(Path(root, "stacks").glob("*/cost.json")):
        for res in load_json(manifest)["resources"]:
            total += resource_cost(res, prices)
    return round(total, 2)


def uncosted_sources(root, allowed):
    root = Path(root)
    found = []
    for tf in sorted(root.rglob("*.tf")):
        rel = tf.relative_to(root).as_posix()
        if ".terraform" in tf.relative_to(root).parts:
            continue
        for match in RESOURCE_RE.finditer(tf.read_text()):
            kind = match.group("type")
            if kind in COSTED_TYPES and rel not in allowed.get(kind, []):
                found.append(f"{rel}: {kind}")
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    root = Path(parser.parse_args(argv).root)
    prices = load_json(root / "docs/cost-prices.json")
    approved = load_json(root / "docs/stages/approved.json")
    try:
        total = total_cost(root, prices)
    except ValueError as err:
        print(f"cost-check: {err}", file=sys.stderr)
        return 1
    problems = [f"costed resource outside allowed files: {item}"
                for item in uncosted_sources(root, approved.get("allowed_sources", {}))]
    if approved["approved_monthly_total"] > approved["ceiling"]:
        problems.append("approved total is above the ceiling")
    if total > approved["approved_monthly_total"]:
        problems.append(f"planned ${total:.2f} is above approved ${approved['approved_monthly_total']:.2f}")
    print(f"cost-check: planned ${total:.2f}/mo, approved ${approved['approved_monthly_total']:.2f}, "
          f"ceiling ${approved['ceiling']:.2f}")
    for problem in problems:
        print(f"cost-check: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the tests and confirm they pass**

Run: `cd /home/chiefgyk3d/src/Clouds-Against-Humanity && python3 -I -m pytest tests -q 2>&1 | tail -3`
Expected: `11 passed`.

- [ ] **Step 6: Commit**

```bash
cd /home/chiefgyk3d/src/Clouds-Against-Humanity
git add .gitignore scripts tests docs/cost-prices.json docs/stages/approved.json stacks
git -c user.name=ChiefGyk3D -c user.email=19499446+ChiefGyk3D@users.noreply.github.com commit -m "feat: cost gate with price table and stage approval" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: VPC module

**Files:**
- Create: `modules/vpc/versions.tf`, `modules/vpc/variables.tf`, `modules/vpc/main.tf`, `modules/vpc/outputs.tf`
- Test: `modules/vpc/tests/vpc.tftest.hcl`

**Interfaces:**
- Produces: module inputs `layer` (string), `region` (string), `ip_range` (private IPv4 CIDR); outputs `id` (VPC id), `ip_range`, `name`.

- [ ] **Step 1: Write the failing test**

`modules/vpc/tests/vpc.tftest.hcl`:
```hcl
mock_provider "digitalocean" {}

variables {
  layer    = "foundation"
  region   = "nyc3"
  ip_range = "10.77.0.0/24"
}

run "name_follows_layer_region_role" {
  command = plan
  assert {
    condition     = digitalocean_vpc.this.name == "foundation-nyc3-vpc"
    error_message = "VPC name must be <layer>-<region>-vpc."
  }
  assert {
    condition     = digitalocean_vpc.this.region == "nyc3"
    error_message = "VPC must be created in the requested region."
  }
}

run "rejects_public_range" {
  command = plan
  variables {
    ip_range = "8.8.8.0/24"
  }
  expect_failures = [var.ip_range]
}

run "rejects_malformed_range" {
  command = plan
  variables {
    ip_range = "not-a-cidr"
  }
  expect_failures = [var.ip_range]
}
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `tofu -chdir=modules/vpc init -backend=false -input=false && tofu -chdir=modules/vpc test`
Expected: FAIL (no configuration files / unsupported attribute), because the module does not exist yet.

- [ ] **Step 3: Write the module**

`modules/vpc/versions.tf`:
```hcl
terraform {
  required_version = ">= 1.8"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}
```

`modules/vpc/variables.tf`:
```hcl
variable "layer" {
  type        = string
  description = "Stack layer, used in names (for example foundation)."
}

variable "region" {
  type        = string
  description = "DigitalOcean region slug."
}

variable "ip_range" {
  type        = string
  description = "Private IPv4 CIDR for the VPC."
  validation {
    condition     = can(cidrnetmask(var.ip_range)) && can(regex("^(10\\.|172\\.(1[6-9]|2[0-9]|3[01])\\.|192\\.168\\.)", var.ip_range))
    error_message = "ip_range must be a private IPv4 CIDR (10/8, 172.16/12 or 192.168/16)."
  }
}
```

`modules/vpc/main.tf`:
```hcl
resource "digitalocean_vpc" "this" {
  name     = "${var.layer}-${var.region}-vpc"
  region   = var.region
  ip_range = var.ip_range
}
```

`modules/vpc/outputs.tf`:
```hcl
output "id" {
  value = digitalocean_vpc.this.id
}

output "ip_range" {
  value = digitalocean_vpc.this.ip_range
}

output "name" {
  value = digitalocean_vpc.this.name
}
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `tofu -chdir=modules/vpc test`
Expected: `3 passed, 0 failed`. If `init` reports a provider version problem, fix the constraint in `versions.tf` to the version `init` resolves, and re-run.

- [ ] **Step 5: Commit**

```bash
cd /home/chiefgyk3d/src/Clouds-Against-Humanity
git add modules/vpc .terraform.lock.hcl 2>/dev/null; git add modules/vpc
git -c user.name=ChiefGyk3D -c user.email=19499446+ChiefGyk3D@users.noreply.github.com commit -m "feat: per-region VPC module" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Deny-inbound firewall module

**Files:**
- Create: `modules/firewall/versions.tf`, `modules/firewall/variables.tf`, `modules/firewall/main.tf`, `modules/firewall/outputs.tf`
- Test: `modules/firewall/tests/firewall.tftest.hcl`

**Interfaces:**
- Produces: inputs `layer`, `region`, `purpose` (strings), `tag` (string), `extra_outbound_rules` (list of `{protocol, port_range}`, default `[]`); outputs `name`, `inbound_rule_count` (number), `outbound_rule_count` (number).
- Behavior: no `inbound_rule` block at all. Default outbound is TCP 443, TCP 80, TCP 53, UDP 53, UDP 123 to any address. Extra rules are appended.

- [ ] **Step 1: Write the failing test**

`modules/firewall/tests/firewall.tftest.hcl`:
```hcl
mock_provider "digitalocean" {}

variables {
  layer   = "foundation"
  region  = "nyc3"
  purpose = "baseline"
  tag     = "cah-baseline-nyc3"
}

run "denies_all_inbound" {
  command = plan
  assert {
    condition     = length(digitalocean_firewall.this.inbound_rule) == 0
    error_message = "The baseline firewall must have zero inbound rules."
  }
  assert {
    condition     = output.inbound_rule_count == 0
    error_message = "inbound_rule_count output must be 0."
  }
}

run "applies_by_tag_with_convention_name" {
  command = plan
  assert {
    condition     = digitalocean_firewall.this.name == "foundation-nyc3-baseline"
    error_message = "Name must be <layer>-<region>-<purpose>."
  }
  assert {
    condition     = contains(digitalocean_firewall.this.tags, "cah-baseline-nyc3")
    error_message = "Firewall must attach by the given tag."
  }
}

run "default_outbound_is_the_five_expected_rules" {
  command = plan
  assert {
    condition     = output.outbound_rule_count == 5
    error_message = "Default outbound must be tcp 443/80/53 and udp 53/123 only."
  }
}

run "extra_outbound_is_appended" {
  command = plan
  variables {
    extra_outbound_rules = [{ protocol = "tcp", port_range = "30000-31000" }]
  }
  assert {
    condition     = output.outbound_rule_count == 6
    error_message = "Extra outbound rules must be appended to the defaults."
  }
}
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `tofu -chdir=modules/firewall init -backend=false -input=false && tofu -chdir=modules/firewall test`
Expected: FAIL (module files do not exist).

- [ ] **Step 3: Write the module**

`modules/firewall/versions.tf`: identical to `modules/vpc/versions.tf`.

`modules/firewall/variables.tf`:
```hcl
variable "layer" {
  type = string
}

variable "region" {
  type = string
}

variable "purpose" {
  type        = string
  description = "Role in the firewall name (for example baseline or connector)."
}

variable "tag" {
  type        = string
  description = "Droplet tag this firewall attaches to."
}

variable "extra_outbound_rules" {
  type = list(object({
    protocol   = string
    port_range = string
  }))
  default     = []
  description = "Outbound rules appended to the defaults."
}
```

`modules/firewall/main.tf`:
```hcl
locals {
  default_outbound = [
    { protocol = "tcp", port_range = "443" },
    { protocol = "tcp", port_range = "80" },
    { protocol = "tcp", port_range = "53" },
    { protocol = "udp", port_range = "53" },
    { protocol = "udp", port_range = "123" },
  ]
  outbound = concat(local.default_outbound, var.extra_outbound_rules)
}

# No inbound_rule block: DigitalOcean denies all inbound traffic that no rule allows.
resource "digitalocean_firewall" "this" {
  name = "${var.layer}-${var.region}-${var.purpose}"
  tags = [var.tag]

  dynamic "outbound_rule" {
    for_each = local.outbound
    content {
      protocol              = outbound_rule.value.protocol
      port_range            = outbound_rule.value.port_range
      destination_addresses = ["0.0.0.0/0", "::/0"]
    }
  }
}
```

`modules/firewall/outputs.tf`:
```hcl
output "name" {
  value = digitalocean_firewall.this.name
}

output "inbound_rule_count" {
  value = length(digitalocean_firewall.this.inbound_rule)
}

output "outbound_rule_count" {
  value = length(digitalocean_firewall.this.outbound_rule)
}
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `tofu -chdir=modules/firewall test`
Expected: `4 passed, 0 failed`.

- [ ] **Step 5: Commit**

```bash
cd /home/chiefgyk3d/src/Clouds-Against-Humanity
git add modules/firewall
git -c user.name=ChiefGyk3D -c user.email=19499446+ChiefGyk3D@users.noreply.github.com commit -m "feat: tag-based deny-inbound firewall module" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Foundation stack

**Files:**
- Create: `stacks/00-foundation/versions.tf`, `variables.tf`, `main.tf`, `outputs.tf`
- Test: `stacks/00-foundation/tests/foundation.tftest.hcl`

**Interfaces:**
- Consumes: `modules/vpc` (inputs `layer`, `region`, `ip_range`; outputs `id`, `ip_range`), `modules/firewall` (inputs `layer`, `region`, `purpose`, `tag`; outputs `inbound_rule_count`).
- Produces (stack outputs read by Task 6 through Spacelift dependency references): `project_id`, `vpc_id`, `vpc_ip_range`, `baseline_tag`, `region`.

- [ ] **Step 1: Write the failing test**

`stacks/00-foundation/tests/foundation.tftest.hcl`:
```hcl
mock_provider "digitalocean" {}

run "defaults_are_a_single_region_deny_all_foundation" {
  command = plan
  assert {
    condition     = digitalocean_tag.baseline.name == "cah-baseline-nyc3"
    error_message = "Baseline tag must be cah-baseline-<region>."
  }
  assert {
    condition     = module.baseline_firewall.inbound_rule_count == 0
    error_message = "Foundation must ship a firewall with zero inbound rules."
  }
  assert {
    condition     = output.baseline_tag == "cah-baseline-nyc3"
    error_message = "The baseline tag must be exported for the access stack."
  }
}

run "region_flows_into_names" {
  command = plan
  variables {
    region = "fra1"
  }
  assert {
    condition     = digitalocean_tag.baseline.name == "cah-baseline-fra1"
    error_message = "Changing region must change the tag name."
  }
}

run "foundation_declares_no_costed_resources" {
  command = plan
  assert {
    condition     = length(jsondecode(file("${path.module}/cost.json")).resources) == 0
    error_message = "Stage 0 must cost nothing."
  }
}
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `tofu -chdir=stacks/00-foundation init -backend=false -input=false && tofu -chdir=stacks/00-foundation test`
Expected: FAIL (stack files do not exist).

- [ ] **Step 3: Write the stack**

`stacks/00-foundation/versions.tf`:
```hcl
terraform {
  required_version = ">= 1.8"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

# The token comes from the DIGITALOCEAN_TOKEN environment variable, injected
# by Spacelift from Doppler. It is never a variable and never written down.
provider "digitalocean" {}
```

`stacks/00-foundation/variables.tf`:
```hcl
variable "region" {
  type        = string
  default     = "nyc3"
  description = "DigitalOcean region slug."
}

variable "vpc_ip_range" {
  type        = string
  default     = "10.77.0.0/24"
  description = "Private CIDR. Must not overlap any homelab range (confirmed in the stage 0 guide before apply)."
}

variable "project_name" {
  type    = string
  default = "clouds-against-humanity"
}
```

`stacks/00-foundation/main.tf`:
```hcl
resource "digitalocean_project" "this" {
  name        = var.project_name
  purpose     = "Service or API"
  environment = "Production"
  description = "Managed by OpenTofu through Spacelift."
}

resource "digitalocean_tag" "baseline" {
  name = "cah-baseline-${var.region}"
}

module "vpc" {
  source   = "../../modules/vpc"
  layer    = "foundation"
  region   = var.region
  ip_range = var.vpc_ip_range
}

module "baseline_firewall" {
  source  = "../../modules/firewall"
  layer   = "foundation"
  region  = var.region
  purpose = "baseline"
  tag     = digitalocean_tag.baseline.name
}
```

`stacks/00-foundation/outputs.tf`:
```hcl
output "project_id" {
  value = digitalocean_project.this.id
}

output "vpc_id" {
  value = module.vpc.id
}

output "vpc_ip_range" {
  value = module.vpc.ip_range
}

output "baseline_tag" {
  value = digitalocean_tag.baseline.name
}

output "region" {
  value = var.region
}
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `tofu -chdir=stacks/00-foundation test`
Expected: `3 passed, 0 failed`. Then run `python3 -I scripts/cost_check.py --root .` and expect exit 0 and `planned $6.00/mo` (stage 1's manifest is already present).

- [ ] **Step 5: Commit**

```bash
cd /home/chiefgyk3d/src/Clouds-Against-Humanity
git add stacks/00-foundation
git -c user.name=ChiefGyk3D -c user.email=19499446+ChiefGyk3D@users.noreply.github.com commit -m "feat: foundation stack (project, tag, VPC, baseline firewall)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Twingate connector module

**Files:**
- Create: `modules/twingate-connector/versions.tf`, `variables.tf`, `main.tf`, `outputs.tf`, `cloud-init.yaml.tftpl`
- Test: `modules/twingate-connector/tests/connector.tftest.hcl`

**Interfaces:**
- Produces: inputs `layer`, `region`, `vpc_id`, `tags` (list of string), `size`, `ssh_public_key`, `twingate_network` (string); outputs `droplet_name`, `droplet_urn`, `private_ip`, `remote_network_id`, `size`. **No output exposes the connector tokens.**
- The droplet is created with `tags` already set, so the baseline firewall is in force from first boot.

- [ ] **Step 1: Write the failing test**

`modules/twingate-connector/tests/connector.tftest.hcl`:
```hcl
mock_provider "digitalocean" {}
mock_provider "twingate" {}

variables {
  layer            = "access"
  region           = "nyc3"
  vpc_id           = "vpc-test"
  tags             = ["cah-baseline-nyc3", "cah-connector-nyc3"]
  size             = "s-1vcpu-1gb"
  ssh_public_key   = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest test"
  twingate_network = "acme"
}

run "droplet_is_tagged_at_creation_inside_the_vpc" {
  command = plan
  assert {
    condition     = contains(digitalocean_droplet.connector.tags, "cah-baseline-nyc3")
    error_message = "The baseline tag must be on the droplet at creation."
  }
  assert {
    condition     = digitalocean_droplet.connector.vpc_uuid == "vpc-test"
    error_message = "The connector must live in the given VPC."
  }
  assert {
    condition     = digitalocean_droplet.connector.name == "access-nyc3-connector"
    error_message = "Name must be <layer>-<region>-connector."
  }
}

run "no_paid_extras_and_no_ipv6" {
  command = plan
  assert {
    condition     = digitalocean_droplet.connector.size == "s-1vcpu-1gb"
    error_message = "Size must come from the variable."
  }
  assert {
    condition     = digitalocean_droplet.connector.backups == false && digitalocean_droplet.connector.ipv6 == false
    error_message = "Backups and IPv6 must stay off (they are unpriced)."
  }
}

run "cloud_init_installs_connector_for_the_network" {
  command = plan
  assert {
    condition     = strcontains(digitalocean_droplet.connector.user_data, "TWINGATE_NETWORK='acme'")
    error_message = "cloud-init must set the Twingate network."
  }
}

run "tokens_never_leave_the_module" {
  command = plan
  assert {
    condition     = !strcontains(file("${path.module}/outputs.tf"), "token")
    error_message = "No output may mention or expose connector tokens."
  }
}
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `tofu -chdir=modules/twingate-connector init -backend=false -input=false && tofu -chdir=modules/twingate-connector test`
Expected: FAIL (module files do not exist).

- [ ] **Step 3: Write the module**

`modules/twingate-connector/versions.tf`:
```hcl
terraform {
  required_version = ">= 1.8"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    twingate = {
      source  = "twingate/twingate"
      version = "~> 3.0"
    }
  }
}
```

`modules/twingate-connector/variables.tf`:
```hcl
variable "layer" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "tags" {
  type        = list(string)
  description = "Droplet tags, including the baseline firewall tag. Set at creation."
}

variable "size" {
  type        = string
  description = "Droplet size slug. The stack reads it from cost.json."
}

variable "ssh_public_key" {
  type        = string
  description = "Admin public key. SSH is reachable only through Twingate."
}

variable "twingate_network" {
  type      = string
  sensitive = true
}
```

`modules/twingate-connector/cloud-init.yaml.tftpl`:
```yaml
#cloud-config
package_update: true
package_upgrade: true
packages:
  - unattended-upgrades
runcmd:
  - [bash, -c, "curl -fsSL https://binaries.twingate.com/connector/setup.sh | TWINGATE_ACCESS_TOKEN='${access_token}' TWINGATE_REFRESH_TOKEN='${refresh_token}' TWINGATE_NETWORK='${network}' TWINGATE_LABEL_DEPLOYED_BY='opentofu' bash"]
```

`modules/twingate-connector/main.tf`:
```hcl
resource "twingate_remote_network" "this" {
  name     = "${var.layer}-${var.region}"
  location = "OTHER"
}

resource "twingate_connector" "this" {
  remote_network_id = twingate_remote_network.this.id
  name              = "${var.layer}-${var.region}-connector"
}

resource "twingate_connector_tokens" "this" {
  connector_id = twingate_connector.this.id
}

resource "digitalocean_ssh_key" "admin" {
  name       = "${var.layer}-${var.region}-admin"
  public_key = var.ssh_public_key
}

resource "digitalocean_droplet" "connector" {
  name       = "${var.layer}-${var.region}-connector"
  region     = var.region
  size       = var.size
  image      = "ubuntu-24-04-x64"
  vpc_uuid   = var.vpc_id
  tags       = var.tags
  ssh_keys   = [digitalocean_ssh_key.admin.fingerprint]
  ipv6       = false
  backups    = false
  monitoring = true

  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    access_token  = twingate_connector_tokens.this.access_token
    refresh_token = twingate_connector_tokens.this.refresh_token
    network       = var.twingate_network
  })
}
```

`modules/twingate-connector/outputs.tf`:
```hcl
output "droplet_name" {
  value = digitalocean_droplet.connector.name
}

output "droplet_urn" {
  value = digitalocean_droplet.connector.urn
}

output "private_ip" {
  value = digitalocean_droplet.connector.ipv4_address_private
}

output "remote_network_id" {
  value = twingate_remote_network.this.id
}

output "size" {
  value = digitalocean_droplet.connector.size
}
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `tofu -chdir=modules/twingate-connector test`
Expected: `4 passed, 0 failed`. If `init` or `validate` reports an unknown attribute on a Twingate or DO resource, read the real schema with `tofu -chdir=modules/twingate-connector providers schema -json | jq '.provider_schemas | keys'` and the resource's block, then fix the attribute name and keep the assertion's intent.

- [ ] **Step 5: Verify the install command against the vendor's current docs**

Open the Twingate Connector Linux install documentation (docs.twingate.com, "Connector deployment" for Linux) and confirm the setup URL and the three `TWINGATE_*` variables used in `cloud-init.yaml.tftpl`. Record the page title and date in `docs/stages/01-access.md` (Task 8). If the documented command differs, change the template and keep the test green.

- [ ] **Step 6: Commit**

```bash
cd /home/chiefgyk3d/src/Clouds-Against-Humanity
git add modules/twingate-connector
git -c user.name=ChiefGyk3D -c user.email=19499446+ChiefGyk3D@users.noreply.github.com commit -m "feat: Twingate connector module" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Access stack

**Files:**
- Create: `stacks/10-access/versions.tf`, `variables.tf`, `main.tf`, `outputs.tf`
- Test: `stacks/10-access/tests/access.tftest.hcl`
- Existing: `stacks/10-access/cost.json` (Task 1)

**Interfaces:**
- Consumes: `modules/twingate-connector` (Task 5), `modules/firewall` (Task 3), foundation outputs `vpc_id`, `project_id`, `baseline_tag`, `region` as stack variables of the same names.
- Produces: stack outputs `connector_private_ip`, `connector_tag`.

Design note recorded for stage 3: the baseline firewall has zero inbound rules, and DigitalOcean firewalls also filter traffic inside a VPC. When a later droplet needs SSH from the connector, that stage adds an inbound rule allowing TCP 22 from the connector tag. Nothing here opens it.

- [ ] **Step 1: Write the failing test**

`stacks/10-access/tests/access.tftest.hcl`:
```hcl
mock_provider "digitalocean" {}
mock_provider "twingate" {}

variables {
  region           = "nyc3"
  vpc_id           = "vpc-test"
  project_id       = "project-test"
  baseline_tag     = "cah-baseline-nyc3"
  twingate_network = "acme"
  admin_ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest test"
}

run "connector_size_comes_from_the_cost_manifest" {
  command = plan
  assert {
    condition     = module.connector.size == jsondecode(file("${path.module}/cost.json")).resources[0].size
    error_message = "The droplet size must be read from cost.json so the cost gate is the single source."
  }
}

run "connector_has_its_own_tag_and_outbound_only_firewall" {
  command = plan
  assert {
    condition     = digitalocean_tag.connector.name == "cah-connector-nyc3"
    error_message = "Connector tag must be cah-connector-<region>."
  }
  assert {
    condition     = module.connector_firewall.inbound_rule_count == 0
    error_message = "The connector firewall must also have zero inbound rules."
  }
}

run "ssh_is_reachable_only_as_a_restricted_twingate_resource" {
  command = plan
  assert {
    condition     = twingate_resource.connector_ssh.name == "cah-nyc3-connector-ssh"
    error_message = "SSH access must be a named, per-host Twingate resource."
  }
  assert {
    condition     = twingate_group.admins.name == "cah-nyc3-admins"
    error_message = "Access is granted to one named group."
  }
}
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `tofu -chdir=stacks/10-access init -backend=false -input=false && tofu -chdir=stacks/10-access test`
Expected: FAIL (stack files do not exist).

- [ ] **Step 3: Write the stack**

`stacks/10-access/versions.tf`:
```hcl
terraform {
  required_version = ">= 1.8"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    twingate = {
      source  = "twingate/twingate"
      version = "~> 3.0"
    }
  }
}

# Credentials come from the environment (Doppler through Spacelift):
# DIGITALOCEAN_TOKEN, and the Twingate provider's API token and network
# variables named in the provider documentation.
provider "digitalocean" {}
provider "twingate" {}
```

`stacks/10-access/variables.tf`:
```hcl
variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "project_id" {
  type = string
}

variable "baseline_tag" {
  type = string
}

variable "twingate_network" {
  type      = string
  sensitive = true
}

variable "admin_ssh_public_key" {
  type = string
}

variable "admin_user_ids" {
  type        = list(string)
  default     = []
  description = "Twingate user ids placed in the admin group. Supplied from Doppler, never committed."
}
```

`stacks/10-access/main.tf`:
```hcl
locals {
  cost      = jsondecode(file("${path.module}/cost.json"))
  connector = one([for r in local.cost.resources : r if r.name == "connector"])
}

resource "digitalocean_tag" "connector" {
  name = "cah-connector-${var.region}"
}

module "connector" {
  source           = "../../modules/twingate-connector"
  layer            = "access"
  region           = var.region
  vpc_id           = var.vpc_id
  tags             = [var.baseline_tag, digitalocean_tag.connector.name]
  size             = local.connector.size
  ssh_public_key   = var.admin_ssh_public_key
  twingate_network = var.twingate_network
}

# The baseline firewall already denies all inbound traffic. This one only adds
# the outbound ports the connector needs. Verify the list against Twingate's
# current firewall documentation before apply and record the date in the stage guide.
module "connector_firewall" {
  source  = "../../modules/firewall"
  layer   = "access"
  region  = var.region
  purpose = "connector"
  tag     = digitalocean_tag.connector.name
  extra_outbound_rules = [
    { protocol = "tcp", port_range = "30000-31000" },
    { protocol = "udp", port_range = "19302-19308" },
    { protocol = "udp", port_range = "443" },
  ]
}

resource "digitalocean_project_resources" "access" {
  project   = var.project_id
  resources = [module.connector.droplet_urn]
}

resource "twingate_group" "admins" {
  name     = "cah-${var.region}-admins"
  user_ids = var.admin_user_ids
}

resource "twingate_resource" "connector_ssh" {
  name              = "cah-${var.region}-connector-ssh"
  address           = module.connector.private_ip
  remote_network_id = module.connector.remote_network_id

  access_group {
    group_id = twingate_group.admins.id
  }

  protocols {
    allow_icmp = false
    tcp {
      policy = "RESTRICTED"
      ports  = ["22"]
    }
    udp {
      policy = "DENY_ALL"
    }
  }
}
```

`stacks/10-access/outputs.tf`:
```hcl
output "connector_private_ip" {
  value = module.connector.private_ip
}

output "connector_tag" {
  value = digitalocean_tag.connector.name
}
```

- [ ] **Step 4: Run it and confirm it passes**

Run: `tofu -chdir=stacks/10-access test`
Expected: `3 passed, 0 failed`.

- [ ] **Step 5: Check the Twingate resource schema against the real provider**

Run: `tofu -chdir=stacks/10-access providers schema -json | jq '.provider_schemas["registry.opentofu.org/twingate/twingate"].resource_schemas.twingate_resource.block | {attributes: (.attributes|keys), blocks: (.block_types|keys)}'`
Expected: the output lists `access_group` and `protocols` (or their v3 equivalents). If a name differs, fix `main.tf` to match, re-run Step 4, and note the difference in `docs/stages/01-access.md`.

- [ ] **Step 6: Run the cost gate**

Run: `python3 -I scripts/cost_check.py --root .`
Expected: exit 0 and `planned $6.00/mo, approved $6.00, ceiling $30.00`.

- [ ] **Step 7: Commit**

```bash
cd /home/chiefgyk3d/src/Clouds-Against-Humanity
git add stacks/10-access
git -c user.name=ChiefGyk3D -c user.email=19499446+ChiefGyk3D@users.noreply.github.com commit -m "feat: access stack (connector, connector firewall, admin group, SSH resource)" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: CI (GYST callers, local tofu-test job, `CI green` gate)

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: GYST `tofu-ci.yml`, `python-ci.yml`, `security.yml` at v1.21.0, commit `faba0b7d1ab65e9033bef1acfa93d6d57b5808c0`.
- Produces: a required check named `CI green`.

- [ ] **Step 1: Resolve the two action pins**

Run:
```bash
for r in actions/checkout opentofu/setup-opentofu; do
  tag=$(gh api repos/$r/releases/latest --jq .tag_name)
  sha=$(gh api repos/$r/commits/$tag --jq .sha)
  echo "$r $tag $sha"
done
```
Expected: two lines, each `owner/repo vX.Y.Z <40-hex>`. Use these exact values in the next step wherever `<CHECKOUT_SHA>`, `<CHECKOUT_TAG>`, `<SETUP_SHA>`, `<SETUP_TAG>` appear.

- [ ] **Step 2: Write the workflow**

`.github/workflows/ci.yml` (substitute the four values from Step 1 before saving; every other value is final):
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

permissions: {}

jobs:
  tofu:
    uses: ChiefGyk3D/git-your-ship-together/.github/workflows/tofu-ci.yml@faba0b7d1ab65e9033bef1acfa93d6d57b5808c0 # v1.21.0
    permissions:
      contents: read
      id-token: write
    with:
      directories: "stacks/00-foundation stacks/10-access modules/vpc modules/firewall modules/twingate-connector"

  python:
    uses: ChiefGyk3D/git-your-ship-together/.github/workflows/python-ci.yml@faba0b7d1ab65e9033bef1acfa93d6d57b5808c0 # v1.21.0
    permissions:
      contents: read
      id-token: write
    with:
      python-versions: '["3.12", "3.13"]'
      install-command: pip install pytest
      test-command: python -I -m pytest tests -q
      lint-install-command: pip install ruff
      lint-command: ruff check scripts tests
      workflow-lint: false

  security:
    uses: ChiefGyk3D/git-your-ship-together/.github/workflows/security.yml@faba0b7d1ab65e9033bef1acfa93d6d57b5808c0 # v1.21.0
    permissions:
      contents: read
      security-events: write
      pull-requests: write
      id-token: write
    with:
      codeql-languages: actions
      pip-audit-requirements: ""

  # Repo-specific: GYST has no tofu-test leg yet. See Task 9, step 9, for the
  # proposal to move this into git-your-ship-together.
  tofu-test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<CHECKOUT_SHA> # <CHECKOUT_TAG>
        with:
          persist-credentials: false
      - uses: opentofu/setup-opentofu@<SETUP_SHA> # <SETUP_TAG>
        with:
          tofu_version: 1.12.6
      - name: Cost gate
        run: python3 -I scripts/cost_check.py --root .
      - name: tofu test
        run: |
          for d in modules/vpc modules/firewall modules/twingate-connector stacks/00-foundation stacks/10-access; do
            tofu -chdir="$d" init -backend=false -input=false
            tofu -chdir="$d" test
          done

  ci-green:
    name: CI green
    if: ${{ always() }}
    needs: [tofu, python, security, tofu-test]
    runs-on: ubuntu-latest
    permissions: {}
    steps:
      - name: Fail unless every needed job succeeded
        env:
          RESULTS: ${{ join(needs.*.result, ' ') }}
        run: |
          for r in $RESULTS; do
            [ "$r" = "success" ] || { echo "a needed job finished as: $r"; exit 1; }
          done
```

- [ ] **Step 3: Lint the workflow locally if actionlint is present**

Run: `command -v actionlint >/dev/null && actionlint .github/workflows/ci.yml || echo "actionlint not installed; the tofu-ci caller lints it in CI"`
Expected: no findings, or the fallback message.

- [ ] **Step 4: Confirm no placeholder survived**

Run: `grep -n '<[A-Z_]*>' .github/workflows/ci.yml; echo "grep-exit=$?"`
Expected: no matching lines and `grep-exit=1`.

- [ ] **Step 5: Commit**

```bash
cd /home/chiefgyk3d/src/Clouds-Against-Humanity
git add .github
git -c user.name=ChiefGyk3D -c user.email=19499446+ChiefGyk3D@users.noreply.github.com commit -m "ci: GYST callers, local tofu-test and cost gate, CI green" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

The first real CI run happens after the repo exists (Task 9). If a GYST job fails on an input this repo does not need (for example dependency-review on a repository without a dependency graph), set that input off in the caller and note why in the commit message.

---

### Task 8: Documentation (README, stage guides, cost page)

**Files:**
- Create: `README.md`, `docs/stages/00-foundation.md`, `docs/stages/01-access.md`, `docs/cost.md`

**Interfaces:** none (prose). Every file obeys the no-identifiers rule. Placeholders use `<angle-bracket names>` only inside command examples a reader fills in at run time.

- [ ] **Step 1: Draft prose with the local model**

Per the routing rule, give `llm-local` the fact lists below and ask for a plain-English walkthrough for learners, one stage per file. Code does all counting and cost math; the model only writes sentences. Review its draft against the facts and fix anything it invented. Do not send any real account value to any model.

- [ ] **Step 2: Write `docs/stages/00-foundation.md`**

Required sections, in this order:

1. **What this stage builds:** a DigitalOcean project, one VPC in `nyc3` (default `10.77.0.0/24`), a baseline tag `cah-baseline-nyc3`, and a firewall with zero inbound rules. Cost: $0.
2. **Account hardening checklist** (each item gets a `Verified on:` date line when done):
   - [ ] Two-factor authentication on the account; recovery codes in the password manager.
   - [ ] Billing alerts set at $10 and $25 (below the $30 ceiling).
   - [ ] Token A: write scope, 90-day expiry, stored only in Doppler, used only by Spacelift.
   - [ ] Token B: read scope, 90-day expiry, for interactive tooling.
   - [ ] The token currently behind the `do-droplets` MCP server is identified; if it is write-scoped, it is replaced with Token B.
   - [ ] Rotation date for both tokens recorded in the password manager (not in this repo).
3. **Choices to confirm before apply:** region (`nyc3` default; it carries the `$6` size), VPC CIDR does not overlap any homelab range (compare against the router's routing table; record only "no overlap confirmed", never the ranges), license of this repo.
4. **Bootstrap order:** (a) create the Doppler project `clouds-against-humanity` with a `prd` config holding `DIGITALOCEAN_TOKEN` (Token A); (b) create the Spacelift stack `cah-00-foundation` rooted at `stacks/00-foundation` with the OpenTofu binary, autodeploy off; (c) feed the Doppler secrets into the stack's environment by the mechanism the free plans support (verify at setup time: Doppler's native Spacelift sync, or a Spacelift context filled once by hand); (d) run a proposed run, read the plan, then confirm.
5. **Verify:** the DO project exists; the firewall lists no inbound rules; `doctl compute droplet list` or the MCP droplet list is empty; the billing alerts are visible.
6. **Rollback:** discard the Spacelift run before confirming; after apply, `destroy` the stack (nothing here costs money).

- [ ] **Step 3: Write `docs/stages/01-access.md`**

Required sections, in this order:

1. **What this stage builds:** one `s-1vcpu-1gb` droplet running the Twingate connector inside the VPC, a connector-only outbound firewall, an admin group, and a per-host SSH resource limited to TCP 22. Cost: $6.00/month, approved total $6.00.
2. **Why there is no public SSH:** DigitalOcean droplets always have a public address; the control is a firewall that is attached by tag at creation and allows no inbound traffic. Reach the host by private IP through Twingate.
3. **Accepted residual risk:** the connector token appears in state and cloud-init user-data; marked sensitive, state in Spacelift, token revocable, rotate by running `tofu apply -replace=module.connector.twingate_connector_tokens.this`.
4. **Vendor facts to record when verified:** the Twingate install page title and date (Task 5 step 5); the Twingate firewall requirements page and date (outbound ports in `stacks/10-access/main.tf`).
5. **Bootstrap:** create the Spacelift stack `cah-10-access` rooted at `stacks/10-access`; add stack dependency on `cah-00-foundation` and map its outputs `vpc_id`, `project_id`, `baseline_tag`, `region` to `TF_VAR_vpc_id`, `TF_VAR_project_id`, `TF_VAR_baseline_tag`, `TF_VAR_region`; add to Doppler: the Twingate API token and network variables the provider reads, `TF_VAR_twingate_network`, `TF_VAR_admin_ssh_public_key`, `TF_VAR_admin_user_ids`.
6. **Verify:** (a) connector shows online in the Twingate admin console; (b) from a Twingate client, `ssh <user>@<connector private IP>` works; (c) from outside Twingate, `nmap -Pn -p 22,80,443 <connector public IP>` shows the ports filtered (scanning your own droplet is authorized); (d) `python3 -I scripts/cost_check.py --root .` still reports `$6.00`.
7. **Stage 3 note:** later droplets need an inbound rule allowing TCP 22 from the connector tag, because DigitalOcean firewalls also filter VPC-internal traffic.
8. **Rollback:** `destroy` the stack; the connector token dies with the connector.

- [ ] **Step 4: Write `docs/cost.md` and `README.md`**

`docs/cost.md` contains the stage table from the spec (stage, adds, monthly, running), the line "Source of prices: `docs/cost-prices.json`, retrieved 2026-10-10 from the DigitalOcean sizes API", and the unverified list (backups fraction, bandwidth overage, snapshots, vendor free-tier limits). `README.md` has: one paragraph of purpose, the layer diagram from the plan's File Structure, how to run `tofu test` and the cost gate, a pointer to the stage guides, and the sentence "Secrets live in Doppler; nothing in this repository is a credential."

- [ ] **Step 5: Run the identifier scan**

Run: `grep -rniE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' README.md docs | grep -v -E '10\.77\.0\.0/24|0\.0\.0\.0/0' ; echo "grep-exit=$?"`
Expected: no lines and `grep-exit=1` (only the documented default CIDR and the any-address rule may appear). Also search by eye for hostnames, serials, a callsign or grid, and the employer's name; there must be none.

- [ ] **Step 6: Commit**

```bash
cd /home/chiefgyk3d/src/Clouds-Against-Humanity
git add README.md docs
git -c user.name=ChiefGyk3D -c user.email=19499446+ChiefGyk3D@users.noreply.github.com commit -m "docs: README, stage 0 and 1 guides, cost page" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Rollout with human gates

Everything above is local and free. This task creates outward-facing things and spends money, so each gate needs the maintainer's explicit yes. Do not skip or reorder.

- [ ] **Step 1: Run the whole local gate once**

Run:
```bash
cd /home/chiefgyk3d/src/Clouds-Against-Humanity
python3 -I -m pytest tests -q > /tmp/cah-gate.log 2>&1; echo "pytest=$?"
for d in modules/vpc modules/firewall modules/twingate-connector stacks/00-foundation stacks/10-access; do
  tofu -chdir="$d" init -backend=false -input=false >> /tmp/cah-gate.log 2>&1
  tofu -chdir="$d" test >> /tmp/cah-gate.log 2>&1; echo "$d test=$?"
done
python3 -I scripts/cost_check.py --root . ; echo "cost=$?"
```
Expected: every line ends in `=0`. Capture exit codes as shown; never pipe the gate into grep and trust the pipe's status.

- [ ] **Step 2 (GATE): Maintainer approves creating the GitHub repo**

Ask: create `ChiefGyk3D/Clouds-Against-Humanity`, private at first, and which license. Confirm the active `gh` account is the personal one with `gh api user --jq .login` before any push. Then:
```bash
gh repo create ChiefGyk3D/Clouds-Against-Humanity --private --source . --push
```
Do not make it public yet.

- [ ] **Step 3: First CI run**

Watch it with `gh run watch` and read every job. Fix any GYST input the repo does not need (Task 7 note). The run is green only when `CI green` succeeds. If anything is red, fix it the same day.

- [ ] **Step 4: Branch protection**

Check that the maintainer's protection script exists (`ls /home/chiefgyk3d/src/protect-main.sh`), read it, and run it for this repo so `CI green` is the required check and force pushes are off. If it is missing, stop and ask.

- [ ] **Step 5 (GATE): Maintainer completes the stage 0 checklist**

The hardening items in `docs/stages/00-foundation.md` are console actions (two-factor, billing alerts, tokens). Wait for the maintainer to report each done, then record the `Verified on:` dates. Resolve the open items: region, VPC range non-overlap, the MCP token's scope, current free-tier limits for Spacelift, Doppler and Twingate (read each vendor's pricing page and record the date in `docs/cost.md`).

- [ ] **Step 6 (GATE): Doppler and Spacelift bootstrap, then stage 0**

The maintainer creates the Doppler project and the `cah-00-foundation` stack. Trigger a proposed run, read the plan, and confirm it creates only: one project, one tag, one VPC, one firewall. Ask for approval, then confirm. Run the stage 0 verification list. Record the results in the stage guide.

- [ ] **Step 7 (GATE): Stage 1**

Before applying, verify the Twingate outbound ports and install command against the vendor docs and fix the stack if needed. Create `cah-10-access` with the dependency mapping. Read the plan: it must create exactly one droplet (`s-1vcpu-1gb`), one SSH key, one tag, one firewall, and the Twingate objects. Ask for approval, then confirm, then run the stage 1 verification list.

- [ ] **Step 8: Stage-gate security review**

Use the Codex security tier only for this review (Plus plan, spend sparingly): `codex exec -m gpt-daybreak-blue-latest -c access_programs.cyber=daybreak_blue` with the diff of this branch as input. If Codex is near its limit, use the `adversarial-reviewer` agent instead. Fix every finding the same day or record why not. Opus or Mythos only with explicit approval.

- [ ] **Step 9 (GATE): Propose the GYST addition**

Ask before filing: a GYST issue proposing a `tofu test` leg in `tofu-ci.yml` (generic; two of the maintainer's repos will need it) and an identifier-denylist check. Until it exists, this repo keeps the local `tofu-test` job.

- [ ] **Step 10: Handoff**

Update the memory index with the repo's state (stages applied, open items), commit the stage guides with their verified dates, and report remaining work: stage 2 (Wazuh agents and log shipping, including the home-side connector VLAN decision).

---

## Self-Review

**Spec coverage:** layout and layered stacks (Tasks 2-6); region variable and naming (Tasks 2-6 tests); hardening checklist, project, VPC, deny-all firewall (Tasks 3-4, 8, 9); state and secrets via Spacelift and Doppler (Tasks 8-9); Twingate connector, groups, per-host resources, no public SSH (Tasks 5-6, 8); accepted token risk (Task 8); cost table and gate (Task 1, 7); documentation and no-identifiers scan (Task 8); AI tiering (Global Constraints, Tasks 8-9); testing and verification (all tasks, Task 9); open items 1-6 (Task 9 steps 2, 5, 6; the home-side VLAN decision is explicitly deferred to stage 2 in Task 9 step 10).

**Placeholders:** the only angle-bracket values are the four action pins resolved by a command in Task 7 step 1 and checked absent by step 4, and runtime values in verification commands.

**Type consistency:** module and stack names, outputs and variables (`vpc_id`, `project_id`, `baseline_tag`, `region`, `droplet_urn`, `private_ip`, `remote_network_id`, `size`, `inbound_rule_count`, `outbound_rule_count`) are identical wherever they appear.

**Review Focus coverage:** items 1-6 map to tests in Tasks 1, 2, 3 and 5.
