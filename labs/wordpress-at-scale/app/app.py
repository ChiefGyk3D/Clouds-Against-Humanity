# SPDX-License-Identifier: Apache-2.0
"""A tiny stand-in for one stateless WordPress web node. It is NOT WordPress.

It exists so you can watch the layers around a WordPress fleet (CDN-like cache,
load balancer, shared object cache, node-local disk) with nothing to install and
nothing to patch. It speaks just enough of the Redis protocol (RESP) to be an
object-cache client without any third-party library.

Routes
  GET  /                  a "page": reads a post from the object cache, falls back to a slow "database"
  GET  /slow?k=NAME       one slow "database" query, counted in Redis (the stampede drill)
  GET  /hits              a shared counter in Redis (state that must NOT live on a node)
  POST /wp-login.php      sets a made-up login cookie named like WordPress's
  POST /upload-local?name=X   writes to THIS node's disk (the plugin-writes-to-disk mistake)
  POST /upload-shared?name=X  writes to the shared volume (the fix)
  GET  /local-files/X, /shared-files/X
  GET  /stats, POST /reset-stats
  GET  /healthz
"""

import json
import os
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

NODE = os.environ.get("NODE_NAME", "web")
REDIS = (os.environ.get("REDIS_HOST", "redis"), 6379)
LOCAL_DIR = Path(os.environ.get("LOCAL_UPLOADS", "/var/local-uploads"))
SHARED_DIR = Path(os.environ.get("SHARED_UPLOADS", "/shared"))
DB_DELAY = float(os.environ.get("DB_DELAY", "0.4"))
CRON_EVERY = 10  # seconds between "scheduled jobs"; WordPress's WP-Cron also rides on page loads
LOGIN_COOKIE = "wordpress_logged_in_demo"


class RedisDown(Exception):
    pass


def redis(*args):
    """One command, one connection. Returns the decoded reply; raises RedisDown on any failure."""
    parts = [b"*%d\r\n" % len(args)]
    for a in args:
        b = a if isinstance(a, bytes) else str(a).encode()
        parts.append(b"$%d\r\n%s\r\n" % (len(b), b))
    try:
        with socket.create_connection(REDIS, timeout=0.3) as s:
            s.settimeout(0.5)
            s.sendall(b"".join(parts))
            f = s.makefile("rb")
            line = f.readline().rstrip(b"\r\n")
            kind, rest = line[:1], line[1:]
            if kind in (b"+", b":"):
                return rest.decode() if kind == b"+" else int(rest)
            if kind == b"$":
                n = int(rest)
                return None if n < 0 else f.read(n + 2)[:-2].decode()
            raise RedisDown(line.decode())
    except (OSError, ValueError) as exc:
        raise RedisDown(str(exc)) from exc


def maybe_run_cron():
    """A WP-Cron lookalike: due jobs run during a page load, at most one node at a time."""
    try:
        if redis("SET", "cron:lock", NODE, "NX", "EX", CRON_EVERY) == "OK":
            redis("INCR", "cron_runs")
    except RedisDown:
        pass


def get_post():
    """Object cache first; on a miss do the slow 'database' read and store it for 30 seconds."""
    try:
        cached = redis("GET", "post:1")
        if cached is not None:
            return cached, "hit"
        state = "miss"
    except RedisDown:
        state = "down"
    time.sleep(DB_DELAY)  # the 'database'
    post = "Hello from the post table"
    try:
        if state == "miss":
            redis("SETEX", "post:1", 30, post)
    except RedisDown:
        state = "down"
    return post, state


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "stand-in"

    def log_message(self, fmt, *args):  # one short line per request, to the container log
        print(f"{NODE} {self.command} {self.path} {fmt % args}", flush=True)

    def reply(self, code, body, ctype="text/html; charset=utf-8", cache="no-store", extra=()):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Node", NODE)
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def logged_in(self):
        return LOGIN_COOKIE in (self.headers.get("Cookie") or "")

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if url.path == "/healthz":
            return self.reply(200, "ok\n", "text/plain")
        if url.path == "/":
            maybe_run_cron()
            started = time.time()
            post, state = get_post()
            who = "Welcome back, demo-user (this page is private)" if self.logged_in() else "Hello, visitor"
            cache = "private, no-store" if self.logged_in() else "public, max-age=30"
            body = (f"<h1>{who}</h1><p>{post}</p><p>built by {NODE} at {time.strftime('%H:%M:%S')}"
                    f" in {int((time.time() - started) * 1000)} ms; object cache: {state}</p>\n")
            return self.reply(200, body, cache=cache, extra=[("X-Obj-Cache", state)])
        if url.path == "/slow":
            time.sleep(1.0)  # an expensive uncached query
            try:
                redis("INCR", "db_queries")
            except RedisDown:
                pass
            return self.reply(200, f"slow {q.get('k', [''])[0]} by {NODE}\n", "text/plain", "public, max-age=30")
        if url.path == "/hits":
            try:
                return self.reply(200, f"hits={redis('INCR', 'hits')} served by {NODE}\n", "text/plain")
            except RedisDown:
                return self.reply(503, "shared counter unavailable\n", "text/plain")
        if url.path == "/stats":
            try:
                stats = {k: int(redis("GET", k) or 0) for k in ("db_queries", "hits", "cron_runs")}
            except RedisDown:
                stats = {"error": "redis down"}
            return self.reply(200, json.dumps(stats) + "\n", "application/json")
        for prefix, base in (("/local-files/", LOCAL_DIR), ("/shared-files/", SHARED_DIR)):
            if url.path.startswith(prefix):
                name = os.path.basename(url.path[len(prefix):])
                path = base / name
                if name and path.is_file():
                    return self.reply(200, path.read_bytes(), "application/octet-stream")
                return self.reply(404, f"{name}: not on {NODE}\n", "text/plain")
        return self.reply(404, "not found\n", "text/plain")

    def do_POST(self):
        url = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(min(n, 65536))
        if url.path == "/wp-login.php":
            return self.reply(200, "logged in\n", "text/plain",
                              extra=[("Set-Cookie", f"{LOGIN_COOKIE}=1; Path=/; HttpOnly")])
        if url.path == "/reset-stats":
            try:
                redis("DEL", "db_queries", "hits", "cron_runs", "cron:lock", "post:1")
            except RedisDown:
                pass
            return self.reply(200, "reset\n", "text/plain")
        for route, base in (("/upload-local", LOCAL_DIR), ("/upload-shared", SHARED_DIR)):
            if url.path == route:
                name = os.path.basename(parse_qs(url.query).get("name", [""])[0])
                if not name:
                    return self.reply(400, "name required\n", "text/plain")
                base.mkdir(parents=True, exist_ok=True)
                (base / name).write_bytes(body)
                return self.reply(201, f"{name} written on {NODE}\n", "text/plain")
        return self.reply(404, "not found\n", "text/plain")


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
