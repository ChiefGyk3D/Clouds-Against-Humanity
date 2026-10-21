# Git from zero: your first change, step by step

Side page to the start-from-zero pages. Read it before [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) if you have never used git, a terminal or GitHub Desktop. Next: [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: vendor steps checked against vendor documentation.** The git commands on this page are standard and stable. The vendor steps (GitHub settings pages, GitHub Desktop menus, `gh` and git install commands, the no-reply address format) were read from the vendors' own pages on **2026-10-21**; each such passage names its source URL and that date. Vendor interfaces change, so check the page if a button has moved. Anything I could not read on a vendor page is marked **est.** (estimate) and is a guess to check. Nothing here was run on your machine.

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

1. Open github.com and choose **Sign up** (est.; the sign-up page was not read). Pick a username. Your username is public, so do not use anything you want to keep private.
2. Use a password that is long and used nowhere else. A password manager makes that easy. [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md) says how this project thinks about password managers and security keys.
3. Turn on **two-factor authentication** (2FA, the same idea as **MFA**: a second proof beyond your password, such as a code from an app on your phone). [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md#mfa-and-identity-providers) explains why and which kind to prefer: an authenticator app or a hardware key over SMS.
4. In the upper-right corner of any GitHub page, click your profile picture, then **Settings**. In the "Access" section of the sidebar, click **Password and authentication**. Under "Two-factor authentication", click **Enable two-factor authentication**. GitHub recommends a **TOTP** app (time-based one-time password: an authenticator app on your phone or computer) over text messages. Scan the QR code with the app, type the six-digit code it shows, and continue.
5. Under "Save your recovery codes", click **Download**, save the codes in your password manager, then click **I have saved my recovery codes**. They are the way back in if you lose your phone. Never put them in a file in a project.

Source: GitHub Docs, "Configuring two-factor authentication" (https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa/configuring-two-factor-authentication), retrieved 2026-10-21.

> **Screenshot to take yourself:** the GitHub page where two-factor authentication is switched on.
> Capture: the Password and authentication settings page after 2FA is enabled, cropped to the panel.
> Look for: the line showing that an authenticator app is set up and the recovery codes option.
> Redact: your username, email address, avatar, any QR code, any recovery code, and the browser address bar and tabs.

## Step 2: make your own copy (a fork)

You will practise on a copy, never on the original, so you cannot break anything.

1. Sign in to GitHub and open this repository's page (https://github.com/ChiefGyk3D/Clouds-Against-Humanity).
2. In the top-right corner of the page, click **Fork**. Leave "Owner" as your own account, leave the name as it is, and click **Create fork**. Optionally tick "Copy the DEFAULT branch only"; that is enough here.
3. GitHub takes you to your copy. The address now has your username instead of the original owner's. This is your fork.

Source: GitHub Docs, "Fork a repository" (https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo), retrieved 2026-10-21.

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
| Install | One installer (Windows 10 64-bit or later, macOS 12.0 or later) | git, plus the GitHub CLI (`gh`) |
| Linux | Not supported ("Linux is not yet supported" on the vendor's install page); use the command line | Fully supported |

If you have never used a terminal, start with the GUI path. The command-line path is still worth learning, because this project's guides (and nearly every engineering team) use it.

## The GUI path: GitHub Desktop

**GitHub Desktop** is a free app from GitHub that wraps the git commands in buttons.

Sources, all retrieved 2026-10-21: GitHub Docs, "Installing GitHub Desktop" (https://docs.github.com/en/desktop/installing-and-authenticating-to-github-desktop/installing-github-desktop), "Authenticating to GitHub in GitHub Desktop" (https://docs.github.com/en/desktop/installing-and-authenticating-to-github-desktop/authenticating-to-github-in-github-desktop), "Cloning and forking repositories from GitHub Desktop" (https://docs.github.com/en/desktop/adding-and-cloning-repositories/cloning-and-forking-repositories-from-github-desktop), "Managing branches in GitHub Desktop" (https://docs.github.com/en/desktop/making-changes-in-a-branch/managing-branches-in-github-desktop), "Committing and reviewing changes to your project in GitHub Desktop" (https://docs.github.com/en/desktop/making-changes-in-a-branch/committing-and-reviewing-changes-to-your-project-in-github-desktop), "Pushing changes to GitHub from GitHub Desktop" (https://docs.github.com/en/desktop/making-changes-in-a-branch/pushing-changes-to-github-from-github-desktop) and "Creating an issue or pull request from GitHub Desktop" (https://docs.github.com/en/desktop/working-with-your-remote-repository-on-github-or-github-enterprise/creating-an-issue-or-pull-request-from-github-desktop).

### Install and sign in

1. Visit the GitHub Desktop download page (the install page links to it) and click **Download for Windows** or **Download for macOS**. On macOS, double-click the downloaded zip file, then double-click the **GitHub Desktop** application. On Windows, double-click the downloaded setup file. GitHub Desktop starts when the install finishes.
2. Sign in. On macOS, choose **GitHub Desktop** in the menu bar, then **Settings**. On Windows, choose **File**, then **Options**. On the **Accounts** pane, click **Sign Into** next to GitHub.com (not the Enterprise button). Click **Continue With Browser**. Your browser opens; sign in there. If you turned on 2FA, type your code and click **Verify**. Then follow the prompts back to the app. Signing in with a username and password is not supported.
3. Git needs your name and email for commits. GitHub Desktop has a Git settings area for this (est.; the page "Configuring Git for GitHub Desktop" was not read). For the email, see "Your name and email" below: you can use the no-reply address so your private email is not stored in your commits.

> **Screenshot to take yourself:** GitHub Desktop signed in, before you open a project.
> Capture: the Welcome window or the main window showing that you are signed in.
> Look for: the list of your repositories, or the "Clone a repository from the Internet" option.
> Redact: your username, name, email address, avatar and the repository list if it names private projects.

### Clone your fork

1. In the **File** menu, click **Clone Repository**.
2. Click the tab for where the repository is (for example **GitHub.com**), then click your fork of `Clouds-Against-Humanity` in the list. You can also click **URL** and paste the address of your fork.
3. Next to "Local Path", click **Choose...** and pick the folder on your computer where it will land. Note this path.
4. At the bottom, click **Clone**. It downloads the project and its history.

(Another route: on your fork's GitHub page, click **Code**, then **Open with GitHub Desktop**, then **Choose...** and **Clone**.)

### Make a branch

1. At the top of the app, click **Current Branch**, then **New Branch**.
2. In the "Create a Branch" window, under "Name", type `fix-readme-word`. Use lowercase words joined by dashes.
3. Under "Create branch based on...", choose `main`, and click **Create Branch**.

### Change a file and commit

1. Open the project folder on your computer in any text editor and change one word in `README.md`. Save the file.
2. Go back to GitHub Desktop. The **Changes** tab in the left sidebar lists `README.md` with a yellow icon (modified), and the diff shows the change. Keep its checkbox ticked so it is included.
3. Type a short message such as `Fix one word in the README` in the **Summary** field. Click **Commit to fix-readme-word**.

### Push and open the pull request

1. Click **Publish branch**. This is the **push** for a new branch: it uploads your branch to your fork on GitHub. (Later commits on the same branch use **Push origin** in the repository bar.) If GitHub Desktop asks "How are you planning to use this fork?", choose **To contribute to the parent project**, or **For my own purposes** if you want this practice to stay inside your fork.
2. Click **Preview Pull Request** to see the diff between your branch and the base branch, or click the dropdown icon and choose **Create Pull Request** to go straight to GitHub. In the **base:** dropdown, confirm the branch you want to merge into. Click **Create Pull Request**; your browser opens on GitHub.
3. Check that the base repository is your own fork, not the original (see the exercise, step 6). Type a title and description and click the green button to create the pull request (est. for the exact label; that part of the vendor page was cut off).

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

Sources, retrieved 2026-10-21: https://git-scm.com/install/windows, https://git-scm.com/install/mac and https://git-scm.com/install/linux.

| System | Install |
|---|---|
| Windows | Download the installer from the git-scm.com Windows page, or run the winget command below. The project notes the winget package is not maintained by the Git for Windows project and may be behind the newest version |
| macOS | `xcode-select --install` (Apple's Xcode Command Line Tools include git), or `brew install git` with Homebrew. The project notes non-source builds are provided by third parties |
| Debian or Ubuntu | `sudo apt-get install git` (the vendor page shows the same without `sudo`, as root) |
| Fedora | `sudo dnf install git` |

```powershell
winget install --id Git.Git -e --source winget
```

Expected (est.): a progress bar, then a line saying the install succeeded. Close the terminal and open a new one so it finds git.

```bash
sudo apt-get install git
```

Expected (est.; Debian, Ubuntu): it asks for your password (you will not see the letters as you type), lists packages and finishes without a line starting `E:`.

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

**A note on the email.** Your commits, and the email in them, are public once you push to a public repository. GitHub offers a **no-reply address** that hides your real one. Its format is `ID+YOUR-USERNAME@users.noreply.github.com`, where `ID` is a number GitHub gives you. To find it and to hide your real address, click your profile picture, then **Settings**, then **Emails** in the "Access" section, and select **Keep my email addresses private**. Sources, retrieved 2026-10-21: GitHub Docs, "Setting your commit email address" (https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-email-preferences/setting-your-commit-email-address) and "Email addresses reference" (https://docs.github.com/en/account-and-profile/reference/email-addresses-reference), which gives the `ID+USERNAME@users.noreply.github.com` form. The "Emails" page shows the exact address to use (est.).

### HTTPS or SSH, and why start with `gh`

To talk to GitHub, git has to prove who you are. There are two ways.

- **HTTPS** uses the ordinary web address (`https://github.com/...`) and a login. Easy to start. The login is no longer a password but a **token**: a long random string that works like a password for a program.
- **SSH** uses a pair of keys: a **private key** that stays on your computer and a **public key** you give to GitHub. It is neat once set up, but there is more to set up. [Networking basics: SSH](Networking-Basics-for-This-Project.md#ssh-in-one-paragraph) explains the idea.

**The easiest start is HTTPS with the GitHub CLI.** The **GitHub CLI** (command-line interface; the program is called `gh`) signs you in through your browser, stores the credential safely and sets git up to use it. You never copy a token by hand. You can move to SSH later if you want to.

### Install the GitHub CLI

Sources, retrieved 2026-10-21: the GitHub CLI README (https://github.com/cli/cli#installation) and its install pages for [Windows](https://github.com/cli/cli/blob/trunk/docs/install_windows.md), [macOS](https://github.com/cli/cli/blob/trunk/docs/install_macos.md) and [Linux](https://github.com/cli/cli/blob/trunk/docs/install_linux.md).

| System | Install |
|---|---|
| Windows | `winget install --id GitHub.cli --source winget` |
| macOS | `brew install gh` (needs Homebrew) |
| Linux | Follow the Debian/Ubuntu or Fedora/RHEL section of the Linux install page. They first add GitHub's own package repository, then install `gh` with `apt` or `dnf`. Copy the current commands from that page, because the signing-key details change |

```powershell
winget install --id GitHub.cli --source winget
```

Expected (est.): a progress bar and a success message. The vendor page says to open a **new** window afterwards so the changed PATH (the list of places the system looks for programs) takes effect.

```bash
gh --version
```

Expected (est.): a line starting `gh version`, then a link to the release notes.

### Sign in with `gh auth login`

```bash
gh auth login
```

Source for the next two commands: the `gh auth login` manual (https://cli.github.com/manual/gh_auth_login), retrieved 2026-10-21. It says the default is a web-based browser flow, that the token is then stored securely in the system credential store (falling back to a plain text file if no store is found), and that the git protocol can be chosen during the interactive prompting.

Expected (est. for the exact wording of the questions): a few questions. Choose **GitHub.com**, then **HTTPS**, answer **Yes** to authenticating git with your GitHub credentials, and choose **Login with a web browser**. It prints a one-time code (eight characters), you press Enter, your browser opens, you type the code and approve. The terminal then says you are logged in as your username.

Check it:

```bash
gh auth status
```

Expected: a line saying you are logged in to github.com, and which protocol git uses (`https`). It does not print the token (est.).

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
8. **Merge it.** Click **Merge pull request**, then **Confirm merge**. GitHub then offers a **Delete branch** button. (Button names are est.; the merge page was not read.)
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
