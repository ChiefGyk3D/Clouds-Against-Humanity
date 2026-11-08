# GCP: account preparation

> **Status: unverified draft.** Written 2026-10-16 from Google's own documentation (sources and dates in the [phase 0 evidence](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-phase0-evidence-azure-gcp.md)). Never applied in a real project and not reviewed by anyone who runs Google Cloud for a living. Google changes its console and its free offers often: treat each step as a goal, and check the live console. If you run GCP and see an error, please say so on [issue #22](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/22).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

This is the page before any infrastructure. You will finish it with a Google Cloud project that is protected, empty and watched, and with no Terraform, no Spacelift and no resources. That is the point. [Why the clouds differ](Why-the-Clouds-Differ.md) explains why the starting point on GCP is so different from AWS and DigitalOcean.

**What this costs:** nothing, if you stop here. **What it does not do:** build anything. No GCP code exists in this repository yet: there is no GCP module or stack, and the build is not yet written (see [issue #22](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/22)). Only AWS has code, and that is mocked-tested and never applied.

## Step 0: decide what this project is for

Use a **new, throwaway project** for learning, not one that holds anything you care about. On GCP the project is the box every resource lives in, so a separate project is the strongest safety control you have: deleting it deletes what is in it. Write down, before you start:

- The most you are willing to spend in a month, and two alert levels under it. This project's shared budget is **$30 a month across everything it builds**, so a GCP experiment and the DigitalOcean stage running together must stay under it. See [the GCP cost lesson](Provider-GCP-Cost-Lesson.md).
- A date by which you will delete the project.

A caution about the word "separate". A project is a box for resources, but the **billing account** that pays for it is a different object. Several projects can share one billing account, and the always-free allowance (Step 1) is counted per billing account, not per project. A throwaway project protects your resources; it does not give you a second free allowance.

## Step 1: understand what the "free" offers are today

There are two different things, and they are easy to confuse.

**The Free Trial.** As of 2026-10-16, Google's free-features page describes a **$300 welcome credit to spend over 90 days**. A card is required. If you spend the credit or the 90 days pass without upgrading, the trial billing account closes, billing is disabled and resources are stopped. You then get a **30-day grace period** to upgrade and possibly recover them; after that the trial's resources are permanently deleted. Google also says the trial does not charge you automatically. (Source: [free cloud features](https://docs.cloud.google.com/free/docs/free-cloud-features), read 2026-10-16.)

**Always Free.** A separate, ongoing allowance. The Compute Engine part, as the same page reads on 2026-10-16:

- one non-preemptible `e2-micro` VM per month, only in `us-west1` (Oregon), `us-central1` (Iowa) or `us-east1` (South Carolina), with the hours counted across those three regions combined, not per instance;
- 30 GB-months of standard persistent disk;
- 1 GB of outbound data a month from North America;
- it needs an active Cloud Billing account in good standing, does not roll over, and is per billing account.

The evidence file records that an external IP is **not** covered by this free tier; the page text I fetched on 2026-10-16 did not mention addresses either way. Treat the address as billable ($0.005 an hour, see the cost lesson) and check the live page.

What this means for a learner:

- A short, planned apply fits inside the trial. A forgotten environment does not: credits draw down, and the trial then closes.
- **Always Free is tiny.** One `e2-micro` has 1 GB of memory, which is below Twingate's general guidance of 1 CPU and 2 GB for a connector (Twingate suggests `e2-small` on GCP). It is a useful thing to test, not a recommendation.
- The trial rules, the regions and the allowances above are exactly what Google edits most often. Check the live page before you sign up. This section is the most likely to be out of date.

## Step 2: know what you do not have, because you have no organization

GCP's hierarchy has an **organization** at the top, optional **folders** under it, and **projects** as the unit every resource lives in. An organization needs Google Workspace or Cloud Identity. A person who signs up with a personal Google account gets **projects and nothing above them**. That has real consequences:

| You do not have | What it would have given you |
|---|---|
| Folders | Grouping projects, and inheriting settings down the group |
| Organization policy | Guardrails that forbid things for every project below (for example, which machines may have an external address) |
| Hierarchical firewall policies | Firewall rules attached above the project, evaluated before the project's own rules |

The evidence file is slightly inconsistent about what a plain personal account has: one Google page mentions a "standalone organization" created at signup, and I could not verify what that means for a personal account. Treat it as **project only** unless you deliberately set up Cloud Identity Free. If you do, you get the organization and its policies, and you take on an identity directory to run.

The practical rule: the guardrails an organization would enforce for you have to be **habits** you apply in every step below. That is why this page is stricter than it looks.

## Step 3: protect the first identity

Your Google Account is the root of everything: whoever has it controls the project and the billing account.

1. Use an address you control, and a long unique password from your password manager.
2. Turn on **2-step verification**, preferably with a passkey or hardware security key, and keep recovery options that do not depend on the same device. **This is general good practice and not sourced from a Google page I could read on 2026-10-16: UNVERIFIED as a Google-specific claim.** Check Google's account-security pages.
3. Do not use an account you also use for work or one near your work.

*Checkpoint: you can sign in with the second step, and you have a recovery path for the second factor.*

## Step 4: no downloaded service-account keys

A **service account** is an identity for software. Google lets you create a **key file** for one: a permanent secret that anyone holding it can use from anywhere. Google's own best-practice page says to avoid service-account keys whenever possible. Write that down as a rule for this project: **you will not create or download a service-account key.** The two places a key tempts people are:

- *A machine that needs to call Google APIs.* Attach a service account to the machine instead (the next page). The platform hands it short-lived tokens; there is no file.
- *Spacelift acting in your project.* Spacelift can create a service account for the stack and use a short-lived token for each run, with no stored key. The next page covers how. A key file is the fallback that this project does not want.

An organization could enforce this with a policy that forbids key creation. You have no organization, so the enforcement is you. (Whether a specific "disable key creation" constraint exists and is on by default was not confirmed: UNVERIFIED.)

*Checkpoint: in **IAM & Admin -> Service Accounts**, open each service account, go to its **Keys** tab, and confirm no user-managed keys exist. (The project's IAM permissions page lists principals and role bindings, not keys, so it cannot show this.)*

## Step 5: a billing budget, before anything else exists

Open **Billing**, then **Budgets & alerts**, and create a monthly budget at your lower number, then another at your higher number.

- Google's defaults are alerts at 50%, 90% and 100% of the budget amount, based on actual spend. You can change or remove them. (Google's budgets page, read 2026-10-16.)
- By default, alert emails go to billing admins and billing users on the account. Make sure that is an address you read.
- **A budget notifies. It does not stop spending.** Google says so directly: an alerts-only budget "doesn't automatically cap" usage or spending. There are two ways to add teeth, and neither is a brake. A notification sent to Pub/Sub can drive automation, such as turning billing off for a project, but the data is an estimate, usage-to-cost reporting lags, delivery can be late or out of order, and a failure is silent, so spend can pass the line before anything happens. A separate "spend cap" budget exists only for eligible services. This is why the alert goes in before the first resource.
- Creating a billing-account budget needs a billing role (Google names Billing Account Costs Manager or Billing Account Administrator); a single project's budget can be made with project-level billing permission.

*Checkpoint: a budget exists, its email address is one you read, and you can point at it. An alert you cannot point at is not an alert.*

## Step 6: enabling APIs, and the default network

GCP ships most features as **APIs that are off until you enable them in a project**. A first apply of this stack would need the Compute Engine API on, and Google's tooling will ask. Enable only what you need, and note what you turned on: an enabled API is not a charge by itself, but it is the list of things that can be used. (Which exact APIs a Spacelift run needs is not yet written and not verified.)

Every new project starts with a network called **`default`**, in auto mode, with pre-populated firewall rules, including ones that allow instance-to-instance traffic and ingress for SSH and RDP. [The next page](Provider-GCP-The-Same-Four-Pieces.md) explains why this project would not use it. Without an organization policy you cannot stop the default network from being created, so the habit is to **create your own network and delete or ignore `default`**.

## Step 7: choose a region, and stay in it

Resources live in a region (subnets) and a zone (machines). Prices differ a little by region, and the Always Free allowance covers only `us-west1`, `us-central1` and `us-east1`. The price figures in this wiki are for `us-central1`. For learning, choose one region and use only it. Choosing a region for data residency is a separate, real decision.

## Step 8: what is deliberately not here yet

- **The identity that lets Spacelift act in your project.** Spacelift creates a service account for each stack and you grant it roles in your project before the first apply. It comes after your project and is covered with the build. **Spacelift's GCP page mentions no plan or tier requirement, but that is not a promise: check your own plan.**
- **Any Terraform or OpenTofu.** Nothing in this page needs it.
- **Any resource.** Your project is empty.

## Try it yourself

- **Predict, then check.** Before you open the free-features page, write down what you think happens to a trial account on day 91. Then read the page. What did you get wrong? (Reference: billing is disabled and resources are stopped; there is a 30-day grace period to upgrade; after that the trial's resources are permanently deleted.)
- Find your project's **IAM** page and list who has access and at what level. Name one role on that list you did not expect.
- You have no organization. Name two guardrails an organization policy would have given you, and say what habit replaces each. (Reference, one reasonable answer: "no external addresses except on approved machines" is replaced by checking each machine's address setting; "no service-account keys" is replaced by never creating one and checking each service account's Keys tab for existing keys.)
- Create a budget with no email you read. Why is it worse than no budget? (Reference: it looks like protection and gives none.)
- List three ways someone could end up controlling your Google Account. Which step above closes each? (Reference, one answer: a reused password, closed by Step 3's unique password; a phished sign-in, closed by a passkey or hardware key, which will not hand a code to a fake site; a stolen already-signed-in session, which a passkey does not stop, answered by signing out other sessions and reviewing account security activity from the Google Account security page, and by keeping the device itself secured (UNVERIFIED as Google-specific steps: check the live account pages); a lost second factor with no recovery path, closed by Step 3's recovery checkpoint.)

Next: [the same four pieces on GCP](Provider-GCP-The-Same-Four-Pieces.md).
