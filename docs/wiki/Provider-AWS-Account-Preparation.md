# AWS: account preparation

> **Status: unverified draft.** Written 2026-10-16 from AWS's own documentation (sources and dates in the [phase 0 evidence](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-phase0-evidence-aws.md)). Not applied in a real account and not yet reviewed by the maintainer. AWS changes its console and its free offers often: treat each step as a goal, and check the live console.

This is the page before any infrastructure. You will finish it with an AWS account that is protected, empty and watched, and with no Terraform, no Spacelift and no resources. That is the point. [Why the clouds differ](Why-the-Clouds-Differ.md) explains why the account is where AWS differs most from DigitalOcean.

**What this costs:** nothing, if you stop here. **What it does not do:** build anything. The AWS code now exists (`modules/aws/*`, `stacks/aws/*` and the [AWS stage guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/aws-access.md)), tested with mocked providers only and never applied; the Spacelift stacks for it are not to be created yet. See [issue #22](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/22).

## Step 0: decide what this account is for

Use a **new, throwaway account** for learning, not one that holds anything you care about and not one near your work. A separate account is the strongest safety control AWS offers: an experiment cannot touch anything outside it. Write down, before you start:

- The most you are willing to spend in a month, and two alert levels under it. This project's shared budget is **$30 a month across everything it builds**, so an AWS experiment and the DigitalOcean stage running together must stay under it. See [the AWS cost lesson](Provider-AWS-Cost-Lesson.md).
- A date by which you will delete the account or empty it.

## Step 1: understand what the "free" plan is today

As of 2026-10-16, AWS describes the free offer for **new AWS customers** as **credit based**, not as twelve free months: $100 on signup and up to $100 more for completing certain activities. The free plan ends after six months or when the credits run out, whichever is first. Then the account closes, its content is kept for 90 days, and you can upgrade to a paid plan inside that window to keep it. If you join the account to AWS Organizations (and some related services), it upgrades to a paid plan automatically, and AWS says the remaining credits then expire immediately.

One trap with the advice to use a fresh account: the offer is for new customers. If you or your employer already have, or ever had, an AWS account, a new one may not get the free plan or the credits at all. Check the eligibility rules before you assume a free ride.

What this means for a learner:

- A short, planned apply fits comfortably. A forgotten environment does not: credits draw down, and then the account closes.
- **Do not join the account to an organization casually.** It can end the free plan and the credits with it.
- The old "750 free hours of public IPv4 a month" belonged to the older twelve-month model. The current pricing page lists no such allowance, so do not assume it. See the cost lesson.

Check the live free-plan page before you sign up. This section is the most likely to be out of date.

## Step 2: create the account and protect the root identity

When you create an account you get a **root user**, tied to the email and with unlimited power that cannot be restricted. It is the thing an attacker most wants. The goal of this step is to make it almost never used.

1. **Use an email address that is a group or alias you control**, not a single person's inbox, if you can. If that mailbox is lost, so is the account.
2. **A long, unique password** from your password manager.
3. **Multi-factor authentication on the root user.** AWS requires it within 35 days of the first console sign-in attempt. A passkey or hardware key is the strongest choice; an authenticator app is acceptable. Register more than one device if the console allows it, and keep recovery in your password manager.
4. **Create no access keys for the root user.** AWS strongly recommends against it. If any exist, delete them.
5. **Turn on IAM access to billing** in the account settings. It is off by default, and without it your admin identity cannot see the bill you are trying to watch.

*Checkpoint: you can sign in as root with MFA, there are no root access keys, and you have a recovery path for the MFA device that does not depend on the same device.*

## Step 3: a billing alert, before anything else exists

Open **AWS Budgets** and create a monthly cost budget at your lower number, with an email notification. Add a second at your higher number.

- Budget monitoring and notifications are free. The first two budgets that also carry an *action* are free each month; extra ones cost a little. You do not need actions yet.
- A budget **notifies**. It does not stop spending. Budget actions can apply a restricting policy or stop selected instances, but they act on billing data that updates only a few times a day, so a cost can pass the line before anything happens. This is why the alert goes in before the first resource.

*Checkpoint: a budget exists, its email address is one you read, and you have a screenshot you do not publish. An alert you cannot point at is not an alert.*

> **Screenshot to take yourself:** the Budgets console while you create your first budget.
> Capture: the final review step of a cost budget with a low monthly amount and an email alert at a percentage of it, before you press Create.
> Look for: the monthly amount, the alert threshold (actual and forecasted), and that the alert goes to an address you read.
> Redact: the 12-digit account id (header and any ARN), the account alias, and the notification email address. Crop the account menu out of the top right corner.

## Step 4: stop using root; create the identity you will use

Root is for rare account tasks. Day to day, you use an administrative identity that can be restricted, audited and given MFA of its own.

- AWS recommends **IAM Identity Center** for people: sign-in through a central directory with temporary credentials. Granting access to AWS accounts needs an *organization* instance of it, and using AWS Organizations upgrades a free-plan account to paid (Step 1). So for a standalone throwaway account on the free plan, the console-only path is an **IAM user with a console password and MFA, used for the console only, with no access keys created**. Choose Identity Center only if you accept the upgrade.
- Whichever you choose: MFA on it, and use it from a browser or a command-line session that obtains temporary credentials, not from a downloaded permanent key.

*Checkpoint: you can sign in as your admin identity with MFA and see the billing page. Return to root only for the few tasks that need it.*

## Step 5: choose a region, and stay in it

Resources live in a region. Costs differ a little by region (Canada's `ca-central-1` was about ten percent more than `us-east-1` for the instance sizes checked on 2026-10-16), and some services are not in every region. For learning, choose one region and use only it. Choosing a region for data residency is a separate, real decision.

## Step 6: what is deliberately not here yet

- **The role that lets Spacelift act in your account.** Spacelift assumes an IAM role in your account using a trust policy and a per-stack identifier that Spacelift generates. The role must exist before the first apply, so it comes after your admin identity and is covered when the build is written. **Whether the Spacelift plan you use includes this AWS integration is not stated in Spacelift's documentation; check your own plan** before relying on it.
- **Any Terraform or OpenTofu.** Nothing in this page needs it.
- **Any resource.** Your account is empty.

## Try it yourself

- **Predict, then check.** Before you open the free-plan page, write down what you think happens to an account at the end of the free plan. Then read the page. What did you get wrong?
- Open your billing page and find the thing you would look at the morning after an experiment to check you are back to zero. Write down its name and where it is. Billing data lags, so one look is not proof; the cost lesson says how to look twice.
- Find the setting that controls whether your admin identity can see billing, and say what you can and cannot see with it on and off. What risk do you take by leaving it on for an identity you share?
- List three ways someone could end up with your root credentials. Which step above closes each?

Next: [the same four pieces on AWS](Provider-AWS-The-Same-Four-Pieces.md).
