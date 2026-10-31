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

## Not verified on a real machine

Docker's apt origin spelling for unattended upgrades, the metadata path for the
private address, and Portainer's behavior with these flags are written from the
vendors' documentation and mocked tests only. The stage guide lists the checks
to run after the first boot.
