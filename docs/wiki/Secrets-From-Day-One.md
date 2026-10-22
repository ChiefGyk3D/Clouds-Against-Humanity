# Secrets from day one: a password manager, Doppler for every asset, and the .env rules

Side page to the start-from-zero pages. Read it after [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) and [Doppler and secrets](Doppler-and-Secrets.md) (core step 17), and before [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md). It does not repeat them. Those pages say what a secret is and how this project keeps its own out of the repository; this one is about **your** habits: what to set up before the first line of code, where each kind of secret lives, how to catch the one that slipped, and what to do in the first hour after one leaks. Next: [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the free local lab was run once on Linux; the PowerShell commands, macOS and the Doppler own-account path were not run.** On **2026-10-22** the author ran every Bash command in exercises 1 to 5 on a Debian-based Linux machine with git 2.47.3, Python 3.13.5, gitleaks 8.30.1 and the `git-filter-repo` script from that project's `main` branch, as an ordinary user, in a scratch folder, and pasted trimmed output from those runs. Four things were **not run** and are marked **est.** (estimate): every PowerShell command (no PowerShell was available), anything on macOS or Windows, the gitleaks download for platforms other than Linux x64, and the whole optional path with your own Doppler account. The Doppler commands in that path were checked only against the `--help` text of the Doppler CLI 3.77.0 and against Doppler's documentation; the output you will see there is not shown because it was never seen. Every vendor and standards claim was read on **2026-10-22** unless a row says otherwise, and sits in the [claims register](#claims-register) with its URL. Parts of this page describe things that are **planned and not built** (the edge assets); those are labeled where they appear. Trust what your terminal prints over this page.

> **Prerequisites.** [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) and [Doppler and secrets](Doppler-and-Secrets.md) for the vocabulary, and [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) for what a token, a scope and a `401` are. [The terminal and your first script](Terminal-and-Your-First-Script.md) and [Git from zero](Git-From-Zero.md) for the shell and git commands. The free path needs `git` and Python 3.11 or newer (3.13 was used), on Linux, macOS (est.) or Windows with PowerShell 5.1 or later (est.). `gitleaks` and `git filter-repo` are optional; the page works without them. About four hours for the reading and the free exercises (est.); the optional Doppler path adds about an hour (est.).

> **Where this runs.** Everything in the free path happens in one scratch folder on your own computer. Nothing is sent anywhere and nothing is pushed. The only secrets are **dummy values built at the moment you run the exercise**, issued by a pretend service that is a short script; no secret-shaped text is stored in this repository. **Never push the scratch repository to GitHub or anywhere else**, even though the values are fake. The optional path uses **your own** Doppler account on its free plan and **your own** time; it starts with the teardown.

## The maintainer's rule, in his words

The maintainer (ChiefGyk3D) gave the brief for this page on 2026-10-22. His words, kept as he wrote them:

> we setup doppler to work with these assets too and showcase how that works and why secrets management is the way, and you should slap the hands on any keyboard hardcoding credentials, and .env at most should stay on a local machine and if on a server reference non sensitive things. You should ideally be building with password management from the initial ground. Eventually in enterprise you have very robust IAM policies, but most likely you are making this lab for yourself and at most maybe you and a handful of other humans may touch it, not counting the dozens of bots you will see in your logs with this server running even for a relatively short period.

That is four rules and one fact of life, and the page is built on them:

1. Never put a credential in code, a script or a commit.
2. A `.env` file stays on a local machine. On a server it holds only non-sensitive references.
3. Machines get their secrets from a secrets manager (here Doppler), one per asset.
4. Build with a password manager from the first day, not after the first scare.
5. In a lab, few humans touch it and many bots probe it. Plan for both.

## What you will be able to do

- Say why a hardcoded secret is a problem that outlives the file it was in, and name six places one value gets copied to.
- Set up a password manager sensibly: unique passwords, MFA, recovery codes stored offline, and a way back in if you lose access.
- Explain what a secrets manager adds for machines, and say how this project uses Doppler for Spacelift, for hosts and (planned) for each edge service, with one config and one short-lived token per asset.
- Write a `.env`, a `.env.example` and a `.gitignore` that work together, set file permissions, and say what may and may not be in a `.env` on a server.
- Choose between an environment variable, a file and run-time injection for a secret, and say who can read each.
- Run a secret scanner (a small one from this page, and gitleaks if you choose), and say what it will miss.
- Rotate a secret, and prove the old value is dead.
- Run the leak drill in order: revoke, rotate, check the logs, then clean history, and say why deleting the file is not enough.
- Read an SSH auth log and separate the constant bot noise from the lines that need a human.
- Say how a solo lab differs from enterprise IAM, and what honest limits a secrets manager has.

## What the wiki already says (and the gap)

I read these pages before writing this one:

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| What a secret is, how secrets leak, why a secrets manager | [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) | What to set up first, in what order, and the habits around it. |
| Where each project secret lives, the Spacelift hook, 90-day rotation | [Doppler and secrets](Doppler-and-Secrets.md), [the secrets runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md) | The same idea for hosts and edge assets, and how to build the habit for your own projects. |
| Which value belongs in which file | [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md) | The `.env` file, which that page does not cover, and its server-side rules. |
| Token words: scope, expiry, revoke; a short "when a secret leaks" list | [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md#when-a-secret-leaks-revoke-then-rotate-then-clean-up) | A drill you can run, scanning, and proving a value is dead. |
| A secret in git history survives deletion | [Hashing, encryption and keys, exercise 7](Hashing-Encryption-and-Keys.md#exercise-7-what-leaks-in-a-git-repository) | Finding it with a scanner, and cleaning history. |
| SSO, PAM, break-glass, secrets at scale | [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md) | The solo-lab side of the same table. |
| Backups and restore | [Backups, recovery and patching](Backups-Recovery-and-Patching.md) | What to back up so losing the password manager is not the end. |

None of the pages above has a password manager section, a `.env` section, a scanner, or a leak drill. That is the gap.

## Why never hardcode

To **hardcode** a secret is to type its value into a file that is meant to be shared, copied or committed: a script, a config, a notebook, a README. It feels harmless because the file is on your laptop. The trouble is how many other places the file, and so the value, ends up.

### How far one pasted value travels

| Place | Why the value is still there after you delete it | What limits the damage |
|---|---|---|
| **Git history** | Every commit keeps the lines it added. A later commit that removes the file adds a new snapshot; the old one stays in the history, and in every copy of the history. [Exercise 4](#exercise-4-the-leak-drill-revoke-rotate-check-then-clean) shows it. | Revoking the value. Rewriting history comes after, and even then it only helps the copies you control. |
| **Forks and clones** | A fork or a clone is a full copy of the history at that moment. GitHub's own removal guide says rewriting your repository does not touch other people's clones, and that a fork containing the commit keeps it ([GitHub Docs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository), read 2026-10-22). | Revoking the value. |
| **CI logs** | A build that prints its environment, or a failing command that echoes its arguments, writes the value into a log many people can read and a platform keeps for months (est.; retention varies). | Masking in the CI tool, and not printing. Revoke if it ever shows. |
| **Screenshots and recordings** | The token in the corner of the terminal, in the Slack screenshot, in the video. See the redaction rules in the [Screenshots policy](Screenshots-Policy.md). | Redact before you share; better, never display it. |
| **Chat, tickets and email** | Searchable, forwarded, backed up, and read by whoever joins the channel next year. | Share a pointer to where it lives, not the value. |
| **Backups and snapshots** | A backup of the laptop or the server contains the file as it was then. Deleting the file now does not reach the backup. See [Backups, recovery and patching](Backups-Recovery-and-Patching.md). | Revoking the value. Backups that are encrypted and access-controlled. |

The table is the case for one rule: **after a value has been pasted anywhere shared, assume it has been copied, and treat revoking it as the cure.** Cleaning up is tidiness. The [APIs and tokens page](APIs-and-Tokens-From-Zero.md#where-a-secret-must-never-live) has the longer "where a secret must never live" table; this one adds the backups and the forks.

## The order: people first, then machines

A common mistake is to start with the clever tool. The order that works, and the reason for each step:

1. **A password manager for you** (step 1 below). Every other secret is protected by a login you control. If that login is weak, reused or lost, nothing above it holds.
2. **A secrets manager for your machines** (step 2). Programs get their values at run time, by name, with a token that can only read. Nothing is written into code.
3. **`.env` rules** (step 3). The small file that still exists on your laptop, kept small and kept local.
4. **Scanning** (a section below). A safety net for the mistakes the first three do not prevent.
5. **Rotation and a leak drill** (two sections below). Because the net will eventually miss one.

A password manager is the first step because it solves a different problem from the others: the secrets **you** type. A secrets manager solves the secrets **programs** use. A lab needs both, and people who set up only the second still reuse a password on the account that holds the first.

## Step 1: a password manager, from the first day

A **password manager** is a program that stores your logins in an encrypted vault, generates a long random password for each account, and fills it in for you. You remember one strong secret (the **master password**); it remembers the rest.

Why it comes first: NIST's current guidance for services that check passwords says the service must allow password managers and autofill, should permit pasting, and gives the reason: "Password managers have been shown to increase the likelihood that subscribers will choose stronger passwords, particularly if the password managers include password generators" ([NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html), read 2026-10-22). The same document says the value of distinct passwords is to avoid "password stuffing", where an attacker takes a password leaked from one site and tries it on others.

### What goes in it, and what does not

**In the vault:** the logins for your email, your GitHub account, your cloud and DNS accounts, Doppler, Spacelift; the recovery codes for each (with the caution below); your own notes of **token expiry dates**, which is where [Doppler and secrets](Doppler-and-Secrets.md#rotation-in-short) already says this project keeps them; the SSH key passphrase.

**Not in the vault:** the runtime secrets a machine needs. A program should not read your password manager; it should read a secrets manager with a token of its own (step 2). The reason is accountability and blast radius: a human vault shared with a script means that script's compromise is a compromise of everything you own.

### Several tools, no recommendation

This page names several and recommends none, and the maintainer has not named a pick for it. Three that publish their own security design, read on 2026-10-22:

- **Bitwarden** describes zero-knowledge end-to-end encryption with key derivation by PBKDF2-SHA256 or Argon2id, and says it "has no way to access, retrieve, or reset your master password" ([security white paper](https://bitwarden.com/help/bitwarden-security-white-paper/), [forgot master password](https://bitwarden.com/help/forgot-master-password/)).
- **1Password** combines your account password with a 128-bit Secret Key and encrypts with AES-GCM-256 ([security overview](https://support.1password.com/1password-security/)); it gives you an Emergency Kit PDF for the sign-in details ([Emergency Kit](https://support.1password.com/emergency-kit/)).
- **KeePassXC** keeps your database as a file you store and back up yourself, and its guide recommends the Argon2 key derivation of the KDBX 4 format ([user guide](https://keepassxc.org/docs/KeePassXC_UserGuide)).

Choose by what you will actually keep using: where it runs, how it syncs, whether you want a hosted service or a local file, what happens if the company changes its terms, what it costs. I have not audited any of them, and a vendor's own white paper describes the design, not the proof. If you already use your browser's built-in manager, that is a start; the steps below apply to it as well.

### The loop: protecting the thing that protects everything

A password manager is one more thing to protect, and it is the best target on your side of the table. The habits that make it safe:

1. **A long, unique master password** that you do not use anywhere else. A passphrase of several random words is easier to remember than symbols. NIST says verifiers must not impose composition rules (such as "one symbol and one capital") and should accept passwords of at least 64 characters, which tells you length is the lever.
2. **MFA on the vault itself and on every account that can reset it.** MFA (multi-factor authentication) is a second proof beyond the password. [CISA's "More than a Password"](https://www.cisa.gov/MFA) (read 2026-10-22) says any MFA beats none and that FIDO/WebAuthn security keys are the phishing-resistant kind; an SMS code is better than nothing and weaker than a key. The [Identity page](Identity-Secrets-and-Zero-Trust-Basics.md#mfa-and-identity-providers) says the same in this project's terms. Your email is the account that resets all the others, so it comes first.
3. **Recovery codes, stored offline.** Most services give you a set of one-time **recovery codes** when you turn on MFA, for the day you lose your phone. GitHub's guidance is to "download and store these codes securely" and "saving them with a secure password manager" ([GitHub Docs](https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa/configuring-two-factor-authentication-recovery-methods), read 2026-10-22). Follow that, and add the part that is easy to miss: **the recovery codes for the password manager itself, and for the email account you use to recover it, cannot live only inside the password manager.** That is a circle: you lose the vault, you need the codes, the codes are in the vault. Print them or write them down and keep the paper somewhere safe and separate from the computer, and keep a second copy somewhere a different failure cannot reach (the [3-2-1 idea](Backups-Recovery-and-Patching.md#the-3-2-1-rule-and-what-it-leaves-open) applies to a sheet of paper too).
4. **A way back in if you lose access.** Know before you need it what yours is. Bitwarden says it cannot reset your master password; 1Password's Emergency Kit holds the Secret Key you cannot get from anywhere else; a KeePassXC database you lose with no backup is gone. Decide who, if anyone, could open it for you (a trusted person with a sealed copy, a written instruction) and test that you can sign in on a second device before you need to.
5. **Two or more MFA methods.** GitHub itself recommends configuring "two or more authentication methods" so one lost phone is not a lockout.

Nothing on this page makes a password manager safe to use on a computer that already has malware on it. If the machine is compromised, the vault is read when you unlock it. That is a limit, not a reason to skip the step.

## Step 2: a secrets manager for machines

A **secrets manager** is a service whose only job is to hold secrets and hand them to programs at run time, by name, to callers it has authenticated, and to keep a record of who asked. The general idea is on the [Identity page](Identity-Secrets-and-Zero-Trust-Basics.md#the-fix-a-secrets-manager-and-the-discipline-around-it); the OWASP Secrets Management Cheat Sheet (read 2026-10-22) says organizations need to "centralize the storage, provisioning, auditing, rotation and management of secrets" to "prevent them from leaking and compromising the organization".

This project uses **Doppler**. The disclosure about that choice is on [Why I picked these tools](Why-I-Picked-These-Tools.md#disclosure-first): Doppler sponsored content the author made years ago, and that is how he found it; they did not sponsor this project or this page. Read it, then weigh anything on this page about Doppler with that in mind. The same page lists open-source and cloud-native alternatives, and every habit below transfers to them.

### The vocabulary

Taken from Doppler's documentation (read 2026-10-22):

- A **project** is "where you define the app config and secrets for a single service or application."
- Each project has three default **environments**: Development, Staging and Production.
- A **config** vaults the secrets of one environment: "Configs are responsible for vaulting and managing app config and secrets such as API keys, database urls, certs".
- A **service token** "provides read-only secrets access to a specific config within a project" and, per Doppler's wording, adheres to least privilege "by ensuring an application only has access to a single config". You can optionally give a token write access or an expiration when you create it.
- A **personal or CLI token** has "write access with the same permissions as the account it was created by", and Doppler's page says not to use one in live environments.

So the unit of isolation is the config, and the unit of access is a token for exactly one config.

### One config and one short-lived token per asset

The pattern, from the maintainer's ruling on 2026-10-22 (issue 236): **each asset gets its own Doppler config and its own short-lived, read-only token**, where you decide what an asset is (a service, a host or a site) and write the choice down. Not one shared config for the whole project, and not one shared token. The reasons are the least-privilege reasons from [APIs and tokens](APIs-and-Tokens-From-Zero.md#scopes-and-least-privilege): a compromised service reads only its own config, a leaked token reads only one asset's values, and a revoked token stops one asset, not all of them. Here is where each asset stands:

| Asset | Doppler config | Token | Status |
|---|---|---|---|
| **Spacelift runs** | `clouds-against-humanity` / `prd` | One read-only service token, scoped to that config, 90-day expiry, held as a write-only variable in a Spacelift context ([Doppler and secrets](Doppler-and-Secrets.md#who-holds-what)). | Built and in use. |
| **Telemetry droplets** (stage 2). The asset is the **site**, not the host: both connectors of a site share one config and the same bootstrap token (the stack passes one `log_shipping_bootstrap_token` to both connector modules). Revoking it affects both, and a compromised connector can read the sibling's boot secret. Splitting per host would be tighter and is not built | `cah-<resource_key>-hostboot`, holding only that site's host secrets | One read-only token, created out of band, handed to the first boot, written to a root-only file, **deleted after the first pull** ([stage 2 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md#secrets-one-mechanism-design-section-28)). | Written and tested as text and with fake binaries; opt-in, off by default, not applied anywhere yet. |
| **Edge services** (the public edge, planned) | One config per edge service. The config names are not decided; `cah-edge-<service>` is an illustration (est.). | One short-lived, read-only token per service. | **Ruled, not built.** There is an open design question below. |
| **CI** | not decided on this page | This repository's `security` job runs a full-history gitleaks scan through a reusable workflow ([CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md)). I did not read whether it gives that job any Doppler access; Doppler and secrets says the author's other repositories fetch over OIDC and store no Actions secrets. | Not checked. |

The open question for the edge, written down rather than hidden: the [edge design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-19-edge-dmz-design.md) puts several daemons on one small droplet and lets the droplet's `user_data` carry **exactly one** secret-shaped field, the bootstrap token (risk 6). One token per service on one droplet would mean several tokens there, or one droplet per service, or a different hand-off. Which of those the project picks is not decided, and this page does not pick it.

Two limits to know about the free Doppler plan if you copy the pattern. Doppler's pricing page (read 2026-10-22) lists the free Developer plan as "Free for 3 users" with service tokens included, and a comparison table that reads 50 service tokens, 10 projects, 4 environments and 10 configs per environment, plus three days of activity logs. I read those numbers from flattened page text, so check the live page; the prices and limits are Doppler's to change. The ten-config limit is the one an asset-per-config habit meets first (est.).

### How a host gets its secret: the first-boot pattern

A new server has to start trusting someone with no secret on it. Writing the real secret into its startup script (cloud-init `user_data`) would put it in the tool's state, in the provider's API, and on the server's metadata endpoint. The pattern this project's stage 2 uses instead:

1. The maintainer creates, **out of band**, a read-only Doppler service token for that site's `-hostboot` config, with an expiry. Doppler documents this: "an ephemeral Service Token can be created by setting an expiration time. Once the duration is reached, the token is automatically deleted", from the CLI with `--max-age` (its example uses `--max-age 1m`) ([service tokens](https://docs.doppler.com/docs/service-tokens)).
2. cloud-init writes that one token to a root-only file (mode 0600). The first-boot script reads it, **deletes the file**, and sends it to the Doppler API over TLS on standard input, so it never appears in a command line.
3. The script takes only the secret it needs, writes it to a root-only file for the one program that needs it, uses it, and removes it. If anything fails, it stops and **fails closed**: it never falls back to a literal value.
4. The token is revoked right after the first boot regardless of its expiry.

Written down honestly in the stage 2 guide: copies of the token remain in the OpenTofu state, the provider's API, the server's metadata endpoint and cloud-init's own retained copy of `user_data` until the token expires or is revoked. That is why the token must be short-lived and why the revoke step exists. The smallest lifetime Doppler accepts, and whether a token can be single-use, are **UNVERIFIED**: the page documents neither.

### Injected at run time with doppler run

For a program that runs on your own machine or a server, `doppler run -- your-command` fetches the secrets of one config and starts the command with them in its environment. Nothing is written to a file in the repository, and the program never contains a value. Three things Doppler's own documentation and the CLI help tell you that beginners miss (read 2026-10-22, CLI 3.77.0 `--help`):

- The CLI writes an **encrypted fallback file** after each successful fetch, so a program can still start when Doppler is unreachable. The same page warns that revoking a token stops access to the latest secrets but "the CLI will continue to provide the last accessed version of the secrets" from that file. After a revoke, test with `--no-fallback` ([exercise 4](#exercise-4-the-leak-drill-revoke-rotate-check-then-clean) uses the same idea).
- `doppler secrets download` can write a plain `.env` file, and Doppler's own example carries the comment "Avoid storing secrets unencrypted whenever possible". The point of the tool is the opposite of writing the file.
- `--preserve-env` lets values already in the environment win over Doppler's, and Doppler's help says that setting it to `true` "has potential security implications". Know what is in your environment before you run.

## Step 3: the .env rules

A **`.env` file** is a plain text file of `NAME=value` lines that a tool or a library reads into the environment at start-up. It is convenient and it is where a great many leaks start, because it is a file of secrets that sits next to the code.

### Local development only

The rule from the maintainer: **a `.env` stays on a local machine at most.** Concretely:

1. **It is in `.gitignore`** before the first commit. Not after the first scare.
2. **It has a twin, `.env.example`**, which is committed. It lists every name the program reads, with comments and **dummy values**, so a new person (or you in a year) knows what to supply. The example is documentation; a test can check that it and the real file have the same names ([exercise 2](#exercise-2-env-envexample-and-gitignore-that-work-together)).
3. **The values in your local `.env` are for local use**: a throwaway database in a container on your laptop, a sandbox API key, a Doppler project and config *name*. Real production credentials do not belong in it. If your program needs a real secret to run locally, use `doppler run` and keep the file out of it.
4. **Its permissions are yours alone** (mode 0600 on Linux and macOS), because a world-readable file of tokens is one shared-machine away from a leak.

`.gitignore` is not a vault. It only stops git from **adding an untracked file** by accident; a file that is already tracked stays tracked, and `git add -f` overrides it ([exercise 2](#exercise-2-env-envexample-and-gitignore-that-work-together) shows both). The scanner is for the cases the ignore file misses.

### What a server's file may hold

On a server the maintainer's rule is: **if there is a `.env` there at all, it references non-sensitive things.** A file like this is fine to be readable:

```text
# /etc/example-service/service.env  - references only, nothing here is a secret
DOPPLER_PROJECT=example-project
DOPPLER_CONFIG=example-service-prd
LOG_LEVEL=info
```

That names the project and the config the service reads from. The names are not credentials: knowing them does not let anyone read the secrets without a token. The token itself is another matter:

- **The token's value is never in a committed file and never in a world-readable one.** Where it lives instead: a root-owned file with mode 0600 that only the process manager reads (as in the first-boot pattern above), or a mechanism your init system provides for credentials (systemd has one; check your version's documentation, est.), or the Doppler CLI's own stored configuration (check where your version keeps it, est.).
- **The secret values pulled with it are never written to the repository, and are written to disk only when a program cannot take them any other way**, in a root-owned 0600 file that is removed when no longer needed.

### Environment variables, files, or injected at run time

| Way | Who can read it | Leaks through | Use when |
|---|---|---|---|
| **An environment variable** | Every program the process starts inherits it. On Linux, the same user and root can read a process's environment from `/proc` (exercise 3). | Child processes, crash reports and debug pages that print the environment, `docker inspect` and similar tools, a shell history line that set it. | A short-lived process that gets the value injected for its own run. |
| **A file** | Whoever the file mode and the folder allow. | Permissions set wrong, backups of the disk, a copy committed or uploaded by mistake, a container image layer that contains it. | A program that can only read a file, or a value too large for the environment (a certificate). Keep it 0600 and remove it when done. |
| **Injected at run time** (`doppler run`, a sidecar, a cloud secret API) | The program, for the life of the run. | The environment, once injected (above); the token that does the fetching. | The default for anything a machine needs. Still needs one **bootstrap secret** to authenticate, which is why that token is read-only, scoped and expires. |

OWASP's cheat sheet makes the same point for containers: never bake a secret in with `ENV` or `ARG` in an image, because those "can easily leak with the container definitions"; have the orchestrator supply it at run time.

## Secret scanning: three layers and their limits

**Secret scanning** is a program that reads text (a working folder, or every commit in a repository) and flags strings that look like credentials. It is a safety net, not a gate: it catches the slip after the habits above have failed.

### Pre-commit, CI, and push protection

| Layer | What it does | The weak point |
|---|---|---|
| **A pre-commit hook** ([gitleaks](https://github.com/gitleaks/gitleaks) with the `pre-commit` tool) | Scans your staged change **before the commit exists**, on your own machine. The cheapest place to catch it, because nothing has been shared. | It runs on your machine only if you installed it, and you can skip it: the gitleaks README shows `SKIP=gitleaks git commit` for exactly that. |
| **A CI scan** | Scans the whole repository history on every change, on a machine you do not control the keyboard of. This project's `security` job calls a reusable workflow that runs gitleaks over the full history ([ci.yml](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/.github/workflows/ci.yml), [git-your-ship-together security workflow](https://github.com/ChiefGyk3D/git-your-ship-together)). | It finds a secret **after** it has been pushed, so by then it exists on a server. A red check says revoke it; it does not undo the push. |
| **Push protection** (GitHub) | GitHub blocks the push itself when it detects a supported secret. Per GitHub's documentation (read 2026-10-22): "push protection for users" is on by default and "stops you from pushing secrets to public repositories on GitHub"; "push protection for repositories" needs GitHub Secret Protection and is "disabled by default". | By default anyone with write access can bypass it by giving a reason. It recognizes the secret formats GitHub knows, not your home-made token. |

GitHub's **secret scanning** (the alerting half) "scans your entire Git history on all branches" of a repository and, for public repositories, runs automatically and free; for organization-owned private repositories it needs GitHub Secret Protection. When it finds a partner's credential it can tell that provider, who can revoke it. I did not check which of those switches are on for this repository, and I did not test any of this on a real repository (est.).

Run all three. They fail in different places, and the pre-commit hook is the only one that stops a secret before it is anywhere.

### What scanners miss

Scanners are pattern matchers. They will miss things, and they will cry wolf. Observed or documented:

- **They match shapes, so a home-made token with no known shape may slip.** In the exercises the planted value is shaped like a GitHub personal access token, so gitleaks' built-in `github-pat` rule found it in 40 of 40 random trials (my run, 2026-10-22). A bare random 40-character value assigned to `DEPLOY_API_KEY` was found by the generic rule in 39 of 40 trials: one random value of the same shape was missed. A hexadecimal token with a made-up prefix was not reported in the one run I tried. The likely reason is the entropy floor below (est.).
- **Entropy rules.** **Entropy** here is Shannon entropy: a measure, in bits per character, of how random a string looks. Random strings score high; English and repeated characters score low. gitleaks' rule format has a minimum `entropy` setting, and its example uses 3.5 ([README](https://github.com/gitleaks/gitleaks)). Raise the floor and you miss weaker secrets; lower it and you flag ordinary words. A human-chosen password such as `Summer2026!` scores low and no entropy rule will love it.
- **False positives.** A placeholder, a test fixture and a hash all look like secrets. Scanners give you escape hatches: a `gitleaks:allow` comment on a line, a `.gitleaksignore` file of fingerprints, a baseline of old findings. Each is a place a real secret can be hidden by a tired person, so review them like code.
- **Encoding and splitting.** In my run, gitleaks 8.30.1 caught a base64-encoded copy of the token (its `--help` showed `--max-decode-depth` defaulting to 5, although the README I read said the default is 0), and missed a token split across two lines. The small scanner on this page misses both. Neither check is a promise about your version.
- **History is the target, not the tip.** A scan of only the files in your folder can say "clean" while an old commit holds the secret. The gitleaks `git` command reads the history; `dir` reads files. Exercise 1 shows the two disagreeing. Its README says "gitleaks only looks at additions in the git history", so it reads the lines each commit **adds**.
- **Places no scanner reads:** a screenshot, a chat message, a voice call, a shared screen. Habits, not tools, cover those.
- **A scanner can only tell you a value looks like a secret.** It cannot tell you whether it is live, who copied it, or whether it was used. Only the issuer's records answer that.

## Rotation, expiry and proving a value is dead

**Rotation** is replacing a secret with a new one on purpose, then retiring the old one. **Expiry** is a date after which the secret stops working by itself. Both exist for the same reason: a stolen value should be useful for a short time only. What to rotate, and how often, depends on the kind:

| Secret | When to rotate | Source and note |
|---|---|---|
| **A human's password** (including your master password) | When there is evidence or suspicion of compromise. Not on a calendar. | NIST SP 800-63B-4 says verifiers "SHALL NOT require subscribers to change passwords periodically" but "SHALL force a change if there is evidence that the authenticator has been compromised". OWASP's cheat sheet says user credentials are excluded from regular rotation for the same reason. This is guidance for services that check passwords. |
| **A machine's token or key** (API token, service token) | On a schedule you can keep, **and** on any exposure, **and** when a person who knew it leaves. | OWASP: "You should regularly rotate secrets so that any stolen credentials will only work for a short time." This project uses 90 days for its long-lived tokens ([Doppler and secrets](Doppler-and-Secrets.md#rotation-in-short)). A first-boot token should live hours to a day (the design's need, est.). |
| **A service token with an expiry** | You do not have to remember: it deletes itself. You do have to replace it before it does, or the next run fails. | Doppler's ephemeral tokens delete themselves at expiry. |
| **Recovery codes** | After you use one (each is single-use, per GitHub), and after any suspected exposure. | GitHub: generating new codes replaces the old set. |
| **An SSH key** | When a device is lost or a person leaves. There is no clock rule that I verified (est.). | The [Identity page](Identity-Secrets-and-Zero-Trust-Basics.md#how-keys-work-without-the-math) has the practical rules. |

The most common rotation failure is not the schedule, it is **nobody owning the date**. Write each expiry in the password manager's notes with the name of the person who renews it, as [Doppler and secrets](Doppler-and-Secrets.md#rotation-in-short) does, and remember that an expired token warns nobody; the next run just fails.

### Proving the old value is dead

"I rotated it" is a belief until you test it. The proof is to **present the old value to the real service and read the answer**:

1. Keep the old value long enough to test it (in a local file with mode 0600, not in chat).
2. Send it to the service. A dead token should be refused: a `401` (the service does not know this credential), as in the [APIs page](APIs-and-Tokens-From-Zero.md#optional-make-test-and-revoke-a-real-scoped-token-your-own-account). A `403` instead means the credential still identifies someone and the service is refusing the action, which is not the same as dead.
3. Look in the issuer's **audit or access log** for your test attempt, shown as refused. If your service does not log refused attempts, you have learned something about it.
4. Check the **copies**: the old value may still sit in CI variables, a `.env` file, a container's environment, a backup, an old laptop. Rotating the master copy does not rotate those; revoking the value at the issuer does.
5. For Doppler specifically, test with `doppler run --no-fallback` so the cached fallback file cannot answer for the dead token.

[Exercise 4](#exercise-4-the-leak-drill-revoke-rotate-check-then-clean) does steps 2 to 4 against a pretend issuer on your computer.

## Least-privilege tokens

**Least privilege** means giving a token the smallest set of permissions that does the job, so a leaked one can do little. For machine tokens, three dials:

| Dial | The question | This project's example |
|---|---|---|
| **Scope** | What may this token do? | The DigitalOcean token has a custom list of scopes, not full access ([Doppler and secrets](Doppler-and-Secrets.md#who-holds-what)). |
| **Reach** | Which assets can it touch? | A Doppler service token reads one config of one project, read-only by default. |
| **Time** | For how long? | 90 days for Spacelift's token; hours to a day for a first-boot token. |

Read-only is a real dial, with a caution from the [Enterprise page](Enterprise-Identity-and-Secrets-at-Scale.md#predict-then-check): a read-only token that can read a **write-capable** token has write power in effect. So the dials apply to what the token **reads**, too. Choose the shortest time you can live with, and the narrowest config. If a service gives you only "full access", that is a reason to ask what you are trading for the convenience.

## After a leak: revoke, rotate, look, then clean

When a secret is seen where it should not be, the order matters, and it is the same order everywhere. GitHub's removal guide (read 2026-10-22) says it as a first step: "you need to revoke and/or rotate that secret", and that once that is done it "may be sufficient to solve your problem". GitHub's secret scanning page says rewriting history is "time-intensive and often unnecessary if you've already revoked the credential". The OWASP cheat sheet's incident-response section lists the containment steps as revocation, rotation, deletion and logging, in that order.

1. **Revoke.** At the issuer, now. Do not wait to learn whether anyone used it. Do not start by deleting the file.
2. **Rotate.** Issue a replacement with the narrowest scope and a short expiry, put it in the secrets manager, and update what needed it. Test that the thing works with the new value.
3. **Check the logs.** Look at the issuer's audit log for the window between the leak and the revoke: what used it that was not you? OWASP lists the questions: who had access, when did they use it, when was it last rotated. If something unfamiliar used it, this is now an incident (see [Working in a company](Working-in-a-Company-Tickets-Change-On-Call-and-Documentation.md) for how companies run one).
4. **Clean history, last.** Rewrite the repository to remove the value, force-push, and ask the other copy-holders to discard theirs. This is tidiness and hygiene. It does not make the value safe, because the revoke already did, and it cannot reach other people's clones or forks.
5. **Learn.** Write down how it got there and which check would have caught it. [Lessons learned](Lessons-Learned.md) is the project's example.

### Why deleting the file is not enough

Three reasons, all shown in [exercise 4](#exercise-4-the-leak-drill-revoke-rotate-check-then-clean):

- A delete is a new commit. The old commit, with the secret, is still there. A scan of your folder says "clean"; a scan of your history does not.
- A rewrite changes **your** repository. A clone made before the rewrite still has the old commit. GitHub's guide lists the places the old commits may live on after a force-push: other clones and forks, cached views on GitHub that are reachable by commit hash, and pull requests that reference them. Removing the cached views and pull-request references means contacting GitHub Support with specific details, and Support says it will only help where rotating the credential cannot mitigate the risk.
- A rewrite has side effects: changed commit hashes, broken signatures, damaged pull-request diffs and a risk that a collaborator's next push puts the secret back. GitHub's guide lists these and says to coordinate with everyone who cloned.

## Solo lab versus enterprise IAM

**IAM** (identity and access management) is the set of tools and rules that decide who may do what. Enterprises have a lot of it. The [Enterprise page](Enterprise-Identity-and-Secrets-at-Scale.md) covers it properly. The maintainer's point is that **a lab is a different job:** you build it for yourself, with at most a handful of other humans touching it, and a very small number of identities means the enterprise table does not fit until the lab grows.

| Concern | Enterprise | A solo or few-person lab |
|---|---|---|
| People signing in | Single sign-on through an identity provider, MFA by policy, joiner-mover-leaver automation. | Your own accounts, MFA on each, a password manager. SSO appears when you add a second person and an identity provider you already have. |
| Roles | Role-based or attribute-based access, groups sourced from the directory. | You are the admin. A second human gets the narrowest role you can find, not admin by default. |
| Privileged access | PAM vaults admin credentials, grants just-in-time access, records sessions. | A separate admin account from your daily one, if the service allows. A physical security key. |
| **Break-glass** | A sealed emergency admin account, alarmed on use, tested on a schedule. | The offline copy of your recovery codes and the master-password recovery path from step 1. It is your break-glass. Test it once. |
| Machine identity | Workload identity (OIDC) so no stored token exists. | One read-only token per asset, short-lived, rotated by hand, as this page shows. OIDC arrives when the vendor plans allow it ([the runbook](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md) section 5a has what each option needs, as read on 2026-10-21). |
| Audit | Immutable logs reviewed by a team, access reviews. | Read the issuer's log after any event, and once a month anyway. |

### Who can actually touch your lab

Make a list, on paper, before you add a second person: every human who can sign in to your cloud account, your Spacelift workspace, your Doppler workspace and your GitHub repository, and every **machine** that can (a CI robot, an app installed on your repository). The [Enterprise page](Enterprise-Identity-and-Secrets-at-Scale.md#privileged-access-pam-just-in-time-and-break-glass) says the [Threat model](Threat-Model.md) accepts that one person holds standing access to everything here. Each person you add is another laptop, another password manager, another phone, and another place for a token to land. Add them on purpose, with the least access that works, and write down what you gave them.

### Bots in the logs

The maintainer's experience is that a server with a public address collects probes from automated programs that try common usernames and passwords, dozens of them showing up in the logs even from a server that has been up a short time. This page has no measured figure for how fast or how many (that depends on the address and the day), so I make no claim about rates; [exercise 5](#exercise-5-read-an-ssh-auth-log-the-noise-and-the-signal) builds a synthetic log so you can practice reading the pattern. What the pattern teaches:

- **Most lines are noise, and the noise is harmless if nothing on the server accepts a password.** This project's droplets accept SSH keys only ([Identity page](Identity-Secrets-and-Zero-Trust-Basics.md#how-keys-work-without-the-math)), so the guessing has nothing to work with.
- **The line that matters is rare:** an `Accepted` line from an address you do not recognize, especially after many failures from that same address, or an `Accepted password` on a machine that should not allow passwords.
- **Do not chase the noise.** Blocking every address is a hobby with no end. Reduce what is exposed, turn off password sign-in, and alert on the rare lines. The [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) page and the [honeypot lessons](Deception-and-Honeypots-Start-Here.md) go further.

## The honest limits

A secrets manager is not magic. Say these out loud before you adopt one:

- **It is another thing to protect.** The first secret problem never goes away: something must authenticate to the secrets manager. OWASP's cheat sheet says so: you "will often have to secure the primary secret of that secrets management solution in a secondary secrets management solution". Here that first secret is the Doppler token, and the first-boot token. They are small, scoped and expire; they are still secrets.
- **It is a dependency.** If Doppler is down, a run that needs a secret fails. Doppler's CLI keeps the encrypted fallback file so a program can start from the last fetch; know whether yours does. OWASP's section on downtime asks you to plan for the service being unavailable, to back up and **test the restore**, and to keep emergency break-glass credentials in a second place that is tested. Write the plan before the outage: who can start the service with a cached value, who can reach the vendor's dashboard, and what you do with no secrets manager at all for an hour.
- **Doppler cannot see what it does not hold.** A secret you still paste into a script is as exposed as it ever was.
- **Whoever can read a config can read everything in it.** A shared "prd" config means everyone and everything with a token for it sees all of it, which is why the per-asset pattern exists.
- **Your recovery path is yours to have.** I did not read Doppler's account recovery documentation, so I cannot tell you what it does if you lose your sign-in and your MFA (est.; find out for the account you use, today). For the password manager, step 1 has the recovery path; for Doppler, the same discipline applies: recovery codes offline, two MFA methods, and a note of who else could regain access.
- **It does not clean up after you.** A value that was in a log last year is still in last year's log.

## Threat model of the secrets path

A threat model here is a short, ranked list of what you are protecting, from whom, and what stops them. The path a secret takes runs from a person to a laptop to a repository to CI to a host, with Doppler beside it. This is a lab-scale model, not a complete audit; no one probed any real system for it. The [Threat model](Threat-Model.md) is the project's own, and the page on [threat frameworks](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md) names the formal methods.

**Assets:** your password manager vault and its recovery material; the sign-ins to your cloud, Doppler and GitHub accounts; Doppler service tokens; cloud API tokens; SSH private keys; the values inside every Doppler config.
**Actors:** automated bots scanning for exposed secrets and weak logins (constant); an opportunistic thief of a laptop or phone; a malicious or careless collaborator; a compromised dependency or CI action; you, tired; the vendor (a breach on their side).
**Trust boundaries:** laptop to repository; repository to CI; CI or Spacelift to Doppler; Doppler to a host; you to your own accounts.

| Where | Abuse case | Mitigation | How to check it works | Residual risk |
|---|---|---|---|---|
| **The person** | Weak or reused password; phishing; losing the phone and the recovery codes together. | Password manager, MFA (security key where possible), recovery codes offline, two MFA methods. | Sign in from a second device. Open the offline codes sheet and confirm each code is readable (do not use one). | A phished or malware-hit session beats most MFA types except FIDO; a lost vault with no recovery path is gone. |
| **The laptop** | A stolen or malware-hit machine reads `.env` files, the vault when unlocked, the shell history and the SSH agent. | Full-disk encryption, a screen lock, `.env` mode 0600 and local-only, keys with passphrases, `read -rs` to enter secrets. | `stat` on each `.env`; `git status` shows no secrets file; `history` has no token. | Malware running as you can read anything you can. Keep few secrets on the laptop, and short-lived ones. |
| **The repository** | A secret committed once lives in history, forks and clones. | `.gitignore` plus a pre-commit hook plus push protection; `.env.example` with dummies. | Exercise 1 and 2: plant a dummy, see it caught; the CI scan reads full history. | Home-made token shapes, encodings and splits (see the limits above). A secret already pushed is exposed until revoked. |
| **CI** | A log that prints a secret; a pull request that tries to read the token; a compromised third-party action. | Mask secrets, no secrets on pull-request runs, pin actions by commit, a token that is read-only and scoped. [Doppler and secrets](Doppler-and-Secrets.md#how-the-hook-works) and [From commit to pipeline](From-Commit-to-Pipeline.md) go deeper. | Search a run log for the token's prefix; the hook's tests prove proposed runs get nothing. | Code that can get into a run can read what the run can read; this project's own page says so. |
| **The host** | Another process or user reads the environment or a file; the token in `user_data` is read from the metadata endpoint. | Root-only 0600 files that are deleted after use, fail-closed first boot, short-lived tokens, a revoke after first boot. | The stage 2 guide's tests; `stat` on any file holding a token (exercise 3 shows reading an environment). | Copies of the bootstrap token persist in state, the provider API and cloud-init's retained copy until it expires (documented in the stage 2 guide). |
| **Doppler** | A leaked service token reads one config; a stolen account reads all of them; the vendor is breached or unavailable. | One config and one short-lived read-only token per asset; MFA and recovery codes on the account; an outage plan; rotation on a schedule. | Revoke a token and confirm refusal with `--no-fallback`; read the activity log. | You trust Doppler's design and operations. The free plan keeps three days of activity logs (est., per the pricing page), so the evidence of use is short. |

**Ranking.** By impact times how easy the first step is: (1) a reused or phished personal password, because it opens the password manager's neighbors; (2) a secret in history on a public repository, because automated scanners read new public commits (est.); (3) a long-lived token with broad scope, because one leak is a large one; (4) a host file left world-readable; (5) a Doppler outage or lost recovery path, because it stops work or the lab rather than leaking. The mitigations above are in that order for a reason.

## Hands-on: free and local

Everything in this section runs on your own computer and costs nothing; the lessons are free and will stay free. Each exercise has four steps: **predict** (write down what you expect first), **do**, **check**, **undo**. Exercises 1 and 4 share one scratch repository, so do 1 first.

**Which track.** Bash and PowerShell are given for each step. All PowerShell here is **est.** (not run). Where the page says `python3`, Windows usually has `python` or the `py` launcher (est.). The Python files are identical on every system: in PowerShell, save the text from the Bash block into a file of the same name with any editor.

### Setup

```bash
LAB=$(mktemp -d)        # a scratch folder; everything below happens in it, and nothing is ever pushed
cd "$LAB" && echo "$LAB"
python3 -I -c 'import sys; print(sys.version.split()[0])'
git --version
```

```powershell
$LAB = New-Item -ItemType Directory -Path (Join-Path ([IO.Path]::GetTempPath()) ("secrets-lab-" + [guid]::NewGuid().ToString("N").Substring(0,8)))
Set-Location $LAB; $LAB.FullName
python -I -c "import sys; print(sys.version.split()[0])"
git --version
```

If you open a new terminal later, `$LAB` is empty: do not run a `rm -r` with it; `cd` into the folder by hand.

### Exercise 1: plant a dummy secret and catch it

You will plant a dummy secret in a scratch repository, remove it again, and see that a scan of the **files** says clean while a scan of the **history** does not.

**Step A: the pretend issuer.** It makes tokens shaped like a GitHub personal access token (so real scanners recognize the shape) but issued by nothing. It writes each token to a 0600 file, never to the screen. Save as `fake_issuer.py` in `$LAB`:

```python
#!/usr/bin/env python3
"""fake_issuer.py - a pretend token issuer, standing in for a real service. Local files only, no network.

  python3 fake_issuer.py issue NAME        make a token, save it to tokens/NAME.token next to this script (mode 0600)
  python3 fake_issuer.py check FILE [WHO]  is the token in FILE accepted right now? exit 0 yes, 1 no (logs WHO tried it)
  python3 fake_issuer.py revoke NAME       stop accepting NAME's token, now
  python3 fake_issuer.py log               print the access log (one line per check)
"""
import hashlib, json, os, secrets, string, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))  # state lives next to this script, wherever you run it from
DB, LOG, TOKENS = (os.path.join(HERE, n) for n in ("issuer.json", "issuer.log", "tokens"))


def load():
    return json.load(open(DB)) if os.path.exists(DB) else {}


def save(db):
    json.dump(db, open(DB, "w"), indent=2)


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd, db = argv[1], load()
    if cmd == "issue" and len(argv) == 3:
        name = argv[2]
        token = "ghp_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36))
        os.makedirs(TOKENS, exist_ok=True)
        fd = os.open(os.path.join(TOKENS, name + ".token"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(token + "\n")
        db[name] = {"sha256": digest(token), "active": True}
        save(db)
        print("issued %s (the value is in tokens/%s.token, not on screen)" % (name, name))
    elif cmd == "check" and len(argv) in (3, 4):
        token = open(argv[2]).read().strip()
        match = [n for n, e in db.items() if e["sha256"] == digest(token)]
        ok = bool(match) and db[match[0]]["active"]
        who = argv[3] if len(argv) == 4 else "unknown"
        with open(LOG, "a") as log:
            log.write("%s who=%s token=%s result=%s\n" % (time.strftime("%H:%M:%S"), who,
                                                         match[0] if match else "unknown", "ACCEPTED" if ok else "REJECTED"))
        print("ACCEPTED" if ok else "REJECTED (401)")
        sys.exit(0 if ok else 1)
    elif cmd == "revoke" and len(argv) == 3 and argv[2] in db:
        db[argv[2]]["active"] = False
        save(db)
        print("revoked %s" % argv[2])
    elif cmd == "log":
        print(open(LOG).read() if os.path.exists(LOG) else "(no checks yet)", end="")
    else:
        sys.exit(__doc__)


main(sys.argv)
```

**Step B: the teaching scanner.** Save as `scan_secrets.py` in `$LAB`. It is a small stand-in for gitleaks: three rules, an entropy floor, a placeholder filter, a tree mode and a history mode. It never prints a whole value.

```python
#!/usr/bin/env python3
"""scan_secrets.py - a small teaching secret finder. It is NOT a replacement for gitleaks.

  python3 scan_secrets.py tree PATH       scan the files under PATH (skips .git)
  python3 scan_secrets.py history REPO    scan every line ever ADDED on any branch of REPO
  python3 scan_secrets.py --self-test     build fixtures at run time and check the rules

Exit code: 0 nothing found, 1 something found. A finding never prints the whole value.
"""
import math, os, random, re, string, subprocess, sys

PLACEHOLDER = re.compile(r"(?i)example|changeme|change-me|dummy|your[-_]|placeholder|xxxx|<[^>]*>|\$\{")
RULES = [  # (name, pattern, minimum entropy of the matched value)
    ("github-token-shape", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b"), 0.0),
    ("private-key-header", re.compile("-----BEGIN [A-Z ]*PRIV" + "ATE KEY-----"), 0.0),
    ("assigned-secret", re.compile(
        r"""(?i)[\w.-]*(?:secret|token|passw(?:or)?d|api[_-]?key)[\w.-]*\s*[:=]\s*['"]?([A-Za-z0-9_\-+/=]{16,})"""), 3.0),
]


def entropy(text):
    """Shannon entropy in bits per character: random text is high, English and repeats are low."""
    return -sum(text.count(c) / len(text) * math.log2(text.count(c) / len(text)) for c in set(text))


def check_line(line):
    """Return a list of (rule, redacted value) for one line of text."""
    found = []
    for name, rx, floor in RULES:
        for m in rx.finditer(line):
            value = m.group(1) if rx.groups else m.group(0)
            if PLACEHOLDER.search(value) or entropy(value) < floor:
                continue
            found.append((name, value[:4] + "..." + "(%d chars)" % len(value)))
    return found


def scan_tree(path):
    hits = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            full = os.path.join(root, f)
            try:
                lines = open(full, encoding="utf-8", errors="strict").read().splitlines()
            except (UnicodeDecodeError, OSError):
                continue  # binary or unreadable: a real scanner decodes more than this one does
            for n, line in enumerate(lines, 1):
                for rule, red in check_line(line):
                    hits.append((rule, "%s:%d" % (os.path.relpath(full, path), n), red))
    return hits


def scan_history(repo):
    out = subprocess.run(["git", "-C", repo, "log", "--all", "-p", "-U0", "--no-color", "--format=@@commit %H"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout
    hits, commit, path = [], "", ""
    for line in out.splitlines():
        if line.startswith("@@commit "):
            commit = line[9:17]
        elif line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            for rule, red in check_line(line[1:]):
                hits.append((rule, "%s %s" % (commit, path), red))
    return hits


def self_test():
    rnd = random.SystemRandom()
    alnum = string.ascii_letters + string.digits
    token = "ghp_" + "".join(rnd.choice(alnum) for _ in range(36))
    password = "".join(rnd.choice(alnum + "-_") for _ in range(24))
    must_find = ["DEPLOY_TOKEN=" + token, 'x = "%s"' % token, 'db_password: "%s"' % password]
    must_skip = ["API_KEY=replace-with-your-api-key-value", "TOKEN=", "password = 'changeme-changeme-1234'",
                 "api_key = " + "a" * 24, "see the token documentation"]
    for text in must_find:
        assert check_line(text), "missed: " + text[:12] + "..."
    for text in must_skip:
        assert not check_line(text), "false positive on: " + text
    print("self-test passed: %d must-find lines found, %d must-skip lines skipped" % (len(must_find), len(must_skip)))


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test(); sys.exit(0)
    if len(sys.argv) != 3 or sys.argv[1] not in ("tree", "history"):
        sys.exit(__doc__)
    results = scan_tree(sys.argv[2]) if sys.argv[1] == "tree" else scan_history(sys.argv[2])
    for rule, where, red in results:
        print("FOUND %-24s %-28s %s" % (rule, where, red))
    print("%d finding(s)" % len(results))
    sys.exit(1 if results else 0)
```

**Predict.** Write down, before you run anything: (a) after you commit a file with a token and then delete it in the next commit, will `scan_secrets.py tree` find it? (b) will `scan_secrets.py history`? (c) which one would a CI job that checks only the newest files miss?

**Do (Bash).**

```bash
cd "$LAB"
python3 -I scan_secrets.py --self-test                 # the tiny test: three must-finds, five must-skips
python3 -I fake_issuer.py issue deploy                 # a dummy token, in tokens/deploy.token, mode 0600
mkdir repo && cd repo && git init -q -b main
git config user.email learner@example.invalid && git config user.name learner
echo "hello" > README.md && git add README.md && git commit -qm "start"
printf 'DEPLOY_API_KEY="%s"\n' "$(cat ../tokens/deploy.token)" > deploy.sh      # the mistake
git add deploy.sh && git commit -qm "add deploy script"
git rm -q deploy.sh && git commit -qm "remove the deploy script"                 # the "fix"
git log --oneline
python3 -I ../scan_secrets.py tree . ; echo "tree exit: $?"
python3 -I ../scan_secrets.py history . ; echo "history exit: $?"
```

**Do (PowerShell, est.).**

```powershell
Set-Location $LAB
python scan_secrets.py --self-test
python fake_issuer.py issue deploy
git init -q -b main repo; Set-Location repo
git config user.email learner@example.invalid; git config user.name learner
Set-Content -Encoding ascii README.md "hello"; git add README.md; git commit -qm "start"
$tok = (Get-Content ..\tokens\deploy.token).Trim()
Set-Content -Encoding ascii deploy.sh ('DEPLOY_API_KEY="' + $tok + '"'); Remove-Variable tok
git add deploy.sh; git commit -qm "add deploy script"
git rm -q deploy.sh; git commit -qm "remove the deploy script"
git log --oneline
python ..\scan_secrets.py tree .; "tree exit: $LASTEXITCODE"
python ..\scan_secrets.py history .; "history exit: $LASTEXITCODE"
```

**Check.** The self-test prints `self-test passed: 3 must-find lines found, 5 must-skip lines skipped`. The log lists three commits. The tree scan finds nothing and exits 0: the file is gone. The history scan finds the token in the middle commit and exits 1. From the 2026-10-22 run (your hashes will differ; the value is redacted):

```text
FOUND github-token-shape       4883c23b deploy.sh           ghp_...(40 chars)
FOUND assigned-secret          4883c23b deploy.sh           ghp_...(40 chars)
2 finding(s)
history exit: 1
```

Two rules matched the same line, which is normal. The answers to the predictions: (a) no, (b) yes, (c) a scan of files only. This is the whole reason secret scanners read history.

**Optional: the same check with gitleaks.** Download policy: only if you choose to, from the **official release** on the project's GitHub releases page, into a scratch folder, with the checksum checked before you run anything. Check the [releases page](https://github.com/gitleaks/gitleaks/releases) for the current version; 8.30.1 (published 2026-03-21) is what was run here.

```bash
cd "$LAB" && mkdir gitleaks-dl && cd gitleaks-dl
V=8.30.1; B=https://github.com/gitleaks/gitleaks/releases/download/v$V
curl -fsSL -O "$B/gitleaks_${V}_linux_x64.tar.gz" -O "$B/gitleaks_${V}_checksums.txt"
grep 'linux_x64.tar.gz' "gitleaks_${V}_checksums.txt" | sha256sum -c -     # must print: OK
mkdir bin && tar -xzf "gitleaks_${V}_linux_x64.tar.gz" -C bin gitleaks
export PATH="$PWD/bin:$PATH" && gitleaks version
cd "$LAB/repo" && gitleaks git -v --redact --no-banner . ; echo "gitleaks exit: $?"
```

On macOS, use the `darwin_arm64` or `darwin_x64` file name and `shasum -a 256 -c -` (est.). On Windows, download `windows_x64.zip`, compute `Get-FileHash -Algorithm SHA256` and compare it by eye to the line in the checksums file (est.). Be honest about what the checksum proves: the checksums file comes from the same release page as the program, so a match shows the download is intact, **not** that the release itself is trustworthy. I did not check whether the project signs its releases or publishes attestations; if that matters to you, look, or install through a package manager you already trust.

With gitleaks 8.30.1 the scan printed one finding, trimmed here (the commit, author and date lines are left out, and `--redact` hides the value):

```text
Finding:     DEPLOY_API_KEY="REDACTED
Secret:      REDACTED
RuleID:      github-pat
Entropy:     4.921928
File:        deploy.sh
Line:        1
Fingerprint: <commit>:deploy.sh:github-pat:1
INF 2 commits scanned.
WRN leaks found: 1
```

and exited 1. `Entropy` is the randomness score described in the limits section. Run `gitleaks dir . --redact --no-banner` too and see it report `no leaks found` for the current files, as the teaching scanner did.

**Undo.** Keep the folder: exercise 4 continues in `$LAB/repo`. The cleanup for everything is at the end of the exercises.

### Exercise 2: .env, .env.example and .gitignore that work together

**Predict.** If `.gitignore` lists `.env`, can a `.env` file ever end up in a commit? And will `.env.example` be ignored by a rule that says `.env.*`?

**Do (Bash).**

```bash
cd "$LAB" && mkdir env-lab && cd env-lab && git init -q -b main
git config user.email learner@example.invalid && git config user.name learner
cat > .gitignore <<'EOF'
# local secrets files stay on this machine
.env
.env.*
!.env.example
EOF
cat > .env.example <<'EOF'
# Copy this file to .env and fill in your own values. Never put a real value in THIS file.
# Names of things (safe to share):
DOPPLER_PROJECT=example-project
DOPPLER_CONFIG=dev
API_BASE_URL=https://api.example.com
# Values you must supply yourself (dummy here):
API_TOKEN=replace-with-your-token
EOF
cp .env.example .env
sed -i.bak "s|^API_TOKEN=.*|API_TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')|" .env && rm .env.bak
chmod 600 .env
stat -c '%a %U %n' .env .env.example          # GNU stat; on macOS: stat -f '%Lp %Su %N' .env .env.example
git check-ignore .env .env.local .env.example # prints only the paths git WILL ignore
git add -A && git status --short
git commit -qm "add the example, not the real file"
git ls-files
```

```bash
# the names in .env.example and .env must match (no output from diff means they do)
diff <(sed -n 's/^\([A-Z_][A-Z0-9_]*\)=.*/\1/p' .env.example | sort -u) <(sed -n 's/^\([A-Z_][A-Z0-9_]*\)=.*/\1/p' .env | sort -u) && echo "same names"
# break it two ways
git add -f .env && git status --short         # -f overrides the ignore rule
git rm -q --cached .env && git status --short # take it back out of the index (the file stays on disk)
python3 -I ../scan_secrets.py tree . ; echo "exit: $?"
```

**Do (PowerShell, est.).**

```powershell
Set-Location $LAB; New-Item -ItemType Directory env-lab | Out-Null; Set-Location env-lab; git init -q -b main
git config user.email learner@example.invalid; git config user.name learner
Set-Content -Encoding ascii .gitignore @("# local secrets files stay on this machine", ".env", ".env.*", "!.env.example")
Set-Content -Encoding ascii .env.example @("# Copy this file to .env and fill in your own values. Never put a real value in THIS file.",
  "DOPPLER_PROJECT=example-project", "DOPPLER_CONFIG=dev", "API_BASE_URL=https://api.example.com", "API_TOKEN=replace-with-your-token")
$v = python -c "import secrets; print(secrets.token_urlsafe(24))"
(Get-Content .env.example) -replace '^API_TOKEN=.*', "API_TOKEN=$v" | Set-Content -Encoding ascii .env; Remove-Variable v
icacls .env /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null; icacls .env       # only you can read it
git check-ignore .env .env.local .env.example
git add -A; git status --short; git commit -qm "add the example, not the real file"; git ls-files
Compare-Object (Select-String '^[A-Z_][A-Z0-9_]*=' .env.example | % { ($_.Line -split '=')[0] }) (Select-String '^[A-Z_][A-Z0-9_]*=' .env | % { ($_.Line -split '=')[0] })
git add -f .env; git status --short; git rm -q --cached .env; git status --short
python ..\scan_secrets.py tree .
```

**Check.** `stat` shows `600` for `.env`. `git check-ignore` prints `.env` and `.env.local` and **not** `.env.example`, because of the `!` rule. `git status` shows `.env.example` and `.gitignore` added and no `.env`; `git ls-files` lists the same two. The `diff` prints `same names` (a name added to `.env` but missing from the example would show up as a diff line; try it). After `git add -f .env` the status shows `A  .env`: the ignore file did not stop a forced add. After `git rm --cached` it is untracked again. The tree scan flags the line `API_TOKEN=...` in `.env` (the random value) and does **not** flag `.env.example` (the placeholder filter skips `replace-with-your-token`):

```text
FOUND assigned-secret          .env:7                       51iQ...(32 chars)
1 finding(s)
```

Two lessons. A local `.env` **will** look like a secret to a scanner, which is right: that is why it is ignored and never pushed. And the placeholder filter is itself a hole: a real secret that contains the word `example` would be skipped. Real scanners have the same trade-off, which is why their allow-lists need review. The answer to the prediction: `.gitignore` stops an **accidental** `git add`, not a forced one and not a file that is already tracked.

**Undo.** `cd "$LAB" && rm -rf env-lab` (PowerShell: `Set-Location $LAB; Remove-Item -Recurse env-lab`).

### Exercise 3: environment, file or injected? Who can read each

**Predict.** If you `export` a value in your shell and then start two other programs, do they see it? If you start a long-running program, can you read its environment from outside it, as the same user?

**Do (Bash).**

```bash
export DEMO_VALUE="$(python3 -c 'import secrets; print(secrets.token_hex(8))')"     # a dummy; not printed
bash -c 'echo "child shell sees ${#DEMO_VALUE} characters"'
python3 -I -c 'import os; print("python child sees", len(os.environ.get("DEMO_VALUE", "")), "characters")'
sleep 30 & pid=$!; sleep 1                                  # a long-running program that inherited it
tr '\0' '\n' < /proc/$pid/environ | grep -c '^DEMO_VALUE='   # Linux: the same user can read another process's environment
ps -o args= -p $pid                                          # the command line shows the arguments only
ps eww -o args= -p $pid | grep -c DEMO_VALUE                 # but 'ps e' appends the environment (value hidden here)
ls -l /proc/$pid/environ
kill $pid; unset DEMO_VALUE
```

**Do (PowerShell, est.).** There is no `/proc` on Windows, so only the inheritance half applies.

```powershell
$env:DEMO_VALUE = python -c "import secrets; print(secrets.token_hex(8))"
powershell -NoProfile -Command "'child sees ' + $env:DEMO_VALUE.Length + ' characters'"
python -I -c "import os; print('python child sees', len(os.environ.get('DEMO_VALUE', '')), 'characters')"
Remove-Item Env:DEMO_VALUE
```

**Check.** Both children print `16 characters`. On Linux the `/proc` read printed `1`: the value was readable from outside the process, by the same user, and the `ps eww` line matched too. `ls -l` shows `-r--------` owned by you, which is why other **non-root** users cannot read it; root can (general knowledge; I did not test as root). The `ps` arguments line shows only `sleep 30`: the value is not in the arguments, but is in the environment. (The one-second `sleep` matters: read too early and the new process has no environment to read yet; I saw a `0` once for that reason.) The lesson is not that environment variables are bad; it is that **an environment variable is readable by anything running as you, and inherited by everything you start.** Put short-lived values there, for a short-lived process.

**Undo.** The `kill` and `unset` already did it.

### Exercise 4: the leak drill (revoke, rotate, check, then clean)

The drill, in the order the page argued for. You will use the repository from exercise 1, where the token `deploy` was leaked into the history.

**Predict.** (a) If you revoke the token **first**, will the old copy in git still scan as a leak? (b) After you rewrite history, will a clone you made before the rewrite still hold the token? (c) In which step do you learn whether anyone used the token?

**Do (Bash).** Step 1, a copy of the repository as "someone else's clone", and the attacker's view:

```bash
cd "$LAB" && git clone -q repo oldclone                                  # a clone made BEFORE any cleanup
cd repo && git show HEAD~1:deploy.sh | cut -d'"' -f2 > ../stolen.token   # a stranger reads the old commit
python3 -I ../fake_issuer.py check ../stolen.token 203.0.113.50; echo "exit: $?"
python3 -I ../fake_issuer.py check ../tokens/deploy.token ci-runner; echo "exit: $?"
```

Step 2, **revoke first**, then prove the old value is dead:

```bash
python3 -I ../fake_issuer.py revoke deploy
python3 -I ../fake_issuer.py check ../stolen.token proof-of-death; echo "exit: $?"
```

Step 3, **rotate**: issue a replacement and test it:

```bash
python3 -I ../fake_issuer.py issue deploy-2
python3 -I ../fake_issuer.py check ../tokens/deploy-2.token ci-runner; echo "exit: $?"
```

Step 4, **check the logs** for the window between the leak and the revoke:

```bash
python3 -I ../fake_issuer.py log
```

Step 5, **clean history, last**. The preferred tool is `git filter-repo` (an add-on to git; install it from your package manager or from the [project's page](https://github.com/newren/git-filter-repo), and read what it does first). If you do not have it, the fallback below uses only git. **Do this only in the scratch repository.**

```bash
# with git filter-repo (preferred): remove the file from every commit on every branch
git filter-repo --invert-paths --path deploy.sh --force
```

```bash
# fallback with plain git (slower, with its own warnings): rewrite, then drop the backup refs and the reflog
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch deploy.sh' --prune-empty -- --all
rm -rf .git/refs/original && git reflog expire --expire=now --all && git gc -q --prune=now
```

Step 6, **rescan**, and look at the old clone:

```bash
git log --oneline
python3 -I ../scan_secrets.py history . ; echo "history exit: $?"
cd "$LAB" && python3 -I scan_secrets.py history oldclone ; echo "oldclone exit: $?"
```

**Do (PowerShell, est.).** The same steps; the only changes are the shell syntax around them.

```powershell
Set-Location $LAB; git clone -q repo oldclone; Set-Location repo
(git show HEAD~1:deploy.sh) -split '"' | Select-Object -Index 1 | Set-Content -Encoding ascii ..\stolen.token
python ..\fake_issuer.py check ..\stolen.token 203.0.113.50
python ..\fake_issuer.py check ..\tokens\deploy.token ci-runner
python ..\fake_issuer.py revoke deploy
python ..\fake_issuer.py check ..\stolen.token proof-of-death
python ..\fake_issuer.py issue deploy-2
python ..\fake_issuer.py check ..\tokens\deploy-2.token ci-runner
python ..\fake_issuer.py log
git filter-repo --invert-paths --path deploy.sh --force
# no git filter-repo? the plain-git fallback in PowerShell:
#   git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch deploy.sh' --prune-empty -- --all
#   Remove-Item -Recurse -Force .git\refs\original; git reflog expire --expire=now --all; git gc -q --prune=now
git log --oneline
python ..\scan_secrets.py history .
Set-Location $LAB; python scan_secrets.py history oldclone
```

**Check.** From the 2026-10-22 run (times and hashes differ):

```text
ACCEPTED                                  # the stranger's copy worked: the value was live while it sat in history
ACCEPTED                                  # your own CI
revoked deploy
REJECTED (401)                            # proof the old value is dead
issued deploy-2 (the value is in tokens/deploy-2.token, not on screen)
ACCEPTED                                  # the replacement works

17:44:47 who=203.0.113.50 token=deploy result=ACCEPTED
17:44:47 who=ci-runner token=deploy result=ACCEPTED
17:44:48 who=proof-of-death token=deploy result=REJECTED
17:44:48 who=ci-runner token=deploy-2 result=ACCEPTED
```

The log is step 3 of the drill working: one line used the token from an address that is **not** yours (203.0.113.50, a documentation address standing for a stranger). In a real incident that line is the news, and it starts the part of the work this page cannot script. Then the rewrite: after `filter-repo` the log shows one commit (`start`), the history scan prints `0 finding(s)` with exit 0, and `gitleaks git` (if you installed it) reports no leaks. **The old clone still scans as a leak** (`2 finding(s)`, exit 1): the rewrite did not touch it, which is the whole reason revoke is first. With the plain-git fallback, skipping the `rm -rf .git/refs/original` and the `reflog expire` step left the history scan reporting 2 findings (the backup refs keep the old commits), and after them it reported none.

The answers to the predictions: (a) yes, the scan still finds the shape; a scanner knows nothing about whether a value is live, which is why you test the issuer; (b) yes; (c) step 4, in the issuer's own log, not in git.

If you were doing this on a real hosted repository, the force-push, the cached views, the pull requests and the fork owners are what [GitHub's guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) is about. None of that was run here.

**Undo.** Nothing outside `$LAB`. The cleanup is at the end.

### Exercise 5: read an SSH auth log (the noise and the signal)

You will build a synthetic day of SSH sign-in lines (every address is a documentation address, the host name is made up) and find the lines worth a human's time.

**Step A.** Save as `gen_authlog.py` in `$LAB`:

```python
#!/usr/bin/env python3
"""gen_authlog.py - write ./auth.log: one invented day of SSH sign-in lines. Every address is a documentation address
(RFC 5737), the host name is made up, and the random seed is fixed so your numbers match the page."""
import random

rnd = random.Random(2026)
USERS = ["root", "admin", "ubuntu", "test", "oracle", "postgres", "git", "pi", "user", "ftpuser", "guest", "deploy"]
BOTS = ["192.0.2.%d" % n for n in (14, 23, 77, 130, 201)] + ["198.51.100.%d" % n for n in (9, 66, 142)] + \
       ["203.0.113.%d" % n for n in (5, 66, 99, 180)]
OPERATOR = "198.51.100.7"          # the learner's own address, for this exercise
events = []                        # (seconds since midnight, text)

def line(sec, text):
    events.append((sec, "Oct 22 %02d:%02d:%02d demo-host sshd[%d]: %s" % (sec // 3600, sec % 3600 // 60, sec % 60,
                                                                           rnd.randint(1000, 60000), text)))

for ip in BOTS:                                   # constant background noise, all day
    for _ in range(rnd.randint(25, 70)):
        sec, user, port = rnd.randint(0, 86399), rnd.choice(USERS), rnd.randint(30000, 65000)
        if user == "root":
            line(sec, "Failed password for root from %s port %d ssh2" % (ip, port))
        else:
            line(sec, "Invalid user %s from %s port %d" % (user, ip, port))
            line(sec + 1, "Failed password for invalid user %s from %s port %d ssh2" % (user, ip, port))
        line(sec + 2, "Connection closed by authenticating user %s %s port %d [preauth]" % (user, ip, port))

for sec in (8 * 3600 + 120, 12 * 3600 + 905, 17 * 3600 + 2011):   # the operator, with a key
    line(sec, "Accepted publickey for opuser from %s port %d ssh2: ED25519 SHA256:EXAMPLEFINGERPRINT" % (OPERATOR, rnd.randint(30000, 65000)))

line(4 * 3600 + 1800, "Accepted password for root from 203.0.113.66 port 40022 ssh2")   # the line that matters

with open("auth.log", "w") as f:
    for _, text in sorted(events, key=lambda e: e[0]):
        f.write(text + "\n")
print("wrote auth.log with %d lines" % len(events))
```

**Step B.** Save as `read_auth.py` in `$LAB`:

```python
#!/usr/bin/env python3
"""read_auth.py FILE - split an SSH auth log into background noise and the lines worth a human's time."""
import collections, re, sys

fails, users, hours, seen_fail = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
accepted = []
for text in open(sys.argv[1]):
    ip = re.search(r" from (\d+\.\d+\.\d+\.\d+) ", text)
    if "Failed password" in text and ip:
        fails[ip.group(1)] += 1
        seen_fail[ip.group(1)] += 1
        hours[text[7:9]] += 1
        who = re.search(r"for (?:invalid user )?(\S+) from", text)
        users[who.group(1)] += 1
    elif "Accepted" in text and ip:
        accepted.append((text.split()[2], text.split("Accepted ")[1].split(" for ")[0], re.search(r"for (\S+) from", text).group(1),
                         ip.group(1), seen_fail[ip.group(1)]))

print("failed passwords: %d from %d addresses" % (sum(fails.values()), len(fails)))
print("most tried names:", ", ".join("%s (%d)" % kv for kv in users.most_common(5)))
print("busiest hours   :", ", ".join("%s:00 (%d)" % kv for kv in hours.most_common(3)))
print("accepted sign-ins, and how many failures that address had made before it:")
for when, how, user, ip, before in accepted:
    flag = "  <-- look at this one" if before or how != "publickey" else ""
    print("  %s  %-9s %-7s from %-14s prior failures: %d%s" % (when, how, user, ip, before, flag))
```

**Predict.** Of a day's lines, will most be failures or successes? Which one line would you want to be woken for?

**Do (Bash).**

```bash
cd "$LAB" && mkdir authlab && cd authlab
python3 -I ../gen_authlog.py
wc -l auth.log
grep -c 'Failed password' auth.log
grep 'Failed password' auth.log | sed -E 's/.* from ([0-9.]+) port.*/\1/' | sort | uniq -c | sort -rn | head -4   # loudest sources
grep -o 'Invalid user [^ ]*' auth.log | sort | uniq -c | sort -rn | head -4                                       # names tried
grep 'Accepted' auth.log                                                                                           # the rare lines
python3 -I ../read_auth.py auth.log
```

**Do (PowerShell, est.).**

```powershell
Set-Location $LAB; New-Item -ItemType Directory authlab | Out-Null; Set-Location authlab
python ..\gen_authlog.py
(Get-Content auth.log).Count
(Select-String 'Failed password' auth.log).Count
Select-String 'Failed password' auth.log | % { ($_.Line -split ' from ')[1].Split(' ')[0] } | Group-Object | Sort-Object Count -Descending | Select-Object -First 4 Count, Name
Select-String 'Accepted' auth.log | % Line
python ..\read_auth.py auth.log
```

**Check.** From the 2026-10-22 run (the seed is fixed, so yours should match; a different Python version could change it):

```text
wrote auth.log with 1650 lines
564                                            # failed passwords
     65 203.0.113.66 ... 63 198.51.100.9 ...   # the loudest sources, 56 to 65 attempts each
     54 Invalid user postgres ...              # names tried, about 50 each
Oct 22 04:30:00 ... Accepted password for root from 203.0.113.66 port 40022 ssh2
Oct 22 08:02:00 ... Accepted publickey for opuser from 198.51.100.7 ...   (and two more like it)
failed passwords: 564 from 12 addresses
accepted sign-ins, and how many failures that address had made before it:
  04:30:00  password  root    from 203.0.113.66   prior failures: 11  <-- look at this one
  08:02:00  publickey opuser  from 198.51.100.7   prior failures: 0
```

So: 1,650 lines, 564 failures from twelve addresses, about fifty tries each at the same dozen names. All of it is noise; nobody was being targeted. Four lines are not noise: three key sign-ins from the operator's own address, and one `Accepted password for root` at 04:30 from an address that had already failed eleven times. That line means a server **accepted a password for root**, which a server on this project's design would not, and it is the one to be woken for. In a real log you would not have the answer printed next to it; you would have a rule (alert on `Accepted` after prior failures from the same address, or on any `Accepted password`) and a person to read the alert, which is what [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) and the [SIEM alert lesson](Deception-and-Honeypots-Alerts-in-the-SIEM.md) build. The answers to the predictions: most lines are failures; the one line is the accepted root password.

**Undo.** The cleanup below.

### Clean up

```bash
cd ~ && rm -rf -- "$LAB"
```

`$LAB` is the scratch folder from the setup. If you opened a new terminal, `$LAB` is empty: do not run the line; delete the folder by hand. In PowerShell: `Set-Location ~; Remove-Item -Recurse -Force $LAB` (est.). The folder holds only dummy values.

## Optional: your own Doppler account (free plan)

This path teaches the real thing the exercises imitated: a project, a config, a secret, a read-only token that expires, a program that reads the secret without a file, and the revoke that you prove. It uses **your own** Doppler account. It is optional; every idea above is in the free local exercises.

> **Status of this path: written from Doppler's documentation and the CLI's `--help` text, never run.** The output is not shown because it was never seen. Run it expecting to fix something. Do it in an account you made for learning, not one that holds real secrets.

### Cost and teardown (read first)

- **Cost.** Doppler's pricing page (read 2026-10-22) lists the Developer plan as "Free for 3 users" and shows "Start for Free"; its Team plan is listed at $21 a month per user with a 14-day trial. The exercise needs no more than the free plan, so **the cost is $0 as long as you do not start a trial or change plans**. Pricing and limits are Doppler's to change; read the page on the day. [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) does not price this and the project's cost gate does not see it, because it creates nothing at a cloud provider.
- **What it leaves behind.** A project, a config and a token in your Doppler workspace, and a local login on your machine. The teardown removes all of them.
- **Teardown (do this at the end; it is also listed here first so you know the way out).**

```bash
# 1. find the token's slug, then revoke it (this is irreversible and immediate, per Doppler's docs)
doppler configs tokens --project example-secrets-lab --config dev
doppler configs tokens revoke --slug TOKEN_SLUG --project example-secrets-lab --config dev
# 2. delete the project and everything in it
doppler projects delete example-secrets-lab --yes
# 3. remove the local token file and sign the CLI out
rm -f reader.token && doppler logout
```

### Steps

```bash
doppler login                                                    # opens your browser; signs the CLI in to your own account
doppler projects create example-secrets-lab                         # three default environments: dev, stg and prd (est.: slugs)
doppler secrets set DEMO_GREETING --project example-secrets-lab --config dev    # prompts for a value; type any harmless text
```

```bash
# a read-only token that deletes itself after one hour (read-only is the default; --max-age sets the expiry)
( umask 077; doppler configs tokens create lab-reader --project example-secrets-lab --config dev --max-age 1h --plain > reader.token )
ls -l reader.token                                               # mode -rw-------
# a program reads the secret from its environment, with no file and no value in the command line
DOPPLER_TOKEN="$(cat reader.token)" doppler run --no-fallback -- python3 -I -c 'import os; print("the secret has", len(os.environ["DEMO_GREETING"]), "characters")'
```

```bash
# revoke, then prove it is dead (--no-fallback so a cached copy cannot answer for the token)
doppler configs tokens --project example-secrets-lab --config dev
doppler configs tokens revoke --slug TOKEN_SLUG --project example-secrets-lab --config dev
DOPPLER_TOKEN="$(cat reader.token)" doppler run --no-fallback -- true; echo "exit: $?"
```

**Predict.** What will the last command do after the revoke: run `true`, or refuse? What would it have done **without** `--no-fallback` if you had run the secrets fetch earlier without that flag?

**Check (est.).** The first `doppler run` prints a character count and nothing else; the secret's value was never in your command line, a file or the output. After the revoke, the last command should fail with a non-zero exit and an error about an invalid token (est.; I did not see the wording). Without `--no-fallback`, Doppler's documentation says the CLI can keep serving the last fetched secrets from its encrypted fallback file even after a revoke, which is why the flag is in the test. Also look in the dashboard's activity log for the events (the free plan keeps three days, per the pricing page).

**PowerShell (est.).** Same commands; use `$env:DOPPLER_TOKEN = (Get-Content reader.token).Trim()` before `doppler run --no-fallback -- python -I -c "..."`, and `Remove-Item Env:DOPPLER_TOKEN` after. Create `reader.token` by redirecting the `--plain` output of the `tokens create` command to the file and then restricting it with `icacls` as in exercise 2.

> **Screenshot to take yourself:** the Access tab of your demo config.
> Capture: the service-token list showing the name `lab-reader`, read-only access and the expiry.
> Look for: that the token is read-only and has an expiry, before you revoke it.
> Redact: the token value (it is shown once, at creation, so never capture that dialog), your email and workspace name.

## Build, break, detect, evade, defend

The same loop as the [labs](Labs-Break-It-on-Purpose.md), on a secret.

- **Build.** The password manager with MFA and offline recovery codes; one Doppler config and one short-lived read-only token per asset; `.env` in `.gitignore` with an `.env.example`; a pre-commit scanner and a CI scan; a note of each expiry and its owner.
- **Break.** Plant a dummy token in a commit and delete it again (exercise 1). Force-add a `.env` past the ignore rule (exercise 2). Reason through what a stranger could do with a token that has write scope and no expiry, on paper, never on a real one.
- **Detect.** The history scan; the scanner's refusal at push time; the issuer's access log showing an address you do not know (exercise 4); the auth log's one rare line (exercise 5); the Doppler activity log.
- **Evade, in words.** How would a careless person, or an attacker with a foothold, get a secret past the net? Skip the local hook (`SKIP=gitleaks`, or committing with the hook not installed); mark the line with an allow comment; encode or split the value so a pattern does not match (the exercises showed a split value slipping past gitleaks and past the small scanner); put it in a place no scanner reads, such as a chat or a screenshot; use a value whose shape the scanner does not know. None of this is a recipe: the point is that **each is a reason the net is the last layer, not the first.** The attacker's own cheapest path is simply to read a public repository's history and a laptop's `.env`.
- **Defend.** Never type the value into a file in the first place; keep it in the manager and inject it at run time; short expiry; narrow scope; revoke first; scan all three layers; own your recovery path; keep a short list of who can touch the lab.

### Flip the board

You built the habit and probed it. Now take the other jobs.

**The reviewer.** A friend hands you this README excerpt and asks "is this safe to publish?" Find at least six problems without running anything.

```text
## Setup
1. Clone the repo and copy the sample: cp env.txt .env   (the real .env is in the repo for convenience, ask Sam for edits)
2. The deploy token is in the Slack channel pinned message; it never expires so you only set it up once.
3. The server reads /etc/app/.env (mode 644) which has DB_PASSWORD and DEPLOY_TOKEN for production.
4. CI: the build prints `env` at the top of the log so we can debug.
5. The same admin password is used on the server, the dashboard and the DB.
6. If a secret leaks, delete the file and push again.
7. Recovery codes are in the shared Google Doc "accounts".
8. Everyone on the team has the Doppler project owner role so nobody gets blocked.
```

<details>
<summary>What to find</summary>

1. A real `.env` committed "for convenience": history, forks and clones (and a gitignored file would have stopped the accident).
2. A token in chat: searchable, forwarded and backed up; and "never expires" means every leak since it was made still works.
3. A production `.env` that is world-readable (mode 644) and holds the real secrets, on a server. The rule is non-sensitive references only, and 0600 root for what must be a file.
4. CI prints the environment into a log many people can read.
5. One password reused for three systems: one leak is three.
6. The leak response is backwards: revoke and rotate first; deleting and pushing does nothing for a value someone already copied.
7. Recovery codes in a shared document, readable by everyone who has it, and probably by the people who left.
8. Everyone is an owner: no least privilege, so any one laptop is the whole workspace, and no per-asset config or token.
9. Smaller: no MFA stated, no expiry or rotation owner, no scanner, no `.env.example`.

</details>

**The responder.** It is 02:00 and a scanner emails you that a token appears in a public repository. Write, in order, the first six things you do. A good answer starts with revoking the token at the issuer **before** reading anything else, then rotates, then reads the issuer's log for the window since the commit, then cleans history, and says who else has to be told. Then say which step the issuer's log would have made impossible if the issuer keeps no log of refused attempts.

**The bot.** Imagine you run a scanner over everything newly pushed to public repositories. You target no one; you read what arrives and try what you find. How long does a new public token survive before someone like you tries it? This page has no figure (est.; "within minutes" is the common claim). Plan as if it is minutes, not days, and revoke accordingly.

## Checkpoint

- Say, in one sentence each, why a deleted file is still a leak, why the password manager comes before the secrets manager, and why a revoked token should be tested with `--no-fallback`.
- Why does `.env` stay on a local machine, and what may a server's `.env` hold?
- Which is the first step after a leak, and what do you check third?
- Your history scan finds a token that was removed two years ago. What do you do, in order?
- A scan of only your current files says clean. What have you not checked?
- Name two things a scanner will miss, and one thing only the issuer's log can tell you.
- Why does each edge service get its own Doppler config and token, and what is the open question about doing that on one droplet?
- What is your recovery path if you lose the password manager, and where is it written?

Answers are in the sections above.

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| A `.env` is in the commit anyway | It was added with `git add -f`, or it was tracked before `.gitignore` existed | `git ls-files .env`; if listed, `git rm --cached .env` and then rotate everything in it. |
| The scan says clean and a leak is reported anyway | You scanned the folder, not the history | `gitleaks git` or `scan_secrets.py history`, which read every commit. |
| The token was rotated and something still works | The old value was revoked nowhere, or a copy exists elsewhere | Present the old value to the service and read the answer; look for the copies (CI variables, an old `.env`, a container). |
| A revoked Doppler token still serves secrets | The CLI's encrypted fallback file | `doppler run --no-fallback`, per Doppler's own warning. |
| History rewritten, secret still scanned | Backup refs and the reflog still hold the old commits, or you scanned an old clone | Delete `refs/original`, expire the reflog, `git gc`; scan a fresh clone. |
| The first-boot pull fails with an expired-looking error | The short-lived token expired before the boot finished | Rebuild with a fresh token; the file is deleted even on failure by design. |
| The password manager is locked and you are not sure how to recover | No tested recovery path | Open the offline codes sheet; sign in on a second device; write the path down while you still can. |
| A `.env.example` carries a real value | Someone copied `.env` over the example | A CI check that the example has only placeholders; rotate the value. |
| Doppler's free plan refuses a new config | The per-environment config limit | Read the pricing page's limits on the day; remove an unused config, or fold assets deliberately (a trade-off, not a default). |

## Claims register

All read-only requests; retrieved **2026-10-22** unless a row says otherwise. "Observed" means I ran it that day. Where I could not read a thing I say so.

| Claim | Source | Status |
|---|---|---|
| The maintainer's rules for this page (four rules and the bot observation) | Issue 236 and his message of 2026-10-22, quoted above | His words; his observation about bots is not a measurement made by this page |
| Doppler: a project holds config and secrets for one service or application; three default environments (Development, Staging, Production) | [Create project](https://docs.doppler.com/docs/create-project) | Read |
| Doppler: a service token gives read-only access to a specific config; optional write access or expiration; a CLI or personal token should not be used in live environments | [Service tokens](https://docs.doppler.com/docs/service-tokens) | Read |
| Doppler: an ephemeral token is created by setting an expiration and deletes itself; CLI `--max-age`, the page's example is `1m`; revoking is irreversible and immediate; after a revoke the CLI can keep serving the last fetched secrets from the encrypted fallback file | [Service tokens](https://docs.doppler.com/docs/service-tokens) | Read; the smallest accepted lifetime and a single-use token: **not stated** |
| Doppler: `doppler run` creates an encrypted fallback file after each successful fetch; `--fallback-only` and a passphrase option exist; a fallback path you set should be in `.gitignore` | [Secret fallback files](https://docs.doppler.com/docs/automatic-fallbacks) | Read |
| Doppler CLI 3.77.0 flags: `configs tokens create --max-age --access read\|read/write --plain`, `configs tokens revoke --slug`, `projects delete --yes`, `run --no-fallback --preserve-env` | `doppler ... --help` on the author's machine | Observed (help text only; no command was run against an account) |
| Doppler: `doppler secrets download --format env > .env` carries the comment "Avoid storing secrets unencrypted whenever possible"; plain-text download recommended only with process substitution | [Accessing secrets](https://docs.doppler.com/docs/accessing-secrets) | Read |
| Doppler's pricing page: Developer "Free for 3 users" with service tokens; limits 50 service tokens, 10 projects, 4 environments, 10 configs per environment; 3 days of activity logs; Team $21 per user per month with a 14-day trial; automatic secret rotation and service accounts listed under Team | [Doppler pricing](https://www.doppler.com/pricing) | Read from flattened page text; the column for each limit is **est.**; the page can change |
| Doppler's account recovery process | none | **Not read** |
| GitHub push protection: for users, on by default, blocks pushes of secrets to public repositories; for repositories, needs GitHub Secret Protection and is disabled by default; by default anyone with write access can bypass it with a reason | [About push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection) | Read |
| GitHub secret scanning: scans the entire Git history on all branches; free and automatic for public repositories; "rotate the affected credential immediately"; removing a secret from history "is time-intensive and often unnecessary if you've already revoked the credential"; notifies partners who can revoke | [About secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning) | Read; which of these are enabled on this repository: **not checked** |
| GitHub: revoke or rotate first; after a rewrite the data may remain in clones, forks, cached views reachable by SHA and pull requests; `git-filter-repo` 2.47 or later for `--sensitive-data-removal`; side effects of rewriting history; Support helps only where rotating cannot mitigate | [Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) | Read; the force-push and Support steps were **not run** |
| GitHub: recovery codes are one-time codes; download and store securely; saving them with a password manager is recommended; configure two or more authentication methods | [Configuring 2FA recovery methods](https://docs.github.com/en/authentication/securing-your-account-with-two-factor-authentication-2fa/configuring-two-factor-authentication-recovery-methods) | Read |
| gitleaks: `git`, `dir` and `stdin` modes; pre-commit hook; `SKIP=gitleaks`; `gitleaks:allow`; `.gitleaksignore`; baseline; rule `entropy` setting (example 3.5); the README says it reads additions in the git history and that decoding defaults to 0 | [gitleaks README](https://github.com/gitleaks/gitleaks) (default branch) | Read; the decode default **differs from the 8.30.1 binary** I ran (see next row) |
| gitleaks 8.30.1 (published 2026-03-21): the linux_x64 tarball matched the checksums file; `--max-decode-depth` default printed as 5; found a `ghp_`-shape token 40 of 40 times, a random 40-character `DEPLOY_API_KEY` value 39 of 40 times, a base64-encoded token once, and missed a split token once and a hex token with an invented prefix once | [releases](https://github.com/gitleaks/gitleaks/releases), my runs | Observed once per case; small samples; whether releases are signed: **not checked** |
| The checksum proves integrity of the download, not trust in the release | reasoning: both files are from the same release page | Reasoning |
| `git-filter-repo` removes a path from all history; `git filter-branch` plus `refs/original` cleanup does the same with plain git | the project's README, my runs | Observed on a scratch repository |
| OWASP Secrets Management Cheat Sheet: centralize and audit; least privilege; rotate regularly, user credentials excluded per NIST; expire where possible; secure the primary secret of a secrets manager in a second place; downtime, backup, test restore, break-glass; incident response order revocation, rotation, deletion, logging; never bake secrets into container images with `ENV` or `ARG` | [OWASP cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html) | Read |
| NIST SP 800-63B-4: verifiers shall not require periodic password change and shall force a change on evidence of compromise; shall allow password managers and paste; password managers increase the chance of stronger passwords; no composition rules; at least 64 characters accepted | [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html) | Read; applies to services that verify passwords, not to machine tokens |
| CISA: any MFA is better than none; FIDO/WebAuthn is the phishing-resistant kind | [More than a Password](https://www.cisa.gov/MFA) | Read |
| Bitwarden: zero-knowledge, PBKDF2-SHA256 or Argon2id, no way to reset a master password | [White paper](https://bitwarden.com/help/bitwarden-security-white-paper/), [forgot master password](https://bitwarden.com/help/forgot-master-password/) | Read; vendor statements, not audited |
| 1Password: account password plus a 128-bit Secret Key, AES-GCM-256, Emergency Kit | [Security overview](https://support.1password.com/1password-security/), [Emergency Kit](https://support.1password.com/emergency-kit/) | Read; vendor statements, not audited |
| KeePassXC: Argon2 recommended for KDBX 4; the guide has sections on storing and backing up the database | [User guide](https://keepassxc.org/docs/KeePassXC_UserGuide) | Read (headings and the key-derivation section) |
| This project's Doppler design: one `prd` config and a 90-day read-only token for Spacelift; a hostboot config and a first-boot pull for telemetry droplets; the edge design allows one secret-shaped field in `user_data` | [Doppler and secrets](Doppler-and-Secrets.md), [stage 2 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/02-telemetry.md), [edge design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-19-edge-dmz-design.md), [runbook section 5a](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/spacelift-secrets.md) | Read in this repository; the edge and telemetry parts are not built or not applied |
| The project's CI runs a gitleaks scan over full history through a reusable workflow | [`ci.yml`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/.github/workflows/ci.yml) (the `security` job), the workflow's own header comments | Read |
| One Doppler config and one short-lived token per edge service | The maintainer's ruling of 2026-10-22 (issue 236) | A ruling, not built; its fit with the edge design's single `user_data` field is **open** |
| How quickly a new public token is found, and how many bots probe a new server | none | **No figure read.** The page makes no rate claim; the auth log is synthetic |
| The `/proc/PID/environ` and `ps e` behavior, file modes, `git check-ignore`, the leak drill output, the auth-log counts | my runs on Linux, 2026-10-22 | Observed once; macOS and Windows behavior **est.** |
| PowerShell commands, the gitleaks download on macOS and Windows, the Doppler own-account path | none | **Not run** |

## Where to next

[CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) shows how the project's gate keeps these habits honest on every change. If you want the long argument for the enterprise side of the table, [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md#secrets-vaults-rotation-and-certificates). If you want to try the detection half with decoys, [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md).
