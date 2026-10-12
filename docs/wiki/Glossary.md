# Glossary

Every term the wiki uses, in plain language, with a pointer to the page that explains it properly. Terms a newcomer is likely to meet first are marked **(basics)**; the start-from-zero pages introduce them in order, beginning at [Start here if you are new](Start-Here-If-You-Are-New.md).

| Term | Meaning |
|---|---|
| **ACL** | Access control list: a list of who may reach what. In Twingate, a signed list of the resources a client (or connector) is allowed to reach. |
| **API** (basics) | Application programming interface. Here: the web interface a cloud provider exposes so programs can create and change resources. Everything the web console does is an API call underneath. [What is the cloud](What-Is-the-Cloud.md) |
| **API token** (basics) | A long random string that authenticates a program to an API. As powerful as a password, and usually less protected. [Identity, secrets and zero trust](Identity-Secrets-and-Zero-Trust-Basics.md) |
| **Apply** (basics) | The OpenTofu step that carries out a plan and changes real infrastructure. Always preceded by a plan a human has read. [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) |
| **Application service (appservice)** | A Matrix component the homeserver trusts to act for many users. The homeserver pushes events to it over HTTP, so it must be reachable from the homeserver. Bridges are application services. |
| **Authentication / authorization** (basics) | Who are you? versus What may you do? Two different questions; a system can get one right and the other wrong. [Identity, secrets and zero trust](Identity-Secrets-and-Zero-Trust-Basics.md) |
| **Branch** (basics) | A parallel line of history in git. Work happens on a branch and is merged into `main` through a pull request. [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) |
| **Branch protection** | A GitHub setting that stops direct pushes to `main`: changes need a pull request with passing checks. |
| **Bridge** | Software that relays messages between two chat networks, here Discord and Matrix. |
| **Bucket** (basics) | A container of files in object storage, reached over HTTPS with an access key. DigitalOcean's product is Spaces. |
| **CI** (basics) | Continuous integration: automated checks that run on every proposed change and report pass or fail. Here CI only tests; it never changes infrastructure. [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) |
| **CIDR** (basics) | A range of IP addresses written as a start address and a slash number, such as `10.78.0.0/24` (256 addresses). `0.0.0.0/0` means every address. [Networking basics](Networking-Basics-for-This-Project.md) |
| **ClickOps** | Building infrastructure by clicking in a web console. The thing infrastructure as code replaces. |
| **cloud-init** | The standard tool that configures a Linux cloud machine on its first boot from a text file (its user-data) handed over at creation. [Droplet hardening](Droplet-Hardening.md) |
| **Cloud firewall** (basics) | A firewall that runs in the provider's network, outside the machine, so the machine cannot turn it off. Attached here by tag. [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) |
| **Commit** (basics) | One recorded set of changes in git, with a message saying why. |
| **Connector** | Twingate's component inside your network. Makes outbound connections only and forwards authorized traffic to resources. Here, two small droplets. [Twingate](Twingate.md) |
| **Container** (basics) | An isolated process that sees its own filesystem and network but shares the host's kernel. Lighter than a virtual machine, less isolated. [Containers and Docker basics](Containers-and-Docker-Basics.md) |
| **Controller** | Twingate's hosted coordinator: configuration, sign-in, signed ACLs. Never carries traffic. |
| **Cost gate** | `scripts/cost_check.py`, which fails CI if planned spend exceeds the approved total or an unpriced paid resource appears. [How money works in the cloud](How-Money-Works-in-the-Cloud.md) |
| **Data source** | In OpenTofu, something that already exists and is looked up rather than created. The admin SSH key here. |
| **Default deny** (basics) | Block everything, then allow only what is needed. Fails safe: a forgotten rule breaks something instead of exposing something. |
| **Disposable** (basics) | A machine that holds nothing irreplaceable and can be destroyed and rebuilt from code at any time. "Stateless" means roughly the same. |
| **Doppler** | Hosted secrets manager. Every real secret in this project lives there. [Doppler and secrets](Doppler-and-Secrets.md) |
| **Drift** | Reality no longer matching the code because something was changed by hand. The next plan shows it. |
| **Droplet** (basics) | A DigitalOcean virtual machine. [What is the cloud](What-Is-the-Cloud.md) |
| **East-west / north-south** | Traffic between machines inside a network versus traffic between the network and the internet. Good cloud designs filter both. |
| **Functions (DigitalOcean)** | DigitalOcean's serverless product, the equivalent of AWS Lambda: a piece of code that runs on a schedule or a request and is billed by the GiB-second, with a free monthly allowance. Deployed with `doctl`, not OpenTofu. |
| **GYST** | git-your-ship-together, the author's library of reusable, hardened GitHub Actions workflows. |
| **HCL** (basics) | HashiCorp Configuration Language, the language Terraform and OpenTofu files are written in. Blocks, names and values. |
| **Hypervisor** | The software on a physical server that splits it into virtual machines. |
| **IaC** (basics) | Infrastructure as code: describing an environment in text files that a tool turns into real resources. [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) |
| **Idempotent** | Safe to run again: applying the same configuration twice changes nothing the second time. |
| **IdP** (basics) | Identity provider, the one service that actually checks who you are and enforces MFA, used by everything else to sign people in. |
| **Image** (basics) | A frozen filesystem with a program and its dependencies, from which containers are started. Published to a registry such as `ghcr.io`. |
| **Inbound / outbound** (basics) | From a machine's view: connections others open toward it, versus connections it opens toward others. This project's droplets allow zero inbound. [Networking basics](Networking-Basics-for-This-Project.md) |
| **IP address** (basics) | A device's number on a network. Private addresses (`10.x`, `172.16-31.x`, `192.168.x`) work only inside one network; public addresses are unique worldwide. |
| **Lateral movement** | An attacker moving from the first compromised system to others on the same network. |
| **Least privilege** (basics) | Give each person and program the smallest set of permissions that lets it do its job. |
| **Listening** (basics) | A program waiting for connections on a port. Only listening programs can be attacked over the network. |
| **MFA** (basics) | Multi-factor authentication: a second proof beyond the password, such as a code from an app or a hardware key. |
| **Module** | A reusable OpenTofu building block: a folder of HCL that does one thing and takes inputs. Never applied on its own here. [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) |
| **Object storage** (basics) | File storage reached over HTTPS, paid per gigabyte, with no operating system to manage. S3 is the common name; Spaces is DigitalOcean's. |
| **OIDC** | OpenID Connect. Here: short-lived identity tokens that let one service authenticate to another without a stored secret. |
| **OpenTofu** (basics) | Open-source, MPL-licensed fork of Terraform. Same language, same providers; `tofu` instead of `terraform`. [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) |
| **Plan** (basics) | The OpenTofu step that compares the code with reality and lists what would be created, changed or destroyed, without doing it. The thing a human reads before confirming. |
| **Port** (basics) | A number from 1 to 65535 that directs a packet to the right program on a machine. 22 is SSH, 443 is HTTPS. |
| **Portainer** | A web UI for a Docker host: stacks, containers, logs. Community Edition is free. It talks to Docker over the local socket, which is root on the host, so its UI is reached only through Twingate here. |
| **Proposed run** | A Spacelift plan for a pull request. Gets no credentials in this repo. |
| **Provider** (basics) | An OpenTofu plugin that knows how to talk to one service's API: DigitalOcean, Twingate. |
| **Public key / private key** (basics) | The two halves of a key pair. You publish one and keep the other; anything locked with one opens only with the other. SSH login here uses them instead of passwords. |
| **Pull request** (basics) | A proposal to merge a branch into `main`, showing the exact diff, with automated checks and human review. Every change here goes through one. [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) |
| **Region** (basics) | A provider's datacenter location, with a short code such as `tor1` (Toronto). A machine and a VPC live in exactly one. |
| **Registry** | Where container images are published and pulled from, such as `ghcr.io`. |
| **Relay** | Twingate component that joins a client and connector when a direct path is impossible, without terminating the encryption. |
| **Remote network (site)** | Twingate's name for a network that connectors serve, here `access-tor1`. |
| **Resource** | Two meanings. In OpenTofu, one thing the tool creates and tracks. In Twingate, one destination (address plus allowed ports) that a group can be granted. |
| **Runbook** | Written operating steps: how to build, verify, rotate and tear down. This project's are in `docs/stages/`. |
| **SASE / SSE** | Secure Access Service Edge / Security Service Edge. Vendor categories that bundle ZTNA with other network security services. |
| **Secret** (basics) | Any string that lets its holder do something: a password, a token, a private key. Lives in Doppler here, never in a file. |
| **Secrets manager** (basics) | A service whose only job is to hold secrets and hand them to programs at run time, by name, with logging and expiry. |
| **Serverless** (basics) | Running a small program on a schedule or request without a machine of your own; the provider runs it and bills the seconds. |
| **Shared responsibility** | The split between what the provider secures (hardware, hypervisor, their API) and what you secure (your firewall rules, updates, logins, tokens). |
| **Spacelift** | Hosted runner for infrastructure as code: plans, applies, holds state, waits for approval. [Spacelift](Spacelift.md) |
| **Spaces** | DigitalOcean's S3-compatible object storage. A bucket of files reached over HTTPS, with optional versioning that keeps earlier copies of every object. |
| **SSH** (basics) | The program and protocol for a command line on a remote Linux machine, on TCP port 22. Keys only here, never passwords. |
| **Stack** | A unit of infrastructure applied on its own with its own state. One Spacelift stack per `stacks/` directory. |
| **State** (basics) | OpenTofu's record of what it created and the real IDs. Lose it and the tool forgets what it built; it can contain secrets, so where it lives matters. |
| **Stateful firewall** | One that lets replies to allowed connections through automatically. New connections in either direction still need a rule. |
| **Supply chain** (basics) | Everything you pull in from others: actions, packages, images, installers. You are only as secure as all of it, so pin versions by hash and verify downloads. |
| **Tag (DigitalOcean)** | A label on a resource. Firewalls attach to tags, so a droplet is protected the moment it has one. |
| **TCP / UDP** (basics) | Two ways to send data to a port. TCP sets up a connection first (SSH, HTTPS); UDP just sends (DNS, time sync, Twingate peer-to-peer). |
| **Terraform** (basics) | The tool that made infrastructure as code mainstream. OpenTofu is its open-source fork; read "Terraform" here as OpenTofu. |
| **Threat model** | A written list of what is worth protecting, who might come for it, what stops them, and what is accepted. [Threat model](Threat-Model.md) |
| **Tracked run** | A Spacelift run on `main` that can apply after confirmation. The only kind that gets credentials. |
| **User-data** | The cloud-init configuration passed to a droplet at creation. Readable from the metadata endpoint. |
| **Virtual machine (VM)** (basics) | A slice of a physical server that behaves like a whole computer with its own operating system. A droplet is one. |
| **Volume** (basics) | A folder on the host mounted into a container so its data survives the container. |
| **VPC** (basics) | Virtual private cloud: a private network you define, that only your machines are on. [Networking basics](Networking-Basics-for-This-Project.md) |
| **VPN (remote access)** | A tunnel that places a device on a private network. The alternative this project chose not to use. [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) |
| **Zero trust** (basics) | A design rule: never grant access because of where a request comes from; grant it per request based on who is asking and what for. |
| **ZTNA** | Zero trust network access: per-user, per-resource access decided on every connection, with no implicit trust from network location. Twingate is the ZTNA product here. |
