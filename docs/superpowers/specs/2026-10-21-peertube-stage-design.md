# Clouds Against Humanity: PeerTube

Status: DRAFT for review. Date: 2026-10-21. Issue: #121 (epic #72). Builds on: [2026-10-19 edge DMZ design](2026-10-19-edge-dmz-design.md), section 8.2, and the [stage 3 design](2026-10-11-stage-3-workloads-design.md).
Tooling: OpenTofu throughout.
Scope: whether and how a public, federated PeerTube video platform could run in the reference environment, what it needs, what it costs in three shapes, what it adds against the ceiling, and whether the project should instead teach it as a lesson without running it. This is a design, not an approval. Nothing here costs money, changes a stack or moves a ceiling until the maintainer picks an option in section 6 and approves it. It also contains no legal advice: section 8 describes duties at a high level and a lawyer decides.

Vendor facts below carry a URL and the date they were read (2026-10-21). Anything I could not verify is marked UNVERIFIED and carries no number; anything I estimated is marked "est.". Facts from the repository's own tables carry the table's retrieval date. Section 12 lists what is still open.

## 1. Purpose

Decide, with numbers, between three things: teach PeerTube as a learner lesson only; run it in the reference environment small; run it in the reference environment with local transcoding. The recommendation is in section 11.

Goals:

- A costed answer against the `approved.json` ceilings and the $60 `hard_max`.
- A public listener that is never on the connector droplets and never widens the zero-inbound core.
- An honest account of the duties a public video host takes on, so the cost is not only dollars.

Non-goals:

- Live streaming. It needs a separate ingest listener and more CPU; it stays off in every option here.
- Choosing a domain, a mail provider or a legal structure.
- Building anything. No stack, module or JSON is changed by this document.

## 2. What exists today

Read from the repository on 2026-10-21:

- Core is `00-foundation` and `10-access`: one VPC and two Twingate connector droplets at $6 each. Inbound is denied by a tag-based Cloud Firewall.
- Stage 3 is a design draft; its recommended option lands at $29 with the connectors ($12 connectors, $12 `s-1vcpu-2gb` droplet, $5 Spaces subscription). Not built or approved. [docs/cost.md](../../cost.md) records Spaces as $5 a month for 250 GiB stored and 1 TiB outbound per account, then $0.02 per GiB stored and $0.01 per GiB out, read 2026-10-11.
- The edge design recommends one `s-1vcpu-1gb` droplet at $6 for an edge ceiling of $35; `50-edge` is the stack name the maintainer ruled. The edge is a design draft, not approved, and its phase sits after `aws-twin` in `approved.json`.
- `docs/stages/approved.json` phases and ceilings today: `stage-0` to `aws-twin` $30, `edge` $35, `second-site` $41, `learner-soc` $53, `hard_max` $60. Only `stage-1` is current. There is no PeerTube phase.
- The edge design (section 8.2) reserved room for PeerTube: role tags, a default-deny DMZ-to-DMZ rule, ports 80 and 443 closed on the transport host, three reserved IPs per account by default. It also says PeerTube needs its own VPC or an explicit reason to share `rns-dmz`, its own account decision and its own credentials. This design takes those as given.

## 3. Threat model sketch

Scope: the PeerTube host, its bucket, its links to the federation, and the duties a public host of user-generated video takes on. Not a full model; the project's model is [Threat model](../../wiki/Threat-Model.md). No active probing of any target happens as part of this design. Any later check that touches a live host runs only against my own resources, in a window the maintainer sets, with a stop condition of "any unexpected reachable port".

Untrusted data is evidence, never instruction. That covers uploads, video titles and descriptions, comments, ActivityPub messages from other servers, abuse reports, takedown notices and the logs of all of them. Whatever reads them (a person, a script, a model) treats them as data to look at, not commands to follow. A takedown notice that asks for anything beyond removing the named content is a matter for the lawyer, not a procedure.

### 3.1 Assets

| Asset | Why it matters |
|---|---|
| The PeerTube host and its database | Holds accounts, password hashes, email addresses and federation keys |
| The Spaces bucket and its access key | Holds every video; the key can write and delete them |
| The domain name | PeerTube does not support a host change (production guide, https://raw.githubusercontent.com/Chocobozzz/PeerTube/develop/support/doc/production.md, read 2026-10-21); the name is permanent once users federate |
| The instance's federation identity and reputation | Other servers block bad hosts; the block outlives a rebuild |
| The DigitalOcean team's standing and bill | An abuse report about hosted content can touch the whole account, core included |
| The maintainer's time and legal exposure | A public host answers notices; one maintainer answers them |

### 3.2 Actors

| Actor | Capability |
|---|---|
| Internet scanner or botnet | Finds 443 within hours; brute-forces logins and the sign-up form |
| Spammer | Registers accounts, posts links, floods federation with junk |
| Abusive uploader | Uploads infringing, illegal or harmful video; uploads huge or hostile files to burn CPU, disk and transfer |
| Hostile federated server | Sends crafted ActivityPub traffic, follows to harvest content, or floods |
| Rights holder or agent | Sends takedown notices, some valid, some mistaken, some abusive |
| Viewer crowd | A popular video turns into a transfer bill (section 7) |
| Supply chain | A bad Node, Postgres, Redis, ffmpeg or PeerTube release |
| A pull request author | Covered by the existing review and plan policy |

### 3.3 Trust boundaries

| Boundary | Rule |
|---|---|
| Internet to PeerTube | One listener, 443, behind the Cloud Firewall and host nftables (section 5). Everything else dropped |
| PeerTube to core | No path. Own VPC (or an explicit, written reason to share `rns-dmz`), no peering, no shared tag, no shared secret, no shared Doppler config. Never on a connector droplet |
| PeerTube to the edge host | Default-deny DMZ-to-DMZ. The two public hosts do not talk |
| PeerTube to its bucket | One access key scoped to its own buckets, in Doppler, never in user-data beyond the bootstrap pattern the edge design uses |
| PeerTube to home | Only if remote runners are chosen (option P1). The runner processes hostile uploaded files, so it is the exposed parser moved, not removed. Outbound-only connectivity gives no process or network isolation, so P1 requires a disposable, isolated runner: a VM or container rebuilt from code on a schedule, on its own VLAN or host with no route to the LAN, no home credentials, no Twingate or Doppler identity, no mounted shares, and egress limited to the PeerTube site and the bucket. Its only secret is a revocable runner registration token. A compromised runner can still alter video content (docs warning), so its output is not trusted more than an upload. Without that isolation, P1 is dropped and only P2 or L remain (risk 11) |
| Uploads to the host | Untrusted files reach ffmpeg. The transcoder is the most exposed parser (risk 3) |

### 3.4 Abuse cases

1. Bots fill the sign-up form and post spam and links.
2. An uploader posts infringing or illegal content and a notice or provider report follows.
3. A crafted upload exploits ffmpeg or the file parser.
4. A burst of large uploads pins the CPU and fills the disk, or queues transcoding jobs for hours.
5. One video goes viral and outbound transfer passes the allowance (section 7).
6. A hostile server floods inbox endpoints or follows to scrape.
7. Credential stuffing against admin or moderator accounts.
8. The bucket key leaks and every video can be deleted or replaced.
9. The provider acts on the team after an abuse report, and core goes down with it.
10. IPv6 is on and a v4-only rule set leaves the v6 side open.
11. A takedown notice is forged to remove a legitimate video.

### 3.5 Ranked risks

Ranked by impact times how easy the first step is.

| # | Risk | Mitigation | Verification |
|---|---|---|---|
| 1 | Illegal or infringing content hosted, notices unanswered, provider acts on the account (cases 2, 9, 11) | Closed or approval-only sign-up, new-video quarantine, ToS, an abuse inbox read on a schedule, a DMCA agent if the lawyer says so, the account-separation decision (decision 4) | Calendar item, not a test. A takedown drill on a test video before launch, written down |
| 2 | Account takeover of admin or moderator (case 7) | Few staff accounts, long unique passwords, two-factor if the installed version supports it (UNVERIFIED: I did not read the 2FA page), rate limits at nginx | Login attempt test against my own host from a scratch client; the stack test asserts the rate-limit config exists |
| 3 | Hostile upload hits ffmpeg or the parser (case 3) | Current releases only; the services run as an unprivileged user under systemd hardening; uploads capped by quota and size; transcoding offloaded (option P1) so the exposed parser is not on the public host; rebuild monthly | Version report; a quota test with an oversized file on my own host |
| 4 | Resource exhaustion by uploads (case 4) | Per-user quota, daily upload limit, transcoding concurrency limit, a disk alarm, video import from URLs off | Upload a capped file as a test user; read the queue; confirm the limit held |
| 5 | Transfer bill (case 5) | Watched usage line and billing alert set before the first apply (section 7), a bucket-only delivery path, a cache | The usage page after week one against the section 7 figures |
| 6 | Bucket key leak (case 8) | Key scoped to this account's own buckets, bucket versioning, a copy of the bucket off the account (section 9), rotation | Restore test (section 9) |
| 7 | Spam and federation flooding (cases 1, 6) | Email verification, registration approval, no automatic follow of other servers, manual approval of followers, a subscribed blocklist (PeerTube 8.3 or newer) | Admin settings review; a test registration |
| 8 | IPv6 left open (case 10) | Cloud Firewall and nftables written for both families | The existing `test_ipv6_closed.py` pattern extended to this stack |
| 9 | Supply chain or unpinned software | Pin by version and checksum; five components, each with its own pin | A test that fails on an unpinned package or image in the template |
| 10 | Pivot to core | Section 3.3; plan policy denying peering and core tags on these resources | Plan policy tests, as for the edge |
| 11 | Compromised home runner (hostile upload exploits ffmpeg there) | The isolated, disposable runner above; revoke the registration token; rebuild | A network test from the runner host that LAN and credential stores are unreachable; a token revocation drill |

### 3.6 Residual risk

A public site that accepts uploads from strangers will be spammed, scanned and sometimes abused. The design limits what an attacker gets (no path to core, no admin path to steal, a rebuild from code and a restore from backup as recovery). What it cannot remove: unlawful content reaching the host before a moderator sees it, a notice that needs a lawyer, an abuse action against the team, and a viral transfer bill. Those are why section 11 recommends not running it by default.

## 4. What PeerTube needs

Current release: v8.3.1, published 2026-09-28 (https://api.github.com/repos/Chocobozzz/PeerTube/releases/latest, read 2026-10-21).

Software, from the official dependencies guide (https://raw.githubusercontent.com/Chocobozzz/PeerTube/develop/support/doc/dependencies.md, read 2026-10-21):

- Node.js LTS, `>= 22.12 and < 25`.
- PostgreSQL `>= 14`. Some distributions ship an older one; the guide says to use the PostgreSQL project's own repository then.
- Redis `>= 6.2`.
- ffmpeg `>= 4.3`; a static ffmpeg build is not recommended.
- Python `>= 3.8`, a C++ toolchain, and, for the bare-metal path, nginx and certbot.

The production guide (https://raw.githubusercontent.com/Chocobozzz/PeerTube/develop/support/doc/production.md, 2026-10-21) provides an nginx configuration template and says only nginx is officially supported as the reverse proxy. A Docker production path also exists in the repository (`support/docker/production`); I did not read it closely. PeerTube listens on 127.0.0.1:9000 behind nginx in the template.

Object storage: any S3-API provider can hold videos after transcoding. The bucket should be public with a CORS rule allowing traffic from anywhere, live videos still sit on disk, and the docs "strongly recommend" a cache server or CDN in front of the bucket to reduce object-storage cost (https://docs.joinpeertube.org/admin/remote-storage, read 2026-10-21). Five kinds of object are kept separately: web videos, HLS streaming playlists, user exports, original video files and captions, in one bucket with prefixes or in several buckets. A private-ACL mode with PeerTube proxying files exists in the docs' OVH example (`proxify_private_files`); with it the bytes pass through the droplet. Whether DigitalOcean Spaces accepts the exact ACL and CORS setup PeerTube wants is UNVERIFIED: Spaces documents a CORS how-to and public file listing, but I did not test PeerTube against it, and that test is an approval prerequisite.

Sizing: this is where the docs are thin, and I will not invent a minimum.

- The docs I read state no minimum RAM, CPU or disk for a small instance.
- The only hardware figure is for scale: for about 1000 concurrent viewers on one video, "at least 4 CPU cores and 4GB of RAM" (https://docs.joinpeertube.org/maintain/configuration, Scalability, read 2026-10-21).
- On transcoding: "a transcoding job takes a lot of CPU, requires time and create an additional video file stored on your disk storage" for each resolution (https://docs.joinpeertube.org/admin/configuration, VOD transcoding, 2026-10-21). For many uploads the docs recommend object storage and remote runners to offload transcoding (maintain/configuration, "Many videos").
- So I cannot say a 1 or 2 GiB droplet is unrealistic, and I cannot say it works. Five processes share it (Node, PostgreSQL, Redis, nginx and ffmpeg while a job runs). It is a measurement to make before the cost is final, as the edge design requires for its droplet. Until measured, treat the 1 GiB droplet as not credible for this and the 2 GiB droplet as a hypothesis that holds only if transcoding is offloaded.

Remote runners (https://docs.joinpeertube.org/admin/remote-runners, 2026-10-21): PeerTube can hand VOD transcoding, studio transcoding, live transcoding, transcription and storyboard generation to a runner that requests, accepts and processes jobs and posts the result back. The runner pulls; PeerTube does not call it. The docs warn that registered runners can alter video content, so the runner's operator must be trusted. A runner at home makes transcoding CPU free and takes the parser off the public host, but it does not remove the risk: the runner still opens hostile uploads, and outbound-only connections give no isolation. It must therefore be a disposable, isolated runner with no home credentials and no LAN routes (section 3.3, risk 11), or P1 is not chosen. Whether the runner can reach files on a Spaces-backed instance with the exact bucket setup is UNVERIFIED.

Email: sign-up verification needs mail. DigitalOcean blocks SMTP ports 25, 465 and 587 on all droplets by default (https://docs.digitalocean.com/support/why-is-smtp-blocked/, 2026-10-21). The mail provider must be one with an HTTPS API or an alternate port; I did not select or price one.

Domain: PeerTube "does not support webserver host change" (production guide). Pick the name once.

## 5. Public exposure, and how it differs from the zero-inbound core

Core has zero inbound and is checked for it. PeerTube cannot have zero inbound: it is a public web service. The difference is bounded and written down:

- One public listener, TCP 443. Cloud Firewall allows 443 from anywhere and nothing else inbound; host nftables repeats it, for IPv4 and IPv6. No SSH, no connector and no admin path, as for the edge: a rebuild is the recovery.
- Port 80 closed. The production guide's certbot step uses the standalone method, which listens on port 80, and the template redirects 80 to 443. To hold 443 only, the certificate must come from a DNS challenge or a TLS-ALPN challenge, and the first needs a DNS-provider API token (a secret). That is a decision (decision 5): open 80 for redirects and the HTTP challenge, or hold 443 only and carry one more credential.
- The listener is on its own droplet in its own VPC (or in `rns-dmz` with a written reason), tagged by role, with default-deny DMZ-to-DMZ. Never on a connector droplet, and no firewall rule lets any public host reach a core tag.
- Outbound: 443 to other PeerTube servers (federation), to the bucket, and to the mail provider. Outbound policy follows the edge design's section 4.6.2.
- The zero-open-ports check keeps checking core. It does not apply to this stack, and the PeerTube stack gets its own check that the only reachable port is 443 (its own host, my own resources, a window the maintainer sets).
- Reserved IP: free when assigned, $5.00 a month when not (https://docs.digitalocean.com/products/networking/reserved-ips/details/pricing/, read 2026-10-19 in the edge design); three per account by default, the edge uses one. A second PeerTube address is the second of three.
- DDoS protection: layer 3 and 4 only, no charge; no layer 7 (edge design, section 9). A layer 7 flood against a PeerTube site is not covered.

## 6. Options and cost

Price sources: `docs/cost-prices.json` (DigitalOcean sizes API, regular droplets, retrieved 2026-10-10), the repo's recorded Spaces price (docs/cost.md, read 2026-10-11), and the DigitalOcean pages named per row, read 2026-10-21. Nothing here includes tax, domain or mail costs, or transfer overage.

Spaces is billed as one subscription per account that covers multiple buckets: "Each subscription allows you to create multiple Spaces buckets", 250 GiB across all of them, 1,024 GiB of outbound shared between all buckets, then $0.02 per GiB stored and $0.01 per GiB out (https://docs.digitalocean.com/products/spaces/details/pricing/, read 2026-10-21; page last verified 13 Jul 2026 by DigitalOcean). That matches what the repo recorded. Stage 3 already pays the $5 subscription, so PeerTube's buckets add $0 until the combined 250 GiB or 1 TiB is passed. If stage 3 is not built, the $5 is PeerTube's.

All "running" columns assume stage 3 option A ($29) is built. The "with edge" column adds the edge option A ($6). Backups are off in every row.

### 6.1 Option L: learner lesson only (recommended)

Run nothing. A lesson, issue and wiki page teach how to run PeerTube on the learner's own account, with this document's numbers, the checklist and the legal warning (section 10).

| Line | Basis | Monthly |
|---|---|---|
| Added | nothing runs | $0.00 |
| Running with stage 3 | $29 + $0 | $29.00 |
| Running with stage 3 and edge | $29 + $6 | $35.00 |

### 6.2 Option P1: small host, transcoding at home

| Line | Basis | Monthly |
|---|---|---|
| Droplet `s-1vcpu-2gb` | `docs/cost-prices.json` | $12.00 |
| Reserved IP, assigned | free when assigned (pricing page above) | $0.00 |
| Own VPC, Cloud Firewall, DDoS protection (L3 and L4) | free types in the gate / no additional charge (edge design, 5.1) | $0.00 |
| Spaces buckets | share the stage 3 subscription, within 250 GiB and 1 TiB; same account only (see 6.5) | $0.00 |
| Transcoding | a remote runner on a home machine | $0.00 |
| Added | | $12.00 |
| Running with stage 3 | $29 + $12 | $41.00 |
| Running with stage 3 and edge | $29 + $6 + $12 | $47.00 |

Postgres and Redis share the droplet. Whether 2 GiB holds Node, PostgreSQL, Redis and nginx with no transcoding is the measurement to make; the docs state no figure. Optional extras not in the number: droplet backups at 20 percent of the droplet cost (`backups_fraction` in cost-prices, https://docs.digitalocean.com/products/backups/details/pricing/) would be 0.2 x $12 = $2.40; I recommend the database dump in section 9 instead.

### 6.3 Option P2: mid host, transcoding on the droplet

| Line | Basis | Monthly |
|---|---|---|
| Droplet `s-2vcpu-4gb` | `docs/cost-prices.json` | $24.00 |
| Reserved IP, VPC, firewall, DDoS, buckets | as above | $0.00 |
| Added | | $24.00 |
| Running with stage 3 | $29 + $24 | $53.00 |
| Running with stage 3 and edge | $29 + $6 + $24 | $59.00 |

This is the smallest shape that has two vCPUs and 4 GiB, and it matches the docs' "4GB of RAM" scale figure on memory but not on cores (the docs say 4). It leaves $1 under the $60 `hard_max` with the edge. Backups at 20 percent would be 0.2 x $24 = $4.80; added to the edge row that is $59 + $4.80 = $63.80, which is $3.80 OVER the $60 `hard_max` and does not fit. Transcoding of a long upload still takes time on 2 vCPUs; the docs give no figure and I give none.

### 6.4 Rejected or priced for completeness

- P0, `s-1vcpu-1gb` at $6: running $35 (or $41 with the edge). Five processes in 1 GiB and ffmpeg in the same box has no support in the docs I read and I have no measurement. Not recommended.
- P1 plus a managed PostgreSQL cluster: single node begins at $15.00 a month with 1 GiB (https://docs.digitalocean.com/products/databases/postgresql/details/pricing/, read 2026-10-21; DigitalOcean's page was last verified 30 Sep 2026). Added $12 + $15 = $27, running $29 + $27 = $56, or $62 with the edge, which is over the $60 `hard_max`. It removes the stateful database from the droplet; section 9 gets the same effect for $0 with a dump.
- A block volume for the database: $0.10 per GiB per month (https://docs.digitalocean.com/products/volumes/details/pricing/, 2026-10-21), so 20 GiB is $2.00. It is billed attached or not. It keeps the database across a rebuild but adds another stateful thing to clean up.
- A bigger droplet (`s-4vcpu-8gb`, $48): $29 + $48 = $77, over `hard_max` $60. Not available without raising `hard_max`.

### 6.5 Same account or separate account

The $0 bucket line holds only if PeerTube runs in the same DigitalOcean account as stage 3, because the $5 subscription is per account. Decision 4 recommends against the same account for a public video host. In a separate account the base is not shared and PeerTube pays its own $5.00 subscription. Both pricings (the project total is what the ceilings count; I assume stage 3 and the edge are built either way):

| Option | Same account: added | + stage 3 + edge | Separate account: added | + stage 3 + edge | Over `hard_max` $60? |
|---|---|---|---|---|---|
| P1 | $12 | $29 + $6 + $12 = $47 | $12 + $5 = $17 | $29 + $6 + $17 = $52 | no either way ($13 and $8 left) |
| P2 | $24 | $29 + $6 + $24 = $59 | $24 + $5 = $29 | $29 + $6 + $29 = $64 | separate: $64 is $4 OVER; same: $1 left |

Without the edge: P1 is $41 same or $29 + $17 = $46 separate; P2 is $53 same or $29 + $29 = $58 separate. So P2 in a separate account does not fit the hard maximum if the edge is built, and the reference environment would need `hard_max` raised first. Whether a second account's costs count against one project ceiling is not settled by the repo's gate, which prices manifests; that is another reason this is a decision. The tables in 6.2, 6.3 and 6.6 below show the same-account numbers unless stated.

### 6.6 Side by side, against `approved.json`

I ran `scripts/cost_raise.py --phase peertube --ceiling N` as a dry run on 2026-10-21 for each value; nothing was written.

| Option | Added | Running (stage 3) | Running (stage 3 + edge) | Phase ceiling needed | What the gate said, appended at the end of the phases | `hard_max` $60 |
|---|---|---|---|---|---|---|
| L | $0 | $29 | $35 | none | no new phase | fits |
| P1 | $12 (sep. $17) | $41 (sep. $46) | $47 (sep. $52) | $47 (sep. $52) | fails: "ceiling $47.00 is below learner-soc $53.00; a lower ceiling needs lowers: true and a reason" | fits |
| P2 | $24 (sep. $29) | $53 (sep. $58) | $59 (sep. $64) | $59 (sep. $64) | passes at $59, since $59 is not below `learner-soc` $53; at $64 it is over `hard_max` | same account: fits, $1 left; separate account: $64 is $4 over, does not fit |

Placing the phase `--after edge` fails for both: `second-site` ($41) would then be below the PeerTube phase ($47 or $59; $52 or $64 in a separate account). `second-site` and `learner-soc` are alternatives that sit on stage 3 and are not stacked on the edge, so the existing phase list does not describe "stage 3 plus edge plus PeerTube". For P1 the honest edit is either `"lowers": true` on a new `peertube` phase with the reason written down, or raising the ceiling to $53 and accepting $6 of unexplained headroom; I would not choose the second. This is the same phase-order problem the edge design describes (its section 5.5), and decision 3 of that design applies here too: do this when the phases before it are done.

## 7. Storage, transfer and the watched usage line

Storage in Spaces, billed against the shared 250 GiB. Estimates, not measurements:

- A source file at 5 Mbit/s (est., a typical 1080p bitrate) is 5 / 8 = 0.625 MB per second, 2.25 GB per hour.
- Every transcoded resolution adds a file (docs, section 4), and the original is optionally kept. Assume 2x the source in total (est.).
- 250 GiB is about 268 GB, so about 268 / (2.25 x 2) = about 60 hours of 1080p source before the subscription's storage allowance is gone. A cap by user quota decides the real number.
- Past the allowance: $0.02 per GiB. 500 GiB total is 250 GiB over = 250 x $0.02 = $5.00 a month.

Outbound transfer, where the viewers' bytes go. If the bucket (or its CDN) serves the files and `proxify_private_files` is off, video bytes leave Spaces, not the droplet. The Spaces CDN is included at no additional cost, and the included 1,024 GiB covers both CDN and origin bandwidth (pricing page, read 2026-10-21). So the 1,024 GiB is the allowance that matters.

- 1 hour viewed at 5 Mbit/s is 2.25 GB (est.). 1,024 GiB is about 1,100 GB, so about 490 viewer-hours a month fit in the allowance. At 2.5 Mbit/s (est., 720p), about 980.
- Overage: $0.01 per GiB. If 2 TiB leaves in a month, 1 TiB is over: 1,024 x $0.01 = $10.24. If 5 TiB leaves, 4 TiB is over: 4,096 x $0.01 = $40.96. One popular video can cost more than the droplet.
- Federation: viewers on other servers can watch through their own servers' bandwidth only if redundancy is enabled on them; without it the bytes come from here. PeerTube's player can also share segments between viewers (peer to peer); I did not read how much of the load that carries, and I do not count on it.
- Droplet outbound is billed at $0.01 per GiB over a pooled team allowance whose included size I do not know (UNVERIFIED, as in the edge design, section 5.7). Uploads count here: "Traffic from Droplets to Spaces ... does currently count against your Droplets' outbound transfer allowance" (Spaces pricing page, 2026-10-21). 100 GiB of video moved from the droplet to the bucket a month is at most 100 x $0.01 = $1.00 if none of it falls inside the allowance. Federation delivery and the web UI add traffic I have no figure for.

The gate cannot see Spaces transfer or droplet transfer. As the maintainer ruled for the edge, it becomes a watched usage line in `docs/cost.md`, with a billing alert set before the first apply. Proposed starting values, mine, not measured: alert at 80 percent of 1,024 GiB; alert if two consecutive days each exceed twice the daily share of the allowance (1,024 / 30 = about 34 GiB a day, so 68 GiB); alert at 80 percent of the storage quota; read the usage page weekly the first month.

## 8. Moderation and legal duties

High level only. A lawyer, not this document, decides what applies, to whom, and what to publish. What follows are the kinds of obligation a public, federated video host usually runs into, so the cost estimate includes them.

- Terms of service and a privacy policy. PeerTube lets the admin publish a ToS and a code of conduct and set whether the platform is for NSFW content (https://docs.joinpeertube.org/admin/managing-users, 2026-10-21). Data about the people who register is personal data; whether GDPR or another regime applies depends on who the users are.
- Copyright notices. In the United States, my understanding (not verified this session, and not advice) is that a host that wants the notice-and-takedown safe harbour registers a designated agent with the Copyright Office, publishes the contact, removes content on a valid notice, offers a counter-notice route and has a repeat-infringer policy. The Copyright Office keeps a directory of agents (https://www.copyright.gov/dmca-directory/); the fee, renewal period and what exactly is required are UNVERIFIED. Outside the United States the rules differ. A lawyer decides.
- Illegal content. Some content must be reported to authorities and removed immediately, with duties that differ by country. Describing them is the lawyer's job. The operational point: a person must be able to see a report the day it arrives, remove the content and preserve whatever the lawyer says to preserve.
- Provider terms. DigitalOcean can act on the team after an abuse report (edge design, risk 4). A video host increases that exposure more than the edge's transport daemons do, which is the strongest argument for the separate-account question (decision 4).
- Federation. Content published here is copied to servers that follow this one; a removal must be federated (PeerTube lets a moderator block a video and choose to unfederate it). Content from other servers shown on this site is also this site's problem to moderate.

What PeerTube offers (https://docs.joinpeertube.org/admin/moderation, 2026-10-21): moderator roles; a list of reports from local and remote users with accept and reject and a moderator comment; muting accounts and servers for the whole platform; manual and automatic video blocks (every new video hidden until a moderator approves it, and users the admin trusts can skip that); watched-word lists that tag or auto-block videos and comments, including an automatic block for videos containing an external link; and subscriptions to remote mute lists and watched-word lists (PeerTube 8.3 or newer). The docs advise against open registration, against uploads without limits (prefer a low quota or automatic quarantine) and against automatic following of other servers. Sign-up settings it recommends: require email verification and require approval, with a registration reason and a moderation response (https://docs.joinpeertube.org/admin/managing-users).

Staffing: one maintainer. The edge design's target for answering a provider abuse notice is 24 hours (its section 9); a notice about a public video site needs the same or faster, every day, including when the maintainer is at a day job or away. That is the real cost of running it, and no price line shows it.

## 9. Security, backups and restore

### 9.1 Security settings (checklist, not a build)

- Accounts: registration closed, or open with email verification and approval, ToS shown. Few staff accounts. Passwords unique and long. Two-factor if the running version supports it (UNVERIFIED).
- Rate limits: nginx `limit_req` on login, sign-up and the API; PeerTube's own rate-limit settings if they exist in the running version (UNVERIFIED: I did not read the configuration reference).
- Federation: no automatic follow, followers manually approved, an own or trusted blocklist subscribed (8.3 or newer), unknown servers muted by default if the moderators want. Whether PeerTube supports an allow-list-only federation mode is UNVERIFIED; I did not find one in the pages I read.
- Uploads: per-user video quota and daily upload limit, a size cap, import from URLs turned off (the admin page lists video import as a setting; an import makes the server fetch an arbitrary URL, which I treat as an SSRF-class risk), transcoding concurrency limited, new videos quarantined at first.
- The host: current releases of Node, PostgreSQL, Redis, ffmpeg and PeerTube, each pinned by version and checksum; unattended security updates; monthly rebuild; the service user unprivileged under systemd hardening; metadata endpoint restricted as in the edge design's handoff PR 1.
- Secrets: bucket key, database password, mail API key and the signing secrets live in Doppler, fetched at first boot. The PeerTube config file is generated from a template.
- Logs go to the stage 2 path home by the edge design's mechanism, with the same relay prerequisites; web access logs contain visitor addresses and email, which the lawyer's privacy answer governs.

### 9.2 What must be backed up

- PostgreSQL: accounts, videos' metadata, follows, moderation. The production guide backs it up with `pg_dump -F c peertube_prod` and restores with `pg_restore -c -C -d peertube_prod` (production guide, 2026-10-21).
- The bucket: every video. Spaces "does not include built-in backups"; copy to another bucket or elsewhere with rclone, s3cmd or similar (https://docs.digitalocean.com/products/spaces/details/limits/, 2026-10-21). A copy to a bucket in the same account does not survive losing the account, so the useful copy is off the account, as stage 3 already plans.
- The PeerTube `config/production.yaml` and the federation signing keys (kept under the instance's storage directory; where exactly is UNVERIFIED): the instance's identity. Losing them means a new identity.
- Redis: the job queue and cache only. It is a cache for this purpose; losing it loses queued jobs, not content. I did not verify that against the docs.

### 9.3 Backup plan and restore test

- Nightly `pg_dump` to a separate private bucket (versioned) and a nightly copy of the video bucket off the account. Combined with the 250 GiB subscription limit this is a second storage bill; a copy of 100 GiB at a second provider would cost what that provider charges, which I did not price.
- Restore: rebuild the droplet from code, restore the latest dump into a fresh PostgreSQL, point PeerTube at the existing buckets, start. Restore time is a measurement. The restore test runs before launch and then monthly, on a scratch droplet that is destroyed after.
- Because PeerTube keeps state in the database and the droplet is otherwise rebuildable, the database is the one part that conflicts with the edge design's "rebuild is the only recovery" rule. Options: dump-and-restore at every rebuild (free, minutes of downtime, up to a day of data loss), a block volume ($0.10 per GiB, section 6.4), or managed PostgreSQL ($15 and up, section 6.4). I recommend dump-and-restore, with the data loss written down.

## 10. Should the project cover PeerTube as a lesson only?

Yes, and for most learners that is the right answer. Reasons, with the other side given:

- For a lesson: the interesting parts (sizing, S3 storage, a public listener next to a zero-inbound core, moderation and legal duties, transfer cost) can be taught from this document and a learner's own throwaway account. Nothing about teaching them requires the reference environment to host user videos.
- For a lesson: a public UGC host exposes the maintainer, not the learner. The reference environment is a published example that bears the maintainer's name and one DigitalOcean team. A learner who runs their own carries their own duties and bill.
- For a lesson: it uses up most of the remaining `hard_max` headroom ($47 or $59 of $60 with the edge in the same account; $52 or $64 in a separate one, and $64 does not fit) for a workload outside the project's point, which is the cloud and zero-trust access.
- Against: a lesson with no running reference can drift from the real software. The mitigation is cheap: the lesson names the PeerTube version it was written against and the date, and a learner's first step is to check the dependencies page.
- Against: running it would produce real measurements for sizing and cost. A time-boxed run on a scratch account (for example a week on `s-2vcpu-4gb`, which is $24 / 30 days x 7 days = about $5.60 at the hourly proration, est.) gets those numbers without a standing public service. I do not recommend it as part of the project's accounts; it is an option for the maintainer's own scratch account.

If the lesson is chosen, a follow-up issue writes it: one wiki page with the section 4 requirements, the section 6 cost table with its dates, the section 8 legal warning (a lawyer decides) and a learner teardown checklist.

## 11. Recommendation

Option L: teach PeerTube as a lesson and do not run it in the reference environment. The cost line it adds against the ceiling is $0.00. The `edge` ceiling stays $35 and no `peertube` phase is created.

Reasons:

- The legal and moderation duties (section 8) are the largest cost and no dollar figure covers them. One maintainer answering notices on a public video host is a different job from running the edge's transport daemons.
- Sizing is unmeasured. The docs I read state no minimum for a small instance, and the only hardware figure (4 cores and 4 GB) is for 1,000 concurrent viewers. I cannot honestly approve a droplet.
- The transfer bill has no cap the gate can see: each TiB of viewing over the allowance costs $10.24 (section 7).
- Either running option lands at $47 or $59 with the edge in the same account (within $13 or $1 of the absolute limit), or $52 or $64 in a separate account, where P2 is $4 over and does not fit. All of that is for a workload that is not why the project exists.
- The edge and stage 3 have not been built or approved, and the phase order means a PeerTube phase waits for them anyway.

If the maintainer wants it running anyway, choose P1: `s-1vcpu-2gb` with transcoding on a disposable, isolated home runner (section 3.3; without that isolation, P1 is dropped), priced as in 6.5: $12 added with buckets on the stage 3 subscription (same account, an explicit prerequisite for that price) or $17 added in a separate account (which decision 4 favours); a new `peertube` phase at $47 (same account) or $52 (separate), each below `learner-soc` $53, with `"lowers": true` and its reason written down, registration closed or approval-only, quarantine on, a lawyer's answer in writing first, and a measurement on the 2 GiB droplet that must pass before the number is final. If the measurement fails, the move is to P2 and $59 in a new reviewed diff (same account only; $64 in a separate account is over `hard_max` and not available), and then the project is $1 under its hard maximum, which is the signal to stop. P0 and the managed-database variants should not be chosen.

## 12. Known risks and decisions

Facts verified today (2026-10-21), with where:

| Fact | Source |
|---|---|
| Latest PeerTube release v8.3.1, 2026-09-28 | https://api.github.com/repos/Chocobozzz/PeerTube/releases/latest |
| Node `>= 22.12 and < 25`, PostgreSQL `>= 14`, Redis `>= 6.2`, ffmpeg `>= 4.3` | https://raw.githubusercontent.com/Chocobozzz/PeerTube/develop/support/doc/dependencies.md |
| Only nginx is officially supported; certbot standalone in the guide; PeerTube does not support a host change; `pg_dump` and `pg_restore` backup steps | https://raw.githubusercontent.com/Chocobozzz/PeerTube/develop/support/doc/production.md |
| Object storage via S3 API; public bucket with permissive CORS; cache server strongly recommended; live stays on disk | https://docs.joinpeertube.org/admin/remote-storage |
| Transcoding takes a lot of CPU and one file per resolution; remote runners pull jobs | https://docs.joinpeertube.org/admin/configuration and /admin/remote-runners |
| About 1000 concurrent viewers: at least 4 CPU cores and 4 GB RAM; many videos: object storage and remote runners | https://docs.joinpeertube.org/maintain/configuration |
| Moderation tools; sign-up settings; blocklist subscriptions need 8.3 or newer | https://docs.joinpeertube.org/admin/moderation and /admin/managing-users |
| Spaces: $5.00 base, 250 GiB, 1,024 GiB outbound shared, $0.02 per GiB stored over, $0.01 per GiB out over, CDN included, no built-in backups | https://docs.digitalocean.com/products/spaces/details/pricing/ and /limits/ |
| SMTP ports 25, 465, 587 blocked on droplets | https://docs.digitalocean.com/support/why-is-smtp-blocked/ |
| Managed PostgreSQL single node from $15.00; volumes $0.10 per GiB | https://docs.digitalocean.com/products/databases/postgresql/details/pricing/ and /volumes/details/pricing/ |
| Droplet prices | `docs/cost-prices.json`, retrieved 2026-10-10 |
| Phase and `hard_max` figures; the `cost_raise.py` dry-run results | `docs/stages/approved.json` and `scripts/cost_raise.py` on 2026-10-21 |

Not verified, and given no number: the minimum RAM, CPU and disk for a small PeerTube; whether DigitalOcean Spaces works with PeerTube's ACL and CORS settings; whether a home runner works with a Spaces-backed instance; the included droplet transfer per plan; how much traffic peer-to-peer playback saves; the DMCA agent fee and renewal period; whether PeerTube supports two-factor and which rate-limit keys it has; whether it has an allow-list federation mode; the live-streaming ingest port; Redis's role beyond jobs and cache; where the federation signing keys live; any mail provider price; the Docker path's requirements; any country's legal duties.

Decisions the maintainer owes (my pick in the right-hand column):

| # | Question | My recommendation |
|---|---|---|
| 1 | Which option: L, P1, P2 | L, the learner lesson only, $0 added |
| 2 | If run anyway: the `peertube` phase ceiling: P1 $47 same account or $52 separate (both $47 and $52 are below `learner-soc` $53, so each needs `lowers`), or P2 $59 same account (separate $64 does not fit) | P1, measured first, with the account answer from decision 4 |
| 3 | When: wait for the phases before `edge`, and the edge, to be done | Wait. Same rule as the edge design |
| 4 | Same DigitalOcean team as core, a separate team, or another provider, given a public video host's abuse exposure | Not the same team. A separate team or account for anything that hosts strangers' content, if it runs at all. This depends on facts the edge design lists as open (price and limits of a team, isolated credentials, pooled transfer) |
| 5 | Certificate method: open port 80, or 443 only with a DNS challenge and one more credential | 443 only, if it runs |
| 6 | Registration policy: closed, or open with approval and quarantine | Closed or approval-only with quarantine |
| 7 | Backup shape: dump-and-restore, volume, or managed PostgreSQL | Dump-and-restore |
| 8 | Transfer: a watched usage line with a billing alert before the first apply | Accept, as ruled for the edge |
| 9 | A lawyer reviews the ToS, the notice process and the agent question before launch | Required for any running option |
| 10 | The lesson issue: write the learner lesson (section 10) | Yes |

## 13. Changes this stage makes to the repository

This PR adds only this file and a one-line link under the edge section of the wiki Roadmap. It changes no JSON, no stack and no policy.

If the maintainer picks P1 or P2 later, the implementation touches: a `stacks/` stack and module for the host, the `approved.json` phase and provider total, `scripts/cost_check.py` (the droplet allowlist and a `spaces` entry, shared with stage 3), `.spacelift/` policies (deny peering and core tags), `docs/cost.md` (the usage line), an operator guide and a wiki page.

## 14. What this design does not claim

It does not claim that any droplet size in this document runs PeerTube, that the transfer and storage figures are anything but arithmetic on assumed bitrates, that Spaces works with PeerTube as configured, or that any page read today stays true (each fact carries its date). It does not describe what the law requires: section 8 lists topics, and a lawyer decides. It did not probe, apply or plan anything, and it called no DigitalOcean API.
