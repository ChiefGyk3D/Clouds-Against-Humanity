"""The DMZ lesson: its exercise output is real, the tests and files it cites exist, and it is registered.

docs/wiki/The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md teaches from the unbuilt edge design and
cites tests as the check for each hardening item. A cited test that does not exist, or an exercise whose
shown output is not what the commands print, teaches the wrong thing.
"""

import re
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md"
PAGE = WIKI / NAME
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
PATH = re.compile(r"`((?:stacks|modules|scripts|tests|\.spacelift|docs/stages|docs/superpowers)/[A-Za-z0-9_./-]+)`")
PYTEST_ID = re.compile(r"`(tests/[A-Za-z0-9_]+\.py)::([A-Za-z0-9_]+)`")
TFTEST = re.compile(r"`([a-z0-9_]+)`")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def blocks() -> list[str]:
    return [b for t, b in FENCE.findall(text()) if t == "text"]


def commands() -> list[str]:
    found = [b for b in blocks() if b.startswith("grep ")]
    assert len(found) == 1, "expected one command block"
    return [ln for ln in found[0].splitlines() if ln.strip()]


def shown() -> str:
    found = [b for b in blocks() if b.startswith("93:")]
    assert len(found) == 1, "expected one output block"
    return found[0].strip()


def run_all(cmds: list[str]) -> str:
    out = []
    for cmd in cmds:
        argv = shlex.split(cmd)  # no shell: a pipe or a semicolon would be a plain argument
        assert argv[0] == "grep"
        done = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
        out.append(done.stdout.rstrip("\n"))
    return "\n".join(out).strip()


def test_the_exercise_prints_what_the_page_shows():
    assert run_all(commands()) == shown()


def test_the_guard_bites_on_a_wrong_output():
    assert run_all(commands()) != shown().replace("policy drop", "policy accept")


def test_every_repository_path_the_page_cites_exists():
    cited = sorted(set(PATH.findall(text())))
    assert len(cited) >= 8, "the guard collected too little"
    missing = [c for c in cited if not (ROOT / c.rstrip("/")).exists()]
    assert not missing, missing


def test_every_pytest_the_page_names_exists():
    ids = PYTEST_ID.findall(text())
    assert len(ids) >= 5, "the guard collected too little"
    for file, name in ids:
        assert re.search(rf"(?m)^def {name}\(", (ROOT / file).read_text(encoding="utf-8")), (file, name)


def test_every_tofu_test_the_page_names_exists():
    tests = (ROOT / "modules/edge-host/tests/edge-host.tftest.hcl").read_text() + (ROOT / "stacks/50-edge/tests/edge.tftest.hcl").read_text()
    named = [n for n in TFTEST.findall(text()) if "_" in n and not n.startswith("test_") and n.islower() and "." not in n]
    wanted = [n for n in named if n in {
        "no_ports_means_no_accept_rules_and_a_default_drop_table",
        "public_and_restricted_ports_render_into_the_host_firewall",
        "the_user_data_has_no_ssh_path",
        "the_droplet_has_no_admin_path_and_no_public_v6",
        "the_reboot_time_defaults_to_the_services_slot_in_eastern",
        "no_service_is_installed",
        "every_public_inbound_rule_is_ipv4_only",
        "enabled_opens_reticulum_and_mqtt_only_so_i2pd_and_iperf3_stay_closed",
    }]
    assert len(set(wanted)) == 8, wanted
    for n in set(wanted):
        assert f'run "{n}"' in tests, n


def test_the_page_says_the_edge_is_design_only():
    t = text()
    assert "design only" in t.lower()
    assert "not approved" in t
    assert "written from reading" in t
    assert "issue #325" in t and "(issue #325" in t


def test_the_page_names_the_patch_lesson_without_linking_it():
    assert not re.search(r"\]\([^)]*(?:325|[Pp]atch-[Mm]anagement)[^)]*\)", text())


def test_the_page_uses_no_real_address():
    for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text()):
        assert ip in {"169.254.169.254"}, ip


def test_the_page_is_registered_everywhere_pages_are():
    for name in ("_Sidebar.md", "Contents.md", "Reading-Order.md", "Glossary.md", "_nav.yaml"):
        assert NAME[:-3] in (WIKI / name).read_text(encoding="utf-8") or NAME in (WIKI / name).read_text(encoding="utf-8"), name


CHECKLIST = WIKI / "DMZ-Hardening-Checklist.md"


def checklist() -> str:
    return CHECKLIST.read_text(encoding="utf-8")


def test_the_checklist_cites_only_tests_and_paths_that_exist():
    t = checklist()
    paths = sorted(set(PATH.findall(t)))
    assert len(paths) >= 5, "the guard collected too little"
    assert not [c for c in paths if not (ROOT / c.rstrip("/")).exists()]
    ids = PYTEST_ID.findall(t)
    assert len(ids) >= 5, "the guard collected too little"
    for file, name in ids:
        assert re.search(rf"(?m)^def {name}\(", (ROOT / file).read_text(encoding="utf-8")), (file, name)
    tofu = (ROOT / "modules/edge-host/tests/edge-host.tftest.hcl").read_text() + (ROOT / "stacks/50-edge/tests/edge.tftest.hcl").read_text()
    named = {n for n in TFTEST.findall(t) if n.islower() and n.count("_") >= 3 and not n.startswith("test_")}
    assert len(named) >= 6, named
    assert not [n for n in named if f'run "{n}"' not in tofu]


def test_every_checklist_row_names_a_check_or_says_none():
    rows = [ln for ln in checklist().split("## What to log")[0].splitlines() if ln.startswith("| [ ]")]
    assert len(rows) >= 12, "the guard collected too little"
    for ln in rows:
        last = ln.rstrip().rstrip("|").rsplit("|", 1)[-1]
        assert "`" in last or "**None" in last, ln


def test_the_checklist_guard_bites_on_a_row_with_neither():
    bad = "| [ ] | Something | Design | we thought about it |"
    last = bad.rstrip().rstrip("|").rsplit("|", 1)[-1]
    assert not ("`" in last or "**None" in last)


def test_the_checklist_is_honest_about_the_edge_and_leaks_nothing():
    t = checklist()
    assert "design only" in t.lower() and "not approved" in t and "written from reading" in t
    assert not re.search(r"\]\([^)]*(?:325|[Pp]atch-[Mm]anagement)[^)]*\)", t)
    for ip in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", t):
        assert ip in {"169.254.169.254"}, ip


def test_the_checklist_is_registered_and_the_lesson_still_names_its_rows():
    for name in ("_Sidebar.md", "Contents.md", "Reading-Order.md", "_nav.yaml"):
        assert "DMZ-Hardening-Checklist" in (WIKI / name).read_text(encoding="utf-8"), name
