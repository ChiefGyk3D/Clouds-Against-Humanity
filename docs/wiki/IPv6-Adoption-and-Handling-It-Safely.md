# IPv6: why adoption is slow, why this project is IPv4-only, and how to handle it safely in a lab

Side page to the networking pages. Read it after [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) (addresses, CIDR, NAT, default deny) and beside [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md), which measured the IPv6 firewall hole this page builds on. It answers four questions in order. What is IPv6, for someone who knows basic networking? Why, years after it was ready, is it still not the default everywhere? Why does this project keep it off, and how would you turn it on on purpose? And how do you practice all of that on your own computer without touching anything real? Next: [Reading order](Reading-Order.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the arithmetic script, the namespace lab (link-local and SLAAC addresses, privacy extensions, neighbor discovery, a rogue router advertisement, a dual-stack listener, the IPv4-only firewall gap, the fix and the ICMPv6 trap) and the allowlist script were run on Linux; the PowerShell commands, the DigitalOcean, AWS and pfSense steps, and everything on a real network were not.** On **2026-10-22** the author ran every Bash and Python command in the free path on a Debian-based Linux machine (kernel 7.1.13, `ip` from iproute2 6.15.0, `nft` 1.1.3, `tcpdump`, Python 3.13.5) as an ordinary user, **rootless**, inside a throwaway `unshare -Urnmpf` shell, with no `sudo`. Output below is pasted from those runs and trimmed. Addresses that contain hex taken from a made-up MAC differ every run, so yours will not match digit for digit. **Not run:** every PowerShell command (no Windows machine and no PowerShell on the test machine; marked **est.**), any cloud step (no account was touched), the pfSense steps (read from Netgate's documentation only), and everything that needs a real IPv6 internet connection. Statistics on this page are snapshots read on 2026-10-22 and **they drift**; each one carries its URL and date in the [claims register](#claims-register).

> **Prerequisites.** [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) (CIDR, default deny, the `unshare` lab technique) and a terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)). A Linux machine or virtual machine with `python3`, `ip` (package `iproute2`), `nft` (`nftables`) and `tcpdump`. Windows learners run the lab in WSL 2 (**est.**; not tested). The reading and the exercises are free and always will be; the free path uses only your own computer. The optional own-account path (one cloud server) is described with its cost before anything else in that section. About three hours for the reading and the free exercises (est.).

## What you will be able to do

- Read an IPv6 address, shorten and expand it, and say what a `/64`, a `/56` and a `/48` are for, with the arithmetic done by a script.
- Tell link-local, unique local (ULA), global unicast, multicast and loopback addresses apart by their first digits.
- Explain how a machine gets an address without a server (SLAAC and router advertisements), what DHCPv6 adds, how neighbors find each other (neighbor discovery), and why a firewall that drops all ICMPv6 breaks IPv6.
- Explain privacy extensions, dual stack, Happy Eyeballs, and what "NAT is not a firewall" means.
- Say, with a source for each, why adoption is slow, separating what is documented from what is opinion.
- Say what this project does about IPv6 and why, and list everything that must change together to turn it on deliberately.
- Run, rootless on your own computer, a lab that assigns addresses by router advertisement, watches neighbor discovery, hijacks a default route with a rogue advertisement and then stops it, shows a dual-stack service stay open over IPv6 behind an IPv4-only firewall, and fixes it.
- Check whether an allowlist covers IPv6, and explain how an IPv4-only allowlist fails in both directions.
- Run Build, Break, Detect, Evade, Defend on a dual-stack host, then flip the board.

The maintainer's words for this topic (2026-10-22), unedited except for punctuation: "While IPv6 has been a thing for years, many companies are hesitant to adopt it, and even I haven't, for a myriad of reasons." And, on why a test from an IPv6 address would not work for him: "IPv6 probably doesn't work, as I have it disabled on pfSense." His reasons are in [their own section](#why-the-author-has-not-adopted-ipv6). The page does not call that choice a mistake. It tries to say what the documents say, and what each choice costs.

## What the wiki already says (and the gap)

I searched the wiki before writing this page. Nothing below repeats those lessons; it links them.

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| IPv4 subnets, CIDR, NAT, default deny | [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) | The same ideas for 128-bit addresses, and what NAT is and is not |
| The measured `ip6tables` hole (IPv4 rules, IPv6 wide open) and the ICMPv6 neighbor-discovery trap | [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md) (Exercises 2 and 3) | This page links it and does not repeat it; it adds the dual-stack listener and the address-family view of the same gap |
| `AAAA` records in one table row; "No `AAAA` unless you have IPv6 on the droplet" | [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) | Why that sentence is a security rule, and what must change before you add one |
| IPv6 prefixes and per-address limits | [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md#what-to-count-by) and [Behind a CDN](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) | What a `/64` is and where the prefix comes from |
| "IPv6 off" on the droplets and "IPv6 stays closed" | [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md#ipv6-off) and [Droplet hardening](Droplet-Hardening.md#ipv6-stays-closed) | The reasoning behind them, in a lesson a beginner can follow |

## First, the words

- **IPv4** addresses are 32 bits, written as four numbers (`192.0.2.10`). There are about 4.3 billion of them. **IPv6** addresses are 128 bits, written as eight groups of four hex digits separated by colons (`2001:db8:0:0:0:0:0:10`). RFC 8200 is the specification of the protocol ([claims register](#claims-register)).
- **`::`** stands for one run of all-zero groups, once per address: `2001:db8::10`. Leading zeros in a group can be dropped. **RFC 5952** says how to write one address a single canonical way (lowercase, shortest form), because the freedom in the older rules "has been causing problems for operators, system engineers, and users".
- **Prefix and prefix length.** `2001:db8:abcd:1::/64` means "the first 64 bits are the network; the rest name a machine on it". It is CIDR, as in the subnets lesson, with bigger numbers.
- **`/64`.** The standard size of one subnet (one LAN). RFC 4291 says that for most addresses the last 64 bits, the **interface ID**, are fixed at 64 bits. RFC 7421 analyzes that boundary and its advantages. A single `/64` holds 2^64 addresses, about 18 quintillion.
- **Link-local address** (`fe80::/10`). Valid on one cable (one link) only, never routed. Every IPv6 interface makes one for itself. It is how neighbors and routers talk before anything else is set up.
- **Unique local address, ULA** (`fc00::/7`, in practice `fd` followed by a random 40-bit value). Private, like `10.0.0.0/8`, but meant to be unique per site (RFC 4193). Not routed on the internet.
- **Global unicast.** The public, routable addresses. Today they are allocated from `2000::/3` (IANA's registry says so; **est.**, I did not fetch it). `2001:db8::/32` is reserved for documentation (RFC 3849), and this page uses it for every example.
- **Multicast** (`ff00::/8`). One packet to a group. IPv6 has no broadcast; `ff02::1` is "all nodes on this link" and `ff02::2` is "all routers on this link".
- **SLAAC**, stateless address autoconfiguration (RFC 4862). A machine builds its own address from a prefix a router announces, with no server keeping a list.
- **Router advertisement, RA** (ICMPv6 type 134). The router's announcement: "this prefix is on this link, and I can be your default router." **Router solicitation** (type 133) is a host asking for one.
- **Neighbor discovery, ND** (RFC 4861). IPv6's replacement for ARP, built from ICMPv6 messages: **neighbor solicitation** (who has this address?) and **neighbor advertisement** (I do, here is my hardware address).
- **DHCPv6.** A server hands out addresses or other settings, as DHCP does for IPv4. It can sit beside SLAAC. A home router also uses it for **prefix delegation**: your internet provider gives the router a whole prefix (often a `/56` or `/48`) to divide among your LANs.
- **Privacy extensions** (RFC 8981, which replaced RFC 4941). A machine makes extra, random, short-lived **temporary addresses** for outgoing connections, so one stable address does not follow it around.
- **Dual stack.** A machine or network running IPv4 and IPv6 side by side. **Happy Eyeballs** (RFC 8305) is how a client that has both tries them quickly one after the other and keeps the one that connects, so a broken IPv6 path costs a fraction of a second instead of a long timeout. **Address selection** (RFC 6724) is the rule list that picks which address to try first.
- **`AAAA` record.** The DNS record that maps a name to an IPv6 address (the `A` record does that for IPv4). It is pronounced "quad-A".
- **NAT66 and NPTv6.** Address translation for IPv6. Rarely wanted; covered below.
- **Dual-stack exposure.** A word for the central risk of this page: a service listening on both families, protected on one.

## The big picture, in one table

| Property | IPv4 | IPv6 |
|---|---|---|
| Address | 32 bits, `192.0.2.10` | 128 bits, `2001:db8::10` |
| One LAN | Often a `/24` (254 hosts) | A `/64` |
| How a host gets an address | DHCP, or by hand | SLAAC from router advertisements, DHCPv6, or by hand; usually several addresses at once |
| Finding a neighbor | ARP | Neighbor discovery (ICMPv6) |
| Private space | `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | ULA `fc00::/7` |
| Sharing one public address | NAT, carrier-grade NAT | Not needed; every device can have its own public address |
| Broadcast | Yes | No; multicast |
| Fragmentation by routers | Yes | No; only the sender fragments (RFC 8200) |
| Firewall tool | `iptables`, or `nft` table `ip` | `ip6tables`, or `nft` table `ip6`, or one `inet` table for both |

## Addressing in practice

**Where the numbers come from.** A provider gives a site a prefix. RFC 6177 (which replaced the earlier "always a `/48`" advice) says the size is an operational decision and that a site should get "significantly more than a single /64", with `/48`, `/56` and `/64` all discussed. A home might get a `/56` (256 LANs); an organization a `/48` (65,536 LANs). Inside the site you cut the prefix into `/64`s, one per LAN. Exercise 1 does that with a script.

**Why 64 and not smaller.** Both SLAAC (RFC 4862) and the standard interface ID (RFC 4291) assume the last 64 bits. SLAAC as specified builds an address from a 64-bit interface ID, so a subnet smaller than a `/64` does not work with it (**est.** from those texts); RFC 7421 is the document that analyzes the boundary. For a point-to-point link between two routers RFC 9099 mentions `/127` (RFC 6164) as an exception, to avoid a neighbor-cache attack.

**Several addresses per interface is normal.** A typical machine has a link-local address, one or more global addresses (a stable one and temporary ones), perhaps a ULA, and `::1`. NIST's guide (SP 800-119) says so too: an IPv6 interface "typically starts with" a loopback, a link-local, a unique local and a globally routable address. A script, a log parser or an allowlist that assumes "one machine, one address" is wrong in IPv6.

**How a machine picks one.** When it has a choice, RFC 6724 says which source and destination addresses to prefer, and RFC 8305 says how a client races them. A machine with a working IPv6 address will often prefer IPv6 to an IPv4 destination whose name also has an `AAAA` record.

## SLAAC, DHCPv6 and router advertisements

1. A machine brings its interface up and makes a **link-local address** from its hardware address or a random value, then runs **duplicate address detection**: it asks the link "does anyone have this?" (RFC 4862).
2. It sends a **router solicitation** to `ff02::2`. Routers answer, and also announce themselves on a timer, with a **router advertisement** to `ff02::1`.
3. The advertisement carries **options**: the prefix (with flags: *on-link* and *autonomous*), its lifetimes, whether to also ask a DHCPv6 server, the router's link-layer address, and a lifetime for the router as a default gateway.
4. For each prefix marked autonomous the host builds an address (prefix plus an interface ID) and, with privacy extensions on, a temporary one as well. The router's own link-local address becomes the **default gateway**. Note this: the gateway is a link-local address, and whoever sends the advertisement becomes it.
5. DHCPv6 is optional. The flags in the advertisement say "also use DHCPv6 for addresses" or "for other settings only". Without it nothing keeps a central list of who has what, which is why logs and inventories get harder (the security section returns to this).

**Why RFC 4861 says hop limit 255.** Every neighbor discovery message must arrive with an IPv6 hop limit of 255, so that it "could not possibly have been forwarded by a router". A packet from another network cannot have that value. This is a built-in defense against a remote attacker sending fake advertisements; it does nothing against someone on the same cable. That is the next section's first lesson.

### Exercise 1: prefix arithmetic with the standard library

Nothing here touches a network. Python's `ipaddress` module does the work.

**Predict.** How many `/64` networks fit in a `/48`? In a `/56`? What kind of address is `fd12:3456:789a::1`? What interface ID does the MAC `00:00:5e:00:53:01` produce?

**Do (Bash).** Make a folder first (`mkdir -p ~/ipv6-lab && cd ~/ipv6-lab`), then save the script:

`subnets.py`:

```bash
cat > subnets.py <<'LAB_EOF'
#!/usr/bin/env python3
# subnets.py - IPv6 prefix arithmetic with the standard library. No network.
# Every address is from the documentation block 2001:db8::/32 (RFC 3849) or is a
# unique-local example under fd00::/8 (RFC 4193). Nothing here is real.
import ipaddress
import secrets

site = ipaddress.ip_network("2001:db8:abcd::/48")  # what a site might be given
print("a /48 holds", 2 ** (64 - site.prefixlen), "separate /64 networks")
print("a /56 holds", 2 ** (64 - 56), "separate /64 networks")
print("one /64 holds", 2**64, "addresses (that is 4 billion times the whole IPv4 internet)")

lans = list(site.subnets(new_prefix=64))
print("\nfirst three /64s of", site)
for n in lans[:3]:
    print("  ", n, "  first host", n.network_address + 1)

host_net = lans[1]
print("\nthe /64 you would put one office LAN on:", host_net)
print("a scan at 1,000,000 probes a second needs", f"{2**64 / 1e6 / 3600 / 24 / 365:,.0f}", "years to walk it")

print("\nscopes by prefix (the first bits decide it):")
for text in ("fe80::1", "fd12:3456:789a::1", "2001:db8::1", "ff02::1", "::1", "::ffff:192.0.2.5"):
    a = ipaddress.ip_address(text)
    if a.is_link_local:
        kind = "link-local (this cable only)"
    elif a.is_multicast:
        kind = "multicast"
    elif a.is_loopback:
        kind = "loopback"
    elif a.ipv4_mapped:
        kind = "IPv4-mapped (an IPv4 client seen through an IPv6 socket)"
    elif a.is_private and text.startswith("fd"):
        kind = "unique local (ULA, private, not routed on the internet)"
    elif text.startswith("2001:db8"):
        kind = "documentation (never routed)"
    else:
        kind = "global unicast"
    print(f"  {text:<20} {kind}")

# A modified EUI-64 interface ID from a MAC (RFC 4291 appendix A): flip the U/L bit,
# put ff:fe in the middle. 00:00:5e:00:53:01 is from the documentation MAC range (RFC 7042).
mac = bytes.fromhex("00005e005301")
eui = bytes([mac[0] ^ 0x02]) + mac[1:3] + b"\xff\xfe" + mac[3:]
print("\nMAC 00:00:5e:00:53:01 makes the interface ID", ipaddress.IPv6Address(b"\x00" * 8 + eui).exploded[20:])
print("on", host_net, "that is", ipaddress.IPv6Address(int(host_net.network_address) | int.from_bytes(eui, "big")))

# A ULA prefix (RFC 4193): fd, then 40 random bits, then a 16-bit subnet ID. The random part
# makes two sites that later join their networks unlikely to collide. Yours differs each run.
gid = secrets.token_bytes(5)
ula = ipaddress.IPv6Network((b"\xfd" + gid + b"\x00\x00" + b"\x00" * 8, 64))
print("\na random ULA /64 for a lab (different every run):", ula)
LAB_EOF
```


```bash
python3 -I subnets.py
```

**Do (PowerShell, est.; needs Python 3 installed).**

```powershell
# est.: not run (no PowerShell on the test machine)
python -I .\subnets.py
```

**Check.** Output from the 2026-10-22 run (the last line differs every run because it is random):

```text
a /48 holds 65536 separate /64 networks
a /56 holds 256 separate /64 networks
one /64 holds 18446744073709551616 addresses (that is 4 billion times the whole IPv4 internet)

first three /64s of 2001:db8:abcd::/48
   2001:db8:abcd::/64   first host 2001:db8:abcd::1
   2001:db8:abcd:1::/64   first host 2001:db8:abcd:1::1
   2001:db8:abcd:2::/64   first host 2001:db8:abcd:2::1

the /64 you would put one office LAN on: 2001:db8:abcd:1::/64
a scan at 1,000,000 probes a second needs 584,942 years to walk it

scopes by prefix (the first bits decide it):
  fe80::1              link-local (this cable only)
  fd12:3456:789a::1    unique local (ULA, private, not routed on the internet)
  2001:db8::1          documentation (never routed)
  ff02::1              multicast
  ::1                  loopback
  ::ffff:192.0.2.5     IPv4-mapped (an IPv4 client seen through an IPv6 socket)

MAC 00:00:5e:00:53:01 makes the interface ID 0200:5eff:fe00:5301
on 2001:db8:abcd:1::/64 that is 2001:db8:abcd:1:200:5eff:fe00:5301

a random ULA /64 for a lab (different every run): fdff:afb6:975b::/64
```

Read it. A `/48` is 65,536 networks, so no site runs out of subnets. The "years to scan" line is the arithmetic behind a claim you will meet again, and the page's [security section](#scanning-is-harder-but-that-is-not-security) says what it does and does not prove. The interface ID from a MAC (called modified EUI-64) puts `ff:fe` in the middle and flips one bit; the MAC `00:00:5e:00:53:01` is from the range reserved for documentation (RFC 7042; **est.**: I did not fetch that RFC). The address `::ffff:192.0.2.5` will matter in Exercise 6.

**Undo.** Nothing to undo.

## Neighbor discovery, and why ICMPv6 must not be blocked wholesale

In IPv4, ICMP is a helpful extra that many firewalls drop wholesale with few ill effects. In IPv6, ICMPv6 is part of the plumbing. RFC 4890 opens by saying ICMPv6 is "essential to the functioning of IPv6" and that there are also "a number of security risks associated with uncontrolled forwarding" of it; its job is to tell you which messages to let through. The ones a host firewall must accept on the link for the host to work:

- **Neighbor solicitation and advertisement** (types 135 and 136): how a machine learns the hardware address of the next hop or the destination on its own link. Drop them and the machine cannot reach anything on its link, including its gateway.
- **Router solicitation and advertisement** (133, 134): how a host learns its prefix and gateway (unless you configure both by hand).
- **Packet too big** (type 2): routers do not fragment IPv6 packets (RFC 8200), so a path's size limit is discovered through these messages. Drop them and some connections stall after they start, which is a miserable bug to find.
- **Destination unreachable and time exceeded** (1 and 3): errors a client needs to fail fast.

The firewall rules in this repository's own host firewall accept the neighbor messages and the error types (see [Droplet hardening](Droplet-Hardening.md)); the [Packet filters](Packet-Filters-Compared-iptables-nftables-ufw-pf.md) lesson measured what happens without them. Exercise 5 does it again in this lab in one step.

## The lab: four pretend machines on one pretend switch

One pretend switch (`sw`, a Linux bridge) and four pretend machines on it: `rtr` (a router that will announce a prefix), `srv` (a server), `cli` (a client) and `evil` (a machine that will misbehave). They are network namespaces inside a throwaway shell you own. **Safety.** You are root only inside the pretend world (a user namespace). Nothing leaves it: the addresses are documentation ranges, and when you exit the shell every namespace, server and rule is destroyed. If `unshare -Urnm` fails with `Operation not permitted`, your distribution restricts unprivileged user namespaces; the fallback is `sudo unshare -nmpf --mount-proc bash` (you are then real root, and should type only what this page gives you; **est.**, not run).

Save these files in a folder of your own (`mkdir -p ~/ipv6-lab && cd ~/ipv6-lab`). `ra.py` sends one router advertisement, which is how you will play a router without installing a router daemon. It builds the ICMPv6 message by hand (RFC 4861 section 4.2) and lets the kernel fill in the checksum.

`ra.py`:

```bash
cat > ra.py <<'LAB_EOF'
#!/usr/bin/env python3
# ra.py IFACE PREFIX/64 [--lifetime SECONDS] [--high]
# Send ONE router advertisement (ICMPv6 type 134, RFC 4861 section 4.2) to the
# all-nodes group ff02::1 on IFACE, announcing PREFIX for SLAAC. Router lifetime
# 0 means "I am not a default router" (the prefix is still announced).
# Lab use only: run it inside your own network namespace.
import ipaddress
import socket
import struct
import sys

args = sys.argv[1:]
lifetime = 1800
flags = 0
if "--high" in args:  # router preference 'high' (RFC 4191): the default route from this sender wins
    flags = 0x08
    args.remove("--high")
if "--lifetime" in args:
    i = args.index("--lifetime")
    lifetime = int(args[i + 1])
    del args[i : i + 2]
iface, prefix = args
net = ipaddress.IPv6Network(prefix)
if net.prefixlen != 64:
    sys.exit("SLAAC needs a /64 (RFC 4862 via RFC 4291)")
# Header: type, code, checksum (the kernel fills it in), hop limit hint,
# flags (M and O clear: no DHCPv6; --high sets the preference bits), router lifetime, reachable time, retrans timer.
msg = struct.pack("!BBHBBHII", 134, 0, 0, 64, flags, lifetime, 0, 0)
# Option 3, prefix information: length 4 (units of 8 bytes), prefix length 64,
# flags L (on-link, 0x80) and A (autonomous address configuration, 0x40),
# valid lifetime 1 day, preferred lifetime 4 hours, 4 reserved bytes, the prefix.
msg += struct.pack("!BBBBIII", 3, 4, 64, 0xC0, 86400, 14400, 0) + net.network_address.packed
s = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_ICMPV6)
s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 255)  # RFC 4861: must arrive with 255
idx = socket.if_nametoindex(iface)
s.sendto(msg, ("ff02::1", 0, 0, idx))
print(f"sent RA on {iface}: prefix {net}, router lifetime {lifetime}s")
LAB_EOF
```


`lab-up.sh`:

```bash
cat > lab-up.sh <<'LAB_EOF'
#!/usr/bin/env bash
# lab-up.sh - one pretend switch and four pretend machines, inside YOUR shell.
# Run it inside:  unshare -Urnmpf --mount-proc bash
#   sw   = a switch (a bridge); the others plug into it
#   rtr  = a router that will announce a prefix
#   srv  = a server;  cli = a client;  evil = a machine that will misbehave
# Addresses: IPv4 192.0.2.0/24 (RFC 5737); IPv6 2001:db8:1:1::/64 (RFC 3849).
# They never leave this shell.
set -euo pipefail
mount -t tmpfs tmpfs /run && mkdir -p /run/netns          # private to this shell
ip netns add sw
ip -n sw link add br0 type bridge
ip -n sw link set br0 type bridge mcast_snooping 0         # a plain switch floods multicast
ip -n sw link set br0 up
for n in rtr srv cli evil; do
  ip netns add "$n"
  ip link add "p-$n" type veth peer name e0
  ip link set "p-$n" netns sw
  ip link set e0 netns "$n"
  ip -n sw link set "p-$n" master br0
  ip -n sw link set "p-$n" up
  ip -n "$n" link set lo up
  ip -n "$n" link set e0 up
done
ip -n rtr addr add 192.0.2.254/24 dev e0
ip -n rtr addr add 2001:db8:1:1::1/64 dev e0 nodad
ip -n srv addr add 192.0.2.1/24 dev e0
ip -n srv addr add 2001:db8:1:1::80/64 dev e0 nodad        # a server usually has a fixed address
ip -n cli addr add 192.0.2.10/24 dev e0
# Wait until the kernel has finished duplicate address detection on the link-local addresses.
for _ in $(seq 1 50); do
  if ! ip -n srv -6 addr | grep -q tentative && ! ip -n cli -6 addr | grep -q tentative \
     && ! ip -n rtr -6 addr | grep -q tentative && ! ip -n evil -6 addr | grep -q tentative; then break; fi
  sleep 0.2
done
echo "lab ready: rtr, srv, cli, evil on one switch. Try: ip -n cli -6 addr show dev e0"
LAB_EOF
```


`serve.py`:

```bash
cat > serve.py <<'LAB_EOF'
#!/usr/bin/env python3
# serve.py [--v6only] PORT [PORT ...] - answer every TCP connection with one line, then close.
# Default: ONE socket on "::" that also takes IPv4 clients (dual stack, IPV6_V6ONLY off).
# --v6only: the socket takes IPv6 only. A second program must listen for IPv4.
import socket
import sys
import threading

args = sys.argv[1:]
v6only = "--v6only" in args
ports = [int(a) for a in args if a != "--v6only"]


def serve(port):
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1 if v6only else 0)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("::", port))
    s.listen(16)
    while True:
        conn, peer = s.accept()
        conn.sendall(f"hello from port {port}, you are {peer[0]}\n".encode())
        conn.close()


for p in ports:
    threading.Thread(target=serve, args=(p,), daemon=True).start()
threading.Event().wait()
LAB_EOF
```


`probe.py`:

```bash
cat > probe.py <<'LAB_EOF'
#!/usr/bin/env python3
# probe.py ADDRESS PORT [PORT ...] - try each TCP port once and print one word:
#   open      the server answered
#   closed    something answered "refused" (a reset or an ICMP error)
#   filtered  silence until the timeout (what a drop looks like)
import socket
import sys

dst = sys.argv[1]
for port in (int(p) for p in sys.argv[2:]):
    fam = socket.AF_INET6 if ":" in dst else socket.AF_INET
    s = socket.socket(fam, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect((dst, port))
        banner = s.recv(80).decode().strip()
        word = f"open      ({banner})"
    except ConnectionRefusedError:
        word = "closed"
    except (socket.timeout, TimeoutError):
        word = "filtered"
    except OSError as e:
        word = f"error: {e.strerror}"
    finally:
        s.close()
    print(f"{dst:>22} port {port:<5} {word}")
LAB_EOF
```


`allowlist.py`:

```bash
cat > allowlist.py <<'LAB_EOF'
#!/usr/bin/env python3
# allowlist.py - "does this allowlist cover IPv6?" A toy, offline. No network.
# usage: allowlist.py ALLOW[,ALLOW...] CLIENT [CLIENT ...]
# ALLOW is a network or address. Documentation ranges only (RFC 5737, RFC 3849).
import ipaddress
import sys

allow = [ipaddress.ip_network(a) for a in sys.argv[1].split(",")]
clients = [ipaddress.ip_address(c) for c in sys.argv[2:]]


def naive(addr):
    """What a first draft does: ask each network whether it contains the address."""
    return any(addr in net for net in allow)


def careful(addr):
    """Unwrap an IPv4 client that arrived through a dual-stack IPv6 socket, then ask."""
    if addr.version == 6 and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return any(addr in net for net in allow)


print(f"{'client':<22}{'naive':<10}careful")
for c in clients:
    print(f"{str(c):<22}{'allow' if naive(c) else 'deny':<10}{'allow' if careful(c) else 'deny'}")

v4 = [n for n in allow if n.version == 4]
v6 = [n for n in allow if n.version == 6]
print()
print(f"allowlist has {len(v4)} IPv4 and {len(v6)} IPv6 entries")
if v4 and not v6:
    print("WARNING: IPv4 only. Under default-deny, IPv6 clients are locked out; under")
    print("         default-allow, every IPv6 client is outside the list and gets in.")
if v6 and not v4:
    print("WARNING: IPv6 only. Every IPv4 client is outside the list.")
wide = [str(n) for n in allow if n.prefixlen == 0]
if wide:
    print("WARNING: a /0 entry allows everything in that family:", ", ".join(wide))
LAB_EOF
```


Start the lab shell. `-p -f --mount-proc` gives it its own process list, so every server dies with the shell:

```bash
unshare -Urnmpf --mount-proc bash
cd ~/ipv6-lab
bash lab-up.sh
```

### Exercise 2: link-local first, then SLAAC, then privacy extensions

**Predict.** Before any router speaks, what IPv6 address will `cli` have, and where does it come from? After `rtr` sends one advertisement for `2001:db8:1:1::/64`, how many global addresses will `cli` have if you first turn privacy extensions on? What will its default gateway be?

**Do (Bash, in the lab shell).**

```bash
echo "--- before any router advertisement"
ip -n cli -6 addr show dev e0 | grep inet6
ip -n cli -6 route
echo "--- privacy extensions on for cli (value 2 = prefer temporary addresses)"
ip netns exec cli sysctl -qw net.ipv6.conf.e0.use_tempaddr=2
echo "--- rtr announces the prefix once"
ip netns exec rtr python3 ra.py e0 2001:db8:1:1::/64
sleep 3
ip -n cli -6 addr show dev e0 | grep inet6
ip -n cli -6 route
```

**Do (PowerShell, est.).** Not available: namespaces are a Linux feature. On Windows run the read-only commands in Exercise 7 on your own machine to see the same address types.

**Check.** Run on 2026-10-22; the hex digits come from random hardware addresses and differ every run:

```text
--- before any router advertisement
    inet6 fe80::bc86:b6ff:fe0e:ffa8/64 scope link proto kernel_ll 
fe80::/64 dev e0 proto kernel metric 256 pref medium
--- rtr announces the prefix once
sent RA on e0: prefix 2001:db8:1:1::/64, router lifetime 1800s
    inet6 2001:db8:1:1:226e:a7be:f303:6daa/64 scope global temporary dynamic 
    inet6 2001:db8:1:1:bc86:b6ff:fe0e:ffa8/64 scope global dynamic mngtmpaddr proto kernel_ra 
    inet6 fe80::bc86:b6ff:fe0e:ffa8/64 scope link proto kernel_ll 
2001:db8:1:1::/64 dev e0 proto kernel metric 256 expires 86398sec pref medium
fe80::/64 dev e0 proto kernel metric 256 pref medium
default via fe80::8009:57ff:fe66:891a dev e0 proto ra metric 1024 expires 1798sec hoplimit 64 pref medium
```

Read it line by line. Before the advertisement the kernel had already given `cli` a link-local address; look at it: `bc86:b6ff:fe0e:ffa8` is the interface's random hardware address with `ff:fe` in the middle (the modified EUI-64 shape from Exercise 1). After the advertisement `cli` has **two** global addresses on the same prefix: the **stable** one (same interface ID as the link-local; `mngtmpaddr` marks it as the one temporary addresses are managed from) and a **temporary** one with a random interface ID. Its default route is `via fe80::8009:...`, the router's **link-local** address, `proto ra`: learned from an advertisement, with a 1,798-second life that will count down. Nobody ran DHCP; no server holds a list. The prefix came from one packet.

Two things to take from it. First, **the address on the wire for outgoing connections is the temporary one**, which changes (RFC 8981 gives defaults of 2 days valid and 1 day preferred, user-adjustable). A log that records only the source address sees a different one after a day. Second, **the same prefix produced two usable addresses on one machine.** If you allowlist "the laptop's address" you must say which, or allow the prefix.

**Undo.** Stay in the shell; the next exercises build on it. Leaving the shell (`exit`) destroys everything.

### Exercise 3: neighbor discovery, watched

**Predict.** `cli` knows nothing about `srv`. When it first pings `srv`'s address, which two ICMPv6 messages will cross the wire before the echo request? Which multicast group will the question go to?

**Do (Bash, in the same shell).** Start a capture in `cli`, then ping (the `-Z root` option stops `tcpdump` from trying to drop to a user that does not exist in your pretend world):

```bash
ip -n cli neigh flush all
ip netns exec cli tcpdump -Z root -n -l -c 4 -i e0 icmp6 &
sleep 1
ip netns exec cli ping -6 -c1 -W2 2001:db8:1:1::80 > /dev/null
wait %1 2>/dev/null
echo "--- neighbor table"
ip -n cli -6 neigh
```

**Check.** Output from the run:

```text
IP6 fe80::e4f4:30ff:fe19:478d > ff02::2: ICMP6, router solicitation, length 16
IP6 2001:db8:1:1:3453:bfff:fef4:f1cd > ff02::1:ff00:80: ICMP6, neighbor solicitation, who has 2001:db8:1:1::80, length 32
IP6 2001:db8:1:1::80 > 2001:db8:1:1:3453:bfff:fef4:f1cd: ICMP6, neighbor advertisement, tgt is 2001:db8:1:1::80, length 32
IP6 2001:db8:1:1:3453:bfff:fef4:f1cd > 2001:db8:1:1::80: ICMP6, echo request, id 100, seq 1, length 64
--- neighbor table
2001:db8:1:1::80 dev e0 lladdr 4e:6f:4b:04:6a:ab REACHABLE
```

The first line is an unrelated router solicitation (a host asking "any routers here?"). Then the point: the question "who has `2001:db8:1:1::80`" went to `ff02::1:ff00:80`, a **solicited-node multicast address**. It is built from the last 24 bits of the address being asked about (`ff:00:80` here), so only machines whose address ends the same way even look at it, instead of every host on the link seeing a broadcast. The owner replied with a neighbor advertisement carrying its hardware address, and `cli` stored the pair in its neighbor table (`REACHABLE`). This table is the IPv6 equivalent of the ARP cache. An attacker who answers that question first can steal the traffic, which is why switches grow features to stop it (RFC 9099 section 2.3 discusses protections).

**Undo.** Nothing; the capture ended after four packets.

### Exercise 4: a rogue router advertisement, and how to stop it

**Predict.** `evil` has no special privilege on the link. If it sends a router advertisement for a different prefix, marked as a high-preference router, what will happen to the default routes and addresses of `cli`? What single setting on `cli` would have prevented it?

**Do (Bash, in the same shell).**

```bash
echo "--- routes before"; ip -n cli -6 route | grep -v '^fe80'
ip netns exec evil python3 ra.py e0 2001:db8:bad:1::/64 --high
sleep 3
echo "--- routes and addresses after the rogue advertisement"
ip -n cli -6 route | grep -v '^fe80'
ip -n cli -6 -o addr show scope global | awk '{print $4}'
echo "--- the fix on cli: stop accepting advertisements, then clear what was learned"
ip netns exec cli sysctl -w net.ipv6.conf.e0.accept_ra=0
ip -n cli -6 route flush proto ra
for a in $(ip -n cli -6 -o addr show scope global dynamic | awk '{print $4}'); do ip -n cli addr del "$a" dev e0; done
ip netns exec evil python3 ra.py e0 2001:db8:bad:1::/64 --high
sleep 2
echo "--- after another rogue advertisement (should print nothing below)"
ip -n cli -6 route | grep -v '^fe80' || true
ip -n cli -6 -o addr show scope global | awk '{print $4}'
```

**Check.** Output from the run:

```text
--- routes before
2001:db8:1:1::/64 dev e0 proto kernel metric 256 expires 86395sec pref medium
default via fe80::9c6c:6cff:fed4:390 dev e0 proto ra metric 1024 expires 1796sec hoplimit 64 pref medium
sent RA on e0: prefix 2001:db8:bad:1::/64, router lifetime 1800s
--- routes and addresses after the rogue advertisement
2001:db8:1:1::/64 dev e0 proto kernel metric 256 expires 86392sec pref medium
2001:db8:bad:1::/64 dev e0 proto kernel metric 256 expires 86396sec pref medium
default via fe80::9c6c:6cff:fed4:390 dev e0 proto ra metric 1024 expires 1792sec hoplimit 64 pref medium
default via fe80::63:5cff:fea4:461f dev e0 proto ra metric 1024 expires 1796sec hoplimit 64 pref high
2001:db8:bad:1:ec7:73a6:786d:2290/64
2001:db8:bad:1:5048:f6ff:fead:c296/64
2001:db8:1:1:8548:c362:401c:ef1f/64
2001:db8:1:1:5048:f6ff:fead:c296/64
--- the fix on cli: stop accepting advertisements, then clear what was learned
net.ipv6.conf.e0.accept_ra = 0
sent RA on e0: prefix 2001:db8:bad:1::/64, router lifetime 1800s
--- after another rogue advertisement (should print nothing below)
```

Read it. One packet from a machine with no special standing on the link (it only had to be plugged in) gave `cli` a **second default router**, marked `pref high` (RFC 4191 router preference), and a second address in a prefix the attacker chose. With the high preference, traffic that goes to the default route now goes to `evil`: it can read it, change it, or drop it. Nothing was hacked; the protocol did what it is built to do. RFC 6104 is the problem statement for rogue advertisements (accidental ones, like a laptop sharing its connection, are common too), and RFC 6105 describes **RA-Guard**, a feature of a managed switch that only lets advertisements in from ports where a router is expected. The hop-limit-255 rule from the SLAAC section did not help, because `evil` is on the same link. In the lab the fix is a host setting (`accept_ra=0`), right for a server with a fixed address and wrong for a laptop that needs advertisements to work at all.

**Undo.** `ip netns exec cli sysctl -w net.ipv6.conf.e0.accept_ra=1`, or leave the shell. Exercise 5 does the first for you, because `cli` now has no IPv6 route at all, which is also what "stop listening to advertisements" costs a machine that needs them.

### Exercise 5: a dual-stack service, the firewall gap, the fix, and the trap

This repeats the measured hole from the [packet filters lesson](Packet-Filters-Compared-iptables-nftables-ufw-pf.md) with a smaller setup, so you can see the address-family view of it. The first two commands turn advertisements back on for `cli` and send one again, so it has a global address and a route even if you skipped Exercise 2 or 4 (`srv` already has a fixed `2001:db8:1:1::80`).

**Predict.** `serve.py` listens on `::` with one socket; a second copy with `--v6only` listens for IPv6 only. Which of ports 80, 8080 and 8443 will answer over IPv4, and over IPv6? Then `srv` gets a default-deny firewall in an `ip` table that allows only port 80. What will port 8080 do over IPv4, and over IPv6? Then the same policy in an `inet` table with `cli` having forgotten `srv`'s hardware address: what happens to even port 80?

**Do (Bash, in the same shell).**

```bash
ip netns exec cli sysctl -qw net.ipv6.conf.e0.accept_ra=1   # undo Exercise 4's fix
ip netns exec rtr python3 ra.py e0 2001:db8:1:1::/64 > /dev/null; sleep 3
ip netns exec srv python3 serve.py 80 8080 &
ip netns exec srv python3 serve.py --v6only 8443 &
sleep 1
echo "--- what is listening"; ip netns exec srv ss -ltn
probe() { ip netns exec cli python3 probe.py "$@"; }
echo "--- no firewall"; probe 192.0.2.1 80 8080 8443; probe 2001:db8:1:1::80 80 8080 8443
echo "--- a firewall that only knows IPv4 (table family ip)"
ip netns exec srv nft -f - <<'RULES'
table ip lab4 {
  chain input {
    type filter hook input priority 0; policy drop;
    iif lo accept
    ct state established,related accept
    tcp dport 80 accept
  }
}
RULES
probe 192.0.2.1 80 8080; probe 2001:db8:1:1::80 80 8080
echo "--- the fix: one inet table covers both families"
ip netns exec srv nft delete table ip lab4
ip netns exec srv nft -f - <<'RULES'
table inet lab {
  chain input {
    type filter hook input priority 0; policy drop;
    iif lo accept
    ct state established,related accept
    tcp dport 80 accept
  }
}
RULES
probe 192.0.2.1 80 8080; probe 2001:db8:1:1::80 80 8080
echo "--- the trap: forget the neighbors and ask again"
ip -n cli neigh flush all; ip -n srv neigh flush all
probe 2001:db8:1:1::80 80
ip -n cli -6 neigh
echo "--- the repair: accept neighbor discovery and the error messages"
ip netns exec srv nft add rule inet lab input icmpv6 type '{ destination-unreachable, packet-too-big, time-exceeded, nd-neighbor-solicit, nd-neighbor-advert }' accept
ip -n cli neigh flush all
probe 2001:db8:1:1::80 80
```

**Check.** Output from the run (the source address in each banner is the client's and differs every run; trimmed to the part that matters):

```text
--- what is listening
State  Recv-Q Send-Q Local Address:Port Peer Address:Port
LISTEN 0      16              [::]:8443         [::]:*   
LISTEN 0      16                 *:8080            *:*   
LISTEN 0      16                 *:80              *:*   
--- no firewall
             192.0.2.1 port 80    open      (hello from port 80, you are ::ffff:192.0.2.10)
             192.0.2.1 port 8080  open      (hello from port 8080, you are ::ffff:192.0.2.10)
             192.0.2.1 port 8443  closed
      2001:db8:1:1::80 port 80    open      (hello from port 80, you are 2001:db8:1:1:e073:daff:fe4a:3d1c)
      2001:db8:1:1::80 port 8080  open      (hello from port 8080, you are 2001:db8:1:1:e073:daff:fe4a:3d1c)
      2001:db8:1:1::80 port 8443  open      (hello from port 8443, you are 2001:db8:1:1:e073:daff:fe4a:3d1c)
--- a firewall that only knows IPv4 (table family ip)
             192.0.2.1 port 80    open      (hello from port 80, you are ::ffff:192.0.2.10)
             192.0.2.1 port 8080  filtered
      2001:db8:1:1::80 port 80    open      (hello from port 80, you are 2001:db8:1:1:e073:daff:fe4a:3d1c)
      2001:db8:1:1::80 port 8080  open      (hello from port 8080, you are 2001:db8:1:1:e073:daff:fe4a:3d1c)
--- the fix: one inet table covers both families
             192.0.2.1 port 80    open      (hello from port 80, you are ::ffff:192.0.2.10)
             192.0.2.1 port 8080  filtered
      2001:db8:1:1::80 port 80    open      (hello from port 80, you are 2001:db8:1:1:e073:daff:fe4a:3d1c)
      2001:db8:1:1::80 port 8080  filtered
--- the trap: forget the neighbors and ask again
      2001:db8:1:1::80 port 80    filtered
2001:db8:1:1::80 dev e0 INCOMPLETE 
--- the repair: accept neighbor discovery and the error messages
      2001:db8:1:1::80 port 80    open      (hello from port 80, you are 2001:db8:1:1:e073:daff:fe4a:3d1c)
```

Read it in four steps.

1. **One socket, two families.** `ss` shows `*:80` and `*:8080` (dual stack: the one `::` socket also takes IPv4, which then shows up with the address written `::ffff:192.0.2.10`, an **IPv4-mapped** address) and `[::]:8443` (IPv6 only). So port 8443 answered `closed` over IPv4 and `open` over IPv6. That `::ffff:` form is the trap in Exercise 6.
2. **The gap.** The `ip` table is an IPv4 firewall. It dropped 8080 over IPv4, and said nothing about IPv6, so IPv6 8080 stayed `open`. The service did not change; the person who wrote the rule thought "firewall" meant "firewall for the address I was thinking about". This is exactly the "zero inbound is only true if IPv6 is closed too" reasoning in [Droplet hardening](Droplet-Hardening.md#ipv6-stays-closed).
3. **The fix.** One `inet` table sees both families. Both 8080 answers are now `filtered`.
4. **The trap.** The policy is default drop and port 80 is allowed, yet port 80 over IPv6 is `filtered` once the neighbor tables are empty. The table entry for `srv` is `INCOMPLETE`: `cli`'s neighbor solicitation reached `srv`, whose firewall dropped it, so `srv` never answered, and without a hardware address `cli` cannot send even the first packet. Accepting the neighbor and error messages repaired it. Do not add `echo-request` blindly either: RFC 4890 spends pages on which ICMPv6 types are safe to allow, from where.

**Undo.** `ip netns exec srv nft delete table inet lab`, or leave the shell.

### Exercise 6: does this allowlist cover IPv6?

An allowlist is a list of addresses allowed to reach something (a firewall source list, a CDN rule, an admin page). The question is not "is my address on it" but "what happens to a client the list never mentions". This script, offline, answers it for a list and some clients.

**Predict.** For the list `192.0.2.0/24,198.51.100.7`, will `2001:db8::9` be allowed? Will `::ffff:192.0.2.9` (an IPv4 client that reached a dual-stack server) be allowed by a first-draft check?

**Do (Bash; also runs in PowerShell as `python -I .\allowlist.py ...`, est.).** Outside the lab shell is fine.

```bash
python3 -I allowlist.py 192.0.2.0/24,198.51.100.7 192.0.2.9 2001:db8::9 ::ffff:192.0.2.9 ::ffff:203.0.113.5
python3 -I allowlist.py 192.0.2.0/24,2001:db8:1:1::/64 2001:db8:1:1::5 2001:db8:1:2::5 192.0.2.77
```

**Check.** Output from the run:

```text
client                naive     careful
192.0.2.9             allow     allow
2001:db8::9           deny      deny
::ffff:192.0.2.9      deny      allow
::ffff:203.0.113.5    deny      deny

allowlist has 2 IPv4 and 0 IPv6 entries
WARNING: IPv4 only. Under default-deny, IPv6 clients are locked out; under
         default-allow, every IPv6 client is outside the list and gets in.
client                naive     careful
2001:db8:1:1::5       allow     allow
2001:db8:1:2::5       deny      deny
192.0.2.77            allow     allow

allowlist has 1 IPv4 and 1 IPv6 entries
```

Read it. An IPv4-only list has two failure modes and both are silent. If the rest of the system is default-deny, every IPv6 client is refused, and the person who gets refused is whoever's network just gained IPv6 (a phone, a hotel, a new provider): an outage with no error to point at. If the rest of the system is default-allow, the list was never the control. The second block shows the cure: put a prefix for each family on the list and decide on purpose. The `naive`/`careful` columns show a subtler bug: a dual-stack server's socket reports an IPv4 client as `::ffff:192.0.2.9`. A check that asks "is this in `192.0.2.0/24`" gets "no" for an address that is in fact allowed, so a dual-stack deployment can start denying its own allowlisted IPv4 clients. Unwrap IPv4-mapped addresses before comparing.

**Undo.** Nothing.

### Exercise 7: look at your own machine (read-only; PowerShell and Bash)

Every command here only reads. They show what your machine does today; the output is yours and is not published.

```bash
# Bash (Linux; run on your own machine)
ip -6 addr show scope global       # global addresses; a temporary one is marked "temporary"
ip -6 route show default           # your default gateway, a link-local address
ip -6 neigh                        # your IPv6 neighbor table (ARP's cousin)
sysctl net.ipv6.conf.all.disable_ipv6 net.ipv6.conf.all.accept_ra
```

```powershell
# PowerShell on Windows (est.: not run)
Get-NetIPAddress -AddressFamily IPv6 | Select-Object InterfaceAlias, IPAddress, PrefixLength, PrefixOrigin, SuffixOrigin
Get-NetRoute -AddressFamily IPv6 -DestinationPrefix '::/0'
Get-NetNeighbor -AddressFamily IPv6 | Select-Object InterfaceAlias, IPAddress, State
```

**Check.** If you see only `fe80::` addresses, your network is not giving your machine a global IPv6 address, which is the common case at home when the router has IPv6 turned off (the [next section](#if-ipv6-is-disabled-on-your-router-as-the-maintainers-pfsense-has-it) is for you). If you see global addresses, you are dual stack today and the rest of the page applies to you.

**Undo.** Nothing.

When you are done with the lab, `exit` the `unshare` shell. Every namespace, server, rule and address is gone.

## NAT66, no NAT, and what "NAT is not a firewall" means

In IPv4, one public address is shared by many private machines, and the router that does the sharing (NAT) keeps a table of who asked what. A side effect: a packet from the internet that matches no table entry has nowhere to go and is dropped. People noticed the side effect and began to call it security.

RFC 4864 (*Local Network Protection for IPv6*, 2007) takes that belief apart. It says IPv4 NAT "was not developed as a security mechanism" and, "despite marketing messages to the contrary", is not one. It also says that the real protection behind NAT is **stateful filtering** (allow replies to connections that started inside; drop unsolicited packets from outside), and that IPv6 gateways can do that without translating any address. RFC 6092 (2011) turns the idea into recommendations for home and small-office routers and is careful about the cost: "there is a constructive tension between the desires of users for transparent end-to-end connectivity on the one hand, and the need for local-area network administrators to detect and prevent intrusion by unauthorized public Internet users on the other." NIST's guide (SP 800-119, 2010) says IPv4 NAT "is often deployed as a security control, a function it was explicitly not intended to perform", and adds that the opinion "is widely stated in IETF documents, and it continues to be a point of controversy". Read the three together and the message is this: **whatever protected you under NAT was the stateful default-deny rule, and you must write it for IPv6 yourself**, because a network of public addresses has no translation table to do it by accident.

IPv6 has translation tools for special cases. **NPTv6** (RFC 6296) swaps one prefix for another without touching the rest of the address, for example to keep internal addresses stable when a provider changes the prefix. **NAT66**, translating addresses and ports as IPv4 NAT does, exists in some products but is not the recommended design; Netgate's pfSense documentation says "the best practice is to allow IPv6 traffic to pass without performing any address or port translation" and that IPv6 removes "almost any need" for translation, with multi-WAN as a rare exception. **NAT64** is a different thing: it lets IPv6-only clients reach IPv4-only servers.

## Security implications

These are the ones that matter for someone who runs a small system. Each is an operational cost, not a reason by itself to avoid IPv6. RFC 9099 (*Operational Security Considerations for IPv6 Networks*, 2021) is the document to read next.

### A dual stack silently exposes what only one family firewalled

You saw it in Exercise 5. RFC 9099 puts it plainly: on a dual-stack network "the network operator has twice the exposure. One needs to think about protecting both protocols now." The common causes: a server that listens on `::` when you thought it listened on IPv4; a cloud setting that adds an IPv6 address by default; a firewall written for IPv4 only; a console form whose source field is pre-filled with both families (DigitalOcean's firewall documentation says the inbound Sources field "is pre-populated with All IPv4 and All IPv6", retrieved 2026-10-22). The defense is dull: one firewall table for both families, default deny, and a test that probes both.

### Scanning is harder, but that is not security

A `/64` has 2^64 addresses. RFC 4864 worked out that a scan at 40 Gbps would need "over 5,000 years" for one, and Exercise 1 printed 584,942 years at a million probes a second. If an attacker had to try every address, that would be the end of it. They do not have to. RFC 7707 (*Network Reconnaissance in IPv6 Networks*) exists because "it is widely assumed" that scanning is unfeasible, and it analyzes why that assumption is weaker than it looks: people who choose addresses by hand tend to pick patterns such as low-byte addresses (`2001:db8::10`), addresses with an embedded IPv4 address, or addresses that embed the service port (`2001:db8::80`), and the RFC measures how common such patterns were in the data it studied. It also has a chapter on learning addresses from DNS and on other places addresses leak (est. for anything beyond DNS: I read its table of contents, not every chapter). RFC 9099 notes that scientific work "makes scanning for IPv6-reachable nodes more feasible than expected". So: the huge space helps against blind worms, and is **not** a substitute for a firewall. Hiding behind an unguessable address is security by obscurity in the plain sense: the secret is the address, and addresses leak. This also works in your favor in one way: random interface IDs from privacy extensions, and DHCPv6 servers that issue addresses randomly from a large pool (RFC 9099 reports that RFC 7707 recommends this), make the pattern-guessing described above cost the scanner something.

### Extension headers and fragmentation

IPv6 packets can carry **extension headers** (hop-by-hop options, routing, fragment, destination options) between the main header and the payload (RFC 8200). Firewalls have to walk the chain to find the real protocol. Packets can be built so the chain is long, odd, or fragmented so that the firewall cannot see the port it is meant to filter. The documents say what to do: RFC 7112 updates the specification so that the first fragment must contain the entire header chain, so a filter can see it, RFC 9288 (2022) gives advice on dropping packets with particular extension headers at transit routers, and RFC 6092 says home gateways must not forward packets carrying the deprecated type 0 routing header. A host firewall such as `nft` handles the common cases for you; the practical point is to keep the firewall software patched and to know that "it matches the port" assumes the firewall understood the packet. Fragmentation also moves: routers do not fragment IPv6 packets (RFC 8200); the sender does, and the "packet too big" message tells it when. That is one more reason to accept that ICMPv6 message.

### Rogue router advertisements and neighbor spoofing

Exercise 4. Anyone on the link can become the gateway. RFC 9099 section 2.3 (Link-Layer Security) is about securing neighbor discovery on a managed network; RFC 6105 describes RA-Guard and calls the canonical solution, Secure Neighbor Discovery, "non-trivial to deploy". On a small network the realistic list is short: do not run unmanaged switches in front of things you care about, set `accept_ra=0` on servers with fixed addresses, and watch for a second default router. This risk exists whether or not your router has IPv6 turned off: a machine on your LAN can send advertisements, and your devices keep their link-local addresses. Turning IPv6 off at the router, as the next sections discuss, does not turn it off inside the LAN.

### Tooling, logging and the things keyed to an address

- **Logs.** The same address can be written several ways: RFC 9099 shows `2001:DB8::1`, `2001:0db8::0001` and others, recommends the single canonical form of RFC 5952 everywhere, and tells you to post-process logs that cannot comply. A search for the text you typed will miss the other spellings.
- **Many addresses per machine.** Privacy extensions rotate the address that appears in your logs (RFC 8981: valid for up to 2 days, preferred for up to 1 day, by default). RFC 4864 lists that short life as a *benefit* ("the node will not respond to the address once its lifetime becomes invalid") and NIST warns it can be hard for ingress filtering to tell temporary addresses from spoofed in-prefix addresses. For an operator it is both: harder to attack a moving target, harder to say which machine did something last Tuesday unless you also log which prefix, which MAC or which DHCPv6 lease.
- **Inventories and monitoring.** With SLAAC no server keeps the list of who has what; the neighbor tables of your routers and switches are the inventory. If your asset list, vulnerability scanner or monitoring only knows IPv4 addresses, IPv6 hosts are invisible to it.
- **Allowlists** that name only IPv4 (Exercise 6), and **rate limits** that key on one address. A person with a `/64` has 2^64 addresses, and a per-address limit (a `/128`) counts each as a stranger. The [rate limiting lesson](Rate-Limiting-at-Every-Layer.md#what-to-count-by) measured it: counting each IPv6 address alone blocked none of 600 requests from one `/64`; grouping by `/64` stopped 540 of them. The same prefix-versus-address question applies to [CDN real-IP lists](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md): Cloudflare publishes IPv6 ranges (7 on 2026-10-22, as that lesson counted) as well as IPv4 ones, and a firewall that trusts only the IPv4 ranges does the wrong thing for IPv6 traffic.
- **Reputation and geography.** Address blocks, blocklists, reputation scores and geolocation data for IPv6 are younger and coarser than IPv4's (est.; I did not read a source for how much; the CDN lesson's section on why an IP is a weak identifier applies with more force).

## Why adoption is slow

Each reason below is labeled **documented** (a primary source says it, cited in the claims register) or **opinion** (commonly said; not established by a source I read). Both kinds can be right. The labels are there so you know which is which.

### How far it has come: the numbers

All figures are read on **2026-10-22** and **they drift**: they change daily, differ by method, and differ by who is measured. Do not quote them without the date.

- **Google** publishes the share of users who reach Google over IPv6. Its data file for the statistics page ends on 2026-10-20 with **45.6 percent**. The same series on 20 October of earlier years: about **1.0 percent** (2012), **11.6** (2016), **29.4** (2020), **44.9** (2024), **44.1** (2025). Between 11 and 20 October 2026 the daily figure moved between about 45.6 and 51.0 percent, and the two highest days were a Sunday (11th) and a Saturday (17th); I did not read a source for why, and the usual explanation, more traffic from homes at weekends, is **opinion**. Note what the later part of the series says: growth from 2024 to 2026 is flat or slightly down at this measuring point.
- **APNIC** Labs measures it differently (through advertisements, not users of one service). For its 30-day window ending 2026-10-21 it reports the **world** at **43.64 percent "IPv6 capable"** and **40.74 percent "IPv6 preferred"**, from 945,719,606 samples. By country in the same snapshot, capable/preferred: India 76.18/73.43, France 85.77/84.79, Germany 72.62/70.43, United States 62.41/60.04, China 48.63/39.25. "Capable" and "preferred" are APNIC's terms; I did not read its method page, so what exactly they test is **est.**
- **Cloudflare Radar** also publishes adoption figures. The page returned HTTP 403 to a plain `curl` on 2026-10-22, and I did not work around that, so **no Cloudflare Radar figure is quoted**. Look at it yourself.
- Netgate's pfSense documentation, in its IPv6 introduction, says "it's been rather slow with only 8% of Google users having IPv6 connectivity by July 2015 and slightly over 40% of users in 2022". It agrees with the Google series above.

Two cautions. These are measurements of *users reaching big websites*, not of enterprise networks, internal systems or servers. And a country figure is not a company figure: a country can be high because a few mobile carriers are IPv6-only while its offices are not.

### The commonly cited reasons

| Reason | What is said | Status |
|---|---|---|
| **Dual-stack operating cost and complexity** | Running two stacks means twice the firewall rules, logs, monitoring and tests, and "twice the exposure". | **Documented.** RFC 9099 section 2.7.1: dual stack is "often the first deployment choice", with "added complexities" and twice the exposure. |
| **Staff skills and training** | Teams know IPv4 well, and IPv6 differs enough (SLAAC, ND, many addresses) to need retraining. | **Documented.** RFC 7381 section 2.3: "Many organizations falter in IPv6 deployment because of a perceived training gap." NIST SP 800-119 advises encouraging "staff to increase their knowledge of IPv6". |
| **Security tooling and appliance gaps** | Some firewalls, scanners, SIEMs and appliances handle IPv6 worse than IPv4 or not at all. | **Mixed.** The narrow claim that logs and tools must cope with new address spellings is documented (RFC 9099, RFC 5952). How common a missing feature is today in any given product is **opinion**; check your own products. |
| **ISP and device support** | Not every provider offers IPv6 to customers, and some devices handle it badly. | **Documented in vendor guides.** DigitalOcean: "Not all ISPs offer IPv6 addresses for customers". Netgate: "it is up to ISPs to start delivering IPv6 connectivity". Which devices are bad is **opinion**. |
| **Address-based habits and allowlists** | People remember, type and filter on IPv4 addresses; allowlists, scripts, rules and runbooks hard-code them. | **Opinion** as a cause of slow adoption. The mechanics are documented here: RFC 5952 on text forms, and Exercise 6. |
| **Perceived lack of need (NAT and CGNAT)** | NAT stretched the IPv4 supply and carrier-grade NAT stretched it more, so nothing forced a change. | **Documented** that NAT amplifies the address space (RFC 4864) and that carrier-grade NAT shares one address among customers (NIST SP 800-119 section 6.5.10.2). That this is why *a given organization* waits is **opinion**. |
| **No forcing event** | IANA's free pool ran out on 31 January 2011 (Netgate's page says so), but the regional registries kept allocating and IPv4 stayed available, at a rising price. | The date is **documented** by Netgate. "No forcing event" as an explanation is **opinion**. |
| **Vendor and application gaps** | One missing IPv6-capable component in a chain stops the move. | **Opinion.** The US federal memo below is related evidence that barriers were expected: it speaks of helping agencies "overcome barriers" to IPv6-only (OMB M-21-07). |
| **Chicken and egg** | Content providers wait for users; users wait for content. | **Documented** as Netgate's wording ("a catch-22 situation"); how much it still matters is **opinion**. |

### The counter-trend

- **Cost of IPv4.** AWS announced that from **1 February 2024** it charges **$0.005 per public IPv4 address per hour**, attached or not, and says "the cost to acquire a single public IPv4 address has risen more than 300% over the past 5 years" and that it hopes customers will think about "accelerating your adoption of IPv6". That is about $3.65 for a 730-hour month per address (est.; my arithmetic, not a vendor figure). The announcement is dated; prices change, so read the current page before you rely on it.
- **Government.** A US Office of Management and Budget memo, **M-21-07 of 19 November 2020**, directs federal agencies to make all new networked systems IPv6-enabled by the end of fiscal year 2023, and sets targets that at least **20 percent** of IP-enabled assets be IPv6-only by the end of FY2023, **50 percent** by FY2024 and **80 percent** by FY2025. I read the memo. **I did not check whether agencies met those targets** (est.: unknown to me).
- **Cloud defaults and discounts.** Clouds now offer IPv6 on their networks. DigitalOcean's documentation says IPv6 on a Droplet is available "at no additional cost" (bandwidth charges apply, because all IPv6 traffic uses the public interface); AWS's VPC guide says a VPC "can operate in dual-stack mode". Offered is not the same as used.
- **Mobile carriers and large content networks** are often cited as the places IPv6 is the norm. I did not read a carrier or content-network source for this page, so it is **opinion** here, not a documented finding. APNIC's per-network pages are the place to check.

## Why the author has not adopted IPv6

The maintainer of this project has not turned IPv6 on at home or in this project. These are his own words (2026-10-22), with only grammar fixes, and they are his view, not the page's finding:

> "While v6 fixes IP exhaustion, the format is hard to remember, and it was designed around the idea that every single device can have its own IP address directly, and it becomes harder to secure traffic."

> **Context box (what the documents say; it does not argue with him).** Read on 2026-10-22; sources in the [claims register](#claims-register). His view is a legitimate operational one and many organizations act on it. The documents below list the same points as design considerations. None of them says "never adopt IPv6", and none says "IPv6 is as easy to run as IPv4 on day one".
>
> - **"The format is hard to remember."** The standard answer is that people use names, not addresses, and `AAAA` records and DNS carry the long form. Where that stops being enough is exactly where operators work: firewall rules, log searches, allowlists, ACLs and ticket notes contain literal addresses. RFC 5952 (*A Recommendation for IPv6 Address Text Representation*, 2010) is the written attempt to reduce the ambiguity: it says the flexibility of the older rules "has been causing problems for operators, system engineers, and users" and defines one canonical text form. RFC 9099 asks operators to use that form in logs because one address can otherwise be written many ways. Exercise 1 and the `ipaddress` module normalize an address for you, which helps a script and does not help a person reading a rule at 3 a.m. The cost is real; the documents treat it as a handling problem, not a reason to avoid IPv6.
> - **"Every single device can have its own IP address directly."** That is the design. RFC 4291 defines an address space where every interface can have a global unicast address, and RFC 2775 (*Internet Transparency*, 2000) describes end-to-end connectivity and transparency as an architectural aim, with firewalls and address translation named among the causes of lost transparency (that RFC says it "refrains from making recommendations"). What it implies for exposure is stated in RFC 4864 section 4.2: "The vulnerability of an IPv6 host directly connected to the Internet is similar to that of an IPv4 host. The use of firewalls and Intrusion Detection Systems (IDSs) is recommended for those that want boundary protection in addition to host defenses." In other words, with IPv4 NAT in practice and with IPv6, what stands between a device and the internet is a stateful, default-deny edge filter. RFC 4864 and NIST SP 800-119 both say NAT is not a security mechanism, and NIST adds that the opinion "continues to be a point of controversy". RFC 6092 (CPE recommendations) and RFC 4864 describe "simple security" for gateways: stateful filtering, with the "constructive tension" quoted earlier between end-to-end connectivity and keeping intruders out. Whether the gateway you own ships with that filter on by default is a product question I did not test (**est.**).
> - **"It becomes harder to secure traffic."** The documents name the same costs: per-device addressability, so mistakes expose individual machines; privacy extensions that change host addresses (RFC 4941, replaced by RFC 8981), which complicate anything keyed to an address; a larger scan space that helps but is not obscurity you can rely on (RFC 7707, RFC 9099); and host-level controls and logs keyed to IP that get harder (RFC 9099 section 2.6.1.1 describes the logging side; NIST SP 800-119 notes the ingress-filtering side with temporary addresses). RFC 9099 also says that on dual stack the operator has twice the exposure. NIST SP 800-119 (December 2010) goes further than a caution: for "organizations that are not yet deploying IPv6 globally" it recommends to "block all IPv6 traffic, native and tunneled, at the organization's firewall", to "disable all IPv6-compatible ports, protocols and services on all software and hardware", and to "begin to acquire familiarity and expertise with IPv6, through laboratory experimentation and/or limited pilot deployments". That is a 2010 recommendation, and it is dated; RFC 7381 (2014) and OMB M-21-07 (2020) lean the other way. But it shows that blocking IPv6 while you build skills is a documented, conventional position, not an oversight.
>
> What follows from that, for this page: the project keeps IPv6 closed and tested, and treats "turn it on" as a deliberate change with its own checklist, below. That is consistent with the maintainer's view and with the documents.

## What this project does, and why

**IPv4 only, by design.** The project's network is IPv4. The reasons, from the repository's own pages:

- **"Zero inbound" has to be true in both families.** [Droplet hardening](Droplet-Hardening.md#ipv6-stays-closed) says so: "Zero inbound is only true if IPv6 is closed as well." Nothing in the project needs IPv6.
- **An address family that is not configured cannot be misconfigured.** [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md#ipv6-off) says that, and keeps `::/0` in the outbound rules so that turning IPv6 on later does not silently widen anything.
- **The cost gate and the egress rules assume IPv4.** The AWS VPC module's own comment says "IPv6 stays off: the egress rules and the cost gate assume IPv4 only".

**What stops it from drifting.** `tests/test_ipv6_closed.py` reads every resource block in `modules/` and `stacks/` offline and fails the build if: a DigitalOcean droplet does not state `ipv6 = false`; a DigitalOcean firewall's inbound `source_addresses` or an AWS security-group ingress rule has an IPv6 source; an AWS VPC or subnet is given IPv6 settings; an instance asks for IPv6 addresses; or an IPv6 association or egress-only internet gateway resource exists. It proves what the repository declares, not what a cloud account shows. Its limits are stated in its own docstring: outbound `::/0` is allowed on purpose, and a `::/0` that reaches an inbound rule only through a `locals` value is not followed (the attribute must be a literal, so a reference fails as unprovable). `scripts/zero_ports_check.py` fails closed too: it raises an error if a droplet has a public IPv6 address, and it probes the IPv4 address only. The host firewall that the connectors use is an `inet` table that accepts the ICMPv6 neighbor-discovery messages, for the reason you saw in Exercise 5, and the connector's bootstrap turns off IPv6 redirects and source-routed packets.

So the answer to "why would an IPv6 source address not work for the maintainer" has two layers. His pfSense has IPv6 turned off, so his network does not give his devices a global IPv6 address, and nothing on the project's side listens on IPv6 either.

## Turning it on deliberately: everything that must change together

If you decide a service of your own needs IPv6, treat it as a change with a checklist, not a checkbox. Steps marked **est.** were read in documentation and not run.

1. **Decide what and why.** Which hosts, which ports, which users need it. Write down who owns the change and how you roll it back. For this project, that also means a reviewed change to `tests/test_ipv6_closed.py` (relax only the rule that requires `ipv6 = false` for the specific resource, keep the inbound-source rules) and to the cost and egress assumptions above; do not delete the test.
2. **Cloud address.** DigitalOcean: tick **Enable IPv6** when creating the Droplet (the networking is configured for you), or for an existing Droplet power it off first, enable IPv6 in the control panel, then configure the interface by hand in its network configuration (address, `/64`, gateway); the docs say you cannot safely test the syntax over the SSH session you are using. The Droplet gets 16 addresses. **est.** (read 2026-10-22, not run). AWS: a VPC "can operate in dual-stack mode"; there is "no migration path from IPv4-only subnets to IPv6-only subnets", so adding IPv6 to an IPv4-only subnet means a dual-stack subnet. **est.**
3. **Firewalls, both families, in every layer.** The cloud firewall: DigitalOcean's console pre-fills inbound Sources with both families, so a rule you meant for IPv4 covers IPv6; check each rule. The host firewall: one `inet` table, default deny, and an `ip6 saddr` form of every `ip saddr` allow rule (an SSH rule that names only an IPv4 source does nothing for IPv6, which locks you out of IPv6 and, if the policy is allow, opens it). Keep the ICMPv6 accepts.
4. **DNS.** Add an `AAAA` record only after the service answers correctly over IPv6 from outside. [The DNS lesson](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) says "No `AAAA` unless you have IPv6 on the droplet", and that is a rule for the order of work. Behind a proxy such as Cloudflare, a proxied name answers with the proxy's addresses; the origin's own family matters for the lock that restricts the origin to the proxy (next item).
5. **Origin locks and allowlists.** Add the CDN's IPv6 ranges next to its IPv4 ones wherever you allowlist it ([the CDN lesson](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) fetches both lists), add your own admin prefixes, and run `allowlist.py` against the list. Decide what IPv6 clients see when they are not on it.
6. **Rate limits.** Key IPv6 by prefix (`/64`, or `/56` for a home), not by single address ([rate limiting](Rate-Limiting-at-Every-Layer.md#what-to-count-by)). Re-test with a client holding many addresses.
7. **Logging and detection.** Make logs record IPv6 in the canonical form (RFC 5952), make parsers, SIEM fields and fail2ban-style tools accept it (the rate limiting lesson's register notes fail2ban's IPv6 support since version 0.10), and record the prefix or the MAC for privacy-extension hosts. Re-run your detection rules against sample IPv6 events.
8. **Monitoring and checks.** Probe from outside over both families, and check the project's own port check: `scripts/zero_ports_check.py` refuses to run when a droplet has a public IPv6 address and tests IPv4 only, so you need a second, IPv6 check. Add IPv6 to inventories and vulnerability scans.
9. **Reverse DNS.** Mail servers and some logs rely on `PTR` records, which for IPv6 live under `ip6.arpa`. Whether and how your provider sets them for IPv6 is not something I read (**est.**).
10. **Privacy extensions and address selection.** Know which address your server uses for outgoing connections to others; decide whether a server should use temporary addresses (usually not; est.).
11. **Test and roll back.** From a network that has IPv6, `curl -6 https://your-name.example.com` should work and from a network that does not, `curl -4` should still work; a `curl -6` to a closed port should fail. The rollback is: delete the `AAAA` record first (clients stop trying IPv6 after the record's TTL expires), then remove the firewall rules, then the address.
12. **Cost.** IPv6 on DigitalOcean has no extra charge but bandwidth is billed (their IPv6 pricing page); on AWS, IPv6 can reduce the number of public IPv4 addresses you pay $0.005 an hour for.

If you do all twelve, you have a dual-stack service that you can reason about. If you skip the third, you have the hole from Exercise 5.

## If IPv6 is disabled on your router (as the maintainer's pfSense has it)

This is the situation the maintainer described. What it means depends on what "disabled" means, and on pfSense that is not one thing.

- **What pfSense's setting does.** Netgate's documentation for the advanced networking page describes an **Allow IPv6** option under System > Advanced > Networking: unchecked, "the firewall will block all IPv6 traffic", and it notes that the option "does not disable IPv6 functions or prevent IPv6 from being configured, it only controls traffic flow using internal firewall rules". There is also the choice of not configuring IPv6 on the WAN interface at all, in which case the router never gets a prefix to give your LAN. I do not know which of these the maintainer used, and the page does not guess. Whichever it is, the result is the same for a client on his LAN: no global IPv6 address, or no path to use one.
- **What your devices still do.** They keep link-local addresses and may still talk IPv6 on the LAN (printers, phones, anything using multicast discovery). A machine that sees a rogue advertisement on the LAN (Exercise 4) can still be steered. "IPv6 is off at the router" means no IPv6 to and from the internet; it does not mean no IPv6 inside.
- **What clients do.** With only IPv4 available, a client that gets both an `AAAA` and an `A` answer tries IPv6, finds it unusable and falls back to IPv4. Happy Eyeballs (RFC 8305) is designed to make that cheap, so it should cost little; badly behaved software can still pause. Netgate's guide documents a related option ("Prefer IPv4 over IPv6") for the firewall's own traffic.
- **Why an IPv6 source "would not work" for him.** Two separate reasons, easy to confuse. First, **his own network cannot originate IPv6**, so any test of "does my service work over IPv6" from home fails, and he cannot tell a broken service from a missing path. Second, **the project's side has no IPv6 listener**: the droplets have none and the firewalls are closed. If a service he reaches has an allowlist of his home IPv4 address, a connection from another network (a phone on mobile data, a hotel) may arrive from an IPv6 address that the list does not mention. That is exactly the Exercise 6 failure.
- **What to do about it, if you are in the same position.** Test from a different vantage point: a phone on mobile data, or a cloud machine of your own with IPv6 (see the next section), is how you learn what a visitor with IPv6 would see. Keep your own allowlists honest about both families. Decide what you want to say when someone asks "is it IPv6 ready": "not yet, by design, and here is the test that keeps it closed" is a perfectly good answer.
- **Read-only checks** on your own machine: Exercise 7. From a machine whose network has IPv6, `curl -6 -m 5 -I https://example.com` (one request to a reserved example domain; **est.**, not run) will succeed or fail depending on whether that path works.

## Optional: your own cloud machine with IPv6 (own-account path)

This path is optional and uses your own account. It is separate from the project's stacks and is **not approved** in `docs/stages/approved.json`; do not apply it with the project's pipelines. Everything above is free and local.

> **Cost box. Read this before you create anything.**
>
> **What is estimated.** Every dollar figure here comes from `docs/cost-prices.json`, retrieved 2026-10-21, for DigitalOcean's regular droplets. Prices change; check your provider's page before you build. Anything marked est. is my arithmetic or a guess, not a vendor figure.
>
> **If you forget it.** With the one droplet in the table left running, the bill is about **$0.20 a day and $6 a month** (est., $6 divided by 30). A machine that is powered off is still billed; only destroying it stops the bill.
>
> **Not covered by this estimate.** Bandwidth (DigitalOcean's IPv6 pricing page says IPv6 itself costs nothing extra but "bandwidth charges apply"), a domain name, snapshots, backups, anything you create outside these steps.
>
> **A spend alert is not a spending cap.** It sends an email; it does not stop anything. Set one before you build and see [How money works in the cloud](How-Money-Works-in-the-Cloud.md#1-a-billing-alert-before-anything-else).
>
> **Teardown first.** Read the teardown steps below before you run anything, and set a reminder for the time you plan to destroy. Destroy in the reverse of the build order.
>
> **You can stop at any piece.** Each piece works and teaches on its own. Exercises 1 to 7 above cover the same ideas for $0.

| Piece | Depends on | Cost per hour | Cost per month | Build order | Destroy order | Teardown proof |
|---|---|---|---|---|---|---|
| `droplet-ipv6`: one `s-1vcpu-1gb` droplet created with IPv6 on | none | about $0.009 (**est.**, $6 divided by 672, the provider's monthly cap; not a vendor rate) | $6 | 1 | 3 | `doctl compute droplet list --format ID,Name` shows no such droplet (**est.**, not run) |
| `cloud-firewall`: a firewall with no inbound rule from either family, then one rule you add | `droplet-ipv6` | $0 | $0 | 2 | 2 | `doctl compute firewall list --format ID,Name` shows no such firewall (**est.**) |
| `aaaa-record`: an `AAAA` record at your DNS provider (needs a name you own) | `droplet-ipv6` | $0 at your DNS provider's free tier (**est.**; the domain itself costs money) | $0 (same) | 3 | 1 | The record is gone from the provider's page, and `dig AAAA your-name` (substitute yours) returns nothing after the TTL (**est.**) |
| Not in this table | | | | | | Bandwidth, a domain, snapshots, backups |

Prices from `docs/cost-prices.json`, retrieved 2026-10-21. DigitalOcean's pricing page says droplets are billed per second with a 60-second minimum, capped at 672 hours a month, and that a powered-off droplet is still billed (retrieved 2026-10-21 by the sibling lessons; I did not re-read it).

Steps, all **est.** (read from DigitalOcean's "How to Enable IPv6 on Droplets", page last verified 3 Sep 2026, retrieved 2026-10-22; **not run**):

1. Create the droplet with IPv6 ticked (control panel: Networking section of the Create page; or `doctl compute droplet create ... --enable-ipv6`).
2. Before anything else, create the firewall with **no** inbound rules and apply it. Add one rule at a time. When you add one in the console, the Sources field is pre-filled with both All IPv4 and All IPv6; remove the one you do not mean.
3. From a machine that has IPv6, connect to the droplet's IPv6 address (DigitalOcean's page notes that you cannot do this from a machine without IPv6).
4. Add the `AAAA` record last. Run the checklist's step 11 tests.
5. Tear down in the reverse order: the record, the firewall, the droplet. Run the proofs. Check your billing page the next day.

**AWS (est.; not run).** The pieces are the same: a VPC and subnet with IPv6 added, an instance with an IPv6 address, a security group with IPv6 rules, an `AAAA` record. The documentation says IPv4 and IPv6 communication are independent in a dual-stack VPC. Whether IPv6 addresses avoid the public IPv4 hourly charge I did not read (**est.**). Prices for the pieces belong in `docs/cost-prices/aws.json`, which I did not re-read for this page.

## A threat model of a dual-stack host

A short one, in the format of [Threat model](Threat-Model.md). The system: a small server with a public name, a cloud firewall, a host firewall and an allowlisted admin path, running IPv4 only today and considering IPv6.

**Assets.** The services and their data; the admin path (SSH or a tunnel); the firewall rules in both families; the logs; the DNS records; the allowlists and rate limits; the bill.

**Actors.** An anonymous scanner; a visitor whose network gained IPv6; a machine on the same LAN as an admin (a rogue advertisement); an administrator who makes a mistake; a package or cloud default that adds an address family; a provider whose defaults differ from yours.

**Trust boundaries.** Internet to cloud firewall; cloud firewall to host; DNS to client (which name resolves to which family); the LAN to the router (advertisements); a CDN or proxy to the origin.

| ID | Abuse case | Impact | What the attacker needs | Rank |
|---|---|---|---|---|
| D1 | IPv6 added to the host, firewalled in IPv4 only | Services reachable over IPv6 that you believed closed | A reachable IPv6 address and a port | High |
| D2 | An `AAAA` record published before IPv6 is firewalled, rate limited and logged | The service is exposed, unmonitored | Knowing the name | High |
| D3 | An IPv4-only allowlist or rate limit | IPv6 users locked out, or the control bypassed | An IPv6 source | High |
| D4 | A rogue or mistaken router advertisement on a LAN | Traffic redirected, a second prefix appears | Presence on the link | Medium |
| D5 | Logs and tools that miss or mis-parse IPv6 | Events invisible to detection | Time | Medium |
| D6 | ICMPv6 dropped wholesale | IPv6 breaks, or stalls after the first packets | A well-meant firewall change | Medium |
| D7 | Scanning discovers the address anyway (DNS, logs, certificate records, patterned addresses) | The "big space" gave no protection | A leaked address | Medium |
| D8 | Extension-header or fragment tricks around a weak filter | A filter sees a packet differently from the host | A filter that does not walk the chain | Low to medium (est.) |
| D9 | A change to relax `test_ipv6_closed.py` removes the guard for everything | IPv6 opens in places not intended | A careless edit | Medium |

| ID | Mitigation | How to verify |
|---|---|---|
| D1 | One `inet` table or both tools; default deny; test both families after every change | Exercise 5's probe: both 8080 answers `filtered`; `tests/test_ipv6_closed.py` stays green |
| D2 | Publish `AAAA` last, after the firewall, limits and logs are verified (checklist 3 to 7) | `curl -6` from outside, and a log line for it |
| D3 | A prefix for each family on every list; key limits by prefix | `allowlist.py` shows no IPv4-only warning; the rate-limit lesson's test with a `/64` |
| D4 | `accept_ra=0` on servers; RA-Guard on managed switches; watch for a second default router | Exercise 4's output; `ip -6 route` |
| D5 | Canonical address form in logs; IPv6 sample events in detection tests | A detection test with an IPv6 source passes |
| D6 | Accept neighbor discovery and the error messages; limit the rest | Exercise 5's last step |
| D7 | Never rely on the unguessable address; firewall regardless | The firewall test, not the scan |
| D8 | Keep firewall software patched; drop obviously malformed header chains where documented (RFC 9288) | Vendor documentation (est.) |
| D9 | Review that edit like a firewall change; keep the inbound-source rules; add a test for what you open | The test file's own failing fixtures |

**Residual risk.** A correct dual-stack firewall does not stop an attack through a port you opened on purpose, a stolen credential, a flaw in the stack, or an attacker on your own LAN. Dual stack doubles what you must keep correct; this page can show you how to do it, and cannot do it for you.

## Build, break, detect, evade, defend (the dual-stack loop)

The same loop as the [labs](Labs-Break-It-on-Purpose.md), applied to one host that speaks both families. Each step was run in Exercises 2 to 6.

- **Build.** A host with a fixed IPv6 address and a SLAAC address, a dual-stack service, and an `inet` default-deny table that allows only the port you mean; an allowlist with both families.
- **Break (the one-family firewall).** Write the same policy in an `ip` table only: IPv4 8080 turns `filtered`, IPv6 8080 stays `open`. Or make the opposite mistake: drop all ICMPv6 and watch IPv6 stop for everyone, including port 80.
- **Detect.** Three signals the lab produced: the probe (`open` where the matrix expects `filtered`), the listener (`ss -ltn` shows `*:8080` and `[::]:8443`, so a service listens on IPv6), and the neighbor table (`INCOMPLETE` after a dropped solicitation). On a real system add the firewall's counters and logs, and a probe from outside over both families.
- **Evade.** Come in through the other family; steer a LAN machine with a router advertisement; use an IPv4-mapped address to slip past a check that only understands one family (Exercise 6); rotate through a `/64` to dodge a per-address limit. None of these needs a vulnerability, only an assumption that one family is all there is.
- **Defend.** One firewall table for both families, default deny; ICMPv6 accepted by type; `AAAA` last; allowlists and rate limits by prefix; canonical logging; `accept_ra=0` or RA-Guard where it matters; and a test that fails when IPv6 opens by accident. Closed by default, tested, and a checklist for opening it.

### Flip the board

**The reviewer.** Someone gives you this and says "the server is locked down, it only allows our office". Find at least five problems without running it.

```bash
nft add table ip filter
nft add chain ip filter input '{ type filter hook input priority 0; policy drop; }'
nft add rule ip filter input ip saddr 198.51.100.0/24 tcp dport 22 accept
nft add rule ip filter input ct state established,related accept
```

```text
# and the service is started with:  python3 serve.py 22 80 443
```

Answers:
1. The table is family `ip`: it is an IPv4 firewall. A service on `::` is not covered, so IPv6 is open on every port.
2. The service listens on a dual-stack socket, so IPv4 and IPv6 both reach it; the allowlist matches IPv4 sources only, so "office only" holds for one family.
3. Ports 80 and 443 are in no rule, so even IPv4 clients cannot reach them although the service listens: the intent and the rules disagree.
4. There is no loopback accept, so local services that talk to each other on this machine break.
5. The office `/24` is trusted whole for SSH, with no rate limit.
6. Nothing logs.
7. The obvious repair, a switch to an `inet` table, brings a new trap: an `icmpv6` mistake (dropping neighbor discovery, or accepting all ICMPv6 unthinkingly). The fix is a documented list of types, as in Exercise 5.

**The attacker's view.** You have a name and no insider knowledge. You ask DNS for `AAAA` as well as `A` and try the same ports on both. You note the router's link-local address if you are on the LAN. You look for the service that was fixed on the family you were not expecting. The defender's only reply is to have thought of both. As an attacker your best question is not "how do I scan 2^64 addresses" but "which family did they forget".

## Checkpoint

You are done when you can say, without looking:

- How many `/64`s are in a `/48`, and what a `/64` is for.
- Which address a machine builds without any server, how it finds its gateway, and why that gateway is a link-local address.
- What neighbor discovery replaces, and which ICMPv6 messages a firewall must not drop.
- What a privacy extension changes about the address you see in a log.
- What "NAT is not a firewall" means, and what you must write yourself for IPv6.
- Why a dual-stack host can be open over IPv6 behind an IPv4-only firewall, and the one-line fix.
- Two documented reasons and two opinions about why adoption is slow, and which is which.
- What this project does about IPv6, why, and the first three items of the checklist for turning it on.

## Common mistakes

| Mistake | Why it happens | Fix |
|---|---|---|
| "IPv4 is closed, so it is closed" | An IPv4-only firewall says nothing about IPv6 | One `inet` table, and probe both families |
| IPv6 stops working after a default-deny | Neighbor discovery was dropped | Accept the neighbor and error messages by type |
| "The address space is huge, so no one will find it" | Scanning is not the only way to learn an address | Firewall it regardless |
| An allowlist with only IPv4 | Habit | A prefix for each family; run `allowlist.py` |
| A per-address rate limit | One person has a whole prefix | Key by prefix |
| Searching logs for an address typed one way | Several valid spellings | Canonical form (RFC 5952) in logs and searches |
| `AAAA` published first | Excitement | Publish it last |
| A dual-stack check rejects its own IPv4 clients | The server reports `::ffff:192.0.2.9` | Unwrap IPv4-mapped addresses before comparing |
| Treating NAT as the firewall | It was a side effect | Write the stateful default-deny rule |
| "IPv6 is off on the router, so the LAN has none" | Link-local and advertisements continue inside | Treat the LAN as a link that speaks IPv6 anyway |

## Claims register

All read-only requests; retrieved **2026-10-22** unless stated. "Read" means I read the passage; "Observed" means I ran it that day in the lab. **These numbers drift.**

| Claim | Source | Status |
|---|---|---|
| IPv6 specification, minimum link MTU 1280, routers do not fragment | [RFC 8200](https://www.rfc-editor.org/rfc/rfc8200) | Read (MTU passage) |
| Interface IDs are 64 bits for most addresses; modified EUI-64 | [RFC 4291](https://www.rfc-editor.org/rfc/rfc4291) | Read |
| Neighbor discovery messages must have hop limit 255; ND, RA, solicited-node multicast | [RFC 4861](https://www.rfc-editor.org/rfc/rfc4861) | Read; Observed (hop limit by effect, Exercises 3 and 4) |
| SLAAC and duplicate address detection | [RFC 4862](https://www.rfc-editor.org/rfc/rfc4862) | Abstract read; Observed |
| Temporary addresses: defaults 2 days valid, 1 day preferred; RFC 4941 is obsolete, replaced by RFC 8981 | [RFC 8981](https://www.rfc-editor.org/rfc/rfc8981), [RFC 4941 info page](https://www.rfc-editor.org/info/rfc4941) ("This RFC is now obsolete, see RFC 8981") | Read |
| Site prefix size is an operational choice; "significantly more than a single /64" | [RFC 6177](https://www.rfc-editor.org/rfc/rfc6177) | Read ("giving home sites significantly more than a single /64") |
| The 64-bit boundary | [RFC 7421](https://www.rfc-editor.org/rfc/rfc7421) | Abstract read |
| Default address selection; Happy Eyeballs v2 | [RFC 6724](https://www.rfc-editor.org/rfc/rfc6724), [RFC 8305](https://www.rfc-editor.org/rfc/rfc8305) | Abstracts read |
| ULA format and purpose | [RFC 4193](https://www.rfc-editor.org/rfc/rfc4193) | Abstract read |
| Documentation prefix `2001:db8::/32` | [RFC 3849](https://www.rfc-editor.org/rfc/rfc3849) | Fetched; cited by the sibling lessons |
| Canonical text form; flexibility "has been causing problems for operators, system engineers, and users" | [RFC 5952](https://www.rfc-editor.org/rfc/rfc5952) | Read (abstract) |
| Dual stack: "twice the exposure"; logs and canonical form; stable addresses and scanning; extension headers; RA-Guard references | [RFC 9099](https://www.rfc-editor.org/rfc/rfc9099) sections 2.1.4, 2.3, 2.6.1.1, 2.7.1 | Read |
| IPv6 scanning is more feasible than assumed | [RFC 7707](https://www.rfc-editor.org/rfc/rfc7707) | Abstract and the address-pattern passage read; the other chapters **not read** |
| Rogue advertisements; RA-Guard | [RFC 6104](https://www.rfc-editor.org/rfc/rfc6104), [RFC 6105](https://www.rfc-editor.org/rfc/rfc6105) | RFC 6105 abstract read; RFC 6104 fetched, only its title relied on |
| Router preference (the `--high` flag) | RFC 4191 | **est.**: not fetched; the lab's output shows the kernel honoring it |
| ICMPv6 filtering recommendations | [RFC 4890](https://www.rfc-editor.org/rfc/rfc4890) | Abstract read |
| Extension header filtering and the header chain in the first fragment | [RFC 9288](https://www.rfc-editor.org/rfc/rfc9288), [RFC 7112](https://www.rfc-editor.org/rfc/rfc7112) | Abstracts read |
| NAT is not a security mechanism; stateful filtering is; "5,000 years"; section 4.2 quotation | [RFC 4864](https://www.rfc-editor.org/rfc/rfc4864) | Read |
| Simple security for gateways; "constructive tension"; type 0 routing header must not be forwarded | [RFC 6092](https://www.rfc-editor.org/rfc/rfc6092) | Read (introduction, REC-4) |
| End-to-end transparency; "refrains from making recommendations" | [RFC 2775](https://www.rfc-editor.org/rfc/rfc2775) | Abstract read |
| Enterprise training gap; deployment guidance | [RFC 7381](https://www.rfc-editor.org/rfc/rfc7381) section 2.3 | Read |
| NPTv6 | [RFC 6296](https://www.rfc-editor.org/rfc/rfc6296) | Fetched; **est.** for details |
| NIST SP 800-119 (December 2010): block IPv6 if not deploying; NAT as a security control; CGNAT sharing; temporary addresses and ingress filtering | [NIST SP 800-119](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-119.pdf) | Read (the passages quoted) |
| Google users reaching Google over IPv6: 45.589127 percent on 2026-10-20; 44.08 (2025-10-20), 44.90 (2024), 29.45 (2020), 11.65 (2016), 0.98 (2012) | [Google IPv6 statistics](https://www.google.com/intl/en/ipv6/statistics.html); data file `https://www.google.com/intl/en_ALL/ipv6/statistics/data/adoption.js` | Read 2026-10-22; **drifts daily** |
| APNIC: world 43.64 percent capable, 40.74 percent preferred, 945,719,606 samples; US 62.41/60.04, Germany 72.62/70.43, India 76.18/73.43, France 85.77/84.79, China 48.63/39.25 | [APNIC IPv6 stats](https://stats.labs.apnic.net/ipv6) (page's query window 22/09/2026 to 21/10/2026) | Read 2026-10-22; **drifts**; meaning of "capable" and "preferred": **est.** |
| Cloudflare Radar figures | [Cloudflare Radar](https://radar.cloudflare.com/adoption-and-usage) | **Not read**: HTTP 403 to `curl`, 2026-10-22 |
| pfSense: adoption "8% ... by July 2015 and slightly over 40% ... in 2022"; IANA allocated all its space on 31 January 2011; "catch-22"; ISP responsibility | [Netgate: IPv6](https://docs.netgate.com/pfsense/en/latest/network/ipv6/index.html) | Read |
| pfSense: best practice is no IPv6 translation; NPt; NAT64 | [Netgate: IPv6 and NAT](https://docs.netgate.com/pfsense/en/latest/network/ipv6/nat.html) (page last updated Dec 16 2025) | Read |
| pfSense: "Allow IPv6" blocks all IPv6 traffic when unchecked and does not disable IPv6 functions; "Prefer IPv4 over IPv6" | [Netgate: Advanced networking](https://docs.netgate.com/pfsense/en/latest/config/advanced-networking.html) | Read |
| pfSense WAN types (static, DHCPv6 with prefix delegation, SLAAC, tunnels) | [Netgate: IPv6 WAN types](https://docs.netgate.com/pfsense/en/latest/network/ipv6/wan-types.html) (last updated Aug 28 2025) | Read; the GUI field names for these on the WAN page: **est.** |
| DigitalOcean: IPv6 on a Droplet gives 16 addresses; no additional cost, bandwidth charges apply | [IPv6 overview](https://docs.digitalocean.com/products/networking/ipv6/), [IPv6 pricing](https://docs.digitalocean.com/products/networking/ipv6/details/pricing/) (last verified 13 Jul 2026) | Read |
| DigitalOcean: enable at creation, or power off and configure by hand; not all ISPs offer IPv6 | [How to enable IPv6](https://docs.digitalocean.com/products/networking/ipv6/how-to/enable/) (last verified 3 Sep 2026), [IPv6 limits](https://docs.digitalocean.com/products/networking/ipv6/details/limits/) | Read; **not run** |
| DigitalOcean firewall: inbound Sources pre-filled with All IPv4 and All IPv6; `::/0` in the API | [Configure firewall rules](https://docs.digitalocean.com/products/networking/firewalls/how-to/configure-rules/) | Read |
| AWS: dual-stack VPC; "no migration path from IPv4-only subnets to IPv6-only subnets" | [AWS VPC: IPv6 support](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-migrate-ipv6.html) | Read |
| AWS: $0.005 per public IPv4 address per hour from 1 February 2024; cost up more than 300 percent over five years | [AWS blog: public IPv4 address charge](https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights/) | Read; dated announcement, prices change |
| OMB M-21-07 (19 November 2020): 20, 50, 80 percent IPv6-only targets for FY2023, FY2024, FY2025 | [M-21-07](https://www.whitehouse.gov/wp-content/uploads/2020/11/M-21-07.pdf) | Read; whether met: **not checked** |
| Droplet price $6 a month for `s-1vcpu-1gb` | `docs/cost-prices.json` (retrieved 2026-10-21) | Read from the repository |
| The project's IPv6 guards | `tests/test_ipv6_closed.py`, `modules/aws/vpc/main.tf`, `modules/twingate-connector/main.tf`, `scripts/zero_ports_check.py` | Read in this repository, 2026-10-22 |
| Lab results: SLAAC, privacy extensions, neighbor discovery, rogue advertisement, dual-stack listener, firewall gap, ICMPv6 trap, allowlist script | Local run, 2026-10-22, rootless `unshare -Urnmpf` | Observed |
| PowerShell commands; cloud steps; `curl -6` checks | Documentation only | **est.**, not run |
| That mobile carriers and large content networks lead adoption; why weekend figures are higher; how many ISPs offer IPv6 today | None read | **Opinion / est.** |
| The maintainer's statements | His own words, 2026-10-22 | Quoted with grammar fixes only |

**Not verified:** every statistic beyond its snapshot; Cloudflare Radar; whether the US agencies met their targets; what APNIC's "capable" and "preferred" test; the exact GUI paths in pfSense; reverse DNS behavior for IPv6 on any provider; the behavior of any product's IPv6 logging; and anything on a real IPv6 network.

Next: [Reading order](Reading-Order.md).
