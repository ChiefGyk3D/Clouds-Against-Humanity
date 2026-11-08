# Network, log and timeline forensics: packet captures, logs and plaso

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. The lab in this page was run once, on 2026-11-07, in two containers I created; the Windows event log, journald tamper-evidence and legal parts were read from documents, not run.** I ran a small web server, captured its traffic with tcpdump, read the capture with tshark 4.4.19 (Debian 13), and built a timeline with plaso 20261027 on Ubuntu 26.04. I did not run Wireshark's graphical interface, a Windows machine, or Timesketch. What failed is listed under [what I ran and what failed](#what-i-ran-and-what-failed). Trust what your terminal prints over what this page says.

> **Prerequisites.** You can run a command in a terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)), you know what a log line is ([Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md)), and you have met Wireshark once ([Security tools: Wireshark](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md#wireshark)). A container engine (Docker or Podman) for the exercise. About 90 minutes for the reading and the exercise (est.).

> **Where this runs, and the rule.** The exercise runs in two containers on a private container network on your own computer, against a web server you start, with traffic you generate. Capturing traffic on a network you do not own or are not authorized to monitor can be a crime (see [the law](#the-law-and-the-rule)). Do not point any of this at a real incident, a workplace network or anyone else's data. No exercise here needs real evidence.

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says (and the gap)](#what-the-wiki-already-says-and-the-gap)
- [The law and the rule](#the-law-and-the-rule)
- [Preserve first: the capture is evidence](#preserve-first-the-capture-is-evidence)
- [What a pcap can and cannot prove](#what-a-pcap-can-and-cannot-prove)
- [Following a stream and extracting objects](#following-a-stream-and-extracting-objects)
- [Encrypted traffic: what is left](#encrypted-traffic-what-is-left)
- [Log sources and how far to trust them](#log-sources-and-how-far-to-trust-them)
- [Tampering and log gaps](#tampering-and-log-gaps)
- [Clock skew and time zones: the classic mistake](#clock-skew-and-time-zones-the-classic-mistake)
- [Building a super timeline with plaso](#building-a-super-timeline-with-plaso)
- [Correlating pcap, logs and disk](#correlating-pcap-logs-and-disk)
- [Writing it up](#writing-it-up)
- [What I ran and what failed](#what-i-ran-and-what-failed)
- [Free exercise: a capture and a timeline you make yourself](#free-exercise-a-capture-and-a-timeline-you-make-yourself)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

## What you will be able to do

- Preserve a capture file as evidence: hash it first, make it read-only, work on copies, write the hash down.
- Say what a pcap proves, what it only suggests and what it cannot show.
- Follow a TCP stream and pull a transferred file out of a capture with tshark.
- Say what you can still learn from a capture of encrypted traffic, and what you cannot.
- Rank log sources by how far you can trust them, and name the signs of tampering and of a gap.
- Explain the classic timeline mistake (a clock or time zone nobody wrote down) and fix it with an anchor event.
- Build a timeline from a log with plaso, read it, filter it by time, and say what each timestamp is.
- Write a four-line finding that separates what you saw from what you infer.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Wireshark as a packet analyzer, plain-text credentials on the wire | [Security tools: Wireshark](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md#wireshark) | Treating the capture as evidence: hashing, copies, what it proves |
| Reading a capture offline, a synthetic pcap | [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md) | Following a stream and extracting objects instead of matching rules |
| Where logs live, parsing, rules | [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) | How far to trust each source, tampering, gaps |
| A small detection stack | [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) | After the alert: reconstructing what happened |
| Who the client address really is behind a proxy | [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) | Why a log line's address may be the proxy's, and what that does to a timeline |
| Hashes and keys | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) | A hash used as a seal on a file you may have to defend later |

This page is one of a series on digital forensics. The siblings are the [foundations lesson](Digital-Forensics-Foundations-Evidence-Handling-Chain-of-Custody-and-Order-of-Volatility.md), the [disk and Autopsy lesson](Disk-Forensics-with-Autopsy-and-The-Sleuth-Kit.md), the [memory lesson](Memory-Forensics-Acquiring-RAM-and-Analyzing-It-with-Volatility-3.md) and the [toolkits lesson](DFIR-Toolkits-and-Live-Triage-SIFT-Velociraptor-KAPE-and-the-Incident-Response-Workflow.md).

## The law and the rule

Capturing packets is interception. In the United States, 18 U.S.C. 2511(1)(a) reaches anyone who "intentionally intercepts" a wire, oral or electronic communication, and 2511(4)(a) sets a penalty of a fine, up to five years in prison, or both. There are exceptions: a party to the communication, or a party who has given prior consent, is not covered under 2511(2)(d) (unless the purpose is a crime or tort), and a service provider's staff may intercept as a necessary incident to running the service or protecting its rights or property under 2511(2)(a)(i). I read those lines on 2026-11-07 (source in the register). I am not a lawyer and this is not legal advice; other countries differ, and a workplace policy can bind you where the statute does not.

The working rule is shorter: capture only networks you own, or ones where you hold written authorization that names the network, the dates and what you may keep. Everything on this page runs on a container network you create on your own computer. If you are asked to capture traffic for an investigation, get the authorization first and ask counsel what you may collect. A capture holds everything that crossed the wire, including other people's data; collect the least that answers the question.

## Preserve first: the capture is evidence

Three rules carry most of the weight, and the first two are not tool features, they are habits.

1. **Hash it the moment you have it.** A hash is a fingerprint of the file ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)). If the file changes by one bit later, the hash changes. Record the hash, the time and who recorded it somewhere other than the same disk.
2. **Never edit the original; work on copies.** Opening a capture in a tool does not change it. Saving, filtering and "exporting specified packets" write new files. Do that to a copy, and name the copy for what it is.
3. **Write down where it came from.** Which interface, which machine, what filter, which clock, who started it. A classic pcap file stores none of that (see below), so it lives in your notes or it is lost.

RFC 3227, "Guidelines for Evidence Collection and Archiving" (February 2002), puts the same idea as "Minimi[z]e changes to the data as you are collecting it," and it orders sources from most to least volatile: registers and cache; routing table, ARP cache, process table, kernel statistics, memory; temporary file systems; disk; remote logging and monitoring data; physical configuration and topology; archival media. A packet capture is volatile in a different way: if you did not start capturing before the event, that traffic is gone. For time it asks you to "Note the difference between the system clock and UTC", to "indicate whether UTC or local time is used" for each timestamp, and to "Record the extent of the system's clock drift." Those three sentences are the whole [clock skew](#clock-skew-and-time-zones-the-classic-mistake) section of this page. NIST SP 800-86, "Guide to Integrating Forensic Techniques into Incident Response" (final, August 2006), is the longer treatment, with network traffic as one of its data sources; both documents are old, and the principles outlast the tools they name.

## What a pcap can and cannot prove

A packet capture ("pcap") is a file of packets with a timestamp each. In the lab below the file is a classic pcap with Ethernet frames and microsecond timestamps (`capinfos` says so). What it can support:

| It can show | It cannot show |
|---|---|
| That these bytes crossed this link at these times, in this order | That the capture point saw everything (a switch, a firewall or a filter may have hidden traffic) |
| Which addresses and ports talked, and for how long and how much | Who was at the keyboard. An address is a machine or a proxy, not a person |
| Plain-text content: URLs, headers, form fields, files | Anything inside encryption you cannot decrypt |
| For TLS: the handshake, the name the client asked for, sizes and timing | What the user did inside the TLS session |
| Absence on this link in this window | Absence anywhere else |

Two limits catch beginners. First, a pcap shows traffic at the capture point, so "no packets" means "none here". Second, the time in the file is the capturing machine's clock at capture time. If that clock was wrong, every packet is wrong by the same amount, and nothing in the file says so. The pcapng format can store interface and capture comments; the classic format cannot, which is why your notes matter. (That pcapng stores metadata and classic pcap does not: **est.**, from my memory of the formats, not checked against the specification.)

Also: a pcap is an observation, and a finding built on it is an inference. "The client sent a POST to `/login` with this body at this time" is an observation. "Alice logged in" is an inference.

## Following a stream and extracting objects

The lab below produces a six-request capture. These are the commands I ran with tshark 4.4.19, and what they printed. The capture was `lab.pcap`, 54 packets over 3.08 seconds.

List the HTTP requests and responses with their epoch times:

```bash
tshark -r /ev/lab.pcap -Y http -T fields -e frame.time_epoch -e ip.src -e ip.dst \
  -e http.request.method -e http.request.uri -e http.response.code
```

It printed one line per message, for example the login request and its answer (addresses are the private ones my container engine handed out; yours will differ):

```text
1794066617.819420000	10.89.0.6	10.89.0.5	POST	/login
1794066617.821248000	10.89.0.5	10.89.0.6		/login	200
```

List the TCP conversations (`-q -z conv,tcp`): three to port 8080 of 12 frames each and one to port 8443 of 18 frames.

Follow the third stream, the login, as text (`-q -z follow,tcp,ascii,2`). The request body was readable:

```text
POST /login HTTP/1.1
Host: cah477-srv:8080
User-Agent: labbrowser
Content-Length: 27
Content-Type: application/x-www-form-urlencoded

user=alice&pass=hunter2-lab
```

The password is a lab value I invented. It sat in the clear because the lab speaks plain HTTP, which is the point of the [Wireshark section](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md#wireshark) and of encrypting in transit.

Extract the files HTTP transferred (`-q --export-objects http,/objs`). It wrote four: `index.html` (3 bytes), `report.csv` (30 bytes), and `login` (27 bytes) plus `login(1)` (2 bytes), the request body and the server's reply, both named after the URL. Hash what you extract (`sha256sum /objs/*`) and write the hashes down; an extracted file is a derived item, and its hash proves you can get the same bytes from the same capture again. The `report.csv` I extracted hashed to the same value as the file on the server, which is the check that extraction gave back the same bytes (I compared the full SHA-256 of the extracted file with the one on the server: identical).

Wireshark's graphical interface does the same through Follow TCP Stream and File, Export Objects. I did not run the interface; the command line is what I can say I ran.

## Encrypted traffic: what is left

The lab also made one TLS connection (an `openssl s_server` on port 8443, a self-signed certificate for a name that does not exist). In the capture, tshark showed the Client Hello (handshake type 1) with the server name `cah477-srv` in the SNI field, then the Server Hello (type 2). The record layer version field showed `0x0303`, the legacy value that TLS 1.3 still carries. I did not see a certificate message in plain view. I did not check which protocol version was negotiated, so I will not say TLS 1.3 was used; the missing certificate is consistent with it, which is **est.**

What you keep with encrypted traffic: who talked to whom, when, how much, how long, and (while SNI is sent in clear) which name was requested. What you lose: the content. Wireshark can decrypt a session only with the session secrets. Its TLS page (read 2026-11-07) says browsers write them to a file when `SSLKEYLOGFILE` is set and Wireshark takes that file in its "(Pre)-Master-Secret log filename" preference, which "always enables decryption, even if a Diffie-Hellman (DH) key exchange is in use." It says a server's RSA private key works only "in a limited number of cases", one being that the cipher suite is not (EC)DHE. The consequence for evidence: unless someone logged the secrets while the session happened, a recording of an (EC)DHE session cannot be decrypted later, even with the server's key. Do not plan an investigation around decrypting a past capture; plan it around endpoint logs. I did not run a decryption.

## Log sources and how far to trust them

The [logs lesson](Logs-SIEM-and-Detection-Basics.md#where-logs-live) covers where logs live. The forensic question is different: how far can I rely on this one?

| Source | Who wrote it | What can go wrong | Trust, roughly |
|---|---|---|---|
| Web server access log | The web server, when it answers | Behind a proxy it logs the proxy's address ([real client IPs](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md)); the time is when the server logged it, which may be after the request started (**est.**) | Good for "this URL was asked for"; weak for "who" |
| Authentication log (`auth.log`, `secure`) | `sshd`, PAM, `sudo`, through syslog | Lines have no year or zone; root on the box can edit the file | Good, if shipped off the box in time |
| systemd journal | `journald` | Binary, so an edit is harder than with a text file, but the journal can be cleared or rotated away | Better than a text file; see sealing below |
| Windows event logs | The Windows event service | Can be cleared by an administrator; each channel has a size limit | Good, when forwarded elsewhere |
| A copy on a remote log server | A different machine | Only as good as the pipe that fed it, and its own clock | Best, because the intruder on the first box did not control it |
| The suspect's own application log | The application | Written by the thing you are investigating | Lowest |

The pattern: a log written on the machine that was compromised is evidence of what that machine said, not of what happened. RFC 3227 puts "remote logging and monitoring data" in its volatility list as its own tier for that reason.

**journald, concept level.** The journal collects kernel, service and syslog messages in a binary format ([journald in the glossary](Glossary.md)). `journald.conf(5)` (read 2026-11-07) says `Storage=auto` is persistent only when `/var/log/journal` exists, and volatile otherwise; a volatile journal is gone at reboot. It describes Forward Secure Sealing (`Seal=`) as protection that "may be used to protect journal files from unnoticed alteration", and that sealing needs a key set up. Sealing makes an edit noticeable; it does not stop deletion.

**Windows event logs, concept level.** I read one page. Event ID 1102 in the Security channel is written whenever the Windows Security audit log is cleared, and carries the account that did it (Microsoft Learn, archived page dated 2021-09-07, read 2026-11-07); Microsoft's note says to monitor it and "investigate why this action was performed." The same page names event 4624 as the successful-logon event, and its Logon ID is the field that links related events. Event 4625 (failed logon) and the System log's own clear event (104) I believe exist, but I did not read their pages: **est.** I did not open a Windows log on a Windows machine, so everything past this paragraph about Windows is from reading, not use.

## Tampering and log gaps

An attacker's easiest cover is deleting or editing the log. What it leaves behind:

- **A clear event.** Windows writes one. A text log on Linux writes nothing when someone truncates it.
- **A gap.** In my timeline below, a heartbeat job logs every 15 minutes, and the entries for 11:00 and 11:15 are missing (I deleted those two lines to make the example). The timeline shows 15:45 UTC, then 16:30 UTC. A gap tells you something stopped being written. It does not tell you why: the machine was off, the service stopped, the file rotated, a disk filled, or someone removed lines. The next step is to ask the other sources what they recorded during the gap.
- **Order that does not add up.** A line with a time earlier than the one before it, a sequence number that jumps, a process id that goes backwards without a reboot.
- **A mismatch between sources.** Your web log says nothing happened at a time your pcap shows a request. One of them is incomplete or lying, and you can often tell which.

The practical defense is off-box copies, which is the [log shipping](Logs-SIEM-and-Detection-Basics.md) idea from the logs lesson, and the habit of copying logs out and hashing them as soon as you suspect trouble.

## Clock skew and time zones: the classic mistake

Most wrong timelines are not wrong evidence. They are right evidence read in the wrong zone. Three distinct problems:

1. **Zone.** A traditional syslog line is `Nov  7 10:49:52 host sshd[811]: ...`: month, day and time. No year, no zone (you can see it in the file below). To put it on a timeline you must supply both.
2. **Skew.** A host's clock is simply off. RFC 3227 says to record the drift; you do that by finding an event that two sources both saw.
3. **Mixed zones.** One log in UTC, another in local time, a third in a user's zone. Each on its own is fine. Merged without conversion, they lie.

In the lab I made the mistake on purpose. I wrote `auth.log` as a machine would in a US Eastern zone (EST, UTC minus five hours on 2026-11-07, because daylight saving ended on 2026-11-01), and ran plaso twice over the same two files. With no zone given, plaso treated the syslog lines as UTC and put the SSH login at `2026-11-07T10:49:52+00:00`, five hours before the web requests that happened at 15:50 UTC. With `--timezone America/New_York` it put the same line at `2026-11-07T15:49:52+00:00`, minutes before them. Same bytes in, two different stories out.

The anchor method fixes skew. Find one event that two sources both recorded and compare. In my files, the web server logged `POST /login` at 15:50:17 UTC, and the pcap agrees to the second (epoch 1794066617). My synthetic `auth.log` has a `weblogin ... session started for user alice` line that, by construction, belongs to that same moment. After the zone fix it reads 15:57:19 UTC, 7 minutes 2 seconds late, so I would write down "this host's clock runs about seven minutes fast" and subtract. In a real case the anchor is a real event you can prove both saw (for example, a request that shows in the pcap and the access log), and you state the uncertainty: an offset measured at one moment tells you the offset at that moment, not an hour later.

Write every timestamp with its zone, convert everything to UTC for the timeline, and keep the original line next to the converted time.

## Building a super timeline with plaso

A **super timeline** is one table of events from many sources (logs, file system times, browser history, registry), sorted by time, so one pass shows what happened across all of them. **Plaso** is the open-source toolkit for it, and **log2timeline** is its extraction tool. The pipeline has three tools:

| Tool | Does |
|---|---|
| `log2timeline.py` | Reads a source (a file, a directory or a disk image), runs parsers, writes a `.plaso` storage file |
| `psort.py` | Reads the storage file, sorts and filters events, writes an output such as CSV |
| `pinfo.py` | Describes a storage file (I confirmed it exists in this version; I did not run it on a result) |

Facts read from the project on 2026-11-07: the GitHub repository `log2timeline/plaso` reports the license as Apache-2.0 and the latest release as `20261027` (published 2026-10-27; the next older were `20260720`, `20260512`, `20260119`), through the GitHub API; the PyPI page lists the same version, requiring Python 3.10 or newer. The plaso documentation says Ubuntu install goes through the GIFT PPA and the `plaso-tools` package, and that only Ubuntu 26.04 LTS ("resolute") is supported there; the SANS SIFT Workstation ships its own plaso builds. Plaso versions are dates, not numbers, so "recent" means a date.

Two things I checked that matter for this page. `log2timeline.py --info` on this version lists a `filestat` parser and many `text/...` plugins, and I searched its output for "pcap" and found nothing: **plaso did not offer a parser that reads a pcap in this version.** Network captures stay in tshark or Wireshark; you correlate by time. And parsers are named with their group: `text/apache_access` and `text/syslog_traditional`, not `apache_access` and `syslog` (my first attempt failed on that; see below).

The commands I ran, over a directory holding the two text logs:

```bash
log2timeline.py --quiet --status_view none \
  --parsers "text/apache_access,text/syslog_traditional" \
  --preferred_year 2026 --timezone America/New_York \
  --storage_file /out/ny2.plaso /src
psort.py --output_time_zone UTC -o dynamic --fields datetime,parser,message \
  -w /out/ny2.csv /out/ny2.plaso
```

`--preferred_year` supplies the year the syslog lines lack, and `--timezone` says what zone those lines were written in; the Apache access log carries its own `+0000`, so it needed neither. `--output_time_zone UTC` is the line that makes the output readable by everyone. It printed eleven events:

```text
datetime,parser,message
2026-11-07T15:30:01.000000+00:00,text/syslog_traditional,Cron ran: /usr/local/bin/heartbeat for user: root pid: 501
2026-11-07T15:45:01.000000+00:00,text/syslog_traditional,Cron ran: ... pid: 533
2026-11-07T15:49:41.000000+00:00,text/syslog_traditional,Unsuccessful connection of user: alice from 10.89.0.6:40122 ...
2026-11-07T15:49:44.000000+00:00,text/syslog_traditional,Unsuccessful connection of user: alice ...
2026-11-07T15:49:52.000000+00:00,text/syslog_traditional,Successful login of user: alice from 10.89.0.6:40122 ...
2026-11-07T15:49:52.000000+00:00,text/syslog_traditional,[sshd  pid: 811] pam_unix(sshd:session): session opened for user alice by (uid=0)
2026-11-07T15:50:15.000000+00:00,text/apache_access,http_request: GET /index.html HTTP/1.1 from: 10.89.0.6 code: 200 ...
2026-11-07T15:50:16.000000+00:00,text/apache_access,http_request: GET /report.csv HTTP/1.1 from: 10.89.0.6 code: 200 ...
2026-11-07T15:50:17.000000+00:00,text/apache_access,http_request: POST /login HTTP/1.1 from: 10.89.0.6 code: 200 ...
2026-11-07T15:57:19.000000+00:00,text/syslog_traditional,[weblogin  pid: 640] session started for user alice
2026-11-07T16:30:01.000000+00:00,text/syslog_traditional,Cron ran: /usr/local/bin/heartbeat for user: root pid: 702
```

### Reading and filtering a timeline

Read it as a story with questions, not a list. Here: two failed SSH logins and then a successful one for `alice`, the last 23 seconds before the first web request from the same address; the requests; the "session started" line seven minutes after the POST (which is the skew, not a delay); then the 15:45 to 16:30 gap in the heartbeat.

`psort.py` takes a filter expression after the storage file. I ran one for the incident window:

```bash
psort.py --output_time_zone UTC -o dynamic --fields datetime,parser,message \
  -w /out/win.csv /out/ny2.plaso \
  'date > "2026-11-07 15:49:00" AND date < "2026-11-07 15:58:00"'
```

It wrote 8 events (the file had 9 lines with the header). Narrow by time first, then by source.

One more thing I saw. When I pointed plaso at the directory with the `filestat` parser on, it also emitted file-system events for my copies: the timestamps were `2026-11-07T15:51:32`, the moment I copied the logs, not the 15:50 the requests happened. A file's own times describe the file, not what it contains. When you copy evidence, the copy has new times; compare the original's metadata first, and never read a copy's modified time as the incident.

## Correlating pcap, logs and disk

Put the three kinds of evidence on one axis and look for corroboration, not agreement of a single source.

| Question | Pcap | Log | Disk |
|---|---|---|---|
| Did a request happen? | Packets with a time | Access log line | Cache, history, dropped files |
| Who sent it? | Source address, maybe a proxy | Address and user agent | User profile, shell history |
| What was sent? | Body, if plain | Often only the URL | The file itself |
| When, really? | Capture host's clock | Logging host's clock | File system times, which copying changes |

In the lab, the pcap's `POST /login` at epoch 1794066617 matches the access log's `15:50:17 +0000` to the second, on the same host and clock. That is corroboration. The auth log's seven-minute offset is a different clock and needs the anchor. A good correlation names the clock behind every line.

The disk side (file system timestamps, deleted files, Autopsy) belongs to the [disk forensics lesson](Disk-Forensics-with-Autopsy-and-The-Sleuth-Kit.md) and memory to the [memory forensics lesson](Memory-Forensics-Acquiring-RAM-and-Analyzing-It-with-Volatility-3.md). The only disk-like evidence I used here is plaso's `filestat`.

## Writing it up

A finding is four lines, in this order. Mine for the lab:

1. **Observed.** At 15:50:17 UTC the capture and the web access log both show one `POST /login` from one address, whose body held the form fields `user=alice` and a password, in plain HTTP.
2. **Also observed.** The authentication log shows two failed and one successful SSH login for `alice` from the same address at 15:49:41 to 15:49:52 UTC, and a `weblogin` session line at 15:57:19 UTC.
3. **Inferred.** The `weblogin` line is the same event as the POST; its host clock is about seven minutes fast (7 minutes 2 seconds at that moment, from one anchor).
4. **Not shown.** Who was at the keyboard; whether the 11:00 and 11:15 heartbeat entries were removed or never written; anything inside the TLS session on port 8443.

Rules for the write-up: every time in UTC with the original beside it; every claim names its source file and hash; observed and inferred are different lines; say what you could not show. Someone who disagrees with you should be able to open your hashed files and reach the same lines.

## What I ran and what failed

Date: 2026-11-07. Machine: one Linux laptop, rootless Podman (the `docker` command here is Podman's emulation). Images: `debian:13` for the capture side (tshark 4.4.19, tcpdump 4.99.5, Python 3.13.5), and `ubuntu:26.04` plus the GIFT PPA `plaso-tools` for plaso (`log2timeline.py`, `psort.py`, `pinfo.py` all 20261027). The data is mine: a toy web server I wrote, one curl each for a page, a CSV and a login POST, and one curl against `openssl s_server`. The `auth.log` is hand-written, the heartbeat gap is a deletion I made, and its clock offset is an invention. Nothing real was captured.

What failed or surprised me:

- **tcpdump had no permission in the container.** The first run said "You don't have permission to perform this capture on that device (socket: Operation not permitted)." Rootless Podman did not grant raw sockets by default. `--cap-add NET_RAW` on the server container fixed it. I threw that first run away and started clean.
- **The first server logged each POST twice.** My handler called the log function itself and `send_response` called it too. I removed my call. Fixed before the evidence run.
- **I could not stop tcpdump from inside the container.** `kill` said "Permission denied" (tcpdump drops to its own user). The capture file was already complete because I ran tcpdump with `-U` (write each packet at once), and I stopped the container. A cleaner stop (a packet count or `timeout`) is **est.**; I did not test it.
- **plaso rejected my parser names.** "Unknown parser or plugin names in element(s)" for `apache_access,syslog`. The names are `text/apache_access` and `text/syslog_traditional`; `log2timeline.py --info` lists them.
- **A reused storage file name broke the next `psort`.** The run after a failed first attempt printed psort's usage text instead of output. A fresh storage file name (`ny2.plaso`) worked. I did not diagnose it; I suspect the leftover file, **est.**
- **My first hash check printed FAILED** because it ran in the wrong folder (`lab.pcap: No such file or directory`); run from the folder that holds the file it printed `lab.pcap: OK`.
- **Not run:** Wireshark's graphical interface, TLS decryption, Timesketch, `pinfo.py` on a result, pcapng, a disk image, any Windows host.

## Free exercise: a capture and a timeline you make yourself

I did not use a public sample capture. Wireshark's SampleCaptures wiki page (read 2026-11-07) states no license for its files and mentions that some captures hold keys or redacted personal data, and two searches did not turn up a reuse policy. So the exercise makes its own data, which is also the only way to know exactly what is in it. Total cost: free; about 30 minutes plus image downloads. Use Podman or Docker; I ran Podman, and the Docker form is **est.**

You need a work folder (not `/tmp`; I used `~/.local/share/forensics-lab`) with three things: a `Containerfile` for the capture tools, a small server, and two log files.

```bash
mkdir -p ~/.local/share/forensics-lab/{src,evidence,out,www}
cd ~/.local/share/forensics-lab
printf 'name,amount\nalice,100\nbob,200\n' > www/report.csv
echo hi > www/index.html
cat > Containerfile <<'EOF'
FROM docker.io/library/debian:13
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    tshark tcpdump curl ca-certificates openssl python3 && rm -rf /var/lib/apt/lists/*
EOF
podman build -t forensics-lab .
cat > server.py <<'EOF'
import http.server, time
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *a): pass
    def log_request(self, code="-", size="-"):
        ts = time.strftime("%d/%b/%Y:%H:%M:%S +0000", time.gmtime())
        with open("/out/access.log", "a") as f:
            f.write('%s - - [%s] "%s" %s %s "-" "%s"\n' % (self.client_address[0], ts,
                    self.requestline, code, size, self.headers.get("User-Agent", "-")))
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers()
        self.wfile.write(b"ok")
http.server.ThreadingHTTPServer(("0.0.0.0", 8080), H).serve_forever()
EOF
```

**Step 1. Capture.** Start the server on a private network with raw sockets allowed, start tcpdump and a TLS listener inside it, then make requests from a second container:

```bash
podman network create forensics-net
podman run -d --name fsrv --cap-add NET_RAW --network forensics-net \
  -v "$PWD/out:/out:Z" -v "$PWD/www:/www:Z" -v "$PWD/server.py:/server.py:Z" \
  -w /www forensics-lab python3 /server.py
podman exec fsrv sh -c 'cd /root && openssl req -x509 -newkey rsa:2048 -nodes -keyout k.pem \
  -out c.pem -subj /CN=lab.invalid -days 2 2>/dev/null
  (openssl s_server -accept 8443 -cert c.pem -key k.pem -www >/out/s.log 2>&1 &)
  (tcpdump -i eth0 -U -w /out/lab.pcap tcp port 8080 or tcp port 8443 >/out/td.log 2>&1 &)
  sleep 2'
podman run --rm --network forensics-net forensics-lab sh -c '
  curl -s http://fsrv:8080/index.html -A labbrowser >/dev/null; sleep 1
  curl -s http://fsrv:8080/report.csv -A labbrowser -o /dev/null; sleep 1
  curl -s -d "user=alice&pass=hunter2-lab" http://fsrv:8080/login -A labbrowser; echo; sleep 1
  curl -sk https://fsrv:8443/ -o /dev/null'
sleep 1; podman stop -t 1 fsrv
```

**Step 2. Preserve.** Copy the capture and the log into `evidence/`, hash, make the capture read-only, and write the hash and time in a notes file. All later work uses a copy:

```bash
cp out/lab.pcap out/access.log evidence/
chmod a-w evidence/lab.pcap
( cd evidence && sha256sum lab.pcap | tee lab.pcap.sha256 )
```

My hash was `bb9e99de...05e8` for my capture; yours will differ because packet times and ports differ. The check is that yours matches itself a day later.

**Step 3. Extract one fact.** Run the tshark commands from [the stream section](#following-a-stream-and-extracting-objects) through the container with `evidence/` mounted read-only (`-v "$PWD/evidence:/ev:ro,Z"`). The fact to find: what form fields were sent to `/login`, at what second, and from which address. Then answer: which bytes of the TLS connection can you read?

**Step 4. Timeline.** Write the synthetic `auth.log` below into `src/` (it is made up; the heartbeat gap and the seven-minute offset are mine), copy `access.log` next to it, and build plaso in an Ubuntu 26.04 container with the GIFT PPA:

```bash
cp evidence/access.log src/
cat > src/auth.log <<'EOF'
Nov  7 10:30:01 labhost CRON[501]: (root) CMD (/usr/local/bin/heartbeat)
Nov  7 10:45:01 labhost CRON[533]: (root) CMD (/usr/local/bin/heartbeat)
Nov  7 10:49:41 labhost sshd[811]: Failed password for alice from 10.89.0.6 port 40122 ssh2
Nov  7 10:49:44 labhost sshd[811]: Failed password for alice from 10.89.0.6 port 40122 ssh2
Nov  7 10:49:52 labhost sshd[811]: Accepted password for alice from 10.89.0.6 port 40122 ssh2
Nov  7 10:49:52 labhost sshd[811]: pam_unix(sshd:session): session opened for user alice by (uid=0)
Nov  7 10:57:19 labhost weblogin[640]: session started for user alice
Nov  7 11:30:01 labhost CRON[702]: (root) CMD (/usr/local/bin/heartbeat)
EOF
cat > Containerfile.plaso <<'EOF'
FROM docker.io/library/ubuntu:26.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    software-properties-common ca-certificates && add-apt-repository -y universe \
    && add-apt-repository -y ppa:gift/stable && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends plaso-tools \
    && rm -rf /var/lib/apt/lists/*
EOF
podman build -t forensics-plaso -f Containerfile.plaso .
```

Edit the addresses in `auth.log` to the address your own capture shows for the client (mine was a private address from the container network). Then run the `log2timeline.py` and `psort.py` commands from [the plaso section](#building-a-super-timeline-with-plaso) once without `--timezone` and once with it, using a new storage file name each time:

```bash
podman run --rm -v "$PWD/src:/src:ro,Z" -v "$PWD/out:/out:Z" forensics-plaso sh -c '
  log2timeline.py --quiet --status_view none --parsers "text/apache_access,text/syslog_traditional" \
    --preferred_year 2026 --storage_file /out/utc.plaso /src
  psort.py --output_time_zone UTC -o dynamic --fields datetime,parser,message -w /out/utc.csv /out/utc.plaso'
```

Add `--timezone America/New_York` and new file names for the second run. Compare the two outputs. Predict first: which one puts the SSH login before the web requests?

**Step 5. Four lines.** Write the finding in the [four-line shape](#writing-it-up). Your skew will be whatever offset you computed from the anchor.

**Step 6. Clean up.** `podman rm -f fsrv`, `podman network rm forensics-net`, delete the work folder and the images (`podman rmi forensics-lab forensics-plaso`). The capture holds a fake password and nothing else, but the habit is to delete captures you no longer need.

## Checkpoint

Without looking back: say the three habits for a new capture file; name two things a pcap cannot show; say what is still visible in a TLS session you cannot decrypt; explain why a Linux text log truncated by an intruder leaves no event but a Windows security log clear does; say what the two plaso runs in the exercise changed and why; and write the four lines of a finding.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "I opened the pcap, so I changed it" | Opening does not; saving does | Hash before and after |
| "The pcap time is the real time" | It is the capturing host's clock | Compare to another source with an anchor |
| "No packets, so nothing happened" | Nothing on this link in this window | Where the capture point sat |
| "The server's key will decrypt the old capture" | Not for (EC)DHE sessions | Whether anyone logged the session secrets |
| "The file's modified time is when it happened" | It is when the file changed, and a copy has its own times | The original's metadata, before copying |
| "Plaso reads my pcap" | Not in this version, from `--info` | Use tshark, correlate by time |
| "The timeline shows the login first" | You may have left out the zone | Run once with and once without `--timezone` |
| "The gap means they deleted it" | A gap only says the writing stopped | Other sources during the gap |

## Claims register

Retrieved on 2026-11-07. "Read" means I read the page text. "Run" means I ran it in the lab described above. "Observed" means I saw it in my own output.

| Claim | Source | Status |
|---|---|---|
| Interception offense, penalty up to five years, party and prior-consent exception, provider exception | 18 U.S.C. 2511(1)(a), (4)(a), (2)(d), (2)(a)(i), Cornell LII | Read; not legal advice |
| RFC 3227: title, February 2002, BCP 55; the volatility list; the quoted sentences on minimizing change, UTC versus local time and clock drift | rfc-editor.org/rfc/rfc3227 | Read |
| NIST SP 800-86 is final, August 2006, covers network traffic among its sources, and shows no withdrawal notice on its page | csrc.nist.gov/pubs/sp/800/86/final | Read |
| Wireshark TLS decryption through `SSLKEYLOGFILE` and the key log preference; RSA private key only in limited cases, one being a non-(EC)DHE suite | wiki.wireshark.org/TLS | Read |
| `journald.conf`: `Storage=auto` rule; `Seal=` Forward Secure Sealing wording | freedesktop.org journald.conf man page | Read |
| Event 1102 is the Security audit log cleared event, with the account that did it; 4624 is the successful logon event; Logon ID links events | Microsoft Learn archived page, ms.date 2021-09-07 | Read |
| Event 4625 is failed logon; event 104 is the System log cleared event | My memory | **est.** |
| Apache-style access time is when the server logged, which may differ from request start | My memory | **est.** |
| pcapng stores metadata that classic pcap does not | My memory | **est.** |
| Plaso license is Apache-2.0; releases 20261027, 20260720, 20260512, 20260119 | GitHub API for log2timeline/plaso | Read |
| Plaso 20261027 on PyPI, requires Python 3.10 or newer | pypi.org JSON | Read |
| Ubuntu install through the GIFT PPA and `plaso-tools`; only Ubuntu 26.04 supported; SIFT ships its own builds | plaso.readthedocs.io, Ubuntu packaged release page | Read |
| Wireshark SampleCaptures page states no license in the portion I read; two searches found no reuse policy | wiki.wireshark.org/SampleCaptures (first 100,000 of 180,063 characters) and two WebSearch queries | Read; the last 80,063 characters were not read |
| Capture: 54 packets, 3.08 seconds, classic pcap, Ethernet, microsecond timestamps; the SHA-256 printed by `capinfos` and `sha256sum` agree | `capinfos`, `sha256sum` | Run |
| HTTP listing, three streams on 8080 of 12 frames, one on 8443 of 18, follow-stream body, four extracted objects; the extracted `report.csv` hash equals the server file's | tshark 4.4.19, `sha256sum` | Run |
| TLS: Client Hello with SNI, Server Hello, `0x0303`; no certificate message visible | tshark `tls.handshake` fields | Run; TLS 1.3 itself **est.** |
| `log2timeline.py --info` lists `filestat` and `text/...` plugins and no pcap parser | plaso 20261027 | Run |
| Eight timeline events in the window filter; two timelines differ by five hours with and without `--timezone` | `psort.py` | Run |
| `filestat` times were the copy time, 15:51:32 UTC | `psort.py` output | Observed |
| A cleaner way to stop tcpdump in the container; Docker command forms; why the reused storage file failed; that the exercise's `/root` and `/out` paths for the key and logs behave like the `/tmp` paths I ran | My expectation | **est.** |

Not verified, plainly: Wireshark's graphical interface; TLS decryption with a key log; any Windows host, event log or tool; journal sealing in use; pcapng; Timesketch; any real case or sample capture; anything about laws outside the United States; the timing of the container steps on your hardware. Every address in the lab is a private container-network address and every credential is invented.

Next: the sibling lessons in the digital forensics series are [foundations](Digital-Forensics-Foundations-Evidence-Handling-Chain-of-Custody-and-Order-of-Volatility.md), [disk and Autopsy](Disk-Forensics-with-Autopsy-and-The-Sleuth-Kit.md), [memory](Memory-Forensics-Acquiring-RAM-and-Analyzing-It-with-Volatility-3.md) and [toolkits](DFIR-Toolkits-and-Live-Triage-SIFT-Velociraptor-KAPE-and-the-Incident-Response-Workflow.md). Related pages are [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md), [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md) and [Build your own mini SOC](Build-Your-Own-Mini-SOC.md).
