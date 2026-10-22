# Deception and honeypots: start here

The hub for a small track of lessons on **deception**: planting things that nobody legitimate should touch, and watching them. A foundations side page to [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md); read that page first. This hub covers **track 1**, which needs no honeypot and no server, and **track 2**, three lessons on a cloud honeypot you run in your own account (the theory is free; the hands-on lesson uses your provider bill). Track 3 is a separate later lesson, and the [last section](#tracks-2-and-3-what-they-will-need) says what each track needs. Next: [What deception is](Deception-and-Honeypots-What-Deception-Is.md), lessons 1 and 2.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: track 1 is written; parts of it were run once, and the track-wide limits are below.** On **2026-10-21** the author ran the Linux and Python exercises on one machine (Python 3.13.5, curl 8.21.0, `inotifywait` 4.23.9.0), and each lesson says exactly what it ran. **Not run anywhere in the track:** every PowerShell command (marked **est.**), the hosted canarytoken service, the audit-framework examples, and every Wazuh rule (the rule file is an unverified draft that was never loaded into a manager). Nothing in the track is built into this repository's cloud environment, and no honeypot exists there. Nothing was priced beyond what the [register](#claims-register) cites. **Track 2** (written 2026-10-22) was read from the Cowrie and DigitalOcean documentation and **never built or run**: only its lure script, its invented-log exercises (Python and `jq`) and a syntax check of its host firewall file were run; each of its three pages says exactly what.

> **Prerequisites.** [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) and, from the foundations pages, [The terminal and your first script](Terminal-and-Your-First-Script.md) (for the exercises). About 8 to 10 hours of learner time across all six lessons (est.). Cost: none for track 1.

## The principle

**Theory is free. Hands-on uses your own accounts, your own hardware or your own provider bill.** The reading and the paper exercises in every lesson here are free and stay free. The hands-on parts of track 1 run on your own computer with your own free tools, so they cost nothing either. Later tracks have a hands-on part that uses *your* cloud account or *your* hardware, with its own figure shown first. You can take the theory only, or both; the choice is yours. The reference environment of this repository spends nothing on a honeypot until the maintainer approves the [honeypot design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md); a learner running their own does not need that approval, but the [safety minimums](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums) apply to them in full.

## The six lessons

Read them in this order. Lesson 6 comes before the hands-on lessons on purpose: it is the safety page.

| Order | Lesson | Page | What it covers | Time (est.) | Hands-on |
|---|---|---|---|---|---|
| 1 | 1 and 2: what deception is, and why a decoy alert is different | [What deception is](Deception-and-Honeypots-What-Deception-Is.md) | Decoys, lures, breadcrumbs, honeytokens, honeypots, honeynets, interaction levels; the zero-activity baseline and when it fails; reading a vendor claim | 2 to 2.5 h | Paper |
| 2 | 6: should you run one? | [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) | The eight minimums, counter-hacking, privacy, a decision tree, a one-page plan | 1 h | Paper and a reviewer |
| 3 | 3: plant a canary token | [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md) | A local tripwire you build; a fake credential; an optional hosted service with a terms review first | 1 h | Your computer |
| 4 | 4: honeyfiles on a host you own | [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md) | A decoy file and a watcher; what raises an event; forged log lines | 2 h | Your Linux computer, or PowerShell |
| 5 | 5: deception alerts in the SIEM | [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) | Structured events, a detector you run, ATT&CK mapping, draft Wazuh rules, hostile lines | 2.5 to 3 h | Your computer |

**The theory path** is the first two rows: lessons 1, 2 and 6. **The local hands-on path** adds lessons 3 to 5. Nothing in either needs an account, a server open to the internet or a purchase.

## How it fits the rest of the wiki

- Deception is a **detection** idea: it says something went wrong after prevention failed. It sits beside the telemetry pages, not in place of them.
- The path from a decoy's event to an alert reuses the one in the [honeypot design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md) (section 9): structured JSON, a file, a Wazuh agent or manager, rules. Lesson 5 is the rule-writing part of it, on invented lines.
- Wazuh and the telemetry pages are described in [Build your own mini SOC](Build-Your-Own-Mini-SOC.md). The stage 2 `auditd` work, which is written and never applied, is what lesson 4's watcher imitates by hand.
- The [Threat model](Threat-Model.md) is the list lesson 1 asks you to place decoys against.

## What track 1 does not teach

- **It does not teach running a honeypot that strangers can reach.** The lessons build tools on your own computer.
- **It does not describe any vendor product.** The category is taught from a vendor's own glossary article, reported as its claims; no product page, configuration or price was read.
- **It does not give legal advice.** The safety lesson gives minimums, not a legal opinion.

## Tracks 2 and 3: what they will need

**Track 2 is written; track 3 is a separate later lesson.** Track 2 has three lessons, in this order, and none of them deploys anything from this repository: they show the steps and you run them in your own account.

| Order | Lesson | Page | What it covers | Time (est.) | Hands-on |
|---|---|---|---|---|---|
| 6 | 7: anatomy of a cloud honeypot | [Anatomy of a cloud honeypot](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md) | The nine guardrails, the provider's acceptable-use policy, what it costs and what is not a spending cap, what visitors do (public data) | 1.5 h | Paper (free) |
| 7 | 8: Cloud Cowrie for a weekend | [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md) | Teardown first, two firewalls, a moved management port, Cowrie install, a decoy credential in its fake file system, a bounded run, a pull of the logs | 3 to 4 h plus the window | **Your own cloud account and bill** |
| 8 | 9: read what arrived | [Read what arrived](Deception-and-Honeypots-Read-the-Sensor-Logs.md) | Cowrie's JSON log read with `jq` and PowerShell, the decoy touches, the lesson 5 detector reused, how visitors spot Cowrie and what you can change | 3 to 4 h | Invented logs (free); your own logs if you ran lesson 8 |

Lesson 9's exercises 1 to 6 use invented logs, so they need no account. Sending the sensor's logs into Wazuh (the education plan's own lesson 9) is **not covered**: it is untested, and the pages say so. Track 3 is not written; the table below says what it will need. The [education plan](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-22-honeypot-education-plan.md) lays out both tracks, with lesson titles, times and gates.

| Aspect | Track 2: a cloud sensor | Track 3: an on-premises honeynet |
|---|---|---|
| What it is | A Cowrie honeypot (an imitation SSH server) on a small cloud server in your own, separate cloud account, for a bounded time. | T-Pot CE, an all-in-one honeypot bundle, on an isolated network segment, internal only at first. |
| Theory path (free) | A read-through of the merged [honeypot design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md). | A paper design of a honeynet and a read of T-Pot's README. |
| Hands-on needs | **Your own cloud account and its provider bill.** Written provider consent. A separate account that holds nothing else. Closed outgoing traffic. A written end date and a kill switch. All eight [minimums](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums). | **Your own hardware** meeting T-Pot's README sizes: 16 GB RAM and a 256 GB SSD for the main node, 8 GB and 128 GB for a sensor, as listed in its README. **A separate, verified-isolated network** with no route to anything you care about. All eight minimums. |
| What it costs you | The design prices a sensor server at $6 a month (`s-1vcpu-1gb` in `docs/cost-prices.json`, retrieved 2026-10-21) and, if you keep logs, a $5 log bucket, $11 in all, while it runs (design section 8.1). A weekend is a fraction of that. These are the design's figures, not a quote for your account. The track 2 lessons use the $6 server only, with no bucket. | New hardware cost is $0 if you already own a suitable machine (est.); otherwise unpriced, as no prices were read. Electricity is unmeasured. |
| Why it is gated | The reference environment spends nothing on it until the design is approved. You do not need that approval, but the provider's policy and the minimums are yours to follow. | The isolated network has to exist and be verified first. T-Pot also sends attack data to a community project by default, which a lesson must switch off before first start. |
| Not recommended | Opening a machine to the internet from a flat home network. | Putting T-Pot on the internet; the README's advice to forward ports 1 to 64000 is not recommended for a first run. |

Both tracks also depend on a way to get their logs to a SIEM, and how T-Pot's data reaches Wazuh is **not documented in its README** and is untested. Lesson 5 is the part of that work you can do today.

## Claims register

Retrieved 2026-10-21 unless stated.

| Claim | Source | Status |
|---|---|---|
| The lesson set, the principle, the track structure and the gating of tracks 2 and 3 | [Honeypot and deception education plan](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-22-honeypot-education-plan.md), sections 1, 4, 5 and 9 | Read in this repository |
| A sensor server costs $6 a month and a log bucket $5; $11 together; option E keeps $6 | `docs/cost-prices.json` (`s-1vcpu-1gb`: 6, retrieved 2026-10-21) and [honeypot design, section 8.1](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md) | The $6 read in the price file; the $5 bucket is the design's figure, which cites a repository note. Prices change; check before relying on them |
| T-Pot's sizes: the main node (Hive) 16 GB RAM and 256 GB SSD, a sensor 8 GB and 128 GB; the installation wants an outgoing, non-filtered internet connection; data is submitted to a community project by default and can be switched off by removing a service | [T-Pot README](https://raw.githubusercontent.com/telekom-security/tpotce/HEAD/README.md), default branch | Read. A lesson must pin one release and re-read that release's README; the default branch is ahead of the latest tag (24.04.1 when read) |
| How T-Pot's data reaches Wazuh | Not documented in the README | Untested and **UNVERIFIED** |
| Track 2: the Cowrie and DigitalOcean facts, the dataset figures, the commands | The registers of the three track 2 pages, read 2026-10-22 | Read; the cloud and Cowrie steps were never run |
| The reading order and the safety-first rule | The education plan's risk table (the safety lesson is a prerequisite of every hands-on lesson) | Read in this repository |

Not verified, plainly: everything in track 3 beyond what the plan and the design say; every cloud and Cowrie step in track 2 (see its pages); any prices other than the ones read.

Next: [What deception is](Deception-and-Honeypots-What-Deception-Is.md), lessons 1 and 2. Or return to the [Reading order](Reading-Order.md).
