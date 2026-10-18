# Why I picked these tools

> If any of the tool names below are new, [Architecture overview](Architecture-Overview.md) shows where each one sits first. This page is opinion, my own, and it says so. [Enterprise habits](Enterprise-Engineering-Habits.md) covers the engineering side of the same choices.

I could have built all of this on open source, and I know that, because Infisical for secrets, Keycloak or Authentik for identity, and NetBird, Headscale or OpenZiti for zero trust all exist and are good. Tailscale's core client is open source too, but its coordination server is not, and Headscale is the community's self-hosted answer to that. So the question you should be asking is why Spacelift, DigitalOcean, Doppler and Twingate, and the answer is that I wanted this to look as close as I could get it to the enterprise environments I have actually worked in.

## Disclosure first

Doppler sponsored content I made years ago, and that is how I found it. They did not sponsor this project or this page. I liked the product enough that I have used it ever since, on every project I have done myself, and I recommend it, so you should still weigh my opinion accordingly because I am not a neutral reviewer.

## Where each piece came from

| Piece | Why it is here | Where I would use it |
|---|---|---|
| GitHub | Where everything lives, and the pull request is the unit of change. | Personal and enterprise |
| Spacelift | I learned infrastructure pipelines on it, so it is the one I can teach honestly. | Personal and enterprise |
| OpenTofu | I started on Terraform and moved when HashiCorp changed the licence to the Business Source License. A broadly compatible language and provider ecosystem, `tofu` instead of `terraform`. | Anywhere |
| Doppler | One place for secrets with a read-only token per consumer, and the easiest secrets tool I have used. | Personal and enterprise |
| DigitalOcean | Cheap, with a straightforward price list. I ran email, WordPress and whole client environments on it at an MSP, and most of what I know about cloud and running servers started there. | Personal and small business |
| Twingate | I wanted Zscaler in the lab and could not afford it, and Twingate does the access part well enough that it has served me well. | Personal and small business |
| Wazuh | Open source, free, and I already ran it at home. | Personal, labs and small shops |

## What Twingate does not do

Twingate's core product is zero trust network access, and that means it decides who can reach which host and port. It is not a secure web gateway or a CASB, and the access product does not do data loss prevention (DLP), so it does not read the content of what crosses it and stop a customer list leaving in a file upload. Twingate has been adding browser-side controls, so check what it offers today before you take my word for the gap. I would love to have that, and for these lessons it does not matter at all, which is why I am telling you now instead of letting you find out.

DLP in a real company commonly works in three places. At the network or cloud edge a proxy inspects traffic and blocks content that matches a policy, at the endpoint an agent watches files, clipboard, USB and uploads, and in the SaaS and cloud apps themselves an API integration scans what is already stored and shared. Each one catches things the others miss, and all three need someone to write and tune the policies, which is the part that actually takes the time. The same vendors that do this are now also watching what AI agents do and letting you block them individually, and CrowdStrike and Zscaler both sell products in that space (check their current product names, they change). That is a whole lesson on its own and this repository does not cover it.

## Why Wazuh and not Splunk

In the businesses I have dealt with it was not Wazuh. It was more likely Splunk, and it could just as easily be CrowdStrike Next-Gen SIEM, Graylog, Datadog or something else. I picked Wazuh because it is free, I could run it at home, and the ideas carry over: agents ship logs, rules turn lines into alerts, and someone has to decide what is worth waking up for. If you learn that here, moving it to a different SIEM means learning a different query language, schema and set of parsers, but the thinking is the same.

## Clouds

DigitalOcean is the one I love for personal use, and I would reach for it and Twingate at a small business or SME. At a large enterprise I would look elsewhere, for deeper DLP coverage at the network level and for datacenter capability, and AWS is where I would look first because in my experience it has by far the widest and most mature set of services. Azure is on the roadmap here because I need to learn it myself, and I will be honest that I question the sanity of anyone who picks it on purpose. But plenty of companies are on it already, so the lessons are worth having.

## Take it as one path

None of this is the only way to do it, and a team with different needs, a different budget or a different cloud would build something different and be right. So swap the pieces: the structure of the project (everything as code, secrets out of the repository, no inbound ports, every change reviewed) does not depend on any one of these products.
