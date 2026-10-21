# The terminal and your first script

Side page to the start-from-zero pages. Read it after [Git from zero](Git-From-Zero.md) (which opens a terminal for the first time) and before the commands on [Droplet hardening](Droplet-Hardening.md) and [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) start to look like another language. It pairs with [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md), which starts where this one ends. Next: [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the Bash half was run, the PowerShell half was not.** I ran every Bash command and the Bash script on this page on Linux (bash 5) on **2026-10-21**; the output shown is what came back, trimmed to the lines that matter. I did **not** run any PowerShell, on any system, and I did not run the Bash script on macOS or WSL. Everything in a PowerShell block, and every macOS or WSL remark, is written from the language's documented behavior and marked **est.** (estimate) where I am least sure. I also did not run ShellCheck or PSScriptAnalyzer; the warnings shown for them are what their documentation says to expect, marked **est.** Trust what your terminal prints over what this page says. If something differs, that is worth a note on the [troubleshooting index](Troubleshooting-Index.md) or an issue.

> **Prerequisites.** You can use a mouse and a browser. You have never needed to write a program, and you do not need an account, a cloud or any money: every exercise runs on your own computer and costs nothing. About two and a half hours with the exercises (est.). If you have never opened a terminal, the short version is in [Git from zero: what a terminal is](Git-From-Zero.md#what-a-terminal-is); this page goes deeper and does not repeat that walk-through.

## What you will be able to do

- Say what a terminal, a shell, a prompt and a command each are, and open one on Windows, macOS or Linux.
- Move around the file system, make, copy, move and delete files, and read a file, with a safety habit for the one command that cannot be undone.
- Chain commands with pipes and send output to files with redirects.
- Read an environment variable, explain `PATH`, and say why the order of `PATH` matters for security.
- Read an exit code and explain why CI and every careful script depend on it.
- Spot the quoting mistakes that break scripts (a space in a name, an unset variable).
- Write, run, break, lint and fix a first script of about forty lines, in the shell for your system, with an argument, a function, a loop and error handling.
- Explain "automation is just a script plus a trigger" and name the trigger for CI, cron, a systemd timer and Windows Task Scheduler.

## Pick your track

This page teaches **one supported shell per system**, so you never have to translate in your head. Both tracks teach the same ideas, in the same order, with the same script.

| Your system | Shell on this page | Linter | Strict mode | Lists listening ports |
|---|---|---|---|---|
| Linux, macOS, or Windows with WSL (a Linux inside Windows) | **Bash** | ShellCheck | `set -euo pipefail` | `ss -tln` on Linux and WSL; macOS has no `ss` (see the script) |
| Windows (native) | **PowerShell** | PSScriptAnalyzer | `Set-StrictMode -Version Latest` and `$ErrorActionPreference = 'Stop'` | `Get-NetTCPConnection -State Listen` |

Where a step differs, you get a **Bash** block and a **PowerShell** block, or the text says the step belongs to one track only. Skip the block that is not yours. On a Mac, Terminal runs zsh by default (est.); typing `bash` inside it starts Bash, and the scripts here start with a line that asks for Bash anyway. Windows has two PowerShells: the built-in Windows PowerShell 5.1 and the newer, cross-platform PowerShell 7 (`pwsh`). The script here asks for 5.1 or later, so either works.

## What a terminal, a shell, a prompt and a command are

Four words that people use as if they were one:

- A **terminal** is the window. It shows text and passes your keystrokes on. (The name is a leftover from the 1970s, when a terminal was a physical screen and keyboard wired to a big computer.)
- A **shell** is the program running inside the window that reads what you typed and runs it. Bash, zsh and PowerShell are shells. The window and the program are separate: you can run Bash or PowerShell in the same terminal app.
- A **prompt** is the short line the shell prints that means "ready". It usually ends in `$` (Bash), `%` (zsh) or `>` (PowerShell) and often shows your folder.
- A **command** is one instruction: a program name, then **arguments** that tell it what to work on, and sometimes **options** (flags) that change how, such as `ls -l`.

A command line is read left to right and split on spaces. That one fact explains most beginner errors on this page, including the space-in-a-filename failure in the mini-loop below.

## Open a terminal

| System | How | Shell you get (est.) |
|---|---|---|
| Windows | Press the Windows key, type `PowerShell`, press Enter. For WSL, see [Microsoft's WSL install page](https://learn.microsoft.com/en-us/windows/wsl/install) and choose the Bash track afterwards. | PowerShell |
| macOS | Press Command and Space, type `Terminal`, press Enter. | zsh; type `bash` for Bash |
| Linux | Ctrl, Alt and T on most desktops, or search the applications menu for Terminal. | Usually Bash |

Opening a terminal is harmless. Nothing runs until you press Enter. Two keys to learn now: **Tab** completes a name for you (and fixes typos before they happen), and **Ctrl and C** stops a command that is running. Up arrow brings back the last command.

## Move around: the commands you will use daily

Everything in your computer is in a tree of folders (directories). The shell is always "standing" in one folder, the **current directory**, and relative names such as `notes.txt` mean "in this folder". A path starting with `/` (Bash) or a drive letter such as `C:\` (Windows) is **absolute**: it means the same place wherever you stand. `~` means your home folder in Bash.

| What you want | Bash | PowerShell |
|---|---|---|
| Where am I? | `pwd` | `Get-Location` (alias `pwd`) |
| List the folder | `ls`, `ls -l` (details), `ls -a` (include hidden) | `Get-ChildItem` (alias `ls`, `dir`); hidden: `Get-ChildItem -Force` |
| Change folder | `cd folder`, `cd ..` (up one), `cd ~` (home), `cd -` (back) | `Set-Location folder` (alias `cd`), `cd ..`, `cd ~` |
| Make a folder | `mkdir name` | `New-Item -ItemType Directory -Name name` (the helper `mkdir name` also works) |
| Copy | `cp from to` (`cp -r` for a folder) | `Copy-Item from to` (`-Recurse` for a folder) |
| Move or rename | `mv from to` | `Move-Item from to` |
| Delete | `rm file` (careful: see below) | `Remove-Item file` (try `-WhatIf` first) |
| Show a file | `cat file` | `Get-Content file` (alias `cat`) |
| Page through a file | `less file` (q quits) | `Get-Content file \| more` |
| Search text | `grep word file` | `Select-String -Pattern word -Path file` |
| First or last lines | `head -n 5 file`, `tail -n 5 file` | `Get-Content file -TotalCount 5`, `Get-Content file -Tail 5` |

PowerShell has short aliases (`ls`, `cd`, `cat`) so the names feel familiar, but the **options are different**: `ls -la` works in Bash and fails in PowerShell. When something looks like a Bash command but errors in PowerShell, that is why. Also: PowerShell passes **objects** between commands, not plain text, so `Get-ChildItem | Select-Object Name` selects a property rather than cutting a column (est.).

### rm: the one with no undo

`rm` (and `Remove-Item`) delete immediately. There is no recycle bin in the terminal. Four habits keep it safe:

1. **List before you delete.** Run `ls` with the exact same pattern first and read what it would match. `rm *.log` deletes every `.log` file in the current folder, so check where you are with `pwd`.
2. **Ask first while you learn.** `rm -i file` asks for each file. In PowerShell, `Remove-Item file -WhatIf` prints what would be deleted and deletes nothing (documented option; est.).
3. **Be wary of `-r` and `-f`.** `-r` means "and everything inside", `-f` means "do not ask, ignore errors". `rm -rf` together, aimed at the wrong place, is how people lose a machine. Never paste one you do not understand, and never put `sudo` in front of it to make an error go away.
4. **Quote variables and never let one be empty.** `rm -rf "$DIR"/*` where `DIR` is unset expands to `rm -rf /*`. Strict mode (below) refuses to run with an unset variable, which is one reason to use it.

All the exercises here delete only a practice folder you create yourself.

## Read, search and chain: files, pipes and redirects

Every command has three channels: **standard input** (what it reads), **standard output** (what it prints, called stdout) and **standard error** (its complaints, stderr). By default input is your keyboard and both outputs are your screen.

- A **redirect** sends a channel somewhere else: `command > file` writes stdout to a file (replacing it), `command >> file` appends, `command 2> errors.txt` sends stderr to a file. These work the same in Bash and PowerShell (`2>` too; est.).
- A **pipe**, `|`, feeds one command's stdout to the next command's input: `ls -l | head -n 3` lists, then keeps three lines. Small commands joined by pipes are the heart of the shell.

```bash
# Bash. Count how many lines of a file mention "error".
grep -i error app.log | wc -l
```

```powershell
# PowerShell. The same idea; Measure-Object counts the matches.
Select-String -Pattern error -Path app.log | Measure-Object
```

Where is `app.log`? Nowhere yet: both commands will report a missing file, which is the next topic.

### Getting help

Never memorize options. Ask the machine.

| What you want | Bash | PowerShell |
|---|---|---|
| The manual page | `man ls` (q quits) | `Get-Help Get-ChildItem` (add `-Examples`) |
| A short summary | `ls --help` (GNU tools; macOS often uses `man` instead) | `Get-Help Get-ChildItem -Examples` |
| What kind of thing is this name? | `type ls` or `type -a ls` | `Get-Command ls` |

Reading the manual is a skill. Search the page for the option you want (in `man`, press `/`, type the word, press Enter).

## Environment variables and PATH

An **environment variable** is a named value that every program you start can read. Programs use them for settings, such as which language to use or where your home folder is. They are also where secrets often travel, which is why the project keeps them out of files ([Doppler and secrets](Doppler-and-Secrets.md), [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md)).

| What you want | Bash | PowerShell |
|---|---|---|
| Show one | `echo "$HOME"` | `$env:USERPROFILE` |
| Show all | `env` | `Get-ChildItem Env:` |
| Set one for this window only | `export MODE=demo` | `$env:MODE = 'demo'` |
| Set one for one command only | `MODE=demo ./checkup.sh` | not a one-liner; set it, run, then remove it (est.) |

A variable you set in a window disappears when the window closes.

`PATH` is the one that matters most. When you type `git`, the shell does not search the whole disk. It reads `PATH`, a list of folders separated by `:` (Bash) or `;` (Windows), and runs the **first** program named `git` it finds, going left to right. Look at yours:

```bash
# Bash: one folder per line, and which copies of a command exist, in order.
echo "$PATH" | tr ':' '\n'
type -a ls
```

```powershell
# PowerShell: one folder per line.
$env:PATH -split ';'
```

Two consequences, both used later. If a program is installed but "command not found", its folder is not on `PATH`. And because the first match wins, **whoever controls the order of the folders controls what `git` or `ls` means.**

## Exit codes, and why CI lives on them

Every command, when it finishes, hands back a number: its **exit code**. By convention `0` means success and anything else means failure (different numbers can mean different failures; read the tool's manual). You do not see it unless you ask:

```bash
# Bash: the exit code of the last command is in $?
ls /nonexistent
echo "exit=$?"
```

Real output (2026-10-21):

```text
ls: cannot access '/nonexistent': No such file or directory
exit=2
```

```powershell
# PowerShell: $? is True or False for the last command;
# $LASTEXITCODE holds the number from the last native program or script (est.).
Get-ChildItem C:\nonexistent
$?
```

Why this matters: a person reads the words; a machine reads only the number. Every CI check is, at bottom, a command whose exit code decides pass or fail, and the merge button waits on it. The `CI green` job on [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) "fails unless every needed job finished as `success`". This repository's habit follows from that: **capture the exit code of a gate, and read the number, not the text.** The shape is:

```bash
# Run the whole gate, keep the output in a file, then print the code.
./gate-command > gate.log 2>&1; echo "gate exit=$?"
```

Three traps this habit avoids:

1. **Read `$?` immediately.** The next command overwrites it. In the real run, `false; echo "first=$?"; echo "second=$?"` printed `first=1` then `second=0`: the `echo` itself succeeded.
2. **A pipe hides the left side's failure.** `gate | grep ok` returns grep's code, not the gate's. In Bash without `pipefail`, `false | cat` ends with exit `0` (real run: the first command's status was 1, the pipeline's was 0). With `set -o pipefail` the pipeline reports 1. So never write `gate | grep something && push`.
3. **Zero does not mean the thing works.** [Lessons learned](Lessons-Learned.md) puts it plainly: "The command exited 0" and "the thing works" are different claims; check the end state too. The reverse also holds: a check that quietly does not run is worse than one that fails, which is why `scripts/ci_cost_gate.sh` says it fails when it cannot fetch the base branch. [From commit to pipeline](From-Commit-to-Pipeline.md) has you print `exit=$?` on a failing check on purpose.

## Quoting pitfalls

The shell splits a command line on spaces *before* the program sees it, and expands `$name` into its value. Quotes control both.

| Form | Bash meaning | PowerShell meaning (est.) |
|---|---|---|
| `"double"` | Keeps spaces together; still expands `$variables` | Same; also expands `$variables` and `$( )` |
| `'single'` | Keeps spaces together; **nothing** expands | Same; nothing expands |
| `\` | Escape the next character | Not an escape; the escape character is the backtick |

The rule that prevents most disasters: **put double quotes around every variable you expand** (`"$file"`, not `$file`). Real run, with a file called `my notes.txt`:

```text
$ f="my notes.txt"
$ wc -l $f
wc: my: No such file or directory
wc: notes.txt: No such file or directory
0 total
$ wc -l "$f"
3 my notes.txt
```

Without quotes the shell split one name into two. The same split on a name such as `a b` with `rm` would delete a different file called `a`. Names with spaces are normal on Windows and macOS, and an attacker can choose a name. Quote.

## File permissions, briefly

Who may read, write or run a file is a separate topic with its own page. To run a script on Linux or macOS you have to give it the "execute" bit (`chmod +x`), and why a file mode of `600` is better than `777` is on [Linux for enterprise beginners: file permissions and ownership](Linux-for-Enterprise-Beginners.md#file-permissions-and-ownership). For `sudo`, see [users, groups and sudo](Linux-for-Enterprise-Beginners.md#users-groups-and-sudo). On Windows, a script may also be blocked by the execution policy, covered in the first-script section.

## Your first script

A **script** is a text file of commands that the shell runs in order. It is the same commands you would type, saved so you can repeat them exactly. This script is a **checkup**: it looks at your machine and prints a pass or fail report. It is read-only. It changes nothing, which is the same split the repo's own scripts follow: a check that reads and reports is kept apart from a change that writes, so you can run the check as often as you like. (The cost gate is the model: `scripts/cost_check.py` reads and judges and never changes anything.)

It does five things you will meet in every script: take an **argument** (the disk limit and the command names), define a **function** (`check_disk`), run a **loop** (once per command name), handle **errors** (a failed check is counted, a bad argument is refused) and return an **exit code** (0 pass, 1 a check failed, 2 used wrongly).

Make a practice folder and open an editor. Notepad, TextEdit (plain-text mode), `nano` or any code editor all work. Save as plain text, with the exact file name shown.

```bash
# Bash
mkdir -p ~/terminal-practice && cd ~/terminal-practice
```

```powershell
# PowerShell
New-Item -ItemType Directory -Force -Path "$HOME\terminal-practice" | Out-Null
Set-Location "$HOME\terminal-practice"
```

### The Bash script: checkup.sh

```bash
#!/usr/bin/env bash
# checkup.sh: a read-only report about this machine. It changes nothing.
#
# Usage: ./checkup.sh [MAX_DISK_PERCENT] [COMMAND ...]
# Example: ./checkup.sh 80 git curl
# Exit code: 0 if every check passed, 1 if any failed, 2 if used wrongly.
set -euo pipefail

failures=0

usage() {
  echo "usage: $0 [MAX_DISK_PERCENT] [COMMAND ...]" >&2
}

# Print one report line. Arguments: status, name, detail.
report() {
  printf '%-5s %-18s %s\n' "$1" "$2" "$3"
}

pass() {
  report PASS "$1" "$2"
}

fail() {
  report FAIL "$1" "$2"
  failures=$((failures + 1)) # not ((failures++)): that returns 1 the first time and set -e would stop the script
}

check_disk() {
  local limit=$1 used
  used=$(df -P / | awk 'NR == 2 { sub("%", "", $5); print $5 }')
  if [ "$used" -lt "$limit" ]; then
    pass disk "/ is ${used}% used (limit ${limit}%)"
  else
    fail disk "/ is ${used}% used (limit ${limit}%)"
  fi
}

check_command() {
  local name=$1
  if command -v "$name" >/dev/null 2>&1; then
    pass "command:$name" "found at $(command -v "$name")"
  else
    fail "command:$name" "not found in PATH"
  fi
}

check_listeners() {
  local count
  if ! command -v ss >/dev/null 2>&1; then
    report SKIP listeners "ss is not installed here (macOS: try netstat -an -p tcp)"
    return 0
  fi
  count=$(ss -tln | tail -n +2 | wc -l)
  report INFO listeners "$count TCP sockets listening (ss -tln)"
}

main() {
  local limit=${1:-90}
  if [ "$#" -gt 0 ]; then
    shift
  fi
  case $limit in
    '' | *[!0-9]*)
      usage
      return 2
      ;;
  esac

  check_disk "$limit"
  local name
  for name in "${@:-git}"; do
    check_command "$name"
  done
  check_listeners

  if [ "$failures" -gt 0 ]; then
    echo "RESULT: $failures check(s) failed" >&2
    return 1
  fi
  echo "RESULT: all checks passed"
}

main "$@"
```

What each part is doing:

- `#!/usr/bin/env bash` (the "shebang") tells the system which program runs the file.
- `set -euo pipefail` is **strict mode**: `-e` stop at the first failing command, `-u` treat an unset variable as an error, `-o pipefail` make a pipeline fail if any part failed. It is the first line after the comments in the repo's own scripts, such as `scripts/ci_cost_gate.sh`.
- `local` keeps a variable inside its function. `"$1"` is the first argument to the function; `"$@"` is all the arguments, kept separate. `${1:-90}` means "the first argument, or 90 if there is none".
- `if ... then ... else ... fi` and `for ... in ... do ... done` are the decision and the loop. `[ "$used" -lt "$limit" ]` compares numbers.
- `df -P /` reports the disk, `command -v` asks whether a program is on `PATH`, and `ss -tln` lists listening TCP sockets, one per line after a header line (hence `tail -n +2`).
- `>&2` sends a message to stderr, so reports and complaints can be separated.

Run it:

```bash
chmod +x checkup.sh
./checkup.sh
echo "exit=$?"
```

Real output (2026-10-21; your numbers and paths will differ):

```text
PASS  disk               / is 49% used (limit 90%)
PASS  command:git        found at /usr/bin/git
INFO  listeners          11 TCP sockets listening (ss -tln)
RESULT: all checks passed
exit=0
```

Now make it fail on purpose, with a limit nothing can meet and a command that does not exist:

```bash
./checkup.sh 1 git nosuchtool
echo "exit=$?"
```

```text
FAIL  disk               / is 49% used (limit 1%)
PASS  command:git        found at /usr/bin/git
FAIL  command:nosuchtool not found in PATH
INFO  listeners          11 TCP sockets listening (ss -tln)
RESULT: 2 check(s) failed
exit=1
```

And misuse it: `./checkup.sh abc` prints the usage line and exits `2`. A name with a space, `./checkup.sh 90 git "my tool"`, is reported as one command and fails cleanly, because every variable is quoted.

### The PowerShell script: checkup.ps1

This is the same script in PowerShell. Not run by me (see the status note above); read it as carefully as you would read a stranger's script, which is the habit this page teaches.

```powershell
#Requires -Version 5.1
<#
.SYNOPSIS
checkup.ps1: a read-only report about this machine. It changes nothing.
.EXAMPLE
.\checkup.ps1 -MaxDiskPercent 80 -Command git,curl
Exit code: 0 if every check passed, 1 if any failed or the arguments were bad.
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 100)]
    [int]$MaxDiskPercent = 90,

    [string[]]$Command = @('git')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:Failures = 0

function Write-Result {
    param([string]$Status, [string]$Name, [string]$Detail)
    '{0,-5} {1,-18} {2}' -f $Status, $Name, $Detail
}

function Write-Pass {
    param([string]$Name, [string]$Detail)
    Write-Result 'PASS' $Name $Detail
}

function Write-Fail {
    param([string]$Name, [string]$Detail)
    Write-Result 'FAIL' $Name $Detail
    $script:Failures++
}

function Test-Disk {
    param([int]$Limit)
    $letter = $env:SystemDrive.Substring(0, 1)
    $drive = Get-PSDrive -Name $letter -PSProvider FileSystem
    $usedPercent = [int][math]::Round(100 * $drive.Used / ($drive.Used + $drive.Free))
    $detail = '{0}: is {1}% used (limit {2}%)' -f $letter, $usedPercent, $Limit
    if ($usedPercent -lt $Limit) { Write-Pass 'disk' $detail } else { Write-Fail 'disk' $detail }
}

function Test-CommandPresent {
    param([string]$Name)
    $found = Get-Command -Name $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $found) {
        Write-Pass "command:$Name" "found at $($found.Source)"
    } else {
        Write-Fail "command:$Name" 'not found in PATH'
    }
}

function Test-Listener {
    try {
        $count = @(Get-NetTCPConnection -State Listen).Count
        Write-Result 'INFO' 'listeners' "$count TCP sockets listening (Get-NetTCPConnection -State Listen)"
    } catch {
        Write-Result 'SKIP' 'listeners' "could not read: $($_.Exception.Message)"
    }
}

Test-Disk -Limit $MaxDiskPercent
foreach ($name in $Command) {
    Test-CommandPresent -Name $name
}
Test-Listener

if ($script:Failures -gt 0) {
    Write-Warning "RESULT: $($script:Failures) check(s) failed"
    exit 1
}
'RESULT: all checks passed'
```

What differs from the Bash version, and why:

- `Set-StrictMode -Version Latest` makes a misspelled or never-set variable an error instead of an empty string. `$ErrorActionPreference = 'Stop'` turns a cmdlet's ordinary errors into stops, like `set -e`. Neither catches a failing **native program** (an `.exe`): for those, read `$LASTEXITCODE` yourself after the call (est.).
- `param(...)` with `[ValidateRange(1, 100)]` rejects bad arguments before the script body runs; there is no separate usage function.
- Functions *output* whatever they produce, so `Write-Result` just emits a string. `Write-Host` is avoided on purpose, because the linter flags it (below).
- Windows has no `df`; `Get-PSDrive` reports the drive. `Get-NetTCPConnection -State Listen` replaces `ss -tln`. If it finds no listeners it can raise an error, which the `try` and `catch` turn into a SKIP line instead of a crash (est.).

Run it. By default Windows may refuse to run any script file (the **execution policy**). If you see "running scripts is disabled on this system", Microsoft's documentation on `Set-ExecutionPolicy` describes `RemoteSigned` for your own user as the usual fix for scripts you wrote yourself (est.; read [about_Execution_Policies](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies) first, and note that an execution policy is a guard against accidents, not a security boundary):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
powershell.exe -NoProfile -File .\checkup.ps1
"exit=$LASTEXITCODE"
```

Expect the same report shape as the Bash run, with `C:` instead of `/` (est.).

## Reading a failure

A good habit costs ten seconds: read the **last line** first, then the **first error** (later errors are often fallout), then the **line number**. The common ones:

| Message (Bash) | What it means |
|---|---|
| `Permission denied` when you run `./checkup.sh` | The execute bit is missing: `chmod +x checkup.sh`, or run it as `bash checkup.sh` |
| `command not found` | The name is wrong or its folder is not on `PATH` |
| `No such file or directory` | A path is wrong, or you are standing in the wrong folder (`pwd`) |
| `unbound variable` | Strict mode caught a variable you never set. This is the feature working |
| `syntax error near unexpected token` | A missing `fi`, `done` or quote earlier in the file; `bash -n checkup.sh` checks syntax without running anything |

In PowerShell the equivalents are "is not recognized as the name of a cmdlet", "Cannot find path", "The variable '$x' cannot be retrieved because it has not been set" (strict mode) and a parse error that points at a line and column (est.). PowerShell error text includes the line number and a caret; read it.

## Make it safe

1. **Use strict mode, always.** Bash: `set -euo pipefail` at the top. PowerShell: `Set-StrictMode -Version Latest` and `$ErrorActionPreference = 'Stop'`. Real output when a variable is never set:

   ```text
   $ bash -c 'set -u; echo "limit is $LIMIT"'
   bash: line 1: LIMIT: unbound variable
   $ bash -c 'echo "limit is [$LIMIT]"'
   limit is []
   ```

   The second one carried on with an empty value. Imagine that value was a folder name in an `rm`.
2. **Quote every expansion** (`"$var"`, `"$@"`). In PowerShell, pass values as parameters, not by gluing strings into a command.
3. **Know what strict mode does not do.** `set -e` has holes: commands in an `if` test, and the left side of `&&` and `||`, do not stop the script. And `((n++))` returns 1 when `n` was 0, so under `set -e` it kills a correct script (real run: exit 1 before "reached" printed). That is why `checkup.sh` uses `failures=$((failures + 1))`.
4. **Never run `curl ... | sh`, or `irm ... | iex`, without reading it first.** Those commands download a script and run it as you in one step, with nothing between the internet and your machine. Download it to a file instead, read it, and run it only if you understand what it does and trust the source:

   ```bash
   # Bash: download, read, then (maybe) run. Replace the placeholder with a real address.
   curl -fsSL -o install.sh https://example.com/install.sh
   less install.sh
   ```

   When the publisher gives a checksum, compare it before running (hashing is covered by the foundations pages on keys and hashes when they are written; see the [reading order](Reading-Order.md)).
5. **Do not put secrets in a script or its arguments.** They end up in the file, in your history and in process listings. Read them from an environment variable, or from a secrets manager as in [Doppler and secrets](Doppler-and-Secrets.md).
6. **Prefer read-only first.** Make a script report before it is allowed to change anything. Add a "dry run" option before you add a delete.

## Lint it

A **linter** reads your script without running it and warns about common mistakes. Use one for your shell.

**Bash: ShellCheck.** Install from your package manager (the project's README, read 2026-10-21, lists `sudo apt install shellcheck` for Debian and Ubuntu, `dnf install ShellCheck` for Fedora and relatives, and `brew install shellcheck` for macOS; on Windows it lists `winget install --id koalaman.shellcheck`, `choco install shellcheck` and `scoop install shellcheck`). Source: [ShellCheck README](https://github.com/koalaman/shellcheck/blob/master/README.md), retrieved 2026-10-21. Run it:

```bash
shellcheck checkup.sh
echo "exit=$?"
```

The manual (retrieved 2026-10-21 from the [ShellCheck man page source](https://github.com/koalaman/shellcheck/blob/master/shellcheck.1.md)) documents `-s` / `--shell` to pick the shell dialect (`sh`, `bash`, `dash`, `ksh`, `busybox`), `-S` / `--severity` to set the minimum level (`error`, `warning`, `info`, `style`) and these exit codes: `0` clean, `1` scanned with issues, `2` some files could not be processed, `3` bad syntax in how it was invoked. So a CI step that runs `shellcheck` fails on the exit code, like any other check. I expect `checkup.sh` to come back clean (est.: I did not run it). Now the version with the mistake from earlier:

```bash
f="my notes.txt"
wc -l $f
```

ShellCheck's documentation names the warning for an unquoted variable **SC2086** ("Double quote to prevent globbing and word splitting"; est.: wording from memory, check the [SC2086 wiki page](https://www.shellcheck.net/wiki/SC2086)). Each warning has a page that explains the fix.

**PowerShell: PSScriptAnalyzer.** The project's README (retrieved 2026-10-21, [PSScriptAnalyzer README](https://github.com/PowerShell/PSScriptAnalyzer/blob/main/README.md)) gives the install as `Install-Module -Name PSScriptAnalyzer`. The cmdlet reference (retrieved 2026-10-21, [Invoke-ScriptAnalyzer](https://github.com/PowerShell/PSScriptAnalyzer/blob/main/docs/Cmdlets/Invoke-ScriptAnalyzer.md)) documents the parameters `-Path`, `-Recurse`, `-Severity` (values Error, Warning, Information, ParseError) and `-EnableExit`, which "exits the PowerShell sessions and returns an exit code equal to the number of error records", useful in CI. Run it:

```powershell
Install-Module -Name PSScriptAnalyzer -Scope CurrentUser
Invoke-ScriptAnalyzer -Path .\checkup.ps1
```

Expect nothing printed when the script is clean (est.; not run). If you replace `Write-Output` with `Write-Host` it should flag `PSAvoidUsingWriteHost` (est.: a built-in rule I know of, not run here).

Treat warnings as a to-do list, not noise. A fix that silences a warning with a comment such as `# shellcheck disable=...` needs a reason written next to it, or it is just hiding the finding.

## Put it in version control

A script you will keep belongs in git: you get history, a way back from a bad edit, and review. This is the same loop as [Git from zero](Git-From-Zero.md), which explains each step (install and the one-time name and email setup are there too):

```bash
git init
git add checkup.sh
git commit -m "Add machine checkup script"
git log --oneline
```

The PowerShell track uses the same four commands with `checkup.ps1`. In a real project the script would be a pull request, and the shell linter would run in CI beside the other checks on [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md).

## Automation is a script plus a trigger

A script runs when something tells it to. The "something" is the **trigger**. Everything called automation in this wiki is a script and a trigger:

| Automation | The script | The trigger |
|---|---|---|
| Continuous integration ([CI](CI-Tests-and-Cost-Gate.md)) | The checks: tests, linters, the cost gate | A pull request or a push |
| cron (Linux, macOS) | Any command or script | A time pattern, such as every 15 minutes: `*/15 * * * * /home/you/terminal-practice/checkup.sh` (a crontab line; est.) |
| systemd timer (Linux) | A service unit that runs the script | A timer unit with a calendar or interval; list yours with `systemctl list-timers` (read-only) |
| Task Scheduler (Windows) | A program or `powershell.exe -File` | A time, a boot, a login or an event; list with `Get-ScheduledTask` (read-only; est.) |

Three things go wrong in the same way for all of them. **The environment is different:** a scheduled job usually has a smaller `PATH` and no terminal, so use absolute paths and set `PATH` at the top of the script. **Nobody is watching:** the exit code and a log are the only voice the job has, so make failures loud (a non-zero exit code, a line in a log) and never swallow them. **The trigger is a permission:** whoever can edit the script, or the file it calls, can run code as whoever the job runs as. Treat a scheduled script as privileged. See [Linux for enterprise beginners: services with systemd](Linux-for-Enterprise-Beginners.md#services-with-systemd) for unit files.

## Exercises

All of them run on your own computer and cost nothing. They touch only `~/terminal-practice` (or `$HOME\terminal-practice`) that you created above. Each has Predict, Do, Check and Undo.

### Exercise 1: navigate and make a mess you can clean up

**Predict.** After `mkdir lab`, `cd lab`, creating `a.txt`, and `cd ..`, what does `pwd` print, and does `ls` show `a.txt`? Write both answers down.

**Do (Bash).**

```bash
cd ~/terminal-practice
mkdir lab && cd lab
echo "first line" > a.txt
echo "second line" >> a.txt
cd ..
pwd
ls
cat lab/a.txt
```

**Do (PowerShell).**

```powershell
Set-Location "$HOME\terminal-practice"
New-Item -ItemType Directory -Name lab | Out-Null
Set-Location lab
'first line' | Set-Content a.txt
'second line' | Add-Content a.txt
Set-Location ..
Get-Location
Get-ChildItem
Get-Content lab\a.txt
```

**Check.** `pwd` shows `terminal-practice` (not `lab`), `ls` shows `lab` but not `a.txt` (it is one level down), and `cat` shows two lines. If `a.txt` had one line, you used `>` twice: it replaces, `>>` appends.

**Undo.** List first, then delete only the practice folder: `ls lab`, then `rm -r lab` (Bash), or `Remove-Item -Recurse lab -WhatIf` and, if the list is only what you expect, the same line without `-WhatIf` (PowerShell).

### Exercise 2: pipes and exit codes

**Predict.** `grep` exits `0` when it finds a match and `1` when it finds none. What will the exit code be for searching `first` in `a.txt`, and for `zebra`? And what will `false | cat` give with and without `pipefail`?

**Do (Bash).**

```bash
cd ~/terminal-practice
printf 'first line\nsecond line\n' > a.txt
grep first a.txt; echo "exit=$?"
grep zebra a.txt; echo "exit=$?"
false | cat; echo "exit=$?"
set -o pipefail; false | cat; echo "exit=$?"; set +o pipefail
```

**Do (PowerShell).**

```powershell
Set-Location "$HOME\terminal-practice"
"first line", "second line" | Set-Content a.txt
$m = Select-String -Pattern zebra -Path a.txt
$null -eq $m
```

**Check.** Bash: `0`, `1`, `0`, `1`. The first two are the search result as a number; the last two show a pipeline hiding a failure until `pipefail`. PowerShell returns no match as an empty result, not an error: `True` means nothing matched. (PowerShell has no `pipefail` flag; est.)

**Undo.** `set +o pipefail` in the same line restored the setting. Close the window if unsure; settings do not survive it.

### Exercise 3: run the checkup and read the failure

**Predict.** Running `checkup` with a disk limit of `1`: which lines turn FAIL, and what is the exit code?

**Do.** Create the script from this page, then run it twice with the arguments shown above (the Bash `./checkup.sh 1 git nosuchtool`, or the PowerShell `powershell.exe -NoProfile -File .\checkup.ps1 -MaxDiskPercent 1 -Command git,nosuchtool`), each followed by printing the exit code.

**Check.** FAIL on `disk` and on `nosuchtool` and exit `1`. The report lines name what failed; the exit code is for machines. The words are for you and the number is for the machine.

**Undo.** Nothing was changed. The script is read-only.

### Exercise 4: break it, then fix it

It is the **Break** step of the mini-loop below: do it there.

### Exercise 5: read the repository's own scripts (read-only)

**Predict.** `scripts/ci_cost_gate.sh` starts with a long comment. Before opening it, guess what two things that comment will say.

**Do.** From a clone of this repository (the [Git from zero](Git-From-Zero.md) page shows how), print the script's top lines: `head -n 25 scripts/ci_cost_gate.sh` (Bash), or `Get-Content scripts/ci_cost_gate.sh -TotalCount 25` (PowerShell). Find the line `set -euo pipefail` and the lines that print `FAIL` and `exit 1`.

**Check.** The comment says what the script does, how to run it, and which environment variables it reads. It fails loudly instead of quietly skipping a check. Do the same for `scripts/demo_monitoring.sh`.

**Undo.** Nothing was changed. You only read.

## Build it, break it, detect it, evade it, defend it

A short loop, entirely on your own machine and your own files.

**Build.** The `checkup` script above. Run it until you can predict every line of its output.

**Break.** Two ways, each in a copy so the original stays as it was (`cp checkup.sh broken.sh`; `Copy-Item checkup.ps1 broken.ps1`):

1. *A space in a filename.* In `broken.sh`, remove the quotes in `check_command` so it reads `command -v $name`, then run `./broken.sh 90 "my tool"`. The shell splits the name in two and asks about both words. Or just repeat the `wc -l $f` example with `my notes.txt`.
2. *An unset variable.* Add the line `echo "limit is $LMIT"` (a typo for `limit`) to the top of `main` in a copy with the `set -u` removed. It prints an empty value and carries on. In PowerShell, remove the `Set-StrictMode` line and misspell a variable the same way.

**Detect.** Put strict mode back and the typo stops the script with `unbound variable` (PowerShell: "has not been set"). Run `shellcheck broken.sh` (or `Invoke-ScriptAnalyzer`): ShellCheck should flag the unquoted variable (SC2086, est.) and the unused or misspelled variable (est.). Also `bash -n broken.sh` checks syntax only.

**Evade.** This part is about how failures hide, so you can recognize them. Words only; nothing here touches another machine.

- *Swallowing the failure in the script.* `risky_command || true`, `set +e`, `2>/dev/null`, `if command; then ...` (the `if` takes the exit code and discards it), and ignoring `$?`, all make a script exit `0` while something failed. Real run: `false || true; echo "exit=$?"` printed `exit=0`. That is how a CI step goes green over a broken check. A reviewer should ask of every `|| true`: what failure is this hiding, and why is that acceptable? An answer should be written beside it.
- *Hiding in shell history.* The history file is a convenience, not an audit log. A command that begins with a space can be left out (with `HISTCONTROL=ignorespace`, a setting many systems have; est.), and history is usually written when the shell exits, so a shell that is killed can lose its last commands (est.). Anyone with access can edit or delete the file. Evidence of what ran on a server comes from logs shipped off the machine ([Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md)), not from the account's own history.
- *Hiding in `PATH` order.* Because the first match on `PATH` wins, a folder placed earlier in the list lets a program named `ls` or `git` in that folder run instead of the real one. `type -a ls` lists every copy in order (real run: `/usr/bin/ls` then `/bin/ls`, both normal). A folder you can write to, or `.` (the current folder), early in `PATH` is the risk. PowerShell does not run a program from the current folder unless you write `.\name` (est.).

**Defend.**

- Strict mode and quoting in every script, and a linter in CI so the habit is enforced instead of remembered.
- No `|| true` without a written reason; check the exit code of everything that matters and fail with a clear message and a non-zero code.
- Absolute paths, or a `PATH` set at the top, in scripts that run on a schedule; no writable folders ahead of system folders in `PATH`; run `type -a name` when a command behaves oddly.
- Treat history as a convenience; ship logs elsewhere for evidence. Read a script before running it, and never pipe the internet into a shell.
- Keep scripts read-only until they need to write, and keep them in version control so a change is a reviewed diff.

**Undo.** Delete the `broken.*` copies (`ls broken.*` first, then `rm broken.sh`; `Remove-Item broken.ps1`).

## What to read next

Read [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) for packages, services, permissions and logs. Then go back to [Droplet hardening](Droplet-Hardening.md) or [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) and see how much of it reads now. For where the checks in this repository run, see [From commit to pipeline](From-Commit-to-Pipeline.md).

## Claims register

| Claim | Source | Retrieved | Status |
|---|---|---|---|
| The Bash commands, the Bash script and its output on this page | Run on Linux, bash 5, by the author | 2026-10-21 | Run |
| PowerShell commands and the PowerShell script | Written from PowerShell's documented behavior | n/a | Not run; est. |
| macOS and WSL remarks | Not run | n/a | est. |
| ShellCheck install methods (apt, dnf, brew, winget, choco, scoop) | [ShellCheck README](https://github.com/koalaman/shellcheck/blob/master/README.md) | 2026-10-21 | Read |
| ShellCheck options `-s`/`--shell`, `-S`/`--severity` and exit codes 0 to 4 | [ShellCheck man page source](https://github.com/koalaman/shellcheck/blob/master/shellcheck.1.md) | 2026-10-21 | Read |
| ShellCheck code SC2086 and its wording | [ShellCheck wiki](https://www.shellcheck.net/wiki/SC2086) | not read | est. |
| PSScriptAnalyzer install command | [PSScriptAnalyzer README](https://github.com/PowerShell/PSScriptAnalyzer/blob/main/README.md) | 2026-10-21 | Read |
| `Invoke-ScriptAnalyzer` parameters `-Path`, `-Recurse`, `-Severity`, `-EnableExit` | [Invoke-ScriptAnalyzer reference](https://github.com/PowerShell/PSScriptAnalyzer/blob/main/docs/Cmdlets/Invoke-ScriptAnalyzer.md) | 2026-10-21 | Read |
| `Get-NetTCPConnection -State Listen` behavior, execution policy advice, `-WhatIf` | Microsoft documentation | not read | est. |
| The `CI green` description and the gate habit | [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md), `scripts/ci_cost_gate.sh` in this repository | 2026-10-21 | Read |
| Cost of everything on this page | None of it spends money | n/a | $0 |
