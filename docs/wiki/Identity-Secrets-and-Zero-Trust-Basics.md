# Identity, secrets and zero trust basics

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

Start-from-zero page 3 of 8. Previous: [Networking basics](Networking-Basics-for-This-Project.md). Next: [What is infrastructure as code](What-Is-Infrastructure-as-Code.md).

Most real-world breaches are not clever. Someone found a password, a token or a key that should have been private, and used it. This page is about what those things are, why they leak, and the handful of habits that stop them leaking. It ends with what "zero trust" means once you take the marketing off.

## Authentication and authorization are two different questions

**Authentication** asks "who are you?" and checks the answer: a password, a code from your phone, a key.

**Authorization** asks "what is this person allowed to do?" and checks that against a policy.

A system can get the first right and the second badly wrong. The classic VPN failure is exactly that: strong authentication at the door, and then once inside, authorization is "whatever the network lets you reach", which is usually far too much. Keep the two apart in your head and a lot of security design becomes obvious.

## What a secret is

A **secret** is any string that lets its holder do something: log in, call an [API](APIs-and-Tokens-From-Zero.md), decrypt data. If API, token, scope or JWT are new words, read [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) first. The common kinds:

| Kind | What it is | Looks like | In this project |
|---|---|---|---|
| **Password** | Something you know and type | `correct horse battery staple` | The DigitalOcean, Twingate, Spacelift and Doppler account logins. Never on a droplet: no account there has a password at all. |
| **API token** (or API key) | A long random string that authenticates a program to a service | `dop_v1_a8f3...`, `dop_` plus 40 characters | The DigitalOcean token that lets OpenTofu create machines; the Twingate token; the Doppler token |
| **SSH key pair** | Two linked files: a **private key** you keep, and a **public key** you give out | `ssh-ed25519 AAAAC3...` for the public half | The admin key that lets the author log in to a connector |
| **Service account token** | A token for a program rather than a person, usually narrow | | The connector tokens that let each droplet identify itself to Twingate |

A token is just as good as a password and often better for an attacker: it does not go through MFA, it is rarely rotated, and it is usually copied around between files, chat windows and terminals. Treat every token as if it were the account's password, because for a program it is.

## How keys work, without the math

A key pair is two numbers with a special relationship. You keep one (the **private key**) and publish the other (the **public key**). With the private key you can make a **signature** over any piece of data; with the public key, anyone can check that signature, but nobody can make a new one.

When you SSH to a machine that has your public key, your client signs a piece of data that is unique to this one connection (it is tied to the session the two sides just set up, so it is useless anywhere else). The server checks the signature against your public key. If it checks out, only the holder of the private key could have made it, so the server knows it is you. Your private key never left your laptop, nothing reusable went over the wire, and there is nothing on the server worth stealing (a public key is public). Some older explanations describe this as the server encrypting a challenge for you to decrypt; modern SSH keys such as ed25519 sign rather than decrypt.

Compare that to a password, which goes over the wire every time, can be guessed, can be reused from another site's breach, and is only as strong as the person who chose it. This is why the droplets here accept keys only: there is no password to guess, so the endless password-guessing traffic that hits every internet-facing SSH server has nothing to work with.

Practical rules for your own keys:

- Use `ssh-keygen -t ed25519`. One key per device you type on, not one key shared everywhere.
- Protect the private key with a passphrase. A stolen laptop should not mean a stolen key.
- The public key's comment field (the bit after the key) usually contains your username and machine name. Strip it before putting the key anywhere public or anywhere it ends up in a log. This repo does exactly that, because the key goes into the droplet's first-boot configuration.

## Why secrets leak

Almost never by being cracked. Usually:

- **Committed to a git repository.** A `.env` file, a config with a token in it, a script with a hardcoded password. Even if deleted in the next commit, it is in the history forever and automated bots scan GitHub for exactly these patterns within minutes of a push.
- **Pasted into chat, a ticket or a screenshot.** The terminal screenshot with the token visible in the command line.
- **Printed in a log.** A build job that echoes its environment; an error message that includes the request headers.
- **Left in shell history.** `export TOKEN=...` typed at the prompt is saved to `~/.bash_history`.
- **Stored somewhere readable on the machine.** A world-readable config file; a token in cloud-init user-data that any process on the VM can read from the metadata endpoint. This project has exactly that last problem with the connector tokens, says so in the [Threat model](Threat-Model.md), and lists the fix as a follow-up rather than pretending.
- **Never rotated.** A token from 2021 that still works means every leak since 2021 still works too.

Every control in this project's secrets design is aimed at one of those bullets.

## The fix: a secrets manager, and the discipline around it

A **secrets manager** is a service whose only job is to hold secrets. Programs fetch what they need at run time, by name, with a token that can only read. Nothing is written into a file in the repository, ever.

This project uses Doppler. The rules it applies:

| Rule | Which leak it stops |
|---|---|
| **Nothing in the repository is a credential.** Not a token, not a tenant name, not an account id. The repo was public from the first commit so that nothing could ever be committed "temporarily". | Committed secrets |
| **Secrets are fetched by name, only during a real run on the main branch.** A pull request's plan gets nothing. | A malicious pull request printing the token |
| **Every fetched value is masked in the run logs**, and the first real run checked that the mask actually worked. | Printed in a log |
| **Secrets are set with a prompt, not on the command line.** `doppler secrets set NAME` asks for the value. | Shell history |
| **One read-only token for the whole pipeline**, scoped to one project and one environment, expiring every 90 days. | Never rotated, and blast radius if it does leak |
| **Expiry dates in a password manager**, rotation steps written down. | Never rotated |

The full picture, including where a secret still ends up outside Doppler and what is done about it, is on [Doppler and secrets](Doppler-and-Secrets.md). The honest table there is worth more than the diagram.

## Least privilege

Give every person and every program the smallest set of permissions that lets it do its job, and nothing more. It sounds obvious and is constantly ignored because "admin" is easier.

In this project: the DigitalOcean token used to build the environment has a custom list of scopes, not full access, and a run that failed with `403 You are not authorized` because a scope was missing is recorded on [Lessons learned](Lessons-Learned.md) as the right kind of failure. The Doppler token can read one environment and cannot write. The stage 0 stack receives only the DigitalOcean token; only stage 1 receives the Twingate token. The CI robots have no cloud credentials at all. Each of those is least privilege applied one layer at a time.

## MFA and identity providers

**MFA** (multi-factor authentication) means a second proof beyond the password: a code from an app, a hardware key, a prompt on your phone. It turns "I found your password" into "I found your password and it is useless". Turn it on for every cloud account before you do anything else. Prefer an authenticator app or a hardware key over SMS.

An **identity provider** (IdP) is the one service that does your logins for everything else. Google, Microsoft, Okta and others play this role; "Sign in with Google" is an IdP at work. The value is that MFA policy, password policy and "this person has left" live in one place. Twingate in this project does not have its own passwords; it hands sign-in to an identity provider, so MFA is enforced there, once.

## Zero trust, with the marketing removed

The old model is a castle: a hard wall (the firewall, the VPN) and a soft inside where everything trusts everything because "we are on the corporate network". Every breach that starts with one phished laptop and ends with the whole company encrypted is that model failing.

**Zero trust** is a design rule, not a product: **never grant access because of where a request comes from. Grant it because of who is asking, what they are asking for, and whether policy allows exactly that.** Every request, every time.

In practice that means:

- No "you are on the network, so you can reach everything". Access is per resource (this host, this port).
- Identity is checked by an identity provider with MFA, not by a shared password.
- Being inside the private network grants nothing on its own; the firewall filters traffic between machines too.
- Each thing a program holds (a token, a key) is as narrow as possible, so a compromised program cannot do much.
- Everything is logged per person per resource, so "who touched what" has an answer.

[Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) is the long argument with the incident reports. [NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final) is the reference definition, and that page maps it line by line onto this repository.

One honest note: zero trust shifts trust, it does not remove it. This project trusts Twingate's control plane, Spacelift, Doppler and DigitalOcean. The [Threat model](Threat-Model.md) names each of those as an accepted risk, which is what you are supposed to do with trust you cannot eliminate.

## Where this shows up in the repo

| Idea | Where |
|---|---|
| Keys only, no passwords, one user, root disabled | `modules/twingate-bootstrap/cloud-init.yaml.tftpl`, explained on [Droplet hardening](Droplet-Hardening.md) |
| Secrets fetched by name only on real runs, masked | `scripts/spacelift/doppler-env.sh` and `.spacelift/config.yml`, explained on [Doppler and secrets](Doppler-and-Secrets.md) |
| Which stack receives which secret | `.spacelift/config.yml` |
| Per-host, per-port access | The `twingate_resource` blocks in `stacks/10-access/main.tf`: one address, TCP port 22, nothing else |
| The admin group, as code | `twingate_group.admins` in the same file, with a check that refuses an empty member list |
| What is accepted and why | The accepted-risks list on [Threat model](Threat-Model.md) |

## Try it yourself

- Turn on MFA for your GitHub account and your email, today, if you have not.
- Make an SSH key with `ssh-keygen -t ed25519 -C ""` (the empty `-C` gives it no comment) and look at the two files it made. Open the `.pub` one; that is the half you may share. Never open the other one in anything that leaves your machine.
- Search your own public repositories for the strings `password`, `token` and `secret`. If you find one, rotate it first, then remove it; removing it from git does not remove it from history or from the bots that already copied it.

Next: [What is infrastructure as code](What-Is-Infrastructure-as-Code.md).
