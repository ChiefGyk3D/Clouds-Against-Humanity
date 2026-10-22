#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The monthly batch as one script: extract, transfer, verify, scan, purge, report.

Automate the repetitive steps; keep a human for exceptions. A failed step stops
the run, writes an alert and exits non-zero, and leaves the batch for the
documented manual path (`--sweep` is that path's first command).
"""
import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import dlp_scan
import tenants_setup as t

PURGE_WINDOW_HOURS = 24


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def alert(work: Path, msg: str) -> None:
    line = f"{now().isoformat()} ALERT {msg}"
    print(line, file=sys.stderr)
    with (work / "alerts.log").open("a") as f:
        f.write(line + "\n")  # in real life: page, email or chat, not just a file


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def keys(c, bucket: str) -> list[str]:
    out = []
    for page in c.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=t.PREFIX):
        out += [o["Key"] for o in page.get("Contents", [])]
    return sorted(out)


def run(args) -> int:
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    a, b = t.client("a"), t.client("b")
    ev = {"run_at": now().isoformat(), "dry_run": args.dry_run, "steps": {}}
    try:
        # 0. Preflight: is the transfer role allowed? (toy evaluator)
        pol = json.loads(b.get_bucket_policy(Bucket=t.DST_BUCKET)["Policy"])
        res = f"arn:aws:s3:::{t.DST_BUCKET}/{t.PREFIX}x"
        if not t.policy_allows(pol, t.TRANSFER_ROLE, "s3:PutObject", res):
            raise RuntimeError("preflight: transfer role is not allowed to write to tenant B")
        # 1. Extract: list the batch in tenant A.
        src = keys(a, t.SRC_BUCKET)
        ev["steps"]["extract"] = {"objects": len(src)}
        if not src:
            raise RuntimeError("extract: no objects found; an empty month is an error until a human says otherwise")
        if args.dry_run:
            print(f"DRY RUN: would copy {len(src)} object(s) to {t.DST_BUCKET}, verify, scan, purge")
            return 0
        # 2. Transfer (push). Idempotent: same key and same hash is skipped.
        deadline = (now() + dt.timedelta(hours=PURGE_WINDOW_HOURS)).isoformat()
        copied = 0
        for k in src:
            body = a.get_object(Bucket=t.SRC_BUCKET, Key=k)["Body"].read()
            try:
                if sha(b.get_object(Bucket=t.DST_BUCKET, Key=k)["Body"].read()) == sha(body):
                    continue
            except b.exceptions.NoSuchKey:
                pass
            b.put_object(Bucket=t.DST_BUCKET, Key=k, Body=body, Metadata={"purge-after": deadline})
            copied += 1
        ev["steps"]["transfer"] = {"copied": copied, "purge_after": deadline}
        # 3. Verify: every object arrived and the hashes match.
        bad = []
        for k in src:
            sa = sha(a.get_object(Bucket=t.SRC_BUCKET, Key=k)["Body"].read())
            sb = sha(b.get_object(Bucket=t.DST_BUCKET, Key=k)["Body"].read())
            if args.inject_error == "verify" and k == src[0]:
                sb = "0" * 64  # simulate corruption in transit
            if sa != sb:
                bad.append(k)
        ev["steps"]["verify"] = {"checked": len(src), "mismatches": len(bad)}
        if bad:
            raise RuntimeError(f"verify: {len(bad)} object(s) differ; NOT purging, data stays for a human")
        # 4. Scan (the DLP step) on the staged copy; record counts only.
        stage = work / "stage"
        stage.mkdir(exist_ok=True)
        for k in src:
            (stage / Path(k).name).write_bytes(b.get_object(Bucket=t.DST_BUCKET, Key=k)["Body"].read())
        findings = dlp_scan.scan_path(stage, {"QX-123456-ZZ"}, 2)
        ev["steps"]["scan"] = {"findings": len(findings)}
        for p in stage.glob("*"):
            p.unlink()  # staged copy is purged right after the scan
        # 5. (Processing would happen here, on tenant B.) Then purge.
        if args.inject_error == "purge":
            raise RuntimeError("purge: simulated outage while deleting from tenant B")
        for k in src:
            b.delete_object(Bucket=t.DST_BUCKET, Key=k)
        left = keys(b, t.DST_BUCKET)
        ev["steps"]["purge"] = {"remaining": len(left)}
        if left:
            raise RuntimeError(f"purge: {len(left)} object(s) still present after delete")
        ev["outcome"] = "ok"
        return 0
    except Exception as exc:  # noqa: BLE001 - the job's whole point is to catch and alert
        ev["outcome"] = "failed"
        ev["error"] = str(exc)
        alert(work, f"monthly job failed: {exc}")
        return 2
    finally:
        if not args.dry_run:
            with (work / "evidence.jsonl").open("a") as f:
                f.write(json.dumps(ev) + "\n")  # counts and times only, never content
            print("outcome:", ev.get("outcome", "?"), json.dumps(ev["steps"]))


def sweep(args) -> int:
    """Manual path / backstop: purge anything in tenant B past its deadline,
    and alert on anything old that is still there."""
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    b = t.client("b")
    overdue = 0
    for k in keys(b, t.DST_BUCKET):
        due = b.head_object(Bucket=t.DST_BUCKET, Key=k)["Metadata"].get("purge-after")
        if args.force or (due and dt.datetime.fromisoformat(due) <= now()):
            if args.dry_run:
                print("DRY RUN: would purge", k)
            else:
                b.delete_object(Bucket=t.DST_BUCKET, Key=k)
                print("purged", k)
            overdue += 1
    if overdue and not args.dry_run:
        alert(work, f"sweep purged {overdue} overdue object(s); find out why the job did not")
    remaining = keys(b, t.DST_BUCKET)
    print(f"sweep done, {len(remaining)} object(s) remain in tenant B")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--inject-error", choices=["none", "verify", "purge"], default="none")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--force", action="store_true", help="with --sweep: purge regardless of deadline (a human decision)")
    args = ap.parse_args()
    return sweep(args) if args.sweep else run(args)


if __name__ == "__main__":
    sys.exit(main())
