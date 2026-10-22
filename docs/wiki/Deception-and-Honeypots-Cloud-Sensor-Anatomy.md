# Anatomy of a cloud honeypot: what you are agreeing to

Lesson 7 of the [deception and honeypots track](Deception-and-Honeypots-Start-Here.md), and the first lesson of **track 2**, a small honeypot that strangers on the internet can reach, run in **your own** cloud account. A foundations side page to [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) and [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md). This page is reading plus a paper exercise: it builds nothing. Next: [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md), lesson 8.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from reading, nothing built, nothing run.** On **2026-10-22** the author read the pages listed in the [claims register](#claims-register) with read-only `curl` and ran nothing against a cloud provider. No honeypot was started for this lesson. The PowerShell command is **est.** (not run). The provider pages change; the register gives the date each was read.

> **Prerequisites.** [What deception is](Deception-and-Honeypots-What-Deception-Is.md) (lessons 1 and 2) and [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) (lesson 6, which you should have finished with a reviewer's answer). [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) helps. About 1.5 hours (est.). Cost: none. This lesson is the free theory path of track 2. The hands-on lessons that follow use **your own cloud account and your own provider bill**, and this page shows the figure before you decide.

## What you will be able to do

- Say what a medium-interaction honeypot is, and what [Cowrie](Glossary.md) does and does not do.
- Draw the path from the internet to the sensor's log file, and name the control that sits at each step.
- Give the reason for each of the guardrails a cloud sensor needs: its own account, a separate management path that only your address can reach, exposed lure ports, nothing real on the box, no route to your other things, closed outgoing traffic, logs pulled out, a teardown written first and a spend limit.
- Read a provider's acceptable-use policy for the clause that decides whether you may run a honeypot at all, and quote it.
- Say what the cost is, what is **not** a spending cap, and what is.

## The free theory path

Everything on this page is reading. If you stop here you have the whole idea and have spent nothing. Lesson 8 builds it; lesson 9 reads what arrives and works in two parts, one of which needs no cloud account.

## What a cloud sensor is

A **honeypot** is a system whose only job is to be attacked and to record how. **Cowrie** is one: an imitation of an SSH server (and, if you switch it on, a telnet server). A visitor connects, tries passwords, and, if the imitation accepts a login, gets what looks like a Linux command line. It is not a Linux command line. It is a program written in Python that answers like one, keeps a fake file system, and writes down everything the visitor types. The project's own README calls it a "medium to high interaction SSH and Telnet honeypot designed to log brute force attacks and the shell interaction performed by the attacker", and says its default shell mode "emulates a UNIX system in Python". The word **medium** matters: the visitor never gets a real shell on your machine, but the imitation talks back, so it records far more than a program that only counts connections. (Interaction levels are in [What deception is](Deception-and-Honeypots-What-Deception-Is.md#the-vocabulary).)

Cowrie also has a proxy mode and an experimental mode that sends visitor input to a language model. This track uses neither. The proxy mode relays a visitor to another machine, which makes your sensor a source of connections to someone else. The model mode sends visitor-controlled text to a third party. Both are out.

Here is the whole path, from the internet to a file you read:

```text
internet --> provider's cloud firewall --> the host's own firewall --> redirect 22 -> 2222 --> Cowrie
 (anyone)    allows only:                  drops the same way          (a rule, as root)       (runs as an unprivileged user,
             - 22 and 23 from anyone       and drops all outgoing                               writes cowrie.json)
             - the management port from
               your address only                                                     you pull the logs over the management port
             - no outgoing at all (run phase)                                        (an outbound connection from you, not from it)
```

Two things about that picture. First, **the sensor does not call out**. You come to it. The firewall is *stateful* (it lets replies to an allowed connection through, see [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md)), so your own connection in works without any outgoing rule. Second, there is a deliberate gap in the picture: the real SSH server you use to administer the machine is on a **different port**, because Cowrie takes port 22.

## The guardrails

Each row is a control with a reason and a way to check it. Lesson 8 builds every one of them; this table is what you will review in the exercise.

| # | Guardrail | Why | How you check it |
|---|---|---|---|
| 1 | **An account of its own**, holding nothing else, with its own payment method. | A provider acts on an account. A honeypot is built to draw complaints, and a suspension should land somewhere that holds nothing you need. The [honeypot design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md) (section 3) says why a separate team or project in your main account is not enough. | The account's resource list shows the sensor, its firewall and nothing else. |
| 2 | **A separate management path**: real SSH on a port other than 22 (for function: the imitation needs 22), reachable **only from your own address** at the cloud firewall and again on the host, key-only, no passwords, no root login. | Port 22 now belongs to the imitation, so the operator needs another way in. **The new port number is not a protection**: anyone who scans finds it. What protects the door is the firewall allowing only your address, key-only login, no passwords, patching by rebuild, and logs you read. If real SSH were open to everyone, the first password-guesser would be guessing against your real door whatever its port. | From a machine that is not yours, the management port does not answer. From yours, it does. |
| 3 | **Only the lure ports are open to everyone**: 22 and, if you chose it, 23. | A honeypot is exposed on purpose; nothing else should be. | The firewall lists exactly the rows in the table in lesson 8. |
| 4 | **Nothing real on the box.** No real files, keys, tokens, passwords or accounts, and no key that opens anything else. | The sensor will be attacked, and a clever visitor may get past the imitation. Whatever is on it is lost. | Read the machine's files and its user-data once, before exposing it. |
| 5 | **No route to anything else of yours.** No peering, no tunnel, no VPN client, no Twingate connector or client on the box, no stored key for another machine. | A taken-over sensor with a path home is a way in. Twingate is how this project reaches private things; the sensor must have none of that. | The account has no other resources; the box has no software that joins a private network. |
| 6 | **Outgoing traffic closed.** Once it is built, no outgoing rules at all, at the cloud firewall **and** on the host. | A sensor that can call out can be used to attack others, and the abuse report goes to you. Cowrie's own `wget` and `curl` imitations make real outgoing connections unless the network stops them (see the [register](#claims-register)). | From the box, an outgoing connection to a test target of yours fails. |
| 7 | **Logs pulled out by you**, over the management port. | A push needs outgoing access, which guardrail 6 removed. A pull needs none. | You can copy the log file out; the sensor holds no key to anything. |
| 8 | **Teardown written first**: an end date, the exact commands, and a check that nothing keeps billing. | Temporary experiments become permanent bills and permanent hazards when nobody remembers them. | The commands are in your plan before you create anything. |
| 9 | **A spend limit** you enforce, because the provider does not. | See [the cost section](#what-it-costs-and-what-is-not-a-cap) below. | The usage page matches your arithmetic after day one. |

Guardrail 7 deviates from the design on purpose. The design shows a log store the sensor writes to and you read from, and it flags that a "write to one storage service" rule still lets a taken-over box reach every other customer's bucket behind the same address (design section 6.2.1). A pull needs no outgoing hole at all, so this lesson uses the pull. The log-store route is described in the design and is **not** covered here.

## Read the provider's rules first

This is the step people skip, and it is the one that decides whether you may run a honeypot at all.

On **2026-10-22** the author read the DigitalOcean [Acceptable Use Policy](https://www.digitalocean.com/legal/acceptable-use-policy) (page text "Last Updated on March 20, 2026"). Three findings:

- **The page does not mention honeypots.** A text search of the fetched page for "honeypot" found nothing. So the policy neither allows nor forbids one by name. The permission has to be asked for.
- **Its "Vulnerability Testing" clause is the one to read.** It says you may not "conduct any security or malware research on or using the Services, without DigitalOcean's prior written consent." A honeypot that records attacker commands and file names is plausibly "security or malware research" done on the service. Whether yours counts is the provider's decision, not yours and not this page's.
- **"Network Abuse" is why outgoing traffic is closed.** It says you may not "make network connections to any users, hosts, or networks unless you have permission to communicate with them." A sensor that fetches whatever a visitor tells it to fetch makes exactly those connections.

Two more clauses to note. "Operation of Certain Network Services" lists "open proxies", and Cowrie can be set to forward a visitor's connections onward (the lesson leaves that off). And the consequences clause says the provider may suspend or end your use, and that this "applies even if a violation is committed unintentionally or without your authorization", which is the case where a taken-over sensor attacks someone.

What to do about it: **ask in writing before you create anything.** Describe the exercise in plain words: a passive SSH and telnet imitation (Cowrie's medium-interaction mode) that records what visitors type and the files they try to send, one small server in a separate account, outgoing traffic closed, a stated end date, a named contact who reads the abuse inbox. Keep the answer. Do not read the policy's silence as permission. The design has the same finding for AWS and a pointer to its pages (design section 7.4); this track's hands-on lesson uses DigitalOcean, and if you use another provider you do this reading again for it.

Also read your **own** contract and laws. Nothing on this page is legal advice, and the author read no statute. Recording the visitors, keeping their addresses and the passwords they type, and publishing any of it are questions about where you live. The lesson 6 [minimums](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums) cover what to do while you find out: keep raw logs private, publish counts, never look back at an address.

## What it costs, and what is not a cap

Prices below are read from this repository's price files, never from memory. The file [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json) (retrieved 2026-10-21) lists the `s-1vcpu-1gb` droplet at **$6 a month**, and [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) lists a $5 a month log bucket. This track does not use a bucket, so **the figure for this lesson set is the $6 droplet**. The design's option with the bucket is $11.

How a short run costs less than $6: DigitalOcean's Droplet pricing page (read 2026-10-22) says a droplet on a bundled plan is "billed per second with a minimum charge of 60 seconds or $0.01, whichever is higher", with usage "capped at 672 hours (28 days) per month". So $6 is the most one such droplet can cost in a month, and a weekend of 48 hours is about 48 / 672 of it: **$0.43 (est.)**, my arithmetic from those two numbers, not a quote. These things are not in that figure: a public address charge (the page says addresses for the newer "v5" droplet configurations are billed separately at an introductory $0.00, and this plan is not one of them, but check your own invoice), outgoing data past the plan's allowance ($0.01 per GiB, from the Bandwidth page; inbound is free; and that page says outgoing traffic "dropped by a DigitalOcean firewall rule" is not billed), and anything you add later.

Now the part that matters. **A spending alert is not a spending cap.** The Spend Alerts page (read 2026-10-22) says so: "A spend alert budget is not a spending cap and does not limit how much you can use". The only pause it offers is for a different product, not for droplets. Nothing in the pages the author read lets you tell DigitalOcean to stop a droplet at a dollar amount. So the limit is yours to enforce, in layers:

1. **One droplet, one size, no extras.** No backups, snapshots, volumes or reserved addresses, so there is nothing else to bill. The most it can cost in a month is its $6.
2. **An end date and a destroy command written first.** The destroy page says billing "ends when you destroy it"; a powered-off droplet is still billed because its resources stay reserved.
3. **A spend alert** with a monthly budget a little above the $6 figure and thresholds you choose, as a warning only.
4. **A calendar alarm** on the end date and one daily check of the billing page while it runs.
5. **A payment method with its own limit**, if your bank offers one (est.; not checked against DigitalOcean).

If you cannot do all five, do not start.

## What arrives, from a public dataset

You do not have to guess what a sensor sees. Two public sources, both read on 2026-10-22:

- **The SANS Internet Storm Center** runs a network of Cowrie-based honeypots and publishes a live page of the most-tried names. On the day it was read, the most-tried usernames were `root`, `admin`, `user`, `super` and `support`, and the most-tried passwords included `1234`, `123456`, `admin` and `password` (one row had no password text on the page, which may mean an empty password). That is one day's page, not a study: it changes daily, and it says nothing about how many sensors feed it.
- **A published analysis of about three years of Cowrie data** from six of those sensors (ISC diary, 2026-03-30; 1,206,566 sessions between 2022-04-13 and 2026-03-21) found that most sessions were bots running a fixed script. Sessions with exactly 22 commands were 38.26 percent of all sessions, those with 20 commands 28.91 percent, and those with a single command 8.64 percent. For the 22-command sessions, 461,344 of 461,561 included the prompt "Enter new UNIX password:", which the author takes to mean the script changes the account password, probably to lock other bots out. The same diary notes that a long session does not prove a person was typing.

What that means for you: expect mostly automated visitors, repeating a short script, and expect a login attempt within hours rather than days if the ISC's own FAQ is a guide (it says even a home connection "will likely see several attacks a day"; that is a claim about a home sensor, not a measurement of yours). Lesson 8 asks you to measure your own time to the first attempt and write it down.

## Exercise: review the plan on paper

**Predict.** Before you read anything else: which of the nine guardrails do you think a first-time builder is most likely to get wrong? Write it down. (The author's guess is the management path: giving real SSH a different port and locking it to one address is the step where people lock themselves out.)

**Do.**

1. Open the DigitalOcean acceptable-use policy and search it for the two phrases below. In Bash:

   ```bash
   curl -sL https://www.digitalocean.com/legal/acceptable-use-policy -o aup.html
   grep -c -i 'honeypot' aup.html
   grep -o -i 'security or malware research' aup.html
   ```

   In PowerShell (**est.**):

   ```powershell
   Invoke-WebRequest https://www.digitalocean.com/legal/acceptable-use-policy -OutFile aup.html
   (Select-String -Path aup.html -Pattern 'honeypot' -SimpleMatch).Count
   Select-String -Path aup.html -Pattern 'security or malware research' -SimpleMatch | Select-Object -First 1
   ```

2. Copy the guardrails table into your own notes. For each row, write the **one command or screen** you will use to prove it, and the date you will check it. Leave the rows you cannot answer blank.
3. Write your end date, your teardown commands and your spend limit (all five layers) on one page.

**Check.** The first count is `0` (if it is not, the policy changed since 2026-10-22: read the new text). The second prints the phrase (it may print twice), which is the clause above. Your page has no blank row. A reviewer who reads it should be able to say what is exposed, to whom, until when, and what happens if you forget.

**Undo.** `rm -f aup.html` (PowerShell: `Remove-Item aup.html`). Nothing else was created.

## Build, break, detect, evade, defend (on paper)

- **Build.** The nine-guardrail plan and the written request to the provider.
- **Break.** Read your plan as the visitor who gets past the imitation. What can they reach from the box? What is on it? Where would a stored key lead? If any answer is "something of mine", a guardrail has a hole.
- **Detect.** What would tell you it has gone wrong: a message from the provider, a spend alert, an outgoing connection from a box that should have none, a login to the management port you did not make. For each, say where you would see it and who looks.
- **Evade.** A visitor who suspects an imitation can test it, and a determined one can leave you a path of its own: look for other machines, try your account's credentials, try to send mail or attack others from your address. Each is a reason for a guardrail. Lesson 9 covers how visitors tell it is Cowrie.
- **Defend.** The nine guardrails, as controls, each with a check.
- **Flip the board.** You are now the provider's abuse team, reading a complaint that a droplet in your network is "attacking" someone. All you can see is the customer's reply. What would you want that reply to say, and how would it differ from a customer who is actually running an attack? Write the reply you would want to be able to send.

## Common mistakes

| Mistake | Why it hurts | Better |
|---|---|---|
| Asking for forgiveness instead of consent. | The policy's own wording makes written consent a requirement, and a strike lingers. | Ask first, in writing, and keep the answer. |
| Treating a spend alert as a limit. | The provider says it is not one. | Enforce the five layers yourself. |
| Putting the sensor in your main account "because it is only a weekend". | A suspension takes everything in that account with it. | A separate account, with its own payment method. |
| Leaving outgoing traffic open "just for updates". | That is how a taken-over sensor attacks others. | Open it only while you build; close it before you expose anything. |
| Copying a tutorial's port 22 redirect before real SSH has another way in. | You lock yourself out, or you expose your real door. | Set up and test the separate management path first (lesson 8 does it in order). A different port number is for function, not protection: the firewall rule and the key are the protection. |

## Claims register

Retrieved 2026-10-22 unless stated.

| Claim | Source | Status |
|---|---|---|
| Cowrie is a "medium to high interaction SSH and Telnet honeypot designed to log brute force attacks and the shell interaction performed by the attacker"; shell mode emulates a UNIX system in Python; proxy and experimental language-model modes exist | [Cowrie README](https://raw.githubusercontent.com/cowrie/cowrie/HEAD/README.rst) | Read |
| Cowrie 3.1.3 is the latest release (published 2026-10-19) and requires Python 3.11 or newer | [GitHub release v3.1.3](https://github.com/cowrie/cowrie/releases/tag/v3.1.3), [PyPI metadata](https://pypi.org/pypi/cowrie/json) | Read |
| The `wget`, `curl`, `nc`, `ftpget` and `tftp` imitations make outgoing connections and have a rate limit; `out_addr` sets the address they bind to | [Cowrie default configuration](https://raw.githubusercontent.com/cowrie/cowrie/HEAD/src/cowrie/data/etc/cowrie.cfg.dist) | Read. That a closed network stops them is **est.**: not run |
| DigitalOcean's AUP: no mention of honeypots; the "Vulnerability Testing", "Network Abuse", "Operation of Certain Network Services" and suspension wording quoted above; page dated March 20, 2026 | [DigitalOcean Acceptable Use Policy](https://www.digitalocean.com/legal/acceptable-use-policy) | Read. Whether a student lab counts as "security research" is the provider's call |
| A bundled-plan droplet is billed per second (60 second or $0.01 minimum), capped at 672 hours a month; billing ends on destroy; a powered-off droplet is still billed | [Droplet Pricing](https://docs.digitalocean.com/products/droplets/details/pricing/) (page "Last verified 25 Aug 2026") | Read |
| Spend alerts "send email notifications" and are "not a spending cap" | [Spend Alerts](https://docs.digitalocean.com/platform/billing/spend-alerts/) ("Last verified 19 Oct 2026") | Read |
| Outgoing traffic past the allowance is $0.01 per GiB; inbound is free; traffic "dropped by a DigitalOcean firewall rule" is not billed | [Bandwidth Billing](https://docs.digitalocean.com/platform/billing/bandwidth/) | Read |
| $6 a month for `s-1vcpu-1gb`; $5 a month for a log bucket | `docs/cost-prices.json` (retrieved 2026-10-21) and `docs/cost.md` | Read in this repository. Prices change; check before you rely on them |
| About 48 / 672 of $6 for a weekend, $0.43 | Arithmetic on the two cited numbers | **est.** |
| Top usernames and passwords on the ISC's page on the day read | [SANS ISC SSH/Telnet scanning activity](https://isc.sans.edu/data/ssh.html) | Read; one day's snapshot |
| The 1,206,566-session analysis, the 22-command and 20-command shares, 461,344 of 461,561 with a password-change prompt | [ISC diary, "DShield (Cowrie) Honeypot Stats and When Sessions Disconnect"](https://isc.sans.edu/diary/DShield+Cowrie+Honeypot+Stats+and+When+Sessions+Disconnect/32840), 2026-03-30 | Read. One analyst's data from six sensors, not the whole internet. The reading of the password-change prompt is the author's |
| "Even a normal home connection will likely see several attacks a day" | [ISC honeypot page](https://isc.sans.edu/honeypot.html) | Read; the ISC's claim, not a measurement of yours |
| The design's account separation, closed outgoing traffic, provider-policy reading and kill switch | [Honeypot design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md), sections 3, 6, 7.4 and 10 | Read in this repository |

Not verified, plainly: any law; your provider's terms other than DigitalOcean's; whether a payment method with a limit is accepted by DigitalOcean; whether DigitalOcean will give consent; the AWS pages (the design read them on 2026-10-21; this page did not).

Next: [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md), lesson 8, if you have your plan, your consent and your end date. Or back to the [track hub](Deception-and-Honeypots-Start-Here.md).
