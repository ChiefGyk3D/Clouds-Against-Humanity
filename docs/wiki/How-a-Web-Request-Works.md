# How a web request works: DNS, TCP, TLS, HTTP and certificates

Side page to the start-from-zero pages. Read it after [Networking basics](Networking-Basics-for-This-Project.md) (core step 3), and before [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) if "TLS", "certificate" or "DNS" are only words to you. It does not repeat what a request and a response look like: [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) covers HTTP methods, status codes and headers, and this page links to it and goes deeper on the path underneath. Next: [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the free local lab was run once on Linux; everything else was not run.** On **2026-10-21** the author ran every Bash command in the free theory path on Linux, with OpenSSL 3.5.7, curl 8.21.0, `dig` and Python 3.13, and pasted trimmed output from that run. Two sets of commands were **not run**: the PowerShell and Windows equivalents (there was no Windows machine; they are written from Microsoft's and curl's documentation and marked **est.**), and the whole optional own-account path with two droplets (written from DigitalOcean's `doctl` documentation, never applied; run it expecting to fix something). Option names for `openssl` were checked against the OpenSSL 3.0 manual pages (the version Ubuntu 24.04 ships is **est.**) and option names for `curl` against the curl manual, both read on **2026-10-21**; see the [claims register](#claims-register). Output varies with your versions, your resolver and the date.

> **Prerequisites.** [Networking basics](Networking-Basics-for-This-Project.md) (addresses, ports, TCP, inbound and outbound) and a terminal ([Git from zero](Git-From-Zero.md) has a first look). [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) helps for the HTTP part but is not required. Nothing needs an account for the free path. About 90 minutes for the reading and the free lab (est.); the optional cloud path adds about an hour (est.).

## What you will be able to do

- Follow one HTTPS request from the name you typed to the page that appears: DNS, TCP handshake, TLS handshake, HTTP request and response, and say which of those a failure belongs to.
- Read a certificate: who it names, who signed it, when it expires, and say how a client decides to trust it (the chain of trust).
- Say in a sentence what a cache, a CDN, a reverse proxy and a load balancer each add.
- Build a tiny private certificate authority, issue a good certificate and an expired one, and see exactly what a client reports for each, on your own computer.
- Explain why clicking through a certificate warning defeats the check, and what an automated renewal and an expiry alert protect.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| DNS | [Networking basics](Networking-Basics-for-This-Project.md#dns-and-ntp-briefly) has one paragraph: names become addresses. | Who answers, what is cached, what a record is. |
| TLS and certificates | The Glossary has a TLS row; [Networking basics](Networking-Basics-for-This-Project.md#dns-and-ntp-briefly) says clocks matter to certificates. Enterprise identity names the PKI and the expiry failure. | What a certificate contains, how a chain is checked, and what a failure looks like. |
| HTTP | [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md#http-in-ten-minutes). | Nothing: read it there. Here HTTP is one step of four. |
| Proxy, load balancer, CDN | Not defined. | A sentence each, and where TLS ends. |

## What happens when you type a URL

You type `https://example.com/` and press Enter. The browser (the **client**) has a name and needs a page. Four things happen in order, and each one can fail on its own, with its own error.

```text
 1. DNS     "what address is example.com?"        -> an IP address
 2. TCP     open a connection to that address:443 -> a reliable pipe
 3. TLS     agree on keys, check the certificate  -> an encrypted pipe to the right name
 4. HTTP    GET / ... 200 OK + the page           -> the page
```

A fifth thing, **caching**, can short-circuit any step. The sections below take one step at a time. [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034) (DNS), [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293) (TCP), [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446) (TLS 1.3) and [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110) (HTTP) are the standards, if you want the exact words.

### Step 1: DNS, from a name to an address

Computers connect to addresses, not names. The **Domain Name System (DNS)** is the phone book that turns `example.com` into an IP address. Your computer does not know the answer, so it asks a **resolver** (usually run by your network or your internet provider, or a public one you chose). The resolver either answers from its **cache** or walks the hierarchy: it asks a root server which servers handle `com`, asks one of those which servers handle `example.com`, and asks one of those (the **authoritative** servers, run by whoever owns the name) for the address.

An answer is a **record**. The ones you will meet: `A` (a name to an IPv4 address), `AAAA` (to an IPv6 address), `CNAME` (this name is an alias for that name), `NS` (which servers are authoritative) and `MX` (where mail goes). Each record carries a **TTL** (time to live): the number of seconds a cache may keep it. Cache means the second lookup is faster and also that a changed record takes up to its TTL to reach everyone, which is why people lower a TTL before a move.

For who owns a name, how delegation works, the other record types, email records and running your own zone, see [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md).

DNS usually travels over UDP port 53 (and TCP when an answer is large), and normally in the clear. The project's baseline firewall allows exactly that outbound ([Networking basics](Networking-Basics-for-This-Project.md#what-a-firewall-does)).

### Step 2: TCP, a reliable connection

With an address, the client opens a **TCP** connection to port 443 (the port for HTTPS; see [Networking basics](Networking-Basics-for-This-Project.md#tcp-and-udp)). TCP does this with a **three-way handshake**: the client sends a SYN ("let us talk, my numbering starts here"), the server answers SYN-ACK ("agreed, and mine starts here"), and the client sends ACK ("received"). After that, both sides can send data that arrives complete and in order. The standard calls it the "three-way handshake" ([RFC 9293](https://www.rfc-editor.org/rfc/rfc9293)).

A refused connection (nobody listening), a silent drop (a firewall) and a timeout are all failures of this step. Your own machine may try an IPv6 address first and fall back to IPv4; the lab output below shows that happening on `localhost`.

### Step 3: TLS, an encrypted pipe to the right name

TCP gives a pipe; **TLS** (Transport Layer Security) makes it private and proves who is on the other end. The padlock is TLS. The steps (TLS 1.3, [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446)):

1. **ClientHello.** The client says which TLS versions and cipher suites it supports, sends its half of a key agreement, and includes the **server name** it wants (SNI, the Server Name Indication extension from [RFC 6066](https://www.rfc-editor.org/rfc/rfc6066)). The name is there because one address can host many sites, and the server needs to know which certificate to show. In the usual setup the name is visible to anyone watching the connection (est.; an extension that hides it exists and is not universal).
2. **ServerHello and certificate.** The server picks the options, sends its half of the key agreement, and sends its **certificate**: a signed statement "this public key belongs to this name". It proves it holds the matching private key by signing part of the handshake.
3. **Verify.** The client checks the certificate (next section). If any check fails, a careful client stops here and shows an error.
4. **Finished.** Both sides compute the same session keys from the key agreement and confirm with a Finished message. From now on everything is encrypted and tamper-evident.

In TLS 1.3 this takes one round trip before the client can send its request. What TLS gives you: **confidentiality** (others on the path cannot read it), **integrity** (they cannot change it unnoticed) and **server authentication** (you are talking to whoever holds the key for that name). What it does not give you: any statement that the site is honest, safe, or run by whom you think. A phishing site can have a perfectly valid certificate for its own name.

### Step 4: HTTP, the request and the response

Inside the encrypted pipe the client sends a plain **HTTP** request (`GET /` with headers, including `Host: example.com`) and the server sends a response (a status line such as `200 OK`, headers, and the body). That part is the subject of [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md#http-in-ten-minutes), including the status-code table. A short rule from there that matters here: **4xx means the request was wrong, 5xx means the server failed**. A TLS error is neither: the request never got that far.

### Caching, CDNs, proxies and load balancers, a sentence each

- **Caching:** keeping a copy of an answer so the question is not asked again: DNS records are cached by TTL, and web pages by the `Cache-Control` and `Last-Modified` headers; the lab shows a TTL counting down.
- **CDN (content delivery network):** many servers around the world that hold copies of a site's files, so a visitor is answered from a nearby copy; the example in the lab is served by one (`server: cloudflare` and a cache-hit header are visible in its response).
- **Reverse proxy:** a server that stands in front of the real servers, receives requests for them, and forwards them; it is a good place for TLS, logging and filtering. (A *forward* proxy is the other direction: it stands in front of clients.)
- **Load balancer:** a reverse proxy that spreads requests across several servers and stops sending to a failed one; it is often where **TLS termination** happens, meaning the encrypted connection ends at the balancer and the rest of the trip may or may not be encrypted again.

Each one can be another place a certificate is checked and another place a log line is written, which matters when you try to answer "where did this request go wrong?"

## Certificates and trust chains in plain language

A certificate is a signed note: *"this public key belongs to this name, valid between these two dates, signed by that issuer."* It is built on the key-pair idea from [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md#how-keys-work-without-the-math): the server holds a private key, the certificate publishes the public half, and anyone can check that a signature was made by the private key.

The fields worth knowing:

| Field | What it says | Where you will see it |
|---|---|---|
| Subject | A distinguished name such as `CN=example.com` (the CN is the common name). Older clients matched the URL against the CN; current ones use the SAN and ignore the CN when a SAN is present (est.; see [RFC 9525](https://www.rfc-editor.org/rfc/rfc9525)). | `subject=` in `openssl` and `curl -v` |
| Subject Alternative Name (SAN) | The names (and IP addresses) the certificate is valid for. **This is the field a client matches your URL against.** | `X509v3 Subject Alternative Name` |
| Issuer | Who signed it. | `issuer=` |
| Not before / not after | The validity window. | `notBefore=`, `notAfter=` |
| Public key and signature algorithm | The key the server proves it holds, and how the issuer signed. | `openssl x509 -text` |
| `basicConstraints` | Whether this certificate is a CA (`CA:TRUE`, allowed to sign other certificates) or an end-entity certificate (`CA:FALSE`). | `X509v3 Basic Constraints` |
| `keyUsage` | What the *key* may be used for, such as `digitalSignature` or `keyCertSign` (signing certificates, so a CA needs it). | `X509v3 Key Usage` |
| `extendedKeyUsage` | The *purposes* the certificate is meant for, such as `serverAuth` (a TLS server) or `clientAuth`. A separate extension from `keyUsage`. | `X509v3 Extended Key Usage` |
| `nameConstraints` | Only on a CA certificate: the names (DNS or IP) the CA may issue for. | `X509v3 Name Constraints` |

### Who vouches for the issuer: the chain of trust

A signature only helps if you trust the signer. So the client builds a **chain**:

1. The **leaf** (or end-entity) certificate is the one for `example.com`. It was signed by an **intermediate** CA.
2. The intermediate's certificate was signed by another intermediate, or directly by a **root** CA.
3. The root's certificate is signed by itself. The client does not check that signature; it checks whether it already trusts that root: the root is in its **trust store**, the list of roots that ship with the operating system or browser.

A **certificate authority (CA)** is an organization that signs certificates after checking that the requester controls the name. Roots are used rarely and kept very safe; intermediates do the daily signing, so a leaked intermediate can be revoked without replacing every root. The standard for all of this is X.509, profiled in [RFC 5280](https://www.rfc-editor.org/rfc/rfc5280).

When the client verifies a server, it checks, at least: every signature in the chain is good and ends at a trusted root; **every** certificate in the chain is inside its validity dates **according to the client's own clock**; the name in the URL matches a name in the leaf's SAN; and the certificate is meant for a TLS server (the `extendedKeyUsage` extension lists `serverAuth`; `keyUsage` is a separate extension about what the key may do, for example `digitalSignature`), and, for the CAs in the chain, that `basicConstraints` says `CA:TRUE`. It may also check whether a certificate has been revoked (est.; revocation checking differs a lot between clients, so do not assume it).

Two consequences that surprise people:

- **The clock that matters is the client's.** The server just sends the certificate. If the client's clock is wrong, a perfectly good certificate looks expired or "not yet valid". That is one of the reasons the baseline firewall allows UDP 123 (time sync) outbound: see [Networking basics](Networking-Basics-for-This-Project.md#dns-and-ntp-briefly). Changing the *server's* clock changes nothing the client checks.
- **A "self-signed" certificate is a root that nobody has agreed to trust.** It encrypts, but it proves nothing, which is why clients warn. The way to make a private system trustworthy is not to click through, it is to give the client the private CA's certificate on purpose, and nothing wider than that (the lab does this).

In practice public certificates come from CAs that automate issuing and renewing (the standard protocol is ACME, [RFC 8555](https://www.rfc-editor.org/rfc/rfc8555)), and **expiry** is the classic outage: nobody renewed it. The [enterprise identity page](Enterprise-Identity-and-Secrets-at-Scale.md#secrets-vaults-rotation-and-certificates) names the same failure at company scale.

## Where this shows up in this project

The connector droplets have no inbound rules and still work, because they make **outbound** connections. Follow one of them from boot, using only what the [Twingate](Twingate.md) and [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md) pages already say:

1. The connector needs the address of the Twingate controller by name. DNS is an outbound rule (TCP and UDP 53).
2. It opens TCP to port 443 (outbound rule) and does a TLS handshake. A TLS client checks the server's certificate against its trust store and the name it asked for; that this is exactly what the connector software does is Twingate's design, not documented on this wiki (est.).
3. It checks the date against its own clock, which is kept right by the outbound UDP 123 rule.
4. The connection then stays open; user traffic rides it back. The droplet never listened on a public port.

So the baseline outbound rules (53, 443, 80 for package mirrors, 123) are, in this lesson's words, DNS, the TLS connection, the package download and the clock. Nothing inbound is needed for any of them. That is the whole design from [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md), seen from the packet level.

## Free theory path: a lab on your own computer

Everything in this section runs on your own computer and costs nothing. The only third-party servers it touches are public sites you request exactly as a browser would, one request at a time. Every exercise follows four steps: **predict** (write down what you expect first), **do**, **check**, **undo**.

**Which track.** Commands are given for **Bash** (Linux, macOS Terminal, WSL, Git Bash) and **PowerShell** (Windows). Where a step is track-specific, it says so. On Windows, call `curl.exe`, not `curl`: in Windows PowerShell 5.1 `curl` is an alias for a different command (`Invoke-WebRequest`) that takes different options. You need `openssl`, `curl`, `dig` (Bash only; PowerShell uses `Resolve-DnsName` and both can use `nslookup`) and `python3`. On macOS the built-in `openssl` is LibreSSL and may lack options used below (est.): install OpenSSL from a package manager. Windows does not ship `openssl`; Git for Windows includes one and WSL gives you the Bash track (est.).

### Exercises on public sites (read only)

All of these are ordinary reads of `example.com`, a name meant for documentation and examples (est.; the same host shows the DNS, TCP, TLS and HTTP steps). One request each; do not loop.

#### Exercise 1: DNS, the answer and its TTL

**Predict.** How many addresses will `example.com` have? If you ask twice, a few seconds apart, will the TTL be the same or smaller the second time?

**Do (Bash).**

```bash
dig example.com A +noall +answer
sleep 3
dig example.com A +noall +answer
dig example.com NS +noall +answer
nslookup example.com
```

**Do (PowerShell).**

```powershell
Resolve-DnsName example.com -Type A
Start-Sleep -Seconds 3
Resolve-DnsName example.com -Type A
Resolve-DnsName example.com -Type NS
nslookup example.com
```

**Check.** On 2026-10-21 the Bash run answered with two `A` records, and the TTL column dropped between the two asks because the resolver was counting down a cached answer (trimmed; your addresses and numbers will differ):

```text
example.com.   129  IN  A   172.66.147.243
example.com.   129  IN  A   104.20.23.154
example.com.   126  IN  A   172.66.147.243
example.com.   126  IN  A   104.20.23.154
example.com.   86400  IN  NS  hera.ns.cloudflare.com.
```

Two addresses for one name is normal: many sites sit behind several. The `NS` records name the authoritative servers. `dig NS com +noall +answer` lists the servers one level up. `dig` also prints, with no `+noall`, the resolver it asked: that is your network's, not a public one, and you should not paste it into a public issue.

**Undo.** Nothing; a lookup changes nothing. (`dig +trace example.com` walks the hierarchy from the root, but it failed here behind the author's resolver, so it is left as an optional extra.)

#### Exercise 2: TCP, TLS and HTTP in one `curl -v`

**Predict.** In the verbose output, which comes first: the certificate, or the line `GET / HTTP/...`? Which step uses the name you typed, and which uses only the address?

**Do (Bash).**

```bash
curl -v https://example.com/ -o /dev/null
```

**Do (PowerShell).**

```powershell
curl.exe -v https://example.com/ -o NUL
```

**Check.** Read it top to bottom. Trimmed from the 2026-10-21 run (local address lines removed):

```text
* Host example.com:443 was resolved.
* IPv6: 2606:4700:10::ac42:93f3, 2606:4700:10::6814:179a
* IPv4: 172.66.147.243, 104.20.23.154
*   Trying [2606:4700:10::ac42:93f3]:443...
* Immediate connect fail ... Network is unreachable
*   Trying 172.66.147.243:443...
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
* TLSv1.3 (IN), TLS handshake, Certificate (11):
* TLSv1.3 (IN), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384 / ...
* Server certificate:
*   subject: CN=example.com
*   expire date: Dec 25 22:56:35 2026 GMT
*   issuer: C=US; O=SSL Corporation; CN=Cloudflare TLS Issuing ECC CA 3
* SSL certificate verified via OpenSSL.
> GET / HTTP/2
> Host: example.com
```

The DNS answer comes first (the `Host ... was resolved` line), then TCP (`Trying`), then the TLS handshake and certificate, and only then the HTTP request. Notice two things: this machine had no IPv6 route, so it fell back to IPv4 (the fallback described in step 2), and the `>` lines (what you sent) come after the certificate. Your curl version words these lines differently; the order is the lesson. The [`-w` options](https://curl.se/docs/manpage.html) can print the time each step took:

```bash
curl -s -o /dev/null -w 'dns=%{time_namelookup} tcp=%{time_connect} tls=%{time_appconnect} first_byte=%{time_starttransfer} total=%{time_total}\n' https://example.com/
```

The same text works in PowerShell with `curl.exe` and `-o NUL`. The 2026-10-21 run printed `dns=0.035 tcp=0.058 tls=0.103 first_byte=0.143 total=0.143` (seconds, cumulative: each number includes the ones before it). Subtract neighbors to see what each step cost; yours will differ.

**Undo.** Nothing.

#### Exercise 3: read a certificate chain

**Predict.** How many certificates will the server send: one, or more? Which one will have `example.com` as its subject?

**Do (Bash).**

```bash
echo | openssl s_client -connect example.com:443 -servername example.com -showcerts 2>/dev/null | grep -E "^ *[0-9] s:|^ *i:|Verification|Verify return"
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

**Do (PowerShell, est.).**

```powershell
'' | openssl s_client -connect example.com:443 -servername example.com 2>$null | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

**Check.** The first command lists the chain the server sent, each certificate's subject (`s:`) and issuer (`i:`). On 2026-10-21 there were four, and the issuer of each was the subject of the next, ending at a root:

```text
 0 s:CN=example.com
   i:C=US, O=SSL Corporation, CN=Cloudflare TLS Issuing ECC CA 3
 1 s:C=US, O=SSL Corporation, CN=Cloudflare TLS Issuing ECC CA 3
   i:C=US, O=SSL Corporation, CN=SSL.com TLS Transit ECC CA R2
 2 s:C=US, O=SSL Corporation, CN=SSL.com TLS Transit ECC CA R2
   i:C=US, O=SSL Corporation, CN=SSL.com TLS ECC Root CA 2022
 3 s:C=US, O=SSL Corporation, CN=SSL.com TLS ECC Root CA 2022
   i:C=GB, ST=Greater Manchester, L=Salford, O=Comodo CA Limited, CN=AAA Certificate Services
Verification: OK
```

Each line points at the next: leaf, intermediate, intermediate, root. (Why a fourth appears is the server's choice and your list may differ; est.) The second command prints the leaf: subject `CN=example.com`, SAN `DNS:example.com, DNS:*.example.com` (the `*` covers any single label), and a validity window of a little under three months (`notBefore` 2026-09-26, `notAfter` 2026-12-25 on the day of the run), which is typical of automated issuance. In a browser, click the padlock and open the certificate viewer to see the same fields.

> **Screenshot to take yourself:** your browser's certificate viewer for `example.com`.
> Capture: the Details or General tab showing the subject, issuer and validity dates.
> Look for: the same issuer and dates `openssl` printed.
> Redact: nothing from this public site; crop out browser profile names and bookmarks.

**Undo.** Nothing.

### The local lab: your own server and your own CA

Now the part you control. You will run a tiny web server on your own computer, once in plain HTTP and once with TLS, using a throwaway certificate authority you make yourself. Everything is bound to `127.0.0.1`, so nothing outside your computer can reach it.

**Set up the folder.**

```bash
mkdir -p ~/web-lab/site && cd ~/web-lab
echo "hello from the local test server" > site/index.html
```

```powershell
New-Item -ItemType Directory -Force $HOME\web-lab\site | Out-Null
Set-Location $HOME\web-lab
Set-Content -Path site\index.html -Value "hello from the local test server" -Encoding ascii
```

**Save three small files** in that folder with a plain-text editor (in Notepad choose "All files" so it does not add `.txt`). Their content is below. `serve.py` is the test server (about 20 lines, standard library only); it serves the `site` folder, and answers `/boom` with a deliberate `500` and `/old` with a `301`, so you can see more status codes than `200`. `srv.ext` says what the server certificate is for. `ca.cnf` is the minimum `openssl ca` needs to issue a certificate with dates you choose.

`serve.py`:

```python
# Throwaway local test server: python3 serve.py PORT [CERT KEY]
# Binds to 127.0.0.1 unless the BIND environment variable names another address.
import http.server, os, ssl, sys

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory="site", **k)
    def do_GET(self):
        if self.path == "/boom":      # a deliberate server-side failure
            self.send_error(500, "Deliberate test failure")
        elif self.path == "/old":     # a redirect, like a moved page
            self.send_response(301); self.send_header("Location", "/index.html"); self.end_headers()
        else:
            super().do_GET()

port = int(sys.argv[1])
srv = http.server.ThreadingHTTPServer((os.environ.get("BIND", "127.0.0.1"), port), Handler)
if len(sys.argv) == 4:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(sys.argv[2], sys.argv[3])
    srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
srv.serve_forever()
```

`srv.ext`:

```text
subjectAltName=DNS:localhost
basicConstraints=CA:FALSE
extendedKeyUsage=serverAuth
```

`ca.cnf`:

```text
[ca]
default_ca = lab
[lab]
database = ca-db/index.txt
serial = ca-db/serial
new_certs_dir = ca-db
certificate = ca.crt
private_key = ca.key
default_md = sha256
policy = any
unique_subject = no
[any]
commonName = supplied
```

#### Exercise 4: plain HTTP is readable

**Predict.** If you request a page over plain HTTP, can anyone on the path read the request? What will the server's status line say for a missing file, and for the `/boom` path?

**Do.** Open a **second terminal** window in the same folder and start the plain server there (leave it running):

```bash
python3 -I serve.py 8080
```

```powershell
python -I serve.py 8080
```

(On Windows `python` may be `py -3`, depending on how Python was installed.) Back in the first terminal:

```bash
curl -v http://localhost:8080/index.html
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/nope
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/boom
curl -sL -o /dev/null -w '%{http_code} %{url_effective} redirects=%{num_redirects}\n' http://localhost:8080/old
```

In PowerShell use `curl.exe` and `-o NUL` for `-o /dev/null`.

**Check.** The verbose output shows your request in plain text (`> GET /index.html HTTP/1.1`, `> Host: localhost:8080`) and the response (`< HTTP/1.0 200 OK`, a `Server:` header, the body `hello from the local test server`). Anyone who can see the network path would see these same bytes. The next three commands print `404`, `500` and `200 http://localhost:8080/index.html redirects=1`: a client error (the path is wrong), a server error (the server failed), and a redirect that `-L` followed. Also look at the `Trying [::1]:8080... Connection refused` line: curl tried IPv6 first, nobody listened there, and it fell back to `127.0.0.1`. The status codes are the same ones in the [APIs and tokens table](APIs-and-Tokens-From-Zero.md#the-parts-of-a-response).

**Undo.** Press Ctrl+C in the second terminal to stop the server.

#### Exercise 5: build a private CA and a server certificate

**Predict.** If you create a certificate signed by your own CA and your computer has never heard of that CA, will `curl` accept it?

**Do (Bash).**

```bash
# 1. The throwaway CA: valid 2 days, and allowed to vouch for the name localhost only.
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes \
  -keyout ca.key -out ca.crt -subj "/CN=Throwaway Test CA" -days 2 \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign" \
  -addext "nameConstraints=critical,permitted;DNS:localhost"
# 2. The server's key and a signing request (what a real server sends a CA).
openssl req -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes \
  -keyout srv.key -out srv.csr -subj "/CN=localhost"
# 3. The CA signs it: valid 1 day, for the names in srv.ext.
openssl x509 -req -in srv.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 1 -extfile srv.ext -out srv.crt
openssl verify -CAfile ca.crt srv.crt
```

**Do (PowerShell).** The same three `openssl` commands, joined on one line each (the backtick is PowerShell's line continuation, but a single line is simpler and safe):

```powershell
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout ca.key -out ca.crt -subj "/CN=Throwaway Test CA" -days 2 -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign" -addext "nameConstraints=critical,permitted;DNS:localhost"
openssl req -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout srv.key -out srv.csr -subj "/CN=localhost"
openssl x509 -req -in srv.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 1 -extfile srv.ext -out srv.crt
openssl verify -CAfile ca.crt srv.crt
```

(In Git Bash, the leading `/` of `-subj "/CN=..."` can be rewritten as a Windows path; if so, use `MSYS_NO_PATHCONV=1` before the command, or use PowerShell. est.)

**Check.** The last command prints `srv.crt: OK`. See what you made:

```bash
openssl x509 -in srv.crt -noout -subject -issuer -dates -ext subjectAltName
```

The subject is `CN=localhost`, the issuer is `CN=Throwaway Test CA`, the window is one day, and the SAN is `DNS:localhost` (the SAN, not the CN, is what the client matches). `openssl x509 -in srv.crt -noout -ext extendedKeyUsage,basicConstraints` shows the purpose `TLS Web Server Authentication` (that is `serverAuth`) and `CA:FALSE`, from `srv.ext`; `-in ca.crt -noout -ext keyUsage,basicConstraints,nameConstraints` shows the CA side. Three details to notice. The CA's `nameConstraints` extension limits it to `localhost` ([RFC 5280, section 4.2.1.10](https://www.rfc-editor.org/rfc/rfc5280)): even if someone stole `ca.key`, certificates for other names would fail verification on a client that trusts this CA. (Try it if you like: sign a certificate whose SAN is `DNS:example.com`; `openssl verify` reports `permitted subtree violation`.) The CA is valid for only two days, so it expires by itself. And the server's private key `srv.key` never left your folder, which is how real issuing works: only the signing request travels.

**Undo.** Nothing to undo yet; the whole lab is removed at the end.

#### Exercise 6: trust the CA on the client only, then connect

**Predict.** Run `curl` against the TLS server with no CA given, then with your CA given. Which one succeeds, and which TLS step does the first one fail at?

**Do.** In the second terminal start the TLS server (Ctrl+C the plain one first if it is still running):

```bash
python3 -I serve.py 8443 srv.crt srv.key
```

```powershell
python -I serve.py 8443 srv.crt srv.key
```

In the first terminal:

```bash
curl -s -o /dev/null -w 'status=%{http_code}\n' https://localhost:8443/
curl -s -o /dev/null -w 'status=%{http_code} verify=%{ssl_verify_result}\n' --cacert ca.crt https://localhost:8443/
echo | openssl s_client -connect localhost:8443 -servername localhost -CAfile ca.crt -verify_return_error -verify_hostname localhost 2>&1 | grep -E "verify|Verif|depth|Protocol|Cipher is"
```

PowerShell: use `curl.exe` and `-o NUL`; for the third command use `'' | openssl s_client ... 2>&1 | Select-String 'verify|Verif|depth|Protocol|Cipher is'` (est.). On Windows, if `curl.exe` reports a revocation-check error such as `CRYPT_E_NO_REVOCATION_CHECK`, that is Windows' certificate library, not the lab; the `openssl s_client` command is the reliable check for the rest of this page (est.).

**Check.** The first command prints `status=000` and exits with code 60, and `curl` without `-s` explains: `SSL certificate OpenSSL verify result: unable to get local issuer certificate (20)`. That is the chain check in step 3 failing: the client has no trust anchor for your CA. The second prints `status=200 verify=0`. The third prints `Verification: OK` and `Verified peername: localhost`, `Protocol: TLSv1.3`, and the chain with `depth=1 CN=Throwaway Test CA` and `depth=0 CN=localhost`.

You gave the CA to **one command** with `--cacert`. You did **not** add it to your operating system's trust store, and you should not: anything in that store is trusted for every site, so a leaked CA key would let someone impersonate any website to your computer. A trust decision should be as narrow as the purpose, and that is what the name constraint and the two-day life are for as well.

**Undo.** Nothing; `--cacert` changed no setting.

#### Exercise 7: the name must match

**Predict.** The certificate is for `localhost`. Your server is also reachable as `127.0.0.1`. Will the certificate be accepted when you connect to the number?

**Do.**

```bash
curl --cacert ca.crt https://127.0.0.1:8443/
```

**Check.** `curl: (60) SSL: no alternative certificate subject name matches target ipv4 address '127.0.0.1'`. The chain is fine; the name check failed, because a client matches the URL's host against the SAN list ([RFC 9525](https://www.rfc-editor.org/rfc/rfc9525) describes how). Same server, same key, different name, different answer. This is the usual error when someone connects to a server by its IP address instead of its name.

**Undo.** Nothing.

## Optional: the same lab across a real network (your own account)

This path puts the server and the client on two machines with a real network between them. It is optional. The free path above teaches all the concepts; this one adds a firewall that visibly drops traffic and a name check against a private IP address. It uses **your own** cloud account and **your own** bill: the lessons are free forever, the cloud usage is yours. Read the cost and the teardown first.

> **Status of this path: written from the `doctl` documentation, never run.** Flags were checked against the `doctl` reference pages on 2026-10-21 (listed in the claims register). Whether a tag-sourced firewall rule matches traffic over the private network exactly as written is **est.**; if the client cannot reach the server, check that first.

### Cost and teardown (read first)

- **Cost.** Two droplets of size `s-1vcpu-1gb`. [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json) (retrieved 2026-10-21) lists that size at $6 a month each, so **up to $12 a month at list price while both exist**; see [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) for how the project prices droplets. DigitalOcean's pricing page (read 2026-10-21) says these plans are billed per second with a 60-second minimum, capped at 672 hours a month, and that **a powered-off droplet is still billed: destroying it ends billing**. I did not read the hourly rate, so I give no per-hour figure. Check region and size availability in your own account first, as `cost.md` explains.
- **Never leave them running.** Set a calendar reminder for one hour from now.
- **Teardown** (the commands are listed again at the end, with the proof):

```bash
doctl compute droplet delete web-lab-client web-lab-server --force
doctl compute firewall list --format ID,Name        # note the two web-lab ids
doctl compute firewall delete FIREWALL_ID_1 FIREWALL_ID_2 --force
doctl vpcs delete VPC_ID --force
```

- **Data rules.** No real data goes on these machines. The certificates are throwaway. Nothing here uses a token beyond the one `doctl` already holds; make that token as narrow as the [identity page](Identity-Secrets-and-Zero-Trust-Basics.md) and the [secrets page](Doppler-and-Secrets.md) teach, and revoke it afterwards if you made it just for this.

### The design

```text
  your laptop ──ssh (only from your /32)──► client droplet ──ssh and TCP 8443 (private)──► server droplet
                                              public IP, inbound: your /32 on 22         public IP, inbound: NOTHING from the internet
                                                                                        both sit in one private VPC (10.99.0.0/24 here)
```

- **Client droplet.** Reachable by SSH only from **your own current public address as a /32** (one address). Never `0.0.0.0/0`. This rule is removed when the firewall is deleted at teardown.
- **Server droplet.** Its firewall has **no inbound rule from the internet at all**. It accepts SSH and port 8443 only from droplets carrying the `web-lab-client` tag. It has no outbound rules, since it never starts a connection (replies to allowed inbound connections still work, as the [stateful firewall](Networking-Basics-for-This-Project.md#inbound-outbound-and-why-the-direction-matters) description explains). You reach it by SSH **through** the client, using it as a jump host. No browser is needed; the browser warning is the free path's job.
- **The certificate.** The server makes its own key and a signing request; your laptop's throwaway CA (one that may only name addresses in the lab's private range) signs it; the client trusts that CA with `--cacert` and nowhere else.

### Steps

Placeholders: replace `203.0.113.7` with your own current public address (a documentation address, not yours). Home addresses change, and behind carrier-grade NAT ([CGNAT](Zero-Trust-at-Home-Two-Connectors-and-Failover.md#vpn-versus-ztna-under-real-residential-conditions)) your visible address is shared with other households, so a /32 is wider than it looks: if you are behind CGNAT, do not use this path from that connection. Find your address with your router or a what-is-my-address page, once.

```bash
export REGION=tor1 SIZE=s-1vcpu-1gb IMAGE=ubuntu-24-04-x64
export MY_IP=203.0.113.7
doctl compute ssh-key list --format ID,Name,FingerPrint      # pick the key you use; note its ID
export KEY_ID=YOUR_KEY_ID

# 1. A private network just for this lab. Pick a range that does not overlap yours.
doctl vpcs create --name web-lab --region "$REGION" --ip-range 10.99.0.0/24
doctl vpcs list --format ID,Name --no-header                  # note the web-lab id
export VPC_ID=YOUR_VPC_ID

# 2. The two droplets, tagged so the firewalls can name them.
doctl compute droplet create web-lab-server --region "$REGION" --size "$SIZE" --image "$IMAGE" \
  --vpc-uuid "$VPC_ID" --ssh-keys "$KEY_ID" --tag-names web-lab-server --wait
doctl compute droplet create web-lab-client --region "$REGION" --size "$SIZE" --image "$IMAGE" \
  --vpc-uuid "$VPC_ID" --ssh-keys "$KEY_ID" --tag-names web-lab-client --wait

# 3. The firewalls, attached by tag. A new droplet is open until these exist: do this at once.
doctl compute firewall create --name web-lab-client --tag-names web-lab-client \
  --inbound-rules "protocol:tcp,ports:22,address:${MY_IP}/32" \
  --outbound-rules "protocol:tcp,ports:22,tag:web-lab-server protocol:tcp,ports:8443,tag:web-lab-server"
doctl compute firewall create --name web-lab-server --tag-names web-lab-server \
  --inbound-rules "protocol:tcp,ports:22,tag:web-lab-client protocol:tcp,ports:8443,tag:web-lab-client"

# 4. The addresses you need.
export CLIENT_PUB=$(doctl compute droplet get web-lab-client --format PublicIPv4 --no-header)
export SERVER_PUB=$(doctl compute droplet get web-lab-server --format PublicIPv4 --no-header)
export SERVER_PRIV=$(doctl compute droplet get web-lab-server --format PrivateIPv4 --no-header)
```

In PowerShell write `$env:REGION = "tor1"` style assignments and `$CLIENT_PUB = (doctl compute droplet get web-lab-client --format PublicIPv4 --no-header)`; the `doctl` flags are identical (est.). Run the lines one at a time. The tag in a rule is written `tag:web-lab-client`, the address form is `address:...`, and several rules are separated by a space inside one quoted string, as the `doctl` reference shows.

**Make the lab CA for the private range** (on your laptop, in `~/web-lab`):

```bash
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes \
  -keyout cloud-ca.key -out cloud-ca.crt -subj "/CN=Throwaway Cloud CA" -days 2 \
  -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign" \
  -addext "nameConstraints=critical,permitted;IP:10.99.0.0/255.255.255.0"
```

**Get a signing request from the server** by logging in to it *through* the client. The first connection to each machine asks you to accept its host key; that prompt is the SSH version of the trust question this page is about, and for a machine you just made, accepting is reasonable (an unexpected change later is not).

```bash
ssh -J root@"$CLIENT_PUB" root@"$SERVER_PRIV"
```

You are now on the server (a Bash shell, whichever track your laptop uses). Run:

```bash
mkdir -p site && echo "hello from the lab server" > site/index.html
openssl req -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout srv.key -out srv.csr -subj "/CN=lab-server"
exit
```

Back on the laptop, copy the new `serve.py` and the request in, sign, and copy the certificate and the CA out:

```bash
scp -J root@"$CLIENT_PUB" serve.py root@"$SERVER_PRIV":
scp -J root@"$CLIENT_PUB" root@"$SERVER_PRIV":srv.csr cloud-srv.csr
printf 'subjectAltName=IP:%s\nbasicConstraints=CA:FALSE\nextendedKeyUsage=serverAuth\n' "$SERVER_PRIV" > cloud-srv.ext
openssl x509 -req -in cloud-srv.csr -CA cloud-ca.crt -CAkey cloud-ca.key -CAcreateserial \
  -days 1 -extfile cloud-srv.ext -out cloud-srv.crt
scp -J root@"$CLIENT_PUB" cloud-srv.crt root@"$SERVER_PRIV":srv.crt
scp cloud-ca.crt root@"$CLIENT_PUB":
```

PowerShell: the `printf` line becomes `Set-Content cloud-srv.ext -Encoding ascii -Value "subjectAltName=IP:$SERVER_PRIV","basicConstraints=CA:FALSE","extendedKeyUsage=serverAuth"`; the rest is the same (the Windows OpenSSH client provides `ssh` and `scp`, est.).

**Start the server on its private address only**, then test from the client:

```bash
ssh -J root@"$CLIENT_PUB" root@"$SERVER_PRIV" "BIND=$SERVER_PRIV nohup python3 -I serve.py 8443 srv.crt srv.key > serve.log 2>&1 < /dev/null &"
ssh root@"$CLIENT_PUB"
```

On the client:

```bash
SERVER_PRIV=THE_PRIVATE_ADDRESS_YOU_NOTED
curl -sv --cacert cloud-ca.crt https://$SERVER_PRIV:8443/ 2>&1 | grep -E "subject|issuer|expire|verified|HTTP/"
echo | openssl s_client -connect $SERVER_PRIV:8443 -CAfile cloud-ca.crt -verify_return_error -verify_ip $SERVER_PRIV 2>&1 | grep -E "Verif|Protocol"
exit
```

**Prove the server is closed to the internet** from your laptop. Both requests should time out (curl exit code 28), because the firewalls drop the packets silently ([a closed port refuses, a firewall stays silent](Networking-Basics-for-This-Project.md#ports-and-listening)):

```bash
curl --connect-timeout 5 -sS https://$SERVER_PUB:8443/ ; echo "exit=$?"
curl --connect-timeout 5 -sS https://$CLIENT_PUB:8443/ ; echo "exit=$?"
```

Then do the **Break** step of the mini-loop below on these machines: copy `ca.cnf` to `cloud-ca.cnf`, change its `certificate` and `private_key` lines to `cloud-ca.crt` and `cloud-ca.key`, issue an expired certificate for `cloud-srv.csr` with `-extfile cloud-srv.ext` and the past dates, copy it to the server as `srv.crt`, restart the server, and run the `s_client` command from the client. Then **tear down**.

### Prove it is gone

```bash
doctl compute droplet list
doctl compute firewall list
doctl vpcs list
```

Read-only; the droplet and firewall lists should show nothing named `web-lab`. Billing data lags: look at the billing page again tomorrow (the habit in the [teardown checklist](Teardown-Checklist.md#3-prove-zero-billable-resources)). Delete the copies of `cloud-ca.key` and `cloud-ca.crt` on your laptop, remove the two lab droplets' entries from `~/.ssh/known_hosts` if you want a tidy file, and revoke any token you made for this.

## Build, break, detect, evade, defend

A small loop in the local lab (add the cloud path if you took it). Local and throwaway: no real systems, no real targets.

**Build.** You already did: a CA that can only name `localhost`, a server certificate it signed, and a client that trusts that CA for one command.

**Break.** Issue a second certificate for the same server key that has **already expired**. You do not move any clock. `openssl ca` lets the issuer choose the dates, so choose dates in the past:

```bash
mkdir ca-db; : > ca-db/index.txt; echo 1000 > ca-db/serial
openssl ca -batch -config ca.cnf -in srv.csr -out old.crt -notext \
  -startdate 20200101000000Z -enddate 20200102000000Z -extfile srv.ext
openssl x509 -in old.crt -noout -dates
```

```powershell
New-Item -ItemType Directory ca-db | Out-Null
New-Item ca-db\index.txt | Out-Null
Set-Content ca-db\serial 1000 -Encoding ascii
openssl ca -batch -config ca.cnf -in srv.csr -out old.crt -notext -startdate 20200101000000Z -enddate 20200102000000Z -extfile srv.ext
openssl x509 -in old.crt -noout -dates
```

The last line prints `notBefore=Jan  1 00:00:00 2020 GMT` and `notAfter=Jan  2 00:00:00 2020 GMT`. Stop the TLS server (Ctrl+C) and start it with the expired certificate (it is signed for the same key, so `srv.key` still matches):

```bash
python3 -I serve.py 8443 old.crt srv.key
```

(A bare self-signed certificate would also warn, but for a different reason, which would hide the lesson; that is why you built a CA first and trusted it, so the only fault left is the date.)

**Detect.** From the first terminal:

```bash
curl --cacert ca.crt https://localhost:8443/
echo | openssl s_client -connect localhost:8443 -servername localhost -CAfile ca.crt -verify_return_error 2>&1 | grep -E "verify error|NotAfter|Verification error|Verify return"
```

`curl` fails with `SSL certificate OpenSSL verify result: certificate has expired (10)` and exits with code 60. `openssl s_client` prints `verify error:num=10:certificate has expired`, the chain with `NotAfter: Jan  2 00:00:00 2020 GMT`, and `Verify return code: 10 (certificate has expired)`. Two more detections you can script. First, `-checkend` answers "will this expire within N seconds?" through its exit code, which is what a monitor needs:

```bash
openssl x509 -in srv.crt -noout -checkend 3600; echo "exit=$?"      # 0: not within an hour
openssl x509 -in srv.crt -noout -checkend 172800; echo "exit=$?"    # 1: will expire within two days
```

Second, `-attime` changes the time the **verifier** uses, not the system clock, so you can ask "what would a client say tomorrow?" without touching anything:

```bash
openssl verify -CAfile ca.crt -attime $(( $(date +%s) + 129600 )) srv.crt
```

```powershell
openssl verify -CAfile ca.crt -attime ([DateTimeOffset]::UtcNow.AddHours(36).ToUnixTimeSeconds()) srv.crt
```

(`-attime` takes Unix seconds. 129,600 seconds is 36 hours; the server certificate lasts one day and the CA two, so the result is `error 10 ... certificate has expired` on the leaf only, with the CA still valid.) This is also the proof that the **client's** clock decides: the verifier alone produced the failure, and the server's clock played no part.

**Evade, in words only.** The way people "make the error go away" is `curl -k` (or `--insecure`), or clicking "proceed anyway" in a browser. Try it on your own expired server:

```bash
curl -sk -o /dev/null -w 'status=%{http_code} verify=%{ssl_verify_result}\n' https://localhost:8443/
```

You get `status=200`: the connection works, the check failed, and the flag told the client to carry on regardless. Nothing in the server's log changed, and nothing marks the response as untrusted. That is the problem: with the check off, an attacker who sits on the path with *any* certificate looks exactly like the real server. The warning is the only thing the system had to say that something was wrong. A second family of evasions is quieter and more dangerous: adding an attacker's or a leaked CA to a trust store, which is why the lab's CA is given to one command, is name-constrained, and expires in two days. This lesson does not show a working attack against anyone else's system, and none is needed to understand the defense.

**Defend.**

- **Automate renewal.** Use a CA and a client that renew by protocol (ACME, [RFC 8555](https://www.rfc-editor.org/rfc/rfc8555)), with short lifetimes, so renewal is routine rather than an annual scramble.
- **Alert on expiry before it happens.** Run the `-checkend` check from a scheduled job against every certificate you own, with a warning window longer than your renewal window, and send the failure to a person. This project's equivalent for secrets is the secret-expiry calendar in the [Roadmap schedule](Roadmap.md#schedule).
- **Keep clocks right.** Time sync (UDP 123 in this project's firewall) is part of certificate security.
- **Never switch the check off to get green.** Fix the certificate, the name or the CA the client trusts.
- **Trust narrowly.** One CA per purpose, constrained to the names it needs, with a short life, handed to the client that needs it and no others.
- **Know your inventory.** The enterprise failure is the certificate nobody remembered: see [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md#secrets-vaults-rotation-and-certificates).

**Undo (the whole lab).** Press Ctrl+C in the second terminal, then delete the folder:

```bash
cd ~ && rm -rf ~/web-lab
```

```powershell
Set-Location $HOME; Remove-Item -Recurse -Force $HOME\web-lab
```

The lab left nothing else behind: no setting changed, nothing was added to a trust store, and the CA key was in that folder.

## Common mistakes

| Symptom | Most likely step | What to check |
|---|---|---|
| `Could not resolve host` | DNS | The name is spelled right; your resolver is reachable; `dig` or `Resolve-DnsName` for the name. |
| `Connection refused` (immediate) | TCP | Nobody is listening on that port, or you are on the wrong address. |
| `Connection timed out` (a wait, then nothing) | TCP | A firewall is dropping the packets, or the address is wrong. |
| `unable to get local issuer certificate (20)` | TLS, trust | The client does not trust the issuer: missing intermediate on the server, or a private CA not given to the client. |
| `certificate has expired (10)` | TLS, dates | Check `notAfter`, and the **client's** clock. |
| `no alternative certificate subject name matches` | TLS, name | You connected by a name or address the certificate does not list. |
| `404` or `500` after a clean handshake | HTTP | The network and TLS worked; the problem is the request (4xx) or the server (5xx). |

## Claims register

All read-only requests; retrieved 2026-10-21 unless stated.

| Claim | Source | Status |
|---|---|---|
| The `openssl` options used (`req -x509 -newkey -nodes -keyout -addext -subj -pkeyopt`, `x509 -req -CA -CAkey -CAcreateserial -extfile -days -checkend -noout -ext -dates -subject -issuer`, `ca -batch -config -startdate -enddate -notext -extfile`, `verify -CAfile -attime`, `s_client -connect -servername -CAfile -verify_return_error -verify_hostname -verify_ip -showcerts`) | OpenSSL 3.0 manual pages: [s_client](https://docs.openssl.org/3.0/man1/openssl-s_client/), [x509](https://docs.openssl.org/3.0/man1/openssl-x509/), [req](https://docs.openssl.org/3.0/man1/openssl-req/), [ca](https://docs.openssl.org/3.0/man1/openssl-ca/), [verify](https://docs.openssl.org/3.0/man1/openssl-verify/), [verification options](https://docs.openssl.org/3.0/man1/openssl-verification-options/) | Read: every option name is on its page. Behavior shown was run on OpenSSL 3.5.7, not 3.0 |
| The `curl` options and `-w` variables used (`-v`, `-s`, `-o`, `-L`, `-k`/`--insecure`, `--cacert`, `--connect-timeout`, `http_code`, `ssl_verify_result`, `time_namelookup`, `time_connect`, `time_appconnect`, `time_starttransfer`, `url_effective`, `num_redirects`) and exit codes 28 and 60 | [curl manual](https://curl.se/docs/manpage.html) | Read. Run on curl 8.21.0 |
| `curl.exe` needs to be named on Windows; Schannel revocation behavior; Git Bash path rewriting; macOS `openssl` is LibreSSL; Windows `openssl` availability; PowerShell piping of PEM text | General knowledge | Not verified: **est.** |
| `Resolve-DnsName` takes `-Name`, `-Type`, `-Server`, `-DnsOnly` | [Microsoft Resolve-DnsName reference](https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname) | Option names read; not run |
| Name constraints extension limits names in the certification path | [RFC 5280, section 4.2.1.10](https://www.rfc-editor.org/rfc/rfc5280) | Read; behavior also run (`permitted subtree violation`) |
| TCP "three-way handshake"; the TLS 1.3 handshake and 1-RTT mode; SNI as `server_name`; DNS TTL as a cache time limit | [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293), [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446), [RFC 6066](https://www.rfc-editor.org/rfc/rfc6066), [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034) | Phrases found in the text; the narrative here is a summary, not a quote |
| Whether the server name is hidden from a path observer | General knowledge | **est.** |
| `doctl` commands and flags used: `vpcs create/list/delete`, `compute droplet create/get/delete/list`, `compute firewall create/delete/list`, `compute ssh-key list` | [doctl reference](https://docs.digitalocean.com/reference/doctl/reference/) pages for each | Flags read (`--vpc-uuid`, `--tag-names`, `--inbound-rules`, `--outbound-rules`, `--ssh-keys`, `--wait`, `--force`, `--no-header`, `--format`); never run |
| Rule sources can be `address` or `tag`; several rules go in one quoted, space-separated string; no outbound rule means none allowed | doctl firewall create reference (first two); the last is general knowledge | First two read; last **est.** |
| Bundled CPU droplets are billed per second, 60 second minimum, capped at 672 hours a month; powered-off droplets are still billed; destroy to stop billing | [Droplet pricing](https://docs.digitalocean.com/products/droplets/details/pricing/) | Read |
| `s-1vcpu-1gb` is $6 a month | `docs/cost-prices.json`, retrieved 2026-10-21 | Read in this repository |
| Ubuntu 24.04 cloud image includes `python3`, `openssl` and `curl` | General knowledge | **est.**; check on the droplet before relying on it |
| The `example.com` outputs (addresses, TTL, issuer names, dates, headers) | One normal request each to `example.com`, 2026-10-21 | Observed; they change |

Not verified, plainly: the whole PowerShell track; macOS; the cloud path from start to finish; `-attime` and `nameConstraints` behavior on OpenSSL 3.0 (they were run on 3.5.7); whether the `tor1` region offers `s-1vcpu-1gb` to your account (the repository records it for its own account).

Next: [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md), core step 4 on the [Reading order](Reading-Order.md) page.
