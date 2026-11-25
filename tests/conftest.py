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
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "labs" / "email-security"


def _init_network_error(stderr: str) -> str | None:
    """Skip only when every error diagnostic is a known provider download failure."""
    text = re.sub(r"\x1b\[[0-9;]*m", "", stderr)
    text = re.sub(r"(?m)^[ \t]*│[ \t]?", "", text)
    diagnostics = re.split(r"(?m)^[ \t]*Error:[ \t]*", text)[1:]
    if not diagnostics:
        return None
    patterns = (
        r"\bconnection refused\b",
        r"\bno such host\b|\bcould not resolve host\b",
        r"\bi/o timeout\b|\bcontext deadline exceeded\b|\bClient\.Timeout exceeded\b",
        r"\bTLS handshake (?:timeout|failed|failure|error)\b",
        r"\b(?:network is unreachable|no route to host)\b",
        r"\b5\d\d (?:Internal Server Error|Not Implemented|Bad Gateway|Service Unavailable|Gateway Timeout)\b"
        r"|\b(?:HTTP(?:/\d(?:\.\d)?)?|status(?: code)?|response code)[: ]+5\d\d\b",
    )
    causes = []
    for diagnostic in diagnostics:
        # A quoted provider message in a configuration error is not its title.
        header = re.match(
            r"failed to (?:query available provider packages|install provider|request discovery document)"
            r"(?:[ \t]*\r?\n|:[ \t]*)(.*)", diagnostic.strip(), re.IGNORECASE | re.DOTALL,
        )
        if header is None:
            return None
        match = next((found for pattern in patterns
                      if (found := re.search(pattern, header.group(1), re.IGNORECASE))), None)
        if match is None:
            return None
        causes.append(match.group(0))
    return "; ".join(dict.fromkeys(causes))


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
    init result and its diagnostics are remembered so other workers get the same failure or skip.
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
            verdict = {"status": "ok"}
            for d in lab_dirs(tree):
                init = subprocess.run(["tofu", "init", "-backend=false", "-input=false"], cwd=d, env=env, capture_output=True, text=True, check=False)
                if init.returncode != 0:
                    verdict = {"status": "failed", "directory": str(d.relative_to(tree)),
                               "stdout": init.stdout, "stderr": init.stderr}
                    break
            state.write_text(json.dumps(verdict))
    try:
        verdict = json.loads(state.read_text())
    except (OSError, ValueError) as error:
        pytest.fail(f"could not read cached tofu init result: {error}", pytrace=False)
    if verdict == {"status": "ok"}:
        return env, tree
    if (not isinstance(verdict, dict) or set(verdict) != {"status", "directory", "stdout", "stderr"}
            or verdict["status"] != "failed"
            or not all(isinstance(verdict[key], str) for key in ("directory", "stdout", "stderr"))):
        pytest.fail("invalid cached tofu init result; refusing to treat it as a network skip", pytrace=False)
    diagnostic = f"{verdict['directory']}: tofu init failed\n{verdict['stdout']}{verdict['stderr']}"
    network_error = _init_network_error(verdict["stderr"])
    if network_error is not None:
        pytest.skip(f"tofu provider download unavailable ({network_error})\n{diagnostic}")
    pytest.fail(diagnostic, pytrace=False)
