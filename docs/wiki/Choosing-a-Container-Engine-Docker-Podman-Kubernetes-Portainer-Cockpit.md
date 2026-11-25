# Choosing a container engine: Docker, Podman and Kubernetes, with Portainer and Cockpit

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Prerequisites.** [Containers and Docker basics](Containers-and-Docker-Basics.md): images, containers, volumes, Compose and why the daemon is the thing to protect. [Kubernetes for beginners](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md) helps for the last third of the comparison, and is not repeated here. A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)) and some systemd vocabulary ([Cron, systemd timers and init scripts versus systemd](Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd.md)). The free exercise runs in a virtual machine you throw away, so [Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) is the side page if you do not have one. About 2 hours for the reading and the exercise (est.).

> **Status: unverified draft. No command on this page was run.** On **2026-11-25** I read the vendor pages named in the [claims register](#claims-register) and wrote the page from them. I did not install Docker, Podman, Portainer or Cockpit, and I started no container, so every command in the exercise is copied from those pages or written from them and has not been seen to work. The "why Docker" section is the maintainer's account of his own use; the comparison beside it cites vendor documentation and marks estimates. Anything I could not read on a vendor page is marked **est.** Trust what your terminal prints over what this page says.

> **Where this runs, and the rule.** Everything here is local and free. The exercise runs in a throwaway virtual machine on your own computer, binds every port to the loopback address, and deletes everything at the end. Nothing here creates a cloud account, a droplet or a bill. Do not expose a container engine's socket, a Portainer port or a Cockpit port to a network you do not control. Placeholder names only (`web`, `demo`).

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says](#what-the-wiki-already-says)
- [Three tools at three layers](#three-tools-at-three-layers)
- [Docker Engine: the daemon, and what it implies](#docker-engine-the-daemon-and-what-it-implies)
- [Podman: no daemon, rootless by design](#podman-no-daemon-rootless-by-design)
- [Compose, systemd and pods](#compose-systemd-and-pods)
- [GPU access](#gpu-access)
- [Where each is the right answer](#where-each-is-the-right-answer)
- [Why the author prefers Docker now](#why-the-author-prefers-docker-now)
- [Portainer: what it manages and how it is exposed](#portainer-what-it-manages-and-how-it-is-exposed)
- [Cockpit: a web console for the host](#cockpit-a-web-console-for-the-host)
- [Try it yourself: the same container under Docker and rootless Podman](#try-it-yourself-the-same-container-under-docker-and-rootless-podman)
- [Build, break, detect, evade, defend](#build-break-detect-evade-defend)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

## What you will be able to do

- Say what Docker Engine, Podman and Kubernetes each are, and that they sit at different layers rather than being three brands of the same thing.
- Explain the daemon versus daemonless difference and what it changes about who holds root.
- Say why membership of the `docker` group is root on the host, in Docker's own words.
- Name what rootless costs (subordinate ID ranges, networking helpers) for each engine.
- Run the same compose file under Docker and under Podman, and say what `podman compose` does and does not do.
- Say what Quadlet is, what `podman kube play` is, and what a Podman pod is.
- Say how GPU access differs between Docker (NVIDIA Container Toolkit runtime) and Podman (CDI).
- Say which engines Portainer manages, what its "Podman support" is limited to, and what exposing its ports or the Docker socket costs.
- Say what Cockpit is, how it is reached and who can log in, and why there is no first-party Docker page.
- Pick an engine for a given job and defend the choice with the tradeoffs.

## What the wiki already says

| Idea | Where it is today | What this page adds |
|---|---|---|
| A container is a process on the host's kernel; whoever controls the Docker daemon controls the host | [Containers and Docker basics](Containers-and-Docker-Basics.md#a-container-is-not-a-small-virtual-machine) | The same fact from the other side: what changes when there is no daemon, and what rootless Docker changes. |
| Compose, and Portainer as a window onto a Docker host | [Containers and Docker basics: Compose and Portainer](Containers-and-Docker-Basics.md#compose-and-portainer) | What Portainer supports besides Docker, and how its agents are exposed. |
| Kubernetes: pods, deployments, the control plane, when Compose is enough | [Kubernetes for beginners](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md) | Only the Podman angle: `podman kube play` and Podman's own pods. |
| Rootless: a break-out lands as an ordinary user | [Glossary](Glossary.md), [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md#what-isolation-each-really-gives) | The prerequisites and the limits, per engine. |
| The `-v /:/host` demonstration of "controls the daemon, controls the host" | [Containers and Docker basics: try it yourself](Containers-and-Docker-Basics.md#try-it-yourself) | Not repeated. The exercise below links to it. |

## Three tools at three layers

Docker and Podman run containers on a host. Kubernetes coordinates containers across hosts.

| Tool | What it is | Where it runs | Scope |
|---|---|---|---|
| **Docker Engine** | A daemon (`dockerd`) plus a command-line client. Builds, runs and networks containers on one host. | One machine | One host |
| **Podman** | A daemonless, Linux-native tool to "find, run, build, share and deploy applications" using OCI containers and images, with a command line "familiar to anyone who has used the Docker" CLI | One machine | One host |
| **Kubernetes** | A system that places containers across many machines and keeps the declared number running. It needs a container runtime underneath on every node. | A cluster | Many hosts |

The first two answer "run this container on this machine". Kubernetes answers "keep three of these running somewhere", and does not replace a container engine on the node (see [the pieces](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md#the-pieces-from-the-bottom-up)). So the real choice for a single host is Docker or Podman, and Kubernetes is a separate decision about whether one host is still enough. The Kubernetes lesson has [the conditions under which Compose on one droplet is the right answer](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md#when-compose-on-one-droplet-is-the-right-answer); this page does not repeat them.

Desktops add a wrinkle. Docker Engine runs directly on Linux, and on Windows and macOS Docker ships Docker Desktop, which "uses Docker Engine as one of its components" and, for commercial use inside larger organizations (more than 250 employees or more than $10 million USD in annual revenue), "requires a paid subscription" (both from Docker's install page). Podman has a native command line on macOS and Windows with a Linux guest it manages for you, a "Podman machine". Either way, on those systems your containers run in a Linux VM, not on the Windows or macOS kernel.

## Docker Engine: the daemon, and what it implies

Docker's engine is a long-running service. You type `docker run`, the client talks to the daemon over a Unix socket, and the daemon starts the container.

The security page says the daemon "requires `root` privileges unless you opt-in to" rootless mode, that "only trusted users should be allowed to control your Docker daemon", and that the REST API endpoint "can be still accessible from containers, and it can easily result in the privilege escalation". The post-install page is blunter: "The `docker` group grants root-level privileges to the user." It adds that by default the root user owns the Unix socket and other users reach it with `sudo`. Adding someone to the `docker` group gives them root-equivalent control without requiring `sudo` for each Docker command. This is the fact behind [the Docker lesson's warning](Containers-and-Docker-Basics.md#a-container-is-not-a-small-virtual-machine) about the socket,.

**Rootless Docker.** The rootless page: "Rootless mode lets you run the Docker daemon and containers as a non-root user." You need `newuidmap` and `newgidmap` on the host, `/etc/subuid` and `/etc/subgid` must hold at least 65,536 subordinate IDs for the user, and the setup is `dockerd-rootless-setuptool.sh install`, run as that user. I did not find a limitations list on that page (the fetch returned none), so **est.** that rootless Docker has the usual rootless limits (privileged ports, some network features, some storage drivers) and you should read the current page before depending on it.

**Published ports and the host firewall.** Docker's own packet-filtering page warns that for the common firewall front ends "packets are routed before the firewall rules can be applied, effectively ignoring your firewall configuration". The Docker lesson covers [the trap](Containers-and-Docker-Basics.md#docker-and-firewalls-one-trap). The habit that follows is to publish to a specific address (`-p 127.0.0.1:8080:80`) rather than to all addresses.

**Compose.** The Compose page: "Docker Compose is a tool for defining and running multi-container applications." You describe services in a YAML file and start them with one command. It is the same file the rest of this wiki already uses.

## Podman: no daemon, rootless by design

The Podman docs open with "Podman is a daemonless, open source, Linux native tool". There is no `dockerd` equivalent that must be running as root for you to run a container: the `podman` command starts the container itself, and "Containers under the control of Podman can either be run by root or by a non-privileged user". Podman "manages the entire container ecosystem which includes pods, containers, container images, and container volumes".

**What daemonless changes.** It removes the single long-running root service that every client talks to. Running Podman as root still gives its containers root-level access, but rootless operation is the normal Podman path; Docker makes rootless mode an explicit opt-in. What daemonless does not give you for free is anything the daemon did on your behalf, for example restarting containers after a reboot; Podman's answer to that is systemd (below). **est.** for the exact behavior of restart policies without a daemon: read the Podman page for `--restart` before relying on it.

**What rootless needs.** The rootless tutorial: "Rootless Podman requires the user running it to have a range of UIDs listed in the files" `/etc/subuid` and `/etc/subgid`, and "Root privileges are required to add or update entries within these files." It uses the `newuidmap` and `newgidmap` programs to map IDs, needs "A user-mode networking tool for unprivileged network namespaces", and warns that `ping` may not work from a non-privileged container. Storage defaults to `${XDG_DATA_HOME}/containers/storage` (`$HOME/.local/share` when unset). That is the same family of prerequisites rootless Docker lists, which is the point: rootless is a Linux feature built on user namespaces, and both engines depend on it.

**macOS and Windows.** A Linux guest does the work, as above.

## Compose, systemd and pods

**Compose compatibility.** `podman compose` is "a wrapper, not a compose implementation": it executes an external compose provider, `docker-compose` or `podman-compose`, and "sets up the environment in a way to let the compose provider communicate transparently with the local Podman socket". If `docker-compose` is installed it takes precedence; you override with `compose_providers` in `containers.conf` or the `PODMAN_COMPOSE_PROVIDER` environment variable. The socket side: `podman system service` offers "a compatibility layer offering support for the Docker v1.40 API" next to a Podman-native layer, supports systemd socket activation, and you point Docker API clients at it with `DOCKER_HOST`. The rootless default endpoint is `unix://$XDG_RUNTIME_DIR/podman/podman.sock` and the rootful one `unix:///run/podman/podman.sock`. The consequence is that compose files mostly work and Docker tools mostly connect, with the caveat in the name: it is a compatibility layer, so a feature that is specific to Docker's daemon may behave differently. **est.** which compose features differ; I did not read a compatibility list.

**systemd and Quadlet.** The Podman unit documentation: "Podman supports building and starting containers (and creating volumes) via systemd by using a systemd generator." You write small files with the extensions `.container`, `.volume`, `.network`, `.build`, `.pod`, `.kube` and `.artifact`, and the generator turns them into services that "can be started and managed with `systemctl` like any other systemd service". Rootful files go in `/etc/containers/systemd/`; rootless ones in `~/.config/containers/systemd/` (the page lists more directories). The older `podman generate systemd` command is marked deprecated: "We recommend using Quadlet files when running Podman containers or pods under systemd", with "no plans to remove the command". The effect is that the init system, not a container daemon, owns the lifecycle, which is [the same systemd you already use for timers and services](Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd.md).

**Pods and Kubernetes YAML.** Podman has pods ("a group of containers, called pods") as a built-in concept, the same word and the same idea as in [Kubernetes](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md#the-pieces-from-the-bottom-up) but run on one host. `podman kube play` "reads in a structured file of Kubernetes YAML" and starts it; the supported kinds are Pod, Deployment, PersistentVolumeClaim, ConfigMap, Secret, DaemonSet and Job, and `--down` tears down the pods a previous run created. That makes it a bridge: a Deployment file written for the Kubernetes lesson can be tried on one host without a cluster (see the exercise). It is not a cluster: nothing here schedules across machines. **est.** how much of a real Deployment's behavior (rolling updates, replica counts) `kube play` reproduces.

Docker has no built-in pod concept and no Kubernetes-YAML runner in the pages I read.

## GPU access

Both engines can pass an NVIDIA GPU to a container, through the NVIDIA Container Toolkit, by different routes.

- **Docker.** NVIDIA's install guide: install the GPU driver, then configure Docker with `sudo nvidia-ctk runtime configure --runtime=docker`, which updates the daemon configuration so Docker can use the NVIDIA runtime, and restart the daemon. Docker's Compose GPU page shows the compose form, `deploy.resources.reservations.devices` with `driver: nvidia`, `count: 1` and `capabilities: [gpu]`. For rootless Docker the guide has extra steps: run `nvidia-ctk` against `$HOME/.config/docker/daemon.json`, restart with `systemctl --user`, and set `nvidia-container-cli.no-cgroups` in `/etc/nvidia-container-runtime/config.toml`. The `--gpus` flag on `docker run` is the usual form; **est.**, because Docker's own GPU page was not readable when I tried it (the page I reached is a pointer to it).
- **Podman.** "For Podman, NVIDIA recommends using CDI for accessing NVIDIA devices in containers." CDI, the Container Device Interface, is "an open specification for container runtimes" for describing device access. You generate a spec with `sudo nvidia-ctk cdi generate --output=/var/run/cdi/nvidia.yaml`, and the example is `podman run --rm --device nvidia.com/gpu=all --security-opt=label=disable ubuntu nvidia-smi -L`.

The pattern: Docker modifies the daemon's runtime configuration once, and then containers ask for a GPU; Podman, having no daemon, reads a device description file and the container asks for a named device. CDI is not Podman-only (the spec is for "container runtimes"), which is why it is the more portable idea; **est.** how far Docker's own support for CDI goes, since I did not read it. Either way the driver on the host is the prerequisite, and a GPU shared with a container is a shared kernel driver, so it lowers the isolation the [containers lesson](Containers-and-Docker-Basics.md#a-container-is-not-a-small-virtual-machine) describes.

## Where each is the right answer

| Situation | Reasonable choice | Why |
|---|---|---|
| One droplet or one server, a handful of services, compose files already written | Docker Engine with Compose | It is the engine the wiki's [stage 3 design](Containers-and-Docker-Basics.md#where-this-shows-up-in-the-repo) installs, and the file format is the one everything documents. |
| A Linux host where services should be managed by the init system, with no root daemon | Podman rootless with Quadlet | systemd owns start order and restarts; no always-on root service. |
| A workstation or laptop on Linux, a learner who wants the unprivileged default | Podman | Rootless is the ordinary mode. |
| A distribution where Podman is the supported engine | Podman | **est.** which ones; check your distribution's docs. |
| A team that needs scaling, several hosts, declarative rollouts | Kubernetes | See the [Kubernetes lesson](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md#when-compose-on-one-droplet-is-the-right-answer). |
| Tools that speak the Docker API (a UI, CI runner, build tool) | Docker, or Podman's socket | Podman serves a Docker-compatible API, with the caveat above. |
| A host shared by people you do not fully trust | Neither is the answer alone | Containers share a kernel. A virtual machine per tenant is the boundary ([VMs, containers and service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md#what-isolation-each-really-gives)). |

## Why the author prefers Docker now

I prefer Docker now because it means less translation between this project's documentation, its Compose files, Portainer and the commands I type.

Compose files, Portainer and most project documentation assume Docker, so with Podman I do more translating. The page's evidence points the same way: `podman compose` is "a wrapper, not a compose implementation", and Portainer reaches Podman only through the Docker-compatible API.

Rootless Podman also gave me friction: the subuid and subgid setup, rootless networking and port limits, and registry login quirks cost me time. The subordinate ID ranges and the user-mode networking tool are prerequisites on the Podman rootless page above, and rootless Docker lists the same family of them.

GPU containers were easier on Docker. For GPU work like FrankenLLM, the NVIDIA Container Toolkit path on Docker was simpler for me than Podman's CDI route. The [GPU section](#gpu-access) shows the difference: one daemon setting for Docker, a generated device spec for Podman.

And I want one engine across machines: the same commands and the same behavior on every host and in CI, not two engines to keep in my head.

I would still choose Podman for a Linux host where an always-on root daemon is unacceptable, especially when Quadlet should hand container lifecycle management to systemd. These are my reasons from my own use, not a benchmark.

The table that follows compares where the two engines' pages say something different. Each row is either read from a vendor page (cited in the register) or marked **est.**


| Area | Docker behavior and support | Podman behavior and support |
|---|---|---|
| Daemon | One service that owns everything, and one place to look at (`docker info`). | No always-on root daemon to protect; Docker's own docs say the daemon "requires `root` privileges unless you opt-in" to rootless. |
| Default privilege | Rootless exists but is opt-in. | Containers "can either be run by root or by a non-privileged user" from the start. |
| Group membership | A shared `docker` group is easy, and Docker's docs say it "grants root-level privileges". | No group that grants access to a root-owned daemon socket (**est.**); rootless needs only your own account. |
| Compose | The reference implementation: `docker compose` is Docker's own tool. | `podman compose` hands the work to `docker-compose` or `podman-compose`, "a wrapper, not a compose implementation". |
| Ecosystem and docs | Portainer targets Docker directly and reaches Podman through Podman's Docker-compatible API. | Serves a "Docker v1.40 API" compatibility layer, so tools written for the Docker API can often connect (**est.**). |
| Service management | `--restart` policies handled by the daemon (**est.**). | Quadlet makes a container a normal systemd unit, with the generator documented. |
| Pods and Kubernetes YAML | No pods in the pages read. | Native pods and `podman kube play`. |
| GPU | One daemon setting, a compose syntax, an NVIDIA guide for it. | CDI, which NVIDIA recommends for Podman. |
| Management UIs | Portainer was built around the Docker API; its CE install page is the Docker one. | Portainer supports Podman only through the Docker-compatible API and supported only on the stated distribution and Podman 5.x ("we currently only support the above"). |
| Cockpit | Third-party pre-release modules only. | A first-party Cockpit page, `cockpit-podman`. |
| Desktop licensing | Docker Desktop needs a paid subscription for larger companies (Engine on Linux does not carry that note on the page I read). | No such note on the pages I read (**est.**). |

If you need to decide for your own setup, the useful questions are in the [checkpoint](#checkpoint), not in this table: who needs access to the socket, how services start at boot, which tools must speak to the engine, and whether anything needs a GPU.

## Portainer: what it manages and how it is exposed

**What it is.** A web interface that runs as a container and manages container environments. The wiki's earlier line is that it "shows containers, logs and resource use, and it can deploy compose files it calls stacks" ([Docker lesson](Containers-and-Docker-Basics.md#compose-and-portainer)).

**Which engines.** The requirements page (the latest listed release, Portainer 2.45.4 LTS, Business and Community) lists Docker 28.5.1 and 29.10.0, Kubernetes 1.35, 1.36 and 1.37, and Podman 5.8.5. It adds that a variant not listed "doesn't mean it won't work, it just means it hasn't been tested". I did not verify Portainer's current Swarm support for this lesson, so this comparison does not cover it (**est.**).

**Podman, and the limit.** The Podman page: Portainer "manages Podman through Podman's Docker-compatible API", so it is "not a native Podman integration"; support "is limited to configurations where that Docker-compatible API behaves consistently". It names "CentOS 9 with the latest version of Podman 5.x", running as root with sudo or root access, and says "Portainer with rootless Podman may work but is currently not officially supported". There are four ways in: Agent, Socket, Edge Agent Standard and Edge Agent Async. In short, the unprivileged combination (rootless Podman) is the one Portainer does not officially support.

**Editions.** The pricing page lists Business Edition plans: Starter at $1,045 a year for 5, 10 or 15 nodes, Scale at $2,095 a year for 5 to 25 nodes, Enterprise at custom pricing, a "Start free: 3 nodes" button, a 45-day, 15-node trial for Enterprise, and a separate Home and Student page for non-commercial use. It does not mention Community Edition. The CE install page uses the image `portainer/portainer-ce:lts`. The wiki's earlier statement that Community Edition is free is repeated from [the Docker lesson](Containers-and-Docker-Basics.md#compose-and-portainer) and I did not re-read a CE license page for it (**est.**). Prices change; read the page.

**How it is exposed.** The default Docker install: `docker run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:lts`. Port 9443 is the UI over a self-signed certificate by default, 8000 is the TCP tunnel server for Edge Agents (optional, only for Edge compute), and 9001 "must be reachable on the Portainer Agent from the Portainer Server". New installs require a setup token for first-time setup. Look at that command from the security side: it mounts the Docker socket into a container that serves a web login. Whoever logs in to that interface, or breaks it, holds the daemon, and the daemon is root ([Docker lesson](Containers-and-Docker-Basics.md#a-container-is-not-a-small-virtual-machine)). That is the reason this project reaches Portainer only through Twingate, and the reason you do not forward 9443 to the internet.

**The agents.** The architecture page describes two shapes.

| Property | Portainer Agent (classic) | Edge Agent |
|---|---|---|
| Who opens the connection | The Server reaches out to the agent | The agent reaches out to the Server |
| Open ports on the managed host | 9001 reachable from the Server | None required (the requirements page: "does not require any open ports") |
| Assumes | Managed environments on the same network as the Server | Remote environments, no direct access needed; an encrypted TLS tunnel |
| The page recommends it | | "for most environments" |

The agent page adds: the agent reaches Docker over Unix sockets and "does not support connecting to the Docker engine via TCP"; adding `-v /:/host` gives host management; SELinux needs `--privileged`; and a custom `AGENT_SECRET` on the server must be provided to the agent. Exposure to avoid: a Portainer Agent on port 9001 open to a network wider than the Server (**est.** as advice, not a quote), an exposed UI, a default admin that nobody finished setting up, and the Docker socket mounted anywhere you did not mean to. The `-v /:/host` mount is the same one the [Docker lesson shows](Containers-and-Docker-Basics.md#try-it-yourself) on purpose, here installed on purpose.

## Cockpit: a web console for the host

**What it is.** The project describes it as "a web-based graphical interface for servers", which "by default ... uses your system's normal user logins and privileges". It manages the Linux host: storage, networking, containers and virtual machines are pages in the same interface. It manages the **host**, not a cluster.

**How it is reached.** `cockpit-ws` "accepts connections on port `9090`" by default, and on systemd hosts it "starts on demand via socket activation" through the `cockpit.socket` unit. The setup line is `sudo systemctl enable --now cockpit.socket`, then `https://<address>:9090` and a login with a system account. To change the port (a functional choice, for example to avoid a clash, and not protection) you add a drop-in `/etc/systemd/system/cockpit.socket.d/listen.conf` with `ListenStream` lines (the first one empty, to reset the list), then reload and restart the socket; with firewalld active you must open the new port. Distributions listed include Fedora, RHEL, CentOS, Debian, Ubuntu and Arch.

**How it is secured.** Access "is controlled by a cockpit specific pam stack, generally located at `/etc/pam.d/cockpit`", and out of the box "logging in with a local account's password" works. So Cockpit login is host login: a weak local password is a weak Cockpit, and the web port is another way to try it. The page does not cover TLS certificates or sudo; **est.** that it uses a self-signed certificate until you provide one and that privileged tasks use the logged-in user's sudo rights. Read the Cockpit pages on those before exposing it. Socket activation means nothing listens in a process until a connection arrives, but the socket itself is still a listening port to firewall.

**Containers and virtual machines.** Cockpit's application list has `cockpit-podman` ("Podman replaces Docker" in the page's words) and `cockpit-machines` for virtual machines. The cockpit-podman README: "Cockpit UI for podman containers", communicating "through its REST API". The cockpit-machines README: "the Cockpit user interface for virtual machines", using libvirt (`libvirt-dbus`, `virt-install`, `virt-xml`). I found no `cockpit-docker` package on the applications page. Third-party entries exist: a "Docker Manager" listed as pre-release, and `cockpit-compose` for "Docker and Podman Compose stacks". Those are community code, not Cockpit's own; read the code before you install them, as you would any plugin.

**Portainer and Cockpit compared.**

| Property | Portainer | Cockpit |
|---|---|---|
| Manages | Container environments (Docker, Kubernetes, Podman via the Docker-compatible API) | One Linux host: storage, network, updates, containers, VMs |
| Runs as | A container with the socket mounted, plus optional agents | A systemd socket and a web service on the host |
| Login | Its own users and roles | The host's PAM accounts |
| Port | 9443 (UI), 8000 (Edge tunnel), 9001 (agent) | 9090 |
| Docker | Yes, the original focus | No first-party module; third-party only |
| Podman | Rootful, via the compatible API; rootless unsupported | First-party `cockpit-podman` |
| Free | See the edition note above | Open source (**est.** for the license; not read) |

## Try it yourself: the same container under Docker and rootless Podman

Free. **Not run** (see the status banner). It follows the Docker, Podman and Compose pages as read on 2026-11-25. Do everything in a throwaway VM, publish only on the loopback address, and delete the VM at the end.

**0. A VM.** Make a Linux VM as in [the first-VM exercise](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md#free-path-a-first-vm-with-qemu-and-a-small-linux-iso). Install Docker Engine and Podman from your distribution's documented route (Docker's install page lists platforms; for Docker prefer its own signed repository, as the [Docker lesson](Containers-and-Docker-Basics.md#where-this-shows-up-in-the-repo) does). Check `/etc/subuid` and `/etc/subgid` have a line for your user. Rootless Podman needs the range; **est.** that the installer created it on your distribution.

**1. The same container, two engines.**

```bash
docker run -d --name web-docker -p 127.0.0.1:8080:80 nginx:stable
podman run -d --name web-podman -p 127.0.0.1:8081:80 nginx:stable
curl -sI http://127.0.0.1:8080 | head -1
curl -sI http://127.0.0.1:8081 | head -1
```

Run the `podman` line as your ordinary user, not with `sudo`. Expect two HTTP responses (est.). The `-p 127.0.0.1:...` form matters: it keeps the port off the network, which is the habit from [the firewall trap](Containers-and-Docker-Basics.md#docker-and-firewalls-one-trap).

**2. Compare who owns the process.**

```bash
ps -eo user,pid,args | grep '[n]ginx'
id
ls -l /var/run/docker.sock
```

You should see the container's nginx processes in the host's process list: **est.** that the one started through Docker shows `root` as its user and the one started by Podman shows your own user (or a subordinate ID for the worker processes). `ls` should show the socket owned by `root`, as Docker's post-install page says, with the `docker` group on it if you were added. That one listing is why the group is root-equivalent. The `-v /:/host` demonstration of the same fact is in [the Docker lesson](Containers-and-Docker-Basics.md#try-it-yourself); do not repeat it here, and do not add your user to the group for this exercise (use `sudo docker` if the socket denies you).

**3. A compose file, run both ways.** Save as `compose.yaml`:

```yaml
services:
  web:
    image: nginx:stable
    ports:
      - "127.0.0.1:8082:80"
```

```bash
sudo docker compose up -d
sudo docker compose down
podman compose up -d
podman compose down
```

`podman compose` needs `docker-compose` or `podman-compose` installed, because it is a wrapper that runs one of them ([Podman's page](https://docs.podman.io/en/latest/markdown/podman-compose.1.html)). If neither exists, expect an error that names the missing provider (est.).

**4. Point the Docker client at Podman's socket (optional).**

```bash
systemctl --user enable --now podman.socket
export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/podman/podman.sock
docker ps
```

The socket path is the rootless default from the `podman system service` page; the unit name `podman.socket` and these exact commands are **est.**, because that page names the service and the path and not this unit. `docker ps` should now list Podman's containers, which shows the compatibility layer. Unset `DOCKER_HOST` afterwards.

**5. A Quadlet unit.** Save as `~/.config/containers/systemd/demo.container`:

```ini
[Container]
Image=docker.io/library/nginx:stable
PublishPort=127.0.0.1:8083:80

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user start demo.service
systemctl --user status demo.service
```

The directory and the `.container` extension are from the Podman unit page; the section and key names (`[Container]`, `Image=`, `PublishPort=`, `[Install]`) and the generated `demo.service` name are **est.**, since I did not read the key reference. If it fails, `journalctl --user -u demo.service` is where the reason is.

**6. A Kubernetes file on one host.** Reuse `web.yaml` from [step 6 of the Kubernetes lesson](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md#try-it-yourself-a-one-node-cluster-in-a-throwaway-vm), then:

```bash
podman kube play web.yaml
podman pod ps
podman kube play --down web.yaml
```

`kube play` supports a Deployment kind per its page; **est.** that this file starts cleanly and what `podman pod ps` prints.

**7. Undo everything.**

```bash
docker rm -f web-docker
podman rm -f web-podman
systemctl --user stop demo.service
rm ~/.config/containers/systemd/demo.container
systemctl --user daemon-reload
systemctl --user disable --now podman.socket
```

Then delete the VM. Check no container or VM process is left running.

## Build, break, detect, evade, defend

**Break.** Publish a Docker container without the loopback address (`-p 8090:80`) in the VM, then look at what is listening from another machine on the same virtual network. Docker's own page says its rules bypass the host firewall front ends; the point is to see that the container is reachable even though you never opened the port. Remove it afterwards. Then try the same under rootless Podman and note that binding a privileged port (below 1024) is where an unprivileged user usually stops (**est.**; the tutorial I read does not list it).

**Detect.** `docker ps` and `podman ps` list what runs; `docker events` and `journalctl` show starts and stops; `ls -l /var/run/docker.sock` and `getent group docker` show who holds the daemon. In a company, the same facts go to a SIEM ([Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md)): an unexpected member of the `docker` group, a new container with the socket mounted, or a new open port on 9443, 9001 or 9090 is the signal.

**Evade, in words only.** An attacker with code running as a user in the `docker` group, or with access to a Portainer login or an exposed agent port, asks the daemon for a container that mounts the host's disk. The Docker lesson shows the harmless version of the same request. This page gives no technique beyond that sentence.

**Defend.** Treat the `docker` group as root, bind published ports to a specific address, and reach Portainer and Cockpit only through the private network used here, Twingate. If Portainer manages a remote host, allow port 9001 only from the Server or use the outbound-connecting Edge Agent. Use rootless Docker or rootless Podman where the workload allows, pin images by version, and keep the engine and the UI patched.

**Undo (the whole lab).** Step 7, then delete the VM and its disk image.

## Checkpoint

Without looking back: say what is different about a daemon and a daemonless engine; say why the `docker` group is root and quote the page; name two prerequisites of rootless mode on either engine; say what `podman compose` actually runs; say what Quadlet is and which file extensions it reads; say how a GPU reaches a container under Docker and under Podman; say what limits Portainer's Podman support and what mounting the Docker socket into it means; say how Cockpit logs you in and which port it uses; and say which engine you would pick for one droplet, for a rootless laptop and for a team that needs scaling, with the reason.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "Podman is Docker with a different name" | Different design: no daemon, rootless by default, and a compatibility layer, not an identical engine | The Podman docs; test your compose file |
| "Adding my user to the `docker` group is the safe way to avoid `sudo`" | The group "grants root-level privileges" | `getent group docker`, Docker's post-install page |
| "Rootless means nothing can go wrong" | A break-out lands as your user, which still owns your files and tokens, and a rootless engine has its own limits | The rootless pages; what that user can reach |
| "`podman compose` is a Compose engine" | It is a wrapper around `docker-compose` or `podman-compose` | `podman compose --help`, the provider on `PATH` |
| "Portainer fully supports Podman" | Through the Docker-compatible API, on stated configurations; rootless is not officially supported | The Portainer Podman page |
| "A UI behind a login is safe on the internet" | Portainer holds the socket, Cockpit holds a host login | Private access only, no forwarding of 9443, 9001 or 9090 |
| "`ufw` blocks my published port" | Docker's rules can bypass it | Publish to `127.0.0.1`, test from another machine |
| "Kubernetes replaces Docker or Podman" | It needs a runtime on each node and answers a different question | The [Kubernetes lesson](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md) |
| "I prefer X, so X is the right answer" | Choose from the actual constraints: daemon privilege, Compose compatibility, systemd integration, GPU access and the number of hosts | The [comparison table](#where-each-is-the-right-answer) |

## Claims register

Read on 2026-11-25 with read-only requests. "Read" means I read the page text. Quotes are from those reads.

| Claim | Source | Status |
|---|---|---|
| Docker's daemon "requires `root` privileges unless you opt-in to" rootless mode; only trusted users should control it; the API endpoint can lead to privilege escalation | [Docker Engine security](https://docs.docker.com/engine/security/) | Read |
| "The `docker` group grants root-level privileges to the user"; the Unix socket is owned by root by default | [Linux post-install steps](https://docs.docker.com/engine/install/linux-postinstall/) | Read |
| Rootless mode runs the daemon and containers as a non-root user; needs `newuidmap` and `newgidmap`; `/etc/subuid` and `/etc/subgid` hold at least 65,536 subordinate IDs; `dockerd-rootless-setuptool.sh install` | [Docker rootless mode](https://docs.docker.com/engine/security/rootless/) | Read (no limitations list on the fetched text) |
| Docker's published-port rules can bypass firewall front ends | [Docker packet filtering and firewalls](https://docs.docker.com/engine/network/packet-filtering-firewalls/) | Read |
| Docker Compose is "a tool for defining and running multi-container applications" | [Docker Compose](https://docs.docker.com/compose/) | Read |
| Docker Desktop uses Docker Engine; commercial use in larger companies (over 250 employees or over $10 million USD revenue) needs a paid subscription | [Install Docker Engine](https://docs.docker.com/engine/install/) | Read |
| Docker Compose GPU syntax: `deploy.resources.reservations.devices`, `driver: nvidia`, `capabilities: [gpu]` | [Compose GPU support](https://docs.docker.com/compose/how-tos/gpu-support/) | Read |
| Docker's own GPU access page and the `docker run --gpus` form | [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints/) | **est.** (the page is a pointer; the target page returned an error) |
| Podman is "daemonless, open source, Linux native"; run by root or a non-privileged user; manages pods, containers, images and volumes; Docker-like CLI | [Podman documentation](https://docs.podman.io/en/latest/) | Read |
| Rootless Podman needs a UID range in `/etc/subuid` and `/etc/subgid`, uses `newuidmap` and `newgidmap`, needs a user-mode networking tool, may not allow `ping`, stores under `${XDG_DATA_HOME}/containers/storage` | [Podman rootless tutorial](https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md) | Read |
| `podman compose` is a wrapper that runs `docker-compose` or `podman-compose` and sets up the Podman socket for it | [podman-compose](https://docs.podman.io/en/latest/markdown/podman-compose.1.html) | Read |
| `podman system service`: Docker v1.40 API compatibility layer, socket activation, `DOCKER_HOST`, default socket paths | [podman-system-service](https://docs.podman.io/en/latest/markdown/podman-system-service.1.html) | Read |
| Quadlet: systemd generator, file extensions, rootful and rootless directories | [podman-systemd.unit](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) | Read (first 100000 characters of the page; the last part was not read) |
| Quadlet key names such as `[Container]`, `Image=`, `PublishPort=`, `[Install]`; generated `demo.service` | Same page, key reference | **est.** |
| `podman generate systemd` is deprecated in favor of Quadlet; no plans to remove it | [podman-generate-systemd](https://docs.podman.io/en/latest/markdown/podman-generate-systemd.1.html) | Read |
| `podman kube play` reads Kubernetes YAML; kinds Pod, Deployment, PersistentVolumeClaim, ConfigMap, Secret, DaemonSet, Job; `--down` | [podman-kube-play](https://docs.podman.io/en/latest/markdown/podman-kube-play.1.html) | Read |
| Podman pods as groups of containers | [podman-pod](https://docs.podman.io/en/latest/markdown/podman-pod.1.html) | Read |
| Podman on macOS and Windows runs a guest Linux system managed through a Podman machine | [Podman for Windows](https://github.com/containers/podman/blob/main/docs/tutorials/podman-for-windows.md) | Read |
| NVIDIA Container Toolkit: driver required; `nvidia-ctk runtime configure --runtime=docker`; rootless Docker steps; Podman uses CDI | [NVIDIA Container Toolkit install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) | Read |
| CDI is an open specification; `nvidia-ctk cdi generate --output=/var/run/cdi/nvidia.yaml`; `podman run --device nvidia.com/gpu=all` example | [NVIDIA CDI support](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html) | Read |
| Portainer 2.45.4 LTS lists Docker 28.5.1 and 29.10.0, Kubernetes 1.35 to 1.37, Podman 5.8.5; ports 9443, 8000, 9001; the Edge Agent needs no open ports | [Portainer requirements](https://docs.portainer.io/start/requirements-and-prerequisites) | Read |
| Portainer manages Podman through the Docker-compatible API; CentOS 9 and Podman 5.x supported; rootless not officially supported; four connection methods | [Portainer: add a Podman environment](https://docs.portainer.io/admin/environments/add/podman) | Read |
| Server and agent roles; classic Agent is reached by the Server; Edge Agent connects out over TLS and is recommended for most environments | [Portainer architecture](https://docs.portainer.io/start/architecture) | Read |
| CE install command, ports 9443 and 8000, self-signed certificate, setup token | [Portainer CE on Docker (Linux)](https://docs.portainer.io/start/install-ce/server/docker/linux) | Read |
| Agent: port 9001, no TCP to the Docker engine, `-v /:/host`, SELinux and `--privileged`, `AGENT_SECRET` | [Portainer: add a Docker Agent environment](https://docs.portainer.io/admin/environments/add/docker/agent) | Read |
| Business Edition plans, prices and the free 3-node button; Home and Student page exists | [Portainer pricing](https://www.portainer.io/pricing) | Read (no mention of Community Edition on that page) |
| Community Edition is free | This wiki's [Docker lesson](Containers-and-Docker-Basics.md) | Repeated from the wiki, not re-read; **est.** |
| Portainer supports Docker Swarm | Not read on the pages above | **est.** |
| Cockpit is a web-based interface for servers using the system's normal logins; storage, network, containers, virtual machines | [cockpit-project.org](https://cockpit-project.org/) | Read |
| `sudo systemctl enable --now cockpit.socket`; browse to `https://<address>:9090`; supported distributions | [Running Cockpit](https://cockpit-project.org/running.html) | Read |
| Default port 9090; socket activation; changing the port with a `cockpit.socket.d` drop-in; open the port in firewalld | [Cockpit guide: listening](https://docs.cockpit-project.org/cockpit-guide/latest/guide/listen.html) | Read |
| Login through the `/etc/pam.d/cockpit` PAM stack with local account passwords | [Cockpit guide: authentication](https://docs.cockpit-project.org/cockpit-guide/latest/guide/authentication.html) | Read (the page does not cover TLS or sudo) |
| Cockpit TLS certificate default and sudo behavior | Not read | **est.** |
| Applications list: `cockpit-podman`, `cockpit-machines`, no `cockpit-docker`, third-party Docker Manager (pre-release) and `cockpit-compose` | [Cockpit applications](https://cockpit-project.org/applications.html) | Read |
| cockpit-podman talks to Podman through its REST API; cockpit-machines uses libvirt | [cockpit-podman](https://github.com/cockpit-project/cockpit-podman), [cockpit-machines](https://github.com/cockpit-project/cockpit-machines) | Read |
| Cockpit license | Not read | **est.** |
| The four reasons for preferring Docker | Stated by the maintainer, 2026-11-25 | Stated by the maintainer |
| The output of every command in the exercise | Not run | **est.** |
