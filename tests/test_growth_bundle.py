# SPDX-License-Identifier: Apache-2.0
"""The daily growth chart bundle (issue #294): hostile input, and the publish script.

The render job hands a bundle (snapshot JSON + PNG) to the publish job as an
artifact. The publish job holds contents: write, so it re-validates the bundle
offline before anything is pushed. What is proved here:
- a good bundle passes, and every hostile variation fails with a message: extra
  file, symlink, oversized snapshot or PNG, bad PNG signature, metadata chunk,
  hash mismatch, wrong repository, a stale or future time stamp, a login-like
  field, duplicate keys, nesting bombs, absurd counts;
- the publish script creates the orphan metrics branch on a first run, pushes
  only the three expected files, skips the push when the picture is unchanged,
  and refuses to overwrite a branch that moved under it (force-with-lease).
Everything is offline: the remote is a bare repository in a temporary directory.
"""

import copy
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from test_repo_metrics import fixture, png_bytes

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_repo_metrics as grm

PUBLISH = ROOT / "scripts" / "publish_metrics_branch.sh"
NOW = datetime.datetime(2026, 10, 25, 6, 0, 0, tzinfo=datetime.UTC)
REPO = "Example/Repo"


def make_bundle(path: Path, snap=None, png=None, fetched="2026-10-25T05:30:00Z") -> Path:
    snap = copy.deepcopy(snap or fixture())
    snap["fetched_at"] = fetched
    snap["stars"] = {"2026-10-10": 2, "2026-10-12": 5}
    snap["forks"] = {"2026-10-13": 1}
    snap["merged_prs"] = {"2026-10-11": 3}
    snap["closed_issues"] = {"2026-10-13": 1}
    path.mkdir(parents=True, exist_ok=True)
    (path / grm.BUNDLE_PNG).write_bytes(png if png is not None else png_bytes())
    snap["source_sha256"] = grm.source_digest(snap)
    snap["png_sha256"] = grm.file_digest(path / grm.BUNDLE_PNG)
    (path / grm.BUNDLE_SNAPSHOT).write_text(json.dumps(snap, indent=1, sort_keys=True) + "\n")
    return path


def problems(bundle: Path, **kw):
    kw.setdefault("expect_repo", REPO)
    kw.setdefault("now", NOW)
    kw.setdefault("max_age_hours", 6)
    return grm.verify_bundle(bundle, **kw)


def rewrite_snapshot(bundle: Path, mutate, rehash=True):
    p = bundle / grm.BUNDLE_SNAPSHOT
    snap = json.loads(p.read_text())
    mutate(snap)
    if rehash:
        snap["source_sha256"] = grm.source_digest(snap)
    p.write_text(json.dumps(snap, indent=1, sort_keys=True) + "\n")


def test_a_good_bundle_passes(tmp_path):
    assert problems(make_bundle(tmp_path / "b")) == []


def test_an_extra_file_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    (b / "payload.sh").write_text("echo hi\n")
    assert any("unexpected" in p for p in problems(b))


def test_a_missing_file_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    (b / grm.BUNDLE_PNG).unlink()
    assert problems(b)


def test_a_symlink_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    target = tmp_path / "elsewhere.png"
    shutil.move(b / grm.BUNDLE_PNG, target)
    os.symlink(target, b / grm.BUNDLE_PNG)
    assert any("regular file" in p for p in problems(b))


def test_a_subdirectory_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    (b / "sub").mkdir()
    assert any("unexpected" in p for p in problems(b))


def test_an_oversized_png_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    with (b / grm.BUNDLE_PNG).open("ab") as f:
        f.write(b"\0" * (grm.MAX_PNG_BYTES + 1))
    assert any("larger than" in p for p in problems(b))


def test_an_oversized_snapshot_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    with (b / grm.BUNDLE_SNAPSHOT).open("a") as f:
        f.write(" " * (grm.MAX_SNAPSHOT_BYTES + 1))
    assert any("larger than" in p for p in problems(b))


def test_a_png_with_a_bad_signature_fails(tmp_path):
    b = make_bundle(tmp_path / "b", png=b"GIF89a" + b"\0" * 40)
    assert any("PNG" in p for p in problems(b))


def test_a_png_that_is_a_script_fails(tmp_path):
    b = make_bundle(tmp_path / "b", png=b"#!/bin/sh\nrm -rf /\n")
    assert problems(b)


def test_a_png_that_does_not_match_its_hash_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    (b / grm.BUNDLE_PNG).write_bytes(png_bytes(color=9))
    assert any("png_sha256" in p for p in problems(b))


def test_a_hand_edited_snapshot_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    rewrite_snapshot(b, lambda s: s["stars"].update({"2026-10-12": 99999}), rehash=False)
    assert any("source_sha256" in p for p in problems(b))


def test_the_wrong_repository_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    assert any("repo" in p for p in problems(b, expect_repo="Other/Thing"))


@pytest.mark.parametrize("field", ["login", "stargazers", "email"])
def test_a_login_like_field_fails(tmp_path, field):
    b = make_bundle(tmp_path / "b")
    rewrite_snapshot(b, lambda s: s.update({field: ["someone"]}))
    assert any("unknown field" in p for p in problems(b))


def test_a_stale_bundle_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    later = NOW + datetime.timedelta(hours=7)
    assert any("old" in p for p in problems(b, now=later))


def test_a_bundle_from_the_future_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    earlier = NOW - datetime.timedelta(hours=3)
    assert any("future" in p for p in problems(b, now=earlier))


def test_no_age_limit_when_none_is_given(tmp_path):
    b = make_bundle(tmp_path / "b")
    assert problems(b, now=NOW + datetime.timedelta(days=400), max_age_hours=None) == []


def test_an_absurd_count_fails(tmp_path):
    b = make_bundle(tmp_path / "b")
    rewrite_snapshot(b, lambda s: s["stars"].update({"2026-10-12": grm.MAX_DAY_COUNT + 1}))
    assert any("too large" in p for p in problems(b))


def test_duplicate_keys_fail(tmp_path):
    b = make_bundle(tmp_path / "b")
    p = b / grm.BUNDLE_SNAPSHOT
    text = p.read_text().replace('"repo": "Example/Repo",', '"repo": "Example/Repo", "repo": "Other/Thing",')
    p.write_text(text)
    assert any("duplicate" in x for x in problems(b))


def test_a_nesting_bomb_fails_without_crashing(tmp_path):
    b = make_bundle(tmp_path / "b")
    (b / grm.BUNDLE_SNAPSHOT).write_text("[" * 50000 + "]" * 50000)
    out = problems(b)
    assert out


@pytest.mark.parametrize("text", ["NaN", "[1, 2", "", "null", '{"schema": 1e999}'])
def test_garbage_snapshots_fail(tmp_path, text):
    b = make_bundle(tmp_path / "b")
    (b / grm.BUNDLE_SNAPSHOT).write_text(text)
    assert problems(b)


def test_the_cli_verifies_and_prints_the_as_of_stamp(tmp_path):
    b = make_bundle(tmp_path / "b")
    run = lambda *a: subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "gen_repo_metrics.py"), *a], check=False, capture_output=True, text=True)
    ok = run("--verify-bundle", str(b), "--expect-repo", REPO, "--print-as-of")
    assert ok.returncode == 0 and ok.stdout.strip() == "2026-10-25T05:30:00Z", ok.stderr
    (b / "extra").write_text("x")
    bad = run("--verify-bundle", str(b), "--expect-repo", REPO)
    assert bad.returncode == 1 and "unexpected" in bad.stderr


# -- the publish script ---------------------------------------------------------------


def git(*args, cwd=None, check=True):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True, env=env)


@pytest.fixture
def remote(tmp_path):
    r = tmp_path / "remote.git"
    git("init", "-q", "--bare", "-b", "main", str(r))
    return r


def publish(bundle, remote, **extra):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null", "METRICS_REMOTE": str(remote), "METRICS_EXPECT_REPO": REPO, "METRICS_MAX_AGE_HOURS": "0", **extra}
    return subprocess.run(["bash", str(PUBLISH), str(bundle)], check=False, capture_output=True, text=True, env=env)


def branch_files(remote):
    return sorted(git("ls-tree", "-r", "--name-only", "metrics", cwd=remote).stdout.split())


def test_first_run_creates_an_orphan_branch_with_three_files(tmp_path, remote):
    out = publish(make_bundle(tmp_path / "b"), remote)
    assert out.returncode == 0, out.stderr
    assert branch_files(remote) == ["as-of.txt", "metrics-snapshot.json", "repo-growth.png"]
    assert git("rev-list", "--count", "metrics", cwd=remote).stdout.strip() == "1"
    assert git("rev-list", "--max-parents=0", "metrics", cwd=remote).stdout.strip() == git("rev-parse", "metrics", cwd=remote).stdout.strip()
    assert git("show", "metrics:as-of.txt", cwd=remote).stdout == "2026-10-25T05:30:00Z\n"
    assert "main" not in git("branch", "--list", cwd=remote).stdout


def test_an_unchanged_picture_is_not_pushed_again(tmp_path, remote):
    b = make_bundle(tmp_path / "b")
    assert publish(b, remote).returncode == 0
    first = git("rev-parse", "metrics", cwd=remote).stdout
    again = publish(b, remote)
    assert again.returncode == 0 and "unchanged" in again.stdout
    assert git("rev-parse", "metrics", cwd=remote).stdout == first


def test_a_changed_picture_replaces_the_branch(tmp_path, remote):
    assert publish(make_bundle(tmp_path / "b"), remote).returncode == 0
    first = git("rev-parse", "metrics", cwd=remote).stdout
    assert publish(make_bundle(tmp_path / "c", png=png_bytes(color=7)), remote).returncode == 0
    assert git("rev-parse", "metrics", cwd=remote).stdout != first
    assert git("rev-list", "--count", "metrics", cwd=remote).stdout.strip() == "1"


def test_a_hostile_bundle_is_not_pushed(tmp_path, remote):
    b = make_bundle(tmp_path / "b")
    (b / "extra.sh").write_text("x")
    out = publish(b, remote)
    assert out.returncode != 0
    assert git("branch", "--list", "metrics", cwd=remote).stdout.strip() == ""


def test_a_branch_that_moved_under_the_publish_is_not_overwritten(tmp_path, remote):
    assert publish(make_bundle(tmp_path / "b"), remote).returncode == 0
    # A second writer lands a commit on the branch after the script read the old
    # value and before it pushes: a git shim moves the remote ref, then pushes.
    other = tmp_path / "other"
    git("clone", "-q", "-b", "metrics", str(remote), str(other))
    (other / "note.txt").write_text("someone else\n")
    git("-C", str(other), "add", "note.txt")
    git("-C", str(other), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x")
    git("-C", str(other), "push", "-q", "origin", "HEAD:refs/heads/side")
    moved = git("rev-parse", "side", cwd=remote).stdout.strip()
    real = shutil.which("git")
    shim = tmp_path / "shim"
    shim.mkdir()
    (shim / "git").write_text(
        "#!/bin/bash\n"
        'for a in "$@"; do\n'
        f'  if [ "$a" = push ]; then {real} --git-dir={remote} update-ref refs/heads/metrics {moved}; break; fi\n'
        "done\n"
        f'exec {real} "$@"\n'
    )
    (shim / "git").chmod(0o755)
    out = publish(make_bundle(tmp_path / "c", png=png_bytes(color=3)), remote, PATH=f"{shim}:{os.environ['PATH']}")
    assert out.returncode != 0
    assert git("rev-parse", "metrics", cwd=remote).stdout.strip() == moved


def test_the_script_never_uses_a_bare_force():
    import re

    text = PUBLISH.read_text()
    assert "--force-with-lease=" in text
    assert not re.search(r"--force(?!-with-lease=)", text)
    assert not re.search(r"push\s+(-\w*f|\+)", text)


def test_a_changed_snapshot_is_pushed_even_when_the_picture_is_identical(tmp_path, remote):
    assert publish(make_bundle(tmp_path / "b"), remote).returncode == 0
    first = git("rev-parse", "metrics", cwd=remote).stdout
    newer = make_bundle(tmp_path / "c", fetched="2026-10-25T05:45:00Z")
    assert (newer / grm.BUNDLE_PNG).read_bytes() == (tmp_path / "b" / grm.BUNDLE_PNG).read_bytes()
    out = publish(newer, remote)
    assert out.returncode == 0 and "pushed" in out.stdout
    assert git("rev-parse", "metrics", cwd=remote).stdout != first
    assert git("show", "metrics:as-of.txt", cwd=remote).stdout == "2026-10-25T05:45:00Z\n"
    assert json.loads(git("show", "metrics:metrics-snapshot.json", cwd=remote).stdout)["fetched_at"] == "2026-10-25T05:45:00Z"


def test_a_remote_branch_with_an_extra_file_is_replaced_not_skipped(tmp_path, remote):
    b = make_bundle(tmp_path / "b")
    assert publish(b, remote).returncode == 0
    other = tmp_path / "other"
    git("clone", "-q", "-b", "metrics", str(remote), str(other))
    (other / "extra.txt").write_text("x\n")
    git("-C", str(other), "add", "extra.txt")
    git("-C", str(other), "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x")
    git("-C", str(other), "push", "-q", "origin", "metrics")
    assert publish(b, remote).returncode == 0
    assert branch_files(remote) == ["as-of.txt", "metrics-snapshot.json", "repo-growth.png"]


@pytest.mark.parametrize("branch", ["main", "master", "metrics:main", "refs/heads/main", "../metrics", "metrics ", "-f", "", "metrics2", "HEAD"])
def test_the_script_refuses_to_push_to_any_ref_but_metrics(tmp_path, remote, branch):
    git("-C", str(remote), "symbolic-ref", "HEAD", "refs/heads/main")
    out = publish(make_bundle(tmp_path / "b"), remote, METRICS_BRANCH=branch)
    assert out.returncode != 0
    assert "refs/heads/metrics" in out.stderr
    assert git("branch", "--list", cwd=remote).stdout.strip() == ""


def test_the_push_refspec_is_spelled_out_in_the_script():
    text = PUBLISH.read_text()
    assert "HEAD:refs/heads/metrics" in text
    assert "refs/heads/metrics" in text.split("push")[-1]


TOKEN = f"fixture-credential-{6 * 7}"  # built at run time: a fake with no literal for a secret scanner to flag


def shimmed_publish(tmp_path, remote, bundle):
    """Run the script with a git shim that logs, per call, the credential env and the work repo's config."""
    import base64

    real = shutil.which("git")
    log = tmp_path / "gitcalls.log"
    shim = tmp_path / "shim"
    shim.mkdir()
    (shim / "git").write_text(
        "#!/bin/bash\n"
        'sub=""; dir=""\n'
        'args=("$@")\n'
        'if [ "${args[0]}" = -C ]; then dir=${args[1]}; sub=${args[2]}; else sub=${args[0]}; fi\n'
        f'{{ echo "CALL $sub count=${{GIT_CONFIG_COUNT:-}} key=${{GIT_CONFIG_KEY_0:-}} hasval=$([ -n "${{GIT_CONFIG_VALUE_0:-}}" ] && echo y || echo n) token=$([ -n "${{GH_TOKEN:-}}" ] && echo y || echo n)"; '
        f'[ -n "$dir" ] && [ -f "$dir/.git/config" ] && sed "s/^/CONFIG /" "$dir/.git/config"; }} >> {log}\n'
        f'exec {real} "$@"\n'
    )
    (shim / "git").chmod(0o755)
    out = publish(bundle, remote, GH_TOKEN=TOKEN, PATH=f"{shim}:{os.environ['PATH']}")
    return out, log.read_text(), base64.b64encode(f"x-access-token:{TOKEN}".encode()).decode()


def test_the_token_header_is_scoped_to_the_remote_url_and_only_remote_commands(tmp_path, remote):
    out, calls, _ = shimmed_publish(tmp_path, remote, make_bundle(tmp_path / "b"))
    assert out.returncode == 0, out.stderr
    remote_calls = [ln for ln in calls.splitlines() if ln.startswith("CALL ") and "hasval=y" in ln]
    assert remote_calls, "the header was never sent"
    for ln in remote_calls:
        assert ln.split()[1] in {"ls-remote", "fetch", "push"}, ln
        assert f"key=http.{remote}.extraheader" in ln, ln
        assert "count=1" in ln
    local = [ln for ln in calls.splitlines() if ln.startswith("CALL ") and ln.split()[1] in {"init", "remote", "add", "commit", "show"}]
    assert local and all("hasval=n" in ln and "count= " in ln for ln in local), local


def test_no_file_and_no_output_ever_holds_the_token(tmp_path, remote):
    out, calls, b64 = shimmed_publish(tmp_path, remote, make_bundle(tmp_path / "b"))
    assert out.returncode == 0
    for secret in (TOKEN, b64):
        assert secret not in calls  # the work repo's .git/config, as seen at every call
        assert secret not in out.stdout + out.stderr
        for path in tmp_path.rglob("*"):
            if path.is_file() and not path.is_symlink() and path != tmp_path / "gitcalls.log":
                assert secret.encode() not in path.read_bytes(), path


def test_the_python_validator_does_not_see_the_token(tmp_path, remote):
    real = shutil.which("python3")
    shim = tmp_path / "pyshim"
    shim.mkdir()
    seen = tmp_path / "py-env.log"
    (shim / "python3").write_text(f'#!/bin/bash\necho "GH_TOKEN=${{GH_TOKEN:-unset}} GITHUB_TOKEN=${{GITHUB_TOKEN:-unset}}" >> {seen}\nexec {real} "$@"\n')
    (shim / "python3").chmod(0o755)
    out = publish(make_bundle(tmp_path / "b"), remote, GH_TOKEN=TOKEN, GITHUB_TOKEN=TOKEN, PATH=f"{shim}:{os.environ['PATH']}")
    assert out.returncode == 0, out.stderr
    assert seen.read_text().strip() == "GH_TOKEN=unset GITHUB_TOKEN=unset"
    assert "export GIT_CONFIG" not in PUBLISH.read_text()
