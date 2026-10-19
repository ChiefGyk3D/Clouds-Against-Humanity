"""Synthetic metrics for the demo monitoring stack.

Everything here is invented. Four fake hosts (two sites, two connectors each)
each get their own port and serve two paths:

  /connector  twingate_* metrics (names verified against Twingate's docs)
  /node       a small slice of standard node exporter metrics

A site "goes silent" when its name is in the file named by DEMO_SILENT_FILE
(one site per line) or in the DEMO_SILENT_SITE environment variable. A silent
host answers HTTP 503, so Prometheus records up == 0 for it: the series still
exist, which is the case the expected-target inventory alert is built for.

Counters keep growing while a host is silent, as they would on a real host
whose tunnel is down but whose machine is still running.
"""

import math
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SILENT_FILE = os.environ.get("DEMO_SILENT_FILE", "/state/silent")
SILENT_ENV = os.environ.get("DEMO_SILENT_SITE", "")

# "base" scales the load, "boot_age" is how long the fake host has been up at start (seconds).
HOSTS = [
    {"name": "site-tor1-a", "site": "site-tor1", "port": 9101, "base": 1.0, "boot_age": 3 * 86400, "phase": 0.0},
    {"name": "site-tor1-b", "site": "site-tor1", "port": 9102, "base": 0.8, "boot_age": 2 * 86400, "phase": 1.1},
    {"name": "site-tor2-a", "site": "site-tor2", "port": 9103, "base": 0.6, "boot_age": 5 * 86400, "phase": 2.3},
    {"name": "site-tor2-b", "site": "site-tor2", "port": 9104, "base": 0.5, "boot_age": 4 * 86400, "phase": 3.7},
]

CPUS = 2
MEM_TOTAL = 4 * 1024**3
DISK_TOTAL = 80 * 1024**3
SWAP_TOTAL = 1024**3
PERIOD = 600.0  # seconds per synthetic "day", so a few minutes of data already has a shape


class Host:
    def __init__(self, cfg):
        self.cfg = cfg
        self.rng = random.Random(cfg["name"])
        self.start = time.time()
        self.boot = self.start - cfg["boot_age"]
        self.lock = threading.Lock()
        self.cpu = {m: [0.0] * CPUS for m in ("idle", "user", "system", "iowait")}
        self.net = {"rx": 0.0, "tx": 0.0}
        self.tun = {(d, t): 0.0 for d in ("in", "out") for t in ("direct", "relay")}
        self.busy = 0.1
        self.mem_used = 0.35
        self.disk_used = 0.42
        self.load = 0.1

    def tick(self, now, dt):
        c = self.cfg
        wave = 0.5 + 0.5 * math.sin(2 * math.pi * now / PERIOD + c["phase"])
        with self.lock:
            self.busy = min(0.95, max(0.02, 0.05 + 0.25 * c["base"] * wave + self.rng.uniform(-0.01, 0.02)))
            for i in range(CPUS):
                f = min(0.98, max(0.01, self.busy + self.rng.uniform(-0.01, 0.01)))
                self.cpu["idle"][i] += (1 - f) * dt
                self.cpu["user"][i] += 0.7 * f * dt
                self.cpu["system"][i] += 0.25 * f * dt
                self.cpu["iowait"][i] += 0.05 * f * dt
            self.load = 0.8 * self.load + 0.2 * (self.busy * CPUS * 1.2)
            self.mem_used = min(0.8, 0.35 + 0.05 * wave + 0.00001 * (now - self.start))
            self.disk_used = min(0.95, 0.42 + 0.000002 * (now - self.start))
            rate = 400_000 * c["base"] * (0.4 + wave) * self.rng.uniform(0.9, 1.1)
            self.net["rx"] += rate * dt
            self.net["tx"] += rate * 0.7 * dt
            self.tun[("in", "direct")] += rate * 0.8 * dt
            self.tun[("in", "relay")] += rate * 0.2 * dt
            self.tun[("out", "direct")] += rate * 0.6 * dt
            self.tun[("out", "relay")] += rate * 0.15 * dt

    def connector(self, now):
        lines = [
            "# HELP twingate_inbound_bytes_total Bytes received by the connector, by transport (synthetic).",
            "# TYPE twingate_inbound_bytes_total counter",
        ]
        with self.lock:
            for t in ("direct", "relay"):
                lines.append(f'twingate_inbound_bytes_total{{transport="{t}"}} {self.tun[("in", t)]:.0f}')
            lines += [
                "# HELP twingate_outbound_bytes_total Bytes sent by the connector, by transport (synthetic).",
                "# TYPE twingate_outbound_bytes_total counter",
            ]
            for t in ("direct", "relay"):
                lines.append(f'twingate_outbound_bytes_total{{transport="{t}"}} {self.tun[("out", t)]:.0f}')
        lines += [
            "# HELP twingate_connector_uptime_seconds Seconds since the connector started (synthetic).",
            "# TYPE twingate_connector_uptime_seconds gauge",
            f"twingate_connector_uptime_seconds {now - self.boot:.0f}",
        ]
        return "\n".join(lines) + "\n"

    def node(self, now):
        out = ["# TYPE node_cpu_seconds_total counter"]
        with self.lock:
            for mode, vals in self.cpu.items():
                for cpu, v in enumerate(vals):
                    out.append(f'node_cpu_seconds_total{{cpu="{cpu}",mode="{mode}"}} {v:.2f}')
            out += [
                "# TYPE node_memory_MemTotal_bytes gauge",
                f"node_memory_MemTotal_bytes {MEM_TOTAL}",
                "# TYPE node_memory_MemAvailable_bytes gauge",
                f"node_memory_MemAvailable_bytes {MEM_TOTAL * (1 - self.mem_used):.0f}",
                "# TYPE node_filesystem_size_bytes gauge",
                f'node_filesystem_size_bytes{{device="/dev/vda1",fstype="ext4",mountpoint="/"}} {DISK_TOTAL}',
                "# TYPE node_filesystem_avail_bytes gauge",
                f'node_filesystem_avail_bytes{{device="/dev/vda1",fstype="ext4",mountpoint="/"}} '
                f"{DISK_TOTAL * (1 - self.disk_used):.0f}",
                "# TYPE node_memory_SwapTotal_bytes gauge",
                f"node_memory_SwapTotal_bytes {SWAP_TOTAL}",
                "# TYPE node_memory_SwapFree_bytes gauge",
                f"node_memory_SwapFree_bytes {SWAP_TOTAL * (1 - 0.02 * self.mem_used):.0f}",
                "# TYPE node_load1 gauge",
                f"node_load1 {self.load:.2f}",
                "# TYPE node_network_receive_bytes_total counter",
                f'node_network_receive_bytes_total{{device="eth0"}} {self.net["rx"]:.0f}',
                "# TYPE node_network_transmit_bytes_total counter",
                f'node_network_transmit_bytes_total{{device="eth0"}} {self.net["tx"]:.0f}',
                "# TYPE node_network_receive_errs_total counter",
                'node_network_receive_errs_total{device="eth0"} 0',
                "# TYPE node_network_transmit_errs_total counter",
                'node_network_transmit_errs_total{device="eth0"} 0',
                "# TYPE node_network_receive_drop_total counter",
                'node_network_receive_drop_total{device="eth0"} 0',
                "# TYPE node_network_transmit_drop_total counter",
                'node_network_transmit_drop_total{device="eth0"} 0',
            ]
        out += [
            "# TYPE node_boot_time_seconds gauge",
            f"node_boot_time_seconds {self.boot:.0f}",
            "# TYPE node_time_seconds gauge",
            f"node_time_seconds {now:.0f}",
        ]
        return "\n".join(out) + "\n"


def silent_sites():
    sites = {s.strip() for s in SILENT_ENV.replace(",", "\n").splitlines() if s.strip()}
    try:
        with open(SILENT_FILE, encoding="utf-8") as fh:
            sites |= {line.strip() for line in fh if line.strip() and not line.startswith("#")}
    except OSError:
        pass
    return sites


def make_handler(host):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - http.server API
            if host.cfg["site"] in silent_sites():
                self.send_error(503, "synthetic outage")
                return
            now = time.time()
            if self.path == "/connector":
                body = host.connector(now)
            elif self.path == "/node":
                body = host.node(now)
            else:
                self.send_error(404)
                return
            data = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    return Handler


def main():
    hosts = [Host(cfg) for cfg in HOSTS]
    # Backfill an hour of counters so rates are non-zero from the first scrape.
    now = time.time()
    for step in range(3600):
        for h in hosts:
            h.tick(now - 3600 + step, 1.0)
    for h in hosts:
        srv = ThreadingHTTPServer(("0.0.0.0", h.cfg["port"]), make_handler(h))  # noqa: S104 - compose network only
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    last = time.time()
    while True:
        time.sleep(1)
        now = time.time()
        for h in hosts:
            h.tick(now, now - last)
        last = now


if __name__ == "__main__":
    main()
