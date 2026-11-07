# Digital forensics foundations: evidence handling, chain of custody and the order of volatility

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. Only the exercise's file commands were run; no forensic tool, write blocker or loop device was used.** On **2026-11-07** I ran, on one Linux machine with GNU coreutils 9.7, the commands in [the exercise](#free-path-hash-image-verify-break-one-bit-and-write-the-form) against a 1 MiB file of random bytes: `sha256sum`, `dd`, `cmp`, a one-bit change with a short Python line, and `sha256sum -c`. Every output shown below comes from that run, except that your hashes will differ because the file is random. **Not run:** the optional loop-device variant, any write blocker, `dc3dd`, `ewfacquire`, Autopsy, memory capture, anything on macOS or Windows, and every PowerShell line (there are none). The standards were read on **2026-11-07** from the pages named in the [claims register](#claims-register); a claim I could not read there is marked **est.** Trust what your terminal prints over what this page says.

> **Prerequisites.** A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)) and the idea of a hash ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)). A throwaway Linux VM is the safest place for the exercise ([Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md)). About 75 minutes for the reading and the exercise (est.).

> **Where this runs, and the rule.** Local and throwaway. The exercise touches a file you create, nothing else. **Examine only your own devices, or data you have written authorization to examine.** Taking someone else's phone, laptop or account and "just looking" can break the law in many places, and evidence you collect without authority can ruin a real case. This page is not legal advice, laws vary by country and I did not read any statute for it, so ask a lawyer before you handle anything that might end up in a dispute. The same written-permission habit is on [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md).

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 2: Defend and detect](Contents.md#track-2-defend-and-detect) > Digital forensics foundations

Previous: [Open firmware and trustworthy hardware](Open-Firmware-and-Trustworthy-Hardware-coreboot-Heads-Nitrokey-and-Vendors-That-Ship-the-Intel-ME-Disabled.md)
<!-- END GENERATED PAGE NAV top -->

This is the first of a small forensics series. The sibling lessons (disk examination with Autopsy, memory, network and log evidence, and toolkits with live triage) are written alongside it and are not linked yet; this page is the vocabulary and the habits they all assume.

## What you will be able to do

- Say what digital forensics is for and how it differs from incident response.
- List the order of volatility from RFC 3227 and say why it sets the order you collect in.
- Explain why you never work on the original, and what a bit-for-bit image is.
- Say what a hash proves in forensics and what it does not.
- Fill in a chain-of-custody record and say why a gap in it hurts.
- Run a hash, image, verify and tamper cycle on a file you made, and write the form for it.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| A hash changes if one byte changes | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md), exercise 1 | Using that as proof an evidence copy is exact, and when to record it. |
| Logs, time and detection | [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) | Keeping a log as evidence rather than reading it as a signal. |
| A copy you have not restored is a hope | [Backups, recovery and patching](Backups-Recovery-and-Patching.md) | A backup is for restoring; a forensic image is for proving. |
| A monitoring stack that raises alerts | [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) | What to do after the alert if the answer matters later. |
| Disposable labs | [Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) | Where to practice without real evidence. |

## What forensics is, and what it is not

NIST SP 800-86 is written from an IT view, not a law enforcement one. It describes a process with four phases: **collection**, **examination**, **analysis** and **reporting**. Collection is the part this page covers: finding, labeling and acquiring data without changing it, and recording what you did. Examination and analysis come later in the series.

Incident response asks "stop it and recover". Forensics asks "what happened, can I show it, and will it hold up if someone challenges it". They collide in the first minutes: the fastest way to recover (reboot it, wipe it) can destroy the answer. NIST says the same thing about decisions: before collecting, someone should decide, with the organization's policy and its legal advisers, whether the data may be needed for legal or disciplinary proceedings, because that decides how strict the handling must be.

## The rules every standard repeats

I read four sources: NIST SP 800-86, RFC 3227, SWGDE's acquisition guide and, secondhand, the UK's ACPO guide. They differ in detail and agree on these:

1. **Do not change the original.** NIST: if the evidence may be needed, make a bit stream image of the original, label the original, store it securely, and do all analysis on the copy.
2. **Prove the copy is exact.** Compute a hash of the source and of the copy and compare them.
3. **Write down everything.** Who, what, where, when, with which tool and version, and every error.
4. **Control who holds it.** Evidence is stored securely and every hand-off is recorded.
5. **Know your limits.** SWGDE says examiners may deviate from its practices when warranted but must document the circumstances and what they did.

The ACPO guide (a UK police document, now hosted by the National Police Chiefs' Council) states these as four principles. I could read only a secondhand quote of the first: no action taken should change data that may later be relied on in court. The other three, as I understand them, cover access by competent people who can explain their actions, an audit trail a third party could repeat, and a person in charge who sees that the law and the principles are followed (**est.**, from search summaries, not from the guide itself).

## Order of volatility

**Volatile** data disappears when power goes off or time passes. RFC 3227 (February 2002) gives the order to collect in, "from the volatile to the less volatile":

| # | Source (RFC 3227 wording) | Lives how long |
|---|---|---|
| 1 | registers, cache | nanoseconds, gone on the next instruction |
| 2 | routing table, ARP cache, process table, kernel statistics, memory | until reboot or until it is overwritten |
| 3 | temporary file systems | until reboot (est. for the exact lifetime) |
| 4 | disk | until it is overwritten or wiped |
| 5 | remote logging and monitoring data relevant to the system | until the log server rotates it |
| 6 | physical configuration, network topology | until someone re-cables |
| 7 | archival media | years |

The lifetimes in the third column are my plain-words gloss, not RFC text. NIST adds that volatility is only one factor: likely value of the source and the effort to get it matter too, and that "non-volatile data may also be somewhat dynamic", with log files that get overwritten as new events arrive as its example.

What this changes in practice:

- **Do not power it off first.** RFC 3227 lists "don't shutdown until you've completed evidence collection" among its things to avoid. Memory is in row 2 and goes with the power.
- **Do not trust the machine's own programs.** RFC 3227: "don't trust the programs on the system", because an intruder may have replaced them. Carry known-good tools on removable media.
- **Do not run anything that touches every file's access time**, such as `tar`, RFC 3227 says, because it changes the timestamps you may need.
- **Cutting the network is not free.** RFC 3227 notes that disconnecting or filtering can trigger "deadman switches" that wipe evidence.

The trade is real: collecting memory from a live machine also changes the machine (your tool loads into memory). ACPO's second principle exists for that case: if you must touch the original, you must be able to explain what you did and what it changed. The memory and live-triage lessons in the series go through how.

## Evidence handling: image, hash, copy

**Logical copy versus bit stream image.** NIST: a logical backup copies files and directories and misses deleted files and slack space. A bit stream image is "a bit-for-bit copy of the original media, including free space and slack space", larger and slower. If the data might matter later, take the image.

**Write blockers.** A write blocker is hardware or software that prevents the computer from writing to the media you attach. NIST: use one while imaging, and attaching a hardware blocker "will ensure that integrity is maintained". SWGDE: hardware or software write blockers "should be used when possible". Plugging a drive into a normal computer lets the operating system write to it, even if only to mount it.

**The hash routine.** NIST's order, quoted closely: compute the hash of the original *before* imaging, compute the hash of the copy *after* and compare, then compute the original's hash again to show imaging did not alter it, and document all results. NIST's 2006 text names MD5 and SHA-1 as the common algorithms, and tells federal agencies to use SHA-1; that is dated. SWGDE's 2023 document says to use "a NIST-approved hash algorithm" and I use SHA-256 below. Which algorithms are approved today is a question for the current NIST pages, not for this one (**est.** for the current list). The general background is on [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md).

**What a matching hash proves, and what it does not.** It proves the copy is bit-identical to the source as of the moment you hashed it. It does not prove the source was untouched before you got to it, that the person who ran the tool did the right thing, or that the evidence means what you think. The hash goes in the record; it does not replace the record.

**Work on a copy of the copy.** Keep one verified image sealed as the master and examine a working copy, so a slip costs you a re-copy, not the case.

## Chain of custody

Chain of custody is the written history of an item: where it was found, who held it, when, what they did to it and where it was stored. RFC 3227's wording: you should be able to describe "how the evidence was found, how it was handled" and keep a record of where, when and by whom it was discovered, handled and transferred, and who held custody and for how long. NIST asks for a log of every person with physical custody, what they did and when, and secure storage when it is not in use. SWGDE's list of what to document includes make, model, serial number or asset tag, source and location, case number, imaging tool and version, hash values, photographs, the examiner's name and title, the date and time with time zone, and errors. At each transfer SWGDE has the record note, at minimum, an identification of the item and the name of the person handing it over, among other fields (the rest of its list I did not copy; read the document).

Why it matters: a gap in the record ("it was in the break room for two days") gives anyone challenging the evidence a way to say it could have been changed. RFC 3227 frames the goal as evidence that is admissible, authentic, complete, reliable and believable; whether a particular court accepts a particular record is a legal question for your jurisdiction, and I do not claim anything about that.

A record is just a table. Yours for the exercise is at the end.

## ISO/IEC 27037, in one paragraph

ISO/IEC 27037:2012 is the international guideline for the identification, collection, acquisition and preservation of digital evidence. From ISO's catalog page and other listings (I could not open the page body, and I did not read the paid text): it is guidance for people handling potential digital evidence, covers devices from hard drives and phones to cameras and networked computers, and helps organizations with disciplinary procedures and with exchanging evidence between jurisdictions. A listing said it was last reviewed and confirmed in 2018, and a reseller showed a review stage in December 2023 (**est.**: check the ISO page for current status). I do not quote it.

## Free path: hash, image, verify, break one bit and write the form

Your own lab VM, a scratch folder, no real evidence. Everything here is a file you create.

```bash
mkdir -p ~/forensics-lab && cd ~/forensics-lab

# 1. A stand-in "evidence drive": 1 MiB of random bytes.
head -c 1048576 /dev/urandom > evidence-disk.img

# 2. Hash the source BEFORE imaging, and keep the hash in a file.
sha256sum evidence-disk.img | tee source.sha256

# 3. Make a bit-for-bit image. noerror,sync keeps going past read errors and pads them.
dd if=evidence-disk.img of=image.dd bs=4096 conv=noerror,sync status=none

# 4. Hash the image and compare. Also compare the bytes directly.
sha256sum image.dd | tee image.sha256
cmp evidence-disk.img image.dd && echo "cmp: identical"

# 5. Hash the SOURCE again: imaging must not have changed it (NIST's third check).
sha256sum -c source.sha256

# 6. Make a working copy, flip ONE bit in it, and hash again.
cp image.dd working-copy.dd
python3 - <<'PY'
b = bytearray(open("working-copy.dd", "rb").read())
b[1000] ^= 0x01
open("working-copy.dd", "wb").write(b)
PY
sha256sum working-copy.dd
cmp -l image.dd working-copy.dd
```

What my run printed on 2026-11-07 (your hashes will differ, since step 1 is random):

```text
7126a863...bce836d  evidence-disk.img
7126a863...bce836d  image.dd
cmp: identical
evidence-disk.img: OK
2eb9d742...f4a780   working-copy.dd
   1001 216 217
```

The first two hashes match, so the image is bit-identical; the third, after changing one bit, shares nothing visible with them. `cmp -l` prints the byte position (1-based, so 1001 is index 1000) and the old and new byte values in octal: `216` became `217`, a one-bit change. That is the whole idea: the hash is a tripwire for any change at all.

**Optional, not run: a loop device.** On a lab VM you can attach the file as a block device with `sudo losetup --find --show --read-only evidence-disk.img`, image the device with the same `dd` line, and detach it with `sudo losetup -d`. Read-only attach is the software cousin of a write blocker. I did not run this variant.

**Write the form.** Fill this in for the exercise, with placeholders for names and a case number you invent. Times in one time zone, written down.

| Field | Entry |
|---|---|
| Case or exercise ID | LAB-0001 |
| Item | `evidence-disk.img`, 1 048 576 bytes, created by me for this exercise |
| Source and location | `~/forensics-lab` on the lab VM |
| Collected by (name, title) | Your name, Student |
| Date, time, time zone | the date you ran it, in UTC |
| Method and tool, version | `dd` (coreutils 9.7), `bs=4096 conv=noerror,sync` |
| Source hash (SHA-256) | the value from step 2 |
| Image hash (SHA-256) | the value from step 4 |
| Verification | hashes match; `cmp` identical; source re-hashed OK |
| Errors | none |

Custody log, one row per hand-off:

| Item | Released by | Received by | Date and time (UTC) | Purpose | Storage |
|---|---|---|---|---|---|
| `image.dd` (master) | You | You (sealed copy) | now | keep as master | read-only, `chmod a-w image.dd` |
| `working-copy.dd` | You | You (examiner) | now | analysis | `~/forensics-lab` |

Then answer in one line each: which file would you hand to someone else, and which hash would they check it against? What would you write on the form if step 5 had failed?

## Build, break, detect, evade, defend

**Build.** The files above, with the hashes saved.

**Break.** Change a byte of `image.dd` (copy it first) and rerun step 4. The comparison fails. Now do it the careless way: change the file and also overwrite the saved hash file. Notice that the check passes. A hash stored beside the evidence proves nothing against someone who can edit both.

**Detect.** Keep the hash somewhere the person handling the evidence cannot edit: on the form, with a second person, or signed ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md), exercise 3). RFC 3227 suggests generating checksums and cryptographically signing the collected evidence "where feasible".

**Evade, in words only.** An intruder who knows investigators will image the disk can plant a program that wipes it when it sees the network cut, or tamper with tools on the box. That is why the standards say not to trust the system's own programs and not to cut the network blindly.

**Defend.** Collect from volatile to less volatile, from a known-good toolkit, with a record at every step, and keep the master sealed.

## Checkpoint

Without looking back: list RFC 3227's order and say why disk comes after memory; say why you work on a copy; give NIST's three hash checks in order; say what a matching hash proves and what it cannot; name five fields on a custody form; and say which devices you may examine.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "I'll shut it down to be safe" | Memory and live network state are gone | RFC 3227: do not shut down until collection is done |
| "I'll just plug the drive in and look" | The operating system may write to it | Use a write blocker, or attach read-only |
| "The copy looks the same" | Only a hash comparison shows it | `sha256sum` source and image |
| "I stored the hash next to the file" | Whoever edits one can edit both | Record it on the form or sign it |
| "A file copy is an image" | It misses deleted data and slack space | NIST: bit stream image |
| "The hash proves it is authentic" | It proves the copy matches the source at that moment | The custody record covers the rest |
| "SHA-1 is what NIST says to use" | That is the 2006 text; it is dated | Current NIST pages for approved algorithms |
| "I'll examine my friend's laptop for him" | Without written authority you may be breaking the law | Authorization first; ask a lawyer |

## Claims register

Read on 2026-11-07 with read-only requests, or run locally as stated. "Read" means I read the page or PDF text. "Search summary" means only a search result summary, which is marked **est.**

| Claim | Source | Status |
|---|---|---|
| RFC 3227 (D. Brezinski and T. Killalea, February 2002, BCP 55) lists the order of volatility: registers and cache; routing table, ARP cache, process table, kernel statistics, memory; temporary file systems; disk; remote logging and monitoring data; physical configuration and network topology; archival media | [RFC 3227](https://www.rfc-editor.org/rfc/rfc3227) | Read |
| RFC 3227 says do not shut down before collection, do not trust the system's programs, do not run programs that change every file's access time such as `tar`, and that cutting the network can trigger deadman switches; it suggests checksums and signing; it describes custody records; it lists admissible, authentic, complete, reliable, believable | [RFC 3227](https://www.rfc-editor.org/rfc/rfc3227) | Read |
| NIST SP 800-86 (Kent, Chevalier, Grance, Dang, August 2006) is listed as final, with no revision or withdrawal noted on its page; takes an IT, not law enforcement, view; says it is not legal advice | [NIST CSRC SP 800-86](https://csrc.nist.gov/pubs/sp/800/86/final) | Read |
| SP 800-86 four phases (collection, examination, analysis, reporting); bit stream image definition, image then label, store and analyze the copy; document the steps; hash original before, copy after, original again; write blockers; custody log; volatility priority with log-file caveat; MD5 and SHA-1 named, SHA-1 advised for federal agencies in 2006 | [SP 800-86 PDF](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-86.pdf) | Read (text extracted from the PDF) |
| NIST SP 800-101 Rev. 1 (Ayers, Brothers, Jansen, May 2014) covers mobile device forensics: validation, preservation, acquisition, examination, analysis and reporting; supersedes the 2007 edition. Mobile devices are out of scope here | [NIST CSRC SP 800-101r1](https://csrc.nist.gov/pubs/sp/800/101/r1/final) | Search summary, **est.** |
| SWGDE Best Practices for Computer Forensic Acquisitions 17-F-002-2.0 (15 June 2023): hardware or software write blockers when possible; hash with a NIST-approved algorithm; documentation fields; custody at transfer; deviation allowed if documented; not legal advice | [SWGDE 17-F-002-2.0](https://www.swgde.org/wp-content/uploads/2024/03/2023-06-15-SWGDE-Best-Practices-for-Computer-Forensic-Acquisitions-17-F-002-2.0.pdf) | Read (text extracted from the PDF) |
| ISO/IEC 27037:2012 title, scope and the 2018 review confirmation; a reseller shows a review stage in December 2023 | [ISO 27037](https://www.iso.org/standard/44381.html) and national catalog listings | Search summary, **est.** (ISO page returned 403 to my fetch; paid text not read) |
| ACPO Good Practice Guide for Digital Evidence: the 2012 version, hosted by the NPCC after ACPO closed in 2015; principle 1 wording (no action should change data that may be relied on in court) | search results quoting a BCS slide deck and a journal paper | Search summary, **est.** |
| ACPO principles 2 to 4 as summarized above | search summaries | **est.** |
| The exercise commands print the outputs shown: matching source and image hashes, `cmp` identical, a different hash after a one-bit change at byte position 1001 | run on 2026-11-07, GNU coreutils 9.7 | Observed |
| The `losetup` variant works as described | not run | **est.** |
| The 75 minute estimate | my guess | **est.** |

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 2: Defend and detect](Contents.md#track-2-defend-and-detect) > Digital forensics foundations

Previous: [Open firmware and trustworthy hardware](Open-Firmware-and-Trustworthy-Hardware-coreboot-Heads-Nitrokey-and-Vendors-That-Ship-the-Intel-ME-Disabled.md)

In this track: [Track 2: Defend and detect](Contents.md#track-2-defend-and-detect), 36 pages

- Network and host defense: [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md) / [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md) / [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) / [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md) / [Plan for failure: blast radius and assuming breach](Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md) / [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md) / [Attack surface map: layer by layer](Attack-Surface-Map-Layer-by-Layer.md) / [The DMZ and hardening an internet-facing host](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md) / [DMZ hardening checklist](DMZ-Hardening-Checklist.md)
- Deception and honeypots: [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md) / [What deception is](Deception-and-Honeypots-What-Deception-Is.md) / [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) / [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md) / [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md) / [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) / [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md) / [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md) / [Anatomy of a cloud honeypot](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md) / [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md) / [Read what arrived: Cowrie logs](Deception-and-Honeypots-Read-the-Sensor-Logs.md)
- Detection and monitoring: [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md) / [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) / [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) / [Wazuh SIEM and data pipelines](Wazuh-SIEM-and-Data-Pipelines.md) / [Detecting Tor, I2P and VPN on a network](Detecting-and-Managing-Tor-I2P-and-VPN-on-a-Network-the-Defenders-View.md) / [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) / [Multiple sites and identity](Multiple-Sites-and-Identity.md) / [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) / [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) / [Grafana basics from a blank page](Grafana-Basics-From-a-Blank-Page.md) / [Grafana dashboards](Grafana-Dashboards.md) / [Lab: synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md) / [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) / [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md)
- Device and credential security: [Open firmware and trustworthy hardware](Open-Firmware-and-Trustworthy-Hardware-coreboot-Heads-Nitrokey-and-Vendors-That-Ship-the-Intel-ME-Disabled.md)
- Digital forensics: **Digital forensics foundations**

Related pages:

- [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md)
- [Build your own mini SOC](Build-Your-Own-Mini-SOC.md)
- [Lab: synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md)
- [Grafana dashboards](Grafana-Dashboards.md)
<!-- END GENERATED PAGE NAV bottom -->
