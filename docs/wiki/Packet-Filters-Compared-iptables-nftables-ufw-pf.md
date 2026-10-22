# Packet filters compared: iptables and ipset, nftables, UFW, and BSD pf (pfSense and OPNsense)

Side page to the start-from-zero pages. Read it after [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md), which teaches the ideas (default deny, stateful, allow by source and port) with one tool, `nft`. This page keeps those ideas and compares the tools that carry them out: the Linux family (`iptables` with `ipset`, `nftables`, UFW, firewalld) and the BSD family (`pf`, and the pfSense and OPNsense firewalls built around it). Next: [Detection and monitoring: Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md).

This is the first of four lessons in a network and host defense track. The other three are [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md), [File integrity and alerting: Tripwire, AIDE, Wazuh](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) and [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md). They are being written at the same time as this page, so those three links may not resolve until they are merged.


> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the Linux lab was run once; the BSD parts were not run at all.** On **2026-10-22** the author ran every Bash command in the free Linux path on a Debian-based machine (kernel 7.1.13, `nft` 1.1.3, `iptables` 1.8.11 in its `nf_tables` variant, `ipset` 7.22, `ufw` 0.36.2, Python 3.13.5) as an ordinary user, with no `sudo`, inside a throwaway `unshare` shell, and pasted trimmed output from those runs. `ipset` was not installed on that machine, so for the run it was unpacked from the distribution's own package into a scratch folder (the page tells you to install the package normally). **Not run:** everything on a BSD system (`pf.conf` and `pfctl -nf` are written from the OpenBSD and FreeBSD documentation and marked **est.**), pfSense and OPNsense (read from their documentation only), firewalld, every PowerShell command (no Windows machine; marked **est.**), the real-host variants with `sudo`, and delivery of firewall logs to the system log (the lab reads them from a netlink log group instead, see Exercise 2). Vendor and project facts were read on **2026-10-22** from the pages named in the [claims register](#claims-register). Your output will differ in small ways (timestamps, port numbers, counters).

> **Prerequisites.** [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) (default deny, stateful or stateless, a rule read line by line, and the same `unshare` lab technique), and a terminal ([Git from zero](Git-From-Zero.md), [The terminal and your first script](Terminal-and-Your-First-Script.md)). The free path needs a Linux machine or virtual machine with `python3`, `ip` (package `iproute2`), `nft` (`nftables`), `iptables`, `ipset`, `ufw` and `tcpdump`. The reading and the exercises are free and always will be; the free path uses only your own computer. About three hours for the reading and the Linux exercises (est.); the optional BSD virtual machine adds about an hour (est.).

> **Where packets go.** Every packet this page sends goes to a pretend machine inside your own shell. Nothing points at anyone else's machine, and you should not point it there: probing a machine you do not own, or have no permission to test, can be against the law or the provider's rules. The rules you write here are loaded into a private network namespace, so they cannot lock you out of your real machine, and they vanish when you leave the shell.

## What you will be able to do

- Say what a packet filter is, and the difference between a stateless and a stateful one, in plain words.
- Name the Linux pieces and how they fit: Netfilter (the hooks in the kernel), `iptables` and `ipset`, `nftables`, and the front ends UFW and firewalld.
- Read a short `pf.conf`, say what "last match wins" and `quick` mean, and say why the same policy is evaluated differently in `pf` and in `nft`.
- Write one small policy (default deny; SSH from one address; web; log the drops; rate-limit new SSH connections) four ways and read all four.
- Apply that policy with `iptables` plus `ipset`, with `nftables` and with UFW in a safe lab, and test it with a tiny server and client.
- Explain what a firewall rule at the host, the subnet, the edge and the cloud can and cannot see.
- Run the build, break, detect, evade, defend loop on a firewall, and say what threatens the firewall itself.

## Where the wiki already touches this (and the gap)

I searched the wiki for these tools before writing. What I found, and what was missing:

| Idea | Where it is used or defined today | The gap this page fills |
|---|---|---|
| Default deny, stateful, a rule set read line by line | [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) teaches them with `nft` and the cloud firewall. | One tool only. No comparison, no `iptables`, no `pf`, nothing about how the tools differ in rule order. |
| nftables, ufw, firewalld | [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md#firewalls) has a table and a warning to pick one manager per machine. [Droplet hardening](Droplet-Hardening.md#host-firewall-built-off-by-default) uses plain `nftables`. | Why there are several, what each generates, what a distribution ships by default. |
| iptables, ipset | Not mentioned in the wiki before this page (Docker's habit of editing the host rules is in [Containers and Docker basics](Containers-and-Docker-Basics.md)). | The older tool, which is still on many machines, and the set feature that makes long lists cheap. |
| pfSense, OPNsense | Named as the home firewall in [Zero trust at home](Zero-Trust-at-Home-Two-Connectors-and-Failover.md) and in the [honeynet design](Deception-and-Honeypots-Design-a-Honeynet.md), whose claims register records how they order rules. | What `pf` is underneath, and how the GUI products wrap it. |
| Cloud firewall | [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md). | How it relates to the host and edge layers (the "think at each level" section below). |

## What a packet filter is

A **packet** is one small chunk of a conversation on a network: a header (who it is from, who it is for, which protocol, which ports) and a body. A **packet filter** is software that looks at each packet's header (and sometimes a little more) and applies a **verdict**: let it through (accept or pass), throw it away silently (drop), or throw it away and tell the sender (reject). The list of rules it checks is the **ruleset**. What happens to a packet that matches no rule is the **default policy**; the safe choice is **default deny**, which the [first firewall lesson](Subnets-NAT-and-Firewalls-By-Hand.md#firewalls) explains.

A packet filter works on addresses, ports, protocols, interfaces and connection state. It does not read the web page inside the packet, tell a good request from a bad one on an allowed port, or know which person is at the other end. That is why it is one layer among several, and why the track continues with [IDS and IPS](IDS-and-IPS-Snort-and-Suricata.md), file integrity and rate limiting.

### Stateless and stateful

A **stateless** filter judges each packet alone. To let replies to your web browsing back in, you must write a rule about reply packets, such as "accept packets from source port 443", which also admits anyone who simply picks that source port. A **stateful** filter keeps a table of the connections it has seen (the **state table**) and recognizes a reply as a reply. Then only the first packet of a connection needs a rule; the replies match the table. Netfilter's own project page lists both stateless and stateful packet filtering among its features ([claims register](#claims-register)). [Exercise 4 of the first firewall lesson](Subnets-NAT-and-Firewalls-By-Hand.md#exercise-4-stateful-or-not) lets you watch the difference. The state table is also an attack surface: it has a size limit (see the threat model below).

## The Linux family

### Netfilter: the hooks

**Netfilter** is the framework inside the Linux kernel that lets other code look at packets at fixed points on their path. The points are called **hooks**. The nftables wiki describes them: traffic addressed to the machine sees the `prerouting` and `input` hooks; traffic made by local programs sees `output` and `postrouting`; traffic merely passing through (the machine acting as a router) sees `prerouting`, `forward` and `postrouting`; and a later addition, `ingress`, attaches to one network interface even earlier ([claims register](#claims-register)).

```text
                    +-----------+     routing     +---------+
 packet in  ------> | prerouting| --- decision -> |  input  | ---> a program on this machine
                    +-----------+        |        +---------+
                                         |                               |
                                         v                               v
                                    +---------+                     +---------+
                                    | forward |                     | output  |
                                    +---------+                     +---------+
                                         |                               |
                                         v                               v
                                    +-------------+  <-----------------+
 packet out <---------------------- | postrouting |
                                    +-------------+
```

Everything on this page that runs on Linux is a way to attach rules to those hooks. `iptables`, `ip6tables`, `ebtables`, `arptables`, `nftables`, UFW and firewalld differ in how you write the rules and how the kernel stores them; the packet path is the same. Connection tracking (**conntrack**) is a separate Netfilter piece that remembers connections; it is what "stateful" means on Linux.

### iptables: tables, chains, targets

`iptables` is the older tool. Its manual page ([claims register](#claims-register)) gives the vocabulary:

- A **table** groups rules by purpose. `filter` is the default and holds the accept-or-drop decisions. `nat` rewrites addresses. `mangle` alters packets. `raw` is mainly for exempting traffic from connection tracking. `security` is for mandatory access control tags.
- A **chain** is an ordered list of rules. The `filter` table has three built-in chains: `INPUT` (packets for this machine), `FORWARD` (packets passing through) and `OUTPUT` (packets this machine makes). You can add your own chains and jump to them.
- A **target** is what a matching rule does: the special values `ACCEPT`, `DROP` and `RETURN`, a jump to another chain, or an extension such as `LOG`, `NFLOG` or `REJECT`.
- A chain has a **policy** (`ACCEPT` or `DROP`) for packets that fall off the end.

The rules of a chain are checked from top to bottom; the first rule that matches and ends in a final verdict decides. `iptables` handles IPv4 only. IPv6 is a separate tool, `ip6tables`, with a separate rule set. That is the source of a classic mistake that the loop below measures: a careful IPv4 ruleset next to an IPv6 path with no rules at all.

### ipset: why sets scale

Suppose you want to drop traffic from 20,000 addresses. With plain `iptables` that is 20,000 rules, and a packet may be compared against many of them before it matches or falls through. **ipset** puts the addresses in one **set** inside the kernel, and one rule asks "is the source in this set?". The ipset project describes sets that can hold addresses, networks, ports, MAC addresses or combinations, in a way "which ensures lightning speed when matching an entry against a set", and lists what it is for: matching a whole collection with one rule, and updating the collection without changing the rules ([claims register](#claims-register)). I make no speed claim beyond that; the lab below shows the structural difference (20,000 members, one rule), not a stopwatch result.

### nftables: the successor

**nftables** is the Netfilter project's replacement for `iptables`, `ip6tables`, `arptables` and `ebtables` ([claims register](#claims-register)). Its wiki lists the differences that matter for a beginner:

- **Families.** One tool, `nft`, handles several families of tables: `ip` (IPv4), `ip6`, `inet` (both IPv4 and IPv6 in one table), `arp`, `bridge` and `netdev`. With `iptables` you needed a tool per family.
- **No built-in tables or chains.** You create the tables and the **base chains** (the ones attached to a hook) you need, and set each chain's `priority` (order among chains on the same hook) and `policy`.
- **Sets and maps.** Named sets of addresses, ports, intervals, even combinations (concatenations) are part of the core; a **map** looks a key up and returns a value or a verdict. **Dynamic** sets can be filled from the packet path, with a rate limit attached to each member; the wiki says this is "a lot more flexible replacement for the hashlimit and connlimit matches in iptables".
- **Atomic loading.** `nft -f file` loads a whole file as one transaction. The wiki's warning about shell scripts is the reason: a script of many `iptables` commands leaves the firewall half configured for a moment, and a half-configured firewall can be wide open or fully closed.
- **Several actions per rule**, optional counters, and a virtual machine inside the kernel so new protocol support can often arrive in the `nft` program without a kernel upgrade.

How verdicts combine differs from what many people assume. The `nft` manual says `accept` and `drop` "terminate ruleset evaluation", but that an accepted packet "can still be dropped later by another hook", or by another base chain on the same hook with a later priority; a `drop` is final. So with `nft` several tables can each have a chain on the `input` hook, and an `accept` in one does not override a `drop` in another. This is why the hardening in this repository keeps its own table (`inet cah_host`) and why a second tool adding its own table is not harmless.

#### The compatibility layer

Most `iptables` commands on a current Linux system are not the old tool. `iptables-nft` accepts `iptables` syntax and stores the rules through the nftables kernel interface; `iptables-legacy` is the old implementation, kept as an alternative. The Debian manual page for `xtables-nft` notes one consequence: each added or deleted rule is atomic. On the lab machine, `iptables --version` printed `iptables v1.8.11 (nf_tables)`, and `nft list ruleset` showed the `iptables` rules as a table marked "managed by iptables-nft, do not touch!" (Exercise 2 shows it). Two practical warnings: some `iptables` extensions have no `nft` equivalent, and on the lab machine `iptables-translate` printed only a comment instead of a rule for `-m recent` and for `-m set`; and two tools editing one ruleset is how rules silently disappear.

#### What current distributions ship

| Distribution family | What I could verify | Source |
|---|---|---|
| Debian | The packaged `iptables` documentation says nftables is the replacement and that the `-nft` variants are the default, with the legacy binaries available as alternatives. The `iptables` NEWS file says it was removed from "important" priority "replaced by nftables". | Files shipped in the Debian `iptables` package, read on a Debian-based machine ([claims register](#claims-register)). Debian's wiki page refused automated reads (an anti-bot challenge). |
| Ubuntu | UFW is the default firewall configuration tool and is disabled by default. Which `iptables` variant is the default: **est.** (not read). | Ubuntu Server documentation. |
| RHEL and relatives | Red Hat's RHEL 8 article calls nftables "the preferred low level firewall solution"; firewalld is the manager, and firewalld's own documentation lists `nftables` as its default backend. RHEL 9 and 10 documentation refused automated reads, so those versions: **est.** | Red Hat blog; firewalld documentation. |
| SUSE | SLES 15 documentation says firewalld is the new default software firewall. | SUSE documentation. |

The table is a snapshot of 2026-10-22. Check your own system with `iptables --version` (look for `nf_tables` or `legacy`) and `sudo nft list ruleset`.

### UFW: a front end

**UFW** ("Uncomplicated Firewall") is a command that writes `iptables` rules for you. Ubuntu's documentation says it was developed "to ease iptables firewall configuration" and is "currently mainly used for host-based firewalls". Its design, from the `ufw-framework` manual page: your commands go into `user.rules`; the files `before.rules` and `after.rules` hold the rules that run before and after yours; "rules are evaluated as follows: before.rules first, user.rules next, and after.rules last"; IPv6 has its own matching files. Three commands matter for this page:

- `ufw default deny incoming` sets the default policy.
- `ufw limit ...` allows a connection but denies an address that "attempts to initiate 6 or more connections within 30 seconds" (UFW manual page).
- `ufw --dry-run ...` prints the rules a command would produce and does not apply them. Ubuntu's documentation shows it.

UFW's own manual says it "is not intended to provide complete firewall functionality via its command interface". Exercise 4 shows what three UFW rules turn into: about a hundred lines of generated `iptables` rules, which is the price of the simple front end and also the reason to read what it generated. A Docker caveat from this wiki: published container ports are added by Docker in a way that can bypass `ufw` ([Containers and Docker basics](Containers-and-Docker-Basics.md)).

### firewalld, in one paragraph

**firewalld** is the manager used on the RHEL family and SUSE. Instead of a flat list of rules it groups network interfaces and sources into **zones** with a level of trust, and rules into named **services**; it separates the running configuration from the permanent one, and it supports IP sets. Its default backend is `nftables` (its `iptables` backend is an option). The command is `firewall-cmd`, for example `sudo firewall-cmd --list-all`. This page does not run it; the comparison below treats it as another front end over the same kernel pieces.

## BSD pf

**pf** (packet filter) started on OpenBSD, where it has been part of the standard kernel since OpenBSD 3.0 ([claims register](#claims-register)). FreeBSD has included a ported version since 5.3 and its handbook warns that its version "has diverged substantially from the upstream OpenBSD version over the years", so "not all features work the same way". pfSense and OPNsense are built on FreeBSD. Three families of the same name, then, with differences you have to check in the manual for the system you actually run.

### A rule file reads like a sentence

`pf.conf` is one text file. Macros, tables and options come first, then the rules. A filter rule has the shape `action [direction] [log] [quick] [on interface] [proto ...] [from ... to ... port ...]`. Two ideas separate it from the Linux tools.

**Last match wins.** The OpenBSD FAQ says: filter rules are evaluated first to last, and "the last rule to match is the 'winner' and will dictate what action to take". The keyword **`quick`** ends the evaluation at once: a packet matching a `quick` rule is decided there. That is why a `pf` ruleset usually starts with `block all` (the FAQ calls this default deny and recommends it as "the first filter rule") and then adds `pass` rules after it that override it for the traffic you want. In `iptables` and in most other filters the first matching rule with a final verdict decides, so the natural order is the reverse: specific rules first, a catch-all last. The same policy written in both styles has the rules in opposite orders.

**State is the default.** The FAQ says `keep state` "is the default for all filter rules", and the `pf.conf` manual says that for stateful TCP connections "the default is flags S/SA": only the opening packet (SYN, without ACK) is matched by the rule, and every later packet of the connection is matched by the state table, which is much faster than walking the rules ([claims register](#claims-register)).

### Tables, anchors, scrub, logging, queues

- **Tables.** A `pf` table holds a group of IPv4 and IPv6 addresses; the FAQ says lookups are "very fast and consume less memory and processor time than lists". It is the `pf` counterpart of an `ipset` set or an `nft` set. In pfSense and OPNsense, "aliases" are the GUI's name for such groups (OPNsense's documentation shows the resulting pf table).
- **Anchors.** An anchor is a named collection of rules, tables and other anchors that you can load and replace separately from the main file; the main ruleset reaches it with an `anchor` rule. A `quick` rule inside an anchor ends evaluation in the anchor and the main ruleset. This is how packages (and the GUI products) add rules without rewriting the main file.
- **Scrub (normalization).** Scrubbing cleans packets so there is no ambiguity in how the receiver reads them (for example reassembling fragments, or lowering the maximum segment size). **The syntax differs between systems:** OpenBSD's manual and FreeBSD 14 use `match in all scrub (no-df random-id max-mss 1440)`; the FreeBSD manual lists an older `scrub in all fragment reassemble ...` form "pre-FreeBSD 14".
- **Logging.** A rule with `log` sends matching packets to the `pflog0` interface; the `pflogd` daemon writes them to `/var/log/pflog`, and `tcpdump -n -e -ttt -i pflog0` shows them live ([claims register](#claims-register)).
- **Queueing and traffic shaping.** `pf` can assign packets to queues for bandwidth control. The mechanism is another place where the systems differ: FreeBSD's manual says ALTQ "is currently not available in the GENERIC kernel", so using it means a custom kernel; the FreeBSD handbook pairs ALTQ with `pf` and `dummynet` with the other firewall, IPFW. Check your system's manual before you rely on a queueing example from another system's page.
- **Syntax check.** `pfctl -n` means "do not actually load rules, just parse them". `pfctl -nf /etc/pf.conf` is the BSD counterpart of `nft -c -f`.

### How pfSense and OPNsense wrap pf

Both are firewalls you configure through a web page; underneath they are FreeBSD with `pf` doing the filtering.

- **pfSense** describes itself as "a free open source customized distribution of FreeBSD tailored for use as a firewall and router entirely managed by an easy-to-use web interface". The GUI rules are translated into a `pf` ruleset: the generated rules are in `/tmp/rules.debug` and are overwritten on the next reload, so edits belong in the GUI, and `pfctl -sr` shows the rules as `pf` interpreted them. Netgate's documentation says rules on the interface tabs are "evaluated on a first match basis", with the Ethernet and Floating tabs as exceptions; on floating rules the Quick option is optional, and without it the behavior becomes "last match wins". So the GUI presents the first-match model most people expect and uses `quick` underneath, while `pf` itself is last-match.
- **OPNsense** documents the same split: a rule's Quick option is on by default ("first match"), and a rule without it is "last match wins", which is how its default deny is built. Its rules are stateful by default, and its rate-limit options (maximum new connections per interval, with an "overload table") are `pf`'s `max-src-conn-rate` and `overload` in a form.
- Both ship traffic shaping that is not plain `pf`: Netgate's page says pfSense limiters use `dummynet(4)`, and OPNsense's shaping page says its shaper is built on IPFW and dummynet.

Pick the product's documentation, not the OpenBSD FAQ, when you work in the GUI.

## Windows, in one paragraph

Windows Defender Firewall is a host firewall that is on by default; Microsoft's documentation says its default is to block incoming traffic unless it is solicited or matches a rule, and to allow outgoing traffic unless a rule blocks it. The rules are made with `New-NetFirewallRule` (parameters such as `-Direction`, `-Action`, `-Protocol`, `-LocalPort`, `-RemoteAddress`) and the profile defaults with `Set-NetFirewallProfile -DefaultInboundAction`. The `New-NetFirewallRule` page I read lists no connection-rate-limit option. The SSH-from-one-address line would be the following (**est.**; not run, since there was no Windows machine):

```powershell
New-NetFirewallRule -DisplayName "Lesson: SSH from one admin" -Direction Inbound -Protocol TCP -LocalPort 22 -RemoteAddress 192.0.2.10 -Action Allow
```

## The same policy, four ways

The policy, in five sentences:

1. **Default deny** for anything arriving at the machine. Outgoing traffic and replies are allowed.
2. **SSH (TCP 22) only from one address**, `192.0.2.10` (a documentation address from [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737)).
3. **Web (TCP 80 and 443)** from anywhere.
4. **Log** what is dropped, with a rate limit so logging cannot flood the disk.
5. **Rate-limit new SSH connections** from the allowed address.

All four examples keep the same shape, and what differs is the point of this page. Read them side by side before running them. The lab uses everything above except the BSD version, which is shown, not run.

### Linux: iptables and ipset

`policy-iptables.sh` (the IPv4 half; the lab adds the IPv6 half later, for a reason you will measure):

```bash
#!/usr/bin/env bash
# policy-iptables.sh: the lesson's policy with iptables + ipset, applied to the machine "srv".
#   1 default deny inbound      2 SSH only from the addresses in the set "admins"
#   3 web (80, 443) from anywhere   4 log what is dropped   5 rate-limit new SSH connections
# The lab starts from an empty firewall. Run it inside the lab shell.
set -euo pipefail
ns() { ip netns exec srv "$@"; }

ns ipset create admins hash:ip                  # a set of single addresses
ns ipset add admins 192.0.2.10                  # add as many as you like; the rules below do not change

ns iptables -P INPUT DROP                       # 1: default deny (policy = what nothing else matched gets)
ns iptables -A INPUT -i lo -j ACCEPT
ns iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
ns iptables -A INPUT -m conntrack --ctstate INVALID -j DROP
# 5 + 2: count every new SSH connection from an admin, then drop the 6th within 30 seconds
ns iptables -A INPUT -p tcp --dport 22 -m set --match-set admins src -m conntrack --ctstate NEW \
    -m recent --name sshnew --set
ns iptables -A INPUT -p tcp --dport 22 -m set --match-set admins src -m conntrack --ctstate NEW \
    -m recent --name sshnew --update --seconds 30 --hitcount 6 -j DROP
ns iptables -A INPUT -p tcp --dport 22 -m set --match-set admins src -j ACCEPT
ns iptables -A INPUT -p tcp -m multiport --dports 80,443 -j ACCEPT          # 3: web
# 4: log what reached the end (NFLOG so the lab can read it; on a real host use -j LOG)
ns iptables -A INPUT -m limit --limit 5/min -j NFLOG --nflog-group 1 --nflog-prefix "fw-drop "
```

Read it: the policy line is the default deny. The set `admins` holds the allowed addresses, and adding a second admin later is one `ipset add`, not a new rule. The two `recent` rules are the rate limit: the first records every new SSH connection from an admin, the second drops the connection when it is the 6th within 30 seconds (the same `recent` pattern UFW generates). The accept rule comes after them. `NFLOG` sends a copy of unmatched packets to a log group, limited to 5 a minute; on a real host you would normally use `-j LOG`, which writes to the kernel log.

### Linux: nftables

`policy.nft`:

```text
#!/usr/sbin/nft -f
# policy.nft: the lesson's policy in nftables. One file, loaded as one atomic transaction.
#   1 default deny inbound      2 SSH only from the addresses in the set "admins"
#   3 web (80, 443) from anywhere   4 log what is dropped   5 rate-limit new SSH connections
# "inet" means this table sees IPv4 and IPv6 both.
table inet filter
delete table inet filter       # start clean if it exists (the pair is what makes re-loading safe)

table inet filter {
    set admins {                          # a named set: add or remove members without touching rules
        type ipv4_addr
        elements = { 192.0.2.10 }
    }
    set ssh_rate {                        # a "dynamic" set: the packet path adds a member per source
        type ipv4_addr
        flags dynamic
        timeout 1m
        size 65535
    }
    chain input {
        type filter hook input priority filter; policy drop;     # 1: default deny
        iifname "lo" accept
        ct state established,related accept
        ct state invalid drop
        # IPv6 needs these ICMPv6 messages to find neighbors; without them nothing over IPv6 works
        icmpv6 type { destination-unreachable, packet-too-big, time-exceeded, nd-neighbor-solicit, nd-neighbor-advert } accept
        # 5: a source that opens new SSH connections faster than the bucket allows is dropped
        tcp dport 22 ct state new ip saddr @admins add @ssh_rate { ip saddr limit rate over 6/minute burst 5 packets } counter drop
        tcp dport 22 ip saddr @admins accept                      # 2: SSH from the admins only
        tcp dport { 80, 443 } accept                              # 3: web
        limit rate 5/minute log group 1 prefix "fw-drop "         # 4: log what reached the end
    }
}
```

Read it: one file, one atomic load. The first two lines are the idiom the repository's own scripts use: create the table if it is missing, then delete it, so the file loads the same way whether or not the table existed. `inet` means the one table sees both IP versions, so there is no second file for IPv6, and the `icmpv6` rule is there because IPv6 needs those messages to find its neighbors (without it, default deny silently kills IPv6; the lab measures this). The rate limit is different in kind from the `iptables` one: the dynamic set `ssh_rate` gets one entry per source address and attaches a **token bucket** to it (`burst 5 packets`, refilled at 6 a minute); `recent` counts hits in a time window. The two will not drop the same connection, and the page does not claim they should.

### Linux: UFW

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw logging low
sudo ufw limit from 192.0.2.10 to any port 22 proto tcp
sudo ufw allow 80,443/tcp
sudo ufw enable
```

Five commands and an enable. There is no set, so a second admin is a second rule. The `limit` rule is UFW's rate limit (6 connections in 30 seconds). `logging low` logs blocked packets that match no rule, with rate limiting. Do **not** type these on a machine you reach over SSH from another address: `ufw enable` with a default-deny policy and a rule for only one address can cut you off. The lab runs them against a private copy.

### BSD: pf (OpenBSD syntax) and the FreeBSD differences

`pf.conf` (**est.**; not run: there was no BSD system):

```text
# pf.conf: the lesson's policy, OpenBSD syntax (est.; not run). See the text for FreeBSD differences.
ext_if = "egress"                 # OpenBSD interface group; on FreeBSD name the real interface

table <admins> { 192.0.2.10 }     # who may use SSH (add more with pfctl -t admins -T add ADDRESS)
table <bruteforce> persist        # filled by the rate limit below

set skip on lo                    # do not filter loopback
set block-policy drop             # blocked packets are dropped silently

match in all scrub (no-df random-id max-mss 1440)    # normalize packets (FreeBSD 13 and older: see text)

block log all                     # 1 and 4: default deny, and log what is blocked to pflog0

block in quick from <bruteforce>  # known abusers: decided here, evaluation stops (quick)

pass out on $ext_if               # our own traffic and its replies (keep state is the default)

# 2 and 5: SSH only from <admins>; more than 6 new connections in 30 seconds
# puts the source in <bruteforce> and kills its existing connections
pass in on $ext_if proto tcp from <admins> to ($ext_if) port ssh flags S/SA keep state \
    (max-src-conn-rate 6/30, overload <bruteforce> flush global)

# 3: web from anywhere
pass in on $ext_if proto tcp to ($ext_if) port { http, https } flags S/SA keep state
```

Read it from the top, remembering that **the last match wins**. `block log all` is the default deny and also the logging: every packet that no later rule passes is dropped and logged to `pflog0`. `block in quick from <bruteforce>` comes next and, being `quick`, ends the evaluation for known abusers. The `pass out` rule is the outbound allow (state is kept by default, so replies come back). The SSH rule has the allowed table as its source and the rate limit in parentheses: more than 6 connections in 30 seconds from one address puts that address into `<bruteforce>`, and `flush global` kills its existing connections. The web rule is last. A packet that matches only `block log all` is blocked; a packet that matches `block log all` and then a pass rule is passed, because the later rule wins.

Differences to expect on other systems (all **est.** unless the claims register says otherwise):

- `ext_if = "egress"` is an OpenBSD interface group; on FreeBSD, pfSense or OPNsense you name the real interface (for example `vtnet0` or `em0`).
- Scrub: on FreeBSD 13 and earlier, replace the `match ... scrub` line with `scrub in all fragment reassemble no-df max-mss 1440` (the FreeBSD handbook shows that form).
- The rate limit counts connections that complete the TCP handshake (the OpenBSD FAQ says so), while the `iptables` `recent` rule above counts attempts; a SYN flood that never completes handshakes is a different problem.
- Entries stay in `<bruteforce>` until you remove them. `pfctl -t bruteforce -T expire 86400` deletes the entries older than a day (the `pfctl` manual describes `expire`; the schedule is yours to build).
- In pfSense or OPNsense you would not edit this file; you would make an alias for `admins` and the rules in the GUI, and the web page does the rest.

## The comparison

No tool wins on every row. Read the rows that match your situation.

| Property | iptables + ipset | nftables | UFW | pf (OpenBSD, FreeBSD) | pfSense / OPNsense |
|---|---|---|---|---|---|
| Rule model | Tables of chains of rules, one tool per IP family | Tables, chains, sets and maps; one tool; `inet` covers both IP versions | Simple commands that write `iptables` rules into files | One text file: macros, tables, options, rules | A web interface that generates a `pf` ruleset |
| Evaluation order | First matching rule with a final verdict decides | First final verdict in a chain; other base chains on the same hook still run after an `accept` | Fixed: before, then yours, then after | Last match wins, unless `quick` | GUI: first match per interface tab (`quick` underneath); floating rules can be last-match |
| Atomic reload | Not for a script of commands; `iptables-restore` loads a file | `nft -f` loads a file as one transaction | Applies through its init script (est.) | `pfctl -f` loads the file (atomicity: est.) | Reload from the GUI (est.) |
| Sets | `ipset` (separate tool and kernel module) | Built in: sets, maps, intervals, dynamic sets | None in UFW itself | Tables, built in | Aliases, backed by pf tables |
| Logging | `LOG` (kernel log) or `NFLOG` (to userspace) | `log` statement | `ufw logging LEVEL` (kernel log or NFLOG backend) | `log` keyword to `pflog0`, read with `tcpdump -i pflog0` | Firewall log view in the GUI |
| Rate limiting | `recent`, `hashlimit`, `connlimit`, `limit` | Dynamic sets and meters with `limit rate`; `ct count` | `ufw limit` (6 connections in 30 seconds) | `max-src-conn-rate` with `overload` tables | The same limits as options on a rule, plus limiters (dummynet) |
| Learning curve | Moderate; many options and two tools for IPv6 | Moderate; one syntax, clear structure | Low for simple cases; read the generated rules for more | Moderate; short file, but last-match order surprises people | Low to start; learn `pf` underneath to debug |
| Where it is the default | Still on many systems, usually as `iptables-nft` | The default or preferred engine on current Debian and RHEL-family systems (see above) | Ubuntu (disabled until you enable it) | OpenBSD; FreeBSD ships it with two other firewalls | pfSense; OPNsense |

The "atomic reload" row has several **est.** cells because I did not find a statement in the pages I read for them, and I did not run them.

The maintainer of this project prefers BSD's `pf` stack and runs pfSense. That is his own statement of preference. The page compares the tools by their documented behavior and by what the lab measured, and does not rank them.

## Think at each level

A rule means little without knowing where it runs and what it can see. This project has all four places.

| Level | Example here | What a rule there can see | What it cannot see |
|---|---|---|---|
| **Host** | `nftables` on the connectors ([Droplet hardening](Droplet-Hardening.md#host-firewall-built-off-by-default)); UFW on an Ubuntu server | The packets arriving at this machine, the interface, addresses, ports, connection state; for traffic the machine itself sends, which user ID sent it (the repository's metadata lock does this) | Packets that never reach this machine. What happens on other machines. The contents of encrypted traffic. |
| **Subnet or VLAN boundary** | Rules between the VLANs on a home firewall; a router access list | Traffic that crosses between segments | Traffic between two machines on the same segment (it does not cross the boundary; est., from how switching works). |
| **Edge firewall** | pfSense at the home edge | Everything entering and leaving the site on that link: addresses, ports, NAT state | Which person or role sent a request ([Zero trust at home](Zero-Trust-at-Home-Two-Connectors-and-Failover.md) makes this point for pfSense); inside encrypted or tunneled traffic; traffic between devices on one segment. |
| **Cloud firewall** | DigitalOcean cloud firewall, attached by tag ([DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md)) | Public and VPC traffic to the droplets that carry the tag; stateful; enforced outside the machine, so a compromised droplet cannot switch it off from inside | Anything inside the droplet (processes, containers, files). Traffic logs are not available on DigitalOcean's firewall, per the limits page recorded in the [first firewall lesson's claims register](Subnets-NAT-and-Firewalls-By-Hand.md#claims-register). |

The levels are layers, not alternatives. A wrong rule at one level is a good reason to have a correct one at the next. The first lesson already says the cloud firewall is the only inbound layer in the project today and that the host firewall is a second one, off by default.

## Free path: a lab on your own computer

Everything in this section runs on your own computer and costs nothing. Each exercise has four steps: **predict** (write down what you expect first), **do**, **check**, **undo**.

**Which track.** The lab uses Linux network namespaces, which Windows does not have. Windows learners run it in WSL 2 with the Bash commands (**est.**; not tested) and use the read-only PowerShell commands in Exercise 5 for their own firewall.

### Setup: the pretend network and three tools

You will build two pretend machines joined by one pretend cable, inside a shell of your own, with the same `unshare` technique as the [first firewall lesson](Subnets-NAT-and-Firewalls-By-Hand.md#the-lab-three-pretend-machines-in-your-own-shell). `srv` is the machine you firewall. `cli` is the client; it owns two IPv4 addresses so it can play "the admin" (`192.0.2.10`) and "someone else" (`192.0.2.20`), and an IPv6 address from the documentation range (`2001:db8::/32`, [RFC 3849](https://www.rfc-editor.org/rfc/rfc3849)).

**Safety.** You are root only inside the pretend world. The firewall rules go into the `srv` namespace, not into your machine's own rules, and when the `unshare` shell exits every namespace, server and rule is destroyed. Nothing persists after the exit. One exception to know about: loading a kernel feature that was not loaded before (for example the `ipset` module) is done by your real kernel and stays loaded until reboot; it changes no rules.

Install the tools if they are missing (**est.**, Debian or Ubuntu family): `sudo apt install ipset nftables iptables ufw tcpdump iproute2 python3`. Make a folder and save these files in it from a normal terminal:

```bash
mkdir -p ~/filter-lab && cd ~/filter-lab
```

`listen.py`, a server that answers every connection with one line, on IPv4 and IPv6:

```python
#!/usr/bin/env python3
# listen.py PORT [PORT ...]: accept TCP on IPv4 and IPv6, send one line, close.
import socket
import sys
import threading


def serve(port):
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)  # one socket, both IP versions
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("::", port))
    s.listen(64)
    while True:
        conn, _ = s.accept()
        conn.sendall(f"hello from port {port}\n".encode())
        conn.close()


for p in sys.argv[1:]:
    threading.Thread(target=serve, args=(int(p),), daemon=True).start()
threading.Event().wait()
```

`probe.py`, a client that connects from a chosen source address and reports `open` (the server answered), `closed` (something answered "refused") or `filtered` (silence until the timeout, which is what a drop looks like):

```python
#!/usr/bin/env python3
# probe.py SRC DST PORT [-n COUNT]
# Connect from address SRC to DST:PORT. Prints one word per try:
#   open      = the server answered
#   closed    = something answered "refused" (a reset or an ICMP error)
#   filtered  = silence until the timeout (a drop)
# With -n COUNT it tries COUNT times in a row and prints one letter each (o, c, f).
import socket
import sys

args = sys.argv[1:]
count = 1
if "-n" in args:
    i = args.index("-n")
    count = int(args[i + 1])
    del args[i : i + 2]
src, dst, port = args[0], args[1], int(args[2])
fam = socket.AF_INET6 if ":" in dst else socket.AF_INET
letters = ""
for _ in range(count):
    s = socket.socket(fam, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.bind((src, 0))
        s.connect((dst, port))
        s.recv(64)
        word = "open"
    except ConnectionRefusedError:
        word = "closed"
    except (socket.timeout, TimeoutError):
        word = "filtered"
    except OSError as e:
        word = f"error({e.strerror})"
    finally:
        s.close()
    letters += word[0]
if count == 1:
    print(f"{src:>12} -> {dst}:{port:<5} {word}")
else:
    print(f"{src:>12} -> {dst}:{port:<5} {letters}   (o=open c=closed f=filtered)")
```

`lab-up.sh`, which builds the pretend network:

```bash
#!/usr/bin/env bash
# lab-up.sh: build two pretend machines joined by one pretend cable, inside YOUR shell.
# Run it inside:  unshare -Urnm bash   (a private user, network and mount namespace)
# srv = the machine we firewall.  cli = the client; it owns two addresses so it can
# play "the admin" (.10) and "someone else" (.20).  Addresses are documentation
# ranges (RFC 5737 for IPv4, RFC 3849 for IPv6): they never leave this shell.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
mount -t tmpfs tmpfs /run && mkdir -p /run/netns     # private to this shell
ip netns add srv
ip netns add cli
ip link add s0 type veth peer name c0
ip link set s0 netns srv
ip link set c0 netns cli
ip -n srv addr add 192.0.2.1/24 dev s0
ip -n srv addr add 2001:db8::1/64 dev s0 nodad
ip -n cli addr add 192.0.2.10/24 dev c0
ip -n cli addr add 192.0.2.20/24 dev c0
ip -n cli addr add 2001:db8::10/64 dev c0 nodad
for n in srv cli; do ip -n "$n" link set lo up; done
ip -n srv link set s0 up
ip -n cli link set c0 up
ip netns exec srv python3 "$here/listen.py" 22 80 8080 > /dev/null 2>&1 &
sleep 0.5
echo "lab ready: srv 192.0.2.1 and 2001:db8::1 (ports 22, 80, 8080); cli 192.0.2.10, 192.0.2.20, 2001:db8::10"
```

`matrix.sh`, which asks the same questions of `srv` whatever firewall it has:

```bash
#!/usr/bin/env bash
# matrix.sh: ask the same six questions of srv, whatever firewall it has.
here="$(cd "$(dirname "$0")" && pwd)"
p() { ip netns exec cli python3 "$here/probe.py" "$@"; }
echo "--- from the admin address (.10)";   p 192.0.2.10 192.0.2.1 22;  p 192.0.2.10 192.0.2.1 80;  p 192.0.2.10 192.0.2.1 8080
echo "--- from another address (.20)";     p 192.0.2.20 192.0.2.1 22;  p 192.0.2.20 192.0.2.1 80
echo "--- over IPv6 (admin address)";      p 2001:db8::10 2001:db8::1 80;  p 2001:db8::10 2001:db8::1 8080
```

Now start the lab shell. `-p -f --mount-proc` gives it its own process list, so the server dies with the shell:

```bash
unshare -Urnmpf --mount-proc bash
cd ~/filter-lab
```

If it fails with `Operation not permitted`, your distribution restricts unprivileged user namespaces. The fallback is `sudo unshare -nmpf --mount-proc bash`: you are then real root on the machine, and you should type only what this page gives you, which touches only the new namespaces (**est.**; not run).

### Exercise 1: the baseline

**Predict.** `srv` has no firewall yet. Which of ports 22, 80, 8080 will answer, from each address, over IPv4 and IPv6?

**Do (Bash, inside the lab shell).**

```bash
bash lab-up.sh
bash matrix.sh
```

**Check.** Everything is open (trimmed, run 2026-10-22):

```text
lab ready: srv 192.0.2.1 and 2001:db8::1 (ports 22, 80, 8080); cli 192.0.2.10, 192.0.2.20, 2001:db8::10
--- from the admin address (.10)
  192.0.2.10 -> 192.0.2.1:22    open
  192.0.2.10 -> 192.0.2.1:80    open
  192.0.2.10 -> 192.0.2.1:8080  open
--- from another address (.20)
  192.0.2.20 -> 192.0.2.1:22    open
  192.0.2.20 -> 192.0.2.1:80    open
--- over IPv6 (admin address)
2001:db8::10 -> 2001:db8::1:80    open
2001:db8::10 -> 2001:db8::1:8080  open
```

This is the "before" picture. The target after the policy: from `.10`, 22 and 80 open and 8080 filtered; from `.20`, 22 filtered and 80 open; over IPv6, 80 open and 8080 filtered.

**Undo.** Nothing yet; keep this shell for Exercise 2.

**PowerShell.** There is no PowerShell equivalent of a network namespace. Use WSL 2 (**est.**).

### Exercise 2: iptables and ipset

**Predict.** After you apply `policy-iptables.sh`: (a) what will `.20` see on port 22? (b) What will IPv6 on port 8080 see, given that the script only talks to `iptables`? (c) If the admin opens 8 SSH connections in a row, how many get through?

**Do (Bash, in the same lab shell).** Save `policy-iptables.sh` from the section above, and `policy-ip6tables.sh`, the IPv6 half:

```bash
#!/usr/bin/env bash
# policy-ip6tables.sh: the IPv6 half of the iptables policy. iptables does not touch IPv6;
# ip6tables is a separate tool with a separate rule set. (The nftables "inet" table needs no twin.)
set -euo pipefail
ns() { ip netns exec srv "$@"; }
ns ip6tables -P INPUT DROP
ns ip6tables -A INPUT -i lo -j ACCEPT
ns ip6tables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
ns ip6tables -A INPUT -m conntrack --ctstate INVALID -j DROP
# IPv6 needs these ICMPv6 messages to find neighbors; without them nothing over IPv6 works
for t in destination-unreachable packet-too-big time-exceeded neighbour-solicitation neighbour-advertisement; do
  ns ip6tables -A INPUT -p icmpv6 --icmpv6-type "$t" -j ACCEPT
done
ns ip6tables -A INPUT -p tcp -m multiport --dports 80,443 -j ACCEPT
```

Apply the IPv4 policy, and ask the questions. Capture the log packets in the background first so you can read them afterwards (`-Z root` stops `tcpdump` from trying to drop its privileges, which a user namespace does not allow):

```bash
bash policy-iptables.sh
ip netns exec srv tcpdump -Z root -l -ni nflog:1 -c 2 > nflog.out 2>&1 &
sleep 1
bash matrix.sh
ip netns exec cli python3 probe.py 192.0.2.10 192.0.2.1 22 -n 8
```

**Check.** Run 2026-10-22 (trimmed):

```text
--- from the admin address (.10)
  192.0.2.10 -> 192.0.2.1:22    open
  192.0.2.10 -> 192.0.2.1:80    open
  192.0.2.10 -> 192.0.2.1:8080  filtered
--- from another address (.20)
  192.0.2.20 -> 192.0.2.1:22    filtered
  192.0.2.20 -> 192.0.2.1:80    open
--- over IPv6 (admin address)
2001:db8::10 -> 2001:db8::1:80    open
2001:db8::10 -> 2001:db8::1:8080  open          <- the IPv6 hole
  192.0.2.10 -> 192.0.2.1:22    ooooffff   (o=open c=closed f=filtered)
```

(a) filtered, as designed. (b) **Open.** The IPv4 rules say nothing about IPv6, and `ip6tables` has an empty rule set. This is the path the loop below uses. (c) Four more connections get through and then the rest are dropped. The matrix already made one SSH connection, so five were counted before the sixth was dropped: the `recent` rule fires on the 6th within 30 seconds. Wait 30 seconds and the counter forgets.

Close the IPv6 path and look at what was built:

```bash
bash policy-ip6tables.sh
bash matrix.sh | tail -3
ip netns exec srv iptables -L INPUT -v -n --line-numbers
cat nflog.out | cut -c1-120
```

```text
--- over IPv6 (admin address)
2001:db8::10 -> 2001:db8::1:80    open
2001:db8::10 -> 2001:db8::1:8080  filtered
Chain INPUT (policy DROP 4 packets, 240 bytes)
num   pkts bytes target     prot opt in     out     source               destination
...
5        5   300 DROP       tcp  --  *      *       0.0.0.0/0            0.0.0.0/0            tcp dpt:22 match-set admins src ctstate NEW recent: UPDATE seconds: 30 hit_count: 6 ...
...
listening on nflog:1, link-type NFLOG (Linux netfilter log messages), snapshot length 262144 bytes
17:27:13.938241 IP 192.0.2.10.38465 > 192.0.2.1.8080: Flags [S], seq ..., length 0
17:27:13.938317 IP 192.0.2.20.35343 > 192.0.2.1.22: Flags [S], seq ..., length 0
```

The packet and byte counters on each line are your evidence of which rule saw how much traffic, and the log shows two dropped opening packets, from the admin to 8080 and from the other address to 22. The counters on the `DROP` line prove the rate limit fired.

Now the sets. Make a set of 20,000 addresses from the benchmark range `198.18.0.0/15` ([RFC 2544](https://www.rfc-editor.org/rfc/rfc2544) reserves it for testing), and drop them with one rule:

```bash
python3 - <<'PY' > blocklist.txt
print("create blocklist hash:net")
for i in range(20000):
    print(f"add blocklist 198.18.{i//250}.{i%250}")
PY
ip netns exec srv ipset restore < blocklist.txt
ip netns exec srv iptables -I INPUT 1 -m set --match-set blocklist src -j DROP
ip netns exec srv ipset list blocklist -t
ip netns exec srv iptables -S INPUT | head -3
```

```text
Name: blocklist
Type: hash:net
...
Size in memory: 576720
References: 1
Number of entries: 20000
-P INPUT DROP
-A INPUT -m set --match-set blocklist src -j DROP
-A INPUT -i lo -j ACCEPT
```

Twenty thousand members, one rule, and "References: 1" says one rule uses the set. Adding the 20,001st address is an `ipset add`; the rules do not change.

Finally, see the compatibility layer. The same rules, as the kernel's nftables interface stores them:

```bash
ip netns exec srv nft list ruleset | head -12 | cut -c1-120
```

```text
# Warning: table ip filter is managed by iptables-nft, do not touch!
# Warning: table ip6 filter is managed by iptables-nft, do not touch!
table ip filter {
	chain INPUT {
		type filter hook input priority filter; policy drop;
		xt match "set" counter packets 0 bytes 0 drop
		iifname "lo" counter packets 0 bytes 0 accept
		ct state related,established counter packets 35 bytes 1820 accept
		...
		tcp dport 22 xt match "set" ct state new xt match "recent" counter packets 5 bytes 300 drop
```

Notice `xt match "set"` and `xt match "recent"`: those two are carried over as legacy extension modules instead of native `nft` expressions (the `ct state` lines, by contrast, became native). That is the line to look at if you plan to migrate.

**Undo.** `exit` the lab shell. Everything is gone. Check in a normal terminal: `ip netns list` shows none of these, and `sudo iptables -S` (if you want to look) shows your machine's own rules, untouched.

### Exercise 3: nftables

**Predict.** Compared with Exercise 2: (a) will IPv6 need a second step? (b) What happens to the running firewall if you load a file with a typo in its last line? (c) Will the admin's eight-connection burst give the same pattern as with `recent`?

**Do (Bash).** Start a fresh lab shell (`unshare -Urnmpf --mount-proc bash`, then `cd ~/filter-lab`, then `bash lab-up.sh`). Save `policy.nft` from above. Check it without loading, load it, ask the questions, and read the log:

```bash
ip netns exec srv nft -c -f policy.nft && echo CHECK-OK
ip netns exec srv nft -f policy.nft
ip netns exec srv tcpdump -Z root -l -ni nflog:1 -c 2 > nflog.out 2>&1 &
sleep 1
bash matrix.sh
ip netns exec cli python3 probe.py 192.0.2.10 192.0.2.1 22 -n 10
ip netns exec srv nft list chain inet filter input
ip netns exec srv nft list set inet filter ssh_rate
```

Then break the file on purpose and load it:

```bash
sed 's/tcp dport { 80, 443 } accept/tcp dport { 80, 443 } acept/' policy.nft > bad.nft
ip netns exec srv nft -f bad.nft; echo exit=$?
ip netns exec srv nft list chain inet filter input | head -3
```

**Check.** The matrix is identical to the `iptables` result, IPv6 included, from one file and without a second tool (run 2026-10-22):

```text
CHECK-OK
  192.0.2.10 -> 192.0.2.1:22    open
  192.0.2.10 -> 192.0.2.1:80    open
  192.0.2.10 -> 192.0.2.1:8080  filtered
  192.0.2.20 -> 192.0.2.1:22    filtered
  192.0.2.20 -> 192.0.2.1:80    open
2001:db8::10 -> 2001:db8::1:80    open
2001:db8::10 -> 2001:db8::1:8080  filtered
  192.0.2.10 -> 192.0.2.1:22    ooooffffff   (o=open c=closed f=filtered)
```

(a) No: `inet` covers both. (c) Similar shape, a different count: the matrix's one connection plus four more got through, then the token bucket was empty and the rest were dropped. A bucket and a window are different rules even when they look alike. The listings show the live counter on the rate-limit rule (`counter packets 6 bytes 360 drop`) and the dynamic set holding the admin's address with its own limit and an expiry:

```text
	set ssh_rate {
		type ipv4_addr
		size 65535
		flags dynamic,timeout
		timeout 1m
		elements = { 192.0.2.10 limit rate over 6/minute burst 5 packets expires 54s309ms }
	}
```

(b) The typo:

```text
bad.nft:30:74-74: Error: syntax error, unexpected newline
        tcp dport { 80, 443 } acept                              # 3: web
                                                                         ^
exit=1
table inet filter {
	chain input {
		type filter hook input priority filter; policy drop;
```

The load failed, the exit status is not zero, and the previous ruleset is still the live one. A bash script of separate commands would have applied the lines before the typo and then stopped. This is atomic loading; it protects against a syntax error (and, the wiki says, against the half-configured moment), and it does not protect against a rule that is valid and wrong.

Last, sets and the "break" you will use in the loop. With the ruleset loaded, remove the admin and ask again, then put the admin back:

```bash
ip netns exec srv nft delete element inet filter admins { 192.0.2.10 }
ip netns exec cli python3 probe.py 192.0.2.10 192.0.2.1 22
ip netns exec srv nft add element inet filter admins { 192.0.2.10 }
ip netns exec srv nft flush set inet filter ssh_rate
ip netns exec cli python3 probe.py 192.0.2.10 192.0.2.1 22
```

```text
  192.0.2.10 -> 192.0.2.1:22    filtered
  192.0.2.10 -> 192.0.2.1:22    open
```

One member removed and the admin is locked out; one added back and the rule works again, with no rule edited. (The `flush set` line clears the rate limiter's memory: the burst test above had emptied the admin's bucket, and without the flush the probe would still read `filtered` for up to a minute, which is a good example of two different reasons for the same symptom.) The same change in `pf` is `pfctl -t admins -T add 192.0.2.10` (the tool's table commands; **est.**, not run).

**Undo.** `exit`.

### Exercise 4: UFW, dry-run first

**Predict.** Three UFW rules (one default policy, one `limit`, one `allow`): about how many lines of `iptables` rules will exist afterwards? Will the over-limit SSH connections look `filtered` or `closed`?

**Do (Bash).** On a real machine you own, the safe first step is the dry run, which prints and applies nothing (needs `sudo` because UFW checks that you are root; **est.**, not run with `sudo` here):

```bash
sudo ufw --dry-run allow 8080/tcp
```

To apply UFW's rules in the lab without touching `/etc/ufw`, make a private copy of its files and point `ufw` at it with `--rootdir` and `--datadir` (these options exist in `/usr/sbin/ufw`; the copy only reads world-readable files). Save `ufw-prepare.sh` and `policy-ufw.sh`:

```bash
#!/usr/bin/env bash
# ufw-prepare.sh: make a private, throwaway copy of ufw's config in ./ufwroot so ufw can be run
# without touching /etc/ufw. Everything it reads is world-readable; it needs no sudo.
# Layout is the Debian/Ubuntu ufw package's (est. for Ubuntu; checked on a Debian-based system).
set -euo pipefail
R="$PWD/ufwroot"
rm -rf "$R"
mkdir -p "$R/etc/ufw/applications.d" "$R/etc/default" "$R/lib" "$R/usr/share"
cp -rL /usr/share/ufw "$R/usr/share/ufw"
cp -r /lib/ufw "$R/lib/ufw"
cp /etc/default/ufw "$R/etc/default/ufw"
for f in ufw.conf before.rules after.rules before6.rules after6.rules user.rules user6.rules before.init after.init; do
  cp -L "/usr/share/ufw/$f" "$R/etc/ufw/$f"
done
: > "$R/etc/ufw/sysctl.conf"
echo "ufw sandbox ready in $R"
```

```bash
#!/usr/bin/env bash
# policy-ufw.sh: the lesson's policy as ufw commands, run against the sandbox copy and the
# machine "srv". On a real Ubuntu machine you would type the same ufw lines with sudo
# and without the --rootdir/--datadir options.
set -euo pipefail
R="$PWD/ufwroot"
u() { ip netns exec srv ufw --rootdir="$R" --datadir="$R" "$@" 2>&1 | grep -v '^WARN' || true; }
u default deny incoming                                   # 1
u default allow outgoing
u logging low                                             # 4 (blocked packets, rate-limited)
u limit from 192.0.2.10 to any port 22 proto tcp          # 2 + 5
u allow 80,443/tcp                                        # 3
u --force enable
u status verbose
```

Start a fresh lab shell, build the lab, and run both:

```bash
unshare -Urnmpf --mount-proc bash
cd ~/filter-lab
bash ufw-prepare.sh
bash lab-up.sh
bash policy-ufw.sh
bash matrix.sh
ip netns exec cli python3 probe.py 192.0.2.10 192.0.2.1 22 -n 8
ip netns exec srv iptables -S | wc -l
grep -c . ufwroot/etc/ufw/user.rules
```

**Check.** Run 2026-10-22 on the Debian-based machine (the layout of the UFW package on Ubuntu: **est.**):

```text
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)

To                         Action      From
--                         ------      ----
22/tcp                     LIMIT IN    192.0.2.10
80,443/tcp                 ALLOW IN    Anywhere
80,443/tcp (v6)            ALLOW IN    Anywhere (v6)
...
  192.0.2.10 -> 192.0.2.1:22    open
  192.0.2.10 -> 192.0.2.1:80    open
  192.0.2.10 -> 192.0.2.1:8080  filtered
  192.0.2.20 -> 192.0.2.1:22    filtered
  192.0.2.20 -> 192.0.2.1:80    open
2001:db8::10 -> 2001:db8::1:80    open
2001:db8::10 -> 2001:db8::1:8080  filtered
  192.0.2.10 -> 192.0.2.1:22    oooocccc   (o=open c=closed f=filtered)
104
38
```

The same matrix as before from five commands. UFW enabled the IPv6 half by itself (`IPV6=yes` is in its defaults file). Two things are different from the other tools, and both are worth seeing. First, the over-limit connections are `c`, **closed**, not `f`: UFW's limit rule ends in `REJECT`, so the sender is told no, where the other two silently dropped. Second, three rules became 104 lines of `iptables` rules for IPv4 (plus the IPv6 set), and the part UFW wrote for you is in `ufwroot/etc/ufw/user.rules`. Open it, find the three lines starting `-A ufw-user-input -p tcp --dport 22 -s 192.0.2.10`, and you will see the same `recent --set` and `recent --update --seconds 30 --hitcount 6` pattern as in `policy-iptables.sh`. UFW is `iptables` with a smaller vocabulary.

**Undo.** `exit`. The `ufwroot` folder in `~/filter-lab` is yours to delete (`rm -rf ~/filter-lab/ufwroot`); your real `/etc/ufw` was never touched.

### Exercise 5: pf syntax check (BSD virtual machine; est.)

**Cost and teardown first.** This exercise needs a BSD system. The software is free. If you do not have one, it uses your own computer's disk, memory and a virtual machine program, and no provider bill. Create a disposable OpenBSD or FreeBSD virtual machine in a host-only or isolated network ([Red and blue as yin and yang](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md#a-safe-network-for-the-lab) explains the isolation). Teardown: delete the virtual machine and its disk. Nothing here was run for this page (**est.**).

**Predict.** `pfctl -nf` only parses. What will it print for a correct file, and what for a file with a misspelled keyword?

**Do (BSD shell, in the VM).** Save the `pf.conf` from above as `/tmp/lesson-pf.conf`. On FreeBSD change `ext_if` to the VM's interface name and, on FreeBSD 13 or older, the `match ... scrub` line as the notes say. Then:

```sh
pfctl -nf /tmp/lesson-pf.conf && echo SYNTAX-OK
sed 's/flush global/flush globl/' /tmp/lesson-pf.conf > /tmp/bad-pf.conf
pfctl -nf /tmp/bad-pf.conf; echo exit=$?
```

**Check (est.).** The first command prints nothing and then `SYNTAX-OK`. The second prints a syntax error with a line number and exits non-zero. Neither loads anything (`-n`). To load the file and watch it, `pfctl -f /tmp/lesson-pf.conf` then `pfctl -sr` (show the rules as `pf` interpreted them), and `tcpdump -n -e -ttt -i pflog0` to see logged packets. **Do not load a default-deny file over SSH to a VM you cannot reach from its console**; the FreeBSD handbook gives the same caution about remote firewall edits.

**PowerShell.** None; use the VM's shell.

**Undo.** `pfctl -d` disables `pf`; delete the VM.

### Exercise 6: the same policy from the manual page (PowerShell, read only, est.)

On Windows, look at your own firewall without changing it:

```powershell
Get-NetFirewallProfile | Format-Table Name, Enabled, DefaultInboundAction, DefaultOutboundAction
Get-NetFirewallRule -Direction Inbound -Enabled True -Action Allow | Select-Object -First 10 DisplayName, Profile
```

**Check (est.).** A default inbound action of `Block` is default deny. The second command lists a few enabled inbound allow rules, which are the equivalent of the open doors in the matrix above.

## Build, break, detect, evade, defend (the firewall loop)

The same loop as the [labs](Labs-Break-It-on-Purpose.md), applied to a firewall. Every step below was run in the lab in Exercises 2 and 3.

- **Build.** The policy above, written as `iptables` plus `ipset` for IPv4, or as one `nft` file. You tested it with `matrix.sh`.
- **Break (a lockout by a bad rule).** Remove the admin from the set (Exercise 3 did it): the admin's SSH goes from `open` to `filtered` with no error on the admin's side, only silence. Typical real causes: a wrong address in the set, the rule order wrong, `ufw enable` before the SSH rule, or a default-deny policy loaded before the accept rules.
- **Detect.** The three signals the lab produced. The **log**: the opening packet from the admin to port 22 arrives at the `NFLOG` group (or in the kernel log with `LOG`; in `pf`, in `pflog0`) with your prefix. The **counters**: the default-policy and log-rule counters rise (`iptables -L -v`, `nft list chain`). The **probe**: `filtered` where the matrix expects `open`. A beginner's habit worth having: keep a second way in (a console, or a timer that removes the new rules, such as `(sleep 60; nft delete table inet filter) &`; **est.**, shown not run) before you edit a firewall you are connected through. Detection of the other kind, the firewall log read by a SIEM, is in [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md).
- **Evade.** Go around the rule rather than through it. In Exercise 2 the IPv6 path was `open` while IPv4 was closed, because `iptables` does not govern IPv6. The `nft` `inet` table closed both at once; UFW did it by default. The related trap runs the other way: a default-deny IPv6 policy without the ICMPv6 neighbor messages made all IPv6 `filtered` in the lab until the rule was added, so a "closed" result is not proof that your deny rule is the cause. A second evasion to know: at the `ingress` hook the nftables wiki says fragmented datagrams have not yet been reassembled, so a rule that matches a port number works only on unfragmented packets or the first fragment. Rules at the usual `input` hook see reassembled traffic when connection tracking is on (**est.**; I did not test fragments).
- **Defend.** Default deny on both stacks (`ip6tables` too, or one `inet` table); a rule set that is tested every time it changes (`matrix.sh` is a regression test: write down the expected answers and diff them), loaded atomically (`nft -c -f` then `nft -f`; `pfctl -nf` then `pfctl -f`); sets for lists so a change is data, not a new rule; rate limits with logs; and the next layer (the cloud firewall, the edge, [IDS and IPS](IDS-and-IPS-Snort-and-Suricata.md)) so one wrong rule is not the whole defense.

### Flip the board

You wrote and tested the rules. Now take the other two jobs.

**The reviewer.** Someone hands you this rule set and asks "is it safe for a server that holds a database?" Find at least five problems without running it.

```bash
iptables -P INPUT ACCEPT
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -s 192.0.2.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 3306 -j ACCEPT
iptables -A INPUT -j DROP
```

Answers (check them against the lab if you like; in the lab the matrix came back all `open`, IPv6 included):
1. The policy is `ACCEPT`, so the file is default allow that a final `DROP` rule tries to turn into default deny. Anything appended after the last rule, or a flush of the chain, leaves the machine open.
2. SSH is open to the whole internet, with no source, no rate limit.
3. A whole `/24` is trusted by one blanket rule, which is far wider than any one administrator needs.
4. Port 3306, the MySQL/MariaDB port, is open to everyone. A database should be reachable by name from the application hosts only.
5. There is no rule for established connections before the final `DROP`; in a lab test the machine's own outgoing connections would hang waiting for replies once the policy is `DROP`.
6. Nothing governs IPv6.
7. Nothing logs.

**The attacker's view.** An outside scanner does not see your rules; it sees the responses. `filtered` (silence) says a drop, `closed` says a reset or a reject, `open` says a service. In the lab the three tools gave different answers to the same over-limit connection: silence from `nft` and `iptables`, "refused" from UFW. A defender who rejects tells the attacker something is there and behaves a certain way; one who drops spends the attacker's time. Either can be right; the point is that the difference is observable, and that is how a scanner fingerprints a firewall. This is the same idea as the port states in the [first firewall lesson](Subnets-NAT-and-Firewalls-By-Hand.md#exercise-4-stateful-or-not).

## Threat model of the firewall itself

The firewall is a security control and also a target. Using the method from the project's [Threat model](Threat-Model.md) page (assets, actors, boundaries, abuse cases, ranked risks, a mitigation and a check for each), here is a short one for a host or edge packet filter. It covers what is below and nothing else: it is not an audit.

**Assets.** The ruleset (its integrity). The management path (SSH, the GUI, the console). The logs. The state table. The machine's availability.

**Actors.** An anonymous remote host. A compromised machine behind the firewall. An administrator who makes a mistake. Someone with a stolen administrator credential. A software update or another tool that rewrites rules.

**Trust boundaries.** The network edge (untrusted to the firewall). The management interface (administrator to firewall). The step from a rule file to the kernel (a front end such as UFW to `iptables`, a file to `nft`). The packet path to the logging path.

| ID | Abuse case | Impact | Prerequisite | Rank |
|---|---|---|---|---|
| R1 | The administrator loads a rule that locks everyone out, or a default-deny policy with no accept rule for the management path. | The machine is unreachable; recovery needs a console. | An administrator with ordinary access. | High |
| R2 | Traffic reaches the host by a path the rules do not cover: IPv6 with only IPv4 rules, a second interface, a container network. | The firewall does nothing for that traffic. | Network access to that path. | High |
| R3 | Another program or update replaces or flushes the ruleset (this repository's own notes: Ubuntu's `nftables.service` begins with `flush ruleset`; Docker adds rules that can bypass `ufw`). | Protections disappear silently. | A package upgrade, a service restart, a Docker run. | High |
| R4 | The management interface is exposed and weakly protected. | The attacker edits the rules. | Network reach and a guessed or stolen credential. | High |
| R5 | A flood fills the state table or the logs. A connection-tracking table has a size limit (`net.netfilter.nf_conntrack_max` exists on the machine used; `pf` has `set limit states`). | Legitimate connections are refused, or the disk fills. | A source that can send many new connections. | Medium |
| R6 | A log entry is attacker-controlled text (a hostname, a user agent) that a tool later treats as an instruction. | Log injection into a SIEM or a script. | Ability to send traffic that is logged. | Medium |
| R7 | The rules drift: an emergency change made by hand and never recorded. | The documented policy and the real one differ. | An administrator under pressure. | Medium |
| R8 | A `drop` hides an attack because nobody reads the log. | Missed detection. | Time. | Medium |

**Mitigation and verification.**

| ID | Mitigation | Verification |
|---|---|---|
| R1 | Test the file before loading (`nft -c -f`, `pfctl -nf`); keep a console or a timed rollback; load the management-path accept rule first. | Run the syntax check and read its exit code; run `matrix.sh` against a lab copy and expect `open` for the admin. |
| R2 | One `inet` table, or `ip6tables` as well; include IPv6 in the test matrix. | `matrix.sh` shows IPv6 8080 `filtered`; `ip6tables -S` and `nft list ruleset` show a drop policy. |
| R3 | Keep this tool's rules in the same place that the system reloads at boot; order the services; one manager per machine; read the generated rules after a Docker change. | After restarting the firewall service, rerun the matrix and `nft list ruleset`; this repository's [Droplet hardening](Droplet-Hardening.md#host-firewall-built-off-by-default) describes its own ordering. |
| R4 | Management only from a trusted source, with keys and MFA where offered; the cloud firewall as the outer layer. | From an address outside the allowed source, the management port reads `filtered`. |
| R5 | Rate limits and per-source limits; size the table; alert on its use. | Rerun the burst test (`probe.py ... -n 10`) and see drops; read the state-table limit on your system. |
| R6 | Treat log fields as data; a SIEM parses, never executes. | See [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md). |
| R7 | The ruleset lives in a file under version control, loaded by script, and the live rules are diffed against it. | `nft list ruleset` against the file; a change without a commit is a finding. |
| R8 | Alert on drops that matter (a spike, a drop of the admin address) rather than on all drops. | The lab's log rule and counters; a SIEM rule from the logs page. |

**Residual risk and what is not covered.** A correct, atomic, tested ruleset does not stop an attack through an allowed port (the web server on 80 and 443 is open to the world on purpose), a stolen credential, or a flaw in the filter's own code or in a front end. This section did not cover physical access, the hypervisor, firmware, or the BSD and pfSense products beyond their documentation. The tools are all maintained software and have had vulnerabilities; patching them is part of the defense ([Backups, recovery and patching](Backups-Recovery-and-Patching.md)).

## Checkpoint

You are done when you can say, without looking:

- What "last match wins" means in `pf`, what `quick` does, and why a first-match filter needs its rules in the opposite order.
- Why `ipset`, an `nft` set and a `pf` table are the answer to "block 20,000 addresses".
- What `iptables-nft` is, and why `iptables --version` printing `nf_tables` does not mean you are running `nftables` rules in the sense of a native `nft` file.
- What an atomic load protects you from, and one thing it does not.
- Why IPv6 needs its own test, and what UFW generated from your three commands.
- What a host firewall, an edge firewall and a cloud firewall can each see.

## Common mistakes

| Symptom | Likely cause | Fix |
|---|---|---|
| Locked out after enabling a default-deny firewall | The management path had no accept rule, or the rule was loaded after the policy took effect | A console, a timed rollback, and the accept rule first. |
| "IPv4 is closed, but the scanner still finds it" | Only `iptables` was configured; IPv6 is another tool | `ip6tables`, or one `inet` table. |
| All IPv6 stops working after a default-deny | The ICMPv6 neighbor messages are dropped | Accept `nd-neighbor-solicit` and `nd-neighbor-advert` (and the error types). |
| A `pf` rule seems ignored | A later rule matched last | Remember last match; use `quick`, or reorder. |
| An `nft` `accept` did not let traffic through | Another table's chain on the same hook dropped it | `nft list ruleset` and look for every table with a base chain on that hook. |
| UFW rule "disappeared" after a Docker run | Docker added its own rules ahead of UFW's | [Containers and Docker basics](Containers-and-Docker-Basics.md); publish ports to `127.0.0.1` or put the control in the cloud firewall. |
| `ipset: command not found` | Not installed (it is a separate package) | Install `ipset`. |
| A script of `iptables` commands left the firewall open for a moment | Not atomic | `iptables-restore` with a file, or `nft -f`. |

## Claims register

All read-only requests; retrieved 2026-10-22 unless stated. "Read" means I read the passage; "Observed" means I ran it that day in the lab.

| Claim | Source | Status |
|---|---|---|
| Netfilter provides packet filtering for Linux 2.4.x and later; features include stateless and stateful packet filtering; the hooks are a kernel framework for other code to register callbacks | [netfilter.org](https://www.netfilter.org/) | Read |
| `iptables` tables (`filter`, `nat`, `mangle`, `raw`, `security`), built-in chains (`INPUT`, `FORWARD`, `OUTPUT` in `filter`), targets `ACCEPT`, `DROP`, `RETURN` or a chain or an extension | [iptables(8), copy for 1.8.3](https://ipset.netfilter.org/iptables.man.html); local `iptables` 1.8.11 | Read the 1.8.3 copy; the lab machine runs 1.8.11 |
| `recent` match: dynamic address list, `--set`, `--update`, `--hitcount`, `--seconds` | [iptables-extensions(8)](https://ipset.netfilter.org/iptables-extensions.man.html) | Read; behavior Observed |
| ipset: sets of addresses, networks, ports and more, "lightning speed when matching an entry against a set"; match a collection with one iptables rule; update without performance penalty | [IP sets](https://ipset.netfilter.org/) | Read. No speed figure is claimed |
| nftables replaces `{ip,ip6,arp,eb}tables`, is based on an in-kernel virtual machine, since kernel 3.13, and ships a backward-compatibility layer that runs `iptables` syntax over it | [nftables project](https://www.netfilter.org/projects/nftables/index.html) | Read |
| nftables: new syntax; no predefined tables or chains; a rule can take several actions; the `inet` family sees IPv4 and IPv6; generic sets, maps, concatenations; new protocols without a kernel upgrade | [What is nftables?](https://wiki.nftables.org/wiki-nftables/index.php/What_is_nftables%3F) | Read |
| `nft -f file` updates the ruleset atomically; a script of many `iptables` commands is not atomic | [Atomic rule replacement](https://wiki.nftables.org/wiki-nftables/index.php/Atomic_rule_replacement) | Read; a typo file leaving the old ruleset live: Observed |
| Families `ip`, `ip6`, `inet`, `arp`, `bridge`, `netdev` | [Nftables families](https://wiki.nftables.org/wiki-nftables/index.php/Nftables_families) | Read |
| Hooks: input path sees `prerouting` and `input`; local output sees `output` and `postrouting`; forwarded traffic sees `prerouting`, `forward`, `postrouting`; `ingress` hook (kernel 4.2) is per interface and fragmented datagrams are not yet reassembled there; no predefined chains | [Netfilter hooks](https://wiki.nftables.org/wiki-nftables/index.php/Netfilter_hooks) | Read |
| `accept` and `drop` terminate ruleset evaluation; an accepted packet can still be dropped by a later hook or a later-priority chain; a `drop` is final | [nft(8), Debian trixie, nftables 1.1.3-1](https://manpages.debian.org/trixie/nftables/nft.8.en.html) | Read |
| Dynamic sets with per-element rate limits are a replacement for `hashlimit` and `connlimit` | [Meters](https://wiki.nftables.org/wiki-nftables/index.php/Meters) | Read; token-bucket behavior Observed |
| `xtables-nft`: additions and deletions are atomic; `iptables-legacy` is the old implementation | [xtables-nft(8), Debian trixie, iptables 1.8.11-2](https://manpages.debian.org/trixie/iptables/iptables-nft.8.en.html); [Moving from iptables to nftables](https://wiki.nftables.org/wiki-nftables/index.php/Moving_from_iptables_to_nftables) | Read. `-m recent` and `-m set` printing as comments in `iptables-translate`: Observed |
| Debian: nftables is the replacement for iptables; `-nft` variants and legacy binaries are alternatives; iptables "replaced by nftables" in default priority | `/usr/share/doc/iptables/README.Debian` and `NEWS.Debian.gz`, shipped in the Debian `iptables` package | Read locally. [Debian wiki nftables page](https://wiki.debian.org/nftables) refused automated reads |
| `iptables --version` printed `v1.8.11 (nf_tables)` on the lab machine; `nft list ruleset` showed the rules as `table ip filter` managed by iptables-nft | Local command | Observed |
| Ubuntu: `ufw` is the default firewall configuration tool; disabled by default; `--dry-run` prints rules without applying; "developed to ease iptables firewall configuration"; "mainly used for host-based firewalls" | [Ubuntu Server firewalls](https://documentation.ubuntu.com/server/how-to/security/firewalls/) | Read |
| UFW: `limit` denies an address that attempts 6 or more connections in 30 seconds; log levels (`low` logs blocked packets not matching policy, rate limited); `LOGGING_BACKEND` kernel or NFLOG | [ufw(8)](https://git.launchpad.net/ufw/plain/doc/ufw.8) | Read (upstream source); behavior Observed |
| UFW framework: `before.rules`, then `user.rules`, then `after.rules`; separate IPv6 files | [ufw-framework(8)](https://git.launchpad.net/ufw/plain/doc/ufw-framework.8) | Read |
| UFW commands generated `iptables-restore` rules (104 lines for IPv4 after enabling three rules) and enabled IPv6 by default; the over-limit connection was refused, not dropped | Local run | Observed. Ubuntu's package layout: **est.** |
| firewalld: zones, IP set support, runtime versus permanent configuration; `FirewallBackend` `nftables` is the default, `iptables` an option | [firewalld.org](https://firewalld.org/documentation/), [firewalld.conf](https://firewalld.org/documentation/man-pages/firewalld.conf.html) | Read |
| RHEL 8: nftables is the preferred low-level firewall solution. RHEL 9 and 10 defaults: not read | [Red Hat, Using nftables in RHEL 8](https://www.redhat.com/en/blog/using-nftables-red-hat-enterprise-linux-8) | Read for 8. RHEL 9 and 10 documentation refused automated reads: **est.** |
| SLES 15 introduced firewalld as the default software firewall | [SLES 15 SP7 firewall chapter](https://documentation.suse.com/sles/15-SP7/html/SLES-all/cha-security-firewall.html) | Read |
| pf: part of OpenBSD's GENERIC kernel since 3.0; filter rules evaluated first to last, last match wins, `quick` ends evaluation; "default deny" with `block all` first; `keep state` the default; table lookups "very fast" | [OpenBSD PF FAQ](https://www.openbsd.org/faq/pf/index.html), [filtering](https://www.openbsd.org/faq/pf/filter.html), [tables](https://www.openbsd.org/faq/pf/tables.html) | Read |
| pf.conf: last matching rule decides; `quick`; stateful default `flags S/SA`; `max-src-conn-rate`, `overload`, `flush global`; scrub is `match ... scrub (...)`; `set limit states`; `log` goes to `pflog0` | [pf.conf(5), OpenBSD](https://man.openbsd.org/pf.conf) | Read |
| Anchors: a named collection of rules, tables and anchors; `quick` inside ends evaluation | [PF Anchors](https://www.openbsd.org/faq/pf/anchors.html) | Read |
| `pflogd` writes `pflog0` traffic to `/var/log/pflog`; `tcpdump -n -e -ttt -i pflog0` shows it live | [PF Logging](https://www.openbsd.org/faq/pf/logging.html) | Read |
| `pfctl -n`: "Do not actually load rules, just parse them"; table `expire` | [pfctl(8), OpenBSD](https://man.openbsd.org/pfctl) | Read |
| FreeBSD: ported pf since 5.3; "diverged substantially" from OpenBSD's; PF with optional ALTQ; three firewalls in base; example with `table <bruteforce> persist` and `overload ... flush global`; caution about remote lockouts | [FreeBSD Handbook, Firewalls](https://docs.freebsd.org/en/books/handbook/firewalls/) | Read |
| FreeBSD pf.conf: last match wins; ALTQ "not available in the GENERIC kernel"; `match in all scrub (...)` with a "pre-FreeBSD 14" scrub form | [pf.conf(5), FreeBSD](https://man.freebsd.org/cgi/man.cgi?query=pf.conf&sektion=5&format=html) | Read |
| pfSense is a customized distribution of FreeBSD managed by a web interface | [pfSense documentation, general](https://docs.netgate.com/pfsense/en/latest/general/index.html) | Read |
| pfSense: interface rules are evaluated on a first-match basis; Ethernet and Floating tabs are exceptions; on floating rules Quick is optional and without it "last match wins" | [Firewall fundamentals](https://docs.netgate.com/pfsense/en/latest/firewall/fundamentals.html), [Floating rules](https://docs.netgate.com/pfsense/en/latest/firewall/floating-rules.html) | Read |
| pfSense generates its `pf` rules in `/tmp/rules.debug`; `pfctl -sr` shows interpreted rules | [Viewing the PF ruleset](https://docs.netgate.com/pfsense/en/latest/firewall/pf-ruleset.html) | Read |
| pfSense limiters use `dummynet(4)`; aliases group hosts, ports, networks | [Limiters](https://docs.netgate.com/pfsense/en/latest/trafficshaper/limiters.html), [Aliases](https://docs.netgate.com/pfsense/en/latest/firewall/aliases.html) | Read |
| OPNsense is FreeBSD based; stateful by default; Quick is the default (first match), without it last match wins; overload table option; aliases shown as pf tables; shaper uses IPFW and dummynet | [OPNsense introduction](https://docs.opnsense.org/intro.html), [Firewall](https://docs.opnsense.org/manual/firewall.html), [Aliases](https://docs.opnsense.org/manual/aliases.html), [Shaping](https://docs.opnsense.org/manual/shaping.html) | Read |
| Windows Defender Firewall: on by default; blocks incoming unless solicited or matching a rule; `New-NetFirewallRule` parameters; `Set-NetFirewallProfile -DefaultInboundAction` | [Windows Firewall overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/), [New-NetFirewallRule](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule?view=windowsserver2025-ps), [Set-NetFirewallProfile](https://learn.microsoft.com/en-us/powershell/module/netsecurity/set-netfirewallprofile?view=windowsserver2025-ps) | Read. The commands in this page were not run |
| DigitalOcean firewalls are stateful, tag based, have no traffic logs | See the claims register of [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md#claims-register) | Recorded there; not re-read on 2026-10-22 |
| Documentation address ranges | [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737) (IPv4), [RFC 3849](https://www.rfc-editor.org/rfc/rfc3849) (IPv6), [RFC 2544](https://www.rfc-editor.org/rfc/rfc2544) (benchmark range `198.18.0.0/15`) | Ranges as named; only RFC 5737 was cross-checked by the first firewall lesson; the other two: **est.** |
| The `pf.conf` and `pfctl` outputs in this page | None | **Not run**: no BSD system. Written from the manuals above |
| Every statement about performance | None | None is made, on purpose |

## Where to next

The next lesson in this track, [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md), adds the layer that reads what a packet filter cannot; [rate limiting at every layer](Rate-Limiting-at-Every-Layer.md) takes the one rule you wrote here and puts it at the CDN, the proxy, the application and the kernel (those links may not resolve until the pages are merged). In the core path, [Detection and monitoring](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) shows where firewall logs end up.
