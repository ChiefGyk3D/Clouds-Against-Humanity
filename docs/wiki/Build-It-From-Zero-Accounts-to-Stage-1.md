# Build it: from zero accounts to stage 1

> Prerequisites: the build track so far ([Fork, private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md), then [Labs](Labs-Break-It-on-Purpose.md)) and [How money works in the cloud](How-Money-Works-in-the-Cloud.md), because you set a billing alert before anything else.

> This is the replication path. It does not repeat the stage guides; it puts them in order, names the accounts you need before you need them, gives every step a "what you should see" check, and ends with how to take it all down and prove the bill is back to zero. Read [Start here if you are new](Start-Here-If-You-Are-New.md) first if the words are unfamiliar.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

The stage guides ([stage 0](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/00-foundation.md), [stage 1](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md)) and the [secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md) are the author's operating records. They are accurate for the author's setup and they contain items that are specific to it. This page tells you which, and in what order to use them.

**Cost, so you can decide before you start.** Stage 0 creates a project, a private network and a firewall, none of which cost money on DigitalOcean at the time of writing. Stage 1 adds two small droplets: about $12 a month at the prices the repository recorded on 2026-10-10, and it is the only part that bills. Free tiers for the other services change, so check each vendor's pricing page on the day instead of trusting this one. The track is built so you can stop after any step with a working, understood environment.

**What this is not.** It is not the only way to build this, and it is not a production recipe. Read [the demo-values table](Fork-Private-Stacks-and-the-Pipeline.md#step-2-which-values-are-demo-values) for what to change before it holds anything you care about.

## Step 0: make a mistake impossible to be expensive

Before you create any cloud account, do what you can to bound your downside.

1. **A password manager, and two-factor authentication on every account you are about to create.** Store recovery codes in the password manager, not in a note. I use and recommend [Proton Pass](https://proton.me/pass). The free plan covers unlimited logins and passkeys, and the built-in 2FA authenticator is part of the paid Pass Plus plan (the free plan has no built-in one, but Proton ships a separate Proton Authenticator app). Proton also sells mail, a VPN and drive storage, which you do not need for this project. A disclosure: if you sign up through [my links page](https://links.chiefgyk3d.com), I earn a commission, it costs you nothing, and this project does not depend on it. Any password manager that stores TOTP secrets or passkeys works the same way.
2. **A hardware security key, and I mean two.** I highly recommend [YubiKeys](https://www.yubico.com/products/security-key/). Buy at least two, register both on every account that allows it, and keep one somewhere other than your keyring, because a single key you lose is a lockout you built yourself. Put the recovery codes for each account in the password manager as well. Hardware keys resist phishing in a way a six-digit code does not, which matters because every account in this build can create or destroy something that costs money.
3. **Decide your numbers.** Choose the most you are willing to spend in a month and two alert levels below it (the author used $10 and $25 under a $30 ceiling). You cannot set the alert yet, because the provider account does not exist; you will set it as the first thing you do after creating that account, in step 4, **before you create a token or any resource**. See [How money works in the cloud](How-Money-Works-in-the-Cloud.md) for why the alert comes first, not last.

*Checkpoint: you have a password manager with MFA, two security keys (or a written plan to get them) for the services that support them, and your budget numbers are written down.*

## Step 1: run the free labs first

Before any cloud account, spend an hour proving to yourself you understand what the code checks. [Labs: break it on purpose](Labs-Break-It-on-Purpose.md) needs a clone of the repository and an internet connection (to download providers and tools), but no cloud account.

**You should see:** `Success! 34 passed, 0 failed.` from `modules/firewall`, and `cost-check: digitalocean: planned $12.00/mo, approved $12.00, active` followed by `cost-check: phase stage-1 ceiling $30.00 (reason: ...)` from `scripts/cost_check.py`.

*Checkpoint: if you could not predict a lab's result, reread its page before you give anything real access to your cloud.*

## Step 2: the accounts you need, in order

You need accounts at five services for stage 0 and 1. Create each one only when its step arrives, and turn on two-factor authentication the moment you do. Where the service supports security keys, register both of them right then, not later. Where it does not, use the strongest option it offers, an authenticator app, and say so in your notes.

| Order | Service | Needed for | Reached at |
|---|---|---|---|
| 1 | GitHub | Holding your private copy of the code | Step 3 |
| 2 | DigitalOcean | The cloud account | Step 4 |
| 3 | Doppler | The secret store | Step 5 |
| 4 | Spacelift | Running OpenTofu, holding state | Step 6 |
| 5 | Twingate **and an identity provider it can sign people in with** | Access to the droplets | Step 9 |

The identity provider is the one nobody mentions: Twingate decides *who* you are by trusting a sign-in service, such as a Google or Microsoft account, a GitHub login, or a company directory. Pick one and confirm it works with Twingate before step 9, because it is the first thing that would otherwise block you with money already spent. The [identity primer](Identity-Secrets-and-Zero-Trust-Basics.md) explains the idea.

**What Twingate can use, and what it costs.** Twingate's free Starter plan (up to 5 users) signs people in with a social login: Google, Microsoft, GitHub or LinkedIn, matched on the email address you invite. That is the zero-cost baseline and it is enough for this project. Directory integrations, meaning Microsoft Entra ID, JumpCloud, Okta, OneLogin and Keycloak, are listed as Business and Enterprise plan features, so using one of them with Twingate means a paid Twingate plan. Google Workspace is the exception Twingate lists for all plans. Twingate lets you connect more than one provider at once, so you can start on a social login and add a directory later.

**The one I actually recommend: a Microsoft 365 account with Microsoft Entra.** It is not the cheapest path and Twingate's free plan will not use it. I recommend it anyway because it gets you hands-on with Entra and IAM administration (users, groups, sign-in logs), which is outside this project's scope and a strong springboard into identity work. Entra ID Free is included with Microsoft cloud subscriptions such as Azure and Microsoft 365. The Microsoft 365 Developer Program is limited to Visual Studio Professional or Enterprise subscribers, ISV Success and Microsoft AI Cloud Partner Program members, and Premier or Unified Support customers, so do not count on it as a learner. An Azure free account, which Microsoft's own tenant documentation points to, is the route I would check first. Look at Microsoft's current offers on the day, because they move.

**JumpCloud** is a real directory and SSO product and a good one to try. Its pricing page shows a 30-day free trial and paid packages, with no permanent free tier that I could verify, and Twingate needs its Business plan to use it. Treat it as a trial, not a free home. **Keycloak** is open source and self-hosted, so the software costs nothing, but you run and patch it yourself, and Twingate lists its Keycloak integration as Business and Enterprise only. Pick it for the learning, not for the budget.

*Checked on 2026-10-19. Sources: [Twingate identity providers](https://www.twingate.com/docs/identity-providers), [Twingate social logins](https://www.twingate.com/docs/social-logins), [Twingate pricing](https://www.twingate.com/pricing), the Twingate setup pages for [Entra ID](https://www.twingate.com/docs/entra-id-configuration), [JumpCloud](https://www.twingate.com/docs/jumpcloud-configuration) and [Keycloak](https://www.twingate.com/docs/keycloak-configuration), [Microsoft Entra licensing](https://learn.microsoft.com/en-us/entra/fundamentals/licensing), [creating a Microsoft Entra tenant](https://learn.microsoft.com/en-us/entra/fundamentals/create-new-tenant), [the Microsoft 365 Developer Program FAQ](https://learn.microsoft.com/en-us/office/developer-program/microsoft-365-developer-program-faq), [JumpCloud pricing](https://jumpcloud.com/pricing), [Proton Pass](https://proton.me/pass). Plan limits and eligibility change, so check each pricing page on the day; I have left the prices out on purpose.*

## Step 3: your private copy

Follow [Fork, private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md): the mirror steps, the demo-values table, and what a mirror does not copy. Choose your region and VPC range now. Stage 0's guide explains why a VPC range that overlaps another one in the account is rejected.

**You should see:** your private repository with the full history, and `git remote -v` listing `origin` (yours) and `upstream` (this project).

*Checkpoint: CI runs on a pull request in your own repository, and you can say what it checks.*

## Step 4: DigitalOcean

> **Disclosure.** This is my DigitalOcean referral link ([https://m.do.co/c/e3aaa65aed6b](https://m.do.co/c/e3aaa65aed6b)). DigitalOcean's referral program page (https://www.digitalocean.com/referral-program, read 2026-10-22) says the person who refers gets $25 after the new account spends its first $25, and I would rather you read DigitalOcean's referral terms than take my summary for what you get. It helps me fund more open-source cloud projects like this one. Using it is optional, the project works exactly the same without it, and nothing here is gated behind it.

1. Create the account, enable two-factor authentication (register both security keys now if the console supports them, otherwise use an authenticator app and note that), and **set the billing alerts you decided on in step 0 before you do anything else**. The exact place in the console changes, so look for the billing or alerts settings in the live console. Take a screenshot you do not publish; an alert you cannot point at is not an alert.
2. Create the API tokens described in the secrets runbook's [token scope table](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md#4a-digitalocean-token-scopes): one write token for Spacelift to use, and optionally a read-only one for your own tooling. Give them a 90-day expiry and write the rotation date in your password manager.
3. Register your SSH public key on the account and note its **name**. Stage 1 looks the key up by name and does not create it. See [Lessons learned, "The SSH key that already existed"](Lessons-Learned.md#3-the-ssh-key-that-already-existed).

Skip the stage 0 guide's checklist item about "the token behind the `do-droplets` MCP server". That is the author's own tooling and has nothing to do with yours.

**You should see:** the billing alert listed, the token listed with its scopes and expiry, and the SSH key listed under the account's security settings.

*Checkpoint: you can point at the billing alert, and the token's scopes match the table, not "full access".*

## Step 5: Doppler

Create a Doppler project with a `prd` config and add `DIGITALOCEAN_TOKEN`. Create a **read-only service token** for that config. This is the one secret Spacelift will hold. Why only one: [Doppler and secrets](Doppler-and-Secrets.md).

**You should see:** the secret in the `prd` config, and a service token whose access is read-only.

*Checkpoint: the token you are about to put in Spacelift cannot change anything in Doppler.*

## Step 6: Spacelift, and the stage 0 stack

1. Create the account and connect your GitHub account to **your private repository**.
2. Create a context holding the Doppler service token as a write-only variable, and attach it to stacks with the `cah` label. The runbook's section 4 is the step-by-step.
3. Create the stack `cah-00-foundation` with project root `stacks/00-foundation`, OpenTofu as the workflow tool, **autodeploy off**, and deletion protection on. The names must match `.spacelift/config.yml` exactly or the secrets hook silently loads nothing for the stack.

Be aware of two plan limits. Push policies, which stop a pull request's code running in Spacelift, need a paid plan, and a free plan has no run-level identity token (which is why Doppler is in the picture). [Push policies: paid plan versus free plan](Spacelift.md#push-policies-paid-plan-versus-free-plan) states the limit once, and the runbook's section 9 gives the free-plan route and says what it cannot cover. Until you have read it, do not let anyone else open a pull request against your repository.

**You should see:** the stack in the Spacelift list with no runs yet.

*Checkpoint: autodeploy is off. Check it twice.*

## Step 7: apply stage 0

Trigger a **tracked run** on `main`. It stops after the plan and waits for you.

**You should see in the plan:** exactly **4 resources to add**: a project, a tag, a VPC and a firewall. Nothing else. The run log should show the hook line `doppler-env: loaded DIGITALOCEAN_TOKEN as DIGITALOCEAN_TOKEN` and the token's value should appear nowhere in it. If it does, revoke the token immediately.

Read the plan. Then confirm it. See [Terraform reference, reading the plan before you confirm](Terraform-Reference.md#reading-the-plan-before-you-confirm).

**You should see after the apply:** the project in the DigitalOcean console, a firewall with **zero inbound rules**, and no droplets.

*Checkpoint: you can explain each of the four resources. Billing is still $0.*

> **Screenshot to take yourself:** the Spacelift run for stage 0, at the confirm step and again after it applies.
> Capture: the tracked run waiting for confirmation with the plan summary visible, then the same run finished with the resources created.
> Look for: the run type tracked, the plan listing only what stage 0 should create, and the Confirm button you pressed yourself.
> Redact: the account name, the stack path if it names your repository owner, resource ids, and anything printed from the plan that is an address or a token.

## Step 8 (optional stop): you have stage 0

You now have a private network and a default-deny firewall, for free, and you understand every line. This is a good place to stop for a week.

## Step 9: Twingate, then stage 1

1. Create the Twingate account and connect your identity provider (the free social login is fine). Turn on two-factor authentication on the identity provider's account, with your security keys where it supports them (otherwise an authenticator app), and consider Twingate's own 2FA on top. **Sign in as a normal user once** to confirm it works.
2. Create a Twingate API key and add the stage 1 secrets to Doppler as listed in the stage 1 guide, section 5: `TWINGATE_API_TOKEN`, `TWINGATE_NETWORK`, `ADMIN_SSH_PUBLIC_KEY`, `ADMIN_SSH_KEY_NAME`, `ADMIN_USER_IDS`.
3. Check that no Twingate site named `access-<region>` already exists. The code creates it, and a hand-made one with the same name collides. See [Lessons learned](Lessons-Learned.md#4-a-hand-made-twingate-site-collides-with-the-code).
4. Create the stack `cah-10-access` rooted at `stacks/10-access`, with a dependency on `cah-00-foundation` and the output mapping in the stage 1 guide. **Give it the same settings as stage 0:** the `cah` label (the Doppler context attaches to stacks carrying it, and without it the run has no Doppler token and fails), **autodeploy off** (this is what makes a human confirm every paid apply), and deletion protection on.
5. **Before you apply, check the price yourself.** The cost gate proves your code is consistent with the repository's approved model: run it and expect `$12.00`. It does not prove your invoice, because it reads a price table fixed on 2026-10-10. Look up the current price and availability of the droplet size in your region in the DigitalOcean console or its sizes API, and confirm it matches. This is the first step that bills.

**You should see in the plan:** **13 resources to add**: a tag, a site, two connectors, two token sets, two droplets, a firewall, a project attachment, a group and two SSH resources. Read it, then confirm.

## Springboards

I want you to think past this page, not just follow it. Too much learning is spoon-fed, and the useful habit is asking what else you could try. For this stage, a few ideas, none of them required:

- Make a throwaway account and break its MFA recovery on purpose: lose the phone, lose one key, and see what actually gets you back in. Do it before it happens to an account you need.
- Read the identity provider's sign-in logs after you log in. Find your own sign-in, and then work out what a failed or odd one would look like.
- Run the same Twingate flow with a second identity provider and compare what each one asks you to set up.
- Map what the identity provider can see about you, and what Twingate can see that it cannot.
- Pick one thing here that you would do differently and write down why, then find a tool that does it that way.

Recommending other springboards is welcome throughout this project, so if you find a better one, open a pull request.

## Step 10: verify, as a visitor would

Do all three. The third is the one that proves the design.

1. Both connectors show **online** in the Twingate admin console, under one site.
2. From a machine running the Twingate client, `ssh cah-admin@<connector private IP>` works for each connector. The user is `cah-admin` (the stage 1 guide explains why not root), and the private addresses are the `connector_private_ips` output of the `cah-10-access` stack.
3. From a machine **not** running the client: `nmap -Pn -p 22,80,443 <connector public IP>` shows the ports **filtered** on both droplets. The stack does not output public addresses; read each droplet's public IP from the DigitalOcean console. Scanning your own droplet is authorized; do not scan anyone else's.

*Checkpoint: you can reach the machines from inside and you cannot from outside, and you know why.* If a connector shows offline, the stage 1 guide's section 6a is the troubleshooting path.

> **Screenshot to take yourself:** the Twingate Connectors page and the DigitalOcean Droplets page once stage 1 is up.
> Capture: both connectors with status Alive, and the Droplets list showing the connector droplets running.
> Look for: Alive on both connectors, and the droplets present, so you know what step 11 will remove.
> Redact: tenant and team names, droplet names and ids, public and private IP addresses, and the region if you do not want it known.

## Step 11: tear it down, and prove the bill is zero

Billing stops when the droplets are gone, not when you stop looking at them.

1. In Spacelift, **destroy `cah-10-access` first**. Stage 0's VPC, project and tag are in use by stage 1, so the order matters. Connector tokens die with the connectors, and the Twingate site goes with the stack.
2. Destroy `cah-00-foundation`.
3. Revoke or let expire the tokens you made. Delete the Doppler secrets you no longer need.
4. **Check the VPC.** Destroying `cah-00-foundation` can fail with `403 Can not delete default VPCs` if the VPC the stack created became the region's default (this happened to the author; see [Lessons learned 9](Lessons-Learned.md#9-a-rebuilt-account-nothing-you-assumed-is-still-true)). DigitalOcean can delete a default VPC only after another VPC is made the default for that region. So: in the console, see whether this VPC is the default. If it is, either make another VPC the default first and destroy again, or remove the VPC from the stack's state and accept that it remains on the account (empty VPCs cost nothing) and say so in your notes. Re-run the destroy and confirm the stack reports nothing left.
5. **Know what survives**, and look for it: the SSH key on your DigitalOcean account (the stack never created it), a VPC you chose to leave, the Doppler project, the Spacelift stacks themselves (deletion protection is on by design), and the Twingate account.
6. **Prove it.** In the DigitalOcean billing page, check that no droplet or reserved resource is listed, and look again the next day. A resource you forgot is a charge you will meet on the invoice.

*Checkpoint: the console lists no droplets, and tomorrow's billing page shows no new usage.*

The same steps as a tick-list, with the order of destruction, the read-only checks and the token clean-up in full, are on the [Teardown checklist](Teardown-Checklist.md).

## When it breaks

The stage guides and [Lessons learned](Lessons-Learned.md) are written as symptom, cause, fix. A few of the first-timer failures, with where to look:

| What you see | Look at |
|---|---|
| The run fails and the log mentions Doppler or an empty variable | [Lessons learned 6](Lessons-Learned.md#6-doppler-names-are-uppercase-opentofu-variables-are-not) and the runbook's troubleshooting section |
| A 422 about an IP range overlapping | The stage 0 guide, "Choices to confirm before apply" |
| A connector offline, ports look fine | The stage 1 guide, section 6a, and [Lessons learned 1](Lessons-Learned.md#1-curl--bash-reported-success-and-installed-nothing-useful) |
| A red check from Spacelift on a pull request | [Lessons learned 10](Lessons-Learned.md#10-a-red-check-from-a-run-that-could-never-pass) |
| Your account is not like the author's | [Lessons learned 9](Lessons-Learned.md#9-a-rebuilt-account-nothing-you-assumed-is-still-true) |

## What you built, and what to do next

You built, by hand and understanding each step, a small environment where no machine has an open port, secrets live in one place, every change is reviewed, and a human confirms every apply. Next: the [Settings reference](Settings-Reference.md) lists every value you can change in your own copy. Then re-read the [Threat model](Threat-Model.md) with the labs fresh in your mind, try the security track, and decide what you would change before this held anything real. [What an enterprise does differently](Small-Example-Enterprise-Landscape.md) starts the detection track.

Back to the [Reading order](Reading-Order.md).
