# SPDX-License-Identifier: Apache-2.0
"""The cost gate refuses provisioner blocks and external data sources.

A provisioner (local-exec, remote-exec, file) runs commands at apply time and
an external data source runs a program at plan time. The gate cannot cost or
read either, so the source scan fails on them whatever resource type holds them.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cost_check
from test_cost_check import droplet, make_repo

OK_DROPLET = {"modules/ok/main.tf": 'resource "digitalocean_droplet" "a" {}\n'}


def problems_for(tmp_path, files):
    root = make_repo(tmp_path, [droplet()], tf_files={**OK_DROPLET, **files})
    approved = json.loads((root / "docs/stages/approved.json").read_text())
    problems, _ = cost_check.gate_problems(root, approved)
    return problems


def provisioner_problems(problems):
    return [p for p in problems if "provisioner" in p or "external data" in p]


NULL_LOCAL_EXEC = (
    'resource "null_resource" "x" {\n'
    '  provisioner "local-exec" {\n    command = "true"\n  }\n}\n'
)


def test_a_null_resource_with_a_local_exec_provisioner_is_refused(tmp_path):
    problems = problems_for(tmp_path, {"stacks/10-access/x.tf": NULL_LOCAL_EXEC})
    found = provisioner_problems(problems)
    assert found and "stacks/10-access/x.tf:2" in found[0]


def test_the_same_file_without_the_provisioner_is_clean(tmp_path):
    clean = 'resource "null_resource" "x" {\n  triggers = {}\n}\n'
    assert problems_for(tmp_path, {"stacks/10-access/x.tf": clean}) == []


@pytest.mark.parametrize(
    "text",
    [
        'resource "null_resource" "x" {\n  provisioner "remote-exec" {\n    inline = []\n  }\n}\n',
        'resource "terraform_data" "x" {\n  provisioner "file" {\n    source = "a"\n  }\n}\n',
        'resource "null_resource" "x" { provisioner "local-exec" { command = "true" } }\n',
        'resource "null_resource" "x" {\n  provisioner local-exec {\n  }\n}\n',
        'resource "digitalocean_tag" "x" {\n  provisioner "local-exec" {\n  }\n}\n',
        'resource "null_resource" "x" {\n  provisioner "local-exec" {\n  when = destroy\n  }\n}\n',
    ],
)
def test_every_provisioner_form_is_refused(tmp_path, text):
    problems = problems_for(tmp_path, {"stacks/10-access/x.tf": text})
    assert provisioner_problems(problems)


def test_a_provisioner_in_a_module_directory_is_refused(tmp_path):
    problems = problems_for(tmp_path, {"modules/other/main.tf": NULL_LOCAL_EXEC})
    assert provisioner_problems(problems)


def test_a_provisioner_in_a_tofu_file_is_refused(tmp_path):
    problems = problems_for(tmp_path, {"stacks/10-access/x.tofu": NULL_LOCAL_EXEC})
    assert provisioner_problems(problems)


@pytest.mark.parametrize(
    "text",
    [
        'data "external" "x" {\n  program = ["true"]\n}\n',
        'data external x {\n  program = ["true"]\n}\n',
        'data "external" "x" { program = ["true"] }\n',
    ],
)
def test_an_external_data_source_is_refused(tmp_path, text):
    problems = problems_for(tmp_path, {"stacks/10-access/x.tf": text})
    found = provisioner_problems(problems)
    assert found and "external data source" in found[0]


def test_other_data_sources_are_not_flagged(tmp_path):
    text = 'data "digitalocean_image" "x" {\n  slug = "a"\n}\n'
    assert provisioner_problems(problems_for(tmp_path, {"stacks/10-access/x.tf": text})) == []


@pytest.mark.parametrize(
    "text",
    [
        '# provisioner "local-exec" {\n',
        '/* provisioner "local-exec" {\n} */\n',
        'locals {\n  note = "provisioner \\"local-exec\\" { }"\n}\n',
        'locals {\n  note = "data external x {"\n}\n',
        'locals {\n  provisioner = "x"\n  data = "external"\n}\n',
        'locals {\n  doc = <<EOT\nprovisioner "local-exec" {\nEOT\n}\n',
    ],
)
def test_the_words_in_comments_strings_and_attributes_are_not_flagged(tmp_path, text):
    assert provisioner_problems(problems_for(tmp_path, {"stacks/10-access/x.tf": text})) == []


@pytest.mark.parametrize(
    "text",
    [
        'resource "null_resource" "x" {\n  provisioner"local-exec"{\n  }\n}\n',
        'resource "null_resource" "x" {\n  provisioner"local-exec" {\n  }\n}\n',
        'resource "null_resource" "x" {\n  provisioner "local-exec"{\n  }\n}\n',
        'resource "null_resource" "x" {\n  provisioner\t"local-exec"\t{\n  }\n}\n',
        'resource "null_resource" "x" {\n  provisioner  \t "local-exec"   {\n  }\n}\n',
        'resource "null_resource" "x" {\n  provisioner{\n  }\n}\n',
        'resource "null_resource" "x" {provisioner"file"{}}\n',
        'resource "null_resource" "x" {\r\n  provisioner "local-exec" {\r\n  }\r\n}\r\n',
        'resource "null_resource" "x" {\n  /* c */ provisioner "local-exec" {\n  }\n}\n',
        'resource "null_resource" "x" {\n  provisioner "local-exec" { # c\n  }\n}\n',
        'resource "null_resource" "x" {\n  provisioner /* c */ "local-exec" {\n  }\n}\n',
    ],
)
def test_odd_spacing_does_not_hide_a_provisioner(tmp_path, text):
    assert provisioner_problems(problems_for(tmp_path, {"stacks/10-access/x.tf": text}))


@pytest.mark.parametrize(
    "text",
    [
        'data"external""x"{\n}\n',
        'data"external" "x"{\n}\n',
        'data "external""x" {\n}\n',
        'data\t"external"\t"x"\t{\n}\n',
        'data "external"{\n}\n',
        'data external{\n}\n',
        'data external"x"{\n}\n',
        'data"external"x{\n}\n',
        'data "ext\\u0065rnal" "x" {\n}\n',
        'data /* c */ "external" "x" {\n}\n',
    ],
)
def test_odd_spacing_does_not_hide_an_external_data_source(tmp_path, text):
    found = provisioner_problems(problems_for(tmp_path, {"stacks/10-access/x.tf": text}))
    assert found and "external data source" in found[0]


@pytest.mark.parametrize(
    "name", ["stacks/10-access/x.tf.json", "stacks/10-access/x.tofu.json", "modules/other/x.tf.json", "labs/vm/x.tf.json"]
)
def test_json_configuration_files_are_refused_outright(tmp_path, name):
    body = '{"resource": {"null_resource": {"x": {"provisioner": [{"local-exec": {"command": "true"}}]}}}}'
    problems = problems_for(tmp_path, {name: body})
    assert any(name in p and "is refused" in p for p in problems), problems


def test_a_provisioner_in_a_tofu_override_file_is_refused(tmp_path):
    problems = problems_for(tmp_path, {"stacks/10-access/x_override.tofu": NULL_LOCAL_EXEC})
    assert provisioner_problems(problems)


@pytest.mark.parametrize(
    "text",
    [
        'locals {\n  doc = <<-EOT\n    provisioner"local-exec"{\n    data"external""x"{\n  EOT\n}\n',
        '// provisioner"local-exec"{\n',
        '# data"external""x"{\n',
        'locals {\n  s = "provisioner\\"local-exec\\"{"\n}\n',
        'locals {\n  s = "${provisioner}"\n}\n',
        'locals {\n  provisioner = {}\n  external = 1\n}\n',
        'data "digitalocean_image" "external" {\n  slug = "a"\n}\n',
        'data "http" "external" {\n}\n',
    ],
)
def test_odd_spacing_in_strings_comments_heredocs_and_other_words_is_not_flagged(tmp_path, text):
    assert provisioner_problems(problems_for(tmp_path, {"stacks/10-access/x.tf": text})) == []


def test_labs_are_exempt_like_the_other_cost_rules(tmp_path):
    problems = problems_for(tmp_path, {"labs/vm/main.tf": NULL_LOCAL_EXEC})
    assert provisioner_problems(problems) == []
