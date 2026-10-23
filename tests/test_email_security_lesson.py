# SPDX-License-Identifier: Apache-2.0
"""Checks for the email security lesson and labs/email-security.

The local lab is pure Python plus the `openssl` command, so the page's claims about it are tested
directly: the evaluator's results on the synthetic messages, the SPF limit, a broken DKIM body,
the DMARC report parser and its refusal of DOCTYPE, the triage hints, the position toy. The
OpenTofu pieces are checked for flag-off defaults, and validated when `tofu` exists and can
download its provider (skipped otherwise). Nothing here touches the network except that download.
"""

import asyncio
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "labs" / "email-security"
LOCAL = LAB / "local"
PAGE = ROOT / "docs" / "wiki" / "Email-Security-DNS-Gateways-and-API-Driven-Protection.md"

needs_openssl = pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl is needed to build the lab keys")


@pytest.fixture(scope="module")
def mods():
    sys.path.insert(0, str(LOCAL))
    try:
        yield {n: importlib.import_module(n) for n in ("dkimlite", "mailauth", "mkmail", "triage", "dmarc_report", "positions")}
    finally:
        sys.path.remove(str(LOCAL))


@pytest.fixture(scope="module")
def built(tmp_path_factory, mods):
    if shutil.which("openssl") is None:
        pytest.skip("openssl is needed")
    out = tmp_path_factory.mktemp("emaillab")
    out.chmod(0o700)
    assert mods["mkmail"].main(str(out)) == 0
    return out


def results(built, mods):
    res = mods["mailauth"].FileResolver(built / "zone.json")
    got = {}
    for m in json.loads((built / "manifest.json").read_text()):
        got[Path(m["file"]).stem] = mods["mailauth"].evaluate(res, (built / m["file"]).read_bytes(), m["client_ip"], m["mail_from"])
    return got


@needs_openssl
def test_dmarc_outcomes_match_the_page(built, mods):
    r = results(built, mods)
    assert (r["01-legit-internal-signed"]["dmarc"], r["01-legit-internal-signed"]["disposition"]) == ("pass", "deliver")
    # a hired mailer passes SPF and DKIM for ITS domain and still fails DMARC for ours
    u = r["02-newsletter-bulk-unaligned"]
    assert (u["spf"], u["dkim"][0]["result"], u["dmarc"], u["disposition"]) == ("pass", "pass", "fail", "quarantine")
    a = r["03-newsletter-bulk-aligned"]
    assert (a["dmarc"], a["spf_aligned"], a["dkim_aligned"]) == ("pass", False, True)
    f = r["04-forged-ceo"]
    assert (f["spf"], f["dmarc"], f["disposition"]) == ("fail", "fail", "quarantine")
    # a look-alike authenticates as itself
    assert r["05-lookalike-domain"]["dmarc"] == "pass"
    assert r["06-display-name-trick"]["dmarc"] == "none"
    # forwarding: SPF has nothing, DKIM carries it
    fw = r["07-forwarded-by-list"]
    assert (fw["dmarc"], fw["dkim_aligned"]) == ("pass", True)
    assert r["08-list-rewrote-body"]["dkim"][0]["reason"].startswith("body hash mismatch")
    assert r["09-spf-too-many-lookups"]["spf"] == "permerror"
    assert r["10-spf-two-records"]["spf"] == "permerror"
    # the subdomain policy is stricter than the domain's
    assert r["11-subdomain-spoof"]["disposition"] == "reject"


@needs_openssl
def test_spf_limit_is_exactly_ten(built, mods):
    res = mods["mailauth"].FileResolver(built / "zone.json")
    result, st = mods["mailauth"].spf(res, "203.0.113.201", "toomany.test")
    assert result == "permerror" and st.lookups == 11
    result, st = mods["mailauth"].spf(res, "203.0.113.200", "toomany.test")
    assert result == "pass" and st.lookups == 1  # matched by the first include, before the budget runs out


@needs_openssl
def test_dkim_detects_tampering_and_a_revoked_key(built, mods):
    ma, dk = mods["mailauth"], mods["dkimlite"]
    res = ma.FileResolver(built / "zone.json")
    raw = (built / "msgs" / "01-legit-internal-signed.eml").read_bytes()

    def lookup(name):
        _, vals = res.query(name, "TXT")
        return vals[0] if vals else None

    assert dk.verify(raw, lookup)[0]["result"] == "pass"
    assert dk.verify(raw.replace(b"Are we still on", b"Are we NOT on"), lookup)[0]["result"] == "fail"
    assert dk.verify(raw.replace(b"Subject: Lunch on Friday", b"Subject: Lunch on Saturday"), lookup)[0]["result"] == "fail"
    assert "revoked" in dk.verify(raw, lambda name: "v=DKIM1; k=rsa; p=")[0]["reason"]
    assert dk.verify(raw, lambda name: None)[0]["result"] == "neutral"


@needs_openssl
def test_udp_resolver_parses_a_real_dns_packet(mods):
    """The wire parser is exercised against a packet built by hand, with name compression."""
    ma = mods["mailauth"]
    name = b"\x04_spf\x04test\x00"
    txt = b"v=spf1 -all"
    pkt = (b"\x00\x01\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00" + name + b"\x00\x10\x00\x01"
           + b"\xc0\x0c\x00\x10\x00\x01\x00\x00\x00\x1e" + (len(txt) + 1).to_bytes(2, "big") + bytes([len(txt)]) + txt)

    class Sock:
        def __init__(self, *a):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def settimeout(self, t):
            pass

        def sendto(self, data, addr):
            assert addr == ("127.0.0.1", 5300)

        def recvfrom(self, n):
            return pkt, ("127.0.0.1", 5300)

    real = ma.socket.socket
    ma.socket.socket = Sock
    try:
        assert ma.UdpResolver("127.0.0.1:5300").query("_spf.test", "TXT") == ("NOERROR", ["v=spf1 -all"])
    finally:
        ma.socket.socket = real


@needs_openssl
def test_dkim_signature_must_cover_from(built, mods):
    """Hostile fixture: sign only an unrelated header under the victim's own key. A verifier that
    accepts it would let any forged visible From pass DMARC through the DKIM side."""
    ma, dk = mods["mailauth"], mods["dkimlite"]
    res = ma.FileResolver(built / "zone.json")
    forged = (b"From: CEO <ceo@example.test>\r\nTo: bob@receiver.test\r\nSubject: Pay now\r\n"
              b"Date: Thu, 22 Oct 2026 14:00:00 +0000\r\nMessage-ID: <x@lab.test>\r\n\r\nWire it today.\r\n")
    signed = (dk.sign(forged, "example.test", "s2026a", built / "keys" / "org.pem", names=["subject"]) + "\r\n").encode() + forged
    r = ma.evaluate(res, signed, "203.0.113.66", "ceo@example.test")
    assert r["dkim"][0]["result"] == "fail" and "From is not in h=" in r["dkim"][0]["reason"]
    assert r["dmarc"] == "fail" and not r["dkim_aligned"]


def test_smtpsink_cap_counts_the_current_line(tmp_path, mods):
    sink = importlib.import_module("smtpsink")

    async def talk(lines):
        out = tmp_path / "got.eml"
        done = asyncio.Event()
        server = await asyncio.start_server(lambda r, w: sink.handle(r, w, str(out), done), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        await reader.readline()
        for line in lines:
            writer.write(line)
        await writer.drain()
        replies = []
        try:
            while True:
                got = await asyncio.wait_for(reader.readline(), timeout=3)
                if not got:
                    break
                replies.append(got.decode())
        except TimeoutError:
            pass
        writer.close()
        server.close()
        return replies, out

    head = [b"EHLO a.test\r\n", b"MAIL FROM:<a@a.test>\r\n", b"RCPT TO:<b@b.test>\r\n", b"DATA\r\n"]
    # one single oversized line must be refused, and nothing written
    replies, out = asyncio.run(talk(head + [b"x" * (sink.MAX_BYTES + 10) + b"\r\n", b".\r\n"]))
    assert any(r.startswith("552") for r in replies) and not out.exists()
    # many small lines whose last one crosses the cap must be refused too
    line = b"y" * 998 + b"\r\n"
    n = sink.MAX_BYTES // 1000 + 2
    replies, out = asyncio.run(talk(head + [line] * n + [b".\r\n"]))
    assert any(r.startswith("552") for r in replies) and not out.exists()
    # a small message still goes through
    replies, out = asyncio.run(talk(head + [b"Subject: hi\r\n", b"\r\n", b"ok\r\n", b".\r\n"]))
    assert any(r.startswith("250 2.0.0") for r in replies) and out.exists()


def test_triage_reads_single_quoted_and_unquoted_hrefs(tmp_path, mods):
    tr = mods["triage"]
    for href in ("'https://evil.invalid/login'", "https://evil.invalid/login", '"https://evil.invalid/login"'):
        eml = tmp_path / "q.eml"
        eml.write_bytes(b"From: A <a@random-host.test>\r\nTo: b@receiver.test\r\nSubject: s\r\nMIME-Version: 1.0\r\n"
                         b"Content-Type: text/html; charset=utf-8\r\n\r\n<p>Go to <a class=x href=" + href.encode()
                         + b">https://example.com/account</a></p>\r\n")
        a = tr.analyze(eml, ["example.test"])
        assert ("https://evil.invalid/login", "https://example.com/account") in a["links"], href
        assert any("shows example.com but goes to evil.invalid" in f for f in a["flags"]), href


@needs_openssl
def test_added_from_header_breaks_the_signature_and_dmarc(built, mods):
    """Parser differential: a second From added above the signed one. DKIM picks the bottom-most
    instance, a mail client may show the top one; the verifier and DMARC must not disagree."""
    ma, dk = mods["mailauth"], mods["dkimlite"]
    res = ma.FileResolver(built / "zone.json")

    def lookup(name):
        _, vals = res.query(name, "TXT")
        return vals[0] if vals else None

    original = (built / "msgs" / "01-legit-internal-signed.eml").read_bytes()
    body = original.split(b"DKIM-Signature:", 1)[1]
    signed = b"DKIM-Signature:" + body  # drop the receiver's stamp lines above the signature
    assert dk.verify(signed, lookup)[0]["result"] == "pass"
    attacked = b"From: CEO <ceo@example.test>\r\n" + signed
    r = ma.evaluate(res, attacked, "203.0.113.66", "ceo@example.test")
    assert r["dkim"][0]["result"] == "fail" and "more From headers" in r["dkim"][0]["reason"]
    assert r["from_headers"] == 2 and r["dmarc"] == "fail" and not r["dkim_aligned"] and not r["spf_aligned"]
    # over-signing: h=from:from verifies with exactly one From, and refuses a From added on top
    plain = (b"From: Alice <alice@example.test>\r\nTo: bob@receiver.test\r\nSubject: Hi\r\n"
             b"Date: Thu, 22 Oct 2026 14:00:00 +0000\r\nMessage-ID: <o@lab.test>\r\n\r\nHello.\r\n")
    key = built / "keys" / "org.pem"
    over = (dk.sign(plain, "example.test", "s2026a", key, names=["from", "from", "subject", "date"]) + "\r\n").encode() + plain
    assert "h=from:from:subject:date" in over.decode()
    assert dk.verify(over, lookup)[0]["result"] == "pass"
    assert ma.evaluate(res, over, "192.0.2.25", "alice@example.test")["dmarc"] == "pass"
    assert dk.verify(b"From: CEO <ceo@example.test>\r\n" + over, lookup)[0]["result"] == "fail"
    # a message that really carries two From headers is never a DMARC pass, even if both are signed
    twice = b"From: Alice <alice@example.test>\r\n" + plain
    both = (dk.sign(twice, "example.test", "s2026a", key, names=["from", "from", "subject"]) + "\r\n").encode() + twice
    r2 = ma.evaluate(res, both, "192.0.2.25", "alice@example.test")
    assert r2["dkim"][0]["result"] == "pass" and r2["dmarc"] == "fail" and r2["from_headers"] == 2


def _eml(html):
    return (b"From: A <a@random-host.test>\r\nTo: b@receiver.test\r\nSubject: s\r\nMIME-Version: 1.0\r\n"
            b"Content-Type: text/html; charset=utf-8\r\n\r\n" + html.encode() + b"\r\n")


def test_triage_link_list_cannot_lose_a_link(tmp_path, mods):
    tr = mods["triage"]

    def run(html):
        eml = tmp_path / "t.eml"
        eml.write_bytes(_eml(html))
        a = tr.analyze(eml, ["example.test"])
        return {u for u, _ in a["links"]}, a["flags"]

    # duplicate href attributes: browsers use the first; the message is flagged
    links, flags = run('<a href="https://first.invalid/" href="https://second.invalid/">https://example.com/</a>')
    assert ("https://first.invalid/" in links) and any("more than one href" in f and "first.invalid" in f for f in flags)
    assert "https://second.invalid/" in links  # not listed by the parser, so the raw scan reports it
    assert any("raw scan" in f and "second.invalid" in f for f in flags)
    # nested anchors: the open one is saved when the next starts
    links, _ = run('<a href="https://one.invalid/">one<a href="https://two.invalid/">two</a>')
    assert {"https://one.invalid/", "https://two.invalid/"} <= links
    # an anchor still open at the end of the document
    links, _ = run('<p>x</p><a href="https://open.invalid/">click')
    assert "https://open.invalid/" in links
    # uppercase tag and attribute
    links, _ = run('<A HREF="https://UPPER.invalid/path">go</A>')
    assert "https://UPPER.invalid/path" in links
    # a link only the raw scan can reach (not an anchor), and an entity-escaped one
    links, flags = run('<map><area href="https://hidden.invalid/x"></map><link href=https://bare.invalid/y>')
    assert {"https://hidden.invalid/x", "https://bare.invalid/y"} <= links
    assert any("hidden.invalid" in f and "raw scan" in f for f in flags)
    links, _ = run('<a href="https://amp.invalid/?a=1&amp;b=2">x</a>')
    assert "https://amp.invalid/?a=1&b=2" in links


@needs_openssl
def test_bare_cr_and_multi_address_from_cannot_hide_the_author(built, mods):
    """Parser differential: a lone CR can be a line break to one parser and nothing to another."""
    ma, dk = mods["mailauth"], mods["dkimlite"]
    res = ma.FileResolver(built / "zone.json")
    tail = b"To: bob@receiver.test\r\nSubject: Pay\r\nDate: Thu, 22 Oct 2026 14:00:00 +0000\r\n\r\nWire it.\r\n"
    # a second From hidden behind a bare CR inside another header's value
    hidden = b"X-Note: hello\rFrom: CEO <ceo@example.test>\r\nFrom: Eve <eve@random-host.test>\r\n" + tail
    headers, _ = dk.split_message(hidden)
    assert [n.lower() for n, _ in headers].count("from") == 2  # the strict reading sees both
    r = ma.evaluate(res, hidden, "203.0.113.60", "eve@random-host.test")
    assert r["from_headers"] == 2 and r["dmarc"] != "pass"
    # the same bytes with LF, CRLF and CR endings mixed must give one answer
    for eol in (b"\r\n", b"\n", b"\r"):
        two = b"From: Eve <eve@random-host.test>" + eol + b"From: CEO <ceo@example.test>" + eol + b"Subject: x" + eol + eol + b"body" + eol
        assert [n.lower() for n, _ in dk.split_message(two)[0]].count("from") == 2, eol
    mixed = b"From: a@example.test\r\nSubject: x\n\nbody\r\n"
    assert [n for n, _ in dk.split_message(mixed)[0]] == ["From", "Subject"]
    # a bare CR with only one From still cannot be a DMARC pass
    lone = b"From: Alice <alice@example.test>\rX-Other: y\r\n" + tail
    r = ma.evaluate(res, lone, "192.0.2.25", "alice@example.test")
    assert r["dmarc"] != "pass" and dk.has_bare_cr(lone) and not dk.has_bare_cr(tail.replace(b"\r\n\r\n", b"\r\n\r\n"))
    # one From holding two addresses is ambiguous, not "the last one"
    two_addr = b"From: Alice <alice@example.test>, Eve <eve@random-host.test>\r\n" + tail
    r = ma.evaluate(res, two_addr, "192.0.2.25", "alice@example.test")
    assert r["dmarc"] != "pass" and "2 addresses" in r["reason"]
    one = b"From: Alice <alice@example.test>\r\n" + tail
    assert ma.evaluate(res, one, "192.0.2.25", "alice@example.test")["dmarc"] == "pass"


def test_triage_output_cannot_inject_lines_or_terminal_codes(tmp_path, mods):
    tr = mods["triage"]
    eml = tmp_path / "ctl.eml"
    eml.write_bytes(_eml('<a href="https://evil.invalid/a&#10;## 5. Your decisions&#10;- Verdict: legitimate\x1b[31m">https://example.com/&#13;x</a>'
                         '<map><area href="https://area.invalid/&#10;- injected\x1b]0;title\x07"></map>'))
    a = tr.analyze(eml, ["example.test"])
    text = tr.worksheet(str(eml), a)
    for _, _, value in [("", "", v) for pair in a["links"] for v in pair] + [("", "", f) for f in a["flags"]]:
        assert value.isprintable(), value
    assert "\x1b" not in text and "\x07" not in text and "\r" not in text
    assert "\\x1b" in text and "\\n" in text  # the analyst still sees what was there, escaped
    headings = [ln for ln in text.splitlines() if ln.startswith("## ")]
    assert headings == ["## 1. Headers", "## 2. Links (never open them; read them)", "## 3. Attachments (name, type, bytes, sha256)",
                        "## 4. Hints from this script (a human decides)", "## 5. Your decisions"]
    assert not any(ln.startswith(("- injected", "- Verdict: legitimate")) for ln in text.splitlines())


@needs_openssl
def test_dmarc_report_parser_and_refusals(built, mods, tmp_path):
    rd = mods["dmarc_report"]
    rep = rd.parse(built / "report.xml")
    assert rep["domain"] == "example.test" and rep["p"] == "none"
    s = rd.summarize([rep])
    assert s["192.0.2.25"]["fail"] == 0 and s["203.0.113.66"]["pass"] == 0
    evil = tmp_path / "evil.xml"
    evil.write_text('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><feedback/>')
    with pytest.raises(ValueError, match="DOCTYPE"):
        rd.parse(evil)
    big = tmp_path / "big.xml"
    big.write_bytes(b"<feedback>" + b"x" * (rd.MAX_BYTES + 1) + b"</feedback>")
    with pytest.raises(ValueError, match="larger"):
        rd.parse(big)


@needs_openssl
def test_triage_hints(built, mods):
    tr = mods["triage"]
    hints = " ".join(tr.analyze(built / "msgs" / "05-lookalike-domain.eml", ["example.test"])["flags"])
    assert "looks like the protected domain" in hints and "link text shows example.com but goes to payroll-update.invalid" in hints
    assert "Reply-To" in hints
    assert "display name contains a different address" in " ".join(tr.analyze(built / "msgs" / "06-display-name-trick.eml", ["example.test"])["flags"])
    a = tr.analyze(built / "msgs" / "13-double-extension-attachment.eml", ["example.test"])
    assert a["attachments"][0][0] == "remittance.pdf.html" and any("double extension" in f for f in a["flags"])
    assert any("image" in f for f in tr.analyze(built / "msgs" / "12-qr-image-only.eml", ["example.test"])["flags"])
    forged = tr.analyze(built / "msgs" / "04-forged-ceo.eml", ["example.test"])
    assert len(forged["authres"]) == 2 and forged["authres"][0].startswith("mx.receiver.test")
    ws = tr.worksheet("x", forged)
    assert "## 5. Your decisions" in ws and "Verdict" in ws


def test_positions_toy(mods, capsys):
    pos = mods["positions"]
    assert pos.main(["--lockdown", "yes"]) == 0
    out = capsys.readouterr().out
    gate = re.search(r"gateway\s+stopped=(\d+) late=(\d+) missed=(\d+)", out)
    assert gate and int(gate.group(3)) >= 3  # internal mail, chat and a later verdict are outside its view
    pos.main(["--lockdown", "no"])
    assert "MISSED" in next(ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("M4 "))
    # a locked-down tenant refuses the direct-send message for every position
    pos.main(["--lockdown", "yes"])
    m4 = next(ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("M4 "))
    assert "MISSED" not in m4


def test_no_secret_shaped_literals_in_the_lab():
    for f in LAB.rglob("*"):
        if f.is_file() and f.suffix in {".py", ".tf", ".md", ".json"}:
            text = f.read_text()
            assert "PRIVATE KEY" not in text, f
            assert not re.search(r"[A-Za-z0-9+/]{100,}={0,2}", text), f"{f}: a long base64-looking run"


def test_cloud_pieces_default_to_off():
    for tf in list((LAB / "cloud").rglob("*.tf")) + list((LAB / "compose").rglob("*.tf")):
        text = tf.read_text()
        for m in re.finditer(r'variable "(enabled|enable_\w+)" \{(.*?)\n\}', text, re.DOTALL):
            assert re.search(r"default\s*=\s*false", m.group(2)), f"{tf}: {m.group(1)} must default to false"
        assert not re.search(r'variable "\w*token\w*"', text), f"{tf}: a token must come from the environment, not a variable"
    comp = (LAB / "compose" / "main.tf").read_text()
    assert comp.count("default = false") >= 5


def test_pieces_json_matches_the_price_table():
    pieces = json.loads((LAB / "pieces.json").read_text())["pieces"]
    prices = json.loads((ROOT / "docs" / "cost-prices.json").read_text())
    droplet = next(p for p in pieces if p["name"] == "droplet")
    assert droplet["monthly_usd"] == prices["droplets"][droplet["size"]]
    assert "$6 at list price" in PAGE.read_text() or "$6 a month" in PAGE.read_text()
    for p in pieces:  # the destroy order is the reverse of the dependencies
        for dep in p["depends_on"]:
            other = next(q for q in pieces if q["name"] == dep)
            assert other["build"] <= p["build"] and other["destroy"] >= p["destroy"]


@pytest.mark.skipif(shutil.which("tofu") is None, reason="tofu is not installed")
def test_tofu_validate(tmp_path):
    env = dict(os.environ, TF_PLUGIN_CACHE_DIR=str(tmp_path / "plugins"), TF_IN_AUTOMATION="1")
    (tmp_path / "plugins").mkdir()
    tree = tmp_path / "lab"
    shutil.copytree(LAB, tree, ignore=shutil.ignore_patterns(".terraform*", "local"))
    for d in sorted((tree / "cloud").iterdir()) + [tree / "compose"]:
        init = subprocess.run(["tofu", "init", "-backend=false", "-input=false"], cwd=d, env=env, capture_output=True, text=True, check=False)
        if init.returncode != 0:
            pytest.skip("tofu could not download its provider (no network)")
        val = subprocess.run(["tofu", "validate"], cwd=d, env=env, capture_output=True, text=True, check=False)
        assert val.returncode == 0, f"{d.name}: {val.stdout}{val.stderr}"
        fmt = subprocess.run(["tofu", "fmt", "-check"], cwd=d, env=env, capture_output=True, text=True, check=False)
        assert fmt.returncode == 0, f"{d.name}: tofu fmt would change {fmt.stdout}"


def test_page_disclosure_and_links():
    text = PAGE.read_text()
    assert "—" not in text
    assert text.count("https://links.chiefgyk3d.com/productrecs") >= 1
    low = text.lower()
    assert "affiliate relationships with **both** proton and tuta" in low
    assert "not an affiliate" not in low and "no affiliation" not in low
    for bad in ("referral", "?ref=", "aff=", "affiliate="):
        assert bad not in low.replace("affiliate relationships", ""), bad
    why = (ROOT / "docs" / "wiki" / "Why-I-Picked-These-Tools.md").read_text()
    assert "affiliate relationships with Proton and with Tuta" in why
    # every repository path the page names exists
    for rel in re.findall(r"labs/email-security(?:/[\w./-]+)?", text):
        rel = rel.rstrip(".")
        assert (ROOT / rel).exists(), rel
    for needed in ("Cost box. Read this before you create anything.", "Teardown first.", "Flip the board", "## Threat model", "## Claims register"):
        assert needed in text
    # no real-looking address other than reserved documentation ranges
    for ip in re.findall(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", text):
        assert ip.startswith(("192.0.2.", "198.51.100.", "203.0.113.", "127.0.0.")) or ip == "0.0.0.0", ip


def _tofu_env(tmp_path):
    env = dict(os.environ, TF_PLUGIN_CACHE_DIR=str(tmp_path / "plugins"), TF_IN_AUTOMATION="1", DIGITALOCEAN_TOKEN="lab-placeholder")
    (tmp_path / "plugins").mkdir(exist_ok=True)
    tree = tmp_path / "lab"
    if not tree.exists():
        shutil.copytree(LAB, tree, ignore=shutil.ignore_patterns(".terraform*", "local"))
    return env, tree


def test_compose_orders_droplet_after_firewall_and_gates_assignment_on_a_known_flag():
    comp = (LAB / "compose" / "main.tf").read_text()
    droplet_block = re.search(r'module "droplet" \{(.*?)\n\}', comp, re.DOTALL).group(1)
    assert "depends_on = [module.firewall]" in droplet_block
    assert "assign     = var.enable_droplet" in comp
    reserved = (LAB / "cloud" / "reserved-ip" / "main.tf").read_text()
    assert re.search(r"count\s*=\s*var\.enabled && var\.assign", reserved)
    assert "var.droplet_id !=" not in reserved  # an unknown value cannot decide a count at plan time


@pytest.mark.skipif(shutil.which("tofu") is None, reason="tofu is not installed")
def test_tofu_all_flags_on_plans_five_resources_and_firewall_rejects_ipv6(tmp_path):
    env, tree = _tofu_env(tmp_path)
    comp = tree / "compose"
    init = subprocess.run(["tofu", "init", "-backend=false", "-input=false"], cwd=comp, env=env, capture_output=True, text=True, check=False)
    if init.returncode != 0:
        pytest.skip("tofu could not download its provider (no network)")
    base = ["tofu", "plan", "-input=false", "-lock=false", "-refresh=false", "-no-color"]
    flags = ["enable_project", "enable_firewall", "enable_droplet", "enable_reserved_ip", "enable_dns"]
    args = [a for f in flags for a in ("-var", f"{f}=true")] + ["-var", 'ssh_key_fingerprints=["aa:bb"]']
    on = subprocess.run(base + args, cwd=comp, env=env, capture_output=True, text=True, check=False)
    assert on.returncode == 0, on.stdout + on.stderr
    created = re.findall(r"# (module\.\S+) will be created", on.stdout)
    assert len(created) == 7, created  # project, firewall, droplet, reserved IP and its assignment, domain, record
    assert any("reserved_ip_assignment" in c for c in created)
    off = subprocess.run(base, cwd=comp, env=env, capture_output=True, text=True, check=False)
    assert off.returncode == 0 and "will be created" not in off.stdout
    for bad in ("2001:db8::/32", "192.0.2.0/24", "0.0.0.0/0", "192.0.2.10/31"):
        r = subprocess.run(base + ["-var", f"admin_cidr={bad}"], cwd=comp, env=env, capture_output=True, text=True, check=False)
        assert r.returncode != 0 and "single IPv4 address" in (r.stdout + r.stderr).replace("\n", " ").replace("│", ""), bad
    ok = subprocess.run(base + ["-var", "admin_cidr=198.51.100.7/32"], cwd=comp, env=env, capture_output=True, text=True, check=False)
    assert ok.returncode == 0
