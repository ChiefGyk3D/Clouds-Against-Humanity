# Clouds Against Humanity: Stage 3 Workloads

Status: DRAFT for review. Date: 2026-10-11. Revised 2026-10-11 (later): the Discord bridge is `mautrix-discord` (Go), self-hosted on the workload droplet by decision of the operator; etke.cc's hosted bridge is the alternative (section 5.4a). Open: how the etke.cc homeserver reaches the bridge (section 5.4).
Tooling: OpenTofu throughout; where this document or a conversation says "Terraform", read OpenTofu.
Scope: stage 3 only. It depends on stages 0 and 1 (built) and on parts of stage 2 (planned) that are called out below. Nothing in this document is approved to cost money yet; the numbers are here so the approval can be made on purpose.

## 1. Purpose

Move a set of small, always-on bots out of the homelab and into the cloud environment, on one Docker host managed with Portainer, and add a Discord-to-Matrix bridge. The daemons are the first "real" workloads the roadmap promised for stage 3, and they are a good first set because they are all outbound-only pollers with tiny state. Nothing in this stage opens a public inbound port.

Success looks like:

- One workload droplet in the VPC, hardened by cloud-init the same way the connectors are, running Docker Engine and Portainer CE.
- Portainer, SSH and any bridge port reachable only through Twingate, each as its own narrow resource.
- The five daemons running from their published images, taking their secrets from Doppler, with their state in an S3-compatible bucket rather than on the droplet, so the droplet is disposable (section 7).
- The one-shot jobs among them offered a path to DigitalOcean Functions, the Lambda equivalent, where the fit is real (section 3a).
- A "cloud-optimized install" for each daemon: the small set of changes that turns software written for Docker on a Raspberry Pi into something that can lose its host and not care (section 6a).
- The Discord-to-Matrix bridge, `mautrix-discord` (Go, actively maintained), self-hosted as a container with its own Postgres database, backed up to the bucket (sections 5.4 and 7). etke.cc's hosted bridge (section 5.4a) is the alternative if self-hosting hits a wall.
- A written cost, approved before the first apply, and a cost gate that knows about the new droplet and the bucket.

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
| [mautrix-discord](https://github.com/mautrix/discord) | Bridges Discord guilds to Matrix as a homeserver application service. Bot-token login; relay login for Matrix users who have not logged in | Go bridge, image `dock.mau.dev/mautrix/discord:<version tag>` (amd64 and arm64); needs a PostgreSQL server per the general setup page | Discord gateway and API as a bot; the Matrix homeserver's client API | **Yes: the homeserver pushes transactions to the bridge's appservice port** | PostgreSQL database, `config.yaml`, `registration.yaml`, a data directory | Not stated; est. 100M to 200M for the bridge plus 50M to 100M for Postgres |

Three things in that table shape the design:

1. **Only the bridge needs an inbound path**, and only from the homeserver (section 5.4). Everything else is a poller. The bridge is also the only one whose state really matters (room and user mappings); the daemons' state is a de-duplication window that rebuilds itself (Star-Daemon re-enumerates stars daily; Stream-Daemon keeps nothing).
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
| DigitalOcean Functions for the one-shot jobs | $0 within the free allowance (section 3a) | Mostly. Deployed with `doctl serverless`, not OpenTofu, so the cost gate cannot see them. | **Use alongside the droplet** for the jobs that are already one-shots. Not a replacement for the long-running pieces. |
| DigitalOcean Kubernetes | control plane free; smallest sensible node pool $24+ | Yes technically; the roadmap says not yet. | Deferred, see section 8. |
| Docker Swarm across the connectors | $0 | No. The connectors are stateless by design and the UDP-any outbound rule is on their tag. Mixing roles undoes stage 1's discipline. | No. |
| Another provider (Hetzner, Vultr, Oracle free tier) | $4 to $8 for a comparable box, or free | Not this repository. The modules, cost gate and docs are DigitalOcean-shaped, and a second provider is a second account to harden. | Out of scope. Worth a line in the roadmap as the answer if the ceiling ever bites. |
| Stay in the homelab | $0 | It is what we have today. | The point of the stage is to move them. |

### 3a. Serverless: DigitalOcean Functions

DigitalOcean's answer to Lambda is **Functions** (built on Apache OpenWhisk). Facts read 2026-10-11 from DigitalOcean's pricing and docs pages:

- Free allowance of 90,000 GiB-seconds per month per team, then $0.0000185 per GiB-second ($0.07 per GiB-hour). Invocations themselves are not billed; the minimum charge per run is 100 ms.
- Maximum run time 15 minutes, including initialization. Built function at most 48 MB zipped. Remote builds limited to 2 minutes.
- Python 3.9, 3.11, 3.12 and 3.13 runtimes; from 3.11 the runtime bundles numpy and some other common packages, and `requirements.txt` plus a build script adds the rest. Community reports say numpy plus Pillow fit; pandas and OpenCV have hit the size and build-memory limits.
- Scheduled (cron) triggers are supported for standalone Functions, declared under the function in `project.yml` (`sourceType: scheduler`) and deployed with `doctl serverless deploy` (doctl 1.82 or newer). Not available for function components inside App Platform. Triggers made in the control panel are overwritten by the next CLI deploy, so they belong in the file.

A function is a good fit when the job already runs to completion on a timer, holds no connection open, and keeps its state somewhere else. Mapped against section 2:

| Workload | Shape today | Function? | Why |
|---|---|---|---|
| penguin-overlord bot (`bot.py`) | Persistent Discord gateway websocket | **No** | A bot must stay connected; a function cannot. Stays a container. |
| penguin-overlord runners (`news_runner.py`, `kev_runner.py`, `solar_runner.py`, `xkcd_runner.py`, `comics_runner.py`) | One job per invocation, written for systemd timers | **Yes, best candidates** | Already one-shots. Their 100-item dedup state moves to the bucket (section 7). Roughly 200 runs a day at a few seconds each, well inside the free allowance. |
| solarstorm_scout | One-shot every 1.5 hours (`docker-compose.oneshot.yml`, cron examples in its README) | **Yes, with a size check** | Already a one-shot. Needs numpy and the chart renderer under the 48 MB cap; numpy comes with the 3.11+ runtime, the imaging library must be measured. 16 runs a day at under a minute each. |
| Boon-Tube-Daemon | Loop, checks every 15 minutes, keeps `youtube_state.json` and a Matrix session | **Later** | Fits a 15-minute cron once it has a `--once` mode and bucket state. The Matrix session token must persist between runs, so it goes in the bucket too. |
| Star-Daemon | Loop with a daily full resync, JSON state | **Later** | Same shape as Boon-Tube: `--once` mode plus bucket state and it becomes a cron function. |
| Stream-Daemon | Loop, polls every minute or so, updates a live Discord embed, state in memory | **Not first** | Minute-level cron is fine for cost, but the live-embed message ids and "currently live" flag live in memory today; they have to move to the bucket before a function can do this without re-posting on every run. |
| mautrix-discord | Persistent listener and gateway connection | **No** | Same reason as the bot. |

So the realistic split: the bot, the bridge and (at first) the three polling daemons on the droplet; the penguin-overlord runners and solarstorm_scout as scheduled Functions; Boon-Tube and Star-Daemon moving to Functions once section 6a lands. Each function's code lives in its own repository with its `project.yml`, and a GYST workflow deploys it with a scoped token from Doppler. Nothing in this repository changes except the cost record.

Two honest limits. Functions are outside OpenTofu and outside the cost gate's allowlist, so their spend is a line that a human checks against the usage page, and the threat model's T11 residual grows by that much. And a function's secrets are environment variables set at deploy time, so each function gets its own narrow Doppler service token or has its secrets injected by the deploy workflow; neither path puts a secret in a repository.

**Later: AWS Lambda.** DigitalOcean Functions is the interim answer because the account already exists. An AWS tenant is planned but not yet established (hardening a fresh one is its own project), and once it is, the scheduled jobs are candidates to move to Lambda with EventBridge schedules, which the AWS provider manages fully in OpenTofu and which the cost gate could then see. The design keeps that move cheap: each job is a plain handler that reads its config from the environment and its state from an S3-compatible bucket, so the rework is a new deploy target and a bucket endpoint, not a rewrite. Until then nothing here depends on AWS.

### 3b. Object storage: Spaces, or an S3 bucket elsewhere

The daemons' state is a handful of small text files (JSON dedup windows, a star list, a YouTube state file, a Matrix session) and one SQLite database (the bridge). Putting those in an S3-compatible bucket instead of on the droplet does three things at once: the droplet becomes disposable, a function and a container can share the same state, and a versioned bucket is itself the first backup.

| Choice | Monthly | Notes (read 2026-10-11) |
|---|---|---|
| **DigitalOcean Spaces** | **$5 flat** for 250 GiB storage and 1 TiB outbound transfer per account, then $0.02 per GiB stored and $0.01 per GiB out | S3-compatible. Supports S3 versioning (enable through the API; the control panel only shows the state) and lifecycle rules, including expiry of noncurrent versions. Managed by OpenTofu as `digitalocean_spaces_bucket`, so it sits inside the cost gate. The $5 is the whole bill for us; the daemons will store megabytes. |
| Backblaze B2 or Cloudflare R2 | $0 at this size: both offer about 10 GB free, R2 with no egress charge | S3-compatible, versioning available. Off-provider, so it is a second account to harden and a second set of keys in Doppler, and this repository would not manage it. The honest answer when the $5 does not fit. |
| Stay on the droplet's disk | $0 | What section 7 of the first draft assumed. Loses "disposable droplet" and makes the backup job carry the whole load. |

Recommendation: a Spaces bucket in the same region, versioning on, a lifecycle rule that expires noncurrent versions after 90 days, one bucket with a prefix per daemon, and one Spaces key per daemon with access to its prefix only (keys in Doppler, never in state). Access is outbound HTTPS to the Spaces endpoint, which the baseline firewall already allows.

## 4. Sizing and cost

Steady state, from the table in section 2: five Python pollers mostly idle, one Node process, Portainer, Docker Engine and Ubuntu 24.04. Adding the compose reservations and the estimates gives roughly 1.2 to 1.6 GB resident, with bursts when solarstorm_scout renders a chart, penguin-overlord sweeps its feeds, or Boon-Tube-Daemon starts. The sum of the compose limits is about 3 GB, which is only reached if everything spikes at once. CPU is negligible between polls (Stream-Daemon reports under 1 percent idle and about 5 percent during a check).

Prices are the repository's own table (`docs/cost-prices.json`, DigitalOcean sizes API, retrieved 2026-10-10). Stage 1 is $12 and stages 2 and 4 are planned to add $0 to the cloud bill (logs and Grafana run on-prem), so stage 3 is the only remaining paid stage.

| Option | Size | Droplet | Running total | Headroom under $30 | Notes |
|---|---|---|---|---|---|
| A: thin | `s-1vcpu-2gb` (1 vCPU, 2 GB, 50 GB SSD) | $12 | $24 | $6 | Enough memory with limits enforced; one shared vCPU means a chart render and a feed sweep queue behind each other. Could add weekly backups ($2.40) and stay under the ceiling. |
| B: fit | `s-2vcpu-2gb` (2 vCPU, 2 GB, 60 GB SSD) | $18 | $30 | $0 | The first draft's pick, and still the floor if state stays on the host. Second vCPU for the bursts, memory limits set on every container, swap off. Spends the whole ceiling; backups stay off. |
| C: comfortable | `s-2vcpu-4gb` (2 vCPU, 4 GB, 80 GB SSD) | $24 | $36 | needs a new ceiling of $40 | No memory pressure, room for a sixth daemon. Only if the ceiling is raised on purpose. |

With the Spaces bucket from section 3b ($5 flat) and the Functions from section 3a (expected $0 within the free allowance; cents if not):

| Option | Droplet | Spaces | Functions | Running total | Fits $30? |
|---|---|---|---|---|---|
| **A + bucket** | $12 | $5 | $0 | **$29** | **Yes.** The one combination that gives a disposable host, versioned state and a backup layer inside the ceiling. Once the runners and solarstorm_scout are Functions, the droplet carries the bot, the bridge and three light pollers, which is what 1 vCPU is for. |
| B + bucket | $18 | $5 | $0 | $35 | No; needs a $40 ceiling. |
| C + bucket | $24 | $5 | $0 | $41 | No; needs a $45 ceiling. |
| A + off-provider bucket | $12 | $0 (B2 or R2 free tier) | $0 | $24 | Yes, but with a second provider account outside this repository. |

This changes the recommendation. The first draft said B at $30. With state off the host, the thin droplet is enough and the $6 of headroom is better spent on the bucket than on a second vCPU: a disposable host with versioned state recovers from a bad day in minutes, while a second vCPU only makes a bad day slightly faster. **Recommended: A + Spaces bucket, $29.** If the daemons stay fat (section 6a not done) then B is the floor and the bucket pushes the ceiling to $40.

Things that are not in those numbers:

- **Backups.** DigitalOcean's own pricing page (read 2026-10-11) confirms weekly backups at 20 percent and daily at 30 percent of the droplet price, so `backups_fraction` in the price table can be marked verified. On option B weekly backups would be $3.60 and break the ceiling. Section 7 argues that once state lives in a versioned bucket with a copy off the account, an image backup of the droplet protects nothing that is not already protected.
- **Bandwidth.** Pooled across the account; the pollers move a few KB per check and the bridge relays chat text. Attachments are fetched by the homeserver, not the bridge. Far below the included transfer. Overage is reported by third parties at $0.01 per GiB; not verified against an official page.
- **Block storage.** Not needed: state is a few megabytes of JSON and SQLite and lives in the bucket or on the droplet's SSD. If a volume is ever wanted, `digitalocean_volume` must be priced and added to the cost gate's allowlist first.
- **Functions overage.** An estimate of the runs in section 3a lands around the 90,000 GiB-second allowance; going over costs $0.07 per GiB-hour, so a bad month is under a dollar. It is a usage charge the cost gate cannot predict, so it is recorded as a line to watch, not a line to approve.
- **Vendor free tiers.** Portainer CE is free. Doppler's free tier limits (projects, service tokens) still need checking against the number of daemons and functions, which this design multiplies; the roadmap's "not yet verified" list carries this already.

Decision needed: A plus the bucket at $29 (recommended), B alone at $30 with state on the host, or a raised ceiling for B or C plus the bucket.

## 5. Network and access design

The pattern is the one stage 1 established, applied to a third droplet.

### 5.1 Firewall

A new tag, `cah-workload`, and a new firewall attached by that tag, in addition to the baseline firewall the droplet also carries.

Inbound, all sourced from the **connector tag**, never an address:

| Port | Why |
|---|---|
| TCP 22 | SSH over Twingate, as the stage 1 guide's section 7 predicted |
| TCP 9443 | Portainer's HTTPS UI |
| bridge appservice port | Not from the connector tag. See section 5.4: the sender is the etke.cc homeserver, which cannot be a Twingate client, so this is the one rule that needs an explicit decision. The port number is the one in the generated config; read it at build time, do not copy it from this document |

Outbound: the firewall module's five defaults (tcp 443, 80, 53; udp 53, 123). Every API in section 2 is HTTPS on 443. The connector firewall's `tcp 30000-31000` and `udp 1-65535` rules are **not** copied to the workload tag; the wiki already promises that.

Docker publishes container ports by editing the host's iptables, which bypasses host firewalls such as ufw. That does not matter here because the DigitalOcean cloud firewall sits outside the droplet, but the compose files should still bind every published port to the droplet's private VPC address, never `0.0.0.0`, so a mistake in the cloud firewall is not immediately an exposure.

### 5.2 Twingate resources

Each is one private address and one port, granted to one group:

| Resource | Port | Group |
|---|---|---|
| `workload-tor1-host-ssh` | TCP 22 | `cah-tor1-admins` |
| `workload-tor1-portainer` | TCP 9443 | `cah-tor1-admins` |
| (none for the bridge) | n/a | The homeserver is a managed service and cannot run a Twingate client, so the bridge is not a Twingate resource. Its inbound path is section 5.4's decision |

No resource for the Docker API, ever. Portainer talks to Docker over the local socket.

### 5.3 The host

A new module, `modules/docker-host`, built from the connector module's cloud-init with the Twingate parts removed and these added:

- Docker Engine and the compose plugin from Docker's apt repository, with the signing key checked against a pinned fingerprint before it is trusted, the same way the Twingate key is. Not `get.docker.com | sh`, for the reason on the lessons page.
- A `/etc/docker/daemon.json` with `"live-restore": true`, `json-file` logging with size caps, and no `hosts` entry (socket only).
- Portainer CE as a compose stack owned by cloud-init, bound to the VPC address on 9443, with its data in a named volume.
- The same hardening as the connectors: one user, keys only, unattended upgrades with a reboot window that does not collide with the connectors, chrony, sysctl drop-in.
- Memory limits in every compose file, and no swap.

Unattended upgrades will restart the Docker daemon when it is updated; with `live-restore` the containers keep running through it. Portainer CE updates itself only when its stack is redeployed, so pin its image tag and bump it in a pull request.

### 5.4a Update: the homeserver is hosted by etke.cc

The homeserver is a managed Matrix server at etke.cc, not something this environment runs. etke.cc offers a bridge of its own, which is the alternative to section 5.4's self-hosted one.

What was read on 2026-10-11 from etke.cc's own pages (https://etke.cc/bridges/ and https://etke.cc/help/bridges/mautrix-discord/):

- They install and support a Discord bridge on the customer's server, **powered by mautrix-discord**, available pre-installed or added to an existing server. They do not list matrix-appservice-discord. A price is not stated; the services page says everything beyond the base service is an optional add-on, so the order form decides.
- Their guide uses a **bot token** (`login-token bot <token>`) and bridges a guild with `guilds bridge GUILD_ID --entire`. It warns that QR-code login is a self-bot, which Discord forbids. This corrects the first draft of section 9, which said `mautrix/discord` works only by signing in as a user account.
- Messages from Matrix users who have not logged in to the bridge go out through a **relay** login (`bridge.relay.enabled` in the bridge config, then `set-relay` per room; `admin_only` defaults to true). Per the mautrix general relay documentation, relayed users' messages get a display-name prefix and their reactions are not bridged. Whether etke.cc enables or lets the customer configure relay mode was not found and has to be asked.

It is therefore two-way, but not the same behavior as `matrix-appservice-discord`:

| Aspect | matrix-appservice-discord (the old bridge) | mautrix-discord from etke.cc |
|---|---|---|
| Runs | where we host it | on the etke.cc server, managed |
| Discord login | a bot, with guild-owner consent | a bot token (recommended); user-token and QR login exist but are self-bot territory |
| Matrix to Discord | per-user webhooks | relay login with a name prefix, unless the user logs in |
| Existing room plumbing | supported | different model (portal rooms); mappings do not carry over |
| Reactions from relayed Matrix users | bridged | not bridged |
| Maintenance | stale since 2023 | active |

The existing bridge's room mappings live in its own database, so moving to the hosted bridge means re-bridging each channel. History already on the Matrix side stays where it is.

**Test whichever bridge is chosen before moving anything.** Bridge one spare channel and one spare room and check: Discord messages arrive with the right sender; a Matrix message appears on Discord with a readable name; replies, edits and attachments work; reactions behave as needed.

Choosing etke.cc's bridge removes the need for any of section 5.4: no inbound rule, no bridge database to back up, no image to build. Choosing the self-hosted bridge means doing all of it, and gives control of relay mode and the update schedule. The operator's stated lean (2026-10-11) is to self-host, to keep a cheap host in use, to avoid dependence on a managed add-on, and to share the module and the lessons with others.

### 5.4 The self-hosted bridge: mautrix-discord

Facts below are from docs.mau.fi (the general Go-bridge pages and the mautrix-discord pages), read 2026-10-11. The docs are written for people hosting the bridge themselves.

**Software.** `mautrix-discord` is a Go program, so there is no Node runtime and no npm dependency tree in the container. It is actively maintained, which the old Node bridge was not. Source builds need Go 1.25 or newer (`./build.sh`; `-tags goolm` replaces libolm with a pure-Go implementation, `-tags nocrypto` removes encryption). The image is published at `dock.mau.dev/mautrix/discord`; `:latest` points at the latest commit, not the latest release, so the compose file pins a version tag, and the digest once chosen. The image mounts its working directory at `/data` and changes ownership of it to UID 1337.

**Setup order, from the docs.** Run the container once and it writes a config file; edit the config (inside Docker, use container names, not `localhost`); run it again to generate the registration file; register that file with the homeserver; start the bridge; log in. The Discord bridge still uses the legacy config layout, so its example config is copied to `config.yaml` by hand.

**Database.** The general setup page says a PostgreSQL server, version 16 or newer, and warns never to share a database between unrelated programs. The initial-config page says SQLite is fine for small instances. The two pages do not agree, so the design uses Postgres in its own container with its own volume, the documented path, and the first build checks the bridge's example config before settling it.

**Settings to fix before the first login**, because the docs say they cannot be changed properly afterwards: backfill (`bridge.backfill`), and end-to-bridge encryption (set it up before logging in; existing rooms cannot be switched to encrypted properly). Double puppeting (`double_puppet.secrets`) is strongly recommended. Relay mode (`bridge.relay.enabled`, then `set-relay` per room; `admin_only` defaults to true) is what lets Matrix users who have not logged in send to Discord; relayed messages carry a display-name prefix and relayed reactions are not bridged.

**Login.** A bot token only: create a Discord application, enable the privileged intents, send `login-token bot <token>` to the bridge bot, add the bot to the guild with the `bot` OAuth2 scope, then `guilds bridge GUILD_ID --entire`. QR and user-token login are self-bot territory and are not used.

**The inbound problem.** Registration files are consumed only by the homeserver. The homeserver pushes every event to the bridge's `appservice.address` over HTTP, and the bridge calls the homeserver's client API in return. With the homeserver at etke.cc, this environment cannot require Twingate on that path, because a managed Synapse cannot run a Twingate client. Two ways through, to be decided with etke.cc:

1. **One narrowly scoped public rule.** The workload firewall admits one TCP port from etke.cc's homeserver address only, with TLS in front of the bridge. It is this environment's first public inbound rule, so it needs the threat model, the wiki and the cost gate's expectations updated in the same pull request, and an address that etke.cc commits to keeping (to ask).
2. **A private path from etke.cc**, if they offer one (to ask). Nothing was found in their public pages.

A second thing to ask etke.cc: registering an external application service means adding the registration file to Synapse's `app_service_config_files` and restarting Synapse, which on a managed server only they can do. Their site mentions custom development and bridge installation, not external appservices. If they will not do it, the alternative is their own bridge (section 5.4a).

**What this changes elsewhere.** The workload firewall, the Twingate section, the threat model and the roadmap all gain the bridge; the cost does not change (it shares the droplet), though Postgres adds roughly 50 to 100 MB of memory, which section 4's range already absorbs.


### 5.5 Reaching Ollama

Every daemon's AI feature defaults to a local Ollama server. From the cloud that is a cloud-to-home connection: a Twingate headless client on the droplet with a service account, reaching one resource (the Ollama host and port). That is stage 2's design and its risk (a compromised droplet with a path home). Until stage 2 is built the cloud daemons run with `LLM_ENABLE` off or on Gemini. The daemons post without the AI text when the LLM is unreachable, so this degrades, it does not break.

## 6. Secrets

Rule from stage 0: every secret lives in Doppler and nothing in this repository is a credential. Applied here:

- **The droplet** gets the same inputs as a connector (admin key, reboot window) from the stack. It gets **no** application secret in its user-data. User-data is readable from the metadata endpoint and ends up in state (threat model T5 and T6); the connector tokens are an accepted risk there, and this stage should not widen it with five more tokens.
- **Each daemon** keeps its own Doppler project and config, as today, with one read-only service token per daemon. The compose file carries only `DOPPLER_TOKEN` as a variable, and that value is entered once in Portainer's stack environment over Twingate. Portainer stores it in its own database on the droplet, which is the same trust level as the daemon's own memory.
- **The bridge** has no Doppler client. Its `config.yaml` holds the Discord bot token, the database password and the homeserver URL, and `registration.yaml` holds the appservice tokens (`as_token` and `hs_token`, which the homeserver needs and the bridge does not read at runtime). Both files are rendered from Doppler by a small systemd oneshot on the host before the stack starts, and the registration file's secret copy lives in Doppler, so neither is ever in this repository, Portainer or the bucket. Regenerating the registration changes the tokens and means asking etke.cc to reload it, so it is stored, not re-derived.
- **Portainer's own admin password** is set on first visit over Twingate and stored in the password manager. Portainer's UI is a second factor away from the internet already (Twingate sign-in through the identity provider), and the admin account should still be strong and unique.

What goes into `.spacelift/config.yml` for the new stack: `DIGITALOCEAN_TOKEN`, `TWINGATE_API_TOKEN`, `TWINGATE_NETWORK`, the admin SSH values, and nothing from the daemons. Spaces access keys are created by the stack (`digitalocean_spaces_key`, one per daemon, scoped to its prefix) and land in state, which is the same accepted risk as the connector tokens; or they are created by hand and stored in Doppler, keeping state clean at the cost of a manual step. The guide should pick the second until Spacelift state access is restricted.

### 6a. Cloud-optimized install: what each daemon needs

The daemons were written for one Docker container on a Raspberry Pi: a writable disk that is always there, one process that never exits, config in a `.env` file next to it. None of that is true of a disposable droplet or a function. The changes below are small, and four of the five daemons share the hypeman-social library, so most of them land once and reach four projects.

Common, in hypeman-social or each daemon's config layer:

1. **A state backend behind the existing file calls.** `STATE_BACKEND=file` (default, unchanged for the Pi) or `STATE_BACKEND=s3` with `STATE_S3_BUCKET`, `STATE_S3_PREFIX`, `STATE_S3_ENDPOINT` and the key pair. Load at start, save after each cycle, conditional write (`If-Match` on the ETag) so two overlapping runs do not clobber each other. The files stay JSON; nothing about their shape changes.
2. **A `--once` mode** that runs one check cycle and exits 0 (or non-zero on failure), next to the existing loop. That is the whole difference between a daemon and a function body. The penguin-overlord runners and solarstorm_scout already are this.
3. **Configuration only from the environment.** Everything already supports `DOPPLER_TOKEN` and `.env`; the change is to stop assuming `.env` exists and to stop writing anything next to the code. Scratch files go to `/tmp` or `tempfile`.
4. **Exit on signal.** Handle `SIGTERM` by finishing the current post and saving state, so a container stop or a function timeout does not lose the cycle.
5. **Logs to stdout** as one line per event. No log files on disk; the Docker `json-file` driver and the Functions log viewer do the retention.
6. **Health that means something.** Keep the `/healthz` endpoints, but make them check the last successful cycle time against the interval, so a stuck loop reads as unhealthy. Stage 4 scrapes these.
7. **Smaller images.** Boon-Tube-Daemon's image is 652 MB; a slim base and a two-stage build should bring every daemon under 200 MB, which matters on a 2 GB host that pulls six of them.

Per daemon:

| Daemon | Already has | Needs |
|---|---|---|
| penguin-overlord | Runners as one-shots; Doppler; Prometheus exporter; compose memory limits | S3 state for `data/*.json`; the runners packaged for Functions (`project.yml`); bot stays a container |
| solarstorm_scout | One-shot mode; cron examples; Doppler | S3 state if it ever keeps any; a measured function build under 48 MB (numpy is bundled, the chart renderer's imaging dependency is the question) |
| Boon-Tube-Daemon | Health endpoint; Doppler; Matrix token rotation | `--once`; S3 state for `youtube_state.json` and the Matrix session; slimmer image; memory limit in compose |
| Stream-Daemon | Health endpoint; Doppler; small footprint | Persist the live-stream flag and Discord message ids (the README already lists Redis or SQLite as planned; the bucket is the cheaper answer); then `--once` |
| Star-Daemon | Doppler; named volume for state; compose limits | S3 state for the star list; `--once` |
| mautrix-discord | Nothing of the above; third-party Go program with its own config | Stays a container with its own Postgres container; its backup is a nightly `pg_dump` copied to the bucket (section 7). Pin the image to a version tag and update by pull request, not by `:latest`. |

None of this is required to run the daemons on the droplet on day one; they run as they do on the Pi, with state in named volumes. It is required before the host can be treated as disposable and before anything moves to Functions, and it is the work that makes the $29 option honest.

## 7. State, backups and recovery

The user's rule is "several backups", and the data is almost all small text. The layers, cheapest first:

| Layer | What | Cost | Protects against |
|---|---|---|---|
| 0: git and Doppler | Compose files, cloud-init, function code, every secret | $0 | Losing the droplet, Portainer or a laptop. Everything is rebuilt from these two. |
| 1: the bucket itself | Each daemon reads and writes its state in Spaces; the bridge database is dumped there nightly with `pg_dump` | in the $5 | Losing the droplet. A new droplet pulls state on first start. |
| 2: versioning on the bucket | S3 versioning on, noncurrent versions expire after 90 days by lifecycle rule | in the $5 | A daemon writing bad state, an accidental delete, a bug that truncates a file. Restore is "copy the previous version back". |
| 3: a copy off the account | Nightly `rclone sync` of the bucket to the homelab over Twingate (stage 2), or to a free-tier bucket at a second provider | $0 | The DigitalOcean account itself (token theft that deletes, billing lockout, region loss). This is the one layer the account cannot provide for itself. |
| 4: droplet backups | DigitalOcean weekly image backups | 20 percent of the droplet | Not needed once layers 1 to 3 exist: the droplet holds nothing that is not in git, Doppler or the bucket. Off. |

What each thing loses, and how it comes back:

| Data | Lives in | If lost |
|---|---|---|
| Daemon state (JSON dedup windows, star list, YouTube state, Matrix session) | The bucket (layer 1), versioned (layer 2), copied off (layer 3) | Restored from a previous version or the off-account copy. Worst case without any of them: a burst of duplicate posts for one cycle; Star-Daemon resyncs within a day. |
| Stream-Daemon state | Memory today; the bucket after section 6a | Already lost on every restart by design, until it is moved. |
| Bridge database (Postgres) | Named volume on the droplet; nightly `pg_dump` to the bucket (an inference, not a documented procedure: docs.mau.fi has no backup page) | Up to a day of room mappings, ghost users, logins and, if encryption is on, the bridge's encryption state. The docs say nothing about restoring that state, so treat encrypted rooms as at risk beyond the last dump; older than the dump means re-bridging each channel and logging in again. A restore test belongs in the operator guide. |
| Bridge `config.yaml` and `registration.yaml` | Doppler (secret copies), rendered to the host at start | Re-rendered from Doppler. The registration file is stored, not regenerated: new tokens would mean etke.cc reloading it. |
| Portainer database | Named volume | Re-enter five tokens and redeploy six stacks from the compose files in git. Twenty minutes, and Portainer's own backup export can go to the bucket too. |
| The droplet | Spacelift | Replace through a run, as the connectors are. Cloud-init rebuilds it, Portainer redeploys the stacks, the daemons pull their state from the bucket. |

Until stage 2 exists, layer 3 is the free-tier bucket at a second provider or nothing. The bridge database has a copy in the bucket (layers 1 and 2) but no copy off the account until layer 3 exists, and that is a risk to accept in writing or a reason to wait. Take a restore test of the `pg_dump` before the bridge is relied on.

## 8. Kubernetes: not yet, and what would change that

The roadmap lists Kubernetes under "explicitly not planned (yet)". The reason is cost, not objection:

- DigitalOcean Kubernetes has a free control plane but the smallest sensible node is the $24 droplet, and a second node for any kind of resilience doubles it. That is the whole ceiling for the same six containers.
- k3s on this one droplet is possible later at $0 extra, but it is the same box with an API server, etcd and a scheduler eating a few hundred megabytes of a 2 GB machine, and a 4 GB droplet to carry that comfortably is option C.

What this stage does so that the move stays cheap when it comes:

- One image per service, configuration only from the environment and Doppler, state in the bucket (or, before section 6a, in named volumes). A compose service shaped like that is a Deployment with no volume at all, which is the easiest kind to schedule anywhere; and a one-shot with a cron trigger is a CronJob or a Function with the names changed.
- No reliance on Portainer-only features (its stack editor is fine; its agent, edge or RBAC are not needed).
- The firewall and Twingate pattern (tag per role, one resource per port) is the same whether the thing behind the port is a container or a Service.

Triggers to revisit: the ceiling is raised past $40, a workload needs more than one host, or a second person starts operating this environment and wants declarative rollouts more than a web UI.

## 9. Known risks and decisions

Facts checked 2026-10-11 and decisions this document asks for.

1. **matrix-appservice-discord is stale and is not used.** Its last release is 4.0.0 from 2023-09-15 and its Node 18 to 20 runtimes are past end of life. The self-hosted bridge is `mautrix-discord` (Go, maintained, bot-token login), chosen on 2026-10-11 partly to avoid Node. Differences from the old bridge are in section 5.4a; existing room mappings do not carry over, so each channel is re-bridged.
2. **How does the etke.cc homeserver reach the bridge** (section 5.4)? Open, with two questions for etke.cc: can they reload an external appservice registration, and do they offer a private path or a fixed source address. Fallback: etke.cc's own bridge (section 5.4a).
3. **A plus the Spaces bucket at $29, B alone at $30, or a raised ceiling** (section 4). The draft recommends A plus the bucket, which depends on the cloud-optimized install work in section 6a being done for at least the state backend.
3a. **Spaces at $5 or a free-tier bucket at a second provider** (section 3b). Spaces keeps everything in one account and inside the cost gate; B2 or R2 is free at this size but is a second account and outside this repository.
3b. **Which jobs become Functions first** (section 3a). The draft says the penguin-overlord runners and solarstorm_scout, with Boon-Tube and Star-Daemon following once they have a `--once` mode and bucket state. Functions are deployed by `doctl`, not OpenTofu, so they live in each daemon's own repository and outside the cost gate.
4. **Portainer's Docker socket is root.** Anyone who can sign in to Portainer can run a privileged container on the host. Mitigation: Portainer only over Twingate to the admins group, a strong local admin, and no public inbound. Accept and record in the threat model.
5. **Bridge database backup before stage 2** (section 7): a nightly `pg_dump` to the bucket with a tested restore, and no off-account copy until layer 3 exists. Accept or wait.
6. **Portainer CE git stacks.** CE can deploy a stack from a git repository; automatic polling for updates is a Business feature as far as the public docs say. Verify, then decide whether compose files live in this repository (public, no secrets in them) or in Portainer alone.
7. **Price table.** Mark `backups_fraction_verified` true (20 percent weekly confirmed on DigitalOcean's pricing page), keep bandwidth overage and block storage as unverified.

## 9a. What is code, and where it lives

Everything in this stage is defined in a file that is reviewed in a pull request. Not all of it can be applied by OpenTofu through Spacelift, and the table says which is which rather than implying it.

| Piece | Defined in | Applied by | Seen by the cost gate | Why not OpenTofu, if not |
|---|---|---|---|---|
| Workload droplet, tag, firewall, cloud-init | `modules/docker-host`, `stacks/30-workloads` (OpenTofu) | Spacelift, human confirms | Yes | |
| Docker Engine and Portainer CE on the host | the module's cloud-init template (OpenTofu renders it) | Spacelift, via the droplet's first boot | Yes (part of the droplet) | |
| Spaces bucket, versioning, lifecycle rule | `stacks/30-workloads` (OpenTofu) | Spacelift | Yes, as a flat `spaces` entry | |
| Spaces access keys, one per daemon | `stacks/30-workloads` (OpenTofu) or by hand into Doppler | Spacelift, or the operator | Free either way | Choice: keys in state (same accepted risk as connector tokens) or a manual step and clean state. The draft leans manual until Spacelift state access is restricted. |
| Twingate group and resources (SSH and Portainer) | `stacks/30-workloads` (OpenTofu) | Spacelift | Free | |
| The daemon compose stacks inside Portainer | compose files in git, no secrets in them | Portainer, pulling from git (CE git stacks, to verify) or deployed once by hand over Twingate | No; nothing in them costs money | Spacelift cannot reach Portainer's API or the Docker socket, because both are reachable only through Twingate by design. A Portainer or Docker provider would need an inbound path that this environment refuses. |
| Per-daemon `DOPPLER_TOKEN` values in Portainer | Doppler | Operator, once, over Twingate | No | A secret, so it must not pass through OpenTofu state or user-data. |
| DigitalOcean Functions and their cron triggers | `project.yml` in each daemon's repository | `doctl serverless deploy` from a GYST workflow, token from Doppler | **No**; recorded in `docs/cost.md` as a watched usage line | The DigitalOcean provider has no resource for standalone Functions or triggers; App Platform function components have no scheduled triggers. Lambda later closes this gap (section 3a). |
| The daemons' code changes (state backend, run-once mode, slimmer images) | each daemon's repository | its own CI and image publish | No | Application code, not infrastructure. |
| The bridge's `config.yaml` and `registration.yaml` | rendered from Doppler on the host by a systemd oneshot | the host, before the stack starts | No | Contain secrets; never in a repository, in Portainer or in the bucket. |
| Backups: nightly `rclone sync` of the bucket off the account, nightly `pg_dump` of the bridge database | the module's cloud-init (systemd timer units) | Spacelift, via the droplet | Free, apart from any second provider's bill | |

## 10. Changes this stage makes to the repository

Not an implementation plan; the list of what the plan will have to touch.

- `modules/docker-host/`: droplet, cloud-init, tests. No Twingate connector in it.
- `stacks/30-workloads/`: tag, firewall (`inbound_from_tag_rules` with the connector tag as source), the module, Twingate resources and group, the Spaces bucket with versioning and a lifecycle rule, and `cost.json` with one `s-1vcpu-2gb` droplet and one `spaces` entry.
- `docs/stages/approved.json`: stage 3, approved total $29.00 (option A plus the bucket), `modules/docker-host/main.tf` added to `allowed_sources` for `digitalocean_droplet`, and `stacks/30-workloads/main.tf` for `digitalocean_spaces_bucket`.
- `docs/cost-prices.json`: a `spaces` entry at $5.00 flat, and `backups_fraction_verified` set to true with the date.
- `scripts/cost_check.py`: today it counts `twingate-connector` module blocks and demands they equal the droplet entries in the manifests, and it prices only droplets. It needs to count every costed module (connector and docker-host) with the same "no `count` or `for_each`" rule, to price a `spaces` manifest kind as a flat amount, to allow `digitalocean_spaces_bucket` (and the bucket's CORS, policy and lifecycle companions, which are free) only in the listed source, and `tests/test_cost_check.py` updated to match. Functions stay outside the gate and are recorded in `docs/cost.md` as a watched usage line.
- `.spacelift/config.yml`: stack `cah-30-workloads` with its Doppler names.
- `docs/stages/03-workloads.md`: the operator guide (decisions, bootstrap, verify, rollback), including the Portainer first-visit steps and the per-daemon Doppler token entry.
- Wiki: roadmap, cost, threat model (Docker socket, bridge inbound), glossary. Done alongside this draft.
