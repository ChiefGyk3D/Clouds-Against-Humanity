# Email security lab

The lesson is
[Email security: DNS records, email gateways with Microsoft 365, and API-driven cloud email security](../../docs/wiki/Email-Security-DNS-Gateways-and-API-Driven-Protection.md).
This folder holds only the code it runs. Nothing here is a product, and nothing here has been applied.

## `local/` (free, your own computer, no network)

| File | What it does |
|---|---|
| `mkmail.py` | Builds the whole fixture at run time into a private folder: two throwaway RSA keys (`openssl`), a fake DNS zone (`zone.json` and a `dnsmasq` config), thirteen synthetic `.eml` files, a manifest and a synthetic DMARC aggregate report. Nothing it makes is committed. |
| `dkimlite.py` | A teaching DKIM signer and verifier (RFC 6376, rsa-sha256, relaxed/relaxed). |
| `mailauth.py` | A teaching SPF (RFC 7208, with the 10-lookup and 2-void-lookup limits), DKIM and DMARC evaluator that reads the zone file or asks a local DNS server. |
| `triage.py` | Reads one message and prints a phishing triage worksheet. It never opens, renders or runs anything. |
| `dmarc_report.py` | Summarizes DMARC aggregate reports and refuses DOCTYPE and ENTITY declarations. |
| `smtpsink.py`, `smtpsend.py` | A loopback-only SMTP receiver that prints the conversation, and a sender whose envelope sender differs from its From header. |
| `positions.py` | A pure-computation toy that compares a gateway position and two API positions on invented messages. |

Python 3 and `openssl` only. Run the scripts from inside a private (mode 700) work folder, as the lesson shows.

## `cloud/` and `compose/` (optional, your own DigitalOcean account)

OpenTofu for a Mail-in-a-Box learning box, one folder per piece (`project`, `firewall`, `droplet`, `reserved-ip`, `dns`) and a `compose/` root that calls them all. **Every flag defaults to false, so `tofu plan` creates nothing.** The token is read from `DIGITALOCEAN_TOKEN` in your environment and is never a variable. Read the lesson's cost box and teardown section before you set any flag to true. The `labs/` directory is outside the project's cost gate on purpose ([`docs/cost.md`](../../docs/cost.md#the-labs-exemption-option-l1)); that makes it your bill, not the project's.

**The lab is IPv4-only on purpose.** The droplet disables IPv6, and the firewall's SSH source must be a single IPv4 address written `a.b.c.d/32` (an IPv6 range, a wider range or the whole internet is refused). Find yours with `curl -4 https://ifconfig.co` (PowerShell, est.: `Invoke-RestMethod -Uri https://ifconfig.co/ip`); any equivalent service works. If your network is IPv6-only or has IPv6 off, use a connection that has an IPv4 address or skip this path.

Outbound SMTP (ports 25, 465 and 587) is blocked on DigitalOcean droplets by default. A fresh address has no sending reputation. Send only to addresses you own.
