# Email security: DNS records, email gateways with Microsoft 365, API-driven cloud email security, and whether to run your own server

Side page to the start-from-zero pages. Read it after [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md), whose short section on email records this page goes deeper on, and beside [Threats in plain words](Threats-in-Plain-Words.md), whose phishing entry it expands. It answers four questions in order: how does a message actually travel and what do the DNS records do to it; what are the two kinds of email security product (a gateway in front of Microsoft 365, and a product that connects by API) and what can each see; what do the attacks seen in email look like and how do you triage one; and should you run your own mail server. Next: [Reading order](Reading-Order.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the free local lab was run once on Linux; the vendor and standards facts were read from primary pages; the cloud parts were not applied.** On **2026-10-22** the author ran every `local/` script in [`labs/email-security`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/tree/main/labs/email-security) on Linux with Python 3.13.5, OpenSSL and `dnsmasq` 2.91, and pasted trimmed output. The DKIM verifier was cross-checked against the `dkimpy` library 1.1.8 (installed in a private virtual environment) on the five signed messages, and agreed on all five. The OpenTofu in `labs/email-security/cloud` was **validated and planned with every flag off and with the flags on and a placeholder token (no API call, nothing applied)**; it has **never created a resource**. Standards were read from rfc-editor.org, vendor facts from the vendors' own public pages, all on **2026-10-22**; each is in the [claims register](#claims-register). **Not run:** every PowerShell command (no Windows machine; written from Microsoft's documentation and marked **est.**), every Exchange Online and Microsoft 365 step, every Mail-in-a-Box step, anything at Proton, Tuta, Check Point or Proofpoint, and anything behind a vendor login. Output varies with your versions and the date.

> **Prerequisites.** [How a web request works](How-a-Web-Request-Works.md) (DNS) and the DNS lesson above, especially its [email records section](DNS-Cloudflare-and-Hosting-Your-Own-Website.md#email-records-at-concept-level) and its local `dnsmasq` lab. A terminal. The free path needs `python3`, `openssl` and, for one exercise, `dnsmasq` and `dig` (Linux or WSL 2). No account, no money. The reading and the exercises are free and always will be. About four hours for the reading and the lab (est.).

## What you will be able to do

- Follow one message from a mail client to a mailbox (MUA, MSA, MTA, MX lookup, delivery) and say which parts of it an attacker controls: the envelope, the headers, the display name.
- Read a message's headers, including `Received` and `Authentication-Results`, and say which lines to trust and which were written by the sender.
- Say what SPF, DKIM, DMARC, MTA-STS and TLS-RPT each do and each fail at, including alignment, the SPF 10-lookup limit, key selectors and rotation, and why forwarding and mailing lists break things.
- Roll out DMARC safely: monitor, fix senders, quarantine, reject, with reports.
- Explain the two product models side by side (position in the mail flow, before or after delivery, MX dependency, bypass risks, coverage beyond email, permissions, failure modes, who can see mail) and the trust boundary a broad OAuth application creates.
- Name the attacks (phishing, business email compromise, spoofing, look-alike domains, display-name tricks, malicious links and attachments, QR codes, OAuth consent phishing, account takeover, thread hijacking, vendor email compromise) with a detection signal and a control for each, and triage a reported phish.
- Say honestly whether to run your own mail server, what Mail-in-a-Box teaches and where it stops, and what to choose instead.

## Why this page exists

The maintainer asked for it on 2026-10-22, in two parts. The first part, in his words:

> "We can add another section related to DNS with Email for Email Security as there are two concepts: Email Gateways and how they work in like say a Proofpoint and Office365 setup, and then the additional API driven ones that can potentially cover even more than Email, such as Avanan, now owned by Checkpoint. It is relatively inexpensive that you as an end user could actually afford it as part of an office365 lab, however they will only sell to business entities, and I have it going through my LLC I have for content and research such as this project. Because it does cover cloud security and can touch a bit on phishing and the various attacks we spot in email."

That is his experience, not a vendor's published policy; the [claims register](#claims-register) says what the vendor pages did and did not say. The second part came later the same day and became the last big section:

> "Yes you can self host email servers, I recommend projects such as mailinabox.email, that's actually how I learned all this about emails and email relays ... friends don't let friends run their own email server ... I even deployed it for businesses in the past and ran my own email for a decade, but running your own email server is a real commitment that in my opinion is worth learning to get intimate knowledge, but not something I would recommend relying on unless you want to deal with why you weren't getting emails for days and had a really important email not get delivered."

I name no employer here, and the page does not name his company. No vendor console screenshots are used: where one would help, the page says "Screenshot to take yourself" and describes what to look for.

### What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| The three email DNS records, null MX, the SPF lookup limit in one sentence | [DNS lesson](DNS-Cloudflare-and-Hosting-Your-Own-Website.md#email-records-at-concept-level) | How mail flows, alignment, selectors, policy modes, reports, forwarding, MTA-STS, a safe rollout, and a lab that evaluates real messages |
| Phishing as a threat | [Threats in plain words](Threats-in-Plain-Words.md#phishing) | The email-specific attack catalog and a triage workflow |
| Email DLP | [Cross-tenant data flows](Cross-Tenant-Data-Governance-Retention-and-DLP.md#where-dlp-looks) | Where a DLP engine sits in the mail path, for each product model |
| OAuth consent | [Enterprise identity](Enterprise-Identity-SSO-SAML-OIDC.md#oauth-20-delegated-access-not-sign-in) | The attack (consent phishing) and the broad grant an API-driven product asks for |
| Logs and detection | [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) | Which mail and sign-in logs answer a phishing report |
| Secrets | [Secrets from day one](Secrets-From-Day-One.md) | Where an API credential for a mail product must and must not live |

## Cost, honestly

You choose what you can afford. This lesson sets no ceiling. It gives honest numbers and realistic expectations, and it does not rate anyone by what they spend.

| Item | What it costs | Source |
|---|---|---|
| Reading this page and the whole free local lab | $0. It runs on your own computer, touches no network beyond loopback, and is complete without any account. | This page |
| A Microsoft 365 business trial (optional) | A 30-day free trial of the business plans, per Microsoft's page; at the end the subscription **renews to an annual term by default** unless you turn off recurring billing. Whether a payment card is asked for at sign-up I did **not** read. After the trial I read no price. | Microsoft Learn, retrieved 2026-10-22 |
| An API-driven email security product | I read **no price**: the vendor's plans page shows "Get a Quote". The maintainer's experience is that it is sold to businesses only. | Check Point plans page, retrieved 2026-10-22 |
| A Mail-in-a-Box learning box (optional) | A $6 a month `s-1vcpu-1gb` droplet at list price ([`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json), retrieved 2026-10-21), billed while it exists even if powered off, plus a domain name (a yearly fee I did not read). The project's own guide estimates about $12 a month for the whole arrangement. | Repository files; Mail-in-a-Box guide, retrieved 2026-10-22 |

The full cost box, piece table and teardown for the two optional own-account paths are in [Build it piece by piece](#build-it-piece-by-piece-and-what-it-costs), after the theory.

## How a message travels

An email address has a local part and a domain: `alice@example.com`. Five roles move a message, and learning their names makes every later section easier.

| Role | Short name | What it does | Port |
|---|---|---|---|
| Mail user agent | MUA | The program you read mail in (a phone app, a webmail page) | none |
| Mail submission agent | MSA | Takes a message from an authenticated user to start sending | 587 or 465 |
| Mail transfer agent | MTA | A server that relays a message to the next server, speaking SMTP | 25 between servers |
| Mail delivery agent | MDA | Puts the message into the recipient's mailbox | none |
| Mail exchanger | MX record | The DNS record that names the MTA that accepts mail for a domain | n/a |

SMTP (Simple Mail Transfer Protocol) is defined in [RFC 5321](https://www.rfc-editor.org/rfc/rfc5321). The trip, in order:

1. Alice's MUA submits the message to her provider's MSA after she logs in.
2. Her provider's MTA looks up the **MX record** of the recipient's domain in DNS (a lower preference number is tried first) and connects to that server on port 25.
3. The two MTAs speak SMTP. The sender states the **envelope**: `MAIL FROM` (the envelope sender, where bounces go, also called Return-Path) and `RCPT TO` (the recipients).
4. It then sends the **message**: headers and body, in the format of [RFC 5322](https://www.rfc-editor.org/rfc/rfc5322). The `From:` header is the one a person sees.
5. The receiving MTA may pass the message through filters, then hand it to the MDA. Each hop adds a `Received:` header on top.

The central fact for the rest of this page: **the envelope sender and the `From:` header are different fields, and SMTP by itself checks neither.** Anyone who can open a connection can write any `From:` they like. [RFC 7208](https://www.rfc-editor.org/rfc/rfc7208) says the same in its first paragraph: existing protocols "place no restriction on what a sending host can use as the 'MAIL FROM' of a message". SPF, DKIM and DMARC exist to put a check on top.

### Exercise 1: watch the envelope and the headers disagree

**Predict.** If the server is told the sender is `attacker@random-host.test` but the message says `From: ceo@example.test`, which one does the recipient's mail program show?

**Do.** Set up the lab folder once (it is private to you, because later scripts write keys into it):

```bash
umask 077
LAB="${XDG_RUNTIME_DIR:-$HOME/.cache}/email-lab"
mkdir -p -m 700 "$LAB" && cd "$LAB" || exit 1
[ "$(stat -c %u .)" = "$(id -u)" ] && [ -z "$(find . -maxdepth 0 -perm /022)" ] || { echo "$LAB is not private to you; stop" >&2; exit 1; }
# Copy labs/email-security/local from a checkout of this repository into ./local, then:
python3 local/mkmail.py "$LAB" && ls msgs | head -3
```

Then, in one terminal, start the loopback receiver (it takes one message and exits), and in another send to it:

```bash
cd "$LAB" && python3 local/smtpsink.py got.eml 2525
```

```bash
cd "$LAB" && python3 local/smtpsend.py 2525 && sed -n 1,3p got.eml
```

```powershell
# est.: not run. Same scripts; on Windows run the Bash blocks inside WSL 2, or use python instead of python3.
$Lab = Join-Path $env:LOCALAPPDATA "email-lab"; New-Item -ItemType Directory -Force $Lab | Out-Null; Set-Location $Lab
python local\mkmail.py $Lab
```

**Check.** On 2026-10-22 the receiver's transcript showed the envelope and, separately, the message:

```text
C: mail from:<attacker@random-host.test>
S: 250 2.1.0 ok
C: rcpt to:<bob@receiver.test>
S: 250 2.1.0 ok
C: data
...
From: "CEO" <ceo@example.test>
```

The server was told `attacker@random-host.test`; the message says `ceo@example.test`; nothing in SMTP objected. Your mail program shows the `From:` header.

**Undo.** The receiver exits by itself after one message. Delete `got.eml` if you like. Everything stayed on `127.0.0.1`.

### Reading headers

Open `msgs/05-lookalike-domain.eml` in a text editor (never in a mail program that renders it). Four header families matter:

| Header | Written by | Trust it? |
|---|---|---|
| `From:`, `To:`, `Subject:`, `Reply-To:` | The sender | No: all of it is claimed, not verified |
| `Return-Path:` | The receiving server, copied from the envelope `MAIL FROM` | It records the envelope; the sender chose the value |
| `Received:` | Each server that handled the message, newest on top | A hop is only as honest as the server that wrote it. Lines below the first server **you** trust may have been invented by the sender |
| `Authentication-Results:` ([RFC 8601](https://www.rfc-editor.org/rfc/rfc8601)) | The receiving server, recording what SPF, DKIM and DMARC said | Only the one stamped by **your own** server's identifier (the part before the first `;`), and the topmost. A sender can add a fake one lower down |

**Do.** Look at the forged message and count:

```bash
cd "$LAB" && grep -n -i -E '^(Authentication-Results|Received|Return-Path):' msgs/04-forged-ceo.eml
```

**Check.** Two `Authentication-Results` lines: the top one, from `mx.receiver.test`, says `spf=fail ... dmarc=fail`. The lower one, which starts `example.test;` and says everything passed, came with the message from the attacker. RFC 8601 describes receivers removing or ignoring such headers from outside their own domain; a person reading headers has to do the same.

## DNS records: what each does and what it fails at

All of these are `TXT` records except `MX`. The DNS lesson explains zones, TTL and delegation; this section assumes them.

### MX: where mail for a domain goes

`example.com. IN MX 10 mail.example.com.` The number is a preference; lower is tried first. A domain that accepts no mail publishes a **null MX** (`MX 0 .`, [RFC 7505](https://www.rfc-editor.org/rfc/rfc7505)). **The MX record is also the switch that decides which product sees your mail first**: point it at a gateway and the gateway is first; leave it at Microsoft 365 and Microsoft is first. Keep that in mind for the product sections.

### SPF: which servers may send for a domain

SPF ([RFC 7208](https://www.rfc-editor.org/rfc/rfc7208)) is a list, published at the domain, of the machines allowed to use that domain in the **envelope** sender (and the HELO name). The receiver takes the connecting IP address and the envelope domain and asks the list.

```text
example.test. IN TXT "v=spf1 ip4:192.0.2.25 include:_spf.bulkmailer.test -all"
```

| Part | Meaning |
|---|---|
| `ip4:192.0.2.25` | This address may send |
| `include:_spf.bulkmailer.test` | Whatever that other domain's SPF record allows may send too (this is how you authorize a third-party sender) |
| `-all` | Anything else: fail. `~all` is softfail (probably not authorized), `?all` neutral, `+all` allows the whole internet and defeats the point |

What SPF fails at:

- **It checks the envelope, not the `From:` the reader sees.** A message can pass SPF for `bounce@bulkmailer.test` and show `From: news@example.test`. DMARC alignment (below) is what connects them.
- **It breaks on forwarding.** A forwarder's address is not on your list, so the forwarded copy fails SPF. DKIM usually survives forwarding; SPF does not.
- **The 10-lookup limit.** The terms `include`, `a`, `mx`, `ptr`, `exists` and `redirect` each cost a DNS query, and an implementation must stop at 10 and return `permerror` ([RFC 7208, section 4.6.4](https://www.rfc-editor.org/rfc/rfc7208#section-4.6.4)); it also recommends stopping at two "void" lookups (queries that return nothing). Add one more SaaS `include:` than your budget allows and the whole record stops working, usually weeks later and silently. Microsoft's SPF page says the same: validation fails "if the check requires too many DNS lookups".
- **Two SPF records at one name is an error** (`permerror`), a common mistake when a second service says "add this record".
- It says nothing about content or about whether the sender is a good actor. A criminal can publish a valid SPF record for their own look-alike domain, and it will pass.

### DKIM: a signature the sender's domain vouches for

DKIM ([RFC 6376](https://www.rfc-editor.org/rfc/rfc6376)) has the sending server sign selected headers and a hash of the body. The signature goes in a `DKIM-Signature:` header and names the signing domain (`d=`) and a **selector** (`s=`). The receiver fetches the public key from DNS at `selector._domainkey.domain` and verifies.

```text
s2026a._domainkey.example.test. IN TXT "v=DKIM1; k=rsa; p=<base64 public key>"
```

- **Selectors are what make rotation possible.** Publish a new selector, switch the signer to it, leave the old key published for a while so mail in transit still verifies, then remove it. Microsoft 365 uses two selectors (`selector1` and `selector2`) published as CNAME records so that it can rotate for you; Microsoft's DKIM page says so.
- **Key size.** RFC 8301 requires signers to use RSA keys of at least 1024 bits and says they should use at least 2048. Google's sender page says delivery to personal Gmail needs 1024 bits or more and recommends 2048. A TXT string is limited to 255 characters, so a 2048-bit key is published as several quoted strings in one record; the lab does exactly that.
- **A revoked key** is published with an empty `p=`.
- **The `From:` header must be among the signed headers** (RFC 6376, section 5.4). A signature that covers only, say, the subject proves nothing about who the message claims to be, so the lab verifier fails it; the test suite includes a forged message signed that way to prove DMARC does not pass.
- DKIM fails at **anything that changes the signed parts after signing**. A mailing list that adds a footer or a `[list]` tag in the subject breaks the signature (Exercise 4 shows the body hash failing).
- A valid DKIM signature from `d=bulkmailer.test` proves only that bulkmailer.test signed it. It does not tie the message to `From: news@example.test` unless the domains are aligned.

### DMARC: tying the visible From to SPF or DKIM, and saying what to do

DMARC adds two things. **Alignment:** a message passes only if SPF passes **and** the envelope domain aligns with the `From:` domain, or DKIM passes **and** `d=` aligns with the `From:` domain. **Policy and reports:** the domain owner says what receivers should do with failures and where to send reports.

```text
_dmarc.example.test. IN TXT "v=DMARC1; p=quarantine; sp=reject; rua=mailto:dmarc-reports@example.test; adkim=r; aspf=r"
```

| Tag | Meaning |
|---|---|
| `p` | Policy for the domain: `none` (monitor only), `quarantine` (treat as suspicious), `reject` |
| `sp` | Policy for subdomains (and `np` for subdomains that do not exist) |
| `adkim`, `aspf` | Alignment mode: `r` relaxed (same organizational domain) or `s` strict (exact match) |
| `rua` | Where to send **aggregate** reports (daily XML summaries: sources, counts, results) |
| `ruf` | Where to send **failure** reports about individual messages (privacy-sensitive; many receivers do not send them) |

**About the numbering.** The DNS lesson notes the DMARC specification changed. On 2026-10-22 rfc-editor.org lists [RFC 9989](https://www.rfc-editor.org/rfc/rfc9989) (DMARC, a Standards Track document dated May 2026, which obsoletes RFC 7489 and RFC 9091), [RFC 9990](https://www.rfc-editor.org/rfc/rfc9990) (aggregate reporting) and [RFC 9991](https://www.rfc-editor.org/rfc/rfc9991) (failure reporting). The older [RFC 7489](https://www.rfc-editor.org/rfc/rfc7489) was an Informational document. Differences that matter to you, as RFC 9989 states them in its Appendix C: the `pct` tag (apply the policy to a percentage of failing mail) is **removed** and replaced by a `t=y/n` test flag; `np` and `psd` were added; the organizational domain is found by a **DNS Tree Walk** instead of the Public Suffix List; and the `rf` and `ri` tags were dropped. **Not every receiver or vendor guide has caught up.** Microsoft's DMARC page, retrieved the same day, still documents `pct`. The lab's evaluator keeps one teaching simplification (the organizational domain is the last two labels) and says so.

What DMARC fails at:

- **It is not about whether the message is safe**, only whether the visible domain matches an authenticated one. A look-alike domain with its own perfect SPF, DKIM and DMARC passes (message 05 in the lab). DMARC protects *your* domain from being forged; it does nothing about `examp1e.test`.
- **Forwarding and mailing lists.** RFC 9989 says plainly that `p=reject` can break indirect mail flows such as alumni forwarders, role aliases and mailing lists, and that domains whose users post to mailing lists **should not** publish `p=reject`. Domains with `p=reject` must not rely on SPF alone and must DKIM-sign. A receiver, it adds, must not reject solely on the basis of `p=reject`; it uses that as one input. In practice many large receivers do honor it, so the interoperability cost is real.
- **ARC** ([RFC 8617](https://www.rfc-editor.org/rfc/rfc8617), Experimental) lets an intermediary that modifies a message seal the authentication results it saw, so a later receiver can choose to trust them; Microsoft's documentation tells you to add a modifying third-party service as a trusted ARC sealer if it supports sealing.

### MTA-STS and TLS-RPT: protecting the connection, not the message

SMTP between servers starts unencrypted and may be upgraded with `STARTTLS`, and an attacker on the path can strip the upgrade. **MTA-STS** ([RFC 8461](https://www.rfc-editor.org/rfc/rfc8461)) lets a domain say, in a policy file served over HTTPS at `https://mta-sts.<domain>/.well-known/mta-sts.txt` and flagged by a `TXT` record at `_mta-sts.<domain>`, which MX hosts are legitimate and that senders must use validated TLS (modes `testing`, `enforce` or `none`). **TLS-RPT** ([RFC 8460](https://www.rfc-editor.org/rfc/rfc8460)) is a `TXT` record at `_smtp._tls.<domain>` with a `rua=` address where senders report TLS failures to you. They protect mail in transit between servers. They do nothing about a forged `From:` and they do not encrypt mail at rest. Exchange Online enforces MTA-STS on mail it sends to protected domains, and supports inbound MTA-STS for domains it hosts, per Microsoft's page.

### Set up DMARC safely

The order matters, and the step that most people skip is the second.

| Step | Record | What you do | Move on when |
|---|---|---|---|
| 1. Monitor | `p=none` and `rua=` set | Publish the record. Collect aggregate reports into a mailbox you read. Change no behavior | At least a few weeks, long enough to see monthly senders (RFC 9989 suggests at least a month at `none` and a month at `quarantine` for domains with users who post to lists) |
| 2. Find and fix senders | `p=none` | For every source in the reports that is **yours** (the payroll system, the newsletter tool, the ticketing system): add it to SPF or, better, sign with DKIM using your domain so it aligns | Every legitimate source passes with an aligned identifier |
| 3. Quarantine | `p=quarantine` | Failing mail goes to spam. Watch reports and help-desk tickets. Keep `sp=` in step | A clean period with no legitimate mail landing in spam |
| 4. Reject | `p=reject` | Failing mail is refused. Keep reading reports; add `sp=reject` and consider a separate subdomain for bulk mail | You decide it is right for your users, knowing the list and forwarding caveat above |

Do it per domain, and publish records for domains and subdomains that send **no** mail too (`v=spf1 -all`, `p=reject`, null MX) so nobody can use them. Exercise 5 is the report-reading half of step 2.

## Two kinds of email security product

Everything below describes **positions**, not brands. Vendor facts come from each vendor's public pages and are marked with the date; the maintainer's own experience is attributed to him.

### Model one: a secure email gateway in front of Microsoft 365

A **secure email gateway (SEG)** is a service that receives your inbound mail, scans it, and forwards the clean mail on to your mailbox service. For Microsoft 365 the setup Microsoft documents in [Manage mail flow using a third-party cloud service with Exchange Online](https://learn.microsoft.com/en-us/exchange/mail-flow-best-practices/manage-mail-flow-using-third-party-cloud) (page last updated 2025-07-28, retrieved 2026-10-22) is:

1. **The MX record points at the gateway's service**, not at Microsoft 365. Microsoft's page says: "Your domain's MX record must point to your third-party service provider."
2. **The gateway delivers to Microsoft 365** at the host in your tenant's mail-routing record. The page's example is of the form `hubstream-mx.mail.protection.outlook.com` and tells you to check your actual value in the admin center.
3. **Lock Exchange Online down so only the gateway can deliver.** Microsoft's page says to create a Partner inbound connector using the gateway's TLS certificate name (preferred) or its sender IP addresses, and to set `RestrictDomainsToCertificate` or `RestrictDomainsToIPAddresses` to true, so that "any messages that are smart-host routed directly to Exchange Online will be rejected". **Without this step an attacker simply sends to Microsoft 365 directly and skips the gateway.** That bypass is the most common design flaw in this model.
4. **Enable Enhanced Filtering for Connectors** ("skip listing") on that connector. Without it, every message appears to come from the gateway's address, so Exchange Online's own spoof and impersonation detection and sender reputation lose the real origin. Microsoft's page calls it "highly recommended" and says that failing to do either it or a filtering bypass "inevitably results in misclassification".
5. **Keep SPF for outbound correct.** The page's example SPF for mail sent from Microsoft 365 is `v=spf1 include:spf.protection.outlook.com -all`; add the gateway only if outbound mail also flows through it.

What Microsoft 365 itself does after the gateway, from [Built-in security features for all cloud mailboxes](https://learn.microsoft.com/en-us/defender-office-365/eop-about) and the [Defender for Office 365 overview](https://learn.microsoft.com/en-us/defender-office-365/mdo-about) (retrieved 2026-10-22): Exchange Online Protection (EOP) runs connection filtering, anti-malware, anti-spam and anti-phishing (spoofing) on every cloud mailbox, on by default. **Defender for Office 365 Plan 1** adds Safe Attachments and Safe Links, impersonation protection, and real-time detections; **Plan 2** adds Threat Explorer, Automated Investigation and Response, attack simulation training and hunting. **Zero-hour auto purge (ZAP)** retroactively moves or quarantines messages already delivered when a later verdict changes; Microsoft's page says its search covers the last 48 hours of delivered mail. Which license includes which plan I did not total; Microsoft's overview lists Business Premium and E3 for Plan 1 and E5 for Plan 2, and notes Plan 2 features can be tried for 90 days.

Proofpoint is the gateway example the maintainer named. Its public product page (retrieved 2026-10-22) now describes "Core Email Protection" deployable "via API or inline" and lists SEG and API deployment options together. **Its step-by-step deployment documentation sits behind a login**: the documentation site redirected to a sign-in page when fetched, so this page states nothing from it, and Microsoft's documentation above is the public source for the Microsoft 365 side of any gateway.

### Model two: API-driven cloud email security

An **API-driven** product does not sit on the MX path. You authorize an application in your Microsoft 365 or Google Workspace tenant, and the product reads and acts on mail, files and messages through the platform's APIs. Check Point's documentation (retrieved 2026-10-22) describes its product, now named **Email Security (Harmony Email & Collaboration)** and formerly sold as **Avanan**, as "an API-based inline protection service". Check Point's press release dated 30 Aug 2021 announces its acquisition of Avanan; I did not read a separate completion notice, but Check Point's current product pages and documentation present the product as its own, and its documentation URLs still contain the old name.

What it connects to, per that vendor's documentation: mail on Microsoft Exchange Online and Gmail; file sharing on OneDrive, SharePoint, Google Drive, ShareFile, Dropbox and Box; messaging on Microsoft Teams and Slack; plus account-takeover detection from sign-in behavior. In Microsoft 365 it uses Microsoft Graph and the Office 365 Management APIs.

The vendor documents **three modes for email**, and this is the detail that breaks the simple "API means after delivery" story:

| Mode | How it works (vendor documentation) | Before or after delivery |
|---|---|---|
| Monitor only | A journal rule copies scoped mail to the vendor for scanning through APIs; creates events; manual or query-based quarantine afterwards | After |
| Detect and Remediate | Same collection; adds automated policy actions to quarantine or modify mail already delivered; the documented scan time is "10 seconds - 5 minutes" | After |
| Protect (Inline) | Exchange Online **mail flow rules and connectors** redirect mail to the vendor's cloud for scanning before it reaches the mailbox, then return it to the mail flow | Before |

So the products are converging. A gateway vendor sells an API option, and an API vendor ships an inline mode that uses connectors and transport rules, which are the same Exchange Online features a gateway uses, without moving the MX record. Check Point's own marketing page says "without changing MX records" for deployment and contrasts itself with "API-only email security that removes malicious messages after delivery". Proofpoint's page makes the matching claim from the other side. **Treat each side's comparison of the other as marketing**, and read what mode a product is actually deployed in.

The permissions are the second thing to read. Check Point's manual-integration page lists the Microsoft application permissions its product requests, including: read and write mail in all mailboxes, read and write all mailbox settings, read and write calendars, read all users' full profiles, read all groups and directory roles, read all audit log data, read activity data, and "send mail as any user". The page explains each use (for example, mailbox write to quarantine or restore mail, mailbox settings to read inbox rules for compromised-account detection, send-as to notify users). That is a broad grant, and it is the price of the model.

### The new trust boundary

With a gateway, your mail passes through a company you chose and you can see where it goes (the MX record). With an API product, **a vendor's application holds standing access to mailboxes, files and chat across your tenant.** That is a new trust boundary, and it is the same kind of grant an attacker tries to obtain with consent phishing (below).

| Concern | What to do |
|---|---|
| Who may consent | Only an administrator, for a small named set of vendors. Microsoft's Entra page recommends allowing user consent only for apps from verified publishers, and lets you restrict or disable it |
| Least privilege | Read the permission list (above) before consent; choose the vendor's reduced-permission or manual mode where the vendor offers one. Check Point's manual mode needs "less permissions" than automatic mode by its own words, and its automatic mode configures Exchange for you |
| Token and credential handling | The tenant grant lives in your tenant; any admin portal login or API key the product gives you is a secret: [Secrets from day one](Secrets-From-Day-One.md), single sign-on and MFA on the vendor console, no shared accounts |
| Audit | Log who granted consent, who changed connectors and mail flow rules, and what the app does. Review the tenant's app registrations on a schedule and remove ones you do not recognize |
| Exit | Know how to revoke the application's access and remove its connectors and rules. Test the removal before you need it, because mail that still routes through a removed vendor can bounce |
| Data location and privacy | Ask where scanned content is processed and kept, and what the vendor can see. I read no vendor's data-processing terms for this page: **not verified** |

### Decision table: the two models side by side

| Question | Gateway in front of Microsoft 365 | API-driven product |
|---|---|---|
| Position in the flow | First hop on the MX path | Inside the tenant, beside the mailbox |
| Before or after delivery | Before, for mail that arrives through it | After by default; **before** only in a vendor's inline mode, which re-routes mail with connectors and rules |
| Depends on the MX record | Yes: it is the whole mechanism | No for monitor and remediate modes |
| Bypass risk | Mail sent straight to the tenant skips it unless the connector lock-down is in place; also anything that never crosses the MX (internal mail) | Mail the API integration is not scoped to; accounts or workloads left out; an admin who disables the app or its rules |
| Sees internal and outbound mail | Only if outbound is routed through it; internal mail normally does not leave the tenant | Yes, by design |
| Coverage beyond email | Email only | Files and chat (Teams, SharePoint, OneDrive, Slack and others) and sign-in behavior, per the vendor |
| Permissions it holds | Delivers mail to you; holds no standing access to your mailboxes | Standing, broad application access to mail, files and directory data |
| Failure modes | Gateway outage queues or bounces your mail; stale connector IP lists; MX changes forgotten | Permissions revoked or consent expires and protection silently stops; scan lag while the user already clicked; a vendor-side compromise reaches your tenant |
| Who can see your mail | The gateway vendor sees mail in transit | The API vendor can read what its permissions allow, at rest, across the tenant |
| Typical cost shape | Per-user subscription plus your time; price not read | Per-user subscription, sold to businesses per the maintainer's experience; price not read |

Neither is "better". Many organizations run Microsoft's built-in layers, add one of the two, and accept the overlap. Exercise 7 lets you compute what each position can and cannot see.

## Attacks seen in email

Each row gives one detection signal and one control. The signals are what a person or a tool can look at; none is proof alone.

| Attack | What it is | Detection signal | Control |
|---|---|---|---|
| **Phishing** | A message that pretends to be someone you trust to get a secret or an action | Mismatch between link text and destination; urgency; new sender | Filtering, awareness training, a report button, phishing-resistant MFA ([why](Enterprise-Identity-SSO-SAML-OIDC.md#mfa-and-why-some-mfa-resists-phishing)) |
| **Business email compromise (BEC)** | A fraud request (wire, gift cards, changed bank details) from someone who looks like an executive or vendor, often with no link or attachment | Reply-To differs from From; first-time sender; out-of-pattern request | Out-of-band verification of payment changes; impersonation protection; DMARC on your own domain |
| **Spoofing of your domain** | Forged `From:` with your domain | `dmarc=fail` in Authentication-Results; a source unknown to you in DMARC reports | SPF, DKIM, DMARC at enforcement |
| **Look-alike (cousin) domain** | `examp1e.test` for `example.test`; passes its own authentication | New domain age, one character different; Reply-To elsewhere | Impersonation protection against your domain and key vendors; register obvious variants; verify out of band |
| **Display-name spoofing** | The name shows a trusted person or an address; the real address is unrelated | Display name contains an `@` address that differs from the real one | Show the full address in the client; policies that flag a known name from an external address |
| **Malicious link or attachment** | Credential-harvesting page, or a file that runs code (HTML, archive, disk image, macro document) | Link host not what the text says; double extension; risky file types | Link rewriting and time-of-click checks; attachment sandbox; block risky types; never open in your normal profile |
| **QR code phishing ("quishing")** | A QR image carries the link, hiding it from text scanners and moving the click to a personal phone | Image-only body, "scan to" language | Image and QR analysis in filtering; training; no scanning on an unmanaged phone for work logins |
| **OAuth consent phishing** | The lure asks you to "allow" an app. Granted, the app reads your mail with no password needed ([Microsoft's description](https://learn.microsoft.com/en-us/defender-office-365/detect-and-remediate-illicit-consent-grants)) | New app registrations; "Consent to application" events in the audit log | Restrict user consent to verified publishers; admin approval workflow; review app grants |
| **Account takeover and inbox rules** | A stolen login is used to read mail and add rules that hide replies or forward mail out | New inbox rules (forward to external, move to RSS or Notes folders), impossible-travel sign-ins, new forwarding | MFA; alert on new forwarding and rules; session revocation. Microsoft's compromised-account guidance lists suspicious inbox rules and forwarding |
| **Thread hijacking** | An attacker with a mailbox replies inside a real conversation, so the message fits | A reply from a known contact with a changed address, domain or bank detail | Verify changes out of band; detect the compromised account that supplied the thread |
| **Vendor email compromise** | A real supplier's mailbox is taken over and the attacker sends legitimate-looking invoices from the real domain | Passes every authentication check. Behavior is the signal: new bank details, unusual timing | Payment-change verification procedure; behavioral detection; vendor risk review |

The last two rows pass SPF, DKIM and DMARC. That is why authentication is necessary and not sufficient.

## Triage a reported phish

A person reports a suspicious message. Work in this order, and keep the message **unopened** in your normal environment.

1. **Preserve it.** Get the original as a file (`.eml`), not a forward, so the headers survive.
2. **Read the headers** (the table above): who it claims to be, who it came from, what your server's `Authentication-Results` said. Do not trust lower, sender-supplied results.
3. **Read the links without clicking.** Compare what the text shows with where it goes. Look for look-alike or punycode hosts and bare IP addresses.
4. **Inspect attachments only in a sandbox you own**: a disposable virtual machine with no access to your network, accounts or files. Take hashes first (SHA-256) and look the hash up; the lab script prints them and opens nothing.
5. **Decide**: phish, spam, legitimate, unsure. Ask the reporter what they did.
6. **Report and block.** Use your provider's submission path so filters learn; block the sender, domain and link host where your tools allow.
7. **Hunt.** Search for the same sender, subject or link host across all mailboxes (Microsoft's Threat Explorer in Plan 2, or message trace and search; a gateway's own console; a SIEM). Find who else received it and who clicked.
8. **Remediate.** Remove it from mailboxes. For anyone who clicked or entered a password: reset the credential, revoke sessions and app grants, check inbox rules and forwarding.
9. **Write it down.** What was attempted, who was exposed, what you changed, and the lesson. [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) covers where the evidence lives.

Exercise 6 gives you a worksheet for steps 2 to 4.

## Should you run your own email server?

This section is the maintainer's experience first, then the sources. It was added the same day as the rest, on his direction.

In his words: you can self-host email, and he recommends [Mail-in-a-Box](https://mailinabox.email/) for learning; "that's actually how I learned all this about emails and email relays". His verdict: **friends don't let friends run their own email server.** What he found hard: a static IP, a server that must stay up, being accepted by the big providers, warming up an address. He ended up relaying through Mailgun from his Mail-in-a-Box "to guarantee deliverability", eventually "threw in the towel" and moved to a hosted service, and he ran his own mail for about a decade and deployed it for businesses before that. The cost of failure he describes is the worst kind: mail that fails to arrive for days, silently, including an important one.

### What Mail-in-a-Box is, from its own pages

Its README and setup guide (retrieved 2026-10-22) describe a project that turns a fresh machine into a mail server by installing and configuring: Postfix (SMTP), Dovecot (IMAP), Nextcloud (calendar and contacts), z-push (Exchange ActiveSync), Roundcube webmail, SpamAssassin and Postgrey (graylisting), its own DNS server (`nsd`) with SPF, DKIM (OpenDKIM), DMARC, DNSSEC and DANE TLSA, Let's Encrypt certificates, backups (duplicity), a firewall (`ufw`), fail2ban, and a control panel with a daily health check. It says what it will not be: not "NSA-proof", not customizable by power users.

What it requires, per the guide: a **dedicated, fresh** machine ("you cannot modify the box after installation"); the README names Ubuntu 22.04 LTS; at least 512 MB of RAM, with 1 GB recommended; not a home connection ("computers on most residential networks are blocked from sending mail" on both ends); reverse DNS set to the box's hostname; and a list of open ports (22, 25, 53 TCP and UDP, 80, 443, 465, 993, 995 and 4190). It says the arrangement costs about $12 a month and warns "you must be prepared to resolve issues as they arise". It also says plainly that "other mail services might block or spam-filter email sent from your Mail-in-a-Box", a challenge "faced by everyone who runs their own mail server".

### What deliverability needs

**Deliverability** is whether your mail reaches the inbox rather than being refused or filtered. The receiving side is making a reputation decision about a sender it has never met. From the receivers' own public requirements (Google's sender guidelines, retrieved 2026-10-22): authenticate with SPF or DKIM (all senders) and SPF, DKIM and DMARC (bulk senders, which Google defines as more than 5,000 messages a day to Gmail), have valid forward and reverse DNS (a **PTR record**) for the sending IP, use TLS, keep the spam rate reported in Google's Postmaster Tools under 0.3%, and for bulk marketing mail support one-click unsubscribe. Microsoft has published matching requirements for high-volume senders to Outlook.com; its announcement page would not render for my fetch, so I state nothing from it: **not verified**.

Beyond the written rules there is **reputation** you cannot read directly: the history of the IP address and the domain, whether the address sits on a **blocklist**, whether recipients report your mail as spam (providers feed some of that back through **feedback loops**), and **warm-up**, the practice of sending small, wanted volume from a new address and growing it. A brand-new address from a cloud provider's range has no history, and provider ranges are often distrusted because abuse is common there. None of this is a setting you can configure; it is earned slowly and lost quickly.

### Why your cloud provider may not let you send at all

Many providers block outbound SMTP by default. DigitalOcean's documentation (retrieved 2026-10-22) says ports 25, 465 and 587 are blocked on Droplets by default, including traffic through a Reserved IP, and, in the same article, "we strongly recommend against running your own mail server" and recommends a third-party email service. AWS's re:Post article says AWS blocks outbound port 25 for EC2 instances and Lambda functions on accounts not on an allowlist, and that you must submit a request, per Region, to have the restriction removed. The Mail-in-a-Box guide itself says Amazon's network "is often blocked to prevent users from sending spam". I did not find DigitalOcean's unblock procedure on that page, and I have not asked either provider for one: check with them.

### Relays, transactional services and list servers

The usual answer to deliverability is **to stop sending directly**. Your server accepts and stores mail, and sends outbound through a **relay** whose reputation is already established: a **transactional email service** reached over SMTP or an API. Examples named by the maintainer and the class: Mailgun, Amazon SES, SendGrid, Postmark. What the pricing pages said on 2026-10-22: Mailgun lists a free tier of 100 emails a day and a Basic plan starting at $15 a month with 10,000 emails included; Postmark lists a free tier of 100 emails a month and a Basic plan at $15.00 a month with 10,000 emails, extra at $1.80 per 1,000; Amazon SES lists per-1,000-email rates in three plans (the Essentials rate shown was $0.16 per 1,000 for 0 to 10 million a month). I did not total these or compare features, and prices change. What you get is a clean sending reputation, bounce and complaint handling, and DKIM/SPF set up for you. What it costs: money, a dependence on the provider's terms, and a third party that handles your outbound mail. You still publish SPF that includes the relay and DKIM that aligns, so Exercise 3's "aligned versus unaligned third-party sender" is exactly this case.

**Newsletter and marketing services** (Mailchimp is the example) and **list servers** (software such as GNU Mailman that redistributes a message to many subscribers) are different tools for one-to-many mail. They matter here for a reason in this lesson: a list server **changes the message** (adds a footer or a subject tag) and **re-sends it from its own address**, which breaks DKIM and SPF for the original sender's domain. Mailman's documentation describes a "DMARC mitigation" rule that checks the sender domain's DMARC policy and, depending on list settings, rejects, discards, or rewrites the message to get around the failure. ARC is the standards-track attempt to let such intermediaries vouch for what they saw. Bulk mail to people who asked for it also has legal and provider requirements (unsubscribe, consent) that I did not research here: **not verified**.

### What Mail-in-a-Box teaches well, and where it stops

| It teaches well | Where it stops, compared with an enterprise email platform |
|---|---|
| Every record in this lesson, set up for you and checked daily: MX, SPF, DKIM, DMARC, DNSSEC, DANE | **Identity.** Users are local mailboxes. No SAML or OIDC single sign-on, no conditional access, no phishing-resistant MFA policy. Compare [Enterprise identity](Enterprise-Identity-SSO-SAML-OIDC.md) |
| How SMTP, IMAP, graylisting, spam scoring and TLS fit together | **Audit and detection.** No unified audit log, message trace, Threat Explorer-style hunting or alert pipeline you did not build |
| Why reverse DNS, blocklists and port 25 matter, by being refused | **Data loss prevention, retention and eDiscovery.** No built-in DLP, retention labels, legal hold or search across mailboxes for a case. Compare [Cross-tenant DLP and retention](Cross-Tenant-Data-Governance-Retention-and-DLP.md) |
| Backups, a firewall, fail2ban, and a health page, all in one box | **Delegated administration.** Its README describes a control panel for adding and removing users, aliases and DNS; it lists no role-based delegated admin (est.) |
| Reading real logs when mail does not arrive | **Availability.** One machine, no stated service level, no high availability; recovery is your backup and your time |
| That a mail server is a long-lived system you must patch and watch | **Compliance and support.** No mailbox compliance attestations, no vendor support line; help is a forum, and the README says not to email the author |

The right-hand column is what its README and guide do not list, not a test I ran, so read it as an estimate of scope (est.). The project is good at what it sets out to do: make "deploying a good mail server easy". It is a learning box and a personal server, not a replacement for an enterprise identity provider and a managed platform, and the comparison above is about scope, not quality.

### The verdict, and "but learn it in a lab"

The maintainer's opinion, which this page endorses as advice: **do not rely on a self-hosted mail server for mail you cannot afford to lose**, because the failure mode is silent. A hosted service takes the reputation, the uptime, the patching and the blocklist problems off you. **Do learn it once, in a lab**, because running a mail server teaches headers, DNS, TLS, reputation and abuse handling faster than any reading, and it is the reason this page's authentication sections make sense. The lab below teaches the protocol and the records without any real delivery. The optional own-account path below builds a Mail-in-a-Box learning box and tells you to send only to addresses you own.

### Hosted email for people: Proton and Tuta

> **Disclosure.** The maintainer has affiliate relationships with **both** Proton and Tuta. If you sign up through his links, he may earn a commission, and that helps fund this research. The recommendation is also his honest, long-standing personal use: he uses both and recommends both for the average user. You can sign up without his links; nothing on this page requires them. His links are collected on one page, [links.chiefgyk3d.com/productrecs](https://links.chiefgyk3d.com/productrecs), and this wiki embeds no individual affiliate address. Where he recommends tools, [Why I picked these tools](Why-I-Picked-These-Tools.md#disclosure-first) keeps the running disclosure.

The two services are described below from their own public pages (retrieved 2026-10-22), neutrally and without a ranking. Both are encrypted-email services run by companies in Europe.

| Question | Proton Mail | Tuta Mail |
|---|---|---|
| Company location as stated | Incorporated and headquartered in Switzerland | Germany ("Privacy made in Germany", data stored in Germany) |
| Encryption model | "Zero-access" encryption of stored mail; end-to-end encrypted between Proton users; an OpenPGP-based design | Its own scheme (not PGP): initially AES-256 and RSA-2048, with a stated move to x25519 plus Kyber-1024; contacts and calendars encrypted too |
| Mail to people on other providers | Not end-to-end encrypted by default: "the recipient's email provider may be able to access it". Password-protected messages and PGP are options | Unencrypted to non-Tuta contacts unless you use a shared password; Tuta says it then "can only encrypt the transmission" |
| What is not end-to-end encrypted | **Subject lines**, to remain compatible with the OpenPGP standard (per Proton's own article) | Metadata "such as email addresses of senders and recipients" is not (per Tuta); Tuta says it does encrypt subject lines |
| Custom domain | Supported on Proton's subscription plans, with MX, SPF, DKIM and DMARC records to publish | Not confirmed from the page I fetched: **check Tuta's current plans** |
| Search | Not read | Done locally on your device through an encrypted index, per Tuta |

Criteria for choosing, not a ranking: which jurisdiction and legal regime you are comfortable with; whether you need to talk to people outside the service and how much of that is encrypted; what metadata (addresses, times, subject lines) you are willing to leave visible; whether you need a custom domain, and how many users or aliases; whether you need to use standard mail clients through IMAP (many encrypted services need a bridge or their own app: check each); the features you will use (calendar, contacts, storage); price; and the exit path (can you export everything and leave). Encrypted email protects mail at rest and between users of the service. **It does not stop phishing**: you still get phish at a Proton or Tuta address, and the rest of this page still applies.

## Build it piece by piece, and what it costs

Every build in this track works two ways: one piece at a time, learning each, or the whole thing at once. There are two optional own-account paths, and either, both or neither is fine. The free local lab does not need them.

> **Cost box. Read this before you create anything.**
>
> **What is estimated.** Dollar figures come from [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json), retrieved 2026-10-21, for DigitalOcean droplets, and from DigitalOcean's reserved-IP pricing page, read 2026-10-22. Prices change; check your provider's page before you build. Anything marked est. is my arithmetic or a guess, not a vendor figure. I read **no** domain registration price, **no** Microsoft 365 subscription price after the trial, and **no** API-driven product price.
>
> **If you forget it.** With the Mail-in-a-Box path built and left running, the droplet is **$6 a month, about $0.20 a day** (est.: $6 divided by 30), and a powered-off droplet is still billed. A **reserved IPv4 address that is not assigned to a droplet costs $5.00 a month ($0.01 an hour)**; it is free while assigned. A domain renews yearly. The Microsoft 365 trial **renews to an annual subscription by default** if you do nothing.
>
> **Not covered by this estimate.** The domain name; snapshots and backups; data transfer; any relay service; any Microsoft 365 or security product subscription after a trial; anything you create by hand.
>
> **A spend alert is not a spending cap.** It sends an email; it does not stop anything. Set one first: [How money works in the cloud](How-Money-Works-in-the-Cloud.md#1-a-billing-alert-before-anything-else). Set your own hard budget for this lab before you start, and destroy everything when you reach it. The project sets no limit for you.
>
> **Teardown first.** Read the teardown steps below before you run anything, and set a reminder for the day you plan to destroy it. Destroy in the reverse of the build order.
>
> **You can stop at any piece.** Each piece works and teaches on its own. The free local lab covers the same ideas for $0.

### The Mail-in-a-Box pieces (DigitalOcean, OpenTofu)

The code is in [`labs/email-security/cloud`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/tree/main/labs/email-security/cloud), one folder per piece, and [`labs/email-security/compose`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/tree/main/labs/email-security/compose) calls them all. **Every flag defaults to false, so a plain `tofu plan` creates nothing.** The `labs/` folder is outside the project's cost gate on purpose (see [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md#the-labs-exemption-option-l1)); that makes it your bill, not the project's.

| Piece | Depends on | Cost per month on your own account | Build order | Destroy order | Teardown proof |
|---|---|---|---|---|---|
| **Project** (a DigitalOcean project of its own) | none | $0 | 1 | 5 | `doctl projects list` does not show it (est.) |
| **Firewall** (the ports the Mail-in-a-Box guide lists; SSH from your one address) | none | $0 (cloud firewalls are free in the project's cost gate) | 1 | 4 | `doctl compute firewall list` shows nothing named `mail-lab-fw` |
| **Droplet** (`s-1vcpu-1gb`, Ubuntu 22.04, named for the box's hostname) | firewall (by tag) | $6 at list price (`docs/cost-prices.json`) | 2 | 3 | `doctl compute droplet list` shows nothing named for your box |
| **Reserved IP** (a stable address to build reputation on) | droplet | $0 while assigned; **$5.00 if left unassigned** | 3 | 2 | `doctl compute reserved-ip list` is empty |
| **DNS** (a zone and the one A record for the box) | reserved IP | $0 on DigitalOcean DNS (read 2026-10-22) | 4 | 1 | `doctl compute domain list` does not show your domain |
| **Not in this table** | | The domain name; snapshots; backups; transfer; any relay | | | |

Prices from `docs/cost-prices.json`, retrieved 2026-10-21, and DigitalOcean's pricing pages, read 2026-10-22. The same facts are in `labs/email-security/pieces.json` as data.

## Free theory path: a local lab

The code lives in [`labs/email-security/local`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/tree/main/labs/email-security/local). Copy it to your machine; Exercise 1 already created the private work folder `$LAB`. Everything here uses reserved names (`.test`, `.invalid`, `example.com`) and RFC 5737 addresses. Every key and message is built at run time by `mkmail.py`; nothing secret-shaped is committed. The scripts import each other, so run them from `$LAB` as `python3 local/NAME.py` (not with `-I`, which would hide the imports); the folder is private to you, which is why that is safe. Every exercise has four steps: predict, do, check, undo.

### Exercise 2: a fake zone, and the evaluator

**Predict.** `mkmail.py` built thirteen messages. Which do you expect to pass DMARC, and which to be quarantined or rejected?

**Do.** Evaluate every message against the zone file (no network at all):

```bash
cd "$LAB" && python3 local/mailauth.py eval --zone zone.json manifest.json
```

```powershell
# est.: not run
python local\mailauth.py eval --zone zone.json manifest.json
```

**Check.** On 2026-10-22 (trimmed):

```text
message                              SPF       DKIM     DMARC  aligned  disposition
01-legit-internal-signed.eml         pass      pass     pass   SD       deliver
02-newsletter-bulk-unaligned.eml     pass      pass     fail   --       quarantine
03-newsletter-bulk-aligned.eml       pass      pass     pass   -D       deliver
04-forged-ceo.eml                    fail      none     fail   --       quarantine
05-lookalike-domain.eml              pass      none     pass   S-       deliver
06-display-name-trick.eml            pass      none     none   --       no DMARC policy
07-forwarded-by-list.eml             none      pass     pass   -D       deliver
08-list-rewrote-body.eml             none      fail     fail   --       quarantine
09-spf-too-many-lookups.eml          permerror none     fail   --       reject
10-spf-two-records.eml               permerror none     fail   --       reject
11-subdomain-spoof.eml               none      none     fail   --       reject
```

The `aligned` column is `S` when SPF aligned and `D` when DKIM aligned. Read the stories: message 02 passes SPF and DKIM and **still fails DMARC** because both identities belong to the bulk mailer, not to `example.test`; message 03 is the fix (the mailer signs with a key published under your own domain); message 05 passes everything and is still a phish; message 07 shows DKIM carrying a forwarded message that SPF cannot; message 11 is rejected because the subdomain policy (`sp=reject`) is stricter than the domain's (`p=quarantine`).

Now ask why, with `--explain`:

```bash
cd "$LAB" && python3 local/mailauth.py eval --zone zone.json manifest.json --explain | sed -n 1,12p
```

**Undo.** Nothing to undo: the evaluator only reads files.

### Exercise 3: serve the zone with dnsmasq, and compare

The same records, as real DNS on the loopback address, reusing the DNS lesson's pattern. `mkmail.py` already wrote `auth.conf`.

```bash
cd "$LAB" && dnsmasq --test -C auth.conf && dnsmasq -C auth.conf
dig @127.0.0.1 -p 5300 _dmarc.example.test TXT +short
dig @127.0.0.1 -p 5300 s2026a._domainkey.example.test TXT +short | cut -c1-60
python3 local/mailauth.py eval --dns 127.0.0.1:5300 manifest.json > udp.txt
python3 local/mailauth.py eval --zone zone.json manifest.json > file.txt
diff udp.txt file.txt && echo SAME
```

**Check.** The two `dig` answers appear (the key is several quoted strings in one record, because a TXT string holds at most 255 characters), and `SAME` prints: the DNS server gave the evaluator the same answers as the file. Stop `dnsmasq` safely (never `pkill -f`, which can match your own shell): the pid file is in your private folder, and this reads it, checks that it holds only digits, and checks that the process really is a `dnsmasq` using `auth.conf`:

```bash
cd "$LAB" && pid="$(cat auth.pid)"
[[ "$pid" =~ ^[0-9]+$ ]] && [[ "$(ps -o command= -p "$pid" 2>/dev/null)" == *dnsmasq*auth.conf* ]] && kill "$pid"
```

```powershell
# est.: dnsmasq is Linux software; run this exercise inside WSL 2. Exercises 2 and 4 to 7 need no server.
```

### Exercise 4: break SPF and DKIM on purpose

**Predict.** `09-spf-too-many-lookups` lists eleven `include:` terms. Where does evaluation stop? What happens to a message that is genuinely authorized by the eleventh?

**Do.**

```bash
cd "$LAB" && python3 local/mailauth.py spf --zone zone.json --ip 203.0.113.201 --domain toomany.test | tail -4
python3 local/mailauth.py spf --zone zone.json --ip 192.0.2.25 --domain twice.test
python3 local/mailauth.py eval --zone zone.json manifest.json --explain | grep -A3 '^08-'
```

**Check.** The first ends `lookup 11: include:hop11.toomany.test`, `LIMIT: more than 10 DNS-querying terms (RFC 7208 section 4.6.4)` and `result=permerror dns_lookups=11`: the sender that only the eleventh include authorizes gets `permerror` from a conforming receiver, and with the domain's `p=reject` the message is refused, with nothing in the sender's own mail logs. The second says `2 SPF records published; exactly one is allowed`. The third shows message 08's DKIM as `body hash mismatch (the body changed after signing)`: the mailing list's footer broke it. The fix for the first is to flatten or consolidate the record (and watch it as vendors change their own records); for the third, an ARC-aware receiver, or a list that rewrites the From.

**Undo.** Nothing changed.

### Exercise 5: read a DMARC aggregate report

`mkmail.py` also wrote `report.xml`, a synthetic report in the shape of RFC 9990 for `example.test` while it still publishes `p=none`.

```bash
cd "$LAB" && python3 local/dmarc_report.py report.xml
```

**Check.** On 2026-10-22:

```text
source ip        messages   pass   fail  signed-by / mail-from domains
198.51.100.7           75     35     40  dkim=bulkmailer.test,example.test spf=bulkmailer.test
203.0.113.66           14      0     14  dkim=- spf=example.test,pay.example.test
203.0.113.25            6      0      6  dkim=example.test spf=receiver.test
192.0.2.25            120    120      0  dkim=example.test spf=example.test

60 of 215 messages (27.9%) fail DMARC. Enforcing now would act on all of them.
```

Sort the failing rows into yours and not yours. `198.51.100.7` is the bulk mailer you hired: half its mail fails because some of it is not signed with your domain; fix it (Exercise 2, message 03) before you enforce. `203.0.113.66` is nobody you know: that is exactly what enforcement is for. `203.0.113.25` is a mailing list that broke a signature: a case to understand, not to fix. The parser refuses any file with a `DOCTYPE` or `ENTITY` declaration and any file over a megabyte, because a report is mail from a stranger and XML can be made to expand or fetch things; try it:

```bash
cd "$LAB" && printf '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><feedback/>' > evil.xml && python3 local/dmarc_report.py evil.xml; rm -f evil.xml
```

It exits with `contains a DOCTYPE or ENTITY declaration, refusing`.

### Exercise 6: the triage worksheet

**Predict.** For `05-lookalike-domain.eml`, which of the two links is the real destination, and what do the authentication results tell you?

**Do.**

```bash
cd "$LAB" && python3 local/triage.py msgs/05-lookalike-domain.eml
python3 local/triage.py msgs/13-double-extension-attachment.eml | sed -n '/## 3/,/## 5/p'
python3 local/triage.py msgs/12-qr-image-only.eml | sed -n '/## 4/,/## 5/p'
```

**Check.** The first worksheet shows `dmarc=pass` for `examp1e.test` (it authenticates as itself), a Reply-To at a different domain, and hints: the From domain looks like the protected `example.test`; the link text shows `example.com` but goes to `payroll-update.invalid`. The second lists `remittance.pdf.html` with its SHA-256 and the hint that it has a double extension and must not be opened outside a sandbox. The third flags an image-only body. The script opened and rendered nothing; the links are `.invalid` and `example.com` names that cannot resolve to anything real. Fill in the decision lines by hand for each message, the way the triage section describes.

**Undo.** Nothing to undo.

### Exercise 7: where the filter sits decides what it can see

A pure-computation comparison. Ten invented messages, one toy detector, three positions: a **gateway** (before delivery, external mail that crossed the MX), an **API product after delivery** (sees all mail and chat, acts minutes later), and an **API product in inline mode** (a mail-flow rule sends mail through it first). The numbers are invented and the detector is a toy; nothing here models a vendor.

```bash
cd "$LAB" && python3 local/positions.py
python3 local/positions.py --lockdown no | sed -n 4,9p
python3 local/positions.py --click 2
```

**Predict.** Which message does the gateway miss that both API positions catch? What changes when the tenant is not locked down to the gateway?

**Check.** With the lock-down in place the gateway stops the spoof, the known-bad link and the look-alike, and **misses** the link that turned bad forty minutes after delivery (M3), the internal phish from a colleague (M5), the Teams message (M6), and the account-takeover request that only mailbox history exposes (M8). Without the lock-down it also misses mail sent straight to the tenant (M4). The after-delivery API position catches more but **after** the delivery: M3 is removed after the user would have clicked, and with `--click 2` more rows move from "removed before the click" to "removed AFTER the click". The inline position stops email before delivery but, in this toy, does not see chat. Every position produced the same **false positive** on a real invoice from a new vendor with an odd domain, and no position removes the need for a person to decide. The point is the position, not the vendor.

## Optional: your own accounts

This section uses **your own** accounts and **your own** bill. The reading and the free lab above are free and always will be. Read the [cost box](#build-it-piece-by-piece-and-what-it-costs) first.

### A Microsoft 365 trial tenant, with a domain from the DNS lesson

**Cost and teardown first.** Microsoft's page says you can sign up for a free 30-day trial of Microsoft 365 Business Basic, Standard or Premium; trial-only tenants are limited to 30 days and 300 GB; and "at the end of your trial period, your subscription renews to an annual term subscription by default, unless you turn off recurring billing from inside of Billing > Your products." I did not read whether a payment card is required at sign-up, and I read no price for after the trial. **Teardown:** turn off recurring billing (or cancel) on the day you sign up, set a reminder for the day before day 30, remove your custom domain from the tenant, and delete the DNS records you added. Deleting the tenant itself is a separate Microsoft procedure I did not read (**est.**).

The **Microsoft 365 Developer Program** is not the easy route it once was. Microsoft's page, updated 2026-09-08, says eligible members can request a free E5 developer sandbox, that eligibility paths are Visual Studio Professional or Enterprise subscribers, certain partner-program members, and customers with certain support contracts, and that the program is not offered in government clouds. Do not assume you qualify. A separate page says existing Microsoft 365 customers can try Defender for Office 365 Plan 2 for 90 days from the Microsoft Defender portal (educational and government tenants excluded).

**What to do with a tenant** (all **est.**: not run): add your domain; publish the SPF record Microsoft documents for your domain; enable DKIM for the domain (the `selector1` and `selector2` CNAME records Microsoft's page describes), then read the signing configuration with `Get-DkimSigningConfig -Identity yourdomain.example | Format-List Name,Enabled,Status,Selector1CNAME,Selector2CNAME`; publish `_dmarc` at `p=none` with an `rua` mailbox; send test mail to and from outside accounts you own; read the `Authentication-Results` and `X-Forefront-Antispam-Report` headers Microsoft stamps; and walk the order in [Set up DMARC safely](#set-up-dmarc-safely).

```powershell
# est.: not run. Exchange Online PowerShell; read-only checks.
Connect-ExchangeOnline
Get-DkimSigningConfig -Identity yourdomain.example | Format-List Name,Enabled,Status,Selector1CNAME,Selector2CNAME
Get-InboundConnector | Format-List Name,ConnectorType,RestrictDomainsToIPAddresses,SenderIPAddresses,EFSkipLastIP
```

```bash
# Read what the world sees for your domain (replace the placeholder with a domain you own):
dig +short TXT yourdomain.example; dig +short TXT _dmarc.yourdomain.example; dig +short CNAME selector1._domainkey.yourdomain.example
```

### The API-driven vendor path: described, not required

Nothing in this lesson needs one. If you want to see one, the vendor documentation above shows the shape: authorize an application in the tenant with a Global Administrator, choose a mode (Monitor only first), and for inline mode add the connectors and mail-flow rules it lists. A free trial request form exists on Check Point's site (a 14-day trial is mentioned on its plans page), and quotes are by request. The maintainer's experience is that these products are sold to business entities only and that he buys through his content and research company; I could not read the vendor's terms of sale, so I cannot say what it requires of a buyer. **Do not grant a vendor application access to a mailbox you do not own, and do not use your employer's tenant.**

### Mail-in-a-Box on a DigitalOcean droplet

**Cost and teardown first.** The piece table above gives the cost: $6 a month for the droplet at list price, $0 for the project, firewall and DNS zone, and **$5.00 a month if you reserve an IP and leave it unassigned**. **Teardown, in this order:** `tofu destroy` from the folder you applied (or delete the DNS zone, then the reserved IP, then the droplet, then the firewall, then the project), then prove it with the `doctl ... list` commands in the table, then check the billing page the next day. Release the reserved IP before you delete the droplet only if you do not intend to keep it.

**Hard warnings, in the order they will bite you:**

1. **Outbound port 25 is blocked on DigitalOcean droplets by default** (the provider's own documentation, above). Your box can receive but may be unable to send. The same page blocks ports 465 and 587 as well, so a relay on those ports is blocked too; follow the provider's documented method (for example a relay service's API over HTTPS, est.) or use a provider that allows outbound mail. I expect Mail-in-a-Box's status page to show the problem (est.).
2. **A fresh address has no reputation**, and large providers may reject or spam-folder mail from it however perfect your records. The guide itself suggests checking whether your assigned address is on a blocklist with a tool such as MXToolbox.
3. **Send only to addresses you own.** Do not send bulk mail from this box. Do not use it for anything you cannot afford to lose.
4. Do **not** run anything on a droplet that you have not put in a firewall first; the OpenTofu creates the firewall by tag before the droplet.

**This lab is IPv4-only on purpose.** The droplet disables IPv6 (the Mail-in-a-Box guide says to disable it if you can), so the firewall's SSH source must be an IPv4 address written `a.b.c.d/32`; the code refuses an IPv6 range, a wider range or the whole internet. To find your public IPv4 address, ask a service that answers with it, for example `curl -4 https://ifconfig.co` (it answered with HTTP 200 on 2026-10-22; any equivalent service works, and the address is whatever your connection presents, so check it again if your router restarts):

```bash
curl -4 -sS https://ifconfig.co
```

```powershell
# est.: not run
Invoke-RestMethod -Uri https://ifconfig.co/ip
```

If IPv6 is switched off on your network (the maintainer's pfSense has it off), you are fine: you still have an IPv4 address and that is what the lab needs. If your internet provider gives you IPv6 only, the lab needs an IPv4 source: use a connection that has one, such as a phone hotspot or another network, or skip the own-account path; the free lab does not need it. Mail reputation checks differ for IPv6 too: Google's sender guidelines (read 2026-10-22) say a sending IPv6 address needs its own PTR record, with a matching forward record, and show a separate "IPv6 sending guidelines" rejection. I read no equivalent Microsoft statement.

**Steps** (the guide is the authority; I did not run them):

1. Create an SSH key and add it to your DigitalOcean account; note its fingerprint. Create a DigitalOcean API token with the least scope that works, and put it in your shell as `DIGITALOCEAN_TOKEN` only for this session (see [Secrets from day one](Secrets-From-Day-One.md)). Never put it in a file in the repository.
2. Decide a domain you own and a hostname `box.<domain>` (the guide recommends `box.` plus the domain; the droplet **name must equal the hostname** so DigitalOcean sets the reverse DNS to it).
3. In `labs/email-security/compose`, read the plan with all flags off, then turn on one piece at a time:

```bash
cd labs/email-security/compose && tofu init -input=false
tofu plan -input=false                                        # nothing: every flag is false
tofu plan -var enable_firewall=true -var 'admin_cidr=<your address>/32'
```

```powershell
# est.: not run
Set-Location labs\email-security\compose; tofu init -input=false; tofu plan -input=false
```

4. When the plan reads right, apply the pieces in the piece table's order, add the droplet only with at least one SSH key fingerprint (the code refuses to create a password-login droplet), reserve and assign the IP, and add the DNS piece for the one `box` record.
5. Run the Mail-in-a-Box setup as its README says on a **fresh** machine (git clone, check out the latest release tag, run the setup script), then work through its "System status" page, which lists the DNS records the box wants. Check the reverse DNS with `dig -x <address>` (whether it follows a reserved address is **est.**).
6. Learn from it: send a message to your own other account, read the headers, read the DMARC reports it generates, and compare them with Exercises 2 and 5.

**Reverse DNS (PTR).** The Mail-in-a-Box guide says a DigitalOcean droplet's reverse DNS is set from the droplet's name. If you change the name or use a reserved IP, check it again.

## Build, break, detect, evade, defend

The loop from the other lessons, on the lab.

**Build.** A domain whose records say who may send for it (SPF), sign with a published key (DKIM) and what to do with failures (DMARC), plus an evaluator that applies them (Exercises 2 to 4) and a report reader (Exercise 5).

**Break.** Forge the CEO's `From:` and watch SPF fail and DMARC quarantine (message 04). Send as a hired mailer that is not aligned and watch legitimate mail fail DMARC (02). Push SPF past ten lookups and watch an authorized sender fail (09). Let a mailing list modify a signed body (08). None of this touches anything but your own files.

**Detect.** Three signals, all in the lab output. A DMARC aggregate report row from a source you do not know (Exercise 5: `203.0.113.66`). An `Authentication-Results` line with `dmarc=fail` on mail claiming your domain. A second `Authentication-Results` header that did not come from your server (message 04). In a real tenant add: new inbox rules and forwarding, "Consent to application" audit events, and impossible-travel sign-ins.

**Evade.** An attacker avoids your domain's controls by using a **different** domain that passes its own checks (the look-alike, message 05), a **display name** that does the impersonating, a **real compromised account** that passes everything (vendor email compromise, which no lab message models), a **QR image** that hides the link from text scanners (12), or a **file type** a filter allows (13). Against a gateway they send to the tenant directly if it is not locked down (M4 in Exercise 7). Against an API product they use a channel it is not connected to. This page shows no working attack against anyone else's system, and none is needed to understand the defenses.

**Defend.** SPF with a record under ten lookups and `-all`; DKIM with 2048-bit keys, selectors you can rotate, and third-party senders signing with your domain; DMARC rolled to enforcement with reports read; subdomain and parked-domain policies; MTA-STS and TLS-RPT; for a gateway, the connector lock-down and Enhanced Filtering; for an API product, admin-only consent, least privilege, audit and a tested exit; user reporting; payment-change verification outside email; phishing-resistant MFA; alerts on new forwarding rules and app consents; and a triage procedure you have practiced.

### Flip the board

You built and attacked. Now take the other two jobs.

**The reviewer.** A colleague sends this plan to "lock down email". Find at least six problems without running anything.

```text
Plan: "Email security, version 1"
- SPF: v=spf1 include:_spf.vendor-a.test include:_spf.vendor-b.test include:_spf.vendor-c.test
  include:_spf.vendor-d.test include:_spf.vendor-e.test +all     (each vendor's record itself includes two more)
- DMARC: p=reject; pct=100; no rua, because "reports are noise".  Published the same day, on the main domain only.
- DKIM: 1024-bit key, one selector, never rotated.
- Gateway: the MX points at it. Exchange Online still accepts mail from anywhere.
- An API email security app was consented to by a helpdesk user, with a "send mail as any user" permission "so it can notify people".
- "Authentication passed, so the message is safe."
- Reported phish: forward it to the security mailbox, then delete the original.
```

<details>
<summary>What to find</summary>

1. **`+all`:** authorizes every server on the internet. It should name the real senders and end in `-all`.
2. **Lookup budget:** five includes that each include more will pass ten lookups; the record will `permerror` (Exercise 4). Consolidate and monitor.
3. **No `rua`, day-one `p=reject`:** nobody has seen the senders. Legitimate mail from the payroll tool and the newsletter service will be refused. Start at `none`, read reports, then enforce (Set up DMARC safely). `pct` is also removed in RFC 9989.
4. **Subdomains and parked domains:** only the main domain is covered. Add `sp=`, and records for domains that send no mail.
5. **DKIM:** a single never-rotated 1024-bit key is the minimum, not a good choice. Use 2048 bits and rotate selectors.
6. **Gateway without lock-down:** an attacker sends to Exchange Online directly and skips the gateway. Add the inbound connector restriction and Enhanced Filtering.
7. **Consent by a helpdesk user, with send-as-anyone:** consent should be admin-only after review; "send mail as any user" in the hands of a compromised vendor lets it impersonate your people.
8. **"Passed, so safe":** look-alike domains and compromised real accounts pass. Authentication is necessary, not sufficient.
9. **Forward and delete:** a forward loses the headers and destroys the evidence. Preserve the original, hunt for others, then remove.

</details>

**The responder.** At 09:00 three people report "payroll" mail. The top `Authentication-Results` says `dmarc=pass` for a domain one character away from yours, the Reply-To is elsewhere, and one person says they entered their password. Write, in order, what you do: preserve the message; read the headers and links without opening them; block the sender, domain and link host; hunt for the same sender and link host across mailboxes; find who clicked; for the person who entered a password, reset it, revoke sessions and app grants, and check inbox rules and forwarding; report to the provider; write the timeline. Restore trust first, then find the cause.

## Threat model

**Assets.** The integrity of your domain's identity in mail; the confidentiality of mailboxes and attachments; the availability of mail delivery; the credentials and sessions of mailbox owners; the tenant and its app grants; money that mail can talk someone into moving.

**Actors.** An outsider who forges or look-alikes your domain; an outsider who phishes your people; an attacker with a stolen mailbox; an attacker with a consented app; an operator who misconfigures SPF, DMARC or a connector; a third-party vendor (a sender, a gateway, an API product, a relay) that is trusted and can fail or be compromised; a mailing list or forwarder that legitimately breaks authentication.

**Trust boundaries.** The internet to your MX (nothing trusted). The gateway to your tenant (only the gateway's certificate or addresses). The tenant to an authorized application (standing broad access). The sender's claimed `From:` to the authenticated identities (only alignment links them). Your mail server to a relay (the relay's reputation, and its view of your mail). A user to a consent screen.

| Abuse case | Impact | Prerequisite | Mitigation | Verification | Residual risk |
|---|---|---|---|---|---|
| Forged `From:` of your domain | Fraud, reputational harm | DMARC at `none` or absent | SPF, DKIM, DMARC at enforcement | Exercise 2; DMARC reports show no unknown sources | Receivers differ in how they treat `p=reject` |
| Legitimate mail fails after enforcement | Lost mail | Unaligned third-party sender | Monitor first; align or sign with your domain | Exercise 5 before enforcing | Forwarders and lists still break SPF |
| SPF over the lookup limit | Authorized senders fail silently | Many includes | Consolidate; monitor lookup count | Exercise 4 | Vendors change their own records |
| Gateway bypass by direct delivery | The gateway sees nothing | Tenant accepts mail from anywhere | Partner connector restriction; Enhanced Filtering | Exercise 7 (`--lockdown`); send a test directly | Internal mail never crosses the gateway |
| Look-alike or display-name phish | Credential theft, fraud | Authentication only on your domain | Impersonation protection; training; out-of-band checks | Triage Exercise 6 | Authentication cannot catch it |
| Illicit consent grant | Standing mailbox access without a password | Users may consent broadly | Admin-only consent for unverified apps; review grants; audit-log alert | Audit-log search for consent events | A trusted vendor that is later compromised |
| API product over-permissioned or compromised | Tenant-wide read and write on mail and files | Broad grant | Least privilege; manual mode where offered; audit; tested exit | Read the permission list; review app registrations | You trust the vendor with standing access |
| Account takeover with hidden rules | Silent forwarding, fraud | Stolen credentials | MFA; alert on new rules and forwarding; revoke sessions | Hunt for rules and forwarding | Session theft past MFA |
| Self-hosted mail not delivered | Silent loss of important mail | New or unreputable address; blocked port 25; blocklist | Do not rely on it; relay through a reputable service; hosted mail for people | Send to several providers and read the bounces | Reputation is outside your control |
| Mail-in-a-Box box compromised or left unpatched | Mailbox theft, spam source | One admin, one machine | Firewall, updates, backups, monitoring, a rebuild plan | The box's daily status checks; your own | Single point of failure |

**Residual risk, in one line:** you can make your own domain hard to forge and your tenant hard to bypass, and you can choose who holds standing access to your mail, but no position, product or protocol makes a message from a convincing stranger or a compromised friend safe to trust.

## Checkpoint

You are done when you can say, without looking:

- The path of a message from MUA to mailbox, and why `MAIL FROM` and `From:` can differ.
- Which header lines you may trust, and why a lower `Authentication-Results` is not one of them.
- What SPF, DKIM, DMARC, MTA-STS and TLS-RPT each check, and one thing each cannot do.
- What alignment is, why a hired mailer can pass SPF and DKIM and still fail DMARC, and how to fix it.
- The SPF lookup limit and what happens past it.
- The rollout order for DMARC and why `p=none` with reports comes first; what changed in RFC 9989.
- How a gateway sits in front of Microsoft 365, and the connector lock-down that stops a bypass.
- What an API-driven product connects to, its three modes, and the permissions and trust boundary it brings.
- Five attacks seen in email, a detection signal and a control for each, and why two of them pass authentication.
- The triage order for a reported phish and why you preserve the original.
- Why the maintainer says not to run your own mail server, what Mail-in-a-Box teaches, and three gaps against an enterprise platform.
- The affiliation disclosure for Proton and Tuta, and the criteria for choosing a hosted service.

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| `spf=permerror` | Over ten lookups, or two SPF records | Count the terms; one record per name (Exercise 4) |
| `dmarc=fail` on your own newsletter | Third party not aligned | Whose domain is in the envelope and in `d=` (Exercise 2, messages 02 and 03) |
| Forwarded mail fails | SPF breaks on forwarding | DKIM alignment; ARC where the forwarder supports it |
| `dkim=fail` after a list | The list changed the body or subject | `body hash mismatch` (Exercise 4) |
| DKIM key will not publish | TXT string over 255 characters | Split into several quoted strings in one record |
| Mail stops after moving the MX to a gateway | Connector or IP list stale; Enhanced Filtering off | The partner connector and its addresses; the Microsoft page |
| Everything looks spoofed after adding a gateway | Receiver sees the gateway's address | Enhanced Filtering for Connectors |
| Cannot send from the self-hosted box | Outbound port 25 blocked by the provider | The provider's SMTP documentation; use a relay |
| Sent mail goes to spam | New address, no reputation, missing PTR | Reverse DNS matches the hostname; blocklist check; relay |
| A test run left a droplet running | No teardown | The `doctl` proof commands; the next day's billing page |

## Claims register

All read-only requests, retrieved **2026-10-22** unless stated.

| Claim | Source | Status |
|---|---|---|
| SMTP, message format and header-field standards; RFC titles and categories | [RFC 5321](https://www.rfc-editor.org/rfc/rfc5321), [RFC 5322](https://www.rfc-editor.org/rfc/rfc5322), [RFC 8601](https://www.rfc-editor.org/rfc/rfc8601) | Read (titles, abstracts, the points cited) |
| SPF: lookup terms limited to 10 (`permerror`), void lookups SHOULD be limited to two; no restriction on `MAIL FROM` in existing protocols | [RFC 7208](https://www.rfc-editor.org/rfc/rfc7208), section 4.6.4 and abstract | Read |
| DKIM: signature and selector design; key-size rule (signers MUST use at least 1024 bits, SHOULD use 2048) | [RFC 6376](https://www.rfc-editor.org/rfc/rfc6376), [RFC 8301](https://www.rfc-editor.org/rfc/rfc8301) | Read |
| DMARC: RFC 9989 (May 2026, Standards Track) obsoletes RFC 7489 and RFC 9091; `pct`, `rf`, `ri` removed; `np`, `psd`, `t` added; DNS Tree Walk; `p=reject` may break lists and forwarders; at least a month each at `none` and `quarantine` for list-posting domains; reports in RFC 9990 and 9991; RFC 7489 Informational | [RFC 9989](https://www.rfc-editor.org/rfc/rfc9989) (section 4.7, 4.10, 5.1, 7.4, Appendix A.6 and C), [RFC 9990](https://www.rfc-editor.org/rfc/rfc9990), [RFC 9991](https://www.rfc-editor.org/rfc/rfc9991), [RFC 7489](https://www.rfc-editor.org/rfc/rfc7489) | Read |
| MTA-STS policy path and `_mta-sts` record, modes; TLS-RPT `_smtp._tls` and `rua`; ARC is Experimental; null MX | [RFC 8461](https://www.rfc-editor.org/rfc/rfc8461), [RFC 8460](https://www.rfc-editor.org/rfc/rfc8460), [RFC 8617](https://www.rfc-editor.org/rfc/rfc8617), [RFC 7505](https://www.rfc-editor.org/rfc/rfc7505) | Read |
| Third-party gateway with Microsoft 365: MX points at the third party; Partner inbound connector with `RestrictDomainsToCertificate` or `RestrictDomainsToIPAddresses`; Enhanced Filtering ("highly recommended"); trusted ARC sealers; the third scenario (service after Microsoft 365) | [Manage mail flow using a third-party cloud service](https://learn.microsoft.com/en-us/exchange/mail-flow-best-practices/manage-mail-flow-using-third-party-cloud), page dated 2025-07-28; [Enhanced Filtering for Connectors](https://learn.microsoft.com/en-us/exchange/mail-flow-best-practices/use-connectors-to-configure-mail-flow/enhanced-filtering-for-connectors), dated 2026-10-15 | Read |
| EOP features; Defender for Office 365 Plan 1 and Plan 2 features; ZAP, 48 hours; Plan 2 90-day trial for existing customers | [EOP](https://learn.microsoft.com/en-us/defender-office-365/eop-about), [overview](https://learn.microsoft.com/en-us/defender-office-365/mdo-about) (dated 2026-05-21), [ZAP](https://learn.microsoft.com/en-us/defender-office-365/zero-hour-auto-purge), [trial](https://learn.microsoft.com/en-us/defender-office-365/try-microsoft-defender-for-office-365) | Read. Licensing totals not verified |
| Microsoft's SPF, DKIM (two selectors, CNAME, `Get-DkimSigningConfig`) and DMARC pages (still documents `pct`) | [SPF](https://learn.microsoft.com/en-us/defender-office-365/email-authentication-spf-configure), [DKIM](https://learn.microsoft.com/en-us/defender-office-365/email-authentication-dkim-configure), [DMARC](https://learn.microsoft.com/en-us/defender-office-365/email-authentication-dmarc-configure) | Read. The cmdlet's output was not run |
| Exchange Online MTA-STS outbound always on; inbound supported | [Enhance mail flow with MTA-STS](https://learn.microsoft.com/en-us/exchange/security-and-compliance/enhance-mail-flow-using-strict-transport-security), dated 2026-07-21 | Read |
| Illicit consent grants; user consent to verified publishers; compromised-account indicators (inbox rules, forwarding); `X-Forefront-Antispam-Report` and `Authentication-results` headers | [Illicit consent](https://learn.microsoft.com/en-us/defender-office-365/detect-and-remediate-illicit-consent-grants), [user consent](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/configure-user-consent), [compromised account](https://learn.microsoft.com/en-us/defender-office-365/responding-to-a-compromised-email-account), [message headers](https://learn.microsoft.com/en-us/defender-office-365/message-headers-eop-mdo) | Read |
| Microsoft 365 business 30-day trial, 300 GB, renews annually by default; card requirement not stated on the page | [Try or buy Microsoft 365](https://learn.microsoft.com/en-us/microsoft-365/commerce/try-or-buy-microsoft-365), dated 2026-04-23 | Read; card requirement and post-trial price **not verified** |
| Microsoft 365 Developer Program: E5 sandbox only for qualifying paths; not in government clouds | [Developer Program](https://learn.microsoft.com/en-us/office/developer-program/microsoft-365-developer-program), dated 2026-09-08 | Read |
| Check Point announced the Avanan acquisition (30 Aug 2021); Avanan described as an API solution | [Press release](https://www.checkpoint.com/press-releases/check-point-software-technologies-acquires-avanan/) | Read; completion notice not read. Current ownership shown by Check Point's own product pages and documentation |
| Current product name Email Security (Harmony Email & Collaboration); "API-based inline protection service"; supported apps (Exchange Online, Gmail, OneDrive, SharePoint, Google Drive, ShareFile, Dropbox, Box, Teams, Slack); modes Monitor only, Detect and Remediate (scan "10 seconds - 5 minutes"), Protect (Inline) with mail flow rules and connectors; journal rule; Microsoft permissions list including `Mail.ReadWrite` and send-as; manual mode needs fewer permissions | [Introduction](https://sc1.checkpoint.com/documents/Harmony_Email_and_Collaboration/Email_Security/Admin_Guide/Topics/introduction/introduction-to-Email-Security.html), [Email protection](https://sc1.checkpoint.com/documents/Harmony_Email_and_Collaboration/Email_Security/Admin_Guide/Topics/email-protection/email-protection.html), [Appendix A](https://sc1.checkpoint.com/documents/Harmony_Email_and_Collaboration/Email_Security/Admin_Guide/Topics/introduction-cp-manual-config-0365/appendix-a-avanan-manual-integration-with-office-365.html), [Step 4](https://sc1.checkpoint.com/documents/Harmony_Email_and_Collaboration/Email_Security/Admin_Guide/Topics/introduction-cp-manual-config-0365/step-4-journal-rule.html), [Step 8](https://sc1.checkpoint.com/documents/Harmony_Email_and_Collaboration/Email_Security/Admin_Guide/Topics/introduction-cp-manual-config-0365/step-8-connectors-protect-inline.html), [Step 9](https://sc1.checkpoint.com/documents/Harmony_Email_and_Collaboration/Email_Security/Admin_Guide/Topics/introduction-cp-manual-config-0365/step-9-transport-rules.html) (guide dated 15 October 2026) | Read; public, no login |
| Check Point plans: quote-only ("Get a Quote"), 14-day free trial mentioned; "without changing MX records"; Slack, Teams, Dropbox, Box | [Plans and packages](https://www.checkpoint.com/harmony/email-security/plans-and-packages/), [product page](https://www.checkpoint.com/harmony/email-security/) | Read. **No price, and nothing about who may buy**, was on these pages; the "sold only to businesses" claim is the maintainer's experience |
| Proofpoint Core Email Protection: "deploy via API or inline", SEG and API options, "without MX record changes" for API; deployment docs behind a login | [Product page](https://www.proofpoint.com/us/products/email-protection); [documentation site](https://help.proofpoint.com) redirected to a sign-in page | Product page read; documentation **not readable** |
| Mail-in-a-Box components, requirements, cost estimate (about $12 a month), ports, reverse DNS, Ubuntu 22.04, dedicated machine, home use not possible | [README](https://github.com/mail-in-a-box/mailinabox) (raw `README.md` on `main`), [setup guide](https://mailinabox.email/guide.html) | Read |
| DigitalOcean blocks SMTP ports 25, 465 and 587 on Droplets and Reserved IPs by default and recommends against self-hosting mail | [Why is SMTP blocked?](https://docs.digitalocean.com/support/why-is-smtp-blocked/) | Read; unblock procedure not found there |
| AWS blocks outbound port 25 on EC2 and Lambda by default; request removal per Region | [re:Post article](https://repost.aws/knowledge-center/ec2-port-25-throttle) | Read |
| DigitalOcean reserved IPv4: free while assigned, $5.00 a month unassigned; droplet billing per second capped at 672 hours | [Reserved IP pricing](https://docs.digitalocean.com/products/networking/reserved-ips/details/pricing/), [Droplet pricing](https://docs.digitalocean.com/products/droplets/details/pricing/) | Read |
| `ifconfig.co` and `api.ipify.org` answered an IPv4-only request with HTTP 200 (address not recorded) | `curl -4`, 2026-10-22 | Observed; any equivalent service works |
| `s-1vcpu-1gb` is $6 a month | [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json), retrieved 2026-10-21 | Read in this repository |
| Google sender requirements (SPF or DKIM; SPF, DKIM, DMARC for bulk over 5,000 a day; PTR; TLS; spam rate under 0.3%; one-click unsubscribe; DKIM 1024 bits or more) | [Google email sender guidelines](https://support.google.com/mail/answer/81126) | Read, including the IPv6 PTR statement and the IPv6 rejection example |
| Microsoft's high-volume sender requirements | Microsoft Tech Community announcement | Page did not render: **not verified** |
| Mailgun, Postmark, Amazon SES pricing figures quoted | [Mailgun](https://www.mailgun.com/pricing/), [Postmark](https://postmarkapp.com/pricing), [SES](https://aws.amazon.com/ses/pricing/) | Read the figures shown; not totaled; they change |
| Mailman DMARC mitigation rule | [Mailman 3 documentation](https://docs.mailman3.org/) (the page titled "DMARC mitigation" under Rules, in the Mailman core documentation, version 3.3.11b1) | Read |
| Proton: Switzerland, zero-access and end-to-end encryption, subject lines not end-to-end encrypted, custom domain on subscription plans | [Proton Mail](https://proton.me/mail), [encryption explained](https://proton.me/support/proton-mail-encryption-explained), [custom domain](https://proton.me/support/custom-domain) | Read |
| Tuta: Germany, own encryption scheme, metadata not encrypted, subject lines encrypted, local search | [Tuta security](https://tuta.com/security) | Read. Custom domain and pricing **not verified** |
| Lab output; DKIM cross-check against `dkimpy` 1.1.8 | Run on Linux, Python 3.13.5, `dnsmasq` 2.91, 2026-10-22 | Observed |
| OpenTofu validated and planned (flags off and on, placeholder token, nothing applied) | OpenTofu 1.12.6, `digitalocean/digitalocean` 2.x | Observed |
| That the sold-to-businesses-only experience, the LLC purchase, the Mail-in-a-Box history, the Mailgun relay, and the Proton and Tuta affiliations and use are the maintainer's | The maintainer's statements, 2026-10-22 | Not checkable here |

**Not verified, plainly:** every PowerShell and Exchange Online command; any Microsoft 365 tenant step; whether the trial asks for a card, and any price after it; Defender license totals; any API-driven product's price, terms of sale or eligibility; Proofpoint's deployment documentation; Microsoft's sender requirements; any provider's SMTP unblock procedure; legal and consent requirements for bulk mail; Tuta's custom-domain support and any Proton or Tuta price; the OpenTofu pieces against a real account (never applied); whether a reserved IP carries the reverse DNS; the contents of the maintainer's link page, which returned an error when fetched from the author's machine; the Ubuntu image slug in the droplet piece (est.); deleting a Microsoft 365 tenant; and any data-processing terms of any vendor named.

Next: [Reading order](Reading-Order.md).
