# Enterprise identity: directories, SSO, SAML, OAuth and OIDC

Side page to the start-from-zero pages. Read it after [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) (core step 4) when "single sign-on", "SAML", "OIDC" or "identity provider" are only words to you, and before [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md), which assumes you know them. It does not repeat the token lesson: [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) covers what a token, a scope and a JWT are, and [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) covers what a signature is. This page is about the sign-in itself: who vouches for you, how an application is told, and how that breaks. Next: [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the free local lab was run once on Linux; everything else was not run.** On **2026-10-21** the author ran the Python scripts and the Bash commands in the free theory path on Linux (Python 3.13) and pasted trimmed output from that run. **Not run:** the PowerShell equivalents (no Windows machine; written from Microsoft's documentation and marked **est.**), and the whole optional own-account path with Keycloak in a container (no image was pulled for this page; the commands are from Keycloak's and Docker's documentation, read the same day, and the one script in it, `oidc_login.py`, was tested only against a small stand-in server the author wrote, not against Keycloak: run it expecting to fix something). Standards and vendor pages were read on **2026-10-21**; see the [claims register](#claims-register). Where a figure or a behavior is **est.**, it is general knowledge or a guess and was not checked against a source.

> **Prerequisites.** [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) (authentication versus authorization, MFA, least privilege), [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) (tokens, scopes, what is inside a JWT) and, for the word "signature", [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#digital-signatures-proof-of-who-and-what). A terminal and Python 3.9 or newer for the free exercises (the scripts use `ElementTree.indent`, added in 3.9). About two hours for the reading and the free exercises (est.); the optional local path adds about an hour (est.). Nothing needs an account for the free path. The reading and the exercises are free; the optional path runs on your own computer and uses its resources, not a cloud bill.

## What you will be able to do

- Say the difference between authentication, authorization and accounting, and match a symptom (a sign-in failure, a "forbidden", a log line) to the right one.
- Draw, in one picture, a directory, an identity provider (IdP), single sign-on (SSO) and an application, and say what each does.
- Walk through a SAML sign-in and an OpenID Connect (OIDC) sign-in step by step, saying what the browser carries and what the application checks.
- Explain why OAuth 2.0 is about delegated access, and what OIDC adds on top of it (who you are).
- Read a SAML assertion and an OIDC ID token: find the issuer, the audience, the expiry, the subject, the groups and the signature, and say which of them an application must check.
- Map people to groups, groups to roles and roles to permissions, and spot an over-broad group and a stale leaver account.
- Explain MFA fatigue, and why a FIDO2/WebAuthn sign-in resists phishing (the key is tied to the website's origin) while a typed code does not.
- Say why identity is called "the new perimeter", and how a zero-trust access product such as the one in this project uses an IdP.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Authentication versus authorization | [Identity basics](Identity-Secrets-and-Zero-Trust-Basics.md#authentication-and-authorization-are-two-different-questions) and [APIs and tokens](APIs-and-Tokens-From-Zero.md#authentication-and-authorization) (a `401` versus a `403`). | Accounting, the third question, and how the three look at company scale. |
| IdP, SSO, MFA, conditional access, SCIM, joiner-mover-leaver, RBAC and ABAC | Named in a paragraph each on [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md#people-idp-sso-mfa-and-conditional-access). | Never walked through. This page shows the actual messages in a SAML and an OIDC sign-in and lets you read them. |
| Tokens, scopes, JWT claims | [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md#what-is-inside-a-jwt-and-why-base64-is-not-encryption). | Not repeated. Here the same JWT is an ID token, and the lesson is what the *application* must check. |
| Signatures, hardware keys | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#keeping-keys-storage-passphrases-and-hardware-keys). | Not repeated. Here a signature is what makes an assertion believable. |
| Zero trust and the IdP | [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) says sign-in is delegated to the IdP; [Zero trust at home](Zero-Trust-at-Home-Two-Connectors-and-Failover.md#honest-limits) says role-based reach depends on the plan. | What "delegated to the IdP" means message by message. |
| Workload identity (OIDC federation for machines) | [Enterprise identity at scale](Enterprise-Identity-and-Secrets-at-Scale.md#machines-service-accounts-and-workload-identity) and [Spacelift: no OIDC on this plan](Spacelift.md#no-oidc-on-this-plan). | One paragraph here, pointing to those. |

## Three questions: authentication, authorization, accounting

Every access system answers three questions, and people shorten them to **AAA**:

1. **Authentication (authn): who are you?** You prove an identity: a password, a code, a key, a passkey. Output: "this is pat@example.com".
2. **Authorization (authz): what may you do?** With the identity known, is *this action on this thing* allowed? Output: allow or deny. An HTTP `401` is an authentication failure; a `403` is an authorization failure ([APIs and tokens](APIs-and-Tokens-From-Zero.md#authentication-and-authorization)).
3. **Accounting: what did you do?** A record, kept by someone other than you, of who did what and when. Sign-in logs, change logs and access reviews are accounting. Without it, the first two questions cannot be audited, and you cannot tell afterwards that an over-broad grant was used.

A system can get one right and another wrong: strong sign-in with sloppy roles lets a stolen login do too much, and good roles with no logs mean nobody notices. The rest of this page is the machinery that answers the three questions across hundreds of applications at once.

## Directory, identity provider, single sign-on: one picture

Three words, three jobs, often sold in one product:

- A **directory** is the database of identities: people, their groups, their attributes (department, manager, employment status), and sometimes devices. Examples of directory software are LDAP servers and Microsoft Active Directory. It answers "who exists, and what are they a member of?". By itself it does not hand out proof to web applications.
- An **identity provider (IdP)** is the service that *authenticates* a person (password, MFA) and then *tells other systems* who that person is, in a form they can check. It usually reads the directory (or contains one). It is the one place sign-in policy lives.
- **Single sign-on (SSO)** is the result: you sign in once, at the IdP, and many applications accept that. The applications are called **service providers** in SAML and **relying parties** in OIDC; both mean "the application that relies on the IdP's word".

```text
        people, groups, status                       "who is this?"
   ┌──────────────────────────┐   reads    ┌───────────────────────────────┐
   │ Directory                │◄───────────│ Identity provider (IdP)       │
   │ pat: staff, billing      │            │ checks password + MFA,        │
   └──────────────────────────┘            │ signs a statement about pat   │
                                           └───────┬───────────────┬───────┘
                          a signed statement,      │               │      a signed statement,
                          carried by the browser   ▼               ▼      carried by the browser
                                     ┌─────────────────┐   ┌─────────────────┐
                                     │ App A           │   │ App B           │
                                     │ (checks it,     │   │ (checks it,     │
                                     │  makes its own  │   │  makes its own  │
                                     │  session)       │   │  session)       │
                                     └─────────────────┘   └─────────────────┘
```

The point of the arrows: the applications never see pat's password. They see a signed statement from a party they were set up to trust. That is why one account can open hundreds of apps, and also why the IdP is the most valuable target in the company.

## SAML, step by step

**SAML 2.0** (Security Assertion Markup Language) is the older of the two protocols, from the 2000s, and is common for workforce SSO to business applications. Its message is an **assertion**: an XML document in which the IdP says "this person authenticated at this time, and here are some facts about them". The browser carries the assertion from the IdP to the application. The application trusts it because of the **signature**, not because of the browser it arrived through.

This is the common "service provider initiated" flow:

```text
  Browser                    App (service provider)               IdP
     │ 1. open /reports  ──────────►│                              │
     │◄─ 2. redirect to the IdP, carrying an AuthnRequest ("who is this?")
     │ 3. follow the redirect  ──────────────────────────────────►│
     │                              │        4. IdP: no session? ask for password + MFA
     │◄───────────────── 5. an HTML form holding a signed Response (the assertion)
     │ 6. browser POSTs the Response to the app's ACS address ───►│ (to the app)
     │                              │ 7. app checks: signature, issuer, audience,
     │                              │    time window, recipient, request id
     │◄─ 8. app sets its OWN session cookie; you are in ───────────│
```

1. You open the application. It has no session for you.
2. It sends your browser to the IdP with an **AuthnRequest**, a small message that says who is asking and where to send the answer. SAML defines several ways to carry messages through a browser; the request usually goes by the **HTTP Redirect** binding.
3. The browser follows the redirect to the IdP. The application is not involved in the next step.
4. If the IdP does not already know you (no session), it asks for your password and your MFA. If it does, you may not see anything at all: this is the "single" in single sign-on.
5. The IdP builds a **Response** containing a signed **assertion** and hands the browser a page that submits it, usually by the **HTTP POST** binding.
6. The browser posts it to the application's **assertion consumer service (ACS)** address, which the application registered with the IdP earlier.
7. The application **checks the assertion** (the list below). Skipping any check is a classic vulnerability.
8. If everything holds, the application starts its own session (a cookie) and the SAML part is over. From now on your browser sends the app's cookie, not an assertion.

What an application must check in step 7 (the field names are the ones you will find in the lab file):

| Check | Field | Why |
|---|---|---|
| The signature is valid, made by the key it was configured to trust | `Signature` / `SignatureValue`, the IdP certificate from its **metadata** | Anyone can write XML. Only the IdP can sign it. |
| It came from the expected IdP | `Issuer` | An assertion from a different IdP must not be accepted just because its signature is valid. |
| It is meant for *this* application | `Audience` inside `Conditions` / `AudienceRestriction` | Stops an assertion issued for App A being replayed to App B. |
| It is fresh | `NotBefore` and `NotOnOrAfter` on `Conditions` (and on `SubjectConfirmationData`) | A short window limits replay. |
| It answers a request this application made, and arrived at the right place | `InResponseTo`, `Recipient` | Ties the answer to the question. In the lab file `InResponseTo` holds a made-up request ID (`_req-lab-1`) standing for the one the application put in its AuthnRequest; the lab has no real application to compare it with, so the exercise asks you to do that comparison by eye. |
| It says who and what | `NameID` (who), `AttributeStatement` (email, groups) | The application's authorization starts from these. |

**Metadata** is a small XML file each side publishes about itself: the IdP's name, its signing certificate and its sign-in address; the application's ACS address and its identifier. Exchanging metadata is most of what "setting up SAML" is. The standard is [SAML 2.0 Core](https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf), with the redirect and POST ways of carrying messages defined in [SAML 2.0 Bindings](https://docs.oasis-open.org/security/saml/v2.0/saml-bindings-2.0-os.pdf).

## OAuth 2.0: delegated access, not sign-in

**OAuth 2.0** ([RFC 6749](https://www.rfc-editor.org/rfc/rfc6749)) answers a different question from SAML. It is **delegated authorization**: letting an application act for you at another service, with limited permissions, *without giving that application your password*. The classic case: "let this calendar tool read my calendar". The four roles:

- the **resource owner**: you;
- the **client**: the application that wants access;
- the **authorization server**: the system that asks you "allow this?" and issues tokens (often the same company as your IdP);
- the **resource server**: the API that holds the thing (the calendar), and accepts the token.

The result is an **access token**, carrying the **scopes** you approved ([APIs and tokens](APIs-and-Tokens-From-Zero.md#scopes-and-least-privilege)). The client sends it to the API. Note what OAuth by itself does *not* say: who you are. An access token is "a ticket for this door"; it is not a name tag. People used OAuth for sign-in anyway, got it wrong in many different ways, and a standard layer was added on top.

## OpenID Connect: OAuth plus "who you are"

**OpenID Connect (OIDC)** is that layer ([OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)). It adds one thing to an OAuth request: the scope `openid`. When that scope is asked for, the authorization server (now called the **OpenID provider**, i.e. the IdP) also returns an **ID token**: a signed JWT that says who just signed in. The application that asked is the **relying party**. The rule from the token lesson applies: *the ID token is for the application that asked for the sign-in; the access token is for calling an API.*

The usual browser flow is the **authorization code flow** with **PKCE** (Proof Key for Code Exchange, [RFC 7636](https://www.rfc-editor.org/rfc/rfc7636), said "pixy"):

```text
  Browser                    App (relying party)                   IdP (OpenID provider)
     │ 1. open /reports ───────────►│                                │
     │◄─ 2. redirect: /authorize?client_id=…&scope=openid&redirect_uri=…
     │        &state=…&nonce=…&code_challenge=…
     │ 3. follow it ─────────────────────────────────────────────────►│
     │                              │      4. password + MFA (or an existing session)
     │◄─ 5. redirect to the app's redirect_uri with ?code=…&state=… ──│
     │ 6. browser delivers it ─────►│                                │
     │                              │ 7. app → IdP, directly (no browser):
     │                              │    "here is the code and my code_verifier"
     │                              │◄─ 8. ID token (+ access token) ─│
     │                              │ 9. app validates the ID token; makes its own session
     │◄─ 10. you are in ────────────│
```

What each piece is for:

- **`redirect_uri`**: where the IdP may send the browser. The IdP must only send it to addresses the application registered in advance. A loose match here is how codes get stolen.
- **`state`**: a random value the app makes up and checks on return. It ties the answer to *this* browser's request and stops a forged callback.
- **`code`**: a short-lived, single-use ticket that is *not* the tokens. It travels through the browser, which is where it could be read or copied.
- **`code_challenge` / `code_verifier` (PKCE)**: the app invents a random secret (the verifier), sends only its hash (the challenge) at step 2, and shows the secret itself at step 7. Someone who copies the code from the browser should not be able to redeem it without the verifier, which is the point of PKCE. [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700) (the current OAuth 2.0 security best practice) recommends this for the code flow.
- **`nonce`**: a random value that comes back *inside* the ID token, to tie the token to this sign-in and resist replay of an old one.
- The **token request** at step 7 is a direct server-to-server call, so the tokens themselves never travel through the browser's address bar.

### What the application must check in an ID token

| Claim | Meaning | The check |
|---|---|---|
| `iss` | Issuer: who signed it | Equals the IdP you configured, exactly. |
| `aud` | Audience: who it is for | Contains *your* client ID. |
| `exp` | Expiry (Unix time) | Not past. Also reject if `iat` ("issued at") is absurd. |
| `sub` | Subject: a stable ID for the person | Use this, not the email, as the key for the account. |
| `nonce` | Ties to this sign-in | Equals the value you sent. |
| signature | Made by the IdP's key | Valid, with the algorithm *you* expect (see the lab). |
| `email`, `groups`, … | Facts the IdP chose to include | Useful for authorization, but only as fresh as the token. |

The core spec says an `aud` must contain the client's own ID, that `exp` is the time on or after which the token must not be accepted, and that `nonce` exists to tie a session to a token and to mitigate replay ([claims register](#claims-register)). The exercise below lets you break each of these checks.

### SAML and OIDC side by side

| Feature | SAML 2.0 | OIDC |
|---|---|---|
| Message | XML assertion | JSON Web Token (ID token) |
| Typical use | Workforce SSO to business and older web applications | Newer web applications, mobile apps, single-page apps, and machine-to-machine federation |
| How the app gets it | The browser POSTs it | The app fetches it directly with a code (or the browser carries it in other, less common flows) |
| Setup | Exchange metadata files | Point at a "discovery" address (`/.well-known/openid-configuration`) and register a client |
| Built on OAuth | No | Yes |

Neither is "more secure" in general; both are as strong as their implementations and configuration. The usual failures are the same: a skipped check, a loose redirect, a long lifetime, a wrongly trusted key.

## SCIM: creating and removing accounts automatically

SSO decides *who may sign in*. It does not, by itself, create the account the application keeps for you. **SCIM** (System for Cross-domain Identity Management, [RFC 7644](https://www.rfc-editor.org/rfc/rfc7644), with the data model in [RFC 7643](https://www.rfc-editor.org/rfc/rfc7643)) is a standard HTTP and JSON interface an IdP uses to create, update and disable user and group records in other applications. When a new hire is added to the "finance" group in the directory, SCIM can create the account in the billing application and put it in the right group there; when they leave, the same channel disables it. Without SCIM, those steps become tickets and scripts, and the application that nobody wired up is where the stale accounts live. SCIM does not by itself end a session that is already open: see the leaver section.

## Groups, roles, and mapping people to access

The pattern in nearly every company is three layers:

```text
  person ──member of──► group ──is granted──► role ──contains──► permissions
  pat                   finance               billing-approver     billing:approve
```

- A **group** is a list of people, maintained in the directory ("finance", "engineering"). People *belong* to groups.
- A **role** is a named bundle of permissions for a job on one system ("billing-approver"). Groups are *mapped to* roles, usually in the application or in the IdP's configuration for that application.
- A **permission** is one allowed action on one kind of thing.

That is **RBAC** (role-based access control): access follows the role. It is easy to explain and audit, and it decays in two ways: groups multiply until nobody knows what they are for, and one over-broad group ("all-staff-admin") grants far more than its name suggests. **ABAC** (attribute-based access control) decides from attributes instead: "department = finance **and** device is managed **and** it is business hours". It is more flexible and harder to audit. Most real systems mix them ([Enterprise identity at scale](Enterprise-Identity-and-Secrets-at-Scale.md#authorization-rbac-and-abac)). The practical skills are naming roles after *tasks* rather than people, and reviewing them.

One trap worth knowing: when groups travel inside a token (the `groups` claim above), they are only as fresh as the token. If someone is removed from a group at 10:00 and their token lasts an hour, the application may keep honoring the old group until it expires or checks again.

## MFA, and why some MFA resists phishing

**MFA** is a second proof beyond the password ([Identity basics](Identity-Secrets-and-Zero-Trust-Basics.md#mfa-and-identity-providers)). Not all second proofs are equal against an attacker who is *talking to you*:

- **A code you type** (SMS or an authenticator app) can be typed into a fake page. The attacker relays it to the real site within the 30 seconds it is valid.
- **A push approval** ("Was this you? Approve / Deny") can be abused by **MFA fatigue**: the attacker already has the password, triggers prompt after prompt, and hopes the person taps "approve" to make it stop, or at 3 a.m. Defenses are number matching (you type the number the sign-in screen shows, so a blind tap does not work) and rate limits on prompts. These are vendor features; check what yours offers.
- **FIDO2 / WebAuthn** is the family usually called **phishing-resistant**. The browser asks the authenticator to sign a challenge, and the credential is **bound to the origin**: the website address (more exactly, a "relying party ID") it was registered for. A fake site at a different address should not obtain a signature that the real site accepts, however convincing it looks, because the browser is built not to offer the credential to the wrong origin ([W3C WebAuthn](https://www.w3.org/TR/webauthn-3/): credentials are "scoped to a given WebAuthn Relying Party").

Two clarifications. First, **origin binding is the point, not the hardware.** WebAuthn authenticators can be separate physical keys ("roaming") or built into a phone or laptop ("platform"; a **passkey** is a WebAuthn credential, and some are synced between a person's devices, which trades some protection for easier recovery, est.). CISA's guidance on phishing-resistant MFA names both kinds ([claims register](#claims-register)). Second, a hardware key *without* that origin check, such as a one-time-code button, or an SSH or smart-card key used outside a WebAuthn sign-in, protects the key from theft but does not by itself stop phishing ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#keeping-keys-storage-passphrases-and-hardware-keys)). And phishing-resistant is not theft-proof: if malware steals the *session* after sign-in, the strong sign-in already happened (the Evade step below).

## The identity lifecycle: joiner, mover, leaver

A person's access should follow their employment, which is why directories are tied to the HR system ([Enterprise identity at scale](Enterprise-Identity-and-Secrets-at-Scale.md#provisioning-scim-and-joiner-mover-leaver)):

- **Joiner.** Accounts and groups appear, the minimum for day one.
- **Mover.** The person changes team. The new access is added, and the **old access must be removed**; skipping that is how long-serving staff accumulate access nobody intended ("access creep").
- **Leaver.** Every account is disabled promptly, including the ones nobody remembers. Disabling the IdP account stops *new* sign-ins everywhere that trusts it. Sessions and tokens already issued may live until they expire or are revoked, and accounts that do not go through the IdP (local accounts, API keys, SSH keys) are untouched.

The lab below makes a leaver whose account is "still enabled" so you can see exactly what a review looks for.

## Service accounts and non-human identities

Not every identity is a person. A pipeline deploys, a service reads a database, a script runs at night. These are **non-human identities** (service accounts, API clients, bot users), and in most companies they outnumber people. They have no MFA and no HR event to end them, which makes them the stale accounts of the future. The questions are the same as for people, answered differently: *who owns it* (a named human or team), *what may it do* (least privilege), *how does it prove itself* (a long-lived key, which leaks, or a short-lived token issued to the workload by the platform, which is the OIDC federation described in [Enterprise identity at scale](Enterprise-Identity-and-Secrets-at-Scale.md#machines-service-accounts-and-workload-identity)), and *when does it end* (an expiry date and a review). This project's own case is on [Spacelift: no OIDC on this plan](Spacelift.md#no-oidc-on-this-plan).

## Conditional access

**Conditional access** makes the sign-in decision depend on context instead of only on "right password": which application is it, is the device managed, where is the sign-in coming from, is this behavior unusual? A policy might read: "an unmanaged device may read email but not open the admin console; any sign-in from a new country needs a phishing-resistant factor; an admin session lasts one hour". It is the IdP applying *authorization-like* rules at sign-in, and it is also the place where a stolen token is limited, because a policy can require the device and location to match again. What a given product can check, and on which plan, varies: confirm in its documentation (est.).

## Why identity is "the new perimeter", and how ZTNA uses the IdP

The old picture: a network with a wall around it. Inside the wall you were trusted. Applications moved to the cloud, people moved to home networks, and the wall stopped meaning anything. What remains constant is the person (or the service) asking. So the question each request must answer is no longer "are you inside?" but "who are you, on what device, and may you do this?". That is **identity as the perimeter**, and it is the heart of [zero trust](Identity-Secrets-and-Zero-Trust-Basics.md#zero-trust-with-the-marketing-removed).

A zero-trust network access (ZTNA) product like the one in this project plugs into exactly the machinery above. Per [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md), sign-in to Twingate is delegated to an identity provider; Twingate itself holds no passwords. The user signs in at the IdP (with MFA), the IdP vouches for them, and the ZTNA service turns "this is pat, a member of this group" into the list of resources pat may reach. The connectors in [Zero trust at home](Zero-Trust-at-Home-Two-Connectors-and-Failover.md) then carry only the traffic that list allows. Two consequences:

- **The IdP becomes critical.** If it is down, nobody signs in; if an attacker controls it, they hold everyone's roles ([the honest limits on that page](Zero-Trust-at-Home-Two-Connectors-and-Failover.md#honest-limits)). Protect it with phishing-resistant MFA and keep break-glass accounts ([Enterprise identity at scale](Enterprise-Identity-and-Secrets-at-Scale.md#privileged-access-pam-just-in-time-and-break-glass)).
- **What you can do depends on the IdP your plan supports.** The maintainer's own lab signs in through an identity provider using SAML, and SAML sign-in is not available on the free plan of the ZTNA product (his statement, not something this wiki verified; the plan details change, so check the vendor's pricing and documentation pages on the day). People on the free plan use a social login (a sign-in through a large consumer account such as the ones listed on [Build it from zero](Build-It-From-Zero-Accounts-to-Stage-1.md)), which is OIDC underneath (est.). Everything on this page applies to both; only the label on the button changes.

## Free theory path: a lab on your own computer

Everything here runs on your own computer, needs no account and costs nothing. All "tokens" and "assertions" are **fake**, built by the scripts at run time; nothing token-shaped or key-shaped is stored on this page. Each exercise follows **predict** (write down what you expect first), **do**, **check**, **undo**.

**Which track.** Commands are given for **Bash** (Linux, macOS Terminal, WSL, Git Bash) and **PowerShell** (Windows). The scripts are Python and identical on both tracks: save each listing to a file with a text editor, in one new folder, and run it with `python3 -I name.py` (Bash) or `python -I name.py` (PowerShell; on Windows `python` may be `py -3`, depending on how Python was installed). The `-I` flag tells Python to ignore the folder's other files and environment variables when starting, which is a good habit when running scripts you did not write. Start with a new empty folder:

```bash
mkdir ~/idlab && cd ~/idlab
```

```powershell
New-Item -ItemType Directory $HOME\idlab | Out-Null; Set-Location $HOME\idlab
```

### Exercise 1: sort the failures (paper)

**Predict.** For each line, write A (authentication), Z (authorization) or C (accounting):

1. A user types the wrong password three times and is locked out.
2. A signed-in intern clicks "Delete production database" and sees "You do not have permission".
3. A weekly report lists every sign-in from outside the country.
4. An API returns `401` because the token expired.
5. An API returns `403` because the token lacks the `write` scope.
6. A manager asks "who added Blake to the admin group, and when?".

**Do.** Write the six letters. **Check.** 1 A, 2 Z, 3 C, 4 A, 5 Z, 6 C. If 4 and 5 felt the same, reread the `401`/`403` paragraph in the [token lesson](APIs-and-Tokens-From-Zero.md#authentication-and-authorization). **Undo.** Nothing to undo.

### Exercise 2: build the fake samples

**Predict.** An ID token is signed. If you can read every claim in it with no key, what exactly does the signature protect?

**Do.** Save this as `make_samples.py`, then run it:

```python
# make_samples.py: build a FAKE SAML assertion and a FAKE OIDC ID token on your own machine.
# Nothing is sent anywhere. The signing key is random and is never printed.
import base64, hashlib, hmac, json, os, secrets, time
import xml.etree.ElementTree as ET

now = int(time.time())
iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))

# ---- 1. A fake SAML assertion (what an identity provider sends to an application) ----
SAML = "urn:oasis:names:tc:SAML:2.0:assertion"
DS = "http://www.w3.org/2000/09/xmldsig#"
ET.register_namespace("saml", SAML)
ET.register_namespace("ds", DS)
REQUEST_ID = "_req-lab-1"          # the ID the application put in its AuthnRequest (step 2 of the flow)
a = ET.Element(f"{{{SAML}}}Assertion", ID="_lab1", Version="2.0", IssueInstant=iso(now))
ET.SubElement(a, f"{{{SAML}}}Issuer").text = "https://idp.example.com/lab"
sig = ET.SubElement(a, f"{{{DS}}}Signature")
si = ET.SubElement(sig, f"{{{DS}}}SignedInfo")
ET.SubElement(si, f"{{{DS}}}SignatureMethod", Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256")
dig = ET.SubElement(si, f"{{{DS}}}Reference", URI="#_lab1")
ET.SubElement(dig, f"{{{DS}}}DigestValue").text = base64.b64encode(hashlib.sha256(b"lab").digest()).decode()
ET.SubElement(sig, f"{{{DS}}}SignatureValue").text = "THIS-IS-A-PLACEHOLDER-NOT-A-SIGNATURE"
subj = ET.SubElement(a, f"{{{SAML}}}Subject")
ET.SubElement(subj, f"{{{SAML}}}NameID").text = "pat@example.com"
ET.SubElement(subj, f"{{{SAML}}}SubjectConfirmationData",
              Recipient="https://app.example.com/saml/acs", InResponseTo=REQUEST_ID,
              NotOnOrAfter=iso(now + 300))
cond = ET.SubElement(a, f"{{{SAML}}}Conditions", NotBefore=iso(now - 30), NotOnOrAfter=iso(now + 300))
ET.SubElement(ET.SubElement(cond, f"{{{SAML}}}AudienceRestriction"), f"{{{SAML}}}Audience").text = "https://app.example.com/saml/metadata"
ET.SubElement(a, f"{{{SAML}}}AuthnStatement", AuthnInstant=iso(now - 5))
attrs = ET.SubElement(a, f"{{{SAML}}}AttributeStatement")
for name, values in (("email", ["pat@example.com"]), ("groups", ["staff", "billing-readers"])):
    at = ET.SubElement(attrs, f"{{{SAML}}}Attribute", Name=name)
    for v in values:
        ET.SubElement(at, f"{{{SAML}}}AttributeValue").text = v
ET.indent(a)                                       # one tag per line, so a person can read it
ET.ElementTree(a).write("assertion.xml", encoding="utf-8", xml_declaration=True)

# ---- 2. A fake OIDC ID token, signed with a throwaway in-memory key (HS256) ----
def b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
def part(obj) -> str:
    return b64u(json.dumps(obj, separators=(",", ":")).encode())

key = secrets.token_bytes(32)                      # never printed, never saved
header = {"alg": "HS256", "typ": "JWT"}
claims = {"iss": "https://idp.example.com/lab", "sub": "user-1001", "aud": "lab-app",
          "iat": now, "exp": now + 900, "nonce": "lab-nonce-1",
          "email": "pat@example.com", "groups": ["staff", "billing-readers"]}
signing_input = part(header) + "." + part(claims)
sig_b64 = b64u(hmac.new(key, signing_input.encode(), hashlib.sha256).digest())
with open("idtoken.txt", "w") as f:
    f.write(signing_input + "." + sig_b64)

# ---- 3. Also write a tampered copy: same signature, but the claims now say "admin" ----
evil = dict(claims, groups=["staff", "billing-readers", "admins"])
with open("idtoken-tampered.txt", "w") as f:
    f.write(part(header) + "." + part(evil) + "." + sig_b64)

# Kept only so read_samples.py can check the signature, in a file only you can read. Delete it at the end.
fd = os.open("lab.key", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "wb") as f:
    f.write(key)
print("wrote assertion.xml, idtoken.txt, idtoken-tampered.txt, lab.key (a throwaway)")
```

```bash
python3 -I make_samples.py
ls -l
```

```powershell
python -I make_samples.py
Get-ChildItem
```

**Check.** One line, `wrote assertion.xml, idtoken.txt, idtoken-tampered.txt, lab.key (a throwaway)`, and four new files. `lab.key` is random bytes from this run, never printed; it exists so the next script can check the signature. The SAML file is a **simplified** assertion in the real shape: a real one sits inside a signed `Response`, carries more elements, and is signed over a canonicalized form of the XML. Its `SignatureValue` here is a placeholder, so **it proves nothing**; the ID token, on the other hand, carries a real HMAC signature. The tampered token has the same signature as the good one but different claims. **Undo.** Do it in Exercise 5's cleanup; the next exercises need these files.

### Exercise 3: read a SAML assertion

**Predict.** Which element names the IdP, which names the person, which names the application the assertion is for, and which says when it stops being valid?

**Do.** Read the file as plain text first:

```bash
cat assertion.xml
```

```powershell
Get-Content assertion.xml
```

Find these with your eyes: `Issuer`, `NameID`, `Audience`, `InResponseTo`, `NotBefore` / `NotOnOrAfter`, the `Attribute` named `groups`, `SignatureMethod`, `SignatureValue`. Now save and run the reader, which pulls out the same fields the way an application would:

```python
# read_samples.py: read the fake SAML assertion and the fake ID token the way an application must.
import base64, hashlib, hmac, json, sys, time
import xml.etree.ElementTree as ET     # fine for a file you just made; see the page about real, untrusted XML

SAML = "{urn:oasis:names:tc:SAML:2.0:assertion}"
DS = "{http://www.w3.org/2000/09/xmldsig#}"
now = int(time.time())

print("== SAML assertion ==")
a = ET.parse("assertion.xml").getroot()
print("issuer       :", a.findtext(SAML + "Issuer"))
print("who (NameID) :", a.findtext(f"{SAML}Subject/{SAML}NameID"))
c = a.find(SAML + "Conditions")
print("valid        :", c.get("NotBefore"), "to", c.get("NotOnOrAfter"))
print("audience     :", c.findtext(f"{SAML}AudienceRestriction/{SAML}Audience"))
scd = a.find(f"{SAML}Subject/{SAML}SubjectConfirmationData")
print("sent to (ACS):", scd.get("Recipient"))
print("answers req id:", scd.get("InResponseTo"), "(the app must compare this with the id it sent)")
for at in a.iter(SAML + "Attribute"):
    print("attribute    :", at.get("Name"), "=", [v.text for v in at])
print("signature alg:", a.find(f"{DS}Signature/{DS}SignedInfo/{DS}SignatureMethod").get("Algorithm"))
print("signature val:", a.findtext(f"{DS}Signature/{DS}SignatureValue"))

def b64u_dec(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def read_token(path, key):
    h, p, s = open(path).read().strip().split(".")
    header, claims = json.loads(b64u_dec(h)), json.loads(b64u_dec(p))
    expect = hmac.new(key, (h + "." + p).encode(), hashlib.sha256).digest()
    ok = header["alg"] == "HS256" and hmac.compare_digest(expect, b64u_dec(s))
    print(f"-- {path}")
    print("header       :", header)
    print("iss / aud    :", claims["iss"], "/", claims["aud"])
    print("sub          :", claims["sub"])
    print("lifetime     :", claims["exp"] - claims["iat"], "seconds;", "expired" if claims["exp"] <= now else "not expired", "right now")
    print("groups       :", claims["groups"])
    print("signature ok :", ok)

print("\n== OIDC ID token ==")
key = open("lab.key", "rb").read()
read_token("idtoken.txt", key)
read_token("idtoken-tampered.txt", key)
```

```bash
python3 -I read_samples.py
```

```powershell
python -I read_samples.py
```

**Check.** The first block of output, from a run on 2026-10-21 (times differ on yours):

```text
== SAML assertion ==
issuer       : https://idp.example.com/lab
who (NameID) : pat@example.com
valid        : 2026-10-21T22:50:47Z to 2026-10-21T22:56:17Z
audience     : https://app.example.com/saml/metadata
sent to (ACS): https://app.example.com/saml/acs
answers req id: _req-lab-1 (the app must compare this with the id it sent)
attribute    : email = ['pat@example.com']
attribute    : groups = ['staff', 'billing-readers']
signature alg: http://www.w3.org/2001/04/xmldsig-more#rsa-sha256
signature val: THIS-IS-A-PLACEHOLDER-NOT-A-SIGNATURE
```

The window is five and a half minutes long: a short window is a defense. Notice what the script did **not** do: it did not verify the signature, because a real check needs the IdP's certificate and a maintained XML-signature library. **Do not write that part yourself.** XML signatures have a long history of bypasses (for example, an attacker adds a second, unsigned assertion that a naive reader picks up instead of the signed one), and Python's own documentation lists XML attacks (such as entity expansion) that its parsers can be vulnerable to, depending on the version of the Expat library underneath. In a real application, use your framework's SAML library and its documented configuration. **Undo.** Nothing yet.

### Exercise 4: read an ID token and watch a signature fail

**Predict.** The tampered token differs from the good one only in its `groups` claim, and carries the *same* signature. Will the signature check pass?

**Do.** First decode the middle part with a few lines of the Python standard library (no extra packages, and the same on every operating system), to see that it needs no key:

```bash
python3 -I -c "import base64,sys; p=open('idtoken.txt').read().split('.')[1]; print(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)).decode())"
```

```powershell
python -I -c "import base64,sys; p=open('idtoken.txt').read().split('.')[1]; print(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)).decode())"
```

(The `-I` flag is Python's isolated mode. The `=` padding that base64url strips is put back before decoding. A shell-only version needs `base64 -d` on Linux but `-D` on older macOS, which is why this page uses Python.) The output of `read_samples.py` you already ran has a second block:

```text
== OIDC ID token ==
-- idtoken.txt
header       : {'alg': 'HS256', 'typ': 'JWT'}
iss / aud    : https://idp.example.com/lab / lab-app
sub          : user-1001
lifetime     : 900 seconds; not expired right now
groups       : ['staff', 'billing-readers']
signature ok : True
-- idtoken-tampered.txt
header       : {'alg': 'HS256', 'typ': 'JWT'}
iss / aud    : https://idp.example.com/lab / lab-app
sub          : user-1001
lifetime     : 900 seconds; not expired right now
groups       : ['staff', 'billing-readers', 'admins']
signature ok : False
```

**Check.** The decode needed no key (base64 is encoding, as the token lesson says), so a holder can read every claim, including `groups`. Changing one claim without the signing key breaks the signature, which is the whole job of the signature. Write down the answers to these:

1. Which claim says who the token is *about*? (`sub`.) Who issued it? (`iss`.) Who is it *for*? (`aud`.) When does it end? (`exp`, a Unix time; the script shows a lifetime of 900 seconds, which is `exp - iat`.)
2. An application checks `aud` equals its own client ID. What attack does that stop? (A token issued for App A being presented to App B.)
3. The header says `HS256`, a *symmetric* algorithm: whoever can verify can also forge. Real IdPs normally sign with an *asymmetric* one so that applications hold only a public key. The page's sample uses HS256 only because Python can do it with no extra library.
4. In `read_samples.py` the check reads `header["alg"] == "HS256" and ...`. Why is it there, rather than trusting whatever algorithm the token's own header names? (A verifier that obeys the header can be told `"alg":"none"`, meaning no signature, and accept a forgery. An application decides which algorithm it accepts; the token does not get a vote. This is a well-known JWT flaw.)

**Undo.** Nothing yet; the cleanup is at the end of Exercise 5.

### Exercise 5: a role map on paper, then in code

**Predict.** Here is a made-up company. Before running anything, fill in the table on paper: what can each person actually do?

| Person | Status | Groups |
|---|---|---|
| alex | active | staff, finance |
| blake | active | staff, engineering |
| casey | active | staff, it-admins |
| drew | left 20 days ago | none |

| Group | Roles |
|---|---|
| staff | wiki-reader |
| finance | billing-reader, billing-approver |
| engineering | repo-writer |
| it-admins | directory-admin, billing-reader |

| Role | Permissions |
|---|---|
| wiki-reader | wiki:read |
| billing-reader | billing:read |
| billing-approver | billing:approve |
| repo-writer | repo:write |
| directory-admin | directory:read, directory:write |

**Do.** Only now run the code. Save `build_org.py` (makes the same data plus a sign-in log and a change log) and `review.py` (computes effective permissions and asks four questions of the logs):

```python
# build_org.py: a tiny made-up company: people, groups, roles, and a sign-in log. All fake.
import json, time

day = 86400
now = int(time.time())
iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))

org = {
    "users": {
        "alex@example.com": {"status": "active", "groups": ["staff", "finance"]},
        "blake@example.com": {"status": "active", "groups": ["staff", "engineering"]},
        "casey@example.com": {"status": "active", "groups": ["staff", "it-admins"]},
        "drew@example.com": {"status": "left", "enabled": False, "left_on": iso(now - 20 * day), "groups": []},
    },
    "group_roles": {
        "staff": ["wiki-reader"],
        "finance": ["billing-reader", "billing-approver"],
        "engineering": ["repo-writer"],
        "it-admins": ["directory-admin", "billing-reader"],
        "all-staff-admin": ["directory-admin"],     # the over-broad group the Break step will use
    },
    "role_permissions": {
        "wiki-reader": ["wiki:read"],
        "billing-reader": ["billing:read"],
        "billing-approver": ["billing:approve"],
        "repo-writer": ["repo:write"],
        "directory-admin": ["directory:write", "directory:read"],
    },
}
log = [
    {"time": iso(now - 3 * day), "user": "alex@example.com", "app": "billing", "result": "success", "mfa": "fido2"},
    {"time": iso(now - 2 * day), "user": "blake@example.com", "app": "repo", "result": "success", "mfa": "totp"},
    {"time": iso(now - 2 * day), "user": "casey@example.com", "app": "directory", "result": "success", "mfa": "fido2"},
    {"time": iso(now - 25 * day), "user": "drew@example.com", "app": "repo", "result": "success", "mfa": "none"},
    {"time": iso(now - 1 * day), "user": "blake@example.com", "app": "directory", "result": "denied", "mfa": "totp"},
]
changes = [
    {"time": iso(now - 40 * day), "actor": "hr-sync", "action": "add-member", "group": "it-admins", "user": "casey@example.com"},
    {"time": iso(now - 20 * day), "actor": "hr-sync", "action": "remove-all-groups", "group": "*", "user": "drew@example.com"},
]
json.dump(org, open("org.json", "w"), indent=2)
with open("changes.jsonl", "w") as f:
    for line in changes:
        f.write(json.dumps(line) + "\n")
with open("signins.jsonl", "w") as f:
    for line in log:
        f.write(json.dumps(line) + "\n")
print("wrote org.json, signins.jsonl, changes.jsonl")
```

```python
# review.py: answer three questions from org.json and signins.jsonl
import json
org = json.load(open("org.json"))
logs = [json.loads(l) for l in open("signins.jsonl")]
changes = [json.loads(l) for l in open("changes.jsonl")]
PRIVILEGED_GROUPS = {"it-admins", "all-staff-admin"}

def perms(user):
    out = set()
    for g in org["users"][user]["groups"]:
        for role in org["group_roles"].get(g, []):
            out.update(org["role_permissions"][role])
    return out

print("1. Effective permissions")
for u in org["users"]:
    print(f"   {u:20} {sorted(perms(u))}")

print("2. Who can change the directory itself")
for u in org["users"]:
    if "directory:write" in perms(u):
        print("  ", u, "groups:", org["users"][u]["groups"])

print("3. Leavers: still enabled, still in groups, or signed in after leaving")
for u, d in org["users"].items():
    if d["status"] == "left":
        after = [e for e in logs if e["user"] == u and e["time"] > d["left_on"] and e["result"] == "success"]
        problems = []
        if d.get("enabled", True):
            problems.append("account still enabled")
        if d["groups"]:
            problems.append("still in groups " + str(d["groups"]))
        if after:
            problems.append(f"{len(after)} sign-in(s) after leaving")
        print("  ", u, "->", "; ".join(problems) if problems else "clean")

print("4. Sign-ins without a phishing-resistant factor")
for e in logs:
    if e["mfa"] not in ("fido2", "passkey"):
        print("  ", e["time"], e["user"], e["app"], "mfa =", e["mfa"])

print("5. Changes to privileged groups, newest last")
for c in sorted(changes, key=lambda c: c["time"]):
    if c["group"] in PRIVILEGED_GROUPS:
        print("  ", c["time"], c["actor"], c["action"], c["group"], c["user"])
```

```bash
python3 -I build_org.py
python3 -I review.py
```

```powershell
python -I build_org.py
python -I review.py
```

**Check.** The first lines should match your table:

```text
1. Effective permissions
   alex@example.com     ['billing:approve', 'billing:read', 'wiki:read']
   blake@example.com    ['repo:write', 'wiki:read']
   casey@example.com    ['billing:read', 'directory:read', 'directory:write', 'wiki:read']
   drew@example.com     []
2. Who can change the directory itself
   casey@example.com groups: ['staff', 'it-admins']
3. Leavers: still enabled, still in groups, or signed in after leaving
   drew@example.com -> clean
```

(Sections 4 and 5 list the sign-ins without a phishing-resistant factor and the privileged group changes; yours will show different times.) Note the shape of the work: nothing here is hard, and it is exactly what an access review is. A company has thousands of people and hundreds of groups, so the review has to be a query, not a meeting.

**Undo (the whole free lab).** Delete the folder and its throwaway key:

```bash
cd ~ && rm -rf ~/idlab
```

```powershell
Set-Location $HOME; Remove-Item -Recurse -Force $HOME\idlab
```

Keep the folder for the mini-loop below if you will do that now.

## Optional: your own identity provider, locally (your own computer)

The free path teaches the vocabulary on fake data. This path makes a *real* sign-in happen, on your computer only, using **Keycloak**, an open-source identity provider run in a container. It is optional. It uses your own machine, no cloud account and no vendor sign-up, so there is no provider bill; the cost is your computer's memory and disk while it runs and the image download (size not checked: est.). Read the teardown first.

> **Status of this path: written from Keycloak's and Docker's documentation, never run for this page.** The `docker run` command and the console steps follow Keycloak's "Getting started with Docker" guide as it read on 2026-10-21 (which showed version 26.8.1; use the version the guide shows on the day you read it). Menu names change between releases. Passing an environment variable with `-e NAME` and no value is standard Docker behavior (est.; not re-checked against its reference). The script `oidc_login.py` was tested only against a stand-in server that speaks the same three requests, not against Keycloak.

**Teardown (read first).**

```bash
docker stop idlab                 # --rm below removes the container, and its data, when it stops
docker image rm quay.io/keycloak/keycloak:26.8.1     # optional: reclaim the disk
unset KC_BOOTSTRAP_ADMIN_USERNAME KC_BOOTSTRAP_ADMIN_PASSWORD
```

```powershell
docker stop idlab
docker image rm quay.io/keycloak/keycloak:26.8.1
Remove-Item Env:KC_BOOTSTRAP_ADMIN_USERNAME, Env:KC_BOOTSTRAP_ADMIN_PASSWORD
```

Podman users can replace `docker` with `podman` (est.). `docker ps` should show nothing named `idlab` afterwards.

**Safety rules for this lab.** The container publishes its port on **127.0.0.1 only** (`-p 127.0.0.1:8080:8080`), so nothing else on your network can reach it; without the `127.0.0.1` Docker publishes on all interfaces. Never mount the Docker socket into it. Keycloak's `start-dev` mode is for learning, over plain HTTP, with an in-container database; Keycloak's own guide says to switch to a production database, TLS and a stronger admin password before production use, and this lab is not that. Do not put real people or real passwords in it. The admin password below is generated fresh and never written to a file.

**Start it** (a new random admin password each time, passed by name so it does not appear in the command line):

```bash
export KC_BOOTSTRAP_ADMIN_USERNAME=admin
export KC_BOOTSTRAP_ADMIN_PASSWORD="$(python3 -I -c 'import secrets; print(secrets.token_urlsafe(16))')"
docker run --name idlab --rm -p 127.0.0.1:8080:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME -e KC_BOOTSTRAP_ADMIN_PASSWORD \
  quay.io/keycloak/keycloak:26.8.1 start-dev
```

```powershell
$env:KC_BOOTSTRAP_ADMIN_USERNAME = "admin"
$env:KC_BOOTSTRAP_ADMIN_PASSWORD = (python -I -c "import secrets; print(secrets.token_urlsafe(16))")
docker run --name idlab --rm -p 127.0.0.1:8080:8080 `
  -e KC_BOOTSTRAP_ADMIN_USERNAME -e KC_BOOTSTRAP_ADMIN_PASSWORD `
  quay.io/keycloak/keycloak:26.8.1 start-dev
```

Leave that terminal running. In a second terminal, print the password once to read it (`printenv KC_BOOTSTRAP_ADMIN_PASSWORD`, or `$env:KC_BOOTSTRAP_ADMIN_PASSWORD`), then open `http://127.0.0.1:8080/admin/` in a browser and sign in as `admin`.

> **Screenshot to take yourself:** the Keycloak admin console after you create `myrealm`, with the Users list open (see the [Screenshots policy](Screenshots-Policy.md); a real console screenshot is not committed to this repository).
> Capture: the left menu with the realm name visible and the Users page showing `pat` and `sam`.
> Look for: the realm selector, and a user's Groups tab listing the groups you made.
> Redact: anything beyond the throwaway lab (other realms, a real email address, the admin password if it appears in a banner).

**Build the directory and the application** (follow the console; each step is in Keycloak's guide):

1. Create a **realm** named `myrealm` (a realm is Keycloak's word for a tenant: an isolated set of users and applications). Do not use the built-in `master` realm for your own users; the guide says to use it only for managing Keycloak.
2. Create two **groups**, `staff` and `billing-readers`, and two **users**, `pat` and `sam`, each with a password you choose (any throwaway; **Temporary** off). Put `pat` in both groups and `sam` in `staff` only.
3. Create a **client** (an application): type **OpenID Connect**, client ID `myclient`, **Client authentication off** (a public client), **Standard flow** on, and set **Valid redirect URIs** to exactly `http://127.0.0.1:8765/callback`. If the console offers a setting for requiring PKCE, turn it on (est.: the name and location vary by version).
4. Add a **groups** claim so you can see it: in the client's dedicated scope, add a mapper of type *Group Membership* with the token claim name `groups` (est.; the menu path varies by version).

**Look at what the server publishes.** Keycloak serves its OIDC "discovery document" at `/realms/{realm}/.well-known/openid-configuration` and its SAML IdP metadata at `/realms/{realm}/protocol/saml/descriptor` (both paths are in its documentation):

```bash
curl -s http://127.0.0.1:8080/realms/myrealm/.well-known/openid-configuration | python3 -I -m json.tool | head -30
curl -s http://127.0.0.1:8080/realms/myrealm/protocol/saml/descriptor | head -c 1200
```

```powershell
curl.exe -s http://127.0.0.1:8080/realms/myrealm/.well-known/openid-configuration | python -I -m json.tool | Select-Object -First 30
curl.exe -s http://127.0.0.1:8080/realms/myrealm/protocol/saml/descriptor | Select-Object -First 5
```

Find `issuer`, `authorization_endpoint`, `token_endpoint` and `jwks_uri` (where the signing *public* keys are published) in the first, and the `EntityDescriptor`, the signing certificate and the single-sign-on URLs in the second. That is a SAML IdP's metadata, the file you would hand to a SAML application. (In the metadata, the certificate is a *public* certificate, safe to display.)

**Do the sign-in by hand.** Save this as `oidc_login.py`. It performs the code flow with PKCE from the diagram above: it reads the discovery document, prints an address for you to open, listens once on `127.0.0.1:8765` for the redirect, checks `state`, redeems the code with the verifier, and prints the ID token's claims. It prints no token.

```python
# oidc_login.py: the OIDC authorization code flow with PKCE, by hand, against YOUR local identity provider.
# Prints the claims of the ID token. It does not verify the signature (see the page for why, and what a real app does).
import argparse, base64, hashlib, json, secrets, sys, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

ap = argparse.ArgumentParser()
ap.add_argument("--base", default="http://127.0.0.1:8080")
ap.add_argument("--realm", default="myrealm")
ap.add_argument("--client", default="myclient")
ap.add_argument("--port", type=int, default=8765)
args = ap.parse_args()
redirect_uri = f"http://127.0.0.1:{args.port}/callback"

b64u = lambda raw: base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
disc_url = f"{args.base}/realms/{args.realm}/.well-known/openid-configuration"
with urllib.request.urlopen(disc_url, timeout=10) as r:
    disc = json.load(r)

verifier = secrets.token_urlsafe(48)                       # stays in this process
challenge = b64u(hashlib.sha256(verifier.encode()).digest())
state, nonce = secrets.token_urlsafe(16), secrets.token_urlsafe(16)
url = disc["authorization_endpoint"] + "?" + urllib.parse.urlencode({
    "response_type": "code", "client_id": args.client, "redirect_uri": redirect_uri,
    "scope": "openid", "state": state, "nonce": nonce,
    "code_challenge": challenge, "code_challenge_method": "S256"})

got = {}
class Callback(BaseHTTPRequestHandler):
    def do_GET(self):
        got.update({k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).items()})
        self.send_response(200); self.send_header("Content-Type", "text/plain"); self.end_headers()
        self.wfile.write(b"You can close this tab and go back to the terminal.\n")
    def log_message(self, *a):                             # keep the code out of the console log
        pass

server = HTTPServer(("127.0.0.1", args.port), Callback)    # loopback only
print("Open this address in your browser and sign in:\n" + url + "\n")
server.handle_request()                                    # waits for exactly one request
server.server_close()

if got.get("state") != state:
    sys.exit("state did not match: stop. (This is the check that stops a forged callback.)")
if "code" not in got:
    sys.exit("no code came back: " + str(got.get("error")))

body = urllib.parse.urlencode({"grant_type": "authorization_code", "code": got["code"],
                               "redirect_uri": redirect_uri, "client_id": args.client,
                               "code_verifier": verifier}).encode()
with urllib.request.urlopen(urllib.request.Request(disc["token_endpoint"], data=body), timeout=10) as r:
    tok = json.load(r)

payload = tok["id_token"].split(".")[1]
claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
print("token response keys:", sorted(tok))
for k in ("iss", "aud", "sub", "iat", "exp", "nonce", "preferred_username", "groups"):
    if k in claims:
        print(f"{k:20}", claims[k])
print("nonce matches    :", claims.get("nonce") == nonce)
print("issuer matches   :", claims.get("iss") == disc["issuer"])
```

```bash
python3 -I oidc_login.py
```

```powershell
python -I oidc_login.py
```

Open the printed address in your browser, sign in as `pat`, and come back to the terminal. **Predict first:** which of the diagram's ten steps do you see in the browser's address bar, and which happen only in the terminal? (Steps 2 to 6 you can see; the token request at step 7 and 8 you cannot, which is the point of the code.) **Check:** the script prints `iss`, `aud` (your client ID), `sub`, `exp` and `groups`, and `nonce matches : True`. The `iss` should equal the `issuer` in the discovery document. Sign in as `sam` and compare the `groups`. The script does **not** verify the signature: a real application downloads the key from `jwks_uri`, checks the signature and the other items in the table above, and should use an OpenID Connect library to do it rather than hand-written code.

**Optional SAML half.** Create a second client of type **SAML** with any made-up client ID and the made-up address `https://app.example.com/saml/acs` (nothing needs to be listening there), and look at its settings: *Name ID format*, *Sign assertions*, *Valid redirect URIs*. You are looking at the knobs that decide what Exercise 3's assertion contains. The sign-in itself needs a real application to receive it, which is beyond this page.

**A hosted free-tier identity provider** is the other optional route. This page names none, because vendor free tiers change and none was read for it. If you choose one, read its current pricing and terms on the day, write down the date, use a throwaway tenant with no real data, and delete the tenant afterwards.

## Build, break, detect, evade, defend

A small loop on the fake company from Exercise 5 (rebuild it with `build_org.py` if you deleted the folder). Local and fake: no real systems, no real targets.

**Build.** You did: users, groups, roles, permissions, a sign-in log and a change log, with a review script that answers "who can do what". The review is baseline-clean: one directory admin (casey), a leaver (drew) with no groups, no enabled account and no sign-ins after leaving.

**Break.** Two classic mistakes, one command:

```bash
python3 -I - <<'PY'
import json, time
org = json.load(open("org.json"))
org["users"]["blake@example.com"]["groups"].append("all-staff-admin")      # an over-broad group
d = org["users"]["drew@example.com"]                                         # a stale leaver
d["enabled"], d["groups"] = True, ["staff", "engineering"]
json.dump(org, open("org.json", "w"), indent=2)
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
with open("changes.jsonl", "a") as f:
    f.write(json.dumps({"time": now, "actor": "casey@example.com", "action": "add-member", "group": "all-staff-admin", "user": "blake@example.com"}) + "\n")
with open("signins.jsonl", "a") as f:
    f.write(json.dumps({"time": now, "user": "drew@example.com", "app": "repo", "result": "success", "mfa": "none"}) + "\n")
PY
```

```powershell
@'
import json, time
org = json.load(open("org.json"))
org["users"]["blake@example.com"]["groups"].append("all-staff-admin")
d = org["users"]["drew@example.com"]
d["enabled"], d["groups"] = True, ["staff", "engineering"]
json.dump(org, open("org.json", "w"), indent=2)
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
with open("changes.jsonl", "a") as f:
    f.write(json.dumps({"time": now, "actor": "casey@example.com", "action": "add-member", "group": "all-staff-admin", "user": "blake@example.com"}) + "\n")
with open("signins.jsonl", "a") as f:
    f.write(json.dumps({"time": now, "user": "drew@example.com", "app": "repo", "result": "success", "mfa": "none"}) + "\n")
'@ | python -I -
```

(The change-log and sign-in lines are written by hand here to *simulate* what a real IdP's audit trail would record when an administrator adds a member and a leaver signs in. In real life you would not write them; the system would, which is what makes them evidence.)

**Detect.** Run `python3 -I review.py` again (`python -I review.py` in PowerShell). The output now reads, in part:

```text
2. Who can change the directory itself
   blake@example.com groups: ['staff', 'engineering', 'all-staff-admin']
   casey@example.com groups: ['staff', 'it-admins']
3. Leavers: still enabled, still in groups, or signed in after leaving
   drew@example.com -> account still enabled; still in groups ['staff', 'engineering']; 1 sign-in(s) after leaving
5. Changes to privileged groups, newest last
   2026-09-11T... hr-sync add-member it-admins casey@example.com
   2026-10-21T... casey@example.com add-member all-staff-admin blake@example.com
```

Blake, an engineer, can now change the directory; the *change log* (section 5) shows who did it and when, and the *sign-in log* shows the leaver coming back. Notice which log answers which question: the sign-in log alone would not have shown the over-broad grant, and the change log alone would not have shown that the leaver signed in. This is why accounting needs both, and why you look at changes to *privileged* groups first. Real systems call these things by their own names (audit log, sign-in log, directory activity); look for the equivalent in your IdP.

**Evade, in words only.** Nothing here is a working technique against a real system; these are the patterns a defender should expect.

- **Token or session theft.** The attacker does not attack the sign-in; they take what the sign-in *produced*. Malware on a laptop, or a malicious browser extension, copies the session cookie or a token. Replayed from elsewhere, it carries everything the original sign-in earned, including the MFA that already happened. A stronger first factor does not help once the session exists; what helps is a short lifetime, binding the session to the device, and policy that re-checks.
- **Consent phishing.** The attacker never asks for your password. They register an ordinary-looking application and send a link to a *real* IdP consent screen: "Allow Calendar Helper to read your mail and files?". If a person clicks "Accept", the IdP itself issues the attacker's application a legitimate access token for those scopes. There is no fake login page, no password, and MFA is irrelevant because the user was genuinely signed in. This is OAuth working as designed, used by the wrong party.
- **MFA fatigue and relay phishing.** A push prompt sent again and again until someone accepts, and a fake sign-in page that relays what you type to the real one in real time, collecting the session at the end. FIDO2/WebAuthn blocks the relay because the key will not sign for the wrong origin, and number matching blunts the blind tap.
- **Groups and stale access.** Not a bypass, a pattern: attackers look for the leftover account and the over-broad group because nothing alerts on them.

**Defend.**

- **Short sessions and token lifetimes**, with a refresh policy that can be revoked. The lab's token lived 900 seconds. How long is right for your risk is a business decision; there is no universal number (est.).
- **Conditional access** (managed device, expected location, phishing-resistant factor for admin actions) to limit what a stolen token is worth.
- **Phishing-resistant MFA** (FIDO2/WebAuthn) for everyone with any privilege, with number matching and prompt limits where push is still used, and real recovery paths (two keys, recovery codes in a password manager) so people are not locked out and talked into weaker fallbacks.
- **Admin consent** for applications: ordinary users may not grant a new application broad scopes; an administrator reviews requests. Review the list of applications that already have grants (Microsoft's documentation on [reviewing permissions granted to applications](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/manage-application-permissions) is one worked example; every IdP has an equivalent).
- **Leaver automation**: HR status drives the account (SCIM or a scripted deprovision), and the leaver checklist also revokes sessions and tokens, and removes keys that do not go through the IdP. A scheduled query like `review.py` section 3, run weekly, catches the account that slipped.
- **Access reviews**: someone who knows the job reads the "who has what" report on a schedule (quarterly is a common cadence, est.), and the privileged groups get the most frequent review. Remove access you cannot explain.
- **Alert on the change, not only on the sign-in**: additions to privileged groups, new application consents, and sign-ins by disabled or departed accounts.

**Flip the board.** Two short exercises, on paper. (1) You are the attacker with one stolen laptop session of a mid-level engineer. List what you can reach in the fake company, using `review.py` section 1 as your map. Which single group membership would you want to add next, and which log line would give you away? (2) You are the defender and may buy only one control this quarter: phishing-resistant MFA for admins, a weekly leaver query, or admin consent for applications. Which attack in the Evade list does each one close, and which does it leave open? There is no single right answer; the habit is to name what remains.

**Undo.** Delete `~/idlab` as in Exercise 5, and stop the Keycloak container if you started it (teardown above).

## Common mistakes

| Symptom or mistake | What is going on | What to check |
|---|---|---|
| "SAML sign-in loops back to the IdP" | The application rejected the assertion and restarted the flow. | Clock skew (the time window), the audience, the ACS address, the certificate in the metadata. |
| `invalid redirect_uri` from the IdP | The address in the request is not exactly one the client registered. | A trailing slash, `http` versus `https`, a different port; the match is meant to be strict. |
| The token has no `groups` claim | The IdP only includes what is configured. | The mapper or attribute release for that application. |
| A removed user still has access | A token or session outlived the change, or a local account exists. | Token lifetime, session revocation, accounts outside the IdP. |
| Using the email address as the account key | Emails change and can be reused. | Key the account on `sub` (OIDC) or a stable `NameID` (SAML). |
| Treating `aud` and `iss` as optional | The token is believed from anywhere. | Both are required checks; a library does them if configured. |
| "We have MFA" as the whole answer | Some MFA is phishable. | Which factor, and what happens when a person loses it. |
| Pasting a real token into an online decoder | The decoder's owner now holds your credential. | Decode locally, as Exercise 4 shows. |

## Checkpoint

You are done when you can say, without looking:

- The three questions of AAA, and which one a `403` and a sign-in log each belong to.
- What a directory, an IdP and SSO each are, and why applications never see your password.
- The eight steps of a SAML sign-in, and which six things the application must check in the assertion.
- Why OAuth is not a sign-in protocol, and what OIDC adds (the `openid` scope and the ID token).
- What `state`, `nonce`, `redirect_uri` and the PKCE verifier each stop.
- Why a FIDO2/WebAuthn sign-in resists phishing (origin binding) and a typed code does not, and why that is not the same as being theft-proof.
- Joiner, mover and leaver, and why disabling the IdP account is not the whole of offboarding.
- How the ZTNA product in this project uses the IdP, and what changes when the plan allows a different kind of sign-in.

## Claims register

All read-only requests; retrieved **2026-10-21** unless stated.

| Claim | Source | Status |
|---|---|---|
| SAML assertions carry `Conditions` with `NotBefore` and `NotOnOrAfter`, an `AudienceRestriction`, and `SubjectConfirmationData` with `InResponseTo`; the HTTP Redirect and HTTP POST bindings exist | [SAML 2.0 Core](https://docs.oasis-open.org/security/saml/v2.0/saml-core-2.0-os.pdf) and [SAML 2.0 Bindings](https://docs.oasis-open.org/security/saml/v2.0/saml-bindings-2.0-os.pdf) | Read (element and binding names found in the text). The eight-step narrative is a summary, not a quote |
| The authorization code grant is redirect-based and used to obtain access and refresh tokens | [RFC 6749, section 4.1](https://www.rfc-editor.org/rfc/rfc6749) | Read |
| PKCE mitigates authorization code interception for public clients | [RFC 7636](https://www.rfc-editor.org/rfc/rfc7636) abstract | Read |
| RFC 9700 is the OAuth 2.0 security best current practice (that it recommends PKCE for the code flow) | [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700) | Title and status read; the PKCE recommendation is **est.** (general knowledge, not re-found in the text) |
| ID token claims: `iss` (https URL of the issuer), `aud` MUST contain the client's `client_id`, `exp` is the time on or after which it MUST NOT be accepted, `nonce` ties a client session to a token and mitigates replay; the client MUST validate the signature | [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html) | Read |
| A JWT is a compact, URL-safe way to represent claims, as the payload of a JWS or JWE | [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519) abstract | Read |
| SCIM is an HTTP-based protocol for managing identities across domains | [RFC 7644](https://www.rfc-editor.org/rfc/rfc7644) abstract (data model: [RFC 7643](https://www.rfc-editor.org/rfc/rfc7643)) | Read (RFC 7643 reachable; not searched) |
| WebAuthn credentials are "scoped to a given WebAuthn Relying Party"; authenticators can be roaming or platform | [W3C WebAuthn Level 3](https://www.w3.org/TR/webauthn-3/); [CISA, Implementing phishing-resistant MFA](https://www.cisa.gov/sites/default/files/publications/fact-sheet-implementing-phishing-resistant-mfa-508c.pdf) | Read. The CISA fact sheet names FIDO/WebAuthn (roaming and platform authenticators) and PKI-based authentication; this page does not repeat its stronger wording about other options. That synced passkeys trade some protection for recovery is **est.** |
| Keycloak Docker quick start: `docker run -p 127.0.0.1:8080:8080` with `KC_BOOTSTRAP_ADMIN_USERNAME` / `KC_BOOTSTRAP_ADMIN_PASSWORD` and `quay.io/keycloak/keycloak:26.8.1 start-dev`; realms, users, clients with *Standard flow*, *Valid redirect URIs*; advice to move to a production database, TLS and a stronger admin password | [Keycloak: Getting started with Docker](https://www.keycloak.org/getting-started/getting-started-docker) | Read; never run |
| Keycloak OIDC discovery path `/realms/{realm-name}/.well-known/openid-configuration` | [Keycloak: OIDC layers](https://www.keycloak.org/securing-apps/oidc-layers) | Read |
| Keycloak SAML IdP descriptor at `/realms/{realm-name}/protocol/saml/descriptor` | [Keycloak Server Administration Guide](https://www.keycloak.org/docs/latest/server_admin/index.html) | Read |
| Publishing a container port on `127.0.0.1` only; without an address Docker publishes on all interfaces | [docker container run reference](https://docs.docker.com/reference/cli/docker/container/run/) | Read |
| `-e NAME` with no value passes the host's value of that variable | Docker documentation | **est.**; not re-read for this page |
| Python's XML modules can be vulnerable to attacks such as "billion laughs" depending on the bundled or system Expat version | [Python: XML vulnerabilities](https://docs.python.org/3/library/xml.html) | Read |
| Microsoft publishes guidance for reviewing the permissions granted to applications | [Microsoft Entra: manage application permissions](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/manage-application-permissions) | Page read in part; consent phishing as a pattern is described here in the author's words (**est.**, general knowledge) |
| Sign-in to the ZTNA product is delegated to an IdP; free-plan sign-in uses a social login; directory integrations are listed as features of higher plans | [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md); [Build it from zero](Build-It-From-Zero-Accounts-to-Stage-1.md) (checked 2026-10-19 by that page) | Repository pages, not re-checked here |
| The maintainer's lab signs in through an IdP using SAML, and SAML sign-in is not on the free plan of the ZTNA product | The maintainer, stated to the author | Not verified against the vendor; no plan name, tier or price is given on this page. Check the vendor's pricing and documentation pages on the day |
| Social login is OIDC underneath | General knowledge | **est.**; depends on the provider |
| Token lifetime numbers (900 seconds in the lab), quarterly review cadence, how long a sensible session is | Invented for the exercise / common practice | **est.**; not a standard |
| The Python scripts' output | Run on Linux with Python 3.13, 2026-10-21 | Observed; times change on every run. `oidc_login.py` tested only against a stand-in server |

Not verified, plainly: the whole PowerShell track; macOS and Windows behavior of the scripts (including the `0o600` file mode, which Windows ignores); the entire Keycloak path from container start to a real sign-in; the console menu names and the token-mapper steps; the Docker `-e NAME` pass-through; whether any vendor's plan includes a given sign-in method.

Next: [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md), then core step 11 on the [Reading order](Reading-Order.md) page, [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md).
