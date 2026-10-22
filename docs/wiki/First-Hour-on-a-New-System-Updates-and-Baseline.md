# First hour on a new system: updates, automatic updates and a baseline, before anything else

Side page to the start-from-zero pages. Read it after [Droplet hardening](Droplet-Hardening.md) (core step 14), or at any point you are about to set up a machine, a virtual machine, a container host or a router and wonder what to do first. It is about the **order** of the first hour. The details of patch cadence, CVE scores and backups are on [Backups, recovery and patching](Backups-Recovery-and-Patching.md); this page does not repeat them. Next: [Droplet hardening](Droplet-Hardening.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from vendor documentation; one local exercise was run once, the rest was not run.** I read every vendor page cited below on **2026-10-22** (read-only requests; the claims register at the end lists each, and says where I read only part of a page). On the same day I ran the baseline script and the drift demo from Exercise 3, and the stagger script from Exercise 5 (Bash only) inside a throwaway Ubuntu 24.04 container with networking switched off, using rootless Podman, and the output shown is from that run, trimmed. That container had no `unattended-upgrade` command and no network, so the `unattended-upgrades` and `dnf-automatic` commands in Exercises 1 and 2 were **not run** and are marked **est.** (estimate). The PowerShell and Windows commands were not run either (no Windows machine); they are marked **est.** The October 2026 PHP flaws were read from php.net and the two GitHub advisories on 2026-10-22; I did not test any exploit and the page contains none.

> **Prerequisites.** [The terminal and your first script](Terminal-and-Your-First-Script.md) (running a script, reading an exit code) and, for the container exercises, [Containers and Docker basics](Containers-and-Docker-Basics.md). [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) helps with the package-manager words. The free path needs a Linux or macOS computer with Podman or Docker, or a virtual machine you can throw away (Windows readers: the PowerShell variant in Exercise 3 runs on your own machine and only reads). About 90 minutes (est.).

> **Where this runs.** Everything in the free path runs inside a throwaway container or virtual machine that you delete afterward, or only **reads** the machine you are on. No exercise installs updates on your real computer. Nothing on this page scans, probes or attacks anyone else's machine. The only thing I ask you to scan is your own lab, on its loopback address.

## What you will be able to do

- Say why the first hour of a new machine is spent on updates and a baseline, and the order of the four steps: **update and turn on automatic updates, take a baseline, harden, then put applications and workloads on**.
- Explain what "automatic updates" means on Debian and Ubuntu, the Red Hat family, SUSE, Amazon Linux 2023, Windows, macOS, FreeBSD, pfSense and OPNsense, what each does by default, and what none of them touches.
- Use the October 2026 PHP flaws to say what an automatic update would have fixed on a server and what it would have missed.
- Name the real risk of automatic updates (a bad update breaks a service) and six ways to manage it.
- Write and run a baseline script, change a machine, and read the difference.
- Describe the update channel as an attack surface of its own.
- Apply the order to this project's cloud-init, and say what is planned but not built.

## The ruling this page teaches

The project maintainer's rule, 2026-10-22: "we should showcase auto updating at system setup and why this is critical no matter what operating system you use before you do anything. Updates and baseline first, then applications and workloads."

The rest of this page is the reasons, the mechanics and a way to practice it. The reasons are not specific to a cloud: the same order applies to a laptop, a Raspberry Pi, a firewall appliance and a server.

## Why this first

A **patch** is a change a vendor ships to fix a defect, usually a security flaw. A **security update** is a patch whose purpose is a security fix. An **image** is a stored copy of an operating system's disk that new machines are made from. Three facts explain the order.

1. **The machine is oldest at the moment you create it.** An image is built at one date and used later. The cloud image, the installer on a USB stick, the container base image and the router firmware all carry whatever was current when they were built, plus whatever was found since. Amazon's documentation says it plainly for its own Linux: by default an Amazon Linux 2023 instance "doesn't automatically receive additional critical and important security updates at launch. Your instance initially contains the updates that were available in the version of AL2023 and the chosen AMI" ([AL2023 guide](https://docs.aws.amazon.com/linux/al2023/ug/deterministic-upgrades.html), read 2026-10-22). So the first update is a step you must take.
2. **Attackers keep using old flaws.** The US Cybersecurity and Infrastructure Security Agency (CISA) writes that "attackers may target vulnerabilities for months or even years after updates are available", and that if automatic options are available it recommends you take them ([CISA, Understanding Patches and Software Updates](https://www.cisa.gov/news-events/news/understanding-patches-and-software-updates), read 2026-10-22). How quickly a new public service is found by internet-wide scanning is a number I did not read from a source I could cite, so I do not give one; the safe working assumption (est.) is that a service on a public address is found within hours, not weeks.
3. **Anything you build on a stale base inherits its flaws.** If the application goes on first and the update later, you update under a running workload, you have no record of what the machine looked like before, and you cannot tell the update's changes from the application's. Updating first, then taking a baseline, gives you a clean starting line.

### The order, in four steps

| Step | What | Why it comes here |
|---|---|---|
| 1. Update, then turn on automatic updates | Bring every package to current once, by hand, and reboot if asked. Then switch on the unattended mechanism for security updates, with a maintenance window that is [staggered](#stagger-your-maintenance-windows) from its peers. | Fixes the known flaws in the image, and keeps fixing new ones while you sleep. |
| 2. Take a baseline | Write down package versions, listening ports, users, enabled services, firewall rules and hashes of key configuration files, in a text file you keep somewhere else. | Everything later is compared against this. You cannot see drift without a "before". |
| 3. Harden | Remove or disable what you do not need, restrict who can log in, set the firewall. See [Droplet hardening](Droplet-Hardening.md) and [Packet filters compared: iptables, nftables, ufw and pf](Packet-Filters-Compared-iptables-nftables-ufw-pf.md). | You harden a current system, and you take a second baseline afterward. |
| 4. Applications and workloads | Install the web server, the database, the containers. | They land on a patched, known, locked-down base, and from now on their changes show up in a diff. |

One caution: step 1 can be done before the machine is reachable from the internet, or with the firewall closed to everything except your own management path. On a cloud droplet that means creating it with the cloud firewall already attached, as [Backups, recovery and patching](Backups-Recovery-and-Patching.md) and [Droplet hardening](Droplet-Hardening.md) do. (A cloud firewall is a filter in front of the machine, run by the provider.)

## The worked example: the October 2026 PHP flaws

On 2026-10-22 the php.net front page announced PHP **8.5.12, 8.4.27, 8.3.36 and 8.2.35** as security releases "fixing two critical vulnerabilities (CVE-2026-109618, CVE-2026-109619) that can allow unauthenticated remote code execution", and said "There are no complete mitigations, updating is the only safe choice" ([php.net](https://www.php.net/), read 2026-10-22). **Remote code execution** (RCE) means an outsider makes your server run code of their choosing. **Unauthenticated** means they did not need to log in first. **PHP** is the language that runs WordPress and a great many other websites; **mod_php** is the Apache web server's built-in way of running it.

The two GitHub advisories, [GHSA-w8hw-w9fx-j79w](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w) ("RCE via OOM corruption") and [GHSA-6wmf-4rv5-p3rp](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp) ("RCE via stale global state"), both read 2026-10-22, are rated Critical, were published on 21 October 2026, list affected versions below 8.2.35, 8.3.36, 8.4.27 and 8.5.12, and list the same four versions as patched. The php.net notice, which I read, says Linux distributions and long-term-support vendors "received the patches in advance, so check your vendor for updated packages" and that PHP 8.1 and older no longer receive updates from the project, though some vendors provide backported fixes. [WordPress and PHP security](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) explains the flaws, the mitigations and which server shapes are most exposed (mod_php is the highest risk in the advisory text); this page asks a different question: **what would "auto update" have done?**

| Where PHP came from | Did OS automatic updates cover it? | What you must do |
|---|---|---|
| The distribution's PHP package (for example `php8.3` from the Ubuntu or Debian archive) | Yes, **if** the distribution shipped a fixed package and the automatic mechanism is allowed to take it. Ubuntu's defaults take the security pocket (Debian's default I did not read, est.); a package fixed there arrives on the next run. Whether your distribution had published the fix on a given day is a fact about your vendor, not about the tool (est.: check the vendor's security tracker). | Make sure the **service restarts** after the package changes (a reboot does it; on some systems a service restart is automatic, on others it is not) and then check the version. |
| A third-party repository (for example a vendor-maintained PHP repository you added) | Only if that repository is in the tool's allowed list. Ubuntu's documentation says adding a repository "WILL NOT make unattended-upgrades consider it for updates" ([Ubuntu Server documentation](https://documentation.ubuntu.com/server/how-to/software/automatic-updates/), read 2026-10-22). | Add the origin to the allowed list on purpose, or update that repository by hand. |
| PHP compiled from source, or unpacked from a download | No. The OS does not know it exists. | You are the vendor. Track the releases yourself. |
| PHP inside a container image (`php:8.3-apache`, a WordPress image) | **No.** The host's updates never look inside an image. Docker says: "Docker images are immutable. Building an image is taking a snapshot of that image at that moment ... To keep your images up-to-date and secure, rebuild your images often" ([Docker build best practices](https://docs.docker.com/build/building/best-practices/), read 2026-10-22). | Pull or rebuild the image, then recreate the container. A running container keeps running the old image (est.; the consequence of immutability). |
| PHP vendored in an application bundle or a Windows `.zip` | No. | Replace it from the application vendor's fixed release. |
| PHP 8.1 or older | Only if your vendor backports fixes. The project does not. | Move to a supported version, or confirm the vendor's backport. |

So a server with perfect automatic updates can still run a vulnerable PHP. What the update setup does is shrink the cases where *you* have to do something to the ones in the lower rows. Notice also that the order mattered in a second way: a server whose operator took a baseline at setup could answer "which of my machines run mod_php, and which version?" with a file search instead of a guess.

The vendor-side detail "patches in advance" is also the reason updates are worth taking daily: the fix may be in your distribution's archive before the public announcement.

## What "automatic updates" means, system by system

Words first. An **update** replaces installed software with a newer version. A **security-only** update takes only changes marked as security fixes. An **all updates** policy takes every new version, including features. A **reboot** restarts the machine; some updates (the kernel, the C library, the init system) only take effect after one. **Live patching** changes the running kernel without a reboot.

| System | The automatic mechanism | What it does by default | Security-only vs all | Reboot | Read from |
|---|---|---|---|---|---|
| Debian, Ubuntu | `unattended-upgrades` (package) driven by APT's daily timer | On Ubuntu, "will apply security updates automatically, without user interaction", the package "installed by default"; the allowed-origins list defaults to the release and its security pocket (and ESM, where available) | Security-focused by default; the origins list decides; "it can apply other types of updates, not just security" | `Automatic-Reboot` defaults to `false`; you can set a reboot time | [Ubuntu Server](https://documentation.ubuntu.com/server/how-to/software/automatic-updates/) (read), [`unattended-upgrade(8)`](https://manpages.debian.org/unstable/unattended-upgrades/unattended-upgrade.8.en.html) (read). Plain Debian: package is not installed by default (est.). |
| RHEL, Fedora, CentOS Stream, Rocky, Alma | `dnf-automatic` (package), run by systemd timers | `/etc/dnf/automatic.conf`: `apply_updates` defaults to **False** (it only downloads and reports); the timer units `dnf-automatic-notifyonly`, `-download` and `-install` override that setting | `upgrade_type` is `default` (all) or `security` (only updates with an issued advisory); the default is `default` | `reboot` is `never`, `when-changed` or `when-needed`; default `never` | [DNF Automatic](https://dnf.readthedocs.io/en/latest/automatic.html) (read) |
| SUSE Linux Enterprise | `zypper patch` installs relevant patches; running it unattended is something you schedule (est.; SUSE also has YaST and `zypper` timers I did not read) | None to speak of out of the box (est.) | `zypper` patches carry a category (security, recommended, optional) | A patch can flag that it needs a reboot or restart; `zypper ps` lists processes using deleted files | [SLES zypper chapter](https://documentation.suse.com/sles/15-SP6/html/SLES-all/cha-sw-cl.html) (read in part) |
| Amazon Linux 2023 | No unattended installer is part of the image; repositories are **versioned** ("deterministic upgrades") | The image is locked to the repository version it was built with; updates arrive when *you* move to a newer version | Amazon recommends taking all updates in a new release; "Picking just security updates, or only specific updates should be the exception" | A new kernel needs a reboot; kernel live patching exists for some uses | [AL2023 guide: managing updates](https://docs.aws.amazon.com/linux/al2023/ug/managing-repos-os-updates.html) and [deterministic upgrades](https://docs.aws.amazon.com/linux/al2023/ug/deterministic-upgrades.html) (read) |
| Windows | Windows Update; in organizations, Windows Update client policies set through Group Policy or a device-management service such as Microsoft Intune | On a consumer PC, updates are on by default (est.; not read for this page) | Microsoft splits **quality updates** (monthly security and fixes, "typically ... the second Tuesday of each month") from **feature updates**; you can pause each for up to 35 days | Updates schedule or require restarts; deadlines are policy (est.) | [Windows Update policies](https://learn.microsoft.com/en-us/windows/deployment/update/waas-manage-updates-wufb) and [configuring them](https://learn.microsoft.com/en-us/windows/deployment/update/waas-configure-wufb) (read in part) |
| macOS | Software Update, "Automatic Updates" settings | Each switch is separate: download new updates; install macOS updates; install "Security Responses and system files" | Three separate toggles, not a security-only mode | Some updates restart the Mac; laptops want the power adapter attached | [Apple, Get macOS updates](https://support.apple.com/guide/mac-help/get-macos-updates-mchlpx1065/mac) (read) |
| FreeBSD | `freebsd-update` for the base system, `pkg` for packages | Not automatic; you may add `@daily root freebsd-update cron` to `/etc/crontab`, which downloads patches but does not apply them and emails root | Binary security and errata updates for the base system | Reboot if `freebsd-version -k` and `uname -r` differ; `freebsd-update rollback` can undo the last set | [FreeBSD Handbook, Updating](https://docs.freebsd.org/en/books/handbook/cutting-edge/) (read) |
| pfSense | Firmware upgrade from the web interface or console; the "Update Settings" page chooses a branch | Not unattended; you run the upgrade. Take a backup first; the page documents ZFS boot environments as a rollback path | Whole-system releases | A reboot is part of the upgrade; the firewall must be connected to the internet to update | [Netgate: upgrade guide](https://docs.netgate.com/pfsense/en/latest/install/upgrade-guide.html) (read in part) |
| OPNsense | System, Firmware, Status: "Check for updates" | Not unattended by default (est.); two major releases a year with minor updates "about every two weeks" | Minor updates from the web interface; major updates install offline | Major updates are installed offline: no web or SSH server runs during the upgrade, so have a console | [OPNsense: Updates](https://docs.opnsense.org/manual/updates.html) (read) |

Four things to take from the table.

- **"Installed" is not "on".** `dnf-automatic` ships with `apply_updates = no` by default. A system with the package installed and the notify-only timer enabled will tell you about updates forever and install none. This is in the Common mistakes table of the sibling page too.
- **Defaults differ and change.** Read the vendor page for your release. Use the table as a map of where to look.
- **Appliances are different.** A router or firewall that updates itself in the middle of the night would take your network down, so the vendors above chose "you press the button". That makes your calendar the control. Set one (est.).
- **Containers, language packages and devices are not in the table.** See "What OS updates do not cover".

### Security-only or all updates?

A **security-only** policy keeps changes small, which lowers the chance of a surprise, and fixes the flaws you hear about. The cost is that the machine slowly drifts from the vendor's tested whole: bug fixes you skip may be what the next security fix assumes. Amazon's recommendation for AL2023 (take all updates in a release) and Debian/Ubuntu's security-first default are both defensible. A practical split (est.; this is a convention, not a vendor rule): **automatic security updates daily; a full update on a calendar, in a maintenance window, after testing.** That is also what this project's droplets do: security updates daily, nothing else automatic ([Droplet hardening: updates](Droplet-Hardening.md#updates)).

### Reboots, kernel live patching, maintenance windows

A **maintenance window** is a time agreed in advance when a system may be restarted or briefly unavailable for work like patching. Reboots matter because some fixes, mainly the kernel, do nothing until the machine restarts. Ubuntu's page warns "Reboots can be very disruptive, especially if the system fails to come back" and lets you set a reboot time. The project's connectors reboot at set times an hour apart so the two never go down together ([Droplet hardening: updates](Droplet-Hardening.md#updates)).

**Live patching** is a way to fix the running kernel without restarting. Canonical's Livepatch says it patches the Linux kernel "between security maintenance windows, while the system runs", and is available with Ubuntu Pro ([Canonical Livepatch](https://ubuntu.com/security/livepatch), read 2026-10-22). The open-source kpatch describes itself as "a Linux dynamic kernel patching infrastructure which allows you to patch a running kernel without rebooting or restarting any processes" ([kpatch on GitHub](https://github.com/dynup/kpatch), read 2026-10-22). Amazon's page says kernel live patching "may allow you to postpone security updates for a limited period of time". I did not read TuxCare's KernelCare page (the request was refused), so I say nothing about it. Live patching covers the **kernel** only, not PHP, not OpenSSL, not a container.

## Stagger your maintenance windows

A single window for everything is the easy plan and the wrong one. **Stagger** means spreading maintenance over different times, so that no two machines that matter to each other are down together. For a few machines the unit is the device. In a company the unit is usually a **group** of devices, updated in waves.

### Why

- **Never take every instance of a service down together.** If two servers do the same job, update one, confirm it is healthy, then the other. Done in the same minute, one bad update or one slow reboot is a full outage.
- **The first window is a canary for the rest.** A **canary** is the first, low-risk machine you update so that you learn about a problem before everyone has it. A staggered plan makes that automatic: whoever goes first is the test.
- **Dependent services need an order.** A database that comes back after the application that needs it produces errors that look like an attack. Put the thing others depend on in a window of its own, with a gap.
- **A bad update has a small blast radius.** The **blast radius** is how much a mistake can break. Staggering shrinks it from "everything" to "this group".
- **Rollback and attention are finite.** One person on call can roll back one machine at a time. Ten machines failing at 04:00 are ten simultaneous problems.
- **Capacity and load.** Machines that come back and all pull updates or rebuild caches at once can saturate a link or a mirror (est.; a general operations point, not a vendor statement). A sibling that stays idle can take the traffic of the one being updated.
- **Avoid reboot storms.** Many machines rebooting in the same minute is a **reboot storm**: they hammer shared services such as DNS, directory logins and storage together, as they come up.

### How this project does it

The two Twingate connector droplets are a pair: either one keeps access working while the other is down. Their windows are set so the pair never reboots together: connector a reboots at 04:00 and connector b at 05:00 Eastern, and the weekly connector package update runs on Sundays half an hour after each reboot (04:30 for a, 05:30 for b) ([Droplet hardening: updates](Droplet-Hardening.md#updates), read in this repository 2026-10-22). The template comment gives the reason for using a cron entry: `cron.weekly` "would fire on both connectors at the same moment, and the whole point of two connectors is that they never restart together".

**The plan for the edge droplets (a maintainer ruling for the DMZ draft; planned, not built).** The edge stacks are not applied and nothing in the [edge DMZ design](../superpowers/specs/2026-10-19-edge-dmz-design.md) is approved to build. The ruling is that each edge service stack gets one slot, set as a variable, in a window **before** the connectors' windows, and a test fails if any two droplets share a minute. I did not find that test in the repository; it is part of the plan. The design itself says the edge host's reboot window must not collide with the connectors' ("a reboot window that does not collide with the connectors'").

### The enterprise version: groups, rings and waves

Companies stagger by groups of devices. The names differ by product; the idea is the same.

| Product | Its word | What it does | Read from |
|---|---|---|---|
| Windows Autopatch | Autopatch groups, deployment rings | A container that ties several Microsoft Entra groups to update policies; "By default, an Autopatch group has the Test and Last deployment rings automatically present" | [Autopatch groups overview](https://learn.microsoft.com/en-us/windows/deployment/windows-autopatch/deploy/windows-autopatch-groups-overview) (read in part) |
| Microsoft Intune | Update rings | Control deferral periods, restart settings, deadlines and active hours; "commonly used to create deployment stages ... test, pilot, and production ... by assigning different settings to different device groups" | [Intune update ring policies](https://learn.microsoft.com/en-us/mem/intune/protect/windows-10-update-rings) (read in part) |
| Windows Update for Business | Deployment rings | The update policies page recommends testing on a subset of devices before the organization (see the Windows row above) | [Windows Update policies](https://learn.microsoft.com/en-us/windows/deployment/update/waas-manage-updates-wufb) (read in part) |
| WSUS (Windows Server Update Services) | Computer groups | Approve updates for a test group first, then wider groups (est.; the Microsoft page I tried returned 404, so I did not read it) | not read |
| AWS Systems Manager | Patch groups, Maintenance Windows | A **patch group** tags nodes so a baseline applies to them; Maintenance Windows "define a schedule for when to perform potentially disruptive actions on your nodes such as patching an operating system". The page notes patch groups are not used with newer patch policies | [Patch groups](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-patch-groups.html), [Maintenance Windows](https://docs.aws.amazon.com/systems-manager/latest/userguide/maintenance-windows.html) (read in part) |
| Ansible | `serial` | "You can set a number, a percentage, or a list of numbers of hosts you want to manage at a time with `serial`"; the play finishes on one batch before the next | [Controlling playbook execution](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_strategies.html) (read in part) |
| Kubernetes | Rolling updates, PodDisruptionBudget | Rolling updates replace pods "incrementally ... with zero downtime"; a **PodDisruptionBudget** limits "the number of concurrent disruptions that your application experiences" while the administrator drains nodes. Staggering node pools (est.: updating one pool of nodes at a time) is the same idea at the machine level and I did not read the managed-Kubernetes pages | [Rolling updates](https://kubernetes.io/docs/tutorials/kubernetes-basics/update/update-intro/), [Disruption budgets](https://kubernetes.io/docs/tasks/run-application/configure-pdb/) (read in part) |

**A typical ring design (est.; a common pattern, not one vendor's rule, and the soak times are examples):**

| Ring | Who | Soak before the next ring |
|---|---|---|
| 0 Test / canary | IT's own machines, a lab copy | 1 to 2 days |
| 1 Early adopters | A few volunteers per team, a non-critical server per role | 2 to 3 days |
| 2 Broad | Most of the fleet, split so redundant pairs land in different slots | A week or a full business cycle |
| 3 Critical, last | Domain controllers, databases, the firewall pair, anything whose outage stops the business | Last, with a person watching |
| Exception group | Systems that need a manual, planned change (medical, factory, anything with a vendor certification) | Manual change, own ticket |

The **soak time** is how long a ring runs on the update, watched, before the next ring starts. It is what turns "stagger" into protection: if ring 1 shows a problem, ring 2 has not started. An update that is an emergency (an actively exploited flaw such as the October 2026 PHP case) may compress the soak, and should still keep the order; that is an emergency change in the sense of [Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md#emergency-changes-and-break-glass).

## The real risk: a bad update breaks something

This is the honest objection and it is correct. An automatic update can break a service, and it will happen to someone. SUSE's own documentation shows both the problem and the vendor's answer: if a patch "contains a bug, a new update (with a higher version number) is issued to revert the buggy update, and the buggy update is blocked from being installed again", and you can list the retracted patches with `zypper lp --all` ([SLES zypper chapter](https://documentation.suse.com/sles/15-SP6/html/SLES-all/cha-sw-cl.html), read 2026-10-22). Break-then-retract happens at every vendor; the question is how you absorb it. Six habits:

1. **Snapshot or back up first.** A snapshot is a point-in-time copy kept near the original. On a cloud droplet this is a provider feature; on a virtual machine it is one click; on pfSense with ZFS it is a boot environment. See [Backups, recovery and patching](Backups-Recovery-and-Patching.md) for the difference between a snapshot and a backup, and for restore time.
2. **Stage on a copy.** Keep a second machine of the same kind. Update it first; wait a day; update the rest. In an enterprise this is a "ring" system; Windows Update policies call them deployment rings (the idea, from the page I read: update "a subset of devices before deploying across the organization").
3. **Pin critical packages on purpose.** Holding a package at a version (`apt-mark hold`, a `versionlock` plugin for dnf) stops it from changing. Do it for the one thing that must not move, and put an owner and an expiry date on the hold, because a forgotten hold is a quiet vulnerability. (Command names are est.)
4. **Canary.** Update one low-risk machine of many first and watch it.
5. **Know how to roll back.** `freebsd-update rollback`; a ZFS boot environment; a snapshot restore; on Debian, installing the previous version of one package from the archive (est.). A rollback you have never tried is a hope.
6. **Monitor the result.** After a window, check that the services are up and the reboot happened. A tool that tells you what the host did is [Patch Gremlin](https://github.com/ChiefGyk3D/Patch-Gremlin), the author's own project (README read 2026-10-22: it sends notifications from `unattended-upgrades` and `dnf-automatic` on Debian and RHEL-based systems; I did not read its code). It reports on the **host OS** only; it does not look inside a container image.

The risk of *not* updating is real as well: the October 2026 flaws are critical and exploitable without a login. Compare the two risks in writing before you decide to turn automatic updates off. "It might break" is a reason for steps 1 to 6, not for staying unpatched.

## What OS updates do not cover

| Layer | Updated by the OS tool? | What does update it |
|---|---|---|
| Container images | No (immutable; the base image is whatever it was built from) | Rebuild or pull a newer tag, recreate the container. A bot that proposes new image tags, such as Dependabot or Renovate (est.), or a scanner. |
| Language packages (npm, pip, composer, Go modules) | No, unless you installed them through the distribution's own package | Your project's dependency list plus a bot. GitHub says Dependabot "takes the effort out of maintaining your dependencies" ([About Dependabot version updates](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/about-dependabot-version-updates), read 2026-10-22; the page's list of supported package managers I did not read). |
| Applications you downloaded | No | The vendor's updater, or you. |
| Firmware and BIOS/UEFI | Sometimes | On Linux, a service such as `fwupd` (est.); on Windows, Windows Update can deliver some; on a router or appliance, the vendor's update page. Firmware updates carry a bigger bricking risk than software: read the vendor's notes and do not interrupt power. |
| Appliances and IoT (routers, cameras, printers) | No | The vendor's firmware page; many never update themselves. Isolate what you cannot patch (the "unpatchable assets" scenario in [NIST SP 800-40r4](https://doi.org/10.6028/NIST.SP.800-40r4), which is cited on the sibling page). |
| The repository you added by hand | No (not on the allowed list) | Add it deliberately; this project's connector package is updated by its own weekly cron job for exactly this reason. |

## Where this shows up in this project

Read these in the repository; I read them on 2026-10-22.

- **Step 1 is in cloud-init.** `modules/twingate-bootstrap/cloud-init.yaml.tftpl` sets `package_update: true` and `package_upgrade: true` (update everything at first boot), installs `unattended-upgrades`, writes `/etc/apt/apt.conf.d/20auto-upgrades` (daily list refresh and daily unattended run) and an override file that allows only the release security origins (and the ESM security origins), removes unused dependencies and reboots at a set time. **Cloud-init** is the first-boot configuration that runs once when a cloud machine starts. The connector software comes from a third-party repository, so it is not in the allowed origins; the template adds a weekly `cron.d` entry that updates just that package and restarts its service. The template's comments say the first boot "races Ubuntu's own apt-daily and unattended-upgrades for the dpkg lock", so the install waits for it ([stage 1 guide](../stages/01-access.md)).
- **The order inside the file** is: update, install the unattended-upgrades package, write the hardening (sshd, sysctl, firewall) and install the connector last. That matches steps 1, 3 and 4.
- **Step 2 is not built.** The template does not record a baseline at first boot. Issue #232's second "done when" item (the stage guides and templates state the same order, with a test) is not done by this page. A baseline hook in cloud-init would be new code and needs its own approval.
- **Edge droplets install no service until its own stack is built and approved** (maintainer ruling). The edge design ([edge DMZ design](../superpowers/specs/2026-10-19-edge-dmz-design.md), a draft, nothing in it approved to build or spend) says the host's software is pinned by version and checksum, "current releases only", that operating system packages come through unattended upgrades, and that the host is rebuilt on a schedule "because the host cannot be patched by hand". That is the order applied to a service host: the host is patched and baselined first; each service arrives later through its own stack, with a version read from that project's releases page and not `latest`. A template test that fails on an unpinned package name is listed in the design as the check; I did not check whether it exists.
- **Containers.** Nothing in the current stacks runs a container ([Backups, recovery and patching](Backups-Recovery-and-Patching.md)); the container row above is about stage 3 and your own machines.

## Free path: a lab with nothing to lose

Cost: $0. Everything below runs in a throwaway container or virtual machine, or only reads your machine.

You need Podman or Docker (`podman` and `docker` commands are interchangeable below; Docker may need `sudo`, Podman rootless does not) or a virtual machine you can delete. You do **not** run these on your real computer's system packages.

### Exercise 1: automatic updates on Debian or Ubuntu (dry run)

**Predict.** If you install `unattended-upgrades` in a fresh container and run its dry run, will it install anything? Which log file will say what it did?

**Do.** In a throwaway container with network access (est.; I could not run this: my lab container had no network and no `unattended-upgrade`):

```bash
# Bash: start a disposable Ubuntu container, install the tool, dry-run it.
podman run --rm -it docker.io/library/ubuntu:24.04 bash -c '
  apt-get update -q && apt-get install -y -q unattended-upgrades
  cat /etc/apt/apt.conf.d/20auto-upgrades 2>/dev/null || echo "(no 20auto-upgrades file yet)"
  unattended-upgrade --dry-run --debug 2>&1 | tail -n 15
  ls /var/log/unattended-upgrades/
'
```

```powershell
# PowerShell on a Windows host with Podman or Docker (est.; same command, different quoting)
podman run --rm -it docker.io/library/ubuntu:24.04 bash -c "apt-get update -q && apt-get install -y -q unattended-upgrades && unattended-upgrade --dry-run --debug 2>&1 | tail -n 15"
```

**Check.** `--dry-run` "just simulate[s] installing updates, do not actually do it", and `--debug` writes to `/var/log/unattended-upgrades/unattended-upgrades.log` ([`unattended-upgrade(8)`](https://manpages.debian.org/unstable/unattended-upgrades/unattended-upgrade.8.en.html), read 2026-10-22). Ubuntu's log excerpt lists the "Allowed origins" on its first lines; read yours and match it against the origins list in the table. In a container, the daily timer does not run (there is no running init system), so this exercise teaches the configuration and the dry run, not the schedule.

**Undo.** `--rm` already deleted the container. `podman images` still shows the downloaded image; remove it with `podman rmi docker.io/library/ubuntu:24.04` if you want the space back.

### Exercise 2: the same idea on the RPM family

**Predict.** After you install `dnf-automatic` and change nothing, will it install updates? Which setting decides?

**Do** (est.; not run, same reason):

```bash
podman run --rm -it docker.io/library/fedora:latest bash -c '
  dnf -y -q install dnf-automatic
  grep -E "^(upgrade_type|apply_updates|reboot) " /etc/dnf/automatic.conf
  ls /usr/lib/systemd/system/ | grep dnf-automatic
'
```

**Check.** From the DNF Automatic page (read 2026-10-22): `apply_updates` defaults to `False`; `upgrade_type` takes `default` or `security`; `reboot` takes `never`, `when-changed` or `when-needed`; and the units `dnf-automatic-notifyonly`, `dnf-automatic-download` and `dnf-automatic-install` "override the configuration file". On a real host you would enable one with `systemctl enable --now dnf-automatic-install.timer` (est.; I did not run it). Container note: `fedora:latest` moves; for a repeatable lab pin a release tag.

**Undo.** `--rm`, as before.

### Exercise 3: take a baseline, drift it, read the diff

This one I ran. It needs no network, so it works anywhere.

Save this as `baseline.sh`. It only reads the system and writes one file.

```bash
#!/usr/bin/env bash
# baseline.sh - write a plain-text baseline of this machine, and compare two of them.
# Usage: ./baseline.sh snapshot FILE      write the baseline to FILE
#        ./baseline.sh compare OLD NEW    show what changed between two baselines
# Read-only: it reads system state and writes only FILE. It never changes the system.
set -u
section() { printf '\n## %s\n' "$1"; }
snapshot() {
  {
    echo "# baseline $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    section os
    grep -E '^(PRETTY_NAME|VERSION_ID)=' /etc/os-release 2>/dev/null
    uname -r
    section packages
    if command -v dpkg-query >/dev/null; then dpkg-query -W -f='${binary:Package} ${Version}\n' | sort
    elif command -v rpm >/dev/null; then rpm -qa --qf '%{NAME} %{VERSION}-%{RELEASE}\n' | sort
    elif command -v apk >/dev/null; then apk info -v | sort
    else echo "(no known package manager)"; fi
    section listening-ports
    if command -v ss >/dev/null; then ss -H -tuln | awk '{print $1, $5}' | sort
    else echo "(ss not installed; est. fall back to netstat -tuln)"; fi
    section users
    awk -F: '{print $1, "uid=" $3, "shell=" $7}' /etc/passwd | sort
    section groups-with-admin-rights
    getent group sudo wheel admin 2>/dev/null
    section enabled-services
    if command -v systemctl >/dev/null && systemctl is-system-running >/dev/null 2>&1; then
      systemctl list-unit-files --state=enabled --no-legend | awk '{print $1}' | sort
    else echo "(systemd not running here)"; fi
    section firewall
    if command -v nft >/dev/null; then nft list ruleset 2>&1
    elif command -v iptables-save >/dev/null; then iptables-save 2>&1 | grep -v '^#'
    else echo "(no nft or iptables-save here)"; fi
    section config-hashes
    for f in /etc/ssh/sshd_config /etc/sudoers /etc/passwd /etc/group /etc/hosts \
             /etc/apt/apt.conf.d/20auto-upgrades /etc/dnf/automatic.conf; do
      [ -r "$f" ] && sha256sum "$f"
    done
    [ -d /etc/sudoers.d ] && find /etc/sudoers.d -type f -exec sha256sum {} + 2>/dev/null | sort -k2
  } > "$1"
  echo "wrote $1 ($(wc -l < "$1") lines)"
}
case "${1:-}" in
  snapshot) [ $# -eq 2 ] || { echo "usage: $0 snapshot FILE" >&2; exit 2; }; snapshot "$2" ;;
  compare)  [ $# -eq 3 ] || { echo "usage: $0 compare OLD NEW" >&2; exit 2; }
            diff -u <(grep -v '^# baseline' "$2") <(grep -v '^# baseline' "$3") && echo "no drift" ;;
  *) echo "usage: $0 snapshot FILE | compare OLD NEW" >&2; exit 2 ;;
esac
```

Then the drift demo, saved as `drift.sh`. It runs **inside a throwaway container**, because it creates a user and a package:

```bash
#!/usr/bin/env bash
# drift.sh - runs INSIDE a throwaway container: baseline, drift, baseline, compare.
set -eu
B=/usr/local/bin/baseline.sh
$B snapshot /tmp/before.txt
# drift 1: a tiny local package built at run time (no network needed)
mkdir -p /tmp/pkg/DEBIAN
printf 'Package: cah-demo\nVersion: 1.0\nArchitecture: all\nMaintainer: lab <lab@example.com>\nDescription: drift demo\n' > /tmp/pkg/DEBIAN/control
dpkg-deb --build /tmp/pkg /tmp/cah-demo.deb >/dev/null
dpkg -i /tmp/cah-demo.deb >/dev/null
# drift 2: a new account, as an attacker or a careless install might add
useradd -M -s /bin/bash cah-drift
# drift 3: a config file edited
echo "# edited" >> /etc/hosts 2>/dev/null || true
$B snapshot /tmp/after.txt
$B compare /tmp/before.txt /tmp/after.txt || true
```

**Predict.** Name the three sections of the diff that will show a change, before you run it.

**Do.** Use any Debian-family image you already have (`docker.io/library/debian:12` or `ubuntu:24.04`); the mounts are read-only and the network is off, so nothing leaves the container:

```bash
chmod +x baseline.sh drift.sh
podman run --rm --network none \
  -v "$PWD/baseline.sh:/usr/local/bin/baseline.sh:ro" \
  -v "$PWD/drift.sh:/drift.sh:ro" \
  docker.io/library/ubuntu:24.04 bash /drift.sh
```

```powershell
# PowerShell host with Podman or Docker (est.; not run): same command, with the paths written out
podman run --rm --network none -v "${PWD}/baseline.sh:/usr/local/bin/baseline.sh:ro" -v "${PWD}/drift.sh:/drift.sh:ro" docker.io/library/ubuntu:24.04 bash /drift.sh
```

**Check.** What I got, trimmed, from an Ubuntu 24.04 container on 2026-10-22 (hashes shortened):

```text
wrote /tmp/before.txt (192 lines)
wrote /tmp/after.txt (194 lines)
@@ -14,6 +14,7 @@
 ca-certificates 20260601~24.04.1
+cah-demo 1.0
 coreutils 9.4-3ubuntu6.3
@@ -159,6 +160,7 @@
 bin uid=2 shell=/usr/sbin/nologin
+cah-drift uid=1001 shell=/bin/bash
 daemon uid=1 shell=/usr/sbin/nologin
@@ -186,6 +188,6 @@
 ## config-hashes
-4c64f4...  /etc/passwd
+85c7f3...  /etc/passwd
 (and the same for /etc/group and /etc/hosts)
```

The new package appears under `packages`, the new account under `users`, and the changed files under `config-hashes`. In this container the `listening-ports`, `enabled-services` and `firewall` sections are empty or say "not here", because a container has no running init system or firewall of its own; on a real machine, a new listening port and a new enabled service are exactly what a drift looks like. That is the point: drift is a *diff*, and a diff needs a *before*.

Two lessons hide in the output. First, a baseline file is data an attacker with root could also edit, so a baseline kept only on the machine proves little; copy it somewhere else the machine cannot write to. Second, `/etc/passwd` changing is normal when you install a package that adds a service account, so a diff needs a reader: the baseline does not say whether a change is *bad*, only that it happened. Real tools do this at scale and with protected databases: see [File integrity and alerting: Tripwire, AIDE and Wazuh](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md), and [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) for what to do with the alerts.

**Undo.** `--rm` removed the container and everything in it. Delete `baseline.sh` and `drift.sh` if you do not want them.

#### The Windows variant (est.; not run)

The same idea in PowerShell, read-only. `Get-HotFix` lists installed updates; `Get-WindowsUpdateLog` merges the Windows Update trace files into one log. Both are Microsoft commands, but I did not run them and did not read their pages for this lesson, so treat the output shape as **est.**

```powershell
# baseline.ps1 (est.; not run) - read-only baseline of this Windows machine.
# Usage: .\baseline.ps1 -Out C:\Temp\baseline-before.txt
param([Parameter(Mandatory)][string]$Out)
$lines = @("# baseline $((Get-Date).ToUniversalTime().ToString('s'))Z")
$lines += "## os";             $lines += (Get-CimInstance Win32_OperatingSystem | ForEach-Object { "$($_.Caption) $($_.Version)" })
$lines += "## hotfixes";       $lines += (Get-HotFix | Sort-Object HotFixID | ForEach-Object { "$($_.HotFixID) $($_.InstalledOn)" })
$lines += "## installed-programs"
$lines += (Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
           Where-Object DisplayName | Sort-Object DisplayName | ForEach-Object { "$($_.DisplayName) $($_.DisplayVersion)" })
$lines += "## listening-ports"; $lines += (Get-NetTCPConnection -State Listen | Sort-Object LocalPort | ForEach-Object { "tcp $($_.LocalAddress):$($_.LocalPort)" })
$lines += "## local-users";    $lines += (Get-LocalUser | Sort-Object Name | ForEach-Object { "$($_.Name) enabled=$($_.Enabled)" })
$lines += "## admins";         $lines += (Get-LocalGroupMember -Group 'Administrators' | Sort-Object Name | ForEach-Object { $_.Name })
$lines += "## automatic-services"; $lines += (Get-Service | Where-Object StartType -eq 'Automatic' | Sort-Object Name | ForEach-Object { $_.Name })
$lines += "## firewall-rules"; $lines += (Get-NetFirewallRule -Enabled True | Sort-Object DisplayName | ForEach-Object { "$($_.DisplayName) $($_.Direction) $($_.Action)" })
$lines | Set-Content -Path $Out
"wrote $Out ($($lines.Count) lines)"
# Compare two baselines:
#   Compare-Object (Get-Content .\baseline-before.txt | Select-Object -Skip 1) (Get-Content .\baseline-after.txt | Select-Object -Skip 1)
```

Run it, install or remove something on a *throwaway Windows virtual machine*, run it again and compare. Do not do this on a machine you rely on.

### Exercise 4: how far behind is this box? (read-only, any machine)

Both are read-only; the first lists, it does not install. These are the same ideas as Exercise 3 on the sibling page, from the other direction.

```bash
# Debian/Ubuntu: how many packages are waiting. Does not install.
apt list --upgradable 2>/dev/null | tail -n +2 | wc -l
# RPM family (est.): list available security updates only. Does not install.
dnf updateinfo list security 2>/dev/null | head
```

```powershell
# Windows (est.): the most recent installed updates. Read-only.
Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5
```

**Check.** The number is a measurement of your cadence, not a grade. On a machine that has not refreshed its package list recently, `apt list --upgradable` can understate how many updates exist, because it only knows what the last `apt update` fetched (est.; this follows from how APT works, and the sibling page notes the same on its Exercise 3).

### Exercise 5: a staggered schedule from a host list (pure computation)

No hosts are touched; the script reads a text file and prints a table. Save as `stagger.sh`:

```bash
#!/usr/bin/env bash
# stagger.sh - build a staggered maintenance schedule from a host list, and flag collisions.
# Pure computation: it reads a text file and prints a table. It touches no host.
# Usage: ./stagger.sh HOSTFILE [START_HH:MM] [SLOT_MINUTES] [SOAK_DAYS]
# HOSTFILE lines: NAME SERVICE RING [FIXED_HH:MM]   (RING is a number: 1 = canary, higher = later)
# Rule 1: hosts of one ring get slots SLOT_MINUTES apart, starting at START.
# Rule 2: ring N starts (N-1)*SOAK_DAYS days after ring 1 (the soak time).
# A FIXED time overrides the slot (the way a real exception does).
# Exit 1 if two hosts of the same service share a day and minute (COLLISION), or any two
# hosts share a day and minute (OVERLAP, reported but only a COLLISION fails).
set -eu
[ $# -ge 1 ] || { echo "usage: $0 HOSTFILE [START] [SLOT_MIN] [SOAK_DAYS]" >&2; exit 2; }
file=$1; start=${2:-04:00}; slot=${3:-30}; soak=${4:-2}
case $slot$soak in *[!0-9]*|'') echo "slot and soak must be whole numbers" >&2; exit 2;; esac
sort -k3,3n -s "$file" | grep -v '^[[:space:]]*#' | grep -v '^[[:space:]]*$' | awk -v start="$start" -v slot="$slot" -v soak="$soak" '
function hm(m) { return sprintf("%02d:%02d", int(m/60)%24, m%60) }
BEGIN { split(start, s, ":"); base = s[1]*60 + s[2]; bad = 0
        printf "%-10s %-8s %-5s %-4s %-5s\n", "HOST", "SERVICE", "RING", "DAY", "TIME" }
{ ring = $3; if (ring != last) { idx = 0; last = ring } 
  m = base + idx*slot; day = (ring-1)*soak + int(m/1440); idx++
  t = hm(m); if (NF >= 4) { t = $4 }
  printf "%-10s %-8s %-5s +%-3d %-5s\n", $1, $2, ring, day, t
  k = day " " t; ks = k " " $2
  if (ks in seenS) { print "COLLISION: " $1 " and " seenS[ks] " (service " $2 ") both at day +" day " " t; bad = 1 }
  else if (k in seen) { print "OVERLAP:   " $1 " and " seen[k] " both at day +" day " " t }
  seenS[ks] = $1; seen[k] = $1 }
END { if (bad) exit 1; print "no collisions" }'
```

Save this host list as `hosts.txt` (invented names; the last column is optional and forces a time, the way a real exception does):

```text
# NAME SERVICE RING [FIXED_HH:MM]
lab-test-1   web   1
lab-web-1    web   2
lab-web-2    web   2
lab-db-1     db    2
lab-db-2     db    3
lab-web-3    web   3
lab-core-1   dns   4
```

**Predict.** With `./stagger.sh hosts.txt` (start 04:00, 30-minute slots, 2-day soak), on which day does the dns host go, and what time does `lab-db-1` get? Then predict what happens if you give `lab-web-2` the fixed time `04:00`.

**Do.**

```bash
chmod +x stagger.sh
./stagger.sh hosts.txt; echo "exit=$?"
sed -i 's/^lab-web-2    web   2/lab-web-2    web   2 04:00/' hosts.txt
./stagger.sh hosts.txt; echo "exit=$?"
```

```powershell
# PowerShell (est.; not run): the same rules, in one pipeline. Needs hosts.txt as above.
$start = 4*60; $slot = 30; $soak = 2; $last = $null; $seen = @{}; $bad = $false
Get-Content hosts.txt | Where-Object { $_ -notmatch '^\s*(#|$)' } | ForEach-Object {
  $f = -split $_; [pscustomobject]@{ Name=$f[0]; Service=$f[1]; Ring=[int]$f[2]; Fixed=$f[3] }
} | Sort-Object Ring | ForEach-Object {
  if ($_.Ring -ne $last) { $idx = 0; $last = $_.Ring }
  $m = $start + $idx*$slot; $idx++; $day = ($_.Ring-1)*$soak + [math]::Floor($m/1440)
  $t = if ($_.Fixed) { $_.Fixed } else { '{0:00}:{1:00}' -f ([math]::Floor($m/60) % 24), ($m % 60) }
  $key = "$day $t $($_.Service)"
  if ($seen.ContainsKey($key)) { "COLLISION: $($_.Name) and $($seen[$key]) at day +$day $t"; $bad = $true }
  $seen[$key] = $_.Name
  "{0,-10} {1,-8} ring {2} day +{3} {4}" -f $_.Name, $_.Service, $_.Ring, $day, $t
}
if ($bad) { exit 1 }
```

**Check.** I ran the Bash version on 2026-10-22. First run: the dns host is on day +6 at 04:00 (rings are two days apart, so ring 4 is day +6), `lab-db-1` is at 05:00 on day +2 (third slot of ring 2), and the last line is `no collisions`, exit 0. Second run: `lab-web-2` and `lab-web-1` are both web hosts at day +2 04:00, so the script prints `COLLISION: lab-web-2 and lab-web-1 (service web) both at day +2 04:00` and exits 1. A same-minute pair of **different** services is reported as `OVERLAP` and does not fail the script, because two unrelated services rebooting together is sometimes acceptable; you decide. The script cannot know which hosts depend on which: that knowledge is the part only you have. Try putting both databases in ring 2 and see what the schedule would do to them.

**Undo.** Delete the two files. Nothing else changed.

## Optional: apply the order on a real droplet (your own account)

Everything above is free. This path uses **your own** DigitalOcean account and **your own** provider bill, and is optional. I did not run it for this page.

**Cost and teardown first.** The smallest regular size in [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json), `s-1vcpu-512mb-10gb`, is **$4 a month** (retrieved 2026-10-21; see [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md)). Billing is by time used, so a few hours is a small fraction of that (est.; the sibling page records DigitalOcean's "billed per second" statement as read on 2026-10-21). A powered-off droplet is still billed; **destroy** it when you finish, and prove it is gone with the [teardown checklist](Teardown-Checklist.md). Backups are off in this path.

**Steps, without repeating the other lessons.** Create the cloud firewall first and attach it, so the new machine is never open to the internet while it updates ([DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md)); create the droplet with `user_data` like the one below; then log in through the access method your lesson set up ([Build it from zero](Build-It-From-Zero-Accounts-to-Stage-1.md) and [Droplet hardening](Droplet-Hardening.md) show the piece-by-piece versions). A cloud-config that follows the order, with no secrets in it:

```yaml
#cloud-config
# Step 1: update everything now, then switch on unattended security updates.
package_update: true
package_upgrade: true
packages:
  - unattended-upgrades
write_files:
  - path: /etc/apt/apt.conf.d/20auto-upgrades
    permissions: "0644"
    content: |
      APT::Periodic::Update-Package-Lists "1";
      APT::Periodic::Unattended-Upgrade "1";
# Step 2 (by hand after first login): copy baseline.sh over and run
#   sudo ./baseline.sh snapshot ~/baseline-day0.txt
# then copy the file OFF the machine. Steps 3 and 4 come after.
```

Check on the machine: `systemctl status apt-daily-upgrade.timer` and `sudo unattended-upgrade --dry-run --debug` (est.; not run). `cloud-init status --wait` tells you the first-boot work finished.

## Build, break, detect, evade, defend (the local loop)

All of this is in your own lab.

**Build.** A lab web server with a deliberately old PHP version is the classic example, but you do not need to build one to see the shape. Take the Debian-family container from Exercise 3 and record what it runs. Start the loop with the question: *what is the oldest thing on this machine that an outsider can reach?*

**Break (shown, not run).** Picture a public web service running a PHP below the fixed versions on the page above. An outsider who can reach it and knows the flaw can try the published attack. I do not describe the attack here and nothing on this page performs one. The break is the *window*: the days between the fix existing and your machine having it.

**Detect.** Find out your own version before an outsider does. For software you installed from the distribution: `php -v`, `dpkg-query -W 'php*'` or `rpm -q php`. For a service you run in your own lab, ask it from the outside of the container, on loopback only: `nmap -sV 127.0.0.1 -p 8080` (est.; `nmap` is covered in [Security tools basics](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md); scan only your own lab, never a machine you do not own). The scan guesses a version from what the service says about itself; read its answer as a hint.

**Evade.** The tempting fix is to hide the version: tell the web server not to announce its version, remove a banner, change a header. It makes your own detection step harder and the attacker's guess slightly harder. It is **security through obscurity**: relying on the attacker not knowing a fact, when the flaw is still there. The maintainer's position is that this is a flawed, one-trick idea, and the PHP advisory supports it from the other side: it says changing `error_reporting`, using `@`, or disabling `display_errors` or `log_errors` "does not protect against this vulnerability" ([GHSA-6wmf-4rv5-p3rp](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp), read 2026-10-22). Hiding is not forbidden; it is not a substitute. An attacker can also test for the flaw without reading your banner.

**Defend.** A patch cadence (security updates daily, full update in a window), the automatic mechanism, the baseline so you can answer "what version, where", a way to restart services after a library changes, a canary and a rollback. Then verify: run the version command again and see the number change.

### Flip the board

You are the attacker. You scan a range of addresses (you are an authorized tester, on a range you own) and list the versions. Which would you pick first: the one whose banner says a recent version, or the one that says nothing? The one that says nothing is more interesting to you, not less, because you must test it; and the old version is a gift. A defender who hides banners but does not patch has handed you the work of testing and kept the flaw.

Now be the defender with ten servers. One is a router that does not update itself, one runs the PHP in a container, one runs a database, and one was set up three years ago by a colleague who left. Which has the oldest software that is reachable? Your baselines answer this; your memory does not. The same lesson from the other side: the attacker's reconnaissance is a baseline of *you*; yours should be at least as good.

## Threat model: the update channel itself

The update mechanism is a high-trust path: it runs as root, and it installs code. That makes it an attractive target. Assets: the machine, every credential on it, the integrity of what gets installed. Actors: a network attacker, a compromised or malicious mirror or repository, someone who steals a signing key, a malicious package maintainer.

| Threat | What it means | Mitigation | Verify |
|---|---|---|---|
| Compromised mirror or network attacker | Someone serves you altered packages | Packages are signed by the distribution's key and the package manager checks signatures; use HTTPS where offered (est. for the details: I did not read each distribution's signing documentation for this page) | `apt-key`/keyring files exist; `apt update` would fail on a bad signature (est.) |
| Downgrade or replay | Someone serves you an old, vulnerable package list so you "update" to a flawed version | Signed, dated repository metadata that the client checks for freshness (est.; mechanism differs by tool) | Compare installed versions against the vendor's advisory page after an update |
| Stolen or rotated signing key | A third-party repository's key is replaced or stolen | Pin the key and check its fingerprint, as this project does for the Twingate repository ([stage 1 guide](../stages/01-access.md): "checks its fingerprint against the one pinned in the template"); update the pin only after confirming with the vendor | The fingerprint in your config equals the vendor's published one |
| Supply chain (a bad update from a trusted source) | The legitimate vendor ships a bad or malicious update | Stage on a copy, canary, hold critical packages, watch for unexpected diffs against your baseline | Baseline diff after the window shows only the packages you expected |
| The updater is the attack | A tool that runs as root on a timer | Keep the allowed-origins list short; every added origin is a trusted publisher | Review the origins list; a baseline records `20auto-upgrades` and its hash |
| Automatic reboot at a bad time | A reboot interrupts a job or a person | Maintenance window; `Automatic-Reboot-WithUsers` is a choice, not a default (this project sets it to true on its connectors on purpose) | Logs show the reboot happened inside the window |

Residual risk: you trust your vendor. The point of the baseline and the staged rollout is to notice if that trust was misplaced, not to remove it.

## Checkpoint

- Name the four steps of the order and say why updates come before the baseline.
- Why does an Amazon Linux 2023 instance need a step before it is current?
- `dnf-automatic` is installed and nothing installs. What setting, and what timer, do you check?
- A host has perfect automatic updates and still runs a vulnerable PHP. Give two ways that happens.
- What does a live patch fix, and what does it not?
- Give three things you do before an update to make a bad one survivable.
- Why do two redundant servers get different maintenance windows, and what is a soak time?
- Why is hiding a banner not a defense, in one sentence?
- Why is a baseline file stored only on the machine weak evidence?

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| Updates "are on" and nothing changes | The tool is installed but not enabled, or notify-only | The timer or the periodic setting, and the tool's log |
| The package updated but the old process still runs | The service was not restarted | `zypper ps` (SUSE), a restart, or a reboot; then the version |
| A repository you added never updates | It is not in the allowed origins | The origins list; a separate cron or timer |
| A container is old on a patched host | Images do not update themselves | Image creation date; rebuild and recreate |
| Auto reboot hit a busy hour | No window set | The reboot time setting |
| Baseline diff is huge and unreadable | Baseline taken after the application and its churn | Take it right after step 1; take a second after step 3 |
| Baseline "proves" the machine is clean | The file lived on the machine | Copy it off; it records state, it does not judge it |

## Claims register

All read-only requests; retrieved **2026-10-22**. "Read" means I read the passage; "read in part" means I read only the passage named, not the whole page.

| Claim | Source | Status |
|---|---|---|
| PHP 8.5.12, 8.4.27, 8.3.36, 8.2.35 are security releases fixing two critical unauthenticated-RCE flaws (CVE-2026-109618, CVE-2026-109619); "no complete mitigations, updating is the only safe choice"; distributions and LTS vendors received patches in advance; 8.1 and older receive no updates from the project | [php.net](https://www.php.net/) | Read |
| Two advisories published 21 October 2026, Critical, affected below the four fixed versions; error-setting changes "do not protect"; mod_php highest risk (as the sibling page records) | [GHSA-w8hw-w9fx-j79w](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w), [GHSA-6wmf-4rv5-p3rp](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp) | Read the header, patched versions and the error-setting passage; mod_php ranking from the advisory text and the sibling page |
| Ubuntu applies security updates via `unattended-upgrades`, installed by default; default origins; `Automatic-Reboot` default false; reboots "can be very disruptive"; a newly added repository is not considered | [Ubuntu Server: automatic updates](https://documentation.ubuntu.com/server/how-to/software/automatic-updates/) | Read |
| `--dry-run` simulates; `--debug` logs to `/var/log/unattended-upgrades/unattended-upgrades.log`; backend for `APT::Periodic::Unattended-Upgrade` | [`unattended-upgrade(8)`](https://manpages.debian.org/unstable/unattended-upgrades/unattended-upgrade.8.en.html) | Read |
| `dnf-automatic`: `apply_updates` default False; `upgrade_type` default or security; `reboot` never/when-changed/when-needed; the three timer units override the config | [DNF Automatic](https://dnf.readthedocs.io/en/latest/automatic.html) | Read |
| AL2023: images locked to a repository version; no automatic critical/important security updates at launch; recommends all updates in a release; kernel needs a reboot; live patching may postpone | [Deterministic upgrades](https://docs.aws.amazon.com/linux/al2023/ug/deterministic-upgrades.html), [Managing updates](https://docs.aws.amazon.com/linux/al2023/ug/managing-repos-os-updates.html) | Read |
| SUSE: `zypper patch` installs relevant patches; buggy patches are retracted and listed by `zypper lp --all`; `zypper ps` lists processes using deleted files. Unattended scheduling on SLES | [SLES zypper chapter](https://documentation.suse.com/sles/15-SP6/html/SLES-all/cha-sw-cl.html) | Read in part; scheduling **not read (est.)** |
| Windows: update policies through Group Policy or MDM such as Intune; quality updates usually the second Tuesday; pause up to 35 days; testing on a subset first. Consumer defaults | [Windows Update policies](https://learn.microsoft.com/en-us/windows/deployment/update/waas-manage-updates-wufb), [configure](https://learn.microsoft.com/en-us/windows/deployment/update/waas-configure-wufb) | Read in part; consumer defaults **not read (est.)** |
| macOS: separate switches for download, install macOS updates, and Security Responses and system files | [Apple: Get macOS updates](https://support.apple.com/guide/mac-help/get-macos-updates-mchlpx1065/mac) | Read the passage |
| FreeBSD: `freebsd-update` binary security/errata updates; the `@daily ... freebsd-update cron` entry downloads but does not apply; `freebsd-update rollback`; `freebsd-version -k` vs `uname -r` | [FreeBSD Handbook](https://docs.freebsd.org/en/books/handbook/cutting-edge/) | Read |
| pfSense: upgrade from GUI or console; firewall must be online; backup first; ZFS boot environments | [Netgate upgrade guide](https://docs.netgate.com/pfsense/en/latest/install/upgrade-guide.html) | Read in part (contents and headings) |
| OPNsense: two major releases a year, minor roughly every two weeks, minor updates from System, Firmware, Status, major updates offline | [OPNsense: Updates](https://docs.opnsense.org/manual/updates.html) | Read |
| Canonical Livepatch patches the kernel between maintenance windows while running, with Ubuntu Pro; kpatch patches a running kernel without rebooting | [Livepatch](https://ubuntu.com/security/livepatch), [kpatch](https://github.com/dynup/kpatch) | Read the descriptions only |
| KernelCare | tuxcare.com | **Not read** (request refused); no claim made |
| Docker images are immutable; rebuild often | [Docker build best practices](https://docs.docker.com/build/building/best-practices/) | Read |
| Dependabot maintains dependencies | [About Dependabot version updates](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/about-dependabot-version-updates) | Read the first sentence only; supported ecosystems **not read** |
| Attackers target vulnerabilities for months or years after updates exist; CISA recommends automatic updates where available | [CISA: Understanding patches and software updates](https://www.cisa.gov/news-events/news/understanding-patches-and-software-updates) | Read |
| How fast internet-wide scanners find a new public service | none | **No source read; no figure given** |
| Patch Gremlin: notifications on top of `unattended-upgrades` and `dnf-automatic`; host OS only | [Patch Gremlin README](https://github.com/ChiefGyk3D/Patch-Gremlin) (page returns 200) | README as described on the sibling page, read 2026-10-22; code not read |
| The project's cloud-init: `package_update`/`package_upgrade`, unattended-upgrades with security origins, reboot time, weekly connector cron | `modules/twingate-bootstrap/cloud-init.yaml.tftpl`, [stage 1 guide](../stages/01-access.md) | Read in this repository |
| Edge design: pinned by version and checksum, unattended upgrades, scheduled rebuild, a test for unpinned packages | [edge DMZ design](../superpowers/specs/2026-10-19-edge-dmz-design.md) | Read; it is a draft and the test's existence is **not verified** |
| Baseline script and drift demo output | Exercise 3 | **Observed** 2026-10-22, Ubuntu 24.04 container, rootless Podman, no network |
| Connector a reboots 04:00, b 05:00; weekly connector update Sundays 04:30 and 05:30; `cron.weekly` would fire on both at once | [Droplet hardening: updates](Droplet-Hardening.md#updates), `modules/twingate-bootstrap/cloud-init.yaml.tftpl` comment | Read in this repository |
| Edge droplets: one slot per edge service stack, a variable, before the connectors' windows, a test that no two droplets share a minute | Maintainer ruling 2026-10-22 as given to me; [edge DMZ design](../superpowers/specs/2026-10-19-edge-dmz-design.md) says the reboot window must not collide with the connectors' | Plan only; the test and the variable are **not built and not found in the repository** |
| Autopatch groups; Test and Last rings present by default | [Autopatch groups overview](https://learn.microsoft.com/en-us/windows/deployment/windows-autopatch/deploy/windows-autopatch-groups-overview) | Read in part |
| Intune update rings: deferrals, restarts, deadlines; commonly used for test, pilot, production stages | [Intune update rings](https://learn.microsoft.com/en-us/mem/intune/protect/windows-10-update-rings) | Read in part |
| WSUS computer groups | Microsoft page (404 on the URL tried) | **Not read (est.)** |
| Systems Manager patch groups (not used by patch policies) and Maintenance Windows | [Patch groups](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-patch-groups.html), [Maintenance Windows](https://docs.aws.amazon.com/systems-manager/latest/userguide/maintenance-windows.html) | Read in part |
| Ansible `serial` batches by number or percentage | [Playbook strategies](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_strategies.html) | Read in part |
| Kubernetes rolling updates; PodDisruptionBudget limits concurrent disruptions | [Rolling updates](https://kubernetes.io/docs/tutorials/kubernetes-basics/update/update-intro/), [PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/) | Read in part; node pools **not read (est.)** |
| Ring design and soak times in the table | General practice | **est.**, not a vendor rule |
| Stagger script output | Exercise 5 | **Observed** 2026-10-22 (Bash); PowerShell **not run** |
| `s-1vcpu-512mb-10gb` is $4 a month | [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json) (retrieved 2026-10-21) | Read |

**Not verified, plainly:** the `unattended-upgrades` and `dnf-automatic` exercises (Exercises 1 and 2), the PowerShell stagger pipeline, WSUS groups, managed-Kubernetes node-pool maintenance, the reboot-storm and capacity points (general practice), including that the images named pull and behave as shown; the entire PowerShell and Windows track; Windows and SUSE consumer or scheduling defaults; the commands `apt-mark hold`, `dnf versionlock`, `fwupd`, `dnf updateinfo` and `nmap -sV`; macOS behavior beyond the Apple passage; whether the edge design's unpinned-package test exists; the optional droplet path from start to finish; Debian's own default for `unattended-upgrades` (I did not read Debian's documentation, so the Debian statement is est.); and any claim about how quickly scanners find new services.
