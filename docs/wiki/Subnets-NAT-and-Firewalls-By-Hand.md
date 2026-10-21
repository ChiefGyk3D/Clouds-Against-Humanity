# Subnets, NAT and firewalls by hand

Side page to the start-from-zero pages. Read it after [Networking basics](Networking-Basics-for-This-Project.md) (core step 3) and, if "TCP", "port" and "handshake" are fuzzy, after [How a web request works](How-a-Web-Request-Works.md). It reaches ahead to [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) (core step 13), which you can read with fresh eyes once you have done the arithmetic and watched a packet get dropped. It does not repeat what those pages say: it makes you do the work they only describe. Next: [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the free local lab was run once on Linux; everything else was not run.** On **2026-10-21** the author ran every Bash command in the free path on a Debian-based Linux machine with `nft` 1.1.3, iproute2 6.15.0 and Python 3.13.5, as an ordinary user (no `sudo`), and pasted trimmed output from those runs. Three things were **not run**: the PowerShell and Windows commands (there was no Windows machine; they are written from Microsoft's documentation and marked **est.**), the fallback for machines that block unprivileged user namespaces (marked **est.**), and the whole optional own-account path with two droplets (written from DigitalOcean's `doctl` documentation, never applied; run it expecting to fix something). Every vendor and standards claim is in the [claims register](#claims-register) with the URL and the date it was read. Output varies with your versions; trust what your terminal prints over this page.

> **Prerequisites.** [Networking basics](Networking-Basics-for-This-Project.md) (addresses, CIDR in one paragraph, ports, inbound and outbound, what a stateful firewall is) and a terminal ([Git from zero](Git-From-Zero.md) has a first look; [The terminal and your first script](Terminal-and-Your-First-Script.md) goes further). The free path needs a Linux machine or virtual machine with `python3`, `ip` (the `iproute2` package) and `nft` (the `nftables` package); Windows readers can use WSL 2 for the lab (est.) and do the arithmetic and the cloud path from PowerShell. About two and a half hours for the reading and the free exercises (est.); the optional cloud path adds about an hour (est.).

> **Where packets go.** Everything on this page that sends a packet sends it to a pretend machine inside your own shell, or, in the optional path, to a droplet you created in your own account. Nothing here points at anyone else's machine, and you should not point it there: scanning a machine you do not own, or have no permission to test, can be against the law or the provider's rules, and it teaches you nothing the lab does not.

## What you will be able to do

- Work out by hand how many addresses are in a `/24`, `/26` or `/28`, where each block starts and ends, and how to split a `/24`, then check your answer with Python's `ipaddress` module (and PowerShell).
- Tell a private address from a public one, name the three private blocks of RFC 1918, and say what the carrier-grade NAT block `100.64.0.0/10` is and why it is not "private" in the same way.
- Read a route table: say where a packet to a given address goes, and why a machine with no route says "network unreachable".
- Say what NAT does (translates addresses so many private machines share one public one), what port forwarding adds, what NAT hides, and what it does **not** protect.
- Explain stateful versus stateless filtering, default deny, and write allow rules by source, port and protocol.
- Read a real rule set, including this repository's `modules/firewall` and its host firewall, and say what each line allows.
- Run Build, Break, Detect, Evade, Defend on a firewall: write a default-deny rule set, break it with an over-permissive rule, find the hole with a port check, see that it is being used with the firewall's counters, learn who is using it from a source-specific rule or a log, and fix it.
- Place a VPN and zero trust network access on one diagram and say what each assumes.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Public and private addresses, CIDR | [Networking basics](Networking-Basics-for-This-Project.md#cidr-the-slash-notation) gives the idea and one worked count (`/26` is 64). | A method you can repeat for any prefix, splitting a block, overlap, and the other special ranges. |
| NAT | [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) prices a NAT gateway; [Zero trust at home](Zero-Trust-at-Home-Two-Connectors-and-Failover.md#vpn-versus-ztna-under-real-residential-conditions) names CGNAT. Neither shows NAT working. | What the translation is, seen in a connection table, and why it is not a firewall. |
| Routing | Mentioned in passing ("the stage 2 ranges must not overlap"). | A route table you can read, and what "no route" looks like. |
| Firewalls | [Networking basics](Networking-Basics-for-This-Project.md#what-a-firewall-does) and [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) describe this project's rules and why. | Writing and breaking one yourself, in a lab, and reading the two real rule sets the repository ships. |

## Addresses and CIDR, by hand

An IPv4 address is 32 bits, written as four numbers from 0 to 255 (each number is 8 bits, an **octet**). A **subnet** is a block of consecutive addresses that share a first part and are meant to reach each other directly. **CIDR** (classless inter-domain routing, [RFC 4632](https://www.rfc-editor.org/rfc/rfc4632)) writes a subnet as a starting address and a **prefix length**: `10.78.0.0/24` means "the first 24 bits are fixed, the last 8 may vary". The same thing is written as a **netmask**, where the fixed bits are ones: `/24` is `255.255.255.0`.

### The method (five steps)

For any address with a prefix, say `10.78.0.37/28`:

1. **Host bits** = 32 minus the prefix. Here 32 - 28 = 4.
2. **Addresses** = 2 to the power of the host bits. Here 2^4 = 16.
3. **Block size** in the octet where the prefix ends. Here the prefix ends inside the last octet, so the block is 16. (For `/20` the prefix ends inside the third octet: 12 host bits is 4096 addresses, which is 16 whole values of the third octet and all 256 of the fourth, so the block is 16 in the third octet.)
4. **Start** = the largest multiple of the block size that is not more than your number in that octet. The multiples of 16 are 0, 16, 32, 48; 37 is at least 32 and below 48, so the start is 32.
5. **End** = start + block size - 1. 32 + 16 - 1 = 47. So `10.78.0.37/28` lives in `10.78.0.32/28`, which runs from `10.78.0.32` to `10.78.0.47`.

The first address of a block is its **network address** and the last is its **broadcast address** (an address meaning "everyone on this subnet"). On an ordinary network neither can be given to a machine, so a block holds 2 fewer usable hosts than addresses. A cloud provider may reserve more: Amazon's documentation reserves five in each subnet (the first four and the last), and I did not read a figure for DigitalOcean (est.). Check yours before you size a subnet to the last host.

| Prefix | Netmask | Addresses | Usable on an ordinary network | Block size (last octet) |
|---|---|---|---|---|
| `/24` | 255.255.255.0 | 256 | 254 | whole octet |
| `/25` | 255.255.255.128 | 128 | 126 | 128 |
| `/26` | 255.255.255.192 | 64 | 62 | 64 |
| `/27` | 255.255.255.224 | 32 | 30 | 32 |
| `/28` | 255.255.255.240 | 16 | 14 | 16 |
| `/29` | 255.255.255.248 | 8 | 6 | 8 |
| `/30` | 255.255.255.252 | 4 | 2 | 4 |
| `/32` | 255.255.255.255 | 1 | one address | 1 |

Two shortcuts follow from the table. **Splitting:** each step down in prefix halves the block, so a `/24` splits into two `/25`, four `/26`, eight `/27` or sixteen `/28`, and the pieces start at 0, 64, 128 and 192 for `/26`. **Sizing:** to fit N hosts, add 2 and round up to the next power of two. Fifty machines need 52, which rounds to 64, so a `/26`.

### The special ranges to know

| Range | What it is | Notes |
|---|---|---|
| `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | The three **private** blocks of [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918): addresses reserved for use inside a network. `172.16.0.0/12` runs `172.16.0.0` to `172.31.255.255`. | Not routed across the internet, so millions of networks reuse them. The same number in two networks you later join is an **overlap**, which is why [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md#vpc-range-chosen-to-avoid-the-homelab) picks a range nobody at home uses. |
| `100.64.0.0/10` | **Shared address space** ([RFC 6598](https://www.rfc-editor.org/rfc/rfc6598)), set aside for internet providers that put many customers behind **carrier-grade NAT (CGNAT)**. | Not RFC 1918 and not a normal public address. If your router's outside address is in this block, your provider is sharing one public address among many homes, and nothing from the internet can reach you without help. |
| `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24` | **Documentation** ranges ([RFC 5737](https://www.rfc-editor.org/rfc/rfc5737)), for examples. | This page uses them for "public" addresses so nothing here is anyone's real machine. |
| `127.0.0.0/8` | Loopback: this machine talking to itself. | `localhost`. |
| `169.254.0.0/16` | Link-local: addresses a machine gives itself when it finds no other. | The cloud metadata address `169.254.169.254` that the [hardening page](Droplet-Hardening.md) locks down lives here (est.; the range is from [RFC 3927](https://www.rfc-editor.org/rfc/rfc3927), which I did not read). |

## Routing, in plain words

A **route table** is a machine's list of "to reach this block, send the packet this way". Every machine has one, not only routers. The rule for each packet is: find the routes whose block contains the destination, take the most specific one (the longest prefix, est.; the `ip-route` manual page mentions "longest match"), and send the packet out that interface, or to the **gateway** that route names. A gateway is a machine on your own subnet that knows the way out.

Two routes cover most cases:

- **The connected route.** When you give a machine `10.78.0.20/24`, it adds "`10.78.0.0/24` is directly attached to this interface". Destinations in that block are sent straight to them.
- **The default route**, `0.0.0.0/0`, "everything else, via the gateway". It is the least specific block there is, so it is used only when nothing else matches. A machine with no default route can reach its own subnet and nothing beyond it.

A **router** is a machine with a foot in two networks that is willing to pass packets between them (on Linux this is a setting, `net.ipv4.ip_forward`, that is off by default on most machines, est.). The lab below builds one and shows what a machine on the far side reports when it has no route: `Network is unreachable`, immediately, because the machine knew it had nowhere to send the packet. That is a different failure from a timeout, where it sent the packet and heard nothing.

## NAT and port forwarding

A private address cannot be a source on the internet: replies would have nowhere to go. **Network address translation (NAT, [RFC 3022](https://www.rfc-editor.org/rfc/rfc3022))** fixes that at the border. The router rewrites the source address of an outgoing packet to its own public address and remembers the pairing in a **connection table** (on Linux, **conntrack**). When the reply arrives, the router looks it up and rewrites the destination back. Many private machines share one public address this way; a single port number tells their replies apart. Home routers do this for you, and a **NAT gateway** in the cloud is the same idea as a managed service you rent ([Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) prices it).

**Masquerade** is the Linux name for NAT that uses whatever address the outgoing interface currently has. **Port forwarding** (destination NAT, "DNAT") is the opposite direction: "a packet that arrives on my public address, port 8080, goes on to this inside machine, port 8080." Without that rule, nothing inside is reachable from outside, because the router has no table entry for a connection nobody inside started.

### What NAT hides and what it does not protect

NAT hides the inside addresses from the other end of a connection: the lab server below sees the router's address, not the client's. It also has a side effect people mistake for security, which is that an unsolicited packet has no table entry and goes nowhere. But translation is not filtering. The router is still willing to forward packets; the only thing missing is the table entry. If an attacker can send packets to the router with a route to the inside (for example, because they are on the same link as its outside port, such as a compromised device on the provider-facing side) the lab shows the inside machine answering. The protection comes from a rule that says "forward only what was asked for", which is a firewall. Keep the two ideas apart: NAT is bookkeeping; the firewall is policy.

## Firewalls

A **firewall** is a list of rules that decides which packets pass. Three ideas matter more than any product.

**Default deny.** What happens to a packet that matches no rule? In a default-deny firewall it is dropped, so a forgotten rule breaks something you will notice instead of exposing something you will not. The opposite, default allow, makes the rule list a list of things you thought of blocking. DigitalOcean's cloud firewall is default deny in both directions ([claims register](#claims-register)), and the Linux `nft` rule sets below say it with `policy drop`.

**Stateful or stateless.** A **stateless** filter judges each packet alone. To let replies to your web browsing back in, you would have to write a rule such as "allow packets from source port 443", which also admits anyone who simply sets that source port. A **stateful** firewall remembers the connections it has seen and recognizes a reply as a reply. On Linux the memory is conntrack, and the rule is `ct state established,related accept`: "accept packets that belong to a connection already allowed". A stateful firewall still needs a rule to allow the connection to start; replies are free, new connections in either direction need a rule, which is the lesson [Networking basics](Networking-Basics-for-This-Project.md#inbound-outbound-and-why-the-direction-matters) took an evening of this project to learn.

**Allow rules by source, port and protocol.** A good allow rule names all three: who may connect (a source address, a range, or a tag), to what (a port), and over which protocol (TCP, UDP, ICMP). A rule that names only a port ("allow 8080") is a rule for the whole internet. In a cloud firewall the "who" can be a **tag**: a label on a droplet, so the rule survives the droplet being rebuilt with a different address, and there is no prefix length to mistype (a tag can still be put on the wrong droplet). In `nft` the closest local thing is a named **set** of addresses, which the lab uses.

Two practical points the rest of the page turns into exercises:

- **Order.** In `nft`, the rules of a chain are checked top to bottom, and the first rule that ends in `accept` or `drop` decides (est.; the lab shows it with `insert`). In DigitalOcean's cloud firewall there is no order to get wrong: traffic is allowed if an allow rule matches, and since 4 August 2026 the product also has **deny rules**, which take precedence over allow rules ([claims register](#claims-register)). This repository's module builds allow rules only.
- **Two layers.** A cloud firewall sits outside the machine, in the provider's network; a **host firewall** (`nftables`, `ufw`, the Windows firewall) runs inside it. DigitalOcean's documentation says its firewall does not show up in the software firewall and that rules in the two should not conflict. This repository runs both on the connectors ([Droplet hardening](Droplet-Hardening.md)): the cloud firewall as the outer wall, an optional `nftables` table as the second.

### VPN and ZTNA on the same diagram

```text
 A VPN                                     ZTNA (this project)
 -----                                     --------------------
  user's laptop                              user's laptop
      |  tunnel in, through an OPEN port         |  asks the service, per request
      v                                          v
  VPN gateway (listens on the internet)      ZTNA service (cloud)
      |                                          ^
      v                                          |  connector dials OUT, holds the line
  the whole subnet is reachable          connector in the subnet (no inbound rule)
      |                                          |
      v                                          v
  servers, printers, everything              only the resources the policy lists
```

What each **assumes**. A VPN assumes the network inside the tunnel is trusted: once you are in, the subnet's own firewall rules are all that stand between you and a server, so the subnet's size and rules matter (this page's arithmetic). It usually needs an inbound port reachable from the internet (est.), and a VPN server at home breaks behind CGNAT because you cannot port-forward an address you do not own. ZTNA assumes nothing about location: each request is checked against policy, and in this project's design the connector needs only outbound rules. The cost is a dependence on the vendor's service. [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) makes the full argument; the point here is which parts of this lesson each design leans on.

## Reading a rule set

Read a firewall the way you would read a contract: what is the default, then what are the exceptions, then who can use each exception.

### A rule set from this repository: the host firewall

The connectors can run a second, host-level firewall (`host_firewall`, off by default; it is **built but not tested on a real machine** according to [Droplet hardening](Droplet-Hardening.md)). Its rules are in `modules/twingate-bootstrap/cloud-init.yaml.tftpl`. With the module's defaults filled in (the three private blocks as SSH sources, no metrics port, no node exporter) the table reads:

```text
table inet cah_host {
  chain input {
    type filter hook input priority 0; policy drop;
    iifname "lo" accept
    ct state established,related accept
    ct state invalid drop
    icmp type { echo-request, destination-unreachable, time-exceeded } accept
    icmpv6 type { destination-unreachable, packet-too-big, time-exceeded, echo-request, nd-router-advert, nd-neighbor-solicit, nd-neighbor-advert } accept
    udp sport 67 udp dport 68 accept
    tcp dport 22 ip saddr { 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 } accept
  }
}
```

Line by line. `table inet cah_host` is the project's own table, so it is designed not to touch anyone else's rules (`inet` means it covers IPv4 and IPv6). `hook input` means this chain sees packets addressed **to this machine** (not packets passing through, and not packets it sends). `policy drop` is default deny. `iifname "lo"` is the machine talking to itself. `ct state established,related` is the stateful line. `ct state invalid drop` drops packets that fit no connection. The ICMP lines allow ping and error messages (ICMP is the small control protocol that `ping` and error messages such as "destination unreachable" use, separate from TCP and UDP); the ICMPv6 line includes the neighbor discovery IPv6 needs to find other machines; `udp sport 67 udp dport 68` is the reply from the DHCP server that renews the machine's address. The last line is the only rule that admits a new TCP connection from the network: port 22, from the three private blocks. (The ICMP and DHCP lines above it also let some non-TCP packets in: ping and error messages from any source, and DHCP replies.) The module's own variable description says the default is wide on purpose because the module "does not know the VPC CIDR", and tells you to narrow it ([`host_firewall_ssh_sources`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/modules/twingate-bootstrap/variables.tf)).

### A rule set from this repository: the cloud firewalls

`modules/firewall` builds a DigitalOcean cloud firewall from three lists. Read from `modules/firewall/main.tf`, `stacks/00-foundation/main.tf` and `stacks/10-access/main.tf`:

| Firewall | Inbound | Outbound |
|---|---|---|
| Baseline (stage 0), attached by tag `cah-baseline-tor1` | none | TCP 443, 80, 53; UDP 53, 123; each to any address (`0.0.0.0/0` and `::/0`) |
| Connector (stage 1), attached by tag `cah-connector-tor1`, on top of the baseline | TCP 22, only from droplets carrying the connector tag | The same five, plus TCP 30000-31000 and UDP 1-65535 to any address, plus TCP 22 to the connector tag |

DigitalOcean evaluates all firewalls attached to a droplet together, so the two combine. The module has no input that can admit an address on the inbound side: its inbound rules are tag-sourced only, which is a design choice, not a limit of the product.

### Drill: read them

Answer each from the tables above, then open the answers.

1. Can a stranger on the internet open a TCP connection to a connector's public address on port 22?
2. Can connector A open SSH to connector B? Which two rules does that take?
3. Can a connector run `ping` against a public address?
4. Which single rule in the connector firewall is the widest, and which direction is it?
5. In the `cah_host` table, can a machine at `10.5.5.5` reach TCP 80? TCP 22? Can a machine at `203.0.113.9` ping it?
6. A teammate says "the cloud firewall already blocks everything, so the host firewall is pointless." Give one reason it is not.

<details>
<summary>Answers</summary>

1. No. No inbound rule admits an address, and traffic that matches no rule is denied.
2. Yes. B needs an inbound rule (TCP 22 from the connector tag) and A needs an outbound rule (TCP 22 to the connector tag). The first fix in this project's build added only the inbound rule and the connection timed out ([Lessons learned](Lessons-Learned.md#2-connector-to-connector-ssh-timed-out-twice)).
3. No (reasoned, not tested). ICMP is a different protocol from TCP and UDP, there is no outbound ICMP rule, and DigitalOcean says that with no matching outbound rule nothing is permitted. The same machine can still resolve names, because that is UDP and TCP 53.
4. UDP 1-65535 to any address, outbound. It exists because Twingate needs outbound UDP to any port for peer-to-peer connections (the comment in `stacks/10-access/main.tf` says so). It is the widest rule, and it is outbound only; inbound stays deny-all. Reviewing a rule set means asking of every wide rule: who needs it, and what is it protecting against if it were misused?
5. TCP 80: no (not accepted, so dropped). TCP 22: yes, `10.5.5.5` is in `10.0.0.0/8`. Ping from `203.0.113.9`: yes, the ICMP line has no source restriction, so echo requests are accepted from anywhere that reaches the machine. Note the second answer: the default SSH source is every private address, which is why the project says to narrow it.
6. The cloud firewall is outside the machine, so the machine's own software cannot switch it off from the inside (someone holding a cloud API token still can), which is its strength. It also says nothing about traffic between processes, and it is one control: a mistake in it (such as the typo this lesson makes on purpose) leaves nothing behind it. The host firewall is a second wall that fails independently. The cost is two rule sets to keep consistent.

</details>

## Where this shows up in this project

- The **VPC** `10.78.0.0/24` is a `/24`: 256 addresses, and every droplet gets one of them as its private address ([Networking basics](Networking-Basics-for-This-Project.md#a-vpc-your-own-private-network-in-the-datacenter)). The stage 2 link back to a home network is where an overlap would hurt, which is why the range is chosen to avoid any home network and the repository records only "no overlap confirmed".
- **No NAT gateway.** A NAT gateway would let private-only droplets reach out, and costs more than the whole budget ([Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md)). So the droplets have a public address and a firewall with zero inbound rules, which is the "NAT is not protection, a firewall is" lesson in practice: no translation is involved, and nothing is reachable.
- **Tags** attach the firewalls, and rules between droplets name tags, not addresses ([DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md#tags-not-addresses-inside-the-vpc)).
- **CGNAT** is why a home VPN server may be impossible and why the connectors dial out ([Zero trust at home](Zero-Trust-at-Home-Two-Connectors-and-Failover.md#vpn-versus-ztna-under-real-residential-conditions)).

## Free path: a lab on your own computer

Everything in this section runs on your own computer and costs nothing; the lessons are free and will stay free. Every exercise follows four steps: **predict** (write down what you expect first), **do**, **check**, **undo**.

**Which track.** Exercises 1 and 2 work in **Bash** and **PowerShell**. Exercises 3 to 5 and the mini-loop use Linux network namespaces, which Windows does not have: on Windows run them in WSL 2 with the Bash commands (est.; not tested), and use the PowerShell commands given for reading your own firewall. On Windows call `python`, or `py`, where this page says `python3` (est.).

### Exercise 1: the arithmetic, by hand and then by machine

**Predict.** Using the five steps above and a pencil, answer all of these before you run anything:

a. How many addresses are in a `/27`?
b. Which `/28` block holds `10.78.0.37`, and what are its first and last addresses?
c. Where do the four `/26` blocks of `10.78.0.0/24` start?
d. Which `/20` block holds `10.78.37.9`?
e. What is the largest block (smallest prefix number) you can use that gives you at least 50 usable hosts on an ordinary network, and what is that prefix?
f. Does `10.78.0.0/24` overlap `10.78.0.128/25`? Does it overlap `192.168.1.0/24`?

**Do (Bash and PowerShell).** Make a folder and save this file in it as `cidr.py`:

```python
# cidr.py: the same arithmetic as the worksheet, done by Python's standard library.
import ipaddress as ip

for text in ["10.78.0.0/24", "10.78.0.0/26", "10.78.0.0/28", "10.78.0.0/16", "10.78.0.7/32"]:
    n = ip.ip_network(text)
    print(f"{text:14} mask {str(n.netmask):15} addresses {n.num_addresses:6} "
          f"first {n.network_address}  last {n.broadcast_address}")

print()
print("split a /24 into /26s:")
for sub in ip.ip_network("10.78.0.0/24").subnets(new_prefix=26):
    print("  ", sub)

print()
vpc = ip.ip_network("10.78.0.0/24")
for who in ["10.78.0.20", "10.78.1.20", "203.0.113.7"]:
    print(f"{who:12} in {vpc}?  {ip.ip_address(who) in vpc}")

print()
print("overlap (the stage 2 problem):",
      ip.ip_network("10.78.0.0/24").overlaps(ip.ip_network("10.78.0.128/25")),
      ip.ip_network("10.78.0.0/24").overlaps(ip.ip_network("192.168.1.0/24")))

print()
for a in ["10.78.0.20", "172.16.5.1", "172.32.0.1", "192.168.1.10", "100.64.3.4", "203.0.113.7"]:
    x = ip.ip_address(a)
    print(f"{a:12} is_private={str(x.is_private):5} is_global={str(x.is_global):5}"
          f"  in 100.64.0.0/10: {x in ip.ip_network('100.64.0.0/10')}")
```

```bash
mkdir -p ~/net-lab && cd ~/net-lab
python3 -I cidr.py
```

```powershell
New-Item -ItemType Directory -Force $HOME\net-lab | Out-Null
Set-Location $HOME\net-lab
python -I cidr.py
```

**Check.** On 2026-10-21 the first half of the output was (trimmed to the lines that answer the questions):

```text
10.78.0.0/24   mask 255.255.255.0   addresses    256 first 10.78.0.0  last 10.78.0.255
10.78.0.0/26   mask 255.255.255.192 addresses     64 first 10.78.0.0  last 10.78.0.63
10.78.0.0/28   mask 255.255.255.240 addresses     16 first 10.78.0.0  last 10.78.0.15
10.78.0.0/16   mask 255.255.0.0     addresses  65536 first 10.78.0.0  last 10.78.255.255

split a /24 into /26s:
   10.78.0.0/26
   10.78.0.64/26
   10.78.0.128/26
   10.78.0.192/26

overlap (the stage 2 problem): True False
```

Answers: (a) 32. (b) `10.78.0.32/28`, from `.32` to `.47`. (c) 0, 64, 128, 192. (d) `10.78.32.0/20`, which runs to `10.78.47.255` (the third octet moves in blocks of 16, and 37 sits in the block that starts at 32). (e) 50 + 2 = 52, rounded up to 64, so `/26`. (f) Yes to the first (the `/25` is the top half of the `/24`), no to the second. The script does not print (b), (d) or (e) for you: add lines to it to confirm them, for example `print(ip.ip_network("10.78.37.9/20", strict=False))`. `strict=False` is needed because `10.78.37.9` has host bits set, which the library refuses by default.

**PowerShell without Python (est.; not run).** Windows PowerShell 5.1 has no built-in subnet calculator, so here is the same arithmetic with bit math. It turns an address into one number, rounds down to a multiple of the block size, and turns it back. Newer .NET versions also have a `System.Net.IPNetwork` type with a `Contains` method (Microsoft Learn page read 2026-10-21; the minimum version was not read), but this version needs nothing new:

```powershell
function ConvertTo-IPv4Number([string]$Ip) {
    $b = ([System.Net.IPAddress]::Parse($Ip)).GetAddressBytes(); [Array]::Reverse($b)
    [uint64][BitConverter]::ToUInt32($b, 0)
}
function ConvertFrom-IPv4Number([uint64]$N) {
    $b = [BitConverter]::GetBytes([uint32]$N); [Array]::Reverse($b)
    ([System.Net.IPAddress]::new($b)).ToString()
}
function Show-Cidr([string]$Cidr) {
    $addr, $len = $Cidr -split '/'
    $size  = [uint64]1 -shl (32 - [int]$len)
    $n     = ConvertTo-IPv4Number $addr
    $first = $n - ($n % $size)
    [pscustomobject]@{ Cidr = $Cidr; Addresses = $size
                       First = (ConvertFrom-IPv4Number $first)
                       Last  = (ConvertFrom-IPv4Number ($first + $size - 1)) }
}
Show-Cidr 10.78.0.37/28     # expect First 10.78.0.32, Last 10.78.0.47
Show-Cidr 10.78.37.9/20     # expect First 10.78.32.0, Last 10.78.47.255
```

**Undo.** Nothing; these only print.

### Exercise 2: is it private?

**Predict.** For each of `10.78.0.20`, `172.16.5.1`, `172.32.0.1`, `192.168.1.10`, `100.64.3.4` and `203.0.113.7`, write down whether it is in an RFC 1918 block (yes or no), and then whether Python's `is_private` will say `True`.

**Do.** The last loop of `cidr.py` from Exercise 1 already ran it.

**Check.** The output:

```text
10.78.0.20   is_private=True  is_global=False  in 100.64.0.0/10: False
172.16.5.1   is_private=True  is_global=False  in 100.64.0.0/10: False
172.32.0.1   is_private=False is_global=True   in 100.64.0.0/10: False
192.168.1.10 is_private=True  is_global=False  in 100.64.0.0/10: False
100.64.3.4   is_private=False is_global=False  in 100.64.0.0/10: True
203.0.113.7  is_private=True  is_global=False  in 100.64.0.0/10: False
```

Read it carefully, because three rows surprise people. `172.32.0.1` is **outside** the `172.16.0.0/12` block (which ends at `172.31.255.255`), so it is an ordinary public address. `100.64.3.4` is neither private nor global: it is the shared CGNAT space, and Python's documentation lists it as an exception, with `is_private` false. And `203.0.113.7` reports `is_private=True` although it is not in RFC 1918: Python's `is_private` means "not globally reachable according to the IANA special-purpose registry" (I read the rule on 2026-10-21), which is wider than the three blocks. So `is_private` is a useful check and not a definition of RFC 1918. If a script must allow only the three blocks, test them by name with `in ip_network(...)`.

**Undo.** Nothing.

### The lab: three pretend machines in your own shell

Exercises 3 to 5 and the mini-loop use a Linux feature called a **network namespace**: a private copy of the network stack (its own interfaces, addresses, route table and firewall). `ip netns` makes them, a **veth pair** is a virtual cable between two of them, and a **bridge** is a virtual switch. Nothing leaves your computer.

To do it without `sudo`, you first make yourself "root" inside a **user namespace**, with private mounts and process list as well. [`unshare`](https://man7.org/linux/man-pages/man1/unshare.1.html) does all of that in one command, and when the shell it starts exits, every process, namespace and rule inside it is destroyed. That exit is the whole cleanup.

```bash
unshare -Urnmpf --mount-proc bash
```

`-U` is a new user namespace, `-r` maps you to root inside it, `-n` a new network namespace, `-m` private mounts, `-p -f` a new process list (so leftover servers die with the shell), and `--mount-proc` makes `ps` see it. You are not root on the real machine; the prompt may say `root`, and it means root in the pretend one.

If the command fails with `Operation not permitted`, your distribution may be restricting unprivileged user namespaces (some Ubuntu releases do this by default, est.). The fallback is `sudo unshare -nmpf --mount-proc bash`: you are then real root on the machine, so type only what this page gives you, which touches only the new namespaces (est.; not run).

Save these files in `~/net-lab` first, from a normal terminal. `portcheck.py` is a tiny TCP connect check. It reports **open** (something answered), **closed** (the machine replied "nobody here", a reset) or **filtered** (silence until the timeout, which is what a firewall that drops packets looks like):

```python
# portcheck.py HOST PORT [PORT ...]   (ranges: 20000-20050)
# A tiny TCP connect check. open = something answered; closed = the host replied
# "nobody here" (a reset); filtered = silence until the timeout.
import os, socket, sys
from concurrent.futures import ThreadPoolExecutor

def check(host, port, timeout=float(os.environ.get("PC_TIMEOUT", "1"))):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return "open"
    except ConnectionRefusedError:
        return "closed"
    except (socket.timeout, TimeoutError):
        return "filtered"
    except OSError as e:
        return "error: %s" % e
    finally:
        s.close()

ports = []
for arg in sys.argv[2:]:
    lo, _, hi = arg.partition("-")
    ports += range(int(lo), int(hi or lo) + 1)
with ThreadPoolExecutor(max_workers=64) as pool:
    results = list(pool.map(lambda p: (p, check(sys.argv[1], p)), ports))
many = len(ports) > 20          # a long list shows only what answered
for p, state in results:
    if not many or state == "open":
        print("%5d/tcp  %s" % (p, state))
counts = {}
for _, state in results:
    counts[state] = counts.get(state, 0) + 1
print("%d ports checked: %s" % (len(ports), ", ".join("%d %s" % (n, s) for s, n in sorted(counts.items()))))
```

`listen.py` is a server that answers every connection with one line:

```python
# listen.py ADDRESS PORT [PORT ...]  - answer each connection with one line, then close.
import socket, sys, threading

def serve(addr, port):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((addr, port))
    s.listen(16)
    while True:
        c, peer = s.accept()
        c.sendall(("port %d says hello; you are %s:%d\n" % (port, peer[0], peer[1])).encode())
        c.close()

for p in sys.argv[2:]:
    threading.Thread(target=serve, args=(sys.argv[1], int(p)), daemon=True).start()
threading.Event().wait()
```

`ask.py` is a client that prints that line:

```python
# ask.py HOST PORT : connect, print the one line the server sends back (or what went wrong).
import socket, sys
try:
    with socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=2) as s:
        print(s.recv(200).decode().strip())
except OSError as e:
    print("failed:", e)
```

`setup.sh` builds the pretend network: a switch, three machines named `srv`, `cli` and `oth` on `10.78.0.0/24`, and servers on `srv` at ports 22, 8080 and 8443:

```bash
#!/usr/bin/env bash
# Builds three pretend machines on one pretend switch, all inside your own shell.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
mount -t tmpfs tmpfs /run && mkdir -p /run/netns          # private to this shell
for n in lan srv cli oth; do ip netns add "$n"; ip -n "$n" link set lo up; done
ip -n lan link add br0 type bridge; ip -n lan link set br0 up
for pair in "srv 10.78.0.10" "cli 10.78.0.20" "oth 10.78.0.30"; do
  set -- $pair
  ip -n lan link add "p-$1" type veth peer name eth0 netns "$1"
  ip -n lan link set "p-$1" master br0; ip -n lan link set "p-$1" up
  ip -n "$1" addr add "$2/24" dev eth0; ip -n "$1" link set eth0 up
done
ip netns exec srv python3 "$here/listen.py" 10.78.0.10 22 8080 8443 > /dev/null 2>&1 &
sleep 0.5
echo "lab ready: srv 10.78.0.10, cli 10.78.0.20, oth 10.78.0.30, all in 10.78.0.0/24"
```

Then, in the new shell, build it once:

```bash
cd ~/net-lab
bash setup.sh
```

You use a pretend machine by putting `ip netns exec NAME` in front of a command. Use a fresh `unshare` shell (exit, then start again) for each of the two labs: the NAT lab in Exercise 3 and the firewall lab in Exercises 4 and 5 and the mini-loop.

### Exercise 3: routes and NAT, the home-router lab

This lab is separate from `setup.sh`. Start a new `unshare` shell and save `natlab.sh`, which builds a home-style router: an `inside` machine on a private `/24`, a `router` with a foot in each network, and an `outside` machine on a "public" documentation range:

```bash
#!/usr/bin/env bash
# A home-style router between a private network and a "public" one.
# Addresses are documentation ranges (RFC 5737) plus a private /24.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
mount -t tmpfs tmpfs /run && mkdir -p /run/netns
for n in inside router outside; do ip netns add "$n"; ip -n "$n" link set lo up; done
ip link add i0 type veth peer name r0 ; ip link set i0 netns inside ; ip link set r0 netns router
ip link add r1 type veth peer name o0 ; ip link set r1 netns router ; ip link set o0 netns outside
ip -n inside  addr add 192.168.50.2/24 dev i0 ; ip -n inside  link set i0 up
ip -n router  addr add 192.168.50.1/24 dev r0 ; ip -n router  link set r0 up
ip -n router  addr add 203.0.113.1/24  dev r1 ; ip -n router  link set r1 up
ip -n outside addr add 203.0.113.50/24 dev o0 ; ip -n outside link set o0 up
ip -n inside route add default via 192.168.50.1
ip netns exec router sysctl -qw net.ipv4.ip_forward=1
ip netns exec inside  python3 "$here/listen.py" 192.168.50.2 8080 >/dev/null 2>&1 &
ip netns exec outside python3 "$here/listen.py" 203.0.113.50 9000 >/dev/null 2>&1 &
sleep 0.5
echo "nat lab ready"
```

```bash
cd ~/net-lab
bash natlab.sh
```

**Predict.** `inside` is `192.168.50.2` with a default route through the router; `outside` is `203.0.113.50` and has no route to `192.168.50.0/24`. (1) What does `outside` say when you ask it to reach `192.168.50.2`? (2) The router forwards packets but does no translation yet. If `inside` connects to `outside`, does it work? (3) After you add masquerade, what source address does the server on `outside` see? (4) Can `outside` reach the inside server on port 8080 before a port-forward rule exists? After?

**Do (Bash; WSL 2 on Windows, est.).**

```bash
ip -n inside route
ip -n inside route get 203.0.113.50
ip -n outside route
ip -n outside route get 192.168.50.2
ip netns exec inside python3 ask.py 203.0.113.50 9000
```

Now turn on masquerade on the router for packets leaving through its outside interface (`r1`), and try again:

```bash
ip netns exec router nft -f - <<'RULES'
table ip nat {
  chain postrouting {
    type nat hook postrouting priority srcnat;
    oifname "r1" masquerade
  }
}
RULES
ip netns exec inside python3 ask.py 203.0.113.50 9000
ip netns exec router cat /proc/net/nf_conntrack
```

Then the outside view, and a port forward:

```bash
ip netns exec outside python3 ask.py 192.168.50.2 8080
ip netns exec outside python3 ask.py 203.0.113.1 8080
ip netns exec router nft add chain ip nat prerouting '{ type nat hook prerouting priority dstnat; }'
ip netns exec router nft add rule ip nat prerouting iifname '"r1"' tcp dport 8080 dnat to 192.168.50.2:8080
ip netns exec outside python3 ask.py 203.0.113.1 8080
```

**Do (PowerShell).** There is no PowerShell equivalent of the lab; use WSL 2. To read the same ideas on Windows, `route print` shows your route table, and `Get-NetRoute -AddressFamily IPv4` (est.) lists it as objects.

**Check.** Trimmed from the 2026-10-21 run:

```text
default via 192.168.50.1 dev i0
192.168.50.0/24 dev i0 proto kernel scope link src 192.168.50.2
203.0.113.50 via 192.168.50.1 dev i0 src 192.168.50.2 uid 0
203.0.113.0/24 dev o0 proto kernel scope link src 203.0.113.50
RTNETLINK answers: Network is unreachable
failed: timed out                                       <- inside to outside, no NAT yet
port 9000 says hello; you are 203.0.113.1:47460         <- after masquerade
ipv4 2 tcp 6 119 TIME_WAIT src=192.168.50.2 dst=203.0.113.50 sport=47460 dport=9000 src=203.0.113.50 dst=203.0.113.1 sport=9000 dport=47460 [ASSURED] ...
failed: [Errno 101] Network is unreachable              <- outside to 192.168.50.2
failed: [Errno 111] Connection refused                  <- outside to the router, no forward yet
port 8080 says hello; you are 203.0.113.50:39470        <- after the port forward
```

Read it in order. The first four lines are route tables: `inside` has a connected route and a default route; `outside` has only its own subnet, so asking for a route to `192.168.50.2` fails on the spot with *Network is unreachable* (the machine never sent anything). Before NAT, `inside`'s packet does reach `outside`, but the reply is addressed to a private address `outside` cannot route to, so the connection times out: **a timeout, not a refusal**. After masquerade the server sees the **router's** address (`203.0.113.1`), and the `nf_conntrack` line is the router's memory: the first address pair is what `inside` sent, the second is what the reply looks like, with the translated address in it. To `outside`, the router's own port 8080 is *refused* until the forward rule exists (the router has nothing listening there), and afterwards the connection reaches the inside server. Note that the server sees `203.0.113.50` as the client: a port forward changes the destination and leaves the source alone. Port numbers will differ.

**Now the part that matters: NAT is not a firewall.** Give `outside` a route to the inside network through the router, as a machine sharing the router's outside link could do, and ask again:

```bash
ip -n outside route add 192.168.50.0/24 via 203.0.113.1
ip netns exec outside python3 ask.py 192.168.50.2 8080
```

The output is `port 8080 says hello; you are 203.0.113.50:...`: the router translated nothing and still forwarded the packet, and the inside server answered. Fix it with a firewall on the router's **forward** chain (packets passing through, not to it): default deny, with the two exceptions a home router has.

```bash
ip netns exec router nft -f - <<'RULES'
table inet fw {
  chain forward {
    type filter hook forward priority 0; policy drop;
    ct state established,related accept
    iifname "r0" oifname "r1" accept
  }
}
RULES
ip netns exec outside python3 ask.py 192.168.50.2 8080
ip netns exec inside python3 ask.py 203.0.113.50 9000
ip netns exec outside python3 ask.py 203.0.113.1 8080
```

The outside attempt to the inside address now times out (dropped), the inside machine can still reach out, and the port forward **stops working**: the third command times out too, because a forwarded packet is a forwarded packet and the new default-deny chain drops it. A port forward takes two rules, the translation and a deliberate forward allow. Add the second and test again:

```bash
ip netns exec router nft add rule inet fw forward iifname '"r1"' oifname '"r0"' ip daddr 192.168.50.2 tcp dport 8080 accept
ip netns exec outside python3 ask.py 203.0.113.1 8080
```

The last command answers again. That second rule is the one a reviewer should read: it is the line that decides what the internet can touch.

**Undo.** Type `exit`. Every namespace, rule and server was inside that shell and is gone. In an ordinary shell, `ip netns list` shows none of them.

### Exercise 4: stateful or not

Exit the NAT lab, start a fresh `unshare` shell, and build the firewall lab: `cd ~/net-lab && bash setup.sh`.

**Predict.** On the pretend machine `cli` you will drop all inbound traffic except loopback, then connect **out** to the server on `srv`, port 8080. The outgoing request is not blocked, because only the input is filtered. Will the connection work? Then you add one rule, `ct state established,related accept`. Will it work now?

**Do (Bash; WSL 2 on Windows, est.).**

```bash
ip netns exec cli nft -f - <<'RULES'
table inet t {
  chain input {
    type filter hook input priority 0; policy drop;
    iifname "lo" accept
  }
}
RULES
ip netns exec cli python3 portcheck.py 10.78.0.10 8080
ip netns exec cli nft add rule inet t input ct state established,related accept
ip netns exec cli python3 portcheck.py 10.78.0.10 8080
ip netns exec cli nft delete table inet t
```

**Check.**

```text
 8080/tcp  filtered
1 ports checked: 1 filtered
 8080/tcp  open
1 ports checked: 1 open
```

The first attempt fails because the server's reply is itself an inbound packet, and with default deny and no state rule it matches nothing. `cli` sent its request and heard nothing, which is what a firewall drop looks like from the sender's side: `filtered`. The state rule teaches the firewall to recognize that reply, and nothing else about its policy changed. A stateless filter would need a rule such as "accept anything from source port 8080", which also admits anyone who picks that source port. On the cloud side, DigitalOcean's documentation says its cloud firewall is stateful and tracks connection state on the droplet's host machine.

**Undo.** The last command removed the table. (`exit` removes everything.)

### Exercise 5: load and read this repository's host firewall

**Predict.** Using the `cah_host` table from [Reading a rule set](#a-rule-set-from-this-repository-the-host-firewall) and without running anything: from `cli` (`10.78.0.20`) and from `oth` (`10.78.0.30`), which of ports 22 and 8080 on `srv` will be open?

**Do (Bash; WSL 2 on Windows, est.).** Load the rendered table onto `srv`, then scan from both machines:

```bash
ip netns exec srv nft -f - <<'RULES'
table inet cah_host
delete table inet cah_host
table inet cah_host {
  chain input {
    type filter hook input priority 0; policy drop;
    iifname "lo" accept
    ct state established,related accept
    ct state invalid drop
    icmp type { echo-request, destination-unreachable, time-exceeded } accept
    icmpv6 type { destination-unreachable, packet-too-big, time-exceeded, echo-request, nd-router-advert, nd-neighbor-solicit, nd-neighbor-advert } accept
    udp sport 67 udp dport 68 accept
    tcp dport 22 ip saddr { 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 } accept
  }
}
RULES
ip netns exec cli python3 portcheck.py 10.78.0.10 22 8080
ip netns exec oth python3 portcheck.py 10.78.0.10 22 8080
ip netns exec srv nft delete table inet cah_host
```

The first two lines (`table` then `delete table`) are an idiom the repository's script also uses, so the file loads whether or not the table already exists. This page's copy is made from the template with the defaults filled in; check it against `modules/twingate-bootstrap/cloud-init.yaml.tftpl` if that file has changed since 2026-10-21.

**Do (PowerShell, read only, est.).** On Windows, look at your own firewall without changing it. The first command shows each profile's default actions; the second lists a few enabled inbound allow rules:

```powershell
Get-NetFirewallProfile | Format-Table Name, Enabled, DefaultInboundAction, DefaultOutboundAction
Get-NetFirewallRule -Direction Inbound -Enabled True -Action Allow | Select-Object -First 10 DisplayName, Profile
```

**Check.** Both machines see port 22 open and 8080 filtered:

```text
   22/tcp  open
 8080/tcp  filtered
2 ports checked: 1 filtered, 1 open
```

`oth` gets in as well, because `10.78.0.30` is inside `10.0.0.0/8`. That is the documented default: the module's variable description says it narrows access to private space only "because this module does not know the VPC CIDR", with the cloud firewall as the layer that limits SSH to the connector tag. Compare that with the `admins` set you write in the mini-loop, which names one address. The same idea at two widths is the whole skill: the narrower the source, the fewer machines could ever misuse the rule. On Windows, a default inbound action of `Block` is default deny.

**Undo.** The last command removed the table.

## Optional: the same loop on a real cloud firewall (your own account)

This path puts the server and the scanner on two droplets in one private network, with a real firewall between nothing and everything. It is optional: the free path above teaches every concept, and this one adds two things the lab cannot: a firewall you do not run yourself, and the fact that DigitalOcean's firewall keeps no traffic log (so detection needs a second layer). It uses **your own** cloud account and **your own** bill. Read the cost and the teardown first.

> **Status of this path: written from the `doctl` documentation, never run.** Flags were checked against the `doctl` reference pages on 2026-10-21 (listed in the claims register). Whether a tag-sourced rule matches traffic over the private network exactly as written is **est.**; if the scanner cannot reach the server on a port you allowed, check that first. Run it expecting to fix something.

### Cost and teardown (read first)

- **Cost.** Two droplets of size `s-1vcpu-1gb`. [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json) (retrieved 2026-10-21) lists that size at $6 a month each, so **up to $12 a month at list price while both exist**; [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) explains how the project prices droplets. DigitalOcean's pricing page (read 2026-10-21) says bundled-plan droplets are billed per second with a minimum charge of 60 seconds or $0.01, whichever is higher, capped at 672 hours a month, and that **a powered-off droplet is still billed: destroying it ends billing**. I did not read an hourly rate, so I give no per-hour figure. The firewalls are free according to DigitalOcean's firewall page ("provided at no additional cost"). I did not read a price for a private network (VPC), and I expect none (est.). Check size and region availability in your own account first.
- **Never leave them running.** Set a calendar reminder for one hour from now.
- **Teardown** (listed again at the end with the proof):

```bash
doctl compute droplet delete net-lab-srv net-lab-scan --force
doctl compute firewall list --format ID,Name        # note the two net-lab ids
doctl compute firewall delete FIREWALL_ID_1 FIREWALL_ID_2 --force
doctl compute tag delete net-lab-srv net-lab-scan --force
doctl vpcs list --format ID,Name                     # note the net-lab id
doctl vpcs delete VPC_ID --force
```

- **Targets.** The only machines you probe are the two you create here. Do not point `portcheck.py` at the droplet's public address from anywhere you are not allowed to, and never at anything that is not yours.
- **Data rules.** No real data goes on these machines. Use a token that is as narrow as the [identity page](Identity-Secrets-and-Zero-Trust-Basics.md) and the [secrets page](Doppler-and-Secrets.md) teach, and revoke it afterwards if you made it just for this.

### The design

```text
  your laptop --ssh (only from your /32)--> scan droplet --ssh and port checks (private)--> srv droplet
                                              public address: inbound 22 from your /32       public address: inbound NOTHING from the internet
                                              outbound: any TCP port, only to tag net-lab-srv   inbound 22 only from tag net-lab-scan
                                                  both in one private network, 10.98.0.0/24 here
```

The server's firewall is the one you will break and fix. It starts with a single inbound rule: SSH from the scanner's tag. The scanner is **in your account, in the same private network**, so a port check from it is a check you are allowed to make. The server's test listener binds to its **private** address only. That matters: when you add the over-permissive rule, the firewall really will admit the whole internet to port 8080 on the public address, and the only reason nothing answers there is that nothing listens on the public address. A hole in the firewall is a hole even when the server happens to save you, so close it in the Defend step and do not rebind the listener to all addresses to "make the test clearer".

### Steps

Placeholders: replace `203.0.113.7` with your own current public address (a documentation address, not yours). Behind carrier-grade NAT your visible address is shared with other households, so a `/32` is wider than it looks; if you are behind CGNAT, do not use this path from that connection.

```bash
export REGION=tor1 SIZE=s-1vcpu-1gb IMAGE=ubuntu-24-04-x64
export MY_IP=203.0.113.7
doctl compute ssh-key list --format ID,Name,FingerPrint      # pick the key you use; note its ID
export KEY_ID=YOUR_KEY_ID

# 1. A private network just for this lab. Pick a range that overlaps nothing of yours.
doctl vpcs create --name net-lab --region "$REGION" --ip-range 10.98.0.0/24
doctl vpcs list --format ID,Name --no-header                  # note the net-lab id
export VPC_ID=YOUR_VPC_ID

# 2. Tags and firewalls BEFORE the droplets, so they are never open, even for a minute.
doctl compute tag create net-lab-srv
doctl compute tag create net-lab-scan
doctl compute firewall create --name net-lab-srv --tag-names net-lab-srv \
  --inbound-rules "protocol:tcp,ports:22,tag:net-lab-scan"
doctl compute firewall create --name net-lab-scan --tag-names net-lab-scan \
  --inbound-rules "protocol:tcp,ports:22,address:${MY_IP}/32" \
  --outbound-rules "protocol:tcp,ports:1-65535,tag:net-lab-srv"

# 3. The two droplets.
doctl compute droplet create net-lab-srv --region "$REGION" --size "$SIZE" --image "$IMAGE" \
  --vpc-uuid "$VPC_ID" --ssh-keys "$KEY_ID" --tag-names net-lab-srv --wait
doctl compute droplet create net-lab-scan --region "$REGION" --size "$SIZE" --image "$IMAGE" \
  --vpc-uuid "$VPC_ID" --ssh-keys "$KEY_ID" --tag-names net-lab-scan --wait

# 4. The addresses and the server firewall's id.
export SCAN_PUB=$(doctl compute droplet get net-lab-scan --format PublicIPv4 --no-header)
export SRV_PUB=$(doctl compute droplet get net-lab-srv --format PublicIPv4 --no-header)
export SRV_PRIV=$(doctl compute droplet get net-lab-srv --format PrivateIPv4 --no-header)
doctl compute firewall list --format ID,Name                  # note the net-lab-srv id
export SRV_FW=YOUR_SERVER_FIREWALL_ID
```

In PowerShell write `$env:REGION = "tor1"` style assignments, put `$SCAN_PUB = (doctl compute droplet get net-lab-scan --format PublicIPv4 --no-header)` for the addresses, and write the multi-line commands on one line (or end each line with a backtick); the `doctl` flags are identical (est.). Run the lines one at a time. Rules in `doctl` are written `protocol:tcp,ports:22,tag:NAME` or `...,address:CIDR`, and several are separated by a space inside one quoted string. The range form `ports:1-65535` is **est.**: the reference page shows single ports.

**Copy the two small files in and start the server.** Use `listen.py` and `portcheck.py` from the free path. The first connection to each machine asks you to accept its host key; for a machine you just made, accepting is reasonable (an unexpected change later is not). Both machines are reached through the scanner, which is the only one with a rule for your address:

```bash
scp -J root@"$SCAN_PUB" listen.py root@"$SRV_PRIV":
scp portcheck.py root@"$SCAN_PUB":
ssh -J root@"$SCAN_PUB" root@"$SRV_PRIV" "nohup python3 listen.py $SRV_PRIV 8080 8443 > listen.log 2>&1 < /dev/null &"
```

(The Ubuntu image includes `python3`, est.; check on the droplet.)

**Build: check the default-deny rule set.** Log in to the scanner and check the server from inside the account:

```bash
ssh root@"$SCAN_PUB"
```

On the scanner (replace the address with the one you noted as `SRV_PRIV`):

```bash
python3 portcheck.py 10.98.0.X 22 80 8080 8443
```

Expected (est.): 22 `open` (the one rule), and 80, 8080 and 8443 `filtered`. Ports 8080 and 8443 have a listener and are still filtered: that is the firewall, not the program. Then `exit` to your laptop.

**Break: the one-line mistake.** From the laptop, add the rule an impatient person adds to "get the demo working": port 8080, from anywhere.

```bash
doctl compute firewall add-rules "$SRV_FW" --inbound-rules "protocol:tcp,ports:8080,address:0.0.0.0/0"
```

Give it a few seconds to apply (est.), then from the scanner run the same `portcheck.py` command. Port 8080 now reads `open`. That is Detect, version one.

**Detect, three ways.**

1. *The scan from the second host*, as above. It tells you what is reachable, from where you stand.
2. *The rule list.* `doctl compute firewall list --format ID,Name,InboundRules` prints the rules (est.). `0.0.0.0/0` on a port is the thing to look for; a review that only reads this list finds the hole without sending a packet.
3. *A log on the host.* DigitalOcean's limits page says traffic logs are not available for its cloud firewall, because it blocks traffic before it reaches the droplet. So the log has to come from the server itself. Log in to the server through the scanner and add a rule that only logs and changes nothing:

```bash
ssh -J root@"$SCAN_PUB" root@"$SRV_PRIV"
```

On the server:

```bash
nft add table inet labwatch
nft add chain inet labwatch input '{ type filter hook input priority -10; policy accept; }'
nft add rule inet labwatch input tcp dport 8080 ct state new log prefix \"net-lab-8080: \" level info
```

Run the port check from the scanner again, then on the server read the kernel log: `journalctl -k --since "10 min ago" | grep net-lab-8080`. Expect (est.) a line with `SRC=` the scanner's private address and `DPT=8080`. With the hole open to `0.0.0.0/0`, you may also see sources you do not recognize: that is what the whole internet looks like to a port that is open, and it is the reason to close it. This is the same kind of rule as the one in the repository's host firewall, only with a `log` statement. Remove the log table when you finish: `nft delete table inet labwatch`.

**Evade, in words.** The folk fix is "move the service to an odd port and nobody will find it." Your scanner just answered why that does not work: the port check lists every port in a range in seconds, and a firewall rule that admits `0.0.0.0/0` on the odd port admits everyone who finds it, however they found it. The free path runs this on the lab. Obscurity changes how long it takes to find the door and nothing about who may walk through it.

**Defend: close it and verify with the same scan.**

```bash
doctl compute firewall remove-rules "$SRV_FW" --inbound-rules "protocol:tcp,ports:8080,address:0.0.0.0/0"
```

Wait a few seconds, then run the **same** `portcheck.py` command on the scanner: 8080 is `filtered` again. Using the same command both times is the point; it is your test, and the only change is the rule. If you do want the scanner to use 8080, say so with a source, not an address range:

```bash
doctl compute firewall add-rules "$SRV_FW" --inbound-rules "protocol:tcp,ports:8080,tag:net-lab-scan"
```

Now 8080 is `open` from the scanner and still `filtered` from everywhere else. Prove the second half from your laptop against your own server's public address (a machine you own, in an account you control):

```bash
python3 portcheck.py "$SRV_PUB" 22 8080
```

```powershell
python portcheck.py $SRV_PUB 22 8080
Test-NetConnection -ComputerName $SRV_PUB -Port 8080 -InformationLevel Quiet
```

Both ports should be `filtered` (the PowerShell command should print `False` after a wait, est.).

**Now tear down**, using the commands at the top of this section.

### Prove it is gone

```bash
doctl compute droplet list
doctl compute firewall list
doctl compute tag list
doctl vpcs list
```

Read-only; nothing named `net-lab` should remain. Billing data lags: look at the billing page again tomorrow (the habit in the [teardown checklist](Teardown-Checklist.md#3-prove-zero-billable-resources)). Remove the two droplets' entries from `~/.ssh/known_hosts` if you want a tidy file, and revoke any token you made for this.

## Build, break, detect, evade, defend (the local loop)

The same loop, with no cloud account. Start a fresh `unshare` shell, `cd ~/net-lab`, and run `bash setup.sh`. Save this as `srv-rules.nft`: a default-deny rule set for `srv` that lets one address, `cli`, in on SSH. The `admins` set plays the part of a tag.

```text
table inet lab
delete table inet lab
table inet lab {
  set admins {
    type ipv4_addr
    elements = { 10.78.0.20 }
  }
  chain input {
    type filter hook input priority 0; policy drop;
    iifname "lo" accept
    ct state established,related accept
    ct state invalid drop
    icmp type echo-request accept
    ip saddr @admins tcp dport 22 counter accept
    counter
  }
}
```

**Build.** Load it, read it, and take the baseline with the same check from both machines:

```bash
ip netns exec srv nft -f srv-rules.nft
ip netns exec srv nft list chain inet lab input
ip netns exec cli python3 portcheck.py 10.78.0.10 22 80 8080 8443
ip netns exec oth python3 portcheck.py 10.78.0.10 22 80 8080 8443
```

Read the rule set top to bottom. The chain's `policy drop` is default deny. `counter` after the last rule counts every packet that reached the end without being accepted, which is the number of packets about to be dropped. Expect `cli` to see 22 open and the rest filtered, and `oth` to see all four filtered. (Ping from `oth` still works, because of the `icmp type echo-request accept` line.)

**Break.** Insert the impatient rule at the top of the chain (`insert`, because the order matters: it goes first), then repeat the check from `oth`:

```bash
ip netns exec srv nft insert rule inet lab input tcp dport 8080 counter accept
ip netns exec oth python3 portcheck.py 10.78.0.10 22 80 8080 8443
```

**Detect.** Two views. The scan shows the hole: 8080 open to a machine that should have no access (the second-host scan of the cloud path). The firewall's counter shows that the hole is being hit:

```bash
ip netns exec srv nft -a list chain inet lab input
```

```text
table inet lab {
	chain input { # handle 1
		type filter hook input priority filter; policy drop;
		tcp dport 8080 counter packets 4 bytes 204 accept # handle 9
		iifname "lo" accept # handle 3
		ct state established,related accept # handle 4
		ct state invalid drop # handle 5
		icmp type echo-request accept # handle 6
		ip saddr @admins tcp dport 22 counter packets 1 bytes 60 accept # handle 7
		counter packets 10 bytes 600 # handle 8
	}
}
```

The new rule's counter has packets on it, so something is using a rule you did not mean to have. A counter holds packet and byte totals only: it does **not** record who sent them, so on its own it cannot say whether the packets came from `oth`, from `cli` or from a stranger. Attribution needs one of two things. In the lab, a source-specific rule: add `ip saddr 10.78.0.30 tcp dport 8080 counter` above the broad one and run the check again; only that counter moves for `oth`. On a real machine, a `log` rule with a prefix, which writes the source address of each matching packet to the kernel log (read it with `journalctl -k` or `dmesg`; the cloud path below does exactly this). `-a` shows each rule's **handle**, the number you use to delete it. The packet counts are small because the check sends few packets; yours will differ. A `log` rule loads in the lab without error, but I did not find a way to read its output from inside the lab (est. reason: the kernel log belongs to the real machine, not to a pretend one), so the counters stand in for the log here; the cloud path shows a `log` rule on a real server.

**Evade (in words, then one run).** An administrator who is told "that port is exposed" might "hide" it instead of fixing it: move a service to port 20222 and open that port to anyone. Run exactly that and then do what an attacker's tool does, check a whole range:

```bash
ip netns exec srv python3 listen.py 10.78.0.10 20222 > /dev/null 2>&1 &
ip netns exec srv nft add rule inet lab input tcp dport 20222 accept
ip netns exec oth env PC_TIMEOUT=0.3 python3 portcheck.py 10.78.0.10 20000-20400
```

The output is `20222/tcp  open` and `401 ports checked: 400 filtered, 1 open`, in about two seconds. Hiding a service on an odd port bought two seconds. (Real scanners do all 65,535 ports; a figure for how long that takes against a real network is **est.**, not measured here, and depends on the network.) The point is the rule, not the port number: the odd port was open to **anyone**.

**Defend.** Delete the two rules that name no source, by handle; let `admins` reach 8080 if it should (inserted above the counter); then run the same checks:

```bash
for h in $(ip netns exec srv nft -a list chain inet lab input | awk '/tcp dport (8080|20222) / && !/saddr/ {print $NF}'); do
  ip netns exec srv nft delete rule inet lab input handle "$h"
done
ip netns exec srv nft insert rule inet lab input ip saddr @admins tcp dport 8080 accept
ip netns exec oth python3 portcheck.py 10.78.0.10 22 80 8080 8443
ip netns exec oth env PC_TIMEOUT=0.3 python3 portcheck.py 10.78.0.10 20000-20400
ip netns exec cli python3 portcheck.py 10.78.0.10 22 8080
```

From `oth`: everything filtered, and `401 ports checked: 401 filtered`. From `cli`: 22 and 8080 open. The rule set is back to default deny, and the exception names a set, not the world. The defenses, in the order they matter: **default deny** (so a forgotten rule fails safe); **allow by source, port and protocol** (so a rule names who); **tags or sets** for sources (so a rule survives a rebuild and has no prefix length to mistype); **re-scan with the same check** after every change; and a **second layer** (the host firewall behind the cloud firewall) so one mistake is not the whole story.

**Undo.** Type `exit`. The servers, rules and namespaces are all gone.

### Flip the board

You wrote the rules and the scan. Now do the other two jobs.

**The reviewer.** Someone hands you this rule set (the file `review.nft`, which parses) and asks "is it safe to deploy on a server that holds a database?" Find at least four problems without running it.

```text
table inet review {
  chain input {
    type filter hook input priority 0; policy accept;
    ct state established,related accept
    tcp dport 22 accept
    tcp dport { 3306, 5432 } ip saddr 10.0.0.0/8 accept
    tcp dport 8080-9090 accept
    ip saddr 203.0.113.0/24 accept
  }
}
```

<details>
<summary>What to find</summary>

1. `policy accept`: the chain is **default allow**, so every port not named is open and the list of rules is only a list of things someone thought to allow, which changes nothing. It should be `policy drop`.
2. `tcp dport 22 accept` has no source: SSH is open to the whole internet.
3. `tcp dport { 3306, 5432 } ip saddr 10.0.0.0/8 accept` opens the database ports to all 16.7 million addresses of `10.0.0.0/8`. A server in a cloud network shares that space with every other machine in the same network, and with any network joined to it. Name the application servers, or their tag.
4. `tcp dport 8080-9090 accept` opens a range of 1,011 ports to anyone, "just in case" (a range is the easy way to open the port you meant and 1,010 you did not).
5. `ip saddr 203.0.113.0/24 accept` has no port or protocol: every port is open to a whole `/24`. A rule that names only a source is a trust grant, not a firewall rule.
6. Smaller: there is no `ct state invalid drop`, no loopback rule, and no counter or log to tell you which rule is used. None of them is dangerous alone.

</details>

**The scanner.** You are given only this output, from a machine you have no other access to, and you must say what you can without guessing:

```text
   22/tcp  open
   80/tcp  closed
 8080/tcp  filtered
```

What is the difference between `closed` and `filtered`, and what does each tell you about the machine and its firewall? (Answer: `closed` means a packet reached the machine and its network stack replied "nothing here": usually no firewall dropped it on that port (a firewall can also be set to reject, est.), and no program is listening. `filtered` means silence: something dropped the packet, so there is a firewall or a network device between you, or the host did not answer, and you cannot tell whether a program listens. `open` means a program answered. [Nmap's documentation](https://nmap.org/book/man-port-scanning-basics.html) describes the same three states, and adds that they describe how the scan sees the port, not a property of the port itself: a scan from inside the same network can show a different result than one from across the internet.)

Defenders who can read a scan the way an attacker does catch the hole before the attacker does; attackers who can read a rule set know which doors to try. Do both, in that order.

## Checkpoint

- Without a calculator: how many addresses are in a `/27`, which `/26` holds `10.78.0.130`, and what is the smallest block that holds 100 hosts?
- Name the three RFC 1918 blocks and say what `100.64.0.0/10` is, and why `is_private` in Python and "RFC 1918" are not the same test.
- What does NAT hide, what does it not protect, and what does protect?
- Explain, in one sentence each, default deny, stateful, and "allow by source, port and protocol".
- A port scan shows `filtered` for a port you opened in a rule five minutes ago. Name three things to check.

Answers are in the sections above. (For the last: the rule's source does not include the scanner; the rule has not applied yet, or applies to a different firewall or tag; something else, a host firewall, or a second cloud firewall, is also dropping it. Whether the program is listening only matters once the packet gets through.)

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| `Network is unreachable` at once | The machine has no route to that block | `ip route get ADDRESS` (Linux), `route print` or `Get-NetRoute` (Windows). No default route or no connected route. |
| A connection times out after a wait | A drop: a firewall, or a reply that cannot get back (a private source with no NAT) | Which layer drops it, and does the reply have a route home? |
| `Connection refused` straight away | The packet arrived and nothing is listening on that port | The service, its port and the address it is bound to (`ss -tlnp`). A firewall would be silent, not refusing. |
| Two networks work alone and fail when joined | Overlapping address ranges | Compare the blocks with `ip_network(...).overlaps(...)` before you connect them. |
| A rule "should" allow it and the connection fails | Only one direction has a rule, or the stateful rule is missing | New connections need a rule in both directions on a cloud firewall; replies need none. |
| `unshare: ... Operation not permitted` | Unprivileged user namespaces are restricted on this machine | The fallback with `sudo`, or a virtual machine (est.). |
| A lab command says `Cannot open network namespace` | You are in a different shell from the one that ran `setup.sh` | Run it in the shell you started with `unshare`. Leaving the shell destroys the lab. |

## Claims register

All read-only requests; retrieved 2026-10-21 unless stated. "Observed" means I ran it that day.

| Claim | Source | Status |
|---|---|---|
| Three private IPv4 blocks: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`; private addresses should not be forwarded across links between enterprises | [RFC 1918](https://www.rfc-editor.org/rfc/rfc1918) | Read |
| `100.64.0.0/10` is the Shared Address Space for carrier-grade NAT | [RFC 6598](https://www.rfc-editor.org/rfc/rfc6598) | Read |
| `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24` are documentation ranges | [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737) | Read the first of the three in detail; the other two were not read separately |
| CIDR replaced the class A/B/C system with variable-length prefixes | [RFC 4632](https://www.rfc-editor.org/rfc/rfc4632) | Phrase found; the detail was not read |
| NAT as address translation at a border; endpoint mapping behaviors exist | [RFC 3022](https://www.rfc-editor.org/rfc/rfc3022), [RFC 4787](https://www.rfc-editor.org/rfc/rfc4787) | Title and first page read; detail not read; the behavior shown is what the lab printed |
| `169.254.0.0/16` is link-local | [RFC 3927](https://www.rfc-editor.org/rfc/rfc3927) | Not read; **est.** |
| `ipaddress`: `is_private` is false for `100.64.0.0/10` and otherwise means "not globally reachable" per the IANA special-purpose registries; `subnets`, `overlaps`, `num_addresses`, `broadcast_address` | [Python `ipaddress` documentation](https://docs.python.org/3/library/ipaddress.html) | Read the `is_private` text; the other names were run (Python 3.13.5) |
| Amazon reserves the first four and the last address of every subnet (five in all) | [AWS VPC subnet sizing](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html) | Read |
| DigitalOcean reserves how many addresses per subnet | none | Not read; **est.** |
| DigitalOcean cloud firewalls are stateful and block everything not permitted by a rule; with no inbound rules no inbound traffic is permitted, with no outbound rules no outbound traffic is permitted | [Cloud firewalls](https://docs.digitalocean.com/products/networking/firewalls/) and [How to configure firewall rules](https://docs.digitalocean.com/products/networking/firewalls/how-to/configure-rules/) (pages "last verified 4 Aug 2026") | Read |
| Rules can have an allow or deny action (added 4 August 2026); deny rules take precedence over allow rules, including across firewalls on the same droplet; traffic that matches no rule is denied | Same two pages | Read. The two `doctl` reference pages disagree: the rules page says `doctl` does not support the action field, and the `add-rules` flag text says an `action` key is supported. I do not use it. |
| Limits: 50 rules per firewall; 10 droplets and 5 tags per firewall; firewalls affect public and VPC traffic; traffic logs are not available; adding rules does not end existing connections; connection state is tracked on the droplet's host | [Firewall limits](https://docs.digitalocean.com/products/networking/firewalls/details/limits/) (last verified 4 Aug 2026) | Read |
| `doctl compute firewall create/add-rules/remove-rules/list/delete`: rule syntax `protocol:tcp,ports:22,address:CIDR` or `tag:NAME`; `--inbound-rules`, `--outbound-rules`, `--tag-names`, `--format` columns `ID,Name,InboundRules`; `--force` on delete | [create](https://docs.digitalocean.com/reference/doctl/reference/compute/firewall/create/), [add-rules](https://docs.digitalocean.com/reference/doctl/reference/compute/firewall/add-rules/), [remove-rules](https://docs.digitalocean.com/reference/doctl/reference/compute/firewall/remove-rules/), [list](https://docs.digitalocean.com/reference/doctl/reference/compute/firewall/list/), [delete](https://docs.digitalocean.com/reference/doctl/reference/compute/firewall/delete/) | Flags read; never run. The `ports:1-65535` range form is **est.** |
| `doctl compute tag create/delete`, `compute droplet create` (`--vpc-uuid`, `--tag-names`, `--ssh-keys`, `--wait`), `vpcs create --ip-range` | [tag create](https://docs.digitalocean.com/reference/doctl/reference/compute/tag/create/), [tag delete](https://docs.digitalocean.com/reference/doctl/reference/compute/tag/delete/), [droplet create](https://docs.digitalocean.com/reference/doctl/reference/compute/droplet/create/) | Read; never run. `vpcs` flags were read for the [web request page](How-a-Web-Request-Works.md#claims-register) the same day |
| Bundled-plan droplets are billed per second, minimum 60 seconds or $0.01, capped at 672 hours a month; powered-off droplets are still billed; destroy to stop billing | [Droplet pricing](https://docs.digitalocean.com/products/droplets/details/pricing/) | Read |
| `s-1vcpu-1gb` is $6 a month | `docs/cost-prices.json`, retrieved 2026-10-21 | Read in this repository |
| nftables: a base chain's `policy` is `accept` or `drop`; `ct state`; named sets; `masquerade` (kernel 3.18 or later) and `dnat`; `log prefix`; `nft -a` shows handles | nftables wiki: [Quick reference](https://wiki.nftables.org/wiki-nftables/index.php/Quick_reference-nftables_in_10_minutes), [Sets](https://wiki.nftables.org/wiki-nftables/index.php/Sets), [NAT](https://wiki.nftables.org/wiki-nftables/index.php/Performing_Network_Address_Translation_(NAT)), [Logging](https://wiki.nftables.org/wiki-nftables/index.php/Logging_traffic) | Read the passages for policy, ct state, sets, masquerade and log prefix; everything shown was also run (nft 1.1.3) |
| Rules in a chain are checked in order and `accept` or `drop` ends the check | General knowledge, and the `insert` result in the lab | **est.** (observed in the lab, not read in a page) |
| `unshare` options `--map-root-user`, `--mount-proc`, `--fork`, `--pid`; `ip netns add/exec` | [unshare(1)](https://man7.org/linux/man-pages/man1/unshare.1.html), [ip-netns(8)](https://man7.org/linux/man-pages/man8/ip-netns.8.html), [ip-route(8)](https://man7.org/linux/man-pages/man8/ip-route.8.html) | Options read; observed. The route-selection rule (longest prefix) is **est.**; the `ip-route` page mentions "longest match" in another context |
| Unprivileged user namespaces are restricted by default on some Ubuntu releases; `ip_forward` is off by default on most machines | General knowledge | **est.**; the sudo fallback was not run |
| Nmap port states open, closed, filtered and that they describe how the scan sees the port | [Nmap book: port scanning basics](https://nmap.org/book/man-port-scanning-basics.html) | Read |
| PowerShell: `Get-NetFirewallRule` has `-Direction`, `-Enabled`, `-Action`; `Get-NetFirewallProfile` exists and `Set-NetFirewallProfile` documents `-DefaultInboundAction` and logging options; `Test-NetConnection` has `-Port` and `-InformationLevel`; `System.Net.IPNetwork` has `Contains` | Microsoft Learn: [Get-NetFirewallRule](https://learn.microsoft.com/en-us/powershell/module/netsecurity/get-netfirewallrule), [Get-NetFirewallProfile](https://learn.microsoft.com/en-us/powershell/module/netsecurity/get-netfirewallprofile), [Set-NetFirewallProfile](https://learn.microsoft.com/en-us/powershell/module/netsecurity/set-netfirewallprofile), [Test-NetConnection](https://learn.microsoft.com/en-us/powershell/module/nettcpip/test-netconnection), [IPNetwork](https://learn.microsoft.com/en-us/dotnet/api/system.net.ipnetwork) | Names read; nothing run. The profile property names and the `Quiet` value are **est.** |
| The repository's rule sets, module defaults and comments quoted here | `modules/firewall/main.tf`, `stacks/00-foundation/main.tf`, `stacks/10-access/main.tf`, `modules/twingate-bootstrap/cloud-init.yaml.tftpl` and `variables.tf`, as of this page's commit | Read in this repository |
| The lab outputs (routes, conntrack line, scans, counters) | Run on 2026-10-21 as an ordinary user | Observed; ports, counts and handles change |

Not verified, plainly: the whole PowerShell and Windows track; WSL 2; the `sudo unshare` fallback; the optional cloud path from start to finish, including whether a tag-sourced rule admits the scanner over the private network, whether the `1-65535` port range is accepted, whether `journalctl -k` shows the `log` lines on the droplet, and how long a change takes to apply; any DigitalOcean subnet reservations; and how long a full 65,535-port sweep takes on a real network.

Next: [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md), core step 4 on the [Reading order](Reading-Order.md) page.
