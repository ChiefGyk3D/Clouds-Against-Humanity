# Wazuh SIEM and data pipelines: from a log line to an alert

A foundations side page in the detection group, for issue #321. Read it after [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) and [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md), and before you build anything in [Build your own mini SOC](Build-Your-Own-Mini-SOC.md). It starts on the **cloud side** (what a connector writes and how it would reach a manager) and only at the end looks at the logging server at home. Next: [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from reading, except the two Python scripts, which were run once.** On **2026-10-30** the author read the Wazuh documentation pages listed in the claims register at the end and ran the two Python scripts below on Linux with Python 3.13.5; the output shown for them is pasted from that run. **No Wazuh manager, agent, indexer or dashboard was available or run.** The decoder and rules are a draft written from the documentation: they were checked to be well-formed XML and never loaded into a manager, so whether they decode, match and fire as described is **UNVERIFIED** until you test them with `wazuh-logtest`. The cloud pieces described (the opt-in agent and auditd on the connectors) are built and merged in this repository and **not applied**. Where this page says "est.", the author did not run it.

> **Prerequisites.** [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) (what a log line, a decoder-like pattern and a rule are), [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) and [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md). [The terminal and your first script](Terminal-and-Your-First-Script.md) helps. Python 3.11 or newer. About 2 hours (est.).

## Cost first: a free path and a paid path

| Path | What you do | Cost |
|---|---|---|
| **Read** | The sections up to "Where a pipeline breaks". No install. | $0 |
| **Run the toy** | Two small Python scripts on your own computer, on invented log lines. They imitate the shape of the pipeline; they are not Wazuh. | $0 |
| **A real Wazuh** (optional) | Wazuh describes an all-in-one deployment, with the server, indexer and dashboard on one machine, as the shape for labs and small environments. Put it on a machine you already own and run the draft rules through `wazuh-logtest`. | Your hardware or your cloud bill. Nothing in this repository starts one, and this page does not need it. |

The cloud mini SOC in [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) is a separate decision with its own cost table. Nothing here changes the cost gate.

## What you will be able to do

- Say what the agent, the manager (Wazuh calls it the server), the indexer and the dashboard each do, and which one a missing alert points at.
- Follow one log line from a file on a connector to a row on a dashboard, naming the stage at each step.
- Read a simple Wazuh decoder and rule, and say what is still unverified about them.
- Run a small pipeline on invented lines and see three failures that raise no error: a line that no decoder understands, a threshold that is one event short, and a clock that is wrong.
- Name where cloud connector logs would enter, and what stands between them and the manager today.

## The four pieces

| Piece | What it does | Default port (from Wazuh's pages) | In this project |
|---|---|---|---|
| **Agent** | Runs on the monitored machine. Its log collector reads files (and, per the configuration reference, the journal) and sends events to the server over an encrypted, authenticated channel. It must be enrolled before its first connection. | Connects out to TCP 1514; enrolls on TCP 1515 | Opt-in on the connectors, built, off by default, not applied |
| **Server (manager)** | Receives events, runs the analysis engine (decoders, then rules), writes alerts, manages the agents. | Listens on 1514 (agents), 1515 (enrollment), 55000 (API) | At home, in the maintainer's own stack |
| **Indexer** | Stores the alerts as JSON documents and makes them searchable. | 9200 | At home |
| **Dashboard** | The web interface: it queries the indexer for data and the server API for status and configuration. It also has a ruleset test tool. | 443 | At home |

Between the server and the indexer sits **Filebeat**, which reads the server's output and ships it to the indexer over TLS. Wazuh also describes deployments where each piece is on its own machine and ones where the server and indexer are clusters; the lesson uses the one-of-each picture.

Notice the direction of the arrows: the agent dials **out** to the server. That is the property the zero-inbound design needs, and it is also why a dead network path looks, from the dashboard, like a quiet machine.

## How one log line becomes an alert

```text
a connector                          the server                                 the indexer         the dashboard
-----------                          ----------                                 -----------         -------------
1 log line written   2 agent reads   3 pre-decode   4 decode    5 rules    6 alert written   7 Filebeat   8 stored as   9 you query it
  to a file or the ->  and sends  ->   header:    -> fields:  -> match,  -> to alerts.json -> ships it -> a JSON     -> and read it
  journal              (1514)          time, host,    srcip,      level,     (and every log             document
                                       program        user        alert      to archives)
```

In words, with a mail room. The agent is the clerk at the monitored machine: it picks up each line as it is written and carries it, in a locked bag, to the server's front desk. Before its first trip it has to register once (port 1515) and is given a key of its own. At the server, a sorter opens each line, reads the header (time, host name, program) and files the rest into labeled slots such as the sender's address and the user name: that is **decoding**. A second desk then holds the rule book and asks of each sorted item whether it matters and how much, from 0 to 16: that is **rule matching**, and a match is an alert. Alerts are written to a file on the server, a courier (Filebeat) carries them to the filing cabinet (the indexer), and you read them through the dashboard.

Three details that change how you debug:

- **Two files, not one.** Per Wazuh's log collection page, alerts go to `/var/ossec/logs/alerts/alerts.json` (and `alerts.log`), while **every** collected log, including lines that matched nothing, is written to `/var/ossec/logs/archives/archives.json` (and `archives.log`). So "no alert" and "never arrived" are different questions with different files.
- **Nothing is deleted for you.** The same page says the server retains logs and does not delete them automatically; you choose when to delete them, to fit your own legal and regulatory needs. A forgotten retention decision is a full disk, not a quiet failure.
- **Decoding comes first.** A rule can only compare what a decoder extracted (or the raw text). A line no decoder understands has no fields, so a rule that needs `srcip` cannot fire. Nothing complains.

## Cloud side first: where the connectors' logs enter

The stage 2 design adds an opt-in Wazuh agent and a short auditd rule set to each Twingate connector droplet, through the shared bootstrap module (`modules/twingate-bootstrap`). Everything is off by default (`log_shipping = {}` is a no-op) and **nothing is applied**. The sources it tells the agent to read, from `/etc/cah/wazuh-localfile.xml` in the cloud-init template, are:

| Source | How the agent reads it | What it would show |
|---|---|---|
| The Twingate connector service | journald, filtered on the unit name | Connector start, stop and error lines |
| The SSH service | journald, filtered on the unit name | Logins and failures |
| `sudo` | journald, filtered on the program identifier | Who used elevated rights |
| `/var/log/auth.log` | a file, as syslog | The same login lines, for hosts that write them to a file |
| `/var/log/audit/audit.log` | a file, in the `audit` format | auditd's file-watch records for identity and sudo files |

The configuration reference confirms that `location` can be `journald` when `log_format` is also `journald`. Whether **your agent version** accepts the journald filter fields the template uses is **UNVERIFIED**: the stage 2 guide says so and keeps a documented syslog fallback that is not built.

What stands between those lines and a manager:

1. **Enrollment.** The agent enrolls on 1515 with a password the first-boot script pulls from the secret store and deletes afterward, and gets a key of its own. A host that fails to enroll stays off, by design. See [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md#the-first-boot-secret-pull-and-where-secrets-still-live).
2. **The network path.** The agent must reach 1514 and 1515 on the manager. The design does that through a Twingate headless client on each droplet. **That client is not built** (stage 2 guide, "not included"), so an enabled agent can only connect if `manager_address` is already reachable. Until the path exists, the connector logs go nowhere and the home side sees silence.
3. **Metrics are a different pipeline.** Logs are pushed by the agent. Metrics are pulled: Prometheus scrapes the node exporter. Two pipelines, two ways to go quiet. The [synthetic lab](Lab-Demo-Monitoring-Stack.md) teaches the second one for free.

| Question | Logs (Wazuh) | Metrics (Prometheus) |
|---|---|---|
| Who starts the connection | The agent, outward | The scraper, inward (over a one-port resource) |
| What a break looks like | The agent's events stop, and no alert says so unless you write one; the dashboard shows agent status, but how it marks a silent agent was not in the pages read | The `up` series for the target goes to 0, or the series disappears |
| What the volume follows | Activity | The number of series |

## A decoder and a rule, simply

Wazuh keeps your own decoders and rules apart from its own: put them in `/var/ossec/etc/decoders/` (the default file is `local_decoder.xml`) and `/var/ossec/etc/rules/` (the default is `local_rules.xml`), because files under `/var/ossec/ruleset/` are overwritten on upgrade. Use rule IDs from 100000 to 120000 for your own rules. The shapes below follow the documentation's own custom example, applied to an invented application called `cahdemo`.

The log line (invented):

```text
Oct 30 12:00:00 connector-a cahdemo[311]: login failed for user 'admin' from 203.0.113.7
```

A **decoder** is two blocks. The parent claims the line by its program name, the child extracts fields. `order` names what each parenthesized group in `regex` holds; `action`, `user` and `srcip` are among the static field names the documentation lists.

```xml
<!-- DRAFT, UNVERIFIED: written from the Wazuh decoder syntax and custom decoder pages,
     never loaded into a manager. Test with wazuh-logtest first. -->
<decoder name="cahdemo">
  <program_name>^cahdemo</program_name>
</decoder>

<decoder name="cahdemo">
  <parent>cahdemo</parent>
  <regex>^login (\w+) for user '(\S+)' from (\d+.\d+.\d+.\d+)</regex>
  <order>action, user, srcip</order>
</decoder>
```

Two **rules**. The first records each failed login quietly at level 3. The second is the only one you would want a person to see: five of the first, from one source address, within 60 seconds, at level 10, then silent for 60 seconds so one burst is one alert.

```xml
<!-- DRAFT, UNVERIFIED: same status. Rule IDs sit in the documented custom range. -->
<group name="local,cahdemo,">

  <rule id="100110" level="3">
    <decoded_as>cahdemo</decoded_as>
    <match>login failed</match>
    <description>cahdemo: login failed</description>
  </rule>

  <rule id="100111" level="10" frequency="5" timeframe="60" ignore="60">
    <if_matched_sid>100110</if_matched_sid>
    <same_srcip />
    <description>cahdemo: 5 failed logins from one source within 60 seconds</description>
  </rule>

</group>
```

Why it is shaped this way, each point from the rules syntax page: `frequency` is how many times the rule must match before it alerts, `timeframe` is the window in seconds, `ignore` is how long to ignore the rule after it fires, and `if_matched_sid` together with `same_srcip` means "that earlier rule fired again and again for the same decoded source address". The page also notes that a level 0 rule is discarded immediately and cannot be used with `if_matched_sid`, which is why the first rule is level 3 and not a silent parent. The [deception alerts lesson](Deception-and-Honeypots-Alerts-in-the-SIEM.md) writes a similar pair over JSON events and lists what it could not check; the same unknowns apply here.

To see the three phases (pre-decoding, decoding, rules) for real, you would paste the line into `/var/ossec/bin/wazuh-logtest` on a manager, or into the dashboard's ruleset test tool. The tool takes one-line logs. Saving the files is enough to test with it; the manager must be restarted before the rules generate real alerts. **That is the first thing to do, and it was not done here.**

The limit of the draft, plainly: the decoder takes the user name as `\S+`, so a name with a space or an odd character may decode wrongly or not at all, and a user-controlled field must never be pasted into a command or a query. Wazuh's regular expression dialect is its own; the Python in the next section uses Python's, so a pattern that works there is not proof it works in Wazuh.

## Exercises: the pipeline on your own computer

Everything runs in a fresh folder on invented lines, with addresses from the documentation ranges. Bash only; on Windows use WSL (not run).

```bash
mkdir -p ~/pipeline-lab && cd ~/pipeline-lab
```

Save the first script as `make_log.py`. It writes a 14-line connector log: source `203.0.113.7` guesses six times against two connectors in 15 seconds and then logs in; one source guesses once; one guesses four times; one line has an unknown format; one is from a different program.

```python
# Builds an INVENTED connector log in syslog style. Nothing here came from a real host.
# Addresses are from the documentation ranges (RFC 5737). Run:
#   python3 -I make_log.py > connector.log            (clocks agree)
#   python3 -I make_log.py --skew 3600 > skewed.log   (connector-b's clock is an hour behind)
import sys
from datetime import datetime, timedelta

skew = int(sys.argv[sys.argv.index("--skew") + 1]) if "--skew" in sys.argv else 0
T0 = datetime(2026, 10, 30, 12, 0, 0)
rows = []  # (seconds after T0, host, text)


def app(sec, host, text, behind=0):
    stamp = (T0 + timedelta(seconds=sec - behind)).strftime("%b %d %H:%M:%S")
    rows.append((sec, f"{stamp} {host} cahdemo[311]: {text}"))


def fail(sec, host, ip, user="admin", behind=0):
    app(sec, host, f"login failed for user '{user}' from {ip}", behind)


# Source A: six wrong guesses against two connectors in 15 seconds, then a success.
for i, sec in enumerate((0, 3, 6, 9, 12, 15)):
    host = "connector-a" if i % 2 == 0 else "connector-b"
    fail(sec, host, "203.0.113.7", behind=skew if host == "connector-b" else 0)
app(20, "connector-a", "login ok for user 'admin' from 203.0.113.7")
# Source B: one wrong guess. Ordinary noise.
fail(30, "connector-a", "198.51.100.23", "pi")
# Source C: four wrong guesses, one short of the rule's threshold.
for sec in (40, 42, 44, 46):
    fail(sec, "connector-a", "192.0.2.66", "root")
# Format drift: the application's new version words the line differently.
app(50, "connector-a", "LOGIN-FAIL admin 203.0.113.99")
# A line from a program with no decoder at all.
rows.append((55, "Oct 30 12:00:55 connector-a sshd[912]: Accepted publickey for ops from 198.51.100.50 port 50222 ssh2"))
print("\n".join(text for _, text in sorted(rows, key=lambda r: r[0])))
```

Save the second as `pipeline.py`. It pre-decodes the header, decodes the body with a regex, applies the two rules and prints alerts as JSON. It counts what it could not read in a `stats` line on the error stream. It keeps no state between runs and runs nothing it reads.

```python
# A toy of the Wazuh server's analysis step: pre-decode, decode, rule match, alert.
# It is NOT Wazuh. It uses Python's regex engine and the log's own timestamp, so it only
# shows the SHAPE of the pipeline. Rules mirror the draft XML on the page:
#   100110 level 3  : a decoded "login failed" line
#   100111 level 10 : 5 of rule 100110 from one srcip within 60 s, then silent for 60 s
# Run: python3 -I pipeline.py connector.log [--min-level N]
import json, re, sys
from collections import defaultdict
from datetime import datetime

HEADER = re.compile(r"^(\w{3} +\d{1,2} \d\d:\d\d:\d\d) (\S+) ([\w.-]+)\[\d+\]: (.*)$")
BODY = re.compile(r"^login (failed|ok) for user '([^']{1,32})' from (\d{1,3}(?:\.\d{1,3}){3})$")
min_level = int(sys.argv[sys.argv.index("--min-level") + 1]) if "--min-level" in sys.argv else 5
stats = {"lines": 0, "no_header": 0, "no_decoder": 0, "undecoded": 0, "decoded": 0, "alerts": 0}
seen = defaultdict(list)   # srcip -> stamps of rule 100110 hits
quiet_until = {}           # srcip -> stamp until which rule 100111 stays silent


def alert(rule, level, text, fields, when):
    if level >= min_level:
        stats["alerts"] += 1
        print(json.dumps({"rule": rule, "level": level, "description": text, "srcip": fields["srcip"], "at": when}))


with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
    for raw in f:
        stats["lines"] += 1
        line = raw.rstrip("\n")[:4096]
        head = HEADER.match(line)
        if not head:
            stats["no_header"] += 1
            continue
        stamp, host, program, message = head.groups()
        if program != "cahdemo":
            stats["no_decoder"] += 1
            continue
        body = BODY.match(message)
        if not body:
            stats["undecoded"] += 1
            continue
        stats["decoded"] += 1
        action, user, ip = body.groups()
        fields = {"action": action, "user": user, "srcip": ip}
        t = datetime.strptime("2026 " + stamp, "%Y %b %d %H:%M:%S").timestamp()
        if action != "failed":
            continue
        alert(100110, 3, "cahdemo: login failed", fields, stamp)
        seen[ip].append(t)
        recent = [s for s in seen[ip] if 0 <= t - s <= 60]   # counts only stamps inside the window
        if len(recent) >= 5 and t >= quiet_until.get(ip, 0):
            quiet_until[ip] = t + 60
            alert(100111, 10, "cahdemo: 5 failed logins from one source within 60 seconds", fields, stamp)

print("stats:", json.dumps(stats), file=sys.stderr)
```

### Exercise 1: predict, then run

**Predict.** How many of the 14 lines will be decoded? Which source raises the level 10 alert, and on which line? Which sources raise nothing, and why? What will `undecoded` and `no_decoder` be?

**Do.**

```bash
python3 -I make_log.py > connector.log
python3 -I pipeline.py connector.log; echo "exit=$?"
```

**Check.** From the 2026-10-30 run:

```text
stats: {"lines": 14, "no_header": 0, "no_decoder": 1, "undecoded": 1, "decoded": 12, "alerts": 1}
{"rule": 100111, "level": 10, "description": "cahdemo: 5 failed logins from one source within 60 seconds", "srcip": "203.0.113.7", "at": "Oct 30 12:00:12"}
exit=0
```

(The `stats` line goes to the error stream, so it may appear first or last.) Source `203.0.113.7` reached five failures at 12:00:12, counting across **both** connectors. The success line at 12:00:20 is decoded but is not a failure, so it counts toward nothing. The `LOGIN-FAIL` line is `undecoded` (the program matched, the body did not) and the `sshd` line is `no_decoder` (nothing in this lab claims that program). Neither raised an error. The exit code is 0 either way: the program reports, it does not judge.

**Undo.** Nothing.

### Exercise 2: the guard bites (a negative case)

**Predict.** Source `192.0.2.66` has four failures. What happens at four, and what happens when you add a fifth within the window?

**Do.**

```bash
grep 192.0.2.66 connector.log > four.log
python3 -I pipeline.py four.log
{ cat four.log; tail -n 1 four.log | sed 's/:46 /:48 /'; } > five.log
python3 -I pipeline.py five.log
```

**Check.** Four lines: no alert, `"decoded": 4, "alerts": 0`. Five lines: one level 10 alert for `192.0.2.66` at `Oct 30 12:00:48`. The threshold is exact: five, not "about five". A rule that cannot stay quiet at four is as useless as one that never fires.

**Undo.** `rm -f four.log five.log`

### Exercise 3: parsing breaks without an error

**Predict.** An application upgrade changes its wording from `login failed for` to `LOGIN-FAIL for`. What does the alert count do? What does any other counter do?

**Do.**

```bash
sed 's/login failed for/LOGIN-FAIL for/' connector.log > drift.log
python3 -I pipeline.py drift.log; echo "exit=$?"
```

**Check.**

```text
stats: {"lines": 14, "no_header": 0, "no_decoder": 1, "undecoded": 12, "decoded": 1, "alerts": 0}
exit=0
```

Zero alerts, exit code 0, and the attack is invisible. The only sign is `undecoded` jumping from 1 to 12. That is the lesson: **a pipeline that parses nothing looks the same as a pipeline with nothing to report.** Count what you could not parse, and alert on that ratio. In a real Wazuh the equivalent is lines that reach `archives.json` with no decoder match; how to alert on that is for you to work out and test (est.).

**Undo.** `rm -f drift.log`

### Exercise 4: a wrong clock

**Predict.** Make the same attack, but `connector-b`'s clock is an hour behind. Every line still parses. What does the pipeline say?

**Do.**

```bash
python3 -I make_log.py --skew 3600 > skewed.log
grep connector-b skewed.log | head -n 1
python3 -I pipeline.py skewed.log; echo "exit=$?"
```

**Check.** The `connector-b` lines carry `Oct 30 11:00:03` instead of `12:00:03`. Output: `"decoded": 12`, `"alerts": 0`, `exit=0`. Nothing was dropped and nothing was malformed; the toy counts by the log's own timestamp, so the two connectors' failures no longer fall in one window, and each connector alone has only three. **Honest limit:** this shows the toy's behavior. Whether a real Wazuh rule counts by the event's own timestamp or by when the server received it was not in the pages read, and is **UNVERIFIED**. Either way, a wrong clock hurts you in the dashboard and in any investigation that lines events up in time. The [glossary entry for NTP](Glossary.md) says why.

**Undo.** `rm -f skewed.log`; to clean up everything, `cd ~ && rm -rf ~/pipeline-lab`.

## Where a pipeline breaks, and how you tell

| Break | What you see | How to tell | Where this page shows it |
|---|---|---|---|
| **A stage stops** (agent down, path cut, server stopped) | Silence; looks like health | A heartbeat you alert on: an agent-status check you have tested, and the metric `up` for scraped targets. Build the "gone quiet" alert before the "attack" alert | The cloud side section; [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) |
| **Dropped or delayed lines** | Fewer events than the host wrote | Compare a count at the source with a count at the destination. Wazuh says the agent channel has flow control and queues events when necessary, so a long outage delays rather than silently drops, up to limits this page did not read | Compare line counts of `connector.log` and what the toy decoded |
| **A line no decoder understands** | Zero alerts, no error | A counter of undecoded lines, as in exercise 3; the dashboard's ruleset test tool to reproduce one line | Exercise 3 |
| **A wrong field mapping** | An alert that fires with the wrong source, or a rule that never matches because `srcip` held something else | Run the real line through `wazuh-logtest` and read phase 2 field by field | The decoder section |
| **A threshold that is one short** | A real attack stays under the rule | Replay recorded lines at the edge, as in exercise 2 | Exercise 2 |
| **Clock skew** | Events in the wrong hour or out of order; windows that miss | Compare the host's time to a reference; keep NTP healthy on every machine | Exercise 4 |
| **Label cardinality** (metrics) | A scrape that grows without bound | Count series per metric. Every distinct label value is a new series, so a label holding a user name, an address or a request id multiplies memory and disk | [Build your own mini SOC: what to measure](Build-Your-Own-Mini-SOC.md#what-to-measure-in-one-list) |
| **Retention** | A full disk, or evidence gone when you need it | Decide the keep time per data type on purpose. Wazuh keeps its logs until you delete them; Prometheus and the cloud mini SOC have their own settings | [Cross-tenant data governance, retention and DLP](Cross-Tenant-Data-Governance-Retention-and-DLP.md) |

## Later: the logging server at home, over ssh

Once stage 2 is applied and a path exists, the on-premises side is where you confirm the pipeline end to end. These commands are **est.** (not run; there was no manager). They assume a manager you administer, reached by ssh through your own access path, never by exposing a port.

```bash
# on the manager (est.)
sudo /var/ossec/bin/wazuh-logtest                       # paste one line, read phases 1 to 3
sudo tail -n 5 /var/ossec/logs/alerts/alerts.json        # recent alerts, from the log collection page's path
sudo tail -n 5 /var/ossec/logs/archives/archives.json    # every log; archiving may need to be switched on first
```

Whether `archives.json` is written by default was not in the pages read, so check the manager's configuration before relying on it (UNVERIFIED). The stage 2 guide has the full home-side check list; the [home-side runbook](Stage-2-Home-Side-Runbook.md) says what must exist first, including a recorded negative test.

## Build, break, detect, evade, defend

- **Build.** The generator, the pipeline, and a decoder and rule pair that you test with `wazuh-logtest` if you stand up a lab manager.
- **Break.** Feed `pipeline.py` a line it was not built for: no header, a 20,000-byte line, bytes that are not valid text. Which are counted, which would crash an unguarded version?
- **Detect.** Add the third counter the exercise needs: an alert when `undecoded` is more than a fraction of `lines`. Choose the fraction, then change a line format and see it fire.
- **Evade.** A careful guesser sends one try a minute, or spreads tries over many addresses. Edit `make_log.py` and see which your rule misses. That is what the threshold means, not a bug.
- **Defend.** Write down, for each stage in the diagram, the one signal that tells you it has stopped. A stage with no such signal is a blind spot.
- **Flip the board.** You operate the manager. An attacker controls the text of a field (a user name). List every place it goes after the decoder: the alert file, the index, the dashboard, a notification. What does each do with it?

## Common mistakes

| Mistake | Why it hurts | Better |
|---|---|---|
| Treating "no alerts" as "all clear" | A broken stage and a quiet network look identical | Alert on silence and on undecoded lines |
| Writing a rule from a line you imagined | The real line has another shape | Capture real lines, then test with `wazuh-logtest` |
| Editing files under `/var/ossec/ruleset/` | The next upgrade overwrites them | Use `/var/ossec/etc/decoders/` and `/var/ossec/etc/rules/`, and an ID in 100000 to 120000 |
| Counting by text anywhere in a line | A visitor can put your match text in a field | Match on decoded fields, as the [deception lesson](Deception-and-Honeypots-Alerts-in-the-SIEM.md) shows |
| Ignoring clocks | Windows miss, evidence is out of order | Fix NTP before tuning rules |
| Never choosing a retention | Disks fill, or logs vanish too early | Pick a keep time per data type |

## Try it yourself

- **No cost.** For each of the nine stages in the diagram, write the one thing you would look at to know it had stopped, and where it lives (a file, a metric, the dashboard).
- Change the generator so source `192.0.2.66` tries one password a minute. Predict what `pipeline.py` does, then run it.
- If you have a lab manager, load the draft decoder and rules, paste the example line into `wazuh-logtest`, and write down which of the claims on this page the tool confirmed and which it corrected.

## Claims register

Retrieved **2026-10-30** unless stated. "Read" means the page text was read; nothing in this register was run against a Wazuh install.

| Claim | Source | Status |
|---|---|---|
| The platform is an agent plus three central components: server, indexer, dashboard; the server analyzes data through decoders and rules; the indexer stores alerts; the dashboard is the web interface | [Components](https://documentation.wazuh.com/current/getting-started/components/index.html) | Read |
| Agent to server over TCP 1514 by default, AES by default; server to indexer through Filebeat with TLS, indexer on 9200; dashboard queries the server API on 55000; the port table (1514, 1515, 1516, 514, 55000, 9200, 443); all-in-one is the shape for labs and small environments | [Architecture](https://documentation.wazuh.com/current/getting-started/architecture.html) | Read |
| The agent reads logs through a log collector; it must be enrolled and gets a unique key; the channel is encrypted and authenticated and has flow control that queues events | [Wazuh agent](https://documentation.wazuh.com/current/getting-started/components/wazuh-agent.html) | Read |
| The server has an enrollment service (TLS or a fixed password), a connection service, an analysis engine with decoders and rules, a server API, and Filebeat | [Wazuh server](https://documentation.wazuh.com/current/getting-started/components/wazuh-server.html) | Read |
| The indexer stores JSON documents; new data is typically searchable in about one second | [Wazuh indexer](https://documentation.wazuh.com/current/getting-started/components/wazuh-indexer.html) | Read |
| The dashboard queries data and includes a ruleset test tool | [Wazuh dashboard](https://documentation.wazuh.com/current/getting-started/components/wazuh-dashboard.html) | Read |
| Logcollector gathers logs; the analysis step decodes then matches rules; alerts go to `alerts.log` and `alerts.json`; all logs go to the archive files; the server retains logs and does not delete them automatically | [How log data collection works](https://documentation.wazuh.com/current/user-manual/capabilities/log-data-collection/how-it-works.html) | Read |
| Pre-decoding extracts timestamp, hostname and program name; decoder options `parent`, `program_name`, `prematch`, `regex`, `order`; `regex` needs an `order`; static field names include `srcuser`, `dstuser`, `user`, `srcip`, `action`, `status`; a parent can have many children | [Decoders syntax](https://documentation.wazuh.com/current/user-manual/ruleset/ruleset-xml-syntax/decoders.html) | Read; the decoder on this page is **UNVERIFIED** |
| Rule `level` 0 to 16, `frequency` 2 to 9999, `timeframe` in seconds, `ignore` in seconds; `if_matched_sid` works with `frequency` and `timeframe`; `same_srcip`; a level 0 rule is discarded immediately and cannot be used with `if_matched_sid` | [Rules syntax](https://documentation.wazuh.com/current/user-manual/ruleset/ruleset-xml-syntax/rules.html) | Read; the rules on this page are **UNVERIFIED** |
| Custom rule IDs between 100000 and 120000; custom rules in `/var/ossec/etc/rules/`; restart the manager for alerts | [Custom rules](https://documentation.wazuh.com/current/user-manual/ruleset/rules/custom.html) | Read |
| Custom decoders in `/var/ossec/etc/decoders/` (`local_decoder.xml`); the documentation's own `example` program has a parent decoder by program name and a child by `regex` and `order` | [Custom decoders](https://documentation.wazuh.com/current/user-manual/ruleset/decoders/custom.html) | Read |
| `wazuh-logtest` shows pre-decoding, decoding and rule phases and runs from the dashboard, the command line or the API; changes need a restart to produce real alerts | [Testing decoders and rules](https://documentation.wazuh.com/current/user-manual/ruleset/testing.html) | Read; not run |
| The ruleset layout under `/var/ossec/ruleset/` is overwritten on upgrade; use `/var/ossec/etc/`; logtest takes one-line logs | [Ruleset](https://documentation.wazuh.com/current/user-manual/ruleset/index.html) | Read |
| `location` may be `journald` when `log_format` is `journald` | [localfile reference](https://documentation.wazuh.com/current/user-manual/reference/ossec-conf/localfile.html) | Read; the filter fields the template uses are **UNVERIFIED** against an agent |
| The connectors' log sources, the agent being off by default, no headless client, enrollment on 1514 and 1515 | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` and `docs/stages/02-telemetry.md` in this repository, read 2026-10-30 | Read; nothing applied |
| The two scripts, their outputs, exercises 1 to 4 | Run on Linux, Python 3.13.5, 2026-10-30 | Run. `tests/test_wazuh_pipeline_lesson.py` re-runs them from this page |
| Whether a real rule counts by the event's own time or the receive time; whether `archives.json` is on by default; the dashboard's alert on a disconnected agent | Not in the pages read | **UNVERIFIED** |

Not verified, plainly: every behavior of a running Wazuh; the draft decoder and rules in a manager; the journald path on a connector; Windows (the commands are not given); any metric of memory or cost.

Next: [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md). Back to the [Reading order](Reading-Order.md).
