"""Reserved IP rules of the cost gate (edge DMZ design, section 5.6 items 1 and 3).

A reserved IP is free while assigned and $5.00 a month when not, so the gate
allows the type only in the files approved.json names and only paired with one
assignment per IP. The manifest has no reserved_ip kind yet, so a stack cannot
cost one: that stays a fail-closed "no price model" until the follow-up lands.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cost_check
from test_cost_check import droplet, make_repo

IP = 'resource "digitalocean_reserved_ip" "a" {\n  region = "tor1"\n}\n'
DROPLET = 'resource "digitalocean_droplet" "d" {}\n'
GOOD_ASSIGN = (
    'resource "digitalocean_reserved_ip_assignment" "a" {\n'
    "  ip_address = digitalocean_reserved_ip.a.ip_address\n"
    "  droplet_id = digitalocean_droplet.d.id\n}\n"
)
ALLOWED = {
    "digitalocean_droplet": ["modules/ok/main.tf"],
    "digitalocean_reserved_ip": ["modules/ok/main.tf"],
}


def repo(tmp_path, text, **kw):
    return make_repo(tmp_path, [droplet()], tf_files={"modules/ok/main.tf": text}, **kw)


def test_the_assignment_is_free_and_the_reserved_ip_is_a_costed_type():
    assert "digitalocean_reserved_ip_assignment" in cost_check.FREE_TYPES["digitalocean"]
    assert "digitalocean_reserved_ip" not in cost_check.FREE_TYPES["digitalocean"]
    assert "digitalocean_reserved_ip" in cost_check.COSTED_TYPES["digitalocean"]


def test_a_reserved_ip_is_refused_outside_its_allowed_file(tmp_path):
    root = make_repo(
        tmp_path,
        [droplet()],
        tf_files={"modules/ok/main.tf": DROPLET, "stacks/10-access/ip.tf": IP},
    )
    found = cost_check.uncosted_sources(root, ALLOWED)
    assert found == ["stacks/10-access/ip.tf: digitalocean_reserved_ip"]


def test_a_reserved_ip_is_allowed_in_the_named_file(tmp_path):
    root = repo(tmp_path, DROPLET + IP + GOOD_ASSIGN)
    assert cost_check.uncosted_sources(root, ALLOWED) == []
    assert cost_check.reserved_ip_problems(root) == []


def test_a_reserved_ip_with_no_assignment_fails(tmp_path):
    problems = cost_check.reserved_ip_problems(repo(tmp_path, DROPLET + IP))
    assert any("1 digitalocean_reserved_ip block(s) but 0" in p for p in problems)


def test_an_assignment_with_no_reserved_ip_fails(tmp_path):
    problems = cost_check.reserved_ip_problems(repo(tmp_path, DROPLET + GOOD_ASSIGN))
    assert any("0 digitalocean_reserved_ip block(s) but 1" in p for p in problems)


def test_two_assignments_of_one_ip_fail(tmp_path):
    second = GOOD_ASSIGN.replace('"a"', '"b"')
    problems = cost_check.reserved_ip_problems(repo(tmp_path, DROPLET + IP + GOOD_ASSIGN + second))
    assert any("block(s) but 2" in p for p in problems)
    assert any("assigned more than once" in p for p in problems)


@pytest.mark.parametrize(
    "ip_expr",
    [
        '"203.0.113.10"',
        "digitalocean_reserved_ip.missing.ip_address",
        "lower(digitalocean_reserved_ip.a.ip_address)",
        "var.address",
    ],
)
def test_an_ip_address_that_is_not_a_plain_reference_to_a_reserved_ip_fails(tmp_path, ip_expr):
    assign = GOOD_ASSIGN.replace("digitalocean_reserved_ip.a.ip_address", ip_expr)
    problems = cost_check.reserved_ip_problems(repo(tmp_path, DROPLET + IP + assign))
    assert any("plain reference to a digitalocean_reserved_ip" in p for p in problems)


@pytest.mark.parametrize("droplet_expr", ["12345", "var.droplet_id", "module.x.id", "null"])
def test_a_droplet_id_that_is_not_a_plain_droplet_reference_fails(tmp_path, droplet_expr):
    assign = GOOD_ASSIGN.replace("digitalocean_droplet.d.id", droplet_expr)
    problems = cost_check.reserved_ip_problems(repo(tmp_path, DROPLET + IP + assign))
    assert any("plain reference to a droplet" in p for p in problems)


def test_count_on_a_reserved_ip_is_refused(tmp_path):
    root = repo(tmp_path, DROPLET + IP.replace("{\n", "{\n  count = 1\n", 1) + GOOD_ASSIGN)
    problems = cost_check.block_problems(root)
    assert any("digitalocean_reserved_ip" in p and "count" in p for p in problems)


def test_the_manifest_cannot_cost_a_reserved_ip_yet(tmp_path):
    root = make_repo(tmp_path, [{"name": "edge-ip", "kind": "reserved_ip", "assigned_to": "x"}])
    with pytest.raises(ValueError, match="no price model"):
        cost_check.total_cost(root, cost_check.load_prices(root, "digitalocean"))


def test_the_real_repository_passes_the_new_rule():
    root = Path(__file__).resolve().parent.parent
    assert cost_check.reserved_ip_problems(root) == []
