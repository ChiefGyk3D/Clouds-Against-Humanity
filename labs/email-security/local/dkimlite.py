#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""dkimlite.py: a teaching DKIM signer and verifier (RFC 6376, rsa-sha256, relaxed/relaxed only).

It exists so you can read every step. It uses the `openssl` command for the RSA math and nothing
else outside the standard library. It is not a production verifier: it refuses what it does not
implement (the l= tag, other algorithms, other canonicalizations) instead of guessing.
"""
import base64
import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

SIGN_HEADERS = ["from", "to", "subject", "date", "message-id", "mime-version"]


def split_message(raw: bytes):
    """Return (headers, body). Each header is (name, raw_text_with_folds, no trailing CRLF)."""
    raw = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    head, _, body = raw.partition(b"\r\n\r\n")
    headers = []
    for line in head.split(b"\r\n"):
        if line[:1] in (b" ", b"\t") and headers:
            headers[-1][1] += b"\r\n" + line
        else:
            headers.append([line.partition(b":")[0].decode("ascii", "replace").strip(), line])
    return [(n, r) for n, r in headers], body


def canon_header(raw: bytes) -> bytes:
    """Relaxed header canonicalization (RFC 6376 section 3.4.2): lowercase name, unfold, squeeze spaces."""
    name, _, value = raw.decode("utf-8", "replace").partition(":")
    value = re.sub(r"\r\n(?=[ \t])", "", value)
    value = re.sub(r"[ \t]+", " ", value).strip(" \t")
    return (name.strip().lower() + ":" + value + "\r\n").encode()


def canon_body(body: bytes) -> bytes:
    """Relaxed body canonicalization (section 3.4.4): squeeze spaces, trim line ends and trailing blank lines."""
    lines = [re.sub(rb"[ \t]+", b" ", line).rstrip(b" ") for line in body.split(b"\r\n")]
    while lines and lines[-1] == b"":
        lines.pop()
    return (b"\r\n".join(lines) + b"\r\n") if lines else b""


def _pick(headers, names):
    """For each name in h=, take the bottom-most unused header of that name (section 5.4.2)."""
    used, out = set(), []
    for want in names:
        for i in range(len(headers) - 1, -1, -1):
            if i not in used and headers[i][0].lower() == want:
                used.add(i)
                out.append(headers[i][1])
                break
    return out


def _openssl(args, data: bytes, sig=None, pub=None, key=None):
    with tempfile.TemporaryDirectory() as td:  # a private random folder, removed afterwards
        d = Path(td)
        (d / "data").write_bytes(data)
        if key:
            subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(key), "-out", str(d / "sig"), str(d / "data")], check=True)
            return (d / "sig").read_bytes()
        (d / "sig").write_bytes(sig)
        (d / "pub.der").write_bytes(pub)
        subprocess.run(["openssl", "pkey", "-pubin", "-inform", "DER", "-in", str(d / "pub.der"), "-out", str(d / "pub.pem")],
                       check=True, capture_output=True)
        r = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(d / "pub.pem"), "-signature", str(d / "sig"), str(d / "data")],
                           capture_output=True)
        return r.returncode == 0


def sign(raw: bytes, domain: str, selector: str, key_path, names=None) -> str:
    """Return a DKIM-Signature header (text, CRLF folded) for the message."""
    headers, body = split_message(raw)
    names = [n for n in (names or SIGN_HEADERS) if any(h[0].lower() == n for h in headers)]
    bh = base64.b64encode(hashlib.sha256(canon_body(body)).digest()).decode()
    unsigned = (f"DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d={domain}; s={selector}; "
                f"h={':'.join(names)}; bh={bh}; b=").encode()
    data = b"".join(canon_header(h) for h in _pick(headers, names)) + canon_header(unsigned).rstrip(b"\r\n")
    b64 = base64.b64encode(_openssl(None, data, key=key_path)).decode()
    folded = "\r\n\t".join(b64[i:i + 64] for i in range(0, len(b64), 64))
    return unsigned.decode() + folded


def _tags(text):
    out = {}
    for part in text.split(";"):
        k, _, v = part.partition("=")
        if k.strip():
            out[k.strip()] = re.sub(r"\s+", "", v) if k.strip() in ("b", "bh", "p") else v.strip()
    return out


def verify(raw: bytes, lookup_txt):
    """Check every DKIM-Signature. lookup_txt(name) returns the TXT string or None.
    Returns a list of {d, s, result, reason}; result is pass, fail or neutral."""
    headers, body = split_message(raw)
    results = []
    for _, hraw in [h for h in headers if h[0].lower() == "dkim-signature"]:
        text = re.sub(r"\r\n(?=[ \t])", "", hraw.decode("utf-8", "replace").partition(":")[2])
        t = _tags(text)
        res = {"d": t.get("d", "?"), "s": t.get("s", "?"), "result": "fail", "reason": ""}
        results.append(res)
        if any(k not in t for k in ("v", "a", "b", "bh", "d", "h", "s")):
            res["reason"] = "missing a required tag"
        elif t["a"] != "rsa-sha256" or t.get("c", "simple/simple") != "relaxed/relaxed":
            res.update(result="neutral", reason="this teaching verifier only does rsa-sha256 with relaxed/relaxed")
        elif "l" in t:
            res.update(result="neutral", reason="l= (body length limit) is refused: it lets an attacker append text")
        elif base64.b64encode(hashlib.sha256(canon_body(body)).digest()).decode() != t["bh"]:
            res["reason"] = "body hash mismatch (the body changed after signing)"
        else:
            rec = lookup_txt(f"{t['s']}._domainkey.{t['d']}")
            if rec is None:
                res.update(result="neutral", reason="no key record at that selector")
                continue
            kt = _tags(rec)
            if not kt.get("p"):
                res["reason"] = "key revoked (empty p=)"
                continue
            names = [n.strip().lower() for n in t["h"].split(":")]
            stripped = re.sub(r"(?<=[;\s:])b=[^;]*", "b=", hraw.decode("utf-8", "replace"), count=1).encode()
            data = b"".join(canon_header(h) for h in _pick(headers, names)) + canon_header(stripped).rstrip(b"\r\n")
            try:
                ok = _openssl(None, data, sig=base64.b64decode(t["b"]), pub=base64.b64decode(kt["p"]))
            except Exception as exc:  # a malformed key or signature is a fail, not a crash
                ok, res["reason"] = False, f"unusable key or signature ({type(exc).__name__})"
            if ok:
                res.update(result="pass", reason="signature verifies")
            else:
                res["reason"] = res["reason"] or "signature does not verify (a signed header changed, or the wrong key)"
    return results
