# Security tools basics: Nmap, OpenVAS, Burp Suite Community Edition, Metasploit and friends

Side page to the threat pages. Read it after [Threats in plain words](Threats-in-Plain-Words.md) and [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md), and alongside [Threat frameworks: STRIDE, ATT&CK, ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md).

Its companion, [Red and blue as yin and yang, and your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md), covers authorization and the lab machine first; that link may not resolve until that page merges.

Next: [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the Bash and Python parts of the free path were run once on Linux; everything else was not.** On **2026-10-22** the author ran the lab scripts, the Nmap commands, the `curl` commands and the detector below on a Debian-based Linux machine (Nmap 7.98, Python 3.13.5, curl 8.21.0), as an ordinary user with no `sudo`, and pasted trimmed output from those runs. **Not run:** every PowerShell command (written from Microsoft's and Nmap's documentation, marked **est.**), anything on Windows or macOS, Burp Suite, OWASP ZAP, Wireshark, Greenbone, Metasploit, Nikto, nuclei, and the Juice Shop container. Those parts are written from each project's own pages (listed in the [claims register](#claims-register)) and say so where it matters. Output varies with your versions; trust your terminal over this page.

> **Prerequisites.** You can open a terminal and run a command ([The terminal and your first script](Terminal-and-Your-First-Script.md)), you know what a port is ([Networking basics](Networking-Basics-for-This-Project.md#ports-and-listening)) and what a web request looks like ([How a web request works](How-a-Web-Request-Works.md)). Python 3 and Nmap on your own computer for the hands-on part. About four hours for the reading and the free exercises (est.); the Greenbone and Metasploit parts are optional extras (est. a further two hours each).

## Why this page exists, in the maintainer's words

The maintainer put the goal like this (2026-10-22): "Get them thinking about cybersecurity holistically, not just as 'oh I found a local exploit on Windows'. Understand how a true enterprise infrastructure could and often should look, albeit much larger in scale. All my best pentester friends can pretty much build the things just as well as they can attack them, because they know how it works."

That is his observation, and this page is built on it. It is **not** a pentesting course. It teaches seven tools at the level where you can say what each one asks of a system, read what it answers, find that answer in the logs of the thing it touched, and turn a finding into a change. The point is to understand systems. A list of findings is a by-product; a system that is built so the finding never appears is the product. The last exercise makes that literal: you build a small system, scan it, fix it by changing the build, and scan again.

## What you will be able to do

- State the rules for using any of these tools (own it or have written permission; isolated lab; no scanning of anything shared) and say why each exists.
- Say, for Nmap, Greenbone/OpenVAS, Wireshark, Burp Suite Community Edition, OWASP ZAP and Metasploit Framework: what it is, who makes it, what question it answers for a defender, and where it sits in a whole system.
- Run a host discovery and a port scan against a target on your own computer, read the result (open, closed, filtered) and say how noisy each scan type is.
- Find the footprint of a scan and of a web scanner in a log, and write a rule that catches the first.
- Read an intercepted request and its response, and say what a replay with one change tells you.
- Say what a `check` does in Metasploit and what exploitation looks like in logs, without running one.
- Turn a finding into a fix, a ticket and a retest, and tell a false positive from a real one.
- Build a three-part toy system, scan it, fix two findings by changing the build, and show the before and after.

## Authorization and scope come first

Every tool here can be used to break the law. The short version of the rules (the full version is in the companion page [Red and blue as yin and yang, and your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md), which may not resolve until it merges; read it first when it does):

1. **Own it, or have written permission.** Scan and test only machines and networks that are yours, or where the owner has given you written permission that names what you may test, when, and from where. "It was open" and "I was only looking" are not permission. This is the same stance as [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md). The law differs by country and this page is not legal advice.
2. **Scope is a list.** Written permission names addresses and dates. Anything not on the list is out of scope, even if it is next door.
3. **The lab is isolated.** Everything on this page runs against **loopback** (`127.0.0.0/8`, addresses that never leave your computer) or a virtual machine on a **host-only or internal** virtual network. Never use a **bridged** virtual network for a deliberately vulnerable machine, because bridging puts it on your real network next to your real devices ([Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md#networking-nat-bridged-host-only) explains the network modes and how to set up a first VM). Never point any of these tools at your home or work network "to see what is there".
4. **No third parties, ever.** Not a friend's server, not a website you dislike, not an address from a search engine. No brute forcing anything that is not yours.
5. **Stop conditions.** If something unexpected answers (an address you did not start), stop and check what it is before you continue.

The addresses on this page are loopback, plus the documentation ranges `192.0.2.0/24`, `198.51.100.0/24` and `203.0.113.0/24` ([RFC 5737](https://www.rfc-editor.org/rfc/rfc5737)) which are reserved for examples and are never real hosts.

## The tools in one table

| Tool | Made by | License (what I read) | The defender's question | Runs on |
|---|---|---|---|---|
| **Nmap** | The Nmap Project (nmap.org) | Nmap Public Source License, based on GPLv2 with extra terms | What is listening on this machine, and what does it say about itself? | Linux, Windows, macOS (installers on nmap.org) |
| **Greenbone Community Edition** (the scanner is **OpenVAS**) | Greenbone | Open-source licenses (per its documentation) | Which known flaws does this machine appear to have? | Linux, usually in containers |
| **Wireshark** | The Wireshark project | Source under the GNU GPL | What actually crossed the wire? | Linux, Windows, macOS |
| **Burp Suite Community Edition** | PortSwigger | Free edition of a commercial product | What does this web app send and accept, and what happens if I change a request? | Linux, Windows, macOS (Java based) |
| **OWASP ZAP** ("ZAP by Checkmarx") | The ZAP Dev Team | Apache License 2.0 | The same, with automation built for pipelines | Linux, Windows, macOS |
| **Metasploit Framework** | Rapid7 and contributors | BSD-style license | Is this flaw real here, and what would it give an attacker? | Linux (and others); lab VM only for this page |
| **Nikto, nuclei** (short mentions) | Nikto: its author, cirt.net; nuclei: ProjectDiscovery | Not read | Does this web server have known risky files or configuration? | Linux and others |

Metasploit **Framework** is the free, open-source tool. **Metasploit Pro** is a different, commercial Rapid7 product ("for penetration testers and other security professionals. Contact Sales", while the Framework is listed "for developers and security researchers" with a Download button, on Rapid7's download page, read 2026-10-22). This page only discusses the Framework. Burp Suite **Community Edition** likewise differs from **Professional** and from **DAST** (an enterprise scanner product), and "OpenVAS" is a name that has meant different things over time: Greenbone's documentation says the Community Edition "was originally built as a community project named OpenVAS". Sources and dates are in the [claims register](#claims-register).

## Where each tool sits in the whole system

The companion page has the enterprise picture. Keep it open: [Red and blue as yin and yang, and your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md) has the reference architecture diagram and a table that maps each box to a lesson (that page is written at the same time as this one; I have not read its final headings, so I name no section; may not resolve until it merges). Use this table to place each tool on that picture and name the control that would catch or contain what it finds:

| Tool | Where it sits | What it looks at | The control that catches or contains the finding |
|---|---|---|---|
| Nmap | Outside a boundary, looking in; also inside, looking at the next zone | Which ports answer, what banner they print | **Segmentation** and default-deny firewalls ([Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md)); **logging** the connection attempts |
| Greenbone / OpenVAS | A scanner host inside the zone it checks, with credentials or without | Software versions and known flaws, by host | **Patching** ([Backups, recovery and patching](Backups-Recovery-and-Patching.md)); a ticket and a retest |
| Wireshark | On a host or a mirrored switch port, passively | Packets on one link | **Encryption in transit**; **segmentation** (the less that shares a link, the less is visible) |
| Burp CE / ZAP | Between a tester's browser and one web application | Requests, responses, cookies, parameters | **Input validation and authentication** in the app ([APIs and tokens from zero](APIs-and-Tokens-From-Zero.md)); a web application firewall in front, as a second layer; **logging** at the app |
| Metasploit | Against one confirmed-vulnerable target in a lab or an authorized test | Whether a specific flaw can be used | **Patching**, **least privilege** (what the compromised service may touch), **segmentation** (where it can go next), **backup** (recovery if it goes wrong) |

## Nmap

**What it is, who makes it.** Nmap ("Network Mapper") is a free tool from the Nmap Project that sends carefully chosen packets to a machine and reports which ports answer and, with the right options, what program and version answers. Its home is [nmap.org](https://nmap.org/). Its license is the Nmap Public Source License, which its own page describes as "based on the GNU GPLv2, but with important additional terms, conditions, clarifications and exceptions" ([nmap.org/npsl](https://nmap.org/npsl/), read 2026-10-22). The extra terms matter if you want to bundle Nmap in a product; they do not stop you from using it on your own network. I ran version 7.98.

**The question it answers for a defender.** "What can a stranger see of this machine?" That is your **attack surface**: the set of things that answer. Every open port is a program you must patch and watch. A port you did not know about is a finding in itself.

**Reading the result.** A **port scan** asks each port whether anything is there. Nmap's three main answers ([port states, as used in the earlier firewall lesson](Subnets-NAT-and-Firewalls-By-Hand.md#flip-the-board)): **open** (a program answered), **closed** (the machine replied that nothing listens), **filtered** (silence, usually a firewall dropping the packet). Scan types differ in how they ask:

| Option | Name | How it asks | Noise in the target's logs |
|---|---|---|---|
| `-sn` | Host discovery only ("ping scan") | Asks whether the host is up; no ports | Low: a few packets. On a network it is often ICMP or ARP, which most services never log |
| `-sT` | TCP connect scan | Completes a normal TCP connection to each port, then closes | **Visible**: every open port sees a full connection, and many programs log one. Needs no special privilege |
| `-sS` | SYN ("half-open") scan | Sends the first packet of the handshake and never finishes it | Lower in application logs (no completed connection), but a firewall or intrusion detection system still sees it. Needs privilege (root or administrator); not run on this page |
| `-sV` | Service and version detection | After finding an open port, sends probes and reads the reply to name the program and version | **Loud**: many connections per port. In the run below, a plain connect scan made 3 connections; `-sV --version-light` made 18; a full `-sV` made about 100 |
| `-sC` | Default scripts | Runs a set of Nmap scripts | Loud, and some scripts are intrusive. Not run here |
| `--scan-delay` | Timing | Waits between probes | Slower and quieter per minute; it changes what a rate-based rule sees |

(Sources: [the port scanning techniques page](https://nmap.org/book/man-port-scanning-techniques.html), read 2026-10-22, for the scan types; the connection counts are from this page's run.)

**What it looks like in the target's logs.** A connect scan leaves one connection line per open port. Exercise 2 shows it, and Exercise 3 writes the rule. Closed and filtered ports leave nothing in an application log, which is why a firewall log (the drops) is the better place to see a scan in a real network. The [logs lesson](Logs-SIEM-and-Detection-Basics.md) covers sources.

**Common false positives and misreads.** "Filtered" does not mean "safe": it means the probe got no answer. A "version" from `-sV` is a guess from the banner; a program that hides or fakes its banner is misnamed, and a patched program that keeps its old banner looks vulnerable. An internal scan that finds many open ports on a **flat** network is not a bug in Nmap: it is a true description of a network with no segmentation.

**From finding to fix, ticket and retest.** Finding: "TCP 18082 answers from outside the zone." Fix: bind it to an address only the app tier can reach, or firewall it. Ticket: owner, the port, the evidence (the scan output), the fix and a date. Retest: the same scan, from the same place, now shows closed or filtered. The same command is the proof, which is why you save it.

**Where it sits.** Outside and between zones; see the table above. Segmentation contains it; connection logging catches it.

## Greenbone Community Edition and OpenVAS

**What it is, who makes it.** A **vulnerability scanner** checks a machine against a large library of known flaws and reports the ones it thinks apply. **Greenbone Community Edition** is the open-source vulnerability management stack from Greenbone; its documentation says it "consists of a framework with several services", "is developed as part of the commercial Greenbone Enterprise product line" and "was originally built as a community project named OpenVAS" ([Background](https://greenbone.github.io/docs/latest/background.html), read 2026-10-22). So **OpenVAS** is the name of the scanner engine and the older name of the project, and **Greenbone** is the company and the product family. "Community" here means the free, open-source edition that is built from the same code base as the commercial Enterprise product line; this is the documentation's wording and I did not compare the editions' contents.

The documentation names three parts: scanner applications that run **vulnerability tests** (VTs) against targets, the **Greenbone Vulnerability Management Daemon (gvmd)** that stores configuration and results and controls the scanner, and the **Greenbone Security Assistant (GSA)**, the web interface.

**How it is deployed, and what it costs.** The documentation's container guide ([Greenbone Community Containers](https://greenbone.github.io/docs/latest/22.4/container/index.html), read 2026-10-22) uses Docker or Podman and Docker Compose, and lists hardware requirements: **minimum 2 CPU cores, 4 GB RAM and 20 GB storage; recommended 4 cores, 8 GB and 60 GB**. It also needs a download of the vulnerability feed on first start, which takes time and bandwidth that I did not measure. That is heavy for a laptop that is also your browser, so **this page does not ask you to run it**: reading the next paragraphs is enough, and the container guide is the optional path (Exercise 6). One thing worth noticing as a defender: the compose file on that page gives the scanner service relaxed container confinement (`seccomp=unconfined` and `apparmor=unconfined`, with a comment about raw sockets). A scanner is a privileged tool; run it in a VM that holds nothing else, and put it in the zone it is meant to check.

**The question it answers.** "Which known flaws does this machine appear to have, and how bad?" Findings carry a [CVE](Glossary.md) number when there is one and a severity score ([CVSS](Backups-Recovery-and-Patching.md#reading-a-cve-entry-and-a-severity-score)).

**Reading the output.** Per finding: the host and port, the test name, the CVE, a severity, a "quality of detection" idea (did it prove the flaw or infer it from a version?), a description and a solution. Read the severity as a start, not an order: a critical finding on a machine nothing can reach is lower priority than a medium one on your internet-facing server.

**What it looks like in the target's logs.** A credentialed scan (the scanner logs in) leaves successful sign-ins in the auth log; an unauthenticated scan looks like a very large port and service scan followed by many odd web requests. Both are loud, which is the reason to schedule them and tell the logging team: a scan that wakes the on-call engineer once is a lesson; a scan nobody knew about is a false incident.

**Common false positives.** Version-based findings on software that has been patched without a version bump (common on Linux distributions, which fix a flaw in a package without changing the upstream version number). Findings on a feature that is installed but turned off. Findings on a port that only the scanner could reach because it sat in the wrong zone.

**Finding to fix, ticket, retest.** Same loop as above, with one addition: record the **decision** for every finding that you do not fix (accepted risk, false positive, compensating control), with an owner and a review date. A scanner report is a list of questions; the decisions are the answers.

**Where it sits.** A scanner host inside the zone it checks. The control that contains what it finds is **patching** on a cadence you can state ([Backups, recovery and patching](Backups-Recovery-and-Patching.md)).

## Wireshark

**What it is.** A **packet analyzer**: it captures the packets crossing a network interface and shows them field by field. Its site calls it "the world's leading network protocol analyzer" and "free and open source", and says its source is available under the GNU General Public License ([wireshark.org](https://www.wireshark.org/), read 2026-10-22; I did not verify the "leading" claim, it is the project's own).

**The question it answers.** "What actually crossed this link?" It is the tool that settles arguments: whether a connection is encrypted, whether a name lookup went where you thought, whether the thing that "should never talk to the internet" did. Capturing needs privilege and, on a switched network, you only see traffic to and from your own machine unless the switch mirrors a port; the project's own FAQ discusses promiscuous mode and why you may not see other machines' traffic ([FAQ](https://www.wireshark.org/faq.html), read 2026-10-22).

**Reading it, in the logs, false positives, fix.** Read top to bottom: the packet list, then the one packet's layers, then the bytes. Look for plain-text credentials and tokens (a finding against whichever service sent them: encrypt it), for services you did not know about, and for traffic that crosses a boundary it should not. A capture file contains whatever was on the wire, including secrets; **treat a capture like a credential store** and delete it when you are done. Wireshark leaves no footprint on the target (it only listens). The false-positive trap is the filter: a display filter that hides a protocol hides the problem. **Where it sits:** on a host or a mirrored port; the controls are encryption in transit and segmentation. I did not run it for this page; Exercise 2 reads the same information from your own logs instead, with no capture privilege needed.

## Burp Suite Community Edition and OWASP ZAP

**What they are.** An **intercepting proxy** sits between your browser and a web application. Every request goes through it, so you can read it, pause it, change it and send it again. PortSwigger's **Burp Suite Community Edition** is the free edition of their commercial tool. PortSwigger's own comparison on its Community download page says (read 2026-10-22) that Community includes: "HTTP(s) / WebSockets proxy and history", "Essential tools - Repeater, Decoder, Sequencer, and Comparer", and "Burp Intruder (demo)". It says **Professional** adds, among other things: project files (save your work), the full Intruder, a web vulnerability scanner, a search function, Burp Collaborator (out-of-band testing) and automatic crawling. So in Community you get the manual tools and not the scanner. Its Repeater tool is "a tool that enables you to modify and send an interesting HTTP or WebSocket message over and over" ([Burp Repeater](https://portswigger.net/burp/documentation/desktop/tools/repeater), read 2026-10-22).

**OWASP ZAP** (the site now says "Zed Attack Proxy (ZAP) by Checkmarx") describes itself as "free and open source" and "an independent Open Source project"; its repository carries the Apache License 2.0 ([zaproxy.org](https://www.zaproxy.org/), [LICENSE](https://raw.githubusercontent.com/zaproxy/zaproxy/main/LICENSE), read 2026-10-22). Unlike Burp Community it includes automated scanning, and its documentation covers an Automation Framework for running it from a pipeline (the documentation's table of contents lists "Automation Framework"; I did not read that section). **Is it used in this repository?** I searched this repository's workflows and documentation for ZAP and DAST on 2026-10-22 and found no use, so this page does not claim one. The maintainer's other repositories were not searched.

**The question they answer.** "What does this web application send and accept, and what happens when I change a request?" For a defender that translates into: are my authentication, authorization and input checks really enforced on the server, or only in the page's JavaScript?

**Reading an intercepted request.** The method and path say what is asked; the headers say who is asking (`User-Agent`, `Cookie`, `Authorization`); the body carries parameters. In the response, read the status code, the `Server` header (does it tell the world the product and version?), cookie flags and what the body discloses. [How a web request works](How-a-Web-Request-Works.md) and [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) teach each part. Exercise 4 does this with a small proxy you can read in full, so you see the idea before you learn a big tool.

**The "Repeater" idea, and "Intruder" only as a concept.** Repeater resends one request with one change: a different path, a different ID, a missing cookie. If the server answers with someone else's data, the flaw is in the server's **authorization**, and the fix is a check on the server. Intruder automates many variants of one request. On this page it is a concept only: automating guesses against anything you do not own is brute forcing, and the Community Edition's Intruder is a limited demo anyway, according to PortSwigger's comparison.

**What it looks like in the target's logs.** A person using a proxy looks like a person. A scanner (ZAP's active scan, or Nikto, or nuclei) looks like hundreds of requests for paths no real user asks for, in seconds, from one address, mostly `404`s, with odd or default `User-Agent` strings and odd characters in parameters. Exercise 3 builds a small version of that footprint and counts it.

**Common false positives.** A scanner reports a missing security header or a version string and calls it high severity; both are real but small. Reflected-input warnings on a field that is encoded on output. A login page that returns `200` for a failure, which a naive scanner reads as a success. **Fix, ticket, retest:** change the code or the configuration; the ticket holds the request that shows the problem; the retest is the same request, now refused or harmless.

**Nikto and nuclei, in one paragraph.** Nikto is a web server scanner (its repository's README calls it "Nikto web server scanner", with documentation linked from [cirt.net/Nikto2](https://cirt.net/Nikto2)). nuclei is, in its README's words, "a modern, high-performance vulnerability scanner that leverages simple YAML-based templates" ([ProjectDiscovery nuclei](https://github.com/projectdiscovery/nuclei), read 2026-10-22). Both ask "does this server expose known risky files or configurations?" and both are loud in a web log in the way just described. I did not run either or read their licenses.

**Where they sit.** Between one tester's browser and one app. The controls that matter are the application's own: authentication, server-side authorization and input handling, with a web application firewall and request logging as extra layers.

## Metasploit Framework (know what it is, and stop there)

**What it is.** The **Metasploit Framework** is an **exploit framework**: a library of modules (checks, exploits, payloads and helper tools) and a console, `msfconsole`, for running them. The Framework's repository says it "is an open-source tool released under a BSD-style license", with copyright held by Rapid7 ([GitHub README](https://github.com/rapid7/metasploit-framework) and [COPYING](https://raw.githubusercontent.com/rapid7/metasploit-framework/master/COPYING), read 2026-10-22). **Metasploit Pro** is the separate commercial product described above. The project's documentation lives at [docs.metasploit.com](https://docs.metasploit.com/).

**The question it answers.** "Is this flaw real on this machine, and what would it give an attacker?" For a defender its value is evidence: a scanner says "appears vulnerable", an exploit proves it, which is how a lab proves that a fix works. It is also what a real attacker may run, so what it looks like in your logs is worth knowing.

**`check`, and what its answers mean.** Exploit and auxiliary modules can support a `check` command that, in the documentation's words, lets "the user ... determine the vulnerable state before using the module", "without actually popping a shell". The documentation lists the possible results ([How to write a check method](https://docs.metasploit.com/docs/development/developing-modules/guides/how-to-write-a-check-method.html), read 2026-10-22): **Unknown** (not enough information, such as a timeout), **Safe** (the check did not trigger the flaw or detect the service), **Detected** (the service is there but the check cannot tell whether it is vulnerable), **Appears** (judged from passive information such as a version or banner), **Vulnerable** (the check obtained hard evidence) and **Unsupported** (the module has no check). Note the same page says the Framework "isn't a vulnerability scanner like Nexpose" (a Rapid7 scanner product); `check` is a courtesy, not a promise, and **Vulnerable can be aggressive**, since it proves the flaw by using it. That is why `check` is run only against a lab machine you own.

**What exploitation looks like in logs, and the defender's takeaway.** You do not need to run one to know the shape: a short burst of unusual requests or connections to one service; the service logging an error or a restart; then a **new outbound connection from a server that never normally makes one**, a new process, a new account or a changed file. Those are the four lines to alert on: the **unexpected outbound connection**, the **unexpected child process**, the **service crash or restart**, and the **new account or persistence**. The fixes are what the earlier lessons teach: patch (the exploit needs a flaw to use), **least privilege** (a compromised service that runs as a plain user and can touch only its own folder gives away much less), **segmentation** (the compromised machine cannot reach the next one) and **egress filtering** (the server cannot dial out), plus tested backups for recovery. See [Threats in plain words](Threats-in-Plain-Words.md) for the vocabulary and [Backups, recovery and patching](Backups-Recovery-and-Patching.md).

**This page does not teach you to exploit anything.** Exercise 7 shows the console commands to start it, search for a module and read its metadata, and stops before you set a target. No exploit code, no payload and no attack chain appear here.

## Attack surface, in one table

The earlier lessons can be read as a list of ways to make this table smaller. (A fuller attack-surface lesson, with an inventory of this project, is [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md); this is the small table that came first.)

| What an outsider can reach | Tool that finds it | The build choice that shrinks it |
|---|---|---|
| Open ports and their banners | Nmap | Bind services to the narrowest address; default-deny firewall; segmentation |
| Known-vulnerable software | Greenbone, Nmap `-sV` | Patch cadence; fewer packages; minimal images |
| Web paths that should not exist (`/admin/`, backups, debug pages) | ZAP, Burp, Nikto, nuclei | Do not ship debug endpoints; deny by default at the proxy |
| Headers and error pages that name the product and version | Nmap, Burp, ZAP | Configure the server to say less; remember this only slows an attacker |
| Plain-text credentials on the wire | Wireshark | Encrypt in transit |
| Over-privileged services | Metasploit (shows the consequence) | Least privilege; no shared accounts |

## Free path: a lab on your own computer

Everything here runs on loopback with a toy system you build from a script on this page. Nothing leaves your computer and nothing is a real product. The reading and the exercises are free and always will be. Every exercise has **Predict**, **Do**, **Check** and **Undo**. Python scripts run the same on Windows, where you type `python` instead of `python3`; the PowerShell commands are **est.** (never run).

**Install.** Nmap from [nmap.org](https://nmap.org/download) (on Debian-based Linux `sudo apt install nmap` works; est. for other systems). Python 3 from your system or python.org. `curl` is on most Linux and macOS machines and, as `curl.exe`, on current Windows 10 and 11 (est.). If you do not want to install Nmap, the reading still works.

### The lab: three toy parts on loopback

Save these three files in an empty folder called `tools-lab`. `lab.py` is the toy system: a web front end, an app and a database, each a small listener that writes a log line for every connection and every web request. By default it is built **badly on purpose**: all three parts sit on one address, the web server announces its product and version, and an `/admin/` debug page leaks a database address. `--fixed` builds the repaired version.

```python
#!/usr/bin/env python3
# lab.py - a toy three-part system (web front end, app, database) on LOOPBACK ONLY.
# Nothing here is a real product. Every address is 127.x.x.x, so nothing leaves your computer.
# Default build: all three parts share one address (a "flat network") and leak details on purpose.
# --fixed build: the app and database move to their own loopback addresses and the leaks are removed.
import argparse
import datetime
import socketserver
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()
STATE = {"log": "lab.log", "fixed": False, "base": 18080}


def log(*fields):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with LOCK, open(STATE["log"], "a", encoding="utf-8") as fh:
        fh.write(" ".join([stamp, *map(str, fields)]) + "\n")


class Handler(BaseHTTPRequestHandler):
    role = "web"

    def version_string(self):
        return "web" if STATE["fixed"] else "LabHTTP/1.0 build-2019-01"

    def log_message(self, *args):
        pass  # we write our own log lines

    def do_GET(self):
        code, body = 404, b"not found\n"
        if self.path in ("/", "/index.html"):
            code, body = 200, b"hello from the lab " + self.role.encode() + b"\n"
        elif self.path.startswith("/admin") and not STATE["fixed"]:
            code, body = 200, b"debug page: db=127.0.0.1 user=lab_reader\n"
        agent = (self.headers.get("User-Agent") or "-").replace('"', "'")[:100]
        log("REQ", self.role, "src=" + self.client_address[0], "dport=" + str(self.server.server_address[1]),
            self.command, self.path[:100], code, 'ua="' + agent + '"')
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class DbHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.sendall(b"LABDB 5.5.0 ready\r\n")  # then the connection closes


class Mixin:
    daemon_threads = True
    allow_reuse_address = True
    role = "web"

    def get_request(self):
        conn, addr = super().get_request()
        log("CONN", self.role, "src=" + addr[0], "dport=" + str(self.server_address[1]))
        return conn, addr


class Web(Mixin, ThreadingHTTPServer):
    pass


class Db(Mixin, socketserver.ThreadingTCPServer):
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixed", action="store_true")
    ap.add_argument("--base-port", type=int, default=18080)
    ap.add_argument("--log", default="lab.log")
    a = ap.parse_args()
    STATE.update(log=a.log, fixed=a.fixed, base=a.base_port)
    app_ip, db_ip = ("127.0.0.2", "127.0.0.3") if a.fixed else ("127.0.0.1", "127.0.0.1")
    parts = []
    for role, ip, port, srv, handler in (
        ("web", "127.0.0.1", a.base_port, Web, Handler),
        ("app", app_ip, a.base_port + 1, Web, type("App", (Handler,), {"role": "app"})),
        ("db", db_ip, a.base_port + 2, Db, DbHandler),
    ):
        s = srv((ip, port), handler)
        s.role = role
        parts.append(s)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        print(f"{role} listening on {ip}:{port}", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
```

`scan_detect.py` is a toy detector for the log lesson's idea: alert when one source touches several different ports in a short window.

```python
#!/usr/bin/env python3
# scan_detect.py LOGFILE WINDOW_SECONDS MIN_PORTS - a toy detector for the logs lesson's idea.
# Alerts when one source address connects to MIN_PORTS or more different ports within WINDOW_SECONDS.
# Reads lab.log CONN lines only. Lines it cannot parse are counted and skipped, never run.
import datetime
import sys

path, window, need = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
seen, bad, alerted = {}, 0, set()
for line in open(path, encoding="utf-8", errors="replace"):
    parts = line.split()
    if len(parts) < 5 or parts[1] != "CONN":
        continue
    try:
        when = datetime.datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%SZ")
        src = parts[3].split("=", 1)[1]
        port = int(parts[4].split("=", 1)[1])
    except (ValueError, IndexError):
        bad += 1
        continue
    hits = seen.setdefault(src, [])
    hits.append((when, port))
    hits[:] = [(t, p) for t, p in hits if (when - t).total_seconds() <= window]
    ports = {p for _, p in hits}
    if len(ports) >= need and src not in alerted:
        alerted.add(src)
        print(f"ALERT port_scan src={src} ports={len(ports)} window={window}s at={parts[0]}")
print(f"skipped {bad} unparseable lines", file=sys.stderr)
```

`proxy.py` is a toy intercepting proxy for Exercise 4. It only forwards plain `http://` requests to loopback addresses and refuses everything else.

```python
#!/usr/bin/env python3
# proxy.py - a toy intercepting proxy: prints each request and response, then passes them on.
# It forwards plain http:// requests to LOOPBACK addresses only and refuses everything else.
import http.client
import ipaddress
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Proxy(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        try:
            port = url.port or 80          # raises ValueError for a bad or out-of-range port
            ok = url.scheme == "http" and ipaddress.ip_address(url.hostname).is_loopback
        except ValueError:
            ok = False
        if not ok:
            self.send_error(403, "this toy proxy only forwards http:// to loopback addresses")
            return
        print(f">>> {self.command} {self.path}", flush=True)
        for k, v in self.headers.items():
            print(f">>> {k}: {v}", flush=True)
        conn = http.client.HTTPConnection(url.hostname, port, timeout=10)
        conn.request("GET", (url.path or "/") + ("?" + url.query if url.query else ""),
                     headers={k: v for k, v in self.headers.items() if k.lower() != "proxy-connection"})
        resp = conn.getresponse()
        body = resp.read(65536)
        print(f"<<< {resp.status} {resp.reason}", flush=True)
        for k, v in resp.getheaders():
            print(f"<<< {k}: {v}", flush=True)
        print(f"<<< body: {body[:80]!r}", flush=True)
        self.send_response(resp.status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        conn.close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18888
    ThreadingHTTPServer(("127.0.0.1", port), Proxy).serve_forever()
```

Why loopback is safe: addresses in `127.0.0.0/8` are delivered inside your own machine and never sent to a network. `127.0.0.2` and `127.0.0.3` work on Linux and Windows without setup (est. for Windows); macOS does not answer on them by default (est.), so on a Mac use a Linux virtual machine on a host-only network.

### Exercise 1: start the lab, and prove it is private

**Predict.** After starting `lab.py`, the three parts listen on ports 18080, 18081 and 18082. On which address? Could another computer on your network connect?

**Do (Bash).** In one terminal:

```bash
mkdir -p ~/tools-lab && cd ~/tools-lab
python3 -I lab.py
```

In a second terminal in the same folder:

```bash
ss -ltn | grep -E ':1808[0-2] '
```

**Do (PowerShell, est.).**

```powershell
New-Item -ItemType Directory -Force $HOME\tools-lab | Out-Null
Set-Location $HOME\tools-lab
python -I lab.py
# in a second window:
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 18080..18082 } | Format-Table LocalAddress, LocalPort
```

**Check.** The first terminal prints `web listening on 127.0.0.1:18080`, then the app and db lines. The second prints three lines with `127.0.0.1` as the local address:

```text
LISTEN 0      5          127.0.0.1:18082      0.0.0.0:*
LISTEN 0      5          127.0.0.1:18080      0.0.0.0:*
LISTEN 0      5          127.0.0.1:18081      0.0.0.0:*
```

`127.0.0.1` means only this machine; a line that said `0.0.0.0` would mean every network interface, and you would stop and fix that first. This check is a habit: **before you scan or test anything, prove where it listens.**

**Undo.** Leave the lab running for the next exercises. Stop it with Ctrl-C when you finish.

### Exercise 2: discover, scan, and read your own log

**Predict.** Write down: how many ports will Nmap report open among 18080 to 18082? How many connection lines will each of these leave in `lab.log`: a connect scan; the same with `--version-light` service detection?

**Do (Bash).** In the second terminal:

```bash
: > lab.log
nmap -sn 127.0.0.1
nmap -sT -p 18080-18082 127.0.0.1
cat lab.log
: > lab.log
nmap -sT -sV --version-light -p 18080-18082 127.0.0.1 | grep -v '^SF'
wc -l lab.log
```

**Do (PowerShell, est.).** Use the same `nmap` commands. Replace `: > lab.log` with `Clear-Content lab.log`, `cat lab.log` with `Get-Content lab.log`, `grep -v '^SF'` with `Select-String -NotMatch '^SF'` and `wc -l lab.log` with `(Get-Content lab.log).Count`. (On Windows, Nmap's `-sT` is the safe choice; the packet-level scan types need the Npcap driver, which this page does not install.)

**Check.** Output of the run on 2026-10-22, trimmed:

```text
Nmap scan report for localhost (127.0.0.1)
Host is up (0.000028s latency).
Nmap done: 1 IP address (1 host up) scanned in 0.00 seconds

PORT      STATE SERVICE
18080/tcp open  unknown
18081/tcp open  unknown
18082/tcp open  unknown

2026-10-22T19:54:48Z CONN web src=127.0.0.1 dport=18080
2026-10-22T19:54:48Z CONN db src=127.0.0.1 dport=18082
2026-10-22T19:54:48Z CONN app src=127.0.0.1 dport=18081
```

and for the second scan, the service column still says `unknown`, Nmap prints "3 services unrecognized despite returning data" and `wc -l` says `18`. Read it:

- The host is "up" (discovery), and all three ports are **open**. That is the finding: from the point of view of the scanner, the app and the database are as reachable as the web server. On a real flat network that is exactly what an intruder who gets onto it would see.
- The plain scan left **3** connection lines, one per open port, in a few milliseconds from one source. The version scan left **18**, six per port, as Nmap probed for a name. A full `-sV` (without `--version-light`) took 87 seconds and left about 100 lines in the one run I timed. Noise is a choice, and a defender can count it.
- Nmap did not name the programs, because they are toys with unusual banners. Real services usually get named; here the **banner** is what leaks. The fingerprint that Nmap prints contains the line `Server: LabHTTP/1.0 build-2019-01`. Anyone who can scan can read it.
- The services are called `unknown`, not "safe". Absence of a name is not absence of a risk.

**Undo.** `: > lab.log` empties the log (the lab file only).

### Exercise 3: catch a scan, evade it, defend

**Predict.** A rule says: alert when one source touches three or more different ports within 10 seconds. Will it fire on the plain scan? On a scan made slow with `--scan-delay 6s`? If you widen the window to 60 seconds?

**Do (Bash).**

```bash
: > lab.log
nmap -sT -p 18080-18082 127.0.0.1 > /dev/null
python3 -I scan_detect.py lab.log 10 3
: > lab.log
nmap -sT -p 18080-18082 --scan-delay 6s 127.0.0.1 > /dev/null
cat lab.log
python3 -I scan_detect.py lab.log 10 3
python3 -I scan_detect.py lab.log 60 3
```

**Do (PowerShell, est.).** `nmap ... | Out-Null`; `Clear-Content lab.log`; `Get-Content lab.log`; `python -I scan_detect.py lab.log 10 3`.

**Check.**

```text
skipped 0 unparseable lines
ALERT port_scan src=127.0.0.1 ports=3 window=10s at=2026-10-22T19:54:48Z
---- slow scan ----
2026-10-22T19:55:01Z CONN web src=127.0.0.1 dport=18080
2026-10-22T19:55:07Z CONN db src=127.0.0.1 dport=18082
2026-10-22T19:55:13Z CONN app src=127.0.0.1 dport=18081
skipped 0 unparseable lines                     <- window 10: no alert
skipped 0 unparseable lines
ALERT port_scan src=127.0.0.1 ports=3 window=60s at=2026-10-22T19:55:13Z
```

(The `---- slow scan ----` line is added here to separate the runs; the script does not print it.) The scan took 24 seconds. The first rule catches the fast scan; the slow scan stays under it because six seconds between probes puts at most two ports in any ten-second window. Widening the window to 60 seconds catches it, at the price a wider window always has: more normal activity (a monitoring check, a health probe) looks like a scan too. The same trade-off is in the [failed-login loop](Logs-SIEM-and-Detection-Basics.md#build-break-detect-evade-defend-the-local-loop). This is described so you recognize it; do not slow-scan anything that is not yours.

**Undo.** `: > lab.log`.

### Exercise 3b: what a web scanner leaves

A web scanner asks for many paths that real users do not. Send six of them to your own lab with a made-up `User-Agent`, then count the `404`s.

**Predict.** How many of the six paths exist? What will the log show as the `User-Agent`, and how long will the whole burst take?

**Do (Bash).**

```bash
: > lab.log
for p in /.env /wp-login.php /phpmyadmin/ /cgi-bin/test /backup.zip /admin/; do
  curl -s -o /dev/null -A "scanner-demo/0.1" -w "$p %{http_code}\n" http://127.0.0.1:18080$p
done
grep ' REQ ' lab.log | awk '$8==404{n[$4]++} END{for(s in n) print s, n[s], "x 404"}'
```

**Do (PowerShell, est.).**

```powershell
Clear-Content lab.log
foreach ($p in '/.env','/wp-login.php','/phpmyadmin/','/cgi-bin/test','/backup.zip','/admin/') {
  curl.exe -s -o NUL -A "scanner-demo/0.1" -w "$p %{http_code}`n" "http://127.0.0.1:18080$p"
}
(Select-String -Path lab.log -Pattern ' REQ .* 404 ').Count
```

**Check.**

```text
/.env 404
/wp-login.php 404
/phpmyadmin/ 404
/cgi-bin/test 404
/backup.zip 404
/admin/ 200
127.0.0.1 5 x 404
```

Five misses and one hit in under a second from one source with an odd agent: that shape is a content-discovery scan. The `200` for `/admin/` is the finding: the debug page exists. A rule counting `404`s per source per minute catches the scan; a human who types a wrong address makes one. **False positive:** a link checker or a broken bookmark makes the same `404`s, so a rule needs a threshold and a look at the `User-Agent` and the paths. 

**Undo.** `: > lab.log`.

### Exercise 4: read an intercepted request, and replay one change

**Predict.** Through a proxy, `curl` sends the same request your browser would. Which headers will the proxy print on the way in? What will the `Server` header in the answer tell you?

**Do (Bash).** Start the proxy in a third terminal, then use it from the second:

```bash
python3 -I proxy.py 18888
```

```bash
curl -s --proxy http://127.0.0.1:18888 http://127.0.0.1:18080/
curl -s --proxy http://127.0.0.1:18888 http://127.0.0.1:18080/admin/
curl -s -o /dev/null -w "%{http_code}\n" --proxy http://127.0.0.1:18888 http://203.0.113.9/
```

**Do (PowerShell, est.).** The same commands with `curl.exe`, and `python -I proxy.py 18888`.

**Check.** The proxy terminal prints, trimmed:

```text
>>> GET http://127.0.0.1:18080/admin/
>>> Host: 127.0.0.1:18080
>>> User-Agent: curl/8.21.0
>>> Accept: */*
>>> Proxy-Connection: Keep-Alive
<<< 200 OK
<<< Server: LabHTTP/1.0 build-2019-01
<<< Content-Length: 41
<<< body: b'debug page: db=127.0.0.1 user=lab_reader\n'
```

The first curl prints `hello from the lab web`, the second prints the debug line, and the third prints `403` and nothing is forwarded, since `203.0.113.9` is not loopback (the toy proxy refuses; in a real tool the scope setting does that job, so set it first). Read what is there: `>>>` is the request (method, full address, who asked, what formats are accepted) and `<<<` the response (status, product and version, length, the first bytes of the body). The `Server` header discloses the product and a build date. The second request is the **Repeater** idea done by hand: one request, one change in the path (`/` to `/admin/`), and the answer changes from a greeting to something that should not be public. Your lab log has both requests, as the target sees them:

```text
2026-10-22T19:55:14Z REQ web src=127.0.0.1 dport=18080 GET / 200 ua="curl/8.21.0"
2026-10-22T19:55:14Z REQ web src=127.0.0.1 dport=18080 GET /admin/ 200 ua="curl/8.21.0"
```

**With Burp Suite Community Edition or ZAP (not run).** Install one from its own site, start it, and in its proxy settings note the address it listens on (see the PortSwigger step "Intercepting HTTP traffic with Burp Proxy" in their [getting started guide](https://portswigger.net/burp/documentation/desktop/getting-started/intercepting-http-traffic), read 2026-10-22). Point your own browser at it, browse to `http://127.0.0.1:18080/`, and read the same fields in the proxy's history. For `https://` sites the tool presents its own certificate, which your browser rejects until you install the tool's certificate authority **in a throwaway browser profile**; never install it in your everyday browser. Keep the tool's scope set to `127.0.0.1` only and do not use its scanner (ZAP) or Intruder against anything else.

**Undo.** Ctrl-C the proxy.

### Exercise 5: Wireshark on loopback (optional, not run)

**Predict.** On loopback, the lab's plain-text traffic is fully readable. **Do (est.).** Install Wireshark from wireshark.org, choose the loopback interface, use the display filter `tcp.port == 18080`, run Exercise 4's first `curl` without the proxy, and open one packet. **Check.** You see the request line and headers as plain text, which is why unencrypted web traffic on a shared network is a finding. **Undo.** Close and delete the capture file.

### Exercise 6: Greenbone, read-only (optional, heavy, not run)

**Predict.** Before you open the guide, guess how much memory a vulnerability scanner stack needs, and whether it can share a laptop with your browser.

**Do (Bash and PowerShell: reading only).** Read the [Greenbone Community Containers](https://greenbone.github.io/docs/latest/22.4/container/index.html) guide start to finish and write a short note with these answers: the minimum and recommended cores, RAM and disk; what must be installed first; and which service has its confinement turned off, and what you would wall around it. No command is needed. If you decide to run it, do it in a virtual machine on a host-only network, against a lab VM you built, never against a real network. Cost: the software is free; the machine is yours or your provider's bill (est.; read [the project's cost explanation](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) before you rent one).

**Check.** On 2026-10-22 the guide listed a minimum of 2 cores, 4 GB RAM and 20 GB storage and a recommendation of 4 cores, 8 GB and 60 GB; it needs Docker or Podman and Docker Compose; and its compose file sets `seccomp=unconfined` and `apparmor=unconfined` on the scanner service. If your note differs, the guide has changed; trust the guide.

**Undo.** Nothing was installed.

### Exercise 7: Metasploit, console only (optional, not run, lab VM only)

**Predict.** If you search for a module and print its `info`, does anything get sent to a target? (It does not; no target is set.)

**Do (Linux VM only; no PowerShell equivalent).** Install the Framework from [docs.metasploit.com](https://docs.metasploit.com/) in a **Linux virtual machine** on a host-only network with nothing else running. These commands only read:

```text
msfconsole -q
msf6 > search type:auxiliary name:http_version
msf6 > info auxiliary/scanner/http/http_version
msf6 > exit
```

(The module name is an example from memory and an **est.**; if `search` returns nothing, search for any module whose name contains `http`.)

**Check.** `info` prints the module's description, the options it needs, its references (CVE numbers when they exist) and its rank. Read them, then close the console. Do **not** run `exploit`, `run` or `check` against anything outside a throwaway VM that you built for this, and set no target on this page's lab. If you later run `check` against your own lab VM, you will get one of the codes in the table above; read it as "what a scanner would say", not as proof of safety.

**Undo.** `exit`, and delete the VM.

### Exercise 8: build it, then scan it

This is the exercise the page was written for. You will treat `lab.py` as a small system you built, scan it, read what the scan says, repair **two findings by changing the build**, and scan again. You do not change the scanner or hide the output.

**Predict.** Fill in the "before" column of the table from what you have seen: which ports are open from the front-end address, what the `Server` header says, whether `/admin/` answers. Then predict which two changes in the build would fix the most.

**Do (Bash).** With the default lab still running, in the second terminal:

```bash
nmap -sT --version-light -p 18080-18082 127.0.0.1 | grep -v '^SF' | sed -n 5,9p
curl -s -D - -o /dev/null http://127.0.0.1:18080/ | head -2
curl -s -o /dev/null -w "admin %{http_code}\n" http://127.0.0.1:18080/admin/
```

Stop the lab (Ctrl-C), then start the repaired build and scan again:

```bash
python3 -I lab.py --fixed
```

```bash
nmap -sT --version-light -p 18080-18082 127.0.0.1 | grep -v '^SF' | sed -n 5,9p
curl -s -D - -o /dev/null http://127.0.0.1:18080/ | head -2
curl -s -o /dev/null -w "admin %{http_code}\n" http://127.0.0.1:18080/admin/
nmap -sT -p 18081 127.0.0.2 | sed -n 5,6p
```

**Do (PowerShell, est.).** `python -I lab.py --fixed`; the same `nmap` and `curl.exe` commands; `Select-Object -Skip 4 -First 5` instead of `sed -n 5,9p`.

**Check.** Before and after, from the run on 2026-10-22:

| What the scan reports | Before (default build) | After (`--fixed`) | Which change fixed it |
|---|---|---|---|
| Ports open at the front-end address `127.0.0.1` | 18080, 18081, 18082 (web, app, db) | 18080 only; 18081 and 18082 are `closed` | **Segmentation.** The app moved to `127.0.0.2` and the database to `127.0.0.3`, so they no longer answer on the front end's address. Scanning `127.0.0.2` port 18081 from the inside still shows it open, which is right: the app tier must reach it |
| `Server` header | `LabHTTP/1.0 build-2019-01` | `web` | **Say less.** The server stops announcing product and build. A small win: it slows reconnaissance and tells a scanner nothing to match, but a determined attacker does not depend on it |
| `GET /admin/` | `200` with a database address | `404` | **Remove what should not ship.** The debug page is gone from the build |

You fixed three things; the exercise asked for two. Two are enough to learn the lesson (segmentation and removing the debug page); the header change shows the third kind, the cosmetic one, which is worth separating from the first two: no amount of hiding the version makes an unpatched service safe.

Notice what you did not do. You did not tell the scanner to stop looking, you did not add the fix to the scanner's ignore list, and you did not rename the finding. The build changed, and the same scan, from the same place, is the proof. That is the loop from the finding section: **finding, fix, ticket, retest.**

**What this toy leaves out, honestly.** Separate loopback addresses are a model of separate networks; they are not a real firewall, and nothing here proves a real network is segmented. The toy parts do not talk to each other. A real build would put each part in its own container or virtual machine on its own isolated network (a Docker or Podman network created with the internal option, or host-only virtual networks), with firewall rules between them; [Containers and Docker basics](Containers-and-Docker-Basics.md) and [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) cover that, and I did not run a container version for this page. If you build one, keep every published port bound to `127.0.0.1` (OWASP Juice Shop's own README shows `docker run --rm -p 127.0.0.1:3000:3000 bkimminich/juice-shop`, read 2026-10-22, which publishes the port on loopback only), never mount the Docker socket, and scan only the loopback side.

**Undo.** Ctrl-C the lab; delete the `tools-lab` folder if you like.

### A deliberately vulnerable target, if you want a bigger one

Two projects exist to be attacked in a lab. **OWASP Juice Shop** describes itself as "probably the most modern and sophisticated insecure web application", usable "in security trainings, awareness demos, CTFs and as a guinea pig for security tools", and ships a container; its README's run command binds the port to loopback ([README](https://raw.githubusercontent.com/juice-shop/juice-shop/master/README.md), read 2026-10-22). **DVWA** (Damn Vulnerable Web Application) carries this warning in its README: "Damn Vulnerable Web Application is damn vulnerable! Do not upload it to your hosting provider's public html folder or any Internet facing servers, as they will be compromised." It recommends a virtual machine "set to NAT networking mode" ([README](https://raw.githubusercontent.com/digininja/DVWA/master/README.md), read 2026-10-22). Both are fine targets for Exercise 4 with Burp or ZAP, on loopback or in a VM on a host-only network. I did not run either. I did not read the pages for Metasploitable, so I do not recommend it here.

## Threat model of the lab itself

Why the lab must be isolated, in the same shape as [Threat model](Threat-Model.md):

| Asset | Threat | Likelier cause | Control on this page | Residual risk |
|---|---|---|---|---|
| Your real network and devices | A scanner or vulnerable app is reachable from them (bridged networking, `0.0.0.0` binding) | Convenience | Loopback or host-only only; Exercise 1 proves where it listens | A typo in a bind address; re-run the check |
| Other people's systems | You scan something that is not yours | Wrong target, copy-pasted command | Loopback and documentation addresses in every command; the toy proxy refuses non-loopback targets | Your own commands edited later |
| Your everyday browser and accounts | An intercepting proxy's certificate authority is trusted by the browser you use for banking | Installing it in your main profile | Throwaway profile (Exercise 4) | You forget to remove it |
| Your secrets | A packet capture or scan report holds credentials and system detail | Saving files "for later" | Treat them as credentials; delete when done | Backups that copy them |
| Your computer | The vulnerable app is compromised and used as a foothold | Exposing it | Loopback only; no Docker socket; a VM for anything heavy | A kernel or hypervisor flaw (low, not zero) |
| Your reputation and record | Unauthorized scanning is reported or prosecuted | Ignoring the rules above | Written scope; the authorization section | Law differs by country |

## What this tells you about building systems

- **Least privilege.** A service that can be reached by fewer things, and can touch less, turns an exploit into an inconvenience. In Exercise 8 the database stopped answering on the front end's address.
- **Patch cadence.** A scanner is a patch list in disguise. If you cannot say how often you patch, a scan tells you how late you are.
- **Segmentation.** Every tool above finds more on a flat network. Zones, default-deny and a small number of deliberate holes are the fix ([Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md)).
- **Logging.** A scan is only noise if no one reads the log. Connection and request logs, shipped off the machine, are what make Exercises 2 and 3 possible ([Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md)).
- **Secure defaults.** A product that ships a debug page, a default password or a revealing banner pushes work onto every user. Ship the safe configuration.
- **Evidence, not hope.** The same scan before and after is how a change becomes a fact.

## Build, break, detect, evade, defend (the local loop)

The same loop the rest of the project uses ([Why this exists](Why-This-Exists.md)), on the toy system, with no real target.

**Build.** The toy system from `lab.py`, and a rule from `scan_detect.py`: three ports in ten seconds.

**Break.** Scan it from the front end's address (Exercise 2). All three ports are open: the build has no segmentation.

**Detect.** The rule fires on the fast scan (Exercise 3), and the web-scanner footprint of five `404`s in a second is visible in the request log.

**Evade.** A patient visitor spaces probes out (`--scan-delay 6s`) and stays under the 10-second window. It is described so that you recognize it, not so you can use it on anything you do not own.

**Defend.** Widen the window and add a second rule that fails differently (count `404`s per source), and change the build: segmentation, no debug page, less banner (Exercise 8). Then the scan finds one port instead of three. Back the rules with a person who knows what to do when they fire.

**Undo.** Stop the lab, empty `lab.log`.

### Flip the board

**The attacker.** You were given written permission to test a lab like this one. List three things you would try first that the defender's rules above would miss, and for each the extra signal that would catch it. Answers below.

<details>
<summary>What to find</summary>

1. **Spread the scan across time** (the slow scan): a defender counts ports per source over hours, not seconds.
2. **Spread it across sources** (many addresses, one probe each): a defender counts hits per destination port, or per target, not only per source.
3. **Skip the scan** and use knowledge of the product: if the banner told you the product and build, you can go straight to a known flaw. The defender's signal is a single request for an unusual path; the fix is a patched build and less banner.

</details>

**The reviewer.** A teammate proposes: "Run a full Greenbone scan of the production network every night at midnight; it finds everything." Find at least four problems.

<details>
<summary>What to find</summary>

1. **Authorization and notice.** Who agreed, and does the on-call team know? A scan nobody expected looks like an attack.
2. **Load.** Scans can slow or crash fragile services. Night is when backups run.
3. **No owner for the output.** A report nobody reads is noise; each finding needs an owner, a ticket and a retest.
4. **"Finds everything" is false.** A scanner finds known flaws it has tests for, on what it can reach, with the access it was given. Logic flaws and unknown flaws are not in its feed.
5. **Scanner placement.** From one place it sees one view. A scan from the wrong zone misses internal-only flaws or reports ones that do not matter.
6. **Scanner security.** The scanner holds credentials and runs with relaxed confinement; it is itself a target.

</details>

## Checkpoint

- What are the five rules before any scan, and which one is broken by a bridged lab VM?
- What is the difference between Greenbone, OpenVAS and Metasploit Pro, and which of the tools here has a paid sibling with more features?
- What did the connect scan leave in the log, and why did `-sV` leave more?
- What does "filtered" mean, and what does it not mean?
- What does Burp Community include that is useful for learning, and what does it leave to Professional?
- What are the six `check` results in Metasploit, and which one can be aggressive?
- Name two fixes in Exercise 8 and the control each one is an example of.
- A teammate says "the scan was clean, so we are secure". What three questions do you ask? (What did it reach? What can it not test? When did you last act on a finding?)

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| `nmap` shows everything `filtered` or nothing | Wrong address, or a firewall on the host | Run Exercise 1's `ss` check first and scan the address it shows |
| `scan_detect.py` prints nothing | The log is empty, or the window is too small for a slow scan | `cat lab.log`; widen the window |
| `-sV` takes minutes | Full intensity on unrecognized services | Add `--version-light`, or skip `-sV` |
| `address already in use` starting the lab | The first copy is still running | Stop it with Ctrl-C before starting `--fixed` |
| `127.0.0.2` does not answer | macOS, or a firewall that blocks it | Use a Linux VM on a host-only network |
| The browser refuses the proxy's certificate | Normal for `https://` through an intercepting proxy | Use the throwaway profile, or test the plain `http://` lab address |
| Scanner reports a "vulnerability" you patched | Version-based detection against an unchanged version string | Check the vendor's advisory for backported fixes before reacting |

## Claims register

All read-only requests; retrieved 2026-10-22. "Observed" means I ran it that day.

| Claim | Source | Status |
|---|---|---|
| Nmap is distributed under the Nmap Public Source License, based on GPLv2 with additional terms, conditions, clarifications and exceptions | [nmap.org/npsl](https://nmap.org/npsl/) | Read |
| Nmap scan types (`-sT`, `-sS`, `-sn`, `-sV`) behave as described | [Port scanning techniques](https://nmap.org/book/man-port-scanning-techniques.html) | Page retrieved; the table is my summary and **est.** in detail. The connect scan and `--version-light` behavior were observed |
| The scan and log output, the 3 / 18 / about 100 connection counts, the 87 second full `-sV`, the 24 second slow scan | Run with Nmap 7.98, Python 3.13.5, curl 8.21.0 | Observed once; counts and times vary |
| Greenbone Community Edition's description, the OpenVAS history, the three architecture parts | [Background](https://greenbone.github.io/docs/latest/background.html) | Read |
| Greenbone container deployment needs Docker or Podman and Compose; minimum 2 cores, 4 GB RAM, 20 GB storage; recommended 4, 8 GB, 60 GB; the scanner service sets `seccomp=unconfined` and `apparmor=unconfined` | [Community Containers](https://greenbone.github.io/docs/latest/22.4/container/index.html) | Read the page for release 22.4; not run. The compose file can change |
| Wireshark's self-description and GPL source | [wireshark.org](https://www.wireshark.org/) and [FAQ](https://www.wireshark.org/faq.html) | Read the home page and FAQ text; not run |
| Burp Suite Community includes the HTTP(S)/WebSockets proxy and history, Repeater, Decoder, Sequencer, Comparer and an Intruder demo; Professional adds project files, full Intruder, scanner, search, Collaborator and crawling | [Burp Community download page](https://portswigger.net/burp/communitydownload) | Read the comparison text on that page; not run. PortSwigger changes its editions |
| Repeater's description | [Burp Repeater](https://portswigger.net/burp/documentation/desktop/tools/repeater) | Read |
| ZAP is "by Checkmarx", free and open source, an independent Open Source project; repository license is Apache 2.0 | [zaproxy.org](https://www.zaproxy.org/), [LICENSE](https://raw.githubusercontent.com/zaproxy/zaproxy/main/LICENSE) | Read; not run. Whether ZAP's Automation Framework works as the docs say was not tested |
| This repository does not use ZAP or a DAST job | A search of the workflows and docs on 2026-10-22 | Observed in this repository only |
| Metasploit Framework is open source under a BSD-style license, copyright Rapid7; Pro is a separate commercial product | [GitHub README](https://github.com/rapid7/metasploit-framework), [COPYING](https://raw.githubusercontent.com/rapid7/metasploit-framework/master/COPYING), [Rapid7 download page](https://www.rapid7.com/products/metasploit/download/) | Read |
| `check` exists for exploit and auxiliary modules; its six result codes; the Framework "isn't a vulnerability scanner like Nexpose" | [How to write a check method](https://docs.metasploit.com/docs/development/developing-modules/guides/how-to-write-a-check-method.html) | Read; `check` never run |
| The `msfconsole` commands and the module name in Exercise 7 | General knowledge of the console | **Est.**; not run |
| Juice Shop's description, its loopback-bound run command and its permissive license text | [README](https://raw.githubusercontent.com/juice-shop/juice-shop/master/README.md), [LICENSE](https://raw.githubusercontent.com/juice-shop/juice-shop/master/LICENSE) | Read the README text and the license's first lines; not run |
| DVWA's warning, VM advice and GPL license | [README](https://raw.githubusercontent.com/digininja/DVWA/master/README.md) | Read; not run |
| Nikto and nuclei descriptions | [nikto](https://github.com/sullo/nikto), [nuclei](https://github.com/projectdiscovery/nuclei) | Read the README opening lines only; licenses not read |
| Documentation address ranges are reserved for examples | [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737) | Known; the RFC page was not re-read for this lesson, **est.** |
| The maintainer's statement of purpose | Maintainer, 2026-10-22 | His words, as given |

Not verified, plainly: every PowerShell command; anything on Windows or macOS; Burp Suite, ZAP, Wireshark, Greenbone, Metasploit, Nikto and nuclei (none run); the Metasploit module name in Exercise 7; the licenses of Nikto and nuclei; whether `-sS` and `-sC` behave on your system as described; the memory, disk and feed-download cost of Greenbone beyond the documentation's table; the current Nmap release (I ran 7.98 and did not confirm it is the newest); Juice Shop's container (not pulled, to avoid a network pull and image change); and the companion page's final headings (it was being written at the same time).

Next: [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md), where the scan you just made is the thing the decoy is waiting for.
