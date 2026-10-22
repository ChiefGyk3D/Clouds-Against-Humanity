# IDS and IPS: Snort and Suricata

Second of four lessons in the network and host defense track. Read it after [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) (what a firewall rule is) and [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) (what a log line, a rule and a false positive are), and alongside [Threats in plain words](Threats-in-Plain-Words.md) and [Security tools basics](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md), the page about the tools that make the traffic this page watches for.

The other three lessons in the track are written at the same time as this one: [Packet filters compared: iptables, nftables, UFW and pf](Packet-Filters-Compared-iptables-nftables-ufw-pf.md), [File integrity and alerting: Tripwire, AIDE and Wazuh](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) and [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md). Those three links may not resolve until the pages merge. Nothing on this page depends on them.

Next: [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the Suricata exercises were run once on Linux, offline, in a container; everything else was not.** On **2026-10-22** the author ran every Bash command and Python script in Exercises 1 to 8 below on a Debian-based Linux machine as an ordinary user, with no `sudo`, using Suricata **8.0.7** from a container image under rootless Podman (the container had no network), Python 3, `tcpdump` and `tshark`. The output pasted below is trimmed from those runs. **Not run:** every PowerShell command (written from the Podman and PowerShell documentation, marked **est.**), anything on Windows or macOS, Docker (the commands are the same shape, but I did not run them), **Snort** in any version (the Snort rule shown is **est.**), a live capture on a network interface, an in-line (IPS) setup on any machine, the Emerging Threats Open ruleset (I read its pages and license; I did not download the rules), Wazuh, pfSense, OPNsense, any cloud traffic mirror, and TLS inspection. Those parts are written from each project's own pages, listed in the [claims register](#claims-register), and say so where it matters. Versions change; trust your terminal over this page.

> **Prerequisites.** You can open a terminal and run a command ([The terminal and your first script](Terminal-and-Your-First-Script.md)), you know what a port, TCP and a firewall rule are ([Networking basics](Networking-Basics-for-This-Project.md)), and you have read what a log, a rule and a false positive are ([Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md#rules-baselines-and-the-two-ways-to-be-wrong)). For the hands-on part: Python 3, `tcpdump` or `tshark` (to look at the capture), and Podman or rootless Docker (to run Suricata without installing it). About four hours for the reading and the free exercises (est.).

## What you will be able to do

- Say what an IDS and an IPS are, how they differ from a firewall, and why an IPS is the riskier of the two to run.
- Say where a sensor can watch traffic (in line, on a tap, on a SPAN port, on a cloud mirror), and what each choice costs you.
- Say what a network sensor and a host sensor each see, and what encrypted traffic hides from the first.
- Tell a signature from an anomaly rule, and say what each is good and bad at.
- Place a sensor on a small network diagram (edge, DMZ, east-west, cloud mirror) and defend the choice.
- Say how Snort 2, Snort 3 and Suricata relate: who makes each, what state each is in, and where their rules do and do not carry over.
- Read a rule field by field: action, protocol, addresses, ports, direction and the options `msg`, `flow`, `content`, `classtype`, `sid`, `rev`, `metadata`.
- Say where rules come from, who owns them and what their licenses allow, and why a rule feed is a supply chain.
- Run Suricata offline on a capture you build yourself, write a rule from the local `sid` range, see its alert in `eve.json`, break the rule, and notice when a broken rule says nothing.
- Tune a noisy rule with a `suppress` entry and a `threshold` entry, and read the counters that show what the tuning did.
- Describe, at concept level, how an attacker evades an IDS (fragmentation, encryption, patience, rule-matching gaps) and what a defender does about each.
- Threat-model the IDS itself: sensor compromise, rule poisoning, resource exhaustion and log tampering.

## The words, in plain language

An **intrusion detection system (IDS)** watches traffic or activity and raises an alert when something matches what it was told to look for. It does not stop anything. An **intrusion prevention system (IPS)** does the same and then acts: it drops the packet or resets the connection. The Suricata project describes its engine as a "high performance Network IDS, IPS and Network Security Monitoring engine" ([What is Suricata](https://docs.suricata.io/en/suricata-8.0.7/what-is-suricata.html), read 2026-10-22). One program, three jobs; which job it does is a matter of how you connect it and what the rules say.

| Question | Firewall (packet filter) | IDS | IPS |
|---|---|---|---|
| Decides on | Addresses, ports, protocol, connection state | The contents of the traffic too (the bytes, the protocol messages) | The same as an IDS |
| Default | Often deny ([default deny](Subnets-NAT-and-Firewalls-By-Hand.md#firewalls)) | Allows everything; it only watches | Suricata's docs say IPS mode "will allow all traffic, and will use drop or reject rules to block unwanted traffic" |
| Where it sits | In the path | Beside the path (a copy of the traffic) or in the path, set to alert only | In the path |
| If it is wrong | A wrong rule blocks or admits | A wrong rule is a wrong alert or a missed one | A wrong rule **breaks something real**, or lets it through |
| If it fails | Depends on the design | You lose visibility | You lose the link, or you lose the protection, depending on how you set the failure behavior |

Two lines to keep. A firewall answers "may these two machines talk on this port?". An IDS answers "is what they are saying on that port what we expect?". And an IPS is an IDS with a hand on the plug, which is why many teams run the same rules in alert-only mode first and promote only the rules they trust ([Logs, SIEM and detection basics: the family of tools](Logs-SIEM-and-Detection-Basics.md#the-family-of-tools-in-one-table)).

### Passive and in line

A **passive** sensor receives a copy of the traffic and normally does not change it. An **in-line** sensor sits in the path: every packet goes through it, so it can drop packets, and it can also be the reason the network stops. Suricata's documentation puts it this way: IPS mode "is generally used inline", either at layer 2 (a bridge, "for example using AF_PACKET or DPDK") or at layer 3 ("routing, for example in NFQueue or IPFW") ([IPS Concept](https://docs.suricata.io/en/suricata-8.0.7/ips/ips-concept.html), read 2026-10-22).

How a passive sensor gets its copy:

- **A network tap**: a small device spliced into a cable that copies each direction of the traffic to a monitoring port. A breakout tap, for example, has two connectors for the existing line and two outputs, one per direction ([Wireshark: Ethernet capture setup](https://wiki.wireshark.org/CaptureSetup/Ethernet), read 2026-10-22). It sees everything on that link and can be tested and trusted; it costs a device per link.
- **A SPAN port** (also called port mirroring or port monitoring): a feature of a managed switch that copies the traffic of chosen ports to another port. "SPAN" is Cisco's name; the same page lists others ("Roving Analysis" from 3Com among them). It warns that the monitoring port must be at least as fast as the monitored one "or you will certainly lose packets", and that some switches cannot mirror everything. A SPAN port is cheap and easy and can silently drop packets under load.
- **A cloud mirror**: a cloud provider feature that copies a network interface's traffic to a collector. Amazon describes Traffic Mirroring as a feature "that you can use to copy network traffic from an elastic network interface" to "out-of-band security and monitoring appliances", with a source, a filter, a target and a session as its parts ([What is Traffic Mirroring](https://docs.aws.amazon.com/vpc/latest/mirroring/what-is-traffic-mirroring.html), read 2026-10-22). Other clouds have their own versions; read your provider's page and price list before you count on one. This page gives no price because I did not read one.
- **The sensor is the router or the host**: the engine runs on the machine that forwards or receives the traffic. That is how the pfSense and OPNsense packages work (below).

### Network-based and host-based

A **network IDS (NIDS)** watches traffic on the wire: Suricata and Snort are the examples on this page. It sees the traffic of every machine whose packets reach it, with no agent to install, but only what crosses that wire, and not what is encrypted. A **host IDS (HIDS)** runs on the machine and watches its files, processes, logins and logs: Wazuh is the example in this project ([Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md)). It sees what happened inside the machine after decryption, but only on machines that run the agent, and an attacker who takes over the machine can try to blind or rewrite it. You want both; each covers the other's blind spot. File-integrity checking, a HIDS technique, is the next lesson in this track ([File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md)).

### Signature and anomaly

A **signature** (also "rule") describes one known-bad thing: "a request whose path starts with `/cah-lab/probe`", "a TLS handshake naming this domain". It is precise and explainable (you can read why it fired), and it only finds what someone wrote it for. An **anomaly** detector learns or is told what normal looks like and flags the difference: "this host never talks to port 445, and now it does". It can find what nobody wrote a rule for, and it is noisy, because normal changes and unusual is not the same as hostile. Most production setups are mostly signatures with some anomaly flavor. Snort 3's page lists a machine-learning component, SnortML, and Suricata has its own anomaly and protocol-violation events; I did not read enough about either to say how well they work, so this page teaches signatures and counting rules, which you can build and check yourself.

### Where to put a sensor

A sensor is only as good as what it can see. Draw the network first, then ask of each candidate spot: what traffic crosses here, in which form (before or after NAT, encrypted or not), and what do I lose if the sensor fails?

| Spot | What it sees | Good for | Limits |
|---|---|---|---|
| **Edge** (just inside the internet link) | All traffic in and out of the site | Known-bad destinations, scans and exploit attempts from outside, command-and-control calls from inside | Behind NAT you see translated addresses: OPNsense's documentation warns that on a WAN interface "all the traffic is originating from your firewall and not from the actual machine behind it that is likely triggering the alert" ([OPNsense IDS and IPS](https://docs.opnsense.org/manual/ips.html), read 2026-10-22). A large share of the traffic is TLS (est.). |
| **DMZ** (the zone with the public servers) | Traffic to and from the exposed servers, after the edge filter | Attacks on your public services, a compromised server calling out | If TLS ends on the load balancer, you see plaintext only after that point. |
| **East-west** (between internal segments) | Machine-to-machine traffic that never reaches the edge | Lateral movement ([Threats in plain words](Threats-in-Plain-Words.md#lateral-movement)), a compromised host probing its neighbors | Needs a tap or mirror per segment, and a lot of internal traffic is noisy and encrypted. This is the placement most small sites skip. |
| **Cloud mirror** | A copy of chosen interfaces' traffic, delivered to a collector | Sites with no switch to mirror | Provider limits, cost, and the collector is one more machine to protect. |
| **On the host** | Traffic to and from that one machine, decrypted at the application if you use a host agent | The one machine you care most about | Per-machine work. |

The question "edge or inside?" has a common answer: both, with different jobs. The edge sensor tells you what is being thrown at you; the internal sensor tells you what got in. If you can only afford one, put it where you can both see the real addresses and be sure the feed is complete.

### What encryption hides

Most web traffic is **TLS**. A network sensor on a TLS flow can read the addresses, ports, sizes, timing, and some of the handshake, and not the request inside. How much of the handshake depends on the version: TLS 1.3 says "All handshake messages after the ServerHello are now encrypted" ([RFC 8446, section 1.2](https://www.rfc-editor.org/rfc/rfc8446.txt), read 2026-10-22), so the server certificate that a TLS 1.2 sensor could read is hidden in 1.3. The client's first message still names the site it wants (the **SNI**, server name indication) unless the client uses **Encrypted Client Hello**, which hides that message as well and is specified in [RFC 9849](https://www.rfc-editor.org/rfc/rfc9849.txt) (March 2026, read 2026-10-22). Suricata can log TLS fields including `sni`, `ja3` and `ja4` fingerprints (a hash of how a client builds its handshake) when they are visible ([EVE JSON output](https://docs.suricata.io/en/suricata-8.0.7/output/eve/eve-json-output.html), read 2026-10-22).

So with TLS in the way a network sensor can still do three useful things: match on the visible metadata (destination, SNI while it is visible, fingerprints), notice patterns in size and timing, and tell you a flow exists. Without the keys, it cannot read an attack inside the encrypted request. Your choices are to end TLS somewhere you control and inspect after that (a reverse proxy, a load balancer, a WAF; this puts a key and a copy of all your plaintext in one more place, so it is a design decision with its own threat model), or to detect on the host, where the traffic has been decrypted anyway. This is the main reason a modern setup is network sensor plus host agent plus logs, not any one of them.

## Snort 2, Snort 3 and Suricata

Two engines and three generations come up in every conversation about this. Facts below are from each project's own pages, read 2026-10-22; the first four are the ones people get wrong.

| Property | Snort 2 | Snort 3 | Suricata |
|---|---|---|---|
| Who makes it | Cisco (snort.org shows "© Cisco"; its license page says "Cisco uses a dual license strategy") | Cisco, developed "in close collaboration with the Snort community" | The Open Information Security Foundation (OISF), "a community-run non-profit foundation" |
| State today | **End of life.** Cisco Talos's blog post of **2026-10-21** says all open-source Snort2 versions "have now formally reached its end-of-life (EOL) and end-of-support (EOS)" and that Talos "will no longer provide rule support" for any of them | Current release on the downloads page: **3.12.4.0** | Stable **8.0.7**, released September 15, 2026; **7.0.17** is listed as End-of-Life |
| Engine license | GPL version 2 | GPL version 2 | GPL version 2 |
| Threads | "One per process" packet thread | "Any number per process", shared configuration | Multi-threaded: "multiple threads are active at once" |
| Configuration | `snort.conf` | Lua (`snort.lua`); "backwards compatibility with Snort 2 was sacrificed" | One YAML file (`suricata.yaml`) |
| Rule syntax | The original | Text rules "with syntax tweaks, so your 2.X rules must be fixed up"; `snort2lua` converts them | Similar header and options with documented differences from Snort 2.9 |
| Alert output | Not read | Loggers include `alert_fast`, `alert_csv` and `alert_json` | **EVE JSON** (`eve.json`), one JSON object per line |
| Inline capture | Through its DAQ library (version 2.x) | DAQ modules including AFPacket, NFQ, Divert and Netmap | AF_PACKET (layer 2), NFQUEUE (layer 3), also DPDK and netmap |
| Lua | Not used (`snort.conf`) | Configuration and "LuaJIT scriptable rule options and loggers" | Lua scripting in rules (the `lua` keyword); since Suricata 8.0 "Lua rules are enabled by default and run in a sandboxed environment" |

Sources: [Snort blog, 2026-10-21](https://blog.snort.org/), [Snort 3 page](https://www.snort.org/snort3), [Snort license](https://www.snort.org/license), [Snort downloads](https://www.snort.org/downloads), [Snort 3 user manual](https://www.snort.org/downloads/snortplus/snort_user.html), [Snort 3 reference manual](https://www.snort.org/downloads/snortplus/snort_reference.html), [Suricata download page](https://suricata.io/download/), [Suricata runmodes](https://docs.suricata.io/en/suricata-8.0.7/performance/runmodes.html), [Suricata Lua detection](https://docs.suricata.io/en/suricata-8.0.7/rules/lua-detection.html).

Some things this table does not say, on purpose. **Which is faster** depends on the rules, the traffic, the hardware and the tuning; I ran neither on a busy link and give no ranking. **Which has better rules** depends on which feed you license; see below. **Snort 3 is not Snort 2 with a new number**: its own manual calls it a redesign in which your old configuration "won't work as is". If you inherit a Snort 2 sensor, the vendor's lifecycle post above is your reason to plan a move; whether the move goes to Snort 3 or to Suricata is a question for your rules, your staff and your platform, not for this table.

### What about "compatible rules"?

The rule languages share a shape (an action, a header, and options in parentheses) and the rules in this lesson read like Snort rules to anyone who has seen one. They are not interchangeable files. Suricata's own page [Differences From Snort](https://docs.suricata.io/en/suricata-8.0.7/rules/differences-from-snort.html) lists behavior that differs even for a rule that parses in both: how `urilen` ranges are counted, what the `http_header` buffer contains, how protocol detection ignores ports. Snort 3 changed its syntax again. The Emerging Threats Open downloads are published per engine and version ("`suricata-$version`" and "`snort-$version`" in the download instructions), which is the project telling you they are different files. Treat a copied rule as untested until it has fired on a capture you control.

### Why this lesson uses Suricata

It runs offline in a container image with one command, reads a capture file, and writes JSON a script can count. That is a reason about a classroom, not a verdict: Snort 3 teaches the same ideas with a Lua configuration file and a `-r some.pcap` flag, and I did not run it.

## Reading a rule

The example rule below is the one in Suricata's documentation. Read it left to right.

```text
alert http $HOME_NET any -> $EXTERNAL_NET any (msg:"HTTP GET Request Containing Rule in URI"; flow:established,to_server; http.method; content:"GET"; http.uri; content:"rule"; fast_pattern; classtype:bad-unknown; sid:123; rev:1;)
```

| Part | In the example | What it does |
|---|---|---|
| **Action** | `alert` | What happens on a match. Suricata's list: `alert`, `pass` (stop inspecting this packet), `drop`, and the `reject` family (send a reset or an ICMP error). In IDS mode a `drop` rule only alerts (observed: the alert says `"action":"allowed"`); it takes IPS mode to drop. |
| **Protocol** | `http` | Limits the rule to that protocol. Suricata detects the application protocol itself, so `http` here means "this stream is HTTP", on any port. |
| **Source address and port** | `$HOME_NET any` | Where the traffic comes from. `$HOME_NET` is a variable you set in the YAML file to your own address ranges; `any` means every port. |
| **Direction** | `->` | From source to destination. `<>` means either way. |
| **Destination** | `$EXTERNAL_NET any` | Where it goes. `$EXTERNAL_NET` defaults to "not `$HOME_NET`". |
| **`msg`** | the quoted text | What a human reads in the alert. Make it say what was matched. |
| **`flow`** | `established,to_server` | Only on an established TCP connection, and only in the direction toward the server. This makes a rule faster and less noisy than one that looks at every packet. |
| **`http.method`, `content`, `http.uri`** | `content:"GET"` and so on | A **sticky buffer** names which part of the message the next `content` match looks in: first the method, then the URI. `content` is a literal byte pattern. |
| **`fast_pattern`** | | Tells the engine which `content` to use as the quick pre-filter. A performance hint. |
| **`classtype`** | `bad-unknown` | The rule's category, from the `classification.config` file. It sets the "Classification" and a default priority in the alert. |
| **`sid`** | `123` | The **signature ID**, a number that names the rule. |
| **`rev`** | `1` | The revision; bump it every time you change the rule. |
| **`metadata`** | (not in this example) | Free `key value` pairs for your tooling: who wrote it, when, which product it applies to. Emerging Threats rules carry `created_at`/`updated_at` fields here. |

The list of actions, protocols and the sentence about the `sid` come from [Rules Format](https://docs.suricata.io/en/suricata-8.0.7/rules/intro.html) and [Meta Keywords](https://docs.suricata.io/en/suricata-8.0.7/rules/meta.html), read 2026-10-22. The `metadata` keyword is "additional, non-functional, information" in the same Meta Keywords page; the ET `created_at` and `updated_at` fields are visible in the sample rule on the thresholding page.

**Which `sid`s are yours.** Suricata's page says "There are reserved ranges of sids" and points at [sidallocation.org](https://sidallocation.org/), which lists `1000000-1999999` as "Reserved for Local Use - Put your custom rules in this range to avoid conflicts" (read 2026-10-22). The same page lists `2000000` and up for Emerging Threats and other feeds. A sid is how a threshold, a suppression, a dashboard and an alert-handling runbook all find a rule, so two rules with one sid is a bug that shows up as the wrong rule being quieted. This lesson uses `1000001` and `1000002`.

The same rule in Snort 3's style, **est.** (written from its manual's `alert http ( ... http_uri:"attack"; ...)` example; I did not run Snort):

```text
alert http
(
    msg:"CAH LAB request for the probe path";
    flow:established, to_server;
    http_uri;
    content:"/cah-lab/probe";
    sid:1000001;
    rev:1;
)
```

## Where rules come from

Almost nobody writes a whole rule set. You subscribe to one, tune it, and add a few local rules for what only you know. The feeds differ in who writes them, what they cost, and what the license lets you do.

| Feed | Made by | License terms, as I read them | Notes |
|---|---|---|---|
| **Emerging Threats Open (ET Open)** | Proofpoint's Emerging Threats team | The `LICENSE` file in the download folder says rules with sids 2000000 to 2799999 are "covered under the BSD License"; some others are GPLv2; sids 2800000 to 2900000 are Emerging Threats Pro and covered by a separate license | Per-engine download URLs. The instructions suggest "once daily" updates on weekdays, a `version.txt` check, and MD5 files for validating downloads. Suricata's docs call it "free and a good reference that has a wide range of signature examples". |
| **Emerging Threats Pro** | The same team | A separate commercial license (not read) | The "Pro" in the sid ranges above. |
| **Snort Community rules** | Cisco Talos | GPLv2, per the Snort license page: "The source-code license governing your use of the Snort Engine and the Community Snort Rules is the GNU General Public License Version 2" | A smaller set, downloadable by anyone from snort.org. |
| **Snort Registered / Subscriber rules** (Talos) | Cisco Talos | "Proprietary Snort Rules": you "must enroll either as a registered user or as a subscriber", and the Non-Commercial Use License allows personal use only, not use "for commercial profit or gain" | Read the license page and the Talos pricing before using them in a business. I did not read the subscriber terms in full. |
| **Your own local rules** | You | Yours | Small, specific, and the only ones that know your environment. This lesson writes two. |
| **Other feeds** (OPNsense lists several, for example abuse.ch lists) | Various | Each its own | Read each license; "free to download" does not mean "free to use in a product". |

Sources: [ET Open download folder and LICENSE](https://rules.emergingthreats.net/open/suricata-8.0.7/), [ET Open instructions](https://rules.emergingthreats.net/OPEN_download_instructions.html), [Snort license](https://www.snort.org/license), [Snort downloads](https://www.snort.org/downloads), [OPNsense IDS and IPS](https://docs.opnsense.org/manual/ips.html), read 2026-10-22.

**A rule feed is a supply chain.** You pull text from the internet on a schedule, and your sensor treats it as instructions. Suricata's security page names it: "supply chain attacks, particularly around rule distribution, could potentially target Suricata installations" ([Security Considerations](https://docs.suricata.io/en/suricata-8.0.7/security.html), read 2026-10-22). The ET instructions give MD5 hashes; a hash published at the same place as the file shows the download was not corrupted, and says little about whether the publisher was compromised. Practical habits: pull through one updater (the ET page calls Suricata-Update "the preferred method" for Suricata), keep the rule files in version control, read the diff before a big update goes live, and keep your local rules in a separate file so an update never overwrites them.

## Tuning

A new sensor with a full rule set is loud. Tuning is the work of making the alerts mean something: keeping what you can act on and quieting what you cannot. The tools, from narrowest to broadest:

- **Fix the rule or the variable.** Most noise comes from `$HOME_NET` being wrong (see the OPNsense NAT warning above) or a rule watching a port or service you do not run. This is the first thing to check and the cheapest fix.
- **Suppress.** Suricata's `threshold.config` file takes lines like `suppress gen_id 1, sig_id 2002087, track by_src, ip 203.0.113.67` (the documentation's example uses a different address), which makes sure that signature "will never match for src host" that address. The documentation notes that "Actions performed when a rule matches, such as setting a flowbit, are still performed". Use it for a known-good source: the monitoring system that checks `/healthcheck` every five seconds. The cost: an attacker on that address is also silent for that rule.
- **Threshold.** A `threshold` line, in the file or in the rule, limits how often a rule alerts: `type limit` allows at most `count` alerts per `seconds`; `type threshold` alerts only after `count` matches; `type both` combines them; `backoff` alerts at growing intervals. Use it for a rule that is right about each event and wrong to tell you about all of them. The cost: you see fewer events, so a count is a count of alerts, not of events.
- **Disable the rule.** Suricata-Update, the rule updater, reads a `disable.conf` file for rules to turn off ([Rule Management with Suricata-Update](https://docs.suricata.io/en/suricata-8.0.7/rule-management/suricata-update.html)). Use it when a rule is wrong for your environment as a whole and no narrower fix helps. Write down why, because the next person will wonder.
- **Rate-filter and action change.** `rate_filter` can change a rule's action when it fires too often, for example from `alert` to `drop` for an address that trips a rule ten times in a minute. It is an IPS tool; test it as alert-only first.

Source: [Global thresholds](https://docs.suricata.io/en/suricata-8.0.7/configuration/global-thresholds.html) and [Thresholding Keywords](https://docs.suricata.io/en/suricata-8.0.7/rules/thresholding.html), read 2026-10-22. Exercise 5 runs a suppression and a threshold on the capture you build.

### False positives and false negatives

A **false positive** is an alert for something that is not a problem. A **false negative** is a problem with no alert. You will not drive both to zero; tuning trades one for the other, and the trade has a cost each way ([Logs, SIEM and detection basics: alert fatigue](Logs-SIEM-and-Detection-Basics.md#alert-fatigue)). Two things about an IDS make the trade harder than for a log rule.

First, a false negative is silent. A quiet sensor looks exactly like a healthy network. The only way to know a rule still works is to test it: replay a known capture that should alert, and check that it does, on a schedule and after every rule or version change. Exercise 4 shows two ways a rule can stop working with no alarm.

Second, an IPS turns a false positive into an outage. That is why the order of work is: run alert-only, read the alerts for a few weeks, tune, and only then promote rules to drop.

## Performance and sizing, at a concept level

I measured nothing here about throughput, and this page gives no numbers for it. What the documentation says about what matters:

- **Traffic volume and packet size.** The sensor has to keep up with every packet or it drops some, and a dropped packet is a blind spot. With AF_PACKET, Suricata's tuning page describes a per-thread ring buffer: "If any of the buffers gets filled (for example packet processing can not keep up) that will result in packet drop counters increasing in the stats logs."
- **Number of rules and what they inspect.** More rules and more application-layer buffers mean more work per packet. The `fast_pattern` hint, `flow` conditions and a good pattern-matching algorithm (`mpm-algo`; the tuning page says "On supported platforms, Hyperscan is the best option") reduce it.
- **Threads and memory.** Suricata runs "workers" threads that each carry the whole pipeline; Snort 3 shares configuration among packet threads so memory does not multiply per process. Memory caps (`memcap`) for flows, streams and reassembly decide what happens at overload.
- **In-line adds risk.** An in-line sensor that cannot keep up adds delay or drops traffic that nobody meant to drop. The IPS documentation notes that new data in IPS mode "is inspected immediately, together with previous data where possible", in a sliding window, so there "can be significant rescanning of data, which has a performance impact".
- **Sizing is an experiment.** Start from your link speed and your busiest hour, capture an hour of real (permitted) traffic, replay it through a test sensor with your rule set, and watch the drop counters and the CPU. Add headroom. Do not size from a vendor's number you did not reproduce.

Sources: [Tuning considerations](https://docs.suricata.io/en/suricata-8.0.7/performance/tuning-considerations.html), [Runmodes](https://docs.suricata.io/en/suricata-8.0.7/performance/runmodes.html), [IPS Concept](https://docs.suricata.io/en/suricata-8.0.7/ips/ips-concept.html), read 2026-10-22.

## IDS and IPS on a firewall appliance: pfSense and OPNsense

Many small sites meet an IDS first as a package on the firewall, not as a server in a rack. What I read:

- **pfSense**: Netgate's documentation says pfSense "can act in an Intrusion Detection System (IDS) / Intrusion Prevention System (IPS) role with add-on packages like Snort and Suricata", and that the two packages "share many design similarities" ([pfSense IDS / IPS](https://docs.netgate.com/pfsense/en/latest/packages/snort/index.html), page last updated June 30, 2022, read 2026-10-22). The [package list](https://docs.netgate.com/pfsense/en/latest/packages/list.html) describes Suricata as "A high performance network IDS/IPS and security monitoring engine by OISF". I did not read the package's own settings pages, so I say nothing here about its modes or defaults.
- **OPNsense**: The manual says its IPS "is based on Suricata and utilizes Netmap to enhance performance". Its settings page offers a packet-capture mode for IDS (alerts only), a Netmap mode for IPS (alerts and discards), and a Divert mode for IPS that works through firewall rules. It warns that with no rulesets downloaded "the system is active without any rules", that IPS mode wants hardware offloading features disabled, and that "it usually does not improve security to use the WAN interface when in IPS mode because it would drop the packet that would have also been dropped by the firewall". It can ship the EVE log to syslog ([OPNsense IDS and IPS](https://docs.opnsense.org/manual/ips.html), read 2026-10-22).

How this ties to the rest of the track: the appliance's packet filter is the firewall layer ([Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md); this link may not resolve until that page merges), and the IDS package is the content-inspection layer on the same box. They share a CPU, so a busy rule set competes with routing. They also share a failure domain: if the box is compromised, so are both.

## How alerts reach a SIEM

Suricata writes **EVE JSON**: "The EVE output facility outputs alerts, anomalies, metadata, file info and protocol specific records through JSON", normally into one file, `eve.json`, one JSON object per line ([EVE JSON Output](https://docs.suricata.io/en/suricata-8.0.7/output/eve/eve-json-output.html), read 2026-10-22). Each line has an `event_type` (`alert`, `http`, `flow`, `tls`, `dns`, `stats` and more), a timestamp, the addresses and ports, and a `flow_id` that ties events from one connection together. Exercise 3 shows one.

To get those lines to a SIEM ([Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md)), something has to read the file or receive the lines. Options the docs describe: the EVE file read by an agent, EVE sent to syslog, or sent to Redis. Wazuh's proof-of-concept guide for Suricata uses the first: the Wazuh agent on the Suricata machine gets a `localfile` block with `log_format` set to `json` and `location` set to `/var/log/suricata/eve.json`, after which "Wazuh automatically parses data from /var/log/suricata/eve.json and generates related alerts", findable by the `suricata` rule group ([Wazuh: Network IDS integration](https://documentation.wazuh.com/current/proof-of-concept-guide/integrate-network-ids-suricata.html), read 2026-10-22; I did not run it). That guide tested Suricata 6.0.8, so check the current EVE field names for your version.

Three decisions when you wire it:

- **Which event types to ship.** Alerts are small and precious. `flow`, `http` and `dns` records are large and useful for investigations. Ship alerts as a rule and the rest as storage and the SIEM's price allow.
- **Keep the sensor's clock right.** Alerts from a sensor with a wrong clock land in the wrong place in the timeline ([Logs lesson: time](Logs-SIEM-and-Detection-Basics.md#time-why-clocks-have-to-agree)).
- **Ship it off the box.** A sensor that has been taken over can rewrite its own file. The copy that already left is the one you can trust ([threat model below](#threat-model-of-the-ids-itself)).

Wazuh's own detection lives on the hosts; see [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) for how this project uses it, and [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) for another source of JSON events. T-Pot ships a Suricata engine as one of its network watchers ([T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md)).

## Free path: a sensor on your own computer, offline

Everything here runs on your computer, reads a capture file you build yourself, and sends nothing anywhere. It costs nothing but disk space and a few minutes of CPU. The reading above is the free path too; this part is the practice.

### Ground rules

1. **A capture file, not a wire.** Suricata reads `lab.pcap`, a file. It does not sniff your home or work network, and neither should you "to see what is there". Other people's traffic is theirs, and the packets you did not make may hold passwords. Two exercises use traffic on your own loopback interface (`127.0.0.1`), which never leaves your computer.
2. **The container has no network.** Every run uses `--network none`: the container gets a loopback interface and nothing else (Exercise 1 proves it). The Docker or Podman socket is never mounted, and the only folder shared is the lab folder.
3. **Documentation addresses.** The capture uses `192.0.2.0/24` and `198.51.100.0/24` ([RFC 5737](https://www.rfc-editor.org/rfc/rfc5737)), ranges reserved for examples, and `example.com`. No real host is involved.
4. **A pcap is data.** A real capture holds everything that crossed the wire. Delete `.pcap` files you no longer need, and never post one.
5. **No `sudo`, no system packages.** Nothing here installs software on your machine except pulling one container image.

### Where the Suricata comes from, and how far to trust it

You do not need to install Suricata on your machine. The exercises run the **8.0.7** release from the container image `docker.io/jasonish/suricata:8.0.7`. About that name, honestly: it is published by Jason Ish, who appears among the top contributors to the `OISF/suricata` repository on GitHub (the contributors list, read 2026-10-22). The Suricata documentation I read does not link to it, so I cannot call it the project's official image. Its README says tags follow Suricata versions and that the image is also on `quay.io` and `ghcr.io` ([README](https://github.com/jasonish/docker-suricata), read 2026-10-22). If that is not enough trust for you, the project's own routes are in its [install guide](https://docs.suricata.io/en/suricata-8.0.7/install.html): your distribution's package, the OISF packages for Ubuntu, Debian-family and RPM systems, or building the signed source from [suricata.io](https://suricata.io/download/). Do that in a disposable virtual machine and replace the `podman run` line in `run.sh` with a `suricata` command; every other file stays the same. Pinning a version tag and not `latest` is deliberate: the exercises were checked against 8.0.7 and the tag keeps a rerun comparable.

Rootless Podman note: the Suricata security page says "Suricata will not work with rootless Podman" for live capture, because it needs privileges to open a network interface. Reading a file needs none of that, and the exercises ran this way. Rootless Docker should behave the same (**est.**, not run). A normal (rootful) Docker would write root-owned output files; use Podman or rootless Docker.

### Setup

```bash
mkdir -p ~/ids-lab && cd ~/ids-lab
```

PowerShell (**est.**):

```powershell
New-Item -ItemType Directory -Force $HOME\ids-lab | Out-Null
Set-Location $HOME\ids-lab
```

Save these files in that folder. The Python scripts use only the standard library and run the same on Linux, macOS and Windows.

**`make_pcap.py`** builds the capture by hand: Ethernet, IP and TCP headers with real checksums, a three-way handshake, one HTTP request and response per connection. It holds one ordinary page request, one request for the path our first rule watches for, and twelve health-check requests from a made-up monitoring system.

```python
#!/usr/bin/env python3
# make_pcap.py - writes lab.pcap, a SYNTHETIC capture built from scratch with the standard library.
# Nothing in it came from a real network. Addresses are RFC 5737 documentation ranges.
# It holds three kinds of web traffic between made-up hosts:
#   1. one ordinary page request from 192.0.2.10
#   2. one request for /cah-lab/probe from 192.0.2.10 (the thing our first rule looks for)
#   3. twelve /healthcheck requests from 192.0.2.50, a pretend monitoring system (the noisy one)
import struct, sys

# "python3 -I make_pcap.py" writes lab.pcap. "python3 -I make_pcap.py case" writes lab-case.pcap, which holds
# only the probe request with its path in capital letters (used in the Evade step).
VARIANT = sys.argv[1] if len(sys.argv) > 1 else ""

SERVER_IP, SERVER_MAC = "198.51.100.20", "02:00:00:00:00:02"
CLIENT_MAC = "02:00:00:00:00:01"

def mac(s): return bytes(int(x, 16) for x in s.split(":"))
def ip4(s): return bytes(int(x) for x in s.split("."))

def csum(data):
    if len(data) % 2: data += b"\x00"
    total = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    while total >> 16: total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF

def frame(src, dst, sport, dport, seq, ack, flags, payload, ident):
    tcp = struct.pack("!HHIIBBHHH", sport, dport, seq, ack, 5 << 4, flags, 64240, 0, 0)
    pseudo = ip4(src) + ip4(dst) + struct.pack("!BBH", 0, 6, len(tcp) + len(payload))
    c = csum(pseudo + tcp + payload)
    tcp = tcp[:16] + struct.pack("!H", c) + tcp[18:]
    iph = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(tcp) + len(payload), ident, 0x4000, 64, 6, 0, ip4(src), ip4(dst))
    iph = iph[:10] + struct.pack("!H", csum(iph)) + iph[12:]
    smac, dmac = (CLIENT_MAC, SERVER_MAC) if dst == SERVER_IP else (SERVER_MAC, CLIENT_MAC)
    return mac(dmac) + mac(smac) + b"\x08\x00" + iph + tcp + payload

SYN, ACK, PSH, FIN = 0x02, 0x10, 0x08, 0x01
packets, clock, ident = [], [1700000000.0], [1]

def emit(data, dt=0.001):
    clock[0] += dt
    packets.append((clock[0], data))
    ident[0] += 1

def conversation(client, sport, request, response):
    c_seq, s_seq = 1000, 5000
    def c2s(flags, payload=b"", seq=None, ack=None):
        emit(frame(client, SERVER_IP, sport, 80, seq, ack, flags, payload, ident[0]))
    def s2c(flags, payload=b"", seq=None, ack=None):
        emit(frame(SERVER_IP, client, 80, sport, seq, ack, flags, payload, ident[0]))
    c2s(SYN, seq=c_seq, ack=0)
    s2c(SYN | ACK, seq=s_seq, ack=c_seq + 1)
    c2s(ACK, seq=c_seq + 1, ack=s_seq + 1)
    c2s(PSH | ACK, request, seq=c_seq + 1, ack=s_seq + 1)
    s2c(ACK, seq=s_seq + 1, ack=c_seq + 1 + len(request))
    s2c(PSH | ACK, response, seq=s_seq + 1, ack=c_seq + 1 + len(request))
    c2s(ACK, seq=c_seq + 1 + len(request), ack=s_seq + 1 + len(response))
    c2s(FIN | ACK, seq=c_seq + 1 + len(request), ack=s_seq + 1 + len(response))
    s2c(FIN | ACK, seq=s_seq + 1 + len(response), ack=c_seq + 2 + len(request))
    c2s(ACK, seq=c_seq + 2 + len(request), ack=s_seq + 2 + len(response))

def get(path, host="example.com", extra=""):
    return ("GET %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: lab-client/1.0\r\n%sConnection: close\r\n\r\n" % (path, host, extra)).encode()

OK = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 3\r\nConnection: close\r\n\r\nok\n"

if VARIANT == "case":
    conversation("192.0.2.10", 40003, get("/CAH-LAB/PROBE?id=1"), OK)
    OUTFILE = "lab-case.pcap"
else:
    conversation("192.0.2.10", 40001, get("/index.html"), OK)
    clock[0] += 5
    conversation("192.0.2.10", 40002, get("/cah-lab/probe?id=1", extra="X-CAH-Lab: ids-exercise\r\n"), OK)
    for i in range(12):
        clock[0] += 5
        conversation("192.0.2.50", 41000 + i, get("/healthcheck", host="monitor.example.com"), OK)
    OUTFILE = "lab.pcap"

with open(OUTFILE, "wb") as f:
    f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))   # classic pcap header, Ethernet
    for ts, data in packets:
        sec = int(ts); usec = int((ts - sec) * 1_000_000)
        f.write(struct.pack("<IIII", sec, usec, len(data), len(data)) + data)
print("wrote %s with %d packets" % (OUTFILE, len(packets)))
```

**`local.rules`** has our two rules. The first looks for a request whose path starts with `/cah-lab/probe`. The second is deliberately noisy: it fires on any request whose path contains `/healthcheck`, which a monitoring system makes every few seconds.

```text
# local.rules - our own rules. sids 1000000-1999999 are the range reserved for local use.
alert http any any -> any any (msg:"CAH LAB request for the probe path"; flow:established,to_server; http.uri; content:"/cah-lab/probe"; startswith; classtype:misc-activity; sid:1000001; rev:1;)
alert http any any -> any any (msg:"CAH LAB any request for a health check"; flow:established,to_server; http.uri; content:"/healthcheck"; classtype:misc-activity; sid:1000002; rev:1;)
```

**`run.sh`** runs Suricata over a capture inside the container. Read the flags once: `-r` reads the capture, `-S` loads only our rule file ("loaded exclusively, regardless of the rules set in the yaml"), `-l` is the output folder, `-k none` turns off checksum checks, `--set vars.address-groups.HOME_NET=...` sets `$HOME_NET` to our two documentation ranges, `--network none` and `--cap-drop all` shrink the container's powers (`dac_override` is added back because the image's configuration files are readable only by an account inside it).

```bash
#!/usr/bin/env bash
# run.sh RULES_FILE OUT_DIR [extra suricata args...]  - offline run over lab.pcap in a container with NO network.
set -u
rules=$1; out=$2; shift 2
mkdir -p "$out"
podman run --rm --network none --cap-drop all --cap-add dac_override --entrypoint suricata \
  -v "$PWD:/work:Z" -w /work docker.io/jasonish/suricata:8.0.7 \
  -c /etc/suricata/suricata.yaml -r "${PCAP:-lab.pcap}" -S "$rules" -l "$out" -k none \
  --set vars.address-groups.HOME_NET="[198.51.100.0/24,192.0.2.0/24]" "$@"
```

Make it executable with `chmod +x run.sh`. PowerShell (**est.**), save as `run.ps1`; it needs Podman for Windows, whose path mapping for the `-v` flag may differ from the Linux one:

```powershell
# run.ps1 RULES_FILE OUT_DIR [extra suricata args...] - offline run over lab.pcap (or $env:PCAP) in a container with NO network.
param([string]$Rules, [string]$Out)
$pcap = if ($env:PCAP) { $env:PCAP } else { 'lab.pcap' }
New-Item -ItemType Directory -Force $Out | Out-Null
& podman run --rm --network none --cap-drop all --cap-add dac_override --entrypoint suricata `
  -v "${PWD}:/work:Z" -w /work docker.io/jasonish/suricata:8.0.7 `
  -c /etc/suricata/suricata.yaml -r $pcap -S $Rules -l $Out -k none `
  --set 'vars.address-groups.HOME_NET=[198.51.100.0/24,192.0.2.0/24]' @args
exit $LASTEXITCODE
```

**`summarize.py`** reads a run's output folder and prints what you need: how many rules loaded and how many failed, the alerts by rule and by source, and a few counters. With `--expect` it is a canary check: it exits 1 if a rule you listed did not alert.

```python
#!/usr/bin/env python3
# summarize.py OUT_DIR - count the alerts in OUT_DIR/eve.json by rule and by source, say how many rules loaded
# and how many failed, then print a few counters from OUT_DIR/stats.log. It reads JSON lines only; a line it
# cannot parse is counted and skipped, never run.
# With "--expect SID [SID ...]" it also exits 1 and says MISSING for any listed rule that did not alert: a canary check.
import json, os, sys, collections

out = sys.argv[1]
expect = [int(x) for x in sys.argv[3:]] if len(sys.argv) > 3 and sys.argv[2] == "--expect" else []
by_rule, by_src, bad, engines = collections.Counter(), collections.Counter(), 0, []
with open(os.path.join(out, "eve.json")) as f:
    for line in f:
        try:
            ev = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if ev.get("event_type") == "stats":
            engines = ev["stats"]["detect"].get("engines", [])
        if ev.get("event_type") == "alert":
            a = ev["alert"]
            by_rule[(a["signature_id"], a["signature"])] += 1
            by_src[ev["src_ip"]] += 1
for e in engines:
    print("rules loaded: %d   rules FAILED to load: %d" % (e["rules_loaded"], e["rules_failed"]))
print("alerts by rule:")
for (sid, msg), n in sorted(by_rule.items()):
    print("  sid %-8s %3d  %s" % (sid, n, msg))
if not by_rule:
    print("  (none)")
print("alerts by source:", dict(by_src) or "(none)")
if bad:
    print("unparseable lines skipped:", bad)
want = ("decoder.pkts", "flow.total", "app_layer.flow.http", "detect.alert", "detect.alerts_suppressed")
print("stats.log (the last block, each counter's Total):")
seen = {}
with open(os.path.join(out, "stats.log")) as f:
    for line in f:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) == 3 and parts[0] in want:
            seen[parts[0]] = parts[2]
for k in want:
    print("  %-26s %s" % (k, seen.get(k, "(not present)")))
missing = [sid for sid in expect if not any(k[0] == sid for k in by_rule)]
for sid in missing:
    print("MISSING: rule %d did not alert" % sid)
if expect:
    print("canary:", "FAILED" if missing else "ok")
sys.exit(1 if missing else 0)
```

### Exercise 1: check your tools, pull the image, prove it is offline

**Predict.** Which of `suricata`, `snort`, `tcpdump`, `tshark`, `podman` and `docker` do you already have? Will a container started with `--network none` be able to look up `example.com`?

**Do (Bash).**

```bash
which suricata snort tcpdump tshark podman docker
podman pull docker.io/jasonish/suricata:8.0.7
podman run --rm --network none --entrypoint suricata docker.io/jasonish/suricata:8.0.7 --build-info | head -1
podman run --rm --network none --entrypoint sh docker.io/jasonish/suricata:8.0.7 -c 'cut -d: -f1 /proc/net/dev | tail -n +3; getent hosts example.com || echo "no name resolution"'
```

**Do (PowerShell, est.).**

```powershell
Get-Command suricata, snort, tcpdump, tshark, podman, docker -ErrorAction SilentlyContinue | Select-Object Name, Source
podman pull docker.io/jasonish/suricata:8.0.7
podman run --rm --network none --entrypoint suricata docker.io/jasonish/suricata:8.0.7 --build-info | Select-Object -First 1
podman run --rm --network none --entrypoint sh docker.io/jasonish/suricata:8.0.7 -c 'cut -d: -f1 /proc/net/dev | tail -n +3; getent hosts example.com || echo "no name resolution"'
```

**Check.** On the machine where this was run, `suricata` and `snort` were not installed, so the answer to "which do I have" was `tcpdump`, `tshark`, `podman` and `docker` (on that machine `docker` was Podman's Docker-compatible command, not Docker). The last two commands printed:

```text
This is Suricata version 8.0.7 RELEASE
    lo
no name resolution
```

One network interface (`lo`, loopback) and no name lookup: the container has no route to the internet and nothing outside can reach it. If you see more than `lo`, stop and find out why before you go on.

**Undo.** Nothing to undo. `podman rmi docker.io/jasonish/suricata:8.0.7` removes the image when you finish the lesson.

### Exercise 2: build the capture, and read it before Suricata does

**Predict.** How many HTTP requests are in the capture, and who sends them?

**Do (Bash).**

```bash
python3 -I make_pcap.py
tcpdump -nr lab.pcap 2>&1 | sed -n 1,4p
tshark -r lab.pcap -Y http.request -T fields -e ip.src -e http.request.uri 2>/dev/null | sort | uniq -c
```

**Do (PowerShell, est.).**

```powershell
python -I make_pcap.py
tshark -r lab.pcap -Y http.request -T fields -e ip.src -e http.request.uri | Sort-Object | Group-Object | Select-Object Count, Name
```

**Check.** The script says `wrote lab.pcap with 140 packets`. `tcpdump` shows the start of a TCP handshake (`Flags [S]`, then `[S.]`, then `[.]`) between `192.0.2.10` and `198.51.100.20`, with the first packet's time shown in your local time zone. `tshark` shows three kinds of request:

```text
      1 192.0.2.10	/cah-lab/probe?id=1
      1 192.0.2.10	/index.html
     12 192.0.2.50	/healthcheck
```

You can now say what Suricata ought to find before it finds it. Make a habit of this: **know the expected answer before you run the engine.** If you skip `tshark` and `tcpdump`, you can still go on, but you lose the independent check.

**Undo.** `rm lab.pcap` (PowerShell: `Remove-Item lab.pcap`). The script rebuilds an identical file.

### Exercise 3: run the rules and read the alert

**Predict.** Two rules, thirteen interesting requests. How many alerts, and for which rule?

**Do (Bash).**

```bash
chmod +x run.sh
./run.sh local.rules out; echo "run exit=$?"
python3 -I summarize.py out
sort out/fast.log | sed -n 1,2p
```

**Do (PowerShell, est.).**

```powershell
.\run.ps1 local.rules out; "run exit=$LASTEXITCODE"
python -I summarize.py out
Get-Content out\fast.log | Sort-Object | Select-Object -First 2
```

**Check.** The run prints four status lines and exits 0 (Suricata reported well under a second of work; the first start of a container takes longer). `summarize.py` prints:

```text
rules loaded: 2   rules FAILED to load: 0
alerts by rule:
  sid 1000001    1  CAH LAB request for the probe path
  sid 1000002   12  CAH LAB any request for a health check
alerts by source: {'192.0.2.50': 12, '192.0.2.10': 1}
stats.log (the last block, each counter's Total):
  decoder.pkts               140
  flow.total                 14
  app_layer.flow.http        14
  detect.alert               13
  detect.alerts_suppressed   (not present)
```

The `fast.log` file is the old one-line-per-alert format. The first two lines, sorted:

```text
11/14/2023-22:13:25.016998  [**] [1:1000001:1] CAH LAB request for the probe path [**] [Classification: Misc activity] [Priority: 3] {TCP} 192.0.2.10:40002 -> 198.51.100.20:80
11/14/2023-22:13:30.026998  [**] [1:1000002:1] CAH LAB any request for a health check [**] [Classification: Misc activity] [Priority: 3] {TCP} 192.0.2.50:41000 -> 198.51.100.20:80
```

Read the bracket `[1:1000001:1]`: generator id, `sid`, `rev`. Notice the date: 2023. In offline mode Suricata stamps an alert with the **packet's** time, and our script wrote packet times from November 2023. (Why `sort`? Suricata ran 8 worker threads, and alerts can reach the file out of time order. That is normal for a multi-threaded engine and the reason a SIEM sorts on the timestamp.)

Now `eve.json`, the format a SIEM reads. This prints the one alert for `/cah-lab/probe`, trimmed to its parts:

```bash
grep '"signature_id":1000001' out/eve.json | python3 -I -c "
import sys, json
e = json.loads(sys.stdin.readline())
print(json.dumps({k: e[k] for k in ('timestamp', 'flow_id', 'event_type', 'src_ip', 'src_port', 'dest_ip', 'dest_port', 'proto', 'app_proto')}))
print(json.dumps(e['alert']))
print(json.dumps(e['http']))"
```

```text
{"timestamp": "2023-11-14T22:13:25.016998+0000", "flow_id": 1454619519188515, "event_type": "alert", "src_ip": "192.0.2.10", "src_port": 40002, "dest_ip": "198.51.100.20", "dest_port": 80, "proto": "TCP", "app_proto": "http"}
{"action": "allowed", "gid": 1, "signature_id": 1000001, "rev": 1, "signature": "CAH LAB request for the probe path", "category": "Misc activity", "severity": 3}
{"hostname": "example.com", "url": "/cah-lab/probe?id=1", "http_user_agent": "lab-client/1.0", "http_content_type": "text/plain", "http_method": "GET", "protocol": "HTTP/1.1", "status": 200, "length": 3}
```

(`flow_id` is a different number on every run. The PowerShell twin is the same script: `Select-String '"signature_id":1000001' out\eve.json` finds the line, and any JSON tool reads it.) Three things to see. `"action": "allowed"` is the IDS saying it let the packet through, because it is not in line. `category` came from the rule's `classtype`. And the `http` object is context the engine parsed for you: that is what makes an alert useful to the person who reads it at 3 a.m.

**Undo.** `rm -r out`.

### Exercise 4: break the rule, and see which breaks are loud

**Predict.** You will break the first rule three ways. For each, will Suricata complain, and will the run fail?

**Do (Bash).** First, a typo that makes the rule invalid: a missing semicolon after `classtype`.

```bash
sed 's/classtype:misc-activity; sid:1000001/classtype:misc-activity sid:1000001/' local.rules > broken1.rules
./run.sh broken1.rules out_t -T; echo "test exit=$?"
./run.sh broken1.rules out_b1; echo "run exit=$?"
python3 -I summarize.py out_b1 | sed -n 1,5p
./run.sh broken1.rules out_b1f --set engine.init-failure-fatal=yes; echo "run exit=$?"
```

Second, a rule that contradicts itself (a request path in a message that goes to the client):

```bash
sed '2s/to_server/to_client/' local.rules > broken2.rules
./run.sh broken2.rules out_b2 >/dev/null; echo "run exit=$?"
python3 -I summarize.py out_b2 | sed -n 1,2p
```

Third, a typo that is valid: the leading slash is missing from the pattern, so the rule can never match a path that starts with one.

```bash
sed 's#content:"/cah-lab/probe"; startswith#content:"cah-lab/probe"; startswith#' local.rules > broken3.rules
./run.sh broken3.rules out_b3 >/dev/null; echo "run exit=$?"
python3 -I summarize.py out_b3 --expect 1000001 1000002 | tail -3; echo "canary exit=${PIPESTATUS[0]}"
```

**Do (PowerShell, est.).**

```powershell
(Get-Content local.rules) -replace 'classtype:misc-activity; sid:1000001','classtype:misc-activity sid:1000001' | Set-Content broken1.rules -Encoding ascii
.\run.ps1 broken1.rules out_t -T; "test exit=$LASTEXITCODE"
.\run.ps1 broken1.rules out_b1; "run exit=$LASTEXITCODE"
python -I summarize.py out_b1
.\run.ps1 broken1.rules out_b1f --set engine.init-failure-fatal=yes; "run exit=$LASTEXITCODE"
$r = Get-Content local.rules; $r[1] = $r[1] -replace 'to_server','to_client'; $r | Set-Content broken2.rules -Encoding ascii
.\run.ps1 broken2.rules out_b2 | Out-Null; "run exit=$LASTEXITCODE"
(Get-Content local.rules) -replace 'content:"/cah-lab/probe"; startswith','content:"cah-lab/probe"; startswith' | Set-Content broken3.rules -Encoding ascii
.\run.ps1 broken3.rules out_b3 | Out-Null; python -I summarize.py out_b3 --expect 1000001 1000002; "canary exit=$LASTEXITCODE"
```

**Check.** The first typo, with `-T` (test the configuration and rules, then stop), fails loudly:

```text
E: detect-parse: Signature missing required value "sid".
E: detect: error parsing signature "alert http any any -> any any (msg:"CAH LAB request for the probe path"; ...) from file broken1.rules at line 2
E: suricata: Loading signatures failed.
test exit=1
```

The same file in a **normal run** prints the first two error lines and then goes on: `run exit=0`, and `summarize.py` says `rules loaded: 1   rules FAILED to load: 1` with only the twelve alerts for the second rule. A sensor started with one bad rule runs without it, and only the log and the exit code of `-T` say so. The setting `--set engine.init-failure-fatal=yes` turns it into `Loading signatures failed.` and `run exit=1`. (I observed this setting work in 8.0.7; I did not find it documented in the pages I read, so check your version before you depend on it.)

The second break also ends `run exit=0` with `rules loaded: 1   rules FAILED to load: 1`, and the log line `rule 1000001 mixes keywords with conflicting directions`.

The third break is the dangerous one:

```text
rules loaded: 2   rules FAILED to load: 0
alerts by rule:
  sid 1000002   12  CAH LAB any request for a health check
MISSING: rule 1000001 did not alert
canary: FAILED
canary exit=1
```

Two rules loaded, nothing failed, exit 0, no error anywhere, and the rule for the thing you care about never fires. There is no message to find because nothing is wrong, as far as the engine can tell. **The canary check is the defense**: replay a capture that should alert and assert that it does, after every rule, version and configuration change. A real deployment keeps a small set of such captures, one per important rule, and runs them in CI before a rule file is promoted.

**Undo.** `rm -r out_t out_b1 out_b1f out_b2 out_b3 broken1.rules broken2.rules broken3.rules`.

### Exercise 5: tune the false positive

**Predict.** The twelve `/healthcheck` alerts all come from one made-up monitoring system, `192.0.2.50`. You are asked to quiet them without losing the first rule. Which of a suppression and a threshold will leave the monitoring system completely silent, and which will let one alert through?

**Do.** Save two small files. `suppress.config`:

```text
# suppress.config - hide sid 1000002 alerts from the monitoring system only.
suppress gen_id 1, sig_id 1000002, track by_src, ip 192.0.2.50
```

`limit.config`:

```text
# limit.config - at most one alert per source per 10 minutes for sid 1000002.
threshold gen_id 1, sig_id 1000002, type limit, track by_src, count 1, seconds 600
```

Bash:

```bash
./run.sh local.rules out_s --set threshold-file=/work/suppress.config >/dev/null
python3 -I summarize.py out_s | sed -n 1,3p
grep -E "detect.alert |detect.alerts_suppressed" out_s/stats.log
./run.sh local.rules out_l --set threshold-file=/work/limit.config >/dev/null
python3 -I summarize.py out_l | sed -n 1,5p
grep -E "detect.alert |detect.alerts_suppressed" out_l/stats.log
```

PowerShell (**est.**):

```powershell
.\run.ps1 local.rules out_s --set threshold-file=/work/suppress.config | Out-Null
python -I summarize.py out_s
Select-String -Path out_s\stats.log -Pattern 'detect.alert '
.\run.ps1 local.rules out_l --set threshold-file=/work/limit.config | Out-Null
python -I summarize.py out_l
Select-String -Path out_l\stats.log -Pattern 'detect.alert '
```

**Check.** With the suppression, only the first rule alerts, and the counters show where the twelve went:

```text
rules loaded: 2   rules FAILED to load: 0
alerts by rule:
  sid 1000001    1  CAH LAB request for the probe path
detect.alert                                                 | Total                     | 1
detect.alerts_suppressed                                     | Total                     | 12
```

With the limit (at most one alert per source per ten minutes), the monitoring system gets one alert and eleven are held back:

```text
alerts by rule:
  sid 1000001    1  CAH LAB request for the probe path
  sid 1000002    1  CAH LAB any request for a health check
detect.alert                                                 | Total                     | 2
detect.alerts_suppressed                                     | Total                     | 11
```

Which is right? Neither, in general. The suppression is exact and permanent: for as long as that line stays, a rule for `/healthcheck` tells you nothing more about `192.0.2.50`, including the day someone on that address uses the path for something else. The limit keeps one signal per window, so a change from "never" to "now" is visible, and the cost is that you must read a count of alerts as a lower bound on events. Write down, next to the tuning line, who asked for it and why; tuning with no owner turns into blindness. Note too that `detect.alerts_suppressed` counts what the limit held back, not only what a `suppress` line hid: the counter is "alerts not shown", and your count of real events is `detect.alert` plus it.

Keyword form of the same limit, **est.** (shown from the thresholding page, not run): add `threshold: type limit, track by_src, count 1, seconds 600;` to the options of rule `1000002`. The rule carries its own tuning that way, which travels with the rule file.

**Undo.** `rm -r out_s out_l`; keep the two config files for the loop below.

### Exercise 6: read the stats

**Predict.** If Suricata dropped packets, where would you see it? What number tells you it saw all 140 packets?

**Do (Bash).**

```bash
sed -n 1,12p out/stats.log
grep -E "^(decoder.pkts|decoder.bytes|flow.total|tcp.sessions|app_layer.flow.http|detect.alert)" out/stats.log
python3 -I -c "
import json
for line in open('out/eve.json'):
    e = json.loads(line)
    if e['event_type'] == 'stats':
        print(e['stats']['detect']['engines'][0])
        print('alerts', e['stats']['detect']['alert'], '  suppressed', e['stats']['detect']['alerts_suppressed'])"
```

**Do (PowerShell, est.).**

```powershell
Get-Content out\stats.log -TotalCount 12
Select-String -Path out\stats.log -Pattern '^(decoder.pkts|decoder.bytes|flow.total|tcp.sessions|app_layer.flow.http|detect.alert)'
```

**Check.** `stats.log` is a table of counters (`Counter | TM Name | Value`). The ones to know:

```text
decoder.pkts          140   packets the sensor received (140 packets were in the file)
decoder.bytes         10221
flow.total            14    connections it tracked (the 14 TCP connections in the file)
tcp.sessions          14
app_layer.flow.http   14    connections recognized as HTTP
detect.alert          13
```

`decoder.pkts` equal to the packet count of the capture is your evidence that nothing was lost on the way in. On a live capture the equivalent worry is the kernel's drop counter, which the Suricata tuning page ties to full ring buffers; a sensor that drops packets has blind spots, and those do not show as an alert. The same numbers are also a JSON `stats` event in `eve.json`, which is how a SIEM can graph them. The `detect.engines` entry there is the machine-readable version of "rules loaded, rules failed": alert on `rules_failed` greater than zero and Exercise 4's first break stops being silent.

**Undo.** Nothing to undo; the files are only read.

### Exercise 7 (optional): capture your own loopback traffic

This replaces our hand-built file with traffic your own computer actually made, so you see the same rule fire on a real capture. It needs permission to capture on the loopback interface, which on many Linux systems means membership in a group the packaging created for it (the `wireshark` group on Debian-family systems; read your distribution's page). **If your account cannot capture without `sudo`, skip this exercise.** Do not run capture tools as root on a machine you share.

**Predict.** A tiny web server on `127.0.0.1` port `18090`, two requests to it from `curl`. What will a rule that looks only at the path say?

**Do (Bash).** Everything on loopback; the server listens on `127.0.0.1` only, and you stop it at the end.

```bash
mkdir -p srv && echo hello > srv/index.html
python3 -I -m http.server 18090 --bind 127.0.0.1 --directory srv >/dev/null 2>&1 &
SERVER=$!
sleep 1; ss -ltn | grep ':18090 '
tshark -i lo -f "tcp port 18090" -w loop.pcapng -a duration:8 2>&1 | tail -1 &
CAPTURE=$!
sleep 2
curl -s -o /dev/null http://127.0.0.1:18090/index.html
curl -s -o /dev/null "http://127.0.0.1:18090/cah-lab/probe?id=9"
wait $CAPTURE
kill $SERVER
tshark -r loop.pcapng -F pcap -w loop.pcap 2>&1 | tail -1
PCAP=loop.pcap ./run.sh local.rules out_loop | tail -1
python3 -I summarize.py out_loop | sed -n 1,4p
```

**Do (PowerShell, est.).** On Windows the loopback interface needs Npcap's loopback adapter and its name varies; list interfaces with `tshark -D` and replace `lo` below.

```powershell
New-Item -ItemType Directory -Force srv | Out-Null; 'hello' | Set-Content srv\index.html
$server = Start-Process python -ArgumentList '-I','-m','http.server','18090','--bind','127.0.0.1','--directory','srv' -PassThru -WindowStyle Hidden
Start-Sleep 1
$cap = Start-Process tshark -ArgumentList '-i','lo','-f','"tcp port 18090"','-w','loop.pcapng','-a','duration:8' -PassThru -WindowStyle Hidden
Start-Sleep 2
curl.exe -s -o NUL http://127.0.0.1:18090/index.html
curl.exe -s -o NUL "http://127.0.0.1:18090/cah-lab/probe?id=9"
$cap.WaitForExit()
Stop-Process -Id $server.Id
tshark -r loop.pcapng -F pcap -w loop.pcap
$env:PCAP = 'loop.pcap'; .\run.ps1 local.rules out_loop | Out-Null; Remove-Item Env:PCAP
python -I summarize.py out_loop
```

**Check.** `ss` shows the server on `127.0.0.1:18090` and nowhere else. The capture holds a few dozen packets (25 in the run recorded here). The summary:

```text
rules loaded: 2   rules FAILED to load: 0
alerts by rule:
  sid 1000001    1  CAH LAB request for the probe path
alerts by source: {'127.0.0.1': 1}
```

One alert, for the `/cah-lab/probe` request. The `/healthcheck` rule is quiet because nobody asked for that path. Same rule, real packets, and the engine did not care that the addresses were `127.0.0.1` (the rule says `any`).

**Undo.** The server is stopped by the `kill`; confirm with `ss -ltn | grep -c ':18090 '` (prints `0`). Delete the captures: `rm -r srv loop.pcapng loop.pcap out_loop`.

### Exercise 8: evade your own rule, then fix it

**Predict.** An attacker (you, against your own lab) asks for `/CAH-LAB/PROBE?id=1`. Does rule `1000001` fire? Does the web server in the capture care about the case? (In the capture it answers `200 OK` to everything; real servers differ.)

**Do (Bash).**

```bash
python3 -I make_pcap.py case
PCAP=lab-case.pcap ./run.sh local.rules out_c >/dev/null
python3 -I summarize.py out_c --expect 1000001 | sed -n '1,3p;$p'
sed '2s/startswith;/startswith; nocase;/;2s/rev:1/rev:2/' local.rules > nocase.rules
sed -n 2p nocase.rules
PCAP=lab-case.pcap ./run.sh nocase.rules out_c2 >/dev/null
python3 -I summarize.py out_c2 --expect 1000001 | sed -n '1,3p;$p'
PCAP=lab.pcap ./run.sh nocase.rules out_c3 >/dev/null
python3 -I summarize.py out_c3 --expect 1000001 1000002 | sed -n '1,4p;$p'
```

**Do (PowerShell, est.).**

```powershell
python -I make_pcap.py case
$env:PCAP = 'lab-case.pcap'; .\run.ps1 local.rules out_c | Out-Null; python -I summarize.py out_c --expect 1000001
$r = Get-Content local.rules; $r[1] = ($r[1] -replace 'startswith;','startswith; nocase;') -replace 'rev:1','rev:2'; $r | Set-Content nocase.rules -Encoding ascii
.\run.ps1 nocase.rules out_c2 | Out-Null; python -I summarize.py out_c2 --expect 1000001
$env:PCAP = 'lab.pcap'; .\run.ps1 nocase.rules out_c3 | Out-Null; python -I summarize.py out_c3 --expect 1000001 1000002
Remove-Item Env:PCAP
```

**Check.** The original rule is blind to the upper-case request:

```text
rules loaded: 2   rules FAILED to load: 0
alerts by rule:
  (none)
canary: FAILED
```

The fixed rule (`rev:2`, with `nocase;` after `startswith;`) fires on it, and still fires on the normal capture without breaking the other rule:

```text
rules loaded: 2   rules FAILED to load: 0
alerts by rule:
  sid 1000001    1  CAH LAB request for the probe path
canary: ok
```

The lesson is the one rule writers learn early: a `content` match is a literal comparison, and the attacker controls the bytes. `nocase` fixes this one. It does not fix the general problem; see the next section.

**Undo.** `rm -r out_c out_c2 out_c3 lab-case.pcap nocase.rules`.

## Optional: a live sensor in a disposable virtual machine (shown, not run)

**Cost and teardown first.** This is the one part that needs more than your laptop's spare cycles: a second machine, ideally a virtual machine you create for this and delete afterward. On your own computer that costs nothing extra. On a cloud account it is the provider's bill; this page reads no price and gives none, so check your provider's price page and set a budget alert first ([How money works in the cloud](How-Money-Works-in-the-Cloud.md)). Teardown: remove any NFQUEUE rule from the firewall **before** you stop Suricata, stop the service, and delete the virtual machine and its disk. Do this only on a virtual machine on a host-only or internal virtual network that you own, and never on a bridged network next to your real devices ([Red and blue as yin and yang](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md#a-safe-network-for-the-lab)).

What the live version looks like, from the Suricata documentation (read 2026-10-22; **none of this was run**):

- **Passive (IDS)** on one interface: `suricata -c /etc/suricata/suricata.yaml --af-packet=eth0` (the `--af-packet[=<device>]` option "Enable[s] capture of packet using AF_PACKET on Linux"). Alerts land in `eve.json` exactly as in Exercise 3.
- **In line at layer 3 (IPS) with NFQUEUE**: Linux's Netfilter can hand packets to a program in user space. The documented sequence is to start Suricata on queue 0 (`sudo suricata -c /etc/suricata/suricata.yaml -q 0`) and then, for a gateway, send forwarded traffic to it with `sudo iptables -I FORWARD -j NFQUEUE`. The order matters, and the documentation says why: "By default, if no userspace program is listening on an Netfilter queue, then all packets that are to be queued are dropped." If the engine is not running, traffic stops. The `bypass` queue option makes the rule behave like ACCEPT when nothing is listening: a fail-open choice, which is a design decision (see the threat model).
- **In line at layer 2 (IPS) with AF_PACKET**: two interfaces and `copy-mode: ips` in the `af-packet` section of the YAML file; traffic is bridged through Suricata.

In IPS mode the documentation says the default exception policies "are set to block (drop)" so that rules are not bypassed when the engine hits an error state, which means the same overload that makes an IDS blind makes an IPS drop traffic. Test with rules set to `alert` and move them to `drop` one at a time ([IPS Concept](https://docs.suricata.io/en/suricata-8.0.7/ips/ips-concept.html), [Setting up IPS/inline for Linux](https://docs.suricata.io/en/suricata-8.0.7/ips/setting-up-ipsinline-for-linux.html), [Command Line Options](https://docs.suricata.io/en/suricata-8.0.7/command-line-options.html), read 2026-10-22).

Screenshot to take yourself: your own EVE log in your SIEM, with the address redacted (see [Screenshots policy](Screenshots-Policy.md)). This page includes no console screenshots.

## Tamper and evade: how an attacker gets past a sensor (concept level)

A defender who has not thought like the attacker has not finished the job. This section describes the families of evasion so that you recognize them in a design review. It gives no tooling and no recipes, and Exercise 8 is the only one that touches one, against your own lab.

**Fragmentation and segmentation.** A sender can split a message across several IP fragments or TCP segments, send them out of order, or send overlapping pieces. The destination machine puts them back together by its own operating system's rules. The sensor must put them back together the same way, or it inspects something the destination never saw (an **insertion**: the sensor takes data the host throws away) or misses something the host accepts (an **evasion**). This is the subject of the classic paper by Ptacek and Newsham, "Insertion, Evasion, and Denial of Service: Eluding Network Intrusion Detection" (January 1998), which argues that a sensor that does not model the end hosts can be fooled however good its signatures are ([text at insecure.org](https://insecure.org/stf/secnet_ids/secnet_ids.html), read 2026-10-22). What defenders do: reassemble and defragment in the sensor, tell the sensor which operating system each address range runs (Suricata's `host-os-policy` setting exists for this: "Operating systems differ in the way they process fragmented packets and streams"), and in IPS mode rely on the way it works in line, where the first data it receives is accepted and "the traffic on the wire is rewritten to match the first data" ([IPS Concept](https://docs.suricata.io/en/suricata-8.0.7/ips/ips-concept.html)). The cost is memory and CPU, and the `defrag` and `stream` memory caps are where an overloaded sensor starts making choices.

**Encryption.** Covered above: TLS hides the content, TLS 1.3 hides the certificate, Encrypted Client Hello hides the site name. The evasion here needs no skill, only the same protocol everyone else uses. What defenders do: inspect where TLS ends (with the design cost described above), detect on the host, and use the metadata that remains (destination, fingerprint, volume, timing).

**Slow, small and spread.** A sensor counts over windows. A patient visitor stays under the count: the same idea as the slow guesser in the [logs lesson](Logs-SIEM-and-Detection-Basics.md#build-break-detect-evade-defend-the-local-loop). Sensors also have limits per flow: with `stream.bypass` on, Suricata's tuning page says inspection of a flow is skipped once `stream.reassembly.depth` (1 megabyte in its example) is reached, which is a performance choice and also a place where an attack can sit if it arrives late in a long flow. What defenders do: choose depths and windows on purpose and write down the reason, count over several time scales and by destination as well as by source, and keep host-side detection for what the wire cannot show.

**Rule-matching gaps.** A signature is a literal description of one known form. Change the form and the match fails: the capital letters in Exercise 8; a different encoding of the same text that the target still accepts; the same attack carried on a port the rule did not expect. Suricata's documentation says its "protocol detection is port agnostic (in most cases)", which closes one gap (the Snort 2.9 behavior it is compared with needed a configured port for its HTTP handling), and Snort's rule categories include one named `indicator-obfuscation` for obfuscated content. What defenders do: write rules on the behavior and not on a tool's signature string, use normalized buffers and case-insensitive matches where the protocol allows it, test each important rule against variants in a capture you built, and layer a second detection that fails differently.

**Blinding.** Rather than hide one attack, make the sensor useless: flood it with traffic that is cheap to send and expensive to inspect, so that it drops packets or falls behind, or trigger so many alerts that a human stops reading. What defenders do: watch the drop counters and the alert rate as health signals, size with headroom, and decide in advance whether an overloaded in-line sensor fails open or closed.

## Threat model of the IDS itself

The sensor is software that reads hostile input, runs with high privilege and is trusted to tell the truth. The same shape as [Threat model](Threat-Model.md):

| Asset | Threat | Likelier cause | Control | Residual risk |
|---|---|---|---|---|
| The sensor host | Compromise through a bug in a protocol parser: it reads untrusted data with elevated privilege | Unpatched version; sensor on the same network it protects | Keep the engine current (the download page marks 7.0.17 as end of life); run it as a non-root user after startup, as the Suricata security page describes; isolate the management interface | A zero-day parser bug; assume the sensor can be taken |
| The rule set | Rule poisoning or a bad update: a feed or your own repository is changed so rules are removed, weakened or harmful in IPS mode | Compromised feed or mirror; unreviewed automatic update; a copied rule nobody read | Pull through one updater; keep rules in version control; review diffs; local rules in their own file with local sids; run alert-only first; canary captures after every update | A trusted feed that is itself compromised |
| Detection coverage | Resource exhaustion: overload makes the sensor drop packets, fall behind, or (in line) drop traffic | Undersized hardware; traffic spike; deliberate flood; a very expensive rule | Size with headroom; watch `decoder.pkts` against expected and the kernel drop counter; decide fail-open or fail-closed on purpose (`bypass` option for NFQUEUE) | A fail-open sensor is blind under attack; a fail-closed one is an outage |
| The alert record | Log tampering: an attacker with the sensor deletes or rewrites `eve.json` | Sensor compromise; permissive file permissions | Ship alerts off the box as they happen (syslog or an agent to the SIEM); restrict who can read and write the log folder; time-sync the sensor | The window between an event and its shipment |
| Alert quality | Silent failure: a rule that does not load, a typo that never matches, a feed that stops updating | Exercise 4's second and third breaks; an updater that fails quietly | Canary replay; alert on `rules_failed` > 0; alert when the rule set is older than expected | A canary that covers few rules |
| The feed of packets | A mirror or tap that is misconfigured or full: the sensor is healthy and sees half the traffic | Wrong source port; mirror port slower than the sources; a switch that cannot mirror everything | Check against a known flow after every network change; compare sensor packet counts with interface counters | A change nobody tells the sensor team about |
| Analysts' attention | Alert fatigue: the one that matters is buried under noise | No tuning; no owner for suppressions; everything set to the same severity | Tune with an owner and a reason; review suppressions on a schedule; tiers of severity | Attackers who hide in a suppressed source |
| The privacy of the people on the network | The sensor keeps payload and URLs and becomes a store of private data | Full packet capture with no retention limit; TLS inspection that stores plaintext | Collect the least that answers the question; retention limits; access control; say so in your policy | A breach of the sensor's store |

## Build, break, detect, evade, defend (the local loop)

The same loop the rest of the project uses ([Why this exists](Why-This-Exists.md)), on the two rules and the capture from the exercises. Nothing here leaves your computer.

**Build.** Two rules and a capture whose answer you know: thirteen alerts, one for `1000001` and twelve for `1000002` (Exercises 2 and 3).

**Break.** Introduce the typo that is valid: drop the slash from the pattern (Exercise 4, third break). The run still exits 0, both rules load, and the first rule never fires.

**Detect.** The canary: `summarize.py ... --expect 1000001 1000002` says `MISSING` and exits 1. Two other signals catch the other two breaks: `rules FAILED to load` (and `-T` in CI) for a rule that does not parse, and a `stats` check on `rules_failed`.

**Evade.** Ask for `/CAH-LAB/PROBE` (Exercise 8). The rule loads and the canary on the normal capture passes, and the upper-case request goes by with no alert. A canary built from one fixed capture does not see this class of gap; it needs a test set with variants.

**Defend.** Add `nocase`, raise `rev` to 2, and put the upper-case capture in the canary set. Make a loading failure fatal where you can (`--set engine.init-failure-fatal=yes`) and alert on `rules_failed`. Tune the noisy rule with an owner and a reason, as in Exercise 5. Ship `eve.json` off the box, so that a sensor taken over still leaves a record. Then pair it with something that fails differently, such as a host agent ([the next lessons in this track](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md); this link may not resolve until it merges).

**Undo.** Delete the output folders and the captures. `podman rmi docker.io/jasonish/suricata:8.0.7` removes the image.

### Flip the board

**The attacker.** You have written permission to test a lab whose edge sensor runs a popular open ruleset with the monitoring system tuned out, as in Exercise 5. Name three things you would try that the sensor will probably miss, and for each the extra signal that would catch it. Answers below.

<details>
<summary>What to find</summary>

1. **Use the tuned-out address.** A source that is suppressed for a rule is silent for that rule. Anything running on, or relayed through, the monitoring system's address gets a free pass on it. The signal: a review of every suppression on a schedule, narrower suppressions (one rule, one source, one destination), and a limit instead of a suppression where a first-time-in-a-while alert matters.
2. **Hide in TLS.** Run the command channel inside a protocol the sensor cannot read. The signal: metadata (destination, SNI while visible, JA3 or JA4 fingerprint, flow sizes and timing), DNS logs, and host-side telemetry.
3. **Change a byte.** Re-case, re-encode or re-route the request so that a literal match fails. The signal: rules written on behavior, variants in your canary set, and an anomaly layer such as a spike in HTTP errors from one source.
4. **Be patient.** Spread the activity over days so that no window sees enough. The signal: counts over longer windows, per destination as well as per source.

</details>

**The reviewer.** A teammate proposes: "Put an IPS on the edge tomorrow with the full open ruleset, every rule set to drop, updating itself every night. Done by Friday." Find at least five problems.

<details>
<summary>What to find</summary>

1. **No alert-only period.** Nobody has seen the false positives, and in line each one is an outage.
2. **Fail-open or fail-closed is undecided.** If the engine stops, the link either stops or the protection goes. Someone must choose, in writing.
3. **Self-updating rules into drop mode.** A bad or malicious update then changes what is blocked with no review. Updates belong in version control, with a diff and a canary run.
4. **Behind NAT, the addresses are wrong.** On a WAN interface the sensor sees translated addresses; OPNsense's own documentation warns about it. `$HOME_NET` has to be right.
5. **Most of it is TLS.** The sensor will see little inside the traffic; what does the team expect it to catch?
6. **Sizing is a guess.** No one measured the busiest hour or the drop counters.
7. **No canary tests, no health alert.** If a rule stops loading, no one finds out.
8. **No owner and no runbook.** Who is paged when it fires, and who can turn a rule off at 2 a.m.?
9. **Licensing and terms were not read** for the rule feed and the engine in the way the team will use them.

</details>

## Checkpoint

- What is the difference between an IDS and an IPS, and why is an IPS rule more expensive to get wrong?
- Name three ways a sensor gets its traffic, and one limit of each.
- What can a network sensor still see when the traffic is TLS 1.3, and what does Encrypted Client Hello take away?
- Where would you put one sensor on the small network you drew, and what would you miss by putting it there?
- Which of Snort 2, Snort 3 and Suricata is at end of life, according to the vendor's own post, and what follows from it?
- Read this rule aloud: `alert http any any -> any any (msg:"x"; flow:established,to_server; http.uri; content:"/a"; sid:1000005; rev:1;)`. What are the action, the protocol, the direction and the `sid`, and is the `sid` in the local range?
- In Exercise 4, which of the three breaks printed an error? Which one did not? How would you catch the one that did not?
- In Exercise 5, what did the suppression give up that the limit kept?
- Why is `detect.alerts_suppressed` worth graphing?
- Name two rule-feed license questions you would settle before using a feed in a business.
- Give two controls on the sensor itself that keep its own logs trustworthy.

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| `Permission denied` on `/etc/suricata/suricata.yaml` | The container dropped the capability that lets root read other users' files | Keep `--cap-add dac_override` in `run.sh` |
| `rules loaded: 0` and no alerts | `-S` pointed at a file that does not exist in `/work`, or the rule file is empty | `ls`, then read `out/suricata.log` for `rule files processed` |
| The run exits 0 but a rule is missing | A rule failed to load and Suricata ran without it | `summarize.py` (FAILED count), `-T`, and `engine.init-failure-fatal` |
| Alerts appear out of time order | Eight worker threads write independently | Sort on `timestamp`; this is normal |
| No alert from `loop.pcap` | The capture is empty (no capture permission), or the request never reached the server | `tshark -r loop.pcap -Y http.request`; start the server before the capture |
| `suppress` seems to do nothing | The `sig_id` does not match, the file is not loaded, or `track`/`ip` do not match the source | `threshold-config: Threshold config parsed: 1 rule(s) found` in `suricata.log`, and the counter `detect.alerts_suppressed` |
| Your fix to a rule has no effect | `rev` was not raised, or the old file was loaded | Raise `rev` on every change; confirm which file `-S` loaded |
| Output files owned by root | Ordinary (rootful) Docker | Use Podman or rootless Docker |
| `podman: command not found` on Windows | Podman for Windows is not installed | Install it from Podman's site, or use WSL 2 (**est.**) with the Bash commands |

## What this page does not prove

- **Throughput and sizing.** I measured nothing on a busy link. The exercises process 140 packets.
- **Snort.** I did not run any version of it. The Snort rule on this page is a translation written from its manual.
- **Live capture and in-line mode.** Never run here. The NFQUEUE and AF_PACKET material is from the documentation.
- **The Emerging Threats Open ruleset.** I read its license and download instructions and did not download or run the rules. How noisy it is on your network is yours to find out.
- **Appliance packages.** pfSense and OPNsense are described from their documentation pages; I installed neither.
- **The SIEM leg.** Wazuh reading `eve.json` is from Wazuh's guide, which tested Suricata 6.0.8; I did not run it.
- **TLS inspection and encrypted traffic.** Described from the RFCs and Suricata's docs. No decryption was tried.
- **Detection quality.** Two rules and a capture I made teach the mechanics. They say nothing about how well any rule set catches real attacks.

## Where this shows up in this project

- [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md) bundles Suricata as one of its network watchers.
- [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) is the host-side half of the story, and where an `eve.json` feed would land.
- [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) is the rule-writing and tuning vocabulary used here, on log lines instead of packets.
- [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) is the filter layer in front of the content-inspection layer.
- [Security tools basics](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md) is the traffic a sensor like this would flag: a scan, a web scanner.
- The track's other lessons: [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md), [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) and [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md). They may not resolve until they merge.

## Claims register

All read-only requests; retrieved **2026-10-22**. "Observed" means I ran it that day. Documentation URLs for Suricata name release 8.0.7, because the `latest` pages describe an unreleased 9.0 development version.

| Claim | Source | Status |
|---|---|---|
| Suricata is "a high performance Network IDS, IPS and Network Security Monitoring engine", owned by the community-run non-profit OISF, source under GPL version 2 | [What is Suricata](https://docs.suricata.io/en/suricata-8.0.7/what-is-suricata.html) (the `latest` page, same text) | Read |
| Stable 8.0.7 released September 15, 2026; 7.0.17 listed End-of-Life | [suricata.io/download](https://suricata.io/download/) (fetched as `suricata.io/download/`) | Read |
| IPS mode allows all traffic by default and uses drop/reject rules; inline at layer 2 (AF_PACKET, DPDK) or layer 3 (NFQueue, IPFW); sliding-window inspection and rescanning cost; first data accepted and wire rewritten; exception policies block by default in IPS mode | [IPS Concept](https://docs.suricata.io/en/suricata-8.0.7/ips/ips-concept.html) | Read |
| NFQUEUE use (`-q 0`, `iptables -I FORWARD -j NFQUEUE`); with no listener queued packets are dropped; `bypass` option | [Setting up IPS/inline for Linux](https://docs.suricata.io/en/suricata-8.0.7/ips/setting-up-ipsinline-for-linux.html) | Read; **not run** |
| Rule format, actions, protocol list, variables, sticky buffers, `sid`, `rev`, `classtype`, `metadata`; the reserved-range sentence | [Rules Format](https://docs.suricata.io/en/suricata-8.0.7/rules/intro.html), [Meta Keywords](https://docs.suricata.io/en/suricata-8.0.7/rules/meta.html) | Read; rules parsed and fired by Suricata 8.0.7 (observed) |
| `1000000-1999999` is reserved for local use | [sidallocation.org](https://sidallocation.org/) | Read |
| Thresholds (`threshold`, `limit`, `both`, `backoff`), `detection_filter`, `rate_filter`, `suppress` syntax and meaning, global threshold file | [Thresholding Keywords](https://docs.suricata.io/en/suricata-8.0.7/rules/thresholding.html), [Global thresholds](https://docs.suricata.io/en/suricata-8.0.7/configuration/global-thresholds.html) | Read; the `suppress` and `threshold` lines in Exercise 5 observed to give 1 and 2 alerts with 12 and 11 held back. The in-rule `threshold:` keyword is **est.**, not run |
| Differences between Suricata and Snort 2.9 rules (urilen, http_header, port-agnostic protocol detection) | [Differences From Snort](https://docs.suricata.io/en/suricata-8.0.7/rules/differences-from-snort.html) | Read |
| Command-line flags `-r`, `-S`, `-l`, `-T`, `-k`, `-q`, `--af-packet`, `--set` | [Command Line Options](https://docs.suricata.io/en/suricata-8.0.7/command-line-options.html) | Read; `-r -S -l -T -k --set` observed |
| `engine.init-failure-fatal=yes` makes a failed rule load fatal | Observed (exit 1 in place of 0) | Observed in 8.0.7; **not found in the docs pages I read** |
| EVE JSON outputs alerts, anomalies, metadata, file info and protocol records; file, syslog and Redis outputs; TLS fields including SNI, JA3, JA4; a stats record | [EVE JSON Output](https://docs.suricata.io/en/suricata-8.0.7/output/eve/eve-json-output.html) | Read; `alert`, `http`, `flow`, `stats` records observed |
| Runmodes: Suricata is multi-threaded; `workers` runs the full pipeline per thread | [Runmodes](https://docs.suricata.io/en/suricata-8.0.7/performance/runmodes.html) | Read; eight worker threads observed |
| `ring-size` and packet drop counters; `mpm-algo` and Hyperscan; `stream.bypass` and `reassembly.depth` | [Tuning considerations](https://docs.suricata.io/en/suricata-8.0.7/performance/tuning-considerations.html) | Read |
| `host-os-policy`; `defrag` and `stream` memcaps | [Configuration: suricata.yaml](https://docs.suricata.io/en/suricata-8.0.7/configuration/suricata-yaml.html) | Read |
| Suricata processes untrusted data with elevated privilege; supply chain attacks on rule distribution; can drop to a non-root user; will not work with rootless Podman (live capture) | [Security Considerations](https://docs.suricata.io/en/suricata-8.0.7/security.html) | Read |
| Lua rules sandboxed and enabled by default as of Suricata 8.0 | [Lua Scripting for Detection](https://docs.suricata.io/en/suricata-8.0.7/rules/lua-detection.html) | Read; not run |
| Suricata-Update is the preferred rule manager; `disable.conf` | [Rule Management with Suricata-Update](https://docs.suricata.io/en/suricata-8.0.7/rule-management/suricata-update.html), [ET Open instructions](https://rules.emergingthreats.net/OPEN_download_instructions.html) | Read; not run |
| The container image `docker.io/jasonish/suricata:8.0.7` contains Suricata 8.0.7 with NFQ, AF_PACKET and Lua; offline pcap runs work under rootless Podman 5.4.2 | [Docker Hub repository API](https://hub.docker.com/v2/repositories/jasonish/suricata/), [README](https://github.com/jasonish/docker-suricata), `--build-info` output | Observed. It is a third-party image by a core contributor and not linked from the project's docs: its being "official" is **not verified** |
| Snort 2 end of life (all versions), no Talos rule support for Snort2; Snort 3.12.4.0 released | [Snort blog, 2026-10-21](https://blog.snort.org/) | Read; the post is one day old and the page will change |
| Snort 3 is a redesign (threads, Lua configuration, 200+ plugins, syntax tweaks); feature table vs Snort 2 | [Snort 3](https://www.snort.org/snort3), [Snort 3 user manual](https://www.snort.org/downloads/snortplus/snort_user.html), [reference manual](https://www.snort.org/downloads/snortplus/snort_reference.html) | Read; not run |
| Snort engine and Community rules are GPL v2; Proprietary Snort Rules need registration or a subscription and a Non-Commercial Use License | [Snort license](https://www.snort.org/license) | Read. The subscriber terms were not read in full |
| Snort downloads list Community and Registered rule packages; Snort 3.12.4.0, Snort 2.9.20 | [Snort downloads](https://www.snort.org/downloads) | Read |
| ET Open rules: BSD license for sids 2000000 to 2799999; some GPLv2; ET Pro range separate; per-engine download URLs; update once daily on weekdays, MD5 validation | [ET Open folder](https://rules.emergingthreats.net/open/suricata-8.0.7/) (the `LICENSE` file), [instructions](https://rules.emergingthreats.net/OPEN_download_instructions.html) | Read; rules not downloaded |
| pfSense IDS/IPS through Snort and Suricata packages | [pfSense IDS / IPS](https://docs.netgate.com/pfsense/en/latest/packages/snort/index.html), [package list](https://docs.netgate.com/pfsense/en/latest/packages/list.html) | Read; the IDS page was last updated June 30, 2022 per its footer; the packages' settings pages not read |
| OPNsense IPS is based on Suricata with Netmap; IDS, Netmap IPS and Divert IPS modes; NAT warning on WAN; EVE to syslog; rulesets download tab | [OPNsense IDS and IPS](https://docs.opnsense.org/manual/ips.html) | Read; not run |
| Wazuh reads `eve.json` through a `localfile` block with `json` format; tested with Suricata 6.0.8 | [Wazuh network IDS integration](https://documentation.wazuh.com/current/proof-of-concept-guide/integrate-network-ids-suricata.html) | Read; not run |
| SPAN/port mirroring and tap descriptions, the speed caution | [Wireshark: Ethernet capture setup](https://wiki.wireshark.org/CaptureSetup/Ethernet) | Read |
| AWS Traffic Mirroring copies traffic from an elastic network interface to out-of-band appliances | [What is Traffic Mirroring](https://docs.aws.amazon.com/vpc/latest/mirroring/what-is-traffic-mirroring.html) | Read; other clouds' pages not read |
| TLS 1.3 encrypts all handshake messages after the ServerHello | [RFC 8446 section 1.2](https://www.rfc-editor.org/rfc/rfc8446.txt) | Read |
| TLS Encrypted Client Hello is RFC 9849 (March 2026) | [RFC 9849](https://www.rfc-editor.org/rfc/rfc9849.txt) | Read the first page; the mechanism not studied |
| Insertion and evasion against network IDS (Ptacek and Newsham, January 1998) | [insecure.org mirror](https://insecure.org/stf/secnet_ids/secnet_ids.html) | Read the abstract and the definitions |
| Snort rule categories include `indicator-obfuscation` | [Explanation of rules](https://www.snort.org/rules_explanation) | Read |
| The capture, its checksums and its counts (140 packets, 14 connections, 13 alerts), the three breaks, the 12 and 11 held-back alerts, the canary results, the loopback capture (25 packets, one alert) | Run on Linux with Suricata 8.0.7, Python 3.13.5, tcpdump 4.99.5, tshark 4.4.19, Podman 5.4.2 | Observed once; counts of alerts are stable, `flow_id` and timestamps vary |
| Every PowerShell command, Docker, Windows, macOS, Snort in any version, live capture, in-line mode | | **Not run (est.)** |
