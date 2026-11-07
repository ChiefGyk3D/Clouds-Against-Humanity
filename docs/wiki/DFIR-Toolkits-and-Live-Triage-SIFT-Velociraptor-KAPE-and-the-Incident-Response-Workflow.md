# DFIR toolkits and live triage: SIFT, Velociraptor, KAPE and the incident response workflow

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 2: Defend and detect](Contents.md#track-2-defend-and-detect) > DFIR toolkits and live triage

Previous: [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) / Next: [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md)
<!-- END GENERATED PAGE NAV top -->

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says (and the gap)](#what-the-wiki-already-says-and-the-gap)
- [What DFIR is, in one paragraph](#what-dfir-is-in-one-paragraph)
- [The toolkits at a glance](#the-toolkits-at-a-glance)
- [Live triage and dead-box imaging](#live-triage-and-dead-box-imaging)
- [An incident response workflow, and where forensics fits](#an-incident-response-workflow-and-where-forensics-fits)
- [Mobile and cloud forensics: what is different](#mobile-and-cloud-forensics-what-is-different)
- [Training and certifications](#training-and-certifications)
- [Free exercise: collect triage artifacts from your own machine and read them](#free-exercise-collect-triage-artifacts-from-your-own-machine-and-read-them)
- [What failed when I ran it](#what-failed-when-i-ran-it)
- [Not verified, plainly](#not-verified-plainly)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

## What you will be able to do

- Say what each of six toolkits is for (SIFT Workstation, CAINE, Velociraptor, KAPE, FTK Imager, plaso), who maintains it, and whether it is open source or only free to download, as of a stated date.
- Explain live triage against dead-box imaging, and the cost of looking at a running system: you change it by touching it.
- Walk an incident through the six steps most teams teach (preparation, detection, containment, eradication, recovery, lessons learned), say where NIST's own text stands on that list, and say where forensics fits in it.
- Say what is different about mobile and cloud forensics and where to read next, without a step-by-step.
- Name the certifications GIAC lists in this area, from GIAC's own pages, without being sold one.
- Collect a small set of triage artifacts from a Linux machine you own, hash and store them like evidence, and read them for anything wrong.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Logs become alerts | [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) | What you do on the one machine after the alert fires |
| A small detection stack | [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) | The step after detection: collecting from the host |
| Backups and restores | [Backups, recovery and patching](Backups-Recovery-and-Patching.md) | The recovery step of an incident, and why a restore is not evidence |
| Careers and certifications in general terms | [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md) | The DFIR certifications named, from the issuer |
| Forensics itself | Nothing before this series | Foundations, disk, memory and network lessons are separate pages in the digital forensics series |

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. The exercise commands were run once, on 2026-11-07, on a Linux workstation I own, not in a throwaway VM.** I ran the collection script below there and kept the output in a private folder. I ran `ps`, `ss`, `w`, `crontab -l`, `ls`, `systemctl list-timers`, `find`, `sha256sum` and `sha256sum -c`. I downloaded Velociraptor 0.77.3 for Linux and ran `velociraptor artifacts collect Linux.Sys.Pslist --format csv` as a normal user (exit 0). **Not run:** Velociraptor's instant `gui` mode (it opens a browser on the desktop, and I do not do that to a machine in use), the downloaded file's signature check, any Windows tool (KAPE and FTK Imager are Windows programs and I have no Windows lab), SIFT Workstation, CAINE and plaso. Everything said about those four, KAPE and FTK Imager comes from the owner's page, read on 2026-11-07, and is dated in the [claims register](#claims-register). Three things failed or did not match, and are listed under [what failed](#what-failed-when-i-ran-it). Trust what your terminal prints over what this page says.

> **Prerequisites.** A Linux machine you own where you may run commands, ideally a virtual machine from the [virtual machines lesson](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md). The [terminal and your first script](Terminal-and-Your-First-Script.md) and [logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) help. [Checksums](Hashing-Encryption-and-Keys.md) are used in the exercise. About 2 hours for reading and the exercise (est.).

> **Where this runs, and the rule.** Only systems you own, or systems you have written permission to examine. Collecting from someone else's computer without that permission can be a crime in many places, and "I was only looking" is not a defense. The exercise reads your own lab machine. It plants one harmless process and removes it. No real evidence, no third-party data, no real addresses appear here. This page is not legal advice.

The lessons that come with this one in the series are plain text until they exist: digital forensics foundations (chain of custody, write blockers, the order of volatility), disk forensics with Autopsy, memory forensics, and network and log forensics. This page does not assume them. Where it needs an idea from one, it says the idea in a sentence.

## What DFIR is, in one paragraph

DFIR is digital forensics and incident response. Incident response is the job of stopping a problem and getting back to work. Digital forensics is the job of working out what happened, in a way you can defend later. They share tools and they pull in opposite directions: a responder wants the bad process dead now, and an examiner wants it left alone until it is captured. Most of this page is about how people live with that tension.

## The toolkits at a glance

"Open source" here means the license text is one the Open Source Initiative recognizes and the source is published. "Free" means no price, which says nothing about whether you can read or change the code. Everything below was read on **2026-11-07** from the owner's page, with a second place noted where the owner's page was silent.

| Tool | Does what | Maintainer | License, as read | Platform | Version read |
|---|---|---|---|---|---|
| SIFT Workstation | A pre-built set of forensic and incident response tools | SANS (created 2007 by Rob T. Lee for the SANS FOR508 course, per SANS) | SANS says "open source and free" and names no license. The `teamdfir/sift` repository on GitHub carries a license file that GitHub reads as MIT | OVA virtual machine appliance (about 8.81 GB), Ubuntu 22.04 install, or Windows through WSL | No version number on the SANS page. Download "last updated 24 Apr 2026". The repository's last push I read was 2024-02-14 |
| CAINE | A bootable forensic Linux distribution with a point-and-click side and a Windows toolset (WinTaylor) | Nanni Bassetti, project manager, Bari, Italy | Free software under the GNU LGPL 2.1 or later; bundled third-party tools keep their own licenses | Live image, Ubuntu 24.04 base | 14.0 "Lightstream", released 2025-03-24 |
| Velociraptor | Collects artifacts from endpoints and answers questions about them, with its own query language (VQL) | The page footer says "brought to you by" Rapid7; the code lives under the Velocidex organization | AGPL-3.0 (the `LICENSE` file in the repository, read) | Binaries for Windows, Linux and macOS | 0.77.3, announced 2026-10-05 |
| KAPE | Fast Windows triage: copies the files that matter, then runs parsers on them | Kroll; Kroll credits Eric Zimmerman as its creator | Free to download, **not open source**. Kroll's terms: free for government agencies, education and research, and internal company use; an enterprise license for paid engagements or use on a third party's network | Windows | Not read from an owner page (see the register) |
| FTK Imager | Makes forensic images of drives, previews evidence, captures memory from a live system | Exterro | Free of charge per Exterro's page; **not open source**; license terms not read | Windows, per the page's structured data | Not stated on the product page |
| plaso (log2timeline) | Turns many artifact sources into one "super timeline" | The log2timeline organization on GitHub | Apache-2.0 | Python; the page does not list platforms | `plaso-20261027`, published 2026-10-27 per GitHub's release record |

Five of these are worth a short note each.

**SIFT Workstation.** SANS built it as the machine you sit at for the FOR508 course and it ships with the open source tools those courses use. The SANS page says the install now goes through a tool called `cast` (`sudo cast install teamdfir/sift` on Ubuntu 22.04), and its feature list still mentions an older Ubuntu release. That mismatch is on SANS's own page; I did not install SIFT to see which is true. A SANS account is needed for the VM download. The same page describes a separate experimental project called Protocol SIFT, which it says is not validated for forensic soundness and is not court-admissible. That is a useful sentence to remember about any tool: "it ran" is not "it is reliable evidence".

**CAINE.** A live distribution you boot from a USB stick so you do not touch the installed system. Its page lists CAINE as free software under the LGPL, with the usual caveat that the many tools inside keep their own licenses. Read the license of a specific tool before you redistribute it.

**Velociraptor.** The one that matters most if you want to run response at more than one machine. The docs describe four things you may do with the same program. A client and server deployment, where endpoints keep a connection to a server on a Linux machine and the data sits in ordinary files. A command line tool that runs a query or collects an artifact locally. An offline collector, a small program you hand to a machine that writes its results to a file with no server involved. And "instant Velociraptor", one process that is both server and a single client on your own machine, started with `velociraptor gui`. The docs state that instant mode listens only on the loopback interface, creates one user with the default name and password `admin` and `password`, stores data in a temporary folder that the operating system may clear, and is "not intended to be a production server". They also warn that running it on a machine you are examining can disturb the evidence, and suggest moving the datastore to an external drive. The page banner on the day I read it told users to upgrade from 0.77.2 to 0.77.3 for several CVEs, so do not run an old copy from a download folder you made last year.

**KAPE.** A target is a list of files to copy (browser history, event logs, registry hives); a module is a program to run on the copies. The docs say it copies locked files by a second pass that reads the disk raw, and re-applies the original timestamps to the copies. It does not download its own tools: the docs say you place the parser programs yourself, so you know what ran. Free to download does not mean free to use on a client's network. If you earn money with it, or use it on a network that is not yours, read Kroll's terms; a page I read said that needs an enterprise license.

**FTK Imager.** Free from Exterro, Windows, closed source. People use it for three things: imaging a drive to a file with a hash, previewing a drive without writing to it, and capturing RAM from a live Windows machine. A note on the age of what you find online: guides for FTK Imager 3 and 4 are everywhere, and Exterro's own page did not name a version when I read it.

plaso is the odd one out: it is a back-end. You feed it disk images or collected artifacts and it parses them into one time-ordered store you can search. It earns its place in the toolkit because "what happened between 02:10 and 02:20" is a question about many files at once.

## Live triage and dead-box imaging

**Dead-box imaging** means the machine is powered off (or its disk is removed), and you copy the storage bit for bit, with a write blocker so the examiner cannot change the original. You hash the copy, work on the copy, and keep the original sealed. The method is slow and thorough. What it loses: everything that lived only in memory, the network connections, who was logged in, and any disk that is encrypted and locked once power is gone.

**Live triage** means you work on the running machine. You list processes, connections and logged-in users, copy a short list of important files, and sometimes capture memory. It is fast and it sees what is running right now. What it costs:

- **You change the system by touching it.** Running a command starts a process, reads files (which can update access times), fills memory and may write to disk. A program you run can also be lied to by malware already on the machine.
- **Order matters.** The more volatile the data, the sooner it should be collected. Memory and network state vanish first; files on disk last. A foundations lesson in the series covers the order of volatility properly. The short version: do not start by copying files if you also want memory.
- **It is not repeatable.** A running system changes every second. A disk image can be checked a hundred times; a process list cannot.
- **You must write down what you did.** Every command, in order, with the time. Your own footprints are part of the record.

NIST's old forensics guide for incident response, SP 800-86 (August 2006, no withdrawal notice on its page when I read it), takes the same practical line. It is written from an IT point of view rather than a law enforcement one and says it is not a complete forensic procedure or legal advice. It is old; read it for the reasoning, not for tool names.

A common working pattern combines the two: triage first to decide how bad it is and which machines to take, capture memory if you will need it, then image the drive. KAPE's docs describe exactly that use: collect the critical artifacts "prior to the start of the imaging process" and review them for leads while the image completes.

| Question | Dead-box imaging | Live triage |
|---|---|---|
| Changes the evidence | Least, with a write blocker | Always some |
| Sees memory and network state | No | Yes |
| Speed | Hours | Minutes |
| Needs the machine to stay up | No | Yes |
| Handles full-disk encryption already unlocked | Not after power-off | Yes, while it runs |
| Can be repeated by someone else | Yes, on the image | No |

## An incident response workflow, and where forensics fits

NIST SP 800-61 is the standard US reference for incident response. Revision 2 (August 2012) had four phases: preparation; detection and analysis; containment, eradication and recovery; post-incident activity. Revision 3 was published in **April 2025** with a new title ("Incident Response Recommendations and Considerations for Cybersecurity Risk Management: A CSF 2.0 Community Profile") and it replaces Revision 2. I read the PDF on 2026-11-07. It drops the circular four-phase picture and says why: incidents used to be rare and narrow, and today they "cause far more damage" and recovery "often takes weeks or months", so lessons should be shared as they are found, not after recovery. It organizes the work by the six functions of NIST's Cybersecurity Framework 2.0 instead: Govern, Identify, Protect, Detect, Respond and Recover. Its Table 1 maps the old phases onto them: preparation to Govern, Identify and Protect; detection and analysis to Detect; containment, eradication and recovery to Respond and Recover; post-incident activity to the Improvement category under Identify. It also tells organizations to use whichever model suits them.

The six steps below are the teaching version that most courses and teams still use. They follow the Revision 2 shape with containment, eradication and recovery pulled apart. I use them because they are easy to hold in your head, not because Revision 3 says so.

1. **Preparation.** Before anything happens: who to call, who may decide to cut a server off, logs turned on and kept, clocks in sync, backups you have restored, and tools you have tried once. This is where most of the outcome is decided. See [logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md), [backups, recovery and patching](Backups-Recovery-and-Patching.md) and the baseline habit in [first hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md).
2. **Detection.** An alert, a user report, an odd bill. Decide whether it is an incident. Write the time you first knew. [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) is a small version of this step.
3. **Containment.** Stop the spread without destroying what you need: isolate the network port, disable the account, snapshot the VM before touching it. Pulling the power loses memory; leaving the machine online lets the attacker keep working. This is the judgment call the whole page is about. **Live triage belongs here**, in the first minutes, before you change the machine further.
4. **Eradication.** Remove the cause: the malicious account, the planted job, the vulnerable service. Remove it everywhere you found it, which means you needed the scoping from triage first.
5. **Recovery.** Put things back: rebuild from a known-good source, restore data you have tested, watch closely for a return. A backup taken after the intruder arrived restores the intruder too.
6. **Lessons learned.** What did we see, miss, and decide? Which log was absent? Write it down while people remember it, and feed it back into preparation.

Where forensics fits: it is not a seventh step. Triage and imaging happen during containment, because that is the last moment the evidence is as the attacker left it. The slower disk, memory and timeline work runs alongside eradication and recovery and mostly answers "how did they get in, what did they take, is it really gone". Its findings go into lessons learned. If law enforcement, insurance or a lawsuit is possible, tell your legal contact before you start; some of what you do first cannot be redone to a legal standard afterward.

## Mobile and cloud forensics: what is different

I am keeping this short on purpose. These are specialties, the tools change faster than a lesson can, and a step-by-step from me would be worse than the vendor's and the standards bodies'.

**Mobile.** A phone is not a PC with a smaller screen. Storage is encrypted by default on current platforms and tied to a hardware key, so a powered-off, locked device may give you nothing. The data you want is in app databases and cloud accounts as much as on the device. Acquisition levels run from what the device agrees to hand over, to a full file system extraction that often needs a commercial tool, an exploit, or the owner's passcode. The phone also keeps talking to the network and can be wiped remotely, which is why examiners isolate it first. NIST's *Guidelines on Mobile Device Forensics*, SP 800-101 Revision 1 (May 2014), describes validating, preserving, acquiring, examining, analyzing and reporting. It is more than ten years old, so read it for the process and look elsewhere for current techniques.

**Cloud.** There is no disk to image. The evidence is logs and snapshots that the provider holds, under the provider's retention settings and the provider's idea of shared responsibility. Your first question is not "which tool" but "were the right logs on, and for how long are they kept". The machines are short-lived: a container or an autoscaled instance can be gone before you arrive. NIST's *Cloud Computing Forensic Reference Architecture*, SP 800-201 (final, July 2024), is about forensic readiness: what a cloud design must already have in place so that an investigation is possible. I read its summary page, not the full text. See [backups, recovery and patching](Backups-Recovery-and-Patching.md) for the cloud snapshot habit, and the cost lessons for what retention costs.

Where to go next, in order: do the disk and memory lessons in this series on your own machine first, because mobile and cloud work assumes you already know what an artifact is; then the vendor documentation of the platform you actually work on; then a course (below).

## Training and certifications

Read from the issuer's pages on **2026-11-07**. No prices are listed on the GIAC pages I read, so I give none. I have no affiliate link with anyone and this is not an endorsement; certifications are one way to get a syllabus and a signal, not a substitute for having done the work (see [careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md#certifications-as-signposts)).

| Certification | Issuer's description | Format read | Related course named |
|---|---|---|---|
| GIAC Certified Forensic Examiner (GCFE) | Windows forensics and data triage: registry, USB devices, shell items, email, log analysis, and browser forensics for Chrome, Edge and Firefox | One proctored exam, 82 questions, 3 hours, 70 percent to pass (for versions released on or after 2022-12-17) | Windows Forensic Analysis |
| GIAC Certified Forensic Analyst (GCFA) | Advanced incident response and forensics: memory forensics, timelines, anti-forensics detection, threat hunting | One proctored exam, 82 questions, 3 hours, 71 percent to pass (for versions released on or after 2023-03-18) | FOR508, Advanced Digital Forensics, Incident Response, and Threat Hunting |
| GIAC Linux Incident Responder (GLIR) | Linux incident response and threat hunting, file system artifacts using The Sleuth Kit, triage, logs, timelines | One proctored exam, 82 questions, 3 hours, 66 percent to pass (for versions released on or after 2025-05-17) | A SANS Linux threat hunting and incident response course |
| GIAC Experienced Forensics Examiner (GX-FE) and GIAC Enterprise Incident Response (GEIR) | Listed on the GIAC certifications page as DFIR certifications | Not read | FOR500 and FOR608 respectively, per that page |

Details from the GCFE page: the exam is web-based and must be proctored, remotely or at a test center, and you have 120 days from activation to take it. Renewal is on a separate GIAC page that I did not read, so I say nothing about cost or cycle. The GIAC certifications page showed a DFIR category count of 16 and listed only three on the view I read; there are more than I name here. Other issuers (vendors, CompTIA, EC-Council, OffSec) have forensic and incident response credentials that I did not check, so I name none. Check the exam objectives on the issuer's page the week you decide, because versions and pass marks change, as the dated rows above show.

Free practice material exists too, and it is the better first step: the other pages in this series, the project documentation of each tool above, and your own lab.

## Free exercise: collect triage artifacts from your own machine and read them

Time: about an hour. Cost: nothing. Use a Linux virtual machine you own, or a Linux computer you own and can afford to look at. Debian, Ubuntu and similar. Do not use a machine that holds someone else's data.

### Step 1. Decide where evidence goes before you collect

Make a folder that is not under `/tmp`, readable only by you. Everything below goes there. You are practicing the habit that matters: collect to a place you chose, with a record of what you did.

```bash
mkdir -p ~/triage-lab && chmod 700 ~/triage-lab
```

### Step 2. Collect, volatile first

This is the order: processes and connections (change in seconds), then who is logged in, then scheduled jobs, then files on disk. It uses only commands that ship with most Linux systems. Save it as `collect.sh` somewhere that is not the folder it writes to.

```bash
#!/usr/bin/env bash
# collect.sh OUTDIR - read-only triage of THIS machine. Writes text files, then hashes them.
set -u
out="$1"; mkdir -p "$out"; cd "$out"; umask 077
{ date -u +%FT%TZ; uname -srm; id; } > 00-collection-info.txt
ps -eo pid,ppid,user,lstart,args --sort=start_time > 10-processes.txt
ss -tunap > 20-connections.txt 2> 20-connections.err
w > 30-users.txt
last -n 20 > 31-last.txt 2>&1
crontab -l > 40-user-cron.txt 2>&1
ls -l /etc/cron.d /etc/cron.daily > 41-system-cron.txt 2>&1
systemctl list-timers --all --no-pager > 42-timers.txt 2>&1
find /home /tmp /etc -xdev -type f -mtime -1 2>/dev/null | head -200 > 50-recent-files.txt
sha256sum [0-9]*.txt > SHA256SUMS
sha256sum -c SHA256SUMS
```

Run it as yourself first. Running as root (`sudo`) shows more (the program that owns each socket, other users' crontabs) and also changes a bit more; for a lab, run both and diff them, which teaches the point of the next section.

```bash
bash collect.sh ~/triage-lab/run1
```

### Step 3. Store it like evidence

The hash file you just made proves the files have not changed since you made it. Make that mean something: lock them, and write a note that says who, when, what and with which versions.

```bash
cd ~/triage-lab/run1
chmod 400 [0-9]*.txt SHA256SUMS
{ echo "collected by: me, on a machine I own"; echo "tool: collect.sh, bash, ps, ss, sha256sum"; ps --version; ss -V; sha256sum --version | head -1; } > NOTES.txt
sha256sum -c SHA256SUMS
```

A real case adds who handled it, when, and where it was stored. A foundations lesson in the series covers chain of custody. Here you are building the reflex.

### Step 4. Read it, and plant something to find

A clean machine teaches you what normal looks like. Make one thing abnormal, harmlessly: a copy of `sleep`, renamed with a leading dot, run from a new folder under `/tmp`, then deleted while it runs.

```bash
plant=$(mktemp -d)
cp "$(command -v sleep)" "$plant/.cache-update"
"$plant/.cache-update" 300 &
pid=$!
echo "planted pid: $pid in $plant"
```

Now collect again (`bash collect.sh ~/triage-lab/run2`) and read both runs for these, in this order:

1. **Processes** (`10-processes.txt`): anything whose command line starts in `/tmp`, `/dev/shm` or a hidden folder; a process whose name imitates a system one; a start time that fits no activity of yours. Your planted process should stand out.
2. **Deleted binaries**: a program that deleted itself after starting is a classic hiding trick. The file listing will not show it; the process still does:

   ```bash
   ls -l /proc/$pid/exe
   ```

   (Use the planted pid. After you delete the file in step 5, the target ends in `(deleted)`.)
3. **Connections** (`20-connections.txt`): listening ports you did not open, and established connections to places you do not recognize. Match each to a process.
4. **Users and logins** (`30-users.txt`, `31-last.txt`): sessions at odd hours, or from where you were not.
5. **Scheduled jobs** (`40-`, `41-`, `42-`): a job you did not write. Compare against [cron, systemd timers and init scripts](Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd.md) for what a normal one looks like.
6. **Recent files** (`50-recent-files.txt`): files changed in the last day under `/etc` that you did not change, and anything new in `/tmp`.

Write down, for each thing you flagged, whether it is suspicious or normal and the evidence either way. Most of what you flag will be normal; learning that is the point.

### Step 5. Clean up

Run this in the same shell as step 4, so `plant` and `pid` are still set. The first `ls` shows the file the process runs from. After the file is deleted, the same link ends in `(deleted)`, which is what you looked for in step 4. Then kill the process by its pid.

```bash
ls -l /proc/$pid/exe
rm "$plant/.cache-update"
ls -l /proc/$pid/exe
kill "$pid"
rmdir "$plant"
```

I ran this sequence on 2026-11-07 and the second `ls` printed `(deleted)`. Keep `~/triage-lab` as long as you like. It holds your own machine's state, which can include command lines with things you typed, so do not post it.

### Step 6 (optional). The same thing with Velociraptor

Velociraptor has an artifact for processes. This runs it without a server and without a browser.

```bash
mkdir -p ~/vr-lab && cd ~/vr-lab
# Download the Linux amd64 binary for the version you choose from the project's GitHub releases page,
# unpack it, and make it executable. On 2026-11-07 the file was velociraptor-v0.77.3-linux-amd64.gz.
gunzip velociraptor-v0.77.3-linux-amd64.gz
chmod 700 velociraptor-v0.77.3-linux-amd64
./velociraptor-v0.77.3-linux-amd64 version
./velociraptor-v0.77.3-linux-amd64 artifacts list | grep -E '^Linux\.(Sys\.(Pslist|Users|Crontab)|Network\.Netstat)'
./velociraptor-v0.77.3-linux-amd64 artifacts collect Linux.Sys.Pslist --format csv > pslist.csv
```

What I saw: the version line printed `0.77.3`; the `list` showed `Linux.Network.Netstat`, `Linux.Sys.Crontab`, `Linux.Sys.Pslist` and `Linux.Sys.Users`; the `collect` exited 0 and printed one row per process. Hash columns for programs I could not read as a normal user were the SHA-256 of nothing at all (`e3b0c442...b855`). That value is what every hash function gives for an empty input, so it means "I could not read this file", not "this file is clean". The download page for each release also lists a `.sig` file next to the binary; I downloaded it and did not verify it.

Instant mode, `velociraptor gui`, is the way to see Velociraptor's web interface on your own machine. The docs say it binds to loopback, uses the default `admin` and `password`, and keeps its data in a temporary folder. I did not run it. If you do, run it in the lab VM, not on a machine you care about, and put `--datastore` on a folder you chose so the data survives a reboot, as the docs suggest.

### Check yourself

- Which of your flagged items did you write down evidence for, and which are only a feeling?
- Did the `sudo` run show something the normal run did not? Which, and why?
- What did running the script change on the machine? (Look at the process list in `run2`: your own `collect.sh`, `ps` and `find` are in it.)
- If this had been a real incident, what would you have done before step 2?

## What failed when I ran it

- `last` is not installed on the machine I ran the script on: exit code 127 ("command not found"), so `31-last.txt` held an error message. I did not check which package provides it on your system. The script keeps going, which is the right behavior, and you should look at the file.
- `crontab -l` exited 1 because my user has no crontab. That is a result, not a failure.
- My `ss` output was over nine thousand lines, far more than I expected, on a machine with many connections. Yours will be different. It shows that "collect everything" can produce more than a person can read, which is why triage tools filter.
- The Velociraptor hash fields were empty-input hashes when I ran as a normal user, described above.

## Not verified, plainly

- I did not install or run SIFT Workstation, CAINE, KAPE, FTK Imager or plaso. What the table says about them is what their owners' pages said on 2026-11-07, and where a page named no version or no license I said so.
- I did not read KAPE's license agreement on Kroll's site; the pages were blocked to my fetch (HTTP 403). The terms in the table come from search-result summaries of Kroll's own pages and from the KAPE documentation, so they are a second-hand reading of Kroll's text. **est.** Read Kroll's terms yourself before you rely on them.
- I did not find a current FTK Imager version from Exterro. A search result mentioned a 4.7 line, from a page I could not confirm is current. **est.**
- The mobile and cloud paragraphs are general knowledge plus the NIST pages named. I read the NIST summary pages for SP 800-101 Revision 1 and SP 800-201, not the full documents. **est.** for the specific statements about encryption and retention.
- I did not run the Windows-side advice (anything about FTK Imager's memory capture or KAPE targets) and have no Windows lab for it.
- Certification pass marks and exam sizes change with exam versions. Check your attempt's details in your GIAC account.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "I will just look around the machine and image it later" | Looking changes it, and what you did is part of the record | Write each command down as you run it |
| "The hash of an empty file matches, so it is clean" | `e3b0c442...b855` is the SHA-256 of nothing | The file size, and whether the tool could read it |
| "KAPE is free so I can use it on a client" | Kroll's terms for paid engagements differ | The current license on Kroll's page |
| "Free means open source" | KAPE and FTK Imager are free and closed | The license on the owner's page |
| "I pulled the plug to stop it" | Memory and connections are gone | Containment options before power-off |
| "Instant Velociraptor is a server" | The docs say it is not for production | The deployment page |
| "Any old copy of the tool is fine" | A tool can have fixed security holes since you downloaded it | The project's current release |
| "A tool's output is a finding" | It is a lead until you understand what it read | Look at the source artifact |

## Claims register

Retrieved on 2026-11-07. "Page read" means I read the owner's page through a fetch tool, which returns a model-written summary of the page, so quoted words come from that summary; "Read" means I read primary text directly; "Run" means I ran it on one Linux machine; **est.** means I did not verify it.

| Claim | Source | Status |
|---|---|---|
| SIFT: free and open source, created 2007 by Rob T. Lee for FOR508, OVA about 8.81 GB, Ubuntu 22.04 install with `cast`, WSL install, download last updated 24 Apr 2026, no version number, issues on GitHub; Protocol SIFT is experimental and not validated for forensic soundness | SANS, SIFT Workstation page | Page read |
| SIFT repository carries an MIT license file and its last push was 2024-02-14 | GitHub repository record for the SIFT project | Read |
| CAINE 14.0 "Lightstream", 64-bit, Ubuntu 24.04 base, released 2025-03-24, LGPL 2.1 or later for CAINE and WinTaylor, third-party tools keep their licenses, project manager Nanni Bassetti | CAINE project site | Page read |
| Velociraptor: 0.77.3 announced 2026-10-05, upgrade advised from 0.77.2 for CVEs; Windows, Linux and macOS binaries; "brought to you by" Rapid7; code under Velocidex | Velociraptor documentation home page; GitHub releases page (tag v0.77.3) | Page read |
| Velociraptor code is AGPL-3.0 | The `LICENSE` file in the Velocidex repository, first lines | Read |
| Velociraptor deployment models; instant mode on loopback, default admin credentials, temporary datastore, not a production server, can pollute evidence, production server on Linux | Velociraptor deployment documentation | Page read (first part of a long page) |
| KAPE is a triage program with targets and modules, copies locked files by a second raw pass, re-applies timestamps, does not download its own tools, and can be used before imaging | KAPE documentation index, `Getting started` page, read from the docs repository | Read |
| KAPE: free to download from Kroll; free for government, education, research and internal company use; enterprise license for paid engagements or use on a third-party network; Eric Zimmerman credited as creator | Search-result summaries of Kroll's resource and license pages; Kroll's own pages returned HTTP 403 to my fetch | **est.** |
| FTK Imager: free, creates images with hash verification, previews, captures volatile memory, Windows per structured data, vendor Exterro, no version stated | Exterro, FTK Imager product page | Page read |
| A 4.7 line of FTK Imager exists | A search result for the vendor's download page, which I could not open | **est.** |
| plaso: Python timeline engine, Apache-2.0; release `plaso-20261027`, published 2026-10-27T10:23:33Z | GitHub repository page; GitHub release record for the latest release | Page read |
| NIST SP 800-61 Revision 3 (April 2025) replaces Revision 2 (2012-08-06); it uses the six CSF 2.0 functions in place of the circular four-phase model; Table 1 maps the old phases; "use the model that suits you" | NIST SP 800-61r3 PDF, sections 2.1 and Table 1; NIST publication page | Read |
| Revision 2's four phases: preparation; detection and analysis; containment, eradication and recovery; post-incident activity | Named in Table 1 of SP 800-61r3 as "previous incident response life cycle model" | Read |
| The six-step list (preparation, detection, containment, eradication, recovery, lessons learned) is a common teaching split | General knowledge; not a NIST wording | **est.** |
| NIST SP 800-86, August 2006: IT perspective, not a complete procedure, no withdrawal notice on its page | NIST publication page | Page read |
| NIST SP 800-101 Rev. 1, May 2014, supersedes the 2007 edition; covers validating, preserving, acquiring, examining, analyzing and reporting | NIST publication page | Page read |
| NIST SP 800-201, final 2024-07-30, forensic readiness for cloud, draft 2023-02-08 | NIST publication page and news release (via search) | Page read; full text not read |
| GCFE: 82 questions, 3 hours, 70 percent for versions released on or after 2022-12-17, proctored, 120 days from activation, no price listed | GIAC, GCFE page | Page read |
| GCFA: 82 questions, 3 hours, 71 percent for versions on or after 2023-03-18, FOR508, no price listed | GIAC, GCFA page | Page read |
| GLIR: 82 questions, 3 hours, 66 percent for versions on or after 2025-05-17; GX-FE (FOR500) and GEIR (FOR608) are listed; DFIR category count 16 | GIAC, GLIR page and certifications page | Page read |
| Mobile devices are encrypted by default and tied to a hardware key; phones can be wiped remotely; cloud instances can disappear before collection | General knowledge | **est.** |
| The collection script and the planted process ran as described; `last` missing (exit 127); `crontab -l` exit 1; Velociraptor 0.77.3 `artifacts collect Linux.Sys.Pslist --format csv` exit 0 with empty-input hashes as a normal user | One run each, 2026-11-07, one Linux workstation (ps from procps-ng 4.0.4, ss from iproute2 6.15.0, sha256sum from GNU coreutils 9.7, bash 5.2.37) | Run |

Search queries I used for items the owners' pages did not settle: "KAPE Kroll Artifact Parser and Extractor free download license"; "Kroll KAPE free for government educational research internal use enterprise license"; "Exterro FTK Imager latest version download release notes"; "SIFT Workstation SANS GitHub sans-dfir sift releases cast"; "NIST SP 800-201 cloud computing forensic reference architecture".

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 2: Defend and detect](Contents.md#track-2-defend-and-detect) > DFIR toolkits and live triage

Previous: [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) / Next: [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md)

In this track: [Track 2: Defend and detect](Contents.md#track-2-defend-and-detect), 35 pages

- Network and host defense: [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md) / [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md) / [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) / [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md) / [Plan for failure: blast radius and assuming breach](Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md) / [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md) / [Attack surface map: layer by layer](Attack-Surface-Map-Layer-by-Layer.md) / [The DMZ and hardening an internet-facing host](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md) / [DMZ hardening checklist](DMZ-Hardening-Checklist.md)
- Deception and honeypots: [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md) / [What deception is](Deception-and-Honeypots-What-Deception-Is.md) / [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) / [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md) / [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md) / [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) / [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md) / [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md) / [Anatomy of a cloud honeypot](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md) / [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md) / [Read what arrived: Cowrie logs](Deception-and-Honeypots-Read-the-Sensor-Logs.md)
- Detection and monitoring: [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md) / [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) / [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) / [Wazuh SIEM and data pipelines](Wazuh-SIEM-and-Data-Pipelines.md) / [Detecting Tor, I2P and VPN on a network](Detecting-and-Managing-Tor-I2P-and-VPN-on-a-Network-the-Defenders-View.md) / [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) / [Multiple sites and identity](Multiple-Sites-and-Identity.md) / [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) / [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) / [Grafana basics from a blank page](Grafana-Basics-From-a-Blank-Page.md) / [Grafana dashboards](Grafana-Dashboards.md) / [Lab: synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md) / [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) / [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md)
- Digital forensics: **DFIR toolkits and live triage**

Related pages:

- [Lab: synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md)
- [Grafana dashboards](Grafana-Dashboards.md)
- [Grafana basics from a blank page](Grafana-Basics-From-a-Blank-Page.md)
- [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md)
<!-- END GENERATED PAGE NAV bottom -->
