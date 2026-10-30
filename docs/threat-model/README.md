# Threat models

Four OWASP Threat Dragon v2 models, read against the code on 2026-10-24.
Open them with the Threat Dragon desktop app or the web app (File > Open, or a
Local Session). Positions come from `scripts/threat_dragon_layout.py`; edit the
layout there, not by hand. The check `scripts/threat_dragon_layout.py --check`
and the tests in `tests/test_threat_*.py` run in CI.

Rule used: a threat is Mitigated only when a control is visible in code or
config. Vendor and GitHub settings cannot be read from a clone, so a claim that
rests on one starts with `UNVERIFIED:` and the threat stays Open.

## What each model covers

| File | View | Covers |
|---|---|---|
| `clouds-against-humanity.threat-dragon.json` | STRIDE, defender | Stages 0 and 1: contributor, CI, Spacelift runs, Doppler `prd`, state, cloud API, Twingate, connector droplets. Boundaries B1 to B8 match the wiki exercise; T-numbers match `docs/wiki/Threat-Model.md`. 47 threats. |
| `clouds-against-humanity.attack.threat-dragon.json` | ATT&CK, attacker | Same diagram, 41 adversary-behavior threats with technique IDs. A deliberate exercise; not a defender model. |
| `clouds-against-humanity.atlas.threat-dragon.json` | ATLAS, attacker | AI tools around the repository (coding agent, hosted reviewer, local model). Boundaries AB1 to AB5. A deliberate exercise. 12 threats. |
| `clouds-against-humanity.stage2.threat-dragon.json` | STRIDE | Stage 2 (written, not applied): `stacks/20-telemetry`, log shipping and metrics in `modules/twingate-bootstrap`. Boundaries SB1 to SB5. 15 threats. |

`framework-reference.json` and `attack-navigator-layer.json` support the ATT&CK
and ATLAS models.

## Trust boundaries

- B1: nothing from the internet reaches a connector. B2: a pull request reaches the repository and CI only.
- B3: the push policy never proposes a Spacelift run. B4: branch protection and CI green guard `main`.
- B5: only a merged commit becomes a tracked run. B6: read-only Doppler token, secrets fetched by name.
- B7: a person confirms every apply. B8: identity provider sign-in and per-resource ACL.
- AB1 to AB5: untrusted text, agent tool permissions, prompts leave the machine, no secrets in agent context, a person reads the diff.
- SB1 to SB5: cloud site, service-account ACL, hostboot secret, home network (outside the repository), tracked run on `main`.

## Not modeled (found in the code, no model yet)

- Outbound from connectors is open to any address on several ports and all UDP.
- The AWS twin (`stacks/aws`, `modules/aws`) has no Spacelift hook entry in `.spacelift/config.yml`.
- The wiki publish path (`wiki.yml`) and the `labs/` directory.
- Planned stages (edge, honeypot, stage 3) have specs and no code.

## Open High threats (STRIDE numbering)

- Core: 4, 5, 6, 7, 12, 13, 16, 17, 20, 21, 27, 33, 34, 36, 37, 38, 40, 42, 43, 47.
- ATT&CK: the same numbers except 40. ATLAS: 1, 3, 5, 6, 8.
- Threat 46 (Tampered Twingate package) moved to Mitigated by issue 288: `cah-apt-key-check` now refuses any extra key in the Twingate apt key file. Threat 4 (tampered download or action) stays Open for the other causes (unpinned weekly connector update, unpinned pytest in CI, a pinned commit that was already malicious).
- Stage 2: 2 (path home), 7 (shared API key), 9 (hostboot token in metadata), 10 (service key on a host).

## UNVERIFIED items

- Branch protection and a required CI green check on `main`; MFA and sign-in policy at the identity provider.
- Whether `push.rego` and `plan.rego` are attached in Spacelift; Doppler token scope and expiry; billing alerts.
- `::add-mask` masking on a real run; state access in Spacelift; Twingate revocation.
- Metadata lock, host firewall, node exporter and log shipping on a real machine.
- Stage 2 end to end: home manager, scraper, headless client, service-key storage, hostboot token lifetime.
- ATLAS: agent configuration, the review bot, the local model server and its proxy plan (not found in this repository).
