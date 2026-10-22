# Backups, recovery and patching

Side page to the start-from-zero pages. Read it after [Droplet hardening](Droplet-Hardening.md) (core step 14), whose "Updates" table it explains from the ground up, and after [How money works in the cloud](How-Money-Works-in-the-Cloud.md) (core step 8) if the price of a backup is new to you. It does not repeat the Enterprise page on [high availability, disaster recovery and backups](Enterprise-Infrastructure-Differences.md#high-availability-disaster-recovery-and-backups); it makes you take a backup, lose the original, and time the way back. Next: [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the free local lab was run once on Linux; everything else was not run.** On **2026-10-22** the author ran every Bash command in the free path on a Debian-based Linux machine with GNU tar 1.35, gzip 1.13, GNU coreutils 9.7 and Python 3.13.5, as an ordinary user, and pasted trimmed output from those runs. Three things were **not run**: the PowerShell and Windows commands (there was no Windows machine; they are written from Microsoft's documentation and marked **est.**), the commands that read the state of your own package manager or container images on machines other than the author's apt-based one (marked **est.**), and the whole optional own-account path with one droplet (written from DigitalOcean's documentation and its public API description, never applied; run it expecting to fix something). Every vendor and standards claim was read on **2026-10-22** unless a row says otherwise, and sits in the [claims register](#claims-register) with its URL. Times and sizes vary with your machine; trust what your terminal prints over this page.

> **Prerequisites.** [How money works in the cloud](How-Money-Works-in-the-Cloud.md) (core step 8) for the price side, and [The terminal and your first script](Terminal-and-Your-First-Script.md) for running a script and reading an exit code. The free path needs a Linux, macOS or WSL 2 machine with `bash`, `tar`, `gzip`, `sha256sum` and `python3` (on macOS use `shasum -a 256` where this page says `sha256sum`, est.), or Windows with PowerShell 5.1 or later (est.). About three hours for the reading and the free exercises (est.); the optional own-account path adds about an hour of your time spread over a day or two (est.).

> **Where this runs.** Everything in the free path happens in one throwaway folder on your own computer, and the script refuses to delete anything in a folder that does not carry its own marker file. The ransomware part of the loop is **in words only**: nothing on this page encrypts, damages or hides a file outside that folder, and nothing here is a recipe for an attack. The optional path uses **your own** cloud account and **your own** provider bill.

## What you will be able to do

- Tell a snapshot, a backup, a replica and an archive apart, and say which of them a mistake, a failed disk, a stolen laptop or ransomware can reach.
- Say what RPO and RTO mean in plain words, work both out from a schedule, and say why a promise is not a measurement.
- Explain the 3-2-1 rule, and say what it still leaves open.
- Back up a folder, lose the original, restore it with a stopwatch running, and prove the restore matches what you backed up.
- Explain patch cadence, an emergency patch and a maintenance window, and say what a host-update tool such as `unattended-upgrades` patches and what it does not touch (a container image is the example that surprises people).
- Read a CVE entry and a CVSS severity score, and say what the number does **not** tell you about your own risk.
- Run Build, Break, Detect, Evade, Defend on a backup, then flip the board and review a backup plan and a patch list as the person who has to live with them.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| The price of backups | [How money works](How-Money-Works-in-the-Cloud.md) lists the backup price; [cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) says the gate prices only the weekly plan. | What a backup is, and how to know it works. |
| RPO, RTO, disaster recovery | [Enterprise infrastructure differences](Enterprise-Infrastructure-Differences.md#high-availability-disaster-recovery-and-backups) defines the words in a table. | A schedule you can work them out from, and a restore you time yourself. |
| Updates | [Droplet hardening](Droplet-Hardening.md#updates) says what runs and when. | Why host updates are not the whole story, and how to read the warning that tells you something is unpatched. |
| Patching at scale | [Golden images and patching](Enterprise-Infrastructure-Differences.md#golden-images-and-patching) and [change management](Enterprise-Change-Management-for-Beginners.md) (emergency changes). | The words cadence, window and emergency, with a plan you write for your own devices. |
| "CVE-2018-13379" in the threat model | [Threat model](Threat-Model.md) uses vulnerability names as given. | How to read one entry end to end. |

## Four words that sound alike

| Word | What it is | Usually kept | What it does not protect against |
|---|---|---|---|
| **Snapshot** | A point-in-time image of a disk or volume, taken on demand. | Often next to the original, on the same storage system (est.; it depends on the product). DigitalOcean keeps a snapshot until you delete it. | Losing the storage system or the account it lives in; a mistake you do not notice before the snapshot is replaced. |
| **Backup** | A **separate**, restorable copy made on a schedule and stored somewhere the original's failure does not reach. | Away from the original: another disk, another site, another account. | Anything that also reaches the backup (the same password, the same machine, the same building), and a copy that has never been restored. |
| **Replica** | A second live copy kept up to date continuously, so service carries on if the first fails. | Another machine or site, running. | A mistake or an attack: it copies deletions and corruption as faithfully as good data. A replica is for **staying up**, not for **going back**. |
| **Archive** | A copy kept for a long time because a rule or a need says so (records, legal hold). | Cheap storage, for years. | Short recovery times: it is built to be kept, not to be restored quickly (est.). |

DigitalOcean's own documentation shows how fuzzy the line is. Its automated backups work by taking a snapshot of the live droplet, copying that snapshot off the disk, and then deleting the snapshot; and its page on converting one to the other says that "backups and snapshots are both disk images of Droplets", with different retention: weekly backups are kept for four weeks, and a snapshot is kept until you delete it ([features](https://docs.digitalocean.com/products/backups/details/features/), [convert to a snapshot](https://docs.digitalocean.com/products/backups/how-to/convert-to-snapshot/), both read 2026-10-22). The words describe **where the copy is, how it is made, and how long it lives**; check those three for any product you meet. Two limits on the same documentation matter for what comes later: those automated backups are stored **in the same datacenter** as the droplet, and they are **not encrypted at rest** (though "not externally accessible", in the page's words), and they do not include attached volumes ([limits](https://docs.digitalocean.com/products/backups/details/limits/), read 2026-10-22).

## RPO and RTO, in plain words

Two questions decide every recovery plan, and neither is about technology.

- **RPO (recovery point objective):** how much recent work can you afford to lose, measured as **time**? "Our RPO is 24 hours" means: after a disaster we accept going back to a copy up to a day old.
- **RTO (recovery time objective):** how long can the service stay down? "Our RTO is 4 hours" means: from the failure until it works again.

Both are **targets someone chose**, usually by weighing what the loss costs against what the protection costs. Whether you meet them is a separate fact you can only learn by measuring.

**Worked example.** A nightly backup runs at 02:00. A disk dies at 16:00 the same day.

- Everything written between 02:00 and 16:00 is gone: **14 hours of loss**. The schedule gives a **worst case** of nearly 24 hours (the failure lands just before the next backup). So a nightly backup has an RPO of about a day, whatever anyone wrote in a document.
- The time to recover is: noticing (a person or an alert), deciding, finding the backup, getting the credentials to reach it, copying it back, starting the service, and checking it is right. Only the copying scales with the size of the data. A figure for the other steps is something you can only learn by doing a drill.

A weekly backup, which is what the cost gate in this repository allows, has a worst-case RPO of about a week. That is a legitimate choice for a machine you can rebuild from code in minutes (the project's droplets), and a poor one for a database nobody can rebuild.

## The 3-2-1 rule, and what it leaves open

The rule comes from a short US government paper, *Data Backup Options* ([CISA, formerly US-CERT; undated PDF](https://www.cisa.gov/sites/default/files/publications/data_backup_options.pdf), read 2026-10-22): keep **3** copies of any important file (one primary and two backups), on **2** different media types so one kind of hazard does not take both, with **1** copy offsite. A laptop, an external drive in a drawer at home, and a copy in a cloud account is a 3-2-1 plan.

What it still leaves open, and what the rest of this page is about:

- **Is a copy restorable?** Three unreadable copies are three copies. Only a restore tells you.
- **Can the same mistake reach all three?** If one account's password can delete the laptop, the drive and the cloud copy, you have one copy with three names. The [mini-loop](#build-break-detect-evade-defend-the-local-loop) turns on this.
- **How old is the newest good copy?** That is the RPO, and 3-2-1 says nothing about it.

## A backup you have not restored is a hope

Common ways a backup job "succeeds" and a restore fails, each of which you can reproduce in the free path:

| What went wrong | How it looks while it is happening | How it shows up |
|---|---|---|
| The archive is damaged (a bad disk, a cut-off copy) | The job exited 0 days ago | The restore fails with a checksum error. |
| It backed up the wrong thing, or part of it | A normal-sized archive | A file you need is not in it. |
| The key or password to open it was lost | Nothing | The restore cannot start. ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) explains why this one has no fix.) |
| The restore takes longer than the business can wait | Nothing | The clock, the first time anyone runs it. |
| It copied a database file while the database was writing | Nothing | The restored database does not start, or loses what was in memory. DigitalOcean's limits page says its backups are crash-consistent: they keep what is on the disk and "never what is in memory or cache", and are "optimized for systems with low write activity" ([limits](https://docs.digitalocean.com/products/backups/details/limits/)). |

So a restore drill has three parts: **restore into a fresh place** (never over the only copy you have), **check the result against something written down before the disaster**, and **write down how long it took**. That is the whole exercise below.

## Patching: cadence, emergencies and windows

A **patch** is a change a vendor ships to fix a defect, usually a security flaw. **Patching** is installing it. Three planning words:

- **Patch cadence** is the regular rhythm: security updates every day, a full update the first Tuesday, a reboot at 04:00. A written cadence is how a team stops patching from depending on who remembers.
- An **emergency patch** is one that skips the rhythm because waiting is too dangerous: a flaw is being actively attacked, or a very severe one is public. NIST's guide to enterprise patch management planning (SP 800-40 Rev. 4, April 2022) separates four situations a plan should cover: routine patching, emergency patching, **emergency mitigation** (reduce the risk before a patch exists, for example by turning a feature off), and **unpatchable assets** (things that cannot be patched, which need isolation) ([NIST SP 800-40r4](https://doi.org/10.6028/NIST.SP.800-40r4), read 2026-10-22). The same document warns that routine patching "is often postponed and neglected", which gives attackers more time. An emergency is not a reason to skip approval; it is a reason for a faster, pre-agreed path ([Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md) covers emergency changes).
- A **maintenance window** is a time agreed in advance when a system may be taken down or rebooted for work like this, chosen when fewest people are affected (est.; this is common usage, not a definition from a standard I read). This project gives each droplet its own reboot time an hour apart so two never restart together ([Droplet hardening: updates](Droplet-Hardening.md#updates)).

A plan also needs a **rollback** (how to go back if the patch breaks something) and a **test** first where the stakes justify one. A backup you have restored is what makes the rollback real.

### What does each tool actually patch?

This is the part most courses skip, and the part that bites. Different layers are updated by different tools, and no single one covers them all.

| Layer | Updated by | Updates itself? |
|---|---|---|
| The operating system's packages (kernel, libraries, `openssh`) | `apt` with `unattended-upgrades` (Debian, Ubuntu), `dnf` with `dnf-automatic` (RHEL family) | Only if you switched the tool on, and only for the repositories it is told to use. |
| A package from an extra repository you added | The same tools, **if** that repository is on their list | Not by default. In this project the Twingate connector comes from Twingate's own repository, which is not in the security-only list, so a separate weekly cron job updates it. |
| A **container image** | You, or tooling that rebuilds or re-pulls it | **No.** An image is as old as the tag you pulled until you pull or rebuild it and start a new container from the result. |
| The libraries inside your own application | Your build, with a tool that opens pull requests for new versions | No. |
| Firmware (router, disk, laptop BIOS) | The vendor's own updater, often by hand | Rarely. |

The facts behind the first rows:

- On Ubuntu, "security updates [are applied] automatically, without user interaction", by the `unattended-upgrades` package, "installed by default"; the file `50unattended-upgrades` lists which repositories it takes updates from, and "just adding another package repository ... WILL NOT make unattended-upgrades consider it for updates" ([Ubuntu Server documentation](https://documentation.ubuntu.com/server/how-to/software/automatic-updates/), read 2026-10-22).
- `dnf-automatic` is the RHEL-family equivalent, run from systemd timers. Its `apply_updates` setting defaults to **False**, so on its stock configuration it downloads or notifies rather than installs ([DNF Automatic](https://dnf.readthedocs.io/en/latest/automatic.html), read 2026-10-22).
- This project's droplets install `unattended-upgrades` in cloud-init, allow only the Ubuntu security origins, and reboot at a set time; the connector package gets its own weekly cron ([`modules/twingate-bootstrap/cloud-init.yaml.tftpl`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/modules/twingate-bootstrap/cloud-init.yaml.tftpl), read in this repository).

**Patch Gremlin.** The author's own project, [Patch Gremlin](https://github.com/ChiefGyk3D/Patch-Gremlin), sits on top of those two tools. Its README (read 2026-10-22) describes it as "automated system update notifications for Debian and RHEL-based systems" that "integrates with `unattended-upgrades` ... or `dnf-automatic` ... to send notifications when security updates are installed", sending to chat and push services. The point for this page: tools of this kind tell you what the **host OS package manager** did. They do not look inside a container image, and they do not read your application's dependency list. I read its README, not its code.

**Containers do not update themselves.** Docker's build guidance puts it plainly: "Docker images are immutable. Building an image is taking a snapshot of that image at that moment", so to keep images up to date "rebuild your images regularly with updated dependencies", and `docker build --pull` forces a check for a newer base image ([Docker build best practices](https://docs.docker.com/build/building/best-practices/), read 2026-10-22). A tag such as `ubuntu:24.04` can later point to a newer image, but nothing on your machine notices. A container started last month keeps running the image it started from (est.; the consequence of images being immutable, not a sentence I found in one page). So a host with `unattended-upgrades` set up perfectly can still run a container with a year-old library inside it. The remedy is the same as for any dependency: a way to be told (a vulnerability scanner, or a bot that opens pull requests for new image tags such as Dependabot or Renovate, est.), a rule for who updates, and a restart.

## Reading a CVE entry and a severity score

A **CVE** (Common Vulnerabilities and Exposures) is a public ID, such as `CVE-2021-44228`, for one specific security flaw, so every vendor, scanner and news article means the same flaw. The ID is only a name; the details live in records. **NVD** is the US government's database that adds scores and affected-software data to CVE records ([NVD](https://nvd.nist.gov/), [CVE Program](https://www.cve.org/)). A **CVSS** score (Common Vulnerability Scoring System, owned by [FIRST](https://www.first.org/cvss/)) is a number from 0 to 10 that tries to say how severe the flaw is in itself.

### A worked entry

On 2026-10-22 the NVD record for `CVE-2021-44228` (the "Log4Shell" flaw in the Apache Log4j 2 logging library) read like this in the fields that matter (trimmed; Exercise 4 gets it yourself, and the record changes as analysts edit it):

```text
id          : CVE-2021-44228 | Analyzed
published   : 2021-12-10T10:15:09.143  last modified: 2026-08-11T19:33:44.513
description : Apache Log4j2 2.0-beta9 through 2.15.0 (excluding security releases 2.12.2, 2.12.3, and 2.3.1) JNDI features ... an attacker who can control log messages ... can execute arbitrary code ...
score       : cvssMetricV31 from nvd@nist.gov (Primary): 10.0 CRITICAL  CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H
score       : cvssMetricV2 from nvd@nist.gov (Primary): 9.3 HIGH  AV:N/AC:M/Au:N/C:C/I:C/A:C
weakness    : nvd@nist.gov ['CWE-917']
KEV         : added 2021-12-10 due 2021-12-24 - Apache Log4j2 Remote Code Execution Vulnerability
```

Read it in this order:

1. **Which software and which versions?** "Log4j2 2.0-beta9 through 2.15.0", with listed fixed releases. If you do not run that library, in a version in that range, this entry is not about you. This is the most important line and the one a score hides.
2. **What can an attacker do?** "Execute arbitrary code": run their own program on the machine.
3. **The vector string** is the score's working: `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H`. Each pair is a question:

| Pair | Question (FIRST specification v3.1) | Here |
|---|---|---|
| `AV:N` | Attack Vector: how far away can the attacker be? The more remote, the higher the score. | **N**etwork: over a network. |
| `AC:L` | Attack Complexity: must conditions beyond the attacker's control line up? | **L**ow: no special conditions. |
| `PR:N` | Privileges Required: must the attacker already have an account? | **N**one. |
| `UI:N` | User Interaction: must some other person do something (click a link)? | **N**one. |
| `S:C` | Scope: can the flaw affect things beyond the vulnerable component's own security boundary? | **C**hanged: yes. |
| `C:H` `I:H` `A:H` | Impact on confidentiality, integrity and availability. | **H**igh each: total loss of all three. |

4. **The number and its band.** FIRST's qualitative scale (the same in v3.1 and v4.0): **None** 0.0, **Low** 0.1 to 3.9, **Medium** 4.0 to 6.9, **High** 7.0 to 8.9, **Critical** 9.0 to 10.0. The specification calls the bands optional and says they are meant to help organizations prioritize. This entry scores 10.0, the top, and the older version 2 scoring of the **same flaw** is 9.3: two scoring systems, two numbers, one bug.
5. **Weakness (CWE)** names the class of mistake (here, an expression-language injection flaw; CWE-917 is NVD's label, and the full name of the class is est.). It helps you recognize the pattern in other software.
6. **KEV** means CISA's *Known Exploited Vulnerabilities* catalog lists it: the flaw has been **exploited in the wild**, and CISA's page says organizations "should use the KEV catalog as an input to their vulnerability management prioritization framework" ([CISA KEV catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog), read 2026-10-22). The `due` date is, as I read the record's "required action" text, a deadline CISA set for US federal agencies (est.): a signal about urgency, not a rule for you.
7. **References** (103 of them on this record) point to the vendor's advisory, which is where the real fix instructions are.

### What the score does not tell you

A CVSS base score answers "how bad is this flaw, in the worst reasonable case, wherever it is found?" It does **not** answer these, and they are the questions that decide what you do on a Tuesday:

- **Do I run the affected software, in an affected version, in a way an attacker can reach?** The score is the same for a server on the internet and for a copy in a lab with no network.
- **Is anyone using it?** The FIRST v4.0 specification says its base value is combined with defaults that assume the highest severity for the Threat and Environmental groups. Threat metrics adjust for factors "such as the availability of proof-of-concept code or active exploitation" and Environmental metrics adjust for your own setup, but a published base score usually has neither (est.; NVD's record above lists a base vector only). Other signals fill the gap: the KEV catalog, and **EPSS**, a daily 0-to-1 estimate of the probability a CVE will be exploited in the next 30 days ([FIRST EPSS](https://www.first.org/epss/), read 2026-10-22).
- **How much does this machine matter?** A Critical on a throwaway lab droplet and a Medium on the machine holding your only copy of something are not equal.
- **Who scored it?** The v3.1 specification says base scores are "usually produced by the organization maintaining the vulnerable product, or a third party scoring on their behalf". The record above carries two v3.1 scores from different sources, here equal; the same flaw can be scored differently by different sources (est.).
- **Does a patch exist, and what does it break?** Not in the score at all.

The v4.0 specification itself describes CVSS as input to a risk process, not the process: consumers "may use CVSS information as input to an organizational vulnerability management process that also considers factors that are not part of CVSS" ([FIRST CVSS v4.0 specification](https://www.first.org/cvss/v4.0/specification-document), read 2026-10-22). Use the score to sort a list; use the other questions to decide. A fuller treatment of the words around it (exploit, zero-day, ransomware) belongs to a later foundations page; this one only teaches you to read the entry in front of you.

## Where this shows up in this project

- **Droplet backups are off in every row** of the approved cost table, on purpose: the droplets are rebuilt from code, and the approved phases hold nothing precious ([cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md)). The same page says that when stage 3 brings real data, "the bucket's versioning and a nightly copy off the account are the backups". Stage 3 is **planned, not built**: nothing like that is running.
- **The weekly plan is the only one priced**: [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json) holds `backups_fraction` 0.2 (retrieved 2026-10-19 from DigitalOcean's backups pricing page), and the cost gate refuses a daily or usage-based plan rather than guess a price. The doctl page you meet below says `--enable-backups` creates **daily** backups by default, which is why the gate asks for the plan to be named.
- **Code is the backup for the machines.** [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) is the other half of recovery here: lose a droplet, apply the stack, get an identical one. The state that is not in code (the Twingate account, the Doppler secrets, the Spacelift contexts) is on the [teardown checklist](Teardown-Checklist.md#2-what-survives-a-destroy) as "what survives a destroy", and it is what a real disaster plan has to cover separately.
- **Patching is automated for the host OS and the connector, and dated.** See [Droplet hardening: updates](Droplet-Hardening.md#updates). Nothing in the current stacks runs a container, so the container warning above is about stage 3 and about your own machines.
- [Threat model](Threat-Model.md) lists backups and patch cadence as things stage 3 brings into scope.

## Free path: a lab on your own computer

Everything in this section runs on your own computer and costs nothing; the lessons are free and will stay free. Every exercise follows four steps: **predict** (write down what you expect first), **do**, **check**, **undo**.

**Which track.** Bash and PowerShell commands are given for each exercise. The PowerShell lab uses a zip file instead of a tar file, because that is what PowerShell builds in; the idea and the checks are the same. All PowerShell here is **est.** (not run). On Windows with WSL 2 you can use the Bash version instead.

### Exercise 1: back up, lose it, restore it, with a stopwatch

**Predict.** Before you run anything, write down: (a) for 6 MB of data, will the restore be faster or slower than the backup, and by roughly how much? (b) If you change nothing but the amount of data, what do you expect to scale: the backup time, the restore time, both? (c) What is the one thing you can check after a restore that proves it worked, other than "no error"?

**Do (Bash).** Save this as `lab.sh` in an empty folder, outside any folder you care about, and make it executable. It builds 200 small text files and three binary files of random data, writes down a checksum of every file, and then does a backup, a pretend disaster and a timed restore on request.

```bash
#!/usr/bin/env bash
# lab.sh - back up and restore a throwaway folder, with a stopwatch.
# Everything lives under $BACKUP_LAB (default: ~/backup-lab). The script refuses to delete
# anything in a folder that does not carry its own marker file.
set -euo pipefail
LAB="${BACKUP_LAB:-$HOME/backup-lab}"
SIZE_MB="${SIZE_MB:-6}"

now()     { date +%s.%N; }
elapsed() { awk -v a="$1" -v b="$(now)" 'BEGIN { printf "  took %.2f seconds\n", b - a }'; }
guard()   { [ -f "$LAB/.backup-lab" ] || { echo "refusing: $LAB is not a backup-lab folder" >&2; exit 2; }; }

case "${1:-}" in
build)    # make the pretend important data, and write down what it should look like
  if [ -e "$LAB" ] && [ ! -f "$LAB/.backup-lab" ]; then echo "refusing: $LAB exists and is not ours" >&2; exit 2; fi
  mkdir -p "$LAB/data" "$LAB/backups"; touch "$LAB/.backup-lab"
  for i in $(seq 1 200); do printf 'note %s\nsecond line of note %s\n' "$i" "$i" > "$LAB/data/note-$i.txt"; done
  for i in 1 2 3; do head -c $((SIZE_MB * 1048576 / 3)) /dev/urandom > "$LAB/data/photo-$i.bin"; done
  (cd "$LAB" && find data -type f -print0 | sort -z | xargs -0 sha256sum > manifest.sha256)
  echo "built $(find "$LAB/data" -type f | wc -l) files, $(du -sh "$LAB/data" | cut -f1) in $LAB/data" ;;
backup)   # one full backup, one compressed archive, timed
  guard; start=$(now); stamp=$(date +%Y%m%d-%H%M%S)
  tar -czf "$LAB/backups/data-$stamp.tar.gz" -C "$LAB" data
  echo "wrote backups/data-$stamp.tar.gz ($(du -h "$LAB/backups/data-$stamp.tar.gz" | cut -f1))"; elapsed "$start" ;;
lose)     # the disaster: the source folder is gone
  guard; rm -rf "$LAB/data"; echo "data/ deleted" ;;
restore)  # unpack into a fresh folder and PROVE it matches the manifest; the clock covers both
  guard; archive="${2:?usage: lab.sh restore ARCHIVE}"
  rm -rf "$LAB/restore-test"; mkdir "$LAB/restore-test"; start=$(now)
  if ! tar -xzf "$archive" -C "$LAB/restore-test"; then echo "RESTORE FAILED: the archive would not unpack"; exit 1; fi
  if (cd "$LAB/restore-test" && sha256sum -c --quiet ../manifest.sha256); then
    echo "RESTORE OK: $(find "$LAB/restore-test/data" -type f | wc -l) files match the manifest"; elapsed "$start"
  else echo "RESTORE FAILED: files missing or different (see above)"; exit 1; fi ;;
corrupt)  # make a damaged copy of an archive (the original is untouched)
  guard; src="${2:?usage: lab.sh corrupt ARCHIVE}"; cp "$src" "$src.damaged"
  printf 'XXXXXXXXXXXXXXXX' | dd of="$src.damaged" bs=1 seek=4000 conv=notrunc status=none
  echo "wrote $src.damaged" ;;
*) echo "usage: lab.sh build | backup | lose | restore ARCHIVE | corrupt ARCHIVE" >&2; exit 2 ;;
esac
```

```bash
chmod +x lab.sh
./lab.sh build
./lab.sh backup
ls ~/backup-lab/backups
./lab.sh lose
ls ~/backup-lab
./lab.sh restore ~/backup-lab/backups/data-YYYYMMDD-HHMMSS.tar.gz   # use the file name `ls` printed
echo "exit code: $?"
```

**Do (PowerShell, est.).** Save this as `lab.ps1`. If PowerShell refuses to run it, `Set-ExecutionPolicy -Scope Process Bypass` allows scripts in this one window only.

```powershell
# lab.ps1 - back up and restore a throwaway folder, with a stopwatch (PowerShell version of lab.sh).
# Usage: .\lab.ps1 build | backup | lose | restore ARCHIVE | corrupt ARCHIVE
param(
  [Parameter(Mandatory)][ValidateSet('build','backup','lose','restore','corrupt')][string]$Action,
  [string]$Archive
)
$ErrorActionPreference = 'Stop'
$Lab    = if ($env:BACKUP_LAB) { $env:BACKUP_LAB } else { Join-Path $HOME 'backup-lab' }
$SizeMB = if ($env:SIZE_MB) { [int]$env:SIZE_MB } else { 6 }
$Marker = Join-Path $Lab '.backup-lab'
$Data   = Join-Path $Lab 'data'

function Assert-Lab { if (-not (Test-Path $Marker)) { throw "refusing: $Lab is not a backup-lab folder" } }
function Get-Manifest([string]$Root) {
  $base = (Resolve-Path $Root).Path
  Get-ChildItem -Path (Join-Path $base 'data') -Recurse -File | ForEach-Object {
    '{0}  {1}' -f $_.FullName.Substring($base.Length).TrimStart('\','/').Replace('\','/'),
                  (Get-FileHash -Algorithm SHA256 -Path $_.FullName).Hash.ToLower()
  } | Sort-Object
}
function Show-Elapsed($sw) { '  took {0:N2} seconds' -f $sw.Elapsed.TotalSeconds }

switch ($Action) {
  'build' {
    if ((Test-Path $Lab) -and -not (Test-Path $Marker)) { throw "refusing: $Lab exists and is not ours" }
    New-Item -ItemType Directory -Force $Data, (Join-Path $Lab 'backups') | Out-Null
    New-Item -ItemType File -Force $Marker | Out-Null
    1..200 | ForEach-Object { Set-Content -Path (Join-Path $Data "note-$_.txt") -Value "note $_", "second line of note $_" }
    $rng = [System.Random]::new()      # filler bytes only; nothing here is secret
    1..3 | ForEach-Object {
      $b = New-Object byte[] ([int]($SizeMB * 1MB / 3)); $rng.NextBytes($b)
      [IO.File]::WriteAllBytes((Join-Path $Data "photo-$_.bin"), $b)
    }
    Get-Manifest $Lab | Set-Content (Join-Path $Lab 'manifest.txt')
    'built {0} files in {1}' -f (Get-ChildItem -Recurse -File $Data).Count, $Data
  }
  'backup' {
    Assert-Lab; $sw = [Diagnostics.Stopwatch]::StartNew()
    $zip = Join-Path $Lab ('backups\data-{0}.zip' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
    Compress-Archive -Path $Data -DestinationPath $zip
    'wrote {0} ({1:N1} MB)' -f $zip, ((Get-Item $zip).Length / 1MB); Show-Elapsed $sw
  }
  'lose' { Assert-Lab; Remove-Item -Recurse -Force $Data; 'data\ deleted' }
  'restore' {
    Assert-Lab; if (-not $Archive) { throw 'usage: .\lab.ps1 restore ARCHIVE' }
    $rt = Join-Path $Lab 'restore-test'
    if (Test-Path $rt) { Remove-Item -Recurse -Force $rt }
    New-Item -ItemType Directory $rt | Out-Null
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try { Expand-Archive -Path $Archive -DestinationPath $rt }
    catch { Write-Host "RESTORE FAILED: the archive would not unpack ($($_.Exception.Message))"; exit 1 }
    $diff = Compare-Object (Get-Content (Join-Path $Lab 'manifest.txt')) (Get-Manifest $rt)
    if ($diff) { $diff | Format-Table | Out-String | Write-Host; Write-Host 'RESTORE FAILED: files missing or different'; exit 1 }
    'RESTORE OK: {0} files match the manifest' -f (Get-ChildItem -Recurse -File (Join-Path $rt 'data')).Count
    Show-Elapsed $sw
  }
  'corrupt' {
    Assert-Lab; if (-not $Archive) { throw 'usage: .\lab.ps1 corrupt ARCHIVE' }
    Copy-Item $Archive "$Archive.damaged"
    $fs = [IO.File]::Open("$Archive.damaged", 'Open', 'Write'); [void]$fs.Seek(4000, 'Begin')
    $x = [Text.Encoding]::ASCII.GetBytes('XXXXXXXXXXXXXXXX'); $fs.Write($x, 0, $x.Length); $fs.Close()
    "wrote $Archive.damaged"
  }
}
```

```powershell
.\lab.ps1 build
.\lab.ps1 backup
Get-ChildItem $HOME\backup-lab\backups
.\lab.ps1 lose
.\lab.ps1 restore $HOME\backup-lab\backups\data-YYYYMMDD-HHMMSS.zip   # use the file name Get-ChildItem printed
$LASTEXITCODE
```

**Check.** On 2026-10-22 the Bash run printed (trimmed; the folder path is shortened and the numbers vary):

```text
built 203 files, 6.8M in .../lab/data
wrote backups/data-20261022-105733.tar.gz (6.1M)
  took 0.17 seconds
data/ deleted
RESTORE OK: 203 files match the manifest
  took 0.04 seconds
```

The restore was several times faster than the backup, because compressing is the slow half and unpacking is the quick one (the exact ratio depends on your machine). The check that proved the restore is the last line before the time: **every file's SHA-256 matched the list written when the data was built**. "No error" only means `tar` was happy. Also notice what was **not** timed: finding the file name, deciding to restore, getting onto the machine. Your RTO is all of those added to this number.

**Undo.** Delete the lab: `rm -rf ~/backup-lab` (Bash) or `Remove-Item -Recurse -Force $HOME\backup-lab` (PowerShell). That is the only folder either script made. The script's own `lose` step already removed `data/`; the `.backup-lab` marker file is what let the script refuse to touch anything else.

### Exercise 2: what makes the restore slow

**Predict.** If you make the data ten times bigger, what happens to the backup time and the restore time? Would a real service's RTO change by the same factor?

**Do (Bash).** Start from a fresh lab and set the size with an environment variable:

```bash
rm -rf ~/backup-lab
SIZE_MB=60 ./lab.sh build
./lab.sh backup
./lab.sh lose
./lab.sh restore ~/backup-lab/backups/data-YYYYMMDD-HHMMSS.tar.gz
```

**Do (PowerShell, est.).**

```powershell
Remove-Item -Recurse -Force $HOME\backup-lab
$env:SIZE_MB = 60
.\lab.ps1 build; .\lab.ps1 backup; .\lab.ps1 lose
.\lab.ps1 restore $HOME\backup-lab\backups\data-YYYYMMDD-HHMMSS.zip
Remove-Item Env:\SIZE_MB
```

**Check.** The Bash run on 2026-10-22 gave a 61 MB archive, a backup of 2.22 seconds and a restore plus verification of 0.42 seconds. Both grew with the data (roughly tenfold for ten times the data here; a small run is noisy). Your numbers will differ, and an ordinary desktop disk is far faster than a cloud droplet's disk reached over a network (est.). The lesson is the shape: **recovery time grows with the amount of data**, so an RTO that was true for last year's data may not be true for this year's. A cloud provider's documentation gives the same shape for its own backups: creating one "takes about 1 to 3 minutes per GB of used disk space on the Droplet" ([DigitalOcean support page](https://docs.digitalocean.com/support/how-long-will-my-backup-or-snapshot-take-to-complete/), read 2026-10-22), so a 10 GB droplet is 10 to 30 minutes, and the page says nothing about restoring.

**Undo.** `rm -rf ~/backup-lab` (or `Remove-Item -Recurse -Force $HOME\backup-lab`).

### Exercise 3: how far behind are you? (patches pending on your own machine)

This one only **reads** your machine's package state. It installs nothing.

**Predict.** How many packages on your own computer have an update waiting? Which one would you want first?

**Do (Bash).** On Debian or Ubuntu (the package lists are only as fresh as the last `apt update`, which needs `sudo` and which you do not have to run for this exercise):

```bash
apt list --upgradable 2>/dev/null | tail -n +2 | wc -l
apt list --upgradable 2>/dev/null | head -5
```

On a Red Hat family machine (est.): `dnf check-update | head` (it exits with code 100 when updates are available, which is not an error). On macOS (est.): `softwareupdate --list`.

**Do (PowerShell, est.).** On Windows 10 or 11 with the Windows package manager installed:

```powershell
winget upgrade
```

For the operating system's own updates, open Settings, then Windows Update, and read the list there (the settings page is the dependable view; the `Get-HotFix` cmdlet lists what is already installed, not what is waiting, est.).

**Check.** On the author's machine on 2026-10-22 the first command printed `20`: twenty packages were waiting, from a package list that had not been refreshed that day. Whatever your number is, it is a measurement of how far your cadence is from your intention. Ask three more questions of each name on the list: is it a security fix or a feature change, does it need a reboot to take effect, and who decides when it goes in? The answers are your patch cadence, written or not.

**Undo.** Nothing changed.

### Exercise 4: read a CVE yourself

**Predict.** Using the vector string `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H` and the table above, what would you expect the band to be? What would change if `AV:N` became `AV:L` (local) and `PR:N` became `PR:L` (low privileges)? Write down whether the score goes up or down and why, then check your guess against FIRST's calculator.

**Do (Bash).** This asks NVD's public API for one record (a read-only request; the service limits how fast you may ask, so do not loop it). Save the reader as `read-cve.py`:

```python
# read-cve.py FILE : print the parts of an NVD API 2.0 record that matter for a first read.
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    doc = json.load(fh)
if not doc.get("vulnerabilities"):
    sys.exit("no such CVE in this response")
cve = doc["vulnerabilities"][0]["cve"]
print("id          :", cve["id"], "|", cve.get("vulnStatus"))
print("published   :", cve["published"], " last modified:", cve["lastModified"])
text = next((d["value"] for d in cve["descriptions"] if d["lang"] == "en"), "")
print("description :", text[:230] + ("..." if len(text) > 230 else ""))
for family, entries in cve.get("metrics", {}).items():
    for m in entries:
        data = m.get("cvssData")
        if not data:
            continue
        print(f"score       : {family} from {m.get('source')} ({m.get('type')}): "
              f"{data['baseScore']} {data.get('baseSeverity', m.get('baseSeverity', ''))}  {data['vectorString']}")
for w in cve.get("weaknesses", []):
    print("weakness    :", w["source"], [d["value"] for d in w["description"]])
if "cisaExploitAdd" in cve:
    print("KEV         : added", cve["cisaExploitAdd"], "due", cve.get("cisaActionDue"), "-", cve.get("cisaVulnerabilityName"))
else:
    print("KEV         : not in the CISA catalog as of this record")
print("references  :", len(cve.get("references", [])))
```

```bash
curl -s "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2021-44228" -o cve.json
python3 -I read-cve.py cve.json
```

**Do (PowerShell, est.).**

```powershell
$r = Invoke-RestMethod "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2021-44228"
$c = $r.vulnerabilities[0].cve
$c.id; $c.vulnStatus; $c.published; $c.lastModified
($c.descriptions | Where-Object lang -eq 'en').value
$c.metrics.cvssMetricV31 | ForEach-Object { '{0} {1} {2} {3}' -f $_.source, $_.cvssData.baseScore, $_.cvssData.baseSeverity, $_.cvssData.vectorString }
$c.cisaExploitAdd
```

**Check.** The Bash output on 2026-10-22 is the block in "A worked entry" above, three score lines included (two for version 3.1, one for the older version 2). Then answer, from the entry alone: which versions are affected; which line tells you the flaw was actually used by attackers; what the score would be for you if you do not run Log4j (the number does not change; your exposure does). Finally, open FIRST's [v3.1 calculator](https://www.first.org/cvss/calculator/3.1) in your browser, enter the vector yourself, and compare with your prediction.

**Undo.** `rm cve.json read-cve.py` (or `Remove-Item`). Nothing else changed.

### Exercise 5: a patch plan on paper

**Predict.** Which of your own devices has the longest gap between "an update exists" and "it is installed"? Which one would hurt most if it were compromised?

**Do (any shell, or a notebook).** Make a table with one row for each of five devices or services you own or manage: a laptop, a phone, a home router, one server or Raspberry Pi if you have one, one cloud account. For each write: **who updates it** (you, the vendor automatically, nobody), **how often**, **how you would know** it had failed, **whether it needs a reboot** and **when it may**, and **what you would do the day a flaw in it is being exploited** (your emergency path, in one sentence).

**Check.** Count the empty cells. Every "nobody" and every "I would not know" is a finding. If a row says "automatic", write which tool and which layer from the table above it covers: the router's firmware is not covered by your laptop's updater, and a container on the server is not covered by the server's.

**Undo.** Keep the table; it is the start of a real asset list.

### Exercise 6: how old is the image you are running? (only if you use Docker)

**Predict.** For each container you run, when was the image it came from built? Is the tag a moving one such as `latest` or a version number?

**Do (Bash and PowerShell, est.; not run).** Both are read-only:

```bash
docker image ls --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedSince}}"
docker image inspect --format "{{.Created}}" IMAGE:TAG
```

```powershell
docker image ls --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedSince}}"
docker image inspect --format "{{.Created}}" IMAGE:TAG
```

**Check.** `CreatedSince` is when the **image was built**, not when you pulled it. A twelve-month-old base image means twelve months of fixes your host's `unattended-upgrades` never saw. Do **not** fix it in this exercise unless you know what the container holds: updating means pulling or rebuilding and then recreating the container, which can lose data kept inside it. If you have no Docker, skip this; the point is made in the table above.

**Undo.** Nothing changed.

## Optional: backups on a real cloud droplet (your own account)

This path takes a droplet with the provider's own backup option on, makes a change **after** a backup exists, restores the droplet from that backup, and checks which change survived. It is optional: the free path teaches every idea, and this one adds two things the lab cannot: a backup someone else's system makes for you, and the experience that a weekly backup means **you lose up to a week**. It uses **your own** cloud account and **your own** provider bill. Read the cost and the teardown first.

> **Status of this path: written from DigitalOcean's documentation and API description, never run.** The doctl flag values for the backup plan, weekday and hour come from DigitalOcean's public API description on GitHub (see the claims register); the doctl reference page lists the flags but not their allowed values. Whether the first weekly backup appears inside the window you choose, and how long the restore takes, are **est.** Run it expecting to fix something.

### Cost and teardown (read first)

- **Cost.** One droplet of size `s-1vcpu-1gb`, which [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json) (retrieved 2026-10-21) lists at **$6 a month**. The weekly backup plan adds **20 percent** of the droplet's monthly cost per the same file (`backups_fraction` 0.2, from DigitalOcean's backups pricing page, retrieved 2026-10-19 per the file, and shown again on that page on 2026-10-22 as "Weekly 20.0% of the Droplet's cost per month", last verified 9 March 2026). That is $6 times 0.2, **$1.20 a month**, so **up to $7.20 a month at list price if you left it running a full month** (est. arithmetic; the figures are the file's). The same pricing page says each successful backup is "charged at a percentage of the Droplet's total cost that month" and that you "may be charged less than the full monthly cost" if you destroy a droplet less than a month old. A droplet is billed per second ([DigitalOcean droplet pricing](https://docs.digitalocean.com/products/droplets/details/pricing/), read 2026-10-21) and a powered-off droplet is still billed; **destroying** it ends billing. I did not read an hourly rate, so I give no per-hour figure, and I did not find how a backup that outlives a destroyed droplet is billed: check your billing page again the next day and again after four weeks.
- **Never leave it running.** Set a calendar reminder for tomorrow.
- **This droplet is not part of the project's stacks**, so the project's cost gate never sees it. It is yours to track.
- **Backups outlive the droplet.** DigitalOcean's destroy page says destroying a droplet "does not destroy its automated backups"; they "remain for four weeks after creation and then expire" ([destroy a droplet](https://docs.digitalocean.com/products/droplets/how-to/destroy/), read 2026-10-22). I found no documented way to delete one sooner, so expect it to show in your image list until it expires.
- **Teardown** (listed again at the end with the proof):

```bash
doctl compute droplet delete backup-lab --force
doctl compute firewall list --format ID,Name        # note the backup-lab id
doctl compute firewall delete FIREWALL_ID --force
doctl compute tag delete backup-lab --force
```

- **Targets.** The only machine you touch is the droplet you create here.
- **Data rules.** No real data goes on it. The two marker files you write are harmless text.

### The design

```text
  your laptop --ssh (only from your /32)--> backup-lab droplet (weekly backups on, firewall: inbound 22 from you, nothing else)
```

The firewall comes first, so the droplet is never open to the internet, even for a minute. It has no outbound rules, which means the droplet cannot start connections of its own; replies to your SSH session still work because the firewall is stateful. That also means you cannot run `apt` on it, which this lab does not need.

### Steps

Placeholders: replace `203.0.113.7` with your own current public address (a documentation address, not yours). Behind carrier-grade NAT your visible address is shared with other households, so a `/32` is wider than it looks; if you are behind CGNAT, do not use this path from that connection.

The backup window is a **four-hour period** in which the droplet starts a backup, set by weekday and a start hour from `0, 4, 8, 12, 16, 20`. Pick a window that **starts later today** so the first backup comes within hours rather than next week. The time zone the hour is read in is not stated on the pages I read (probably UTC, est.), so look at the **Backups** tab of the droplet in the console, which shows your actual window, and be ready for it to land a day later than you hoped.

```bash
export REGION=tor1 SIZE=s-1vcpu-1gb IMAGE=ubuntu-24-04-x64
export MY_IP=203.0.113.7
doctl compute ssh-key list --format ID,Name,FingerPrint      # pick the key you use; note its ID
export KEY_ID=YOUR_KEY_ID

# 1. Tag and firewall BEFORE the droplet.
doctl compute tag create backup-lab
doctl compute firewall create --name backup-lab --tag-names backup-lab \
  --inbound-rules "protocol:tcp,ports:22,address:${MY_IP}/32"

# 2. The droplet, with the WEEKLY plan named (the doctl default is daily, which costs 30 percent).
doctl compute droplet create backup-lab --region "$REGION" --size "$SIZE" --image "$IMAGE" \
  --ssh-keys "$KEY_ID" --tag-names backup-lab --enable-backups \
  --backup-policy-plan weekly --backup-policy-weekday THU --backup-policy-hour 20 --wait

# 3. Its address and id.
export DROPLET_IP=$(doctl compute droplet get backup-lab --format PublicIPv4 --no-header)
export DROPLET_ID=$(doctl compute droplet get backup-lab --format ID --no-header)
```

In PowerShell write `$env:REGION = "tor1"` style assignments, put `$DROPLET_IP = (doctl compute droplet get backup-lab --format PublicIPv4 --no-header)` for the addresses, and write the multi-line commands on one line (or end each line with a backtick); the `doctl` flags are identical (est.). Change `THU` and `20` to a window that starts later today in your reading of the console.

**Build: write the "before" marker, then wait for a backup.** The first connection asks you to accept the droplet's host key; for a machine you just made, accepting is reasonable.

```bash
ssh root@"$DROPLET_IP" 'echo "written before the backup" > /root/marker-a; sync'
doctl compute droplet backups "$DROPLET_ID" --format ID,Name,Created
```

The second command lists the droplet's backup images. It prints nothing useful until the first backup has finished; run it now and then (a few times a day, not in a loop). When a row appears, note its ID: `export BACKUP_ID=THE_ID`. DigitalOcean says creating a backup takes about 1 to 3 minutes per GB of used disk, so it finishes some time after its window opens (est. for this small droplet).

**Break: make a change the backup does not have, then restore.** Write the "after" marker, then restore the droplet from the backup and time it:

```bash
ssh root@"$DROPLET_IP" 'echo "written AFTER the backup" > /root/marker-b; sync; ls /root'
time doctl compute droplet-action restore "$DROPLET_ID" --image-id "$BACKUP_ID" --wait
```

DigitalOcean's page says restoring replaces the droplet with one based on the backup image, and "you lose any changes on the Droplet from after the backup was taken"; the doctl reference says the operation leaves embedded SSH keys intact ([create or restore from backups](https://docs.digitalocean.com/products/backups/how-to/create-and-restore/), [doctl droplet-action restore](https://docs.digitalocean.com/reference/doctl/reference/compute/droplet-action/restore/), read 2026-10-22).

**Detect: check what survived.**

```bash
ssh root@"$DROPLET_IP" 'ls /root; cat /root/marker-a'
```

Expect (est.) `marker-a` present and `marker-b` **missing**. If your SSH client warns that the droplet's host key changed, stop and read the warning rather than overriding it; a restore from the droplet's own backup should bring the same host key back (est.), so a mismatch is a thing to understand first. The `time` figure is your measured restore time for a nearly empty droplet. It is not an RTO: the real one adds everything from Exercise 1's "what was not timed".

The missing `marker-b` is your **RPO, felt**: the work you did after the last backup is gone, and with a weekly plan that gap can be a week.

**Now tear down**, using the commands at the top of this section.

### Prove it is gone

```bash
doctl compute droplet list
doctl compute firewall list
doctl compute tag list
doctl compute image list --format ID,Name,Type
```

Read-only; nothing named `backup-lab` should remain in the first three. The image list may still show the droplet's backup until it expires, as the destroy page above says. Billing data lags: look at the billing page again tomorrow (the habit in the [teardown checklist](Teardown-Checklist.md#3-prove-zero-billable-resources)). Remove the droplet's entry from `~/.ssh/known_hosts` if you want a tidy file.

## Build, break, detect, evade, defend (the local loop)

The same loop on the free lab, with no cloud account. Start from a fresh `rm -rf ~/backup-lab` and `./lab.sh build`.

**Build: a backup on a schedule.** A backup you must remember to take is a backup you will skip. On Linux and macOS a scheduled job runs a command at fixed times; this line (shown, not installed, because it depends on where you saved the script) would run the backup at 02:17 every night:

```text
17 2 * * * BACKUP_LAB=/home/YOU/backup-lab /home/YOU/lab.sh backup >> /home/YOU/backup-lab/backup.log 2>&1
```

On Windows the equivalent is a scheduled task (Task Scheduler, or the `Register-ScheduledTask` cmdlet, est.). Notice what the line cannot do: it can write `exit 0` to a log nobody reads. Build the schedule **and** a place where a failure becomes visible.

**Break: lose the source.** Run `./lab.sh backup`, then `./lab.sh lose`, then restore as in Exercise 1. You just did the loss most people actually suffer: an accidental delete, a bad edit, a disk that gave up. The RPO you felt is the age of the newest backup.

Now a question to answer in writing before you read on. Which one event, from this list, destroys **both** the data and the backup in this lab, and which do not? (a) `lose`. (b) The laptop's disk fails. (c) The laptop is stolen. (d) Malware running as you. (e) A fire in the room. (f) You run `rm -rf` on the wrong folder.

<details>
<summary>The answers</summary>

(a) No: that is what the backup is for. (b), (c) and (e) take both: the backup is in a folder on the same disk in the same room, so it is **one failure domain**, and the lab has one copy of the data, not three. (d) and (f) take both if they reach the lab folder: the backup is reachable by the same account that can delete the data. This lab teaches the restore; it does **not** meet 3-2-1, and the Defend step below is what moves it a few steps closer.

</details>

**Detect: a restore test that fails on a bad copy.** Two failures, both on a throwaway copy:

```bash
./lab.sh build
./lab.sh backup
ARCH=$(ls -t ~/backup-lab/backups/*.tar.gz | head -1)
./lab.sh corrupt "$ARCH"
./lab.sh restore "$ARCH.damaged"; echo "exit code: $?"
```

On 2026-10-22 the second command printed (trimmed):

```text
gzip: stdin: invalid compressed data--crc error
tar: Child returned status 1
tar: Error is not recoverable: exiting now
RESTORE FAILED: the archive would not unpack
exit code: 1
```

A damaged archive was caught because the restore **was run**. The second failure is subtler: a backup that is intact but **incomplete**. Delete one file from the source and take a new backup (wait a second first, so the new archive has its own name), then restore it:

```bash
rm ~/backup-lab/data/note-1.txt
sleep 1
./lab.sh backup
./lab.sh restore "$(ls -t ~/backup-lab/backups/*.tar.gz | head -1)"; echo "exit code: $?"
```

Output (trimmed): `data/note-1.txt: FAILED open or read`, then `RESTORE FAILED: files missing or different (see above)` and exit code 1. The archive is perfectly good; it faithfully contains a folder that was already missing a file. Only a comparison against a record written **earlier** can say so. That is why the manifest exists, and why real systems keep one (file counts, sizes, checksums, a database row count, a known test record) and alert when a backup, or a restore test, does not match.

For PowerShell, run `.\lab.ps1 corrupt` on the newest zip and restore the `.damaged` file; either `Expand-Archive` stops, or it unpacks and the manifest comparison names the files, and both are `RESTORE FAILED` (est.). Then schedule the restore test too. A restore test that runs on a calendar and **pages someone when it fails** is the cheapest control on this page.

**Evade, in words.** Think like a ransomware crew, and keep it at the level of understanding. After they get in with a stolen password, the first thing a well-run crew does is look for your backups, because a backup is the one thing that lets you say no. [CISA's StopRansomware guide](https://www.cisa.gov/stopransomware/ransomware-guide) (read 2026-10-22) says to "maintain offline, encrypted backups of critical data" and gives the reason: "many ransomware variants attempt to find and subsequently delete or encrypt accessible backups to make restoration impossible unless the ransom is paid". So the attack on a backup is not clever; it is **reach**:

- The backup is reachable by the account that was just taken over (a mounted share, a cloud folder the same login can edit, a backup server joined to the same directory).
- The tool that writes backups also holds credentials that can **delete** them.
- The attacker waits. If they are inside for longer than your retention, every copy you hold already contains the damage. A weekly backup kept for four weeks protects against an attacker who has been present for under four weeks, and that is all (est.; the retention is DigitalOcean's, and the principle is that retention must be longer than the time an intruder can go unnoticed).
- They copy your data out first and threaten to publish it. A backup restores your files; it does **not** un-publish them. That is a separate defense (not being broken into, [detecting it](Detection-and-Monitoring-Wazuh-and-the-Landscape.md), and having decided in advance what you will do).

You have just learned why "we have backups" is a claim to check, not an answer.

**Defend: a copy that the same mistake cannot reach, and a drill.** Put a second copy somewhere else, check it is identical, and make it hard to change by accident:

```bash
mkdir -p ~/backup-lab/elsewhere
ARCH=$(ls -t ~/backup-lab/backups/*.tar.gz | head -1)
cp "$ARCH" ~/backup-lab/elsewhere/
sha256sum "$ARCH" ~/backup-lab/elsewhere/"$(basename "$ARCH")"
chmod a-w ~/backup-lab/elsewhere/"$(basename "$ARCH")"
```

The two checksums match: that is a verified second copy. `chmod a-w` stops an accident; it does **not** stop an attacker running as you, who can change the permission back. Be honest about that, because the real protections are different in kind: a copy on a **disconnected drive** that is not plugged in when malware runs; a copy in a service with a **write-only credential** (the machine can add backups but not delete them); or **immutable** (also called WORM, write once read many) storage that refuses changes for a set time even to the account owner. DigitalOcean's backups are in the same datacenter and the same account as the droplet (above), so on their own they are one copy, convenient and not a 3-2-1 plan. The defenses in order of what they buy: **a second copy outside the reach of the first copy's credentials; retention longer than a plausible time to detect; a restore test on a calendar that alerts when it fails; the keys needed to open the backup stored separately (and themselves restorable); and a written, practiced path for "it is 3 a.m. and the data is gone".**

**Undo.** `rm -rf ~/backup-lab`. Remove any cron line you added.

### Flip the board

You built and attacked the backup. Now do the other two jobs.

**The reviewer.** A colleague hands you this plan and asks "do we have backups?" Find at least five problems without running anything.

```text
Plan for the order-tracking server (one VM, holds the only copy of the order database)
- Backup: nightly at 02:00, a script copies /srv/orders to /srv/orders/backups on the same disk.
- Retention: the last 3 nights.
- The script writes "done" to a log; its exit code is not checked.
- The backup user is the server's admin account, with the same password as the admin console.
- Files are copied while the database is running.
- The restore has not been tried: "tar is reliable".
- Patching: security updates are applied "when someone remembers".
```

<details>
<summary>What to find</summary>

1. The backup is **in the thing it protects**: the same folder tree, the same disk. A disk failure, a deletion of `/srv/orders`, or malware as that account takes data and backup together (one failure domain; no second or offsite copy, so not 3-2-1).
2. **Retention of three nights** is shorter than any plausible time to notice a problem (a bad deployment found after a long weekend leaves no good copy).
3. **Nobody is told when it fails.** A log that says "done" and an exit code nobody reads mean a broken job runs silently.
4. **The backup credential is the admin credential**, reused: whoever takes the server takes the backups, and an attacker with that password can delete them. A backup credential should be able to **add** copies, not remove them.
5. **A running database is copied file by file.** That can produce a copy the database will not open (DigitalOcean's own documentation says its crash-consistent backups miss anything in memory and suit low-write systems). Use the database's own dump or backup tool.
6. **No restore test.** "Tar is reliable" describes the tool, not the copy. Time a restore; compare against known good.
7. **No RPO or RTO is written down**, so nobody can say whether nightly is enough.
8. **Patching is "when someone remembers"**: no cadence, no owner, no emergency path, no way to know how far behind it is (Exercise 3 in one line).
9. Smaller: no encryption stated, and no statement of where the key lives.

</details>

**The responder.** It is 03:00 and a file server shows every document renamed and unreadable. You hold the plan above. Write down, in order, the questions you ask before you touch anything: what is the last backup, when was it taken, is it clean, who can restore it and how fast, **and what else did the attacker take**. Then say which question the plan can answer today and which it cannot. (A good answer starts with isolating the machine and finding the time the damage began, **before** restoring over anything: restoring first can destroy the evidence and re-infect the restored machine.)

**The patch version.** You are handed 400 CVEs from a scanner, every one "High" or "Critical". Using only what this page taught, name four questions that sort them (Do we run the software? Is it reachable? Is it in the KEV catalog or high on EPSS? How important is the machine?), and say why sorting by CVSS alone sends you to the wrong place first. Defenders who read a vulnerability list the way an attacker does fix the exploited one first; attackers who read the same list know which unpatched machines are worth the effort. Do both, in that order.

## Checkpoint

- Say, in one sentence each, the difference between a snapshot, a backup and a replica, and which one protects against someone deleting the wrong folder.
- A nightly backup runs at 01:00. A server fails at 23:00. How much work can be lost at worst, and what is that number called?
- What is the 3-2-1 rule, and name one way a plan can follow it and still fail.
- Your restore "succeeded" with no error. Name two further checks before you call it a success.
- Why does `unattended-upgrades` not keep a Docker container patched?
- Read this vector: `AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N`. In plain words, would you expect a high or a low score, and why?
- A scanner reports a Critical CVSS score in a library you do not use. What does it tell you about your risk?

Answers are in the sections above. (For the vector: the attacker must already be on the machine, find a hard-to-meet condition, hold high privileges and rely on a user's action, and the effect is a small leak of information; the score is low. For the library: nothing, until you find out whether you run it.)

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| "I have snapshots, so I am backed up" | A snapshot on the same storage, in the same account, is one copy | Where the copy lives, who can delete it, and whether you have restored it. |
| The restore command ran with no error and the data is wrong | Nothing compared the result to a known good record | A manifest or checksum list written before the disaster. |
| A new backup silently replaced an older one | The script names the file by time to the second, so two runs in one second overwrite each other; or the retention is too short | Name files so they cannot collide, and keep more than you think you need. |
| Weekly backups on, still lost a day of work | The plan's RPO is a week; the window is four hours | RPO from the schedule, not from the product name. |
| `unattended-upgrades` is on and a library is still old | The library is in a container image, an extra repository, or your own application | Which layer, from the table, owns that file. |
| A Critical on the scanner is ignored, then exploited | It was not near the top of anyone's list, and nobody checked KEV | Sort by exploited first, exposed second, score third. |
| The restore only works on the machine that made the backup | The key or a credential lived on that machine | Restore on a different, empty machine; store keys apart. |
| `dnf-automatic` is installed and nothing installs | `apply_updates` defaults to False; the notify-only timer may be the one enabled | The timer you enabled and the setting it reads. |

## Claims register

All read-only requests; retrieved **2026-10-22** unless stated. "Observed" means I ran it that day.

| Claim | Source | Status |
|---|---|---|
| 3-2-1: three copies (one primary, two backups), two media types, one copy offsite | [CISA / US-CERT, *Data Backup Options*](https://www.cisa.gov/sites/default/files/publications/data_backup_options.pdf) (PDF; its publication year is not printed in the text I read; the paper cites sources accessed in 2012, so the date is **est.**) | Read |
| Ransomware commonly targets accessible backups; keep offline, encrypted backups; test them | [CISA StopRansomware guide](https://www.cisa.gov/stopransomware/ransomware-guide), September 2023 edition per the page | Read the backup passages |
| DigitalOcean backups: made by snapshotting the live droplet, copying it off-disk, deleting the snapshot; crash-consistent; frequencies from weekly to every 4 hours; a four-hour backup window; stored in the same datacenter; exclude volumes | [Backups features](https://docs.digitalocean.com/products/backups/details/features/) (last verified 9 Dec 2025) | Read |
| Backups are not encrypted at rest but not externally accessible; suited to low-write systems; memory and cache contents are not saved; copy-on-write slows writes during a backup | [Backups limits](https://docs.digitalocean.com/products/backups/details/limits/) (last verified 17 Jun 2025) | Read |
| Weekly basic plan 20.0 percent and daily 30.0 percent of the droplet's monthly cost; each successful backup is charged at a percentage of that month's cost; usage-based plans are priced per GiB | [Backups pricing](https://docs.digitalocean.com/products/backups/details/pricing/) (last verified 9 Mar 2026) | Read; the repository file below records the same fraction |
| `s-1vcpu-1gb` is $6 a month; `backups_fraction` is 0.2 and verified; retrieved 2026-10-21 and 2026-10-19 | [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json), [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) | Read in this repository |
| Droplets are billed per second; a powered-off droplet is still billed; destroying ends billing | [Droplet pricing](https://docs.digitalocean.com/products/droplets/details/pricing/) | Read on 2026-10-21 (not re-read) |
| Weekly backups are kept for four weeks, daily for seven days; snapshots are kept until deleted; backups and snapshots are both disk images; converting a backup to a snapshot applies snapshot pricing | [Convert backups to snapshots](https://docs.digitalocean.com/products/backups/how-to/convert-to-snapshot/) (last verified 13 Jul 2026), [FAQ: destroy droplets, keep backups](https://docs.digitalocean.com/support/how-can-i-destroy-my-droplets-while-maintaining-my-backups/) | Read |
| Destroying a droplet does not destroy its automated backups; they expire four weeks after creation | [Destroy a droplet](https://docs.digitalocean.com/products/droplets/how-to/destroy/) | Read the passage; whether a retained backup of a destroyed droplet is billed: **not found** |
| Disabling backups keeps existing backups until their scheduled deletion | [Disable backups](https://docs.digitalocean.com/products/backups/how-to/disable/) (last verified 13 Jul 2026) | Read |
| Creating a snapshot or backup takes about 1 to 3 minutes per GB of used disk; backups cannot be downloaded | [Backup time FAQ](https://docs.digitalocean.com/support/how-long-will-my-backup-or-snapshot-take-to-complete/) (last verified 13 Jul 2026) | Read; restore time: **not found** |
| Restoring replaces the droplet with one based on the backup and loses changes since; `doctl compute droplet-action restore DROPLET_ID --image-id ID`; `doctl compute droplet backups DROPLET_ID` lists backup images | [Create or restore from backups](https://docs.digitalocean.com/products/backups/how-to/create-and-restore/), [doctl restore](https://docs.digitalocean.com/reference/doctl/reference/compute/droplet-action/restore/), [doctl droplet backups](https://docs.digitalocean.com/reference/doctl/reference/compute/droplet/backups/) | Read; never run |
| `doctl compute droplet create` has `--enable-backups` (daily by default) and `--backup-policy-plan`, `--backup-policy-weekday`, `--backup-policy-hour` | [doctl droplet create](https://docs.digitalocean.com/reference/doctl/reference/compute/droplet/create/) (generated 15 Oct 2026, doctl v2.0.0 per the page) | Flags read; the allowed values are **not** on that page |
| Backup plan `daily` or `weekly`; weekday `SUN` to `SAT`; start hour one of `0, 4, 8, 12, 16, 20` | DigitalOcean's [public OpenAPI description](https://raw.githubusercontent.com/digitalocean/openapi/main/specification/resources/droplets/models/droplet_backup_policy.yml) (GitHub, `main`) | Read; whether `doctl` accepts the same strings is **est.** |
| Time zone of the backup window hour | none | Not read; **est.** |
| Ubuntu applies security updates through `unattended-upgrades`, installed by default; origins are listed in `50unattended-upgrades`; a newly added repository is not considered | [Ubuntu Server: automatic updates](https://documentation.ubuntu.com/server/how-to/software/automatic-updates/) | Read |
| `dnf-automatic`: `apply_updates` default False; runs from systemd timers | [DNF Automatic](https://dnf.readthedocs.io/en/latest/automatic.html) | Read |
| Patch Gremlin: update notifications on top of `unattended-upgrades` and `dnf-automatic` for Debian and RHEL families, to chat and push services | [Patch Gremlin README](https://github.com/ChiefGyk3D/Patch-Gremlin) | README read; code not read |
| Docker images are immutable snapshots of a build; rebuild regularly; `docker build --pull` checks for a newer base | [Docker build best practices](https://docs.docker.com/build/building/best-practices/) | Read |
| A running container keeps the image it started from; Dependabot and Renovate open pull requests for image tags | General knowledge | **est.**; not read here |
| Routine, emergency, emergency-mitigation and unpatchable-asset scenarios; routine patching "often postponed and neglected" | [NIST SP 800-40r4](https://doi.org/10.6028/NIST.SP.800-40r4) (April 2022; PDF read) | Read |
| "Maintenance window" meaning | General usage | **est.**; not in a standard I read |
| CVSS v3.1 and v4.0: bands None 0.0, Low 0.1-3.9, Medium 4.0-6.9, High 7.0-8.9, Critical 9.0-10.0, and the bands are optional; Base, Temporal and Environmental (v3.1) or Base, Threat, Environmental and Supplemental (v4.0) groups; v3.1 base scores usually produced by the vendor or a third party; v4.0 base score assumes the highest severity for Threat and Environmental; CVSS as input to a risk process | [CVSS v3.1](https://www.first.org/cvss/v3.1/specification-document), [CVSS v4.0 (document version 1.2)](https://www.first.org/cvss/v4.0/specification-document) | Read the passages cited; metric meanings read for AV, AC, PR, UI, S, C |
| EPSS: a probability that a published CVE will be exploited in the wild in the next 30 days, published daily | [FIRST EPSS](https://www.first.org/epss/) | Read |
| CISA KEV catalog: authoritative source of vulnerabilities exploited in the wild; to be used as an input to prioritization | [CISA KEV catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) | Read |
| The `CVE-2021-44228` record as shown: status, dates, two v3.1 scores of 10.0 and one v2 score of 9.3, CWE-917, 103 references, KEV added 2021-12-10 with due date 2021-12-24 | NVD API `https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2021-44228` | Observed 2026-10-22; records change as they are edited |
| NVD API rate limit | none | Not read; "do not loop it" is caution, not a stated limit |
| What CVE and NVD are | [CVE Program](https://www.cve.org/), [NVD](https://nvd.nist.gov/) | Pages load; descriptions here are general knowledge, **est.** |
| The cloud-init update setup quoted for this project | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` as of this page's commit | Read in this repository |
| The lab outputs (sizes, times, the CRC error, the manifest failure, 20 pending packages) | Run 2026-10-22 on Linux as an ordinary user | Observed; numbers change on your machine |
| Differences between `tar` and `Compress-Archive`, `Expand-Archive` behavior on a damaged zip, `winget upgrade`, `softwareupdate`, `dnf check-update` exit code 100, PowerShell scheduled tasks | Microsoft Learn and vendor manuals, not read in this session | **est.** |

Not verified, plainly: the whole PowerShell and Windows track; macOS; every Docker command; the optional own-account path from start to finish, including whether the doctl backup-plan strings are accepted as written, whether the first weekly backup lands inside the window you choose, the time zone of that window, how long a restore takes, whether the host key is unchanged after a restore, and how a retained backup of a destroyed droplet is billed; Patch Gremlin's code and behavior beyond its README; and the DigitalOcean pages' behavior after their stated "last verified" dates.

Next: [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md), core step 15 on the [Reading order](Reading-Order.md) page.
