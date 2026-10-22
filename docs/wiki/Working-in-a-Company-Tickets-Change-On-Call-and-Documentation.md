# Working in a company: tickets, change, on-call and documentation

Side page to the start-from-zero pages. Read it after [Enterprise engineering habits](Enterprise-Engineering-Habits.md) (core step 9) and the [Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md) page. Those two explain the vocabulary; this page is the practice session: you write the ticket, the change record, the handover note, the runbook step, the post-mortem and the access request, and you learn what to do in your first week. Next: [Architecture overview](Architecture-Overview.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the free local exercises were run once on Linux; the PowerShell versions and the own-fork path were not run.** On **2026-10-22** the author ran the Bash reviewer script and the record counter in the Break, Detect and Defend sections below on Linux (Bash 5, `grep`, `sed`) and pasted what they printed. The PowerShell versions were written from Microsoft's documentation and not run (no Windows machine), so they are marked **est.** The `gh` commands in the own-fork exercise were checked against GitHub's CLI manual on **2026-10-22** but **not run** against a real fork for this page. The ten worked examples were built by reading ten merged pull requests of this repository with `gh pr view` on **2026-10-22**. The classifications are the author's reading for teaching: **this project does not run a change process**, and nobody in it filed these records. Everything with a company in it is an invented, clearly labeled example: no real incident, outage, employer or person appears on this page.

> **Prerequisites.** [Enterprise engineering habits](Enterprise-Engineering-Habits.md) and [Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md) (what standard, normal and emergency changes are). For the exercises, a terminal ([Git from zero](Git-From-Zero.md) shows how to open one) and, for the optional own-fork path, a free GitHub account. No money and no cloud account. About two hours for the reading and the local exercises, and about 45 minutes more for the own-fork path (est.).

## What you will be able to do

- Write a ticket someone else can act on without asking you a question, and say the difference between **priority** and **severity**.
- Write a change request for a real merged pull request in this repository, and classify it as standard, normal or emergency, giving the reason.
- Write a handover note, a runbook step and a short blameless post-mortem.
- Request access with a specific scope, a reason and an end date.
- Read an unfamiliar environment in your first week, know whom to ask and how, and tell the difference between "I can" and "I may".
- Run a small control that catches a change with no rollback plan, say how someone would get around it, and say what stops that.

## What the wiki already says (and the gap)

The vocabulary is covered. The [change management page](Enterprise-Change-Management-for-Beginners.md) defines the change types, the CAB (change advisory board) and the post-implementation review. [Enterprise engineering habits](Enterprise-Engineering-Habits.md) explains why runbooks and blameless post-mortems exist. [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md) covers just-in-time and break-glass access. [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md) lists the roles around the work.

What none of them gives you is a blank form and a worked example. Colleges teach the technology and leave this to your first job, where a manager says "put it in the ticket" and assumes you know what that means. This page is the blank forms, filled in.

One honest limit. Every company does these things a little differently, under different names, in different tools. The templates here are a starting point that matches the common shape, and your employer's template wins.

## Free theory path: the six documents

Read this part with a text editor open. Each section gives a purpose, a template, and a worked example. The examples use invented systems and the reserved documentation addresses `192.0.2.0/24`, `198.51.100.0/24` and `203.0.113.0/24` (RFC 5737), which never belong to a real host.

### 1. A ticket

A **ticket** (also called an issue, a case or a work item) is a numbered record of one request, fault or task. The number is the point: people say "see 4182" instead of retelling the story, and the record keeps who did what and when. The working rule in most companies is "no ticket, no work", because work with no record cannot be prioritized, handed over or audited.

A good ticket answers six questions without a follow-up conversation:

| Question | What to write |
|---|---|
| **What happened, or what do you need?** | One sentence in the title: a verb, the thing, and where. "Reporting page returns an error after 09:00" is a title. "Help" and "It's broken" are not. |
| **What did you expect?** | The behavior you were counting on. |
| **What actually happened?** | The exact words of the error message, copied, not paraphrased. |
| **Who and how many are affected?** | One person, one team, everyone? This drives the urgency. |
| **How can someone see it?** | Steps, a link, a screenshot with private data removed. |
| **What have you tried, and what changed recently?** | Saves the first ten minutes of the person who picks it up. |

**Never put a password, token or key in a ticket.** Tickets are read by many people and kept for years, and they are often searchable. If a secret is part of the problem, say which one and where it lives, and send the value through the approved secrets tool. If you pasted one by mistake, treat it as leaked: tell the owner and have it replaced (the [APIs and tokens page](APIs-and-Tokens-From-Zero.md#when-a-secret-leaks-revoke-then-rotate-then-clean-up) shows the order).

**A weak ticket and a better one** (invented):

```text
Title: Report broken
Body:  The report doesn't work. Please fix ASAP!!
```

```text
Title: Monthly sales report fails with "timeout" since 09:00 today
Expected: Report page loads in under a minute, as it did yesterday.
Actual: Page spins for 5 minutes, then shows: "Request timed out (504)".
Affected: Everyone on the finance team (about 12 people). Month-end close is Friday.
Steps: Sign in, open Reports, Monthly sales, pick last month, press Run.
Tried: Another browser, same result. A colleague sees the same.
Changed recently: Nothing I know of; the server was patched last night (per the notice).
Wanted outcome: Report runs again; if it cannot be fixed today, a way to export the data by Thursday.
```

The second ticket can be triaged by a stranger in two minutes. That is the whole skill.

#### Priority versus severity

These two words get mixed up in every first job. Atlassian's incident management guide (read **2026-10-22**) defines them this way: **severity** is "a measurement of impact" (how much harm the problem does), and **priority** is "a measurement of urgency" (how quickly, and in what order, it should be fixed). They often agree, and sometimes do not:

| Case (invented) | Severity (impact) | Priority (urgency) | Why they differ |
|---|---|---|---|
| The whole company cannot sign in | High | High | Wide harm, fix now. |
| A typo in a headline on the public home page | Low | Can be high | Little functional harm, but the business may want it fixed today for its image. |
| A crash that affects one user in a thousand | High for them | Medium | Severe where it happens, rare, and other work may be wider. |
| A cosmetic glitch in a screen nobody opens | Low | Low | Nothing is lost by waiting. |

Companies attach different numbers to these (SEV 1 to SEV 3 or 1 to 5 are common; est.). What matters is that you write down the **impact** in your ticket in plain words (who, how many, doing what) and let the triager set the priority, because they can see the whole queue and you cannot. Writing "URGENT" in the title does not make it so, and it spends trust you will want later.

**Triage** is the sorting of a queue: read each new ticket, confirm it is clear enough, set severity and priority, assign an owner, and ask for what is missing. Some teams measure **time to first response** and **time to resolution** against a **service level agreement** (SLA, a promised target). Expect your own tickets to wait behind higher priorities, and expect a clarifying question rather than a fix first.

#### How to ask for help without being vague or rude

Use the ticket structure in a chat message: what you are trying to do, what you expected, what happened (exact text), what you tried, and what you need ("a pointer to the right document", "someone to look at this with me for ten minutes"). One message with all of it beats five messages that each say "hey, got a minute?". Say what you have already searched. Say when you need it by, and why.

### 2. A change request, and ten worked examples

You have the vocabulary from the [change management page](Enterprise-Change-Management-for-Beginners.md#the-vocabulary): a **change request** (or RFC, request for change) is the written proposal; a **standard change** is a pre-approved, low-risk, repeatable type; a **normal change** is assessed and approved each time; an **emergency change** takes a fast path and is reviewed afterward. A **rollback** (or back-out) plan is the exact steps to return to the previous state and the point at which you decide to use them.

A template that matches the common shape (use the same fields in any tool):

```text
Title:            <one line: what changes, and where>
Type:             standard | normal | emergency
Reason:           <why now; link the ticket>
Systems affected: <what it touches, and what depends on it>
Description:      <exactly what will be changed>
Risk:             <how likely it is to go wrong, and how bad if it does>
Test evidence:    <where you tried it first, with a link to the result>
Not verified:     <what you could not test, said plainly>
Implementation:   <the steps, in order>
Verification:     <how you will know it worked>
Rollback:         <the exact steps back, and the trigger for using them>
Window:           <when it may happen; who is told>
Approver:         <a person other than you who can say yes>
```

**How to classify, in four questions.**

1. Is it on the company's list of pre-approved types, with a written procedure? Then it is **standard**. Otherwise it is not, however small it looks.
2. Is something broken or under attack right now, and waiting for the normal cycle makes it worse? Then it may be **emergency**, which still gets recorded, approved by someone on call, and reviewed afterward.
3. Otherwise it is **normal**: someone with authority matched to the risk reads it and approves it first.
4. Whatever the type, check that the **rollback** is real. If you cannot undo it, say so in the record, because that raises the risk and the approval level.

**Ten worked examples from this repository.** Each is a real merged pull request, cited by number only (read them with `gh pr view NUMBER --repo ChiefGyk3D/Clouds-Against-Humanity`, or on the Pull requests page on GitHub, on **2026-10-22**). The facts come from the pull request's own description. The type and the reasoning are the author's teaching reading; no company approved or classified these. The sizes are lines added and removed, from `gh pr view`.

| PR | What it changed (in plain words) | Type I would give it | Why | Rollback, and its limit |
|---|---|---|---|---|
| #8 | Added an outbound firewall rule so each connector can open SSH (TCP 22) to the other, scoped to one tag, one port | **Normal** | A firewall is a security boundary, so not a pre-approved type. The page [Trace one change end to end](Trace-One-Change-End-to-End.md) walks this one in detail. | Revert the pull request, read the plan (one in-place firewall update expected). The description says only mocked providers were tested: the real behavior was proved only by the apply. |
| #136 | Fixed a diagram in the README that displayed as raw text (two syntax edits) | **Standard**, if a "documentation fix" type exists; otherwise normal and low risk | No system is touched; it changes a picture and its source file. | Revert. No limit. |
| #139 | Added a test that fails the build if IPv6 is opened inbound or a droplet does not state `ipv6 = false` | **Normal**, low risk | No running system changes, but a stricter test can block everyone's next build, so someone besides the author should agree it is wanted. | Revert. The description states the by-hand `ip -6` check in a guide was not run on a real droplet. |
| #140 | Added a Spacelift plan policy (26 new tests) that denies plans opening inbound rules or IPv6 | **Normal** | It governs every future infrastructure change. **It does nothing until it is attached in Spacelift's own settings**, which is a separate change that needs its own record. | Revert the file, or detach the policy. The description says the plan-policy type's availability on the current plan was unconfirmed. |
| #141 | Extended that policy with a destroy guard (protected resources) and an autodeploy guard | **Normal**, higher risk | It can block a legitimate teardown, and the description says so under "Consequence to know about". A good record states the side effect that surprises people. | Revert, or add an exact address to the allowlist through a reviewed pull request. |
| #142 | Added an opt-in default-drop host firewall on the connectors, off by default | **Normal**, high risk when enabled | Off by default, so merging plans no change. Enabling it **replaces the droplet**, so the description stages it one connector at a time. | Turn the flag off and replace the droplet. The description says it was not tested on a real droplet and names a residual hole. |
| #143 | Corrected four documentation pages that wrongly called a block deprecated | **Standard**, if documentation fixes are pre-approved; otherwise normal and low risk | No code changed. The value is in the evidence: the author read the provider's source and docs and said what was wrong. | Revert. No limit. |
| #147 | Relicensed the repository from MIT to Apache-2.0 | **Normal**, approved by the owner | A legal and ownership decision, recorded as the maintainer's decision. The approver is the person with the authority, not a reviewer of code. | **Partly irreversible:** the description says releases already published stay MIT for those who have them. A rollback plan can say "this cannot be fully undone", and that raises the approval needed. |
| #163 | Made the cost gate refuse backup configurations it cannot price | **Normal**, low to medium risk | It changes a control that blocks other people's merges. The description lists the behavior change and what it cannot see (backups enabled outside OpenTofu). | Revert. |
| #173 | Moved the Twingate provider from 3.x to 5.x across six directories | **Normal**, higher risk | A major-version upgrade that touches the lock files for state. The description says it is **not done until the maintainer reads the first real plan**, and lists "not verified": a real plan with the new version. | Revert the version pin and lock files, then re-initialize. A provider state upgrade can be hard to reverse (est.); the description of #143 says version 4 carries an in-place state upgrader. |

Three patterns to notice. First, almost every real change is **normal**; "standard" is a narrow category you earn by defining and repeating a procedure. Second, the best descriptions have a **Not verified** section, which is exactly what an approver needs. Third, **none of the ten is an emergency**, and that is typical: a real emergency is rare, and a team that has many has a different problem (see the Evade step below).

**An emergency change, shown rather than done (invented).** At 02:10 an expired certificate is breaking sign-in for every customer, the renewal job failed, and the on-call engineer has the renewed certificate ready. Waiting for the next change meeting would mean hours of outage. The engineer calls the duty approver (the emergency CAB, or ECAB, a small on-call group), gets a verbal yes, applies it, and writes the record the same morning with: the incident number, who approved and when, what was done, and the verification. A review a day or two later checks that the emergency path was needed and what to fix so it is not needed again. If any of those steps is skipped, the emergency path has become a way around the control.

### 3. A handover note

A **handover note** is what you leave for the person who takes over your work for a day, a week or a role: an on-call shift ending, a vacation, a move to another team. The test is simple: could they carry on without calling you? Include what is **in progress**, what is **waiting on someone** and what is **likely to happen in the next few days**, plus where the evidence lives.

```text
Handover: reporting service, week of the 5th (invented)
From: the outgoing on-call engineer       To: the incoming on-call engineer
Open items:
  1. Ticket 4182 (reports time out). Cause not found. Tried: restarting the service
     (no change), checking disk space (fine). Next idea: the nightly import job
     holds a lock; look at its start and end times. Owner: me until Monday 09:00.
  2. Change CHG-0931 (firewall rule for the new reporting range) approved for
     Tuesday 22:00. Rollback is in the record. You run it.
Watch for: the backup job fails silently if the disk is above 90 percent;
  the alert has been noisy this week (see ticket 4177, it is a known false alarm).
Do not do: restart the database before 18:00; the finance close is running.
Contacts: database owner team (channel #db-help); the on-call manager for escalations.
Where things are: runbook "Reporting service" in the team wiki; dashboards linked there.
```

The line "Do not do" and the line "Watch for" are the ones people forget and the ones that save a day.

### 4. A runbook step

A **runbook** is written operating steps for a system: how to start, check, fix, and undo. The person reading it is tired and may not have built the system, so every step says what to run, what you should see, and what to do if you do not see it. This repository's own runbooks are the stage guides in `docs/stages/`; the habit is explained in [Enterprise engineering habits](Enterprise-Engineering-Habits.md#runbooks-how-to-operate-it-written-before-you-need-to).

Template for one step:

```text
Step N: <verb and object>
Run:       <the exact command or click>
Expect:    <what you should see>
If not:    <what it means and what to do>
Undo:      <how to reverse this step>
```

An example (invented system and address; the commands are shown, not meant to be run anywhere):

```text
Runbook: restart the reporting service safely (host 192.0.2.10, invented)
Preconditions: no report is running (step 1), and an approved ticket or on-call page exists.

Step 1: Check that no report is running
Run:     ssh -t admin@192.0.2.10 'sudo systemctl status reporting.service'
Expect:  "active (running)" and no line saying "job in progress".
If not:  A job is running. Wait up to 15 minutes; if it is still running, ask the owner. Do not restart.
Undo:    Nothing changed.

Step 2: Restart the service
Run:     ssh -t admin@192.0.2.10 'sudo systemctl restart reporting.service'
Expect:  No output, exit status 0.
If not:  Copy the last 20 lines of 'sudo journalctl -u reporting.service' into the ticket and escalate (see below).
Undo:    The previous state was "running"; if it does not come back, escalate. There is no safe manual rollback.

Step 3: Verify
Run:     curl -s -o /dev/null -w '%{http_code}\n' http://192.0.2.10:8080/health
Expect:  200
If not:  Wait one minute and try again. Then escalate.

Escalate to: the service owner on call (channel #reporting-oncall); after 30 minutes with no reply, the on-call manager.
Last tested: <date> by <role>. A runbook never tested is a guess.
```

Notice what a good step contains that a bad one does not: an **expected result** (so you can tell it worked), an **if not** (so a miss is not a panic), and an **undo** (so you know what you can safely try).

### 5. A short blameless post-mortem

A **post-mortem** (or post-incident review) is a short written account of an incident, written afterward, to learn from it. **Blameless** means it looks for contributing causes in the system, the process and the tools, without pointing at a person. Google's Site Reliability Engineering book (chapter "Postmortem Culture", read **2026-10-22**) puts it this way: a blameless postmortem focuses on "the contributing causes of the incident without indicting any individual or team", and assumes everyone involved had good intentions and did the right thing with the information they had. The reason is practical. If people fear being blamed, they hide what happened, and you lose the lesson.

> **This incident is fictional.** It is invented for teaching. No real outage, company, system or person is described, and roles are used instead of names.

```text
Post-mortem FICT-0001: nightly backups silently stopped for six days (FICTIONAL)
Status: complete.   Severity: 2 (data at risk, no data lost).   Duration: 6 nights.

Summary
  The nightly backup job of the invented "reporting" server failed every night
  for six nights. A restore request on day 7 found the newest backup was six days old.
  No data was lost. The job had been failing quietly.

Impact
  Had the disk failed during the six days, up to six days of reports would
  have been lost. Nothing was lost. Two staff spent about four hours confirming
  the state of the data.

Timeline (day and local time, invented)
  Day 1 22:00  A routine change (a firewall rule edit) closes the port the
               backup job uses to reach the storage server. The change record
               lists "reporting server" only, not "backup path".
  Day 2 02:00  The backup job fails and writes an error to a log nobody reads.
               No alert is attached to the job. It fails again each night.
  Day 7 10:15  A user asks the on-call engineer to restore a deleted file.
  Day 7 10:25  The engineer finds the newest backup is six days old and raises a ticket.
  Day 7 11:00  The cause is found in the job's log. The rule is corrected under
               an emergency change; the job is run by hand and succeeds.
  Day 7 14:30  The restore request is completed from the new backup.

What went well
  The on-call engineer checked the age of the backup before restoring, which
  turned an unnoticed problem into a ticket within ten minutes.

Where we got lucky
  Nothing broke during the six days.

Contributing causes (the system, not a person)
  1. The change record listed systems by name and had no field for what depends
     on the system, so nobody was prompted to ask what uses that port.
  2. The backup job had no alert for "no successful run in 36 hours".
  3. The only evidence of failure was a log nobody was assigned to read.
  4. The inventory of dependencies was out of date.

Action items (each has an owner role and a due date, counted from day 7)
  A1. Add an alert: no successful backup in 36 hours. Owner: backup owner. Due: day 13.
  A2. Add a "what depends on this" line to the change template. Owner: change process owner. Due: day 20.
  A3. Update the dependency inventory for the reporting server. Owner: system owner. Due: day 27.
  A4. Add a restore test to the monthly checklist. Owner: operations lead. Due: next month.

Lessons
  A backup that has never been checked is a hope. The change process could not
  catch this because the information it needed was not in the record.
```

Read it again for what is missing: there is no "the engineer should have". Every cause is a gap a person could not have been expected to fill unaided. That is the discipline, and it is harder to write than it looks.

### 6. An access request

You do not just get administrator rights. You ask, you say why, you say for how long, and an owner approves. The reasoning is **least privilege**: grant the smallest permission that lets the job be done, for the shortest time (see [Enterprise engineering habits](Enterprise-Engineering-Habits.md#least-privilege-at-every-layer) and [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md) for just-in-time and access reviews).

```text
Access request (invented)
Who:        <your name or account id>
What:       Read-only access to the "reporting" database, schema "sales".
            Not: write access, other schemas, or the production admin role.
Why:        Ticket 4182. I need to read the import job's timestamps to find the
            cause of the timeouts. I cannot see them through the application.
Duration:   Until 2026-11-05 (two weeks), then remove it.
Alternatives tried: Asked the database team to run the query; they are booked this week.
Approvers:  My manager (confirms I need it for my work); the data owner for "sales"
            (confirms the data may be read by me).
When done:  I will note the result in the ticket and ask for the access to be removed.
```

Why two approvers? Your **manager** answers "does this person need this to do their job?" The **data owner** (or system owner) answers "may this person see or change this?" Neither can answer the other's question. A request that lists a specific scope, a reason and an end date is easy to approve; "please give me admin on everything" is easy to refuse, and should be.

**Why "temporary" access has an end date.** Access that is never removed accumulates, and a stolen account then reaches far more than the job needs. An end date, plus a periodic **access review** (a recurring check by an owner that each person's access is still needed), keeps the number of paths small. When your need is over, ask for removal yourself.

### On-call: the first five minutes

**On-call** means you are the named person who answers an alert out of hours for a period. It is a shared duty, usually with a schedule and a way to hand it on, and a good team never leaves it to one person forever. When the page arrives:

1. **Acknowledge it**, so the system and your team know a human has it. This is not a promise to fix it alone.
2. **Read the alert and open the runbook** for that alert, if there is one.
3. **Judge impact** in plain words: who cannot do what? That sets severity.
4. **Stop the harm first, find the cause second.** If a rollback or a failover restores service, do that before you study why it broke.
5. **Escalate early** if the runbook does not cover it, the impact is wide, or you are unsure. Asking for help at minute ten is fine; asking at hour three is late.
6. **Tell people** what you know and when you will update next, even if you know little.
7. **Write down what you do, with times**, as you go. It becomes the timeline in the post-mortem.

Practices vary by company and by tool (est.). Treat this as a shape, not a rule.

### Your first week: reading an unfamiliar environment

Nobody expects you to know the systems. They expect you to find out safely. The unwritten questions of week one:

| Question | Where an answer usually lives |
|---|---|
| What does this team own, and what does it not? | The team's page, an inventory, or the service catalog. Ask your manager for the one-page version. |
| Who owns this system? | An owner field in the inventory or catalog, a `CODEOWNERS` file in the repository, or the top of the runbook. |
| How do changes happen here? | The last ten merged changes or closed change tickets. Read them. They are better than the policy. |
| How do I get help at 02:00? | The on-call schedule and the escalation list in the runbook. |
| What breaks, and how do we hear about it? | The last few post-mortems and the noisiest alerts. |
| What do I have access to, and what may I do with it? | Your access list, and the next section. |

**Whom to ask.** Try in this order, and spend a bounded time on each (a common rule is 15 to 30 minutes before you ask; est.): the documentation and the search box, the ticket history for the same words, a teammate, the named owner of the system, the on-call person, your manager. When you ask, give the six pieces from the ticket template. People help the person who has clearly tried.

### "I can" is not "I may"

Being technically able to do something is different from being allowed to. A password that works, a shared folder you can open, a firewall console that lets you click, an admin role someone granted by mistake: all of these say what **you can** do. Only the owner, a policy or an approval says what **you may** do. The unwritten rules:

- If you can see something you should not, **report it instead of using it**. A person who finds an over-broad permission and tells the owner is doing the job well.
- Do not test, scan or probe systems you have not been given written permission to test, inside or outside your company. Authorization is a separate thing from ability, and unauthorized access can be a legal problem as well as a policy one (est.; this page is not legal advice, and laws differ by country).
- Do not reuse another person's account, even if they offer. The audit trail then says the wrong person did it.
- If you are unsure whether a task is yours, **ask before, not after**. The answer costs a minute.

## Where this appears in this project

This project is a one-person lab, and says so. It has the habits (reviewed pull requests, a written plan before apply, a cost gate, runbooks in `docs/stages/`, a [Lessons learned](Lessons-Learned.md) page that works like a short blameless post-mortem) and none of the ceremony: no ticket numbers beyond GitHub issues, no CAB, no on-call. The change management page says it plainly: use it as a decoder ring, not as a description of this repository. The 10 examples above are this repository's pull requests dressed in the fields a company would require.

## Hands-on: a ticket and a change record in your own fork

> **Cost and teardown (read first).** **$0.** This uses GitHub's issues and pull requests on your own free account and a fork of this public repository. GitHub's plans page ([docs.github.com/en/get-started/learning-about-github/githubs-plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans), retrieved **2026-10-22**) describes GitHub Free as unlimited collaborators on unlimited public repositories; I did not find an explicit line for Issues there, so treat "Issues and pull requests in a public repository cost nothing" as **est.** and check your account if in doubt. The project's own board is a free GitHub Project (see [How this project is planned](How-This-Project-Is-Planned.md)). **Teardown:** close the pull request and delete its branch, close the issue, delete the local folder, and optionally delete the fork under its Settings, Danger zone. Nothing here touches this repository or any cloud account, and nothing here changes anything outside your fork. Never run these `gh` commands against the upstream repository by accident: every command below names your fork with `--repo`.

> **Screenshot to take yourself:** your fork's Issues tab after Exercise 4.
> Capture: the ticket with its title and the linked pull request.
> Look for: the title, the six answers in the body, and the "Refs" link to the change.
> Redact: your username if you do not want it shown, and any private notes.

### Exercise 1: classify a pull request (no account needed)

**Predict.** Take #175 (a small documentation correction about expiring tokens). Standard, normal or emergency, and what is the rollback?

**Do (Bash).** You need the `gh` CLI signed in (`gh auth login`), or read the same page in a browser.

```bash
gh pr view 175 --repo ChiefGyk3D/Clouds-Against-Humanity --json title,additions,deletions,changedFiles,files \
  -q '"+\(.additions)/-\(.deletions), \(.changedFiles) files"'
gh pr view 175 --repo ChiefGyk3D/Clouds-Against-Humanity --json body -q .body
```

**Do (PowerShell, est.).**

```powershell
gh pr view 175 --repo ChiefGyk3D/Clouds-Against-Humanity --json title,additions,deletions,changedFiles,files `
  -q '"+\(.additions)/-\(.deletions), \(.changedFiles) files"'
gh pr view 175 --repo ChiefGyk3D/Clouds-Against-Humanity --json body -q .body
```

**Check.** On 2026-10-22 it showed +5/-5 across 5 files, changing wording on a vendor's token feature in documentation and a settings manifest. No infrastructure changes. A reasonable answer is **standard if documentation fixes are a pre-approved type, otherwise normal and low risk**; the rollback is a revert, with no limit. If you said emergency, ask what was broken at that moment (nothing). Now do the same for #170 and compare: it adds a new variable and resources behind flags, with a note about what stays unverified, and is a clearer **normal**.

**Undo.** Nothing; these are reads.

### Exercise 2: rewrite a bad ticket

**Predict.** Which of the six questions does this ticket fail? "Server slow. Fix today. Password is in the next message."

**Do.** In a text file `ticket.md`, rewrite it with the six answers, using invented facts, and no secret. Decide the impact in plain words and leave the priority for the triager.

**Check.** You should have a title with a verb and a place, an expected and an actual result, who is affected, steps, what you tried, and a wanted outcome. If you put a password anywhere, delete it and say what you would do instead (send it through the approved secrets tool and rotate it).

**Undo.** Delete the file.

### Exercise 3: write the change record for a different pull request

**Predict.** For #163 (the cost gate that refuses backup configurations it cannot price), what is the rollback, and what is the one thing you would ask the author to add before approving?

**Do.** Read the pull request with the commands in Exercise 1 (change the number). Fill in the template from section 2 as `chg-163.txt`, using only what the description says. Mark anything the description does not support as "not stated".

**Check.** Compare with the table: normal, low to medium risk; rollback is a revert; the limit is that backups enabled outside OpenTofu are invisible to the gate. A good thing to ask for: how an existing manifest with backups on would be migrated, or a statement that none exists (the description says every committed manifest has backups off).

**Undo.** Delete the file.

### Exercise 4: file a ticket and a change record against your own fork

**Predict.** If you open the pull request with `gh pr create` and forget `--repo`, where might it go? (Answer: toward the upstream repository, which you do not want. That is why every command below names your fork.)

**Do (Bash).** Replace `YOUR-USER` with your GitHub username.

```bash
gh auth status
gh repo fork ChiefGyk3D/Clouds-Against-Humanity --clone=false
# Forks may start with Issues turned off (est.). Turn them on for your fork:
gh repo edit YOUR-USER/Clouds-Against-Humanity --enable-issues
```

Write the ticket (a file, so you can edit it):

```bash
cat > ticket.md <<'EOF'
Expected: A practice note exists that explains what a change record is.
Actual: There is no such note in this fork.
Affected: Only me; this is a practice fork.
Steps: Look in the repository root for a file called practice-notes.md.
Tried: Searched the wiki folder; nothing with that purpose.
Wanted outcome: A one-page practice-notes.md file.
Priority (my suggestion; triager decides): Low. Severity: Low.
EOF
gh issue create --repo YOUR-USER/Clouds-Against-Humanity \
  --title "Add a practice note explaining change records" --body-file ticket.md
```

Note the number it prints (for example `#1`). Then make the change on a branch:

```bash
gh repo clone YOUR-USER/Clouds-Against-Humanity f12-practice
cd f12-practice
git switch -c practice/f12-change-record
printf '# Practice notes\n\nA change record says what, why, risk, test evidence and rollback.\n' > practice-notes.md
git add practice-notes.md
git commit -m "practice: add a note about change records"
git push -u origin practice/f12-change-record
```

Write the change record as the pull request description:

```bash
cat > change.md <<'EOF'
Refs #1

Type: standard (practice; no real system)
Reason: Ticket #1.
Systems affected: One new Markdown file in this fork.
Risk: None to any running system.
Test evidence: The file renders on GitHub.
Rollback: Revert this pull request.
Approver: Myself (practice only; at work this must be someone else).
EOF
gh pr create --repo YOUR-USER/Clouds-Against-Humanity --base main \
  --head practice/f12-change-record --title "practice: add a note about change records" \
  --body-file change.md
```

**Do (PowerShell, est.).**

```powershell
gh auth status
gh repo fork ChiefGyk3D/Clouds-Against-Humanity --clone=false
gh repo edit YOUR-USER/Clouds-Against-Humanity --enable-issues

@'
Expected: A practice note exists that explains what a change record is.
Actual: There is no such note in this fork.
Affected: Only me; this is a practice fork.
Steps: Look in the repository root for a file called practice-notes.md.
Tried: Searched the wiki folder; nothing with that purpose.
Wanted outcome: A one-page practice-notes.md file.
Priority (my suggestion; triager decides): Low. Severity: Low.
'@ | Set-Content ticket.md
gh issue create --repo YOUR-USER/Clouds-Against-Humanity `
  --title "Add a practice note explaining change records" --body-file ticket.md

gh repo clone YOUR-USER/Clouds-Against-Humanity f12-practice
Set-Location f12-practice
git switch -c practice/f12-change-record
Set-Content practice-notes.md "# Practice notes`n`nA change record says what, why, risk, test evidence and rollback."
git add practice-notes.md
git commit -m "practice: add a note about change records"
git push -u origin practice/f12-change-record

@'
Refs #1

Type: standard (practice; no real system)
Reason: Ticket #1.
Systems affected: One new Markdown file in this fork.
Risk: None to any running system.
Test evidence: The file renders on GitHub.
Rollback: Revert this pull request.
Approver: Myself (practice only; at work this must be someone else).
'@ | Set-Content change.md
gh pr create --repo YOUR-USER/Clouds-Against-Humanity --base main `
  --head practice/f12-change-record --title "practice: add a note about change records" `
  --body-file change.md
```

**Check.** On your fork's Issues tab, ticket #1 appears; on the Pull requests tab, the pull request shows "Refs #1" in its body, linking the two. The command options (`--title`, `--body-file`, `--repo`, `--enable-issues`, `--clone=false`) were read in GitHub's CLI manual on 2026-10-22 and not run; if `gh repo fork` or Issues behave differently on your account, the Settings page of your fork has the same switches. Replace the issue number in `change.md` with the one you got. If you have a GitHub Project, add both items to its board and move them between columns: that is the whole of a free ticket tracker.

**Undo.**

```bash
gh pr close 1 --repo YOUR-USER/Clouds-Against-Humanity --delete-branch   # use your pull request number
gh issue close 1 --repo YOUR-USER/Clouds-Against-Humanity --reason "not planned"
cd .. && rm -r f12-practice ticket.md change.md
```

```powershell
gh pr close 1 --repo YOUR-USER/Clouds-Against-Humanity --delete-branch
gh issue close 1 --repo YOUR-USER/Clouds-Against-Humanity --reason "not planned"
Set-Location ..; Remove-Item -Recurse f12-practice; Remove-Item ticket.md, change.md
```

(Use your own issue and pull request numbers. Deleting the fork itself is a button in its Settings.)

### Exercise 5: read an unfamiliar environment, read-only

**Predict.** Using only files and the pull request list, can you find out who owns this repository, how a change lands, where the runbooks are and what stops an expensive change, in ten minutes?

**Do (Bash).** In a clone of the public repository (or your fork):

```bash
gh pr list --repo ChiefGyk3D/Clouds-Against-Humanity --state merged --limit 5
ls docs/stages
ls tests | head -20
sed -n 1,12p docs/wiki/How-This-Project-Is-Planned.md
```

**Do (PowerShell, est.).**

```powershell
gh pr list --repo ChiefGyk3D/Clouds-Against-Humanity --state merged --limit 5
Get-ChildItem docs\stages
Get-ChildItem tests | Select-Object -First 20
Get-Content docs\wiki\How-This-Project-Is-Planned.md -TotalCount 12
```

**Check.** Merged pull requests show how a change lands (a branch, a pull request, checks, a merge). `docs/stages` holds the runbooks. The planning page says who decides. The tests folder shows what stops a bad change; the cost gate is one of them. If you could answer in ten minutes, you can do the same on Monday in a new job with the team's wiki.

**Undo.** Nothing; these are reads.

## Build it, break it, detect it, evade it, defend it

The same loop as the [labs](Labs-Break-It-on-Purpose.md), translated into process. Everything is local text files and a small script. Nothing touches a real system.

**Build.** A change record for a one-line firewall edit, in the "Key: value" form below. The address and port are invented. The script is the **reviewer checklist**: it fails when a required field is empty.

```bash
mkdir -p f12-loop/records && cd f12-loop
cat > check_change.sh <<'EOF'
#!/usr/bin/env bash
# Reviewer checklist for a change record: "Key: value" lines.
set -u
file="${1:?usage: check_change.sh RECORD}"
problems=0
need() {
  local value
  value=$(grep -m1 -i "^$1:" "$file" | cut -d: -f2- | sed 's/^ *//')
  if [ -z "$value" ]; then
    echo "MISSING: $1"
    problems=$((problems + 1))
  fi
}
for key in Title Type Reason "Systems affected" Risk "Test evidence" Rollback Approver; do
  need "$key"
done
if grep -qi '^Type: *emergency' "$file"; then
  need Incident
  need "Review within"
fi
if [ "$problems" -eq 0 ]; then echo "OK: $file"; fi
[ "$problems" -eq 0 ]
EOF
chmod +x check_change.sh
cat > records/chg-001.txt <<'EOF'
Title: Allow TCP 8443 from 198.51.100.0/24 to the reporting server 192.0.2.10
Type: normal
Reason: The finance team's reporting tool moved to port 8443.
Systems affected: Firewall rule set "reporting", server 192.0.2.10 (fictional)
Risk: Low. One source range, one port, one destination.
Test evidence: Rule applied in the test firewall; a test connection from 198.51.100.7 succeeded.
Rollback: Delete the rule by its name, "reporting-8443"; confirm the connection now fails.
Approver: Network owner (a different person from the requester)
EOF
./check_change.sh records/chg-001.txt; echo "exit=$?"
```

```powershell
# est.: not run
New-Item -ItemType Directory -Force f12-loop\records | Out-Null; Set-Location f12-loop
@'
param([Parameter(Mandatory)][string]$File)
$problems = 0
function Get-Field($name) {
  $line = Select-String -Path $File -Pattern "^$([regex]::Escape($name)):" | Select-Object -First 1
  if ($line) { ($line.Line -split ':', 2)[1].Trim() } else { '' }
}
$keys = 'Title','Type','Reason','Systems affected','Risk','Test evidence','Rollback','Approver'
if ((Get-Field 'Type') -eq 'emergency') { $keys += 'Incident','Review within' }
foreach ($k in $keys) { if (-not (Get-Field $k)) { "MISSING: $k"; $problems++ } }
if ($problems -eq 0) { "OK: $File" }
exit ([int]($problems -ne 0))
'@ | Set-Content check_change.ps1
@'
Title: Allow TCP 8443 from 198.51.100.0/24 to the reporting server 192.0.2.10
Type: normal
Reason: The finance team's reporting tool moved to port 8443.
Systems affected: Firewall rule set "reporting", server 192.0.2.10 (fictional)
Risk: Low. One source range, one port, one destination.
Test evidence: Rule applied in the test firewall; a test connection from 198.51.100.7 succeeded.
Rollback: Delete the rule by its name, "reporting-8443"; confirm the connection now fails.
Approver: Network owner (a different person from the requester)
'@ | Set-Content records\chg-001.txt
.\check_change.ps1 records\chg-001.txt; "exit=$LASTEXITCODE"
```

On 2026-10-22 the Bash version printed `OK: records/chg-001.txt` and `exit=0`.

**Break.** Submit the same change with **no rollback plan**:

```bash
grep -v '^Rollback' records/chg-001.txt > records/chg-002.txt
```

```powershell
Get-Content records\chg-001.txt | Where-Object { $_ -notmatch '^Rollback' } | Set-Content records\chg-002.txt
```

**Detect.** Run the checklist on the broken record. The reviewer script is what catches it.

```bash
./check_change.sh records/chg-002.txt; echo "exit=$?"
```

```powershell
.\check_change.ps1 records\chg-002.txt; "exit=$LASTEXITCODE"
```

On 2026-10-22 the Bash run printed `MISSING: Rollback` and `exit=1`. A human reviewer with the template in front of them catches the same thing, which is the point of a template: the missing field is visible because there is a slot for it.

**Evade.** Words only; nothing here touches another system. There are two ways the check gets bypassed, and both are common in real companies.

- *Calling it an emergency.* The emergency path is faster, so a change that would be refused as normal is labeled "emergency" to skip the wait for review. The record is written afterward, or not at all. The warning sign is a rising count of emergencies, especially ones with no incident number, no named approver and no later review. Check it yourself: copy the record, change `Type: normal` to `Type: emergency`, and run the checker. On 2026-10-22 it printed `MISSING: Incident` and `MISSING: Review within`, because the script demands those two extra fields for an emergency.
- *Filling the form without the truth.* Type `Incident: later` and `Review within: n/a` and the script is satisfied. A form check proves that fields exist, not that they are true. That limit is why the controls below involve people and numbers, not only forms.

**Defend.** Controls that address both, in rising order of cost:

- **A retro-approval rule:** every emergency change gets a named approver at the time, and a review within a stated number of working days (many companies use one to three; est.). An emergency with no review by the deadline is itself reported.
- **Count them.** Emergency changes per month, and as a share of all changes. In the folder above, `grep -il '^Type: *emergency' records/*.txt | wc -l` counts them (PowerShell, est.: `(Select-String -Path records\*.txt -Pattern '^Type: *emergency' | Select-Object -Unique Path).Count`). A team that sees its count rising asks why: missing tooling, a slow normal path or a shortcut habit.
- **An incident number is required for emergency**, and it must exist in the ticket system. Someone other than the requester checks that it does.
- **Separation of duties:** the approver is not the author. Where a pull request is required, branch protection makes it a tool rule rather than a promise (see [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) and the Glossary entry for branch protection).
- **Make the normal path fast enough** that nobody needs the shortcut, and define **standard** changes for the repeatable ones. A process that is slow for everything teaches people to bypass it.

**Flip the board.** You are now an **auditor** sampling twenty changes from last quarter. What three questions do you ask of each record to tell a real emergency from a relabeled normal change? Which evidence would you ask to see that cannot be written after the fact? (A timestamped page or alert, a chat log, the approver's own message.) Then flip again: you are the engineer under pressure at 02:10 with no approver answering. What do you write down as you act so that the review is short and fair? Write both answers in a few lines.

## Common mistakes

- **A title that says nothing.** "Issue", "Help" and "Urgent" are not titles. Put the verb, the thing and the place.
- **Putting a secret in a ticket or a chat.** Treat it as leaked and replace it.
- **A rollback of "revert".** Revert what, how, and who decides? Name the trigger and the steps. Say so if there is no real rollback.
- **Calling a normal change standard** because it is small. Standard needs a written, pre-approved procedure.
- **Marking everything urgent.** Priority is the triager's call; give the impact and let it be set.
- **Writing a post-mortem that blames a person.** Rewrite each "should have" as "the system allowed".
- **Asking for "admin" with no end date.** Ask for the narrowest role and a date.
- **Treating "I can" as "I may".** If you are not sure, ask first.

## Checkpoint

You are done when you can say, without looking:

- The six things a good ticket contains, and why a ticket never holds a secret.
- The difference between severity and priority, with one case where they disagree.
- How to tell a standard, a normal and an emergency change apart, and why almost everything is normal.
- What belongs in a rollback plan, and what to write when something cannot be fully undone.
- Why a post-mortem names causes in the system, not a person.
- What an access request must say, and why two different people approve it.
- The difference between "I can" and "I may".

## Claims register

All pages were retrieved read-only on **2026-10-22**. Pull request facts come from `gh pr view` on this repository on the same date.

| Claim | Source | Status |
|---|---|---|
| Severity is a measurement of impact; priority is a measurement of urgency; they can disagree (the examples in the table are paraphrased in the author's words) | [Atlassian, understanding incident severity levels](https://www.atlassian.com/incident-management/kpis/severity-levels) | Read |
| A blameless postmortem identifies contributing causes without indicting any individual or team, and assumes everyone involved had good intentions | [Google SRE book, Postmortem Culture](https://sre.google/sre-book/postmortem-culture/) | Read |
| `gh issue create` takes `--title`, `--body-file`, `--label`, `--repo`; `gh repo edit` takes `--enable-issues` | [GitHub CLI manual: gh issue create](https://cli.github.com/manual/gh_issue_create), [gh repo edit](https://cli.github.com/manual/gh_repo_edit) | Option names read; not run against a real fork |
| `gh pr view`, `gh pr create`, `gh pr close --delete-branch` options | [GitHub CLI manual](https://cli.github.com/manual/gh_pr_view) | `pr view` read and run against this public repository; `pr create` and `pr close` not run (est.) |
| GitHub Free: unlimited collaborators on unlimited public repositories | [GitHub plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans) | Read; an explicit line for Issues was not found on that page: **est.** |
| GitHub Projects is "a table, board, and roadmap that integrates with your issues and pull requests" | [About Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects) | Read; its price on a free plan was not read: **est.** | <!-- identifier-check: ignore -->
| The ten worked examples (#8, #136, #139, #140, #141, #142, #143, #147, #163, #173): sizes, descriptions, "not verified" statements and rollback limits | `gh pr view` on this repository | Read; the type and risk classifications are the author's teaching reading and were **not approved by any process** |
| Forks may start with Issues turned off; many teams ask for help after 15 to 30 minutes; review within one to three working days for emergencies; access reviews and on-call practices vary | General practice | **est.** |
| Unauthorized access can be a legal problem as well as a policy one | General knowledge, not legal advice | **est.** |
| The Bash reviewer script and the record counter | Run on Linux on 2026-10-22 | Run once; PowerShell versions **not run** |
| The post-mortem, the handover note, the runbook example and the emergency change story | Invented for teaching | **Fictional**; no real incident, person or system |

Next: [Architecture overview](Architecture-Overview.md), or back to [Enterprise engineering habits](Enterprise-Engineering-Habits.md) and the [Reading order](Reading-Order.md).
