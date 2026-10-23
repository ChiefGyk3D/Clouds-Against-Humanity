# Rate limiting at every layer: deciding what to count, and where

Lesson D4, the last of four lessons on network and host defense. Read it after [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) and [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md), because it uses their words (NAT, firewall, `429`, token, scope). It is written to be read after [How a web request works](How-a-Web-Request-Works.md) too, since that page names the CDN, the proxy and the load balancer that this page tells apart. The other three lessons in the track are [Packet filters compared: iptables, nftables, UFW and pf](Packet-Filters-Compared-iptables-nftables-ufw-pf.md), [IDS and IPS: Snort and Suricata](IDS-and-IPS-Snort-and-Suricata.md) and [File integrity and alerting: Tripwire, AIDE and Wazuh](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md). They were written at the same time as this one, so those three links, and the link to the WordPress lesson below, **may not resolve until they are merged**. This page does not depend on them.

Next: [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the algorithm demos, the Nginx container lab, the namespace firewall lab and the per-key quota demo were run on Linux; the PowerShell, Docker, macOS and Windows versions, the Cloudflare rule and the DNS, HAProxy and fail2ban snippets were not run.** On **2026-10-22** the author ran every Bash and Python command in the free path on a Debian-based Linux machine with Python 3.13, curl 8.21.0, Podman 5.4.2 (rootless), the `nginx:1.30.6-alpine` image and nftables 1.1.3, and pasted trimmed output from those runs. **Not run:** every PowerShell script (there was no PowerShell on the machine; they are written from Microsoft's documentation and marked **est.**), anything on Docker, Docker Desktop, macOS or Windows, the optional own-account path, and the configuration snippets for HAProxy, BIND, Unbound and fail2ban (they are read from each project's manual and are examples of shape, not tested setups). Vendor and standards claims were read on **2026-10-22**; the [claims register](#claims-register) says what was read and what was run. Anything not in that register is general knowledge and marked **est.** where it matters. Rate limiting is a place where products change plan limits and defaults often, so treat every number taken from a vendor page as a snapshot.

> **Prerequisites.** A terminal and `curl` ([The terminal and your first script](Terminal-and-Your-First-Script.md)); Python 3 for the demos. For the Nginx lab, Podman or Docker on a machine you own. For the namespace lab, Linux. You do not need an account, a domain or any money. About 2 hours for the reading and the free exercises (est.).

## What you will be able to do

- Say why a service limits how fast it is used, and name the five reasons: abuse, password guessing, scraping, cost, and protecting a weak backend.
- Explain fixed window, sliding window, token bucket and leaky bucket in plain words, run all four, and say which one allows a doubled burst at a window boundary.
- Explain why the hardest question is not "how many" but **what to count by** (address, account, token, session, network, path), and how shared NAT, IPv6 prefixes, proxies and the `X-Forwarded-For` header break per-address limits.
- Say, for DNS, the CDN edge, the load balancer, the reverse proxy, the application, the login endpoint, the API, the database pool, the host kernel and the upstream network, what that layer can see, what it cannot, what it is good at limiting and how it fails.
- Read and send `429 Too Many Requests` and `Retry-After`, and write a client that backs off politely.
- Spoof `X-Forwarded-For` against a deliberately naive limiter on your own machine, and fix it by trusting the header only from the proxy.
- Put a rate limit in a private network namespace with nftables and iptables, and watch the kernel's SYN cookie counters.
- Say what a distributed attack does to per-address limits, why fail-open and fail-closed both cost something, and what to log so a limit is not a silent outage.
- Run Build, Break, Detect, Evade, Defend on a limiter, then flip the board.

The maintainer's words for this topic were: "rate limiting requires, like, we need to think thoroughly at each level." That is the shape of the page. It is not a recipe with numbers to copy. It is a way to ask the same four questions at every layer: what can this layer see, what should it count, what happens to a real person when it says no, and what happens to the rest of the system when it fails.

## What the wiki already says (and the gap)

I searched the wiki before writing this page.

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| A rate limit is a cap on requests in a time window, answered with `429` | [APIs and tokens: rate limits and pagination](APIs-and-Tokens-From-Zero.md#rate-limits-and-pagination) is one paragraph and the `Retry-After` row of a header table. | How a limiter works inside, what it counts, and what the client should do on a `429`. |
| Rate limiting and bot management at concept level, plus a login limit in a lab | The WordPress at scale lesson ([WordPress at scale: CDN, WAF and CI](WordPress-at-Scale-CDN-WAF-and-CI.md); may not resolve until merged) has a short concept section, a login-path limit in its Nginx edge and a toy WAF, all aimed at WordPress. | The general reasoning for every layer, the algorithms, the keys and the failure modes. This page reuses that lesson's words (edge, origin, noisy neighbor) and does not repeat its lab. |
| Firewalls, NAT, default deny and stateful rules | [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) and [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md). | Rules that count (a rate) instead of only allow or deny. |
| Detecting brute force by counting failures | [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) builds a "five failures in sixty seconds" rule and shows how a slow attacker walks under it. | The same counting idea used as a **control** (it refuses) instead of a **detection** (it tells you), and the difference between them. |
| Proxies, CDNs and load balancers in one sentence each | [How a web request works](How-a-Web-Request-Works.md#caching-cdns-proxies-and-load-balancers-a-sentence-each). | What each can see, and why a limit placed at the wrong one counts the wrong thing. |
| DNS and where it is answered | [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md). | Response rate limiting, and why DNS is a place attackers borrow rather than attack. |

## First, the words

- **Request**: one thing a client asks of a server. **Rate**: requests per unit of time. **Limit**: the most the owner will allow. **Throttle** means slow a client down; **block** means refuse it. Both are rate limiting.
- **Window**: the stretch of time a count covers ("per minute"). **Burst**: a short run of requests faster than the average rate. A limit that allows 60 a minute may or may not allow all 60 in the first second; that choice is the burst setting.
- **Key**: whatever the limiter counts by. In practice a limit is "N per window **per key**". Choosing the key is most of the work, and it gets its own section.
- **Quota**: a total allowance over a long period ("10,000 calls this month"). A **rate limit** protects the service right now; a **quota** is a business rule about a total. They are different tools and are often confused. The API section shows both.
- **HTTP 429 Too Many Requests**: the status code that means "you are being limited". [RFC 6585](https://www.rfc-editor.org/rfc/rfc6585.txt) defines it and says the response MAY carry a `Retry-After` header saying how long to wait. The same RFC says plainly that it does not define how a server identifies the user or counts requests: those are the server's choices.
- **Fail open** means that when the limiter itself breaks, requests are let through. **Fail closed** means they are refused. Neither is free, and a later section is about choosing.
- **Origin**: the real server behind a CDN or proxy. **Edge**: the CDN or proxy at the front.

## Why rate limit

Five different reasons. They lead to different limits, so name which one you are serving before you set a number.

1. **Abuse and denial of service.** One client, or many, sends so much that real users cannot get through. This is the "volume" reason and it is the only one that a plain total cap helps.
2. **Password guessing.** An attacker tries many passwords against one account (brute force), or one common password against many accounts (spraying), or leaked username and password pairs from another breach (credential stuffing). The limit is not about volume at all: 100 guesses a day is no load to a server, and it is still a problem. NIST's digital identity guideline requires a limit on failed attempts per account for this reason ([claims register](#claims-register)).
3. **Scraping.** Someone copies your whole catalog, price list or user directory by walking every page. Each request is polite; the total is not.
4. **Cost.** In a cloud, requests turn into money: compute time, bandwidth, per-call fees to another service, even a language model's tokens. OWASP's API Security list gives a worked example in which a file that grew past a cache's size limit made every client pull it from storage and a monthly bill went from about US$13 to about US$8,000, with no cost alert and no spending cap in place ([OWASP API4:2023](https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/), read 2026-10-22). A rate limit is also a **spending limit**. See [How money works in the cloud](How-Money-Works-in-the-Cloud.md) for the billing alert that belongs next to it.
5. **Protecting a weak backend.** Some component cannot take the load the front door can: a database with a hundred connection slots, a legacy system, a search that scans the whole table, a payment API with its own limits. The limit's job is to keep the weak part alive.

Two things a rate limit is **not**:

- It is **not authentication**. It does not decide who you are or what you may do ([APIs and tokens](APIs-and-Tokens-From-Zero.md#authentication-and-authorization)). It decides how often.
- It is **not a fix for a bug**. If one request can take down the server, slowing the attacker to a request a minute still takes it down. Fix the request; limit as well.

## The algorithms

A limiter answers one question many times a second: "may this request pass?" Four ways of answering are in common use. The names are used loosely by vendors, so read what a product's manual says it does.

- **Fixed window.** Cut time into clock-aligned windows (say ten seconds). Keep a count per key per window; refuse once the count passes the limit; reset at the next boundary. It is the cheapest to store (one number per key). Its flaw is the **boundary**: a client can use the whole allowance in the last second of one window and again in the first second of the next, so the real worst case is **twice the limit** in a short span.
- **Sliding window.** Count requests in the last N seconds, measured back from now, not from a clock boundary. The exact version keeps a list of timestamps per key (accurate and larger); approximations blend the current and previous fixed windows to save space. There is no boundary doubling.
- **Token bucket.** A bucket holds up to `capacity` tokens and refills at a steady `rate`. Each request takes one token; with none left, the request is refused. The bucket is the **burst**: a quiet client saves up tokens and can then send `capacity` requests at once, after which it is held to the refill rate. This is the model most API gateways describe; AWS says API Gateway "throttles requests to your API using the token bucket algorithm, where a token counts for a request" ([AWS docs](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html), read 2026-10-22), and the `limit` match in `iptables` is documented as "a token bucket filter" ([iptables-extensions](https://ipset.netfilter.org/iptables-extensions.man.html), read 2026-10-22).
- **Leaky bucket.** Requests pour into a bucket and leak out at a fixed rate; if the bucket is full, the new request is refused. Used as a **queue** it makes the output perfectly smooth: the server sees a request every `1/rate` seconds no matter how bursty the input was, and the price is delay. Used as a **meter** (a counter that drains) it behaves almost the same as a token bucket. The Nginx manual says its `limit_req` module "is done using the 'leaky bucket' method" ([ngx_http_limit_req_module](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html), read 2026-10-22); with the `burst` setting it holds excess requests briefly and lets them out at the configured rate, and with `nodelay` it lets the burst pass at once and refuses what is beyond it. The Nginx lab below shows both.

| Property | Fixed window | Sliding window | Token bucket | Leaky bucket (queue) |
|---|---|---|---|---|
| Memory per key | one counter | a list of times, or two counters (approximate) | a number and a time | a queue length and a time |
| Allows a burst? | Yes, and up to double at a boundary | Up to the limit; no boundary doubling | Up to `capacity`, then the refill rate | Absorbed and smoothed into a steady rate |
| Smooth output? | No | No | No | Yes |
| What the client feels | Sudden refusals, then a reset | Refusals that ease off gradually | Fast until the bucket empties, then paced | Everything is delayed rather than refused, until the queue is full |
| Typical use | Cheap per-minute counters, daily quotas | Login attempts, "last hour" rules | API quotas, gateways, firewalls | Protecting a backend that wants an even load |

### Exercise 1: run all four and watch the burst

This is a simulation. It uses a pretend clock, so it does not sleep, opens no network connection and finishes at once. The limit everywhere is **5 requests per 10 seconds on average**.

**Predict.** In scenario 2, five requests arrive just before a window boundary and five just after it. Which of the four algorithms lets all ten through? Write down your guess, then run it.

**Do.** Save this as `algos.py` and run `python3 -I algos.py` (PowerShell: the same command, if `python3` is on your path; otherwise `py -3 -I algos.py`, **est.**).

```python
# algos.py - four rate limiters on a SIMULATED clock (no sleeping, no network).
# Each class answers one question: "may a request arriving at time t be served?"
# Limit used everywhere: 5 requests per 10 seconds on average.

class FixedWindow:
    """Count requests in clock-aligned windows of `size` seconds; the count resets at each boundary."""
    def __init__(self, limit, size):
        self.limit, self.size, self.window, self.count = limit, size, None, 0
    def allow(self, t):
        w = int(t // self.size)
        if w != self.window:
            self.window, self.count = w, 0
        if self.count < self.limit:
            self.count += 1
            return True
        return False

class SlidingWindowLog:
    """Remember every accepted timestamp; allow if fewer than `limit` fall in the last `size` seconds."""
    def __init__(self, limit, size):
        self.limit, self.size, self.log = limit, size, []
    def allow(self, t):
        self.log = [x for x in self.log if x > t - self.size]
        if len(self.log) < self.limit:
            self.log.append(t)
            return True
        return False

class TokenBucket:
    """A bucket holds up to `capacity` tokens and refills at `rate` per second; a request spends one."""
    def __init__(self, capacity, rate):
        self.capacity, self.rate, self.tokens, self.last = capacity, rate, float(capacity), 0.0
    def allow(self, t):
        self.tokens = min(self.capacity, self.tokens + (t - self.last) * self.rate)
        self.last = t
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

class LeakyBucketQueue:
    """A queue of at most `capacity` waiting requests that drains at a fixed `rate` per second.
    allow() returns the time the request will be SERVED (smooth output), or None if the queue is full.
    One request is served at once and up to `capacity` more may wait behind it."""
    def __init__(self, capacity, rate):
        self.capacity, self.gap, self.next_free, self.waiting = capacity, 1.0 / rate, 0.0, []
    def allow(self, t):
        self.waiting = [d for d in self.waiting if d > t]          # already served by now
        if len(self.waiting) >= self.capacity:
            return None
        depart = max(t, self.next_free)
        self.next_free = depart + self.gap
        self.waiting.append(depart)
        return depart

def run(name, make, times):
    lim = make()
    out = [lim.allow(t) for t in times]
    ok = [t for t, r in zip(times, out) if r is not None and r is not False]
    print(f"{name:22} allowed {len(ok):2} of {len(times)}")
    return lim, out

def scenario(title, times):
    print(f"\n{title}  ({len(times)} requests)")
    run("fixed window", lambda: FixedWindow(5, 10), times)
    run("sliding window log", lambda: SlidingWindowLog(5, 10), times)
    run("token bucket (cap 5)", lambda: TokenBucket(5, 0.5), times)
    lim, out = run("leaky bucket (queue 5)", lambda: LeakyBucketQueue(5, 0.5), times)
    served = [round(d, 1) for d in out if d is not None]
    print(f"{'':22} served at {served[:8]}{' ...' if len(served) > 8 else ''}")

# 1. A burst: 12 requests in the same instant.
scenario("Scenario 1: 12 requests at t=0", [0.0] * 12)

# 2. The boundary trick: 5 requests just before a window ends, 5 just after it starts.
scenario("Scenario 2: 5 requests at t=9.5, 5 at t=10.5",
         [9.5] * 5 + [10.5] * 5)

# 3. A polite client: one request every 2 seconds for a minute (exactly the average rate).
scenario("Scenario 3: one request every 2 s for 60 s", [i * 2.0 for i in range(30)])
```

**Check.** On 2026-10-22 it printed:

```text

Scenario 1: 12 requests at t=0  (12 requests)
fixed window           allowed  5 of 12
sliding window log     allowed  5 of 12
token bucket (cap 5)   allowed  5 of 12
leaky bucket (queue 5) allowed  6 of 12
                       served at [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]

Scenario 2: 5 requests at t=9.5, 5 at t=10.5  (10 requests)
fixed window           allowed 10 of 10
sliding window log     allowed  5 of 10
token bucket (cap 5)   allowed  5 of 10
leaky bucket (queue 5) allowed  6 of 10
                       served at [9.5, 11.5, 13.5, 15.5, 17.5, 19.5]

Scenario 3: one request every 2 s for 60 s  (30 requests)
fixed window           allowed 30 of 30
sliding window log     allowed 30 of 30
token bucket (cap 5)   allowed 30 of 30
leaky bucket (queue 5) allowed 30 of 30
                       served at [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0] ...
```

The fixed window let all ten through in scenario 2, ten requests in one second, twice the limit. The other three held it to five, or to five plus the one the leaky queue is serving. The leaky bucket's "allowed" count is six rather than five for a reason worth understanding: it never refused a request while its queue had room, it spread them out (see `served at`, two seconds apart), and the first one is served at once. It converts a burst into steady, slower traffic. In scenario 3 the client sends exactly at the average rate (one request every two seconds), and **all four allow every request**. Keep that in mind: a limit on average rate is no obstacle to a client that stays just under it. That is the "slow and low" idea the Evade step uses.

**Undo.** Nothing was written except `algos.py`. Delete it if you like.

## What to count by

Every limit is, in effect, "N per window per **key**". The key is what makes the count belong to someone. The same traffic gives different results with different keys, and the wrong key either blocks the innocent or lets the guilty through.

| Key | Good for | Breaks when |
|---|---|---|
| **Source IP address** | The only key you have before anyone logs in. Cheap. The right first choice for volume. | Many people share one address (NAT); one person has many addresses (IPv6, proxies, botnets); the address you see is a proxy's, not the client's. |
| **Account or username** | Password guessing: count failures **per account**, wherever they come from. OWASP's authentication guide says the failed-login counter should be tied to the account, "rather than the source IP address, in order to prevent an attacker from making login attempts from a large number of different IP addresses" ([OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), read 2026-10-22). | An attacker can lock out a victim on purpose (a denial of service on one person). Only works after the username is known. |
| **API key or token** | APIs: each customer gets their own bucket and quota. | A leaked or shared token gets one customer's allowance used by two parties; a free-trial signup lets one person mint many tokens. |
| **Session or cookie** | Telling people behind one NAT address apart. | A bot simply does not send the cookie, or throws it away each request. Cloudflare's "IP with NAT support" works this way and the vendor says visitors who clear cookies, use private browsing or reject cookies "will not be individually identified" and share one counter ([Cloudflare](https://developers.cloudflare.com/waf/rate-limiting-rules/parameters/), read 2026-10-22). |
| **Network (ASN) or country** | Slowing a whole hosting provider or region that sends only attackers. | Blocks real people on that network; countries are crude. |
| **Path or operation** | Making an expensive endpoint (search, export, password reset) stricter than a cheap one. | Different spellings of the same path (encoding, case, trailing slash) can miss the rule. Cloudflare's own rate limiting guide warns that origins and frameworks "may normalize or decode paths differently", so test every path form your application accepts. |
| **A combination** | Most real rules: "per IP **and** path", "per account **and** IP". | More keys means more memory and more ways to be wrong; an attacker rotating one part of the key escapes. |

### The three ways an address lies

1. **Shared NAT (many people, one address).** NAT, covered in [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md#nat-and-port-forwarding), lets a whole office, campus, hotel, school or mobile carrier appear as one address (carrier-grade NAT; how many people share one address varies a lot and I do not give a number, est.). A per-address limit tight enough to stop an attacker will block the real people sharing the address. Exercise 2 puts numbers on this.
2. **IPv6 (one person, many addresses).** In IPv6, a home or small site is normally handed a block of addresses, not one. [RFC 6177](https://www.rfc-editor.org/rfc/rfc6177.txt) says home sites should get "significantly more than a single /64" (a **/64** is a block of 2^64 addresses; the number after the slash is how many leading bits are fixed). A device is also expected to change the address it uses over time: [RFC 4941](https://www.rfc-editor.org/rfc/rfc4941.txt) defines temporary addresses whose interface part "change over time". So a limit keyed on the single IPv6 address is trivially escaped: the owner of one block rotates through addresses. The usual response is to key IPv6 on the **prefix** (a /64, sometimes a larger block) instead of the single address. The cost is the reverse of NAT: a prefix may be one household or a whole small site. The right prefix length is a judgment call (est.).
3. **Proxies (the address you see is not the client).** When a CDN, load balancer or proxy sits in front of your server, the connection arrives from the proxy, so every client looks like the same address. The proxy passes the real client address along in a header, most often `X-Forwarded-For`. The next section is about why you cannot just believe that header.

### Trusting `X-Forwarded-For`

`X-Forwarded-For` (XFF) is a request header that carries a list of addresses: the client first, then each proxy that handled the request, each one appending the address it received the connection from. Because it is just text in the request, **anyone can send one**. MDN puts the rule plainly: if the server can be reached directly from the internet, "no part of the X-Forwarded-For IP list can be considered trustworthy or safe for security-related uses", and "any security-related use of X-Forwarded-For (such as for rate limiting or IP-based access control) must only use IP addresses added by a trusted proxy" ([MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Forwarded-For), read 2026-10-22). It names "rate-limiter avoidance" as a consequence.

Three rules follow:

- **Count the address a trusted proxy added, not the one the client wrote.** Each proxy appends to the right, so the **rightmost** value is the most recent hop. If you have exactly one trusted proxy in front, the rightmost value is the client as that proxy saw it. The leftmost value is whatever the client chose to claim.
- **Only trust the header from the proxy's own address.** Nginx's real-address module does this with `set_real_ip_from` ("defines trusted addresses that are known to send correct replacement addresses") and `real_ip_header`; `real_ip_recursive` controls whether it takes the last address or the last one that is not itself trusted ([ngx_http_realip_module](https://nginx.org/en/docs/http/ngx_http_realip_module.html), read 2026-10-22).
- **Close the side door.** If an attacker can reach your origin directly, they can send the proxy's address in the header or skip the proxy and its limits entirely. Cloudflare's guidance for protecting an origin lists allowing only Cloudflare's address ranges at the origin, Authenticated Origin Pulls, and Cloudflare Tunnel ([Cloudflare](https://developers.cloudflare.com/fundamentals/security/protect-your-origin-server/), read 2026-10-22). Cloudflare also sends the client address in its own header, `CF-Connecting-IP`, which it says is sent only on traffic from Cloudflare's edge to your origin web server ([Cloudflare HTTP headers](https://developers.cloudflare.com/fundamentals/reference/http-headers/), read 2026-10-22); that header is only worth believing if nothing but Cloudflare can reach you.

### Exercise 2: count by the wrong key and see who gets hurt

A simulated minute again, no network. Forty office workers share one NAT address and each makes a request every five seconds. One attacker owns an IPv6 /64 and sends 600 requests from 600 different addresses, all aimed at **one** account. The limit is 60 per minute per key. The addresses are from the documentation ranges ([RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.txt) for IPv4, [RFC 3849](https://www.rfc-editor.org/rfc/rfc3849.txt) for IPv6), so nothing here is a real network.

**Predict.** Which key protects the office and stops the attacker? Is there a key that does only one of the two?

**Do.** Save as `keys.py` and run `python3 -I keys.py`.

```python
# keys.py - what you COUNT BY decides who gets hurt. A simulated minute, no network.
# Addresses are documentation ranges (RFC 5737 for IPv4, RFC 3849 for IPv6). Limit: 60 requests per minute per key.
import ipaddress
from collections import Counter

LIMIT = 60

def run(events, keyfn):
    """events: (second, ip, account, is_attacker). Returns (served, blocked) split by who sent them."""
    seen, served, blocked = Counter(), Counter(), Counter()
    for sec, ip, acct, bad in sorted(events):
        k = keyfn(ip, acct)
        seen[k] += 1                                   # one fixed one-minute window: enough for the point
        (served if seen[k] <= LIMIT else blocked)["attacker" if bad else "legit"] += 1
    return served, blocked

events = []
# A. 40 office workers behind one shared NAT address, one request every 5 seconds each (480 in the minute).
for u in range(40):
    for s in range(0, 60, 5):
        events.append((s + u / 40, "198.51.100.7", f"worker{u}", False))
# B. One attacker who owns a whole IPv6 /64 and uses 600 different addresses, 1 request each, all at ONE account.
net = ipaddress.ip_network("2001:db8:abcd:12::/64")
for i in range(600):
    events.append((i / 10, str(net[1000 + i]), "victim", True))

def per_ip(ip, acct):      return ip                                   # every address its own key
def per_v6_64(ip, acct):   # IPv4 as is; IPv6 grouped by its /64
    a = ipaddress.ip_address(ip)
    return str(ipaddress.ip_network(f"{a}/64", strict=False)) if a.version == 6 else ip
def per_account(ip, acct): return acct

for name, fn in (("per address (each /128 alone)", per_ip), ("per address, IPv6 grouped by /64", per_v6_64), ("per account", per_account)):
    served, blocked = run(events, fn)
    print(f"{name:34} legit blocked {blocked['legit']:3} of {served['legit']+blocked['legit']:3}   "
          f"attacker blocked {blocked['attacker']:3} of {served['attacker']+blocked['attacker']:3}")
```

**Check.** On 2026-10-22:

```text
per address (each /128 alone)      legit blocked 420 of 480   attacker blocked   0 of 600
per address, IPv6 grouped by /64   legit blocked 420 of 480   attacker blocked 540 of 600
per account                        legit blocked   0 of 480   attacker blocked 540 of 600
```

Counting each IPv6 address alone blocks none of the attacker's 600 requests (each address sent one) and blocks 420 of the office's 480, because the office is one address. Grouping IPv6 by /64 stops 540 of the attacker's requests and still hurts the office. Counting **per account** stops the attacker (the account sees 600 attempts) and leaves the office alone, because each worker is a separate account. Two honest cautions: this simulation is built so that per-account wins, and in the real world per-account counting is available **only where an account is known** (a login form, not a public page), and it lets an attacker deliberately lock the victim out. No single key is right; layers use different ones.

**Undo.** Nothing but the file.

## Think at each level

A request passes through a chain of layers on its way to the data. Each layer can limit, and each sees something the others cannot. A limit is only as good as the information at the layer that makes it. The table is the whole idea of this page; the sections after it fill it in. Read it from the outside (where the attacker is) inward (where the data is).

| Layer | What it can see | What it cannot see | Good to limit | How it fails |
|---|---|---|---|---|
| **Upstream network (your ISP or transit provider)** | Bytes and packets on your link | Requests, accounts, anything inside encrypted traffic | Volume that would fill your link; the provider's own tools decide the rest | The link is full before any of your rules see the traffic. You cannot fix this from inside; it is a contract and a call to the provider (est.). |
| **DNS** (authoritative and recursive servers) | The source address of the query (often a **resolver**, not the person) and the name and type asked for | Who the person is; the web request that follows | Identical responses per second per client (response rate limiting) on authoritative servers; queries per address on resolvers | Spoofed source addresses make you limit the victim; a limit per resolver address blocks everyone using that resolver; open resolvers are abused for amplification. |
| **CDN or WAF edge** | The full HTTP request: path, method, headers, cookies, address, network, country, sometimes body and response code | The application's idea of "who" (until it logs in); traffic that skips the edge | Per-address and per-path rates, login and search paths, bots by reputation, challenges | Counters are not exact or global (Cloudflare counts per data center); the origin is reachable around the edge; per-address keys hit NAT. |
| **Load balancer** | Connections and requests across all the servers; backend health | Application users | Concurrent connections, queue length, connection rate per client, per-backend concurrency | Overload makes health checks fail, servers are removed, the rest get more load and fail too (est.: a general pattern, not read from one source). |
| **Reverse proxy** (Nginx, HAProxy) | The request headers, the connection address, the upstream's response status | Which user the application thinks it is | Request rate and concurrent connections per key, per route; body size; timeouts | Wrong key (header spoofed); counts per instance, not per fleet; a rewrite step that answers before the limiter runs. |
| **Application or framework** | The authenticated user, tenant, plan, what the endpoint costs | Anything that never reached it (dropped earlier) | Per-user and per-tenant rates, expensive operations, business rules | Each server instance counts alone unless the state is shared; the shared store is down; the check and the update are not atomic (est.); everything is limited at the same rate whatever it costs. |
| **Login, reset and OTP endpoints** | The username, whether the guess was right, the address | The person behind the address | Failures **per account**, per address and across the whole service | Account lockout becomes a way to attack the victim; a limit that is too tight locks out the owner; a limit that is too loose lets a six-digit code be guessed. |
| **API per-token quotas** | The token, the plan, the endpoint, sometimes the cost | Whether two tokens belong to one attacker | A token bucket per token, a quota per plan, a cost-based budget | One tenant's hard limit starves a shared service; a leaked token spends the owner's quota; clients that retry at once on a `429` make it worse. |
| **Database and connection pools** | Connection counts, queue depth, query time | Where the load came from | Pool size, queue length, statement timeouts, connections per role | The pool is exhausted, application threads wait, everything times out together. |
| **Host firewall and kernel** | Packets, new connections, source addresses, the connection table | HTTP content, accounts, paths | New connections per source, the SYN backlog, the size of the connection tracking table | The table fills and drops everyone's new connections; spoofed sources get the wrong host blocked; a per-address limit hits NAT. |

Now each layer in a little more detail. The point is not to memorize it. The point is to notice the pattern: **limit as early as the information allows, and again later where the information is better.**

### The upstream network

Everything you build runs on a link of finite size. A flood that is bigger than the link cannot be stopped by any rule on your side of it, because the packets have already used up the capacity by the time they reach your firewall. This is why the answer to a large flood is usually bought or arranged in advance: a CDN or scrubbing provider that absorbs traffic on its own very large network, or a request to your provider to filter upstream. I did not read a source for the provider-side mechanisms and I will not describe them as fact (est.). The lesson for a learner is the boundary: **a rate limit in your own firewall is not a defense against a flood bigger than your connection.** It is a defense against a flood that fits.

### DNS

DNS answers over UDP, which has no handshake. A server that answers anyone who asks can be used to hit a **third party**: an attacker sends queries with the victim's address forged as the source, and the server sends its (usually much larger) answers to the victim. That is a **reflection and amplification** attack, and the server is the weapon, not the target. Rate limiting is the standard fix on the server side.

- **BIND**'s `rate-limit` block "controls excessive UDP responses, to prevent BIND 9 from being used to amplify reflection denial-of-service (DoS) attacks". It uses "a 'credit' or 'token bucket' scheme": each combination of identical response and client has an account that earns credits each second, and a response costs one; when the account is negative, responses are dropped or truncated. The manual says the mechanism is "intended for authoritative DNS servers" and that on recursive servers it "can slow applications such as SMTP servers (mail receivers) and HTTP clients (web browsers) that repeatedly request the same domains", adding that "when possible, closing 'open' recursive servers is better" ([BIND 9 reference](https://bind9.readthedocs.io/en/latest/reference.html), read 2026-10-22). The truncation trick is clever: a short answer with the TC bit set tells a real client to retry over TCP, which cannot be spoofed, while a victim of forged queries just gets a small packet.
- **Unbound** has two. `ratelimit` limits queries it sends upstream for recursion per zone ("This stops recursive floods, eg. random query names, but not spoofed reflection floods"); `ip-ratelimit` limits queries accepted per client address, before the cache, and its manual says it "may be useful for mitigating amplification attacks" and that clients with a valid DNS cookie bypass it. Both are marked experimental in the manual page I read ([Unbound manual](https://unbound.docs.nlnetlabs.nl/en/latest/manpages/unbound.conf.html), read 2026-10-22).

A shape (not run, **est.**; check the manual for your version before using any of it):

```text
# BIND, in named.conf (authoritative server)
options {
    rate-limit {
        responses-per-second 10;
        window 5;
    };
};

# Unbound, in unbound.conf (resolver for your own network only)
server:
    ip-ratelimit: 200
```

What DNS cannot see is the person. The client address is usually the person's **resolver**, shared by everyone who uses it, so a per-address limit on a busy resolver's address punishes all of them. And a DNS limit never helps with the web request that comes after the lookup. If you host DNS through a provider ([DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md)), this layer is the provider's job, and the useful question is whether they say how they handle it.

### The CDN or WAF edge

A CDN (content delivery network) answers from servers near the visitor, and a WAF (web application firewall) inspects requests for attack patterns; both are described in [How a web request works](How-a-Web-Request-Works.md#caching-cdns-proxies-and-load-balancers-a-sentence-each). The edge is the first layer that sees the whole HTTP request, and it sits where it can absorb volume before it reaches you. It is the best first place for per-address and per-path limits on a login page or a search.

Facts from Cloudflare's rate limiting rules documentation (read 2026-10-22; plan details change, so check the page): a rule has **characteristics** (what to count by), a **period**, a **request count**, and a **mitigation timeout** (how long to keep blocking once the rate is reached). The Free plan offered one rule counting by IP with a ten-second period; richer keys (header, cookie, ASN, country, path, JSON field, TLS fingerprint) and longer periods were on higher plans, and some need extra products. The default response status for a block is `429`. The most important sentences are about what it does **not** promise: rate limiting rules "are not designed to allow a precise number of requests to reach your origin server", because there can be "a delay of up to a few seconds between detecting a request and updating rate counters"; and "counters are not shared across data centers, with the exception of data centers associated with the same geographical location", because every rule includes the data center ID as a characteristic ([Cloudflare](https://developers.cloudflare.com/waf/rate-limiting-rules/) and [how the rate is determined](https://developers.cloudflare.com/waf/rate-limiting-rules/request-rate/), read 2026-10-22). In plain words: a limit of 100 a minute at the edge is "about 100 a minute per place the traffic enters", and an attacker spread across regions gets more.

Its best-practice guidance includes a step I want every beginner to copy: **start with the Log action** and look at what would have been blocked, then change to block or challenge ([Cloudflare: find an appropriate rate limit](https://developers.cloudflare.com/waf/rate-limiting-rules/find-rate-limit/), read 2026-10-22). Nginx has the same idea as `limit_req_dry_run`, and the lab uses it.

The edge cannot see the application's idea of a user, with one useful exception: on plans that support a custom counting expression, Cloudflare lets you **count only requests whose response was a failure** (a counting expression that includes the response code), so a login rule can count only `401` and `403` answers from your origin. That folds application knowledge into an edge rule. And the edge is useless if the origin can be reached without it, which is the side-door point from earlier.

### The load balancer

A load balancer spreads requests over several servers and stops sending to one that failed. What it can limit is **concurrency**, not only rate: how many connections or requests are in flight at once per client, per backend, and how long a queue may grow. This matters because slow requests, not fast ones, hold resources: a thousand clients each sending one byte a second can hold a thousand connections open for a long time without exceeding any request rate. A concurrency limit (`limit_conn` in Nginx, connection counts in HAProxy) catches that; a rate limit does not. The failure mode to know is the cascade: overload makes health checks fail, the balancer removes the struggling servers, the survivors take more load and fail in turn. Limits that shed load early, with a clear `429` or `503`, keep a smaller working system standing instead of a bigger dead one (est.: a general pattern; I did not read a source for it).

### The reverse proxy: Nginx and HAProxy

A reverse proxy (see the Glossary) is the layer most beginners will configure themselves, and the lab below uses one.

**Nginx** (`limit_req`, `limit_conn`):

- `limit_req_zone` defines the key and the rate and a shared-memory zone that stores the state. One megabyte "can keep about 16 thousand 64-byte states or about 8 thousand 128-byte states", and when the zone is full "the least recently used state is removed"; if a new state still cannot be created, the request is refused. **Requests with an empty key are not accounted at all**, so a key built from a header that the client can leave out is a limit that can be skipped.
- `burst` sets how many excess requests are held, `nodelay` lets them through at once instead of pacing them, and `delay` sets where pacing starts. `limit_req_status` sets the refusal code (the default is `503`; this lab sets `429`). `limit_req_dry_run` counts without refusing. The variable `$limit_req_status` records `PASSED`, `DELAYED`, `REJECTED` and the dry-run versions, which is what you want in your access log.
- `limit_conn` limits concurrent connections per key, and a connection is counted only while a request is being processed and "the whole request header has already been read". In HTTP/2 and HTTP/3 each concurrent request counts as one.
- Both modules work in the "preaccess" phase of request handling, which comes **after** the rewrite phase ([Nginx development guide](https://nginx.org/en/docs/dev/development_guide.html), read 2026-10-22). I found the consequence while building the lab: a location that answers with `return 200 ...` ends the request in the rewrite phase, before `limit_req` runs, so the limit silently never applied (every request got `200`). If a limit seems to do nothing, check what answers first.
- Each Nginx instance keeps its own zone. Two proxies each enforce the limit separately, so the fleet allows twice the number. The `sync` parameter that shares a zone across instances is listed in the manual as part of the commercial subscription.

**HAProxy** keeps counters in **stick tables**: a table keyed by (for example) the source address that stores data such as `http_req_rate(<period>)`, "the average HTTP request rate over that period"; a rule tracks the request into the table and another denies when the stored rate is too high. Tables can be replicated between HAProxy instances with `peers` ([HAProxy 3.0 configuration manual](https://docs.haproxy.org/3.0/configuration.html), read 2026-10-22). A shape (not run, **est.**):

```text
frontend web
    bind :80
    stick-table type ipv6 size 100k expire 10m store http_req_rate(10s)
    http-request track-sc0 src
    http-request deny deny_status 429 if { sc_http_req_rate(0) gt 20 }
```

The manual says a plain `deny` returns 403 by default and that `deny_status` changes it. It also notes that on an IPv6 table, IPv4 addresses are mapped into IPv6 form. The manual says of `http_req_rate` that "it does not matter whether they are valid requests or not", which means the counter sees bad requests too.

### The application and the framework

Only the application knows who is logged in, which plan they pay for, and what a request costs. So per-user, per-tenant and per-operation limits belong here: "10 exports an hour", "50 searches a minute", "at most 3 concurrent uploads". Frameworks and libraries have rate limiting add-ons; I name none and recommend none, because that choice depends on your stack.

The hard problem in the application is **shared state**. If four copies of the application run behind a balancer and each counts alone, the user gets four times the limit. Counting in a shared store (a cache like Redis) fixes that, and creates two new problems: the store is a dependency (what happens when it is down? see fail open and fail closed below), and an update done as "read the count, add one, write it back" can lose counts when two requests overlap (est.: the usual remedy is an atomic increment in the store). One more design question: should a cheap request and an expensive one cost the same? A limiter that charges by cost (a search that scans a table costs ten times a lookup) is fairer to users and harder to build. Cloudflare's Enterprise plan with Advanced Rate Limiting lists a "complexity score" counting model for the same reason (read 2026-10-22).

### Login, password reset and one-time codes

These are the endpoints where the limit is about guessing, not volume, so the key is the **account**, and the numbers are small.

- OWASP's guide describes **login throttling** and **account lockout**: lock after a threshold of failures in an observation window for a duration; or use an exponential delay that starts tiny and doubles. It warns that lockout can itself be used to cause a denial of service by locking out other users' accounts, and suggests letting the forgotten-password flow still work for a locked account. It treats a CAPTCHA as "a defense-in-depth control to make brute-force attacks more time-consuming and expensive, rather than as a preventative", best shown after a few failures ([OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), read 2026-10-22).
- NIST's digital identity guideline (SP 800-63B-4, section 3.2.2) says a verifier SHALL limit consecutive failed attempts on an account to **no more than 100**, calls that an upper bound that organizations may lower, and lists ways to reduce the chance an attacker locks the real user out: a bot-detection challenge, a wait that grows toward the limit (it gives "30 seconds up to an hour" as an example) and risk-based checks. It explains the 100 by weighing "100 attempts against a six-digit decimal OTP" ([NIST](https://pages.nist.gov/800-63-4/sp800-63b.html), read 2026-10-22). Do the arithmetic yourself: a six-digit code has 1,000,000 values, so 100 guesses succeed 1 time in 10,000, or 0.01 percent. Without a limit, a computer tries a million codes in minutes (est.).
- OWASP's API guidance names the same operations: limit "how many times or how often a single API client/user can execute a single operation (e.g. validate an OTP, or request password recovery without visiting the one-time URL)" ([OWASP API4:2023](https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/)).

Put per-account, per-address and a global ceiling together. Per-account stops a distributed guess at one person; per-address stops one machine trying many people; the global ceiling notices a spray that stays under both.

### API per-token quotas

An API (see [APIs and tokens](APIs-and-Tokens-From-Zero.md)) has a built-in key: the token. A token bucket per token gives each customer a fair, separate allowance. Two numbers matter: the **refill rate** (steady) and the **capacity** (burst). AWS's description is useful because it admits the limits are soft: "throttles and quotas are applied on a best-effort basis and should be thought of as targets rather than guaranteed request ceilings" (AWS, read 2026-10-22). Exercise 8 builds a per-key limiter with a rate limit and a separate quota.

How should the server tell the client? Use `429` and a `Retry-After`. RFC 9110 defines `Retry-After` as either a number of seconds or an HTTP date ([RFC 9110, section 10.2.3](https://www.rfc-editor.org/rfc/rfc9110.txt), read 2026-10-22). Many services also send headers saying how much is left. There is a work in progress to standardize them: an Internet-Draft, `draft-ietf-httpapi-ratelimit-headers`, which at revision 11 defines `RateLimit-Policy` and `RateLimit` header fields and is marked to expire on 24 November 2026. **It is a draft, not a standard**, and the headers you meet in the wild (`X-RateLimit-Remaining` and others) are vendor choices ([IETF datatracker](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/), read 2026-10-22).

The client's side is half of the system. A well-behaved client reads `Retry-After`, waits at least that long, adds a little random **jitter** (so a thousand clients that were all told "wait one second" do not return in the same instant), and does not retry forever. A badly behaved client retries instantly, which turns a limit into a **retry storm** that makes the overload worse. Exercise 3 writes the polite one.

### Database and connection pools

The deepest layer is often the weakest. PostgreSQL's `max_connections` has a default that "is typically 100 connections" (PostgreSQL 18 documentation, read 2026-10-22), and each connection uses memory. An application that opens a connection per request falls over at a hundred simultaneous requests whatever rate limit sits in front. The usual answer is a **connection pool**: a fixed number of connections shared by many requests, with the rest waiting in a queue. PgBouncer is a well-known pooler for PostgreSQL; its `max_client_conn` caps client connections, and its manual warns that raising it may mean raising the operating system's file descriptor limits ([PgBouncer configuration](https://www.pgbouncer.org/config.html), read 2026-10-22).

This is a rate limit by another name: pool size is a concurrency limit and the queue length is a burst. The failure mode is a stall: when every connection is busy with slow queries, every request waits, the application's own threads pile up, timeouts expire and the whole service looks dead although no one sent a large number of requests. The defenses are timeouts (on the queue and on the statement), a bounded queue that fails fast, and limits above that stop the pile before it starts. Every layer above should be stricter than this one, so the weakest component is never the first to learn about a surge.

### The host firewall and the kernel

The operating system sees packets and connections, not requests. Three things are worth knowing.

1. **Per-source limits on new connections** are what `nftables` and `iptables` offer. In nftables, a **meter** or dynamic set keeps state per key; the nftables wiki shows `update @set { ip saddr limit rate 3/minute }`, notes that "Meters replace iptables hashlimit in nft", and that `ct count` (since kernel 4.18) limits the number of connections per key ([nftables wiki: Meters](https://wiki.nftables.org/wiki-nftables/index.php/Meters), last edited 2023-08-15, read 2026-10-22). In iptables, `limit` is "a token bucket filter" for the rule as a whole, and `hashlimit` does the same per group of connections (per source, per destination, per port) ([iptables-extensions](https://ipset.netfilter.org/iptables-extensions.man.html)). Exercise 7 runs both in a private namespace.
2. **SYN cookies.** A TCP connection starts with a three-step handshake (SYN, SYN-ACK, ACK; see the Glossary). A **SYN flood** sends many SYNs and never finishes; the server keeps half-open connections in a queue until it fills and real clients are refused. A **SYN cookie** avoids keeping that state: the server encodes what it needs in the sequence number of its reply and allocates nothing until a valid ACK comes back, which a spoofed sender cannot produce ([RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.txt), read 2026-10-22). The kernel's documentation says cookies are sent "when the syn backlog queue of a socket overflows", that the default is 1, and that syncookies is "fallback facility. It MUST NOT be used to help highly loaded servers to stand against legal connection rate"; it also warns that cookies "seriously violate TCP protocol" and can degrade some services. `tcp_max_syn_backlog` is "a per-listener limit" ([kernel networking sysctl documentation](https://docs.kernel.org/networking/ip-sysctl.html), read 2026-10-22). Exercise 7 shows the counters move.
3. **The connection tracking table.** A stateful firewall remembers every connection. The table has a maximum (`nf_conntrack_max`); when it is full, new connections are dropped for everyone. The kernel documentation notes that each entry is added twice, once per direction. A flood of spoofed connections, or simply a service that holds many, can fill it (est.: the exact failure message and defaults depend on the distribution). A per-source connection limit upstream of the table keeps one source from using it all.

What the kernel cannot see is anything inside the connection. It cannot count login failures or paths. Its keys are addresses, so NAT and IPv6 hurt here exactly as they do at the edge. A **fail2ban**-style tool bridges the gap: it "scans log files like /var/log/auth.log and bans IP addresses conducting too many failed login attempts" by "updating system firewall rules to reject new connections from those IP addresses, for a configurable amount of time", and the project says plainly that it "cannot eliminate the risk presented by weak authentication" ([fail2ban README](https://github.com/fail2ban/fail2ban/blob/master/README.md), read 2026-10-22). That makes it a **slow, log-driven** limiter: the damage happens first, then the ban. It belongs on the file-integrity and alerting lesson as much as this one ([File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md); may not resolve until merged).

## When one address is not one attacker

A limit per address assumes an attacker has few addresses. A botnet of ten thousand machines, a pool of residential proxies or an IPv6 block breaks that. Each address sends a handful of requests, none of which exceeds any limit, and the total is an attack. What helps instead of a smaller per-address number (which only hurts real users sooner):

- **Count something that does not rotate.** The account being attacked (credential stuffing), the path being hit, the target being scraped. Exercise 2 showed this.
- **A global ceiling** on an expensive endpoint, so the whole service refuses the surplus no matter who sends it. It is blunt: real users get refused during the attack. It protects the backend at the cost of availability.
- **A challenge** instead of a block: a proof of work, a browser check, a CAPTCHA, an extra factor. It costs real users a little and costs a bot farm money. OWASP and NIST both present challenges as a cost-raiser, not a wall (see above).
- **Reputation and context.** Known-bad networks, hosting providers, fingerprints of a client library (Cloudflare can count by a TLS fingerprint on its top plans), a login from an address that has just failed at a hundred other sites. Detection rather than counting; see [IDS and IPS](IDS-and-IPS-Snort-and-Suricata.md) (may not resolve until merged) and [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md).
- **Cost caps.** If the real danger is a bill, a hard spending limit or an alert at the provider stops the damage even when no rate limit caught the cause.

## Fail open or fail closed

Your limiter has a state store (memory, a cache, a database) and rules (a config). Either can break. The choice of what happens next is a decision, not a default, and it should be made on purpose for each layer.

- **Fail open**: if the limiter cannot decide, let the request through. Real users are served; the protection is gone. Pick this when availability is the product (a public web page) and a backend can survive a surge for a while.
- **Fail closed**: if the limiter cannot decide, refuse. The protection holds; the limiter's outage is now your outage. Pick this when the thing being protected must not be exposed uncounted (a login, an OTP check, a payment) even at the price of turning away real users.
- It does not have to be all or nothing. A limiter that cannot reach its shared store can fall back to a **local, stricter** count on each instance.
- Nginx gives one concrete example: when its zone is full and cannot create a state, "the request is terminated with an error" (the manual's words), which is fail closed for that key under memory pressure. Another: an empty key is "not accounted", which is fail open for requests without the header.

Write the choice down, and **test** it: stop the store in a lab and see what users get. A choice nobody has tried is a guess.

## The honest cost to real people

A rate limit tight enough to stop an attacker will usually refuse some real people too. The ones who pay are rarely the ones you imagine.

- **Shared addresses.** An office, a school, a hotel, a coffee shop and a mobile carrier put many people behind one address. A limit that stops a script in a minute can stop a whole branch office in the same minute.
- **People with accessibility needs and slow connections**, who retry or reload because pages are slow, look like a client that hammers.
- **Mobile apps** retrying on a flaky network. **Browsers** that open many parallel requests for one page. A single page load can legitimately make dozens of requests.
- **Support staff** reviewing one customer's account quickly; **monitoring tools and health checks** that you forgot to exempt; **search engines** that you may want to allow at a gentler rate. Cloudflare warns that limiting verified bots might affect search ranking (read 2026-10-22).
- **A locked-out account** is a denial of service on one person, and for a person who needs the account (a bank, a medical portal) it is serious.

Mitigations, each with its own cost: generous limits with short windows (so a mistake lasts seconds); a **challenge before a block**; exemptions for known-good health checks and partners, kept short and reviewed; a clear error that says how long to wait (`Retry-After`) and how to reach a human; and a way for support to see and lift a block. Measure false positives: if you do not count how often real users were refused, you do not know the cost of your limit.

## Observability: a limit nobody can see is an outage nobody can explain

A limiter changes the answer a client receives. If you cannot see that it did, then every complaint is a mystery and every attack is invisible.

- **Log every refusal**, with the key, the rule that refused, the path, and the time. In Nginx, log `$limit_req_status` in the access log (the lab's config does, and Exercise 6 reads it) and set `limit_req_log_level` so refusals appear in the error log.
- **Alert on the rate of refusals**, not each one. A burst of `429`s on the login path at 03:00 is a signal; a steady trickle of them from one office is a tuning problem. This is the "rule or baseline" question of [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md#rules-baselines-and-the-two-ways-to-be-wrong): alert on a change from normal. Avoid [alert fatigue](Logs-SIEM-and-Detection-Basics.md#alert-fatigue) by alerting on top keys and sudden changes, not every block.
- **Dashboard the shape**: refusals per layer per minute, top keys, the share of traffic limited, the per-endpoint response codes, and how close the busiest legitimate clients come to the limit. If your heaviest honest customer is at 90 percent of the limit all day, it is a bad limit.
- **Dry-run new rules** (Nginx `limit_req_dry_run`, Cloudflare's Log action) and look before enforcing.
- **Record what changed**: a limit that changes without a ticket and a date is a future mystery ([Working in a company](Working-in-a-Company-Tickets-Change-On-Call-and-Documentation.md)).

## Layers must not hide each other

Layers fight if you let them.

- **A refusal early hides the signal later.** If the edge blocks the noisy address, the origin never sees it, and its logs say all is calm. Keep the edge's logs and the origin's logs, and read both. In the lab, the edge's log line for a refused request says `limit=-` (the edge did not refuse it) while the application's says `limit=REJECTED`: two layers, two different views of one request.
- **A limit later can be blind to the identity.** The application behind a proxy sees only the proxy's address unless the header is trusted correctly; a limit there counts the whole internet as one client.
- **Limits can contradict.** An edge that allows 100 a minute and an origin that allows 10 a minute means clients see mysterious `429`s from a layer the edge team does not own. Write down each layer's number, who owns it, and which is meant to bite first. The usual rule: the **outer** layers are looser and absorb volume; the **inner** layers are stricter about the things only they can see, and the innermost (the database pool) is the one you never want to reach.
- **Retries multiply.** If every layer retries a refused request three times, one request becomes twenty-seven. Retry only at one layer, with backoff and a cap.
- **Make `429` and `503` distinguishable.** `429` means "you are going too fast"; `503` means "I am unable"; clients and alerts should treat them differently.

## Only your own lab

Everything above is for systems you own or are explicitly authorized to test. The exercises on this page run on your own computer and send traffic only to `127.0.0.1` or to a private network namespace with nothing else in it. Do not run a rate limit test, a "burst", a spoofed-header test or a load loop against a service you do not own: a public API's terms usually forbid it, it can look like an attack, it can get your address banned, and in many places it is a crime. If you want to see a vendor's limits, read their documentation, which is what the claims register records. The same applies to the public sites in the other exercises of this wiki: send each of them a handful of requests, not a loop.

## Free path: a lab on your own computer

All of this runs on one computer you own, uses no account and costs nothing. Exercises 1 and 2 above need only Python. The rest use a container with Nginx (Exercises 3 to 6), a Linux network namespace (Exercise 7) and Python again (Exercise 8). The reading and the exercises are free and always will be.

### Setup for the Nginx lab: files and a container

You need Podman or Docker. The container publishes ports on **127.0.0.1 only**, mounts two folders read-only, does not run privileged and does not get the container runtime's socket. It is a local test and not a production configuration. Pick the runtime once:

```bash
RT=podman        # or: RT=docker
mkdir -p rl-lab/data && cd rl-lab
echo ok > data/ok.txt
head -c 20480 /dev/zero > data/blob.bin     # 20 KB, served slowly on purpose
```

PowerShell (**est.**, not run; needs PowerShell 7 for the later scripts):

```powershell
$RT = 'podman'   # or 'docker'
New-Item -ItemType Directory -Force rl-lab/data | Out-Null; Set-Location rl-lab
Set-Content -Path data/ok.txt -Value 'ok'
[System.IO.File]::WriteAllBytes("$PWD/data/blob.bin", [byte[]]::new(20480))
```

Save this as `nginx.conf` in the `rl-lab` folder. Read the comments; every line has a purpose in one of the next four exercises.

```nginx
# rl-lab nginx.conf - a rate limiting lab for 127.0.0.1 only. Not a production configuration.
worker_processes 1;
pid /run/nginx.pid;   # inside the container, as the official image does
error_log /dev/stderr notice;
events { worker_connections 256; }

http {
  # A log line that shows what the limiter saw: the connection address, the header, the status.
  log_format rl '$time_iso8601 $remote_addr xff="$http_x_forwarded_for" $request_method $uri -> $status limit=$limit_req_status';
  access_log /dev/stdout rl;

  # --- Zones: 1 MB of state holds about 16,000 addresses (nginx docs) ---
  limit_req_zone  $binary_remote_addr zone=perip:1m   rate=2r/s;     # by connection address
  limit_conn_zone $binary_remote_addr zone=connip:1m;
  # NAIVE key: the leftmost value of X-Forwarded-For, which the client can write.
  map $http_x_forwarded_for $leftmost { ~^\s*(?<first>[^,\s]+) $first; default $remote_addr; }
  limit_req_zone  $leftmost zone=naive:1m rate=2r/s;

  limit_req_status  429;
  limit_conn_status 429;
  limit_req_log_level warn;

  server {
    listen 8080;
    # --- Burst, delay and nodelay (the same 2 requests per second on each path) ---
    location = /strict  { limit_req zone=perip;                 alias /data/ok.txt; }
    location = /burst   { limit_req zone=perip burst=4 nodelay; alias /data/ok.txt; }
    location = /smooth  { limit_req zone=perip burst=4;         alias /data/ok.txt; }
    # Dry run: count and log what WOULD be refused, but refuse nothing. How to try a limit safely.
    location = /dry     { limit_req zone=perip; limit_req_dry_run on; alias /data/ok.txt; }
    # Make a 429 say how long to wait (RFC 6585 says a 429 MAY carry Retry-After).
    error_page 429 = @limited;
    location @limited { add_header Retry-After 1 always; return 429 "slow down\n"; }

    # --- Connections, not requests. /slow sends 20 KB at 2 KB per second, about 10 s per request ---
    location = /slow { limit_conn connip 2; limit_rate 2k; alias /data/blob.bin; }
    location = /free { limit_rate 2k; alias /data/blob.bin; }

    # --- Behind a proxy. The "edge" appends to X-Forwarded-For (nginx default behavior). ---
    location /naive/ { proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_pass http://127.0.0.1:9001/; }
    location /fixed/ { proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_pass http://127.0.0.1:9002/; }
  }

  # The "application" that trusts the header's leftmost value. This is the bug.
  server {
    listen 127.0.0.1:9001;
    location / { limit_req zone=naive; root /data; rewrite ^ /ok.txt break; }
  }

  # The "application" that trusts the header only when the connection comes from the proxy (127.0.0.1).
  # With real_ip_recursive off, nginx takes the LAST address in the header: the one the proxy appended.
  server {
    listen 127.0.0.1:9002;
    set_real_ip_from 127.0.0.1;
    real_ip_header X-Forwarded-For;
    real_ip_recursive off;
    location / { limit_req zone=perip; root /data; rewrite ^ /ok.txt break; }
  }

  # Two more copies of the "fixed" application, reachable DIRECTLY (as if the origin were left open).
  # 8081 trusts the header only from the proxy's address. 8082 trusts everybody: the classic mistake.
  server {
    listen 8081;
    set_real_ip_from 127.0.0.1;
    real_ip_header X-Forwarded-For;
    location / { limit_req zone=perip; root /data; rewrite ^ /ok.txt break; }
  }
  server {
    listen 8082;
    set_real_ip_from 0.0.0.0/0;
    real_ip_header X-Forwarded-For;
    location / { limit_req zone=perip; root /data; rewrite ^ /ok.txt break; }
  }
}
```

Start it:

```bash
$RT run -d --name rllab \
  -p 127.0.0.1:8080:8080 -p 127.0.0.1:8081:8081 -p 127.0.0.1:8082:8082 \
  -v "$PWD/nginx.conf:/etc/nginx/nginx.conf:ro" -v "$PWD/data:/data:ro" \
  docker.io/library/nginx:1.30.6-alpine
sleep 2; curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/free
```

PowerShell (**est.**):

```powershell
& $RT run -d --name rllab -p 127.0.0.1:8080:8080 -p 127.0.0.1:8081:8081 -p 127.0.0.1:8082:8082 `
  -v "${PWD}/nginx.conf:/etc/nginx/nginx.conf:ro" -v "${PWD}/data:/data:ro" `
  docker.io/library/nginx:1.30.6-alpine
Start-Sleep 2; (Invoke-WebRequest http://127.0.0.1:8080/free -SkipHttpErrorCheck).StatusCode
```

The first run pulls the image (a few tens of megabytes, est.). The check should print `200`. On a machine with SELinux, add `,Z` after `ro` on each `-v`. If a port is busy, stop what holds it or change the number on both sides of the colon in the command and in the exercises.

> **Screenshot to take yourself:** your terminal after the setup check prints `200`.
> Capture: the `run` command and the `200`.
> Look for: all three `-p` options start with `127.0.0.1:`, meaning nothing outside your machine can reach the lab.
> Redact: your username and the path in the prompt if they identify you.

**Teardown (do this when you finish):** `$RT rm -f rllab`. PowerShell: `& $RT rm -f rllab`. Then delete the `rl-lab` folder. Check nothing is left with `$RT ps -a`.

### Exercise 3: a client that sees 429 and Retry-After

First, a small client. Save as `hits.sh`, then `chmod +x hits.sh`. It sends `COUNT` requests one after another and prints each status, then the `Retry-After` of the last `429`.

```bash
#!/usr/bin/env bash
# hits.sh URL COUNT [EXTRA curl args...]  - sends COUNT requests back to back, prints one status per request,
# then the Retry-After header of the last 429 (if any). Loopback lab use only.
url=$1; n=$2; shift 2
codes=(); ra=""
for ((i = 0; i < n; i++)); do
  out=$(curl -s -o /dev/null -D - -w '%{http_code}' "$@" "$url")
  code=${out: -3}
  codes+=("$code")
  [[ $code == 429 ]] && ra=$(grep -i '^retry-after:' <<<"$out" | tr -d '\r')
done
echo "${codes[*]}"
[[ -n $ra ]] && echo "last 429 carried: $ra"
exit 0
```

PowerShell (**est.**, PowerShell 7), `hits.ps1`:

```powershell
# hits.ps1 URL [COUNT]  - sends COUNT requests back to back, prints one status per request,
# then the Retry-After of the last 429 (if any). Needs PowerShell 7 (-SkipHttpErrorCheck). Loopback lab use only.
param([Parameter(Mandatory)][string]$Url, [int]$Count = 8)
$codes = @(); $ra = ''
for ($i = 0; $i -lt $Count; $i++) {
    $r = Invoke-WebRequest -Uri $Url -SkipHttpErrorCheck -UseBasicParsing
    $codes += [int]$r.StatusCode
    if ($r.StatusCode -eq 429 -and $r.Headers.ContainsKey('Retry-After')) {
        $ra = 'Retry-After: ' + ($r.Headers['Retry-After'] -join ',')
    }
}
$codes -join ' '
if ($ra) { "last 429 carried: $ra" }
```

**Predict.** `/strict` allows 2 requests a second with **no burst**. If you send 8 requests back to back, how many get `200`? Then `/burst` (burst of 4, `nodelay`): how many? Then `/smooth` (burst of 4, **with** delay), sent one after the other: how many `429`s?

**Do.**

```bash
./hits.sh http://127.0.0.1:8080/strict 8; sleep 3
./hits.sh http://127.0.0.1:8080/burst  8; sleep 3
./hits.sh http://127.0.0.1:8080/smooth 8
```

(PowerShell: `.\hits.ps1 http://127.0.0.1:8080/strict 8`, and so on, with `Start-Sleep 3` between.)

**Check.** On 2026-10-22:

```text
200 429 429 429 429 429 429 429
last 429 carried: Retry-After: 1
200 200 200 200 200 429 429 429
last 429 carried: Retry-After: 1
200 200 200 200 200 200 200 200
```

- `/strict`: one request passes, the rest are refused. With no burst, the second request in the same half-second is already too fast.
- `/burst`: five pass (the one allowed, plus a burst of four) and the rest are refused, immediately. That is `nodelay`.
- `/smooth`: all eight pass, and the whole run takes about three and a half seconds. Nginx **delayed** the excess requests to hold the 2-per-second pace instead of refusing them, and because this client waits for each answer before sending the next, it never has more than the burst waiting. A client that sends them **at the same time** is refused:

```bash
seq 8 | xargs -P 8 -I{} curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/smooth | sort | uniq -c
```

Expect about five `200`s (the first immediately, then four paced half a second apart) and about three `429`s (the pace and the burst setting decide the exact split; I got five and three). The difference between sequential and parallel clients is exactly why concurrency limits exist.

The `Retry-After: 1` is there because the lab's config added it. The server did not have to; RFC 6585 says it MAY. Check what your own tools do if it is missing.

**Now the polite client.** Save as `polite.sh`. It waits for the number of seconds the server asked for, adds a little random jitter, and tries again.

```bash
#!/usr/bin/env bash
# polite.sh URL COUNT - gets URL COUNT times. On a 429 it waits for the Retry-After the server sent
# (plus a little random jitter so many clients do not all return at the same instant), then tries again.
url=$1; want=$2; got=0; tries=0; waited=0
while ((got < want)); do
  out=$(curl -s -o /dev/null -D - -w '%{http_code}' "$url"); code=${out: -3}; tries=$((tries + 1))
  if [[ $code == 200 ]]; then
    got=$((got + 1))
  elif [[ $code == 429 ]]; then
    ra=$(grep -i '^retry-after:' <<<"$out" | tr -d '\r' | awk '{print $2}')
    ra=${ra:-1}                                          # no header: fall back to one second
    nap=$(awk -v r="$ra" -v j="$RANDOM" 'BEGIN { printf "%.2f", r + (j % 100) / 400 }')
    waited=$(awk -v w="$waited" -v n="$nap" 'BEGIN { printf "%.2f", w + n }')
    sleep "$nap"
  else
    echo "unexpected status $code" >&2; exit 1
  fi
done
echo "got $got successes in $tries tries, slept $waited s in total"
```

PowerShell (**est.**), `polite.ps1`:

```powershell
# polite.ps1 URL [WANT] - gets URL until it has WANT successes. On a 429 it waits for the Retry-After the
# server sent (seconds form only) plus a little random jitter, then tries again. Needs PowerShell 7.
param([Parameter(Mandatory)][string]$Url, [int]$Want = 6)
$got = 0; $tries = 0; $slept = 0.0
while ($got -lt $Want) {
    $r = Invoke-WebRequest -Uri $Url -SkipHttpErrorCheck -UseBasicParsing; $tries++
    if ($r.StatusCode -eq 200) { $got++ }
    elseif ($r.StatusCode -eq 429) {
        $ra = 1.0                                       # no usable header: fall back to one second
        if ($r.Headers.ContainsKey('Retry-After')) { [void][double]::TryParse(($r.Headers['Retry-After'] -join ''), [ref]$ra) }
        $nap = $ra + (Get-Random -Minimum 0.0 -Maximum 0.25)
        $slept += $nap
        Start-Sleep -Milliseconds ([int]($nap * 1000))
    }
    else { throw "unexpected status $($r.StatusCode)" }
}
"got $got successes in $tries tries, slept $([math]::Round($slept, 2)) s in total"
```

```bash
./polite.sh http://127.0.0.1:8080/strict 6
```

On 2026-10-22 it printed `got 6 successes in 11 tries, slept 5.65 s in total`; yours will differ by a try or two because of the jitter and the timing. It waits as asked instead of hammering. It handles only the number-of-seconds form of `Retry-After` (the HTTP-date form falls back to one second here); a real client library handles both. Compare the 11 tries with a client that ignores the header and retries at once: it would send hundreds in the same five seconds, all refused, all costing the server work.

**Undo.** Nothing to undo; the limiter forgets within seconds.

### Exercise 4: connections, not requests

A client that sends nothing fast but holds connections open uses up the server differently. `/slow` serves a 20 KB file at 2 KB a second (about ten seconds a request) and allows 2 connections per address; `/free` is the same file with no connection limit.

**Predict.** Start four slow downloads at once on `/slow`, then four on `/free`. How many of each are refused?

**Do.**

```bash
for i in 1 2 3 4; do curl -s -o /dev/null -m 4 -w "slow$i %{http_code}\n" http://127.0.0.1:8080/slow & done; wait
for i in 1 2 3 4; do curl -s -o /dev/null -m 4 -w "free$i %{http_code}\n" http://127.0.0.1:8080/free & done; wait
```

(`-m 4` stops each after four seconds so you do not wait ten. PowerShell, **est.**: `1..4 | ForEach-Object -Parallel { (Invoke-WebRequest http://127.0.0.1:8080/slow -SkipHttpErrorCheck -TimeoutSec 4).StatusCode }` may be cut off by the timeout before it returns; use WSL or Git Bash for this one.)

**Check.** Two of the four `/slow` calls got `429` and two got `200`; all four `/free` calls got `200` (the order of the lines varies). A request-rate limit would not have caught this: each client made one request. The manual's rule that a connection is counted only once its header has been read matters: a client that opens a connection and sends nothing is **not yet counted** by `limit_conn`, which is why timeouts for slow headers also matter (est.: Nginx has separate timeout settings for that; none are used in this lab).

**Undo.** Nothing.

### Exercise 5: spoof `X-Forwarded-For`, then fix it

The lab has an "application" that sits behind the proxy on port 8080 in two forms. `/naive/` counts by the **leftmost** address in `X-Forwarded-For`, which the client can write. `/fixed/` trusts the header only on a connection from the proxy (`set_real_ip_from 127.0.0.1`) and takes the **last** address, the one the proxy appended. Ports 8081 and 8082 are two "fixed" applications that you can reach **directly**, as if someone left the origin open: 8081 trusts only the proxy's address; 8082 trusts everyone (`set_real_ip_from 0.0.0.0/0`), which is the classic mistake.

Save the script as `spoof.sh`. It sends ten requests honestly, waits three seconds, then sends ten more with a different made-up `X-Forwarded-For` each time (addresses from the documentation range 203.0.113.0/24, [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.txt)).

```bash
#!/usr/bin/env bash
# spoof.sh URL  - 10 quick requests to URL, once honest and once with a different
# made-up X-Forwarded-For on every request (documentation addresses, RFC 5737). Prints the status codes.
base=$1
honest=(); spoofed=()
for i in $(seq 1 10); do
  honest+=("$(curl -s -o /dev/null -w '%{http_code}' "$base")")
done
sleep 3                                   # let the limiter forget the honest burst
for i in $(seq 1 10); do
  spoofed+=("$(curl -s -o /dev/null -w '%{http_code}' -H "X-Forwarded-For: 203.0.113.$i" "$base")")
done
echo "honest : ${honest[*]}"
echo "spoofed: ${spoofed[*]}"
```

PowerShell (**est.**), `spoof.ps1`:

```powershell
# spoof.ps1 URL  - 10 quick requests to URL, once honest and once with a different made-up
# X-Forwarded-For on every request (documentation addresses, RFC 5737). Needs PowerShell 7.
param([Parameter(Mandatory)][string]$Url)
function Get-Code([hashtable]$Headers) {
    [int](Invoke-WebRequest -Uri $Url -Headers $Headers -SkipHttpErrorCheck -UseBasicParsing).StatusCode
}
$honest  = 1..10 | ForEach-Object { Get-Code @{} }
Start-Sleep -Seconds 3                          # let the limiter forget the honest burst
$spoofed = 1..10 | ForEach-Object { Get-Code @{ 'X-Forwarded-For' = "203.0.113.$_" } }
"honest : $($honest -join ' ')"
"spoofed: $($spoofed -join ' ')"
```

**Predict.** Which of the four targets lets the spoofer through?

**Do.**

```bash
chmod +x spoof.sh
for u in http://127.0.0.1:8080/naive/ http://127.0.0.1:8080/fixed/ http://127.0.0.1:8081/ http://127.0.0.1:8082/; do
  echo "$u"; ./spoof.sh "$u"; sleep 3
done
```

**Check.** On 2026-10-22:

```text
http://127.0.0.1:8080/naive/
honest : 200 429 429 429 429 429 429 429 429 429
spoofed: 200 200 200 200 200 200 200 200 200 200
http://127.0.0.1:8080/fixed/
honest : 200 429 429 429 429 429 429 429 429 429
spoofed: 200 429 429 429 429 429 429 429 429 429
http://127.0.0.1:8081/
honest : 200 429 429 429 429 429 429 429 429 429
spoofed: 200 429 429 429 429 429 429 429 429 429
http://127.0.0.1:8082/
honest : 200 429 429 429 429 429 429 429 429 429
spoofed: 200 200 200 200 200 200 200 200 200 200
```

- **Naive** (counts the client-written value): ten different lies, ten fresh counters, no limit at all.
- **Fixed behind the proxy**: the proxy appended the true connection address on the right, the application trusted only that, and the lies did nothing.
- **Direct, trusting only the proxy (8081)**: the connection did not come from `127.0.0.1`, so the header was ignored and the spoof failed. This is the point of listing the trusted proxy by address.
- **Direct, trusting everyone (8082)**: the application believed the header from the world, and the spoof worked. Same code as the fixed one, one wrong trust list.

An honest limit on the container's own view: the container's port forwarding makes every request appear to come from one private address (the log shows it), so in this lab all "clients" share one counter. That is itself the NAT problem from earlier. Read the log (next exercise) to see both views. In the pasted logs on this page I replaced that private address with `192.0.2.10`; yours will show your runtime's own address, and with Docker it will be a different one (est.).

**Undo.** Nothing to undo; wait three seconds between runs.

### Exercise 6: read the evidence, then try the limit safely

Everything the limiter did is in the container's log. Count refusals and see who and when.

```bash
$RT logs rllab 2>&1 | grep -c -- 'limit=REJECTED'
$RT logs rllab 2>&1 | grep -- 'limit=REJECTED' | awk '{print substr($1,1,16)}' | sort | uniq -c    # per minute
$RT logs rllab 2>&1 | grep -- 'limit=REJECTED' | awk '{print $2}' | sort | uniq -c                  # per key (address)
$RT logs rllab 2>&1 | grep -- 'xff="203' | tail -3
```

PowerShell (**est.**):

```powershell
(& $RT logs rllab 2>&1 | Select-String 'limit=REJECTED').Count
& $RT logs rllab 2>&1 | Select-String 'limit=REJECTED' | ForEach-Object { $_.Line.Substring(0,16) } | Group-Object | Select-Object Count, Name
```

You will see log lines of this shape (the address replaced with `192.0.2.10`):

```text
2026-10-22T21:19:08+00:00 192.0.2.10 xff="203.0.113.9" GET /fixed/ -> 429 limit=-
2026-10-22T21:19:08+00:00 192.0.2.10 xff="203.0.113.10, 192.0.2.10" GET /ok.txt -> 429 limit=REJECTED
```

The first line is the **proxy's** view: it answered `429` because the application behind it did, and it did not itself limit (`limit=-`). The second is the **application's** view: its limiter refused (`limit=REJECTED`), and the header it saw was the client's lie followed by the address the proxy appended. This is also the evidence that shows spoofing: a header in which the first value is not a plausible client. Detection from this: alert when `xff` begins with a value that is not the connection address and the same connection address is refused many times.

**Dry run.** The `/dry` path has the same limit as `/strict` and `limit_req_dry_run on`. Send five requests:

```bash
sleep 3; ./hits.sh http://127.0.0.1:8080/dry 5
$RT logs rllab 2>&1 | grep '/dry' | grep -v warn | tail -3
```

All five return `200`, and the log says `limit=REJECTED_DRY_RUN` for the four that **would** have been refused. This is how to try a limit on live traffic without risking a real user: watch what it would block, adjust, and only then turn it on.

**Undo.** Nothing. To remove the lab, run the teardown line from the setup.

### Exercise 7: the firewall layer, in a private namespace

A Linux **network namespace** is a private copy of the networking: its own interfaces, routing table, firewall rules and many kernel network settings. `unshare -rn` gives your command a new user namespace (you appear as root inside it, with no real privileges outside) and a new network namespace that has only a loopback interface, switched off. Rules you add there exist only inside it and vanish when the command ends; they never touch the host's firewall. Nothing leaves the namespace, because it has no network connection to anywhere.

This needs a Linux with unprivileged user namespaces enabled. Some distributions restrict them (Ubuntu 24.04 does by default through AppArmor, est.); if `unshare -rn true` fails, you can read this exercise instead, or run it inside a throwaway virtual machine. It is Linux only; on Windows, WSL 2 should work (est., not tried). Windows PowerShell has no equivalent here.

**nftables.** Save as `nsdemo.sh`, `chmod +x nsdemo.sh`, and run `unshare -rn ./nsdemo.sh nft`. The same script takes `ipt` for the iptables version below.

```bash
#!/usr/bin/env bash
# nsdemo.sh nft|ipt - runs INSIDE `unshare -rn`: a private network namespace with only its own loopback.
# Rules added here vanish when this script exits and never touch the host's real firewall.
set -u
case ${1:-nft} in nft | ipt) ;; *) echo "usage: nsdemo.sh nft|ipt" >&2; exit 2 ;; esac
ip link set lo up
python3 -I - <<'PY' &
import socket
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 9000)); s.listen(64)
while True:
    c, _ = s.accept(); c.close()
PY
srv=$!
sleep 0.5
try() {   # open N connections as fast as possible (0.3 s timeout each); print how many got through
  python3 -I - "$1" <<'PY'
import socket, sys
n, ok = int(sys.argv[1]), 0
for _ in range(n):
    s = socket.socket(); s.settimeout(0.3)
    try:
        s.connect(("127.0.0.1", 9000)); ok += 1
    except OSError:
        pass
    finally:
        s.close()
print(f"{ok} of {n} connections got through")
PY
}
echo "--- before any rule"; try 12
case ${1:-nft} in
  nft)
    nft -f - <<'NFT'
table inet lab {
  set rate_new { type ipv4_addr; flags dynamic; timeout 60s; }
  chain input {
    type filter hook input priority 0; policy accept;
    iifname "lo" tcp dport 9000 ct state new add @rate_new { ip saddr limit rate over 5/second burst 3 packets } counter drop
  }
}
NFT
    show() { nft list chain inet lab input | grep counter; } ;;
  ipt)
    iptables -A INPUT -i lo -p tcp --dport 9000 -m conntrack --ctstate NEW \
      -m hashlimit --hashlimit-above 5/second --hashlimit-burst 3 --hashlimit-mode srcip --hashlimit-name lab -j DROP
    show() { iptables -L INPUT -v -n | tail -2; } ;;
esac
echo "--- rule: more than 5 new connections per second per source address (burst 3) are dropped"; try 12
echo "--- the counter the rule kept:"; show
kill "$srv" 2>/dev/null
```

**Predict.** Twelve connections, as fast as one program can open them, to a listener on port 9000. Before the rule: how many get through? After a rule that drops new connections over 5 a second per source address, with a burst of 3?

**Check.** On 2026-10-22, three runs in a row printed the same:

```text
--- before any rule
12 of 12 connections got through
--- rule: more than 5 new connections per second per source address (burst 3) are dropped
8 of 12 connections got through
--- the counter the rule kept:
    ... limit rate over 5/second burst 3 packets } counter packets 4 bytes 240 drop
```

Eight got through and four were dropped, and the counter says four packets were dropped. I did not derive the exact arithmetic of "8" from the kernel's rules (it is the rate plus the burst plus timing, est.); the pattern is the point: a burst up to the allowance passes, the rest are cut. A dropped SYN gives the client no answer at all, so each of the four waited out its timeout. That silence is different from the `429` a web layer sends. The firewall cannot send a polite reason.

**iptables.** The same limit written with `hashlimit`, the older tool (on modern systems `iptables` is often a front end for nftables; mine reported `iptables v1.8.11 (nf_tables)`). Run `unshare -rn ./nsdemo.sh ipt`. Result on 2026-10-22: `12 of 12`, then `8 of 12`, and the rule's counter listing showed `4` packets dropped, with `limit: above 5/sec burst 3 mode srcip`.

**SYN cookies and the kernel's limits.** Save as `syn.sh`, run `unshare -rn ./syn.sh`. It reads the kernel's own settings and then floods a listener that never accepts, and shows the counters.

```bash
#!/usr/bin/env bash
# syn.sh - runs INSIDE `unshare -rn`, so every setting below belongs to this private namespace only.
# A listener that never calls accept(), then 20 quick connection attempts, with the kernel's own counters
# before and after. Run 1 uses the default (syncookies only when the SYN queue overflows); run 2 sets
# tcp_syncookies=2 (always send cookies), which the kernel documentation offers as a way to test.
ip link set lo up
echo "tcp_syncookies      = $(cat /proc/sys/net/ipv4/tcp_syncookies)"
echo "tcp_max_syn_backlog = $(cat /proc/sys/net/ipv4/tcp_max_syn_backlog)"
echo "somaxconn           = $(cat /proc/sys/net/core/somaxconn)"
if [[ -r /proc/sys/net/netfilter/nf_conntrack_max ]]; then
  echo "nf_conntrack_max    = $(cat /proc/sys/net/netfilter/nf_conntrack_max)"
else
  echo "nf_conntrack_max    : not available in this namespace"
fi
flood() {   # flood PORT BACKLOG
python3 -I - "$1" "$2" <<'PY'
import socket, sys, time
port, backlog = int(sys.argv[1]), int(sys.argv[2])
def counters():
    lines = open("/proc/net/netstat").read().splitlines()
    for h, v in zip(lines[::2], lines[1::2]):
        if h.startswith("TcpExt:"):
            d = dict(zip(h.split()[1:], map(int, v.split()[1:])))
            return {k: d[k] for k in ("ListenOverflows", "SyncookiesSent", "SyncookiesRecv") if k in d}
srv = socket.socket(); srv.bind(("127.0.0.1", port)); srv.listen(backlog)    # never accepted
before = counters()
clients = []
for _ in range(20):
    c = socket.socket(); c.setblocking(False)
    try: c.connect(("127.0.0.1", port))
    except BlockingIOError: pass
    clients.append(c)
time.sleep(0.5)
print("  before:", before); print("  after :", counters())
PY
}
echo "run 1: default syncookies, listen backlog 1";  flood 9100 1
sysctl -qw net.ipv4.tcp_syncookies=2
echo "run 2: tcp_syncookies=2, listen backlog 128";  flood 9101 128
```

On 2026-10-22:

```text
tcp_syncookies      = 1
tcp_max_syn_backlog = 2048
somaxconn           = 4096
nf_conntrack_max    = 262144
run 1: default syncookies, listen backlog 1
  before: {'ListenOverflows': 0, 'SyncookiesSent': 0, 'SyncookiesRecv': 0}
  after : {'ListenOverflows': 18, 'SyncookiesSent': 0, 'SyncookiesRecv': 0}
run 2: tcp_syncookies=2, listen backlog 128
  before: {'ListenOverflows': 18, 'SyncookiesSent': 0, 'SyncookiesRecv': 0}
  after : {'ListenOverflows': 18, 'SyncookiesSent': 20, 'SyncookiesRecv': 20}
```

Read this carefully, because it surprised me. In run 1, a listener with a tiny accept queue (backlog 1) overflowed (18 `ListenOverflows`), but **no SYN cookies were sent**: the kernel's documentation says cookies are sent when the **SYN backlog** overflows, and that is a different queue, sized by `tcp_max_syn_backlog` (2048 here), not by the program's `listen` call. A full accept queue just drops. In run 2, setting `tcp_syncookies=2` (the documentation's way "to test which effects syncookies have to your network connections") made the kernel send a cookie for every connection: `SyncookiesSent` and `SyncookiesRecv` both went to 20, which means the cookies worked as designed, because each client's final ACK validated and rebuilt the connection with nothing stored in between. The settings printed are this namespace's; yours will differ. `nf_conntrack_max` was readable here; it may not be on your system (est.).

**Undo.** Nothing: the namespace, its rules and its sysctl change ended with each command. Run `sudo nft list ruleset` on the host if you want proof that nothing changed there (it needs your password; I did not run it as root for this page).

### Exercise 8: a token bucket per API key, with a quota

Back to Python. One script starts a tiny API on `127.0.0.1` (a random free port), makes two API keys **at run time** (random values that are never printed or saved), and shows: a rate limit per key, a different bucket per key, a stricter limit for callers with no key (counted by address), `Retry-After` computed exactly from the bucket, and a **quota** that does not come back in seconds.

**Predict.** Key A makes 8 quick calls. Key B then makes 3. Does key A's trouble affect key B?

**Do.** Save as `apikeys.py`, run `python3 -I apikeys.py` (it takes about eight seconds).

```python
# apikeys.py - a token bucket per API key, plus a separate quota, on 127.0.0.1 only.
# Keys are made up at run time and never printed; the script shows their labels instead.
import http.server, json, math, secrets, threading, time, urllib.request, urllib.error

CAPACITY, REFILL = 5, 1.0          # per key: 5-token bucket, one token back each second (the rate limit)
QUOTA = 12                         # per key: 12 requests in total in this run (the quota)
ANON_CAPACITY, ANON_REFILL = 2, 0.2   # callers with no key: counted by connection address instead

class Bucket:
    def __init__(self, cap, refill):
        self.cap, self.refill, self.tokens, self.last, self.used = cap, refill, float(cap), time.monotonic(), 0
    def take(self):
        now = time.monotonic()
        self.tokens = min(self.cap, self.tokens + (now - self.last) * self.refill)
        self.last = now
        if self.tokens >= 1:
            self.tokens -= 1
            self.used += 1
            return True, 0
        return False, math.ceil((1 - self.tokens) / self.refill)   # whole seconds until one token is back

buckets, lock = {}, threading.Lock()

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            who, make = "key:" + auth[7:], lambda: Bucket(CAPACITY, REFILL)
        else:
            who, make = "addr:" + self.client_address[0], lambda: Bucket(ANON_CAPACITY, ANON_REFILL)
        with lock:
            b = buckets.setdefault(who, make())
            if who.startswith("key:") and b.used >= QUOTA:
                ok, wait, why = False, 86400, "quota used up"      # a quota does not refill in seconds
            else:
                ok, wait = b.take()
                why = "rate limit"
            left = int(b.tokens)
        self.send_response(200 if ok else 429)
        self.send_header("X-RateLimit-Remaining", str(left))
        if not ok:
            self.send_header("Retry-After", str(wait))
        self.end_headers()
        self.wfile.write(json.dumps({"ok": ok, **({} if ok else {"why": why})}).encode())

def call(port, key=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/")
    if key:
        req.add_header("Authorization", "Bearer " + key)
    try:
        r = urllib.request.urlopen(req)
        return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Retry-After")

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
key_a, key_b = secrets.token_hex(8), secrets.token_hex(8)       # run-time secrets: never printed

print("key A, 8 quick calls :", [call(port, key_a)[0] for _ in range(8)])
print("key B, 3 quick calls :", [call(port, key_b)[0] for _ in range(3)], "<- B has its own bucket")
print("no key, 4 quick calls:", [call(port)[0] for _ in range(4)], "<- counted by address")
code, wait = call(port, key_a)
print(f"key A again          : {code}, Retry-After: {wait}")
time.sleep(int(wait) + 0.1)
print("after waiting        :", call(port, key_a)[0])
for _ in range(20):                                              # spend the quota politely, one per second
    code, wait = call(port, key_a)
    if code == 429 and int(wait) >= 3600:
        break
    time.sleep(1.05 if code == 429 else 0.0)
print(f"key A when the quota is gone: {code}, Retry-After: {wait} s, a day, not a second")
srv.shutdown()
```

**Check.** On 2026-10-22:

```text
key A, 8 quick calls : [200, 200, 200, 200, 200, 429, 429, 429]
key B, 3 quick calls : [200, 200, 200] <- B has its own bucket
no key, 4 quick calls: [200, 200, 429, 429] <- counted by address
key A again          : 429, Retry-After: 1
after waiting        : 200
key A when the quota is gone: 429, Retry-After: 86400 s, a day, not a second
```

Five calls fit in key A's bucket and three were refused; key B had its own full bucket and was not affected; the no-key caller got a smaller allowance and was counted by address (that is the NAT problem again for anyone not using a key); the `429` after the wait carried the time to the next token; and when the quota ran out, `Retry-After` was a day, because waiting a second does not refill a quota. A client that treats both the same will keep hammering a door that is shut for the month. The server code is also a reminder of what you must decide: the bucket size, the refill rate, what to do for keyless callers, and what a refusal costs the server. Real systems also expire idle buckets; this toy keeps them for the life of the process.

**Undo.** The server stops when the script ends; nothing is written to disk. The two keys existed only in memory.

## Optional: your own accounts

Nothing above needs an account. If you want to see a CDN-level limit on something you own, this uses your own accounts and domain. The reading and exercises on this page are free and always will be; this part uses your own provider bill. I did not do this part. The steps and menu names are read from Cloudflare's documentation (2026-10-22) and are **est.** as a procedure.

> **Warning.** Do this only on a domain you own, with a test path you create, and never on this project's domains.

**Cost and teardown, first.** Cloudflare's rate limiting page (read 2026-10-22) lists rate limiting rules on the Free plan, with one rule that counts by IP address with a ten-second period; more rules and keys on paid plans. I read no price for this page; read the current plans page and [How money works in the cloud](How-Money-Works-in-the-Cloud.md) first, and use the Free plan. Teardown: delete the rule (**Security**, **Security rules**, the rate limiting rule, **Delete**; menu names est.), and confirm the dashboard shows no rate limiting rule. The [DNS and Cloudflare lesson](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) covers getting a domain behind Cloudflare.

**Steps.** Create a rule matching a path such as `/rl-test`, counting by IP, with a low threshold, and set the action to **Log** first (the documentation recommends this). Send a few requests from your own machine to your own site, look at the Security Events or analytics for the matches, then change the action to **Block** and watch the `429`. Look for the header the response carries and for whether `Retry-After` appears (est.: I do not know whether it does). Then delete the rule.

## Build, break, detect, evade, defend

The same loop the rest of the project uses ([Why this exists](Why-This-Exists.md)), run on a limiter. You need the Nginx lab and the scripts from Exercises 3 to 6, and the simulations from Exercises 1 and 2. All of it runs on your computer against your own container; nothing is sent anywhere else.

**Build.** The `/strict` rule: two requests a second per connection address. It also has a log line that records the result of the limiter, and you read it in Exercise 6. You built a limiter, you can say what it counts by, and you know it answers `429` with `Retry-After: 1`.

**Break.** Take the rule apart from the outside, in three ways, all of which you have already done:

1. **Lie about the key.** Send a different `X-Forwarded-For` on each request to `/naive/` (Exercise 5). Ten requests, ten fresh counters, no limit.
2. **Find the side door.** Send the same lie directly to port 8082, the application that trusts every address. Same result with the "fixed" code, because the trust list was wrong.
3. **Stay under the line.** In Exercise 1, scenario 3, a client sending exactly at the average rate was never refused by any of the four algorithms.

**Detect.** Predict first: what would you see in the logs from each of those three?

- The header lie leaves a line where `xff` starts with an address that is not the connection address, and where the same connection address keeps coming back. Count distinct `xff` values per connection address (Exercise 6 prints the lines). Hundreds of distinct values from one address in a minute is not a household.
- The side door shows as requests hitting the application's port directly and not through the proxy. The lab logs both listeners; a real system would compare "requests the application saw" with "requests the proxy forwarded". A mismatch means traffic is bypassing the front.
- The slow client leaves **nothing** unusual in a per-minute rate: that is the point. What it leaves is a long-window pattern: the same key, at a perfectly regular interval, for hours, against the same path. A baseline of how real users behave on that path (see [baselines](Logs-SIEM-and-Detection-Basics.md#rules-baselines-and-the-two-ways-to-be-wrong)) catches it; a threshold does not.
- The Nginx dry-run status (`REJECTED_DRY_RUN`) and Cloudflare's Log action are the detection of **your own** limit before it bites.

**Evade.** Now describe the careful attacker, in words and on your own toy only.

- **Slow and low.** Stay under the rate and use the full time: one guess per account per hour, across a million accounts, is a million guesses a day that no per-account limit sees. The defender watches **totals over a long window** and counts distinct accounts tried from one source or one network.
- **Distributed.** Many addresses, one request each (Exercise 2). The defender counts by what does not rotate (the account, the path, the product being scraped), and puts a global ceiling on what is expensive.
- **Imitation.** Send the headers, cookies and timing of a real browser, so a challenge or reputation check passes. The defender looks at behavior over a session, not one request.
- **Spread across the edge.** Because Cloudflare's counters are per data center, traffic spread across regions can stay under each. The defender uses a key that is global in the application, behind the edge.
- **Go around.** Find the origin's real address and skip the edge entirely. The defender allows only the edge's address ranges (or a tunnel, or an origin certificate check) at the origin, and does not publish the origin's address in DNS history or error pages (est.).
- **Abuse the defense.** Deliberately fail logins for a victim's account to lock them out, or send a flood from addresses forged to look like a good customer so the limiter blocks the customer. The defender prefers delays and challenges to hard lockouts, and does not count requests whose sender could not have completed a handshake.

None of this is a reason not to limit. It is the reason limits come in layers, with different keys, and with logs.

**Defend.** What changes:

1. Name the reason (volume, guessing, scraping, cost, weak backend) before choosing the number.
2. Pick the key the layer can actually trust, and the second key that does not rotate.
3. Trust a forwarded header only from the proxy that wrote it, and close the side door.
4. Make outer layers looser and inner layers stricter, with the database pool never first.
5. Dry-run, then enforce, then watch the false positives.
6. Choose fail open or fail closed for each layer and test it.
7. Log every refusal with its key and layer; alert on changes, not every block.
8. Send `429` with `Retry-After`, and write clients that obey it.

### Flip the board

You built the limiter. Now do the other two jobs.

**The attacker.** You have permission to test your own lab (and only that). The owner runs "two requests a second per address" at a login path, with an account lockout at ten failures. List four ways to get more guesses in, and for each one thing the defender can watch to catch it anyway. (Answers below.)

<details>
<summary>What to find</summary>

1. **Rotate addresses.** A defender counts failures per account, not only per address.
2. **Slow down to just under the rate.** A defender watches totals over hours and a regular rhythm.
3. **Spray one password across many accounts**, so no account reaches ten. A defender counts distinct accounts tried from one source or network, and the service-wide failure rate.
4. **Lie in `X-Forwarded-For`** if the application trusts it. A defender checks that the header's rightmost value is the proxy's observation and logs the connection address next to the header.
5. **Hit the origin directly.** A defender restricts the origin to the edge and compares edge and origin counts.

</details>

**The reviewer.** You are given this proposed change to a shop's checkout API and asked if it is ready to ship. Find at least five problems without running it.

```text
Change: add a rate limit to /api/checkout.
  - Count by the first address in X-Forwarded-For.
  - 5 requests per minute per address, fixed window, reset on the minute.
  - If the limit store (Redis) is down, allow the request.
  - Return 500 when the limit is exceeded.
  - No logging, "to keep the logs small".
```

<details>
<summary>What to find</summary>

1. **The key is client-writable.** The first address in `X-Forwarded-For` is what the client chose. Anyone can send a new one each time. Use the address the trusted proxy added, and only trust the header from the proxy.
2. **Five a minute per address will block shared addresses** (an office buying together, a shop's own staff entering orders, a mobile carrier) and is trivially exceeded by one customer who retries after an error. It also says nothing about the thing that matters on a checkout: attempts per card or per account (card testing).
3. **A fixed window** allows ten requests across a boundary and has a sharp edge on reset. A sliding window or a token bucket is gentler for real users.
4. **Fail open on the store, on a payment endpoint.** When Redis is down, the protection vanishes at the moment the service is least healthy. Decide on purpose; for a payment path a local, stricter fallback is likely better than allowing everything (est.).
5. **A `500` is the wrong status.** It tells clients and monitors the server broke; it will page the on-call engineer and clients will retry at once. Use `429` with `Retry-After`.
6. **No logging** means nobody can tell a limit from an outage, measure false positives or detect an attack. Log every refusal with its key.
7. **No dry run, owner or review date**, and no test of what happens when the limit is hit.

</details>

## A threat model for a limiter

A short one, in the format of [Threat model](Threat-Model.md). The system: a limiter at some layer, protecting a service behind it. The point of writing it down is to see that the limiter is itself an asset to protect and a thing that can be turned against you.

**Assets.** The service's availability; the accounts behind a login; the weak backend (a database, a metered API); the bill; the limiter's own state and configuration; the logs that show what it did.

**Actors.** A single script (scraper or guesser); a distributed botnet or proxy pool; a slow, patient attacker; someone using your service as a weapon against a third party (reflection); a legitimate heavy user; an insider or a mistaken change; the provider whose limits sit under yours.

**Trust boundaries.** Client to edge; edge to origin (the header and the address you believe); proxy to application (the forwarded header); application to its shared state; application to database.

| Abuse case | Impact | What the attacker needs | Mitigation | How to verify |
|---|---|---|---|---|
| Forge the forwarded header to get a fresh counter | The limit does nothing | The application trusts a client-writable value | Trust only the proxy's address; count the rightmost trusted value; close direct access | Exercise 5, all four targets; a test that sends a spoofed header and expects `429` |
| Reach the origin around the edge | Edge limits and rules skipped | The origin's address and a reachable port | Allow only the edge's ranges, a tunnel or origin authentication at the origin | Try the origin directly from a non-edge address you own; expect refusal |
| Spread traffic over many addresses (distributed) | Per-address limits rarely fire | A botnet or proxy pool, or an IPv6 block | Count by a key that does not rotate; global ceiling on expensive endpoints; challenges; reputation | Simulate with Exercise 2; alert on total failures per account |
| Slow and low | Passes every rate; the cost accumulates | Patience | Long-window totals, distinct-account counts, baselines | Replay a slow sequence through the detection rule |
| Lock a victim out (abuse the defense) | A person cannot log in | Knowledge of the username | Delay and challenge in preference to hard lockout; recovery path that still works | Fail a test account's logins on purpose and confirm the owner can still recover |
| Exhaust the limiter's own memory or table | New keys refused or old state evicted | Many distinct keys | Size zones; LRU eviction; key on bounded values; alert on evictions | Fill a small zone in the lab and read the log (the manual describes the behavior) |
| The shared store goes down | Fail open (no protection) or closed (outage) | A fault or an attack on the store | A tested policy per layer; local stricter fallback | Stop the store in a lab; observe the answers |
| Retry storm from clients | A short overload becomes a long one | A `429` without `Retry-After`, or clients that ignore it | `Retry-After`, jitter, retry caps at one layer | Exercise 3's two clients, counted |
| Reflection through your DNS or UDP service | Your server hits a victim; your IP gets a bad reputation | A server that answers anyone | Response rate limiting; close open resolvers | Query rates against your own authoritative server in a lab (not run here) |
| Mistaken or unreviewed change | Real users blocked | A config edit | Dry run; review; dated change record; false-positive metric | Exercise 6's dry run |

**Residual risk.** A patient, well-resourced attacker with many addresses and human-like behavior is **not stopped** by rate limiting; they are made slower and more expensive, which is its honest job. A limit is a speed bump with a log, and the log is how you notice the attacker is still there.

## Checkpoint

- Name the five reasons to rate limit, and say which one a plain request-rate cap does **not** help.
- Which of the four algorithms allowed ten requests in one second in Exercise 1, and why?
- Why is "what to count by" the hard part? Give two keys and one way each breaks.
- What does a limiter that trusts the first address in `X-Forwarded-For` actually count? What does Nginx's `set_real_ip_from` change?
- For three layers of your choice, say what each can see, what it cannot, and one way each fails.
- What is the difference between `429` and `503`, and what does `Retry-After` let a client do?
- A teammate says "we have a Cloudflare rate limit, so the login is protected." What three questions do you ask? (Can the origin be reached without it? What does it count by? Where do the logs of what it blocked go?)
- Why does fail open versus fail closed need an explicit decision?

Answers are in the sections above.

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| A limit seems to do nothing | Something answers before the limiter (an Nginx `return` runs in the rewrite phase, before `limit_req`); or the key is empty so nothing is counted; or the traffic goes around the layer | What serves the location; `$limit_req_status` in the log; whether the origin is reachable directly |
| Everyone is blocked at once | The key is the proxy's address (every client looks the same); or a shared NAT | Log the key; trust the forwarded header only from the proxy |
| Nobody is ever blocked | The key is client-writable (spoofed header), or traffic is spread across more keys than the limit sees | Send a spoofed request; count by something that does not rotate |
| `429`s with no explanation, from a layer nobody owns | Two layers with different numbers; the outer one is stricter than the inner | Write down each layer's limit and owner |
| The limit works in testing and not in production | Several instances each count alone; the shared zone is not shared | One instance, or a shared store; compare the fleet's total allowance |
| Clients make the overload worse | They retry at once on a `429` | `Retry-After`, jitter and a retry cap; fix the client |
| Alerts on every block | The rule is "each refusal" rather than a change | Alert on rate of refusals and top keys, with a baseline |
| A container will not start in the lab | A port is in use, or SELinux blocks the mount | Change the port on both sides; add `,Z` to the mounts |
| `unshare -rn` says operation not permitted | Unprivileged user namespaces are restricted on this system | Read the exercise instead, or use a throwaway virtual machine (est.) |
| A PowerShell script will not run | Execution policy, or the wrong folder, or PowerShell 5.1 (the scripts need 7) | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for this window only, `.\` before the name, and `$PSVersionTable.PSVersion` (**est.**) |

## Claims register

All read-only requests with `curl`, retrieved 2026-10-22 unless stated. "Run" means I ran it that day on the machine described in the status banner.

| Claim | Source | Status |
|---|---|---|
| Nginx `limit_req` uses the "leaky bucket" method; key, `burst`, `nodelay`, `delay` (1.15.7), `limit_req_status` (default 503), `limit_req_dry_run` (1.17.1), `limit_req_log_level`; requests with an empty key are not accounted; 1 MB holds about 16 thousand 64-byte or 8 thousand 128-byte states; least recently used state removed, then an error; `sync` listed under the commercial subscription; `$limit_req_status` (1.17.6) values `PASSED`, `DELAYED`, `REJECTED` and dry-run variants | [ngx_http_limit_req_module](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html) | Read; behavior of burst, nodelay, delay, dry run and the status variable run in the lab |
| `limit_conn` counts a connection only when a request is being processed and the whole header has been read; each concurrent request counts in HTTP/2 and HTTP/3 | [ngx_http_limit_conn_module](https://nginx.org/en/docs/http/ngx_http_limit_conn_module.html) | Read; the two-connection limit run |
| `set_real_ip_from`, `real_ip_header`, `real_ip_recursive` semantics (last address when off; last non-trusted when on); the module is not built by default | [ngx_http_realip_module](https://nginx.org/en/docs/http/ngx_http_realip_module.html) | Read; the image used had the module and the `off` behavior was run |
| `limit_req` and `limit_conn` run in the preaccess phase, after the rewrite phases | [Nginx development guide](https://nginx.org/en/docs/dev/development_guide.html) | Read; the consequence (`return` skipping the limit) observed while building the lab |
| Cloudflare rate limiting rule parameters (characteristics, period, requests, mitigation timeout); plan table (Free: IP only, 10 s period, 1 rule at the time of reading; richer keys on higher plans); default block status 429; "not designed to allow a precise number of requests"; counters per data center | [Rate limiting rules](https://developers.cloudflare.com/waf/rate-limiting-rules/), [parameters](https://developers.cloudflare.com/waf/rate-limiting-rules/parameters/), [request rate](https://developers.cloudflare.com/waf/rate-limiting-rules/request-rate/) | Read. Plans change; check the page. **Not run:** I used no Cloudflare account |
| "IP with NAT support" relies on the `_cfuvid` cookie; visitors who do not accept cookies share one counter | [parameters](https://developers.cloudflare.com/waf/rate-limiting-rules/parameters/) | Read |
| Cloudflare recommends deploying a rule with the Log action first | [Find an appropriate rate limit](https://developers.cloudflare.com/waf/rate-limiting-rules/find-rate-limit/) | Read |
| Cloudflare counting expressions can include the response code; the guidance warns about path normalization | [Rate limiting best practices](https://developers.cloudflare.com/waf/rate-limiting-rules/best-practices/) | Read |
| `CF-Connecting-IP` and `X-Forwarded-For` behavior; origin protection options (allowlist ranges, Authenticated Origin Pulls, Tunnel) | [Cloudflare HTTP headers](https://developers.cloudflare.com/fundamentals/reference/http-headers/), [Protect your origin server](https://developers.cloudflare.com/fundamentals/security/protect-your-origin-server/) | Read |
| HAProxy stick tables, `http_req_rate(<period>)`, `track-sc0`, `sc_http_req_rate`, `deny` default 403 and `deny_status`, `peers`; IPv4 mapped on IPv6 tables | [HAProxy 3.0 configuration manual](https://docs.haproxy.org/3.0/configuration.html) (version 3.0.30-2 as fetched) | Read. **Not run:** the snippet is an example of shape |
| nftables dynamic sets and meters (`update @set { ip saddr limit rate ... }`), meters replace iptables hashlimit, `ct count` since 4.18 | [nftables wiki: Meters](https://wiki.nftables.org/wiki-nftables/index.php/Meters) (page last edited 2023-08-15) | Read; a meter-style rule with `add` and `limit rate over ... burst` run in a private namespace on nftables 1.1.3 |
| `limit` is a token bucket filter; `hashlimit` rate-limits per group (source, destination, port) | [iptables-extensions](https://ipset.netfilter.org/iptables-extensions.man.html) | Read; `hashlimit --hashlimit-above 5/second --hashlimit-burst 3 --hashlimit-mode srcip` run in a private namespace |
| `tcp_syncookies` default 1, sent when the SYN backlog overflows, "fallback facility", can degrade services, value 2 sends always; `tcp_max_syn_backlog` is per listener; `nf_conntrack_max` entries are added twice | [Kernel networking sysctl](https://docs.kernel.org/networking/ip-sysctl.html), [nf_conntrack sysctl](https://docs.kernel.org/networking/nf_conntrack-sysctl.html) | Read; the counters in the SYN exercise run |
| SYN cookies encode connection state in the SYN-ACK sequence number and allocate no state; they are incompatible with some TCP options | [RFC 4987](https://www.rfc-editor.org/rfc/rfc4987.txt) | Read section 3.6 |
| fail2ban scans logs and updates firewall rules to ban addresses; it cannot eliminate the risk of weak authentication; IPv6 matching since v0.10 | [fail2ban README](https://github.com/fail2ban/fail2ban/blob/master/README.md) | Read. **Not run:** fail2ban was not installed |
| BIND `rate-limit`: credit or token bucket per identical response and client; intended for authoritative servers; slows some applications on recursive servers; closing open recursive servers is better | [BIND 9 reference](https://bind9.readthedocs.io/en/latest/reference.html) | Read. **Not run:** the snippet is an example of shape |
| Unbound `ratelimit` (per-zone recursion queries; not spoofed reflection) and `ip-ratelimit` (per client address, before the cache; valid DNS cookie bypasses it); both marked experimental | [unbound.conf manual](https://unbound.docs.nlnetlabs.nl/en/latest/manpages/unbound.conf.html) | Read. **Not run** |
| 429 Too Many Requests; the response MAY include `Retry-After`; the RFC does not define how users are identified or requests counted; 429 responses MUST NOT be stored by a cache | [RFC 6585 section 4](https://www.rfc-editor.org/rfc/rfc6585.txt) | Read |
| `Retry-After` is an HTTP date or a number of seconds | [RFC 9110 section 10.2.3](https://www.rfc-editor.org/rfc/rfc9110.txt) | Read |
| `RateLimit-Policy` and `RateLimit` header fields are defined by an Internet-Draft (revision 11, expires 24 November 2026); a draft, not a standard | [draft-ietf-httpapi-ratelimit-headers](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/) | Read the header and status; may be revised or expire |
| `X-Forwarded-For`: leftmost values are client-writable; only addresses added by a trusted proxy may be used for rate limiting; rightmost is the nearest hop | [MDN: X-Forwarded-For](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Forwarded-For) | Read |
| Home sites should be given significantly more than a single /64 (IPv6 prefix, not address, is the unit a site controls) | [RFC 6177](https://www.rfc-editor.org/rfc/rfc6177.txt) | Read the relevant paragraphs |
| IPv6 temporary addresses change over time | [RFC 4941](https://www.rfc-editor.org/rfc/rfc4941.txt) | Read the abstract |
| Documentation address ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24; 2001:db8::/32) | [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.txt), [RFC 3849](https://www.rfc-editor.org/rfc/rfc3849.txt) | Read |
| API Gateway throttles with the token bucket algorithm, returns 429, and limits are best-effort targets | [AWS API Gateway throttling](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html) | Read |
| OWASP API4:2023: limit how often a client can execute an operation (OTP validation, password recovery); the US$13 to US$8k cost example | [OWASP API4:2023](https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/) | Read |
| OWASP: count failed logins per account; lockout can be abused for denial of service; CAPTCHA is defense in depth | [Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) | Read |
| NIST SP 800-63B-4 section 3.2.2: no more than 100 consecutive failed attempts per authenticator on an account, reducing lockout risk with challenges and growing waits | [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html) | Read |
| PostgreSQL `max_connections` default is typically 100; PgBouncer `max_client_conn` and its file descriptor note | [PostgreSQL 18: connections](https://www.postgresql.org/docs/current/runtime-config-connection.html), [PgBouncer config](https://www.pgbouncer.org/config.html) | Read |
| The outputs of Exercises 1 to 8 (algorithm counts, key table, status runs, spoof table, namespace counts, SYN counters, per-key demo) | Run on 2026-10-22: Python 3.13, curl 8.21.0, Podman 5.4.2, `nginx:1.30.6-alpine`, nftables 1.1.3, iptables 1.8.11 (nf_tables) | Observed. The private container address in the logs was replaced with `192.0.2.10` |
| The definitions of fixed and sliding windows and of the leaky bucket as a queue; upstream provider and DDoS scrubbing behavior; carrier-grade NAT sharing; IPv6 prefix grouping lengths; load balancer cascade; the retry-storm pattern; the "atomic increment" remedy | General knowledge | **est.**; no single source read for each |

Not verified, plainly: every PowerShell script and command on this page (written from Microsoft's documentation, never run, with a real chance of a typo, and `Invoke-WebRequest -SkipHttpErrorCheck` needs PowerShell 7); Docker, Docker Desktop, macOS and Windows (only rootless Podman on Linux was used, so the address the application sees through the port forward, and whether `127.0.0.1` could ever be it, is unchecked for Docker); the namespace exercise on any distribution other than the test machine, including the AppArmor restriction note; the Cloudflare rule steps and whether its `429` includes `Retry-After`; the HAProxy, BIND, Unbound and fail2ban snippets; the exact arithmetic behind "8 of 12" in the nftables and iptables runs; any figure for how many people share a mobile carrier's address; and everything provider-side about upstream network defense. The Cloudflare plan limits are a dated snapshot and will drift.

Next: [Detection, Wazuh and the landscape](Detection-and-Monitoring-Wazuh-and-the-Landscape.md), where the detect job is spread across real products.
