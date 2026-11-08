# SPDX-License-Identifier: Apache-2.0
"""Shared pytest setup.

`slow` marks the tests that run OpenTofu (an init that may download a provider, then validate or
plan). They always run, in CI too; the marker only lets a person on a laptop write
`-m "not slow"` for a quick pass (#527).

`tofu_lab` is one initialized copy of labs/email-security for the whole test session. Before this,
`test_tofu_validate` and the plan test each copied the tree and ran `tofu init` in a fresh plugin
cache, so the digitalocean provider was downloaded twice per run and initialized twice per directory.
"""

import fcntl
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "labs" / "email-security"

NO_NETWORK = "tofu could not download its provider (no network)"


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: runs OpenTofu (provider download on a cold plugin cache); always run, CI included")


def _plugin_cache(fallback: Path) -> Path:
    """A per-user plugin cache that survives between runs; a session directory if that cannot be made."""
    base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    cache = base / "cah-tests" / "tofu-plugins"
    try:
        cache.mkdir(parents=True, exist_ok=True)
        return cache
    except OSError:
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def lab_dirs(tree: Path) -> list[Path]:
    return sorted((tree / "cloud").iterdir()) + [tree / "compose"]


@pytest.fixture(scope="session")
def tofu_lab(tmp_path_factory):
    """(env, tree): the email-security lab copied once and `tofu init`ed once per session.

    Under pytest-xdist every worker is its own session, so the tree lives in the directory the workers
    share and a file lock lets the first worker build it while the others wait and then reuse it. The
    plugin cache is only written while that lock is held: a plugin cache is not documented as safe for
    two `tofu init` runs at once, so init is serialized rather than given one cache per worker. A
    failed init (no network) is remembered so the other workers skip at once instead of retrying.
    """
    if shutil.which("tofu") is None:
        pytest.skip("tofu is not installed")
    base = tmp_path_factory.getbasetemp()
    shared = base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base
    tree = shared / "tofu-lab"
    state = shared / "tofu-lab.state"
    cache = _plugin_cache(shared / "tofu-plugins")
    env = dict(os.environ, TF_PLUGIN_CACHE_DIR=str(cache), TF_IN_AUTOMATION="1")
    with open(cache.parent / ".cah-tofu.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not state.exists():
            shutil.copytree(LAB, tree, ignore=shutil.ignore_patterns(".terraform*", "local"))
            verdict = "ok"
            for d in lab_dirs(tree):
                init = subprocess.run(["tofu", "init", "-backend=false", "-input=false"], cwd=d, env=env, capture_output=True, text=True, check=False)
                if init.returncode != 0:
                    verdict = "no-network"
                    break
            state.write_text(verdict)
    if state.read_text() != "ok":
        pytest.skip(NO_NETWORK)
    return env, tree
