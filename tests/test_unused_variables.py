"""Every variable is used, or is on the short documented list of exceptions.

tflint's terraform_unused_declarations rule runs in CI. `site_name` is declared
before anything reads it (the telemetry stage uses it), so it carries a
`tflint-ignore` annotation. This test keeps that list explicit: a new unused
variable fails here instead of being quietly ignored, and an annotation on a
variable that is used (or on one not listed) fails too.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANNOTATION = "tflint-ignore: terraform_unused_declarations"
# (directory, variable): declared on purpose, read by a later stage.
DOCUMENTED_UNUSED = {
    ("stacks/00-foundation", "site_name"),
    ("stacks/10-access", "site_name"),
}


def directories():
    for top in ("stacks", "modules"):
        for path in sorted((ROOT / top).rglob("variables.tf")):
            if ".terraform" not in path.parts:
                yield path.parent


def strip_comments(text: str) -> str:
    return re.sub(r"(?m)(#|//).*$", "", text)


def annotated(directory: Path) -> set[str]:
    text = (directory / "variables.tf").read_text()
    return set(
        re.findall(rf"(?m)^# {re.escape(ANNOTATION)}\nvariable \"([A-Za-z0-9_-]+)\"", text)
    )


def unused(directory: Path) -> set[str]:
    declared = re.findall(
        r'(?m)^variable "([A-Za-z0-9_-]+)"', (directory / "variables.tf").read_text()
    )
    others = "\n".join(
        strip_comments(p.read_text()) for p in directory.glob("*.tf") if p.name != "variables.tf"
    )
    # A variable is used when var.<name> appears in another file, or in a
    # validation of another variable in variables.tf is not use (it is its own).
    return {n for n in declared if not re.search(rf"\bvar\.{re.escape(n)}\b", others)}


def test_there_are_directories_to_check():
    assert len(list(directories())) >= 6


def test_the_unused_variables_are_exactly_the_documented_ones():
    found = {
        (d.relative_to(ROOT).as_posix(), name) for d in directories() for name in unused(d)
    }
    assert found == DOCUMENTED_UNUSED


def test_the_annotations_are_exactly_the_documented_ones():
    found = {
        (d.relative_to(ROOT).as_posix(), name) for d in directories() for name in annotated(d)
    }
    assert found == DOCUMENTED_UNUSED
    for d in directories():
        text = (d / "variables.tf").read_text()
        assert text.count(ANNOTATION) == len(annotated(d)), d
