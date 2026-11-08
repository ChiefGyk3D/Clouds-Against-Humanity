# Memory forensics: acquiring RAM and analyzing it with Volatility 3

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. The Linux half was run once on one machine; the Windows half was read, not run.** On **2026-11-07** I ran this on a Linux host with QEMU 10.0.13 (a Debian build) and `/dev/kvm`: a Debian 13 cloud image as the guest, one memory dump taken from the hypervisor, a symbol table built from Debian's debug-symbol package with dwarf2json 0.9.0, and Volatility 3 2.28.2 (Python 3.13.5) reading the dump. The plugins whose output appears below are the ones I ran: `banners.Banners`, `linux.pslist.PsList`, `linux.psscan.PsScan`, `linux.psaux.PsAux`, `linux.sockstat.Sockstat`, `linux.lsof.Lsof`, `linux.malfind.Malfind` and `linux.malware.malfind.Malfind`. **Run as scripts, not as written:** I ran the commands in Exercises 2 to 4 from small script files and a helper that talks to the QEMU socket, with the same options. The one-line forms printed on this page (the `printf` that builds the cloud-init file, the single `ssh` line in Exercise 3, the inline Python in Exercise 4) are my rewrites for reading and were not run as printed, so expect to fix a typo. **Not run:** LiME, WinPmem, FTK Imager, anything on Windows or macOS, every `windows.*` plugin against a real dump, VirtualBox and VMware dump methods, and the Windows PowerShell lines. The Windows plugin names are checked against the plugin list the installed tool prints, not against a Windows image. Claims about other projects were read from their own pages on **2026-11-07**, listed in the [claims register](#claims-register); a claim I could not read there is marked **est.** Trust what your terminal prints over what this page says.

> **Prerequisites.** A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)) and a throwaway Linux virtual machine you can start and stop ([Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md)). Knowing what a hash is helps ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)). The free path needs a Linux host with KVM, about 6 GB of free disk and 3 GB of free memory (est.; I used a 2 GB guest, a 2.1 GB dump and a 1.8 GB unpacked debug package). About two hours the first time, most of it downloads and waiting (est.).

> **Where this runs, and the rule.** Everything here happens on your own computer, in a VM you built an hour ago. The guest uses QEMU's default outbound-only network, and the one forwarded port is bound to `127.0.0.1`. Analyze memory from systems you own or are authorized in writing to examine. A memory image holds whatever was in RAM: passwords, keys, other people's messages. Treat the file as sensitive, and delete it when you are done. This page runs no malware; the exercise finds a harmless process you started yourself.

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Security tools and threat modeling](Contents.md#security-tools-and-threat-modeling) > Memory forensics with Volatility 3
<!-- END GENERATED PAGE NAV top -->

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says (and the gap)](#what-the-wiki-already-says-and-the-gap)
- [Why memory matters](#why-memory-matters)
- [Getting a memory image from a lab VM](#getting-a-memory-image-from-a-lab-vm)
- [Why acquiring changes memory](#why-acquiring-changes-memory)
- [Symbol tables: why Volatility 3 needs them](#symbol-tables-why-volatility-3-needs-them)
- [Plugins: what to run for what](#plugins-what-to-run-for-what)
- [Honest limits](#honest-limits)
- [Volatility 3: version and license](#volatility-3-version-and-license)
- [Free path: dump a lab VM and find what you started](#free-path-dump-a-lab-vm-and-find-what-you-started)
- [Build, break, detect, evade, defend](#build-break-detect-evade-defend)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

## What you will be able to do

- Say what lives in RAM that is not on disk, and what disappears when the power goes off.
- Name three ways to get a memory image from a lab VM and say what each one costs.
- Explain why acquiring memory changes it, and why a hypervisor dump changes it less than a tool running inside the machine.
- Say what a symbol table is and why Volatility 3 refuses to work without a matching one.
- Pick the right plugin for "what was running", "what was listening" and "is there injected code", and read its output.
- Run the free exercise: dump a lab VM, build the symbol table, and find a process you started and a file it had open.
- State the limits: encrypted memory, anti-forensics and version drift.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| A virtual machine, snapshots, host and guest | [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) | A VM as the thing you capture, not only the thing you run. |
| Running a command, reading output, redirecting to a file | [The terminal and your first script](Terminal-and-Your-First-Script.md) | The same skills pointed at a 2 GB binary file. |
| Hashing a file to prove it did not change | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) | Hashing the evidence right after you take it. |
| Firmware and management engines run below the operating system | The [Intel ME lesson](Device-Firmware-Security-Intel-ME-AMD-PSP-MINIX-and-Kernel-Design.md) and the [open firmware lesson](Open-Firmware-and-Trustworthy-Hardware-coreboot-Heads-Nitrokey-and-Vendors-That-Ship-the-Intel-ME-Disabled.md) | RAM images show what the operating system saw; they do not show what runs underneath it (see [limits](#honest-limits)). |
| Disk and file forensics, the order in which to collect evidence, incident response, logs | Sibling lessons: [foundations](Digital-Forensics-Foundations-Evidence-Handling-Chain-of-Custody-and-Order-of-Volatility.md), [disk](Disk-Forensics-with-Autopsy-and-The-Sleuth-Kit.md), [network and log](Network-Log-and-Timeline-Forensics-Packet-Captures-Logs-and-Plaso.md) and [toolkits](DFIR-Toolkits-and-Live-Triage-SIFT-Velociraptor-KAPE-and-the-Incident-Response-Workflow.md) | This page is the memory half only. |

## Why memory matters

A disk keeps files. RAM keeps what the machine is doing. Things that are in memory and often nowhere else:

- **Processes, and what they were asked to do.** The process list, each command line, the parent of each process, when each started. A program that deletes itself from disk after it starts is still running from memory.
- **Network connections.** Which program has a socket open, to where, and in what state, including listeners.
- **Injected code.** Code written into another process's memory never touches a file. The only place to see it is memory.
- **Open files and mapped libraries.** What each process had open, which is how you tie a program to a file.
- **Credentials and keys.** Passwords typed into a program, session tokens and decryption keys are in RAM while they are in use. Disk encryption keys are in RAM while the disk is unlocked. That is why a memory image is as sensitive as the secrets it came from, and why [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) matters here.
- **Recent activity.** Shell history that has not been written yet, the clipboard, recently read file contents. In my run, a 43-byte note I wrote with `echo` showed up in the image at seven places (Exercise 6).

### What is lost at power off

RAM does not keep its contents without power. Shut the machine down, pull the plug, or let a laptop battery die, and the process list, the sockets and the keys go with it. Disk survives. RFC 3227, the IETF's guide to collecting evidence, tells you to collect the most volatile items first. Its list in section 2.1, read on 2026-11-07, runs: registers and cache; routing table, ARP cache, process table, kernel statistics and memory; temporary file systems; disk; remote logging data; physical configuration and network topology; archival media. So memory comes before disk. The full treatment of that order, and what to do about it in a real incident, is in the sibling lesson [foundations of forensics](Digital-Forensics-Foundations-Evidence-Handling-Chain-of-Custody-and-Order-of-Volatility.md).

A practical consequence: if a machine is suspected of being compromised, the first question is whether to capture memory before anyone powers it down. That is a decision for the incident owner, not a reflex.

## Getting a memory image from a lab VM

You have three options in a lab, from least to most intrusive to the guest.

**1. Ask the hypervisor.** The guest never runs a capture program, so it cannot notice and cannot be told to lie about its own memory (a compromised kernel can lie to a tool running inside it). In QEMU the monitor command `dump-guest-memory` writes the guest's physical memory to a file. That is the method I ran, and Volatility 3 2.28.2 read the result (an ELF core file) without conversion. Other hypervisors keep memory in a file when the VM is suspended or snapshotted: VMware keeps it in a `.vmem` file next to a `.vmss` or `.vmsn` file (**est.**, from the Volatility 2 documentation I saw quoted, not from VMware's pages), and VirtualBox has a `VBoxManage debugvm` dump command (**est.**; I did not read VirtualBox's page for it). Check your hypervisor's own documentation before you rely on either.

**2. Run a capture tool inside the machine.** This is the only option on real hardware, and on a VM when you cannot reach the hypervisor. Two things to know on Linux:

- **LiME** (Linux Memory Extractor) is a loadable kernel module that writes RAM to a file or over TCP. It must be built for the exact kernel it will run in. Its README, read on 2026-11-07, shows `insmod ./lime-$(uname -r).ko "path=/tmp/ram.lime format=lime"` and names three formats: `lime`, `padded` and `raw` (it calls `raw` "not recommended except for advanced users"). The license is GPL-2.0, and the project's latest release when I looked was v1.12.0 (2026-03-31). I did not build or run it. In a lab, write the output to a second disk or send it over the network (`path=tcp:4444`) so the capture does not fill the system disk or overwrite files you may want. Loading a kernel module also needs root, and on a system with Secure Boot or module signing it may be refused.
- Volatility 3 reads the LiME format. Its basics page says a raw LiME-format image and a page file "can be combined" into one memory layer (read 2026-11-07).

**3. On Windows, a tool that loads a driver.** Volatility 3's own Windows tutorial names two acquisition tools, WinPmem and FTK Imager (read 2026-11-07), and gives no usage for either.

- **WinPmem** is Apache-2.0 licensed. Its README, read on 2026-11-07, shows `winpmem_mini_x64.exe physmem.raw` for a raw image and says the signed binaries have write support off. The newest release I could see through the project's release list is `v4.1.dev1`, marked a pre-release, dated 2024-11-23; the README is older and describes Windows 7 through 10, so **check which build supports your Windows version before you plan around it (est.)**. The mini executables write raw only.
- **FTK Imager** is Exterro's imaging tool. Its product page, read on 2026-11-07, says you can "perform memory capture or registry capture on a live device" and calls the download free. The page did not show a version number, and the download asks for contact details. In the program the memory capture is under the File menu, with an option to include the pagefile (a secondary source, not the vendor, said so). A raw capture works with Volatility according to the same secondary source (**est.**; I did not run it).

On macOS the options are different again and out of scope here.

### Hash what you took

As soon as the file exists, record a hash of it (`sha256sum`) and keep the hash somewhere apart from the file. It lets you show later that the image you analyzed is the one you took. The page [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) explains why one changed byte changes the hash.

## Why acquiring changes memory

You cannot photograph a running machine without the machine moving. RFC 3227 puts it as a principle, section 2: "Minimize changes to the data as you are collecting it" (read 2026-11-07). Three separate causes:

1. **The tool needs memory.** A capture program loads, allocates and runs. On a real machine, that overwrites some free pages and pushes some cached data out. Loading LiME means a new kernel module appears in the module list, and it shows up in the image you took.
2. **The machine keeps running.** A capture of 2 GB takes seconds to minutes, and the system does not stop for it. One page can be captured before a process changes it and another after. The result is not a single instant; it is a smear. Your process list and your network table may describe slightly different moments.
3. **Writing the file touches memory.** The file goes through the page cache and buffers.

I measured the second cause. I took two dumps of the same idle guest about three minutes apart, with nothing run inside the guest in between, and compared them in 4096-byte pages: **1,583 of 528,417 pages (0.30 percent) differed**. `linux.pslist.PsList` listed 93 processes in the first dump and 90 in the second (kernel worker threads came and went). A hypervisor dump of a running guest is a smear too, unless you pause the guest first, which I did not do. Pausing (the QEMU monitor has `stop`; I did not test it with `dump-guest-memory`) is the way to get a single instant. The cost is that a paused guest stops answering the network, and a timing-sensitive attack may notice.

None of this makes memory evidence useless. It means you write down what you did, in what order, and what tool you ran, so a reader can judge what your capture changed.

## Symbol tables: why Volatility 3 needs them

A memory image is a long run of bytes. To find the process list in it, Volatility needs to know where the kernel keeps it and what each field of a process record looks like: the offsets of the process ID, the parent, the name, the command line. Those layouts differ between kernel versions, and sometimes between two builds of the same version. A **symbol table** is a file that describes them for one specific kernel. Volatility 3's symbol table format is JSON (called ISF, Intermediate Symbol File).

The project's symbol-tables page, read on 2026-11-07, says this for each system:

- **Windows.** Volatility finds the identifying GUID and age of the kernel in the image, looks for a matching file, and if there is none it **downloads the matching debug file (PDB) from Microsoft's symbol server, converts it, and saves it**. The Windows tutorial says the same. This needs an internet connection from the analysis machine the first time, and it is why a Windows image usually just works.
- **Linux and macOS.** Volatility finds the kernel's version banner in the image and looks for a symbol file with that banner. The banner has to match the image exactly, including compile time and compiler version; "matching only the version number is not enough." Linux kernels need a separately installed debug-symbol package, and some distributions do not keep old ones.

Where to get a Linux table: the Linux tutorial (read 2026-11-07) points to a community collection of prebuilt ISF files for Debian, Ubuntu and AlmaLinux (Abyss-W4tcher/volatility3-symbols on GitHub). That collection is third-party; the Volatility project does not run it. When it has no match, you build the table with the project's tool, **dwarf2json**, from the distribution's debug kernel: `dwarf2json linux --elf [path to debug kernel] > [kernel name].json`. Files go under `volatility3/symbols/linux` (or any directory you pass with `-s`) and may be compressed as `.json.xz`.

What that looked like for me: the guest ran `6.12.115+deb13.1-cloud-amd64`. I listed the prebuilt collection's Debian amd64 directory through its API on 2026-11-07 and saw no 6.12.115 entry (its 6.12 entries stopped at `6.12.96+deb13`), so I built my own, as Exercise 5 shows. The build took 41 seconds for a 49.9 MB JSON file (the debug package unpacked to 1.8 GB).

What happens without it, run verbatim on the same dump with no symbol directory given:

```text
Unable to validate the plugin requirements: ['plugins.PsList.kernel.layer_name', 'plugins.PsList.kernel.symbol_table_name']
Unsatisfied requirement plugins.PsList.kernel.layer_name:
Unsatisfied requirement plugins.PsList.kernel.symbol_table_name:
```

followed by a checklist ending "The symbol file is named appropriately or contains the correct banner". That is the message you will see most. It means: no symbol file matched the banner in this image.

## Plugins: what to run for what

Volatility 3 is a framework; each analysis is a plugin. You run `vol -f IMAGE PLUGIN`. The names below are from the plugin list that `vol -h` printed for 2.28.2 on 2026-11-07. **I ran only the Linux ones below on a real dump.**

| Question | Linux plugin | Windows plugin |
|---|---|---|
| What operating system and kernel is this? | `banners.Banners` (ran) | `windows.info.Info` |
| What processes were running? | `linux.pslist.PsList` (ran) | `windows.pslist.PsList` |
| What processes exist, including ones that are gone or hidden from the list? | `linux.psscan.PsScan` (ran) | `windows.psscan.PsScan` |
| Who started what? | `linux.pstree.PsTree` | `windows.pstree.PsTree` |
| What arguments did each process get? | `linux.psaux.PsAux` (ran) | `windows.cmdline.CmdLine` |
| What was connected or listening? | `linux.sockstat.Sockstat` (ran) | `windows.netstat.NetStat`, `windows.netscan.NetScan` |
| What files did a process have open? | `linux.lsof.Lsof` (ran) | not covered here |
| Memory that looks injected? | `linux.malware.malfind.Malfind` (ran) | `windows.malfind.Malfind` |

What the pairs mean:

- **`pslist` versus `psscan`.** `pslist` follows the kernel's own list of processes, so it shows what the kernel will admit to. `psscan` scans memory for process records, so it can find processes that were removed from the list or have exited but not yet been overwritten. A process in `psscan` and not in `pslist` is worth a look; in a quiet system it usually just exited. In my first dump `pslist` showed 93 processes and `psscan` 126.
- **`netstat` versus `netscan` on Windows.** I believe `netscan` scans memory for network objects and so can find closed connections, as `psscan` does for processes, and that it is aimed at older Windows versions while `netstat` walks live structures (**est.**; I did not run either, and the Windows tutorial I read does not mention them). Run both on a real Windows image and compare.
- **`malfind`.** It lists memory regions in a process that are executable and not backed by a file on disk, which is what injected code often looks like. It also flags legitimate things such as just-in-time compilers, so a hit is a lead, not a verdict. On my clean guest it printed only its header: no regions.

Output can be written as text, CSV or JSON, and many plugins can dump the object they found (an executable, a file) to a directory; read `vol -h` and the plugin's own `-h` for the options of your version.

### Reading output

Read the columns before the rows. In `linux.pslist.PsList` the key columns are `PID`, `PPID` (parent), `COMM` (the process name, truncated to 15 characters by the kernel) and `CREATION TIME`. A name is only a label: a program can be called anything. The `PsAux` plugin shows the real command line, which says more. Start with the oddities: a shell with a network service as its parent, a system-sounding name running from a home directory, a process whose parent no longer exists (`PPID` of 1 on Linux means it was re-parented to the init process).

Treat the timestamps with care. They are the clock of the machine that was captured, in UTC here, and a clock can be wrong or set by an attacker.

## Honest limits

- **Encrypted memory.** Some processors can encrypt a virtual machine's RAM so the host cannot read it. A hypervisor dump of such a guest, or a hardware capture, gives you ciphertext that Volatility cannot parse (**est.**; this is general knowledge and I did not read the vendor pages or test it). Inside the guest, memory is readable as usual.
- **Anti-forensics.** A kernel-level attacker can lie to a capture tool running in the same kernel by hiding processes and files from the very lists it asks. That is why a hypervisor dump is preferred, why `psscan` exists next to `pslist`, and why Volatility 3 ships checks such as `linux.malware.hidden_modules.Hidden_modules` and `linux.malware.check_syscall.Check_syscall` (names from `vol -h`, **not run**). An attacker who knows the tool can also overwrite what you would look for. Absence of a finding in memory is not proof of absence.
- **Version drift.** Operating systems change structures between releases, so a Volatility plugin that works on one kernel can fail or mislead on a newer one, and new plugin features lag new kernels. Plugins are also renamed. I hit one: on 2.28.2, `linux.malfind.Malfind` still runs, but prints a deprecation warning saying it "will be removed in the first release after 2026-06-07" and asks you to call `linux.malware.malfind.Malfind`. Both names were listed by `vol -h` on 2.28.2. The release it names (2026-06-07) is already past in my run, so the old name has outlived its own notice; do not rely on that. Pin the version you used in your notes, along with the symbol file.
- **What RAM cannot show.** Firmware, the management engine and anything running on other processors do not appear in an operating system's memory view. See the [Intel ME lesson](Device-Firmware-Security-Intel-ME-AMD-PSP-MINIX-and-Kernel-Design.md) and the [open firmware lesson](Open-Firmware-and-Trustworthy-Hardware-coreboot-Heads-Nitrokey-and-Vendors-That-Ship-the-Intel-ME-Disabled.md).
- **Smear.** Covered above. A live capture is not a single instant.
- **Legal and chain of custody.** An image taken without authority is a problem for the person who took it. In a real incident you document who captured what, when, with which tool, and the hash. This page is for your own systems.

## Volatility 3: version and license

I installed it from the Python Package Index (`pip install volatility3`), which gave **2.28.2**, uploaded **2026-09-17** (PyPI and the project's release list agree). The two releases before it, from the same list, were 2.28.0 (2026-04-30) and 2.27.0 (2026-01-29). The project is the Volatility Foundation's, and the repository was last pushed to on 2026-10-12 (read 2026-11-07). Its license is the **Volatility Software License, Version 1.0** (dated 2019-10-03). The first part of the text, which I read on 2026-11-07, grants free use and sharing and requires that if you make "Additions" (changes, wrappers that run the software and parse its output, and similar) available, including over the Internet, you publish them as source. I read only the opening of the license; **have a lawyer read it before you build a product around it (est.)**, because GitHub's own license detector reports it as unrecognized and the clause about what counts as an Addition is the part that matters for a commercial tool. It is not an OSI-approved license (**est.**; I did not check the OSI list).

## Free path: dump a lab VM and find what you started

Everything is local and free. Use a throwaway directory. Disk: about 6 GB. The numbers below are what happened on my machine on 2026-11-07, one run each.

### Exercise 1: get Volatility 3 into its own Python environment

```bash
mkdir -p ~/memlab && cd ~/memlab
python3 -m venv venv
./venv/bin/pip install volatility3
./venv/bin/vol -h | head -3
```

Mine printed `Volatility 3 Framework 2.28.2`. The `vol` command is installed into the environment's `bin`.

### Exercise 2: boot a guest

I used Debian 13 "trixie" `genericcloud` image from `cloud.debian.org` (341 MB), which has no password login; a small "cidata" disk gives it a user and a key. Check the download against the project's checksum file first.

```bash
cd ~/memlab
curl -LO https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2
curl -L https://cloud.debian.org/images/cloud/trixie/latest/SHA512SUMS | grep genericcloud-amd64.qcow2 > sums
sha512sum -c sums
```

If the check does not say `OK`, do not boot the image. Mine matched.

```bash
ssh-keygen -q -t ed25519 -N "" -f labkey
mkdir seed
printf '#cloud-config\nusers:\n  - name: lab\n    sudo: ALL=(ALL) NOPASSWD:ALL\n    shell: /bin/bash\n    ssh_authorized_keys:\n      - %s\n' "$(cat labkey.pub)" > seed/user-data
printf 'instance-id: lab1\nlocal-hostname: lab\n' > seed/meta-data
genisoimage -quiet -output seed.iso -volid cidata -joliet -rock seed/user-data seed/meta-data
qemu-img create -q -f qcow2 -b debian-13-genericcloud-amd64.qcow2 -F qcow2 disk.qcow2 10G
qemu-system-x86_64 -accel kvm -m 2048 -smp 2 -display none -serial file:serial.log \
  -drive file=disk.qcow2,if=virtio -drive file=seed.iso,media=cdrom \
  -nic user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:2222-:22 \
  -monitor unix:mon.sock,server,nowait -pidfile qemu.pid &
```

Two things failed for me, so you can skip them. First, with a plain `-nic user` the guest had **no network card**: this kernel build has no driver for QEMU's default emulated card, so `model=virtio-net-pci` is not optional. Second, the first boots took over two minutes under load, and `ssh` printed "Connection timed out during banner exchange" until the guest finished; use `-o ConnectTimeout=40` and wait for `login:` in `serial.log`. The guest is on QEMU's outbound-only network; the one open port is on your own `127.0.0.1`.

### Exercise 3: start a known process, a known file and a known listener

```bash
S="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=40 -i labkey -p 2222 lab@127.0.0.1"
$S 'uname -r; cat /proc/version'
$S 'cp /bin/sleep /home/lab/labmarker; echo "N0TST lab note: the-quick-brown-fox-424242" > /home/lab/lab-notes.txt; nohup /home/lab/labmarker 100000 >/dev/null 2>&1 & nohup tail -f /home/lab/lab-notes.txt >/dev/null 2>&1 & nohup nc -l 127.0.0.1 4444 >/dev/null 2>&1 &'
```

(Disabling the host-key check is acceptable here only because the guest is a local, throwaway machine you just built.) My kernel was `6.12.115+deb13.1-cloud-amd64`. `labmarker` is a copy of `sleep` with a name no real program has, so it is easy to find; `tail -f` holds the note file open; `nc` listens on port 4444 on the guest's loopback. These were PIDs 803, 804 and 805 for me; yours will differ.

### Exercise 4: take the dump from the hypervisor

QEMU's monitor was on a Unix socket, so I sent the command with a few lines of Python. With `-monitor stdio` instead of the socket you can type `dump-guest-memory` at the `(qemu)` prompt (**est.**; I used the socket).

```bash
mkdir -p ~/memlab/dump
python3 -I - <<'PY'
import os, socket, time
s = socket.socket(socket.AF_UNIX)
s.connect(os.path.expanduser("~/memlab/mon.sock"))
s.settimeout(5)
s.send(("dump-guest-memory " + os.path.expanduser("~/memlab/dump/lab.core") + "\n").encode())
time.sleep(30)
PY
ls -l ~/memlab/dump
sha256sum ~/memlab/dump/lab.core
```

Mine was 2,164,394,051 bytes, about 2 GB for a 2 GB guest, and `info dump` reported `Status: completed` when I checked after waiting 30 seconds. Keep the `sha256sum` output; I ran it on my dump after the analysis, not right after taking it, which is the wrong order for real evidence. That file is an ELF core file; Volatility 3 recognized it with no conversion. The dump contains everything in the guest's RAM, so delete it when you finish.

### Exercise 5: build the symbol table

The table has to match the banner in the image. Read the exact kernel from the dump first:

```bash
cd ~/memlab
./venv/bin/vol -q -f dump/lab.core banners.Banners
```

Mine printed a banner beginning `Linux version 6.12.115+deb13.1-cloud-amd64` (four hits at four offsets, because the banner string sits in several places in memory) and ending `Debian 6.12.115-2 (2026-11-01)`.

Debian's kernel debug symbols are a package named `linux-image-<version>-dbg`. Mine was in the security archive, not the main archive, because the kernel had a recent security update:

```bash
mkdir -p dbg syms/linux
curl -o dbg/kernel-dbg.deb "https://security.debian.org/debian-security/pool/updates/main/l/linux/linux-image-6.12.115+deb13.1-cloud-amd64-dbg_6.12.115-2_amd64.deb"
dpkg-deb -x dbg/kernel-dbg.deb dbg/ex
curl -L -o dwarf2json https://github.com/volatilityfoundation/dwarf2json/releases/download/v0.9.0/dwarf2json-linux-amd64
chmod +x dwarf2json
./dwarf2json linux --elf dbg/ex/usr/lib/debug/boot/vmlinux-6.12.115+deb13.1-cloud-amd64 > syms/linux/debian-6.12.115-cloud.json
```

Substitute the version your guest printed. The package was 306 MB and unpacked to 1.8 GB. I took `dwarf2json` from the project's release page rather than building it from source as the docs describe (the docs say to clone and run `go build`); its checksum was `e2e75ba5bc9c22bc38a48edffbb050456d089d54998d54f46cb580223d9fbc6b` on my download, and **I did not verify it against anything the project publishes**. Do the same check you would for any binary you are about to run. I also did not verify the `.deb` against the archive's package index. `dwarf2json 0.9.0` printed "output schema 6.2.0". The run took 41 seconds and wrote a 49.9 MB file. If your distribution's collection already has your kernel (the prebuilt collection above is the first place to look), download that file into `syms/linux/` and skip all of this.

### Exercise 6: ask the dump questions

```bash
cd ~/memlab
./venv/bin/vol -q -s syms -f dump/lab.core linux.pslist.PsList | grep -E "PID|labmarker|tail|nc"
```

Mine, trimmed to the columns that matter:

```text
OFFSET (V)      PID  TID  PPID  COMM        UID   ... CREATION TIME
0x89fc05691840  803  803  1     labmarker   1000  ... 2026-11-07 15:24:02 UTC
0x89fc05690000  804  804  1     tail        1000  ... 2026-11-07 15:24:02 UTC
0x89fc01abc8c0  805  805  1     nc          1000  ... 2026-11-07 15:24:02 UTC
```

That is the process I started, found in a dump that never ran a capture program inside the guest. Then the command lines, the listener and the open file:

```bash
./venv/bin/vol -q -s syms -f dump/lab.core linux.psaux.PsAux
./venv/bin/vol -q -s syms -f dump/lab.core linux.sockstat.Sockstat | grep 4444
./venv/bin/vol -q -s syms -f dump/lab.core linux.lsof.Lsof | grep lab-notes
```

`PsAux` showed `/home/lab/labmarker 100000`, `tail -f /home/lab/lab-notes.txt` and `nc -l 127.0.0.1 4444`. `Sockstat` showed `nc` (PID 805) as an `AF_INET` `STREAM` `TCP` socket on `127.0.0.1` port 4444 in state `LISTEN`. `Lsof` showed `tail` (PID 804) holding `/home/lab/lab-notes.txt` open on file descriptor 3, with size 43, which is the length of the note I wrote. Finally the note itself, as text in the raw image:

```bash
grep -a -b -o "the-quick-brown-fox-424242" dump/lab.core | head
```

It matched at seven offsets (the first at byte 136,584,040), because RAM held it in the page cache and in buffers. That is the "credentials and keys in RAM" point at small scale: a string you wrote, not hidden anywhere, readable in a file you could copy to another machine.

Last, the two checks that should find nothing on a clean guest:

```bash
./venv/bin/vol -q -s syms -f dump/lab.core linux.malware.malfind.Malfind
./venv/bin/vol -q -s syms -f dump/lab.core linux.psscan.PsScan | grep -c "^0x"
```

`malfind` printed only its header. `psscan` found 126 process records against the 93 that `pslist` listed; I did not work out which of the extra 33 were exited processes and which were something else, so I cannot tell you they were all benign. Chasing that difference is the next exercise.

Each plugin took about 7 seconds on a warm run on this machine (one measured: `linux.pslist.PsList` 6.7 seconds).

### Exercise 7: clean up

```bash
pid=$(cat ~/memlab/qemu.pid)
case "$pid" in ""|*[!0-9]*) echo "not a pid"; exit 1;; esac
ps -o command= -p "$pid"
kill "$pid"
rm -r ~/memlab
```

The `ps` line should show your `qemu-system-x86_64` command; if it shows anything else, stop and do not kill it.

The dump, the key, the guest disk and the unpacked debug package are all under that one directory. Check `ps -C qemu-system-x86_64` shows nothing left.

## Build, break, detect, evade, defend

**Build.** The lab above: a guest, a known process, a dump, a symbol table.

**Break.** Change one thing and watch the tool fail the way it will in real life: run the plugin without `-s syms`, or with a symbol file for a different kernel. Both give the "Unsatisfied requirement" message. Then boot the guest again, apply a kernel update, and try the old symbol file against a new dump. The banner no longer matches. That is version drift in two minutes.

**Detect.** What a defender watches for around memory capture: a kernel module loaded by an administrator who does not normally do that, a new driver on a Windows machine, a large file appearing in an odd place. On the analysis side, `psscan` against `pslist`, `malfind`, and a listening port on a process that should not listen are the first three checks.

**Evade, in words only.** An attacker who has the kernel hides processes from the list a tool walks, runs only in memory so nothing is left on disk, or scrubs what an analyst would look for after the fact. This page shows no technique. The point for the defender: do not trust a single list, take the dump from outside the machine when you can, and compare views.

**Defend.** Collect memory early, from outside if possible; record the hash and the tool; keep the image offline and encrypted; analyze a copy. Keep a symbol file for each kernel you run in production, built at release time while the debug package still exists.

### Flip the board

**The reviewer.** A teammate writes: "The server was hacked. I rebooted it to be safe, then ran a memory capture on the clean boot, and the malware is not in the image, so it was a false alarm." Find at least four problems.

<details>
<summary>What to find</summary>

1. Rebooting destroyed the memory that would have held the evidence; this is the order of volatility backwards.
2. A capture of a freshly booted machine shows a fresh boot, not the compromised state.
3. Absence in a capture is not proof of absence, particularly of kernel-level malware.
4. The tool ran inside the possibly compromised system, so what it reported was only what that system allowed.
5. No hash, no record of the tool or time, no chain of custody.
6. "False alarm" is a conclusion; no other evidence (logs, disk, network) was weighed.

</details>

**The auditor.** A manager says "we capture memory for every incident and keep the images for ten years." What does the image contain, who can read it, and what should the retention rule say? (Passwords, keys and other people's data; anyone with the file; a short, justified retention, encrypted storage, and access logging.)

## Checkpoint

Without looking back: name three things that exist in RAM and often nowhere else; say why a hypervisor dump is better than a tool running inside the guest and what it still does not give you; explain smear; say what a symbol table is and what message you get when it is missing; say the difference between `pslist` and `psscan`; name two limits of memory forensics.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "Unsatisfied requirement ... symbol_table_name" | No symbol file matched the image's banner | Run `banners.Banners`; match the kernel string exactly; put the file under a `-s` directory |
| "The prebuilt table is for the same kernel version, so it will do" | The banner includes compile details and must match exactly | Compare the full banner, not the version number |
| "It is Linux, so I can use any Debian symbols" | A cloud kernel and a standard kernel of the same version are different builds | The `-cloud-amd64` suffix in `uname -r` |
| "`-nic user` gave my guest no network" | The default emulated card has no driver in this cloud kernel | `model=virtio-net-pci` |
| "The process is in `psscan` but not `pslist`, so it is malware" | Exited processes also appear there | Check state and exit information, then context |
| "`malfind` printed a hit, so it is injected malware" | Just-in-time compilers and some legitimate software do the same | Look at the process and the region before calling it |
| "I rebooted first to be safe" | You destroyed the evidence | Capture first, if the incident owner agrees |
| "The dump is just a file, I can email it" | It holds passwords and keys | Treat it like the secrets inside it |
| "`linux.malfind.Malfind` runs, so the name is fine" | It is a deprecated alias that may be removed | Use `linux.malware.malfind.Malfind` and note the version |

## Claims register

Retrieved 2026-11-07 with read-only requests, unless stated. "Read" means I read the page text. "Observed" means I ran it on the machine described in the status note.

| Claim | Source | Status |
|---|---|---|
| Volatility 3 latest release is 2.28.2, uploaded 2026-09-17; 2.28.0 on 2026-04-30; 2.27.0 on 2026-01-29; repository last pushed 2026-10-12 | [PyPI: volatility3](https://pypi.org/project/volatility3/), the project's release list on [GitHub](https://github.com/volatilityfoundation/volatility3/releases) (read through the public API) | Read |
| Volatility 3 license is the Volatility Software License, Version 1.0 (October 3, 2019): free use and sharing, source of "Additions" must be published | [LICENSE.txt in the repository](https://github.com/volatilityfoundation/volatility3/blob/develop/LICENSE.txt) | Read (opening of the text only) |
| GitHub's license detector does not recognize the Volatility license | The repository's metadata through the public API | Observed |
| Windows: symbol file found by GUID and age, downloaded from Microsoft's symbol server, converted and stored if missing | [Volatility 3: symbol tables](https://volatility3.readthedocs.io/en/latest/symbol-tables.html), [Windows tutorial](https://volatility3.readthedocs.io/en/latest/getting-started-windows-tutorial.html) | Read |
| Linux and Mac: banner must match exactly, including compile time and compiler; `banners` and `isfinfo` plugins; dwarf2json usage and directory layout; `.json`, `.json.gz`, `.json.xz` or ZIP accepted | [Volatility 3: symbol tables](https://volatility3.readthedocs.io/en/latest/symbol-tables.html) | Read; the dwarf2json step and banner match Observed |
| Linux tutorial points to a community collection of prebuilt Linux symbol files (Debian, Ubuntu, AlmaLinux), third-party | [Volatility 3: Linux tutorial](https://volatility3.readthedocs.io/en/latest/getting-started-linux-tutorial.html) | Read |
| The collection's Debian amd64 listing had no 6.12.115 entry on 2026-11-07 | The collection's directory listing through the GitHub API | Observed (names only; I did not open the files) |
| Windows tutorial names WinPmem and FTK Imager as acquisition tools, no usage given | [Volatility 3: Windows tutorial](https://volatility3.readthedocs.io/en/latest/getting-started-windows-tutorial.html) | Read |
| Raw LiME-format image and a page file can be combined into one layer | [Volatility 3: basics](https://volatility3.readthedocs.io/en/latest/basics.html) | Read |
| Plugin names on 2.28.2 (the Linux and Windows ones in the table; `linux.malfind` and `linux.malware.malfind` both listed) | `vol -h` from the installed package | Observed |
| `linux.malfind.Malfind` deprecation warning naming 2026-06-07 | Output of that plugin on 2.28.2 | Observed |
| LiME: loadable kernel module, GPL-2.0, formats raw, padded, lime, `insmod` syntax, `path=tcp:` option; latest release v1.12.0 on 2026-03-31 | [LiME on GitHub](https://github.com/504ensicsLabs/LiME) and its release list | Read; not built or run |
| WinPmem: Apache-2.0, raw output from the mini builds, `winpmem_mini_x64.exe physmem.raw`, signed binaries have write support off, README names Windows 7 to 10; newest listed release `v4.1.dev1` (pre-release, 2024-11-23) | [WinPmem on GitHub](https://github.com/Velocidex/WinPmem) and its release list | Read; not run. Which build suits a current Windows: **est.** |
| FTK Imager: free, memory capture on a live device; no version shown on the product page; download asks for contact details | [Exterro: FTK Imager](https://exterro.com/digital-forensics-software/ftk-imager) | Read. Menu path and raw output: from a secondary guide, **est.** |
| RFC 3227 section 2.1 order of volatility; section 2 "Minimize changes to the data as you are collecting it" | [RFC 3227](https://www.rfc-editor.org/rfc/rfc3227.txt) | Read |
| QEMU `dump-guest-memory` wrote a 2,164,394,051-byte ELF core file for a 2 GB guest that Volatility 3 read directly | QEMU 10.0.13 monitor, Volatility 3 2.28.2 | Observed |
| Two dumps three minutes apart differed in 1,583 of 528,417 pages; `pslist` listed 93 then 90 processes | My comparison script on the two dumps | Observed |
| `-nic user` with no model gave the Debian cloud guest no network card; `model=virtio-net-pci` worked | Guest console log (cloud-init's device table showed only loopback) | Observed |
| Debian cloud image `genericcloud-amd64.qcow2` matches the project's SHA512SUMS | [Debian cloud images](https://cloud.debian.org/images/cloud/trixie/latest/) | Observed |
| dwarf2json 0.9.0, output schema 6.2.0, built a 49.9 MB table in 41 seconds from the debug kernel | The release binary, run locally | Observed. Binary's integrity: not verified |
| VMware `.vmem` and VirtualBox `debugvm` as memory sources; VMware/VirtualBox memory handling | Volatility 2 documentation quoted in a search result; no vendor page read | **est.** |
| Memory encryption on VMs hides RAM from a hypervisor dump | General knowledge | **est.** |
| `netscan` versus `netstat` behavior on Windows | General knowledge | **est.** |
| The Volatility license is not OSI approved | General knowledge | **est.** |

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Security tools and threat modeling](Contents.md#security-tools-and-threat-modeling) > Memory forensics with Volatility 3

In this group: [Security tools and threat modeling](Contents.md#security-tools-and-threat-modeling), 8 pages

- Also here: [Threats in plain words](Threats-in-Plain-Words.md) / [Security tools: Nmap, OpenVAS, Burp, Metasploit](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md) / [Email security](Email-Security-DNS-Gateways-and-API-Driven-Protection.md) / [Threat model exercise](Threat-Model-Exercise.md) / [Threat Dragon exercise](Threat-Dragon-Exercise.md) / [Threat frameworks: STRIDE, ATT&CK, ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md)
- Digital forensics: **Memory forensics with Volatility 3** / [Disk forensics with Autopsy and The Sleuth Kit](Disk-Forensics-with-Autopsy-and-The-Sleuth-Kit.md)

Related pages:

- [Disk forensics with Autopsy and The Sleuth Kit](Disk-Forensics-with-Autopsy-and-The-Sleuth-Kit.md)
- [Security tools: Nmap, OpenVAS, Burp, Metasploit](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md)
- [Email security](Email-Security-DNS-Gateways-and-API-Driven-Protection.md)
- [Threats in plain words](Threats-in-Plain-Words.md)
<!-- END GENERATED PAGE NAV bottom -->
