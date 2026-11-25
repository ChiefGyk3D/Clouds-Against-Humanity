# SPDX-License-Identifier: Apache-2.0
"""Classify init results without provider downloads or cloud accounts (#533)."""
import json
import subprocess
from types import SimpleNamespace

import pytest

import conftest


def _failure_message(action):
    try:
        with pytest.raises(pytest.fail.Exception) as caught:
            action()
    except pytest.skip.Exception as error:
        raise AssertionError("unexpected skip in required-failure regression") from error
    return str(caught.value)


def _initialized(action):
    try:
        return action()
    except pytest.skip.Exception as error:
        raise AssertionError("unexpected skip in required-success regression") from error


@pytest.fixture
def init_case(tmp_path, monkeypatch):
    lab = tmp_path / "lab"
    (lab / "cloud" / "example").mkdir(parents=True)
    (lab / "compose").mkdir()
    (lab / "compose" / "main.tf").write_text("# fictional local input\n")
    base = tmp_path / "session"
    base.mkdir()
    monkeypatch.setattr(conftest, "LAB", lab)
    monkeypatch.setattr(conftest.shutil, "which", lambda name: "/fictional/tofu")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    factory = SimpleNamespace(getbasetemp=lambda: base)
    calls = []

    def run(result, worker=None):
        def fake_run(args, **kwargs):
            calls.append((args, kwargs))
            return result

        monkeypatch.setattr(conftest.subprocess, "run", fake_run)
        if worker is None:
            monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
            return conftest.tofu_lab.__wrapped__(factory)
        # Independent worker base directories share the same cached result.
        worker_base = base / worker
        worker_base.mkdir(exist_ok=True)
        monkeypatch.setenv("PYTEST_XDIST_WORKER", worker)
        return conftest.tofu_lab.__wrapped__(SimpleNamespace(getbasetemp=lambda: worker_base))

    return SimpleNamespace(run=run, calls=calls, state=base / "tofu-lab.state", base=base)


def test_success_returns_initialized_tree_and_reuses_it(init_case):
    success = subprocess.CompletedProcess(["tofu", "init"], 0, "initialized", "")
    env, tree = _initialized(lambda: init_case.run(success))
    assert tree == init_case.base / "tofu-lab"
    assert env["TF_IN_AUTOMATION"] == "1"
    assert len(init_case.calls) == 2
    assert all(args == ["tofu", "init", "-backend=false", "-input=false"] for args, _ in init_case.calls)
    cached_env, cached_tree = _initialized(lambda: init_case.run(success, worker="gw1"))
    assert cached_tree == tree
    assert cached_env["TF_IN_AUTOMATION"] == env["TF_IN_AUTOMATION"]
    assert cached_env["TF_PLUGIN_CACHE_DIR"] == env["TF_PLUGIN_CACHE_DIR"]
    assert len(init_case.calls) == 2


@pytest.mark.parametrize("stderr", [
    'Error: Argument or block definition required\n  on main.tf line 1: broken {{{',
    'Error: Failed to query available provider packages\nno available releases match the given constraints >= 999.0.0',
    'Error: permission denied while writing the dependency lock file',
    'Error: timeout is not a valid argument for this resource',
    'Error: Failed to query available provider packages\nregistry.opentofu.org: 403 Forbidden',
    'Error: Failed to query available provider packages\nregistry.opentofu.org: 404 Not Found',
    'Error: Failed to install provider\nx509: certificate signed by unknown authority',
    'Error: Failed to query available provider packages\nno available releases match the given constraints >= 999.0.0\nError: Invalid value for variable\nThe value "no such host" is not allowed.',
    'Error: Invalid value for variable "message"\nThe literal "Failed to install provider: connection refused" is forbidden.',
    'Error: Failed to query available provider packages\nlookup registry.opentofu.org: no such host\nError: Invalid provider configuration\nMissing required argument: token.',
    'Failed to query available provider packages\nno such host',
    '',
])
def test_non_network_init_failure_and_cached_failure_still_fail(init_case, stderr):
    failure = subprocess.CompletedProcess(["tofu", "init"], 1, "original init stdout\n", stderr)
    for worker in ("gw0", "gw1"):
        message = _failure_message(lambda: init_case.run(failure, worker=worker))
        assert "tofu init failed" in message
        assert failure.stdout in message and failure.stderr in message
    assert len(init_case.calls) == 1


@pytest.mark.parametrize("stderr, matched", [
    ('Error: Failed to query available provider packages\nGet "https://registry.opentofu.org/": dial tcp: connection refused', 'connection refused'),
    ('Error: Failed to query available provider packages\nlookup registry.opentofu.org: no such host', 'no such host'),
    ('Error: Failed to install provider\nGet "https://registry.opentofu.org/": i/o timeout', 'i/o timeout'),
    ('Error: Failed to request discovery document\nTLS handshake timeout', 'TLS handshake timeout'),
    ('Error: Failed to query available provider packages\nregistry.opentofu.org: 503 Service Unavailable', '503 Service Unavailable'),
    ('Error: Failed to query available provider packages\nregistry.opentofu.org: HTTP 502', 'HTTP 502'),
    ('\x1b[31m│ Error: Failed to install provider\x1b[0m\n│ TLS handshake timeout', 'TLS handshake timeout'),
    ('Error: Failed to query available provider packages\nno such host\nError: Failed to install provider\nconnection refused', 'no such host; connection refused'),
])
def test_recognized_network_failure_and_cached_skip_name_the_error(init_case, stderr, matched):
    failure = subprocess.CompletedProcess(["tofu", "init"], 1, "original init stdout\n", stderr)
    for worker in ("gw0", "gw1"):
        with pytest.raises(pytest.skip.Exception) as caught:
            init_case.run(failure, worker=worker)
        message = str(caught.value)
        assert f"({matched})" in message
        assert failure.stdout in message and failure.stderr in message
    assert len(init_case.calls) == 1


@pytest.mark.parametrize("cached", ['not JSON', '"no-network"', '{}', '{"status":"unknown"}',
    '{"status":"failed","directory":"example","stdout":"","stderr":null}',
    '{"status":"ok","unexpected":true}'])
def test_unknown_or_corrupt_cache_fails_without_rerunning_init(init_case, cached):
    init_case.state.write_text(cached)
    message = _failure_message(lambda: init_case.run(subprocess.CompletedProcess(["tofu", "init"], 0, "", "")))
    assert "cached tofu init result" in message
    assert not init_case.calls


@pytest.mark.parametrize("stderr", [
    'Error: timeout',
    'Error: connection refused while evaluating a fictional local script',
    'Error: Invalid value "no such host" for an input variable',
    'Error: Invalid local value "registry.opentofu.org connection refused"',
    'Error: Failed to query available provider packages\nprovider constraint mismatch',
])
def test_arbitrary_stderr_is_not_network(stderr):
    assert conftest._init_network_error(stderr) is None
