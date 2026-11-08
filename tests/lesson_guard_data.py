# SPDX-License-Identifier: Apache-2.0
"""Data for tests/test_lesson_guards.py (issue #525): the shared defaults, then one entry per lesson page.

An entry is {"config": {...}, "rows": [...]}. Both are optional: a page with no entry gets the defaults only.

config keys (all optional):
  status_words        EXACT list of words a claims register status cell may contain. It replaces the shared
                      vocabulary, so use it where the old per-lesson file had a narrower set.
  status_extra        words added to the shared vocabulary for one page (a status the page really uses).
  addresses_allow     EXACT list of address regexes the page may contain. It replaces the shared defaults.
  addresses_extra     address-shaped strings added to the shared defaults (a version number, a documented lab net).
  addresses_require   addresses that must appear (so the address guard cannot go vacuous).
  min_register_rows, min_links, min_glossary_rows   thresholds; 0 glossary rows means the page has no glossary terms.
  nav_contains        text the page's _nav.yaml line must carry (its status and subgroup).
  nav_places_skip     navigation files that do not list the page, with the reason in a comment.
  must_link, must_link_prefix   pages (or page-name prefixes) the lesson must link, as links, never as plain text.

A row is {"id", ...assertions}; the assertion keys are documented on `check_row` in test_lesson_guards.py. A row with
"start"/"end" looks only at the text between those two strings.
"""

DEFAULTS = {
    "status_words": ("Read", "Observed", "Run", "General knowledge", "**est.**", "Not read", "Not run", "Not verified", "Constructed", "Secondary", "Page read", "Search summary"),
    # documented placeholder ranges (RFC 5737), loopback, the unspecified address and the cloud metadata address
    "addresses_default": (r"192\.0\.2\.\d+", r"198\.51\.100\.\d+", r"203\.0\.113\.\d+", r"127\.\d+\.\d+\.\d+", r"0\.0\.0\.0", r"169\.254\.169\.254"),
    "min_register_rows": 1,
    "min_links": 1,
    "min_glossary_rows": 1,
}

# Pages whose _nav.yaml entry carries a `status` but that have no `## Claims register`: the cloud-provider pages, the
# telemetry pages and a few runbooks. They are not lessons of this form, so the discovery rule leaves them out. The
# list is explicit so that a lesson which LOSES its register is a named failure and not a silent drop from the suite.
NO_REGISTER = (
    "Build-Your-Own-Mini-SOC",
    "Cloud-Telemetry-What-and-Why",
    "DMZ-Hardening-Checklist",
    "Detection-and-Monitoring-Wazuh-and-the-Landscape",
    "Multiple-Sites-and-Identity",
    "Provider-AWS-Account-Preparation",
    "Provider-AWS-Cost-Lesson",
    "Provider-AWS-The-Same-Four-Pieces",
    "Provider-Azure-Account-Preparation",
    "Provider-Azure-Cost-Lesson",
    "Provider-Azure-The-Same-Four-Pieces",
    "Provider-GCP-Account-Preparation",
    "Provider-GCP-Cost-Lesson",
    "Provider-GCP-The-Same-Four-Pieces",
    "Reading-a-Dashboard-as-an-Operator",
    "Stage-2-Home-Side-Runbook",
    "Telemetry-Crosses-the-Trust-Boundary",
    "Why-Not-Private-Droplets-Yet",
    "Why-the-Clouds-Differ",
)

VM = "Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options"
CRON = "Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd"
ANSIBLE = "Ansible-Configuration-Management-Versus-Provisioning"
DFIR = "DFIR-Toolkits-and-Live-Triage-SIFT-Velociraptor-KAPE-and-the-Incident-Response-Workflow"
DISK_ENC = "Disk-and-File-Encryption-VeraCrypt-TrueCrypt-History-BitLocker-FileVault-and-LUKS"
DISK_FOR = "Disk-Forensics-with-Autopsy-and-The-Sleuth-Kit"
HSM = "Hardware-Security-Modules-What-They-Are-and-Building-Your-Own-with-pico2hsm"
MEMORY = "Memory-Forensics-Acquiring-RAM-and-Analyzing-It-with-Volatility-3"
NETLOG = "Network-Log-and-Timeline-Forensics-Packet-Captures-Logs-and-Plaso"
FIRMWARE = "Open-Firmware-and-Trustworthy-Hardware-coreboot-Heads-Nitrokey-and-Vendors-That-Ship-the-Intel-ME-Disabled"

DRAFT = 'status: "draft"'
FORENSICS = 'subgroup: "Digital forensics"'
BRIDGE_FORBID = r"-(nic|netdev|net)\s+(bridge|tap)|\bbridge=|--network\s+bridged|nic\d?\s+bridged"

PAGES: dict[str, dict] = {
    # ---- pages that have no per-lesson file: the generic checks, plus the statuses they really use ----------------
    "Attack-Surface-List-Shrink-Measure": {"config": {"status_extra": ("Searched", "est."), "min_glossary_rows": 0}},
    "Attack-Surface-Map-Layer-by-Layer": {"config": {"status_extra": ("Carried over",), "min_glossary_rows": 0}},
    "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys": {"config": {"status_extra": ("Listing read", "Title and header read")}},
    "Deception-and-Honeypots-Cloud-Cowrie-Weekend": {"config": {"status_extra": ("The ISC's claim",), "min_glossary_rows": 0}},
    # the Reading-Order page lists the cloud-sensor path of the deception lessons, not this introduction
    "Deception-and-Honeypots-What-Deception-Is": {"config": {"nav_places_skip": ("Reading-Order.md",)}},
    "Environments-and-Promotion-Dev-Staging-Production": {"config": {"status_extra": ("**Not designed**",)}},
    "Grafana-Basics-From-a-Blank-Page": {"config": {"status_extra": ("Written from reading",)}},
    "Hardware-Security-Keys-YubiKey-Nitrokey-Smart-Cards-and-PIV": {"config": {"status_extra": ("My opinion",)}},
    "Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose": {"config": {"status_extra": ("Quoted from", "Repeated from")}},
    "Linux-for-Enterprise-Beginners": {"config": {"status_extra": ("Matches the vendor pages", "Not re-verified")}},
    "Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero": {"config": {"status_extra": ("Nothing run",)}},
    "Radio-Off-Grid-Communication-LoRa-Meshtastic-Reticulum-Ham-and-SIGINT": {"config": {"status_extra": ("Stated by the maintainer",)}},
    "Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon": {"config": {"status_extra": ("**Est.**", "His words", "**Unverified.**")}},
    "The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet": {"config": {"status_extra": ("Recommendation", "Interpretation")}},
    "Wazuh-SIEM-and-Data-Pipelines": {"config": {"status_extra": ("**UNVERIFIED**",)}},
    # version numbers and lab networks that look like addresses
    "Hands-On-Whonix-and-Qubes-OS-Gateway-Split-Compartments-Disposables-and-Policy-Prompts": {"config": {"addresses_extra": (r"10\.152\.152\.\d+", r"18\.2\.4\.2", r"255\.255\.192\.0")}},
    "How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database": {"config": {"addresses_extra": (r"0\.9\.7\.1",)}},
    "Lab-Publish-a-Web-Server-as-a-Tor-Onion-Service-and-an-I2P-Site-Time-Boxed-and-Defensive": {"config": {"addresses_extra": (r"0\.4\.8\.10", r"0\.4\.9\.14")}},
    "Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig": {"config": {"addresses_extra": (r"1\.14\.1\.0",)}},
    # ---- Ansible ------------------------------------------------------------------------------------------------
    ANSIBLE: {
        "config": {
            "status_words": ("Read", "Observed", "**est.**"),
            "addresses_allow": (r"127\.0\.0\.1",),
            "min_register_rows": 20,
            "min_links": 8,
            "min_glossary_rows": 5,
            "nav_contains": (DRAFT,),
        },
        "rows": [
            {"id": "banner", "startswith": "# Ansible: configuration management versus provisioning", "contains": ["Status: unverified draft", "2026-11-07", "**Not run:**", "ansible-core 2.22.0"]},
            {
                "id": "lab-commands-stay-on-the-local-machine",
                "code": {
                    "tags": ["bash", "ini"],
                    "require": ["ansible_connection=local", "ansible-playbook"],
                    "forbid": r"\bansible_host=|\bansible_ssh_|\bssh\s+\S+@",
                    "bite_bad": ["web ansible_host=203.0.113.9", "ssh admin@box"],
                    "bite_good": ["localhost ansible_connection=local"],
                },
            },
            {"id": "check-mode-before-the-real-repair-run", "start": "### Exercise 4", "end": "### Exercise 5", "order_before_last": [("--check --diff", "ansible-playbook -i inventory.ini site.yml\n")]},
            {"id": "unverified-claims-are-marked-in-the-body", "count_at_least": {"est.": 10}},
            # test_ansible_playbook_is_idempotent_and_the_bad_task_is_not (needs ansible-playbook) stays code in the suite
        ],
    },
    # ---- Cron, timers, init scripts -----------------------------------------------------------------------------------
    CRON: {
        "config": {
            "status_words": ("Read", "Run", "Observed", "**est.**", "Statement of opinion"),
            "addresses_allow": (),
            "min_register_rows": 15,
            "min_links": 5,
            "min_glossary_rows": 7,
            "nav_contains": (DRAFT,),
        },
        "rows": [
            {"id": "banner", "startswith": "# Cron, systemd timers, and init scripts versus systemd", "contains": ["Status: unverified draft", "I did not start a timer", "did not edit a crontab", "2026-11-07", "Not verified, plainly"]},
            {"id": "lessons-that-mention-cron-link-this-one", "inbound_all": ["Terminal-and-Your-First-Script", "Linux-for-Enterprise-Beginners", "First-Hour-on-a-New-System-Updates-and-Baseline"]},
            {
                "id": "translation-table-weekly-and-the-day-rule",
                "contains": ["`weekly` means Monday at midnight in systemd", "`@weekly` | `Sun *-*-* 00:00`"],
                "contains_any": ["the 1st and 15th **or** Fridays", "the 1st and 15th **and** on every Friday"],
            },
            {
                "id": "distro-table-dated-and-unread-edges-marked",
                "start": "## Is cron still installed? What I checked",
                "end": "## Init scripts versus systemd",
                "contains": ["2026-11-07", "Debian", "Ubuntu", "Rocky", "Fedora", "Arch", "openSUSE"],
                "count_at_least": {"**est.**": 4},
            },
            {
                "id": "exercises-never-use-crontab-r",
                "contains": ["crontab -r"],  # the warning about it must stay in the page
                "code": {"tags": ["bash"], "require": ["crontab"], "forbid": r"crontab -r", "bite_bad": ["crontab -r"], "bite_good": ["crontab -l"]},
            },
        ],
    },
    # ---- DFIR toolkits ----------------------------------------------------------------------------------------------
    DFIR: {
        "config": {
            "status_words": ("Read", "Run", "Page read", "**est.**"),
            "addresses_allow": (),
            "min_register_rows": 20,
            "min_links": 8,
            "min_glossary_rows": 5,
            "nav_contains": (DRAFT, FORENSICS),
            "must_link": ("Build-Your-Own-Mini-SOC", "Logs-SIEM-and-Detection-Basics", "Backups-Recovery-and-Patching", "Careers-Roles-and-What-to-Learn-Next"),
        },
        "rows": [
            {"id": "banner", "startswith": "# DFIR toolkits and live triage", "contains": ["Status: unverified draft", "**Not run:**", "2026-11-07", "Not verified, plainly"]},
            {
                "id": "toolkit-table-names-every-tool-and-closed-ones-are-marked",
                "start": "## The toolkits at a glance",
                "end": "## Live triage and dead-box imaging",
                "contains": ["SIFT Workstation", "CAINE", "Velociraptor", "KAPE", "FTK Imager", "plaso", "AGPL-3.0", "Apache-2.0", "2026-11-07"],
                "count_at_least": {"**not open source**": 2},
            },
            {
                "id": "nist-account-names-both-revisions",
                "start": "## An incident response workflow, and where forensics fits",
                "end": "## Mobile and cloud forensics",
                "contains_ci": ["Revision 2", "Revision 3", "April 2025", "Govern", "lessons learned"],
            },
            {
                "id": "certifications-carry-no-prices-and-no-affiliate-links",
                "start": "## Training and certifications",
                "end": "## Free exercise",
                "regex_absent": [r"[$€£]\s?\d|\bUSD\b"],
                "absent": ["http", "ref="],
                "contains": ["GCFE", "GCFA"],
            },
            {
                "id": "exercise-collects-only-into-the-learners-folder",
                "code": {
                    "tags": ["bash"],
                    "require": ["collect.sh", "sha256sum -c", "mkdir -p ~/triage-lab"],
                    "forbid": r"crontab -r|sudo rm|>\s*/(etc|usr|var|bin)/",
                    "bite_bad": ["crontab -r", "sudo rm -rf x", "echo x > /etc/passwd"],
                    "bite_good": ["echo x > ~/triage-lab/out"],
                },
            },
        ],
    },
    # ---- Disk and file encryption --------------------------------------------------------------------------------------
    DISK_ENC: {
        "config": {
            "status_words": ("Read", "Observed", "**est.**"),
            "addresses_allow": (),
            "min_register_rows": 20,
            "min_links": 8,
            "min_glossary_rows": 10,
            "nav_contains": (DRAFT,),
        },
        "rows": [
            {"id": "banner", "startswith": "# Disk and file encryption", "contains": ["Status: unverified draft", "**Not run:**", "2026-11-07", "Not verified, plainly"]},
            {"id": "not-run-list-names-the-untried-features", "start": "**Not run:**", "end": "Vendor and project statements", "contains": ["a hidden volume", "a keyfile", "BitLocker", "FileVault"]},
            {"id": "no-unfinished-placeholder", "absent": ["RESULTS_", "TODO", "@@"]},
            {
                "id": "every-password-in-a-command-is-a-labeled-placeholder",
                "contains": ["Never type a password you use anywhere real"],
                "code": {
                    "tags": ["bash"],
                    # a literal password handed to the tool (-p 'x', --new-password='x', PW='x') that is not marked PLACEHOLDER
                    "forbid": r"(?:\s-p\s+|--new-password=|\bPW=)'(?![^']*PLACEHOLDER)[^']*'",
                    "count_at_least": {r"(?:\s-p\s+|--new-password=|\bPW=)'[^']*'": 4},
                    "bite_bad": ["veracrypt -C x -p 'hunter2'"],
                    "bite_good": ["veracrypt -C x -p 'Wrong-PLACEHOLDER-2'"],
                },
            },
            {
                "id": "truecrypt-history-dated-and-quotes-the-notice",
                "start": "## From TrueCrypt to VeraCrypt: a dated history",
                "end": "## Where it fits",
                "contains": [
                    "2014-04-14", "2014-05-28", "2014-09-04", "2014-12-30", "2015-04-02", "2015-08-05", "2016-10-17", "2023-10-01", "2026-06-09",
                    "WARNING: Using TrueCrypt is not secure as it may contain unfixed security issues",
                    "two High, none Medium, one Low, one Undetermined",
                    "8 critical, 3 medium and 15 low",
                    "(secondary)",
                ],
            },
            {
                "id": "hidden-volumes-with-their-honest-limits",
                "start": "### Hidden volumes and plausible deniability, with the limits",
                "end": "### Use across",
                "contains": ["several points over time", "wear-leveling", "TRIM", "1.18a", "must recreate both the outer and hidden volumes", "legal"],
            },
            {"id": "platform-tools-and-comparison", "start": "## Full-disk encryption by platform", "end": "## Three layers", "contains": ["BitLocker", "FileVault", "LUKS", "XTS", "recovery key", "TPM"]},
            {"id": "defaults-quoted-match-the-documentation", "contains": ["500,000 iterations", "200,000", "416 MiB", "6 passes"]},
        ],
    },
    # ---- Disk forensics ---------------------------------------------------------------------------------------------
    DISK_FOR: {
        "config": {
            "status_words": ("Read", "Observed", "Search summary only", "**est.**"),
            "addresses_allow": (),
            "min_register_rows": 25,
            "min_glossary_rows": 4,
            "nav_contains": (DRAFT, FORENSICS),
            "must_link": ("Hashing-Encryption-and-Keys", VM, "Terminal-and-Your-First-Script"),
            # the siblings are on main: each is a link to a page that exists (it was plain text before)
            "must_link_prefix": ("Digital-Forensics-Foundations", "Memory-Forensics", "Network-Log-and-Timeline-Forensics", "DFIR-Toolkits"),
        },
        "rows": [
            {"id": "banner", "startswith": "# Disk forensics with Autopsy and The Sleuth Kit", "contains": ["Status: unverified draft", "Autopsy itself was not installed or started", "**Not run:**", "2026-11-07", "Not verified, plainly"]},
            {
                "id": "authorization-rule-is-stated-up-front",
                "order": [("Examine only your own devices or data you are explicitly authorized to examine", "## What you will be able to do")],
                "contains": ["not legal advice"],
            },
            {
                "id": "hash-step-before-the-examination-commands",
                "order": [("sha256sum lab.dd > lab.dd.sha256", "mmls lab.dd\n   fsstat")],
                "regex_present": [r"`[0-9a-f]{64}`|[0-9a-f]{64}  lab\.dd"],
            },
            {"id": "versions-and-licenses-are-dated", "contains": ["4.23.1", "4.15.0", "2026-05-07", "2026-04-15", "Apache License", "Common Public License", "October 2023"]},
        ],
    },
    # ---- Hardware security modules ----------------------------------------------------------------------------------------
    HSM: {
        "config": {
            "status_words": ("Read", "Observed", "General knowledge", "**est.**"),
            "min_register_rows": 20,
            "min_links": 6,
            "min_glossary_rows": 5,
            "nav_contains": (DRAFT,),
        },
        "rows": [
            {"id": "banner", "startswith": "# Hardware security modules", "contains": ["Status: unverified draft", "**Not run:**", "2026-11-07", "no Pico 2 was available"]},
            {"id": "part-b-is-marked-untested", "contains": ["Part B: the same on a Pico 2 (UNTESTED)", "**Untested.**"]},
            {"id": "maintainer-checks-exist", "start": "## For the maintainer: checks to run when you build it", "end": "## Checkpoint", "numbered_items_min": 10},
            # the three values the project's own docs publish as sample PINs
            {"id": "no-published-sample-pins", "absent": ["648219", "3537363231383830", "57621880"]},
            {"id": "projects-own-limits-are-quoted", "contains": ["not a certified secure element", "Never deploy either: the development storage key is public.", "A4", "RP2350-E24"]},
            # test_hsm_part_a_signs_verifies_and_fails_on_a_changed_message (needs openssl) stays code in the suite
        ],
    },
    # ---- Memory forensics ------------------------------------------------------------------------------------------------
    MEMORY: {
        "config": {
            "status_words": ("Read", "Observed", "General knowledge", "**est.**"),
            "addresses_allow": (r"127\.0\.0\.1",),
            "addresses_require": ("127.0.0.1",),
            "min_register_rows": 20,
            "min_links": 4,
            "min_glossary_rows": 4,
            "nav_contains": (DRAFT, FORENSICS),
            # the siblings are on main now: each is a link to a page that exists (they were plain text before)
            "must_link_prefix": ("Digital-Forensics-Foundations", "Disk-Forensics", "Network-Log-and-Timeline-Forensics", "DFIR-Toolkits", "Device-Firmware-Security", "Open-Firmware"),
        },
        "rows": [
            {"id": "banner", "startswith": "# Memory forensics: acquiring RAM", "contains": ["Status: unverified draft", "**Not run:**", "2026-11-07", "Volatility 3 2.28.2"]},
            {"id": "callsign-and-machine-names-are-placeholders", "contains": ["N0TST", r"local-hostname: lab\n"]},
            {
                "id": "guest-never-bridged-onto-a-real-network",
                "code": {
                    "tags": ["bash"],
                    "require": ["-nic user", "hostfwd=tcp:127.0.0.1"],
                    "forbid": r"-(nic|netdev|net)\s+(bridge|tap)|\bbridge=",
                    "bite_bad": ["qemu-system-x86_64 -nic bridge,br=br0"],
                    "bite_good": ["qemu-system-x86_64 -nic user,model=virtio-net-pci"],
                },
            },
            {"id": "checksum-before-first-boot", "order": [("sha512sum -c sums", "qemu-system-x86_64 -accel kvm")], "contains": ["do not boot the image"]},
            {"id": "license-and-version-dated", "contains": ["Volatility Software License, Version 1.0", "2.28.2", "2026-09-17"]},
            {"id": "plugins-it-ran", "contains": ["linux.pslist.PsList", "linux.psscan.PsScan", "linux.sockstat.Sockstat", "linux.malware.malfind.Malfind", "windows.psscan.PsScan", "windows.netscan.NetScan"]},
        ],
    },
    # ---- Network, log and timeline forensics -------------------------------------------------------------------------------
    NETLOG: {
        "config": {
            "status_words": ("Read", "Run", "Observed", "**est.**"),
            "addresses_allow": (r"10\.89\.0\.\d{1,3}", r"0\.0\.0\.0"),  # the lab container network
            "min_register_rows": 15,
            "min_links": 6,
            "min_glossary_rows": 5,
            "nav_contains": (DRAFT, FORENSICS),
        },
        "rows": [
            {"id": "banner", "startswith": "# Network, log and timeline forensics", "contains": ["Status: unverified draft", "2026-11-07", "Not verified, plainly", "What I ran and what failed"]},
            {"id": "in-page-anchors-were-collected", "regex_count_at_least": {r"\]\(#[a-z0-9-]+\)": 1}},
            {"id": "invented-lab-password-is-marked-invented", "contains": ["hunter2-lab", "invented"]},
            {"id": "time-zone-lesson-names-both-runs-and-the-offset", "contains": ["--timezone America/New_York", "2026-11-07T10:49:52+00:00", "2026-11-07T15:49:52+00:00", "7 minutes 2 seconds"]},
            {"id": "plaso-facts-dated-with-real-parser-names", "contains": ["20261027", "Apache-2.0", "text/apache_access", "text/syslog_traditional"]},
            {"id": "law-section-and-own-network-only", "contains": ["not legal advice"], "contains_any": ["own computer", "container network you create"]},
        ],
    },
    # ---- Open firmware -------------------------------------------------------------------------------------------------
    FIRMWARE: {
        "config": {
            "status_words": ("Read", "Observed", "General knowledge", "**est.**", "**not verified**"),
            "addresses_allow": (),
            "min_register_rows": 35,
            "min_links": 5,
            "min_glossary_rows": 6,
            "nav_contains": (DRAFT,),
        },
        "rows": [
            {"id": "banner", "startswith": "# Open firmware and trustworthy hardware", "contains": ["> **Status: unverified draft.", "Nothing was flashed", "**Not run:**", "2026-11-07", "Not verified, plainly"]},
            {"id": "no-en-dash", "absent": ["–"]},
            {"id": "no-affiliate-links", "urls_min": 20, "url_forbid": r"[?&](ref|aff|affiliate|utm_[a-z]+|tag|partner)="},
            {
                "id": "no-flashing-or-write-commands-in-any-code-block",
                "code": {
                    "require": ["curl", "fwupdmgr"],
                    "forbid": r"\bsudo\b|\bflashrom\b|\bifdtool\b|\bme_cleaner\b|\bnvramtool\b|\bdd\b|\bchmod\b|>\s*/(?:sys|dev|boot)",
                    "ignorecase": True,
                    "bite_bad": ["sudo flashrom -p internal -w rom.bin", "python me_cleaner.py -S image.bin", "echo 1 > /sys/class/x"],
                    "bite_good": ["cat /sys/class/tpm/tpm0/tpm_version_major"],
                },
            },
            {
                "id": "each-vendor-has-a-firmware-and-an-me-line",
                "vendor_sections": {
                    "Novacustom": ["Firmware", "ME"],
                    "System76": ["Firmware", "ME"],
                    "Purism": ["Firmware", "ME"],
                    "Tuxedo": ["ME"],
                    "Tuxedo Computers": ["I could not verify a claim"],
                },
            },
            {"id": "me-words-and-dasharo-modes-are-named", "contains": ["**Absent**", "**Neutralized**", "**Soft-disabled**", "**HAP-disabled**", "Enabled", "Disabled (Soft)", "Disabled (HAP)"]},
            {"id": "register-is-dated", "count_at_least": {"2026-11-07": 8}},
            {"id": "register-names-every-vendor", "start": "## Claims register", "contains": ["Novacustom", "System76", "Purism", "Tuxedo"]},
            {"id": "heads-key-table-matches-the-prerequisites-wording", "contains": ["Heads does NOT support FIDO2 or U2F", "OpenPGP only", "YubiKey 5 Series", "Nitrokey Pro 2", "Nitrokey Storage 2", "Nitrokey 3", "Librem Key"]},
            {
                "id": "page-ends-by-linking-the-firmware-and-hardware-keys-lessons",
                "start": "## Where this goes next",
                "links_in_scope": ["Device-Firmware-Security-Intel-ME-AMD-PSP-MINIX-and-Kernel-Design", "Hardware-Security-Keys-YubiKey-Nitrokey-Smart-Cards-and-PIV"],
                "absent": ["no link"],
            },
            {"id": "no-unwritten-page-wording", "absent": ["not written yet"], "contains": ["Hardware-Security-Keys-YubiKey-Nitrokey-Smart-Cards-and-PIV.md"]},
            {
                "id": "tuxedo-is-a-dated-user-selectable-option-on-one-model",
                "vendor_sections": {"Tuxedo Computers": ["2018-03-14", "InfinityBook Pro 13", "TUXEDO-disables-Intels-Management-Engine.tuxedo"]},
            },
            {
                "id": "tuxedo-wording-pin",
                "absent": ["Ask Tuxedo in writing"],
                "absent_except": [("ships with the ME disabled", 'not "ships with the ME disabled"')],
                "register_row": {"select": ["press release", "Tuxedo"], "first_has": ["2018-03-14"], "second_has": ["TUXEDO-disables"]},
            },
        ],
    },
    # ---- Virtual machines and hypervisors -------------------------------------------------------------------------------------
    VM: {
        "config": {
            "status_words": ("Read", "Observed", "Page read", "General knowledge", "**est.**"),
            "addresses_allow": (r"127\.0\.0\.1",),
            "addresses_require": ("127.0.0.1",),
            "min_register_rows": 25,
            "min_links": 8,
            "min_glossary_rows": 5,
            "nav_contains": (DRAFT,),
        },
        "rows": [
            {"id": "banner", "startswith": "# Virtual machines for beginners", "contains": ["Status: unverified draft", "no hypervisor was installed and no guest was booted", "**Not run:**", "2026-10-31", "Not verified, plainly"]},
            {"id": "pages-that-assume-a-vm-link-the-lesson", "inbound_min": 4},
            {
                "id": "lab-commands-never-bridge-the-guest-onto-a-real-network",
                "code": {
                    "tags": ["bash"],
                    "require": ["qemu-system-x86_64", "-nic user"],
                    "forbid": BRIDGE_FORBID,
                    "bite_bad": ["qemu-system-x86_64 -nic bridge,br=br0", "qemu-system-x86_64 -netdev tap,id=n0"],
                    "bite_good": ["qemu-system-x86_64 -nic user,model=virtio-net-pci"],
                },
            },
            {
                "id": "safety-rule-names-the-three-core-steps",
                "start": "## The safety rule for malware and recon labs",
                "end": "## Free path",
                "contains": ["Isolate the network first", "Snapshot a clean state first", "Never bridge a hostile VM onto your home LAN"],
            },
            {"id": "checksum-before-first-boot", "order": [("sha256sum -c", "qemu-system-x86_64 -accel kvm")], "contains": ["do not boot an image that fails its check"], "regex_present": [r"`[0-9a-f]{64}`"]},
            {
                "id": "vmware-account-dated-with-vendor-and-news-sources",
                "start": "## VMware after Broadcom: a dated account",
                "end": "## The bigger options",
                "contains": ["2023-11-22", "2023-12-11", "May 2024", "2024-11-11", "2025-03-10", "2025-04-10", "BBC News", "Ars Technica", "release notes", "**est.**", "Read"],
                "contains_ci": ["not verified"],
            },
            {"id": "apple-options-from-apples-own-pages", "contains": ["Virtualization framework", "macOS 11.0", "`container`", "macOS 26"]},
            # test_vm_exercise_3_runs_and_the_snapshot_round_trips (needs qemu-img) stays code in the suite
        ],
    },
}
