# The CIA triad: confidentiality, integrity and availability, with this project as the worked example

Side page to the start-from-zero pages. Read it before [Backups, recovery and patching](Backups-Recovery-and-Patching.md) if "what are we protecting, and from what" is still fuzzy, or at any point you want one short checklist to hold against a system. It names the three properties that almost every security control is for, shows how real failures map onto them, and then checks this repository's own controls against them, with the file that implements each. It does not repeat the pages it points at. Next: the lessons on business continuity and on disaster recovery (named here in plain text; they are issues 356 and 357 and are not written yet).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. One local script was run; everything else was read, not run.** On **2026-10-31** I ran the Bash script in the free path once on a Debian-based Linux machine (GNU bash 5.2.37, GNU coreutils 9.7, GNU tar 1.35, as an ordinary user) and pasted its output. **Not run:** the script on macOS or Windows, any PowerShell version (none is given), and every control in the project table (I read the files; I applied no stack and ran no check against a real droplet, bucket or account). The standard definitions come from NIST pages I downloaded and read on **2026-10-31**, listed with their URLs in the [claims register](#claims-register). The project table says "Built", "Written, off by default" or "None" for each row, taken from the files and pages named; where a row rests on a page and not on code I read, it says so.

> **Prerequisites.** [Threats in plain words](Threats-in-Plain-Words.md) for the words vulnerability, exploit and ransomware, and [The terminal and your first script](Terminal-and-Your-First-Script.md) for running a script. [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) helps for the integrity part but is not required. The free path needs a Linux machine or WSL 2 with `bash`, GNU `tar`, `sha256sum` and `stat` (stock macOS lacks the GNU forms, so it is not written for macOS). No cloud account, no network, no installs. About 60 minutes with the exercise (est.).

> **Where this runs.** Everything in the free path happens in one folder the script creates with `mktemp -d` and deletes at the end. It reads nothing else on your machine and opens no connection. Nothing on this page scans, probes or attacks anything.

## What you will be able to do

- Say what **confidentiality**, **integrity** and **availability** each mean in one plain sentence, give a non-tech example of each, and say what breaks it.
- Tell which property a real failure hit first, and say when it hit more than one.
- Explain why the three pull against each other, with two examples.
- Say what **authenticity** and **non-repudiation** add, and why some sources fold them into integrity while others list them apart.
- Read this project's controls as a table and find the gaps: a property with nothing behind it.
- Check a file's integrity with a hash, show an access rule refusing a read, and time a restore, all on your own computer.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| The three letters inside a severity score | [Threats in plain words](Threats-in-Plain-Words.md) and [Backups, recovery and patching](Backups-Recovery-and-Patching.md) decode `C:H I:H A:H` in a CVSS vector. | What the three letters mean on their own, before a score uses them. |
| Why controls exist | [Threat model](Threat-Model.md) lists threats and controls. | Which property each control protects, so a missing one is visible. |
| Containing damage | The lesson called Plan for failure: blast radius and assuming breach (named in plain text here) asks what a compromise can reach. | The triad is the list of what "damage" can mean. |
| Backups and restores | [Backups, recovery and patching](Backups-Recovery-and-Patching.md) | It is the availability part of this page, in depth. |

## The three properties in plain words

The standard definitions are NIST's, which take them from US law (44 U.S.C. Sec. 3542) and quote them in FIPS 199, the 2004 standard for sorting systems by how much a failure would hurt. The quotes are below; the plain words and the examples are mine.

### Confidentiality

NIST: "Preserving authorized restrictions on information access and disclosure, including means for protecting personal privacy and proprietary information." A loss of confidentiality is "the unauthorized disclosure of information."

In plain words: only the people who are allowed to see something can see it. A sealed letter is the picture: anyone can carry it, only the addressee should open it. A doctor's file on a patient is the same idea with a rule behind it.

What breaks it: a password pasted into a public place, a stolen laptop with an unencrypted disk, a misconfigured storage bucket anyone can list, a person who looks at something they were never meant to. Nothing is deleted or changed. That is why it is the easiest to miss: the owner still has everything and may never learn that someone else has a copy.

### Integrity

NIST: "Guarding against improper information modification or destruction, and includes ensuring information non-repudiation and authenticity." A loss of integrity is "the unauthorized modification or destruction of information."

In plain words: the information is what it is supposed to be, and nobody changed it without being allowed to. A signed contract is the picture: the words on the page are the words that were agreed. A bank balance that quietly changes is an integrity failure even if nobody else can see it.

What breaks it: a person or a program changes a value (a price, a config file, a dependency), a download is swapped for a tampered one on the way, a disk silently corrupts a file, or a bad edit is applied by someone who was allowed to apply it. Note the last one: integrity is about **improper** change, and a mistake by an authorized person is improper too.

### Availability

NIST: "Ensuring timely and reliable access to and use of information." A loss of availability is "the disruption of access to or use of information or an information system."

In plain words: the thing works and you can reach it when you need it. A shop that is open during its posted hours is the picture. A safe so secure nobody can open it is not available either.

What breaks it: a disk dies, a region goes dark, a bill is not paid and the account is suspended, a service is flooded with traffic, a key is lost so the data cannot be opened, a ransomware program locks the files. Both attackers and plain accidents do this, and accidents are the more common cause.

### The same three, side by side

| | Question | A loss looks like | Typical protections |
|---|---|---|---|
| Confidentiality | Who can read it? | Someone unauthorized has a copy | Access rules, encryption, secrets kept out of code, no open doors |
| Integrity | Is it still what it should be? | Content changed or destroyed without permission | Hashes and signatures, review before change, versioning, least privilege to write |
| Availability | Can I use it now? | It is slow, unreachable or gone | Redundancy, backups you have restored, capacity, rebuild-from-code |

The three together are called the **CIA triad** (the letters have nothing to do with the intelligence agency). NIST's FIPS 199 treats the three as the "security objectives" and asks you to rate the harm of losing each one separately as low, moderate or high, so a system can be, for example, high on confidentiality and low on availability ([FIPS 199](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.199.pdf), read 2026-10-31). A public web page is the opposite: no confidentiality to lose, a lot of integrity and availability.

## How real failures map to the triad

Most real events hit more than one property. The table says which one is hit **first** and what follows. These are generic shapes, not accounts of a named incident.

| Event | Hits first | Then | Why |
|---|---|---|---|
| **Ransomware** | Availability: the files are encrypted and unusable | Integrity (the files were changed); confidentiality, when the attacker also copies the data first and threatens to publish it (est.; common in reports, not a claim about one case) | The attacker's product is your loss of access. A backup you have restored is the answer to the first part and does nothing for the second. |
| **A leaked token** (an API key pasted into a public repository) | Confidentiality: someone who should not have the key has it | Integrity and availability, **as far as the token's permissions reach**: a read-only token mostly costs confidentiality, a write token can change or delete things | The damage is the token's scope, which is why least privilege and blast radius sit next to this triad. |
| **A bad deploy** (a typo in a firewall rule, a wrong config pushed) | Integrity: the system is now not what was intended | Availability (the site is down) or confidentiality (the rule opened a door) | No attacker needed. The change was authorized and still improper. |
| **A cloud region outage** | Availability: the service is unreachable | None, if nothing is lost; integrity if writes were half done | Nothing was stolen or changed. Redundancy across regions is the control; backups in the same region do not help. |
| **An insider** (a person with legitimate access misusing it) | Confidentiality (they read or copy what they should not) or integrity (they change records) | Availability, if they delete things | They are already inside, so a firewall does not matter; what matters is what each account can do and whether the use is logged. |

Two readings to take away. First, **ask which property first, then ask what follows.** The same event is a different problem depending on the answer, and so is the response: a leaked key is solved by revoking it, an outage by waiting or failing over, a tampered file by restoring a known good copy. Second, **availability is the one people forget** when they think about security, because nothing was stolen. A lost day is still a loss.

## The trade-offs: why you cannot maximize all three

The triad is a set of dials, not a checklist where everything goes to maximum. Turning one up usually turns another down, and the right setting depends on what you are protecting.

- **Confidentiality against availability.** Encrypt a backup and a thief cannot read it; lose the key and **you** cannot either. A second copy of your data in another place protects availability and gives an attacker a second place to steal from. The tightest access rule is also the one that locks out the person who needs it at 3 a.m.
- **Integrity against availability.** Requiring a review and a signature before every change keeps bad edits out and makes a fix slower. A system that refuses to start when a check fails is safe from tampering and down until someone looks. (This project's Doppler download refuses to run on a checksum mismatch, which is the right choice there and an outage if the pinned hash is ever wrong.)
- **Confidentiality against integrity.** Logging everything so you can prove who changed what (integrity, accountability) means the logs themselves hold sensitive data that now needs protecting.
- **Cost against all three.** Redundancy, review and encryption cost money and effort. A lab with a $30 ceiling chooses where to spend it, and says so in the [threat model](Threat-Model.md) as accepted risks.

The question to ask is not "how do I maximize security" but "which property would hurt most to lose here, and what am I willing to give up for it". That is exactly the FIPS 199 exercise: rate each loss, then decide.

## Extra properties some frameworks add

Three letters are the common core. You will meet others, and it helps to know they are **extensions**, not rival definitions.

- **Authenticity** is the property that data really came from its stated source. NIST's glossary gives "the property that data originated from its purported source" ([NIST glossary: authenticity](https://csrc.nist.gov/glossary/term/authenticity), read 2026-10-31). A digitally signed software release is authentic if the signature checks against the publisher's key.
- **Non-repudiation** is assurance that a person or system cannot later deny having done something. NIST's glossary describes it as "a service that is used to provide assurance of the integrity and origin of data in such a way that the integrity and origin can be verified and validated by a third party" ([NIST glossary: non-repudiation](https://csrc.nist.gov/glossary/term/non_repudiation), read 2026-10-31). A signed contract, or a signed commit that only one private key could have made, is the picture.

Here the sources differ, and that is worth knowing. The FISMA wording quoted above **puts both inside integrity**: "includes ensuring information non-repudiation and authenticity". Some other frameworks and textbooks list them as separate properties next to the three. Both are fine; check which list your course or auditor uses. Others you will see are accountability (every action traceable to someone), privacy, and safety for systems that move physical things. I did not read a standard for those three in preparing this page, so treat the list as **est.**

## Where this shows up in this project

Each row is one control, the property it mainly protects, the file that implements it and whether it exists. "Built" means the file is in the repository and does what the row says; I read the file and did not apply it. Where nothing exists the row says **None**, because a missing control is a finding, not a blank. The same control can serve two properties; the table lists it once under the one it is mainly for.

| Property | Control | File that implements it | Status |
|---|---|---|---|
| Confidentiality | **No inbound door.** Inbound is deny-all, and a rule admits only droplets carrying the firewall's own tag, never an address | `modules/firewall/main.tf` | Built |
| Confidentiality | **An outside check that every port times out** (run by hand) | `scripts/zero_ports_check.py` | Built; not run for this page |
| Confidentiality | **Secrets come from Doppler at run time**, not from files in the repository; `.env`, `*.tfvars` and state files are git-ignored | `scripts/spacelift/doppler-env.sh`, `.gitignore` | Built |
| Confidentiality | **A placeholder or empty secret is refused**, so the project cannot run with a value everyone has read in the docs | `scripts/secret_rule.py` | Built |
| Confidentiality | **The bucket is private**: the variable accepts only `private` and anything else fails | `modules/spaces-bucket/variables.tf` | Written, off by default (the stage 3 stack is off) |
| Confidentiality | **Keys only for SSH, no password login** | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` | Built |
| Confidentiality | **Encryption of data at rest that the project controls** | None in this repository. DigitalOcean's own page says its automated droplet backups are not encrypted at rest (see [Backups, recovery and patching](Backups-Recovery-and-Patching.md#four-words-that-sound-alike)); droplet backups are off here, and the bucket's encryption is the provider's, not set in code | None |
| Integrity | **The Doppler download is pinned by SHA-256** per CPU architecture and refused on mismatch | `scripts/spacelift/doppler-env.sh` | Built |
| Integrity | **The Twingate apt key must match a pinned fingerprint** before it is trusted | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` | Built |
| Integrity | **Pipeline code is pinned by commit**: the shared CI and security workflows are called by full commit hash with the version in a comment, and the workflow's default permission is none | `.github/workflows/ci.yml` | Built |
| Integrity | **A plan policy denies a plan that opens a port or turns on IPv6**, whatever code produced it | `.spacelift/policies/plan.rego` | Written and tested in CI; the repository's own page says it is not yet attached in Spacelift |
| Integrity | **Versioning on the state bucket**, so an overwritten or deleted object has an earlier version | `modules/spaces-bucket/main.tf` | Written, off by default |
| Integrity | **File integrity monitoring on real hosts** | None built. The lesson [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) runs on a scratch folder, and its own page says the agent configuration for real paths is not built | None |
| Integrity | **Signed container images that this project builds** | None. The project builds no image; I searched every text file for `cosign` and `sigstore` and found no use of either | None |
| Availability | **Two connectors, at staggered reboot times**, so one going down does not lock everyone out | `stacks/10-access/main.tf` | Built |
| Availability | **Rebuild from code**: a lost droplet is recreated by applying the stack; droplet backups are `false` on purpose | `modules/twingate-connector/main.tf` | Built (the rebuild path; the data backups for stage 3 are planned, not built) |
| Availability | **A bucket that is never deleted with its contents by accident** (`force_destroy = false`) and keeps old versions for a set time | `modules/spaces-bucket/main.tf` | Written, off by default |
| Availability | **Automatic security updates and a reboot window** | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` | Built |
| Availability | **A restore that has been timed on a real project backup** | None. There is no stage 3 data to restore yet, and the account-level state (the Twingate account, Doppler secrets, Spacelift contexts) is outside the code; see [Teardown checklist](Teardown-Checklist.md#2-what-survives-a-destroy) | None |
| Availability | **A second region or provider for the same service** | None found. The stage 1 stack takes one DigitalOcean region as its input (`stacks/10-access/variables.tf`), and I found no second-region or second-provider copy of it | None |

Three honest observations from filling in the table. **Confidentiality and integrity have many rows; availability has fewer, and its strongest control is "rebuild from code".** That is a reasonable choice for a lab whose droplets hold nothing precious and the wrong one the day stage 3 holds real data. **Every "None" is a place to ask a question**, such as who would notice a changed file on a droplet. And **"Written, off by default" is not protection yet**: a control that is not applied protects nothing today.

## Free path: three properties on your own computer

Every exercise follows four steps: **predict** (write down what you expect first), **do**, **check**, **undo**. This one script exercises all three properties in a throwaway folder. Save it as `cia_lab.sh`.

```bash
#!/usr/bin/env bash
# cia_lab.sh - one throwaway folder, three properties. Touches nothing outside the folder it makes.
set -eu
lab=$(mktemp -d)
cd "$lab"
mkdir notes
printf 'meeting at noon\n' > notes/plan.txt
printf 'made-up door code 0000\n' > notes/secret.txt

echo "== Integrity: a fingerprint written down before anything goes wrong"
sha256sum notes/plan.txt > plan.sha256
sha256sum -c plan.sha256
tar czf backup.tgz notes
printf 'meeting at 1pm\n' > notes/plan.txt
if sha256sum -c plan.sha256 2>/dev/null; then echo "unchanged"; else echo "CHANGED: the check failed, so the file is not what was recorded"; fi

echo "== Availability: lose the folder, restore it, and time it"
rm -r notes
start=$(date +%s%N)
tar xzf backup.tgz
end=$(date +%s%N)
echo "restore took $(( (end - start) / 1000000 )) ms"
sha256sum -c plan.sha256

echo "== Confidentiality: who may read this file?"
chmod 644 notes/plan.txt
chmod 600 notes/secret.txt
stat -c '%a %A %n' notes/plan.txt notes/secret.txt
chmod 000 notes/secret.txt
if cat notes/secret.txt >/dev/null 2>&1; then echo "still readable (are you root?)"; else echo "denied: the rule stopped even the owner"; fi
chmod 600 notes/secret.txt

cd /
rm -r "$lab"
echo "done: the lab folder is gone"
```

**Predict first.** Before you run it, write down (a) whether the hash check fails after the file is edited, (b) whether it passes again after the restore, and (c) roughly how many milliseconds you expect a tiny restore to take.

```bash
bash cia_lab.sh
```

Output from my run (GNU bash 5.2.37, coreutils 9.7, tar 1.35, Linux, 2026-10-31). The restore time is the one line that will differ on your machine:

```text
== Integrity: a fingerprint written down before anything goes wrong
notes/plan.txt: OK
notes/plan.txt: FAILED
CHANGED: the check failed, so the file is not what was recorded
== Availability: lose the folder, restore it, and time it
restore took 21 ms
notes/plan.txt: OK
== Confidentiality: who may read this file?
644 -rw-r--r-- notes/plan.txt
600 -rw------- notes/secret.txt
denied: the rule stopped even the owner
done: the lab folder is gone
```

How to read it:

- **Integrity.** A hash is a fingerprint: change one byte and it no longer matches. The check does not say **what** changed or **who** changed it, only that it is not what was written down. It also only works because the fingerprint was recorded **before** the edit and stored apart from the file. A fingerprint kept next to the thing it protects, where the same attacker can rewrite both, proves nothing. The restore then brings back the version that matches, which shows integrity and availability working together.
- **Availability.** The whole folder was deleted and came back, and you know it came back correctly because the hash passed. The 21 ms is a tiny folder on a local disk. A real restore adds noticing, deciding, finding the backup and reaching its credentials, which a script cannot time for you. [Backups, recovery and patching](Backups-Recovery-and-Patching.md) runs this drill properly.
- **Confidentiality.** Mode `644` lets the owner write and everyone read; `600` lets only the owner read and write; `000` lets nobody, and the read was refused. Run as root the last read would succeed, because root ignores these modes, and the script then prints "still readable". The point: **an access rule is a control, and it only protects against the people it applies to.** A copy of the file in another place has none of these rules.

**Check.** Did the failed check match what you predicted? If the restore had been slower than you guessed, what would you change first: the backup size, where it is stored, or who can reach it?

**Undo.** The script deletes its own folder. Nothing else was touched; `ls /tmp` will not show it.

### A thinking exercise, no commands

Pick a system you use every day (your phone, a shared drive, a game account). For each of the three properties write one sentence: what is the worst loss, who could cause it (a stranger, a friend, you by mistake), and which one would hurt most. Rate each as low, moderate or high, the way FIPS 199 does. The one you rated highest is the one to protect first.

## Build, break, detect, evade, defend (the local loop)

All of this is on paper or in the throwaway folder.

**Build.** List the three most valuable things in your small system, and put each in the triad: which property matters most for it?

**Break (shown, not run).** For the item you rated highest, say in one sentence how the property could be lost by an honest mistake, and in one by an attacker. You do not need an exploit.

**Detect.** Name the one check that would show the loss: a hash comparison for integrity, an access log for confidentiality, a monitor or a failed restore for availability. If you cannot name one, that is a gap.

**Evade.** The tempting move is to hide the thing. Hiding it changes what a casual observer sees and changes none of the three properties for someone who knows where it is.

**Defend.** Add the cheapest control that moves the highest rating down. Write what it costs in the other two properties.

### Flip the board

You are the one who wants to cause harm and you have one foothold. Which property do you go after, and why is the answer often "the one the defender did not write a control for"? Now look at your table and find the property with the fewest rows.

## Leading into business continuity and disaster recovery

Availability is the property the next two lessons are about, and they will be written as issues 356 and 357: **business continuity** (how the work carries on while something is broken) and **disaster recovery** (how you get the systems back). Both start from questions this page already asked: which property would hurt most to lose, and how long can you live without it. The existing page [Backups, recovery and patching](Backups-Recovery-and-Patching.md) is the hands-on piece to read first: it turns "recovery point" and "recovery time" into numbers you measure, and the restore exercise in this lesson was a one-minute version of its first exercise. When the two new lessons exist they will be linked from here; until then they are named, not linked.

## Checkpoint

- Say each of the three properties in one plain sentence, from memory.
- Which property does a leaked API key hit first, and what decides how much of the other two it also hits?
- A region outage destroys no data and steals nothing. Which property was lost?
- Give one pair of properties that pull against each other, and a real control that sits on the tension.
- Why do some sources fold non-repudiation and authenticity into integrity and others list them apart?
- Name one row in this project's table that says **None**, and say which question it leaves open.
- In the lab, why was the recorded hash useless until it was stored **before** the edit and apart from the file?
- Why does a file mode of `600` not protect a copy of the file kept somewhere else?

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| "We are secure, nothing was stolen" after an outage | Treating security as confidentiality only | Ask which of the three was lost; an outage is availability |
| A hash is stored in the same folder, and the same account can edit both | An integrity check the attacker can also rewrite | Keep the fingerprint where the file's writer cannot change it |
| Everything is encrypted and the key is in the same place as the data | Confidentiality bought at the price of availability | Where is the key, and who can reach it in an emergency |
| A backup exists and has never been restored | Availability assumed, not measured | A timed restore into a fresh place, once |
| A control is "written" and called protection | A control that is off or unattached | The table's status column; off by default protects nothing today |
| An authorized person's mistake is not counted as a threat | Integrity read as "stopping attackers" | Add a typo and a wrong deploy to the same list |
| All three rated high everywhere | No one chose | Rate each loss low, moderate or high and justify each |

## Claims register

Standards and vendor pages were downloaded and read on **2026-10-31**; the repository files were read in the worktree this page was written in on the same day. Status words: **Read** means I read the passage, **Observed** means I ran it, **Not run** and **est.** mean neither.

| Claim | Source | Status |
|---|---|---|
| Confidentiality is "preserving authorized restrictions on information access and disclosure, including means for protecting personal privacy and proprietary information" | [NIST glossary: confidentiality](https://csrc.nist.gov/glossary/term/confidentiality), which cites 44 U.S.C. Sec. 3542 and FIPS 200 | Read 2026-10-31 |
| Integrity is "guarding against improper information modification or destruction, and includes ensuring information nonrepudiation and authenticity" | [NIST glossary: integrity](https://csrc.nist.gov/glossary/term/integrity) | Read 2026-10-31 |
| Availability is "ensuring timely and reliable access to and use of information" | [NIST glossary: availability](https://csrc.nist.gov/glossary/term/availability) | Read 2026-10-31 |
| A loss of each is unauthorized disclosure, unauthorized modification or destruction, and disruption of access or use; impact is rated low, moderate or high per objective | [FIPS 199, February 2004](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.199.pdf), section 3 | Read 2026-10-31 (the PDF, text extracted and the first pages viewed) |
| Authenticity is "the property that data originated from its purported source" | [NIST glossary: authenticity](https://csrc.nist.gov/glossary/term/authenticity) | Read 2026-10-31 |
| Non-repudiation is a service that assures integrity and origin so a third party can verify them | [NIST glossary: non-repudiation](https://csrc.nist.gov/glossary/term/non_repudiation) (the FIPS 186-5 entry) | Read 2026-10-31 |
| Some other frameworks list authenticity and non-repudiation as separate properties, and also accountability, privacy and safety | General knowledge | **est.**, not checked against a named standard |
| The ransomware, leaked-token, bad-deploy, region-outage and insider rows are generic shapes | General knowledge | **est.**, not accounts of a named incident |
| DigitalOcean's automated droplet backups are not encrypted at rest | [Backups, recovery and patching](Backups-Recovery-and-Patching.md#four-words-that-sound-alike), which cites DigitalOcean's limits page | Read in the repository page; the vendor page was not re-read for this lesson |
| Inbound is deny-all and a rule admits only droplets carrying the firewall's own tag | `modules/firewall/main.tf` (header comment) | Read 2026-10-31 |
| The outside check tries every TCP port of each connector and passes only if all time out | `scripts/zero_ports_check.py` (header) | Read 2026-10-31; not run |
| Doppler CLI download pinned by SHA-256 per architecture and refused on mismatch | `scripts/spacelift/doppler-env.sh` | Read 2026-10-31 |
| A placeholder or empty secret is refused | `scripts/secret_rule.py` (header) | Read 2026-10-31 |
| `.env`, `*.tfvars` and state files are git-ignored | `.gitignore` | Read 2026-10-31 |
| The bucket accepts only `private`, has `force_destroy = false`, versioning and a noncurrent-version expiry | `modules/spaces-bucket/variables.tf`, `modules/spaces-bucket/main.tf` | Read 2026-10-31; module off by default per [the cost document](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) |
| SSH is key-only (`ssh_pwauth: false`) and the Twingate apt key is checked against a pinned fingerprint | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` | Read 2026-10-31 |
| Shared workflows are called by commit hash with a version comment; workflow permissions default to none | `.github/workflows/ci.yml` | Read 2026-10-31; the called workflows were not read |
| The plan policy is written and tested; it is not yet attached in Spacelift | `.spacelift/policies/plan.rego`, the [Spacelift page](Spacelift.md) | Read the header and the page; not run |
| Two connectors with different reboot times; droplet `backups = false` | `stacks/10-access/main.tf`, `modules/twingate-connector/main.tf` | Read 2026-10-31 |
| Unattended upgrades and a reboot window are configured on the droplets | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` | Read 2026-10-31; not applied |
| File integrity on real paths is not built | [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) | Read in the project section of the wiki page earlier; not re-read for this lesson |
| No `cosign` or `sigstore` use outside the wiki | A recursive search of the repository, 2026-10-31 | Observed (a case-insensitive search of every text file found no hit except this page) |
| The Bash script and its output | The free path | **Observed** 2026-10-31, GNU bash 5.2.37, coreutils 9.7, tar 1.35, Linux |
| The script on macOS, or under another shell | | **Not run** |
