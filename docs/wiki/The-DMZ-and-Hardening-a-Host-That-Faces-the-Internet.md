# The DMZ, and hardening a host that faces the internet

Side page to the security and defense pages. Read it after [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md) (which asks what there is to attack) and the Plan for failure: blast radius and assuming breach page (which asks what a compromised machine can reach). This page takes the one machine that cannot avoid being reachable, and asks how to build it so that losing it is survivable. Neighbors: [Droplet hardening](Droplet-Hardening.md) (the same ideas on the private connectors) and [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft, written from reading.** Every project fact below names the file or design section I read it in, on **2026-10-30**. **The public edge is design only.** `stacks/50-edge` and `modules/edge-host` are written and tested with mocked providers, the switch `edge_enabled` defaults to `false`, the stage is **not approved**, nothing is approved to build or spend, and nothing here has run on a real machine or against a cloud API (`docs/stages/05-edge.md`). Where a control is only a design it says **design**; where a control is written in code but never applied it says **built, not applied**; anything that exists only as my advice is marked **recommendation**. The exercise at the end runs three `grep` commands against this repository; I ran them once on Linux on the date above. Nothing on the page is an attack or asks you to test an address that is not yours. Not yet reviewed by the maintainer.

> **Prerequisites.** [Networking basics](Networking-Basics-for-This-Project.md) for "port" and "firewall", and [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md). The exercise needs a Linux or macOS terminal and a copy of this repository. No cloud account. About 60 minutes (est.).

## What you will be able to do

- Say what a DMZ is, and why a machine that faces the internet is placed in a network of its own.
- Say what may talk to what in this project's edge design, and what may not.
- Name the hardening steps for an internet-facing host, say which this project's design chose and why it went further than "key-only SSH", and say which steps are built and which are not.
- Say why logs have to leave the host, and what "a place the host cannot rewrite" means.
- Sort events into "alert", "log only" and "noise", and say what the person who gets the alert should do.
- Find, for each hardening item, the test in this repository that checks it, and say what that test does not prove.

## In plain words

Most of what you run should not be reachable from the internet at all. Some things have to be: a public website, a relay that strangers connect to, a game server. A **DMZ** (the name comes from "demilitarized zone") is a separate network zone for exactly those machines. The idea is simple. If a machine must accept connections from anyone, assume someone will eventually find a flaw in it. So put it where a break-in gets the attacker only that machine, not the rest of your systems.

That gives three jobs. **Isolate** the machine so it has no private road into your other networks. **Harden** it so it offers little to attack, and so a flaw in one service does not hand over the whole host. **Watch** it, because a machine you expect to be attacked is the one place where a log and an alert are certain to be useful. This page covers each, and uses this project's public-edge design as the worked example.

## Where this stands in this project

The core environment has no public service: it keeps zero inbound from the internet, with one tag-scoped rule between the two connectors ([Attack surface](Attack-Surface-List-Shrink-Measure.md#how-this-project-shrinks-it)). The edge is a **design** for putting a few internet-facing radio and measurement services on one host, so that core can stay that way. The design's purpose, in its own words: "one immutable host, in a VPC of its own, so the core environment keeps zero inbound" (`docs/superpowers/specs/2026-10-19-edge-dmz-design.md`, section 1).

What exists, from `docs/stages/05-edge.md`:

- A network stack (`stacks/50-edge`): a VPC named `rns-dmz`, two tags, and a Cloud Firewall. It holds no droplet.
- A reusable host module (`modules/edge-host`): one droplet, a reserved IP and a small cloud-init. It installs **no service**, and no stack calls it yet.
- A switch that is off, a cost manifest that prices nothing, and no Spacelift stanza.

What does not exist: any service on the host, any log shipping from it, and any approval. Everything about the services (Reticulum, lxmd, i2pd, Mosquitto, iperf3) and about logging is **design**. The stage guide says the same, and so does the [Roadmap](Roadmap.md).

## What a DMZ is, and why it is its own network

Picture a building with a lobby. Visitors may enter the lobby. The offices behind it need a badge. If someone breaks a window in the lobby, you want the lobby to have no door into the offices that stays open. The DMZ is the lobby.

Three properties make a DMZ what it is, and the design has all three:

1. **A separate network.** The edge is a VPC of its own, `rns-dmz`. DigitalOcean says resources in different VPCs cannot reach each other privately unless the VPCs are peered, and VPC ranges in one account cannot overlap (design section 4.1, citing DigitalOcean's VPC limits page, read 2026-10-19 by the design's author). So the isolation is the default behavior of the VPC, and the work is in never adding the exception.
2. **No peering, no shared tag, no shared secret.** The trust-boundary table says the edge-to-core boundary has "no private east-west path and no admin path: separate VPC, no peering, no shared tag, no shared secret, no shared Doppler config" (design section 3.3).
3. **Nothing in the lobby opens a door into the offices.** The design has one public flow on purpose, the measurement path through a core connector, and it is conditional on two checks nobody has made yet (design section 4.3). The edge also needs one narrow path out for its logs (below).

Isolation does not make the DMZ safe. It makes its compromise **bounded**. The design says so in plain terms: it "accepts that the edge can be compromised and limits what that buys: no path to core, one narrow path home, no admin path to steal, and a rebuild from code as the recovery" (design section 3.6). That is the same habit as the blast radius page: ask what a compromised machine can reach, then cut those edges ahead of time.

### What may talk to what

| From | To | Allowed? | Source |
|---|---|---|---|
| The internet | The edge, on the service ports | Yes, only the ports in the Cloud Firewall. Today the network stack opens TCP 4242 (Reticulum, a variable) and TCP 8883 (MQTT over TLS). i2pd and iperf3 stay closed until their own stacks exist | `stacks/50-edge/main.tf`, `stacks/50-edge/tests/edge.tftest.hcl` |
| The internet | The edge, any other port | No. The Cloud Firewall drops it, and the host's own firewall drops it again | design section 3.3, `modules/edge-host/cloud-init.yaml.tftpl` |
| The edge | Core | No path. Separate VPC, never peered; a test refuses peering and core tags in the edge code | `tests/test_edge_stack.py` (`test_no_peering_and_no_core_tag_in_the_edge_code`) |
| Core | The edge, over a private network | No. There is no private path. The one planned exception is a measurement flow to the edge's public address, **design only** | design section 4.3 |
| An administrator | The edge | No. No SSH, no connector, no admin user. Every change is a pull request, a plan and a rebuild | design section 1, `docs/stages/05-edge.md` |
| The edge | The internet | Only DNS, HTTP and HTTPS for packages, and NTP at the cloud layer. This is wider than it looks once i2pd is added (see "Egress" below) | `stacks/50-edge/main.tf` |
| The edge | Home (logs) | **Design only.** One Twingate service account, one resource: the ingest endpoint on a home relay, never the SIEM. Not built | design section 3.3 and 4.6, `docs/stages/05-edge.md` section 4 |

Two things in that table are easy to misread. First, "the host firewall drops it again" describes a **built, not applied** script (the next section). Second, the firewall rows say what the code declares; no test here looked at a running cloud account.

## Hardening a host that faces the internet

"Hardening" means taking away what the machine does not need and fencing what is left. The list below is general; the second column says what the edge design chose, and the third says where that is checked. A fuller treatment of a private host, with the reasoning for each setting, is on [Droplet hardening](Droplet-Hardening.md).

| # | Step | What the edge design does | Status | The check in this repository |
|---|---|---|---|---|
| 1 | Default-drop host firewall, behind the cloud firewall | An nftables table `inet cah_host` with `policy drop` on input. It accepts loopback, replies to outbound traffic, a few ICMP types, DHCP replies, and exactly the ports the Cloud Firewall opens, rendered from the same list. It filters input only | Built, not applied | `tests/test_edge_stack.py::test_the_host_firewall_is_default_drop_and_mirrors_the_cloud_firewall_input`; `no_ports_means_no_accept_rules_and_a_default_drop_table` and `public_and_restricted_ports_render_into_the_host_firewall` in `modules/edge-host/tests/edge-host.tftest.hcl` |
| 2 | No password login; key-only SSH if you must have SSH | The edge goes further: **no SSH at all**. sshd is stopped and masked, the root password is locked, no key is installed, no admin user exists | Built, not applied | `tests/test_edge_stack.py::test_the_droplet_has_no_admin_path`; `the_user_data_has_no_ssh_path` and `the_droplet_has_no_admin_path_and_no_public_v6` in the module's tests |
| 3 | Automatic security updates | `unattended-upgrades` on the security origins only, with an automatic reboot at a per-droplet time between 01:00 and 03:00 Eastern, before the connectors' 04:00 and 05:00 | Built, not applied | `tests/test_edge_stack.py::test_reboot_slots_are_unique_staggered_and_clear_of_the_connectors`; the module's `the_reboot_time_defaults_to_the_services_slot_in_eastern` |
| 4 | Minimal services and packages | The host's first boot installs three OS packages (`unattended-upgrades`, `chrony`, `nftables`) and **no daemon**. Each service arrives later, through its own stack, with an exact version read from the project's releases | Built, not applied | `tests/test_edge_stack.py::test_the_cloud_init_installs_only_os_packages_and_no_service`; the module's `no_service_is_installed` |
| 5 | Only the ports the service needs, and no IPv6 surprise | The Cloud Firewall opens named ports from one list; IPv6 is off on the droplet, and no inbound rule may carry `::/0` | Built, not applied | `every_public_inbound_rule_is_ipv4_only` and `enabled_opens_reticulum_and_mqtt_only_so_i2pd_and_iperf3_stay_closed` in `stacks/50-edge/tests/edge.tftest.hcl`; `tests/test_ipv6_closed.py` |
| 6 | Protect the metadata endpoint | A script rejects outbound traffic to `169.254.169.254` unless the process runs as root or as the monitoring agent's user. On the connectors this lock is optional and off by default; in the edge template it is enabled in the first-boot commands | Built, not applied. Never tested on a real droplet | `modules/edge-host/cloud-init.yaml.tftpl`. **I found no test that names the metadata lock for the edge** (searched `tests/test_edge_stack.py` and the module tests, 2026-10-30), so this row has a template but no check |
| 7 | No secret in the first-boot data | The template carries no secret-shaped value, and the rendered user-data is never an output. One short-lived read-only token per service is planned for later | Built, not applied (the empty allowed set); the token itself is **design** | `tests/test_edge_stack.py::test_the_user_data_carries_no_secret_shaped_field` and `test_the_user_data_is_never_an_output` |
| 8 | Services run as their own unprivileged users under sandboxing | A stated goal for each service stack | **Design.** No service exists, so there is nothing to test | design section 4.4 |
| 9 | Rate limits and caps on what a service will accept or store | Caps on i2pd transit, lxmd storage and transfer, and a rate cap for Reticulum, which the design says it does not yet have a mechanism for | **Design, and an open blocker.** The design says approval waits for a stated Reticulum rate cap | design section 5.7; see [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md) for the idea |
| 10 | File integrity and "what changed" checks | See the logging and alerting section below | **Design / recommendation** | none |
| 11 | Logs go somewhere the host cannot rewrite | See below | **Design.** Nothing ships logs today | none |

The patching step has a lesson of its own, the patch management lesson tracked as issue #325, which is not written yet. This page only notes that the edge turns on automatic security updates and a staggered reboot; the cadence, the emergencies and the reasons for the windows belong there, and [Backups, recovery and patching](Backups-Recovery-and-Patching.md#patching-cadence-emergencies-and-windows) is the page that exists today.

### Why "no SSH" and not "key-only SSH"

The usual advice for a public host is: no password login, keys only, root login off, and limit who may log in. That is what the connectors do ([Droplet hardening: login](Droplet-Hardening.md#login)), behind Twingate. The edge design goes a step further, because a public host that has a login service has a login service for the internet to find. The design removes the admin path altogether: "Every change is a pull request, a Spacelift plan and a rebuild, and a rebuild is the only recovery" (design section 1). It even refuses the Droplet Console as a break-glass path, because "a standing password that works remotely is the admin path this design removes" (design section 4.2).

That choice has a price, and the stage guide records the open parts: whether DigitalOcean emails a root password, and whether the console works at all, are **unverified** and tracked in issue #248 as a gate before any apply (`docs/stages/05-edge.md` section 4). It also means a host you cannot log in to must be diagnosed from its logs, which is why the next two sections matter more here than on a normal server.

Moving a service to another port is not on this list: it is not protection, and not a hardening step. [The port-move rule](Attack-Surface-List-Shrink-Measure.md#the-port-move-rule) says why, and the design repeats it for i2pd: a random port "is not a security measure", and the port stays closed until its stack exists because nothing needs it (`docs/stages/05-edge.md` section 2, ruling 1).

### Egress: the half people forget

Everything above is about what comes **in**. A compromised daemon that can make arbitrary outbound connections can call home, move data out, or attack someone else from your address. The design is candid here. At the cloud layer the outbound rules are DNS, HTTP, HTTPS and NTP, and the module's host firewall filters input only. The design's proposal is per-user outbound rules on the host, and it states the limit: once i2pd is added with arbitrary outbound ports, "the cloud layer's outbound is fully open and adds nothing", and the per-user rules "are a non-root boundary: a root compromise bypasses them" (design section 4.6.2). Those per-user rules are a **proposal**, not built. The lesson to keep is that an outbound rule is a control you design on purpose, and that logging egress is how you notice when it is missing.

## Logging on a host you cannot log in to

A host that faces the internet will be scanned within hours (design section 3.2 lists "an internet scanner or botnet" as the first actor). Most of what you see in its logs will be that noise. The goal of logging is not to read all of it; it is to be able to answer, after the fact, three questions: what reached the host, what did the host do, and what changed on it.

### What to log

| Source | What it tells you | Status for the edge |
|---|---|---|
| Firewall drops and new connections | What reached the host, and what the host tried to reach | The design says dropped and new outbound connections are counted per user and shipped. **Design.** This repository configures no firewall logging in the connector module either ([Attack surface](Attack-Surface-List-Shrink-Measure.md#log-it-and-alert-on-it), searched 2026-10-30) |
| Each service's own log | What it accepted, rejected or crashed on | No service exists yet. **Design** |
| The system journal and the audit log | Logins (there are none by design), `sudo` (there is no user), service starts and stops, writes to watched files | On the connectors, the opt-in agent collects the journal and `auditd` watches account files; **not applied**, and not configured for the edge (`modules/twingate-bootstrap/cloud-init.yaml.tftpl`) |
| A version report | Which package versions are running, so a missed patch is visible | The design lists "a version report in the log stream" as the check for risk 5. **Design** (design section 3.5) |
| Update and reboot results | That the nightly patch happened and the host came back | The template turns on the automatic reboot; **nothing logs the result** that I could find |

### Where logs go

If the only copy of a log is on the machine that was broken into, the attacker can edit it. The [logs lesson](Logs-SIEM-and-Detection-Basics.md) lists "delete or rewrite the log afterward" among the usual moves, and [Cloud telemetry](Cloud-Telemetry-What-and-Why.md#why-telemetry-has-to-leave-the-machine) explains why a copy has to leave the machine as it is written. The edge design's answer is a home-side **relay**: a Twingate headless client on the edge, a service account that holds exactly one resource (the relay's ingest endpoint), and a relay that forwards into the SIEM so the edge never has a line to the SIEM itself (design section 4.6). The relay's prerequisites include that the edge identity be "unable to read what it wrote", a bounded queue, a maximum message size and a rate limit, and a separate host on its own VLAN (design section 4.6.1). My reading is that a write-only, size-limited, authenticated feed is what "a place the host cannot rewrite" means in practice: the host can add lines, and cannot go back and change the ones already there. That sentence is my interpretation of the design's list, not a quote from it.

This is all **design**. Two facts from the stage guide matter more than the rest: "there is no Twingate headless client, relay, or log path home," and "until then the edge sends no logs" (`docs/stages/05-edge.md` section 4). The design lists the ingest protocol itself as an open item owned by the home-side work. And the design does not assume the home side is safe: the relay treats edge logs as untrusted input, to parse, size-limit and never execute (design section 3.5, risk 9). A hostile line is data, not an instruction, whether a person, a script or a model reads it.

## Alerting: what deserves a person

An alert is a request for a human to do something. A host with no admin path has an advantage here: almost nothing should ever happen on it that you did not plan, so a small number of rules covers a lot. Sort events three ways.

| Event | Alert, log only, or noise? | Why, and what the person should do |
|---|---|---|
| A port scan, or a failed connection to a closed port | Noise | The internet does this constantly. Count it, graph it, do not page anyone. A page for every scan trains people to ignore pages |
| A sudden rise in the number of drops, or in traffic to one service | Log, alert on a threshold | Could be an attack or a popular day. The design's proposed starting values are to alert at 80 percent of the monthly transfer cap and when two days in a row each exceed twice the daily share; these are the design author's numbers, **not measured**, for the maintainer to set (design section 9) |
| Storage for a service nears its cap | Alert at 80 percent | The design proposes it for `lxmd` (design section 9). The person checks whether it is growth or abuse and either raises the cap in a pull request or switches the service off |
| **Any login** | Alert | There is no SSH and no admin user by design, so a successful login of any kind means the design was bypassed. This is my inference from the design, a **recommendation**. The person treats the host as suspect and rebuilds |
| **A change to a file that should never change** (the firewall script, the update configuration, account files) | Alert | The host is built from code and never edited by hand, so any difference from the build is a finding. **Recommendation**; the design names no integrity tool for the edge. See [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) for the tools and for how an attacker attacks the monitor |
| **A new outbound destination from a daemon that had none** | Alert | By design `rnsd`, `mosquitto`, `iperf3` and `lxmd` need no outbound connection at all, replies ride the stateful rule (design section 4.6.2). A new one is a compromise signal. **Design** for the rules; the alert is a recommendation |
| The host firewall table is missing | Alert | The units are ordered after `nftables.service` because it flushes the whole ruleset, but the connector page says a plain stop of it still flushes the ruleset, and this reasoning was never tested on a real machine ([Droplet hardening](Droplet-Hardening.md#host-firewall-built-off-by-default)). **Recommendation** |
| The measurement path shows the edge is down | Alert | The design's own check for the flood case: "the measurement path shows the outage and ntfy alerts" (design section 3.5, risk 7). The person decides whether to wait or to move the address; a flood past DigitalOcean's capacity gets the address black-holed, and the design accepts that |
| A provider abuse notice | A person reads it | Not an alert from a log. The design's check is a calendar item: read the abuse inbox weekly, and its proposed target is to answer within 24 hours and switch the named service off by a pull request and a rebuild (design section 3.5 risk 4 and section 9). The provider's own window is **unverified** |
| A scheduled monthly rebuild finishes | Log only | A routine event. A rebuild that does **not** happen is the thing to alert on |

### How an alert reaches a person

The design names one channel, ntfy, for the outage case (design section 3.5, risk 7). It does not describe any other route from the SIEM to a human for the edge, and the SIEM side is not built. So there is no complete path to describe, and I will not invent one. What you need, for any alert, is the sentence the earlier pages ask for ([Attack surface](Attack-Surface-List-Shrink-Measure.md#log-it-and-alert-on-it), [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md)): who gets it, what it means, and what to do next. On an immutable host the answer to "what to do next" is usually the same for a serious alert: preserve the logs that already left the machine, then rebuild from code, not repair. The design's relay has the same rule ("a suspect relay is replaced, not repaired", section 4.6.1).

## Free path: read the hardening in the code

This exercise reads one file in this repository. It changes nothing and contacts nothing.

**Predict.** The edge template is the first-boot configuration of a public host. Before you look, write down: does it open a port for SSH? What is its input firewall policy? How many lines in it stop sshd or lock root, and how many rules name port 22?

**Do.** From the root of a copy of this repository:

```text
grep -n "policy drop" modules/edge-host/cloud-init.yaml.tftpl
grep -n -E "^  - \[(systemctl, (disable|mask)|passwd)" modules/edge-host/cloud-init.yaml.tftpl
grep -c "dport 22" modules/edge-host/cloud-init.yaml.tftpl
```

Output, from one run on Linux on 2026-10-30:

```text
93:          type filter hook input priority 0; policy drop;
155:  - [systemctl, disable, --now, ssh.service, ssh.socket]
156:  - [systemctl, mask, ssh.service, ssh.socket]
157:  - [passwd, -l, root]
0
```

**Check.** Line 93 is the default-drop policy. Lines 155 to 157 stop and mask sshd and lock the root password. The count of rules naming port 22 is zero. Compare with your prediction. Then ask the harder question: this shows what the template **declares**. It does not show that a droplet built from it behaves that way, because none has been built. The tests named in the hardening table are checks of the same kind, on the code, with mocked providers. A passing test is evidence about the repository, and not about a running host. When the stage is eventually applied, the outside check described in [Droplet hardening](Droplet-Hardening.md#the-outside-check-zero-open-ports) is the kind of measurement that answers the second question, and the design says any such check on a live host runs only against your own resources, in a window the maintainer sets (design section 3).

## Checkpoint

1. What three properties make a network a DMZ in this project's design?
2. The edge has no peering, no shared tag and no shared secret with core. What does it still have that touches the outside, and what is the status of each?
3. Why does the design go further than key-only SSH, and what open questions does that choice leave?
4. Why is a log on the host not enough? What does the design propose, and what is the status?
5. Give two events that are noise, two that deserve an alert, and say what the person should do for each alert.
6. Pick one row of the hardening table and find its test. What does a passing test not prove?
7. Which hardening row has a template but no test that I could find?

Answers: (1) a separate network, no peering or shared tag or secret, and no open door from it into the rest; (2) the public service ports (built in the network stack, not applied), a possible measurement flow through a core connector (design only, conditional on two unverified checks) and a log path home (design only, nothing built); (3) a login service is something the internet can find, so the design removes the admin path and rebuilds instead, and the root-password and console behavior is unverified (issue #248); (4) an attacker who owns the host can edit local logs, so the design ships them to a home relay through one Twingate resource; it is not built; (5) your own answer from the alert table; (6) it proves the repository declares the control, not that a running host has it; (7) the metadata endpoint lock.

## Common mistakes

- **Treating the DMZ as safe.** It is a place where a break-in is contained, not a place where a break-in cannot happen.
- **Hardening the way in and forgetting the way out.** Egress is the half attackers use after they are in.
- **Logging only on the host.** The log you need most is the one the attacker wants to delete.
- **Alerting on everything.** A scan is not an incident. A login on a host that has no login is.
- **Calling something "hardened" because a test passed.** The tests here read code with mocked providers.
- **Repairing a suspect host.** On an immutable host the recovery is a rebuild from code.
- **Copying the edge's "no SSH" onto a host that has state or no replacement path.** It works here only because the host is rebuilt from code, and the design accepts the cost of having no other recovery.

## Claims register

Every project claim above was read on 2026-10-30 in this repository. Nothing was applied, and no cloud API was called. The only commands run were the three `grep` lines in the exercise.

| Claim | Where read | Status |
|---|---|---|
| The edge is design only: switch off, stage not approved, nothing run on a real machine | `docs/stages/05-edge.md` (banner and sections 1, 4, 5) | Read |
| Purpose: a separate VPC so core keeps zero inbound; no SSH, no admin path; rebuild is the only recovery | design section 1 | Read |
| Different VPCs do not reach each other unless peered; ranges cannot overlap | design section 4.1, citing DigitalOcean's VPC limits page read by the design's author on 2026-10-19 | Read the design's citation; I did not re-read the vendor page |
| Trust boundaries, including no shared tag, secret or Doppler config | design section 3.3 | Read |
| The design accepts compromise and bounds it | design section 3.6 | Read |
| Network stack opens TCP 4242 and 8883 inbound; outbound is DNS, HTTP, HTTPS, NTP; no SSH rule | `stacks/50-edge/main.tf`, `stacks/50-edge/tests/edge.tftest.hcl`, `docs/stages/05-edge.md` section 1 | Read; tests not run on a real account |
| Host firewall is `policy drop` on input only, mirrors the Cloud Firewall ports, no port 22 rule | `modules/edge-host/cloud-init.yaml.tftpl` (line 93), the exercise output | Read, and the greps run |
| sshd stopped and masked, root password locked, no key or admin user | `modules/edge-host/cloud-init.yaml.tftpl` (lines 155 to 157), `tests/test_edge_stack.py` | Read, and the greps run |
| Unattended security updates, reboot slots 01:00 to 03:00 Eastern before 04:00 and 05:00 | `modules/edge-host/cloud-init.yaml.tftpl`, `modules/edge-host/reboot-slots.json`, `docs/stages/05-edge.md` ruling 5 | Read |
| Only three OS packages, no daemon | `tests/test_edge_stack.py` (`test_the_cloud_init_installs_only_os_packages_and_no_service`) | Read |
| Metadata lock in the edge template; no test names it | template read; `tests/test_edge_stack.py` and the module tests searched 2026-10-30 | Read; searched, nothing found |
| Root password and console behavior unverified | `docs/stages/05-edge.md` section 4 (issue #248), design section 4.2 | Read |
| Per-user outbound rules proposed, not built; the cloud layer's outbound is open once i2pd is added | design section 4.6.2 | Read |
| No log shipping, no relay, no headless client; the edge sends no logs | `docs/stages/05-edge.md` section 4 | Read |
| Relay prerequisites, including the edge being unable to read what it wrote | design section 4.6.1 | Read |
| Logs from the edge are untrusted input | design section 3.5 (risk 9) | Read |
| Proposed alert thresholds and the 24 hour response target are the design author's, not measured | design section 9 | Read |
| ntfy alerts on the measurement path outage | design section 3.5 (risk 7) | Read |
| "A login on this host means the design was bypassed" and the file-change alert | My inference from the design | Recommendation, not in the repository |
| Reading of "a place the host cannot rewrite" as write-only, size-limited, authenticated | My interpretation of design section 4.6.1 | Interpretation |
| The patch management lesson (issue #325) | Named only; not written | Not read |

Back to [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md), the [Threat model](Threat-Model.md) or [Droplet hardening](Droplet-Hardening.md).
