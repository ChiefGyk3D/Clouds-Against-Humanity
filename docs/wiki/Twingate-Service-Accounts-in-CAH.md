# Twingate service accounts in CAH

Side page to [Twingate](Twingate.md). Read it when you want to know where this project uses a Twingate service account, what one is, and which Twingate plan each use needs. Next: [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from the repository and from Twingate's own pages, read on 2026-10-22; nothing here was run against a Twingate account.** The repository side was read from the code and the tests. The vendor side was read with a plain `curl` of Twingate's public pages and of the Terraform provider's documentation. Every claim is in the [claims register](#claims-register) with its address and date. Where Twingate says nothing, this page says so and gives no number. The service accounts the repository defines are **not applied** and the headless client that would use them is **not built**.

> **Prerequisites.** [Twingate](Twingate.md) (what a connector, a resource and a remote network are) and [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md#service-accounts-and-personal-tokens) (why a program gets its own identity). About 45 minutes for the free exercises (est.).

## What you will be able to do

- Say what a Twingate service account, a service key and a headless client are, and how each differs from a user, a device and a connector.
- Name the four places this repository defines a service account, what each is for, and who would hold its key.
- Say which Twingate plans list service accounts, using the vendor's own pages, and which question Twingate leaves unanswered.
- Say which stages and exercises of this project still work on the free Starter plan, and which do not.

## The short answer

| Question | Answer | Where it comes from |
|---|---|---|
| Does the free Starter plan include service accounts? | **No.** In the pricing page's comparison table the "Secure service accounts" row has no mark under Starter. | [Twingate pricing](https://www.twingate.com/pricing), 2026-10-22 |
| Which plans list them? | **Home, Business and Enterprise.** Teams does not. | The same table |
| Does Twingate's documentation agree? | **Not fully.** One documentation page says "Business and Enterprise", and does not mention Home. The pricing page lists Home too. | [Linux userspace networking](https://www.twingate.com/docs/linux-userspace-networking), 2026-10-22 |
| How many may a plan hold? | **Twingate does not say** on any page read. This repository gives no number. | [Claims register](#claims-register) |
| Does every stage need one? | **No.** Stages 0 and 1 do not. Only the optional cloud-to-home paths of stage 2 and later do. | [Where the repository uses them](#where-the-repository-uses-them) |

The SAML point is a separate matter. The maintainer's own lab signs in through an identity provider using SAML, and he states the free plan does not include that. No Twingate page read for this page contains the word SAML, so that one stays his statement, not a vendor-confirmed fact ([Enterprise identity](Enterprise-Identity-SSO-SAML-OIDC.md) says the same).

## What a service account is

A **user** is a person. A **device** is the laptop or phone that person signs in from. A **connector** is a small program inside your network that carries traffic out to Twingate; it is part of the infrastructure, and it never signs in as a person. A **service account** is a fourth thing: an identity for a program, so that an unattended job can be given access to a few resources without borrowing a person's login.

Twingate's own words, from its Services page:

- "Services offer a way to provide programmatic, centrally-controlled, and consistent access controls for automated processes such as CI/CD pipelines and custom applications."
- "Security Policies do not apply to Services, and instead, access is granted by a valid Service Key."

Twingate's documentation calls the object a **Service** on one page and a **Service Account** on others, and its Terraform provider calls it `twingate_service_account`. They are the same thing in this page.

The pieces:

| Piece | What it is | What Twingate says |
|---|---|---|
| **Service account** | The container. You give it a name and assign resources to it. | A resource "may be assigned directly to a Service" |
| **Service key** | The credential. It is a file; whoever holds a valid one acts as the service account. | "Any Service Key authorizes access to all Resources assigned to the Service." |
| **Headless client** | The ordinary Twingate client for Linux or Windows, started without a person to sign in, using a service key. | "Headless mode is accessed by passing a --headless parameter to the twingate setup command with the path to a valid Service Key specified." |

Three consequences follow, and the repository's design depends on each:

1. **A service key reaches everything its service account has.** There is no narrower key. That is why this project makes one service account per site per role and gives each only its own resources, so a stolen key reaches a small set.
2. **The usual sign-in rules do not apply.** The Services page says security policies "do not apply to Services". There is no person to ask for a second factor, so the key is the whole defense.
3. **The key is a secret like any other.** The Services page says of a new key: "This is the only time that the Service Key can be viewed and copied." Store it in a secrets manager the moment it is shown.

### Key lifetime and revocation

From the Services page:

- "Service Key expiration can be configured at creation time and expire after 365 days by default."
- "Service Key expiry can only be set at creation time; unlimited expiration is allowed."
- "Service Keys must be revoked before they are deleted." and "Once revoked, keys cannot be made active again."
- A deleted key is "permanently deleted and cannot be recovered".
- "Every Service Key on a Service Account is individually API rate-limited", so Twingate advises a unique key for each high-traffic system.

One wrinkle. The Terraform provider's documentation for `twingate_service_account_key` says its `expiration_time` "Defaults to 0, meaning the key will never expire", while the console page says 365 days by default. Both were read on 2026-10-22; the provider text is from the project's `main` branch, and the registry listed version 5.2.0 that day. This repository does not create keys with the provider (next section), so the difference does not bite here, but if you ever do, set the expiry yourself.

### Which plans, according to Twingate

On the [pricing page](https://www.twingate.com/pricing), read 2026-10-22:

- The **Starter** card says "Free" and "Up to 5 users". The card does not list service accounts.
- The **Home** card says "Everything in Starter, plus:" and lists "Secure Service Accounts", "Up to 7 users", and "Limited to non-commercial use". Its price is shown as "$15 per month", with a 14-day trial button.
- The **Teams** card does not list them.
- The **Business** card lists "Secure service accounts", as does the Enterprise tier above it.
- The comparison table, in the Automation group, has a row "Secure service accounts" described as "Accounts used by machines to securely access privileged resources required by unattended tasks and automated processes like CI/CD pipelines". Read from the page's markup, the row has a mark under Home, Business and Enterprise and none under Starter or Teams. The marks are drawn in the browser, so **open the page and look at the row yourself** before you decide anything; a plain `curl` cannot show them.

Other rows that matter here, from the same table: the Terraform and Pulumi providers and the admin API are marked on every plan including Starter, so stage 1 (which uses the provider) works on the free plan. Social login (Google, Microsoft, GitHub, LinkedIn) is marked on every plan. Sign-in through a company identity provider such as Okta or Microsoft Entra ID is marked from Business up, and Google Workspace on every plan.

Where Twingate is silent or inconsistent:

- **The count.** No page read states how many service accounts any plan may hold. The older stage 2 guidance said so too, and it still stands.
- **The Home plan in the documentation.** The Linux userspace networking page says "Service accounts are available for Business and Enterprise plan customers". The pricing page lists Home as well. Both were read on 2026-10-22. This page follows the pricing page for the plan list and marks the disagreement; ask Twingate, or read your own account's plan page, before you buy anything on the strength of one reading.
- **Whether a service account counts against a plan's user cap.** The subscription page says "Twingate licenses are based on your total number of Users and Service Accounts" and lists "Service Accounts, regardless of how many Service Keys they have or whether those keys are active" as counting. It does not say whether the cap of 5 or 7 users includes them. Do not assume either way.
- **What happens if you try on Starter.** Whether the console hides the button, the API refuses, or something else, no page says. This page did not try it.

## Where the repository uses them

I searched `stacks/`, `modules/`, `docs/` and `tests/` for `service_account`, "service account", "service key" and "headless". Code defines service accounts in exactly one file: `stacks/20-telemetry/main.tf`. Everything else is documentation, designs and tests.

### Defined in code (four resources, all off by default)

| Resource | Switch | Name | What it is for | What it can reach | Who holds the key | Built? |
|---|---|---|---|---|---|---|
| `twingate_service_account.logging` | `logging_enabled` | `telemetry-<resource_key>-logging` | Lets each cloud connector host's log agent reach the home log collector | Only the logging resources, one per endpoint and port you list in `logging_servers`, in the home remote network. The design names the manager's ports 1514 and 1515 | One key per cloud host, issued by hand, kept in that site's first-boot secrets config in Doppler | Service account: code merged, **not applied**. Headless client on the cloud hosts: **not built** |
| `twingate_service_account.scrape` | `metrics_enabled` | `telemetry-<resource_key>-scrape` | Lets the home Prometheus pull metrics from the cloud connectors | Only the scrape resources, one per `scrape_allowlist` entry per connector, in the cloud remote network (the node exporter port and the connector metrics port) | The maintainer, on the home Prometheus host | Service account: code merged, **not applied**. Headless client on the Prometheus host: **not done** (a home-side step) |
| `twingate_service_account.site_logging` | `logging_enabled` plus an entry in `sites` | `telemetry-<site key>-logging` | The same as `logging`, for each extra site | Only that site's logging resources | One key per cloud host of that site | Same status as `logging` |
| `twingate_service_account.site_scrape` | `metrics_enabled` plus an entry in `sites` | `telemetry-<site key>-scrape` | The same as `scrape`, for each extra site | Only that site's scrape resources | The home Prometheus host | Same status as `scrape` |

Facts about all four:

- **Off by default.** Both switches default to `false`, and a mock-provider test asserts that with the defaults no service account and no Twingate resource is planned (`stacks/20-telemetry/tests/telemetry.tftest.hcl`). A learner who never turns a switch on never needs a service account.
- **No keys in code.** The stack creates the service accounts and their resource grants only. A test, `test_no_service_key_is_created` in `tests/test_telemetry_stack.py`, fails if `twingate_service_account_key` ever appears in the stack. Keys are issued by hand in the Twingate console, one per host, so no key is ever in OpenTofu state.
- **Even one site makes two.** With both switches on, one site has two service accounts (logging and scrape). Each extra site adds two more.
- **The headless client is the missing half.** The stage guide says "The Twingate headless client is NOT included". Until it exists, an enabled log agent cannot connect and, by design, stays off. See [the stage 2 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md) and the [home-side runbook, section 4](Stage-2-Home-Side-Runbook.md#4-the-headless-client-on-the-prometheus-host).
- **Nothing is applied.** Stage 2 has not been applied to a real account; the [Roadmap](Roadmap.md) says so.

### Described in designs only (no code)

| Where | Use | Status |
|---|---|---|
| [Build your own mini SOC](Build-Your-Own-Mini-SOC.md), stage N2 | The home Prometheus pushes filtered metrics to a cloud Prometheus; the receiver's resource is granted to the home Prometheus's service | Design only |
| Stage 3 workloads design | A headless client on the workload droplet so the daemons can reach a home Ollama server. The design says that until it exists the daemons run with the language-model feature off or on Gemini | Design only |
| Edge (DMZ) design, log option A | A headless client on the public edge host with one resource: the ingest port on a home relay. Option B, no log path home at first, needs none | Design only |

None of these has code. All of them have the same shape as stage 2: a host that cannot sign in as a person, given a narrow key.

### What does not use one

Stage 0 (foundation) and stage 1 (access: the remote network, two connectors, a group and the resources) define no service account. Connectors are not service accounts; each connector has its own access and refresh tokens, a different credential ([Twingate: the connector tokens](Twingate.md#accepted-risk-the-connector-tokens)).

## What this means on the free plan

| Part of the project | Needs a service account? | On the free Starter plan |
|---|---|---|
| Reading every page, and the [free exercises](#hands-on-free-exercises) below | No | Works. No Twingate account is needed |
| Stage 0, foundation | No | Works (no Twingate objects) |
| Stage 1, access: connectors, groups, resources | No | Works. The provider and API are marked on Starter. Starter's limits on the pricing page (5 users, 10 remote networks, 50 resources) look far above what stage 1 uses (est.) |
| Stage 2 with both switches `false`; `tofu plan` as a no-op; the mock-provider tests | No | Works |
| Stage 2 switches on: logs from the cloud to a home SIEM, metrics pulled by a home Prometheus | **Yes** | **Does not work** on Starter, by the pricing page. Needs a plan that lists service accounts (Home, Business or Enterprise), on your own bill |
| Mini SOC N1: a cloud Grafana you reach as yourself through Twingate | No (you sign in as a user) | Should work (est.): it uses a user and one resource, not a service account |
| Mini SOC N2: push from home to the cloud | Yes | Does not work on Starter |
| Stage 3 daemons using a home model | Yes | Does not work; run the daemons without the feature or with Gemini, as the design says |
| Sign-in through your own SAML identity provider | No | Not on the free plan, per the maintainer (the vendor pages read here do not use the word SAML). Use social login |

**The free theory path.** Everything about the idea is free: this page, [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md), the [threat model](Threat-Model.md), the repository's tests and the exercises below. You can learn what a service account is, why one per role, and how a stolen key is limited, without owning one.

**A workaround that stays inside the repository's own text.** The [mini SOC page](Build-Your-Own-Mini-SOC.md) offers a lab collector in the same cloud site, so nothing needs a path home and no service account is involved (N1, and S1 forwarding to a collector in the same site). I have not run it, and whether it fits your droplet size and budget is an estimate to check (est.). It teaches the monitoring half, not the cross-boundary half.

**What I would not do** (est., my opinion, not tested): put a person's own sign-in on a server so it can reach a resource without a service account. It avoids the plan question by putting a human credential on an unattended machine, which is the problem a service account exists to solve.

## Hands-on: free exercises

None of these needs a Twingate account or any money. They read this repository and Twingate's public pages. Commands marked est. were not run in PowerShell; the Bash ones were run on 2026-10-22.

### Exercise 1: list every service account the code defines

**Predict.** How many `twingate_service_account` resources are there, and in how many files?

**Do.** From the repository root.

Bash:

```bash
grep -rn 'resource "twingate_service_account"' stacks --include='*.tf'
```

PowerShell (est.):

```powershell
Get-ChildItem stacks -Recurse -Filter *.tf | Select-String 'resource "twingate_service_account"'
```

**Check.** Four lines, all in `stacks/20-telemetry/main.tf`: `logging`, `scrape`, `site_logging`, `site_scrape`. If you see a fifth, the repository changed after 2026-10-22 and this page needs an update.

**Undo.** Nothing changed.

### Exercise 2: prove the code never makes a key

**Predict.** What does a search for `twingate_service_account_key` in the stacks and modules find?

**Do.**

Bash:

```bash
grep -rn 'twingate_service_account_key' stacks modules --include='*.tf'; echo "exit=$?"
```

PowerShell (est.):

```powershell
Get-ChildItem stacks, modules -Recurse -Filter *.tf | Select-String 'twingate_service_account_key'; $?
```

**Check.** No lines, and `exit=1` in Bash (grep's way of saying nothing matched). That is the point: the keys are issued by hand, outside OpenTofu and outside its state.

**Undo.** Nothing changed.

### Exercise 3: confirm it is off by default

**Predict.** With the stage 2 switches at their defaults, how many service accounts does a plan contain?

**Do.** Read the first `run` block of `stacks/20-telemetry/tests/telemetry.tftest.hcl`, then run the stack's tests (the test setup is in [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md)).

Bash:

```bash
python3 -I -m pytest tests/test_telemetry_stack.py -q
```

PowerShell (est.):

```powershell
python -I -m pytest tests/test_telemetry_stack.py -q
```

**Check.** The test file asserts zero service accounts and zero Twingate resources at the defaults, and the Python tests pass (7 passed on 2026-10-22). The `tofu test` run itself needs OpenTofu installed and was not run for this page (est.).

**Undo.** Nothing changed.

### Exercise 4: read the vendor's sentence yourself

**Predict.** Which one sentence on Twingate's Services page explains why one service account per role is a good idea?

**Do.**

Bash:

```bash
curl -sL https://www.twingate.com/docs/services | grep -o 'Any Service Key authorizes access to all Resources assigned to the Service\.' | head -1
```

PowerShell (est.):

```powershell
(Invoke-WebRequest -UseBasicParsing https://www.twingate.com/docs/services).Content -match 'Any Service Key authorizes access to all Resources assigned to the Service\.'
```

Then open the [pricing page](https://www.twingate.com/pricing) in a browser, scroll to the comparison table and find the "Secure service accounts" row.

**Check.** The command prints the sentence (Bash) or `True` (PowerShell). In the browser, note which plan columns carry a mark. Write the date next to what you saw. If it differs from the register below, the page changed, and your reading is the newer evidence.

**Undo.** Nothing changed.

> **Screenshot to take yourself:** the comparison table's "Secure service accounts" row.
> Capture: the row and the column headings, in one frame.
> Look for: which plan columns carry a mark.
> Redact: nothing on a public page; do not include any signed-in account menu.

## Optional: make, use and revoke a service account in your own account

**Cost, teardown, first.** This needs a Twingate plan that lists service accounts. At the pricing-page read on 2026-10-22, the lowest is Home at "$15 per month" with a 14-day trial, limited to non-commercial use; the bill is yours and nothing you spend goes to the maintainer. It is not part of the repository's cost gate, which counts cloud resources. Before you start, decide how you will stop paying: Twingate's [cancel your subscription](https://www.twingate.com/docs/subscription-cancellation) page covers it, and the [Teardown checklist](Teardown-Checklist.md) lists the service keys to revoke. Cancel before the trial ends if you do not want to continue (est.: check the trial terms on the day).

I did not run this path. The steps are from Twingate's Services page.

1. In the Admin Console go to Team, then Services, and select "Create Service Account". Name it for its job, for example `learning-readonly-delete-me`.
2. Select "Generate Key". Choose a short expiry (the console default is 365 days; pick far fewer for a lab). Save the key the moment it is shown; it cannot be shown again.
3. Select "Add Resource" and assign one resource, one host and one port.
4. Predict: with that key in headless mode, what can the host reach? (Only that one resource.) The Linux steps are on Twingate's [Linux headless mode](https://www.twingate.com/docs/linux-headless) page.
5. Undo: revoke the key first (Twingate requires revoking before deleting), then delete the key, then delete the service account, then confirm the account bills nothing you did not intend. Service accounts count toward your license whether or not their keys are active, so delete the account itself, not only the key.

> **Screenshot to take yourself:** the service account page after step 3.
> Capture: the name, the key list showing state and expiry, and the assigned resource.
> Look for: the key shows an expiry date, and exactly one resource is assigned.
> Redact: the key value if it is ever on screen (never capture that screen), your network name and your email.

## Build it, break it, detect it, defend it

| Step | Question | Here |
|---|---|---|
| **Build** | What is the smallest working version? | One service account per site per role, one key per host, only that role's resources assigned, an expiry set when the key is made |
| **Break** | What happens when a part fails or is stolen? | A stolen key works from anywhere until it expires or is revoked, and reaches everything its service account holds. For a cloud host's logging key that is the home log ports of its own site, and it can send false logs. Reason it through on paper; do not test with a real key |
| **Detect** | How would you know? | Twingate has analytics and audit-log pages; whether and how they attribute traffic to a service account I did not verify (est.), so check in your own account. Signs to look for: a key in use from a host you did not issue it to, or a spike on a quiet one. A service account with no key in use is clutter and counts toward your license |
| **Evade** | How would an attacker avoid being noticed? | Use the key only for the resources it already has, at the hours the real host does, from the real host's traffic path. The narrower the grant, the less there is to do quietly |
| **Defend** | What closes it? | A narrow grant, one key per host so one can be revoked alone, a short expiry, the key kept in a secrets manager and not in files or state, and revocation the minute a host is lost |

Then **flip the board.** You are now the attacker who found a key on a disk image. What did it give you? Only its service account's resources. What would have made it worth more? A shared service account for every site, or one key copied to many hosts. Now the defender again: which of this repository's choices (a service account per role, no key in state, one key per host) removes that prize, and which part still depends on a human issuing and revoking keys correctly?

## Claims register

Retrieved 2026-10-22 with a read-only `curl`. Quoted phrases are exact.

| Claim | Source | Notes |
|---|---|---|
| Services give "programmatic, centrally-controlled, and consistent access controls for automated processes"; "Security Policies do not apply to Services"; "Any Service Key authorizes access to all Resources assigned to the Service"; key expiry default 365 days, set only at creation, unlimited allowed; revoke before delete; keys shown once; each key "individually API rate-limited" | [Twingate, Services](https://www.twingate.com/docs/services) | Read directly. Page footer said "Last updated 5 months ago" |
| Headless mode uses `--headless` with a service key file; the Docker client needs a tun device and NET_ADMIN; "AWS Fargate" is not supported for it | [Twingate, Linux headless mode](https://www.twingate.com/docs/linux-headless) | Read directly. Windows has its own page |
| Licenses count "Users and Service Accounts", whether or not their keys are active | [Twingate, Subscription management](https://www.twingate.com/docs/subscription-management) | Read directly. Does not say how the user caps treat them |
| "You are billed for all of your synchronized users and any service accounts you create." | [Twingate, Users](https://www.twingate.com/docs/users) | Read directly |
| "Service accounts are available for Business and Enterprise plan customers" | [Twingate, Linux userspace networking](https://www.twingate.com/docs/linux-userspace-networking) | Read directly. Disagrees with the pricing page on Home |
| Starter: "Free", "Up to 5 users", no service accounts listed. Home: "$15 per month", "Up to 7 users", "Secure Service Accounts", "Limited to non-commercial use". Teams: not listed. Business and Enterprise: listed. Terraform, Pulumi and the admin API marked on every plan | [Twingate, Pricing](https://www.twingate.com/pricing) | Card text read directly. The comparison table's marks were read from the page's markup, not seen in a browser: confirm by eye |
| Social login is Google, Microsoft, LinkedIn and GitHub; Google Workspace works "for all product plans" and other identity providers are in "Business and Enterprise product plans" | [Twingate, Social logins](https://www.twingate.com/docs/social-logins) and [Identity providers](https://www.twingate.com/docs/identity-providers) | Read directly. Neither page nor the pricing page uses the word SAML |
| `twingate_service_account` takes a name; `twingate_service_account_key` has `expiration_time` that "Defaults to 0, meaning the key will never expire" and a sensitive `token` "Used to configure a Twingate Client running in headless mode" | [Provider docs on GitHub, main branch: service account](https://github.com/Twingate/terraform-provider-twingate/blob/main/docs/resources/service_account.md) and [service account key](https://github.com/Twingate/terraform-provider-twingate/blob/main/docs/resources/service_account_key.md); registry listed version 5.2.0 on [the registry](https://registry.terraform.io/providers/Twingate/twingate/latest) | Read directly. Neither resource page names a plan |
| The number of service accounts per plan | None found | **Twingate is silent in everything read.** No number is given here |
| What a Starter account does when asked for a service account | None found | Not read, not tried |
| The maintainer's lab uses SAML, which the free plan does not include | The maintainer's statement | Not confirmed by any Twingate page read |
| The code defines four service accounts, creates no keys, and defaults to none | `stacks/20-telemetry/main.tf`, `stacks/20-telemetry/tests/telemetry.tftest.hcl`, `tests/test_telemetry_stack.py` | Read and searched in this repository |

## Checkpoint

You are done when you can say, without looking:

- Why a service key reaches everything its service account holds, and what this project does about that.
- Which stage first needs a service account, and why stages 0 and 1 do not.
- Which question about plans Twingate leaves unanswered, and where the page's two sources disagree.
- Why the repository creates the service accounts in code but never the keys.

## Where to next

[Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) shows the cloud-to-home paths these service accounts would serve, then the [home-side runbook](Stage-2-Home-Side-Runbook.md) covers the host that holds the scrape key.
