# SPDX-License-Identifier: Apache-2.0
"""Structure of .github/workflows/growth-chart.yml (issue #294).

The growth chart (redrawn every three hours) is rendered in one job that can only read, and published
by a second job that can write but runs nothing it did not validate. These tests
read the workflow as data and pin the properties that make that true: permissions
per job, commit-pinned actions with a version comment, no expression inside a run
script, no secrets in the publish job, no bare force push, a main-only guard, and
hash-pinned plotting dependencies. Each rule is a function over text so a negative
case can prove the rule bites.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "growth-chart.yml"
REQUIREMENTS = ROOT / "scripts" / "growth-chart-requirements.txt"
PUBLISH = ROOT / "scripts" / "publish_metrics_branch.sh"
IMAGE_URL = "https://raw.githubusercontent.com/ChiefGyk3D/Clouds-Against-Humanity/metrics/repo-growth.png"

USES_RE = re.compile(r"^\s*-?\s*uses:\s*(\S+)(.*)$")
PINNED_RE = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
VERSION_RE = re.compile(r"^\s*#\s*v\d+\.\d+\.\d+\b")


def load(text: str | None = None) -> dict:
    return yaml.safe_load(text if text is not None else WORKFLOW.read_text())


def triggers(doc: dict) -> dict:
    return doc.get("on", doc.get(True))


def unpinned_uses(text: str) -> list[str]:
    bad = []
    for line in text.splitlines():
        m = USES_RE.match(line)
        if m and not (PINNED_RE.match(m.group(1)) and VERSION_RE.match(m.group(2))):
            bad.append(line.strip())
    return bad


def run_scripts(doc: dict):
    for name, job in doc["jobs"].items():
        for step in job["steps"]:
            if "run" in step:
                yield name, step["run"]


def expressions_in_run(doc: dict) -> list[str]:
    return [f"{job}: {script}" for job, script in run_scripts(doc) if "${{" in script]


def bare_force(text: str) -> list[str]:
    return re.findall(r"--force(?!-with-lease=)\S*|\bpush\b[^\n]*\s-\w*f\b|\bpush\b[^\n]*\s\+\S", text)


@pytest.fixture(scope="module")
def doc():
    return load()


def test_the_workflow_exists_and_has_two_jobs(doc):
    assert set(doc["jobs"]) == {"render", "publish"}


def test_triggers_are_a_three_hourly_schedule_off_the_hour_and_a_manual_run(doc):
    on = triggers(doc)
    assert set(on) == {"schedule", "workflow_dispatch"}
    crons = [s["cron"] for s in on["schedule"]]
    assert len(crons) == 1
    minute, hour, dom, month, dow = crons[0].split()
    assert minute.isdigit() and minute not in {"0", "00", "30", "15", "45"}
    assert hour == "*/3" and (dom, month, dow) == ("*", "*", "*")


def test_workflow_default_permissions_are_empty_and_jobs_name_their_own(doc):
    assert doc["permissions"] == {}
    assert doc["jobs"]["render"]["permissions"] == {"contents": "read"}
    assert doc["jobs"]["publish"]["permissions"] == {"contents": "write"}


def test_publish_waits_for_render(doc):
    assert doc["jobs"]["publish"]["needs"] == "render" or doc["jobs"]["publish"]["needs"] == ["render"]


def test_both_jobs_are_guarded_to_main_in_this_repository(doc):
    for name in ("render", "publish"):
        cond = doc["jobs"][name]["if"]
        assert "github.ref == 'refs/heads/main'" in cond, name
        assert "github.repository == 'ChiefGyk3D/Clouds-Against-Humanity'" in cond, name


def test_concurrency_group_queues_runs_instead_of_cancelling(doc):
    conc = doc["concurrency"]
    assert conc["group"] and conc["cancel-in-progress"] is False


def test_every_action_is_pinned_by_commit_with_a_version_comment():
    text = WORKFLOW.read_text()
    assert "uses:" in text  # collect loosely: something must have been collected
    assert unpinned_uses(text) == []


@pytest.mark.parametrize(
    "line",
    [
        "      - uses: actions/checkout@main",
        "      - uses: actions/checkout@v7",
        "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b # v7.0.1",
        "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # latest",
    ],
)
def test_the_pin_rule_bites(line):
    assert unpinned_uses(line)


def test_every_checkout_drops_its_credentials(doc):
    seen = 0
    for job in doc["jobs"].values():
        for step in job["steps"]:
            if str(step.get("uses", "")).startswith("actions/checkout@"):
                seen += 1
                assert step["with"]["persist-credentials"] is False
    assert seen == 2


def test_no_expression_inside_a_run_script(doc):
    assert expressions_in_run(doc) == []


def test_the_expression_rule_bites():
    bad = load("on: push\njobs:\n  j:\n    runs-on: x\n    steps:\n      - run: echo ${{ github.head_ref }}\n")
    assert expressions_in_run(bad)


def test_publish_has_no_secrets_and_only_the_default_token(doc):
    text = WORKFLOW.read_text()
    assert not re.search(r"\$\{\{[^}]*\bsecrets\b", text)
    assert "secrets:" not in text and "inherit" not in text
    publish = doc["jobs"]["publish"]
    for step in publish["steps"]:
        for value in (step.get("env") or {}).values():
            if "${{" in str(value):
                assert str(value).replace(" ", "") in {"${{github.token}}", "${{needs.render.outputs.tip}}"}


def test_render_never_pushes_and_publish_never_installs_packages(doc):
    render = "\n".join(s for n, s in run_scripts(doc) if n == "render")
    publish = "\n".join(s for n, s in run_scripts(doc) if n == "publish")
    assert "git push" not in render and "publish_metrics_branch" not in render
    assert "pip" not in publish and "matplotlib" not in publish


def test_no_bare_force_push_anywhere():
    for path in (WORKFLOW, PUBLISH):
        assert bare_force(path.read_text()) == [], path
    # history is kept and the push is an exact lease: the only "--force" spelling allowed
    forces = re.findall(r"--force\S*", PUBLISH.read_text())
    assert forces and all(re.match(r'--force-with-lease="?refs/heads/metrics:', f) for f in forces), forces


@pytest.mark.parametrize("text", ["git push --force origin x", "git push -f origin x", "git push origin +x:y", "git push --force-with-lease origin x"])
def test_the_force_rule_bites(text):
    assert bare_force(text)


def test_the_render_job_uploads_a_short_lived_artifact_and_fails_if_empty(doc):
    uploads = [s for s in doc["jobs"]["render"]["steps"] if str(s.get("uses", "")).startswith("actions/upload-artifact@")]
    assert len(uploads) == 1
    w = uploads[0]["with"]
    assert w["if-no-files-found"] == "error" and int(w["retention-days"]) <= 3


def test_both_jobs_validate_the_bundle(doc):
    for name in ("render", "publish"):
        scripts = "\n".join(s for n, s in run_scripts(doc) if n == name)
        assert "--verify-bundle" in scripts or "publish_metrics_branch" in scripts, name


def test_dependencies_are_installed_only_with_hashes_from_the_pinned_file(doc):
    render = "\n".join(s for n, s in run_scripts(doc) if n == "render")
    assert "--require-hashes" in render and "growth-chart-requirements.txt" in render
    assert not re.search(r"pip\S*\s+install\s+(?!.*-r)", render.replace("\\\n", " "))


def test_the_requirements_file_pins_every_package_with_hashes():
    lines = REQUIREMENTS.read_text().replace("\\\n", " ").splitlines()
    pins = [ln for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    assert any(ln.startswith("matplotlib==") for ln in pins)
    for ln in pins:
        assert re.match(r"^[A-Za-z0-9_.-]+==[\w.]+(\s+--hash=sha256:[0-9a-f]{64})+$", ln.strip()), ln


def test_the_job_timeouts_are_set(doc):
    for job in doc["jobs"].values():
        assert 0 < job["timeout-minutes"] <= 15


# -- the pages point at the metrics branch -----------------------------------------


@pytest.mark.parametrize("page", ["README.md", "docs/wiki/Home.md", "docs/wiki/Repository-Growth.md"])
def test_pages_reference_the_chart_from_the_metrics_branch(page):
    text = (ROOT / page).read_text()
    refs = re.findall(r"!\[[^\]]*\]\(([^)]*repo-growth\.png)\)", text)
    assert refs == [IMAGE_URL], page


def test_publish_runs_only_checkout_download_and_the_verified_script(doc):
    steps = doc["jobs"]["publish"]["steps"]
    kinds = [s.get("uses", "").split("@")[0] or "run" for s in steps]
    assert kinds == ["actions/checkout", "actions/download-artifact", "run"]
    assert steps[-1]["run"].strip() == "bash scripts/publish_metrics_branch.sh bundle"
    assert set(steps[-1]["env"]) == {"GH_TOKEN", "METRICS_MAX_AGE_HOURS", "METRICS_EXPECTED_TIP"}
    assert steps[-1]["env"]["METRICS_EXPECTED_TIP"] == "${{ needs.render.outputs.tip }}"


def test_the_residual_risk_is_documented_in_the_workflow_and_the_page():
    text = WORKFLOW.read_text()
    assert "repository-wide" in text and "ruleset" in text
    page = (ROOT / "docs/wiki/Repository-Growth.md").read_text()
    assert "repository-wide" in page and "ruleset" in page and "metrics" in page


def test_render_holds_no_write_permission_and_no_graphql_only_grant(doc):
    perms = doc["jobs"]["render"]["permissions"]
    assert perms == {"contents": "read"}
    assert all(v == "read" for v in perms.values())


def render_script(doc):
    return "\n".join(s for n, s in run_scripts(doc) if n == "render")


def test_render_never_asks_for_star_times_and_carries_the_ledger(doc):
    script = render_script(doc)
    assert "--no-star-times" in script
    assert "stargazers" not in script and "graphql" not in script
    assert "--baseline docs/wiki/.metrics-snapshot.json" in script
    assert "--ledger-from carried/metrics-snapshot.json" in script


def test_the_carry_step_uses_the_script_and_exports_the_tip(doc):
    steps = doc["jobs"]["render"]["steps"]
    carry = next(st for st in steps if st.get("id") == "carry")
    assert "scripts/carry_metrics_snapshot.sh" in carry["run"] and '>> "$GITHUB_OUTPUT"' in carry["run"]
    assert doc["jobs"]["render"]["outputs"] == {"tip": "${{ steps.carry.outputs.tip }}"}


def test_the_carry_script_fails_closed_on_every_read_problem():
    text = (ROOT / "scripts" / "carry_metrics_snapshot.sh").read_text()
    assert "ls-remote --exit-code" in text and '"$rc" -eq 2' in text
    assert "|| true" not in text


def test_the_carry_step_runs_before_the_refresh(doc):
    names = [s.get("name", "") for s in doc["jobs"]["render"]["steps"]]
    carry = next(i for i, n in enumerate(names) if "ledger" in n)
    fetch = next(i for i, n in enumerate(names) if n.startswith("Fetch"))
    assert carry < fetch
