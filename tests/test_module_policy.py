"""Repository-wide rules the per-module tofu tests cannot enforce on their own.

A provider connector module must reuse the shared bootstrap, and CI must run
the tests of every module, so a new provider cannot quietly skip either.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP = "twingate-bootstrap"


def tofu_dirs():
    found = []
    for parent in ("modules", "stacks"):
        for d in sorted((ROOT / parent).iterdir()):
            if d.is_dir() and list(d.glob("*.tf")):
                found.append(f"{parent}/{d.name}")
    return found


def ci_directories():
    text = (ROOT / ".github/workflows/ci.yml").read_text()
    match = re.search(r'directories:\s*"([^"]+)"', text)
    assert match, "ci.yml has no directories: list"
    return match.group(1).split()


def test_ci_runs_every_module_and_stack():
    missing = sorted(set(tofu_dirs()) - set(ci_directories()))
    assert not missing, f"not run by CI (add to directories in ci.yml): {missing}"


def test_ci_lists_no_directory_that_does_not_exist():
    gone = sorted(d for d in ci_directories() if d not in tofu_dirs())
    assert not gone, f"ci.yml lists directories with no .tf files: {gone}"


def bootstrap_callers():
    callers = []
    for rel in tofu_dirs():
        if not rel.startswith("modules/") or rel.endswith(BOOTSTRAP):
            continue
        main = (ROOT / rel / "main.tf").read_text()
        if re.search(r'source\s*=\s*"\.\./' + BOOTSTRAP + '"', main):
            callers.append((rel, main))
    return callers


def test_at_least_one_provider_uses_the_bootstrap():
    assert bootstrap_callers(), "no provider module calls the shared bootstrap"


def test_a_bootstrap_caller_passes_the_shared_boot_data_straight_to_the_machine():
    for rel, main in bootstrap_callers():
        name = re.search(r'module\s+"([^"]+)"\s*\{[^}]*?source\s*=\s*"\.\./' + BOOTSTRAP, main, re.DOTALL).group(1)
        assert re.search(r"(?m)^\s*(user_data|custom_data|metadata_startup_script)\s*=\s*module\." + name + r"\.user_data\s*$", main), \
            f"{rel}: the machine's boot data must be module.{name}.user_data, unmodified"
        assert "templatefile" not in main, f"{rel}: a provider module must not render its own cloud-init"
        assert not (ROOT / rel / "cloud-init.yaml.tftpl").exists(), f"{rel}: private copy of the cloud-init"
        assert not re.search(r'(?m)^resource\s+"twingate_', main), f"{rel}: Twingate resources belong in the bootstrap"


def test_the_bootstrap_template_is_the_only_cloud_init():
    found = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.glob("modules/**/cloud-init*") if ".terraform" not in p.parts)
    assert found == [f"modules/{BOOTSTRAP}/cloud-init.yaml.tftpl"], found
