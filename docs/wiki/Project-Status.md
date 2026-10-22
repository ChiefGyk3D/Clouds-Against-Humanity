<!-- GENERATED from docs/wiki/.status-snapshot.json by scripts/gen_project_status.py. Do not
edit this page by hand: the snapshot is refreshed from the maintainer's GitHub login with
`python -I scripts/gen_project_status.py --refresh`. CI fails when this page does not match
the snapshot. -->

# Project status: where we are

> Prerequisites: [How this project is planned](How-This-Project-Is-Planned.md), because it explains the board, sprints and sizes this page counts.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

This page is regenerated from GitHub's own issues, pull requests and project board, not from memory. It is a reference page, not a lesson. A refresh saves a snapshot of what GitHub said at one moment, and everything below is counted and listed by code from that snapshot.

**Generated at:** 2026-10-22T23:06:29Z (UTC), from `ChiefGyk3D/Clouds-Against-Humanity` and the maintainer's project board. This is a snapshot: GitHub may have moved since.

> **Board data may lag.** The board holds 71 items and the repository has 94 issues, so 23 issues are not visible on the board. GitHub Projects had an incident on 2026-10-22 that delayed newly added items; the board lists below can undercount until they appear.

## The counts

| What | Count |
|---|---|
| Issues, all states | 94 |
| Open issues | 64 |
| Open issues in flight | 4 |
| Open issues with a merged PR, to review for close | 14 |
| Open issues that need the maintainer | 18 |
| Open issues not started | 28 |
| Open pull requests | 4 |
| Merged pull requests | 159 |
| Items on the board (all repositories) | 71 |
| Issues not visible on the board | 23 |
| Pull requests not visible on the board | 166 |
| Closed issues not Done on the board | 9 |

## How each open issue is classified

The rules are the ones the 2026-10-22 audit used, applied in this order. Only an issue that is open is classified.

1. **In flight:** an open pull request mentions the issue with `Closes`, `Fixes`, `Resolves` or `Refs` followed by `#N`.
2. **Has merged PR:** no open pull request, but a merged one mentions it the same way. This is a candidate to review for closing. **A `Refs` link is not proof the work is done**: it only says the pull request touched the issue, so each row says whether the link was a closing word or `refs only`.
3. **Needs the maintainer:** neither of the above, and the issue has the `needs-maintainer` label.
4. **Not started:** none of the above.

A pull request closed without merging counts for nothing. A reference into another repository is ignored. Linking is by keyword in the pull request body; a number in a title or a branch name is not a link.

## Open issues by state

### In flight (4)

An open pull request mentions each of these.

| Issue | Title | Board status | Size | Sprint | Linked PRs |
|---|---|---|---|---|---|
| [#122](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/122) | DMZ stack implementation | Backlog | XL | S 6 | [#206](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/206) (refs only) |
| [#229](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/229) | Network and host defense track: packet filters, IDS/IPS, file integrity and alerting, rate limiting at every layer | not on board | not on board | not on board | [#234](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/234) (refs only) |
| [#243](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/243) | Cross-tenant data flows, data governance and retention, and email and network DLP | not on board | not on board | not on board | [#258](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/258) (closes) |
| [#246](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/246) | Plan policy: allowlists keyed by stack id plus resource address, with per-entry direction, ports and source or destination scope | not on board | not on board | not on board | [#252](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/252) (closes) |

### Has merged PR: review for close (14)

A merged pull request mentions each of these and the issue is still open. Check the work against the issue before closing; a `refs only` link is not proof of done.

| Issue | Title | Board status | Size | Sprint | Linked PRs |
|---|---|---|---|---|---|
| [#22](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/22) | AWS, Azure, and GCP Lessons | Backlog | XL | S 7 | [#24](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/24) (refs only) |
| [#70](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/70) | Epic: stage 2 telemetry | Backlog |  |  | [#146](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/146) (refs only), [#151](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/151) (refs only), [#154](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/154) (refs only) |
| [#79](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/79) | Verify the Twingate plan limit on service accounts | Next | S | S 2 | [#167](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/167) (refs only) |
| [#93](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/93) | Optional: upgrade the Twingate provider from 3.x to 4.x or 5.x | Backlog | M | S 2 | [#173](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/173) (refs only) |
| [#95](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/95) | Audit logging on the droplets | Backlog | M | S 3 | [#151](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/151) (refs only) |
| [#96](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/96) | Create the private spacelift-stack-factory repository and adopt cah-00 by import | Backlog | L | S 3 | [#181](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/181) (refs only) |
| [#102](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/102) | Wazuh agents push droplet logs home over a second service account | Backlog | L | S 4 | [#151](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/151) (refs only) |
| [#106](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/106) | Stage 2 guide: verification section and wiki update | Backlog | M | S 2 | [#145](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/145) (refs only), [#157](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/157) (refs only), [#160](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/160) (refs only), [#174](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/174) (refs only), [#180](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/180) (refs only) |
| [#178](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/178) | Honeypots/HoneyNet | In progress | XL | S 1 | [#182](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/182) (refs only), [#194](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/194) (refs only) |
| [#214](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/214) | Mirror the Hammunition board layout and backfill every shipped and planned item (no hidden work) | not on board | not on board | not on board | [#215](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/215) (refs only), [#216](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/216) (refs only), [#217](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/217) (refs only), [#218](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/218) (refs only), [#219](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/219) (refs only), [#220](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/220) (refs only), [#222](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/222) (refs only), [#223](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/223) (refs only) |
| [#221](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/221) | Security tools basics track: red and blue as yin and yang, Kali versus Parrot, Nmap, OpenVAS, Burp CE, Metasploit (basics only) | not on board | not on board | not on board | [#224](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/224) (refs only), [#225](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/225) (refs only) |
| [#226](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/226) | Verify every lesson end to end: local exercises, then Spacelift scratch stacks, then optional cloud tiers, each torn down | not on board | not on board | not on board | [#233](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/233) (refs only) |
| [#230](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/230) | Explain security through obscurity honestly, and audit every page that suggests changing a port | not on board | not on board | not on board | [#231](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/231) (refs only) |
| [#232](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/232) | First hour on a new system: updates, automatic updates and a baseline before anything else, on every OS | not on board | not on board | not on board | [#237](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/237) (refs only) |

### Needs the maintainer (18)

Labeled `needs-maintainer`, with no pull request mentioning it.

| Issue | Title | Board status | Size | Sprint |
|---|---|---|---|---|
| [#76](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/76) | Check whether Spacelift's AWS integration is on the current plan | Blocked | S | S 1 |
| [#77](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/77) | Unlock the stacks and read the first tracked plans | Blocked | M | S 1 |
| [#78](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/78) | Confirm the Twingate API key expiry and put every secret expiry on a calendar | Blocked | S | S 1 |
| [#81](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/81) | Skim the live wiki: images render, diagrams are readable, Reading Order works | Blocked | S | S 2 |
| [#82](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/82) | Review the per-phase cost ceilings in docs/stages/approved.json | Next | S | S 3 |
| [#83](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/83) | Verify and delete unused Doppler secrets | Next | S | S 3 |
| [#84](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/84) | Rotate the DigitalOcean and Doppler tokens before 2027-01-08 | Next | S | S 6 |
| [#86](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/86) | Attach the Spacelift push policy once the plan allows it | Backlog | M | S 6 |
| [#94](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/94) | First-run checks: log masking and the runner image | Next | S | S 6 |
| [#97](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/97) | Home side: connector VLAN and firewall allow-list with a negative reachability test | Next | M | S 6 |
| [#98](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/98) | Create the cah-20-telemetry Spacelift stack, locked, with the cah label | Next | S | S 7 |
| [#105](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/105) | Confirm end to end, then add notes to siem-docker-stack | Backlog | S | S 3 |
| [#108](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/108) | Decide the Discord-to-Matrix bridge: self-host mautrix-discord or use etke.cc's | Backlog | S | S 4 |
| [#109](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/109) | Approve the stage 3 cost and make stage-3 the current phase | Backlog | S | S 3 |
| [#123](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/123) | Throwaway AWS account (root MFA, budget first) and one real apply | Backlog | L | S 5 |
| [#124](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/124) | Recruit Azure and GCP reviewers for the lessons | Backlog | S | S 6 |
| [#133](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/133) | Keep the board current: a scheduled safo reconcile from the maintainer's login | Next | S | S 2 |
| [#134](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/134) | Sprint 1 review and re-plan | Next | S | S 1 |

### Not started (28)

Open, no pull request mentions it, no maintainer label.

| Issue | Title | Board status | Size | Sprint |
|---|---|---|---|---|
| [#68](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/68) | Epic: operations and gates | Next |  |  |
| [#69](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/69) | Epic: stage 1 hardening | Next |  |  |
| [#71](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/71) | Epic: stage 3 workloads | Backlog |  |  |
| [#72](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/72) | Epic: edge and DMZ | Backlog |  |  |
| [#73](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/73) | Epic: multi-cloud | Backlog |  |  |
| [#74](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/74) | Epic: learning and wiki | Backlog |  |  |
| [#75](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/75) | Epic: process | Next |  |  |
| [#85](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/85) | Update the pinned Twingate apt signing key fingerprint before it expires | Blocked | S | S 7 |
| [#100](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/100) | Enable connector telemetry one connector at a time | Next | M | S 7 |
| [#101](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/101) | Prometheus scrapes the cloud connectors through a headless Twingate client | Next | L | S 8 |
| [#111](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/111) | Workload stack: droplet, firewall and Twingate resources | Backlog | L | S 4 |
| [#112](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/112) | Portainer CE: hardening and a check of git-stack behaviour | Backlog | M | S 4 |
| [#113](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/113) | Spaces bucket with versioning and the state backend for the daemons | Backlog | L | S 3 |
| [#114](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/114) | Cloud-optimized install for the five daemons (run-once mode, bucket state) | Backlog | XL | S 5 |
| [#115](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/115) | Functions for the timer jobs (penguin-overlord runners, solarstorm_scout) | Backlog | L | S 5 |
| [#116](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/116) | mautrix-discord with Postgres and a nightly dump to the bucket, restore tested | Backlog | XL | S 6 |
| [#125](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/125) | Azure modules and stacks with mocked tests | Backlog | XL | S 7 |
| [#126](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/126) | GCP modules and stacks with mocked tests | Backlog | XL | S 8 |
| [#127](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/127) | Move the stage 3 timer jobs to AWS Lambda with scheduled triggers | Backlog | L | S 7 |
| [#196](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/196) | Check the DigitalOcean firewall docs: deny rules and rule precedence | not on board | not on board | not on board |
| [#235](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/235) | Switch the cloud-init auditd rules from the deprecated -w form to -a rules (and regenerate the golden hashes) | not on board | not on board | not on board |
| [#247](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/247) | Rework the DMZ draft (#206) to the eleven DMZ rulings | not on board | not on board | not on board |
| [#248](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/248) | Verify Droplet Console and root password behavior on a throwaway droplet before the first edge droplet | not on board | not on board | not on board |
| [#249](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/249) | Wiki navigation: reorganize the sidebar, add a dedicated Contents page, and clean up | not on board | not on board | not on board |
| [#253](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/253) | Plan policy: evaluate outbound firewall rules (world-open egress) once the firewall module is address-aware | not on board | not on board | not on board |
| [#254](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/254) | Remove the self-hosted Discord-to-Matrix bridge from the stage 3 plan (etke.cc hosts it) | not on board | not on board | not on board |
| [#259](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/259) | Project status page: one wiki page regenerated from SAFO's audit, so where we are is always visible | not on board | not on board | not on board |
| [#260](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/260) | Sweep every lab and lesson snippet for predictable shared temp paths and unsafe pid or kill handling | not on board | not on board | not on board |

## Open pull requests (4)

| Pull request | Title | Draft | CI | Review | Linked issues |
|---|---|---|---|---|---|
| [#206](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/206) | feat: DMZ edge stack and edge-host module, flag off (#122) | draft | failing | none | [#122](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/122) (refs only) |
| [#234](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/234) | docs: lesson D3, file integrity and alerting (Tripwire, AIDE, Wazuh, auditd, fail2ban) | ready | failing | none | [#229](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/229) (refs only) |
| [#252](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/252) | feat: plan policy allowlists keyed by stack id and resource, with per-entry scope (#246) | ready | pending | none | [#246](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/246) (closes) |
| [#258](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/258) | docs: lesson, cross-tenant data flows, data governance and retention, and DLP | ready | pending | none | [#243](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/243) (closes) |

## Board gaps

These come from the project board's items, read through GitHub's GraphQL API. See the lag note at the top when the numbers look low.

### Issues missing from the board (23)

| Issue | State | Title |
|---|---|---|
| [#196](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/196) | open | Check the DigitalOcean firewall docs: deny rules and rule precedence |
| [#214](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/214) | open | Mirror the Hammunition board layout and backfill every shipped and planned item (no hidden work) |
| [#221](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/221) | open | Security tools basics track: red and blue as yin and yang, Kali versus Parrot, Nmap, OpenVAS, Burp CE, Metasploit (basics only) |
| [#226](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/226) | open | Verify every lesson end to end: local exercises, then Spacelift scratch stacks, then optional cloud tiers, each torn down |
| [#227](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/227) | closed | Start Here: say plainly that gaps are deliberate and AI is a tool, not a crutch |
| [#229](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/229) | open | Network and host defense track: packet filters, IDS/IPS, file integrity and alerting, rate limiting at every layer |
| [#230](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/230) | open | Explain security through obscurity honestly, and audit every page that suggests changing a port |
| [#232](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/232) | open | First hour on a new system: updates, automatic updates and a baseline before anything else, on every OS |
| [#235](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/235) | open | Switch the cloud-init auditd rules from the deprecated -w form to -a rules (and regenerate the golden hashes) |
| [#236](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/236) | closed | Secrets from day one: password manager, Doppler for every asset, .env rules, scanning and leak response |
| [#239](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/239) | closed | Behind a CDN: real client IPs, why an IP is a weak identifier, OSI basics, and links to the on-prem SIEM stacks |
| [#241](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/241) | closed | Flaky test: test_proxy_forwards_loopback_and_refuses_everything_else in the S2 lesson tests |
| [#243](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/243) | open | Cross-tenant data flows, data governance and retention, and email and network DLP |
| [#245](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/245) | closed | Firewall module: address-aware extra outbound rules (prerequisite for the edge iperf3 egress rule) |
| [#246](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/246) | open | Plan policy: allowlists keyed by stack id plus resource address, with per-entry direction, ports and source or destination scope |
| [#247](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/247) | open | Rework the DMZ draft (#206) to the eleven DMZ rulings |
| [#248](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/248) | open | Verify Droplet Console and root password behavior on a throwaway droplet before the first edge droplet |
| [#249](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/249) | open | Wiki navigation: reorganize the sidebar, add a dedicated Contents page, and clean up |
| [#250](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/250) | closed | Cost gate: skip labs/ for the resource-type allowlist, still check syntax (option L1) |
| [#253](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/253) | open | Plan policy: evaluate outbound firewall rules (world-open egress) once the firewall module is address-aware |
| [#254](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/254) | open | Remove the self-hosted Discord-to-Matrix bridge from the stage 3 plan (etke.cc hosts it) |
| [#259](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/259) | open | Project status page: one wiki page regenerated from SAFO's audit, so where we are is always visible |
| [#260](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/260) | open | Sweep every lab and lesson snippet for predictable shared temp paths and unsafe pid or kill handling |

### Pull requests missing from the board (166)

| Pull request | State | Title |
|---|---|---|
| [#1](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/1) | merged | feat: load Doppler secrets into Spacelift runs |
| [#2](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/2) | merged | docs: state where the secrets trust boundary actually is |
| [#3](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/3) | merged | feat: two Twingate connectors sharing one site |
| [#4](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/4) | merged | fix: reuse the existing SSH key; harden the connector droplets |
| [#5](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/5) | merged | fix: retry the connector install, open outbound UDP, run on Eastern time |
| [#6](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/6) | merged | fix: install the connector the way Twingate's own Terraform does |
| [#7](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/7) | merged | fix: let the connectors reach each other's SSH inside the VPC |
| [#8](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/8) | merged | fix: let each connector open SSH to the other (outbound rule) |
| [#9](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/9) | merged | docs: wiki with flowcharts, component rationale, and why ZTNA instead of a VPN |
| [#10](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/10) | merged | docs: stage 3 design draft, workload host with Portainer, daemons and Matrix bridge |
| [#11](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/11) | merged | docs: exact DigitalOcean token scopes (Token A and B) |
| [#12](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/12) | merged | docs: wiki Terraform reference explaining every declaration |
| [#13](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/13) | closed | fix: use s-1vcpu-1gb-intel for the connectors |
| [#14](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/14) | merged | fix: move the environment to Toronto (tor1) |
| [#15](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/15) | merged | fix: use 10.78.0.0/24 for the Toronto VPC |
| [#16](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/16) | merged | docs: lessons from the account redeploy |
| [#17](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/17) | merged | docs: stage 3 draft, self-hosted mautrix-discord (Go) bridge, backups, etke.cc alternative |
| [#18](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/18) | merged | Stage 2 design: logging, metrics and the link home (draft) |
| [#19](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/19) | merged | docs: start-from-zero wiki track; Spacelift push policy; CI and wiki publishing on GYST only |
| [#20](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/20) | merged | docs: add edge DMZ handoff to the plans and the roadmap |
| [#23](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/23) | merged | docs(wiki): fork, private stacks and the pipeline (capstone page) |
| [#24](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/24) | merged | docs: multi-cloud design for AWS, Azure and GCP (#22) |
| [#25](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/25) | merged | docs(wiki): enterprise landscape and detection (Wazuh) lessons |
| [#26](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/26) | merged | docs: address Copilot review of the multi-cloud design (#24 follow-up) |
| [#27](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/27) | merged | docs(wiki): labs, build-it track, and path-based navigation |
| [#28](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/28) | merged | docs(wiki): one home for the push-policy caveat, Wazuh lesson fixes, heading links |
| [#29](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/29) | merged | docs: record the maintainer's multi-cloud decisions (#22) |
| [#30](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/30) | merged | docs: multi-cloud phase 0 findings and evidence (#22) |
| [#31](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/31) | merged | docs(wiki): AWS lessons for phase 1 (#22) |
| [#32](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/32) | merged | refactor(modules): shared Twingate bootstrap module (phase 2a of #22) |
| [#33](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/33) | merged | feat(modules): the provider module contract (phase 2b of #22) |
| [#34](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/34) | merged | feat(cost-gate): price more than one cloud (phase 2c-i of #22) |
| [#35](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/35) | merged | feat(ci): identifier check for cloud account ids (phase 2c-ii of #22) |
| [#36](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/36) | merged | docs(design): stage 2 settings layer and mini cloud SOC |
| [#37](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/37) | merged | docs(wiki): threat-model exercise and a traced change |
| [#38](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/38) | merged | docs(wiki): glossary links and a troubleshooting index |
| [#39](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/39) | merged | test(secrets): per-cloud secret separation (phase 2c-iii of #22) |
| [#40](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/40) | merged | docs(wiki): link the threat-model exercise and the traced change |
| [#41](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/41) | merged | fix(cost-gate): close parser-differential bypasses found in review |
| [#42](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/42) | merged | docs(wiki): OWASP Threat Dragon exercise for trust boundaries |
| [#43](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/43) | merged | docs(wiki): GCP lessons, unverified drafts (#22) |
| [#44](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/44) | merged | docs(wiki): Azure lessons, unverified drafts (#22) |
| [#45](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/45) | merged | feat(aws): vpc, firewall and connector modules (phase 3a of #22) |
| [#46](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/46) | merged | docs(wiki): Threat Dragon exercise fixes from review |
| [#47](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/47) | merged | docs: correct the proposed-run credential claim in the secrets runbook |
| [#48](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/48) | merged | feat(cost-gate): stack instances for multi-site (step 2b of the stage 2 design) |
| [#49](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/49) | merged | feat(settings): settings manifest, ignore rules and generated reference (step 1 of the stage 2 design) |
| [#50](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/50) | merged | docs(wiki): reading order and navigation |
| [#51](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/51) | merged | feat(aws): foundation and access stacks (phase 3b of #22) |
| [#52](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/52) | merged | docs(wiki): threat frameworks (STRIDE, ATT&CK, ATLAS) with importable Threat Dragon models |
| [#53](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/53) | merged | feat(settings): variables, examples and immutable keys (step 2 of the stage 2 design) |
| [#54](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/54) | merged | feat(firewall): tag-sourced rules from other tags (additive, step 4.2 of the stage 2 design) |
| [#55](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/55) | merged | feat(settings): timezone variable with a byte-identical default (step 3 of the stage 2 design) |
| [#56](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/56) | merged | docs(wiki): cloud telemetry, multiple sites and a mini SOC (lessons, drafts) |
| [#57](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/57) | merged | feat(telemetry): stack 20 skeleton, everything off (step 4 of the stage 2 design) |
| [#58](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/58) | merged | docs: consistency sweep across the wiki after a day of changes |
| [#59](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/59) | merged | test: README layout check walks provider directories |
| [#60](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/60) | merged | docs(wiki): enterprise change management for beginners (not used in this project) |
| [#61](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/61) | merged | feat(connector): Twingate connector telemetry in the access layer (default off) |
| [#62](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/62) | merged | docs(wiki): enterprise networks, infrastructure, identity and careers |
| [#63](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/63) | merged | docs(wiki): change-management page corrections from review |
| [#64](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/64) | merged | feat(cost-gate): a ceiling per phase, raised deliberately |
| [#65](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/65) | merged | docs(wiki): screenshots, an image pipeline and a screenshots policy |
| [#66](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/66) | merged | docs: Support this project section in the README and wiki |
| [#67](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/67) | merged | docs: Author and socials section in the README and wiki |
| [#135](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/135) | merged | docs: project board as code and the planning page |
| [#136](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/136) | merged | Fix README mermaid flowchart rendering as raw code |
| [#137](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/137) | merged | docs: every diagram is a dark-mode picture with its Mermaid source underneath |
| [#138](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/138) | merged | feat(hardening): opt-in lock on the droplet metadata endpoint (#87) |
| [#139](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/139) | merged | test(hardening): fail the build if IPv6 is opened (#89) |
| [#140](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/140) | merged | feat(hardening): Spacelift plan policy denying inbound rules and IPv6 (#88) |
| [#141](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/141) | merged | feat(hardening): plan policy destroy guard and autodeploy guard (#92) |
| [#142](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/142) | merged | feat(hardening): opt-in default-drop host firewall on the connectors (#90) |
| [#143](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/143) | merged | docs: access_group is not deprecated; correct four pages (#93) |
| [#144](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/144) | merged | docs: design for the external zero-open-ports check (#91) |
| [#145](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/145) | merged | docs: stage 2 verification section and home-side runbook (#106) |
| [#146](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/146) | merged | feat(telemetry): opt-in node exporter and tag-sourced metrics firewall rules (step 5, #99) |
| [#147](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/147) | merged | Relicense from MIT to Apache-2.0 |
| [#148](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/148) | merged | docs: why I picked these tools |
| [#150](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/150) | merged | docs: carry the README Support and Socials formatting into the wiki Home page |
| [#151](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/151) | merged | feat(telemetry): opt-in Wazuh agent and auditd with a first-boot secret pull (step 7) |
| [#152](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/152) | merged | docs: add Grafana to why I picked these tools |
| [#153](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/153) | merged | feat(dashboards): site-aware Grafana dashboards, validation test and wiki page (#149) |
| [#154](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/154) | merged | feat(telemetry): opt-in node exporter and security-group-sourced metrics rules on AWS (#99) |
| [#155](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/155) | merged | feat: external zero-open-ports check (#91) |
| [#156](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/156) | merged | chore(cost): mark the DO weekly backups fraction verified (#117) |
| [#157](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/157) | merged | docs: bring the Roadmap stage 2 status up to date (#106) |
| [#158](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/158) | merged | feat(labs): synthetic Grafana and Prometheus demo lab (#128) |
| [#159](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/159) | merged | docs: MFA, hardware key and identity-provider guidance, plus springboards |
| [#160](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/160) | merged | docs(wiki): telemetry banners say built and merged, still unapplied |
| [#161](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/161) | merged | docs(wiki): dashboards page reflects the merged demo lab (#103) |
| [#162](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/162) | merged | docs(wiki): stale-claims pass on the stage 2 lesson pages |
| [#163](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/163) | merged | feat(cost): refuse backup plans the gate cannot price |
| [#164](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/164) | merged | feat(telemetry): Wazuh agent site label and an offline test of the Wazuh dashboard (#103) |
| [#165](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/165) | merged | docs: edge and DMZ design with costed options (#118) |
| [#166](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/166) | merged | docs: record edge rulings, add Why-Not-Private-Droplets-Yet, verify tor1 sizes |
| [#167](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/167) | merged | docs: short-lived Doppler tokens and the Twingate service-account limit, re-checked |
| [#168](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/168) | merged | docs: PeerTube stage design with costed options |
| [#169](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/169) | merged | docs: honeypot design in a separate account |
| [#170](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/170) | merged | feat(telemetry): per-site Twingate services via a sites map, TLS decision record |
| [#171](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/171) | merged | docs: accessibility pass over the wiki, with a test that holds it |
| [#172](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/172) | merged | docs: teardown checklist (order, leftovers, zero proof, token revocation) |
| [#173](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/173) | merged | chore: bump the Twingate provider from 3.x to 5.x |
| [#174](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/174) | merged | docs: sprint schedule on the roadmap |
| [#175](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/175) | merged | docs: Doppler expiring service tokens are documented, fix the UNVERIFIED claims |
| [#176](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/176) | merged | docs: Git from zero, a beginner page for clone, commit and pull requests |
| [#177](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/177) | merged | docs: deepen the GitHub lessons, fork steps, demo vs production, commit to pipeline |
| [#179](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/179) | merged | docs: reusable workflows and Git Your Ship Together in the CI lessons |
| [#180](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/180) | merged | docs: one stage 2 verification checklist, with pay-to-play and the sites map |
| [#181](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/181) | merged | docs: stack factory status and gap analysis |
| [#182](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/182) | merged | docs: honeypot and deception education plan |
| [#183](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/183) | merged | docs: Why this exists |
| [#184](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/184) | merged | docs: APIs and tokens from zero, a foundations side page |
| [#185](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/185) | merged | docs: foundations gap audit and proposed beginner lessons |
| [#186](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/186) | merged | docs: Linux for enterprise beginners, a foundations side page |
| [#187](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/187) | merged | docs: zero trust at home, two connectors and failover |
| [#188](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/188) | merged | docs: American English spelling sweep, style note and guard test |
| [#189](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/189) | merged | docs: foundations F2, the terminal and your first script |
| [#190](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/190) | merged | docs: foundations F4, hashing, encryption and keys |
| [#191](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/191) | merged | docs: foundations F3, how a web request works |
| [#192](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/192) | merged | docs: foundations F1, data formats and config files (JSON, YAML, HCL) |
| [#193](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/193) | merged | docs: foundations F7, enterprise identity (SSO, SAML, OAuth, OIDC) |
| [#194](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/194) | merged | docs: deception and honeypots track 1, concepts and honeytokens |
| [#195](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/195) | merged | docs: foundations F5, subnets, NAT and firewalls by hand |
| [#197](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/197) | merged | docs: where CAH uses Twingate service accounts, and what plan they need |
| [#198](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/198) | merged | docs: foundations F6, virtual machines, containers and cloud service models |
| [#199](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/199) | merged | docs: foundations F8, Windows, Active Directory and macOS in the enterprise |
| [#200](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/200) | merged | docs: foundations F12, working in a company (tickets, change, on-call, documentation) |
| [#201](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/201) | merged | docs: foundations F9, logs, SIEM and detection basics |
| [#202](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/202) | merged | docs: foundations F10, backups, recovery and patching |
| [#203](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/203) | merged | docs: foundations F11, threats in plain words |
| [#204](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/204) | merged | docs: honeypot Track 3, honeynet design and T-Pot at home |
| [#205](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/205) | closed | docs: honeypot Track 2, cloud sensor anatomy, a Cowrie weekend and reading the logs |
| [#206](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/206) | open | feat: DMZ edge stack and edge-host module, flag off (#122) |
| [#207](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/207) | merged | docs: open calls for feedback and issues, with a how-to, issue forms and SECURITY.md |
| [#208](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/208) | closed | docs: stack-per-service design note (maintainer ruling), cost shapes and open questions |
| [#209](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/209) | merged | docs: lesson I3, Spacelift from zero |
| [#210](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/210) | merged | docs: lesson I1, OpenTofu from zero (init, plan, apply, destroy) |
| [#211](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/211) | merged | docs: lesson I4, build and destroy a bunch, one stack per service |
| [#212](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/212) | merged | docs: lesson I2, plans, state, drift and recovery |
| [#213](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/213) | merged | docs: threat-model coverage audit and plan (TM-0 to TM-12) |
| [#215](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/215) | merged | docs: composable labs design note (piecemeal or whole builds, cost transparency) |
| [#216](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/216) | merged | docs: lesson W1, LAMP and LEMP from zero |
| [#217](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/217) | merged | docs: lesson W3, DNS, Cloudflare and hosting your own website |
| [#218](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/218) | merged | docs: mirror the Hammunition board layout in board.yaml (Kind, Epic, Decision, views, Security and Docs areas) |
| [#219](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/219) | merged | docs: lesson W2, WordPress and PHP security, WAFs, and why static sites win so often |
| [#220](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/220) | merged | docs: lesson W4, WordPress at scale (CDN, WAF, caching and CI) with a local lab |
| [#222](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/222) | merged | docs: honeypot Track 2, cloud sensor anatomy, a Cowrie weekend and reading the logs |
| [#223](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/223) | merged | docs: stack-per-service design note (maintainer ruling), cost shapes and open questions |
| [#224](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/224) | merged | docs: lesson S1, red and blue as yin and yang, think in systems, and choosing your lab OS |
| [#225](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/225) | merged | docs: lesson S2, security tools basics (Nmap, OpenVAS, Burp CE, Metasploit and friends) |
| [#228](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/228) | merged | docs: Start Here says what is left out on purpose and where AI fits |
| [#231](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/231) | merged | docs: Track 2 presents the separate SSH port as function, not protection |
| [#233](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/233) | merged | fix: remove a race that made the S2 nmap scan-log test flaky |
| [#234](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/234) | open | docs: lesson D3, file integrity and alerting (Tripwire, AIDE, Wazuh, auditd, fail2ban) |
| [#237](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/237) | merged | docs: first hour on a new system, updates, automatic updates and a baseline before anything else |
| [#238](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/238) | merged | docs: lesson D1, packet filters compared (iptables and ipset, nftables, UFW, BSD pf) |
| [#240](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/240) | merged | docs: lesson D2, IDS and IPS (Snort and Suricata) |
| [#242](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/242) | merged | docs: lesson D4, rate limiting at every layer |
| [#244](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/244) | merged | fix: make the lab tests' ports collision-proof and clean up in finally (#241) |
| [#251](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/251) | merged | docs: lesson, behind a CDN: real client IPs, why an IP is a weak identifier, and OSI basics |
| [#252](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/252) | open | feat: plan policy allowlists keyed by stack id and resource, with per-entry scope (#246) |
| [#255](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/255) | merged | docs: lesson, secrets from day one (password manager, Doppler for every asset, .env rules, scanning, leak drill) |
| [#256](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/256) | merged | feat: address-aware outbound rules in the DigitalOcean firewall module (#245) |
| [#257](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/257) | merged | feat: cost gate skips labs/ for the type allowlist but still checks syntax (option L1, #250) |
| [#258](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/258) | open | docs: lesson, cross-tenant data flows, data governance and retention, and DLP |

### Closed issues not Done on the board (9)

| Issue | Board status | Title |
|---|---|---|
| [#21](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/21) | Next | Expand GitHub Lessons |
| [#91](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/91) | Next | External zero-open-ports check |
| [#103](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/103) | Backlog | Home Grafana dashboards that work across sites (site label) |
| [#104](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/104) | Backlog | Per-site Twingate service accounts and TLS on the telemetry path |
| [#107](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/107) | Next | Follow up with etke.cc on how the homeserver reaches a self-hosted bridge |
| [#118](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/118) | Backlog | Edge design document with costed options |
| [#120](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/120) | Backlog | Honeypot design document (separate account, never in this apply path) |
| [#121](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/121) | Backlog | PeerTube: costed stage design |
| [#130](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/130) | Backlog | Accessibility pass on the wiki (alt text, contrast, plain language) |

## Pull requests with no linked issue (90)

Open or merged pull requests whose body has no `Closes`, `Fixes`, `Resolves` or `Refs` followed by an issue number.

| Pull request | State | Title |
|---|---|---|
| [#1](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/1) | merged | feat: load Doppler secrets into Spacelift runs |
| [#2](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/2) | merged | docs: state where the secrets trust boundary actually is |
| [#3](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/3) | merged | feat: two Twingate connectors sharing one site |
| [#4](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/4) | merged | fix: reuse the existing SSH key; harden the connector droplets |
| [#5](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/5) | merged | fix: retry the connector install, open outbound UDP, run on Eastern time |
| [#6](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/6) | merged | fix: install the connector the way Twingate's own Terraform does |
| [#7](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/7) | merged | fix: let the connectors reach each other's SSH inside the VPC |
| [#8](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/8) | merged | fix: let each connector open SSH to the other (outbound rule) |
| [#9](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/9) | merged | docs: wiki with flowcharts, component rationale, and why ZTNA instead of a VPN |
| [#10](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/10) | merged | docs: stage 3 design draft, workload host with Portainer, daemons and Matrix bridge |
| [#11](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/11) | merged | docs: exact DigitalOcean token scopes (Token A and B) |
| [#12](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/12) | merged | docs: wiki Terraform reference explaining every declaration |
| [#14](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/14) | merged | fix: move the environment to Toronto (tor1) |
| [#15](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/15) | merged | fix: use 10.78.0.0/24 for the Toronto VPC |
| [#16](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/16) | merged | docs: lessons from the account redeploy |
| [#17](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/17) | merged | docs: stage 3 draft, self-hosted mautrix-discord (Go) bridge, backups, etke.cc alternative |
| [#18](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/18) | merged | Stage 2 design: logging, metrics and the link home (draft) |
| [#19](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/19) | merged | docs: start-from-zero wiki track; Spacelift push policy; CI and wiki publishing on GYST only |
| [#20](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/20) | merged | docs: add edge DMZ handoff to the plans and the roadmap |
| [#25](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/25) | merged | docs(wiki): enterprise landscape and detection (Wazuh) lessons |
| [#26](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/26) | merged | docs: address Copilot review of the multi-cloud design (#24 follow-up) |
| [#27](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/27) | merged | docs(wiki): labs, build-it track, and path-based navigation |
| [#28](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/28) | merged | docs(wiki): one home for the push-policy caveat, Wazuh lesson fixes, heading links |
| [#29](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/29) | merged | docs: record the maintainer's multi-cloud decisions (#22) |
| [#30](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/30) | merged | docs: multi-cloud phase 0 findings and evidence (#22) |
| [#31](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/31) | merged | docs(wiki): AWS lessons for phase 1 (#22) |
| [#32](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/32) | merged | refactor(modules): shared Twingate bootstrap module (phase 2a of #22) |
| [#33](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/33) | merged | feat(modules): the provider module contract (phase 2b of #22) |
| [#34](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/34) | merged | feat(cost-gate): price more than one cloud (phase 2c-i of #22) |
| [#35](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/35) | merged | feat(ci): identifier check for cloud account ids (phase 2c-ii of #22) |
| [#36](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/36) | merged | docs(design): stage 2 settings layer and mini cloud SOC |
| [#37](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/37) | merged | docs(wiki): threat-model exercise and a traced change |
| [#38](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/38) | merged | docs(wiki): glossary links and a troubleshooting index |
| [#39](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/39) | merged | test(secrets): per-cloud secret separation (phase 2c-iii of #22) |
| [#40](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/40) | merged | docs(wiki): link the threat-model exercise and the traced change |
| [#41](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/41) | merged | fix(cost-gate): close parser-differential bypasses found in review |
| [#42](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/42) | merged | docs(wiki): OWASP Threat Dragon exercise for trust boundaries |
| [#43](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/43) | merged | docs(wiki): GCP lessons, unverified drafts (#22) |
| [#44](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/44) | merged | docs(wiki): Azure lessons, unverified drafts (#22) |
| [#45](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/45) | merged | feat(aws): vpc, firewall and connector modules (phase 3a of #22) |
| [#46](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/46) | merged | docs(wiki): Threat Dragon exercise fixes from review |
| [#47](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/47) | merged | docs: correct the proposed-run credential claim in the secrets runbook |
| [#48](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/48) | merged | feat(cost-gate): stack instances for multi-site (step 2b of the stage 2 design) |
| [#49](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/49) | merged | feat(settings): settings manifest, ignore rules and generated reference (step 1 of the stage 2 design) |
| [#50](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/50) | merged | docs(wiki): reading order and navigation |
| [#51](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/51) | merged | feat(aws): foundation and access stacks (phase 3b of #22) |
| [#52](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/52) | merged | docs(wiki): threat frameworks (STRIDE, ATT&CK, ATLAS) with importable Threat Dragon models |
| [#53](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/53) | merged | feat(settings): variables, examples and immutable keys (step 2 of the stage 2 design) |
| [#54](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/54) | merged | feat(firewall): tag-sourced rules from other tags (additive, step 4.2 of the stage 2 design) |
| [#55](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/55) | merged | feat(settings): timezone variable with a byte-identical default (step 3 of the stage 2 design) |
| [#56](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/56) | merged | docs(wiki): cloud telemetry, multiple sites and a mini SOC (lessons, drafts) |
| [#57](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/57) | merged | feat(telemetry): stack 20 skeleton, everything off (step 4 of the stage 2 design) |
| [#58](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/58) | merged | docs: consistency sweep across the wiki after a day of changes |
| [#59](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/59) | merged | test: README layout check walks provider directories |
| [#60](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/60) | merged | docs(wiki): enterprise change management for beginners (not used in this project) |
| [#61](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/61) | merged | feat(connector): Twingate connector telemetry in the access layer (default off) |
| [#62](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/62) | merged | docs(wiki): enterprise networks, infrastructure, identity and careers |
| [#63](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/63) | merged | docs(wiki): change-management page corrections from review |
| [#64](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/64) | merged | feat(cost-gate): a ceiling per phase, raised deliberately |
| [#65](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/65) | merged | docs(wiki): screenshots, an image pipeline and a screenshots policy |
| [#66](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/66) | merged | docs: Support this project section in the README and wiki |
| [#67](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/67) | merged | docs: Author and socials section in the README and wiki |
| [#135](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/135) | merged | docs: project board as code and the planning page |
| [#136](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/136) | merged | Fix README mermaid flowchart rendering as raw code |
| [#137](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/137) | merged | docs: every diagram is a dark-mode picture with its Mermaid source underneath |
| [#143](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/143) | merged | docs: access_group is not deprecated; correct four pages (#93) |
| [#144](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/144) | merged | docs: design for the external zero-open-ports check (#91) |
| [#147](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/147) | merged | Relicense from MIT to Apache-2.0 |
| [#148](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/148) | merged | docs: why I picked these tools |
| [#150](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/150) | merged | docs: carry the README Support and Socials formatting into the wiki Home page |
| [#152](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/152) | merged | docs: add Grafana to why I picked these tools |
| [#159](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/159) | merged | docs: MFA, hardware key and identity-provider guidance, plus springboards |
| [#162](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/162) | merged | docs(wiki): stale-claims pass on the stage 2 lesson pages |
| [#163](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/163) | merged | feat(cost): refuse backup plans the gate cannot price |
| [#175](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/175) | merged | docs: Doppler expiring service tokens are documented, fix the UNVERIFIED claims |
| [#188](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/188) | merged | docs: American English spelling sweep, style note and guard test |
| [#197](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/197) | merged | docs: where CAH uses Twingate service accounts, and what plan they need |
| [#198](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/198) | merged | docs: foundations F6, virtual machines, containers and cloud service models |
| [#199](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/199) | merged | docs: foundations F8, Windows, Active Directory and macOS in the enterprise |
| [#200](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/200) | merged | docs: foundations F12, working in a company (tickets, change, on-call, documentation) |
| [#201](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/201) | merged | docs: foundations F9, logs, SIEM and detection basics |
| [#202](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/202) | merged | docs: foundations F10, backups, recovery and patching |
| [#203](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/203) | merged | docs: foundations F11, threats in plain words |
| [#204](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/204) | merged | docs: honeypot Track 3, honeynet design and T-Pot at home |
| [#207](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/207) | merged | docs: open calls for feedback and issues, with a how-to, issue forms and SECURITY.md |
| [#209](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/209) | merged | docs: lesson I3, Spacelift from zero |
| [#210](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/210) | merged | docs: lesson I1, OpenTofu from zero (init, plan, apply, destroy) |
| [#211](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/211) | merged | docs: lesson I4, build and destroy a bunch, one stack per service |
| [#212](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/212) | merged | docs: lesson I2, plans, state, drift and recovery |
| [#213](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/pull/213) | merged | docs: threat-model coverage audit and plan (TM-0 to TM-12) |

## Reproduce every number

Run these from the maintainer's GitHub login (the board is private to it). `ChiefGyk3D/Clouds-Against-Humanity` is the repository and `ChiefGyk3D` / `4` the owner and number of the project.

```bash
gh issue list --repo ChiefGyk3D/Clouds-Against-Humanity --state all --limit 5000 --json number,title,state,labels,createdAt,closedAt,stateReason
gh pr list --repo ChiefGyk3D/Clouds-Against-Humanity --state all --limit 5000 --json number,title,state,isDraft,mergedAt,createdAt,body,headRefName
gh pr list --repo ChiefGyk3D/Clouds-Against-Humanity --state open --limit 500 --json number,statusCheckRollup,reviewDecision
gh project item-list 4 --owner ChiefGyk3D --limit 5000 --format json
python -I scripts/gen_project_status.py --refresh   # does all of the above and rewrites this page
```

The classification above is applied to that data by `scripts/gen_project_status.py`. CI re-renders the committed snapshot, `docs/wiki/.status-snapshot.json`, and fails when this page does not match it or has no generated-at time; it does not call GitHub. The page is only as current as the last refresh, which the maintainer runs from a login: by hand, from a scheduled local job, or from a hook in the Scrum Around and Find Out (SAFO) audit.

Next: [Roadmap](Roadmap.md), which says what is built and what is only planned; this page says what the work is doing right now.
