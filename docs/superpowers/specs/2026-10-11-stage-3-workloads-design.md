# Clouds Against Humanity: Stage 3 Workloads

Status: DRAFT for review. Date: 2026-10-11.
Scope: stage 3 only. It depends on stages 0 and 1 (built) and on parts of stage 2 (planned) that are called out below. Nothing in this document is approved to cost money yet; the numbers are here so the approval can be made on purpose.

## 1. Purpose

Move a set of small, always-on bots out of the homelab and into the cloud environment, on one Docker host managed with Portainer, and add a Discord-to-Matrix bridge. The daemons are the first "real" workloads the roadmap promised for stage 3, and they are a good first set because they are all outbound-only pollers with tiny state. Nothing in this stage opens a public inbound port.

Success looks like:

- One workload droplet in the VPC, hardened by cloud-init the same way the connectors are, running Docker Engine and Portainer CE.
- Portainer, SSH and any bridge port reachable only through Twingate, each as its own narrow resource.
- The five daemons running as containers from their published images, taking their secrets from Doppler, with state on the droplet.
- The Discord-to-Matrix bridge running wherever the homeserver can reach it (section 5.4 explains why that may not be this droplet).
- A written cost, approved before the first apply, and a cost gate that knows about the new droplet.

Non-goals: Kubernetes (section 8), a managed database, block storage volumes, load balancers, running an LLM in the cloud, and anything that needs a public listener.

## 2. The workloads

All six are the author's own projects except the bridge. Facts below were read from each repository's README and compose file on 2026-10-11; "est." marks a figure that is this document's estimate, not a vendor's or author's statement.

| Workload | What it does | Runtime and image | Talks to (outbound) | Needs inbound | State | Memory |
|---|---|---|---|---|---|---|
| [penguin-overlord](https://github.com/ChiefGyk3D/penguin-overlord) | Discord bot: news, CISA KEV, space weather, XKCD, comics, moderation. About 220 RSS feeds. | Python 3.10 to 3.14, `ghcr.io/chiefgyk3d/penguin-overlord`, amd64 and arm64 | Discord gateway and API, NOAA, RSS feeds, optional Ollama or Gemini | None. Optional Prometheus exporter and health check, local only | JSON state in `/app/data` (named volume) | Compose limit 512M, reservation 128M |
| [solarstorm_scout](https://github.com/ChiefGyk3D/solarstorm_scout) | Space-weather thread to Bluesky and Mastodon every 1.5 hours; renders a GOES X-ray chart | Python 3.11+ with numpy, `ghcr.io/chiefgyk3d/solarstorm_scout`; runs as a one-shot (timer or `docker-compose.oneshot.yml`) | NOAA SWPC, Bluesky, Mastodon, optional Ollama (Gemini opt-in) | None | None stated beyond config | est. 200M to 300M while a run is active, 0 between runs |
| [Boon-Tube-Daemon](https://github.com/ChiefGyk3D/Boon-Tube-Daemon) | Posts new YouTube uploads to Discord, Matrix, Bluesky and Mastodon | Python 3.8+, `ghcr.io/chiefgyk3d/boon-tube-daemon` (652 MB image) | YouTube Data API, the four social APIs, Gemini or Ollama | None. Health endpoint on 127.0.0.1 | `youtube_state.json`, Matrix session; `./config` mounted at `/app/config` | No compose limit set; est. 100M to 200M |
| [Stream-Daemon](https://github.com/ChiefGyk3D/Stream-Daemon) | Go-live and stream-ended posts for Twitch, YouTube Live and Kick | Python 3.10+, `ghcr.io/chiefgyk3d/stream-daemon` | Twitch, YouTube, Kick, the four social APIs, Gemini or Ollama | None. Health endpoint on 127.0.0.1 | In memory only (README: a restart mid-stream re-posts the go-live) | README: 50M to 100M; example compose limit 512M |
| [Star-Daemon](https://github.com/ChiefGyk3D/Star-Daemon) | Posts GitHub starred-repo updates to Mastodon, Bluesky, Discord, Matrix and Threads | Python 3.11+, built from `docker/Dockerfile` | GitHub API (fine-grained PAT, starring read), the social APIs, Ollama or Gemini | None | `~/.star-daemon-state.json` in named volume `star-daemon-state` | Compose limit 512M, reservation 256M |
| [matrix-appservice-discord](https://github.com/matrix-org/matrix-appservice-discord) | Bridges Discord channels to Matrix rooms as a homeserver application service | Node.js 18 to 20 only; Yarn classic; image `halfshot/matrix-appservice-discord` | Discord gateway and API as a bot; the Matrix homeserver's client API | **Yes: the homeserver pushes transactions to the bridge on TCP 9005** | `discord.db`, user and room stores (files), `config.yaml`, the registration file | Not stated; est. 150M to 300M |

Three things in that table shape the design:

1. **Only the bridge needs an inbound path**, and only from the homeserver. Everything else is a poller. The bridge is also the only one whose state really matters (room and user mappings); the daemons' state is a de-duplication window that rebuilds itself (Star-Daemon re-enumerates stars daily; Stream-Daemon keeps nothing).
2. **Four of the five daemons share one posting library**, hypeman-social, and all of them default to a **local Ollama server** for their optional AI text, with Gemini as the cloud alternative. Ollama lives in the homelab. A cloud daemon can only reach it over the cloud-to-home link that stage 2 designs. Until then the cloud daemons run with the LLM off or on Gemini.
3. **Every daemon already reads its secrets from Doppler** (`DOPPLER_TOKEN`), which is this project's rule anyway. The bridge does not; it wants a `config.yaml` and a registration file. Section 6 handles that.

## 3. Hosting options considered

The question is "where do six small containers live for the least money and the least new machinery", under the project's rules: everything as code, no public inbound, Doppler for secrets, a cost gate that refuses surprises.

| Option | Monthly | Fits the rules? | Verdict |
|---|---|---|---|
| **One droplet, Docker Engine, Portainer CE** | $12 to $24 for the droplet (section 4) | Yes. One `digitalocean_droplet` from a new module, one firewall, Twingate resources. Portainer CE is free with no node limit and no license key. | **Pick.** Cheapest thing that gives a web UI, compose stacks and container logs behind Twingate. |
| Same droplet, Portainer Business "3 nodes free" | $0 extra | Yes, but the free license is per company domain, runs a year at a time and must be re-applied for. | Not needed for one node. Revisit only if a BE-only feature (git auto-update of stacks, RBAC) becomes worth the paperwork. |
| Same droplet, plain compose and systemd, no Portainer | same | Yes, and fewer moving parts. | Fine fallback. Portainer costs about 100 MB of RAM and buys logs, restarts and a stack editor without SSH. Operator's choice; this spec assumes Portainer because it was asked for. |
| DigitalOcean App Platform workers | about $5 per worker on the smallest plan, so $25 to $30 for five or six workers (price to verify) | Partly. No Twingate-only admin plane, no persistent disk for state without another paid product, a new resource type for the cost gate. | No. Costs as much as the whole droplet for less control. |
| DigitalOcean Kubernetes | control plane free; smallest sensible node pool $24+ | Yes technically; the roadmap says not yet. | Deferred, see section 8. |
| Docker Swarm across the connectors | $0 | No. The connectors are stateless by design and the UDP-any outbound rule is on their tag. Mixing roles undoes stage 1's discipline. | No. |
| Another provider (Hetzner, Vultr, Oracle free tier) | $4 to $8 for a comparable box, or free | Not this repository. The modules, cost gate and docs are DigitalOcean-shaped, and a second provider is a second account to harden. | Out of scope. Worth a line in the roadmap as the answer if the ceiling ever bites. |
| Stay in the homelab | $0 | It is what we have today. | The point of the stage is to move them. |

## 4. Sizing and cost

Steady state, from the table in section 2: five Python pollers mostly idle, one Node process, Portainer, Docker Engine and Ubuntu 24.04. Adding the compose reservations and the estimates gives roughly 1.2 to 1.6 GB resident, with bursts when solarstorm_scout renders a chart, penguin-overlord sweeps its feeds, or Boon-Tube-Daemon starts. The sum of the compose limits is about 3 GB, which is only reached if everything spikes at once. CPU is negligible between polls (Stream-Daemon reports under 1 percent idle and about 5 percent during a check).

Prices are the repository's own table (`docs/cost-prices.json`, DigitalOcean sizes API, retrieved 2026-10-10). Stage 1 is $12 and stages 2 and 4 are planned to add $0 to the cloud bill (logs and Grafana run on-prem), so stage 3 is the only remaining paid stage.

| Option | Size | Droplet | Running total | Headroom under $30 | Notes |
|---|---|---|---|---|---|
| A: thin | `s-1vcpu-2gb` (1 vCPU, 2 GB, 50 GB SSD) | $12 | $24 | $6 | Enough memory with limits enforced; one shared vCPU means a chart render and a feed sweep queue behind each other. Could add weekly backups ($2.40) and stay under the ceiling. |
| **B: fit** | `s-2vcpu-2gb` (2 vCPU, 2 GB, 60 GB SSD) | $18 | **$30** | $0 | **Recommended.** Second vCPU for the bursts, memory limits set on every container, swap off. Spends the whole ceiling; backups stay off. |
| C: comfortable | `s-2vcpu-4gb` (2 vCPU, 4 GB, 80 GB SSD) | $24 | $36 | needs a new ceiling of $40 | No memory pressure, room for a sixth daemon. Only if the ceiling is raised on purpose. |

Things that are not in those numbers:

- **Backups.** DigitalOcean's own pricing page (read 2026-10-11) confirms weekly backups at 20 percent and daily at 30 percent of the droplet price, so `backups_fraction` in the price table can be marked verified. On option B weekly backups would be $3.60 and break the ceiling. Section 7 argues the only state worth a backup is the bridge database, and that it should go home over Twingate instead.
- **Bandwidth.** Pooled across the account; the pollers move a few KB per check and the bridge relays chat text. Attachments are fetched by the homeserver, not the bridge. Far below the included transfer. Overage is reported by third parties at $0.01 per GiB; not verified against an official page.
- **Block storage.** Not needed: state is a few megabytes of JSON and SQLite and lives on the droplet's SSD. If a volume is ever wanted, `digitalocean_volume` must be priced and added to the cost gate's allowlist first.
- **Vendor free tiers.** Portainer CE is free. Doppler's free tier limits (projects, service tokens) still need checking against the number of daemons; the roadmap's "not yet verified" list carries this already.

Decision needed: B at exactly $30, or raise the ceiling to $40 and take C. This document recommends B and says so in the roadmap.

## 5. Network and access design

The pattern is the one stage 1 established, applied to a third droplet.

### 5.1 Firewall

A new tag, `cah-workload`, and a new firewall attached by that tag, in addition to the baseline firewall the droplet also carries.

Inbound, all sourced from the **connector tag**, never an address:

| Port | Why |
|---|---|
| TCP 22 | SSH over Twingate, as the stage 1 guide's section 7 predicted |
| TCP 9443 | Portainer's HTTPS UI |
| TCP 9005 | The bridge's appservice listener, only if the bridge runs here (section 5.4) |

Outbound: the firewall module's five defaults (tcp 443, 80, 53; udp 53, 123). Every API in section 2 is HTTPS on 443. The connector firewall's `tcp 30000-31000` and `udp 1-65535` rules are **not** copied to the workload tag; the wiki already promises that.

Docker publishes container ports by editing the host's iptables, which bypasses host firewalls such as ufw. That does not matter here because the DigitalOcean cloud firewall sits outside the droplet, but the compose files should still bind every published port to the droplet's private VPC address, never `0.0.0.0`, so a mistake in the cloud firewall is not immediately an exposure.

### 5.2 Twingate resources

Each is one private address and one port, granted to one group:

| Resource | Port | Group |
|---|---|---|
| `workload-nyc3-host-ssh` | TCP 22 | `cah-nyc3-admins` |
| `workload-nyc3-portainer` | TCP 9443 | `cah-nyc3-admins` |
| `workload-nyc3-bridge` | TCP 9005 | a new group for the homeserver's service account, only if 5.4 lands here |

No resource for the Docker API, ever. Portainer talks to Docker over the local socket.

### 5.3 The host

A new module, `modules/docker-host`, built from the connector module's cloud-init with the Twingate parts removed and these added:

- Docker Engine and the compose plugin from Docker's apt repository, with the signing key checked against a pinned fingerprint before it is trusted, the same way the Twingate key is. Not `get.docker.com | sh`, for the reason on the lessons page.
- A `/etc/docker/daemon.json` with `"live-restore": true`, `json-file` logging with size caps, and no `hosts` entry (socket only).
- Portainer CE as a compose stack owned by cloud-init, bound to the VPC address on 9443, with its data in a named volume.
- The same hardening as the connectors: one user, keys only, unattended upgrades with a reboot window that does not collide with the connectors, chrony, sysctl drop-in.
- Memory limits in every compose file, and no swap.

Unattended upgrades will restart the Docker daemon when it is updated; with `live-restore` the containers keep running through it. Portainer CE updates itself only when its stack is redeployed, so pin its image tag and bump it in a pull request.

### 5.4 Where the bridge runs

An application service is a two-way contract with the homeserver. The bridge calls the homeserver's client API (outbound from the bridge, port 443 or 8448 on the homeserver), and the homeserver pushes every event to the bridge's `url` from the registration file (inbound to the bridge, TCP 9005). So the bridge and the homeserver must reach each other, in both directions, and this environment allows neither direction from the public internet.

The homeserver's location is not recorded in this repository and is the first thing to settle:

| Homeserver is | Then the bridge | Because |
|---|---|---|
| In the homelab | belongs next to the homeserver, costed at $0 here, **or** on this droplet only after stage 2 exists | Home to cloud (homeserver pushes to 9005) works with a Twingate headless client on the homeserver host today. Cloud to home (bridge calls the client API) is exactly the path stage 2 designs. Both are needed. |
| Hosted elsewhere on the internet | belongs next to the homeserver, or on a host that can run a Twingate client | The homeserver must reach 9005. Opening it from the homeserver's public address would be this environment's first public inbound rule, and the answer to that is no. |
| Also being moved to the cloud | goes on this droplet, and the homeserver gets its own sizing and cost line | A Synapse or Conduit homeserver is a bigger workload than everything else here combined and is not in this stage. |

Recommendation: plan the bridge as a stage 3 **workload definition** (compose file, Doppler layout, Twingate group) but make its placement a decision that follows the homeserver, and do not count on it landing on this droplet.

### 5.5 Reaching Ollama

Every daemon's AI feature defaults to a local Ollama server. From the cloud that is a cloud-to-home connection: a Twingate headless client on the droplet with a service account, reaching one resource (the Ollama host and port). That is stage 2's design and its risk (a compromised droplet with a path home). Until stage 2 is built the cloud daemons run with `LLM_ENABLE` off or on Gemini. The daemons post without the AI text when the LLM is unreachable, so this degrades, it does not break.

## 6. Secrets

Rule from stage 0: every secret lives in Doppler and nothing in this repository is a credential. Applied here:

- **The droplet** gets the same inputs as a connector (admin key, reboot window) from the stack. It gets **no** application secret in its user-data. User-data is readable from the metadata endpoint and ends up in state (threat model T5 and T6); the connector tokens are an accepted risk there, and this stage should not widen it with five more tokens.
- **Each daemon** keeps its own Doppler project and config, as today, with one read-only service token per daemon. The compose file carries only `DOPPLER_TOKEN` as a variable, and that value is entered once in Portainer's stack environment over Twingate. Portainer stores it in its own database on the droplet, which is the same trust level as the daemon's own memory.
- **The bridge** has no Doppler client. Its `config.yaml` holds the Discord bot token and the homeserver URL, and the registration file holds the appservice tokens. The bot token can come from the environment (`APPSERVICE_DISCORD_AUTH_BOT_TOKEN`); the rest is rendered from Doppler by a small systemd oneshot on the host (`doppler run --mount`, or a template step) before the stack starts, so the files never live in this repository or in Portainer.
- **Portainer's own admin password** is set on first visit over Twingate and stored in the password manager. Portainer's UI is a second factor away from the internet already (Twingate sign-in through the identity provider), and the admin account should still be strong and unique.

What goes into `.spacelift/config.yml` for the new stack: `DIGITALOCEAN_TOKEN`, `TWINGATE_API_TOKEN`, `TWINGATE_NETWORK`, the admin SSH values, and nothing from the daemons.

## 7. State, backups and recovery

| Data | Where | If lost |
|---|---|---|
| Daemon state (JSON dedup windows, Star-Daemon's star list, Boon-Tube's YouTube state) | Named volumes under `/var/lib/docker/volumes` | A burst of duplicate or missed posts for one cycle; Star-Daemon resyncs within a day. Annoying, not serious. |
| Stream-Daemon state | Memory | Already lost on every restart by design. |
| Bridge database and stores | Named volume | Room and ghost-user mappings gone; the bridge has to be re-plumbed into every room. This is the one that hurts. |
| Portainer database | Named volume | Re-enter five tokens and redeploy six stacks from the compose files in git. Twenty minutes. |
| The droplet itself | Spacelift | Replace through a run, as the connectors are. Everything above is recreated from git plus Doppler plus the backups below. |

Plan: no DigitalOcean backups (cost, section 4). A nightly job on the host writes a consistent copy of the bridge database (`sqlite3 ... ".backup"`) and a tar of the daemon volumes, encrypted, and pushes it home over Twingate once stage 2 provides the path. Until then the bridge is the dependency: if it runs on this droplet before stage 2 exists, its database has no off-host copy, and that is a risk to accept in writing or a reason to wait.

## 8. Kubernetes: not yet, and what would change that

The roadmap lists Kubernetes under "explicitly not planned (yet)". The reason is cost, not objection:

- DigitalOcean Kubernetes has a free control plane but the smallest sensible node is the $24 droplet, and a second node for any kind of resilience doubles it. That is the whole ceiling for the same six containers.
- k3s on this one droplet is possible later at $0 extra, but it is the same box with an API server, etcd and a scheduler eating a few hundred megabytes of a 2 GB machine, and a 4 GB droplet to carry that comfortably is option C.

What this stage does so that the move stays cheap when it comes:

- One image per service, configuration only from the environment and Doppler, state only in named volumes. A compose service shaped like that is a Deployment and a PersistentVolumeClaim with the names changed.
- No reliance on Portainer-only features (its stack editor is fine; its agent, edge or RBAC are not needed).
- The firewall and Twingate pattern (tag per role, one resource per port) is the same whether the thing behind the port is a container or a Service.

Triggers to revisit: the ceiling is raised past $40, a workload needs more than one host, or a second person starts operating this environment and wants declarative rollouts more than a web UI.

## 9. Known risks and decisions

Facts checked 2026-10-11 and decisions this document asks for.

1. **matrix-appservice-discord is stale.** Its last release is 4.0.0 from 2023-09-15 and the `develop` branch has no commit since that date. It supports Node 18 to 20 only, and both of those lines have reached end of life. The `halfshot/matrix-appservice-discord` tag on Docker Hub was last pushed about six years ago, so the image must be built from the tagged source. It still works and it is the right class of bridge for the job: a proper Discord **bot** with guild-owner consent, which is how a community server is bridged. The alternative, [mautrix/discord](https://github.com/mautrix/discord) (Go, actively developed), is a *puppeting* bridge that signs in as a Discord user account; that is automation of a user account, which Discord's terms forbid, and it is aimed at bridging one person's DMs and servers, not a server for its members. Decision: keep matrix-appservice-discord, build its image ourselves from the pinned tag on a supported Node 20 base, record the staleness as an accepted risk, and check for an active fork before the stage is built.
2. **Where is the homeserver** (section 5.4)? Decides whether the bridge is on this droplet at all.
3. **Option B at $30 or option C at $40** (section 4).
4. **Portainer's Docker socket is root.** Anyone who can sign in to Portainer can run a privileged container on the host. Mitigation: Portainer only over Twingate to the admins group, a strong local admin, and no public inbound. Accept and record in the threat model.
5. **Bridge database backup before stage 2** (section 7). Accept or wait.
6. **Portainer CE git stacks.** CE can deploy a stack from a git repository; automatic polling for updates is a Business feature as far as the public docs say. Verify, then decide whether compose files live in this repository (public, no secrets in them) or in Portainer alone.
7. **Price table.** Mark `backups_fraction_verified` true (20 percent weekly confirmed on DigitalOcean's pricing page), keep bandwidth overage and block storage as unverified.

## 10. Changes this stage makes to the repository

Not an implementation plan; the list of what the plan will have to touch.

- `modules/docker-host/`: droplet, cloud-init, tests. No Twingate connector in it.
- `stacks/30-workloads/`: tag, firewall (`inbound_from_tag_rules` with the connector tag as source), the module, Twingate resources and group, `cost.json` with one `s-2vcpu-2gb` droplet.
- `docs/stages/approved.json`: stage 3, approved total $30.00 (option B), and `modules/docker-host/main.tf` added to `allowed_sources` for `digitalocean_droplet`.
- `scripts/cost_check.py`: today it counts `twingate-connector` module blocks and demands they equal the droplet entries in the manifests. That check needs to count every costed module (connector and docker-host), with the same "no `count` or `for_each`" rule, and `tests/test_cost_check.py` updated to match.
- `.spacelift/config.yml`: stack `cah-30-workloads` with its Doppler names.
- `docs/stages/03-workloads.md`: the operator guide (decisions, bootstrap, verify, rollback), including the Portainer first-visit steps and the per-daemon Doppler token entry.
- Wiki: roadmap, cost, threat model (Docker socket, bridge inbound), glossary. Done alongside this draft.
