# Behind a CDN: real client IPs, why an IP is a weak identifier, and OSI basics

Side page to the start-from-zero pages. Read it after [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) (which puts a site behind Cloudflare and locks the server to it) and [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md), and beside [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md), whose loopback lab this page borrows its vocabulary from. It answers one practical question (when a CDN stands in front of your server, whose address does your server see, and what breaks if it sees the wrong one?) and then two bigger ones that the answer leads to: how much an IP address can tell you about anybody, and where in the layered model of networking each of this project's controls sits. Next: [Reading order](Reading-Order.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Related lessons that may not open yet.** The network and host defense track is being written at the same time as this page. [Packet filters compared: iptables and ipset, nftables, UFW, and BSD pf](Packet-Filters-Compared-iptables-nftables-ufw-pf.md) and [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md) are linked below by their exact names. **Until each is merged, the link to it leads nowhere.** Nothing on this page depends on reading them first, and that is why the "Next" line above names a page that exists today.

> **Status: the free local lab was run once on Linux; everything else was not run.** On **2026-10-22** the author ran every Bash command in the free lab on Linux with nginx 1.26.3 (built with the real-IP module), Python 3.13.5 and curl 8.21.0, all on `127.0.0.x` addresses, and pasted trimmed output from those runs. The Cloudflare range fetch in Exercise 7 was run the same day against the public list. **Not run:** every PowerShell command (there was no Windows machine and no PowerShell on the machine; they are written from the Bash ones and marked **est.**), anything on macOS (where the extra `127.0.0.x` addresses need to be added by hand, est.), Apache `mod_remoteip`, fail2ban, any application framework setting, any real CDN, load balancer or firewall, and every statement about Tor, residential proxy networks and ISP address rotation (general knowledge, marked **est.**). Vendor and standards facts were read from the pages named in the [claims register](#claims-register) on **2026-10-22**. Output varies with your versions and the date.

> **Prerequisites.** [How a web request works](How-a-Web-Request-Works.md) (DNS, TCP, TLS, HTTP and what a proxy is) and [Networking basics](Networking-Basics-for-This-Project.md) (addresses, ports). [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) helps a lot, because this page starts where its "Lock the origin to Cloudflare" section stops. A terminal ([Git from zero](Git-From-Zero.md) has a first look). The free path needs `nginx` (with the real-IP module, which Debian and Ubuntu builds include), `python3`, `curl` and a Linux machine or WSL 2; no account, no money. The reading and the exercises are free and always will be. About three hours for the reading and the lab (est.).

## What you will be able to do

- Explain why a server behind a CDN or reverse proxy sees the proxy's address on every connection, and what that does to its logs, its firewall, its rate limiter and its ban lists.
- Name the ways the real client address is passed along (headers, the PROXY protocol), what each can carry, and what none of them can prove.
- State the trust rule in one sentence, and configure Nginx so it follows it: believe the address in a header only when the connection came from a proxy you trust.
- Show, on your own computer, the three results that matter: the proxy is the only address you see, a forged header is believed, and a trusted-proxy rule fixes it. Then show a rate limiter that blocks everybody, and the same limiter blocking only the abuser.
- Explain why an IP address is a weak identifier: shared addresses, carrier-grade NAT, moving addresses, one address in many places, and an organization reachable through several networks under one autonomous system number (ASN).
- Draw the seven-layer OSI model and the four-layer TCP/IP model side by side, say which layer each tool in this wiki works at, and say honestly where the models stop being useful.
- Point to where to go for on-premises networking in depth.

## Why this page exists

The maintainer asked for it on 2026-10-22, and the substance of his request is the outline of this page. In his words: anything behind Cloudflare that needs the visitor's address for its own firewall has to be documented, "how to pass that stuff along and how that works and why that happens with Cloudflare, because many requests come from one IP address", so that the firewall does not "accidentally block cloudflare". He added that, contrary to popular belief, "IP addresses are not that much of an identifier": an organization can own address space and have it reachable through several providers and backbones under an ASN (an autonomous system number; the term is defined [below](#asns-and-bgp-one-organization-several-roads)). He also asked for the OSI model and the basics of networking from that side, linked to pfSense for depth on on-premises networking and to his two SIEM repositories, "because this project is mainly cloud oriented".

### What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| A proxied site hides the server's address, and the server should refuse everyone but the CDN | [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md#lock-the-origin-to-cloudflare) | That lesson locks the door. It does not say what the server sees once the door is locked: only the CDN's address. The material on [origin locking and TLS modes](DNS-Cloudflare-and-Hosting-Your-Own-Website.md#tls-between-the-visitor-cloudflare-and-your-server) is not repeated here. |
| CDN, WAF, load balancer, rate limit at concept level, with a loopback lab | [WordPress at scale](WordPress-at-Scale-CDN-WAF-and-CI.md#what-a-cdn-a-waf-and-a-load-balancer-each-do) | That lab's login limit counts the address the edge sees. Here the same idea is broken and fixed behind a proxy. |
| Addresses, CIDR, NAT, default deny | [Networking basics](Networking-Basics-for-This-Project.md), [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) | Nothing about how reliable an address is as an identifier, or about BGP and ASNs. |
| Layers of networking | Scattered words ("layer 4", "TLS") | A single table that places every tool. |

## The problem: every request comes from the proxy

Without a CDN, a visitor's connection reaches your server directly, and the server's socket records the visitor's address. That address is what your access log prints, what your firewall matches, what your rate limiter counts and what fail2ban bans.

With a CDN or any **reverse proxy** (a server that receives requests on behalf of other servers and forwards them), there are **two** connections. The visitor connects to the proxy. The proxy opens a **second, new** connection to your server. Your server's socket belongs to the second one, so its peer is the proxy.

```text
 visitor 203.0.113.7  ---->  CDN edge 192.0.2.50  ---->  your origin
                      conn 1                      conn 2
 what the origin's socket says the client is:   192.0.2.50   (the CDN)
 what the origin wants to know:                 203.0.113.7  (the visitor)
```

Cloudflare's documentation says it plainly: because Cloudflare is a reverse proxy, "when responding to requests and logging them, your origin server returns a Cloudflare IP address", and applications "that depend on the incoming IP address of the original visitor" will log a Cloudflare address by default (retrieved 2026-10-22). AWS says the same of its load balancers: your server access logs "only contain the IP address of the load balancer" ([claims register](#claims-register)).

And there are **few** CDN addresses and **many** visitors. Cloudflare publishes its ranges as short lists (the Exercise 7 fetch counted 15 IPv4 and 7 IPv6 ranges on 2026-10-22) and says they are "shared by all proxied hostnames". Thousands of unrelated visitors arrive from the same handful of addresses.

### The accidental self-block

Now give the origin the tools from [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) and the rate limiter from the WordPress lesson, and let them all work on the address they see:

- A **rate limiter** that allows "5 logins a minute per address" counts the CDN as one address. The first few visitors use the budget up, and every later visitor, including the owner, is refused.
- A **ban list** (fail2ban, a firewall deny rule, a WAF block) that reacts to one abusive request now bans the CDN's address. The site goes dark for everyone, which is the attacker's goal achieved with one bad request.
- **Logs** show one "visitor" with a million requests, so you cannot tell a crawler from a customer from an attack, and a security tool that scores by source address sees nothing useful.
- **Allow-lists by address** (an admin page "only from the office") see the CDN, not the office.

None of this is a bug in the CDN. It is what a proxy does. The fix is to learn the real address from the proxy and use that, **but only from a proxy you trust**, which is the part people get wrong. Exercise 1 reproduces the self-block, and Exercise 2 reproduces the wrong fix.

## How the real address is passed along

A proxy can tell your server who the client was in two ways: **in the HTTP request** (a header, which works only for HTTP) or **in front of the request** (the PROXY protocol, which works for any TCP service).

| Mechanism | What it is | Carries | Cannot do |
|---|---|---|---|
| `CF-Connecting-IP` | A header Cloudflare adds: "the client IP address connecting to Cloudflare to the origin web server", sent only on traffic from Cloudflare's edge to your origin (Cloudflare HTTP headers, 2026-10-22). | One address | Prove itself: it is just text. The proxy overwrites a client-supplied copy; a request that did not come through the proxy can carry any value. |
| `True-Client-IP` | The same value under another name, available "on an Enterprise plan" only; the page says there is "no difference ... besides the name". | One address | The same limits. Useful when an older product expects that name. |
| `X-Forwarded-For` (XFF) | A de facto standard header holding a **list** of addresses, nearest hop last. If the request had none, Cloudflare sends the visitor's address; if it had one, Cloudflare **appends**. AWS's Application Load Balancer defaults to append, and can be set to `preserve` or `remove`. | A chain | Tell you which entries are honest: every entry added before your first trusted proxy came from somebody else. |
| `Forwarded` ([RFC 7239](https://www.rfc-editor.org/rfc/rfc7239)) | The standardized replacement: `Forwarded: for=192.0.2.60;proto=http;by=203.0.113.43`. Carries the address, the protocol and more, with IPv6 in quotes. | Address, protocol, host, proxy identity | The RFC's own security section: it "cannot be relied upon to be correct, as it may be modified ... by every node on the way to the server, including the client". Many products still send only the older headers. |
| `X-Real-IP` | A common single-address header written by Nginx-style proxies. Nginx's real-IP module reads it by default. | One address | The same limits. |
| PROXY protocol | A line (version 1) or a binary block (version 2) the proxy sends **first**, before any of the client's bytes, carrying the client and server addresses and ports. Specified by HAProxy's authors. | Addresses and ports for any TCP protocol, including TLS passed through untouched | Work unless the receiver is told to expect it: the receiver "MUST be configured to only receive the protocol" and must not guess whether the header is present. |

Two clarifications that save hours:

- **A CDN may offer both, or a vendor-specific one.** Amazon CloudFront can add `CloudFront-Viewer-Address` (the viewer's address and source port, for example `198.51.100.10:46532`) and `CloudFront-Viewer-ASN` through an origin request policy. Other CDNs have their own names. The pattern is the same: a header, plus the CDN's published ranges to decide whether to believe it.
- **Why the PROXY protocol exists.** A header can only be added by something that understands HTTP, which means the proxy must have decrypted the TLS. A plain TCP load balancer in front of, say, an SSH or SMTP server, or a TLS pass-through balancer, cannot add a header. The PROXY protocol lets such a proxy hand over the original address in a line the receiver strips off before it parses its own protocol. The specification says the whole point is to "safely transport connection information such as a client's address across multiple layers of NAT or TCP proxies".

Cloudflare also has two options worth knowing. **Remove visitor IP headers** (a Managed Transform) strips every header that may contain the visitor's address, for sites that want the privacy and do not need the address. **Pseudo IPv4** can add a `CF-Pseudo-IPv4` header (an address from the Class E block, hashed from the visitor's IPv6 address) or overwrite `Cf-Connecting-Ip` and `X-Forwarded-For` with it, with the real IPv6 address kept in `CF-Connecting-IPv6`, for software that cannot handle IPv6 (Cloudflare HTTP headers, 2026-10-22). If your logs show strange `240.x` addresses, this setting is why.

## The trust problem

Anyone can type `X-Forwarded-For: 198.51.100.9` into a request. Anyone can send `CF-Connecting-IP`. A header is only text. So "use the address from the header" is a vulnerability unless it comes with a rule about **whom to believe**. The rule has four parts:

1. **Believe a header only when the connection came from a proxy you trust.** For a CDN, that means the CDN's published ranges and nothing else. Nginx calls the trusted addresses `set_real_ip_from`, and its documentation says they are "known to send correct replacement addresses". If the connection came from anywhere else, **ignore the header**.
2. **Make the proxy overwrite, not trust, what the client sent.** Cloudflare overwrites a client-supplied `CF-Connecting-IP`. For `X-Forwarded-For` a proxy usually **appends**, so the client's own copy stays at the **left** of the list. That is why you read the list from the **right**: the entries you can trust are the ones added by your own proxies, and the first address from the right that is not one of yours is the client. Nginx does this with `real_ip_recursive on`: it picks "the last non-trusted address sent in the request header field". Apache's `mod_remoteip` documents the same right-to-left processing.
3. **Close the other door.** If the origin answers anybody, an attacker skips the CDN, connects straight to the origin, and sends whatever header they like. If every source is trusted, anybody can forge any identity. The origin must accept connections from the proxy only ([the DNS lesson](DNS-Cloudflare-and-Hosting-Your-Own-Website.md#lock-the-origin-to-cloudflare) shows the cloud firewall way). Exercise 2 shows the failure and Exercise 4 the second lock.
4. **Know your tool's default.** Apache's documentation says that, unless `RemoteIPInternalProxy` or `RemoteIPTrustedProxy` is used, "mod_remoteip will trust all hosts presenting a RemoteIPHeader IP value". That default is the spoofing hole in a single line. Nginx's module has no trusted list until you write one, so it changes nothing by default. Read the default of every tool you turn this on in.

Even a correct setup has a limit. The RFC 7239 security section points out that trusting a proxy covers only what that proxy saw: "the chain of IP addresses listed before the request came to the proxy cannot be trusted", and without protection between the proxy and your server, the header "can be modified by an attacker with access to the network". The PROXY protocol specification adds the same warning in its own words: accept the header "only from a number of known sources", or a normal client can "make [its activities] appear as coming from someone else".

An address you restored this way is **a better guess, not a proof**. It is the address the CDN saw, which is as good as the connection. Behind that address may be a shared network, a VPN or a compromised phone ([below](#why-an-ip-address-is-a-weak-identifier)).

## Setting it up, component by component

The principle is the same everywhere: tell the component **which peers are proxies it may believe**, and **which header to read**.

### The web server

**Nginx** needs the real-IP module (`ngx_http_realip_module`, "not built by default" per its documentation, though the common Debian and Ubuntu packages include it; check with `nginx -V`). Its three directives:

```nginx
# Trust these peers (the CDN's ranges), read this header, and walk XFF from the right.
set_real_ip_from 192.0.2.0/24;          # one line per published CDN range, IPv4 and IPv6
real_ip_header CF-Connecting-IP;        # or X-Forwarded-For, or proxy_protocol
real_ip_recursive on;                   # only matters for X-Forwarded-For
```

The module keeps the connection's own address in `$realip_remote_addr`, which matters later. A real deployment keeps the range lines in a generated file and pulls it in with `include`; Exercise 7 builds that file from the published list. Cloudflare's own instructions for Nginx say the same thing and add: "That list of prefixes needs to be updated regularly". To log both addresses, Cloudflare suggests adding `$http_cf_connecting_ip` and `$http_x_forwarded_for` to the `log_format`.

**Apache** uses `mod_remoteip` (Cloudflare retired its own `mod_cloudflare` and recommends `mod_remoteip`):

```apache
RemoteIPHeader CF-Connecting-IP
RemoteIPTrustedProxy 192.0.2.0/24
# and change %h to %a in the LogFormat so the log shows the restored address
```

Because of the default quoted above, never write `RemoteIPHeader` without a `RemoteIPTrustedProxy` or `RemoteIPInternalProxy` line. This snippet is **est.**; it was read from the documentation and not run.

**Other servers:** HAProxy, Envoy, Caddy, IIS and others have their own settings; Cloudflare's restoring-IPs page has a section for many of them. The shape is always peers-to-trust plus header-to-read.

### The application

Your web server may know the real address while your application still sees the proxy, because the application reads the socket or its own header, not Nginx's idea. Every web framework has a setting with a name like "trusted proxies":

- **Express (Node.js):** the `trust proxy` setting. Its documentation warns that the setting trusts values in the request, so it "must match how the reverse proxy operates", and that with `true` the client is "the left-most entry in the X-Forwarded-For header", which is exactly the entry a client controls. Prefer a count of hops or a list of subnets.
- **Flask and other WSGI apps (Werkzeug):** the `ProxyFix` middleware, with `x_for` set to "the number of values to trust"; the documentation says it "is a security issue to trust values that came from the client rather than a proxy".
- **Laravel, Rails, Django and others:** each has the equivalent (a trusted-proxies list). These names were not read for this page (**est.**); look up the one for your framework and read its default.

The common mistake is to set it to "trust everything" because it makes the number in the log look right. That reopens the spoofing door from inside the application.

### Logs

Log **both** addresses: the restored client and the connection's own peer. The lab's `log_format` does exactly that (`client=` and `via=`). When the two differ, a trusted proxy was involved; when they are equal on a site that is supposed to be behind a CDN, somebody connected to the origin directly, which is a finding on its own. Logs are also where privacy law bites: an IP address is often personal data, and how long you keep it is a decision, not a default (this page gives no legal advice).

### fail2ban and other ban tools

fail2ban reads a log file, extracts an address from each matching line, and bans that address with a firewall action. Two consequences:

- If the log holds the CDN's address (Exercise 1 shows this), fail2ban bans the CDN. Its `jail.conf` has an `ignoreip` setting ("a list of IP addresses, CIDR masks or DNS hosts" it will not ban) and says `ignoreself` defaults to true. Putting the CDN's ranges in `ignoreip` is a **safety net** that stops the self-block; it does not make the bans work.
- The fix is to log the restored address, so the line fail2ban reads names the visitor. But a ban at the **origin's** firewall then does nothing useful: the visitor's packets never reach the origin from their own address, they arrive from the CDN, so a rule that drops the visitor's address matches nothing. To stop a visitor you have to block at a layer that sees the visitor: the **CDN's own firewall rules**, or an application-level deny (the web server refusing the restored address). fail2ban ships a Cloudflare action (`action.d/cloudflare.conf`, read but not run) that asks Cloudflare's API to do the ban.

That last point is the one that surprises people, so it is worth stating again as a rule: **a firewall at the origin can only ban peers, and behind a CDN the peers are the CDN.** Ban visitors in the CDN or in the web server, and keep the origin's firewall for "only the CDN may connect".

### The rate limiter

Rate limiters key on an address. In Nginx, `limit_req_zone $binary_remote_addr` keys on the address the module has restored, so enabling the real-IP module is what makes the limiter count the visitor. The documentation describes the limiter as limiting "the processing rate of requests coming from a single IP address", and the address it means is whatever `$remote_addr` is at that point. The same is true of any limiter that uses the connection address: it needs the restored one. [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md) goes through the other layers and keys. Exercise 3 shows the difference with numbers.

### The origin firewall, and what changes

The origin firewall is the lock from [the DNS lesson](DNS-Cloudflare-and-Hosting-Your-Own-Website.md#lock-the-origin-to-cloudflare): allow ports 80 and 443 **only** from the CDN's published ranges, refuse the rest. Cloudflare's documentation recommends it ("block all traffic that does not come from Cloudflare IP addresses or the IP addresses of your trusted partners, vendors, or applications"). Restoring the real address changes four things:

1. **The firewall is not changed.** A network firewall matches the packet's real source, the CDN. Restoring an address in the web server happens later and above it. Do not "add the visitors" to the firewall; they never connect.
2. **Never block the CDN's own addresses**, including by a broad "deny country" or "deny bad reputation" list that happens to cover them, and including by an automatic ban tool. Test after every firewall change by loading the site through the CDN.
3. **Address checks in the web server move.** After the real-IP module runs, `$remote_addr` is the visitor. A rule like "allow only 192.0.2.0/24" written with Nginx's `allow` and `deny` is now checked against the visitor, not the connection. To check the connection, use `$realip_remote_addr`. Exercise 4 does this, and an Apache `Require ip` rule changes in the same way (the documentation says the replaced address is "used for the mod_authz_host Require ip feature").
4. **IPv6 needs its own lines.** Allow-lists for IPv4 do not cover IPv6. Cloudflare publishes both lists. A site that is reachable over IPv6 but whose firewall and real-IP lists cover only IPv4 will, depending on the setup, log the CDN as the client or refuse the CDN's IPv6 connections (est.).

### When the CDN's ranges change

Cloudflare says its ranges "do not change frequently" and that, when they do, they are "added to our list of IP ranges before being put into production", so a change is announced before it matters, and it publishes an API for keeping a configuration current. A copy-pasted list in a config file is a time bomb: the day a new range is used and your list lacks it, the new range's connections are refused by the firewall, or arrive at Nginx untrusted and unrestored.

Treat the list as data you refresh, not text you wrote:

- Fetch it from the CDN's page on a schedule (a timer or a pipeline job) and regenerate the firewall rules and the Nginx include file from it.
- **Fail closed on a bad fetch:** if the download fails, is empty or has an implausible number of lines, change nothing and alert. Exercise 7 does this.
- **Diff against the last list** and alert when it changed, so a human looks.
- Reload the web server (or the firewall) only after the generated file passes its own syntax test (`nginx -t`).

### Failure modes

| Failure | What you see | Cause and check |
|---|---|---|
| Stale range list | Some visitors logged as the CDN, or some CDN connections refused, intermittently | A new range is not in your lists. Refresh from the published page; compare. |
| Forged header accepted | A client picks its own identity, evades rate limits or frames somebody | Trust list too wide (`0.0.0.0/0`, a whole private range, Apache without a trusted list), or the origin reachable directly. Exercise 2. |
| Header missing on some requests | The log shows the CDN or the load balancer as the client for a few paths | Health checks and internal calls come straight from the load balancer and carry no header. Fine, but they must not be counted or banned as clients. A Cloudflare setting such as a Managed Transform or a Transform Rule can also remove the header (the restoring-IPs page says to check these). |
| Double proxy | The address in the log is a CDN address, or a private one | Two proxies in front (CDN, then your own load balancer): both must be trusted, `real_ip_recursive on`, and the XFF walk must skip both. Exercise 5 walks the arithmetic. |
| Everyone is one address | A rate limit or ban hits all users at once | The real-IP module was never enabled, or the rule uses the wrong variable. Exercise 1. |
| Self-block | The site is down for everyone after one bad request | A ban tool acted on the CDN's address. Add the CDN to its ignore list, fix the log, and ban at the CDN. |
| PROXY protocol mismatch | Every request fails, or garbage in the log | One side sends the header and the other does not expect it, or the reverse. Never autodetect; configure both ends the same way. |
| Spoofed first XFF entry used by the app | Logs show a made-up address that is nobody's | The app reads the left-most entry. Read from the right, or use a trusted-hops setting. Exercise 3. |

## Why an IP address is a weak identifier

After all this work to restore the visitor's address, a warning, which is the maintainer's point: **an IP address is not much of an identifier.** It is a number that tells the network where to send packets for the moment, not a statement about who is at the other end. Use it as a **signal**, never as the only thing that decides who somebody is.

### Many people behind one address

- **NAT at home and at work.** A router rewrites many private machines onto one public address ([Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md#nat-and-port-forwarding)). A household, an office or a university campus can be one address for thousands of people. Block it and you block them all.
- **Carrier-grade NAT (CGNAT).** Internet providers run the same trick at scale. [RFC 6598](https://www.rfc-editor.org/rfc/rfc6598) reserves `100.64.0.0/10` as "Shared Address Space" for it. Many mobile and some home customers share one public address with strangers, and the share changes (how any one carrier does it is est.). A limit or ban on that address hits unrelated people. See also the [CGNAT entry in the Glossary](Glossary.md).
- **VPNs and Tor.** A VPN gives many customers the provider's addresses; the Tor network does the same through exit relays (est.). A VPN user can look like they are in another country, and a bad actor can look like an ordinary customer of the same provider.
- **Mobile carriers.** A phone changes address as it moves between towers and networks (est.).
- **Cloud egress.** Servers in a cloud often share addresses (a NAT gateway), and traffic from a data center is a bot, a backup job, or a customer's CI run, not a person.

### One person, many addresses

- **Addresses move.** A home address may change when the router restarts or the provider rebalances; IPv6 hosts also use temporary addresses by design ([RFC 4941](https://www.rfc-editor.org/rfc/rfc4941)), which are generated to make a device harder to follow, and a provider may change the **prefix** it hands to a home (est.). Counting "distinct IPs" overcounts one person on IPv6.
- **Rotation as a service.** Residential proxy networks route traffic through ordinary customers' connections, so an abusive client can present thousands of different home addresses that each look like a normal household (est.). A per-address limit does nothing against it, and a country or reputation block can hit the household that did not know it was a relay.

### Anycast: one address, many places

**Anycast** is, in the words of [RFC 4786](https://www.rfc-editor.org/rfc/rfc4786), "making a Service Address available to a routing system at Anycast Nodes in two or more discrete locations". The same address is announced from many data centers, and the network sends each client to a nearby one. That is how a CDN's few addresses serve the whole world and why a Cloudflare address does not point at one machine in one city. For you it means two things: an address does not name a place, and the same address can be answered by different hardware for different visitors.

### ASNs and BGP: one organization, several roads

The internet is a network of networks. Each large network that decides its own routing is an **autonomous system**, and it has an **autonomous system number**, an **ASN**. [RFC 1930](https://www.rfc-editor.org/rfc/rfc1930) defines an AS as "a connected group of one or more IP prefixes run by one or more network operators which has a SINGLE and CLEARLY DEFINED routing policy". (A **prefix** is a block of addresses written like `203.0.113.0/24`.) Networks tell each other which prefixes they can reach using the **Border Gateway Protocol (BGP)**, defined in [RFC 4271](https://www.rfc-editor.org/rfc/rfc4271), whose "primary function ... is to exchange network reachability information with other BGP systems", including "the list of Autonomous Systems (ASes) that reachability information traverses".

What that means in practice, and it is the maintainer's point: an organization can **own** address space, run its own ASN, and announce its prefixes to **several providers and backbones at once**. RFC 1930 calls a site connected to more than one provider "multi-homed" and says such a site should have an AS of its own. The same block of addresses is then reachable over several roads, and traffic from the same organization may enter the internet through different providers on different days. (The standard says that, in general, a prefix has one **origin** AS, so "one prefix, one owner ASN, many upstream providers" is the normal shape.) So "which ISP is this address from?" does not have a single answer, and different ISPs' customers can share one network operator's address space.

**An ASN lookup** (a public routing database or a service built on one) turns an address into "the AS that announces the prefix containing it, and its name". At a beginner level it tells you:

- **What it tells you:** which organization's network announces that address. A hosting company, a cloud, a campus, a mobile carrier or a residential ISP is a strong signal. "The traffic comes from a data center" is a good reason to treat a login attempt differently from "from a residential ISP".
- **What it does not tell you:** who the user is; whether the address is shared; where the person is; or whether the organization's customers behave. An ASN is the **operator**, not the **tenant**. A cloud's ASN covers every customer of that cloud, honest or not.

Exercise 8 builds a small table at run time with documentation numbers and shows how a lookup works and what it leaves out.

### Geolocation is a guess

Databases that map an address to a country or a city are built from registry data, routing data and measurements. The maker of one such product states on its own accuracy page that it is "not possible for us to guarantee 100% geolocation accuracy", that accuracy varies "according to country, distance, type of IP (cellular vs. broadband, IPv4 vs. IPv6), and practices of ISPs", and that the data "is never precise enough to identify or locate a specific household, individual, or street address" (MaxMind, retrieved 2026-10-22). It adds that for a VPN user it may locate the VPN server and not the person. A country block is a blunt tool for those reasons, and anycast and VPNs make it blunter.

### What to use alongside an IP

Treat the address as one input among several, and prefer signals that belong to a **person or session**, not a network position:

- **Accounts and sessions:** rate-limit and lock per account, per token and per session, not only per address. Credential-stuffing from many addresses against one account is invisible to an address limit and obvious to an account limit.
- **Tokens and keys:** [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) covers API keys and per-client limits. A key identifies a caller far better than an address.
- **Device signals:** a client certificate, a device-bound token, a browser or device fingerprint (with privacy and legal cost; est.).
- **Behavior:** request rate over time, the paths hit, failure ratio, time between requests, and what happens after login.
- **Network context as a score, not a verdict:** the ASN class (data center, residential, mobile), the country, whether the address is a known relay. Combine them; do not block on one.
- **Defense in depth:** the CDN's challenge pages and bot scoring, which see far more than one address.

## OSI and TCP/IP for cloud people

This project is cloud-oriented, so the on-premises layers (cables, switches, VLANs) are mostly somebody else's problem here. They still shape the words every vendor uses, so here is the short version.

### The two models

The **OSI model** (Open Systems Interconnection, an ISO standard, ISO/IEC 7498-1; not read for this page, **est.**) divides networking into seven layers. The **TCP/IP model**, which the internet actually runs, uses four. The host-requirements standard [RFC 1122](https://www.rfc-editor.org/rfc/rfc1122) describes the communication layers of an Internet host as the link layer, the IP layer and the transport layer, with the application protocols in its companion RFC 1123.

| OSI layer | Name | TCP/IP layer | What it does | Examples |
|---|---|---|---|---|
| 7 | Application | Application | What the program speaks | HTTP, DNS, SSH, SMTP |
| 6 | Presentation | Application | Formats and encoding, including encryption in the textbook | TLS (placed here or at 5 or 4, depending on who you ask), JSON, character sets |
| 5 | Session | Application | Keeping a conversation going | Login sessions, RPC (rarely a separate thing in practice) |
| 4 | Transport | Transport | Ports, and reliability or not | TCP, UDP |
| 3 | Network | Internet | Addresses and routing between networks | IP (IPv4, IPv6), ICMP |
| 2 | Data link | Link | Delivery on one local network | Ethernet, Wi-Fi, MAC addresses, VLAN tags |
| 1 | Physical | Link | Bits on the medium | Cable, radio, fiber |

People say "layer 7" for the application, "layer 4" for TCP and UDP, "layer 3" for IP, and "layer 2" for Ethernet. The middle layers (5 and 6) are rarely named in practice.

### Where each tool sits

| Tool | Works at | What it can see | Why that matters here |
|---|---|---|---|
| **Switch** | 2 | MAC addresses and VLAN tags | Moves frames inside one network. |
| **Router** | 3 | IP addresses | Moves packets between networks; does NAT. |
| **Packet filter / firewall** (iptables, nftables, UFW, pf) | 3 and 4 | Addresses, ports, connection state | The origin lock "only the CDN's ranges on 443". See [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md). |
| **Cloud security group / cloud firewall** | 3 and 4 | The same | The [DigitalOcean firewall](DigitalOcean-Network-and-Firewalls.md) and its AWS equivalents. |
| **Load balancer, layer 4** | 4 | Addresses and ports, not the HTTP request | Passes TCP through; cannot add an HTTP header; uses the PROXY protocol to pass the client. |
| **Load balancer, layer 7** | 7 | The whole HTTP request | Can route by path or host, add `X-Forwarded-For`. |
| **TLS termination** | 6 (by convention) | Decrypts so layer 7 can be read | Where the connection splits into two, and where a header can first be added. |
| **Reverse proxy / CDN** | 7 | HTTP | The two-connection picture at the top of this page. |
| **WAF** | 7 | HTTP requests and responses | Matches attack patterns; behind it, the address is the CDN's unless restored. |
| **DNS** | 7 (and a transport underneath) | Names | Decides which address a visitor connects to. |
| **ZTNA / VPN** | 3 and up | Tunnels IP traffic, or brokers per-app access | [Why ZTNA, not a VPN](Why-ZTNA-Not-a-VPN.md). |

### Which layer each control in this project works at

| Control | Layer | Where |
|---|---|---|
| Cloud firewalls with no inbound rules | 3 and 4 | [Networking basics](Networking-Basics-for-This-Project.md#what-a-firewall-does) |
| CIDR and subnet design | 3 | [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) |
| The origin locked to the CDN's ranges | 3 and 4 | [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md#lock-the-origin-to-cloudflare) |
| Authenticated Origin Pulls (client certificate) | 6 and 7 | The same page |
| The CDN's cache, WAF and rate rules | 7 | [WordPress at scale](WordPress-at-Scale-CDN-WAF-and-CI.md) |
| Real-IP restore, header trust | 7 (using a layer 3 fact) | This page |
| Account and token limits | 7 | [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) |
| Twingate (per-resource access) | 3 and up, brokered | [Twingate](Twingate.md) |

### An honest note about OSI

OSI is a **teaching model**, not a description of how software is built. The internet's protocols were designed under the four-layer architecture, and real protocols cross the lines: TLS does not fit cleanly at 5 or 6, a VPN runs IP inside IP, QUIC (HTTP/3) puts transport behavior in user space on top of UDP, and "layer 8" is a joke about people. Use the numbers as a common vocabulary ("is this a layer 4 problem or a layer 7 problem?") and not as a law. Two practical uses: it tells you what a device **can see** (a layer 4 balancer cannot read a URL), and it tells you where to look when something fails (a refused connection is layer 4, a certificate error is the TLS handshake, a 502 is layer 7).

### On-premises networking in depth: pfSense and the maintainer's SIEM stacks

Cables, switches, VLANs, routing, NAT and firewalls on your own premises are a subject of their own. This project covers the cloud side; for the rest, the next stops are these.

- **pfSense.** Netgate's [pfSense documentation](https://docs.netgate.com/pfsense/en/latest/) covers installing and running the firewall and router; its [firewall fundamentals](https://docs.netgate.com/pfsense/en/latest/firewall/fundamentals.html) and [NAT](https://docs.netgate.com/pfsense/en/latest/nat/index.html) sections are the right starting points (both pages exist; read for their existence on 2026-10-22). This wiki mentions it in [Design a honeynet](Deception-and-Honeypots-Design-a-Honeynet.md) (rule order and VLANs), in [Zero trust at home](Zero-Trust-at-Home-Two-Connectors-and-Failover.md) (the firewall as the outer wall), and in [Packet filters compared](Packet-Filters-Compared-iptables-nftables-ufw-pf.md) (pfSense as pf with a web interface).
- **[pfsense-siem-stack](https://github.com/ChiefGyk3D/pfsense-siem-stack)** (the maintainer's public repository). Its README describes two things that can be used separately: a knowledge base for running Suricata, pfBlockerNG and Telegraf on pfSense, and a SIEM stack that ships pfSense's Suricata alerts and metrics to OpenSearch and Grafana. It says it supports pfSense CE with caveats (see its status table) and that its own SIEM-server installer is the manual path while the canonical server side is the other repository below. I read the README on 2026-10-22; I did not run the code.
- **[siem-docker-stack](https://github.com/ChiefGyk3D/siem-docker-stack)** (the maintainer calls it "docker-siem-stack"). Its README describes a Dockerized SIEM and SOC stack for home labs and small-to-medium businesses, with OpenSearch in hot and warm storage tiers, Logstash, Grafana, Wazuh, Prometheus, InfluxDB and Syslog-ng, taking logs from a pfSense router and Wazuh agents. It carries a notice that it is under active development and that formats may change between releases. I read the README on 2026-10-22; I did not run the code.

Both repositories were public when read. Neither is part of this project's reference environment, and this page does not claim they are installed, tested or supported by it.

## Free hands-on lab: a toy CDN, an origin and a login limit on your own computer

Everything here runs on `127.0.0.x` addresses on your own machine. Nothing is exposed, nothing needs an account, and the only outside request is the read-only fetch of Cloudflare's public range list in Exercise 7.

**The cast.** A tiny Python application on `127.0.0.1:19001` that prints what it can see. An origin Nginx on `127.0.0.1:18082`. A toy "CDN" Nginx on `127.0.0.1:18081` that forwards to the origin **from the address `127.0.0.50`** (Nginx's `proxy_bind`), sets `CF-Connecting-IP` and `X-Forwarded-For` the way a CDN does, and so plays "a CDN with one address". Several "clients" are made with `curl --interface 127.0.0.11`, `.12` and so on: the whole `127.0.0.0/8` block is loopback on Linux, so these need no setup. RFC 5737 documentation addresses (`198.51.100.x`, `203.0.113.x`) appear only inside forged headers, as claims.

```text
  curl --interface 127.0.0.11 ---> toy CDN :18081 ---(from 127.0.0.50)---> origin :18082 ---> app :19001
  curl --interface 127.0.0.66 ------------------------------------------> origin :18082   (the attacker, going around)
```

**Safety.** Every listener is bound to `127.0.0.1`. The Nginx processes run as you, with their own folder, so nothing needs `sudo`. The origin's `/login` path is a pretend login that accepts everything; the lab counts requests to it and nothing else. The forged headers are sent only to your own toy. Do not send them to a site you do not own or operate. If a port is taken on your machine, change the number in all the files with the same edit.

**If you do not have Nginx:** install it from your distribution (`sudo apt install nginx` on Debian or Ubuntu; `nginx -V 2>&1 | grep realip` should print a match), or use WSL 2 on Windows. Without Nginx you can still do Exercises 5 and 8 (pure Python). Running the same Nginx in a container with host networking should work too, but was not tried (**est.**).

### Setup

Make a folder and write the files. The two Nginx configs are generated by `make-conf.sh` so one script produces all four modes.

```bash
# a private folder only you can use (the pid files, logs and Nginx temp files all live here, never in a shared /tmp)
mkdir -p -m 700 ~/cdn-lab && cd ~/cdn-lab
[ "$(stat -c %u .)" = "$(id -u)" ] && [ -z "$(find . -maxdepth 0 -perm /077)" ] || { echo "~/cdn-lab is not private to you; stop" >&2; exit 1; }   # exit closes this shell on purpose
cat > app.py <<'LAB_EOF'
#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# app.py: a tiny application on 127.0.0.1:19001. It prints what it can see about the caller.
# The socket peer is always the proxy in front of it; the headers are whatever the proxy forwarded.
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        h = self.headers
        xff = h.get("X-Forwarded-For", "-")
        body = ("app: socket-peer=%s nginx-decided-client=%s cf-header=%s xff=[%s] naive-first-xff=%s\n" % (
            self.client_address[0], h.get("X-Decided-Client", "-"), h.get("CF-Connecting-IP", "-"),
            xff, xff.split(",")[0].strip())).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # nginx keeps the access log

ThreadingHTTPServer(("127.0.0.1", 19001), H).serve_forever()
LAB_EOF
cat > make-conf.sh <<'LAB_EOF'
#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# make-conf.sh MODE [HEADER]: write the two nginx configs for the lab into the current folder.
#   MODE naive    origin trusts nothing and counts the address it sees (the proxy)
#   MODE trustall origin believes the header from anyone (the spoofing demo)
#   MODE correct  origin believes the header only from the toy CDN's address (127.0.0.50)
#   MODE locked   correct, and the origin refuses any connection that did not come from the CDN
#   HEADER        CF-Connecting-IP (default) or X-Forwarded-For
set -euo pipefail
mode=${1:?naive|trustall|correct|locked}; hdr=${2:-CF-Connecting-IP}
lab=$PWD
case $mode in
  naive)    realip="" ;;
  trustall) realip="set_real_ip_from 0.0.0.0/0; real_ip_header $hdr; real_ip_recursive on;" ;;
  correct)  realip="set_real_ip_from 127.0.0.50; real_ip_header $hdr; real_ip_recursive on;" ;;
  locked)   realip="set_real_ip_from 127.0.0.50; real_ip_header $hdr; real_ip_recursive on;
    if (\$realip_remote_addr != 127.0.0.50) { return 403; }" ;;
  *) echo "mode?" >&2; exit 2 ;;
esac
common="daemon on; worker_processes 1; error_log $lab/error.log notice;
events { worker_connections 64; }"
tmp="client_body_temp_path $lab/tmp/body; proxy_temp_path $lab/tmp/proxy; fastcgi_temp_path $lab/tmp/fcgi; uwsgi_temp_path $lab/tmp/uwsgi; scgi_temp_path $lab/tmp/scgi;"
mkdir -p tmp
# The toy CDN: listens on 18081, talks to the origin FROM 127.0.0.50, and sets the headers the way a real CDN does.
cat > cdn.conf <<C
pid $lab/cdn.pid; $common
http { access_log $lab/cdn-access.log; $tmp
  server { listen 127.0.0.1:18081;
    location / {
      proxy_bind 127.0.0.50;
      proxy_set_header CF-Connecting-IP \$remote_addr;                  # overwrite: a client copy is discarded
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;     # append: a client copy is KEPT, ours added on the right
      proxy_pass http://127.0.0.1:18082;
    } } }
C
# The origin: listens on 18082, counts requests per address on /login, forwards to the app on 19001.
cat > origin.conf <<C
pid $lab/origin.pid; $common
http { $tmp
  log_format lab 'client=\$remote_addr via=\$realip_remote_addr status=\$status uri=\$uri';
  access_log $lab/origin-access.log lab;
  limit_req_zone \$binary_remote_addr zone=login:1m rate=1r/s;
  limit_req_status 429;
  server { listen 127.0.0.1:18082;
    $realip
    location / {
      proxy_set_header X-Decided-Client \$remote_addr;
      proxy_pass http://127.0.0.1:19001;
    }
    location /login {
      limit_req zone=login burst=3 nodelay;
      proxy_set_header X-Decided-Client \$remote_addr;
      proxy_pass http://127.0.0.1:19001;
    } }
  # The PROXY-protocol door (exercise 6): the address arrives in a line before the request, not in a header.
  server { listen 127.0.0.1:18083 proxy_protocol;
    set_real_ip_from 127.0.0.50; real_ip_header proxy_protocol;
    location / { proxy_set_header X-Decided-Client \$remote_addr; proxy_pass http://127.0.0.1:19001; } } }
C
LAB_EOF
cat > ctl.sh <<'LAB_EOF'
#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# ctl.sh up MODE [HEADER] | down | reload MODE [HEADER]: start or stop the lab. Run from the lab folder.
set -euo pipefail
cd "$(dirname "$0")"
stop() {
  for p in cdn origin app; do
    if [ -f $p.pid ]; then kill "$(cat $p.pid)" 2>/dev/null || true; rm -f $p.pid; fi
  done
}
case ${1:?up|down|reload} in
  down) stop ;;
  up|reload)
    stop; sleep 0.3
    ./make-conf.sh "${2:?mode}" "${3:-CF-Connecting-IP}"
    : > origin-access.log; : > cdn-access.log
    python3 -I app.py & echo $! > app.pid
    nginx -p "$PWD" -c "$PWD/origin.conf" -e "$PWD/error.log"
    nginx -p "$PWD" -c "$PWD/cdn.conf" -e "$PWD/error.log"
    sleep 0.5; echo "lab up: mode=$2 header=${3:-CF-Connecting-IP}" ;;
esac
LAB_EOF
cat > pp.py <<'LAB_EOF'
#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# pp.py SOURCE CLAIMED: connect to the PROXY-protocol door from the local address SOURCE and claim
# that the real client is CLAIMED. The first line is the PROXY protocol v1 header (HAProxy spec, section 2.1).
import socket, sys
src, claimed = sys.argv[1], sys.argv[2]
s = socket.socket()
s.bind((src, 0))
s.connect(("127.0.0.1", 18083))
s.sendall(("PROXY TCP4 %s 192.0.2.1 51000 443\r\n" % claimed).encode()
          + b"GET / HTTP/1.1\r\nHost: lab\r\nConnection: close\r\n\r\n")
data = b""
while chunk := s.recv(4096):
    data += chunk
print(data.decode().splitlines()[0], "|", data.decode().splitlines()[-1])
LAB_EOF
cat > xff.py <<'LAB_EOF'
#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# xff.py PEER XFF [TRUSTED...]: pick the client address the way real_ip_recursive does.
# Walk the X-Forwarded-For list from the RIGHT, skipping addresses we trust; the first one we do not trust is the client.
# If the connection's own peer is not trusted, the header is ignored completely.
import ipaddress, sys

def client(peer, xff, trusted):
    nets = [ipaddress.ip_network(t) for t in trusted]
    def ok(a):
        return any(ipaddress.ip_address(a) in n for n in nets)
    if not ok(peer):
        return peer, "peer not trusted: header ignored"
    chain = [p.strip() for p in xff.split(",") if p.strip()]
    for hop in reversed(chain):
        if not ok(hop):
            return hop, "first untrusted from the right"
    return peer, "every hop trusted"

if __name__ == "__main__":
    peer, xff, *trusted = sys.argv[1:]
    who, why = client(peer, xff, trusted)
    print("client=%s (%s)" % (who, why))
LAB_EOF
cat > asn.py <<'LAB_EOF'
#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# asn.py: a toy ASN lookup. Builds a small table at run time, then answers
# "which autonomous system announces this address?" by the longest matching prefix.
# Every prefix is from RFC 5737 / RFC 3849 and every ASN is a documentation number (RFC 5398). No network.
import csv, ipaddress, sys

ROWS = [  # prefix, origin ASN, organization (invented), upstream ASNs it is announced through (invented)
    ("198.51.100.0/24", 64500, "Example Hosting",  "64510 64511"),   # one origin, TWO providers (multihomed)
    ("203.0.113.0/25",  64501, "Example Campus",   "64510"),
    ("203.0.113.128/25", 64502, "Example Mobile",  "64511"),
    ("192.0.2.0/24",    64503, "Example CDN",      "64510 64511 64496"),
    ("2001:db8:100::/40", 64503, "Example CDN",    "64510 64511 64496"),
]
with open("asn-table.csv", "w", newline="") as f:
    csv.writer(f).writerows([("prefix", "asn", "org", "announced_via")] + ROWS)

table = [(ipaddress.ip_network(r["prefix"]), r) for r in csv.DictReader(open("asn-table.csv"))]

def lookup(addr):
    ip = ipaddress.ip_address(addr)
    best = None
    for net, row in table:
        if ip.version == net.version and ip in net and (best is None or net.prefixlen > best[0].prefixlen):
            best = (net, row)
    return best

for a in sys.argv[1:]:
    hit = lookup(a)
    if hit:
        net, r = hit
        print("%-18s -> %-17s AS%s %-16s announced via: %s" % (a, net, r["asn"], r["org"], r["announced_via"]))
    else:
        print("%-18s -> no match in this table" % a)
LAB_EOF
cat > cf-ranges.sh <<'LAB_EOF'
#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# cf-ranges.sh: fetch Cloudflare's published ranges (read-only), validate them, and write nginx lines.
# Fails closed: if either list is missing, malformed or implausibly short, it changes nothing and exits non-zero.
set -euo pipefail
cd "$(dirname "$0")"
v4=$(curl -fsS --max-time 20 https://www.cloudflare.com/ips-v4)
v6=$(curl -fsS --max-time 20 https://www.cloudflare.com/ips-v6)
printf '%s\n%s\n' "$v4" "$v6" | python3 -I -c '
import ipaddress, sys
nets = [ipaddress.ip_network(l.strip()) for l in sys.stdin if l.strip()]
v4 = [n for n in nets if n.version == 4]; v6 = [n for n in nets if n.version == 6]
if not (len(v4) >= 5 and len(v6) >= 3):
    sys.exit("implausible list: %d IPv4, %d IPv6 ranges" % (len(v4), len(v6)))
print("ok: %d IPv4 and %d IPv6 ranges" % (len(v4), len(v6)), file=sys.stderr)
'
{ echo "# generated $(date -u +%Y-%m-%dT%H:%MZ) from the published lists"
  printf '%s\n%s\n' "$v4" "$v6" | sed '/^$/d; s|^|set_real_ip_from |; s|$|;|'; } > cf-realip.new
if [ -f cf-realip.conf ] && ! diff -q <(grep -v '^#' cf-realip.conf) <(grep -v '^#' cf-realip.new) >/dev/null; then
  echo "ranges CHANGED since the last run:"; diff <(grep -v '^#' cf-realip.conf) <(grep -v '^#' cf-realip.new) || true
fi
mv cf-realip.new cf-realip.conf
echo "wrote cf-realip.conf ($(grep -vc '^#' cf-realip.conf) lines)"
LAB_EOF
chmod +x *.sh
# a helper: print only the status code of a request
hit() { curl -s -o /dev/null -w "%{http_code} " "$@"; }
O=http://127.0.0.1:18082; C=http://127.0.0.1:18081
```

```powershell
# est.: the lab is Linux software. On Windows run the Bash blocks inside WSL 2 (Ubuntu); from PowerShell:
wsl -e bash -c 'mkdir -p -m 700 ~/cdn-lab && ls ~/cdn-lab'
# The exercises below give a curl.exe line for each Bash line; run them against the lab running in WSL.
# (WSL 2 forwards localhost ports to Windows; --interface 127.0.0.11 may behave differently there. est.)
function hit { curl.exe -s -o NUL -w "%{http_code} " @args }
$O = "http://127.0.0.1:18082"; $C = "http://127.0.0.1:18081"
```

Each exercise has the same four steps: **Predict** (write down what you expect), **Do**, **Check**, **Undo**. The lab stays up between exercises; `./ctl.sh up MODE` restarts it in a mode and `./ctl.sh down` stops it.

### Exercise 1: only the proxy's address, and the self-block

**Predict.** The origin is not told to restore anything (mode `naive`). Client `.11` sends eight quick logins through the toy CDN, and then client `.12`, a different and innocent visitor, sends one. What address does the origin log for each? What does `.12` get?

**Do.**

```bash
./ctl.sh up naive
for c in 11 12 13; do curl -s --interface 127.0.0.$c $C/; done
for i in $(seq 8); do hit --interface 127.0.0.11 $C/login; done; echo
hit --interface 127.0.0.12 $C/login; echo
sort origin-access.log | uniq -c | sort -rn
```

```powershell
# est.
./ctl.sh up naive   # inside WSL
11,12,13 | ForEach-Object { curl.exe -s --interface "127.0.0.$_" "$C/" }
1..8 | ForEach-Object { hit --interface 127.0.0.11 "$C/login" }; ""
hit --interface 127.0.0.12 "$C/login"; ""
```

**Check.** From the author's run:

```text
app: socket-peer=127.0.0.1 nginx-decided-client=127.0.0.50 cf-header=127.0.0.11 xff=[127.0.0.11] naive-first-xff=127.0.0.11
app: socket-peer=127.0.0.1 nginx-decided-client=127.0.0.50 cf-header=127.0.0.12 xff=[127.0.0.12] naive-first-xff=127.0.0.12
app: socket-peer=127.0.0.1 nginx-decided-client=127.0.0.50 cf-header=127.0.0.13 xff=[127.0.0.13] naive-first-xff=127.0.0.13
200 200 200 200 429 429 429 429
429
      5 client=127.0.0.50 via=127.0.0.50 status=429 uri=/login
      4 client=127.0.0.50 via=127.0.0.50 status=200 uri=/login
      3 client=127.0.0.50 via=127.0.0.50 status=200 uri=/
```

Read it line by line. The three "visitors" are all `127.0.0.50` in the origin's log (`client=`). The header **was** sent (`cf-header=` shows each client's real address) but nobody read it. The limit (one request a second, burst of three) let the first four through and refused the rest, and then **refused the innocent client `.12` too**, because the limiter counted one address. That is the accidental self-block, in a log you can read.

**Undo.** Nothing; the next exercise restarts the lab.

### Exercise 2: believe the header from anyone (the spoofing demo)

**Predict.** The "fix" most people try first: trust the header from every source (mode `trustall`, which writes `set_real_ip_from 0.0.0.0/0`). Through the CDN everything looks right. What can the attacker at `127.0.0.66` now do by connecting straight to the origin and sending their own `CF-Connecting-IP`? Three things to try: be somebody else, dodge the login limit, and get an innocent client blocked.

**Do.**

```bash
./ctl.sh up trustall
curl -s --interface 127.0.0.11 $C/                                         # a legitimate visitor
curl -s --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.7" $O/      # straight to the origin, forged
curl -s --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.7" $C/      # forged, but through the CDN
for i in $(seq 8); do hit --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.$i" $O/login; done; echo    # evade
for i in $(seq 8); do hit --interface 127.0.0.66 -H "CF-Connecting-IP: 127.0.0.12" $O/login; done; echo       # frame client .12
hit --interface 127.0.0.12 $C/login; echo                                  # the innocent client's one login
```

```powershell
# est.
curl.exe -s --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.7" "$O/"
1..8 | ForEach-Object { hit --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.$_" "$O/login" }; ""
1..8 | ForEach-Object { hit --interface 127.0.0.66 -H "CF-Connecting-IP: 127.0.0.12" "$O/login" }; ""
hit --interface 127.0.0.12 "$C/login"; ""
```

**Check.**

```text
app: ... nginx-decided-client=127.0.0.11 cf-header=127.0.0.11 ...
app: ... nginx-decided-client=198.51.100.7 cf-header=198.51.100.7 xff=[-] ...
app: ... nginx-decided-client=127.0.0.66 cf-header=127.0.0.66 xff=[127.0.0.66] ...
200 200 200 200 200 200 200 200
200 200 200 200 429 429 429 429
429
```

Line 1: the legitimate path works, which is why this mistake survives testing. Line 2: the origin now believes `198.51.100.7`, an address of the attacker's choosing; they can be anyone. Line 3: the same forgery sent **through** the CDN is overwritten by the CDN with the true peer, which is why the header can be trusted **from the CDN** and not from anyone. Line 4: eight logins, each with a new made-up address, all succeed; **a per-address limit has been evaded**. Line 5: the attacker used the real client's address and got the limit applied to it, and line 6 shows the real `.12`, with a clean record, refused: the attacker **framed** them, and a ban tool reading this log would ban the innocent address. One missing rule, three attacks.

**Undo.** Nothing.

### Exercise 3: the fix, trust only the CDN

**Predict.** Now mode `correct`: `set_real_ip_from 127.0.0.50` only, `real_ip_recursive on`, header `CF-Connecting-IP`. Repeat the attacks. What does the origin log for the attacker's forged header? Then repeat Exercise 1's rate-limit test: does client `.12` still get blocked by `.11`'s burst?

**Do.**

```bash
./ctl.sh up correct
curl -s --interface 127.0.0.11 $C/
curl -s --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.7" $O/
for i in $(seq 8); do hit --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.$i" $O/login; done; echo
for i in $(seq 8); do hit --interface 127.0.0.66 -H "CF-Connecting-IP: 127.0.0.12" $O/login; done; echo
hit --interface 127.0.0.12 $C/login; echo
sleep 2
for i in $(seq 8); do hit --interface 127.0.0.11 $C/login; done; echo
hit --interface 127.0.0.12 $C/login; echo
grep status=429 origin-access.log | awk '{print $1,$2}' | sort | uniq -c
```

```powershell
# est.
./ctl.sh up correct   # inside WSL
curl.exe -s --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.7" "$O/"
1..8 | ForEach-Object { hit --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.$_" "$O/login" }; ""
Start-Sleep 2
1..8 | ForEach-Object { hit --interface 127.0.0.11 "$C/login" }; ""
hit --interface 127.0.0.12 "$C/login"; ""
```

**Check.** From the author's run:

```text
app: ... nginx-decided-client=127.0.0.11 cf-header=127.0.0.11 xff=[127.0.0.11] ...
app: ... nginx-decided-client=127.0.0.66 cf-header=198.51.100.7 xff=[-] ...
200 200 200 200 429 429 429 429
429 429 429 429 429 429 429 429
200
200 200 200 200 429 429 429 429
200
      4 client=127.0.0.11 via=127.0.0.50
     12 client=127.0.0.66 via=127.0.0.66
```

The forged header arrives (`cf-header=198.51.100.7`) and is **ignored**: the origin's decision is `127.0.0.66`, the attacker's real address, because that connection is not from a trusted proxy. The eight "new identity" attempts are counted against the attacker's own address, and after four they are refused. The framing attempt is refused as well, and the innocent `.12` gets `200`. In the visitor leg, `.11`'s burst is limited as `.11` and `.12` is untouched. The last tally is the ban list you would want: it names `127.0.0.11` (the heavy visitor) and `127.0.0.66` (the attacker), never `127.0.0.50`, the CDN.

**The same with `X-Forwarded-For`.** Restart with the header changed, and send a forged first entry through the CDN:

```bash
./ctl.sh up correct X-Forwarded-For
curl -s --interface 127.0.0.11 -H "X-Forwarded-For: 203.0.113.99" $C/
```

```text
app: ... nginx-decided-client=127.0.0.11 cf-header=127.0.0.11 xff=[203.0.113.99, 127.0.0.11] naive-first-xff=203.0.113.99
```

The toy CDN **appended** the true peer to the client's own list. The origin, walking from the right with `real_ip_recursive on`, decided `127.0.0.11`. An application that reads the **first** entry (`naive-first-xff`) would believe `203.0.113.99`, an address the client invented. That is the whole reason to read from the right.

**Undo.** Nothing.

### Exercise 4: close the other door, and the variable that moves

**Predict.** Mode `locked` adds one line to the origin: refuse any connection whose own peer is not `127.0.0.50`. What happens to the attacker's direct request? Why does the rule use `$realip_remote_addr` and not `$remote_addr`?

**Do.**

```bash
./ctl.sh up locked
curl -s --interface 127.0.0.11 $C/
curl -s -o /dev/null -w "direct: %{http_code}\n" --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.7" $O/
grep -n 'realip_remote_addr !=' origin.conf
```

```powershell
# est.
curl.exe -s -o NUL -w "direct: %{http_code}\n" --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.7" "$O/"
```

**Check.**

```text
app: ... nginx-decided-client=127.0.0.11 ...
direct: 403
    if ($realip_remote_addr != 127.0.0.50) { return 403; }
```

The attacker's direct connection is refused. This is the application-level echo of the cloud firewall in [the DNS lesson](DNS-Cloudflare-and-Hosting-Your-Own-Website.md#lock-the-origin-to-cloudflare): the firewall should refuse it first, and this line is the second lock. Why `$realip_remote_addr`? After the real-IP module runs, `$remote_addr` is the **visitor**. A check written against `$remote_addr` would test the visitor against the CDN's range and refuse every real user. The connection's own address is kept in `$realip_remote_addr`, which is why the module provides it. A firewall is not affected, because it sees the packet before any of this.

**Undo.** `./ctl.sh down` when you are finished with the lab.

### Exercise 5: read an X-Forwarded-For chain by hand

**Predict.** For each case, which address is the client? The trusted proxy range is `198.51.100.0/24`.

1. Connection from `198.51.100.50`, header `203.0.113.99, 192.0.2.7`.
2. Connection from `198.51.100.50`, header `203.0.113.99, 192.0.2.7, 198.51.100.60` (two of your proxies in a row).
3. Connection from `203.0.113.200` (not a proxy), header `10.0.0.1`.
4. Connection from `198.51.100.50`, header `203.0.113.99` only.

**Do.** `xff.py` applies the rule from this page: ignore the header unless the connection is from a trusted peer, then walk from the right and skip trusted addresses. It needs no Nginx.

```bash
python3 -I xff.py 198.51.100.50 "203.0.113.99, 192.0.2.7" 198.51.100.0/24
python3 -I xff.py 198.51.100.50 "203.0.113.99, 192.0.2.7, 198.51.100.60" 198.51.100.0/24
python3 -I xff.py 203.0.113.200 "10.0.0.1" 198.51.100.0/24
python3 -I xff.py 198.51.100.50 "203.0.113.99" 198.51.100.0/24
```

```powershell
# est.
python xff.py 198.51.100.50 "203.0.113.99, 192.0.2.7" 198.51.100.0/24
python xff.py 198.51.100.50 "203.0.113.99, 192.0.2.7, 198.51.100.60" 198.51.100.0/24
python xff.py 203.0.113.200 "10.0.0.1" 198.51.100.0/24
python xff.py 198.51.100.50 "203.0.113.99" 198.51.100.0/24
```

**Check.**

```text
client=192.0.2.7 (first untrusted from the right)
client=192.0.2.7 (first untrusted from the right)
client=203.0.113.200 (peer not trusted: header ignored)
client=203.0.113.99 (first untrusted from the right)
```

Case 1: the left entry, `203.0.113.99`, was written by somebody before your proxy; the right one, `192.0.2.7`, was written by your trusted proxy about its own peer, so it is the client you can name. Case 2 shows two trusted hops skipped. Case 3 is the spoof that fails: the peer is not a proxy, so the header is ignored. Case 4 is the limit: with only one entry, you believe the proxy that wrote it. The restored address is exactly as honest as the proxy.

**Undo.** Nothing.

### Exercise 6: the PROXY protocol

**Predict.** The origin also listens on `127.0.0.1:18083` with `proxy_protocol` on the `listen` line and `real_ip_header proxy_protocol`, trusting `127.0.0.50`. `pp.py` connects from a chosen local address and sends the one-line version 1 header claiming a client address. One connection comes from the trusted proxy address, one from the attacker. Which claim is believed?

**Do.**

```bash
./ctl.sh up correct
python3 -I pp.py 127.0.0.50 203.0.113.5     # from the trusted proxy
python3 -I pp.py 127.0.0.66 203.0.113.5     # from the attacker, same claim
tail -2 origin-access.log
```

```powershell
# est.
python pp.py 127.0.0.50 203.0.113.5
python pp.py 127.0.0.66 203.0.113.5
```

**Check.**

```text
HTTP/1.1 200 OK | app: ... nginx-decided-client=203.0.113.5 ...
HTTP/1.1 200 OK | app: ... nginx-decided-client=127.0.0.66 ...
client=203.0.113.5 via=127.0.0.50 status=200 uri=/
client=127.0.0.66 via=127.0.0.66 status=200 uri=/
```

The same line from the same client is believed from the proxy's address and ignored from the attacker's. Trust attaches to the **connection that carried it**, not to the content, which is the rule of the specification: accept the header only from known sources. Notice also what the PROXY protocol does not fix: the attacker was able to connect and be served. Closing the door is still the firewall's job.

**Undo.** Nothing.

### Exercise 7: refresh the CDN's ranges, and fail closed

**Predict.** `cf-ranges.sh` downloads the published IPv4 and IPv6 lists (read-only requests to two public pages), checks that every line is a valid network and that the counts are plausible, and writes `set_real_ip_from` lines. If it ran twice with no change, what does it say the second time? If the download failed halfway, what should it do to the file you already have?

**Do.**

```bash
./cf-ranges.sh
head -4 cf-realip.conf
./cf-ranges.sh
```

```powershell
# est.: run it in WSL, or the same steps with Invoke-RestMethod
$v4 = (Invoke-RestMethod https://www.cloudflare.com/ips-v4) -split "`n" | Where-Object { $_ }
$v6 = (Invoke-RestMethod https://www.cloudflare.com/ips-v6) -split "`n" | Where-Object { $_ }
"{0} IPv4 and {1} IPv6 ranges" -f $v4.Count, $v6.Count
```

**Check.** From the author's run on 2026-10-22:

```text
ok: 15 IPv4 and 7 IPv6 ranges
wrote cf-realip.conf (22 lines)
# generated 2026-10-22T21:37Z from the published lists
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 103.21.244.0/22;
set_real_ip_from 103.22.200.0/22;
ok: 15 IPv4 and 7 IPv6 ranges
wrote cf-realip.conf (22 lines)
```

The counts are what the page held that day; yours may differ, which is the point. The second run reported no change, so it printed no diff. A change would print `ranges CHANGED since the last run:` followed by a diff. The script uses `set -e` and a validation step, so a failed download, an empty list or a malformed line stops it **before** it overwrites `cf-realip.conf`; the old file stays. In production this file would be `include`d by the Nginx config and followed by `nginx -t` and a reload; the same list also feeds the firewall.

**Undo.** Nothing.

### Exercise 8: a toy ASN lookup

**Predict.** `asn.py` builds a small CSV at run time with RFC 5737 prefixes and documentation ASNs (RFC 5398 reserves 64496 to 64511 for examples), then finds the longest matching prefix for each address. One organization is announced through two providers. Which addresses will match what? What will the table not be able to tell you?

**Do.**

```bash
python3 -I asn.py 198.51.100.77 203.0.113.9 203.0.113.200 192.0.2.50 2001:db8:100::5 198.18.1.1
cat asn-table.csv
```

```powershell
# est.
python asn.py 198.51.100.77 203.0.113.9 203.0.113.200 192.0.2.50 2001:db8:100::5 198.18.1.1
Get-Content asn-table.csv
```

**Check.**

```text
198.51.100.77      -> 198.51.100.0/24   AS64500 Example Hosting  announced via: 64510 64511
203.0.113.9        -> 203.0.113.0/25    AS64501 Example Campus   announced via: 64510
203.0.113.200      -> 203.0.113.128/25  AS64502 Example Mobile   announced via: 64511
192.0.2.50         -> 192.0.2.0/24      AS64503 Example CDN      announced via: 64510 64511 64496
2001:db8:100::5    -> 2001:db8:100::/40 AS64503 Example CDN      announced via: 64510 64511 64496
198.18.1.1         -> no match in this table
```

Three things to read off it. **Longest prefix wins:** `203.0.113.9` and `203.0.113.200` sit in the same `/24` but two different `/25` announcements, so two different organizations; the more specific route is what gets traffic. **One owner, several roads:** Example Hosting (AS64500) is announced through two upstream providers, so the same addresses are reached over two paths, which is the multi-homing from RFC 1930. **One organization, both address families:** Example CDN announces IPv4 and IPv6 under one number. And what the table cannot say: who was at `198.51.100.77`, one customer of Example Hosting or a hundred, in which country, or whether they are the same person who was there yesterday. The lookup names the operator, not the user. A real database is a large table of the same shape, fed by routing data; this lab calls no outside service.

**Undo.** Nothing. Stop everything with `./ctl.sh down`, then `cd ~ && rm -r ~/cdn-lab` removes the folder.

## Optional: the same fix on your own Cloudflare account

The lab above is everything this lesson needs. If you follow [the DNS lesson's walkthrough](DNS-Cloudflare-and-Hosting-Your-Own-Website.md#hosting-your-own-website-the-walkthrough) on your own accounts, you can then repeat Exercises 1 and 3 for real: look at what your web server logs before and after you add the real-IP lines and the generated range file. **Cost and teardown first:** this adds no new resource beyond that lesson's droplet, firewall and Cloudflare zone; what they cost is on [that page](DNS-Cloudflare-and-Hosting-Your-Own-Website.md#cost-honestly) and in `docs/cost.md`, and tearing the walkthrough down removes everything this step touched. This page gives no figure of its own. The Cloudflare side (a Managed Transform, the header names) was read from the documentation and not clicked through (**est.**), and the real-IP include file would be applied on your server, not in this repository. Run it expecting to fix something, test the site through the CDN after every firewall change, and keep the SSH door you used to log in open until you have tested the new lists.

## Build, break, detect, evade, defend

The loop from the other lessons, on the lab.

**Build.** A toy CDN, an origin that restores the client address from a header only when the connection comes from the CDN, a login limit that counts the restored address, and a second lock that refuses non-CDN connections (Exercises 3 and 4).

**Break.** Spoof it: send a forged `CF-Connecting-IP` straight to the origin and be somebody else, dodge the limit and frame an innocent client (Exercise 2). Send a forged `X-Forwarded-For` through the CDN and see which entry an application would believe (Exercise 3).

**Detect.** Two signals, both from the log format the lab uses (`client=` and `via=`):

- A connection whose `via=` is not the CDN's address on a site that should only be reached through the CDN. In the lab: `grep -v 'via=127.0.0.50' origin-access.log`.
- A ban or rate-limit tally that names the CDN. In the lab: `grep status=429 origin-access.log | awk '{print $1,$2}' | sort | uniq -c`; the naive lab produced `client=127.0.0.50`, the correct one never does.

```bash
./ctl.sh up trustall; curl -s -o /dev/null --interface 127.0.0.66 -H "CF-Connecting-IP: 198.51.100.7" $O/
grep -v 'via=127.0.0.50' origin-access.log
```

```text
client=198.51.100.7 via=127.0.0.66 status=200 uri=/
```

Even in the broken mode the log shows it: a request that claims to be `198.51.100.7` but came in from `127.0.0.66`, which is not the CDN. A rule that alerts on "via is not the CDN" would have caught the attack the moment it started. In production the same check is: compare the connection peer with the published ranges, and alert on any origin hit from outside them (your cloud firewall's drop log is the other copy of the evidence).

**Evade.** An attacker who finds the origin's address (the DNS lesson lists how: old DNS records, a mail server, certificate scans) goes around the CDN and talks to the origin directly, where the CDN's WAF and rate rules do not apply. In `trustall` that was the whole attack; in `correct` it still works as a plain request, which is why the origin needs the firewall and the second lock. Evasion also works through rotation: a network of residential proxies presents many addresses ([above](#one-person-many-addresses)) and defeats a per-address limit. This page shows no working attack against anyone else's system and none is needed to understand the defense.

**Defend.** Believe a header only from the CDN's current published ranges; overwrite or read-from-the-right; lock the origin to the CDN in the cloud firewall and again in the web server; log both addresses; ban visitors at the CDN or in the web server and never at an origin firewall that sees only the CDN; refresh and diff the range list and fail closed; use accounts, tokens and behavior next to the address.

### Flip the board

You built and attacked the design. Now take the other two jobs.

**The reviewer.** A colleague sends this plan for a site behind a CDN. Find at least six problems without running anything.

```text
Plan: "Get real visitor IPs, version 1"
- Nginx: set_real_ip_from 0.0.0.0/0; real_ip_header X-Forwarded-For; real_ip_recursive off.
- The origin keeps ports 80 and 443 open to the world "so the CDN can always reach it".
- fail2ban runs on the origin, reading the access log, banning with iptables. Its ignoreip is empty.
- Cloudflare's ranges are pasted into the firewall by hand, once.
- The app reads the first value of X-Forwarded-For and puts it in the audit log.
- Failed logins are limited to 5 per IP per hour; the lockout is the main protection against password guessing.
- Only IPv4 ranges were added to the firewall; the site also has an AAAA record.
```

<details>
<summary>What to find</summary>

1. **`0.0.0.0/0` as the trusted set:** any client can forge any identity (Exercise 2). Trust only the CDN's ranges.
2. **`real_ip_recursive off` with XFF:** takes the last entry, which may be a proxy rather than the client, and gives no way to skip more than one trusted hop.
3. **Origin open to the world:** an attacker bypasses the CDN and forges at will. The firewall should allow 80 and 443 only from the CDN, plus a second lock in the web server.
4. **fail2ban with an empty `ignoreip` on the origin:** with the real address restored, it bans visitors at the origin's firewall, which does nothing (their packets arrive from the CDN), and if any line still shows the CDN's address it bans the CDN. Ban at the CDN or in the web server, and set `ignoreip` to the CDN as a safety net.
5. **Ranges pasted once:** they will go stale. Fetch, diff and fail closed.
6. **App trusts the first XFF value:** that is the entry a client controls. The audit log would record invented addresses and could be used to frame somebody.
7. **An address-only lockout as the main protection:** residential proxies and CGNAT make an address limit both evadable and unfair. Add per-account limits, MFA and monitoring.
8. **IPv4 only in the firewall, but an AAAA record:** IPv6 visitors either bypass or are refused (est.). Cover both families, or remove the AAAA.
9. **No test of the unhappy path:** nothing checks that a forged header is ignored or that the CDN is not banned. Add the Exercise 2 and 3 checks to the pipeline.

</details>

**The responder.** At 02:00 the site is down for everyone, and the origin's log shows one address with an enormous request count: the CDN's. Write the questions in order before you touch anything: is the origin itself healthy (check it directly from a trusted host); did a ban tool just act (fail2ban or firewall logs); is the CDN's address in a deny list (remove it first, since that restores service); is the real-IP module configured and the header present (a Transform Rule or Managed Transform may have removed it); did the CDN publish a range change you have not applied. Restore service, then fix the cause, then write the timeline.

## Threat model

**Assets.** The site's availability; the integrity of logs and audit trails; the fairness of limits and bans; the secrecy of the origin's address; the identities of visitors (an address is often personal data).

**Actors.** An ordinary visitor behind a shared address; an attacker who finds the origin; an attacker who does not and can only send requests through the CDN; an operator who makes a configuration mistake; the CDN itself (trusted for the header, and a place where a mistake or a change can affect everyone).

**Trust boundaries.** The visitor to the CDN (nothing is trusted). The CDN to the origin (the header is trusted **only** here, and only if the connection is from the CDN's ranges). The origin's firewall (the boundary that keeps the previous one meaningful). The web server to the application (a second place to get "trusted proxies" wrong).

| Abuse case | Impact | Prerequisite | Mitigation | Verification | Residual risk |
|---|---|---|---|---|---|
| Forge `CF-Connecting-IP` or XFF at the origin to impersonate, evade or frame | Evaded limits, false bans, poisoned logs | Origin reachable directly, or trust set too wide | Trust list limited to the CDN's ranges; origin locked to the CDN; read XFF from the right | Exercises 2 to 4; a pipeline test that sends a forged header | Whoever the CDN saw can still be a shared or relayed address |
| Ban or limit applied to the CDN's address | Site down for everyone | No real-IP restore, or a tool using the connection address | Restore the address; ignore list for the CDN; ban at the CDN | Exercise 1 and the 429 tally | A new CDN range missing from the ignore list |
| Stale range list | Intermittent refusal or untrusted headers | Lists copied once | Scheduled fetch, diff, fail closed, alert | Exercise 7; an alert test with a doctored list | The window between a CDN change and your next run |
| Origin address discovered; CDN bypassed | WAF and CDN rules skipped | Old DNS records, mail records, certificate scans | Cloud firewall allow-list; second lock in the web server; Authenticated Origin Pulls | Exercise 4; a test from outside that must time out | Other customers of the same CDN share its ranges, hence AOP |
| Per-address limit evaded by rotation | Credential guessing at scale | Residential proxy network or many addresses | Per-account limits, MFA, behavior and bot scoring at the CDN | Account-lockout test across addresses (own lab) | Slow, distributed guessing is hard to see |
| Innocent users blocked behind shared addresses | Lost customers | CGNAT, offices, VPNs | Soft limits (challenge, slow down) before hard blocks; account-based signals | Review of block logs by ASN class | Some shared-address users will be inconvenienced |
| Wrong "trusted proxies" in the application | The app logs or authorizes on a forged address | Framework set to trust everything | Hop count or subnet list; read the default | Test with a forged header; see Exercise 3 | Framework upgrades can change defaults |
| Address logging beyond need | Privacy exposure | Long retention | Decide retention; hash or truncate where the use allows | A retention policy that is checked | Law and contract vary; this page gives no legal advice |

**Residual risk, in one line:** you can make the address you log as honest as the CDN that supplied it, and no more honest than that; decisions about people should not rest on it alone.

## Checkpoint

You are done when you can say, without looking:

- Why a server behind a CDN sees the CDN's address, and three things that break because of it.
- What a header can carry and what it cannot prove, and what the PROXY protocol adds.
- The trust rule, and why a forged header is believed in Exercise 2 and ignored in Exercise 3.
- Why `X-Forwarded-For` is read from the right, and what `real_ip_recursive` does.
- Why a firewall at the origin cannot ban a visitor behind a CDN, and where the ban has to happen.
- What `$realip_remote_addr` is for.
- What to do when the CDN's ranges change, and why the refresh job must fail closed.
- Five reasons an IP address is a weak identifier, and what an ASN lookup does and does not tell you.
- The OSI layer of a switch, a router, a packet filter, a layer 4 balancer, a WAF and a CDN, and one place the model breaks down.
- Where to go next for on-premises networking.

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| Every log line shows the CDN's address | The real-IP module is off, or `set_real_ip_from` lacks the range | `nginx -V` for the module; the include file; the range list. |
| `nginx: unknown directive "set_real_ip_from"` | The module is not built in | `nginx -V 2>&1 \| grep realip`; install a build that has it. |
| Real-IP is on but the address is still the CDN's | The peer is not in the trusted list, or the header is missing or has another name | `$realip_remote_addr` in the log; the actual header in a request capture. |
| Everybody is allowed or blocked by an `allow` / `deny` list after enabling real-IP | The rule now tests the visitor | Use `$realip_remote_addr` for connection checks. |
| Address in the log is a private or `240.x` one | Another proxy in the chain, or Pseudo IPv4 | Trust the inner proxy too; read the CDN's Pseudo IPv4 setting. |
| `Address already in use` starting the lab | Another program has one of the lab's ports | Change the port number in every file, or stop the other program. |
| `curl: bind failed` with `--interface 127.0.0.11` | macOS and some systems only have `127.0.0.1` on loopback | Add the alias (needs admin rights) or use a Linux machine. |
| Bans at the origin have no effect | The firewall sees the CDN, not the visitor | Ban at the CDN or in the web server. |

## Claims register

All read-only requests; retrieved 2026-10-22 unless stated.

| Claim | Source | Status |
|---|---|---|
| Behind Cloudflare the origin logs a Cloudflare address by default; the original visitor address is in `CF-Connecting-IP`; web server instructions exist for many servers; Apache users are told to use `mod_remoteip` because `mod_cloudflare` is no longer supported; the Nginx example uses `set_real_ip_from` and either `real_ip_header CF-Connecting-IP` or `X-Forwarded-For`; the list "needs to be updated regularly"; log `$http_cf_connecting_ip` and `$http_x_forwarded_for`; check Transform Rules and Managed Transforms if the header is missing | [Cloudflare: restoring original visitor IPs](https://developers.cloudflare.com/support/troubleshooting/restoring-visitor-ips/restoring-original-visitor-ips/) (page dated Apr 23, 2026) | Read |
| `CF-Connecting-IP` is sent only on traffic from Cloudflare's edge to the origin; `True-Client-IP` is Enterprise only and identical to `CF-Connecting-IP` apart from its name; `X-Forwarded-For` equals `CF-Connecting-IP` if the request had none and is appended to if it had one; the Remove visitor IP headers Managed Transform; Pseudo IPv4 (`CF-Pseudo-IPv4`, overwrite mode, `CF-Connecting-IPv6`) | [Cloudflare HTTP headers](https://developers.cloudflare.com/fundamentals/reference/http-headers/) (page dated Oct 9, 2026) | Read |
| Cloudflare's ranges are shared by all proxied hostnames; they "do not change frequently" and are added to the published list "before being put into production"; an API can keep a configuration current; recommendation to block other addresses at the origin | [Cloudflare IP addresses](https://developers.cloudflare.com/fundamentals/concepts/cloudflare-ip-addresses/) (page dated Apr 21, 2026) | Read |
| The current published ranges (15 IPv4 and 7 IPv6 on the day) | [ips-v4](https://www.cloudflare.com/ips-v4) and [ips-v6](https://www.cloudflare.com/ips-v6) | Fetched in Exercise 7; no range is copied into this page |
| Nginx real-IP module: not built by default; `set_real_ip_from` defines trusted addresses "known to send correct replacement addresses"; `real_ip_header` accepts a header, `X-Real-IP` (default), `X-Forwarded-For` or `proxy_protocol`; `real_ip_recursive` picks "the last non-trusted address"; `$realip_remote_addr` keeps the original client address | [ngx_http_realip_module](https://nginx.org/en/docs/http/ngx_http_realip_module.html) | Read; behavior run in the lab (nginx 1.26.3) |
| `proxy_bind` makes outgoing connections originate from a given local address | [ngx_http_proxy_module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) | Read; used in the lab |
| `limit_req_zone` / `limit_req` limit the rate per key, in particular per client address | [ngx_http_limit_req_module](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html) | Read; run (429 after the burst) |
| Apache `mod_remoteip`: right-to-left processing; "Unless these other directives are used, mod_remoteip will trust all hosts presenting a RemoteIPHeader IP value"; `RemoteIPTrustedProxy`; the replaced address feeds `Require ip` and `%a`; it also implements the server side of the PROXY protocol | [mod_remoteip](https://httpd.apache.org/docs/2.4/mod/mod_remoteip.html) | Read; not run |
| PROXY protocol: carries client connection information across proxies; receiver must be configured to expect it and must not guess; "only trusted proxies" should be allowed; version 1 is one text line; accept only from known sources | [HAProxy PROXY protocol specification](https://www.haproxy.org/download/1.8/doc/proxy-protocol.txt) | Read; version 1 run in Exercise 6 |
| `Forwarded` header syntax and examples; security: "cannot be relied upon to be correct", the chain before the proxy "cannot be trusted" | [RFC 7239](https://www.rfc-editor.org/rfc/rfc7239) | Read |
| AWS Application Load Balancer: `X-Forwarded-For` modes `append` (default), `preserve`, `remove`; server logs otherwise hold the balancer's address; "should be used with caution" | [AWS: HTTP headers and Application Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html) | Read |
| CloudFront can add `CloudFront-Viewer-Address` and `CloudFront-Viewer-ASN` via an origin request policy | [AWS: CloudFront headers](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/adding-cloudfront-headers.html) | Read |
| Express `trust proxy`: must match the proxy setup; `true` means the left-most `X-Forwarded-For` entry; `req.ip` from the first untrusted address | [Express: behind proxies](https://expressjs.com/en/guide/behind-proxies.html) | Read |
| Werkzeug `ProxyFix`: `x_for` is the number of values to trust; trusting client values is "a security issue" | [Werkzeug: ProxyFix](https://werkzeug.palletsprojects.com/en/stable/middleware/proxy_fix/) | Read |
| fail2ban `ignoreip` and `ignoreself` settings; a Cloudflare ban action exists | [jail.conf](https://raw.githubusercontent.com/fail2ban/fail2ban/master/config/jail.conf) and [cloudflare.conf](https://raw.githubusercontent.com/fail2ban/fail2ban/master/config/action.d/cloudflare.conf) | Read; not run |
| Definition of an autonomous system; multi-homed sites; one origin AS per prefix in general | [RFC 1930](https://www.rfc-editor.org/rfc/rfc1930) | Read |
| BGP's function: exchange of reachability information including the AS list; CIDR prefixes | [RFC 4271](https://www.rfc-editor.org/rfc/rfc4271) | Read (introduction) |
| Anycast: a service address available at nodes in two or more locations; the routing system picks the node | [RFC 4786](https://www.rfc-editor.org/rfc/rfc4786) | Read |
| `100.64.0.0/10` is "Shared Address Space" | [RFC 6598](https://www.rfc-editor.org/rfc/rfc6598) | Read (that CGNAT deployments use it is the RFC's stated purpose; how any given carrier behaves was not checked) |
| Documentation ASNs 64496 to 64511 | [RFC 5398](https://www.rfc-editor.org/rfc/rfc5398) | Read |
| Documentation address blocks `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`, and `2001:db8::/32` for IPv6 | [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737) and [RFC 3849](https://www.rfc-editor.org/rfc/rfc3849) | RFC 3849 fetched; RFC 5737 read for the other lessons; used as placeholders |
| Temporary IPv6 addresses exist to make a device harder to follow | [RFC 4941](https://www.rfc-editor.org/rfc/rfc4941) | Read (abstract) |
| The communication layers of a host (link, IP, transport) and the application protocols in a companion RFC | [RFC 1122](https://www.rfc-editor.org/rfc/rfc1122) | Read (summary) |
| IP geolocation is not guaranteed accurate; varies by country, IP type and ISP; "never precise enough to identify or locate a specific household, individual, or street address"; a VPN user may be located at the VPN server | [MaxMind: geolocation accuracy](https://support.maxmind.com/hc/en-us/articles/4407630607131-Geolocation-Accuracy) | Read |
| pfSense documentation: the home page, firewall fundamentals and NAT pages exist | [Netgate pfSense docs](https://docs.netgate.com/pfsense/en/latest/) | Pages fetched (HTTP 200); contents of the NAT section not read in depth |
| The two SIEM repositories are public; what each describes itself as | [pfsense-siem-stack](https://github.com/ChiefGyk3D/pfsense-siem-stack) and [siem-docker-stack](https://github.com/ChiefGyk3D/siem-docker-stack) READMEs | Read via the GitHub API; code not run |
| The seven-layer OSI model as an ISO standard (ISO/IEC 7498-1); where TLS and QUIC sit; "the Internet runs four layers" as a teaching simplification | General knowledge | Not verified: **est.** |
| Behavior of Tor exits, VPN pools, residential proxy networks, mobile-carrier address changes, ISP prefix rotation, cloud egress sharing; Laravel, Rails and Django settings; health checks arriving without the header; IPv6 mismatch behavior; that a firewall at the origin cannot see the visitor behind a CDN | General knowledge (the last follows from the two-connection design) | Not verified: **est.** |

Not verified, plainly: every PowerShell command; macOS and Windows; Apache `mod_remoteip` and fail2ban in practice; any real CDN, cloud load balancer or firewall; the Cloudflare dashboard steps; ISO/IEC 7498-1 itself; the two SIEM repositories' code; and anything about how a particular ISP, mobile carrier, VPN or proxy network assigns addresses. The lab proves the logic of the trust rule in Nginx 1.26.3 on loopback, not the behavior of a real CDN's network.

Next: [Reading order](Reading-Order.md), to choose the next page. Back to [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) for the origin lock this page builds on.
