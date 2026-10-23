#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""triage.py FILE.eml [--protect example.test]: read a message the way a phishing responder does.

It never opens, renders or runs anything. It reads headers and text, lists links and attachments
(name, type, size, SHA-256) and prints a worksheet with the open questions left blank for a human.
Its flags are hints for a person, not a verdict.
"""
import argparse
import hashlib
import re
import sys
from html.parser import HTMLParser
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from urllib.parse import urlparse

RISKY = {".html", ".htm", ".iso", ".img", ".lnk", ".js", ".vbs", ".exe", ".scr", ".one", ".docm", ".xlsm", ".jar", ".hta"}
HOMOGLYPHS = str.maketrans({"1": "l", "0": "o", "5": "s", "3": "e"})


def skeleton(domain):
    return domain.lower().replace("rn", "m").translate(HOMOGLYPHS)


def distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class Anchors(HTMLParser):
    """Collect (href, visible text) for every <a>, whatever quote style the attribute uses."""

    def __init__(self):
        super().__init__()
        self.found, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._text = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.found.append((self._href, "".join(self._text).strip()))
            self._href = None


def host(url):
    return (urlparse(url).hostname or "").lower()


def analyze(path, protect):
    msg = BytesParser(policy=policy.default).parsebytes(open(path, "rb").read())
    flags = []
    name, addr = parseaddr(str(msg["From"]))
    dom = addr.rpartition("@")[2].lower()
    rp = parseaddr(str(msg["Return-Path"] or ""))[1].rpartition("@")[2].lower()
    reply = parseaddr(str(msg["Reply-To"] or ""))[1].rpartition("@")[2].lower()
    if "@" in name and parseaddr(name)[1].lower() != addr.lower():
        flags.append(f"display name contains a different address ({name!r}) than the real one ({addr})")
    if rp and rp != dom:
        flags.append(f"envelope sender domain ({rp}) differs from the From domain ({dom}); fine for bulk mailers, check it")
    if reply and reply != dom:
        flags.append(f"Reply-To domain ({reply}) differs from the From domain ({dom}): replies go somewhere else")
    for p in protect:
        if dom != p and (skeleton(dom) == skeleton(p) or distance(dom, p) <= 2):
            flags.append(f"From domain {dom} looks like the protected domain {p}")
        if dom != p and p.split(".")[0] in name.lower():
            flags.append(f"display name {name!r} mentions {p.split('.')[0]} but the domain is {dom}")
    ars = msg.get_all("Authentication-Results") or []
    received = msg.get_all("Received") or []
    if len(ars) > 1:
        flags.append(f"{len(ars)} Authentication-Results headers: trust only the one stamped by YOUR server's authserv-id, the topmost")
    links, atts = [], []
    for part in msg.walk():
        ctype = part.get_content_type()
        if part.get_filename():
            data = part.get_payload(decode=True) or b""
            ext = "." + part.get_filename().rsplit(".", 1)[-1].lower() if "." in part.get_filename() else ""
            atts.append((part.get_filename(), ctype, len(data), hashlib.sha256(data).hexdigest()))
            if ext in RISKY or part.get_filename().lower().count(".") > 1:
                flags.append(f"attachment {part.get_filename()!r}: risky or double extension; never open it outside a sandbox you own")
        elif ctype in ("text/plain", "text/html"):
            text = part.get_content()
            if ctype == "text/html":
                parser = Anchors()
                parser.feed(text)
                parser.close()
                for href, label in parser.found:
                    links.append((href, label))
                    shown = re.search(r"https?://[^\s<]+", label)
                    if shown and host(shown.group(0)) != host(href):
                        flags.append(f"link text shows {host(shown.group(0))} but goes to {host(href)}")
                if re.search(r"<img\b", text, re.I) and len(re.sub(r"<[^>]+>", "", text).strip()) < 20:
                    flags.append("body is almost only an image: a QR code hides the destination from text scanners; do not scan it on a work phone")
            else:
                for u in re.findall(r"https?://[^\s<>\"]+", text):
                    links.append((u, ""))
    for href, _ in links:
        h = host(href)
        if h.startswith("xn--") or ".xn--" in h:
            flags.append(f"link host {h} is punycode (an internationalized look-alike is possible)")
        if re.fullmatch(r"[\d.]+", h):
            flags.append(f"link host {h} is a bare IP address")
    return {"from": (name, addr), "return_path": rp, "reply_to": reply, "subject": str(msg["Subject"]),
            "authres": [str(a) for a in ars], "received": [str(r).replace("\r\n", " ").replace("\n", " ") for r in received],
            "links": links, "attachments": atts, "flags": flags}


def worksheet(path, a):
    L = [f"# Phishing triage worksheet: {path}", "", "## 1. Headers", f"- From: {a['from'][0]!r} <{a['from'][1]}>",
         f"- Return-Path domain: {a['return_path'] or '(none)'}   Reply-To domain: {a['reply_to'] or '(none)'}",
         f"- Subject: {a['subject']}"]
    L += [f"- Authentication-Results #{i + 1}: {x}" for i, x in enumerate(a["authres"])] or ["- Authentication-Results: none"]
    L += ["- Received chain, newest first (the bottom line is the first hop you can partly trust; the rest was written by others):"]
    L += [f"  {i + 1}. {r}" for i, r in enumerate(a["received"])]
    L += ["", "## 2. Links (never open them; read them)"]
    L += [f"- {u}" + (f"   (text shown: {t})" if t else "") for u, t in a["links"]] or ["- none"]
    L += ["", "## 3. Attachments (name, type, bytes, sha256)"]
    L += [f"- {n}, {t}, {s}, {h}" for n, t, s, h in a["attachments"]] or ["- none"]
    L += ["", "## 4. Hints from this script (a human decides)"] + ([f"- {f}" for f in a["flags"]] or ["- none"])
    L += ["", "## 5. Your decisions", "- Verdict (phish / spam / legitimate / unsure):", "- Who else received it (search by sender, subject, link host):",
          "- Did anyone click or open it? (check sign-in logs for those users):", "- Block (sender, domain, link host):",
          "- Remove from mailboxes (hunt, then purge):", "- Reset credentials or revoke sessions or app grants for anyone who clicked:",
          "- Report to the provider and to the impersonated brand:", "- Lesson for the awareness note:"]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--protect", action="append", default=["example.test"])
    args = ap.parse_args(argv)
    print(worksheet(args.file, analyze(args.file, args.protect)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
