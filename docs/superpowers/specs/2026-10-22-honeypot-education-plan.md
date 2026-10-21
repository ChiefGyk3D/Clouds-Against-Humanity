# Clouds Against Humanity: Honeypot and deception education plan

Status: DRAFT for review. Date: 2026-10-22. Issue: #178 (epic #74, learning and wiki). Builds on the merged [honeypot design](2026-10-21-honeypot-design.md) (issue #120, epic #72).
Tooling: none. This is a plan for lessons; no lesson page, code, stack or cost entry is added by it.
Scope: the education layer for honeypots and deception: what a learner is taught, in what order, at what cost, how the data reaches Wazuh, and when the work could be scheduled. It does not repeat the cloud honeypot's design, threat model, provider rules or teardown; it links them.

Facts carry a URL and the date they were read (2026-10-22). Anything I could not read is marked "est." or UNVERIFIED and carries no number I could not source. Nothing here was run: no honeypot, no install, no token, no scan.

## 1. Purpose and the principle

Issue #178 asks for lessons on honeypots modelled on Zscaler Deception, an on-premises path with T-Pot CE once the maintainer's malware network exists in the homelab, and a route back into the SIEM.

The maintainer's principle, stated here so every lesson and every cost line follows it:

> **A learner does what they want, at a cost they can afford. Theory is free. Hands-on is paid for by the person doing it.** Each track below has a THEORY path (no cost, no infrastructure, nothing to approve) and an optional HANDS-ON path with its own cost figure. A learner may take theory only, or run the hands-on path in their own account or on their own hardware. Cloud sensors are wanted, not discouraged.

What the principle does not change: this repository's reference environment spends nothing on a honeypot until the maintainer approves #120 (section 8, decision 1). A learner's own account is outside that gate; the safety minimums in section 7 apply to them regardless of who pays.

## 2. What the cloud design already covers (not repeated)

The [honeypot design](2026-10-21-honeypot-design.md) is merged as a draft. For Track 2 it already provides, and this plan links instead of copying:

| Topic | Where |
|---|---|
| Why a separate account | design section 3 |
| Threat model, ranked risks | design section 4 |
| Candidate software (Cowrie, OpenCanary), and why T-Pot is too heavy for a cloud droplet | design section 5 |
| Network and closed egress | design section 6 |
| Data handling, retention, provider policies | design section 7 |
| Costed options A to E | design section 8 |
| Log path into the mini SOC and Wazuh | design section 9 |
| Teardown and kill switch | design section 10 |
| Decisions owed on the cloud sensor (15) | design section 12 |

What the design leaves open and this plan adds: the lessons that teach the ideas, the honeytoken material (no honeypot needed), the on-prem T-Pot CE path, and the SIEM rule work as a lesson. The design's non-goal "no wiki lesson now" (its decision 14) is the question this plan puts back to the maintainer.

## 3. Research summary

### 3.1 Zscaler Deception: the concepts worth teaching

Source read: Zscaler's Zpedia article "What Is Deception Technology?" (https://www.zscaler.com/resources/security-terms-glossary/what-is-deception-technology, read 2026-10-22). I could **not** read Zscaler's product page or its help portal: the product URLs I tried returned a not-found page or an empty shell. So everything below about Zscaler is what a vendor glossary article says about the category; I did not read what the Zscaler product itself ships, how it is configured or what it costs. The lessons teach the category with that article as one cited source, and do not describe the product. Vendor claims are reported as claims.

Vocabulary the article uses, which makes a good lesson skeleton (my wording, not a copy):

| Term | Meaning in the article's usage |
|---|---|
| Decoy | A fake resource that looks real: a server, database, application |
| Lure | Fake information that leads an attacker to a decoy: a planted password, API key or file |
| Breadcrumb | A lure planted on a real endpoint, such as a fake cached credential, to pull an attacker sideways |
| Honeytoken | One fake data point, such as a false record in a database; needs no new infrastructure, so the article calls it a good place to start |
| Honeypot | A standalone decoy system; the oldest of these |

The central teaching claim: legitimate users have no reason to touch a decoy, so the baseline is zero activity and any touch is worth a look. The article calls the resulting alerts high-fidelity with very few false positives. Teach it as a **conditional**, not a promise: it holds for decoys *inside* a network that nobody should visit. The same article concedes that internet-facing honeypots can produce many false positives from broad scanning. That contrast is a lesson in itself (Lesson 2). The article also contrasts static honeypots with "modern" platforms that deploy and adapt decoys automatically; that is a vendor-category claim. The lesson can report it and mark it as unmeasured here.

Active Directory decoys and deceptive credentials: the article mentions Active Directory and fake credentials in general terms only. I read nothing specific to how Zscaler does either. The lessons teach deceptive credentials with canary tokens (3.3) and do not claim parity with any product.

### 3.2 T-Pot CE

Sources: the project README at the default branch (https://raw.githubusercontent.com/telekom-security/tpotce/HEAD/README.md), the README at tag 24.04.1 (same path with the tag), the licence file and the GitHub API for tags and licence (https://api.github.com/repos/telekom-security/tpotce), all read 2026-10-22.

| Fact | Value |
|---|---|
| Latest tagged release | 24.04.1, dated 2024-12-11 (tags list: 24.04.1, 24.04.0, ...). The default branch has a commit dated 2026-10-17 and is ahead of the tag |
| Licence | GNU GPL v3 (licence file and API); bundled honeypots carry their own licences |
| Hardware (README, both tag and default branch) | Hive: 16 GB RAM, 256 GB SSD. Sensor: 8 GB RAM, 128 GB SSD. "The more honeypots, sensors & data, the more RAM and storage is needed" |
| Network need | An IPv4 address (DHCP or static) and "a working, non-proxied, internet connection" |
| Install types | Standard / Hive (everything on one host, also a Hive endpoint) and Distributed (a Hive plus one or more Sensors that ship data to it). Runs on bare metal, in a VM (UTM, VirtualBox, VMware and KVM reported working), and on a Raspberry Pi 4 (8 GB) per the README. Never with a desktop environment installed |
| Operating systems | The list differs between the tag and the default branch. Tag 24.04.1 lists Alma 9.5, Debian 12, Fedora 41, openSUSE Tumbleweed, Rocky 9.5 and Ubuntu 24.04.1. The default branch lists newer releases (for example Debian 13). A lesson must pin one release and re-read that tag's README |
| Honeypots bundled (default-branch list, 31 named) | adbhoney, beelzebub, ciscoasa, citrixhoneypot, conpot, cowrie, ddospot, dicompot, dionaea, elasticpot, endlessh, galah, go-pot, glutton, h0neytr4p, hellpot, heralding, honeyaml, honeypots (qeeqbox), honeytrap, ipphoney, log4pot, mailoney, medpot, miniprint, redishoneypot, rdphoneypot, sentrypeer, snare, tanner, wordpot. Beelzebub and Galah are marked "LLM required" in the port table; the README says "a selection of the 23 available honeypots" runs depending on the chosen compose file |
| Tools | Elastic Stack (Elasticsearch, Logstash, Kibana), Elasticvue, CyberChef, an attack map, Spiderfoot, Suricata, Fatt, P0f, Autoheal, an nginx reverse proxy |
| Where logs live | Honeypot logs persist under `~/tpotce/data`; the `tpot` index lifecycle policy keeps indices 30 days |
| Management ports | 64294 (sensor data to Hive), 64295 (SSH), 64297 (web UI behind nginx), as listed in its port table. Outbound 80 and 443 for install, updates and logs; 11434 outbound if an Ollama server backs the LLM honeypots |

README warnings a learner must hear before touching it (my paraphrase of its Disclaimer and System Placement sections):

- "You install and run T-Pot within your responsibility." A system compromise "can never be ruled out"; pick the deployment accordingly. Honeypots should not hold sensitive data.
- Data is **submitted by default** to a community project (Sicherheitstacho) through the `ewsposter` service; the README describes removing that section to opt out. HPFEEDS sharing is a separate opt-in. For a learner, default-on outbound sharing of attack data is a decision, not a default to accept.
- Placement: get to know it in a VM before exposing it. To catch internet attacks it must sit in a zone that receives them. The README suggests forwarding ports 1 to 64000 to it while limiting the high management ports to trusted addresses. That advice is for someone who wants internet exposure; this plan does not recommend it for a first run (section 5, Track 3).
- It needs a working outbound internet path to install and update. That conflicts with a strictly closed malware network, and the plan must resolve it with an allow-list (section 5, Track 3 prerequisites).

**Export to a SIEM: not documented in the README.** I searched the README for syslog, filebeat, Wazuh and forwarding and found none. What it does say: Logstash ingests events into Elasticsearch, Kibana reads them, Elasticvue browses the Elasticsearch, NDJSON export is for Kibana objects only, and in the distributed layout a Sensor ships to a Hive through nginx. Honeypot logs are files under the data directory. So the following ways of getting T-Pot data into Wazuh are **est. and UNVERIFIED**, to be proven in a lab before a lesson claims any of them:

1. A Wazuh agent on the T-Pot host reading the honeypot JSON log files under the data directory. Simplest conceptually; puts an agent (a key and a manager connection) on a host built to be attacked, which the cloud design rejects for the internet-facing sensor (design section 9.3) and which is a smaller concern on an isolated internal honeynet.
2. Filebeat or a Logstash output added to T-Pot's own pipeline, shipping to the Wazuh indexer. Requires editing the Logstash configuration; whether this survives T-Pot updates is unread.
3. Querying T-Pot's Elasticsearch from the SIEM side. Requires exposing it; unread.
4. A syslog forwarder reading the log files. Plausible, unread.

### 3.3 Vendor-neutral concepts and honeytokens

- **Low versus high interaction.** The design already fixes the labels: Cowrie's emulated shell is medium interaction (design section 5.1); a port listener that only logs connections is low; a real system left for an attacker to use is high, with the danger that implies. T-Pot is a bundle of mostly low and medium interaction honeypots, plus tools.
- **Canarytokens.** Thinkst's documentation describes them as motion sensors for networks, computers and clouds: a token is typically a unique URL or hostname, placed where nobody should look, and an email arrives if it is used. The service is described as free, requires no installed software, and lists many token types (documents, AWS API keys, DNS, cloned website, SQL dump, and others). Sources: https://docs.canarytokens.org/guide/ and https://docs.canarytokens.org/guide/getting-started.html, read 2026-10-22; the guide pages carry a "last updated" mark of 2024-07-23 and the token list may have grown. I read no terms of service or privacy policy for the hosted service, so what the hosted service retains about a learner's token, memo and email is UNVERIFIED and the lesson must have the learner read it first. A learner who wants no third party can self-host the open-source version (UNVERIFIED: not read here).
- **Honeyfiles.** A decoy file with an attractive name, watched for access. The watching is the learner's own: a file-integrity or audit rule on a host they own. The existing stage 2 work already ships Wazuh with auditd as an opt-in on the cloud connectors; the same mechanism is the teaching hook (built, not applied; see the [Roadmap](../../wiki/Roadmap.md) stage 2 section).
- **How SIEMs consume honeypot data.** Honeypots emit structured events (Cowrie: JSON with fields including `eventid`, `session`, `src_ip`, `timestamp`; read at https://docs.cowrie.org/en/latest/_sources/OUTPUT.rst.txt, 2026-10-22). Wazuh has a default JSON decoder that turns each field of a JSON log into a dynamic field that rules can reference (https://documentation.wazuh.com/current/user-manual/ruleset/decoders/json-decoder.html, read 2026-10-22). So the missing work is **rules**, not a decoder: Wazuh rules matching Cowrie's `eventid` values and counting by source. Cowrie's own documentation lists guides for Splunk, Azure Sentinel and Graylog; it lists none for Wazuh, so there is no vendor recipe to cite. Same principle as the mini SOC page: write rules from captured lines.

### 3.4 Legal and safety minimums for a learner at home

Not legal advice. I read no statute or ISP contract. What I did read: the cloud providers' policies (summarised in the design, section 7.4), and the T-Pot README's disclaimer. The ISP terms point is **est.**: residential ISP terms vary and many restrict running servers or inbound services; the learner must read their own contract.

The minimums, which every hands-on path repeats:

1. **Never on the main LAN.** A honeypot is a machine designed to be broken into. It lives in a separate segment with no route to anything the learner cares about. On a flat home network, do the theory path only.
2. **Read the ISP terms first** before any inbound exposure (port forwards, a public address). A first run needs no exposure (Track 3 internal-only).
3. **Provider consent in writing** for a cloud sensor, as the design requires (section 7.4); a learner's own account is their own responsibility under the same provider policy.
4. **Closed or allow-listed egress.** The honeypot must not be able to attack others.
5. **No counter-hacking.** No scanning back, no exploiting an attacker's host, no reporting by script. Passive only.
6. **No real data on it**, no reused passwords, no real keys.
7. **Raw logs stay private**; aggregates only (design section 7.3).
8. **A named stop**: an end date and a kill switch (design section 10).

## 4. Lesson set

Each track has a THEORY path (free) and a HANDS-ON path (paid for by the learner). Times are estimates for a learner, "est." throughout. A lesson says whether it needs hardware or cost. All sample data in lessons is synthetic and built at run time; nothing is copied from a real attacker.

### Track 1: concepts and honeytokens (no honeypot at all)

Everything in Track 1 is free and safe. Theory path = Lessons 1, 2, 6. Hands-on path = Lessons 3, 4, 5, on the learner's own machine with their own free accounts; their cost is $0 (est.; the hosted token service is described as free, terms unread).

| # | Title | Learning goals | Prerequisites | Hands-on exercise | Time (est.) | Cost / hardware |
|---|---|---|---|---|---|---|
| 1 | What deception is | Name and tell apart decoy, lure, breadcrumb, honeytoken, honeypot, honeynet; low, medium, high interaction; place each on the attacker's path | [Detection and monitoring](../../wiki/Detection-and-Monitoring-Wazuh-and-the-Landscape.md) | Paper exercise: given a small network diagram, mark where a decoy, a lure and a breadcrumb would go and what each should alert on | 1 to 1.5 h | None |
| 2 | Why a decoy alert is different | The zero-activity baseline; why deception alerts are high-signal inside a network and noisy on the open internet; what a vendor claim ("near-zero false positives") needs to be true; how to read vendor deception material critically | Lesson 1 | Sort 20 synthetic event descriptions into "decoy touched" versus "ordinary noise"; for each, say which alert type would fire and whether a person must look | 1 h | None |
| 3 | Plant a canarytoken | A token is a tripwire you place and watch; what a trip reveals and what it cannot (a source address, a time, not the person); that the hosted service sees your email and memo | Lesson 1; a mailbox you do not mind using | Create one token of your choice, place it in a folder you own, trip it yourself, read the alert, and note the fields. Then read the service's terms and say what you gave it | 1 h | Free service (terms unread); no hardware |
| 4 | Honeyfiles on a host you own | A decoy file plus a watch rule; the difference between "someone read it" and "someone copied it"; why names matter | Lesson 3; a Linux machine you own | Create a decoy file in a test directory and an audit watch on it; open it; find the audit record. Optional: have the Wazuh agent from the mini SOC report it | 2 h | None beyond a Linux box; optional uses the mini SOC (cost per [Build your own mini SOC](../../wiki/Build-Your-Own-Mini-SOC.md)) |
| 5 | Deception in the SIEM: write the rule | Turn a structured honeypot event into an alert; count by source; map to ATT&CK T1110 (brute force) and T1078 (valid accounts); keep hostile strings inert | Lessons 1 and 4; the Wazuh basics page | Using **synthetic** JSON lines in Cowrie's documented shape (`eventid`, `session`, `src_ip`, `timestamp`, built by the lesson's own script at run time, labelled synthetic), write a rule for repeated failures from one source and one for a success after failures. Feed it a hostile-looking line and show it stays data. Re-do with real lines if the learner runs Track 2 or 3 | 2 to 3 h | None; runs on a laptop with a Wazuh test install |
| 6 | Should you run one? Safety and law minimums | The eight minimums in section 3.4; provider policy basics; the ethics of recording people who did not agree; a decision tree from "I'm curious" to "I run a sensor" | Lesson 1 | Write your own one-page plan: where, whose account or hardware, which network, which end date, who reads the abuse inbox. A reviewer (the maintainer or a peer) answers "would you run this?" | 1 h | None |

Lesson 5 depends on what real Cowrie lines look like; with synthetic lines it teaches the shape and states that real rules are written from captured lines (design section 9.3). Flag: rule file format and Wazuh syntax are not verified in this plan; the lesson author reads the Wazuh rules documentation and runs the rule in a test manager.

### Track 2: cloud Cowrie, riding the #120 design

Theory path (free): Lesson 7 only, a read-through of the merged design, so the learner knows what a cloud sensor is, what it costs and why it is built the way it is. Hands-on path: Lessons 8 and 9, run in the **learner's own cloud account at their own cost**. Gating, stated plainly: the project's reference environment builds nothing for this until the maintainer approves #120; a learner running it in their own account needs no project approval and takes all the provider and safety obligations (design sections 3 and 7.4, plus the section 3.4 minimums above).

| # | Title | Learning goals | Prerequisites | Hands-on exercise | Time (est.) | Cost / hardware |
|---|---|---|---|---|---|---|
| 7 | Anatomy of a cloud honeypot (theory) | Why a separate account, closed egress, a write-only log key and a kill switch; the cost arithmetic; what "medium interaction" means | Lessons 1, 2, 6; [Edge and DMZ](../../wiki/Roadmap.md) context | Review exercise: take the design's risk table and for each risk write the check you would run before turning it on | 1.5 h | None |
| 8 | Stand up a sensor for a weekend | Run Cowrie for a bounded window; read raw logs; measure time to first attempt | Lesson 7; written provider consent (design section 7.4); a funded account of your own | Follow the design's option E (logs read on the host, then delete) for a stated window; count attempts and top usernames by hand; write down the end date first and tear down on it | 3 to 4 h plus the window | Option E in the design: $6 a month figure for the droplet (design 8.1; a weekend is a fraction of it, est.). Provider account and payment method required |
| 9 | Send the sensor's logs to your SIEM | The pull-only log path; why no Wazuh agent on the sensor; rules from captured lines | Lessons 5 and 8; a log store and key as designed (design 9) | Pull the objects, write them to a file a Wazuh agent reads, rerun Lesson 5's rules on real lines and fix them. Feed the hostile lines from design 4.5 risk 5 | 4 to 6 h | Option A in the design: $11 a month ($6 droplet plus $5 bucket) while it runs; prices per the design's table, DigitalOcean prices retrieved 2026-10-10 |

Decoder and rule work needed for Lesson 9, all UNVERIFIED until real lines are captured: Wazuh's default JSON decoder already extracts the fields; the work is local rules keyed on Cowrie `eventid` values (login failure, login success, command input, file download) with frequency and same-source conditions, a rule group for the honeypot source, and a mapping to ATT&CK ids. No custom decoder is expected, but whether the pulled lines need a wrapper or a location label for the agent's collector to treat them as JSON is not verified.

### Track 3: on-prem T-Pot CE in the homelab

Theory path (free): Lesson 10, a paper design of the honeynet and a read of the README. Hands-on path: Lessons 11 and 12, on the learner's own hardware. For the maintainer's homelab this is **gated on the malware net being done** (section 5 lists the prerequisites). A learner without such a network does the theory path, or a VM on a host with its own isolated virtual network.

| # | Title | Learning goals | Prerequisites | Hands-on exercise | Time (est.) | Cost / hardware |
|---|---|---|---|---|---|---|
| 10 | Design a honeynet on paper (theory) | What a honeynet is; segments, default-deny, one-way management, where logs leave; read T-Pot's README and name each placement warning | Lessons 1, 2, 6 | Draw your segment: what may reach the honeynet, what it may reach (nothing, plus an allow-list), how you manage it, where logs go. Mark the T-Pot README warnings on the drawing | 2 h | None |
| 11 | T-Pot CE on an isolated segment, internal only | Install, tour the honeypots and Kibana; generate traffic from your own lab machine inside the segment and watch each honeypot react; opt out of default data sharing | Lesson 10; the isolated network; a pinned T-Pot release and its README | Install the Standard / Hive type from the pinned tag in a VM or on a spare machine; remove the community-submission section; from a second lab VM in the same segment run a scan against it and a few login attempts; find the events in Kibana. Nothing is exposed to the internet | 6 to 8 h | Hive: 16 GB RAM, 256 GB SSD per README (a VM or a spare machine). Sensor: 8 GB, 128 GB. New hardware cost $0 if the learner has a machine (est.); otherwise unpriced, I did not read prices. Electricity est., unmeasured |
| 12 | T-Pot to the SIEM | Ship a honeynet's events to Wazuh; compare mechanisms; ask what the pipeline costs in bytes and risk | Lessons 5 and 11 | Prove one of the four ways in section 3.2 (agent on the host is the suggested first, because the segment is isolated), write rules for two T-Pot honeypots (for example Cowrie and Dionaea) from captured lines, and record which way failed and why. If T-Pot updates are applied, check the shipping still works | 6 to 10 h | None beyond Lesson 11; uses the existing SIEM |

Optional later lesson (not scheduled, named for completeness): "Expose it on purpose", with ISP terms, a port-forward plan and the README's port advice. It is **not recommended as a project lesson**; a learner who does it takes the risk and the section 3.4 minimums apply with extra force. It needs its own decision (section 8).

## 5. Track 3 hard prerequisites and network isolation

Hard prerequisites before any hands-on T-Pot lesson in the maintainer's homelab. The malware network itself is the maintainer's project and is not described in this repository; the list says what it must provide, not how it is built.

1. **The malware network exists and is verified isolated.** A segment on its own VLAN or physical port with a default-deny firewall in both directions. Verification is a test (from inside the segment nothing reaches other networks; from other networks nothing reaches in), not a belief.
2. **No route to the main LAN or to management networks**, including the SIEM and the logging network, except the single allowed log path (item 6).
3. **Egress is an allow-list, not open.** T-Pot needs outbound 80 and 443 to install and update, and says it needs a working internet connection. Resolve that with a time-boxed allow-list during install and update windows (package and container registries), then closed. The README's note that it needs an unfiltered connection is a conflict to be handled deliberately; the lesson records what broke when egress was closed.
4. **Management access** (T-Pot SSH on 64295 and the web UI on 64297 per the README) reachable only from one admin host or jump path, never from the segment's own clients.
5. **No internet exposure for the first run.** No port forward, no public address, until the maintainer decides separately (section 8, decision 6).
6. **One log path out**, initiated in a direction the segment's rules allow, to a collector that treats the data as untrusted (design 4.5 risk 5). The collector end is the SIEM's logging network; opening any hole to it is a firewall change the maintainer approves.
7. **Community data submission removed** before first start (README documents removing the `ewsposter` section).
8. **A pinned release and README** for the chosen tag (24.04.1 was the latest tag when read; the default branch is ahead).
9. **A rebuild path.** Stop-and-reimage is the recovery; nothing on the host is irreplaceable. A named end date or review date.
10. **Hardware sized to the README** (Hive 16 GB and 256 GB SSD, Sensor 8 GB and 128 GB), not to the cloud droplet sizes in the cloud design.

## 6. How the lessons feed Wazuh and the SIEM

Reuse the merged path ([design section 9](2026-10-21-honeypot-design.md)): the sensor produces structured JSON; a collector on the learner's side lands it as a file; a Wazuh agent or manager reads it; rules produce alerts and counts; Grafana shows aggregates. No agent on an internet-facing sensor.

Per track:

| Track | Source | Path | New work needed |
|---|---|---|---|
| 1 | Synthetic JSON lines; audit records from a honeyfile; token alerts (email) | A file the learner's Wazuh test install reads; for tokens, the email is the alert | Lesson 5 rule files and the generator script for synthetic lines |
| 2 | Cowrie JSON from the cloud sensor | Design 9.1: pull from the store, write a file, agent reads | Local rules keyed on `eventid`; ATT&CK mapping; the hostile-line test |
| 3 | T-Pot honeypot JSON logs on an isolated host | One of the four mechanisms in 3.2 (UNVERIFIED), agent-on-host suggested first | Prove the mechanism; rules per honeypot type; decide whether T-Pot's own Elasticsearch is a second store or ignored |

Decoder work: none expected, because Wazuh ships a JSON decoder (read 2026-10-22). Rule work: a rule group for honeypot sources, rules for repeated failure from one source, success after failure, command execution, file-download attempt, and a decoy-touched rule for Track 1 honeyfiles. Each rule is written from captured lines. Wazuh rule syntax and whether Cowrie's nested fields decode as expected: UNVERIFIED, to be proven in a test manager before a lesson ships.

A teaching point to keep honest: deception alerts are strongest when the decoy is inside the network (zero baseline). Internet sensors feed *threat-intelligence* style data (what is out there), not *detection* of the learner's own compromise. The SIEM lessons label which is which.

## 7. Cost

No spend is approved by this plan. Learners pay for hands-on; the reference environment pays for nothing until #120 is approved. Figures come from the design's tables (DigitalOcean prices retrieved 2026-10-10, AWS 2026-10-16, Spaces 2026-10-11) or are marked est.

| Path | What it costs | Source / state |
|---|---|---|
| Track 1 theory and hands-on | $0 | Hosted canarytoken service described as free; terms unread |
| Track 2 theory | $0 | |
| Track 2 hands-on, option E (look once, delete) | $6 a month figure for the droplet; a weekend is a fraction of that (est.) | Design 8.1 |
| Track 2 hands-on, option A (with log store) | $11 a month while it runs ($6 + $5) | Design 8.1; the $5 bucket is charged for the month |
| Track 2 on AWS (option C) | $10.42 a month plus S3, unpriced | Design 8.1 |
| Track 3 theory | $0 | |
| Track 3 hands-on | $0 in new hardware if the learner has a machine meeting the README (est.); otherwise unpriced (no prices read); electricity unmeasured | README sizes |
| Cloud T-Pot | Not offered. The design prices the T-Pot-sized droplet at $48 a month (`s-4vcpu-8gb`, design 8.2); a learner may do it, the project does not teach it | Design 8.2 |
| Wiki and agent time | Agent hours in section 9, no cash | |

No line goes in `docs/cost.md`, `docs/stages/approved.json` or the cost gate. The honeypot figures stay outside the ceiling as the design requires (its section 8.3).

## 8. Risks

| Risk | Mitigation |
|---|---|
| A lesson teaches a learner to expose a vulnerable machine to the internet | Track 3 is internal-only first; exposure is a separate decision; the safety lesson (6) is a prerequisite of every hands-on lesson |
| Vendor claims are repeated as facts | Zscaler material is cited as one vendor's glossary article; product behaviour unread; Lesson 2 teaches the condition under which "near-zero false positives" holds |
| T-Pot data leaves by default | Lesson 11 removes community submission first |
| Dated or wrong instructions (T-Pot tag versus default branch differ) | Pin a release; re-read that tag's README at write time; unverified-draft banner until run |
| Hostile strings in logs reach the SIEM | Hostile-line test in Lessons 5 and 9 (design 4.5 risk 5) |
| The malware net is not built when scheduled | Track 3 is gated; theory path and Track 1 do not depend on it |
| Cloud provider acts on a learner's account | Written consent step in Lesson 8; separate account; kill switch (design 4.5 risk 2) |
| Privacy of third parties in captured data | Aggregates only; no raw publication; legal question left to the learner (design 7) |
| Canarytoken hosted service stores learner data | Lesson 3 includes reading its terms; self-hosting named as an alternative, unread |
| Stage 2 not applied, so "feed the SIEM" lessons cannot be verified | Lessons carry the unverified-draft banner as the mini SOC page does |

## 9. Triage

Sizes use the project's convention: S about 2 h, M about 5, L about 12, XL about 30. Agent owner for lesson writing is a Sonnet agent; anything that applies, spends or touches a live account is the maintainer. Schedule context from the Roadmap: S2 (2026-11-03 to 11-16) is when the honeypot, edge and PeerTube **designs** are approved or sent back; S3 (2026-11-17 to 11-30) is stage 3 start; S6 (2026-12-29 to 2027-01-11) is the DMZ stack (flag off) and cloud reviewer recruiting; S7 (2027-01-12 to 01-25) is "the cloud lessons" among other items.

| Track | Size (sum of lessons, est.) | Agent owner | Epic / area | Dependencies | Recommended sprint and reasons |
|---|---|---|---|---|---|
| Track 1: Lessons 1 to 6 (about 8 to 10 h of learner time; writing effort as lessons: 1, 2 and 6 are S each, 3 is S, 4 is M, 5 is M plus a small generator script) | L overall (about 12 h agent time) | Sonnet agent writes; the maintainer reviews and merges | Learning and wiki (epic #74); area default "Learning and wiki" | Needs nothing built. Lesson 5 best after the Wazuh basics page; Lesson 4 optionally links stage 2's auditd work | **S3.** Free and safe, so it can ship before any approval. S1 and S2 are the maintainer's busiest hours; agent work does not use them, but S2's plan already includes the design reviews. S3 has stage 3 work for the maintainer, not for a docs agent. Split into two issues (Lessons 1, 2, 6 theory; then 3, 4, 5) and land the theory first. Not S1: only three agent items may be in flight and S1 is the unlocking sprint |
| Track 2: Lesson 7 (theory) | S | Sonnet agent | Learning and wiki (links to Edge and DMZ #72) | The merged design only | **S3 with Track 1 theory** (no gate, a read-through of an already merged document). It carries the "not built" banner |
| Track 2: Lessons 8 and 9 (hands-on) | M to L (about 5 to 12 h agent time; real runs by the maintainer or a learner) | Sonnet agent drafts; the maintainer performs any apply in an account he approves | Edge and DMZ epic #72 for the build; Learning and wiki #74 for the pages | Hard gates: the maintainer approves #120 (decisions 1 to 3, 7 and 13 of the design), provider consent, a real capture to write rules from | **After S8**, as the default. Reasons: the cloud design is itself only scheduled for approval in S2; its build is not in any sprint; S6 is the DMZ stack and cloud reviewers, and the maintainer's S6 hours are full; S7's "cloud lessons" are the Azure/AWS/GCP provider lessons. A learner may run it earlier on their own account with only a draft lesson. If the maintainer approves #120 in S2, the earliest honest slot is S7 for a draft page flagged unverified |
| Track 3: Lesson 10 (theory) | S | Sonnet agent | Learning and wiki | Nothing built | **S4 or S5**, after Track 1, as filler once the stage 3 work is moving. Free, no gate |
| Track 3: Lessons 11 and 12 (hands-on) | L (writing 12 h) plus about 10 to 18 h of maintainer lab time (est.) | Sonnet agent drafts; the maintainer runs it on his network | Learning and wiki (#74); the malware net sits outside this repo | **Hard gate:** the malware net done and verified isolated (section 5), plus a decision to spend maintainer lab hours. T-Pot prerequisites are time, not money | **After S8.** The malware net has no date in the Roadmap and his hours are capped at about 10 to 12 per sprint. Nothing in S1 to S8 frees a block of lab time. Revisit at the S8 retro, or earlier if he finishes the net |
| Wazuh rule work for Tracks 2 and 3 | M | Sonnet agent drafts; verified by a real capture | Stage 2 telemetry (#70) | A manager that has seen real Cowrie or T-Pot lines; stage 2 applied | After the first real capture exists; no sprint before that |

## 10. Decisions owed by the maintainer

1. Whether this plan is accepted as the education roadmap for #178, and whether Track 1 may be written as wiki lessons now (answering design decision 14 in the affirmative for Track 1 and Track 2 theory).
2. The principle in section 1, confirmed as the project's rule, and whether the reference environment should ever fund a hands-on path (default: no).
3. Whether Track 1 Lesson 3 may recommend the hosted canarytoken service (free, terms to be read) or should teach self-hosting.
4. Track 2: whether the design (#120) is approved for the reference environment, and, if not, whether Lessons 8 and 9 still ship as learner-pays drafts.
5. Track 3: the date or condition for the malware net being done; who runs the lab hours.
6. Whether a lesson on internet exposure of T-Pot is ever written (default: no, internal-only).
7. The T-Pot lesson's source of truth: pin tag 24.04.1 or wait for a newer tagged release.
8. Whether T-Pot community data sharing may ever be recommended on (default: off in lessons).
9. Sprint placement in section 9 (Track 1 and Track 2 theory in S3; the rest after S8).
10. Where lesson pages live (the Learning and wiki area; ordering on the Reading order page).

## 11. Changes this plan makes

This file only. No lesson pages, no code, no `docs/stages/approved.json`, `docs/cost.md` or cost-gate change.

## 12. What this plan does not claim

- That any lesson works. Nothing was installed, run, placed or scanned.
- Anything about Zscaler's actual product, price or configuration. The only Zscaler source read is a glossary article; the product and help pages were not readable.
- That T-Pot exports to Wazuh in any of the four ways listed. The README documents none of them.
- The terms of the hosted canarytoken service, the terms of any ISP, or any law.
- That Cowrie's fields suit Wazuh rules as described beyond what the two documentation pages say; rule syntax is unverified.
- Any hardware price. None was read.
