# File integrity and alerting: Tripwire, AIDE, Wazuh FIM, auditd, fail2ban and friends

Lesson D3 of the network and host defense track, and a foundations side page to [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) and [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md). Read it after those two, and after [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) if "hash" and "signature" are still blurry.

The track has four lessons. D1 is [Packet filters compared: iptables, nftables, UFW and pf](Packet-Filters-Compared-iptables-nftables-ufw-pf.md), D2 is [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md), this is D3, and D4 is [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md). Those three pages were written at the same time as this one, so their links may not resolve until they merge.

Next: [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md), where the same watching idea is turned into bait.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the Bash parts of the free path were run once on Linux; everything else was not.** On **2026-10-22** the author ran the Bash scripts and the `ssh-keygen` and `sha256sum` commands below on a Debian-based Linux machine (GNU Bash 5.2, GNU coreutils 9.7, GNU Awk 5.2, OpenSSH 10.3, systemd 257), as an ordinary user with no `sudo`, in a scratch folder, and pasted trimmed output from those runs. **Not run:** every PowerShell script and command (written from Microsoft's documentation and checked by reading only, marked **est.**), anything on Windows or macOS, AIDE, Tripwire Open Source, Wazuh, auditd, osquery and fail2ban (none is installed on the author's machine and none is installed here by `sudo`), and the systemd and mail or webhook examples. Those parts are written from each project's own pages (listed in the [claims register](#claims-register)) and say so where it matters. The commercial Tripwire product pages answered the author's read-only requests with an access error on 2026-10-22, so what this page says about the commercial product is **est.** Output varies with your versions; trust your terminal over this page.

> **Prerequisites.** You can open a terminal and run a command ([The terminal and your first script](Terminal-and-Your-First-Script.md)), you know what a hash is ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#hashing-a-fingerprint-not-a-lock)) and what a log line and an alert are ([Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md)). Bash, Python 3 and OpenSSH on your own computer for the hands-on part, or PowerShell if you use Windows. About three hours for the reading and the free exercises (est.); the optional real-tool exercise adds about an hour (est.).

## What you will be able to do

- Say what file integrity monitoring (FIM) is, what it can and cannot tell you, and why a baseline is its core idea.
- Choose what to watch (binaries, configuration, startup files) and what to leave out (logs, caches, temporary files), and say what noise costs.
- Name six ways an attacker defeats a file integrity monitor and one control for each.
- Tell Tripwire, AIDE, Wazuh's file integrity module, auditd and osquery apart: what each one answers, and where it keeps its data.
- Explain what fail2ban does, why a log-driven ban is rate limiting after the fact, and where it sits next to the firewall and rate-limit lessons.
- Build a tiny file integrity monitor in a scratch folder, change, add and delete files, read the differences, write an alert line a detection rule can read, then forge the baseline and defend it.
- Say what every alert needs before you switch it on: an owner, a first step, and a way to tune it.

## Where the project already touches this (and the gaps)

- **Wazuh and its file integrity module** are named in [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md#wazuh-piece-by-piece). The stage 2 design lists file integrity on `/etc/twingate`, `/etc/ssh` and `/etc/sudoers.d` among the planned host checks (design document, read 2026-10-22). The Grafana page says the agent configuration that watches those paths is **not built**, and that only the dashboard panel exists ([Grafana dashboards](Grafana-Dashboards.md)).
- **auditd** is installed on the connectors by the cloud-init template in `modules/twingate-bootstrap`, with seven file rules (each also written with an arch=b32 twin on x86_64) and a Wazuh `<localfile>` block that reads `/var/log/audit/audit.log`. It is opt-in, off by default and never applied to a real machine. Those rules are written in the `-a always,exit` form that the `auditctl` manual page recommends over the deprecated `-w` watch form (changed in #235); the [auditd section](#auditd-who-did-what) below shows them and what each one means.
- **Tripwire, AIDE, osquery and fail2ban** appear nowhere else in the wiki. The word "tripwire" does appear in the deception pages, as a decoy that rings when touched; that is a different idea from the one here, and [Where this meets deception](#where-this-meets-deception) below ties the two together.
- **Droplet hardening** lists audit logging as planned for stage 2 ([Droplet hardening](Droplet-Hardening.md)).

## What file integrity monitoring is, and why

A **file** on a computer is just bytes. If an attacker gets in, they usually change some: they replace a program with one that hides them, add a key to a login file, edit a configuration to open a door, or drop a script that starts at every boot (**persistence**: a way to stay in after a restart). **File integrity monitoring** (FIM) answers one question over and over: *is this file still the file I expected?*

It works in two steps, and every tool in this lesson has both:

1. **Take a baseline.** Walk the files you care about, record a fingerprint (a hash, see [Hashing](Hashing-Encryption-and-Keys.md)) and some attributes (size, owner, permissions, times) of each, and store the result as a **baseline** or **database**. This is the "known good" picture.
2. **Compare later.** Walk the same files again, compare with the baseline, and report what was **added**, **changed** or **removed**.

The AIDE manual states the reasoning well. After a break-in, an administrator "may begin by examining the system using system tools like ls, ps, netstat, and who --- the very tools most likely to be trojaned" (AIDE manual, aide.github.io, read 2026-10-22). Dates and sizes can be faked; a cryptographic checksum is much harder to fake. The same manual is honest about the limit: AIDE "can not provide absolute sureness about change in files", because "AIDE's binary and/or database can also be altered". Hold on to that sentence. The whole second half of this lesson is about it.

What FIM is **good** at: finding that something changed, including when nothing else was watching (a changed `sshd_config`, a new file in `/etc/cron.d`, a replaced binary), and giving change management an audit trail ("this file changed at this time, and we did or did not make that change").

What FIM is **not**: it does not stop anything (it only reports), it does not say *why* a file changed (a patch and an attack look the same until someone checks), and it says nothing about a change in memory, in a database, or in a file you did not list.

## What to watch, and what to leave alone

The AIDE manual gives the rule of thumb: the database should hold "key system binaries, libraries, header files, all files that are expected to remain the same over time", and "probably should not contain information about files which change frequently like log files, mail spools, proc filesystems, user's home directories, or temporary directories" (read 2026-10-22).

| Watch (change is rare, and means something) | Leave out or watch loosely (change is constant) |
|---|---|
| Programs and libraries: `/usr/bin`, `/usr/sbin`, `/bin`, `/sbin`, `/lib*` | Logs under `/var/log`, mail spools, caches |
| System configuration: `/etc` (login, sudo, SSH, cron, systemd units) | Temporary folders, browser caches, build output |
| Startup and persistence spots: `/etc/cron*`, `/etc/systemd/system`, shell startup files, `authorized_keys` files | Home directories as a whole (watch only the startup files and key files in them) |
| The kernel and boot files under `/boot` | `/proc`, `/sys`, `/dev` (not real files) |
| Your own application's configuration | Databases and anything else an application writes all day |

Two reasons to be strict about this. **Noise:** a monitor that reports forty harmless changes a day teaches people to stop reading (see [alert fatigue](#alert-fatigue-the-discipline) below). **Cost:** hashing every file is slow; on a small server a full scan of everything is a real load.

Package updates are the usual source of "expected" changes. When you patch, the monitor will report the replaced programs. The routine is: patch, check, read the report, confirm that every change is a package you meant to update, then refresh the baseline. Tripwire's README says exactly this: "When an expected change occurs, such as upgrading a package, the baseline database can be updated to the new known-good state" (read 2026-10-22). Your package manager also keeps its own record of file checksums that it can verify (est.: `debsums` on Debian and Ubuntu, `rpm -V` on Red Hat families; neither was read or run for this page).

## How an attacker attacks the monitor

A monitor is a program that runs on the machine it watches, reads a database kept on that machine, and tells you what it found. Each of those three facts is a place to attack. This table is the core of the lesson.

| Attack | What the attacker does | The control |
|---|---|---|
| **Update the baseline** | Change a file, then regenerate (or edit) the database so the change becomes "normal". Exercise 5 does this to the toy monitor. | Keep the database where the machine's root user cannot rewrite it: read-only media, another machine, or a signed copy. AIDE's manual says to move the new database to "read-only media" and to keep the binary and config there too. |
| **Tamper with the monitor** | Replace the checker, edit its config so it ignores their folder, or stop the service or timer. | Keep the checker and config off the watched machine or on read-only media; watch the monitor's own files; alert when a check is *missing*, not only when it finds something (a heartbeat). |
| **Timestomp** | Set the file's modified time back so a quick `ls -l` or an mtime-only check sees nothing. MITRE ATT&CK lists it as the technique "Indicator Removal: Timestomp" ([ATT&CK page](https://attack.mitre.org/techniques/T1070/006/)). | Compare content hashes, not only times and sizes (Exercise 3). |
| **Offline modification** | Boot the disk from another system, or edit a virtual disk image, so the running monitor never sees the change happen. | Compare against a baseline kept elsewhere; for high value machines, check from outside (est.: a trusted boot environment or measured boot). A scheduled check can still catch the result. |
| **Change and revert between scans** | Edit a file, use it, put it back before the next scheduled scan. Wazuh's default scheduled scan interval is 43200 seconds (12 hours; Wazuh reference, read 2026-10-22). | Real-time watching for the few files that matter, plus a record of *who* touched them (auditd, who-data). |
| **Bury it in noise** | Make many harmless-looking changes so the real one is lost, or trip a "stop alerting on files that change too often" setting. Wazuh's `auto_ignore` option does exactly that: after a file changes `frequency` times within `timeframe` seconds the manager "generates no more alerts" for it until the window ends (Wazuh reference, read 2026-10-22). It is off by default. | Leave such suppressions off for files that should almost never change; keep the watch list small enough that a change is rare. |
| **Forge the report** | A file name containing a newline and a fake log line can make a careless monitor write a second, forged alert. | Escape untrusted text (file names are attacker-controlled) before it goes into a log. The toy monitor does this; Exercise 2 shows it. |

One more, for completeness: a **rootkit** (malware that hides inside the operating system) can make the kernel lie to every program on the machine, including the monitor. That is why the AIDE manual keeps coming back to read-only media and to running the check from outside.

## The tools

### Tripwire (open source and commercial)

**Tripwire Open Source** is a free, GPL-licensed file integrity checker (the project's `COPYING` file is the GNU General Public License version 2, read 2026-10-22). Its README describes it as "a security and data integrity tool for monitoring and alerting on file & directory changes", based on code contributed by Tripwire, Inc. in 2000. How it works, from that README:

- A **policy file** says which files and directories to watch and which **attributes** to compare (hashes, permissions, ownership). A rule looks like `/etc -> $(IgnoreNone);` (every attribute), and `!/start/point/subdir/to/ignore;` is a stop point (do not scan this).
- **Keys.** Tripwire signs its files. A **site key** signs the configuration and policy files; a **local key** signs the database and reports. Several machines can share a site key but each has its own local key. You make them with `twadmin --generate-keys`.
- **`tripwire --init`** builds the baseline (a `.twd` file, typically under `/var/lib/tripwire`). **`tripwire --check`** compares and writes a report (a `.twr` file); with email reporting set up it also mails the result. **`tripwire --update`** accepts changes into the database, with checkboxes in an editor so you accept only what you recognize.
- The README says that "the OST install script currently does not create any cron jobs", so the scheduled check is yours to set up. A monitor nobody runs is not a monitor.
- On Windows it builds under Cygwin, and the README notes this "does not provide support for monitoring the Registry or any Windows-specific file attributes".

Why the signing matters: a signed database means a change to the database, by anyone without the local key's passphrase, fails verification. It does not help if the attacker has the passphrase or the key file, and it does not help if they replace the whole program. Tripwire is not magic; it is the idea in this lesson with signatures bolted on.

**Tripwire, the commercial product.** Tripwire is also a company, and a commercial line of products (the "Tripwire Enterprise" family) sold for managing integrity and configuration across many machines. The author could not read the vendor's product pages (the requests were refused on 2026-10-22), so features, editions and prices are **est.** and are not described here. The practical point stands without them: the open source tool above and the commercial products share a name and a history, not a price or a feature list. Check the vendor's own page before you compare.

### AIDE

**AIDE** (Advanced Intrusion Detection Environment) is another free file integrity checker, GPL-2.0, in the package lists of Debian, Ubuntu, Red Hat families, openSUSE and the BSDs per its home page (read 2026-10-22). It is smaller and simpler than Tripwire: plain text configuration and a plain database, no signing keys of its own.

- The **config file** has rules. A line like `/etc  MyRule` means "watch `/etc` using the group of checks called MyRule"; a group is built from attribute letters and hashes joined with `+`. The manual lists attributes (`p` permissions, `u` user, `g` group, `s` size, `m` mtime, `c` ctime and more) and hash algorithms (`sha256`, `sha512`, and older ones). A leading `!` excludes a path. The manual's example group `R` is `p+ftype+i+l+n+u+g+s+m+c+md5`.
- **`aide --init`** builds the database. **`aide --check`** compares. **`aide --update`** does a check and writes a *new* database (it never replaces the old one by itself). **`aide --compare`** compares two databases. All four are in the manual.
- **Database handling is where AIDE teaches the lesson.** The manual says the new database "should now be moved to a secure location such as read-only media", together with the config file and the AIDE binary; that "the config file should not be kept on the target machine", because an attacker "could read the config file and alter it" and place a rootkit "in a place that AIDE does not check"; and that replacing the input database "should always be a manual operation. This should not be automated". For many machines it describes running `aide --init` on each and moving the databases to a central host, where you compare with `aide --compare`.
- The manual also recommends that you "verify the signature of a release before using it" (`gpg --verify` on the tarball, or `git verify-tag`). That is the same idea applied to the tool itself.

### Wazuh: the file integrity module (syscheck)

You met Wazuh as the SIEM ([Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md)). Its agent includes a **file integrity monitoring** module, whose configuration section is called `syscheck` (hence `rule.groups:syscheck` in the Grafana page). From Wazuh's documentation (read 2026-10-22):

- It "runs a baseline scan, storing the cryptographic checksum and other attributes of the monitored files", then compares and alerts on a mismatch. It does both **scheduled** and **real-time** scans.
- The checksums live in a local SQLite-based database on the endpoint (on Linux under `/var/ossec/queue/fim/db`) and a per-agent database on the Wazuh server; the two are kept in step. **That means the server holds a second copy of the baseline off the monitored machine**, which is exactly the property the AIDE manual asks you to build by hand.
- The default watched directories are `/etc,/usr/bin,/usr/sbin,/bin,/sbin`, the default scheduled interval is 43200 seconds, and the module is "enabled and pre-configured by default" (reference and "how it works" pages). So on a default agent `/etc/ssh` and `/etc/twingate` would be inside `/etc` and watched (**est.**: this is the author's reading of the defaults, not checked on a running agent).
- **Real time** uses `inotify` on Linux, "only works with directories, not individual files", and is off by default (`realtime="no"`). Real time costs more; use it for the few directories where a 12-hour gap is too long.
- **Who-data** (`whodata="yes"`, also off by default) adds *who* made the change. The reference says the provider defaults to the Linux audit system (`audit`), with an `ebpf` option. That is how FIM and auditd fit together: FIM says *what* changed, audit says *which user and which program*.
- `report_changes` can show a diff of text files; `alert_new_files` controls alerts for created files; `scan_on_start` is "accepted but has no effect" because the module always scans at start to create the baseline.

In this project's stage 2 design the agent is the only thing that dials out; a compromised connector can still tamper with its own local FIM database, which is why the copy on the manager matters. Do not treat the server-side copy as tamper-proof either: whoever controls the manager controls it.

### auditd: who did what

**auditd** is the userspace half of the Linux **audit** system. The kernel can record events (a file opened or written, a program run, an account used) and `auditd` writes them to `/var/log/audit/audit.log`; `ausearch` and `aureport` read them back. FIM tells you a file *is different*. Audit can tell you *which login session and which program changed it*, which is what you need to decide whether the change was a colleague or an intruder.

The `auditctl` manual page (man7.org, read 2026-10-22) says that the old **watch form**, `-w path -p wa -k key`, "is for backwards compatibility and is deprecated due to poor system performance", and that you should "convert watches of this form to the syscall based form". The page gives this pair as "2 ways to express" the same rule:

```text
auditctl -w /etc/shadow -p wa
auditctl -a always,exit -F arch=b64 -F path=/etc/shadow -F perm=wa
```

and likewise `-F dir=/etc/ -F perm=wa` for a whole directory. The project's cloud-init template (`modules/twingate-bootstrap/cloud-init.yaml.tftpl`) used the watch form until #235 and now carries this set, the form the manual recommends (**est., not run**: it needs administrator rights and a machine you own, so it has been checked against the manual page by reading, not loaded into a real auditd; the `key` field is documented as a text label of up to 31 bytes that `ausearch -k` can search):

```text
-a always,exit -F arch=b64 -F path=/etc/passwd -F perm=wa -F key=cah_identity
-a always,exit -F arch=b64 -F path=/etc/group -F perm=wa -F key=cah_identity
-a always,exit -F arch=b64 -F path=/etc/shadow -F perm=wa -F key=cah_identity
-a always,exit -F arch=b64 -F path=/etc/gshadow -F perm=wa -F key=cah_identity
-a always,exit -F arch=b64 -F path=/etc/sudoers -F perm=wa -F key=cah_sudo
-a always,exit -F arch=b64 -F dir=/etc/sudoers.d/ -F perm=wa -F key=cah_sudo
-a always,exit -F arch=b64 -F dir=/etc/twingate/ -F perm=wa -F key=cah_twingate
```

`arch=b64` covers 64-bit programs; the manual says to write a second rule with `arch=b32` on a machine that also runs 32-bit programs. The template writes the `b64` rules everywhere and adds the `arch=b32` twin of every rule (a second file, `61-cah-b32.rules`, made at first boot) only when `uname -m` says `x86_64`. A 32-bit program could otherwise write these files unseen, where the old watch saw every program. It is not added on arm64 (the AWS Graviton connectors) because a `b32` rule may not load on a kernel without 32-bit support, and a load failure would fail the first-boot script closed. So an x86_64 machine has 14 rules and any other has 7; a 32-bit ARM program on a Graviton host would go unseen (**est.**: not run on a real machine). `perm=wa` is the same write and attribute-change pair as `-p wa`, and `dir=` keeps the rule recursive for a directory, as the watch was. Two more honest notes from the same page: audit rules cost something on every system call they apply to, so keep the list short (the template's own comment says per-command auditing is too noisy for the 1 GB droplets); and "on many systems auditd is configured to install an `-a never,task` rule by default" which turns audit processing off, so a rule that is loaded but never fires may simply be switched off.

### osquery: questions on a schedule

**osquery** "exposes an operating system as a high-performance relational database", so you can ask it SQL questions about processes, network connections, file hashes and more (osquery documentation, read 2026-10-22). Two ways it relates to this lesson:

- **Scheduled queries** are the general tool. "Which programs are listening on a port?" run every ten minutes, with the result compared to last time, finds a new listener the way a file hash finds a new binary.
- **FIM in osquery** exists but is "disabled by default". On Linux the `file_events` table uses `inotify`; a separate `process_file_events` table uses the Audit system. You name the files in a `file_paths` section of the config, schedule a `SELECT * FROM file_events`, and, per the docs, "the events are always recorded in real time; the interval is just how often the already recorded events will be logged" (five minutes in their example).

osquery shines when you want one agent to answer many questions across a fleet; it is a larger thing to run than AIDE. This lesson does not run it.

### Two more, in a sentence each

- **Samhain** describes itself as a "file integrity / host-based intrusion detection system" that adds log monitoring, rootkit detection and port monitoring, with central storage of baseline databases for many hosts (project page, la-samhna.de, read 2026-10-22; not run).
- **OSSEC** is described in its README as "a full platform to monitor and control your systems" mixing host-based intrusion detection, log monitoring and SIEM (GitHub README, read 2026-10-22; not run). Wazuh is a separate project that started from this code base (est., general knowledge; not checked on a page for this lesson).

## The neighbors: bans, summaries and plumbing

File integrity is one signal. Three neighbors turn other signals into action. None of them replaces it.

### fail2ban: log-driven bans

**fail2ban** "scans log files like `/var/log/auth.log` and bans IP addresses conducting too many failed login attempts" by "updating system firewall rules to reject new connections from those IP addresses, for a configurable amount of time" (fail2ban README, read 2026-10-22). In config terms ([`jail.conf(5)`](https://github.com/fail2ban/fail2ban/blob/master/man/jail.conf.5)): `maxretry` failures within `findtime` seconds earns a ban of `bantime` seconds, and `ignoreip` lists addresses never to ban.

Think about it as a rate limit built out of three parts: a log (D3-style evidence), a rule (N failures in a window) and a firewall action (D1's packet filter). Compare with [Logs, SIEM and detection basics, Exercise 5](Logs-SIEM-and-Detection-Basics.md#exercise-5-write-a-detection-rule-the-rule-fires): that is the same rule, with a ban attached. Things to keep in mind:

- It acts **after** the failures are written, so it lowers the number of guesses, it does not stop the first few. Its own README says it "cannot eliminate the risk presented by weak authentication" and points to two-factor or key-based login.
- **A ban is an automatic action on untrusted input.** Put your own management address in `ignoreip`, or a typo locks you out of your own server. Anything an outsider can make appear in a log can influence what gets banned (est.: for example a service that logs a client-supplied name or address field); only feed it logs whose source address you trust.
- **Where else could this limit live?** Before the application (a proxy, a load balancer, a CDN), inside the application, in the kernel's connection tracking. Each sees different things and fails differently. That comparison is [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md) (D4; may not resolve until it merges). The packet filter fail2ban talks to is in [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md) (D1; same caveat).

A minimal jail, **est., not run** (needs the package, administrator rights, and a machine you own). Addresses are documentation addresses:

```text
[sshd]
enabled  = true
maxretry = 5
findtime = 10m
bantime  = 1h
ignoreip = 127.0.0.1/8 ::1 192.0.2.10
```

### logwatch and logcheck: a daily summary

Tools of this family read your logs and email you a digest. **logcheck**'s Debian manual page says it "helps spot problems and security violations in your logfiles automatically and will send the results to you periodically in an e-mail" (read 2026-10-22). Its trick is an inverted rule: it knows patterns for *boring* lines, hides those, and shows you the rest (est.: this inversion is from the author's general knowledge; the man page opening was all that was read). logwatch does a similar daily summary (not read; est.). Their value is a cheap "have I looked at my logs today" that needs no SIEM. Their risk is the one every digest has: if it is long, nobody reads it.

### systemd OnFailure and plain mail or webhook alerts

If your check is a program that exits non-zero when it finds something (`fim.sh` below does: exit 1), then **systemd** can run it on a timer and notify you when it fails. The `systemd.unit` manual says `OnFailure=` takes "units that are activated when this unit enters the 'failed' state" (read 2026-10-22). A pair of unit files, accepted by `systemd-analyze verify` on the author's machine (that checks syntax only; the units were never installed or started):

```ini
# fim-check.service
[Unit]
Description=Toy file integrity check
OnFailure=fim-alert@%n.service

[Service]
Type=oneshot
ExecStart=/path/to/fim.sh check /path/to/tree /path/to/baseline.tsv
```

```ini
# fim-alert@.service   (the %i is the name of the unit that failed)
[Unit]
Description=Tell a human that %i failed

[Service]
Type=oneshot
ExecStart=/usr/bin/logger -p user.crit -t fim-alert "unit %i failed"
```

`logger` writes a line to the system log, which your log shipping can pick up. A mail or webhook is the same shape with a different last command. **Treat a webhook address as a secret**: anyone who has it can post to your channel. Read it from an environment variable or your secrets manager ([Doppler and secrets](Doppler-and-Secrets.md)), and keep it out of the command line, where other users can see it in the process list. **Est., not run:**

```bash
printf 'url = "%s"\n' "$ALERT_WEBHOOK_URL" |
  curl -fsS --max-time 10 -K - -H 'Content-Type: application/json' \
       -d '{"text":"fim-check failed on demo-host"}'
```

`printf` is a shell builtin, so the address never appears in a command line; `-K -` tells curl to read its options from standard input.

Also think about **the alert that never arrives**. An attacker who can block your outbound mail or kill the timer gets silence, and silence looks like "all clear". The control is a **heartbeat**: also alert when the expected check did *not* run (est.: most monitoring systems call this a "dead man's switch" or "absence alert").

## Alert fatigue: the discipline

[Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md#alert-fatigue) explains why too many alerts are as bad as none. For anything in this lesson, write the **alert card** *before* you turn the alert on:

| Field | Question | Example for a changed `sshd_config` |
|---|---|---|
| **Owner** | One named person or role who gets it, and who covers when they are away | The platform on-call |
| **First step** | The first thing to do, short enough to follow at 03:00 | Compare the file with the last commit in the configuration repository; if it matches a recent change ticket, close; if not, treat as an incident |
| **Expected rate** | How often it should fire when nothing is wrong | Zero, except on a patch day |
| **Tune path** | How to quiet a false positive without turning the rule off | Add an exact path to the ignore list, with a note and a date; review the list monthly |
| **Heartbeat** | How you will know the check itself stopped | An alert if no check has reported in 36 hours (est. value) |

A rule that nobody owns, or that has fired fifty times without anyone acting, is not a control. Fix it or remove it. This is the same rule as the one in the logs lesson, applied to FIM: if the baseline is full of noise, shrink the watch list until a change is rare.

## Windows: the same ideas, other names

This section is **concept level and est. unless marked**: the author did not run Windows tools for this lesson.

- **Hash a file:** `Get-FileHash -Algorithm SHA256` is the PowerShell version of `sha256sum` (used in [Hashing](Hashing-Encryption-and-Keys.md)). The toy monitor in `fim.ps1` uses it.
- **Audit file access:** Windows records file access in the Security log only if the file or folder has a **SACL** (system access control list: an audit setting on the object) and the **Audit File System** policy is on. Microsoft's page for event **4663** ("An attempt was made to access an object") says the event "generates only if object's SACL has required ACE to handle specific access right use", and that it differs from **4656** ("A handle to an object was requested") because 4663 shows the access right was actually used (Microsoft Learn, read 2026-10-22). That pair is the closest match to an auditd file rule.
- **Wazuh on Windows:** the agent's FIM module watches folders and, on Windows, registry keys too; the Wazuh documentation notes that from 4.13.0 it only watches local file systems on Windows, not network shares (read 2026-10-22).
- **Other options (est., not read):** Sysmon (a free Microsoft Sysinternals tool) can log file creation and a change to a file's creation time, which is how timestomping shows up on Windows; and `sfc /verifyonly` checks protected system files against Windows' own copies.

## Free path: a lab in a scratch folder

Everything below runs in a scratch folder you make, on files you invent. **Never point any of this at a real system folder** (`/etc`, `/usr`, `C:\Windows`, your home directory). The scripts refuse any folder that has no `.fim-lab` marker file, as a guard, but the marker is a seat belt, not a reason to be careless. Nothing is sent anywhere.

Make and enter a scratch folder:

```bash
LAB="$(mktemp -d)" && cd "$LAB"      # remembered in $LAB; delete it at the end
```

PowerShell (**est.**, not run):

```powershell
$d = Join-Path ([IO.Path]::GetTempPath()) ("fimlab-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $d | Out-Null; Set-Location $d
```

Save these scripts into that folder (copy each block into a file with the name in its first comment line). Read each once before you run it. They are short on purpose, so you can see everything a monitor really does: walk, hash, store, compare.

**`mktree.sh`** builds a toy tree:

```bash
#!/usr/bin/env bash
# mktree.sh - builds a toy tree called "tree" in the current folder. Everything is invented.
# The .fim-lab marker is how fim.sh knows this folder is a lab and not a real system folder.
set -eu
mkdir -p tree/etc tree/bin tree/data tree/tmp
: > tree/.fim-lab
printf 'listen_port=8080\nadmin_user=demo\n'        > tree/etc/app.conf
printf 'key-line-one demo\n'   > tree/etc/authorized_keys.demo
printf '#!/bin/sh\necho hello from the toy tool\n'  > tree/bin/tool.sh
chmod 755 tree/bin/tool.sh
printf 'customer list v1\n'                         > tree/data/list.txt
printf 'started\n'                                  > tree/data/app.log
printf 'scratch\n'                                  > tree/tmp/cache.bin
echo "built tree with $(find tree -type f ! -name .fim-lab | wc -l) files"
```

**`fim.sh`** is the monitor. It uses GNU `stat` (`-c`), so on macOS install GNU coreutils or use the PowerShell version:

```bash
#!/usr/bin/env bash
# fim.sh init|check TREE DB - a toy file integrity monitor for a scratch folder.
#   init  writes DB: one line per file: sha256, mode, size, path (tab separated).
#   check re-reads TREE, compares with DB, prints "added", "changed" or "removed" lines.
#         Exit 0 = no differences, 1 = differences, 2 = refused or broken.
# It only runs on a folder that holds a .fim-lab marker file, so it cannot be pointed at /etc.
# Paths are written with printf %q so a file name holding a newline or an escape code cannot
# forge a second line in the database or in anyone's log. GNU stat (-c) is assumed.
# Skipped on purpose (noise): *.log files and anything under a tmp/ folder.
set -eu
mode=${1:-}; tree=${2:-}; db=${3:-}
[ -n "$mode" ] && [ -n "$tree" ] && [ -n "$db" ] || { echo "usage: fim.sh init|check TREE DB" >&2; exit 2; }
[ -f "$tree/.fim-lab" ] || { echo "refusing: $tree has no .fim-lab marker (not a lab folder)" >&2; exit 2; }

snapshot() {
  ( cd "$tree" && find . -type f ! -name .fim-lab -print0 | LC_ALL=C sort -z |
    while IFS= read -r -d '' f; do
      case $f in *.log|*/tmp/*) continue ;; esac
      printf '%s\t%s\t%s\t%s\n' "$(sha256sum < "$f" | cut -d' ' -f1)" \
        "$(stat -c %a "$f")" "$(stat -c %s "$f")" "$(printf '%q' "$f")"
    done )
}

case $mode in
  init)
    snapshot > "$db"
    echo "baseline: $(wc -l < "$db") files recorded in $db"
    ;;
  check)
    [ -s "$db" ] || { echo "refusing: $db is missing or empty" >&2; exit 2; }
    new=$(mktemp); trap 'rm -f "$new"' EXIT
    snapshot > "$new"
    out=$(awk -F'\t' '
      NR == FNR { oh[$4] = $1; om[$4] = $2; next }
      { seen[$4] = 1
        if (!($4 in oh))        print "added\t"   $4
        else if (oh[$4] != $1)  print "changed\t" $4 "\tcontent"
        else if (om[$4] != $2)  print "changed\t" $4 "\tmode" }
      END { for (p in oh) if (!(p in seen)) print "removed\t" p }' "$db" "$new" | LC_ALL=C sort)
    if [ -n "$out" ]; then printf '%s\n' "$out"; exit 1; fi
    echo "clean: no differences from the baseline"
    ;;
  *) echo "usage: fim.sh init|check TREE DB" >&2; exit 2 ;;
esac
```

**PowerShell versions** (**est., not run**; Windows has no Unix mode bits, so `fim.ps1` compares content only, and its database format is not the same as `fim.sh`'s). `mktree.ps1`:

```powershell
# mktree.ps1 - builds a toy folder called "tree" in the current folder. Everything is invented.
# The .fim-lab marker is how fim.ps1 knows this folder is a lab and not a real system folder.
$ErrorActionPreference = 'Stop'
foreach ($d in 'tree\etc', 'tree\bin', 'tree\data', 'tree\tmp') {
  New-Item -ItemType Directory -Force -Path $d | Out-Null
}
New-Item -ItemType File -Force -Path 'tree\.fim-lab' | Out-Null
Set-Content -Path 'tree\etc\app.conf' -Value @('listen_port=8080', 'admin_user=demo')
Set-Content -Path 'tree\etc\authorized_keys.demo' -Value 'key-line-one demo'
Set-Content -Path 'tree\bin\tool.sh' -Value 'echo hello from the toy tool'
Set-Content -Path 'tree\data\list.txt' -Value 'customer list v1'
Set-Content -Path 'tree\data\app.log' -Value 'started'
Set-Content -Path 'tree\tmp\cache.bin' -Value 'scratch'
$n = (Get-ChildItem tree -Recurse -File -Force | Where-Object { $_.Name -ne '.fim-lab' }).Count
"built tree with $n files"
```

`fim.ps1`:

```powershell
# fim.ps1 -Mode init|check -Tree FOLDER -Db FILE - a toy file integrity monitor for a scratch folder.
#   init  writes Db: one line per file: sha256, size, path (tab separated).
#   check re-reads Tree, compares with Db, prints "added", "changed" or "removed" lines.
#         Exit 0 = no differences, 1 = differences, 2 = refused or broken.
# It only runs on a folder that holds a .fim-lab marker file, so it cannot be pointed at C:\Windows.
# Control characters in a file name are replaced with ? so a name cannot forge a second line.
# Windows has no Unix mode bits, so this version compares content only (permissions are ACLs).
# Skipped on purpose (noise): *.log files and anything under a tmp folder.
param(
  [Parameter(Mandatory)][ValidateSet('init', 'check')][string]$Mode,
  [Parameter(Mandatory)][string]$Tree,
  [Parameter(Mandatory)][string]$Db
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath (Join-Path $Tree '.fim-lab'))) {
  [Console]::Error.WriteLine("refusing: $Tree has no .fim-lab marker (not a lab folder)"); exit 2
}
$root = (Resolve-Path -LiteralPath $Tree).Path

function Get-Snapshot {
  Get-ChildItem -LiteralPath $root -Recurse -File -Force |
    Where-Object { $_.Name -ne '.fim-lab' -and $_.Name -notlike '*.log' -and $_.FullName -notmatch '[\\/]tmp[\\/]' } |
    Sort-Object FullName |
    ForEach-Object {
      $rel = ($_.FullName.Substring($root.Length).TrimStart('\', '/')) -replace '\\', '/'
      [pscustomobject]@{
        Hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower()
        Size = $_.Length
        Path = ($rel -replace '[\x00-\x1f]', '?')
      }
    }
}

if ($Mode -eq 'init') {
  $rows = @(Get-Snapshot | ForEach-Object { "$($_.Hash)`t$($_.Size)`t$($_.Path)" })
  Set-Content -LiteralPath $Db -Value $rows -Encoding UTF8
  "baseline: $($rows.Count) files recorded in $Db"
  exit 0
}

if (-not (Test-Path -LiteralPath $Db) -or (Get-Item -LiteralPath $Db).Length -eq 0) {
  [Console]::Error.WriteLine("refusing: $Db is missing or empty"); exit 2
}
$old = @{}
foreach ($line in Get-Content -LiteralPath $Db) {
  $p = $line -split "`t", 3
  $old[$p[2]] = $p[0]
}
$seen = @{}
$findings = @()
foreach ($f in Get-Snapshot) {
  $seen[$f.Path] = $true
  if (-not $old.ContainsKey($f.Path)) { $findings += "added`t$($f.Path)" }
  elseif ($old[$f.Path] -ne $f.Hash) { $findings += "changed`t$($f.Path)`tcontent" }
}
foreach ($path in $old.Keys) {
  if (-not $seen.ContainsKey($path)) { $findings += "removed`t$path" }
}
if ($findings.Count -gt 0) { $findings | Sort-Object; exit 1 }
'clean: no differences from the baseline'
exit 0
```

### Exercise 1: build a toy tree and take a baseline

**Predict.** The tree has six files. Which of them will the baseline hold? (Look at the "Skipped on purpose" line in `fim.sh`.)

**Do (Bash).**

```bash
bash mktree.sh
bash fim.sh init tree baseline.tsv
bash fim.sh check tree baseline.tsv; echo "exit=$?"
mkdir offbox && (sha256sum baseline.tsv > offbox/baseline.sha256) && chmod a-w offbox/baseline.sha256
```

The last line saves a fingerprint of the baseline file in a second folder and makes that file read-only. It is a stand-in for "a copy somewhere the monitored machine cannot rewrite"; Exercise 6 uses it.

**Do (PowerShell, est.).**

```powershell
.\mktree.ps1
.\fim.ps1 -Mode init -Tree tree -Db baseline.tsv
.\fim.ps1 -Mode check -Tree tree -Db baseline.tsv; "exit=$LASTEXITCODE"
New-Item -ItemType Directory offbox | Out-Null
(Get-FileHash baseline.tsv -Algorithm SHA256).Hash.ToLower() | Set-Content offbox\baseline.sha256
```

**Check.** Output from the Bash run on 2026-10-22:

```text
built tree with 6 files
baseline: 4 files recorded in baseline.tsv
clean: no differences from the baseline
exit=0
```

Four files, not six: `app.log` (a log) and `tmp/cache.bin` (under `tmp/`) were skipped as noise. `head -c 80 baseline.tsv` shows the shape: a 64-character hash, a tab, the permissions (`755`), the size and the path.

**Undo.** Nothing outside the scratch folder changed. `rm -r "$LAB"` at the end of the page removes everything.

### Exercise 2: change, add and delete, and read the differences

**Predict.** You will edit `etc/app.conf`, make `bin/tool.sh` world-writable, add `bin/new-tool`, delete `data/list.txt`, append to the skipped log, and append to the skipped cache file. Which of the six actions will the check report?

**Do (Bash).**

```bash
printf 'listen_port=8080\nadmin_user=demo\nadmin_user=intruder\n' > tree/etc/app.conf
chmod 666 tree/bin/tool.sh
printf 'x\n' > tree/bin/new-tool
rm tree/data/list.txt
echo noise >> tree/data/app.log
echo more  >> tree/tmp/cache.bin
bash fim.sh check tree baseline.tsv; echo "exit=$?"
bash fim.sh check /etc baseline.tsv; echo "exit=$?"
```

PowerShell (est.): the same changes with `Set-Content`, `New-Item`, `Remove-Item`; skip the `chmod` (no mode bits in `fim.ps1`), then `.\fim.ps1 -Mode check -Tree tree -Db baseline.tsv`.

**Check.** The Bash run printed:

```text
added	./bin/new-tool
changed	./bin/tool.sh	mode
changed	./etc/app.conf	content
removed	./data/list.txt
exit=1
refusing: /etc has no .fim-lab marker (not a lab folder)
exit=2
```

Four of six: the two skipped files did not show, which is the point of an ignore list and also its danger: **an attacker's file in a skipped folder is invisible**. Look at what you ignored and ask who can write there. The mode change is reported separately from content, and the exit code is `1` when something differs, `0` when clean, `2` when the tool refuses.

Now the forgery check. File names are chosen by whoever creates the file:

```bash
touch "tree/data/evil
Oct 22 03:00:00 demo-host fimcheck[1]: ALERT action=changed path=.x detail=forged"
bash fim.sh check tree baseline.tsv | grep evil
```

```text
added	$'./data/evil\nOct 22 03:00:00 demo-host fimcheck[1]: ALERT action=changed path=.x detail=forged'
```

`printf '%q'` turned the newline into the two characters `\n`, so the hostile name stays on one line and cannot pose as a second alert. Without that, an attacker could write fake lines into your log just by creating a file.

**Undo.** `rm tree/data/evil*` only. Leave the other changes in place: Exercises 3 to 5 use them. (To start over, `rm -r tree` and run `bash mktree.sh` and `fim.sh init` again.)

### Exercise 3: why hashes, not times

**Predict.** An attacker replaces `etc/authorized_keys.demo` with different text of the same length, then sets the file's modified time back to what it was. Will a check that compares only size and modified time notice? Will `fim.sh`?

**Do (Bash).**

```bash
cp -p tree/etc/authorized_keys.demo ref                          # -p keeps the modified time
printf 'key-line-two evil\n' > tree/etc/authorized_keys.demo     # different text, same length (17 characters)
wc -c < tree/etc/authorized_keys.demo; wc -c < ref               # both 18 bytes with the newline
touch -r ref tree/etc/authorized_keys.demo                       # copy the old modified time onto it
stat -c '%s bytes, modified %y' tree/etc/authorized_keys.demo ref
bash fim.sh check tree baseline.tsv | grep authorized
```

**Check.** On 2026-10-22 the two files showed the same size and the same modified time to the nanosecond, and the check still printed `changed	./etc/authorized_keys.demo	content`. That is the reason the AIDE manual puts hashes first: "File dates and sizes can be manipulated". (PowerShell, est.: `(Get-Item f).LastWriteTime = (Get-Item ref).LastWriteTime` sets the time; `fim.ps1` compares hashes.)

**Undo.** Leave it; Exercise 4 reports it too.

### Exercise 4: turn a finding into an alert a rule can read

**Predict.** The logs lesson's `normalize.sh` turns an `sshd` syslog line into one `key=value` shape so one rule can read many sources. If a monitor writes its findings as syslog-style lines, what will it take to feed them to the same kind of rule?

**Do (Bash).** Save `fim-alert.sh` and `fim-normalize.sh`:

```bash
#!/usr/bin/env bash
# fim-alert.sh TREE DB LOGFILE - runs fim.sh check and appends one syslog-style line per finding.
# Line shape (like auth.log): "Oct 22 17:20:11 demo-host fimcheck[4242]: ALERT action=changed path=... detail=..."
# "demo-host" is an invented name on purpose. Exit status is fim.sh's: 0 clean, 1 findings.
set -u
here=$(dirname "$0")
tree=${1:?usage: fim-alert.sh TREE DB LOGFILE}; db=${2:?}; logfile=${3:?}
out=$(bash "$here/fim.sh" check "$tree" "$db"); rc=$?
[ "$rc" -eq 1 ] || { printf '%s\n' "$out"; exit "$rc"; }
stamp=$(date '+%b %e %H:%M:%S')
printf '%s\n' "$out" | while IFS=$'\t' read -r action path detail; do
  printf '%s demo-host fimcheck[%s]: ALERT action=%s path=%s detail=%s\n' \
    "$stamp" "$$" "$action" "$path" "${detail:--}" >> "$logfile"
done
echo "wrote $(printf '%s\n' "$out" | wc -l) alert line(s) to $logfile"
exit 1
```

```bash
#!/usr/bin/env bash
# fim-normalize.sh LOGFILE - turns fimcheck lines into the key=value shape of the logs lesson's normalize.sh.
# Only lines from "fimcheck[...]:" are read; anything else is skipped, never run.
awk -v year="$(date +%Y)" '
  BEGIN { split("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec", m, " "); for (i = 1; i <= 12; i++) mon[m[i]] = i }
  $5 ~ /^fimcheck\[[0-9]+\]:$/ && $6 == "ALERT" {
    # The path is %q-escaped, so a space inside it is written as "\ ". Take everything between
    # " path=" and the last " detail=" instead of splitting on spaces.
    split($7, a, "=")
    path = $0; sub(/^.* ALERT action=[^ ]+ path=/, "", path); sub(/ detail=[^ ]*$/, "", path)
    printf "ts=%04d-%02d-%02dT%sZ src=- source=fim action=fim_%s user=- path=%s\n", year, mon[$1], $2, $3, a[2], path
  }' "$1"
```

```bash
bash fim-alert.sh tree baseline.tsv alerts.log; echo "exit=$?"
cat alerts.log
bash fim-normalize.sh alerts.log
```

PowerShell (**est.**): save `fim-alert.ps1` and run `.\fim-alert.ps1 -Tree tree -Db baseline.tsv -LogFile alerts.log`. There is no PowerShell version of the normalizer here; the awk script is the whole job and a short `-split` loop does the same.

```powershell
# fim-alert.ps1 -Tree FOLDER -Db FILE -LogFile FILE - runs fim.ps1 check and appends one
# syslog-style line per finding. "demo-host" is an invented name on purpose.
param(
  [Parameter(Mandatory)][string]$Tree,
  [Parameter(Mandatory)][string]$Db,
  [Parameter(Mandatory)][string]$LogFile
)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = @(& (Join-Path $here 'fim.ps1') -Mode check -Tree $Tree -Db $Db)
$rc = $LASTEXITCODE
if ($rc -ne 1) { $out; exit $rc }
$stamp = (Get-Date).ToString('MMM d HH:mm:ss', [Globalization.CultureInfo]::InvariantCulture)
foreach ($line in $out) {
  $action, $path, $detail = $line -split "`t"
  if (-not $detail) { $detail = '-' }
  Add-Content -LiteralPath $LogFile -Value "$stamp demo-host fimcheck[$PID]: ALERT action=$action path=$path detail=$detail"
}
"wrote $($out.Count) alert line(s) to $LogFile"
exit 1
```

**Check.** The Bash run, with the process id replaced by `N`, after the changes of Exercises 2 and 3 (five findings: the four from Exercise 2 plus the key file from Exercise 3):

```text
wrote 5 alert line(s) to alerts.log
exit=1
Oct 22 17:18:26 demo-host fimcheck[N]: ALERT action=added path=./bin/new-tool detail=-
Oct 22 17:18:26 demo-host fimcheck[N]: ALERT action=changed path=./bin/tool.sh detail=mode
Oct 22 17:18:26 demo-host fimcheck[N]: ALERT action=changed path=./etc/app.conf detail=content
Oct 22 17:18:26 demo-host fimcheck[N]: ALERT action=changed path=./etc/authorized_keys.demo detail=content
Oct 22 17:18:26 demo-host fimcheck[N]: ALERT action=removed path=./data/list.txt detail=-
ts=2026-10-22T17:18:26Z src=- source=fim action=fim_added user=- path=./bin/new-tool
ts=2026-10-22T17:18:26Z src=- source=fim action=fim_changed user=- path=./bin/tool.sh
ts=2026-10-22T17:18:26Z src=- source=fim action=fim_changed user=- path=./etc/app.conf
ts=2026-10-22T17:18:26Z src=- source=fim action=fim_changed user=- path=./etc/authorized_keys.demo
ts=2026-10-22T17:18:26Z src=- source=fim action=fim_removed user=- path=./data/list.txt
```

The date is today's, yours will differ. The first five lines have the same layout as the `sshd` lines in the logs lesson's `auth.log`: month, day, time, host, `program[pid]:`, message. The last five are the logs lesson's `key=value` shape, with `source=fim`. The logs lesson's `detect.sh` counts `login_failed` events per `src`, so it will **not** fire on these; the exercise is to write a rule in the same style. For example, "three or more `fim_*` actions within a minute" or "any `fim_changed` whose path starts with `./etc/`". You need the `action` and `path` fields, and the idea (a window, a threshold, a quiet period) is the logs lesson's Exercise 5 and 6.

**Undo.** `rm alerts.log`.

### Exercise 5: evade it, by forging the baseline

This is the attacker's move against the **defender's own tool**, in your own scratch folder. Do it to see it; do not do it anywhere else.

**Predict.** An intruder with enough rights to edit `app.conf` can usually edit `baseline.tsv` too, because both sit on the machine. If they change the file and then fix up its line in the baseline, what will `fim.sh check` say about `app.conf`?

**Do (Bash).** Keep a copy of the honest baseline first, then forge the line:

```bash
cp baseline.tsv baseline.orig
python3 -I - <<'PY'
import hashlib
p = 'tree/etc/app.conf'
data = open(p, 'rb').read()
rows = [l.rstrip('\n').split('\t') for l in open('baseline.tsv')]
for r in rows:
    if r[3] == './etc/app.conf':
        r[0], r[2] = hashlib.sha256(data).hexdigest(), str(len(data))
open('baseline.tsv', 'w').write(''.join('\t'.join(r) + '\n' for r in rows))
PY
bash fim.sh check tree baseline.tsv | grep app.conf; echo "grep found: $?"
bash fim.sh check tree baseline.orig | grep app.conf
```

PowerShell (est.): the same edit in a few lines (read the lines, replace the hash and size for `etc/app.conf` with `Get-FileHash` and the file's `.Length`, write the file back).

**Check.** With the forged baseline, `app.conf` disappeared from the report (`grep found: 1` means no line matched; the other changes still show). Against the honest copy, `changed	./etc/app.conf	content` is back. The monitor did its job perfectly and told the truth about a lie. **A monitor is exactly as trustworthy as its baseline.**

**Undo.** `cp baseline.orig baseline.tsv`.

### Exercise 6: defend the baseline, off the machine

**Predict.** Two cheap controls: a fingerprint of the baseline stored where the attacker's account cannot write, and a signature on the baseline made with a key the machine does not hold. Which one stops the forgery in Exercise 5? Which one stops an attacker who has root on the machine and a chance to rewrite the fingerprint file?

**Do (Bash).** First, compare the forged baseline against the fingerprint you saved in Exercise 1:

```bash
python3 -I - <<'PY'            # re-forge the line, as in Exercise 5
import hashlib
p = 'tree/etc/app.conf'; data = open(p, 'rb').read()
rows = [l.rstrip('\n').split('\t') for l in open('baseline.orig')]
for r in rows:
    if r[3] == './etc/app.conf': r[0], r[2] = hashlib.sha256(data).hexdigest(), str(len(data))
open('baseline.tsv', 'w').write(''.join('\t'.join(r) + '\n' for r in rows))
PY
mkdir -p v && cp baseline.tsv v/
(cd v && sha256sum -c ../offbox/baseline.sha256; echo "exit=$?")
```

Then sign the honest baseline with a throwaway key. The key belongs on your **other** machine in real life, not next to the baseline. (This is [Hashing, Exercise 3](Hashing-Encryption-and-Keys.md#exercise-3-a-throwaway-key-pair-a-signature-and-a-tampered-file) applied to the baseline.)

```bash
ssh-keygen -q -t ed25519 -N '' -C demo-throwaway -f demo_key
cp baseline.orig baseline.signed.tsv
ssh-keygen -Y sign -f demo_key -n fim-baseline baseline.signed.tsv
printf 'demo-signer %s\n' "$(cut -d' ' -f1,2 demo_key.pub)" > allowed_signers
ssh-keygen -Y verify -f allowed_signers -I demo-signer -n fim-baseline -s baseline.signed.tsv.sig < baseline.signed.tsv; echo "exit=$?"
ssh-keygen -Y verify -f allowed_signers -I demo-signer -n fim-baseline -s baseline.signed.tsv.sig < baseline.tsv; echo "exit=$?"
```

PowerShell (est.): `(Get-FileHash baseline.tsv).Hash.ToLower()` and compare with the text in `offbox\baseline.sha256`; signing needs the OpenSSH client, as in the hashing lesson.

**Check.** The fingerprint check on the forged copy printed `baseline.tsv: FAILED` and `exit=1`; on the honest copy it printed `baseline.tsv: OK`. The signature check printed `Signing file ...`, then `Good "fim-baseline" signature for demo-signer with ED25519 key SHA256:...` with exit 0 for the honest file, and `Signature verification failed: incorrect signature` and exit 255 for the forged one.

Both controls stop the forgery of Exercise 5. They do not stop an attacker who can rewrite the fingerprint file as well, which is why the second copy has to live somewhere the monitored machine's accounts cannot reach: another machine you reach with a different credential, read-only media you attach only for the check, or a system (like the Wazuh manager) that holds its own copy. The signature has the extra property that the **key stays elsewhere**, so a rewrite of the baseline needs something the attacker does not have. Every extra step still moves the problem; the goal is making the attacker's job harder than your alert's, not making it impossible.

**Undo.** `rm -r v demo_key* allowed_signers baseline.signed.tsv*` (the `offbox` folder is read-only on purpose; `chmod u+w offbox/baseline.sha256` then remove it).

### Exercise 7: the real tools (optional; not run for this page)

The author's machine has no `aide` and no `tripwire`, and installing system packages with `sudo` was out of bounds for this page, so **everything in this exercise is est.** and unrun. Check what you have first:

```bash
command -v aide tripwire auditctl fail2ban-client osqueryi
```

If `aide` is missing, do not install it on your everyday machine. A throwaway container does not touch your system; with Podman (or Docker, rootless; **never mount the Docker socket**) and your own scratch folder:

```bash
podman run --rm -it -v "$LAB:/lab:Z" docker.io/library/debian:stable-slim bash
# inside the container (est.; it needs network to install):
apt-get update && apt-get install -y aide
```

Then, inside the container, write a config that points only at the toy tree (est.: the option names are from the AIDE manual and `aide.conf(5)`; check `man aide.conf` for your version, as options changed across releases):

```text
database_in=file:/lab/aide.db
database_out=file:/lab/aide.db.new
report_url=stdout
MyRule = p+u+g+s+sha256
/lab/tree  MyRule
!/lab/tree/tmp
!/lab/tree/.*\.log$
```

```bash
aide --init  -c /lab/aide.conf        # writes /lab/aide.db.new
mv /lab/aide.db.new /lab/aide.db      # a manual step, as the manual insists
# change, add and delete files in /lab/tree, as in Exercise 2, then:
aide --check -c /lab/aide.conf        # prints added, removed and changed entries
```

**What to compare with the toy.** Does AIDE's report name the same four files? What attribute did it report for the mode change? Where did it keep its database, and how would you protect that file? For **Tripwire Open Source**, the README sequence is `twadmin --generate-keys` (twice), `twadmin --create-cfgfile`, `twadmin --create-polfile`, `tripwire --init`, `tripwire --check`, `twprint` to read a report; building it from source needs a C++ compiler and Perl for its tests. Both stay est. here.

**Undo.** Exit the container (`--rm` removed it). Delete `$LAB`.

### Clean up

When you are done, leave the folder and delete the whole lab. The `offbox` file is read-only on purpose, so give yourself write permission first:

```bash
cd ~ && chmod -R u+w "$LAB" && rm -r "$LAB"
```

PowerShell (est.): `Set-Location ~; Remove-Item -Recurse -Force $d`.

## Optional: Wazuh on a machine of your own

This uses a virtual machine or spare computer you already own, or a cloud machine on your own provider bill. The wiki does not price it; for what this project spends and how it is capped, see [How money works in the cloud](How-Money-Works-in-the-Cloud.md) and `docs/cost.md`. **Teardown first:** know how to remove the agent (`apt remove` of the package you installed, est.) and how to delete the VM before you start, and do not enroll a machine you do not own or are not allowed to manage.

The shape of the exercise: install the agent on a test VM, point it at a manager you control, add a `<directories realtime="yes">` line for **one scratch folder** (never `/etc`), change a file in it, and find the alert in the dashboard under `rule.groups:syscheck`. Then turn on `whodata="yes"` for the same folder and see what extra fields appear. Setup steps are in [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) (an unverified draft). **Not run by the author.**

> **Screenshot to take yourself:** your Wazuh dashboard's file integrity events view.
> Capture: one `changed` event for your scratch folder, with the path and the checksum fields visible.
> Look for: the event time, the path, and (if you turned on who-data) the user.
> Redact: your machine name, addresses, and your manager's address.

## Threat model of the FIM and alerting pipeline

Why the pipeline itself needs guarding, in the shape of [Threat model](Threat-Model.md):

| Asset | Threat | Likelier cause | Control on this page | Residual risk |
|---|---|---|---|---|
| The baseline | Edited so a change looks normal | Attacker has root on the monitored machine | Off-box copy, signature, read-only media | The off-box copy is only as safe as its own host |
| The checker and its config | Replaced, disabled or told to ignore a folder | Same, or a bad update | Keep it off-box; heartbeat alert; watch the checker's own files | A kernel-level rootkit can lie to any local program |
| The alert path | Blocked, flooded, or forged (file names, log lines) | Attacker controls outbound mail, or a filename | Escape untrusted text; heartbeat; more than one channel | You still depend on a human reading it |
| The watch list | Gaps the attacker writes into | Ignore rules for "noisy" folders | Review ignore lists with an owner and a date | A folder you never thought to watch |
| The humans | Alert fatigue: real alerts ignored | Too many low-value alerts | Alert cards: owner, first step, rate, tune path | People leave; cards go stale |
| The production machine | The monitor itself causes load or an outage | Hashing everything, or real-time watching too much | Small watch list; scan off-peak (est.) | Load surprises after a big package update |

## What this tells you about building systems

- **Evidence beats memory.** A baseline turns "I think nobody touched that" into a fact you can check.
- **Separate the judge from the defendant.** A monitor that lives where the attacker lives can be forged. Move the copy of the truth.
- **Small and owned beats large and ignored.** A short watch list with a named owner finds more than a huge one nobody reads.
- **Change management is a security control.** The routine "patch, check, review, refresh baseline" is the same habit as [Enterprise change management](Enterprise-Change-Management-for-Beginners.md).
- **FIM, audit and logs answer different questions.** What changed (FIM), who did it (audit), what the system said about it (logs). Together they let you answer "what happened" instead of guessing.

## Build, break, detect, evade, defend (the local loop)

The same loop as the rest of the project ([Why this exists](Why-This-Exists.md)), on the toy monitor.

**Build.** `fim.sh` and a baseline of four files, with a saved fingerprint of the baseline (Exercise 1).

**Break.** Change a config, a mode, add and delete files (Exercise 2). The monitor says exactly what happened.

**Detect.** The check exits `1`; `fim-alert.sh` writes syslog-style lines; `fim-normalize.sh` turns them into the shape a detection rule reads (Exercise 4). A hash catches the file whose time was faked back (Exercise 3).

**Evade.** Forge the baseline so the changed file looks normal (Exercise 5). Also: change a file inside a folder the ignore list skips; change and revert between scheduled scans. This is described so that you recognize it, and Exercise 5 touches only your own toy.

**Defend.** A fingerprint and a signature of the baseline, kept apart from the machine it describes (Exercise 6); a short watch list; real-time and who-data for the few files that matter; a heartbeat; an alert card for each alert.

**Undo.** Delete the scratch folder.

### Flip the board

**The attacker.** You have root on a machine that runs a file integrity monitor with a local database and a nightly check that emails a report. List three things you would try, and for each name the extra signal that would catch it. Answers below.

<details>
<summary>What to find</summary>

1. **Fix the baseline** after your change. Signal: the database's fingerprint no longer matches the off-box copy; or its modified time is odd. The control is the copy you cannot reach.
2. **Make the report not arrive.** Block outbound mail, or stop the timer. Signal: no check has reported for longer than the usual gap. The control is a heartbeat, and a second channel.
3. **Work between checks.** Do what you came to do and put the files back before the next run. Signal: audit records (who opened or wrote the file, from which session) and real-time events on the few files that matter, which a nightly hash cannot give you.

</details>

## Where this meets deception

The deception track plants bait and waits for a touch. File integrity monitoring is the same watching, pointed at files that are *supposed* to be quiet. The two combine well: a honeyfile that nobody has a reason to open ([Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md)) is a file whose change or deletion, under a FIM rule or an audit rule, is almost never a false positive, which is the property [alert fatigue](#alert-fatigue-the-discipline) asks for. FIM, however, sees *changes*; a plain read of a bait file needs an audit rule or similar, as that lesson explains. And the same weakness applies: if an intruder can edit the monitor's database, they can quiet the bait too.

## Checkpoint

You are done when you can say, without looking:

- What a baseline is, and the two steps of every file integrity tool.
- Four kinds of file to watch and four kinds to leave out, and why a skipped folder is both a feature and a risk.
- Why the baseline and the checker must not live only on the machine they watch, and two ways to protect the baseline.
- The difference between what Tripwire Open Source, AIDE, Wazuh's FIM and auditd each tell you.
- Why a modified time proves nothing, and what a hash adds.
- What fail2ban does, and why its ban is a rate limit that arrives after the failures.
- The five fields of an alert card.
- How a file name could forge a log line, and the one-line control.

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| `refusing: ... has no .fim-lab marker` | The folder is not the one `mktree.sh` made, or you are in the wrong directory | `ls -a tree`; run the scripts from the scratch folder |
| `stat: invalid option` or odd output on macOS | The script uses GNU `stat -c` | Install GNU coreutils, or use the PowerShell version |
| Every check reports every file changed | You baselined, then rebuilt the tree with `mktree.sh` | Run `fim.sh init` again after a rebuild |
| The monitor reports nothing, but you know a file changed | The file is in a skipped folder, or the baseline was edited | Read the skip list; compare the baseline with the off-box copy |
| Hundreds of changed files after patching | A normal package update | Check the changes against the update log, then refresh the baseline |
| Wazuh alerts arrive hours late | The scheduled scan interval is 12 hours by default | Use `realtime` on the few directories that need it |
| An audit rule is loaded and never fires | Audit processing is switched off by a default `never` rule, or the path is wrong | `auditctl -l` and the man page's "disabled by default" note |
| fail2ban banned your own address | No `ignoreip`, or a typo in a password | Add your management address to `ignoreip` before you test |

## Claims register

All read-only requests; retrieved 2026-10-22. "Observed" means the author ran it that day on one Linux machine.

| Claim | Source | Status |
|---|---|---|
| Open Source Tripwire monitors and alerts on file and directory changes, is based on code contributed by Tripwire, Inc. in 2000, and works from a baseline and a policy file | [README](https://raw.githubusercontent.com/Tripwire/tripwire-open-source/master/README.md) | Read; not run |
| Tripwire signs config and policy with a site key, and database and reports with a local key; `twadmin --generate-keys`, `tripwire --init`, `--check`, `--update`; no cron job is created by the installer; the Windows (Cygwin) build lacks Registry support | same README | Read; not run |
| Open Source Tripwire is under the GNU General Public License, version 2 | [COPYING](https://raw.githubusercontent.com/Tripwire/tripwire-open-source/master/COPYING) | Read the first lines |
| Tripwire policy rules, the `$(ReadOnly)` style variables, stop points and rule attributes such as `emailto` and `severity` | [twpolicy(4)](https://raw.githubusercontent.com/Tripwire/tripwire-open-source/master/man/man4/twpolicy.4) | Read parts; not run |
| Commercial Tripwire products, editions, features and prices | Vendor pages | **Not read**: the author's requests were refused on 2026-10-22. **est.**; nothing on this page depends on them |
| AIDE builds a database from regex rules, supports several hash algorithms and attributes, is GPL-2.0, and is packaged in the listed distributions | [aide.github.io](https://aide.github.io/) | Read; not run |
| AIDE's manual advises read-only media for the database, config and binary, that the config should not be on the target machine, that update is manual, that file dates and sizes can be manipulated, that the binary and database can be altered, and describes `--init`, `--check`, `--update` and `--compare` | [AIDE manual](https://aide.github.io/doc/) | Read; not run |
| The AIDE config lines in Exercise 7 (`database_in=file:`, `report_url=stdout`, group syntax) | AIDE manual and `aide.conf(5)` | Option names partly from the manual page text and partly from the author's recollection; **est.**, never run |
| Wazuh FIM: baseline scan, checksums, real-time and scheduled scans, local SQLite database plus per-agent server database, enabled and pre-configured by default, Windows local drives only from 4.13.0 | [FIM overview](https://documentation.wazuh.com/current/user-manual/capabilities/file-integrity/index.html), [How it works](https://documentation.wazuh.com/current/user-manual/capabilities/file-integrity/how-it-works.html) | Read; not run |
| Wazuh `syscheck` options: default directories `/etc,/usr/bin,/usr/sbin,/bin,/sbin`, default `frequency` 43200 seconds, `realtime` and `whodata` default `no` and real time works on directories only, whodata provider `audit` (default) or `ebpf`, `auto_ignore` default `no`, `scan_on_start` has no effect | [syscheck reference](https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/syscheck.html) | Read; not run. Versions change; the defaults on your agent may differ |
| The `-w` watch form of `auditctl` (what the template used before #235) is deprecated "due to poor system performance"; the equivalent `-a always,exit -F arch=b64 -F path=... -F perm=wa` form; the `key` field; the default `-a never,task` rule | [auditctl(8)](https://man7.org/linux/man-pages/man8/auditctl.8.html) | Read; not run |
| The project's cloud-init template uses `-w` watch rules for passwd, group, shadow, gshadow, sudoers, sudoers.d and /etc/twingate/ | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` in this repository | Read; the template has never run on a real machine |
| The stage 2 design lists FIM on `/etc/twingate`, `/etc/ssh` and `/etc/sudoers.d`; the agent configuration for it is not built | `docs/superpowers/specs/2026-10-11-stage-2-logging-design.md` and [Grafana dashboards](Grafana-Dashboards.md) | Read in this repository |
| osquery exposes the operating system as a database; FIM is disabled by default; `file_events` uses inotify on Linux; events are recorded in real time and logged on the schedule interval | [osquery docs](https://osquery.readthedocs.io/en/latest/), [FIM page](https://osquery.readthedocs.io/en/latest/deployment/file-integrity-monitoring/) | Read; not run |
| fail2ban scans logs and bans addresses by updating firewall rules, "cannot eliminate the risk presented by weak authentication"; `maxretry`, `findtime`, `bantime`, `ignoreip` meanings | [README](https://raw.githubusercontent.com/fail2ban/fail2ban/master/README.md), [jail.conf(5)](https://raw.githubusercontent.com/fail2ban/fail2ban/master/man/jail.conf.5) | Read; not run. The jail example is **est.** |
| Samhain and OSSEC one-line descriptions | [la-samhna.de](https://www.la-samhna.de/samhain/), [OSSEC README](https://raw.githubusercontent.com/ossec/ossec-hids/master/README.md) | Read the opening text only; not run. That Wazuh began from OSSEC code is **est.** (general knowledge) |
| `OnFailure=` activates units when a unit enters the failed state | [systemd.unit(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html) | Read; the unit files passed `systemd-analyze verify` (observed), never installed or started |
| logcheck "helps spot problems and security violations in your logfiles ... and will send the results to you periodically in an e-mail" | [Debian manual page](https://manpages.debian.org/stable/logcheck/logcheck.8.en.html) | Read the description; not run. logwatch not read |
| MITRE ATT&CK lists "Indicator Removal: Timestomp" as modifying a file's modify, access, create and change times to blend in | [ATT&CK: Timestomp](https://attack.mitre.org/techniques/T1070/006/) | Read the opening paragraph |
| Event 4663 needs a SACL and differs from 4656; the Audit File System subcategory | [Microsoft Learn: 4663](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4663) | Read; not run |
| Sysmon and `sfc /verifyonly` roles on Windows | Not read | **est.** |
| Package-manager checksum verification (`debsums`, `rpm -V`) | Not read | **est.** |
| The toy scripts' output: 4 baseline files, 4 findings, the forged-line escape, same-time same-size change caught, forged baseline hidden, fingerprint and signature failing | Run with GNU Bash 5.2, coreutils 9.7, GNU Awk 5.2, OpenSSH 10.3, Python 3.13 | Observed once; process ids and times vary |

Not verified, plainly: every PowerShell script and command; anything on Windows or macOS; AIDE, Tripwire Open Source, Wazuh, auditd, osquery and fail2ban (none run, because none was installed and no `sudo` was used); the commercial Tripwire products (pages refused); the Wazuh defaults on a live agent; whether the `-a` rules shown load unchanged on your audit version; the AIDE configuration in Exercise 7; the current release number of any tool; and the final names and headings of the three sibling lessons (written at the same time).

Next: [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md), where the file you watch is a decoy and any touch is the alert.
