# Clouds Against Humanity: threat-model coverage audit and plan

> **Status: audit and proposal, nothing built.** This document changes no model, test, workflow or stack. It records what the repository holds on 2026-10-22 (main at a11dac2) and proposes work for the maintainer to approve, size and schedule. Anything marked **est.** was not read from a file in this repository.

Request, in the maintainer's words: "Don't forget we need to go over threat modeling for everything in this project too."

Method: read `docs/threat-model/` (three Threat Dragon files, `framework-reference.json`, the Navigator layer), the five threat-modeling lesson pages, `tests/test_threat_dragon_model.py`, `tests/test_threat_frameworks.py` and `tests/test_threat_dragon_layout.py` (test names and headers), the threat or risk section of every spec under `docs/superpowers/specs/`, `docs/stages/01-access.md`, the stack and module directories, the two workflows, `.spacelift/` policies, and the wiki page list. Open branches were listed with `git fetch origin` and compared by file name only: `docs/iac-1` to `docs/iac-4` and `docs/foundations-f1` to `f12` exist; the IaC lessons (PRs #209 to #212) and the web lessons (PRs #216, #217, #219, #220) were added to the inventory from their PR heads, by status line and keyword counts, not read in full. The security tools lessons (S1, S2) are still in flight and are **est.**

The five threat-modeling lesson pages are: [Threat model](../../wiki/Threat-Model.md) (core step 19), [Threat model exercise](../../wiki/Threat-Model-Exercise.md), [Threat Dragon exercise](../../wiki/Threat-Dragon-Exercise.md), [Threat frameworks: STRIDE, ATT&CK, ATLAS](../../wiki/Threat-Frameworks-STRIDE-ATTACK-ATLAS.md) and [Threats in plain words](../../wiki/Threats-in-Plain-Words.md) (foundations F11).

## 1. What exists today

| Asset | What it covers |
|---|---|
| `docs/threat-model/clouds-against-humanity.threat-dragon.json` | One data flow diagram of the **core pipeline**: contributor, CI, source repo, Spacelift proposed and tracked runs, state, Doppler `prd`, cloud API, Twingate, connector droplets, protected resources. Boundaries B1 to B8. 47 threats, T1 to T14 from the wiki page, STRIDE |
| `...attack.threat-dragon.json` | The same diagram, 41 threats rewritten with ATT&CK technique IDs (Repudiation rows dropped on purpose) |
| `...atlas.threat-dragon.json` | A second diagram: AI tools touching the repository (coding agent, hosted reviewer, local model). Boundaries AB1 to AB5. 12 threats, ATLAS IDs |
| `docs/wiki/Threat-Model.md` | T1 to T14 table, accepted risks, and a "What would change the model" section that covers stages 2 and 3 in prose only |
| Design-doc sketches | `edge-dmz` (section 3), `honeypot` (section 4), `peertube-stage` (section 3): assets, actors, trust boundaries, abuse cases, ranked risks each with a mitigation and a verification, residual risk. Not importable, not STRIDE-tagged |
| Risk tables in other specs | stage 2 (section 11), stage 3 (section 9), multicloud (section 9), zero-open-ports (residual risks), stage 1 guide (section 3). Decisions and risks, not threat models |
| Guard tests | `test_threat_dragon_model.py` (structure, boundaries match the exercise page, every T-number modeled, no addresses), `test_threat_frameworks.py` (every cited ID exists in `framework-reference.json`, counts match the wiki), `test_threat_dragon_layout.py` (geometry via `scripts/threat_dragon_layout.py`), `test_attack_navigator_layer.py` |

What the tests cannot do today: they guard the three existing models and their pages. Nothing fails when a new stack, module or lesson family has no model at all.

## 2. Inventory

Column key. **TM?** = has a threat model, and where. **Method**: STRIDE, ATT&CK, ATLAS, AT (attack tree) or "sketch" (the design-doc format: assets, actors, boundaries, abuse cases, ranked risks). **DFD** = a data flow diagram exists (Threat Dragon or drawn). **TB** = trust boundaries named. **Ctrl/Test** = mitigations mapped to a control or a test. **Residual** = residual risk stated. **Reviewed** = date of the last commit touching the file, which is not a review; no file records a review date (see section 5, item 1). "Core" means the model in section 1, row 1.

### 2.1 Stacks and modules

| Component | Status | TM? | Method | DFD | TB | Ctrl/Test | Residual | Reviewed |
|---|---|---|---|---|---|---|---|---|
| `stacks/00-foundation` (project, VPC, baseline firewall) | built | Core: T1, T12 | STRIDE, ATT&CK | in core | B1 | yes: zero-rule firewall tests, `zero_ports_check.py`, `test_ipv6_closed.py` | yes | 2026-10-21 |
| `stacks/10-access` (connectors, groups, SSH resources) | built | Core: T1, T2, T5, T6, T13 | STRIDE, ATT&CK | in core | B1, B8 | partly: tests exist; `metadata_lock` and `host_firewall` built, off, untested on a real droplet | yes (accepted) | 2026-10-21 |
| `stacks/20-telemetry` (cross-site Twingate objects, service accounts) | written, not applied | Prose only: Threat-Model.md "Stage 2"; sketch rows in stage 2 spec section 11; lesson `Telemetry-Crosses-the-Trust-Boundary` | informal | no | named in prose (cloud to home) | partly: `test_telemetry_stack.py` | partly | 2026-10-21 |
| `stacks/aws/00-foundation`, `stacks/aws/10-access` (AWS twin) | written, mock-tested | None. Multicloud spec section 9 has a risk table | none | no | named: per-cloud secret separation (spec section 4) | partly: `test_secret_separation.py`, `test_metrics_firewall_aws.py` | one line | 2026-10-21 |
| `modules/vpc`, `modules/firewall` | built | Core (indirect) | STRIDE | no | no | module tests | no | 2026-10-21 |
| `modules/twingate-connector`, `modules/twingate-bootstrap` (cloud-init, token on disk, Doppler CLI pin, apt key pin) | built | Core: T5, T8, T9 | STRIDE, ATT&CK | in core (as "Connector droplets") | no module-level boundary (guest versus metadata endpoint is prose) | partly: `test_metadata_lock_script.py`, `test_host_firewall_script.py`, `test_node_exporter_script.py`, `test_log_shipping_*` | partly | 2026-10-21 |
| `modules/aws/*` (vpc, firewall, twingate-connector) | written, mock-tested | None | none | no | no | `test_module_contract.py`, `test_module_policy.py` | no | 2026-10-21 |
| `modules/docker-host`, `stacks/30-workloads` (stage 3) | planned (named in stage 3 spec section 9a), no code | Prose only: Threat-Model.md "Stage 3"; spec risks 4 to 6 | informal | no | partly (Portainer socket) | no | partly | 2026-10-21 |
| `stacks/50-edge` | planned (design merged, rulings 2026-10-19), no code | Sketch: edge spec section 3 | sketch | ASCII architecture in section 4 | yes, 5 named | yes: each risk has a verification, several are proposed tests | yes (3.6) | 2026-10-21 |
| Honeypot host (separate account) | planned (design merged), no repo code applied | Sketch: honeypot spec section 4 | sketch | est. (not read) | yes, 7 named | yes: 11 risks each with a verification | yes (4.6) | 2026-10-21 |
| PeerTube stage | planned, design only, recommended off by default | Sketch: peertube spec section 3 | sketch | est. | yes, 6 named | yes, with "not testable" calendar items marked | yes (3.6) | 2026-10-21 |
| Azure and GCP modules | planned, mocked tests only | None | none | no | no | no | no | not started |

### 2.2 Stages

| Stage | Status | TM? | Notes |
|---|---|---|---|
| 0 foundation, 1 access | built | Core | Guide `docs/stages/01-access.md` section 3 holds accepted residual risk; it duplicates, not links, Threat-Model.md |
| 2 logging and link home | designed, cloud side written, not applied | Prose and spec table only | The cloud-to-home path is the highest-value boundary the project will add (Threat-Model.md says so) and has no diagram and no T-numbers |
| 3 workloads | planned | Prose only | See stacks table |
| 4 Grafana (on-prem) | planned | None | Home side; est. |
| edge, second-site, learner-soc, aws-twin phases | planned | Edge: sketch; others none | `approved.json` phases carry cost reasons, not threat references |

### 2.3 Lesson families

A lesson that teaches a mechanism should name the boundary the mechanism guards. Only lessons about the model itself do so today.

| Family | TM? | Notes |
|---|---|---|
| Threat modeling set (5 pages above) | Yes, they are the method | Guarded by the tests in section 1 |
| Core path (Build-It-From-Zero, Twingate, Doppler-and-Secrets, Spacelift, Droplet-Hardening, CI-Tests-and-Cost-Gate, Fork-Private-Stacks) | Link to Threat-Model.md, 1 to 3 mentions each | `Doppler-and-Secrets` has no mention of "threat model" or "trust boundary" (grep count 0) |
| Telemetry (`Telemetry-Crosses-the-Trust-Boundary`, `Cloud-Telemetry-What-and-Why`, `Build-Your-Own-Mini-SOC`, `Stage-2-Home-Side-Runbook`) | The first has a boundary section; the others link or are silent | Mini SOC names a boundary once and states no residual risk (count 0) |
| Foundations F1 to F12 (branches and main) | F11 is the threat vocabulary page. F1 to F10, F12 are not models and need none, but F5 (subnets, NAT, firewall), F4 (crypto), F7 (identity), F9 (logs) and F10 (backups) each teach one boundary | Audit of the F-pages themselves is est.: only F11, F10 and F12 are on main; the rest were not opened |
| Deception and honeypots (8 pages on main: the Start-Here hub, five short lessons (What-Deception-Is, Safety-and-Law, Plant-a-Canary, Honeyfiles, Alerts-in-the-SIEM) and two on-premises pages (Design-a-Honeynet, T-Pot-at-Home)) | The design spec has a sketch; the lesson pages mention "threat model" 0 to 2 times each and never "trust boundary" or "residual" (counts read) | `Design-a-Honeynet` and `T-Pot-at-Home` teach a hostile-by-design host and are the highest-risk lessons in the set |
| Provider lessons (AWS, Azure, GCP: preparation, cost, same four pieces) | Two of the "Same four pieces" pages mention a threat model once or twice | No provider page states what an account boundary protects |
| IaC lessons I1 to I4 (open PRs #210 OpenTofu from zero, #212 plans, state, drift and recovery, #209 Spacelift from zero, #211 build and destroy a stack per service) | Not merged. Opened by head fetch and checked by status line and keyword counts only, **not read in full**. Keyword counts for "threat model", "trust boundary", "residual": I1 0/0/0, I2 0/0/0, I3 0/1/0, I4 0/0/0. None states a threat model or residual risk | I3 and I4 teach the Spacelift-to-cloud and state boundaries; state holds connector tokens (T6), so I2 (state) and I4 belong in TM-9 |
| Web lessons W1 to W4 (open PRs #216 LAMP and LEMP from zero, #217 DNS, Cloudflare and hosting your own website, #219 WordPress and PHP security, WAF and static sites, #220 WordPress at scale: CDN, WAF and CI) | Not merged. Opened by head fetch and checked by status line and keyword counts only, **not read in full**. Counts for "threat model" / "trust boundary" / "residual": #216 5/6/1, #217 1/4/0, #219 5/2/5, #220 3/4/0. These four are the only lessons that already use the vocabulary; #219 also states residual risk. Whether each boundary matches a component model is not checked | The most exposed topic family (internet-facing). The CDN or WAF to origin boundary in section 7 is taught here (#217, #220), so TM-9 for W1 to W4 is a review of existing text, not new text |
| Labs and demo monitoring (`labs/demo-monitoring`, `Labs-Break-It-on-Purpose`) | Labs mention threats (Labs: 1 grep hit) | Not read in depth; est. |
| Pi connectors lesson | Not found: `Zero-Trust-at-Home-Two-Connectors-and-Failover` is the nearest page; no Pi-specific connector lesson is in the repository. Status est. | A home connector on a small board is a boundary lesson in waiting |

### 2.4 Cross-cutting systems

| System | TM? | Where | Gap in one line |
|---|---|---|---|
| CI and GYST callers (`ci.yml`: tofu, python, security, `CI green`) | Yes | Core T7 (pinned actions, `permissions: {}`) | The reusable workflows are third-party code at a pinned commit; the pin is the only control and one line (T7) covers it |
| Wiki publishing path (`wiki.yml` calls a GYST `wiki-publish` workflow) | No | none | The path writes to a repository that is not this one; the token and its scope were not read (est.) |
| Spacelift (stacks, contexts, push and plan policies) | Yes, in part | Core T3, T6, T10; `.spacelift/policies/*.rego` with tests | The policy copy in the repo is only as current as the last paste into Spacelift (accepted risk 5); contexts per cloud have a test, but no model |
| Doppler (prd config, service tokens, bootstrap tokens) | Yes, in part | Core T4 (one row), T8 | No DFD of who holds which token: Spacelift run, host first boot, edge bootstrap token, daemons, honeypot write key are all separate secret paths |
| Twingate (controller, relays, connectors, headless client, service accounts) | Yes, in part | Core T2, T9, T10; B8 | The service-account and headless-client paths (stage 2, edge) are not diagrammed |
| DigitalOcean (account, team, billing, tokens, Spaces keys) | Yes, in part | Core T11; honeypot and edge specs argue for account separation | "An abuse report against one workload can touch the whole team" is stated twice in specs and nowhere in the model |
| Cost gate (`cost_check.py`, `approved.json`) | Yes | Core T11 | Metered use is outside the gate; accepted |
| AI tools (agent, hosted reviewer, local model) | Yes | ATLAS model, AB1 to AB5 | Does not include the local-model triage and bot-style text pipelines planned for the SIEM (est.) |
| Public-repo identifier leakage | Yes | Core T14; `identifier_check.py`, `test_threat_dragon_model.py` no-addresses test | Strong; keep |
| Planned edge services (rnsd/lxmd, i2pd, MQTT broker, iperf3) | Sketch | Edge spec | Five internet-facing daemons, one risk row each at most |
| Honeypot sensors | Sketch | Honeypot spec | Logs are attacker-chosen strings fed to a SIEM (risk 5 there) |
| Stage 3 daemons (five social and announcement bots, Portainer, Spaces keys, Functions) | Prose only | Threat-Model.md, stage 3 spec risks | They hold API tokens for the maintainer's public accounts; a host compromise posts as him |
| Home side (home connectors, pfSense backstop, SIEM, log relay) | Prose | Stage 2 spec 11, edge spec 4.6.1 | Out of the public repo's control; the repo should still state the assumption |

## 3. Gaps ranked by exposure

Ranking rule: internet-facing and secret-holding first, then what a compromise reaches, then how little is written.

| Rank | Gap | Why it ranks here |
|---|---|---|
| 1 | Edge (`50-edge`): five public daemons, reserved IP, Twingate headless key, bootstrap token in user-data | The only planned thing that accepts inbound from the internet in the core account's team. A sketch exists and is good, but it is not in a Threat Dragon file, has no STRIDE or ATT&CK pass, and the "no peering" and "one group resource" tests it proposes are not written |
| 2 | Stage 2 cloud-to-home link (headless client, two service accounts, home connector, log relay) | Turns a cheap droplet into a path home. Prose only; the relay is a boundary of its own and is a prerequisite in the edge spec, not a modeled element |
| 3 | Stage 3 workload host: Portainer (Docker socket is root), five daemons with public-account tokens, Spaces keys | Secret-holding, outbound-only (the Discord-to-Matrix bridge is hosted by etke.cc and is not part of this project, #254). Prose only |
| 4 | Secret flows across Doppler, Spacelift contexts, host first boot and the AWS twin | Secret-holding. T4 is one row; the multicloud, edge, honeypot and stage 3 designs each add a path. No DFD names who can read which secret |
| 5 | PeerTube (public uploads, federation, bucket key, takedown duty) and honeypot (hostile host, write key, separate account) | Both internet-facing by design. Both have a sketch. Both are off by default, which is why they rank below 1 to 4 |
| 6 | Wiki publishing and GYST reusable-workflow trust | Writes to a published surface under a token; no model |
| 7 | AWS twin and the cloud API boundary (Spacelift to AWS, short-lived integration versus static key) | Decision 6 of the multicloud spec defers a static key; the model is absent |
| 8 | Modules (`twingate-bootstrap` first) | Trust boundary is the metadata endpoint; the controls exist and are tested but no module-level element lists them |
| 9 | Lessons: deception Track 2/3 pages, provider pages, IaC I3 and I4, web W1 to W4 | Teach exposure; none state the boundary they guard |
| 10 | Review dates and ownership | Nothing records when a model was last read by a human or who owns it |

## 4. Standard per-component template

Goal: one shape for every component, matching the Threat Dragon files and framework tests so a sketch can be promoted to a file without rewriting. Where a field maps to the JSON, the mapping is given.

```
Component:        <name>, kind (stack | module | stage | lesson family | system)
Status:           built | written, not applied | designed | planned  (matches Roadmap wording)
Owner:            maintainer | agent name or role   (est. for unassigned)
Model file:       docs/threat-model/<component>.threat-dragon.json   (or "covered by <file>, rows T..")
Methods used:     STRIDE (default); ATT&CK and/or ATLAS if applicable; attack tree for one named goal
Last reviewed:    YYYY-MM-DD by <who>      Review trigger: <event list>
```

Sections, in order:

1. **Scope and non-goals.** What the model covers; what it excludes. State "no active probing; verification runs only against resources the operator owns, in a window, with a stop condition" (as the three sketches already do).
2. **Assets.** Table: asset, why it matters. Maps to `tm.Store` elements and credentials held by `tm.Process` elements.
3. **Actors.** Table: actor, capability. Maps to `tm.Actor`. Include the pull-request author and the supply chain as standing rows.
4. **Trust boundaries.** Table: boundary id, rule. Maps to `tm.BoundaryBox`. Ids: core uses B1 to B8 and the AI model uses AB1 to AB5; a component model uses its own prefix (proposal: `E` edge, `H` honeypot, `P` PeerTube, `W` workloads, `L` home link, `S` secrets) so ids never collide, and `test_threat_dragon_model.py`-style checks stay per file.
5. **Data flows.** One row per flow: source, destination, data, protocol, boundary crossed. Maps to `tm.Flow`. Flows are unidirectional (existing test); a two-way link is two flows.
6. **STRIDE table.** One row per element per applicable category, status `Open`, `Mitigated` or `NotApplicable`, severity `High`, `Medium` or `Low`. Maps to the `threats` array: `id`, `number`, `status`, `severity`, `title`, `type` (one of the six STRIDE names), `modelType` ("STRIDE"), `description`, `mitigation`. Threats attach to elements, not boundaries (existing test).
7. **Abuse cases.** Numbered stories (as in the three sketches); each links to at least one STRIDE row.
8. **Mitigations with a verification.** Table: risk, control, verification kind, verification pointer. Verification kind is one of: **test** (file and test name), **policy test** (rego), **cost gate**, **runbook check** (read-only command, marked "not run yet" until run), **calendar item** (for things that cannot be tested, marked as such). A mitigation with no verification is written as "unverified" and stays `Open`.
9. **Residual risk.** What remains and who accepted it. Accepted risks stay `Open` and say so (existing `test_accepted_risks_stay_open_and_say_so`).
10. **Framework mapping (optional).** ATT&CK IDs or ATLAS IDs that exist in `framework-reference.json`, copied to a sibling file the way the ATT&CK model copies the STRIDE one.
11. **Review trigger.** Any of: a new inbound port or public hostname; a new credential type or holder; a new third-party service in the path; a provider or plan change; an incident; a change to the component's firewall, cloud-init or policy file; six months since the last review.

Rules carried from the existing models: generic names only, no IP addresses (not even documentation ranges: the existing `test_no_addresses_or_private_identifiers` and `test_no_addresses_urls_or_private_identifiers` reject every IPv4 and IPv6 literal, so write "the reserved IP" or a name) and no account identifiers, no secret-shaped literals, untrusted data is evidence and never instruction, American spelling.

## 5. Proposed test: a stack or lesson family with no threat-model entry fails CI

Described only; not written.

**Registry.** New file `docs/threat-model/coverage.json`, a list of entries `{"component": "...", "kind": "stack|module|stage|lessons|system", "path_globs": [...], "phase_ids": [...] (optional), "model": "docs/threat-model/<file>" or "spec": "<spec path>#<section>", "status": "modeled|sketch|exempt", "exempt_reason": "...", "last_reviewed": "YYYY-MM-DD", "owner": "..."}`. Everything in section 2 becomes a row.

**New test file.** `tests/test_threat_coverage.py`, which would read:

1. `stacks/*/` and `stacks/aws/*/` (directories containing `main.tf`) and `modules/*/` and `modules/aws/*/` (directories containing `main.tf`): each must match a registry `path_globs` entry.
2. `docs/wiki/*.md`, grouped into lesson families by filename prefix: `Deception-and-Honeypots-`, `Provider-`, `Threat`, plus the families named in `docs/wiki/Reading-Order.md`. A new prefix that matches no registry entry fails.
3. `docs/stages/approved.json` phase ids: each key under `phases` must appear in exactly one entry's `phase_ids` (an entry that has `phase_ids` and no `path_globs` is allowed; `approved.json` is never used as a path, so the exactly-one rule for paths is not affected). This catches a new phase such as a future `edge` or `second-site` build with no model).
4. `docs/threat-model/*.threat-dragon.json`: an entry whose `status` is `modeled` must name a file that exists and whose diagram has at least one `tm.BoundaryBox` and one threat.
5. `docs/superpowers/specs/*-design.md`: any spec that has a "Threat model" heading must be registered with `status: sketch` or higher.
6. `.github/workflows/*.yml` and `.spacelift/policies/*.rego`: each must be matched by a `system` entry.

**Assertions.**

- Every path found in 1 to 6 (including every Threat Dragon file from 4 and every design spec with a threat-model heading from 5) is covered by exactly one entry or a fully reasoned `exempt` (non-empty reason, at most a small set, listed in the test as an allowlist that a reviewer sees in the diff).
- A `modeled` entry's file exists and passes the existing structure tests (the structure and framework tests glob `docs/threat-model/*.threat-dragon.json`). `tests/test_threat_dragon_layout.py` also asserts the on-disk model set equals `LAYOUTS` in `scripts/threat_dragon_layout.py` and regenerates each file from its layout, so every new model needs a `LAYOUTS` entry in the same pull request, and the model must satisfy the geometry checks.
- `last_reviewed` is a valid date no later than today and, for `modeled`, within 180 days (the six-month trigger; the day count is a proposal).
- Every `sketch` entry's `spec` path exists and its heading anchor resolves (reuse the anchor logic in `tests/test_markdown_anchors.py`).
- The registry has no entry whose paths match nothing (stale rows fail).

**Failure message** names the new path and says: add a registry row, then a model or a sketch.

**Limit, stated in the test docstring** (as the framework test's docstring does): it proves a model is registered and well formed, not that it is correct or complete.

## 6. Work items

Sizes per [How this project is planned](../../wiki/How-This-Project-Is-Planned.md): S about 2 h, M about 5 h, L about 12 h, XL split first. Sprints are the [Roadmap](../../wiki/Roadmap.md) sprints: S1 2026-10-20, S2 2026-11-03, S3 2026-11-17, S4 2026-12-01, S5 2026-12-15, S6 2026-12-29, S7 2027-01-12, S8 2027-01-26. S1 and S2 are the maintainer's busiest sprints, so these are agent items with the maintainer reading the result; at most three agent items run at once. Security-sensitive models get a second, adversarial read by an agent that did not write them (Definition of done, item 5).

| # | Item | Size | Sprint | Depends on | Done when |
|---|---|---|---|---|---|
| TM-0 | Template as `docs/threat-model/TEMPLATE.md` plus an empty `coverage.json` filled from section 2 | S | S2 | this audit approved | Registry lists every row of section 2 with a status; template reviewed |
| TM-1 | `tests/test_threat_coverage.py` (section 5) | M | S2 | TM-0 | Test fails on a fixture stack with no entry (shown failing), passes on main |
| TM-2 | Secrets and identity flows model (Doppler, Spacelift contexts, host first boot, bootstrap tokens): new Threat Dragon file `S` boundaries, STRIDE | M | S2 | TM-0 | Every token in `docs/spacelift-secrets.md` section 2 appears as a store or flow; each has a verification or is marked unverified |
| TM-3 | Stage 2 cloud-to-home link model (`L` boundaries): headless client, two service accounts, home connector, log relay | M | S2 | TM-0; stage 2 spec | In place before the first apply of `20-telemetry`; relay prerequisites from edge spec 4.6.1 appear as elements |
| TM-4 | Edge model: promote edge spec section 3 to a Threat Dragon file with STRIDE rows (`E` boundaries); write down the two proposed tests as items, not code | M | S2 | edge design approved (S2 planned review) | Model exists before the edge stack is built (DMZ stack is S6, flag off); second agent read |
| TM-5 | Stage 3 workloads model (`W` boundaries): Portainer socket, daemon tokens, Spaces keys | L | S3 | stage 3 cost approval (S3) | Exists before the workload stack lands flag-off in S4 |
| TM-6 | Core model update: wiki publishing path, GYST reusable workflows, AWS twin cloud API boundary; add T15 onward and sync the wiki table, ATT&CK copy and counts | M | S3 | TM-1 | `test_wiki_page_counts_match_the_models` style tests green; T-numbers continue from T14 |
| TM-7 | Honeypot model (`H` boundaries) from honeypot spec section 4; link from the deception safety lesson | M | S3 | honeypot design approved | Lesson Track 2 and 3 pages cite the model before they ship hands-on steps |
| TM-8 | PeerTube model, only if the maintainer chooses to proceed | M | S5 (est.) | decision on the PeerTube stage | Skipped and recorded as `exempt: not built, off by default` if the stage is not approved |
| TM-9 | Add a "boundary this guards" paragraph to lesson families, one item per family: Doppler, Twingate, Spacelift, telemetry, deception, provider, IaC I1 to I4, web W1 to W4, foundations (F4, F5, F7, F9, F10) | S each, about 8 items | S4 to S7 | TM-0; I and W lessons merged | Each lesson links its model row; wiki tests green |
| TM-10 | Review cadence: `last_reviewed` and owner in the registry; a note in the stage guides' "Definition of done" that a boundary change updates the model | S | S3 | TM-1 | Documented in How-This-Project-Is-Planned.md; test checks the date |
| TM-11 | ATLAS model update for local-model triage of logs and issues | S | S4 | SIEM triage plans | New AI element and rows; counts synced |
| TM-12 | Azure and GCP module models | M | S8 | modules exist | Done with the modules, mocked tests only; labeled unverified like the lessons |

Every new Threat Dragon model (TM-2 to TM-8) also needs its `LAYOUTS` entry in `scripts/threat_dragon_layout.py`, which adds about an hour to each; the sizes above include it.

Rough load: TM-0 to TM-4 about 22 h of agent time in S2, split across three agents is too much for one sprint, so TM-3 and TM-4 may slip to S3; TM-5 (L) is the biggest single item. S1 holds no items.

## 7. Trust boundaries are the unifying idea

Every control in this repository is a decision about a boundary: who may cross it, carrying what, and what happens when a thing on the far side is compromised. The lessons repeat the same questions in different clothes, and a model is the place to ask them once per boundary.

The clearest example is the planned edge. A public relay (the Reticulum transport) and a message router (the LXMF propagation node) can look like one program on one droplet. They are not one thing: one faces strangers and relays traffic it does not understand, the other stores messages for identities it does. The edge design puts them in a separate VPC with no peering, no shared tag, no shared Doppler config and no admin path, and the honeypot goes a step further into a separate account with a separate login and payment method. Separate stacks and separate identities exist because the boundary between a public relay and a message router, and between either and the core, is a trust boundary: if the relay is owned, the blast radius ends where the identity ends. The lxmd-and-Reticulum split is the lesson in miniature; the stack layout is the answer to it.

The same question appears elsewhere:

- **Twingate connectors.** Connectors dial out, so there is no inbound edge to defend (B1); the controller and the identity provider decide who may ask for a resource (B8); a stolen identity still needs the host key. Two connectors are a boundary against lockout as well as against attack.
- **Spacelift to the cloud.** A proposed run is not given the named provider secrets, because the hook skips the fetch, but the `cah-doppler` context is attached to every run type, so `DOPPLER_TOKEN` is present and branch-controlled hook code could read it (`docs/spacelift-secrets.md` section 3); a tracked run on `main` fetches the secrets, and a human confirms apply (B3, B5, B7). The push policy keeps pull requests from crossing at all. Per cloud, the Doppler config and the Spacelift context are separate so that one tracked run does not reach every control plane.
- **Doppler to the host.** The secret store is a boundary with the host's disk and with the metadata endpoint. The token is read-only, one config, expiring; the bootstrap token that must exist in user-data is the one place the boundary leaks, and the design says so (T5, edge risk 6).
- **CDN or WAF to origin** (est.; no CDN is planned in the repository). If one is ever added in front of the edge or PeerTube, the origin must accept traffic only from it, or the filter is a suggestion. That is the web lessons' version of the same question and belongs in W1 to W4.
- **The cloud-to-home link.** Stage 2 adds a boundary the repository does not own: the home connector, its VLAN and the log relay. The model should state the assumption, because the public repository cannot test the far side.
- **Account to account.** A provider acts on an account. The honeypot and the edge both separate accounts so that an abuse report lands where nothing else lives.

Teaching consequence: each lesson in TM-9 ends with the same three sentences: which boundary this guards, what crosses it, what is left over. A learner who can answer those for the Twingate connector can answer them for a CDN.

## 8. Questions for the maintainer

1. Is the core model to be extended (T15 onward) or should each component get its own file with its own boundary prefix? The audit assumes separate files; the exercise page teaches one diagram.
2. Should specs with a sketch keep it, or should the sketch move into the Threat Dragon file and the spec link to it?
3. Is a six-month review window right for models of things that are not built yet, or should "designed" models be reviewed at each stage approval instead?
4. Should the registry in section 5 live in `docs/threat-model/` or alongside `docs/stages/approved.json`, so a stage cannot become current without a model?
5. Are the stage 3 daemons' tokens (public accounts) in scope for a public model, or should only the pattern be written?
6. Which of the unread items should an agent read next: the IaC branches, the foundations pages F1 to F9, the web lessons once they exist?
