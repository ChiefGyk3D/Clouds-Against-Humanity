# Honeyfiles on a host you own: a decoy file and a watcher you build

Lesson 4 of the [deception and honeypots track](Deception-and-Honeypots-Start-Here.md). A foundations side page to [Build your own mini SOC](Build-Your-Own-Mini-SOC.md): it builds, from scratch and on one folder, the idea that the stage 2 audit work applies to a whole host. Next: [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md), lesson 5.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the Linux watcher was run once; the PowerShell watcher and everything with auditd or Wazuh were not.** On **2026-10-21** the author ran every Bash command in the Linux exercises with `inotifywait` 4.23.9.0 (from the `inotify-tools` package in a Debian-based repository, unpacked and run without installing) and pasted trimmed output. **Not run:** the PowerShell watcher (no Windows machine; **est.**), the audit-framework examples (they need administrator rights and the author ran none), and the optional Wazuh report. macOS has no `inotify`; the exercises do not cover it.

> **Prerequisites.** [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md) and [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) (minimums 6 to 8). [The terminal and your first script](Terminal-and-Your-First-Script.md) for scripts, pipes and exit codes. A Linux machine you own, or a Windows machine for the PowerShell track. About 2 hours (est.). Cost: none; the Linux package is free, and the PowerShell watcher is built into Windows PowerShell and .NET (est.). Nothing leaves your computer.

## What you will be able to do

- Build a decoy file and a watcher that prints an alert when the file is touched.
- Say which actions on a file raise an event and which do not, from a table you made by trying them.
- Say why "someone read it" and "someone copied it" look identical to this kind of watcher, and what would tell them apart.
- Say why a file name is data a stranger can choose, show a forged alert line made with one, and fix the watcher.
- Explain where an operating-system audit rule does a better job than a script, and why the project's stage 2 uses one.

## The idea

A **honeyfile** is a decoy file with an attractive name (`passwords-backup-OLD.txt`), placed where nobody legitimate has a reason to open it, and watched. Two parts matter: the **name** that makes it worth opening, and the **watch** that notices.

The operating system can tell a program when a file is opened or read. On Linux the feature is **inotify**: a program asks the kernel to report events on a folder, and the kernel sends one each time something is opened, read, changed, renamed or deleted. `inotifywait` is a small command that turns those into text lines. On Windows the nearest built-in is the .NET `FileSystemWatcher`, which PowerShell can drive.

A script watcher is a good way to *learn* the idea. A real host would use the system's audit framework, which logs who did it and survives a script being killed. That is the last section.

## The Linux exercises

### Set up

Install the tool (Debian or Ubuntu, where the package exists as `inotify-tools`; other distributions name it similarly, est.):

```bash
sudo apt install inotify-tools
```

Make a lab folder and a decoy file with invented content:

```bash
mkdir -p ~/deception-lab/honeyfile/bait && cd ~/deception-lab/honeyfile
printf 'DECOY - invented content, nothing real here\n' > bait/passwords-backup-OLD.txt
```

Save this as `watch.sh` in `~/deception-lab/honeyfile` and make it executable:

```bash
#!/usr/bin/env bash
# Usage: ./watch.sh FOLDER [LOGFILE]   - every touch of a file in FOLDER is an alert.
set -u
dir=${1:?folder to watch}
log=${2:-alerts.log}
stamp='^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[+-][0-9]{4}$'
inotifywait -m -q -e open,access,modify,attrib,moved_from,moved_to,delete,create \
  --timefmt '%Y-%m-%dT%H:%M:%S%z' --format '%T|%e|%f' "$dir" |
while IFS='|' read -r ts events name; do
  # A file name is data an attacker can choose (it may hold a newline). Only a line that
  # starts with a real timestamp is an event; anything else is dropped, never echoed.
  [[ $ts =~ $stamp ]] || { echo "NOTE: dropped a line that is not an event" >&2; continue; }
  case $events in *ISDIR*) continue ;; esac   # listing the folder is not touching a file
  printf 'ALERT time=%s event=%s file=%q\n' "$ts" "$events" "$name" | tee -a "$log"
done
```

```bash
chmod +x watch.sh
```

What it does, line by line. `-m` keeps watching instead of stopping at the first event. `-q` hides the tool's own chatter. `-e` lists the events to report. `--format` prints a timestamp, the event names and the file name separated by `|`. The `while read` loop turns each into an `ALERT` line and appends it to `alerts.log`. `%q` prints the file name in a form that cannot contain a raw newline.

Start it in a **second terminal**, in the same folder, and leave it running:

```bash
./watch.sh bait
```

### Exercise 1: what raises an event, and what does not

**Predict.** For each action below, write **yes** or **no**: will an alert appear? Write your guess for `cat` and `cp` separately.

1. `ls bait` (list the folder)
2. `ls -l bait/passwords-backup-OLD.txt` and `stat bait/passwords-backup-OLD.txt`
3. `cat bait/passwords-backup-OLD.txt`
4. `cp bait/passwords-backup-OLD.txt ../copy.txt`
5. `echo more >> bait/passwords-backup-OLD.txt`
6. `mv bait/passwords-backup-OLD.txt bait/x.txt`, then back again
7. `rm bait/passwords-backup-OLD.txt`

**Do.** In the first terminal, run the seven commands one at a time, in order. Re-create the file (the `printf` line above) before you run 6 if you removed it.

**Check.** From the 2026-10-21 run (the seven actions in order; a blank row means nothing was printed):

| # | Action | What the watcher printed |
|---|---|---|
| 1 | `ls bait` | nothing (the folder's own events are skipped by the `ISDIR` line) |
| 2 | `ls -l` of the file, and `stat` | nothing |
| 3 | `cat` | `OPEN` then `ACCESS` |
| 4 | `cp` out of the folder | `OPEN` then `ACCESS`, **the same two lines as `cat`** |
| 5 | append | `OPEN` then `MODIFY` |
| 6 | rename and rename back | `MOVED_FROM` and `MOVED_TO`, four lines in all |
| 7 | `rm` | `DELETE` |

Four things to take from it:

- **Looking at a file's details is not opening it.** Listing a folder, `ls -l` and `stat` read the file's *record*, not its content, and raised nothing. A watcher on the file's *contents* will not notice someone browsing names. That is a gap and a mercy: it is why the file name, not the contents, has to do the work of attracting.
- **`ACCESS` means someone read the data.** An open without a read raises only `OPEN`.
- **A read and a copy look identical.** `cat` and `cp` both raise `OPEN` and `ACCESS` on the source. The copy shows up in the *destination* folder, which this watcher does not see. To tell "read" from "copied", you would also need to watch where files can be written, or watch for the program doing it (the audit framework records the program).
- **A change is a stronger signal than a read.** `MODIFY`, `MOVED_*` and `DELETE` mean someone did something to the decoy, not only to look at it.

A line looked like this:

```text
ALERT time=2026-10-21T18:52:28-0400 event=OPEN file=passwords-backup-OLD.txt
```

**Undo.** Re-create the decoy if you removed it. Stay in the lab folder for the next exercise.

### Exercise 2: a file name that forges an alert

**Predict.** A file name can contain a newline. If someone creates a file in the watched folder whose name contains `ALERT fake`, what will the log contain?

**Do.** The first version of the watcher, before the two guard lines were added, printed the name as it came. Its loop was only:

```bash
while IFS='|' read -r ts events name; do
  printf 'ALERT time=%s event=%s file=%s\n' "$ts" "$events" "$name"
done
```

With that loop, creating a file whose name holds a newline (`touch $'bait/line1\nALERT fake'`) produced extra lines. From the 2026-10-21 run of the unguarded version:

```text
ALERT time=2026-10-21T18:52:42-0400 event=CREATE file=line1
ALERT time=ALERT fake event= file=
```

The second line was never an event: it is the file's name, and it forged an `ALERT` line in the log. Now try the guarded `watch.sh` from above (start it again if you stopped it):

```bash
touch 'bait/a|b'
touch $'bait/line1\nALERT fake'
```

**Check.** The guarded watcher prints the file with a `|` in its name safely (`file=a\|b`) and drops the stray line:

```text
ALERT time=2026-10-21T18:52:55-0400 event=CREATE file=a\|b
ALERT time=2026-10-21T18:52:55-0400 event=CREATE file=line1
NOTE: dropped a line that is not an event
```

Two guards did it. The timestamp pattern accepts only lines that start with a real timestamp, so a name that spills onto a second line is dropped without being echoed. `%q` prints names so a stray newline cannot start a new line. The first line shows the truncated name `line1`; that is the cost, and an alert is still raised. The lesson, which comes back in lesson 5: **text a stranger can choose is data. Never treat it as part of your own log format.**

**Undo.** Delete the test files:

```bash
rm -f ~/deception-lab/honeyfile/bait/'a|b' ~/deception-lab/honeyfile/bait/line1*
```

### Exercise 3: who tripped it, and when it is a false alarm

**Predict.** Name three ordinary things that could raise `OPEN` and `ACCESS` on a decoy file in real life (lesson 2 listed some).

**Do.** Open the file with a text editor, a file manager or `grep -r secret bait/`, and see what the watcher prints for each.

**Check.** `grep -r` raises `OPEN` and `ACCESS` the same as `cat`. A file manager or editor may raise more or fewer lines, depending on the program (est.; try it). So: the watcher knows *that* and *when*, and it does not know *which person* or even *which program*. The audit framework below adds the program and the account.

**Undo.** Close the editor.

### In production: the audit framework (shown, not run)

The Linux audit framework (`auditd`) can watch a path and record **who** did what and with which program. A watch rule has this shape (from the Wazuh documentation's example, which watches `/home` for reads with the tag `audit-wazuh-r`):

```bash
sudo auditctl -w /path/to/bait -p r -k decoy-read      # est.; not run: needs administrator rights
sudo ausearch -k decoy-read                            # est.; not run: reads the events back
```

Wazuh's documentation describes the use case "monitoring file and directory access" with exactly this kind of rule, and shows the alerts in its dashboard (see the register). The repository's stage 2 work ships an opt-in `auditd` and Wazuh agent on the connector hosts; it is written and has never been applied ([Roadmap](Roadmap.md#stage-2-logging-and-the-link-home-design-merged-cloud-side-in-progress-not-applied)). So the honest status: the idea in this lesson is the same one stage 2 would use, but nothing here is connected to it.

Optional, if you have a Wazuh test install and a stage 2 style agent: add a rule like the one above for your lab folder, trip it, and find the alert in the dashboard. Treat it as a draft: the author ran none of it. Record what you changed.

## The PowerShell watcher (est., not run)

Windows has no `inotify`. PowerShell can drive the .NET `FileSystemWatcher`. Save the following as `watch.ps1` in `$HOME\deception-lab\honeyfile`, make a `bait` folder with a decoy file, and run `.\watch.ps1`:

```powershell
$dir = (Resolve-Path .\bait).Path
$log = (Get-Location).Path
$w = New-Object System.IO.FileSystemWatcher $dir
$w.NotifyFilter = [System.IO.NotifyFilters]'FileName, LastWrite, LastAccess, Attributes, Size'
$w.EnableRaisingEvents = $true
$action = {
  $e = $Event.SourceEventArgs
  $name = $e.Name -replace '[\r\n]', '?'    # a file name is data a stranger can choose
  $line = 'ALERT time={0} event={1} file={2}' -f (Get-Date -Format o), $e.ChangeType, $name
  Write-Host $line
  Add-Content -Path (Join-Path $Event.MessageData 'alerts.log') -Value $line
}
foreach ($kind in 'Changed', 'Created', 'Deleted', 'Renamed') {
  Register-ObjectEvent $w $kind -Action $action -MessageData $log | Out-Null
}
```

To stop it and clean up: `Get-EventSubscriber | Unregister-Event; $w.Dispose()`.

**Limits, honestly.** The watcher reports changes, creations, deletions and renames. It **does not reliably report a plain read**: the "last access" notification depends on whether Windows is updating last-access times on that disk, which can be switched off or delayed (est.). So the PowerShell watcher cannot repeat exercise 1 for `cat`. Windows has a built-in way to audit reads on a file (an audit policy and an entry on the file that asks for it, which write events to the Security log), but the author did not read or run it; it is the Windows equivalent of the `auditd` section above and is **est.** here.

## Build, break, detect, evade, defend

- **Build.** The decoy and the watcher.
- **Break.** Try to get the content without raising an alert. `ls -l` and `stat` showed that the *metadata* is free. What else? Read the file through a path that bypasses your watched folder (a backup, a snapshot, a copy someone made earlier), or from another machine that mounts the folder. Try one you can do safely on your own folder and record the result.
- **Detect.** Add one rule: a **change** (`MODIFY`, `MOVED_*`, `DELETE`) is worse than a read. Make the watcher print `ALERT` for reads and `ALERT-HIGH` for changes. Predict which line a `cp` gives, then test.
- **Evade.** An intruder who suspects a decoy reads a *copy* from a backup, reads the folder's metadata first (as above) to check the file's age and owner, or simply kills the watcher process. If the watcher is the only guard, killing it is a complete evasion, which is the case for the audit framework (it runs in the kernel and can be made tamper-resistant, est.) and for an alert when the watcher itself goes quiet.
- **Defend.** Use names that fit their neighbors; use plausible but invented content; keep the folder out of backups and scans, or allow-list those programs by name; test the alert on a schedule; ship the log off the machine so deleting it locally does not erase it; watch the watcher.
- **Flip the board.** You are the intruder with a shell on this host. List what you would do in the first minute to learn whether a folder is watched: process list, kernel module list, rules in the audit framework. Then be the defender who has to make that list less useful.

## Common mistakes

| Mistake | Why it hurts | Better |
|---|---|---|
| Putting the decoy in a backed-up or scanned folder. | The alert fires every night. | Keep it out, or allow-list by program. |
| Echoing a file name into the log as-is. | A stranger can forge log lines. | Check the line's shape and quote the name (`%q`). |
| Watching only the file's contents. | `ls -l` and `stat` reveal it for free. | Accept that names are the bait; do not rely on the contents. |
| Believing a read and a copy are different events. | They look the same here. | Watch where copies land, or use the audit framework. |
| Running the watcher with no one to read the log. | A baseline of zero and a value of zero. | Send it somewhere a person reads, or to the SIEM in lesson 5. |

## Claims register

Retrieved 2026-10-21 unless stated.

| Claim | Source | Status |
|---|---|---|
| `inotifywait` options used (`-m`, `-q`, `-e open,access,modify,attrib,moved_from,moved_to,delete,create`, `--timefmt`, `--format` with `%T`, `%e`, `%f`) | `inotifywait --help` from `inotify-tools` 4.23.9.0, unpacked from a Debian-based repository and run | Run on Linux. The package name on other distributions is **est.** |
| The event results in the exercise 1 table, and the forged line in exercise 2 | Run on Linux on 2026-10-21 | Run |
| Windows `FileSystemWatcher` behavior; that it does not reliably report a plain read; that last-access updating can be off or delayed | General knowledge of .NET and Windows | **est.**; not run |
| Windows built-in file auditing writes to the Security log | General knowledge | **est.**; not read, not run |
| An audit rule has the shape `-w <path> -p r -k <key>`; Wazuh's documentation describes monitoring file and directory access with such rules and shows alerts in its dashboard | [Wazuh: monitoring file and directory access](https://documentation.wazuh.com/current/user-manual/capabilities/system-calls-monitoring/use-cases/monitoring-file-and-directory-access.html) | Read; not run |
| The stage 2 `auditd` and Wazuh agent are opt-in and never applied | [Roadmap](Roadmap.md#stage-2-logging-and-the-link-home-design-merged-cloud-side-in-progress-not-applied) | Read in this repository |
| That the audit framework can be made tamper-resistant | General knowledge | **est.** |

Not verified, plainly: the whole PowerShell track; macOS; the audit commands; the Wazuh report; behavior of file managers and editors on your system.

Next: [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md), lesson 5. Or back to the [track hub](Deception-and-Honeypots-Start-Here.md).
