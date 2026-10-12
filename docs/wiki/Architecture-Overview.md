# Architecture overview

> New to cloud, networking or infrastructure as code? Read [Start here if you are new](Start-Here-If-You-Are-New.md) first; this page assumes the vocabulary those pages teach.

There are two planes here, and keeping them separate in your head makes everything else easier.

- **The data plane** is how a person (or later, a service) reaches a host. It runs through Twingate.
- **The control plane** is how the infrastructure itself gets created and changed. It runs through GitHub, Spacelift, Doppler and two cloud APIs.

Neither plane needs a single inbound port open on a droplet.

## Everything on one page

```mermaid
flowchart TB
    subgraph operator["Operator side"]
        dev["Laptop<br/>git + Twingate client"]:::you
    end

    subgraph control["Control plane: changes to infrastructure"]
        gh["GitHub repo<br/>(public)"]:::ctrl
        ci["GitHub Actions<br/>fmt, validate, tofu test,<br/>cost gate, scanners"]:::ctrl
        sl["Spacelift<br/>stacks 00 and 10,<br/>holds OpenTofu state"]:::ctrl
        dp["Doppler<br/>project clouds-against-humanity,<br/>config prd"]:::secret
    end

    subgraph apis["Provider APIs"]
        doapi["DigitalOcean API"]:::cloud
        tgapi["Twingate API"]:::ctrl
    end

    subgraph dataplane["Data plane: reaching a host"]
        tgc["Twingate controller<br/>auth + signed ACLs"]:::ctrl
        relay["Twingate relays<br/>(fallback path only)"]:::ctrl
        subgraph vpc["DigitalOcean VPC 10.78.0.0/24 (tor1)"]
            ca["access-tor1-connector-a"]:::cloud
            cb["access-tor1-connector-b"]:::cloud
        end
    end

    internet["Public internet<br/>scanners, bots, everyone"]:::ext

    dev -- "push branch, open PR" --> gh
    gh -- "every PR and push" --> ci
    gh -- "PR: no run (push policy)<br/>main: tracked run if the<br/>change touches that stack" --> sl
    sl -- "read-only service token" --> dp
    dp -- "named secrets, masked" --> sl
    sl -- "plan, then apply after<br/>a human confirms" --> doapi
    sl --> tgapi

    dev -- "1. sign in, get ACL" --> tgc
    ca -- "outbound TLS" --> tgc
    cb -- "outbound TLS" --> tgc
    dev == "2. end-to-end encrypted,<br/>peer-to-peer when possible" ==> ca
    dev -.-> relay -.-> cb

    internet -. "no inbound rule exists" .-x vpc

    classDef you fill:#132a1f,stroke:#4ade80,color:#dcfce7
    classDef ext fill:#3b1d1d,stroke:#f87171,color:#fde2e2
    classDef ctrl fill:#1e1b3a,stroke:#a78bfa,color:#ede9fe
    classDef cloud fill:#0f2a3d,stroke:#38bdf8,color:#e0f2fe
    classDef secret fill:#3a2a0f,stroke:#fbbf24,color:#fef3c7
```

Color key: green is you, purple is a hosted control service, blue is DigitalOcean, amber holds secrets, red is untrusted.

## Component by component

| Component | What it does here | Why this one |
|---|---|---|
| **DigitalOcean** | Runs the droplets, the VPC and the cloud firewalls | Cheap, predictable pricing, a good OpenTofu provider, and a firewall that attaches by tag. AWS would work and would cost more for the same box and teach IAM before it teaches networking. |
| **OpenTofu** | Describes every resource as code | Open-source fork of Terraform under the Linux Foundation with an MPL license. Same language, no license surprise later. See [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md). |
| **Spacelift** | Runs plan and apply, stores state, waits for a human | State never sits on a laptop, nothing applies from CI, and a pull request plan can be kept away from credentials. See [Spacelift](Spacelift.md). |
| **Doppler** | Holds every secret | One place to rotate. Spacelift only holds a single read-only token. See [Doppler and secrets](Doppler-and-Secrets.md). |
| **Twingate** | Gets an authenticated person to one specific host and port | Outbound-only connectors, per-resource access, no open port. See [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) and [Twingate](Twingate.md). |
| **GitHub Actions** | Tests, scans and the cost gate on every pull request | Calls the shared hardened workflows from git-your-ship-together instead of reinventing them. See [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md). |
| **cloud-init** | Hardens each droplet on first boot | The host is locked down before a human can touch it, and the config is code. See [Droplet hardening](Droplet-Hardening.md). |

## The three paths that matter

### Path 1: a change to infrastructure

```mermaid
flowchart LR
    pr["Pull request"]:::you --> ci["CI green?<br/>tests, cost gate, scanners"]:::ctrl
    pr --> prop["Spacelift: no run<br/>(push policy never proposes)"]:::ctrl
    ci -- "yes" --> merge["Merge to main"]:::you
    merge --> tracked["Spacelift tracked run"]:::ctrl
    tracked --> hook["Hook fetches secrets<br/>from Doppler"]:::secret
    hook --> plan["tofu plan"]:::ctrl
    plan --> human{"Human reads<br/>the plan"}:::you
    human -- "confirm" --> apply["tofu apply"]:::cloud
    human -- "discard" --> stop["Nothing changes"]:::ext

    classDef you fill:#132a1f,stroke:#4ade80,color:#dcfce7
    classDef ext fill:#3b1d1d,stroke:#f87171,color:#fde2e2
    classDef ctrl fill:#1e1b3a,stroke:#a78bfa,color:#ede9fe
    classDef cloud fill:#0f2a3d,stroke:#38bdf8,color:#e0f2fe
    classDef secret fill:#3a2a0f,stroke:#fbbf24,color:#fef3c7
```

Full detail on [Spacelift](Spacelift.md).

### Path 2: an SSH session to a droplet

```mermaid
sequenceDiagram
    autonumber
    participant C as Twingate client (laptop)
    participant K as Twingate controller
    participant R as Relay (only if P2P fails)
    participant A as connector a
    participant B as connector b (target)
    C->>K: Sign in through the identity provider
    K-->>C: Signed ACL: cah-tor1-admins may reach connector-b-ssh, TCP 22
    Note over C: ssh cah-admin@10.78.0.x<br/>client intercepts, address is in the ACL
    C->>A: Certificate-pinned TLS tunnel (peer-to-peer, or through R)
    A->>A: Verify client signature and ACL claim
    A->>B: TCP 22 inside the VPC (tag-scoped firewall rule)
    B-->>C: SSH banner, key auth as cah-admin
```

Twingate may hand the session to either connector, which is why connector a needs to reach connector b's port 22. That one detail cost a debugging session; the story is on [Lessons learned](Lessons-Learned.md).

### Path 3: a secret reaching a run

```mermaid
flowchart TB
    dp["Doppler prd<br/>every real secret"]:::secret
    ctx["Spacelift context cah-doppler<br/>one read-only token, write-only variable"]:::secret
    hook["scripts/spacelift/doppler-env.sh<br/>tracked or destroy run on main only"]:::ctrl
    env["Run environment<br/>values masked in logs"]:::ctrl
    tofu["tofu plan / apply"]:::cloud
    dp -- "read-only service token" --> hook
    ctx -- "auto-attached by label cah" --> hook
    hook --> env --> tofu

    classDef ctrl fill:#1e1b3a,stroke:#a78bfa,color:#ede9fe
    classDef cloud fill:#0f2a3d,stroke:#38bdf8,color:#e0f2fe
    classDef secret fill:#3a2a0f,stroke:#fbbf24,color:#fef3c7
```

Full detail on [Doppler and secrets](Doppler-and-Secrets.md).

## Naming

Everything follows `<layer>-<region>-<role>`, for example `access-tor1-connector-a` or `foundation-tor1-baseline`. Region is a variable everywhere, so a second region is the same modules instantiated again with a different slug, not a copy-paste of the code.

## Repository layout

```
stacks/00-foundation/      project, tag, VPC, baseline firewall        (Spacelift stack cah-00-foundation)
stacks/10-access/          site, connectors, connector firewall,       (Spacelift stack cah-10-access)
                           admin group, SSH resources
modules/vpc/               one VPC per region
modules/firewall/          tag-attached, deny-inbound firewall
modules/twingate-connector/  connector + droplet + cloud-init
scripts/cost_check.py      the cost gate
scripts/spacelift/         Doppler hook for Spacelift runs
docs/stages/               one guide per stage: decisions, verify, rollback
docs/wiki/                 these pages
```

Modules are reusable building blocks; stacks are what actually gets applied. More on that split on [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md).
