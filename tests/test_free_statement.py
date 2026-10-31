"""The maintainer's "free and not for sale" statement is on the README and both wiki pages.

The support links in the statement must be links the README already carries,
so a page cannot quietly point readers at a donation address nobody reviewed.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
WHY = ROOT / "docs" / "wiki" / "Why-This-Exists.md"
HOME = ROOT / "docs" / "wiki" / "Home.md"

HEADINGS = {
    README: "## Free, and not for sale",
    WHY: "## Why this is free and not for sale",
    HOME: "## Why this is free and not for sale",
}
# Phrases every copy must keep: the meaning, not the whole wording.
COMMON = ["System76 Pangolin", "knowledge is power", "gatekeeping", "90K in 90 days", "under no obligation", "share it"]
# Only the long version carries the school and certificate claims.
LONG_ONLY = ["CISSP", "about twelve years", "WGU", "not an indictment of WGU", "college as a whole", "four-year degree"]

URL = re.compile(r"\]\((https?://[^)\s]+)\)")


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    rest = text[start + len(heading):]
    end = re.search(r"^## ", rest, re.MULTILINE)
    return heading + (rest[: end.start()] if end else rest)


def foreign_support_links(body: str, readme_text: str) -> list[str]:
    """External links in body that the README does not already contain."""
    return [u for u in URL.findall(body) if u not in readme_text]


def test_each_page_carries_the_statement():
    for path, heading in HEADINGS.items():
        text = path.read_text()
        assert heading in text, f"{path.name}: missing {heading!r}"
        body = section(text, heading)
        missing = [p for p in COMMON if p not in body]
        assert not missing, f"{path.name}: statement lost {missing}"
        assert "—" not in body and "–" not in body, f"{path.name}: dash in statement"


def test_long_version_keeps_the_school_and_cert_claims():
    body = section(WHY.read_text(), HEADINGS[WHY])
    missing = [p for p in LONG_ONLY if p not in body]
    assert not missing, f"long version lost {missing}"


def test_support_links_are_already_in_the_readme():
    readme_text = README.read_text()
    for path, heading in HEADINGS.items():
        body = section(path.read_text(), heading)
        own_wiki = "github.com/ChiefGyk3D/Clouds-Against-Humanity/wiki/"
        bad = [u for u in foreign_support_links(body, readme_text) if own_wiki not in u]
        assert not bad, f"{path.name}: links not in README.md: {bad}"
    readme_body = section(readme_text, HEADINGS[README])
    for url in ("https://patreon.com/chiefgyk3d", "https://streamelements.com/chiefgyk3d/tip"):
        assert url in readme_body and readme_text.count(url) >= 2


def test_guard_bites_on_a_link_the_readme_lacks():
    body = "[tip](https://example.invalid/tip) and [Patreon](https://patreon.com/chiefgyk3d)"
    assert foreign_support_links(body, README.read_text()) == ["https://example.invalid/tip"]
    assert section("## A\nx\n## B\ny", "## A") == "## A\nx\n"
