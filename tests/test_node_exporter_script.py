"""Hermetic tests for the node-exporter wrapper in the connector cloud-init.

The script is extracted from modules/twingate-bootstrap/cloud-init.yaml.tftpl
(same extraction as the host-firewall tests) and run with a fake `ip` on a PATH
that holds nothing but that fake and awk, inside a temporary directory. The
exporter binary it `exec`s is replaced by a fake that records its arguments.
Nothing here touches this machine's network or services. Documentation and
private ranges only.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from test_host_firewall_script import TEMPLATE, extract_file

BASH = shutil.which("bash")
AWK = shutil.which("awk")
SCRIPT_PATH = "/usr/local/sbin/cah-node-exporter-run"
EXPORTER = "/usr/bin/prometheus-node-exporter"
DROPIN_PATH = "/etc/systemd/system/prometheus-node-exporter.service.d/10-cah-private-bind.conf"

pytestmark = pytest.mark.skipif(BASH is None or AWK is None, reason="bash and awk are required")

# `ip -4 -o addr show scope global` on a DigitalOcean-like machine: the public
# address on eth0 (documentation range) and the VPC address on eth1.
DO_LIKE = (
    "2: eth0    inet 203.0.113.10/20 brd 203.0.113.255 scope global eth0\\       valid_lft forever\n"
    "3: eth1    inet 10.118.0.2/20 brd 10.118.15.255 scope global eth1\\       valid_lft forever\n"
)
PUBLIC_ONLY = "2: eth0    inet 203.0.113.10/20 brd 203.0.113.255 scope global eth0\n"


def extract(port: str = "9100") -> str:
    return extract_file(
        TEMPLATE.read_text(encoding="utf-8"), SCRIPT_PATH, {"node_exporter_port": port}
    )


def run_script(tmp: Path, ip_out: str, port: str = "9100"):
    bindir = tmp / "bin"
    bindir.mkdir()
    (tmp / "ip.out").write_text(ip_out)
    fake_ip = bindir / "ip"
    fake_ip.write_text(
        f"#!{BASH}\n"
        'while IFS= read -r l || [ -n "$l" ]; do printf \'%s\\n\' "$l"; done '
        f'< "{tmp / "ip.out"}"\n'
    )
    fake_ip.chmod(0o755)
    (bindir / "awk").symlink_to(AWK)
    args_file = tmp / "exporter.args"
    fake_exporter = tmp / "fake-exporter"
    fake_exporter.write_text(f'#!{BASH}\nprintf \'%s\\n\' "$@" > "{args_file}"\n')
    fake_exporter.chmod(0o755)
    script = tmp / "run.sh"
    text = extract(port)
    assert EXPORTER in text
    script.write_text(text.replace(EXPORTER, str(fake_exporter)))
    proc = subprocess.run(
        [BASH, str(script)],
        env={"PATH": str(bindir), "HOME": str(tmp)},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return proc, (args_file.read_text() if args_file.exists() else None)


def test_extraction_finds_the_script():
    assert extract().startswith("#!/usr/bin/env bash\n")


def test_picks_the_private_address_not_the_public_one(tmp_path):
    proc, args = run_script(tmp_path, DO_LIKE)
    assert proc.returncode == 0, proc.stderr
    assert args == "--web.listen-address=10.118.0.2:9100\n"


def test_uses_the_configured_port(tmp_path):
    proc, args = run_script(tmp_path, DO_LIKE, port="9200")
    assert proc.returncode == 0, proc.stderr
    assert args == "--web.listen-address=10.118.0.2:9200\n"


@pytest.mark.parametrize("addr", ["10.0.0.5", "172.16.0.5", "172.31.255.1", "192.168.1.1"])
def test_every_rfc1918_block_is_accepted(tmp_path, addr):
    line = f"2: eth0    inet {addr}/24 brd 0.0.0.0 scope global eth0\n"
    proc, args = run_script(tmp_path, line)
    assert proc.returncode == 0, proc.stderr
    assert args == f"--web.listen-address={addr}:9100\n"


# Negative cases: the guard bites. With no private address the script fails and
# never execs the exporter, so the unit fails and there is no wildcard fallback.
@pytest.mark.parametrize(
    "ip_out",
    [
        PUBLIC_ONLY,
        "",
        "2: eth0    inet 172.32.0.1/24 scope global eth0\n",
        "2: eth0    inet 172.15.0.1/24 scope global eth0\n",
        "2: eth0    inet 100.64.0.1/10 scope global eth0\n",
    ],
    ids=["public-only", "no-address", "172.32", "172.15", "cgnat"],
)
def test_no_private_address_fails_closed(tmp_path, ip_out):
    proc, args = run_script(tmp_path, ip_out)
    assert proc.returncode != 0
    assert args is None
    assert "refusing to start" in proc.stderr


def test_the_script_never_writes_a_wildcard_address():
    text = extract()
    assert "0.0.0.0" not in text
    assert not re.search(r"listen-address=:", text)
    assert "exec " + EXPORTER in text


def test_dropin_replaces_exec_start_with_the_wrapper_and_nothing_order_dependent():
    text = extract_file(TEMPLATE.read_text(encoding="utf-8"), DROPIN_PATH)
    lines = text.splitlines()
    # An empty ExecStart= clears the package's own command line before ours.
    first = lines.index("ExecStart=")
    assert lines[first + 1] == "ExecStart=/usr/local/sbin/cah-node-exporter-run"
    # systemd reads EnvironmentFile= before ExecStartPre= runs, so neither may
    # carry the address.
    assert "EnvironmentFile" not in text and "ExecStartPre" not in text


def test_extraction_negative_case_missing_path_is_an_error():
    with pytest.raises(AssertionError):
        extract_file(TEMPLATE.read_text(encoding="utf-8"), "/etc/not-written")


def test_template_gates_every_node_exporter_piece_on_the_flag():
    # Every mention of the exporter must sit inside a node_exporter conditional,
    # so the default render is unchanged.
    text = TEMPLATE.read_text(encoding="utf-8")
    needles = (
        "- prometheus-node-exporter",
        SCRIPT_PATH,
        "prometheus-node-exporter.service.d",
        "systemctl restart prometheus-node-exporter",
        "node_exporter_rule",
        "host_firewall_node_exporter",
    )
    for needle in needles:
        found = list(re.finditer(re.escape(needle), text))
        assert found, f"{needle} is not in the template"
        for m in found:
            before = text[: m.start()]
            assert before.rfind("%{ if node_exporter ~}") > before.rfind("%{ endif ~}"), (
                f"{needle} is outside a node_exporter conditional"
            )
