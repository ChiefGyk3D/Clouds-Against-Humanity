# Attack surface: list it, shrink it, measure it

Side page to the security and defense pages. Read it after Plan for failure: blast radius and assuming breach (which asks "what can this reach if it is compromised") and beside the [Threat model](Threat-Model.md) (which names the threats). This page asks the question that comes first: **what is there to attack at all**. Next: [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft, written from this repository's own pages and code.** Every project fact below names the file or page I read it in, on **2026-10-30**. The one script on the page was run once on Linux with Python 3.13 and its output is shown. `scripts/zero_ports_check.py` has **not** been run against real infrastructure (the [stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md) says so), several controls named here are **built but off by default** or **not applied**, and the table says which. The logging and alerting advice is marked **recommendation** where the repository does not do it. Nothing here was tested against an attacker, and the page contains no attack. Not yet reviewed by the maintainer.

> **Prerequisites.** [Networking basics](Networking-Basics-for-This-Project.md) for the words "port" and "firewall", and [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) for "token" and "least privilege". The exercises need a Linux or macOS terminal and Python 3.11 or newer. No cloud account and no installs. About 60 minutes (est.).

> **Where this runs.** Exercise 1 only reads what your own computer is listening on. Exercise 2 connects to `127.0.0.1`, which is your own machine and never leaves it. Nothing on this page asks you to test an address that is not yours. The authorization rule is in [Measure it](#measure-it).

## What you will be able to do

- Define **attack surface** and say why you cannot shrink what you have not listed.
- List a system's surface in six categories: inbound ports, public addresses, accounts, keys and tokens, dependencies, and people.
- Point to the choices in this project that remove items from that list, and say which are built, which are off by default and which are not applied.
- Measure the surface from the outside, on addresses you own, and say what a clean result does not prove.
- Say why moving a service to another port is not protection and shrinks nothing.
- Say, for each part of the surface, what should be logged and what should raise an alert.

## In plain words

An **attack surface** is every place an attacker could try to get in, or get something out. A door is part of it, and so is a key to the door, a person who holds the key and a lock maker whose product you trust.

The first job is an inventory, because an item you never wrote down is an item nobody is guarding. The second job is to **remove** items. Removing is different from hiding: a service on an unusual port is still there, and the [port-move rule](#the-port-move-rule) below says why it is not protection. The third job is to measure from outside, so you find out what a stranger sees and not what you believe they see. The fourth is to watch what is left, because a small surface still needs someone to notice when something touches it.

Surface is not the same as risk. A single exposed door with a bad lock is worse than ten doors that are all bricked up. This page counts doors; the [Threat model](Threat-Model.md) ranks what happens when one fails.

## List it: six questions

Ask these six questions of any system. Write the answers down, with the owner of each.

1. **Inbound ports.** Which ports will accept a connection from outside, and from whom? Count the cloud firewall, the host firewall and every service that listens.
2. **Public addresses.** Which machines, load balancers or DNS names can be reached from the internet? Include IPv6 (a forgotten IPv6 rule undoes an IPv4-only design: [IPv6: adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md)).
3. **Accounts.** Which logins exist on each machine, and in each service (cloud provider, code host, secrets manager, identity provider)? Include service accounts.
4. **Keys and tokens.** Which secrets exist, what does each one let its holder do, where is each stored, and when does it expire? Include the ones that sit in a machine's own configuration.
5. **Dependencies.** Which software, packages, container images, CI actions and hosted services does the system trust to behave? Each one is code or infrastructure you did not write.
6. **People.** Who can change the system or read its secrets? A person with access is surface: their laptop, their phone and their habits come with them.

A seventh item hides inside the first six, and deserves its own line: **the things that answer on the inside**. A droplet's metadata service is reachable by any process on the machine, not by the internet, and it can serve secrets. It is easy to miss because no firewall rule mentions it.

## How this project shrinks it

The table is the inventory for this repository, one row per category. "Status" says whether the control is applied. "Where" is the file or page the claim comes from.

| Category | What is on the list | What the project did to shrink it | Status | Where |
|---|---|---|---|---|
| Inbound ports | Each connector droplet has a public address, but the baseline cloud firewall has zero inbound rules from the internet. The one exception is TCP 22 between the two connectors, allowed only from the connector tag, never from an address range. | No SSH, VPN or bastion port is open to the internet. People reach a host through Twingate, whose connectors make outbound connections only. A plan policy denies any inbound rule that is open to the whole internet or not scoped to a tag. | Stage 1 design. The firewall and policy are in the repository; the project notes say nothing was run against a real account for several checks | [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md), [Architecture overview](Architecture-Overview.md), `stacks/10-access/main.tf`, `.spacelift/policies/plan.rego` |
| Public addresses | One public IPv4 per droplet, which cannot be removed on DigitalOcean. | Nothing answers on it. IPv6 is kept off, and a test fails the build if a droplet, a rule, a network or an address resource brings IPv6 back. | Test is built and runs in CI; it reads the repository, not a live account | [Droplet hardening: IPv6 stays closed](Droplet-Hardening.md#ipv6-stays-closed), `tests/test_ipv6_closed.py` |
| Accounts on a host | One login, `cah-admin`, key only. The stock `ubuntu` user is never created. | Password login off, root login off, `AllowUsers cah-admin` in the sshd drop-in, three tries and a 20 second grace time. | Built in the first-boot template | [Droplet hardening: login](Droplet-Hardening.md#login), `modules/twingate-bootstrap/cloud-init.yaml.tftpl` |
| Accounts in services | DigitalOcean, Twingate, Doppler, Spacelift and GitHub. | Spacelift holds one secret only, a read-only Doppler token for one config. Sign-in to Twingate is delegated to the identity provider, where the threat model says to enforce multi-factor. | Design, as documented | [Architecture overview](Architecture-Overview.md), [Doppler and secrets](Doppler-and-Secrets.md), [Threat model](Threat-Model.md) (T2, T4) |
| Keys and tokens | The DigitalOcean write token, the Twingate API token, the Doppler service token and one token per connector. | Every real secret lives in Doppler. The three provider tokens have a 90 day rotation. State is marked sensitive and lives only in Spacelift. The outside check uses its own read-only token, not the Spacelift one. | Built; the rotation is a documented routine the operator performs | [Doppler and secrets](Doppler-and-Secrets.md), [Threat model](Threat-Model.md) (assets, T4, T6), [stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md) section 6b |
| Inside the host | The metadata service at `169.254.169.254` serves each droplet's first-boot configuration, which includes its connector tokens, to any local process. | `metadata_lock` restricts it to root and the monitoring agent's user. | **Built, off by default, not tested on a real droplet.** The threat model lists this as an accepted risk (T5) | [Droplet hardening: metadata endpoint lock](Droplet-Hardening.md#metadata-endpoint-lock-built-off-by-default), [Threat model](Threat-Model.md) (T5), `stacks/10-access/variables.tf` |
| Dependencies | CI actions, the Doppler command line tool, the Twingate package repository, Ubuntu mirrors. | Actions pinned by commit, the Doppler tool pinned by checksum and failing closed, the Twingate repository key checked against a pinned fingerprint before it is trusted. | Built | [Threat model](Threat-Model.md) (T7, T8, T9) |
| Hosted services | Three third-party control planes are trusted. | Narrow scopes and a separate SSH key gate. The residual risk is accepted and written down. | Accepted risk | [Threat model](Threat-Model.md) (T10), [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) |
| People | One operator, in a public repository. | A human reads the plan and confirms before anything applies, a push policy keeps pull requests from starting a Spacelift run (it needs a paid plan and must be attached in Spacelift), and account identifiers stay out of the repository. | Built, with one control that lives in Spacelift and not in this repository | [Architecture overview](Architecture-Overview.md), [Threat model](Threat-Model.md) (T3, T14) |
| Software on the host | Anything installed is something to patch. | Daily security updates and staggered reboots so the two connectors never go down together. | Built | [Droplet hardening: updates](Droplet-Hardening.md#updates) |

Two points to hold onto.

- **The metadata item above corrects a common shorthand.** It is tempting to say "this project has no metadata endpoint". It has one, on every droplet, because the cloud provides it. What exists is a built, optional lock that is off today. The honest sentence is "the endpoint is there, and the lock that narrows it is not applied yet".
- **"Zero inbound" is shorthand too.** The accurate wording is zero inbound from the internet, with one tag-scoped rule between the connectors. The [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) page says it that way on purpose.

What the table does not list, because this repository does not cover it: your laptop, the identity provider account, the DNS registrar and anything a second person adds later. A real inventory for your own system has those rows, and the people row grows as soon as there is a second person.

## Measure it

Listing from the inside tells you what you believe. Measuring from the outside tells you what a stranger sees.

**The authorization rule, stated plainly.** Scan only addresses you own, or addresses whose owner has given you written permission to test, with the scope and time written down. A port scan of someone else's address can be treated as hostile activity by the owner, the provider or the law, whatever your reason. If you are unsure who owns an address, it is not yours. Practice on your own computer (`127.0.0.1`) or on a lab you built.

This project applies the rule in code. `scripts/zero_ports_check.py` tries a TCP connection to every port from 1 to 65535 on each connector's public address, from a machine outside the VPC, and passes only if every attempt timed out. It **cannot be given an address**: no argument, file or environment variable accepts one. The targets come only from the DigitalOcean API, and a droplet must carry the project's baseline tag, belong to the project and match the count you state. A scanner that takes any address is a tool that can be pointed at someone else, so this one cannot. The runbook, token scopes and exit codes are in the [stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md) (section 6b) and the summary is in [Droplet hardening: the outside check](Droplet-Hardening.md#the-outside-check-zero-open-ports).

How to read its result, from the stage 1 guide: exit 0 means every attempt timed out, exit 1 means something answered (a refusal counts as an answer), and exit 2 means "cannot tell", which is never counted as a pass. Run it after any change to a firewall or droplet, and repeat from a second network before calling it verified.

What a clean result does **not** prove, again from the guide and the hardening page:

- UDP. Silence on UDP only means "open or filtered".
- Any network other than the one it ran from.
- Anything after the moment it ran. A later change can reopen a door.
- Anything inside: it cannot see the metadata service, a stolen token or a person with access.
- Anything at all if the DigitalOcean API it reads the targets from is wrong.
- Anything yet in practice: its logic is tested against fakes and loopback, and it has not been run against real infrastructure.

An outside check is one instrument. The inside lists (firewall rules, the plan policy, the IPv6 test) say what is declared, and the outside check says what answered. When the two disagree, believe the outside, then find out why.

## The port-move rule

Moving a service to a different port, for example SSH to a high number, does not shrink the attack surface. The service is still reachable and still has the same flaws, and a scanner tries every port in minutes. That is security through obscurity, and no page in this wiki counts it as protection. The section "What does not count as protection" on the Plan for failure page gives the reasoning, [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) lets you run the scan yourself, and this project's sshd stays on port 22 for exactly that reason ([Droplet hardening](Droplet-Hardening.md#host-firewall-built-off-by-default)).

Two honest uses of a different port are not protection claims. It can make your logs quieter, because automated guessing aimed at the default port does not reach it, which is log noise and not a control. And it can be forced by function: a honeypot that needs port 22 for its lure pushes the real management service elsewhere. Say which of these it is, every time.

What to do instead is to remove or restrict the door: a default-deny firewall, a path only your identity can use, keys instead of passwords, and patching. Those are the entries in the table above.

## Log it and alert on it

A smaller surface makes the logs smaller and the alerts clearer: when almost nothing is allowed, almost anything that happens is worth a look. Two honest notes first. This repository configures **no firewall logging** (I found none in `modules/firewall/`, 2026-10-30), and the host log shipping below is **opt-in, off by default and not applied** (`variables.tf` in `stacks/10-access/` and `modules/twingate-bootstrap/`; [stage 2 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md)). So the middle column says what the repository has built, and the right column is a **recommendation** unless it names a source.

| Surface | What should be logged | What should alert |
|---|---|---|
| Inbound ports and the firewall | Every change to a firewall or rule, from the infrastructure runner's run history. The result and date of each outside check. | Any answer from the outside check (exit 1 or 2). Any plan the policy denies. Any rule not scoped to a tag. (recommendation; the policy and the check exist, the alerting around them is yours to wire) |
| Public addresses | Which addresses exist and which droplet each belongs to. | A new public address that nobody planned, or any IPv6 address at all in this project. (recommendation) |
| Accounts on a host | Logins and `sudo`, from the journal and `/var/log/auth.log`. With log shipping on, the agent collects the `ssh` and `sudo` units and that file, and `auditd` watches `/etc/passwd`, `/etc/group`, `/etc/shadow`, `/etc/gshadow`, `/etc/sudoers`, `/etc/sudoers.d/` and `/etc/twingate/` for writes (`modules/twingate-bootstrap/cloud-init.yaml.tftpl`). | A burst of failed logins, a login by any name other than `cah-admin`, and any write to a watched file. The stage 2 guide's L3 check creates one failed login on purpose and reads the alert it produces. (partly built; not run) |
| Accounts in services | Sign-ins and permission changes in each service's own audit log. | A new member, a new token or a changed role. (recommendation; this repository does not say which audit logs each vendor offers, so check the vendor's page before relying on one) |
| Keys and tokens | When each token was created and last used, if the provider shows it. First-boot scripts here print no token (the install log is written "no token printed", per the first-boot diagram on the hardening page). | A token used from an unexpected place, a token past its 90 day rotation date, and the billing alerts. The billing alerts at $10 and $25 are in the [Threat model](Threat-Model.md) (T11). |
| Inside the host | Nothing today: with `metadata_lock` off, a read of the metadata service is not logged. | Once the lock is applied and a log source exists, a reject of an outbound connection to the metadata address from a user other than root or the monitoring agent. (recommendation) |
| Dependencies | CI runs on every pull request, and the pins are in the repository's history. | A pin that changes, a package source whose key no longer matches, and a published advisory against something you pinned. (recommendation) |
| People | Who approved and confirmed each apply, in the code host and the infrastructure runner. | An apply nobody expected, and any change to who has access. (recommendation) |

A log nobody reads is not a control, and an alert nobody can act on trains people to ignore alerts. Each alert should say what it means and what to do next: [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) teaches how to write one, and [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) covers what this project plans to collect and why.

## Free path: a lab with nothing to lose

Both exercises are on your own computer. Each has Predict, Do and Check.

### Exercise 1: list your own inbound surface

**Predict.** How many programs on your computer accept a network connection right now? Write down a number before you look.

**Do.** On Linux:

```
ss -tuln
```

On macOS (est.; not run here):

```
lsof -nP -iTCP -sTCP:LISTEN
```

Each line is one thing listening. The local address column matters most: `127.0.0.1` (or `::1`) means only this computer can reach it, and `0.0.0.0` (or `*`, or `[::]`) means every network interface, which may include the one facing your network. The exact lines differ on every machine, so no output is shown here.

**Check.** For each listener that is on all interfaces, answer the six questions above: who owns it, why does it exist, and could it be bound to `127.0.0.1` or removed? Compare with your prediction. The usual surprise is how many there are and how few you chose.

### Exercise 2: remove a door, do not hide it

This script opens one listener on `127.0.0.1` on a port the operating system picks, then tries 101 ports around it, then closes the listener and tries again. It never touches any address but your own computer.

```python
import socket

listener = socket.socket()
listener.bind(("127.0.0.1", 0))
listener.listen()
door = listener.getsockname()[1]
window = range(door - 50, door + 51)


def answering():
    found = []
    for port in window:
        probe = socket.socket()
        probe.settimeout(0.5)
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            found.append(port)
        probe.close()
    return found


print("ports tried:", len(window))
print("the door was found:", door in answering())
listener.close()
print("after closing it, the door was found:", door in answering())
```

**Predict.** Does the scan find the listener when it is a random, unannounced port? Does it find it after the listener is closed?

**Do.** Save the script as `door.py` and run `python3 -I door.py`.

Output, from one run on Linux with Python 3.13:

```text
ports tried: 101
the door was found: True
after closing it, the door was found: False
```

**Check.** The scan found the door although nobody told it which port to try: a port nobody announced is not hidden, it is simply not yet checked. And the only thing that made the door go away was closing it. That is the whole lesson in two lines: shrinking is removing, and measuring is trying every port.

Free path summary: both exercises are free and run offline.

## Checkpoint

1. Name the six categories of attack surface.
2. In this project, why does a droplet have a public address if nothing can connect to it?
3. What does `scripts/zero_ports_check.py` do to make sure it is only ever used on this project's own droplets?
4. Why does a clean result from it not prove the connectors are safe?
5. Is the metadata lock applied today? What is the accepted risk until it is?
6. Give two reasons a person might run a service on a non-default port, and say why neither is a protection claim.
7. Pick two rows of the logging table and say what you would alert on and what the person who gets the alert should do.

Answers: (1) inbound ports, public addresses, accounts, keys and tokens, dependencies, people. (2) DigitalOcean gives every droplet one and it cannot be removed; the firewall has no inbound rules from the internet, so nothing answers ([Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md)). (3) It takes no address at all and discovers its targets only from the provider's API, requiring a tag, the project and an expected count. (4) It sees only TCP, only from one network, only at one moment, and nothing inside. (5) No, it is built and off by default; the accepted risk is that any local process can read the user-data, connector tokens included (T5). (6) Quieter logs and a function that forces the move, such as a honeypot needing port 22; neither changes who can reach the service.

## Common mistakes

- **Counting only ports.** Most real incidents start with a credential or a dependency, which are on the list too.
- **Calling something removed when it was hidden.** A new port number, a renamed login page or a hidden banner is the same door.
- **Treating a clean scan as a certificate.** It is one network, one moment and one protocol.
- **Scanning an address you do not own "just to look".** Ownership or written permission comes first, every time.
- **Writing "no metadata endpoint" or "zero inbound" without the qualifier.** State the exact version of the claim.
- **Logging without a reader.** Decide who gets the alert before turning the log on.

## Claims register

Every project claim above was read on 2026-10-30 in this repository. Nothing was applied or run against real infrastructure except the loopback script.

| Claim | Where read | Status |
|---|---|---|
| Zero inbound from the internet, one tag-scoped TCP 22 rule between connectors | [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md), `stacks/10-access/main.tf` | Read |
| The plan policy denies inbound rules open to the internet or not scoped to a tag | [Why not private droplets (yet)](Why-Not-Private-Droplets-Yet.md) (its description of `.spacelift/policies/plan.rego`) | Read the description; I did not re-derive it from the policy text |
| IPv6 closed, enforced by a test that reads the repository | [Droplet hardening](Droplet-Hardening.md#ipv6-stays-closed), [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) | Read |
| `cah-admin` only, key only, root off, `AllowUsers` | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` (lines for `lock_passwd`, `ssh_pwauth`, `PermitRootLogin`, `AllowUsers`) | Read |
| 90 day rotation for the DigitalOcean, Twingate and Doppler tokens | [Doppler and secrets](Doppler-and-Secrets.md) | Read |
| The metadata service serves user-data with connector tokens, and `metadata_lock` is off by default and untested | [Droplet hardening](Droplet-Hardening.md#metadata-endpoint-lock-built-off-by-default), `stacks/10-access/variables.tf`, [Threat model](Threat-Model.md) T5 | Read |
| The outside check cannot be given an address, its exit codes and its limits | [Droplet hardening](Droplet-Hardening.md#the-outside-check-zero-open-ports), [stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md) section 6b | Read; script not run against real infrastructure |
| Log shipping, `auditd` watch list and journal sources are opt-in and not applied | `modules/twingate-bootstrap/cloud-init.yaml.tftpl`, `stacks/10-access/variables.tf` | Read |
| No firewall logging in the firewall module | `modules/firewall/` searched for "log", 2026-10-30 | Searched, nothing found |
| Billing alerts at $10 and $25 | [Threat model](Threat-Model.md) T11 | Read |
| The loopback script output | Run once, Linux, Python 3.13, 2026-10-30 | Run |
| macOS `lsof` command | Not run here | est. |

Back to the [Threat model](Threat-Model.md), Plan for failure or [Droplet hardening](Droplet-Hardening.md).
