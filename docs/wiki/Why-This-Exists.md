# Why this exists

> Nothing to read first. This page is opinion, my own, and it says so. If a word is new, the [Glossary](Glossary.md) defines it. For the tool choices specifically, [Why I picked these tools](Why-I-Picked-These-Tools.md) goes piece by piece.

I built this because I was sick of zero trust knowledge being locked behind the companies that sell it, where you can only find out how a ZTNA platform really works by paying for the platform, and then listening to a sales pitch while you do. Every vendor says they are the right answer, and Zero Trust is still poorly understood until you are inside an enterprise, so the people who most need to learn it (the ones who are not inside one yet) get the marketing version.

This is me distilling and condensing what I learned over almost four years of working with zero trust network access and enterprise networks, into something you can read for free and try for a price you choose.

## Where I am coming from

It took me around six months to learn this, and that was with the advantage of administering Zscaler at work. I had architects whiteboard it for me and spend hours with me, and I went through a lot of documentation. If that is what it took with a paid platform, a team around me and a job that required it, I do not think it is reasonable to expect anyone to piece it together alone from vendor pages.

So the lessons here are my attempt to remove the part that cost me the most, which was the head bashing, and keep the part that taught me something. I would rather you spend your time on the second one.

I am not going to say more about my job than that. What I know about enterprise networks I know from doing it, and where I only know something from reading, the pages say so.

## Why Twingate

If Zscaler were more affordable I might have used it here, and I say that from working with it every day. It is not, at least not for one person with a homelab, so I settled on Twingate, and I use it myself.

The reason that matters for this project is the connector. In both Twingate and Zscaler there is a node you deploy inside the network you want to reach, and it dials out, so you do not open an inbound port. That means it can sit in front of devices that cannot run an agent, such as IoT gear, and you reach them through it without building a jump host. In this repository the connectors are two small droplets, and [Twingate](Twingate.md) and [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) show the rest.

Plenty of you will reach for Tailscale or something like it, and that is a fair choice, so here is the comparison as fairly as I can make it.

| Question | Twingate | Zscaler (ZPA) | Tailscale |
|---|---|---|---|
| Reaching a device that cannot run the client | Deploy a connector next to it; it dials out. | The same idea: an App Connector. Not read from a vendor page, **est.** | A subnet router extends your tailnet to "devices that don't or can't run the Tailscale client" (Tailscale docs). |
| How access is described | Per resource, per group, set in the admin console or in code. | Per application segment, **est.** | Access rules over the tailnet, with a subnet router advertising routes. |
| What it costs a hobbyist | There is a free tier at the time of writing, **est.** (check the pricing page). | Sold to enterprises; I could not afford it for a lab. | There is a free personal plan, **est.** (check the pricing page). |

I am not saying Tailscale is wrong. It also reaches devices that cannot run a client, and for plenty of homelabs it is the simpler tool. What pulled me toward Twingate was that its model (a connector, resources, groups, and per-resource policy) is the closest thing I could afford to what I work with in an enterprise, and the point of this project is to teach that model. If you use Tailscale and learn the ideas, you have lost nothing.

Sources, retrieved 2026-10-22: Twingate, [Connectors](https://www.twingate.com/docs/connectors) ("Connectors are Twingate components that are deployed behind your firewall to provide access to private Resources", read directly). Tailscale, [Subnet routers](https://tailscale.com/kb/1019/subnet-routers) (quoted above, read directly). Zscaler's help pages (`help.zscaler.com`) returned only a JavaScript shell to a plain `curl`, so I could not read the App Connector text; the Zscaler cells are from my own work with it and marked **est.** The "no jump host" point is my own experience, not a sentence from the Twingate page. Neither pricing page was read for this page, so nothing on it should be taken as a price.

## Cost, and who pays for what

This project has cost gates. They exist and I will not pretend otherwise: a change that would push the planned monthly bill past the ceiling is refused. The ceiling for the current phase and the per-phase table are on the [Roadmap](Roadmap.md#cost-per-phase), and the arithmetic and how to raise it are in [docs/cost.md](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md).

The model is pay to play, and I would like to be plain about it. The theory is free: every page is readable without an account. The hands-on part costs money, because real infrastructure costs money, and you decide what you can afford to run. The labs in [Labs: break it on purpose](Labs-Break-It-on-Purpose.md) need no cloud account and cost nothing. Going further is your call and your budget.

What I did not want was for you to depend on a CTF platform or some other subscription service to learn this, where the money flows to someone who is selling you access to the practice. Here you can run it yourself, in your own accounts, and tear it down when you are done, with a [checklist](Teardown-Checklist.md) to prove the bill is zero.

## Who it is for

If you are a self-starter who can teach yourself, you will go a long way, and this is for you. I am not trying to hand you a certificate. I am trying to give you a springboard, the way I had to build mine, with some extra twists so you hit fewer walls than I did, and to point you at real field work and complex ideas and get you thinking outside the box.

A lot of what matters at work sits in places that college classes and certifications do not touch, and I have picked up much of it from colleagues across many disciplines. I believe a good share of it is not properly covered anywhere, at least not without the bullshit and the sales pitches attached, so some of these pages are me writing down what those people taught me. The ones that are my opinion say so.

## The motto, and the method

You are not dead until you stop learning.

Question everything, on every piece, including these pages. I treat security like chess, and I keep playing against myself. Build it. Break it. Detect it. Evade it. Defend it. Then flip the board around and do it again. Build it. Break it. Detect it. Evade it. Defend it. Then flip the board around and do it again.

The reason to play both sides is that the defender who has never tried to get past their own control does not know whether it works, and the attacker who has never had to detect anything does not know what leaves a trace.

### How the loop maps onto this project's lessons

This is a rough map, not a promise that every step is covered in depth. Some steps have a lot behind them and some have little, and the table says which.

| Step of the loop | Where to do it here | How much is there |
|---|---|---|
| Build it | [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md), [Droplet hardening](Droplet-Hardening.md) | Built and applied for stages 0 and 1. |
| Break it | [Labs: break it on purpose](Labs-Break-It-on-Purpose.md), [Threat model exercise](Threat-Model-Exercise.md) | Five labs that weaken a safety property on your own computer, and a what-if exercise. |
| Detect it | [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md), [Lab: a synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md) | The detection page maps each threat to the log line that would show it. The telemetry pages are unverified drafts and nothing is deployed. |
| Evade it | [Threat frameworks: STRIDE, ATT&CK and ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md), [Threat model](Threat-Model.md) | Thin. These name how an attacker would think and what the accepted risks are. There is no red team exercise here yet. |
| Defend it | [Build your own mini SOC](Build-Your-Own-Mini-SOC.md), [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) | The gates are real. The mini SOC is an unverified draft. |
| Flip the board, again | [Trace one change end to end](Trace-One-Change-End-to-End.md) | Follow one real change through every gate, then change something and watch a different gate object. |

I have not measured what anyone gets out of this, and I am not claiming a result. If a page is wrong, or the board needs flipping somewhere I have not thought of, say so; suggestions are welcome anywhere in the project.
