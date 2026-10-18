"""Generate docs/wiki/Settings-Reference.md from docs/settings.json.

The manifest is the source of truth for every tunable setting. This script
renders it as a wiki page. With --check it writes nothing and fails (exit 1)
when the committed page differs from what the manifest produces, the same
idea as the wiki generator's check mode.

Usage (from anywhere inside a clone):
  python -I scripts/gen_settings_doc.py            write the page
  python -I scripts/gen_settings_doc.py --check    fail if the page is stale
  python -I scripts/gen_settings_doc.py --root DIR use a different repository root

Exit codes: 0 ok, 1 stale page (--check) or unreadable manifest, 2 usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MANIFEST = Path("docs") / "settings.json"
PAGE = Path("docs") / "wiki" / "Settings-Reference.md"

SENSITIVITY_TEXT = {
    "public": "public",
    "private": "private (not a credential, but identifies the owner)",
    "secret": "secret",
    "bootstrap-credential": "bootstrap credential (a short-lived bearer token rendered into user_data for first boot)",
}

HEADER = """\
<!-- GENERATED from docs/settings.json by scripts/gen_settings_doc.py. Do not edit
this page by hand: change the manifest and run `python -I scripts/gen_settings_doc.py`.
CI fails when this page is out of date. -->

# Settings reference: every tunable setting

> New to the tools? Read [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) first. This page is a lookup table, not a lesson.

This page lists every setting you can change in this repository, where each one lives, and what values it accepts. It is generated from one machine-readable file, `docs/settings.json`, and tests check that file against the code, so a variable cannot be added without being listed here.

## Four kinds of place a value can live

| Place | What it holds | In git? | Example here |
|---|---|---|---|
| A variable (`variables.tf`) | The name, type, description, validation and default of a setting. This is the *definition*, not the value for your site. | Yes | `region`, `vpc_ip_range` |
| A value file (`terraform.tfvars`) | The values for *your* site. Ignored by git (`.gitignore` covers `*.tfvars`, `*.tfvars.json`, `*.auto.tfvars.json` and `*.tfplan`), so a real value never lands in a public repository by accident. A committed `terraform.tfvars.example` shows the shape with documentation-range values only. | No (the `.example` file, yes) | a private copy of the repository keeps its own |
| Environment variables (`TF_VAR_*`) | The same values delivered to a run, from the Spacelift stack environment (non-secret) or from Doppler (private values and secrets). | No | `TF_VAR_admin_user_ids` |
| `cost.json` and `approved.json` | Droplet sizes and the approved spend. The cost gate reads them, so the size lives there and nowhere else. | Yes | `stacks/10-access/cost.json` |

Two rules follow. **A secret is never a variable default and never in a value file**: a value file is a plain file with no access control, and it is copied to laptops, chats and shell history. Secrets live in Doppler and arrive as an environment variable for one run. And **a setting that is hard-coded today is listed too**, so you can see it is not yet a knob.

Related pages: [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) (what a stack and a module are), [Doppler and secrets](Doppler-and-Secrets.md) (how a secret reaches a run), [Fork, private stacks and the pipeline](Fork-Private-Stacks-and-the-Pipeline.md) (keeping your real values in a private copy), [Terraform reference](Terraform-Reference.md) (each declaration explained).

**How to read the tables.** *Status* is `exists` (in the code today) or `planned` (in the stage 2 design, not built yet). *Sensitivity* is `public` (safe for anyone), `private` (not a credential, but it identifies the owner's network or accounts) `secret` (a credential) or `bootstrap-credential` (a short-lived bearer token that has to be rendered into `user_data` so a machine can pull its own secrets once at first boot; it is a credential, not a plain private value, and only the log shipping bootstrap token has this class). Examples use documentation ranges (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`), private ranges, and `example.com` only; none is a real value.
"""


def pipes(value: object) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    return text.replace("|", "\\|")


def cell(value: object) -> str:
    """Render prose for a Markdown table cell (angle brackets are escaped)."""
    return pipes(value).replace("<", "&lt;").replace(">", "&gt;").replace("$", "\\$")


def code(value: object) -> str:
    text = pipes(value)
    return f"`{text}`" if text else ""


def show_default(entry: dict) -> str:
    if entry.get("required"):
        return "required"
    value = entry.get("default")
    if isinstance(value, str):
        if value.startswith(("{", "[")):
            return code(value)
        return code(json.dumps(value))
    return code(json.dumps(value))


def anchor(title: str) -> str:
    return "".join(
        c for c in title.lower().replace(" ", "-") if c.isalnum() or c == "-"
    )


def render_variables(sections: dict) -> list[str]:
    out = ["## OpenTofu variables", ""]
    out.append(
        "Stack variables are the settings you set per site. Module variables are filled in by the calling stack; "
        "they are listed so the table is complete, and you normally leave them alone."
    )
    out.append("")
    for place, entries in sections.items():
        out.append(f"### {place}")
        out.append("")
        out.append(
            "| Setting | Type | Default | Validation | Set where | Example | Sensitivity | Status |"
        )
        out.append("|---|---|---|---|---|---|---|---|")
        for e in entries:
            notes = ""
            if e.get("planned_change"):
                notes = f" Planned change: {cell(e['planned_change'])}"
            out.append(
                "| "
                + " | ".join(
                    [
                        code(e["name"])
                        + (
                            "<br>" + cell(e["description"]) + notes
                            if e.get("description")
                            else ""
                        ),
                        code(e["type"]),
                        show_default(e),
                        cell(e["validation"]),
                        cell(e["set_where"]),
                        code(e["example"]),
                        cell(SENSITIVITY_TEXT.get(e["sensitivity"], e["sensitivity"])),
                        cell(e["status"]),
                    ]
                )
                + " |"
            )
        out.append("")
    return out


def render_manifests(entries: list[dict]) -> list[str]:
    out = [
        "## Values read from `cost.json`, `approved.json` and the price table",
        "",
        "These are not OpenTofu variables. The cost gate (`scripts/cost_check.py`) reads them, and stack 10 reads its droplet sizes from `cost.json`, so there is one source of truth for money. To change a size you edit `cost.json` and `docs/stages/approved.json` together; that is the lesson.",
        "",
        "| Setting | File | Pointer | Current value | Validation | Example | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in entries:
        out.append(
            "| "
            + " | ".join(
                [
                    cell(e["name"]),
                    code(e["file"]),
                    code(e["pointer"]),
                    code(json.dumps(e["current"])),
                    cell(e["validation"]),
                    code(e["example"]),
                    cell(e["status"]),
                ]
            )
            + " |"
        )
    out.append("")
    return out


def render_hardcoded(entries: list[dict]) -> list[str]:
    out = [
        "## Settings that are hard-coded today",
        "",
        "These are literals in the code, not variables. They are listed so the table is complete and so you know a change is a code edit, not a value.",
        "",
        "| Setting | Where | Current value | Validation | Plan | Status |",
        "|---|---|---|---|---|---|",
    ]
    for e in entries:
        out.append(
            "| "
            + " | ".join(
                [
                    cell(e["name"]),
                    code(e["file"]),
                    code(e["current"]),
                    cell(e["validation"]),
                    cell(e["converted_by"]),
                    cell(e["status"]),
                ]
            )
            + " |"
        )
    out.append("")
    return out


def render_secrets(entries: list[dict]) -> list[str]:
    out = [
        "## Secrets and private values: names only",
        "",
        "This table lists names and where they live. It never holds a value. See [Doppler and secrets](Doppler-and-Secrets.md) for how they reach a run.",
        "",
        "| Name | Class | Lives in | Used by | Delivered as | Expiry | Rotation | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for e in entries:
        out.append(
            "| "
            + " | ".join(
                [
                    code(e["name"]),
                    cell(e["class"]),
                    cell(e["store"]),
                    cell(", ".join(e["used_by"])),
                    cell(e["delivered_as"]),
                    cell(e["expiry"]),
                    cell(e["rotation"]),
                    cell(e["status"]),
                ]
            )
            + " |"
        )
    out.append("")
    return out


def render_external(entries: list[dict]) -> list[str]:
    out = [
        "## Settings that live somewhere else",
        "",
        "Nothing here is checked by a machine except that a pointer file exists. Each has an owner and a place to look.",
        "",
        "| Setting | Owner | Where | Pointer | Status |",
        "|---|---|---|---|---|",
    ]
    for e in entries:
        out.append(
            "| "
            + " | ".join(
                [
                    cell(e["name"]),
                    cell(e["owner"]),
                    cell(e["where"]),
                    cell(e["pointer"]),
                    cell(e["status"]),
                ]
            )
            + " |"
        )
    out.append("")
    return out


FOOTER = """\
Next: [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md), step 5 of the build track on the [Reading order](Reading-Order.md) page, which says which of these places a value belongs in and why.
"""


def render(manifest: dict) -> str:
    lines = [HEADER.rstrip("\n"), ""]
    lines += render_variables(manifest["variables"])
    lines += render_manifests(manifest["manifests"])
    lines += render_hardcoded(manifest["hardcoded"])
    lines += render_secrets(manifest["secrets"])
    lines += render_external(manifest["external"])
    lines += ["", FOOTER.rstrip("\n")]
    return "\n".join(lines).rstrip("\n") + "\n"


def load_manifest(root: Path) -> dict:
    path = root / MANIFEST
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"gen_settings_doc: cannot read {path}: {exc}") from exc
    for key in ("variables", "manifests", "secrets", "hardcoded", "external"):
        if key not in data:
            raise SystemExit(f"gen_settings_doc: {path} has no {key!r} section")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check", action="store_true", help="fail if the committed page is stale"
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="repository root",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    page = root / PAGE
    wanted = render(load_manifest(root))
    if args.check:
        have = page.read_text(encoding="utf-8") if page.is_file() else None
        if have != wanted:
            print(
                f"gen_settings_doc: {PAGE} is out of date; run: python -I scripts/gen_settings_doc.py",
                file=sys.stderr,
            )
            return 1
        print(f"gen_settings_doc: {PAGE} is up to date")
        return 0
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(wanted, encoding="utf-8")
    print(f"gen_settings_doc: wrote {PAGE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
