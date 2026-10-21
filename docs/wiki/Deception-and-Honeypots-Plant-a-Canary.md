# Plant a canary token: a tripwire you build and watch

Lesson 3 of the [deception and honeypots track](Deception-and-Honeypots-Start-Here.md). A foundations side page to [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md). You build a tripwire on your own computer first, so you see what a canary token is made of and nothing leaves your machine. A hosted version is described after it, with a terms-and-privacy review as step one. Next: [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md), lesson 4.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the local lab was run once on Linux; everything else was not run.** On **2026-10-21** the author ran every Bash command in the local lab on Linux, with Python 3.13.5 and curl 8.21.0, and pasted trimmed output from that run. **Not run:** the PowerShell commands (no Windows machine; they are marked **est.**), the hosted canarytoken service (the author created no token, sent no email and **did not find** its terms or privacy policy; see [step 1 of the hosted path](#optional-the-hosted-service-with-a-review-first)), and self-hosting. Output varies with your versions and clock.

> **Prerequisites.** [What deception is](Deception-and-Honeypots-What-Deception-Is.md) and [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) (minimums 6, 7 and 8 apply here). [The terminal and your first script](Terminal-and-Your-First-Script.md) for saving and running a script. Python 3 and `curl`. About an hour for the local lab (est.), plus the review time if you take the hosted path. Cost: none for the local lab, and no hardware beyond your computer. For the hosted path the service is described as free (see the register); you give it an email address.

## What you will be able to do

- Say what a canary token is made of: something to find, something that is fetched or used when it is found, and something that tells you.
- Build a local tripwire with a bait document, a link and a fake login, and trip each one yourself.
- Read the alert and say what it shows (a time, an address, a client name) and what it cannot show (who the person is).
- Say what a hosted service learns about you when you use it, and review its terms before you create anything.
- Say why a fetched link trips for robots as well as people.

## What a canary token is

A **canary token** is a tripwire with three parts:

| Part | In this lab | In a hosted service |
|---|---|---|
| **A bait** that looks worth opening | A text file named like an old notes file, with an invented login. | A document, a file, or a key, made by the service. |
| **A trigger**: using or opening the bait makes something happen that you can see | The file contains a link; fetching the link, or using the invented login on a fake login page, makes the local tripwire write a line. | The document contains a unique link or name; opening it fetches it from the service's server. |
| **A way to be told** | A line in a local log file (`alerts.jsonl`), printed to your terminal. | An email, according to the service's guide. |

The service documentation describes canarytokens as motion sensors for networks, computers and clouds that you put where nobody should be looking and get an alarm if they are used (see the [register](#claims-register)). That is the same idea as the lab below, with somebody else running the part that listens.

### What a trip reveals, and what it cannot

When a token is tripped, what the listener sees is what any web server sees: **when** the request came, **from which address**, and **which client** it says it is (the user agent). Not who is holding the keyboard. The address can be a person's home, a company's gateway, a cloud server, a proxy or a mail-scanning robot. The user agent is whatever the client chooses to say. So a trip is a reason to look, never a verdict.

## The local lab

Everything binds to `127.0.0.1` (your own computer). No account, no network, nothing exposed. The lab has two scripts, both standard library only, and uses invented data built when you run it.

**Bash and PowerShell.** The commands are given for **Bash** (Linux, macOS Terminal, WSL, Git Bash) and **PowerShell** (Windows). PowerShell commands are **est.**: not run. On Windows, run Python as `py -3` or `python` where the Bash text says `python3`.

### Set up

```bash
mkdir -p ~/deception-lab/canary && cd ~/deception-lab/canary
```

```powershell
New-Item -ItemType Directory -Force $HOME\deception-lab\canary | Out-Null
Set-Location $HOME\deception-lab\canary
```

Save these two files in that folder with a plain-text editor (in Notepad choose "All files" so it does not add `.txt`).

`build_bait.py` makes the bait document and a settings file. It creates the "password" with the `secrets` module each time you run it, so no secret-shaped text is written in advance:

```python
# Builds the decoy document and the tripwire's settings. Everything is invented
# at run time; nothing here is a real account or a real secret.
import json, os, secrets

PORT = int(os.environ.get("TRIPWIRE_PORT", "8099"))
cfg = {
    "port": PORT,
    "token_id": secrets.token_hex(8),
    "decoy_user": "svc-backup-" + secrets.token_hex(3),
}
decoy_password = secrets.token_urlsafe(12)  # printed only into the bait file

os.makedirs("bait", exist_ok=True)
with open("tripwire.json", "w") as f:
    json.dump(cfg, f)
with open("bait/vpn-notes-OLD.txt", "w") as f:
    f.write(
        "DECOY FILE - invented for a lab, nothing here is real\n"
        "Old backup login, do not use:\n"
        f"user: {cfg['decoy_user']}\n"
        f"password: {decoy_password}\n"
        f"details: http://127.0.0.1:{PORT}/t/{cfg['token_id']}\n"
    )
print("built bait/vpn-notes-OLD.txt and tripwire.json")
```

`tripwire.py` is the listener. It does three things: it answers the planted link, it answers a fake login page, and it writes a line to `alerts.jsonl` only for those two. It reads at most 1,024 bytes of a login body, refuses a `Content-Length` that is not a number, and gives up on a slow client after five seconds. It never records the password, and every field goes through `json.dumps`, which escapes quotes and control characters so a hostile client name stays inert data:

```python
# A local tripwire. It listens on 127.0.0.1 only. Two things are decoys:
#   GET /t/<token_id>  - the link planted in the bait file (a "web bug" token)
#   POST /login        - a fake login page; only the decoy username raises an alert
# Run: python3 -I tripwire.py     (stop with Ctrl+C)
import http.server, json, time, urllib.parse

CFG = json.load(open("tripwire.json"))
LOG = "alerts.jsonl"

def alert(eventid, handler, **extra):
    rec = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "eventid": eventid,
        "src_ip": handler.client_address[0],
        "user_agent": handler.headers.get("User-Agent", "")[:100],
    }
    rec.update(extra)
    line = json.dumps(rec)  # escapes quotes and control characters: hostile input stays data
    with open(LOG, "a") as f:
        f.write(line + "\n")
    print("ALERT", line, flush=True)

class Handler(http.server.BaseHTTPRequestHandler):
    timeout = 5  # a client that promises more bytes than it sends cannot hold a thread forever

    def log_message(self, *args):  # keep the console quiet; alerts.jsonl is the record
        pass

    def reply(self, code, body=b""):
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/t/" + CFG["token_id"]:
            alert("decoy.token.hit", self)
            self.reply(200, b"ok")
        else:
            self.reply(404)  # ordinary noise: no alert

    def do_POST(self):
        if self.path != "/login":
            return self.reply(404)
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:                    # not a number: refuse, do not guess
            return self.reply(400)
        n = max(0, min(n, 1024))              # negative and huge values are clamped before reading
        body = self.rfile.read(n).decode("utf-8", "replace")
        fields = urllib.parse.parse_qs(body)
        user = fields.get("user", [""])[0]
        if user == CFG["decoy_user"]:
            alert("decoy.credential.used", self, username=user)  # never log the password
        self.reply(401, b"denied")

http.server.ThreadingHTTPServer(("127.0.0.1", CFG["port"]), Handler).serve_forever()
```

Build the bait and read it, with the password hidden so you do not paste it anywhere:

```bash
python3 -I build_bait.py
sed 's/^password: .*/password: <hidden>/' bait/vpn-notes-OLD.txt
```

```powershell
py -3 -I build_bait.py
(Get-Content bait\vpn-notes-OLD.txt) -replace '^password: .*','password: <hidden>'
```

A run on 2026-10-21 produced a file shaped like this (the name and the id are different every time):

```text
DECOY FILE - invented for a lab, nothing here is real
Old backup login, do not use:
user: svc-backup-650d4b
password: <hidden>
details: http://127.0.0.1:8099/t/46da4479ef81123c
```

Start the tripwire in a **second terminal** in the same folder and leave it running:

```bash
python3 -I tripwire.py
```

```powershell
py -3 -I tripwire.py
```

If the port is taken, set `TRIPWIRE_PORT` to another number and run `build_bait.py` again before starting.

### Exercise 1: trip the link

**Predict.** If you fetch the planted link with `curl`, will the tripwire say anything? And what will it say about *who* you are?

**Do (Bash, first terminal).**

```bash
URL=$(sed -n 's/^details: //p' bait/vpn-notes-OLD.txt)
curl -s -o /dev/null -w 'status=%{http_code}\n' "$URL"
BASE=${URL%/t/*}   # the address and port from the bait file, whatever port you chose
curl -s -o /dev/null -w 'status=%{http_code}\n' "$BASE/index.html"
```

**Do (PowerShell, est.).**

```powershell
$url = ((Get-Content bait\vpn-notes-OLD.txt) | Where-Object { $_ -like 'details: *' }) -replace '^details: ',''
(Invoke-WebRequest -UseBasicParsing $url).StatusCode
$base = ([Uri]$url).GetLeftPart('Authority')   # the address and port from the bait file
try { Invoke-WebRequest -UseBasicParsing "$base/index.html" } catch { $_.Exception.Response.StatusCode.value__ }
```

**Check.** The first request returns `status=200` and the second terminal prints an `ALERT` line. The second request returns `status=404` and prints **nothing**: a visit to a page that is not the token is ordinary noise. Trimmed from the run:

```text
ALERT {"timestamp": "2026-10-21T18:52:04-0400", "eventid": "decoy.token.hit", "src_ip": "127.0.0.1", "user_agent": "curl/8.21.0"}
```

Read it: a time, an address (yours, because you fetched it yourself), and `curl/8.21.0`, which is what the client *said* it was. Nothing in the line says who you are.

**Undo.** Nothing to undo; the line stays in `alerts.jsonl`.

### Exercise 2: trip the fake credential

The decoy file also holds an invented login. A *fake credential* is the most common honeytoken in real networks. In real systems the fake account is created in the place where logins are checked and an alert fires when anyone tries it; in this lab the "place" is the fake login page.

**Predict.** If you try a different username on the fake login page, does it alert? If you use the one from the file, will the alert contain the password?

**Do (Bash).**

```bash
BASE=$(sed -n 's/^details: //p' bait/vpn-notes-OLD.txt); BASE=${BASE%/t/*}
U=$(sed -n 's/^user: //p' bait/vpn-notes-OLD.txt)
P=$(sed -n 's/^password: //p' bait/vpn-notes-OLD.txt)
curl -s -o /dev/null -w 'other user: %{http_code}\n' --data-urlencode "user=admin" --data-urlencode "password=x" "$BASE/login"
curl -s -o /dev/null -w 'decoy user: %{http_code}\n' --data-urlencode "user=$U" --data-urlencode "password=$P" "$BASE/login"
```

**Do (PowerShell, est.).**

```powershell
$b = Get-Content bait\vpn-notes-OLD.txt
$base = ([Uri](($b | Where-Object { $_ -like 'details: *' }) -replace '^details: ','')).GetLeftPart('Authority')
$u = ($b | Where-Object { $_ -like 'user: *' }) -replace '^user: ',''
$p = ($b | Where-Object { $_ -like 'password: *' }) -replace '^password: ',''
foreach ($body in @{user='admin';password='x'}, @{user=$u;password=$p}) {
  try { Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$base/login" -Body $body } catch { $_.Exception.Response.StatusCode.value__ }
}
```

**Check.** Both attempts get `401 denied`, but only the second prints an alert, and its line holds the username and **no password**:

```text
ALERT {"timestamp": "2026-10-21T18:52:16-0400", "eventid": "decoy.credential.used", "src_ip": "127.0.0.1", "user_agent": "curl/8.21.0", "username": "svc-backup-650d4b"}
```

Why leave the password out? A log is another place to leak from. The username alone says "this decoy was used".

**Undo.** Nothing.

### Exercise 3: a hostile client name stays data

**Predict.** If a client sends a user-agent with a quote, a terminal escape and template braces, will the tripwire's log line stay valid JSON?

**Do (Bash).**

```bash
URL=$(sed -n 's/^details: //p' bait/vpn-notes-OLD.txt)
curl -s -o /dev/null -A $'evil"\x1b[2J{{x}}' "$URL"
tail -n 1 alerts.jsonl
python3 -I -c "import json;print(json.loads(open('alerts.jsonl').read().splitlines()[-1])['user_agent'].encode('unicode_escape'))"
```

**Do (PowerShell, est.).** Windows PowerShell has no `$'...'` quoting; use the Bash track for this exercise, or read the result below.

**Check.** The log line is on one line, with the quote written `\"` and the escape written `\u001b`:

```text
{"timestamp": "2026-10-21T18:52:04-0400", "eventid": "decoy.token.hit", "src_ip": "127.0.0.1", "user_agent": "evil\"\u001b[2J{{x}}"}
```

The line still parses as JSON. Your terminal was not cleared and nothing was run. This is the same rule the [SIEM lesson](Deception-and-Honeypots-Alerts-in-the-SIEM.md) applies to every line it reads: **text from a stranger is data, never an instruction.**

**Undo.** Nothing.

### Stop and tidy

Press Ctrl+C in the second terminal. To remove the lab (it holds only invented data):

```bash
cd ~ && rm -rf ~/deception-lab/canary
```

```powershell
Set-Location $HOME; Remove-Item -Recurse -Force $HOME\deception-lab\canary
```

## Optional: the hosted service, with a review first

A hosted canarytoken service lets you skip building the listener: it makes the bait and sends you an email. That is convenient and it hands **your email address, your description of the token and the addresses of whoever trips it** to a third party. This is optional, and nothing else in the track needs it.

**Step 1: read the terms and the privacy policy before you create anything.** The author tried the policy addresses on the service and on its maker's sites and found only page shells with no policy text (see the register), so *finding the policy is part of your exercise*. If you cannot find it, or you do not accept it, **stop here and use the local lab above**. Write down what the policy says it keeps: your email address, the memo text, the details of each trip (addresses, client names), how long, and who can see them. The two guide pages the author read say the service is free; they do not say what happens to your data.

**Step 2: use synthetic data only.** A throwaway mailbox that links to nothing about you. A memo that names no person, host, project or real identifier. A decoy file with invented content, built the way the local lab builds one. Never a real credential, never a work project name.

**Step 3: create one token** of a simple kind the guide lists (a web or DNS type is the easiest to trip from your own machine; the names on its list change over time), place the bait in a folder you own, and trip it yourself.

**Step 4: read the alert** and compare its fields with `alerts.jsonl`. Which fields does the hosted service add (a place name? a list of details?), and which does it not give?

**Step 5: tear down.** Delete the bait file. If the service lets you delete or disable the token, do it; if it does not, write that in your notes as a cost of using it. Delete the throwaway mailbox when you no longer need it.

**Hosted commands were not run.** The steps are written from the service's guide; creating a token and receiving an alert are untested.

### The self-hosted alternative: UNVERIFIED

The maker publishes the server as open source, and its README recommends a Docker installation. The Docker repository's prerequisites, as read, are **at least one domain name and an internet-facing Docker host**. That is not a free local lab. It also collides with the [safety minimums](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums): a machine that strangers can reach. So this track does **not** teach self-hosting. The author did not install it, did not read its license text and cannot say whether it works as described. If you want no third party, the local lab above does the same job on your own computer.

## Build, break, detect, evade, defend

- **Build.** The bait, the listener and the alert you did above.
- **Break.** Trip the token without a person: any program that fetches links trips it. Try `curl -A 'Mozilla/5.0 (preview-bot)' "$URL"` (PowerShell: `Invoke-WebRequest -UseBasicParsing -UserAgent 'Mozilla/5.0 (preview-bot)' $url`, est.). The tripwire cannot tell a human from a robot; it only sees a fetch. Chat programs, mail scanners and link previewers often fetch links on their own (est.), which is why a token sent through email or chat can alert before anyone opens it.
- **Detect.** What does a real trip look like compared with a robot trip? Look at the fields you have: the user agent, the address and the time. Write one sentence on how you would tell them apart, then notice how weak each clue is.
- **Evade.** An intruder who reads the bait may see that the link points at an unusual name and never fetch it, or fetch it through another address, or use the stolen login only on the real system. The fake credential only alerts where you watch for it. So place each fake credential where **a login is checked and logged**, not only in a file.
- **Defend.** Make a **unique token for each place** you put one, so a trip says *which* bait was found. Keep it away from tools that fetch automatically. Send the alert somewhere a person reads. Test it regularly. Pair it with other detection. Keep what it records to a minimum, as above.
- **Flip the board.** You found this file on a machine you broke into. What do you check before you open the link, and what does that tell you about how a careful defender should name and place a token?

## Common mistakes

| Mistake | Why it hurts | Better |
|---|---|---|
| Creating the hosted token before reading the policy. | You may not be able to take back what you already gave. | Review first. |
| Putting a real name or project in the memo. | The memo is data the service holds, and it shows in the alert. | Invented words only. |
| Logging the password that was tried. | The log is another place to leak from. | Log the username only. |
| One token placed everywhere. | A trip does not say which bait was found. | One per place. |
| Treating a trip as proof of a person. | Robots and scanners fetch links. | A trip is a reason to look. |

## Claims register

Retrieved 2026-10-21 unless stated.

| Claim | Source | Status |
|---|---|---|
| Canarytokens are "like motion sensors for your networks, computers and clouds", put where nobody should be, and are "completely free"; the service needs no installed software; the guide lists many token types; the guide pages show a last-updated mark of 7/23/24 | [Canarytokens guide, introduction](https://docs.canarytokens.org/guide/) and [getting started](https://docs.canarytokens.org/guide/getting-started.html) | Read. The page is older than today, so the list of types may have grown |
| A token alert arrives as an email | The guide's getting-started page, as summarized in the [education plan](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-22-honeypot-education-plan.md) section 3.3 | Not re-checked on the page text here: **est.** |
| The hosted service's terms and privacy policy | Tried: `canarytokens.org/terms`, `canarytokens.org/privacy`, `thinkst.com/terms`, `thinkst.com/privacy`, `canary.tools/terms`, `canary.tools/privacy`. The pages returned were application shells or generic company pages with no policy text I could read | **Not found.** What the hosted service keeps about you is unknown to this page. Read it yourself before creating a token |
| The open-source server exists and the README recommends a Docker installation; the Docker repository lists as prerequisites at least one domain name and an internet-facing Docker host | [canarytokens README](https://raw.githubusercontent.com/thinkst/canarytokens/master/README.md) and [canarytokens-docker README](https://raw.githubusercontent.com/thinkst/canarytokens-docker/master/README.md) | Read. Not installed, not run, license text not read: UNVERIFIED that it works as described |
| Chat programs, mail scanners and link previewers often fetch links automatically | General knowledge | **est.** |
| In real networks the fake credential is an account in the place where logins are checked, and a sign-in attempt on it is the alert | General knowledge | **est.** |
| The local lab scripts and every Bash command, and the output shown | Run on Linux with Python 3.13.5 and curl 8.21.0 on 2026-10-21 | Run. The PowerShell equivalents are **est.** and not run |

Not verified, plainly: the whole PowerShell track; macOS; the hosted service from start to finish; self-hosting; the terms of any service.

Next: [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md), lesson 4. Or back to the [track hub](Deception-and-Honeypots-Start-Here.md).
