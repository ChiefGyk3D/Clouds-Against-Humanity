# Cron, systemd timers, and init scripts versus systemd

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Cron, systemd timers and init scripts versus systemd

Previous: [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) / Next: [How a web request works](How-a-Web-Request-Works.md)
<!-- END GENERATED PAGE NAV top -->

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says (and the gap)](#what-the-wiki-already-says-and-the-gap)
- [Cron: what it is and how to read a line](#cron-what-it-is-and-how-to-read-a-line)
- [User crontabs and system crontabs](#user-crontabs-and-system-crontabs)
- [Why people like cron](#why-people-like-cron)
- [Where cron falls short](#where-cron-falls-short)
- [systemd timers: a timer and a service](#systemd-timers-a-timer-and-a-service)
- [Timer settings that matter](#timer-settings-that-matter)
- [Reading timers and their logs](#reading-timers-and-their-logs)
- [Cron to timer: a translation table](#cron-to-timer-a-translation-table)
- [Is cron still installed? What I checked](#is-cron-still-installed-what-i-checked)
- [Init scripts versus systemd](#init-scripts-versus-systemd)
- [Where systemd is not the answer](#where-systemd-is-not-the-answer)
- [Troubleshooting: why did my job not run](#troubleshooting-why-did-my-job-not-run)
- [Free exercises](#free-exercises)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

Side page to [The terminal and your first script](Terminal-and-Your-First-Script.md) and [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md). Read it when a script needs to run on a schedule, when a tutorial says "add a crontab line" and your system has no `crontab` command, when `systemctl list-timers` shows jobs you never wrote, or when an old guide says `/etc/init.d/something start` and you want to know why you do not type that anymore. It covers two linked questions: how a Linux machine runs a job on a schedule (cron, or a systemd timer), and how it starts and watches services at all (init scripts, or systemd). The second question is why the first one has two answers.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. The `systemd-analyze` lines were run; no timer was started and no crontab was edited.** On **2026-11-07**, on one Debian 13 machine with systemd 257 (257.13-1~deb13u1) and the Debian `cron` package, I ran: `systemctl list-timers`, `systemctl list-unit-files --type=timer`, `systemd-analyze calendar` on eleven expressions (the output is quoted below), `systemd-analyze verify` on the two unit pairs in this page, and read-only looks at `/etc/init.d/cron`, `/etc/rc2.d`, `cron.service`, `/etc/cron.daily` and the man pages. `systemd-analyze verify` passed the first pair and failed the second for a real reason (see [reading timers](#reading-timers-and-their-logs)). I tried to enable the demo timer and my environment refused the command, so **I did not start a timer, did not read a timer's output in the journal, and did not edit a crontab.** Every exercise step that does those is written from the man pages and marked **est.** The package facts in [the distro table](#is-cron-still-installed-what-i-checked) were read from package indexes and repository metadata on 2026-11-07. Trust what your terminal prints over what this page says.

> **Prerequisites.** A terminal and a small script ([The terminal and your first script](Terminal-and-Your-First-Script.md)). Knowing what a service is helps ([Linux for enterprise beginners: services](Linux-for-Enterprise-Beginners.md#services-with-systemd)). For the free exercise you need a Linux virtual machine that runs systemd (Debian, Ubuntu or Fedora; **not** the Alpine ISO from the [virtual machines lesson](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md), which uses OpenRC) or a Linux computer where you may use `sudo`. About 75 minutes for the reading and the exercises (est.).

> **Where this runs, and the rule.** The exercises write one line to the journal and one file under your home folder, and the undo for each is stated. Do them in a throwaway VM, not on a server that does work. No exercise edits a system file other than a pair of unit files you create and then delete. A container usually has no systemd and no cron daemon, so the timer exercise does not work in a typical container (see [where systemd is not the answer](#where-systemd-is-not-the-answer)). No real addresses appear.

## What you will be able to do

- Read a crontab line, say which field is which, and say when it runs.
- Tell a user crontab from a system crontab, and find both.
- Give the real reasons people like cron, and the five ways it lets you down.
- Write a `.timer` and `.service` pair, read `systemctl list-timers`, check a schedule with `systemd-analyze calendar`, and read a job's output with `journalctl -u`.
- Translate a cron line to a timer, including the two places the translation is not one to one.
- Say which distributions install cron by default, as of a stated date, and which do not.
- Compare a SysV init script with a systemd unit fairly, including what the critics get right.
- Work through a "my job did not run" checklist for cron and for timers.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| A script plus a trigger | [The terminal and your first script: automation](Terminal-and-Your-First-Script.md#automation-is-a-script-plus-a-trigger) names cron and systemd timers in one table row each | The syntax, the tradeoffs, and how to write either one |
| `systemctl` and `journalctl` | [Linux for enterprise beginners: services](Linux-for-Enterprise-Beginners.md#services-with-systemd) | What a unit file contains and why the journal helps |
| Automatic updates run on timers | [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md#what-automatic-updates-means-system-by-system) | How to see those timers and read their last run |
| One weekly job in this project | A file in `/etc/cron.d`, written by the first-boot config in `modules/twingate-bootstrap/cloud-init.yaml.tftpl` ([Droplet hardening](Droplet-Hardening.md)) | Why that file works, and what a timer would change |

## Cron: what it is and how to read a line

**cron** is a program that wakes up every minute, looks at a list of jobs, and starts any job whose time has come. Debian's manual says it "examines cron entries once every minute". The list is a **crontab** ("cron table"): a text file with one job per line. Cron is old, it is on nearly every Unix-like system, and for a lot of jobs it is all you need.

A job line has five time fields and then a command:

```text
# m   h   dom mon dow   command
*/15  *   *   *   *     /home/you/bin/checkup.sh
30    2   *   *   *     /home/you/bin/backup.sh >> /home/you/backup.log 2>&1
0     9   *   *   1-5   /home/you/bin/weekday-report.sh
```

| Field | Allowed values | In the examples above |
|---|---|---|
| minute | 0 to 59 | `*/15` every 15 minutes; `30`; `0` |
| hour | 0 to 23 | `*` every hour; `2`; `9` |
| day of month | 1 to 31 | `*` every day |
| month | 1 to 12, or three-letter names | `*` every month |
| day of week | 0 to 7 (0 and 7 are Sunday), or names | `1-5` Monday to Friday |

Inside a field, `*` means every value, `,` makes a list (`1,15`), `-` makes a range (`8-11`) and `/` makes a step (`*/15`, or `0-23/2` for every other hour). These come from the Debian `crontab(5)` page, which also lists eight shortcut strings that replace the five fields: `@reboot`, `@hourly`, `@daily` (also `@midnight`), `@weekly`, `@monthly`, `@yearly` (also `@annually`). `@reboot` means "when the cron daemon starts", which the manual warns may be before other system services are up.

Four things in that manual trip people up:

- **Day of month and day of week are an OR, not an AND.** If both are set, the job runs when either matches. The manual's example: `30 4 1,15 * 5` runs at 04:30 on the 1st and 15th **and** on every Friday. If you wanted "Fridays that are also the 1st or 15th", cron cannot say it in the fields; you test the date inside the command.
- **A `%` in the command is a newline** unless you write `\%`. A `date +%Y-%m-%d` in a crontab line breaks until you escape it as `date +\%Y-\%m-\%d`.
- **A comment on the same line as a job is not a comment.** It is passed to the shell as part of the command.
- **Variables are not expanded in the crontab itself.** `PATH=$HOME/bin:$PATH` does not do what it looks like.

## User crontabs and system crontabs

| Aspect | User crontab | System crontab |
|---|---|---|
| Where | A file per user, kept by cron (on Debian under `/var/spool/cron/crontabs/`); you never edit it directly | `/etc/crontab`, and one file per job in `/etc/cron.d/` |
| How you edit it | `crontab -e` (edit), `crontab -l` (list) | Any editor, as root |
| Fields | Five time fields, then the command | Five time fields, **then a user name**, then the command |
| Runs as | The user who owns it | The user named in the line |
| Use it for | Your own jobs | Jobs that belong to a package or to the machine |

Debian's `cron(8)` page says user crontabs "should not be accessed directly - the crontab(1) command should be used". A system crontab line looks like this, with the extra `root` column (the form below is the one in the `crontab(5)` page):

```text
17 *  * * *  root  cd / && run-parts --report /etc/cron.hourly
```

`/etc/cron.hourly`, `cron.daily`, `cron.weekly` and `cron.monthly` are folders of scripts that `run-parts` runs at those intervals; a package drops a script in one. A warning that is easy to lose: `crontab -r` removes **your whole crontab with no confirmation** (est.; read `crontab(1)` on your system before you use it).

## Why people like cron

I am not going to tell you cron is bad. These are the real reasons it is still everywhere:

- **It is simple.** One line per job. A schedule fits in 20 characters and you can read it a year later.
- **It is classic.** The format is decades old. Every guide, every Stack Overflow answer and every old colleague knows it.
- **It is portable.** The same five fields work on Linux, the BSDs and macOS (est. for macOS; the Debian manual notes that `@` strings and some range forms are extensions, so a strict old cron may not take them). FreeBSD's handbook uses an `/etc/crontab` line for its update check, as the [First hour](First-Hour-on-a-New-System-Updates-and-Baseline.md#what-automatic-updates-means-system-by-system) page shows.
- **It is reliable.** It has run a lot of the world's backups. A tool that does one thing for forty years has had its bugs found.
- **It needs no setup.** Edit a file, wait a minute.

## Where cron falls short

Five limits, each of which will eventually cost you an evening.

1. **A minimal environment.** The `crontab(5)` page lists what cron sets for you: `SHELL`, `LOGNAME` and `HOME`. Your login `PATH`, your aliases, and anything your shell profile exports are not there. The classic bug is a script that works in your terminal and fails from cron because it called a program by name. Use absolute paths, and set `PATH` at the top of the script.
2. **No run record of its own.** Cron mails any output to the crontab's owner (`MAILTO` changes who, `MAILTO=""` turns it off, both from the man page). On a machine with no mail system set up (est. for most new servers), that output goes nowhere. Cron logs the **start** of each job (the default log level in `cron(8)` is 1, "log the start of all cron jobs"), and the end and the exit status only if you raise the level. Whether the job worked is up to you: redirect output into a log file yourself, as the second example above does.
3. **Missed runs.** Cron only runs a job when the clock hits that minute **while cron is running**. If the machine is off at 02:30, the 02:30 job does not run later. The `crontab(5)` page says it directly: where a system is not powered on in the 6 to 7 am window, "only the hourly tasks will be executed". A separate program, `anacron`, exists to catch up daily, weekly and monthly jobs. On Debian 13 and Ubuntu it is a separate package with priority `optional`, not part of a default install (package index, 2026-11-07).
4. **Overlap.** If a job takes longer than its interval, cron starts the next one anyway. Two backups writing to the same file is not a good evening. The usual fix is to wrap the command in `flock -n /path/to/lockfile command`, which makes the second copy give up (`-n` is "nonblock" in `flock(1)`).
5. **No dependencies.** Cron has no idea whether the network is up, the disk is mounted or the database has started. `@reboot` is the closest it gets, and the manual says it is not ordered.

None of these is a reason to throw cron out. They are why a second tool was built.

## systemd timers: a timer and a service

A **systemd timer** is a unit that says when, and it activates a second unit that says what. You write two small files.

The `.service` is the job:

```ini
# nightly.service
[Unit]
Description=Nightly backup check (example)

[Service]
Type=oneshot
ExecStart=/usr/local/bin/backup-check.sh
```

The `.timer` is the schedule:

```ini
# nightly.timer
[Unit]
Description=Run nightly.service at 03:15 every day

[Timer]
OnCalendar=*-*-* 03:15:00
Persistent=true
RandomizedDelaySec=10min

[Install]
WantedBy=timers.target
```

By default a timer activates the service **with the same name**: `nightly.timer` starts `nightly.service` (the `systemd.timer(5)` manual). `Type=oneshot` says "this program runs and exits", which is what a script is. A system-wide pair lives in `/etc/systemd/system/`; you then run `sudo systemctl daemon-reload` and `sudo systemctl enable --now nightly.timer`. You enable the **timer**, not the service. A per-user pair lives in `~/.config/systemd/user/` and you use `systemctl --user`.

A **unit file** is that kind of file: an INI-style text file, with sections like `[Unit]`, `[Service]` and `[Timer]`, that tells systemd about one thing it manages (a service, a timer, a mount, a socket). The same format describes everything systemd runs, which is one of the things it is good for.

## Timer settings that matter

| Setting | What it does | Note |
|---|---|---|
| `OnCalendar=` | A wall-clock schedule, written as `DayOfWeek Year-Month-Day Hour:Minute:Second` | `*` is any, `,` a list, `..` a range, `/` a step. Check yours with `systemd-analyze calendar` |
| `OnBootSec=` | Run this long after the machine booted | A "monotonic" timer, not tied to the clock |
| `OnUnitActiveSec=` | Run this long after the service **last started** | With `OnBootSec=`, gives "first run after boot, then every interval" |
| `OnActiveSec=` | Run this long after the timer itself was started | Handy for a quick test |
| `Persistent=true` | Remember when the service last ran; if a run was missed while the machine was off, run once at the next start | Works **only** with `OnCalendar=` (the manual says so). This is the missed-run fix cron lacks |
| `RandomizedDelaySec=` | Add a random delay up to this long before each run | Spreads many machines so they do not all hit one server at 03:15 |
| `AccuracySec=` | How far the run may slip so that wake-ups bunch together | **Default 1 minute.** A timer set for 03:15:00 may fire up to a minute late. Set `AccuracySec=1s` if that matters |

Three calendar words you will see: `hourly`, `daily` and `weekly`. I ran them through the checker. `systemd-analyze calendar weekly` printed `Mon *-*-* 00:00:00`, so **`weekly` means Monday at midnight in systemd**, where cron's `@weekly` is Sunday (`0 0 * * 0`, from the cron man page). `daily` normalizes to `*-*-* 00:00:00` and `monthly` to `*-*-01 00:00:00`.

## Reading timers and their logs

Four commands cover most of what you do.

```bash
systemctl list-timers                  # every active timer: NEXT, LEFT, LAST, PASSED, UNIT, ACTIVATES
systemctl list-timers --all            # include timers that are inactive
systemd-analyze calendar '*:0/15'      # when would this expression fire? (no unit needed)
journalctl -u nightly.service          # everything that unit printed, with timestamps
```

The first command on my Debian 13 machine gave a table with these columns (I removed the rows of this machine's own units): `NEXT  LEFT  LAST  PASSED  UNIT  ACTIVATES`, one row per timer, for example `apt-daily.timer` activating `apt-daily.service`. That is the answer to "did my job run, and when does it run next" in one line, which cron does not give you.

`systemd-analyze calendar` is the tool I would have wanted when I started. It parses your expression, prints the **normalized form**, and shows the next time it fires. What I ran:

```text
$ systemd-analyze calendar '*:0/15' --iterations=3
  Original form: *:0/15
Normalized form: *-*-* *:00/15:00
    Next elapse: (the next quarter hour)
   Iteration #2: (the one after)
   Iteration #3: (and the one after that)
```

`Mon..Fri 09:00` normalized to `Mon..Fri *-*-* 09:00:00` and printed the next three weekday mornings. Use it before you trust a schedule, and put a cron line through the same test by translating it first (next section).

`systemd-analyze verify` checks a unit file without starting it. I ran it on the two example pairs. The `hello-timer` pair in the exercise passed with exit 0. The `nightly` pair printed `nightly.service: Command /usr/local/bin/backup-check.sh is not executable: No such file or directory` and exit 1, because that script does not exist on my machine. That is what you want a check to say, before 03:15.

**Logs.** A service started by systemd has its standard output and standard error connected to the journal by default (`DefaultStandardOutput=journal` in `systemd-system.conf(5)`). So `echo` and `print` in your script show up in `journalctl -u your.service` with a timestamp, no redirect needed. Two settings of the journal matter. By default it stores logs on disk only if `/var/log/journal` exists, and in memory (lost at reboot) otherwise (`Storage=auto` in `journald.conf(5)`). And `journalctl --user` shows a user's service logs, but the `journalctl(1)` page says it "only works if persistent logging is enabled".

## Cron to timer: a translation table

Each row was checked with `systemd-analyze calendar` except where noted.

| Cron | systemd `OnCalendar=` | Careful |
|---|---|---|
| `*/5 * * * *` | `*:0/5` (normalizes to `*-*-* *:00/5:00`) | Same |
| `15 3 * * *` | `*-*-* 03:15:00` | Same |
| `0 9 * * 1-5` | `Mon..Fri 09:00` | Same |
| `23 0-23/2 * * *` | `*-*-* 0/2:23` (normalizes to `*-*-* 00/2:23:00`) | Same |
| `@hourly` | `hourly` | Same |
| `@daily` | `daily` | Same |
| `@weekly` | `Sun *-*-* 00:00` | **Not** the word `weekly`: that is Monday |
| `@monthly` | `monthly` | Same (`*-*-01 00:00:00`) |
| `30 4 1,15 * 5` | no single equivalent | **Different meaning.** In cron it is the 1st and 15th **or** Fridays. `Fri *-*-1,15 04:30` is Fridays that are **also** the 1st or 15th; the checker's next two hits were 2027-01-01 and 2027-01-15 (I ran it). To get cron's behavior write two `OnCalendar=` lines, one for the dates and one for Fridays |
| `@reboot` | `OnBootSec=1min` (or `WantedBy=multi-user.target` on a service) | Not identical: cron's `@reboot` is when cron starts, a timer is a set time after boot. Est. |
| `MAILTO=you` | `OnFailure=` pointing at a unit that notifies you | No mail by default in a timer; see below. Est. |

What you get that a crontab line cannot give you: `Persistent=true` for missed runs; `RandomizedDelaySec=` for a fleet; `After=network-online.target` or any other dependency in the service; resource limits and a sandbox on the service (`MemoryMax=`, `ProtectSystem=`, est.); the output in the journal with the exit status in `systemctl status`; and one more safety. The timer manual says "in case the unit to activate is already active at the time the timer elapses it is not restarted, but simply left running", so a long `oneshot` job does not overlap itself.

What you pay: **two files instead of one line**, a unit syntax to learn, a `daemon-reload` after each edit, and the schedule is harder to eyeball for someone who knows cron cold.

## Is cron still installed? What I checked

Some systems no longer install cron by default and use systemd timers for their own housekeeping, so a guide that starts "add this to your crontab" does nothing. I checked what I could, on **2026-11-07**, from package indexes and repository metadata. I name only what I read; the rest is marked **est.**

| System | What I read | What it says about cron |
|---|---|---|
| Debian 12 "bookworm", 13 "trixie" | Package index: `cron` has priority **important** (3.0pl1-162, 3.0pl1-197). `debootstrap(8)`: the default makes "a base Debian installation with all packages of priority required and important" | cron is in a default base install. The installer's default task list: **est.** |
| Ubuntu 24.04 LTS "noble", 26.04 LTS "resolute" | Package index: `cron` has priority **standard**; the `ubuntu-standard` metapackage lists `cron` in its `Depends` for both releases. Launchpad lists 26.04 as Supported, released 2026-04-23 | cron is part of Ubuntu's standard package set. Whether a given cloud image includes `ubuntu-standard`: **est.** |
| Rocky Linux 9 and 10 | Repository metadata: `cronie` is a mandatory member of the group `core`, which is marked default | cron is in a default install. RHEL and Alma are built to match Rocky, so probably the same: **est.**; I did not read them |
| Fedora 43 and 44 | Release metadata: `cronie` is in **no** package group. `crontabs` (which requires `cronie`) is in the group `standard` only, and that group is **not** marked default | Not in the default groups. What each Fedora edition's installer adds on top: **est.**; I did not read it. The package is in the repository (cronie 1.7.2) |
| Arch Linux | The `base` package (version 3, updated 2026-02-07) has no cron in its depends; `cronie` 1.7.2 is in the `extra` repository | cron is not in `base`. You install it |
| openSUSE Tumbleweed | Repository metadata for today: no `patterns-*` package lists `cron` or `cronie` as a requirement or recommendation. `cron` exists (4.2) and requires `cronie` | Not in any pattern I read. The installer's choices, Leap and SUSE Linux Enterprise: **est.**; I did not read them |

So the true statement is narrower than "Linux dropped cron". **Debian, Ubuntu and the Red Hat family (by Rocky) still install it. Fedora's default groups do not list it, and Arch and openSUSE Tumbleweed do not install it by default**, each as of 2026-11-07, from the data above.

Two more things from the Debian machine, both observed. First, cron and timers live side by side. `/etc/cron.daily/logrotate` and `/etc/cron.daily/man-db` each begin with a check that exits when `/run/systemd/system` exists, and a comment saying the script is skipped because a systemd timer does the job. So a package ships both and the one that runs is chosen by whether systemd is there. Second, `systemctl list-unit-files --type=timer` on that machine listed at least 30 timers, including `apt-daily`, `logrotate`, `man-db`, `fstrim` and `systemd-tmpfiles-clean`. Even with cron installed, much of the machine's own housekeeping runs from timers.

**Why most of my recent projects ship only timers.** Some operating systems no longer install cron by default and rely on systemd timers, and the table above shows how that varies. A project that schedules itself with a crontab line works only where someone has installed the daemon; a timer works wherever systemd is the init system, with nothing extra to install. That is the whole reason. A bonus is that the output lands in the journal. Where systemd cannot be assumed, ship the cron line and say so. This repository's connector droplets use one `/etc/cron.d` file (the weekly update, from Twingate's own update guide), and that is fine on an Ubuntu image that ships cron (est. for the exact droplet image). It is a note about my newer work, not a rule you must follow.

## Init scripts versus systemd

A timer is a small piece of a bigger change. The reason systemd has timers at all is that it replaced the program that starts everything else.

**PID 1** is the first process the kernel starts. It starts the rest of the system and adopts any process whose parent died. That program is the **init system**. For decades on Linux it was **SysV init** (the name comes from Unix System V). The Debian wiki's history: in Debian "squeeze and earlier releases, sysvinit was the only supported init system", systemd became the default in "jessie", and "since jessie, only systemd is fully supported".

How SysV init worked, in four pieces:

- **Init scripts.** One shell script per service in `/etc/init.d/` that takes `start`, `stop`, `restart` and `status`. You ran `/etc/init.d/ssh restart`, or `service ssh restart`.
- **Runlevels.** Numbered modes (single-user, multi-user, with or without a graphical login) and a folder per level, `/etc/rc2.d` and so on. Each folder holds **symlinks** named `S01cron` or `K01ssh` to the scripts; `S` means start, `K` means kill, and the number sets the order. The machine ran the `S` links in number order at boot. I looked: on the Debian 13 machine `/etc/rc2.d/S01cron` is a symlink to `../init.d/cron`, still there for compatibility.
- **Ordering by number, plus comments.** The script for `cron` on that machine begins with a comment block (`### BEGIN INIT INFO`) with `Provides: cron` and `Required-Start: $remote_fs $syslog $time`. These LSB headers describe the order, but a tool reads them to decide the link numbers (est.); the script itself does not enforce anything.
- **Logging up to each service.** The init system does not collect output. A daemon writes to its own log file, or to syslog if the author did that, and every one differs.

How systemd does the same job: the `cron.service` unit on the same machine is a short INI file:

```ini
[Unit]
Description=Regular background program processing daemon
Documentation=man:cron(8)
After=remote-fs.target nss-user-lookup.target

[Service]
EnvironmentFile=-/etc/default/cron
ExecStart=/usr/sbin/cron -f $EXTRA_OPTS
Restart=on-failure
SyslogFacility=cron

[Install]
WantedBy=multi-user.target
```

(I left out two settings, `IgnoreSIGPIPE=` and `KillMode=`; the rest is the unit as shipped.) Compare it with the init script, which on that machine is a screenful of shell that you have to read to know what `start` does.

| Aspect | SysV init scripts | systemd units |
|---|---|---|
| A service is | A shell script that handles `start` and `stop` however its author wrote it | A declarative file: what to run, what it needs, what to do when it dies |
| Order | `S` and `K` numbers in a runlevel folder, plus comment headers a tool reads | `After=`, `Requires=`, `Wants=`; systemd works out the order. Units with no ordering between them start in parallel (`systemd(1)`) |
| Start-up | One script after another, by number | Parallel where nothing forces an order |
| Keeping track of a service | A PID file the script keeps; if the daemon forks oddly, the pid file lies | Every service gets its own **cgroup** (`systemd(1)`: "Processes systemd spawns are placed in individual Linux control groups named after the unit"). Systemd knows exactly which processes belong to it, and `stop` kills all of them |
| Restart on failure | Not built in; needs another tool | `Restart=on-failure` |
| Logs | Whatever the daemon does | One journal; the service's stdout and stderr go in it by default; `journalctl -u name` |
| Commands | `service`, `chkconfig`, `update-rc.d`, differing by distribution | `systemctl` and `journalctl`, the same on every systemd distribution |
| Schedules | cron beside it, a separate program | Timers, units like any other, with the same logging and dependency tools |

Systemd also reads old SysV scripts. The `systemd(1)` page: "SysV init scripts are supported and simply read as an alternative (though limited) configuration file format", and if there is no native unit it looks for an init script of the same name.

### My stance, and the other side

systemd is where Linux has gone: Debian's default since jessie (Debian wiki), and Ubuntu and the Red Hat family use it too (est. for those two). I did not like it at first. I learned it is the better way, and the main reason is **the unified journal**. With init scripts, "why did the thing not start" meant working out which file that daemon logs to, then whether it logged at all. With systemd it is `systemctl status name`, then `journalctl -u name`, and every service answers the same way. For troubleshooting, that is worth the learning cost. The parallel start, the cgroup tracking and the consistent commands came with it.

The critics are not wrong about everything, and you should know their case:

- **Scope.** systemd is not just an init system. It ships a login manager (`systemd-logind`), a network manager (`systemd-networkd`), a DNS resolver (`systemd-resolved`), a time-sync client (`systemd-timesyncd`), the journal and more. The Debian wiki says non-systemd setups need replacements for session management (`elogind`) when a desktop expects it. Critics call that creeping scope and a lot of code in PID 1's neighborhood. Defenders say the pieces are separate programs that share a design. Both are describing the same fact.
- **The binary journal.** The journal's format is binary: the `systemd.io` file-format page says it "stores log data in a binary format" with indexing, compression and optional forward secure sealing. You cannot `grep` it; you use `journalctl`. If the file is damaged, plain-text logs degrade more gracefully (est.). The usual answer is that the journal can forward to a traditional syslog daemon (`ForwardToSyslog=` in `journald.conf(5)`) and `journalctl -o json` exports text. That is an answer to the objection, not a dismissal of it.
- **Lock-in.** Software that assumes systemd (a desktop that needs `libpam-systemd`, said the Debian wiki for GNOME in Bullseye) is harder to run elsewhere. The wiki notes that Debian supports alternatives with less testing.

You can run Linux without systemd, and some people do. Debian's wiki says other init systems are provided, "but are less actively supported".

## Where systemd is not the answer

- **Containers.** A container is a process on the host's kernel, and most images run one program with no init system at all ([Containers and Docker basics](Containers-and-Docker-Basics.md)). There is no cron daemon and no systemd inside a typical container. You schedule from outside it: the host's timer runs `docker run` or `docker exec`, or the orchestrator does (Kubernetes has its own scheduled job type, the CronJob; est.). A guide that tells you to put a crontab line inside a container image is usually wrong unless that image starts cron on purpose.
- **Alpine Linux.** The Alpine wiki: "Alpine Linux uses OpenRC for its init system." OpenRC manages services with `rc-service` and `rc-update` and a runlevel idea like SysV, with services as scripts. Alpine's cron story (BusyBox `crond`, est.) is a different one. This is why the Alpine ISO in the VM lesson cannot do the timer exercise.
- **Other Linux distributions.** Gentoo defaults to OpenRC (est.); Void uses runit (est.); Devuan is Debian without systemd (est.). The Debian wiki does list OpenRC and runit as alternatives in Debian.
- **The BSDs.** FreeBSD's handbook describes `rc.conf` and startup scripts in `rc.d` directories; its base system has cron; it does not use systemd, which is a Linux program.
- **macOS and Windows.** Neither uses systemd. macOS uses `launchd` and Windows has Task Scheduler (the [terminal lesson](Terminal-and-Your-First-Script.md#automation-is-a-script-plus-a-trigger) lists the Windows one).

The rule I use: on a Linux server I run, assume systemd, check with `readlink /proc/1/comm` or look for `/run/systemd/system` (the Debian wiki gives both), and write a timer. Anywhere else, use what the platform has.

## Troubleshooting: why did my job not run

Go in this order. Most of the time it is the first or second thing.

**Cron job:**

1. **Is the daemon running?** `systemctl status cron` (Debian, Ubuntu) or `systemctl status crond` (Red Hat family; est.). If the unit does not exist, cron is not installed. See the distro table.
2. **Is the line in the right place and valid?** `crontab -l` for your user, or the file in `/etc/cron.d`. In a system file, did you add the user column? A user-style line in `/etc/cron.d` fails.
3. **Did cron start it?** Cron logs each job start. Look in the system log: `journalctl -u cron --since "1 hour ago"` (unit name differs by family, est.), or `/var/log/syslog` or `/var/log/cron` on systems that keep one. If there is no line, cron never matched the time: check the five fields, and remember the OR rule for day of month and day of week.
4. **Did it start and fail?** Redirect the output yourself: `>> /home/you/job.log 2>&1`. Then read the log. A "command not found" almost always means the minimal `PATH`.
5. **Was the machine off at that minute?** Cron does not catch up. Use `anacron`, or move the job to a timer with `Persistent=true`.
6. **Is it a `%`?** An unescaped `%` in the command cuts it off.
7. **Is mail the only place the error went?** `mail`, or `MAILTO`.

**systemd timer:**

1. **Is the timer enabled and active?** `systemctl list-timers --all | grep yourname`. A timer you created but never enabled with `enable --now` does nothing. `systemctl status yourname.timer` shows `active (waiting)` when it is armed (est.).
2. **When is it next?** The `NEXT` and `LEFT` columns. If `NEXT` is blank, the timer has nothing scheduled; check `OnCalendar=` with `systemd-analyze calendar`.
3. **Did it run?** `LAST` and `PASSED` in `list-timers`. Then `systemctl status yourname.service`: the exit status and the last log lines are right there.
4. **What did it print?** `journalctl -u yourname.service`. Add `--since today` or `-b` for this boot. Note that the **timer** and the **service** have separate histories: `journalctl -u yourname.timer` shows the timer activating, and `-u yourname.service` shows the job.
5. **Did you reload?** After editing a unit file, `sudo systemctl daemon-reload`; after changing a timer, `sudo systemctl restart yourname.timer`. Systemd warns when a unit changed on disk (est.).
6. **Did the file check pass?** `systemd-analyze verify yourname.service yourname.timer` (I ran this; it caught a missing script).
7. **Is it up to a minute late?** `AccuracySec=` defaults to 1 minute.
8. **Is the service still running from last time?** The timer leaves a running service alone, so a hung job means no new runs (`systemctl status`).
9. **Is the clock right?** A calendar timer follows the clock; the manual notes timers are ordered after time sync.

## Free exercises

Do these in a throwaway VM with systemd, or on a Linux computer where you do not mind a pair of unit files for ten minutes. Each has Predict, Do, Check and Undo.

### Exercise 1: look at your own machine (read-only)

> Run on Debian 13 on 2026-11-07. Your output will differ.

1. **Predict.** Does your machine have more timers than cron jobs?
2. **Do.**

   ```bash
   systemctl list-timers --all
   ls /etc/cron.d /etc/cron.daily
   crontab -l
   ```

3. **Check.** `list-timers` printed rows with NEXT, LEFT, LAST, PASSED, UNIT and ACTIVATES. `crontab -l` prints `no crontab for <you>` if you have none. Compare the two lists: on my machine, the timers were more numerous and several `cron.daily` scripts were present but exit immediately because a timer replaced them.
4. **Undo.** Nothing changed.

### Exercise 2: translate five cron lines (run, no changes)

1. **Predict.** For `45 6 * * 1-5`, what is the `OnCalendar=` value? For `@weekly`?
2. **Do.** Check your answers with the tool, and try these:

   ```bash
   systemd-analyze calendar 'Mon..Fri 06:45' --iterations=3
   systemd-analyze calendar weekly
   systemd-analyze calendar 'Sun *-*-* 00:00'
   systemd-analyze calendar 'Fri *-*-1,15 04:30' --iterations=2
   ```

3. **Check.** `weekly` normalizes to `Mon *-*-* 00:00:00`; the Sunday form to `Sun *-*-* 00:00:00`. The last line prints dates that are Fridays **and** the 1st or 15th, weeks or months apart, unlike cron's OR.
4. **Undo.** Nothing changed.

### Exercise 3: a timer that logs to the journal (written from the man pages; not started)

> **Not run: enabling the timer and reading the journal.** `systemd-analyze verify` passed on these two files (exit 0, see the status banner). I did not start them, so the journal output below is what the manual says to expect, **est.**

1. **Predict.** If the timer fires every 30 seconds, what will the journal show, and under which unit name?
2. **Do.** In a VM, create two files as root. The first is `/etc/systemd/system/hello-timer.service`:

   ```ini
   [Unit]
   Description=Write one line to the journal (lesson demo)

   [Service]
   Type=oneshot
   ExecStart=/usr/bin/echo hello from the timer
   ```

   The second is `/etc/systemd/system/hello-timer.timer`:

   ```ini
   [Unit]
   Description=Run hello-timer.service every 30 seconds (lesson demo)

   [Timer]
   OnActiveSec=5s
   OnUnitActiveSec=30s
   AccuracySec=1s

   [Install]
   WantedBy=timers.target
   ```

   Then check, load, start and watch it:

   ```bash
   systemd-analyze verify /etc/systemd/system/hello-timer.service /etc/systemd/system/hello-timer.timer
   sudo systemctl daemon-reload
   sudo systemctl enable --now hello-timer.timer
   systemctl list-timers hello-timer.timer
   sleep 70
   journalctl -u hello-timer.service --since "5 minutes ago"
   ```

3. **Check.** `list-timers` should show `hello-timer.timer` with a NEXT time under 30 seconds away and `hello-timer.service` under ACTIVATES. After about 70 seconds the journal should hold two or three lines containing `hello from the timer`, each with a timestamp, plus systemd's own start and finish lines for the unit (est.). Compare that with what a cron job would give you without a redirect: nothing.
4. **Undo.**

   ```bash
   sudo systemctl disable --now hello-timer.timer
   sudo rm /etc/systemd/system/hello-timer.service /etc/systemd/system/hello-timer.timer
   sudo systemctl daemon-reload
   ```

   Confirm with `systemctl list-timers --all | grep hello` (nothing).

### Exercise 4: break it and read the failure (written from the manual; not run)

1. **Predict.** If `ExecStart=` points at a program that does not exist, where do you find out?
2. **Do.** Before the undo in exercise 3, edit the service to `ExecStart=/usr/bin/echo-not-here`, run `sudo systemctl daemon-reload`, wait one interval, then:

   ```bash
   systemctl status hello-timer.service
   journalctl -u hello-timer.service --since "2 minutes ago"
   ```

3. **Check.** The status should show the unit as `failed` and an exit status, and the journal should show why. Run `systemd-analyze verify` on the file: on my machine the same kind of mistake in the `nightly` example printed `Command ... is not executable: No such file or directory` and exit 1, which is the error you get before it ever runs.
4. **Undo.** Fix the line, or run the undo from exercise 3.

### Exercise 5: the same job in cron, with a log (written from reading; not run)

1. **Predict.** Which of these will fail from cron and work in your terminal?
2. **Do.** Back up your crontab first, then add the line and wait a minute:

   ```bash
   crontab -l > ~/crontab.backup 2>/dev/null
   ( crontab -l 2>/dev/null; echo '* * * * * /usr/bin/echo hello from cron >> /home/you/cron-demo.log 2>&1' ) | crontab -
   sleep 90
   cat /home/you/cron-demo.log
   ```

   Change `/home/you` to your real home folder.
3. **Check.** The log should hold one `hello from cron` line per minute. Find cron's own start record in the system log (`journalctl -u cron`, est., or `/var/log/syslog`).
4. **Undo.** Restore the backup: `crontab ~/crontab.backup`. Do **not** use `crontab -r` unless you mean to delete every job. Then `rm ~/cron-demo.log ~/crontab.backup`.

## Checkpoint

Without looking back: write the cron line for 09:00 on weekdays and its `OnCalendar=` form; say which of day of month and day of week must match in cron; name the setting that fixes a missed run and the one setting it needs; say what `weekly` means in systemd; name the command that shows when each timer fires next and the one that shows what a job printed; explain what a cgroup gives systemd that a pid file does not; name one fair criticism of systemd and the answer to it; say which of Debian, Fedora, Arch and Rocky list cron by default (per the table), and with what date.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "My script works in the terminal and not from cron" | Cron's environment is minimal | Absolute paths; `PATH` in the script |
| "`@weekly` and `weekly` are the same" | Cron's is Sunday; systemd's is Monday | `systemd-analyze calendar weekly` |
| "`30 4 1,15 * 5` is Fridays that are the 1st or 15th" | In cron it is the 1st and 15th **or** Fridays | The `crontab(5)` note |
| "There is no `crontab` command, so my server is broken" | The package may not be installed | The distro table; use a timer |
| "I created the timer and nothing happens" | It is not enabled and started | `systemctl enable --now name.timer` |
| "I enabled the service, not the timer" | Enabling the service starts it at boot; it does not schedule it | Enable the `.timer` |
| "`Persistent=true` on my `OnBootSec=` timer fixes missed runs" | It has an effect only with `OnCalendar=` | The `systemd.timer(5)` page |
| "Cron logged nothing so it did not run" | It logs the start in the system log, not in your file | `journalctl -u cron` or syslog |
| "`journalctl --user` shows nothing" | It needs persistent journal storage | `/var/log/journal`, `Storage=` |
| "systemd killed cron" | They coexist; many packages ship both | `/etc/cron.daily` scripts that defer to timers |
| "The timer fires at exactly 03:15:00" | It can be up to a minute late by default | `AccuracySec=` |
| "I'll put a crontab in my container" | There is usually no cron daemon in the image | Schedule from the host |
| "`crontab -r` removes one line" | It removes your whole crontab | Back up with `crontab -l` first |

## Claims register

Retrieved on 2026-11-07 with read-only requests, unless stated. "Read" means I read the page, index or metadata text. "Run" means I ran it on one Debian 13 machine, systemd 257.

| Claim | Source | Status |
|---|---|---|
| Crontab fields, ranges, steps, names, the eight `@` strings, `%` as newline, the day-of-month OR day-of-week rule, comments not interpreted on a job line, no variable expansion, `SHELL` `LOGNAME` `HOME` set, `MAILTO`, the user column in the system crontab, `/etc/cron.d`, "examines cron entries once every minute", only hourly tasks run on a system off in the 6 to 7 am window | `crontab(5)` and `cron(8)` man pages shipped with Debian's `cron` 3.0pl1 | Read |
| The default cron log level is 1, "log the start of all cron jobs"; ends and exit status need a higher level | `cron(8)` | Read |
| Timer pair; same-name default; `OnCalendar`, `OnBootSec`, `OnUnitActiveSec`, `OnActiveSec`; `Persistent=` only with `OnCalendar=`; `RandomizedDelaySec=`; `AccuracySec=` default 1 minute; an already-active service is left running; timers are ordered after time sync | `systemd.timer(5)` | Read |
| `systemd-analyze calendar`: eleven expressions, including `weekly` = `Mon *-*-* 00:00:00`, `monthly` = `*-*-01 00:00:00`, `daily`, `hourly`, `*:0/5`, `*:0/15`, `*-*-* 0/2:23`, `Mon..Fri 09:00`, `Sun *-*-* 00:00`, `*-*-* 03:15:00` and `Fri *-*-1,15 04:30` (next hits 2027-01-01 and 2027-01-15) | One run each, 2026-11-07 | Run; yours print your own dates |
| `systemd-analyze verify`: `hello-timer` pair exit 0; `nightly` pair exit 1 with "Command /usr/local/bin/backup-check.sh is not executable: No such file or directory" | One run each in a scratch folder | Run |
| Default standard output of a service is the journal | `systemd-system.conf(5)`, `systemd.exec(5)` | Read |
| Journal storage `auto` is persistent only if `/var/log/journal` exists; `journalctl --user` needs persistent logging; `-u` with `--user` is converted to `--user-unit=`; `ForwardToSyslog=` | `journald.conf(5)`, `journalctl(1)` | Read |
| The journal file format is binary, indexed, compressed, with forward secure sealing | [systemd.io: Journal File Format](https://systemd.io/JOURNAL_FILE_FORMAT/) | Read |
| systemd places each service in its own cgroup, starts independent units in parallel, reads SysV init scripts as a limited alternative format, and finds a script when no native unit exists | `systemd(1)` | Read |
| Debian: sysvinit was the only init through squeeze; systemd default since jessie; only systemd fully supported; OpenRC and runit provided; detect systemd by `/run/systemd/system`; GNOME needed `libpam-systemd` in Bullseye | [Debian Wiki: Init](https://wiki.debian.org/Init) | Read |
| The Debian init script for cron has LSB headers and `S01cron` in `/etc/rc2.d`; `cron.service` is the unit quoted; `logrotate` and `man-db` cron.daily scripts exit when `/run/systemd/system` exists; at least 30 timers listed | Local files and `systemctl` on one Debian 13 machine | Observed; yours differ |
| `cron` priority `important` in Debian 12 and 13; `debootstrap` default installs required and important | Debian archive `Packages` index for bookworm and trixie (main, amd64); [debootstrap(8)](https://manpages.debian.org/unstable/debootstrap/debootstrap.8.en.html) | Read |
| `cron` priority `standard` in Ubuntu 24.04 and 26.04; `ubuntu-standard` depends on `cron`; `anacron` is `optional` in Debian 13 and Ubuntu; 26.04 released 2026-04-23 | Ubuntu archive `Packages` index for noble and resolute; Launchpad API for the series | Read |
| Rocky 9 and 10: `cronie` mandatory in default group `core` | Rocky BaseOS repository comps | Read. RHEL and Alma: **est.** |
| Fedora 43 and 44: no `cronie` in any comps group; `crontabs` only in non-default group `standard`; `crontabs` requires `cronie`; `cronie-1.7.2-16.fc44` in the repository | Fedora release comps and primary metadata | Read. Edition installers: **est.** |
| Arch `base` (version 3, updated 2026-02-07) does not depend on cron; `cronie` 1.7.2 in `extra` | [archlinux.org package data](https://archlinux.org/packages/) | Read |
| openSUSE Tumbleweed: no pattern requires or recommends `cron` or `cronie`; `cron` 4.2 requires `cronie` | Tumbleweed OSS repository metadata | Read. Leap, SLES and the installer: **est.** |
| Alpine uses OpenRC (`rc-service`, `rc-update`) | [Alpine Wiki: OpenRC](https://wiki.alpinelinux.org/wiki/OpenRC) | Read |
| FreeBSD uses `rc.conf` and `rc.d` startup scripts | [FreeBSD Handbook: configuration](https://docs.freebsd.org/en/books/handbook/config/) | Read |
| systemd ships `systemd-logind`, `systemd-networkd`, `systemd-resolved`, `systemd-timesyncd` and the journal | Unit files and the Debian package index on the same machine | Read; resolved and timesyncd as packages, not run |
| This repository's one cron file (weekly connector update) | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` | Read in this repository |
| Maintainer's stance on systemd, and that his recent projects ship only timers | The maintainer's own direction, 2026-11-07 | Statement of opinion; not a measurable claim |
| Gentoo and Void and Devuan init choices; BusyBox `crond` on Alpine; `OnFailure=` replacing `MAILTO`; `ProtectSystem=` and `MemoryMax=`; `@reboot` mapping; Red Hat unit name `crond`; `journalctl -u cron` output; plain-text logs degrading better; mail not set up on new servers; `crontab -r` | General knowledge | **est.** |

Not verified, plainly: starting a timer and reading its output in the journal; editing a crontab; any behavior on macOS, Windows, Alpine, Fedora, Rocky, Arch or SUSE (the package facts came from metadata, not from a running system); RHEL and Alma defaults; installer defaults and cloud-image contents on every system in the table; and everything marked **est.**

Next: back to [The terminal and your first script](Terminal-and-Your-First-Script.md) for the automation section, or on to [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md), then the [Reading order](Reading-Order.md) page.

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Cron, systemd timers and init scripts versus systemd

Previous: [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) / Next: [How a web request works](How-a-Web-Request-Works.md)

In this track: [Track 1: Foundations](Contents.md#track-1-foundations), 35 pages

- OS and Linux, git and the terminal: [Git from zero](Git-From-Zero.md) / [The terminal and your first script](Terminal-and-Your-First-Script.md) / [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) / [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) / [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md) / [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md) / [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) / [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) / [Kubernetes for beginners](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md) / [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) / **Cron, systemd timers and init scripts versus systemd**
- Networking: [How a web request works](How-a-Web-Request-Works.md) / [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) / [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) / [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) / [IPv6 adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md)
- Identity and secrets: [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) / [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) / [Secrets from day one](Secrets-From-Day-One.md) / [Password managers and passkeys](Password-Managers-and-Passkeys-What-Each-Protects-and-Where-They-Fail.md) / [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) / [Hardware security keys: YubiKey, Nitrokey, PIV](Hardware-Security-Keys-YubiKey-Nitrokey-Smart-Cards-and-PIV.md)
- Infrastructure as code: [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md) / [OpenTofu from zero](OpenTofu-From-Zero.md) / [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) / [Ansible: configuration management versus provisioning](Ansible-Configuration-Management-Versus-Provisioning.md) / [Native IaC versus open standards](Native-IaC-vs-Open-Standards-CloudFormation-ARM-Bicep-and-OpenTofu.md) / [Spacelift from zero](Spacelift-From-Zero.md) / [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md) / [Environments and promotion](Environments-and-Promotion-Dev-Staging-Production.md)
- Web hosting: [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md) / [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) / [Static against dynamic: Hugo, WordPress and recon](Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon.md) / [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md) / [Autoscaling and elasticity](Autoscaling-and-Elasticity-Scale-Out-Targets-Cooldowns-and-Cost-Caps.md)

Related pages:

- [Kubernetes for beginners](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md)
- [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md)
- [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md)
- [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md)
<!-- END GENERATED PAGE NAV bottom -->
