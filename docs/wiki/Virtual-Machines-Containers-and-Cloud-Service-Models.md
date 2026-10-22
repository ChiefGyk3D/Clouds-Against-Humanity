# Virtual machines, containers and the cloud service models

Side page to the start-from-zero pages. Read it after [What is the cloud](What-Is-the-Cloud.md) (core step 2) and [Containers and Docker basics](Containers-and-Docker-Basics.md) (core step 7), if a virtual machine, a container and a "managed service" still blur together. It does not repeat the two pages it follows: it draws the stacks side by side, says what each one really isolates, and sorts everything on a map of who patches what. Next: [How money works in the cloud](How-Money-Works-in-the-Cloud.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the free local lab was run once on Linux with Podman; everything else was not run.** On **2026-10-22** the author ran the Bash commands of Exercises 2 to 6 on a Linux machine with Podman 5.4.2 (rootless), using images already on that machine, and the output shown is trimmed from those runs. **Not run:** the PowerShell and Windows equivalents (written from Microsoft's and the tools' documentation, marked **est.**), Docker itself (the commands are the same, but I ran Podman), the `apt` step of Exercise 3 (it needs the network), and the whole own-account path with a droplet (written from the `doctl` reference, never applied). Vendor statements were read on **2026-10-22** from the pages named in the claims register at the end; anything I could not read is marked **est.** Cost figures come only from this repository's price files, with their dates. Trust what your terminal prints over what this page says.

> **Prerequisites.** [What is the cloud](What-Is-the-Cloud.md) and [Containers and Docker basics](Containers-and-Docker-Basics.md), and a terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md) has a first look). [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) helps if `apt`, users and `uname` are new, and [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) explains the firewall the own-account path uses. The free path needs Docker or Podman on your laptop and nothing else. About two hours for the reading and the free lab (est.); the optional cloud path adds about 45 minutes (est.).

> **Where things listen.** Every container in the free path is published, if at all, to your own computer's loopback address (`127.0.0.1`), which no other machine can reach. Nothing here mounts the Docker socket, uses `--privileged`, or points at a machine you do not own. The one dangerous configuration on this page, the socket mount, is shown as text and read from a made-up file, never run.

## What you will be able to do

- Draw the stack for a virtual machine and for a container, and say what is shared in each.
- Say, without absolutes, what isolation each really gives, and name two ways it fails.
- Sort IaaS, PaaS and SaaS by who patches what, and place a load balancer, a managed database and Kubernetes on that map.
- State the shared responsibility model with a vendor's own words, and say which half a breach usually lives in.
- Explain why a container does not patch itself, and why patching the host does not update the images on it.
- Explain regions and availability zones, read a machine size, and find its price in this repository's price files.
- List what you need to rebuild a lost machine, and run a container as non-root, read-only, with no extra privileges and published to loopback only.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Virtual machine, hypervisor | [What is the cloud](What-Is-the-Cloud.md#a-virtual-machine-a-little-more-precisely) | What a hypervisor adds, and what a guest cannot see. |
| Container, image, registry | [Containers and Docker basics](Containers-and-Docker-Basics.md) | What a container's isolation is made of, and how it differs from a VM's. |
| Shared responsibility | [What is the cloud](What-Is-the-Cloud.md#who-is-responsible-for-what) (VM only); [Enterprise infrastructure differences](Enterprise-Infrastructure-Differences.md#shared-responsibility) (one paragraph) | How the line moves for a container platform, a database and a SaaS app. |
| Regions | [What is the cloud](What-Is-the-Cloud.md) | Availability zones, and why "region" and "zone" are not the same. |
| Sizes and prices | [How money works in the cloud](How-Money-Works-in-the-Cloud.md) and `docs/cost.md` | What a size name tells you, in plain terms. |

## Virtual machines

A **virtual machine (VM)** is a whole computer made of software: virtual processors, memory, disk and network card, running its own full operating system, including its own kernel. The kernel is the core of an operating system that talks to the hardware ([Glossary](Glossary.md)). A VM does not know it is not real.

The software that makes the pretend hardware is the **hypervisor**. NIST's guide to full virtualization describes it as the layer that "controls the flow of instructions between the guest OSs and the physical hardware" and partitions the machine's resources so that "each has access to only its own resources" (read 2026-10-22, [NIST SP 800-125](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-125.pdf)). The operating system inside a VM is called the **guest**.

```text
   One physical server                          One VM, as the guest sees it
 +-------------------------------+            +-------------------------+
 |  VM A        VM B       VM C  |            |  your programs          |
 | +------+   +------+   +------+|            |  your libraries         |
 | | apps |   | apps |   | apps ||            |  YOUR OS and kernel     |
 | | OS   |   | OS   |   | OS   ||            |  (virtual CPU, RAM,     |
 | |kernel|   |kernel|   |kernel||            |   disk, network card)   |
 | +------+   +------+   +------+|            +-------------------------+
 |  hypervisor (splits the box)  |
 |  physical CPU, RAM, disk, NIC |
 +-------------------------------+
```

Each VM has its own kernel, so it can run a different operating system from its neighbors, and a bug in one guest's kernel is, by design, a problem for that guest. A droplet, an EC2 instance and an Azure or Google Cloud virtual machine are all VMs. A VM takes tens of seconds or minutes to boot (est.), because a whole operating system starts.

DigitalOcean's pricing page makes the hypervisor visible: a powered-off bundled-plan droplet is still billed "because the compute resources stay reserved on the hypervisor" (read 2026-10-22). The hypervisor is where the reservation lives.

## Containers and images

A **container** is not a small VM. It is an ordinary process (or a few) on the host's kernel, wrapped so that it sees its own filesystem, its own process list, its own network and a limited share of CPU and memory. The Linux manual page says it plainly: a namespace "wraps a global system resource in an abstraction that makes it appear to the processes within the namespace that they have their own isolated instance of the global resource", and "one use of namespaces is to implement containers" ([namespaces(7)](https://man7.org/linux/man-pages/man7/namespaces.7.html), read 2026-10-22). Kubernetes' overview says containers "have relaxed isolation properties to share the Operating System (OS) among the applications" (read 2026-10-22).

Two kernel features do most of the work:

- A **namespace** changes what a process can see: its own process numbers, mounts, network and hostname.
- A **control group (cgroup)** limits what a process can use: memory, CPU, number of processes.

An **image** is the frozen filesystem a container starts from: the program, its libraries and a minimal slice of an operating system (the "userland": commands and libraries, but not a kernel). A **registry** stores images. A **tag** such as `ubuntu:24.04` is a human-readable name for one version of an image. A container is a running copy of an image; one image, many containers.

```text
   One host (a physical machine or a VM)

 +--------------+ +--------------+ +--------------+
 | container 1  | | container 2  | | container 3  |
 | app + libs   | | app + libs   | | app + libs   |
 | (own files,  | | (own files,  | | (own files,  |
 |  own PIDs)   | |  own PIDs)   | |  own PIDs)   |
 +--------------+ +--------------+ +--------------+
 |  container runtime (Docker, Podman, containerd) |
 |  ONE host kernel, shared by all three           |
 |  hardware, or a hypervisor's virtual hardware   |
 +-------------------------------------------------+
```

Because there is no second kernel and no boot, a container starts in well under a second (est.), and many fit on one machine. That is also why its isolation is a different kind of thing, which the next section sorts out.

On macOS and Windows the container tools quietly run a small Linux VM and put your containers inside it, because containers need a Linux kernel. So on a laptop you often have a container inside a VM inside your operating system.

## What isolation each really gives

Neither is a wall. Both are barriers of different strength, and both have failed in public.

| Question | Virtual machine | Container |
|---|---|---|
| What is shared with its neighbors? | The physical hardware, split by the hypervisor | The host's whole kernel |
| Does it have its own kernel? | Yes | No: it uses the host's |
| What does an attacker inside need to break? | The hypervisor (a smaller, narrower program), through virtual hardware | The shared kernel's interface (very large), or a mistake in how the container was started |
| Can it run a different operating system family? | Yes, within what the hypervisor supports | Only one that uses the host's kernel type (Linux containers need Linux) |
| Start time and weight | Slower, heavier (est.) | Faster, lighter (est.) |
| Typical use | A machine you log in to and keep | A packaged program you start and replace |

Honest summary: a VM boundary is generally considered stronger than a container boundary because the shared surface is smaller, and clouds put different customers in different VMs for that reason (est.; AWS's page below says it keeps tenants separated). A container boundary is good for separating your own programs from each other and for limiting accidents, and weaker than a VM against a determined attacker running hostile code.

Two ways the container boundary has failed, in words only:

- **A bug in the runtime.** CVE-2019-5736 let a process inside a container overwrite the host's `runc` program (the low-level piece that starts containers), obtaining root on the host ([NVD record](https://nvd.nist.gov/vuln/detail/CVE-2019-5736), read 2026-10-22). CVE-2024-21626, in the same program, leaked a file descriptor so that a new container process could end up with a working directory in the host's filesystem, "allowing for a container escape" ([NVD record](https://nvd.nist.gov/vuln/detail/CVE-2024-21626), read 2026-10-22). Both were fixed in later versions, which is the point: the fix is a patch you must apply.
- **A mistake in how it was started.** A container started with the host's Docker socket mounted, with `--privileged`, or with the host's root folder mounted is not isolated from the host at all. Docker's security page says "only trusted users should be allowed to control your Docker daemon" and describes how a container can be given the host's `/` as a folder and alter it "without any restriction" ([Docker Engine security](https://docs.docker.com/engine/security/), read 2026-10-22). The daemon's socket is the control channel for that daemon, so a container that can write to it can ask the daemon to start a container with the host's root folder mounted; that is root-equivalent control (the reasoning follows Docker's page; I did not run it, and you should not).

Docker's same page says containers are "by default, quite secure; especially if you run your processes as non-privileged users inside the container". Both halves are fair: the defaults are decent, and a single flag can undo them. A **rootless** runtime, which runs the daemon and containers as an ordinary user inside a user namespace, adds another layer ([Docker rootless mode](https://docs.docker.com/engine/security/rootless/), read 2026-10-22; Podman is rootless by default for ordinary users, est.).

## Containers do not patch themselves

This is the fact beginners miss, and the maintainer of this project confirmed it for this lesson:

> An image stays exactly as old as the tag you pulled, until you update it. A running container does not update itself, and patching the host operating system does not update the container images on the host.

Why: an image is a snapshot. Docker's best-practices page says "Docker images are immutable. Building an image is taking a snapshot of that image at that moment. That includes any base images, libraries, or other software you use in your build", and tells you to rebuild "regularly with updated dependencies" (read 2026-10-22). It also says tags are mutable: a publisher can move a tag such as `ubuntu:24.04` to a newer build "with new security patches", and you only get the new one when you pull or rebuild.

So there are three separate things to keep fresh, and they are patched in different places:

| Layer | Who updates it | How |
|---|---|---|
| The host's kernel and packages (or the VM's) | You | `apt upgrade` or `dnf upgrade` on the host, then reboot if the kernel changed |
| The image's libraries and base system | You, or a tool you run | Pull a newer tag (or rebuild from a newer base), then stop the old container and start a new one from the new image |
| Your own application and its dependencies | You, or a tool you run | Rebuild the image |

Exercise 3 shows this on your own machine: the container's `libc6` version is the image's, not the host's. In practice teams use a scanner to list the known-vulnerable packages inside each image, and an automated update tool (a scheduled rebuild, or a bot that opens a pull request when a base image changes). Which tool is a team choice; having one is not.

## IaaS, PaaS, SaaS and shared responsibility

NIST defines three **service models** ([NIST SP 800-145](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-145.pdf), read 2026-10-22), here in plainer words:

- **IaaS (infrastructure as a service).** You get "processing, storage, networks, and other fundamental computing resources" and can "deploy and run arbitrary software, which can include operating systems and applications". A droplet or an EC2 instance. You manage the operating system; the provider manages the hardware and the hypervisor.
- **PaaS (platform as a service).** You deploy "consumer-created or acquired applications" onto the provider's platform. The provider runs the operating system and runtime; you bring the code and its settings. A function platform, or a service that runs your container for you.
- **SaaS (software as a service).** You use "the provider's applications running on a cloud infrastructure", with at most "limited user-specific application configuration settings". Email, a ticketing tool, a chat service.

The **shared responsibility model** is the cloud providers' name for who secures which part. AWS states it as two halves: AWS is responsible for "protecting the infrastructure that runs all of the services offered in the AWS Cloud", and the customer's responsibility "will be determined by the AWS Cloud services that a customer selects". Its example: Amazon EC2 is categorized as IaaS, and customers who deploy an instance "are responsible for management of the guest operating system (including updates and security patches), any application software or utilities installed by the customer on the instances, and the configuration of the AWS-provided firewall (called a security group)" ([AWS shared responsibility model](https://aws.amazon.com/compliance/shared-responsibility-model/), read 2026-10-22). The line moves with the service.

Here is the map. "You" means the customer; a cell that says "shared" means both sides do something and you must read the vendor's page for where the line is.

| Layer | On-premises (you own it all) | IaaS (droplet, EC2) | PaaS (platform runs your code) | SaaS (hosted app) |
|---|---|---|---|---|
| Physical building, power, network | You | Provider | Provider | Provider |
| Hypervisor and hardware | You | Provider | Provider | Provider |
| Guest operating system and its patches | You | **You** | Provider | Provider |
| Runtime, libraries | You | **You** | Provider (runtime); you (your own libraries) | Provider |
| Your application code and its dependencies | You | **You** | **You** | Provider |
| Your data, who may log in, your settings | You | **You** | **You** | **You** |
| Network rules and firewall for your machine | You | **You** (the cloud firewall is a tool the provider gives you) | Shared | Provider; you only choose who is allowed in |

(The PaaS column varies by vendor; this is the typical split, and a particular service's page decides. est.) In this table the bottom row does not move: your data, your accounts and your settings are yours in every column. That is why the [shared responsibility paragraph](What-Is-the-Cloud.md#who-is-responsible-for-what) says almost every breach lives in the customer's half.

### Placing three things on the map

- **A managed database** (a service that runs the database engine for you). DigitalOcean describes its managed databases as clusters where you "avoid manual setup and maintenance" ([Managed Databases](https://docs.digitalocean.com/products/databases/), read 2026-10-22). The provider patches the engine and the operating system under it. You still own who can connect, the credentials, the firewall rule on it, and your backups strategy (check what the vendor includes; est.). It sits between PaaS and IaaS and is usually called a managed service.
- **A load balancer** ([Glossary](Glossary.md)). A managed load balancer is a provider-run reverse proxy: the provider keeps the software patched, you choose the rules, the certificate and what happens to a failed backend. The balancer's setting is yours; its software is theirs.
- **Kubernetes.** The Kubernetes overview calls it "a portable, extensible, open source platform for managing containerized workloads and services" (read 2026-10-22). It decides which machine runs which container and replaces failed ones. Whose job it is depends on how you get it. If you run it yourself on VMs, you patch the nodes and the control software (IaaS). If a provider runs the control part for you (a "managed Kubernetes" service), the provider patches that part and **you still patch the worker machines or choose their image and update the container images** unless the service takes the node updates too; how much it takes varies by vendor and setting (est., check the vendor page). Containers inside it are still images that do not patch themselves.

## Regions and availability zones

A **region** is a geographic area where a provider has datacenters, with a short code (`tor1`, `us-east-1`). Your machine and its private network live in one region.

An **availability zone (AZ)** is a separate location inside a region, so that one building's power or network failure does not take down everything. AWS says: "Each Region is designed to be isolated from the other Regions", an Availability Zone's name is its region code plus a letter (for example `us-east-1a`), and "by launching EC2 instances in multiple Availability Zones, you can protect your applications from the failure of a single location in the Region" ([AWS: Regions and Availability Zones](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html), read 2026-10-22).

Other providers use other words. DigitalOcean's regional page says it has "16 datacenters across 13 regions" (last verified by DigitalOcean 9 October 2026, read 2026-10-22), and talks of datacenters, not zones; it does not use the AWS term on that page. Azure and Google Cloud also have zones (est.; I did not read their pages for this lesson).

Why you care: a single machine in a single zone is a single point of failure; two machines in two zones can survive the loss of one building, and two regions the loss of a whole area, but only if the design supports it: state replicated to both places, health checks that route traffic away from the failed side, and a failover you have tested. Machines in two zones that share one database, one dependency or one bad deploy can still fail together. More places also means more complexity and often a second bill. Location also decides latency, which laws apply to the data, and which sizes are available ([cost.md](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) records a real case where a cheap size was missing in one region).

## Sizes, in plain terms

A machine **size** (DigitalOcean) or **instance type** (AWS) is a menu item that fixes how many virtual CPUs (vCPUs), how much memory and how much disk you get, and the price per hour or month. More of each costs more. A name such as `s-1vcpu-1gb` is a code you can read: the plain `s` family, 1 vCPU, 1 GB of memory.

What this repository records (the only figures on this page):

| Size | What it is | List price | Where it comes from |
|---|---|---|---|
| DigitalOcean `s-1vcpu-1gb` | 1 GiB memory, 25 GB disk, 1 TB transfer | $6 a month | `docs/cost.md` size table and `docs/cost-prices.json`, retrieved 2026-10-21 |
| DigitalOcean `s-1vcpu-2gb` | 2 GiB memory, 50 GB disk, 2 TB transfer | $12 a month | same |
| DigitalOcean `s-2vcpu-2gb` | 2 GiB memory, 60 GB disk, 3 TB transfer | $18 a month | same |
| AWS `t4g.nano` | (vCPU and memory not read) | $0.0042 an hour, about $3.07 a month at 730 hours | `docs/cost-prices/aws.json`, us-east-1, retrieved 2026-10-16 |
| AWS `t3.micro` | (vCPU and memory not read) | $0.0104 an hour, about $7.59 a month at 730 hours | same |

(The monthly AWS figures are the hourly price times 730, my arithmetic. The instance prices above are for the instance alone. The same file lists separate charges for a public IPv4 address ($0.005 an hour) and a gp3 disk ($0.08 per GB-month), which are not included in them, and its `not_priced` field lists what it does not price at all: data transfer, logging, snapshots and anything created outside OpenTofu. The vCPU and memory of the AWS types are on AWS's instance-types page, which I did not read for this lesson.)

Two ideas make sizes less mysterious. First, a **vCPU** is a share of a physical processor handed to your VM by the hypervisor; two VMs on one server may share cores (est.). Second, a size is not a promise about speed under load: some families are "burstable" and slow down when their credits run out, which is what the [AWS cost lesson](Provider-AWS-Cost-Lesson.md) covers for AWS.

## What you need to rebuild a lost machine

A machine will be lost sooner or later: a mistake, a failed disk, a compromise. The question is whether losing it is a nuisance or a disaster. The checklist, from the [disposable machine idea](Containers-and-Docker-Basics.md#state-the-thing-that-makes-containers-hard):

1. **The recipe for the machine itself**: the image or operating system version, the size, the network, the firewall. In this project that is [infrastructure as code](What-Is-Infrastructure-as-Code.md), so it is a file in git.
2. **The first-boot configuration**: users, keys, packages, services (`cloud-init` in this project, see [Droplet hardening](Droplet-Hardening.md)).
3. **The application**: a version-pinned image or package, and the settings it needs.
4. **The secrets**: from a secret store, not from the lost machine's disk ([Doppler and secrets](Doppler-and-Secrets.md)).
5. **The data**: kept somewhere else (a bucket, a volume, a database with backups), and **a restore you have actually tested**. A backup you have never restored is a hope.
6. **The way back in**: an account, a key and a procedure that do not depend on the lost machine.

If every item is written down and stored apart from the machine, the machine is "cattle, not a pet".

## Where this shows up in this project

- `modules/twingate-connector/main.tf` creates the one VM type this project builds (a droplet, IaaS), with an Ubuntu 24.04 image; the OS patching is therefore yours, and `unattended-upgrades` is installed by the first-boot file ([Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md#what-this-project-runs)).
- Stage 3 (designed, not built) puts containers on one droplet, so the image-freshness question above becomes real there ([Containers and Docker basics](Containers-and-Docker-Basics.md#pi-shaped-to-cloud-shaped)). It also moves timer jobs to DigitalOcean Functions, a PaaS-style service where the provider runs the OS and runtime ([Cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md)).
- The cost gate prices droplet sizes from `docs/cost-prices.json`, which is why the size names above matter.
- [Why the clouds differ](Why-the-Clouds-Differ.md) compares how the big three name and shape the same boxes, and [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) covers the firewall that is outside a VM.

## Free path: a lab on your own computer

You need **Docker** or **Podman** ([Docker Engine](https://docs.docker.com/engine/install/), [Podman](https://podman.io/docs/installation)). The commands below use `podman`; replace it with `docker` if that is what you installed (the flags are the same). The images are `docker.io/library/ubuntu:24.04` (also used by [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md)) and `docker.io/library/python:3.13-slim`, both official Docker Hub images (est. that those tags exist on the day you read this; the author's machine had them). The first run pulls each image, which needs internet access outbound and nothing inbound.

**Which track.** Bash is shown first and PowerShell second. On Windows run the container commands from PowerShell with Docker Desktop or Podman Desktop running (est.); the container itself is still Linux, so commands inside the quoted strings are Bash. Host-side checks that use Linux tools (`uname`, `ss`) have a PowerShell equivalent where one exists and are marked where not.

> **Throwaway means throwaway.** Every container below uses `--rm`, so it is deleted when it stops. The one folder mounted in (Exercise 5) is a small web folder you create, mounted read-only. No command uses `--privileged`, mounts a socket or the host's root folder, or publishes a port to any address except `127.0.0.1`.

### Exercise 1: fill in the responsibility table (no commands)

1. **Predict.** For each of these, write who patches the operating system, you or the provider: a droplet; a managed database; a container you run on your own droplet; a hosted ticketing tool; a function on a function platform.
2. **Do.** Read the [AWS shared responsibility page](https://aws.amazon.com/compliance/shared-responsibility-model/), the [NIST service model definitions](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-145.pdf) (pages 2 and 3) and, for the provider you use, the pricing or product page for one managed service. Fill in a copy of the map table above for that service, with the date you read it.
3. **Check.** Your answers should be: droplet, you; managed database, provider (but you own access and settings); container on your droplet, **you patch the droplet and you update the image, so two things**; hosted tool, provider; function, provider for the OS and runtime, you for your code and its libraries. If your reading of the vendor page differs, the vendor page wins; note the difference.
4. **Undo.** Nothing to undo.

### Exercise 2: one kernel, many containers

1. **Predict.** Will `uname -r` inside a container print the same kernel as on your host? Will the container see the host's processes?
2. **Do.**

   ```bash
   uname -r
   podman run --rm docker.io/library/ubuntu:24.04 sh -c 'uname -r; id; ps -e; readlink /proc/self/ns/pid'
   readlink /proc/self/ns/pid
   ```

   ```powershell
   [System.Environment]::OSVersion.VersionString
   podman run --rm docker.io/library/ubuntu:24.04 sh -c 'uname -r; id; ps -e; readlink /proc/self/ns/pid'
   ```

3. **Check.** On a Linux host the two `uname -r` lines match (the author's run printed the same version both times, `7.1.13+parrot7-amd64`). `id` shows `uid=0(root)`: you are root *inside* the container. `ps -e` lists only two or three processes, the container's own, while the host has hundreds. The two `/proc/self/ns/pid` values differ (`pid:[4026533563]` against `pid:[4026531836]` in the author's run; yours will be other numbers), which is the **namespace**: the same kernel, a different view. On macOS or Windows `uname -r` prints the kernel of the small Linux VM the tool runs, not your operating system's, and the PowerShell line on Windows prints a Windows version, which is the point: the container has its own userland but not its own kernel. Being "root" in a rootless container is not root on the host: a rootless runtime maps it to your ordinary user (the lab used Podman rootless; with a root-owned Docker daemon it is real host root with a restricted view, est.).
4. **Undo.** Nothing: `--rm` already removed the containers. `podman ps -a` should list nothing from this exercise.

### Exercise 3: how old is the image, and who patches it

1. **Predict.** Is the `libc6` package version inside `ubuntu:24.04` the same as the one on your host? If you patch your host tonight, will the image change?
2. **Do.** Read the image's age and version, then compare with the host:

   ```bash
   podman image inspect --format '{{.Created}}' docker.io/library/ubuntu:24.04
   podman image inspect --format '{{.Id}}' docker.io/library/ubuntu:24.04
   podman image inspect --format '{{.RepoDigests}}' docker.io/library/ubuntu:24.04
   podman run --rm docker.io/library/ubuntu:24.04 dpkg-query -W -f='${Version}\n' libc6
   dpkg-query -W -f='${Version}\n' libc6        # on a Debian-family host (est. elsewhere)
   ```

   ```powershell
   podman image inspect --format '{{.Created}}' docker.io/library/ubuntu:24.04
   podman image inspect --format '{{.Id}}' docker.io/library/ubuntu:24.04
   podman image inspect --format '{{.RepoDigests}}' docker.io/library/ubuntu:24.04
   podman run --rm docker.io/library/ubuntu:24.04 dpkg-query -W -f='${Version}\n' libc6
   ```

   Now ask the container how many updates it is missing. This fetches package lists from Ubuntu's mirrors (outbound only) and changes nothing outside the container (**est.**, not run for this page):

   ```bash
   podman run --rm docker.io/library/ubuntu:24.04 sh -c 'apt-get update -qq && apt list --upgradable 2>/dev/null | tail -n +2 | wc -l'
   ```

3. **Check.** `Created` is the date the *publisher built* the image, not the day you pulled it: in the author's run it was 2026-09-18 for a tag pulled earlier, a number that only grows as the tag ages unless you pull again. `Id` is a hash of the image's contents; the `RepoDigests` line is the permanent address of exactly that build (a **digest**, in the form `name@sha256:...`). The `libc6` versions differ (the author saw `2.39-0ubuntu8.9` in the container and `2.41-12+deb13u4` on a Debian host): the container's libraries come from the image, so patching the host leaves the image alone. A non-zero count from the `apt` command is the number of packages the image is behind (est.). To update, run `podman pull docker.io/library/ubuntu:24.04`: if the publisher moved the tag, `Id` changes and the old image is left on disk, unnamed, until you remove it. Containers already running keep using the old image until you stop and start them from the new one.
4. **Undo.** The `--rm` containers are gone. The pulled image stays on your disk; remove it with `podman rmi docker.io/library/ubuntu:24.04` when you are finished with all the exercises.

### Exercise 4: root and defaults against a hardened start

1. **Predict.** In the hardened run below, which of these will fail: writing a file in `/`; running as root; reaching the network? What will the capability line show?
2. **Do.**

   ```bash
   # The default start: root inside, a writable filesystem, a default set of capabilities.
   podman run --rm docker.io/library/ubuntu:24.04 sh -c 'id; grep -E "^Cap(Eff|Bnd)" /proc/self/status'

   # Hardened: non-root, read-only filesystem, no capabilities, no new privileges,
   # no network, and limits on memory and number of processes.
   podman run --rm --read-only --cap-drop=ALL --security-opt no-new-privileges \
     --user 65534:65534 --network none --memory 64m --pids-limit 64 \
     docker.io/library/ubuntu:24.04 \
     sh -c 'id; touch /x; echo touch_exit=$?; grep -E "^Cap(Eff|Bnd)" /proc/self/status'
   ```

   ```powershell
   podman run --rm docker.io/library/ubuntu:24.04 sh -c 'id; grep -E "^Cap(Eff|Bnd)" /proc/self/status'
   podman run --rm --read-only --cap-drop=ALL --security-opt no-new-privileges `
     --user 65534:65534 --network none --memory 64m --pids-limit 64 `
     docker.io/library/ubuntu:24.04 `
     sh -c 'id; touch /x; echo touch_exit=$?; grep -E "^Cap(Eff|Bnd)" /proc/self/status'
   ```

3. **Check.** The first run prints `uid=0(root)` and a non-zero capability set (`CapEff: 00000000800405fb` in the author's run). The second prints `uid=65534(nobody)`, then `touch: cannot touch '/x': Read-only file system` and `touch_exit=1`, then both capability lines as all zeros. The flags are documented in the [docker run reference](https://docs.docker.com/reference/cli/docker/container/run/) (`--read-only`, `--cap-drop`, `--security-opt`, `--user`, `--memory`, `--pids-limit`, read 2026-10-22; Podman's equivalents are in its [run reference](https://docs.podman.io/en/latest/markdown/podman-run.1.html), est. for the details). A program that needs to write somewhere gets a `--tmpfs` folder or a volume, on purpose, and nothing else.
4. **Undo.** Nothing: `--rm`.

### Exercise 5: publish a port to loopback only

1. **Predict.** If you publish with `-p 18080:8000`, which addresses on your computer can reach it? With `-p 127.0.0.1:18080:8000`?
2. **Do.** Build a web folder at run time, then serve it from a hardened container, published to loopback only. Docker's port-publishing page warns that publishing "is insecure by default" because the port "becomes available not only to the Docker host, but to the outside world as well", and that including `127.0.0.1` limits it to the host (read 2026-10-22). So the address is part of the command:

   ```bash
   mkdir -p vmlab/site && cd vmlab
   echo "hello from a container" > site/index.html
   podman run -d --rm --name vmlab-web --read-only --cap-drop=ALL \
     --security-opt no-new-privileges --user 65534:65534 --memory 64m --pids-limit 64 \
     -p 127.0.0.1:18080:8000 -v "$PWD/site:/site:ro" \
     docker.io/library/python:3.13-slim \
     python -m http.server 8000 --bind 0.0.0.0 --directory /site
   curl -s http://127.0.0.1:18080/
   podman port vmlab-web
   ss -ltn | grep 18080
   ```

   ```powershell
   New-Item -ItemType Directory -Force vmlab\site | Out-Null; Set-Location vmlab
   Set-Content site\index.html "hello from a container"
   podman run -d --rm --name vmlab-web --read-only --cap-drop=ALL `
     --security-opt no-new-privileges --user 65534:65534 --memory 64m --pids-limit 64 `
     -p 127.0.0.1:18080:8000 -v "${PWD}\site:/site:ro" `
     docker.io/library/python:3.13-slim `
     python -m http.server 8000 --bind 0.0.0.0 --directory /site
   curl.exe -s http://127.0.0.1:18080/
   podman port vmlab-web
   Get-NetTCPConnection -LocalPort 18080 -State Listen
   ```

   (`--bind 0.0.0.0` is the address *inside the container's own network*, where it must listen to be reachable through the port mapping; the host side is the `127.0.0.1` in `-p`. If your system uses SELinux and the folder is unreadable inside, add `:Z` after `ro`, est.)
3. **Check.** `curl` prints `hello from a container`; `podman port` prints `8000/tcp -> 127.0.0.1:18080`; `ss` shows the socket listening on `127.0.0.1:18080` and not on `0.0.0.0`. A machine on your network cannot reach that port. **Do not** try the wide form, `-p 18080:8000`, to see the difference: it would put the port on every address of your computer, which is the mistake this exercise warns about, and you have the `ss` output to prove the narrow form is narrow.
4. **Undo.**

   ```bash
   podman stop -t 1 vmlab-web
   cd .. && rm -rf vmlab
   ```

   ```powershell
   podman stop -t 1 vmlab-web
   Set-Location ..; Remove-Item -Recurse -Force vmlab
   ```

   `--rm` removes the container when it stops; `-t 1` skips the ten-second wait, because a plain Python server as the first process ignores the polite stop signal and the runtime has to force it.

### Exercise 6: read the dangerous mount without running it

A made-up `inspect` report, built here at run time, for two containers. One has the host's Docker socket mounted. You read it, you do not run anything that creates it.

1. **Predict.** Which of the two containers is the risky one, and what are the other problems you can spot from the fields alone?
2. **Do.** Create the sample and a small reader:

   ```bash
   cat > sample-inspect.json <<'EOF'
   [
     { "Name": "/sample-build-agent",
       "Config": { "User": "" },
       "HostConfig": { "Privileged": false, "ReadonlyRootfs": false },
       "Mounts": [
         { "Type": "bind", "Source": "/var/run/docker.sock", "Destination": "/var/run/docker.sock", "RW": true },
         { "Type": "bind", "Source": "/srv/sample/work", "Destination": "/work", "RW": true } ] },
     { "Name": "/sample-web",
       "Config": { "User": "65534:65534" },
       "HostConfig": { "Privileged": false, "ReadonlyRootfs": true },
       "Mounts": [
         { "Type": "bind", "Source": "/srv/sample/site", "Destination": "/site", "RW": false } ] }
   ]
   EOF
   cat > audit.py <<'EOF'
   import json, sys
   for c in json.load(sys.stdin):
       findings = []
       if c["Config"].get("User", "") in ("", "0", "root"):
           findings.append("runs as root")
       if c["HostConfig"].get("Privileged"):
           findings.append("PRIVILEGED")
       if not c["HostConfig"].get("ReadonlyRootfs"):
           findings.append("writable root filesystem")
       for m in c.get("Mounts", []):
           if m["Source"].endswith(".sock"):
               findings.append("mounts a socket: " + m["Source"])
       print(c["Name"].lstrip("/"), "->", "; ".join(findings) or "nothing flagged")
   EOF
   python3 -I audit.py < sample-inspect.json
   ```

   ```powershell
   @'
   [
     { "Name": "/sample-build-agent",
       "Config": { "User": "" },
       "HostConfig": { "Privileged": false, "ReadonlyRootfs": false },
       "Mounts": [
         { "Type": "bind", "Source": "/var/run/docker.sock", "Destination": "/var/run/docker.sock", "RW": true },
         { "Type": "bind", "Source": "/srv/sample/work", "Destination": "/work", "RW": true } ] },
     { "Name": "/sample-web",
       "Config": { "User": "65534:65534" },
       "HostConfig": { "Privileged": false, "ReadonlyRootfs": true },
       "Mounts": [
         { "Type": "bind", "Source": "/srv/sample/site", "Destination": "/site", "RW": false } ] }
   ]
   '@ | Set-Content sample-inspect.json
   foreach ($c in (Get-Content sample-inspect.json -Raw | ConvertFrom-Json)) {
     $f = @()
     if ($c.Config.User -in @('', '0', 'root')) { $f += 'runs as root' }
     if ($c.HostConfig.Privileged) { $f += 'PRIVILEGED' }
     if (-not $c.HostConfig.ReadonlyRootfs) { $f += 'writable root filesystem' }
     foreach ($m in $c.Mounts) { if ($m.Source -like '*.sock') { $f += "mounts a socket: $($m.Source)" } }
     $text = if ($f) { $f -join '; ' } else { 'nothing flagged' }
     "$($c.Name.TrimStart('/')) -> $text"
   }
   ```

3. **Check.** The Bash version prints `sample-build-agent -> runs as root; writable root filesystem; mounts a socket: /var/run/docker.sock` and `sample-web -> nothing flagged`. The socket line is the one that matters: a program that can talk to that socket can ask the daemon to start any container, including one with the host's root folder mounted, so the build agent is root-equivalent on its host, whatever its own user says. Now point the same reader at your real containers, read-only: `podman inspect NAME | python3 -I audit.py` (the author ran it on a plain test container and it printed `runs as root; writable root filesystem`). Your lab containers from Exercise 5 flag nothing.
4. **Undo.** `rm sample-inspect.json audit.py` (PowerShell: `Remove-Item sample-inspect.json`; the PowerShell version made only the JSON file).

## Optional: one small cloud VM (your own account)

This path puts the same ideas on a real hypervisor, in **your own** DigitalOcean account and on **your own** bill: the lessons are free forever, the cloud usage is yours. Read the cost and the teardown first.

> **Status of this path: written from the `doctl` documentation, never run.** The flags were checked against the `doctl` reference on 2026-10-22 (listed in the claims register) for names only. That a tag-based firewall created before the droplet attaches to it at creation is **est.**; check `doctl compute firewall get` before you rely on it.

### Cost and teardown (read first)

- **Cost.** One droplet of size `s-1vcpu-1gb`, listed at **$6 a month** in [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json) (retrieved 2026-10-21; see [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md)). DigitalOcean's pricing page (read 2026-10-22) says bundled-plan CPU droplets are billed per second with a minimum charge of 60 seconds or $0.01, capped at 672 hours a month, and that you are still billed for one that is powered off: "to end billing, destroy the Droplet". I did not read an hourly rate and give no per-hour figure. An hour or two is a small part of the monthly figure; leaving it running is the whole of the monthly figure. Firewalls and tags are free in this project's cost gate (est. for your account; check the billing page).
- **Never leave it running.** Set a calendar reminder for one hour from now.
- **Teardown** (listed again at the end with the proof):

  ```bash
  doctl compute droplet delete vm-lab --force
  doctl compute firewall list --format ID,Name        # note the vm-lab id
  doctl compute firewall delete FIREWALL_ID --force
  doctl compute tag delete vm-lab --force
  ```

- **Data rules.** No real data goes on this machine. Use a token as narrow as the [identity page](Identity-Secrets-and-Zero-Trust-Basics.md) and the [secrets page](Doppler-and-Secrets.md) teach, and revoke it afterwards if you made it for this.

### Steps

Placeholders: replace `203.0.113.7` with your own current public address (a documentation address, not yours); do not use this path from behind carrier-grade NAT ([CGNAT](Zero-Trust-at-Home-Two-Connectors-and-Failover.md#vpn-versus-ztna-under-real-residential-conditions)), where your visible address is shared. Create the **tag and firewall first**, so the droplet is protected from its first second (a new droplet with no firewall is open):

```bash
export REGION=tor1 SIZE=s-1vcpu-1gb IMAGE=ubuntu-24-04-x64 MY_IP=203.0.113.7
doctl compute ssh-key list --format ID,Name,FingerPrint      # pick your key; note its ID
export KEY_ID=YOUR_KEY_ID

doctl compute tag create vm-lab
doctl compute firewall create --name vm-lab --tag-names vm-lab \
  --inbound-rules "protocol:tcp,ports:22,address:${MY_IP}/32" \
  --outbound-rules "protocol:tcp,ports:80,address:0.0.0.0/0,address:::/0 protocol:tcp,ports:443,address:0.0.0.0/0,address:::/0 protocol:udp,ports:53,address:0.0.0.0/0,address:::/0 protocol:tcp,ports:53,address:0.0.0.0/0,address:::/0"
doctl compute droplet create vm-lab --region "$REGION" --size "$SIZE" --image "$IMAGE" \
  --ssh-keys "$KEY_ID" --tag-names vm-lab --wait
export VM_IP=$(doctl compute droplet get vm-lab --format PublicIPv4 --no-header)
ssh root@"$VM_IP"
```

In PowerShell write the variables as `$env:REGION = "tor1"` style assignments and `$VM_IP = (doctl compute droplet get vm-lab --format PublicIPv4 --no-header)`; the `doctl` flags are identical (est.). Inbound allows only SSH from your one address; outbound allows only web, DNS and nothing else, enough for package downloads. On the droplet:

```bash
systemd-detect-virt                 # names the hypervisor technology (est.: often kvm on droplets)
lscpu | grep -i -E 'hypervisor|virtualization'
uname -r; cat /etc/os-release | head -2
apt list --upgradable 2>/dev/null | tail -n +2 | wc -l      # updates waiting: your job, on IaaS
apt-get update -qq && apt-get install -y podman
podman run --rm docker.io/library/ubuntu:24.04 uname -r     # same kernel as the droplet's
```

**Check.** `systemd-detect-virt` prints a virtualization name rather than `none`, and `lscpu` shows a hypervisor vendor line: you are inside someone else's hypervisor. The container's `uname -r` matches the droplet's, not your laptop's: container, then VM, then hypervisor, three layers. The update count is the provider-versus-you line from the map made real: the droplet's operating system is yours to patch. Run Exercise 4's hardened command here as well; it behaves the same inside the VM.

### Prove it is gone

```bash
doctl compute droplet list
doctl compute firewall list
doctl compute tag list
```

All three should show nothing named `vm-lab`. Billing lags, so check the billing page again tomorrow (the habit in the [teardown checklist](Teardown-Checklist.md#3-prove-zero-billable-resources)). Remove the droplet's line from `~/.ssh/known_hosts` if you want a tidy file.

## Build, break, detect, evade, defend

A small loop in the local lab (add the cloud VM if you took it). Local and throwaway: no real systems, no real targets.

**Build.** Start the web container from Exercise 5 from a pinned image, hardened, published to loopback only. For a stricter pin, replace the tag with the digest you read in Exercise 3 (`name@sha256:...`): a tag can move, a digest names one build (digest behavior observed on Podman; the form is standard, est.).

**Break.** Show the soft spots, safely, with nothing exposed. Start a default container and look at what it has: `podman run --rm docker.io/library/ubuntu:24.04 sh -c 'id; grep -E "^Cap(Eff|Bnd)" /proc/self/status; touch /x && echo writable'`. It is root, holds a set of capabilities and can write to its filesystem. Then **read, do not run**, these three starts and write one sentence on what each hands over: `docker run -v /var/run/docker.sock:/var/run/docker.sock ...` (control of the daemon, so root-equivalent control of the host), `docker run --privileged ...` (nearly all of the isolation switched off; the [run reference](https://docs.docker.com/reference/cli/docker/container/run/) describes it as giving extended privileges), and `docker run -p 8080:80 ...` (the port is open to every address on the host, "the outside world" in Docker's words). Also note the age problem: an image pulled a year ago and never updated is a year behind.

**Detect.** Use the Exercise 6 reader on your real containers (`podman inspect NAME | python3 -I audit.py`, or `docker inspect`) to flag root users, writable filesystems, privileged mode and socket mounts. For published ports, `podman port NAME` and `ss -ltn` show the address each is bound to; anything bound to `0.0.0.0` that you meant to keep private is a finding. For age, `podman image inspect --format '{{.Created}}' IMAGE` is the publisher's build date. At scale a scanner lists vulnerable packages per image and a SIEM watches for containers starting with unexpected mounts ([Detection and monitoring](Detection-and-Monitoring-Wazuh-and-the-Landscape.md)); the detection you can do by hand today is the three commands above.

**Evade, in words only.** An intruder who lands in a container tries to find out whether it is a container (a process list of two programs and a tiny filesystem give it away), what it can see (a mounted socket, a writable host folder, a high capability set), and whether the runtime or kernel has a known bug, such as the two runc issues above, that turns a container into a host. A careless defender helps by running as root, mounting the socket, and never updating the image. This page shows no working escape against any system, and none is needed to understand the defense. **Defend** below is the list of what removes those handholds.

**Defend.**

- **Non-root, read-only, no extra privileges.** Exercise 4's flags: `--user`, `--read-only`, `--cap-drop=ALL`, `no-new-privileges`, plus memory and process limits. Add back only what the program proves it needs.
- **Never mount the container runtime's socket, never `--privileged`,** and treat control of the Docker daemon as root on the host. If a tool genuinely needs to start containers, run that tool in a disposable, isolated VM with nothing else on it, not on a machine you care about.
- **Publish narrowly.** Put `127.0.0.1` (or the private address) in `-p`, and keep a cloud firewall outside the machine, since the host firewall and Docker's own rules can disagree ([Containers and Docker basics](Containers-and-Docker-Basics.md#docker-and-firewalls-one-trap)).
- **Keep images fresh on a schedule.** Pin a version, rebuild or pull regularly, restart the container from the new image, and scan.
- **Patch the host and the VM too.** They are separate jobs from the image.
- **Rootless where you can,** so a break-out lands as an ordinary user.
- **Choose the service model on purpose.** If you do not want to patch an operating system, pick a service where the provider does, and spend the saved time on the part that stays yours in every column: data, accounts, settings.

**Undo (the whole lab).** Make sure nothing is running (`podman ps`), delete the files you made, and remove the images if you want the disk back (`podman rmi docker.io/library/ubuntu:24.04 docker.io/library/python:3.13-slim`). If you took the cloud path, walk the teardown above.

### Flip the board

You wrote the container; now do the other two jobs.

**The reviewer.** A teammate sends this to run a build helper and asks "is it fine to put on the shared build server?":

```text
docker run -d --restart always --privileged \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -p 8080:8080 --name helper example.com/team/helper:latest
```

Find at least five problems without running it.

<details>
<summary>What to find</summary>

1. `--privileged` removes most of the isolation, so the container is nearly the host.
2. The mounted socket gives the helper control of the daemon, which is root-equivalent on the server.
3. `-p 8080:8080` publishes to every address on the host, so anyone who can route to the server can reach the helper.
4. `:latest` is a moving tag: you cannot say what you are running, and it will not update itself either, so the version is whatever was pulled that day. Pin a version or a digest, and say how it is refreshed.
5. No `--user`, `--read-only`, `--cap-drop` or limits: it runs as root with a writable filesystem and no memory cap.
6. `--restart always` brings it back after a reboot with all of the above and no one looking.
7. The image comes from a name you cannot verify here, and there is no scan or update schedule.

</details>

**The auditor.** You are asked "who is responsible for patching the operating system under this service?" for four services: a droplet, a managed database, a container platform where the provider runs the nodes, and a hosted chat tool. For each, name the party, and then name one thing that is **still yours** in that service. (The answer from this page: droplet, you; database, provider, but access and settings are yours; container platform, provider for the nodes if the vendor page says so, but the images and your code are yours; chat tool, provider, but who is invited and what is shared are yours.) Write it in two sentences each, then check each against the vendor's own page and note the date.

**The attacker's cost.** If you were trying to escape a container and the defender had applied every item above, what would you be left with? (A kernel or runtime bug, and no handholds from configuration.) What does that tell you about why patching still matters even when the configuration is good?

## Checkpoint

Without looking back: draw the VM stack and the container stack and mark the kernel in each; say who patches the operating system on a droplet, on a managed database and on a hosted tool; say what happens to a container's libraries when you patch the host; give the difference between a region and an availability zone; list four items needed to rebuild a lost machine; name two flags that harden a container and one start option you must not use on a machine you care about.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "A container is a small VM" | It is a process on the host's kernel with its own view | `uname -r` inside and outside match (Exercise 2) |
| "Containers are secure because they are isolated" | They share a kernel; runtime bugs and options can break out | The two CVEs above; `inspect` for socket mounts and privileged mode |
| "Patching the server patched my containers" | Images are separate snapshots | `libc6` inside and outside differ (Exercise 3) |
| "It is `latest`, so it is up to date" | A tag points at what the publisher last built when you last pulled | `Created` date and `RepoDigests` |
| "It is in the cloud, so the provider patches it" | Only the layers the service model gives them | The map table, and the vendor's page |
| "`-p 8080:80` is local" | It is open to every address on the host | `podman port NAME`; write `127.0.0.1:8080:80` |
| "A stopped droplet costs nothing" | A powered-off bundled-plan droplet is still billed | Destroy it; read the billing page |
| "One zone is high availability" (or "two zones is") | One building is one point of failure; a second zone helps only with replicated state, health-aware routing and a tested failover | Two machines in two zones, shared dependencies removed, and a tested restore |

## Claims register

Retrieved 2026-10-22 with read-only requests, unless stated.

| Claim | Source | Status |
|---|---|---|
| A hypervisor controls instructions between guests and hardware and partitions resources so each guest has access to only its own | [NIST SP 800-125](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-125.pdf) | Read (executive summary) |
| IaaS, PaaS and SaaS definitions quoted | [NIST SP 800-145](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-145.pdf) | Read |
| AWS describes security of the cloud vs in the cloud, and EC2 as IaaS with the customer managing the guest OS, updates, software and security group | [AWS shared responsibility model](https://aws.amazon.com/compliance/shared-responsibility-model/) | Read |
| AWS Regions are isolated from each other; AZ names are the region code plus a letter; multiple AZs protect against the failure of a single location | [AWS: Regions and Availability Zones](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html) | Read |
| DigitalOcean: 16 datacenters across 13 regions; page last verified 9 Oct 2026; talks of datacenters and regions | [Regional availability](https://docs.digitalocean.com/platform/regional-availability/) | Read. That Azure and Google Cloud use zones: **est.**, not read |
| Bundled CPU droplets billed per second, 60 s or $0.01 minimum, 672-hour cap, still billed when powered off because resources stay reserved on the hypervisor | [Droplet pricing](https://docs.digitalocean.com/products/droplets/details/pricing/) | Read. No hourly rate read |
| Managed databases described as clusters where you avoid manual setup and maintenance | [DigitalOcean Managed Databases](https://docs.digitalocean.com/products/databases/) | Read (the intro). What a managed database includes for backups: **est.** |
| A namespace gives processes their own isolated instance of a global resource; one use is containers | [namespaces(7)](https://man7.org/linux/man-pages/man7/namespaces.7.html) | Read |
| Containers have relaxed isolation properties and share the OS; Kubernetes definition | [Kubernetes overview](https://kubernetes.io/docs/concepts/overview/) | Read. What a managed Kubernetes service patches: **est.**, varies by vendor |
| Docker daemon requires root unless rootless; only trusted users should control it; a container can be given the host root folder; containers are by default quite secure especially as non-root | [Docker Engine security](https://docs.docker.com/engine/security/) | Read |
| Rootless mode runs the daemon and containers in a user namespace as a non-root user | [Docker rootless mode](https://docs.docker.com/engine/security/rootless/) | Read |
| Images are immutable snapshots; rebuild regularly; tags are mutable and a publisher can move a tag to a newer build with security patches | [Docker build best practices](https://docs.docker.com/build/building/best-practices/) | Read |
| Containers do not patch themselves; host patching does not update container images | Confirmed by the project maintainer for this lesson; consistent with the Docker page above; shown in Exercise 3 | Maintainer-confirmed; observed |
| Publishing a port with no address is reachable from outside the host; including `127.0.0.1` limits it to the host | [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/) | Read |
| `--read-only`, `--cap-drop`, `--security-opt`, `--user`, `--memory`, `--pids-limit`, `--tmpfs`, `--privileged` exist as `docker run` options | [docker run reference](https://docs.docker.com/reference/cli/docker/container/run/) | Option names read. `no-new-privileges` appears on the page; its exact behavior: **est.** |
| CVE-2019-5736: runc overwrite leading to host root | [NVD](https://nvd.nist.gov/vuln/detail/CVE-2019-5736) | Read (published 2019-02-11) |
| CVE-2024-21626: runc file descriptor leak allowing container escape | [NVD](https://nvd.nist.gov/vuln/detail/CVE-2024-21626) | Read (published 2024-01-31) |
| `doctl` commands used: `compute tag create/delete/list`, `compute firewall create/delete/list`, `compute droplet create/get/delete/list`, `compute ssh-key list` | [doctl reference](https://docs.digitalocean.com/reference/doctl/reference/) | Names and the rule syntax checked against the firewall create page; never run |
| `s-1vcpu-1gb` $6, `s-1vcpu-2gb` $12, `s-2vcpu-2gb` $18 a month, with memory, disk and transfer | `docs/cost.md`, `docs/cost-prices.json` | Read in this repository (retrieved 2026-10-21) |
| AWS `t4g.nano` $0.0042 and `t3.micro` $0.0104 an hour, us-east-1, 730 hours a month; the file lists IPv4 ($0.005 an hour) and gp3 ($0.08 per GB-month) separately and says data transfer, logging, snapshots and non-OpenTofu resources are not priced | `docs/cost-prices/aws.json` | Read in this repository (retrieved 2026-10-16); monthly figures are my arithmetic |
| Exercise outputs (kernel and `libc6` versions, image date, capability values, loopback binding, audit lines) | One run each on Linux with Podman 5.4.2, 2026-10-22 | Observed; your values differ |
| VM boot time, container start time, "VM boundary generally considered stronger", `systemd-detect-virt` naming kvm, vCPU sharing, SELinux `:Z`, the rootless-versus-rootful root mapping, PowerShell and Windows behavior | General knowledge | **est.** |

Not verified, plainly: the whole PowerShell and Docker track; macOS and Windows behavior; the `apt` count in Exercise 3; the cloud path from start to finish; the vCPU and memory of the AWS types; Azure and Google Cloud zone terms; what any managed service patches beyond what its vendor page says.

Next: [How money works in the cloud](How-Money-Works-in-the-Cloud.md), then continue the core path on the [Reading order](Reading-Order.md) page.
