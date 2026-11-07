# Device firmware security: Intel ME, AMD PSP, MINIX and kernel design

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Device firmware security: Intel ME, AMD PSP, MINIX and kernel design

Previous: [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) / Next: [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md)
<!-- END GENERATED PAGE NAV top -->

Side page to the foundations track. Read it when you have heard that "there is a second computer inside your computer", that "Intel's management engine runs MINIX", or that "the NSA put a backdoor in your CPU", and you want to know which parts of that are documented, which are a claim, and what you can do about it. It sits beside [Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) (software that pretends to be hardware; this page is about hardware that runs software you did not choose) and [Attack surface map, layer by layer](Attack-Surface-Map-Layer-by-Layer.md), where firmware is one of the layers.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. Read-only checks were run on one Intel laptop; nothing was run on an AMD machine; nothing here modifies firmware.** On **2026-11-07** I ran, on one Linux laptop with an 11th-generation Intel Core processor: `lspci -nn`, `ls -l` on the MEI device, `cat` on two files under `/sys/class/mei/`, `lsmod`, `journalctl -k`, `dmesg` (refused without privilege) and `fwupdmgr security`. **Not run:** anything on an AMD machine (the AMD commands below are marked as not run), `me_cleaner`, any flashing tool, any vendor BIOS option, `intelmetool` or any Intel detection tool. I read sources on **2026-11-07** from the pages named in the [claims register](#claims-register); a claim I could not read there is marked **est.** Trust what your terminal prints over what this page says.

> **Prerequisites.** A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)). Knowing what a kernel and a driver are helps; the page explains the rest. Knowing what a CVE is helps ([Threats in plain words](Threats-in-Plain-Words.md)). About 90 minutes for the reading and the exercise (est.).

> **Where this runs, and the rule.** The exercise is read-only on your own machine. Nothing on this page asks you to flash, patch, reset or reconfigure firmware, and it gives no steps for doing so: a bad flash can leave a computer that will not start, and the one protection discussed here (the HAP bit) needs hardware this page does not cover. If you want to change firmware, that is a different lesson, planned in issue #466 (see the end of this page). No real hostnames, serials or addresses appear.

## What you will be able to do

- Say what the Intel Management Engine (ME) and the AMD Platform Security Processor (PSP) are, and where they sit relative to the CPU cores and the operating system.
- List what they are used for: out-of-band management, boot, copy protection and a firmware TPM.
- Say what MINIX is, and give the dated evidence that ME firmware from version 11 is based on it.
- Explain monolithic and microkernel designs, with Linux, MINIX 3 and seL4 as examples, and name the real tradeoffs.
- Take the "intentional backdoor" claim apart: what is evidenced (vulnerabilities, with CVE ids and dates), what is not, and the argument that does not need the claim.
- Describe what `me_cleaner`, vendor "disable" options and the HAP bit are, and why each is a caveat-heavy answer.
- Read your own machine's report of its management engine.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Layers of a system, firmware as one of them | [Attack surface map, layer by layer](Attack-Surface-Map-Layer-by-Layer.md) | What the always-on processors in the firmware layer are. |
| Patching, including firmware | [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md) | Why ME and PSP fixes arrive as BIOS updates, and why you may never see a notice. |
| Hardware roots of trust in the wallet context | [Wallets and key custody](Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md) | A firmware TPM is one of these processors' jobs. |
| Ranking a risk | [Threat model](Threat-Model.md) | A worked case of a risk with no evidence of intent. |

## Two processors you did not buy separately

A modern PC has more than the processor you chose. Two vendors put a second, smaller processor on the board or in the chip that starts **before** the main CPU cores run your firmware, keeps running **beside** the operating system, and is not under the operating system's control.

**Intel Management Engine (ME).** Positive Technologies, a security research firm, describes it in a Black Hat Europe 2017 whitepaper as "a microcontroller integrated into the Platform Controller Hub (PCH) chip and a set of built-in peripherals". The PCH carries almost all communication between the processor and external devices, so, in their words, "Intel ME has access to almost all data on the computer". The same paper says its main purpose is to initialize the platform and start the main processor, and that from 2015 the ME core has been an x86 core (previously it was an ARCompact core with an unfamiliar instruction set). Intel now calls the product family CSME (Converged Security and Manageability Engine); NVD's wording for a 2018 flaw uses that name. On my laptop (11th-generation Core) the ME firmware reports major version 15 in `/sys`, which is the numbering the whitepaper's "ME 11" belongs to.

**AMD Platform Security Processor (PSP)**, also called the AMD Secure Processor (ASP). Wikipedia's article (a secondary source, read 2026-11-07) says it has been in AMD processors since about 2013, is an ARM Cortex-A5 core with TrustZone placed on the main CPU die, and quotes an AMD developer's guide: it is "responsible for creating, monitoring and maintaining the security environment", including managing the boot process. A 2017 Phoronix article (read from the Internet Archive copy) also says the PSP uses ARM TrustZone. The Cortex-A5 detail is **est.** until I read AMD's or the researchers' own material. The difference in placement is real either way: Intel's sits in the chipset, AMD's is inside the CPU package.

What they share, and why they get discussed together:

1. **They run first.** They are part of how the machine starts. On Intel the ME is also the root of trust for Intel Boot Guard (Positive Technologies, above). On AMD, Wikipedia says the PSP verifies the firmware stored on the board's flash chip and loads parts of it before the main cores run.
2. **They run beside the OS.** Your operating system cannot see their code or read their memory, and cannot stop them. Linux sees a PCI device and a driver (the MEI interface, below), which is a mailbox, not a window.
3. **They are signed and closed.** The firmware is signed by the vendor, the source is not public, and, per `me_cleaner`'s README, the ME firmware "can be neither disabled nor reimplemented, as it is tightly integrated in the boot process and it is signed". Wikipedia reports that AMD has declined requests to open source the PSP code (2017 HotHardware report).
4. **They have wide reach.** The Positive Technologies whitepaper says ME can intercept and modify network packets and graphics output and has full access to USB devices. That is a researcher's description of capability, not a report of misuse.

## What they do

The vendor-neutral list, with the sources:

| Job | What it means | Source |
|---|---|---|
| Boot | Initializes the platform, verifies firmware, starts the main processor | Positive Technologies (ME); Wikipedia on AMD's developer guide (PSP) |
| Out-of-band management | Intel AMT lets an administrator see and control a machine over the network below the OS: power, remote screen and keyboard, reinstall. Business ("vPro") machines only | Positive Technologies whitepaper |
| Firmware TPM | Intel PTT / AMD firmware TPM: a TPM that is software in the secure processor, not a separate chip | Positive Technologies (PTT / fTPM); Wikipedia (PSP provides TPM services) |
| Content protection (DRM) | Intel PAVP (Protected Audio Video Path) and related paths for protected video | Positive Technologies |
| Other secure features | Intel SGX is listed as built around the ME; AMD's SEV (encrypted virtual machines) is implemented by the PSP | Positive Technologies; NVD record of CVE-2019-9836 |
| Random numbers | The PSP provides the random number generator behind the `RDRAND` instruction | Wikipedia, citing an AMD document (not read) |

Purism's 2017 press release adds that the ME "can run and control a computer even when powered off". That is a vendor selling a product that disables it, so read it as a claim; the part that is generally accepted is that the ME runs when the main cores do not (power is still connected).

On Linux you can see the ME's footprint in the modules that talk to it. On my laptop `lsmod` shows `mei`, `mei_me`, `mei_wdt`, `mei_hdcp` and `mei_pxp`. By their names these are the MEI driver, a watchdog, HDCP (a display content-protection scheme) and protected-content support. That reading of the names is **est.**; I did not read the module documentation.

## MINIX, and why it keeps coming up

**What MINIX is.** MINIX is a small Unix-like operating system written by Andrew Tanenbaum, a computer science professor at the Vrije Universiteit Amsterdam, to teach how operating systems work (General knowledge; first released in 1987, **est.** for the year). The project site, read 2026-11-07, describes MINIX 3 as "a free, open-source, operating system designed to be highly reliable, flexible, and secure", "based on a tiny microkernel running in kernel mode with the rest of the operating system running as a number of isolated, protected, processes in user mode". It is the system Linus Torvalds's first kernel was compared to in a famous 1992 argument (below).

**What is evidenced about the ME.**

- **Positive Technologies, Black Hat Europe 2017 whitepaper (read 2026-11-07).** It states that ME 11's software side is a "modified MINIX as an operating system", and that earlier ME versions ran on an ARCompact core. Its own work on this started from unpacking the ME 11 firmware images, whose modules were compressed with Huffman tables the team recovered. The same team's August 2017 blog post is the one other sources point to for the first public statement; I could not load that site (DNS failure from my machine), so I did not read it.
- **Tanenbaum's "An Open Letter to Intel" (page read 2026-11-07; the server's last-modified date is 2017-11-10).** He writes that he learned of it from press reports, that Intel's engineers had earlier asked him technical questions and asked for changes (a smaller memory footprint, `#ifdef`s to disable parts of the code), and that the permissive license (BSD-style, adopted for MINIX in 2000 by his account) let Intel keep its changes private. He also writes that he "certainly" hoped Intel hardened it, because "apparently an older version of MINIX was used". His claim that MINIX is thereby "probably the most widely used operating system in the world on x86 computers" is his estimate, and I did not verify it.
- **Intel's own statement.** I looked for Intel confirming MINIX use and did not find one in the sources I could read, so I do not state it. **est.:** I believe Intel has not objected, but that is my recollection, not a source.

The practical consequence is small and specific: code that runs inside the ME is a real operating system with a kernel, a file system and a collection of services, not a fixed chip. That is why it can have bugs of the ordinary kind. For versions after 11 (my laptop reports 15) I did not find a primary source about the operating system, so "ME 12 and later also use MINIX-derived code" is **est.**

## Microkernel against monolithic kernel

A kernel is the part of an operating system that runs with full power over the hardware. The design question is how much goes in it.

**Monolithic.** Everything that needs hardware access (scheduler, memory manager, file systems, network stack, device drivers) runs in one program in the kernel's privileged mode and address space. **Linux** is monolithic, but it loads and unloads parts at run time as modules. The `mei` modules above are loaded into the running kernel and, from then on, are the kernel as far as privilege goes. A bug in one of them can take over the machine, because there is no wall between it and the rest.

**Microkernel.** The kernel keeps only the minimum: address spaces, scheduling of threads and a way for processes to send each other messages. File systems, drivers and the network stack are ordinary programs in user mode. **MINIX 3** is built this way (per its project page above). A crashed driver is a crashed program that can be restarted, and a driver bug does not hand over the machine.

**A third example, seL4.** seL4 is a microkernel whose project FAQ (read 2026-11-07) says that several configurations (Arm, x86-64 and RISC-V among them) have "a full code-level functional correctness proof - a mathematical proof that the C implementation adheres to its specification", and describes itself as "the first (and still only) general-purpose OS kernel" with that. Read the next lines of the same FAQ: it says this is not "zero bugs" and not "secure" without conditions; the proof holds only if its assumptions are met, and the confidentiality proof "makes no guarantees about the absence of covert timing channels". That is what a good claim about a kernel looks like: a stated scope.

**Windows NT and macOS's XNU** are usually called hybrids: a microkernel heritage with much of the OS moved back into the kernel for speed (General knowledge, **est.**; not looked up for this lesson).

The tradeoffs, honestly (General knowledge, the standard account, **est.** on the specifics):

| Property | Monolithic | Microkernel |
|---|---|---|
| Speed | A service call is a function call; no copies or context switches | Services talk by messages, which costs context switches; good designs make this small, and it is the classic objection |
| Trusted code | Millions of lines run with full privilege | A small kernel runs with full privilege; the rest is confined (seL4's proof is only feasible because it is small) |
| A buggy driver | Can corrupt anything | Can be contained and restarted, if the design confines it |
| Complexity | One program, easy to share data | Many programs, careful message design, harder to debug across the boundaries |
| Hardware support | Linux has the widest driver set | Fewer drivers, so more porting work |

The 1992 Torvalds and Tanenbaum argument on `comp.os.minix`, in which Tanenbaum called Linux's monolithic design obsolete and Torvalds defended it, is the origin of this debate in the open-source world. I did not re-read the thread for this lesson (**est.** on the date and the participants' exact words).

**Two cautions that matter for the ME.**

1. A microkernel does not make a system safe. Intel's own advisory INTEL-SA-00086 (below) lists buffer overflows **in the ME's kernel** (NVD: "Multiple buffer overflows in kernel in Intel Manageability Engine Firmware 11.0/11.5/11.6/11.7/11.10/11.20"). A design that confines a bug limits the damage only if the services are confined well and the privileged parts are correct.
2. The design is not what makes the ME the topic. The privilege is. Whatever kernel runs it, it has access to memory, network and storage that you cannot inspect.

## The "intentional backdoor" claim, as a claim

You will hear: "the ME and the PSP are backdoors put there on purpose, for the NSA." Treat that as a claim and sort what is behind it.

**What is evidenced.**

- **Both exist, run with high privilege and cannot be switched off by ordinary means.** See the sources above.
- **Both have had real vulnerabilities.** A short, dated list (CVE records read from NVD, 2026-11-07; the vendor advisory pages I could not read are marked):

| CVE | Published | What NVD says it is | Product |
|---|---|---|---|
| [CVE-2017-5689](https://nvd.nist.gov/vuln/detail/CVE-2017-5689) | 2017-05-02 | An unprivileged network attacker could gain system privileges on provisioned AMT/ISM machines (CVSS v3.1 base score 9.8, NVD) | Intel AMT |
| [CVE-2017-5705](https://nvd.nist.gov/vuln/detail/CVE-2017-5705) (with -5706 and -5707) | 2017-11-21 | Multiple buffer overflows in the ME 11 kernel allow local arbitrary code execution (CVSS v3.0 7.8, NVD). Intel's advisory INTEL-SA-00086 was published 2017-11-20 (Positive Technologies timeline) | Intel ME 11 |
| [CVE-2018-3628](https://nvd.nist.gov/vuln/detail/CVE-2018-3628) | 2018-07-10 | Buffer overflow in the AMT HTTP handler, exploitable from the same subnet | Intel AMT / CSME |
| [CVE-2020-0594](https://nvd.nist.gov/vuln/detail/CVE-2020-0594) | 2020-06-15 | Out-of-bounds read in the AMT IPv6 code, possible privilege escalation by an unauthenticated user over the network (CVSS v3.1 9.8, NVD) | Intel AMT / ISM |
| [CVE-2019-9836](https://nvd.nist.gov/vuln/detail/CVE-2019-9836) | 2019-06-25 | Insecure cryptographic implementation in SEV in the PSP | AMD PSP |
| [CVE-2021-26335](https://nvd.nist.gov/vuln/detail/CVE-2021-26335) | 2021-11-16 | Missing checks in the ASP boot loader image header before signature validation, possibly arbitrary code execution (AMD bulletin AMD-SB-1027, named in the NVD record) | AMD ASP |
| [CVE-2021-46759](https://nvd.nist.gov/vuln/detail/CVE-2021-46759) | 2023-05-09 | Improper syscall input validation in AMD's TEE, needs physical access (AMD-SB-4001, named in the NVD record) | AMD ASP |

  Older research, from the Positive Technologies whitepaper: a 2009 Black Hat talk on "Ring-3 rootkits" (code injected into memory the ME spills to the host's RAM), a 2010 attack on AMT's zero-touch provisioning, and the 2017 AMT authorization bypass above. Intel's advisory pages answered my script with HTTP 403, so I did not read them; the Intel advisory number for CVE-2017-5689 (INTEL-SA-00075) is from memory, **est.** The AMD bulletin pages were not read either, only the NVD records that name them.
- **Researchers have examined both.** Positive Technologies unpacked ME 11's images; Wikipedia reports a 2019 talk, "Dissecting the AMD Platform Security Processor" (Werling and Buhren, 24 August 2019), that found the PSP's off-chip firmware in ordinary UEFI images. So the code is not wholly unseen; it is just not public, not reproducible by you and not replaceable.

**What is not evidenced.** I found nothing in what I read showing that either vendor built a deliberate secret access path for a government. A vulnerability is a bug that someone found. A memory-safety bug in a large, privileged, legacy-heavy network service (the CVE list above is mostly AMT's network code) looks exactly like what bugs look like when nobody planted them, and nothing in the record distinguishes them from planted ones. The word "backdoor" also gets used loosely: the NVD records for CVE-2018-8934 and CVE-2018-8935 literally say "has a backdoor", but that is the label the 2018 researchers gave to chipset flaws in a different part (the Promontory chipset, not the PSP), and AMD published an assessment of that research that I did not read. A label in a CVE title is not a finding of intent.

Intel's response, quoted by The Register (updated 2017-08-29): "Intel does not and will not design backdoors for access into its products." I did not find an equivalent AMD statement in anything I could read.

**The argument that does not need the claim.** You do not have to prove malice. A processor that runs before and beside your OS, that can reach memory, storage and (on AMT machines) the network below the firewall, whose code you cannot read, cannot replace and cannot fully switch off, is a risk **because of what it is able to do**, whoever wrote it and whatever they meant. The same sentence is true of any single point of trust you cannot inspect. Honest vendors still ship bugs; the table above is the proof. If the processor can be compromised, the compromise sits underneath your encryption, your firewall and your antivirus, where none of them can see it. And a machine that someone else can reach is an unacceptable default for some people (a journalist, a lab, a person handling a wallet) while being an acceptable one for a company that uses AMT on purpose.

So the position here is narrow. Do not say the vendors planted backdoors; there is no evidence for it in what I read. Do say that people who cannot accept this risk should be able to turn it off, and that today that option is partial, unsupported or absent, which is a problem whatever the vendors intended.

## Turning it off, or down: what exists

Everything here is described at concept level. There are no steps, because the steps need a hardware flasher and a wrong move can leave the machine unable to start.

**Do not mistake "off" for what it is.** On current Intel hardware the ME cannot be removed, because it is part of starting the machine. The `me_cleaner` README (read 2026-11-07) says that from Nehalem (ME version 6, 2008/2009) the firmware cannot be removed: "without a valid firmware the PC shuts off forcefully after 30 minutes". Its goal is therefore smaller: modify the firmware image so the ME runs only during boot and is largely idle in normal operation.

**`me_cleaner`.** An open-source Python script that rewrites an ME firmware image to strip most modules. Its README says what it achieves per generation (generation 3, ME 11 onward, keeps four modules needed to boot and leaves about 300 kB), that on some boards "the OEM firmware fails to boot without a valid Intel ME firmware", that other boards boot with "minor inconveniences" such as longer boot times or warnings, and that "the features provided by Intel ME won't be functional anymore". It also says obtaining the original image and flashing the modified one "is usually not trivial" and often needs an external SPI flasher. Caveats from me: I read the README only. I did not check how actively the project is maintained or which of your machines it supports (the README points at a status page I did not read), I did not run it, and I have no verified count of how many people use it. If a site tells you a number, ask for its source.

**OEM and vendor options.** Some vendors have shipped machines with the ME reduced or disabled. Purism's press release of 2017-10-19 says its Librem laptops with coreboot ship with the ME "disabled by default", and says the check is a boot message. That is a vendor statement about its own product; I did not test it, and the release itself admits that "removing the management engine entirely is the next step beyond just disabling it". Other makers (Dell and System76 are the ones I remember from 2017) have offered similar options; I did not read their pages, so that is **est.** and I make no claim about which models.

**AMD.** Phoronix reported on 2017-12-07 that a newer AGESA (AMD's firmware component) update for Ryzen systems "reportedly" lets the PSP be disabled from the UEFI setup, with users seeing "BIOS PSP Support - Disabled" on their boards. The author said he could not confirm it on his own boards. That is a report of a report. Whether the setting stops the PSP or only part of its feature set is not established by what I read; assume the second. **Check your own board's manual.**

**Breakage.** Expect real loss: features that depend on these processors (AMT remote management, the firmware TPM, protected video, sometimes sleep states and fan control, **est.** for the last two) may stop working or disappear. A modified or disabled ME on a machine with Intel Boot Guard enforced may not start at all (**est.**; mechanism not checked here). That is a reason to test on a spare machine, not a reason to do nothing.

**The HAP bit (concept only).** In August 2017 Positive Technologies reported an undocumented setting in the ME firmware's configuration that makes the ME stop early in boot (The Register, 2017-08-29, "On Monday", so 2017-08-28). It is called the HAP bit: HAP is the "High Assurance Platform" program, which The Register describes as a security framework developed by the US National Security Agency, and the bit has been nicknamed the NSA switch. Intel's statement, as published by The Register: "the modifications were made at the request of equipment manufacturers in support of their customer's evaluation of the US government's 'High Assurance Platform' program. These modifications underwent a limited validation cycle and are not an officially supported configuration." So it is reported to exist, to have been built for a government evaluation, and not to be supported for ordinary buyers. Setting it means changing the contents of the flash chip, which needs specialized hardware and care that this lesson does not cover, and no instructions follow. Positive Technologies noted that HAP's effect on Boot Guard was unknown at the time.

Note what this does and does not show. It shows that a switch to turn the ME off exists in the firmware, that Intel built it for a particular customer class and that it is unsupported for everyone else. It does not show that the switch is a backdoor; an off switch is the opposite of one. It is the best available evidence for the argument above: the ability exists, and it is not offered.

## Free path: what does your machine report?

All of this is read-only. None of it changes firmware. Run it on a Linux machine you own. The results below are what I got on 2026-11-07 on one Intel laptop; yours will differ.

### Exercise 1: find the management engine on the PCI bus

```bash
lspci -nn | grep -i -E 'management|communication controller'
```

I got two lines: a "Communication controller" named "Tiger Lake-LP Management Engine Interface" (ID `8086:a0e0`) and a "Serial controller" named "Tiger Lake-LP Active Management Technology - SOL". The first is the mailbox the OS uses to talk to the ME. The second shows that the chipset has the serial-over-LAN piece of AMT. **It does not show that AMT is enabled or provisioned on my machine.** I did not check that. If you see nothing, your machine may not expose it, or you are in a virtual machine.

### Exercise 2: see the MEI device, without opening it

```bash
ls -l /dev/mei0
cat /sys/class/mei/mei0/kind
cat /sys/class/mei/mei0/fw_ver
```

On mine, `/dev/mei0` is a character device owned by root with mode `0600` (so I did not open it), `kind` printed `mei`, and `fw_ver` printed three lines that begin `0:15.0.` followed by a build number. The `15` is the ME's major version. Do not paste your full build string into a public question without thinking about it; it identifies your firmware generation.

### Exercise 3: what the kernel loaded

```bash
lsmod | grep '^mei'
```

I got `mei`, `mei_me`, `mei_wdt`, `mei_hdcp` and `mei_pxp`. Compare them with the table in [What they do](#what-they-do).

### Exercise 4: the kernel log

```bash
dmesg | grep -i -E 'mei|psp|ccp'
journalctl -k -b --no-pager | grep -i -E 'mei|psp|ccp'
```

`dmesg` answered "read kernel buffer failed: Operation not permitted" for my user, and the `journalctl` line printed nothing for me. I did not escalate to read it as root, so I have no kernel-log evidence from this machine. On a machine where you can read the log, lines naming `mei` or, on AMD, `ccp` (the Linux driver that talks to the PSP) are what to look for. **est.**: the `ccp` name is from memory, not tested.

### Exercise 5: the firmware security report

```bash
fwupdmgr security
```

`fwupdmgr` (from the fwupd project) rates a machine's firmware settings. On mine it printed a Host Security ID of `HSI:1!` and a list of checks, among them "MEI key manifest: Valid", "csme manufacturing mode: Locked", "csme override: Locked", "csme v0:15.0.56.2834: Valid" (a build string; yours will differ), "Intel BootGuard: Enabled", "BIOS rollback protection: Disabled" (marked as a failed check) and "UEFI secure boot: Disabled". Read the lines that mention `csme`, `MEI` and `BootGuard`. What each means is in the fwupd project's documentation, which I did not read for this lesson, so I will not paraphrase it. The point of the exercise is the one fact it demonstrates: the operating system can report that the ME exists, which version it is, and whether the manufacturer's locks are set, and it cannot do anything about the code.

### Exercise 6 (AMD machines): not run

On an AMD machine the corresponding checks would be `lspci | grep -i -E 'encryption|platform security'` and a `ccp` search of the kernel log. I did not have an AMD machine and did not run them; the expected output is **est.** Share what you see in the project's discussion instead of trusting this line.

### Exercise 7: write your own risk statement

Using only what Exercises 1 to 5 printed, write two lines: what processor is present, and what you can and cannot know about it. Do not write the word "safe" or the word "backdoor" in it.

## Flip the board

**The reviewer.** A forum post says: "I flashed `me_cleaner` on my ThinkPad and now the NSA cannot spy on me." Find at least five problems.

<details>
<summary>What to find</summary>

1. "Cannot" is a claim about a closed system the poster cannot fully inspect. A stripped ME that runs during boot is still running.
2. `me_cleaner`'s own README says the ME cannot be fully removed on modern hardware and that it is reduced, not eliminated.
3. Nothing in the evidence on this page shows a government is "spying" through it; the evidenced risk is bugs in a privileged component.
4. There is no statement of the exact model, ME version or platform support, and `me_cleaner` support depends on all three.
5. No statement of what stopped working (AMT, firmware TPM, protected video, sleep, boot time).
6. No recovery plan or backup of the original firmware image, and no mention of the external flasher a flash usually needs.
7. The poster treats the ME as the only firmware risk; the UEFI firmware, the embedded controller and device firmware are not addressed.

</details>

**The auditor.** A manager says: "Our fleet uses vPro, so it is more manageable. Do we need to patch the ME?" What do you ask? (Whether AMT is provisioned and reachable from any network; the ME firmware version on each model; the BIOS update that carries the fix; and who sees the advisories. The 2017 and 2020 AMT entries in the table above were network-reachable.)

## Checkpoint

Without looking back: say where the ME and PSP sit and what runs first; name three things they do besides boot; state the dated evidence that ME 11 is MINIX-based and what you did not find; explain monolithic against microkernel and give one real tradeoff each way; say why a microkernel did not stop the 2017 ME advisory; split the backdoor claim into what is evidenced and what is not; state the argument that needs no proof of malice; and say what the HAP bit is reported to be, who it was built for and why this lesson does not tell you to set it.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "The ME is a backdoor the NSA put there" | A claim. The evidence on this page is vulnerabilities and capability, not intent | The table of CVEs; the vendor's published denial |
| "No proof of backdoor, so no problem" | The risk does not need malice; it needs a privileged, uninspectable component | The argument in the backdoor section |
| "me_cleaner turns the ME off" | It reduces the firmware; the ME still starts the machine | The README's "What can be done" |
| "My machine has no ME because I run AMD" | AMD has the PSP, a comparable component | The PSP section |
| "A microkernel is secure" | The ME's kernel had buffer overflows in 2017 | CVE-2017-5705 |
| "Linux is a microkernel because it has modules" | Modules run inside the kernel with full privilege | `lsmod`; the monolithic section |
| "I can read my ME firmware version, so I can audit it" | You can read a version string; you cannot read the code | Exercise 2 |
| "The HAP bit is an official option" | Intel calls it an unsupported configuration | Intel's statement as quoted |

## Claims register

Retrieved 2026-11-07 with read-only requests unless stated. "Read" means I read the page or record text. "Observed" means I ran it on my laptop.

| Claim | Source | Status |
|---|---|---|
| ME is a microcontroller in the PCH with access to almost all data; x86 core since 2015; modified MINIX as its OS; ME is the root of trust for Boot Guard; lists AMT, PTT/fTPM, SGX, PAVP; earlier versions ARCompact | Positive Technologies, "How to hack a turned off computer, or running unsigned code in Intel Management Engine" whitepaper, Black Hat Europe 2017 (blackhat.com, docs/eu-17) | Read |
| INTEL-SA-00086 (CVE-2017-5705, -5706, -5707) published 2017-11-20; Intel acknowledged the report 2017-07-17; the 2009, 2010 and 2017 earlier ME/AMT issues | Same whitepaper | Read |
| Tanenbaum's open letter: learned from press, Intel's earlier questions and change requests, BSD-style license since 2000, "older version of MINIX", not a spy engine | [cs.vu.nl/~ast/intel](https://www.cs.vu.nl/~ast/intel/) (last-modified header 2017-11-10; page has no date) | Read |
| Intel confirmed MINIX use | None found | Not verified |
| The first public MINIX-in-ME report was Positive Technologies' August 2017 blog post | Pointed to by Tanenbaum's page; that blog did not load | Not read |
| MINIX 3: tiny microkernel in kernel mode, the rest as isolated user-mode processes, free and open source | [minix3.org](https://www.minix3.org/) | Read |
| MINIX written to teach; first released 1987; 1992 Torvalds and Tanenbaum debate | General knowledge | **est.** |
| seL4: code-level functional correctness proof for named configurations; not "zero bugs"; no covert timing channel guarantee | [seL4 FAQ](https://sel4.systems/About/FAQ.html) | Read |
| Windows NT and XNU are hybrid kernels | General knowledge | **est.** |
| Monolithic against microkernel tradeoff table | General knowledge | **est.** |
| CVE records, dates and scores in the table | [NVD](https://nvd.nist.gov/) records via its public API | Read |
| Intel advisory pages, AMD bulletin pages | Intel's returned HTTP 403; AMD's not requested | Not read |
| INTEL-SA-00075 is the advisory for CVE-2017-5689 | Memory | **est.** |
| AMD PSP: since about 2013, ARM Cortex-A5 with TrustZone, in the CPU die; verifies board firmware; provides TPM services and RDRAND; AMD refuses to open source | [Wikipedia: AMD Platform Security Processor](https://en.wikipedia.org/wiki/AMD_Platform_Security_Processor) (secondary; citing AMD's developer guide, HotHardware 2017, Werling and Buhren 2019, none read) | Read (secondary). Details **est.** |
| PSP uses ARM TrustZone; AGESA reportedly adds a PSP disable option (2017-12-07), unconfirmed by the author | [Phoronix, AMD Reportedly Allows Disabling PSP](https://www.phoronix.com/scan.php?page=news_item&px=AMD-PSP-Disable-Option) (Internet Archive copy; the live page returned 403) | Read |
| me_cleaner: what it does, what it cannot do, breakage, SPI flasher note | [me_cleaner README](https://github.com/corna/me_cleaner) (raw README text) | Read. Project activity and platform support not checked |
| Number of people who disable the ME or the PSP | None found | Not verified |
| Purism Librem ships with the ME disabled by default (2017-10-19); "removing entirely is the next step" | [Purism press release](https://puri.sm/posts/purism-librem-laptops-completely-disable-intel-management-engine/) | Read (vendor claim, not tested) |
| Dell and System76 offered ME-disable options in 2017 | Memory | **est.** |
| HAP bit: reported by Positive Technologies; HAP is an NSA-developed framework per The Register; Intel's statement; Intel's "does not and will not design backdoors" statement | [The Register, 2017-08-29](https://www.theregister.com/2017/08/29/intel_management_engine_can_be_disabled/) | Read |
| An AMD statement denying a backdoor | Not found | Not verified |
| CVE-2018-8934 and -8935 are labeled "backdoor" for the Promontory chipset | NVD records | Read |
| Exercises 1 to 5 results | My laptop, 2026-11-07 | Observed (`dmesg` refused; `journalctl` empty) |
| Exercise 6 output on AMD | n/a | Not run; **est.** |

## What comes next

A planned lesson, issue #466, covers open firmware: coreboot and similar projects, what they can and cannot replace, and the hardware and risks involved in changing firmware. It does not exist yet, so there is no link.

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Device firmware security: Intel ME, AMD PSP, MINIX and kernel design

Previous: [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) / Next: [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md)

In this track: [Track 1: Foundations](Contents.md#track-1-foundations), 37 pages

- OS and Linux, git and the terminal: [Git from zero](Git-From-Zero.md) / [The terminal and your first script](Terminal-and-Your-First-Script.md) / [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) / [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) / [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md) / [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md) / [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) / **Device firmware security: Intel ME, AMD PSP, MINIX and kernel design** / [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) / [Kubernetes for beginners](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md) / [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) / [Cron, systemd timers and init scripts versus systemd](Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd.md)
- Networking: [How a web request works](How-a-Web-Request-Works.md) / [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) / [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) / [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) / [IPv6 adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md)
- Identity and secrets: [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) / [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) / [Secrets from day one](Secrets-From-Day-One.md) / [Password managers and passkeys](Password-Managers-and-Passkeys-What-Each-Protects-and-Where-They-Fail.md) / [Disk and file encryption: VeraCrypt, TrueCrypt, BitLocker, FileVault, LUKS](Disk-and-File-Encryption-VeraCrypt-TrueCrypt-History-BitLocker-FileVault-and-LUKS.md) / [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) / [Hardware security keys: YubiKey, Nitrokey, PIV](Hardware-Security-Keys-YubiKey-Nitrokey-Smart-Cards-and-PIV.md)
- Infrastructure as code: [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md) / [OpenTofu from zero](OpenTofu-From-Zero.md) / [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) / [Ansible: configuration management versus provisioning](Ansible-Configuration-Management-Versus-Provisioning.md) / [Native IaC versus open standards](Native-IaC-vs-Open-Standards-CloudFormation-ARM-Bicep-and-OpenTofu.md) / [Spacelift from zero](Spacelift-From-Zero.md) / [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md) / [Environments and promotion](Environments-and-Promotion-Dev-Staging-Production.md)
- Web hosting: [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md) / [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) / [Static against dynamic: Hugo, WordPress and recon](Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon.md) / [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md) / [Autoscaling and elasticity](Autoscaling-and-Elasticity-Scale-Out-Targets-Cooldowns-and-Cost-Caps.md)

Related pages:

- [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md)
- [Kubernetes for beginners](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md)
- [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md)
- [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md)
<!-- END GENERATED PAGE NAV bottom -->
