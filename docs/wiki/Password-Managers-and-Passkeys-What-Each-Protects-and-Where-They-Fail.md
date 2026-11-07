# Password managers and passkeys: what each protects, and where they fail

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Password managers and passkeys

Previous: [Secrets from day one](Secrets-From-Day-One.md) / Next: [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md)
<!-- END GENERATED PAGE NAV top -->

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says (and the gap)](#what-the-wiki-already-says-and-the-gap)
- [How a vault works](#how-a-vault-works)
- [Hosted, self-hosted, offline](#hosted-self-hosted-offline)
- [Passkeys and FIDO2, in plain words](#passkeys-and-fido2-in-plain-words)
- [TOTP: the middle step](#totp-the-middle-step)
- [Recovery](#recovery)
- [Phishing resistance, in one table](#phishing-resistance-in-one-table)
- [What a manager does not protect](#what-a-manager-does-not-protect)
- [One setup, as a worked example](#one-setup-as-a-worked-example)
- [Free path: build, break and restore a KeePassXC vault](#free-path-build-break-and-restore-a-keepassxc-vault)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

A password manager is an encrypted file and a way to open it. Everything else (autofill, sync, sharing, the nice app) is built around that one fact, and so is every way it can go wrong. A passkey is a different animal: no secret you type, nothing a fake website can collect. This page takes both apart, side by side, and ends with a vault you build, break and restore yourself.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. Only the KeePassXC exercise was run; every vendor claim was read, not tested.** On **2026-11-07** I ran, on one Linux machine, KeePassXC 2.8.0 (the Flatpak build) through its command-line tool, `keepassxc-cli`: create a vault, add an entry, copy the file, overwrite part of it, try to open it, restore from the copy, try a wrong password, a truncated file and a vault with a key file. The output quoted in the exercise is what that run printed. I did not run the desktop windows, a browser extension, a hardware key, a passkey sign-in, or any hosted service (Proton Pass, Bitwarden): for those I read each vendor's own pages on 2026-11-07, and the [claims register](#claims-register) says which. Anything marked **est.** is my estimate, not something I checked.

> **Prerequisites.** [Secrets from day one](Secrets-From-Day-One.md) (read its step 1 first; this page does not repeat it) and [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) help. For the exercise: a computer where you may install KeePassXC and a terminal. About 90 minutes for reading and the exercise (est.). It costs nothing.

> **Where this runs, and the rule.** The exercise is local and throwaway: a vault of one fake entry, a passphrase you invent for the occasion and delete after. No real account, no real password and no cloud service is involved. Do not put a real credential in the practice vault, and do not reuse the practice passphrase anywhere.

## What you will be able to do

- Say what is in a vault file, what opens it, and what a thief holding only the file still has to do.
- Say what a breach of a hosted password manager exposes, and what it cannot, and why that depends on the design and not on the brand.
- Choose between hosted, self-hosted and offline, knowing what each one makes you responsible for.
- Explain a passkey and FIDO2 in plain words, and the difference between a synced passkey and a device-bound one.
- Place the three steps (password, TOTP code, passkey) in order, and say which resist phishing.
- Say what a password manager does not protect, starting with a compromised device.
- Create a KeePassXC vault, break it, restore it from a backup, and list what an attacker holding only the file needs.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Why use a manager, what goes in it, what stays out | [Secrets from day one, step 1](Secrets-From-Day-One.md#step-1-a-password-manager-from-the-first-day) | How the vault is built and what a breach hands over. |
| Master password length, MFA on the vault, recovery codes kept outside the vault | [The loop](Secrets-From-Day-One.md#the-loop-protecting-the-thing-that-protects-everything) | Not repeated here; this page starts where it stops. |
| Bitwarden, 1Password and KeePassXC named, none recommended | [Several tools, no recommendation](Secrets-From-Day-One.md#several-tools-no-recommendation) | A worked example of one setup, with the tradeoffs of each piece. |
| FIDO2/WebAuthn resists phishing through origin binding | [MFA, and why some MFA resists phishing](Enterprise-Identity-SSO-SAML-OIDC.md#mfa-and-why-some-mfa-resists-phishing) | What a passkey is, how synced and device-bound differ, and recovery. |
| What a KDF is | [Glossary: key derivation function](Glossary.md), [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#passwords-are-a-special-case) | How a vault uses one, and what it buys you after a theft. |

## How a vault works

A vault has three parts: a **key**, a **cipher** and a **file**.

1. You type a master password. It is weak raw material (short, guessable), so the program runs it through a **key derivation function (KDF)**, a deliberately slow calculation, to produce the real encryption key. The slowness is the point: an attacker guessing passwords has to pay that cost on every guess.
2. The key encrypts your entries with a standard cipher, AES-256 in the three tools below.
3. The result is stored as a file (or as a record on a server). Without the key the file is noise.

Two ideas to hold onto:

- **Zero-knowledge** is a claim about who holds the key. The vendor says it never sees the master password or the key, because the key is made on your device and the encryption happens there. Bitwarden's white paper puts it as "Bitwarden team members cannot see your passwords" and says it "never stores and cannot access your master password or your cryptographic keys" (read 2026-11-07). Proton says "all cryptographic operations, including key generation and data encryption, are performed locally on your device" (2023 post, read 2026-11-07). These are the vendors' own descriptions of their designs. They are not audits.
- **The cost of a guess is the whole defense after a theft.** Bitwarden's paper says new accounts stretch the master password with PBKDF2 at 600,000 iterations, and that you can switch to Argon2id. The KeePassXC guide says its newer file format, KDBX 4, can use Argon2, which "provides a better resistance against GPU/ASIC attacks" than the older AES-based KDF. On my test vault (below), the older kind was set to about 65 million rounds for a target of one second to open (the benchmark picked 62.5 million on one run and 65.2 million on the next). Those numbers are not comparable across algorithms, so do not rank tools by them.

### What a breach of the provider exposes

With a hosted manager the provider holds a copy of your vault, so the question is what a thief gets by taking the provider's data:

- **The encrypted vault.** Useless without your key, but the thief can keep it and try guesses at leisure. A long random-word master password makes that hopeless; a short one does not. This is why the master password matters more than the brand.
- **What the provider keeps in the clear.** Your account email, billing, sign-in records, probably some metadata. Which parts of an entry (the site address, the title) are encrypted differs by design. Proton's 2023 post says its design encrypts every field, "including usernames, web addresses, and all data contained in the encrypted notes", so Proton "prevents anyone, including Proton itself, from knowing which online services you subscribe to". I did not check what each other product leaves unencrypted. **est.**: ask that question of any manager you pick, because a list of the sites you use is useful to a phisher even without the passwords.
- **Not your master password.** In the designs above it is never sent as is. Bitwarden's paper says a derived "Master Password Hash" is what goes to the server, and that the server hashes it again.

What a provider breach does not change: a stolen vault is attacked offline against your master password. What it can change is the code the provider serves you: a web vault or extension is code the vendor ships, and a compromised vendor could ship bad code (est.). That is one reason open source, published audits and signed apps matter, and also why they are claims you read, not proof.

## Hosted, self-hosted, offline

| Kind | You get | You carry |
|---|---|---|
| **Hosted** (the vendor runs the server) | Sync across devices, a recovery path the vendor designs, sharing, no servers of your own. | Trust in one company's code and account system; an account that can be locked or priced differently later. |
| **Self-hosted** (you run the server) | The same apps, with the data on your machine. Bitwarden documents a single-container deployment ("Bitwarden lite", for personal use and home labs) and Linux, Windows and Kubernetes deployments (read 2026-11-07). | Every duty of an operator: patches, TLS, backups of the server, uptime. If your server is down, so is your sign-in. A small server is a bigger target than it feels like. |
| **Offline file** (no server at all) | A file you control. KeePassXC says its design is "cloud-free" and that no data is stored on remote servers. | Sync, backup and recovery are all yours. Lose the only copy, or the key, and it is gone. |

Self-hosting does not make the crypto better. It moves who can lose your data from the vendor to you, which is the right trade only if you will keep the server patched and backed up. The [Droplet hardening](Droplet-Hardening.md) and [Backups](Backups-Recovery-and-Patching.md) pages describe that work.

## Passkeys and FIDO2, in plain words

A password is a secret shared with the website. The website stores a check value of it, you send the secret on every sign-in, and anyone you send it to (a real site, a fake one) can use it.

A **passkey** drops the shared secret. When you register, your device makes a **key pair** (see [asymmetric keys](Hashing-Encryption-and-Keys.md#asymmetric-a-key-pair)) for that one site. The website keeps the **public key**. The **private key** never leaves your authenticator. To sign in, the site sends a random challenge, your device signs it after you unlock it (fingerprint, face, PIN), and the site checks the signature with the public key. The webauthn.guide introduction describes exactly this shape: "The private key is stored securely on the user's device; a public key and randomly generated credential ID is sent to the server" (read 2026-11-07).

Three results follow:

- **Nothing to steal from the website.** A leaked database of public keys is useless to an attacker.
- **Nothing to type, so nothing to phish.** The credential is **bound to the origin**, the website's address, and the browser will not offer it to another one. The page you already read says this under [MFA, and why some MFA resists phishing](Enterprise-Identity-SSO-SAML-OIDC.md#mfa-and-why-some-mfa-resists-phishing). NIST's definition, in SP 800-63B-4, is that phishing resistance means the protocol prevents "the disclosure of authentication secrets and valid authenticator outputs to an impostor verifier... without relying on the vigilance of the claimant" (read 2026-11-07). You do not have to spot the fake; the protocol does not hand it anything.
- **No reuse.** Every site gets its own key pair.

**FIDO2** is the family of standards: **WebAuthn** is the browser and website side (a W3C standard), and CTAP is how a browser talks to an external key. **Passkey** is the user-facing name for a WebAuthn credential that can be used to sign in without a password. A physical security key, a phone, a laptop's chip and a password manager can all hold passkeys.

### Synced versus device-bound

The W3C WebAuthn spec calls them **multi-device credentials** ("commonly referred to as synced passkeys") and **single-device credentials** ("commonly referred to as device-bound passkeys"), and says backup eligibility is decided when the credential is created and is "permanent" (read 2026-11-07).

| Question | Synced passkey | Device-bound passkey |
|---|---|---|
| Where the private key lives | On the device and in a sync service, copied encrypted between your devices. | Only in one device or key. |
| Lose the device | Your other devices still have it. | It is gone; you need a second registered key or another way in. |
| Who holds a copy | The sync provider (a platform account, or your password manager). Apple says iCloud Keychain is "end-to-end encrypted with strong cryptographic keys not known to Apple". Google says passkeys are "securely encrypted on-device before being synced". | Nobody but you. |
| Phishing resistance | Yes, the same origin binding. NIST's appendix says properly configured syncable authenticators achieve it. | Yes. |
| Highest assurance | NIST: "syncing violates the non-exportability requirements of AAL3". Fine for the second-highest level, not the top. | Meets the non-exportable requirement when the hardware is built for it. |

Which to use is a risk decision. Synced passkeys fix the problem that made hardware keys unpopular (what do I do when I lose it?) and trade some of the protection for it, since your account with the sync provider is now part of the chain. For a personal account that is usually the right trade (est.). For an administrator account, a device-bound key, with a second key kept in a drawer, is what the [Enterprise identity page](Enterprise-Identity-SSO-SAML-OIDC.md#mfa-and-why-some-mfa-resists-phishing) argues for.

Password managers now hold passkeys too: Bitwarden says passkeys saved in it "are synced between devices where you use Bitwarden"; Proton's passkey page says passkeys are available in all its plans; the KeePassXC guide has a passkeys chapter (all read 2026-11-07). That puts your passkeys under the same master password and the same recovery as your passwords, which is convenient and concentrates the risk (below).

## TOTP: the middle step

A **time-based one-time password (TOTP)** is the six-digit code that changes every 30 seconds. At setup the site shows a QR code that contains a shared secret (the **seed**); your app and the site both compute the code from the seed and the clock. Bitwarden's documentation describes them as "six-digit codes using SHA-1 that rotate every 30 seconds" (read 2026-11-07).

Where it sits, from weakest to strongest:

1. **Password only.** Stuffing, phishing and leaks beat it.
2. **Password plus TOTP.** An attacker needs the code as well, which stops stuffing and most leaked-password attacks. It does not stop a live phishing page: you type the code into the fake, and the fake passes it to the real site within the 30 seconds. NIST says plainly that "OTP authentication is not phishing-resistant", and that recovery codes (look-up secrets) are not either (SP 800-63B-4, read 2026-11-07).
3. **Passkey.** No code to relay.

Use TOTP wherever a passkey is not offered; it is far better than nothing. Two choices to make on purpose:

- **Where the seed lives.** Most managers can generate the codes for you (Bitwarden: "Generating TOTP codes is available with Premium or membership to a paid organization"; Proton's pricing page lists a built-in 2FA authenticator under its paid plan, not its free one; both read 2026-11-07). That is convenient and it puts both factors in one vault, so a stolen unlocked vault is both. A separate authenticator app keeps them apart, at the cost of one more thing to back up. Which side you take depends on what you are protecting; for an account that can reset others (your email), the separate place is the safer default (est.).
- **Back up the seed, not only the code.** The code changes; the seed is the thing a new phone needs. Sites that give you recovery codes at setup are giving you the way out; keep them on paper, as [step 1](Secrets-From-Day-One.md#the-loop-protecting-the-thing-that-protects-everything) says.

## Recovery

Every secret you cannot reset needs a way back that does not depend on itself.

- **Password manager:** hosted vendors differ. Bitwarden says it "has no way to access, retrieve, or reset your master password" (per the [Secrets page](Secrets-From-Day-One.md#several-tools-no-recommendation)); that is what zero-knowledge means for recovery, and it is why you set up a way back beforehand. With KeePassXC the recovery is a backup of the file plus whatever opens it (password, key file, hardware key).
- **Synced passkeys:** the sync service is the recovery. Lose every device and you recover through the account that syncs them, which is why that account needs its own MFA and its own recovery codes on paper.
- **Device-bound passkeys:** register at least two keys on every account that matters, and keep the second one somewhere else.
- **TOTP:** recovery codes, or the seed backed up.
- **Test it.** A recovery path you have not used is a hope. Open the vault from a clean second device, or from the backup file, before you need it. The exercise below does this for the offline case.

## Phishing resistance, in one table

| What you use | Fake sign-in page collects it | Can be replayed by the fake | Verdict |
|---|---|---|---|
| Password | Yes | Yes | Not resistant |
| Password plus TOTP | Both | Yes, within the 30 seconds | Not resistant |
| SMS or app push code | The code (or your tap) | Yes | Not resistant (tap fatigue is the other failure) |
| Passkey, synced or device-bound | Nothing to collect: the browser does not offer it for the wrong origin | No | Resistant |

A password manager helps a little with the first rows even without passkeys: autofill matches the stored address, so a lookalike domain does not get filled (est.), which is a prompt to stop and look. It is a prompt, not a guarantee, and you can still copy the password and paste it into the fake.

## What a manager does not protect

- **A compromised device.** If malware runs on the machine, it can read the screen, log keystrokes (your master password), read the clipboard, read the vault from memory while it is unlocked, or steal the browser session after you sign in. The vault's encryption protects it at rest; it cannot protect it from the place it is being used. This is the same limit the [Secrets page](Secrets-From-Day-One.md#the-loop-protecting-the-thing-that-protects-everything) ends on, and the same one the [Enterprise identity page](Enterprise-Identity-SSO-SAML-OIDC.md#mfa-and-why-some-mfa-resists-phishing) gives for a stolen session: phishing-resistant is not theft-proof.
- **A weak master password.** The cipher is AES-256 and the master password is `summer2024`. The KDF buys time; it does not buy a miracle.
- **The accounts around it.** The email account that can reset the vault account, the phone number, the sync account. These are the doors beside the vault door.
- **Your own copy of the secret.** A password pasted into a chat, a screenshot of a recovery code, a vault file synced to a service with a weak password.
- **Machines and programs.** A program should read a secrets manager, not your vault ([why](Secrets-From-Day-One.md#what-goes-in-it-and-what-does-not)).

Protecting the file and the device it lives on (full-disk encryption, an encrypted backup, a locked screen) belongs to the planned disk and file encryption lesson, issue #467 in this project's tracker. That page does not exist yet, so this line has no link.

## One setup, as a worked example

This is the maintainer's choice, given to me for this page on 2026-11-07. It is a worked example, not a ranking, and not a recommendation for your situation. His setup: **Proton Pass as primary, Bitwarden as secondary, KeePassXC as the fully offline option.** His reasons, in his words as passed to me: hosted and integrated, open source and self-hostable, and a fully offline file. Here is what each is good and bad at, from each vendor's own pages, read 2026-11-07.

### Proton Pass (primary)

Affiliate link: [Proton Pass](https://go.getproton.me/aff_c?offer_id=38&aff_id=8335). This is an affiliate link. The maintainer may earn a commission if you sign up through it. The lesson would read the same without it, and nothing here depends on your using it.

- **Good:** end-to-end encrypted, with all fields encrypted including web addresses (2023 post, above); the apps are described as open source and independently audited, with audit reports public (Proton Pass security page); a free plan with unlimited logins and devices, and passkeys in all plans (pricing page); it sits inside the same account as the rest of his Proton services (hosted and integrated).
- **Bad, or to watch:** hosted only, as far as the pages I read say; I found no self-hosting option. **est.** One company runs the account system, so its lock-out and recovery rules are yours. Per the pricing page, the built-in 2FA authenticator and vault sharing are on the paid plan. Its encryption description, by its own date, is from 2023; I did not find a newer one, so check the current security page. The user key is protected with a bcrypt hash of the account password (2023 post), a different design than the others, which makes a straight comparison of cost-per-guess impossible.

### Bitwarden (secondary)

- **Good:** open source (all products' source code is on GitHub per the white paper); AES-CBC 256 with HMAC, PBKDF2 at 600,000 iterations by default, Argon2id as an option; zero-knowledge per its paper; a documented self-hosting route, including the single-container Bitwarden lite; passkeys saved in it sync between your devices.
- **Bad, or to watch:** the default KDF is PBKDF2 until you change it, per the paper; changing to Argon2id is your job. Generating TOTP codes in the vault needs Premium or a paid organization. Self-hosting is an operator's job, and that includes keeping the server patched; the self-host page lists "Intermediate to advanced" skill for the Linux server routes. Hosted data lives in Microsoft Azure, US or EU, per its data-storage page.

### KeePassXC (offline)

- **Good:** a file you own, no account, no server; free and open source (GPL version 3 per the guide); the project says it has been awarded a Security Visa by the French agency ANSSI (its home page; I did not check the visa itself); supports a key file and a hardware key (YubiKey challenge-response) on top of the password; passkeys and TOTP are supported per the guide's own contents.
- **Bad, or to watch:** sync is yours to build (a copy on a USB stick, a sync tool, a folder). Backup is yours; the guide describes a backup-before-save option and an on-demand backup. Recovery is the file plus its key; there is no help desk. The tool I ran created a **KDBX 3.1** file with the older AES-based KDF by default (the exercise shows it), and the guide says Argon2 needs KDBX 4: check Database Settings when you create a real vault. **est.**: the desktop wizard defaults may differ from the command-line tool's; I did not run it.

None of the three is a safe choice by name. What makes any of them safe is a long master password, MFA on the account behind it, recovery you have tested, and a device that is not already compromised.

## Free path: build, break and restore a KeePassXC vault

You need KeePassXC 2.5 or newer (est.; I ran 2.8.0), a terminal, and about 20 minutes. Everything happens in one folder you delete at the end.

**What I ran.** The commands below, in this order, on 2026-11-07, KeePassXC 2.8.0 as a Flatpak on Linux, with `CLI` set to the Flatpak form. Output lines are what it printed, trimmed. I did not run the graphical version, so the screens are not described here.

### Setup

```bash
mkdir -p ~/pwlab && cd ~/pwlab
# Native package:
CLI=keepassxc-cli
# Flatpak build instead:
# CLI="flatpak run --command=keepassxc-cli org.keepassxc.KeePassXC"
PW='example-passphrase-for-the-lesson'   # invent your own throwaway phrase
```

Piping a passphrase on the command line puts it in your shell history. That is acceptable for a throwaway phrase and exactly the habit not to copy for a real one.

### 1. Create a vault and add one fake entry

```bash
printf '%s\n%s\n' "$PW" "$PW" | $CLI db-create -p -t 1000 vault.kdbx
printf '%s\n' "$PW" | $CLI add -u alice@example.com -g -L 24 vault.kdbx example.com
printf '%s\n' "$PW" | $CLI ls vault.kdbx
printf '%s\n' "$PW" | $CLI db-info vault.kdbx | head -5
```

What I saw: `Setting 65217392 rounds for key derivation function.`, then `example.com` listed, then `Cipher: AES 256-bit` and `KDF: AES (65217392 rounds)`. The file was 2,030 bytes with one entry. (I ran the whole script twice; the benchmark chose 62,500,000 rounds the first time, so your count will differ.)

### 2. Back it up, and prove the copy matches

```bash
cp vault.kdbx vault.kdbx.bak
sha256sum vault.kdbx vault.kdbx.bak
```

I saw the same hash on both lines. The copy is a backup only because it is a copy somewhere else; on the same disk it is a second file that dies with the first (see [Backups deep dive](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md#restore-testing)).

### 3. What does someone holding only the file see?

```bash
head -c 12 vault.kdbx | xxd
strings -n 4 vault.kdbx | grep -c -i -E 'example|alice'
```

I saw `03d9 a29a 67fb 4bb5 0100 0300`, a fixed signature and a version (the last four bytes read as KDBX 3.1, which matches what the program reported), and a count of **0** for the entry's site and user name. The site name and user name are in the encrypted part. One entry and one search is a small sample; it shows that these strings were not left in plain sight in this file, not that no metadata is anywhere.

### 4. Break it

```bash
SZ=$(stat -c %s vault.kdbx)
dd if=/dev/zero of=vault.kdbx bs=1 seek=$((SZ/2)) count=64 conv=notrunc
printf '%s\n' "$PW" | $CLI ls vault.kdbx
```

I saw `Error while reading the database: No root group`, exit status 1, with the correct passphrase. Sixty-four overwritten bytes in the middle and the whole vault is unreadable. An encrypted file does not degrade gracefully; one bad block can cost everything after it. That is why the backup exists.

### 5. Restore, and try the other failures

```bash
cp vault.kdbx.bak vault.kdbx
printf '%s\n' "$PW" | $CLI ls vault.kdbx                 # works again
printf '%s\n' 'wrong-guess' | $CLI ls vault.kdbx         # wrong password
head -c 200 vault.kdbx.bak > trunc.kdbx
printf '%s\n' "$PW" | $CLI ls trunc.kdbx                 # truncated file
```

I saw: `example.com` after the restore; `Invalid credentials were provided, please try again. If this reoccurs, then your database file may be corrupt.` for the wrong password; and `Invalid header data length` for the truncated file. Three different failures, three different messages: a wrong passphrase, damage inside the file, and a cut-off file.

### 6. Add a second factor to the file

```bash
printf '%s\n%s\n' "$PW" "$PW" | $CLI db-create -q -t 1000 -p --set-key-file k.key v2.kdbx
printf '%s\n' "$PW" | $CLI ls v2.kdbx                    # password alone
printf '%s\n' "$PW" | $CLI ls -k k.key v2.kdbx           # password and key file
$CLI ls -k k.key --no-password v2.kdbx                   # key file alone
```

I saw `Invalid credentials` for the password alone, a successful (empty) listing for password plus key file, and `Invalid credentials` for the key file alone. The two together open it; either one alone does not. A key file stored apart from the vault (a USB stick, a different machine) turns "steal the file" into "steal the file and the stick".

### 7. List what an attacker with only the vault file needs

Write your own list before you read mine. Mine, from steps 3 to 6 and the KDF discussion above:

1. **Every credential on the file**: the passphrase and, if you added them, the key file and the hardware key. In step 6 the password alone failed. Add them and the work is much larger.
2. **Time and hardware for guessing.** There is no server to rate-limit, so the thief can guess as fast as their machines allow, offline. The only brake is the KDF: on my machine the whole open command, including starting the Flatpak, took 1.2 and 1.4 seconds on the two runs, so a guess costs at most about that much on comparable hardware; an attacker with graphics cards and a cheaper path per guess is faster (est.).
3. **A guessable passphrase.** With a long random passphrase the guessing never ends; with `summer2024` it ends in minutes (est.).
4. **Nothing else.** No account, no device, no network. That is the strength of the offline file and its weakness: once copied, the file is out of your control forever, so you cannot revoke it. If the passphrase was weak, change every secret in it.
5. **What they do not need:** your computer. Which is why the planned disk and file encryption lesson matters: where the file sits decides how easy the first step is.

### Clean up

```bash
cd ~ && rm -r ~/pwlab
```

Check nothing else holds the vault open (`ls ~/pwlab` should fail), and that no real secret ever went into it.

### What I did not run

The desktop windows, KDBX 4 with Argon2 (the command-line tool I used offers no option for it), a hardware key, browser integration, TOTP in KeePassXC, a passkey, Proton Pass and Bitwarden. Treat everything about those as read, not tested.

## Checkpoint

Without looking back: say what the KDF does and why its slowness helps after a theft; say what a provider breach exposes and what it does not; name one cost each of hosted, self-hosted and offline; explain in two sentences why a passkey cannot be phished and a TOTP code can; say what a synced passkey trades for easy recovery; say what you would do if you lost your only phone; and name one thing a password manager does not protect.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "Zero-knowledge means unbreakable" | It means the vendor does not hold your key. A weak master password still falls to offline guessing. | Length of your master password; the KDF setting |
| "TOTP is phishing-proof" | A fake page can relay the code within 30 seconds. | NIST SP 800-63B-4: OTP "is not phishing-resistant" |
| "A passkey lives only on this phone" | A synced passkey is copied to the sync service. | Whether it is synced or device-bound |
| "My recovery codes are in the vault" | Then they are lost with the vault. | A paper copy, stored apart |
| "Self-hosted is more secure" | It is more yours. It is less secure if you do not patch and back it up. | Who updates the server, and when |
| "I can recover a lost master password from support" | Not in a zero-knowledge design. | The vendor's recovery page, before you need it |
| "A backup on the same disk is a backup" | It dies with the disk. | A copy on another device |
| "Passkeys make a compromised laptop safe" | Malware on the device uses the sign-in or steals the session. | Device health; see the Enterprise identity page |

## Claims register

Retrieved 2026-11-07 with read-only requests. "Read" means I read the page text; "Run" means I ran it. Pages that need JavaScript were not usable, which is noted where it matters.

| Claim | Source | Status |
|---|---|---|
| Bitwarden: zero-knowledge, end-to-end encryption, AES-CBC 256 with HMAC, PBKDF2 or Argon2id, 600,000 PBKDF2 iterations at account creation, option to move to Argon2id, master password hash sent to the server and hashed again, open source on GitHub | [Bitwarden security white paper](https://bitwarden.com/help/bitwarden-security-white-paper/) | Read; vendor's own description, not an audit |
| Bitwarden data on Azure in the US or EU; servers store only encrypted data | [Bitwarden data storage](https://bitwarden.com/help/data-storage/) | Read |
| Bitwarden self-hosting routes, including Bitwarden lite as one container, skill levels | [Self-host Bitwarden](https://bitwarden.com/help/self-host-bitwarden/) | Read |
| Bitwarden TOTP generation needs Premium or a paid organization; six-digit SHA-1 codes every 30 seconds | [Bitwarden integrated authenticator](https://bitwarden.com/help/authenticator-keys/) | Read |
| Bitwarden passkeys saved in it sync between devices where Bitwarden is used | [Bitwarden: store passkeys](https://bitwarden.com/help/storing-passkeys/) | Read |
| Proton Pass: end-to-end encryption, all fields encrypted including web addresses, local cryptographic operations, bcrypt-protected user key, AES-256-GCM | [The Proton Pass security model](https://proton.me/blog/proton-pass-security-model) (published 2023-04-20) | Read; the post is old and may not describe the current design |
| Proton Pass: apps open source, independent audits with public reports | [Proton Pass security page](https://proton.me/pass/security) | Read; vendor's own claim |
| Proton Pass: free plan with unlimited logins and devices; passkeys on all plans; built-in 2FA authenticator and vault sharing on the paid plan | [Proton Pass pricing](https://proton.me/pass/pricing), [Proton Pass passkeys](https://proton.me/pass/passkeys) | Read; plans change |
| Proton Pass has no self-hosted edition | the pages above do not mention one | **est.**: absence in what I read, not a statement from Proton |
| KeePassXC: free and open source, "cloud-free", ANSSI Security Visa (its own claim) | [keepassxc.org](https://keepassxc.org/) | Read; the visa not checked |
| KeePassXC: KDBX 3.1 supports AES-KDF only, Argon2 needs KDBX 4; key file and YubiKey challenge-response; backup before save; passkeys chapter; GPL version 3 | [KeePassXC user guide](https://keepassxc.org/docs/KeePassXC_UserGuide) | Read |
| KeePassXC 2.8.0 command-line tool created a KDBX 3.1, AES-KDF vault; a corrupted file gave "No root group"; a wrong password gave "Invalid credentials"; a vault with a key file refused the password alone | the exercise above | Run, 2026-11-07, one machine |
| Passkey = private key stays on the authenticator, public key to the server | [webauthn.guide](https://webauthn.guide/) | Read |
| Multi-device ("synced") and single-device ("device-bound") credentials; backup eligibility is permanent | [W3C WebAuthn Level 3](https://www.w3.org/TR/webauthn-3/) | Read |
| Phishing resistance defined; "OTP authentication is not phishing-resistant"; look-up secrets are not phishing-resistant | [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html) | Read |
| Syncable authenticators: phishing resistance achieved when properly configured; syncing violates AAL3 non-exportability | [NIST SP 800-63B-4, appendix on syncable authenticators](https://pages.nist.gov/800-63-4/sp800-63b/syncable/) | Read |
| iCloud Keychain end-to-end encrypted, passkeys sync through it | [Apple Support: About the security of passkeys](https://support.apple.com/en-us/102195) | Read |
| Google: passkeys encrypted on-device before sync | [Google passkeys developer page](https://developers.google.com/identity/passkeys) | Read |
| A hosted vendor could ship bad code to its web client or extension | reasoning, not a source | **est.** |
| Autofill that matches the stored address will not fill a lookalike domain | reasoning from how autofill is described, not tested | **est.** |
| Per-guess cost on an attacker's hardware is lower than on mine | reasoning | **est.** |

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Password managers and passkeys

Previous: [Secrets from day one](Secrets-From-Day-One.md) / Next: [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md)

In this track: [Track 1: Foundations](Contents.md#track-1-foundations), 34 pages

- OS and Linux, git and the terminal: [Git from zero](Git-From-Zero.md) / [The terminal and your first script](Terminal-and-Your-First-Script.md) / [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) / [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) / [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md) / [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md) / [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) / [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) / [Kubernetes for beginners](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md) / [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) / [Cron, systemd timers and init scripts versus systemd](Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd.md)
- Networking: [How a web request works](How-a-Web-Request-Works.md) / [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) / [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) / [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) / [IPv6 adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md)
- Identity and secrets: [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) / [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) / [Secrets from day one](Secrets-From-Day-One.md) / **Password managers and passkeys** / [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md)
- Infrastructure as code: [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md) / [OpenTofu from zero](OpenTofu-From-Zero.md) / [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) / [Ansible: configuration management versus provisioning](Ansible-Configuration-Management-Versus-Provisioning.md) / [Native IaC versus open standards](Native-IaC-vs-Open-Standards-CloudFormation-ARM-Bicep-and-OpenTofu.md) / [Spacelift from zero](Spacelift-From-Zero.md) / [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md) / [Environments and promotion](Environments-and-Promotion-Dev-Staging-Production.md)
- Web hosting: [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md) / [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) / [Static against dynamic: Hugo, WordPress and recon](Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon.md) / [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md) / [Autoscaling and elasticity](Autoscaling-and-Elasticity-Scale-Out-Targets-Cooldowns-and-Cost-Caps.md)

Related pages:

- [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)
- [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md)
- [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md)
- [OpenTofu from zero](OpenTofu-From-Zero.md)
<!-- END GENERATED PAGE NAV bottom -->
