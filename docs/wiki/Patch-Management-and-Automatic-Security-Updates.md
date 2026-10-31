# Patch management and automatic security updates, with alerting and logging

> **Status: partly run, mostly written from reading.** On **2026-10-30** I ran three things inside throwaway Ubuntu 24.04.5 containers (rootless Podman, `unattended-upgrades` 2.9.1+nmu4ubuntu1, network on): the dry run in Exercise 1, how a second configuration file changes the list of allowed origins (measured, in "Configure it"), and the triage script in Exercise 2 against both hand-made logs and the dry-run log. Everything else was **not run** and is written from reading: the RPM-family tool, plain Debian, the daily timers firing on a real host, a real automatic reboot, every rollback step, and [Patch Gremlin](https://github.com/ChiefGyk3D/Patch-Gremlin) (I read its README on the same day, not its code, and installed nothing). The vendor pages were read on **2026-10-30**; each is in the [claims register](#claims-register) with what I took from it. Where a statement is general knowledge and not on a page I read, the text says **est.** (estimate). The staging stack in the "Testing a patch" section is planned and not built.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

**Prerequisites:** [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) (why updates come first, the table of mechanisms for every system, and the staggered windows) and [Backups, recovery and patching](Backups-Recovery-and-Patching.md) (cadence, emergency patches, and a backup you have restored). [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) helps with the alerting half. To run the exercises you need Podman or Docker on a Linux or macOS computer; they cost nothing and touch no cloud.

Those two pages say *that* you should patch and give the vocabulary. This page is about the machinery on one Debian or Ubuntu host and the part people leave out: how you find out that it worked, that it broke, or that it quietly stopped.

## What you will be able to do

- Say what `unattended-upgrades` does in one daily run, and which files and timers control it.
- Read its configuration and say which repositories it will and will not take updates from.
- Name where each kind of update result is logged.
- List the four conditions that deserve an alert and say which one people miss.
- Choose a reboot policy and say what it costs.
- Describe how a patch is tested before production, and how you go back when one goes wrong.
- Say what automatic updating does not cover.
- Say what Patch Gremlin does and does not do, from its README.

## Why patch automatically

A vendor fixes a flaw and publishes the fix. From that moment the flaw is public, and the only question is how long your machine stays unfixed. Attackers do not need to be clever: they scan for the known-bad version. The time between "fix published" and "fix installed on your host" is the window they use. A person who patches "when I remember" leaves that window open for weeks (est.); a daily automatic job closes it in about a day.

The price is real. An update can break a service, and a reboot can fail to come back. Nothing in this lesson removes that price; it makes it smaller and visible. The rest of the page is the four habits that do it: **limit what is automatic** (security fixes only), **make the result loud** (logs and alerts), **try it somewhere cheap first** (staging and a canary), and **know the way back** (rollback). The comparison to make in writing is the one [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md#the-real-risk-a-bad-update-breaks-something) makes: the risk of an update breaking something against the risk of leaving a known flaw open. "It might break" is a reason for these habits, not for staying unpatched.

## What unattended-upgrades does

**`unattended-upgrades`** is a package for Debian and Ubuntu. Ubuntu's server documentation says Ubuntu "will apply security updates automatically, without user interaction", through this package, "installed by default". It does the equivalent of `apt update` followed by `apt upgrade`: it refreshes the package lists, checks which upgrades are available, and applies those from the allowed repositories. By default it runs once a day. Its man page calls it the backend for `APT::Periodic::Unattended-Upgrade`, run by APT's systemd service `apt-daily-upgrade.service` or from cron.

Three pieces make it go:

1. **Two systemd timers**, `apt-daily.timer` (downloads) and `apt-daily-upgrade.timer` (upgrades), start the work at a scheduled time **plus a random delay**. The Debian wiki explains the delay: before it existed, Debian's servers got "massive traffic spikes for a few seconds a day", so if you move the time, keep a delay of at least an hour. If the machine was off at the scheduled time, the timer fires at the next start, which is why a freshly booted VM often upgrades itself at once (Ubuntu page). The setting that stops that catch-up is `Persistent=false` in a timer override.
2. **`/etc/apt/apt.conf.d/20auto-upgrades`** switches the work on. Two lines, each a number of days; `0` disables, `1` is daily, `2` is every other day:
   ```text
   APT::Periodic::Update-Package-Lists "1";
   APT::Periodic::Unattended-Upgrade "1";
   ```
3. **`/etc/apt/apt.conf.d/50unattended-upgrades`** says *what* it may do: which repositories, which packages to skip, whether to reboot, whether to send mail.

Plain Debian differs from Ubuntu in one respect worth knowing. The Debian wiki says "most versions of Debian install unattended-upgrades with fairly conservative settings" but that your system "might not have installed the package at all, or might have installed it but disabled it altogether", and tells you to check with `sudo dpkg-reconfigure unattended-upgrades`. Its example configuration works on a copy named `52unattended-upgrades-local` and refers to an `Origins-Pattern` section, where Ubuntu's page documents `Allowed-Origins`. Read the page for your release and look at your own 50 file; do not assume the two are the same (I ran only Ubuntu 24.04.5).

The same job on the RPM family is `dnf-automatic`. It is not set up for you: per its documentation, `apply_updates` defaults to `False` (it downloads and reports), `upgrade_type` can be `security`, and `reboot` is `never`, `when-changed` or `when-needed`. The table in [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md#what-automatic-updates-means-system-by-system) lines up every mechanism; this page stays on Debian and Ubuntu and notes the RPM equivalent where it matters.

## Configure it

Do not edit the 50 file. Put your settings in a file that sorts after it, as the Debian wiki suggests (it names `52unattended-upgrades-local`), so a package upgrade of `unattended-upgrades` cannot overwrite them. This project does the same, in the order its stage guides state (update and switch on automatic security updates, write the baseline, switch on the hardening, install the application last): its bootstrap writes `52cah-unattended-upgrades` next to `20auto-upgrades` ([`modules/twingate-bootstrap/cloud-init.yaml.tftpl`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/modules/twingate-bootstrap/cloud-init.yaml.tftpl), read in this repository).

| Option | What it does | Default or note | Source |
|---|---|---|---|
| `Unattended-Upgrade::Allowed-Origins` | Repositories updates may come from. Written `"origin:suite"`. | The release itself, its `-security` pocket, and Ubuntu's ESM (Expanded Security Maintenance) pockets where they exist. `-updates` is commented out. | Ubuntu page; confirmed in the container |
| `Unattended-Upgrade::Package-Blacklist` | Packages never upgraded automatically; a list of Python regular expressions, matched as if anchored at the start. `"libc6$"` matches `libc6` and not `glibc6`. | Empty. Blocking a package can block updates that depend on it. | Ubuntu page |
| `Unattended-Upgrade::Mail`, `MailReport` | Send a report to an address. `MailReport` is `always`, `only-on-error` or `on-change`. | No mail unless `Mail` is set; `on-change` by default. Needs a mail program on the host. | Ubuntu page |
| `Unattended-Upgrade::Automatic-Reboot` | Reboot at the end of a run if an update asks for it. | `false` | Ubuntu page |
| `Unattended-Upgrade::Automatic-Reboot-WithUsers` | Reboot even if someone is logged in. | `true` (only matters when the line above is `true`) | Ubuntu page |
| `Unattended-Upgrade::Automatic-Reboot-Time` | When to reboot. Passed as is to `shutdown(8)`: `now`, `hh:mm` in the machine's local time, or `+m` minutes. | `now` | Ubuntu page |
| `Unattended-Upgrade::OnlyOnACPower` | A laptop setting: by default the run is skipped on battery. | The Debian wiki warns the skipped run produces no notification. | Debian wiki |

**Which repositories it trusts is the most important line.** Ubuntu's page is blunt: adding another package repository "WILL NOT make unattended-upgrades consider it for updates". That is a safety feature (a third-party repository is not auto-installed as root) and a gap (the software from that repository is never updated automatically). To include one, add its `Origin` from its `InRelease` file to the list. Take the gap seriously: the Twingate connector comes from Twingate's own repository, so it is not covered by the security origins; this project patches it with its own weekly cron job ([Droplet hardening: updates](Droplet-Hardening.md#updates)).

**A second file adds to a list; it does not replace it.** I measured this on 2026-10-30 in an Ubuntu 24.04.5 container. With the stock 50 file in place, I added a 52 file that named only the `-security` origin, and asked `apt-config dump` for the result. The output held the four stock origins **and** the security origin again. The tool's own log then listed the five. So a 52 file that restates a shorter list does not restrict anything; it only adds. To actually replace the list, put `#clear Unattended-Upgrade::Allowed-Origins;` on the first line of your file; with that line the dump showed an empty entry followed by only the origin I wrote (also measured, one run). Why it matters: this project's 52 file lists the security origins, and the stock list still holds the base release pocket. That pocket carries the packages from release day, not later updates, so the practical difference is small (est.), but a page that says "only security origins" should be read as "at least the security origins".

A correct, minimal local file for a server that wants security fixes only and a nightly reboot window looks like this (the same shape as this project's):

```text
// /etc/apt/apt.conf.d/52local-updates
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";
Unattended-Upgrade::Automatic-Reboot-WithUsers "true";
Unattended-Upgrade::Mail "root";
Unattended-Upgrade::MailReport "on-change";
```

This is an example, not a recommendation for your host. Every line has a cost: `WithUsers "true"` will reboot a machine someone is working on, and `Mail` does nothing until a mail program is installed. The Debian wiki's debug command checks your file without waiting for the timer: `sudo unattended-upgrade -d` (and `--dry-run` simulates).

## Where the results are logged

Know these before you need them. All paths are Debian or Ubuntu; the first two I saw created by a run in the container.

| What you want to know | Where | Source |
|---|---|---|
| What the tool decided and did, with a timestamp and a level (`INFO`, `WARNING`, `ERROR`, `DEBUG`): the allowed origins, "Packages that will be upgraded", "All upgrades installed", reboot messages | `/var/log/unattended-upgrades/unattended-upgrades.log` | `unattended-upgrade(8)`; saw it in the container |
| What `dpkg` printed while installing | `/var/log/unattended-upgrades/unattended-upgrades-dpkg.log` | `unattended-upgrade(8)`; saw it in the container |
| Every package change on the host, by any tool, by hand or automatic | `/var/log/dpkg.log` | Debian wiki |
| Whether the timer and its service ran, and what the service wrote to the journal | `journalctl -u apt-daily-upgrade.service` and `systemctl list-timers apt-daily*` | est.: standard systemd commands; the unit name is from the man page, the commands were not run |
| Whether a reboot is waiting | the file `/var/run/reboot-required` | Ubuntu page (the mechanism is described, the path appears in its log excerpt: "Found /var/run/reboot-required, rebooting") |
| A mailed report of one run | the address in `Unattended-Upgrade::Mail`, subject like "unattended-upgrades result for <host>: SUCCESS" | Ubuntu page |
| Patch Gremlin's own record | `journalctl -t patch-gremlin`, the file `/var/lib/patch-gremlin/state` | Patch Gremlin README |

One consequence: **the log file only helps you if you read it, and it lives on the host.** If a host is compromised or destroyed, its log goes with it. Shipping it to a collector is the point of [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md); this project's droplets do not ship these logs yet (audit logging is planned for stage 2, see [Droplet hardening](Droplet-Hardening.md)).

Log files rotate (est.), so "the newest run" is not "the whole file". The exercise below handles that.

## What deserves an alert

An alert is a message to a person who should do something. Four conditions earn one. Everything else is a log line.

| Condition | Why a person must hear about it | How you can tell | Urgency |
|---|---|---|---|
| **A security update was applied** | It is what you wanted, and it is also a change on a production host. You want a record that tomorrow's odd behavior has a cause. | "Packages that will be upgraded" followed by "All upgrades installed" in the log; the mail with `on-change`; Patch Gremlin's notification | Notice: no one is paged; it is read in the morning |
| **A reboot is required** | A kernel or C library fix does nothing until the reboot. A host that has been waiting a week is a host with a known flaw. | `/var/run/reboot-required` exists; the log says it is rebooting | Warning: fine if your window handles it, not fine after a few days |
| **An update failed** | A half-applied update can leave a package broken, and the next run may fail the same way. | An `ERROR` line in the newest run; `only-on-error` mail | Page during working hours; the fix is a person looking |
| **The host stopped updating** | Silence looks like success. A host with a stuck lock, a full disk, a broken repository, a disabled timer or a turned-off job logs *nothing* and sends *nothing*. | The newest run is too old; no run at all | The one most worth waking someone for, because nothing else will tell you |

The fourth row is the point of this section. The first three are events and every tool reports events. The fourth is the **absence** of an event, and a tool that reports only events cannot report it. You need something that notices a number going stale: a "last successful run" age compared with a limit. [Grafana basics](Grafana-Basics-From-a-Blank-Page.md) has the same trap in its no-data setting, and the [synthetic lab](Lab-Demo-Monitoring-Stack.md) has a rule that counts expected targets for the same reason.

**How the alert reaches a person** is a separate decision from what triggers it, and each hop can fail silently:

1. **Detection** on the host or in a collector: a script like the one in Exercise 2, a mail report, or Patch Gremlin.
2. **Delivery** to somewhere a person looks: email, or a chat webhook. Test it with a real message; a webhook that was revoked fails without telling anyone.
3. **Routing**: notices to a quiet channel, failures and staleness to the one that pages. If every run posts a message, people mute the channel, and the mute hides the failure.
4. **A second path for the alert path itself.** If the notifier is the only thing that says the host stopped updating, who says the notifier stopped? A heartbeat or a central check that reads the last-run time from outside the host is the usual answer (est.).

### Patch Gremlin, as the worked example

Patch Gremlin is the maintainer's own project, public at [github.com/ChiefGyk3D/Patch-Gremlin](https://github.com/ChiefGyk3D/Patch-Gremlin). Everything here comes from its README as I read it on 2026-10-30; I did not read its code, install it, or run its tests.

What the README says it is: automated update notifications for Debian and RHEL-based systems. It integrates with `unattended-upgrades` on Debian, Ubuntu and Raspbian, and with `dnf-automatic` on RHEL, Rocky, Alma, Amazon Linux and Fedora, and sends a notification when security updates are installed. Destinations it lists: Discord, Microsoft Teams, Slack, Matrix, ntfy, Gotify, and a generic JSON webhook, in any combination.

How it maps onto the four conditions:

| Condition | What the README describes |
|---|---|
| Update applied | It reports a run as "N packages updated", "still pending (some security)" or "up to date", with the package names (the number of names listed is a setting). It hooks the upgrade service itself (`ExecStartPost` on `apt-daily-upgrade.service` or `dnf-automatic.service`) so the message describes the run that just finished. |
| Reboot required | An optional auto-reboot, with a reboot window it derives from your update time. The setup prompts for it and recommends it; it reboots after kernel or critical library updates and, when enabled, even with users logged in (the README's words). I found no separate "reboot pending" notification in the part I read. |
| Update failed | It logs success or failure of its own delivery to the system log and retries a failed send. Whether an `unattended-upgrades` `ERROR` becomes its own message I did not find stated. |
| Host stopped updating | A "heartbeat" report, **disabled by default** (`ENABLE_HEARTBEAT=true` turns it on), scheduled two hours after the upgrade window, for the days when no upgrade ran. A health check that exits 0, 1 or 2, a Nagios/Icinga check whose sample output shows `last_run_age_hours`, and a Prometheus exporter with a `patch_gremlin_last_run_timestamp_seconds` metric. |

The last row is the useful one. The Prometheus metric is a last-run time, so the stale-host rule is one comparison. As an example only (not run, no Prometheus here; the 36-hour limit is my choice, a day plus a margin):

```text
time() - patch_gremlin_last_run_timestamp_seconds > 36 * 3600
```

What to remember about it:

- **It reports what the host's package manager did. It does not look inside a container image or at your application's own dependencies.** [Backups, recovery and patching](Backups-Recovery-and-Patching.md#what-does-each-tool-actually-patch) has the table.
- **It is another thing that holds a secret** (a webhook address or a token). The README says it keeps them in a root-only mode 600 file or in Doppler, the same rule as [Secrets from day one](Secrets-From-Day-One.md). A webhook URL in a chat channel is a password for posting to that channel.
- **It writes configuration into the same files this lesson shows** (the README's file list names `/etc/apt/apt.conf.d/50unattended-upgrades`, a drop-in on the upgrade timer for the schedule, and `20auto-upgrades`). If you manage those with a configuration tool or cloud-init, give one of them ownership, or each will undo the other (est.).
- **The README describes the trigger in two places that read differently**: the Configuration section says a hook on the upgrade service, the How It Works section says an APT post-invoke hook. The file list shows the service drop-in. I cannot say which is current without reading the code.
- **License**: the README says dual MPL-2.0 or commercial; read it before reusing it in a company.
- The README's own notice says version 2.0 changed how notifications are triggered and fixed a credential-exposure issue in 1.x; if you find an older copy, update it first.

This project does not install it on its droplets. It is the example of the alert path, not part of the reference environment.

## Reboot handling

Some updates cannot take effect until the machine restarts. The kernel is the main one; Ubuntu's page says an update can "let the system know that a reboot is recommended" and that `unattended-upgrades` "can benefit from this mechanism and optionally reboot". It also says "Reboots can be very disruptive, especially if the system fails to come back." Your policy is one of three.

| Policy | How | Good for | Cost |
|---|---|---|---|
| **Never automatic** (the default) | `Automatic-Reboot "false"`; you watch for the reboot-required alert | Machines where a person owns each restart: a database, a router, a desktop | The flaw stays open until a person acts. Alert on how long the flag has been set. |
| **Automatic in a window** | `Automatic-Reboot "true"` and `Automatic-Reboot-Time "hh:mm"` | Stateless or redundant machines; this project's droplets | A reboot at that time, whether or not you are watching. If the machine fails to come back, you find out at that time. |
| **Replace, do not patch** | Build a new instance from a newer image and destroy the old one | Cloud machines designed to be recreated | You need the pipeline for it. Ubuntu's page notes the exposure is the same: "the update still has to happen somewhere, it's just not at runtime." |

Three details that bite:

- **The time is local to the machine.** `hh:mm` is read in the machine's time zone. This project sets the droplet clock from its `timezone` setting (default `America/New_York`), so its times are Eastern ([Droplet hardening: updates](Droplet-Hardening.md#updates)). A machine left on UTC reboots at a different hour than you meant.
- **Not everything needs a reboot, but it needs a restart.** After a library update, running services keep the old copy in memory. The package `needrestart`, which `unattended-upgrades` calls, restarts those services; the Ubuntu page says that starting with Ubuntu 24.04 LTS it does so automatically by default, except for a built-in list. You can set `$nrconf{restart}` to `'l'` (list only) or exclude one critical service with `$nrconf{override_rc}`, in a file under `/etc/needrestart/conf.d/`, and restart it in a window. The Debian wiki points at the same package for processes that need restarting without a reboot.
- **Never reboot the redundant machines together.** This project has two Twingate connectors so that one can be down; they reboot an hour apart (04:00 and 05:00 Eastern by default), and a validation in the access stack refuses two reboot times less than 60 minutes apart ([`stacks/10-access/variables.tf`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/stacks/10-access/variables.tf), read in this repository). The planned edge host takes one of five 30-minute slots from 01:00 to 03:00, each service its own, listed in `modules/edge-host/reboot-slots.json`, before the connectors' windows. [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md#stagger-your-maintenance-windows) explains why the stagger is also your canary.

With `dnf-automatic`, the equivalent is `reboot = when-needed`, and the command defaults to `shutdown -r +5 'Rebooting after applying package updates'`: a five-minute warning, which you can shorten (DNF Automatic page).

## Testing a patch before production

Automatic security updates are the one class you let reach production without a human, so the testing happens in two other places.

1. **The upstream test.** The vendor's security pocket holds small, targeted fixes. That is why "security only" is the automatic default: the change is small, and the vendor has already tested it. A full update (`-updates`) is bigger and belongs in a window with a person watching (First hour page).
2. **A dry run on the host.** `sudo unattended-upgrade --dry-run` (add `-d` for detail) shows what it *would* install. It does not prove the new versions work; it proves the configuration reads and the origins match. Exercise 1.
3. **A canary.** The first machine in the window is the test for the rest. A staggered schedule gives you one by accident; naming one on purpose is better.
4. **A staging copy.** A machine built the same way as production, updated first, watched for a day. This project does not have one yet: the staging stack is [issue #310](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/310), a separate Spacelift stack and DigitalOcean project, planned for sprint S7 and built only when the maintainer sets up its accounts ([Roadmap](Roadmap.md)). Until then, a connector droplet's own rebuild from cloud-init is the closest thing to a test, and it is not one: both connectors share the same template.
5. **The test that matters: did the service come back?** After the window, check the thing the host is for, not the update tool. For a connector that means it shows online in Twingate. An update log that says "All upgrades installed" and a service that is down is a failed patch.

## Rolling back

Be honest about what apt gives you: **no transaction undo** (est.; nothing on the pages I read describes one). So rollback is one of these, in order of how much you can rely on them:

| Method | What it needs | Honest limit |
|---|---|---|
| **Restore a snapshot** or boot environment taken before the window | A snapshot habit ([Backups, recovery and patching](Backups-Recovery-and-Patching.md#a-backup-you-have-not-restored-is-a-hope)) | A snapshot restores the disk, including data written since. Time-box the decision. |
| **Rebuild from the code** | The machine is defined as code and holds no state that matters. This project's droplets are exactly this: change `user_data` and the droplet is replaced ([Droplet hardening](Droplet-Hardening.md#why-cloud-init-and-not-ansible)). | A rebuild installs *today's* versions, so it does not take you back to the old package. It gets you a clean host, which is often what you wanted. |
| **Install the previous version of one package** | The old version still in the archive; `apt install package=version`, then hold it (`apt-mark hold`) (est.; commands not run) | The fix you are avoiding is gone too. Put an owner and an expiry date on the hold, or it becomes a quiet vulnerability. |
| **Stop the next run** | `Package-Blacklist` for one package, or `APT::Periodic::Unattended-Upgrade "0"` for all | Stops the problem getting worse, but does not undo it. A blocked package can block its dependents (Ubuntu page). |

A rollback you have never tried is a hope. Pick one machine and try the method you would use, once, before you need it.

For the general rule, Ubuntu's own page lists when to disable or limit automatic updates: systems that are rebuilt anyway; where a manual step is needed before or after an update (block those packages instead of the whole feature); and where the risk of changing outweighs the risk of staying put. Its middle ground for the last case is to block specific libraries rather than everything.

## The limits of automatic updating

Automatic security updates are necessary and not sufficient. What they miss:

- **Software from other repositories.** Not considered unless you add the origin. The connector here is the example.
- **Containers.** The host's updater does not look inside an image. [Backups, recovery and patching](Backups-Recovery-and-Patching.md#what-does-each-tool-actually-patch) covers this.
- **Application dependencies** (a Python, JavaScript or PHP package that your code pulls in). Those need a different tool and a person who owns the update.
- **Anything waiting on a reboot.** An installed kernel fix is not a running kernel fix.
- **Machines that are off, or not on mains power.** A timer that fires while a laptop is off runs later; a laptop on battery skips the run and, per the Debian wiki, "you're not notified about it".
- **A broken updater.** A locked package database, a full disk or a dead repository stops the job. This is the fourth alert in the table above.
- **Fleet questions.** Ubuntu's page says the feature is not "a replacement for fleet management software" when many machines need compliance reports ("how many systems are up-to-date, how many are still behind"), different windows, and canary rollouts, and names Landscape as an example for Ubuntu. If you can no longer answer "which of my machines is behind?" in one query, you have outgrown it.
- **Appliances** (routers, firewalls) are updated by a person on purpose; see the [First hour](First-Hour-on-a-New-System-Updates-and-Baseline.md#what-automatic-updates-means-system-by-system) table.
- **Emergencies.** A flaw being exploited now cannot wait for tomorrow's timer. You need the pre-agreed fast path ([Enterprise change management](Enterprise-Change-Management-for-Beginners.md)), and the means to run `apt` on every host at once.

## Free path: a container, a log and a script

Cost: $0. Everything runs in a throwaway container and deletes itself. You need Podman or Docker (`podman` and `docker` are interchangeable below; Docker may need `sudo`). Nothing here installs anything on your real computer, sends anything, or touches anyone else's machine.

### Exercise 1: the dry run and what it logs

**Predict.** If you install `unattended-upgrades` in a fresh container and run a dry run, will it install anything? Which file will say what it did, and what will the first lines of its log list?

**Do.**

```bash
podman run --rm docker.io/library/ubuntu:24.04 bash -c '
  apt-get update -q >/dev/null 2>&1 && apt-get install -y -q unattended-upgrades >/dev/null 2>&1
  cat /etc/apt/apt.conf.d/20auto-upgrades
  unattended-upgrade --dry-run >/dev/null 2>&1
  ls -l /var/log/unattended-upgrades/
  grep -E "Starting|Allowed origins|upgraded:|All upgrades|dry-run" /var/log/unattended-upgrades/unattended-upgrades.log | cut -c1-200
'
```

**Check.** On 2026-10-30 this printed the two `20auto-upgrades` lines, two files in the log directory (`unattended-upgrades.log` and `unattended-upgrades-dpkg.log`), and log lines starting "Starting unattended upgrades script" and "Allowed origins are:", the list being the release, its security pocket and the two ESM pockets. One run also listed "Packages that will be upgraded: zlib1g" and a line saying the dry-run option was given and nothing was done; an image pulled on another day may list other packages or none. The container has no running init system, so the daily timer does not run: this teaches the configuration and the log, not the schedule.

**Undo.** `--rm` removed the container. `podman rmi docker.io/library/ubuntu:24.04` frees the image.

### Exercise 2: turn a log into the four alerts

The script below reads an `unattended-upgrades.log` and prints which of the four conditions it finds, with an exit code a monitor can use. It is read-only: it sends nothing. It looks only at the **newest run** (from the last "Starting unattended upgrades script" line), because one file can hold many runs and an old error is not today's. It treats the age of that run as the "stopped updating" test.

```bash
#!/usr/bin/env bash
# uu-triage.sh - read an unattended-upgrades log and say which of four alerts it would raise.
# Usage: ./uu-triage.sh LOGFILE [MAX_AGE_HOURS]      (MAX_AGE_HOURS defaults to 36)
# Environment: TRIAGE_NOW   epoch seconds to use instead of the clock (for practice and tests)
#              REBOOT_FLAG  path to the reboot-required file (default /var/run/reboot-required)
# Read-only: it reads the log and the flag file and prints. It sends nothing and changes nothing.
# Exit code: 0 nothing to alert on, 1 a warning, 2 critical, 64 wrong usage.
set -u
[ "$#" -ge 1 ] || { echo "usage: uu-triage.sh LOGFILE [MAX_AGE_HOURS]" >&2; exit 64; }
log=$1
max_h=${2:-36}
flag=${REBOOT_FLAG:-/var/run/reboot-required}
[ -r "$log" ] || { echo "CRITICAL cannot read $log"; exit 2; }
now=${TRIAGE_NOW:-$(date +%s)}
status=0
raise() { [ "$2" -gt "$status" ] && status=$2; echo "$1 $3"; }

# Only the newest run counts: everything from its "Starting" line to the end of the file.
run=$(awk '/Starting unattended upgrades script/ { buf = "" } { buf = buf $0 "\n" } END { printf "%s", buf }' "$log")
started=$(printf '%s' "$run" | grep -m1 -F "Starting unattended upgrades script" | cut -c1-19)

# 4. A host that stopped updating: no run at all, or the newest run is too old.
if [ -z "$started" ]; then
  raise CRITICAL 2 "stale: no run recorded in $log"
else
  last=$(date -d "$started" +%s) || { echo "CRITICAL cannot read the time '$started'"; exit 2; }
  age_h=$(( (now - last) / 3600 ))
  [ "$age_h" -gt "$max_h" ] && raise CRITICAL 2 "stale: the newest run began ${age_h} hours ago (limit ${max_h})"
fi
# 3. An update that failed: any ERROR line in the newest run.
errors=$(printf '%s' "$run" | grep -c ' ERROR ')
[ "$errors" -gt 0 ] && raise CRITICAL 2 "failed: ${errors} ERROR line(s) in the newest run"
# 2. A reboot is needed: the flag file exists, or the tool said it was rebooting.
if [ -e "$flag" ] || printf '%s' "$run" | grep -q 'reboot-required, rebooting'; then
  raise WARNING 1 "reboot: this host needs a reboot to finish an update"
fi
# 1. Something was installed.
pkgs=$(printf '%s' "$run" | grep -m1 'Packages that will be upgraded:' | sed 's/.*upgraded: *//')
if [ -n "$pkgs" ]; then
  if printf '%s' "$run" | grep -q -F -- '--dry-run given'; then
    raise NOTICE 0 "dry run, nothing installed; would apply: $pkgs"
  else
    raise NOTICE 0 "applied: $pkgs"
  fi
fi
[ "$status" -eq 0 ] && [ -z "$pkgs" ] && echo "OK nothing to report"
exit "$status"
```

Save it as `uu-triage.sh`. It needs GNU `date` (`date -d`), so run it in the container (Linux) rather than on a Mac. Make a folder with five small logs, written to match the format you saw in Exercise 1:

```bash
mkdir -p triage-lab && cd triage-lab
cp ../uu-triage.sh .
printf '%s\n' \
  '2026-10-29 06:19:10,100 INFO Starting unattended upgrades script' \
  '2026-10-29 06:19:12,000 INFO No packages found that can be upgraded unattended and no pending auto-removals' > ok.log
printf '%s\n' \
  '2026-10-29 06:19:10,100 INFO Starting unattended upgrades script' \
  '2026-10-29 06:19:12,000 INFO Packages that will be upgraded: libc6 python3-jinja2' \
  '2026-10-29 06:19:30,000 INFO All upgrades installed' > applied.log
printf '%s\n' \
  '2026-10-29 06:19:10,100 INFO Starting unattended upgrades script' \
  '2026-10-29 06:19:12,000 INFO Packages that will be upgraded: libc6' \
  '2026-10-29 06:19:30,000 INFO All upgrades installed' \
  '2026-10-29 06:19:31,000 WARNING Found /var/run/reboot-required, rebooting' > reboot.log
printf '%s\n' \
  '2026-10-28 06:19:10,100 INFO Starting unattended upgrades script' \
  '2026-10-28 06:19:30,000 ERROR an old failure from a previous run' \
  '2026-10-29 06:19:10,100 INFO Starting unattended upgrades script' \
  '2026-10-29 06:19:12,000 INFO Packages that will be upgraded: openssl' \
  '2026-10-29 06:19:30,000 ERROR Installing the upgrades failed!' > failed.log
printf '%s\n' '2026-10-29 06:19:10,100 DEBUG nothing useful' > empty.log
```

The `failed.log` text is made up to show the shape of an `ERROR` line; I did not collect real failure messages, so a real failure may read differently and your monitor should key on the level, as this script does, not on my wording.

**Predict.** Set the clock to noon on the day of the logs. For each of the five files, which line will the script print, and what exit code? Then set the clock to four days later and run `ok.log` again.

**Do.** Use `TZ=UTC` so the log's timestamps and the clock agree, and point `REBOOT_FLAG` at a path that does not exist so your own machine's flag cannot leak in:

```bash
export TZ=UTC REBOOT_FLAG=/nonexistent
NOW=$(date -d '2026-10-29 12:00:00' +%s)
for f in ok applied reboot failed empty; do
  echo "== $f"; TRIAGE_NOW=$NOW bash uu-triage.sh $f.log; echo "exit=$?"
done
echo "== stale"; TRIAGE_NOW=$(date -d '2026-11-02 12:00:00' +%s) bash uu-triage.sh ok.log; echo "exit=$?"
```

**Check.** On 2026-10-30 the script printed, in order: `OK nothing to report` (exit 0); `NOTICE applied: libc6 python3-jinja2` (0); `WARNING reboot: ...` then `NOTICE applied: libc6` (1); `CRITICAL failed: 1 ERROR line(s) in the newest run` then `NOTICE applied: openssl` (2; the old error from the day before is not counted); `CRITICAL stale: no run recorded in empty.log` (2); and for the clock four days on, `CRITICAL stale: the newest run began 101 hours ago (limit 36)` (2). Now run it on the real log from Exercise 1 inside the container, and again after `touch /var/run/reboot-required`: the first run printed a dry-run notice and exit 0, the second added the reboot warning and exit 1.

Notice what the script cannot tell you. It cannot see a host whose log was never written, a host that is off, or a log file someone deleted. That is why the check belongs on a machine other than the one it checks.

**Undo.** `--rm` and `cd .. && rm -r triage-lab`.

### Exercise 3: on paper, choose the alert path

For a fleet of three machines (one web server, one database, one connector), write a table: for each of the four conditions, who is told, by what route, how fast, and what they do. Then answer: what tells you the *notifier* has stopped? Compare with what Patch Gremlin's README offers.

## Predict, then check

1. A host's updater logs nothing for a week and sends no message. Is it healthy? Which of the four alerts would tell you, and why does a tool that reports only events miss it?
2. You add a 52 file that lists only the `-security` origin. Does the host now take updates from fewer places? How would you check?
3. A kernel fix was installed at 06:00. At 06:05 the host is running the old kernel. Why? What decides when it changes?
4. You add the vendor's own apt repository for an application and the application is not updated automatically. Is that a bug?
5. A Patch Gremlin message says "3 packages updated". Does that tell you the service on the host is working?

<details>
<summary>Answers</summary>

1. Not necessarily; unknown. The fourth alert (stale), checking the age of the last run. A tool that reports events only has nothing to report when nothing happens.
2. No: a list option adds; the stock origins stay. Run `apt-config dump | grep Allowed-Origins`, or read the "Allowed origins are:" line of the tool's log. `#clear` on the first line replaces.
3. The new kernel is installed but only loaded at the next boot. The reboot policy: `Automatic-Reboot` and its time, or a person.
4. No, it is the designed behavior (Ubuntu's page). Add the origin if you want it, or give that application its own update job and its own alert.
5. No. It says the package manager did its job. Check the service.

</details>

## Try it yourself

- In the container, write a `52` file that lists only the `-security` origin, run `apt-config dump | grep Allowed-Origins`, then put `#clear Unattended-Upgrade::Allowed-Origins;` on its first line and run it again. Read the difference.
- Add a check to the script for the age of the reboot-required flag: warn after one day, critical after three. Where does the host get its modification time?
- Change `MAX_AGE_HOURS` to 12 and say what that does to a weekly schedule. Then say what the right limit is for a host that updates weekly.
- If you use Patch Gremlin or another notifier, find where it records the last-run time and write the one-line stale check for it.

## Claims register

Vendor pages were read on **2026-10-30** (read-only fetches). The Debian wiki page shows its own last-modified date; the others carry none in the text I read. I took only the statements listed here from each page.

| Claim | Source | Status |
|---|---|---|
| Ubuntu applies security updates automatically through `unattended-upgrades`, installed by default; it does the equivalent of `apt update` and `apt upgrade`; runs once a day by default; files `50unattended-upgrades` (behavior), `20auto-upgrades` (on/off, in days), logs in `/var/log/unattended-upgrades`; timers `apt-daily.timer` and `apt-daily-upgrade.timer` with a random delay; `Persistent=false` stops catch-up | [Ubuntu Server: automatic updates](https://documentation.ubuntu.com/server/how-to/software/automatic-updates/) | Read, 2026-10-30 |
| Default `Allowed-Origins` (release, security, ESM pockets; `-updates` commented out); another repository is not considered unless its `Origin` is added; `Package-Blacklist` as Python regular expressions, anchored as if by `^`; blocking can block dependents | Same page | Read, 2026-10-30; default origins and `20auto-upgrades` also observed in the container |
| `Mail` and `MailReport` (`always`, `only-on-error`, `on-change`; default `on-change`); needs a mail client; example subject and body | Same page | Read, 2026-10-30; mail not tried |
| `Automatic-Reboot` (default `false`), `Automatic-Reboot-WithUsers` (default `true`), `Automatic-Reboot-Time` (default `now`, `hh:mm` in the local time zone, passed to `shutdown(8)`); the log excerpt "Found /var/run/reboot-required, rebooting" | Same page | Read, 2026-10-30; no real reboot run |
| `needrestart` called after upgrades; restarts services automatically by default from Ubuntu 24.04 LTS, with a built-in exception list; `$nrconf{restart}` and `$nrconf{override_rc}` under `/etc/needrestart/conf.d/` | Same page | Read, 2026-10-30; not run |
| When to consider disabling it (recreated systems, manual steps, risk); not a replacement for fleet management, Landscape named | Same page | Read, 2026-10-30 |
| Logs: all operations to `unattended-upgrades.log`, dpkg output to `unattended-upgrades-dpkg.log`; the tool is the backend for `APT::Periodic::Unattended-Upgrade`, run by `apt-daily-upgrade.service` or cron; options `--dry-run`, `--debug` | [`unattended-upgrade(8)`](https://manpages.debian.org/unstable/unattended-upgrades/unattended-upgrade.8.en.html) (unattended-upgrades 2.13, source dated 2026-07-06) | Read, 2026-10-30; the two files seen in the container (2.9.1) |
| Debian: usually installed with conservative settings but may be absent or disabled; check with `dpkg-reconfigure`; use a `52unattended-upgrades-local` copy; `Origins-Pattern`; check `/var/log/dpkg.log` and the log directory; `apt-listchanges`; `unattended-upgrade -d`; timers and `RandomizedDelaySec` guidance; laptops skip runs on battery without notice, `OnlyOnACPower`; `needrestart` | [Debian Wiki: PeriodicUpdates](https://wiki.debian.org/UnattendedUpgrades) (redirects to PeriodicUpdates; last modified 2026-07-10) | Read, 2026-10-30; not run on Debian |
| `dnf-automatic`: `apply_updates` default False, `upgrade_type` `default` or `security`, `reboot` `never`/`when-changed`/`when-needed`, `reboot_command` default `shutdown -r +5 ...`, timer units `-notifyonly`, `-download`, `-install` | [DNF Automatic](https://dnf.readthedocs.io/en/latest/automatic.html) | Read, 2026-10-30; not run |
| A 52 file adds to `Allowed-Origins` rather than replacing it; `#clear` replaces it | Author's measurement: `apt-config dump` in an Ubuntu 24.04.5 container, 2026-10-30 | Run once; not read on a page (`apt.conf(5)` not read) |
| Dry run in a fresh container: two log files, "Allowed origins are:", dry-run line | Author's run, 2026-10-30, as in Exercise 1 | Run once per claim |
| `uu-triage.sh` output for the five logs, the stale case, and the real dry-run log | Author's run, 2026-10-30; `tests/test_patch_management_lesson.py` runs the script from this page | Run |
| Patch Gremlin: purpose, supported systems and destinations, `ExecStartPost` hook, heartbeat default off, health check exit codes, Prometheus metric names, state file, `journalctl -t patch-gremlin`, secrets modes, license line, 2.0 notice, the two descriptions of the trigger | [Patch Gremlin README](https://github.com/ChiefGyk3D/Patch-Gremlin) | README read 2026-10-30; code not read; nothing installed or run |
| Which of the four alerts Patch Gremlin raises for a failed update and for a pending reboot | README | Not stated in the part I read |
| This project's update, baseline and harden order, the 52 file, the weekly connector cron, reboot times, the 60-minute validation, the edge slots | `modules/twingate-bootstrap/cloud-init.yaml.tftpl`, `stacks/10-access/variables.tf`, `modules/edge-host/reboot-slots.json`, [Droplet hardening](Droplet-Hardening.md#updates) | Read in the repository; `tests/test_update_order_pinned.py` pins the first-hour order in the template |
| Staging stack planned, not built | [Issue #310](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/310), [Roadmap](Roadmap.md) | Read 2026-10-30 |
| `journalctl -u apt-daily-upgrade.service`, `systemctl list-timers`, `apt install package=version`, `apt-mark hold`, log rotation, "apt has no transaction undo", the stale-metric expression, "weeks" of exposure | Author's general knowledge | **est.**; not run, not read on a page |

Next: [Backups, recovery and patching](Backups-Recovery-and-Patching.md), then the [Reading order](Reading-Order.md).
