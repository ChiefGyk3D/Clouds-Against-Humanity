# Kubernetes for beginners: what it adds over Docker and Compose

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Prerequisites.** [Containers and Docker basics](Containers-and-Docker-Basics.md): images, containers, volumes and what Compose does. A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)). Reading YAML helps ([Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md)). The free exercise runs in a virtual machine you throw away, so [Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) is the side page if you do not have one. About 2 hours for the reading and the exercise (est.).

> **Status: unverified draft. No command on this page was run.** On **2026-11-07** I read the vendor pages named in the [claims register](#claims-register) and wrote the page from them. I did not install `kind`, `minikube`, `kubectl` or `helm`, and I did not start a cluster, so every command in the exercise is copied from those pages or written from them and has not been seen to work. Anything I could not read there is marked **est.** Trust what your terminal prints over what this page says.

> **Where this runs, and the rule.** Everything here is local and free. The exercise builds a cluster inside a throwaway virtual machine on your own computer, exposes nothing to a network, and deletes it at the end. Nothing here creates a cloud account, a droplet or a bill. Placeholder names only (`web`, `demo`).

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Kubernetes for beginners

Previous: [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) / Next: [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md)
<!-- END GENERATED PAGE NAV top -->

## What you will be able to do

- Say what problem Kubernetes solves that Docker and Compose do not, and what it costs you.
- Name a pod, a deployment, a service, a node and the control plane, and say which one you write and which one the cluster runs.
- Explain "desired state" and the loop that chases it, and why deleting a pod does not remove an app.
- Say what managed Kubernetes (DOKS, EKS, AKS, GKE) takes off your hands and what it leaves on them.
- Say what Helm is for, and that secrets and RBAC are concepts you must learn before a cluster holds anything real.
- Decide, with numbers from this project, why Compose on one droplet is the right answer for stage 3.
- Build a one-node cluster in a VM, scale a deployment, kill a pod and watch it come back.

## What the wiki already says

| Idea | Where it is today | What this page adds |
|---|---|---|
| Kubernetes is "the thing that decides which machine runs which container" | [Glossary](Glossary.md), [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md#placing-three-things-on-the-map) (who patches what) | The parts and how they fit. |
| A Kubernetes control plane costs $0 on DigitalOcean, the nodes do not | [How money works in the cloud](How-Money-Works-in-the-Cloud.md), [Roadmap](Roadmap.md) | The reasoning behind "not yet", and when "yet" arrives. |
| Containers, volumes, Compose, the daemon | [Containers and Docker basics](Containers-and-Docker-Basics.md) | Not repeated here. Read it first. |

## The problem it solves

Compose answers: here is a set of containers, run them on **this** machine. That is a good answer until the machine is the problem.

- **One host is one failure.** If the droplet dies, everything on it is down until you build another and start Compose again.
- **Capacity stops at the host.** You can resize a droplet. You cannot tell Compose "run ten copies, spread across three machines".
- **Updates without downtime are manual.** You can start the new container before stopping the old one with scripting. Kubernetes has that as a built-in behavior.
- **A second operator needs a shared description.** A compose file works for one person on one box. Several people changing several machines want an API, permissions on that API, and a record of who asked for what.

Kubernetes is a system for that. The project's own overview calls it "a portable, extensible, open source platform for managing containerized workloads and services" ([Kubernetes overview](https://kubernetes.io/docs/concepts/overview/), the same sentence quoted on the [cloud service models page](Virtual-Machines-Containers-and-Cloud-Service-Models.md#placing-three-things-on-the-map)). The short version for someone who knows Docker: you stop saying "run this container here" and start saying "I want three of these running somewhere", and the system works out where.

It does not do your thinking about state. The Deployment page says a Deployment is for a workload "usually one that doesn't maintain state". Where an app keeps its data is still [the hard question](Containers-and-Docker-Basics.md#state-the-thing-that-makes-containers-hard) it was on Compose, and Kubernetes adds its own objects for it (a separate kind called a StatefulSet; the Pods page points to it).

## The pieces, from the bottom up

```text
You: kubectl apply -f deployment.yaml
        |
        v
+-- Control plane ------------------------+
|  API server <-> etcd (desired state)    |
|  scheduler, controllers (talk to API)   |
+-----------------------------------------+
        ^                       ^
        | kubelet               | kubelet
+-- Node 1 ----------+   +-- Node 2 ----------+
|  pod     pod       |   |  pod               |
+--------------------+   +--------------------+
        ^        ^                ^
        +--------+----------------+
          Service: one stable address in front of the pods
```

**Pod.** The smallest thing Kubernetes runs. The Pods page: "a group of one or more containers, with shared storage and network resources". Most pods hold one container. A pod is **not** durable: you do not name your pods and nurse them. The same page says "Pods are generally not created directly and are created using workload resources".

**Deployment.** The workload resource you will write most. You describe the pod you want and how many copies. The Deployment page: "You describe a desired state in a Deployment, and the Deployment Controller changes the actual state to the desired state at a controlled rate." Underneath it creates a ReplicaSet that keeps the count; the docs say not to manage a ReplicaSet a Deployment owns. Changing the image tag makes a rolling replacement, and `kubectl rollout undo deployment/<name>` goes back one revision.

**Service.** Pods come and go and their addresses change with them. A Service is a stable name and address in front of a changing set of pods, picked by labels. The default type is `ClusterIP`: "Exposes the Service on a cluster-internal IP". Reaching it from outside needs another type or an ingress; with type `LoadBalancer` the docs say Kubernetes "does not directly offer a load balancing component; you must provide one, or you can integrate your Kubernetes cluster with a cloud provider". On a cloud that is a provider load balancer, and it is a line on your bill ([How money works](How-Money-Works-in-the-Cloud.md)).

**Node.** A machine (a VM or a server) that runs pods. Each runs a **kubelet**, which the components page says "ensures that Pods are running, including their containers", and a container runtime. Your containers still run as ordinary processes on a node's kernel, so everything in the [Docker page about kernels and the daemon](Containers-and-Docker-Basics.md#a-container-is-not-a-small-virtual-machine) still applies.

**Control plane.** The brain: the **API server** (every command and every component talks to it), **etcd** (the "consistent and highly-available key value store for all API server data"), the **scheduler** ("assigns each Pod to a suitable node") and the **controller manager** (runs the loops below). You usually do not run workloads on it; you talk to it with `kubectl`.

## Declarative reconciliation: the idea that explains the rest

You do not tell Kubernetes what to do. You tell it what should be true, and a set of loops keeps trying to make it so. The Controllers page uses a thermostat: you set the temperature (the **desired state**), the room has a temperature (the **current state**), and the controller acts to close the gap.

That is why this works:

1. You apply a Deployment with `replicas: 3`.
2. You delete one pod.
3. Current state is 2, desired is 3. A controller asks for a new pod, the scheduler places it, a kubelet starts it.

Nobody "restarted" anything. The cluster noticed a difference and fixed it. It is also why you edit the YAML and re-apply instead of changing a running thing by hand: the file is the record of what you want, the same idea as [infrastructure as code](What-Is-Infrastructure-as-Code.md) and `tofu apply`. The two share a shape (declare, compare, change) but not a tool: OpenTofu makes the cloud match your code when **you** run it, a Kubernetes controller does it continuously on its own.

Two limits. A loop restores what you declared, so a deployment with a bad image keeps failing to start until you fix the file. And a loop does not notice what you never declared: no deployment, no app.

## Managed versus self-run

You can run all of this yourself, or pay a provider to run the control plane.

| Part | Self-run | Managed (DOKS, EKS, AKS, GKE) |
|---|---|---|
| Control plane (API server, etcd, scheduler) | You install, patch, back up and make highly available | The provider runs it |
| Worker nodes | You | Still machines you pay for; patching them is shared (check your provider's page, est.) |
| Your workloads, secrets, RBAC, network rules | You | You |
| Cost | Machines and your time | Nodes, plus a control plane fee that varies by provider |

On DigitalOcean (DOKS) the pricing page says the control plane "is fully managed by DigitalOcean and included at no cost", with control plane high availability at $40.00 a month, and that worker nodes "are built on Droplets and are charged per second at the same price as Droplets". Load balancers and volumes are charged at the same rate as their standalone products (all read 2026-11-07, page marked "Last verified 5 Nov 2026"). I did not read the EKS, AKS or GKE pricing pages for this lesson; **est.** that the other three charge for the control plane or tier in some form, and check each page before you plan around it.

"Managed" is the same lesson as [the cloud service models page](Virtual-Machines-Containers-and-Cloud-Service-Models.md#placing-three-things-on-the-map): the provider takes the control plane, and your workloads, your secrets and your access rules stay your problem.

## Helm: a package manager for the YAML

A real application is a deployment, a service, a config and more, in several files. **Helm** packages them. Its home page: "Helm Charts help you define, install, and upgrade even the most complex Kubernetes application." A **chart** is the package, a **release** is one installed copy, and a values file changes the settings without editing the chart. The Helm usage page's example is `helm install happy-panda bitnami/wordpress`, a release name you pick plus a chart name. `helm rollback` goes back a version.

Two cautions. A chart is somebody else's YAML running in your cluster with whatever permissions you give it, so read it and pin the version, the same habit as [pinning an action by commit](CI-Tests-and-Cost-Gate.md). And Helm is a tool you add, which is one more thing to learn and to keep patched.

## Secrets and RBAC, at concept level

**Secrets.** Kubernetes has a Secret object for passwords and tokens. The Secrets page warns: "Kubernetes Secrets are, by default, stored unencrypted in the API server's underlying data store (etcd). Anyone with API access can retrieve or modify a Secret, and so can anyone with access to etcd." It adds that anyone allowed to create a pod in a namespace can read any Secret there, "including indirect access such as the ability to create a Deployment". So a Secret is a place to put a value, not protection for it. Encryption at rest and tight access are things you turn on. This project keeps secrets in Doppler and hands them to a program at start ([Doppler and secrets](Doppler-and-Secrets.md)); in a cluster that stays the better habit, with the cluster only ever seeing the value it needs.

**RBAC.** Role-based access control ([Glossary](Glossary.md)) decides who may do what to which object: read pods in one namespace, change deployments, nothing else. The security good practices page says administrators "should not use cluster-admin accounts except where specifically needed" and to avoid the `system:masters` group, because its members bypass all RBAC checks. This is [least privilege](Identity-Secrets-and-Zero-Trust-Basics.md) again, with a new vocabulary. A cluster where everyone is cluster-admin has an API server that is one stolen token from total loss.

Neither is a quick add-on. They are why "we will tighten it later" is more expensive on Kubernetes than on a single Compose host.

## What it honestly costs

- **Money.** A cluster is at least the nodes, and a second node is what makes it a cluster rather than one host with extra steps. The [Roadmap](Roadmap.md) works the numbers for this project: the smallest sensible DOKS node is the $24 droplet, a second node doubles that, and the same six containers fit on one $12 host (the Roadmap's figures, not re-checked on 2026-11-07). Control plane free, high availability $40 a month on top, load balancer on top of that.
- **Concepts.** Pods, deployments, services, ingress, namespaces, labels, config, secrets, RBAC, storage, upgrades. The first working app takes an afternoon. Knowing why it broke takes months (est.).
- **Operating it.** Cluster versions need upgrading, nodes need patching, add-ons need patching, and the API server is a high-value target. A managed service removes some of that and not all.
- **The attack surface.** An exposed API server or dashboard has a long record of being the way into other people's clouds (est.; no source read for this lesson). Treat the API like the Docker daemon from the Docker page: whoever controls it controls the machines under it.

## When Compose on one droplet is the right answer

Stage 3 of this project runs about six small containers (a Discord bot, a few daemons, Portainer) on one droplet with Compose. The [stage 3 design draft](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-11-stage-3-workloads-design.md) says why. In short, it is right when all of these are true:

- Everything fits on one machine, with room.
- A few minutes of downtime on a rebuild is acceptable.
- One operator.
- Nothing needs to scale out for a traffic spike.
- The cost ceiling is fixed ($30 a month here; the Roadmap says Kubernetes gets revisited past $40).

The Roadmap's three triggers for moving are: the ceiling moves, a workload needs more than one host, or a second operator wants declarative rollouts more than a web UI. None applies at stage 3. The stage is built so the move is cheap later: one image per service, configuration from the environment and Doppler only, state in a bucket and not on the host. The disposable-droplet habit from the Docker page is what makes a later cluster easy; nothing about Compose blocks it.

Kubernetes is the right answer when the opposite is true: several machines, several people, more than one environment, a need to scale out and in, or a platform team whose job is exactly this.

Scaling pods up and down automatically with a horizontal pod autoscaler (HPA) is its own lesson (issue #461). This page only scales by hand.

## Try it yourself: a one-node cluster in a throwaway VM

Free. **Not run** (see the status banner). It follows the `kind` quick start and the Kubernetes Deployment page, as read on 2026-11-07.

**kind** runs Kubernetes with "Docker container" nodes; **minikube** is "local Kubernetes, focusing on making it easy to learn and develop for Kubernetes" and wants "2 CPUs or more, 2GB of free memory, 20GB of free disk space" (its start page). Pick one. The steps use `kind`.

**0. A VM.** Make a Linux VM as in [the first-VM exercise](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md#free-path-a-first-vm-with-qemu-and-a-small-linux-iso), with at least the 2 CPUs, 2 GB of memory and 20 GB of disk minikube lists, and install a container engine (Docker or Podman) in it. Ordinary guest networking is fine; nothing needs to reach it from outside. Nested virtualization is not needed, because both tools can use containers as nodes ([nested virtualization](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md#nested-virtualization) is the other route).

**1. Install `kind` and `kubectl`.** Download the `kind` release binary from the project's releases page, check its checksum the way you did for the ISO, rename it `kind` and put it on your `PATH`. Install `kubectl` from the Kubernetes docs the same way. The `kind` page says it does not need `kubectl` but its examples do.

**2. Create the cluster.**

```bash
kind create cluster
kubectl get nodes
```

The kind page: "Creating a Kubernetes cluster is as simple as `kind create cluster`." Expect one node, `kind-control-plane` (the container name the kind page uses), in status `Ready` (est.).

**3. Deploy.**

```bash
kubectl create deployment web --image=nginx:stable
kubectl get deployment web
kubectl get pods
```

`create deployment` gives the pods an `app=web` label (est.). Wait until the pod says `Running`.

**4. Scale.**

```bash
kubectl scale deployment/web --replicas=3
kubectl get pods
```

`kubectl scale deployment/<name> --replicas=<n>` is the command on the Deployment page. You should see three pods.

**5. Delete a pod and watch the cluster replace it.** In one terminal:

```bash
kubectl get pods --watch
```

In a second terminal, copy one pod name from the list and run:

```bash
kubectl delete pod <one-pod-name>
```

You should see that pod go `Terminating` and a new one with a different name appear, back to three. That is the reconciliation loop. Now run `kubectl get deployment web` and notice it never changed: you deleted a pod, not the thing you declared.

**6. Declare it in a file.** Save this as `web.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo
  template:
    metadata:
      labels:
        app: demo
    spec:
      containers:
        - name: nginx
          image: nginx:stable
```

Run `kubectl apply -f web.yaml`, then `kubectl get pods -l app=demo`. Change `replicas` to 4, apply again, and compare. The file is now your record, which is the difference from steps 3 and 4. (The shape follows the Deployment page's example, with my names and tag; **est.** that it applies cleanly as written.)

**7. A service in front.**

```bash
kubectl expose deployment demo --port=80
kubectl get service demo
```

You get a `ClusterIP` address that works only inside the cluster (est. for the exact output). Inside the cluster, that one name reaches whichever pods are alive.

**8. Undo.**

```bash
kind delete cluster
```

Then delete the VM, or keep it as a lab. The kind page: "kind delete cluster" deletes the cluster named `kind`. Nothing else was created on your computer.

## Build, break, detect, evade, defend

**Break.** Set a bad image tag (`image: nginx:does-not-exist`), apply, and run `kubectl get pods`. Expect a status like `ImagePullBackOff` (est.). The cluster keeps trying to reach your desired state, which is not the same as reaching a working one. Fix the file and apply again, or run `kubectl rollout undo deployment/demo`.

**Detect.** `kubectl describe pod <name>` lists events at the bottom and `kubectl logs <pod>` prints what the container wrote ([Docker's rule](Containers-and-Docker-Basics.md#pi-shaped-to-cloud-shaped): log to standard output). In a company, cluster audit logs and a SIEM do this at scale ([Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md)).

**Evade, in words only.** An attacker who gets a token for the API looks for what it can read (Secrets), what it can create (a pod that mounts a node's disk) and where cluster-admin is handed out freely. This page shows no technique; the point is that the API server is the Docker daemon with more rooms behind it.

**Defend.** Least-privilege RBAC, no cluster-admin for daily work, no public API server or dashboard, Secrets kept out of the cluster where you can (Doppler) and encrypted where you cannot, pinned images and charts, and upgrades on a schedule.

**Undo (the whole lab).** `kind delete cluster`, then remove the VM and its disk image. Check no container or VM process is left running.

## Checkpoint

Without looking back: name what a pod, a deployment and a service each are; say what the control plane does and what a kubelet does; explain why deleting a pod brings one back and deleting the deployment does not; say what a managed service takes and what it leaves; give two things a Secret does not do by default; give the three triggers in the Roadmap that would move this project off Compose.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "I will run the container with `kubectl run` and call it deployed" | A bare pod is not replaced by anything that you declared | Use a Deployment |
| "Kubernetes makes my app highly available" | It replaces failed pods. One node, one control plane is still one failure | Count your nodes and your control planes |
| "A Secret is encrypted" | Not by default | The Secrets page; enable encryption at rest |
| "Managed means the provider secures it" | The control plane, yes. Your workloads, secrets and RBAC, no | The provider's shared responsibility page |
| "A Service gives me a public address" | The default type is cluster-internal | The `type` field; a load balancer is a bill |
| "The free control plane means a free cluster" | The nodes are billed per second, like droplets | The DOKS pricing page |
| "I deleted the pod and it came back, so it is broken" | That is the design | Change the Deployment, not the pod |
| "I will move to Kubernetes because it is what companies use" | It is a trade of money and attention for features you may not need | The [list of conditions above](#when-compose-on-one-droplet-is-the-right-answer) |

## Claims register

Read on 2026-11-07 with read-only requests. "Read" means I read the page text.

| Claim | Source | Status |
|---|---|---|
| Kubernetes is "a portable, extensible, open source platform for managing containerized workloads and services" | [Kubernetes overview](https://kubernetes.io/docs/concepts/overview/) | Quoted from the wiki's earlier page (read 2026-10-22), not re-read |
| Cluster is a control plane plus nodes; kube-apiserver, etcd, kube-scheduler, kube-controller-manager; kubelet and container runtime on every node | [Kubernetes components](https://kubernetes.io/docs/concepts/overview/components/) | Read |
| A pod is a group of one or more containers with shared storage and network; pods are generally not created directly | [Pods](https://kubernetes.io/docs/concepts/workloads/pods/) | Read |
| A Deployment provides declarative updates; scale with `kubectl scale`; rollback with `kubectl rollout undo`; for workloads that usually do not keep state | [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) | Read |
| A Service gives a stable address to a set of pods; default type ClusterIP; LoadBalancer needs a provider integration | [Service](https://kubernetes.io/docs/concepts/services-networking/service/) | Read |
| Controllers are control loops moving current state toward desired state (thermostat example) | [Controllers](https://kubernetes.io/docs/concepts/architecture/controller/) | Read |
| Secrets are stored unencrypted in etcd by default; anyone who can create a pod in a namespace can read its Secrets | [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/) | Read |
| Avoid routine cluster-admin; `system:masters` bypasses RBAC checks | [RBAC good practices](https://kubernetes.io/docs/concepts/security/rbac-good-practices/) | Read |
| Helm Charts define, install and upgrade Kubernetes applications; `helm install <release> <chart>`; `helm rollback` | [helm.sh](https://helm.sh/), [Using Helm](https://helm.sh/docs/intro/using_helm/) | Read |
| `kind create cluster` and `kind delete cluster`; `kind` does not require `kubectl` | [kind quick start](https://kind.sigs.k8s.io/docs/user/quick-start/) | Read |
| minikube needs 2 CPUs, 2 GB of memory and 20 GB of disk and a container or VM manager | [minikube start](https://minikube.sigs.k8s.io/docs/start/) | Read |
| DOKS control plane included at no cost; control plane HA $40.00 a month; nodes billed like Droplets; load balancers and volumes at their standalone rates | [DigitalOcean: Kubernetes pricing](https://docs.digitalocean.com/products/kubernetes/details/pricing/) | Read; page marked "Last verified 5 Nov 2026" |
| $24 smallest sensible node, $12 host, $40 revisit point | This wiki's [Roadmap](Roadmap.md) | Repeated from the Roadmap, not re-checked |
| EKS, AKS and GKE control plane pricing | Not read | **est.** |
| The output of every command in the exercise | Not run | **est.** |

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Kubernetes for beginners

Previous: [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) / Next: [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md)

In this track: [Track 1: Foundations](Contents.md#track-1-foundations), 36 pages

- OS and Linux, git and the terminal: [Git from zero](Git-From-Zero.md) / [The terminal and your first script](Terminal-and-Your-First-Script.md) / [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) / [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) / [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md) / [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md) / [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) / [Device firmware security: Intel ME, AMD PSP, MINIX and kernel design](Device-Firmware-Security-Intel-ME-AMD-PSP-MINIX-and-Kernel-Design.md) / [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) / **Kubernetes for beginners** / [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) / [Cron, systemd timers and init scripts versus systemd](Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd.md)
- Networking: [How a web request works](How-a-Web-Request-Works.md) / [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) / [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) / [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) / [IPv6 adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md)
- Identity and secrets: [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) / [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) / [Secrets from day one](Secrets-From-Day-One.md) / [Password managers and passkeys](Password-Managers-and-Passkeys-What-Each-Protects-and-Where-They-Fail.md) / [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) / [Hardware security keys: YubiKey, Nitrokey, PIV](Hardware-Security-Keys-YubiKey-Nitrokey-Smart-Cards-and-PIV.md)
- Infrastructure as code: [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md) / [OpenTofu from zero](OpenTofu-From-Zero.md) / [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) / [Ansible: configuration management versus provisioning](Ansible-Configuration-Management-Versus-Provisioning.md) / [Native IaC versus open standards](Native-IaC-vs-Open-Standards-CloudFormation-ARM-Bicep-and-OpenTofu.md) / [Spacelift from zero](Spacelift-From-Zero.md) / [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md) / [Environments and promotion](Environments-and-Promotion-Dev-Staging-Production.md)
- Web hosting: [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md) / [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) / [Static against dynamic: Hugo, WordPress and recon](Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon.md) / [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md) / [Autoscaling and elasticity](Autoscaling-and-Elasticity-Scale-Out-Targets-Cooldowns-and-Cost-Caps.md)

Related pages:

- [Device firmware security: Intel ME, AMD PSP, MINIX and kernel design](Device-Firmware-Security-Intel-ME-AMD-PSP-MINIX-and-Kernel-Design.md)
- [Cron, systemd timers and init scripts versus systemd](Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd.md)
- [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md)
- [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md)
<!-- END GENERATED PAGE NAV bottom -->
