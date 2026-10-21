# Git from zero: your first change, step by step

Side page to the start-from-zero pages. Read it before [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) if you have never used git, a terminal or GitHub Desktop. Next: [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft for the vendor steps.** The git commands on this page are standard and stable. The vendor steps (GitHub Desktop menus, `gh` install commands, GitHub settings pages, the no-reply address format) were written from memory of the vendors' documentation and were **not** re-read for this page, because the tool to read them was not available when it was written. Every such claim is marked **est.** (estimate). Before you rely on one, open the vendor page named next to it and check it. Nothing here was run on your machine. Retrieval date for all vendor pages: **not retrieved** (page written 2026-10-21).

> **Prerequisites.** A computer with internet access and an email address you can read. No git, no command line and no GitHub knowledge. About 90 minutes the first time, including the exercise at the end.

## What you will be able to do

- Say what git is and what GitHub is, and why they are two different things.
- Make an account that is protected by a second factor.
- Copy a project to your computer (**clone** it), change a file on a **branch**, **commit** the change, **push** it, and open a **pull request**, either by clicking (GitHub Desktop) or by typing (the command line).
- Read what git prints back, and fix the five mistakes beginners make most.

## Git and GitHub are not the same thing

**Git** is a program on your computer. It remembers every version of the files in a folder, like the "version history" in a shared document, but for a whole folder, and you decide when to save a version.

**GitHub** is a website. It stores a copy of that folder online so other people can see it, copy it and suggest changes. It is to git roughly what a photo-sharing site is to a camera: the camera (git) works with no website, and the website (GitHub) is where you share what the camera took.

An analogy for the words you are about to meet:

| Everyday idea | Git word | What it means |
|---|---|---|
| A project folder with its whole history | **Repository** (repo) | The files plus every saved version of them |
| Your own photocopy of someone else's project, kept on the website | **Fork** | A copy of a repository under your account |
| Copying a project from the website to your computer | **Clone** | Download a repository, history included |
| A draft you can mark up without touching the original | **Branch** | A parallel line of history |
| Saving a version with a note | **Commit** | A snapshot plus a message saying why |
| Uploading your saved versions to the website | **Push** | Send commits from your computer to GitHub |
| Asking the owner to take your changes | **Pull request** (PR) | A proposal to merge a branch |
| The website copy you cloned from | **Remote**, usually named `origin` | The other copy git talks to |

The [Glossary](Glossary.md) has all of these. The bigger picture of why this project uses pull requests is on [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md).

## Step 1: make a GitHub account and turn on two-factor authentication

1. Open the GitHub sign-up page (github.com, then **Sign up**; est.). Pick a username. Your username is public, so do not use anything you want to keep private.
2. Use a password that is long and used nowhere else. A password manager makes that easy. [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md) says how this project thinks about password managers and security keys.
3. Turn on **two-factor authentication** (2FA, the same idea as **MFA**: a second proof beyond your password, such as a code from an app on your phone). [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md#mfa-and-identity-providers) explains why and which kind to prefer: an authenticator app or a hardware key over SMS.
4. In GitHub, open your profile picture menu, then **Settings**, then **Password and authentication** (est.), and follow the prompts to add an authenticator app (est.).
5. GitHub shows **recovery codes**. Save them in your password manager. They are the way back in if you lose your phone. Never put them in a file in a project.

Vendor page to check: GitHub Docs, "Securing your account with two-factor authentication (2FA)" (https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa; est., not retrieved).

> **Screenshot to take yourself:** the GitHub page where two-factor authentication is switched on.
> Capture: the Password and authentication settings page after 2FA is enabled, cropped to the panel.
> Look for: the line showing that an authenticator app is set up and the recovery codes option.
> Redact: your username, email address, avatar, any QR code, any recovery code, and the browser address bar and tabs.

## Step 2: make your own copy (a fork)

You will practise on a copy, never on the original, so you cannot break anything.

1. Sign in to GitHub and open this repository's page (https://github.com/ChiefGyk3D/Clouds-Against-Humanity).
2. Click **Fork** at the top right (est.). Accept the defaults and confirm.
3. GitHub takes you to your copy. The address now has your username instead of the original owner's. This is your fork.

> **Screenshot to take yourself:** your fork's front page right after forking.
> Capture: the repository header showing "forked from" under the repository name.
> Look for: your username in the repository path and the "forked from" line.
> Redact: your username, avatar, and anything in the browser chrome.

## Step 3: pick a way to work

There are two ways. Both do exactly the same thing underneath. Pick one and do the exercise at the end with it; if you are curious, do it again the other way.

| Question | GUI path: GitHub Desktop | Command-line path: git and `gh` |
|---|---|---|
| What you do | Click buttons | Type commands |
| Good for | Your first hour; seeing changes as colours | Everything later; copy-pasting from guides; servers, which have no mouse |
| Install | One installer (Windows or macOS) | git, plus the GitHub CLI (`gh`) |
| Linux | No official build that I know of (est.); use the command line | Fully supported |

If you have never used a terminal, start with the GUI path. The command-line path is still worth learning, because this project's guides (and nearly every engineering team) use it.

## The GUI path: GitHub Desktop

**GitHub Desktop** is a free app from GitHub that wraps the git commands in buttons.

Vendor pages to check: GitHub Docs, "Installing GitHub Desktop" (https://docs.github.com/en/desktop/installing-and-authenticating-to-github-desktop/installing-github-desktop; est., not retrieved) and "Cloning a repository from GitHub to GitHub Desktop" (https://docs.github.com/en/desktop/adding-and-cloning-repositories/cloning-a-repository-from-github-to-github-desktop; est., not retrieved).

### Install and sign in

1. Download the installer from the GitHub Desktop page (desktop.github.com; est.) for Windows or macOS. Run it, as you would any installer.
2. Open GitHub Desktop. Choose **Sign in to GitHub.com** (est.). Your browser opens, you approve the sign-in, and it hands you back to the app. Use your 2FA code if asked.
3. When it asks for your **name and email** (est.), type your real name or your username. For the email, see "Your name and email" below: you can choose the no-reply address so your private email is not stored in your commits.

> **Screenshot to take yourself:** GitHub Desktop signed in, before you open a project.
> Capture: the Welcome window or the main window showing that you are signed in.
> Look for: the list of your repositories, or the "Clone a repository from the Internet" option.
> Redact: your username, name, email address, avatar and the repository list if it names private projects.

### Clone your fork

1. Choose **File**, then **Clone repository** (est.).
2. Pick the **GitHub.com** tab, find your fork of `Clouds-Against-Humanity` in the list (est.), and select it.
3. Choose a **local path**: the folder on your computer where it will land. Note this path. A folder named for the project inside Documents is fine.
4. Click **Clone**. It downloads the project and its history. When asked how you plan to use the fork, choose **To contribute to the parent project** (est.).

### Make a branch

1. Click the **Current branch** button at the top (est.), then **New branch**.
2. Name it `fix-readme-word`. Use lowercase words joined by dashes.
3. Make sure it says it will branch from `main`, and click **Create branch**.

### Change a file and commit

1. Open the project folder on your computer in any text editor and change one word in `README.md`. Save the file.
2. Go back to GitHub Desktop. The **Changes** list shows `README.md` and the right-hand panel shows the difference: removed lines in red, added lines in green.
3. At the bottom left, type a short summary such as `Fix one word in the README`. Click **Commit to fix-readme-word** (est.).

### Push and open the pull request

1. Click **Publish branch** at the top (est.). This is the **push**: it uploads your branch to your fork on GitHub.
2. Click **Create Pull Request** (est.). Your browser opens on GitHub with the pull request form.
3. Check that the **base repository** is your own fork, not the original (see the exercise, step 6). Write a one-line title and click **Create pull request**.

> **Screenshot to take yourself:** GitHub Desktop with one committed change on your branch.
> Capture: the Changes view showing the diff, and the commit box.
> Look for: the red and green lines and the branch name on the top button.
> Redact: your name, email address, local folder path (it contains your computer username) and the repository list.

## The command-line path

### What a terminal is

A **terminal** is a window where you type a command and the computer types the answer back. The program inside it, the **shell**, reads what you typed. A **command** is one instruction, for example `git status`. Opening a terminal is harmless. Nothing happens until you press Enter.

How to open one:

| System | How (est.) |
|---|---|
| Windows | Press the Windows key, type `PowerShell`, press Enter. After installing git you also get **Git Bash** in the same menu. The commands on this page work in both. |
| macOS | Press Command and Space, type `Terminal`, press Enter. |
| Linux | Press Ctrl, Alt and T on most desktops, or search the applications menu for **Terminal**. |

You will see a **prompt**: a short line ending in a symbol such as `$` or `>`, which means "ready for a command". Type a command after it and press Enter. This page leaves the prompt out of the code blocks so you can copy each block as it is.

Three habits that make it easy:

- **Copy and paste** the blocks below. In most terminals paste is Ctrl, Shift and V; on macOS it is Command and V (est.).
- **Press the Up arrow** to bring back the last command.
- **Read the answer** every time. Most mistakes announce themselves.

### Install git

Vendor page to check: the git project's download page (https://git-scm.com/downloads; est., not retrieved).

| System | Install (est.) |
|---|---|
| Windows | Download the installer from git-scm.com and accept the defaults, or run the PowerShell command below |
| macOS | Run `git --version` in Terminal; if git is missing, macOS offers to install the developer tools. Or use Homebrew |
| Debian or Ubuntu | `sudo apt install git` |
| Fedora | `sudo dnf install git` |

```powershell
winget install --id Git.Git -e
```

Expected: a progress bar, then a line saying the install succeeded. Close the terminal and open a new one so it finds git.

```bash
sudo apt install git
```

Expected (Debian, Ubuntu): it asks for your password (you will not see the letters as you type), lists packages and finishes without a line starting `E:`.

Now check it:

```bash
git --version
```

Expected: one line such as `git version 2.x.y`. The exact number does not matter. If you see "command not found" or "not recognized", git is not installed or the terminal was open before you installed it: close it, open a new one and try again.

### Your name and email (one time)

Every commit records who made it. Tell git once. Use placeholders below; type your own values.

```bash
git config --global user.name "YOUR NAME"
git config --global user.email "YOUR-EMAIL"
```

Expected: nothing at all. In a terminal, silence usually means success.

Check what you set:

```bash
git config --global --list
```

Expected: lines including `user.name=YOUR NAME` and `user.email=YOUR-EMAIL`.

**A note on the email.** Your commits, and the email in them, are public once you push to a public repository. GitHub offers a **no-reply address** that hides your real one. Its format is `ID+YOUR-USERNAME@users.noreply.github.com`, where `ID` is a number GitHub gives you (est.). You find yours under **Settings**, then **Emails**, where you can also tick **Keep my email addresses private** (est.). Vendor page to check: GitHub Docs, "Setting your commit email address" (https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-email-preferences/setting-your-commit-email-address; est., not retrieved).

### HTTPS or SSH, and why start with `gh`

To talk to GitHub, git has to prove who you are. There are two ways.

- **HTTPS** uses the ordinary web address (`https://github.com/...`) and a login. Easy to start. The login is no longer a password but a **token**: a long random string that works like a password for a program.
- **SSH** uses a pair of keys: a **private key** that stays on your computer and a **public key** you give to GitHub. It is neat once set up, but there is more to set up. [Networking basics: SSH](Networking-Basics-for-This-Project.md#ssh-in-one-paragraph) explains the idea.

**The easiest start is HTTPS with the GitHub CLI.** The **GitHub CLI** (command-line interface; the program is called `gh`) signs you in through your browser, stores the credential safely and sets git up to use it. You never copy a token by hand. You can move to SSH later if you want to.

### Install the GitHub CLI

Vendor page to check: the GitHub CLI installation page (https://github.com/cli/cli#installation; est., not retrieved). It has the current commands for every system.

| System | Install (est.) |
|---|---|
| Windows | `winget install --id GitHub.cli` |
| macOS | `brew install gh` (needs Homebrew) |
| Linux | Follow the Linux section of the vendor page. Do not rely on the distribution's own `gh` package: it can be too old for the sign-in command below |

```powershell
winget install --id GitHub.cli
```

Expected: a progress bar and a success message. Open a new terminal afterwards.

```bash
gh --version
```

Expected: a line starting `gh version`, then a link to the release notes.

### Sign in with `gh auth login`

```bash
gh auth login
```

Expected: a few questions. Choose **GitHub.com**, then **HTTPS**, answer **Yes** to authenticating git with your GitHub credentials, and choose **Login with a web browser** (est.). It prints a one-time code (eight characters), you press Enter, your browser opens, you type the code and approve. The terminal then says you are logged in as your username.

Check it:

```bash
gh auth status
```

Expected: a line saying you are logged in to github.com, and which protocol git uses (`https`). It does not print the token.

### Clone your fork

Replace `YOUR-USERNAME` with your GitHub username.

```bash
git clone https://github.com/YOUR-USERNAME/Clouds-Against-Humanity.git
```

Expected: lines such as `Cloning into 'Clouds-Against-Humanity'...`, counts of objects, then `Resolving deltas: 100%`. A new folder with the project's name appears in the folder you were in.

Move into it. `cd` means "change directory" (directory is another word for folder):

```bash
cd Clouds-Against-Humanity
```

Expected: nothing printed. Your prompt usually now shows the folder name.

### Look before you leap: `git status`

```bash
git status
```

Expected, on a fresh clone: `On branch main`, `Your branch is up to date with 'origin/main'.`, and `nothing to commit, working tree clean`. The **working tree** is the files in the folder. Clean means you have not changed any. Run this command whenever you are unsure; it never changes anything.

### Make a branch

```bash
git switch -c fix-readme-word
```

Expected: `Switched to a new branch 'fix-readme-word'`. The `-c` means "create". Now `git status` starts with `On branch fix-readme-word`.

### Change a file and see it

Open `README.md` in a text editor, change one word, and save. Then:

```bash
git status
```

Expected: `Changes not staged for commit:` and, in red, `modified:   README.md`.

```bash
git diff
```

Expected: a block showing the file name, then lines starting with `-` (removed, red) for the old text and `+` (added, green) for the new. If the output stops at a `:` or `(END)`, press `q` to leave the viewer.

### Stage and commit

Git saves in two steps. First you choose what goes into the snapshot (**staging**; the chosen files sit in the **staging area**). Then you take the snapshot.

```bash
git add README.md
```

Expected: nothing printed. `git status` now shows `Changes to be committed:` in green.

```bash
git commit -m "Fix one word in the README"
```

Expected: a line like `[fix-readme-word abc1234] Fix one word in the README` and a summary: `1 file changed, 1 insertion(+), 1 deletion(-)`. The short code (`abc1234` here) is the start of the commit's fingerprint. If git instead says `Please tell me who you are`, redo the name and email step above.

### Push

```bash
git push -u origin fix-readme-word
```

Expected: lines about writing objects, then `* [new branch]      fix-readme-word -> fix-readme-word` and `branch 'fix-readme-word' set up to track 'origin/fix-readme-word'`. Often it also prints a link for opening a pull request. The `-u` links your local branch to the one on GitHub so later you can just type `git push`.

### Open the pull request

Important: a fork's pull request offers the original project by default. For the exercise you want your **own fork** as the target. The `--repo` option names the target explicitly.

```bash
gh pr create --repo YOUR-USERNAME/Clouds-Against-Humanity --base main --head fix-readme-word --title "Fix one word in the README" --body "Practice change on my own fork."
```

Expected: a web address ending `/pull/1`. Open it in a browser. That is your pull request.

## How to read the output

- **Silence is usually success.** `git add`, `git config` and `cd` print nothing when they work.
- **`error:` and `fatal:`** are failures. Read the line after it; git usually says what to do.
- **`hint:`** lines are advice, not errors.
- **`warning:`** lines mean it worked, but look.
- **Colours** help but do not carry meaning alone: removed lines begin with `-`, added lines begin with `+`. The sign is the reliable part.
- **A pager** (the `:` or `(END)` at the bottom) shows long output one screen at a time. Press `q` to leave, Space for the next page.
- **Never paste a terminal's output into a public place without reading it.** It can contain your computer's username and paths.

## When it goes wrong: the five common errors

None of these loses your work if you read first. Run `git status` before you try anything.

### 1. `fatal: not a git repository`

**You are in the wrong folder.** Git commands only work inside a project folder.

```bash
pwd
```

Expected: prints the folder you are in (on Windows PowerShell use `Get-Location`). It is probably not the cloned project.

```bash
cd Clouds-Against-Humanity
```

Expected: no output. Then `git status` works. If the folder is somewhere else, `cd` to its full path.

### 2. `Authentication failed` (or `could not read Username`)

**GitHub did not accept your login.** With HTTPS the account password does not work; the credential has to come from `gh` or a token.

```bash
gh auth status
```

Expected: if you are signed out or the token expired it says so. Fix it by signing in again:

```bash
gh auth login
```

Expected: the same questions as before, ending in a logged-in message. Then repeat the git command. Also check that you cloned *your* fork, not the original, because you cannot push to a project you do not own.

### 3. A merge conflict

A **merge conflict** happens when two changes touch the same lines and git cannot choose. Git stops and marks the file. It looks like this inside the file:

```text
<<<<<<< HEAD
the line from your branch
=======
the line from the other branch
>>>>>>> main
```

Expected: `git status` says `You have unmerged paths` and names the file. To fix it:

1. Open the file. Keep the text you want, and delete the three marker lines (`<<<<<<<`, `=======`, `>>>>>>>`) and the text you do not want.
2. Save, then tell git it is resolved:

```bash
git add README.md
git commit -m "Resolve merge conflict in the README"
```

Expected: a commit line like before. If you panic, you can undo the whole merge attempt:

```bash
git merge --abort
```

Expected: no output, and `git status` returns to normal. (If the conflict came from a rebase, use `git rebase --abort`; git tells you which one is in progress.)

### 4. `You are in 'detached HEAD' state`

**HEAD** is git's name for "where you are now". Normally it points at a branch. Detached means it points at one old commit, usually because you checked out a commit or a tag. Commits made here belong to no branch and are easy to lose.

```bash
git status
```

Expected: `HEAD detached at abc1234`. If you made no changes worth keeping:

```bash
git switch main
```

Expected: `Previous HEAD position was ...` then `Switched to branch 'main'`. If you did commit and want to keep it, give it a branch name first:

```bash
git switch -c rescue-branch
```

Expected: `Switched to a new branch 'rescue-branch'`, with your commits on it.

### 5. I committed to `main` by mistake

You meant to be on a branch but were on `main`. Fix it before you push. First look at where the commit is:

```bash
git status
```

Expected: `On branch main` and `Your branch is ahead of 'origin/main' by 1 commit.` This keeps the commit on a new branch, then moves `main` back to match the remote:

```bash
git branch fix-readme-word
git reset --hard origin/main
git switch fix-readme-word
```

Expected: the first command prints nothing. The second prints `HEAD is now at ...`. The third prints `Switched to branch 'fix-readme-word'`, and your commit is on it. **Warning:** `git reset --hard` throws away uncommitted edits. Commit them first, and only use it when `git status` showed that the only extra commit was the one you just saved on the new branch. If you already pushed to `main` of *your own fork*, it is only your copy. On a shared project, ask the owner before changing `main`; [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md#branch-protection-and-one-writer) explains why this project blocks it.

## A first exercise on your own fork

This is safe: it changes only your copy. If anything looks wrong, delete the fork on GitHub and start again. It takes about 20 minutes.

1. **Fork and clone** as above (step 2, and the clone step of your chosen path).
2. **Branch.** Make a branch called `fix-readme-word`.
3. **Change one word** in `README.md`, on that branch. Save.
4. **Commit** with a message of your own.
5. **Push** the branch.
6. **Open a pull request on your own fork.** On the pull request page, check the line near the top that says which repository and branch the pull request merges *into*. If it shows the original project, click the **base repository** drop-down and choose *your fork* (est.). If you skip this you propose your practice edit to the real project. Nothing breaks (it is closed, not merged), but avoid it.
7. **Read the page.** Open **Files changed**. You should see your one word, removed in red and added in green. Look at the checks at the bottom: your fork may run none, or some may need approval (est.).
8. **Merge it.** Click **Merge pull request**, then **Confirm merge**. GitHub then offers a **Delete branch** button.
9. **Delete the branch.** Click **Delete branch** on GitHub. Then tidy up your computer. On the command line:

```bash
git switch main
git pull
git branch -d fix-readme-word
```

Expected: `Switched to branch 'main'`; `git pull` prints `Updating ...` and `Fast-forward` with your change (it brings the merged work down to your computer); the last prints `Deleted branch fix-readme-word`. In GitHub Desktop: switch to `main` from **Current branch**, click **Fetch origin** then **Pull origin** (est.), then right-click the old branch and choose **Delete** (est.).

*Checkpoint: your fork's `main` shows the one-word change, the branch is gone, and you can say in your own words what clone, branch, commit, push and pull request each did.*

> **Screenshot to take yourself:** the merged pull request on your own fork.
> Capture: the pull request page showing the purple Merged label and the Files changed diff.
> Look for: one removed line and one added line, and the Delete branch button or message.
> Redact: your username, email address, avatar and anything in the browser chrome.

## Where to go next

- [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) shows why every change in this project goes through a pull request.
- Send a real correction to this wiki the way that page describes, from a fork like the one you just made.

## Try it yourself

- Do the exercise a second time using the other path (GUI if you used the command line, or the reverse), and compare what each shows you.
- Make a second commit on a branch, run `git log --oneline` and describe each line in your own words. Expected: one line per commit, newest first, with the short code and the message.
- Make a merge conflict on purpose on your fork: change the same line on two branches, merge one, then the other, and resolve it. Break it where it is safe.

Next: [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md).
