# SPDX-License-Identifier: Apache-2.0
"""Two loopback HTTP servers the onion lab tests share: one that makes the mistakes the lesson lists and one that does not.

They bind 127.0.0.1 on an ephemeral port, serve fixed bytes and are shut down by the caller. Nothing leaves the machine.
"""

import contextlib
import http.server
import threading


class Leaky(http.server.BaseHTTPRequestHandler):
    """A version in Server, a stack header, a clearnet image, an address in the text and a status page."""

    server_version = "nginx/1.30.6"
    sys_version = ""

    def do_GET(self):
        if self.path == "/server-status":
            body, code = b"Total Accesses: 1", 200
        elif self.path == "/":
            body, code = b'<img src="https://cdn.example.test/logo.png"><p>host 203.0.113.9</p>', 200
        else:
            body, code = b"nope", 404
        self.send_response(code)
        self.send_header("X-Powered-By", "PHP/8.3")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class Clean(http.server.BaseHTTPRequestHandler):
    """The lab page: the word nginx and nothing else in the headers, plain text, a plain 404."""

    server_version = "nginx"
    sys_version = ""

    def do_GET(self):
        body, code = (b"<p>plain</p>", 200) if self.path == "/" else (b"Not found.", 404)
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@contextlib.contextmanager
def serving(handler):
    """Yield the port of a loopback server running `handler`; shut it down on exit."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
