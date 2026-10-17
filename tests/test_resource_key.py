"""resource_key and site_name (stage 2 design, section 3.1), checked on the sources.

`resource_key` builds NAMES; `region` is only the region argument. `site_name`
is a telemetry label and must never reach a resource name, a tag, a `moved`
target or an output. The tofu tests prove the rendered names; these tests read
every .tf file, so a name built another way, or a site_name used in a new
file, fails here too.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The one file where the telemetry stack reads site_name (see the tests below).
TELEMETRY_SITE_FILE = "stacks/20-telemetry/site.tf"


def source_files():
    """Every .tf file under stacks and modules, except variable declarations."""
    for top in ("stacks", "modules"):
        for path in sorted((ROOT / top).rglob("*.tf")):
            if ".terraform" in path.parts or path.name == "variables.tf":
                continue
            # stack 20 reads site_name in exactly one file; its own test below
            # keeps that file honest, so the general rules skip it.
            if path.relative_to(ROOT).as_posix() == TELEMETRY_SITE_FILE:
                continue
            # resource_key is DigitalOcean-only for now: stacks/<NN-name> and
            # modules/<role>. The AWS code (stacks/aws/*, modules/aws/*) still
            # names from region and has no resource_key; see the PR text.
            if len(path.relative_to(ROOT / top).parts) > 2:
                continue
            yield path


def without_comments(text: str) -> str:
    return re.sub(r"(?m)(#|//).*$", "", text)


def test_resource_key_is_digitalocean_only_for_now():
    # Say so in a test: if an AWS stack or module gains resource_key, this
    # fails and the scope above must be widened on purpose, with golden names.
    for path in (ROOT / "stacks" / "aws").rglob("variables.tf"):
        assert 'variable "resource_key"' not in path.read_text(), path
    for path in (ROOT / "modules" / "aws").rglob("variables.tf"):
        assert 'variable "resource_key"' not in path.read_text(), path


def test_there_are_source_files_to_check():
    assert len(list(source_files())) >= 12


def test_site_name_is_declared_but_never_used():
    for path in source_files():
        assert "site_name" not in without_comments(path.read_text()), (
            f"{path.relative_to(ROOT)} uses site_name; it is for telemetry labels only"
        )


def test_site_name_is_only_declared_in_the_stacks():
    declared = [
        p.parent.relative_to(ROOT).as_posix()
        for p in (ROOT / "stacks").glob("*/variables.tf")
        if 'variable "site_name"' in p.read_text()
    ]
    assert sorted(declared) == [
        "stacks/00-foundation",
        "stacks/10-access",
        "stacks/20-telemetry",
    ]
    for path in (ROOT / "modules").glob("*/variables.tf"):
        assert 'variable "site_name"' not in path.read_text(), path


def test_no_name_is_built_from_the_region_directly():
    # A name must use resource_key (or the modules' name_key). A string that
    # interpolates var.region would ignore resource_key and rename on change.
    pattern = re.compile(r"\$\{[^}]*\bvar\.region\b[^}]*\}")
    for path in source_files():
        assert not pattern.search(without_comments(path.read_text())), (
            f"{path.relative_to(ROOT)} interpolates var.region into a string"
        )


def test_region_is_only_used_as_an_argument_or_a_fallback():
    # Every use of var.region outside variables.tf is either `region = var.region`
    # (the real region argument) or the resource_key fallback.
    allowed = re.compile(
        r"(?m)^\s*region\s*=\s*var\.region\s*$"
        r"|^\s*value\s*=\s*var\.region\s*$"
        r"|\?\s*var\.resource_key\s*:\s*var\.region\b"
        r"|^\s*region\s*=\s*var\.region\b"
    )
    for path in source_files():
        text = without_comments(path.read_text())
        for line in text.splitlines():
            if "var.region" in line:
                assert allowed.search(line), (
                    f"{path.relative_to(ROOT)}: unexpected use of var.region: {line.strip()}"
                )


def test_resource_key_is_passed_down_next_to_every_region():
    # Wherever a module call receives the real region it also receives the key.
    for path in source_files():
        text = without_comments(path.read_text())
        for block in re.findall(r"(?ms)^module\s+\"[^\"]+\"\s*\{\n(.*?)^\}\n", text):
            if re.search(r"(?m)^\s*region\s*=\s*var\.region", block):
                assert re.search(r"(?m)^\s*resource_key\s*=\s*var\.resource_key\s*$", block), (
                    f"{path.relative_to(ROOT)}: a module gets region but not resource_key"
                )


def test_telemetry_reads_site_name_in_one_file_and_only_for_labels():
    # Stack 20 is the telemetry consumer of site_name. It may be read in site.tf
    # (into local.site) and local.site may feed outputs.tf, nothing else.
    stack = ROOT / "stacks" / "20-telemetry"
    site = without_comments((ROOT / TELEMETRY_SITE_FILE).read_text())
    assert "var.site_name" in site
    for path in sorted(stack.glob("*.tf")):
        if path.name in ("variables.tf", "site.tf"):
            continue
        text = without_comments(path.read_text())
        assert "site_name" not in text, f"{path.name} reads site_name"
        if path.name != "outputs.tf":
            assert "local.site" not in text, f"{path.name} uses the site label"
    # No name, tag or moved target is built from the label.
    main = without_comments((stack / "main.tf").read_text())
    assert not re.search(r"(?m)^\s*(name|tags?)\s*=.*(\bsite\b|site_name)", main)
    assert "moved" not in main
