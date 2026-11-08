"""CI wiring: one pinned GYST commit everywhere, and a CI green that skips only tofu."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
GYST = "ChiefGyk3D/git-your-ship-together/"
REF = re.compile(
    r"uses:\s*" + re.escape(GYST) + r"(?P<path>\S+)@(?P<sha>\S+)(?P<rest>.*)$"
)
EXPECTED_PATTERNS = ["docs/**", "tests/**", "*.md"]
FORBIDDEN_PATTERNS = (".github", "stacks", "modules", "labs")


def gyst_refs(files: dict[str, str]) -> list[tuple[str, str, str, str]]:
    """(file, path, sha, trailing comment) for every GYST reference."""
    found = []
    for name, text in files.items():
        for line in text.splitlines():
            match = REF.search(line)
            if match:
                found.append((name, match["path"], match["sha"], match["rest"]))
    return found


def pin_problems(files: dict[str, str]) -> list[str]:
    refs = gyst_refs(files)
    problems = [] if refs else ["no GYST reference collected"]
    for name, path, sha, rest in refs:
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            problems.append(f"{name}: {path} is not pinned to a full commit")
        if not re.fullmatch(r"\s*#\s*v\d+\.\d+\.\d+(\s.*)?", rest):
            problems.append(f"{name}: {path} has no version comment")
    if len({sha for _, _, sha, _ in refs}) > 1:
        problems.append("GYST references use more than one commit")
    return problems


def gate_problems(text: str) -> list[str]:
    jobs = yaml.safe_load(text)["jobs"]
    green = [j for j in jobs.values() if j.get("name") == "CI green"]
    if len(green) != 1:
        return ["expected exactly one job named CI green"]
    problems = []
    gate = next(
        (s for s in green[0].get("steps", []) if "/actions/ci-gate@" in s.get("uses", "")),
        None,
    )
    if gate is None or not gate["uses"].startswith(GYST):
        problems.append("CI green does not use the ci-gate action")
    else:
        with_ = gate.get("with", {})
        if str(with_.get("skippable-jobs", "")).split() != ["tofu"]:
            problems.append("tofu must be the only skippable job")
        if with_.get("classifier-job") != "classify":
            problems.append("classifier-job must be classify")
    classify = jobs.get("classify", {})
    step = next(
        (s for s in classify.get("steps", []) if "/actions/classify-changes@" in s.get("uses", "")),
        None,
    )
    if step is None:
        problems.append("classify job does not use classify-changes")
    else:
        patterns = step["with"]["docs-only-patterns"].split()
        if patterns != EXPECTED_PATTERNS:
            problems.append(f"docs-only patterns are {patterns}")
        for pattern in patterns:
            if pattern.startswith(FORBIDDEN_PATTERNS):
                problems.append(f"docs-only pattern {pattern} covers code")
    return problems


def workflow_texts() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(WORKFLOWS.glob("*.yml"))}


def test_every_gyst_reference_is_pinned_to_one_commit_with_a_version_comment():
    files = workflow_texts()
    assert len(gyst_refs(files)) >= 5
    assert pin_problems(files) == []


def test_ci_green_uses_the_gate_and_only_tofu_may_be_skipped():
    assert gate_problems(workflow_texts()["ci.yml"]) == []


def test_the_guards_bite():
    files = workflow_texts()
    sha = gyst_refs(files)[0][2]
    other = {k: v.replace(sha, "0" * 40, 1) for k, v in files.items()}
    assert pin_problems(other)
    no_comment = {k: v.replace("# v1.", "# x1.") for k, v in files.items()}
    assert pin_problems(no_comment)
    assert pin_problems({}) == ["no GYST reference collected"]
    ci = files["ci.yml"]
    assert gate_problems(ci.replace("docs/**\n", "stacks/**\n            docs/**\n", 1))
    assert gate_problems(ci.replace("skippable-jobs: tofu", "skippable-jobs: tofu python"))
    assert gate_problems(ci.replace("name: CI green", "name: CI ok"))
