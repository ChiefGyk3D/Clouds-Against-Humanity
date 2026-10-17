"""Generate stacks/<stack>/tests/example.tftest.hcl from terraform.tfvars.example.

The example value file is only worth committing if it is valid. OpenTofu has no
way to validate a tfvars file without real providers, but a test file's
`variables { }` block takes the same assignments, so this script wraps the
example verbatim in a test that plans the stack with mocked providers. Every
validation then runs against the example, in the same `tofu test` that CI
already runs for the stack.

Usage (from the repository root):
  python -I scripts/gen_example_tests.py            write the test files
  python -I scripts/gen_example_tests.py --check    fail if one is stale
  python -I scripts/gen_example_tests.py --root DIR use a different root

Exit codes: 0 ok, 1 stale or missing (--check), 2 usage.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

EXAMPLE = "terraform.tfvars.example"
TEST = Path("tests") / "example.tftest.hcl"

HEADER = """\
# GENERATED from terraform.tfvars.example by scripts/gen_example_tests.py. Do not
# edit by hand: change the example file and run
# `python -I scripts/gen_example_tests.py`. CI fails when this file is stale.
# It plans the stack with the example values, so the example stays valid.
"""

MOCKS = {
    "stacks/00-foundation": 'mock_provider "digitalocean" {}\n',
    "stacks/10-access": """\
mock_provider "digitalocean" {
  mock_data "digitalocean_ssh_key" {
    defaults = {
      fingerprint = "aa:bb:cc:dd:ee:ff"
    }
  }
}
mock_provider "twingate" {}
""",
    "stacks/20-telemetry": 'mock_provider "twingate" {}\n',
}

RUN = """\

run "the_example_values_are_valid" {
  command = plan
}
"""


def render(stack: str, root: Path) -> str:
    example = (root / stack / EXAMPLE).read_text(encoding="utf-8")
    body = example.rstrip("\n")
    indented = "\n".join(("  " + line) if line.strip() else "" for line in body.splitlines())
    return f"{HEADER}\n{MOCKS[stack]}\nvariables {{\n{indented}\n}}\n{RUN}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    status = 0
    for stack in MOCKS:
        target = root / stack / TEST
        try:
            want = render(stack, root)
        except OSError as exc:
            print(f"gen_example_tests: {stack}: cannot read {EXAMPLE} ({exc.strerror})", file=sys.stderr)
            return 1
        if args.check:
            have = target.read_text(encoding="utf-8") if target.is_file() else None
            if have != want:
                print(
                    f"gen_example_tests: {stack}/{TEST} is out of date. "
                    "Run: python -I scripts/gen_example_tests.py",
                    file=sys.stderr,
                )
                status = 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(want, encoding="utf-8")
            print(f"gen_example_tests: wrote {stack}/{TEST}")
    return status


if __name__ == "__main__":
    sys.exit(main())
