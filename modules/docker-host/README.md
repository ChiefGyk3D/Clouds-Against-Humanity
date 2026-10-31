# docker-host (DigitalOcean)

One hardened droplet that runs Docker Engine and Portainer CE, set up by
cloud-init. It is the machine of stage 3 (the workload host); the stack
[`stacks/30-workloads`](../../stacks/30-workloads) gives it its tag, its
firewall and its Twingate resources. There is no Twingate connector in this
module and no inbound path of its own.

**Unapplied.** Only `stacks/30-workloads` calls this module, behind a switch
that defaults to off, and the stage is not approved. Nothing here has run on a
real machine.

## What the cloud-init does, in order

1. **Update.** Package update and upgrade, and unattended upgrades with a
   reboot window the stack chooses (`reboot_time`).
2. **Baseline.** One admin user (`cah-admin`) with one public key, no
   password, root locked; sshd drop-in (`PermitRootLogin no`,
   `PasswordAuthentication no`, `AllowUsers cah-admin`); a sysctl drop-in that
   leaves `ip_forward` alone because Docker needs it.
3. **Harden.** `sshd -t && systemctl restart ssh`, before any application is
   installed.
4. **Applications.** Docker Engine and the compose plugin from Docker's signed
   apt repository; the key file must hold exactly one key, the pinned
   fingerprint (`cah-apt-key-check`), before it is trusted. No piped installer.
   Then Portainer CE, pinned to an exact tag.

## No wildcard binds

- `/etc/docker/daemon.json` has no `hosts` key, so the Docker API is the local
  socket only, and its default bind address is `127.0.0.1`.
- Portainer's one published port is `${PORTAINER_BIND:?}:9443:9443`.
  `cah-portainer-up` reads the VPC address from the droplet metadata endpoint
  and writes it to `.env`; with no private address nothing starts. The Edge
  agent port (8000) and plain HTTP (9000) are not published.
- The module renders no credential. Daemon credentials stay in Doppler and are
  entered in Portainer over Twingate.

## Outputs

`instance_id`, `instance_name`, `droplet_urn`, `private_ip`, `size`,
`portainer_port`. `user_data` is never an output.

## Verified claims

- **Docker apt signing key fingerprint, checked 2026-10-31.** The default
  `docker_apt_key_fingerprint` is `9DC858229FC7DD38854AE2D88D81803C0EBFCD88`.
  The key file at `https://download.docker.com/linux/ubuntu/gpg` was downloaded
  with plain curl, the page `https://docs.docker.com/engine/install/ubuntu/`
  (which points apt at that exact URL) was fetched the same day, and
  `gpg --show-keys --with-colons` in an Ubuntu 24.04 container listed one
  primary key (`Docker Release (CE deb) <docker@docker.com>`) with exactly this
  fingerprint. It matched what was first written from memory, so nothing
  changed. The published install page itself does not print the fingerprint;
  the proof is the downloaded key.

## Not verified on a real machine

Docker's apt origin spelling for unattended upgrades, the metadata path for the
private address, and Portainer's behavior with these flags are written from the
vendors' documentation and mocked tests only. The stage guide lists the checks
to run after the first boot.
