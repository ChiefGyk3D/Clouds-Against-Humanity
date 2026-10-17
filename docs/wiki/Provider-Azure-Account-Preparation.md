# Azure: account preparation

> **Status: unverified draft.** Written 2026-10-16 from Microsoft's own documentation and its public retail price API (sources and dates in the [phase 0 evidence](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-phase0-evidence-azure-gcp.md); several claims were read again on the same day, and the ones still unconfirmed are marked UNVERIFIED below). Never applied in a real Azure account, and not reviewed by anyone who runs Azure. If you do, please correct it on [issue #22](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/22). Microsoft changes its portal and its free offers often: treat each step as a goal and check the live portal.

This is the page before any infrastructure. You will finish it with an Azure subscription that is protected, empty and watched, and with no OpenTofu, no Spacelift and no resources. That is the point. [Why the clouds differ](Why-the-Clouds-Differ.md) explains why the account is where Azure differs most from DigitalOcean, and [the AWS version of this page](Provider-AWS-Account-Preparation.md) is the same exercise on another cloud.

**What this costs:** nothing, if you stop here. **What it does not do:** build anything. The build comes later and is not yet written (see [issue #22](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/22)).

## Step 0: decide what this subscription is for

Use a **new, throwaway subscription** for learning, not one that holds anything you care about and not one near your work. A separate subscription limits what an experiment can spend and delete, and gives it one bill. It does **not** isolate the directory: a subscription trusts a tenant, and if you create it inside an existing tenant (work, school, or one you share), a Global Administrator of that tenant can change tenant-wide settings and reach your subscription. So do the directory steps below (security defaults, MFA, Global Administrator) only in an **isolated personal learning tenant** that you created and nobody else administers, and give every experiment identity a role scoped to the learning subscription or resource group, not to the tenant. Do not count on a new subscription alone for containment. (This follows from Microsoft's description of the tenant as the identity directory and the Global Administrator role as a directory role, read 2026-10-16.) Write down, before you start:

- The most you are willing to spend in a month, and two alert levels under it. This project's shared budget is **$30 a month across everything it builds**, so an Azure experiment and the DigitalOcean stage running together must stay under it. See [the Azure cost lesson](Provider-Azure-Cost-Lesson.md).
- A date by which you will delete the resource group, or the subscription.

## Step 1: understand the boundaries before you create anything

Azure has more levels than DigitalOcean, and people mix up the first three. As of 2026-10-16, Microsoft's documentation says:

| Word | What it is | Why you care |
|---|---|---|
| **Tenant** | Your Microsoft Entra directory: the people, groups and applications. It is an *identity* boundary. | Who can sign in, and the MFA rules, live here. |
| **Management group** | An optional folder above subscriptions. Every directory has one root management group (display name "Tenant root group", with the tenant's id as its id). | You will probably never touch it. No one has default access to it. |
| **Subscription** | The billing and access boundary where resources live. | Budgets, bills and most role assignments attach here. |
| **Resource group** | A container for resources that share a lifecycle. | Deleting it deletes everything inside it. |

Microsoft names four levels of *management scope*: management groups, subscriptions, resource groups and resources. The tenant is the directory beside and above them. The practical rule: **the tenant decides who you are; the subscription decides what you can spend and break; the resource group decides what you can delete in one stroke.**

Two details to hold on to:

- The user who creates a tenant is automatically its Global Administrator (Microsoft Entra documentation, read 2026-10-16). Being Global Administrator is a directory role. Microsoft's documentation says only Global Administrators can elevate to access the root management group. What role you hold on the *subscription* after signup is a separate question that this wiki has not confirmed.
- **UNVERIFIED:** that a new individual signup creates exactly one tenant and one "Free Trial" subscription. The pages read do not say so. Open the portal's subscription list and write down what you actually see.

## Step 2: understand what the "free" account is today

As of 2026-10-16, the Azure free account page (azure.microsoft.com/en-us/free) describes, for **new Azure customers** only:

- A **$200 credit that must be used within 30 days.**
- **12 months** of 750 hours each of three burstable VM sizes (`B1s`, `B2pts v2` on Arm, `B2ats v2` on AMD), plus a list of other services, and a set of always-free services.
- A phone number, a **credit or non-prepaid debit card**, and a Microsoft or GitHub account are required. A temporary one-dollar authorization may be placed on the card and then reversed.
- "You won't be charged unless you choose pay-as-you-go." When the credit runs out or 30 days pass, you must move to pay-as-you-go to continue; otherwise, the page says, your account and services are disabled.

What this means for a learner:

- The 30-day clock is the real limit, not the 12 months. A short, planned apply fits inside it. A forgotten environment is switched off when the credit or the 30 days end, which is a safety net of sorts.
- The free account has a **spending limit** equal to the credit, turned on by default (Microsoft's spending-limit page, read 2026-10-16). When it is reached, your VMs are stopped and deallocated, and settings such as virtual IP addresses are lost. You cannot change the amount. You can remove it, and **upgrading to pay-as-you-go removes it**. Pay-as-you-go subscriptions do not have one at all. So the one built-in brake on Azure disappears at the moment you upgrade to keep your resources, which makes the budget in Step 5 more important after an upgrade, not less. (That last sentence is this page's reading of two documented facts, not a Microsoft statement.)
- The eligibility is for *new* customers. If you or your employer already have an Azure account, a new one may not qualify. Check before you assume a free ride.
- **UNVERIFIED:** whether the free account's 750 hours also cover a public IP address or a disk. The page is silent. The cost lesson assumes they do not.
- One of the three free VM sizes, `B1s`, belongs to a VM series that Microsoft's size page (updated 2026-09-27) lists as **End of Life** with an announced retirement. Do not build on it.

Check the live free-account page before you sign up. This section is the most likely to be out of date.

## Step 3: protect the first identity

Your first identity is the Global Administrator of a brand-new tenant, and it is also what you will use to create everything else. It is the thing an attacker most wants.

1. **A long, unique password** from your password manager, and a sign-in email you control and can recover.
2. **Multi-factor authentication.** Microsoft turns on *security defaults* for new tenants, with a **24-hour grace period** before they are enforced so you can finish setting up. Once enforced (documentation read 2026-10-16):
   - all users must register for MFA, using the Microsoft Authenticator app (notifications) or an OATH TOTP app;
   - administrators (Global Administrator and a list of other admin roles) do MFA **every time they sign in**;
   - anyone using the Azure portal, Azure CLI, Azure PowerShell or the Entra admin center needs MFA;
   - legacy authentication is blocked, and **device code flow is blocked** (since 2026-07-01 for all new tenants). If a tutorial tells you to run `az login --use-device-code`, expect it to fail. Use a browser sign-in.
3. Microsoft warns not to disable authentication methods while security defaults are on, because you can lock yourself out of your own tenant.
4. **Recovery.** Microsoft recommends two cloud-only *emergency access* ("break glass") accounts with the Global Administrator role for real tenants. For a one-person throwaway tenant that may be more than you need, but the reason is worth understanding: if your only admin loses the only MFA device, nobody can fix the tenant. At the least, register more than one method and keep recovery in your password manager.

*Checkpoint: you can sign in to the portal with MFA, you know which method you registered, and you have a recovery path for the device that does not depend on that same device.*

## Step 4: no standing keys

Do not create a long-lived secret for your own use or for a tool. For you: sign in through the browser, with MFA. For machines and for Spacelift: use identities that do not hold a password you must store. Azure's three options, and the one this project's build would use, are on [the Azure "same four pieces" page](Provider-Azure-The-Same-Four-Pieces.md). The short form: a static service principal secret is a standing key (you rotate it by hand), and the alternatives avoid it.

Microsoft's role-based access control guidance (read 2026-10-16) says to grant the least privilege that gets the work done, at the narrowest scope, to keep the number of **subscription owners at three or fewer**, to prefer job-function roles over privileged administrator roles, to use Privileged Identity Management for just-in-time elevation where you have it, and to assign roles to groups rather than to individual users. For a throwaway subscription with one person, the practical version is: you are the Owner, nothing else is, and every tool gets a role narrower than yours.

## Step 5: a budget, before any resource exists

Open **Cost Management**, choose your **subscription** as the scope, and create a monthly budget at your lower number with an email alert. Add a second at your higher number. Microsoft's budget documentation (read 2026-10-16) says:

- You can set alerts on **actual** or **forecasted** cost, up to five thresholds and five email addresses per budget.
- Budgets are **evaluated every 24 hours**, on cost data that is typically available **8 to 24 hours** after the spending. Notification emails normally arrive within an hour of the evaluation.
- **"Resources aren't affected, and your consumption isn't stopped."** A budget notifies. It does not stop spending. A budget can call an *action group* (at subscription or resource-group scope), which can run automation such as a function or a webhook. So you could *build* something that stops resources, but it is not built in, and it would act on data that is up to a day old.
- Add `azure-noreply@microsoft.com` to your approved senders so the alerts do not land in junk.
- Budget creation needs the Owner role on the subscription, or Contributor (who can manage their own budgets); Reader and Cost Management Reader roles can only view them.
- **A new subscription may not allow budgets at once.** Microsoft says it can take up to **48 hours** before you can use all Cost Management features on a new subscription. That is a real conflict with "budget before any resource". The rule here is the one that survives: **if you cannot create the budget yet, create nothing yet.**
- A budget is not a spending limit. The spending limit in Step 2 is a separate feature that exists only on credit-type subscriptions, and it does not stop every charge: some Marketplace items are billed separately even when it is on.

*Checkpoint: a budget exists, its email address is one you read, and you have seen it listed. An alert you cannot point at is not an alert.*

## Step 6: Cost Management access

Cost data is visible through Azure role assignments. For a non-enterprise subscription, a user needs at least read access at the management-group, subscription or resource-group scope; the **Cost Management Reader** role gives exactly that without any ability to change resources. Microsoft says you need at least User Access Administrator or Owner on a scope to give others access to its costs. Enterprise Agreement accounts add extra billing-portal switches ("account owners can view charges"); an individual learner should not meet those.

If you will ever share the subscription with someone who should see the bill but not change anything, Cost Management Reader is the role to give them. Do not hand out Owner to make the billing page appear.

## Step 7: choose a region, and stay in it

Resources live in a region. This wiki's price figures are all for **East US**; no other region was priced, so do not assume another region costs the same. Two things Microsoft's documentation does say:

- A **resource group has its own location**, which only determines where the group's metadata is stored. Its resources can be in other regions, but Microsoft recommends the same one.
- Azure's NAT gateway price meters came back from the retail price API as "Global" with no East US row on 2026-10-16. **UNVERIFIED:** whether an East US NAT gateway costs the same. See the cost lesson.

Whether your chosen VM size is offered in your chosen region was not checked for any region. The portal shows what is available when you create the machine. Choosing a region for data residency is a separate, real decision.

## Step 8: what is deliberately not here yet

- **The identity that lets Spacelift act in your subscription.** It must exist before the first apply, so it comes after your admin identity and is covered when the build is written. **Whether the Spacelift plan you use includes the managed Azure integration is not stated in Spacelift's Azure documentation (read 2026-10-16); check your own plan** before relying on it.
- **Any OpenTofu.** Nothing in this page needs it.
- **Any resource.** Your subscription is empty.

## Try it yourself

- **Predict, then check.** Before you re-read Step 2, write down what you think happens to resources when a free account's credit runs out, and what removes the protection. Then read it. What did you get wrong?
  *Reference: the spending limit stops the services (virtual machines are stopped and deallocated; stored data becomes read-only). Upgrading to pay-as-you-go removes the limit and re-enables the subscription, which is the moment you are exposed to ordinary billing.*
- Put these in order, largest to smallest scope: resource group, tenant, subscription, resource, management group. Which of them does deleting "everything in this experiment" correspond to?
  *Reference: the tenant is the directory, beside the scope chain. The scope chain is management group, subscription, resource group, resource. Deleting a resource group deletes all resources in it, so that is the unit of "everything in this experiment" if you put the experiment in its own group.*
- You are the tenant's only Global Administrator and your phone is stolen. Name two things from Step 3 that decide whether you recover.
  *Reference: a second registered MFA method, and a recovery path (or emergency access account) that does not depend on the stolen device.*
- Your budget is $20 and your forecast shows $19. A VM bill spikes by $60 in one afternoon. When do you find out, and what stops the spending?
  *Reference: at the next 24-hour evaluation at the earliest, on data that is 8 to 24 hours old, so up to a day or more later. Nothing stops it: you stop it. (On a free account, the spending limit would stop it at the credit amount, but not for charges billed separately.)*
- List three ways someone could end up in control of your Global Administrator account. Which step closes each?
  *One reasonable answer: a stolen password (Step 3, MFA), a phished MFA prompt or device-code approval (Step 3, number matching in the Authenticator app and device code blocked), a standing secret left in a repository (Step 4).*

Next: [the same four pieces on Azure](Provider-Azure-The-Same-Four-Pieces.md).
