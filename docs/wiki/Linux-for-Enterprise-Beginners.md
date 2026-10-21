# Linux for enterprise beginners: the families, the survival skills, a safe lab

Side page to the start-from-zero pages. Read it before [Droplet hardening](Droplet-Hardening.md) if the Linux commands there look like another language, or alongside [Containers and Docker basics](Containers-and-Docker-Basics.md). Next: [Droplet hardening](Droplet-Hardening.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: vendor facts checked against vendor pages on 2026-10-22; commands not run by the author.** Each lifecycle date, default and maintainer below was read on **2026-10-22** from the page named next to it, which is a vendor page unless the text says otherwise. Where a vendor site blocked automated reads, lifecycle dates come from endoflife.date, a secondary community-maintained aggregator (also read 2026-10-22) and say so; confirm them on the vendor page before a real decision. Anything else I could not read is marked **est.** (estimate) and is a guess to check. No price appears anywhere on this page: prices change, so go to the vendor. The commands are standard and stable but I did not run them in a container for this page, so run the lab, and trust what your terminal prints over what this page says.

> **Prerequisites.** You can open a terminal and type a command ([Git from zero](Git-From-Zero.md) has a gentle first look) and you know what an SSH key is ([Networking basics](Networking-Basics-for-This-Project.md#ssh-in-one-paragraph)). Nothing about Linux itself. About three hours for the reading and the free lab.

## What you will be able to do

- Say what a Linux distribution is, and name the five families you will meet at work.
- Tell, from a command line, which family and version a machine is, and which package manager to reach for.
- Install, search, update and remove software, start and inspect a service, read a log, and read a file's permissions on any of them.
- Explain why you do not run as root, why you do not "just disable SELinux", and why a lifecycle end date is a security date.
- Say exactly what this project's two connector machines run.

## Why Linux, and what "a distro" is

Most servers, and most cloud workloads, run Linux. When you rent a small virtual machine from any cloud, the default choices are Linux images, and containers ([Containers and Docker basics](Containers-and-Docker-Basics.md)) are processes on a Linux kernel. If you work in IT or security you will log in to Linux machines; college courses often cover this in a few weeks of theory, so the day-to-day habits below are the part people learn on the job.

"Linux" strictly means the **kernel**: the program that talks to the hardware and decides which program gets the processor, memory and disk. A kernel alone is not something you can use. A **distribution** (distro) is a kernel plus everything around it, packaged and maintained by someone:

| Part of a distro | What it is | Example |
|---|---|---|
| Kernel | The core that talks to hardware | Linux |
| Userland | The commands and libraries you type and programs call | `ls`, `bash`, the C library |
| Package manager | The tool that installs and updates software from the distro's repositories | `dnf`, `apt`, `zypper` |
| Defaults | What is on or off out of the box | Firewall, SELinux or AppArmor, which services start |
| Support | Who patches it, for how long, and at what cost model | A vendor subscription or a community |

Two distros of the same **family** share the package format, most commands and a lot of configuration. Learn one family well and the next one in it often takes an afternoon. A different family can take a few days of "where did they put it". The commands in the survival section differ almost only in the package manager.

## The families you will meet

Who feeds whom:

- Fedora (fast upstream) feeds CentOS Stream, which sits just ahead of RHEL; Rocky Linux and AlmaLinux are rebuilt to be compatible with RHEL.
- Amazon Linux 2023 is AWS's own distro, based in part on Fedora.
- Debian feeds Ubuntu.
- SUSE Linux Enterprise Server stands on its own; openSUSE is the community side.

**The Red Hat family (RPM packages, `dnf`).** Red Hat Enterprise Linux (RHEL) is the one you will see most in large organizations, with a paid subscription from Red Hat. **Fedora** is the fast-moving upstream; **CentOS Stream** "tracks just ahead of RHEL", described by its own project as a midstream between Fedora and RHEL. After Red Hat announced the end of the old CentOS Linux on 2020-12-08, two free rebuilds appeared: **Rocky Linux** and **AlmaLinux**. AlmaLinux states it is "binary compatible with RHEL" since a July 2023 change of goal (software and kernel modules that work on RHEL should work on it). Rebuild or not, the reason to choose them is the same: the RHEL way of doing things without the RHEL subscription. **Oracle Linux** is a further RHEL-compatible distro from Oracle (compatibility claim **est.**; I could not read it).

**Amazon Linux (`dnf`).** AWS's own distro for its cloud. Amazon Linux 2023 (AL2023) is "based in part on the current version of the upstream Fedora Linux distribution" and uses DNF. Amazon Linux 2 reached end of support on 2026-06-30, so if you meet it, that is a finding, not a machine to learn.

**The Debian family (`apt`, `.deb` packages).** **Debian** is a community distro. **Ubuntu** is built on it by Canonical and is the most common default on cloud images, and the one this project uses. Ubuntu's Long Term Support (LTS) releases are the ones used in production.

**The SUSE family (RPM packages, `zypper`).** **SUSE Linux Enterprise Server** (SLES) is common in large SAP and mainframe-adjacent shops, particularly in Europe. **openSUSE** is the community side.

**Others you may see.** Alpine Linux appears inside containers because it is tiny: its own page says it is built on musl libc and busybox. Arch Linux and NixOS are loved by enthusiasts and rarely run production fleets at companies, so treat them as hobby and learning systems.

### Comparison table

Read left to right as "who stands behind it, and what will I type". Every cell has a source in the claims register at the bottom; cells marked **est.** are guesses I could not verify. Lifecycle cells tagged "aggregator" come from the secondary community site endoflife.date (see [where the dates come from](#where-the-dates-come-from-and-how-far-to-trust-them)), not the vendor; confirm on the vendor page before a real decision.

| Distro | Maintained by | Family and package manager | Init and firewall tool | MAC (mandatory access control) | Typical use | Support length and cost model |
|---|---|---|---|---|---|---|
| RHEL | Red Hat | Red Hat, `dnf` | systemd; firewalld (**est.**) | SELinux, enforcing by default (**est.**) | Enterprise servers, regulated shops | 10-year life cycle for 8, 9 and 10, up to 14 years with add-ons (Red Hat); RHEL 9 ends maintenance 2032-05-31 and RHEL 10 on 2035-05-31 (aggregator); paid subscription |
| Rocky Linux | Community project, founded after the 2020 CentOS announcement | Red Hat, `dnf` | systemd; firewalld (**est.**) | SELinux (**est.**) | Free RHEL-style servers | Rocky 9 ends 2032-05-31, Rocky 10 on 2035-05-31 (aggregator; matches RHEL); free |
| AlmaLinux | AlmaLinux OS Foundation | Red Hat, `dnf` | systemd; firewalld (**est.**) | SELinux (**est.**) | Free RHEL-compatible servers | AlmaLinux 10: active support to 31 May 2030, security to 31 May 2035 (vendor and aggregator agree); free, paid support from third parties |
| CentOS Stream | The CentOS Project | Red Hat, `dnf` | systemd; firewalld (**est.**) | SELinux (**est.**) | Development, ahead of RHEL | Stream 9 ends 2027-05-31, Stream 10 on 2030-05-31 (aggregator): about five years, far shorter than RHEL; free |
| Amazon Linux 2023 | AWS | Own, Fedora-based; `dnf` | systemd (**est.**); security groups outside the host | SELinux present, permissive by default | Workloads on AWS | Supported to 2029-06-30 (standard support ends 2027-06-30); no additional charge |
| Ubuntu LTS (24.04) | Canonical | Debian, `apt` | systemd (**est.**); `ufw`, disabled by default | AppArmor | Cloud images, general servers, this project | 24.04: security maintenance to May 2029, expanded to May 2034 with Ubuntu Pro; free base, paid Pro |
| Debian | Debian project (community) | Debian, `apt` | systemd (**est.**); nftables or none (**est.**) | AppArmor (**est.**) | Stable servers, container base images | Current stable is 13 "trixie" (2025-08-09); Debian 12 ends 2028-06-30 and 13 on 2030-06-30; community long-term extension beyond that (aggregator); free |
| SUSE Linux Enterprise Server | SUSE | SUSE, `zypper` | systemd (**est.**); firewalld since SLES 15 | AppArmor in 15; SELinux supported but off by default there; SLES 16 default **est.** SELinux | SAP, large enterprises | SLES 15 SP7 ends 2031-07-31, extended (LTSS) to 2034-07-31; 16.0 ends 2027-11-30 (aggregator; SUSE's page not readable); subscription |
| Oracle Linux | Oracle | Red Hat-compatible, `dnf` (**est.**) | systemd (**est.**) | SELinux (**est.**) | Oracle database shops | Oracle Linux 9 ends 2032-06-30, 10 on 2035-06-30 (aggregator); Oracle's own page not read |
| Alpine | Alpine project | Own, `apk` (**est.**) | OpenRC (**est.**); usually none in containers | None by default (**est.**) | Container base images | Releases each May and November, a branch is supported for a stated period |

Two reading tips. First, "free" and "paid" describe the **support relationship**, not the software: the software is open source in all of these. Second, the lifecycle column is the one that matters for security (see [Patching and lifecycle dates](#patching-and-why-lifecycle-dates-matter)).

## Survival skills, side by side

Commands that differ by family are shown for **dnf** (RHEL, Rocky, Alma, Amazon Linux, Fedora), **apt** (Ubuntu, Debian) and **zypper** (SUSE). Lines starting with `$` are what you type; `#` lines are explanations. Commands that change the system start with `sudo` (see [Users, groups and sudo](#users-groups-and-sudo)).

### Find out what you are on

Do this first on any machine you have not used before. Tips found online are written for one family.

```text
$ cat /etc/os-release       # distro name, version, and ID= / ID_LIKE= (the family)
$ uname -r                  # the kernel version
$ uname -m                  # x86_64 or aarch64 (arm), which matters for downloads
$ hostnamectl               # name, OS and kernel together
```

`ID_LIKE` is the family hint: Ubuntu says `debian`; Rocky and Alma say `rhel` and `fedora`. SUSE's documentation index lists an article on identifying SUSE products from this same file (read 2026-10-22).

### Packages

| Task | dnf (Red Hat family, Amazon Linux) | apt (Ubuntu, Debian) | zypper (SUSE) |
|---|---|---|---|
| Refresh the list of what exists | `sudo dnf makecache` | `sudo apt update` | `sudo zypper refresh` |
| Search | `dnf search nginx` | `apt search nginx` | `zypper search nginx` |
| Install | `sudo dnf install nginx` | `sudo apt install nginx` | `sudo zypper install nginx` |
| Update everything | `sudo dnf upgrade` | `sudo apt upgrade` | `sudo zypper update` |
| Remove | `sudo dnf remove nginx` | `sudo apt remove nginx` | `sudo zypper remove nginx` |
| Which package owns this file? | `dnf provides /usr/bin/dig` | `dpkg -S /usr/bin/dig` (installed) or `apt-file search` | `zypper search --provides /usr/bin/dig` |
| List what is installed | `rpm -qa` | `dpkg -l` | `rpm -qa` |

One trap: on Debian and Ubuntu `apt update` only refreshes the list; `apt upgrade` is what changes software. On Red Hat family machines `dnf upgrade` refreshes and changes in one step. On older RHEL-family machines you will also see the old `yum` command; on modern ones it is a link to `dnf`.

### Services with systemd

Almost every distro above uses **systemd**; the exception in this page's table is Alpine, which uses OpenRC (**est.**), and minimal container images usually run no init system at all. On a systemd machine, the commands below are the same across families. A **service** is a program that runs in the background; systemd starts, stops and watches them. On a non-systemd system, use that system's own service tool (on Alpine, `rc-service`, **est.**).

```text
$ systemctl status sshd          # is it running? last log lines (Ubuntu names it ssh)
$ sudo systemctl start sshd      # start now (does not survive a reboot)
$ sudo systemctl enable sshd     # start at every boot (does not start it now)
$ sudo systemctl enable --now sshd   # both
$ sudo systemctl restart sshd
$ systemctl list-units --type=service --state=failed
$ journalctl -u sshd --since "1 hour ago"    # that service's log
$ journalctl -p err -b           # errors since the last boot
```

The SSH service is called `sshd` on the Red Hat and SUSE families and `ssh` on Ubuntu and Debian (**est.**; check with `systemctl list-units | grep ssh`). That small difference is the sort of thing that breaks a copied snippet.

### Where things live

| Path | What is in it |
|---|---|
| `/etc` | Configuration. Text files, owned by root. You edit these. |
| `/var` | Things that change: logs (`/var/log`), caches, spools, databases. |
| `/usr` | Installed programs and libraries. The package manager owns it; do not hand-edit. |
| `/home` | Each person's files. |
| `/opt` | Add-on software installed outside the package manager. |
| `/proc` | Not real files: a live view of the kernel and running processes. `cat /proc/cpuinfo`. |
| `/tmp` | Scratch space anyone can write to. Cleared at reboot or on a timer. Do not keep anything you need in it. |

### Users, groups and sudo

Every program runs as a **user**. **root** (user ID 0) bypasses the ordinary file-permission checks, so a mistake or a stolen session as root can change almost anything. (Root is not unlimited: the mandatory access control layer below, and kernel capabilities, can still restrict it. That is a reason to keep them on, not a reason to log in as root.) The habit: log in as a normal user and use **sudo** to run one command with root's power. sudo logs who ran what, which is the point ([least privilege](Identity-Secrets-and-Zero-Trust-Basics.md)).

A **group** is a named set of users. Who may use sudo is decided by a group, and the name differs by family:

| Family | Admin group | Add a user to it |
|---|---|---|
| Red Hat family, Amazon Linux, SUSE (**est.** for SUSE) | `wheel` | `sudo usermod -aG wheel alice` |
| Ubuntu, Debian | `sudo` | `sudo usermod -aG sudo alice` |

`alice` is a made-up name. This is the single most copied-wrong line on the internet: `-aG` means add to the group; without `-a` you replace all the user's groups. This project's droplets use the `sudo` group because they run Ubuntu ([below](#what-this-project-runs)).

```text
$ id                       # who am I, which groups
$ sudo useradd -m -s /bin/bash alice     # create a user with a home folder
$ sudo passwd -l alice     # lock the password (key-only login)
$ sudo -l                  # what may I run with sudo?
```

Debian-family machines also ship `adduser`, a friendlier wrapper (**est.** that it is installed by default on minimal images).

### File permissions and ownership

`ls -l` shows who owns a file and what each party can do.

```text
$ ls -l /etc/ssh/sshd_config
-rw-r--r-- 1 root root 3269 Oct 22 09:00 /etc/ssh/sshd_config
```

Read the first ten characters as one type character plus three triples. `-` means a plain file (`d` is a directory). Then the owner `rw-`, the group `r--`, everyone else `r--`. `r` read, `w` write, `x` run (or enter a directory). The next two words are the owner (`root`) and the group (`root`).

Numbers are the same thing added up: read 4, write 2, execute 1. `rw-r--r--` is 6, 4, 4, so `644`; `0600` means "owner reads and writes; no other ordinary user can touch it" (root still can) (the connector's config file in this project uses it).

```text
$ chmod 600 secret.txt          # owner only
$ chmod u+x script.sh           # add execute for the owner
$ sudo chown alice:alice file   # change owner and group
```

**setuid** in a sentence: a program with the setuid bit (an `s` where the owner's `x` would be) runs with its owner's rights, not yours, which is how `sudo` itself works and why unexpected setuid files are a security finding.

### SSH keys, not passwords

SSH with a **key pair** replaces typing a password with proof that you hold a private key; the server stores only the public half in `~/.ssh/authorized_keys`. A key cannot be guessed the way a weak password can, and there is no password to type into a fake login page. Keys are not magic: a stolen private key works for the thief, and a user can be tricked into connecting to, or forwarding their key agent to, an attacker's machine. Protect the private key with a passphrase and keep it off shared machines. (What a key pair, a signature and a fingerprint are: [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#key-pairs-in-the-wild-ssh-keys-and-tls-certificates).) The server-side switches are `PasswordAuthentication no` and `PermitRootLogin no` in `/etc/ssh/sshd_config` or a drop-in file under `/etc/ssh/sshd_config.d/`. Run `sudo sshd -t` before restarting so a typo in the config is caught before it can lock you out.

This project goes further. By default the droplets have **no public inbound** at all: the baseline cloud firewall is deny-all inbound. The connector firewall adds one inbound rule, TCP 22 from droplets carrying the connector tag (connector to connector), and, only if a telemetry tag is set, the metrics ports from that tag. The optional host firewall admits TCP 22 from private address blocks, and the metrics port if telemetry sets one ([Droplet hardening](Droplet-Hardening.md#host-firewall-built-off-by-default)). None of those is open to the internet, and SSH is reached through the Twingate connector model, so the design does not expose an SSH port to the internet ([Twingate](Twingate.md), [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md)). The host-level settings are in [Droplet hardening](Droplet-Hardening.md#sshd-drop-in-etcsshsshd_configd99-cah-hardeningconf). The key idea is layers: a network control, then the host control.

### Firewalls

A host firewall filters packets on the machine itself, as a second wall behind a cloud firewall ([DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md)). Three names to untangle:

| Name | What it is | Where you see it |
|---|---|---|
| **nftables** | The kernel's packet filter (the engine) and its `nft` command. | Under everything modern |
| **firewalld** | A manager that organizes rules into zones and services; talks to nftables. Command `firewall-cmd`. | RHEL family; SUSE since SLES 15 |
| **ufw** | "Uncomplicated Firewall", a simple front end. Command `ufw`. Disabled until you enable it. | Ubuntu |

```text
$ sudo firewall-cmd --list-all              # firewalld: what is open
$ sudo firewall-cmd --permanent --add-service=https && sudo firewall-cmd --reload
$ sudo ufw status verbose                   # ufw
$ sudo nft list ruleset                     # the engine underneath, read-only
```

Before you enable `ufw`, allow SSH first (`sudo ufw allow ssh`) or you cut off your own session. Pick one manager per machine; two tools editing one ruleset is how rules silently disappear. This project's optional host firewall uses plain nftables on Ubuntu ([Droplet hardening: host firewall](Droplet-Hardening.md#host-firewall-built-off-by-default)).

### SELinux and AppArmor, in plain language

Normal permissions ask "who owns this file?". **Mandatory access control (MAC)** adds a second, stricter question set by the system, not by the file's owner: "is *this program* allowed to touch *this thing* at all?" If a web server is compromised, MAC can stop it reading your SSH keys even if file permissions would have allowed it.

- **SELinux** labels every file, process and port, and policy says which labels may talk. Used by the Red Hat family. AL2023 ships it permissive (denials are logged, not blocked); SLES 15 supports it but needs boot settings to turn it on.
- **AppArmor** gives each program a profile of paths it may use. Used by Ubuntu and, in SLES 15, SUSE.

```text
$ getenforce                   # Enforcing, Permissive or Disabled (SELinux)
$ sudo ausearch -m avc -ts recent    # recent SELinux denials (needs auditd)
$ sudo aa-status               # AppArmor: which profiles are loaded and enforcing
```

**Never "just disable it".** When something breaks and a forum says `setenforce 0`, that command is a diagnosis tool, not a fix: it proves SELinux is the cause. Then read the denial, and fix the label (`restorecon`), set the one boolean you need (`setsebool`) or add a narrow rule. Switching it off for good removes a layer that has stopped real attacks.

### Logs: where to look

| What | Where |
|---|---|
| Anything a systemd service printed | `journalctl -u <service>` |
| Errors since boot | `journalctl -p err -b` |
| Kernel messages | `journalctl -k` or `dmesg` |
| Logins and sudo | `/var/log/secure` (Red Hat family), `/var/log/auth.log` (Debian family), or `journalctl _COMM=sudo` |
| Everything else | `/var/log/` |

The two filenames for the login log are a classic difference between families. Log shipping to a SIEM is stage 2 in this project ([Detection and monitoring](Detection-and-Monitoring-Wazuh-and-the-Landscape.md)).

### Time sync

Clocks drift, and TLS, tokens and log correlation all fail when they do. The Red Hat family and recent Ubuntu use `chrony` (this project installs it explicitly, see [Droplet hardening](Droplet-Hardening.md#time)). Check it with `chronyc tracking` and `timedatectl` (look for "System clock synchronized: yes"). Some cloud images use `systemd-timesyncd` instead (**est.**).

### Patching, and why lifecycle dates matter

A distro is supported for a stated period. After the date, the vendor stops publishing security fixes for it, and new vulnerabilities are no longer promised a fix on that release (some vendors sell extended support, and a few fixes may still be backported, but you can no longer count on them). So an **end-of-life date is a security date**. Ask of every machine: what release is it, when does support end, who is going to move it before that date? Amazon Linux 2 reached its end on 2026-06-30; Ubuntu 22.04 LTS reaches the end of standard security maintenance in May 2027 (read on the Ubuntu release page).

**Two examples already in the past** (from the aggregator described below, read 2026-10-22, today being 2026-10-22): Debian 11 reached its end of support on **2026-08-31**, and SLES 15 SP6 reached its general-support end on **2025-12-31**. A machine still on either today gets no new security fixes from the vendor's normal channel. Older still: RHEL 7 ended maintenance on 2024-06-30.

#### Where the dates come from, and how far to trust them

The vendor's own lifecycle page is the authority; each is linked in the claims register. For a quick overview I also read [endoflife.date](https://endoflife.date/), a **secondary, community-maintained aggregator**, through its public read-only API on 2026-10-22 (for example `https://endoflife.date/api/rhel.json`). It carried the RHEL, SLES, Rocky, Debian, Oracle Linux and CentOS Stream dates in this page's table, which I could not read on the vendors' pages. For Amazon Linux 2023, AlmaLinux 10 and Ubuntu 24.04 it matched what I read from the vendors, with one small difference: for the end of Ubuntu 24.04's expanded security maintenance the aggregator says 2034-04-25 and Canonical's page says May 2034, so prefer Canonical's. **Confirm a date on the vendor's own page before relying on it for a real decision.**

Two distinctions come up in interviews. **Standard** support (security fixes plus bug fixes) is different from **extended** support (security fixes only, often paid). And "supported" depends on the product: Red Hat's own page lists a Full Support Phase, a Maintenance Support Phase and an Extended Life Phase.

Patching practice in one line each: test, stage, roll out in rings, keep a way back, and reboot when a kernel update needs it. Automatic security updates are reasonable for a small stateless fleet like this one and risky for a database server. See [Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md).

## What this project runs

I read the repository's modules for this section on 2026-10-22.

- **DigitalOcean droplets:** the image is `ubuntu-24-04-x64` (Ubuntu 24.04 LTS), set in `modules/twingate-connector/main.tf`.
- **AWS (the optional second cloud):** Ubuntu 24.04 LTS from the parameter Canonical publishes (`modules/aws/twingate-connector/main.tf`).
- **First boot:** `modules/twingate-bootstrap/cloud-init.yaml.tftpl` creates one admin user in the `sudo` group with a key and no password, disables root login and password SSH, installs `unattended-upgrades` and `chrony`, and the cloud firewall has no public inbound rules (see [SSH keys, not passwords](#ssh-keys-not-passwords) for the private and connector-tag exceptions; checked in `modules/firewall/` and `stacks/10-access/main.tf`).

So this project is a Debian-family, `apt`, systemd system. Ubuntu images ship `ufw` (disabled until enabled) and AppArmor as the image default, but this repository does not configure or verify AppArmor or `ufw`: it selects the image, installs `chrony` and `unattended-upgrades`, and adds the hardening in Droplet hardening. Check `sudo aa-status` on a real machine rather than assuming. Its hardening is explained line by line in [Droplet hardening](Droplet-Hardening.md); the cloud-init idea is in [What is infrastructure as code](What-Is-Infrastructure-as-Code.md). The same ideas apply on RHEL, Amazon Linux or SUSE, with the commands changed using the tables above.

## Hands-on, free path: two families in throwaway containers

You will run the same tasks on two families. A container shares a Linux kernel with its host (on a Linux computer, your own; on Docker Desktop or Podman for macOS or Windows, the kernel of the small Linux virtual machine those tools run), so it is a quick way to see the userland difference, but it is not a full machine (no systemd by default, no real firewall). That is why the service exercise says what to expect.

**Install a runtime.** Either [Podman](https://podman.io/docs/installation) or [Docker Engine](https://docs.docker.com/engine/install/). On Windows and macOS, the container tools run a small Linux virtual machine for you. If you would rather have a full virtual machine (needed for the service and firewall tasks), use a VM manager such as VirtualBox, Multipass or GNOME Boxes with an Ubuntu Server or AlmaLinux ISO; the exercises below work the same way inside a VM.

**Images, checked 2026-10-22 on Docker Hub (the official images exist, and each tag below existed):** `docker.io/library/ubuntu:24.04`, `docker.io/library/almalinux:9`, `docker.io/library/rockylinux:9`, `docker.io/library/amazonlinux:2023`. SUSE publishes its images on `registry.suse.com` (reachable 2026-10-22; I did not check a specific tag). Replace `podman` with `docker` if that is what you installed.

> **Throwaway means throwaway.** `--rm` deletes the container when you exit. Nothing you do inside survives, and as long as you do not mount a folder from your computer into it (these commands do not), nothing is written outside the container except package downloads.

### Exercise 1: identify, install, read permissions in two families

1. **Predict.** Write down, before running anything: which package manager does each image use, and what will `ID_LIKE` say?
2. **Do.** Open two terminals.

   ```text
   $ podman run --rm -it docker.io/library/ubuntu:24.04 bash
   $ podman run --rm -it docker.io/library/almalinux:9 bash
   ```

   In each: `cat /etc/os-release`, then install a small tool (`apt update && apt install -y dnsutils` in Ubuntu; `dnf install -y bind-utils` in Alma). In a container you are root, so no `sudo` is needed. Then run `dig` or `command -v dig`, and `ls -l /etc/shadow`.
3. **Check.** Ubuntu says `ID=ubuntu`, `ID_LIKE=debian`; Alma says `ID_LIKE="rhel centos fedora"` (**est.** for the exact wording; read yours). `/etc/shadow` should give no access to ordinary users. On Ubuntu it is typically `0640 root:shadow` (readable by root and the protected `shadow` group); on Alma it is typically mode `000`. Either is fine; read your own output.
4. **Undo.** Type `exit`. The `--rm` removes the container. Check with `podman ps -a`.

### Exercise 2: which package owns a file, and what is on the kernel

1. **Predict.** Will `uname -r` be the same in both containers? (Hint: containers share the kernel of their host, which on macOS or Windows is the runtime's Linux virtual machine.)
2. **Do.** In each container, find the owner of a file: `dnf provides /usr/bin/dig` in Alma; `dpkg -S /usr/bin/dig` in Ubuntu. Run `uname -r` in both and on your own computer.
3. **Check.** On Linux the kernel numbers match your host and each other; on macOS or Windows they match each other and the runtime's Linux VM, not your host OS. Either way, the container has its own userland but not its own kernel. This is the central fact of [Containers and Docker basics](Containers-and-Docker-Basics.md).
4. **Undo.** `exit` both.

### Exercise 3: a user, a group, and `sudo`

1. **Predict.** In a minimal image `sudo` may not be installed. What will `sudo -l` print?
2. **Do.** Install it (`apt update && apt install -y sudo` on Ubuntu, `dnf install -y sudo` on Alma). Create `alice` and give her a throwaway password: `useradd -m -s /bin/bash alice && passwd alice` (use a made-up password; the container is deleted afterwards). First run `su - alice -c 'sudo -l'` and note that she is refused, since she is in no admin group. Then add her to the admin group: `usermod -aG sudo alice` on Ubuntu or `usermod -aG wheel alice` on Alma. Switch to her with `su - alice`, then run `id` and `sudo -l` (it asks for her password).
3. **Check.** Before the group change, `sudo -l` refuses her; after it, `sudo -l` lists what she may run, and `id` shows the group. The group name differs by family: try the Ubuntu name on Alma (`usermod -aG sudo alice` fails there if no `sudo` group exists) to see the difference.
4. **Undo.** `exit`. The container goes away with the user.

### Exercise 4: read the end-of-life date of the OS you just ran

1. **Predict.** Will the AlmaLinux 9 container you used show an end date earlier or later than the Ubuntu 24.04 one? Write the two years down.
2. **Do.** On your host (not in the minimal container, which may lack `curl` and Python), read-only:

   ```text
   $ curl -sL https://endoflife.date/api/almalinux.json | python3 -m json.tool | head -30
   $ curl -sL https://endoflife.date/api/ubuntu.json | python3 -m json.tool | head -30
   ```

   Find the entry whose `cycle` matches your container's `VERSION_ID` from `/etc/os-release` (`9` and `24.04`). Read `eol` (end of support), `support` (end of the full-support phase), and `extendedSupport` where present.
3. **Check.** AlmaLinux 9 should show `eol` 2032-05-31 and Ubuntu 24.04 `eol` 2029-05-31 (as read on 2026-10-22; the data changes). Compare with the vendor pages in the claims register. If they disagree, the vendor wins.
4. **Undo.** Nothing to undo: the requests only read.

### Paid optional path: a small cloud instance of a family you pick

For a real machine with systemd, a firewall and SELinux or AppArmor, rent a small instance of one family. This project's own sizes and their cost basis are in `docs/cost.md` ([Cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md)); other providers' prices are on their own pricing pages, which I did not read, so I give no figure here. Use key-based login only, do not open port 22 to the world (restrict it to your own address, or use the Twingate model if you built this project), and write down the machine's creation time before you start.

**Teardown reminder.** A cloud machine bills until you destroy it, including a stopped one in some providers. Use the [Teardown checklist](Teardown-Checklist.md) when you finish, and confirm in the provider's console that the instance and its disk are gone.

## Build it, break it, detect it, defend it

A small loop in a throwaway Ubuntu or Alma container (or a VM, if you want the service steps).

**Build.** Create a service user and a file only it should read, in a folder others can enter (home folders are often closed to other users, which would hide the problem). In the container:

```text
$ useradd -m svcdemo
$ mkdir -p /srv/svcdemo && chmod 755 /srv/svcdemo
$ echo "demo-not-a-real-secret" > /srv/svcdemo/config.txt
$ chown svcdemo:svcdemo /srv/svcdemo/config.txt
$ chmod 600 /srv/svcdemo/config.txt
$ ls -l /srv/svcdemo/config.txt
```

The value is a made-up string; do not type a real secret into an exercise. In a VM, also write a tiny systemd service that runs as `svcdemo` (a unit file in `/etc/systemd/system/` with `User=svcdemo`), enable it, and confirm with `systemctl status`.

**Break.** Misconfigure it the way people do under pressure: `chmod 777 /srv/svcdemo/config.txt` (anyone can read and write). First create a second user `useradd -m bob` and try `su - bob -c 'cat /srv/svcdemo/config.txt'`: it is refused. Now run the chmod and repeat; it works, which is the problem.

**Detect.** `ls -l` shows `-rwxrwxrwx`. A one-line sweep finds every world-writable file in a folder: `find /srv /home -type f -perm -0002`. On a VM with journald, `journalctl -p warning -b` and `journalctl -u <service>` show what the service reported. This is the beginner version of what a SIEM does at scale ([Detection and monitoring](Detection-and-Monitoring-Wazuh-and-the-Landscape.md)).

**Defend.** Put it right and add layers: `chmod 600`, the least-privilege user, and the MAC layer left **on**. On a VM with SELinux or AppArmor, check `getenforce` or `sudo aa-status` before and after; it should still say Enforcing, or show profiles in enforce mode. If a legitimate step is blocked, read the denial and fix that one thing; do not turn the layer off. Close by listing what you would alert on in production: new world-writable files, new setuid files, changes in `/etc/sudoers`.

**Undo.** `exit` and let `--rm` clean up, or delete the VM or cloud instance and walk the teardown checklist.

## Claims register

All retrieved 2026-10-22 with read-only requests. "Not read" means the page was blocked or lacked the detail; the table uses **est.** for those.

| Claim | Source | Status |
|---|---|---|
| RHEL 8, 9 and 10 have a ten-year life cycle (Full and Maintenance Support) then Extended Life Phase; up to 14 years with ELCP and Long-Life add-ons | [Red Hat: Enterprise Linux life cycle](https://access.redhat.com/support/policy/updates/errata) | Read. Exact end dates per major version not read |
| RHEL 7, 8, 9, 10 dates: 10 `eol` 2035-05-31 (extended 2039-05-31), 9 `eol` 2032-05-31 (extended 2036-05-31), 8 `eol` 2029-05-31 (extended 2033-05-31), 7 `eol` 2024-06-30 | [endoflife.date: rhel](https://endoflife.date/api/rhel.json), secondary aggregator | Read 2026-10-22. Consistent with Red Hat's ten-year statement; vendor per-version dates not extracted from Red Hat's page |
| SLES: 15.7 `eol` 2031-07-31 (extended 2034-07-31), 15.6 `eol` 2025-12-31, 16.0 `eol` 2027-11-30 | [endoflife.date: sles](https://endoflife.date/api/sles.json), secondary aggregator | Read 2026-10-22. SUSE's own [lifecycle page](https://www.suse.com/lifecycle/) could not be read; confirm there |
| Rocky 9 `eol` 2032-05-31, 10 `eol` 2035-05-31; CentOS Stream 9 `eol` 2027-05-31, 10 `eol` 2030-05-31; Oracle Linux 9 `eol` 2032-06-30, 10 `eol` 2035-06-30 | [rocky-linux](https://endoflife.date/api/rocky-linux.json), [centos-stream](https://endoflife.date/api/centos-stream.json), [oracle-linux](https://endoflife.date/api/oracle-linux.json), secondary aggregator | Read 2026-10-22. Vendor pages: [Rocky](https://rockylinux.org/), [CentOS Stream](https://www.centos.org/centos-stream/), [Oracle Linux](https://docs.oracle.com/en/operating-systems/oracle-linux/); their dates not read there |
| Debian 11 `eol` 2026-08-31 (past), 12 `eol` 2028-06-30, 13 `eol` 2030-06-30 | [endoflife.date: debian](https://endoflife.date/api/debian.json), secondary aggregator | Read 2026-10-22. [Debian releases](https://www.debian.org/releases/) confirms 13 only (release date) |
| Cross-check: AL2023 `eol` 2029-06-30, AL2 `eol` 2026-06-30, Alma 10 `eol` 2035-05-31 and Alma 9 `eol` 2032-05-31, Ubuntu 24.04 `eol` 2029-05-31 | [amazon-linux](https://endoflife.date/api/amazon-linux.json), [almalinux](https://endoflife.date/api/almalinux.json), [ubuntu](https://endoflife.date/api/ubuntu.json) | Matches the vendor pages above. One difference: Ubuntu 24.04 extended 2034-04-25 (aggregator) vs May 2034 (Canonical); vendor preferred |
| Red Hat subscription tiers (Standard, Premium, ELCP) exist | Same page | Read. No prices given |
| RHEL SELinux enforcing, firewalld default | [Red Hat documentation](https://docs.redhat.com/) | Not read (blocked for automated reads); **est.** |
| AL2023 supported to 2029-06-30, standard support ends 2027-06-30, based in part on Fedora, DNF | [Amazon Linux 2023 release cadence](https://docs.aws.amazon.com/linux/al2023/ug/release-cadence.html) | Read |
| AL2023 "provided at no additional charge" | [What is Amazon Linux 2023](https://docs.aws.amazon.com/linux/al2023/ug/what-is-amazon-linux.html) | Read |
| AL2023 SELinux enabled, permissive by default | [SELinux on AL2023](https://docs.aws.amazon.com/linux/al2023/ug/selinux.html) | Read |
| Amazon Linux 2 reached end of support 2026-06-30 | [Amazon Linux 2 FAQs](https://aws.amazon.com/amazon-linux-2/faqs/) | Read |
| Ubuntu 24.04 LTS: standard security maintenance to May 2029; expanded to May 2034; 22.04 standard to May 2027 | [Ubuntu release cycle](https://ubuntu.com/about/release-cycle) | Read |
| Ubuntu Pro extends security maintenance (up to 15 years) | [Ubuntu ESM page](https://ubuntu.com/security/esm) | Read. Pro price and any free tier not read |
| Ubuntu default firewall tool is `ufw`, disabled by default; AppArmor is a Linux Security Module with per-program profiles | [Ubuntu Server firewalls](https://documentation.ubuntu.com/server/how-to/security/firewalls/), [Ubuntu Server AppArmor](https://documentation.ubuntu.com/server/how-to/security/apparmor/) | Read. That AppArmor is on by default in Ubuntu: **est.** (general knowledge) |
| AlmaLinux binary compatible with RHEL since July 2023; AlmaLinux 10 active support to 2030-05-31, security to 2035-05-31 (9: 2027-05-31 and 2032-05-31) | [AlmaLinux](https://almalinux.org/) and [AlmaLinux release notes](https://wiki.almalinux.org/release-notes/) | Read |
| Rocky Linux began after the 2020-12-08 CentOS announcement; releases 10.2, 9.8, 8.10 are out | [Rocky Linux about page](https://rockylinux.org/about) and [Rocky Linux](https://rockylinux.org/) | Read. Rocky's own support dates not read |
| CentOS Stream is a midstream between Fedora and RHEL | [CentOS Stream](https://www.centos.org/centos-stream/) | Read |
| Debian stable is 13 "trixie", released 2025-08-09 | [Debian releases](https://www.debian.org/releases/) | Read. Support length not read |
| Alpine uses musl libc and busybox; releases each May and November | [Alpine releases](https://alpinelinux.org/releases/) | Read |
| SLES 15 introduced firewalld as default; AppArmor chapter exists; SELinux supported, permissive by default, enabled via boot parameters | [SLES 15 SP7 firewall chapter](https://documentation.suse.com/sles/15-SP7/html/SLES-all/cha-security-firewall.html), [AppArmor](https://documentation.suse.com/sles/15-SP7/html/SLES-all/cha-apparmor-intro.html), [SELinux](https://documentation.suse.com/en-us/sles/15-SP7/html/SLES-all/cha-selinux.html) | Read. SUSE's own lifecycle page was not readable (dates come from the aggregator row above); the SLES 16 default MAC is **est.** |
| Docker Hub official images `ubuntu:24.04`, `almalinux:9`, `rockylinux:9`, `amazonlinux:2023` exist; SUSE publishes images at registry.suse.com | [Docker Hub: ubuntu](https://hub.docker.com/_/ubuntu), [almalinux](https://hub.docker.com/_/almalinux), [rockylinux](https://hub.docker.com/_/rockylinux), [amazonlinux](https://hub.docker.com/_/amazonlinux), [SUSE registry](https://registry.suse.com/) | Read |
| This project's images and first-boot settings | `modules/twingate-connector/main.tf`, `modules/aws/twingate-connector/main.tf`, `modules/twingate-bootstrap/cloud-init.yaml.tftpl` | Read in this repository |
| Everything else (commands, file layout, group names, `systemctl` behavior) | General Linux knowledge, standard across the named distros | Not re-verified per distro; run the lab |

Next: [Droplet hardening](Droplet-Hardening.md), step 14 of the core path on the [Reading order](Reading-Order.md) page.
