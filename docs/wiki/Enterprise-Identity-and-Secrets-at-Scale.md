# Enterprise identity and secrets at scale

> **Orientation, not a design guide: verified claims dated.** Claims checked against a vendor or standards page carry the date they were checked (2026-10-16) and the source in the claims register at the bottom. Everything else is general industry knowledge or marked UNVERIFIED. Vendor features and plan tiers change; check the vendor's current documentation before relying on any of it.

**Prerequisites:** [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md), [Doppler and secrets](Doppler-and-Secrets.md) and [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md).

In this project, identity is one administrator and secrets are a handful of tokens that expire every 90 days. In a company, identity is thousands of people, tens of thousands of devices and many more **non-human** identities (services, pipelines, scripts), and the number of secrets grows with the number of systems. The questions are the same four you already know: who is it, can they prove it, what may they do, and what did they do. The rest of this page is how those questions are answered at scale.

## Contrast at a glance

| Question | In this project | In an enterprise |
|---|---|---|
| Who are the people? | One administrator, sign-in through Twingate | A workforce identity provider (IdP) holding every employee, contractor and group |
| How do they sign in? | One identity, MFA on each account | Single sign-on to hundreds of applications, MFA enforced centrally |
| How are accounts created and removed? | By hand, once | Automatically, driven by HR events (joiner, mover, leaver) |
| What may people do? | Everything the one admin may do | Roles and attributes, reviewed regularly |
| Who holds standing admin rights? | One person, always | Few or none: elevated access is requested, approved, time-limited and recorded |
| How do machines authenticate? | A read-only token in a Spacelift context, 90 days | Short-lived credentials exchanged from the machine's own identity |
| Where do secrets live? | Doppler, one project, one `prd` config | A secrets manager or vault per environment, with rotation and audit |
| Who checks? | The operator, by habit | Access reviews, audit logs and an auditor |

## People: IdP, SSO, MFA and conditional access

An **identity provider** is the system of record for who works here. **Single sign-on (SSO)** lets a person sign in once to the IdP and reach many applications through a standard protocol, usually SAML or OpenID Connect. **MFA** is enforced there once instead of per application, and the strongest forms (hardware security keys, passkeys) resist phishing. **Conditional access** makes the decision depend on context: managed device or not, risky location, sensitive application, unusual behaviour. A single policy can say "an unmanaged device may read email but not the admin console".

SSO is also a security argument for IT: when a person leaves, disabling one account blocks new sign-ins everywhere that trusts the IdP. That is not the same as complete offboarding: sessions and tokens already issued may stay valid until they expire or are revoked, accounts and credentials that are independent of the IdP (local accounts, API keys, SSH keys) are untouched, and SCIM alone does not guarantee revocation, so downstream deprovisioning and session or token revocation have to be handled too. It is also a single point of failure and a high-value target, which is why IdP administrators are among the most protected people in a company.

**In this project:** the Twingate sign-in is the only SSO-like moment. One administrator, one MFA setup, and the [Twingate](Twingate.md) group `cah-tor1-admins` is the whole directory.

## Provisioning: SCIM and joiner, mover, leaver

Creating accounts by hand does not scale, and removing them by hand does not happen reliably. The **joiner, mover, leaver** (JML) lifecycle is the formal name for three events:

- **Joiner:** a new person arrives; accounts and group memberships should appear, with the minimum they need on day one.
- **Mover:** the person changes role; old access should be removed as new access is added. Skipping the removal is how long-serving employees accumulate far more access than anyone intended.
- **Leaver:** the person departs; every account should be disabled promptly, including the ones nobody remembers.

**SCIM** (System for Cross-domain Identity Management) is a standard protocol an IdP uses to create, update and disable accounts and group memberships in other applications automatically. When an application supports SCIM, the IdP's group becomes the application's group, and the leaver step is one change. Applications that do not support it are handled by tickets, scripts or manual checklists, and they are where the stale accounts live.

## Authorization: RBAC and ABAC

- **RBAC (role-based access control):** people hold roles; roles hold permissions. Simple to explain and audit; roles multiply over time ("role explosion").
- **ABAC (attribute-based access control):** decisions use attributes of the person, the resource and the context, such as department, data classification and time. More flexible, harder to reason about and to audit.

Most real systems mix them. The practical skill is writing roles that match tasks rather than people, and reviewing them.

## Privileged access: PAM, just-in-time and break-glass

Administrator accounts are the most valuable thing an attacker can obtain. Enterprises reduce **standing privilege**:

- **PAM (privileged access management)** vaults administrator credentials, checks them out for a purpose, and can record sessions. The [landscape page](Small-Example-Enterprise-Landscape.md) names Delinea as an example.
- **Just-in-time (JIT) access** grants elevated rights for a limited time after a request and an approval, then removes them.
- **Separate admin accounts** keep the account used for email and the web apart from the one that can change the domain.
- **Break-glass accounts** are emergency administrator accounts, stored sealed, for when the IdP itself is unavailable or an automated lockout has locked everyone out. They are excluded from the normal conditional-access rules on purpose, so their use must be loudly alarmed, tightly guarded and tested, because they are the exception to every control on this page.

**In this project:** one person holds standing access to everything. The [threat model](Threat-Model.md) accepts that, and PAM is the product class that would close the gap.

## Machines: service accounts and workload identity

The fastest-growing group of identities is non-human. A pipeline needs to deploy; a service needs to read a database. The old answer was a **service account with a long-lived key** in a configuration file, which is the secret that leaks. The better answer is **workload identity**: the platform running the job already knows what it is, so it presents a short-lived signed token and a trust relationship says "this repository, on this branch, may assume this role for ten minutes". The protocol most commonly used is OpenID Connect (OIDC) federation. GitHub Actions, GitLab CI, Kubernetes and the large clouds can all issue such tokens (general knowledge; the Doppler docs list GitHub, GitLab, CircleCI and Kubernetes among the issuers it accepts, see the register).

This is the thing to understand in this project's Doppler design: a `DOPPLER_TOKEN` read-only service token stored in a Spacelift context is exactly the kind of long-lived secret that OIDC federation exists to remove. It is the "first secret" problem described on the [landscape page](Small-Example-Enterprise-Landscape.md#secrets): the token is small, scoped to one config and one project, read-only and expires, which is the second-best answer.

## Secrets: vaults, rotation and certificates

A **secrets manager** stores values encrypted, controls who can read them, records every access, and ideally helps rotate them. At scale the problems are:

- **Sprawl:** secrets in code, chat, wikis and spreadsheets. Scanning tools in CI and on repositories look for them.
- **Rotation:** changing a secret on a schedule or after an exposure without breaking its users. Easy for one token, hard for a password embedded in forty applications. **Dynamic secrets** avoid it by issuing a credential per request that expires on its own; Vault-class tools are known for this.
- **Environments:** development, staging and production must hold different values and different access, not one shared set.
- **Blast radius:** a leaked token should expose one thing. Scoping by project and config, as in this repository, is the mechanism.
- **Certificates:** a **PKI (public key infrastructure)** issues certificates for servers, devices and people. The failure mode is expiry: an unrenewed internal certificate can take down a service on an ordinary Tuesday. Automation (short-lived certificates, ACME-style renewal) is the cure; a certificate inventory is the minimum.

## Audit and access reviews

Controls matter only if you can prove they worked. Two routine activities do that:

- **Audit logs:** who signed in, who changed which access, who read which secret, kept somewhere an administrator cannot quietly edit, and ideally sent on to the SIEM.
- **Access reviews (recertification):** a manager or system owner periodically confirms that each person's access is still needed, and removes it if not. Auditors ask to see the evidence.

## Where Doppler and Vault-class tools sit

Doppler is a hosted secrets and configuration manager. Its documentation says it keeps secrets and application config in sync across machines, hosting providers, CI/CD tools and secrets managers, and its pages address developers, platform teams and security teams; its user-groups page targets large and enterprise organizations (register, retrieved 2026-10-16). The landscape page compares it in context with Vault-class tools, each cloud's secrets service, Bitwarden Secrets Manager and Infisical, with no ranking; this page does the same by naming what the vendor's own documentation says it offers for each enterprise concern.

| Enterprise concern | What Doppler's documentation describes (retrieved 2026-10-16) |
|---|---|
| Environments and configs | Projects contain environments and configs, with branch configs and config inheritance |
| Machine access | Service tokens scoped to one config in one project, read-only by default, with optional expiry; service accounts that tie activity to the account rather than a person (Team or Enterprise plan); OIDC identities so a CI tool exchanges its own token without a static one (Team or Enterprise plan) |
| Roles | Custom roles for workplace and project permissions (standard on the Enterprise plan, or an add-on to Team); user groups for project access at scale (plan wording on the page is inconsistent; confirm) |
| SSO and provisioning | SAML SSO with guides for Auth0, Authentik, AWS, Duo, Google, JumpCloud, Microsoft Entra ID, Okta and OneLogin; SCIM with guides for Authentik, Duo, JumpCloud, Microsoft Entra ID, Okta and OneLogin. Plan requirements for SSO and SCIM were not stated on the pages read; confirm |
| Audit | An activity log entry for actions the team takes; config changes link to a version history. Retention and export were not stated on the page read; confirm |
| Integrations | Syncs to cloud secret stores (AWS Secrets Manager, AWS Parameter Store, Azure Key Vault, GCP Secret Manager), hosting platforms, CI/CD services, Kubernetes and Terraform Cloud |

Whether any of this beats the alternatives for a given organization depends on things this page cannot see: where the workloads run, who already pays for what, whether dynamic secrets are required, and whether the team wants to run the service or buy it. Weigh the operating burden, not only the feature list, as the landscape page says.

## How the repository's model scales up, or breaks

The model is Doppler for secrets, Spacelift for runs, Twingate for people reaching hosts.

| Piece | Scales how | Breaks where |
|---|---|---|
| One Doppler project and `prd` config | More projects and configs, one per application and environment, with roles and groups | A single shared `prd` config means every stack's token can read every secret, as the Doppler page already notes about stack 00 and 10 |
| One read-only service token in the Spacelift context | Fine for a handful of stacks | Rotated by hand every 90 days; at hundreds of stacks that is a chore and an outage waiting for an expiry. Moving to OIDC-based exchange removes the stored token (whether Spacelift can be a trusted issuer for Doppler is UNVERIFIED here: Doppler's page lists a custom discovery URL option, which suggests it may be possible) |
| Spacelift context labels and push policy as the protection | Policy-as-code scales if reviewed | Two different protections. The technical boundary is the attached push policy (`.spacelift/policies/push.rego`), which never proposes pull-request runs, so branch-controlled code does not run beside the Doppler context token; it must stay attached, and the page on Spacelift has the paid-plan and free-plan caveat. The organizational part is trust in whoever can write to `main`, which no policy file replaces |
| Twingate group with one admin | Groups sourced from the IdP, and SCIM, keep memberships current | Hand-managed membership drifts; leavers get missed |
| Hand-tracked expiry dates in a password manager | Fine for four tokens | Needs a monitored inventory with owners and alerts |

None of that makes the design wrong. It makes it **the right size**, with clear places to grow.

## Predict, then check

1. A person moves from the finance team to the marketing team. Which of joiner, mover and leaver is it, and what usually goes wrong?
2. A CI job has a cloud access key stored in the CI settings. Name the risk and the pattern that replaces the stored key.
3. The identity provider is down and the on-call engineer cannot sign in to fix it. Which control was designed for this, and what must be true about it?
4. In this repository, which single secret, if leaked, would let someone read all the others? What limits the damage?
5. Why does a read-only token that expires in 90 days still need an owner?

### Reference answers

1. Mover. Old access is not removed when new access is granted, so the person keeps finance access they no longer need.
2. A long-lived secret that can leak from logs, forks or the settings page and works from anywhere. Replace it with OIDC federation: the job presents a short-lived signed token and a trust rule names the repository and branch allowed.
3. A break-glass account. It must be stored securely and excluded from the normal sign-in dependency, alarmed on every use, tested, and its use reviewed afterwards.
4. The Doppler service token in the Spacelift context. It is read-only, scoped to one config of one project, expires in 90 days and is a write-only variable in Spacelift, so it cannot write to Doppler and cannot read other projects. Read-only access to Doppler does not make what it retrieves harmless, though: the config holds a DigitalOcean token with create, update and delete scopes and a Twingate key that can read, write and provision, so a leaked Doppler token can lead to infrastructure changes, not just disclosure of values. The write-only setting in Spacelift does not limit damage once the value has been extracted. The [Doppler page](Doppler-and-Secrets.md) is honest that the per-stack "gets" lines are least privilege for honest code, not isolation.
5. Someone must know it expires, rotate it before it does, and revoke it if it leaks. An expired token warns nobody; the next run just fails.

## Try it yourself

- Read the SCIM page of one IdP and one application. Write down which events (create, update, disable) flow, and what the application does on "disable".
- List every non-human identity in this repository (Spacelift, CI, Twingate API, DigitalOcean token, connector tokens). For each, write its owner, scope and expiry, then mark the one you would move to short-lived credentials first.
- Write a three-line break-glass policy for a pretend two-person company.
- Look at Doppler's service-token and OIDC-identity pages and write down what a switch from the stored token to OIDC would change in the Spacelift context.

## Claims register

Status is one of: `Verified <date>` (checked against the named source on that date), `General knowledge` (widely held industry usage, not checked here), or `UNVERIFIED`.

| Claim | Status | Source |
|---|---|---|
| Doppler describes itself as keeping secrets and application config in sync across machines, hosting providers, CI/CD tools and secrets managers | Verified 2026-10-16 | https://docs.doppler.com |
| Doppler docs address developers, DevOps/platform teams and security teams, and the user-groups page targets large and enterprise organizations | Verified 2026-10-16 | https://docs.doppler.com and https://docs.doppler.com/docs/user-groups.md |
| A Doppler service token gives access to one config in one project, is read-only by default, and can be given an expiry | Verified 2026-10-16 | https://docs.doppler.com/docs/service-tokens |
| Doppler service accounts tie activity to the account rather than a user and require the Team or Enterprise plan | Verified 2026-10-16 | https://docs.doppler.com/docs/service-accounts.md |
| Doppler service account identities allow OIDC authentication without a static token, require Team or Enterprise, and name GitHub, GitLab, CircleCI, Kubernetes and AWS IAM Outbound Identity Federation | Verified 2026-10-16 | https://docs.doppler.com/docs/service-account-identities.md |
| Doppler custom roles are standard on Enterprise and available as a Team add-on | Verified 2026-10-16 | https://docs.doppler.com/docs/custom-roles.md |
| Doppler user groups: plan requirement stated inconsistently on the page (Enterprise standard or Team add-on versus Enterprise only) | Verified 2026-10-16 | https://docs.doppler.com/docs/user-groups.md |
| Doppler SAML SSO guides exist for Auth0, Authentik, AWS, Duo, Google, JumpCloud, Microsoft Entra ID, Okta and OneLogin | Verified 2026-10-16 | https://docs.doppler.com/docs/saml-sso.md |
| Doppler SCIM guides exist for Authentik, Duo, JumpCloud, Microsoft Entra ID, Okta and OneLogin | Verified 2026-10-16 | https://docs.doppler.com/docs/scim.md |
| Doppler generates an activity log entry for team actions; config changes link to a version-history log | Verified 2026-10-16 | https://docs.doppler.com/docs/workplace-logs.md |
| Doppler syncs include AWS Secrets Manager, AWS Parameter Store, Azure Key Vault, GCP Secret Manager, Kubernetes and Terraform Cloud | Verified 2026-10-16 | https://docs.doppler.com/docs/integrations.md |
| Doppler SSO and SCIM plan requirements, log retention and log export | UNVERIFIED | the pages read did not state them |
| Spacelift can act as an OIDC issuer Doppler would accept | UNVERIFIED | not checked |
| JML, SCIM, RBAC/ABAC, PAM, JIT, break-glass definitions | General knowledge | not checked; widely used terms |
| Vault-class tools are known for dynamic secrets | General knowledge | not checked here; see the landscape page |
| GitHub Actions, GitLab CI, Kubernetes and the major clouds can issue OIDC tokens | General knowledge | not checked here, except where Doppler's page lists them |

Next: [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md). Back to the [Reading order](Reading-Order.md).
