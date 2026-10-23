#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""dmarc_report.py REPORT.xml [REPORT.xml ...]: summarize DMARC aggregate reports (RFC 9990 shape).

It answers the question that decides when you may raise a policy: which sources send mail as my
domain, and which of them would fail if I enforced? It refuses DOCTYPE and ENTITY declarations
(an aggregate report is mail from strangers: never let XML fetch or expand anything) and caps the size.
"""
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

MAX_BYTES = 1_000_000


def local(tag):
    return tag.rsplit("}", 1)[-1]


def child(el, name):
    for c in el:
        if local(c.tag) == name:
            return c
    return None


def text(el, name, default=""):
    c = child(el, name)
    return (c.text or default).strip() if c is not None else default


def parse(path):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError(f"{path}: larger than {MAX_BYTES} bytes, refusing")
    head = raw.upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in head:
        raise ValueError(f"{path}: contains a DOCTYPE or ENTITY declaration, refusing")
    root = ET.fromstring(raw)
    md, pp = child(root, "report_metadata"), child(root, "policy_published")
    rows = []
    for rec in [c for c in root if local(c.tag) == "record"]:
        row, ids, auth = child(rec, "row"), child(rec, "identifiers"), child(rec, "auth_results")
        pe = child(row, "policy_evaluated")
        rows.append({
            "ip": text(row, "source_ip"), "count": int(text(row, "count", "0")),
            "dkim": text(pe, "dkim"), "spf": text(pe, "spf"), "disposition": text(pe, "disposition"),
            "header_from": text(ids, "header_from"),
            "dkim_domains": [text(d, "domain") for d in auth if local(d.tag) == "dkim"] if auth is not None else [],
            "spf_domains": [text(d, "domain") for d in auth if local(d.tag) == "spf"] if auth is not None else [],
        })
    dr = child(md, "date_range")
    when = [datetime.fromtimestamp(int(text(dr, k)), timezone.utc).strftime("%Y-%m-%d %H:%MZ") for k in ("begin", "end")]
    return {"reporter": text(md, "org_name"), "id": text(md, "report_id"), "when": when,
            "domain": text(pp, "domain"), "p": text(pp, "p"), "rows": rows}


def summarize(reports):
    by_ip = defaultdict(lambda: {"total": 0, "pass": 0, "fail": 0, "froms": set(), "dkim": set(), "spf": set()})
    for rep in reports:
        for r in rep["rows"]:
            s = by_ip[r["ip"]]
            ok = r["dkim"] == "pass" or r["spf"] == "pass"
            s["total"] += r["count"]
            s["pass" if ok else "fail"] += r["count"]
            s["froms"].add(r["header_from"])
            s["dkim"].update(r["dkim_domains"])
            s["spf"].update(r["spf_domains"])
    return by_ip


def main(argv):
    if not argv:
        sys.exit("usage: dmarc_report.py REPORT.xml ...")
    reports = [parse(p) for p in argv]
    for rep in reports:
        print(f"report {rep['id']} from {rep['reporter']}: {rep['when'][0]} to {rep['when'][1]}, domain {rep['domain']}, published p={rep['p']}")
    by_ip = summarize(reports)
    total = sum(s["total"] for s in by_ip.values())
    print(f"\n{'source ip':16} {'messages':>8} {'pass':>6} {'fail':>6}  signed-by / mail-from domains")
    for ip, s in sorted(by_ip.items(), key=lambda kv: -kv[1]["fail"]):
        print(f"{ip:16} {s['total']:8} {s['pass']:6} {s['fail']:6}  dkim={','.join(sorted(s['dkim'])) or '-'} spf={','.join(sorted(s['spf'])) or '-'}")
    bad = sum(s["fail"] for s in by_ip.values())
    print(f"\n{bad} of {total} messages ({100 * bad / total:.1f}%) fail DMARC. Enforcing now would act on all of them." if total else "no records")
    print("Next step for each failing source: is it yours (fix SPF or DKIM alignment) or not (that is what enforcement is for)?")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
