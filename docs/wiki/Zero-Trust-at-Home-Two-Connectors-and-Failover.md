# Zero trust at home: two connectors and failover

Side page to [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md). Read that page and [Twingate](Twingate.md) first; this one shows the same idea in a home lab, then asks what changes when the internet connection fails. Not counted in the path totals. Next: [Twingate](Twingate.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from the maintainer's own description of his home lab, from this repository's design, and from vendor pages; nothing here was applied or tested for this page.** The home setup is described only as he described it to me, in general terms: no addresses, VLAN numbers, host names or product models appear, on purpose. The two free exercises (1 and 4) need only paper. Exercise 2 is a small container model of the idea; **its commands were not run for this page** (marked est.; the digests were read, the images were not pulled). Vendor facts were read on **2026-10-21** and are cited where used.

> **Prerequisites.** [Networking basics](Networking-Basics-for-This-Project.md) (inbound, outbound, ports, firewalls) and [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md). About 45 minutes of reading and about 60 minutes for the free exercises (est.). Cost: theory is free. The hands-on part uses your own hardware or a provider bill, see [cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md); nothing here is sold.

## What you will be able to do

- Say what zero trust means in practice, without the marketing.
- Explain why a home lab with two outbound-only connectors stays reachable when the home internet fails over to cellular, and why a traditional VPN often does not.
- Map the home design to the cloud design in this repository, piece by piece.
- Write firewall rules by role on paper, using documentation-only addresses.
- Name the limits: a connector is a high-value target, and the identity provider becomes critical.

## What zero trust means in practice

The old model is **"inside the network means trusted"**. Get onto the network (plug in, join the Wi-Fi, connect the VPN) and you can usually reach most things. The network location is the credential.

**Zero trust** removes that. Every request is decided on three things:

1. **Identity**: who is asking, proven by an identity provider with MFA.
2. **Device**: is this a device we expect, in a state we accept (managed, patched, screen lock on)? Which of these checks you get depends on the product and plan; treat device checks as something to verify, not assume.
3. **Least-privilege resource access**: may this identity reach *this one resource* (an address and a port), right now? Not "the network", not "the subnet".

Being on the home LAN, or having a working tunnel, grants nothing by itself. The wiki's longer version is [Identity basics: zero trust](Identity-Secrets-and-Zero-Trust-Basics.md#zero-trust-with-the-marketing-removed). The standard reference is [NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final).

## The home design, as a pattern

This is the maintainer's own home lab, described in general terms. It is a small version of what an enterprise does with larger equipment.

- Two small single-board computers (Raspberry Pi 4 boards with 4 GB of memory) each run one Twingate **connector** in a container. The two are **active peers** in one remote network: either one can carry a new connection, so losing one is survivable (high availability, with failover to whichever is still up). There is no "primary" and "standby".
- Both sit on **their own VLAN**. A VLAN is a way to split one physical network into separate virtual ones, so the connector hosts are not on the same network as laptops, phones or smart devices.
- In his lab, different roles and individuals get access to different resources, scoped at the network level in different ways: some to a single device and port, some to a whole subnet. The pfSense firewall rules limit what the connector hosts themselves can reach. Per-role and per-person scoping is where a ZTNA product beats a VPN; the section below spells it out.
- The host operating systems of the two boards are patched automatically with his own project, [Patch Gremlin](https://github.com/ChiefGyk3D/Patch-Gremlin). Patch Gremlin patches only the host operating system, not container images, so the Twingate connector containers on the two boards are updated **manually** today (his statement). Adding container-image updates to Patch Gremlin is a possible later feature; it is not built.

No diagram image is used here: the repository renders diagrams with `scripts/render_diagrams.py`, which needs Mermaid CLI and a browser, and neither is available in the sandbox this page was written in. A text diagram follows; every box and arrow is invented-for-teaching and carries no real address.

```text
   Your laptop (Twingate client, signed in through the identity provider)
        |
        |  outbound only: client dials out to Twingate
        v
  +--------------------------------------------+
  | Twingate cloud: controller + relays        |   decides: is THIS user
  | (signs the access list; carries no data    |   allowed THIS resource?
  |  in the normal case)                       |
  +--------------------------------------------+
        ^                          ^
        | outbound only            | outbound only
        | (TCP 443, relay ports)   | (TCP 443, relay ports)
  +-----------+              +-----------+
  | Connector |              | Connector |        <- connector VLAN
  |   one     |              |   two     |           (own network,
  +-----------+              +-----------+            tight rules)
        \                          /
         \  firewall limits what the  /
          \   connector hosts reach  /
          v                        v
   +---------------+ +----------------+ +---------------+
   | Lab subnet    | | Admin subnet   | | IoT subnet    |
   | (role: lab)   | | (role: admin)  | | (role: admin, |
   | 192.0.2.0/24  | | 198.51.100.0/24| |  no agent)    |
   +---------------+ +----------------+ | 203.0.113.0/24|
                                        +---------------+

   Home router, normal path:      broadband
   Home router, failover path:    cellular (still outbound-only, still works)
   Inbound port forwards:         none
```

The two connectors dial **out** to Twingate. Nothing on the internet connects *in* to the house. Read that last line twice, because it is the whole advantage.

## How this maps to the cloud design in this repository

The cloud stage-1 design is the same pattern with droplets instead of Pis. See [Twingate](Twingate.md) for the detail.

| Home lab | This repository's cloud design | Same idea |
|---|---|---|
| Two connectors on two small computers | Two connector droplets in `access-tor1`, one per `a` and `b` | At least two per site; Twingate recommends it, see [Twingate: two connectors](Twingate.md#two-connectors-not-one) |
| Connectors only dial out | Zero inbound ports on every droplet; the firewall allows only outbound | No listener to scan or attack |
| Own VLAN for the connector hosts | Own firewall, attached by tag, and a VPC | Connector hosts get stricter rules than the things they reach |
| Role in the identity provider decides reach | A Twingate **group** (`cah-tor1-admins`) is granted **resources** | Identity picks the resources, not the network |
| Different roles and individuals reach different resources, some one device and port, some a whole subnet | One resource per host and port, never "the whole VPC" | Least privilege, one resource at a time |
| Patching with Patch Gremlin | Staggered reboots and updates, 04:00 and 05:00 Eastern | Never restart both at once |

One difference to state plainly: at home the connector hosts can reach whole subnets because the firewall allows it. In this repository each Twingate resource is a single address and port. Prefer the narrow form wherever you can; subnet-wide access is the thing that rebuilds a VPN.

## Why two connectors

A single connector is a single point of failure. Two give you **high availability** (HA: the service keeps working if one part fails) and **failover** (new connections use whichever connector is still up). Connectors in one remote network are active peers, not primary and standby: both are live, and either can carry a new connection. Failover does not rescue a session already in flight: a long SSH session that was going through the connector that died will probably drop (est.) and you reconnect through the other.

| What fails | What you see | What still works |
|---|---|---|
| One connector's host loses power or crashes | One connector shows offline in the admin console | New connections, through the other connector; sessions that used the failed one may drop |
| One connector's software is updating or restarting | Same, for a few minutes | New connections, through the other |
| The home broadband link goes down, router fails over to cellular | Both connectors lose their path, redial over cellular | Access, once they reconnect (seconds to a minute, est.) |
| Both connector hosts fail, or the connector VLAN breaks | Nothing reachable | Nothing remote. The Twingate admin console is a cloud service and stays reachable, so it shows both connectors offline, but it cannot repair a host or a VLAN: you need local or out-of-band access (keyboard, a console cable, a second path) to restore them |
| The identity provider is down | Nobody can sign in | Already-open sessions may continue (est.); new ones cannot start |

Two connectors on two separate Pis share the same house, switch, router and power circuit. They protect against a failed board or a bad update, not against a house-wide outage. For this repository's cloud connectors the same warning applies to the shared region, noted on [Twingate](Twingate.md).

### How to test failover safely

Test during a time you can walk to the equipment, with a way in that does not depend on the thing you break.

1. **Predict first.** Write down what you expect to see: which connector shows offline, whether your open SSH session drops (it may), and how long a new connection takes.
2. Stop **one** connector (stop its container, not the host). Confirm you can still reach a harmless resource. Start it again and wait until the console shows it online.
3. Only then, with the other connector verified healthy, repeat on the other one.
4. Do not stop both at once unless you have local access (keyboard or console) to the hosts: the admin console cannot restart them for you.
5. For the cellular test, switch the router's failover manually in a maintenance window you chose, not by pulling a cable at random.

## VLAN isolation and firewall rules by role

A connector host is a stepping stone: it can reach whatever the firewall lets it reach. So give it its own network and write the rules from the connector VLAN outward, on a **default deny** basis (block everything, allow only what is listed).

Generic examples, using documentation-only addresses ([RFC 5737](https://www.rfc-editor.org/rfc/rfc5737): `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`). Treat them as a shape, not a recipe; your firewall's syntax differs.

| # | From | To | Port | Action | Why |
|---|---|---|---|---|---|
| 1 | Connector VLAN | Internet | TCP 443 and the relay range | Allow | Connectors dial out (see below) |
| 2 | Connector VLAN | Internet | DNS and time | Allow | Name lookup and clock |
| 3 | Connector VLAN | Lab subnet `192.0.2.0/24` | SSH, web | Allow | Needed by the lab role's resources |
| 4 | Connector VLAN | Admin subnet `198.51.100.0/24` | SSH | Allow | Needed by the admin role's resources |
| 5 | Connector VLAN | IoT subnet `203.0.113.0/24` | One named port | Allow | Needed by the admin role's agentless resource |
| 6 | Anywhere | Connector VLAN | any | Deny | Nothing initiates to a connector |
| 7 | Connector VLAN | everything else | any | Deny | Default deny |

A caution that matters: a firewall such as pfSense does not see which identity-provider role started a request. What it sees is a packet from the connector host's address on the connector VLAN. So the firewall limits what the **connector hosts** can reach, which is the **union** of every role any user may hold. The decision "this role may use that resource" is made by Twingate groups and resources, before the traffic reaches the connector. The firewall is the coarse outer wall; the identity-based policy is the inner one. Do both.

**Design option.** If you want the firewall itself to differ by role, give different roles' resources different connectors, ideally in different remote networks, on different source addresses or VLANs, and write one firewall rule set per connector. The firewall then sees different sources and can treat them differently. The cost is more connectors to run and patch.


## Patching the connectors safely

The software that provides access to everything is the most important thing to keep patched, and it is also the thing whose failure locks you out. So:

- **Automate it**, because a manual patch routine is a patch routine that gets skipped. The honest state of his own lab is mixed: the host operating systems are automated, and the connector containers are still updated by hand.
- **Stagger it**: never update both connectors at the same time. This repository does it with reboots an hour apart.
- **Have a rollback plan**: know how to start the previous container image, or reinstall from a known-good version, before you need it. Write the commands down on paper.
- **Watch the outcome**: an update that silently fails is the same as no update.

Patch Gremlin is the maintainer's public project for this. What its README says (read 2026-10-21, read-only): it provides automated system update notifications for Debian and RHEL-based systems, integrating with `unattended-upgrades` (Debian, Ubuntu) or `dnf-automatic` (RHEL, Fedora, Amazon Linux); it fires when the upgrade run finishes so the report describes that run; its setup asks for update type, schedule and whether to auto-reboot; it lists Raspberry Pi OS among supported systems; and it sends to Discord, Teams, Slack, Matrix, ntfy, Gotify and generic webhooks. The README does not mention Docker or container images, and the maintainer confirms Patch Gremlin patches only the host operating system, not container images. So a connector container is not updated by it: on his two boards that is a manual step today, and container-image updates in Patch Gremlin are a possible later feature, not built. Twingate's own [upgrading connectors](https://www.twingate.com/docs/upgrading-connectors) page (read 2026-10-22) says "For Docker and systemd deployments, you apply updates manually using the platform-specific instructions above", publishes connector updates "on an approximately monthly cadence", and says the admin console "will surface an upgrade prompt for any Connector that has an update available". Plan and check your own update routine separately.

## ZTNA versus a VPN: flexibility of access

The firewall is a coarse outer wall; the real policy lives in the ZTNA product. There, access is granted per **role or individual**, per **resource**, and each resource can be drawn as narrowly or as widely as you need: one device and one port, or a whole subnet.

| Who | Resource they are granted | Granularity | What a traditional VPN would typically do |
|---|---|---|---|
| Role A (a lab tinkerer) | One lab device, SSH only (`192.0.2.10`, TCP 22) | Single device and port | Put them on the network; the whole lab subnet is reachable |
| Role B (an administrator) | The whole admin subnet `198.51.100.0/24` | Subnet-wide | Same network-wide reach, same as everyone else |
| Role C (a guest or an unassigned person) | Nothing | None | Anyone with a VPN login gets on the network |

With a VPN the usual unit of access is "the network the tunnel joins", and per-user limits mean separate VPN profiles or firewall rules keyed on each user's tunnel address, which is hard to keep right. With ZTNA the unit is the resource, and moving a person between roles is an identity change, not a firewall change.

What the firewall still does: it only sees packets from the connector hosts, so it cannot tell which role started a request and does not need to. It limits what the connectors can reach (the union of all roles), which caps the damage if a connector is compromised.

**Honest limit.** The finer the policy, the more you rely on product features: how granular a resource can be, and whether roles come from your identity provider's groups, depend on the plan. I have not verified which tier offers what; confirm on the vendor's pricing and documentation pages (see Honest limits below).

## VPN versus ZTNA under real residential conditions

A traditional remote-access VPN is a server you run, and your laptop connects **in** to it. So the server must be **reachable**: it needs an address that stays put and a hole in the firewall.

| Condition | Traditional VPN at home | Outbound-only connector |
|---|---|---|
| **Stable address** | Needs a static IP, or **DDNS** (dynamic DNS: a name that follows your changing IP address) | Not needed; the connector finds Twingate, not the other way round |
| **CGNAT** (carrier-grade NAT: your ISP shares one public address among many customers) | Usually breaks it; you have no address of your own to forward to | Works; connections go out |
| **Failover to cellular** | The cellular link often has a different address or sits behind CGNAT; the VPN address changes or disappears | Works; the connectors redial out over the new path |
| **ISP changes the path** | Remote users get a stale address until DDNS catches up | Reconnects by itself |
| **Inbound port forward** | Required (an open port on the router) | None |
| **Exposure** | The VPN port is on the internet and is scanned constantly | No inbound listener |

The case that prompted this page: the home connection fails over to cellular, and he can still reach his lab from outside, with no static IP and no DDNS involved. A VPN server behind the same cellular link would normally be unreachable. Be careful with "always": some cellular plans and some VPN designs (for instance a VPN server in a cloud instance that the home site dials out to) can work. The simple, single-box VPN at home is the one that struggles.

**What a connector needs instead**, from Twingate's [allowlist article for outbound connections](https://help.twingate.com/articles/1198271128-allowlist-for-outbound-connections-to-twingate-infrastructure) (read 2026-10-21):

| Direction | Port | Why |
|---|---|---|
| Outbound TCP | 443 | Basic communication with the controller and relays |
| Outbound TCP | 30000 to 31000 | Relay connections when peer-to-peer is not possible |
| Outbound UDP | any | Peer-to-peer connections, for speed |
| Outbound TCP | 80 | Operating-system package mirrors (not Twingate itself, per [Twingate](Twingate.md#outbound-ports-the-connector-needs); needed if the host fetches updates over plain HTTP) |
| Outbound TCP and UDP | 53 | DNS |
| Outbound UDP | 123 | Time (NTP) |

The first three rows are from Twingate's article; the last three come from this repository's connector setup. The same article says allowlisting by address needs the fully-qualified domain names as well. **If you leave a row out:** without TCP 443 the connector cannot work at all; without the relay range it can only use direct peer-to-peer paths and some clients will fail to connect; without UDP the connection falls back to relays and is slower (est.); without TCP 80 or DNS the host cannot fetch its own updates; without NTP the clock drifts and TLS checks can start to fail.

## The agentless-device case

Some devices cannot run any software you install: a printer, a camera, a thermostat, an old network appliance. Zero trust assumes an agent on the device; these have none.

The connector solves it from the other side. The device sits behind a connector. You (the user, with the client and your identity) are checked, and the connector forwards your traffic to that one device and port. The device never needs to know Twingate exists, and you do not need a **jump host** (a machine you log in to first, then hop from). Put such devices on their own subnet so the firewall can name them.

Tailscale offers a comparable feature called a **subnet router**: a machine that extends your Tailscale network to devices that cannot run the Tailscale client. Tailscale's [subnet routers page](https://tailscale.com/kb/1019/subnets) (read 2026-10-21) describes it as a gateway between your tailnet and a conventional subnet, for printers and legacy networks. The two are the same idea with different products; how they differ in access control and in what is reachable by default I did not compare for this page. Both leave the device itself unprotected: whoever reaches it is trusted by that device, so keep the path narrow.

## Honest limits

- **A connector is a high-value target.** It sits inside your network and can reach what its firewall allows. Compromise one and the attacker starts from there. That is why it has its own VLAN, minimal rules and patches.
- **The identity provider is now critical.** If the IdP is down you cannot sign in; if an attacker takes it over they hold your roles. Protect it with phishing-resistant MFA, as on [Identity basics](Identity-Secrets-and-Zero-Trust-Basics.md#mfa-and-identity-providers).
- **Role-based reach from an identity provider is a plan question.** From this repository's checked guidance (2026-10-19, see [Build it: zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md)): the free Starter plan (up to 5 users) signs in with a social login (Google, Microsoft, GitHub or LinkedIn); directory integrations such as Entra ID, JumpCloud, Okta, OneLogin and Keycloak are listed as Business and Enterprise features, so they need a paid Twingate plan. The SAML requirement was not stated on the pages read there, and none of the Twingate pages read on 2026-10-22 uses the word SAML; confirm it. Separately, Twingate's pricing page lists service accounts (which headless clients use) on Home, Business and Enterprise and not on the free Starter plan, so cloud-to-home automation is a second plan question; see [Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md). Check the pricing page on the day.
- **The two Pis share a house.** Power, switch and router are single points of failure.
- **Connector telemetry is off by default.** If you turn on the optional connection analytics, each line names the user's email, client IP and city (see [Twingate: connector telemetry](Twingate.md#connector-telemetry-off-by-default)), and you should then treat those logs as personal data. With it off, that identifying detail is not written.

## Cost

The reading is free. For the hands-on parts you use your own hardware (two Raspberry Pis or two virtual machines) or, if you prefer, two small cloud instances at the provider's price; see [cost](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md). Nothing here is sold; the plan limits above are the vendor's, not mine.

## Exercises

Each has predict, do, check, undo.

### Exercise 1: draw the trust boundaries of your own home network (free, paper)

- **Predict.** How many separate trust zones does your home network have? Most people say one.
- **Do.** On paper, draw your router, every device, and the internet. Draw a line around every group of devices that should not trust each other (guests, smart devices, work laptop, anything you cannot patch). Mark every place a connection can start from the internet. Compare with [Threat model exercise: trust boundaries](Threat-Model-Exercise.md#step-2-draw-the-trust-boundaries).
- **Check.** Every line you drew should answer: what is allowed across it, and who decided? A flat network has no lines; that is the finding.
- **Undo.** Nothing to undo; keep the drawing.

### Exercise 2: a model of failover with two containers (free, own computer; commands not run, est.)

This is a **model**, not Twingate. A "hub" waits for check-ins; two "connectors" dial out to it. It shows two ideas only: the hub listens on no published port, and the work continues when one connector stops. Needs Docker or Podman. The images are public; downloading them is an internet use on your side. **Why the images are pinned by digest:** a tag such as `3.12-slim` or `latest` is mutable, so the same name can point at different contents next week, including after a compromise of the publisher's account. A digest names exact contents. The digests above are the multi-architecture index digests of `python:3.12-slim` and `curlimages/curl:latest`, read from Docker Hub's registry API (read-only) on 2026-10-21; they go stale as the publisher releases updates, so refresh them: `docker buildx imagetools inspect python:3.12-slim` (or `skopeo inspect --raw docker://docker.io/library/python:3.12-slim | sha256sum`) prints the current one. Pin, then update on purpose.

- **Predict.** After you stop connector `a`, will the hub's log still show check-ins? From which connector?
- **Do.**

```bash
docker network create zt-lab
docker run -d --name zt-hub --network zt-lab python:3.12-slim@sha256:cb33f7f771ecec2ef1225cf39b159591a040391bd73e4c01f00fdfc4c47611d2 python -m http.server 8000
for n in a b; do
  docker run -d --name "zt-conn-$n" --network zt-lab --entrypoint sh curlimages/curl@sha256:11e64e28c5f58c8d93ee95fcf22ac055f48b0bc440e0ce7d8013bbb5ad6aa8ac \
    -c "while true; do curl -s -o /dev/null http://zt-hub:8000/?from=$n; sleep 2; done"
done
sleep 6; docker logs --tail 6 zt-hub
docker stop zt-conn-a
sleep 8; docker logs --tail 4 zt-hub
```

- **Check.** The first log shows both `from=a` and `from=b`. After the stop, new lines show only `from=b`. Also confirm nothing was published: `docker port zt-hub` prints nothing. If your output differs, say so on the pull request; I could not run this.
- **Undo.** `docker rm -f zt-hub zt-conn-a zt-conn-b; docker network rm zt-lab`

Honest limit: this does not test Twingate's sessions, relays or client behavior, only the outbound-only and redundant shape.

### Exercise 3: two Pis or two virtual machines (optional, own hardware)

- **Predict.** With both connectors online, what happens to an open SSH session when the connector it uses stops? (It may drop; a new connection should work through the other.)
- **Do.** Follow Twingate's own connector deployment documentation to install two connectors in one remote network, on separate machines. Put them on their own network segment if your gear allows it. Use a free social-login account to start. Use only a lab resource you do not mind losing.
- **Check.** Both show online. Stop the connector your session uses: the session may drop, and a **new** connection works through the other. Start it again and wait for it to show online. Then do the same to the other one.
- **Undo.** Remove the connectors and revoke their tokens in the admin console. Check the vendor's pricing page before leaving anything running.

### Exercise 4: write the firewall rules by role (free, paper)

- **Predict.** How many rules does the connector VLAN need? (The table above has seven; could you do with fewer?)
- **Do.** Pick three roles (for instance admin, lab, guest) and three subnets with placeholder addresses. For each role write the allowed resource, the port, and the reason. Then write the default-deny line.
- **Check.** For every rule ask: who is the identity, which resource, which port? A rule that says "any" in the port column is a VPN rule; justify it or narrow it.
- **Undo.** Nothing to undo.

## Build, break, detect, evade, defend, flip

A mini-loop for this design.

| Step | Question | Here |
|---|---|---|
| **Build** | What is the smallest working version? | Two connectors, own VLAN, roles in Twingate groups, firewall limits on the connectors, host patches automated (connector containers updated by hand) |
| **Break** | What happens when a part fails? | Stop one connector, then the other; the table of failures above |
| **Detect** | How would you know? | Connector offline in the console; host patch notifications (container updates are a manual check); the identity provider's sign-in log |
| **Evade** | How would an attacker avoid being noticed? | Use a stolen identity-provider session so the traffic looks like you; stay inside the allowed resource |
| **Defend** | What stops that? | Phishing-resistant MFA, device checks where available, narrow resources, alerts on odd sign-ins |
| **Flip** | What if you were the attacker on the connector host? | You hold whatever its firewall can reach; the VLAN and default deny are what limits you |

## Further reading

- [How Twingate works](https://www.twingate.com/docs/how-twingate-works) and [Connector best practices](https://www.twingate.com/docs/connector-best-practices), Twingate docs
- [Allowlist for outbound connections](https://help.twingate.com/articles/1198271128-allowlist-for-outbound-connections-to-twingate-infrastructure), Twingate help
- [Subnet routers](https://tailscale.com/kb/1019/subnets), Tailscale docs
- [Patch Gremlin](https://github.com/ChiefGyk3D/Patch-Gremlin), the maintainer's patch-notification project
- [RFC 5737: documentation address blocks](https://www.rfc-editor.org/rfc/rfc5737)
- [NIST SP 800-207: Zero Trust Architecture](https://csrc.nist.gov/pubs/sp/800/207/final)
- On this wiki: [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md), [Twingate](Twingate.md), [Enterprise networks](Enterprise-Networks-Campus-Branch-Datacenter-Cloud.md), [A small example: the enterprise landscape](Small-Example-Enterprise-Landscape.md)

Next: [Twingate](Twingate.md).
