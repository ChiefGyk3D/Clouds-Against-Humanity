"""The settings manifest (docs/settings.json) against the code, and the ignore rules.

Step 1 of the stage 2 design, section 2.9. What is proved here:
- every `variable` block in every stack and module appears in the manifest
  with the same type, default, sensitivity flag and validation presence, and
  every manifest entry marked "exists" is a real variable (and a "planned" one
  is not yet a variable);
- the other manifest sections point at real things (cost.json keys, literals in
  the code, secret names used by .spacelift/config.yml, pointer files);
- examples use documentation or private ranges and example domains only, and no
  secret carries a value;
- the generated wiki page is not stale;
- `.gitignore` ignores the value files that can hold real settings and does not
  ignore terraform.tfvars.example, and the previous .gitignore text fails that
  test.

The HCL reader (scripts/hcl_variables.py) fails closed: a shape it does not
understand is an error, never a skipped variable.
"""

import ipaddress
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_settings_doc
import hcl_variables

MANIFEST = ROOT / "docs" / "settings.json"
SECTIONS = ("variables", "manifests", "secrets", "hardcoded", "external")
STATUSES = ("exists", "planned")
SENSITIVITIES = ("public", "private", "secret")

VARIABLE_FIELDS = {
    "name",
    "type",
    "description",
    "required",
    "validation",
    "set_where",
    "example",
    "sensitivity",
    "sensitive_in_code",
    "status",
}
MANIFEST_FIELDS = {
    "name",
    "file",
    "pointer",
    "current",
    "stack",
    "validation",
    "set_where",
    "example",
    "sensitivity",
    "status",
}
SECRET_FIELDS = {
    "name",
    "class",
    "store",
    "used_by",
    "delivered_as",
    "expiry",
    "rotation",
    "sensitivity",
    "status",
}
HARDCODED_FIELDS = {
    "name",
    "file",
    "literal",
    "current",
    "stack",
    "validation",
    "set_where",
    "example",
    "sensitivity",
    "converted_by",
    "status",
}
EXTERNAL_FIELDS = {"name", "owner", "where", "pointer", "sensitivity", "status"}

DOC_NETS = [
    ipaddress.ip_network(n)
    for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
]
PRIVATE_NETS = [
    ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
]
IPV4_RE = re.compile(r"(?<![0-9.])([0-9]{1,3}(?:\.[0-9]{1,3}){3})(?![0-9])")
HOST_RE = re.compile(
    r"\b((?:[a-z0-9-]+\.)+(?:com|net|org|io|dev|cloud|local|lan|internal|home|corp))\b",
    re.IGNORECASE,
)
HOST_OK = re.compile(r"(^|\.)example\.(com|net|org)$", re.IGNORECASE)
# A path or file name that happens to end like a host name is not a host.
FILE_SUFFIXES = (".tf", ".json", ".md", ".yml", ".yaml", ".tftpl")

# The .gitignore on main before this change, captured as a fixture.
OLD_GITIGNORE = """\
.terraform/
*.tfstate
*.tfstate.*
crash.log
*.tfvars
!*.tftest.hcl
__pycache__/
.pytest_cache/
.venv/
.superpowers/
"""


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


# --- coverage ------------------------------------------------------------


def normalize_type(text: str) -> str:
    return hcl_variables._normalize_type(text)


def coverage_problems(root: Path, manifest: dict) -> list[str]:
    """Every disagreement between the code under root and the manifest."""
    problems: list[str] = []
    sections = manifest["variables"]
    dirs = {
        d.relative_to(root).as_posix(): d
        for d in hcl_variables.variable_directories(root)
    }

    for key, entries in sections.items():
        if key not in dirs and any(e["status"] == "exists" for e in entries):
            problems.append(
                f"{key}: has 'exists' entries but is not a stack or module directory"
            )
    for rel, directory in dirs.items():
        try:
            code = hcl_variables.variables_in_dir(directory)
        except hcl_variables.HclError as exc:
            problems.append(f"{rel}: cannot read variables ({exc})")
            continue
        entries = sections.get(rel)
        if entries is None:
            if code:
                problems.append(f"{rel}: has variables but no manifest section")
            continue
        names = [e["name"] for e in entries]
        for dup in sorted({n for n in names if names.count(n) > 1}):
            problems.append(f"{rel}: {dup} is listed twice")
        by_name = {e["name"]: e for e in entries}
        for name, var in code.items():
            entry = by_name.get(name)
            if entry is None:
                problems.append(f"{rel}: variable {name} is not in the manifest")
                continue
            if entry["status"] != "exists":
                problems.append(
                    f"{rel}: variable {name} exists in code but the manifest says {entry['status']}"
                )
                continue
            if normalize_type(entry["type"]) != var.type:
                problems.append(
                    f"{rel}: {name} type differs: manifest {entry['type']!r}, code {var.type!r}"
                )
            if entry["required"] == var.has_default:
                problems.append(
                    f"{rel}: {name} required/default disagrees with the code"
                )
            elif var.has_default and entry.get("default") != var.default:
                problems.append(
                    f"{rel}: {name} default differs: manifest {entry.get('default')!r}, code {var.default!r}"
                )
            if entry["sensitive_in_code"] != var.sensitive:
                problems.append(f"{rel}: {name} sensitive flag differs from the code")
            if var.sensitive and entry["sensitivity"] == "public":
                problems.append(
                    f"{rel}: {name} is sensitive in code but 'public' in the manifest"
                )
            has_validation = not entry["validation"].startswith("none")
            if has_validation != (var.validations > 0):
                problems.append(
                    f"{rel}: {name} validation text disagrees with {var.validations} validation block(s)"
                )
            if (
                "has no description" in entry["description"]
                and var.description is not None
            ):
                problems.append(
                    f"{rel}: {name} is said to have no description but has one"
                )
        for name, entry in by_name.items():
            if entry["status"] == "exists" and name not in code:
                problems.append(
                    f"{rel}: manifest lists {name} as existing but the code has no such variable"
                )
    return problems


def test_manifest_has_the_typed_sections():
    manifest = load()
    assert manifest["schema_version"] == 1
    for section in SECTIONS:
        assert section in manifest, section
    assert set(manifest) == {"schema_version", "about", *SECTIONS}


def test_every_variable_and_manifest_entry_agree():
    assert coverage_problems(ROOT, load()) == []


def test_the_directories_found_are_the_ones_expected():
    found = {
        d.relative_to(ROOT).as_posix() for d in hcl_variables.variable_directories(ROOT)
    }
    assert {
        "stacks/00-foundation",
        "stacks/10-access",
        "modules/vpc",
        "modules/firewall",
        "modules/twingate-bootstrap",
        "modules/twingate-connector",
        "modules/aws/vpc",
        "modules/aws/firewall",
        "modules/aws/twingate-connector",
    } <= found


def test_there_are_variables_to_check():
    # Guards against the coverage test passing because nothing was found.
    total = sum(
        len(hcl_variables.variables_in_dir(d))
        for d in hcl_variables.variable_directories(ROOT)
    )
    assert total >= 30


def test_entries_have_every_field():
    manifest = load()
    for place, entries in manifest["variables"].items():
        for e in entries:
            missing = VARIABLE_FIELDS - set(e)
            assert not missing, f"{place}.{e.get('name')} missing {sorted(missing)}"
            assert e["status"] in STATUSES, e["name"]
            assert e["sensitivity"] in SENSITIVITIES, e["name"]
            if not e["required"]:
                assert "default" in e, (
                    f"{place}.{e['name']} is optional but has no default"
                )
            if e["sensitivity"] != "public":
                assert e.get("readers"), (
                    f"{place}.{e['name']} is non-public but lists no readers"
                )
    for key, fields in (
        ("manifests", MANIFEST_FIELDS),
        ("secrets", SECRET_FIELDS),
        ("hardcoded", HARDCODED_FIELDS),
        ("external", EXTERNAL_FIELDS),
    ):
        for e in manifest[key]:
            missing = fields - set(e)
            assert not missing, f"{key}.{e.get('name')} missing {sorted(missing)}"
            assert e["status"] in STATUSES, e["name"]
            assert e["sensitivity"] in SENSITIVITIES, e["name"]


def test_every_name_is_listed_once_per_section():
    manifest = load()
    for key in SECTIONS[1:]:
        names = [e["name"] for e in manifest[key]]
        assert len(names) == len(set(names)), key


@pytest.fixture
def tree(tmp_path):
    """A copy of the stacks and modules, to be broken on purpose."""
    for top in ("stacks", "modules"):
        shutil.copytree(
            ROOT / top,
            tmp_path / top,
            ignore=shutil.ignore_patterns(".terraform", "tests"),
        )
    return tmp_path


def test_coverage_bites_when_a_variable_is_added(tree):
    with (tree / "stacks" / "10-access" / "variables.tf").open("a") as f:
        f.write('\nvariable "fake_setting" {\n  type    = string\n  default = "x"\n}\n')
    problems = coverage_problems(tree, load())
    assert any("fake_setting" in p and "not in the manifest" in p for p in problems), (
        problems
    )


def test_coverage_bites_when_a_variable_is_added_in_another_file(tree):
    (tree / "modules" / "vpc" / "extra.tf").write_text(
        'variable "sneaky" {\n  type = bool\n}\n'
    )
    problems = coverage_problems(tree, load())
    assert any("sneaky" in p for p in problems), problems


def test_coverage_bites_when_a_variable_is_removed(tree):
    path = tree / "stacks" / "00-foundation" / "variables.tf"
    text = path.read_text()
    path.write_text(text.replace('variable "project_name"', 'variable "project_label"'))
    problems = coverage_problems(tree, load())
    assert any("project_name" in p and "no such variable" in p for p in problems), (
        problems
    )
    assert any("project_label" in p for p in problems), problems


def test_coverage_bites_on_a_new_stack_without_a_section(tree):
    new = tree / "stacks" / "30-example"
    new.mkdir()
    (new / "variables.tf").write_text(
        'variable "logging_enabled" {\n  type = bool\n}\n'
    )
    problems = coverage_problems(tree, load())
    assert any(
        "stacks/30-example" in p and "no manifest section" in p for p in problems
    ), problems


def test_coverage_bites_on_a_changed_default_type_and_sensitivity(tree):
    path = tree / "stacks" / "00-foundation" / "variables.tf"
    path.write_text(
        re.sub(r'default(\s+)= "tor1"', r'default\1= "nyc3"', path.read_text())
    )
    path = tree / "stacks" / "10-access" / "variables.tf"
    text = path.read_text()
    text = text.replace("type      = string\n  sensitive = true", "type      = string")
    text = text.replace(
        'admin_user_ids" {\n  type        = list(string)',
        'admin_user_ids" {\n  type        = set(string)',
    )
    path.write_text(text)
    problems = "\n".join(coverage_problems(tree, load()))
    assert "region default differs" in problems
    assert "twingate_network sensitive flag differs" in problems
    assert "admin_user_ids type differs" in problems


def test_coverage_bites_when_a_validation_is_added_or_dropped(tree):
    path = tree / "stacks" / "00-foundation" / "variables.tf"
    path.write_text(
        path.read_text().replace(
            'variable "project_name" {',
            'variable "project_name" {\n  validation {\n    condition     = true\n    error_message = "x"\n  }\n',
        )
    )
    problems = coverage_problems(tree, load())
    assert any("project_name validation text disagrees" in p for p in problems), (
        problems
    )


def test_coverage_bites_when_a_planned_entry_becomes_real(tree):
    with (tree / "stacks" / "00-foundation" / "variables.tf").open("a") as f:
        f.write('\nvariable "provider_name" {\n  type    = string\n  default = "digitalocean"\n}\n')
    problems = coverage_problems(tree, load())
    assert any(
        "provider_name exists in code but the manifest says planned" in p for p in problems
    ), problems


def test_coverage_bites_on_a_phantom_manifest_entry():
    manifest = load()
    manifest["variables"]["stacks/10-access"].append(
        {**manifest["variables"]["stacks/10-access"][0], "name": "phantom"}
    )
    problems = coverage_problems(ROOT, manifest)
    assert any("phantom" in p and "no such variable" in p for p in problems), problems


def test_coverage_refuses_a_shape_it_does_not_understand(tree):
    (tree / "modules" / "vpc" / "weird.tf").write_text(
        'variable "odd" {\n  type    = string\n  default = <<EOT\nhi\nEOT\n}\n'
    )
    problems = coverage_problems(tree, load())
    assert any("modules/vpc" in p and "cannot read variables" in p for p in problems), (
        problems
    )


# --- the HCL reader fails closed -------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        'variable "a" {\n  default = "x"\n}\n',  # no type
        'variable "a" {\n  type = string\n  bogus = 1\n}\n',  # unknown attribute
        'variable "a" {\n  type = string\n  type = string\n}\n',  # repeated attribute
        'variable "a" {\n  type = string\n  default = "${var.x}"\n}\n',  # template
        'variable "a" {\n  type = string\n  default = <<EOT\nx\nEOT\n}\n',  # heredoc
        'variable "a" {\n  type = string\n  default = foo(1)\n}\n',  # not a literal
        'variable "a" {\n  type = string\n',  # unbalanced
        "variable {\n  type = string\n}\n",  # no label
        'variable "a b" {\n  type = string\n}\n',  # bad label
        'variable "a" "b" {\n  type = string\n}\n',  # two labels
        'variable "a" {\n  type = string\n  other {\n  }\n}\n',  # unknown block
        'variable "a" {\n  type = string\n  sensitive = var.x\n}\n',  # not a bool
        "x = 1\n",  # top-level attribute
        'variable "a" {\n  type = string\n  default = "unterminated\n}\n',
    ],
)
def test_the_reader_refuses_what_it_does_not_understand(text):
    with pytest.raises(hcl_variables.HclError):
        hcl_variables.parse_variables(text)


def test_the_reader_reads_the_shapes_in_use():
    text = """
# comment
variable "a" {
  type        = list(object({
    protocol   = string
    port_range = string
  }))
  default     = []
  description = "has \\"quotes\\" and a # hash"
  sensitive   = true
  validation {
    condition     = alltrue([for r in var.a : contains(["tcp", "udp"], r.protocol)])
    error_message = "x ${not here} is fine inside a validation? no"
  }
}
resource "x" "y" {
  name = "cah-${var.region}"
}
"""
    # The ${...} inside a variable's validation string is refused (fail closed).
    with pytest.raises(hcl_variables.HclError):
        hcl_variables.parse_variables(text)
    text = text.replace("${not here}", "braces")
    (var,) = hcl_variables.parse_variables(text)
    assert var.name == "a"
    assert var.type == "list(object({protocol=string,port_range=string}))"
    assert var.has_default and var.default == []
    assert var.sensitive and var.validations == 1


def test_a_duplicate_variable_in_one_directory_is_refused(tmp_path):
    (tmp_path / "a.tf").write_text('variable "x" {\n  type = string\n}\n')
    (tmp_path / "b.tf").write_text('variable "x" {\n  type = string\n}\n')
    with pytest.raises(hcl_variables.HclError):
        hcl_variables.variables_in_dir(tmp_path)


# --- the other sections ------------------------------------------------------


def test_manifest_pointers_resolve_and_match():
    for e in load()["manifests"]:
        node = json.loads((ROOT / e["file"]).read_text())
        for part in e["pointer"].strip("/").split("/"):
            node = node[int(part)] if isinstance(node, list) else node[part]
        assert node == e["current"], (
            f"{e['name']}: {e['file']}{e['pointer']} is {node!r}"
        )


def test_hardcoded_literals_are_still_in_the_code():
    for e in load()["hardcoded"]:
        text = (ROOT / e["file"]).read_text()
        assert e["literal"] in text, f"{e['name']}: literal not found in {e['file']}"


def test_external_pointer_files_exist():
    for e in load()["external"]:
        if "pointer_file" in e:
            assert (ROOT / e["pointer_file"]).is_file(), e["name"]


def doppler_names_in_use() -> set[str]:
    config = yaml.safe_load((ROOT / ".spacelift" / "config.yml").read_text())
    names: set[str] = set()
    for stack in config["stacks"].values():
        for hook in stack.values():
            for line in hook:
                if "cah_doppler_env" not in line:
                    continue
                for word in line.split("cah_doppler_env", 1)[1].split():
                    names.add(word.split("=", 1)[1] if "=" in word else word)
    return names


def test_every_doppler_name_in_the_hook_config_is_listed():
    listed = {e["name"] for e in load()["secrets"]}
    used = doppler_names_in_use()
    assert used, "no Doppler names found in .spacelift/config.yml"
    assert used <= listed, sorted(used - listed)


def test_every_exists_secret_is_used_somewhere():
    used = doppler_names_in_use() | {
        "DOPPLER_TOKEN",
        "DOPPLER_PROJECT",
        "DOPPLER_CONFIG",
    }
    for e in load()["secrets"]:
        if e["status"] == "exists":
            assert e["name"] in used, (
                f"{e['name']} is listed as existing but nothing uses it"
            )


def test_no_secret_has_a_value():
    for e in load()["secrets"]:
        assert set(e) == SECRET_FIELDS, (
            f"{e['name']}: unexpected keys {sorted(set(e) ^ SECRET_FIELDS)}"
        )
        assert e["class"] in ("secret", "private")
        assert isinstance(e["used_by"], list)
    for place, entries in load()["variables"].items():
        for e in entries:
            if e["sensitivity"] == "secret":
                raise AssertionError(
                    f"{place}.{e['name']}: a secret must not be a variable entry"
                )


# --- examples ----------------------------------------------------------------


def address_ok(text: str) -> bool:
    ip = ipaddress.ip_address(text)
    return any(ip in n for n in DOC_NETS + PRIVATE_NETS)


def example_problems(manifest: dict) -> list[str]:
    problems: list[str] = []

    def scan(where: str, value: object) -> None:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        text = str(value)
        for m in IPV4_RE.finditer(text):
            try:
                ok = address_ok(m.group(1))
            except ValueError:
                ok = True  # not an address (a version number or an id)
            if not ok:
                problems.append(
                    f"{where}: {m.group(1)} is outside the documentation and private ranges"
                )
        for m in HOST_RE.finditer(text):
            host = m.group(1)
            if host.lower().endswith(FILE_SUFFIXES) or HOST_OK.search(host):
                continue
            problems.append(
                f"{where}: host name {host} is not an example.com/net/org name"
            )

    for place, entries in manifest["variables"].items():
        for e in entries:
            scan(f"{place}.{e['name']}.example", e["example"])
            if "default" in e:
                scan(f"{place}.{e['name']}.default", e["default"])
    for key in ("manifests", "hardcoded"):
        for e in manifest[key]:
            scan(f"{key}.{e['name']}.example", e["example"])
    return problems


def test_examples_use_documentation_and_private_ranges_only():
    assert example_problems(load()) == []


def test_the_example_check_bites():
    manifest = load()
    manifest["variables"]["stacks/10-access"][0]["example"] = "8.8.8.8"
    manifest["variables"]["stacks/10-access"][1]["example"] = "db.corp-real.com"
    problems = "\n".join(example_problems(manifest))
    assert "8.8.8.8" in problems
    assert "corp-real.com" in problems


def test_the_planned_logging_example_uses_a_documentation_range():
    entry = next(
        e
        for e in load()["variables"]["stacks/20-telemetry"]
        if e["name"] == "logging_servers"
    )
    ips = IPV4_RE.findall(entry["example"])
    assert ips and all(ipaddress.ip_address(i) in DOC_NETS[0] for i in ips)


# --- generated page ----------------------------------------------------------


def test_the_generated_page_is_current():
    page = ROOT / "docs" / "wiki" / "Settings-Reference.md"
    assert page.read_text(encoding="utf-8") == gen_settings_doc.render(load())


def run_gen(*args: str, root: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-I", str(ROOT / "scripts" / "gen_settings_doc.py"), *args]
    if root is not None:
        cmd += ["--root", str(root)]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_check_passes_on_the_committed_page():
    result = run_gen("--check")
    assert result.returncode == 0, result.stderr


def test_check_fails_when_the_page_is_stale(tmp_path):
    (tmp_path / "docs" / "wiki").mkdir(parents=True)
    shutil.copy(MANIFEST, tmp_path / "docs" / "settings.json")
    assert run_gen(root=tmp_path).returncode == 0
    assert run_gen("--check", root=tmp_path).returncode == 0
    page = tmp_path / "docs" / "wiki" / "Settings-Reference.md"
    page.write_text(page.read_text() + "\nhand edit\n")
    stale = run_gen("--check", root=tmp_path)
    assert stale.returncode == 1
    assert "out of date" in stale.stderr
    page.unlink()
    assert run_gen("--check", root=tmp_path).returncode == 1


def test_check_fails_when_the_manifest_changes(tmp_path):
    (tmp_path / "docs" / "wiki").mkdir(parents=True)
    manifest = load()
    (tmp_path / "docs" / "settings.json").write_text(json.dumps(manifest))
    assert run_gen(root=tmp_path).returncode == 0
    manifest["variables"]["stacks/00-foundation"][0]["example"] = "nyc3"
    (tmp_path / "docs" / "settings.json").write_text(json.dumps(manifest))
    assert run_gen("--check", root=tmp_path).returncode == 1


def test_a_missing_manifest_is_an_error(tmp_path):
    assert run_gen("--check", root=tmp_path).returncode != 0


# --- .gitignore ----------------------------------------------------------------

MUST_BE_IGNORED = (
    "foo.tfvars",
    "terraform.tfvars",
    "foo.auto.tfvars",
    "foo.tfvars.json",
    "foo.auto.tfvars.json",
    "plan.tfplan",
    "tfplan",
    "stacks/10-access/prod.auto.tfvars.json",
)
MUST_NOT_BE_IGNORED = (
    "terraform.tfvars.example",
    "stacks/10-access/terraform.tfvars.example",
    "access.tftest.hcl",
    "variables.tf",
)


def gitignore_failures(gitignore_text: str, tmp: Path) -> list[str]:
    """Names that are wrongly ignored or wrongly not ignored under this text."""
    subprocess.run(["git", "init", "-q", str(tmp)], check=True)
    (tmp / ".gitignore").write_text(gitignore_text)
    failures = []
    for name in MUST_BE_IGNORED + MUST_NOT_BE_IGNORED:
        ignored = subprocess.run(
            ["git", "-C", str(tmp), "check-ignore", "-q", "--no-index", name],
            check=False,
        ).returncode
        if ignored not in (0, 1):
            raise AssertionError(f"git check-ignore failed for {name}")
        if (ignored == 0) != (name in MUST_BE_IGNORED):
            failures.append(name)
    return failures


def test_gitignore_ignores_value_files_and_keeps_the_example(tmp_path):
    assert gitignore_failures((ROOT / ".gitignore").read_text(), tmp_path) == []


def test_the_old_gitignore_fails_the_same_test(tmp_path):
    failures = gitignore_failures(OLD_GITIGNORE, tmp_path)
    assert {"foo.tfvars.json", "foo.auto.tfvars.json", "plan.tfplan"} <= set(failures)
    # What the old text already did right stays right.
    assert "foo.tfvars" not in failures
    assert "terraform.tfvars.example" not in failures


def test_an_example_value_file_can_be_added_to_git(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text((ROOT / ".gitignore").read_text())
    (tmp_path / "terraform.tfvars.example").write_text("# example\n")
    (tmp_path / "terraform.tfvars").write_text("secret = 1\n")
    add = subprocess.run(
        ["git", "-C", str(tmp_path), "add", "--dry-run", "."],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "terraform.tfvars.example" in add.stdout
    assert "'terraform.tfvars'" not in add.stdout


# --- literal values: lists, objects, assignments --------------------------------


def test_the_reader_reads_list_and_object_defaults():
    text = """
variable "m" {
  type = map(string)
  default = {
    a = "04:00" # a comment after a value
    "b" = "05:00",
  }
}
variable "l" {
  type    = list(string)
  default = ["x", "y", ]
}
variable "n" {
  type    = list(object({ k = number }))
  default = [{ k = 1 }, { k = 2.5 }]
}
"""
    found = {v.name: v.default for v in hcl_variables.parse_variables(text)}
    assert found == {
        "m": {"a": "04:00", "b": "05:00"},
        "l": ["x", "y"],
        "n": [{"k": 1}, {"k": 2.5}],
    }


@pytest.mark.parametrize(
    "default",
    [
        '{ a = "x", a = "y" }',  # repeated key
        '{ a = "x" b = "y" }',  # no separator on one line
        '["x" "y"]',  # no comma
        "{ a = var.x }",  # not a literal
        "[1, foo]",
        "10.78.0.0",  # an unquoted address is not a number
        "truely",
        "[[[[[[[[[[1]]]]]]]]]]",  # nested too deeply
        '{ a = "x"',  # unbalanced
    ],
)
def test_the_reader_refuses_a_default_it_does_not_understand(default):
    text = f'variable "a" {{\n  type    = string\n  default = {default}\n}}\n'
    with pytest.raises(hcl_variables.HclError):
        hcl_variables.parse_variables(text)


def test_parse_assignments_reads_a_value_file():
    text = (
        '# c\nregion = "tor1" # why\nlist = ["a",\n  "b"]\n'
        'map = { a = "1", b = "2" }\nflag = true\nnum = 3\nnone = null\n'
    )
    assert hcl_variables.parse_assignments(text) == {
        "region": "tor1",
        "list": ["a", "b"],
        "map": {"a": "1", "b": "2"},
        "flag": True,
        "num": 3,
        "none": None,
    }
