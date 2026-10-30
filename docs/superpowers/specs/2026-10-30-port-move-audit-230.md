# Port-move audit (issue #230)

Done-when for #230: "a grep audit that lists each place checked and what changed". Audit records in this repository live in `docs/superpowers/specs/` (see [the foundations gap audit](2026-10-22-foundations-gap-audit.md)), so this one does too. The question: does any page present moving a service to another port as protection? The maintainer's position is that it is security through obscurity. A scanner finds any open port, and a full-range scan takes minutes on a default run and seconds with a fast scanner on a good link.

The check is also a test, `tests/test_no_port_move_as_protection.py`. This record was derived by re-running its patterns against `origin/main` (before the change) and against this branch (after), not from memory.

## What was checked

| Scope | Files | How |
|---|---|---|
| `docs/wiki/*.md` (without `Contents.md`, `_Sidebar.md`, `_Footer.md`), `docs/stages/*.md`, `README.md` | 124 files | The test's `PORT_MOVE` and `SERVICE` patterns, then the `HONEST` pattern |
| `docs/superpowers/specs/`, `docs/superpowers/plans/`, `docs/threat-model/README.md`, plus the three scopes above | all files | Plain `grep -rniE` with the patterns below (not in the test) |

Patterns (case-insensitive):

1. `PORT_MOVE`: `(non-?standard|odd|unusual|alternate|alternative|different|another|high|random|other than 22)\s+(tcp\s+)?port`, or `(move|moves|moved|moving|change|changes|changed|changing)` within 40 characters before `port`, or `port` within 20 characters before `move|moved|change|changed`, or `its own port`.
2. `SERVICE` on the same line: `ssh|sshd|rdp|telnet|management|admin|service|daemon|login|server`.
3. `HONEST` on the same line passes the line: the move is called not a protection, obscurity, log noise, functional, and similar.
4. Extra greps over the design docs: `non-?standard port`; `odd port|unusual port|alternate port|different port|another port|high port|random port|other than 22`; `20222`; `pinned (inbound )?port|pins? the port|fixed port`; `obscurity`.

## Result of the wiki, stage and README scan

Before (`origin/main`): 14 lines matched `PORT_MOVE` and `SERVICE`; 6 had no `HONEST` wording and failed. After: 17 lines match (three new honest lines were added); 0 fail. Counts are lines, not pages.

## Lines that failed and what changed

| File:line (on `origin/main`) | What it said | Change |
|---|---|---|
| `Deception-and-Honeypots-Cloud-Cowrie-Weekend.md:260` | Debian/Ubuntu SSH note: "a changed port surprising people" | Added "(a functional problem, not a security one)" |
| `Deception-and-Honeypots-Cloud-Sensor-Anatomy.md:103` | Predict box: "giving real SSH a different port" | Added "(for function)" |
| `Deception-and-Honeypots-T-Pot-at-Home.md:137` | Installer "changes the SSH port to 64295" | Added "(to free port 22 for its honeypots; that is function, not protection)" |
| `Deception-and-Honeypots-T-Pot-at-Home.md:230` | Uninstall leaves "the changed SSH port" | Added "(a function change, not protection)" |
| `Deception-and-Honeypots-T-Pot-at-Home.md:268` | Evidence table: installer changes the SSH port | Added "(for function, so the honeypots can use 22)" |
| `Subnets-NAT-and-Firewalls-By-Hand.md:879` | Evade: admin "hides" a service on 20222 | Added "(security through obscurity)" |

## Lines that passed already, with a small edit

| File:line | What changed |
|---|---|
| `Deception-and-Honeypots-Cloud-Cowrie-Weekend.md:85` | None. Already says function, not a defense. A clause was added: a different port "makes your own logs quieter, which is not a security control" |
| `Deception-and-Honeypots-Cloud-Sensor-Anatomy.md:49` | Added "(it is security through obscurity)" |

## Lines that passed and were left alone

`Cowrie-Weekend:245` (says "for function, not protection"), `Sensor-Anatomy:40`, `Sensor-Anatomy:147`, `Deception-and-Honeypots-Start-Here.md:49`, `Plan-for-Failure:113` (functional move, stated as such), `Subnets:774` and `Subnets:887` (the lab run that shows a scan finding the odd port in about two seconds; a full-range figure is already marked est.).

## New text

- `Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md:100`: the "What does not count as protection" section states the position. Review fix: it said a scanner tries all 65,535 ports "in seconds"; it now says a default full-range scan takes minutes and a fast scanner on a good link can do it in seconds. The Subnets lab measured 401 ports in about two seconds, which is a small range, not a full scan.
- `Droplet-Hardening.md:120`: says sshd stays on 22 and why, linking the section above. Wording aligned with the same figure.
- `Threats-in-Plain-Words.md:392`: the Evade bullet links the section above.
- `test_blast_radius_lesson.py`: the cap on pages linking the lesson went from 8 to 9 for the two new links (Droplet hardening, threats lesson).

## Design docs (not scanned by the test)

| File | Hit | Change |
|---|---|---|
| `specs/2026-10-19-edge-dmz-design.md` (exposure table and the handoff paragraph) | "pinned inbound port" for i2pd | Reworded: the port stays closed until the i2pd stack is built, then i2pd picks it at random, not as a security measure |
| `specs/2026-10-19-edge-dmz-design.md` rulings table | no ruling on the i2pd port | Added ruling 11 (issue #122, ruled 2026-10-22), linking the lesson |
| `plans/2026-10-12-edge-dmz-handoff.md:51` | "i2pd pinned inbound port" | Not changed. It is the original handoff record, which the design doc quotes and supersedes (ruling 11) |
| `specs/2026-10-22-foundations-gap-audit.md:161` | "port" and "different" in an unrelated sentence (a firewall mini-loop) | None. False positive, not about moving a service |
| `specs/2026-10-21-peertube-stage-design.md:137` | SMTP ports blocked by the provider | None. Not a port move |
| `docs/stages/*.md`, `README.md`, other specs | `non-standard port`, `20222`, `obscurity`: no hits outside the wiki | None |
| `docs/stages/01-access.md`, `aws-access.md` | "1-65535" outbound UDP range | None. A firewall range for Twingate peer-to-peer, not a port move |

## Limits

A phrase check finds common wording, not every possible one. A page that says "run it on 2222" with no "port" next to it would not match. The patterns were not widened for this audit.
