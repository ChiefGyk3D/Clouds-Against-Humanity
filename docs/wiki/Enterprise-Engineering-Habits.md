# Enterprise engineering habits

Start-from-zero page 8 of 8. Previous: [How money works in the cloud](How-Money-Works-in-the-Cloud.md). Next: [Architecture overview](Architecture-Overview.md), step 10 of the core path. The capstone, [Fork, private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md), opens the build track and comes after the core path.

Reading this repository for the first time, a reasonable reaction is "this is a lot of ceremony for two $6 machines". Pull requests for a one-person project. A threat model for a hobby. A cost gate for a bill smaller than a streaming subscription. A document about every failure.

That reaction is correct, and the ceremony is the point. These are the habits that professional infrastructure teams use, applied to something small enough that you can see every piece of them at once. Big systems have them because they were learned the expensive way. This page names each habit, says what it is for, and says which ones are worth taking home.

## Everything is code, and code is reviewed

**The habit.** No change to the environment happens outside the repository. Every change is a pull request, with checks and a description, even when the author is the only person who will ever read it.

**What it is for.** Review catches mistakes, but the bigger value is the record. Two years from now, "why does the connector firewall allow UDP on every port?" is answered by the pull request that added it, not by memory. And a change that has to be written down tends to be a change that was thought about.

**At home.** Keep your compose files and configs in a git repository, and write a one-line commit message that says why. That alone puts you ahead of most homelabs.

## Separation of duties: the thing that checks is not the thing that changes

**The habit.** GitHub Actions tests every change and holds no cloud credentials. Spacelift applies changes and is the only thing that holds them. A human stands between the plan and the apply.

**What it is for.** If the testing system is compromised (a malicious action, a bad dependency), it can only block, not destroy. If the applying system gets a bad plan, a human sees it first. In a company this is the difference between a developer and a release manager; here it is the difference between two services.

**At home.** When a script can both check something and change it, split it. Your backup verification should not be able to delete backups.

## Least privilege, at every layer

**The habit.** Each token does the minimum: the Doppler token reads one environment and cannot write; the stage 0 run gets only the DigitalOcean token; a Twingate resource grants one host and one port; the CI workflow starts with no permissions and adds them per job.

**What it is for.** A compromise is bounded by what the compromised thing could do. Attackers chain small permissions into big ones; narrow permissions give them less to chain.

**At home.** Make a read-only API token for the dashboard that only reads. Give the backup user access to the backup folder and nothing else. It is slightly more work once and much less worry forever.

## Default deny, and attach protection before the thing exists

**The habit.** The firewall has zero inbound rules and is attached by tag at the moment a droplet is created, so there is no window where the machine is open. Anything not explicitly allowed is dropped.

**What it is for.** "Allow what you need" fails safe: forget a rule and something does not work. "Block what you do not want" fails open: forget a rule and something is exposed. Only one of those failures is survivable.

**At home.** Your router already does this for inbound traffic. Do it for the things on your LAN too: a Pi that runs one service should not have five other ports listening.

## Write the threat model down, including what you accept

**The habit.** The [Threat model](Threat-Model.md) lists what is worth protecting, who might come for it, what stops them, and what is **not** stopped and has been accepted on purpose, with a reason.

**What it is for.** Security is a set of trade-offs, and an unwritten trade-off is indistinguishable from an oversight. Writing "the connector tokens are readable from the metadata endpoint and we accept that for now because X" is honest, reviewable, and gives future-you a list of things to fix. Pretending the environment is perfect helps nobody.

**At home.** Write down the three worst things that could happen to your homelab and what currently stops each. If the answer for one is "nothing", you have found your next weekend.

## Stage gates: small steps, each approved and costed

**The habit.** The environment grows in numbered stages. Each has a design, a cost, an approval and an operator guide before it exists. Stage 1 did not start until stage 0 was built and verified.

**What it is for.** Small changes are easy to review, easy to test and cheap to undo. A failure on a new cloud account (and there were several; see [Lessons learned, "A rebuilt account"](Lessons-Learned.md#9-a-rebuilt-account-nothing-you-assumed-is-still-true)) is found at stage 0, where nothing bills, instead of at stage 3 with six services running.

**At home.** Change one thing, check it works, then change the next. Everyone knows this and nobody does it at 11pm.

## Runbooks: how to operate it, written before you need to

**The habit.** Each stage has a guide in `docs/stages/` with bootstrap steps, how to verify it worked, what to do when it does not, how to rotate every secret, and how to tear it down.

**What it is for.** The person reading the runbook is tired, something is broken, and they may not be the person who built it. A runbook turns "I think I remember" into "step 4". Rotation steps written in calm times are the only reason rotation happens at all.

**At home.** Write down how to rebuild your most important box from nothing. Then try it on a spare SD card. The gaps in the document are the gaps in your backups.

## Post-mortems without blame

**The habit.** [Lessons learned](Lessons-Learned.md) records every failure: the symptom, what was really going on, the fix, and the general lesson. It does not record whose fault it was, because the answer is always "the system let it happen".

**What it is for.** A failure that is written up once saves every future reader the evening it cost. A culture where failures are hidden is a culture where they repeat.

**At home.** When something breaks and you fix it at 2am, write three lines in a `LESSONS.md` before you go to bed. Future you will not remember otherwise.

## Verify, then write down that you verified

**The habit.** The wiki says "masking was checked on the first real run", "backup pricing confirmed on 2026-10-11", "the install only counts as a success if the service is active". Claims come with how and when they were checked.

**What it is for.** "It should work" and "I watched it work" are different kinds of knowledge, and documentation that does not distinguish them is a trap for the next reader. The dated vendor facts also age gracefully: a reader in 2028 knows exactly which claims to re-check.

**At home.** When you set something up from a tutorial, do the one check that proves it works, not just the one that proves the command ran. Then note the date.

## Default to the boring, open, replaceable choice

**The habit.** OpenTofu over Terraform for the license. DigitalOcean over AWS for the one-page price list. Twingate because it mirrors how real organisations do access, with the self-hosted alternatives named for anyone who does not want the vendor dependency. Nothing exotic, nothing you could not swap.

**What it is for.** A teaching repository, and most production systems, are better served by tools whose failure modes are well known than by clever ones. Every vendor dependency is listed as a trust decision, which makes replacing one a known amount of work rather than a surprise.

**At home.** Before adopting a tool, ask what it would take to leave it. If the answer is "rewrite everything", keep looking or go in with your eyes open.

## Which of these matter most for a homelab

If you only take three:

1. **Put your configs in git** with messages that say why.
2. **Default deny.** Nothing listens that does not need to; nothing is reachable from outside that is not meant to be public.
3. **Write down how to rebuild it.** Then test the document.

Everything else on this page is those three, applied with more people and more money at stake.

## Where to go next

You now have the vocabulary the rest of the wiki assumes. Continue with the core path on the [Reading order](Reading-Order.md) page. The [Architecture overview](Architecture-Overview.md) will read as a description of things you understand, and [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) will read as an argument you can evaluate rather than a position you are asked to accept. When a word does not land, the [Glossary](Glossary.md) is there. When you find a page that still assumes too much, that is a pull request waiting to happen, and [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) says how.

Next: [Architecture overview](Architecture-Overview.md).
