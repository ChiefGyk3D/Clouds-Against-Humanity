# Multiple sites and identity: one codebase, many sets of values

> **Unverified draft: the stage 2 telemetry pieces this page describes are built and merged (opt-in node exporter, Wazuh agent with auditd, metrics firewall rules, Grafana dashboards), but none of it has been applied or run against real infrastructure, and nothing has been measured.** Sources: the [settings and mini SOC design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-stage2-settings-and-mini-soc-design.md) section 3 (2026-10-16), `docs/cost.md` (the stack-instance section, read 2026-10-16), and the merged settings layer described in [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md). The settings layer, the cost gate's stack instances, the telemetry stack (stack 20, everything off by default) and the site-aware dashboards exist as code. No second site is deployed, and none of it is applied. Statements about Twingate's behaviour that are marked UNVERIFIED were not checked.

**Prerequisites:** [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md), [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md) and [Twingate](Twingate.md).

One site is easy to name: it is "the cloud". The moment a second one exists (another region, another account, another cloud), every telemetry question gets a second answer, and "which one?" becomes part of every query. This page is about what a site *is*, what breaks at two, and why adding one should be a new settings file and not new code.

## A site has an identity, and the identity has two halves

A **site** is one deployment of the same code with its own values. The home network counts as a site too, so one dashboard can put home next to the clouds.

| Attribute | Example | Meaning |
|---|---|---|
| `site_name` | `site-tor1`, `site-home` | A short, unique name. The join key in telemetry |
| `region` | `tor1`, `on-prem` | Where it physically is |
| `provider` | `digitalocean`, `aws`, `onprem` | Which cloud, or none |

Two settings carry that identity, and they must never be confused. This is the most expensive mistake on the page, so it comes first.

| Setting | Goes into | Default | Can it change on a live stack? |
|---|---|---|---|
| `resource_key` | **Names and tags** of cloud and Twingate objects: `access-tor1`, `cah-connector-tor1`, droplet `access-tor1-connector-a` | The `region`, so every existing name is unchanged | **Never.** A new name is a replace, and several replaces force a new machine |
| `site_name` | **Telemetry only**: metric labels, the `site_identity` output (including the agent group) and dashboard variables. Agent names take their prefix from a separate stack 10 input, `log_shipping.agent_name_prefix`, which you keep equal to it by hand | Empty, meaning `site-<region>` | Yes. It renames nothing in the cloud; it changes the identity under which history is recorded |

Why two? Because the obvious design uses one value for both, and that renames live infrastructure the day someone decides a label should be friendlier. [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md#resource_key-and-site_name-one-is-immutable-and-why) walks through the plan you would see. Both settings exist in the code (step 2 of the build order), and stack 20 reads `site_name` into its `site_identity` and `scrape_targets` outputs (`stacks/20-telemetry/site.tf`). No telemetry carries the label yet, because nothing is applied.

## Labels: the shape of "which one"

When Prometheus stores a number, it stores it with **labels**: key and value pairs. The design uses exactly five identity labels:

| Label | Example values | Question it answers |
|---|---|---|
| `site` | `site-tor1`, `site-home` | Where? |
| `region` | `tor1`, `on-prem` | In what part of the world? |
| `provider` | `digitalocean`, `onprem` | On whose platform? |
| `role` | `connector`, `workload`, `soc` | Doing what? |
| `instance` | `connector-a`, `connector-b` | Which machine? |

One label per question, one name per label. The design found a mistake of the opposite kind in its own first draft: dashboard panels filtered on a label called `host` that no target file set. A panel that filters on a label nobody sets shows nothing, or everything, depending on the query. It is better to pick the label once (`instance`) and use it everywhere.

**Why `site` is a label and not a job name.** A Prometheus *job* names a kind of thing that gets scraped. If each site had its own job, every dashboard panel and alert that selects the job would need rewriting for each site, and "all sites" would be a list of names to maintain. As a label, `site` costs one more filter, and `by (site)` turns any query into a per-site view.

### Cardinality: the cost of labels

Every distinct combination of label values is a separate time series, stored and indexed on its own. Labels that take few values (site, role) are cheap. A label that takes a new value for every event (a request id, a user name, a timestamp) turns one metric into millions of series and brings the server down. The design limits free-form labels to an allow-list (`env`, `role`, `owner_team`) with values no longer than 32 characters, and stack 20's `labels` variable refuses any other key and any value over 32 characters (`stacks/20-telemetry/variables.tf`). The home-side generator that writes the Prometheus target file is not built.

Worked scale: two sites with two connectors each is four targets. One metric on those four targets is four series. Add a label `env` with the value `lab` everywhere, and it is still four, because every series has the same value. Add a label with a different value per scrape, and the number of series grows with time. The first is a label; the second is a mistake.

## What breaks at two sites

| Problem | Why | What the design does | Status of the fact |
|---|---|---|---|
| Overlapping VPC ranges | Both sites default to `10.78.0.0/24`. A Twingate resource's address is an IP, so two networks with the same range make an address ambiguous | `reserved_ranges` validation: list the other ranges and the plan fails on overlap | The validation exists. That Twingate cannot tell two same-address resources apart is UNVERIFIED |
| Names collide | Every name embeds the region; two stacks in one region produce equal names | A distinct `resource_key` on the **new** stack | Whether Twingate or DigitalOcean refuses duplicates is UNVERIFIED |
| One stolen key reaches too much | A Twingate service key authorizes access to all resources assigned to its service (Twingate documentation, https://www.twingate.com/docs/services/ , fetched 2026-10-16, quoted in the design) | One service per site per role; one key per host; each service granted only that role's resources | Key facts from one page. Re-checked 2026-10-21 on the Twingate pricing page and the Services page: they name "secure service accounts" as a plan feature but state no count per plan. Not documented is not the same as "no limit": the maintainer reads the limit in the Twingate console (Settings, Billing) before applying stack 20 with more than one site |
| Label cardinality | See above | The label allow-list and the generator test | General Prometheus behaviour |
| Agent name reuse | A rebuilt droplet enrolls again under the same name | A site prefix in agent names, set through the separate `log_shipping.agent_name_prefix` input (the access stack never reads `site_name`), which you set to the same value by hand | Built as the opt-in `log_shipping.agent_name_prefix` in stack 10 (`<prefix>-connector-<a or b>`), not applied |
| Dashboards show only some sites | The existing Twingate dashboard at home has variables for exactly two named connectors; a third host shows nothing | `site` and `instance` variables | Read from the home stack on 2026-10-16, by role only |
| A whole site goes silent and nothing alerts | `absent()` cannot say which site is gone | An expected-target inventory | See [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) |
| The home logging connector is a single point | Every site's telemetry uses the same home-side path | Two connectors at home; the inventory alert runs at home | From the design |
| The cost gate is blind to the second site | It sees directories, not Spacelift stacks | Stack instance manifests, below | Exists, `docs/cost.md` |

## A second site is a new settings file, not new code

Here is what the design says adding `site-tor2` takes. Every step is data.

1. **Values.** A new `region` or a new `resource_key` (for example `tor2`), a `vpc_ip_range` that overlaps nothing (the first site's range goes in `reserved_ranges`), a `site_name`, and its own list of logging servers. The shape of that file is the `terraform.tfvars.example` of each stack.
2. **Stacks.** New Spacelift stacks pointing at the same code, with their own state, environment and Doppler config. A new stack starts from nothing, so its names can use the new key and nothing existing is renamed.
3. **`.spacelift/config.yml` entries** for the new stack ids. The entry tells the hook which Doppler secrets to fetch for that stack (see [Fork, private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md)). It is not what attaches credentials: in `docs/spacelift-secrets.md` (sections 4 and 8, read for this page) the `cah-doppler` context attaches to any stack carrying the `cah` label and supplies `DOPPLER_TOKEN` to every run type, independently of `config.yml`. So a new stack's label, context attachments and run policies are Spacelift settings you must control by hand.
4. **A cost approval.** A second site is a deliberate decision, not a side effect.
5. **A scrape inventory** for the home Prometheus, generated from the new stack's outputs. The data side exists: stack 20 emits a sensitive `scrape_targets` output per site. The generator that turns it into a target file and an expected-target inventory is not built, and the inventory in the synthetic lab is written by hand.

The lesson is the shape: **code is the thing that does not change per site; values are the thing that does.** If adding a site needs a code change, the code has a hard-coded value that belongs in a setting.

### How the cost gate sees a second site

The gate (`scripts/cost_check.py`) finds `cost.json` manifests under `stacks/` on disk and checks, in each stack directory, that the number of connector modules equals the number of machines listed. Two Spacelift stacks on one directory look like one stack to it, so the second site's $12 would be invisible. The fix, built and documented in `docs/cost.md`, is a **stack instance manifest**: a data-only file at `stacks/sites/<resource_key>/10-access/cost.json` with `"instance_of": "stacks/10-access"`. The gate then:

- prices the instance like any manifest, using the provider of the stack it names;
- requires the instance's machines to equal the base stack's (instances carry no code);
- requires every stack id **declared** in `.spacelift/config.yml` to have exactly one manifest (`config_problems()` in `scripts/cost_check.py`), so a declared stack cannot be added without being costed. The id for the example is `cah-10-access-tor2`;
- optionally reads a `sites` map in `approved.json`, so each site is named in the approval:

```json
"digitalocean": { "approved_monthly_total": 24.0, "active": true,
  "sites": { "tor2": { "approved_monthly_total": 12.0 } } }
```

The gate checks **declared** stacks only. It cannot see a Spacelift stack that someone creates and never lists in `config.yml`, and such a stack is not harmless: if it carries the `cah` label, the context supplies `DOPPLER_TOKEN` to its runs whether or not `config.yml` mentions it (`docs/spacelift-secrets.md` sections 4 and 8). Stack creation, context attachment and the push and run policies have to be controlled in Spacelift; the cost gate does not do that.

**The money.** A DigitalOcean site carries two connectors. At the list price of `s-1vcpu-1gb` in `docs/cost-prices.json` (retrieved 2026-10-10), that is $6 + $6 = $12 per site, so two sites are $24 before any telemetry component, against the $30 shared ceiling in `docs/stages/approved.json`. That leaves $6. The reference environment's planned stage 3 option A is $29 on one site (`docs/cost.md`), so a second site and stage 3 A together are $29 + $12 = $41, which does not fit.

## Predict, then check

1. From the names on the [Twingate page](Twingate.md) (`access-tor1`, `cah-tor1-admins`, `cah-tor1-connector-a-ssh`, `cah-connector-tor1`, `access-tor1-connector-a`), which would collide if two stacks in `tor1` used the default `resource_key`? Does anything stop the second apply?
2. Site one uses `10.78.0.0/24`. The home network uses `10.50.0.0/16` and `10.60.0.0/16`. Which of `10.79.0.0/24`, `10.50.4.0/24` and `10.78.0.0/25` may the second site use, and what must you list in `reserved_ranges` first?
3. You set `site_name = "site-tor1"` on the live stack. What does the plan show? You set `resource_key = "tor1-main"` instead. What does it show?
4. Why is `site` a label and not a job name?
5. Under the one-service-per-site-per-role rule, with a logging service and a scrape service per site, how many services and keys do one site and two sites need? Assume each cloud host holds one key for its site's logging service and the home Prometheus host holds one key per scrape service.
6. You add a second site. What kinds of change are needed beyond the values themselves?

<details>
<summary>Reference answers</summary>

1. Every one of them: all five embed `tor1`. Whether Twingate or DigitalOcean refuses duplicate names is UNVERIFIED in the design, so do not rely on a provider error. Two stacks with equal names would be confusing even where the provider allows them. The fix is a distinct `resource_key` on the new stack.
2. `10.79.0.0/24` only. `10.50.4.0/24` is inside `10.50.0.0/16`, and `10.78.0.0/25` is inside the first site's range. List the first site's range and both home ranges in `reserved_ranges`; the check only knows what you list, so it prompts the human check and does not replace it.
3. `site_name` alone: nothing. No resource, tag or output uses it, so the plan is a no-op. `resource_key`: the Twingate network, group, resources, tag, firewall and both droplets are renamed, and several force new machines. Discard the run.
4. A job names a kind of target. A job per site means every panel and alert that selects the job is rewritten per site and "all sites" is a list to maintain. A label adds one filter and `by (site)` gives the per-site view.
5. One site: 2 services (logging, scrape) and 3 keys (two cloud hosts for logging, one home key for scrape). Two sites: 4 services and 6 keys. This is this page's counting of the design, not a figure the design states. Whether the Twingate plan allows that many services is **not documented** (pricing and Services pages read 2026-10-21, no count per plan); the maintainer reads the limit in the Twingate console (Settings, Billing) before applying stack 20 with more than one site, and nobody assumes a number.
6. Three kinds of change, not three files. (a) **A cost manifest for every new stack id**, including zero-cost ones: `config_problems()` requires exactly one manifest per declared id, so the access instance (`stacks/sites/tor2/10-access/cost.json`) and, later, the foundation instance and the telemetry stack each need one. (b) **The site's settings**: its values, plus the provider's `approved_monthly_total` (and the `sites` map if used) in `docs/stages/approved.json`, and an entry in `.spacelift/config.yml` per new stack id. (c) **The Spacelift and Doppler objects**: the stacks themselves, their label and context attachments, their run policies, and the site's Doppler config and token.

</details>

## Try it yourself

- **No cost.** Copy a stack's `terraform.tfvars.example` to a scratch directory, write the values for a second site, and mark each one public, private or secret using the [decision table](Variables-Tfvars-and-Secrets.md#the-decision-table).
- Work out the ceiling you would need for three DigitalOcean sites with no telemetry components, and say which of the gate's checks would refuse the third if you did not raise it.
- Read `docs/cost.md` "Stack ids and `.spacelift/config.yml`" and write the stack id the rule gives for `stacks/sites/east/aws/10-access`.

Next: [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md). Back to the [Reading order](Reading-Order.md).
