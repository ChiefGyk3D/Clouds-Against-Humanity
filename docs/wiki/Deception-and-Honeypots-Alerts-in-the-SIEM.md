# Deception alerts in the SIEM: turn a decoy event into a rule

Lesson 5 of the [deception and honeypots track](Deception-and-Honeypots-Start-Here.md). A foundations side page to [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) and [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md). You work on **synthetic** events made on your own computer, write the detection logic as a small program you can run, and then read a draft of the same logic as Wazuh rules. Next: back to the [track hub](Deception-and-Honeypots-Start-Here.md), which says what the later tracks need.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the Python parts were run once on Linux; the Wazuh rules are an unverified draft that was never loaded.** On **2026-10-21** the author ran every Bash command that uses the two Python scripts, with Python 3.13.5, and pasted trimmed output. The XML rules were checked only to be well-formed XML and compared with the Wazuh rules syntax page. They were **never loaded into a Wazuh manager**, and no Wazuh was available to the author, so whether they match, group, count and fire as described is **UNVERIFIED**. The PowerShell commands are **est.** (not run). Real rules are written from captured lines; the lines here are invented, and the lesson says where that limit bites.

> **Prerequisites.** [What deception is](Deception-and-Honeypots-What-Deception-Is.md) (lessons 1 and 2), [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md) (lesson 4, for the habit of treating names as data), and [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md). [JSON](Glossary.md) and [the terminal and your first script](Terminal-and-Your-First-Script.md) help. Python 3.11 or newer (the scripts read a timestamp that ends in `Z`). About 2.5 to 3 hours (est.). Cost: none; a Wazuh test install is optional, and its cost is yours.

## What you will be able to do

- Read a structured honeypot event and name the fields a rule can use.
- Write down detection logic for repeated failures from one source and for a success after them, and run it on invented lines.
- Map the first to the right ATT&CK technique, and say why the second is *not* "valid accounts" on a honeypot.
- Show that a hostile-looking line stays inert data, and show that a naive text search is fooled by it.
- Read a draft Wazuh rule, say what is still unverified about it, and say what you would test first.

## How a decoy event becomes an alert

```text
decoy or honeypot     writes JSON lines     a file on a host      rules               alerts and counts
(or your lesson 3/4   one event per line --> a Wazuh agent or  --> match, count by --> a person, a dashboard
 tripwire, or later                         manager reads         source, map to
 a Cowrie sensor)                                                 ATT&CK
```

This reuses the path in the [honeypot design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md) (section 9): the sensor produces structured JSON, a collector on your side lands it as a file, an agent or manager reads the file, and rules produce alerts and counts. That design pulls from an internet-facing sensor and keeps an agent *off* that sensor. In this track nothing is internet-facing: your lesson 3 and 4 tools already write on your own host.

Wazuh ships a default JSON decoder that turns each field of a JSON log line into a field that a rule can name (see the register). So for JSON events the missing work is **rules**, not a decoder.

### The shape of the events

Cowrie is a honeypot that imitates an SSH server. Its documentation lists the fields every event carries, among them `eventid`, `session`, `src_ip` and `timestamp` (in UTC), and the extra fields of each event type: a login event carries `username` and `password`; a command event carries `input`. The lesson uses three event ids from that list: `cowrie.login.failed`, `cowrie.login.success` and `cowrie.command.input`. The generator below builds lines in that shape. **Nothing in them came from a real attacker.**

| Field | Meaning | Who controls it |
|---|---|---|
| `eventid` | What happened. | The sensor. |
| `session` | One visit. | The sensor. |
| `src_ip` | The visitor's address. | The network (it can be forged only as far as the network allows). |
| `timestamp` | When, in UTC. | The sensor. |
| `username`, `password`, `input` | What the visitor typed. | **The visitor.** Hostile until proven otherwise. |

The last row is the whole security lesson of this page. Fields the visitor controls can hold anything: quotes, control characters, text that looks like another JSON line, text that looks like a rule.

## Exercises

All of them work in a fresh folder. **Bash and PowerShell** commands are given; PowerShell is **est.**

```bash
mkdir -p ~/deception-lab/siem && cd ~/deception-lab/siem
```

```powershell
New-Item -ItemType Directory -Force $HOME\deception-lab\siem | Out-Null
Set-Location $HOME\deception-lab\siem
```

Save `make_events.py` and `detect.py` in that folder.

`make_events.py` builds the invented lines. Source A makes six wrong guesses in 15 seconds, then a login the imitation accepts; source B makes one guess; source C logs in on the first try; source D makes five wrong guesses and then sends hostile text; the last two lines are not valid events. Addresses come from the documentation ranges reserved for examples.

```python
# Builds SYNTHETIC honeypot events in the shape Cowrie documents (eventid, session,
# src_ip, timestamp, plus username/password/input). Nothing here came from a real
# attacker. Addresses are from the documentation ranges (RFC 5737). Run:
#   python3 -I make_events.py > events.jsonl
import json
from datetime import datetime, timedelta, timezone

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
lines = []

def ev(seconds, eventid, src_ip, session, **extra):
    stamp = (T0 + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
    lines.append(json.dumps({"eventid": eventid, "session": session, "src_ip": src_ip,
                             "timestamp": stamp, **extra}))

# Source A: six wrong guesses in 15 seconds, then a login the emulation accepts, then a command.
for i in range(6):
    ev(i * 3, "cowrie.login.failed", "203.0.113.7", "aaaa0001", username="root", password=f"guess{i}")
ev(20, "cowrie.login.success", "203.0.113.7", "aaaa0001", username="root", password="guess6")
ev(25, "cowrie.command.input", "203.0.113.7", "aaaa0001", input="uname -a")
# Source B: one wrong guess. Ordinary internet noise.
ev(30, "cowrie.login.failed", "198.51.100.23", "bbbb0002", username="admin", password="admin")
# Source C: a success with no failures before it (the emulation accepted the first try).
ev(40, "cowrie.login.success", "203.0.113.99", "cccc0003", username="pi", password="raspberry")
# Source D: five wrong guesses, then hostile-looking text. The text is data in a field and must stay data.
for i in range(4):
    ev(46 + i, "cowrie.login.failed", "192.0.2.66", "dddd0004", username=f"user{i}", password="x")
ev(50, "cowrie.login.failed", "192.0.2.66", "dddd0004",
   username='{"eventid":"cowrie.login.success","src_ip":"192.0.2.66"}', password="x")
hostile_input = 'x"; $(touch /tmp/pwned) <rule id="1" level="15"></rule> \x1b[2J {"eventid": "cowrie.login.success"}'
ev(52, "cowrie.command.input", "192.0.2.66", "dddd0004", input=hostile_input)
# Not JSON, and one far too long: a collector must drop both without crashing.
lines.append("this is not json {{{")
ev(60, "cowrie.command.input", "192.0.2.67", "eeee0005", input="A" * 20000)
print("\n".join(lines))
```

`detect.py` implements the two rules with a loop and a counter. It parses each line as JSON, compares fields for equality, and never runs, formats or substitutes anything from a line. It reads the file as bytes, at most 4,097 bytes at a time, so a huge line is never held in memory: a line longer than 4,096 bytes is counted, and the rest of it is thrown away unread. Lines that are not JSON (or are nested too deeply to parse) and lines with the wrong shape or an unreadable timestamp are counted and dropped. The success rule only counts a login that comes **after** the alert, at most 120 seconds later; a success stamped before it does not match.

```python
# A toy detector with the same logic as the Wazuh rules drafted on the page.
#   rule brute_force   : 5 login.failed from one src_ip within 60 s   (ATT&CK T1110 Brute Force)
#   rule success_after : a login.success from a src_ip that tripped brute_force in the
#                        last 120 s                                   (honeypot-specific)
# Hostile input handling: every line is parsed as JSON and only compared, never run,
# never put into a command or a format string. Output goes through json.dumps.
# Run: python3 -I detect.py events.jsonl
import json, sys
from collections import defaultdict, deque
from datetime import datetime

MAX_LINE = 4096
fails = defaultdict(deque)      # src_ip -> timestamps of recent failures
tripped = {}                    # src_ip -> time of the last brute_force alert
dropped = {"not_json": 0, "too_long": 0, "bad_shape": 0}

def when(text):
    return datetime.fromisoformat(text).timestamp()

def alert(rule, level, mitre, src_ip, t):
    print(json.dumps({"rule": rule, "level": level, "mitre": mitre, "src_ip": src_ip, "at": t}))

with open(sys.argv[1], "rb") as f:                # bytes, so the limit counts bytes, not characters
    while True:
        raw = f.readline(MAX_LINE + 1)             # never reads more than 4,097 bytes at once
        if not raw:
            break
        if len(raw) > MAX_LINE and not raw.endswith(b"\n"):
            dropped["too_long"] += 1
            while raw and not raw.endswith(b"\n"):  # throw away the rest of the long line
                raw = f.readline(MAX_LINE + 1)
            continue
        try:
            e = json.loads(raw.decode("utf-8", errors="replace"))
        except (ValueError, RecursionError):       # not JSON, or nested too deeply to parse
            dropped["not_json"] += 1
            continue
        if not isinstance(e, dict) or not all(isinstance(e.get(k), str) for k in ("eventid", "src_ip", "timestamp")):
            dropped["bad_shape"] += 1
            continue
        try:
            t = when(e["timestamp"])
        except (ValueError, OverflowError, OSError):  # a timestamp we cannot read is a bad line, not a crash
            dropped["bad_shape"] += 1
            continue
        ip = e["src_ip"]
        if e["eventid"] == "cowrie.login.failed":
            q = fails[ip]
            q.append(t)
            while q and t - q[0] > 60:
                q.popleft()
            if len(q) >= 5 and t - tripped.get(ip, -1e9) > 60:
                tripped[ip] = t
                alert("brute_force", 10, "T1110 Brute Force", ip, e["timestamp"])
        elif e["eventid"] == "cowrie.login.success" and 0 <= t - tripped.get(ip, -1e9) <= 120:
            alert("success_after_brute_force", 12, "none (honeypot-specific)", ip, e["timestamp"])

print("dropped:", json.dumps(dropped), file=sys.stderr)
```

### Exercise 1: look at the events, then predict the alerts

**Do.**

```bash
python3 -I make_events.py > events.jsonl
wc -l events.jsonl
head -n 2 events.jsonl
```

```powershell
py -3 -I make_events.py | Set-Content -Encoding ascii events.jsonl
(Get-Content events.jsonl).Count
Get-Content events.jsonl -TotalCount 2
```

(PowerShell 5.1 writes UTF-16 with a plain `>`; `Set-Content -Encoding ascii` avoids that. The lines are plain ASCII.)

**Predict.** Before running the detector: the file has 18 lines. Which source addresses will raise an alert, and at which of the two rules? Will source D raise the second rule, given that two of its lines contain the words "cowrie.login.success"? What will be dropped?

**Check.** The first command prints `18 events.jsonl`; the second prints two failed-login lines for `203.0.113.7`, shaped like:

```text
{"eventid": "cowrie.login.failed", "session": "aaaa0001", "src_ip": "203.0.113.7", "timestamp": "2026-01-01T12:00:00.000000Z", "username": "root", "password": "guess0"}
```

**Undo.** Nothing.

### Exercise 2: run the detector

**Do.**

```bash
python3 -I detect.py events.jsonl
echo "exit=$?"
```

```powershell
py -3 -I detect.py events.jsonl
$LASTEXITCODE
```

**Check.** From the 2026-10-21 run:

```text
dropped: {"not_json": 1, "too_long": 1, "bad_shape": 0}
{"rule": "brute_force", "level": 10, "mitre": "T1110 Brute Force", "src_ip": "203.0.113.7", "at": "2026-01-01T12:00:12.000000Z"}
{"rule": "success_after_brute_force", "level": 12, "mitre": "none (honeypot-specific)", "src_ip": "203.0.113.7", "at": "2026-01-01T12:00:20.000000Z"}
{"rule": "brute_force", "level": 10, "mitre": "T1110 Brute Force", "src_ip": "192.0.2.66", "at": "2026-01-01T12:00:50.000000Z"}
exit=0
```

(The `dropped` line goes to the error stream, so it may appear first.) Source A raised both alerts: its fifth failure came 12 seconds after its first, and the accepted login came 8 seconds after that. Sources B and C raised nothing: one failure is noise, and a success with no failures before it is not the chain this rule looks for. Source D raised only the first rule (five failed logins), never the second, and the two unusable lines were counted as dropped. The detector exits `0` either way: it reports, it does not judge.

**Undo.** Nothing.

### Exercise 3: the guard bites (a negative case)

A rule that never fires is as bad as one that always does. Prove it can stay quiet and prove it can fire at the edge.

**Predict.** Each command also removes source D, so only source A can alert. Remove source A's events entirely. Remove only its fifth and sixth failures. Remove only its sixth failure. What does the detector print each time?

**Do.**

```bash
python3 -I make_events.py | grep -v -e '203.0.113.7' -e '192.0.2.66' > quiet.jsonl
python3 -I detect.py quiet.jsonl; echo "exit=$?"
grep -v -e '"guess4"' -e '"guess5"' -e '192.0.2.66' events.jsonl > four.jsonl
python3 -I detect.py four.jsonl; echo "exit=$?"
grep -v -e '"guess5"' -e '192.0.2.66' events.jsonl > five.jsonl
python3 -I detect.py five.jsonl
```

```powershell
py -3 -I make_events.py | Select-String -NotMatch '203.0.113.7|192.0.2.66' | ForEach-Object { $_.Line } | Set-Content -Encoding ascii quiet.jsonl
py -3 -I detect.py quiet.jsonl
Get-Content events.jsonl | Select-String -NotMatch '"guess4"|"guess5"|192.0.2.66' | ForEach-Object { $_.Line } | Set-Content -Encoding ascii four.jsonl
py -3 -I detect.py four.jsonl
Get-Content events.jsonl | Select-String -NotMatch '"guess5"|192.0.2.66' | ForEach-Object { $_.Line } | Set-Content -Encoding ascii five.jsonl
py -3 -I detect.py five.jsonl
```

**Check.** `quiet.jsonl` and `four.jsonl` raise **no alert** (the second has only four failures, one short of the threshold, so the later accepted login is not a chain either). `five.jsonl` has five failures and raises both alerts, exactly as before. The threshold is exact at five, not "about five". Tuning it is the work.

**Undo.** `rm -f quiet.jsonl four.jsonl five.jsonl` (PowerShell: `Remove-Item quiet.jsonl, four.jsonl, five.jsonl`).

### Exercise 4: hostile lines stay data

Source D's last two lines carry hostile text. One has, in `input`, a command-substitution string, a fragment of a Wazuh rule and a terminal escape, plus a *complete JSON object that claims to be a login success*. The other has a username that is itself a JSON object claiming a success.

**Predict.** If you count lines that contain the text `cowrie.login.success` with `grep`, how many will you get, and how many real successes are there? And how many `success_after_brute_force` alerts should the detector print, given that source D had five failures before its hostile lines?

**Do.**

```bash
grep -c 'cowrie.login.success' events.jsonl
python3 -I detect.py events.jsonl 2>/dev/null | grep -c success_after
```

```powershell
(Select-String -SimpleMatch 'cowrie.login.success' events.jsonl | Measure-Object).Count
(py -3 -I detect.py events.jsonl 2>$null | Select-String -SimpleMatch 'success_after' | Measure-Object).Count
```

**Check.** The text search counts **4** lines, but only **2** are real successes (sources A and C). The other two are source D's hostile lines, where the words sit inside a field. The detector prints **1** `success_after_brute_force` alert (source A's). Source D had five failures first, so a rule that looked for the *text* in the line would have fired a second, false alert on D's hostile `input` line. The detector does not, because it parses the line and compares the *`eventid` field*, not the text. Two habits this shows. First, **match on a parsed field, never on a substring of the whole line.** Second, **never build a command, a file name or a query out of a field a visitor controls.** The detector also prints through `json.dumps`, which escapes control characters, so a terminal escape cannot clear your screen.

This is the same rule from the [honeyfile lesson](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md#exercise-2-a-file-name-that-forges-an-alert), and the design's hostile-line test (risk 5, section 4.5) in miniature.

**Undo.** Nothing.

## Mapping to ATT&CK

[ATT&CK](https://attack.mitre.org/) is a public catalog of attacker techniques. Two entries matter here.

| Observed | Technique | Why |
|---|---|---|
| Many failed logins from one source in a short time | **T1110 Brute Force** (the catalog lists sub-techniques for guessing, cracking, spraying and stuffing; which one fits depends on the pattern: many passwords for one account versus one password for many accounts) | The technique page describes repeatedly guessing passwords against a service that checks them. The detector counts failures per source and does not look at which accounts were tried, so it can say T1110 Brute Force and no more. |
| A login the imitation accepts, after those failures | **Not T1078 Valid Accounts.** Tag it as a honeypot-specific detection | The T1078 Valid Accounts page describes adversaries obtaining and abusing credentials of **existing accounts**. On a honeypot the account is not real: the imitation accepts whatever it was set up to accept. T1078 Valid Accounts would apply to a **real, valid account** on a real system, for example a real SSH server whose stolen password was used. |

The honest limit: this author did not read which credentials Cowrie accepts by default, so the lesson says only that an accepted login on an *imitation* is not a valid account. It is still useful, because it shows that guessing worked against whatever the sensor accepts. Real rules are written from captured lines, not from assumed ones.

## The same logic as a Wazuh rule: an unverified draft

This is the detector's logic written in Wazuh's rule language. It was read against the rules syntax page and checked to be well-formed XML. **Never loaded into a manager.**

```xml
<!-- DRAFT, UNVERIFIED: written from the Wazuh rules syntax page, never loaded into a manager.
     Test every line with wazuh-logtest before trusting it. -->
<group name="local,honeypot,">

  <!-- Silent parent: any JSON event whose eventid starts with "cowrie." -->
  <rule id="100900" level="0">
    <decoded_as>json</decoded_as>
    <field name="eventid">^cowrie\.</field>
    <description>Honeypot event (Cowrie-shaped JSON).</description>
  </rule>

  <rule id="100901" level="0">
    <if_sid>100900</if_sid>
    <field name="eventid">^cowrie\.login\.failed$</field>
    <description>Honeypot: failed login.</description>
  </rule>

  <rule id="100902" level="10" frequency="5" timeframe="60" ignore="60">
    <if_matched_sid>100901</if_matched_sid>
    <same_field>src_ip</same_field>
    <description>Honeypot: 5 failed logins from one source within 60 seconds.</description>
  </rule>

  <rule id="100903" level="12" timeframe="120">
    <if_sid>100900</if_sid>
    <field name="eventid">^cowrie\.login\.success$</field>
    <if_matched_sid>100902</if_matched_sid>
    <same_field>src_ip</same_field>
    <description>Honeypot: emulated login accepted after a brute-force alert from the same source.</description>
  </rule>

</group>
```

How to read it: rule `100900` is a **silent parent** (level 0) that matches any JSON event whose `eventid` begins `cowrie.`; `100901` narrows to failed logins, still silent; `100902` fires when the failed-login rule has matched five times within 60 seconds for the same source, then ignores that source for 60 seconds; `100903` is the success after that alert. This is the same shape as the silent-parent pattern the detection page asks you to find in the author's Twingate rules. Rule IDs are in a range the Wazuh documentation reserves for local rules (check yours do not collide with existing ones; **est.**).

**What is UNVERIFIED, in the order you would test it with the `wazuh-logtest` tool on a test manager:**

1. Whether the JSON decoder exposes `eventid` and `src_ip` under exactly those names, and how nested fields appear.
2. The `same_field` element: the syntax page lists it among the "same" options, and the text the author read does not show the argument form used here.
3. Whether a rule can combine `if_sid` (about the current event) with `if_matched_sid` and `timeframe` without `frequency`, as `100903` does. If not, the success-after-alert logic needs another shape.
4. How `frequency` and `ignore` interact, so that exactly one alert fires and not five.
5. Adding a `mitre` element with the technique id (the Wazuh syntax page shows one inside a rule). The draft leaves it out because this wiki's tests require every technique id to be followed by its name, which an XML id element cannot be; the mapping lives in the table above. Check that the dashboard shows it once added.
6. Whether a hostile string in `username` or `input` stays inert in the rule engine and on the dashboard. The simulator proves the *program*; only a manager proves the *rules*.

The education plan's list of rules also includes "a decoy touched" rule for the honeyfile alerts of lesson 4. That is left as a design question here: the lesson 4 watcher writes plain text lines, not JSON, so you would either change the watcher to write JSON (using a real JSON library to quote the name) or write a decoder for the plain format. Pick one and say why.

## Build, break, detect, evade, defend

- **Build.** The generator, the detector, and a draft rule file.
- **Break.** Feed the detector a line it was not built for: a failure with a timestamp in the future, a timestamp with no time zone (Python reads it as your local time, not UTC), a missing field, `"src_ip": 5`. Which are dropped, which make a wrong alert, which would crash it? Fix one. (A timestamp that cannot be read at all used to crash the first version; the `try` in the script above is that fix.)
- **Detect.** Add a third rule: `cowrie.command.input` after a success, with a list of commands you consider interesting (`uname`, `wget`, `curl`). Predict what it alerts on in this file (source A's `uname -a`), then run it. Map it to the technique the command shows; on this page the author mapped nothing for commands.
- **Evade.** A careful visitor guesses slowly (one guess a minute), from many addresses, or one password across many accounts. Change the generator to do each, and see which your 5-in-60-seconds rule misses. That is not a bug in the rule: it is what the threshold *means*.
- **Defend.** Add a second rule that counts distinct usernames from one source (spraying), and an alert when the sensor goes quiet. A detector that fails silent is the one nobody finds.
- **Flip the board.** You operate the sensor. A hostile string from an attacker lands in your dashboard. List every place it goes after the detector (the file, the SIEM, a chat alert, an email) and what each one does with it.

## Common mistakes

| Mistake | Why it hurts | Better |
|---|---|---|
| Matching on text in the whole line. | A visitor can put your match text in a field. | Parse the line; compare a field. |
| Building a command or query from a field. | Command or query injection. | Never. Use the field as a value only. |
| Treating real and invented data alike. | Rules tuned on invented lines fail on real ones. | Write from captured lines when you have them. |
| Tagging an accepted honeypot login as T1078 Valid Accounts. | The account is not real. | Call it a honeypot detection. |
| A detector with no "quiet" test. | You do not know it can stay quiet. | A negative case, as in exercise 3. |

## Claims register

Retrieved 2026-10-21 unless stated.

| Claim | Source | Status |
|---|---|---|
| Cowrie events carry `eventid`, `session`, `src_ip` and `timestamp` (ISO 8601, UTC); login events carry `username` and `password`; command events carry `input`; the event ids `cowrie.login.failed`, `cowrie.login.success`, `cowrie.command.input` exist | [Cowrie output documentation](https://docs.cowrie.org/en/latest/_sources/OUTPUT.rst.txt) | Read |
| Cowrie's documentation lists Splunk, Sentinel and Graylog guides and no Wazuh guide | [Cowrie documentation index source](https://docs.cowrie.org/en/latest/_sources/index.rst.txt) | Read |
| Wazuh has a JSON decoder that turns the fields of a JSON event into fields; `wazuh-logtest` tests a log against decoders and rules | [Wazuh JSON decoder](https://documentation.wazuh.com/current/user-manual/ruleset/decoders/json-decoder.html) | Read; not run |
| Rule elements and attributes used (`decoded_as`, `field`, `if_sid`, `if_matched_sid`, `frequency`, `timeframe`, `ignore`, `same_field`, `group`; `mitre` was read but is not in the draft) | [Wazuh rules syntax](https://documentation.wazuh.com/current/user-manual/ruleset/ruleset-xml-syntax/rules.html) | Names read; the combination in `100903` and the `same_field` argument are UNVERIFIED |
| T1110 Brute Force describes systematically guessing passwords against a service or offline; its sub-techniques include password guessing, cracking, spraying and credential stuffing | [ATT&CK T1110 Brute Force](https://attack.mitre.org/techniques/T1110/) | Read |
| T1078 Valid Accounts describes obtaining and abusing credentials of existing accounts | [ATT&CK T1078 Valid Accounts](https://attack.mitre.org/techniques/T1078/) | Read |
| The generator, detector, outputs and the exercise 3 and 4 results | Run on Linux with Python 3.13.5 on 2026-10-21 | Run. The XML was only checked to be well-formed. PowerShell: **est.** |
| Custom rule ID ranges | Wazuh documentation | **est.**; not re-read for this page |

Not verified, plainly: the whole PowerShell track; macOS; the rules in a real manager; whether real Cowrie output matches the shape here beyond what its documentation says; any Track 2 or 3 behavior.

Next: back to the [track hub](Deception-and-Honeypots-Start-Here.md), which says what [tracks 2 and 3](Deception-and-Honeypots-Start-Here.md#tracks-2-and-3-what-they-will-need) will need.
