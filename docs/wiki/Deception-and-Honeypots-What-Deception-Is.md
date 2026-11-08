# What deception is: decoys, lures, honeytokens and honeypots

Lessons 1 and 2 of the [deception and honeypots track](Deception-and-Honeypots-Start-Here.md). A foundations side page to [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md): read that page first. Everything here is reading and paper exercises; nothing needs an account, a server or a tool. Next: [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md), lesson 6, which comes before any hands-on lesson.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from reading, nothing run.** On **2026-10-21** the author read the sources in the [claims register](#claims-register) and wrote this page. There are no commands to run on it; the two exercises are on paper. Where a source is a vendor's own article, the page says so and reports its statements as the vendor's claims, not as measured facts. No product was installed, tried or priced.

> **Prerequisites.** [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) (what an alert and a false alarm are) and, for the paper exercise, the [Threat model](Threat-Model.md) table. About 2 to 2.5 hours with both exercises (est.). Cost: none, and no hardware.

## What you will be able to do

- Say in a sentence what deception is, and name the difference between a decoy, a lure, a breadcrumb, a honeytoken, a honeypot and a honeynet.
- Tell low, medium and high interaction apart, and say which one carries the most risk to the person running it.
- Say why a touch on a decoy inside your own network is worth a human look, and name at least four ordinary things that can touch it anyway.
- Say why the same idea gives noisy data on the open internet, and what that data is good for instead.
- Read a vendor's "near-zero false positives" claim and say what would have to be true for it to hold.
- Place decoys on a paper design of this project, and say who or what would trip each one by accident.

## The idea in one paragraph

Almost everything else in security tries to separate good activity from bad by looking at behavior: this login is from an unusual country, this program does something odd. That is hard, because bad behavior often looks like good behavior. **Deception** turns it around. You plant things that **no legitimate person or program has any reason to touch**: a file nobody needs, an account nobody uses, a server nobody was told about. Then you watch them. If something touches one, you do not need a clever judgment about whether the behavior is odd. Nobody should have been there at all, so a person should look. The word for the tool you use is a **decoy**, in a broad sense: a fake that is easy to find, cheap to watch, and worthless to everyone except an intruder.

## The vocabulary

Terms differ between authors. This table follows the usage in one vendor's glossary article (see the [register](#claims-register)), plus two terms that article does not define in the same way. When you read other material, check which meaning it uses.

| Term | What it is | Example, in this wiki's world |
|---|---|---|
| **Decoy** | A fake resource that looks real: a server, a database, an application, an account. | A server named `backup-old` that nothing in the real design uses. |
| **Lure** | Fake information that leads an intruder toward a decoy. | A note listing a login for that server. |
| **Breadcrumb** | A lure planted on a real machine, such as a fake saved credential, to pull an intruder sideways. | A saved-login entry on a laptop for `backup-old`. |
| **Honeytoken** | One fake piece of data that has no use except to be noticed when used: a false record, a fake key, a fake account name. It needs no new server. | A fake customer row in a database copy; a fake API key in a settings file. |
| **Canary token** (**canarytoken**) | A honeytoken built so that using or opening it sends you a message. The name comes from the miner's canary. [Lesson 3](Deception-and-Honeypots-Plant-a-Canary.md) builds one. | A document with a link inside; opening it fetches the link, and the fetch is the alert. |
| **Honeyfile** | A decoy file with an attractive name, watched for access. [Lesson 4](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md) builds one. | `passwords-backup-OLD.txt` in a folder nobody uses. |
| **Honeypot** | A standalone decoy system that accepts connections and logs what happens. The oldest kind of decoy. | A fake SSH server that records every login attempt. |
| **Honeynet** | Several honeypots on a network of their own, built to look like a small environment. | A separate segment holding a few honeypots and the collector that reads them. |

A **honeytoken** and a **honeyfile** can be set up with no server at all. That is why this track starts with them and leaves honeypots to later lessons.

## Low, medium and high interaction

How much a decoy lets the intruder *do* is its **interaction level**. More interaction teaches you more and costs you more risk.

| Level | What the decoy does | What you learn | Risk to you |
|---|---|---|---|
| **Low** | Listens on a port and records that a connection happened. May print a banner. | That something knocked, from where, when. | Smallest: there is nothing to take over. |
| **Medium** | Imitates a service well enough to let the visitor try things: an emulated login and a pretend shell that answers commands without running them. | What credentials and commands the visitor tries. | Moderate: the imitation is software with its own bugs. |
| **High** | A real system the visitor can really use. | The most. Everything the visitor does. | Highest: it is a real machine an intruder controls. It can be used to attack others from your address. |

Where the examples sit: the project's [honeypot design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md) (section 5.1) calls Cowrie's default emulated shell **medium** interaction, and notes that Cowrie's own README describes it as medium to high interaction. A plain listener that only logs connections is low. That T-Pot bundles mostly low and medium honeypots is the education plan's description; the author did not check each bundled honeypot (est.). A real server left open on purpose is high, and the later lessons do not recommend it.

## Where a decoy goes on an intruder's path

Think of an intruder's path as a short story, and put a decoy where a character in the story would reach out.

```text
 1. outside      scan the internet for anything open
 2. foothold     get onto one machine (a stolen password, a bad link)
 3. look around  list files, read saved logins, read notes and settings
 4. move         use what was found to reach another machine
 5. the prize    reach the data or the control the intruder came for
```

| Step | Decoy that fits | What the touch tells you |
|---|---|---|
| 1. outside | An internet-facing honeypot | Someone is scanning. See lesson 2 below: this is a weather report, not a break-in. |
| 3. look around | A honeyfile in a folder on a real machine; a fake saved login (breadcrumb) | Someone is on a machine you thought was clean, reading things. |
| 4. move | A fake server that the breadcrumb points at | Someone is trying to move sideways. |
| 5. the prize | A honeytoken in the data (a fake record) | The data has been copied or used. |

Steps 3 to 5 happen **inside** your network, after the intruder is already in. That is where deception is most useful: it may tell you about a break-in that your other controls missed.

## Lesson 2: why a decoy alert is different, and when it is not

### The zero-activity baseline

Most detection needs a **baseline**: what normal looks like. A decoy has an easy one: **zero**. Nobody legitimate touches it. So the first touch is the anomaly, with no tuning of thresholds and no model. The vendor article this page learned from calls the alerts high-fidelity with very few false positives and sets that against detection that flags departures from a learned baseline.

Teach this as a **conditional**, not a promise. It holds when:

1. **The decoy is somewhere nobody legitimate goes.** A decoy in a folder that a backup job reads is touched every night.
2. **Nothing automatic touches it.** Antivirus scanners, file indexers, backup tools, sync clients, and vulnerability scanners all open files and probe servers.
3. **Only you know it is there.** If a colleague, a contractor or an old script knows the name, their use is an alert.
4. **A person will actually look.** An alert nobody reads has a baseline of zero and a value of zero.

### Inside versus the open internet

The same article concedes the other side: honeypots reachable from the internet can produce many false positives when they cannot tell broad scanning from a targeted visit. Say it plainly: an internet-facing sensor is touched **constantly, by automation, by design**. Its baseline is not zero. What it gives you is **threat intelligence**: what is out there, what it tries first. A sensor *inside* your network, touched once, is **detection**: something is wrong here. The SIEM lessons that follow keep these two apart.

### Reading a vendor claim

The article is a vendor's glossary entry. It is useful for its vocabulary and for the claims it makes, and each claim comes with a condition. The table reports what the article says and asks what has to be true. It does not say whether the claim is right; the author measured none of it.

| The claim (paraphrased) | What would have to be true | A way to test it |
|---|---|---|
| Deception produces almost no false positives, because legitimate users have no reason to touch a decoy. | The four conditions above. | Count how often an authorized system touches your decoy in a month. |
| Alerts are accurate *and* cover many kinds of threat. | Intruders actually go to the decoys; the decoys look real enough that they do. | Run a red-team exercise and count how many intruders reached any decoy. |
| Deception can detect virtually any attack. | "Any" requires the attacker to touch a decoy at some point. An intruder who never looks at what you planted is not caught. | Ask what attack path avoids every decoy, and draw it. |
| Modern platforms deploy and adapt decoys automatically, unlike static honeypots. | That the automation is good enough to be worth its cost and stays accurate as the network changes. | Not testable from this page. The author read no product documentation and measured nothing, so this stays an unmeasured vendor claim. |

A habit worth keeping for all vendor material: find the **condition** hidden in each word like "almost", "virtually" or "any", and write it next to the claim.

## Exercises

Both exercises are on paper. They follow four steps: **predict** (write your answer first), **do**, **check**, **undo**.

### Exercise 1: place decoys on a paper design of this project

The reference design has no decoys. This is a thought exercise on the real design, not a plan to build one.

**Predict.** Pick one row of the [Threat model](Threat-Model.md) (T1 to T14). In one sentence, where would an intruder who succeeded at that row go next?

**Do.** For three different rows, fill this in on paper:

| Question | Your answer |
|---|---|
| What decoy, lure, breadcrumb or honeytoken? | |
| Where does it sit, and on which machine or service? | |
| What would an intruder see that makes it attractive? | |
| What legitimate thing could touch it by accident? | |
| What alert would fire, and who looks at it? | |
| What new risk does the decoy itself add? | |

**Worked example, to compare with after you have tried one.** Row T5, "connector token theft from the droplet". The real token is a file readable only by the administrator account. A decoy could be a second, plausible file name in the same folder, with invented content, watched by the host's audit mechanism (the opt-in auditd work in stage 2 is the closest thing in the repository, and it is written but never applied; see the [Roadmap](Roadmap.md#stage-2-logging-and-the-link-home-design-merged-cloud-side-in-progress-not-applied)). Who could trip it by accident: a backup job, a configuration tool that reads the whole folder, an administrator who lists the folder with a tool that opens files. What new risk: the audit rule is extra configuration to maintain, and a decoy next to a real secret can be confused with it during an incident.

Two things the table forces you to see. First, **never plant a decoy secret in this public repository**: secret scanners flag it, and so does every scraper that reads public code, which means the "touch" would mean "someone scraped GitHub", not "someone is inside". A decoy has to sit where only an intruder would go. Second, the right-hand column is never empty: a decoy is another thing to keep working.

**Check.** Swap with another learner, or re-read after a day. Does every row name a legitimate toucher? A row that says "nobody" is probably wrong.

**Undo.** Nothing: it is paper.

### Exercise 2: decoy touched, or ordinary noise?

Each line below is a synthetic event. The setting for all of them: a small office network with a file server, a canary file `passwords-backup-OLD.txt` in a folder nobody uses, a fake login page on a server with no real purpose (inside the network), and, separately, one honeypot on a cloud server open to the internet.

**Predict.** Before reading the answers, write one of three labels next to each line:

- **A:** a decoy was touched and a person should look now.
- **B:** ordinary noise; no person needs to look.
- **C:** a decoy was touched but it is expected, so the decoy is badly placed and needs fixing.

| # | What happened |
|---|---|
| 1 | At 03:12 the canary file is opened from a user account that has never logged in at night. |
| 2 | The nightly backup reads every file in the file server, including the canary file. |
| 3 | An administrator lists the folder that holds the canary file. |
| 4 | The antivirus scan opens the canary file. |
| 5 | The inside fake login page receives one login attempt using an invented account name, from a laptop on the staff network. |
| 6 | The internet-facing honeypot logs 40 login attempts from 12 unknown addresses in an hour. |
| 7 | The internet-facing honeypot logs a login attempt from the office's own public address. |
| 8 | A file with a name similar to the canary file is opened on a different machine. |
| 9 | The canary file is copied to a USB drive. |
| 10 | The owner of the canary file opens it to test that the alert works. |
| 11 | The inside fake login page is hit by the vulnerability scanner that the security team runs every Friday. |
| 12 | An old script written by a former employee tries the decoy server's name every hour. |
| 13 | A new colleague, never told about the decoys, opens the canary file out of curiosity. |
| 14 | Nothing touches any decoy for three months. |
| 15 | The inside fake login page receives 200 attempts in a minute from one staff laptop. |
| 16 | The internet-facing honeypot receives a connection from an address that, a week later, appears in a threat report. |
| 17 | The canary file's modification time changes, and its contents are different. |
| 18 | The canary file is deleted. |
| 19 | The file server's indexing service reads the canary file after a software update. |
| 20 | The internet-facing honeypot sees a login attempt that uses the invented account name printed in the inside canary file. |

**Do.** Fill in your column. For any line you cannot decide, write what extra fact you would need.

**Check.** One reasonable set of answers, with the reason. Argue with it; the point is the reasoning, not a perfect score.

| # | Label | Reason |
|---|---|---|
| 1 | A | Nobody legitimate has a reason to be there, and the time and account make it stranger. A person looks. |
| 2 | C | A decoy in the backup scope fires every night. Move it or exclude it from the backup, or the alert becomes ignored. |
| 3 | B | Listing a folder is not opening the file. Whether the watch tool distinguishes the two is something you test in [lesson 4](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md). |
| 4 | C | An automatic scanner. Same fix as 2: keep the decoy out of the scan, or teach the rule to ignore that program. |
| 5 | A | Someone on the staff network typed an account that exists only in the lure. That is the lure working, and a person looks. |
| 6 | B | Typical internet-facing sensor traffic. It feeds counts and threat intelligence, not an investigation. |
| 7 | A | An internet honeypot touched from your own public address is not scanning noise. Something inside is behaving like an outsider, or someone is testing. Look. |
| 8 | A or B | Depends on whether the name was part of the plan. If it is a coincidence in naming, your decoy name is too ordinary. Either way it is a sign to look at the name. |
| 9 | A | The decoy was read and copied. Copying matters more than opening. |
| 10 | B | Your own test. Say so in a log or a ticket, or it will look like an incident later. |
| 11 | C | A known, scheduled touch. Allow-list the scanner's address and time, or the Friday alert is trained away. |
| 12 | C | Stale automation. Find and remove the script, then the decoy is clean again. |
| 13 | A (then B) | The alert is right: someone touched it. The follow-up is a human conversation. Deciding who is told about the decoys is part of the design, not an afterthought. |
| 14 | B | Silence is the expected state. It also hides the question "is the sensor working?" Test it on purpose. |
| 15 | A | Two hundred attempts in a minute is a tool, not a person. Look now. |
| 16 | B | An internet sensor feeding intelligence. Record it; nobody needs to be woken. |
| 17 | A | A change is different from a read: someone wrote to the decoy. Look now. |
| 18 | A | Same as 17. |
| 19 | C | An automatic reader. Exclude the decoy from the indexer, or ignore that service in the rule. |
| 20 | A | The invented account name leaked outside. Either the file was copied out or an intruder is testing it from elsewhere. |

**Undo.** Nothing.

What the exercise should leave you with: **C is the most common label** in real use. A decoy is cheap to plant and a steady cost to keep clean.

## Build, break, detect, evade, defend (on paper)

The loop from [Why this exists](Why-This-Exists.md#the-motto-and-the-method), for deception.

- **Build.** You made a placement table (exercise 1). A decoy, a lure and a thing to watch.
- **Break.** Argue as an intruder who already knows deception exists. How would you find out which files are decoys? A file nobody ever modified; a file with a name that is too attractive; an account that has never logged in; a server absent from the inventory; a path no real process reads. Each of those is a fingerprint that a careful intruder can use to skip the bait.
- **Detect.** What would tell you the intruder noticed? A *lack* of expected touches while other signs of activity appear is hard to see; so is a decoy being avoided. This is the weak spot of the whole technique: it detects the careless, not the careful.
- **Evade.** An intruder who is careful skips what looks planted, or checks a file's age and owner before opening it, or reads a copy rather than the original. They may also tamper with the watch itself.
- **Defend.** Make decoys look like their neighbors: realistic names, plausible timestamps, believable content (invented). Rotate them. Keep the watching hard to turn off and tell someone when the watcher goes quiet. Combine decoys with real detection, because they cover different failures.
- **Flip the board.** Now sit on the other side: you are the defender who must keep 50 decoys looking alive, and you can afford to check five a week. Which five? What does that tell you about whether deception scales without automation, and why the vendor article keeps returning to automatic deployment?

## Common mistakes

| Mistake | Why it hurts | Better |
|---|---|---|
| Putting a decoy where scanners or backups reach it. | Daily false alarms, then the alert is ignored. | Place it outside every automatic reader, or allow-list them deliberately. |
| Using a decoy with real data or a reused password. | A decoy that leaks gives away something real. | Invent everything. [Lesson 3](Deception-and-Honeypots-Plant-a-Canary.md) builds samples at run time. |
| Not telling the right people. | Colleagues trip it and it looks like an incident. | A short list of people who know the decoys exist, kept private. |
| Never testing the alert. | You find out it is broken in an incident. | Trip it yourself on a schedule, and write that down. |
| Treating an internet sensor as an intrusion alarm. | Constant alerts, no meaning. | Count and compare; do not page anyone. |
| Treating "no touches" as "no intruder". | The careful intruder skips the bait. | Deception is one layer. |

## Claims register

Retrieved 2026-10-21 unless stated.

| Claim | Source | Status |
|---|---|---|
| Terms decoy, lure, breadcrumb, honeytoken, honeypot as used above; a honeytoken needs no new infrastructure; legitimate users do not interact with decoys, so interaction triggers an alert; deception sets a zero-activity baseline; internet-facing honeypots can produce many false positives when they cannot tell broad scanning from targeted reconnaissance; the article says modern platforms deploy and adapt decoys automatically and that deception can detect "virtually any attack" | [Zscaler Zpedia, "What is deception technology?"](https://www.zscaler.com/resources/security-terms-glossary/what-is-deception-technology) | Read as a vendor's glossary article, in the author's own wording. The author read no Zscaler product page, help page, price or configuration, so nothing on this page describes any product. The statements are the vendor's claims, none of them measured here |
| Cowrie's default emulated shell is medium interaction; Cowrie's README describes it as medium to high interaction | [Honeypot design, section 5.1](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md) | Read in this repository |
| T-Pot bundles mostly low and medium interaction honeypots | [Honeypot and deception education plan, section 3.3](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-22-honeypot-education-plan.md) | The plan's statement; not checked per honeypot here: **est.** |
| Opt-in auditd and Wazuh agent on the connectors are written and never applied | [Roadmap, stage 2](Roadmap.md#stage-2-logging-and-the-link-home-design-merged-cloud-side-in-progress-not-applied) | Read in this repository |
| The loop and "flip the board" | [Why this exists](Why-This-Exists.md#the-motto-and-the-method) | Read in this repository |
| The "C is most common" remark, and the list of automatic readers (backup, antivirus, indexer, scanner) | General experience, not measured | **est.** |

Not verified, plainly: every product behavior; every number of false alarms; whether any of the exercise-2 answers hold in your environment.

Next: [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md), lesson 6, before any hands-on lesson. Or back to the [track hub](Deception-and-Honeypots-Start-Here.md).
