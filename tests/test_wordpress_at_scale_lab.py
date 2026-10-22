"""Structure and rule checks for labs/wordpress-at-scale, no Docker needed.

The lab is local only, so these tests guard what could make it unsafe or misleading: a
published port that is not loopback, an unpinned image, a mounted Docker socket, a web tier on
a network with a route out, an edge that bypasses the cache but still stores private pages,
and a reviewer's-rules script that stops biting.
"""

import importlib.util
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "labs" / "wordpress-at-scale"
_spec = importlib.util.spec_from_file_location("ci_policy_check", LAB / "ci" / "ci_policy_check.py")
cpc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cpc)


def compose():
    return yaml.safe_load((LAB / "compose.yaml").read_text())


def test_published_ports_are_loopback_only():
    for name, svc in compose()["services"].items():
        for port in svc.get("ports", []):
            assert str(port).startswith("127.0.0.1:"), f"{name} publishes {port}"


def test_images_are_pinned_and_no_docker_socket():
    text = (LAB / "compose.yaml").read_text()
    assert "docker.sock" not in text
    for name, svc in compose()["services"].items():
        image = svc["image"]
        assert ":" in image and not image.endswith(":latest"), f"{name}: {image}"


def test_the_origin_tier_has_no_route_out_and_publishes_nothing():
    c = compose()
    assert c["networks"]["backend"]["internal"] is True
    for name in ("lb", "web1", "web2", "redis"):
        assert c["services"][name]["networks"] == ["backend"], name
        assert "ports" not in c["services"][name], name
    assert set(c["services"]["edge"]["networks"]) == {"public", "backend"}


def test_the_careful_edge_pairs_bypass_with_no_cache_and_locks():
    text = (LAB / "edge" / "edge.conf.template").read_text()
    careful = text.split("listen 8080;")[1].split("listen 8081;")[0]
    for directive in ("proxy_cache_bypass $has_session;", "proxy_no_cache     $has_session;", "proxy_cache_lock on;"):
        assert directive in careful, directive
    careless = text.split("listen 8081;")[1]
    assert "proxy_cache_lock" not in careless and "proxy_cache_bypass" not in careless


def test_the_origin_secret_is_never_a_literal():
    for path in LAB.rglob("*"):
        if path.is_file() and path.name != ".env" and ".state" not in path.parts:
            assert not re.search(r"ORIGIN_SECRET\s*[=:]\s*[0-9a-f]{16,}", path.read_text(errors="ignore")), path


def test_every_lab_file_carries_the_spdx_header():
    for path in LAB.rglob("*"):
        if path.is_file() and path.suffix in {".sh", ".ps1", ".py", ".yaml", ".yml", ".php", ".template"}:
            head = "\n".join(path.read_text().splitlines()[:4])
            assert "SPDX-License-Identifier: Apache-2.0" in head, path


def test_the_sample_site_and_example_workflow_pass_the_reviewers_rules():
    assert cpc.check_workflow(LAB / "ci" / "example-wordpress-ci.yml") == []
    assert cpc.check_site(LAB / "site") == []


def _bad_workflow(tmp_path, body):
    path = tmp_path / "w.yml"
    path.write_text(body)
    return cpc.check_workflow(path)


def test_each_workflow_rule_bites(tmp_path):
    good_pin = "a" * 40
    base = f"name: x\npermissions: {{}}\njobs:\n  p:\n    environment: production\n    uses: o/r/.github/workflows/w.yml@{good_pin} # v1\n"
    assert _bad_workflow(tmp_path, base) == []
    assert any("W1" in f for f in _bad_workflow(tmp_path, base.replace(good_pin, "main")))
    assert any("W2" in f for f in _bad_workflow(tmp_path, base.replace("permissions: {}\n", "")))
    assert any("W3" in f for f in _bad_workflow(tmp_path, base.replace("name: x\n", "name: x\non:\n  pull_request_target:\n")))
    assert any("W4" in f for f in _bad_workflow(tmp_path, base + "    secrets: inherit\n"))
    assert any("W6" in f for f in _bad_workflow(tmp_path, base.replace("    environment: production\n", "")))
    injected = base + "    steps:\n      - run: echo ${{ github.event.pull_request.title }}\n"
    assert any("W5" in f for f in _bad_workflow(tmp_path, injected))
    literal = base + "    env:\n      api_key: 'abcdefghijkl'\n"
    findings = _bad_workflow(tmp_path, literal)
    assert any("W7" in f for f in findings) and not any("abcdefghijkl" in f for f in findings)


def test_each_site_rule_bites(tmp_path):
    site = tmp_path / "site"
    (site / "config").mkdir(parents=True)
    for name in ("composer.json", ".gitignore"):
        (site / name).write_text((LAB / "site" / name).read_text())
    (site / "config" / "application.php").write_text((LAB / "site" / "config" / "application.php").read_text())
    assert cpc.check_site(site) == []
    data = json.loads((site / "composer.json").read_text())
    data["require"]["example-vendor/example-plugin-a"] = "^2.3"
    (site / "composer.json").write_text(json.dumps(data))
    assert any("S2" in f for f in cpc.check_site(site))
    app = site / "config" / "application.php"
    app.write_text(app.read_text().replace("'DISALLOW_FILE_MODS', true", "'DISALLOW_FILE_MODS', false"))
    assert any("S6" in f for f in cpc.check_site(site))
    (site / "web" / "app" / "uploads").mkdir(parents=True)
    assert any("S4" in f for f in cpc.check_site(site))
