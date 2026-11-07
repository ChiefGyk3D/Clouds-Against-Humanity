# Hardware security modules: what they are, and building your own with pico2hsm

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 3: Privacy, anonymity and cryptocurrency](Contents.md#track-3-privacy-anonymity-and-cryptocurrency) > Hardware security modules and building your own with pico2hsm

Previous: [Radio and off-grid communication](Radio-Off-Grid-Communication-LoRa-Meshtastic-Reticulum-Ham-and-SIGINT.md)
<!-- END GENERATED PAGE NAV top -->

A private key kept as a file can be copied, and the copy signs as you from anyone's machine. A hardware security module (HSM) changes that: the key lives inside a device, the device signs on request, and nobody gets the key itself to copy. This page sorts out what that does and does not buy you, how it differs from a TPM, a smart card, a security key and a cloud KMS, what "certified" means, and then looks at pico2hsm, a hobby HSM firmware for the Raspberry Pi Pico 2, a project by its maintainer (https://github.com/mcarey42/pico2hsm).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. Written from reading; nothing was run on a Pico, and the pico2hsm part is a reading of its repository, not a test of it.** On **2026-11-07** these files of the pico2hsm repository were read: README, SECURITY, QUICKSTART, BUILDING (searched, not read through), ARCHITECTURE, LICENSE, the examples README and the sign-in examples, parts of `docs/` (SINGLE_DEVICE_SETUP, PROVISIONING, SECURITY_SUMMARY, AUDIT_2026-10) and the first part of the CHANGELOG, through the GitHub API at commit `07d2d3b` (committed 2026-11-05, 14:21 UTC), the tip of `main` that day. The newest release that day was **v2.2.0**, published 2026-11-02. **Observed:** the software rehearsal in [the exercise](#exercise-a-key-that-has-no-file), Part A, with OpenSSL 3.5.7 on 2026-11-07. **Not run:** every pico2hsm build, flash and device command (the maintainer has not built it and no Pico 2 was available), `pkcs11-tool`, `pcscd`, GnuPG with a card, `ssh` with a PKCS#11 key, and every cloud HSM and KMS product. Standards and vendor statements were read on 2026-11-07 from the pages named in the [claims register](#claims-register); anything that could not be read there is marked **est.** Trust what your terminal prints over what this page says.

> **Prerequisites.** [Cryptography fundamentals](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md), at least its sections on digital signatures and key management. A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)). About 75 minutes for the reading and Part A of the exercise (est.). Part B needs a Raspberry Pi Pico 2 and a USB data cable, about 2 hours the first time (est.), and is **untested**.

> **Where this runs, and the rule.** Part A is OpenSSL on your own computer with a throwaway key. Part B is a USB device on your own computer. Nothing here touches a network service, and no real key, PIN or address appears: every PIN is a placeholder you choose, and the exercise uses a deliberately disposable development configuration. **Do not put a key you care about on a hobby device you built from a lesson.** The exercise is a way to see the shape of an HSM, not a way to guard anything valuable.

## What you will be able to do

- Say what an HSM is, what it protects against (copying the key) and what it does not (someone who can ask it to sign).
- Explain PKCS#11 at concept level: a module, a slot, a token, a session, an object and a login.
- Tell key custody (who can use a key) from key export (who can copy it), and say which question an HSM answers.
- Compare a physical HSM, a cloud HSM and a cloud KMS, and say what you are trusting in each.
- Tell a TPM, an HSM, a smart card and a security key apart, and say which job each is built for.
- Say what FIPS 140 and Common Criteria are, what a validation does and does not prove, and why a homemade device is not certified hardware.
- Describe pico2hsm as its own repository describes it, including what it says it does not protect against.
- Run a software rehearsal of "sign, then verify with only the public key", and (with the hardware) follow the steps for the same thing on a Pico 2.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Keys, signatures, key custody | [Cryptography fundamentals: key management and custody](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md#key-management-and-custody-the-hard-part); [Hashing, encryption and keys: hardware keys](Hashing-Encryption-and-Keys.md#keeping-keys-storage-passphrases-and-hardware-keys) | What a device that does the signing for you is, and how it differs from keeping the key well. |
| An HSM as the place a policy engine asks to sign | [Wallets and key custody: custody](Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md#custody-and-institutional-custody) | The device itself, PKCS#11, certification and a build-your-own. |
| A hardware wallet and its secure element | [Wallets and key custody: the Trezor section](Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md#the-hardware-wallet-i-recommend-trezor) | How that single-purpose device differs from a general-purpose HSM. |
| Phishing-resistant MFA with a security key | [Enterprise identity: MFA](Enterprise-Identity-SSO-SAML-OIDC.md#mfa-and-why-some-mfa-resists-phishing) | Where a security key sits next to the other devices on this page. |
| Where real values live in this project | [Doppler and secrets](Doppler-and-Secrets.md), [Secrets from day one](Secrets-From-Day-One.md) | This project keeps secrets in a secrets manager, not an HSM. The page says when the step up to an HSM is worth it. |

## What an HSM is, and what it protects against

A hardware security module is, in AWS's words, "a computing device that processes cryptographic operations and provides secure storage for cryptographic keys." Two jobs in one box: it **holds** keys and it **uses** them. The caller sends data in, asks for a signature or a decryption, and gets the result back. The key does not travel.

The property that matters is that the key is created inside the device and is not exported in a usable form. Compare the usual case:

```
Key as a file:    thief copies key.pem  ->  signs as you, anywhere, forever
Key in an HSM:    thief reaches the host ->  can ask the device to sign while connected
                                             cannot take the key away and use it later
```

So an HSM protects against **copying the key**. That covers a stolen laptop disk, a leaked backup, a compromised build server's filesystem and a careless commit. It does not protect against someone who can talk to the device while it is plugged in and unlocked: malware on the host can ask for signatures just as you can. What changes is that the access ends when the device is unplugged, locked or revoked, and the key cannot be walked out of the building. A PIN or a quorum in front of the device, and logs of what it signed, are how you limit and see the asking.

What an HSM does not give you:

- **It is not a policy.** If the process that calls it approves anything, the HSM will sign anything. The wallets page makes the same point for custody platforms.
- **It is not a backup.** A key that cannot leave the device is lost with the device unless the design includes a wrapped, encrypted way to copy it to another device. Plan the loss before you rely on it.
- **It is not magic against an attacker holding the device.** Real HSMs resist probing, and some wipe their keys when they detect it (est.); how much of that a given device does is exactly what certification levels measure, below.

## PKCS#11 in concept

PKCS#11 is the long-standing way for programs to talk to a device that holds keys. The current OASIS standard read for this page is version 3.0, dated 15 June 2020; its abstract says it "defines data types, functions and other basic components of the PKCS #11 Cryptoki interface," and it describes Cryptoki as the interface for "devices that hold cryptographic information and perform cryptographic functions." The names you meet are:

| Word | What it is |
|---|---|
| Module (library) | A shared library from the device's maker or a generic driver. The program loads it; on Linux it is a `.so` file. |
| Slot | A place a device can be plugged into (think: a reader). |
| Token | What is in the slot: the device's keys and certificates. |
| Session | An open conversation with a token; a user logs in during a session, usually with a PIN. |
| Object | A key, a certificate or some data on the token, with attributes (a label, an ID, "may sign", "may not be extracted"). |

The standard's own table of contents has sections on slot and token types, session types and object types (read 2026-11-07). The reason it matters to you: **a program that speaks PKCS#11 does not care which device it is.** OpenSSH, OpenSSL, a browser or a code-signing tool loads the module, logs in, names a key by label or ID and asks it to sign. Swap the device and the program does not change. That is also why a hobby device that speaks the same protocol can stand in for an expensive one in a lab.

## Key custody: who can use the key, and who can get it out

Two questions, easy to run together:

1. **Who can use the key** (cause a signature)? Anyone who holds the device and the PIN, or any software they let ask.
2. **Who can get the key out** (copy it)? Ideally nobody, except through a deliberate, encrypted backup path.

An HSM is strongest on the second question. On the first, you still need people and process: who holds the PIN, whether two people must agree (a quorum, built on split knowledge), where the device sits, and what logs exist. The wiki's [wallet custody section](Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md#custody-and-institutional-custody) lays out the same split for money. When a key is the root of trust for other keys, such as a certificate authority root, the custody question is the whole game: get the root key out and every certificate under it is suspect.

## Cloud HSM and KMS versus a device you hold

| Option | What it is | What you trust | Source |
|---|---|---|---|
| Device in your hand | A box or USB token you own | Its maker's design, its firmware, and your physical custody | General knowledge |
| Cloud HSM (for example AWS CloudHSM) | Dedicated HSMs in a provider's data center, single-tenant, FIPS 140-2 or 140-3 Level 3 validated in FIPS mode | The provider runs the hardware and the data plane is not visible to it; you manage users and take on more responsibility than with a managed service | AWS CloudHSM User Guide, read 2026-11-07 |
| KMS (for example AWS KMS) | A managed service where you create and use keys by calling an API; the keys are protected by FIPS 140-3 Security Level 3 validated HSMs and "never leave AWS KMS unencrypted" | The provider's service, its policies and its availability; you hold a key policy, not a device | AWS KMS Developer Guide, read 2026-11-07 |

The honest trade is custody against convenience. A cloud KMS gives you validated hardware, availability and no device to lose, and costs you the fact that the keys live in someone else's service. A device in your hand costs you backup, loss and travel, and gives you physical control and no provider in the path. Neither is better in general; they answer different threat models. Enterprise practice often puts a cloud KMS under an application and an HSM or two under the certificate authority roots (est.).

## TPM, HSM, smart card and security key

| Device | Built for | Typical shape | Notes |
|---|---|---|---|
| TPM | One computer's own trust: measured boot, disk-encryption keys, attestation | A chip on the board, or firmware on the CPU (est.) | The Trusted Computing Group describes it as a "hardware-based root of trust that securely generates and stores cryptographic keys, attesting to the integrity of the platform it runs on." It is tied to one machine. |
| HSM | Many keys, many callers, signing and decrypting at scale | A rack appliance, a PCIe card, a cloud service, or a USB device | General purpose; speaks PKCS#11 and often more. |
| Smart card | One person's credentials: login, email signing, a few keys | A card and reader, or the same chip in a USB token | Speaks APDUs over a standard; PIV and OpenPGP card are two common applications (est.). |
| Security key | Phishing-resistant login for websites | A small USB or NFC key | Built for FIDO2 and WebAuthn: it signs a challenge for one site's origin. See the [Glossary](Glossary.md). Some also do PIV or OpenPGP (est.). |

These blur at the edges, and one device can wear several hats. pico2hsm is a good example: its README says it implements "multiple smartcard applet protocols over USB CCID," so the same board presents as a PKCS#11 HSM (the SC-HSM applet), a PIV card and an OpenPGP card. That is a feature of the project, not the general case.

## Certification: FIPS 140, Common Criteria, and why a hobby device is not certified

**FIPS 140.** FIPS 140-3, published by NIST (document dated March 22, 2019), "provides four increasing, qualitative levels of security: Level 1, Level 2, Level 3, and Level 4," across areas that include physical security, non-invasive security, software and firmware security, sensitive security parameter management, self-tests and life-cycle assurance. It supersedes FIPS 140-2 and aligns with ISO/IEC 19790:2012. A device is **validated**, not merely "compliant," by the Cryptographic Module Validation Program (CMVP), a joint effort of NIST and the Canadian government's national cyber security agency. Accredited independent labs test each module; CMVP began validating to 140-3 on September 22, 2020, stopped accepting new 140-2 submissions after March 31, 2022, and keeps a validated module on its active list for five years. Higher levels require more physical protection (est.): Level 3 is what the cloud services above cite.

**Common Criteria.** A separate international scheme, adopted as ISO/IEC 15408 (the 2022 edition, per the summary read; the Common Criteria portal itself refused the request on 2026-11-07). It evaluates a product against a security target or a protection profile, to an assurance level (est.). It answers "was this product built and tested to claim these properties," not "is it unbreakable."

**Why a hobby device is not certified hardware.** Certification is a paid, lab-run process tied to one specific hardware and firmware version, and it is about the *module*: its physical design as well as its code. pico2hsm runs on an off-the-shelf microcontroller board. Its own SECURITY.md says so in as many words (quoted below). Writing good code does not make a device validated; the validation is a separate act by a lab, on a specific build, and no claim of one was found in the repository files read. That is not a flaw to hide, it is a category: a hobby HSM can be excellent for learning and a lab, and still not be something you could use where a rule says "FIPS validated."

## pico2hsm: what it is

pico2hsm is firmware, written in Rust, for the Raspberry Pi RP2350 microcontroller, by its maintainer. The project is at <https://github.com/mcarey42/pico2hsm> and is **MIT licensed** (the license file names one copyright holder, 2024 to 2026; contributors were not counted). The GitHub description is "SmartCard-HSM firmware for Raspberry Pi Pico 2 (RP2350)." Read the repository for the truth; this section is a signpost, dated 2026-11-07, and its code and documentation are not copied here.

What the README says (read 2026-11-07):

- **A USB smart-card reader that is an HSM.** It speaks smart-card protocols over USB CCID, compatible with OpenSC, `pkcs11-tool`, GnuPG and any PKCS#11 application that supports smart cards.
- **Applets.** SmartCard-HSM (SC-HSM, always on) and PIV are listed as "Hardware-validated"; OpenPGP Card 3.4 is "Hardware-validated"; OpenPGP with Ed25519 and X25519 is listed as "Implemented." The README does not define "hardware-validated"; it reads as "the author tested it on a device," and how was not checked.
- **Boards.** Off-the-shelf RP2350 boards only: the Raspberry Pi Pico 2 (4 MB flash, room for 109 SC-HSM keys, feature flag `pico2_4m`) and several Waveshare boards, some with a 16 MB chip and room for 251 keys. The Pico 2 is the stated primary debug and test target.
- **Key types.** Elliptic-curve keys (P-256, P-384, P-521, secp256k1) always; RSA 2048, 3072 and 4096 with the `rsa` feature; Ed25519 and X25519 in the OpenPGP applet with its feature. Brainpool curves are refused (SINGLE_DEVICE_SETUP).
- **Storage.** A journaled keystore on the board's flash (or a microSD card in some builds). Objects are sealed with AES-256-GCM under a key derived from one-time-programmable (OTP) fuses, so a copy of the flash alone does not open them (README, ARCHITECTURE).
- **PINs.** PIN-protected key use; retry counters are written to flash before each comparison.
- **Backup.** No plaintext export. HSM-to-HSM backup uses a DKEK (a key that wraps other keys) built from one to eight shares; without the share file the keys cannot be restored (ARCHITECTURE, SINGLE_DEVICE_SETUP).
- **Secure boot.** Once a device is provisioned, it verifies the firmware signature before running it. Provisioning writes OTP, which is **permanent**; PROVISIONING.md opens with that warning.
- **Releases.** v1.0.0 on 2026-04-18, v2.0.0 on 2026-10-16 (a breaking storage change: "1.x keys do not carry over"), v2.2.0 on 2026-11-02.

### What the project says it protects against, and what it says it does not

This is the part to read slowly. SECURITY.md's "Threat model summary" says pico2hsm protects against network-level key theft (keys leave only as DKEK-encrypted blobs), unauthorized key use without the PIN, firmware tampering once secure boot is on, and USB eavesdropping to the extent the OS restricts access. It then says what it does **not** protect against, in its own words:

> "physical attackers with flash-read hardware (the RP2350 is a general-purpose microcontroller, not a certified secure element -- OTP row locking improves but does not eliminate the physical attack surface); side-channel attacks on the Cortex-M33 (ECC operations use software implementations without masking or constant-time guarantees beyond what the RustCrypto crates provide, and there is no hardware ECC accelerator); or denial-of-service via USB."

Other limits stated in the repository:

- **Silicon revision.** The README says to use **RP2350 A4** silicon for any business or production use. Revisions A2 and A3 have erratum RP2350-E24, which lets an attacker with the board in hand bypass the secure-boot signature check; A2 also has BOOTSEL glitch errata (E20, E21). A2 and A3 are "fine for a homelab or evaluation." `picotool info -a` prints the revision.
- **Release builds and a blank board.** A release build on a board whose OTP storage secret is not provisioned disables its keystore rather than store keys under a key anyone can compute. For a development board, the QUICKSTART points to a debug build or a release build with the `insecure-dev-keystore` feature, and says: "Never deploy either: the development storage key is public." In that configuration the "key sealed under a device-tied secret" property does not hold, and your exercise key is only as safe as the board on your desk.
- **No per-device PIN salt.** The PIN hashing uses PBKDF2 with a random per-credential salt, but the device-identity part of the salt is a fixed string. The project calls out that extracting both flash and the OTP secret is outside its threat model.
- **Flash replay.** PROVISIONING.md says someone with a clip on the flash chip could write an old image back and roll the store back (a deleted key returns, retry counters reset); the contents stay encrypted.
- **Debug.** A production device with debug left enabled can be read over SWD (PROVISIONING.md).
- **Platforms.** The examples README says Windows is untested and suggests WSL2.

Not found stated, so no claim is made either way: any independent third-party audit (the repository has an internal audit document dated October 2026 and an older security summary labeled a historical snapshot), any FIPS or Common Criteria evaluation, and any statement about how long a given key takes to extract with physical tools.

One more thing worth saying fairly. The README describes the project as "production-grade." SECURITY.md describes the hardware limits plainly, and the second is the better guide to what to use it for: a learning device, a lab, a homelab, and, on A4 silicon with careful provisioning, whatever the owner decides is acceptable. That is the project being honest about itself, and it is more than many hobby projects manage.

## Worked uses

Only the ones the repository supports, with what it says and what was not seen.

| Use | What the repository shows | Status |
|---|---|---|
| **Sign with a key that never leaves the device** | QUICKSTART step 7 and SINGLE_DEVICE_SETUP step 3 and 4 generate an EC P-256 key with `pkcs11-tool`, then sign a test message with the ECDSA-SHA256 mechanism. Example 02 does the key generation as a repeatable script. | Read. Not run. |
| **SSH key** | SINGLE_DEVICE_SETUP, "Use cases": generate a key, then use OpenSSH with the OpenSC PKCS#11 module (`ssh-add -s` or `ssh -I`). | Read. Not run. |
| **Code and release signing** | Example 04 signs a test file with a GnuPG subkey on the OpenPGP applet and says this covers `git commit -S`. It does not mention release artifacts or Authenticode or any platform signing scheme. | Read. Signing a git tag or a tarball with the card follows from GnuPG (**est.**). Not run. |
| **Smart-card login (PIV)** | SINGLE_DEVICE_SETUP lists macOS smart card login, Windows Hello for Business and SSH through PIV middleware. Example 03 signs a challenge with a key in PIV slot 9A. | Read. Not run. |
| **A small lab CA root** | No certificate-authority walkthrough was found in the files read. The route would be a tool that uses a PKCS#11 module to sign certificate requests (OpenSSL with a PKCS#11 provider, for instance), with the root key on the Pico. That is plausible for a device that speaks PKCS#11, but it is **est.** and not something the project documents. | Not stated by the project. **est.** |

The CA case is the interesting one for a lab: a root key you can unplug and put in a drawer is a better teaching model of an offline root than a file on a laptop. If the maintainer tries it, the notes in [the checks section](#for-the-maintainer-checks-to-run-when-you-build-it) say what to record.

## Exercise: a key that has no file

**Goal.** Feel the difference between a key in a file and a key behind a device, using only a signature and its verification.

### Part A: the software rehearsal (observed, no hardware)

This is the same flow as the device version, with the private key as a file so you can see what the HSM removes. It was run on 2026-11-07 with OpenSSL 3.5.7.

```bash
mkdir -p ~/hsmlab && cd ~/hsmlab
echo "hello hsm lesson" > msg.txt

# 1. A software key. This file IS the key; anyone who copies it can sign as you.
openssl ecparam -name prime256v1 -genkey -noout -out soft.pem

# 2. The public half, in the DER form a verifier needs.
openssl pkey -in soft.pem -pubout -outform DER -out pub.der

# 3. Sign, then verify using ONLY the public key.
openssl dgst -sha256 -sign soft.pem -out sig.bin msg.txt
openssl dgst -sha256 -verify pub.der -keyform DER -signature sig.bin msg.txt

# 4. Change the message by one line and verify again: it must fail.
echo "tamper" >> msg.txt
openssl dgst -sha256 -verify pub.der -keyform DER -signature sig.bin msg.txt
```

Expected, and what was observed: `Verified OK` for the first verify, then `Verification failure` and a nonzero exit for the second. Now answer on paper: where is the thing a thief would copy? (`soft.pem`.) In Part B there is no such file for the private key, and that is the whole point.

Clean up: `rm -r ~/hsmlab`.

### Part B: the same on a Pico 2 (UNTESTED)

> **Untested.** Nobody has run these steps. They follow the pico2hsm QUICKSTART and SINGLE_DEVICE_SETUP as read on 2026-11-07. Where this page adds something the repository does not say, it is marked **est.** If a step fails, trust the repository over this page and tell the maintainer so the page can be corrected.

You need a Raspberry Pi Pico 2 (a 4 MB RP2350 board) and a data USB cable (a charge-only cable will not work). Use a spare board: Part B uses a **development** configuration whose storage key is public, and you will not provision it.

1. **Install the tools.** Rust with the `thumbv8m.main-none-eabihf` target, `picotool` version 2.1 or later, `pcscd` and OpenSC (QUICKSTART, step 1 and step 6). Link: <https://github.com/mcarey42/pico2hsm/blob/main/QUICKSTART.md>.
2. **Get the code at a release tag, not the moving tip** (**est.**, advice from this page): clone the repository and check out `v2.2.0`, the release read about on 2026-11-07. The tip of `main` can carry unreleased changes.
3. **Check the silicon.** With the board in BOOTSEL mode, run `picotool info -a` and write down the revision. A2 and A3 are acceptable for a lab per the README; A4 is the one it asks for in production.
4. **Do not provision.** The repository says OTP writes are permanent. Skip secure-boot provisioning entirely for this exercise.
5. **Build a development image.** The default release build disables the keystore on a blank board. QUICKSTART's note offers two ways, a debug build or a release build with the `insecure-dev-keystore` feature, for the `pico2_4m` board. Pick the second if you have no debug probe, and follow QUICKSTART for the exact commands. Whether the signing-key generation step (QUICKSTART step 3) is required for a development image is not clear from the text; do it, since it is harmless on a lab machine, and keep the key file out of version control.
6. **Install the partition table, then the firmware**, with `picotool` in BOOTSEL mode, as QUICKSTART step 5 (Method A) describes. Converting the development ELF into a UF2 is shown in the build note; loading it into partition 0 is the same command shape (**est.**).
7. **Confirm the reader.** `lsusb` and `pkcs11-tool --list-slots` should show a pico2hsm slot (QUICKSTART step 6). If not, check that `pcscd` is running.
8. **Initialize with your own PINs.** QUICKSTART and the examples print sample PINs; do not reuse them, even on a lab device, so the habit is right. Use `sc-hsm-tool --initialize` with a label, a SO-PIN and a user PIN of your choosing and `--dkek-shares 0` (no backup, since this is a throwaway key).
9. **Generate the key on the device.** `pkcs11-tool --login --keypairgen --key-type EC:prime256v1 --id 01 --label lab-key`, entering your PIN when asked.
10. **Sign.** Sign `msg.txt` with the ECDSA-SHA256 mechanism and `--id 01`, writing `sig.bin`.
11. **Get the public key and verify off the device** (**est.**): read the public key object with `pkcs11-tool --read-object --type pubkey --id 01 --output-file pub.der`, then check it with the same `openssl dgst -sha256 -verify` command as Part A. Two things may differ: `pkcs11-tool` may produce a raw signature (r and s side by side) instead of the DER form OpenSSL expects, in which case look for its signature-format option; and the public key file may need converting. Write down what you had to do. That friction is exactly what a PKCS#11 user meets.
12. **Tamper.** Change `msg.txt` by a line and verify again; it must fail, as in Part A.
13. **Look for the private key.** There is no `.pem` on your disk. Try to read the private key object from the token with `pkcs11-tool --read-object --type privkey --id 01`; the expected result is a refusal, not key bytes (**est.**). Do not try more PIN guesses than you need: the device counts wrong PINs, and too many locks it until the SO-PIN resets it.
14. **Unplug and replug**, then list objects with `pkcs11-tool --login --list-objects`. The key should still be there, because it lives in the device's flash.
15. **Clean up.** Delete the lab key, and when you are finished run `sc-hsm-tool --initialize` again, which per SINGLE_DEVICE_SETUP erases SC-HSM keys and domain records. Delete your `~/hsmlab` files.

**What you should be able to say afterward:** the private key was never in a file you could copy; the device signed, and the verifier needed only the public key; and the tamper check failed the way Part A's did. Then say what a development image cost you: the board's storage key is public, so this device protects against nothing physical.

**Going further, still untested:** the repository's example 04 (GnuPG signing) and the SSH steps in SINGLE_DEVICE_SETUP are the next two uses. If you try the lab-CA idea, treat the root key as disposable.

## For the maintainer: checks to run when you build it

Not done yet; this is the list to work through when the hardware is on the bench, so the exercise and this page get corrected from what the terminal prints. Record the exact versions of every tool.

1. Pin the release (`v2.2.0` or whatever is newest) and note the commit. Confirm the README, QUICKSTART and this page still agree on the build path.
2. On a Pico 2, run `picotool info -a` and record the silicon revision. Confirm the README's A2/A3/A4 guidance matches what you have.
3. Follow QUICKSTART steps 1 to 6 as written. Note every step that needs something the document does not mention.
4. Is the signing key from QUICKSTART step 3 required for a development image, or does the build skip signing without it? Does `insecure-dev-keystore` need the key?
5. Does the UF2 conversion in the dev-keystore note load with `picotool load -p 0 -x`, or does the dev image need something else? Does the board enumerate as a CCID reader?
6. Run Part B steps 8 to 14. In particular: the signature format `pkcs11-tool` writes, the exact command that lets OpenSSL verify it, and what `--read-object` on the private key returns.
7. Time the key generation for P-256, and one RSA-2048 key if you build with `rsa` (the README says RSA generation uses a pre-generated pool; examples say OpenPGP RSA-4096 can take up to 16 minutes).
8. Run the repository's `examples/01` to `04` scripts and note which pass. Example 04 is interactive in part.
9. Try the SSH use from SINGLE_DEVICE_SETUP with a lab account on a machine you own, and record the command that worked.
10. Try the lab-CA idea once, with a throwaway root: sign a CSR with the Pico key through a PKCS#11 provider for OpenSSL. This is the one the project does not document, so write down every step.
11. After a plug and replug, confirm the key persists. Try the wrong PIN once and confirm the counter drops; do not exhaust it unless you are ready to reset with the SO-PIN.
12. Confirm which of the "hardware-validated" claims you can reproduce yourself, and tell the author what you find.
13. Update this page: change the status banner, replace each **est.** with what you saw, and remove the "untested" marks you earned.

## Checkpoint

Without looking back: say in one sentence what an HSM protects against and what it does not; name the five words of a PKCS#11 session (module, slot, token, session, object) and what each is; say why an HSM is not a backup; explain the difference between a TPM and an HSM; say who you trust in a cloud KMS versus a device in your hand; and say why a board running open firmware is not FIPS validated, even if the code is excellent.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "The key is in a hardware device, so it is safe" | It cannot be copied. It can still be used by anyone who can talk to it and has the PIN | Who holds the PIN and what software may ask the device |
| "An HSM is my backup" | A key that cannot leave is lost with the device unless a wrapped backup exists | Set up and test a restore before you rely on it |
| "Open firmware on a Pico is an HSM, so it is as good as an appliance" | Different physical protection, no certification, no side-channel hardening | The project's own SECURITY.md |
| "FIPS compliant" and "FIPS validated" mean the same | Validated means a lab tested a specific module and CMVP listed it | The CMVP validated modules list |
| "A development image is just a build option" | `insecure-dev-keystore` uses a public storage key | QUICKSTART's note; never deploy one |
| "I'll provision it to see what happens" | OTP writes are permanent and can leave a board that accepts only your signed firmware | PROVISIONING.md section 1, before touching a board |
| "The sample PIN is fine because it's a lab" | The sample values are published in the docs | Use your own and keep the habit |
| "A TPM and a security key are the same thing" | A TPM is tied to one computer; a security key goes with you | The table above |

## Claims register

Retrieved 2026-11-07 with read-only requests. "Read" means the page or file text was read. "Observed" means it was run. Pages that could not be read are marked.

| Claim | Source | Status |
|---|---|---|
| pico2hsm is SmartCard-HSM firmware for Raspberry Pi Pico 2 (RP2350), Rust, MIT license, created 2026-04-05, `main` at commit `07d2d3b` on 2026-11-05 | [GitHub API: repository metadata](https://github.com/mcarey42/pico2hsm) | Read |
| Latest release v2.2.0, 2026-11-02; v2.0.0 on 2026-10-16 broke key compatibility with 1.x; v1.0.0 on 2026-04-18 | [Releases](https://github.com/mcarey42/pico2hsm/releases), README ("2.0.0: breaking") | Read |
| Applets and statuses (SC-HSM, PIV, OpenPGP "Hardware-validated"; Ed25519 "Implemented"); USB CCID; compatible with OpenSC, pkcs11-tool, GnuPG | [README](https://github.com/mcarey42/pico2hsm/blob/main/README.md) | Read. What "hardware-validated" involved: not stated |
| Supported boards, key counts (109 on a 4 MB Pico 2, 251 on 16 MB) and the Pico 2 as primary debug and test target | README, supported boards table | Read |
| Key types: P-256, P-384, P-521, secp256k1; RSA with the `rsa` feature; Brainpool refused | README feature flags, [SINGLE_DEVICE_SETUP](https://github.com/mcarey42/pico2hsm/blob/main/docs/SINGLE_DEVICE_SETUP.md) | Read |
| No plaintext export; backup is DKEK-wrapped; without the share file keys cannot be restored | [ARCHITECTURE](https://github.com/mcarey42/pico2hsm/blob/main/ARCHITECTURE.md), SINGLE_DEVICE_SETUP | Read |
| Storage sealed with AES-256-GCM under a key derived from OTP fuses | README, ARCHITECTURE section 7 | Read |
| What it protects against and does not (physical flash-read attackers, side channels, USB denial of service); "not a certified secure element" | [SECURITY.md](https://github.com/mcarey42/pico2hsm/blob/main/SECURITY.md) | Read |
| RP2350 A4 for business or production; A2/A3 erratum RP2350-E24 bypasses secure-boot signature check; A2/A3 acceptable for homelab | README, SECURITY.md, [PROVISIONING](https://github.com/mcarey42/pico2hsm/blob/main/docs/PROVISIONING.md) section 1 | Read. Erratum details: the project's, not checked against Raspberry Pi's pages |
| Release builds on an unprovisioned board disable the keystore; `insecure-dev-keystore` uses a public key and must never be deployed | [QUICKSTART](https://github.com/mcarey42/pico2hsm/blob/main/QUICKSTART.md), ARCHITECTURE section 7 | Read |
| Provisioning writes OTP and is permanent; flash replay can roll the store back; debug left enabled exposes RAM | PROVISIONING section 1 | Read |
| Windows is untested for the examples | [examples README](https://github.com/mcarey42/pico2hsm/blob/main/examples/README.md) | Read |
| Use cases: SSH via the OpenSC PKCS#11 module, OpenPGP via GnuPG, PIV; example 04 signs with a GnuPG subkey | SINGLE_DEVICE_SETUP "Use cases", examples 02 to 04 | Read. Not run |
| No third-party audit or FIPS/CC evaluation stated in the files read; an internal October 2026 audit document exists | [AUDIT_2026-10](https://github.com/mcarey42/pico2hsm/blob/main/docs/AUDIT_2026-10.md), SECURITY_SUMMARY | Read. Absence of a claim: selected files were read, not the whole repository |
| An HSM "processes cryptographic operations and provides secure storage for cryptographic keys"; CloudHSM is single-tenant, FIPS 140-2 or 140-3 Level 3 validated in FIPS mode; data plane is not visible to AWS; customer takes more responsibility | [AWS CloudHSM User Guide: What is AWS CloudHSM?](https://docs.aws.amazon.com/cloudhsm/latest/userguide/introduction.html) | Read |
| AWS KMS keys are protected by FIPS 140-3 Security Level 3 validated HSMs and never leave KMS unencrypted | [AWS KMS Developer Guide](https://docs.aws.amazon.com/kms/latest/developerguide/overview.html) | Read |
| PKCS#11 v3.0 OASIS Standard, 15 June 2020; defines the Cryptoki interface; slot, token, session and object sections | [PKCS #11 Specification v3.0](https://docs.oasis-open.org/pkcs11/pkcs11-base/v3.0/os/pkcs11-base-v3.0-os.html) | Read (abstract and table of contents) |
| FIPS 140-3: four increasing qualitative levels, the areas covered, supersedes 140-2, dated March 22, 2019, aligns with ISO/IEC 19790:2012 | [FIPS 140-3 (NIST)](https://doi.org/10.6028/NIST.FIPS.140-3) | Read |
| CMVP: NIST and the Canadian government's national cyber security agency; independent NVLAP-accredited labs; 140-3 validation from 2020-09-22; no new 140-2 submissions after 2022-03-31; five-year active list | [NIST CMVP](https://csrc.nist.gov/projects/cryptographic-module-validation-program) | Read |
| Higher FIPS levels require more physical protection; Level 3 is what the cloud services cite | FIPS 140-3 text (levels), AWS pages (Level 3) | Level 3 cited by AWS: Read. What each level requires physically: **est.** |
| Common Criteria is adopted as ISO/IEC 15408:2022 | [Wikipedia: Common Criteria](https://en.wikipedia.org/wiki/Common_Criteria) (the portal returned 403) | Read (secondary source). Evaluation levels and protection profiles: **est.** |
| A TPM is a "hardware-based root of trust that securely generates and stores cryptographic keys, attesting to the integrity of the platform"; TPM 2.0 Library Specification, version 185, March 2026; implements ISO/IEC 11889 | [Trusted Computing Group: TPM 2.0 Library](https://trustedcomputinggroup.org/resource/tpm-library-specification/), [Wikipedia: Trusted Platform Module](https://en.wikipedia.org/wiki/Trusted_Platform_Module) | Read |
| Security keys sign a challenge for one site (FIDO2); smart cards carry PIV and OpenPGP applications; HSMs in the CA-root role | [Glossary: FIDO2](Glossary.md), general knowledge | General knowledge. Roles marked **est.** in the text |
| The OpenSSL sign and verify flow in Part A, including the failure on a changed message | OpenSSL 3.5.7, run 2026-11-07 | Observed |
| `pkcs11-tool` options for reading a public key and the signature format; OpenSSL with a PKCS#11 provider for a CA; what happens on reading a private key object | none read | **est.** Not run |

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 3: Privacy, anonymity and cryptocurrency](Contents.md#track-3-privacy-anonymity-and-cryptocurrency) > Hardware security modules and building your own with pico2hsm

Previous: [Radio and off-grid communication](Radio-Off-Grid-Communication-LoRa-Meshtastic-Reticulum-Ham-and-SIGINT.md)

In this track: [Track 3: Privacy, anonymity and cryptocurrency](Contents.md#track-3-privacy-anonymity-and-cryptocurrency), 20 pages

- Cryptography and privacy: [Cryptography fundamentals](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md) / [Privacy, security and anonymity](Privacy-Security-and-Anonymity-Three-Different-Things-and-Why-There-Is-No-Silver-Bullet.md) / [Privacy versus security](Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero.md) / **Hardware security modules and building your own with pico2hsm**
- Tor, I2P, VPN and browsing: [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md) / [How a VPN works](How-a-VPN-Works-Tunnels-What-It-Hides-What-It-Does-Not-and-What-an-Audit-Proves.md) / [How Tor works in depth](How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services.md) / [How I2P works](How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database.md) / [The browsing setups compared](The-Browsing-Setups-Compared-Tor-Browser-Brave-Whonix-Tails-and-Qubes-with-Whonix.md) / [OPSEC for Tor and I2P](OPSEC-for-Tor-and-I2P-That-Holds-Up-Identities-Layers-Metadata-and-Habits.md) / [Hands-on Whonix and Qubes OS](Hands-On-Whonix-and-Qubes-OS-Gateway-Split-Compartments-Disposables-and-Policy-Prompts.md) / [The darknet landscape: markets, OPSEC and layering](The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN.md) / [Lab: publish a web server as an onion service and an I2P site](Lab-Publish-a-Web-Server-as-a-Tor-Onion-Service-and-an-I2P-Site-Time-Boxed-and-Defensive.md)
- Cryptocurrency: [Blockchain fundamentals](Blockchain-Fundamentals-Hashes-Blocks-Nodes-Consensus-and-Forks.md) / [How Bitcoin works](How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable.md) / [How Monero works](How-Monero-Works-Compared-with-Bitcoin-and-Ethereum-DeFi-Mixers-Swaps-and-Ransomware.md) / [Wallets and key custody](Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md) / [Paper wallets and offline key generation](Paper-Wallets-Generators-and-Offline-Key-Generation-Tails-Electrum-and-Monero.md) / [Running Monero properly](Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR.md)
- Radio and off-grid: [Radio and off-grid communication](Radio-Off-Grid-Communication-LoRa-Meshtastic-Reticulum-Ham-and-SIGINT.md)

Related pages:

- [Cryptography fundamentals](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md)
- [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)
- [Wallets and key custody](Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md)
- [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md)
- [Doppler and secrets](Doppler-and-Secrets.md)
<!-- END GENERATED PAGE NAV bottom -->
