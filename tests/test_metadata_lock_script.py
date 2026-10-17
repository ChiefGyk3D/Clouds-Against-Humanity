"""Hermetic tests for the metadata-lock script in the connector cloud-init.

The script is extracted from modules/twingate-bootstrap/cloud-init.yaml.tftpl
(undoing the template's `$$` escaping and the YAML block indentation) and run
with a fake `nft` and a fake `id` first on PATH, inside a temporary directory.
The real nft is never invoked for a change: the one optional syntax check runs
`nft -c` (check only) in a throwaway user and network namespace and skips when
that is not possible.
"""

import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "modules/twingate-bootstrap/cloud-init.yaml.tftpl"
SCRIPT_PATH = "/usr/local/sbin/cah-metadata-lock"
BASH = shutil.which("bash")


def _run(args, **kwargs):
    """subprocess.run that reports the exit code instead of raising."""
    return subprocess.run(args, check=False, **kwargs)


def extract_script(template_text: str, path: str = SCRIPT_PATH) -> str:
    """The write_files content for `path`, as it lands on the machine."""
    lines = template_text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == f"- path: {path}"), None
    )
    assert start is not None, f"{path} is not written by the template"
    body: list[str] = []
    in_content = False
    for line in lines[start + 1 :]:
        if not in_content:
            if line.strip() == "content: |":
                in_content = True
            continue
        # The block scalar ends at the first line indented less than 6 spaces
        # that is not blank (the next "  - path:" entry or a %{ directive).
        if line.strip() and not line.startswith("      "):
            break
        body.append(line[6:] if line.startswith("      ") else "")
    assert body, f"{path} has no content"
    text = "\n".join(body).rstrip("\n") + "\n"
    # tftpl: "$$" renders as "$"; "${...}" would be an interpolation.
    assert "${" not in text, "an unescaped template interpolation reached the script"
    return text.replace("$$", "$")


def make_fakes(tmp: Path, agent_uid: str | None) -> tuple[Path, Path, Path]:
    bindir = tmp / "bin"
    bindir.mkdir()
    calls = tmp / "calls.log"
    stdin_copy = tmp / "nft.stdin"
    reader = (
        'while IFS= read -r line || [ -n "$line" ]; do '
        f'printf \'%s\\n\' "$line"; done > "{stdin_copy}"\n'
    )
    (bindir / "nft").write_text(
        f"#!{BASH}\n"
        f'echo "nft $*" >> "{calls}"\n'
        # Only shell builtins: PATH holds nothing but these fakes.
        + reader
    )
    if agent_uid is None:
        id_body = f'echo "id $*" >> "{calls}"\nexit 1\n'
    else:
        id_body = (
            f'echo "id $*" >> "{calls}"\n'
            f'if [ "$*" = "-u do-agent" ]; then echo {agent_uid}; exit 0; fi\n'
            "exit 1\n"
        )
    (bindir / "id").write_text(f"#!{BASH}\n{id_body}")
    for f in bindir.iterdir():
        f.chmod(f.stat().st_mode | stat.S_IXUSR)
    return bindir, calls, stdin_copy


def run_script(tmp: Path, agent_uid: str | None):
    script = tmp / "cah-metadata-lock"
    script.write_text(extract_script(TEMPLATE.read_text(encoding="utf-8")))
    bindir, calls, stdin_copy = make_fakes(tmp, agent_uid)
    env = {"PATH": str(bindir), "HOME": str(tmp)}
    proc = _run(
        [BASH, str(script)], env=env, capture_output=True, text=True, timeout=30
    )
    call_lines = calls.read_text().splitlines() if calls.exists() else []
    ruleset = stdin_copy.read_text() if stdin_copy.exists() else ""
    return proc, call_lines, ruleset


pytestmark = pytest.mark.skipif(BASH is None, reason="bash is not available")


def test_extraction_finds_a_real_script():
    text = extract_script(TEMPLATE.read_text(encoding="utf-8"))
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    assert "169.254.169.254" in text


def test_extraction_negative_case_missing_path_is_an_error():
    with pytest.raises(AssertionError):
        extract_script(TEMPLATE.read_text(encoding="utf-8"), "/usr/local/sbin/nope")


def test_extraction_negative_case_rejects_an_interpolation():
    fake = "  - path: /x\n    content: |\n      echo ${oops}\n"
    with pytest.raises(AssertionError):
        extract_script(fake, "/x")


def test_do_agent_present_is_allowed_next_to_root(tmp_path):
    proc, _calls, ruleset = run_script(tmp_path, "998")
    assert proc.returncode == 0, proc.stderr
    assert "meta skuid != { 0, 998 }" in ruleset
    assert "uids: 0, 998" in proc.stdout


def test_do_agent_missing_leaves_only_root_and_exits_zero(tmp_path):
    proc, _calls, ruleset = run_script(tmp_path, None)
    assert proc.returncode == 0, proc.stderr
    assert "meta skuid != { 0 }" in ruleset
    assert "," not in re.search(r"skuid != \{([^}]*)\}", ruleset).group(1)


def test_ruleset_is_idempotent_and_self_contained(tmp_path):
    _proc, _calls, ruleset = run_script(tmp_path, "998")
    lines = [line.strip() for line in ruleset.splitlines()]
    first = lines.index("table inet cah_metadata")
    delete = lines.index("delete table inet cah_metadata")
    full = next(i for i, line in enumerate(lines) if line == "table inet cah_metadata {")
    assert first < delete < full
    assert "ip daddr 169.254.169.254 meta skuid != { 0, 998 } reject with icmp type admin-prohibited" in lines
    assert "type filter hook output priority 0; policy accept;" in lines
    # No flush of the whole ruleset: other rules are never touched.
    assert "flush ruleset" not in ruleset


def test_only_the_fake_nft_and_id_are_invoked(tmp_path):
    proc, calls, _ruleset = run_script(tmp_path, "998")
    assert proc.returncode == 0, proc.stderr
    assert calls == ["id -u do-agent", "nft -f -"]


def test_a_failing_nft_fails_the_script(tmp_path):
    script = tmp_path / "s"
    script.write_text(extract_script(TEMPLATE.read_text(encoding="utf-8")))
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "nft").write_text(f"#!{BASH}\nexit 1\n")
    (bindir / "id").write_text(f"#!{BASH}\nexit 1\n")
    for f in bindir.iterdir():
        f.chmod(f.stat().st_mode | stat.S_IXUSR)
    proc = _run(
        [BASH, str(script)],
        env={"PATH": str(bindir)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode != 0


def _can_check_syntax() -> bool:
    nft, unshare = shutil.which("nft"), shutil.which("unshare")
    if not nft or not unshare:
        return False
    probe = _run(
        [unshare, "-rn", nft, "-c", "-f", "-"],
        input="table inet cah_probe\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    return probe.returncode == 0


@pytest.mark.skipif(not _can_check_syntax(), reason="unshare -rn nft -c is unavailable here")
def test_generated_ruleset_passes_nft_syntax_check(tmp_path):
    _proc, _calls, ruleset = run_script(tmp_path, "998")
    check = _run(
        [shutil.which("unshare"), "-rn", shutil.which("nft"), "-c", "-f", "-"],
        input=ruleset,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert check.returncode == 0, check.stderr
    # Negative case: the checker really rejects a broken ruleset.
    bad = _run(
        [shutil.which("unshare"), "-rn", shutil.which("nft"), "-c", "-f", "-"],
        input=ruleset.replace("skuid", "skuidd"),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert bad.returncode != 0


def test_template_gates_the_lock_on_metadata_lock():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert len(re.findall(r"%\{ if metadata_lock ~\}", text)) == 3
    assert len(re.findall(r"%\{ endif ~\}", text)) == 3
