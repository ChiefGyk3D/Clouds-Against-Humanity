"""Tests for scripts/gen-wiki.sh, the generate step of the Wiki workflow.

The script copies docs/wiki/ into an output directory and rewrites relative
page links for the flat GitHub wiki. It never pushes; git-your-ship-together's
wiki-publish.yml does that from main only.
"""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "gen-wiki.sh"
WIKI = ROOT / "docs" / "wiki"
RELATIVE_MD_LINK = re.compile(r"\]\([A-Za-z0-9_-]+\.md(#[^)]*)?\)")


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, check=False
    )


@pytest.fixture(scope="module")
def tree(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("wiki-out")
    result = run(str(out))
    assert result.returncode == 0, result.stderr
    return out


def test_every_page_is_written(tree):
    assert sorted(p.name for p in tree.iterdir()) == sorted(
        p.name for p in WIKI.glob("*.md")
    )


def test_relative_page_links_lose_their_md_suffix(tree):
    for page in tree.iterdir():
        assert not RELATIVE_MD_LINK.search(page.read_text()), (
            f"{page.name} still links to a .md page"
        )


def test_home_links_become_wiki_page_names(tree):
    assert "](Twingate.md)" in (WIKI / "Home.md").read_text()
    assert "](Twingate)" in (tree / "Home.md").read_text()


def test_a_link_with_an_anchor_keeps_the_anchor(tmp_path):
    """The script finds docs/wiki from its own location, so a copy in a scratch tree reads that tree."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "docs" / "wiki").mkdir(parents=True)
    copy = tmp_path / "scripts" / "gen-wiki.sh"
    copy.write_text(SCRIPT.read_text())
    (tmp_path / "docs" / "wiki" / "Page.md").write_text(
        "[a](Other.md#some-section) [b](Other.md) [c](https://example.org/x.md)\n"
    )
    out = tmp_path / "out"
    result = subprocess.run(
        ["bash", str(copy), str(out)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert (
        (out / "Page.md").read_text()
        == "[a](Other#some-section) [b](Other) [c](https://example.org/x.md)\n"
    )


def test_an_empty_source_is_refused(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "docs" / "wiki").mkdir(parents=True)
    copy = tmp_path / "scripts" / "gen-wiki.sh"
    copy.write_text(SCRIPT.read_text())
    result = subprocess.run(
        ["bash", str(copy), str(tmp_path / "out")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "no pages" in result.stderr


def test_absolute_links_are_left_alone(tree):
    for page in WIKI.glob("*.md"):
        for url in re.findall(r"\]\((https?://[^)]+)\)", page.read_text()):
            assert url in (tree / page.name).read_text(), (
                f"{page.name}: absolute link {url} was changed"
            )


def test_no_argument_is_a_usage_error():
    result = run()
    assert result.returncode == 2
    assert "usage" in result.stderr
