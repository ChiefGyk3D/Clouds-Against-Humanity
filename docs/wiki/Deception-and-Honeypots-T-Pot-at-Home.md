# T-Pot at home: an internal-only honeynet on your own hardware

Lesson 11 of the [deception and honeypots track](Deception-and-Honeypots-Start-Here.md), track 3, the path for **your own hardware or home lab**. A foundations side page to [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md), which you finish first. This page covers T-Pot, a free all-in-one honeypot bundle: what it is, what it listens on, what it sends to others by default and how to stop that, how to install it on the isolated segment you designed, what to do when it alerts, and how to take it down. Next: back to the [track hub](Deception-and-Honeypots-Start-Here.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from reading. T-Pot was not installed, run or tested, and nothing here is verified on a running system.** On **2026-10-22** the author read T-Pot's README (the default branch and the 24.04.1 tag) and the project's GitHub API pages with read-only requests, and ran nothing from them. Every command that touches T-Pot, a firewall or your network is marked **est.** and is a draft for you to confirm against the README of the release you choose. The README is long, changes between releases and is the real authority; this page is a guide to reading it safely. Not legal advice. The [claims register](#claims-register) says what was read and what was not.

> **Prerequisites.** [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md) (the isolated segment, the rules and the checker) and [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) (all eight minimums). A Linux terminal and comfort with SSH ([The terminal and your first script](Terminal-and-Your-First-Script.md)). **Your own hardware** that meets the sizes under [Cost and hardware](#cost-and-hardware-read-this-first), or a virtual machine on a computer that does. Time: 2 hours to read and plan, 4 to 8 more to install and tour (est.). Cost: **none for the reading; the hands-on uses your own machine and your own electricity.** Nothing here needs a cloud account.

## What you will be able to do

- Say what T-Pot is, which honeypots and tools it bundles, and which ports it listens on.
- Explain what Elasticsearch, Logstash, Kibana and `ewsposter` do, in a sentence each.
- Find the setting that sends your data to a community project, turn it off, and check that it stayed off.
- Choose a release and read that release's README before you install.
- Install T-Pot on an isolated segment and reach it only through your admin path.
- Cause a few events yourself from your own machine and find them in Kibana.
- Decide what to do when the decoy is touched, and when it was probably you.
- Take it down completely, and check that it is gone.

## What T-Pot is

T-Pot describes itself as "the all in one, optionally distributed, multiarch (amd64, arm64) honeypot plattform, supporting 20+ honeypots". Under the hood it runs each honeypot and tool in its own container (a packaged program with its own files and network view, run by Docker, a container runtime). The project lives under the `telekom-security` organization on GitHub, whose API lists the license as GNU GPL v3, and the bundled honeypots carry their own licenses, which the README lists.

**Two install shapes.** *Standard / Hive* puts everything on one host. *Distributed* is a **Hive** (the main node, with the dashboards) plus one or more **Sensors** (hosts with only honeypots, sending events to the Hive). You want Standard / Hive.

### The honeypots

The README (default branch, read 2026-10-22) names these honeypots: adbhoney, beelzebub, ciscoasa, citrixhoneypot, conpot, cowrie, ddospot, dicompot, dionaea, elasticpot, endlessh, galah, go-pot, glutton, h0neytr4p, hellpot, heralding, honeyaml, honeypots (from qeeqbox), honeytrap, ipphoney, log4pot, mailoney, medpot, miniprint, redishoneypot, rdphoneypot, sentrypeer, snare, tanner and wordpot. It says a selection of them runs, depending on which compose file (the file that tells Docker what to start) you choose, so you will not run all of them at once. Beelzebub and Galah are marked "LLM required": they need an Ollama server (a program that runs a language model) and the README says CPU-only use is "not recommended, not even for testing". For a first run, leave them off.

Most are *low or medium interaction* ([defined here](Deception-and-Honeypots-What-Deception-Is.md#low-medium-and-high-interaction)): they imitate a service enough to log what a visitor tries. A sample of what listens where, from the README's port table:

| Honeypot | What it imitates (est., from its name and project) | Listens on (README) |
|---|---|---|
| Cowrie | An SSH and Telnet server with a fake shell | tcp 22, 23 |
| Dionaea | Windows-style file sharing, databases, FTP and more, to catch malware | tcp 21, 42, 135, 443, 445, 1433, 1723, 1883, 3306, 8081; udp 69 |
| Conpot | Industrial control systems | tcp 80, 102, 502, 1025, 2404, 10001, 44818, 47808, 50100; udp 161, 623 |
| Heralding | Many login prompts, to record credentials | tcp 21, 22, 23, 25, 80, 110, 143, 443, 993, 995, 1080, 5432, 5900 |
| Redishoneypot | A Redis database | tcp 6379 |
| RDPHoneypot | Remote Desktop | tcp 3389 |
| Mailoney | A mail server | tcp 25 |
| Snare / Tanner | A web application trap | tcp 80 |

Several honeypots want the same port (22 is claimed by Cowrie, Beelzebub, Endlessh and Heralding in the table). Which one actually owns it depends on the compose file you run, and the README says its customizer script checks for conflicts. Two more, glutton and honeytrap, "dynamically bind any TCP port that is not occupied by other honeypot daemons", so they answer on ports not listed at all. Plan on a decoy that answers almost everywhere, which is why the segment around it matters.

### The management ports, and why they differ

T-Pot's own doors are separate from the honeypots': **64295** (SSH to the host, instead of 22), **64297** (the web page, behind an nginx reverse proxy that asks for a username and password), and **64294** (sensors sending data to a Hive). These are the ones your [firewall rules](Deception-and-Honeypots-Design-a-Honeynet.md#what-the-rules-look-like) allow only from the admin path.

### The Elastic pieces and `ewsposter`

| Piece | What it does, in one sentence |
|---|---|
| **Logstash** | Receives events from the honeypots and sends them to Elasticsearch. |
| **Elasticsearch** | A database built for searching logs; it stores the events. |
| **Kibana** | The web dashboards that read Elasticsearch. The README says there is "a large variety of dashboards and visualizations all tailored to the T-Pot supported honeypots". Together the three are the **Elastic Stack**. |
| **Elasticvue** | A web page for browsing Elasticsearch directly. |
| **Attack Map** | An animated map of where attacks come from. On an internal-only decoy, every source is a private address, so a map has little to show (est.). |
| **CyberChef, Spiderfoot** | Tools for decoding data and for gathering open-source intelligence about an address. Spiderfoot is an open-source intelligence tool that, as far as I know, looks things up on other services (est.); do not point it at anything you do not own. |
| **Suricata, p0f, Fatt** | Network watchers: an intrusion-detection engine, a passive fingerprinting tool, and a tool that extracts connection fingerprints. |
| **`ewsposter`** | A service that sends your captured data to a community backend. See the next section. |

## Your data goes to a community project by default

This is the thing to know before the first start. The README's disclaimer says: "By default, your data is submitted to Sicherheitstacho" (a community threat-sharing site that the README says the community backend feeds). The service doing it is `ewsposter`. For you this is a decision, not a default to accept: on an internal-only decoy, what it would send is addresses and attempts from **your own home network**, which says things about your devices and household. And [minimum 7](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums) says raw logs stay private.

The README's way to opt out (default branch, read 2026-10-22), est. until you do it:

1. Stop T-Pot: `systemctl stop tpot`.
2. Open `~/tpotce/docker-compose.yml` in an editor.
3. Delete the whole block that begins with the comment `# Ewsposter service`, through its `volumes:` lines.
4. Start T-Pot: `systemctl start tpot`.

Four things the README leaves for you to notice:

- **It also says it encourages you not to disable it**, because "sharing is caring". That is the project's view of its community, and a fair one. Your safety minimums are a different list, and you decide.
- **HPFEEDS is a separate opt-in.** It lives in the same `ewsposter` section, set to `EWS_HPFEEDS_ENABLE=false` in the README's text. Deleting the section removes it too.
- **Your closed egress is a second off switch.** The README lists outgoing `80` and `443` as T-Pot's install, update and log path, and names Sicherheitstacho in that line. With the firewall window shut, a submission cannot leave even if the service is still running.
- **Updates can bring it back.** The README says `update.sh` will "mercilessly overwrite local changes to be in sync with the branch the installation follows". Whether it restores the `ewsposter` block is not stated (est.), so **check again after every update**.

The order matters too, and the README does not give it (est.): the installer enables a service that starts T-Pot on boot, so the first boot after install could submit data before you edit the file. Edit the file after the installer finishes and before you reboot, or keep the egress closed through the first boot.

## Cost and hardware (read this first)

**Hardware is yours.** The README's sizes, both in the default branch and in the 24.04.1 tag:

| T-Pot type | RAM | Storage | Note from the README |
|---|---|---|---|
| Hive (main node; also Standard) | 16 GB | 256 GB SSD | "The more honeypots, sensors & data, the more RAM and storage is needed" |
| Sensor | 8 GB | 128 GB SSD | "honeypot logs are persisted (~/tpotce/data) for 30 days, storage depends on attack volume" |

It also needs "an IPv4 address via DHCP or statically assigned" and "a working, non-proxied, internet connection" to install and operate. It runs on real hardware, in a VM (UTM, VirtualBox, VMware and KVM are reported to work), and on a Raspberry Pi 4 (8 GB) with 64-bit Raspberry Pi OS Lite, per the README. In a VM, the README says you may need to enable promiscuous mode on the virtual network interface for Fatt, Suricata and p0f to work. It recommends checking the hardware compatibility list of your chosen operating system before buying anything, and says to get to know T-Pot in a VM before putting it on a network that receives attacks. Its installer asks for a clean system: "never install a graphical desktop environment such as Gnome or KDE", because of port conflicts.

| Item | Your cost |
|---|---|
| A machine meeting the table | $0 if you already own one that is spare. Otherwise unpriced: no prices were read for this page |
| A VM on a computer you already run | $0, but the VM's memory and disk are not available to that computer meanwhile |
| Electricity | Unmeasured. To estimate: watts drawn (read it from a plug-in meter) times hours running, divided by 1,000, times your price per kilowatt-hour. This page gives no figure because it measured none (**est.**) |
| A cloud relay, an internet connection upgrade, a managed switch | Not needed for the internal-only path. A managed switch is needed only if you use a VLAN rather than separate wires |

There is no repository figure for any of this, and nothing here changes this project's budget: [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) covers the cloud environment, which does not run T-Pot.

## Pick a release, and read its README

On 2026-10-22 the project's tags listed **24.04.1** first, published 2024-12-11, and the repository's default branch had been pushed to on 2026-10-21, so the default branch is **ahead of the latest tag**. That matters:

- The two READMEs list **different supported operating systems**. The 24.04.1 README lists Alma 9.5, Debian 12, Fedora 41, openSUSE Tumbleweed, Rocky 9.5 and Ubuntu 24.04.1. The default branch lists newer versions (it names Debian 13, for example). The default-branch README says the installer "will stop on an older one". Pick a system the release you chose supports.
- The default branch documents installer options (`-b` for a branch, tag or commit; `-s -t h` for an unattended Hive) that the 24.04.1 README does not.
- The ports, the management ports, the `ewsposter` opt-out and the 30-day retention read the same in both.

So: **decide on one release, and read that release's README, not this page's summary of it.** I did not install either.

## Install it on the isolated segment

All of this is est.: nothing here was run. Do it in a VM first if you can.

**1. Prepare the segment.** Your [rules](Deception-and-Honeypots-Design-a-Honeynet.md#what-the-rules-look-like) are in place, the checker passes, and [Exercise 4](Deception-and-Honeypots-Design-a-Honeynet.md#exercise-4-optional-prove-the-real-firewall-before-you-install-anything) showed the real firewall blocks what the file says. Give the decoy a fixed address or a DHCP reservation (a router setting that always hands one machine the same address).

**2. Install a minimal operating system** from your chosen release's list, with only SSH as an extra, no desktop.

**3. Open the update window** (the temporary rule from the design page) so the host can reach the web on 80 and 443. The installer will use it.

**4. Read the installer before you run it.** The README's quick start pipes a downloaded script into a shell. Clone and read first instead:

```bash
# est.: not run. Run on the Linux host that will be the decoy, as an ordinary user (not root).
git clone https://github.com/telekom-security/tpotce ~/tpotce
less ~/tpotce/install.sh                 # read it; q to quit
~/tpotce/install.sh                      # or add -b <tag> as the default-branch README describes (see below)
```

The default-branch README says `-b` takes a "branch, tag or commit" for the installer, and that the installer "prints what it settled on before it changes anything": read that line and stop if it is not what you meant. A plain clone without `-b` follows the default branch, which is ahead of the latest tag. Whether the 24.04.1 tag's own installer accepts `-b` was not read.

**5. Know what the installer changes.** The README lists, among others: it **changes the SSH port to 64295**, **disables the DNS stub listener**, sets SELinux (a Linux access-control system) to monitor mode, **sets the firewall target for the public zone to ACCEPT**, installs Docker, and **adds your user to the `docker` group**. Two consequences. First, the host's own firewall is opened up, so **your network firewall is the wall**; this is why the design page tests it first. Second, membership of the `docker` group is effectively root on that machine (est.; widely documented), which is fine on a disposable decoy and a reason never to reuse that account anywhere else.

**6. Opt out of data sharing now**, before rebooting: do steps 2 and 3 of the opt-out (open the file, delete the block) and skip the stop and start, since the reboot comes next.

**7. Close the update window**, reboot (`sudo reboot`), and give it a few minutes to start containers.

**8. Reach it through the admin path only.** From the admin machine: `ssh -p 64295 USER@203.0.113.5` (placeholder address; yours differs) and `https://203.0.113.5:64297` for the web page, with the `WEB_USER` name and password you chose in the installer (the README's "User Types" table separates these from your operating system account). From a Windows machine, PowerShell's built-in `ssh` client takes the same arguments (est.). The web page's certificate is self-signed, so a browser will warn; that is expected, and it is also a reason to reach it only over your admin path.

**Exercise 1: confirm the opt-out and the closed door.**

**Predict.** After step 7, should the string `ewsposter` appear in the compose file? Should anything from the decoy appear in your firewall's blocked log? If so, what?

**Do.** On the T-Pot host:

```bash
# est.: not run
grep -n -i ewsposter ~/tpotce/docker-compose.yml ; echo "grep exit=$?"       # 1 means no match
dps                                                                          # T-Pot's alias for a container list (the README says the installer adds it)
```

Then read your firewall's log of blocked connections from the honeynet interface for the last hour. From a Windows machine: `ssh -p 64295 USER@203.0.113.5 "grep -n -i ewsposter ~/tpotce/docker-compose.yml; echo grep exit=$?"` (est.).

**Check.** The `grep` should print nothing and exit 1 (no match). `ewsposter` should not be in the container list. The firewall log will probably show blocked attempts from the decoy host: name resolution, time synchronization, update checks. Each one is something the machine wants that you have not allowed. Write down what they are and decide on purpose whether to allow any of them. If you see a connection to a name you do not recognize, stop and look it up before you continue.

**Undo.** None needed: the opt-out is what you want to keep. If you ever want sharing back (not recommended here), the block is quoted in the README and the compose files sit in `~/tpotce/compose`.

## A guided tour, from your own machine

You will cause a few events yourself, from **your own machine on your own LAN**, to the decoy you built and own. Never point this at an address you do not own: this is the same rule as the rest of the track, and [minimum 5](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums) applies.

**Predict.** If you open the decoy's address in a browser on port 80 and try to log in over SSH on port 22 with an invented password, which honeypots do you expect to see in Kibana, and will the invented password be in the event? Write both guesses.

**Do.** From a machine on the LAN (the tripwire path in your rules):

```bash
# est.: not run
curl -sS -m 5 -o /dev/null -w '%{http_code}\n' http://203.0.113.5:80/
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password -o StrictHostKeyChecking=no -p 22 labuser@203.0.113.5
# type an invented password when asked, e.g. the word "invented-1"; a refusal is expected
```

```powershell
# est.: not run
try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 http://203.0.113.5:80/).StatusCode } catch { $_.Exception.Message }
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password -p 22 labuser@203.0.113.5
```

Then, from the admin machine, open the T-Pot web page, choose **Kibana**, and look for your two events in a dashboard for the honeypot that owns the port (the port table above tells you which, depending on your compose file). The dashboard titles were not read for this page (est.).

**Check.** You should find your address as the source, a time that matches, and the port. Whether the invented password appears in the event depends on the honeypot and release (est.; Cowrie is described as logging login attempts), which is why [minimum 7](Deception-and-Honeypots-Safety-and-Law.md#the-eight-minimums) says logs stay private: **real people's passwords can appear in these logs.** Note how many events your two actions made. It is likely more than two, because one web request can touch several honeypots (est.).

**Undo.** Nothing to undo on the decoy: events are just data, and the 30-day retention cleans up. Close the web page and SSH session. If you want the data gone now, see the [teardown](#teardown-and-decommission).

## What to do when it alerts

First, the honest limit: **the README documents dashboards and an attack map, not notifications.** I searched it for alert, notification, email, webhook, syslog, Wazuh and filebeat and found none of them. So "alert" here means a human looking at Kibana or at your firewall's log, until you build a way to be told. The README does not document how to send T-Pot's data to a SIEM either, and the [education plan](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-22-honeypot-education-plan.md) lists the ways to do it as unverified. Lesson 12, "T-Pot to the SIEM", is **not written** for that reason. [Lesson 5](Deception-and-Honeypots-Alerts-in-the-SIEM.md) shows the detection ideas on invented events.

On an internal-only decoy, nothing legitimate has a reason to touch it, so a touch is a signal. Before you panic, rule out yourself.

| What you see | Most likely | First move |
|---|---|---|
| A burst of connections across many ports from one LAN address, at a time you were testing | **You**, or a scanner you run: a vulnerability scanner, a network inventory tool, a backup or monitoring probe | Compare the address and time with your own activity. If it is yours, add a note and consider whether that tool should avoid the segment |
| One or two connections from a phone or smart device | A device doing discovery or a bad configuration (est.) | Identify the device. Does it do this every day at the same time? |
| A sweep across ports, then login attempts | Something on your LAN is scanning and guessing: an infected machine, or a guest | Treat as real. Continue below |
| A login attempt with a username like `root` or `admin`, or from a device that should be asleep | As above | Continue below |
| The decoy's own firewall log shows it tried to reach your LAN, the admin path, or the internet | **The decoy may be taken over** | Disconnect it from the network (unplug it or disable its switch port). Do not trust anything on it. Rebuild later |

If it is real and not you:

1. **Write down** the time, the source address and what it touched. Screenshots of Kibana are fine; keep them private.
2. **Identify the device** behind the address: your router's DHCP lease list shows the machine name and hardware address for a LAN address.
3. **Contain it.** Move that device off the network (unplug it, or put its switch port on an isolated VLAN) *without* wiping it. A wiped machine tells you nothing. Do not log in to it from a machine you care about.
4. **Look wider.** What else did that address touch in the last days? Check your firewall's log for the same source going elsewhere.
5. **Change credentials from a clean device.** If that machine held your passwords or keys, treat them as exposed.
6. **Do not look back.** No scanning or logging in to the source "to see what it is". Even on your own network, do not log in to or scan the source from a machine you care about. For any source outside your network, [counter-hacking](Deception-and-Honeypots-Safety-and-Law.md#counter-hacking-in-plain-terms) applies in full.
7. **Tell your household** at home. At work, a decoy on a network you do not own is not yours to deploy; get written permission.

## Build, break, detect, evade, defend

- **Build.** The segment, the rules, the install with the opt-out and closed egress, and the admin path.
- **Break.** On a copy of the rules, put the management block below the LAN pass (the design page's `broken2`) and try the web page from an ordinary LAN machine: it opens. Then fix it. Then break the opt-out on paper: list the three things that would each have to fail for your data to leave (the `ewsposter` block comes back, the window is open, and something is listening on the way out), and where you would see each.
- **Detect.** Kibana for the decoy's events, the firewall log for the decoy's attempts to leave, and a daily look at both. What would tell you the decoy is no longer behaving: a stopped container in `dps`, no events at all for weeks (it may be broken or it may be quiet; test it with a touch of your own), or a blocked outgoing attempt.
- **Evade.** An intruder fingerprints the decoy: twenty services on one host, unusual management ports, a default web page. The README's blackhole mode, which "null routes all requests from known mass scanners", is aimed at internet scanners and "drastically" reduces visibility, so it is the wrong tool for an internal tripwire. Another way around is to avoid touching it at all: an intruder who stays on the machines they already own never trips it. A decoy catches the careless and the curious, not everyone.
- **Defend.** One management path, no way out, no real data, no shared data, a log nobody else reads, and the ability to wipe it. Updates are a risk and a duty: update in the window, then re-check the opt-out and the rules.
- **Flip the board.** You are now the person who wrote T-Pot's installer. You have to run as root, install Docker, open the host firewall and claim dozens of ports on a machine that will be attacked. What would you tell a user about the machine you handed them? (The README tells them: "a system compromise can never be ruled out".) And as the attacker who found it: what is the first thing you try that the defender did not think of? Write one answer for each and compare them with your rules.

## Teardown and decommission

Do this when you finish, or on the end date you wrote in your [one-page plan](Deception-and-Honeypots-Safety-and-Law.md#exercise-write-your-one-page-plan). **Order matters: remove the firewall access last,** so the decoy cannot call out while you are working on it.

1. **Decide what to keep.** Counts and a short written summary may be worth keeping. Raw logs are not. Copy nothing off the decoy that you would not publish.
2. **Stop it:** `systemctl stop tpot` (README).
3. **Uninstall, if you will reuse the machine:** `~/tpotce/uninstall.sh`, then `sudo reboot` (README; only on supported distributions). The README does not say what it leaves behind. Expect Docker, the changed SSH port and the `docker` group membership to remain (est.), which is why the next step exists.
4. **Wipe or reimage the disk.** A machine that was built to be attacked is not worth trusting. Reinstall the operating system from scratch, or for a VM delete the VM and its disk file. The README's factory reset (delete `~/tpotce/data`, `git reset --hard`, reinstall) is for repairing T-Pot, not for decommissioning.
5. **Data on disk.** Honeypot logs live in `~/tpotce/data` and persist for the number of cycles in `TPOT_PERSISTENCE_CYCLES` in `~/tpotce/.env` (default 30), and the Elasticsearch indices follow a 30-day policy by default. Wiping the disk removes both. Backups you made are yours to delete too.
6. **Remove the network pieces,** in this order: the ZTNA resource or VPN rule for the decoy; the DHCP reservation; any DNS names; the firewall rules for the honeynet (**the LAN-to-honeynet pass, the admin pass, the update window and the block**); then the VLAN or the switch port and the interface. Restore the switch port to its normal use.
7. **Prove it is gone.** From a LAN machine, connect to the old decoy address on a port it used to answer. You should get no answer: a timeout, or "no route" if you removed the interface. Then read your firewall's rule list for anything still naming the old address or segment. A rule left behind is a hole waiting for the next device that is given that address (est.).
8. **Close the paper.** Note the date, what you learned, what surprised you, and what you will do differently. Delete the plan's draft passwords and test accounts.

## Common mistakes

| Mistake | Why it hurts | Better |
|---|---|---|
| Piping the install script into a shell without reading it. | The installer changes the firewall, SSH and Docker with your password. | Clone, read, then run. |
| Skipping the opt-out because "it is only my home network". | Your devices' addresses and attempts go to a third party. | Remove it before the first boot; confirm after each update. |
| Leaving the update window open "to be safe". | A taken-over decoy can call out. | Close it after every install and update. |
| Reaching the web page from the whole LAN. | The control panel is as exposed as the trap. | Admin path only, tested. |
| Trusting a quiet dashboard. | It may be broken, or just quiet. | Touch it yourself once a week and see the event. |
| Updating without a backup and a re-check. | The README says updates overwrite local changes. | Back up first; re-check the opt-out and your rules afterward. |
| Forgetting the end date. | The decoy becomes an unmaintained machine on your network. | The plan's end date, and the teardown list. |

## What this page does not prove

- **T-Pot was not run.** Every install, tour and teardown step is a draft from the README. Dashboard names, event contents, how long start-up takes and which honeypot answers on which port in *your* compose file are unverified.
- **Release differences.** The README changes between releases. The tag and the default branch differ in supported operating systems and options.
- **What the uninstaller leaves behind** is not stated by the README.
- **Whether updates restore the data-sharing block** is not stated.
- **How to ship the events to a SIEM** is not documented, and lesson 12 is not written.
- **Your network.** The rules are placeholders. Your firewall, switch and router decide what holds.

## Claims register

Retrieved 2026-10-22.

| Claim | Source | Status |
|---|---|---|
| T-Pot is a multi-honeypot platform with 20+ honeypots and the Elastic Stack; the honeypot names; the tools (Elasticsearch, Logstash, Kibana, Elasticvue, CyberChef, Spiderfoot, Suricata, p0f, Fatt, attack map, nginx) | [T-Pot README](https://raw.githubusercontent.com/telekom-security/tpotce/HEAD/README.md), default branch | Read |
| Sizes (Hive 16 GB / 256 GB SSD; Sensor 8 GB / 128 GB SSD), IPv4 and non-proxied internet need, VM and Raspberry Pi 4 notes, no desktop environment | Same, and the [24.04.1 README](https://raw.githubusercontent.com/telekom-security/tpotce/24.04.1/README.md) for the sizes | Read |
| Required ports: management 64294, 64295, 64297; outgoing 80 and 443; honeypot port table; glutton and honeytrap bind unclaimed TCP ports | Same README, "Required Ports" and "System Placement" | Read |
| Data submitted by default to Sicherheitstacho via `ewsposter`; opt out by removing the `# Ewsposter service` block; HPFEEDS is a separate opt-in; the README encourages not disabling it | Same README, "Disclaimer" and "Community Data Submission" | Read. That the opt-out holds after an update is **not stated** |
| The installer changes the SSH port to 64295, disables the DNS stub listener, sets SELinux to monitor mode, sets the public firewall zone target to ACCEPT, installs Docker and adds the user to the docker group | Same README, "Get and install T-Pot" (also in the 24.04.1 README) | Read. That `docker` group membership is root-equivalent is **est.** (widely documented, not read here) |
| `update.sh` "mercilessly" overwrites local changes; it writes a backup first; uninstall is `~/tpotce/uninstall.sh` then a reboot; logs are in `~/tpotce/data`, kept for `TPOT_PERSISTENCE_CYCLES` (default 30); the Elasticsearch policy keeps 30 days; a daily reboot is set up at install | Same README, "Maintenance", "Uninstall T-Pot", "Log Persistence", "Daily Reboot" | Read |
| Latest tag 24.04.1, published 2024-12-11; repository last pushed 2026-10-21 (`pushed_at`); license GPL-3.0 | [GitHub API: tags](https://api.github.com/repos/telekom-security/tpotce/tags), [releases](https://api.github.com/repos/telekom-security/tpotce/releases/latest) and [repository](https://api.github.com/repos/telekom-security/tpotce) | Read |
| The two READMEs list different operating systems; the installer "will stop on an older one"; `-b` takes a branch, tag or commit | Both READMEs | Read. Whether the 24.04.1 installer accepts `-b` is **not read** |
| The README has no notification or SIEM-export documentation | Search of the default-branch README for alert, notification, email, webhook, syslog, Wazuh, filebeat | Read (a search, not proof that none exists elsewhere in the project) |
| Hardware is the learner's; no electricity figure; no hardware prices | [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) has no home-lab figures | **est.** Nothing priced |
| Behavior of any honeypot beyond the README's port table, dashboard names, event contents | Nothing | **Not read** |
| What your provider, your router or the law allows | Nothing | **Not read** |

Not verified, plainly: every command touching T-Pot or a firewall on this page.

Next: back to the [track hub](Deception-and-Honeypots-Start-Here.md), or on to [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) if you skipped it.
