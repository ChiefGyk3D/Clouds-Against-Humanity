"""Structure checks for labs/demo-monitoring, no Docker needed.

The lab is synthetic data only, so these tests guard what could make it unsafe
or misleading: an unpinned image, a published port that is not loopback, a
non-documentation address, a dashboard querying a metric the generator never
exports, a committed secret, and provisioning that points at nothing.
"""

import ipaddress
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "labs" / "demo-monitoring"
# The lab mounts the repository's own dashboards; it keeps no copy of them.
SHARED = ROOT / "dashboards"
MOUNTED = ("cah_sites_overview", "cah_droplet_health")
DASHBOARDS = [SHARED / f"{name}.json" for name in MOUNTED]
GENERATOR = LAB / "generator" / "generator.py"

# Metric names the generator and the rule files really produce: the generator's
# own text, plus the series Prometheus itself writes for every scrape.
PROMETHEUS_OWN = {"up", "ALERTS", "cah_expected_targets", "scrape_duration_seconds", "scrape_samples_scraped"}

def generator_metrics():
    return set(re.findall(r"\b((?:node|twingate)_[A-Za-z0-9_]+)", GENERATOR.read_text()))


PROMQL_WORDS = {
    "sum", "avg", "count", "max", "min", "by", "on", "without", "rate", "time", "timestamp",
    "max_over_time", "vector", "or", "and", "unless", "ignoring", "group_left", "group_right",
    "clamp_min", "label_values",
}
DOCUMENTATION_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]


def lab_files():
    skip = {".env", ".gitkeep"}
    return [p for p in LAB.rglob("*") if p.is_file() and p.name not in skip and "state" not in p.relative_to(LAB).parts[:1]]


def compose():
    return yaml.safe_load((LAB / "docker-compose.yml").read_text())


def test_lab_files_exist():
    assert (LAB / "docker-compose.yml").is_file()
    assert all(d.is_file() for d in DASHBOARDS), "the shared dashboards the lab mounts must exist"
    assert not (LAB / "grafana" / "dashboards").exists(), "the lab must not carry its own copy of the dashboards"


def test_images_are_pinned_without_latest():
    for name, svc in compose()["services"].items():
        image = svc["image"]
        assert ":" in image.rsplit("/", 1)[-1] or "@sha256:" in image, f"{name}: no tag or digest"
        assert not image.endswith(":latest"), f"{name} uses latest"
        assert re.search(r":v?\d+\.\d+|@sha256:", image), f"{name}: tag is not an exact version"


def test_ports_bind_to_loopback_only():
    for name, svc in compose()["services"].items():
        for port in svc.get("ports", []):
            assert str(port).startswith("127.0.0.1:"), f"{name} publishes {port} beyond loopback"


def test_grafana_has_no_anonymous_access_and_no_literal_password():
    env = compose()["services"]["grafana"]["environment"]
    assert str(env["GF_AUTH_ANONYMOUS_ENABLED"]).lower() == "false"
    password = str(env["GF_SECURITY_ADMIN_PASSWORD"])
    assert password.startswith("${GRAFANA_ADMIN_PASSWORD"), "the admin password must come from the environment"
    example = (LAB / "env.example").read_text()
    assert re.search(r"^GRAFANA_ADMIN_PASSWORD=$", example, re.MULTILINE), "env.example must carry no value"
    assert ".env" in (LAB / ".gitignore").read_text().splitlines()


def test_compose_mounts_exist():
    for name, svc in compose()["services"].items():
        for vol in svc.get("volumes", []):
            src = str(vol).split(":")[0]
            if src.startswith("."):
                assert (LAB / src).resolve().exists(), f"{name} mounts missing {src}"


def test_grafana_mounts_the_shared_dashboards_read_only():
    vols = [str(v) for v in compose()["services"]["grafana"]["volumes"]]
    for name in MOUNTED:
        want = f"../../dashboards/{name}.json:/var/lib/grafana/dashboards/{name}.json:ro"
        assert want in vols, f"grafana does not mount {name} read-only"


def test_provisioning_points_at_real_files():
    provider = yaml.safe_load((LAB / "grafana/provisioning/dashboards/dashboards.yml").read_text())
    assert provider["providers"][0]["options"]["path"] == "/var/lib/grafana/dashboards"
    ds = yaml.safe_load((LAB / "grafana/provisioning/datasources/prometheus.yml").read_text())["datasources"][0]
    assert ds["uid"] == "cah-prometheus" and ds["url"] == "http://prometheus:9090"
    prom = yaml.safe_load((LAB / "prometheus/prometheus.yml").read_text())
    for rule in prom["rule_files"]:
        assert (LAB / "prometheus" / Path(rule).name).is_file(), rule
    for scrape in prom["scrape_configs"]:
        for sd in scrape["file_sd_configs"]:
            for f in sd["files"]:
                assert (LAB / "prometheus" / Path(f).name).is_file(), f


def exprs(node):
    if isinstance(node, dict):
        if isinstance(node.get("expr"), str):
            yield node["expr"]
        for v in node.values():
            yield from exprs(v)
    elif isinstance(node, list):
        for v in node:
            yield from exprs(v)


def metrics_in(expr):
    text = re.sub(r'"[^"]*"', '""', expr)
    text = re.sub(r"\{[^}]*\}", "", text)  # label matchers
    text = re.sub(r"\[[^\]]*\]", "", text)  # ranges and subquery steps
    text = re.sub(r"\b(by|on|without|ignoring)\s*\([^)]*\)", " ", text)
    text = re.sub(r"\$\w+", "", text)
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
    return {w for w in words if w not in PROMQL_WORDS}


def test_dashboards_have_variables_and_uids():
    for path in DASHBOARDS:
        dash = json.loads(path.read_text())
        names = {v["name"] for v in dash["templating"]["list"]}
        assert {"DS_PROMETHEUS", "site", "instance"} <= names, path.name
        assert dash["panels"], path.name


def test_panel_queries_use_only_metrics_the_lab_exports():
    allowed = generator_metrics() | PROMETHEUS_OWN
    assert "node_memory_SwapFree_bytes" in allowed, "the generator's metric names were not collected"
    seen = 0
    for path in DASHBOARDS:
        for expr in exprs(json.loads(path.read_text())):
            seen += 1
            unknown = metrics_in(expr) - allowed
            assert not unknown, f"{path.name}: the generator does not export {sorted(unknown)} (in {expr})"
    assert seen > 10


def test_metric_guard_bites_on_an_unexported_name():
    assert metrics_in("rate(not_a_real_metric_total[5m])") - (generator_metrics() | PROMETHEUS_OWN)


def test_targets_follow_the_runbook_shape():
    targets = json.loads((LAB / "prometheus/targets.json").read_text())
    assert len(targets) == 8
    prom = yaml.safe_load((LAB / "prometheus/prometheus.yml").read_text())
    assert [s["job_name"] for s in prom["scrape_configs"]] == ["twingate-ztna"], "one job, as in the design"
    paths = {"node-exporter": "/node", "connector-metrics": "/connector"}
    per_site = {}
    for t in targets:
        labels = t["labels"]
        assert labels["endpoint"] in paths
        assert labels["__metrics_path__"] == paths[labels["endpoint"]]
        assert {"site", "region", "provider", "role", "instance"} <= set(labels)
        per_site[labels["site"]] = per_site.get(labels["site"], 0) + 1
    assert set(per_site.values()) == {4}
    inventory = yaml.safe_load((LAB / "prometheus/inventory.rules.yml").read_text())
    exprs_ = {r["labels"]["site"]: r["expr"] for g in inventory["groups"] for r in g["rules"]}
    assert exprs_ == {site: "vector(4)" for site in per_site}, "the inventory counts endpoints, as the targets do"


def test_rule_files_use_only_allowed_metrics():
    for name in ("alerts.rules.yml", "inventory.rules.yml"):
        for expr in exprs(yaml.safe_load((LAB / "prometheus" / name).read_text())):
            assert not (metrics_in(expr) - (generator_metrics() | PROMETHEUS_OWN)), expr
    alerts = (LAB / "prometheus/alerts.rules.yml").read_text()
    assert "CloudSiteSilent" in alerts and "CloudSiteDegraded" in alerts
    assert "absent(" not in alerts.replace("# ", "").split("groups:")[1]


def test_promtool_fixtures_cover_the_scenarios():
    text = (LAB / "prometheus/tests/alerts.test.yml").read_text()
    assert text.count("alertname: CloudSiteSilent") >= 5
    assert text.count("endpoint=\"connector-metrics\"") and text.count("endpoint=\"node-exporter\"")
    assert "0x40" in text, "an every-target-at-up==0 scenario is required"
    assert (LAB / "prometheus/tests/alerts-site-removed.test.yml").is_file()


def test_every_ip_in_the_lab_is_a_documentation_address():
    ip = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
    allowed_other = {"127.0.0.1", "0.0.0.0"}  # loopback bind and the generator's in-network listener
    for path in lab_files():
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for m in ip.findall(text):
            if m in allowed_other:
                continue
            addr = ipaddress.ip_address(m)
            assert any(addr in n for n in DOCUMENTATION_NETS), f"{path.relative_to(ROOT)} has {m}"


def test_no_secret_shaped_literals_in_the_lab():
    pattern = re.compile(r"(password|secret|token|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9/+_-]{12,}", re.IGNORECASE)
    for path in lab_files():
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        assert not pattern.search(text), f"secret-shaped literal in {path.relative_to(ROOT)}"


def test_script_exposes_the_subcommands():
    script = (ROOT / "scripts" / "demo_monitoring.sh").read_text()
    for sub in ("up)", "down)", "silent-site)", "restore-site)", "test)", "screenshots)"):
        assert sub in script
    assert "restart-prometheus)" in script, "the supported way to apply a rule-file edit"
    assert "compose restart prometheus" in script
    assert "set -euo pipefail" in script
    assert "sudo" not in script.replace("no sudo is used", "")


def password_line(tmp_path, shell_value, env_file_value):
    """Run the script's login-hint function against a temporary lab directory."""
    import os
    import subprocess

    if env_file_value is not None:
        (tmp_path / ".env").write_text(f"GRAFANA_ADMIN_PASSWORD={env_file_value}\n")
    env = {k: v for k, v in os.environ.items() if k != "GRAFANA_ADMIN_PASSWORD"}
    if shell_value is not None:
        env["GRAFANA_ADMIN_PASSWORD"] = shell_value
    script = ROOT / "scripts" / "demo_monitoring.sh"
    out = subprocess.run(
        ["bash", "-c", f'source "{script}"; LAB="{tmp_path}"; password_hint'],
        env=env, capture_output=True, text=True, check=True,
    ).stdout
    return out


def test_login_hint_names_the_shell_environment_when_the_password_comes_from_it(tmp_path):
    # Built at run time, and named so it is not secret-shaped in the source.
    value = "hint" + "Value" + str(len(str(tmp_path)))
    out = password_line(tmp_path, value, None)
    assert "shell environment" in out and ".env" not in out
    assert value not in out


def test_login_hint_names_the_env_file_when_only_the_file_has_it(tmp_path):
    value = "file" + "Value" + str(len(str(tmp_path)))
    out = password_line(tmp_path, None, value)
    assert str(tmp_path / ".env") in out
    assert value not in out


def test_shell_environment_wins_over_the_env_file_as_compose_does(tmp_path):
    out = password_line(tmp_path, "fromShellOne", "fromFileOne")
    assert "shell environment" in out
    assert "fromShellOne" not in out and "fromFileOne" not in out
