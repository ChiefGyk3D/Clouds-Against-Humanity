#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""mailauth.py: a teaching evaluator for SPF, DKIM and DMARC. Standard library plus `openssl`.

    python3 mailauth.py eval  --zone zone.json  manifest.json     (answers from a file; no network)
    python3 mailauth.py eval  --dns 127.0.0.1:5300 manifest.json  (asks a local DNS server, e.g. dnsmasq)
    python3 mailauth.py spf   --zone zone.json --ip 192.0.2.25 --domain example.test

It follows RFC 7208 (SPF, with the 10-lookup and 2-void-lookup limits), RFC 6376 (DKIM, via dkimlite.py)
and the shape of DMARC in RFC 9989 (alignment, p/sp, relaxed/strict). Teaching simplifications, on
purpose: the organizational domain is the last two labels (RFC 9989 uses a DNS Tree Walk; RFC 7489 used
the Public Suffix List), np= and t= are read but not applied, ptr is refused, and HELO is not checked.
It only ever talks to the zone file or the DNS server you name; it never queries the public internet.
"""
import argparse
import ipaddress
import json
import random
import re
import socket
import struct
import sys
from pathlib import Path

import dkimlite

TYPES = {"A": 1, "MX": 15, "TXT": 16, "AAAA": 28}


class FileResolver:
    """Answers from a JSON zone: {name: {"TXT": [[chunk, ...]], "MX": [[pref, host]], "A": [ip]}}."""

    def __init__(self, path):
        self.zone = {k.lower(): v for k, v in json.loads(Path(path).read_text()).items()}

    def query(self, name, rtype):
        name = name.lower().rstrip(".")
        node = self.zone.get(name)
        if node is None:
            return "NXDOMAIN", []
        vals = node.get(rtype, [])
        if rtype == "TXT":
            vals = ["".join(chunks) for chunks in vals]
        return "NOERROR", [tuple(v) if isinstance(v, list) else v for v in vals]


class UdpResolver:
    """A tiny DNS client (RFC 1035) for one server, e.g. a local dnsmasq on 127.0.0.1:5300."""

    def __init__(self, hostport):
        host, _, port = hostport.partition(":")
        self.server = (host, int(port or 53))

    @staticmethod
    def _name(data, off):
        labels, jumped, end = [], False, off
        for _ in range(128):
            n = data[off]
            if n == 0:
                off += 1
                break
            if n & 0xC0 == 0xC0:
                ptr = ((n & 0x3F) << 8) | data[off + 1]
                if not jumped:
                    end = off + 2
                jumped, off = True, ptr
                continue
            labels.append(data[off + 1:off + 1 + n].decode("ascii", "replace"))
            off += 1 + n
        return ".".join(labels), (end if jumped else off)

    def query(self, name, rtype):
        qname = b"".join(bytes([len(x)]) + x.encode() for x in name.rstrip(".").split(".")) + b"\0"
        pkt = struct.pack(">HHHHHH", random.randrange(65536), 0x0100, 1, 0, 0, 0) + qname + struct.pack(">HH", TYPES[rtype], 1)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(2.0)
            try:
                s.sendto(pkt, self.server)
                data, _ = s.recvfrom(4096)
            except OSError:
                return "SERVFAIL", []
        rcode = data[3] & 0x0F
        if rcode == 3:
            return "NXDOMAIN", []
        if rcode != 0:
            return "SERVFAIL", []
        qd, an = struct.unpack(">HH", data[4:8])
        off = 12
        for _ in range(qd):
            _, off = self._name(data, off)
            off += 4
        out = []
        for _ in range(an):
            _, off = self._name(data, off)
            rt, _, _, ln = struct.unpack(">HHIH", data[off:off + 10])
            rd = data[off + 10:off + 10 + ln]
            if rt == 16 and rtype == "TXT":
                parts, i = [], 0
                while i < len(rd):
                    parts.append(rd[i + 1:i + 1 + rd[i]].decode("utf-8", "replace"))
                    i += 1 + rd[i]
                out.append("".join(parts))
            elif rt == 15 and rtype == "MX":
                out.append((struct.unpack(">H", rd[:2])[0], self._name(data, off + 12)[0]))
            elif rt == 1 and rtype == "A":
                out.append(socket.inet_ntoa(rd))
            elif rt == 28 and rtype == "AAAA":
                out.append(socket.inet_ntop(socket.AF_INET6, rd))
            off += 10 + ln
        return "NOERROR", out


class Limit(Exception):
    pass


class SpfState:
    def __init__(self):
        self.lookups, self.voids, self.trace = 0, 0, []

    def count(self, what):
        self.lookups += 1
        self.trace.append(f"lookup {self.lookups}: {what}")
        if self.lookups > 10:
            raise Limit("more than 10 DNS-querying terms (RFC 7208 section 4.6.4)")

    def void(self, what):
        self.voids += 1
        self.trace.append(f"void lookup {self.voids}: {what} returned nothing")
        if self.voids > 2:
            raise Limit("more than 2 void lookups (RFC 7208 section 4.6.4)")


def _match_hosts(res, st, hosts, ip, cidr4, cidr6):
    addr = ipaddress.ip_address(ip)
    for h in hosts:
        rc, vals = res.query(h, "A" if addr.version == 4 else "AAAA")
        if not vals:
            st.void(f"{h} {'A' if addr.version == 4 else 'AAAA'}")
        for v in vals:
            net = ipaddress.ip_network(f"{v}/{cidr4 if addr.version == 4 else cidr6}", strict=False)
            if addr in net:
                return True
    return False


def spf_check(res, ip, domain, st, depth=0):
    if depth > 10:
        raise Limit("include/redirect nesting too deep")
    rc, txts = res.query(domain, "TXT")
    if rc == "SERVFAIL":
        return "temperror"
    recs = [t for t in txts if re.match(r"v=spf1(\s|$)", t, re.I)]
    if not recs:
        return "none"
    if len(recs) > 1:
        st.trace.append(f"{domain}: {len(recs)} SPF records published; exactly one is allowed")
        return "permerror"
    st.trace.append(f"{domain}: {recs[0]}")
    redirect, addr = None, ipaddress.ip_address(ip)
    for term in recs[0].split()[1:]:
        if term.lower().startswith("redirect="):
            redirect = term[9:]
            continue
        if re.match(r"[a-z0-9_-]+=", term, re.I):
            continue  # exp= and unknown modifiers
        q = "+"
        if term[0] in "+-~?":
            q, term = term[0], term[1:]
        mech, _, arg = term.partition(":")
        low = mech.lower()
        matched = False
        if low in ("ip4", "ip6"):
            net = ipaddress.ip_network(arg, strict=False)
            matched = addr.version == net.version and addr in net
        elif low == "all":
            matched = True
        elif low == "include":
            st.count(f"include:{arg}")
            r = spf_check(res, ip, arg, st, depth + 1)
            if r in ("temperror", "permerror"):
                return r
            if r == "none":
                st.trace.append(f"include:{arg} has no SPF record")
                return "permerror"
            matched = r == "pass"
        elif re.match(r"(a|mx)(:|/|$)", term, re.I):
            cm = re.match(r"(a|mx)(?::([^/\s]+))?(?:/(\d+))?(?://(\d+))?$", term, re.I)
            if not cm:
                st.trace.append(f"cannot parse {term!r}")
                return "permerror"
            kind, target = cm.group(1).lower(), cm.group(2) or domain
            c4, c6 = int(cm.group(3) or 32), int(cm.group(4) or 128)
            st.count(f"{kind}:{target}")
            if kind == "a":
                matched = _match_hosts(res, st, [target], ip, c4, c6)
            else:
                _, mxs = res.query(target, "MX")
                if not mxs:
                    st.void(f"{target} MX")
                hosts = [h for _, h in sorted(mxs)][:10]
                matched = _match_hosts(res, st, hosts, ip, c4, c6)
        elif low == "exists":
            st.count(f"exists:{arg}")
            _, vals = res.query(arg, "A")
            if not vals:
                st.void(f"{arg} A")
            matched = bool(vals)
        elif low == "ptr":
            st.trace.append("ptr is not supported here (RFC 7208 says it SHOULD NOT be used)")
            return "permerror"
        else:
            st.trace.append(f"unknown mechanism {mech!r}")
            return "permerror"
        if matched:
            return {"+": "pass", "-": "fail", "~": "softfail", "?": "neutral"}[q]
    if redirect:
        st.count(f"redirect={redirect}")
        r = spf_check(res, ip, redirect, st, depth + 1)
        return "permerror" if r == "none" else r
    return "neutral"


def spf(res, ip, domain):
    st = SpfState()
    try:
        return spf_check(res, ip, domain, st), st
    except Limit as exc:
        st.trace.append(f"LIMIT: {exc}")
        return "permerror", st


def org_domain(d):
    return ".".join(d.lower().rstrip(".").split(".")[-2:])


def aligned(a, b, mode):
    return a.lower() == b.lower() if mode == "s" else org_domain(a) == org_domain(b)


def dmarc_policy(res, from_domain):
    """Return (record_dict, where) or (None, None). Exact name first, then the organizational domain."""
    for name in dict.fromkeys([from_domain, org_domain(from_domain)]):
        _, txts = res.query(f"_dmarc.{name}", "TXT")
        recs = [t for t in txts if re.match(r"v=DMARC1\s*;", t.strip(), re.I)]
        if len(recs) == 1:
            tags = {}
            for part in recs[0].split(";"):
                k, _, v = part.partition("=")
                if k.strip():
                    tags[k.strip().lower()] = v.strip()
            return tags, name
    return None, None


def evaluate(res, raw, client_ip, mail_from):
    headers, _ = dkimlite.split_message(raw)
    froms = [r for n, r in headers if n.lower() == "from"]
    # DKIM picks the bottom-most instance of a header (RFC 6376 section 5.4.2); use the same one here
    frm = (froms[-1] if froms else b"").decode("utf-8", "replace")
    from_addr = re.findall(r"[\w.+-]+@([\w.-]+)", frm.partition(":")[2])
    from_domain = (from_addr[-1] if from_addr else "").lower()
    # Anything that makes the author ambiguous fails DMARC instead of being resolved by a guess.
    ambiguous = None
    if len(froms) > 1:
        ambiguous = f"{len(froms)} From headers: DMARC cannot evaluate an ambiguous author, so it fails"
    elif len(set(from_addr)) > 1 or len(from_addr) > 1:
        ambiguous = f"the From header holds {len(from_addr)} addresses: the author is ambiguous, so DMARC fails"
    elif dkimlite.has_bare_cr(raw):
        ambiguous = "a bare CR in the headers: parsers disagree about where the lines end, so DMARC fails"
    mf_domain = mail_from.rpartition("@")[2].lower() if mail_from else ""
    out = {"from_domain": from_domain, "mail_from_domain": mf_domain, "from_headers": len(froms)}
    if ambiguous:
        out["reason"] = ambiguous
    out["spf"], st = spf(res, client_ip, mf_domain) if mf_domain else ("none", SpfState())
    out["spf_trace"], out["spf_lookups"] = st.trace, st.lookups

    def lookup_txt(name):
        _, vals = res.query(name, "TXT")
        return vals[0] if vals else None

    out["dkim"] = dkimlite.verify(raw, lookup_txt)
    rec, where = dmarc_policy(res, from_domain)
    out["dmarc_record"], out["dmarc_found_at"] = rec, where
    if rec is None:
        out.update(dmarc="none", disposition="no DMARC policy", spf_aligned=False, dkim_aligned=False)
        return out
    multi = ambiguous is not None  # RFC 7489 section 6.6.1 / RFC 9989: an ambiguous From is not evaluated as a pass
    out["spf_aligned"] = not multi and out["spf"] == "pass" and aligned(mf_domain, from_domain, rec.get("aspf", "r").lower())
    out["dkim_aligned"] = not multi and any(d["result"] == "pass" and aligned(d["d"], from_domain, rec.get("adkim", "r").lower()) for d in out["dkim"])
    if multi:
        out["reason"] = ambiguous
    if out["spf_aligned"] or out["dkim_aligned"]:
        out.update(dmarc="pass", disposition="deliver")
    else:
        policy = rec.get("p", "none").lower()
        if where != from_domain and "sp" in rec:
            policy = rec["sp"].lower()
        out.update(dmarc="fail", disposition={"none": "deliver (p=none: monitor only)", "quarantine": "quarantine", "reject": "reject"}.get(policy, "deliver"))
    return out


def authres(r, authserv="mx.receiver.test"):
    """An RFC 8601 Authentication-Results value, the way a receiving server would stamp it."""
    dk = "; ".join(f"dkim={d['result']} header.d={d['d']} header.s={d['s']}" for d in r["dkim"]) or "dkim=none"
    return (f"{authserv}; spf={r['spf']} smtp.mailfrom={r['mail_from_domain'] or 'none'}; {dk}; "
            f"dmarc={r['dmarc']} header.from={r['from_domain']}")


def make_resolver(args):
    return FileResolver(args.zone) if args.zone else UdpResolver(args.dns or "127.0.0.1:5300")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("eval", "spf"):
        p = sub.add_parser(name)
        p.add_argument("--zone")
        p.add_argument("--dns")
    sub.choices["eval"].add_argument("manifest")
    sub.choices["eval"].add_argument("--explain", action="store_true")
    sub.choices["spf"].add_argument("--ip", required=True)
    sub.choices["spf"].add_argument("--domain", required=True)
    args = ap.parse_args(argv)
    res = make_resolver(args)
    if args.cmd == "spf":
        result, st = spf(res, args.ip, args.domain)
        print("\n".join(st.trace))
        print(f"result={result} dns_lookups={st.lookups}")
        return 0
    base = Path(args.manifest).parent
    rows = json.loads(Path(args.manifest).read_text())
    print(f"{'message':36} {'SPF':9} {'DKIM':8} {'DMARC':6} {'aligned':8} disposition")
    for m in rows:
        r = evaluate(res, (base / m["file"]).read_bytes(), m["client_ip"], m["mail_from"])
        dk = ",".join(d["result"] for d in r["dkim"]) or "none"
        al = ("S" if r["spf_aligned"] else "-") + ("D" if r["dkim_aligned"] else "-")
        print(f"{m['file'].split('/')[-1]:36} {r['spf']:9} {dk:8} {r['dmarc']:6} {al:8} {r['disposition']}")
        if args.explain:
            for line in r["spf_trace"]:
                print("    spf:", line)
            for d in r["dkim"]:
                print(f"    dkim: d={d['d']} s={d['s']} {d['result']}: {d['reason']}")
            print("    authres:", authres(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
