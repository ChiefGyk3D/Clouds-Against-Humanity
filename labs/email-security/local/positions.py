#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""positions.py [--lockdown yes|no] [--lag MIN] [--click MIN]: where a filter sits decides what it can see.

A pure-computation toy. Three positions look at the same synthetic messages with the same toy detector:
  gateway     in front of the mailbox service, on the MX path, decides before delivery, external mail only
  api-after   connected by API, sees every message in the mailbox (including internal), acts after delivery
  api-inline  the API product's inline mode: a mail-flow rule sends mail through its cloud before delivery
Nothing here models any vendor's real engine, speed or accuracy. It shows what each POSITION can and cannot
observe, which is the part that does not depend on the vendor. All numbers are invented.
"""
import argparse
import sys

# id, label, channel, origin, route, attributes (each a reason a detector rule could use)
MESSAGES = [
    ("M1", "external spoof of our own domain", "email", "external", "mx", {"auth_fail"}, True, None),
    ("M2", "external phish, link already known bad", "email", "external", "mx", {"bad_url_now"}, True, None),
    ("M3", "external phish, link clean at delivery, turns bad at +40 min", "email", "external", "mx", set(), True, 40),
    ("M4", "external phish sent straight to the tenant, skipping the gateway MX", "email", "external", "direct", {"bad_url_now"}, True, None),
    ("M5", "internal phish from a compromised colleague", "email", "internal", "internal", {"bad_url_now"}, True, None),
    ("M6", "Teams message with a bad link", "teams", "internal", "internal", {"bad_url_now"}, True, None),
    ("M7", "look-alike domain asks for a wire (no link)", "email", "external", "mx", {"lookalike"}, True, None),
    ("M8", "real vendor, account taken over, unusual request", "email", "external", "mx", {"behavior_anomaly"}, True, None),
    ("M9", "harmless newsletter", "email", "external", "mx", set(), False, None),
    ("M10", "real invoice from a new vendor, odd domain", "email", "external", "mx", {"lookalike"}, False, None),
]
# rules every position shares, then one only a position with mailbox history can use
SHARED = {"auth_fail", "bad_url_now", "lookalike"}
HISTORY = {"behavior_anomaly"}


def decide(position, m, lockdown, lag, click):
    mid, label, channel, origin, route, attrs, truth, turns_bad = m
    if route == "direct" and lockdown == "yes":
        return "flag before delivery", truth  # the tenant refuses mail that did not come from the gateway
    sees = True
    if position == "gateway":
        sees = channel == "email" and origin == "external" and route == "mx"  # direct mail never crossed it
    elif position == "api-inline":
        sees = channel == "email"  # a mail-flow rule covers email only, internal mail included
    if not sees:
        return "not seen", truth
    rules = SHARED | (HISTORY if position != "gateway" else set())  # only the API products read mailbox history
    before = position in ("gateway", "api-inline")
    if attrs & rules:
        return ("flag before delivery" if before else f"flag +{lag} min"), truth
    if turns_bad is not None and position != "gateway":
        return f"flag +{turns_bad + lag} min", truth  # a rescan after the link's reputation changed
    return "no flag", truth


def outcome(verdict, truth, click):
    if verdict.startswith("flag"):
        if not truth:
            return "FALSE POSITIVE"
        if verdict == "flag before delivery":
            return "stopped before the inbox"
        minutes = int(verdict.split("+")[1].split()[0])
        return "removed before the click" if minutes <= click else "removed AFTER the click"
    return "MISSED" if truth else "ok"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--lockdown", choices=["yes", "no"], default="yes")
    ap.add_argument("--lag", type=int, default=5, help="minutes an after-delivery product needs to act (invented)")
    ap.add_argument("--click", type=int, default=10, help="minutes until the user clicks (invented)")
    a = ap.parse_args(argv)
    positions = ["gateway", "api-after", "api-inline"]
    print(f"lockdown={a.lockdown} lag={a.lag}min click-after={a.click}min   (toy numbers)\n")
    print(f"{'':4}{'message':62}" + "".join(f"{p:26}" for p in positions))
    score = {p: {"stopped": 0, "late": 0, "missed": 0, "fp": 0} for p in positions}
    for m in MESSAGES:
        cells = []
        for p in positions:
            verdict, truth = decide(p, m, a.lockdown, a.lag, a.click)
            o = outcome(verdict, truth, a.click)
            cells.append(f"{o:26}")
            key = ("stopped" if o in ("stopped before the inbox", "removed before the click") else "late" if "AFTER" in o
                   else "missed" if o == "MISSED" else "fp" if o == "FALSE POSITIVE" else None)
            if key:
                score[p][key] += 1
        print(f"{m[0]:4}{m[1][:60]:62}" + "".join(cells))
    print("\nscore (bad messages stopped in time / removed late / missed; false positives):")
    for p in positions:
        s = score[p]
        print(f"  {p:11} stopped={s['stopped']} late={s['late']} missed={s['missed']} false_positives={s['fp']}")
    print("\nRead the table by position, not by product: with the tenant locked down the gateway still never sees M5 or M6 (internal), and without lockdown it misses M4 too; the API positions cannot act before delivery unless a")
    print("mail-flow rule sends mail through them first; and M8 and M10 show that no position removes the need for a person to decide.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
