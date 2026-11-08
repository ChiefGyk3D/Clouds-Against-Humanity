# Cryptography fundamentals: symmetric and asymmetric keys, hashing, certificates, and where this project uses each

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says (and the gap)](#what-the-wiki-already-says-and-the-gap)
- [What encryption is and is not](#what-encryption-is-and-is-not)
- [Symmetric and asymmetric: what each is good for](#symmetric-and-asymmetric-what-each-is-good-for)
- [Hashing is not encryption: salts, passwords and message authentication](#hashing-is-not-encryption-salts-passwords-and-message-authentication)
- [Digital signatures](#digital-signatures)
- [Certificates and PKI in plain words](#certificates-and-pki-in-plain-words)
- [Data at rest, in transit and in use](#data-at-rest-in-transit-and-in-use)
- [Where this shows up in this project](#where-this-shows-up-in-this-project)
- [Key management and custody: the hard part](#key-management-and-custody-the-hard-part)
- [Common mistakes](#common-mistakes)
- [Modern defaults per NIST](#modern-defaults-per-nist)
- [Post-quantum planning, as far as NIST publishes it](#post-quantum-planning-as-far-as-nist-publishes-it)
- [Free path: run the drill, then read a real certificate chain](#free-path-run-the-drill-then-read-a-real-certificate-chain)
- [Build, break, detect, defend](#build-break-detect-defend)
- [Checkpoint](#checkpoint)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

Side page to the start-from-zero pages. Read it after [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md), which tells encoding, hashing, encryption and signing apart and has the first hands-on exercises, and after [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md), because encryption mainly serves confidentiality and does very little for the other two properties by itself. This page does not repeat them. It adds the parts they leave open: how symmetric and asymmetric encryption work together, message authentication, what a certificate authority is, the difference between data at rest, in transit and in use, where this project uses each (and where it uses none), why key custody is the hard part, the mistakes that break good algorithms, what NIST currently recommends, and what NIST has published about post-quantum planning. The [lesson on Tor and I2P](Tor-I2P-and-the-Darknet-Without-the-Myths.md) (issue 358) is separate, and this page does not depend on it. Next: [Backups deep dive](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md), which takes up who holds the key to an encrypted backup.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. One local script was run and one network command was run once; everything else was read, not run.** On **2026-10-31** I ran the Bash script in the free path on a Debian-based Linux machine (GNU bash 5.2.37, GNU coreutils 9.7, OpenSSL 3.5.7, GnuPG 2.4.7, Python 3.13.5, as an ordinary user) and pasted its output. On the same day I ran one `openssl s_client` command against a public website; its output is a **sample from that date**, because a third-party site changes its certificates and settings. **Not run:** the script on macOS or Windows, any PowerShell version (none is given), the `age` tool, every cloud and provider command named, and every control in the project table (I read the files; I applied no stack and called no provider). The NIST pages and IETF documents were downloaded and read on **2026-10-31** and sit in the [claims register](#claims-register) with their URLs and the date each page shows. A suggestion that is mine and not a standard's is marked **est.** I did not consult or copy any exam material or any copyrighted text; the CISSP cryptography domain was used only as a rough list of topics to cover.

> **Prerequisites.** [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) first, then [The terminal and your first script](Terminal-and-Your-First-Script.md) for running a script. The free path needs a Linux machine or WSL 2 with `bash`, GNU `sha256sum` and `cmp`, `openssl` 3.x, `gpg` and `python3` (stock macOS lacks some of the GNU forms, so it is not written for macOS). The TLS exercise needs an internet connection and nothing else. No cloud account, no installs. About 90 minutes with the exercises (est.).

> **Where this runs.** The script works in one folder it creates with `mktemp -d` and deletes at the end, with its own throwaway GnuPG home so your real keyring is not touched. It opens no connection. Every demo key is derived inside the script from a readable seed, and the passphrases are obviously fake words, so all of them are public and must never protect anything real. The TLS exercise makes one ordinary HTTPS connection to a public example site, the same thing a browser does when you open it, and nothing else.

## What you will be able to do

- Say what encryption gives you (secrecy) and what it does not (a promise that nothing was changed, or who sent it).
- Say what symmetric and asymmetric encryption are each good for, and how a real connection uses both: a key exchange first, then a fast symmetric cipher.
- Explain why a hash is not encryption, why a password hash needs a salt and a slow function, and what a message authentication code adds.
- Explain what a digital signature proves, and what a certificate and a certificate authority add to it.
- Sort a data problem into at rest, in transit or in use, and say which one a given control covers.
- Read this project's table and find the places where it uses cryptography, the places where the provider does, and the rows that say **None**.
- Explain why custody of the key, not the algorithm, is usually where encryption fails.
- Name the common mistakes (your own cryptography, ECB mode, a reused nonce, a password used as a key, expecting secrecy to give integrity) and show two of them happen.
- State the current NIST guidance in a table, with the document and date for each line, and say what NIST has published about post-quantum cryptography and what it has not.
- Run the drill, read a real certificate chain, and tell which parts of the output are fixed by this page and which will differ on your machine.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Encoding, hashing, encryption and signing told apart; salt; password storage; SSH keys; the beginner mistakes | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) | How the pieces combine in a real connection, message authentication, PKI, the three data states, this project's own map, key custody, and what NIST says to use now. |
| What a certificate chain looks like, in a browser | [How a web request works](How-a-Web-Request-Works.md#certificates-and-trust-chains-in-plain-language) | Reading the fields yourself from the command line, and running a small certificate authority of your own. |
| Confidentiality, integrity and availability, and the key-versus-availability trade | [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) | The tools that deliver each property, and the ones that do not. |
| Who holds the key to an encrypted backup | [Backups deep dive](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md#encryption-and-key-custody) | Key custody for every kind of key, not only backups. |
| Secrets in state, and how secrets reach a run | [Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md), [Doppler and secrets](Doppler-and-Secrets.md) | Which of those are protected by encryption, and which only by access rules. |

## What encryption is and is not

**Encryption** turns readable data (the **plaintext**) into unreadable data (the **ciphertext**) using a **cipher** and a **key**, and turns it back only for someone who has the right key. In modern practice the cipher is public. Experts try to break it for years, and a method kept secret has been tried only by its author. All the secrecy lives in the key. (This idea is usually called Kerckhoffs's principle; I did not read a source for it, so treat the name as **est.**)

That is all it does. Four things people assume it also does, and does not:

| People assume encryption gives... | It does not, because... | What does |
|---|---|---|
| **Integrity**: nobody changed it | A cipher hides content; it does not by itself notice a change. Experiments 4 and 6 below show a changed ciphertext decrypting without any error. | An authenticated mode (AES-GCM, ChaCha20-Poly1305, or a tool that includes a check), or a separate MAC or signature |
| **Authenticity**: it came from who you think | Anyone who has the key (or the public key, in asymmetric encryption) can make a valid ciphertext. | A signature, or a MAC with a key only the two parties hold |
| **A password check** | If you "encrypt" passwords, whoever finds the key reads them all. | A salted, slow hash (see below) |
| **Availability** | A key that is lost makes the data as gone as a deleted file. | A backup of the key, held somewhere else, with more than one holder |

Two neighbors that are not encryption at all. **Encoding** such as base64 changes the form of data and has no key; anyone reverses it. **Hashing** gives a short fingerprint of data and cannot be reversed because the data is not in it. Both are on [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md).

**Predict.** A tool says it "encrypts with AES-256". A friend says that means nobody can change your file without you noticing. Who is right? (Answer: it depends on the mode, and the claim leaves it out. Experiment 4 shows a mode where the friend is wrong.)

## Symmetric and asymmetric: what each is good for

| Property | Symmetric | Asymmetric (public key) |
|---|---|---|
| **Keys** | One shared secret key locks and unlocks | A key pair: a private key you guard and a public key you share |
| **Speed** | Fast; encrypts gigabytes | Slow, and limited to small inputs |
| **Good for** | Encrypting the data itself: a disk, a backup, a file, the bulk of a connection | Agreeing a key with a stranger, proving who signed something |
| **The hard part** | Getting the same key to both sides without anyone else seeing it | Knowing that a public key really belongs to the person or server you meant |
| **Examples** | AES, ChaCha20 | Elliptic-curve key exchange (X25519, ECDH), RSA, EdDSA signatures (Ed25519) |

NIST's own transition report describes symmetric algorithms the same way: one key both applies protection and removes or checks it, so it "must be kept secret if the data is to remain protected" (IR 8547, October 2026, read 2026-10-31).

### How they combine: a key exchange, then a symmetric cipher

Neither kind does the whole job. A real connection uses both, in this order:

1. The two sides use asymmetric cryptography to **agree on a secret** (a key exchange). Each side makes a fresh key pair, sends the public half, and combines its own private half with the other side's public half. Both arrive at the same secret, and someone who saw only the public halves cannot.
2. A short step called a **key derivation function** (KDF) turns that secret into one or more symmetric keys.
3. All the real data is then protected with a fast symmetric cipher using those keys.

TLS 1.3 is built this way. Its handshake carries an "ephemeral Diffie-Hellman share" from each side, and the combination of the two hello messages "determines the shared keys" (RFC 8446, August 2018, read 2026-10-31). Because the key pairs are made fresh for each connection and then thrown away, a key stolen next year cannot open traffic recorded today. That property is called **forward secrecy** (my wording of the idea; the RFC text I read says the keys are ephemeral, so the name is **est.** here). The same shape appears when you encrypt a file to someone's public key: the tool picks a random symmetric key, encrypts the file with it, and encrypts only that small key to the public key (this is how tools such as GnuPG and `age` work, from general knowledge; **est.**).

Experiment 7 does steps 1 and 2 with real X25519 keys: two sides get the same secret, a third party who has both public keys gets a different one, and a KDF step yields the same 32-byte key for both.

## Hashing is not encryption: salts, passwords and message authentication

[Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#hashing-a-fingerprint-not-a-lock) covers hashing and password storage in detail. The short version, and what to add:

- A **hash** is a one-way fingerprint. Change one byte of the input and the output changes completely. Experiment 1 shows it: changing `100` to `900` changes one byte, and the SHA-256 value looks unrelated. Of the 64 hex digits, 7 happen to line up by chance, and chance alone gives about 4.
- A hash with no secret proves only "same data as before", and only if you got the expected hash from somewhere an attacker could not also change. Experiment 1 also shows `sha256sum -c` passing, then failing after the file changes.
- A **message authentication code** (MAC) mixes a **secret key** into the hash. Only someone with the key can make or check the value, so it proves both that the data was not changed and that the sender held the key. The standard construction is **HMAC** (RFC 2104, February 1997): use it, not a home-made `hash(secret + message)`. In experiment 1 the same message under a different key gives a different tag, and a changed message gives a different tag.
- **A MAC is not a signature.** Both sides hold the same key, so either could have made the tag, and a MAC cannot prove to a third party who made it. A signature can (next section).

### Why a password is not a key, and not a plain hash

A website must check your password without being able to read it, so it stores a hash. Three details decide whether that is safe, because the attacker's likely position is "I stole the database and can try guesses at leisure":

- **Never a raw fast hash.** SHA-256 is built to be fast. OWASP's Password Storage Cheat Sheet says fast algorithms such as SHA-256 are not suitable for password storage (read 2026-10-31).
- **A salt.** A random value, unique per password and stored beside the hash, mixed in before hashing. Two users with the same password then have different hashes, and one precomputed table cannot crack the whole database. Experiment 2 shows the effect on a key derived from a password: the same password and different salts give completely different keys.
- **A slow, memory-hard function.** OWASP's current first choice is Argon2id, with a minimum configuration of 19 MiB of memory, 2 iterations and parallelism 1; PBKDF2 with HMAC-SHA-256 at a work factor of 600,000 or more if FIPS-140 compliance is required. RFC 9106 (September 2021, Argon2) recommends Argon2id with t=1 and 2 GiB of memory first, and t=3 with 64 MiB for memory-constrained environments. The two documents give different numbers: use your language's library at its current documented settings, and never write the loop yourself.

A password is also **not a key.** A key should be random and as long as the cipher needs; a human-chosen password is short and guessable. When you must derive an encryption key from a passphrase (a file encryption tool does), the passphrase goes through a salted, slow function first, which is exactly what experiment 2 does, and the strength of the result is still limited by the passphrase.

## Digital signatures

A **digital signature** is made with a private key and checked with the matching public key. It gives three things: the signer held the private key, the data has not changed since signing, and (weakly) the signer cannot easily say it was not them. It hides nothing: the data is readable by anyone. It is made over a hash of the data, which is why it is fast enough for large files.

Experiment 8 signs the note with an Ed25519 key. The signature is 64 bytes whatever the message size, verification of the original is labeled `VERIFY-OK`, and verification of the changed note is labeled `VERIFY-FAIL`. A signature proves only that the key signed. Whether that key belongs to the person you think is a separate question, and the answer is a certificate.

## Certificates and PKI in plain words

You are given a public key by a stranger (a website). How do you know it is theirs? You cannot, unless somebody you already trust vouches for it. A **certificate** is that voucher: a file that says "this public key belongs to this name", valid between two dates, **signed** by an **issuer**. The standard format for web certificates is X.509, profiled for the internet in RFC 5280 (May 2008, read 2026-10-31).

- A **certificate authority** (CA) is an organization that issues and signs certificates. Its own certificate is signed by itself (a **root**) or by a higher CA.
- Your operating system or browser ships with a list of root certificates it trusts. RFC 5280 calls such a starting point a **trust anchor**, and says the choice of trust anchor is "a matter of policy". A site's certificate is accepted when you can follow signatures from it up a **chain** to a trust anchor, each link valid, unexpired and allowed to sign certificates.
- The checks a client makes: the chain leads to a trust anchor; every certificate is within its dates; the name you asked for matches the name in the certificate; and the server proves it holds the matching private key by signing something during the handshake.
- **PKI** (public key infrastructure) is the whole arrangement: the CAs, the formats, the rules for issuing and revoking, and the software that checks them. Its weakness is the one in the paragraph above: every CA your system trusts can vouch for any name. When a CA is careless or compromised, a certificate for a name it should not have issued becomes valid, which is why the dates are short and why chains are inspected.

Experiment 9 builds a small CA in your terminal and shows four outcomes for the same site certificate: valid against the right CA and name; rejected for the wrong name; rejected when there is no trusted CA; and rejected when a different CA with the same name is offered. The last one is the important one. Names are labels, and the check follows the signature, not the name. The experiment is also a reminder that "the padlock" means "the chain checked out", which says nothing about whether the site is honest.

SSH uses the same idea without CAs by default: a server's key is trusted because you accepted its fingerprint the first time (see [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#key-pairs-in-the-wild-ssh-keys-and-tls-certificates)).

## Data at rest, in transit and in use

| State | What it means | What protects it | What it does not stop |
|---|---|---|---|
| **At rest** | Stored: on a disk, in a backup, in a bucket, in a state file | Disk, file or object encryption with a key kept elsewhere; access rules | Anyone who can read it through the system while it is running, because the system holds the key and decrypts for them |
| **In transit** | Moving across a network | TLS (or SSH, or another encrypted tunnel) | What the other end does with the data after it arrives; a client that accepts any certificate |
| **In use** | Being processed in memory by a program | Access control, process isolation, short lifetimes for secrets; special hardware features that keep memory encrypted exist but are not covered here (est.) | Almost everything, since the program needs the plain data to work on it |

The practical reading is that **encryption moves trust to the key and to whoever can ask for decryption.** A database encrypted on disk is plaintext to every account that can query it. A TLS connection is plaintext to both ends. Ask of any "it's encrypted" claim: encrypted where, against whom, and who holds the key? (The [CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md#the-trade-offs-why-you-cannot-maximize-all-three) page shows the trade on the availability side.)

## Where this shows up in this project

Each row is one place the project depends on cryptography, what it relies on, the file that shows it and whether it exists. "Built" means the file is in the repository and does what the row says; I read the file and did not apply it. Where the project sets nothing, the row says **None**, because a missing control is a finding, not a blank.

| Place | What protects it, or does not | File that shows it | Status |
|---|---|---|---|
| Disk of a droplet (at rest) | Nothing the project sets. Whatever the provider does to its disks is not stated in this repository and I did not read the provider's page | None | None |
| Droplet backups (at rest) | Turned off on purpose, so there is no backup to encrypt; the provider's own page says its automated backups are not encrypted at rest (see [Backups, recovery and patching](Backups-Recovery-and-Patching.md#four-words-that-sound-alike)) | `modules/twingate-connector/main.tf` | Built (`backups = false`); nothing encrypted |
| Object storage bucket (at rest) | The bucket is private and versioned; no encryption setting is written in the module, so any encryption is the provider's | `modules/spaces-bucket/main.tf`, `modules/spaces-bucket/variables.tf` | Written, off by default; no encryption in code |
| OpenTofu state (at rest) | Git-ignored so it is not committed; I found no `encryption` block in any `.tf` file. State holds all resource attributes, so a connector token resource means a secret in state (est.) | `.gitignore` | Partly built: ignored, not encrypted by the project |
| Download of the Doppler command-line tool (in transit and integrity) | HTTPS only, TLS 1.2 or newer, then the file is checked against a pinned SHA-256 and refused on mismatch | `scripts/spacelift/doppler-env.sh` | Built |
| Twingate package key (integrity) | The vendor's apt key must match a pinned fingerprint before it is trusted | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` | Built |
| SSH to hosts (in transit, signatures) | Keys only; password login is off | `modules/twingate-bootstrap/cloud-init.yaml.tftpl` | Built |
| The Twingate path (in transit) | Twingate documents that its relay connects a client to the requested connector for "a single, certificate-pinned TLS tunnel". The project does not configure this; it relies on the vendor, and the connectors are the project's part of the path | `docs/wiki/Twingate.md`, `stacks/10-access/main.tf` | Vendor-documented (page read 2026-10-31); not testable from this repository |
| The secret store | Secrets come from Doppler at run time; Spacelift holds one read-only token; an expiry of 90 days is set by hand. How Doppler encrypts its own storage was not read | `docs/spacelift-secrets.md` | Built as a process; vendor encryption not read |
| Calls from OpenTofu and the pipeline to provider APIs (in transit) | Each tool's own HTTPS default; the repository sets nothing | None | None (not a gap to fix, a fact to know) |
| Pipeline code (integrity) | Shared workflows are called by full commit hash with the version in a comment, so different code would have a different hash | `.github/workflows/ci.yml` | Built |
| Public MQTT over TLS on port 8883 | Listed in the edge firewall; no service is installed yet | `stacks/50-edge/main.tf` | Written; no service |
| Data in use | Nothing the project sets; no confidential-computing hardware is used | None | None |
| A list of every place that uses RSA, ECC or Diffie-Hellman, for post-quantum planning | Not written down | None | None |
| Written key custody for each key (who holds it, who can recover it, when it was last rotated) | Tokens have an expiry and a rotation note in the Spacelift secrets page; I did not find a table covering SSH keys or who can recover each key | `docs/spacelift-secrets.md` | Partly built |

Three honest observations. **The project does a lot of integrity checking (pins and fingerprints) and almost no encryption of its own at rest**; what it relies on is the provider's controls plus keeping secrets out of the repository, which suits a lab that holds nothing precious and is the wrong answer the day stage 3 holds real data. **Most of the in-transit protection is somebody else's** (TLS to the APIs, Twingate's tunnel). **Every None is a question** to ask before the data arrives, such as where the state is stored and what encrypts it.

## Key management and custody: the hard part

Cryptography replaces "protect the data" with "protect the key", and the key has a whole life:

| Stage | The question | What goes wrong |
|---|---|---|
| **Generate** | Is it random, and made where it will live? | A key made from a password or a predictable value; a key generated on a shared machine |
| **Store** | Where does it rest, and who can read it there? | A key next to the data it protects (a locked door with the key in the lock); a key in a repository |
| **Use** | Which process may ask for it, and how often? | One key reused for every purpose, so one theft opens everything |
| **Share or distribute** | How does it reach the other side? | A symmetric key sent by email; a public key accepted without checking whose it is |
| **Rotate** | How do you replace it, and how long may one key stay in use? | A key never changed; rotation that nobody has rehearsed |
| **Back up and recover** | If the only holder is gone, can the data be opened? | A key held by one person, or only on the machine that died. The data is gone for good |
| **Revoke** | If it leaks, how fast can you stop trusting it? | Nobody knows where the public half was installed |
| **Destroy** | When it is retired, is it really gone? | Copies in old backups, old laptops and chat logs |

NIST's key-management guidance has been rewritten around the same problem: the December 2025 draft of SP 800-57 Part 1 Revision 6 says it adds "a section ... to discuss keying material storage and mechanisms" and discusses the keys used for key establishment and for key storage separately (listing page, read 2026-10-31; a draft, comments closed). The published Revision 5 is May 2020.

Rules that follow, and that hold for any key in this project:

- **Separate the key from the data**, and keep the key somewhere an attacker who gets the data cannot reach by the same route.
- **More than one holder, and a written recovery path.** A single holder is a single point of failure; a circle (the key to the backup lives in the system the backup restores) is a failure waiting for the worst day. The [Backups deep dive](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md#encryption-and-key-custody) takes both up.
- **One key per purpose.** A key for signing is not a key for encrypting; a key for one device is not a key for another.
- **Give secrets a short life**, as the Spacelift page does with a 90-day token, so a leak expires.
- **Hardware for the keys that matter.** A hardware key signs on request and never lets the private half out (see [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#keeping-keys-storage-passphrases-and-hardware-keys)).
- **Test recovery.** A key you have never restored from is a key you do not know you have.

## Common mistakes

| Mistake | What breaks | Instead |
|---|---|---|
| **Rolling your own cryptography** | Home-made schemes fail in ways their authors cannot see | A well-reviewed library or tool at its defaults (TLS, OpenSSH, GnuPG, `age`, libsodium) |
| **ECB mode** | Equal blocks of plaintext give equal blocks of ciphertext, so patterns show through (experiment 3). NIST's draft SP 800-131A Rev. 3 proposes retiring ECB for data encryption | An authenticated mode such as GCM, or a library that picks it for you |
| **Reusing a nonce** | With a stream-style mode, two messages under one key and one nonce let an attacker XOR the ciphertexts and strip the key away (experiment 5). With AES-GCM the same mistake can allow forged messages. SP 800-38D calls the uniqueness requirement "almost as important as the secrecy of the key". RFC 8439 says the ChaCha20 nonce "MUST not be repeated for the same key" | Let the library choose nonces; never write your own counter |
| **A password used as a key** | Passwords are short and guessable | A salted, slow key derivation function (experiment 2), and still a long passphrase |
| **Expecting secrecy to give integrity** | A changed ciphertext decrypts without an error and the attacker chose the change (experiment 4) | An authenticated mode or a MAC (experiment 6) |
| **Trusting the output before the check finishes** | A tool can print data and report the failure afterward. On GnuPG 2.4.7 an edited file in experiment 6 printed damaged text (`domlars` for `dollars`), then a warning and exit status 2; the drill itself prints only a label, because that wording and order can vary by version | Check the exit status; throw the output away on failure |
| **Encrypting passwords instead of hashing them** | One stolen key reads every password | A salted, slow hash |
| **Accepting any certificate** | Turns TLS into encryption to an unknown party | Verify the chain and the name; never turn verification off to "make it work" |
| **Key next to the data** | The lock and the key fall together | A different place, and a different route to reach it |
| **Old algorithms kept for convenience** | Weaknesses only get worse | Retire what the standards retire (see below) |

## Modern defaults per NIST

NIST publishes guidance as numbered documents with status words. **Acceptable** means approved for use. **Deprecated** means it may be used if the owner accepts the risk. **Disallowed** means no longer allowed for the stated purpose. **Legacy use** means only to process data already protected (to decrypt or to verify) (IR 8547, October 2026, section 4.1). The table is what I read; it is a summary, not a replacement for the documents, and one of its sources is a draft.

| Need | Current guidance | Document and date |
|---|---|---|
| Block cipher | AES with 128, 192 or 256 bit keys is acceptable. Two-key and three-key Triple DES are disallowed for encryption (three-key after 2023); SKIPJACK is disallowed | SP 800-131A Rev. 2, March 2019; AES is FIPS 197 (updated 2023-05-09 with no technical change) |
| Mode of operation | CBC, CFB, CTR, OFB, CCM, GCM and XTS-AES are listed as acceptable; ECB is listed as disallowed for data encryption in the draft's table | SP 800-131A Rev. 3 initial public draft, 2024-10-21 (a draft, comments closed). I did not find a final Revision 3 on the page I read |
| Strength of a key | 112 bits is the minimum for new protection; 128 bits and up is the target. Comparable sizes: 128 bits is AES-128, RSA 3072 or elliptic-curve keys of 256 to 383 bits; 192 bits is AES-192, RSA 7680, curves of 384 to 511 bits; 256 bits is AES-256, RSA 15360, curves of 512 or more. RSA 2048 and curves of 224 to 255 bits are rated 112 bits | SP 800-57 Part 1 Rev. 5, May 2020, Table 2. Its footnote says the estimates for public-key algorithms "will be significantly affected when quantum computing becomes a practical consideration" |
| Hash | The SHA-2 and SHA-3 families. SHA-1 is not allowed for digital signature generation except where protocol-specific guidance allows, and is acceptable for uses that do not need collision resistance. The draft Revision 3 proposes retiring SHA-1 and the 224-bit hashes after 2030 | SP 800-131A Rev. 2 (March 2019) and the Rev. 3 draft (2024-10-21) |
| Keyed hash | HMAC | RFC 2104 (February 1997); named in SP 800-131A |
| Password storage | Argon2id, then scrypt, with bcrypt only for old systems; PBKDF2 (HMAC-SHA-256, 600,000 or more) when FIPS-140 compliance is required | OWASP cheat sheet and RFC 9106 (September 2021); these are not NIST documents |
| Signatures | RSA, ECDSA and EdDSA are approved and rated by strength as in the key table; all three are scheduled for deprecation after 2030 and disallowance after 2035 | IR 8547, October 2026, Table 2 |
| Key agreement | Finite-field and elliptic-curve Diffie-Hellman and RSA key transport, same schedule | IR 8547, October 2026, Table 4 |
| TLS | TLS 1.2 with FIPS-based suites supported by all government servers and clients; support for TLS 1.3 required by 2024-01-01. The page says the document is being reviewed. IR 8547 separately says agencies must support TLS 1.3 by 2030-01-02 | SP 800-52 Rev. 2, August 2019 (planning note 2026-05-07); IR 8547 |
| Authenticated encryption in practice | Use GCM or ChaCha20-Poly1305 through a library, with a unique nonce for every message | SP 800-38D (November 2007; NIST has decided to revise it, per its page); RFC 8439 (June 2018) |

Two cautions. These are the **federal** numbers; they are a sound benchmark for everyone else, and they are not the law for a hobby project. And **a key size is not the whole story**: the weakest part of a system, usually the key handling above, decides the outcome.

## Post-quantum planning, as far as NIST publishes it

A **cryptanalytically relevant quantum computer** (one able to break today's public-key algorithms) does not exist today as far as the pages I read say; NIST's project page describes quantum computers as "machines that may be years or decades away but could eventually break many of today's widely used cryptographic systems" (read 2026-10-31). The planning problem is that data recorded now can be decrypted later. NIST's report calls this "harvest now, decrypt later" and names it as "one of the main reasons why the transition to post-quantum cryptography is urgent" (IR 8547, October 2026).

What NIST has published, with dates:

- **Three finished standards, 2024-08-13:** FIPS 203, **ML-KEM** (a key-encapsulation mechanism, for key establishment); FIPS 204, **ML-DSA** (digital signatures); FIPS 205, **SLH-DSA** (hash-based digital signatures). Their pages note errata that will be corrected in future revisions (FIPS 203: planning note 2025-11-17; FIPS 204: 2026-07-31).
- **More coming:** the Falcon signature algorithm and the **HQC** key-encapsulation mechanism were selected for ongoing standardization. IR 8547 says a standard for HQC is under development. I found no final standard for either on the pages I read.
- **A transition plan, IR 8547, final, published October 2026** (the page shows 2026-10-27; the first draft was 2024-11-12). NIST will deprecate quantum-vulnerable public-key algorithms (RSA, ECDSA, EdDSA, Diffie-Hellman and elliptic-curve Diffie-Hellman) **after 2030** and disallow them **after 2035**. It also reports that US federal directives (Executive Order 14412 and OMB Memorandum M-26-15, which I did not read, only IR 8547's summary of them) require the most sensitive federal systems to adopt post-quantum key establishment by 2030-12-31 and post-quantum signatures by 2031-12-31. NIST recommends ML-KEM-768 as the default parameter set.
- **Symmetric cryptography and hashes are affected less.** IR 8547 says NIST's symmetric standards are "significantly less vulnerable to known quantum attacks" and that every approved symmetric primitive with at least 128 bits of classical strength is believed to reach at least category 1 of its five post-quantum security categories. A few 112-bit symmetric standards will be disallowed in 2030.
- **Hybrids are allowed but expected to be temporary.** IR 8547 describes combining a post-quantum and a classical algorithm so that the result is secure if at least one holds, notes that hybrids "add complexity", and says they are "typically expected to be temporary measures".

What this means for a beginner, kept to what is published: **the first thing NIST asks organizations to do is take an inventory of where quantum-vulnerable algorithms are used** (IR 8547 says to begin with "cryptographic inventories, migration planning, and early deployments"). The project row above that says **None** for such an inventory is the honest state today. Nothing in this repository needs changing on account of the dates above, and I am not proposing a change; what changes with time is the TLS and signature libraries your tools use, which you get by keeping them updated ([Patch management](Patch-Management-and-Automatic-Security-Updates.md)).

A sample from the TLS exercise below shows the transition already in the wild: the connection from my machine on 2026-10-31 negotiated a group named `X25519MLKEM768`. By its name, that pairs X25519 with ML-KEM-768 (est., from the name). It is a sample from one client and one site on one day, not evidence about any other.

## Free path: run the drill, then read a real certificate chain

### Exercise 1: the drill

The script below runs nine small experiments. Save it as `crypto_drill.sh` and run it with `bash crypto_drill.sh`.

```bash
#!/usr/bin/env bash
# crypto_drill.sh - nine small experiments in one throwaway folder. Needs bash, openssl 3.x, gpg, sha256sum, cmp, od, python3.
# It reads nothing outside the folder it makes, opens no connection, and deletes the folder at the end.
# Every demo key is derived at run time from a readable seed, so no key bytes are written in this file.
# The seeds are public, so these keys must never protect anything real.
# Only stable lines are printed: where tools word an error differently by version, a fixed label is printed instead.
set -u
lab="$(mktemp -d)"
export GNUPGHOME="$lab/gnupg"
mkdir -m 700 "$GNUPGHOME"
cleanup() { gpgconf --kill gpg-agent 2>/dev/null; cd / && rm -rf "$lab"; }
trap cleanup EXIT
cd "$lab" || exit 1
hex() { od -An -v -tx1 -w64 | tr -d ' \n'; }
blocks() { od -An -v -tx1 -w16 | tr -d ' ' | awk '{print "block " NR ": " substr($0,1,8) "..."}'; }
derive() { openssl kdf -keylen "$2" -kdfopt digest:SHA256 -kdfopt pass:"$1" -kdfopt salt:demo-salt -kdfopt iter:1000 -binary PBKDF2 | hex; }
AES_K="$(derive demo-seed-one 32)"
AES_K2="$(derive demo-seed-two 32)"
NONCE="$(derive demo-nonce-seed 16)"
label() { if "$@" > /dev/null 2>&1; then echo "$LABEL_OK"; else echo "$LABEL_FAIL"; fi; }

echo "== 1. Hashing: one changed byte, a checksum file, and a keyed hash"
printf 'pay Alice 100 dollars\n' > note.txt
printf 'pay Alice 900 dollars\n' > note-changed.txt
a="$(sha256sum note.txt | cut -d' ' -f1)"
b="$(sha256sum note-changed.txt | cut -d' ' -f1)"
echo "original SHA-256, first 8 hex digits: ${a:0:8}..."
echo "changed SHA-256, first 8 hex digits:  ${b:0:8}..."
[ "$a" != "$b" ] && echo "the two full digests are equal: no"
cmp -l note.txt note-changed.txt | awk '{print "bytes that differ: " NR " (byte " $1 ", octal " $2 " became " $3 ")"}'
same=0
for i in $(seq 0 63); do [ "${a:$i:1}" = "${b:$i:1}" ] && same=$((same + 1)); done
echo "same hex digit in the same place: $same of 64 (about 4 by chance alone)"
sha256sum note.txt > note.sha256
LABEL_OK="checksum check, original file: CHECK-OK" LABEL_FAIL="checksum check, original file: CHECK-FAIL" label sha256sum -c note.sha256
cp note-changed.txt note.txt
LABEL_OK="checksum check, changed file:  CHECK-OK" LABEL_FAIL="checksum check, changed file:  CHECK-FAIL" label sha256sum -c note.sha256
printf 'pay Alice 100 dollars\n' > note.txt
tag() { openssl mac -digest SHA256 -macopt hexkey:"$1" -in "$2" HMAC; }
[ "$(tag "$AES_K" note.txt)" = "$(tag "$AES_K" note.txt)" ] && echo "hmac, same key and same message twice: tags equal"
[ "$(tag "$AES_K" note.txt)" != "$(tag "$AES_K2" note.txt)" ] && echo "hmac, different key: tags differ"
[ "$(tag "$AES_K" note.txt)" != "$(tag "$AES_K" note-changed.txt)" ] && echo "hmac, changed message: tags differ"

echo
echo "== 2. A password is not a key: one password, two salts"
slow() { openssl kdf -keylen 16 -kdfopt digest:SHA256 -kdfopt pass:hunter2 -kdfopt salt:"$1" -kdfopt iter:600000 -binary PBKDF2 | hex; }
[ "$(slow salt-one)" = "$(slow salt-one)" ] && echo "same password and same salt twice: derived keys equal"
[ "$(slow salt-one)" != "$(slow salt-two)" ] && echo "same password and different salts: derived keys differ"

echo
echo "== 3. ECB shows its pattern, CTR does not"
printf 'ATTACK AT DAWN!!ATTACK AT DAWN!!ATTACK AT DAWN!!' > pattern.txt
echo "ECB, first 8 hex digits of each 16-byte block:"
openssl enc -aes-256-ecb -K "$AES_K" -in pattern.txt | blocks
echo "CTR, first 8 hex digits of each 16-byte block:"
openssl enc -aes-256-ctr -K "$AES_K" -iv "$NONCE" -in pattern.txt | blocks

echo
echo "== 4. Encryption without authentication: an attacker edits the ciphertext"
openssl enc -aes-256-ctr -K "$AES_K" -iv "$NONCE" -in note.txt -out note.ctr
echo "ciphertext: $(wc -c < note.ctr) bytes, first 8 hex digits: $(od -An -v -tx1 -w4 -N4 note.ctr | tr -d ' ')..."
echo "decrypted, right key: $(openssl enc -d -aes-256-ctr -K "$AES_K" -iv "$NONCE" -in note.ctr)"
openssl enc -d -aes-256-ctr -K "$AES_K2" -iv "$NONCE" -in note.ctr > wrong.out 2> wrong.err
echo "decrypted with a different key: exit=$?, $(wc -c < wrong.out) bytes, same as the original: $(cmp -s wrong.out note.txt && echo yes || echo no)"
python3 -I -c "
d = bytearray(open('note.ctr', 'rb').read())
d[10] ^= 0x08
open('note-edited.ctr', 'wb').write(d)
"
printf 'edited ciphertext, decrypted: '
openssl enc -d -aes-256-ctr -K "$AES_K" -iv "$NONCE" -in note-edited.ctr
echo "exit=$?"

echo
echo "== 5. Reusing a nonce: two messages, one key, one IV"
printf 'the safe code is 4417\n' > secret.txt
openssl enc -aes-256-ctr -K "$AES_K" -iv "$NONCE" -in note.txt -out c1.bin
openssl enc -aes-256-ctr -K "$AES_K" -iv "$NONCE" -in secret.txt -out c2.bin
python3 -I -c "
c1, c2, known = (open(n, 'rb').read() for n in ('c1.bin', 'c2.bin', 'note.txt'))
x = bytes(a ^ b for a, b in zip(c1, c2))
print('c1 xor c2:', len(x), 'bytes, first 8 hex digits', x.hex()[:8] + '...')
print('known note xor that =', repr(bytes(a ^ b for a, b in zip(x, known))))
"

echo
echo "== 6. Authenticated encryption with gpg: wrong passphrase and edited file are refused"
printf 'demo-passphrase-not-real\n' > pass.txt
chmod 600 pass.txt
printf 'another-wrong-phrase\n' > wrong-pass.txt
gpg_with() { gpg --batch --quiet --pinentry-mode loopback --passphrase-file "$1" "${@:2}"; }
gpg_with pass.txt --symmetric --cipher-algo AES256 --compress-algo none --output note.gpg note.txt
printf 'right passphrase: '
gpg_with pass.txt --decrypt note.gpg 2> /dev/null
LABEL_OK="wrong passphrase: GPG-OK (unexpected)" LABEL_FAIL="wrong passphrase: GPG-REFUSED" label gpg_with wrong-pass.txt --decrypt note.gpg
python3 -I -c "
d = bytearray(open('note.gpg', 'rb').read())
d[-28] ^= 0x01
open('note-edited.gpg', 'wb').write(d)
"
LABEL_OK="edited file: GPG-OK (unexpected)" LABEL_FAIL="edited file: GPG-REFUSED" label gpg_with pass.txt --decrypt note-edited.gpg

echo
echo "== 7. Key exchange: two key pairs, one shared secret, then one symmetric key"
openssl genpkey -algorithm X25519 -out alice.pem
openssl genpkey -algorithm X25519 -out bob.pem
openssl genpkey -algorithm X25519 -out eve.pem
for n in alice bob eve; do openssl pkey -in $n.pem -pubout -out $n.pub; done
openssl pkeyutl -derive -inkey alice.pem -peerkey bob.pub -out alice.shared
openssl pkeyutl -derive -inkey bob.pem -peerkey alice.pub -out bob.shared
openssl pkeyutl -derive -inkey eve.pem -peerkey bob.pub -out eve.shared
cmp -s alice.shared bob.shared && echo "alice and bob derived the same $(wc -c < alice.shared)-byte secret"
cmp -s alice.shared eve.shared || echo "eve, who saw both public keys, derived a different one"
hkdf() { openssl kdf -keylen 32 -kdfopt digest:SHA256 -kdfopt hexkey:"$(od -An -v -tx1 -w64 "$1" | tr -d ' \n')" -kdfopt info:demo-v1 -binary HKDF | hex; }
[ "$(hkdf alice.shared)" = "$(hkdf bob.shared)" ] && echo "an HKDF step turns it into the same 32-byte AES key on both sides"

echo
echo "== 8. A digital signature"
openssl genpkey -algorithm ed25519 -out sign.pem
openssl pkey -in sign.pem -pubout -out sign.pub
openssl pkeyutl -sign -inkey sign.pem -rawin -in note.txt -out note.sig
echo "signature is $(wc -c < note.sig) bytes"
LABEL_OK="original note: VERIFY-OK" LABEL_FAIL="original note: VERIFY-FAIL" label openssl pkeyutl -verify -pubin -inkey sign.pub -rawin -in note.txt -sigfile note.sig
LABEL_OK="changed note:  VERIFY-OK" LABEL_FAIL="changed note:  VERIFY-FAIL" label openssl pkeyutl -verify -pubin -inkey sign.pub -rawin -in note-changed.txt -sigfile note.sig

echo
echo "== 9. A certificate authority in miniature"
openssl genpkey -algorithm ed25519 -out ca.pem
openssl req -x509 -new -key ca.pem -subj "/CN=Demo Root CA" -days 30 -addext "basicConstraints=critical,CA:TRUE" -addext keyUsage=critical,keyCertSign -out ca.crt
openssl genpkey -algorithm ed25519 -out site.pem
openssl req -new -key site.pem -subj "/CN=demo.example.test" -out site.csr
printf 'subjectAltName=DNS:demo.example.test\nbasicConstraints=CA:FALSE\n' > site.ext
openssl x509 -req -in site.csr -CA ca.crt -CAkey ca.pem -CAcreateserial -days 7 -extfile site.ext -out site.crt 2> /dev/null
LABEL_OK="trusted CA, right name:  VERIFY-OK" LABEL_FAIL="trusted CA, right name:  VERIFY-FAIL" label openssl verify -CAfile ca.crt -verify_hostname demo.example.test site.crt
LABEL_OK="trusted CA, wrong name:  VERIFY-OK" LABEL_FAIL="trusted CA, wrong name:  VERIFY-FAIL" label openssl verify -CAfile ca.crt -verify_hostname other.example.test site.crt
LABEL_OK="no trusted CA at all:    VERIFY-OK" LABEL_FAIL="no trusted CA at all:    VERIFY-FAIL" label openssl verify -no-CApath -no-CAfile -no-CAstore site.crt
openssl genpkey -algorithm ed25519 -out rogue.pem
openssl req -x509 -new -key rogue.pem -subj "/CN=Demo Root CA" -days 30 -addext "basicConstraints=critical,CA:TRUE" -addext keyUsage=critical,keyCertSign -out rogue.crt
LABEL_OK="same-name rogue CA:      VERIFY-OK" LABEL_FAIL="same-name rogue CA:      VERIFY-FAIL" label openssl verify -CAfile rogue.crt site.crt

exit 0
```

**Predict.** In experiment 4, the attacker changes one byte of the ciphertext without the key. Will the decryption fail, print garbage, or print something readable? In experiment 6, will `gpg` accept the edited file?

What it printed on 2026-10-31. The script prints only lines that do not depend on the tool version: the keys, nonce and passphrases are fixed by the script, the key pairs in experiments 7 to 9 only appear as equal or unequal, and each pass or fail outcome is a fixed label (`CHECK-OK`, `GPG-REFUSED`, `VERIFY-FAIL` and so on) chosen from the tool's exit status, so the raw error wording never appears. Yours should match line for line:

```text
== 1. Hashing: one changed byte, a checksum file, and a keyed hash
original SHA-256, first 8 hex digits: cbcc2a3b...
changed SHA-256, first 8 hex digits:  c48f4ce3...
the two full digests are equal: no
bytes that differ: 1 (byte 11, octal 61 became 71)
same hex digit in the same place: 7 of 64 (about 4 by chance alone)
checksum check, original file: CHECK-OK
checksum check, changed file:  CHECK-FAIL
hmac, same key and same message twice: tags equal
hmac, different key: tags differ
hmac, changed message: tags differ

== 2. A password is not a key: one password, two salts
same password and same salt twice: derived keys equal
same password and different salts: derived keys differ

== 3. ECB shows its pattern, CTR does not
ECB, first 8 hex digits of each 16-byte block:
block 1: 805bf342...
block 2: 805bf342...
block 3: 805bf342...
block 4: 194f5a0e...
CTR, first 8 hex digits of each 16-byte block:
block 1: 0c5e3aca...
block 2: cc8839d8...
block 3: a5e2e3b9...

== 4. Encryption without authentication: an attacker edits the ciphertext
ciphertext: 22 bytes, first 8 hex digits: 3d6b17ab...
decrypted, right key: pay Alice 100 dollars
decrypted with a different key: exit=0, 22 bytes, same as the original: no
edited ciphertext, decrypted: pay Alice 900 dollars
exit=0

== 5. Reusing a nonce: two messages, one key, one IV
c1 xor c2: 22 bytes, first 8 hex digits 04091c00...
known note xor that = b'the safe code is 4417\n'

== 6. Authenticated encryption with gpg: wrong passphrase and edited file are refused
right passphrase: pay Alice 100 dollars
wrong passphrase: GPG-REFUSED
edited file: GPG-REFUSED

== 7. Key exchange: two key pairs, one shared secret, then one symmetric key
alice and bob derived the same 32-byte secret
eve, who saw both public keys, derived a different one
an HKDF step turns it into the same 32-byte AES key on both sides

== 8. A digital signature
signature is 64 bytes
original note: VERIFY-OK
changed note:  VERIFY-FAIL

== 9. A certificate authority in miniature
trusted CA, right name:  VERIFY-OK
trusted CA, wrong name:  VERIFY-FAIL
no trusted CA at all:    VERIFY-FAIL
same-name rogue CA:      VERIFY-FAIL
```

**Check.** How to read it:

1. **Hashing.** One byte differs (the `1` in `100` became `9`), and the two SHA-256 values look unrelated (the first eight hex digits already differ, and the script confirms the full digests differ). `sha256sum -c` is labeled `CHECK-OK` for the original and `CHECK-FAIL` for the changed file. The same key and message give the same HMAC tag twice; a different key gives a different tag, and so does a changed message. (The script does not print the tags: a tag is derived from a key, and the point is only whether they match.)
2. **Password and salt.** The same password and salt always give the same derived key, and the same password under a different salt gives a different one. (The script prints that conclusion, not the keys.)
3. **ECB.** The first three 16-byte blocks of the ECB output start with the same eight digits (they are identical in full) because the three plaintext blocks are identical. The CTR blocks all start differently. This is the pattern leak.
4. **No authentication.** With a different key, decryption "succeeds" with exit status 0 and produces 22 bytes that are not the original. With the right key and one edited byte, the output is `pay Alice 900 dollars` with no error: the attacker flipped one bit of the ciphertext and the same bit flipped in the plaintext. The attacker never needed the key.
5. **Nonce reuse.** XOR of the two ciphertexts equals the XOR of the two plaintexts, so knowing one message (`pay Alice 100 dollars`) reveals the other (`the safe code is 4417`) without the key.
6. **Authenticated.** A wrong passphrase and an edited file are both refused (`GPG-REFUSED`, chosen from a nonzero exit status), where experiment 4's unauthenticated mode accepted the edit. **Trust the exit status, not the output:** on GnuPG 2.4.7 I saw the edited file print damaged text (`domlars`) before the warning `encrypted message has been manipulated!` and exit status 2. That raw output is not part of the compared text because wording and order differ between versions.
7. **Key exchange.** Alice and Bob derive the same 32-byte secret from each other's public keys. Eve, who knows both public keys, does not. A KDF step then gives both sides the same AES key.
8. **Signature.** A 64-byte signature verifies against the original note and fails against the changed one.
9. **Certificates.** The site certificate verifies (`VERIFY-OK`) for the right name and CA. A wrong name fails, with no trusted CA it fails, and a rogue CA with the same name fails too, because the check follows the signature, not the label. (OpenSSL 3.5.7 worded these as `hostname mismatch` and `unable to get local issuer certificate`; the drill prints labels because the wording differs between versions.)

**Undo.** The script deletes its folder and stops its private `gpg-agent` on exit. Nothing else was changed.

### Exercise 2: read a real TLS certificate chain (needs the internet)

This exercise makes one TLS connection to a public site. The output below is a **sample read on 2026-10-31 (2026-11-01 00:01 UTC)** from my machine. Certificates are renewed, issuers change, and the algorithms negotiated depend on your OpenSSL version, so **your output will differ** and should. What stays the same is how to read it.

```bash
mkdir -p tls-lab && cd tls-lab
openssl s_client -connect example.com:443 -servername example.com -showcerts < /dev/null 2> /dev/null > s_client.txt
grep -E "^ *[0-9] s:|^ *i:|a:PKEY|v:NotBefore" s_client.txt | sed 's/a:PKEY: /a: /'
grep -E "Protocol|Cipher is|Peer signature|Negotiated TLS1.3 group|Verification:|Verify return" s_client.txt
openssl x509 -in s_client.txt -noout -subject -issuer -dates -ext subjectAltName,basicConstraints
openssl x509 -in s_client.txt -noout -text | grep -E "Signature Algorithm|Public Key Algorithm|ASN1 OID|NIST CURVE"
```

The first `grep` (with `sed` shortening OpenSSL's `a:PKEY:` label to `a:`) printed the chain, one block of four lines per certificate (`s:` is the subject, `i:` the issuer, `a:` the public key and the algorithm the issuer signed with, `v:` the dates):

```text
 0 s:CN=example.com
   i:C=US, O=SSL Corporation, CN=Cloudflare TLS Issuing ECC CA 3
   a: EC, (prime256v1); sigalg: ecdsa-with-SHA256
   v:NotBefore: Sep 26 22:49:11 2026 GMT; NotAfter: Dec 25 22:56:35 2026 GMT
 1 s:C=US, O=SSL Corporation, CN=Cloudflare TLS Issuing ECC CA 3
   i:C=US, O=SSL Corporation, CN=SSL.com TLS Transit ECC CA R2
   a: EC, (prime256v1); sigalg: ecdsa-with-SHA384
   v:NotBefore: May 29 19:49:45 2025 GMT; NotAfter: May 27 19:49:44 2035 GMT
 2 s:C=US, O=SSL Corporation, CN=SSL.com TLS Transit ECC CA R2
   i:C=US, O=SSL Corporation, CN=SSL.com TLS ECC Root CA 2022
   a: EC, (secp384r1); sigalg: ecdsa-with-SHA384
   v:NotBefore: Oct 21 17:02:23 2022 GMT; NotAfter: Oct 17 17:02:22 2037 GMT
 3 s:C=US, O=SSL Corporation, CN=SSL.com TLS ECC Root CA 2022
   i:C=GB, ST=Greater Manchester, L=Salford, O=Comodo CA Limited, CN=AAA Certificate Services
   a: EC, (secp384r1); sigalg: sha256WithRSAEncryption
   v:NotBefore: Aug  1 00:00:00 2025 GMT; NotAfter: Dec 31 23:59:59 2028 GMT
```

The second `grep`, the connection summary:

```text
Peer signature type: ecdsa_secp256r1_sha256
Negotiated TLS1.3 group: X25519MLKEM768
Verification: OK
New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384
Protocol: TLSv1.3
Verify return code: 0 (ok)
```

The third and fourth commands read the first (leaf) certificate:

```text
subject=CN=example.com
issuer=C=US, O=SSL Corporation, CN=Cloudflare TLS Issuing ECC CA 3
notBefore=Sep 26 22:49:11 2026 GMT
notAfter=Dec 25 22:56:35 2026 GMT
X509v3 Basic Constraints: critical
    CA:FALSE
X509v3 Subject Alternative Name: 
    DNS:example.com, DNS:*.example.com
        Signature Algorithm: ecdsa-with-SHA256
            Public Key Algorithm: id-ecPublicKey
                ASN1 OID: prime256v1
                NIST CURVE: P-256
    Signature Algorithm: ecdsa-with-SHA256
```

**Check.** Read it like an examiner:

- **Subject and names.** The leaf is for `example.com` and `*.example.com` (the Subject Alternative Name list is what the client actually checks). `CA:FALSE` says this certificate may not sign other certificates.
- **Issuer.** Who vouched: here an intermediate CA, whose own certificate is certificate 1, signed by certificate 2, and so on. Each line's `i:` is the next line's `s:`. The last certificate in the list is a root of the issuing company that an older root (`AAA Certificate Services`) has also signed, which I read as a cross-signature that lets clients who only know the older root still build a chain (est.). A server need not send a root that the client already holds.
- **Validity.** The leaf was valid from 26 September to 25 December 2026, about 90 days. Short lives are deliberate: a stolen key or a mis-issued certificate stops being useful soon. Check today's date lies between the two.
- **Signature algorithm.** `ecdsa-with-SHA256` means the issuer signed a SHA-256 hash of the certificate with an ECDSA key. The public key is on the NIST P-256 curve, which is f=256 in the SP 800-57 table above, so 128 bits of classical strength. All the algorithms in this chain are quantum-vulnerable in the sense of IR 8547 (RSA and ECDSA are in its deprecate-after-2030 table); the key exchange group in the summary is a different matter, and shows a hybrid.
- **Verification.** `Verify return code: 0 (ok)` means the chain led to a trust anchor in **your machine's** store with a valid name and dates. A sample from another network or another OpenSSL could differ.

**Safe-use rules for this page.**

- Run `s_client` only against sites you may connect to as an ordinary visitor. It is a plain handshake. Do not point it at a system you do not own in a loop, and do not use it to test for flaws.
- Never turn certificate verification off to "make a connection work". If it fails, read the error: it is telling you something.
- The demo keys and passphrases here are public. For real work let the tool generate them, keep them out of shell history and process lists (a passphrase on a command line, as in the script, is visible to other users of the machine while it runs), and keep them out of a repository.
- Do not paste a private key, a token or a real passphrase into a chat, an issue or a terminal log. Your public key and a certificate are fine to share.
- Delete the `tls-lab` folder when finished: `cd .. && rm -r tls-lab`.

### A thinking exercise, no commands

Pick one row of the project table above whose status is **None** and answer: what is the data, who would want it, which of the three states (at rest, in transit, in use) is it in, which tool from this page would protect it, and who would hold the key and how would you get it back if that person left? Write the answer in a few sentences. If you cannot name a holder, you have found the next problem.

## Build, break, detect, defend

- **Build.** Run the drill. Make a small CA and a certificate you signed yourself (experiment 9).
- **Break.** Edit a ciphertext and watch the unauthenticated mode accept it (experiment 4). Reuse a nonce and recover a message (experiment 5).
- **Detect.** An authenticated mode, a MAC or a signature turns silent tampering into an error (experiments 6 and 8). In a real system the equivalent is monitoring for certificate-validation failures and for unexpected changes to a host's SSH key.
- **Defend.** Use libraries at their defaults, keep keys apart from data, give secrets a short life, write down who can recover each key, and keep tools updated so the next algorithm transition arrives with an update and not a rebuild.

## Checkpoint

You are done when you can answer these without looking:

1. Name two things encryption alone does not give you, and what gives each.
2. Why does a real connection use both a public-key step and a symmetric cipher?
3. What is the difference between a hash, an HMAC and a signature?
4. Why does a password hash need a salt and a slow function, and why is a password not a key?
5. What does a certificate add to a signature?
6. A disk is encrypted. Name one threat it stops and one it does not.
7. Where are the keys to this project's secrets held, and what happens to a secret that is never rotated?
8. What does NIST say it will do to RSA, ECDSA and Diffie-Hellman after 2030 and after 2035, and what is its first suggested step for an organization?
9. In experiment 6, why must you check the exit status and not only the output?

## Claims register

All pages below were downloaded and read on **2026-10-31**; the NIST pages show the dates given. Status words: Read means I read the text I cite; Listing read means I read the NIST record page (abstract, dates, status notes) but not the document; Run means I ran it; General knowledge or **est.** means I read no source.

| Claim | Source | Status |
|---|---|---|
| Symmetric algorithms use one key to apply and remove or check protection; hashes, block ciphers, KDFs and AEADs are less vulnerable to known quantum attacks than public-key standards; all approved symmetric primitives of at least 128 bits classical strength are believed to meet at least category 1; some 112-bit standards will be disallowed in 2030 | [NIST IR 8547, Transition to Post-Quantum Cryptography Standards](https://doi.org/10.6028/NIST.IR.8547), October 2026; record page [csrc.nist.gov/pubs/ir/8547/final](https://csrc.nist.gov/pubs/ir/8547/final) | Read (PDF text, sections 2.1.3 and 4.1.3) |
| NIST will deprecate RSA, ECDSA, EdDSA, finite-field and elliptic-curve Diffie-Hellman and RSA key establishment after 2030 and disallow them after 2035; ML-KEM-768 is the recommended default; HQC selected and a standard is under development; harvest now, decrypt later; hybrids add complexity and are expected to be temporary; 2030-12-31 and 2031-12-31 federal deadlines for the most sensitive systems; begin with cryptographic inventories | Same document, sections 1, 3.2, 4 and Tables 2 to 5; the executive order and OMB memorandum themselves were not read | Read |
| IR 8547 final is dated October 2026 (history: draft 2024-11-12, final 2026-10-27) | [csrc.nist.gov/pubs/ir/8547/final](https://csrc.nist.gov/pubs/ir/8547/final) and the [initial public draft record](https://csrc.nist.gov/pubs/ir/8547/ipd) | Listing read |
| FIPS 203 (ML-KEM), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA) were released in August 2024 (2024-08-13); Falcon and HQC were selected for ongoing standardization; quantum computers "may be years or decades away"; the project page was updated 2026-10-27 | [NIST Post-Quantum Cryptography project](https://www.nist.gov/pqcrypto) (the short address the project page itself gives; I read the page it leads to on csrc.nist.gov); [FIPS 203](https://csrc.nist.gov/pubs/fips/203/final), [FIPS 204](https://csrc.nist.gov/pubs/fips/204/final), [FIPS 205](https://csrc.nist.gov/pubs/fips/205/final) | Listing read |
| FIPS 203 has an errata note dated 2025-11-17 and FIPS 204 one dated 2026-07-31 | The FIPS 203 and FIPS 204 record pages above | Listing read |
| Comparable security strengths: 112 bits is RSA 2048 or curves of 224 to 255 bits; 128 bits is AES-128, RSA 3072 or curves of 256 to 383 bits; 192 bits is AES-192, RSA 7680, 384 to 511; 256 bits is AES-256, RSA 15360, 512 or more; less than 112 bits no longer approved for protecting federal data; the public-key estimates change when quantum computing becomes practical | [NIST SP 800-57 Part 1 Rev. 5](https://doi.org/10.6028/NIST.SP.800-57pt1r5), May 2020, Table 2 and the text after it | Read (PDF text) |
| SP 800-57 Part 1 Rev. 6 initial public draft, 2025-12-05, adds the post-quantum algorithms, discusses keying material storage and separates key-establishment keys from key-storage keys; comments closed 2026-02-05 | [csrc.nist.gov/pubs/sp/800/57/pt1/r6/ipd](https://csrc.nist.gov/pubs/sp/800/57/pt1/r6/ipd) | Listing read |
| AES-128, -192, -256 acceptable; two-key TDEA and SKIPJACK disallowed for encryption; three-key TDEA disallowed after 2023; SHA-1 not allowed for signature generation except where protocol guidance allows, acceptable for non-signature uses that do not need collision resistance; at least 112 bits required | [NIST SP 800-131A Rev. 2](https://doi.org/10.6028/NIST.SP.800-131Ar2), March 2019 | Read (PDF text) |
| The Rev. 3 draft proposes retiring ECB as a confidentiality mode and a schedule retiring SHA-1 and the 224-bit hashes (deprecated through 2030); its table lists CBC, CFB, CTR, OFB, CCM, GCM and XTS-AES as acceptable and ECB as disallowed for data encryption with legacy use for decryption; the record page shows only the draft | [NIST SP 800-131A Rev. 3 ipd](https://doi.org/10.6028/NIST.SP.800-131Ar3.ipd), 2024-10-21, and [its record page](https://csrc.nist.gov/pubs/sp/800/131/a/r3/ipd) | Read (PDF text); a draft |
| GCM requires that the probability of invoking authenticated encryption with the same IV and key on two distinct inputs be no greater than 2^-32; a repeated IV may allow forgery; "almost as important as the secrecy of the key"; 96-bit IVs recommended; NIST has decided to revise SP 800-38D | [NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final), November 2007 (PDF text read from the NIST publications server; planning note 2024-03-06 from the record page) | Read section 8 and the planning note |
| TLS 1.2 with FIPS-based suites supported by government servers and clients, TLS 1.3 support required by 2024-01-01; the publication is under review | [NIST SP 800-52 Rev. 2](https://csrc.nist.gov/pubs/sp/800/52/r2/final), August 2019; planning note 2026-05-07 | Listing read |
| FIPS 197 (AES) was updated 2023-05-09 with no technical change | [csrc.nist.gov/pubs/fips/197/final](https://csrc.nist.gov/pubs/fips/197/final) | Listing read |
| TLS 1.3 key shares are ephemeral Diffie-Hellman; the hello messages determine the shared keys; the version removes compression, DSA and custom DHE groups | [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446), August 2018 | Read sections 1.2 and 2 |
| X.509 certificates for the internet; trust anchors; the choice of trust anchor is a matter of policy | [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280), May 2008, section 6 | Read |
| HMAC is a keyed-hash MAC construction | [RFC 2104](https://www.rfc-editor.org/rfc/rfc2104), February 1997 | Title and header read; detail not read |
| ChaCha20 nonce "MUST not be repeated for the same key" | [RFC 8439](https://www.rfc-editor.org/rfc/rfc8439), June 2018, section 2.3 | Read |
| Argon2id with t=1 and 2 GiB is the first recommended option, t=3 with 64 MiB the second | [RFC 9106](https://www.rfc-editor.org/rfc/rfc9106), September 2021, section 7.4 | Read |
| Password hashing: Argon2id with at least 19 MiB, 2 iterations, parallelism 1; scrypt, bcrypt and PBKDF2 (600,000 or more, HMAC-SHA-256, if FIPS-140 compliance is required); fast hashes such as SHA-256 not suitable; salts; hash, do not encrypt | [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) (source file read from the OWASP CheatSheetSeries repository) | Read |
| Twingate documents a certificate-pinned TLS tunnel between the client and the connector, and a relay that joins them; the page shows "Last updated 5 months ago", not a date | [Twingate: How Twingate works](https://www.twingate.com/docs/how-twingate-works) | Read |
| The Doppler download uses HTTPS only, TLS 1.2 or newer and a pinned SHA-256; cloud-init pins a package key fingerprint and turns off SSH password login; droplet backups are `false`; the bucket module accepts only a private ACL and sets no encryption; no `encryption` block exists in the `.tf` files; Spacelift holds one Doppler token with a 90-day expiry | The files named in the project table | Read 2026-10-31 (`grep` for `encryption` run over every `.tf` file) |
| The wiki's earlier statements about the provider's automated backups being unencrypted at rest | [Backups, recovery and patching](Backups-Recovery-and-Patching.md#four-words-that-sound-alike) | Read in the repository page; the vendor page was not re-read for this lesson |
| Exercise 1: outputs described | The script above, run on Linux with the versions in the banner | Run 2026-10-31 |
| Exercise 2: certificate chain sample | `openssl s_client` and `openssl x509` against a public site, OpenSSL 3.5.7 | Run once 2026-10-31; a sample, not a fixed result |
| Forward secrecy, Kerckhoffs's principle, hybrid encryption as done by GnuPG and `age`, confidential computing, the name `X25519MLKEM768` | General knowledge | Not read; **est.** |
| Windows and macOS equivalents, PowerShell, `age` | Tool documentation | **Not run** |

Next: [Backups deep dive](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md), on who holds the key to an encrypted backup, then [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) to see which property each control serves.
