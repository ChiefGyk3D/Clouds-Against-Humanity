# Hardware security keys: YubiKey, Nitrokey, smart cards, PIV and a firmware you cannot update

> **Status: unverified draft. No hardware key was available, so no key-based step was run.** On **2026-11-07** I ran the two no-hardware exercises on one Linux machine, in scratch directories, as an ordinary user: a software PKCS#11 token (SoftHSM 2.6.1 with OpenSC 0.26.1's `pkcs11-tool`, unpacked from the distribution packages and not installed) and a throwaway GnuPG 2.4.7 home. I ran them on the host, not inside a VM, though the page tells you to use a VM. **Not run:** every step with a real YubiKey or Nitrokey (registering on a site, `ykman`, `nitropy`, PIV or OpenPGP on a card, SSH with a key on a token), and the instructions for your operating system's installer. Vendor and advisory statements were read on **2026-11-07** from the pages in the [claims register](#claims-register); a claim I could not read there is marked **est.** Trust what your terminal prints over what this page says.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Prerequisites.** [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) for what a key pair and a signature are. A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)). A virtual machine for the free exercise ([Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md)). About 90 minutes for the reading and the free exercises (est.); the hardware exercise adds about 30 minutes and about the price of two keys.

> **Where this runs, and the rule.** The free exercises are local and throwaway: a scratch directory, test PINs written in the commands, no account, no network. The hardware exercise uses an account you create for it and can delete. Never practice on a key that already guards a real account, and never reset a key you depend on. A reset is permanent.

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Hardware security keys: YubiKey, Nitrokey, PIV

Previous: [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) / Next: [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md)
<!-- END GENERATED PAGE NAV top -->

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says (and the gap)](#what-the-wiki-already-says-and-the-gap)
- [Five protocols in one small device](#five-protocols-in-one-small-device)
- [What a YubiKey does](#what-a-yubikey-does)
- [Nitrokey, the open alternative](#nitrokey-the-open-alternative)
- [Which protocol for which job](#which-protocol-for-which-job)
- [PINs, retry counters and what a reset does](#pins-retry-counters-and-what-a-reset-does)
- [Two keys, minimum, and the rest of the habits](#two-keys-minimum-and-the-rest-of-the-habits)
- [The YubiKey 5 side-channel vulnerability (EUCLEAK)](#the-yubikey-5-side-channel-vulnerability-eucleak)
- [The double edge: firmware that cannot be updated](#the-double-edge-firmware-that-cannot-be-updated)
- [Exercise 1 (no hardware): a PIN-protected key that cannot leave the token](#exercise-1-no-hardware-a-pin-protected-key-that-cannot-leave-the-token)
- [Exercise 2 (no hardware): OpenPGP with separate sign, encrypt and authenticate keys](#exercise-2-no-hardware-openpgp-with-separate-sign-encrypt-and-authenticate-keys)
- [Exercise 3 (hardware, not run): register a key on a throwaway account](#exercise-3-hardware-not-run-register-a-key-on-a-throwaway-account)
- [Build, break, detect, evade, defend](#build-break-detect-evade-defend)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

## What you will be able to do

- Say in one sentence each what FIDO2/WebAuthn, U2F, OTP, OpenPGP card, PIV and a smart card are, and which job each is for.
- List what a YubiKey 5 Series does, say what a Security Key Series key does not, and say how Nitrokey 3 differs.
- Pick the protocol for a job: a website login, an SSH login, signing a Git commit, a computer login, a one-time code.
- Set up two keys properly: where the second lives, which PINs exist, what happens when a counter runs out, what to do with recovery codes.
- Explain the YubiKey 5 firmware side-channel vulnerability (CVE-2024-45678, advisory YSA-2024-03): what an attacker needs, what it breaks and what it does not.
- Argue both sides of "the firmware cannot be updated", and say why that is still a defensible design and what it costs you.
- Run a PIN-protected, non-exportable key through a software token, and a GnuPG key with separate signing, encryption and authentication subkeys, without buying anything.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| A hardware key holds the private key and signs on request; origin binding is what resists phishing; SSH, PIV and OTP do not check the site | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#keeping-keys-storage-passphrases-and-hardware-keys) | What each protocol on the key actually is, and how to choose. Not repeated. |
| Buy two, register both, keep one off the keyring, recovery codes in the password manager | [Build it from zero, step 0](Build-It-From-Zero-Accounts-to-Stage-1.md#step-0-make-a-mistake-impossible-to-be-expensive) | The reasons behind each part, the PIN and counter details, and a worked setup. The short rule is not repeated. |
| MFA beats no MFA, and FIDO/WebAuthn is the phishing-resistant kind | [Secrets from day one](Secrets-From-Day-One.md#the-loop-protecting-the-thing-that-protects-everything); [Enterprise identity: MFA](Enterprise-Identity-SSO-SAML-OIDC.md#mfa-and-why-some-mfa-resists-phishing) | Not repeated. This page starts where they stop: what is inside the key, and what can go wrong with the key itself. |
| A hardware wallet keeps keys in a device | [Wallets and key custody](Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md#what-a-hardware-wallet-protects-and-what-it-does-not) | Same idea, different job. This page is about login and signing keys. |
| Firmware you cannot update, and a vulnerability you cannot patch | nowhere | The whole [second half of this page](#the-yubikey-5-side-channel-vulnerability-eucleak). |

## Five protocols in one small device

A security key is a small computer with a secure chip inside. It stores private keys, signs when asked and refuses to hand the keys over. What differs between "FIDO2", "PIV" and "OpenPGP" is the language the computer uses to ask. One YubiKey speaks several of those at once, and each one has its own storage, its own PIN and its own reset.

| Protocol | In plain words | Typical job | Resists phishing? |
|---|---|---|---|
| **FIDO2 / WebAuthn** | The browser asks the key to sign a challenge for one website. The key makes a different key pair for each site and signs only for the address it was registered at. CTAP is the language between browser and key. | Logging in to websites: as a second factor, or instead of a password (a passkey). | Yes, because of the origin check. |
| **U2F** | The older FIDO standard: second factor only, no PIN, no passwordless. Still works on most sites. | A second factor on sites that predate FIDO2. | Yes, same origin check. |
| **OTP** | The key types a one-time code when you touch it (Yubico OTP), or holds the secrets for the six-digit TOTP codes an authenticator app makes (OATH). | Sites and apps that accept codes but not keys. | No. A code can be typed into a fake site. |
| **OpenPGP card** | The key pretends to be an OpenPGP smart card, so GnuPG keeps its signing, encryption and authentication keys inside it. | Signing Git commits and email, decrypting files, SSH logins through gpg-agent. | No site is involved, so the question does not apply. |
| **PIV** | The US government's smart card standard (NIST SP 800-73): numbered slots hold keys and certificates, behind a PIN. | Computer and domain logins, client TLS certificates, signing, SSH through PKCS#11, an organization's own certificate authority. | Same. It proves a key, not a website. |

**A smart card** is a credit-card-sized chip with its own processor that holds keys, checks a PIN and does the signing inside. You never see the key. A security key is the same idea in a different body: when a YubiKey says "smart card" it means it speaks PIV (and the OpenPGP card protocol) to the computer through the same driver interface a card reader would use.

Two things to hold on to. First, **phishing resistance belongs to FIDO2 and U2F**, not to hardware in general. A YubiKey used as a typing OTP button is hardware, and it can be phished. Second, **each protocol is a separate store.** Resetting the OpenPGP part does nothing to the FIDO part. The slot limits you will read below are per application.

## What a YubiKey does

Yubico makes several series. This is what their pages said on **2026-11-07**, so check the page again before you buy:

- **YubiKey 5 Series:** "multi-protocol support; FIDO2, U2F, smart card, OTP, OpenPGP 3", in USB-A, USB-C, NFC and Lightning versions, rated IP68 and crush resistant, with no battery and no moving parts. This is the one that does everything in the table above.
- **Security Key Series:** the page offers it for people "interested in using only FIDO2/WebAuthn or FIDO U2F". It is the cheaper, narrower key. The page frames it as FIDO-only, so expect no PIV, OpenPGP or OTP; I did not find a feature table, so the exact list is **est.**
- **YubiKey Bio Series** (fingerprint instead of a PIN), **YubiKey 5 FIPS** (certified for US government use) and **YubiHSM 2** (a server-side module, not a key you carry) exist too. The FIPS series with firmware 5.7.4 is listed as NIST certified for FIPS 140-3 from 22 May 2026.

What the YubiKey 5 Series holds, from the Yubico technical manual (read 2026-11-07):

| Application | What it stores | Limits worth knowing |
|---|---|---|
| FIDO2 | Passkeys (discoverable credentials) | Up to 25 on older firmware, 100 on firmware 5.7 and later. A PIN you set yourself. Eight wrong PIN tries lock the FIDO2 application, and only a FIDO2 reset unlocks it. A reset also resets U2F. |
| OATH | TOTP and HOTP secrets for code generators | 32 on older firmware, 64 on 5.7 and later. |
| OTP | Yubico OTP and similar | Two slots. Slot 1 comes loaded at the factory with a Yubico OTP credential; a short touch fires slot 1, a three-second touch fires slot 2. |
| PIV | Keys and certificates in numbered slots (9A, 9C, 9D, 9E and retired slots) | Firmware 5.7 and later adds RSA 3072 and 4096, Ed25519 and X25519. The PIN, PUK and management key all ship with published default values. |
| OpenPGP | Three keys: sign, encrypt, authenticate | Version 3.4 of the card spec from firmware 5.2.3. RSA-2048, 3072, 4096 and several elliptic curves including Ed25519. Published default PINs here too. |

Yubico's own tech manual says the default PIV PIN, PUK and management key, and the default OpenPGP PINs, are public, and urges you to change them before any real use. Anyone can look them up, so a card still on its defaults has no PIN worth the name.

**Touch.** PIV and OpenPGP can be set to need a touch of the key for each use. That matters more than it sounds: it means malware on your computer cannot quietly use the key while it is plugged in. It can ask, but you will see the light and feel the key ask for your finger.

## Nitrokey, the open alternative

Nitrokey is a German company (the site says it is developed and produced primarily in Berlin). Its pitch, from its own pages read 2026-11-07, is that "both hardware and software are open-source" and so open to independent security review. That is the company's claim, not something I audited. What I did read in the Nitrokey 3 documentation:

- **Features:** FIDO2, U2F, OpenPGP card, PIV, TOTP and a password safe, on one key. Each feature has its own PIN.
- **Secure element:** the FAQ says the SE050M secure element in the Nitrokey 3 is Common Criteria EAL 6+ certified "up to the OS level", and that OpenPGP uses it by default since firmware v1.7.0. So the open part sits on top of a chip whose insides are not open (that last point is **est.**; I did not read the chip vendor's terms).
- **Updatable firmware.** The Nitrokey 3 has a documented firmware-update procedure. The docs say images are signed and checked by the host tool and by the device before an update and on every boot, and that the firmware cannot be downgraded: you can only install the same or a higher version. That is the opposite design choice to Yubico's, and it comes back in [the double edge](#the-double-edge-firmware-that-cannot-be-updated).
- **No ordinary storage.** It holds keys and certificates, not files.

Open source is not a security result. It means a reviewer can read it, not that anyone did, and not that the device you hold was built from what they read. It does mean that if you care about being able to look, the option exists. I only checked these two vendors. Others make FIDO keys too, and the rules below apply to any of them.

## Which protocol for which job

| Job | Use | Why |
|---|---|---|
| Logging in to a website | FIDO2/WebAuthn (a passkey on the key, or the key as second factor) | The only option here that checks the website. |
| A site that only takes a TOTP code | OATH on the key through an authenticator app, or a phone app | It is not phishing resistant. Better than SMS, worse than a key. |
| SSH to a server | OpenSSH's FIDO key types, or an OpenPGP or PIV key through the agent | See [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#keeping-keys-storage-passphrases-and-hardware-keys) for the `ed25519-sk` note and the catch about decrypting files. |
| Signing Git commits or email | OpenPGP card | That is what the protocol was built for. |
| Logging in to a managed computer or domain | PIV | The operating systems and directory products speak smart card. |
| A backup login for a service that takes only a password | Recovery codes in the password manager | Not a key job. |

When a site offers both a security key and an app code, register the key, keep the app code as a fallback only if the site makes you, and remove SMS if you can. On a site that offers it, turn on "require a PIN" for the key. That brings us to PINs.

## PINs, retry counters and what a reset does

A key without a PIN protects you against a stolen password. A key with a PIN protects you against a stolen password and a stolen key. Set it.

- **Each application has its own PIN or PINs.** FIDO2 has one. PIV has a PIN, a PUK (to unblock the PIN) and a management key (to change what is stored). OpenPGP has a user PIN and an admin PIN. Mixing them up is the commonest self-inflicted problem.
- **Every PIN has a retry counter.** Guess wrong enough times and the application locks. For FIDO2 on a YubiKey 5 the manual says eight. For PIV and OpenPGP the counts are lower (the common default is three; I did not read it for this page, so **est.**). Check the number with the vendor tool before you rely on it.
- **A lock is not a catastrophe if you planned it.** The way back is a reset, and a reset wipes the application's keys (**est.** for PIV and OpenPGP; I read it only for FIDO2, where a reset is the unlock). That is why the second key and the recovery codes exist: the lock then costs you one key, not the account.
- **Do not change the PIN on a schedule.** The Yubico manual says there is no security benefit to regular PIN changes unless you think it is compromised, because the PIN only unlocks the key and the key limits guessing. Change it when you suspect it leaked.
- **Use a PIN you can type from memory.** Do not write it on the key or keep it with the key.
- **Hardware does the counting.** That is the part you cannot fake in software, as exercise 1 shows.

## Two keys, minimum, and the rest of the habits

Yubico's own manual says why in plain words: a lost key is a lockout, and "Yubico recommends registering a minimum of two YubiKeys on each web site you use". So:

1. **Buy two of the same model.** Same behavior, same PIN habits, and either one can be the spare.
2. **Register both on every account at setup time, not later.** Later is when you will have lost one. Do it the minute you create the account, which is also why [Build it from zero](Build-It-From-Zero-Accounts-to-Stage-1.md#step-0-make-a-mistake-impossible-to-be-expensive) says so.
3. **Keep the backup apart from the daily key.** A different room is the floor: a drawer at home. A different building is better, since the fire that takes one takes both if they share a keyring and a bag. A safe or a safe-deposit box is plenty. Remember that a backup key you cannot reach on the day you need it is not a backup.
4. **Register on everything that offers it, and keep a list.** The list holds site names and dates, never PINs. It is how you know where to remove a key that is lost. The key cannot tell you, because for FIDO the registrations live on the sites.
5. **Store recovery codes in the password manager, and print one copy for the safe.** Test that you can sign in with a recovery code once, on a throwaway account first, because a code you have never used is a guess.
6. **Lost or stolen key: remove it from every account first, then order a replacement.** Yubico's advice in the advisory discussed below is the same: deregister a lost or stolen key from all services promptly.
7. **Know what firmware you bought.** Yubico Authenticator shows it (the advisory says so), and `ykman info` should too (**est.**, not run). Keep it in the list next to the registrations.

A note on buying. Buy from the vendor or a seller you trust, sealed, and treat a used key as hostile. Everything above assumes the key you hold is the one the maker built. That is outside what you can check from a terminal.

**Disclosure, plainly.** The link below is an Amazon affiliate link: if you buy through it, I may earn a commission, at no extra cost to you. This lesson is not a sales page, it would read the same without the link, and the advice is the same if you buy from Yubico, from Nitrokey, or from anywhere else. When I checked it redirected to a Yubico key listing on Amazon, and listings change, so check that the model in it matches what you need from the table above before you pay. It is the only affiliate link on this page. [Yubico keys on Amazon (affiliate link)](https://amzn.to/3PSRPp7).

## The YubiKey 5 side-channel vulnerability (EUCLEAK)

Nothing here is infallible, and this is the case that proves it for a widely used key.

**What was found.** On **2024-04-19** Dr. Thomas Roche of NinjaLab told Yubico about a side-channel flaw in a cryptographic library from Infineon, the maker of the secure chip inside the YubiKey 5 (an Infineon SLE78, per NinjaLab). NinjaLab named the attack **EUCLEAK**. The flaw is a modular inversion that does not take the same time every run, so a signing operation leaks a little through its electromagnetic emissions. NinjaLab's write-up says the bug went unnoticed for 14 years and about 80 top-level Common Criteria evaluations, that a few local electromagnetic captures (minutes, they say) are enough to extract the ECDSA private key, and that they demonstrated it on a YubiKey 5Ci. For FIDO, extracting the key lets the attacker clone the credential.

**Official identifiers.** Yubico published advisory **YSA-2024-03** on **2024-09-03**, "Infineon ECDSA Private Key Recovery", and rated it moderate at **CVSS 4.9**. The CVE is **CVE-2024-45678**. The advisory page said "in process" when published; NinjaLab says its own CVE request was rejected and MITRE used this number. The NIST entry for the CVE, read 2026-11-07, gives its own score, CVSS 3.1 **4.2**, with the vector "physical access, high complexity". The two scores differ because two parties scored it; both fall in the medium band.

**Who and what is affected (from the advisory):**

- Affected: YubiKey 5 Series, Security Key Series and 5 FIPS and CSPN versions with firmware **before 5.7**; YubiKey Bio before 5.7.2; YubiHSM 2 before 2.4.0.
- Not affected: firmware **5.7.0 and newer** (Bio 5.7.2 and newer). Yubico moved to its own cryptographic library in 5.7. Keys with 5.7 began shipping on **2024-05-21**.

**What the attacker needs (Yubico's words, condensed):**

1. Physical possession of the key, for long enough to measure it.
2. Specialized equipment and expertise.
3. Knowledge of the account to target.
4. Depending on how the credential was made: the PIN or fingerprint, or the username (and for some accounts the password) so the attacker can get far enough into a login to make the key sign. For FIDO credentials that demand user verification, the attacker needs the PIN too. For credentials that do not, a username may be enough to discover the credential ID.

**What it breaks:**

- **FIDO credentials on an affected key:** a successful attacker holds a working clone of them, and could use it without the real key. My inference, not the advisory's: a clone leaves no mark on the original, so an owner who got the key back would have no sign.
- **PIV and OpenPGP elliptic curve signing keys** on affected firmware, with the PIN needed in the PIV case. Yubico's advice is to use RSA or Ed25519 keys instead.
- **Attestation:** a clone could pretend to be a genuine YubiKey to a site that filters by model.

**What it does not break:**

- It is not remote. As described, it needs the key on a bench and a measuring probe, so malware on your computer cannot do it.
- It does not break phishing resistance: a fake website still cannot get a signature the real one accepts. The attack is on the key, not the protocol.
- It does not touch RSA or Ed25519 keys in PIV or OpenPGP use, per the advisory.
- It does not weaken keys with firmware 5.7 or newer.
- It does not turn a key into a bad choice. Yubico and the researchers both say FIDO remains the strongest option and that a key is "significantly safer than not using one at all". NinjaLab's attack needs the device in hand and an electromagnetic lab, and a fast response (deregister the key everywhere) makes a stolen key a dead key.

**Yubico's answer.** No replacement program: they rated it moderate and said that keeping possession of the key and deregistering it if lost or stolen mitigates it. If you own a key from before 2024-05-21, that is the answer you get. Check your version, and decide whether a new key is worth the money for the accounts it guards. For most readers it is not an emergency. For someone who is likely to face a lab (an activist or a journalist under targeted surveillance, not a student), it is a reason to replace the key.

## The double edge: firmware that cannot be updated

This is the part most write-ups skip, and it cuts both ways.

**A YubiKey's firmware cannot be updated.** Not by you, not by Yubico, not with a tool. The advisory FAQ asks why and answers it in Yubico's words: firmware updates "can introduce new vulnerabilities", and by preventing them "your firmware remains secure from the moment" the key is made.

Look at what that buys and what it costs.

**What it buys.** An update path is an attack surface. If a key can be re-flashed, then somebody can try to re-flash it: a malicious update from a compromised vendor or a stolen signing key, a hostile program on your computer, a person with your key for five minutes. A key with no update path has none of those. What was in the chip when it shipped is what is in it today, which also means a security researcher can check the firmware of a key once and the answer stays true. For a device whose whole job is to be the thing you do not have to doubt, this is a strong property, and I would call it the right default for a small, single-purpose device.

**What it costs.** The same property is why EUCLEAK cannot be fixed. The flaw sat in a library from the chip maker for 14 years. When it was found, every key already in the field stayed vulnerable. Yubico fixed it in new keys, and the fix is "buy a new key" for you. A phone, laptop or router gets a patch; this does not. The cost lands on the user, in money and in the hassle of re-registering on every account, and the keys that need replacing are the ones in people's pockets for years.

**Why it is still the right design.** My argument, not Yubico's: look at the two failures side by side.

- A **patchable** device can fail in a way that scales and hides. One bad update, or one stolen signing key, could change every key of that model at once, silently, with nothing for you to compare.
- An **unpatchable** device fails in a way that is loud, local and slow. The bug is public, with an advisory, a CVE, a version number and a date. Each exploit needs the key in a lab, one at a time. You can see which of your keys are in scope, and the fix is to replace a thing you can hold.

For a credential that is meant to be rare and physical, I would take loud, local and slow. But "right" does not mean "free", and the Nitrokey 3 makes the opposite bet with the same goal: signed firmware, checked on every boot, no downgrades. If the vendor's signing process holds, that gives you patches without giving an attacker a flash. It also makes you trust the vendor's signing key and the update tool for the life of the key, which a frozen device does not ask for. Neither is wrong. They trade different risks, and you should know which one you bought.

**What to do about it, whichever you pick:**

- Record the firmware version when you buy, and read the vendor's advisories page now and then.
- Keep two keys, and make one a different generation or maker if you can, so one flaw does not reach both.
- Treat a lost key as burned, and treat a key you cannot account for the same way.
- Use the PIN. It was the second lock in the EUCLEAK conditions.
- If your threat model includes someone with a lab, replace pre-5.7 keys.

A planned set of lessons on firmware security (issues #465 and #466) goes much deeper into how firmware gets signed, updated, attacked and verified. Those pages do not exist yet, so there is nothing to link to. Look for them in the [Contents](Contents.md) when they land.

## Exercise 1 (no hardware): a PIN-protected key that cannot leave the token

**Where it ran.** On **2026-11-07** on one Linux machine, as an ordinary user, with SoftHSM 2.6.1 and OpenSC 0.26.1 unpacked from the distribution packages into a scratch directory (not installed system wide), against a token directory I created for the purpose. I did not run it in a VM. **What this is.** SoftHSM is a software token that speaks PKCS#11, the same interface a PIV smart card uses with OpenSC. It is a model of the interface, not of the protection: its keys live in files on disk.

In your VM (Debian or Ubuntu names; **est.**, I did not install them there):

```bash
sudo apt install softhsm2 opensc
dpkg -L libsofthsm2 | grep 'libsofthsm2.so'
```

Use the module path that command prints in the next lines. Everything below goes into a scratch directory so no system token is touched:

```bash
mkdir -p ~/hsm-lab/tokens && cd ~/hsm-lab
printf 'directories.tokendir = %s/tokens\nobjectstore.backend = file\n' "$PWD" > softhsm2.conf
export SOFTHSM2_CONF="$PWD/softhsm2.conf"
M=/usr/lib/softhsm/libsofthsm2.so      # use the path dpkg -L printed

softhsm2-util --module "$M" --init-token --free --label demo --so-pin demo-so-pin --pin demo-user-pin
pkcs11-tool --module "$M" --login --pin demo-user-pin --keypairgen --key-type EC:prime256v1 --id 01 --label demo-key
```

What I saw, edited for width: the token initialized, then the key pair generated, with the private key listed as `Access: sensitive, always sensitive, never extractable, local`. That line is the point. The token says the key cannot be read out.

Sign something and check it with OpenSSL, which has never seen the private key:

```bash
echo hello > msg.txt
openssl dgst -sha256 -binary msg.txt > msg.hash
pkcs11-tool --module "$M" --login --pin demo-user-pin --sign --mechanism ECDSA --id 01 \
  --input-file msg.hash --output-file sig.raw --signature-format openssl
pkcs11-tool --module "$M" --read-object --type pubkey --id 01 --output-file pub.der
openssl pkey -pubin -inform DER -in pub.der -out pub.pem
openssl dgst -sha256 -verify pub.pem -signature sig.raw msg.txt
```

I saw `Verified OK`. Now try to take the private key:

```bash
pkcs11-tool --module "$M" --login --pin demo-user-pin --read-object --type privkey --id 01 --output-file priv.bin
```

I saw `sorry, reading private keys not (yet) supported`. Be careful what you conclude. That message is the tool declining, and not proof by itself. The proof is the `never extractable` attribute the token reported. Here, a person with your user account could still read the token's files, which is exactly the gap a real key closes with hardware.

Now the part a software token cannot do. Try the wrong PIN:

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do
  pkcs11-tool --module "$M" --login --pin wrong-pin --list-objects 2>&1 | grep -o 'CKR_PIN_INCORRECT'
done | sort | uniq -c
pkcs11-tool --module "$M" --login --pin demo-user-pin --list-objects | head -3
```

I saw ten `CKR_PIN_INCORRECT` results, and then the correct PIN still worked. In this setup SoftHSM never locked. A real key would have counted down and locked. **That is the lesson:** the retry counter is a property of the hardware, and software that merely says "PIN" has nothing to enforce it.

**Clean up.** `rm -rf ~/hsm-lab`, and unset `SOFTHSM2_CONF`. Or destroy the VM.

## Exercise 2 (no hardware): OpenPGP with separate sign, encrypt and authenticate keys

An OpenPGP card holds three keys, one for each job. GnuPG can make the same layout on disk, so you see the shape before a card is involved. I ran this on **2026-11-07** with GnuPG 2.4.7 in a throwaway home directory, not in a VM.

```bash
export GNUPGHOME="$(mktemp -d)"; chmod 700 "$GNUPGHOME"
gpg --batch --pinentry-mode loopback --passphrase demo-pass \
    --quick-generate-key "Demo User <demo@example.com>" ed25519 cert never
FPR=$(gpg --list-keys --with-colons | awk -F: '/^fpr/{print $10; exit}')
gpg --batch --pinentry-mode loopback --passphrase demo-pass --quick-add-key "$FPR" ed25519 sign 1y
gpg --batch --pinentry-mode loopback --passphrase demo-pass --quick-add-key "$FPR" cv25519 encrypt 1y
gpg --batch --pinentry-mode loopback --passphrase demo-pass --quick-add-key "$FPR" ed25519 auth 1y
gpg --list-secret-keys --keyid-format long
```

I saw one certify key `[C]` and three subkeys, `[S]` for signing, `[E]` for encryption and `[A]` for authentication, each expiring in a year. That is the layout a YubiKey's OpenPGP application holds: the three subkeys go on the card, the certify key stays offline, and GnuPG asks the card for each signature.

```bash
echo hello > "$GNUPGHOME/m.txt"
gpg --batch --pinentry-mode loopback --passphrase demo-pass --detach-sign "$GNUPGHOME/m.txt"
gpg --verify "$GNUPGHOME/m.txt.sig" "$GNUPGHOME/m.txt"
```

I saw `Signature made ...` and the signing subkey's fingerprint. Key generation also stored a revocation certificate under the home directory: look at it. On a real setup that file goes offline with the backup, because it is how you kill a key you lost.

**Clean up.** `rm -rf "$GNUPGHOME"; unset GNUPGHOME`.

The step that needs hardware is moving the subkeys to a card (`gpg --edit-key`, then `keytocard`). I did not run it and I am not going to describe commands I could not test. Yubico's OpenPGP and PIV support articles are the place to go next.

## Exercise 3 (hardware, not run): register a key on a throwaway account

**This exercise was not run. I had no key.** Treat every step as unverified, and if a step differs on the screen from what is written here, believe the screen.

You need two keys of the same model, and an account you can delete: make a throwaway account on a site that supports security keys (GitHub is a common one; the exact menu names change, so look under the account's security settings for "security keys" or "passkeys").

1. Create the throwaway account with a password you will not reuse. Save the recovery codes into a throwaway entry in your password manager.
2. Register key 1. The site asks you to insert it and touch it. Name it "key 1".
3. Register key 2 the same way, and name it "key 2". Take key 2 out of reach.
4. Sign out. Sign in again using key 1 only. Do the same with key 2 only.
5. Optional, and only for a key that guards nothing: set the FIDO2 PIN with Yubico Authenticator (or `ykman`, or Nitrokey's tools) and sign in again; the site should now ask for the PIN or touch plus PIN.
6. Remove key 1 from the account as though it were lost. Confirm key 2 still signs in and key 1 does not.
7. Use one recovery code to sign in once. Mark it as spent.
8. Delete the throwaway account.

Expect to find out two things: how few seconds it takes, and how many places you would have to repeat this on your real accounts. That second number is the argument for doing it as you create each account.

## Build, break, detect, evade, defend

- **Build.** Two keys, PINs set, both registered everywhere that offers it, backup kept in another place, recovery codes in the password manager, a list of where each is registered.
- **Break.** Phishing a password steals the password but not a FIDO login. An attacker with the key and a lab can read an affected pre-5.7 key. An attacker with your key and no PIN can use it where no PIN is required. A weak recovery path, such as an SMS reset or a support-desk reset, goes around the key.
- **Detect.** Sign-in alerts from the site. A key you cannot find. A registered key you do not recognize in the account's security page, which means somebody registered one. Check that page after any account recovery.
- **Evade.** Social engineering the recovery process, malware that waits for you to touch the key and then uses the session, and downgrade tricks that steer a login to a weaker method such as an SMS code if the site still offers it.
- **Defend.** Remove the weaker methods once a key works. Require a PIN. Remove lost keys at once. Keep firmware versions on your list. Read the advisories for the vendor you chose.

## Checkpoint

You are done when you can answer these without looking:

1. Which of the five protocols is phishing resistant, and why does the hardware not matter by itself?
2. What is the difference between FIDO2's PIN and PIV's PIN, and which one locks after eight wrong tries?
3. Where does your second key live, and what lives with it?
4. For EUCLEAK: name the CVE, what an attacker needs, and one thing it does not break.
5. Make the case for and against firmware that cannot be updated, in two sentences each.
6. What did the software token show you that real hardware does and software does not?

## Common mistakes

- **Registering one key.** The lockout is guaranteed to arrive on a Sunday.
- **Putting both keys on the same keyring.** One bag, one loss.
- **Leaving PIV or OpenPGP on factory PINs.** The defaults are in the vendor's documentation.
- **Treating a typed OTP as phishing resistant.** It is a code. A fake site can take it.
- **Never testing a recovery code.** You find out it is wrong on the day you need it.
- **Resetting a key to "fix" a locked application** without remembering a reset deletes the keys in that application (**est.**).
- **Assuming "has a security key" means "safe".** The account's recovery path is only as strong as its weakest method.
- **Treating the flaw as a reason to drop keys.** It is a reason to check your version and replace a pre-5.7 key where the threat is a lab, not a reason to go back to SMS codes.

## Claims register

Retrieved 2026-11-07 with read-only requests. "Read" means I read the page text. "General knowledge" is stated without a source I checked this session.

| Claim | Source | Status |
|---|---|---|
| Advisory YSA-2024-03, "Infineon ECDSA Private Key Recovery", published 2024-09-03, CVSS 4.9 (Yubico), rated moderate | [Yubico: YSA-2024-03](https://www.yubico.com/support/security-advisories/ysa-2024-03/) | Read |
| Affected: YubiKey 5, 5 FIPS, 5 CSPN and Security Key Series before 5.7, Bio before 5.7.2, YubiHSM 2 before 2.4.0; not affected from those versions on | [Yubico: YSA-2024-03](https://www.yubico.com/support/security-advisories/ysa-2024-03/) | Read |
| Attacker needs physical possession, specialized equipment, target account knowledge, and sometimes PIN, username or password; PIV and OpenPGP elliptic curve signing keys and attestation also affected; RSA or Ed25519 as mitigation | [Yubico: YSA-2024-03](https://www.yubico.com/support/security-advisories/ysa-2024-03/) | Read |
| Timeline: reported 2024-04-19, 5.7 released 2024-05-21, YubiHSM 2.4 announced 2024-09-02, advisory 2024-09-03; no replacement program; FIDO still recommended; deregister a lost or stolen key | [Yubico: YSA-2024-03](https://www.yubico.com/support/security-advisories/ysa-2024-03/) | Read |
| Yubico does not allow firmware updates because updates "can introduce new vulnerabilities" and firmware "remains secure from the moment" the key is made | [Yubico: YSA-2024-03, FAQ](https://www.yubico.com/support/security-advisories/ysa-2024-03/) | Read (Yubico's stated position, quoted in part) |
| CVE-2024-45678 for the EUCLEAK issue; NVD base score 4.2 under CVSS 3.1 (vector with physical attack vector and high complexity); description names a non-constant-time modular inversion | [NVD: CVE-2024-45678](https://nvd.nist.gov/vuln/detail/CVE-2024-45678) | Read (via the NVD API) |
| NinjaLab: secure element Infineon SLE78, bug unnoticed 14 years and about 80 Common Criteria evaluations, few local EM captures, demonstrated on YubiKey 5Ci, FIDO clone possible; its own CVE request rejected and MITRE used CVE-2024-45678 | [NinjaLab: EUCLEAK](https://ninjalab.io/eucleak/) | Read (researcher's claims) |
| YubiKey 5 Series: FIDO2, U2F, smart card, OTP, OpenPGP 3; USB-A, USB-C, NFC, Lightning; IP68 | [Yubico: YubiKey 5 Series](https://www.yubico.com/products/yubikey-5-overview/) | Read |
| Security Key Series is offered for people wanting only FIDO2/WebAuthn or FIDO U2F; its exact feature list not read | [Yubico: Security Key Series](https://www.yubico.com/products/security-key/) | Read; feature list **est.** |
| FIDO2: eight wrong PIN attempts lock the application; unlock needs a FIDO2 reset, which also resets U2F; no benefit from regular PIN changes; Yubico recommends a minimum of two keys per site | [Yubico technical manual: FIDO](https://docs.yubico.com/hardware/yubikey/yk-tech-manual/yk5-apps-fido.html) | Read |
| Passkey capacity 25 (older) and 100 (5.7+); OATH 32 and 64; PIV slot algorithms added in 5.7 | [Yubico technical manual: 5.7 firmware](https://docs.yubico.com/hardware/yubikey/yk-tech-manual/yk5-firmware-5.7.html); [OATH](https://docs.yubico.com/hardware/yubikey/yk-tech-manual/yk5-apps-oath.html) | Read |
| OTP: two slots, slot 1 loaded at the factory, touch durations | [Yubico technical manual: OTP](https://docs.yubico.com/hardware/yubikey/yk-tech-manual/yk5-apps-otp.html) | Read |
| OpenPGP card 3.4 from firmware 5.2.3; algorithms; touch policy; default PINs published | [Yubico technical manual: OpenPGP](https://docs.yubico.com/hardware/yubikey/yk-tech-manual/yk5-apps-openpgp.html) | Read |
| PIV is specified by NIST SP 800-73; default PIN, PUK and management key are published and should be changed; slots 9A, 9C, 9D, 9E | [Yubico developers: YubiKey and PIV](https://developers.yubico.com/PIV/Introduction/YubiKey_and_PIV.html) | Read |
| YubiKey 5 FIPS with firmware 5.7.4 NIST certified for FIPS 140-3 effective 22 May 2026 | [Yubico technical manual: introduction](https://docs.yubico.com/hardware/yubikey/yk-tech-manual/yk5-intro.html) | Read |
| Nitrokey 3 features (FIDO2, U2F, OpenPGP card, PIV, password safe), distinct PINs per feature, SE050M secure element EAL 6+ "up to the OS level", no ordinary storage | [Nitrokey 3 documentation](https://docs.nitrokey.com/nitrokey3/) and [FAQ](https://docs.nitrokey.com/nitrokey3/faq.html) | Read |
| Nitrokey 3 firmware images signed and verified by host tool and device before update and on every boot; no downgrades | [Nitrokey 3: firmware update](https://docs.nitrokey.com/nitrokey3/linux/firmware-update.html) | Read |
| Nitrokey says hardware and software are open source and the company produces primarily in Berlin | [nitrokey.com](https://www.nitrokey.com/) | Read (the company's claim, not audited) |
| FIDO2/WebAuthn credentials are scoped to one relying party (origin) | [W3C WebAuthn Level 3](https://www.w3.org/TR/webauthn-3/) | Read via [Enterprise identity](Enterprise-Identity-SSO-SAML-OIDC.md#claims-register) |
| U2F as second-factor-only predecessor of FIDO2; CTAP as the browser-to-key protocol | | General knowledge |
| Exercises 1 and 2 behaved as quoted (SoftHSM 2.6.1, OpenSC 0.26.1, GnuPG 2.4.7; ten wrong PINs did not lock the software token) | My own terminal, 2026-11-07 | Observed |
| `apt install softhsm2 opensc` and `dpkg -L libsofthsm2` on Debian or Ubuntu | | **est.** (packages downloaded and unpacked, not installed) |
| Exercise 3 on a site's security settings; PIV and OpenPGP retry counts of three | | **est.** (no key, not run) |
| Why a patchable and an unpatchable device fail differently; the "loud, local and slow" argument | | My opinion, labeled as such in the text |

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Hardware security keys: YubiKey, Nitrokey, PIV

Previous: [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) / Next: [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md)

In this track: [Track 1: Foundations](Contents.md#track-1-foundations), 35 pages

- OS and Linux, git and the terminal: [Git from zero](Git-From-Zero.md) / [The terminal and your first script](Terminal-and-Your-First-Script.md) / [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) / [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) / [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md) / [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md) / [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) / [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) / [Kubernetes for beginners](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md) / [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) / [Cron, systemd timers and init scripts versus systemd](Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd.md)
- Networking: [How a web request works](How-a-Web-Request-Works.md) / [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) / [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) / [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) / [IPv6 adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md)
- Identity and secrets: [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) / [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) / [Secrets from day one](Secrets-From-Day-One.md) / [Password managers and passkeys](Password-Managers-and-Passkeys-What-Each-Protects-and-Where-They-Fail.md) / [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) / **Hardware security keys: YubiKey, Nitrokey, PIV**
- Infrastructure as code: [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md) / [OpenTofu from zero](OpenTofu-From-Zero.md) / [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) / [Ansible: configuration management versus provisioning](Ansible-Configuration-Management-Versus-Provisioning.md) / [Native IaC versus open standards](Native-IaC-vs-Open-Standards-CloudFormation-ARM-Bicep-and-OpenTofu.md) / [Spacelift from zero](Spacelift-From-Zero.md) / [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md) / [Environments and promotion](Environments-and-Promotion-Dev-Staging-Production.md)
- Web hosting: [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md) / [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) / [Static against dynamic: Hugo, WordPress and recon](Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon.md) / [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md) / [Autoscaling and elasticity](Autoscaling-and-Elasticity-Scale-Out-Targets-Cooldowns-and-Cost-Caps.md)

Related pages:

- [Password managers and passkeys](Password-Managers-and-Passkeys-What-Each-Protects-and-Where-They-Fail.md)
- [Secrets from day one](Secrets-From-Day-One.md)
- [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)
- [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md)
<!-- END GENERATED PAGE NAV bottom -->
