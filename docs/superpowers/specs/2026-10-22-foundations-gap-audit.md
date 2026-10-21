# Clouds Against Humanity: foundations gap audit and proposed lessons

Status: DRAFT for review. Date: 2026-10-22. Branch `docs/foundations-audit`, from main `cb1286e`.
Tooling: none shipped. This is an audit and a plan; no wiki page, code, cost file or stage manifest is changed by it.
Scope: which basic terms the wiki uses without teaching, and which beginner lessons would close the gaps. It does not write those lessons. Two sibling lessons are already being written by other work and are out of scope here: `APIs-and-Tokens-From-Zero` and `Linux-for-Enterprise-Beginners`. Where a proposed lesson leans on either, it says so.

## 1. Why this audit

The maintainer's observation is that IT and cybersecurity college programs teach foundations badly: a graduate can recite a framework and cannot say what a DNS lookup does, what a certificate is for, or why a ticket is raised before a change. This wiki already has eight start-from-zero pages (core steps 1 to 9). They cover the cloud, addresses and ports, secrets, infrastructure as code, git, containers, money and habits. The question here is what they assume anyway, and what a learner needs next to work in a company rather than a homelab.

## 2. Method

Everything below was counted by script; the judgments were read by hand.

1. **Corpus.** The 66 pages under `docs/wiki` whose names do not start with an underscore, excluding the Glossary (the Glossary defines terms and would hide every gap). The sidebar and footer are not pages.
2. **Order.** The 21 pages of the core path in [Reading order](../../wiki/Reading-Order.md), in table order, then every other page alphabetically. "Before" means an earlier step of the core path, so a page that is not on the core path never counts as "earlier".
3. **Terms.** 53 terms or term groups, each a regular expression (case-sensitive for acronyms such as DNS, SIEM and NAT, so "ad" and "ids" do not match; case-insensitive for phrases such as "private key"). The script counts pages whose text matches, and which core step first matches.
4. **Definition.** A script cannot tell a definition from a mention, so this column was judged by reading the page the script found first and the page that looked like the definition: a bold term followed by an explanation, a heading, or a sentence of the form "X is...". "NOT DEFINED" means no wiki page explains the term in prose. A Glossary row is noted separately, because the Glossary is a lookup page that is not on any reading path, and a learner meets the term on a page before they look anything up.
5. **Pages using it before its definition.** The count of core-path pages with a match at a lower step number than the defining page. When the definition is off the core path or absent, every core page that uses the term counts.
6. **Verdicts.** `ok` (defined at or before first use), `minor` (one core page uses it first), `defined late` (two or more core pages use it before its definition), `defined off the core path` (the only definition is on a page the core path does not include), `thin` (a definition exists but gives a name, not an understanding), `gap` (no definition in prose), `gap (off core only)` (no definition, and only pages outside the core path use it).

Limits, stated plainly. The regular expressions overcount ordinary words (a "port" in a cost sentence, a "log" in a verb) and undercount when a page says the same thing in other words. The counts rank gaps; they are not exact. The definitions were judged from the first use of each term and from the page that looked like the definition, not by rereading all 67 pages for each of the 53 terms. The script is a scratch file and is not committed; the method above is enough to rebuild it. No page was run, followed or tested; this audit reads text.

## 3. Results

Of 53 terms: 4 are defined at or before first use, 4 are a minor ordering slip, 3 are thin, 11 are defined late (after two or more core pages used them), 9 are defined only off the core path, and 22 have no prose definition anywhere (17 used on the core path, 5 only outside it).

### 3.1 Table

| Term | First used (core step) | Defined where | Pages using it (all / core) | Core pages using it before its definition | Verdict |
|---|---|---|---|---|---|
| DNS | Networking-Basics-for-This-Project (#3) | Networking-Basics-for-This-Project (#3); one sentence | 11 / 4 | 0 | thin (defined, not taught) |
| TLS, certificates | Networking-Basics-for-This-Project (#3) | **NOT DEFINED** (Glossary TLS row only) | 11 / 5 | 5 | gap |
| Public/private key, SSH key pair | Networking-Basics-for-This-Project (#3) | Identity-Secrets-and-Zero-Trust-Basics (#4) | 16 / 6 | 1 | minor |
| SSH | Start-Here-If-You-Are-New (#1) | Networking-Basics-for-This-Project (#3); used on page 1 as a given | 40 / 16 | 2 | defined late |
| Hashing / commit hash | Git-GitHub-and-Pull-Requests (#6) | Git-GitHub-and-Pull-Requests (#6); informal "fingerprint" only; hashing vs encryption never explained | 10 / 5 | 0 | thin (defined, not taught) |
| Encryption | Identity-Secrets-and-Zero-Trust-Basics (#4) | **NOT DEFINED** (none) | 13 / 5 | 5 | gap |
| YAML | Git-GitHub-and-Pull-Requests (#6) | **NOT DEFINED** (only "a YAML file") | 7 / 2 | 2 | gap |
| JSON | Twingate (#12) | **NOT DEFINED** (none) | 13 / 2 | 2 | gap |
| HCL | What-Is-Infrastructure-as-Code (#5) | What-Is-Infrastructure-as-Code (#5) | 5 / 4 | 0 | ok |
| Terminal / shell / CLI | Networking-Basics-for-This-Project (#3) | Git-From-Zero (off core); off the core path | 26 / 7 | 7 | defined off the core path |
| Environment variable | Identity-Secrets-and-Zero-Trust-Basics (#4) | **NOT DEFINED** (none) | 11 / 5 | 5 | gap |
| Scripting (bash, Python) | What-Is-Infrastructure-as-Code (#5) | **NOT DEFINED** (none) | 27 / 8 | 8 | gap |
| VPN | Start-Here-If-You-Are-New (#1) | Why-ZTNA-Not-a-VPN (#11); defined at core step 11 | 16 / 8 | 5 | defined late |
| ZTNA / zero trust | Start-Here-If-You-Are-New (#1) | Identity-Secrets-and-Zero-Trust-Basics (#4) | 22 / 11 | 2 | defined late |
| Firewall | Start-Here-If-You-Are-New (#1) | Networking-Basics-for-This-Project (#3) | 53 / 20 | 2 | defined late |
| Port, listening | Start-Here-If-You-Are-New (#1) | Networking-Basics-for-This-Project (#3) | 41 / 16 | 2 | defined late |
| CIDR, subnet | Networking-Basics-for-This-Project (#3) | Networking-Basics-for-This-Project (#3); subnet only implied | 21 / 6 | 0 | thin (defined, not taught) |
| NAT | CI-Tests-and-Cost-Gate (#18) | Why-Not-Private-Droplets-Yet (off core); side page | 16 / 2 | 2 | defined off the core path |
| VM, hypervisor | Start-Here-If-You-Are-New (#1) | What-Is-the-Cloud (#2) | 18 / 6 | 1 | minor |
| Container, Docker | Start-Here-If-You-Are-New (#1) | Containers-and-Docker-Basics (#7); optional step 7 | 23 / 8 | 2 | defined late |
| Kubernetes | What-Is-the-Cloud (#2) | **NOT DEFINED** (none) | 7 / 4 | 4 | gap |
| Infrastructure as code | Start-Here-If-You-Are-New (#1) | What-Is-Infrastructure-as-Code (#5) | 19 / 10 | 3 | defined late |
| State (IaC state file) | What-Is-Infrastructure-as-Code (#5) | What-Is-Infrastructure-as-Code (#5) | 5 / 2 | 0 | ok |
| CI/CD, pipeline | Start-Here-If-You-Are-New (#1) | Git-GitHub-and-Pull-Requests (#6) | 44 / 15 | 3 | defined late |
| Version control (git) | Start-Here-If-You-Are-New (#1) | Git-GitHub-and-Pull-Requests (#6) | 29 / 10 | 3 | defined late |
| HTTP/HTTPS | What-Is-the-Cloud (#2) | **NOT DEFINED** (none) | 10 / 5 | 5 | gap |
| API | Start-Here-If-You-Are-New (#1) | What-Is-the-Cloud (#2) | 32 / 13 | 1 | minor |
| Logs, logging | Start-Here-If-You-Are-New (#1) | Cloud-Telemetry-What-and-Why (off core); detection path, unverified draft; the log-versus-metric split only | 47 / 15 | 15 | defined off the core path |
| SIEM | Why-ZTNA-Not-a-VPN (#11) | Cloud-Telemetry-What-and-Why (off core); detection path, unverified draft | 17 / 4 | 4 | defined off the core path |
| IDS/IPS, EDR | Detection-and-Monitoring-Wazuh-and-the-Landscape (off core) | Detection-and-Monitoring-Wazuh-and-the-Landscape (off core); EDR only; IDS/IPS never named | 3 / 0 | 0 | defined off the core path |
| OAuth | Provider-GCP-The-Same-Four-Pieces (off core) | **NOT DEFINED** (none) | 1 / 0 | 0 | gap (off core only) |
| OIDC | Spacelift (#16) | Spacelift (#16); Glossary row | 10 / 3 | 0 | ok |
| SAML | Enterprise-Identity-and-Secrets-at-Scale (off core) | **NOT DEFINED** (none) | 2 / 0 | 0 | gap (off core only) |
| SSO | Build-It-From-Zero-Accounts-to-Stage-1 (off core) | Enterprise-Identity-and-Secrets-at-Scale (off core); enterprise path, off core | 3 / 0 | 0 | defined off the core path |
| MFA | Start-Here-If-You-Are-New (#1) | Identity-Secrets-and-Zero-Trust-Basics (#4) | 15 / 5 | 2 | defined late |
| Least privilege / RBAC | Identity-Secrets-and-Zero-Trust-Basics (#4) | Identity-Secrets-and-Zero-Trust-Basics (#4); RBAC itself undefined | 15 / 6 | 0 | ok |
| IAM | Architecture-Overview (#10) | **NOT DEFINED** (only inside AWS/GCP drafts) | 12 / 1 | 1 | gap |
| IaaS/PaaS/SaaS | Small-Example-Enterprise-Landscape (off core) | **NOT DEFINED** (none) | 3 / 0 | 0 | gap (off core only) |
| Backups, snapshots | Start-Here-If-You-Are-New (#1) | **NOT DEFINED** (only price) | 24 / 8 | 8 | gap |
| Regular expressions | CI-Tests-and-Cost-Gate (#18) | **NOT DEFINED** (none) | 3 / 1 | 1 | gap |
| Active Directory, Windows admin | Git-From-Zero (off core) | **NOT DEFINED** (no page covers it) | 3 / 0 | 0 | gap (off core only) |
| Windows (as a platform) | Careers-Roles-and-What-to-Learn-Next (off core) | **NOT DEFINED** (install steps only) | 5 / 0 | 0 | gap (off core only) |
| macOS | Networking-Basics-for-This-Project (#3) | **NOT DEFINED** (install steps only) | 3 / 1 | 1 | gap |
| Linux basics (sudo, systemd, files) | Twingate (#12) | **NOT DEFINED** (sibling lesson in flight) | 17 / 5 | 5 | gap |
| Ticketing, ITSM | Identity-Secrets-and-Zero-Trust-Basics (#4) | Enterprise-Change-Management-for-Beginners (off core); enterprise path, off core | 11 / 2 | 2 | defined off the core path |
| On-call, incident | Identity-Secrets-and-Zero-Trust-Basics (#4) | Enterprise-Infrastructure-Differences (off core); enterprise path, off core | 11 / 2 | 2 | defined off the core path |
| Change management, CAB | Enterprise-Engineering-Habits (#9) | Enterprise-Change-Management-for-Beginners (off core); enterprise path, off core | 6 / 1 | 1 | defined off the core path |
| Vulnerability, CVE, exploit | Why-ZTNA-Not-a-VPN (#11) | **NOT DEFINED** (none) | 5 / 2 | 2 | gap |
| Phishing, malware, ransomware | Why-ZTNA-Not-a-VPN (#11) | **NOT DEFINED** (none) | 6 / 1 | 1 | gap |
| Patching | Containers-and-Docker-Basics (#7) | Droplet-Hardening (#14); as a habit, not a concept | 6 / 3 | 2 | defined late |
| Compliance (SOC 2, ISO, NIST) | Identity-Secrets-and-Zero-Trust-Basics (#4) | **NOT DEFINED** (none) | 9 / 3 | 3 | gap |
| Load balancer, proxy, CDN | What-Is-the-Cloud (#2) | **NOT DEFINED** (none) | 12 / 5 | 5 | gap |
| TCP/UDP, packet, protocol | What-Is-the-Cloud (#2) | Networking-Basics-for-This-Project (#3) | 30 / 13 | 1 | minor |

How to read it: "First used (core step)" is the first core-path step whose text matches, or "off core" if only other pages match. "Pages using it (all / core)" is out of 66 pages and 21 core steps.

### 3.2 What stands out

1. **The biggest block is not networking, it is the working vocabulary of a technician.** Logs (47 pages, 15 core pages, defined only on a draft telemetry page off the path), scripting (27 pages, 8 core), terminal and shell (26 pages, 7 core, defined only in the off-path Git from zero), environment variables (11 and 5), YAML and JSON (7 and 13 pages, never defined), HTTP and HTTPS, and backups (24 pages, 8 core, only ever priced). A reader who has never opened a terminal meets all of these on core steps 3 to 7.
2. **Cryptography is used in four places and taught in none.** TLS and certificates (11 pages, 5 core), encryption (13, 5) and hashing (10, 5) have no prose definition. The key pair is explained at core step 4, but a hash is only "a 40-character fingerprint" at step 6, and nothing says how hashing differs from encryption, or what a certificate proves. The Glossary has a TLS row and nothing for certificates, hashing or encryption.
3. **Terms pass through core steps 1 and 2 as given.** SSH, firewall, port, VPN, ZTNA, MFA, container, IaC and CI/CD appear in the step 1 comparison table, before the pages that define them. That is acceptable for a map page (every row links onward), and the table counts it, but it means steps 1 and 2 carry about a dozen undefined words each.
4. **Enterprise identity is the thinnest area for a beginner heading to an enterprise.** SAML, OAuth and IAM are undefined; SSO and OIDC are defined only on the enterprise page or in Spacelift's no-OIDC section; Active Directory has no page at all (Microsoft Entra is named as a product on five pages); Windows and macOS appear only as install steps. The enterprise reality for most new hires is a Windows laptop, a directory, SSO, and a ticket queue. The wiki teaches a Linux droplet, git and a pipeline.
5. **Security vocabulary arrives without its foundations.** Vulnerability, CVE, exploit, phishing, malware and compliance frameworks first appear at core step 11 (and step 4 for compliance) with no definition. IDS and IPS are never named; EDR is defined once, in a draft page off the core path.
6. **The enterprise-habits terms are defined, but off the path a beginner takes.** Tickets, change management, CAB and on-call are defined on the Enterprise path; core steps 4 and 9 use them first. See section 6.
7. **Not-gaps worth recording.** DNS, CIDR, ports, VM, API, HCL, state and least privilege are all defined where they are first needed or one step later. These pages (core steps 2 to 5) are good; the proposals below extend them rather than replace them.

## 4. Proposed foundations lessons

Principle (the project's pay-to-play rule, as written in the [honeypot education plan](2026-10-22-honeypot-education-plan.md) and stage 2 guide): theory is free; hands-on is paid for by the person doing it, at a cost they can afford. Every lesson below has a THEORY path (reading plus exercises on the learner's own computer, no account, nothing to approve) and an optional HANDS-ON path with its cost. Cost figures come from `docs/cost-prices.json` (retrieved 2026-10-21): a `s-1vcpu-1gb` droplet is $6 a month, `s-1vcpu-512mb-10gb` is $4. A droplet exists only for as long as the learner keeps it; the hands-on paths assume it is destroyed at the end of the session, and the cost shown is the monthly price as a ceiling, not an hourly figure (the hourly rate was not read for this plan; est.). Nothing here changes the reference environment's $30 ceiling: a learner's lab is the learner's own account.

Every lesson ends in a Build/Break/Detect/Evade/Defend mini-loop, kept small and local (see section 5 for the shared rules). "Prerequisite" names pages that exist today. Sizes use the planning page's hours: S about 2 h, M about 5 h, L about 12 h of writing and review.

Sprints use the [Roadmap schedule](../../wiki/Roadmap.md#schedule). S1 is the maintainer's account and review sprint, so no lesson is scheduled into it. Agent-written docs can land early and wait for review; the sprint shown is when the page is written, not when the maintainer has reviewed it.

### F1. Configuration files and data formats (YAML, JSON, HCL, environment variables, regular expressions)

- **For:** someone who can read a sentence but has never opened a config file; everyone who reaches core step 6 (workflows in YAML) or step 12 (a JSON log line).
- **Learning goals:** read and write YAML, JSON and HCL and say which one a given file in this repo is; spot the three classic syntax mistakes (indentation, quotes, trailing commas); say what an environment variable is, how a program reads one, why a token must not be in the command line; read a short regular expression and write two.
- **Prerequisite:** core step 5 (What is infrastructure as code).
- **Theory path (free):** the lesson plus ten predict-then-check exercises on the repo's own files (`.github/workflows`, `stacks/*/cost.json`, a `.tf` file). Validate with the free tools already on a laptop (`python3 -m json.tool`, or `python -m json.tool` on Windows; `ConvertFrom-Json` in PowerShell; a YAML linter if installed).
- **Hands-on path (optional paid):** none needed; every exercise runs locally. Cost $0.
- **Mini-loop:** Build a valid workflow file. Break it with a tab character. Detect the error from the linter's message. Evade: show how a value that parses as a number or a boolean (the "Norway problem") silently changes meaning. Defend: schema validation in CI. (Local only.)
- **Size:** M.
- **Suggested sprint:** S2.
- **Links into:** [Git, GitHub and pull requests](../../wiki/Git-GitHub-and-Pull-Requests.md) (first YAML), [Variables, tfvars and secrets](../../wiki/Variables-Tfvars-and-Secrets.md), [Settings reference](../../wiki/Settings-Reference.md).

### F2. The terminal and a first script (shell, bash, Python)

- **For:** a learner who can use a mouse and a browser and has never written a program; also those who copy commands from this wiki without knowing what they do.
- **Learning goals:** navigate a file tree, redirect and pipe, read an exit code, write a ten-line bash script with a variable and a loop, and write the same thing in Python; explain why the repo's scripts split "check" from "change".
- **Prerequisite:** the sibling `Linux-for-Enterprise-Beginners` page (files, permissions, sudo) and F1. This lesson must not repeat the Linux lesson; it starts where that one ends.
- **Theory path (free):** a local shell on Linux, macOS (Terminal) or Windows (WSL or PowerShell); exercises on the repo's `scripts/` directory read-only.
- **Hands-on path (optional paid):** none needed. Cost $0.
- **Mini-loop:** Build a script that lists the open ports on the learner's own machine. Break it by running it with a space in a filename. Detect with a linter. Evade: show an unquoted-variable injection with a harmless filename. Defend: quote everything and fail on the first error. The lesson teaches one supported shell per track and names it at the top: **bash** on Linux, macOS or WSL (linter `shellcheck`; defence `set -euo pipefail`; listing with `ss -tln`) and **PowerShell** on Windows (linter PSScriptAnalyzer; defence `Set-StrictMode -Version Latest` and `$ErrorActionPreference = 'Stop'`; listing with `Get-NetTCPConnection -State Listen`). Each step has both forms or says it is track-specific. Read-only by default. (Local only.)
- **Size:** L.
- **Suggested sprint:** S4.
- **Links into:** [Git from zero](../../wiki/Git-From-Zero.md), [Doppler and secrets](../../wiki/Doppler-and-Secrets.md) (the doppler-env script), [CI, tests and the cost gate](../../wiki/CI-Tests-and-Cost-Gate.md).

### F3. How a web request works (DNS, TCP, HTTP, TLS, certificates, proxies and load balancers)

- **For:** anyone who types a URL and wants to know what happens next; essential before the Twingate and ZTNA pages (core steps 11 and 12).
- **Learning goals:** follow one HTTPS request from the name to the page: DNS, TCP handshake, TLS handshake, HTTP request and response; read a certificate's subject, issuer and expiry; say what a reverse proxy, load balancer and CDN each add; tell a client error (4xx) from a server error (5xx).
- **Prerequisite:** core step 3 (Networking basics for this project).
- **Theory path (free):** `dig` (or `Resolve-DnsName` in PowerShell), `curl -v` (`curl.exe` on Windows) and the browser's certificate viewer against a public site the learner does not own, read-only and one request each. Worked traces of the repo's connector setup (outbound TLS only).
- **Hands-on path (optional paid):** two droplets in the learner's own account and one private VPC: a web server with no public inbound rule, and a small client droplet that runs `openssl s_client` and `curl` against the server's private address. The learner reaches the client droplet over SSH with a firewall rule scoped to the learner's own current address only (a /32, removed at teardown), never `0.0.0.0/0`. A browser is not needed; the browser warning is shown in the theory path against a local test server on the laptop. Cost up to $12 a month while both exist (est.; two `s-1vcpu-1gb`, or $8 with two `s-1vcpu-512mb-10gb`); destroy both after, using the teardown checklist pattern.
- **Mini-loop:** Build a throwaway test certificate authority and a short-lived server certificate signed by it, and add that test CA (only) to the client's trust store, so the only fault left to see is expiry (a bare self-signed certificate warns anyway, which would hide the lesson). Break: issue a second certificate that has already expired (a start and end date in the past), rather than moving any clock; the lesson says which clock matters: certificate validity is checked against the **client's** clock, so changing the server's clock changes nothing, and `openssl verify -attime <time>` or `s_client -verify_return_error` shows the verifier-time check without touching a system clock. Detect: `openssl s_client` reports the verify error and the `notAfter` date. Evade: show why clicking through a warning defeats the check. Defend: automated renewal and an expiry alert (links to the secret-expiry calendar in the Roadmap).
- **Size:** L.
- **Suggested sprint:** S3.
- **Links into:** [Networking basics](../../wiki/Networking-Basics-for-This-Project.md), [Why ZTNA and not a VPN](../../wiki/Why-ZTNA-Not-a-VPN.md), [Enterprise identity and secrets at scale](../../wiki/Enterprise-Identity-and-Secrets-at-Scale.md) (certificates).

### F4. Hashing, encryption and keys: what each one is for

- **For:** anyone who has said "it's encrypted" or "it's hashed" without being sure which, or who needs core step 4 and step 6 to make sense.
- **Learning goals:** state in one sentence what encoding, hashing, encryption (symmetric and asymmetric) and signing each give you and what they do not; explain why a password is hashed with a salt and a slow hash while a file is encrypted; explain why a commit hash and a pinned action hash detect tampering; explain the key pair and the SSH host fingerprint prompt.
- **Prerequisite:** core step 4 (Identity, secrets and zero trust basics).
- **Theory path (free):** `sha256sum` (or `shasum -a 256` on macOS, `Get-FileHash` in PowerShell), `openssl enc` and `ssh-keygen` on the learner's own machine, exercises with deliberately wrong guesses.
- **Hands-on path (optional paid):** none needed. Cost $0.
- **Mini-loop:** Build a hash of a file (`sha256sum` on Linux, `shasum -a 256` on macOS, `Get-FileHash` in PowerShell) and a signature of that hash (`openssl` or `ssh-keygen -Y sign`). Break: change one byte. Detect: the hash and signature check fail. Evade: show a length-extension or an unsalted-hash lookup in words only, no tooling against anything real. Defend: salted slow hashes, signed commits, pinned dependencies.
- **Size:** M.
- **Suggested sprint:** S3.
- **Links into:** [Identity, secrets and zero trust basics](../../wiki/Identity-Secrets-and-Zero-Trust-Basics.md), [Git, GitHub and pull requests](../../wiki/Git-GitHub-and-Pull-Requests.md) (pinned hashes).

### F5. Subnets, routing, NAT and the firewall, by hand

- **For:** someone who finished Networking basics and wants to do the arithmetic and see a packet filtered.
- **Learning goals:** work out a /24, /26 and /28 by hand; read a route table; say what NAT hides and what it does not protect; write a default-deny firewall rule set and explain stateful versus stateless; place VPN and ZTNA on the same diagram and say what each assumes.
- **Prerequisite:** core step 3, and F3 for the packet walk.
- **Theory path (free):** a subnet worksheet, and a firewall rule-reading exercise on this repo's `DigitalOcean-Network-and-Firewalls` page. Optionally a free local VM with `nft` or `ufw`.
- **Hands-on path (optional paid):** two $4 or $6 droplets in one VPC with a deliberately wrong firewall rule, destroyed after. Cost up to $12 a month while they exist (est.; two `s-1vcpu-1gb`). Use only the learner's own account.
- **Mini-loop:** Build a default-deny rule set. Break: add `0.0.0.0/0` on one port. Detect: a port scan run from the second droplet against the first one's private address (both in the learner's own account, no other target) shows it. Evade: show why moving SSH to another port hides nothing. Defend: close it and verify with the same scan.
- **Size:** L.
- **Suggested sprint:** S3.
- **Links into:** [Networking basics](../../wiki/Networking-Basics-for-This-Project.md), [DigitalOcean network and firewalls](../../wiki/DigitalOcean-Network-and-Firewalls.md), [Enterprise networks](../../wiki/Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md), [Why not private droplets (yet)](../../wiki/Why-Not-Private-Droplets-Yet.md) (NAT).

### F6. Virtual machines, containers and the cloud service models (IaaS, PaaS, SaaS, shared responsibility)

- **For:** anyone who read core step 2 and 7 and still blurs a VM, a container and a managed service.
- **Learning goals:** draw the stack for a VM and a container and say what is shared; explain IaaS, PaaS and SaaS by who patches what; place Kubernetes, a load balancer and a managed database on that map; say what the shared responsibility model leaves to you; list what is needed to restore a lost machine.
- **Prerequisite:** core steps 2 and 7.
- **Theory path (free):** the lesson plus a table-filling exercise using the three vendor pages already linked in the provider pages. Optionally Docker on the learner's laptop (free), but only for the safe steps below; the socket-mount step is not run on a laptop.
- **Hands-on path (optional paid):** none beyond a laptop. Cost $0.
- **Mini-loop:** Build a container from a pinned image. Break: show a container run as root, then show the Docker-socket mount **without executing it**: read the command and the daemon's documentation, and inspect a pre-made `docker inspect` output that includes the mount. Mounting the host's Docker socket gives the container root-equivalent control of the host, so it is run, if at all, only inside a disposable, isolated VM or sandbox with nothing on it (no shared folders, no credentials, no network to the learner's other machines), destroyed afterwards; never on the learner's laptop or on any machine they care about. Detect: inspect the container and see the mount. Evade: describe a container escape in words only. Defend: non-root, read-only filesystem, no socket mount.
- **Size:** M.
- **Suggested sprint:** S4.
- **Links into:** [What is the cloud](../../wiki/What-Is-the-Cloud.md), [Containers and Docker basics](../../wiki/Containers-and-Docker-Basics.md), [Enterprise infrastructure differences](../../wiki/Enterprise-Infrastructure-Differences.md) (shared responsibility).

### F7. Enterprise identity: directories, SSO, SAML, OAuth and OIDC

- **For:** a learner who expects to sign in to everything at work with one account and wants to know how that works and how it breaks.
- **Learning goals:** explain directory, identity provider, SSO, SAML and OIDC in one picture; explain why OAuth is about delegated access and OIDC adds who you are; read a SAML assertion and a JWT's claims; describe RBAC and a joiner-mover-leaver; explain MFA fatigue and why phishing-resistant factors exist.
- **Prerequisite:** core step 4, F4 (keys, signatures), and the sibling `APIs-and-Tokens-From-Zero` page (tokens and scopes). This lesson must not repeat the token lesson.
- **Theory path (free):** read-only exercises on decoded sample tokens built at run time (never a real one), and a role-mapping worksheet.
- **Hands-on path (optional paid):** a free identity-provider developer tenant (UNVERIFIED: vendor free tiers change; check the vendor page and date it before the lesson names one) wired to a free app. Cost $0 to est.; the lesson must check the vendor page on the day.
- **Mini-loop:** Build SSO to one test app. Break: assign a user to the wrong group. Detect: the sign-in log shows the over-broad grant. Evade: describe token replay in words. Defend: short token lifetime, MFA, and a quarterly access review.
- **Size:** L.
- **Suggested sprint:** S5.
- **Links into:** [Identity, secrets and zero trust basics](../../wiki/Identity-Secrets-and-Zero-Trust-Basics.md), [Enterprise identity and secrets at scale](../../wiki/Enterprise-Identity-and-Secrets-at-Scale.md), [Spacelift](../../wiki/Spacelift.md) (the OIDC section).

### F8. Windows, Active Directory and macOS for the helpdesk and the sysadmin

- **For:** the many learners whose first job manages Windows laptops and a domain, not Linux droplets. The wiki has no page on this at all.
- **Learning goals:** explain domain, domain controller, user, group, OU and group policy in plain words; say what Active Directory and Microsoft Entra ID each are and how they differ; do five PowerShell actions (list users, check a service, read the event log, check the firewall, find a hash of a file); say what a Mac does for device management (profiles, enrolment) and where it differs; explain why a local admin account is a risk.
- **Prerequisite:** F2 (shell) and F7 (identity).
- **Theory path (free):** a read-only tour using screenshots to take yourself (see the Screenshots policy: no vendor console shots committed) and Microsoft's own documentation (cite and date each page when the lesson is written).
- **Hands-on path (optional paid):** a Windows Server evaluation VM on the learner's own machine. Whether Microsoft's evaluation edition is free, and for how long, was not read for this plan: UNVERIFIED, and the lesson must check it. No cloud cost.
- **Mini-loop:** Build a test domain with one group and one policy. Break: put a user in Domain Admins. Detect: the event log and a group-membership report. Evade: describe a credential-dumping technique in words, no tooling (see the ATT&CK page). Defend: tiering, least privilege and local administrator password rotation.
- **Size:** L.
- **Suggested sprint:** S5.
- **Links into:** [Careers, roles and what to learn next](../../wiki/Careers-Roles-and-What-to-Learn-Next.md), [Enterprise identity and secrets at scale](../../wiki/Enterprise-Identity-and-Secrets-at-Scale.md), [Threat frameworks](../../wiki/Threat-Frameworks-STRIDE-ATTACK-ATLAS.md).

### F9. Logs, alerts and detection (log lines, syslog, SIEM, IDS/IPS, EDR)

- **For:** anyone who reads "stage 2 ships logs to a SIEM" and wants to know what is in a log and what a SIEM does with it. Fills the gap in core steps 11 and 14.
- **Learning goals:** read an SSH auth log line and a web access log line field by field; explain log, metric, trace, alert; write a regular expression or query that finds failed logins; say what a SIEM, an IDS, an IPS, an EDR and a NOC/SOC each does; say why timestamps and time sync matter.
- **Prerequisite:** F1 (regular expressions), F2, and core step 14.
- **Theory path (free):** sample log files built at run time; read-only exercises.
- **Hands-on path (optional paid):** the existing [Lab: a synthetic multi-site monitoring stack](../../wiki/Lab-Demo-Monitoring-Stack.md) runs locally (free). A cloud mini SOC is already costed on [Build your own mini SOC](../../wiki/Build-Your-Own-Mini-SOC.md) ($35 to $53 total with the reference environment, per the Roadmap cost table).
- **Mini-loop:** Build a rule that fires on five failed logins in a minute, tested only against a synthetic log file the lesson generates (no real login attempts against any host). Break: add four fake failure lines. Detect: no alert, and the lesson says why. Evade: describe slow-and-low guessing. Defend: tune the window and add a second rule.
- **Size:** M.
- **Suggested sprint:** S6.
- **Links into:** [Cloud telemetry: what and why](../../wiki/Cloud-Telemetry-What-and-Why.md), [Detection, Wazuh and the landscape](../../wiki/Detection-and-Monitoring-Wazuh-and-the-Landscape.md), [Build your own mini SOC](../../wiki/Build-Your-Own-Mini-SOC.md).

### F10. Backups, recovery and patching

- **For:** anyone who thinks "I have a snapshot" means "I can recover".
- **Learning goals:** tell snapshot, backup and replica apart; state RPO and RTO in plain words; explain the 3-2-1 rule; run and time a restore; explain patch cadence, an emergency patch and a maintenance window; read a CVE entry and a severity score.
- **Prerequisite:** core step 8 (How money works in the cloud) for the price side, F2.
- **Theory path (free):** back up and restore a folder on the learner's own machine, with a stopwatch.
- **Hands-on path (optional paid):** a $4 or $6 droplet with the vendor's paid backup option on (weekly 20 percent of the droplet price per `docs/cost-prices.json`, verified 2026-10-19), destroyed after. Cost up to about $7.20 a month while it exists (est.; $6 plus 20 percent).
- **Mini-loop:** Build a nightly backup. Break: delete the source and restore. Detect: a restore test that fails on a corrupt copy. Evade: describe ransomware that encrypts the backups too. Defend: an offline or immutable copy and a restore drill.
- **Size:** M.
- **Suggested sprint:** S7.
- **Links into:** [How money works in the cloud](../../wiki/How-Money-Works-in-the-Cloud.md), [Droplet hardening](../../wiki/Droplet-Hardening.md), [Enterprise infrastructure differences](../../wiki/Enterprise-Infrastructure-Differences.md) (disaster recovery), [Teardown checklist](../../wiki/Teardown-Checklist.md).

### F11. Threats in plain words: vulnerabilities, exploits, phishing, malware and compliance

- **For:** a learner who has met "CVE-2018-13379" at core step 11 and needs to know what the sentence means.
- **Learning goals:** define vulnerability, exploit, patch, zero-day, phishing, malware, ransomware and lateral movement in one sentence each, with one real, dated example each; read a CVE record; say what SOC 2, ISO 27001 and NIST are for and that none is a security guarantee; map the words to the STRIDE and ATT&CK pages.
- **Prerequisite:** core step 11, and F9 for the detection side.
- **Theory path (free):** reading plus public sources, each cited and dated when written (no figure without a retrieval date).
- **Hands-on path (optional paid):** none. Cost $0. This lesson never asks a learner to run an exploit.
- **Mini-loop:** Build a one-page asset list for the learner's home. Break: add a device with a known old firmware. Detect: look it up in a public vulnerability list. Evade: describe why an attacker prefers the unpatched one. Defend: patch plan and an exposure review.
- **Size:** M.
- **Suggested sprint:** S7.
- **Links into:** [Why ZTNA and not a VPN](../../wiki/Why-ZTNA-Not-a-VPN.md), [Threat model](../../wiki/Threat-Model.md), [Threat frameworks](../../wiki/Threat-Frameworks-STRIDE-ATTACK-ATLAS.md).

### F12. Working in a company: tickets, change, on-call and documentation (practicum)

- **For:** every learner heading to a first job; it turns the Enterprise pages into practice.
- **Learning goals:** write a good ticket; write a change request for a real pull request in this repo and classify it; run a handover note; write a runbook step and a short blameless post-mortem; request access with a justification and a duration. See section 6 for the map.
- **Prerequisite:** core step 9 (Enterprise engineering habits) and the [Enterprise change management](../../wiki/Enterprise-Change-Management-for-Beginners.md) page.
- **Theory path (free):** templates and ten worked examples on the existing merged pull requests.
- **Hands-on path (optional paid):** a free issue tracker or board the learner already has (the project's own board uses free GitHub Projects). Cost $0.
- **Mini-loop:** Build a change record for a one-line firewall edit. Break: submit it with no rollback. Detect: a reviewer checklist catches it. Evade: show how "emergency" gets used to skip review. Defend: a retro-approval rule and a count of emergency changes.
- **Size:** S.
- **Suggested sprint:** S2.
- **Links into:** [Enterprise engineering habits](../../wiki/Enterprise-Engineering-Habits.md), [Enterprise change management for beginners](../../wiki/Enterprise-Change-Management-for-Beginners.md), [Trace one change end to end](../../wiki/Trace-One-Change-End-to-End.md).

### 4.1 Summary table

| ID | Title | Size | Sprint | Prerequisite | Hands-on cost (ceiling while it exists) |
|---|---|---|---|---|---|
| F1 | Configuration files and data formats | M | S2 | Core 5 | $0 |
| F12 | Working in a company (practicum) | S | S2 | Core 9, Enterprise change mgmt | $0 |
| F3 | How a web request works | L | S3 | Core 3 | up to $12 a month (est.) |
| F4 | Hashing, encryption and keys | M | S3 | Core 4 | $0 |
| F5 | Subnets, routing, NAT, firewall by hand | L | S3 | Core 3, F3 | up to $12 a month (est.) |
| F2 | The terminal and a first script | L | S4 | Linux sibling lesson, F1 | $0 |
| F6 | VMs, containers, cloud service models | M | S4 | Core 2, 7 | $0 |
| F7 | Enterprise identity (SSO, SAML, OAuth, OIDC) | L | S5 | Core 4, F4, APIs sibling lesson | $0 to est. (vendor check) |
| F8 | Windows, Active Directory, macOS | L | S5 | F2, F7 | $0 (evaluation licence UNVERIFIED) |
| F9 | Logs, alerts and detection | M | S6 | F1, F2, Core 14 | $0 to $53 total (mini SOC) |
| F10 | Backups, recovery and patching | M | S7 | Core 8, F2 | up to about $7.20 (est.) |
| F11 | Threats in plain words | M | S7 | Core 11, F9 | $0 |

Total: 1 S, 6 M, 5 L = about 2 + 30 + 60 = 92 hours by the planning page's conversion, across S2 to S7 (S8 left as buffer). A lesson page is not an XL, so none needs splitting, but F2, F3, F5, F7 and F8 are the largest and may be split in half if a sprint runs hot. S3 carries three lessons (5 + 12 + 12 = about 29 h by that conversion) and is the one to rebalance first, probably by moving F4 to S4. The plan does not claim the maintainer's reviewing capacity; that is his call.

Gaps this set does not cover, on purpose: Linux (sibling lesson), APIs and tokens (sibling lesson), git (already two pages), threat modelling (already five), and cryptographic protocol detail beyond F4.

## 5. Rules every foundations lesson follows

1. **Match the existing page pattern:** the header block, the "Unfamiliar word? Glossary" blockquote, a Prerequisites blockquote, predict-then-check sets, a claims register for anything dated, and the "unverified draft" banner while unbuilt or unchecked.
2. **Add the Glossary rows** for every term in section 3.1 that a lesson closes. The Glossary currently has no DNS, certificate, hash, encryption, YAML, JSON, environment variable, SAML, RBAC, IAM, backup, log or regex row (checked by script against the Glossary's first column).
3. **Mini-loops are local or in the learner's own account.** No lesson tells a learner to scan, attack or probe a host they do not own. "Evade" is taught as a concept and a defensive lesson, in words, not as a working evasion for a real target. Synthetic data only; any sample token or key is built at run time and never committed.
4. **Costs follow the project's cost gate and price files:** cite the file and retrieval date; mark anything unread as est.; a hands-on path that spends money says the cost and the teardown step first.
5. **Screenshots:** none of a real vendor console; use the "Screenshot to take yourself" placeholder from the [Screenshots policy](../../wiki/Screenshots-Policy.md).
6. **A lesson is added to the sidebar and to a Reading order path in the same pull request that adds the page (proposed convention).** `tests/test_wiki_navigation.py` checks only that each page appears in the sidebar **or** in Reading order (an OR, not both), that sidebar and Next-line targets exist, and that no page repeats within one path. It does not check that a lesson is added in the same pull request, or that it is in both places. Doing both in one pull request is therefore a convention this plan proposes; making it a rule would need a test change (require every non-lookup page in both), which is proposed here and not made.

## 6. Recommended Foundations reading track for Reading order

A new row in the table at the top of [Reading order](../../wiki/Reading-Order.md): **Foundations (start here if the vocabulary is new)**. Nothing on the core path moves. The track runs beside it and is meant to be read in this order, each page linked to the core step it supports.

| # | Page | Supports core step | Status |
|---|---|---|---|
| 1 | Linux for enterprise beginners (sibling, in flight) | 3, 7, 14 | being written |
| 2 | APIs and tokens from zero (sibling, in flight) | 2, 4 | being written |
| 3 | F1 Configuration files and data formats | 5, 6, 12 | proposed |
| 4 | F2 The terminal and a first script | 6, 17 | proposed |
| 5 | F3 How a web request works | 3, 11, 12 | proposed |
| 6 | F4 Hashing, encryption and keys | 4, 6 | proposed |
| 7 | F5 Subnets, routing, NAT, firewall by hand | 3, 13 | proposed |
| 8 | F6 VMs, containers, cloud service models | 2, 7 | proposed |
| 9 | F7 Enterprise identity | 4, 16 | proposed |
| 10 | F8 Windows, Active Directory, macOS | 4 | proposed |
| 11 | F9 Logs, alerts and detection | 14, 19 | proposed |
| 12 | F10 Backups, recovery and patching | 8, 14 | proposed |
| 13 | F11 Threats in plain words | 11, 19 | proposed |
| 14 | F12 Working in a company (practicum) | 9 | proposed |

Placement: after the first three core steps for rows 1 to 4, and "as needed" for the rest, since every foundation page opens with the core step it supports. The core path's own "Before you start: None" line should say: if more than two words on step 1 are new, take Foundations rows 1 to 4 first. That is an edit to Reading order and is proposed here, not made.

Smaller edits that would help now, without a new lesson (proposed, not made): move the Glossary link to the top of Start here and of core step 1; add a one-line definition of SSH, firewall, MFA, container, CI/CD and VPN beside each in the step 1 table (the table is the densest place for undefined words); define "terminal" at first use at step 3 with a link to Git from zero; give the six step 1 acronyms a Glossary link on first use.

## 7. Enterprise realities beginners are not taught

These are the things a first job expects on day one that no course explains. Each of the five has some coverage on an Enterprise page; none has a practice session. The map shows where each lives and what is still missing.

| Reality | Where the wiki teaches it today | What a beginner is still missing | Covered by |
|---|---|---|---|
| **Change management** (a change is requested, risk-rated, approved, scheduled, done and reviewed) | [Enterprise change management for beginners](../../wiki/Enterprise-Change-Management-for-Beginners.md): vocabulary, standard/normal/emergency, a worked example of a real pull request, auditor view. [Enterprise engineering habits](../../wiki/Enterprise-Engineering-Habits.md): "stage gates". | A practice session: writing the record for a change you actually made. The page is off the core path and is 30 minutes. | F12 |
| **Ticketing** (every request, fault and change has an id; no ticket, no work) | The change page explains the ticket as the record. No page says what a good ticket contains, or how a queue is triaged. | Writing a clear ticket; priority versus severity; how to ask for help without being rude or vague. | F12 |
| **On-call and incidents** (someone is paged, there is a runbook, an escalation path, a post-incident review) | [Enterprise infrastructure differences](../../wiki/Enterprise-Infrastructure-Differences.md) (observability section), the change page (emergency and break-glass), and [Enterprise engineering habits](../../wiki/Enterprise-Engineering-Habits.md) (runbooks, blameless post-mortems). | A worked incident from alert to review, and what to do in the first five minutes of being paged. | F9, F12 |
| **Least-privilege requests** (you do not just get admin; you ask, say why and for how long, and an owner approves) | [Identity, secrets and zero trust basics](../../wiki/Identity-Secrets-and-Zero-Trust-Basics.md) and [Enterprise engineering habits](../../wiki/Enterprise-Engineering-Habits.md) teach the principle. [Enterprise identity and secrets at scale](../../wiki/Enterprise-Identity-and-Secrets-at-Scale.md) covers just-in-time, break-glass and access reviews. | How to phrase and justify a request, what a manager and a data owner each approve, and why "temporary" access is removed on a date. | F7, F12 |
| **Documentation habits** (the runbook, the decision record, the handover note: if it is not written, it did not happen) | [Enterprise engineering habits](../../wiki/Enterprise-Engineering-Habits.md) (runbooks, "verify, then write down that you verified"), [How this project is planned](../../wiki/How-This-Project-Is-Planned.md) (definition of done), [Lessons learned](../../wiki/Lessons-Learned.md). | A template and a worked example: a runbook step, a handover note, a decision record. | F12 |

One thing the audit could not find on any page: **the first-week reality of working at a company**, meaning how to read an unfamiliar environment, whom to ask, and the unwritten difference between "I can" and "I may". It is partly covered by [Careers, roles and what to learn next](../../wiki/Careers-Roles-and-What-to-Learn-Next.md) (roles and ladder), and F12 should end with a short "your first week" checklist. The wiki's enterprise pages say where the project differs from an enterprise; they do not say what to do on Monday.

## 8. Decisions owed to the maintainer

1. Approve the set as written, trim it, or reorder it. F12, F1 and F4 are the cheapest and the most visibly missing.
2. Should the Foundations track be its own path in Reading order (this plan's recommendation), or folded into the core path as extra steps? Folding would break the "21 pages, about 3 h 15 min" figures and the "Next" lines in every start-from-zero page.
3. Is F8 (Windows and Active Directory) wanted at all? It has no Linux or cloud-project hook, and it needs a vendor licence check that this plan could not do. It is the most useful lesson for an enterprise reader and the one least tied to this repository.
4. Do the sibling lessons (Linux, APIs and tokens) count as Foundations rows 1 and 2, or stay separate?
5. Whether to commit the counting script. It is a scratch file now; adding it would be a code change under `scripts/` and a test, and the audit would then rerun on every wiki change.

## 9. Not verified

- No lesson was written and no page was changed; every proposal is a proposal.
- Counts are regular-expression counts over text (section 2 limits). Definition judgments were read from the first use and the likely defining page, not from a full reread.
- No vendor page was read for this plan. The only prices used are in `docs/cost-prices.json`. The Windows evaluation licence terms, identity-provider free tiers and the hourly droplet rate were not read: marked UNVERIFIED or est.
- The sprint assignment follows the Roadmap table and the planning page's size hours; the maintainer's availability is not assumed.
- The sibling lessons were not read (they were not on main when this audit ran), so overlaps with them are guesses.
