# Clouds Against Humanity: one stack per service

> **Proposal for the maintainer. Nothing is built, nothing is approved, nothing is applied.** Three questions are ruled (2026-10-22): edge per service with stage 3 shared (question 1), edge services approved step by step (question 2), and lxmd on its own stack and droplet (question 3); questions 4 to 6, 8 and 9 stay open. This note records a ruling, works out what it means for the repository, and asks the questions that decide the cost. It changes no stack, no module, no manifest and no ceiling. The draft edge stack on branch `feat/dmz-stack-122` (draft PR #206) is read, not modified.

Status: DRAFT for review; questions 1 to 3 RULED 2026-10-22, the rest open. Date: 2026-10-22. Based on main `936a15d`. Epic: #72 (edge), issue #122 (edge stack), issue #96 (stack factory).
Tooling: OpenTofu throughout.
Scope: how the ruling splits the edge, the stage 3 workloads, the honeypot sensor and the telemetry pieces into stacks; the numbering; the one question that decides the bill; how values pass between stacks; and what the factory, the cost gate, the plan policy and the teardown checklist must change. It is not an implementation plan.

How this was produced: read in full from the repository on 2026-10-22: the edge design (`2026-10-19-edge-dmz-design.md`), the edge handoff, the stack factory status note, `docs/cost.md`, `docs/cost-prices.json`, `docs/stages/approved.json`, `scripts/cost_check.py` (the type tables, the connector-module rule, the stack naming and totals code; the plan-JSON half was skimmed), `.spacelift/config.yml`, `.spacelift/policies/plan.rego`, the existing stacks and modules, `tests/test_secret_separation.py` (the stack-name patterns), the stage 3 and honeypot designs (section lists and the tables that matter here), the teardown checklist (headings), and the draft #122 branch (`stacks/50-edge`, `modules/edge-host`, `docs/stages/05-edge.md`, its `cost.json` and `approved.json`). Not read: the full Rego rule bodies below the first deny rules, the rest of the Spacelift documentation, the DigitalOcean console, and the private factory repository. Spacelift product behavior is written from general knowledge and marked "est." wherever the repository does not already prove it. No cloud or Spacelift API was called.

## 1. The ruling

As relayed to me by the maintainer's lead on 2026-10-22 (the wording below is the brief's, not a quote from a transcript, and he should confirm it reads right):

> Services are split into individual OpenTofu stacks (one stack per service), and the same holds when terraforming a whole infrastructure.

What I take it to mean, in plain words:

1. A "service" is one thing that runs and has its own failure and its own lifecycle: Reticulum, lxmd, i2pd, Mosquitto, iperf3, each stage 3 daemon, the honeypot sensor. It gets its own directory under `stacks/`, its own Spacelift stack, its own state, its own `cost.json`, its own Doppler config and its own plan.
2. It applies to a whole build, not only to the edge. If someone terraforms an entire environment, the result is many small stacks that can each be planned, applied and destroyed alone, not one stack with everything in it.
3. It does not say by itself whether each service gets its own machine. The maintainer ruled that on 2026-10-22: "Agree, edge per service, stage 3 shared." Each internet-facing edge service stack gets its own droplet; the stage 3 daemons are separate stacks on one shared Docker host. The honeypot and the shared network stack are not ruled yet (section 4.3).

This reverses part of an earlier ruling. Edge design decision 7 (2026-10-19) accepted the single stack name `50-edge`, and decisions 1 and 2 priced one shared droplet at a $35 ceiling. The 2026-10-22 ruling (edge per service) reopens decisions 1 and 2, because five edge droplets cost more than one; the ceiling is handled by the question 2 ruling (step by step, section 4.4). Decision 7 (the name) is question 5. They stand until he answers those.

## 2. What exists today

Read on 2026-10-22:

| Stack | Directory | Holds | Cost manifest |
|---|---|---|---|
| Foundation | `stacks/00-foundation` | VPC, project, baseline tag | `{ stage 0, resources [] }` |
| Access | `stacks/10-access` | Two Twingate connector droplets, firewall, Twingate objects | Two `s-1vcpu-1gb` droplets, $12 |
| Telemetry | `stacks/20-telemetry` | Twingate service accounts and resources (logging and scrape), per site | `{ stage 2, resources [] }`, $0 |
| AWS twins | `stacks/aws/00-foundation`, `stacks/aws/10-access` | The AWS version of stages 0 and 1 | Priced from `docs/cost-prices/aws.json` |
| Edge (draft, branch only) | `stacks/50-edge` plus `modules/edge-host` | One VPC, tags, a Cloud Firewall, one droplet, one reserved IP; every daemon would be in one cloud-init | Empty until approved |
| Workloads (design only) | `stacks/30-workloads` in the stage 3 design | One Docker host, Portainer, five daemons, a Spaces bucket | Not written |

Two facts shape everything below.

- The repository is already split at the stage level (00, 10, 20) with one explicit Spacelift stanza per stack (`.spacelift/config.yml`, decision recorded in the stack factory status note, section 4.1). Splitting by service is the same idea one level down, not a new idea.
- The unbuilt edge services (Reticulum, lxmd, i2pd, Mosquitto, iperf3) are all in one cloud-init template in the draft. The draft's `docs/stages/05-edge.md` says so: no service is installed yet, `service_packages` accepts pins and installs nothing by default. So the split costs little code today; it costs a lot after the services exist.

## 3. Which services become stacks

| Zone | Service | Own stack? | Why / note |
|---|---|---|---|
| Edge | Network (VPC, tags, project resources) | Yes, one shared stack | Free resources every edge service needs. Not a service, but it must exist first |
| Edge | Reticulum transport (rnsd) | Yes | Internet-facing, own CVE surface |
| Edge | lxmd (LXMF propagation node) | Yes (ruled 2026-10-22) | Own stack and droplet, connecting to Reticulum over a TCPClientInterface. See section 9a |
| Edge | i2pd | Yes | Heaviest on bandwidth; its own transit and share caps |
| Edge | Mosquitto (private MQTT over TLS) | Yes | Holds credentials and a TLS key |
| Edge | iperf3 | Yes | Source-restricted; the only edge port core connectors reach (design 4.3) |
| Workloads | penguin-overlord, solarstorm_scout, Boon-Tube-Daemon, Stream-Daemon, Star-Daemon | Yes, each | Outbound-only pollers per the stage 3 design. Some may become scheduled DigitalOcean Functions instead, which the design leaves open. The stage 3 design deploys Functions with `doctl serverless`, outside OpenTofu and outside the cost gate, so a Function is not an OpenTofu stack and this ruling cannot cover it as written. Question 10 asks whether Functions are an exception (their own repository path and a hand-checked usage line) or are dropped in favor of the shared host |
| Workloads | Docker host, Portainer, Spaces bucket | Yes, as shared "host" stacks | Not services; see section 4 |
| Honeypot | Cowrie sensor | Yes | Lives in a separate cloud account by its own design (honeypot design, section 3), so its stack needs its own provider credentials. It never shares a stack, a state or a Doppler config with core |
| Telemetry | Logging paths, scrape paths | Not now | `stacks/20-telemetry` creates only Twingate access objects, costs $0, and already has `logging_enabled` and `metrics_enabled` switches. It is access policy, not a running service. Splitting it into a logging stack and a scrape stack is possible and small but buys little; defer, and say so in the lesson |
| Telemetry | node_exporter, log shippers | No | They are packages on the connector droplets, installed by the access stack's cloud-init. They stay with the host they run on |
| Dashboards | Grafana (stage 4) | No cloud stack | On-prem, $0 to the cloud bill |

## 4. The droplet question (ruled 2026-10-22)

> **Does each service stack get its own droplet, or do several service stacks deploy onto one shared host?**

In plain words: if Reticulum, Mosquitto and iperf3 are three stacks, is that three machines or one machine with three stacks pointed at it? One machine each costs more and isolates more. One machine costs less and blurs the line the ruling is drawing.

### 4.1 Cost of each shape

Prices are from `docs/cost-prices.json`, retrieved 2026-10-21 from the DigitalOcean sizes endpoint. The sizes are the 512 MB plan at $4, `s-1vcpu-1gb` at $6 and `s-1vcpu-2gb` at $12. Backups off. A reserved IP is free while assigned and $5.00 a month when not (edge design, section 5.1, read 2026-10-19). Whether five services fit a 1 GiB droplet, or one service fits 512 MB, is unmeasured: every "fits" below is est. The approved DigitalOcean total today is $12; `hard_max` is $60; the `edge` phase placeholder is $35 (`docs/stages/approved.json`).

| Shape | Edge droplets | Stage 3 droplets | Running total (connectors $12, Spaces $5 included) | Against `hard_max` $60 |
|---|---|---|---|---|
| S0. Today's rulings: one shared edge droplet, one shared stage 3 droplet | 1 x $6 | 1 x $12 | $12 + $12 + $5 + $6 = **$35** | Fits, $25 spare |
| S1. Edge: one droplet per service (5). Stage 3: one shared host | 5 x $6 = $30 | 1 x $12 | $12 + $12 + $5 + $30 = **$59** | Fits by $1 |
| S1a. As S1, with iperf3 and Mosquitto on the $4 size (est. fit) | 3 x $6 + 2 x $4 = $26 | 1 x $12 | **$55** (est.) | Fits, $5 spare |
| S2. Fallback only (question 3 ruled lxmd separate): lxmd on the Reticulum droplet, four droplets. Stage 3 shared | 4 x $6 = $24 | 1 x $12 | **$53** | Fits, $7 spare |
| S3. Everything per service: 5 edge, 6 workload droplets at $6 | 5 x $6 = $30 | 6 x $6 = $36 | $12 + $5 + $30 + $36 = **$83** | Over by $23 |
| S3a. As S3, every droplet that can on $4 (est.) | about $26 | 6 x $4 = $24 | about **$67** (est.) | Over by about $7 |
| S4. Several service stacks on one shared host stack per zone | 1 x $6 | 1 x $12 | **$35** | Fits |

The honeypot is not in the table. Its design keeps it in a separate account with its own figure ($6 droplet plus $5 Spaces, $11, option A, est. until decided) and its own alert, outside the core ceiling.

Other limits that per-service droplets hit, all from the edge design's verified table (read 2026-10-19):

- Reserved IPs: three per account by default, one per droplet. Five public edge services each wanting a stable address is five, so a limit increase would be needed first. How to ask, and whether it is granted, is not verified.
- Cloud Firewall: 50 rules, 10 droplets, five tags, free. Per-service firewalls fit.
- Outbound transfer is pooled at team level, $0.01 per GiB over; more droplets do not add allowance beyond what each plan includes (the per-plan figure is not verified in the design).

### 4.2 What "shared host" really means for an OpenTofu stack

This is the part that is easy to get wrong, so it is spelled out. OpenTofu creates resources; it does not log into a machine and install software. A stack called `reticulum` that deploys "onto" a droplet owned by another stack needs some way to get its configuration to that machine. The ways, and what each costs:

| Mechanism | Works for edge? | Works for stage 3? | Cost to the design |
|---|---|---|---|
| User-data on the host: the host stack renders every service's config into one cloud-init | Yes | Yes | Not really separate stacks. A change to one service replaces the droplet (a user-data change forces a new droplet, stage 1 doc section on rotation) and restarts all of them. The services share one blast radius and one plan |
| The host pulls its own desired state (a puller reads per-service config from Doppler or a bucket and starts units) | Yes, in principle | Yes | Adds a runtime configuration loop on a host the edge design wants immutable ("a rebuild is the only recovery", no admin path). A new component to harden and a new thing that can be poisoned |
| A service stack deploys containers through the Portainer API over Twingate | No: the edge has no connector and no admin path by design | Yes: stage 3 already reaches Portainer through Twingate | Real separate stacks with real separate plans, on a shared machine. The Portainer credential is a wide key; it can touch every container on the host |
| SSH provisioners | No: the edge has no SSH | Possible but against the repo's stance (SSH is not how this project configures hosts) | Rejected |

So on the edge, "several stacks on one host" has only two honest forms, both of which weaken the design's central rule (config only from cloud-init, no admin path). On stage 3 there is a clean form (Portainer), because that host is already designed to be managed that way.

### 4.3 Recommendation and ruling

**Ruled by the maintainer on 2026-10-22: "Agree, edge per service, stage 3 shared."** Points 1 and 2 below are therefore the ruling, kept with their reasoning. Points 3 and 4 (the shared network stack, the honeypot in its own account) are my recommendation only and are not ruled.

**Isolation follows exposure.** One rule, applied twice:

1. **Edge services: one droplet per service stack.** They face the internet, they run five different daemons with five different CVE histories, and the edge design's top-ranked risk is remote code execution in any one of them followed by theft of the log credential (risk 1). One service per machine is the cheapest control that shrinks that: a compromised iperf3 no longer shares a disk and a process space with the MQTT broker's passwords and TLS key. The design already says "the edge can be compromised; limit what that buys". Per-service machines are that sentence made structural. Each machine still has no SSH, no admin path and cloud-init only, exactly as the draft's host module does today.
2. **Workload daemons: separate stacks, one shared host stack.** The five daemons are outbound-only pollers at one trust level with their state in a bucket, and the host is already managed through Portainer over Twingate. Each daemon is its own stack that deploys one container through Portainer onto the shared host stack's Docker. Giving every poller its own droplet buys little isolation (they hold the same kind of social-API tokens) and costs $24 to $36 more a month.
3. **Shared free things stay shared, in their own network stack.** VPC, tags, project resource lists and the bucket cost nothing or a flat fee and are used by many services. They are a stack of their own (`50-edge-network`, and a workloads host/bucket stack), built first and destroyed last.
4. **Honeypot: its own account, its own stacks, never shared.** Unchanged from its design.

That is shape S1 in the table, now the ruled shape: **$59 a month at full build**, one dollar under `hard_max`. That is thin and I would not hide it. Three ways to widen it, none decided here: put iperf3 and Mosquitto on the $4 size once measured (S1a, $55 est.); fold lxmd onto Reticulum's machine only if the two-droplet link proves fragile (S2, $53, the fallback); or build the edge in stages and stop where the ceiling stops (section 4.4).

Why S4 (everything shared, $35) is not the shape, recorded for the lesson: it is the only shape that fits today's `edge` ceiling unchanged, and it is the cheapest, but on the edge it either collapses the stacks back into one plan (user-data) or adds a runtime puller on a host designed to have no admin path. It satisfies the letter of the ruling and defeats its point. It would have been the choice only if the money were the hard constraint; the lesson can use it as the contrast case ("stacks in name" on one machine).

Why S3 (everything per service) is also not the shape: it breaks `hard_max` ($83, or about $67 at the smallest sizes) to isolate pollers from each other for no stated threat.

### 4.4 What the ruling does to the ceilings (step by step, ruled 2026-10-22)

Edge design decisions 1 and 2 priced one edge droplet and set the `edge` phase at $35. Under the ruled shape S1 the real number is $59 at full build. Nothing forces full build at once, and the cost gate already makes each step its own reviewed raise:

- Ruled: approval is step by step, one service stack per reviewed change, and the ceiling is not raised to the full-build figure in advance.
- At the unchanged $35 ceiling there is room for exactly one edge droplet ($29 for stage 3 plus $6). The first service stack can be switched on; the rest wait.
- Each further service stack raises the DigitalOcean approved total by its droplet in its own reviewed change (`scripts/cost_raise.py` prints the diff; the process is in `docs/cost.md`). A raise past the `edge` phase's ceiling also needs a ceiling edit. So the order of enablement is also the order of spending, and the maintainer approves one $6 step at a time.
- `hard_max` stays $60 and the full S1 build sits just under it. Raising `hard_max` is its own reviewed edit and I do not propose it.

## 5. Numbering and naming

The cost gate and the secret-separation tests constrain the choice, so the options are narrow:

- `scripts/cost_check.py` accepts a stack directory named `<digits>-<name>` (`STACK_NAME_RE`) and derives the Spacelift stack id from the path (`stacks/50-edge-iperf3` becomes `cah-50-edge-iperf3`).
- `tests/test_secret_separation.py` has a fixed list of DigitalOcean stack names (`cah-00-foundation|cah-10-access|cah-20-telemetry`) and asserts that an unlisted name such as `cah-30-new` is refused. Every new stack needs one deliberate edit there, which is the point: a stack cannot appear with secrets by accident.

### 5.1 Options

| Scheme | Example | For | Against |
|---|---|---|---|
| A. Flat, one decade per zone (recommended) | `50-edge-network`, `51-edge-iperf3`, `52-edge-mosquitto`, `53-edge-i2pd`, `54-edge-reticulum`, `55-edge-lxmd`; `30-workloads-host`, `31-...` | Works with the gate and the tests as written; the number is the build order inside the zone, so the teardown order is the reverse; one stack, one directory, one Spacelift stanza | Ten slots per zone; a zone that outgrows its decade needs a renumber (which changes Spacelift stack ids, so it is expensive) |
| B. Nested | `stacks/50-edge/network`, `stacks/50-edge/iperf3` | Groups a zone in the file tree | The gate's stack-name check expects the number on the first path level and treats `stacks/aws/...` as a provider directory; nested service directories would need new code in `cost_check.py`, the sites logic and the tests for no functional gain. The stack id (`cah-50-edge-iperf3`) is the same either way |
| C. Names only, no numbers | `edge-iperf3` | Nothing to renumber | Loses the build-order meaning the repository uses everywhere (00, 10, 20) and fails `STACK_NAME_RE` as written |

Recommendation: **A, flat.** Rename the draft `50-edge` to `50-edge-network` and put each edge service at 51 to 55 in build order (iperf3 first, because it is the simplest daemon and the only one with an enforced source list, so it is the cheapest first proof of the pattern). The honeypot gets its own decade (suggested `60-honeypot-...`, unreserved) and, because it is another account, its own provider pattern in `STACK_PATTERNS` and its own secret names, not a name under the core pattern. Ordering inside a decade is by dependency, not by importance; a service with no dependency on another sits wherever it was added.

The stage 4 number is not used in the repository yet; leave `40` unclaimed (est. for Grafana, which has no cloud stack).

### 5.2 Per-site instances

The repository already has a second multiplication axis: `stacks/sites/<resource_key>/<stack>/cost.json` with `instance_of`, one instance of a base stack per site. Per-service stacks multiply with it (services x sites). Recommendation: do not instance edge or workload service stacks per site now. The second-site phase adds two connectors, not a second edge. If a second edge site ever exists, it is a second set of directories or an `instance_of` per service; that decision waits for the need.

## 6. How values pass between stacks

Today the answer is "by hand": `stacks/10-access` takes `vpc_id` and `project_id` as variables, and `stacks/20-telemetry` says in its variable text that the connector addresses come "by hand or by a stack dependency (a map through a dependency is UNVERIFIED)". Per-service stacks make this a rule instead of a habit.

Rules:

1. **Only non-secret identifiers cross a stack boundary.** Ids, names, tags, CIDRs, region, and a service's public address. Never a token, key, password, bootstrap value or anything marked sensitive. A test should fail any stack output that is sensitive or whose name looks like a secret, and any `terraform_remote_state` read of a secret-bearing stack.
2. **Network stack outputs, service stacks read.** `50-edge-network` outputs the VPC id, its CIDR, the region and the base tag name. Each service stack takes them as plain variables.
3. **Three ways to get a value in; pick in this order:**
   1. Spacelift stack dependencies with output references, which map an upstream output to a downstream input on the downstream run (est., from general Spacelift knowledge; confirm in the Spacelift documentation before relying on it, and note the repository's own UNVERIFIED about maps). It also orders runs. No state read permission needed beyond what Spacelift does internally.
   2. A data source that looks the object up by deterministic name or tag in the same cloud account (for example the VPC by its fixed name). No coupling through state and no extra permission, but it fails late (at plan) with a plain "not found".
   3. A variable set by hand in the stack's tfvars or Doppler config, as stage 1 does today. Slowest, least coupled, always works.
   Reading another stack's state directly (`terraform_remote_state`) is the option I would avoid: it gives a service stack read access to a state file that may hold more than the output it wants.
4. **Dependencies point from service to network, never the other way, and never from core to edge.** The one place this bites: the core connector firewall needs a TCP 5201 outbound rule that names the iperf3 service's public address (edge design decision 10). If `10-access` took that as a dependency on `51-edge-iperf3`, core could not be planned or destroyed without edge. Give it as a plain variable from Doppler (a public address is not a secret) set after the iperf3 stack exists. Core stays independent.
5. **Secrets use Doppler; per-service isolation is an unresolved security decision, not an effect of the split.** Today `.spacelift/config.yml` gives each stack a stanza that names the secrets it may load, and `tests/test_secret_separation.py` enforces those names fail-closed. That is a convention for honest code, not a barrier: the hook uses the shared `cah-doppler` context with one read token for config `prd` (`docs/spacelift-secrets.md`, sections 1 and 8), so a compromised service run could read any secret in that config, not only the ones its stanza names. Naming fewer secrets in a stanza does not change that. To make "one Doppler config per service" true, each service stack needs its own Doppler config and read-only token, its own Spacelift context attached only to that stack (not the `autoattach:cah` context), and a fail-closed test that proves a stack cannot attach another stack's context. That is new wiring this note does not design; it is an open decision for the maintainer (new question 11) and a prerequisite to claiming isolation between service stacks at the Spacelift level. Separately, the edge design's per-host runtime bootstrap token (one short-lived, read-only token per host, scoped to that host's own Doppler config) is host-side and unaffected: it is what stops the Reticulum host reading the Mosquitto credentials once those configs exist. N hosts means N bootstrap tokens to issue and revoke; that is real operator work and belongs in the build checklist.

## 7. How the stack factory registers N stacks

The factory decision stands and gets more important: **one explicit stanza per stack, nothing generated from a loop or a pattern** (stack factory status, section 4.1). Splitting the edge into six stacks and stage 3 into about seven makes about thirteen new stanzas.

Per stack, one pair of pull requests, in lockstep (the status note's open question 2):

1. In this repository: a stanza in `.spacelift/config.yml` (identical `before_init` and `before_apply`, only that service's secret names) and a matching name in `STACK_PATTERNS` in `tests/test_secret_separation.py`.
2. In the private factory repository: the stack entry (project root `stacks/<n>-<name>`, OpenTofu, autodeploy off, deletion protection on).

Consequences to plan for:

- The status note's proposed cross-repo agreement check (the private CI compares its stack list with this repository's `.spacelift/config.yml` at a pinned commit) goes from nice to necessary. With thirteen more stacks the two lists will drift without it.
- The `STACK_PATTERNS` entry is a hand-edited alternation today. At about sixteen names it should become a short explicit list in the test, still one name per stack, with the same "an unlisted name is refused" negative test.
- Run ordering uses Spacelift stack dependencies (section 6). The factory should declare them next to the stacks. Whether a destroy run respects reverse order automatically is not verified here (est.: it does not); the teardown checklist must say the order explicitly.
- No Spacelift change happens without the maintainer's confirmation (issue #96's gate). That does not change.

### 7.1 Plan policy and allowlist impact

`.spacelift/policies/plan.rego` has two allowlists, `inbound_allowlist` and `destroy_allowlist`, both sets of exact resource addresses such as `module.fw.digitalocean_firewall.this`. An address is stack-relative: it does not say which stack it is in. With one stack per service and one module reused for each, five stacks would each contain a `module.service_host.digitalocean_firewall.this`. Allowlisting that address for one stack's world-open port would silently allowlist it in all five. That is a real defect, found by reading, not run.

Required changes, before the first service stack is enabled:

1. **Key both allowlists by stack id and address**, for example entries of the form stack id plus address, read from `input.spacelift.stack.id` (the status note says the plan input exposes `input.spacelift.stack.autodeploy`; the stack id is in the same object, est., confirm in the policy contract). Add Rego tests that an entry for one stack does not allow the same address in another.
2. The edge services are public by design, but not all of their rules are world-open, and this change must not make them so. The policy denies any inbound rule that is not tag-scoped, so every public rule needs its own allowlist entry (one reviewed line naming port, source and reason, as the policy header requires). The per-port source restrictions in the edge design stay exactly as designed: iperf3 (5201) stays limited to the named sources (the maintainer's home address and the core connectors' egress addresses, design section 4.2) and is allowlisted as a source-restricted rule, never as 0.0.0.0/0. Only the ports the design opens to everyone (Reticulum, the i2pd port, MQTT over TLS) are world-open, and the lxmd-to-Reticulum rule names one source (section 9a). The draft #122 notes the same for its single firewall.
3. **Destroy guard friction.** The guard denies deleting or replacing a `digitalocean_vpc`, `digitalocean_firewall`, project or anything tagged `protected`. A per-service teardown deletes that service's firewall, so each one needs a destroy-allowlist pull request and a policy paste into Spacelift, then an emptying pull request afterwards (teardown checklist, section 1). With six edge stacks that is six rounds. Option: allow a firewall delete when the same plan deletes its droplet in the same stack (a whole-service teardown) and deny it otherwise (a lone firewall delete would open or strip protection). That keeps the guard and removes ceremony. It is a policy change with its own tests and the maintainer's approval; I propose it, I do not assume it.
4. The edge design (section 10) already calls for a rule that denies any VPC peering resource and any core tag on an edge resource. Per service that becomes: a service firewall may reference only its own service tag, and no service stack may create a peering resource.
5. The policy is attached by the label `autoattach:cah`; each new stack carries the label through the factory. The Rego tests run in CI; the live copy is pasted into Spacelift by the maintainer.

## 8. How the cost gate changes

The gate (`scripts/cost_check.py`) already sums every `stacks/**/cost.json`, prices them from the provider table, compares each provider's total with `approved_monthly_total`, and compares the current phase's ceiling. So "each service stack has its own manifest, and the totals reconcile" is largely how it works. What breaks is narrower:

1. **The module-count rule is connector-specific.** The gate counts `twingate-connector` module blocks in a stack and demands the count equal the machine entries in that stack's manifest, and it requires each connector's size to be a plain `local.<name>.size` reference. A droplet is allowed only in files named in `approved.json` (`allowed_sources`). The draft #122 already needed to add its host module there. The stage 3 design (section 10) independently says the rule must generalize to "every costed module". With six service stacks it must: a small registry of costed modules (`twingate-connector`, `edge-service-host`, the stage 3 host module) with the same no-`count`/`for_each` rule and the same "block count equals manifest entries" reconciliation, per stack.
2. **Reserved IP.** The draft #122 branch adds a `reserved_ip` manifest kind and price handling to `cost_check.py` (`digitalocean_reserved_ip` is not on the free list today). Each edge service stack's manifest then lists one droplet and one `reserved_ip`. The gate must also catch the failure the edge design names: an apply that destroys a droplet but leaves its IP, billing $5 a month. With the IP and droplet in the same stack this is a per-stack plan check, not a cross-stack one; keep it there on purpose.
3. **One manifest per service stack.** Each `stacks/5x-edge-<svc>/cost.json` is empty while the stack is disabled and lists exactly its droplet and reserved IP once approved. `stacks/50-edge-network/cost.json` stays empty (every resource in it is free). A test should fail if a network or host-free stack lists a priced resource, and if an enabled service stack has an empty manifest (the draft's output precondition already does this per stack; it carries over).
4. **Totals reconcile in the existing way.** The sum of all manifests must not exceed `approved_monthly_total` for the provider; that is what the gate checks today (it errors when planned is above approved, not when it is below). An approval can therefore sit above the manifests, and "each approval is one $6 raise" is a review convention, not a gate rule. If the maintainer wants equality enforced, that is an added rule with its own tests and a migration for the existing figures; I do not assume it. Each service stack's approval is one reviewed change: its manifest gains $6, the approved total rises $6, and a phase ceiling is raised if needed. The gate output should print a per-stack and per-phase breakdown so the maintainer can see "iperf3 $6, Mosquitto $6 ..." and not only a sum. That is a report change, not a rule change.
5. **Phases.** `approved.json` phases are a map of ceilings with one `current_phase`. Edge is one phase; its services share it. If the maintainer prefers to approve services individually by phase, the phase map gets one entry per service. I recommend not: services within a zone share a phase, and the per-stack manifest gives the per-service view.
6. **The honeypot.** Separate account, separate figure, outside the core ceiling (its design, section 8.3). It must be a separate provider key in `approved.json` or a separately gated total so it can never be added into the core sum by accident. A design question for the gate; not decided here.
7. **Plan-versus-manifest reconciliation** (`plan_problems`) already checks one stack's plan against its own `cost.json`; with one plan per service this check gets stronger, since a plan is now small enough to read in full.

## 9. Build order and teardown

Build order, lowest number first. Everything in a row may be built in any order relative to the others in that row, one at a time:

| Order | Stack | Depends on |
|---|---|---|
| 1 | `00-foundation` | nothing |
| 2 | `10-access` | foundation |
| 3 | `50-edge-network` (separate VPC, no peering; independent of core) | nothing in core |
| 4 | `51-edge-iperf3`, `52-edge-mosquitto`, `53-edge-i2pd`, `54-edge-reticulum`, `55-edge-lxmd` | edge network; lxmd also needs a reachable Reticulum (section 9a) |
| 5 | `30-workloads-host`, then the daemon stacks (the container-based ones) | foundation, access (Twingate path), bucket |
| 6 | `20-telemetry` | access, plus the home side |
| separate | the honeypot stacks | nothing in core; separate account |

Destroy order is the exact reverse: services first, then the shared network or host stack that carried them, then core. The reason is the same as the existing checklist's reason for 10 before 00: a shared object cannot be deleted while a stack still uses it.

Teardown checklist impact (`docs/wiki/Teardown-Checklist.md` today covers two stacks and five addresses):

1. The checklist's section 1 grows from two stacks to the full list, with the reverse order written out, not implied. Do not rely on Spacelift to reverse it (est.).
2. Section 3 "prove zero billable resources" becomes a per-stack column: for every service stack, one droplet gone and one reserved IP gone. The IP is the line people miss, and with five of them the odds of a forgotten $5 rise. Add "count reserved IPs in the account: expect zero" as its own step.
3. The destroy guard ceremony (section 7.1, item 3) either repeats per stack or is replaced by the whole-service rule. The checklist must say which.
4. Section 4 "revoke and rotate" gains one Doppler bootstrap token and one service key per edge host. Revoke each with its host.
5. The "look again tomorrow" step stays and matters more.
6. A partial teardown becomes a normal, safe operation: destroy one service stack and the other five keep running. That is the main practical gain of the ruling, and the checklist should teach it as a first-class path ("take one service down", not only "take everything down").

## 9a. lxmd and Reticulum as a trust boundary

The maintainer ruled on 2026-10-22 that lxmd (the LXMF propagation node) and the Reticulum transport each get their own stack and droplet, joined by a TCPClientInterface. He remarked: "remember this is an example of trust boundaries." That remark is about this split only; it is not a general ruling about stacks. Taken that way, lxmd and Reticulum as separate stacks with separate identities are an example of a trust boundary, and the lesson can use them as one.

What was read (2026-10-22, not run): lxmd's source (`LXMF/Utilities/lxmd.py`, around line 369) calls `RNS.Reticulum(configdir=...)`, so lxmd always starts its own Reticulum stack or joins a shared instance on the same machine. The Reticulum manual (`reticulum.network/manual/using.html`) describes the shared instance as for local programs only, and its interfaces page (`interfaces.html`) shows a TCPClientInterface with `target_host` and `target_port`. Not verified: whether a shared instance can be reached from another machine. This design does not need it to be: lxmd runs its own Reticulum stack on its own droplet and reaches the transport as a client of it. So the link is an ordinary Reticulum interface, not a remote shared-instance socket (est.; confirm against the pinned versions before building, as the draft's pinning rule already requires).

**What crosses the boundary.** One TCP connection, from the lxmd droplet to the Reticulum droplet's Reticulum port, and only from that one source: the Reticulum host's Cloud Firewall and nftables name the lxmd host as the single permitted source for that port, in addition to whatever public sources the transport serves. The Reticulum stack must expose its address as a plain output or Doppler value (non-secret), never a key. Nothing else crosses: no shared disk, no shared tag, no shared Doppler config, no shared secret.

**What each side trusts.**
- Reticulum trusts the lxmd host only as an interface peer. It does not trust the content: LXMF messages are untrusted data to it.
- lxmd trusts the transport for reachability only. It does not trust that the transport is honest about who sent a message; Reticulum's own cryptography authenticates destinations, and each side checks it.
- Neither trusts the other's host. Each has no SSH, no admin path and cloud-init only (edge design).

**What a compromise gives the other side.**
- Compromised Reticulum host: the attacker can drop, delay or flood traffic to lxmd and can send it hostile frames. They cannot read lxmd's message store, its identity key or its Doppler config, because none are on that machine. The blast radius is availability plus whatever a parser bug in lxmd lets hostile frames do.
- Compromised lxmd host: the attacker holds the propagation store and its identity. They can send hostile frames back down the link and use the one permitted source address, which gives them nothing on the Reticulum host except what that one port exposes. They cannot read the transport's identity or configuration.
- Compared with one shared droplet (the fallback), where either compromise gives both: same disk, same user space, both identities.

**Why separate identities matter.** Each Reticulum stack has its own identity (a keypair). On one machine they could share a config directory and a single identity, so stealing one is stealing both and a rebuild would rotate both. On two machines each identity is generated and stored on its own host, each has its own bootstrap token and Doppler config, and each can be revoked and rebuilt alone. Identities are secrets: they never cross a stack boundary as outputs (section 6, rule 1).

**What this costs.** One more droplet, $6 (edge total unchanged at five services, $59 at full build, section 4.1), one more bootstrap token, and a link that can fail (the fragility the maintainer named). The TCP link should be tested first, with the host firewall rule that admits exactly one source, before either service is approved. The test is the plan-level one already in the stack tests: the rule exists with one source, and an unlisted source is refused.

**How it ties to the threat model.** The repository's approach is in `docs/wiki/Threat-Model.md`: name assets, actors and trust boundaries, then abuse cases, ranked risks, a mitigation and a verification for each, and residual risk. The edge design (section 3) applies it to the edge; this boundary is a new row in its trust-boundary table ("lxmd to Reticulum: one TCP flow from one named source, no shared secrets") and a new mitigation under its risk 1 (remote code execution in a daemon). No part of this section is a live test of anything; any verification against real hosts follows the edge design's rule of my own resources only, in a window the maintainer sets.

## 10. What has to change in the draft #122 stack

A list, not work done. The draft's checked-in structure: `stacks/50-edge` (VPC, two tags, one firewall with all public ports, one `edge_host` module call, an output precondition that tied the switch to `cost.json`) and `modules/edge-host` (one droplet, one reserved IP and assignment, a cloud-init template that renders nftables from one port list and installs pinned packages). Nothing is installed yet.

1. Rename `stacks/50-edge` to `stacks/50-edge-network` and shrink it to the free shared pieces: the `rns-dmz` VPC, the base tag, the CIDR guard against overlap with core and `reserved_ranges`. Its outputs become the VPC id, CIDR, region and tag name only.
2. Remove the firewall, droplet, reserved IP and `edge_host` call from it. Its `cost.json` stays empty permanently.
3. Split `modules/edge-host` into the reusable parts: the base hardening (sshd off, root locked, unattended upgrades, sysctl, metadata-endpoint lock, nftables default drop) and a per-service payload (package pin, ports, config template, service user and systemd unit). The module takes one service, so a droplet carries one daemon.
4. Replace the single shared `public_ports` / `restricted_ports` lists with one service's ports per stack. The Cloud Firewall and nftables continue to be rendered from the same single list inside each stack.
5. Give each service stack its own tag (for example `rns-dmz-<service>`), its own firewall attached to that tag, its own droplet, its own reserved IP and its own `cost.json`. Choose a gate-compatible activation model before writing this down as the implementation: `scripts/cost_check.py` rejects `count` and `for_each` on every costed resource and on connector module blocks, and its source scan cannot reconcile a disabled droplet with an empty manifest, so the draft's `count = local.on` on a droplet cannot give a disabled stack with an empty manifest. Two ways forward, to be chosen in step 1: (a) before approval the stack holds only free resources behind a switch (tag, firewall) and the droplet-bearing module call is added in the same reviewed change that adds the `cost.json` entry, so no priced block exists unpriced; or (b) change the gate to accept one tested boolean switch on a costed module and reconcile it against the manifest by plan, with tests that prove it bites. (a) needs no gate change and is my preference; neither is decided.
6. Drop the `i2pd_port != reticulum_port` precondition: separate machines cannot collide on a port. Replace it with a repository test that the set of public ports across edge service stacks matches the table in the edge design (no port opened that the design did not list).
7. Update the tests that assume one stack: `tests/test_edge_stack.py` (pins the single-stack shape), `tests/test_tfvars_example.py`, `tests/test_ipv6_closed.py`, `tests/test_module_policy.py`, `scripts/gen_example_tests.py` and the generated `tfvars` examples. They become loops over the edge service stack directories so a sixth service is covered without a new test.
8. Update `docs/stages/05-edge.md` from one stage page to a page per service (or one page with a section per service stack), and regenerate `docs/settings.json` and the Settings Reference with `scripts/gen_settings_doc.py` (CI checks they are in sync).
9. `docs/stages/approved.json`: keep the module file in `allowed_sources`, but do not raise anything yet. The edge phase and the DigitalOcean total are decisions after question 1.
10. `scripts/cost_check.py` and its tests: the generalized costed-module rule and the per-stack reporting from section 8. The reserved IP kind the draft added stays.
11. `.spacelift/config.yml`: no stanzas yet, as today (a test keeps them absent). Each is added in its own approval step (section 11).
12. The log path home. The edge design's option A ships logs through a Twingate headless client on the edge host with one service account and one resource (design 4.6, decisions 5 and 9). With one host per service that is a client and a service account per host, or a different design where services log only locally until the relay exists. This is not resolved by this note and decision 9 is still not ruled; it must not be quietly multiplied by six. Question 4.
13. The iperf3 firewall rule on the core connector side (decision 10) takes the iperf3 address as a Doppler-sourced variable, not a stack dependency (section 6, rule 4). A variable alone is not enough: `modules/firewall` takes `extra_outbound_rules` with only a protocol and a port and always emits `0.0.0.0/0` and `::/0` as the destination (the edge design records the same limit). Restricting TCP 5201 to the iperf3 address needs an address-aware change to the firewall module (a destination list per extra rule), its tests, and the plan policy check that the rule names one destination, as a reviewed core change. Without it the core connector rule would be open to any destination.

## 11. A migration order that keeps every step small and gated

Each line is one pull request or one maintainer action. Nothing in the first nine steps spends a dollar or touches a cloud account.

| Step | Change | Cost / risk | Gate |
|---|---|---|---|
| 0 | Maintainer answers the questions in section 13 and approves or edits this note | none | His decision |
| 1 | Cost gate: generalize the costed-module rule, per-stack and per-phase report, keep the reserved IP kind. Tests only; no stack changes | none | Full test suite; every existing check and its output for the existing stacks unchanged; the new per-stack and per-phase report added and tested as extra output |
| 2 | Plan policy: allowlists keyed by stack id and address; whole-service destroy rule if approved; Rego tests; maintainer pastes into Spacelift | none; policy only | `opa test` in CI; his paste |
| 3 | Re-cut the draft: rename to `50-edge-network`, shrink to free resources, still disabled. This replaces the contents of draft PR #206 (done by the person who owns that branch, as new commits, not by this note) | $0 | Mocked `tofu test`, the gate |
| 4 | Split `modules/edge-host` into base plus per-service payload; mocked tests only; no stack uses it yet | $0 | Mocked `tofu test` |
| 5 | First service stack, `51-edge-iperf3`, disabled, empty manifest | $0 | Mocked tests; the gate |
| 6 to 9 | `52-edge-mosquitto`, `53-edge-i2pd`, `54-edge-reticulum`, `55-edge-lxmd`, one pull request each, disabled | $0 | Same |
| 10 | Prerequisite: the arithmetic of the ruled shape ($59 at full build) assumes stage 3 ($12 host, $5 bucket) is already approved, and `current_phase` today is `stage-1` at $30 with `edge` only planned. Either stage 3 is approved first, with its own phase transition and approved-total edit, or the edge approvals proceed on the stage 1 base ($12 plus $6 per service) and each carries its own `current_phase` and ceiling edit; the maintainer picks the order (new question 12). Approve edge service 1 (`51-edge-iperf3`) as its own reviewed change: the DigitalOcean approved total up by its droplet, the `edge` phase left as is while it fits, its `cost.json`, its Spacelift stanza and factory entry (a pair), its Doppler config and bootstrap token, the plan policy allowlist line. Then its switch. Order inside the step follows the draft's own approval order in `05-edge.md` section 3 | +$6 | Maintainer in Spacelift; read the plan |
| 11 | Approve edge service 2 (`52-edge-mosquitto`), same checklist as step 10, its own pull request. The running total passes the $35 `edge` ceiling here, so this change also carries the matching ceiling edit and nothing beyond it | +$6 (or +$4) | Same |
| 12 | Approve edge service 3 (`53-edge-i2pd`), same checklist, own change; ceiling edit by the step only | +$6 | Same |
| 13 | Approve edge service 4 (`54-edge-reticulum`), same | +$6 | Same |
| 14 | Approve edge service 5 (`55-edge-lxmd`), same checklist, own change | +$6 | Same |
| later (before or after step 10, question 12) | Stage 3: the workloads host stack, then each daemon stack through Portainer | per the stage 3 design | Stage 3's own approval |

The sizes of steps 1 and 2 are the point: the two repository-wide changes (cost gate, plan policy) land first, once, with no stack in flight, so no service stack ever lands on a gate that cannot price it or a policy that cannot tell it from its neighbor.

## 12. Risks and rollback

| # | Risk | Mitigation | Rollback |
|---|---|---|---|
| 1 | Cost: S1 is $59 against `hard_max` $60; one unmeasured upsize ($6 to $12) breaks it | Build one service at a time; measure memory before sizing; each approval is its own reviewed raise | Destroy the service stack; its droplet and IP go with it |
| 2 | Forgotten reserved IP bills $5 a month, now up to five times | IP and droplet in the same stack; teardown checklist adds an IP count; billing alert before the first apply (edge decision 8) | Release the IP in the console; confirm tomorrow |
| 3 | Reserved IP limit (three by default) blocks the fourth edge service | Ask for the increase before step 10 of the services that need an address; not every service needs a stable address | Leave that service unbuilt |
| 4 | Plan policy allowlist leaks across stacks (section 7.1) | Keyed allowlists plus the tests that prove it | Empty the allowlist; the default is deny |
| 5 | Cross-stack coupling creeps in (core depends on edge, or secrets travel in outputs) | Rule 4 and rule 1 of section 6, with tests | Remove the reference; the stacks stay independent |
| 6 | More stacks, more drift between the public stanza list and the private factory | The cross-repo agreement check from the status note | Remove the unregistered stack from the factory |
| 7 | More hosts means more hosts to patch | Edge hosts are immutable and rebuilt monthly (design risk 5); a rebuild per service is smaller than one rebuild of everything | Rebuild the one stack |
| 8 | The two-droplet lxmd and Reticulum setup proves fragile | Ruled 2026-10-22: separate is the plan, folding lxmd into the Reticulum stack (S2) is only the fallback; test the TCP link first | Merge the two stacks before either is applied |
| 9 | The shared network stack is a single point: destroying it with services present | Dependencies in the factory; destroy guard on the VPC stays; reverse-order teardown | Rebuild from code (it is free resources only) |
| 10 | Honeypot account mixed with core by a shared pattern or Doppler name | Own provider pattern, own secret names, own state; never a core stanza | Delete the honeypot account's stacks; core is untouched |

What this note could not check: Spacelift's actual dependency and destroy-ordering behavior, whether the plan input exposes the stack id as assumed, the per-droplet memory need of any edge daemon, whether lxmd can reach a remote Reticulum, the reserved IP limit-increase process, and Twingate's service account count limits for one account per host. All are marked est. where they appear.

## 13. Questions for the maintainer

1. **RULED 2026-10-22.** Does each service stack get its own droplet? The maintainer: "Agree, edge per service, stage 3 shared." Edge services get a droplet each (five, $30); stage 3 daemons are separate stacks on one shared Docker host. Full build is $59 a month against the $60 hard limit. The honeypot-in-its-own-account and shared-network-stack parts of my recommendation were not part of the ruling and remain proposals.
2. **RULED 2026-10-22.** Which ceiling? The maintainer: "A, step by step." The edge ceiling is not raised to about $59 up front; each edge service is approved as its own reviewed change that raises the approved total by that service's droplet (about $6). Where a step takes the running total past the `edge` phase ceiling, that same reviewed change carries the matching ceiling edit and no more. Reading to confirm: I take "keep the edge ceiling as is" to mean no up-front raise, not that a second droplet can be added without touching the $35 figure, since $35 covers only one.
3. **RULED 2026-10-22.** Can lxmd run on its own machine? The maintainer: "yes." lxmd keeps its own stack and droplet and connects to Reticulum over a TCPClientInterface; folding it into the Reticulum stack (S2, $53) stays only a fallback if the two-droplet setup proves fragile. About this split he added: "remember this is an example of trust boundaries." See section 9a.
4. **Logging from each edge host.** The log path home (Twingate headless client, one service account) was designed for one host and decision 9 is still not ruled. With a host per service do you want a client per host, or no log shipping from the edge until the relay exists?
5. **Numbering.** Flat decades (`50-edge-network`, `51` to `55` for services, a separate decade for the honeypot), or something else? Is renaming the draft's `50-edge` to `50-edge-network` acceptable, given you ruled the name `50-edge` on 2026-10-19?
6. **Plan policy.** May the destroy guard allow a firewall delete when the same plan deletes its droplet in the same stack (a whole-service teardown), or do you want every teardown to go through the allowlist pull request ceremony?
7. **Workloads. Settled by the question 1 ruling.** The stage 3 daemons are separate stacks on one shared Docker host. What stays open under it is only the mechanism (Portainer, as the stage 3 design plans) and the stack count; confirm when stage 3 is approved.
8. **Telemetry.** Leave `20-telemetry` as one stack (it creates only Twingate access objects, $0), or split logging and scrape for the lesson's sake?
9. **Honeypot figure.** Still outside the core ceiling in its own account, as its design says, so the gate needs a separate total for it?
10. **Scheduled Functions.** Stage 3 plans some jobs as DigitalOcean Functions deployed with `doctl serverless`, which is not OpenTofu and is invisible to the cost gate (stage 3 design, sections 3 and 3a). Under one OpenTofu stack per service they cannot be stacks. Make Functions a named, documented exception with a usage line checked by hand, or run those jobs as containers on the shared host so every service is a stack?
11. **Per-service Doppler isolation.** The current hook gives every stack the same read token for config `prd`, so a stanza's secret list is a convention, not a barrier (section 6, rule 5). Do you want per-service Doppler configs, tokens and Spacelift contexts attached stack by stack, with a fail-closed test, before service stacks are enabled, or do you accept the shared context for now and drop the isolation claim?
12. **Order against stage 3.** Is stage 3 approved before the edge services (the $59 arithmetic holds), or do the edge services go first on the stage 1 base, each with its own phase and ceiling edit?

## 14. The lessons that teach it

The lesson `I4 Build-and-Destroy-Stack-Per-Service` is being written separately; this note should be what it cites. The points it needs, so the two agree:

- A stack is the unit of plan, apply, destroy, state, cost and secret access. Splitting by service makes each of those small and independent.
- Blast radius: what a bad plan or a compromised service can touch shrinks to one stack. Show a six-stack edge and take one down.
- Cost per stack: read each stack's `cost.json`, then the gate's total. The learner sees a $6 line move the approved total by $6.
- Passing values: ids cross boundaries, secrets never do. Doppler config per stack.
- Order: build up the numbers, destroy down. Look for the shared stack last.
- The tradeoff question (section 4) is a good discussion for the lesson: one machine per service costs more and isolates more; one shared machine costs less and blurs the stacks. The reader should be able to say which they would choose and why.
- Pay-to-play, per the project's principle: the theory path is free (read the manifests, run the gate, run `tofu plan` with every switch off, a no-op at $0). The hands-on path is one service stack at one $6 droplet for the hours it takes, torn down with the checklist; the learner does not need to build all six.
- Mark every figure here as a repository figure from the dates above, not a live quote.

## 15. What this note does not claim

- It does not claim any service fits any droplet size. Memory is unmeasured everywhere in it.
- It does not claim Spacelift's dependency, output-reference or destroy-ordering behavior; it names what to confirm.
- It does not claim the $59 total is final: it assumes the stage 3 shared host stays at one $12 droplet and the five edge services each fit $6.
- It changes no ruling already made except to name the ones it reopens (edge decisions 1, 2 and 7), and it leaves them as they are until the maintainer answers section 13.
