# A small example: what an enterprise does differently

> Read this after [Architecture overview](Architecture-Overview.md). It assumes you know what this project builds. It is about what this project is **not**.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

Everything in this repository is a deliberately small example: two $6 machines, one person, one cloud account, a handful of tools chosen because they are cheap, have a free or small tier, and are easy to see all at once. That is what makes it a good place to learn. It is also not what you will find at a company.

An enterprise answers the same questions this project answers, usually with different products, often several at once, because it has thousands of people, hundreds of offices and applications, auditors, contracts, and a decade of decisions it cannot undo. If you leave this wiki thinking "the cloud security stack is Twingate, Doppler, Spacelift and DigitalOcean," you have learned the example, not the field.

The deeper pages on this are [Enterprise networks](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md), [Enterprise infrastructure](Enterprise-Infrastructure-Differences.md), [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md) and [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md).

The better thing to take away is the **list of questions**. Each section below names a question this project answers with one tool, says what a larger organization may use for the same question, and says what stays the same whichever product answers it.

Two honest limits first:

- **This page is a map, not a buyer's guide.** It names products so you recognize them in a job description, not to recommend or rank them. No vendor paid for placement on this page, and vendors change what their products do and what they are called. Treat anything product-specific here as the shape of the category, and check the vendor's own documentation for specifics.
- **It is not exhaustive.** The lists are examples. A real environment has more, and the author has not run every product named here.

## The questions, and who answers them

| Question | This project | Examples you may meet at a larger organization |
|---|---|---|
| How does a person reach a private resource? | Twingate ZTNA, [no VPN](Why-ZTNA-Not-a-VPN.md) | Other ZTNA and SSE (security service edge) products, such as Zscaler Private Access, Netskope Private Access and Palo Alto's Prisma Access; remote-access VPNs |
| How does a branch, data center or cloud network connect to another? | One VPC; nothing to connect | GRE and IPsec tunnels, SD-WAN, dedicated cloud links |
| What inspects and filters traffic? | A cloud firewall attached by tag, default deny | Next-generation firewalls (Palo Alto is one example of many), cloud-native firewalls, secure web gateways |
| Who are you? | Twingate sign-in, a single administrator | A workforce identity provider or directory: Okta, JumpCloud, Microsoft Entra ID and others |
| Prove it is you | MFA on each account | MFA and phishing-resistant authentication, such as Duo, often enforced by the identity provider (some products cover both jobs) |
| Who can use the admin accounts? | One person holds the root-level keys | Privileged access management such as Delinea: vaulted credentials, checkout, session recording |
| Where do secrets live? | Doppler | Bitwarden Secrets Manager, Infisical, HashiCorp Vault, a cloud's own secrets service, encrypted-in-git workflows, and others |
| How do you know something went wrong? | Planned: a Wazuh agent on each host reporting to a home SIEM ([Detection](Detection-and-Monitoring-Wazuh-and-the-Landscape.md)) | EDR and XDR (CrowdStrike, SentinelOne, Bitdefender GravityZone), cloud posture tools (Wiz), observability platforms (Datadog), a SIEM, often watched by a SOC or an MDR service |
| How does change reach production? | A pull request, CI, Spacelift with a human confirm | The same shape, which may add change tickets, approvers, separate environments and a platform team |

## Getting traffic from here to there

### Remote access: ZTNA, SSE and the VPN

This project uses ZTNA (zero trust network access) so that no machine has an open port. In a large organization the same job is often part of a broader **SSE** (security service edge) platform, which bundles ZTNA with a secure web gateway (inspect and filter outbound web traffic), a CASB (control which SaaS applications people use and what they put in them) and data loss prevention. Zscaler (Zscaler Private Access for the ZTNA part), Netskope (Netskope Private Access) and Palo Alto's Prisma Access are examples in that category. Each is a portfolio, so one company's name is not one box. They answer more questions than this project asks, because an enterprise worries about what its people send *out* to the internet as well as who comes *in* to its resources.

What stays the same is the principle on [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md): least-privilege access that depends on who and what is asking, with nothing exposed to the internet to make it work. How strictly a product enforces it varies. This project describes Twingate's model (per user and per resource, checked on every connection); other products in the category also offer broader modes, such as network-level access for particular users or sites, so check how a given product defines the object it protects.

What differs in practice: enterprises have **many** apps and **many** teams, so policy is written once as groups and tags and attached to hundreds of resources, not typed per resource as in [Twingate](Twingate.md). Rollout is a project in itself: agents on every laptop, exceptions for legacy apps, and a long period where the old VPN and the new system run side by side.

### Tunnels: GRE, IPsec and linking whole networks

Everything in this repository is about reaching *a resource* as *a person*. A different, older problem is connecting *a whole network* to another one: a branch office to a data center, a data center to a cloud account.

- **GRE** (generic routing encapsulation) is a simple way to wrap packets from one network inside packets traveling across another, which makes a point-to-point link between two routers or firewalls that behaves like a cable. GRE by itself does **not** encrypt. It is commonly paired with IPsec when the path is the internet.
- **IPsec** is a family of protocols. In the usual tunnel it uses ESP to provide encryption and authentication.
- Organizations often use tunnels like these to steer branch-office traffic to a cloud security service, so that traffic leaving that office is inspected without installing anything on each laptop in it. (People working from elsewhere still usually need a client.)
- Cloud providers sell two related things. A **managed site-to-site VPN** is an encrypted IPsec tunnel over the internet. A **dedicated private link** is a direct circuit to the provider. A private circuit is not automatically encrypted: if the traffic needs encryption, you add it, for example by running IPsec over the link. Check each provider's documentation for what its offering does and does not protect.

Why this project has none of it: there is no second network to join. One VPC, no office, and the only person who needs access reaches it as a user through Twingate. If this environment ever connected to a home network as a *network* (not a user), that would be the moment to learn this properly, and to check that the address ranges do not overlap, which is why [the VPC range is called out as a demo value](Fork-Private-Stacks-and-the-Pipeline.md#step-2-which-values-are-demo-values).

### Inspecting traffic: firewalls

The firewall here is a cloud firewall: stateful, attached by tag, default deny. It is the right size for two machines. Larger environments often add a **next-generation firewall** (Palo Alto Networks is one example, and there are many others), which looks inside traffic by application and user, not only by port and address, and often sits at the edge of a data center or in a transit network between cloud networks. They are bought for visibility, central policy, and sometimes compliance requirements that ask for a particular kind of inspection.

What stays the same: **default deny, least privilege, and writing the rule's reason down.** An enterprise firewall rulebase with thousands of unexplained rules is the same mistake as the one this project avoids, at a larger scale.

## Identity, authentication and privilege

This project has one administrator, so identity is almost trivial. In an organization, identity is the control plane for everything else.

- **Identity providers and directories.** Okta, JumpCloud, Microsoft Entra ID and similar products hold the list of people and groups, handle single sign-on to hundreds of applications, and enforce MFA. They often do more: JumpCloud, for example, also manages devices and offers LDAP and RADIUS. In many organizations the identity provider is where a joiner or leaver change reaches every other system, sometimes fed by an HR system or an identity-governance product. Many organizations have more than one because of mergers.
- **Multi-factor authentication.** Duo is a well-known example. It began as a second factor added to an existing directory and now also offers its own directory and single sign-on, which is a good example of products crossing category lines. The trend is toward factors that cannot be phished, such as hardware keys and passkeys, in place of codes a person types into a page.
- **Privileged access management (PAM).** Products such as Delinea vault the credentials for administrator, root and service accounts, release them for a limited time with an approval, and record what happened. This addresses the gap this project accepts: one person with standing access to everything.

Identity is, in many organizations, the control plane the rest depends on. What stays the same: the lessons in [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md). Who is it, can they prove it, what may they do, and can you show afterwards what they did. A larger system answers each at scale and with an audit trail.

## Secrets

This project uses [Doppler](Doppler-and-Secrets.md): one place for secrets, a read-only token per consumer, injected only when needed. Others in the same category include Bitwarden Secrets Manager, Infisical, HashiCorp Vault and each cloud provider's own secrets service. They differ in where they run (hosted or self-hosted), how they authenticate the machine asking, whether they create short-lived credentials on demand, and their pricing and licensing model. Vault, for example, has a free community edition, a licensed enterprise edition and a managed cloud service, with important features differing between them; running it yourself also means owning its storage, availability, unsealing and upgrades, which is real work. Weigh the operating burden, not only the feature list.

What stays the same, whichever you pick:

- In this project's rule, a secret is **never in the repository**, public or private. Some organizations commit secrets in encrypted form (with tools such as SOPS or Sealed Secrets) and keep the decryption keys elsewhere. That is a legitimate design with its own risks, and it is a different answer to the same question.
- Every consumer gets the **least** it needs, and a way to rotate it.
- A machine proves *who it is* to the store without a secret that is itself long-lived and powerful, when the platform allows it. The best answer to "where do I keep the first secret?" is not to have one, and the second best is to keep it small and expiring.

### Doppler is used in enterprises too

Say it plainly: this project uses Doppler, and Doppler is not only a hobbyist tool. Its own documentation addresses developers, DevOps and platform teams, and security teams, and describes features aimed at larger organizations. That is a statement about what the vendor documents, not an endorsement and not a claim about how many companies use it, which this page has not verified. What the documentation describes, retrieved 2026-10-16 from [docs.doppler.com](https://docs.doppler.com):

- **Environments and configs.** A project holds environments and configs, with branch configs and config inheritance, so development, staging and production hold different values.
- **Service tokens.** A service token gives access to one config in one project, is read-only by default and can be given an expiry. This is the token type this project uses.
- **Service accounts and OIDC.** Service accounts tie machine activity to the account rather than a person, and OIDC identities let a CI tool authenticate without a static token. Both are listed as requiring the Team or Enterprise plan.
- **Roles and groups.** Custom roles for workplace and project permissions (standard on the Enterprise plan or an add-on to Team), and user groups for project access at scale.
- **SSO and SCIM.** SAML SSO and SCIM provisioning, with guides for identity providers such as Okta, Microsoft Entra ID, JumpCloud and OneLogin. The plan requirements were not stated on the pages read, so confirm them.
- **Audit logs.** An activity log entry for team actions. Retention and export were not stated on the page read.
- **Integrations.** Syncs to cloud secret stores (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager), hosting platforms, CI/CD services, Kubernetes and Terraform Cloud.

How that compares: Vault-class tools are known for dynamic, per-request credentials and can be self-hosted, at the price of running them; each cloud's own secrets service is closest to the workloads on that cloud; Bitwarden Secrets Manager and Infisical are the other names already on this page. This page does not rank them. Plans, features and prices change; check the vendor before relying on any line above. The long version, including where this project's Doppler, Spacelift and Twingate model scales and where it breaks, is [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md).

Choosing a secrets manager is a decision about your team and your platform. Switching later is harder than choosing well, which is a reason to keep the names and shapes of your secrets tidy from the start.

## Change and delivery

The pipeline in the [capstone page](Fork-Private-Stacks-and-the-Pipeline.md#where-the-pipeline-actually-starts) has seven gates. An enterprise has the same ones with more people inside them, and may add a change request, a named approver, separate development, staging and production environments, a freeze calendar, or a platform team that owns the pipeline and offers it to everyone else. The tools differ (other CI systems, other infrastructure-as-code runners, policy engines, ticketing). The reason for every gate is the same as here. For the change-request vocabulary (standard, normal and emergency changes, CAB, freeze windows) and an honest list of what this project does not do, see [Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md).

## What you cannot get from a small example

Be honest with yourself about what this project does not teach, because it is easy to leave thinking you have seen the field.

- **Scale.** Two machines never show you what happens to a firewall policy at ten thousand rules, an identity provider at fifty thousand accounts, or a secrets store with a thousand consumers.
- **People and process.** Most failures in large environments are an unclear owner, an unreviewed exception or an offboarding step that was missed. A one-person project has none of those.
- **Procurement and constraints.** Contracts, existing vendors, regulatory requirements and "we already pay for that" decide more real architecture than technical merit does.
- **Integration.** Real environments are mostly the glue between products that were never designed for each other.
- **Legacy.** Something old, important and undocumented is always in the way.

## Where to go deeper

- Networks (campus, branch, data center, cloud, segmentation, hub and spoke): [Enterprise networks](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md).
- Accounts, guardrails, FinOps, images, IaC at scale, recovery, vendors: [Enterprise infrastructure](Enterprise-Infrastructure-Differences.md).
- Identity providers, provisioning, privilege, workload identity, vaults: [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md).
- The people who do this work and what to learn next: [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md).

## Turning this into your own learning

- Pick one row of the first table. Read the vendor's public documentation for two products in that category and write down, in your own words, which part of the question each answers differently from the tool used here. Do not look at a comparison article first; form your own view, then compare.
- Take the [threat model](Threat-Model.md) and pick a risk that was accepted on purpose. Which product from this page would you add to reduce it, and what would it cost in money, effort and new things that can break?
- Look at a job description for a cloud or security engineer. Highlight every product name. For each, find which row or rows of the table it answers, and which of its capabilities are separate products or licenses. Many will not fit one row, which is the point: products are portfolios and the questions are what stay put.
- If you work somewhere that uses several of these, ask the person who runs one how it ended up there. The history is usually more instructive than the feature list.

Next: [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md), step 2 of the detection track. For the enterprise context track, continue with [Enterprise networks](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md). Back to the [Reading order](Reading-Order.md).
