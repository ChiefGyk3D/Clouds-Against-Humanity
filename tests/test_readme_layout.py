"""The README's layout block and script list match the tree.

A layout that lists last month's directories sends a new reader to the wrong
place, so these tests fail when a script, a top-level directory or a module or
stack directory exists without a mention, and when the README names a script
that is gone. A script that deliberately has no README line goes in
UNLISTED_SCRIPTS with the reason, so the exception is visible in review.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text()

# script path (relative to the repository root) -> why the README does not list it
UNLISTED_SCRIPTS: dict[str, str] = {}

# Top-level directories that exist in a working copy but are not part of the repository.
UNTRACKED_DIRS = {".git", ".venv", ".claude", ".pytest_cache", ".ruff_cache", "__pycache__"}


def layout_block() -> str:
    match = re.search(r"^## Layout\n+```\n(.*?)\n```", README, re.DOTALL | re.MULTILINE)
    assert match, "README.md has no fenced block under '## Layout'"
    return match.group(1)


def tracked_top_level_dirs() -> set[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split("\n")
        return {line.split("/", 1)[0] for line in out if "/" in line}
    except (OSError, subprocess.CalledProcessError):
        return {
            p.name
            for p in ROOT.iterdir()
            if p.is_dir() and p.name not in UNTRACKED_DIRS
        }


def scripts() -> list[str]:
    found = []
    for path in sorted((ROOT / "scripts").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            found.append(path.relative_to(ROOT).as_posix())
    return found


def test_every_script_is_in_the_readme_or_has_a_reason():
    missing = [
        s for s in scripts() if s not in README and s not in UNLISTED_SCRIPTS
    ]
    assert not missing, f"scripts not mentioned in README.md: {missing}"


def test_unlisted_script_reasons_are_current():
    stale = [s for s in UNLISTED_SCRIPTS if s not in scripts() or s in README]
    assert not stale, f"UNLISTED_SCRIPTS entries to remove: {stale}"
    assert all(reason.strip() for reason in UNLISTED_SCRIPTS.values())


def test_the_readme_names_no_script_that_is_gone():
    named = set(re.findall(r"\bscripts/[A-Za-z0-9_./-]*[A-Za-z0-9_]\.(?:py|sh)\b", README))
    gone = sorted(n for n in named if not (ROOT / n).is_file())
    assert not gone, f"README.md names scripts that do not exist: {gone}"


def test_every_top_level_directory_is_in_the_layout_block():
    block = layout_block()
    missing = [
        d
        for d in sorted(tracked_top_level_dirs())
        if not re.search(rf"^\s+{re.escape(d)}/", block, re.MULTILINE)
    ]
    assert not missing, f"top-level directories missing from the README layout: {missing}"


# Layout convention for directories below modules/ and stacks/: a directory is
# covered when the layout block names its full path (`modules/aws/vpc`), or when
# a brace form names it under its parent (`modules/aws/{vpc,firewall}` covers
# modules/aws/vpc and modules/aws/firewall, and the parent modules/aws). Naming
# only a parent covers the parent, never the directories under it.
BRACE = re.compile(r"((?:modules|stacks)(?:/[\w.-]+)*)/\{([^}]*)\}")
PLAIN = re.compile(r"(?<![\w./{-])((?:modules|stacks)(?:/[\w.-]+)*)")


def covered_paths(block: str) -> set[str]:
    covered = set()
    for prefix, names in BRACE.findall(block):
        parts = prefix.split("/")
        covered.update("/".join(parts[:n]) for n in range(1, len(parts) + 1))
        covered.update(f"{prefix}/{n.strip()}" for n in names.split(",") if n.strip())
    stripped = BRACE.sub("", block)
    covered.update(m.rstrip("/") for m in PLAIN.findall(stripped))
    return covered


def module_and_stack_dirs(root: Path) -> list[str]:
    """Every directory under modules/ and stacks/ that is a module, a stack or a
    grouping directory above them (provider, site). Stops at a directory that
    holds .tf files, and skips tests/ and hidden directories."""
    found: list[str] = []

    def walk(directory: Path) -> None:
        for child in sorted(directory.iterdir()):
            if not child.is_dir() or child.name == "tests" or child.name.startswith("."):
                continue
            found.append(child.relative_to(root).as_posix())
            if not any(child.glob("*.tf")):
                walk(child)

    for top in ("modules", "stacks"):
        if (root / top).is_dir():
            walk(root / top)
    return found


def undocumented_dirs(root: Path, block: str) -> list[str]:
    covered = covered_paths(block)
    return [d for d in module_and_stack_dirs(root) if d not in covered]


def test_every_module_and_stack_directory_is_in_the_layout_block():
    missing = undocumented_dirs(ROOT, layout_block())
    assert not missing, f"missing from the README layout: {missing}"


def test_the_layout_check_reaches_nested_directories(tmp_path):
    for d in ("modules/aws/vpc", "stacks/aws/00-foundation", "stacks/aws/20-telemetry"):
        (tmp_path / d).mkdir(parents=True)
        (tmp_path / d / "main.tf").write_text("")
    (tmp_path / "stacks/aws/20-telemetry/tests").mkdir()
    block = "modules/aws/{vpc}\nstacks/aws/{00-foundation}\n"
    assert undocumented_dirs(tmp_path, block) == ["stacks/aws/20-telemetry"]
    # naming only the parent does not cover its children
    assert undocumented_dirs(tmp_path, "modules/aws/\nstacks/aws/\n") == [
        "modules/aws/vpc",
        "stacks/aws/00-foundation",
        "stacks/aws/20-telemetry",
    ]
    assert undocumented_dirs(tmp_path, block + "stacks/aws/20-telemetry/  x\n") == []
