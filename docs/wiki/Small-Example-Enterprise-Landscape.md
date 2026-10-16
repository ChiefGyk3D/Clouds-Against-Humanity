# A small example: what an enterprise does differently

> Read this after [Architecture overview](Architecture-Overview.md). It assumes you know what this project builds. It is about what this project is **not**.

Everything in this repository is a deliberately small example: two $6 machines, one person, one cloud account, a handful of tools chosen because they are cheap, have a free or small tier, and are easy to see all at once. That is what makes it a good place to learn. It is also not what you will find at a company.

An enterprise answers the same questions this project answers, usually with different products, often several at once, because it has thousands of people, hundreds of offices and applications, auditors, contracts, and a decade of decisions it cannot undo. If you leave this wiki thinking "the cloud security stack is Twingate, Doppler, Spacelift and DigitalOcean," you have learned the example, not the field.

The better thing to take away is the **list of questions**. Each section below names a question this project answers with one tool, says what a larger organization may use for the same question, and says what stays the same whichever product answers it.

Two honest limits first:

- **This page is a map, not a buyer's guide.** It names products so you recognise them in a job description, not to recommend or rank them. I have no affiliation with any of them, and vendors change what their products do and what they are called. Treat anything product-specific here as the shape of the category, and check the vendor's own documentation for specifics.
- **It is not exhaustive.** The lists are examples. A real environment has more, and the author has not run every product named here.

## The questions, and who answers them

| Question | This project | Examples you may meet at a larger organization |
|---|---|---|
| How does a person reach a private resource? | Twingate ZTNA, [no VPN](Why-ZTNA-Not-a-VPN.md) | Other ZTNA and SSE (security service edge) products such as Zscaler, Netskope and Palo Alto's Prisma Access; remote-access VPNs; site-to-site tunnels |
| How does a branch, data center or cloud network connect to another? | One VPC; nothing to connect | GRE and IPsec tunnels, SD-WAN, dedicated cloud links |
| What inspects and filters traffic? | A cloud firewall attached by tag, default deny | Next-generation firewalls (Palo Alto and others), cloud-native firewalls, secure web gateways |
| Who are you? | Twingate sign-in, a single administrator | A workforce identity provider or directory: Okta, JumpCloud, Microsoft Entra ID and others |
| Prove it is you | MFA on each account | Duo and other MFA and phishing-resistant authentication, enforced by the identity provider |
| Who can use the admin accounts? | One person holds the root-level keys | Privileged access management such as Delinea: vaulted credentials, checkout, session recording |
| Where do secrets live? | Doppler | Bitwarden Secrets Manager, Infisical, HashiCorp Vault, a cloud's own secrets service, and others |
| How does change reach production? | A pull request, CI, Spacelift with a human confirm | The same shape, with change tickets, approvers, separate environments and often a platform team |

## Getting traffic from here to there

### Remote access: ZTNA, SSE and the VPN

This project uses ZTNA (zero trust network access) so that no machine has an open port. In a large organization the same job is often part of a broader **SSE** (security service edge) platform, which bundles ZTNA with a secure web gateway (inspect and filter outbound web traffic), a CASB (control which SaaS applications people use and what they put in them) and data loss prevention. Zscaler, Netskope and Palo Alto's Prisma Access are well-known examples of that category. They answer more questions than this project asks, because an enterprise worries about what its people send *out* to the internet as well as who comes *in* to its resources.

What stays the same: the principle on [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md). Access is decided per user and per resource, the decision is made again on every connection, and nothing has to be exposed to the internet to make it work. A product that does the job well changes which dashboard you click, not why.

What differs in practice: enterprises have **many** apps and **many** teams, so policy is written once as groups and tags and attached to hundreds of resources, not typed per resource as in [Twingate](Twingate.md). Rollout is a project in itself: agents on every laptop, exceptions for legacy apps, and a long period where the old VPN and the new system run side by side.

### Tunnels: GRE, IPsec and linking whole networks

Everything in this repository is about reaching *a resource* as *a person*. A different, older problem is connecting *a whole network* to another one: a branch office to a data center, a data center to a cloud account.

- **GRE** (generic routing encapsulation) is a simple way to wrap packets from one network inside packets travelling across another, which makes a point-to-point link between two routers or firewalls that behaves like a cable. GRE by itself does **not** encrypt. It is commonly paired with IPsec when the path is the internet.
- **IPsec** provides the encryption and authentication for a tunnel.
- Organizations often use tunnels like these to steer branch-office traffic to a cloud security service, so that all of an office's web traffic is inspected without installing anything on each laptop.
- Cloud providers sell the same idea as managed site-to-site VPN and as dedicated private links.

Why this project has none of it: there is no second network to join. One VPC, no office, and the only person who needs access reaches it as a user through Twingate. If this environment ever connected to a home network as a *network* (not a user), that would be the moment to learn this properly, and to check that the address ranges do not overlap, which is why [the VPC range is called out as a demo value](Fork-Private-Stacks-and-the-Pipeline.md#step-2-which-values-are-demo-values).

### Inspecting traffic: firewalls

The firewall here is a cloud firewall: stateful, attached by tag, default deny. It is the right size for two machines. Larger environments often add a **next-generation firewall** (Palo Alto is the best-known name, and there are many others), which looks inside traffic by application and user, not only by port and address, and often sits at the edge of a data center or in a transit network between cloud networks. They are bought for visibility, central policy, and sometimes compliance requirements that ask for a particular kind of inspection.

What stays the same: **default deny, least privilege, and writing the rule's reason down.** An enterprise firewall rulebase with thousands of unexplained rules is the same mistake as the one this project avoids, at a larger scale.

## Identity, authentication and privilege

This project has one administrator, so identity is almost trivial. In an organization, identity is the control plane for everything else.

- **Identity providers and directories.** Okta, JumpCloud, Microsoft Entra ID and similar products hold the list of people and groups, handle single sign-on to hundreds of applications, and enforce MFA. When someone joins or leaves, the identity provider is where that change happens, and everything else (including a ZTNA product) should follow from it. Many organizations have more than one because of mergers.
- **Multi-factor authentication.** Duo is a well-known product that adds a second factor, either on its own or alongside a directory. The trend is toward factors that cannot be phished, such as hardware keys and passkeys, in place of codes a person types into a page.
- **Privileged access management (PAM).** Products such as Delinea vault the credentials for administrator, root and service accounts, release them for a limited time with an approval, and record what happened. This addresses the gap this project accepts: one person with standing access to everything.

What stays the same: the lessons in [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md). Who is it, can they prove it, what may they do, and can you show afterwards what they did. A larger system answers each at scale and with an audit trail.

## Secrets

This project uses [Doppler](Doppler-and-Secrets.md): one place for secrets, a read-only token per consumer, injected only when needed. Others in the same category include Bitwarden Secrets Manager, Infisical, HashiCorp Vault and each cloud provider's own secrets service. They differ in where they run (hosted or self-hosted), how they authenticate the machine asking, whether they create short-lived credentials on demand, and what they cost per seat or per secret.

What stays the same, whichever you pick:

- A secret is **never in the repository**, public or private.
- Every consumer gets the **least** it needs, and a way to rotate it.
- A machine proves *who it is* to the store without a secret that is itself long-lived and powerful, when the platform allows it. The best answer to "where do I keep the first secret?" is not to have one, and the second best is to keep it small and expiring.

Choosing a secrets manager is a decision about your team and your platform. Switching later is harder than choosing well, which is a reason to keep the names and shapes of your secrets tidy from the start.

## Change and delivery

The pipeline in the [capstone page](Fork-Private-Stacks-and-the-Pipeline.md#where-the-pipeline-actually-starts) has seven gates. An enterprise has the same ones with more people inside them: a change request, a named approver, separate development, staging and production environments, a freeze calendar, and often a platform team that owns the pipeline and offers it to everyone else. The tools differ (other CI systems, other infrastructure-as-code runners, policy engines, ticketing). The reason for every gate is the same as here.

## What you cannot get from a small example

Be honest with yourself about what this project does not teach, because it is easy to leave thinking you have seen the field.

- **Scale.** Two machines never show you what happens to a firewall policy at ten thousand rules, an identity provider at fifty thousand accounts, or a secrets store with a thousand consumers.
- **People and process.** Most failures in large environments are an unclear owner, an unreviewed exception or an offboarding step that was missed. A one-person project has none of those.
- **Procurement and constraints.** Contracts, existing vendors, regulatory requirements and "we already pay for that" decide more real architecture than technical merit does.
- **Integration.** Real environments are mostly the glue between products that were never designed for each other.
- **Legacy.** Something old, important and undocumented is always in the way.

## Turning this into your own learning

- Pick one row of the first table. Read the vendor's public documentation for two products in that category and write down, in your own words, which part of the question each answers differently from the tool used here. Do not look at a comparison article first; form your own view, then compare.
- Take the [threat model](Threat-Model.md) and pick a risk that was accepted on purpose. Which product from this page would you add to reduce it, and what would it cost in money, effort and new things that can break?
- Look at a job description for a cloud or security engineer. Highlight every product name. For each, find which row of the table it belongs to. That is the quickest way to turn a list of logos into an understanding of the field.
- If you work somewhere that uses several of these, ask the person who runs one how it ended up there. The history is usually more instructive than the feature list.

Back to [Home](Home.md).
