# Open firmware and trustworthy hardware: coreboot, Heads, Nitrokey and vendors that ship the Intel ME disabled

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 2: Defend and detect](Contents.md#track-2-defend-and-detect) > Open firmware and trustworthy hardware

Previous: [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md) / Next: [Digital forensics foundations](Digital-Forensics-Foundations-Evidence-Handling-Chain-of-Custody-and-Order-of-Volatility.md)
<!-- END GENERATED PAGE NAV top -->

Before Linux, Windows or macOS starts, a program stored on a flash chip on the motherboard has already run. It set up the memory, woke the devices and decided what to hand control to. That program is the firmware, on most laptops it is closed source, and it runs with more privilege than anything you install later. This page covers the open alternative (coreboot), the tool that lets the machine prove to you that its firmware did not change (Heads, with a hardware key), what a TPM and Secure Boot do and do not prove, and four vendors that sell machines with the Intel Management Engine switched off or cut down. For each vendor I read the vendor's own pages and wrote down exactly what they claim, and where I could not read a claim I left it out.

> **Status: unverified draft. Everything here comes from reading vendor and project pages on 2026-11-07, plus a few read-only checks on one Linux laptop. Nothing was flashed. I never built or booted coreboot or Heads, never used a hardware key with Heads, and never touched a machine from any of the four vendors.** The checks I ran, all on 2026-11-07 on one laptop with a Linux kernel and no root access: reading the firmware vendor, version and date from `/sys/class/dmi/id`; testing for `/sys/firmware/efi`; listing `/sys/class/tpm` and reading the TPM version; reading the `SecureBoot` and `SetupMode` EFI variables; listing `/dev/mei*`, `lspci` for the Management Engine interface and `/sys/class/mei/mei0/fw_ver`; `fwupdmgr security --no-unreported-check`; and one `curl` of coreboot's supported-board index. **Not run:** `bootctl` and `mokutil` (neither is installed on that laptop), `tpm2-tools`, `dmidecode`, and anything that needs root. Every vendor statement carries the date I read it in the [claims register](#claims-register); a claim I could not read there is marked **est.** or left out. Trust what your terminal prints over what this page says.

> **Prerequisites.** A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)) and the idea of a hash and a key ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)). A threat model helps more than any of the hardware: read [Threat model](Threat-Model.md) first if you have not. The exercises need a Linux computer and about 30 minutes (est.). They are read-only and cost nothing.

> **Where this runs, and the rule.** Everything is local and read-only. There are no flashing steps on this page, on purpose: replacing firmware can leave a machine that will not start, coreboot's own documentation says recovery can mean attaching tools to chips, and the vendors in this lesson exist partly so you do not have to. No affiliate links, no referral codes, and nothing here is a recommendation to buy.

## What you will be able to do

- Say what firmware is, how BIOS and UEFI differ, and what coreboot replaces.
- Explain a payload, and why coreboot supports a list of boards and not "most laptops".
- Say in plain words what a TPM and Secure Boot do, and three things neither proves.
- Describe how Heads uses a TPM and a hardware key so the machine can show you that its firmware did not change.
- Say why Heads needs a key with OpenPGP and a Nitrokey-style one-time-password check, and what that means for a YubiKey.
- Tell apart an Intel ME that is absent, neutralized, soft-disabled and HAP-disabled, and read a vendor's sentence for which one it is.
- Read what four vendors claim, with the date, the method and the models, and name what each page does not say.
- Run six read-only checks on your own machine and read what they print.

## What the wiki already says (and the gap)

[Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) explains hardware security keys in one paragraph, and [Hands-on Whonix and Qubes](Hands-On-Whonix-and-Qubes-OS-Gateway-Split-Compartments-Disposables-and-Policy-Prompts.md) lists a TPM as a requirement for Qubes Anti Evil Maid. The wiki says nothing about what runs before the operating system, which is the gap. Two sibling lessons are planned: a lesson on hardware security keys (issue #463, not written yet, so I give no link) and a lesson on device firmware security, the Intel ME, the AMD PSP and kernel design (issue #465, also not written yet). This page leans on neither; it says what it needs and points at them as plain text.

## Firmware, in plain words

**Firmware** is software stored on a chip on the board, run at power-on, that sets up the hardware and starts the next program. The old PC version was called the **BIOS**. Its replacement is **UEFI**, a larger specification. The Heads project's FAQ puts the size difference this way: UEFI "consists of millions of lines of code and is an entire operating system, with network device drivers, graphics, USB, TCP, https", and each of those features is surface for attack. The same FAQ points out a detail that gets lost: Intel's open source edk2 tree is the base of UEFI firmware, but "the firmware that vendors install on their machines is proprietary and closed source."

Two more facts shape everything below.

- **It survives your reinstall.** Firmware lives in flash chips, not on your disk. A summary of a 2025 talk on the Heads wiki cites a UEFI rootkit called CosmicStrand as one that "survives OS reinstalls". I did not check that report; the point that matters is where the code lives.
- **It is not one program.** Besides the main BIOS or UEFI, a modern laptop carries a separate embedded controller (keyboard, battery, fans), the Intel Management Engine on Intel machines, an AMD Platform Security Processor on AMD machines, and firmware inside the SSD, the Wi-Fi card and the Thunderbolt controller. "Open firmware" usually means the first of these, sometimes the embedded controller too. System76 lists its embedded controller separately ("Open EC") from its "Open Firmware"; that split is the vendor's own.

## coreboot: what it replaces, payloads and limits

coreboot describes itself as "open source boot firmware for various architectures" whose "design philosophy is to do the bare minimum necessary to ensure that hardware is usable and then pass control to a different program called the payload" (coreboot documentation, read 2026-11-07). So it replaces the part of the vendor firmware that initializes the processor, memory and devices. What you see after that is the payload's job.

**Payloads** the documentation names: SeaBIOS (an open implementation of the old PC BIOS interface), edk2 (UEFI), GRUB2 (the bootloader many Linux distributions use), depthcharge (Chromebooks), and a small Linux kernel that loads the real one. Heads is the last kind: "a distribution that bundles coreboot, Linux, busybox and custom tools". A coreboot machine with the edk2 payload still looks like a UEFI machine, which is how Novacustom and System76 ship.

Now the limits, which matter more than the pitch.

- **It is source code, not a product.** The project "only provides source code and does not ship ready-to-install coreboot-based firmware binaries". It expects "a firmware developer mindset", and warns that recovering from a bad flash can mean "hooking wires onto chips in your computer". Ready-made builds come from distributions: it names Purism and Chromebooks (shipped with the hardware) and Libreboot and MrChromebox (aftermarket).
- **It is a list of boards.** coreboot's own page says that without a deprecation rule it could "inflate the number of supported devices (probably 300+)" but only a tiny fraction would work. The index I read on 2026-11-07 (documentation build 26.09-586) links 161 board pages under 36 vendor directories, including emulators; System76 has 29 of them, Lenovo 23. Exercise 2 reproduces that count.
- **It still carries blobs.** The project says plainly that it distributes "a collection of vendor binaries (that we call 'blobs')" that "cover the parts of hardware init that we haven't managed to open up", and that "there's still hardware that can boot without any such binary components". On modern Intel that means the Firmware Support Package (FSP) and microcode; on AMD it means the platform initialization code and PSP firmware kept in an `amd_blobs` repository.
- **A vendor lock can stop it.** Heads' FAQ says newer ThinkPads carry Intel Boot Guard, "a closed source security function implemented by Intel to prevent unsigned custom firmware, such as coreboot and heads, from being installed." That is why you cannot put coreboot on any laptop you like, and why buying one that ships with it is the realistic route.

## TPM and Secure Boot: what they do and what they do not prove

**A TPM** (Trusted Platform Module) is a small chip that stores keys and can store "platform measurements that help ensure that the platform remains trustworthy" (Trusted Computing Group summary, read 2026-11-07). Its registers for measurements are called PCRs. A measurement is a hash of the code about to run. A PCR can only be extended, never set: the new value is a hash of the old value and the new measurement, so the final value summarizes everything that ran, in order (the TPM specification's design; I did not read the specification itself, so this one is general knowledge). With **measured boot** each stage hashes the next stage into a PCR before running it. Then a secret, such as a disk key, can be sealed to those values: the TPM releases it only if the PCRs match what they were when you sealed it (Arch Linux wiki, read 2026-11-07).

**Secure Boot** is a different mechanism. Microsoft's description: "the firmware checks the signature of each piece of boot software, including UEFI firmware drivers (also known as Option ROMs), EFI applications, and the operating system. If the signatures are valid, the PC boots". The allowed signers live in a database (`db`), the revoked ones in `dbx`, and a platform key (PK) "can be used to sign updates to the KEK or to turn off Secure Boot". On a retail machine the maker generated the PK. Microsoft's page adds a dated note I checked on 2026-11-07: the Secure Boot certificates it issued in 2011 "begin expiring in June 2026", and tells readers to review its guidance to avoid disruption.

| Mechanism | What it does | What it does not prove |
|---|---|---|
| Secure Boot | Stops boot software that is not signed by a key in `db`, or is listed in `dbx`, from starting | That the firmware doing the check is honest or unchanged. That the signed program has no bug. Who holds the keys is the maker's decision; Heads' FAQ calls this "signing keys are controlled by vendors" and says some distributions "have signed insecure kernels" that bypass it (their claim, not checked) |
| TPM with measured boot | Records what ran, and refuses to unseal a secret if the record differs | That anything was blocked: a TPM records, it does not stop. The TCG says a TPM "cannot control the software that is running on a PC". That the first measured code was honest: the chain has to start somewhere |
| Intel Boot Guard | On machines where the maker enabled it, verifies the firmware against the maker's key | That the firmware is open or yours; Heads' FAQ says it blocks custom firmware |

Heads' answer to "the chain has to start somewhere" is to put the first code in a write-protected region of flash that you control, so measurement begins with code you can read. That claim is the project's design statement, not something I tested.

## Heads: measured boot you can check

Heads is, in its own words, "an open source custom firmware and OS configuration for laptops and servers that aims to provide slightly better physical security" (Heads wiki, read 2026-11-07). It is coreboot plus a small Linux in the flash chip. It measures each step of the boot firmware into the TPM, and the wiki says that "makes it possible to attest to the user or a remote system that the machine has not been tampered with." The TPM can also hold the disk key, released only when the machine is in the state you expect. And the kernel, hypervisor and initrd are signed by keys you control.

How it shows you the result, from the Heads FAQ:

- **TOTP with your phone.** Heads shows a six-digit code on screen. Your phone, which has the same sealed secret, shows the same code. If the firmware changed, the TPM will not release the secret and the codes differ. It needs accurate time on the machine.
- **HOTP with a USB security key.** Heads sends codes to the key, and the key checks them. A wrong code makes the key's LED show red. This works without a phone or accurate time. Rankin's talk, as summarized on the Heads wiki, states the reason: "you can't trust the computer. What you can trust is this key."
- **OpenPGP signing of `/boot`.** Every Heads setup uses the key's OpenPGP function to sign the kernel and boot files, so a changed kernel fails before it starts.

Two properties people miss. First, Heads detects, it does not prevent: "Heads is not designed to block the boot process, but to detect tampering" (Novacustom's Heads page), and on a failed check the FAQ says it "alerts rather than locks the user out". Second, there is a real usability cost. A 2024 Qubes design session, summarized on the Heads wiki, has Nitrokey's founder calling the re-signing needed after every kernel update "a burden" that blocks mainstream use. That summary is secondhand; read the talk if it matters to you.

Which machines? The hardware compatibility page of the Heads wiki, read on 2026-11-07, lists many Lenovo ThinkPad and ThinkCentre boards, a Dell OptiPlex, MSI desktop boards, two Chrome devices, a Raptor Talos II and the NitroPad NS50, NovaCustom NV4x ADL, V540TU and V560TU. Its prerequisites page says boards that repeatedly went untested were moved to an `unmaintained_boards` directory and are no longer built. The FAQ says installing Heads "requires opening the machine and extensive warranty voiding". I give no steps for that, here or anywhere.

## The key that checks the firmware: Nitrokey and YubiKey

The Heads prerequisites page, read on 2026-11-07, says every key used with Heads "must support OpenPGP", that HOTP verification uses a protocol "developed by Nitrokey", and that "Heads does NOT support FIDO2 or U2F authentication" so "be careful when purchasing". Its compatibility table:

| Key | OpenPGP | HOTP check | Heads says |
|---|---|---|---|
| Yubico YubiKey 5 Series | yes | no | OpenPGP only: works with the phone-code (TOTP) setups |
| Nitrokey Pro 2 | yes | yes | Full support |
| Nitrokey Storage 2 | yes | yes | Full support |
| Nitrokey 3 | yes | yes | Full support |
| Purism Librem Key | yes | yes | Full support |

The same page notes that the Nitrokey 3 comes in USB A, A-mini and C, and that the A-mini is "the one most shipped with novacustom and nitropads".

**Why Nitrokey is called the open-leaning choice.** Nitrokey's about page calls it "the world-leading company in open source security hardware" (the company's own words), says its developments are available to the public so that others "can check and audit" them, says all Nitrokeys are produced in Germany, and describes a Secure Element as optional. I did not check which Nitrokey 3 parts are open, what the Secure Element is, or whether anyone has audited the source. Yubico takes the other side in a post dated 2016-05-16: "The YubiKey hardware with its integral firmware has never been open sourced", the firmware cannot be updated in the field on purpose, and it argues that open source and secure-element certification pull in different directions. That post is about the YubiKey 4 and NEO; whether it still describes the YubiKey 5 I did not check (**est.** that it does). Both positions are arguments, not tests. For this lesson the practical difference is simpler: with Heads, a Nitrokey does the one-time-password check and a YubiKey 5 does not.

The hardware keys lesson (issue #463, not written yet) is the place for FIDO2, PIV and what to buy for logins. Here the key is a witness, nothing more.

## The Intel ME and the words vendors use

The Intel Management Engine is a small separate processor inside Intel's processor package, with its own firmware. Purism's page describes it as "a separate independent processor core" in "ring -2", and the Heads wiki as a coprocessor that "can be powered even when the main CPU is off". It cannot be removed on any Intel machine since Nehalem: Dasharo's documentation says that from ME version 6 on, the firmware "can't be completely removed. If ME firmware is missing, the PC will not boot at all", and System76's firmware documentation says the ME has been "required (since Nehalem, 2008)". Vendors therefore use four different verbs, and the difference is the whole lesson.

| Word | What is done | What is left |
|---|---|---|
| **Absent** | The processor has no Intel ME, as on AMD | AMD has its own Platform Security Processor, "an on-die, isolated security processor that runs independently from the main x86 cores" with its own firmware in the same flash (coreboot documentation) |
| **Neutralized** (also "neutered") | A tool such as me_cleaner deletes the non-essential ME modules and keeps the few the hardware needs to start | A stub: Dasharo lists the modules left (for ME 11 and later `rbe`, `kernel`, `syslib`, `bup`, sometimes `mfs`). Dasharo calls it "not recommended in production without extensive testing" because of power-management problems, and says it is not supported on all platforms |
| **Soft-disabled** | The BIOS sends the ME a command over the Intel management interface telling it to stop | The full ME firmware, which stays disabled "until a corresponding ENABLE message is sent" (Dasharo) |
| **HAP-disabled** | A bit in the flash descriptor (called AltMeDisable on older ME, HAP, "High Assurance Platform", on ME 11 and later) tells the ME to halt | The full ME firmware, halted earlier than a soft disable. Dasharo adds that clearing the bit enables it again |

Purism uses two of those at once: it says it "neutralized" the ME with me_cleaner and also "disable[s] the Intel Management Engine using ... the HAP bit". Dasharo's firmware offers a menu with the words "Enabled", "Disabled (Soft)" and "Disabled (HAP)". A sentence that says only "disabled" has not told you which of the four it is. The separate Intel AMT remote-management feature, which needs a vPro processor, is another matter: Purism says its Librem computers avoid processors with AMT.

## Four vendors, read from their own pages

All pages below were read with `curl` on **2026-11-07**. Several of the vendors' pages carry no publication date; the one date I found is noted. I record what the page says, not what I think is true.

### Novacustom

- **Firmware.** "Our laptops and mini PCs are equiped with Dasharo coreboot open-source firmware" (home page), assembled in the Netherlands. Dasharo is a coreboot and edk2 firmware distribution with its own documentation site.
- **ME.** Two sources, which together say more than either. Novacustom's SecurityTitan page (V54 and V56, "Intel 14th Gen", Core Ultra 7) lists "Disabled Intel ME: Disabling the Intel Management Engine (ME) minimizes potential security risks substantially." It does not say which method. Dasharo's setup-menu documentation says the ME mode is a setting with three values (Enabled, Disabled (Soft), Disabled (HAP)), and Dasharo's test specification checks that, after flashing Dasharo, the field says **Enabled**. That test is generic to Dasharo, so for any particular Novacustom model I do not know the shipped default (**est.** that it is user-selectable). Novacustom's own Dasharo comparison page lists a row "Intel ME disabling (HECI and HAP)"; the text I fetched does not show which columns carry a check mark, so I read it only as the options being offered.
- **Heads.** Sold as a variant: "NV41 Series, V54 Series and V56 Series only, requires a subscription". The SecurityTitan models ship with coreboot and Heads, a USB security device, anti-tamper measures and Qubes OS installed. Novacustom's Heads setup page shows a Nitrokey 3 PIN among the credentials and tells you to check the Nitrokey's LED at boot. The Heads hardware compatibility page names NV4x ADL, V540TU and V560TU.
- **Prices and support as displayed.** From 1,420 EUR (V54 14 inch) and 1,460 EUR (V56 16 inch), 930 EUR for the NUC Box; SecurityTitan V54 2,695 EUR and V56 2,749 EUR shown as sale prices (original 3,256 and 3,296); "3 years of warranty and 7 years of firmware updates and guaranteed spare parts availability". Whether taxes are included I did not check.

### System76

- **Firmware.** "System76 Open Firmware is an open source distribution of firmware utilizing coreboot, EDK2, and System76 firmware applications" (support documentation, last updated 2026-08-14 on the page).
- **ME.** The support page says: "System76 laptops will have the Intel Management Engine (IME) disabled when it does not break functionality." For Open Firmware systems the IME "is typically disabled by default unless doing so would break functionality (such as suspend/resume)". The firmware repository documentation names the method: instead of me_cleaner, which "does not support the ME version used on many of our systems", they "send a HECI command" to disable runtime components during early boot, and "most Intel-based machines from System76 come with the IME disabled". The same file records the cost: disabling the ME with the HAP bit or a HECI command keeps the CPU in a shallower state and "nearly triples the power usage in S0ix suspend" (modern standby), "from around 1 watt to around 3 watts". By Dasharo's definitions that is a soft disable; I take the two descriptions to be the same class (**est.**).
- **Which models.** Not all of them, and not the newest in every line. The vendor's table, last updated 2026-08-14, marks Open Firmware "Yes" for Darter Pro darp6 and newer, Galago Pro galp4 and newer, Lemur Pro lemp9 and newer, Oryx Pro oryp6 through oryp12, Serval WS serw13 and Meerkat meer9; and "No" for Oryx Pro oryp13, Serval WS serw14, Bonobo WS bonw15-b and newer, Adder WS addw5 and Meerkat meer10. A few models "shipped with closed firmware/EC, but have since been updated to Open Firmware/EC".
- **Proprietary-firmware models.** Where the setting exists, it "is usually disabled by default, although there have been some models that required re-disabling after an over-the-air firmware update".
- **Heads.** Not mentioned on the pages I read. I did not record System76 prices.

### Purism

- **Firmware.** coreboot with Heads, sold as PureBoot with the Librem Key. coreboot's own documentation names Purism as shipping coreboot with its hardware, and lists boards for the Librem 14 and Librem Mini.
- **ME.** The Intel ME page (undated) says Purism laptops "can function with a neutralized and disabled ME", and describes both: me_cleaner removes "the Intel ME's kernel, network stack, and about 90-92% of the Intel ME binary in total (this figure varies across ME versions)", and the HAP bit disables it "cleanly". It adds that its policy is to ship the ME-related fuses unset ("unfused") so the user keeps control. It also says "We are still working to completely remove (or reverse engineer ...) the Intel ME (and other components, such as the Intel FSP)", so the vendor itself says the job is not finished.
- **Which models.** The Librem 14 (Core i7-10710U, Comet Lake) page lists "Disabled the Intel Management engine" and "Less binary blob firmware", plus write-protected BIOS and EC chips with hardware switches. The Librem Mini (Core i7-10510U, Comet Lake) lists "Disabled Intel Management Engine". The Librem 11 (Intel N5100, Jasper Lake) page says it ships with PureBoot, coreboot and Heads, and says nothing about the ME, so I claim nothing for it. Comet Lake is a 2019 and 2020 generation (**est.**).
- **Prices.** I did not capture a machine price from these pages.

### Tuxedo Computers

I could not verify a claim. Here is what I could read and what I could not.

- Tuxedo's pages that `curl` can fetch (home page, "why TUXEDO", news, the notebook category page) are built by script, and none of the text I got says anything about the Intel ME or coreboot. The FAQ page returned an empty shell. If Tuxedo has a statement, it was not in what I could read.
- The notebook category page says it pairs graphics cards with "Intel's or AMD's most powerful processors". So some Tuxedo machines have no Intel ME at all (the AMD case in the table above), and the AMD PSP and AMD's initialization blobs remain.
- Dasharo's documentation has a release for the Tuxedo InfinityBook S 15 Gen6, version 1.0.0 dated 2022-03-15, built on coreboot 4.16 with edk2, with "Support for Intel ME version 15.0.30.1776" and UEFI Secure Boot. That is a Dasharo release page, not a Tuxedo claim. I do not know whether Tuxedo ships it or whether any current model has it, so I leave "Tuxedo ships the ME disabled" out. Ask Tuxedo in writing, for the exact model, which of absent, neutralized, soft-disabled or HAP-disabled applies, and who made the firmware.

### Side by side

| What I read | Novacustom | System76 | Purism | Tuxedo |
|---|---|---|---|---|
| What the vendor says about the ME | "Disabled Intel ME" on SecurityTitan; Dasharo offers a setting | Disabled when it does not break functionality | "Neutralized and disabled"; "Disabled" on two models | Nothing I could read |
| Method named | Soft or HAP (Dasharo menu) | HECI command (soft), not me_cleaner | me_cleaner and the HAP bit | none |
| Firmware | Dasharo coreboot with edk2; Heads as a paid variant on three series | System76 Open Firmware: coreboot, edk2 | coreboot with Heads (PureBoot) | not stated on pages I read |
| Models named | NV41, V54, V56 (Heads); SecurityTitan | A list by model code, some lines not covered | Librem 14, Mini; Librem 11 with PureBoot but no ME claim | none |
| Hardware key | Nitrokey 3 in the Heads setup | not on pages I read | Librem Key | none |

## What "disabled" leaves behind

- **The ME firmware is still in the flash.** In Dasharo's openness-score page for a NovaCustom NV4x ADL image (v1.7.2), the Intel ME region is listed as 0x4b6000 bytes, about 4.7 MiB, category "closed-source". Disabling is a state, not a deletion.
- **Other blobs.** The same score pages list the FSP files and the CPU microcode as closed. Dasharo's own utility reports the Heads image v0.9.3 for the NV4x ADL as 60.0% open and 40.0% closed code, and the v1.8.0 build as 30.8% open and 69.2% closed. Novacustom's own wording is "only necessary and unavoidable binary blobs". Heads' wiki says it plainly: "While modern Intel CPUs require binary blobs to boot, these non-Free components are included in the measurements and are at least guaranteed to be unchanging". Measured is not the same as read.
- **Whoever can write the flash can undo it.** Dasharo says choosing Enabled works by sending an enable command or "clearing the HAP bit in flash descriptor". Write protection of the flash (Purism advertises hardware write-protect switches) is what makes the setting hold.
- **Everything else with firmware.** The embedded controller, the SSD, Wi-Fi, Thunderbolt and the camera keep theirs. Heads' FAQ links reading on "the other embedded devices in the system" for this reason.
- **A price in battery.** System76's own figures above are the clearest I found.
- **The delivery.** A TPM check answers "did the firmware change since I set it up". It cannot tell you the machine was altered before you took ownership. Purism sells "Anti-Interdiction Services" and Novacustom's Heads page describes anti-tamper seals and photographs for the same reason.

## Price, support and who this is for

- **Cost.** At the prices Novacustom displayed, a Heads laptop from them starts well above a mainstream laptop and a SecurityTitan costs nearly double a base V54 (1,420 versus 2,695 EUR, the sale price), though it includes 64 GB of memory and a 2 TB drive. The Heads variant needs a subscription. I did not capture prices from the other three. Two Purism models I read about use 10th generation Comet Lake processors and the Librem 11 a Jasper Lake N5100; compare benchmarks for the work you do, not generation numbers.
- **Support life.** Novacustom states 7 years of firmware updates for the SecurityTitan. For the others I did not read a support period. Open firmware you cannot update is worse than a vendor's you can, so ask.
- **Who needs it.** Someone whose threat model includes physical access to the laptop (travel, border crossings, shared offices), or who wants firmware they can audit. For most people the larger risks are phishing, reused passwords and unpatched software, and an ordinary laptop with updates, disk encryption and a firmware password beats a Heads laptop that is never updated. Read [Threat model](Threat-Model.md) before spending the money.
- **The cheaper first step.** On the laptop you own, apply firmware updates (exercise 1 shows the tool), keep Secure Boot on, set a firmware password, and encrypt the disk.

## Exercise 1: what your own machine reports

Free, read-only, no root. Two of these need a tool that may not be installed; if a command is missing, skip it.

```bash
[ -d /sys/firmware/efi ] && echo "booted with UEFI" || echo "booted with legacy BIOS (or a container)"
cat /sys/class/dmi/id/bios_vendor /sys/class/dmi/id/bios_version /sys/class/dmi/id/bios_date
ls /sys/class/tpm
cat /sys/class/tpm/tpm0/tpm_version_major
od -An -t u1 /sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c
ls /dev/mei*
lspci | grep -i "management engine"
cat /sys/class/mei/mei0/fw_ver
fwupdmgr security --no-unreported-check
```

What I got on 2026-11-07, on one Intel laptop:

- UEFI boot: yes. Firmware vendor and version: the laptop maker's, version 1.45.0, dated 07/23/2026.
- `ls /sys/class/tpm` printed `tpm0`, and the version file printed `2`: a TPM 2.0 is present.
- The `SecureBoot` variable printed `6 0 0 0 0`. The first four numbers are the variable's attributes; the last is the value, `0`, which means **Secure Boot is off** on this laptop. (`SetupMode` also printed `0`, which means keys are enrolled; the machine is simply not enforcing them.) The `fwupdmgr` report agreed: "UEFI secure boot: Disabled".
- `/dev/mei0` exists and `lspci` showed a "Tiger Lake-LP Management Engine Interface": the ME is **running** on this machine. `fw_ver` printed `0:15.0.56.2834`.
- `fwupdmgr security` printed "HSI:1!" (the Host Security ID the tool computes). Among its lines: "csme v0:15.0.56.2834: Valid", "TPM v2.0: Found", "Intel BootGuard: Enabled", "Intel BootGuard verified boot: Valid", "SPI lock: Enabled", and failures for "Pre-boot DMA protection", "Encrypted RAM" and "BIOS rollback protection", with "Linux kernel lockdown: Disabled".

Read those lines against this page. Boot Guard enabled is why coreboot or Heads could not go on this machine, matching Heads' FAQ. A retail laptop with the ME running and a TPM present is the ordinary case, and the numbers are the reason a vendor's "ME disabled" sentence is worth asking about.

On a laptop with Dasharo set to a Disabled mode, Dasharo's documentation says "MEI/HECI interface is being hidden from OS when ME is disabled". If you ever see no `/dev/mei*` and no Management Engine line in `lspci`, that is consistent with a disabled ME; it is not proof. I could not test it. `bootctl status` and `mokutil --sb-state` report the same Secure Boot fact on machines that have them; I did not run either.

## Exercise 2: read a supported-hardware list

coreboot's list is public. This reads it and counts it; nothing is installed.

```bash
curl -s https://doc.coreboot.org/mainboard/index.html \
  | grep -o 'href="[a-z0-9_]*/[^"]*\.html"' | cut -d'"' -f2 | sort -u > boards.txt
wc -l < boards.txt
cut -d/ -f1 boards.txt | uniq -c | sort -rn | head -n 5
cut -d/ -f1 boards.txt | uniq | wc -l
grep -c -E '^(novacustom|tuxedo)/' boards.txt
```

On 2026-11-07 (documentation build 26.09-586) I got 161 pages; the top vendors were `system76` 29, `lenovo` 23, `asus` 17, `starlabs` 16 and `hp` 14; 36 vendor directories; and 0 for Novacustom and Tuxedo. Purism's two boards, `librem_14` and `librem_mini`, were there. Two lessons from that. A board in the list is a board that builds, not a board someone sells with a support promise. And Novacustom is not in the upstream list at all: its boards come through Dasharo, which is why the Dasharo and Heads hardware lists are the ones to read for a Novacustom claim. (That Dasharo builds on top of coreboot rather than replacing it is Novacustom's and Dasharo's description; I did not read the source.)

Then open the [Heads hardware list](https://osresearch.net/Hardware-Compatibility/) and find the board you own. If it is not there, that answers the question.

## Exercise 3: sort three vendor sentences

Pen and paper. For each real sentence, write which of absent, neutralized, soft-disabled or HAP-disabled it names, which models it covers, whether it is a default or a setting, and who could undo it. Then compare with what the pages actually say above.

1. "System76 laptops will have the Intel Management Engine (IME) disabled when it does not break functionality."
2. "Disabled Intel ME" (Novacustom SecurityTitan page).
3. "Purism laptops can function with a neutralized and disabled ME."

My answers: (1) the method is not in the sentence; the firmware documentation says a HECI command; models only where it does not break functionality; a setting in coreboot that a user can change. (2) No method, no default, and the Dasharo menu is a setting; ask. (3) "Can function with" is capability, not a statement about what ships; the product pages state "Disabled" for the Librem 14 and Mini.

## Checkpoint

1. Name the two things Secure Boot cannot tell you about the firmware.
2. Why does Heads use a key and not just the screen?
3. A seller says "ME removed". What is the first question?
4. Why would a vendor ship a laptop with the ME on, even with open firmware? (System76's page gives one.)
5. Your laptop shows Intel Boot Guard enabled. What does that do to the idea of putting coreboot on it?

## Common mistakes

- **Reading "Secure Boot is on" as "my firmware is trustworthy".** It checks signatures on what comes after the firmware.
- **Thinking a TPM blocks tampering.** It records and withholds secrets.
- **Buying a FIDO-only key for Heads.** Heads uses OpenPGP and, for the automatic check, the Nitrokey HOTP protocol. A YubiKey 5 is "OpenPGP only" in Heads' table.
- **Reading "disabled" as "removed".** The firmware is in the flash and can sometimes be re-enabled by a setting.
- **Assuming the newest model has the same firmware as last year's.** System76's table lists Oryx Pro oryp13 as "No".
- **Treating a vendor page as an audit.** Everything above is a claim by the seller or its firmware partner. I did not test any of it.
- **Flashing a machine because a guide exists.** Buy it pre-installed or leave the firmware alone.

## Claims register

Retrieved on 2026-11-07 with read-only requests. "Read" means I read the page text; "Observed" means I ran the command on one laptop.

| Claim | Source | Status |
|---|---|---|
| UEFI is much larger than BIOS; edk2 is open source but vendor builds are proprietary | [Heads FAQ](https://osresearch.net/FAQ/) | Read |
| coreboot's purpose, payload idea, named payloads (SeaBIOS, edk2, GRUB2, depthcharge) and the Linux and Heads payloads | [coreboot documentation home](https://doc.coreboot.org/index.html), [Payloads](https://doc.coreboot.org/payloads.html) | Read |
| coreboot ships source only, expects a developer mindset, distributes blobs, names Purism, Chromebooks, Libreboot and MrChromebox, deprecates devices ("probably 300+") | [coreboot documentation home](https://doc.coreboot.org/index.html) | Read |
| The mainboard index had 161 board pages, 36 vendor directories, system76 29 and lenovo 23 (my count of unique links) | [coreboot mainboard index](https://doc.coreboot.org/mainboard/index.html), build 26.09-586 | Observed |
| Purism's Librem 14 and Librem Mini are in the coreboot board list; no Novacustom or Tuxedo directory | [coreboot mainboard index](https://doc.coreboot.org/mainboard/index.html) | Observed |
| AMD PSP is an on-die isolated security processor with its own firmware in the shared flash; blobs live in `amd_blobs` | [coreboot documentation: AMD PSP](https://doc.coreboot.org/soc/amd/psp_integration.html) | Read |
| Boot Guard blocks custom firmware on newer ThinkPads | [Heads FAQ](https://osresearch.net/FAQ/) | Read (their claim) |
| TPM stores keys and platform measurements; cannot control software running on the PC | [TCG TPM summary](https://trustedcomputinggroup.org/resource/trusted-platform-module-tpm-summary/) | Read |
| PCRs bind secrets to software state through hashes | [Arch wiki: Trusted Platform Module](https://wiki.archlinux.org/title/Trusted_Platform_Module) | Read |
| A PCR can only be extended (hash of old value and measurement) | TPM design, not read from a specification | General knowledge |
| Secure Boot: firmware checks signatures; db, dbx, KEK, PK; PK can sign KEK updates or turn off Secure Boot; 2011 certificates begin expiring June 2026 | [Microsoft Learn: Secure Boot](https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/oem-secure-boot) | Read |
| Intel Boot Guard verifies firmware against the maker's key when the maker enables it | General description; my laptop reports Boot Guard verified boot "Valid" | General knowledge |
| Heads' criticism of Secure Boot (vendor keys, signed insecure kernels) | [Heads FAQ](https://osresearch.net/FAQ/) | Read (their claim, not checked) |
| Heads is coreboot plus Linux in ROM, measures into the TPM, attests to the user, TPM can hold the disk key, user-controlled signing keys | [Heads wiki home](https://osresearch.net/) | Read |
| Heads checks with TOTP (phone), HOTP (USB key, LED red on mismatch) and OpenPGP signing; alerts and does not lock out | [Heads FAQ](https://osresearch.net/FAQ/) | Read |
| "Heads is not designed to block the boot process, but to detect tampering" | [Novacustom Heads setup page](https://novacustom.com/heads-setup/) | Read |
| Quote "you can't trust the computer. What you can trust is this key", and the re-signing "burden" | Talk summaries on the [Heads wiki home](https://osresearch.net/) | Read (secondhand summaries; talks not watched) |
| Heads hardware compatibility page lists ThinkPad boards, OptiPlex, MSI boards, Chrome devices, Talos II, NitroPad NS50, NovaCustom NV4x ADL, V540TU, V560TU | [Heads: hardware compatibility](https://osresearch.net/Hardware-Compatibility/) | Read |
| Untested boards moved to `unmaintained_boards`; ME deactivated on all current Heads boards (HAP bits on Skylake and later) | [Heads prerequisites](https://osresearch.net/Prerequisites) | Read |
| Installing Heads "requires opening the machine and extensive warranty voiding" | [Heads FAQ](https://osresearch.net/FAQ/) | Read |
| Heads dongles need OpenPGP, no FIDO2 or U2F; YubiKey 5 OpenPGP only; Nitrokey Pro 2, Storage 2, 3 and Librem Key full; Nitrokey 3 A-mini most shipped by Novacustom | [Heads prerequisites](https://osresearch.net/Prerequisites) | Read |
| Nitrokey: open source security hardware, produced in Germany, Secure Element optional | [Nitrokey about](https://www.nitrokey.com/about) | Read (company's claim; per-model openness not checked) |
| YubiKey firmware "never been open sourced", not field-updatable, in the YubiKey 4 era | [Yubico, 2016-05-16](https://www.yubico.com/blog/secure-hardware-vs-open-source/) | Read. Applies to YubiKey 5: **est.** |
| Intel ME cannot be removed since Nehalem; four ways to reduce it; definitions of neutering, soft disable and HAP; modules left; not supported on all platforms | [Dasharo: Intel ME/CSME](https://docs.dasharo.com/osf-trivia-list/me/), [Dasharo: Dasharo System Features](https://docs.dasharo.com/dasharo-menu-docs/dasharo-system-features/) | Read |
| Dasharo's ME mode values (Enabled, Disabled (Soft), Disabled (HAP)); MEI hidden from the OS when disabled; Enabled by clearing the HAP bit | [Dasharo: Dasharo System Features](https://docs.dasharo.com/dasharo-menu-docs/dasharo-system-features/) | Read |
| After flashing Dasharo the ME mode field is expected to read Enabled | [Dasharo test MNE001.001](https://docs.dasharo.com/unified-test-documentation/dasharo-security/20F-me-neuter/) | Read. For a given Novacustom model: **est.** |
| Novacustom ships Dasharo coreboot, assembled in the Netherlands | [novacustom.com](https://novacustom.com/) | Read |
| Novacustom's Dasharo page lists "Intel ME disabling (HECI and HAP)" as a feature row | [Novacustom: Dasharo coreboot](https://novacustom.com/dasharo-coreboot/) | Read. Which columns have a check mark: not visible in the text, **est.** |
| Novacustom SecurityTitan V54 and V56: "Disabled Intel ME", coreboot and Heads, anti-tamper, Qubes OS, Intel 14th Gen, 2,695 and 2,749 EUR (sale), 3 years warranty and 7 years firmware updates | [Novacustom: SecurityTitan series](https://novacustom.com/cat/extremely-secure-laptops/) | Read |
| Novacustom Heads variant for NV41, V54, V56 only, subscription; From prices 930, 1,420, 1,460 EUR | [Novacustom: Dasharo coreboot](https://novacustom.com/dasharo-coreboot/) | Read |
| Novacustom's Heads setup includes a Nitrokey 3 PIN and an LED check | [Novacustom Heads setup page](https://novacustom.com/heads-setup/) | Read |
| NV4x ADL image v1.7.2: Intel ME region 0x4b6000 bytes closed-source; Heads v0.9.3 60.0% open and 40.0% closed; v1.8.0 30.8% open and 69.2% closed | [Dasharo openness score: NV4x ADL](https://docs.dasharo.com/variants/novacustom_nv4x_adl/openness-score/) | Read |
| System76 Open Firmware is coreboot, EDK2 and firmware apps; IME disabled when it does not break functionality; typically disabled by default on Open Firmware | [System76 support: Intel ME](https://support.system76.com/articles/intel-me/) (page last updated 2026-08-14) | Read |
| System76 uses a HECI command, not me_cleaner; most Intel machines ship with the IME disabled; the S0ix power cost (about 1 W to 3 W) | [System76 firmware-open: intel-me.md](https://github.com/system76/firmware-open/blob/master/docs/intel-me.md) | Read |
| System76 model table (Yes and No by model code) | [System76 support: open firmware systems](https://system76.com/support/open-firmware-systems) (last updated 2026-08-14) | Read |
| That System76's HECI command is the same class as Dasharo's "soft" disable | My comparison of the two documents | **est.** |
| Purism: neutralized with me_cleaner (about 90-92% of the binary), disabled with the HAP bit, fuses left unset, still working on the ME and FSP, avoids AMT processors; page undated | [Purism: Intel ME](https://puri.sm/learn/intel-me/) | Read |
| Purism Librem 14 and Librem Mini state a disabled ME, PureBoot and Librem Key; processors named; Librem 11 has PureBoot and no ME statement | [Librem 14](https://puri.sm/products/librem-14/), [Librem Mini](https://puri.sm/products/librem-mini/), [Librem 11](https://puri.sm/products/librem-11/) | Read |
| Comet Lake is a 2019 and 2020 generation | General knowledge | **est.** |
| Tuxedo: no ME or coreboot statement in the text I could fetch; sells Intel and AMD; Dasharo release for InfinityBook S 15 Gen6, 2022-03-15 | [Tuxedo notebooks](https://www.tuxedocomputers.com/en/Linux-Hardware/Linux-Notebooks.tuxedo), [Dasharo: Tuxedo IBS15 release notes](https://docs.dasharo.com/variants/tuxedo_ibs15/releases/) | Read. That Tuxedo has no such statement anywhere: **not verified** |
| `SetupMode` 0 means a platform key is enrolled (User Mode) | UEFI convention, not read from the specification | General knowledge |
| My laptop: UEFI boot, TPM 2.0, Secure Boot off, ME interface present and running, Boot Guard enabled, `fwupdmgr` report | The commands in exercise 1, run on 2026-11-07 | Observed |

Not verified, plainly: that any vendor ships what its page says; any Novacustom, System76, Purism or Tuxedo hardware; whether an ME is really stopped on any machine; booting coreboot or Heads; Heads with any key; the openness of any Nitrokey part; Yubico's current firmware policy; anything on macOS or Windows; and the Tuxedo ME status.

## Where this goes next

The firmware lesson that comes before this one (issue #465: device firmware security, the Intel ME, the AMD PSP, MINIX and kernel design) is the place for what the Management Engine does and how it has been attacked. It is not written yet, so there is no link. The hardware keys lesson (issue #463) is also not written yet.

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 2: Defend and detect](Contents.md#track-2-defend-and-detect) > Open firmware and trustworthy hardware

Previous: [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md) / Next: [Digital forensics foundations](Digital-Forensics-Foundations-Evidence-Handling-Chain-of-Custody-and-Order-of-Volatility.md)

In this track: [Track 2: Defend and detect](Contents.md#track-2-defend-and-detect), 38 pages

- Network and host defense: [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md) / [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md) / [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) / [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md) / [Plan for failure: blast radius and assuming breach](Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md) / [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md) / [Attack surface map: layer by layer](Attack-Surface-Map-Layer-by-Layer.md) / [The DMZ and hardening an internet-facing host](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md) / [DMZ hardening checklist](DMZ-Hardening-Checklist.md)
- Deception and honeypots: [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md) / [What deception is](Deception-and-Honeypots-What-Deception-Is.md) / [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) / [Plant a canary token](Deception-and-Honeypots-Plant-a-Canary.md) / [Honeyfiles on a host you own](Deception-and-Honeypots-Honeyfiles-on-Your-Host.md) / [Deception alerts in the SIEM](Deception-and-Honeypots-Alerts-in-the-SIEM.md) / [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md) / [T-Pot at home](Deception-and-Honeypots-T-Pot-at-Home.md) / [Anatomy of a cloud honeypot](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md) / [Cloud Cowrie for a weekend](Deception-and-Honeypots-Cloud-Cowrie-Weekend.md) / [Read what arrived: Cowrie logs](Deception-and-Honeypots-Read-the-Sensor-Logs.md)
- Detection and monitoring: [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md) / [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) / [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) / [Wazuh SIEM and data pipelines](Wazuh-SIEM-and-Data-Pipelines.md) / [Detecting Tor, I2P and VPN on a network](Detecting-and-Managing-Tor-I2P-and-VPN-on-a-Network-the-Defenders-View.md) / [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) / [Multiple sites and identity](Multiple-Sites-and-Identity.md) / [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) / [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) / [Grafana basics from a blank page](Grafana-Basics-From-a-Blank-Page.md) / [Grafana dashboards](Grafana-Dashboards.md) / [Lab: synthetic multi-site monitoring stack](Lab-Demo-Monitoring-Stack.md) / [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) / [Stage 2 home-side runbook](Stage-2-Home-Side-Runbook.md)
- Digital forensics: [DFIR toolkits and live triage](DFIR-Toolkits-and-Live-Triage-SIFT-Velociraptor-KAPE-and-the-Incident-Response-Workflow.md) / [Digital forensics foundations](Digital-Forensics-Foundations-Evidence-Handling-Chain-of-Custody-and-Order-of-Volatility.md) / [Network, log and timeline forensics](Network-Log-and-Timeline-Forensics-Packet-Captures-Logs-and-Plaso.md)
- Device and credential security: **Open firmware and trustworthy hardware**

Related pages:

- [Threat model](Threat-Model.md)
- [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)
- [Hands-on Whonix and Qubes OS](Hands-On-Whonix-and-Qubes-OS-Gateway-Split-Compartments-Disposables-and-Policy-Prompts.md)
<!-- END GENERATED PAGE NAV bottom -->
