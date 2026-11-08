# Attack surface map: layer by layer

Side page to [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md). That page lists the surface by category (ports, addresses, accounts, tokens, dependencies, people). This page walks the same system by **layer**, from the cloud account in to the web tier, and asks four questions of each: what could an attacker aim at, what does this project do about it, which test or check in the repository covers it (or says none), and what should be logged and alerted on. Read it beside the [Threat model](Threat-Model.md), which ranks the threats this page only maps.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft, written from this repository's own pages and code.** Every row names the file it was read in, on **2026-10-30**. Nothing here was run against real infrastructure, and nothing was tested against an attacker. Several controls are **built but off by default** or **written but not applied**, and the row says which. The logging and alerting column is a **recommendation** unless it names a source in this repository. The page repeats only what the repository's own pages and threat model already publish, and it contains no attack steps. The first draft of the two short paragraphs under "In plain words" and "How to read the map" came from a local model and was then checked and corrected by hand; the tables were written by hand from the files they cite. Not yet reviewed by the maintainer.

> **Prerequisites.** [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md) for the six questions, and the Plan for failure page (blast radius and assuming breach, reached from the first page) for "what can this reach". The exercises need a Linux or macOS terminal and a clone of this repository. No cloud account. About 45 minutes (est.).

> **Where this runs.** Nothing on this page asks you to touch a system you do not own. The one command in the exercises runs this repository's own tests on your computer.

## What you will be able to do

- Walk a system layer by layer and name, for each layer, the thing an attacker would aim at first.
- Say which of this project's controls are applied, which are off by default and which are only designed.
- Find the test that guards a control, and say when the honest answer is "none".
- Say what to log and what to alert on in each layer, and what not to claim without a source.
- Build the same map for a system of your own.

## In plain words

A layered map walks a system from the outside in. For this project the layers are the cloud account, Spacelift and CI, Doppler, Twingate, the droplets, telemetry, the edge, and the web tier. For each layer it asks four things: what an attacker could aim at, what the project does about it, which test or check in the repository covers it (or says there is none), and what should be logged and alerted on.

The point of a map is that no layer is left to a single control. A token that leaks from one layer should be stopped by the next, and the [Threat model](Threat-Model.md) is where each threat is ranked. This page does not rank anything; it shows where each control lives and whether anything in the repository would notice if the control were removed.

## How to read the map

Each layer below has one table. The five columns are the four questions plus the file each row was read in.

- A test column that says **None** is an honest gap. It does not mean the control is absent; it means nothing in the repository fails if the control is changed, so a person has to notice. Many controls live in a vendor's settings, which a clone cannot read; the [threat model README](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/threat-model/README.md) lists those as unverified.
- A control that is **built but off by default** is not an applied control. A control that is **written, not applied** has never run against a real account.
- A citation written as `path::name` points at one test function or one OpenTofu `run` block inside that file. A bare path points at the whole file.
- "Recommendation" in the log column means this repository does not do it. It is advice, not a feature.

## Layer 1: the cloud account

The DigitalOcean account is what everything else builds on. Whoever holds its write token can create, destroy or open anything in it, and can run up a bill.

| What an attacker could aim at | What the project does | Test or check | What to log and alert on | Where |
|---|---|---|---|---|
| The write API token | Custom scopes only, never full access; a 90 day expiry; stored in Doppler; used only by Spacelift. A second, read-only token serves tooling, so a leak of that one costs visibility, not infrastructure. | None. Token scope and expiry are settings in the provider console; the threat model lists them as unverified. | Recommendation: the account's own activity history (check the vendor's page for what it offers), a token past its rotation date, and any use from a place you do not recognize. | `docs/spacelift-secrets.md`, `docs/threat-model/README.md` |
| A plan that opens a port, turns IPv6 on, or deletes the network or firewall | A plan policy denies an inbound rule that is open to the internet or not scoped to a tag, a droplet with IPv6, and the deletion of the project, network or firewall. A stack with autodeploy on is denied. The exceptions list is empty by default. | `.spacelift/policies/plan_test.rego` (run in CI by the policy job); `tests/test_ipv6_closed.py::test_the_repository_keeps_ipv6_closed`; `tests/test_outbound_allowlist_matches_module.py` | Every denied plan and every pull request that adds to an exceptions list. The run history in Spacelift is the source. Recommendation: treat a new exception as a reviewed event. | `.spacelift/policies/plan.rego` |
| A runaway bill | A cost gate refuses resource types it has not priced and totals the approved phases. Billing alerts at $10 and $25 are the second line. | `tests/test_cost_check.py::test_unknown_size_fails_closed`; `tests/test_ci_cost_gate.py` | The billing alerts. The model's own residual is spend outside the repository (bandwidth, resources made by hand), so check the usage page. The alerts themselves are unverified. | `docs/stages/approved.json`, `scripts/cost_check.py`, `docs/wiki/Threat-Model.md` |
| The account sign-in | The build guide tells the operator to turn on two-factor authentication before anything else. | None. A clone cannot read an account setting. | Recommendation: alerts for new sign-ins and for any change to the account's members or keys, from the provider's own settings. | `docs/wiki/Build-It-From-Zero-Accounts-to-Stage-1.md` |

## Layer 2: Spacelift and CI

Spacelift runs the plan and the apply. GitHub Actions runs the tests. Between them sit the code, the hook that fetches secrets, and the people who can change either.

| What an attacker could aim at | What the project does | Test or check | What to log and alert on | Where |
|---|---|---|---|---|
| A pull request that becomes a Spacelift run next to the secrets | A push policy never proposes a run, so no pull request's code runs in Spacelift; only a merge to `main` that changes a stack's files becomes a tracked run. The policy lives in Spacelift; the repository holds the copy that is tested. | `.spacelift/policies/push_test.rego::test_policy_never_allows_forks`; `.spacelift/policies/push_test.rego::test_docs_only_pull_request_starts_nothing`. Nothing in the repository checks that the policy is attached in Spacelift. | Any proposed run, and any run that is not a tracked run of `main`, is a signal: the run history shows both. Recommendation: alert on a stack that loses the `cah` label, because it loses the policy with it. | `.spacelift/policies/push.rego`, `docs/spacelift-secrets.md` |
| The hook script or the config that names the secrets | The script fails closed: proposed runs, task runs and branches other than `main` get nothing, names must be plain identifiers, and a bad download checksum stops the run. The script's checks are not the boundary; the push policy and branch protection are. | `tests/test_doppler_env.py::test_other_run_types_get_nothing`; `tests/test_doppler_env.py::test_non_main_branch_gets_nothing`; `tests/test_secret_separation.py` | A change to `.spacelift/` or `scripts/spacelift/` should be read by a human, and the push policy makes such a change a tracked run. Recommendation: a required review before a second writer is added. | `scripts/spacelift/doppler-env.sh`, `.spacelift/config.yml` |
| A compromised or replaced GitHub Action | Every action is pinned by commit, the default token permission is empty, and CI holds no cloud credential. | `tests/test_growth_chart_workflow.py` checks pins and permissions for that one workflow. None for `ci.yml` and `wiki.yml`: the pin is visible in the file and nothing fails if it moves. | A changed pin in a pull request, a CI run on a branch that should not have one. Recommendation: read pin changes as code changes. | `.github/workflows/ci.yml`, `docs/wiki/Threat-Model.md` |
| An apply nobody reviewed | A person reads the plan and confirms before the apply; autodeploy is denied by the plan policy. The repository cannot show who pressed confirm. | `.spacelift/policies/plan_test.rego` (the autodeploy denial). None for the confirmation itself. | The audit trail in Spacelift shows who confirmed. Recommendation: alert on an apply nobody expected. | `.spacelift/policies/plan.rego`, `docs/threat-model/README.md` |
| The wiki publish path | The workflow holds write permission in its publish job only, and the generate job reads. The threat model README lists this path as not yet modeled. | `tests/test_gen_wiki.py` covers page generation and refusals (symlinks, unusual names), not the token's scope. | A wiki change that no pull request explains. Recommendation: review the token scope with the vendor's page. | `.github/workflows/wiki.yml`, `docs/threat-model/README.md` |

## Layer 3: Doppler

Doppler holds every real secret. Spacelift holds one: a read-only Doppler token for one config.

| What an attacker could aim at | What the project does | Test or check | What to log and alert on | Where |
|---|---|---|---|---|
| The Doppler service token in Spacelift | Read-only, one config, 90 day expiry, write-only in the context, and the fetched values are masked in logs. If it leaks, the reach is every secret in that config until it is revoked. | `tests/test_doppler_env.py::test_tracked_main_exports_and_masks`. Masking on a real run is unverified until someone searches a real log for the token prefix. | Recommendation: the vendor's access log for the token, and a search of each tracked run's log for the token prefix. A token past 90 days. | `docs/spacelift-secrets.md`, `docs/threat-model/README.md` |
| Secrets of one cloud reaching another | One Doppler config and one Spacelift context per cloud, and a stack may request only its own cloud's names. The test proves the declared requests, not what the vendor enforces. | `tests/test_secret_separation.py::test_requesting_another_clouds_or_unlisted_secret_fails` | Recommendation: alert on a new context, a changed attachment, or a stack that asks for a name outside its prefix. | `.spacelift/config.yml`, `docs/spacelift-secrets.md` |
| The Doppler command line download | A pinned version and a pinned SHA-256 per architecture, failing closed on a mismatch. | `tests/test_doppler_env.py::test_bad_checksum_refuses_to_run_downloaded_cli` | A run that stops on `checksum mismatch` is an alert in itself; do not bypass it. | `scripts/spacelift/doppler-env.sh` |
| A required secret left as a placeholder or empty | One definition of the placeholder rule, with copies in the hook script and the OpenTofu validations that tests pin to it. | `tests/test_secret_rule.py` | A run that fails with `empty in Doppler` is an alert to read, not noise. | `scripts/secret_rule.py` |

## Layer 4: Twingate

Twingate is how a person reaches a droplet. Its connectors make outbound connections only.

| What an attacker could aim at | What the project does | Test or check | What to log and alert on | Where |
|---|---|---|---|---|
| A stolen Twingate login or API key | Sign-in is delegated to the identity provider, where multi-factor is to be enforced (a setting this repository cannot read). Access is one host and one port per resource, and an SSH key is still needed on the host. | `stacks/10-access/tests/access.tftest.hcl::ssh_resources_are_two_and_each_restricted_to_tcp_22`. None for the identity provider's policy. | Recommendation: the vendor's audit log for a new resource, group, service account or connector, and for a sign-in from a new place. | `stacks/10-access/main.tf`, `docs/wiki/Threat-Model.md` |
| A connector token | It is written to a root-only file, one token per connector, and each can be revoked. | `modules/twingate-bootstrap/tests/bootstrap.tftest.hcl::tokens_appear_only_in_the_root_only_config` | Recommendation: a connector that goes offline, and a connector that appears which you did not create. | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` |
| Locking the operator out | Two connectors with staggered updates and reboots; recovery is rebuilding the stateless droplets. | `stacks/10-access/tests/access.tftest.hcl::the_two_connectors_reboot_at_different_times` | Both connectors offline at once is the alert. | `docs/wiki/Threat-Model.md`, `stacks/10-access/main.tf` |
| Trusting a hosted control plane | Narrow scopes, end-to-end encryption to the connectors and a separate SSH key gate. The residual risk is accepted and written down. | None, by nature: it is a trust decision, not a setting. | The vendor's status and incident notices. Recommendation: a way to learn of them. | `docs/wiki/Why-ZTNA-Not-a-VPN.md`, `docs/wiki/Threat-Model.md` |

## Layer 5: the droplets

The two connector droplets are the only machines in the core. Each has a public address that cannot be removed, and nothing is meant to answer on it.

| What an attacker could aim at | What the project does | Test or check | What to log and alert on | Where |
|---|---|---|---|---|
| Any port on the public address | The baseline cloud firewall has no inbound rule from the internet; the one inbound rule is tag-scoped SSH between the connectors. IPv6 is kept off. | `stacks/00-foundation/tests/foundation.tftest.hcl::baseline_firewall_has_no_tag_scoped_rules_in_either_direction`; `tests/test_ipv6_closed.py`; `tests/test_zero_ports_check.py` (the tests of the outside check, which has not been run against real infrastructure) | The outside check's result and date: any answer, or "cannot tell", is an alert. | `modules/firewall/main.tf`, `scripts/zero_ports_check.py` |
| The login | One user, key only, root login off, `AllowUsers` set. | `modules/twingate-bootstrap/tests/bootstrap.tftest.hcl::sshd_dropin_has_the_hardening_settings` | Failed logins and `sudo` use, from the journal. With log shipping on (off by default), the agent collects them and `auditd` watches the account and sudoers files. | `modules/twingate-bootstrap/cloud-init.yaml.tftpl`, `docs/wiki/Droplet-Hardening.md` |
| The metadata service at `169.254.169.254` | It serves first-boot configuration, connector tokens included, to any local process. A lock that narrows it to root and the monitoring agent is **built, off by default and not tested on a real droplet**; the threat model lists the exposure as an accepted risk (T5). | `tests/test_metadata_lock_script.py::test_template_gates_the_lock_on_metadata_lock` tests the script with fakes. None on a real droplet. | Nothing today: a read of the metadata service is not logged. | `stacks/10-access/variables.tf`, `docs/wiki/Droplet-Hardening.md` |
| Unpatched or tampered software | Daily security updates from a restricted origin list, staggered reboots, a pinned package-repository key, and the order "update, then harden, then install". | `tests/test_unattended_origins_cleared.py`; `tests/test_update_order_pinned.py` | Recommendation: an alert when a host has not updated for longer than its window, and when the repository key changes. | `modules/twingate-bootstrap/cloud-init.yaml.tftpl`, `docs/wiki/Droplet-Hardening.md` |
| Outbound traffic from a connector | Outbound is allowed on a short list of ports, and a new world-open outbound rule needs an exception entry in the plan policy. The threat model README lists the open outbound range as not yet modeled. | `tests/test_outbound_allowlist_matches_module.py` | Recommendation: firewall logging. This repository configures none for the firewall module. | `modules/firewall/main.tf`, `docs/threat-model/README.md` |

## Layer 6: telemetry

Stage 2 carries logs and metrics from the droplets to a home network. Its cloud side is **written and mock-tested, not applied**. A compromised connector with a path home is a different kind of problem from a cheap droplet, which is why the [Threat model](Threat-Model.md) says to design the home side carefully.

| What an attacker could aim at | What the project does | Test or check | What to log and alert on | Where |
|---|---|---|---|---|
| The metrics endpoint, which has no login | The exporter binds the private address only, refusing to start if it finds none, and the metrics ports accept connections from a tag, not an address. | `tests/test_node_exporter_script.py::test_picks_the_private_address_not_the_public_one`; `tests/test_metrics_firewall.py::test_the_guard_bites_on_an_address_sourced_inbound_rule` | Recommendation: an alert when a scrape target stops answering. | `modules/twingate-bootstrap/cloud-init.yaml.tftpl`, `modules/firewall/main.tf` |
| The path from a connector to home | One service account per role, one resource per port, and the stack creates no service key. The stage 2 model lists the path home, the shared API key, the first-boot token and the key on a host as open high threats, and the home network as outside the repository. | `stacks/20-telemetry/tests/telemetry.tftest.hcl::defaults_plan_zero_resources`; `tests/test_telemetry_stack.py::test_no_service_key_is_created`; `tests/test_log_shipping_ports.py` | Recommendation, home side: alert on any connection from a connector to anything but its listed resources. | `stacks/20-telemetry/main.tf`, `docs/threat-model/README.md` |
| The log agent's first boot | The agent is denied and masked until it is enrolled, stale token files are swept, and every failure leaves the agent off. | `tests/test_log_shipping_hardening.py::test_success_unmasks_only_after_enrollment`; `tests/test_log_shipping_guard.py` | The agent's own silence: a host that stops reporting is an alert, not a quiet day. | `modules/twingate-bootstrap/cloud-init.yaml.tftpl`, `docs/stages/02-telemetry.md` |
| The logs themselves as an input | The stage 2 and edge designs say logs from a public host are untrusted data: parse them, limit their size, never treat them as instructions. | None yet: the edge design proposes a relay-side test with a hostile line. | Recommendation: alert on an oversized or unparsable line, not only on matches. | `docs/superpowers/specs/2026-10-19-edge-dmz-design.md` |

## Layer 7: the edge

The edge is a **designed** public network for services that must accept connections from the internet. Its network stack is built but **disabled and unapplied**: every resource is behind a switch that defaults to off, the stage is not approved, and no droplet or service stack exists yet. Read the [DMZ lesson](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md) for the concept.

| What an attacker could aim at | What the project does | Test or check | What to log and alert on | Where |
|---|---|---|---|---|
| A bug in an internet-facing service | The design allows four service ports, runs services as unprivileged users, and rebuilds the host from code instead of patching by hand. The network stack opens two of the ports and keeps the other two closed to everyone until a later change. | `stacks/50-edge/tests/edge.tftest.hcl::enabled_opens_reticulum_and_mqtt_only_so_i2pd_and_iperf3_stay_closed`; `tests/test_edge_stack.py::test_i2pd_and_iperf3_are_closed_to_everyone_in_the_network_stack` | The design's own residual: a public host will be scanned and sometimes attacked. Recommendation: alert on any port that answers beyond the declared ones. | `stacks/50-edge/main.tf`, `docs/superpowers/specs/2026-10-19-edge-dmz-design.md` |
| A pivot from the edge into the core | A separate network, no peering, no shared tag and no shared Doppler config; the address ranges must not overlap the core's. | `tests/test_edge_stack.py::test_no_peering_and_no_core_tag_in_the_edge_code`; `stacks/50-edge/tests/edge.tftest.hcl::an_edge_range_inside_core_is_refused` | Any new route, peering or shared tag between edge and core is an alert. | `stacks/50-edge/main.tf` |
| Secrets in the first-boot data | The first-boot data may carry one short-lived, read-only bootstrap token and no other secret-shaped field; it is never an output. | `tests/test_edge_stack.py::test_the_user_data_carries_no_secret_shaped_field`; `tests/test_edge_stack.py::test_the_user_data_is_never_an_output` | See the metadata row in layer 5: the same lock applies. | `modules/edge-host/cloud-init.yaml.tftpl`, `docs/superpowers/specs/2026-10-19-edge-dmz-design.md` |
| A flood, a bill spike, or an abuse report | The design accepts these: the provider's basic flood protection is not a layer 7 defense, byte caps and a billing alert come before the first apply, and the abuse inbox is a calendar item. | None: the design marks the abuse-report check as not testable in advance. | Read the abuse inbox weekly; watch the usage page after the first week; alert on the measurement path going dark. | `docs/superpowers/specs/2026-10-19-edge-dmz-design.md` |

## Layer 8: the web tier

This repository **builds no web server for visitors**. The layer is taught through a local lab and several lessons, and the map shows what to ask when a real one exists. The edge design is the planned home for public services.

| What an attacker could aim at | What the project does | Test or check | What to log and alert on | Where |
|---|---|---|---|---|
| The lab's own web tier | The lab publishes only on loopback, pins its images, mounts no Docker socket, and puts the origin tier on a network with no route out. It is local only. | `tests/test_wordpress_at_scale_lab.py::test_published_ports_are_loopback_only`; `tests/test_wordpress_at_scale_lab.py::test_the_origin_tier_has_no_route_out_and_publishes_nothing` | The lab teaches the questions; it ships no alerting. Recommendation for a real site: access logs, error rates and blocked requests, sent somewhere other than the web host. | `labs/wordpress-at-scale/compose.yaml` |
| Plugins, PHP and the admin page | The lesson's answer is to remove the surface where you can (a static site has no PHP to patch) and to put a filter in front where you cannot. | None for the advice itself; the lab's rules are tested. | A new plugin or admin account, a burst of login attempts, and a changed file in the web root. | `docs/wiki/WordPress-and-PHP-Security-WAF-and-Static-Sites.md` |
| A CDN hiding the real client address | The lesson teaches that behind a CDN the address in the log is the CDN's unless the origin is configured to trust the right header, and that an address is a weak identifier. | `tests/test_cdn_real_ip_lesson.py` runs the lesson's two Python scripts and compares their output with the page. The Nginx part is not run. | Recommendation: log the forwarded address next to the connection address, and alert when the origin is reached by anything but the CDN. | `docs/wiki/Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md` |

## What the map shows

Reading the eight tables together, three things stand out. They are all stated in the project's own pages.

- **Most of the "None" cells are settings held by a vendor**: token scopes, branch protection, the identity provider's multi-factor policy, whether a Spacelift policy is attached. A clone cannot read them, which is why the threat model README keeps an unverified list. The remedy is a human check on a schedule, written down.
- **Several controls are built but not applied**: the metadata lock, the host firewall, log shipping, the telemetry stack and the edge. Until they run on a real machine, the honest wording is "designed and tested against fakes".
- **The log column is mostly recommendation.** The repository builds some host logging (opt-in) and relies on the vendors' audit trails for the rest. A log nobody reads is not a control: decide who gets each alert before turning it on, as [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) teaches.

## Free path: fill a map of your own

### Exercise 1: run a guard and read what it guards

**Predict.** Pick one row of layer 5 or layer 7. If the control it names were removed, which test would fail, and what would the failure message say?

**Do.** From the root of a clone, create the project's test environment as the [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) page describes, then run one guard on its own:

```
python3 -I -m pytest tests/test_ipv6_closed.py -q
```

Open the file and find the test named after the control. Read the hostile fixture next to it: a guard worth trusting has a case that makes it fail.

**Check.** The run ends with a count of passed tests. Compare with your prediction. If the file has no hostile case for the control, write that down as a gap in the map, in the same way the "None" cells do.

### Exercise 2: map a system of your own

**Predict.** Which layer of your own home network or small project has the fewest tests and the fewest logs?

**Do.** Write the eight layer names on a page (or the layers that fit your system: account, code host, secrets, access, machines, logs, public services, web). For each, write one thing an attacker would aim at, the control you have, how you would know it still works, and what you would log. Write "none" where it is none.

**Check.** The cells you left as "none" are your list of work. Order them by what the layer can reach if it fails.

Free path summary: both exercises are free and run offline. Exercise 1 needs only Python 3.11 or newer and the repository's test dependencies.

## Checkpoint

1. Name the eight layers on this page, outside in.
2. What does a "None" in the test column mean, and what does it not mean?
3. Why is the push policy listed under Spacelift and CI, and what does the repository not check about it?
4. Which layer-5 control is built, off by default and untested on a real droplet?
5. Why does the edge layer say "designed" while its network stack is built?
6. Pick two layers and say what you would alert on and what the person who gets the alert should do.

Answers: (1) cloud account, Spacelift and CI, Doppler, Twingate, droplets, telemetry, edge, web tier. (2) Nothing in the repository fails if the control changes, so a person must notice; it does not mean the control is missing. (3) It stops pull requests from becoming runs next to the secrets; the repository tests its copy of the policy but cannot show that the copy in Spacelift is attached or current. (4) The metadata lock. (5) The stack exists behind a switch that is off and nothing runs on it; no service stack exists yet. (6) See the log column of any table; a good answer names the source and the next step.

## Common mistakes

- **Reading "a test exists" as "the control works".** Most tests here use fakes or read the code; they prove what is declared, not what a vendor does.
- **Counting a built-but-off control as applied.** The status words on each row exist to stop that.
- **Skipping the log column.** A control with no way to notice its removal is a control only until someone changes it.
- **Writing a new weakness into a public repository.** If a map of your own shows one, tell the owner privately first.
- **Treating the web tier as someone else's layer.** Plugins, the admin page and the address in the log are all part of the surface.

## Claims register

Every project claim above was read in the file named on its row, in this repository, on 2026-10-30. Nothing was applied or run against real infrastructure.

| Claim | Where read | Status |
|---|---|---|
| Token scopes, the 90 day expiry, the read-only second token | `docs/spacelift-secrets.md` (sections 2 and 4a) | Read; the console settings are unverified |
| The plan policy's denials, empty exceptions and autodeploy guard | `.spacelift/policies/plan.rego` | Read; tests exist, the attachment in Spacelift is a vendor setting |
| The push policy never proposes a run | `.spacelift/policies/push.rego`, `docs/spacelift-secrets.md` (section 9) | Read; the live copy was recorded as matching on 2026-10-30 in that page, not re-checked here |
| The hook script's run-type, branch and checksum rules | `scripts/spacelift/doppler-env.sh`, `tests/test_doppler_env.py` | Read |
| Per-cloud secret separation | `tests/test_secret_separation.py`, `docs/spacelift-secrets.md` (section 8a) | Read; proves declared requests only |
| Billing alerts at $10 and $25 | `docs/wiki/Threat-Model.md` (T11) | Read; unverified per `docs/threat-model/README.md` |
| Zero inbound from the internet, IPv6 closed | `docs/wiki/Threat-Model.md` (T1), `tests/test_ipv6_closed.py` | Read |
| The metadata lock is off by default | `docs/wiki/Threat-Model.md` (T5), `docs/wiki/Droplet-Hardening.md` | Read |
| The exporter binds the private address; metrics rules are tag-sourced | `modules/twingate-bootstrap/cloud-init.yaml.tftpl`, `tests/test_metrics_firewall.py` | Read |
| Stage 2 open high threats and the not-yet-modeled list | `docs/threat-model/README.md` | Read |
| The edge stack is disabled and unapplied | `stacks/50-edge/main.tf`, `tests/test_edge_stack.py` | Read |
| The lab's loopback, pinned-image and no-route-out rules | `tests/test_wordpress_at_scale_lab.py` | Read; the lab was not run |
| No firewall logging in the firewall module | Stated in the [first attack surface page](Attack-Surface-List-Shrink-Measure.md), searched 2026-10-30 | Carried over, not re-searched |

Back to the [Threat model](Threat-Model.md), [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md), or [Droplet hardening](Droplet-Hardening.md). Next: [The DMZ and hardening an internet-facing host](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md).
