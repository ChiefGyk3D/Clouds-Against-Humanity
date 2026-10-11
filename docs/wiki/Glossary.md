# Glossary

| Term | Meaning |
|---|---|
| **ACL** | Access control list. In Twingate, a signed list of the resources a client (or connector) is allowed to reach. |
| **Application service (appservice)** | A Matrix component the homeserver trusts to act for many users. The homeserver pushes events to it over HTTP, so it must be reachable from the homeserver. Bridges are application services. |
| **Bridge** | Software that relays messages between two chat networks, here Discord and Matrix. |
| **cloud-init** | The tool that configures a Linux cloud instance on first boot from its user-data. |
| **Connector** | Twingate's component inside your network. Makes outbound connections only and forwards authorized traffic to resources. |
| **Controller** | Twingate's hosted coordinator: configuration, sign-in, signed ACLs. Never carries traffic. |
| **Cost gate** | `scripts/cost_check.py`, which fails CI if planned spend exceeds the approved total. |
| **Doppler** | Hosted secrets manager. Every real secret in this project lives there. |
| **Droplet** | A DigitalOcean virtual machine. |
| **GYST** | git-your-ship-together, the author's library of reusable, hardened GitHub Actions workflows. |
| **IdP** | Identity provider, the service that actually checks who you are (and enforces MFA). |
| **Lateral movement** | An attacker moving from the first compromised system to others on the same network. |
| **MFA** | Multi-factor authentication. |
| **Module** | A reusable OpenTofu building block. Never applied on its own here. |
| **OIDC** | OpenID Connect. Here: short-lived identity tokens that let one service authenticate to another without a stored secret. |
| **OpenTofu** | Open-source, MPL-licensed fork of Terraform. |
| **Portainer** | A web UI for a Docker host: stacks, containers, logs. Community Edition is free. It talks to Docker over the local socket, which is root on the host, so its UI is reached only through Twingate here. |
| **Proposed run** | A Spacelift plan for a pull request. Gets no credentials in this repo. |
| **Relay** | Twingate component that joins a client and connector when a direct path is impossible, without terminating the encryption. |
| **Remote network (site)** | Twingate's name for a network that connectors serve, here `access-nyc3`. |
| **Resource** | In Twingate, one destination (address plus allowed ports) that a group can be granted. |
| **SASE / SSE** | Secure Access Service Edge / Security Service Edge. Vendor categories that bundle ZTNA with other network security services. |
| **Spacelift** | Hosted runner for infrastructure as code: plans, applies, holds state, waits for approval. |
| **Stack** | A unit of infrastructure applied on its own with its own state. One Spacelift stack per `stacks/` directory. |
| **State** | OpenTofu's record of what it created. Can contain secrets, so where it lives matters. |
| **Tag (DigitalOcean)** | A label on a resource. Firewalls attach to tags, so a droplet is protected the moment it has one. |
| **Tracked run** | A Spacelift run on `main` that can apply after confirmation. The only kind that gets credentials. |
| **User-data** | The cloud-init configuration passed to a droplet at creation. Readable from the metadata endpoint. |
| **VPC** | Virtual private cloud, a private network for droplets. |
| **VPN (remote access)** | A tunnel that places a device on a private network. |
| **ZTNA** | Zero trust network access: per-user, per-resource access decided on every connection, with no implicit trust from network location. |
