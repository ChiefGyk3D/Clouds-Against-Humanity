# SPDX-License-Identifier: Apache-2.0
"""The Ansible lesson: it is registered, honest about what was run, local-only, and its playbook really is idempotent.

docs/wiki/Ansible-Configuration-Management-Versus-Provisioning.md teaches a playbook run twice. A broken link, a
missing registration, a remote target in a lab command, a real address, or a claim with no status would each teach
the wrong thing. The run test needs ansible-playbook and is skipped where it is absent.
"""

import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Ansible-Configuration-Management-Versus-Provisioning"
PAGE = WIKI / f"{NAME}.md"
FENCE = re.compile(r"^[ ]*```(\w*)\n(.*?)^[ ]*```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
STATUS_WORDS = ("Read", "Observed", "**est.**")
RECAP = re.compile(r"ok=(\d+)\s+changed=(\d+)")


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def blocks(tag: str) -> list[str]:
    return [textwrap.dedent(b) for t, b in FENCE.findall(text()) if t == tag]


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    rows = [line for line in reg.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def rows_missing_status(body: str) -> list[str]:
    return [r[0] for r in register_rows(body) if not any(w in r[-1] for w in STATUS_WORDS)]


def remote_targets(commands: str) -> list[str]:
    """Lines that would aim a lab command at a machine other than the local one."""
    return [l for l in commands.splitlines() if re.search(r"\bansible_host=|\bansible_ssh_|\bssh\s+\S+@", l)]


def test_the_page_exists_and_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Ansible: configuration management versus provisioning")
    assert "Status: unverified draft" in body
    assert "2026-11-07" in body and "**Not run:**" in body
    assert "ansible-core 2.22.0" in body


def test_every_linked_wiki_page_exists():
    links = set(LINK.findall(text()))
    assert len(links) >= 8, "the guard collected too few links"
    missing = sorted(t for t in links if not (WIKI / f"{t}.md").exists())
    assert not missing, missing


def test_the_lesson_is_registered_everywhere():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    assert f"page: {NAME}," in nav and 'status: "draft"' in nav.split(f"page: {NAME},")[1].split("\n")[0]
    for special in ("Contents.md", "_Sidebar.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [l for l in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in l]
    assert len(rows) >= 5, "expected glossary rows for the new terms"


def test_glossary_rows_point_at_real_headings():
    heads = {re.sub(r"[^a-z0-9-]", "", re.sub(r"[^a-z0-9 -]", "", h.lower()).strip().replace(" ", "-")) for h in re.findall(r"^#+ (.+)$", text(), re.MULTILINE)}
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= heads, sorted(anchors - heads)


def test_no_addresses_and_no_em_dashes():
    body = text()
    assert set(ADDR.findall(body)) <= {"127.0.0.1"}, set(ADDR.findall(body))
    assert "—" not in body


def test_the_address_guard_bites():
    assert not set(ADDR.findall("ping 192.0.2.7")) <= {"127.0.0.1"}


def test_the_lab_commands_stay_on_the_local_machine():
    cmds = "\n".join(blocks("bash") + blocks("ini"))
    assert "ansible_connection=local" in cmds and "ansible-playbook" in cmds, "the guard collected nothing"
    assert not remote_targets(cmds)


def test_the_remote_guard_bites():
    assert remote_targets("web ansible_host=203.0.113.9")
    assert remote_targets("ssh admin@box")
    assert not remote_targets("localhost ansible_connection=local")


def test_check_mode_comes_before_the_real_repair_run():
    ex = text().split("### Exercise 4")[1].split("### Exercise 5")[0]
    assert ex.index("--check --diff") < ex.rindex("ansible-playbook -i inventory.ini site.yml\n")


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(text())


def test_the_register_guard_bites():
    bad = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n"
    assert rows_missing_status(bad) == ["X"]


def test_the_estimated_claims_are_marked_in_the_body():
    body = text()
    assert body.count("est.") >= 10, "unverified claims must be marked"


@pytest.mark.skipif(shutil.which("ansible-playbook") is None, reason="ansible-playbook is not installed")
def test_the_playbook_is_idempotent_and_the_bad_task_is_not(tmp_path):
    inventory = next(b for b in blocks("ini") if "[lab]" in b)
    playbook = next(b for b in blocks("yaml") if "Make a small config directory" in b)
    bad = next(b for b in re.findall(r"cat > bad\.yml <<'EOF'\n(.*?)\nEOF", "\n".join(blocks("bash")), re.DOTALL))
    (tmp_path / "inventory.ini").write_text(inventory, encoding="utf-8")
    (tmp_path / "site.yml").write_text(playbook, encoding="utf-8")
    (tmp_path / "bad.yml").write_text(bad, encoding="utf-8")

    def run(name: str) -> tuple[int, int]:
        out = subprocess.run(["ansible-playbook", "-i", "inventory.ini", name], cwd=tmp_path, capture_output=True, text=True, timeout=120, check=False)
        assert out.returncode == 0, out.stdout + out.stderr
        m = RECAP.search(out.stdout)
        assert m, out.stdout
        return int(m.group(1)), int(m.group(2))

    assert run("site.yml") == (3, 3)
    assert run("site.yml") == (3, 0)
    assert run("bad.yml")[1] == 1 and run("bad.yml")[1] == 1
    assert (tmp_path / "sandbox" / "bad.conf").read_text(encoding="utf-8").count("retries = 3") == 2
