# Security policy

Clouds Against Humanity is a teaching repository: OpenTofu code, a wiki of lessons, tests and scripts. It is not a hosted service and it runs nothing for you.

## What is in scope

- The code and configuration in this repository (stacks, modules, scripts, workflows).
- A lesson that would lead a reader into an unsafe state, such as a command that opens a port, exposes a secret or weakens a firewall.
- A secret, token or personal identifier that was committed by mistake.

Out of scope: problems in the vendors' own products (DigitalOcean, Twingate, Spacelift, Doppler, GitHub and the others). Report those to the vendor.

## Supported versions

Only the current `main` branch is maintained. There are no release branches.

## How to report privately

Please do not open a public issue for a vulnerability or an exposed secret.

1. Open the repository's **Security** tab and choose **Report a vulnerability** to use GitHub's private vulnerability reporting.
2. If that button is not there, open a public issue that says only that you have a security report and asks for a private way to send it. Put no details in it.

## What to include

- Where it is: the file and line, or the wiki page and step.
- What you think the impact is, in a sentence or two.
- Steps to reproduce, using placeholders.

## What never to include

Do not send real tokens, API keys, passwords, account or tenant names, real IP addresses or hostnames, or anything from a real console that identifies you. If you found a live secret in the repository, say where it is, but do not paste it. The maintainer will rotate it.

This is one person's open-source education project, so replies come in evenings and weekends and I cannot promise a response time.

General feedback, wrong commands and questions are welcome as ordinary issues: see [Give feedback and open an issue](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/wiki/Give-Feedback-and-Open-an-Issue).
