# SPDX-License-Identifier: Apache-2.0
"""The SearXNG workload (issue #425): a compose definition that is pinned, private, limited and holds no secret.

workloads/searxng/ is a documented, unapplied stage 3 workload. Nothing here starts a container or reads the
network. A mutable tag, a published cache, a wildcard bind, a secret value in a file, a limiter that is off or a
public instance flag would each make a private search proxy into something else, so each guard has a negative case.
"""

import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "workloads" / "searxng"
COMPOSE = DIR / "docker-compose.yml"
SETTINGS = DIR / "settings.yml"
LIMITER = DIR / "limiter.toml"
ENV_EXAMPLE = DIR / "env.example"
README = DIR / "README.md"

PINNED = re.compile(r"^[a-z0-9./_-]+:[A-Za-z0-9._-]+@sha256:[0-9a-f]{64}$")
MUTABLE_TAGS = {"latest", "stable", "main", "master", "edge", "unstable"}
WILDCARD = re.compile(r"(^|[:\s\"'])(0\.0\.0\.0|\[::\]|::)([:\s\"']|$)")
# A bind is acceptable only as a required variable (compose stops if it is unset) or a literal private address.
BIND_OK = re.compile(r"^(\$\{[A-Z_]+:\?[^}]*\}|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+):\d+:\d+$")
SECRET_NAME = re.compile(r"(SECRET|PASSWORD|PASSWD|TOKEN|API_?KEY|PRIVATE_?KEY)", re.IGNORECASE)
REQUIRED_VAR = re.compile(r"^\$\{[A-Z_]+:\?[^}]*\}$")
PLACEHOLDER = re.compile(r"(replaced|placeholder|changeme|change-me|set-by|from-the-environment)", re.IGNORECASE)


def load(path: Path = COMPOSE) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def images(compose: dict) -> list[str]:
    return [s["image"] for s in compose["services"].values()]


def unpinned(compose: dict) -> list[str]:
    bad = []
    for ref in images(compose):
        tag = ref.split("@")[0].rsplit(":", 1)[-1]
        if not PINNED.match(ref) or tag in MUTABLE_TAGS:
            bad.append(ref)
    return bad


def port_problems(compose: dict) -> list[str]:
    bad = []
    for name, svc in compose["services"].items():
        for p in svc.get("ports", []):
            p = p if isinstance(p, str) else str(p)
            if WILDCARD.search(p) or not BIND_OK.match(p):
                bad.append(f"{name}: {p}")
    return bad


def cache_problems(compose: dict) -> list[str]:
    bad = []
    for name, svc in compose["services"].items():
        if "valkey" in svc["image"] or "redis" in svc["image"]:
            if svc.get("ports"):
                bad.append(f"{name} publishes ports")
            if "network_mode" in svc:
                bad.append(f"{name} sets network_mode")
            nets = svc.get("networks", [])
            if not nets or any(not compose["networks"][n].get("internal") for n in nets):
                bad.append(f"{name} is on a network that is not internal")
        for p in svc.get("ports", []):
            if "6379" in str(p):
                bad.append(f"{name} publishes 6379")
    return bad


def secret_value_problems(compose: dict) -> list[str]:
    """Any environment value whose name looks secret must be a required variable (or empty), never a literal."""
    bad = []
    for name, svc in compose["services"].items():
        env = svc.get("environment", {})
        if isinstance(env, list):
            env = dict(e.split("=", 1) for e in env)
        for key, val in env.items():
            if SECRET_NAME.search(key) and val not in (None, "") and not REQUIRED_VAR.match(str(val)):
                bad.append(f"{name}.{key}")
    return bad


def env_file_problems(text: str) -> list[str]:
    bad = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, val = s.split("=", 1)
        if SECRET_NAME.search(key) and val.strip().strip("\"'") != "":
            bad.append(key)
    return bad


def settings_problems(settings: dict) -> list[str]:
    bad = []
    server = settings.get("server", {})
    if server.get("limiter") is not True:
        bad.append("server.limiter is not true")
    if server.get("public_instance") is not False:
        bad.append("server.public_instance is not false")
    if not str(settings.get("valkey", {}).get("url", "")).startswith("valkey://"):
        bad.append("valkey.url is missing (the limiter needs it)")
    key = str(server.get("secret_key", ""))
    if key == "ultrasecretkey" or not PLACEHOLDER.search(key):
        bad.append("server.secret_key is not a placeholder")
    out = settings.get("outgoing", {}) or {}
    if out.get("proxies") or out.get("using_tor_proxy"):
        bad.append("an outgoing proxy is on by default")
    return bad


def env_override_problems(compose: dict) -> list[str]:
    """The environment overrides the file in SearXNG, so it must not switch the guards off."""
    bad = []
    for name, svc in compose["services"].items():
        env = svc.get("environment", {}) or {}
        if isinstance(env, list):
            env = dict(e.split("=", 1) for e in env)
        if str(env.get("SEARXNG_LIMITER", "true")).lower() not in ("true", "1"):
            bad.append(f"{name}: SEARXNG_LIMITER is off")
        if str(env.get("SEARXNG_PUBLIC_INSTANCE", "false")).lower() not in ("false", "0"):
            bad.append(f"{name}: SEARXNG_PUBLIC_INSTANCE is on")
    return bad


# ---- the real files -------------------------------------------------------------------------------------------


def test_the_workload_files_exist():
    for p in (COMPOSE, SETTINGS, LIMITER, ENV_EXAMPLE, README):
        assert p.is_file(), p


def test_the_compose_file_parses_and_has_the_two_services():
    compose = load()
    assert set(compose["services"]) == {"core", "valkey"}
    assert compose["networks"]["backend"]["internal"] is True


def test_every_image_is_pinned_by_tag_and_digest():
    refs = images(load())
    assert len(refs) == 2, "the guard collected too little"
    assert not unpinned(load()), unpinned(load())


def test_the_pins_guard_bites():
    good = {"services": {"a": {"image": "docker.io/x/y:1.2.3@sha256:" + "a" * 64}}}
    assert not unpinned(good)
    assert unpinned({"services": {"a": {"image": "docker.io/x/y:latest"}}})
    assert unpinned({"services": {"a": {"image": "docker.io/x/y:1.2.3"}}})
    assert unpinned({"services": {"a": {"image": "docker.io/x/y@sha256:" + "a" * 64}}})
    assert unpinned({"services": {"a": {"image": "docker.io/x/y:latest@sha256:" + "a" * 64}}})


def test_every_published_port_is_bound_to_the_private_address():
    compose = load()
    published = [p for s in compose["services"].values() for p in s.get("ports", [])]
    assert len(published) == 1, "the guard collected the wrong number of ports"
    assert not port_problems(compose)
    assert not WILDCARD.search(COMPOSE.read_text(encoding="utf-8"))


def test_the_port_guard_bites():
    def one(p: str) -> dict:
        return {"services": {"core": {"image": "x", "ports": [p]}}}

    assert not port_problems(one("${SEARXNG_BIND:?set the private address}:8080:8080"))
    assert not port_problems(one("10.116.0.5:8080:8080"))
    for bad in ("8080:8080", "0.0.0.0:8080:8080", "[::]:8080:8080", ":::8080:8080", "${SEARXNG_BIND:-0.0.0.0}:8080:8080", "127.0.0.1:8080:8080x"):
        assert port_problems(one(bad)), bad
    assert WILDCARD.search("0.0.0.0:8080:8080")


def test_the_cache_is_not_published_and_sits_on_an_internal_network():
    compose = load()
    assert "valkey" in compose["services"]["valkey"]["image"], "the guard collected nothing"
    assert not cache_problems(compose)


def test_the_cache_guard_bites():
    base = {"networks": {"backend": {"internal": True}, "open": {}}}
    ok = {"services": {"v": {"image": "valkey/valkey:1@sha256:x", "networks": ["backend"]}}, **base}
    assert not cache_problems(ok)
    published = {"services": {"v": {"image": "valkey/valkey:1", "networks": ["backend"], "ports": ["10.0.0.1:6379:6379"]}}, **base}
    assert cache_problems(published)
    exposed = {"services": {"v": {"image": "valkey/valkey:1", "networks": ["open"]}}, **base}
    assert cache_problems(exposed)
    host_net = {"services": {"v": {"image": "valkey/valkey:1", "network_mode": "host", "networks": ["backend"]}}, **base}
    assert cache_problems(host_net)
    redis = {"services": {"v": {"image": "redis:7", "ports": ["6379:6379"]}}, **base}
    assert cache_problems(redis)


def test_no_secret_value_is_in_any_workload_file():
    compose = load()
    assert not secret_value_problems(compose)
    assert "SEARXNG_SECRET" in str(compose["services"]["core"]["environment"]), "the guard collected nothing"
    assert REQUIRED_VAR.match(compose["services"]["core"]["environment"]["SEARXNG_SECRET"])
    assert not env_file_problems(ENV_EXAMPLE.read_text(encoding="utf-8"))
    settings = load(SETTINGS)
    assert PLACEHOLDER.search(settings["server"]["secret_key"])
    for p in (COMPOSE, SETTINGS, LIMITER, ENV_EXAMPLE):
        assert "ultrasecretkey" not in p.read_text(encoding="utf-8"), p


def test_the_secret_guard_bites():
    bad = {"services": {"core": {"image": "x", "environment": {"SEARXNG_SECRET": "z" * 32}}}}
    assert secret_value_problems(bad) == ["core.SEARXNG_SECRET"]
    as_list = {"services": {"core": {"image": "x", "environment": ["DB_PASSWORD=hunter2hunter2"]}}}
    assert secret_value_problems(as_list) == ["core.DB_PASSWORD"]
    assert not secret_value_problems({"services": {"core": {"image": "x", "environment": {"SEARXNG_SECRET": "${SEARXNG_SECRET:?set it}"}}}})
    assert env_file_problems("SEARXNG_SECRET=" + "z" * 16 + "\n") == ["SEARXNG_SECRET"]
    assert not env_file_problems("# SEARXNG_SECRET=abc\nSEARXNG_SECRET=\n")


def test_the_settings_file_has_the_limiter_on_and_the_instance_not_public():
    settings = load(SETTINGS)
    assert settings["server"]["limiter"] is True, "the guard collected nothing"
    assert not settings_problems(settings)
    assert not env_override_problems(load())


def test_the_settings_guard_bites():
    good = load(SETTINGS)
    for path, value, needle in (
        (("server", "limiter"), False, "limiter"),
        (("server", "public_instance"), True, "public_instance"),
        (("server", "secret_key"), "ultrasecretkey", "secret_key"),
        (("server", "secret_key"), "k3J9xQ2mZ8vL5nR7", "secret_key"),
    ):
        bad = yaml.safe_load(yaml.safe_dump(good))
        bad[path[0]][path[1]] = value
        assert any(needle in p for p in settings_problems(bad)), path
    no_valkey = yaml.safe_load(yaml.safe_dump(good))
    no_valkey["valkey"] = {"url": False}
    assert any("valkey" in p for p in settings_problems(no_valkey))
    tor = yaml.safe_load(yaml.safe_dump(good))
    tor["outgoing"] = {"using_tor_proxy": True}
    assert any("proxy" in p for p in settings_problems(tor))


def test_the_environment_cannot_switch_the_guards_off():
    off = {"services": {"core": {"image": "x", "environment": {"SEARXNG_LIMITER": "false"}}}}
    assert env_override_problems(off)
    public = {"services": {"core": {"image": "x", "environment": ["SEARXNG_PUBLIC_INSTANCE=true"]}}}
    assert env_override_problems(public)
    assert not env_override_problems({"services": {"core": {"image": "x", "environment": {"SEARXNG_LIMITER": "true"}}}})


def test_the_limiter_file_parses_and_trusts_no_private_range_as_a_proxy():
    cfg = tomllib.loads(LIMITER.read_text(encoding="utf-8"))
    trusted = cfg["botdetection"]["trusted_proxies"]
    assert trusted, "the guard collected nothing"
    assert set(trusted) <= {"127.0.0.0/8", "::1"}, trusted
    assert cfg["botdetection"]["ip_limit"]["link_token"] is False
    assert cfg["botdetection"]["ip_lists"]["pass_searxng_org"] is False


def test_the_tor_proxy_is_a_documented_option_and_off_by_default():
    text = SETTINGS.read_text(encoding="utf-8")
    assert "socks5h://" in text and "using_tor_proxy" in text, "the option is not documented in the settings file"
    assert not (load(SETTINGS).get("outgoing") or {}).get("proxies")
    assert not any("tor" in name for name in load()["services"])
    readme = README.read_text(encoding="utf-8")
    assert "off by default" in readme and "socks5h" in readme


def test_both_services_have_a_memory_limit_and_no_new_privileges():
    for name, svc in load()["services"].items():
        assert "mem_limit" in svc, name
        assert "no-new-privileges:true" in svc.get("security_opt", []), name


def test_the_readme_says_nothing_was_applied_and_links_the_lesson():
    readme = README.read_text(encoding="utf-8")
    assert "Not applied" in readme and "Not verified" in readme
    assert "Self-Hosting" in readme
    for needle in ("2026-11-01", "sha256:", "Twingate", "Portainer"):
        assert needle in readme, needle


def test_the_digests_in_the_readme_match_the_compose_file():
    digests = {ref.split("@")[1] for ref in images(load())}
    readme = README.read_text(encoding="utf-8")
    assert len(digests) == 2
    for d in digests:
        assert d in readme, d
