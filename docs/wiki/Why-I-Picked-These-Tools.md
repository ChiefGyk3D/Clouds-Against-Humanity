# Why I picked these tools

> If any of the tool names below are new, [Architecture overview](Architecture-Overview.md) shows where most of them sit first. This page is opinion, my own, and it says so. [Enterprise habits](Enterprise-Engineering-Habits.md) covers the engineering side of the same choices.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 5: Build and operate](Contents.md#track-5-build-and-operate) > Why I picked these tools

Previous: [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) / Next: [From commit to pipeline](From-Commit-to-Pipeline.md)
<!-- END GENERATED PAGE NAV top -->

I could have built all of this on open source, and I know that, because Infisical for secrets, Keycloak or Authentik for identity, and NetBird, Headscale or OpenZiti for zero trust all exist and are good. Tailscale's core client is open source too, but its coordination server is not, and Headscale is the community's self-hosted answer to that. So the question you should be asking is why Spacelift, DigitalOcean, Doppler and Twingate, and the answer is that I wanted this to look as close as I could get it to the enterprise environments I have actually worked in.

## Disclosure first

Doppler sponsored content I made years ago, and that is how I found it. They did not sponsor this project or this page, and I liked the product enough that I have used it ever since. I use it on every project I have done myself and I recommend it, so you should still weigh my opinion accordingly because I am not a neutral reviewer.

Twingate gave me a plan for free in exchange for a review. The free plan covers stages 0 and 1, and it has two gaps. First, my lab has an identity provider and uses SAML authentication, which the free plan does not include. That is my statement about my own lab: no Twingate page I read uses the word SAML. Twingate's [pricing page](https://www.twingate.com/pricing), read 2026-10-22, lists sign-in through Okta, Entra ID and similar providers from the Business plan up, and social login on every plan. Second, stage 2's cloud-to-home paths use Twingate service accounts, which the same page lists on the Home, Business and Enterprise plans and not on the free Starter plan; it states no limit on how many a plan holds. The details, with each source and date, are in [Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md). If you are on the free plan, use social login through a provider you already have, and see [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md#mfa-and-identity-providers) for why MFA belongs at that provider. Which social providers the free plan offers I did not read, so check the console (est.).

I also have a DigitalOcean referral link ([https://m.do.co/c/e3aaa65aed6b](https://m.do.co/c/e3aaa65aed6b)). If you sign up through it and spend, DigitalOcean credits me; the program is described on its [referral page](https://www.digitalocean.com/referral-program) (read 2026-10-22). It is optional and the project works the same without it.

I also have affiliate relationships with Proton and with Tuta, the two hosted email services the [email security lesson](Email-Security-DNS-Gateways-and-API-Driven-Protection.md#hosted-email-for-people-proton-and-tuta) recommends for an ordinary person who does not want to run a mail server. If someone signs up through my links, I may earn a commission, and that helps fund this research. I used and recommended both before I wrote this paragraph, and the recommendation is my own opinion, so weigh it accordingly. Both can be bought without my links, and the lesson says how to choose. My links are on one page, [links.chiefgyk3d.com/productrecs](https://links.chiefgyk3d.com/productrecs); this wiki embeds no individual affiliate address.

If I ever have an affiliation or sponsorship with something I recommend, I will say so here and on the page, the way I did for Doppler and Twingate.

## Where each piece came from

| Piece | Why it is here | Where I would use it |
|---|---|---|
| GitHub | Where everything lives, and the pull request is the unit of change. | Personal and enterprise |
| Spacelift | I learned infrastructure pipelines on it, so it is the one I can teach honestly. | Personal and enterprise |
| OpenTofu | I started on Terraform and moved when HashiCorp changed the license to the Business Source License. A broadly compatible language and provider ecosystem, `tofu` instead of `terraform`. | Anywhere |
| Doppler | One place for secrets, handed to the pipeline as a read-only token, and the easiest secrets tool I have used. | Personal and enterprise |
| DigitalOcean | Cheap, with a straightforward price list. I ran email, WordPress and whole client environments on it at an MSP, and most of what I know about cloud and running servers started there. | Personal and small business |
| Twingate | I wanted Zscaler in the lab and could not afford it, and Twingate does the access part well enough that it has served me well. | Personal and small business |
| Wazuh | Open source, free, and I already ran it at home. | Personal, labs and small shops |
| Grafana | It makes data from many sources readable, and I use it at home and would use it in a business. | Personal and enterprise |

## What Twingate does not do

Twingate's core product is zero trust network access, and that means it decides who can reach which host and port. It is not a secure web gateway or a CASB, and the access product does not do data loss prevention (DLP; [what that is, with a lab](Cross-Tenant-Data-Governance-Retention-and-DLP.md#dlp-in-plain-words)), so it does not read the content of what crosses it and stop a customer list leaving in a file upload. Twingate has been adding browser-side controls, so check what it offers today before you take my word for the gap. I would love to have that, and for these lessons it does not matter at all, which is why I am telling you now instead of letting you find out.

DLP in a real company commonly works in three places. At the network or cloud edge a proxy inspects traffic and blocks content that matches a policy, at the endpoint an agent watches files, clipboard, USB and uploads, and in the SaaS and cloud apps themselves an API integration scans what is already stored and shared. Each one catches things the others miss, and all three need someone to write and tune the policies, which is the part that actually takes the time. The same vendors that do this are now also watching what AI agents do and letting you block them individually, and CrowdStrike and Zscaler both sell products in that space (check their current product names, they change). That is a whole lesson on its own and this repository does not cover it.

## Why Wazuh and not Splunk

In the businesses I have dealt with it was not Wazuh. It was more likely Splunk, and it could just as easily be CrowdStrike Next-Gen SIEM, Graylog, Datadog or something else. I picked Wazuh because it is free, I could run it at home, and the ideas carry over: agents ship logs, rules turn lines into alerts, and someone has to decide what is worth waking up for. If you learn that here, moving it to a different SIEM means learning a different query language, schema and set of parsers, but the thinking is the same.

## Grafana

Grafana is the one on this list I think is most underrated, and I wish more businesses used it. It connects to a wide range of data sources, including Prometheus, SQL databases and OpenSearch (through a plugin), and it turns what it reads into something people can actually look at, so the same tool works for a homelab and for a company. Grafana OSS is open source, so you can start free and decide later whether you want anything from the company behind it, because some features are paid. I run it at home on top of the SIEM data, and this project will ship dashboards of its own, which are tracked in [issue 149](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/149).

## Clouds

DigitalOcean is the one I love for personal use, and I would reach for it and Twingate at a small business or SME. At a large enterprise I would look elsewhere, for deeper DLP coverage at the network level and for datacenter capability, and AWS is where I would look first because in my experience it has by far the widest and most mature set of services. Azure is on the roadmap here because I need to learn it myself, and I will be honest that I question the sanity of anyone who picks it on purpose. But plenty of companies are on it already, so the lessons are worth having.

## Take it as one path

None of this is the only way to do it, and a team with different needs, a different budget or a different cloud would build something different and be right. So swap the pieces: the structure of the project (everything as code, secrets out of the repository, no inbound ports, every change reviewed) does not depend on any one of these products.

Next: [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md), step 3 of the Understand the design path on the [Reading order](Reading-Order.md) page.

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 5: Build and operate](Contents.md#track-5-build-and-operate) > Why I picked these tools

Previous: [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) / Next: [From commit to pipeline](From-Commit-to-Pipeline.md)

In this track: [Track 5: Build and operate](Contents.md#track-5-build-and-operate), 32 pages

- Stage guides and design: [Fork, private stacks, the pipeline](Fork-Private-Stacks-and-the-Pipeline.md) / [Labs: break it on purpose](Labs-Break-It-on-Purpose.md) / [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md) / [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md) / [Teardown checklist](Teardown-Checklist.md) / [Self-hosting: when and why, with SearXNG](Self-Hosting-When-and-Why-with-SearXNG-as-the-Worked-Example.md) / [Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md) / [Zero trust at home: two connectors and failover](Zero-Trust-at-Home-Two-Connectors-and-Failover.md) / [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) / **Why I picked these tools** / [From commit to pipeline](From-Commit-to-Pipeline.md) / [Trace one change end to end](Trace-One-Change-End-to-End.md)
- Other clouds: [Why the clouds differ](Why-the-Clouds-Differ.md) / [AWS: account preparation](Provider-AWS-Account-Preparation.md) / [AWS: the same four pieces](Provider-AWS-The-Same-Four-Pieces.md) / [AWS: where the money goes](Provider-AWS-Cost-Lesson.md) / [Azure: account preparation](Provider-Azure-Account-Preparation.md) / [Azure: the same four pieces](Provider-Azure-The-Same-Four-Pieces.md) / [Azure: where the money goes](Provider-Azure-Cost-Lesson.md) / [GCP: account preparation](Provider-GCP-Account-Preparation.md) / [GCP: the same four pieces](Provider-GCP-The-Same-Four-Pieces.md) / [GCP: where the money goes](Provider-GCP-Cost-Lesson.md)
- Enterprise practice: [Enterprise networks: campus, branch, data center, cloud](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md) / [Enterprise infrastructure differences](Enterprise-Infrastructure-Differences.md) / [Enterprise change management (not used here)](Enterprise-Change-Management-for-Beginners.md) / [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md) / [Working in a company: tickets, change, on-call, documentation](Working-in-a-Company-Tickets-Change-On-Call-and-Documentation.md) / [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md)
- Project process: [How this project is planned](How-This-Project-Is-Planned.md) / [Project status](Project-Status.md) / [Repository growth](Repository-Growth.md) / [Screenshots policy](Screenshots-Policy.md)

Related pages:

- [Zero trust at home: two connectors and failover](Zero-Trust-at-Home-Two-Connectors-and-Failover.md)
- [Trace one change end to end](Trace-One-Change-End-to-End.md)
- [Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md)
- [Self-hosting: when and why, with SearXNG](Self-Hosting-When-and-Why-with-SearXNG-as-the-Worked-Example.md)
<!-- END GENERATED PAGE NAV bottom -->
