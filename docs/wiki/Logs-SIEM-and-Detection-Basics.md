# Logs, SIEM and detection basics: from a log line to an alert

Side page to the detection pages. Read it after [Droplet hardening](Droplet-Hardening.md) (core step 14) if "log", "SIEM", "rule" and "alert" are only words to you, and before [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) if you want the vocabulary first. It reaches ahead to [Threat model](Threat-Model.md) (core step 19), whose residual risks are the things this page teaches you to notice. It does not repeat what the telemetry pages say: it makes you read a log, find a pattern in it, write a rule and watch that rule be wrong. Next: [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the Bash scripts were run once on Linux; the PowerShell, the Windows commands and the Wazuh rule shapes were not run.** On **2026-10-22** the author ran every Bash script and command in the free path on a Debian-based Linux machine, once with GNU Awk 5.2.1 and once with mawk 1.3.4 (the output was byte-for-byte the same), as an ordinary user, and pasted trimmed output from those runs. **Not run:** every PowerShell script and command (there was no PowerShell on the machine; they are written from Microsoft's documentation and marked **est.**, so expect to fix a typo), every Windows event log command, and the optional own-account path. Nothing on this page was checked against a real Wazuh manager. The stage 2 log shipping this page points at is built and merged but **has not been applied to any real machine** ([stage 2 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md)). Every vendor, standard and tool claim is in the [claims register](#claims-register) with the URL and the date it was read. Output varies with your versions; trust what your terminal prints over this page.

> **Prerequisites.** You can open a terminal and run a command ([Git from zero](Git-From-Zero.md#what-a-terminal-is) shows how; [The terminal and your first script](Terminal-and-Your-First-Script.md) covers pipes and exit codes). A regular expression (a pattern that describes which text matches) helps; [Data formats: read a pattern, write two](Data-Formats-JSON-YAML-HCL.md#exercise-11-read-a-pattern-write-two) teaches it. [Droplet hardening](Droplet-Hardening.md) (core step 14) is the page that mentions the logs. About 90 minutes for the reading and the free exercises (est.).

## What you will be able to do

- Say what a log is, and tell a log, a metric, a trace and an alert apart.
- Read an SSH log line and a web server log line field by field, and say where on a Linux machine and on a Windows machine each kind of log lives.
- Write a regular expression that finds failed logins, and explain why the first one you write will probably miss some.
- Explain parsing and normalizing, and show why a log pile you can only search by hand is not a SIEM.
- Write a detection rule as a small program, run it on invented logs, and say what it catches, what it misses and why.
- Tell a rule from a baseline, a false positive from a false negative, and explain why too many alerts is a failure of its own.
- Say what a SIEM, an IDS, an IPS, an EDR, a NOC and a SOC each does, and why clocks have to agree.
- Run Build, Break, Detect, Evade, Defend on a failed-login rule, then flip the board and read someone else's rule as an attacker would.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Log, metric, trace and alert as four different things | [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md#four-words-that-are-not-synonyms) is a table of the four, with the project's own examples. | What a log line actually contains, and how you read one. |
| Collect, store, detect, respond; SIEM, EDR, XDR, MDR | [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md#four-jobs-and-the-words-people-mix-up) names the jobs and the products. | Doing the detect job yourself on a small file, so the words have a shape. |
| What the stage 2 agent collects | [The stage 2 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md) (section 2.4) lists the sources: the journal for `twingate-connector`, `ssh`/`sshd` and `sudo`, `/var/log/auth.log` and `/var/log/audit/audit.log`. | What each of those sources looks like, and what a rule does with it. |
| A brute-force rule on honeypot events | [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) detects five wrong guesses in sixty seconds on JSON events from a decoy. | The same idea on ordinary text logs from two different sources, plus baselines, time, false positives and tuning. |
| The mini SOC and the metrics lab | [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) and [Lab: a synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md). | Neither teaches you to read a log. The lab is about metrics (numbers over time), not log lines. |

## A log is one event written down

A **log** is a record that software writes when something happens: a user signed in, a request arrived, a file changed, a service crashed. Each record is usually one line of text (or one small structured record) and carries at least a **timestamp** (when), a **source** (which program or machine) and a **message** (what). Most logs also carry an identity (which user or which address). A log answers "what exactly happened?", and it is written whether or not anyone is watching. Nobody reads it until something goes wrong; that is why reading one is a skill and not a habit.

Four words get mixed up, and [the telemetry page](Cloud-Telemetry-What-and-Why.md#four-words-that-are-not-synonyms) has the full table. The short version:

- A **log** is one event. Volume follows activity.
- A **metric** is a number sampled over time ("CPU is 40 percent"). Volume follows how many things you measure.
- A **trace** is the path of one request through several services. This project has none.
- An **alert** is a *decision* made from logs or metrics: "this needs a person". It is derived, so an alert built on bad data is a bad alert.

NIST's log management guide (SP 800-92, September 2006) gives the reasons organizations keep logs: to find out what happened, to spot problems early, and to have evidence afterward. It is an old document and the details have moved on, but the reasons have not.

## Where logs live

The same event can be written in several places, in different shapes. Here are the ones you will meet first.

| Where | What writes it | Shape | Read it with |
|---|---|---|---|
| **syslog** messages | Programs on Unix-like systems, sent to a logging service | One text line: a timestamp, a host, a program name and a process id, a message | `less`, `grep`, `tail -f` on the files the logging service writes |
| **journald** (the systemd journal) | `systemd-journald`, which collects kernel messages, the `syslog` calls, service output and audit records | A **structured, indexed** record with fields, not only a line | `journalctl` |
| **`/var/log/auth.log`** | On Debian and Ubuntu, the logging service writes sign-in and `sudo` messages here | syslog lines | `grep` and friends. Not every installation has the file; the machine this page was tested on did not (observed 2026-10-22), because its messages are only in the journal |
| **Web server access log** | Apache, nginx and others | One line per request, in a format the server is configured to write; the Common Log Format is the classic | `grep`, `awk`, a log tool |
| **auditd** | The Linux audit system, from the kernel | Key-value records about files, accounts and commands, written to `/var/log/audit/audit.log` | `ausearch`, `aureport`, or a SIEM agent |
| **Windows Event Log** | Windows and its programs | A structured record with an **event ID** (a number for the kind of event), a channel (`Security`, `Application`, `System`) and fields | Event Viewer, or `Get-WinEvent` in PowerShell |

**syslog** is both a message format and a habit: a program writes a line, a logging service stamps and files it. The older format (RFC 3164, 2001, "BSD syslog") has a timestamp like `Oct 22 03:14:07`: month, day and time, **with no year and no time zone**. The newer format (RFC 5424) uses a full date and time with a zone, and splits the header into named fields: priority, version, timestamp, host name, application name, process id and message id. A lot of what you see on a Linux machine still looks like the old one, so you will meet the missing year and zone.

**journald** keeps each event as a record with named fields and indexes them, so you can ask for "messages from this service at this priority since this time" instead of searching text. `journalctl -u ssh`, `journalctl -p warning` and `journalctl --since "2026-10-22 03:00:00"` are the three filters you will use first, and `-o json` prints the same records as JSON.

On Windows, the **Security** channel records sign-ins by event ID. Two to know: **4624** is "an account was successfully logged on" and **4625** is "an account failed to log on". The 4625 record has fields such as the account name, a *Logon Type* (a number saying how the person signed in: at the keyboard, over the network, and so on), the *Source Network Address* and a *Failure Reason*. A Windows failed login and a Linux `Failed password` line are the same event in two shapes, and a SIEM's job is to make them look alike (below).

### The web access log line

The Common Log Format (CLF) writes one request per line as `%h %l %u %t "%r" %>s %b`: the client address, an identity-by-ident field that is almost always `-`, the signed-in user (or `-`), the time in brackets, the request in quotes (method, path, protocol), the status code and the size in bytes. A `401` means "not authorized": for a login form, a failed attempt. A `200` means success.

## Parsing and normalizing

A raw log line is just text. **Parsing** is cutting the line into named fields: this part is the time, this part the user, this part the address. **Normalizing** is giving the same kind of fact the same name whatever the source: the Linux line says `Failed password for admin from 203.0.113.9`, the Windows event has `TargetUserName` and `IpAddress`, the web log says status `401` and a client address in column one. After normalizing, all three might read `action=login_failed user=admin src=203.0.113.9`, and *one* rule can find all three.

That is the difference between a **log pile** and a **SIEM** (security information and event management, a tool that collects logs from many places, parses and normalizes them, stores them where you can search and correlate, and runs rules on them):

| Log pile | SIEM |
|---|---|
| Files on many machines, each in its own shape | One place, one shape per kind of event |
| You `grep` one box at a time, and only after something is wrong | Rules run all the time, on everything, and a person is told |
| Finding "everything this address did" means logging in to every source | One search across every source (you will do this in Exercise 3) |
| Evidence disappears when the machine does, or when an attacker deletes it | Logs have left the machine, so deleting them locally does not erase them (see [why telemetry leaves the machine](Cloud-Telemetry-What-and-Why.md#why-telemetry-has-to-leave-the-machine)) |

A SIEM is a tool, not a team. A **SOC** (security operations center) is the team that uses it, and a **NOC** (network operations center) is the team that asks "is it up?" ([the telemetry page](Cloud-Telemetry-What-and-Why.md#noc-soc-and-siem-a-team-a-team-and-a-tool) compares all three).

### Where this shows up in this project

- **Wazuh** is the SIEM-shaped tool the project plans to use ([Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md#wazuh-piece-by-piece)). Its **agent** runs on a monitored machine and sends events out to a **manager**, which applies **decoders** (XML that parses a raw line into fields) and **rules** (XML that decides which parsed events deserve an alert, and how serious). Parsing and normalizing are the decoder's job; detecting is the rule's.
- **The stage 2 log shipping** installs the Wazuh agent and `auditd` on each connector, opt-in and off by default, and not applied anywhere yet. The agent reads the journal for `twingate-connector`, `ssh`/`sshd` and `sudo`, plus `/var/log/auth.log` and `/var/log/audit/audit.log`. Because `sshd` writes to both the journal and `auth.log`, the guide warns to expect each SSH event twice until one source is dropped. That is a normalizing problem in real life: the same fact arrives in two shapes, and counting them naively doubles your numbers (a threshold of five counted failures fires after only three real ones).
- **The `auditd` rules** the stage 2 bootstrap installs are watches only: writes to the identity files (`/etc/passwd`, `group`, `shadow`, `gshadow`) tagged `cah_identity`, to `sudoers` tagged `cah_sudo`, and to `/etc/twingate/` tagged `cah_twingate`. They are written as `-a always,exit` file rules (with an `arch=b32` twin of each added on x86_64 so 32-bit programs are seen too), the form the `auditctl` manual page recommends in place of the deprecated `-w` watch (shown in [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md#auditd-who-did-what)); whether a given audit version loads them as written is **est.** (they are in the cloud-init template, which has not run on a real machine).
- **Grafana** shows the numbers (metrics) from Prometheus; the repository does not run a separate log store. A log store such as **Loki** is a different kind of tool: its documentation says it indexes only the labels of a log stream (like Prometheus labels) and stores the log text compressed, which is cheap but means searching text is slower than in a full-text index. Loki is named here as an example of the "store and search" job from the landscape page; **this repository does not use it**, so do not look for it in the stacks.
- **The synthetic monitoring lab** ([Lab-Demo-Monitoring-Stack](Lab-Demo-Monitoring-Stack.md)) is the metrics half. This page's exercises are the logs half, and they need no Docker.

## Rules, baselines and the two ways to be wrong

A **rule** says what bad looks like and fires when it sees it: "five failed logins from one address in a minute". It is easy to explain, easy to test, and only as good as your idea of bad. A **baseline** says what normal looks like, learned from data, and fires on a deviation: "this user has signed in between 8:00 and 17:00 for two weeks, and now it is 03:40". It can catch things you did not think to write a rule for, and it is only as good as the data it learned from (if the attacker was already there during the learning period, the baseline learned them).

Both can be wrong in two directions:

- A **false positive** is an alert for something harmless. A person who mistypes a password five times, or a script with a stale password, trips the five-failures rule.
- A **false negative** is a miss: a real attack that no rule fired on. You usually find out later, and that is the worse of the two.

You cannot drive both to zero. Lowering a threshold catches more attacks and more mistakes; raising it silences the mistakes and some attacks with them. That trade-off is the whole of **tuning**.

### Alert fatigue

People who are told too often stop reading. **Alert fatigue** is what happens when a SOC (or a single operator) gets so many alerts, most of them false, that the real one is ignored or closed in a hurry. The fix is not "more alerts". It is fewer, better ones: each alert should say what to do about it, and a rule that has fired a hundred times and never been real should be fixed or removed. A quick bit of arithmetic, with **invented numbers** to show the shape: if one rule fires 40 times a day, each needs two minutes to look at, and one of those 40 is real, then 80 of the operator's minutes a day go on that rule and 39 of every 40 minutes are spent on noise. Cutting the rule to 8 alerts a day, with the real one still among them, gives back 64 minutes.

### Time: why clocks have to agree

Correlating two logs means putting their events in order. If one machine's clock is seven minutes fast, a web login attempt appears to happen *after* an SSH login that came well after it, and the story you tell is wrong. That is why machines keep their clocks aligned with the **Network Time Protocol** (NTP, RFC 5905 is version 4) and why logs should carry a time zone, ideally UTC. On a systemd Linux machine `timedatectl` shows whether the clock is synchronized. Exercise 4 shows the damage when it is not.

## The family of tools, in one table

| Tool | Watches | What it does when it sees something | Where it fits |
|---|---|---|---|
| **SIEM** | Logs from everywhere | Collects, normalizes, stores, searches, alerts | The "store and detect" job |
| **IDS** (intrusion detection system) | Network traffic, or a host's activity | Raises an alert and does not block | Detection only. Suricata describes itself as a network IDS, IPS and monitoring engine; [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md) runs one offline |
| **IPS** (intrusion prevention system) | The same | Drops or blocks the traffic it judges hostile | Detection plus action; a false positive here **breaks something real**, which is why many run in alert-only mode first |
| **EDR** (endpoint detection and response) | Processes, files and network activity on each laptop or server | Records, detects, and can isolate the machine | Per-machine, agent-based ([the landscape page](Detection-and-Monitoring-Wazuh-and-the-Landscape.md#four-jobs-and-the-words-people-mix-up) places the products) |
| **NOC** | Whether things are up and fast | A team acts to restore service | Uses metrics first |
| **SOC** | Whether anything is hostile | A team investigates and contains | Uses logs and endpoint events |

Vendors blur these labels. Treat the table as the shape of the idea and read a product's own documentation for what it does today.

## Free path: a lab on your own computer

Everything in this section runs on your own computer, needs no account, and costs nothing; the lessons are free and will stay free. The logs are **invented** by a script you run: no real machine, no real login, no real address. The addresses come from the documentation ranges reserved by RFC 5737 (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`), which are set aside for examples and are not meant to be routed. Every exercise follows four steps: **predict** (write down what you expect first), **do**, **check**, **undo**.

**Which track.** Bash needs `awk`, `grep`, `sort` and `seq` (any Linux or macOS machine; on macOS the default `awk` is different, and a fix is **est.**). On Windows, use the PowerShell commands, or WSL 2 with the Bash commands. PowerShell scripts may be blocked by the execution policy on a fresh Windows machine; the fix for one window only is `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` (**est.**, not run). Nothing here sends anything anywhere.

### Setup: build the fake logs

Make a folder, then save and run the script for your shell. It writes two files: `auth.log` (SSH lines in the old syslog shape) and `access.log` (web requests in the Common Log Format). Read the scripts once; the story is in the addresses. `203.0.113.9` is a guesser. `203.0.113.50` signs in as `alice` at 03:40. `198.51.100.23` is `alice` fumbling a password once and succeeding. `192.0.2.10` is `bob`, five failures in forty seconds and then success, from an address nobody should worry about. The `CRON` line is noise your rule must ignore.

```bash
mkdir -p ~/log-lab && cd ~/log-lab
```

Save as `mklogs.sh`:

```bash
#!/usr/bin/env bash
# mklogs.sh - builds two SYNTHETIC log files in the current folder. Nothing here came from a
# real machine. Addresses are documentation ranges (RFC 5737); "demo-host" is invented.
set -eu
cat > auth.log <<'LOG'
Oct 22 03:14:07 demo-host sshd[2201]: Failed password for invalid user admin from 203.0.113.9 port 51234 ssh2
Oct 22 03:14:13 demo-host sshd[2203]: Failed password for invalid user admin from 203.0.113.9 port 51236 ssh2
Oct 22 03:14:19 demo-host sshd[2205]: Failed password for root from 203.0.113.9 port 51240 ssh2
Oct 22 03:14:26 demo-host sshd[2207]: Failed password for root from 203.0.113.9 port 51244 ssh2
Oct 22 03:14:33 demo-host sshd[2209]: Failed password for invalid user test from 203.0.113.9 port 51248 ssh2
Oct 22 03:14:41 demo-host sshd[2211]: Failed password for invalid user test from 203.0.113.9 port 51252 ssh2
Oct 22 03:40:12 demo-host sshd[2290]: Accepted publickey for alice from 203.0.113.50 port 40100 ssh2
Oct 22 09:00:03 demo-host sshd[2310]: Accepted publickey for alice from 198.51.100.7 port 40022 ssh2
Oct 22 09:02:10 demo-host sshd[2318]: Failed password for alice from 198.51.100.23 port 40510 ssh2
Oct 22 09:02:19 demo-host sshd[2319]: Accepted password for alice from 198.51.100.23 port 40512 ssh2
Oct 22 10:00:01 demo-host CRON[2400]: pam_unix(cron:session): session opened for user root(uid=0) by (uid=0)
Oct 22 14:20:11 demo-host sshd[2501]: Failed password for bob from 192.0.2.10 port 33001 ssh2
Oct 22 14:20:21 demo-host sshd[2502]: Failed password for bob from 192.0.2.10 port 33003 ssh2
Oct 22 14:20:31 demo-host sshd[2503]: Failed password for bob from 192.0.2.10 port 33005 ssh2
Oct 22 14:20:41 demo-host sshd[2504]: Failed password for bob from 192.0.2.10 port 33007 ssh2
Oct 22 14:20:51 demo-host sshd[2505]: Failed password for bob from 192.0.2.10 port 33009 ssh2
Oct 22 14:21:05 demo-host sshd[2506]: Accepted password for bob from 192.0.2.10 port 33011 ssh2
LOG
cat > access.log <<'LOG'
203.0.113.9 - - [22/Oct/2026:03:14:10 +0000] "POST /login HTTP/1.1" 401 512
203.0.113.9 - - [22/Oct/2026:03:14:22 +0000] "POST /login HTTP/1.1" 401 512
203.0.113.9 - - [22/Oct/2026:03:14:35 +0000] "POST /login HTTP/1.1" 401 512
203.0.113.50 - alice [22/Oct/2026:03:40:50 +0000] "GET /dashboard HTTP/1.1" 200 8120
198.51.100.7 - - [22/Oct/2026:09:00:20 +0000] "GET / HTTP/1.1" 200 1534
198.51.100.23 - alice [22/Oct/2026:09:03:02 +0000] "GET /dashboard HTTP/1.1" 200 8120
LOG
echo "wrote auth.log ($(wc -l < auth.log) lines) and access.log ($(wc -l < access.log) lines)"
```

```bash
bash mklogs.sh
```

```text
wrote auth.log (17 lines) and access.log (6 lines)
```

PowerShell (**est.**, not run). Save as `mklogs.ps1` in a folder such as `~\log-lab`, and run `.\mklogs.ps1`:

```powershell
# mklogs.ps1 - builds two SYNTHETIC log files in the current folder. Nothing here came from a
# real machine. Addresses are documentation ranges (RFC 5737); "demo-host" is invented.
$auth = @'
Oct 22 03:14:07 demo-host sshd[2201]: Failed password for invalid user admin from 203.0.113.9 port 51234 ssh2
Oct 22 03:14:13 demo-host sshd[2203]: Failed password for invalid user admin from 203.0.113.9 port 51236 ssh2
Oct 22 03:14:19 demo-host sshd[2205]: Failed password for root from 203.0.113.9 port 51240 ssh2
Oct 22 03:14:26 demo-host sshd[2207]: Failed password for root from 203.0.113.9 port 51244 ssh2
Oct 22 03:14:33 demo-host sshd[2209]: Failed password for invalid user test from 203.0.113.9 port 51248 ssh2
Oct 22 03:14:41 demo-host sshd[2211]: Failed password for invalid user test from 203.0.113.9 port 51252 ssh2
Oct 22 03:40:12 demo-host sshd[2290]: Accepted publickey for alice from 203.0.113.50 port 40100 ssh2
Oct 22 09:00:03 demo-host sshd[2310]: Accepted publickey for alice from 198.51.100.7 port 40022 ssh2
Oct 22 09:02:10 demo-host sshd[2318]: Failed password for alice from 198.51.100.23 port 40510 ssh2
Oct 22 09:02:19 demo-host sshd[2319]: Accepted password for alice from 198.51.100.23 port 40512 ssh2
Oct 22 10:00:01 demo-host CRON[2400]: pam_unix(cron:session): session opened for user root(uid=0) by (uid=0)
Oct 22 14:20:11 demo-host sshd[2501]: Failed password for bob from 192.0.2.10 port 33001 ssh2
Oct 22 14:20:21 demo-host sshd[2502]: Failed password for bob from 192.0.2.10 port 33003 ssh2
Oct 22 14:20:31 demo-host sshd[2503]: Failed password for bob from 192.0.2.10 port 33005 ssh2
Oct 22 14:20:41 demo-host sshd[2504]: Failed password for bob from 192.0.2.10 port 33007 ssh2
Oct 22 14:20:51 demo-host sshd[2505]: Failed password for bob from 192.0.2.10 port 33009 ssh2
Oct 22 14:21:05 demo-host sshd[2506]: Accepted password for bob from 192.0.2.10 port 33011 ssh2
'@
$web = @'
203.0.113.9 - - [22/Oct/2026:03:14:10 +0000] "POST /login HTTP/1.1" 401 512
203.0.113.9 - - [22/Oct/2026:03:14:22 +0000] "POST /login HTTP/1.1" 401 512
203.0.113.9 - - [22/Oct/2026:03:14:35 +0000] "POST /login HTTP/1.1" 401 512
203.0.113.50 - alice [22/Oct/2026:03:40:50 +0000] "GET /dashboard HTTP/1.1" 200 8120
198.51.100.7 - - [22/Oct/2026:09:00:20 +0000] "GET / HTTP/1.1" 200 1534
198.51.100.23 - alice [22/Oct/2026:09:03:02 +0000] "GET /dashboard HTTP/1.1" 200 8120
'@
Set-Content -Path auth.log -Value $auth -Encoding ascii
Set-Content -Path access.log -Value $web -Encoding ascii
"wrote auth.log ($((Get-Content auth.log).Count) lines) and access.log ($((Get-Content access.log).Count) lines)"
```

**Undo (any exercise).** Re-run the setup script to put both files back as they were. `cd ~ && rm -r ~/log-lab` removes the whole lab.

### Exercise 1: read a log line field by field

**Predict.** The first line of `auth.log` has 16 words separated by spaces. Which word is the time, which is the program that wrote it, and which is the address the attempt came from? Then, for the first line of `access.log`: which column is the status code?

**Do (Bash).**

```bash
awk 'NR==1{for(i=1;i<=NF;i++) printf "%2d  %s\n", i, $i}' auth.log
awk 'NR==1{for(i=1;i<=NF;i++) printf "%2d  %s\n", i, $i}' access.log
```

**Do (PowerShell, est.).**

```powershell
$i = 0; (Get-Content auth.log -TotalCount 1) -split ' ' | ForEach-Object { $i++; '{0,2}  {1}' -f $i, $_ }
$i = 0; (Get-Content access.log -TotalCount 1) -split ' ' | ForEach-Object { $i++; '{0,2}  {1}' -f $i, $_ }
```

**Check.** In `auth.log`, field 1 and 2 are the month and day, 3 is the time, 4 is the host, 5 is `sshd[2201]:` (the program and its process id), 6 to 11 are the message `Failed password for invalid user admin`, 12 is `from`, 13 is the address `203.0.113.9`, 14 and 15 are `port 51234` (the attacker's side of the connection, mostly noise) and 16 is `ssh2`. Notice: **no year, no time zone**. In `access.log`, column 1 is the client address, 2 and 3 are the ident and user (both `-`), 4 and 5 are the time and its offset, 6 to 8 are the request, 9 is the status (`401`) and 10 is the size. Note too that the user field's position moves: a failed attempt for an *invalid* user has two extra words, so "the user is always field 9" is wrong. That is the lesson of Exercise 2.

**Undo.** Nothing to undo; the commands only read.

### Exercise 2: find failed logins with a regular expression

**Predict.** A first attempt at a pattern is `Failed password for [^ ]+ from`. (`[^ ]+` means one or more characters that are not a space.) Out of the 12 failed-password lines in `auth.log`, how many will it find? Write down a number, and then say what kind of line it will miss.

**Do (Bash).**

```bash
grep -cE 'Failed password for [^ ]+ from' auth.log
grep -cE 'Failed password for (invalid user )?[^ ]+ from [0-9.]+' auth.log
grep -oE 'Failed password.* from [0-9.]+' auth.log | awk '{print $NF}' | sort | uniq -c | sort -rn
```

**Do (PowerShell, est.).**

```powershell
(Select-String -Path auth.log -Pattern 'Failed password for \S+ from').Count
(Select-String -Path auth.log -Pattern 'Failed password for (invalid user )?\S+ from [0-9.]+').Count
Select-String -Path auth.log -Pattern 'Failed password.* from ([0-9.]+)' |
  ForEach-Object { $_.Matches[0].Groups[1].Value } | Group-Object | Sort-Object Count -Descending | Format-Table Count, Name
```

**Check.**

```text
8
12
      6 203.0.113.9
      5 192.0.2.10
      1 198.51.100.23
```

The first pattern finds 8, because it assumes the word after `for` is the user. When the user does not exist, SSH writes `invalid user admin`, so `[^ ]+` grabs `invalid` and then expects `from` but sees `user`. The four invalid-user lines are exactly the attacker guessing names that do not exist, the lines you most wanted. A pattern that works on the lines you looked at and misses the variant you did not look at is the commonest way a rule fails quietly. The third command counts failures per source address, which is the shape every brute-force rule starts from.

**Undo.** Nothing to undo.

### Exercise 3: normalize two sources into one shape

**Predict.** `203.0.113.9` appears in both files. How many lines mention it across `auth.log` and `access.log` together? And once both files are turned into one shape, can you ask for everything it did in time order with a single command?

**Do (Bash).** Save as `normalize.sh`. It reads both files, writes one `key=value` line per event, and sorts by time. It skips lines it does not understand (the `CRON` line) on purpose.

```bash
#!/usr/bin/env bash
# normalize.sh [WEB_CLOCK_OFFSET_SECONDS]
# Reads auth.log (syslog style) and access.log (web server style) from the current folder and
# prints one key=value line per event, in one shape, in time order. Lines it does not
# understand (like the CRON line) are skipped on purpose.
# Limits: syslog has no year, so 2026 is supplied here. Times are treated as UTC. The offset
# does not carry across midnight.
set -eu
off=${1:-0}
{
  awk -v year=2026 '
    BEGIN { split("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec", m, " "); for (i = 1; i <= 12; i++) mon[m[i]] = i }
    $5 ~ /^sshd\[[0-9]+\]:$/ {
      if (match($0, /Failed password for (invalid user )?[^ ]+ from [0-9.]+/)) act = "login_failed"
      else if (match($0, /Accepted (password|publickey) for [^ ]+ from [0-9.]+/)) act = "login_ok"
      else next
      n = split(substr($0, RSTART, RLENGTH), f, " ")
      printf "ts=%04d-%02d-%02dT%sZ src=%s source=sshd action=%s user=%s\n", year, mon[$1], $2, $3, f[n], act, f[n - 2]
    }' auth.log
  awk -v off="$off" '
    BEGIN { split("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec", m, " "); for (i = 1; i <= 12; i++) mon[m[i]] = i }
    $4 ~ /^\[/ && $6 ~ /^"/ {
      split(substr($4, 2), p, /[\/:]/)
      s = p[4] * 3600 + p[5] * 60 + p[6] + off
      s = ((s % 86400) + 86400) % 86400
      printf "ts=%04d-%02d-%02dT%02d:%02d:%02dZ src=%s source=web action=http_%s user=%s path=%s\n", p[3], mon[p[2]], p[1], int(s / 3600), int((s % 3600) / 60), s % 60, $1, $9, $3, $7
    }' access.log
} | LC_ALL=C sort
```

```bash
grep -cF '203.0.113.9' auth.log access.log
bash normalize.sh | head -4
bash normalize.sh | grep -c 'src=203.0.113.9 '
bash normalize.sh | grep 'src=203.0.113.9 ' | cut -d' ' -f1,3
```

**Do (PowerShell, est.).** Save as `normalize.ps1`.

```powershell
# normalize.ps1 [-WebOffset SECONDS]
# Same job as normalize.sh: both files in, one key=value line per event out, in time order.
param([int]$WebOffset = 0)
$months = @{ Jan = 1; Feb = 2; Mar = 3; Apr = 4; May = 5; Jun = 6; Jul = 7; Aug = 8; Sep = 9; Oct = 10; Nov = 11; Dec = 12 }
$ssh = foreach ($line in Get-Content auth.log) {
    if ($line -match '^(\w{3}) +(\d+) (\d\d:\d\d:\d\d) \S+ sshd\[\d+\]: (Failed password|Accepted (?:password|publickey)) for (invalid user )?(\S+) from ([0-9.]+) ') {
        $action = if ($Matches[4] -like 'Failed*') { 'login_failed' } else { 'login_ok' }
        'ts={0:0000}-{1:00}-{2:00}T{3}Z src={4} source=sshd action={5} user={6}' -f 2026, $months[$Matches[1]], [int]$Matches[2], $Matches[3], $Matches[7], $action, $Matches[6]
    }
}
$web = foreach ($line in Get-Content access.log) {
    if ($line -match '^(\S+) \S+ (\S+) \[(\d+)/(\w{3})/(\d{4}):(\d\d):(\d\d):(\d\d) [+-]\d{4}\] "\S+ (\S+) [^"]*" (\d{3}) ') {
        $s = [int]$Matches[6] * 3600 + [int]$Matches[7] * 60 + [int]$Matches[8] + $WebOffset
        $s = (($s % 86400) + 86400) % 86400
        $t = [TimeSpan]::FromSeconds($s).ToString('hh\:mm\:ss')
        'ts={0}-{1:00}-{2:00}T{3}Z src={4} source=web action=http_{5} user={6} path={7}' -f $Matches[5], $months[$Matches[4]], [int]$Matches[3], $t, $Matches[1], $Matches[10], $Matches[2], $Matches[9]
    }
}
$all = [string[]]@(@($ssh) + @($web) | Where-Object { $_ })
[Array]::Sort($all, [StringComparer]::Ordinal)
$all
```

```powershell
(Select-String -Path auth.log, access.log -SimpleMatch '203.0.113.9').Count
.\normalize.ps1 | Select-Object -First 4
(.\normalize.ps1 | Select-String -SimpleMatch 'src=203.0.113.9 ').Count
```

**Check.**

```text
auth.log:6
access.log:3
ts=2026-10-22T03:14:07Z src=203.0.113.9 source=sshd action=login_failed user=admin
ts=2026-10-22T03:14:10Z src=203.0.113.9 source=web action=http_401 user=- path=/login
ts=2026-10-22T03:14:13Z src=203.0.113.9 source=sshd action=login_failed user=admin
ts=2026-10-22T03:14:19Z src=203.0.113.9 source=sshd action=login_failed user=root
9
ts=2026-10-22T03:14:07Z source=sshd
ts=2026-10-22T03:14:10Z source=web
ts=2026-10-22T03:14:13Z source=sshd
ts=2026-10-22T03:14:19Z source=sshd
ts=2026-10-22T03:14:22Z source=web
ts=2026-10-22T03:14:26Z source=sshd
ts=2026-10-22T03:14:33Z source=sshd
ts=2026-10-22T03:14:35Z source=web
ts=2026-10-22T03:14:41Z source=sshd
```

Nine lines across two sources, and now they interleave in time order: the guesser was hitting the web login and SSH at the same time. In the raw files you would have had to open two files and merge by hand. That one search over many sources, in one shape, is the part of a SIEM that a log pile does not give you. The `sshd` and `web` lines are different events, but the same keys (`ts`, `src`, `action`, `user`) let one rule read them. Also notice what the normalizer *chose to throw away*: the port, the process id, the `CRON` line. Every normalizer drops something; if what it drops is what you needed later, that is information the SIEM no longer has (keep the raw line too, which real tools do).

**Undo.** Nothing to undo; the output goes to the terminal.

### Exercise 4: put the clocks out of step

**Predict.** Suppose the web server's clock is seven minutes (420 seconds) ahead of the SSH host's. Where will the web login attempts from `203.0.113.9` appear in the combined, time-ordered list, and what story would an investigator tell from it?

**Do (Bash).**

```bash
bash normalize.sh 420 | head -9 | cut -d' ' -f1,3,4
```

**Do (PowerShell, est.).**

```powershell
.\normalize.ps1 -WebOffset 420 | Select-Object -First 9
```

**Check.**

```text
ts=2026-10-22T03:14:07Z source=sshd action=login_failed
ts=2026-10-22T03:14:13Z source=sshd action=login_failed
ts=2026-10-22T03:14:19Z source=sshd action=login_failed
ts=2026-10-22T03:14:26Z source=sshd action=login_failed
ts=2026-10-22T03:14:33Z source=sshd action=login_failed
ts=2026-10-22T03:14:41Z source=sshd action=login_failed
ts=2026-10-22T03:21:10Z source=web action=http_401
ts=2026-10-22T03:21:22Z source=web action=http_401
ts=2026-10-22T03:21:35Z source=web action=http_401
```

The six SSH failures now sit together, and the three web failures look like a second, later wave from seven minutes after. The real picture was one interleaved burst. An investigator would write "tried SSH, gave up, tried the web login seven minutes later", which is false, and any rule that needs to know "within a minute of each other, across sources" would stop firing. The defenses are boring and essential: run NTP on every machine ([RFC 5905](https://www.rfc-editor.org/rfc/rfc5905) defines version 4; `timedatectl` shows whether a systemd machine believes it is synchronized), log in UTC with the time zone written down, and record when each log *arrived* as well as when it says it happened.

**Undo.** Nothing to undo.

### Exercise 5: write a detection rule (the rule fires)

**Predict.** A rule says: *fire when one source address has five or more failed logins within sixty seconds, and stay quiet about that source for the next sixty seconds.* Reading the normalized lines, which sources fire, and at what time each? Look at `203.0.113.9` (six failures over 34 seconds) and `192.0.2.10` (five over 40 seconds). What about `198.51.100.23`, with one?

**Do (Bash).** Save as `detect.sh`. It reads normalized lines on standard input. It only compares text; it never runs any of it, so a hostile username in a log is not run as a command (a test in this repository checks that). It takes the threshold and the window as arguments, and an optional hours file for the second rule used later.

```bash
#!/usr/bin/env bash
# detect.sh THRESHOLD WINDOW_SECONDS [HOURS_FILE]   (reads normalized lines on standard input)
# Rule 1, brute_force: THRESHOLD login_failed events from one src within WINDOW_SECONDS.
#   After it fires for a source, that source is quiet for WINDOW_SECONDS.
# Rule 2, off_hours (only if HOURS_FILE is given): a login_ok for a user listed in the file as
#   "user FIRST_HOUR LAST_HOUR_EXCLUSIVE", outside those hours.
# Every line is only compared, never run. One day of input only.
set -eu
awk -v n="$1" -v w="$2" -v hf="${3:-}" '
  function secs(ts,  t) { split(substr(ts, 12, 8), t, ":"); return t[1] * 3600 + t[2] * 60 + t[3] }
  BEGIN {
    if (hf != "") while ((getline line < hf) > 0) { split(line, h, " "); from[h[1]] = h[2]; to[h[1]] = h[3] }
  }
  {
    delete kv
    for (i = 1; i <= NF; i++) { split($i, p, "="); kv[p[1]] = p[2] }
    day = substr(kv["ts"], 1, 10)
    if (first == "") first = day
    if (day != first) { print "error: input spans more than one day; this toy compares times within a day" > "/dev/stderr"; exit 2 }
    t = secs(kv["ts"])
    if (kv["action"] == "login_failed") {
      ip = kv["src"]; k = 0
      for (j = 1; j <= cnt[ip]; j++) if (t - times[ip, j] <= w) { k++; times[ip, k] = times[ip, j] }
      k++; times[ip, k] = t; cnt[ip] = k
      if (k >= n && (!(ip in muted) || t - muted[ip] > w)) {
        printf "ALERT brute_force src=%s failures=%d window=%ds at=%s\n", ip, k, w, kv["ts"]
        muted[ip] = t
      }
    } else if (hf != "" && kv["action"] == "login_ok" && (kv["user"] in from)) {
      hr = int(t / 3600)
      if (hr < from[kv["user"]] || hr >= to[kv["user"]])
        printf "ALERT off_hours user=%s src=%s at=%s\n", kv["user"], kv["src"], kv["ts"]
    }
  }'
```

```bash
bash normalize.sh | bash detect.sh 5 60
echo "exit=$?"
```

**Do (PowerShell, est.).** Save as `detect.ps1`.

```powershell
# detect.ps1 [-Threshold 5] [-Window 60] [-HoursFile hours.txt]   (normalized lines on the pipeline)
# Same two rules as detect.sh. Every line is only compared, never run. One day of input only.
# [CmdletBinding()] makes this an advanced script so the pipeline binds each line to $Line.
[CmdletBinding()]
param(
    [int]$Threshold = 5,
    [int]$Window = 60,
    [string]$HoursFile = '',
    [Parameter(ValueFromPipeline = $true)][string]$Line
)
begin {
    $times = @{}; $muted = @{}; $from = @{}; $to = @{}; $firstDay = $null
    if ($HoursFile -ne '') {
        foreach ($l in Get-Content $HoursFile) { $f = $l -split ' '; $from[$f[0]] = [int]$f[1]; $to[$f[0]] = [int]$f[2] }
    }
}
process {
    if (-not $Line) { return }
    $kv = @{}
    foreach ($pair in ($Line -split ' ')) { $a = $pair -split '=', 2; $kv[$a[0]] = $a[1] }
    $day = $kv['ts'].Substring(0, 10)
    if ($null -eq $firstDay) { $firstDay = $day }
    if ($day -ne $firstDay) { throw 'input spans more than one day; this toy compares times within a day' }
    $t = [TimeSpan]::Parse($kv['ts'].Substring(11, 8)).TotalSeconds
    if ($kv['action'] -eq 'login_failed') {
        $ip = $kv['src']
        if (-not $times.ContainsKey($ip)) { $times[$ip] = @() }
        $times[$ip] = @($times[$ip] | Where-Object { $t - $_ -le $Window }) + $t
        if ($times[$ip].Count -ge $Threshold -and (-not $muted.ContainsKey($ip) -or $t - $muted[$ip] -gt $Window)) {
            'ALERT brute_force src={0} failures={1} window={2}s at={3}' -f $ip, $times[$ip].Count, $Window, $kv['ts']
            $muted[$ip] = $t
        }
    }
    elseif ($HoursFile -ne '' -and $kv['action'] -eq 'login_ok' -and $from.ContainsKey($kv['user'])) {
        $hr = [math]::Floor($t / 3600)
        if ($hr -lt $from[$kv['user']] -or $hr -ge $to[$kv['user']]) {
            'ALERT off_hours user={0} src={1} at={2}' -f $kv['user'], $kv['src'], $kv['ts']
        }
    }
}
```

```powershell
.\normalize.ps1 | .\detect.ps1 -Threshold 5 -Window 60
```

**Check.**

```text
ALERT brute_force src=203.0.113.9 failures=5 window=60s at=2026-10-22T03:14:33Z
ALERT brute_force src=192.0.2.10 failures=5 window=60s at=2026-10-22T14:20:51Z
exit=0
```

Two alerts. `203.0.113.9` fires on its fifth failure, at 03:14:33 (the sixth, at 03:14:41, is inside the quiet period). `192.0.2.10` fires at 14:20:51. `198.51.100.23` does not, because one failure is not five. Now the uncomfortable part: look at who `192.0.2.10` is. It is `bob`, who got the password wrong five times and then succeeded. The rule fired on a person having a bad minute. That is a **false positive**, and the rule cannot tell the difference, because "five failures in a minute" is all it knows.

Also notice what did *not* fire: the three `401`s on the web login. The rule reads only `login_failed`, which only SSH produces. Normalizing made it possible to count the web failures with the SSH ones; it does not do it for you. A rule covers the sources and actions it names.

**Undo.** Nothing to undo; the script only reads standard input.

### Exercise 6: tune the threshold, and count the cost

**Predict.** If you raise the threshold from 5 to 6, which of the two alerts goes away? If you raise it to 7? If you lower it to 3 or 4, do any new alerts appear on this file? Write the number of alerts you expect for thresholds 3, 4, 5, 6 and 7.

**Do (Bash).**

```bash
for n in 3 4 5 6 7; do echo "threshold=$n alerts=$(bash normalize.sh | bash detect.sh $n 60 | wc -l)"; done
```

**Do (PowerShell, est.).**

```powershell
foreach ($n in 3..7) { $c = (.\normalize.ps1 | .\detect.ps1 -Threshold $n -Window 60 | Measure-Object).Count; "threshold=$n alerts=$c" }
```

**Check.**

```text
threshold=3 alerts=2
threshold=4 alerts=2
threshold=5 alerts=2
threshold=6 alerts=1
threshold=7 alerts=0
```

At 6, `bob` goes quiet (he made five attempts) and the guesser still fires (it made six). At 7, both are silent. The trade-off is now visible as a table. Threshold 6 removes the false positive, and also means an attacker who tries five passwords a minute and then waits may never be seen. There is no setting that is right for every network: the threshold depends on how often real users fail, how fast real guessing runs, and how many alerts someone can read. Writing down *why* you chose a number (and when you will look at it again) is part of the work, which is what the [change management](Enterprise-Change-Management-for-Beginners.md) habit is for.

For reference, Wazuh's own SSH brute-force rule (number 5763 in the ruleset on the master branch, read 2026-10-22) uses `frequency="8" timeframe="120" ignore="60"` with `same_source_ip`: eight matching failures from one address within 120 seconds, then quiet for 60. That is looser than five in sixty. Both are defensible; they are different answers to the same trade-off, and the ruleset is free to change, so check the current file rather than trusting this page.

**Undo.** Nothing to undo.

### Exercise 7: a baseline instead of a rule

**Predict.** A rule needs someone to say what bad looks like. A baseline learns what normal looks like. Alice's sign-ins over two weeks all fall between 08:00 and 16:59. Her sign-in at 03:40 from `203.0.113.50` was not a failure, so the failed-login rule ignores it. Will a baseline catch it? And will it catch `bob`'s success?

**Do (Bash).** Save as `mkbaseline.sh`. It builds an invented two-week history for Alice, learns her usual hours from it and writes `hours.txt`, the file `detect.sh` reads as its optional third argument.

```bash
#!/usr/bin/env bash
# mkbaseline.sh - builds a SYNTHETIC two-week login history for one invented user, then learns
# her usual hours from it and writes hours.txt in the form detect.sh reads.
set -eu
: > history.log
for d in $(seq 1 14); do
  hour=$((8 + (d * 5) % 9))
  printf 'Oct %2d %02d:%02d:00 demo-host sshd[1000]: Accepted publickey for alice from 198.51.100.7 port 40022 ssh2\n' \
    "$d" "$hour" $((d * 7 % 60)) >> history.log
done
awk '/Accepted .* for alice / { split($3, t, ":"); h = t[1] + 0; if (lo == "" || h < lo) lo = h; if (h > hi) hi = h }
     END { printf "alice %d %d\n", lo, hi + 1 }' history.log > hours.txt
echo "learned from $(wc -l < history.log) logins:"; cat hours.txt
```

```bash
bash mkbaseline.sh
bash normalize.sh | bash detect.sh 5 60 hours.txt
```

**Do (PowerShell, est.).** Save as `mkbaseline.ps1`.

```powershell
# mkbaseline.ps1 - SYNTHETIC two-week history for one invented user; learns her usual hours
# and writes hours.txt in the form detect.ps1 reads.
$lines = foreach ($d in 1..14) {
    $hour = 8 + ($d * 5) % 9
    'Oct {0,2} {1:00}:{2:00}:00 demo-host sshd[1000]: Accepted publickey for alice from 198.51.100.7 port 40022 ssh2' -f $d, $hour, ($d * 7 % 60)
}
Set-Content -Path history.log -Value $lines -Encoding ascii
$hours = $lines | ForEach-Object { [int]$_.Substring(7, 2) }
$lo = ($hours | Measure-Object -Minimum).Minimum
$hi = ($hours | Measure-Object -Maximum).Maximum
Set-Content -Path hours.txt -Value ('alice {0} {1}' -f $lo, ($hi + 1)) -Encoding ascii
"learned from $($lines.Count) logins:"; Get-Content hours.txt
```

```powershell
.\mkbaseline.ps1
.\normalize.ps1 | .\detect.ps1 -Threshold 5 -Window 60 -HoursFile hours.txt
```

**Check.**

```text
learned from 14 logins:
alice 8 17
ALERT brute_force src=203.0.113.9 failures=5 window=60s at=2026-10-22T03:14:33Z
ALERT off_hours user=alice src=203.0.113.50 at=2026-10-22T03:40:12Z
ALERT brute_force src=192.0.2.10 failures=5 window=60s at=2026-10-22T14:20:51Z
```

The new `off_hours` alert is the 03:40 sign-in, which no failed-login rule would ever catch, because it did not fail. Alice's 09:00 and 09:02 sign-ins are inside her hours and stay quiet; `bob` is not in the file, so he is never judged by this rule. Three honest limits: the baseline only knows about users it was taught, so a new user is invisible; it learned a *range* of hours, so a sign-in at 16:30 on a Sunday looks normal; and it is only as honest as the history. An attacker already present during the two weeks becomes part of "normal". Baselines raise their own false positives too (Alice travels, or works a shift). The usual answer is both: rules for the things you know are bad, baselines for the things you cannot list.

**Undo.** `rm history.log hours.txt` (PowerShell: `Remove-Item history.log, hours.txt`). The earlier exercises do not need them.

### Exercise 8: look at your own machine's real logs (read-only)

This is the only exercise that reads real data. It only reads, sends nothing and changes nothing. **Do not paste what it prints into a public place**: real logs contain your machine's name, your user name and addresses.

**Predict.** Does your machine have a `/var/log/auth.log`? What is the newest event in the journal? What kind of message is it?

**Do (Bash, Linux with systemd).**

```bash
journalctl -n 5 --no-pager -o short-iso
journalctl -p warning -n 5 --no-pager
ls -l /var/log/auth.log
timedatectl | grep -i synchronized
```

**Do (PowerShell, est.).** The first needs no special rights; the second needs an elevated prompt and fails with "no events were found" if the machine has no such events.

```powershell
Get-WinEvent -LogName Application -MaxEvents 5 | Format-List TimeCreated, ProviderName, Id, Message
Get-WinEvent -FilterHashtable @{ LogName = 'Security'; Id = 4625 } -MaxEvents 5
```

**Check.** `short-iso` prints a full date, a time and a time zone offset, which is the shape syslog's old format lacks. On a minimal Debian-based system `auth.log` may not exist at all, with the messages only in the journal; if you do see it, its lines look like the ones in your fake `auth.log`. If the journal says you may not read system messages, you need to be in a group such as `systemd-journal` or `adm` (**est.**, distribution-dependent), or run it with your administrator rights. The `synchronized` line should say `yes`. On Windows, a `4625` is a failed sign-in; if you find some, the `Logon Type` and `Source Network Address` fields tell you how and from where.

**Undo.** Nothing to undo.

## Optional: your own accounts

Nothing above needs an account. If you want to see these ideas on a running stack, two things in this wiki use your own machine or account. The reading and the exercises on this page are free and always will be; this part uses your own hardware or provider bill.

- **A synthetic monitoring stack on your own computer.** [Lab: a synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md) runs Prometheus and Grafana in containers on your machine and needs no cloud account. Cost: **$0**. It shows metrics, the NOC half, and not logs. Teardown: `scripts/demo_monitoring.sh down` (the lab page explains it).
- **A cloud mini SOC in your own account.** [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) builds it in stages. The page's cost table is computed from [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json) (retrieved 2026-10-21 for the droplet prices below); read [the project's cost explanation](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) first. A single `s-1vcpu-1gb` droplet is **$6 a month** at list price, an `s-1vcpu-2gb` is **$12** and an `s-2vcpu-2gb` is **$18** (bundled-plan droplets are billed per second, with a minimum of 60 seconds or $0.01, from creation until you **destroy** them; a powered-off one is still billed, per [DigitalOcean's pricing page](https://docs.digitalocean.com/products/droplets/details/pricing/), read 2026-10-22; [Teardown checklist](Teardown-Checklist.md) lists what to remove). The mini SOC page lists the totals with the reference environment around them. **Teardown first:** the page's [Tear it down](Build-Your-Own-Mini-SOC.md#tear-it-down) section lists the steps, and a stage you cannot remove is a bill you cannot stop. Whether the log shipping side works on a real machine is not verified; the [stage 2 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md) says so.

Do not point the exercises' detection ideas at a machine that is not yours, and never log in "to test" a rule against someone else's host.

## Build, break, detect, evade, defend (the local loop)

The same loop the rest of the project uses ([Why this exists](Why-This-Exists.md)), on a failed-login rule. You need the files from Exercises 3 to 7 and nothing else. All of it runs on your computer against the invented logs; no real login happens anywhere.

**Build.** The rule from Exercise 5: five failed logins from one source in sixty seconds. You built it, tested it on a file you control, and know it fires twice.

**Break.** Add four failed logins from a new source, `198.51.100.88`, inside a minute, and run the rule again.

```bash
for i in 0 1 2 3; do
  printf 'Oct 22 16:00:%02d demo-host sshd[3000]: Failed password for root from 198.51.100.88 port 5%d ssh2\n' $((i*10)) $i >> auth.log
done
bash normalize.sh | bash detect.sh 5 60
```

PowerShell (**est.**):

```powershell
0..3 | ForEach-Object { 'Oct 22 16:00:{0:00} demo-host sshd[3000]: Failed password for root from 198.51.100.88 port 5{1} ssh2' -f ($_ * 10), $_ } | Add-Content -Path auth.log -Encoding ascii
.\normalize.ps1 | .\detect.ps1 -Threshold 5 -Window 60
```

**Detect.** Predict first: does the new source alert? It does **not**. The output is the same two alerts as before.

```text
ALERT brute_force src=203.0.113.9 failures=5 window=60s at=2026-10-22T03:14:33Z
ALERT brute_force src=192.0.2.10 failures=5 window=60s at=2026-10-22T14:20:51Z
```

Four is less than five. The rule did exactly what you told it to; the new source is an attacker's four guesses, and nobody is told. Run `bash normalize.sh | bash detect.sh 4 60` to see it fire (three alerts, the third for `198.51.100.88`, and the other two a failure earlier). This is a **false negative**, and it is the threshold working as written. A rule that fires on `N` and an attacker who knows (or guesses) `N - 1` is the oldest game in detection.

**Evade.** Now describe, and then build, the careful visitor. Someone who guesses slowly does not put five failures in one minute. Add eight guesses from `203.0.113.77`, twenty minutes apart, starting at 02:00, and run the same rule.

```bash
for i in 0 1 2 3 4 5 6 7; do
  m=$((i*20))
  printf 'Oct 22 %02d:%02d:00 demo-host sshd[3100]: Failed password for invalid user guest from 203.0.113.77 port 6%d ssh2\n' $((2 + m/60)) $((m%60)) $i >> auth.log
done
bash normalize.sh | bash detect.sh 5 60
```

PowerShell (**est.**):

```powershell
0..7 | ForEach-Object { $m = $_ * 20; 'Oct 22 {0:00}:{1:00}:00 demo-host sshd[3100]: Failed password for invalid user guest from 203.0.113.77 port 6{2} ssh2' -f (2 + [math]::Floor($m / 60)), ($m % 60), $_ } | Add-Content -Path auth.log -Encoding ascii
.\normalize.ps1 | .\detect.ps1 -Threshold 5 -Window 60
```

The output is still the same two alerts, and the file now holds eight more failed logins that the rule never counts. This is named so you recognize it, not so you can use it. It is a description of how a patient attacker beats a short window: the rule's idea of "too many" is only the right idea inside its window. Do not try this against any host that is not yours; the only target here is a text file.

**Defend.** Two changes, both tuning and a second rule.

First, widen the window, so slow guessing adds up:

```bash
bash normalize.sh | bash detect.sh 5 7200
```

```text
ALERT brute_force src=203.0.113.9 failures=5 window=7200s at=2026-10-22T03:14:33Z
ALERT brute_force src=203.0.113.77 failures=5 window=7200s at=2026-10-22T03:20:00Z
ALERT brute_force src=192.0.2.10 failures=5 window=7200s at=2026-10-22T14:20:51Z
```

PowerShell (**est.**): `.\normalize.ps1 | .\detect.ps1 -Threshold 5 -Window 7200`.

The slow guesser now fires, at 03:20, on its fifth attempt about 80 minutes in. Notice what it cost: a wider window also makes a user who fumbles five logins over two hours look like an attack, so the false-positive side gets worse, and `198.51.100.88` (four guesses) still slips under five. There is no free setting. Second, add a different kind of rule so you are not betting everything on one threshold: the off-hours baseline from Exercise 7 (`bash normalize.sh | bash detect.sh 5 60 hours.txt`). Two rules that fail in different ways are worth more than one rule tuned to perfection. Put each in front of a person with a sentence on what to do about it, or you have only made more noise.

**Undo.** Re-run the setup script (`bash mklogs.sh`) to put the logs back. The loop does not change anything outside the lab folder.

### Flip the board

You wrote the rule. Now do the other two jobs.

**The attacker.** You are guessing passwords against a host you are *allowed* to test, say your own lab machine, and you know the owner runs "five failures in sixty seconds". List three ways to stay under it, and for each the extra thing a defender could watch to catch it anyway. (Answers in the details below.)

<details>
<summary>What to find</summary>

1. **Slow down.** One guess a minute stays under any short window. A defender watches *totals over a long window* (hours), or counts distinct usernames tried from one source.
2. **Spread out.** One guess each from hundreds of addresses never gives any single address five. A defender counts failures per *account* (many sources, one target username), not only per source.
3. **Spray.** Try one common password against many accounts, so each account sees one failure. A defender counts distinct usernames tried from one source in a window, or failures across the whole service.
4. **Use something that is not a failure.** A stolen working password or key produces a clean `Accepted` line. A defender needs the second rule, a baseline: a new source, an odd hour, an unusual place.
5. **Delete or rewrite the log afterward.** A defender ships logs off the machine as they are written, so the local copy is not the only one ([why telemetry leaves the machine](Cloud-Telemetry-What-and-Why.md#why-telemetry-has-to-leave-the-machine)).

</details>

**The reviewer.** You are given this proposed rule and asked whether it is ready to deploy. Find at least four problems without running it.

```text
Rule: alert when the text "Failed password" appears 3 times in auth.log, any source, any time.
Severity: critical, page the on-call engineer.
```

<details>
<summary>What to find</summary>

1. **No window.** "Any time" means failures spread over a year add up. The rule needs a time window.
2. **No grouping.** "Any source" counts three different people's typos together. It should count per source address (and perhaps per account).
3. **Three is very low**, and `critical` with a page is the loudest possible response. This will fire daily and teach the on-call engineer to ignore it: alert fatigue by design. Severity should match what the alert means and what a person should do.
4. **It matches text, not a field.** A user named `Failed password` or a log line that contains the phrase in another place would count. Parse first, then compare fields.
5. **It misses the invalid-user variant** if the pattern is anywhere less careful than Exercise 2's, and misses every other source (the web login, Windows 4625).
6. **No tuning plan, no owner and no review date.** Nobody will know when it should be changed or removed.

</details>

## Checkpoint

- What are the four things in a log line, and what two things does the old syslog timestamp leave out?
- Why did the first regular expression in Exercise 2 find 8 and not 12?
- What is the difference between parsing and normalizing, and what does normalizing let one rule do?
- What is the difference between a rule and a baseline, and what is each bad at?
- Give one false positive and one false negative from this page, and say what each costs.
- Why does a seven-minute clock difference make an investigation wrong, even if every log is complete?
- A teammate says "we have a SIEM, so we're covered". What three questions do you ask?

Answers are in the sections above. (For the last: which sources actually feed it, and which are missing? Which rules run on them, and when did someone last read an alert and act? Where do the logs live if the machine is lost?)

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| The rule finds nothing on a log you know has failures | The pattern misses a variant of the line (the invalid-user case), or the file is not the format you think | Count with the loosest pattern (`Failed password`) and then tighten it; compare counts |
| The rule fires twice for one event | Two sources carry the same event (the journal and `auth.log` both have `sshd`) | Drop one source or deduplicate in the pipeline. The stage 2 guide warns about exactly this |
| Events from two machines appear in the wrong order | Clocks differ, or one log has no time zone | `timedatectl`, NTP, and log in UTC with the zone written |
| A detector fails on the second day | The toy compares times within one day | The script says so and stops. A real tool uses full dates |
| Alerts nobody reads | Too many, too similar, no instruction | Fewer, tuned alerts; one sentence of "what to do" each; remove rules that were never real |
| A baseline alerts every Monday | The baseline learned only weekdays or one shift | Longer, more varied history; per-day-of-week baselines |
| A PowerShell script will not run | Execution policy, or running it from the wrong folder | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for this window only, and `.\` before the name (**est.**) |
| `awk` errors on macOS | The built-in `awk` differs from the GNU one | Install GNU awk, or use PowerShell or WSL 2 (**est.**; not tested) |

## Claims register

All read-only requests; retrieved 2026-10-22 unless stated. "Observed" means I ran it that day.

| Claim | Source | Status |
|---|---|---|
| The BSD syslog protocol is an Informational RFC (2001) documenting existing practice; its timestamp is local time in the form `Mmm dd hh:mm:ss`, which has no year | [RFC 3164](https://www.rfc-editor.org/rfc/rfc3164) | Read the category, the date and the timestamp section |
| The newer syslog header is PRI, version, timestamp, host name, application name, process id and message id; its timestamp follows RFC 3339 (full date, time and zone) | [RFC 5424](https://www.rfc-editor.org/rfc/rfc5424) | Read the header grammar and the timestamp section |
| `systemd-journald` collects kernel messages, syslog calls, structured messages, service output and audit records into structured, indexed journals | [systemd-journald(8)](https://man7.org/linux/man-pages/man8/systemd-journald.service.8.html) | Read |
| `journalctl` has `-u`/`--unit`, `-p`/`--priority`, `-S`/`--since`, `-n` and `-o` with `short-iso` and `json` among its outputs | [journalctl(1)](https://man7.org/linux/man-pages/man1/journalctl.1.html) | Read; `-n` and `-o short-iso` observed |
| The Common Log Format is `%h %l %u %t "%r" %>s %b` | [Apache HTTP Server: Log Files](https://httpd.apache.org/docs/2.4/logs.html) | Read |
| Windows event 4625 is a failed logon and carries a Logon Type, a Source Network Address and a Failure Reason; 4624 is a successful logon | [4625](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4625), [4624](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4624) (Windows 10 pages) | Read the titles and field names. The pages are in Microsoft's "previous versions" area, so a newer Windows may differ |
| `Get-WinEvent` has a `-FilterHashtable` parameter set and a `-MaxEvents` parameter | [Get-WinEvent](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent) | Read; never run |
| `auditctl` documents `-w path`, `-p` permissions and `-k key`, and calls the watch form deprecated in favor of syscall rules | [auditctl(8)](https://man7.org/linux/man-pages/man8/auditctl.8.html), [audit.rules(7)](https://man7.org/linux/man-pages/man7/audit.rules.7.html) | Read. Whether the repository's `-w` rules load as written on a given audit version is **est.** |
| The repository's auditd rules (`-a always,exit` file rules) cover `/etc/passwd`, `group`, `shadow`, `gshadow` (`cah_identity`), `sudoers` and `sudoers.d` (`cah_sudo`) and `/etc/twingate/` (`cah_twingate`); the agent reads the journal for `twingate-connector`, `ssh`/`sshd` and `sudo`, plus `auth.log` and `audit.log`; `sshd` events arrive from both sources | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` and `docs/stages/02-telemetry.md` section 2.4, as of this page's commit | Read in this repository. Not applied to any real machine |
| Wazuh rules accept `frequency` (matches before alert), `timeframe` (seconds), `ignore` (seconds quiet) and `same_srcip` (same source address) | [Wazuh rules syntax](https://documentation.wazuh.com/current/user-manual/ruleset/ruleset-xml-syntax/rules.html) | Read |
| Wazuh rule 5763 (sshd brute force, authentication failed) uses `frequency="8" timeframe="120" ignore="60"`, `same_source_ip`, MITRE T1110 Brute Force | [0095-sshd_rules.xml](https://raw.githubusercontent.com/wazuh/wazuh/master/ruleset/rules/0095-sshd_rules.xml) on the master branch | Read the file; the ruleset can change at any time |
| Loki indexes only the labels of a log stream and stores the log text compressed in chunks | [Grafana Loki documentation](https://grafana.com/docs/loki/latest/) | Read the overview; I did not run Loki and the repository does not use it |
| Suricata describes itself as a high performance network IDS, IPS and network security monitoring engine | [What is Suricata](https://docs.suricata.io/en/latest/what-is-suricata.html) | Read |
| NIST SP 800-92, "Guide to Computer Security Log Management", was published September 2006 | [NIST CSRC](https://csrc.nist.gov/pubs/sp/800/92/final) | Read the publication page (date and title); the guide's text was not read in full, so the "reasons organizations keep logs" paragraph is a summary of its stated purpose and **est.** as to detail. The document is old |
| NTP version 4 is specified in RFC 5905 | [RFC 5905](https://www.rfc-editor.org/rfc/rfc5905) | Read the title only |
| `timedatectl` prints "System clock synchronized" and "NTP service"; `set-ntp` controls network time synchronization | [timedatectl(1)](https://man7.org/linux/man-pages/man1/timedatectl.1.html) | Read; the `synchronized` line observed |
| The definitions of IPS blocking, EDR, SOC and alert fatigue, and the invented alert arithmetic | General knowledge and [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) | **est.**; no vendor page was read for EDR. The arithmetic uses invented numbers |
| Droplet prices `s-1vcpu-1gb` $6, `s-1vcpu-2gb` $12, `s-2vcpu-2gb` $18 a month | `docs/cost-prices.json`, retrieved 2026-10-21 | Read in this repository |
| Bundled-plan droplets are billed per second (minimum 60 seconds or $0.01); billing ends when the droplet is destroyed; powered-off bundled droplets are still billed | [Droplet pricing](https://docs.digitalocean.com/products/droplets/details/pricing/) | Read |
| The script outputs on this page (alert lines, counts, sweep table, normalized lines) | Run on 2026-10-22 with GNU Awk 5.2.1 and with mawk 1.3.4 | Observed; identical under both |

Not verified, plainly: every PowerShell script and command on this page (written from Microsoft's documentation, never run, with a real chance of a typo in a quoting or a format string); every Windows event log command; the macOS `awk` note; the `sudo`-free `journalctl` group names; whether `/var/log/auth.log` exists on your Linux (it did not on the test machine); whether the Wazuh rule shapes quoted here behave as read when loaded into a manager; whether the stage 2 agent, its `auditd` rules and the opt-in log shipping work on a real machine; and the NIST guide's content beyond its abstract and date.

Next: [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md), the first of the five telemetry pages.
