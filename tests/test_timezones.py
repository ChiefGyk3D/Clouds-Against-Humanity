"""The committed zone list behind the bootstrap module's timezone check."""

import re
from pathlib import Path

LIST = Path(__file__).resolve().parents[1] / "modules" / "twingate-bootstrap" / "timezones.txt"
SHAPE = re.compile(r"^(UTC|[A-Za-z_]+(/[A-Za-z0-9_+-]+){1,2})$")


def names():
    return LIST.read_text(encoding="utf-8").splitlines()


def test_the_list_is_sorted_unique_and_has_the_default():
    n = names()
    assert n == sorted(set(n))
    assert "America/New_York" in n and "UTC" in n
    assert len(n) > 300  # guards against passing on an empty or truncated file


def test_no_name_can_carry_a_line_break_or_yaml_character():
    assert "\r" not in LIST.read_text(encoding="utf-8")
    assert all(re.fullmatch(r"[A-Za-z0-9_+/-]+", x) for x in names())


def test_the_shape_check_still_applies_on_top_of_the_list():
    # Names without an Area/ prefix (EST, Zulu) are listed but rejected by the shape check.
    assert any(not SHAPE.match(x) for x in names())
    assert sum(1 for x in names() if SHAPE.match(x)) > 300
