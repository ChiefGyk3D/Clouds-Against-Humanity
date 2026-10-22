#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""The reviewer's rules for a WordPress-as-code repository, as a script anyone can run.

  python3 -I ci_policy_check.py --workflow FILE.yml --site DIR

Prints one line per finding as `file:line: rule: message` and exits 1 when there is any.
It reads text only (no YAML or JSON library beyond the standard one), never prints a matched
secret value, and runs offline.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FULL_SHA = re.compile(r"[0-9a-f]{40}")
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)")
EXACT = re.compile(r"^\d+(\.\d+){1,3}$")
SECRET_LIKE = re.compile(r"""(password|passwd|secret|token|api[_-]?key)\w*\s*[:=]\s*['"]?([^$'"\s{][^'"\s]{7,})""", re.I)
INJECTION = re.compile(r"\$\{\{\s*(github\.event\.|github\.head_ref)")


def check_workflow(path: Path) -> list[str]:
    out: list[str] = []
    lines = path.read_text().splitlines()
    text = "\n".join(lines)
    if not re.search(r"^permissions:", text, re.M):
        out.append(f"{path}:1: W2: no top-level `permissions:` block (the token would get defaults)")
    if re.search(r"permissions:\s*write-all", text):
        out.append(f"{path}:1: W2: `write-all` permissions")
    run_indent: int | None = None
    for n, line in enumerate(lines, 1):
        stripped = line.strip()
        m = USES.match(line)
        if m:
            target = m.group(1)
            ref = target.partition("@")[2]
            if not target.startswith("./") and not FULL_SHA.fullmatch(ref):
                out.append(f"{path}:{n}: W1: `{target}` is not pinned to a full 40-character commit")
        if (re.search(r"^\s*pull_request_target\s*:", line) or re.search(r"\[.*pull_request_target.*\]", line)
                or re.search(r"^\s*on:\s*pull_request_target\b", line) or re.search(r"^\s*-\s*pull_request_target\b", line)):
            out.append(f"{path}:{n}: W3: pull_request_target runs with secrets on code from a fork")
        if re.search(r"secrets:\s*inherit", line):
            out.append(f"{path}:{n}: W4: `secrets: inherit` hands every secret to the called workflow")
        indent = len(line) - len(line.lstrip())
        if run_indent is not None and stripped and indent <= run_indent:
            run_indent = None
        if run_indent is not None and INJECTION.search(line):
            out.append(f"{path}:{n}: W5: untrusted event text expanded inside a run script")
        if re.match(r"^\s*(?:-\s*)?run:\s*[|>]?\s*$", line) or re.match(r"^\s*(?:-\s*)?run:\s*\S", line):
            run_indent = indent
            if INJECTION.search(line):
                out.append(f"{path}:{n}: W5: untrusted event text expanded inside a run script")
        if SECRET_LIKE.search(line):
            out.append(f"{path}:{n}: W7: a secret-shaped literal (value not shown)")
    if re.search(r"^\s*environment:\s*production\s*$", text, re.M) is None:
        out.append(f"{path}:1: W6: no job uses `environment: production`, so no approval gate can attach")
    return out


def check_site(root: Path) -> list[str]:
    out: list[str] = []
    manifest = root / "composer.json"
    if not manifest.is_file():
        return [f"{root}:1: S1: no composer.json (plugins and themes must be declared, not uploaded)"]
    data = json.loads(manifest.read_text())
    for name, constraint in data.get("require", {}).items():
        if not EXACT.match(str(constraint)):
            out.append(f"{manifest}:1: S2: `{name}` is `{constraint}`, not an exact version")
    ignore = (root / ".gitignore").read_text() if (root / ".gitignore").is_file() else ""
    for needed in ("/vendor/", "/web/wp/", "/web/app/plugins/", "/web/app/uploads/", ".env"):
        if needed not in ignore:
            out.append(f"{root}/.gitignore:1: S3: `{needed}` is not ignored")
    for bad in ("web/app/plugins", "web/app/uploads", "wp-content/plugins", "wp-content/uploads"):
        if (root / bad).exists():
            out.append(f"{root}/{bad}:1: S4: installed code or uploads are committed")
    config = root / "config" / "application.php"
    if not config.is_file():
        out.append(f"{config}:1: S5: no config/application.php")
    else:
        body = config.read_text()
        if not re.search(r"define\(\s*'DISALLOW_FILE_MODS'\s*,\s*true", body):
            out.append(f"{config}:1: S6: DISALLOW_FILE_MODS is not true")
        for n, line in enumerate(body.splitlines(), 1):
            if re.search(r"define\(\s*'(DB_PASSWORD|AUTH_KEY|SECURE_AUTH_KEY|LOGGED_IN_KEY|NONCE_KEY)'\s*,\s*'", line):
                out.append(f"{config}:{n}: S7: a secret is written as a literal (value not shown)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workflow", type=Path)
    ap.add_argument("--site", type=Path)
    args = ap.parse_args()
    if not args.workflow and not args.site:
        ap.error("give --workflow, --site or both")
    findings: list[str] = []
    if args.workflow:
        findings += check_workflow(args.workflow)
    if args.site:
        findings += check_site(args.site)
    for f in findings:
        print(f)
    print(f"{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
