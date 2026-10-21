# APIs and tokens from zero

Side page to the start-from-zero pages. Read it before [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) if the words API, token or HTTP are new, or at any point you meet them and want them explained properly. Next: [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from standards and vendor documentation; the free exercises were run once.** The HTTP and token ideas are standard (HTTP: [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110); JWT: [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519); OAuth 2.0: [RFC 6749](https://www.rfc-editor.org/rfc/rfc6749); OpenID Connect: [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)). The free `curl` exercises use two public services and were run read-only on **2026-10-21**; the output shown is what came back that day, trimmed. Services change, so your output may differ in small ways (dates, counters, ids). The paid-account exercise (the optional one at the end) uses GitHub's menu names as read from [GitHub's page on managing personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) on **2026-10-21**; I did not click through it on a real account for this page, so the exact response text there is marked **est.** (estimate).

> **Prerequisites.** A computer with a terminal and internet access. Nothing else: no account, no money, no programming. The terminal part of [Git from zero](Git-From-Zero.md) shows how to open one, if you have never done it. About 60 minutes for the free exercises; the optional one adds about 20 minutes (est.).

## What you will be able to do

- Say what an API is, in one sentence a non-technical friend would follow.
- Read a web request and a response: the method, the address, the status code, the headers and the body.
- Read JSON without being frightened of it.
- Tell apart the things people loosely call "a token": an API key, a bearer token, a session cookie, an OAuth access token, an OIDC ID token and a JWT.
- Explain what a scope is, why a token should have an expiry date, and what to do in the first five minutes after one leaks.
- Say how those ideas show up in this project: the DigitalOcean token, the Doppler service token, the Twingate keys and the Spacelift context.

## Where this project already touches these ideas (and the gaps)

I searched the wiki before writing this page. What I found, and what was missing:

| Idea | Where it is used or defined today | The gap this page fills |
|---|---|---|
| API | Glossary says "the web interface a cloud provider exposes so programs can create and change resources". [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) defines a provider as a plugin that talks to an API. | No explanation of what is actually sent over the wire, or what a request and a response look like. |
| API token / API key | [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) has a table row and a paragraph ("as good as a password"). | No difference between a key, a bearer token, a cookie and an OAuth token. No scopes, expiry or revocation explained from first principles. |
| Service token | [Doppler and secrets](Doppler-and-Secrets.md) uses it ("read-only, one config, 90 days") without defining it. | Why a program gets its own token rather than borrowing yours. |
| OIDC | The Glossary defines it in one line, and [Spacelift](Spacelift.md) explains why this project cannot use it on the current plan. | What an ID token is, and what a JWT contains. |
| Scope, expiry | Used in Identity, Doppler and Spacelift as working words. | Never defined. |
| HTTP, status codes, JSON, `curl` | [Networking basics](Networking-Basics-for-This-Project.md) covers HTTPS as port 443; the Identity page mentions a `403` in passing. | No status-code table, no headers, no JSON, and no hands-on request anywhere. |

If you read this page first, the other pages get easier. If you read them first and some word was fuzzy, this page is the repair.

## What an API is

Picture a restaurant. You sit at a table. You do not walk into the kitchen and cook; you do not even know how the kitchen works. You read a **menu** (the list of things you may ask for), tell a **waiter** what you want, and the waiter brings back a plate or says "sorry, we are out of that". The menu is the contract: ask for something not on it and you get a polite no.

An **API** (application programming interface) is that arrangement between two programs. One program (the **client**, the customer) sends a **request** to another program (the **server**, the kitchen) and gets a **response** back. The documentation of what you may ask for is the menu. The server decides whether to serve you; that decision is the rest of this page.

The real thing, with the analogy removed: an API on the web is a request and a response over **HTTP** (HyperText Transfer Protocol), the same protocol your browser uses. Your browser asks a server for a page and gets HTML back. A program asks a server for data and usually gets **JSON** back (a text format, covered below). The only real difference is who is reading the answer: a person looking at a page, or a program.

This is how the project works. When OpenTofu creates a droplet, it sends an HTTP request to DigitalOcean's API saying "create this machine" and reads the response. The DigitalOcean web console is just another client of the same API. See [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) for the other half of that story.

## HTTP in ten minutes

### The parts of a request

A request has four parts:

1. **A URL**: where to send it. `https://api.github.com/users/octocat` breaks into the **scheme** (`https`, meaning HTTP inside an encrypted connection, see [Networking basics](Networking-Basics-for-This-Project.md)), the **host** (`api.github.com`, which is looked up through DNS), and the **path** (`/users/octocat`, which thing on that server you mean). After a `?` you may see a **query string** such as `?per_page=5`: extra options, written `name=value` and joined with `&`.
2. **A method**: what you want to do with the thing.
3. **Headers**: small `Name: value` lines of extra information about the request (who you are, what format you want).
4. **A body** (sometimes): data you send, for example the details of the droplet to create.

### The methods

| Method | Means | Plain example | Changes anything? |
|---|---|---|---|
| `GET` | Read this | Show me my list of droplets | No |
| `POST` | Create something, or run an action | Make a new droplet | Yes |
| `PUT` | Replace this thing with what I am sending | Overwrite this record entirely | Yes |
| `PATCH` | Change part of this thing | Rename it, touch nothing else | Yes |
| `DELETE` | Remove this | Destroy that droplet | Yes |

`PATCH` is often left out of introductions, but you will meet it constantly. The rule of thumb for staying safe: **`GET` should never change anything**. When you are exploring an API you do not know, use only `GET`.

### The parts of a response

A response has a **status line** (a number and a short phrase), **headers** and usually a **body**. The status code is the first thing to read. The first digit tells you the family: 2 means it worked, 3 means "look somewhere else", 4 means **you** got something wrong, 5 means **the server** has a problem.

| Code | Name | What it tells you |
|---|---|---|
| `200` | OK | It worked; the answer is in the body. |
| `201` | Created | It worked and a new thing now exists (the reply to a successful `POST`). |
| `204` | No Content | It worked and there is nothing to send back (common after a `DELETE`). |
| `301` | Moved Permanently | The thing lives at another URL, named in a `Location` header. Follow it (`curl -L`). |
| `400` | Bad Request | The server could not understand what you sent: malformed JSON, a missing field. Read the body; it usually says which. |
| `401` | Unauthorized | **I do not know who you are.** No credential, a wrong one, or an expired one. (The name is misleading; it really means "unauthenticated".) |
| `403` | Forbidden | **I know who you are, and the answer is no.** The credential is valid but not allowed to do this. Usually a scope or permission problem. |
| `404` | Not Found | No such thing at that path. Also used by some services to hide something you are not allowed to see, so a `404` on a real thing can be a permissions problem in disguise. |
| `429` | Too Many Requests | You are being rate limited; slow down and look at the `Retry-After` header. |
| `500` | Internal Server Error | The server broke. Not your fault; retry later, and do not hammer it. |

The pair to burn in: **`401` is about who you are, `403` is about what you may do.** This project's own history has an example: a run that failed with a `403 You are not authorized` told the author the DigitalOcean token was valid but missing a scope (recorded on [Lessons learned](Lessons-Learned.md)).

### Headers worth knowing

| Header | Direction | What it does |
|---|---|---|
| `Authorization` | Request | Carries your credential, for example `Authorization: Bearer <token>`. The one that matters most for this page. |
| `Content-Type` | Both | The format of the body: `application/json` means JSON. |
| `Accept` | Request | The format you would like back. |
| `User-Agent` | Request | Names the program making the request. Some services refuse requests without one; `curl` sends one for you. |
| `Location` | Response | Where to go next, on a `301` or after a `201`. |
| `Retry-After` | Response | How many seconds to wait before trying again, on a `429`. |
| `X-RateLimit-Remaining` | Response | How many requests you have left in this window. Names vary by service. |

## JSON in five minutes

**JSON** (JavaScript Object Notation) is how most APIs write down data. It is plain text with only a few shapes:

```json
{
  "id": 7,
  "title": "learn what an API is",
  "done": false,
  "tags": ["basics", "web"],
  "owner": { "name": "example-user", "admin": null }
}
```

- `{ ... }` is an **object**: a set of `"name": value` pairs, like a form with labeled fields. Names are always in double quotes.
- `[ ... ]` is an **array**: an ordered list. Items are separated by commas.
- A value is a double-quoted **string**, a **number** (no quotes), `true` or `false`, `null` (nothing), or another object or array.
- Nesting is normal. Read it like a tree: `owner` is a field whose value is an object with its own fields.
- Mistakes that break it: single quotes, a trailing comma, a missing quote. A `400` from an API is very often one of these.

This repository uses it too: the settings manifest behind the [Settings reference](Settings-Reference.md) is JSON.

## REST, and "just an API"

You will hear "a REST API". **REST** is a habit of design, not a product: things are nouns in the URL (`/droplets/123`), the HTTP method is the verb (`GET` reads it, `DELETE` removes it), and each request carries everything the server needs, so the server need not remember you between requests. Most APIs you meet are roughly REST and most people say "REST API" for any JSON-over-HTTP API.

"Just an API" is everything else that does not fit that style: GraphQL (one address, you describe the data you want in the request), gRPC (a binary format between services), SOAP (an older XML style). The tokens and status-code ideas on this page apply to all of them; only the shape of the request changes. Spacelift has a GraphQL API, for example (est.: from its vendor documentation; the [Spacelift](Spacelift.md) page does not use it), and DigitalOcean and Twingate expose ordinary REST ones (est.: check each vendor's docs for the current state).

## Authentication and authorization

Two words that students mix up in exams and in real incidents:

- **Authentication** (often shortened to **authn**): *who are you?* Proving an identity, with a password, a key, a token.
- **Authorization** (**authz**): *what may you do?* After the server knows who you are, the check on whether this action is allowed.

A `401` is an authentication failure; a `403` is an authorization failure. The [Identity basics](Identity-Secrets-and-Zero-Trust-Basics.md) page shows why keeping them apart matters: strong authentication with weak authorization is how a stolen login becomes a whole-network breach.

## The kinds of credential, side by side

A **credential** is whatever you present to prove who you are. People call nearly all of them "tokens", which causes confusion. Here is the sorting:

| Kind | What it is | How it is sent | Lifetime | Typical use |
|---|---|---|---|---|
| **API key** | A long random string issued to an account or app, usually never changing until you replace it. Identifies the *caller*, often with fixed permissions. | A header (often `Authorization` or `X-API-Key`), sometimes in the URL (avoid: URLs get logged). | Long, or forever | Simple services, weather APIs, older integrations |
| **Bearer token** | Any credential where *whoever bears (holds) it is let in*, with no further proof. The word describes **how it is used**, not what it is. | `Authorization: Bearer <token>` | Varies | Almost every modern API |
| **Session cookie** | A random identifier a website gives your browser after you log in; the browser sends it back automatically. | The `Cookie` header | Minutes to weeks | A person using a website |
| **OAuth access token** | A bearer token issued by an authorization server after you (or an app acting for you) agreed to a specific, limited list of permissions. | `Authorization: Bearer` | Short (minutes to hours) | "Sign in and let this app read my calendar" |
| **OIDC ID token** | A statement from an identity provider that says **who just logged in**. It is for the app that asked for the login, not for calling APIs. | Delivered to the app during sign-in | Short | Single sign-on (SSO) |
| **JWT** | Not a different purpose but a **format**: a signed, self-describing token. Many OAuth access tokens and all OIDC ID tokens are JWTs. | Usually as a bearer token | Short | See the next section |

Some definitions behind that table:

- **OAuth 2.0** is a standard for letting one app act for you at another service *without* handing over your password: you approve a list of permissions, and the app gets an access token limited to them.
- **OIDC** (OpenID Connect) is a thin layer on top of OAuth that adds the "who is this?" answer, the ID token. "Log in with Google" is OIDC.
- **SSO** (single sign-on) is logging in once, with one identity provider, and being let into many services.

The distinction people miss: an **ID token says who you are; an access token says what you may do**. Do not send an ID token to an API as if it were an access token.

### What is inside a JWT (and why base64 is not encryption)

A **JWT** (JSON Web Token, said "jot") is a *format for a set of claims*. It is carried in one of two wrappers. The common one, and the one OIDC ID tokens use, is a **signed** token (a JWS, JSON Web Signature) made of three chunks of text joined by dots. The other is an **encrypted** token (a JWE, JSON Web Encryption) with five chunks, whose payload is *not* readable by everyone who holds it. The rest of this section is about the signed, three-part kind, because it is the one you will meet most:

```text
<header>.<payload>.<signature>
```

- The **header** says how it was signed (JSON).
- The **payload** holds the **claims**: facts such as who it is about (`sub`, the subject), who issued it (`iss`), when it expires (`exp`, a Unix time, meaning seconds since 1 January 1970) and often a list of `scope` values.
- The **signature** is a cryptographic seal over the first two parts, so the receiver can tell nobody altered them. Who can make and check it depends on the algorithm named in the header. With an **asymmetric** algorithm (names starting `RS` or `ES`) only the issuer holds the private key that signs, and anyone with the matching public key can verify: the receiver needs no secret. With a **symmetric** one (names starting `HS`) a single shared secret both signs and verifies, so anyone who can verify can also forge, and both sides must guard that secret.

Each of the first two chunks is **base64url-encoded** JSON. **Base64** is a way of writing arbitrary bytes using only letters, digits and a few symbols so they survive being pasted into a header. It is **encoding, not encryption**: anyone can reverse it with no key, and you are about to do it yourself in the exercise. So:

- In a signed (three-part) JWT the payload can be read by anyone who holds the token. Never put a secret in a claim. (An encrypted five-part one hides its payload from holders without the key, but you cannot assume which kind you have been given, so treat any token as a credential.)
- The signature stops *changes*, not *reading*.
- **A real JWT is a credential. Never paste one into a website that "decodes JWTs", a chat, a ticket, a screenshot or an issue.** The decoder site is a stranger who now holds your token. Decode locally, as the exercise shows, or not at all.

This is why a JWT can be checked without calling the issuer: the receiver verifies the signature (with the public key, or the shared secret) and reads `exp`. It is also why one cannot easily be taken back before it expires, which is the point of short lifetimes. What a signature is, and how it differs from a hash or encryption, is on [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#digital-signatures-proof-of-who-and-what).

## Scopes and least privilege

A **scope** is one named permission on a token: `read`, `repo:status`, `droplet:create`. A token with the scopes `read` can read and nothing else, no matter whose account it belongs to. **Least privilege** is the rule of granting the fewest scopes that do the job, so a leaked token can do little.

In this project:

- The DigitalOcean token that OpenTofu uses has a **custom list of scopes**, not full access, and expires in 90 days (see the diagram on [Doppler and secrets](Doppler-and-Secrets.md#who-holds-what)). A `403` showed one scope was missing; because DigitalOcean tokens cannot be edited after creation, the fix was a replacement token with that scope added, not a token widened to everything ([Lessons learned](Lessons-Learned.md)).
- The Doppler **service token** is read-only and scoped to one config. If it leaks, it reads these values and nothing else.

## Expiry, rotation and revocation

Three words about a token's life:

- **Expiry**: the date after which the token stops working by itself. A token with no expiry date is a token that stays dangerous forever. Choose the shortest date you can live with.
- **Rotation**: replacing a token with a new one *before* it expires (or on a schedule), then removing the old one. [Doppler and secrets](Doppler-and-Secrets.md) has the rotation table for this project (90 days for each token).
- **Revocation**: killing a token *now*, before its expiry, because it may be in the wrong hands. Revoke is a button or an API call at the issuer. A token you cannot revoke is a bad design; check before you adopt one.

## Service accounts and personal tokens

A **personal token** (often called a personal access token or PAT) acts as *you*, with whatever your account can do (or whatever you ticked). A **service account** or **service token** belongs to a *program*, not a person.

Why the difference matters: if a program uses your personal token, then when you leave, change your password or lose a laptop, the program breaks, and anything it does in the logs looks like you did it. If the program has its own narrow token, you can see in the audit log which thing acted, and you can revoke only that.

How the four tokens in this project line up (no value is ever shown anywhere, and none is in a file). Three of them are held in [Doppler](Doppler-and-Secrets.md) or a Spacelift context. The Twingate connector keys are the exception: per the [Twingate page](Twingate.md#accepted-risk-the-connector-tokens), they end up in OpenTofu state (held by Spacelift) and in the droplet's cloud-init user-data, marked sensitive, each revocable, and the project lists that as an accepted risk:

| Token | Held by | Acts for | Scope and lifetime | Where explained |
|---|---|---|---|---|
| DigitalOcean API token | Doppler, fetched by the run | OpenTofu creating cloud resources | Custom write scopes, 90 days | [Doppler and secrets](Doppler-and-Secrets.md) |
| Twingate API token | Doppler | OpenTofu creating the access network | 90 days | [Twingate](Twingate.md) |
| Twingate connector keys | OpenTofu state (Spacelift) and the droplet's user-data | That one connector, proving itself to Twingate | Per connector; rotation steps on the Twingate page | [Twingate: rotating a connector token](Twingate.md#rotating-a-connector-token) |
| Doppler service token | A Spacelift context (a named bundle of variables that stacks can attach) | Spacelift, fetching secrets by name | Read-only, one config, 90 days | [Spacelift](Spacelift.md) |

## Where a secret must never live

| Place | Why not | What to do instead |
|---|---|---|
| **A git repository, including history** | History is forever and copied to every clone and fork; deleting the file later does not remove it from old commits. In a public repo, bots find new tokens within minutes (est.). | A secrets manager ([Doppler](Doppler-and-Secrets.md)); a `.gitignore`d local file for experiments. |
| **Chat, tickets, email** | Searchable, forwarded, backed up, read by bots in the channel. | Share a link to the secrets manager, never the value. |
| **Screenshots and screen recordings** | The token in the corner of the terminal. See the redaction rules in the [Screenshots policy](Screenshots-Policy.md). | Redact first; better, never display it. |
| **Logs and CI output** | Logs are widely readable and kept for months. | Use CI features that mask secrets; do not `echo` them; never run commands with `-v` against secret URLs. |
| **URLs and query strings** | URLs are logged by servers, proxies and browser history, and leak through the `Referer` header. | Send credentials in the `Authorization` header. |
| **Shell history** | Typing `export TOKEN=...` saves the line in a file. | Read it silently with `read -rs` (the exercise shows it). |

## When a secret leaks: revoke, then rotate, then clean up

In that order, and fast. Every minute between the leak and the revoke is a minute an attacker has.

1. **Revoke first.** Go to the issuer and kill the token. Do not wait to find out whether anyone used it. Do not start by deleting the file or rewriting git history; that does nothing to a copy someone already has.
2. **Rotate.** Issue a replacement with the narrowest scopes and a short expiry, put it in the secrets manager, and update whatever needed it.
3. **Check the logs.** Look at the issuer's audit log for the window the token was exposed: what did it do that you did not do? (The detect step of the loop below.)
4. **Clean up.** Remove the value from the file, the history, the chat message, the screenshot. This is tidiness, not safety: assume the old value was copied, which is why step 1 comes first.
5. **Learn.** Write down how it got there, and what check would have caught it. [Lessons learned](Lessons-Learned.md) is the project's example.

## Rate limits and pagination

A **rate limit** is the number of requests a service lets you make in a time window (for example 60 an hour without logging in); go over it and you get a `429`. **Pagination** is how a service sends a long list in pieces: you ask for a page of, say, 30 items at a time, and the response tells you how to ask for the next page (a `Link` header or a "next" field).

## Hands-on: free exercises

Every exercise below follows four steps: **predict** (write down what you expect before you run anything; guessing wrong is how you learn), **do**, **check**, **undo**.

All commands use only public services that need no account and no payment: [JSONPlaceholder](https://jsonplaceholder.typicode.com/) (a free fake API for practice, whose writes are pretended and never saved) and the unauthenticated root of [GitHub's REST API](https://docs.github.com/en/rest) (`https://api.github.com/`). Both were checked with `curl` on **2026-10-21**: every request was a `GET` except Exercise 5, a `POST` to JSONPlaceholder that the service only simulates and never saves. Treat them as shared: do not run loops or send large amounts of traffic at them.

You need `curl` and `python3`, both present on most Linux and macOS machines; Windows users can use WSL or Git Bash (see [Git from zero](Git-From-Zero.md)). `jq` is an optional nicer JSON viewer; the exercises use `python3 -m json.tool` so you need nothing extra.

> **Screenshot to take yourself:** your terminal after Exercise 1.
> Capture: the command, the first lines of output including the status line (`200`), and a few header lines.
> Look for: the status line, the `content-type: application/json` header, and the JSON body.
> Redact: your username, hostname and the prompt path if they identify you. None of the output of these public endpoints is secret.

### Exercise 1: read a response (GET, 200)

**Predict.** Will asking for item number 1 of a to-do list return a status in the 2xx family or the 4xx family? What format will the body be in?

**Do.**

```bash
curl -i https://jsonplaceholder.typicode.com/todos/1
```

`-i` means "include the response headers in the output".

**Check.** The first line is the status line; the code is `200`. (It may read `HTTP/2 200` or `HTTP/1.1 200 OK`, depending on your `curl` and the server; the number is what matters. To print only the number: `curl -s -o /dev/null -w '%{http_code}\n' <url>`.) Then a block of headers (one of them `content-type: application/json; charset=utf-8`), a blank line, and a body like this (retrieved 2026-10-21):

```json
{
  "userId": 1,
  "id": 1,
  "title": "delectus aut autem",
  "completed": false
}
```

Find in the body: one object, four fields, one number that is the item's `id`, one `false` boolean. Find in the headers: the `x-ratelimit-` lines, if present (est.: names vary, and the service can change them).

**Undo.** Nothing to undo; a `GET` changes nothing.

### Exercise 2: pretty-print JSON

**Predict.** If you ask for the first two items, how will the body differ in shape from Exercise 1: an object or an array?

**Do.**

```bash
curl -s 'https://jsonplaceholder.typicode.com/todos?_limit=2' | python3 -m json.tool
```

`-s` is "silent" (no progress meter). The `|` hands curl's output to the pretty-printer. The `?_limit=2` is a query string.

**Check.** The output starts with `[` and holds two `{ ... }` objects: an **array of objects**. Each item has the same fields as Exercise 1. Spotting that "shape" (list of records) is the whole skill. If you installed `jq`, `curl -s ... | jq .` gives the same, colored.

**Undo.** Nothing.

### Exercise 3: trigger a 404 on purpose

**Predict.** What happens when you ask for a path that does not exist? Is it your fault or the server's?

**Do.**

```bash
curl -i https://jsonplaceholder.typicode.com/this-path-does-not-exist
```

**Check.** The status code is `404` and the body is an empty object, `{}` (retrieved 2026-10-21). 4xx means the mistake is in the request. Now change one letter in `todos/1` from Exercise 1 (try `todo/1`) and watch it turn from `200` to `404`: a typo in a URL is an ordinary cause of a failing run.

**Undo.** Nothing.

### Exercise 4: trigger a 401 on purpose

**Predict.** GitHub's API root works with no login. Its `/user` path means "the account that is signed in". What will it say to an anonymous caller: `401`, `403` or `404`?

**Do.**

```bash
curl -i https://api.github.com/user
```

**Check.** Status code `401`, with a JSON body whose `message` is `Requires authentication` (retrieved 2026-10-21). That is the server saying: *I do not know who you are.* You sent no `Authorization` header. Compare with the unauthenticated root, which answers `200` because it is public:

```bash
curl -s https://api.github.com/ | python3 -m json.tool | head -8
curl -si https://api.github.com/ | grep -i '^x-ratelimit'
```

The second command shows a rate limit that counts requests from your address (the 2026-10-21 response showed `x-ratelimit-limit: 60`; yours may differ).

**Undo.** Nothing.

### Exercise 5: a pretend write (POST and 201)

**Predict.** JSONPlaceholder says it fakes writes. If you `POST` a new item, which code do you expect, and will the item really exist afterwards?

**Do.**

```bash
curl -i -X POST -H 'Content-Type: application/json' \
  -d '{"title":"demo"}' https://jsonplaceholder.typicode.com/posts
```

`-X POST` sets the method, `-H` adds a header, `-d` supplies the body.

**Check.** Status code `201` and a body that echoes your field with an `id` added (retrieved 2026-10-21). Ask for it back with `GET /posts/101` and you get a `404`: the service acknowledged the write but, by design, saved nothing. Note this for later: a `201` means the server *says* it created the thing; always read the thing back.

**Undo.** Nothing was saved, so nothing to undo. (Against a real service you would `DELETE` what you created.)

### Exercise 6: build and decode a fake JWT, locally

This builds a **fake** token on your own machine, so no token-shaped text is stored in this repository. Nothing is sent anywhere. The signature is left empty, which is exactly why this one proves nothing to anybody: it is for learning only.

**Predict.** If base64 were encryption, you would need a key to read the middle chunk. Do you?

**Do.**

```bash
python3 - <<'PY'
import base64, json

def b64url(obj):
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

header = {"alg": "none", "typ": "JWT"}
claims = {"sub": "example-user", "scope": "read", "exp": 1893456000}
fake = b64url(header) + "." + b64url(claims) + "."
print("three parts, split on dots:", len(fake.split(".")))
print("fake token length:", len(fake))

payload = fake.split(".")[1]
payload += "=" * (-len(payload) % 4)          # restore the padding removed above
print(json.loads(base64.urlsafe_b64decode(payload)))
PY
```

**Check.** Three lines of output. The last prints the claims dictionary you put in: `{'sub': 'example-user', 'scope': 'read', 'exp': 1893456000}`. You read the middle part with no key, because it is encoded, not encrypted. `exp` 1893456000 is a Unix time; convert it with `date -u -d @1893456000` (GNU/Linux) or `date -u -r 1893456000` (macOS) to see a date in January 2030. The script prints the length and parts count but **not the fake token itself**, on purpose: make a habit of not echoing token-shaped values, even fake ones.

**Undo.** Nothing was written to disk; the token existed only in the script's memory.

## Optional: make, test and revoke a real scoped token (your own account)

This uses an account you already have. Free GitHub accounts work and nothing here costs money. You can do the same on any service that offers scoped tokens (a cloud provider, a Doppler workspace of your own); the steps are the same shape.

> **Warning.** Do this in your **own personal account**, never an employer's or a shared one. Never run it against this project's accounts. If you are not sure whether a token is yours to make, stop.

**Predict.** A token that has read-only access to nothing in particular can still tell the server who you are. Will `GET /user` succeed with it? Will an attempt to *change* your profile succeed?

**Do.**

1. On GitHub: profile picture, **Settings**, **Developer settings**, **Personal access tokens**, **Fine-grained tokens**, **Generate new token** (menu names as read from GitHub's documentation on 2026-10-21; the page may have moved since).
2. Name it `learning-readonly-delete-me`. Under **Expiration**, choose the shortest option offered (about 7 days). Under repository access choose **Public repositories (read-only)** or none. Add no account or repository permissions.
3. Generate it. GitHub shows the value **once**. Do not screenshot it, paste it into chat or save it in a file.
4. In your terminal, load it without it entering your shell history:

```bash
read -rs GH_TOKEN      # paste the token, press Enter; nothing is echoed
curl -i -H @- https://api.github.com/user <<<"Authorization: Bearer $GH_TOKEN"
```

Why `-H @-` and a here-string instead of `-H "Authorization: ..."`: the arguments of a command are visible to other users and programs on the machine (for example in the process list) while it runs, and may be recorded by auditing tools. Headers read from standard input never appear in the arguments. (`read -rs` and the here-string are bash/zsh features; the variable is not exported, so child programs do not inherit it.)

**Check.** You expect status `200` and a JSON body about *your* account (that proves the credential works). Then try a change, which the token should not be allowed to make:

```bash
curl -i -X PATCH -H @- -H 'Content-Type: application/json' \
  -d '{"bio":"test"}' https://api.github.com/user <<<"Authorization: Bearer $GH_TOKEN"
```

Expect a `403` (est.: the exact message varies; it should say the token cannot access this resource). This is authorization failing while authentication succeeds: the server knows who you are and says no. Look also for response headers that list the token's permissions (names vary by token type).

**Undo.** Revoke it, then prove it is dead:

1. Settings, Developer settings, Personal access tokens, Fine-grained tokens, find `learning-readonly-delete-me`, **Delete** (menu names as read on 2026-10-21).
2. Re-run the first `curl` command above (the one with `-H @-`). It should now answer with status `401`. A made-up token sent to the same address on 2026-10-21 got `401` with the message `Bad credentials`; a real revoked one should look the same (est., I did not revoke a real one). A revoked token fails as an unknown credential.
3. Clear it from your shell: `unset GH_TOKEN`.

> **Screenshot to take yourself:** the fine-grained token creation page.
> Capture: the form with the name, expiration and repository access chosen, **before** you press Generate.
> Look for: the expiration is short, repository access is read-only or none, no permissions are ticked.
> Redact: your username and avatar, and above all the token value if the page ever shows one (never capture that screen).

## Build it, break it, detect it, defend it

The same four-step loop the [labs](Labs-Break-It-on-Purpose.md) use, applied to a token.

- **Build.** Make a token with one narrow scope, a short expiry and a name that says what it is for (what you just did, minus the revoking).
- **Break.** Ask what a leaked token with *broad* scopes and *no* expiry could do. For a cloud API token with write scopes: create machines that mine cryptocurrency on your bill, read data, delete the environment. That is the case for narrow scopes, written down as a risk in the [Threat model](Threat-Model.md). Do not try this on a real token; reason it through on paper, or in a throwaway account of your own.
- **Detect.** Find where a *use* of the token shows. Most services keep an audit log or a token "last used" field in their settings (est.: it varies by vendor). Cloud logs record the caller's identity and source address; look for use from a place or at a time you do not recognize. This project's detection ideas are in [Detection and monitoring](Detection-and-Monitoring-Wazuh-and-the-Landscape.md).
- **Defend.** Expiry limits the window, revocation ends it, scopes limit the damage, and a secrets manager keeps the value out of files, chat and history in the first place. The [Doppler and secrets](Doppler-and-Secrets.md) page is the project's version of all four.

## Checkpoint

You are done when you can say, without looking:

- What a `401` and a `403` each mean, and which one says "I know who you are, and no".
- Why base64 is not encryption, and why you never paste a real JWT into a website.
- The difference between an ID token and an access token.
- The first thing to do when a token leaks (revoke), and why that comes before cleaning up.

## Where to next

[Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) uses these words directly, then [Doppler and secrets](Doppler-and-Secrets.md) shows them in this project's pipeline.
