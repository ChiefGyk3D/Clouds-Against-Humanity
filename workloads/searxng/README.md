# SearXNG on the docker host (stage 3 workload)

> **Not applied.** This is a compose definition written on 2026-11-01. Nothing has deployed it, and nothing here has run on a real machine. Stage 3 is not approved (see [the stage 3 guide](../../docs/stages/03-workloads.md)). The maintainer will run it and report differences. Why you might run a service like this yourself, and when not to: [Self-hosting, when and why, with SearXNG as the worked example](../../docs/wiki/Self-Hosting-When-and-Why-with-SearXNG-as-the-Worked-Example.md).

SearXNG is a metasearch engine: it sends your query to many search engines and returns the merged results, without passing your address or cookies on (SearXNG's "Why use a private instance?" page, read 2026-11-01). This workload runs it with its cache on the stage 3 docker host as a private instance, for the maintainer and anyone granted access, and for no one else.

## Files

| File | What it is |
|---|---|
| `docker-compose.yml` | Three services: `core` (SearXNG), `valkey` (the cache the limiter needs) and `bind-check` (runs once before `core` and exits with an error unless `SEARXNG_BIND` is a private IPv4 address, so `core` does not start) |
| `settings.yml` | SearXNG settings: limiter on, not a public instance, HTML output only, secret key a placeholder |
| `limiter.toml` | Bot detection settings that differ from the defaults |
| `env.example` | The names of the stack variables, no values |

## How it is reached

Only over Twingate, through the host's private address, never public. The compose file publishes SearXNG's port on the private address named in `SEARXNG_BIND`, which has no default. Docker's default for a published port is every host address, and Docker's own pages say that published-port traffic is diverted before host firewall rules such as ufw see it (read 2026-11-01), so the bind in this file is the control that counts and a cloud firewall is a second layer outside the host. Reaching the web page from a laptop needs a Twingate resource for port 8080 on the host's private address. **That resource now exists in `stacks/30-workloads` as an unapplied option, off by default.** The stack variable `workload_web_ports` is a list of web ports, empty by default. Setting it to `[8080]` (and only when the stage is approved and switched on) makes one TCP-only Twingate resource for port 8080 on the host's private address, granted to the admins group, plus a matching inbound allowance from the connector tag only. Nothing has been applied and stage 3 is not approved.

## Images, pinned on 2026-11-01

Both images are pinned by tag and digest. The digest is the manifest-list digest read from the Docker Hub registry API on 2026-11-01 (anonymous token, `HEAD` on the manifest), and it matched the Docker Hub tags API.

| Service | Image | Digest |
|---|---|---|
| `core` | `docker.io/searxng/searxng:2026.11.1-8b35dcd2e` | `sha256:4b106e61eeb9e216ac96c85591338c1e9ceb5a84c26f72cd18b8ba8f0f52093c` |
| `valkey` | `docker.io/valkey/valkey:9.1.3-alpine` | `sha256:bf09d58e96d6b4524a15396b65b242bbe18beebbcc15a04d8ee75ddac62fae0b` |

SearXNG publishes a rolling `latest` and a dated tag for every build, and has no GitHub releases to read (the releases API returned an empty list on 2026-11-01), so there are no release notes. The pinned tag is the build that its documentation was generated from (documentation version 2026.11.1+8b35dcd2e). The upstream template uses the floating tags `latest` and `9-alpine`; this file does not.

## Deploy through Portainer (steps for the maintainer)

1. On the host, create the config directory `/opt/cah/searxng/config` (your choice; set `SEARXNG_CONFIG_DIR` if different) and copy `settings.yml` and `limiter.toml` into it. The container's start-up may change the ownership of mounted files (SearXNG's `FORCE_OWNERSHIP` setting, default true), so the mount is read-write.
2. In Portainer (over Twingate) create a stack from `docker-compose.yml`.
3. In the stack environment set `SEARXNG_BIND` (the host's private address), `SEARXNG_SECRET` (a long random value generated for this instance and kept in Doppler; never in git or in a file here), `SEARXNG_CORE_MEM` and `SEARXNG_VALKEY_MEM` (see `env.example`).
4. Deploy. Then check, on the host: `ss -ltn` shows port 8080 on the private address only and nothing on a wildcard address for it; the Valkey container shows no published port in `docker ps`; the logs show no error about the secret key or the Valkey connection.

## Memory, and whether it fits the droplet

**The memory SearXNG needs is unknown from its documentation.** None of the SearXNG pages read on 2026-11-01 (installation, container, settings, limiter, architecture) state a figure, and nothing here has been measured. The two limits in `env.example` are starting ceilings to test, not needs.

The droplet in the plan is `s-1vcpu-2gb` with no swap. The [stage 3 design](../../docs/superpowers/specs/2026-10-11-stage-3-workloads-design.md) estimates that the existing daemons, Portainer, Docker and the operating system already use roughly 1.2 to 1.6 GB (est., the design's own figure). Whether SearXNG fits in what is left is **unknown**. It may be tight (est.). Measure with `docker stats` on the real host before relying on it, and if it does not fit, the choices are a larger droplet (a cost decision for the maintainer, not made here) or not running it there.

## The optional Tor proxy (off by default)

SearXNG can send its outgoing requests through a proxy, and its docs say to use a `socks5h://` address for Tor so names are resolved by the proxy (settings_outgoing page, read 2026-11-01). The commented block at the bottom of `settings.yml` shows the shape. It is off by default, there is no Tor service in the compose file, and no Tor image is pinned, because running a Tor client is a separate decision with its own review. Tor hides the droplet's address from the search engines, not your queries from your own host, and many engines treat Tor exit addresses as suspect, so expect more CAPTCHAs (est.). See [How Tor works](../../docs/wiki/How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services.md).

## Updates

The images do not update themselves. To update: read the new tag and digest from the registry, change both in `docker-compose.yml`, run the tests, and redeploy the stack in Portainer. Compare the upstream template (`container/docker-compose.yml` in SearXNG's repository) for changes first, as its docs advise.

## Backups

There is almost nothing to back up. The configuration is in git. The secret is in Doppler. The Valkey service saves nothing to disk (the limiter's counters are short-lived). The `core-data` volume holds a favicon cache that SearXNG rebuilds. SearXNG keeps no user accounts. Restore test: redeploy the stack on a fresh host from git and Doppler and check that the page loads. See [Backups, recovery and patching](../../docs/wiki/Backups-Recovery-and-Patching.md).

## Verified and not verified

Read on 2026-11-01: SearXNG's container installation page, its server, valkey and outgoing settings pages, the limiter page, the bot detection page, the architecture page, the "Why use a private instance?" page, the upstream compose template, `.env.example`, `settings.yml` and `limiter.toml`; Docker's port publishing and packet filtering pages; the registry digests above.

Checked offline by `tests/test_searxng_workload.py`: the compose file parses; both images are pinned by tag and digest; the one published port is bound by a required variable and no wildcard bind appears; the `bind-check` script, run in a local shell, accepts private addresses and refuses a wildcard or public one, and `core` waits for it to finish successfully; the cache publishes nothing and sits on an internal network; no secret value is in any file; the limiter is on and the instance is not public in the file and in the environment; the Tor option is off.

**Not verified:** that the `bind-check` container runs as written (its script was tested in a local shell only, and the cache image's shell was not run); that Portainer accepts the file or that a container engine starts it (no Docker Engine was run; the checks were a YAML parse and `docker-compose config` 2.26.1, which rendered the file with the variables set and stopped with an error naming `SEARXNG_BIND` when it was unset, a syntax and interpolation check only); that the images start with these settings; that SearXNG honors `use_default_settings` with this file and the environment overrides as the docs describe; that the container starts with `no-new-privileges` and a read-write config mount; that the limiter works when every user reaches the instance from the Twingate connector's address (the limiter counts requests per client address, so all users may look like one client, est.); what memory it uses; that the Twingate and firewall path exists; that the Valkey instance needs no password on an internal network (it is unreachable from outside the compose network by construction, not tested).
