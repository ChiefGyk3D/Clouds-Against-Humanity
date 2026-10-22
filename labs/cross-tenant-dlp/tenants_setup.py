#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Set up the two simulated tenants and a toy policy evaluator.

moto stores bucket policies but, per its own documentation, only takes simple
"Principal: *" statements into account and ignores conditions. So the
enforcement you see in this lab is `policy_allows` below, a teaching toy that
reads the same JSON. Real AWS evaluates far more (see the lesson).
"""
import argparse
import fnmatch
import json
import sys
from pathlib import Path

import boto3

ENDPOINTS = {"a": "http://127.0.0.1:5101", "b": "http://127.0.0.1:5102"}
ACCOUNT_A = "111122223333"  # documentation-style placeholder ids
ACCOUNT_B = "123456789012"
SRC_BUCKET = "governance-extracts"
DST_BUCKET = "analytics-inbox"
TRANSFER_ROLE = f"arn:aws:iam::{ACCOUNT_A}:role/monthly-transfer"
PREFIX = "batch/2026-10/"


def client(tenant: str):
    # Any key pair works against moto; these are labels, not secrets.
    return boto3.client(
        "s3", endpoint_url=ENDPOINTS[tenant], region_name="us-east-1",
        aws_access_key_id=f"lab-{tenant}", aws_secret_access_key=f"lab-{tenant}-label",
    )


def narrow_policy() -> dict:
    """Tenant B lets exactly one role from tenant A put objects under one prefix."""
    return {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AllowMonthlyTransferWriteOnly",
            "Effect": "Allow",
            "Principal": {"AWS": TRANSFER_ROLE},
            "Action": ["s3:PutObject", "s3:PutObjectTagging", "s3:GetObject", "s3:DeleteObject"],
            "Resource": f"arn:aws:s3:::{DST_BUCKET}/{PREFIX}*",
        }],
    }


def broad_policy() -> dict:
    """The mistake: any principal, any action, the whole bucket."""
    return {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "TooBroad", "Effect": "Allow", "Principal": "*",
            "Action": "s3:*", "Resource": [f"arn:aws:s3:::{DST_BUCKET}", f"arn:aws:s3:::{DST_BUCKET}/*"],
        }],
    }


def _as_list(v):
    return v if isinstance(v, list) else [v]


def policy_allows(policy: dict, principal: str, action: str, resource: str) -> bool:
    """Toy evaluator: explicit Deny wins, then any matching Allow, else deny.

    Ignores conditions, NotPrincipal, NotAction, ACLs, SCPs and identity
    policies. A teaching aid only.
    """
    allowed = False
    for st in policy["Statement"]:
        p = st["Principal"]
        principals = ["*"] if p == "*" else _as_list(p.get("AWS", []))
        if not any(x == "*" or x == principal for x in principals):
            continue
        if not any(fnmatch.fnmatch(action, a) for a in _as_list(st["Action"])):
            continue
        if not any(fnmatch.fnmatch(resource, r) for r in _as_list(st["Resource"])):
            continue
        if st["Effect"] == "Deny":
            return False
        allowed = True
    return allowed


def lifecycle_rule() -> dict:
    return {"Rules": [{
        "ID": "backstop-expire-inbound-after-1-day",
        "Status": "Enabled",
        "Filter": {"Prefix": PREFIX},
        "Expiration": {"Days": 1},
    }]}


def setup(data_dir: Path | None) -> None:
    a, b = client("a"), client("b")
    for c, name in ((a, SRC_BUCKET), (b, DST_BUCKET)):
        try:
            c.create_bucket(Bucket=name)
        except c.exceptions.BucketAlreadyOwnedByYou:
            pass
    b.put_bucket_policy(Bucket=DST_BUCKET, Policy=json.dumps(narrow_policy()))
    b.put_bucket_lifecycle_configuration(Bucket=DST_BUCKET, LifecycleConfiguration=lifecycle_rule())
    if data_dir:
        for p in sorted((data_dir / "batch").glob("*")):
            a.put_object(Bucket=SRC_BUCKET, Key=PREFIX + p.name, Body=p.read_bytes())
    print("tenants ready:", SRC_BUCKET, "(A) and", DST_BUCKET, "(B)")
    print("policy and lifecycle read back from B:")
    print(" policy statements:", len(json.loads(b.get_bucket_policy(Bucket=DST_BUCKET)["Policy"])["Statement"]))
    print(" lifecycle rule   :", b.get_bucket_lifecycle_configuration(Bucket=DST_BUCKET)["Rules"][0]["ID"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="directory made by make_fake_data.py")
    ap.add_argument("--check-policies", action="store_true", help="show narrow vs broad")
    a = ap.parse_args()
    if a.check_policies:
        res = f"arn:aws:s3:::{DST_BUCKET}/{PREFIX}x.csv"
        other = f"arn:aws:s3:::{DST_BUCKET}/secret/x.csv"
        stranger = "arn:aws:iam::000000000000:user/stranger"
        for label, pol in (("narrow", narrow_policy()), ("broad", broad_policy())):
            print(label)
            print("  transfer role puts under the prefix :", policy_allows(pol, TRANSFER_ROLE, "s3:PutObject", res))
            print("  transfer role puts outside it       :", policy_allows(pol, TRANSFER_ROLE, "s3:PutObject", other))
            print("  a stranger account reads the batch  :", policy_allows(pol, stranger, "s3:GetObject", res))
        return 0
    setup(Path(a.data) if a.data else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
