# How money works in the cloud

Start-from-zero page 7 of 8. Previous: [Containers and Docker basics](Containers-and-Docker-Basics.md). Next: [Enterprise engineering habits](Enterprise-Engineering-Habits.md).

A Pi costs what it cost once, plus a little electricity. The cloud bills you for everything that exists, for as long as it exists, and sends the invoice at the end of the month. Most learners' first cloud mistake is not a security hole; it is a $40 surprise from something they forgot to delete. This page is how to not do that, and how this project turned its bill into a number that gets reviewed like code.

## What costs and what is free

Prices below are DigitalOcean's at the time this project's price table was fetched (October 2026; see `docs/cost-prices.json` for the exact date). They change. The shape does not.

| Thing | Costs | Notes |
|---|---|---|
| A **droplet** (virtual machine) | From about $4 to $6 a month for the smallest sizes, billed per second it exists | Billed whether it is busy or idle, powered on or off. "Off" is not "deleted". |
| **Backups** of a droplet ([what a backup is](Backups-Recovery-and-Patching.md#four-words-that-sound-alike)) | 20 percent of the droplet's price for weekly, 30 percent for daily | Confirmed on DigitalOcean's pricing page on 2026-10-11 |
| **Snapshots** | Per gigabyte stored | A snapshot you took once and forgot is a small bill forever |
| **Block storage** (extra disks) | Per gigabyte per month | |
| **Object storage** (Spaces) | $5 a month flat for a generous allowance | Flat fee even if you store one file |
| **Bandwidth** | A large allowance is included per droplet and pooled; overage is per gigabyte | A hobby project will not reach it. A misconfigured download loop might. |
| **Serverless functions** | A free monthly allowance, then fractions of a cent per gigabyte-second | Timer jobs at hobby scale usually stay inside the free allowance |
| **Load balancers, managed databases, Kubernetes nodes** | Each starts around the price of a droplet or more | Not used here, on purpose |
| **Projects, VPCs, firewalls, tags, SSH keys** | **Free** | Which is why stage 0 of this project costs $0 |

On DigitalOcean specifically: This is my DigitalOcean referral link ([https://m.do.co/c/e3aaa65aed6b](https://m.do.co/c/e3aaa65aed6b)). DigitalOcean's referral program page (https://www.digitalocean.com/referral-program, read 2026-10-22) says the person who refers gets $25 after the new account spends its first $25, and I would rather you read DigitalOcean's referral terms than take my summary for what you get. It helps me fund more open-source cloud projects like this one. Using it is optional, the project works exactly the same without it, and nothing here is gated behind it.

The other services in this project (Spacelift, Doppler, Twingate, GitHub) have free tiers that cover a one-person lab at the time of writing, with one Twingate exception for stage 2: service accounts are listed on Twingate's Home, Business and Enterprise plans and not on the free Starter plan ([Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md)). The project's [cost page](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) deliberately lists those limits as "not yet verified", because a wiki that promises a free tier is wrong the day the vendor changes it. Check the pricing page yourself before you depend on it.

## How bills get out of hand

- **Forgetting.** You followed a tutorial, created a machine, and moved on. It bills until deleted. Powering it off does not stop the bill; only destroying it does.
- **Snapshots and volumes left behind.** Deleting a droplet does not delete the snapshot you took of it or the extra disk you attached. Those are separate resources with separate bills.
- **The wrong size.** One character in a size name is the difference between $6 and $48 a month.
- **Managed services that sound small.** A "basic" managed database or load balancer is often more than all your droplets combined.
- **A leaked token.** The classic: a cloud token committed to a public repository, found by a bot within minutes, used to spin up dozens of large machines to mine cryptocurrency. The bill can reach thousands before you notice. This is a security problem and a money problem, and it is why every page on this wiki about secrets is also about money.
- **Bandwidth or API loops.** A bug that downloads the same file every second, or a function that triggers itself.

## The defenses, in order of how early they act

### 1. A billing alert, before anything else

Every provider lets you set an email alert at a dollar threshold. Set one before you create your first resource. This project set two in stage 0, at $10 and $25, against the $30 ceiling of the current phase. An alert does not stop spending, but it turns a month of silence into a same-day email.

### 2. A ceiling, written down

Decide the most this is allowed to cost per month, and write the number where it will be seen. Here it is $30 today, and it is written per phase in `docs/stages/approved.json`: every phase carries its own ceiling, why it is that number and when it was decided. A later phase can raise it, but only by editing that entry in a pull request someone reads, so the number rises on purpose and never by drift. The README, the Home page, the cost page and the roadmap quote it. A number nobody wrote down is a number nobody is held to.

### 3. Approve before it exists, not after

Each stage of this project has its cost worked out and approved **before** the first apply. Stage 1's two connector droplets were approved at $12 before they existed. Stage 3 is designed and priced at $17 but not approved, so it does not exist. The ordering is the point: a plan that says "this will cost $12" is a decision; an invoice that says "this cost $12" is news.

### 4. A check that fails the build

The **cost gate** is a small program, `scripts/cost_check.py`, that runs on every pull request. It:

- reads a manifest in each stack listing the paid resources it will create (`cost.json`), looks each one up in the price table, and adds them up;
- fails if the total is above the approved amount in `docs/stages/approved.json`;
- refuses any DigitalOcean resource type that is not on its list of known-free types, unless it is the one paid type (a droplet) in the one file where it is allowed. A pull request that adds a managed database fails by name, before anyone has to notice it in review;
- refuses a few things it cannot price safely, such as backups while the backup price is marked unverified. The committed table marks the basic weekly backup plan (20 percent of the droplet) verified as of 2026-10-19. Daily and usage-based backup plans are refused by the gate until someone prices and verifies them; bandwidth overage, snapshots and block storage stay unverified.

Raising the budget is a visible change: you edit `approved.json`, the diff shows the old number and the new one, and that is reviewed like any code. [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) has the full logic and, just as importantly, what the gate cannot see.

### 5. Make the expensive mistake impossible to make quietly

The droplet size in this project is not typed into the machine's definition. It is read from the same `cost.json` the gate prices. So the price the gate approved and the size that actually gets built cannot disagree. That is a general trick: when two things must match, make them one thing.

### 6. Destroy order and "nothing irreplaceable"

Because every stage is code, each one can be destroyed completely with one run, in a known order (access first, then foundation). A learner following along can build stage 1, poke at it for a weekend, destroy it, and pay for two days of two droplets, which is cents. That is only painless because nothing on the droplets needs saving, and designing for that is a recurring theme here.

## Reading your own bill

Once a month, open the provider's billing page and compare it with what you think exists. Every line should be something you can name. A line you cannot name is either a forgotten resource or someone else's use of your account, and both need action today.

For this project, the running total is kept in two places so they can be checked against each other: the cost page in the repo (what was approved) and the DigitalOcean billing page (what happened). The threat model's T11, "runaway bill", lists what the gate covers and what only the billing page can catch.

## The cost of the free stuff

Two more kinds of cost that do not appear on an invoice:

**Vendor lock and free tiers.** A free tier is a marketing budget, and it can end. This project uses four vendors' free tiers. The honest stance is to write down the limits with the date they were checked, and to know what the paid tier would cost or what the exit would look like. The cost page's "not yet verified" list is exactly that.

**Your time.** Running a Kubernetes cluster is free in the sense that the control plane costs $0. It is not free. The [Roadmap](Roadmap.md) says no to Kubernetes for now partly on money and partly on the complexity budget, and that second budget is as real as the first.

## Where this shows up in the repo

| Idea | Where |
|---|---|
| The ceiling per phase and the approved totals | `docs/stages/approved.json` (`phases`, `current_phase`) |
| Raising a phase's ceiling | `scripts/cost_raise.py` (dry run by default) |
| What each stack will create and cost | `stacks/*/cost.json` |
| The price table, with its retrieval date | `docs/cost-prices.json` |
| The gate itself and its tests | `scripts/cost_check.py`, `tests/test_cost_check.py` |
| The size read from the manifest, not typed into the droplet | the `cost` local in `stacks/10-access/main.tf` |
| Running totals and the "not yet verified" list | [docs/cost.md](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) |

## Try it yourself

- Run the gate: `python3 -I scripts/cost_check.py --root .` from a clone of this repo. It prints the planned total, the approved total and the current phase's ceiling. Then edit a `cost.json` to use a bigger size and run it again; it should refuse.
- Before you create your first cloud resource anywhere, find the billing alert setting and set one. Then, and only then, create the resource.
- If you already have a cloud account, open its billing page right now and name every line.

Next: [Enterprise engineering habits](Enterprise-Engineering-Habits.md).
