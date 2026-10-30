# Plan for failure: blast radius and assuming breach

Side page to the start-from-zero pages. Read it after [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) (core step 4, where least privilege is introduced), or at any point you are about to design, build or review a system and want one question to ask of it. It is about a **mindset**, and then it shows that the mindset is the reason for many choices you have already met in this wiki. It links those pages instead of repeating them. Next: [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from this repository's own pages and code; one local exercise was run once, the rest was not run.** I read every repository page, policy file and design note cited below on **2026-10-22** (the claims register at the end lists each, and says where I read only part of one). No vendor page is cited, so there is nothing to retrieve from a vendor. On the same day I ran the Python script in Exercise 1 with Python 3.13 on Linux, and the output shown is from that run. The PowerShell version of the same exercise was **not run** (no Windows machine here) and is marked **est.** (estimate). Several things the examples rely on are **planned, not built**, and the table in [Where this shows up in this project](#where-this-shows-up-in-this-project) says which. Nothing on this page was tested against a real attacker, and it contains no attack.

> **Prerequisites.** [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) for the words "least privilege" and "zero trust", and [The terminal and your first script](Terminal-and-Your-First-Script.md) for running a script. The exercise needs Python 3.11 or newer (3.13 was used) on any operating system, or Windows PowerShell for the second version. No cloud account, no network, no installs. About 60 minutes with the exercise (est.).

> **Where this runs.** The exercise is pure computation on a made-up graph. It reads no file on your machine, opens no connection and changes nothing. Nothing on this page scans, probes or attacks anything.

## What you will be able to do

- State the idea in one sentence: **plan for the day protection fails, not only for stopping every attack**.
- Define **blast radius**, **assume breach** and **defense in depth**, and tell them apart.
- Ask the three questions of any system: if this is compromised, what can it reach; how will I know; how do I recover.
- Point to ten real choices in this repository that exist because of that idea, and say which of them are built and which are only designed.
- Say what the idea costs, and where it does not help.
- Compute the blast radius of a small system, cut one connection, and read what the cut buys and what it costs.

## The maintainer's framing, in his words

The project maintainer (ChiefGyk3D) said this on 2026-10-22, when he asked whether the wiki teaches blast radius as a reason for how things are built. Grammar fixes only:

> In cybersecurity we do not just plan for protecting from all the attacks, but also for WHEN we will fail to protect from those attacks. We have to be right every time; they only have to be right once.

That is the whole lesson in two sentences. The rest of the page says what "plan for failure" looks like when you build something, with the project's own pages as the evidence.

## In plain words

A good security plan has to cover what happens when protection fails, not only how to stop attacks. Nobody can promise to stop every one, and the other side does not need to win often; it needs to win once, in the one place you did not cover. So the practical plan has three parts besides prevention: put several layers in the way, notice quickly when one fails, and be able to recover.

The part that is easy to skip is limiting the damage in advance. You cannot always choose whether something fails, but you can choose, ahead of time, how much it takes down with it. That size has a name, **blast radius**, defined in the next section.

## Three ideas, defined once

**Blast radius** is how far the damage of one failure, mistake or compromise can reach: everything that goes wrong, or can be touched, when one thing goes wrong. The word comes from explosions, and it is a size, not a verdict. A web server that can only reach its own disk has a small blast radius. A laptop that holds the keys to every other machine has a large one.

**Assume breach** is a way of designing and operating: you take it as given that some part of the system will be compromised or will fail, and you decide in advance what that costs you. It is a planning rule, not a prediction about your system and not an admission of defeat. You still try to prevent. You also stop treating prevention as the only plan.

**Defense in depth** is having several independent controls between an attacker and the thing they want, so one control failing does not mean everything fails. It is the "several layers" half of assuming breach: blast radius limits what a breach reaches, and depth makes a breach take more steps.

## Why defenders have to be right every time

A short, honest note. "We have to be right every time, they only have to be right once" is a slogan about **asymmetry**: a defender is judged over every day and every system, and an attacker can try as often as they like and only needs one success. It is a true description of the pressure. It is **not** a claim that a perfect defense exists, and it is not a reason to give up, because the practical answer to the asymmetry is not "be perfect". The practical answer is three things at once:

1. **Layers**, so being wrong once does not mean losing everything.
2. **Detection**, so being wrong once is noticed in hours and not months.
3. **Recovery**, so being wrong once is an event you can undo.

A slogan can also be misused. "We cannot stop everything, so why bother" is the wrong reading. Prevention removes most of the easy attacks, and everything below this heading is what covers the rest.

## Contain, detect, recover, and prevent

Four jobs, in the order you would do them to a single system:

| Job | The question | What it looks like |
|---|---|---|
| **Prevent** | Can I stop the attack from working at all? | Patches, closed ports, strong login, least privilege. The most valuable job and the one that never reaches 100%. |
| **Contain** | If it works, how far does it get? | Separate accounts, separate machines, narrow credentials, narrow network paths. This is blast radius work. |
| **Detect** | How soon do I know? | Logs, alerts, file integrity checks, decoys. |
| **Recover** | How do I get back to a known good state? | Rebuild from code, restore from a backup you have tested, rotate what leaked. |

The jobs are not alternatives. Prevention is first because it is cheapest per attack stopped. The other three exist because prevention fails sometimes, and a system with only the first has no plan for that day.

> **Three questions for any system.** Ask them of a laptop, a web server, a cloud account, a script with a token, or a plan for a new service.
>
> 1. **If this is compromised, what can it reach?** (Contain. Every credential it holds, every network path it has, every machine that trusts it.)
> 2. **How will I know?** (Detect. Which log, alert or check would show it, and who looks at it.)
> 3. **How do I recover?** (Recover. Rebuild, restore or rotate, and have you done it once, on purpose, before you needed it.)
>
> If you cannot answer one of them, that is the finding.

## Where this shows up in this project

Each row names a real choice, links the page that teaches it, and says whether it exists today. "Built" means it is in the repository and described by its own page as built. "Designed" or "planned" means a page or design note describes it and it is not built. Where I could not tell, the row says so.

| Job | The choice | What it limits or shows | Status | Read |
|---|---|---|---|---|
| Prevent and contain | **Zero inbound ports** on every droplet. The Twingate connectors dial out; nothing listens for the internet. | A bug in a service that would be exposed has no path in from outside. The firewall tests, a plan policy and an outside port check all test this rule. | Built for the stage 1 connectors. The outside check is a script you run by hand, and its own page says its logic was tested against fakes and loopback. | [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md#what-ztna-does-instead), [Droplet hardening: the outside check](Droplet-Hardening.md#the-outside-check-zero-open-ports) |
| Contain | **A stack per stage today, and a stack per service by ruling.** Each stack has its own state, so a bad **change** (a mistaken plan or apply) reaches only what is in that stack's state. | A bad edit to one stack cannot plan a change to another. This is a boundary for changes only. **Credentials are a separate boundary and today a wider one:** stacks 00 and 10 load the same DigitalOcean token from one Doppler config, so a stolen or misused token reaches everything either stack manages (see the shared-token example below). For the future edge the ruling is one droplet per internet-facing service, so a compromised iperf3 no longer shares a disk with the MQTT broker's keys. | Stacks 00, 10 and 20 are built. The per-service split and the edge are a **ruling and a design note, not built**. | [Build and destroy: why one stack per service](Build-and-Destroy-Stack-Per-Service.md#why-one-stack-per-service), [the stack-per-service note](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-22-stack-per-service.md) |
| Contain | **A fail-closed plan policy with keyed allowlists.** A plan that opens an inbound port to anything but a tag, turns on IPv6, deletes the network, or comes from a stack with autodeploy on is denied. An exception is a reviewed code change, keyed by stack, and anything unknown is denied. | Limits what one mistaken or malicious change can do, even if the code that produced it was wrong. An exception for one service does not cover another. | The policy is **written and tested, and not yet attached** to a stack in Spacelift, per its own page. | [Spacelift: the allowlist model](Spacelift.md#the-plan-policy-the-allowlist-model), [no open ports in a plan](Spacelift.md#the-plan-policy-no-open-ports-in-a-plan) |
| Contain | **The cost gate and the phase ceilings.** A pull request that adds paid resources beyond the approved monthly ceiling fails CI, and raising the ceiling is its own reviewed edit. | A mistake, or a runaway copy of a resource, has a bounded bill. This is the blast radius of an error measured in dollars. | Built and run in CI. It reads code with patterns; it cannot see what is created outside the repository. The `labs/` directory is **exempt** from the resource allowlist and is not counted in any ceiling, because a learner's bill is the learner's, so for labs the limit is the lab's own stated cost, not the gate. | [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md#the-cost-gate), [the labs exemption in the cost document](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md#the-labs-exemption-option-l1) |
| Contain | **Resource-scoped access, not a flat VPN.** Each Twingate resource is one private address and one port, and access is a group kept as code. | A person, or a stolen login for that person, reaches the resources the group names, not the whole network. It does **not** limit the credentials in Doppler or the Twingate API token (see the secrets row), and the two connectors may SSH to each other by design (TCP 22 between droplets carrying the connector tag), so one connector host is not isolated from the other. | Built for the stage 1 access layer. | [Twingate: one resource per host and port](Twingate.md#one-resource-per-host-and-port-never-the-whole-vpc), [why connector a may SSH to connector b](Twingate.md#why-connector-a-may-ssh-to-connector-b), [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) |
| Contain | **Secrets scoped per asset (a ruling, only partly built).** The pattern is one Doppler config and one short-lived, read-only token per service, host or site. What exists today is wider: Spacelift runs for stacks 00 and 10 fetch from **one** Doppler config (`clouds-against-humanity` / `prd`) through one context, and `DOPPLER_TOKEN` is present in every run, so code that gets into a run could read the whole config, including secrets that stack never asked for. Stack 00 asks only for the DigitalOcean token ("least privilege for honest code, not isolation", in the Doppler page's words). | Where per-asset configs exist, a leaked token exposes one asset's secrets. Today, a compromised run exposes the whole shared config. | The shared Spacelift config is built and in use. The telemetry site config is written and tested but opt-in, off by default and not applied anywhere, and its two connectors share one token. The per-service edge configs are **ruled, not built**. | [Doppler and secrets: who holds what](Doppler-and-Secrets.md#who-holds-what), [Secrets from day one: one config and one token per asset](Secrets-From-Day-One.md#one-config-and-one-short-lived-token-per-asset) |
| Detect | **A SIEM fed by the hosts' logs,** with `auditd` watch rules on the identity files, `sudoers` and the Twingate configuration. | Shows that something changed on a host. | The shipping is opt-in, off by default and **never applied** to a real machine, per the pages. | [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md#where-this-shows-up-in-this-project), [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) |
| Detect | **Honeypot alerts.** A decoy no legitimate user touches turns any touch into a high-signal alert. | A cheap way to notice an intruder who is already inside. | The lessons run on synthetic events on your computer; the Wazuh rules are an **unverified draft**; the cloud honeypot is a design. | [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md#how-a-decoy-event-becomes-an-alert) |
| Detect | **File integrity monitoring.** Hashes of files you chose to watch, compared with a stored baseline. | Shows a changed config or binary. | The lesson runs on a scratch folder. The agent configuration that would watch real paths is **not built**, per the page. | [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) |
| Recover | **Code is the backup for the machines,** and a tested restore for data. Lose a droplet, apply the stack, get an identical one. | A rebuilt machine drops whatever an intruder left on the old one. | The rebuild path is how the stacks work. The data backups for stage 3 are **planned, not built**. The Twingate account, Doppler secrets and Spacelift contexts are outside the code and need their own plan. | [Backups, recovery and patching](Backups-Recovery-and-Patching.md#a-backup-you-have-not-restored-is-a-hope), [Teardown checklist: what survives a destroy](Teardown-Checklist.md#2-what-survives-a-destroy) |

A reader who has met these pages one at a time may not have seen what they have in common. Each one answers at least one of the three questions, and most of them were written before this page existed. The page does not add a control. It names the reason.

### An example that goes the other way

Not every choice here shrinks the radius. [Fork private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md) asks what the blast radius of one token is, and notes that both stacks in that setup load the same DigitalOcean token, so its scopes must cover everything either stack manages. The honest reading is that the token's reach is wider than the stack boundary suggests: the stack boundary limits a bad change, not a stolen credential. The [Doppler page](Doppler-and-Secrets.md#who-holds-what) adds that the one read-only Doppler token is present in every Spacelift run and can read the whole config. One token per stack, and one config per stack, would help at the price of more tokens to rotate. The lesson is the question, not a claim that the project has already closed that gap.

## What does not count as protection

Changing a service to a nonstandard port, hiding a version banner, or renaming an admin page do not shrink a blast radius and do not stop an attack. They are **security through obscurity**: relying on the attacker not knowing a fact. The maintainer's position is that this is a flawed, one-trick idea. It works only until the attacker learns the fact, and learning it is cheap: a port scanner can try all 65,535 ports of a host (a default full-range scan takes minutes; a fast scanner on a good link can do it in seconds), and once it finds the service the attacker goes straight to it with the same reach as before. [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) makes the same point about banners and PHP, and [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) runs the scan so you can watch it.

Measures that work the same way every time, whether or not the attacker knows how you set things up:

- **Patching.** The flaw is gone, so there is nothing left to find behind any port.
- **Least privilege.** An account or service that can do little limits what a break-in buys.
- **Key-only authentication.** There is no password to guess; see [Droplet hardening](Droplet-Hardening.md#login).
- **A default-deny firewall.** Nothing is reachable unless a rule says who may reach it; see [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md).
- **Rate limiting.** Guessing is slowed whatever it targets; see [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md).
- **Detection.** Someone has to notice; see [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md).

A non-default port can make your logs quieter, because the automated guessing aimed at the default port does not reach it. That is a log-noise effect and not a security control, and no page here counts it as a layer. Some software picks a random port by design, for example an I2P router, which chooses one when it is first set up. That is how the software works, and it is not claimed as protection either.

Sometimes a port move is **functional**, and then the page says that is the reason. A honeypot needs port 22 for its lure, so the real management SSH has to live on another port ([Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md)). The new number protects nothing; the protection is that only your address can reach it, with a key and no passwords.

## Honest limits

- **Isolation costs money and complexity.** One droplet per service is more droplets to pay for and patch. The stack-per-service note prices its own ruled shape at $59 a month at full build, one dollar under the hard maximum of $60 (its figures, read 2026-10-22, and the sizes it assumes are unmeasured, so treat them as est.). More tokens, more stacks and more accounts mean more things to rotate, document and get wrong. Splitting is a trade, not a free improvement.
- **It does not replace patching or prevention.** A smaller radius does not make the first compromise less likely or less bad for the thing that was hit. [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) says the same about a compromised laptop: access control shrinks the reach, and endpoint security and patching still matter.
- **It covers mistakes and outages, not only attackers.** A bad deploy, a deleted bucket, a typo in a firewall rule, a stuck update or a full disk have blast radii too. Canary releases, staggered maintenance windows and a stack per service are mostly about honest mistakes. If you only think about attackers you miss the more common cause of a bad day.
- **A small environment can reasonably share one thing.** A single-person throwaway lab does not need ten accounts. The stack-per-service note itself keeps shared free pieces (the network and a bucket) in one stack, and puts the five outbound-only polling daemons on one shared host because they hold the same kind of data at the same trust level. The tradeoff to say out loud: one shared piece means one failure or one compromise reaches everything that uses it. Share on purpose, name the shared piece, and make it the one you watch hardest.
- **A detection nobody reads is not detection, and a backup nobody restored is a hope.** Containment and detection need someone, or something, paying attention; recovery needs a rehearsal.
- **Pure shrinkage has a floor.** Past a point, cutting more edges costs more in work and mistakes than it saves. The exercise below shows the cost side on purpose.

## Free path: a lab with nothing to lose

### Exercise 1: compute a blast radius, cut one edge, read the cost

A toy system with five nodes: the internet, your laptop, a web server, a NAS (a file server on your home network) and a password manager (the vault). An **edge** "A to B" means someone who controls A can reach B: a network path, a mounted share, a stored password or a trusted login. The script lists every node's reach, removes one edge, lists again, and prints what the cut costs. It is a few lines of walking a dictionary.

Save this as `radius.py` and run it.

```python
#!/usr/bin/env python3
"""radius.py - what does one compromised node reach? Pure computation, touches nothing.

Usage: python3 radius.py [FROM TO]
  no arguments   show every node's blast radius, remove web->nas, show them again
  FROM TO        remove that one edge instead (it must exist)

An edge "A -> B" means: someone who controls A can reach B (a network path, a mounted share,
a stored password or a trusted login). The cost is what you give up if you cut the edge.
"""
import sys

EDGES = {
    ("internet", "web"): ("the public site", "the site goes offline"),
    ("laptop", "web"): ("you administer it over SSH", "you must administer it from somewhere else"),
    ("laptop", "nas"): ("you open files on it", "no more file shares from this laptop"),
    ("laptop", "vault"): ("the vault is unlocked here", "you unlock the vault on a second device each time"),
    ("web", "nas"): ("uploads are stored on the NAS share", "uploads live on the web server's own disk, so it needs its own backup"),
    ("vault", "web"): ("it stores the web admin password", "you would have to remember that password another way"),
    ("vault", "nas"): ("it stores the NAS admin password", "you would have to remember that password another way"),
}
NODES = ["internet", "laptop", "web", "nas", "vault"]


def reach(edges, start):
    """Everything reachable from start, including start (a plain walk over the graph)."""
    seen, todo = {start}, [start]
    while todo:
        here = todo.pop()
        for (a, b) in edges:
            if a == here and b not in seen:
                seen.add(b)
                todo.append(b)
    return seen


def table(title, edges):
    print(title)
    for n in NODES:
        r = sorted(reach(edges, n) - {n})
        print(f"  {n:<9} compromised -> reaches {len(r)}: {', '.join(r) if r else 'nothing else'}")


def main(argv):
    cut = ("web", "nas") if len(argv) == 1 else (argv[1], argv[2]) if len(argv) == 3 else None
    if cut is None or cut not in EDGES:
        print("usage: radius.py [FROM TO]   (FROM TO must be an edge in EDGES)", file=sys.stderr)
        return 2
    table("Before:", EDGES)
    after = {e: v for e, v in EDGES.items() if e != cut}
    print(f"\nCut {cut[0]} -> {cut[1]} ({EDGES[cut][0]}).")
    print(f"What it costs: {EDGES[cut][1]}.\n")
    table("After:", after)
    b, a = len(reach(EDGES, cut[0])) - 1, len(reach(after, cut[0])) - 1
    print(f"\n{cut[0]} compromised: reach went from {b} to {a}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

```bash
python3 -I radius.py
```

Output from my run (Python 3.13, Linux, 2026-10-22):

```text
Before:
  internet  compromised -> reaches 2: nas, web
  laptop    compromised -> reaches 3: nas, vault, web
  web       compromised -> reaches 1: nas
  nas       compromised -> reaches 0: nothing else
  vault     compromised -> reaches 2: nas, web

Cut web -> nas (uploads are stored on the NAS share).
What it costs: uploads live on the web server's own disk, so it needs its own backup.

After:
  internet  compromised -> reaches 1: web
  laptop    compromised -> reaches 3: nas, vault, web
  web       compromised -> reaches 0: nothing else
  nas       compromised -> reaches 0: nothing else
  vault     compromised -> reaches 2: nas, web

web compromised: reach went from 1 to 0.
```

How to read it:

- **Predict first.** Before you run it, write down which node you think has the biggest reach. Then compare. Most people guess the web server, because it faces the internet. The laptop and the vault reach more, because they hold ways in to the others.
- **The cut helped one node and not the others.** The web server's reach fell from one to zero, and the internet's from two to one. The laptop's did not move, because the laptop still reaches the NAS directly.
- **The cost is real.** The NAS no longer holds the uploads, so the web server needs its own backup, and that is the "isolation costs complexity" point in one line.

### Exercise 2: pick a different cut

Run the script with a different edge and read what changes:

```bash
python3 -I radius.py laptop vault
```

The laptop's reach falls from three to two (it can still reach the NAS and the web server directly), and the cost line says you now unlock the vault on a second device each time. Now answer in writing, for each of the other edges: what does cutting it shrink, who does it not help, and what does it cost? Then change the `EDGES` dictionary to describe **your own** home or lab (a router, a camera, a phone, a work laptop that you keep separate) and see which node has the largest radius. That node is the one to protect and watch first.

An exit-code check, so the script can be used in a test: a bad edge exits 2 with a usage line.

```bash
python3 -I radius.py x y; echo "exit=$?"
```

```text
usage: radius.py [FROM TO]   (FROM TO must be an edge in EDGES)
exit=2
```

### The Windows PowerShell version (est.; not run)

The same walk, written for Windows PowerShell 5.1 or PowerShell 7. I did not run this: there is no Windows machine here and `pwsh` is not installed. Like the Python version it exits 2 with a usage line when the pair is not an edge (also est.). It is marked **est.** and the Python version above is the one that was run and tested.

```powershell
# radius.ps1 (est.; not run) - what does one compromised node reach? Pure computation.
# Usage: .\radius.ps1 [-From web -To nas]
param([string]$From = "web", [string]$To = "nas")
$edges = @(
  @("internet","web"), @("laptop","web"), @("laptop","nas"), @("laptop","vault"),
  @("web","nas"), @("vault","web"), @("vault","nas")
)
$nodes = "internet","laptop","web","nas","vault"
function Get-Reach($edgeList, $start) {
  $seen = New-Object System.Collections.Generic.HashSet[string]
  [void]$seen.Add($start)
  $todo = New-Object System.Collections.Generic.Stack[string]
  $todo.Push($start)
  while ($todo.Count -gt 0) {
    $here = $todo.Pop()
    foreach ($e in $edgeList) {
      if ($e[0] -eq $here -and $seen.Add($e[1])) { $todo.Push($e[1]) }
    }
  }
  return ($seen | Where-Object { $_ -ne $start } | Sort-Object)
}
function Show-Table($title, $edgeList) {
  $title
  foreach ($n in $nodes) {
    $r = @(Get-Reach $edgeList $n)
    $text = if ($r.Count) { $r -join ", " } else { "nothing else" }
    "  {0,-9} compromised -> reaches {1}: {2}" -f $n, $r.Count, $text
  }
}
if (-not ($edges | Where-Object { $_[0] -eq $From -and $_[1] -eq $To })) {
  [Console]::Error.WriteLine("usage: radius.ps1 [-From NODE -To NODE]   (the pair must be an edge)")
  exit 2
}
Show-Table "Before:" $edges
$after = $edges | Where-Object { -not ($_[0] -eq $From -and $_[1] -eq $To) }
""
"Cut $From -> $To."
""
Show-Table "After:" $after
```

## Build, break, detect, evade, defend (the local loop)

All of this is on paper or in the toy graph.

**Build.** Describe a small system you know (your home network, a side project, a stage of this project) as nodes and edges. Write the reach of each node.

**Break (shown, not run).** Pick the node with the largest reach and say, in a sentence, how it could be compromised. Examples are everyday ones: a reused password, an unpatched service, a stolen laptop, a mistaken command. You do not need an exploit, and this page contains none. The point is the reach.

**Detect.** For that node, write the one log line, alert or check that would show it. If you cannot name one, you have found a gap.

**Evade.** The tempting move is to hide the node (a different port, a quiet banner). That changes what a casual scanner sees. It does not change the reach, so it moves nothing in the table you wrote.

**Defend.** Cut the edge that shrinks the largest radius most for the least cost. Write what it costs. Write how you would rebuild the node if it were lost. Then say what you did **not** fix.

### Flip the board

You are the attacker and you have one foothold. What do you do next? Look for the foothold's edges. A defender who writes the graph first has already found your next step, and a defender who only guards the front door has not. Now be the defender with the graph: which single edge, if you cut it, would make an attacker's second step a different kind of work?

## Checkpoint

- State the maintainer's two sentences in your own words.
- Define blast radius in one sentence, and give one example that is not an attack.
- What are the three questions?
- Why is "defenders have to be right every time" not a claim that perfect defense is possible?
- Name two choices in this repository that limit blast radius, and for each say whether it is built.
- Which of this repository's examples is about detection, and which is about recovery?
- Give one cost of isolation, and one case where sharing a piece is reasonable.
- Why does changing a port number not shrink a blast radius?
- In Exercise 1, why did cutting `web -> nas` not change the laptop's reach?

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| "We are secure, we have a firewall." | Treating prevention as the only plan | Ask the three questions; the second and third will have no answer |
| Everything is isolated and nobody can work | Cutting edges with no regard for cost | The cost line for each cut; keep the cut only if the radius shrinks enough to justify it |
| The radius looks small but one token opens everything | Isolation of machines, but a shared credential | List credentials as nodes in the graph |
| Detection is "on" and nobody has ever read an alert | A log with no owner | Who reads it, how often, and what they do next |
| The backup job is green | Backup never restored | A timed restore, once, on purpose |
| A hidden port or banner is listed as a control | Obscurity counted as a layer | Would it change what a determined attacker can reach? If not, it is not a layer |
| Only attackers are modeled | Ignoring mistakes and outages | Add a typo, a bad deploy and a full disk to the same graph |

## Claims register

All entries are about this repository, read on **2026-10-22** in the worktree this page was written in. "Read" means I read the passage; "read in part" means only the passage named. No vendor page is cited.

| Claim | Source | Status |
|---|---|---|
| The maintainer's wording, and the request to teach blast radius as a reason for how things are built | Issue ChiefGyk3D/Clouds-Against-Humanity#277 (2026-10-22) | Read; wording lightly fixed for grammar |
| Zero inbound ports on droplets; outside check tries every TCP port once and passes only if all time out; logic tested against fakes and loopback | `scripts/zero_ports_check.py` (header), [Droplet hardening](Droplet-Hardening.md#the-outside-check-zero-open-ports) | Read; the check was **not** run for this page |
| Plan policy denies non-tag inbound rules, IPv6, destroys of core network pieces and autodeploy; allowlists keyed by stack id; unknown means denied | `.spacelift/policies/plan.rego` (header), [Spacelift](Spacelift.md) | Read; the page says it is written and tested and **not yet attached**; not run here |
| Stack-per-service ruling; edge per service, stage 3 shared; $59 a month at full build against `hard_max` $60; shared free pieces stay shared | `docs/superpowers/specs/2026-10-22-stack-per-service.md` sections 1, 4.3, 12 | Read; the note's own figures, with sizes unmeasured, so **est.**; the split is not built |
| Stacks 00, 10 and 20 exist | the same note, section 2 | Read |
| Cost gate and ceilings; `hard_max` 60; `labs/` exempt from the resource allowlist, not priced and not in any ceiling | [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md), `docs/cost.md`, `docs/stages/approved.json` | Read |
| Twingate resources are one address and one port; the connectors may SSH to each other | [Twingate](Twingate.md#one-resource-per-host-and-port-never-the-whole-vpc), [connector a to b](Twingate.md#why-connector-a-may-ssh-to-connector-b) | Read |
| Stacks 00 and 10 share one Doppler config and one context token; `DOPPLER_TOKEN` is present in every run; "gets" lines are least privilege for honest code, not isolation | [Doppler and secrets](Doppler-and-Secrets.md#who-holds-what) | Read; stack code (`stacks/*/versions.tf`) reads the token from the environment |
| One Doppler config and one token per asset; telemetry site shares one token between two connectors; edge configs ruled, not built | [Secrets from day one](Secrets-From-Day-One.md#one-config-and-one-short-lived-token-per-asset) | Read |
| Stage 2 log shipping and `auditd` rules are opt-in, off by default, never applied | [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md#where-this-shows-up-in-this-project) | Read |
| Honeypot lessons run on synthetic events; Wazuh rules are an unverified draft | [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) | Read the status banner and intro |
| File integrity agent configuration for real paths is not built | [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) | Read the project section |
| Droplet backups off; code is the backup for machines; stage 3 data backups planned | [Backups, recovery and patching](Backups-Recovery-and-Patching.md#where-this-shows-up-in-this-project) | Read |
| Both stacks in the private-fork setup load the same DigitalOcean token | [Fork private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md) | Read the one passage |
| "Blast radius" as a term, and "defense in depth" and "assume breach" as definitions | General practice | **est.**, my wording, not a quotation from a standard |
| Python script output | Exercise 1 | **Observed** 2026-10-22, Python 3.13, Linux |
| PowerShell script | Exercise 1 | **Not run (est.)** |
