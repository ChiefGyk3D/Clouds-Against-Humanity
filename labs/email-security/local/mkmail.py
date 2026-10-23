#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""mkmail.py OUTDIR: build the whole email-security lab fixture at run time. Nothing here is committed.

Writes into OUTDIR (create it private first: mkdir -m 700):
  keys/*.pem            two throwaway RSA keys made by `openssl genrsa` (never reuse them anywhere)
  zone.json, auth.conf  the fake DNS zone, as data for mailauth.py and as a dnsmasq config
  msgs/*.eml            synthetic messages built with Python's email package
  manifest.json         the envelope facts (connecting IP, MAIL FROM) for each message
  report.xml            a synthetic DMARC aggregate report (RFC 9990 shape)

Every name is a reserved example name (.test, .invalid, example.com) and every address is RFC 5737.
No message contains a working link or real malware; the "attachments" are harmless text.
"""
import base64
import json
import struct
import subprocess
import sys
import zlib
from email import policy
from email.message import EmailMessage
from pathlib import Path
from xml.etree import ElementTree as ET

import dkimlite
import mailauth

DATE = "Thu, 22 Oct 2026 14:00:00 +0000"
RECEIVER = "mx.receiver.test"


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True)


def make_key(path):
    run(["openssl", "genrsa", "-out", str(path), "2048"])
    der = run(["openssl", "pkey", "-in", str(path), "-pubout", "-outform", "DER"]).stdout
    return base64.b64encode(der).decode()


def chunks(s, n=200):
    return [s[i:i + n] for i in range(0, len(s), n)]


def build_zone(pub_org, pub_bulk):
    z = {}

    def put(name, rtype, val):
        z.setdefault(name, {}).setdefault(rtype, []).append(val)

    # example.test: the organization that is learning to defend its domain
    put("example.test", "A", "192.0.2.11")
    put("example.test", "MX", [10, "mail.example.test"])
    put("mail.example.test", "A", "192.0.2.25")
    put("example.test", "TXT", ["v=spf1 ip4:192.0.2.25 include:_spf.bulkmailer.test -all"])
    put("_dmarc.example.test", "TXT", ["v=DMARC1; p=quarantine; sp=reject; rua=mailto:dmarc-reports@example.test; adkim=r; aspf=r"])
    put("s2026a._domainkey.example.test", "TXT", chunks(f"v=DKIM1; k=rsa; p={pub_org}"))
    put("bulk1._domainkey.example.test", "TXT", chunks(f"v=DKIM1; k=rsa; p={pub_bulk}"))
    # the bulk mailer the organization hired (a different domain on purpose)
    put("_spf.bulkmailer.test", "TXT", ["v=spf1 ip4:198.51.100.0/24 -all"])
    put("bulkmailer.test", "TXT", ["v=spf1 ip4:198.51.100.0/24 -all"])
    put("bm1._domainkey.bulkmailer.test", "TXT", chunks(f"v=DKIM1; k=rsa; p={pub_bulk}"))
    # a partner that forwards through a mailing list, and a look-alike registered by an attacker
    put("partner.test", "TXT", ["v=spf1 ip4:198.51.100.0/24 -all"])
    put("_dmarc.partner.test", "TXT", ["v=DMARC1; p=reject; rua=mailto:reports@partner.test"])
    put("pt1._domainkey.partner.test", "TXT", chunks(f"v=DKIM1; k=rsa; p={pub_org}"))
    put("examp1e.test", "TXT", ["v=spf1 ip4:203.0.113.50 -all"])
    put("_dmarc.examp1e.test", "TXT", ["v=DMARC1; p=reject"])
    put("random-host.test", "TXT", ["v=spf1 ip4:203.0.113.60 -all"])
    # a broken SPF record: eleven DNS-querying terms (the limit is ten)
    inc = " ".join(f"include:hop{i}.toomany.test" for i in range(1, 12))
    put("toomany.test", "TXT", [f"v=spf1 {inc} -all"])
    for i in range(1, 12):
        put(f"hop{i}.toomany.test", "TXT", ["v=spf1 ip4:203.0.113.201 -all" if i == 11 else "v=spf1 ip4:203.0.113.200 -all"])
    put("_dmarc.toomany.test", "TXT", ["v=DMARC1; p=reject"])
    # another broken one: two SPF records at one name
    put("twice.test", "TXT", ["v=spf1 ip4:192.0.2.25 -all"])
    put("twice.test", "TXT", ["v=spf1 mx -all"])
    put("_dmarc.twice.test", "TXT", ["v=DMARC1; p=reject"])
    return z


def zone_to_dnsmasq(z):
    lines = ["port=5300", "listen-address=127.0.0.1", "bind-interfaces", "no-resolv", "no-hosts",
             "auth-server=ns1.example.test,127.0.0.1",
             "auth-zone=test,192.0.2.0/24,127.0.0.0/8", "auth-ttl=30",
             "auth-soa=2026102201,hostmaster.example.test,1200,120,604800", "host-record=ns1.example.test,127.0.0.1"]
    for name, recs in sorted(z.items()):
        for ip in recs.get("A", []):
            lines.append(f"host-record={name},{ip}")
        for pref, host in recs.get("MX", []):
            lines.append(f"mx-host={name},{host},{pref}")
        for ch in recs.get("TXT", []):
            lines.append("txt-record=" + name + "," + ",".join('"' + c.replace('"', '') + '"' for c in ch))
    return "\n".join(lines) + "\n"


def msg(frm, to, subject, body, msgid, extra=None, html=None):
    m = EmailMessage(policy=policy.SMTP)
    m["From"], m["To"], m["Subject"], m["Date"], m["Message-ID"] = frm, to, subject, DATE, f"<{msgid}@lab.test>"
    for k, v in (extra or {}).items():
        m[k] = v
    m.set_content(body)
    if html:
        m.add_alternative(html, subtype="html")
    return m


def png_1x1():
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff")) + chunk(b"IEND", b""))


def main(out):
    out = Path(out)
    (out / "keys").mkdir(parents=True, exist_ok=True)
    (out / "msgs").mkdir(exist_ok=True)
    pub_org = make_key(out / "keys" / "org.pem")
    pub_bulk = make_key(out / "keys" / "bulk.pem")
    zone = build_zone(pub_org, pub_bulk)
    (out / "zone.json").write_text(json.dumps(zone, indent=1))
    (out / "auth.conf").write_text(zone_to_dnsmasq(zone) + f"pid-file={out}/auth.pid\n")
    org, bulk = out / "keys" / "org.pem", out / "keys" / "bulk.pem"

    # (file, message, connecting ip, MAIL FROM, (domain, selector, key) to sign with, volume for the report)
    plan = []
    plan.append(("01-legit-internal-signed", msg('"Alice Example" <alice@example.test>', "bob@receiver.test", "Lunch on Friday",
                 "Are we still on for lunch?\n", "m01"), "192.0.2.25", "alice@example.test", ("example.test", "s2026a", org), 120))
    plan.append(("02-newsletter-bulk-unaligned", msg("Example News <news@example.test>", "bob@receiver.test", "October update",
                 "Our newsletter.\n", "m02"), "198.51.100.7", "bounce@bulkmailer.test", ("bulkmailer.test", "bm1", bulk), 40))
    plan.append(("03-newsletter-bulk-aligned", msg("Example News <news@example.test>", "bob@receiver.test", "November update",
                 "Our newsletter, signed with a key for our own domain.\n", "m03"), "198.51.100.7", "bounce@bulkmailer.test", ("example.test", "bulk1", bulk), 35))
    plan.append(("04-forged-ceo", msg("CEO <ceo@example.test>", "bob@receiver.test", "Urgent: wire needed today",
                 "Pay the attached invoice now. Reply only to me.\n", "m04",
                 {"Authentication-Results": "example.test; spf=pass smtp.mailfrom=example.test; dkim=pass; dmarc=pass"}),
                 "203.0.113.66", "ceo@example.test", None, 9))
    plan.append(("05-lookalike-domain", msg('"Example Payroll" <payroll@examp1e.test>', "bob@receiver.test", "Action needed: update direct deposit",
                 "Please confirm your details at https://example.com/payroll today.\n", "m05", {"Reply-To": "hr-help@random-host.test"},
                 html='<p>Please confirm your details at <a href="https://payroll-update.invalid/login">https://example.com/payroll</a> today.</p>'),
                 "203.0.113.50", "payroll@examp1e.test", ("examp1e.test", "x", None), 4))
    plan.append(("06-display-name-trick", msg('"alice@example.test" <billing@random-host.test>', "bob@receiver.test", "Invoice 4471 attached",
                 "See the attached invoice.\n", "m06"), "203.0.113.60", "billing@random-host.test", None, 3))
    plan.append(("07-forwarded-by-list", msg("Pat Partner <pat@partner.test>", "list@receiver.test", "Quarterly numbers",
                 "Numbers attached below.\n", "m07"), "203.0.113.25", "list-bounces@receiver.test", ("partner.test", "pt1", org), 12))
    plan.append(("08-list-rewrote-body", msg("Alice Example <alice@example.test>", "list@receiver.test", "Meeting notes",
                 "Notes from the meeting.\n", "m08"), "203.0.113.25", "list-bounces@receiver.test", ("example.test", "s2026a", org), 6))
    plan.append(("09-spf-too-many-lookups", msg("Ops <ops@toomany.test>", "bob@receiver.test", "Status", "All quiet.\n", "m09"),
                 "203.0.113.201", "ops@toomany.test", None, 2))
    plan.append(("10-spf-two-records", msg("Ops <ops@twice.test>", "bob@receiver.test", "Status", "All quiet.\n", "m10"),
                 "192.0.2.25", "ops@twice.test", None, 2))
    plan.append(("11-subdomain-spoof", msg("Billing <billing@pay.example.test>", "bob@receiver.test", "Past due", "Pay now.\n", "m11"),
                 "203.0.113.66", "billing@pay.example.test", None, 5))
    qr = msg("IT Helpdesk <it-help@random-host.test>", "bob@receiver.test", "Scan to keep your mailbox active", "(image only)\n", "m12",
             html='<p><img src="cid:qr1" alt=""></p>')
    qr.get_payload()[1].add_related(png_1x1(), "image", "png", cid="<qr1>", filename="scan-me.png")
    plan.append(("12-qr-image-only", qr, "203.0.113.60", "it-help@random-host.test", None, 3))
    att = msg("Vendor <accounts@random-host.test>", "bob@receiver.test", "Remittance advice", "Open the attachment.\n", "m13")
    att.add_attachment(b"Synthetic placeholder text. Not malicious.\n", maintype="text", subtype="html", filename="remittance.pdf.html")
    plan.append(("13-double-extension-attachment", att, "203.0.113.60", "accounts@random-host.test", None, 3))

    res = mailauth.FileResolver(out / "zone.json")
    manifest, qid = [], 0
    for name, m, ip, mail_from, signer, volume in plan:
        raw = m.as_bytes()
        if signer and signer[2]:
            raw = (dkimlite.sign(raw, signer[0], signer[1], signer[2]) + "\r\n").encode() + raw
        if name == "08-list-rewrote-body":  # the list adds a footer and a tag after the sender signed
            raw = raw.replace(b"Subject: Meeting notes", b"Subject: [team-list] Meeting notes").replace(
                b"Notes from the meeting.", b"Notes from the meeting.\r\n\r\n-- \r\nYou are on team-list@receiver.test")
        r = mailauth.evaluate(res, raw, ip, mail_from)
        qid += 1
        stamp = (f"Return-Path: <{mail_from}>\r\n"
                 f"Received: from helo.{ip.replace('.', '-')}.invalid (unknown [{ip}])\r\n\tby {RECEIVER} (Postfix) with ESMTPS id Q{qid:04d}\r\n"
                 f"\tfor <{m['To']}>; {DATE}\r\n"
                 f"Authentication-Results: {mailauth.authres(r)}\r\n")
        if name == "04-forged-ceo":  # the attacker's own fake stamp sits below the real one
            stamp += "Received: from smtp.example.test (smtp.example.test [192.0.2.25])\r\n\tby relay.invalid; " + DATE + "\r\n"
        (out / "msgs" / f"{name}.eml").write_bytes(stamp.encode() + raw)
        manifest.append({"file": f"msgs/{name}.eml", "client_ip": ip, "mail_from": mail_from, "volume": volume})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    write_report(out / "report.xml", manifest, res, out)
    return 0


def write_report(path, manifest, res, out):
    fb = ET.Element("feedback", xmlns="urn:ietf:params:xml:ns:dmarc-2.0")
    ET.SubElement(fb, "version").text = "1.0"
    md = ET.SubElement(fb, "report_metadata")
    for k, v in (("org_name", "receiver.test"), ("email", "postmaster@receiver.test"), ("report_id", "synthetic-0001")):
        ET.SubElement(md, k).text = v
    dr = ET.SubElement(md, "date_range")
    ET.SubElement(dr, "begin").text, ET.SubElement(dr, "end").text = "1792627200", "1792713599"
    pp = ET.SubElement(fb, "policy_published")
    for k, v in (("domain", "example.test"), ("p", "none"), ("sp", "none"), ("testing", "n"), ("discovery_method", "treewalk")):
        ET.SubElement(pp, k).text = v
    for m in manifest:
        r = mailauth.evaluate(res, (out / m["file"]).read_bytes(), m["client_ip"], m["mail_from"])
        if r["from_domain"] != "example.test" and not r["from_domain"].endswith(".example.test"):
            continue
        rec = ET.SubElement(fb, "record")
        row = ET.SubElement(rec, "row")
        ET.SubElement(row, "source_ip").text = m["client_ip"]
        ET.SubElement(row, "count").text = str(m["volume"])
        pe = ET.SubElement(row, "policy_evaluated")
        ET.SubElement(pe, "disposition").text = "none"
        ET.SubElement(pe, "dkim").text = "pass" if r["dkim_aligned"] else "fail"
        ET.SubElement(pe, "spf").text = "pass" if r["spf_aligned"] else "fail"
        ids = ET.SubElement(rec, "identifiers")
        ET.SubElement(ids, "envelope_from").text = r["mail_from_domain"]
        ET.SubElement(ids, "header_from").text = r["from_domain"]
        ar = ET.SubElement(rec, "auth_results")
        for d in r["dkim"]:
            e = ET.SubElement(ar, "dkim")
            ET.SubElement(e, "domain").text, ET.SubElement(e, "result").text, ET.SubElement(e, "selector").text = d["d"], d["result"], d["s"]
        e = ET.SubElement(ar, "spf")
        ET.SubElement(e, "domain").text, ET.SubElement(e, "result").text = r["mail_from_domain"], r["spf"]
    ET.ElementTree(fb).write(path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: mkmail.py OUTDIR")
    sys.exit(main(sys.argv[1]))
