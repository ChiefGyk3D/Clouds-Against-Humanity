# DNS, Cloudflare and hosting your own website

Side page to the start-from-zero pages, and the third lesson of a four-lesson web-hosting track. Read it after [How a web request works](How-a-Web-Request-Works.md) (which explains DNS in one section) and [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md), and beside [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md). Next: [Droplet hardening](Droplet-Hardening.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **The track.** W1 is [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md), W2 is [WordPress and PHP security, WAF and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md), W3 is this page, and W4 is [WordPress at scale: CDN, WAF and CI](WordPress-at-Scale-CDN-WAF-and-CI.md). The four are written at the same time. **Until each of those pages is merged, the links to it on this page lead nowhere.** That is why the closing pointer at the top and bottom of this page names a page that already exists, and why nothing on this page depends on reading the others first: where W1's web server is needed, a three-line static site does the job.

> **Status: the free local DNS lab and the OpenTofu example were run once on Linux; the Cloudflare dashboard steps and the whole own-account path were not run.** On **2026-10-22** the author ran the local lab with `dnsmasq` 2.91, `dig` 9.20.29 and OpenTofu 1.12.6, and pasted trimmed output from that run. The read-only queries against public DNS were run the same day. The vendor facts (Cloudflare, DigitalOcean, AWS, the RFCs, PHP) were read from the vendor's own pages on **2026-10-22** with read-only `curl`; each is in the [claims register](#claims-register) with its URL. **Not run:** every PowerShell command (no Windows machine; written from Microsoft's documentation and marked **est.**), every Cloudflare dashboard click (written from Cloudflare's documentation, so button names may have moved), and the droplet, firewall and certificate steps (written from `doctl` and nginx documentation, never applied; run them expecting to fix something). Output varies with your versions, your resolver and the date.

> **Prerequisites.** [How a web request works](How-a-Web-Request-Works.md) (the four steps of a request, and what a record and a TTL are) and a terminal ([Git from zero](Git-From-Zero.md) has a first look). [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) helps for the firewall part. The free path needs no account and no money. About three hours for the reading and the free lab (est.); the optional own-account path adds an afternoon (est.).

## What you will be able to do

- Say who owns what: the registry, the registrar, the DNS host and you, and what "pointing a domain at a server" really changes.
- Read and write the common record types (A, AAAA, CNAME, MX, TXT, NS, SOA, CAA, SRV, PTR) and say what each is for.
- Explain TTL and caching well enough to say why a change "takes time", and what to lower before a move.
- Explain delegation: how the `com` servers know which servers answer for your name, and what changing nameservers does.
- Say what Cloudflare's proxy ("orange cloud") hides, what it exposes, and what it cannot protect.
- Choose a TLS mode, explain why **Flexible** is a trap, and say what an origin certificate is for.
- Lock a web server's firewall to Cloudflare's published address ranges, and say why leaving the server reachable directly defeats the point.
- Run your own DNS server and resolver on your computer, break a record, watch a cache serve the old answer, and build a reverse lookup.
- Walk through hosting a website on your own domain, from buying the name to tearing it all down, as a whole or one piece at a time.
- Read DNS as a trust boundary: hijack, dangling records, subdomain takeover, registrar account takeover, cache poisoning, and what stops each.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| DNS lookup, records, TTL | [How a web request works](How-a-Web-Request-Works.md#step-1-dns-from-a-name-to-an-address) has one section and one exercise: A, AAAA, CNAME, NS, MX, and a TTL counting down. | Who owns a name, delegation, the rest of the record types, running a zone, email records, DNSSEC, and operating DNS for a real site. This page does not repeat that section; it starts where it stops. |
| Firewalls on a droplet | [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) and [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md): tags, zero inbound, by-hand rules. | A web server is the first thing in this project that **must** take inbound traffic from the internet. This page shows how to allow only a proxy's ranges. |
| TLS and certificates | [How a web request works](How-a-Web-Request-Works.md#certificates-and-trust-chains-in-plain-language). | Two TLS connections instead of one (visitor to proxy, proxy to server), and what each mode checks. |
| A public website | Not covered. The project's droplets have no public service on purpose. | Hosting one, safely, on your own account. |

## Cost, honestly

You choose what you can afford. This lesson sets no ceiling. It gives honest numbers and realistic expectations; some readers can afford more than others, and the lesson does not rate anyone by what they spend.

| Item | What it costs | Source |
|---|---|---|
| Reading this page and the free local DNS lab | $0. The lab runs on your own computer, teaches the same concepts as a real domain, and is complete without any account. | This page |
| A registered domain name | A **yearly fee set by the registrar**. I give no price: I did not read one. It renews every year (Cloudflare's registrar page says domains auto-renew by default, retrieved 2026-10-22). Whether a registration can be refunded is the registrar's own term; I did **not** read any registrar's terms, so assume it cannot be refunded until you have read yours. | Cloudflare Registrar page; the rest is your registrar's terms |
| Cloudflare account on the Free plan | $0 a month (the plans page lists the Free plan at "$0 /month", retrieved 2026-10-22). | cloudflare.com/plans |
| A small droplet (`s-1vcpu-1gb`) as the web server | $6 a month at list price ([`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json); see [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md)). Billed per second while it exists, **even powered off**; destroying it ends billing (DigitalOcean droplet pricing page, retrieved 2026-10-22). | Repository files and DigitalOcean docs |
| **A forgotten droplet** | About **$0.20 a day and $6 a month** (est.: $6 divided by 30). A forgotten domain costs nothing until the renewal date, then the yearly fee, and the cheapest way to stop it is to turn off auto-renew and let it lapse (see the teardown section for what a lapsed name risks). | Arithmetic from the figure above |
| DNS hosting elsewhere | DigitalOcean: "DNS management is free" (DigitalOcean DNS pricing page, retrieved 2026-10-22). AWS Route 53: $0.50 per hosted zone per month for the first 25 zones (AWS pricing page, retrieved 2026-10-22; queries and health checks are priced separately and I did not total them). | Vendor pricing pages |

A realistic first run of the whole walkthrough: the domain fee, plus about $0.20 a day for the droplet while you work, plus $0 for Cloudflare Free. Do the whole thing in a weekend and destroy the droplet on Sunday night, and the droplet costs a dollar or less (est.). The domain is the part you keep.

## Names, who owns them, and who answers

A **domain name** such as `example.com` is a label you rent. Four different parties are involved, and beginners mix them up because one company often plays several roles.

| Party | What it does | Example |
|---|---|---|
| **Registry** | Runs a whole top-level domain (TLD) and keeps its master list of names: who holds `example.com` and which nameservers answer for it. | The organization that runs `com` |
| **Registrar** | A company accredited to sell you a name in that registry. You pay the registrar a yearly fee; it tells the registry your details and your nameservers. | Whichever company you buy the name from |
| **DNS host** (authoritative DNS provider) | Runs the **nameservers** that hold your **zone** (your records) and give the official answer. Often the registrar by default, but it can be anyone. | Your registrar's DNS, Cloudflare, DigitalOcean, AWS Route 53 |
| **You, the registrant** | Hold the right to use the name, and decide who the DNS host is. | You |

A **zone** is the set of records one DNS host answers for, starting at a name (`example.com`) and covering everything below it that you have not handed to someone else. A **nameserver** (NS) is a server that answers for a zone. **Authoritative** means "the source of truth for this zone", as opposed to a **resolver**, which only looks answers up and remembers them ([RFC 1034](https://www.rfc-editor.org/rfc/rfc1034) is the original description; [RFC 8499](https://www.rfc-editor.org/rfc/rfc8499) is the terminology reference).

### Delegation: how the world finds your nameservers

Nobody keeps a list of every domain. Instead the hierarchy hands responsibility down. The root servers know who runs `com`; the `com` servers know which nameservers you chose for `example.com`; your nameservers know the records. Each step is a **referral** ("I do not know, ask them") and the pointer is called a **delegation**. When you "change nameservers" at your registrar, you edit the delegation record that the registry publishes. That is the only thing the registrar's setting does; your records live elsewhere, at the DNS host.

Two consequences matter for everything below:

1. **Records you add at the wrong DNS host are invisible.** If your registrar's nameservers are still the delegated ones, the records you typed into Cloudflare answer nobody.
2. **Whoever controls the delegation controls the name.** The registrar login is the most powerful login in this lesson (see [DNS as a trust boundary](#dns-as-a-trust-boundary)).

Exercise 1 below walks a real delegation by hand.

## The records you will meet

Each record has a **name**, a **type**, a **value** (the data) and a **TTL**. Read the examples as `name  TTL  IN  type  value`.

| Type | Maps | Used for | Example (documentation names and addresses) |
|---|---|---|---|
| `A` | name to IPv4 address | Where the website lives | `www.example.com. 300 IN A 192.0.2.10` |
| `AAAA` | name to IPv6 address | The same, for IPv6 | `www.example.com. 300 IN AAAA 2001:db8::10` |
| `CNAME` | name to **another name** (an alias) | "This name is just another name for that one" | `blog.example.com. 300 IN CNAME www.example.com.` |
| `MX` | domain to mail servers, with a preference number | Where email for the domain is delivered; lower number is tried first | `example.com. 300 IN MX 10 mail.example.com.` |
| `TXT` | name to free text | Proof of ownership and email policy (SPF, DKIM, DMARC) | `example.com. 300 IN TXT "v=spf1 -all"` |
| `NS` | zone to its nameservers | The delegation: who answers for this zone | `example.com. 86400 IN NS ns1.example.com.` |
| `SOA` | zone to its administrative data | Start of authority: primary server, contact, serial number and timers; one per zone | `example.com. IN SOA ns1.example.com. hostmaster.example.com. 2026102201 1200 120 604800 30` |
| `CAA` | domain to the certificate authorities allowed to issue for it | Limits who can get a certificate for the name | `example.com. IN CAA 0 issue "ca.example.net"` |
| `SRV` | service name to host and port | Finding a service that is not on a standard port (some chat and voice systems) | `_sip._tcp.example.com. IN SRV 0 5 5060 sip.example.com.` |
| `PTR` | address to name (**reverse** lookup) | "Who is this address?"; used by mail servers and logs | `10.2.0.192.in-addr.arpa. IN PTR www.example.com.` |

Details worth knowing, each with its primary source:

- **A name with a CNAME cannot hold other records.** A CNAME means "everything about this name is the same as that name", so it cannot sit beside an MX, a TXT or an NS at the same name ([RFC 1912, section 2.4](https://www.rfc-editor.org/rfc/rfc1912) says a CNAME "is not allowed to coexist with any other data"; [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034) describes how CNAMEs are followed). That is why a plain CNAME is not allowed at the **apex**, the bare `example.com`, which must carry the SOA and NS records.
- **CNAME flattening** is a DNS host's workaround: the host looks up the target itself and answers with the final address, so you can alias the apex. Cloudflare documents it as a feature that "allows you to use a CNAME record at your zone apex" ([Cloudflare CNAME flattening](https://developers.cloudflare.com/dns/additional-options/cname-flattening/)); it is a vendor feature, not a standard record type, and other providers call theirs `ALIAS` or `ANAME` (est.).
- **The SOA serial number and timers** tell secondary servers when to refresh. The last SOA field (the "minimum") became the time negative answers may be cached ([RFC 2308](https://www.rfc-editor.org/rfc/rfc2308)).
- **CAA** records are checked by certificate authorities before they issue; the standard is [RFC 8659](https://www.rfc-editor.org/rfc/rfc8659), which defines the `issue`, `issuewild` and `iodef` properties.
- **SRV** is defined in [RFC 2782](https://www.rfc-editor.org/rfc/rfc2782): priority, weight, port and target. Browsers do not use it to find websites.
- **Subdomains** (`www`, `blog`, `shop.example.com`) are just more names in the same zone, unless you **delegate** one by adding NS records for it, which hands that subdomain to another DNS host. A delegated subdomain whose nameservers you stop controlling is one route to takeover.
- **Reserved names for practice.** [RFC 2606](https://www.rfc-editor.org/rfc/rfc2606) sets aside `example.com`, `example.net`, `example.org` and the TLDs `.test`, `.example`, `.invalid` and `.localhost` for documentation and testing. This page uses `example.test` for the local lab (so nothing you configure can collide with a real name) and `example.com` for read-only lookups. The documentation address blocks are `192.0.2.0/24`, `198.51.100.0/24` and `203.0.113.0/24` ([RFC 5737](https://www.rfc-editor.org/rfc/rfc5737)) and `2001:db8::/32` for IPv6 ([RFC 3849](https://www.rfc-editor.org/rfc/rfc3849), est.: not read for this page).

### TTL and caching: why changes "take time"

The **TTL** (time to live) on a record says how many seconds a resolver may keep the answer. A resolver that has your record cached with a TTL of 3,600 will keep giving the old address for up to an hour after you change it, and nothing you do at the DNS host can reach inside that cache. That is the whole story behind "DNS propagation": it is not data traveling around the world, it is thousands of independent caches expiring at different moments. The standard describes TTL as a cache limit ([RFC 1034](https://www.rfc-editor.org/rfc/rfc1034), [RFC 2181](https://www.rfc-editor.org/rfc/rfc2181)).

Practical rules:

- **Before a planned move, lower the TTL** (to 300 seconds, say) a full old-TTL ahead of time, make the change, then raise it again. Lowering it at the same moment as the change does nothing for caches that already hold the old record.
- **Negative answers are cached too.** If a name did not exist and a resolver cached "no such name", creating the record later does not help that resolver until the negative TTL passes. You will see this in Exercise 5.
- **Your own computer caches too.** An operating system or browser can hold an answer after the resolver has dropped it.
- On Cloudflare, proxied records have a fixed TTL of Auto, which is 300 seconds and cannot be edited; DNS-only records can be set between 60 seconds and one day on non-Enterprise plans ([Cloudflare TTL page](https://developers.cloudflare.com/dns/manage-dns-records/reference/ttl/)).

## Email records at concept level

A website domain should still publish email records, **even if it never sends mail**, because anyone can forge the `From:` address of your domain. Three TXT-based mechanisms let a receiving mail server check:

| Mechanism | One-sentence idea | Where it lives | Primary source |
|---|---|---|---|
| **SPF** (Sender Policy Framework) | A list of the servers allowed to send mail for the domain. | A `TXT` record at the domain, starting `v=spf1` | [RFC 7208](https://www.rfc-editor.org/rfc/rfc7208) |
| **DKIM** (DomainKeys Identified Mail) | The sending server signs each message; the public key to check the signature is published in DNS. | A `TXT` record at `selector._domainkey.yourdomain` | [RFC 6376](https://www.rfc-editor.org/rfc/rfc6376) |
| **DMARC** (Domain-based Message Authentication, Reporting and Conformance) | Tells receivers what to do when SPF and DKIM do not line up with the visible `From:` domain (nothing, quarantine, reject) and where to send reports. | A `TXT` record at `_dmarc.yourdomain` | [RFC 9989](https://www.rfc-editor.org/rfc/rfc9989) (with reporting in [RFC 9990](https://www.rfc-editor.org/rfc/rfc9990) and [RFC 9991](https://www.rfc-editor.org/rfc/rfc9991)); these obsolete [RFC 7489](https://www.rfc-editor.org/rfc/rfc7489), per the RFC Editor |

For a domain that sends no mail, the safe set is: an SPF record that allows nothing (`v=spf1 -all`), a DMARC record that says reject, and a **null MX** (`MX 0 .`) that says "this domain accepts no mail" ([RFC 7505](https://www.rfc-editor.org/rfc/rfc7505)). Exercise 2 reads exactly that set from `example.com`. For a domain that does send mail, the exact values come from your mail provider, and SPF has a limit of ten DNS lookups while it is evaluated ([RFC 7208](https://www.rfc-editor.org/rfc/rfc7208), the "10 mechanisms/modifiers" limit), which is why people who keep adding `include:` entries one day find mail rejected. Email is a deep subject; this page covers only the DNS records. For how mail flows, alignment, DMARC rollout, gateways and API-driven protection, and whether to run your own mail server, read [Email security: DNS records, gateways, API-driven protection, and running your own server](Email-Security-DNS-Gateways-and-API-Driven-Protection.md).

## DNSSEC at concept level

Ordinary DNS answers are plain text with nothing to prove they are genuine. **DNSSEC** (DNS Security Extensions) adds digital signatures to DNS data so a validating resolver can tell an answer came from the zone's owner and was not changed on the way. The pieces ([RFC 4033](https://www.rfc-editor.org/rfc/rfc4033), [RFC 4034](https://www.rfc-editor.org/rfc/rfc4034), [RFC 4035](https://www.rfc-editor.org/rfc/rfc4035); [RFC 9364](https://www.rfc-editor.org/rfc/rfc9364) is the current summary):

- The DNS host **signs** your zone's records with a key and publishes the public part as a `DNSKEY` record.
- You give your registrar a **`DS` record**, a fingerprint of that key. The registry publishes it in the parent zone, which links the chain of trust down from the root.
- A resolver that validates checks the chain; if the signatures do not match, it returns an error instead of a forged answer.

What it does **not** do: it does not encrypt anything (the RFC says the extensions "do not provide confidentiality"), it does not protect a visitor whose own resolver does not validate, and it does not help if the attacker has your registrar or DNS host login and simply publishes valid signed records. It protects against forged answers on the path, not against a stolen account.

The practical trap, from Cloudflare's own documentation: if DNSSEC is enabled at your old DNS host and you change nameservers without first removing the `DS` record at the registrar, validating resolvers can reject the new DNS host's answers and the domain can become unreachable ([Cloudflare DNSSEC](https://developers.cloudflare.com/dns/dnssec/)). Turn it off before the move, then turn it on again at the new host and add the new `DS` record.

## Cloudflare: what it is, and why this lesson uses it

**Cloudflare** is a company that sells, among other things, authoritative DNS hosting, a **reverse proxy** and content delivery network (CDN) in front of websites, and a registrar. This lesson teaches the concepts in a vendor-neutral way, then uses Cloudflare for the hands-on path.

**Recommendation, and how to read it.** The maintainer recommends Cloudflare for a first domain, and says he runs it himself for his own domains. That is his statement; this page cannot check it. There is no affiliation to disclose. The project's standing promise is to disclose any affiliation on the page where it applies, as it appears. The recommendation rests on facts you can read yourself, listed in the [claims register](#claims-register): the DNS and proxy features are on the Free plan, the registrar sells at cost, and the documentation is public. It is not the only sound choice:

| Alternative | Honest note |
|---|---|
| **Your registrar's own DNS** | Fewest moving parts; features and quality vary by registrar. A fine place to start; you can move later (est.). |
| **DigitalOcean DNS** | Free per DigitalOcean's pricing page; fits if the server is already a DigitalOcean droplet. It is DNS only: it does not proxy web traffic. |
| **AWS Route 53** | $0.50 per hosted zone per month for the first 25 zones (pricing page, 2026-10-22). Strong if you already live in AWS. |
| **Other DNS hosts** (several exist) | Compare on price, API, DNSSEC support, and what happens to your records if you leave. |

One trade-off to know before you commit, from Cloudflare's own transfer page: **Cloudflare Registrar requires the domain to use Cloudflare for authoritative DNS; you cannot use another DNS provider while registered there.** If you want the freedom to move DNS later, register the name somewhere else and only delegate DNS to Cloudflare.

### The Free plan, as read on 2026-10-22

The Cloudflare plans page lists the Free plan at $0 a month and shows DNS, unmetered DDoS protection, a CDN and a Universal SSL certificate among its features. A WAF row and a "Free Managed Ruleset" row also appear; I did not verify per-plan limits for firewall rules, so check the page for what Free includes today before you rely on a specific rule. Origin CA certificates and Authenticated Origin Pulls are both listed as available on Free in their documentation pages. A primary (full) DNS setup, where Cloudflare holds your zone, is "the only one available for Free or Pro plans" ([Cloudflare zone setups](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/)).

### Delegating to Cloudflare, in outline

Cloudflare's full-setup guide, as read, goes: add the domain ("Onboard a domain"), choose a plan, review the records it scanned (the scan "is not guaranteed to find all existing DNS records"), turn **off** DNSSEC at the old DNS host if it is on, replace the registrar's nameservers with the two Cloudflare assigns to your zone, and wait (the page says "up to 24 hours") until the domain shows **Active**. Cloudflare's standard nameservers follow the pattern `<name>.ns.cloudflare.com`, are assigned per zone and cannot be chosen. Copy them exactly; "if their names are not copied exactly, your DNS will not resolve correctly". Check from outside with `dig NS yourdomain @1.1.1.1` and `@9.9.9.9`, as Cloudflare's guide suggests.

### Proxied or DNS-only: the orange cloud

For `A`, `AAAA` and `CNAME` records Cloudflare gives each record a switch ([Cloudflare proxy status](https://developers.cloudflare.com/dns/proxy-status/)):

| Question | **Proxied** (orange cloud) | **DNS-only** (gray cloud) |
|---|---|---|
| A lookup of the name returns | A Cloudflare address, not yours | Your real server address |
| Web traffic goes | Visitor, then Cloudflare, then your server | Visitor straight to your server |
| Cloudflare can cache, filter, rate-limit and add a WAF | Yes | No |
| Your server's address is | Hidden from a simple lookup | **Visible to anyone who asks DNS** |
| Works for | HTTP and HTTPS web traffic | Anything (mail, SSH, other services) |
| TTL | Fixed at Auto (300 seconds) | You choose |

Cloudflare's page says other record types (MX, TXT) are always DNS-only, and recommends proxying records that serve web traffic and keeping records for mail and domain verification DNS-only.

**What proxying hides, and what it does not.** It hides your server's address *in DNS*. It does not hide it from:

- **Old DNS history.** Public services record past answers; a record that was DNS-only yesterday may still be in a history database.
- **Other records that point at the server.** A `mail` record, an `ssh` record, an `ftp` record, or a gray-cloud `dev` record on the same address gives it away. Cloudflare says the same: an origin address can be found "through historical DNS records or mail server configuration".
- **The server's own behavior.** A certificate scan of the internet's address space can match your certificate to your address; a site that echoes its own address in a page or header gives it away.

Once the address is known, an attacker connects straight to it and skips the proxy and its WAF. That is why the **origin must refuse everyone except the proxy**, the next section. Once the origin does accept only the proxy, it sees only the proxy's address on every connection; [Behind a CDN: real client IPs, why an IP is a weak identifier, and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) shows how to get the visitor's address back safely.

## TLS between the visitor, Cloudflare and your server

With a proxy there are **two** TLS connections: visitor to Cloudflare (the padlock the visitor sees, using a certificate Cloudflare provides; the setup page says Universal SSL certificates are free to all Cloudflare domains) and Cloudflare to your server (the **origin** connection, where your server presents a certificate). The setting that controls the second connection is the **SSL/TLS encryption mode**:

| Mode | Cloudflare to origin | Origin certificate checked? | Cloudflare's own guidance (docs, read 2026-10-22) |
|---|---|---|---|
| **Off** | Plaintext HTTP; and it redirects HTTPS requests to HTTP | n/a | "Cloudflare does not recommend setting your encryption mode to Off." |
| **Flexible** | Plaintext HTTP | n/a; no origin certificate needed | "Partially secure"; do not use if the origin redirects HTTP to HTTPS (redirect loop); "if your application contains sensitive information... use Full or Full (Strict)" |
| **Full** | HTTPS | **No.** "It can be expired, self-signed, or not even have a matching CN/SAN entry" | "Without using Full (strict), a malicious party could technically hijack the connection and present their own certificate." |
| **Full (strict)** | HTTPS | **Yes.** Unexpired; from a publicly trusted CA or Cloudflare's Origin CA; name matches | "For the best security, choose Full (strict) mode whenever possible" |

Cloudflare also says it "strongly recommends" Full or Full (strict). There is also an **Automatic SSL/TLS** option that chooses a mode for you and never moves you to a less secure one; this lesson sets the mode by hand so you see what each does.

**Why Flexible is a trap.** The padlock in the visitor's browser is real in Flexible mode, so the site *looks* secure. But the leg from Cloudflare to your server crosses the internet in plaintext, passing through networks you do not control. Login cookies, form posts and session tokens ride that leg unencrypted, readable and changeable by anyone on the path. It is a trust-boundary mistake: the visitor's browser tells them the whole journey is protected, and half of it is not. Flexible exists for origins that *cannot* speak TLS; a droplet can, so there is no reason to choose it.

**Why Full is only half the job.** Full encrypts the second leg but does not verify who answers. Anyone who intercepts the connection can present any certificate and Cloudflare accepts it. Full (strict) closes that.

### Origin certificates

For Full (strict) your server needs a certificate Cloudflare will accept: one from a publicly trusted CA (for example one issued by an ACME client, per [RFC 8555](https://www.rfc-editor.org/rfc/rfc8555), a protocol this page does not teach), or a **Cloudflare Origin CA certificate**. The latter is created in the Cloudflare dashboard (SSL/TLS, Origin Server, Create Certificate), is free on every plan per its documentation page, and is trusted **only by Cloudflare**, not by browsers: "these certificates only encrypt traffic between Cloudflare and your origin server, not traffic from client browsers to your origin". If you turn the proxy off, visitors see certificate errors. Two cautions from that page: the private key is shown **once**, on the creation screen, and cannot be seen again; and "Cloudflare does not currently send expiration notifications for origin CA certificates", so track the expiry yourself (the [expiry-monitoring habit from the TLS lesson](How-a-Web-Request-Works.md#build-break-detect-evade-defend) applies). Never put the private key in a repository or a chat; copy it straight into a root-only file on the server.

## Lock the origin to Cloudflare

A proxied site has two doors: the proxy and the server's own public address. Close the second.

**Layer 1: the cloud firewall.** Allow inbound web traffic (port 443) only from Cloudflare's published ranges, and everything else only from you. Cloudflare publishes its ranges at [cloudflare.com/ips-v4](https://www.cloudflare.com/ips-v4) and [cloudflare.com/ips-v6](https://www.cloudflare.com/ips-v6) and on its [IP addresses page](https://developers.cloudflare.com/fundamentals/concepts/cloudflare-ip-addresses/), which says: "block all traffic that does not come from Cloudflare IP addresses or the IP addresses of your trusted partners, vendors, or applications", and that the ranges "do not change frequently" and are "added to our list of IP ranges before being put into production". This page does not copy the list, because a copy goes stale; the walkthrough fetches it when you run it.

**Layer 2: Authenticated Origin Pulls (mTLS).** A firewall allows by address. An address list is a coarse test: every Cloudflare customer's proxy comes from those same addresses, so another customer's proxy could be pointed at your origin address. Cloudflare's **Authenticated Origin Pulls** makes Cloudflare present a client certificate on the origin connection, and your server rejects connections without it. Cloudflare's page says it "helps ensure requests to your origin server come from the Cloudflare network", works only in Full or Full (strict) modes, is available on all plans, and is not compatible with Cloudflare Tunnel. Setting it up is beyond this lesson; W4 picks the topic up for sites at scale.

**Layer 3: do not rely on the proxy for patching.** A WAF reduces risk; it does not remove a bug in the software behind it. In October 2026 the PHP project released 8.5.12, and its changelog lists fixes for two GitHub security advisories, titled "RCE via OOM corruption" and "RCE via stale global state", both rated Critical on the php-src advisory pages (read 2026-10-22; I did not test whether any WAF rule blocks them, and the advisories' own text says the exact exposure depends on the PHP configuration and server software). The lesson for this page: a WAF in front of a reachable origin is not a patch, and a server reachable directly by address skips the WAF entirely. Keep the origin unreachable except through the proxy **and** keep PHP patched. [WordPress and PHP security, WAF and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) (W2) covers the patching and WAF side.

## Hosting your own website: the walkthrough

> **Status of this section: written from vendor documentation, never run.** Treat each step as a draft to test, on an account and a domain you can afford to break.

The pieces, in the order a visitor meets them: **domain** (registrar), **DNS zone**, **Cloudflare proxy and WAF settings**, **origin firewall**, **origin server**, **TLS**. The whole path:

1. **Buy a domain** at the registrar of your choice. The cost is the registrar's yearly fee. Before paying, read the registrar's refund and renewal terms. Turn on two-factor authentication on the registrar account at once, use a unique password, and note the recovery path.
2. **Create the Cloudflare account** (Free plan), turn on two-factor authentication there too, and onboard the domain ("full" setup). Review the scanned records and delete any you do not recognize.
3. **Delegate DNS**: at the registrar, turn off DNSSEC if it is on, replace the nameservers with the two Cloudflare assigned, save, then wait until the domain shows **Active** and `dig NS yourdomain @1.1.1.1` shows Cloudflare's names.
4. **Build the origin** (see below), with its cloud firewall **before** the first boot is exposed.
5. **Add the records**: `A` for the apex and `www` pointing at the droplet's public address, **proxied**. No `AAAA` unless you have IPv6 on the droplet.
6. **TLS**: create an Origin CA certificate, install it, set the mode to **Full (strict)**.
7. **Test**, with the commands below.
8. **Tear down** in the order given in the teardown section.

### Build the origin

The origin is "a small droplet running the W1 stack, or a static site". The W1 lesson is [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md). If it is not merged yet, use the static version here: the same nginx, no PHP and no database, which also has the smallest attack surface of any option.

Cost and teardown first: one `s-1vcpu-1gb` droplet is $6 a month at list price (`docs/cost-prices.json`), billed while it exists even if powered off, and destroying it ends billing. Set a reminder for the day you plan to destroy it.

```bash
export REGION=tor1 SIZE=s-1vcpu-1gb IMAGE=ubuntu-24-04-x64
export MY_IP=203.0.113.7                      # replace: YOUR current public address; this is a documentation address
doctl compute ssh-key list --format ID,Name   # note your key's ID
export KEY_ID=YOUR_KEY_ID

# 1. The firewall first, attached by tag, so the droplet is never open.
#    Cloudflare's ranges are fetched now, from Cloudflare, not copied into this page.
set -eu    # stop on the first error: a failed fetch must never reach the firewall command
CF_RANGES="$(curl -fsS https://www.cloudflare.com/ips-v4 https://www.cloudflare.com/ips-v6)"
# Fail closed: refuse to continue unless both lists came back, with a plausible count.
[ "$(printf '%s\n' "$CF_RANGES" | grep -c '[./:]')" -ge 10 ] || { echo "Cloudflare ranges missing; stopping" >&2; exit 1; }
CF_RULES=""
for r in $CF_RANGES; do
  CF_RULES="${CF_RULES},address:${r}"
done
case "$CF_RULES" in ,address:*) ;; *) echo "empty rule list; stopping" >&2; exit 1;; esac
doctl compute firewall create --name web-origin --tag-names web-origin \
  --inbound-rules "protocol:tcp,ports:443${CF_RULES} protocol:tcp,ports:22,address:${MY_IP}/32" \
  --outbound-rules "protocol:tcp,ports:80,address:0.0.0.0/0,address:::/0 protocol:tcp,ports:443,address:0.0.0.0/0,address:::/0 protocol:udp,ports:53,address:0.0.0.0/0,address:::/0 protocol:tcp,ports:53,address:0.0.0.0/0,address:::/0 protocol:udp,ports:123,address:0.0.0.0/0,address:::/0"

# 2. The droplet, carrying the tag.
doctl compute droplet create web-origin --region "$REGION" --size "$SIZE" --image "$IMAGE" \
  --ssh-keys "$KEY_ID" --tag-names web-origin --wait
export ORIGIN_IP=$(doctl compute droplet get web-origin --format PublicIPv4 --no-header)
```

Save this block as a script and run it with `bash`, rather than pasting it into your login shell: `set -eu` would close an interactive terminal on the first error. The count check is a sanity floor (the lists held 22 entries on 2026-10-22), not a validation of the ranges; compare them with Cloudflare's page if anything looks off. In PowerShell, build the list with `$ErrorActionPreference = 'Stop'`, then `$cf = (curl.exe -fsS https://www.cloudflare.com/ips-v4 https://www.cloudflare.com/ips-v6) -split "\s+" | Where-Object { $_ }`, stop if `$LASTEXITCODE -ne 0` or `$cf.Count -lt 10`, and only then `$CF_RULES = ($cf | ForEach-Object { ",address:$_" }) -join ""`; the `doctl` flags are the same (est.).

Notes on this block, each marked as what I read or did not: DigitalOcean's firewall limits page says a rule's Sources field can hold up to 1,000 entries and a firewall up to 50 rules, so the 22 Cloudflare ranges (15 IPv4 and 7 IPv6 on 2026-10-22) fit in one rule. That several `address:` entries can be repeated inside one rule string with `doctl` is **est.**: the reference shows the single-address form, so if the command is refused, create the firewall in the control panel and paste the ranges into the Sources box. The outbound rules allow what a patching server needs (package downloads on 80 and 443, DNS on both UDP and TCP port 53 because resolvers fall back to TCP for large answers, and time) and nothing more; check them against [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) for the reasoning. Port 80 is deliberately **not** open inbound: with the proxy in front, Cloudflare can redirect HTTP to HTTPS at its own edge (its Flexible-mode page points to an "Enforce HTTPS connections" setting for this), so the origin needs only 443. The exact setting name in your dashboard is **est.**

On the droplet, a static site and a TLS server block (nginx), using the Origin CA certificate you create in the dashboard:

```bash
ssh root@"$ORIGIN_IP"
apt-get update && apt-get -y install nginx
mkdir -p /var/www/site /etc/ssl/origin
printf '<!doctype html><title>hello</title><p>hello from the origin\n' > /var/www/site/index.html
# Paste the certificate and the key from the Cloudflare screen into these files.
# Use an editor on the server; never paste the key into a chat, an issue or a repository.
install -m 600 /dev/null /etc/ssl/origin/origin.key
install -m 644 /dev/null /etc/ssl/origin/origin.pem
nano /etc/ssl/origin/origin.pem
nano /etc/ssl/origin/origin.key
cat > /etc/nginx/sites-available/site <<'EOF'
server {
    listen 443 ssl default_server;
    server_name example.com www.example.com;     # replace with your own domain
    ssl_certificate     /etc/ssl/origin/origin.pem;
    ssl_certificate_key /etc/ssl/origin/origin.key;
    root /var/www/site;
}
EOF
ln -sf /etc/nginx/sites-available/site /etc/nginx/sites-enabled/site
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

(`install -m 600 /dev/null FILE` creates an empty file that only root can read, before you put a key in it. That the Ubuntu 24.04 image's nginx package ships `sites-available` and `sites-enabled` as shown is **est.**; check on the droplet.)

### Add the records and set the mode

In the dashboard (no command-line token needed for this lesson): DNS, Records, add an `A` record with name `@` (the apex) and value your droplet's address, **Proxied**; and another named `www`. Then SSL/TLS, Overview, set the encryption mode to **Full (strict)**. Order matters: switching to Full (strict) before the origin certificate is installed produces error `526` for visitors (the Cloudflare Full (strict) page names it).

### Test it

```bash
# 1. DNS: what do outsiders learn? You should see Cloudflare addresses, NOT your droplet's.
dig +short yourdomain @1.1.1.1
dig +short yourdomain NS @1.1.1.1

# 2. The site works through the proxy, over HTTPS.
curl -sI https://yourdomain/ | head -5

# 3. The origin refuses everyone else. These should time out (exit 28), not answer.
curl --connect-timeout 5 -sSk https://"$ORIGIN_IP"/ ; echo "exit=$?"
```

```powershell
Resolve-DnsName yourdomain -Server 1.1.1.1 -Type A -DnsOnly
curl.exe -sI https://yourdomain/
curl.exe --connect-timeout 5 -sSk https://$env:ORIGIN_IP/ ; "exit=$LASTEXITCODE"
```

If the third command returns your page, the origin is open to the world and the firewall rule is wrong. That is the single most important test on this page.

### Teardown and transfer

Order matters, because a DNS record that outlives its server is a takeover waiting to happen (see below).

1. **Delete the A records** (or set them to a parked page) first. Never leave a record pointing at an address you no longer control.
2. **Destroy the droplet**, then the firewall, then prove it: `doctl compute droplet list` and `doctl compute firewall list` show nothing named `web-origin`. Check billing again tomorrow, as the [teardown checklist](Teardown-Checklist.md#3-prove-zero-billable-resources) says.
3. **Revoke the Origin CA certificate** in the dashboard if you will not reuse it, and delete the key files you downloaded. Cloudflare's page warns that revoking cannot be undone.
4. **Decide about the domain.** To keep it: leave auto-renew on and the account secured. To let it go: turn auto-renew off and let it expire. A lapsed name can be registered by anyone, including someone who then receives mail or links meant for you, so first remove any service that trusted it. To **transfer** it to another registrar: unlock it, request an authorization code, and approve. Cloudflare's transfer page says the domain must be at least 60 days old and not transferred in the last 60 days (an ICANN requirement), and that changing the registrant name, organization or email in the last 60 days triggers a 60-day lock under ICANN rules. A transfer usually takes up to ten days, depending on the registrar, and Cloudflare says most include a one-year extension.
5. **Remove the zone** from Cloudflare when you no longer need it. If you move nameservers back to the registrar first, the domain keeps resolving while you do.

## Build it piece by piece or all at once

Every build in this track works two ways: one piece at a time, learning each, or the whole thing at once. The pieces:

| Piece | Depends on | Cost per month on your own accounts | Build order | Destroy order |
|---|---|---|---|---|
| **Domain and registrar** | Nothing | The registrar's yearly fee, divided by twelve; **price not read, so no figure here**. Renews yearly; refund depends on the registrar's own terms (not read) | 1 | 6 (last, and optional: letting it lapse is a choice with consequences) |
| **DNS zone** (records, DNSSEC, email records) | Domain | $0 on Cloudflare Free and on DigitalOcean DNS; $0.50 on Route 53 (all read 2026-10-22) | 3 | 2 (records go **before** the server) |
| **Origin server** | Account, firewall | $6 for `s-1vcpu-1gb` at list price (`docs/cost-prices.json`), billed until destroyed | 2 | 3 |
| **Origin firewall** | Origin server tag; Cloudflare's published ranges | $0 (cloud firewalls are free in the project's cost gate: see [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md)) | 2 (created with or before the server) | 4 |
| **TLS** (origin certificate and mode) | DNS zone, origin server | $0 for an Origin CA certificate (Cloudflare docs, read 2026-10-22) | 4 | 1 (revoke; or leave: it expires) |
| **Cloudflare proxy and WAF settings** | DNS zone, TLS, origin firewall | $0 on Free; other plans have their own prices, not read | 5 | 1 (turn the proxy off before you delete the origin) |

The build order reads: domain, then server and firewall together, then DNS records, then TLS, then turn on the proxy and its protections last, once everything behind it works. The destroy order reads the other way: switch the proxy off, delete the records that point at the server, destroy the server and its firewall, remove the zone, and only then decide about the domain.

### Three ways to do it

1. **By hand.** This page's walkthrough and the dashboard. Slowest, teaches the most, and the easiest way to understand what each step changes. Nothing is remembered between runs except your notes.
2. **One OpenTofu stack per piece.** The maintainer has ruled that each service is its own OpenTofu stack with its own build and destroy, so a piece can be created and destroyed without touching the others. The method is taught in [OpenTofu from zero](OpenTofu-From-Zero.md) and [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md). **Until those pages are merged, those two links lead nowhere**; [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) already exists and explains how this project lays out stacks. **No web-hosting stack exists in this repository yet; the examples below are teaching code, not shipped infrastructure.**
3. **One composed launch.** A single configuration that calls every piece in order and one command that destroys them all in reverse. The least typing and the least learning; use it after you have done the pieces once. A composed launch has to respect the same ordering: records are created after the server's address is known and destroyed before the server is.

Whichever you pick, destroy in the destroy order above, and prove it with read-only listings.

### A read-and-run example: the DNS records as data (free, local)

The free way to see "DNS as code" needs no Cloudflare account and no network: records are described as data, and OpenTofu renders them into a zone file for the `dnsmasq` server from the lab below, using only built-in functions (no provider is downloaded; `tofu init` needs no registry access for this). Save as `main.tf` in an empty folder:

```terraform
# SPDX-License-Identifier: Apache-2.0
# DNS records as data, rendered into a dnsmasq zone for the local lab.
# No provider, no account, no network: only OpenTofu's built-in functions.

variable "zone" {
  type    = string
  default = "example.test"
}

variable "records" {
  type = list(object({
    name  = string # "@" is the zone apex
    type  = string # A, AAAA, CNAME or TXT in this example
    value = string
  }))
  default = [
    { name = "@", type = "A", value = "192.0.2.11" },
    { name = "www", type = "A", value = "192.0.2.10" },
    { name = "blog", type = "CNAME", value = "www" },
    { name = "@", type = "TXT", value = "v=spf1 -all" },
  ]

  validation {
    condition     = alltrue([for r in var.records : contains(["A", "AAAA", "CNAME", "TXT"], r.type)])
    error_message = "This example renders A, AAAA, CNAME and TXT only."
  }
}

locals {
  named = [
    for r in var.records :
    merge(r, { fqdn = r.name == "@" ? var.zone : "${r.name}.${var.zone}" })
  ]

  lines = [
    for r in local.named :
    r.type == "A" || r.type == "AAAA" ? "host-record=${r.fqdn},${r.value}" :
    r.type == "CNAME" ? "cname=${r.fqdn},${r.value}.${var.zone}" :
    "txt-record=${r.fqdn},\"${r.value}\""
  ]
}

output "dnsmasq_records" {
  value = join("\n", local.lines)
}
```

```bash
tofu init -input=false
tofu apply -auto-approve -input=false
tofu output -raw dnsmasq_records > records.conf ; cat records.conf
```

On 2026-10-22 this printed four lines (`host-record=example.test,192.0.2.11`, `host-record=www.example.test,192.0.2.10`, `cname=blog.example.test,www.example.test`, `txt-record=example.test,"v=spf1 -all"`), and a `dnsmasq` instance loading it with `conf-file=` answered for `www`, `blog` and the apex. Change `192.0.2.10` to `192.0.2.77` and run `tofu plan`: it shows the output changing by one line. That is the point of the example, with one honest limit: here the "plan" is a text difference between two renderings, not a comparison against live records, because there is no remote system. A real provider compares against the real zone and can also show a record you added by hand that the code does not know about.

**The same resources against Cloudflare, as read-only text.** This is what the free example becomes with a real provider. Do not run it without a Cloudflare account, a scoped API token and an understanding of what it will change. Provider and resource names were checked on 2026-10-22: `registry.opentofu.org` lists the provider `cloudflare/cloudflare` with 5.28.1 as the newest 5.x release, and the provider's own documentation (in its public repository, which the registry page mirrors) names the resources `cloudflare_zone`, `cloudflare_dns_record`, `cloudflare_zone_setting` and `cloudflare_zone_dnssec`. The older 4.x provider named the record resource differently (est.: I did not read 4.x documentation), so match the resource names to the version you pin.

```terraform
terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.28"
    }
  }
}

variable "cloudflare_api_token" {
  type      = string
  sensitive = true # supplied from the environment or a secrets manager, never written in a file
}

variable "account_id" { type = string }
variable "origin_ip"  { type = string } # from the droplet, e.g. a 192.0.2.x placeholder while reading

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

resource "cloudflare_zone" "site" {
  account = { id = var.account_id }
  name    = "example.com"
  type    = "full"
}

resource "cloudflare_dns_record" "apex" {
  zone_id = cloudflare_zone.site.id
  name    = "@"
  type    = "A"
  content = var.origin_ip
  proxied = true
  ttl     = 1 # 1 means automatic, per the provider docs
}

resource "cloudflare_dns_record" "www" {
  zone_id = cloudflare_zone.site.id
  name    = "www"
  type    = "A"
  content = var.origin_ip
  proxied = true
  ttl     = 1
}

resource "cloudflare_zone_setting" "ssl" {
  zone_id    = cloudflare_zone.site.id
  setting_id = "ssl"
  value      = "strict" # the provider's allowed values: off, flexible, full, strict
}

resource "cloudflare_zone_dnssec" "site" {
  zone_id = cloudflare_zone.site.id
  status  = "active"
}
```

What the real version does not do for you: it does not buy the domain, it does not change the registrar's nameservers (you do that by hand, once), and it does not add the `DS` record at the registrar (the DNSSEC resource produces the values you give the registrar). The token needs only the permissions the provider documentation lists for these resources (DNS read and write, Zone Settings read and write, and zone creation); create it narrow, per the [APIs and tokens](APIs-and-Tokens-From-Zero.md#scopes-and-least-privilege) lesson.

## Free theory path: a DNS lab on your own computer

Everything in this section runs on your computer and costs nothing. Every exercise follows four steps: **predict** (write down what you expect), **do**, **check**, **undo**. The only third-party servers touched are public DNS servers, queried read-only with a handful of ordinary lookups, which is what any resolver does all day.

**Which track.** Bash is complete. The lab **servers** use `dnsmasq`, which is a Linux program: on Windows run the server side inside WSL (est.). `Resolve-DnsName` has no option for a port other than 53 (its documented parameters include `-Server`, `-Type`, `-DnsOnly` and `-NoRecursion`, and no port), so the PowerShell lab queries use `nslookup -port=PORT` instead (the `-port=` option form is **est.**; Microsoft's `nslookup` page documents a `set port` command). Install on Debian or Ubuntu with `sudo apt install dnsmasq-base dnsutils` (the first provides the `dnsmasq` program without starting a system service; the second provides `dig`); package names on other systems are **est.**

### Exercises on public DNS (read only)

#### Exercise 1: walk a delegation by hand

**Predict.** The root servers do not know the address of `example.com`. What will one of them answer when asked for it, and what will a `com` server answer?

**Do (Bash).** `+norecurse` asks a server only for what it knows itself, so you see the referral instead of a finished answer.

```bash
dig @a.root-servers.net example.com A +norecurse +noall +authority | head -4
dig @a.gtld-servers.net example.com A +norecurse +noall +authority +additional | head -6
dig @hera.ns.cloudflare.com example.com A +norecurse +noall +answer +comments | grep -E 'flags|IN'
```

**Do (PowerShell, est.).**

```powershell
Resolve-DnsName example.com -Type A -Server a.root-servers.net -DnsOnly -NoRecursion
Resolve-DnsName example.com -Type A -Server a.gtld-servers.net -DnsOnly -NoRecursion
```

**Check.** On 2026-10-22 the root server answered with a list of `com` nameservers (a referral, with a TTL of 172800 seconds, two days); the `com` server answered with the two nameservers for `example.com`, plus their addresses (the **glue**: addresses supplied in the referral because the nameserver's own name lives inside the zone it serves); and the third query came from the zone's own server with the `aa` flag (authoritative answer) and two `A` records with a 300-second TTL (trimmed; yours will differ):

```text
com.            172800  IN  NS  l.gtld-servers.net.
example.com.    172800  IN  NS  hera.ns.cloudflare.com.
example.com.    172800  IN  NS  elliott.ns.cloudflare.com.
;; flags: qr aa; QUERY: 1, ANSWER: 2, AUTHORITY: 0, ADDITIONAL: 1
example.com.    300  IN  A   (two Cloudflare addresses)
```

That is delegation: root to `com` to the zone's own servers. Note the last line: the 300-second TTL and Cloudflare addresses are what a proxied record looks like from outside, and `example.com` happens to be one.

**Undo.** Nothing; lookups change nothing. One request per command; do not loop them.

#### Exercise 2: read a real zone's records

**Predict.** `example.com` is documentation. Does it send mail? What do you think its SPF, MX and DMARC say?

**Do (Bash).**

```bash
dig @1.1.1.1 example.com NS +noall +answer
dig @1.1.1.1 example.com SOA +noall +answer
dig @1.1.1.1 example.com MX +noall +answer
dig @1.1.1.1 example.com TXT +noall +answer
dig @1.1.1.1 _dmarc.example.com TXT +noall +answer
dig @1.1.1.1 example.com CAA +short
dig @1.1.1.1 example.com A +dnssec +noall +comments | grep flags
```

**Do (PowerShell, est.).**

```powershell
foreach ($t in 'NS','SOA','MX','TXT') { Resolve-DnsName example.com -Type $t -Server 1.1.1.1 -DnsOnly }
Resolve-DnsName _dmarc.example.com -Type TXT -Server 1.1.1.1 -DnsOnly
Resolve-DnsName example.com -Type CAA -Server 1.1.1.1 -DnsOnly
```

**Check.** On 2026-10-22: two Cloudflare nameservers; an SOA naming one of them; `MX 0 .` (the null MX: accepts no mail); a TXT set including `"v=spf1 -all"` (nobody may send as this domain); `_dmarc` with `"v=DMARC1;p=reject;sp=reject;adkim=s;aspf=s"`; no CAA records (empty output); and an `ad` flag in the last query (the resolver validated DNSSEC signatures: `ad` means "authenticated data"). The domain has the "domain that sends no mail" set from the email section. You used `dig`'s `+dnssec` option only to ask for signatures; to see the signing key itself, `dig example.com DNSKEY +short`.

**Undo.** Nothing. Note that a TXT record at `example.com` can also carry verification tokens for services; do not paste the full output of your own domain into a public place without reading it.

### The local lab: your own authoritative server and resolver

Two `dnsmasq` programs on the loopback address (`127.0.0.1`, reachable only from your own machine): one acts as the **authoritative server** for the zone `example.test`, the other as a **caching resolver** that forwards `example.test` questions to the first, like a real resolver would. They use ports 5300 and 5301, which need no administrator rights. (Port 5353 is avoided: mDNS uses it.) Nothing here listens on a network address, touches your system resolver settings or needs root.

Create a folder and the generator script (it writes the zone, so you can regenerate it with a different address later):

```bash
mkdir -p -m 700 ~/dns-lab && cd ~/dns-lab
[ "$(stat -c %u .)" = "$(id -u)" ] && [ -z "$(find . -maxdepth 0 -perm /022)" ] || { echo "~/dns-lab is not private to you; stop" >&2; exit 1; }   # the pid files live here, so only you may write to it
cat > stop-dns.sh <<'STOP_EOF'
#!/usr/bin/env bash
# stop-dns.sh NAME...: stop the dnsmasq started with NAME.conf (auth, resolver or tofu-auth).
# It kills only when the pid file is ours, holds only digits, and that process is a dnsmasq using NAME.conf.
for n in "$@"; do
  case $n in tofu-auth) f="$PWD/tofu.pid" ;; *) f="$PWD/$n.pid" ;; esac
  [ -f "$f" ] && [ -O "$f" ] || continue
  pid="$(cat "$f")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && [[ "$(ps -o command= -p "$pid" 2>/dev/null)" == *"dnsmasq"*"$n.conf"* ]]; then kill "$pid"; fi
  rm -f "$f"
done
STOP_EOF
chmod +x stop-dns.sh
cat > make-auth.sh <<'EOF'
#!/usr/bin/env bash
# make-auth.sh [IPV4_FOR_WWW] writes auth.conf: the zone example.test (www defaults to 192.0.2.10)
set -eu
WWW="${1:-192.0.2.10}"
# CAA record data, built here at run time: flags 0, tag length 5, "issue", then the CA name.
CAA_HEX=$(printf '\000\005issueca.example.test' | od -An -tx1 | tr -d ' \n')
cat > auth.conf <<CONF
port=5300
listen-address=127.0.0.1
bind-interfaces
no-resolv
no-hosts
pid-file=$PWD/auth.pid
log-queries
log-facility=$PWD/auth.log
auth-server=ns1.example.test,127.0.0.1
auth-zone=example.test,192.0.2.0/24,2001:db8::/64,127.0.0.0/8
auth-ttl=30
auth-soa=2026102201,hostmaster.example.test,1200,120,604800
host-record=example.test,192.0.2.11
host-record=www.example.test,$WWW
host-record=ns1.example.test,127.0.0.1
host-record=app.example.test,2001:db8::10
host-record=mail.example.test,192.0.2.25
cname=blog.example.test,www.example.test
mx-host=example.test,mail.example.test,10
txt-record=example.test,"v=spf1 mx -all"
srv-host=_sip._tcp.example.test,www.example.test,5060
ptr-record=10.2.0.192.in-addr.arpa,www.example.test
dns-rr=example.test,257,$CAA_HEX
CONF
EOF
chmod +x make-auth.sh && ./make-auth.sh

cat > resolver.conf <<EOF
port=5301
listen-address=127.0.0.1
bind-interfaces
no-resolv
no-hosts
cache-size=150
log-queries
log-facility=$PWD/resolver.log
pid-file=$PWD/resolver.pid
server=/example.test/127.0.0.1#5300
server=/2.0.192.in-addr.arpa/127.0.0.1#5300
EOF
dnsmasq --test -C auth.conf && dnsmasq --test -C resolver.conf
dnsmasq -C auth.conf && dnsmasq -C resolver.conf
cat auth.pid resolver.pid
```

`dnsmasq` is a small server that is not a full authoritative implementation (its zone support is a subset, so the apex must exist as a host record and the addresses must fall inside the subnets given to `auth-zone`), but it answers real DNS and is enough to teach every concept here. The lab's `dns-rr` line builds a `CAA` record's data from text at run time, so no opaque hex string is stored in the page. The addresses are RFC 5737 and RFC 3849 documentation ranges.

**Stop it** whenever you finish (never `pkill -f`, which can match your own shell; `stop-dns.sh` reads each pid file, checks that it holds only digits, belongs to you and names a `dnsmasq` running that config, and only then stops it):

```bash
cd ~/dns-lab && ./stop-dns.sh auth resolver
```

```powershell
# Inside WSL, the same Bash commands; from Windows:
wsl -e bash -c 'cd ~/dns-lab && ./stop-dns.sh auth resolver'   # est.
```

#### Exercise 3: ask every record type

**Predict.** Which of these will answer with an `aa` flag, the authoritative server or the resolver? Which will show a TTL of 30 and which a smaller number?

**Do (Bash).**

```bash
A="dig +noall +answer @127.0.0.1 -p 5300"
$A www.example.test A
$A app.example.test AAAA
$A blog.example.test CNAME
$A example.test MX
$A example.test TXT
$A example.test SOA
$A example.test NS
$A example.test CAA
$A _sip._tcp.example.test SRV
$A nope.example.test A ; echo "(empty answer above means no such record)"
dig @127.0.0.1 -p 5300 nope.example.test | grep -E 'status|flags'
dig @127.0.0.1 -p 5301 www.example.test | grep -E 'flags|^www'
```

**Do (PowerShell, est.; the server runs in WSL).**

```powershell
foreach ($n in 'www.example.test','blog.example.test') { nslookup -port=5300 $n 127.0.0.1 }
nslookup -port=5300 -type=MX example.test 127.0.0.1
nslookup -port=5300 -type=TXT example.test 127.0.0.1
```

**Check.** On 2026-10-22 each query returned its record: `www` `192.0.2.10`; `app` `2001:db8::10`; `blog` a CNAME to `www.example.test.`; `MX 10 mail.example.test.`; `TXT "v=spf1 mx -all"`; an SOA with the serial `2026102201`; the NS `ns1.example.test.`; `CAA 0 issue "ca.example.test"`; and an SRV with port 5060. The authoritative server's header carried `aa`, the resolver's carried `ra` ("recursion available") and no `aa`: it is relaying, not owning. A name that does not exist returned `NXDOMAIN` (status), with the SOA in the authority section: that is the negative answer a resolver caches.

**Undo.** Nothing changed. Leave the servers running for the next exercises.

#### Exercise 4: a reverse lookup

**Predict.** To ask "who is `192.0.2.10`?", DNS needs a name to look up. What name would you build from the address?

**Do (Bash).**

```bash
dig +noall +answer @127.0.0.1 -p 5300 -x 192.0.2.10
dig +noall +answer @127.0.0.1 -p 5300 10.2.0.192.in-addr.arpa PTR
```

**Do (PowerShell, est.).**

```powershell
nslookup -port=5300 192.0.2.10 127.0.0.1
```

**Check.** Both forms return `10.2.0.192.in-addr.arpa. 30 IN PTR www.example.test.`: `-x` just builds that name for you by writing the address backwards (the four numbers reversed, then `in-addr.arpa`, so each step down the tree is a more specific piece of the address; IPv6 uses `ip6.arpa` and reverses the hexadecimal digits). Who answers for a reverse zone is whoever holds that address block (usually your internet or cloud provider), not you: on DigitalOcean you cannot edit the reverse name of a public address in DNS records, but you can set it by naming the droplet (est.; check DigitalOcean's documentation). Mail servers often distrust senders whose reverse name does not match.

**Undo.** Nothing.

#### Exercise 5: break a record, watch the cache lie

**Predict.** You change the address of `www` at the authoritative server. Immediately asking the resolver (which cached the old answer 20 seconds ago): old address or new? And after the TTL runs out?

**Do (Bash).**

```bash
cd ~/dns-lab
echo "--- first ask (fills the resolver's cache)"
dig +noall +answer @127.0.0.1 -p 5301 www.example.test
sleep 4
echo "--- ask again 4 seconds later: the TTL has counted down"
dig +noall +answer @127.0.0.1 -p 5301 www.example.test

echo "--- BREAK: change www at the authoritative server"
./stop-dns.sh auth; sleep 1; ./make-auth.sh 192.0.2.99; dnsmasq -C auth.conf; sleep 1
echo "authoritative says:"; dig +short @127.0.0.1 -p 5300 www.example.test
echo "resolver still says:"; dig +noall +answer @127.0.0.1 -p 5301 www.example.test

sleep 27
echo "--- after the TTL expired"
dig +noall +answer @127.0.0.1 -p 5301 www.example.test
```

**Do (PowerShell, est.).** The edit and restart happen in WSL as above; ask with `nslookup -port=5301 www.example.test 127.0.0.1` before, right after, and 30 seconds after the change.

**Check.** On 2026-10-22 the first answer was `www.example.test. 30 IN A 192.0.2.10`; four seconds later the TTL read 26. After the change the authoritative server returned `192.0.2.99` at once, while the resolver still returned `192.0.2.10` with a TTL of 23. After 27 more seconds the resolver returned `192.0.2.99` with a fresh 30. That gap is "propagation": the authority was right the whole time, and a cache served the old truth until its timer ran out. Now the negative case: `dig @127.0.0.1 -p 5301 nope.example.test` twice. The first returned `NXDOMAIN` after a forward (the resolver log shows `forwarded` then `reply ... is NXDOMAIN`), and the second returned `NXDOMAIN` from `cached`. Check with `tail -4 resolver.log`. A resolver can remember "this does not exist" as well.

**Undo.** `./make-auth.sh` regenerates the original zone (restart the authoritative server after).

#### Exercise 6: a dangling record

**Predict.** A subdomain `old` is an alias for a name at a service you stopped using and removed. What does the alias still do?

**Do (Bash).**

```bash
cd ~/dns-lab
./stop-dns.sh auth; sleep 1
./make-auth.sh
echo 'cname=old.example.test,gone.example.test' >> auth.conf
dnsmasq -C auth.conf; sleep 1
dig @127.0.0.1 -p 5300 old.example.test | grep -E 'status|CNAME'
dig @127.0.0.1 -p 5300 gone.example.test | grep -E 'status'
```

**Check.** The first query succeeds and returns the alias (`old.example.test. 30 IN CNAME gone.example.test.`); the second returns `NXDOMAIN`. Your zone still advertises a name that points at nothing. In the lab it is harmless. In real DNS the target (`gone`) is typically a name at a hosting or SaaS service: if anyone can register that name at the service again, they now serve content under **your** subdomain. That is a **subdomain takeover**, and the only fix is the one you can do now: delete the record. Cloudflare's own CNAME-flattening page notes the milder symptom: a CNAME whose final target has no address returns an empty answer, which can "make it appear as if the DNS record is not propagating".

**Undo.** `./make-auth.sh` then restart the authoritative server, or stop the lab.

#### Exercise 7: the records as code

Run the OpenTofu example above (`tofu init`, `tofu apply`, `tofu output -raw dnsmasq_records > records.conf`), then start a third `dnsmasq` that serves it, and ask it:

```bash
cat > tofu-auth.conf <<EOF
port=5302
listen-address=127.0.0.1
bind-interfaces
no-resolv
no-hosts
pid-file=$PWD/tofu.pid
log-facility=$PWD/tofu.log
auth-server=ns1.example.test,127.0.0.1
auth-zone=example.test,192.0.2.0/24
auth-ttl=30
auth-soa=1,hostmaster.example.test,1200,120,604800
conf-file=$PWD/records.conf
EOF
dnsmasq -C tofu-auth.conf
dig +noall +answer @127.0.0.1 -p 5302 www.example.test
dig +noall +answer @127.0.0.1 -p 5302 blog.example.test
./stop-dns.sh tofu-auth
```

On 2026-10-22, `www` returned `192.0.2.10` and `blog` returned the CNAME to `www.example.test.` followed by that address. Edit a value in `main.tf`, run `tofu plan`, and read the one-line difference before you apply. **Undo:** `tofu destroy -auto-approve` and delete the folder.

## A DNS troubleshooting flow

When "the site is down", work from the outside in and stop at the first failure. Each step names one tool.

```text
1. Does the name resolve at all?                 dig +short NAME @1.1.1.1
     no (empty / NXDOMAIN / SERVFAIL)  --> go to 2
     yes, an address                    --> go to 5
2. Who is supposed to answer?                    dig NS DOMAIN @1.1.1.1    and compare with the registrar's nameserver setting
     nameservers differ from what you set        --> the delegation has not changed, or you edited the wrong DNS host
3. Do those servers answer, and are they sure?   dig NAME @THE_NAMESERVER +norecurse   (look for the aa flag)
     SERVFAIL only on validating resolvers       --> suspect DNSSEC (a stale DS at the registrar)
     NXDOMAIN from the authority                 --> the record does not exist there (typo, wrong zone, wrong name)
4. Is it only your cache or your resolver?       dig NAME @1.1.1.1  versus  dig NAME @9.9.9.9  versus your own resolver
     the authority is right, a cache is wrong    --> wait the TTL; flush your own OS cache; do not "fix" the record
5. Is it the right address?                      compare with your server's address
     a Cloudflare address while you expect yours --> the record is proxied; that is normal
     a different address entirely                 --> a stale record, a second A record, or a hijack: check the zone
6. DNS is fine: the problem is the next step     TCP (curl exit 28 or 7), TLS (curl exit 60, Cloudflare 525 / 526), HTTP (4xx / 5xx)
```

Symptoms worth recognizing:

| Symptom | Likely cause |
|---|---|
| Works for you, not for a colleague | Different caches or resolvers: ask the authority directly |
| Fine from the office, `NXDOMAIN` at home | Split DNS (an internal view differs from the public one) |
| `DNS_PROBE_FINISHED_NXDOMAIN` right after moving to Cloudflare | The record was not recreated at the new DNS host (the quick scan is not guaranteed to find everything) |
| Everything broke when nameservers changed | DNSSEC was left on at the registrar |
| Redirect loop (`ERR_TOO_MANY_REDIRECTS`) | Flexible mode with an origin that redirects HTTP to HTTPS |
| Cloudflare error 525 or 526 | Origin TLS fails: no certificate (525), or Full (strict) does not accept it (526) |
| Email bounces after you moved DNS | The MX, SPF, DKIM and DMARC records did not come across |

## DNS as a trust boundary

Everything that decides where visitors, mail and certificate checks go is written in DNS. Whoever can edit those records, or fool the resolvers that read them, owns the name. A **trust boundary** is a line where data or control passes between parties that do not trust each other equally; DNS has several, and each is a place to ask "who may change this, and how would I know?"

The mapping below uses the STRIDE letters from [Threat model](Threat-Model.md). Likelihood and impact are my own estimates (est.) for a small personal site, not measurements.

| Threat | What happens | STRIDE | Likelihood / impact (est.) | Mitigation | How you would detect it |
|---|---|---|---|---|---|
| **Registrar account takeover** | An attacker gets into your registrar login (phishing, password reuse, a hijacked email) and changes nameservers or transfers the name away | Spoofing, Elevation of privilege | Medium / Severe: they own the name | Unique password, **two-factor authentication** (an authenticator app or a hardware key), a protected email account, **registrar lock** (the EPP statuses `clientTransferProhibited`, `clientUpdateProhibited` and `clientDeleteProhibited` of [RFC 5731](https://www.rfc-editor.org/rfc/rfc5731) block transfers, updates and deletes until you lift them) | An unexpected email from the registrar; a nameserver check on a schedule |
| **DNS host account takeover** | The same, at Cloudflare or whoever hosts the zone: records changed to point at an attacker | Spoofing, Tampering | Medium / Severe | Two-factor authentication; least-privilege API tokens; no shared logins; audit logs | Change notifications; read the zone's audit log; compare records against your code |
| **Dangling record / subdomain takeover** | A record points at a cloud or SaaS resource you deleted; an attacker claims the same name there and serves content on your subdomain | Spoofing | Medium / Moderate to severe: cookies and trust attach to your domain | Delete records **before** the thing they point to; inventory subdomains; avoid wildcards you do not need | Routinely resolve every record and flag targets that return `NXDOMAIN` (Exercise 6) |
| **Stale delegation** | An `NS` record delegates a subdomain to a provider you no longer use | Spoofing | Low / Severe for that subdomain | Review NS records when you leave a provider | Check every `NS` record in the zone against what you run |
| **Cache poisoning** (concept) | An attacker tricks a resolver into storing a forged answer, so its users go to the wrong address | Spoofing, Tampering | Low today / Severe | **DNSSEC** (validating resolvers reject forged data), randomized source ports and query IDs in modern resolvers, HTTPS with certificate checks as a second layer | Hard from your side; a validating resolver reports failures; certificate warnings |
| **On-path interference** | A hostile network changes DNS answers before they reach the visitor | Tampering | Medium on untrusted networks / Moderate | HTTPS with a valid certificate (a forged address cannot present your certificate); encrypted resolver transport is a separate topic this page does not cover | Certificate errors |
| **Unwanted certificate issuance** | A certificate authority issues a certificate for your name to someone else | Spoofing | Low / Severe | **CAA** records limiting which CAs may issue ([RFC 8659](https://www.rfc-editor.org/rfc/rfc8659)); monitoring public certificate logs (est.: a topic this page names but does not teach) | CAA only helps the CAs that check it; watch for unknown certificates |
| **Origin address leaks and direct access** | The proxy is bypassed because the server's address is known | Elevation of privilege | High / Moderate to severe | The origin firewall allows only the proxy's ranges, and Authenticated Origin Pulls on top | The `curl --connect-timeout` test in this page, run on a schedule |
| **Lapsed registration** | The domain expires; someone else registers it and receives your traffic and mail | Spoofing | Medium (it happens to real companies) / Severe | Auto-renew with a card that will not expire; a calendar reminder; long registration | A renewal-failure email; a check of the expiry date |
| **Hijack of mail** | Forged mail is sent as your domain | Spoofing | High / Moderate | SPF, DKIM and DMARC at reject, null MX for a domain that sends nothing | DMARC reports (the `rua` address) |

Two points worth saying plainly. First, almost every mitigation in the table is **account hygiene** and **cleaning up after yourself**, not clever technology: the most common DNS failures are a stolen login and a record nobody deleted. Second, DNSSEC and CAA reduce specific risks; neither helps if an attacker already holds your DNS login, because they will simply publish valid records.

## Build, break, detect, evade, defend

A small loop in the local lab (nothing here touches a real domain).

**Build.** The `example.test` zone with an authoritative server and a resolver, from Exercise 3, plus the `www` and `old` records.

**Break.** Make three mistakes on purpose: change `www` at the authority and read the stale answer from the cache (Exercise 5); add the dangling `old` alias (Exercise 6); and publish a second `A` record for `www` pointing at a different documentation address, as an attacker with zone access would:

```bash
cd ~/dns-lab
./stop-dns.sh auth; sleep 1
./make-auth.sh
echo 'host-record=www.example.test,198.51.100.66' >> auth.conf
dnsmasq -C auth.conf; sleep 1
dig +short @127.0.0.1 -p 5300 www.example.test
```

**Detect.** The last command returns **two** addresses for `www` (`192.0.2.10` and `198.51.100.66`). Detection is a comparison between what the zone says and what you meant it to say. Write the expected records in a file and diff the live answers against them:

```bash
printf '192.0.2.10\n' > expected-www.txt
dig +short @127.0.0.1 -p 5300 www.example.test | sort | diff - expected-www.txt && echo "matches" || echo "DRIFT: the live zone differs from what you intended"
```

```powershell
# est.: nslookup output is free text and differs by version, so on Windows run the Bash check inside WSL:
wsl -e bash -c 'cd ~/dns-lab && dig +short @127.0.0.1 -p 5300 www.example.test | sort | diff - expected-www.txt && echo matches || echo DRIFT'
```

(Run from cron or a pipeline, the same check is the real defense: infrastructure-as-code makes this a one-line plan, because the code is the intended state and the provider shows the drift. The OpenTofu example above is that idea at lab scale.) For the cloud, also read the DNS host's audit log, and enable change notifications on the registrar and the DNS host.

**Evade, in words only.** An attacker who has a stolen login does not need to break anything: they add one record that looks like many legitimate ones (a verification `TXT`, a plausible `mail` host, an `A` for a name nobody visits often), or make a change in the hour a team is busy and the alert is noise. They prefer a *new, quiet* name over changing `www`, which gets looked at. Another quiet route is a long-lived record on a name you forgot you had. This lesson shows no working attack against anyone's system and none is needed: defenders catch it by keeping an inventory and diffing against it, not by watching only the names that matter.

**Defend.** In order of value for a personal site:

- Two-factor authentication on the registrar and DNS host accounts, with a recovery path you have tested.
- Registrar lock on, and auto-renew on a card that will not expire.
- Least-privilege tokens for any automation (the [APIs and tokens](APIs-and-Tokens-From-Zero.md#scopes-and-least-privilege) rules apply to the Cloudflare token).
- DNS as code, with the code reviewed ([Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md)): then a stray record is a diff, not a surprise.
- CAA records; DNSSEC where your registrar and DNS host both support it; SPF, DKIM and DMARC.
- Delete records before the resource they point at; check for dangling ones on a schedule.
- Origin firewall to the proxy's ranges only; Full (strict); patched software.

### Flip the board

You built the zone and the check. Now do the other two jobs.

**The reviewer.** You are handed this zone snippet and asked "is it safe to publish?" Find at least five problems without running it. (Documentation names and addresses.)

```text
example.com.        3600  IN  A      203.0.113.5
*.example.com.      3600  IN  A      203.0.113.5
www                 3600  IN  CNAME  example.com.
mail                300   IN  A      203.0.113.5
example.com.        3600  IN  MX     10 mail.example.com.
example.com.        3600  IN  TXT    "v=spf1 +all"
shop                300   IN  CNAME  example-shop.hosting.example.net.
dev                 300   IN  A      198.51.100.77
```

<details>
<summary>What to find</summary>

1. `v=spf1 +all` authorizes **every server on the internet** to send mail as the domain. It should name the real senders and end in `-all`.
2. There is no DMARC record at all, and no DKIM key is published, so forged mail is not rejected.
3. The wildcard `*.example.com` answers for every name that does not exist, including typos and names an attacker can invent; it also makes dangling records harder to notice. Remove it unless you need it.
4. `shop` is a CNAME to a third-party hosting name. If the shop is ever canceled and this line stays, someone else can claim that hosting name: a subdomain takeover.
5. `dev` points at a separate address that is probably an unpatched test server, on a record that is not proxied, so it exposes an address and a service. Many forgotten `dev` names start as one record.
6. The `mail` record and the apex share one address. If that is also the web server, the "hidden" origin address is not hidden: a gray-cloud `mail` record gives it away.
7. There is no CAA record, so any certificate authority may issue certificates for the name.
8. TTLs of 3600 on the apex and 300 on others: not a flaw by itself, but one or the other will surprise you in a migration. Decide on purpose.

</details>

**The scanner.** You are given only this output from an unknown domain and must say what you can without guessing:

```text
$ dig +short secure.example.net
203.0.113.40
$ dig +short example.net NS
ns1.example.net.
ns2.example.net.
$ dig +short _dmarc.example.net TXT
(nothing)
$ dig +short staging.example.net
(nothing, status NXDOMAIN)
```

What can you tell? (An address and two nameservers inside the domain itself, which means glue records exist; no DMARC, so mail forgery is not discouraged; an authoritative `NXDOMAIN` for `staging`, which tells you the name is not in use today but says nothing about whether it was, or whether a delegated sub-zone exists elsewhere. You cannot tell what runs on the address, whether the server is patched, or whether DNSSEC is on until you ask for `DNSKEY` or `DS`. A defender reads the same output the same way and asks "which of these did I mean to publish?")

Defenders who can read a zone as an attacker does catch the dangling record before the attacker does; attackers who can read a zone know which names to try. Do both, in that order.

## Checkpoint

- Name the four parties in "I own example.com" and say which one you change to move the website, and which to move the email.
- What does changing nameservers at the registrar change, and what does it leave alone?
- A TTL is 3,600 and you change the record now. What do you tell your customers, and what should you have done yesterday?
- Why can the bare `example.com` not hold a plain CNAME, and what does CNAME flattening do about it?
- What are the three things SPF, DKIM and DMARC each say, in one sentence apiece?
- In Flexible mode, which connection is encrypted and which is not? Why does the visitor not notice?
- Your origin is firewalled to Cloudflare's ranges. Name one thing that can still reach it that you did not intend, and one more layer that closes it.
- A record points at a droplet you destroyed last month. What is the risk and what do you do first?

Answers are in the sections above. (For the fourth: the apex must carry SOA and NS, and a CNAME cannot coexist with other record types at the same name; flattening makes the DNS host resolve the alias and return the final address.)

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| Records added in Cloudflare do nothing | The registrar still delegates to the old nameservers | `dig NS yourdomain @1.1.1.1` against the two Cloudflare assigned |
| "It works for me" but not for others | Caches | Ask the authority directly; wait the TTL |
| Site down after enabling the proxy | Origin firewall blocks Cloudflare's ranges, or the origin is not listening on 443 | The firewall's source list; `curl` the origin from the server itself |
| Error 526 after Full (strict) | The origin certificate is missing, expired, for another name, or from an untrusted CA | The certificate's dates and names |
| Padlock shows, but passwords travel in clear text | Flexible mode | Switch to Full (strict) after installing the origin certificate |
| The origin address appears in a lookup | A gray-cloud record, a mail record, or old DNS history | Every record in the zone that holds that address |
| Domain stopped working a year later | Auto-renew failed (expired card) | The renewal email and the registrar's expiry date |
| Email lands in spam after moving DNS | SPF/DKIM/DMARC records were not copied | The three TXT records |

## Claims register

All read-only requests, retrieved **2026-10-22** unless stated. Cloudflare documentation pages are under `developers.cloudflare.com`.

| Claim | Source | Status |
|---|---|---|
| Encryption modes: what Off, Flexible, Full and Full (strict) do; quoted warnings; error 525 and 526; Automatic SSL/TLS never moves to a less secure mode; Authenticated Origin Pulls does not work in Off or Flexible | `/ssl/origin-configuration/ssl-modes/` and its `off`, `flexible`, `full`, `full-strict` pages | Read |
| Proxy status: only A, AAAA and CNAME can be proxied; proxied records answer with Cloudflare anycast addresses; the proxied TTL is Auto (300 s) and not editable; DNS-only exposes the origin address | `/dns/proxy-status/` and `/dns/manage-dns-records/reference/ttl/` (unproxied TTL 60 s to 1 day on non-Enterprise) | Read |
| Origin CA certificates: free on all plans; created in the dashboard; the key is shown once; trusted only by Cloudflare; no expiry notifications; revocation cannot be undone | `/ssl/origin-configuration/origin-ca/` | Read |
| Authenticated Origin Pulls: mTLS from Cloudflare; Free through Enterprise; not compatible with Cloudflare Tunnel | `/ssl/origin-configuration/authenticated-origin-pull/` | Read |
| Cloudflare IP ranges: published lists; block other sources at the origin; ranges change rarely and are announced in advance; origin may be found by DNS history or mail configuration | `/fundamentals/concepts/cloudflare-ip-addresses/`, [ips-v4](https://www.cloudflare.com/ips-v4), [ips-v6](https://www.cloudflare.com/ips-v6) | Read. The current lists were fetched (15 IPv4 and 7 IPv6 ranges that day); the page deliberately does not copy them |
| Full (primary) setup is the only setup on Free or Pro; steps to change nameservers; DNSSEC must be disabled first; "up to 24 hours" to become Active; standard nameservers `<name>.ns.cloudflare.com`; static IPs of nameservers | `/dns/zone-setups/full-setup/setup/`, `/dns/nameservers/`, `/dns/dnssec/` | Read |
| CNAME flattening lets a CNAME exist at the apex; a dangling target yields an empty answer | `/dns/additional-options/cname-flattening/` | Read |
| Record types supported (A, AAAA, CNAME, MX, TXT, CAA, SRV, SOA, NS, DS, DNSKEY and others); SOA created automatically on Cloudflare | `/dns/manage-dns-records/reference/dns-record-types/` | Read |
| Cloudflare Registrar: at cost, no markup; auto-renew by default; one-click DNSSEC; requires Cloudflare DNS; transfer needs 60 days since registration or last transfer, 60-day lock after registrant changes, usually up to 10 days | `/registrar/` and `/registrar/get-started/transfer-domain-to-cloudflare/` | Read. No price was read, so none is given |
| The Free plan is $0 a month and lists DNS, DDoS protection, CDN and Universal SSL; Free-plan WAF limits | [cloudflare.com/plans](https://www.cloudflare.com/plans/) | Read for price and the feature rows; WAF limits **not verified** |
| Cloudflare provider `cloudflare/cloudflare`, newest 5.x release 5.28.1; resource names `cloudflare_zone`, `cloudflare_dns_record`, `cloudflare_zone_setting` (setting id `ssl`, values off, flexible, full, strict), `cloudflare_zone_dnssec`; provider argument `api_token` | `registry.opentofu.org/v1/providers/cloudflare/cloudflare/versions`; the provider's documentation in [github.com/cloudflare/terraform-provider-cloudflare](https://github.com/cloudflare/terraform-provider-cloudflare) (`docs/`, main branch) | Read; the Cloudflare configuration was **not** applied. 4.x naming is **est.** |
| DigitalOcean DNS management is free; firewalls allow up to 50 rules and 1,000 entries per Sources field; droplets billed per second, powered-off still billed | [DNS pricing](https://docs.digitalocean.com/products/networking/dns/details/pricing/), [firewall limits](https://docs.digitalocean.com/products/networking/firewalls/details/limits/), droplet pricing page | Read |
| `doctl` accepts several `address:` entries in one rule string | `doctl compute firewall create` reference shows single-address examples | **est.** |
| AWS Route 53: $0.50 per hosted zone per month for the first 25 zones | [aws.amazon.com/route53/pricing](https://aws.amazon.com/route53/pricing/) | Read; query and health-check pricing not totaled |
| `s-1vcpu-1gb` is $6 a month | [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json) | Read in this repository |
| About $0.20 a day for a forgotten droplet | $6 divided by 30 | est. (arithmetic) |
| RFC titles and the points cited: 1034, 1035, 1912, 2181, 2308, 2606, 2782, 4033, 4034, 4035, 5731, 5737, 7208 (ten-lookup limit), 7505 (null MX), 8499, 8555, 8659, 9364; DMARC in 9989, 9990, 9991 which obsolete 7489; DKIM in 6376 | [rfc-editor.org](https://www.rfc-editor.org/) | Titles, categories and the specific phrases quoted were found in the text; the surrounding summaries are mine. RFC 3849 was not read: **est.** |
| `Resolve-DnsName` has `-Server`, `-Type`, `-DnsOnly`, `-NoRecursion` and no port parameter; `nslookup` has a `set port` command | [Resolve-DnsName](https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname), [nslookup](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/nslookup) | Parameter and command names read; the `-port=` command-line form and every PowerShell command here are not run: **est.** |
| PHP 8.5.12 changelog fixes GHSA-w8hw-w9fx-j79w and GHSA-6wmf-4rv5-p3rp; the two advisories are titled "RCE via OOM corruption" and "RCE via stale global state" and rated Critical | [php.net ChangeLog-8](https://www.php.net/ChangeLog-8.php), [advisory 1](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w), [advisory 2](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp) | Read the titles, ratings and changelog; the exploitation conditions were not analyzed. The changelog dates the release 22 Oct 2026 and the release data 21 Oct 2026 |
| The `example.com` outputs (nameservers, TTLs, SPF, null MX, DMARC, `ad` flag, referrals) | One query each to a root server, a `com` server, the zone's server, and 1.1.1.1, 2026-10-22 | Observed; they change |
| The local lab output | Run on Linux with `dnsmasq` 2.91, `dig` 9.20.29, OpenTofu 1.12.6, 2026-10-22 | Observed |
| That the maintainer runs Cloudflare for his own domains | The maintainer's statement | Not checkable here |

Not verified, plainly: every PowerShell command; macOS; Windows and WSL behavior of the lab; the Cloudflare dashboard steps and button names; the droplet, firewall, nginx and certificate steps; the Cloudflare OpenTofu configuration (never applied); any registrar's terms, prices or refund policy; Cloudflare WAF limits on the Free plan; reverse-DNS editing on DigitalOcean; whether any WAF rule blocks the October 2026 PHP vulnerabilities.

Next: [Droplet hardening](Droplet-Hardening.md), core step 14 on the [Reading order](Reading-Order.md) page.

In this track, W4 is [WordPress at scale: CDN, WAF and CI](WordPress-at-Scale-CDN-WAF-and-CI.md) once it is merged.
