# Design a honeynet: an isolated segment, on paper and in a checker

Lesson 10 of the [deception and honeypots track](Deception-and-Honeypots-Start-Here.md) and the first page of track 3, the path for **your own hardware or home lab**. A foundations side page to [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md). It is a design lesson: you decide where a decoy machine may live, who may reach it, what it may reach, and how you manage it, and you test the design with a small program before you build anything. Next: [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md), lesson 11.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the checker was run once on Linux; the firewall tables and every vendor-product step were not run.** On **2026-10-22** the author ran the checker and all four rule files on this page with Python 3.13.5 on Linux and pasted the output. **Not run:** every PowerShell command (no Windows machine; marked **est.**), every step on a real firewall, and the optional real-network test, which needs your own network. The pfSense and OPNsense statements come from their documentation pages, read on 2026-10-22 (see the [claims register](#claims-register)); no pfSense or OPNsense system was built. Nothing here is legal advice or a statement about your internet provider's contract.

> **Prerequisites.** [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) (all eight minimums apply from here on), [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) (addresses, default deny, stateful rules), and a terminal. About 2 to 3 hours (est.). **Cost: none for this page.** The reading, the paper design and the checker are free. The hardware you would later build on is yours (see [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md#cost-and-hardware-read-this-first)), and nothing on this page needs it.

## What you will be able to do

- Say what a honeynet is, and why you design its network before you install anything on it.
- Tell the three ways to place a decoy apart: inside your own network (a tripwire), isolated in a lab, and open to the internet, and say why this track teaches only the first two.
- Describe an isolated segment in layers: separate wires or a VLAN, a firewall that blocks in both directions, closed outgoing traffic, and management only through a zero trust or VPN path.
- Explain a port forward, a DMZ host and a cloud relay in plain terms, and say why the DMZ host is the risky one.
- Read and write the firewall rules for an internal-only honeynet, in the style of pfSense and OPNsense, using documentation addresses.
- Run a small checker that tells you whether your rules say what you meant, and see which expectation fails when you break them.
- Say what the checker cannot prove.

## What a honeynet is, and why design first

A **honeypot** is a machine built to be probed and logged. A **honeynet** is a network of them, or one machine that imitates many, kept on a segment of its own. The [vocabulary page](Deception-and-Honeypots-What-Deception-Is.md#the-vocabulary) defines both.

You design first because the machine is the easy part. T-Pot, the bundle you will meet next, installs with a script. What decides whether it is safe is the network around it: a decoy that anyone can take over is only safe if taking it over leads nowhere. The T-Pot README says "a system compromise can never be ruled out", so the plan is to make a compromise boring.

## Three places a decoy can live

| Placement | Who can reach it | What it teaches | Risk | This track |
|---|---|---|---|---|
| **Inside your network, as a tripwire** ("internal-only") | Machines on your own home network, and nobody from the internet | Whether something already inside is looking around: a scanner you forgot, an infected laptop, a guest's phone. Nothing legitimate has a reason to touch it, so any touch is worth a look | Lowest of the three. The decoy has to be on a segment that cannot reach the rest, or a takeover is a step into your network | **Taught, and the recommended first run** |
| **Isolated in a lab** | Only your own test machines on the same segment | How the software behaves, with traffic you cause yourself | Low | **Taught** (it is the first half of the next page) |
| **Open to the internet** | Anyone, which means automated scanners within minutes to hours (est.) | What real, constant, untargeted attacks look like | Highest: your address is the target, your provider's terms apply, and a takeover is real | **Not taught.** The [options are explained below](#if-you-ever-decide-to-open-it-to-the-internet) so you can say no on purpose |

The internal-only variant is the best fit for a beginner for a plain reason: it catches **lateral movement**, which is an intruder who is already inside moving from machine to machine, and it does so with almost no noise. [The zero-activity baseline](Deception-and-Honeypots-What-Deception-Is.md#the-zero-activity-baseline) is what makes that work: if nobody should touch it, a touch is a signal.

## Isolation, in layers

"Isolated" is a claim about several things at once. Each layer below fails on its own, so you use all of them.

1. **A separate segment.** Either a **physically separate network** (its own switch, its own network card in the firewall, no cable to anything else) or a **VLAN**, a feature of a managed switch that splits one wire into separate virtual networks. pfSense's documentation describes VLANs as letting "a switch function as if it were multiple switches" so that hosts sit on a specific segment, "isolated from other segments". A VLAN is only as isolated as the switch configuration and the firewall rules behind it: a port set to the wrong VLAN, or a link that carries more VLANs than you meant, undoes it (est.; the documentation describes the feature, not this failure). Physical separation has fewer ways to go wrong and more cost.
2. **A firewall between the segment and everything else, default deny both ways.** *Default deny* means anything not explicitly allowed is blocked. The segment's rules decide what its machines may start; a second set decides what may start toward it. You write both.
3. **No route to your other networks.** The segment's machines should not be able to start a connection to your LAN, your management network or your SIEM. The checker below tests exactly this.
4. **Closed outgoing traffic.** This is *egress*: traffic leaving the segment. The decoy gets none by default, so that a taken-over decoy cannot attack anyone, which is [minimum 4](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums). T-Pot's installer needs outgoing web access, so you open a short, narrow window for installs and updates and close it again (see [the next page](Deception-and-Honeypots-T-Pot-at-Home.md#install-it-on-the-isolated-segment)).
5. **Management through a zero trust or VPN path only.** See the next section.
6. **Nothing irreplaceable on it.** It can be wiped and rebuilt, and it holds no real data ([minimum 6](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums)).

## Managing it: a ZTNA or VPN path, and nothing else

You will need to log in to the decoy to look after it. T-Pot's README lists three management ports: **64295** for SSH, **64297** for its web page (behind a reverse proxy, a server that forwards requests to services behind it), and **64294** for a sensor sending data to a main node. They are not honeypot ports; they are the way in for you. If an intruder or a scanner can reach them, they can try to log in to the thing you use to run the trap.

The rule: **management reaches the decoy from one place only, and that place is a zero trust network access (ZTNA) connector or a VPN endpoint that you run.** Not from the whole LAN, not from the decoy's own segment, and never from the internet.

- With ZTNA ([Why ZTNA, not a VPN](Why-ZTNA-Not-a-VPN.md), [Twingate](Twingate.md)), a small connector inside your network makes outbound connections only, and you reach a named resource through it. The decoy's management ports become that one resource, and the connector's address is the only source your firewall allows to them.
- With a VPN you run yourself, the VPN endpoint is the one allowed source. A home VPN server needs an inbound hole in your router, and some internet providers share one public address among many customers (CGNAT, defined in the [Glossary](Glossary.md)), which prevents it. An outbound-only connector does not have that problem ([Zero trust at home](Zero-Trust-at-Home-Two-Connectors-and-Failover.md#vpn-versus-ztna-under-real-residential-conditions)).

Either way the checker below tests it: an ordinary LAN machine must be denied the management ports, and the admin path must be allowed.

## If you ever decide to open it to the internet

This track does not teach it, and the [education plan](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-22-honeypot-education-plan.md) lists it as "not recommended as a project lesson". You may still wonder what your options are, so here they are, plainly. T-Pot's README suggests forwarding ports 1 to 64000 to it from the internet so it can catch attacks. Anything in this section is your decision and your risk, and [minimum 2](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums) says to read your internet provider's terms first.

| Option | What it is | What it exposes | If the decoy is taken over | Cost and catches |
|---|---|---|---|---|
| **Port forward** | A rule on your router: traffic arriving at your public address on port N goes to one inside machine's port N | Only the ports you list. Listing 1 to 64000 is nearly everything | The intruder is on the machine you chose. If it sits on an isolated segment with closed egress, that is where they stay | Free. Does not work if your provider uses CGNAT, because you have no address of your own to forward from |
| **DMZ host** | A feature on many consumer routers that sends **every** unsolicited inbound connection that no other rule claims to one inside machine | **All ports**, including management ports, and nothing you listed | Worse, in two ways. The router's firewall no longer filters inbound traffic to that machine, and on many consumer routers the machine stays on the same network as your laptop (est.; it varies by router) | Free. **This is the risky one** |
| **Cloud relay** | A small server in a cloud account with a public address that takes the attacks, and either hosts the decoy or passes traffic through a tunnel to your honeynet | What the relay exposes. Your home address is not the target | The relay is the first thing taken. A tunnel from it to your home is a path toward you unless it is one-way and filtered | A provider bill: one small server size is $6 a month in `docs/cost-prices.json` (`s-1vcpu-1gb`, retrieved 2026-10-21), and the tunnel is unpriced and undesigned here. The provider's consent and acceptable-use policy apply ([minimum 3](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums)) |

Why the **DMZ host** is the risky one, in four sentences. First, the name misleads: a real DMZ is a separate segment with a firewall on both sides (the [Glossary](Glossary.md) defines it), while a DMZ host is one machine with the door left open. Second, it exposes every port, including your management ports, so the machine you use to run the trap is in the open too. Third, it removes the router's inbound filtering for that machine, so any flaw in it is reachable. Fourth, on a typical home router the machine remains on your main network, which breaks [minimum 1](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums). A general-reference page describes it as "a less secure alternative to port forwarding" that "must be avoided" except in narrow cases (see the [register](#claims-register)).

If you want to see real attacks without any of this, track 2's cloud sensor does it in its own account for a bounded time, and canary tokens catch what touches them with nothing exposed. Both are in the [hub](Deception-and-Honeypots-Start-Here.md).

## What the rules look like

Firewalls from different makers share the same ideas. pfSense's documentation says rules on an interface tab are "evaluated on a first match basis" from top to bottom, that traffic "need only be permitted on the interface where it enters the firewall" because replies are matched through the state table, and that traffic matching no rule is blocked by the default deny rule. OPNsense's documentation says rules default to filtering the "incoming direction", set "on the interface where the traffic originates from", and that a rule with *quick* set is handled on a first-match basis (the default), while a rule without it is last-match, which is how its own default deny rule works. So in both: **a rule belongs to the interface a connection starts on**, order matters, and what no rule allows is blocked.

Here is the internal-only design as rules. The addresses are documentation placeholders from [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.txt); on a real home network you use your own private ranges ([the private blocks](Subnets-NAT-and-Firewalls-By-Hand.md#the-special-ranges-to-know)). Names in capitals stand for **aliases** (a named list of addresses or ports that pfSense and OPNsense let you define and reuse).

| Placeholder | Stands for |
|---|---|
| `192.0.2.0/24` (`LAN`) | Your home network |
| `192.0.2.10` (`ADMIN_PATH`) | The connector or VPN endpoint that manages the decoy |
| `203.0.113.0/24` (`HONEYNET`) | The isolated segment; the decoy is `203.0.113.5` |
| `198.51.100.0/24` | Pretend internet |
| `198.51.100.80` (`UPDATE_MIRRORS`) | A pretend package mirror, for the update window |

**Rules on the `LAN` interface** (connections that start on your home network), top to bottom:

| # | Action | Protocol | Source | Destination | Ports | Why |
|---|---|---|---|---|---|---|
| 1 | Pass | TCP | `ADMIN_PATH` | `HONEYNET` net | `64295`, `64297` | The one management path. Log it |
| 2 | Block | TCP | `LAN` net | `HONEYNET` net | `64294`-`64297` | Nobody else on the LAN gets management. Log it |
| 3 | Pass | any | `LAN` net | `HONEYNET` net | any | The tripwire: the decoy can be touched from the LAN. Log it, because a hit here is the alert |
| 4+ | | | | | | Your normal LAN rules |

The range in rule 2 also covers `64296`, which the README does not list; blocking a neighbor you do not use costs nothing. Rule 2 must sit above rule 3. If it sits below, rule 3 matches first and the management ports are open to every machine on the LAN. You will see that happen in the checker.

**Rules on the `HONEYNET` interface** (connections the decoy starts):

| # | Action | Protocol | Source | Destination | Ports | Why |
|---|---|---|---|---|---|---|
| 1 | Block | any | `HONEYNET` net | any | any | Default deny made explicit, so you can log it. A hit here means the decoy tried to call out: that is the alarm |

**Update window.** While you install or update, add a rule *above* the block: Pass, TCP, `HONEYNET` net to `UPDATE_MIRRORS`, ports `80`, `443`. `UPDATE_MIRRORS` is a one-address stand-in so the checker has something to test. A real T-Pot install reaches several kinds of endpoint (GitHub for the clone, your operating system's package mirrors, and container registries for the images), so your real alias must list all of them, found by watching the firewall log during a trial install in a VM. If you would rather not allow that many, download what you need on another machine and copy it over, or point the decoy at a proxy you control (est.; the README says T-Pot wants a non-proxied connection, so a proxy may break it). Remove it, or give it an expiry if your firewall supports a schedule (est.), when the work is done. The T-Pot README also lists outgoing `80` and `443` as the install and update path; the decoy will need name resolution too, which you allow to one resolver of your choosing if you find it fails (est.).

**On the `WAN` interface** (the internet side): no port forward, no DMZ host, and nothing that sends traffic to `HONEYNET`. The default deny rule already blocks unsolicited inbound traffic.

**Logging.** Turn on logging for the rules marked "Log it". Logs of what the firewall blocked are your second detector: they see the honeynet reaching for the LAN even if the decoy software is silent.

## Exercise 1: draw it

**Predict.** Before you draw: how many arrows go from the honeynet to anywhere? Write a number.

**Do.** On one page draw four boxes: the internet, your home network, the honeynet, and the admin path. Draw an arrow for each connection that is *allowed to start*, labeled with the ports. Then mark the T-Pot README's warnings, one of each in a different color: it can be compromised, it holds no sensitive data, it shares data with a community project by default, and it expects a working outgoing connection to install.

**Check.** Your drawing should have arrows for: home network to honeynet (the tripwire, all ports except management), admin path to honeynet (management ports only), and the install window (honeynet out to the mirror, drawn dotted, with a note about when it closes). It should have **no** arrow from the honeynet to the home network or the admin path, and none from the internet to the honeynet. Your answer to the first question should be one: the single dotted arrow, which exists only while you install or update.

**Undo.** Nothing. It is paper.

## Exercise 2: test your rules with a checker

The checker is a small Python program. It reads your rules and a list of things that must be true, and says which hold. It sends no packets and touches no network. It is a **model**: it judges the first packet of each new connection, the first rule that matches wins, and no match means blocked. It does not model replies, address translation, or the switch.

Make a folder, `cd` into it, and save the program as `policy_check.py`:

```python
# Checks a firewall rule file against a list of things that must be true.
# A SIMPLE MODEL, not a firewall: it judges the first packet of a new connection,
# first match wins, no match = blocked. Replies are not modeled. It reads two
# small text files and prints a verdict per line; it sends no packets.
import ipaddress
import sys

# Pretend networks, all from the documentation blocks of RFC 5737.
NAMES = {
    "internet": "198.51.100.0/24",   # stands in for "everyone outside"
    "lan": "192.0.2.0/24",           # your home network
    "admin": "192.0.2.10/32",        # the one machine allowed to manage the honeypot
    "honeynet": "203.0.113.0/24",    # the isolated segment
    "updates": "198.51.100.80/32",   # a pretend package mirror
    "any": "0.0.0.0/0",
}
NETS = {k: ipaddress.ip_network(v) for k, v in NAMES.items()}
MAX_BYTES, MAX_LINES = 65536, 500


def lines_of(path):
    try:
        with open(path, "rb") as fh:
            raw = fh.read(MAX_BYTES + 1)
    except OSError as err:
        sys.exit(f"{path}: cannot read ({err.strerror})")
    if len(raw) > MAX_BYTES:
        sys.exit(f"{path}: larger than {MAX_BYTES} bytes")
    text = raw.decode("utf-8", errors="replace").splitlines()
    if len(text) > MAX_LINES:
        sys.exit(f"{path}: more than {MAX_LINES} lines")
    for number, line in enumerate(text, 1):
        line = line.strip()
        if line and not line.startswith("#"):
            yield number, line


def port_ranges(spec, where):
    if spec == "any":
        return [(0, 65535)]
    out = []
    for part in spec.split(","):
        lo, _, hi = part.partition("-")
        if not lo.isdigit() or (hi and not hi.isdigit()):
            sys.exit(f"{where}: bad port {part!r}")
        lo, hi = int(lo), int(hi or lo)
        if not 0 <= lo <= hi <= 65535:
            sys.exit(f"{where}: port out of range {part!r}")
        out.append((lo, hi))
    return out


def load_rules(path):
    rules = []
    for number, line in lines_of(path):
        words = line.split()
        where = f"{path}:{number}"
        if len(words) != 5:
            sys.exit(f"{where}: want 5 fields, got {len(words)}")
        action, src, dst, proto, ports = words
        if action not in ("pass", "block") or proto not in ("tcp", "udp", "any"):
            sys.exit(f"{where}: bad action or protocol")
        if src not in NETS or dst not in NETS:
            sys.exit(f"{where}: unknown network name")
        rules.append((len(rules) + 1, action, NETS[src], NETS[dst], proto, port_ranges(ports, where)))
    return rules


def judge(rules, src, dst, proto, port):
    for number, action, snet, dnet, rproto, ranges in rules:
        if src in snet and dst in dnet and rproto in ("any", proto) \
                and any(lo <= port <= hi for lo, hi in ranges):
            return action, f"rule {number}"
    return "block", "default deny"


def main(rules_path, expect_path):
    rules = load_rules(rules_path)
    bad = total = 0
    for number, line in lines_of(expect_path):
        words = line.split(None, 5)
        where = f"{expect_path}:{number}"
        if len(words) != 6 or words[0] not in ("allow", "deny"):
            sys.exit(f"{where}: want allow|deny src dst proto port why")
        want, src, dst, proto, port, why = words
        try:
            src, dst = ipaddress.ip_address(src), ipaddress.ip_address(dst)
        except ValueError:
            sys.exit(f"{where}: bad address")
        if not port.isdigit() or int(port) > 65535 or proto not in ("tcp", "udp"):
            sys.exit(f"{where}: bad protocol or port")
        action, why_matched = judge(rules, src, dst, proto, int(port))
        got = "allow" if action == "pass" else "deny"
        total += 1
        ok = got == want
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {want:5} {src} -> {dst} {proto}/{port}  [{why_matched}]  {why}")
    if total == 0:
        sys.exit(f"{expect_path}: no expectations found; an empty list proves nothing")
    print(f"{total - bad} of {total} expectations hold")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: policy_check.py RULES EXPECT")
    sys.exit(main(sys.argv[1], sys.argv[2]))
```

Save your rules as `rules.txt`. Each line is `action source destination protocol ports`; the names are the ones in the program's `NAMES` table, and it is the table above in code:

```text
# Internal-only honeynet rules. First match wins. Nothing matched = blocked.
# action  source    destination  protocol  ports
pass      admin     honeynet     tcp       64295,64297
block     lan       honeynet     tcp       64294-64297
pass      lan       honeynet     any       any
block     any       any          any       any
```

Save what must be true as `expect.txt`. Each line is `allow` or `deny`, a source address, a destination address, a protocol, a port, and a reason:

```text
# what must be true. allow|deny  source-address  destination-address  protocol  port  why
deny   198.51.100.7   203.0.113.5   tcp  22     the internet cannot reach the honeypot
deny   198.51.100.7   203.0.113.5   tcp  64297  the internet cannot reach the management page
allow  192.0.2.50     203.0.113.5   tcp  22     a machine on the home LAN can touch the tripwire
allow  192.0.2.50     203.0.113.5   tcp  3389   the tripwire answers on many ports
deny   192.0.2.50     203.0.113.5   tcp  64295  an ordinary LAN machine cannot reach management SSH
deny   192.0.2.50     203.0.113.5   tcp  64297  an ordinary LAN machine cannot reach the web page
allow  192.0.2.10     203.0.113.5   tcp  64297  the admin path can reach the web page
deny   203.0.113.5    192.0.2.50    tcp  445    the honeypot cannot start a connection to the LAN
deny   203.0.113.5    192.0.2.10    tcp  22     the honeypot cannot reach the admin path
deny   203.0.113.5    198.51.100.7  tcp  443    the honeypot cannot call out to the internet
deny   203.0.113.5    198.51.100.80 tcp  443    not even to the update mirror, while the window is closed
```

**Predict.** Do all eleven hold? Which rule do you expect to decide the line about the web page (`tcp/64297`) from an ordinary LAN machine?

**Do.**

```bash
python3 -I policy_check.py rules.txt expect.txt; echo "exit=$?"
```

```powershell
py -I policy_check.py rules.txt expect.txt; "exit=$LASTEXITCODE"   # est.: not run (no Windows machine); `python` works if `py` is absent
```

**Check.** The run on 2026-10-22:

```text
ok   deny  198.51.100.7 -> 203.0.113.5 tcp/22  [rule 4]  the internet cannot reach the honeypot
ok   deny  198.51.100.7 -> 203.0.113.5 tcp/64297  [rule 4]  the internet cannot reach the management page
ok   allow 192.0.2.50 -> 203.0.113.5 tcp/22  [rule 3]  a machine on the home LAN can touch the tripwire
ok   allow 192.0.2.50 -> 203.0.113.5 tcp/3389  [rule 3]  the tripwire answers on many ports
ok   deny  192.0.2.50 -> 203.0.113.5 tcp/64295  [rule 2]  an ordinary LAN machine cannot reach management SSH
ok   deny  192.0.2.50 -> 203.0.113.5 tcp/64297  [rule 2]  an ordinary LAN machine cannot reach the web page
ok   allow 192.0.2.10 -> 203.0.113.5 tcp/64297  [rule 1]  the admin path can reach the web page
ok   deny  203.0.113.5 -> 192.0.2.50 tcp/445  [rule 4]  the honeypot cannot start a connection to the LAN
ok   deny  203.0.113.5 -> 192.0.2.10 tcp/22  [rule 4]  the honeypot cannot reach the admin path
ok   deny  203.0.113.5 -> 198.51.100.7 tcp/443  [rule 4]  the honeypot cannot call out to the internet
ok   deny  203.0.113.5 -> 198.51.100.80 tcp/443  [rule 4]  not even to the update mirror, while the window is closed
11 of 11 expectations hold
exit=0
```

Rule 2 decides the web page line. The bracket after each line names the rule that decided it, so you can read why. **Passing means your file says what you meant. It does not mean your firewall enforces it**; the next section is how you find that out.

**Undo.** Nothing: it only read two files.

## Exercise 3: break it on purpose

You will make three broken copies of the rules, one at a time, and see which expectations catch each.

```bash
{ echo 'pass honeynet any any any'; cat rules.txt; } > broken1.txt                  # "just to get updates working"
{ echo 'pass lan honeynet any any'; cat rules.txt; } > broken2.txt                  # a pass above the management block
sed '$d' rules.txt > broken3.txt                                                    # drop the final block ...
echo 'pass honeynet updates tcp 80,443' >> broken3.txt                              # ... add the update window ...
echo 'block any any any any' >> broken3.txt                                         # ... and put the block back
```

```powershell
# est.: not run (no Windows machine)
(@('pass honeynet any any any') + (Get-Content rules.txt)) | Set-Content broken1.txt
(@('pass lan honeynet any any') + (Get-Content rules.txt)) | Set-Content broken2.txt
(Get-Content rules.txt | Select-Object -SkipLast 1) + 'pass honeynet updates tcp 80,443' + 'block any any any any' | Set-Content broken3.txt
```

**Predict.** For each file, how many of the eleven will fail, and which lines? Think about which direction each added rule opens. Write it down, then run:

```bash
for f in broken1 broken2 broken3; do echo "== $f"; python3 -I policy_check.py $f.txt expect.txt | grep -E 'FAIL|of 11'; done
```

```powershell
foreach ($f in 'broken1','broken2','broken3') { "== $f"; py -I policy_check.py "$f.txt" expect.txt | Select-String 'FAIL|of 11' }   # est.
```

**Check.** The run on 2026-10-22:

```text
== broken1
FAIL deny  203.0.113.5 -> 192.0.2.50 tcp/445  [rule 1]  the honeypot cannot start a connection to the LAN
FAIL deny  203.0.113.5 -> 192.0.2.10 tcp/22  [rule 1]  the honeypot cannot reach the admin path
FAIL deny  203.0.113.5 -> 198.51.100.7 tcp/443  [rule 1]  the honeypot cannot call out to the internet
FAIL deny  203.0.113.5 -> 198.51.100.80 tcp/443  [rule 1]  not even to the update mirror, while the window is closed
7 of 11 expectations hold
== broken2
FAIL deny  192.0.2.50 -> 203.0.113.5 tcp/64295  [rule 1]  an ordinary LAN machine cannot reach management SSH
FAIL deny  192.0.2.50 -> 203.0.113.5 tcp/64297  [rule 1]  an ordinary LAN machine cannot reach the web page
9 of 11 expectations hold
== broken3
FAIL deny  203.0.113.5 -> 198.51.100.80 tcp/443  [rule 4]  not even to the update mirror, while the window is closed
10 of 11 expectations hold
```

Three lessons, one per file. `broken1` is the rule people add when an install fails: a pass for the decoy to anywhere. It opens the decoy to your LAN, your admin path and the internet in one line, and four expectations catch it. `broken2` is an **ordering** mistake: the right rules are present but a broad pass sits above them, and the checker names rule 1 as the culprit. `broken3` is the update window left open; the one failure is the point, because the window is meant to open and close, and the expectation is how you notice you forgot to close it.

**Undo.** Delete the three files if you like (`rm broken1.txt broken2.txt broken3.txt`, or `Remove-Item broken*.txt`). `rules.txt` and `expect.txt` stay.

## Exercise 4 (optional): prove the real firewall, before you install anything

The checker tests a file. This exercise tests your network. It uses **only machines you own**, on your own segment, with **no decoy software installed yet**. Substitute your own addresses for the placeholders.

You need two test machines: one on the honeynet segment (a spare computer or a VM with nothing on it) and one on your LAN. Open a harmless listening port on each so a success is visible, for example `python3 -m http.server 8000` in an empty folder (Python's built-in web server; stop it with Ctrl+C afterwards). Then try connections in each direction and compare with your `expect.txt`.

```bash
# from the LAN machine to the honeynet test machine (should succeed; this is the tripwire path):
curl -sS -m 5 -o /dev/null -w '%{http_code}\n' http://203.0.113.5:8000/ ; echo "exit=$?"
# from the honeynet test machine to the LAN machine (should time out; exit 28 is curl's timeout):
curl -sS -m 5 -o /dev/null -w '%{http_code}\n' http://192.0.2.50:8000/ ; echo "exit=$?"
```

```powershell
# est.: not run
try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 http://203.0.113.5:8000/).StatusCode } catch { "blocked or failed: $($_.Exception.Message)" }
```

**Predict.** Which of the two should connect, and what does a block look like (a quick refusal, or a wait until the timeout)? pfSense's documentation says a *block* rule is silent, so the client waits and times out, and a *reject* rule sends back a refusal. Your firewall's default for the rule you wrote decides which you see.

**Check.** The connection from the LAN should work and the reverse should time out. Then check your firewall's log: the blocked attempt should appear in it. If both directions work, the isolation is not there yet, and you do not install anything.

**Undo.** Stop both test servers, remove any firewall rule you added only for the test, and note the date of the test in your plan.

## Build, break, detect, evade, defend

- **Build.** The segment, the three tables of rules, and a checker run that passes.
- **Break.** Exercise 3: a broad pass, a pass above a block, and a window left open. Add a fourth of your own, such as a rule for "DNS to anywhere", and see what the checker says; it will say nothing if you have no expectation for it, which is the lesson about expectations.
- **Detect.** The failing line names the rule. On the real firewall, the logs of blocked connections from the honeynet are the detector: a honeynet machine that tries to reach the LAN is either broken or taken. Write down where you would read that log.
- **Evade.** Imagine an intruder who has taken the decoy. They try your LAN (blocked), the admin path (blocked), the internet (blocked), and then the quiet routes: the firewall's own address, if rules do not cover traffic to the firewall itself (est.; check yours), name resolution to a resolver you allowed, and anything on the switch that is not the firewall's business. Each is a question for your rule set, not for the decoy.
- **Defend.** The six layers, the one management path, the narrow and temporary update window, the logging, and a rebuild plan: wipe and reinstall, with nothing to recover.
- **Flip the board.** You are the intruder who just landed on a laptop in the home network and ran a scan. You see a machine that answers on twenty ports it should not have and says it is a printer, a web server and an industrial controller at once. What do you do? An experienced attacker thinks "decoy" and leaves, and the quiet value of the trap is that you learned someone was scanning. Then switch: how would a defender make that machine less obviously a decoy, and what does that cost in risk? (T-Pot's README says its blackhole mode reduces visits but "is neither a guarantee for being completely stealth nor will it prevent fingerprinting of some honeypot services".)

## Common mistakes

| Mistake | Why it hurts | Better |
|---|---|---|
| A VLAN with no firewall rules between it and the LAN. | Many routers route between their own VLANs by default or allow it until told otherwise (est.). | Default deny in both directions, tested. |
| Management ports reachable from the whole LAN. | The trap's control panel is exposed to the same intruder it is meant to catch. | One source, the admin path, tested by an expectation. |
| The update window left open. | A taken-over decoy can call out. | A dated reminder; an expectation that fails when the window is open. |
| A DMZ host "just for a weekend". | Every port is open and the machine is likely on your main network. | Do not. If you must expose, a port forward to an isolated segment, after reading your provider's terms. |
| Treating a passing checker as proof. | It tests a file, not a network. | Exercise 4, and read the firewall's own rule list and logs. |
| Putting real data or reused passwords on the decoy. | It is meant to be taken. | Invent everything ([minimum 6](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums)). |

## What this page does not prove

- **The checker is a model.** It does not know about address translation, replies, rules that apply to traffic to the firewall itself, IPv6, or what the switch does. Passing it is necessary, not sufficient.
- **The VLAN failure modes are est.** Misconfigured ports and trunks are widely known, but this page read no document describing them for your equipment.
- **No firewall was configured.** The pfSense and OPNsense tables are the design in their vocabulary, built from what their documentation says about rule order and direction. Your menus differ by version.
- **No provider contract was read.** What your internet provider says about servers and inbound connections is yours to read.

## Claims register

Retrieved 2026-10-22.

| Claim | Source | Status |
|---|---|---|
| pfSense evaluates an interface's rules top to bottom on a first-match basis; traffic need only be permitted on the interface where it enters; a block rule is silent and is the behavior of the default deny rule | [pfSense documentation, firewall fundamentals](https://docs.netgate.com/pfsense/en/latest/firewall/fundamentals.html) | Read |
| pfSense: rules not matched by any user-defined or automatic rule are silently blocked by the default deny rule | [pfSense documentation, rule methodology](https://docs.netgate.com/pfsense/en/latest/firewall/rule-methodology.html) | Read |
| pfSense VLANs let a switch act as several switches, placing hosts on a segment isolated from others | [pfSense documentation, VLANs](https://docs.netgate.com/pfsense/en/latest/vlan/index.html) | Read. That a VLAN is only as isolated as its switch configuration is **est.** |
| OPNsense: rules filter the incoming direction by default, set on the interface where the traffic originates; *quick* (default) means first match wins; a rule without it is last-match, which is how its default deny works | [OPNsense documentation, firewall rules](https://docs.opnsense.org/manual/firewall.html) | Read |
| A DMZ host exposes all ports of one node to the outside, is "a less secure alternative to port forwarding" and "must be avoided" except in narrow cases | [Wikipedia, DMZ (computing)](https://en.wikipedia.org/wiki/DMZ_(computing)), section "DMZ host" | Read. A general reference, not a vendor page. How a given consumer router implements it, and whether the host stays on the main network, is **est.** |
| 192.0.2.0/24, 198.51.100.0/24 and 203.0.113.0/24 are the documentation blocks | [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.txt) | Read |
| T-Pot's management ports (64294, 64295, 64297), the suggestion to forward 1 to 64000, the blackhole wording, and the compromise warning | [T-Pot README](https://raw.githubusercontent.com/telekom-security/tpotce/HEAD/README.md), default branch | Read |
| One small cloud server is $6 a month | `docs/cost-prices.json` (`s-1vcpu-1gb`, retrieved 2026-10-21) | Read in the repository. Prices change |
| Automated scanning finds an open machine within minutes to hours | General knowledge | **est.** |
| What your provider, your router or the law allows | Nothing | **Not read** |

Not verified, plainly: anything about a real pfSense or OPNsense installation, any consumer router's DMZ-host behavior, any provider contract, and the cost of a tunnel for a cloud relay (not designed or priced).

Next: [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md), lesson 11. Or back to the [track hub](Deception-and-Honeypots-Start-Here.md).
