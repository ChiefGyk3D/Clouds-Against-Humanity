# Clouds Against Humanity: Honeypot (separate account)

Status: DRAFT for review. Date: 2026-10-21. Issue: #120 (epic #72). Source brief: [the 2026-10-12 edge handoff](../plans/2026-10-12-edge-dmz-handoff.md), section 7, and the [edge design](2026-10-19-edge-dmz-design.md), section 8.1.
Tooling: OpenTofu if it is ever built; none of it is built.
Scope: a design for an educational honeypot that a learner runs in a cloud account of their own, apart from this project's cloud environment. It covers the goal, why a separate account, the candidate software, the network, data handling and the provider rules, costed options, how its logs would feed the learner mini SOC, teardown, a threat model and the decisions the maintainer still owes. This is a design, not an approval. Nothing here costs money, adds a stack, changes `docs/stages/approved.json` or opens an account until the maintainer decides section 12.

Vendor facts below carry a URL and the date they were read (2026-10-21). Facts from the repository's price tables carry the table's retrieval date. Anything I did not read is marked "est." or UNVERIFIED and carries no number I could not source. Nothing in this document was run: no honeypot, no scan, no provider API call.

## 1. Purpose

A honeypot is a system whose only job is to be attacked and to record how. For a learner it makes the internet's background noise visible: within hours of a public address coming up, SSH and telnet login attempts arrive, and the attempted usernames, passwords and post-login commands are real data to read, count and map to ATT&CK techniques. That feeds the detection lessons in [Build your own mini SOC](../../wiki/Build-Your-Own-Mini-SOC.md) with data nobody had to invent.

Goals:

- A single low-interaction honeypot host in a cloud account that is not this project's, exposing the lure ports (SSH and telnet) and nothing else.
- Egress closed by default, so a compromised honeypot cannot be used to attack anyone (section 6).
- No route to any other environment and no credential, state, Doppler config, Twingate network or VPC shared with the core environment (section 3).
- Logs leave one way, as structured text, into a store the learner reads from (section 9).
- A single command that ends it, and a way to end it that does not depend on this repository (section 10).
- A cost recorded as its own figure, outside the core ceiling (section 8).

Non-goals:

- Not part of this project's apply path, ever. No stack for it under `stacks/`, no module, no Spacelift project and no `cost.json` here.
- Not a production sensor, a threat-intelligence feed or a research platform. It is an exercise.
- Not a high-interaction honeypot: no real shell for an attacker, no QEMU backend pool, no proxy mode into another system, no LLM backend (section 5.4).
- No active response, no hack-back, no scanning of attacker addresses. The honeypot is passive.
- No publication of raw logs (section 7).
- No claim that it is safe to run without the provider's consent. Section 7.4 says what the two providers' own policies require, and it is a condition, not a footnote.

## 2. What exists today

Nothing is built. Specifically:

| Thing | State |
|---|---|
| A honeypot of any kind | Not built, not costed against any approval, no account opened |
| A stack, module or `cost.json` for it | None in this repository, by design |
| A phase in `docs/stages/approved.json` | None. The honeypot is not a phase (section 8.3) |
| A cost-gate rule that keeps it out | Only the existing one: the gate refuses a provider prefix that is neither a known cloud nor in `SAFE_PREFIXES`. It would not stop someone adding a honeypot stack on a provider the gate already knows (edge design, section 8.1). The separation holds because of review and because the code lives elsewhere |
| A wiki page for learners | None. The Roadmap carries one line pointing at this document |
| The learner mini SOC it would feed | Documented in [Build your own mini SOC](../../wiki/Build-Your-Own-Mini-SOC.md); its stage 2 telemetry pieces are built and merged and none of it has been applied or measured |

Two lines in the earlier edge design are superseded here, on purpose, because the maintainer's roadmap constraint is stricter: the edge design's section 8.1 let the honeypot's logs go "over its own Twingate service account scoped to one relay endpoint". This document shares no Twingate network with the core environment, so the log path is a pull from a store in the honeypot's own account instead (section 9). The handoff's idea of pushing straight into an on-prem T-Pot Hive is dropped for the same reason and because T-Pot is not a fit for the sizes in section 8.

## 3. Why a separate account

Three separations, each for its own reason:

| Separation | What it protects | What "separate" means |
|---|---|---|
| Blast radius | The core environment and the public edge | A compromised or null-routed honeypot cannot reach, enumerate or take down anything else. No peering, no shared VPC, no shared Twingate network, no shared tag |
| Billing isolation | The $30-class ceiling and the cost gate | Its spend is its own figure in its own account with its own alert. A runaway transfer bill on a host that invites traffic cannot move the core number (section 8.3) |
| Credential isolation | Every token the project holds | A different login identity, a different API token, a different Doppler project or no Doppler at all, a different state location. Nothing from the core environment is ever present on the honeypot, and nothing on the honeypot can authenticate to anything of the core |

Why an account and not a separate team or project in the same account: the provider acts on an account. The edge design already names the risk that "an abuse report against the edge can touch the whole account, core included" (edge design, section 3.1). A honeypot is a host built to attract hostile traffic and to be compromised, so abuse reports and null-routes about it are expected, not unlikely. A suspension must land on an account that holds nothing else. A separate login identity and a separate payment method belong to the same decision (section 12, item 11).

The separation is by process, not by technology, and the repository cannot prove it. Section 13 lists a possible follow-up that would add a repository guard.

## 4. Threat model

Scope: the honeypot host, its VPC, its log path and the operator's pull job. It is not a model of the core environment. No active probing of any target happens as part of this design. Verification steps below that touch a live host run only against the learner's own honeypot, in a window the learner sets, with a stop condition of "any outbound connection not on the allow list" (section 6.2). Section 7.4 says why even that needs the provider's consent first.

Untrusted data is evidence, never instruction. That covers everything the honeypot records: usernames, passwords, commands, file names, file contents, banners and the client strings of the attacking software. Attackers choose all of it. Anything that reads those (a person, a script, Grafana, Wazuh, a model) treats it as data to look at, not as commands to follow, and strips terminal escape sequences and markup before display.

### 4.1 Assets

| Asset | Why it matters |
|---|---|
| The honeypot host (a disposable, hostile-by-design machine) | It will be compromised sooner or later; it must hold nothing worth taking |
| The honeypot account and its payment method | The thing a provider suspends; a bill the learner pays |
| The log write key | A credential on a host that will be attacked; it must be able to do one thing |
| The log store and the read key | The data, and the learner's way in to it |
| Collected session data | Attacker addresses and, possibly, other people's real passwords (section 7) |
| Captured files (malware samples) | Dangerous to handle, a hosting problem if served (section 7) |
| The learner's collector and SIEM | The far end: it parses attacker-chosen strings |
| The learner's standing with the provider | A strike on the account lingers |

### 4.2 Actors

| Actor | Capability |
|---|---|
| Internet scanner or botnet | Finds the lure ports within hours, tries default credentials, drops scripts |
| Skilled attacker who spots the honeypot | Fingerprints the emulation, leaves, or abuses the host instead of the lure |
| Attacker with an exploit for the honeypot software | Escapes the emulation to a shell as the service user |
| Third party who receives traffic from the honeypot | Files an abuse report; may retaliate |
| Provider | Reads an abuse report, then limits or suspends the account |
| Supply chain | A bad package or image pin in the build |
| A pull request author | Tries to bring honeypot code or identifiers into this repository |

### 4.3 Trust boundaries

| Boundary | Rule |
|---|---|
| Internet to honeypot | Only the lure ports are open. Everything else is dropped by the cloud firewall and again by host nftables |
| Honeypot to internet | Closed. Only the log store endpoint on 443, time sync and (during build only) the package source. Section 6.2 |
| Honeypot to anything else of the learner's | There is no path. No peering, no tunnel, no shared network |
| Honeypot to log store | One write-only credential, one prefix. The store is in the honeypot's own account |
| Log store to learner | The learner pulls, over outbound HTTPS, with a read-only credential kept at the learner's side. Nothing connects in |
| Repo to honeypot | None. No code for it is applied from this repository |
| Honeypot account to core account | No shared identity, no shared secrets store, no shared state, no shared network, no shared billing |

### 4.4 Abuse cases

1. An attacker gets a shell on the honeypot and uses it to scan or attack other hosts.
2. The same shell sends spam or joins a DDoS.
3. An attacker reads the log write key and floods the store, or overwrites earlier logs.
4. An attacker finds a path from the honeypot to other resources of the learner.
5. A captured malware sample is served, executed on the host or leaves in a backup.
6. A third party reports the honeypot to the provider and the provider suspends the account.
7. A hostile string in a log line attacks the collector, the SIEM, a dashboard or a model that reads it.
8. Session data with other people's real credentials leaks, or raw logs are published.
9. The host runs for months after the exercise and the bill climbs.
10. The honeypot is used to learn which defenses the learner runs elsewhere (fingerprinting the owner).
11. A bad pin or a poisoned package lands in the build.
12. IPv6 is on and an IPv4-only rule set leaves the other family open.

### 4.5 Ranked risks

Ranked by impact times how easy the first step is.

| # | Risk | Mitigation | Verification |
|---|---|---|---|
| 1 | The honeypot attacks others (abuse cases 1, 2) | Egress default-drop at the cloud firewall and at host nftables, for both address families; the service runs as an unprivileged user; the emulated shell is not a real shell (section 5); no proxy mode; telnet and SSH lures only | A test that renders the firewall and nftables rules and fails on any outbound allow beyond the list in section 6.2. Live: from the host, outbound connects to a test target in the learner's own other account all fail. A flow log or a counter of denied egress is read weekly |
| 2 | Account suspended after an abuse report (abuse case 6) | Separate account holding nothing else (section 3); written consent from the provider before running (section 7.4); the abuse contact is read; a short, time-boxed run; a kill switch (section 10) | Not testable in advance. Calendar item: read the abuse inbox daily while it runs. Residual risk accepted until decided |
| 3 | Pivot to the learner's other resources (abuse case 4) | Separate account, separate login, no peering, no shared secret; the host holds only the write key | A checklist run at build: the account has no resource other than the honeypot stack and the store; the write key's policy is shown and has one action. A repository guard is a follow-up (section 13) |
| 4 | Log write key abused (abuse case 3) | Write-only, one prefix, no list, no delete, no read; object names carry a random component so one object cannot overwrite another; versioning or object lock on the store if the provider offers it (UNVERIFIED, section 9.2); a size cap and a request alarm | Attempt each forbidden action with the key from outside the honeypot, against the learner's own store, and expect a denial |
| 5 | Hostile string reaches the collector or SIEM (abuse case 7) | Collector treats logs as untrusted: parse as JSON, size-limit every field, drop control and escape characters, never evaluate, never pass to a model as an instruction, escape on display in Grafana and any web view | A collector test with an oversized line, a line with terminal escapes, a line with markup and a line with a Wazuh-rule-shaped payload; each must be stored inert |
| 6 | Malware samples mishandled (abuse case 5) | Captured files go to a non-executable, size-capped directory, are hashed and are not served, executed or copied into backups; by default nothing is fetched at all (section 6.3); the hash, not the file, goes to the store | A build check that the capture directory is mounted `noexec` and capped; a log check that no object in the store is larger than the field cap |
| 7 | Personal data in the logs leaks (abuse case 8) | Retention limits, redaction of passwords, no raw-log publication, aggregates only (section 7) | Review of anything proposed for publication against section 7.3 before it leaves the learner's machine |
| 8 | Cost runaway (abuse case 9) | A billing alert set before the first apply; a time limit on the run; the kill switch; closed egress keeps transfer small (inbound is not billed by DigitalOcean, section 8.1) | The usage page after week one against section 8's arithmetic |
| 9 | Fingerprinting the owner (abuse case 10) | The host's metadata, banners and the account name reveal nothing about the learner or the project; no reuse of keys, names or tags from other work | A read of the rendered cloud-init and the host banners before the first apply |
| 10 | Supply chain (abuse case 11) | Pin the package version and checksum, current releases only, rebuild instead of patching in place | A test that fails on an unpinned package name in the build template |
| 11 | IPv6 left open (abuse case 12) | Either disable IPv6 on the host or write every rule for both families | The existing `test_ipv6_closed.py` pattern extended to the honeypot; the external check runs against the v6 address too if it has one |

### 4.6 Residual risk

A host built to be attacked will be attacked, and some attackers will get past the emulation. The design accepts that the honeypot can be compromised and limits what that buys: nothing of value on the host, no credentials but a write-only key, no egress, no route anywhere, and a rebuild or a delete as the recovery. What it does not remove: a provider acting on the account after a report, whatever the policies say (section 7.4); a zero-day in the honeypot software that hands an attacker the host until it is deleted; transfer the provider counts that the learner did not expect; and the privacy exposure of keeping data about people who never consented (section 7).

## 5. Candidate software

Facts read on 2026-10-21 from each project's current README (default branch) and, for Cowrie, its installation page (https://docs.cowrie.org/en/latest/INSTALL.html). Raw URLs: https://raw.githubusercontent.com/cowrie/cowrie/HEAD/README.rst, https://raw.githubusercontent.com/thinkst/opencanary/HEAD/README.md, https://raw.githubusercontent.com/telekom-security/tpotce/HEAD/README.md, and each project's `LICENSE` file at the same location.

| Project | What it is | Licence | Stated minimum resources | Fit for 1 GiB |
|---|---|---|---|---|
| Cowrie | A "medium to high interaction SSH and Telnet honeypot designed to log brute force attacks and the shell interaction performed by the attacker". Emulated shell by default; proxy and LLM modes exist; JSON logging | BSD-3-Clause (SPDX header in the README) | None stated in the README or the install page. It is pure Python with native dependencies for cryptography and similar; pip install into a venv is the recommended operator path. No number to cite | Plausible, unmeasured. This design does not claim it fits |
| OpenCanary | "A multi-protocol network honeypot", whose "primary use-case is to catch hackers after they've breached non-public networks" | BSD-3-Clause text in `LICENSE` (Thinkst Applied Research, 2018) | "Extremely low resource requirements; for example, it can be deployed happily on a Raspberry Pi or a VM with minimal resources". No number | Yes in the README's words, still unmeasured |
| T-Pot (telekom-security/tpotce) | An all-in-one, optionally distributed, "multiarch (amd64, arm64)" honeypot platform with 20+ honeypots and the Elastic Stack | GNU GPL v3 for the project (`LICENSE`); bundled honeypots carry their own licences, GPLv2 among them (README "Licenses") | Sensor: 8 GB RAM, 128 GB SSD. Hive: 16 GB RAM, 256 GB SSD. "At least 8-16 GB RAM, 128 GB free disk space as well as a working (outgoing non-filtered) internet connection" | No. Eight times too large, and it needs outbound access this design closes |

Reading the table:

### 5.1 Cowrie, the main candidate

It listens on SSH and telnet, records login attempts, shell commands, uploaded and downloaded files and sessions, and writes JSON for log tooling. It defaults to port 2222 and the install page documents moving traffic from 22 and 23 to it by firewall redirect, authbind or setcap. The page says "It is strongly recommended to run Cowrie as a dedicated non-root user" and "Cowrie refuses to start as root". Both fit the unprivileged-service rule. Because the lure takes port 22, the host has no real SSH: administration is by rebuild (section 10), the same stance as the edge host.

### 5.2 OpenCanary, a second sensor, optional

It covers more protocols with little weight, but its stated main use is inside a network after a breach, and its README warns that the configuration "is read while the process is running with root privileges" and must be root-owned. Its portscan module uses iptables and is disabled in the Docker build. It adds little for an internet-facing lure beyond Cowrie, so it is optional and a decision (section 12, item 3), not a default.

### 5.3 T-Pot is too heavy

The sensor edition alone wants 8 GB RAM and 128 GB disk by its own README, against a 1 GiB candidate. The README also lists outbound ports it needs for management and updates, which conflicts with closed egress, and a sensor ships to a Hive (16 GB, 256 GB) that must be reachable, which conflicts with a pull-only design. The handoff's question about arm64 is answered: the README says amd64 and arm64. It stays out of the options as a build target and stays in as a thing to read about in the lesson. Section 8.2 prices what it would take anyway.

### 5.4 Modes not used

Cowrie's proxy mode relays attacker traffic to another system, which makes the honeypot a source of connections to a target. Its pool mode runs QEMU guests. Its experimental LLM mode sends attacker input to a model, which is third-party data handling and a cost, and the handoff allowed an LLM honeypot only if it did not use the home model. None of the three is in this design. Cowrie also documents a VirusTotal integration; submitting captured files to a third party is off unless a decision turns it on, because it sends data about attacker samples outward from a host with closed egress.

## 6. Network design

Public by design, locked everywhere else.

### 6.1 Placement

One VPC in the honeypot's own account, containing one host, with its own CIDR and nothing else in it. No peering, no VPN, no Twingate connector, no private route. The address is an ordinary assigned one: a reserved address buys nothing here and a new address after a rebuild is fine.

### 6.2 Rules

Inbound: TCP 22 and 23 (the lures, redirected on the host to the unprivileged listener ports) from anywhere. Nothing else, including no administrative port. ICMP is a choice with no security consequence either way.

Outbound, default drop at both layers (cloud firewall outbound rules, then host nftables):

| Allowed | Why |
|---|---|
| TCP 443 to the log store's endpoint in the same account | Log shipping |
| UDP 123 to the provider's time source | Clocks; logs without time are useless |
| DNS to the provider's resolver, only if the shipper needs a name | Could be avoided by pinning the store's address in the build; a decision for the implementation |
| During build only: the package source | First-boot install. After the build finishes the rule is removed, and the host is never patched in place: an update is a rebuild |

Nothing else leaves: no SMTP (25 and the submission ports are the spam risk), no arbitrary TCP, no UDP, no ICMP to third parties. Both address families are written; IPv6 is simplest turned off, with a test that says so. The DigitalOcean firewall page of this repository ([DigitalOcean network and firewalls](../../wiki/DigitalOcean-Network-and-Firewalls.md)) covers how rules attach by tag and the AWS equivalent is a security group with explicit egress; both are existing project knowledge and are not re-verified here against the vendor pages.

### 6.3 Captured files and the egress trade-off

Cowrie's README says it "saves files downloaded with wget/curl or uploaded with SFTP and scp for later inspection". A wget by the attacker is a real outbound fetch from the honeypot. With egress closed the fetch fails, the attempt is still logged (the URL and the command), and the sample is not captured. With a fetch allowed, the honeypot connects to attacker-chosen servers, which is exactly "make network connections to any users, hosts, or networks unless you have permission" in DigitalOcean's AUP (section 7.4). So the default is closed egress, no downloads, URLs logged and never fetched. A restricted fetch path (a proxy that only retrieves and hashes, with size and rate caps, logging every target) is a separate decision with its own risk (section 12, item 6) and is not part of the options below.

### 6.4 Log shipping, one way out

Covered in section 9. In short: the host holds a write-only credential for one prefix in a store in its own account; the learner's side pulls. There is no listener on the honeypot for the learner to connect to, and no path from the honeypot to the learner.

## 7. Data handling, legal and ethics

This section is not legal advice. I read the two providers' policies (7.4) and the projects' READMEs. I did not read any statute, regulation or case, so the paragraphs on privacy and interception below are questions to answer with the right person, not conclusions.

### 7.1 What is collected

Attacker source addresses and ports, timestamps, client software strings, attempted usernames and passwords, post-login commands, downloaded or uploaded file names and hashes, session recordings, and fingerprints. The attempted passwords may be the real passwords of the people whose machines are doing the attacking, or of accounts leaked elsewhere. The source addresses are often other people's compromised machines or residential routers, not the attacker.

Whether an address or a session counts as personal data, and what that requires of a learner, depends on where the learner and the traffic are. It is an open question for the learner (section 12, item 13).

### 7.2 Retention

Proposed, all "est." and a decision, not a measurement or a legal threshold:

- Raw session logs in the store: 30 days, then deleted. T-Pot's README says its honeypot logs are persisted for 30 days, which is a reference point and not a rule.
- Passwords: stored as a salted hash or a truncated value if the exercise allows it; the exercise needs counts and patterns, not the secret. If the plain value must be kept for the lesson, keep it only in the learner's local analysis directory and not in any shared place.
- Derived aggregates (counts per day, top usernames, ATT&CK technique counts): up to 12 months.
- Captured files: none by default (section 6.3).

### 7.3 Do not publish raw logs

Raw logs, session recordings and attacker address lists stay private. This matches the repository rule that raw corpus data stays untracked and unpublished. What can be shared: aggregate counts, distributions, a handful of redacted example commands with addresses and passwords removed, and detection logic. An address is not published as an accusation: it often belongs to a victim. A learner's blog or class report follows the same rule.

### 7.4 What the providers' own policies say

Both pages read 2026-10-21. Neither mentions honeypots by name (a text search of each fetched page found no match). That is a finding in itself: the permission has to be asked for, because the policies do not grant it.

DigitalOcean, Acceptable Use Policy, last updated March 20, 2026 (https://www.digitalocean.com/legal/acceptable-use-policy):

- Vulnerability Testing: "You may not attempt to probe, scan, penetrate, or test the vulnerability of a DigitalOcean system or network ... or conduct any security or malware research on or using the Services, without DigitalOcean's prior written consent." A honeypot that stores attacker commands and file hashes is plausibly "security or malware research" using the service. This design treats DigitalOcean's prior written consent as a required step before the first apply, not an optional courtesy. Whether a student's lab counts is DigitalOcean's call, not mine.
- Network Abuse: "You may not make network connections to any users, hosts, or networks unless you have permission to communicate with them." This is why egress is closed (section 6).
- Intentional Interference: a DoS attack or flooding is prohibited. Under Retaliation: "behavior that results in any DigitalOcean server being the target of a DoS attack". A honeypot that draws a retaliatory flood falls under the second clause.
- Harmful Software: content that "may damage, interfere with, surreptitiously intercept, or expropriate any computer system". Hosting captured malware that is served to others would be a problem; this design never serves samples.
- Consequences: DigitalOcean may suspend or terminate, and that right "applies even if a violation is committed unintentionally or without your authorization". A compromised honeypot attacking a third party is therefore the learner's violation, whatever the intent.

AWS, Acceptable Use Policy, last updated July 1, 2021 (https://aws.amazon.com/aup/):

- You may not use, or "facilitate or allow others to use", the services "to violate the security, integrity, or availability of any user, network, computer or communications system". The words "allow others to use" are what a compromised honeypot would breach. AWS also "may consider your ability and willingness to comply with this Policy, including the policies and processes you have in place to prevent or identify and remove any prohibited content or activity", which is an argument for the egress and kill-switch design being written down.
- Abuse reports go through "our abuse reporting process".

AWS, Penetration Testing (https://aws.amazon.com/security/penetration-testing/, read 2026-10-21, no date shown on the page):

- Customers may carry out security assessments of their own AWS infrastructure on the permitted services without prior approval, and "all security testing that includes Command and Control (C2) requires prior approval". A honeypot is not a security assessment of the customer's own resources, so this page neither permits nor forbids it; it shows only what AWS treats as testing and approval territory.
- "If AWS receives an abuse report for activities related to your security testing, we will forward it to you. When responding, please provide us with approved language detailing your use case, including a point of contact that we can share with any third party reporters." That is a model for the response a learner should have ready.
- Malware testing, simulated phishing, iPerf testing and red-team style simulations go through a Simulated Events form for review. Whether captured malware samples count is for AWS to say.
- Network flooding and any DoS, "yours or otherwise", are prohibited.

What this means before running one, on either provider:

1. Ask in writing. Open a support request that describes the exercise in plain words: a passive low-interaction SSH and telnet honeypot, closed egress, one host, a stated duration, a named contact. Keep the answer. Do not infer permission from the silence of the policy.
2. DigitalOcean's wording makes written consent a requirement; AWS's makes it a prudent step that shows the policies and processes it says it will weigh.
3. Have the abuse-response text ready before the first apply, and a named person who reads the inbox.
4. Do not scan, probe or test anything you do not own from the honeypot, and do not run live verification against the honeypot until the consent covers it (DigitalOcean's clause names probing and testing; scanning your own droplet from outside is probably fine but is a question for the same request).

### 7.5 Ethics

The honeypot records people who did not agree to be recorded, and some of them are victims of someone else's malware. It is a passive instrument: it does not lure with real data, does not engage back, and does not retaliate. If a session contains evidence of a crime against a person (not the usual scanning noise), stop and ask a lawyer before doing anything with it.

## 8. Options and cost

All the options exist only on paper. Prices come from `docs/cost-prices.json` (DigitalOcean regular droplets, retrieved 2026-10-10), `docs/cost-prices/aws.json` (retrieved 2026-10-16, `us-east-1`, 730 hours a month) and, for the bucket, `docs/cost.md` (Spaces $5 a month flat for 250 GiB stored and 1 TiB outbound, read 2026-10-11). Memory figures for droplet and instance sizes are not in the price tables; the ones below are "est." and must be checked before use.

### 8.1 The options

| Option | Shape | Arithmetic | Monthly | Notes |
|---|---|---|---|---|
| A (recommended) | DigitalOcean `s-1vcpu-1gb`, Cowrie, log store, closed egress, no backups | $6 droplet + $5 Spaces = $11 | $11 | 1 GiB (est.). Spaces holds the logs; inbound transfer is not billed by DigitalOcean (edge design, section 5.7, read 2026-10-19) |
| A-small | DigitalOcean `s-1vcpu-512mb-10gb` | $4 + $5 = $9 | $9 | 512 MB (est.). Unmeasured fit for Cowrie plus the shipper; ten gigabytes of disk. Try only after A is measured |
| B | DigitalOcean `s-1vcpu-2gb` for headroom (Cowrie + OpenCanary + shipper) | $12 + $5 = $17 | $17 | Room for the second sensor |
| C | AWS `t4g.micro`, an 8 GiB gp3 root disk, a public IPv4 address | 730 h x $0.0084 = $6.13; 730 h x $0.005 = $3.65; 8 GiB x $0.08 = $0.64; total $10.42 | $10.42 + S3 | S3 request and storage price is not in `docs/cost-prices/aws.json` and I did not read it. At the log volumes of one honeypot it should be small, but that is est. and unpriced. Data transfer out is listed in that file under `not_priced`. 1 GiB memory (est.). The existing AWS twin figure uses the same arithmetic (Roadmap: $10.42 for one) |
| C-nano | AWS `t4g.nano` | 730 h x $0.0042 = $3.07; $3.65; $0.64; total $7.36 | $7.36 + S3 | 0.5 GiB (est.). Probably too small for a Python honeypot with a shipper; unmeasured |
| D | T-Pot sensor edition on a DigitalOcean `s-4vcpu-8gb` | $48 droplet; disk size of that plan is not in the table, and the README asks for 128 GB | $48 and more | Meets the README's 8 GB RAM and still needs a Hive to ship to (16 GB, 256 GB), which this design cannot reach. Rejected |
| E | Option A with no store: logs stay on the host and are read through the provider console, then the host is deleted | $6 | $6 | Cheapest and simplest as a one-evening exercise. There is nothing for the mini SOC to ingest and nothing survives a rebuild. A lesson option, not a pipeline |

A time-boxed exercise costs far less than a month: a weekend (48 hours) on option C is 48 h x ($0.0084 + $0.005) = 48 x $0.0134 = $0.64 plus the disk, which AWS bills by the GB-month and prorates (est., not read today). A week (168 h) is 168 x $0.0134 = $2.25 plus the disk (est. $0.15). DigitalOcean also bills by the hour up to the monthly price, so a week of option A is about $6 x 7/30 = $1.40 for the droplet (est., hourly billing was not re-read today) plus the bucket, which is a flat monthly charge (the repository's note says "$5 a month", so it is charged for the month even if used for a week).

### 8.2 Why not T-Pot, in money

The cheapest DigitalOcean plan in the price table that has 8 GB of RAM is `s-4vcpu-8gb` at $48. That is above the whole $30 ceiling and above the learner-soc proposal's SOC droplet. The AWS table prices only three instance types, none close to 8 GB, so T-Pot on AWS is not priced here and I do not invent a number. Oracle's free tier and Hetzner, which the handoff mentioned, are unpriced: I did not read either provider's pages for this design (section 12, item 1).

### 8.3 Recorded as its own figure, outside the core ceiling

The honeypot's monthly figure is not a stage and not a phase, and it does not appear in `docs/stages/approved.json`, `docs/cost-prices*.json` or any `cost.json`. Reasons:

- The cost gate sums stacks under `stacks/`. A honeypot has no stack here, so the gate neither counts nor can count it. That is correct: counting it would imply it shares the account and the apply path.
- It does not sit under the $30 working ceiling and does not raise it, the way `edge` ($35), `second-site` ($41) and `learner-soc` ($53) are phases that do. It has its own cap, in its own account, with its own billing alert.
- It is shown in one place in this repository: this design, with a row in the Roadmap's edge section pointing here. If the maintainer wants a standing line in `docs/cost.md` ("honeypot, separate account, not in the ceiling: $11"), that is an edit he decides (section 12, item 4). I did not make it.

Proposed figure and cap, both "est." until a decision: figure $11 a month while it runs (option A); a hard cap in the honeypot account's own billing alert of $20 a month, about twice the figure, so a surprise shows up before it hurts. The alert mechanism for each provider was not verified for this design.

## 9. Feeding the learner mini SOC and Wazuh

The honeypot is a log source for the stages in [Build your own mini SOC](../../wiki/Build-Your-Own-Mini-SOC.md). Nothing below is built.

### 9.1 The path

```text
honeypot host            store in the honeypot's account        learner's own log host
Cowrie JSON log  --PUT-->  one prefix, write-only key   <--GET--  collector (read-only key, outbound HTTPS)
(closed egress                                                      |
 except this)                                                       v
                                                          file the Wazuh agent or manager reads
                                                                    |
                                                                    v
                                                  alerts, and counts for a Grafana panel
```

The honeypot pushes batches of JSON lines as objects; the learner pulls them. Neither side opens a port. The honeypot never learns where the learner is, and the learner's side keeps the "no path into home" property that the stages before S1 have.

### 9.2 The store

An object store in the same account as the honeypot: Spaces on DigitalOcean (the $5 in option A) or S3 on AWS (option C). The write credential allows one action on one prefix. Two points are UNVERIFIED and are prerequisites to any build, to be proven by a test against the learner's own store:

- That the chosen provider can issue a key limited to writing under one prefix or bucket, with no list, read or delete. I did not read DigitalOcean's current Spaces access key documentation or the S3 policy examples for this design. The test attempts each forbidden action with the key and expects a denial.
- Whether the store supports object versioning or an immutability lock, so that an attacker holding the write key cannot rewrite what is already there. If it does not, object names carry a random component and the collector treats a changed object as an alert.

### 9.3 Into Wazuh

The learner's collector writes the pulled JSON lines to a file on the learner's log host. A Wazuh agent on that host reads the file with its log collector, or the manager does if it lives there, and rules turn lines into alerts. Which Wazuh decoders and rules fit Cowrie's JSON, and whether Wazuh's JSON log collection handles the exact field names, are UNVERIFIED: the mini SOC page states the principle, that rules for a forwarded format "are written from captured lines, not assumed", and this design follows it. Capture real lines from the learner's own honeypot, then write the rules.

No Wazuh agent runs on the honeypot. An agent holds a key and talks to a manager, which would put a manager's port and an enrollment secret on a host built to be compromised, and it breaks the closed egress rule. That is a deliberate omission and a lesson in itself.

### 9.4 What a learner can do with it

| Exercise | Output |
|---|---|
| Count login attempts per hour, top usernames, top passwords | A Grafana panel from aggregated counts |
| Detect brute force and valid-account use against ATT&CK T1110 and T1078 | A Wazuh alert on repeated failures from one source, then on a success |
| Read what the attacker did after login | Commands and file names (not the files), mapped to ATT&CK techniques |
| Compare the honeypot to the learner's own real host | Why a real SSH host sees few of these because of key-only auth and a closed port |
| Defend the pipeline | Feed the collector the hostile lines in section 4.5 risk 5 and show they stay inert |
| Measure | Time from first exposure to first attempt, attempts per day, bytes shipped per day, and the cost line |

The learner's version of the mini SOC also pairs with the cost lessons: shipping bytes, retention and a bucket are costs, and the honeypot makes each visible.

## 10. Teardown and kill switch

The honeypot is disposable by design and its recovery is deletion.

| Layer | Action | Depends on this repository? |
|---|---|---|
| 1. Normal teardown | Destroy the stack with the same tool that created it, then confirm in the provider's console that the host, firewall, store contents and keys are gone | No |
| 2. Stop attracting traffic | Remove the inbound rules in the provider's console (a one-minute action, no tool needed). The host stops receiving new sessions | No |
| 3. Cut the credential | Revoke the log write key in the provider console. The host can no longer write anywhere | No |
| 4. Delete the host | Delete the droplet or terminate the instance in the console; do not rely on a power-off, since a stopped host can still be billed (est., not re-read today) | No |
| 5. Delete the account | If a provider has acted or the learner is unsure, close the account. It holds nothing else | No |

Triggers to use the kill switch at once, without waiting: an abuse report or a provider message; a single outbound connection not on the allow list; any sign of a path to another resource; a bill over the cap; the end of the planned window; a published vulnerability in the honeypot software with a working exploit.

A time-to-live is part of the design: the exercise has an end date written before it starts, and the date is a calendar item with an alarm. An automated destroy at that date is a decision (section 12, item 12). The honeypot lives in an account the repository cannot reach, so it cannot be torn down by this repository's pipeline, and that is intended.

## 11. Recommendation

For the first exercise, option A: one DigitalOcean `s-1vcpu-1gb` droplet running Cowrie only, closed egress, no downloads fetched, no OpenCanary, logs to a Spaces bucket in the same account with a write-only key, pulled by the learner's collector, kept for at most a few weeks, in a separate account with its own login identity and payment method. $11 a month, outside the core ceiling, recorded as its own figure.

The recommendation is conditional on three things I could not settle from documents:

1. DigitalOcean's prior written consent (section 7.4). If it is refused or unanswered, switch to option C on AWS, where the policy language is broader and the consent is a prudent step instead of a stated requirement, and ask AWS the same question first.
2. A passing test that the write key can write and nothing else (section 9.2).
3. A real measurement of whether Cowrie and the shipper fit in 1 GiB. If not, option B.

If the maintainer wants no pipeline at all for a first look, option E is the cheapest way to see the data once.

## 12. Decisions owed

1. Provider and account: DigitalOcean, AWS or another (Oracle's free tier and Hetzner are unpriced and unread here). Whose account, with what login identity and payment method.
2. Who contacts the provider for written consent, with what text, and what happens if there is no answer.
3. Option: A, A-small, B, C, C-nano, D or E (section 8.1). Whether OpenCanary is included at all.
4. Where the honeypot figure is recorded: this design only, or a standing line in `docs/cost.md`. And the cap ($20 proposed, est.).
5. Where the code lives: no code in this repository (assumed), a separate private or public repository of the learner's, or only a documented lesson in the wiki. If a repository, its name, after checking what already exists.
6. Egress and malware capture: closed with no downloads (recommended), or a restricted fetch path with caps (section 6.3). Whether the VirusTotal integration stays off.
7. The log store and credential: provider, prefix layout, write-only policy, versioning or lock, and the size caps (section 9.2).
8. Retention numbers (section 7.2) and password handling (hash, truncate or keep locally).
9. Publication policy for any lesson, blog or class material (aggregates only is proposed).
10. Whether the learner sends outbound abuse reports about attacker addresses (not recommended by default: many are victims; a human reviews each one).
11. Separate login identity and a payment method with a limit, if the issuer offers one (est.).
12. Time-to-live and whether an automated destroy runs on a date.
13. Legal review: which jurisdiction applies to the learner, whether an address or session is personal data there, and what recording a third party's keystrokes requires. Not answered here.
14. Whether a wiki lesson is written now (as an unverified draft) or only after a real run.
15. Whether to build a repository guard against honeypot code or identifiers entering this repository (section 13).

## 13. Changes this design makes to the repository

Documentation only:

- This file.
- One line in the Roadmap's edge section pointing here.

No tests, no code, no stack, no `cost.json`, no change to `docs/stages/approved.json`, `docs/cost.md` or the cost gate.

A possible follow-up, not provided by this design and not built: repository policies and tests that reject any stack or resource whose name or tag marks it as a honeypot, any identifier of the honeypot account in a core file, and any reference to the honeypot's store or keys from a core module. The edge design lists the same idea; it is a decision to file as an issue, or not.

## 14. What this design does not claim

- That any of it works. Nothing was built, run or scanned.
- That Cowrie, OpenCanary or the log shipper fit in 1 GiB. The projects state no minimum for Cowrie, and OpenCanary says only "extremely low".
- That a provider allows a honeypot. Both policies are silent on the word; DigitalOcean's text requires prior written consent for security or malware research on its services.
- That the log key can be scoped as described, that the store supports versioning, or that Wazuh's JSON collection suits Cowrie's fields (all UNVERIFIED, section 9).
- Any price not in the repository's tables or on the vendor pages cited with a date. The S3 charge, AWS data transfer, hourly proration and billing-alert mechanics are not priced or not verified.
- Legal advice, or an answer to any privacy question in section 7.
- That a separate account makes the honeypot safe. It makes the harm fall on an account that holds nothing else.
