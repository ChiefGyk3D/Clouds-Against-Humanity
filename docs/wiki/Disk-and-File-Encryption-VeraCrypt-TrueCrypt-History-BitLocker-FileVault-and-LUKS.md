# Disk and file encryption: VeraCrypt in depth, its TrueCrypt history, and BitLocker, FileVault and LUKS

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says (and the gap)](#what-the-wiki-already-says-and-the-gap)
- [What encryption at rest protects, and what it does not](#what-encryption-at-rest-protects-and-what-it-does-not)
- [Full-disk encryption by platform: BitLocker, FileVault, LUKS](#full-disk-encryption-by-platform-bitlocker-filevault-luks)
- [Three layers: whole disk, volume and file](#three-layers-whole-disk-volume-and-file)
- [VeraCrypt in depth](#veracrypt-in-depth)
- [From TrueCrypt to VeraCrypt: a dated history](#from-truecrypt-to-veracrypt-a-dated-history)
- [Where it fits: a password manager vault and a hardware key](#where-it-fits-a-password-manager-vault-and-a-hardware-key)
- [Free path: an encrypted container in a VM](#free-path-an-encrypted-container-in-a-vm)
- [Flip the board](#flip-the-board)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
- [Not verified, plainly](#not-verified-plainly)
<!-- END GENERATED PAGE CONTENTS -->

Encryption at rest protects a device that is switched off. That is the whole promise, and most of this page is the fine print on it: what a powered-off laptop gets from it, what a running one does not, what the three built-in disk encryptions do, and how VeraCrypt (the free tool that grew out of TrueCrypt) covers the cases they leave open, including the ones where you move an encrypted folder between machines.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. One exercise was run, in a throwaway virtual machine; every platform and vendor claim was read, not tested.** On **2026-11-07** I booted a Debian 12 cloud image in QEMU 10.0.13 (a Debian build, KVM on), installed the VeraCrypt 1.26.31 console package in it, and ran Exercises 2 to 6 below as `root`, with the output quoted where it matters. **Not run:** VeraCrypt's graphical program, a hidden volume, a keyfile, a whole-partition or system-encryption setup, anything on Windows or macOS, BitLocker, FileVault, `manage-bde`, `fdesetup`, and a LUKS volume I created myself (I only read the defaults my own `cryptsetup` prints). Vendor and project statements were read on **2026-11-07** from the pages named in the [claims register](#claims-register); a claim I could not read there is marked **est.** Trust what your terminal prints over what this page says.

> **Prerequisites.** A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)). Knowing what a key and a hash are helps ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)). For the exercise you need a Linux virtual machine; [Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) builds one for free. About two hours for the reading and the exercise (est.). Nothing here needs money.

> **Where this runs, and the rule.** Everything in the exercise is local and throwaway: a disposable VM, a 20 MB container, passwords that are labeled placeholders. **Never type a password you use anywhere real into a command in this lesson.** A password on a command line is visible in the process list and in your shell history, which is fine for a placeholder in a throwaway VM and wrong for anything else; the lesson shows the prompting form for real use.

## What you will be able to do

- Say what encryption at rest protects against and what it does not, with the powered-off versus running-and-unlocked line drawn in the right place.
- Describe cold boot and evil maid attacks at concept level and name the control that answers each.
- Explain BitLocker, FileVault and LUKS in plain words: where the key lives, how you get back in, and what each one assumes.
- Choose between full-disk, volume (container) and file encryption for a job.
- Create, mount, unmount and break a VeraCrypt container, and say what a keyfile, a PIM, a hidden volume and a cascade are.
- Give the honest limits of hidden volumes and plausible deniability, in the project's own words.
- Give a dated account of TrueCrypt's shutdown, the public audit and what the VeraCrypt fork changed, and say which parts of that account are primary-sourced and which are not.
- Place VeraCrypt next to a password manager vault and a hardware key, and say when it is the wrong tool.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Encrypt, decrypt, break it on purpose (one file, `age`) | [Hashing, encryption and keys: exercise 4](Hashing-Encryption-and-Keys.md#exercise-4-encrypt-decrypt-and-break-it-on-purpose) | Encrypting a whole volume you can use like a folder, and what happens when the key is gone. |
| Hardware keys, passphrases on keys | [Hashing, encryption and keys: keeping keys](Hashing-Encryption-and-Keys.md#keeping-keys-storage-passphrases-and-hardware-keys) | Where a hardware key does and does not help with encrypted storage. |
| "Full-disk encryption" as a laptop control | [Secrets from day one](Secrets-From-Day-One.md), the laptop row of its threat table | What it is, by platform, and what it does not stop. |
| FileVault as the Mac disk encryption, recovery key held by MDM | [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) | How FileVault protects the key, and its two sibling tools. |
| Disk encryption in a table of what helps against what | [Privacy, security and anonymity: the matrix](Privacy-Security-and-Anonymity-Three-Different-Things-and-Why-There-Is-No-Silver-Bullet.md) | The mechanics behind that row. |
| Data at rest, in transit and in use; key custody | [Cryptography fundamentals](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md) | A tool-level look at at-rest encryption you can run. |
| TrueCrypt, VeraCrypt, LUKS, BitLocker | Nothing | All of it. |

## What encryption at rest protects, and what it does not

Disk, volume and file encryption all do one thing: they make the stored bytes unreadable without a key. The protection lasts exactly as long as the key stays out of the attacker's reach. That gives two situations that are easy to mix up.

| The device is | The key is | Full-disk or volume encryption |
|---|---|---|
| Powered off, or at the boot prompt, or a container that is dismounted | Not in memory. It exists only as something you know or hold (a password, a PIN, a key stored in a TPM that releases it only to the right boot chain) | Does its job. A thief with the drive gets ciphertext, and what is left is guessing the password |
| Running, logged in, or a volume that is mounted | In memory, so the operating system can decrypt on the fly | Does nothing against a person using the computer, malware running as you, or anything that can read memory |
| Asleep, or locked but on | **Still in memory.** The cold boot paper below says that locking the screen "does not protect the contents of memory" and that suspending a laptop ("sleeping") "is also ineffective" | A lock screen stops a casual user, not someone who can read memory |

That table is why "I have disk encryption" and "my data is safe" are different sentences. A laptop lost in a taxi is the case encryption at rest was built for. A laptop taken from your hands while it is unlocked is not.

**What it does not protect against, in one list.** Malware or a person using your logged-in session. A keystroke logger that records the password. Plaintext copies the operating system makes elsewhere (the VeraCrypt documentation's list: the paging file, the hibernation file, memory dumps, file-indexing databases, recently-used lists, temporary files). Data you already saved to an unencrypted place. A backup that is not encrypted. Being made to hand over the password. Losing the password (the next sections show that one on purpose).

**Cold boot, at concept level.** Memory chips do not lose their contents the instant the power goes. The 2008 paper *Lest We Remember: Cold Boot Attacks on Encryption Keys* (Halderman and eight co-authors, 17th USENIX Security Symposium) says that the DRAM in most modern computers will "retain their contents for several seconds after power is lost, even at room temperature and even if removed from a motherboard", and that simple cooling raises that "dramatically". The authors used cold reboots to attack disk encryption systems, naming BitLocker, TrueCrypt and FileVault, and wrote that they "know of no simple remedy that would eliminate them". The answers are partial: a pre-boot password or PIN so the key is never loaded without you (Microsoft says this helps against "memory remanence attacks"), clearing memory on reset (Microsoft cites the TCG Reset Attack Mitigation), and shutting a machine down fully, not suspending it, when it holds something that matters. VeraCrypt's own documentation tells you to shut down and leave the computer powered off "for at least several minutes" after a session, and notes that master keys cannot be erased if power is cut or the system crashes.

**Evil maid, at concept level.** The disk is encrypted, but the small piece of code that runs first and asks for your password is not, and someone with a few minutes of access can swap it for one that records what you type. In October 2009 Joanna Rutkowska and Alex Tereshkin published a proof of concept against TrueCrypt's system disk encryption, a bootable USB image that, they wrote, takes about a minute to run. The answer is making the boot chain measurable and refusing to release the key if it changed. Microsoft's BitLocker documentation says the TPM "should observe" a bootkit through its boot measurements and that BitLocker "protects against this attack by default". VeraCrypt added detection of boot loader tampering for Windows system encryption in version 1.12 (2015-08-05). Its physical security page still says you "must not use VeraCrypt on a computer that an attacker has physically accessed", because the hardware may have been modified.

**Two honest side notes.** First, an attacker with the drive and unlimited time attacks the password, not the cipher; the strength of the password and of the key derivation is the whole game ([Ciphers, modes and key derivation](#ciphers-modes-and-key-derivation)). Second, ransomware is encryption used against you, by someone else holding the key. The mechanism is the same and the intent is opposite, which is why [backups](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md) and encryption are separate jobs.

## Full-disk encryption by platform: BitLocker, FileVault, LUKS

All three encrypt a whole volume transparently below the file system, so every file and the system's temporary files are covered. All three use the same block-cipher mode, XTS, with AES. The differences are where the key lives and how you get back in.

| Question | BitLocker (Windows) | FileVault (macOS) | LUKS (Linux) |
|---|---|---|---|
| In plain words | Microsoft's volume encryption. With a TPM chip it releases the key only if the boot chain is unchanged, and can add a PIN | Apple's volume encryption. On a Mac with Apple silicon or a T2 chip the internal drive is always encrypted, and FileVault adds your account password to the key protection | The standard Linux on-disk format, used through `dm-crypt`. A header holds several key slots, each opened by its own passphrase or key file |
| Default cipher (as read) | XTS-AES 128-bit for device encryption | AES-XTS | `aes-xts-plain64` with a 512-bit key (my `cryptsetup` 2.7.5 prints 256 and says XTS doubles it) |
| Where the key lives | In the TPM, sealed to the boot measurements; optionally also needs a PIN or a USB startup key | Wrapped by a key that needs your password and the chip's hardware key; keys handled in the Secure Enclave on Apple silicon and T2 | In the LUKS header, wrapped by each passphrase through a key derivation function; the default on my machine is Argon2id |
| Getting back in | A recovery key. Device encryption backs it up to a Microsoft account, Entra ID or Active Directory | A recovery key shown at setup, which can be saved in the keychain or escrowed by an organization | Another key slot, or a header backup you made earlier. There is no escrow unless you build one |
| Editions and defaults | "Device encryption" turns it on automatically on eligible devices and is listed for all Windows versions; manual BitLocker is listed for Pro, Enterprise, Pro Education/SE and Education | Built in; off or on by choice for the password layer | A choice at install on most distributions; not automatic |

Sources for the table above are in the [claims register](#claims-register) (Microsoft Learn pages updated 2026-08-24, the Apple Platform Security guide published 2026-01-28, the `cryptsetup` manual, and my own `cryptsetup --help`). A few details that change what you do:

- **BitLocker with local-account-only sign-in can be encrypted and still open.** Microsoft's page says that on a device that uses only local accounts, "it remains unprotected even though the data is encrypted", because the key sits in the clear (the equivalent of BitLocker being suspended) until a recovery key is backed up and a TPM protector is created. Look at the status, not the label.
- **A password-only BitLocker is discouraged.** Microsoft: the password option "isn't secure since it's subject to brute force attacks as there isn't a password lockout logic", and it is "disabled by default". A TPM with a PIN has anti-hammering protection, and Microsoft says pre-boot authentication exists to keep the keys from being loaded into memory "without the trusted user supplying another authentication factor", which is why the cold boot answer above leans on the PIN.
- **FileVault: turn it on early.** Apple's guide says data "added and then deleted before turning on FileVault isn't encrypted and may be recoverable with forensic data recovery tools". The same guide says that with FileVault off on a Mac with Apple silicon or a T2 chip the volume is still encrypted, but the key is protected only by the hardware, not by your password.
- **LUKS gives you several doors.** Each key slot is independent and can be revoked, and the manual says slots can be scrubbed from the media with "anti-forensic stripes". The flip side: if the header is damaged and you have no backup of it, the data is gone, so back up the header (`cryptsetup luksHeaderBackup`) and keep it off the same disk.
- **Escrow is a decision.** A recovery key stored with a vendor or an employer means that party can open the disk. That is the right trade for a company fleet and a real choice for a person ([Hashing, encryption and keys: "encrypted" is not "secure"](Hashing-Encryption-and-Keys.md#encrypted-is-not-secure) makes the same point about managed keys).

## Three layers: whole disk, volume and file

| Layer | What is encrypted | Example | Best for | Weak at |
|---|---|---|---|---|
| Whole disk (or system volume) | Everything on the device, including the operating system's scratch files | BitLocker, FileVault, LUKS, VeraCrypt system encryption (Windows) | Every laptop and phone, by default | Anything once it is booted and unlocked; moving one folder to another machine |
| Volume (a partition or a file that acts as a drive) | A separate drive-sized space that you mount and unmount | A VeraCrypt container or partition, a LUKS data partition | A set of files that must be locked when you are not using them, or that travels on a USB stick or in cloud storage | Leaks from the host system around it (see [Operating habits that matter](#operating-habits-that-matter)) |
| File | One file at a time, with a key or password | `age`, GnuPG, an encrypted archive ([exercise 4](Hashing-Encryption-and-Keys.md#exercise-4-encrypt-decrypt-and-break-it-on-purpose)) | Sending one file to one person; a secret you hand over once | Convenience for a whole working folder; hiding file names and sizes |

The layers add up instead of competing. A sensible default for a person: full-disk encryption on every device, a password manager for credentials, and a container only for the folder you carry or sync. The [password manager and hardware key section](#where-it-fits-a-password-manager-vault-and-a-hardware-key) says where each fits.

## VeraCrypt in depth

VeraCrypt is free, open source disk encryption for Windows, macOS and Linux. Its home page (read 2026-11-07) says it is "based on TrueCrypt 7.1a" and credits AM Crypto; the current version on the site that day was 1.26.31, released 2026-11-02. It supports Windows 10 version 1809 and later and Windows 11, macOS 12 and later, several Linux builds on x86 and ARM64, FreeBSD 14 and later, OpenBSD 7.8 and later, and Raspberry Pi OS (its supported-systems page, read the same day). It is a separate program from the platform tools above, with its own on-disk format; its own pages describe it as encryption software that "encrypts only disks, not RAM" and "not anti-malware software".

### How it is used

| Mode | What you get | Notes (from the project's documentation unless marked) |
|---|---|---|
| **File container** | An ordinary file (any name, often `.hc`) that you mount as if it were a drive | Portable: copy it to a USB stick or a cloud folder. Looks like random data, with no signature, until mounted |
| **Non-system partition or whole drive** | An entire partition or an external drive, mounted by VeraCrypt after you give the password | No file to carry around; good for external disks. Needs administrator rights |
| **System encryption** | The drive that holds Windows, with a password asked before Windows boots | **Windows only** (the page is about "a partition or drive where Windows is installed"). Pre-boot authentication happens in the VeraCrypt boot loader, which sits unencrypted and can be recognized as VeraCrypt |
| **Hidden volume or hidden operating system** | A second volume inside the free space of the first, or a second operating system inside a hidden volume | [Its own section below](#hidden-volumes-and-plausible-deniability-with-the-limits), with the limits |

When you give VeraCrypt a password, it derives a key from it, uses that key to unlock a header that sits at the front of the volume, and the header holds the real master keys. Encryption of the data itself is on the fly: it is decrypted in memory in small pieces as programs read it, never written back to disk in the clear (the project's FAQ uses the example of playing a video from a mounted volume). Changing the password re-encrypts only the header, which is fast and does not touch the data.

### Passwords, keyfiles and the PIM

- **The password.** The project says to use more than 20 characters, not a dictionary word or a combination of them, and nothing with names or dates in it. For a human to remember, a long phrase of unrelated words is the usual way to get length (est., general practice, not VeraCrypt's text). A password generator is fine only if it is high-quality and not controlled by an attacker, and the project says never to let a third party choose the password.
- **A keyfile** is any file whose contents are mixed into the password. The project: any file can be one, only the first 1,048,576 bytes (1 MiB) count, and you can supply as many as you like. A keyfile needs at least 30 bytes **of real randomness** to resist guessing, so the project suggests having VeraCrypt generate one (*Tools, Keyfile Generator*) and not using a photo or a download. Because the file's bytes go into the key, a keyfile that is lost, or changed in its first megabyte, is a password you no longer have; if the password is empty and the keyfile is the only secret, the file **is** the key. Keyfiles can also live on a smart card or hardware token that speaks PKCS #11, and the project documents EMV bank cards as a keyfile source too (read, not tested).
- **A word on keyfile strength.** In the TrueCrypt audit's cryptography report (2015, TrueCrypt 7.1a), the way TrueCrypt mixed a keyfile into the password was one of four findings, rated Low: "not cryptographically sound". VeraCrypt's documentation today still describes a pool built with CRC-32 and then passed to the key derivation function. I did not check whether anything about that finding changed, so treat a keyfile as an extra factor, not as something that makes a weak password strong (**est.**).
- **PIM (Personal Iterations Multiplier).** Added in 1.12 (2015-08-05). A number you also have to remember that sets how many rounds the key derivation runs, as a secret in its own right. Leave it blank and VeraCrypt uses the defaults. A larger PIM makes every wrong guess slower for an attacker and every correct mount slower for you.

### Ciphers, modes and key derivation

What I read on 2026-11-07 on the project's documentation pages:

- **Ciphers.** AES, Camellia, Kuznyechik, Serpent and Twofish, each with a 256-bit key and a 128-bit block, and cascades of two or three of them (for example AES-Twofish-Serpent). All run in XTS mode.
- **Header key derivation.** For a non-system volume or a file container you choose **PBKDF2-HMAC** with one of SHA-512, SHA-256, BLAKE2s-256, Whirlpool or Streebog, or **Argon2id**, which was added for non-system volumes in 1.26.29 (2026-06-09). System encryption always uses PBKDF2-HMAC.
- **Defaults.** With no PIM, PBKDF2 uses **500,000 iterations** for containers and non-system volumes, 200,000 for system encryption with SHA-256, BLAKE2s or Streebog, and 500,000 for system encryption with SHA-512 or Whirlpool. With a PIM, the container formula is 15,000 + (PIM x 1,000). Argon2id with no PIM behaves like PIM 12: 416 MiB of memory and 6 passes. The salt is 512 bits for both.
- **What to pick (est.).** AES with SHA-512 is a plain, fast choice, and AES uses the processor's hardware acceleration where it exists. A cascade multiplies the work per block and protects against a break in one cipher at the cost of speed; I would not choose one for a portable folder. Argon2id is memory-hard, which makes parallel guessing on graphics cards more expensive than PBKDF2 does; it is new in VeraCrypt (about five months old on the day I read it) and the format change means older VeraCrypt versions cannot open such a volume (est.; check the release notes for your version before you rely on it).
- **What the numbers mean.** A KDF only slows guessing; a weak password still falls. The iteration count is a cost to an attacker per guess, and the cost to you is a longer wait when you mount. I measured the wait in the exercise below.

### Hidden volumes and plausible deniability, with the limits

The idea. A VeraCrypt volume's free space is filled with random data, and an unmounted hidden volume cannot be told apart from it. So you create a hidden volume inside the free space of an outer one, give each its own password, and put some believable-looking files in the outer volume. If you are forced to reveal "the" password, you reveal the outer one. Which volume mounts depends only on which password you type. For Windows, the project also offers a **hidden operating system**: a second system inside a hidden volume, with a decoy system alongside it.

What the project itself says about the limits, which is where most explanations stop too early:

- **Changes are visible to someone who sees the volume twice.** "If an adversary has access to a (unmounted) VeraCrypt volume at several points over time, he may be able to determine which sectors of the volume are changing." If sectors inside the hidden area changed and you cannot explain it, that "might indicate the existence of a hidden volume".
- **Where the file lives matters.** Copies of a container, or fragments of it, can be left behind by a defragmentation, by a journaling file system such as NTFS, by wear-leveling on a solid-state drive or USB flash drive, and by cloning the host volume. The project says not to store hidden volumes on devices that use wear-leveling, and that "If you need plausible deniability, you must not use VeraCrypt to encrypt any part of (or create encrypted containers on) a device (or file system) that utilizes a wear-leveling mechanism". That rules out solid-state drives and USB flash drives that use wear-leveling, which I expect is most of them (**est.**; the project says to ask the manufacturer).
- **TRIM tells an observer which sectors are free.** The project's TRIM page: "the adversary will be able to tell which sectors contain free space", and plausible deniability "may be negatively affected".
- **The surroundings leak.** While a hidden volume is mounted, the operating system and applications can write file names, recent-file lists and temporary files to the unencrypted system drive. The documented answers are to use a hidden operating system, or a live CD that writes only to a RAM disk, and to mount the outer volume read-only. On Linux and macOS the project says that if you cannot guarantee this, you must not create or mount hidden volumes.
- **The outer volume must look used.** The decoy operating system should be used as often as the real one, or the lack of use is itself a hint. The hidden system must not be connected to a network, and it must never be reactivated (Windows activation logs a time on a server).
- **A container file itself is evidence.** The project: a file-hosted container has no signature, "they cannot provide this kind of plausible deniability, because there is practically no plausible explanation for the existence of a file containing solely random data". Only the hidden volume inside gives you a story. Likewise, the system-encryption boot loader "can be easily identified" as VeraCrypt.
- **The feature has had a bug.** VeraCrypt 1.18a (2016-08-17) fixed a TrueCrypt vulnerability "allowing detection of hidden volumes presence". The release notes say anyone who depends on deniability "must recreate both the outer and hidden volumes" made by older versions. If the feature leaked once, plan for the chance that it leaks again.
- **It is a legal and human claim as much as a technical one.** The cryptography can only promise that the bytes are indistinguishable from random. Whether anyone believes there is no second volume is not a cryptographic question, and I did not research how any particular country treats compelled passwords (**est.**; the wiki's legal pages are about other topics). Do not build a plan on deniability without an adviser who knows the law where you are.

Plain summary: a hidden volume is a narrow tool for a narrow case, with a long list of ways to defeat it by habit. If your case does not clearly need it, a normal volume with a good password is simpler and fails less often.

### Use across Windows, macOS and Linux

A container is one file, and the same file opens on all three if both machines have VeraCrypt and the **file system inside** is one both can read. The choice made when you create it is the one that travels.

| File system inside | Read on Windows | Read on macOS | Read on Linux | Note |
|---|---|---|---|---|
| exFAT or FAT | Yes | Yes | Yes | No Unix permissions; FAT has a 4 GB per-file limit (general knowledge, **est.**) |
| NTFS | Yes | Read, and write with extra software | Yes, through a driver | VeraCrypt can format NTFS on Linux (release notes, 1.0f) |
| ext2, ext3, ext4 | Needs extra software | Needs extra software | Yes | VeraCrypt's Linux and macOS builds offer these; I used ext4 in the exercise |

On macOS, VeraCrypt depends on a FUSE layer (its release notes mention macFUSE compatibility). On Linux, mounting uses the kernel's device-mapper by default and so needs administrator rights, which is why the exercise below is run as `root` in a VM. On Windows, system encryption is the one thing the other two platforms do not have.

### Operating habits that matter

- **Dismount when you are done.** A mounted volume is an open door for everything running as you. VeraCrypt has auto-dismount options; the 1.0f release notes added one for when the user session is locked, and I did not check the others (**est.**).
- **Shut down after a session that mattered** (cold boot, above). The project's text: "you must shut down ... the computer and then leave it powered off for at least several minutes".
- **Back up the header.** The volume header is a single point of failure; VeraCrypt has a backup and restore function. Keep the backup away from the volume. The wear-leveling page adds a warning that goes both ways: on a solid-state drive, changing a password may not really overwrite the old header, so an old, compromised password can still open the volume if someone finds the old header (the project's wording is "VeraCrypt cannot ensure that the older header is really overwritten").
- **A cloud-synced container re-uploads as a whole file** after any change (general behavior of file sync, **est.**), and the project warns that backing up a hidden volume by cloning its host volume is one of the ways to defeat it. For a folder that changes daily, an encrypted cloud client that works per file is usually less painful.
- **Do not trust a machine you have lost control of.** The project's physical-security and malware pages both say that if an attacker has had access or the machine is infected, VeraCrypt "may become unable to secure data".
- **Keep the program updated and from the project's site.** Windows builds in 2026 depend on Microsoft-signed drivers and boot loaders. The project's release notes for 1.26.29 to 1.26.31 (2026-06-09 to 2026-11-02) include security fixes on Windows and Linux and notes on Secure Boot certificate migration; reading them is part of owning the tool.

## From TrueCrypt to VeraCrypt: a dated history

The short version. TrueCrypt was the free, widely used disk encryption tool of the 2000s. Its authors were anonymous. In 2013 a public fundraiser began to pay for an independent audit. On 2014-05-28 the TrueCrypt web page was replaced with a notice that the project was ended and that using it "is not secure". The audit went on and found no backdoor. A fork called VeraCrypt took the code forward under active maintenance, kept the on-disk idea and raised the cost of password guessing.

| Date | What happened | Source and status |
|---|---|---|
| 2004 | TrueCrypt 1.0 released, by "the TrueCrypt Team", anonymous developers | Wikipedia (secondary). Not checked against a primary page |
| 2013-10 | The public audit fundraiser succeeds and the Open Crypto Audit Project forms | Wikipedia (secondary). Ars Technica (2014-04-14) says about $80,000 had been raised by February 2014, and that Matthew Green, a Johns Hopkins cryptographer who helped lead the effort, told the developers of the plan |
| 2014-04-14 | **Audit phase 1** (iSEC): the bootloader and Windows kernel driver reviewed. Result: "no evidence of backdoors or otherwise intentionally malicious code in the assessed areas". Minor vulnerabilities found, judged "unintentional, introduced as the result of bugs rather than malice". The code was found below standard for secure code, with a weak spot in the volume header integrity check (a string and two CRC-32 values) | Ars Technica, 2014-04-14, quoting the report. I did not read the iSEC report itself |
| 2014-05-28 | **The shutdown.** The SourceForge page began with red text: "WARNING: Using TrueCrypt is not secure as it may contain unfixed security issues". It said development "was ended in 5/2014 after Microsoft terminated support of Windows XP" and told users to migrate to the disk encryption built into their platform. A new version 7.2 was signed with the real TrueCrypt key and, according to Ars, appeared to let you decrypt but not create volumes | Ars Technica, 2014-05-28 (read). Ars said at the time it could not immediately confirm the page was authentic; Green told Ars he had no advance notice and believed it was |
| 2014-06 | A developer reportedly refuses permission to reuse the TrueCrypt name for a fork under a standard license; the forks are named VeraCrypt and CipherShed, and a re-implementation tc-play | Wikipedia (secondary), citing Green. Not checked against a primary page |
| 2014-06-03 | Oldest entry in VeraCrypt's own release notes: 1.0d. (Wikipedia gives 2013-06-22 as the first release. I could not reconcile the two, so I give no start date) | VeraCrypt release notes (read). Wikipedia date: secondary, unconfirmed |
| 2014-09-04 | VeraCrypt 1.0e: "Correct most of the security vulnerabilities reported by the Open Crypto Audit Project" | VeraCrypt release notes (read) |
| 2014-12-30 | VeraCrypt 1.0f: can mount TrueCrypt volumes and convert containers and non-system partitions; SHA-512 becomes the default key derivation hash; a bootloader fix for a finding of the audit | VeraCrypt release notes (read) |
| 2015-04-02 | **Audit phase 2** (cryptography review of TrueCrypt 7.1a on Windows, by NCC Group's Cryptography Services team). Report dated 2015-03-13: **four findings: two High, none Medium, one Low, one Undetermined**. The two High: `CryptAcquireContext` can fail silently and key generation continues; the AES implementation is open to cache-timing attacks. The Low: keyfile mixing is "not cryptographically sound". Undetermined: unauthenticated ciphertext in volume headers. Green's summary: "no evidence of deliberate backdoors, or any severe design flaws that will make the software insecure in most instances" | NCC report (read, an archived copy of the project's PDF, because the live host returned an error on 2026-11-07); Green's blog post of 2015-04-02 (read) |
| 2015-04-05 | VeraCrypt 1.0f-2: "Solve CryptAcquireContext vulnerability reported by Open Crypto Audit Phase II" | VeraCrypt release notes (read) |
| 2015-08-05 | VeraCrypt 1.12: the PIM; detection of boot loader tampering ("Evil Maid" attacks) for system encryption | VeraCrypt release notes (read) |
| 2016-10-17 | **VeraCrypt audit** (Quarkslab, for the Open Source Technology Improvement Fund) of version 1.18: 8 critical, 3 medium and 15 low or informational findings. VeraCrypt 1.19 shipped the same day and fixed most; the GOST 28147-89 cipher was removed because "the implementation was unsafe" | OSTIF post of 2016-10-17 (read). I did not read the Quarkslab report |
| 2020-10 | Another audit of VeraCrypt, by Fraunhofer SIT for the German BSI | Wikipedia (secondary). Not read at the source |
| 2023-10-01 | VeraCrypt 1.26.7 removes TrueCrypt mode ("Version 1.25.9 can be used to mount or convert TrueCrypt volumes") and removes RIPEMD-160 and GOST89 | VeraCrypt release notes (read) |
| 2026-03 and 2026-04 | The lead developer reports Microsoft terminated the account used to sign VeraCrypt's Windows drivers and boot loader, blocking new Windows releases for a time; access was restored on 2026-04-10 | Wikipedia (secondary). Not checked against a primary page. It matters because it shows how much rides on one maintainer and one signing account |
| 2026-06-09 | VeraCrypt 1.26.29 adds Argon2id for non-system volumes | VeraCrypt release notes (read) |

What is still unknown. Why the authors stopped, and why the notice said "unfixed security issues" when the audit found no backdoor, has never been confirmed in any source I read. Green told Ars he had no warning. Several explanations circulated in 2014; I report none of them as fact, and an unexplained shutdown by anonymous developers is itself something the audit could not clear up, because it audited code and not people.

**What VeraCrypt changed from TrueCrypt 7.1a.**

| Change | TrueCrypt 7.1a | VeraCrypt | Source |
|---|---|---|---|
| Password guessing cost | PBKDF2-RIPEMD-160 with 1,000 iterations for system encryption and "at most 2000" for containers and other partitions | 200,000 (system, with SHA-256 and similar) and 500,000 (containers and non-system volumes) by default; a PIM raises it | VeraCrypt home page (the TrueCrypt figures are the VeraCrypt project's own statement) and its key-derivation page |
| Tuning | None | The PIM (1.12) | Release notes |
| Memory-hard key derivation | No | Argon2id for non-system volumes (1.26.29) | Release notes |
| Findings from the audits | Present in 7.1a | Several fixed in 1.0e, 1.0f, 1.0f-2 and 1.19 | Release notes; OSTIF |
| Hidden-volume detection flaw | Present | Fixed in 1.18a; volumes made earlier must be recreated | Release notes |
| Boot tampering | No detection | Detection added in 1.12; EFI system encryption for Windows in 1.18 | Release notes; home page |
| Memory | No such option (**est.**) | Optional RAM encryption of keys and cached passwords from 1.24 (2019-10-06), at a stated 5 to 15 percent cost and with Windows hibernation disabled | VeraCrypt RAM page |
| Ciphers | AES, Serpent, Twofish and cascades | Adds Camellia and Kuznyechik; no GOST 28147-89 and no RIPEMD-160 (removed 1.26.7) | Release notes; encryption algorithms page |
| TrueCrypt volumes | Native | Mount and convert since 1.0f; support removed in 1.26.7 (use 1.25.9 to convert) | Release notes |

**If you still have TrueCrypt volumes.** Use VeraCrypt 1.25.9 to mount or convert them, per the release notes. The project's FAQ advises backing up the header before converting. I did not run a conversion.

## Where it fits: a password manager vault and a hardware key

Three tools with the same word, "secret", and three different jobs.

| Question | Password manager vault | VeraCrypt container | Hardware security key |
|---|---|---|---|
| What it protects | Your credentials: logins, notes, one-time-code seeds | A folder of files, from outside readers when it is dismounted | Your login to an account, and in some designs a private key that never leaves the device |
| Where the secret is | A master password (and often a device key), wrapping an encrypted file | A password, a PIM, optionally keyfiles | Inside the key; unlocked by touch and often a PIN |
| What happens if you lose it | Depends on the product: some can recover through an account, some cannot | The data is gone. There is no reset, and the project says in its FAQ it has no backdoor and cannot recover your data | You use a second key or a recovery method set up in advance, per account |
| Phishing | A master password typed into a fake page is lost; autofill that matches the site helps (**est.**) | Not applicable | Strong, for FIDO2 and WebAuthn logins ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#keeping-keys-storage-passphrases-and-hardware-keys)) |
| Weak point | A malicious page or a keylogger that records the master password | Malware while mounted; a lost password; leaks to the host system | Loss, and the setup of recovery |

A password manager vault is itself an encrypted file behind one password, so its core is the same idea as a container; what it adds is syncing, autofill and sharing, and what it costs is exposure to the sync and to whoever hosts it. The right pairing is not either/or:

- **Use the manager to hold the VeraCrypt password** only if the manager is not on the machine or volume you are protecting. If the vault lives inside the encrypted container it opens, the loop locks you out. A password you memorize, or a break-glass copy on paper kept somewhere you can trust, covers that (the [secrets lesson](Secrets-From-Day-One.md) has the habits).
- **A hardware key does not unlock a VeraCrypt volume the way it signs a login.** VeraCrypt's documented hardware use is keyfiles stored on a PKCS #11 token or smart card, where the key holds the keyfile and you supply a PIN. That is a different protocol from the FIDO2 or WebAuthn login a hardware key is usually bought for (**est.**: I did not test one). Keep both and keep their jobs apart.
- **Where VeraCrypt is the wrong tool.** Secrets a machine needs at run time belong in a secrets manager ([Doppler and secrets](Doppler-and-Secrets.md)). A file a team edits together belongs in a service with per-user access. Anything where you cannot afford "the password is gone, so the data is gone" needs a recovery plan first, which usually means a header backup and a second copy of the data.

## Free path: an encrypted container in a VM

Everything here is local and free. The commands are the ones I ran on 2026-11-07, in a Debian 12 cloud image under QEMU 10.0.13 with KVM and two virtual CPUs, as `root` (a fresh throwaway guest, so the focus stays on VeraCrypt and not on `sudo`). I ran the whole sequence three times. The first two runs failed for reasons of my own harness (the console lost the output, and a 120-second time limit I set was too short for a wrong password with no hash given). The output quoted below is from the third, complete run. The guest's CPU did not advertise AES instructions (`grep -w aes /proc/cpuinfo` printed nothing), so every time below is slower than it would be on your hardware; use the ratios, not the seconds.

Set up: you need a Linux guest (see the [virtual machines lesson](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md)) and the VeraCrypt console package for your distribution from the project's Downloads page. I installed the Debian 12 console `.deb` for 1.26.31. I checked its detached signature against the project's published PGP key on the host first; `gpg` reported a good signature and the key fingerprint matched the one printed on the project's home page. That fingerprint comes from the same site, so it proves the file matches the key and not that the key is the right one.

### Exercise 1: predict (no commands)

1. **Predict.** You have a 20 MB container file with a file system inside it. (a) What does `file` say about it? (b) If you save a note containing the words "marker line" in it, then dismount, will `grep` find those words in the container file? (c) What happens on a wrong password: an error, or a quiet empty folder? (d) Does a wrong password take about as long to reject as a right one takes to accept? (e) After you change the password, does the old one still work, and does a copy of the container made before the change still open with it?
2. **Do.** Write your answers down, then check them with Exercises 2 to 5.
3. **Check.** The results are in the exercises that follow.
4. **Undo.** Nothing.

### Exercise 2: create, mount, write and dismount

1. **Predict.** How long does creating the container take, and how long does one mount take with 500,000 iterations of SHA-512?
2. **Do.** Placeholder passwords only, for a throwaway guest:

   ```bash
   mkdir -p ~/vclab /mnt/vc && cd ~/vclab
   PW='PLACEHOLDER-one'
   time veracrypt --text --create demo.hc --volume-type=normal --size=20M \
     --encryption=AES --hash=SHA-512 --filesystem=ext4 --pim=0 -k "" \
     --random-source=/dev/urandom -p "$PW" --non-interactive
   file demo.hc
   time veracrypt --text --mount demo.hc /mnt/vc --hash=SHA-512 -p "$PW" \
     --pim=0 -k "" --protect-hidden=no --non-interactive
   echo "this is a marker line that must not appear in the container file" > /mnt/vc/note.txt
   sha256sum /mnt/vc/note.txt
   df -h /mnt/vc | tail -1
   veracrypt --text --list
   sync
   veracrypt --text --unmount /mnt/vc
   veracrypt --text --list
   grep -c "marker line" demo.hc || echo "marker not found in demo.hc"
   ```

   For real use, drop `-p "$PW"` and `--non-interactive` and let the program prompt for the password, so it is never on a command line. `--random-source` adds a file's bytes to the program's entropy pool (I used `/dev/urandom`; the graphical wizard asks you to move the mouse for this step). `--hash=SHA-512` on the mount tells VeraCrypt which hash the volume was made with, which Exercise 3 shows is worth knowing.
3. **Check.** What the guest printed (the order of the lines trimmed to the useful ones):

   ```text
   The VeraCrypt volume has been successfully created.        real 0m21.073s
   demo.hc: data
                                                              real 0m4.596s   (the mount)
   c40b68b6eed62b92108fe68b81440545cafc3ff192b8173abc01035ecea5634f  /mnt/vc/note.txt
   /dev/mapper/veracrypt1   18M   15K   16M   1% /mnt/vc
   1: /root/demo.hc /dev/mapper/veracrypt1 /mnt/vc
   Error: No volumes mounted.                                 (after the unmount)
   0
   marker not found in demo.hc
   ```

   `file` could not name the container (`data`), because it has no signature. The file system appeared as a device under `/dev/mapper`, which is the kernel's device-mapper doing the on-the-fly decryption. The marker text was not in the container file on disk: `grep -c` printed `0`. Creating took about 21 seconds for 20 MB in a guest without AES instructions; one mount took about 4.6 seconds.
4. **Undo.** `rm -f demo.hc` removes the container.

### Exercise 3: a wrong password

1. **Predict.** Does a wrong password mount an empty volume, or fail? Does it fail fast?
2. **Do.** Once with the hash named, once without:

   ```bash
   time veracrypt --text --mount demo.hc /mnt/vc --hash=SHA-512 -p 'PLACEHOLDER-two' \
     --pim=0 -k "" --protect-hidden=no --non-interactive; echo "exit status: $?"
   veracrypt --text --list
   time veracrypt --text --mount demo.hc /mnt/vc -p 'PLACEHOLDER-two' \
     --pim=0 -k "" --protect-hidden=no --non-interactive; echo "exit status: $?"
   ```
3. **Check.** Both attempts printed the same error and exit status 1, and nothing was mounted:

   ```text
   Error: Operation failed due to one or more of the following:
    - Incorrect password.
    - Incorrect Volume PIM number.
    - Incorrect PRF (hash).
    - Not a valid volume.
    - Volume uses an old algorithm that has been removed.
    - TrueCrypt format volumes are no longer supported.
   ```

   The message does not say which of those it was, which is deliberate: a wrong password and a file that is not a volume look the same. The times differed a great deal. **With the hash named, the rejection took 7.3 seconds. With no hash named, it took 1 minute 26.8 seconds**, about twelve times longer, because the program tries every hash it supports before it gives up. (The 7.3 seconds against 4.6 for a right password fits two header attempts, the standard one and the area where a hidden volume's header would be; that reading is **est.**, from the project's description of how it tries the second header.) Nothing about a wrong guess is cheap, and that is the point of a key derivation function.
4. **Undo.** Nothing was mounted, so nothing to undo.

### Exercise 4: change the password

1. **Predict.** After you change the password, the old one fails. Does a copy of the container made before the change still open with the old password?
2. **Do.**

   ```bash
   cp demo.hc demo-before-change.hc
   time veracrypt --text -C demo.hc --hash=SHA-512 -p "$PW" --pim=0 -k "" \
     --new-password='PLACEHOLDER-three' --new-pim=0 --new-keyfiles="" \
     --new-hash=SHA-512 --random-source=/dev/urandom --non-interactive
   veracrypt --text --mount demo.hc /mnt/vc --hash=SHA-512 -p "$PW" --pim=0 -k "" \
     --protect-hidden=no --non-interactive
   veracrypt --text --mount demo.hc /mnt/vc --hash=SHA-512 -p 'PLACEHOLDER-three' \
     --pim=0 -k "" --protect-hidden=no --non-interactive
   cat /mnt/vc/note.txt; veracrypt --text --unmount /mnt/vc
   veracrypt --text --mount demo-before-change.hc /mnt/vc --hash=SHA-512 -p "$PW" \
     --pim=0 -k "" --protect-hidden=no --non-interactive
   cat /mnt/vc/note.txt; veracrypt --text --unmount /mnt/vc
   ```
3. **Check.** The change took 42 seconds and printed `Password, PIM and/or keyfile(s) successfully changed.` The old password then failed with the same six-line error as above. The new one mounted and `note.txt` read back as written. The copy made **before** the change still opened with the old password and showed the same note. A password change rewrites the header, not the data, so an older copy of the header opens an older door; on a solid-state drive the same can happen without you making a copy, which is the wear-leveling warning in [Operating habits that matter](#operating-habits-that-matter).
4. **Undo.** `rm -f demo-before-change.hc`.

### Exercise 5: lose the password on purpose

1. **Predict.** If the new password is generated, never shown and never saved, what recovers the data?
2. **Do.** The shell variable is unset right after use, so the value is gone:

   ```bash
   LOST=$(head -c 24 /dev/urandom | base64)
   veracrypt --text -C demo.hc --hash=SHA-512 -p 'PLACEHOLDER-three' --pim=0 -k "" \
     --new-password="$LOST" --new-pim=0 --new-keyfiles="" --new-hash=SHA-512 \
     --random-source=/dev/urandom --non-interactive
   unset LOST
   for p in "$PW" 'PLACEHOLDER-three' 'PLACEHOLDER-two'; do
     veracrypt --text --mount demo.hc /mnt/vc --hash=SHA-512 -p "$p" --pim=0 -k "" \
       --protect-hidden=no --non-interactive; echo "exit $?"
   done
   veracrypt --text --list
   ```
3. **Check.** All three known passwords failed with exit status 1, and `--list` printed `Error: No volumes mounted.` The container is 20 MB of data that nothing I know can read. Nothing in the program or the project's documentation offers a way back: the FAQ says there is no backdoor and that "the only way to recover your files is to try to 'crack' the password or the key". The older copy from Exercise 4 is the one thing that still opens, which is a lesson about backups and also about why an old copy is a liability if the old password leaked.
4. **Undo.** `rm -f demo.hc demo-before-change.hc`. The data was a note you wrote for this exercise.

### Exercise 6: the cost of a guess with Argon2id

1. **Predict.** Does Argon2id (new in 1.26.29), at its defaults, take more or less time to mount than PBKDF2 with 500,000 rounds?
2. **Do.** Make a second container with `--hash=Argon2id`, the same size and file system, and time its creation and one mount:

   ```bash
   time veracrypt --text --create argon.hc --volume-type=normal --size=20M \
     --encryption=AES --hash=Argon2id --filesystem=ext4 --pim=0 -k "" \
     --random-source=/dev/urandom -p "$PW" --non-interactive
   time veracrypt --text --mount argon.hc /mnt/vc --hash=Argon2id -p "$PW" \
     --pim=0 -k "" --protect-hidden=no --non-interactive
   veracrypt --text --list
   veracrypt --text --unmount /mnt/vc
   ```
3. **Check.** Creation took 1 minute 1.7 seconds (against 21 seconds for the SHA-512 container) and one mount took 4.9 seconds (against 4.6). So at the defaults the two cost about the same per mount here; the difference between them is what the work is made of (memory for Argon2id, plain computation for PBKDF2), not the wait, and I did not measure a graphics-card attack. Why creation took longer I did not investigate.
4. **Undo.** `rm -f argon.hc`. Then shut the guest down and delete its disk image.

### Not run, by name

A hidden volume, a keyfile, an entire partition, system encryption and the graphical wizard were **not run**. If you try the hidden volume, do it in the same throwaway guest with a new container, and write down your prediction of what an observer sees before you do ([Hidden volumes and plausible deniability, with the limits](#hidden-volumes-and-plausible-deniability-with-the-limits) lists what to check). To see what protects your real machine, the status commands are `lsblk -f` and `cryptsetup status <name>` on Linux, `manage-bde -status` in an administrator PowerShell on Windows, and `fdesetup status` on macOS (**not run** by me; the last two are from memory, so check the vendor pages in the claims register).

## Flip the board

**The reviewer.** A colleague writes: "I put the client files in a 2 GB VeraCrypt container on my laptop's SSD, stored the password in a note on the same desktop, synced the container to my cloud drive, and I use a hidden volume in case I get stopped at a border. I leave it mounted while I work all day." Find at least six problems.

<details>
<summary>What to find</summary>

1. The password is next to the container; anyone who gets the desktop gets both.
2. A mounted all-day volume is open to anything running as that user; malware, a stolen unlocked laptop and a cold boot all see plaintext.
3. A hidden volume on an SSD runs into the project's own rule against wear-leveling devices for anyone who needs deniability.
4. A synced container changes in an observable way in the cloud on every save, and a copy or a version of it sits in the provider's history, which the project warns can defeat a hidden volume.
5. There is no header backup and no stated recovery path; lose the header or the password and the files are gone.
6. The plan does not say what the full-disk encryption on the laptop is, or whether the paging and hibernation files are covered.
7. "In case I get stopped" is a legal question, not a technical one, and the plan has not asked anyone who knows.
8. No second copy of the data: a container is a single point of failure, not a backup.

</details>

**The auditor.** A manager says "all laptops have BitLocker, so lost-laptop risk is closed." Name three things to check before agreeing. (Whether it is actually on and protected, not suspended or running on a clear key; whether it uses a TPM with a PIN or password at boot or only the TPM; where the recovery keys are stored and who can read them; whether the fleet includes a Mac or a Linux machine; whether backups are encrypted.)

## Checkpoint

Without looking back: say why a powered-off laptop and a running one get different protection; name the control that answers cold boot and the one that answers evil maid; say where the key lives for BitLocker, FileVault and LUKS; state what a keyfile and a PIM are; give three reasons a hidden volume fails to give deniability; give the date and the first sentence of the TrueCrypt notice; say what audit phase 2 found and in how many findings; say what VeraCrypt raised the key-derivation cost to; and explain why a hardware key and a password manager do not replace a recovery plan for a container.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "It's encrypted, so it's safe" | Encrypted at rest covers the powered-off case only | Is the volume mounted? Is the machine on? |
| "BitLocker is on" | It may be suspended, or sealed with a clear key on a local-only account | `manage-bde -status` or the Settings page; whether the recovery key was backed up |
| "FileVault is optional on a modern Mac, the disk is encrypted anyway" | The volume is, but the key is bound to the hardware only until FileVault ties it to your password | Apple's FileVault page; turn it on |
| "I'll pick Serpent-AES-Twofish for more security" | A cascade costs speed and does not fix a weak password | The password length and the KDF |
| "A keyfile makes my short password strong" | The audit called the old mixing unsound at Low severity, and a keyfile is still one file to lose | Use a long password; keep a keyfile for a second factor only |
| "I changed the password, so the old one is dead" | On SSDs and flash, an old header may survive | The wear-leveling page; restore from a copy only on media you control |
| "My hidden volume is deniable" | Only if you also handle sector changes, the host system, TRIM, wear-leveling and decoy habits | The hidden-volume requirements page |
| "VeraCrypt lost my data" | A forgotten password cannot be recovered by the project or anyone | Header backup and a recovery plan made before you need it |
| "TrueCrypt was proven backdoored" | The audit found no backdoor. The shutdown reason was never confirmed | The two audit reports |
| "I'll use TrueCrypt, it was audited" | The code has been unmaintained since 2014 and later fixes live in forks | Convert with VeraCrypt 1.25.9 |

## Claims register

Retrieved 2026-11-07 with read-only requests, unless stated. "Read" means I read the page text. "Secondary" means a source that is not the project or vendor.

| Claim | Source | Status |
|---|---|---|
| VeraCrypt: free open source disk encryption for Windows, macOS and Linux; "based on TrueCrypt 7.1a"; brought by AM Crypto; release 1.26.31 on 2026-11-02; Argon2id added in 1.26.29 on 2026-06-09; project statements on TrueCrypt's iteration counts | [veracrypt.io home](https://veracrypt.io/en/Home.html) | Read. The TrueCrypt figures are the VeraCrypt project's own |
| Release history: 1.0d (2014-06-03), 1.0e, 1.0f, 1.0f-2, 1.12, 1.18a, 1.24, 1.26.7 (TrueCrypt mode and RIPEMD-160 removed), 1.26.29 to 1.26.31 | [VeraCrypt release notes](https://veracrypt.io/en/Release%20Notes.html) | Read |
| Supported systems: Windows 10 1809 and later, Windows 11, macOS 12 and later, Linux, FreeBSD 14 and later, OpenBSD 7.8 and later, Raspberry Pi OS | [Supported operating systems](https://veracrypt.io/en/Supported%20Operating%20Systems.html) | Read |
| Ciphers (AES, Camellia, Kuznyechik, Serpent, Twofish and cascades), XTS, 256-bit keys, 128-bit block | [Encryption algorithms](https://veracrypt.io/en/Encryption%20Algorithms.html) | Read |
| PBKDF2-HMAC hashes (BLAKE2s-256, SHA-256, SHA-512, Whirlpool, Streebog) and Argon2id; defaults 500,000, 200,000 and 500,000 iterations; PIM formulas; Argon2id default equals PIM 12 (416 MiB, 6 passes); 512-bit salt; Argon2id for non-system volumes only | [Hash algorithms](https://veracrypt.io/en/Hash%20Algorithms.html), [Header key derivation](https://veracrypt.io/en/Header%20Key%20Derivation.html), [PIM](https://veracrypt.io/en/Personal%20Iterations%20Multiplier%20%28PIM%29.html) | Read |
| Keyfiles: any file, first 1 MiB processed, PKCS #11 tokens, EMV cards, CRC-32 pool then KDF; 30-byte and real-entropy rule; password length advice of more than 20 characters | [Keyfiles](https://veracrypt.io/en/Keyfiles.html), [Choosing passwords and keyfiles](https://veracrypt.io/en/Choosing%20Passwords%20and%20Keyfiles.html) | Read |
| Hidden volume, plausible deniability, and the security requirements and precautions for hidden volumes | [Hidden volume](https://veracrypt.io/en/Hidden%20Volume.html), [Plausible deniability](https://veracrypt.io/en/Plausible%20Deniability.html), [Security requirements for hidden volumes](https://veracrypt.io/en/Security%20Requirements%20for%20Hidden%20Volumes.html) | Read |
| Wear-leveling, TRIM, data leaks, unencrypted data in RAM, physical security, malware | [Wear-leveling](https://veracrypt.io/en/Wear-Leveling.html), [TRIM](https://veracrypt.io/en/Trim%20Operation.html), [Data leaks](https://veracrypt.io/en/Data%20Leaks.html), [Unencrypted data in RAM](https://veracrypt.io/en/Unencrypted%20Data%20in%20RAM.html), [Physical security](https://veracrypt.io/en/Physical%20Security.html), [Malware](https://veracrypt.io/en/Malware.html) | Read |
| System encryption is for the drive Windows is installed on; the boot loader is unencrypted | [System encryption](https://veracrypt.io/en/System%20Encryption.html) | Read |
| The FAQ: no backdoor and no recovery for a forgotten password; TrueCrypt volumes can be mounted and converted since 1.0f | [VeraCrypt FAQ](https://veracrypt.io/en/FAQ.html) | Read. The page is marked last updated 2017-07-02 |
| TrueCrypt shutdown notice text, 7.2, authenticity caveats | [Ars Technica, 2014-05-28](https://arstechnica.com/information-technology/2014/05/truecrypt-is-not-secure-official-sourceforge-page-abruptly-warns/) | Read. The TrueCrypt page itself was blocked to me; Ars quotes it |
| Audit phase 1 result and wording; fundraising amount | [Ars Technica, 2014-04-14](https://arstechnica.com/information-technology/2014/04/truecrypt-audit-finds-no-evidence-of-backdoors/) | Read (secondary). I did not read the iSEC report |
| Audit phase 2: four findings, two High, one Low, one Undetermined, TrueCrypt 7.1a, report dated 2015-03-13 | NCC Group, *Open Crypto Audit Project TrueCrypt Cryptographic Review*, v1.0 (archived copy of the PDF at web.archive.org, from the Open Crypto Audit Project site) | Read. The live host returned an error on 2026-11-07 |
| Audit phase 2 summary and the RNG and cache-timing findings | [Matthew Green, "Truecrypt report", 2015-04-02](https://blog.cryptographyengineering.com/2015/04/02/truecrypt-report/) | Read |
| VeraCrypt audit by Quarkslab: 8 critical, 3 medium, 15 low or informational; fixes in 1.19 | [OSTIF, 2016-10-17](https://ostif.org/the-veracrypt-audit-results/) | Read. Report not read |
| TrueCrypt history before 2014, the forks, the Fraunhofer audit, the 2026 signing episode, VeraCrypt's licensing | [Wikipedia: TrueCrypt](https://en.wikipedia.org/wiki/TrueCrypt), [Wikipedia: VeraCrypt](https://en.wikipedia.org/wiki/VeraCrypt) | Read (secondary). Not checked against primary pages |
| BitLocker: purpose, TPM, PIN and startup key, XTS-AES 128 default for device encryption, device encryption availability, local-account caveat, password option discouraged, editions | [Microsoft Learn: BitLocker overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/) | Read. Page marked last updated 2026-08-24 |
| BitLocker countermeasures: pre-boot authentication, TPM with PIN anti-hammering, DMA, memory remanence, reset attacks, bootkits | [Microsoft Learn: BitLocker countermeasures](https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/countermeasures) | Read |
| FileVault: AES-XTS, key hierarchy, Secure Enclave, recovery key, escrow, deletion caveat | [Apple Platform Security: volume encryption with FileVault](https://support.apple.com/guide/security/volume-encryption-with-filevault-sec4c6dc1b6e/web) | Read. Page marked published 2026-01-28 |
| LUKS: key slots, anti-forensic stripes, LUKS2 default, PBKDF2 for LUKS1 and Argon2 for LUKS2 | [cryptsetup(8) manual](https://man7.org/linux/man-pages/man8/cryptsetup.8.html), and `cryptsetup --version` and `--help` output on my machine (2.7.5) | Read, and observed |
| Cold boot attacks; DRAM keeps its contents for seconds; screen lock and sleep do not protect memory | [Halderman et al., *Lest We Remember*, USENIX Security 2008](https://www.usenix.org/legacy/event/sec08/tech/full_papers/halderman/halderman.pdf) | Read (abstract, introduction and the section on suspending a system) |
| Evil maid proof of concept against TrueCrypt, 2009-10-16 | [Invisible Things Lab blog](https://theinvisiblethings.blogspot.com/2009/10/evil-maid-goes-after-truecrypt.html) | Read |
| The VeraCrypt package signature verified against the published key; fingerprint printed on the home page | `gpg --verify` on my machine, 2026-11-07 | Observed |
| Container creation, mount, write, dismount, wrong password, password change and the Argon2id timing | My run in a Debian 12 guest, 2026-11-07 | Observed (see the exercises) |
| FAT's 4 GB limit; file sync re-uploads whole files; memorized phrase advice; VeraCrypt's Argon2id volumes unreadable by older versions | Not sourced | **est.** |

## Not verified, plainly

The two exercises on hidden volumes and keyfiles were not run. The graphical program was not used. I did not run anything on Windows or macOS. The audit reports for phase 1 (iSEC) and for the Quarkslab audit were not read, only summaries of them. Wikipedia is a secondary source and I used it only where marked. Law on compelled passwords was not researched.
