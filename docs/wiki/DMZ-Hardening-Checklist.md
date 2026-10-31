# DMZ hardening checklist: one page to print

Reference card for [The DMZ, and hardening a host that faces the internet](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md). Read the lesson first; this page only lists. Every row comes from the lesson or from the file it cites, and each row names the repository check that covers it, or says **none**.

> **Status: unverified draft, written from reading on 2026-10-30.** The public edge is **design only**: `stacks/50-edge` and `modules/edge-host` are written and tested with mocked providers, the switch is off, the stage is **not approved**, and nothing has run on a real machine (`docs/stages/05-edge.md`). A passing check below shows that the repository declares a control. It does not show that a running host has it. Not yet reviewed by the maintainer.

## Build checklist

Tick a box when you have verified the item on your own host. "Status" is the edge's status in this project: **built, not applied**, or **design**.

| Done | Item | Status | The check in this repository |
|---|---|---|---|
| [ ] | Host firewall is default-drop on input, behind the cloud firewall, with the same port list | Built, not applied | `tests/test_edge_stack.py::test_the_host_firewall_is_default_drop_and_mirrors_the_cloud_firewall_input`; `no_ports_means_no_accept_rules_and_a_default_drop_table` in `modules/edge-host/tests/edge-host.tftest.hcl` |
| [ ] | No SSH and no admin user; root password locked | Built, not applied | `tests/test_edge_stack.py::test_the_droplet_has_no_admin_path`; `the_user_data_has_no_ssh_path` in the module tests |
| [ ] | Automatic security updates, with a staggered reboot time | Built, not applied | `tests/test_edge_stack.py::test_reboot_slots_are_unique_staggered_and_clear_of_the_connectors`; `the_reboot_time_defaults_to_the_services_slot_in_eastern` in the module tests |
| [ ] | Only the packages the host needs; no daemon on first boot | Built, not applied | `tests/test_edge_stack.py::test_the_cloud_init_installs_only_os_packages_and_no_service`; `no_service_is_installed` in the module tests |
| [ ] | Open only the ports the service needs; no IPv6 inbound | Built, not applied | `every_public_inbound_rule_is_ipv4_only` and `enabled_opens_reticulum_and_mqtt_only_so_i2pd_and_iperf3_stay_closed` in `stacks/50-edge/tests/edge.tftest.hcl`; `tests/test_ipv6_closed.py` |
| [ ] | Block outbound traffic to the metadata endpoint for non-root users | Built, not applied | **None.** The template has it (`modules/edge-host/cloud-init.yaml.tftpl`); no test names it |
| [ ] | No secret in the first-boot data; rendered user-data never an output | Built, not applied | `tests/test_edge_stack.py::test_the_user_data_carries_no_secret_shaped_field` and `test_the_user_data_is_never_an_output` |
| [ ] | Each service runs as its own unprivileged user, sandboxed | Design | **None.** No service exists (design section 4.4) |
| [ ] | Rate and storage caps on what each service accepts | Design, open blocker | **None.** The design waits on a stated Reticulum rate cap (design section 5.7) |
| [ ] | Outbound rules chosen on purpose, per user | Design (proposal) | **None.** The module's host firewall filters input only (design section 4.6.2) |
| [ ] | File integrity checks on files that should never change | Recommendation | **None.** The design names no integrity tool for the edge |
| [ ] | Logs copied off the host as written, to a place the host cannot rewrite | Design | **None.** The edge sends no logs (`docs/stages/05-edge.md` section 4) |

## What to log

| Log | Status for the edge |
|---|---|
| Firewall drops and new outbound connections | Design. **None** configured in this repository |
| Each service's own log | Design. No service exists |
| System journal and audit log (service starts and stops, writes to watched files) | Not configured for the edge; the connectors' opt-in version is in `modules/twingate-bootstrap/cloud-init.yaml.tftpl` |
| A version report, so a missed patch is visible | Design (design section 3.5) |
| Update and reboot results | Nothing logs them that the lesson found |

## What should alert

| Event | Action | Status |
|---|---|---|
| Any login of any kind | Alert. Treat the host as suspect and rebuild | Recommendation |
| A change to the firewall script, update configuration or account files | Alert | Recommendation |
| A new outbound destination from a daemon that had none | Alert | Alert is a recommendation; the rules are design |
| The host firewall table is missing | Alert | Recommendation |
| The measurement path shows the edge is down | Alert (ntfy) | Design (design section 3.5, risk 7) |
| Storage for a service nears its cap (design proposes 80 percent for `lxmd`) | Alert | Design; thresholds not measured |
| Traffic or transfer near the monthly cap (design proposes 80 percent) | Alert on a threshold | Design; thresholds not measured |
| A rebuild that was scheduled does not happen | Alert | Lesson table: a finished rebuild is log only; the missed one is the alert |

**Noise, do not page:** a port scan or a failed connection to a closed port. Count it and graph it.

**Not a log alert:** a provider abuse notice. A person reads the abuse inbox on a calendar (design section 3.5, risk 4).

For every alert, write down who gets it, what it means and what to do next. On an immutable host the usual answer is to preserve the logs that already left the machine and rebuild from code, not repair. No complete route from log to person exists yet for the edge, so none is described here.

Back to the lesson: [The DMZ, and hardening a host that faces the internet](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md). Related: [Droplet hardening](Droplet-Hardening.md).
