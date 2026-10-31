# Virtual machines for beginners: hypervisors, the desktop options and the bigger platforms

Side page to the start-from-zero pages. Read it when a lesson says "in a virtual machine" or "on a Linux host" and you do not have one yet, or when you keep hearing "type 1", "KVM", "Proxmox" or "what happened to VMware" and want the words sorted out. It sits beside [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md), which draws a VM next to a container and the cloud service models; this page is about the machines you run on **your own** computer or server. Next: [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. Only the checksum step, `qemu-img` and a few read-only host checks were run; no hypervisor was installed and no guest was booted.** On **2026-10-31** I ran, on one Linux machine with QEMU 10.0.13 (a Debian build), these things: `sha256sum -c` on a downloaded Alpine ISO, `qemu-img create`, `qemu-img info` and `qemu-img snapshot` (create, list, apply, delete) on a throwaway disk image, a read-only look at the CPU and `/dev/kvm`, and the first-VM command with the display switched off and the virtual CPU paused (it started and I stopped it after three seconds, so I know the options parse, not that the guest boots). **Not run:** booting the guest, VirtualBox, VMware, Hyper-V, Proxmox, TrueNAS, Xen, anything on macOS or Windows, and every PowerShell line. Vendor statements were read on **2026-10-31** from the pages named in the [claims register](#claims-register); a claim I could not read there is marked **est.** Trust what your terminal prints over what this page says.

> **Prerequisites.** A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)). Knowing what a hash is helps ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)). You do not need to have run a VM before. The free path needs a computer with a processor that supports virtualization, roughly 4 GB of free memory and 10 GB of free disk (est.), and a download of about 70 MB. About 90 minutes for the reading and the exercises (est.).

> **Where this runs, and the rule.** Everything here is local and throwaway. The first VM uses QEMU's default networking, which gives the guest a private, outbound-only network. Nothing on this page asks you to expose a VM to your home network, and the one place a lab can go wrong, bridging a hostile VM onto your real network, is a **do not** in [the safety rule](#the-safety-rule-for-malware-and-recon-labs). No real addresses appear; the only address in a command is `127.0.0.1`, your own computer.

## What you will be able to do

- Say what a virtual machine is, what a hypervisor is, and give three reasons a learner wants one.
- Explain type 1 and type 2 hypervisors, and why KVM does not fit neatly in either.
- Name the desktop choices for Linux, Mac and Windows hosts, say what each costs and what it is licensed as, and pick one.
- Give a dated, neutral account of what changed for VMware products after Broadcom bought the company, with each claim marked read or estimated.
- Say what TrueNAS, Proxmox VE, Xen, ESXi and the enterprise platforms are for, and how they differ from a desktop hypervisor.
- Verify a downloaded ISO with a checksum, create a virtual disk, take a snapshot and roll back, and start a first VM.
- Choose NAT, host-only, internal or bridged networking for a lab, and say why a lab defaults to NAT or host-only.
- Size a host for a lab, and know what nested virtualization is and when it fails.
- Follow the safety rule for malware and recon labs.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Virtual machine, hypervisor, guest | [What is the cloud](What-Is-the-Cloud.md#a-virtual-machine-a-little-more-precisely); [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md#virtual-machines) | How to get one on your own computer, and which tool. |
| Container tools run a small Linux VM on Mac and Windows | [Containers and Docker basics](Containers-and-Docker-Basics.md), [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) | What those VMs are made of, and your other options. |
| "Use a VM on a host-only network" | [Security tools basics](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md) | What host-only means, how to make one and what else to switch off. |
| "Snapshot first" | [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) | How a snapshot works and what it is not. |

## What a virtual machine is, and why use one

A **virtual machine (VM)** is a whole computer made of software: a virtual processor, memory, disk and network card, running its own operating system with its own kernel. The program that makes the pretend hardware is the **hypervisor**. The machine you install it on is the **host**; the operating system inside the VM is the **guest**. The cloud lesson draws the stack ([Virtual machines](Virtual-Machines-Containers-and-Cloud-Service-Models.md#virtual-machines)); the idea is the same on your laptop.

Why a learner wants one:

- **Safe to break.** Delete the wrong folder, run a script you do not trust, misconfigure the firewall: the damage stays inside the guest, and you rebuild it.
- **Isolated from your real computer.** The guest has its own disk file and its own network card, so an experiment does not touch your files unless you connect them. This is a strong barrier, not a perfect one (see [the safety rule](#the-safety-rule-for-malware-and-recon-labs)).
- **Other operating systems on one computer.** A Linux lab on a Windows or Mac laptop, a test Windows on a Linux desktop. One limit: a guest that runs at full speed must be built for the same processor family as the host. A Mac with an Apple processor runs Arm guests natively; Apple's documentation says its framework "emulates a complete hardware machine of the same architecture as the underlying Mac computer" (read 2026-10-31). Running a different architecture means full emulation, which QEMU can do and which is much slower (est. for "much"; QEMU's page says the CPU "may be fully emulated").
- **Snapshots.** Save the state of the machine, try something, go back ([snapshots](#snapshots-an-undo-button-that-is-not-a-backup)).

## Type 1 and type 2, honestly

Textbooks sort hypervisors into two types.

```text
  Type 1 (bare metal)                 Type 2 (hosted)

  VM A    VM B    VM C                VM A    VM B
 +------+ +------+ +------+          +------+ +------+
 | apps | | apps | | apps |          | apps | | apps |
 | OS   | | OS   | | OS   |          | OS   | | OS   |
 +------+ +------+ +------+          +------+ +------+
 |  hypervisor            |          |  hypervisor (an ordinary program)
 |  hardware              |          |  host operating system
 +------------------------+          |  hardware
                                     +--------------------------+
```

- A **type 1** hypervisor runs directly on the hardware and starts the guests itself. Xen's project page calls Xen "an open-source type-1 or baremetal hypervisor"; Microsoft's overview says "As a type-1 hypervisor, Hyper-V runs directly on computing hardware" (both read 2026-10-31). Servers usually use this kind.
- A **type 2** hypervisor is an ordinary program on top of a normal operating system, like a word processor. VirtualBox and VMware Workstation are the usual examples (est.; their pages do not use the label). Desktops usually use this kind.

The line is blurry. The Wikipedia article on hypervisors, which I read on 2026-10-31, says "The distinction between these two types is not always clear" and gives KVM as the example: it is a **kernel module** that "effectively convert[s] the host operating system to a type-1 hypervisor". KVM's own page describes it as "a loadable kernel module, kvm.ko, that provides the core virtualization infrastructure" (read 2026-10-31). A Linux machine running KVM is an ordinary Linux desktop and also has a hypervisor in its kernel, so people argue either way. Hyper-V is similar from the other side: on Windows 10 or 11 it is a type 1 hypervisor that Windows itself runs on top of (est., from Microsoft's description that it runs directly on hardware; I did not read that detail). **Do not spend your time on the label.** The questions that matter are what it costs, what hosts it runs on, what guests it supports, and who maintains it.

What all of them need from your processor: hardware virtualization extensions (Intel VT-x, AMD-V; Microsoft's page names them and also requires second level address translation for Hyper-V). They are often switched off in the firmware settings on a new machine (est.). Exercise 1 checks yours.

## The desktop choices

The first group runs on the computer in front of you.

| Tool | Hosts | Licensed as | Notes |
|---|---|---|---|
| **KVM with QEMU**, plus **libvirt** and **virt-manager** | Linux (QEMU alone also runs on macOS, Windows and the BSDs) | Open source. QEMU is GPL version 2 | The Linux standard. KVM is the kernel part; QEMU is the program that models the machine; libvirt manages many back ends; virt-manager is the desktop app. |
| **Apple Virtualization framework**, and apps built on it | Mac, Apple silicon and Intel | Part of macOS; an interface for apps, not an app | Runs macOS or Linux guests of the Mac's own architecture. |
| **Hyper-V** | Windows 10 and 11 Pro or Enterprise, and Windows Server | Included with Windows | Not in Home editions. Type 1. |
| **VirtualBox** | Windows, macOS (Intel and Apple silicon), Linux, Solaris | Base package GPL version 3; a separate Extension Pack under a personal and educational license | Free to use, one program on every host. |
| **VMware Workstation and Fusion** | Workstation: Windows and Linux. Fusion: Mac | Proprietary, from Broadcom; free to download and use | See [the next section](#vmware-after-broadcom-a-dated-account). |

**KVM, QEMU, libvirt and virt-manager.** QEMU describes itself as "a generic and open source machine emulator and virtualizer"; with a hypervisor such as KVM, Xen or Hypervisor.framework it can "allow the guest to run directly on the host CPU", and it ships `qemu-img`, a disk image tool (read 2026-10-31). QEMU is released under the GNU General Public License, version 2. libvirt is "a toolkit to manage virtualization platforms" that supports KVM, QEMU, Xen and others, and virt-manager is "a desktop user interface for managing virtual machines through libvirt" that primarily targets KVM (both read 2026-10-31). On Debian-family systems the virt-manager page says to install it with `apt-get install virt-manager`. This is the path the exercises use, because it is the one I could run here.

**Apple's options on a Mac.** The built-in interface is the **Virtualization framework**. Apple's documentation says it provides "high-level APIs for creating and managing virtual machines (VM) on Apple silicon and Intel-based Mac computers" to "boot and run macOS or Linux-based operating systems", and its page lists macOS 11.0 as the first release that has it (read 2026-10-31 from Apple's developer documentation). So the framework itself is not new. It is a toolkit for app makers, not a window you open; an app such as UTM uses it (UTM's page says it is "built on QEMU" and can also use "Apple Virtualization", read 2026-10-31; UTM is free and open source per that page). If you remember something *new* from Apple, it is probably the **`container`** tool and its **Containerization** Swift package: Apple's repository describes `container` as "a tool that you can use to create and run Linux containers as lightweight virtual machines on your Mac", written in Swift and "optimized for Apple silicon", and says it is supported on **macOS 26** and needs a Mac with Apple silicon (read 2026-10-31). That is a way to run Linux containers, one small VM per container, rather than a general VM manager. Which Apple release you have is yours to check; I did not run any of this.

**Hyper-V on Windows.** Microsoft's page: Hyper-V is "built into Windows Server and Windows" and applies to Windows 10 and 11; the role "can't be installed on Windows 10 Home or Windows 11 Home", and Windows 10 or 11 Pro or Enterprise with a 64-bit processor with second level address translation and at least 4 GB of memory is required (read 2026-10-31). Microsoft warns that third-party virtualization apps such as VMware Workstation and VirtualBox may start VMs that "might not start or might run unreliably" while the Hyper-V hypervisor is running (same page). So on Windows pick one tool as your daily driver. Windows Home users: use VirtualBox or VMware Workstation.

**VirtualBox.** Oracle's pages: the base package is "licensed under the GNU General Public License, version 3"; the Extension Pack is "freely available under the VirtualBox Extension Pack Personal Use and Educational License (PUEL) for personal and educational use", and a fee applies for commercial use (Licensing FAQ, last updated 12 September 2024, read 2026-10-31). The downloads page on 2026-10-31 offered VirtualBox 7.2.22 for Windows, macOS on Intel and Apple silicon, Linux and Solaris. Most beginners never need the Extension Pack; if you add it for a business, read the license first.

## VMware after Broadcom: a dated account

This section is here because many tutorials and old forum answers say "just use VMware Workstation Player" or "download the free ESXi", and the situation changed. It is told from Broadcom's and VMware's own pages first, then one news source for the customer side. Each row says whether I **read** the source on 2026-10-31 or the point is **est.** I have left out adjectives; the sources do not need them.

| Date | What happened | Source | Status |
|---|---|---|---|
| 2023-11-22 | Broadcom completed its acquisition of VMware, reported at $69 billion | BBC News, 23 November 2023 | Read |
| 2023-12-11 | VMware announced the end of perpetual licensing: VMware Cloud Foundation (VCF) and vSphere Foundation, "available as subscription software only", became the two main offers, and many products "will not be available for purchase as standalone point solutions". The list of products no longer sold alone includes "VMware vSphere Hypervisor (free edition)" | VMware blog "VMware End Of Availability of Perpetual Licensing and SaaS Services" (replaces a knowledge base article from 15 January 2024) | Read |
| May 2024 | Workstation Pro and Fusion Pro became "Free for Personal Use" or "Paid Commercial Use". Workstation Player and Fusion Player were discontinued. The commercial subscription was one product at $120 a year. Downloads moved to a Broadcom support-portal account | VMware Workstation blog post, dated by its address (2024/05); I read an archived copy because the live address now redirects | Read (archived copy) |
| 2024-11-11 | Fusion and Workstation became "available for free to everyone" including commercial users; the paid Pro versions "are no longer available for purchase". Support tickets end with a contract | VMware Cloud Foundation blog "VMware Fusion and Workstation are Now Free for All Users" | Read |
| 2025-03-10 | Broadcom's follow-up post says free users "are NOT ENTITLED TO SUPPORT THROUGH THE GLOBAL SUPPORT TEAM" and points them to community forums and documentation | VMware Cloud Foundation blog, dated by its address (2025/03/10) | Read |
| 2025-04-10 | ESXi 8.0 Update 3e (build 24674464) released. Its notes say Broadcom "makes available the VMware vSphere Hypervisor version 8, an entry-level hypervisor", with no Broadcom support, "for non-production use", no vCenter management, a maximum of 8 virtual CPUs per VM, free of charge from the Broadcom Support portal | Broadcom ESXi 8.0 Update 3e release notes | Read |
| 2025 to 2026 | Workstation documentation now lists versions 17.0, 25H2 and 26H1 (the 26H1 page was updated 2026-10-30), so the product moved from a numbered release (17) to half-year names. Workstation Player is documented inside the Workstation Pro pages | Broadcom Workstation Pro documentation | Read. That the new names are a deliberate scheme: **est.** |

What this means for a learner, as of 2026-10-31:

- **Desktop VMware is free to download and use** (Workstation for Windows and Linux, Fusion for Mac), personal or commercial, on the terms of Broadcom's November 2024 post, with community support only. You need a Broadcom account to download (stated in May 2024; whether that is still true today: **not verified**). Read the license text on the day you download; the terms changed several times in the table above.
- **"Workstation Player" is gone as a separate product** (May 2024 post). Old tutorials that start with Player still describe the interface, but you download Workstation Pro.
- **The free ESXi is back, with limits** (8 vCPUs per VM, no support, non-production). It is a type 1 hypervisor you install on a spare machine, covered below.

**Why many people moved away.** The desktop products got cheaper (free). The pressure was on the server side, where the source is the technology press. Ars Technica reported on 2024-10-31, one year after the acquisition, that many customers it spoke with said their VMware costs "rose 300 percent", that VMware products "were previously sold under 8,000 SKUs, but they have now been combined into a few bundle packages", and that AT&T claimed Broadcom proposed a 1,050 percent price increase (AT&T sued Broadcom over perpetual-license support; that is a claim in a lawsuit, not a finding). Ars quoted a Gartner analyst attributing the cost increases to "the required shift from perpetual licenses to subscriptions, changing the compute licensing metric, and simplifying the offers to a limited number of bundles", and quoted Gartner's 2024 report that costs "can increase two or three times". Ars also reported that Broadcom's representative declined to answer specific questions, and that Broadcom says VMware had planned a move to subscriptions before the acquisition. A June survey of 300 director-level IT workers, cited in the same article, found 83 percent of those with contracts expiring by June 2025 said they would likely stay with VMware at least partly, because moving is slow and expensive. So "many people left" is true for some customers and not a mass exodus; the article's own numbers are mixed. I did not read newer reporting for this lesson, so I make no claim about what happened in 2025 or 2026 beyond the vendor pages above.

For a hobbyist the practical points are smaller: the free desktop products are still there, tutorials may be out of date, and the open source tools below never had this problem. For a company, a change of licensing is a project, and Proxmox VE's page lists an "ESXi import" feature and its screenshot list goes back to 8.1 for it, which is the kind of tool people reach for when they move (read 2026-10-31).

## The bigger options: a tour

A desktop hypervisor shares your computer with everything else you do. The next group is installed on a machine of its own, usually a server or a spare PC, and runs many VMs for many people or services, with management over a network, clusters and backups. You will meet them at work or in a home lab.

| Platform | What it is for | How it differs from a desktop hypervisor | License model (one line) |
|---|---|---|---|
| **Proxmox VE** | A server virtualization platform: KVM virtual machines and Linux containers (LXC), clustering, high availability and backups, managed through a web page | It is the operating system on the machine (Debian-based), not an app | Open source under AGPL version 3; paid subscriptions per CPU socket for support and the enterprise update repository: Community €120 a year (non-production), Basic €370, Standard €550, Premium €1,100, with every feature at every level (price page, read 2026-10-31) |
| **TrueNAS** | A storage system built on OpenZFS that also runs apps, containers and VMs on the same box | Storage first, virtualization as a bonus; a good fit for a home lab that needs a file server | Community Edition is a free open core download with community support; TrueNAS Enterprise is sold as supported appliances |
| **Xen** | A type 1 hypervisor: a small layer under a control Linux ("domain 0") | A hypervisor you assemble into something; the base for several cloud and appliance products | Open source, a Linux Foundation project; the repository is GPL version 2 only |
| **VMware ESXi** | The type 1 hypervisor in VMware's vSphere family | Managed from vCenter in companies; the free edition cannot be | Subscription as part of vSphere or VCF; a free version with the limits above |
| **Hyper-V in Windows Server** | Hyper-V with clustering, live migration and replication for Windows-centered shops | Same hypervisor as on Windows 10 or 11, with the server features | Included with Windows Server; Microsoft says there is no "additional hypervisor licensing" |
| **Nutanix AHV** and similar corporate platforms | A hypervisor sold as part of an integrated storage and virtualization product | Bought as a platform with vendor support | Not sold alone; "included with the purchase of a Nutanix Cloud Infrastructure (NCI) software license" |
| **A cloud provider** | Renting VMs by the hour | You never see the hypervisor | See [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) |

Notes from the project pages (read 2026-10-31):

- Proxmox says its platform "tightly integrates the KVM hypervisor and Linux Containers (LXC), software-defined storage and networking functionality, on a single platform". Its price page says a subscription is needed for each occupied CPU socket, "The number of CPU cores does not affect the price", and Community is for "Home labs", "Training environments" and "Non-critical workloads". Whether you can run Proxmox with no subscription for a home lab: the Proxmox pages I read show free source and a download button, but I did not read the no-subscription repository terms, so **est.** that it is allowed for non-production use.
- TrueNAS describes Community Edition as "open core" and lists, for Community 25.10, "VMs: Windows, Linux, FreeBSD, PCIe/ USB pass-thru, CPU pinning" and Docker apps.
- Xen's page says it "uses a microkernel design, with a small memory footprint", most installations run Linux as the main control stack, and the project says it powers "the largest clouds in production today" (the project's own claim; I did not check it).
- Hyper-V in Windows Server is for "enterprise deployments with advanced features like live migration, high availability, and disaster recovery"; Hyper-V in Windows is "a lightweight solution suitable for development and testing scenarios" (Microsoft's words).
- Nutanix markets AHV as an alternative to VMware on its own page ("Your Future Free of VMware Begins With AHV"). That is a vendor's marketing, not evidence about anyone else's product.

How to choose in a home lab, plainly: a laptop you also use for other things, use a desktop hypervisor. A spare machine you want to keep running all the time, use Proxmox VE (or TrueNAS if storage is the main job). Use ESXi free only if you want to learn what companies run, and accept that it is limited and may change again.

## Networking: NAT, bridged, host-only

A VM has a virtual network card. The hypervisor decides what that card is connected to. Plain words, with VirtualBox's names (its manual, chapter 6, read 2026-10-31) and the others' equivalents:

| Mode | What the VM can reach | Who can reach the VM | Use in a lab |
|---|---|---|---|
| **NAT** | The internet and your network, outbound, through the hypervisor | Nobody from outside, unless you add a port forward | **The default.** VirtualBox's manual: the VM "acts much like a real computer that connects to the Internet through a router" and is "invisible and unreachable from the outside internet" without port forwarding |
| **Host-only** | The host and the other VMs on that network; nothing outside | The host and those VMs | Best for attack and defense labs. The VMs "cannot talk to the world outside the host" |
| **Internal** | Other VMs on the same named network | Those VMs, not even the host | Strongest separation; VirtualBox's term. Hyper-V's "private" switch is similar |
| **Bridged** | Your real network, as if it were another device plugged into your router | Anything on that network | Only for a VM you *want* on the network, such as a server you deliberately run. Never for anything hostile |

Hyper-V names its switch types **external**, **internal** and **private** (Microsoft's switch page); an external switch is bridged to a real network adapter, and the page warns that creating one "may disrupt your network connectivity". QEMU's default, with no option given, is "a completely user mode network stack", and the `hostfwd` option forwards a host port into the guest (QEMU networking documentation, read 2026-10-31). In libvirt the default virtual network is NAT (est.).

Two cautions. First, a NAT VM is not walled off from the host: VirtualBox's manual notes that a NAT VM "has access to the host's loopback interface and the network services running on it" through a special address. A service you run on your host and bind to loopback is therefore reachable from the guest. Second, host-only traffic sits on a software interface on the host, where "the traffic on the loopback interface on the host can be intercepted" (VirtualBox manual), which is what you want in a lab where you are the one watching.

**Why a lab defaults to NAT or host-only.** A guest on NAT can download updates and cannot be attacked from your home network. A guest on host-only cannot reach the internet or the rest of your house at all. A guest on a bridged network is a new device on your real network, with a real address, visible to your router, your phones and your other computers. For anything you do not trust, the first two are right and the third is wrong. [Networking basics](Networking-Basics-for-This-Project.md) and [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) explain the NAT idea itself.

## Snapshots: an undo button that is not a backup

A **snapshot** saves the state of a VM's disk (and, in some tools, its memory) at one moment, so you can return to it. The `qemu-img` tool puts it plainly: `snapshot` can create (`-c`), apply (`-a`, "revert disk to saved state"), delete (`-d`) and list (`-l`) snapshots of an image (QEMU documentation, read 2026-10-31). Hyper-V calls them **checkpoints**; Microsoft's page distinguishes standard and production checkpoints (read 2026-10-31). VirtualBox and VMware have their own snapshot managers (est.).

How to use them in a lab: take one after the clean install and updates, take one before every risky step, and name them so you remember. Roll back after any experiment that changes the guest.

What a snapshot is **not**: a backup. It usually lives in the same disk image or beside it, so a lost disk loses both; a long chain of snapshots slows the VM and eats space (est.). Copy the disk image somewhere else if you care about it ([Backups, recovery and patching](Backups-Recovery-and-Patching.md)).

## Sizing a host for a lab

Plan from the host down. These are rules of thumb (est.), not vendor figures, except where marked.

| Resource | Rule of thumb | Why |
|---|---|---|
| Memory | Leave the host at least 4 GB (or half, on a small machine); give each small Linux guest 1 to 2 GB, a Windows guest 4 GB or more | Memory is what runs out first. Microsoft's page asks for at least 4 GB on a Windows host to run Hyper-V |
| Processor | Give each guest 1 or 2 virtual CPUs; the total across the VMs that run at once should not exceed the host's thread count by much | More virtual CPUs than threads means the guests queue for the processor |
| Disk | A thin (growing) disk image: a 4 GB virtual disk started at 196 KiB in Exercise 3. Plan 10 to 30 GB per Linux guest and more for Windows; use an SSD | Images grow as they fill and never shrink on their own; snapshots add to it |
| Network | NAT is free. Host-only needs the hypervisor's network manager | |
| ISO files | Alpine's virtual ISO is 70,254,592 bytes; a desktop Linux or Windows ISO is several gigabytes | Keep them in one folder and delete the ones you are done with |

The host I used has 8 threads (`nproc`), so a lab of three one-CPU guests running together is comfortable; five is the edge.

## Nested virtualization

**Nested virtualization** is a hypervisor running inside a VM: a guest that is itself a host. You meet it when you run a VM lab inside a cloud VM, or run Hyper-V, KVM or Docker Desktop inside a VM you already have. The Linux kernel documentation defines a nested guest as "the ability to run a guest inside another guest" and has names for the levels (L0 for the real host, L1 for the guest hypervisor, L2 for the nested guest). On Intel hosts the module option `kvm_intel nested` controls it, enabled by default since kernel 4.20 (read 2026-10-31); on this machine `/sys/module/kvm_intel/parameters/nested` printed `Y`.

Caveats:

- The outer hypervisor must expose the processor's virtualization extensions to its guest. Microsoft says it does so only when nesting is enabled, and that "Virtualization applications other than Hyper-V aren't supported in Hyper-V virtual machines, and are likely to fail". Microsoft also says nested virtualization "isn't suitable for" failover clustering and performance sensitive applications (Microsoft's nested virtualization page, read 2026-10-31).
- It is slower, with two layers between your program and the hardware (est.).
- Many cloud providers do not offer it on every machine size, or at all (est.; check the provider's page before you plan a lab around it, and do not assume the droplet in this project's stages supports it).
- Memory settings can be restricted: Microsoft notes a VM running Hyper-V cannot change its memory while running.

If nested virtualization is not available, a guest can still start, slowly, under QEMU's software emulation (`-accel tcg`).

## The safety rule for malware and recon labs

A VM is a good place to analyze malware, run a vulnerable training app or practice recon. It is a barrier made of software, and software has bugs. Treat it as one layer.

1. **Isolate the network first.** Use host-only or internal networking, or no network card at all, for any hostile or vulnerable guest. Use NAT only when it needs the internet (to download a tool), and unplug it after.
2. **Snapshot a clean state first.** Take it before you open a sample or start a vulnerable service, and revert when you finish. Never reuse a guest that ran malware without reverting.
3. **Never bridge a hostile VM onto your home LAN.** A bridged guest is a real device on your network. Malware or a vulnerable service there can reach your other computers, your router and everything else on that network.
4. **Cut the bridges between host and guest.** Do not share folders, clipboard or drag and drop with the host, and do not pass through USB devices, for a guest you do not trust (est.; the names differ per tool, and they are conveniences the guest-additions or tools packages add). Move files in on a read-only disk image or a one-way transfer.
5. **Remember the NAT-to-loopback path.** A NAT guest can reach services you run on your host's loopback (VirtualBox's manual says so). Do not leave a database or admin page listening on loopback that you would not offer to the guest.
6. **Keep the hypervisor patched** and use a separate account with nothing important in it. Hypervisor escape bugs have been found and fixed in the past (est.; no specific case is cited here), so a patched host matters more than any setting.
7. **Only real, legal samples and only your own targets.** Malware samples come from research sources that allow them. Recon tools are used only against machines you own or have written permission to test ([Security tools basics](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md#authorization-and-scope-come-first)).
8. **Keep real data out.** No real credentials, no personal files. Delete the guest and its snapshots when you are done.

## Free path: a first VM with QEMU and a small Linux ISO

You need a Linux host with QEMU. On Debian-family systems that is the `qemu-system-x86` and `qemu-utils` packages (est. for the package names; the author had QEMU installed already). Cost: $0. The image is **Alpine Linux's "virtual" ISO**, built for virtual machines. It comes from the Alpine project, which lists a SHA-256 checksum for every image. The version changes every few weeks, so read the current name and checksum from the project's page rather than copying mine.

> **Throwaway means throwaway.** The only things this creates are a folder, one ISO and one disk image, all of which you delete at the end. Nothing here changes your network, installs a service or opens a port. The VM uses QEMU's default outbound-only networking.

If you would rather use a graphical tool, the same exercises work in VirtualBox on any host: create a VM, attach the ISO, leave the network on NAT, take a snapshot from the Machine menu. I did not run VirtualBox (est.).

### Exercise 1: can this computer run a VM?

1. **Predict.** Does your processor advertise virtualization support? Is your computer itself already a VM?
2. **Do.**

   ```bash
   lscpu | grep -i -E 'Virtualization|Hypervisor'
   ls -l /dev/kvm
   systemd-detect-virt
   nproc
   ```

   On Windows, `systeminfo` ends with a "Hyper-V Requirements" block (est.). On a Mac, `sysctl kern.hv_support` prints 1 when the hypervisor framework is available (est.). Neither was run.
3. **Check.** On the author's machine, `lscpu` printed `Virtualization: VT-x`, `/dev/kvm` existed as a character device owned by `root` and group `kvm`, `systemd-detect-virt` printed `none` (so not inside a VM), and `nproc` printed 8. If `lscpu` shows nothing, the feature may be off in the firmware settings. If `/dev/kvm` is missing, QEMU will fall back to software emulation (slow). If `systemd-detect-virt` names something (such as `kvm` or `microsoft`), you are already inside a VM, and nested virtualization is in play.
4. **Undo.** Nothing: all four commands only read.

### Exercise 2: download an ISO and verify its checksum

A **checksum** is a fingerprint of a file. If one byte differs, the fingerprint changes. Comparing yours with the one the project publishes catches a corrupted or tampered download ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)). Honest limit: if the checksum comes from the same web page as the file, an attacker who controls the page controls both; the check catches errors and a swapped mirror, and a signature check is stronger (est.).

1. **Predict.** If you change one byte of the ISO, will `sha256sum -c` say OK or FAILED?
2. **Do.** Make a folder, open [the Alpine downloads page](https://alpinelinux.org/downloads/), pick the **x86_64 "Virtual"** image, and copy the file name and the `sha256` value. Then download both. The names below are the ones current on the day I ran this; replace `3.24.3` and the checksum with what the page shows.

   ```bash
   mkdir -p ~/vmlab && cd ~/vmlab
   curl -sL -o alpine-virt-3.24.3-x86_64.iso https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/x86_64/alpine-virt-3.24.3-x86_64.iso
   curl -sL -o alpine-virt-3.24.3-x86_64.iso.sha256 https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/x86_64/alpine-virt-3.24.3-x86_64.iso.sha256
   cat alpine-virt-3.24.3-x86_64.iso.sha256
   sha256sum -c alpine-virt-3.24.3-x86_64.iso.sha256
   ```

   ```powershell
   Set-Location $HOME; New-Item -ItemType Directory -Force vmlab | Out-Null; Set-Location vmlab
   curl.exe -sL -o alpine-virt-3.24.3-x86_64.iso https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/x86_64/alpine-virt-3.24.3-x86_64.iso
   (Get-FileHash -Algorithm SHA256 .\alpine-virt-3.24.3-x86_64.iso).Hash
   ```

   In PowerShell, compare the printed hash with the one on Alpine's downloads page by eye (case does not matter). The PowerShell lines were not run (est.).
3. **Check.** On 2026-10-31 the file was 70,254,592 bytes, and the checksum file held `cdc1bc0efc64d8d611bf3733f54868172a545888dfd726f518bf279bcb0ff1af` followed by the file name; `sha256sum -c` printed `alpine-virt-3.24.3-x86_64.iso: OK` and exited 0. The release listing on Alpine's site gave the same hash for that file. If you see `FAILED`, delete the file and download again; do not boot an image that fails its check. A different version number gives a different hash, which is normal.
4. **Undo.** `rm -r ~/vmlab` at the end of the lab.

### Exercise 3: a virtual disk and a snapshot you can roll back

1. **Predict.** A new 4 GB virtual disk: how much space does the file take on your real disk? What does "apply" do to a snapshot?
2. **Do.**

   ```bash
   cd ~/vmlab
   qemu-img create -f qcow2 lab-disk.qcow2 4G
   qemu-img info lab-disk.qcow2
   qemu-img snapshot -c clean-start lab-disk.qcow2
   qemu-img snapshot -l lab-disk.qcow2
   qemu-img snapshot -a clean-start lab-disk.qcow2
   qemu-img snapshot -d clean-start lab-disk.qcow2
   qemu-img snapshot -l lab-disk.qcow2
   ```

3. **Check.** `qemu-img` printed `virtual size: 4 GiB (4294967296 bytes)` and `disk size: 196 KiB`: the image is **thin**, so the file is tiny until the guest writes to it (`qcow2` is QEMU's growing format). The snapshot list showed one line, `1 clean-start 0 B` with the time it was taken; apply returned exit 0 (rolling the disk back to that state), delete returned exit 0, and the last list was empty. Run this way, an offline image snapshot holds only the disk; on a running VM a full snapshot also needs memory state, and that is where the tool you use (virt-manager, VirtualBox) does the work for you (est.).
4. **Undo.** `rm lab-disk.qcow2` if you do not continue.

### Exercise 4: start the first VM (written from reading)

> **Not run: booting the guest.** I checked that QEMU accepts these options (it started with the display off and the CPU paused, and I stopped it three seconds later) and I did not boot the guest or open a window. A window opens on your desktop, which is why I left that to you.

1. **Predict.** The guest has a disk with nothing on it. What will it boot from, and what will it be able to reach on the network?
2. **Do.** The command boots the ISO in a window. `-accel kvm` uses the Linux hypervisor; if `/dev/kvm` was missing in Exercise 1, use `-accel tcg` instead. `-m 1024` is 1 GB of memory, `-smp 2` is two virtual CPUs, and `-nic user` is QEMU's default outbound-only network.

   ```bash
   cd ~/vmlab
   qemu-system-x86_64 -accel kvm -m 1024 -smp 2 \
     -cdrom alpine-virt-3.24.3-x86_64.iso -boot d \
     -drive file=lab-disk.qcow2,format=qcow2,if=virtio \
     -nic user,model=virtio-net-pci
   ```

   Alpine's live ISO should show a login prompt where `root` with no password works (est.; I did not boot it, so check the Alpine documentation for your version). Run `uname -a` and `ip addr` inside the guest. Close the window to power it off.
3. **Check.** `uname -a` should show Alpine's Linux kernel, not your host's. The guest should have one network address in a private range that is not on your home network, and it should be able to reach the internet and not be reachable from your other computers. That is NAT, working as designed.
4. **Undo.** Close the window. The ISO is read-only, so the guest changed nothing there. Delete `~/vmlab` when finished.

### Exercise 5: pick the network for each job (no commands)

1. **Predict.** For each job, write NAT, host-only, internal or bridged: (a) a Linux guest that needs `apt update`; (b) a deliberately vulnerable web app you will scan with a tool from your host; (c) two guests that must talk to each other and not to your host; (d) a malware sample you are going to open; (e) a small web server that your phone should reach.
2. **Do.** Check each against the table in [the networking section](#networking-nat-bridged-host-only).
3. **Check.** (a) NAT. (b) Host-only, so the app is not reachable from your network and your host can scan it. (c) Internal. (d) Host-only with the network unplugged, or no network card at all, after a clean snapshot. (e) Bridged, and the only one of the five where bridged is right; give the guest a firewall and patch it, and remember that a server on a bridged network is exposed to everyone on that network.
4. **Undo.** Nothing to undo.

## Build, break, detect, evade, defend

A small loop in the lab you just built. Local and throwaway; no real systems.

**Build.** The Alpine guest from Exercise 4 on NAT, after taking a snapshot of the clean disk.

**Break.** Inside the guest only, delete something important (`rm -rf /etc/apk` is safe in a throwaway live guest, est.) and notice that `apk` stops working. Revert the guest by closing the window and starting again, or by applying the snapshot to the disk. The point is that the damage stopped at the edge of the guest.

**Detect.** From the host, list what the hypervisor is doing: `ps -o pid,args -C qemu-system-x86_64` shows the process and its options, including the network option. If a command line shows a bridge or a tap device you did not mean, that is a finding. In a company, detection looks for unexpected VMs, hypervisors started on workstations and management interfaces open to a user network (est.; [Detection and monitoring](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) covers the tooling).

**Evade, in words only.** An intruder inside a guest looks for what it can reach: a bridged network, a shared folder, a clipboard, a USB device, a service on the host's loopback (the NAT path above) or a hypervisor bug. A careless lab owner hands over every one of those at once for convenience. This page shows no escape technique.

**Defend.** Host-only or internal networks for hostile guests; no shared folders or clipboard; a clean snapshot; a patched hypervisor; no real data in the guest; the guest deleted afterward. The [safety rule](#the-safety-rule-for-malware-and-recon-labs) is the list.

**Undo (the whole lab).** `rm -r ~/vmlab`, and make sure no `qemu-system-x86_64` process is left (`ps -C qemu-system-x86_64`).

### Flip the board

**The reviewer.** A teammate wants to analyze a suspicious file and writes: "I set up a VirtualBox VM on bridged networking so the sample can phone home and I can see where it goes, shared folders on so I can copy it in, and I will take a snapshot afterward." Find at least five problems.

<details>
<summary>What to find</summary>

1. Bridged networking puts a hostile program on the real network, where it can scan and attack every other device.
2. Shared folders connect the guest to the host's files in both directions.
3. The snapshot is taken afterward, so there is no clean state to return to; it should be taken first.
4. The sample is allowed out freely; observing where it goes is done with a controlled network (host-only with a logging machine, or a monitored lab), not by letting it out.
5. No statement of where the sample came from or whether the teammate may handle it.
6. The host's loopback services (a database, an admin page) would be reachable from a NAT guest, and the plan has not said what runs on the host.
7. No plan to delete the guest afterward.

</details>

**The auditor.** A manager says "we moved off VMware, so we do not need to patch the hypervisor anymore." Who patches the hypervisor in each of: Proxmox VE you installed, a cloud provider's VM, Hyper-V on a workstation? (You, the provider, and the workstation's owner or IT team, respectively; the hypervisor is software on someone's machine, and someone patches it.)

## Checkpoint

Without looking back: say what a hypervisor is and give one example each of type 1 and type 2; explain why KVM blurs the line; name what Workstation Player became and what the free ESXi cannot do; explain why a lab defaults to NAT or host-only and what bridged does to a hostile guest; say what a snapshot is and why it is not a backup; give the first three steps of the safety rule.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "My VM is slow, so the hypervisor is bad" | KVM is probably not in use, so it runs under software emulation | `ls -l /dev/kvm`; use `-accel kvm`; firmware setting |
| "VirtualBox fails after I turned on Hyper-V" | Both want the same processor features | Microsoft's note on third-party apps; turn the Hyper-V hypervisor off or use one tool |
| "Hyper-V is missing on my Windows" | It is not in Home editions | Edition in Settings; use VirtualBox |
| "I'll download VMware Workstation Player" | Player was discontinued as a separate product in May 2024 | Broadcom's May 2024 post; download Workstation Pro |
| "The free ESXi is for my small business" | Its notes say non-production, no support, 8 vCPUs per VM | The ESXi 8.0 U3e release notes |
| "Bridged is just better because the VM gets an address" | The VM becomes a device on your real network | Use NAT or host-only; bridge only what you mean to expose |
| "A snapshot is my backup" | It lives with the disk and can be lost with it | Copy the image elsewhere |
| "The ISO downloaded, so it is fine" | Downloads corrupt, and mirrors get swapped | `sha256sum -c`, from the project's page |
| "My Intel ISO will not boot on my new Mac" | The guest must match the Mac's architecture to run at speed | Download the Arm64 image |
| "NAT means the guest cannot touch my host" | It can reach services on the host's loopback | Read the NAT note in the VirtualBox manual |

## Claims register

Retrieved 2026-10-31 with read-only requests, unless stated. "Read" means I read the page text. Pages that need JavaScript were read through the data behind them or an archived copy, as stated.

| Claim | Source | Status |
|---|---|---|
| A hypervisor makes and runs VMs; Hyper-V is a type 1 hypervisor that runs directly on hardware, is included with Windows Server and Windows, and in Windows is for development and testing | [Microsoft: Hyper-V in Windows Server and Windows](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/overview) | Read |
| Hyper-V role needs Windows 10 or 11 Pro or Enterprise, SLAT, 4 GB; not on Home; third-party apps such as VMware Workstation and VirtualBox might not start VMs or run unreliably while Hyper-V runs | [Microsoft: Install Hyper-V](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/get-started/install-hyper-v) | Read |
| Xen is an open-source type-1 hypervisor, a Linux Foundation project; "powering the largest clouds" is the project's claim | [xenproject.org](https://xenproject.org/) (the site's Hypervisor page, under Projects) | Read. Cloud claim: project's own, not checked |
| Xen's repository is GPL version 2 only | [COPYING in the Xen repository](https://github.com/xen-project/xen/blob/master/COPYING) (read from a mirror copy; the project's own host blocked my request) | Read |
| Type 1 versus type 2 and the KVM remark ("not always clear"; kernel modules that effectively convert the host to type 1) | [Wikipedia: Hypervisor](https://en.wikipedia.org/wiki/Hypervisor) | Read (secondary source) |
| KVM is a loadable kernel module in mainline Linux | [linux-kvm.org](https://linux-kvm.org/page/Main_Page) | Read |
| QEMU is a machine emulator and virtualizer; works with KVM, Xen or Hypervisor.framework; has `qemu-img`; license GPL version 2 | [About QEMU](https://www.qemu.org/docs/master/about/index.html), [License](https://www.qemu.org/docs/master/about/license.html) | Read |
| libvirt manages KVM, QEMU, Xen and others; virt-manager is a desktop UI for libvirt targeting KVM | [libvirt.org](https://libvirt.org/), [virt-manager.org](https://virt-manager.org/) | Read |
| Apple's Virtualization framework: VMs on Apple silicon and Intel Macs, macOS or Linux guests, introduced macOS 11.0; emulates a machine of the same architecture as the Mac | [Apple developer documentation: Virtualization](https://developer.apple.com/documentation/virtualization), [VZVirtualMachine](https://developer.apple.com/documentation/virtualization/vzvirtualmachine) (read through the page data) | Read |
| Apple `container`: Linux containers as lightweight VMs on a Mac, Apple silicon, supported on macOS 26 | [apple/container README](https://github.com/apple/container) | Read |
| UTM is free and open source, built on QEMU, can also use Apple Virtualization | [mac.getutm.app](https://mac.getutm.app/) | Read |
| VirtualBox base package GPL version 3; Extension Pack under PUEL, fee for commercial use; 7.2.22 for Windows, macOS (Intel and Apple silicon), Linux, Solaris | [VirtualBox Licensing FAQ](https://www.virtualbox.org/wiki/Licensing_FAQ), [Downloads](https://www.virtualbox.org/wiki/Downloads) | Read |
| VirtualBox networking modes; NAT is the default and invisible from outside; NAT guest can reach host loopback; host-only traffic can be intercepted on the host | [VirtualBox manual, chapter 6](https://www.virtualbox.org/manual/ch06.html) | Read |
| Hyper-V virtual switch types external, internal, private | [Microsoft: virtual switch](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/get-started/create-a-virtual-switch-for-hyper-v-virtual-machines) | Read |
| QEMU default networking is a user mode stack; `hostfwd` forwards ports | [QEMU networking](https://www.qemu.org/docs/master/system/devices/net.html) | Read |
| `qemu-img snapshot` can list, create, apply and delete snapshots | [qemu-img](https://www.qemu.org/docs/master/tools/qemu-img.html) | Read; create, list, apply and delete run (Exercise 3) |
| Hyper-V checkpoints, standard and production | [Microsoft: checkpoints](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/manage/choose-between-standard-or-production-checkpoints-in-hyper-v) | Page read; details not exercised |
| Nested KVM definition, levels L0 to L2, enabled by default since kernel 4.20 | [Linux kernel docs: running nested guests](https://docs.kernel.org/virt/kvm/x86/running-nested-guests.html) | Read |
| Nested Hyper-V: needs exposed extensions, other virtualization apps unsupported inside, not for performance-sensitive loads | [Microsoft: nested virtualization](https://learn.microsoft.com/en-us/virtualization/hyper-v-on-windows/user-guide/nested-virtualization) | Read |
| Broadcom completed the VMware acquisition, $69 billion | [BBC News, 23 Nov 2023](https://www.bbc.com/news/business-67505114) | Read |
| Perpetual licensing ended; VCF and vSphere Foundation subscription-only; vSphere Hypervisor (free edition) among products no longer standalone | [VMware blog, end of availability of perpetual licensing](https://blogs.vmware.com/cloud-foundation/2024/01/22/vmware-end-of-availability-of-perpetual-licensing-and-saas-services/) | Read |
| May 2024: Pro products free for personal use, paid for commercial ($120 a year), Player products discontinued, Broadcom portal account | VMware Workstation blog post, 2024/05, [archived copy](https://web.archive.org/web/2024/https://blogs.vmware.com/workstation/2024/05/vmware-workstation-pro-now-available-free-for-personal-use.html) | Read (archive); live address redirects |
| 2024-11-11: Fusion and Workstation free for everyone | [VMware Cloud Foundation blog](https://blogs.vmware.com/cloud-foundation/2024/11/11/vmware-fusion-and-workstation-are-now-free-for-all-users/) | Read |
| Free users not entitled to Global Support Team support | [VMware Cloud Foundation blog, March 2025](https://blogs.vmware.com/cloud-foundation/2025/03/10/vmware-fusion-workstation-going-free-new-resources/) | Read |
| ESXi 8.0 Update 3e, 10 April 2025: free vSphere Hypervisor 8, non-production, no support, no vCenter, 8 vCPUs per VM | [ESXi 8.0 Update 3e release notes](https://techdocs.broadcom.com/us/en/vmware-cis/vsphere/vsphere/8-0/release-notes/esxi-update-and-patch-release-notes/vsphere-esxi-80u3e-release-notes.html) | Read |
| Workstation documentation versions 17.0, 25H2, 26H1 | [Workstation Pro 26H1 documentation](https://techdocs.broadcom.com/us/en/vmware-cis/desktop-hypervisors/workstation-pro/26H1.html) | Read. That it is a naming scheme: **est.** |
| Customer reports of cost increases, bundling, AT&T claim, Gartner quotes, survey, Broadcom's position | [Ars Technica, 31 Oct 2024](https://arstechnica.com/information-technology/2024/10/a-year-after-broadcoms-vmware-buy-customers-eye-exit-strategies/) | Read. Reported claims, not audited |
| Proxmox VE: KVM and LXC, AGPL version 3, subscription prices per socket, ESXi import | [Proxmox VE](https://www.proxmox.com/en/products/proxmox-virtual-environment/overview), [pricing](https://www.proxmox.com/en/products/proxmox-virtual-environment/pricing), [wiki](https://pve.proxmox.com/wiki/Main_Page) | Read. Prices will change |
| TrueNAS Community Edition free open core download, VMs, Enterprise appliances | [TrueNAS Community Edition](https://www.truenas.com/truenas-community-edition/) | Read |
| Nutanix AHV included with a Nutanix Cloud Infrastructure license, not standalone | [Nutanix AHV](https://www.nutanix.com/products/ahv) | Read (vendor page) |
| Alpine virtual ISO 3.24.3 for x86_64, 70,254,592 bytes, SHA-256 `cdc1bc0e...ff1af` | [Alpine release listing](https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/x86_64/latest-releases.yaml) | Read; checksum verified (Exercise 2) |
| Exercise outputs (CPU flag, `/dev/kvm`, nested `Y`, thin disk 196 KiB, snapshot list) | One run each on Linux with QEMU 10.0.13, 2026-10-31 | Observed; yours differ |
| "Much slower" emulation, firmware switch, snapshot chains, shared-folder and USB names, libvirt NAT default, Proxmox no-subscription for home use, hypervisor escapes, sizing numbers, Alpine's root login, PowerShell, macOS and Windows commands, VirtualBox and VMware snapshot managers | General knowledge | **est.** |

Not verified, plainly: booting the guest; any behavior on Windows or macOS; VirtualBox, VMware, Proxmox, TrueNAS, Xen or Hyper-V in use; whether a Broadcom account is still required for the Workstation download today; any VMware news after the pages above; how Proxmox treats a non-subscribed home-lab install; and everything marked est.

Next: [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md), then continue on the [Reading order](Reading-Order.md) page.
