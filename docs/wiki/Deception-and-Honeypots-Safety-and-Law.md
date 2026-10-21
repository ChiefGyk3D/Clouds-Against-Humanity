# Deception safety and law: should you run one?

Lesson 6 of the [deception and honeypots track](Deception-and-Honeypots-Start-Here.md), and the one to read **before any hands-on lesson**. A foundations side page to [Droplet hardening](Droplet-Hardening.md) and [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md). It is reading and a one-page plan on paper. Next: [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md), lesson 3.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from reading, nothing run, and not legal advice.** On **2026-10-21** the author read the sources in the [claims register](#claims-register). The author read no statute and no internet provider contract. The rules below are *minimums* to stop you hurting yourself or others, not a statement of what the law allows where you live. Residential internet terms vary, and what yours say is **est.** until you read your own contract.

> **Prerequisites.** [What deception is](Deception-and-Honeypots-What-Deception-Is.md) (lessons 1 and 2). About an hour (est.). Cost: none. This page is the only lesson in the track whose exercise is a reviewer saying "no".

## What you will be able to do

- State the eight minimums for running a decoy that attracts real attackers, and the reason for each.
- Tell apart the low-risk things (a canary file on your own laptop) from the high-risk thing (a machine built to be broken into).
- Say what "counter-hacking" is and why even a good intention does not make it safe or legal.
- Decide, with a short decision tree, whether to stay on theory, do the local lessons, or ever consider a cloud or home sensor.
- Write a one-page plan that a reviewer could say "yes" or "no" to.

## Two very different activities

The word "honeypot" covers two kinds of activity with very different risk.

| Aspect | Honeytokens and honeyfiles (lessons 3 and 4) | A honeypot that attracts real attackers (later tracks) |
|---|---|---|
| What runs | A file, a link, a watcher on your own machine. | A server built to be probed and broken into, reachable by strangers. |
| Who can reach it | You, and anyone already on your machine. | Anyone who can reach its address. |
| What goes wrong | A false alarm; a service that holds your email address. | It is taken over and used against other people; your account is closed; your address is blocked; the machine becomes a route into your network. |
| Safety lesson | The minimums below that apply to data and privacy. | All eight. |

This track's lessons 1 to 6 involve **only the left column**. The right column is the subject of tracks 2 and 3, which are separate later lessons ([what they will need](Deception-and-Honeypots-Start-Here.md#tracks-2-and-3-what-they-will-need)). This page exists so that nobody drifts from the left column to the right one without noticing.

## The eight minimums

Every hands-on lesson that exposes a decoy to strangers repeats these. They come from the education plan, the [honeypot design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md) and the T-Pot README's own warnings (see the [register](#claims-register)).

| # | Minimum | Why |
|---|---|---|
| 1 | **Never on your main LAN.** A honeypot is a machine designed to be broken into, so it lives in a separate segment with no route to anything you care about. On a flat home network (one network, everything on it), do theory and the local lessons only. | If it is taken over, an intruder who owns it is already beside your laptop, your phone and your files. |
| 2 | **Read your internet provider's terms first** before any inbound exposure (a port forward, a public address). | Many residential contracts restrict running servers or inbound services (est.; yours may differ). Breaking a contract can cost you the service. |
| 3 | **Get the cloud provider's written consent** for a cloud sensor, and read its acceptable-use policy. | A provider can close an account that appears to host attacks, even if you are only the bait. The design records what the providers' own policies say (section 7.4). |
| 4 | **Closed or allow-listed outgoing traffic.** The honeypot must not be able to attack anyone else. | A taken-over decoy with open outgoing access becomes a launch point, and the abuse report goes to you. |
| 5 | **No counter-hacking.** No scanning back, no breaking into an attacker's machine, no reporting by script. Watch and record; that is all. | It is risky and often illegal, and it is easy to hit an innocent machine: attackers use other people's computers. A good motive is not a defense. |
| 6 | **No real data on it.** No real files, reused passwords or real keys. | Decoys are meant to be taken. Whatever is on one is lost. |
| 7 | **Raw logs stay private.** Share counts and summaries, not raw logs. | Logs hold addresses and strings from people who did not agree to be recorded. |
| 8 | **A named stop.** An end date and a kill switch, written before you start. | Temporary experiments become permanent hazards when nobody remembers them. |

## Which minimums apply to which lesson

| Lesson | Minimums that apply | Why not the rest |
|---|---|---|
| 3: a canary token | 6 (invented data), 7 (privacy of what the service sees) and 8 (a stop: delete the token) | Nothing is exposed to strangers. |
| 4: honeyfiles | 6, 7 (what your watcher records), 8 | A watcher on your own folder. |
| 5: a rule in the SIEM | 6 (synthetic data only), 7 | The events are made up at run time. |
| Any internet-facing sensor | All eight | This is where the risk lives. |

## Counter-hacking, in plain terms

When a decoy is probed, it is tempting to look back: scan the address, try to log in, send a nasty message, run a script that files abuse reports. **Do none of it.**

- The address that touched your decoy is often not the attacker. It may be a compromised home router, a rented server, or a proxy. Probing it can be a computer-misuse offense against an innocent owner (not legal advice; the law differs by place).
- Scanning another person's machine without permission is the same act whether you were provoked or not.
- A script that files reports at scale makes mistakes at scale.

The passive route is the safe one: record, keep the record private, and if something reaches your own accounts, use the provider's normal abuse channel by hand.

## Recording people who did not agree

A decoy that attracts strangers records strangers. Their addresses, the usernames they try and the passwords they guess can include real people's data (a leaked password from a breach, a person's real username). Two habits follow from that:

- **Aggregates, not raw logs, are what you publish**: counts per day, top usernames with the passwords removed, a map-free summary. Never paste a raw log into an issue, a chat or a blog.
- **Decide what you keep and how long**, and write it down. A shorter retention is a kinder default.

Inside your own network the question is different: staff or housemates who trip a canary file are recorded by your watcher. At home, tell the household. **At work, a canary on a company system is not yours to deploy** without the owner's written permission.

## A decision tree

Start at the top. Stop at the first "no".

1. **Do you want to understand how deception works?** Read lessons 1 and 2. Stop here if that is enough. Cost: nothing.
2. **Do you want to try it with nothing exposed?** Lessons 3 to 5 run on your own computer. Read minimums 6 to 8 first.
3. **Do you want a sensor that strangers can reach?** Then answer, in writing, every item in the plan below. If you cannot answer one, the answer is "not yet".
4. **Is it on a separate network or a separate cloud account, with no route to anything you care about, outgoing traffic closed, and the provider's consent?** If not, no.
5. **Do you have an end date and a person who will read the abuse inbox?** If not, no.
6. **Are you doing this at work, on a network you do not own, or on one you share with others?** Get written permission from the owner first, or do not do it.

## Exercise: write your one-page plan

**Predict.** Before you write: do you expect to end the exercise wanting to run a sensor, or deciding to stay on theory? Write down which, and why.

**Do.** On one page, in your own words, answer:

| Question | Your answer |
|---|---|
| What do I want to learn, and can lessons 3 to 5 teach it without exposing anything? | |
| Whose account or whose hardware, and who pays for what? | |
| Which network does it sit on, and what is the route from it to anything I care about? (The answer should be "none".) | |
| What does the provider's or my internet provider's contract say about this? (Quote the clause or say "not read yet".) | |
| What can it send out? (The answer should be "nothing, apart from the one path I list".) | |
| What data is on it? (The answer should be "invented".) | |
| What do I record, how long do I keep it, and what do I publish? | |
| When does it stop, and what is the kill switch? | |
| Who reads the abuse inbox, and how often? | |

**Check.** A reviewer, such as the maintainer or a peer, reads the page and answers one question: *would you run this?* A reviewer who says "not yet" is giving you the lesson. Write down the first thing they would need to see.

**Undo.** Nothing: it is paper. If you decide to run something later, the plan is the thing you check against.

## Build, break, detect, evade, defend (on paper)

- **Build.** The plan above.
- **Break.** The reviewer reads for the hole: a route you did not list, a credential you reused, a missing end date, a clause you did not read.
- **Detect.** What would tell you it has gone wrong: a spike in outgoing traffic, an email from the provider, a new process, a login from an address you do not recognize. For each, name where you would see it.
- **Evade.** What would an attacker who owns the decoy do next: look for other machines on the same network, try your cloud account's credentials, try to send spam or attack others from your address. Each of those is a reason a minimum exists.
- **Defend.** The minimums, as controls: separate network, closed outgoing traffic, no real data, a time limit.
- **Flip the board.** You are now the provider's abuse team, getting a report that a machine in your network is attacking somebody. What would you want to know from the customer, and how would you tell a careful learner from a careless one? Put yourself in that inbox before you write to one.

## Common mistakes

| Mistake | Why it hurts | Better |
|---|---|---|
| "It is only for a weekend." | A weekend setup gets forgotten. | Write the end date and the kill switch first. |
| Using the same password or key "because it is just a decoy". | The first taken-over decoy leaks the real one. | Invent everything. |
| Skipping the contract. | The consequence arrives as a closed account. | Read the clause; quote it in the plan. |
| Looking back at the attacker. | Offense risk and wrong targets. | Passive only. |
| Posting a raw log to ask for help. | Other people's data, public. | Post counts, or invented lines in the same shape. |

## Claims register

Retrieved 2026-10-21 unless stated.

| Claim | Source | Status |
|---|---|---|
| The eight minimums, and the statement that residential terms vary | [Honeypot and deception education plan, section 3.4](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-22-honeypot-education-plan.md) | Read in this repository. The internet provider point is **est.**: no contract was read |
| Provider policies on consent and acceptable use; closed outgoing traffic; separate account; retention and publishing raw logs | [Honeypot design, sections 3, 6 and 7](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md) | Read in this repository; the design itself says what it read and what it did not |
| T-Pot's README warns "You install and run T-Pot within your responsibility", that a compromise "can never be ruled out", that honeypots "should not host any sensitive data", that data is submitted to a community project by default, and that its installation wants "a working (outgoing non-filtered) internet connection" | [T-Pot README](https://raw.githubusercontent.com/telekom-security/tpotce/HEAD/README.md), default branch | Read |
| Probing an address that touched a decoy can hit an innocent owner; attackers use other people's machines | General knowledge | **est.** |
| What the law of your country says about recording visitors, scanning back, or running a server on a residential line | Nothing | **Not read.** This page does not tell you |

Not verified, plainly: any law, any contract, any provider's current policy beyond what the design recorded.

Next: [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md), lesson 3. Or back to the [track hub](Deception-and-Honeypots-Start-Here.md).
