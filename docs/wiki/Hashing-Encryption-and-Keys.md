# Hashing, encryption and keys: what each one is for

Side page to the start-from-zero pages. Read it before [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) if "hashed", "encrypted", "signed" and "key" all sound like the same thing, or at any point you meet them and want them told apart. Next: [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: Bash commands run on Linux on 2026-10-21; PowerShell and macOS commands not run; recommendations checked against the sources in the claims register.** I ran every Bash command below on a Linux machine with OpenSSL 3.5 and OpenSSH 10.3 and pasted what the tools printed (random values aside). I could not run PowerShell, macOS or the optional `age` tool for this page, so those lines are written from the tools' documentation and marked **not run**. Each algorithm recommendation names the page it came from and the date I read it; anything I could not read is marked **est.** (estimate) and is a guess to check. Trust what your terminal prints over what this page says. Cost: $0. Nothing here touches a cloud account, and the project's real spending lives on the [cost page](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md).

> **Prerequisites.** You can open a terminal and type a command ([Git from zero](Git-From-Zero.md#what-a-terminal-is) shows how). Core step 4 helps but is not required: this page is the long version of its [key pair section](Identity-Secrets-and-Zero-Trust-Basics.md#how-keys-work-without-the-math). About 75 minutes for the reading and the free exercises (est.).

## What you will be able to do

- Say in one sentence what encoding, hashing, encryption and signing each give you, and what each one does not.
- Explain why a file's hash changes when one byte changes, and why a git commit ID and a pinned action hash detect tampering.
- Explain why a password is stored as a salted slow hash and never as a plain SHA hash or as encrypted text.
- Explain symmetric and asymmetric encryption, a key pair, a digital signature, an SSH key and a TLS certificate in plain words.
- Hash, sign, verify, encrypt and decrypt a file with throwaway keys, break each one on purpose and read the failure.
- Say why "encrypted" does not mean "secure", and name the beginner mistakes that make it false.

## The four things beginners mix up

Four different tools get called "encryption" in casual speech. They answer four different questions. Most security mistakes in this area are using the right word for the wrong tool.

| Tool | The question it answers | Needs a secret? | Reversible? | Example | Common mistake |
|---|---|---|---|---|---|
| **Encoding** | How do I write this data in a form that another system can carry or read? | No | Yes, by anyone | base64, URL encoding, hex | Calling base64 "encrypted" |
| **Hashing** | Is this the same data as before? (a fingerprint) | No (a plain hash), or a key for an HMAC | No: one way | SHA-256 of a file | Using a fast hash to store passwords |
| **Encryption** | Can only the holder of the key read this? (secrecy) | Yes: a key | Yes, with the key | AES, ChaCha20 | Thinking it also proves nobody changed it |
| **Signing** | Who made this, and was it changed? (authenticity and integrity) | Yes: a private key to sign, a public key to check | Not applicable: nothing is hidden | An SSH or Ed25519 signature | Signing proves identity only if you trust whose public key you hold |

Two more words to keep apart. **Authentication** and **authorization** ([Identity basics](Identity-Secrets-and-Zero-Trust-Basics.md#authentication-and-authorization-are-two-different-questions)) are about who you are and what you may do; the tools above are the machinery underneath them.

**Predict.** A website says "your password is encoded with base64". Is that good, bad or meaningless? (Answer: bad. Anyone can reverse base64 with no key; see Exercise 6 on the [APIs and tokens page](APIs-and-Tokens-From-Zero.md#exercise-6-build-and-decode-a-fake-jwt-locally) and the section below on mistakes.)

## Hashing: a fingerprint, not a lock

A **hash function** takes any amount of data and returns a short fixed-size number, the **hash** (also called a digest). SHA-256 always returns 256 bits, written as 64 hexadecimal characters, whether you give it one letter or a ten-gigabyte file. A good one has these properties:

- **Same input, same output.** Always.
- **A tiny change gives a completely different output.** Change one character and the hash looks unrelated, not "a little different".
- **One way.** From the hash you cannot work back to the input. There is nothing to "decrypt": the hash holds less information than the data, so the data is not in it.
- **Collision resistant.** It should be impractical to find two different inputs with the same hash. When someone finds a way, the function is "broken" for any use that relies on that.

One-way does not mean unguessable. If the input is small or predictable (a short password, a four-digit PIN), an attacker does not reverse the hash: they hash guesses until one matches. That single fact explains the next two sections.

### What hashes are for

- **Integrity.** Download a file, hash it, compare with the hash the publisher posted. A mismatch means the file changed on the way, by accident or by an attacker. This only works if the hash itself came from somewhere you trust, because an attacker who can change the file can often change the hash next to it. That gap is what signatures close.
- **Finding the same data twice.** Backup and deduplication tools identify identical files by hash.
- **Commit IDs.** Git names each commit by a hash of its content, its parent's ID and its message. Change an old commit and its ID changes, and so does every ID after it. That is why a history can be checked for tampering by comparing the newest ID. Git has used SHA-1 for this and has a documented plan to move to a stronger function; see the claims register.
- **Pinned dependencies.** A GitHub Actions `uses:` line pinned to a full commit hash cannot be silently pointed at different code, because different code would have a different hash. The [Glossary](Glossary.md) calls this SHA pinning, and [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md#github-actions-and-the-supply-chain-problem) explains why it matters.
- **Part of a signature.** A signature is usually made over a hash of the data, because hashing first is faster than signing a whole file.

### Which hash to use

Use **SHA-256** (or another member of the SHA-2 or SHA-3 family) for new work. Avoid **MD5** and **SHA-1** where an attacker could benefit from a collision: NIST deprecated SHA-1 in 2011, disallowed it for digital signatures at the end of 2013, and published a plan in December 2022 to move away from its remaining limited uses; RFC 6151 updates the security considerations for MD5. MD5 is still fine as a quick checksum against accidental corruption, but then so is any other hash, so there is no reason to choose it.

**HMAC** is a hash mixed with a secret key, so only someone with the key can produce or check the result. Use it, not a home-made `hash(secret + message)`, when two parties share a key and want to prove a message was not changed. (The home-made version has a known weakness for some hash functions called a length-extension attack; the HMAC construction exists to avoid it. In words only here.)

## Passwords are a special case

A website must check your password without being able to read it. So it stores a hash of it and hashes what you type next time. Three details decide whether that is safe, because the attacker's likely position is "I stole the database and can try guesses at my leisure".

- **Never a raw fast hash.** SHA-256 is built to be fast, so an attacker with a graphics card tests billions of guesses a second. OWASP says plainly that fast algorithms such as SHA-256 are not suitable for password storage.
- **A salt.** A **salt** is a random value, unique per password, stored next to the hash and mixed in before hashing. Without it, two users with the same password have the same hash, one precomputed table of common passwords cracks the whole database at once, and anyone can see who shares a password. With it, every hash has to be attacked separately. A salt is not secret and does not need to be.
- **A slow, memory-hard hash.** A password-hashing function is made deliberately slow and memory-hungry, so each guess costs the attacker real time and RAM. OWASP's current first choice is **Argon2id**, with **scrypt** if Argon2id is unavailable, and bcrypt only for legacy systems; the claims register has the numbers I read. In practice you call your language's library for one of these and never write the loop yourself.

Not encryption, either. If passwords are stored encrypted, whoever steals the key (which sits next to the data far too often) gets every password at once. OWASP's guidance is to hash passwords, not encrypt them.

A **pepper** is an extra secret, shared across all passwords and kept outside the database (in a secrets manager, which is what [Doppler](Doppler-and-Secrets.md) is for). OWASP describes it as defense in depth on top of salting, not a replacement.

## Encryption: keeping it secret

**Encryption** scrambles data with a **key** so that only someone with the right key can unscramble it. The scrambling method (the **cipher**) is public on purpose: serious ciphers survive years of strangers trying to break them, and a secret method nobody has tested is a worse bet. Only the key is secret. (This idea is old; it is usually called Kerckhoffs's principle. I did not read a source for it; est.)

### Symmetric: one key for both

**Symmetric** encryption uses the same key to lock and unlock. It is fast and is what encrypts the actual data: your disk, a backup, a file, the bulk of a web connection. Common ones are **AES** and **ChaCha20**. The hard part is not the math: both sides need the same key, and you must get it to them without anyone else seeing it.

### Asymmetric: a key pair

**Asymmetric** encryption uses a **key pair**: two keys that are mathematically linked. What one locks, only the other unlocks. You publish one (the **public key**) and guard the other (the **private key**).

**The lock-and-mailbox picture.** Imagine a mailbox with a slot. Anyone can drop a letter through the slot (that is the public key: everybody has it, and it only lets them put things in). Only the owner has the key to the box (the private key), so only the owner can take letters out. You never had to meet the owner or share a secret first. That is the trick: it solves the key-delivery problem.

**The real thing.** Asymmetric operations are slow and handle only small amounts of data, so real systems combine both (a "hybrid" design). In the key-wrapping form, a random symmetric key encrypts the data and the recipient's public key encrypts that small symmetric key, so only the private key holder can recover it. Email and file tools in the PGP style work this way (`age` encrypts to a recipient's public key too; its internals I did not read, est.), and so did older TLS versions that used RSA key exchange. Modern TLS 1.3 does not wrap a key with the certificate's public key: it derives fresh traffic keys with an ephemeral Diffie-Hellman exchange (next section) and uses the certificate's key only to sign, which authenticates the handshake. Exercise 5 does the key-wrapping building block by hand.

The picture has a limit. Encryption and signing are separate operations, and you cannot assume one key pair does both. Modern designs use separate key types for each job: Ed25519 for signatures, X25519 for key agreement. RSA is the well-known case where one key pair supports both operations (though good practice is still to use separate keys for separate purposes). The next section covers signatures.

### Key exchange in one paragraph

Two strangers who want to talk privately over a public line need a shared secret without sending it. **Diffie-Hellman key exchange** does this: each side combines its own private number with the other's public number and, by the math, both arrive at the same shared secret while an eavesdropper who saw everything cannot. Modern TLS and SSH use such an exchange (with fresh numbers each session, so recorded traffic cannot be unlocked later by stealing a long-term key) to agree a symmetric key, and then encrypt the connection with it. The long-term keys and certificates are used to prove who is on the other end, which is the signing job below. (Protocol detail is out of scope here; I did not read the TLS specification for this page. RFC 8446 describes TLS 1.3; est.)

## Digital signatures: proof of who and what

A **digital signature** uses a signing key pair: you make the signature with your **private** key over some data, and anyone can check it with your **public** key. Three things follow if the check passes:

- **Authenticity.** Someone holding the private key made it.
- **Integrity.** The data has not changed since. One flipped byte and the check fails.
- **Non-repudiation, weakly.** The signer cannot easily claim it was not them, unless they can claim the key was stolen.

A signature does not hide the data, and it proves only that the key signed. Whether that key belongs to the person you think is a separate question that signing alone cannot answer. You answer it by getting the public key from a source you trust (a repository's `allowed_signers` file, a certificate authority, a colleague in person).

This is the machinery in [Identity basics: how keys work](Identity-Secrets-and-Zero-Trust-Basics.md#how-keys-work-without-the-math), where an SSH client signs a connection-specific piece of data to prove it holds the private key. It is also what is inside a signed JWT: the issuer signs the header and the claims, and a receiver verifies the signature without calling the issuer. The format is covered on [APIs and tokens](APIs-and-Tokens-From-Zero.md#what-is-inside-a-jwt-and-why-base64-is-not-encryption); this page does not repeat it. And git can sign commits with an SSH key (`gpg.format ssh`), so a reviewer can tell your commit from one with your name forged on it.

## Key pairs in the wild: SSH keys and TLS certificates

**An SSH key.** You make a pair with `ssh-keygen`. You put the public half on the server (in `authorized_keys`) or on GitHub; the private half stays on your machine. On connection, your client signs data tied to that session, and the server checks it with the public half. No password crosses the network, which is why this project's droplets accept keys only. The OpenSSH manual says `ssh-keygen` makes an Ed25519 key when you give it no type, which is why this project's guidance is `ssh-keygen -t ed25519`. See also [Linux for enterprise beginners: SSH keys](Linux-for-Enterprise-Beginners.md#ssh-keys-not-passwords) and [Git from zero: HTTPS or SSH](Git-From-Zero.md#https-or-ssh-and-why-start-with-gh).

**The host fingerprint prompt.** The first time you connect to a server, SSH shows its **fingerprint** (a hash of the server's public key) and asks whether to trust it. This is the same problem in reverse: how do you know the public key you were handed belongs to the server you meant? SSH does not know either. It asks you, then remembers the answer in `~/.ssh/known_hosts` and warns loudly if the key later changes. If you have another trusted route (the cloud console, a colleague), compare the fingerprint with it, and treat an unexpected change as a finding, not an annoyance. You can print a fingerprint yourself with `ssh-keygen -lf id_ed25519.pub` (use your own public key file name) (Exercise 3).

**A TLS certificate.** The padlock on a website works on the same idea. A **certificate** is a small file saying "this public key belongs to this name", and it is **signed** by a **certificate authority** (CA) that your browser or operating system already trusts. The browser checks the signature chain, checks the name matches the site and that the certificate has not expired, and then checks a signature made during the handshake, which proves the server holds the matching private key. The traffic keys themselves come from the key exchange, not from the certificate. The cryptography is the signing you already know; the hard part, as always, is who you trust to vouch for a key.

## Keeping keys: storage, passphrases and hardware keys

Cryptography moves your problem from "protect the data" to "protect the key". So:

- **A private key is a secret.** Treat it like a password that cannot be changed by phoning someone. Do not email it, paste it in chat or a ticket, copy it between machines casually or put it in a git repository.
- **Give it a passphrase.** A **passphrase** encrypts the private key file on disk, so a stolen laptop or a copied file is not a stolen identity. The project's rule is already on the identity page: one key per device you type on, protected with a passphrase.
- **Permissions matter.** SSH refuses a private key that others can read. `chmod 600` is the mode ([Linux for enterprise beginners: permissions](Linux-for-Enterprise-Beginners.md#file-permissions-and-ownership)).
- **Keep it in the right place.** A secrets manager for machine keys and tokens ([Doppler and secrets](Doppler-and-Secrets.md)); a password manager for yours. Neither belongs in a repository.
- **Have a way to replace it.** Know where each public key is installed, so you can remove it everywhere when the private key is lost.

**Hardware keys (YubiKey and similar).** A hardware security key holds the private key inside a small device that signs on request and never lets the key out. Malware on your computer can ask it to sign while it is plugged in, but cannot copy it, and for a login with FIDO2 or WebAuthn the key signs only for the website address it was registered with (it is origin-bound), which is why that kind of login resists phishing in a way a six-digit code does not. That protection is specific to FIDO2 and WebAuthn: an SSH key on a hardware token, a smart-card (PIV) login or a one-time-code (OTP) button does not check the website, so it keeps the private key safe from theft but does not by itself stop phishing. This project's guidance is in [Build it from zero, step 0](Build-It-From-Zero-Accounts-to-Stage-1.md#step-0-make-a-mistake-impossible-to-be-expensive): buy at least two, register both on every account that allows it, keep one somewhere other than your keyring, and put the recovery codes in your password manager, because a single key you lose is a lockout you built yourself. OpenSSH also supports hardware-backed keys (`ed25519-sk` appears among the key types in its manual). One catch from the `age` README: SSH keys held on a YubiKey cannot be used to decrypt files; they can sign and authenticate.

## "Encrypted" is not "secure"

Saying "it's encrypted" ends too many conversations. Questions to ask next:

- **Where is the key?** Data encrypted with a key stored in the same place is a locked door with the key in the lock. Key management (who can read the key, where it is stored, how it is rotated and revoked) is where most real failures sit, not in the cipher.
- **Encrypted in transit, at rest, or both?** A database encrypted on disk is plaintext to anyone who can query it. A TLS connection protects data on the wire and nothing about what the server does with it afterward.
- **Is it also authenticated?** Plain encryption hides data but may not notice tampering. Exercise 4 shows a modified ciphertext decrypting without any error. Use modes and tools that authenticate (AES-GCM and ChaCha20-Poly1305 do; `age` does), and verify before you trust the output.
- **Is the nonce used once?** Many modes need a **nonce** ("number used once") with each message. Reusing a nonce with the same key can destroy the secrecy and, in some modes, expose the key's authentication secret. NIST SP 800-38D defines AES-GCM; I read its listing page but not the requirement text, so the nonce rule is stated from general knowledge (est.). Let the library choose nonces; never invent your own.
- **Who else holds the key?** A cloud provider's "managed keys" mean the provider can decrypt. That may be fine; it is a decision, not a default.

## Beginner mistakes, and what to do instead

| Mistake | Why it fails | Do this instead |
|---|---|---|
| **base64 as encryption** | Encoding, not secrecy: anyone reverses it with no key | Encrypt with a real tool and a key; keep secrets out of tokens and URLs |
| **Rolling your own cryptography** | Home-made schemes fail in ways their authors cannot see | Use a well-reviewed library or tool (`age`, TLS, OpenSSH, libsodium) and its defaults |
| **Committing a private key** | Git keeps history; bots scan public repositories within minutes | Keep keys outside repositories; if one leaks, replace it first, clean up after (see Exercise 7) |
| **MD5 or SHA-1 for security** | Collision attacks are practical | SHA-256 or stronger |
| **Fast hash for passwords** | Billions of guesses a second | Argon2id or scrypt, with a per-password salt |
| **Same key everywhere** | One theft opens everything | One key per device or purpose |
| **No passphrase on a laptop key** | A stolen disk is a stolen identity | A passphrase, plus disk encryption |
| **Trusting a hash that arrived with the file** | An attacker who changes the file changes the hash | Get the hash from a different trusted channel, or verify a signature |
| **Ignoring the host-key warning** | That prompt is the only check SSH has | Treat a changed key as a finding |

## Hands-on, free path: everything local

Everything below runs on your own machine with throwaway files and keys. **Nothing is sent anywhere, and no real password or key is used.** Work in a scratch folder and delete it at the end. **Do not run any of this inside a clone of this repository.**

Tools: `sha256sum` (Linux), `shasum -a 256` (macOS), `Get-FileHash` (PowerShell), `python3`, `openssl` and `ssh-keygen`. OpenSSL and the OpenSSH client are on most Linux and macOS machines; I ran the commands with OpenSSL 3.5 and OpenSSH 10.3, and `ssh-keygen -Y` needs a reasonably recent OpenSSH (it was added in OpenSSH 8.0, est.). Windows 10 and later offers the OpenSSH client as an optional feature (est.; check Microsoft's page) and does not ship `openssl` by default. For the encryption exercise on Windows, or anywhere `openssl` is missing, install `age` from [its install page](https://github.com/FiloSottile/age) (it is in the Debian, Ubuntu and Homebrew package lists per its README: `apt install age`, `brew install age`). `age` was **not installed on my machine and not run** for this page.

### Setup (Bash, once)

```bash
LAB="$(mktemp -d)" && cd "$LAB"   # a fresh scratch folder, remembered in $LAB
printf 'pay Alice 100 dollars\n' > note.txt
```

PowerShell (**not run**):

```powershell
$d = Join-Path ([IO.Path]::GetTempPath()) "f4lab"
New-Item -ItemType Directory -Path $d | Out-Null
Set-Location $d
[IO.File]::WriteAllText("$d\note.txt", "pay Alice 100 dollars`n")
```

### Exercise 1: hash a file, change one byte

**Predict.** If you change `100` to `900`, will the hash change a little or completely?

**Do (Bash).**

```bash
sha256sum note.txt                     # Linux
shasum -a 256 note.txt                 # macOS; also works on most Linux
sha256sum note.txt > note.sha256       # save it
sed 's/100/900/' note.txt > note2.txt  # a one-character change
sha256sum note2.txt
```

**Do (PowerShell, not run).**

```powershell
Get-FileHash note.txt -Algorithm SHA256
[IO.File]::WriteAllText("$d\note2.txt", "pay Alice 900 dollars`n")
Get-FileHash note2.txt -Algorithm SHA256
```

**Check.** For the original file the hash starts with `cbcc2a3b` (PowerShell prints it in capital letters; the value is the same). `note2.txt` gives a hash starting `c48f4ce3`: no resemblance, from one character. The hash is 64 hex characters either way.

**Undo.** Nothing to undo; the files stay in your scratch folder.

### Exercise 2: detect tampering by hash mismatch

**Predict.** If someone swaps the file after you saved its hash, what happens when you check?

**Do.**

```bash
sha256sum -c note.sha256               # the saved hash against the real file
cp note2.txt note.txt                  # the "attacker" replaces the file
sha256sum -c note.sha256; echo "exit=$?"
printf 'pay Alice 100 dollars\n' > note.txt   # put the original back
```

PowerShell (not run):

```powershell
$saved = (Get-FileHash note.txt -Algorithm SHA256).Hash          # save the original hash
(Get-FileHash note.txt -Algorithm SHA256).Hash -eq $saved        # True
Copy-Item note2.txt note.txt -Force                              # the "attacker" replaces the file
(Get-FileHash note.txt -Algorithm SHA256).Hash -eq $saved        # False
[IO.File]::WriteAllText("$d\note.txt", "pay Alice 100 dollars`n")  # put the original back
(Get-FileHash note.txt -Algorithm SHA256).Hash -eq $saved        # True again
```

**Check.** The first check prints `note.txt: OK`. The second prints `note.txt: FAILED`, a warning that one computed checksum did not match, and `exit=1`. That nonzero exit code is what a script or a pipeline uses to stop. This is the whole idea behind a pinned dependency.

**Undo.** The last line (in either shell) restores the file.

### Exercise 3: a throwaway key pair, a signature, and a tampered file

**Predict.** A hash alone could be swapped by whoever swaps the file. What does a signature add?

**Do.** The flags below are from the OpenSSH manual page for `ssh-keygen` (read 2026-10-21): `-Y sign -f key_file -n namespace file` signs and writes `file.sig`; `-Y verify -f allowed_signers_file -I signer_identity -n namespace -s signature_file` reads the signed data on standard input.

```bash
ssh-keygen -q -t ed25519 -N '' -C 'demo-throwaway' -f demo_key
ssh-keygen -lf demo_key.pub            # the fingerprint: SHA256:..., ending (ED25519)
ssh-keygen -Y sign -f demo_key -n file note.txt   # writes note.txt.sig
# a verifier needs a list of who is trusted: "name key-type key"
printf 'demo-signer %s\n' "$(cut -d' ' -f1,2 demo_key.pub)" > allowed_signers
ssh-keygen -Y verify -f allowed_signers -I demo-signer -n file -s note.txt.sig < note.txt; echo "exit=$?"
ssh-keygen -Y verify -f allowed_signers -I demo-signer -n file -s note.txt.sig < note2.txt; echo "exit=$?"
ssh-keygen -Y verify -f allowed_signers -I demo-signer -n other -s note.txt.sig < note.txt; echo "exit=$?"
```

PowerShell (not run; needs the OpenSSH client). PowerShell has no `<` operator, so the verify lines go through `cmd /c`:

```powershell
ssh-keygen -q -t ed25519 -N '""' -C demo-throwaway -f demo_key     # '""' is the Windows PowerShell 5.1 form of an empty passphrase (est.)
ssh-keygen -lf demo_key.pub
ssh-keygen -Y sign -f demo_key -n file note.txt
$pub = (Get-Content demo_key.pub).Split(' ')[0..1] -join ' '
"demo-signer $pub" | Set-Content -Encoding ascii allowed_signers
cmd /c "ssh-keygen -Y verify -f allowed_signers -I demo-signer -n file -s note.txt.sig < note.txt"; "exit=$LASTEXITCODE"
cmd /c "ssh-keygen -Y verify -f allowed_signers -I demo-signer -n file -s note.txt.sig < note2.txt"; "exit=$LASTEXITCODE"
cmd /c "ssh-keygen -Y verify -f allowed_signers -I demo-signer -n other -s note.txt.sig < note.txt"; "exit=$LASTEXITCODE"
```

`-N ''` is an empty passphrase, acceptable only because this key is throwaway. For a key you keep, leave `-N` off and type a passphrase when asked.

**Check.**

- The first verify prints `Good "file" signature for demo-signer with ED25519 key SHA256:...` and `exit=0`.
- The second, with the changed file, prints `Signature verification failed: incorrect signature` and a nonzero exit (255 here).
- The third, with the wrong namespace, prints `Couldn't verify signature: namespace does not match`. The namespace stops a signature made for one purpose being reused for another.

Compare with Exercise 2: this time an attacker who changes the file cannot also make a new matching signature, because they lack `demo_key`.

**Undo.** Delete the files at the end of the page.

### Exercise 4: encrypt, decrypt, and break it on purpose

`openssl enc` is on most machines and good enough to learn with. It does **not** authenticate, which is itself the lesson. Use `age` for real work.

**Predict.** If you decrypt with the wrong passphrase, do you get an error, garbage, or nothing? And if you flip one byte of the ciphertext?

**Do.** The passphrase is generated at run time and kept in an environment variable, so it is never typed or saved.

```bash
export DEMO_PASS="$(openssl rand -hex 12)"
openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -pass env:DEMO_PASS -in note.txt -out note.enc
xxd note.enc | head -2                 # starts with the text "Salted__", then unreadable bytes
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:DEMO_PASS -in note.enc

# Break 1: the wrong passphrase
DEMO_PASS=wrong openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:DEMO_PASS -in note.enc; echo "exit=$?"

# Break 2: change one byte of the ciphertext (byte 21)
head -c 20 note.enc > tampered.enc; printf '\000' >> tampered.enc; tail -c +22 note.enc >> tampered.enc
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:DEMO_PASS -in tampered.enc | xxd; echo "exit=${PIPESTATUS[0]}"
unset DEMO_PASS
```

The `age` equivalent, from its README (not run): `age -p note.txt > note.age`, then `age -d note.age > note.out`; it asks for a passphrase, and a modified `note.age` fails with an error instead of printing altered text. For a key pair instead of a passphrase (not run):

```bash
age-keygen -o key.txt                 # prints "Public key: age1..." (the public part)
RECIPIENT='paste the printed age1... public key here'
age -r "$RECIPIENT" note.txt > note.age
age -d -i key.txt note.age
```

PowerShell (not run). `openssl` is not on Windows by default; if you have one (for example the copy that ships with Git for Windows, est.), the commands are the same as the Bash ones apart from these lines. `age` commands are identical in PowerShell, except that redirecting with `>` in Windows PowerShell 5.1 writes text, not bytes, so use `age -o note.age ...` instead of `> note.age`.

```powershell
$env:DEMO_PASS = (openssl rand -hex 12); $good = $env:DEMO_PASS
openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -pass env:DEMO_PASS -in note.txt -out note.enc
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:DEMO_PASS -in note.enc
$env:DEMO_PASS = 'wrong'
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:DEMO_PASS -in note.enc; "exit=$LASTEXITCODE"
$env:DEMO_PASS = $good
$b = [IO.File]::ReadAllBytes("$d\note.enc"); $b[20] = 0; [IO.File]::WriteAllBytes("$d\tampered.enc", $b)
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:DEMO_PASS -in tampered.enc -out tampered.out; "exit=$LASTEXITCODE"
Format-Hex tampered.out
Remove-Item Env:DEMO_PASS
```

**Check.**

- The correct passphrase prints `pay Alice 100 dollars`.
- The wrong one prints `bad decrypt` and `exit=1`. (This check works only because of padding; about one wrong passphrase in 256 slips through as garbage, so do not rely on it.)
- The tampered file is the lesson: **there is no error, exit status 0**, and the output is the original message damaged. The first 16 bytes come out as unreadable garbage and one byte of the next block is changed (in my run, `llars` became `llarV`; yours will differ because your passphrase differs). Encryption alone told you nothing about tampering. A tool that authenticates (`age`, AES-GCM) refuses the file. Combine encryption with a check, or use a tool that includes one.

**Undo.** `unset DEMO_PASS` ran at the end; delete the files later.

### Exercise 5: the same idea with a key pair (small message)

A public key encrypts, only the private key decrypts. RSA can only encrypt a short message, which is why key-wrapping tools use it on a small symmetric key, not on the data.

**Do.**

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out rsa_priv.pem
openssl pkey -in rsa_priv.pem -pubout -out rsa_pub.pem
printf 'meet at noon\n' > msg.txt
openssl pkeyutl -encrypt -pubin -inkey rsa_pub.pem -pkeyopt rsa_padding_mode:oaep -in msg.txt -out msg.rsa
wc -c msg.rsa                          # 384 bytes, whatever the message length
openssl pkeyutl -decrypt -inkey rsa_priv.pem -pkeyopt rsa_padding_mode:oaep -in msg.rsa
openssl pkeyutl -encrypt -pubin -inkey rsa_pub.pem -pkeyopt rsa_padding_mode:oaep -in msg.txt -out msg2.rsa
cmp msg.rsa msg2.rsa; echo "exit=$?"     # they differ: the padding is random
```

PowerShell (not run; needs an `openssl`, see Exercise 4):

```powershell
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out rsa_priv.pem
openssl pkey -in rsa_priv.pem -pubout -out rsa_pub.pem
[IO.File]::WriteAllText("$d\msg.txt", "meet at noon`n")
openssl pkeyutl -encrypt -pubin -inkey rsa_pub.pem -pkeyopt rsa_padding_mode:oaep -in msg.txt -out msg.rsa
(Get-Item msg.rsa).Length
openssl pkeyutl -decrypt -inkey rsa_priv.pem -pkeyopt rsa_padding_mode:oaep -in msg.rsa
openssl pkeyutl -encrypt -pubin -inkey rsa_pub.pem -pkeyopt rsa_padding_mode:oaep -in msg.txt -out msg2.rsa
(Get-FileHash msg.rsa).Hash -eq (Get-FileHash msg2.rsa).Hash        # False
```

**Check.** `msg.rsa` is 384 bytes (3072 bits); the last command prints `meet at noon`. The `cmp` line reports that the two ciphertexts differ (exit 1), because the padding adds randomness. Try to decrypt with the *public* key and it will not work.

**Undo.** Delete the files later.

### Exercise 6: a password, salted versus unsalted

Use a made-up word. Never type a real password into any exercise.

**Predict.** If two users pick the same password, do their stored values match? In which scheme?

**Do.**

```bash
python3 - <<'PY'
import hashlib, os, time
pw = b"correct horse (demo only)"

print("unsalted sha256, user 1:", hashlib.sha256(pw).hexdigest()[:24])
print("unsalted sha256, user 2:", hashlib.sha256(pw).hexdigest()[:24])

for user in (1, 2):
    salt = os.urandom(16)
    digest = hashlib.scrypt(pw, salt=salt, n=2**14, r=8, p=1, dklen=32)
    print(f"scrypt, user {user}: salt {salt.hex()[:8]} hash {digest.hex()[:24]}")

t = time.perf_counter()
for _ in range(100_000):
    hashlib.sha256(pw).digest()
fast = time.perf_counter() - t
t = time.perf_counter()
hashlib.scrypt(pw, salt=os.urandom(16), n=2**14, r=8, p=1, dklen=32)
slow = time.perf_counter() - t
print(f"100,000 sha256 guesses: {fast:.2f} s; one scrypt guess: {slow:.3f} s")
PY
```

PowerShell (not run): the Python is the same on every system. Save the lines between `python3 - <<'PY'` and `PY` (not those two lines themselves) to a file named `scrypt_demo.py` in your scratch folder, then run `python scrypt_demo.py` (or `py scrypt_demo.py`).

**Check.** The two unsalted lines are identical: an attacker's table of common passwords matches both at once. The two scrypt lines differ because the salts differ. The timing line shows the cost difference (on my machine about 0.04 s for the 100,000 SHA-256 guesses against about 0.03 s for a single scrypt guess; yours will differ, but expect scrypt to cost about as much for one guess as SHA-256 does for a hundred thousand). **The parameters here are chosen for a quick demo, N=2^14, below the OWASP scrypt minimum of N=2^17 (128 MiB) with r=8 and p=1.** In real code use a maintained library (for Argon2id: OWASP's minimum is 19 MiB of memory, 2 iterations, 1 degree of parallelism) and read the cheat sheet's current numbers.

**Undo.** Nothing was written to disk.

### Exercise 7: what leaks in a git repository

This builds a repository **in your scratch folder**, with a **fake** key made a moment ago. No key-shaped text is stored in this project.

**Predict.** You commit a private key by mistake, notice, and delete it in the next commit. Is it gone?

**Do.** Run it in the scratch folder, not in a clone of this project.

```bash
mkdir leak-demo && cd leak-demo && git init -q -b main
git config user.email demo@example.invalid && git config user.name demo
ssh-keygen -q -t ed25519 -N '' -C fake -f ./fake_key
echo hello > README.md
git add README.md fake_key && git commit -qm "add readme (and, oops, a key)"
git rm -q --cached fake_key && echo fake_key >> .gitignore
git add .gitignore && git commit -qm "remove the key"
git log --oneline
git show HEAD~1:fake_key | head -n 1             # read it back from history
git log --all --diff-filter=A --name-only --format='%h'
```

Next, a commit ID is a hash of content (the idea from the start of the page), and the same repository can sign commits with an SSH key:

```bash
printf 'hello\n' | git hash-object --stdin
printf 'blob 6\0hello\n' | sha1sum              # the same value: git hashes "blob", the size, a NUL, then the content
git config gpg.format ssh && git config user.signingkey ./fake_key.pub
git commit --allow-empty -S -qm "a signed commit" && git cat-file -p HEAD | head -n 6
```

PowerShell (not run; needs git and the OpenSSH client). Avoid `echo hello > README.md` in Windows PowerShell 5.1, which writes UTF-16, and piping text into `git hash-object`, which adds a carriage return:

```powershell
New-Item -ItemType Directory leak-demo | Out-Null; Set-Location leak-demo; git init -q -b main
git config user.email demo@example.invalid; git config user.name demo
ssh-keygen -q -t ed25519 -N '""' -C fake -f ./fake_key
[IO.File]::WriteAllText("$PWD\README.md", "hello`n")
git add README.md fake_key; git commit -qm "add readme (and, oops, a key)"
git rm -q --cached fake_key; Add-Content .gitignore fake_key
git add .gitignore; git commit -qm "remove the key"
git log --oneline
git show HEAD~1:fake_key | Select-Object -First 1
git log --all --diff-filter=A --name-only --format='%h'
git hash-object README.md
python -c "import hashlib; print(hashlib.sha1(b'blob 6\0hello\n').hexdigest())"
git config gpg.format ssh; git config user.signingkey ./fake_key.pub
git commit --allow-empty -S -qm "a signed commit"; git cat-file -p HEAD | Select-Object -First 6
```

**Check.** Two commits, but `git show HEAD~1:fake_key` still prints the whole key, and the log lists `fake_key` as added in the first commit: deleting a file in a new commit never removes it from history. The two hashes in the second block match, so a commit ID is a hash of content. The signed commit's header carries a `gpgsig` block holding an SSH signature. (To check such signatures later, git needs `gpg.ssh.allowedSignersFile`, the same file format as Exercise 3.) The real lesson for a leaked key: **replace the key first** (create a new pair, install the new public key, remove the old one everywhere), and only then think about cleaning history, which does not help once someone has cloned it. The same order is on [APIs and tokens: when a secret leaks](APIs-and-Tokens-From-Zero.md#when-a-secret-leaks-revoke-then-rotate-then-clean-up). This project scans all history for key shapes, which is why no sample key is ever committed here, and why every sample on this page is made at run time.

**Undo.** `cd ..` and delete `leak-demo` (PowerShell: `Set-Location ..; Remove-Item -Recurse leak-demo`).

### Clean up

```bash
cd ~ && rm -r -- "$LAB"
```

`$LAB` is the scratch folder from the setup. If you opened a new terminal, `$LAB` is empty: do not run the line; delete the folder by hand. It holds only throwaway files. In PowerShell: `Set-Location ~; Remove-Item -Recurse $d` (not run).

## Build it, break it, detect it, defend it

The same loop as the [labs](Labs-Break-It-on-Purpose.md), on what you just did.

- **Build.** Hash a file, sign it with a throwaway Ed25519 key, encrypt it, and keep the public key and the hash somewhere you trust (Exercises 1 to 4).
- **Break.** Change one byte of the file (Exercise 2 and 3), the signature's namespace (Exercise 3) or the ciphertext (Exercise 4); decrypt with the wrong key. Then ask what an attacker with a stolen disk and no key can do: nothing useful with the data, which is the point of encryption, so they go looking for the key.
- **Detect.** The hash check fails with a nonzero exit. The signature check says `incorrect signature`. A changed SSH host key produces a loud warning. The unauthenticated ciphertext is the case where nothing detects the change, which is why the habit is to authenticate and verify. In an organization, the detection for a leaked key is a secret scanner in CI (this project runs one) and cloud audit logs showing the key used from somewhere unexpected.
- **Evade.** Attackers rarely attack the math, which has been reviewed for decades. They go after **keys** (stolen from a laptop, a repository, a log, a backup, or a developer who pasted one into chat) and **implementations** (a library bug, a reused nonce, a missing authentication check, a weak random number, a downgrade to an old protocol version). For passwords, the evasion of a plain hash is a **lookup**: with no salt, one precomputed table of common passwords matches every user at once, and a fast hash lets an offline guesser try billions of candidates. A **length-extension** attack abuses a home-made `hash(secret + message)` check. Described in words only, and none of it is aimed at anything real here.
- **Defend.** Salted, slow, memory-hard password hashes; authenticated encryption; signed commits and pinned dependencies; HMAC instead of a home-made check; keys with passphrases or in hardware, one per device; keys kept out of repositories, with a scanner as the safety net; a rotation and revocation plan ([Doppler and secrets](Doppler-and-Secrets.md)).

## Checkpoint

- Fill the table from memory: encoding, hashing, encryption, signing: what each answers, and which is reversible.
- Explain to a friend why `sha256(password)` is the wrong way to store a password, and what two things fix it.
- Say what a certificate is in one sentence, and what the SSH fingerprint prompt is asking you.
- Explain why a deleted private key in a git history is still leaked, and what you do first.

Answers are in the sections above.

## Claims register

Read 2026-10-21 with read-only requests, or run locally as stated. "Not read" is marked **est.** in the text.

| Claim | Source | Status |
|---|---|---|
| Passwords should be hashed with a unique salt and a slow hash such as Argon2id, bcrypt or PBKDF2; fast hashes such as SHA-256 are not suitable; use Argon2id with at least 19 MiB, 2 iterations and parallelism 1; scrypt (if Argon2id is unavailable) with N=2^17, r=8, p=1 or the listed equivalents; bcrypt only for legacy systems; passwords hashed, not encrypted; peppers are defense in depth | [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) (source file read from the OWASP CheatSheetSeries repository) | Read |
| NIST deprecated SHA-1 in 2011, disallowed it for digital signatures at the end of 2013, and published a plan in December 2022 to move away from its remaining limited uses; FIPS 180-4 defines SHA-1 and SHA-2, FIPS 202 defines SHA-3 | [NIST: Hash Functions](https://csrc.nist.gov/Projects/Hash-Functions) | Read |
| MD5 has security considerations updated for collision attacks | [RFC 6151](https://www.rfc-editor.org/rfc/rfc6151.txt) | Title and abstract read; detail not read |
| `ssh-keygen` generates an Ed25519 key when given no arguments; lists `ed25519-sk` among key types; `-Y sign` and `-Y verify` flags, namespaces and the allowed signers file | [OpenBSD ssh-keygen(1)](https://man.openbsd.org/ssh-keygen) and the local `ssh-keygen` manual (OpenSSH 10.3) | Read, and the commands run |
| `ssh-keygen -Y` introduced in OpenSSH 8.0 | General knowledge | Not read; **est.** |
| `age` install methods (`apt install age`, `brew install age`), passphrase and key-pair usage, and that SSH keys on a YubiKey cannot decrypt files | [age README](https://github.com/FiloSottile/age) | Read; `age` not run |
| Git names objects with SHA-1 and has a documented transition plan to a stronger function | [Git: hash function transition](https://git-scm.com/docs/hash-function-transition) | Opening read |
| `gpg.format` accepts `ssh`, and `gpg.ssh.program` defaults to `ssh-keygen` | `git-config` manual, Git 2.47.3 (local) | Read, and the signed commit run |
| AES-GCM is defined in NIST SP 800-38D | [NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final) | Listing read; the nonce requirement text not read (**est.**) |
| Hardware key guidance (two keys, one stored apart, recovery codes in a password manager) | [Build it from zero, step 0](Build-It-From-Zero-Accounts-to-Stage-1.md#step-0-make-a-mistake-impossible-to-be-expensive) | Read in this repository |
| Diffie-Hellman in TLS and SSH, certificates and CAs, Kerckhoffs's principle, length-extension, HMAC | General knowledge; TLS 1.3 is [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446) | Not read; **est.** |
| PowerShell, macOS `shasum`, the Windows OpenSSH feature, and `age` commands | Tool documentation | **Not run** |
| Exercises 1 to 7 in Bash: outputs described | Run on Linux, OpenSSL 3.5.7, OpenSSH 10.3, Python 3.13, Git 2.47.3 | Run 2026-10-21 |

Next: [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md), step 4 of the core path on the [Reading order](Reading-Order.md) page.
