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


# Every run gets this environment, not the caller's: a workflow in a fork sets
# GITHUB_REPOSITORY, and the raw image URL depends on it.
CLEAN_ENV = {"PATH": "/usr/bin:/bin"}


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=CLEAN_ENV,
    )


@pytest.fixture(scope="module")
def tree(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("wiki-out")
    result = run(str(out))
    assert result.returncode == 0, result.stderr
    return out


def test_every_page_is_written(tree):
    assert sorted(p.name for p in tree.glob("*.md")) == sorted(
        p.name for p in WIKI.glob("*.md")
    )


def test_relative_page_links_lose_their_md_suffix(tree):
    for page in tree.glob("*.md"):
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
        ["bash", str(copy), str(out)],
        capture_output=True,
        text=True,
        check=False,
        env=CLEAN_ENV,
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
        env=CLEAN_ENV,
    )
    assert result.returncode == 1
    assert "no pages" in result.stderr


def test_absolute_links_are_left_alone(tree):
    for page in WIKI.glob("*.md"):
        for url in re.findall(r"\]\((https?://[^)]+)\)", page.read_text()):
            assert url in (tree / page.name).read_text(), (
                f"{page.name}: absolute link {url} was changed"
            )


def test_the_complete_output_set_is_pages_plus_images(tree):
    expected = {p.name for p in WIKI.glob("*.md")} | {p.name for p in (WIKI / "images").iterdir()}
    assert {p.name for p in tree.iterdir()} == expected
    assert not (tree / "images").exists()


def test_images_are_copied_flat(tree):
    images = sorted((WIKI / "images").iterdir())
    assert images, "no images examined"
    for img in images:
        assert (tree / img.name).read_bytes() == img.read_bytes()


def scratch(tmp_path, pages, images=None, env=None, out="out", prepare=None):
    """A scratch copy of the script with its own docs/wiki; returns (result, out path)."""
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    wiki = tmp_path / "docs" / "wiki"
    (wiki / "images").mkdir(parents=True, exist_ok=True)
    copy = tmp_path / "scripts" / "gen-wiki.sh"
    copy.write_text(SCRIPT.read_text())
    for name, text in pages.items():
        (wiki / name).write_text(text)
    for name, data in (images or {}).items():
        (wiki / "images" / name).write_bytes(data)
    if prepare:
        prepare(tmp_path)
    target = tmp_path / out
    result = subprocess.run(
        ["bash", str(copy), str(target)],
        capture_output=True,
        text=True,
        check=False,
        env={**CLEAN_ENV, **(env or {})},
    )
    return result, target


@pytest.mark.parametrize(
    "value",
    [
        "x/\\1)#g\ne touch PWNED\n#",
        "a/b\nc/d",
        "a/b c",
        "a/b#c",
        "a/b/c",
        "/b",
        "a/",
        "noslash",
        "../b",
        "a/..",
        "a/b$(touch PWNED)",
        "a/b`touch PWNED`",
        "a/b;touch PWNED",
        "a/b&c",
        "a/b\\c",
    ],
)
@pytest.mark.parametrize("variable", ["GITHUB_REPOSITORY", "WIKI_REPO"])
def test_a_hostile_repository_value_is_refused_before_anything_runs(tmp_path, variable, value):
    pages = {"Page.md": "![alt text here](images/a.png)\n"}
    result, out = scratch(tmp_path, pages, {"a.png": b"x"}, env={variable: value})
    assert result.returncode == 2, result.stderr
    assert "owner/repository" in result.stderr
    assert not out.exists()
    assert not list(tmp_path.rglob("PWNED"))


def test_wiki_repo_is_the_fallback_and_github_repository_wins(tmp_path):
    pages = {"Page.md": "![alt text here](images/a.png)\n"}
    result, out = scratch(tmp_path / "a", pages, {"a.png": b"x"}, env={"WIKI_REPO": "fall/back"})
    assert result.returncode == 0, result.stderr
    assert "wiki/fall/back/a.png)" in (out / "Page.md").read_text()
    both = {"WIKI_REPO": "fall/back", "GITHUB_REPOSITORY": "actions/value"}
    result, out = scratch(tmp_path / "b", pages, {"a.png": b"x"}, env=both)
    assert "wiki/actions/value/a.png)" in (out / "Page.md").read_text()


def test_a_valid_but_unusual_repository_name_is_accepted(tmp_path):
    pages = {"Page.md": "![alt text here](images/a.png)\n"}
    result, out = scratch(tmp_path, pages, {"a.png": b"x"}, env={"GITHUB_REPOSITORY": "Some-Org_1/repo.name-2"})
    assert result.returncode == 0, result.stderr
    assert "wiki/Some-Org_1/repo.name-2/a.png)" in (out / "Page.md").read_text()


def test_a_symlinked_image_is_refused_and_nothing_is_published(tmp_path):
    secret = tmp_path / "private.png"
    secret.write_bytes(b"PRIVATE")

    def link(root):
        (root / "docs" / "wiki" / "images" / "leak.png").symlink_to(secret)

    result, out = scratch(tmp_path, {"Page.md": "![a private diagram](images/leak.png)\n"}, prepare=link)
    assert result.returncode == 1
    assert "symlink" in result.stderr
    assert not out.exists()


def test_a_symlinked_images_directory_or_page_is_refused(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.png").write_bytes(b"x")

    def link_dir(root):
        import shutil

        shutil.rmtree(root / "docs" / "wiki" / "images")
        (root / "docs" / "wiki" / "images").symlink_to(outside)

    result, out = scratch(tmp_path / "a", {"Page.md": "text\n"}, prepare=link_dir)
    assert result.returncode == 1 and "symlink" in result.stderr and not out.exists()

    def link_page(root):
        (root / "docs" / "wiki" / "Linked.md").symlink_to(outside / "x.png")

    result, out = scratch(tmp_path / "b", {"Page.md": "text\n"}, prepare=link_page)
    assert result.returncode == 1 and "symlink" in result.stderr and not out.exists()


@pytest.mark.parametrize("name", ["photo.jpg", "photo.jpeg", "notes.txt", "A.PNG.bak", ".hidden"])
def test_only_png_files_may_be_in_the_images_directory(tmp_path, name):
    result, out = scratch(tmp_path, {"Page.md": "text\n"}, {name: b"x"})
    assert result.returncode == 1
    assert "only .png" in result.stderr
    assert not out.exists()


def test_a_subdirectory_in_images_is_refused(tmp_path):
    def sub(root):
        (root / "docs" / "wiki" / "images" / "deep").mkdir()

    result, _out = scratch(tmp_path, {"Page.md": "text\n"}, prepare=sub)
    assert result.returncode == 1 and "not a regular file" in result.stderr


def test_a_non_empty_output_directory_is_refused_and_left_alone(tmp_path):
    def stale(root):
        (root / "out").mkdir()
        (root / "out" / "unexpected.bin").write_text("secret")
        (root / "out" / "Deleted-Page.md").write_text("stale")

    result, out = scratch(tmp_path, {"Page.md": "text\n"}, prepare=stale)
    assert result.returncode == 2
    assert "not empty" in result.stderr
    assert sorted(p.name for p in out.iterdir()) == ["Deleted-Page.md", "unexpected.bin"]
    assert (out / "unexpected.bin").read_text() == "secret"


def test_an_empty_existing_output_directory_is_fine_and_a_file_is_not(tmp_path):
    result, out = scratch(tmp_path / "a", {"Page.md": "text\n"}, prepare=lambda r: (r / "out").mkdir())
    assert result.returncode == 0, result.stderr
    assert [p.name for p in out.iterdir()] == ["Page.md"]
    result, _ = scratch(tmp_path / "b", {"Page.md": "text\n"}, prepare=lambda r: (r / "out").write_text("x"))
    assert result.returncode == 2 and "not a plain directory" in result.stderr


def test_image_links_are_rewritten_only_in_prose(tmp_path):
    raw = "https://raw.githubusercontent.com/wiki/o/r/a.png"
    page = (
        "before ![alt text here](images/a.png) after\n"
        "\n"
        "inline `![alt text here](images/a.png)` code and ![alt text here](images/a.png) prose\n"
        "\n"
        "```markdown\n"
        "![alt text here](images/a.png)\n"
        "```\n"
        "\n"
        "~~~\n"
        "![alt text here](images/a.png)\n"
        "~~~\n"
        "\n"
        "    ![alt text here](images/a.png)\n"
        "\n"
        "- list item\n"
        "\n"
        "    ![alt text here](images/a.png)\n"
        "\n"
        "again ![alt text here](images/a.png)\n"
    )
    result, out = scratch(tmp_path, {"Page.md": page}, {"a.png": b"x"}, env={"GITHUB_REPOSITORY": "o/r"})
    assert result.returncode == 0, result.stderr
    lines = (out / "Page.md").read_text().splitlines()
    img = "![alt text here](images/a.png)"
    rewritten = f"![alt text here]({raw})"
    assert lines[0] == f"before {rewritten} after"
    assert lines[2] == f"inline `{img}` code and {rewritten} prose"
    assert lines[5] == img  # inside a backtick fence
    assert lines[9] == img  # inside a tilde fence
    assert lines[12] == f"    {img}"  # indented code block
    assert lines[16] == f"    {rewritten}"  # nested under a list item, so prose
    assert lines[18] == f"again {rewritten}"


def test_image_links_become_raw_wiki_urls(tree):
    page = (tree / "Threat-Dragon-Exercise.md").read_text()
    assert "](images/" not in page
    assert (
        "](https://raw.githubusercontent.com/wiki/ChiefGyk3D/Clouds-Against-Humanity/"
        "threat-dragon-stride-diagram.png)" in page
    )


def test_raw_url_follows_the_repository_in_a_fork(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "docs" / "wiki" / "images").mkdir(parents=True)
    copy = tmp_path / "scripts" / "gen-wiki.sh"
    copy.write_text(SCRIPT.read_text())
    (tmp_path / "docs" / "wiki" / "images" / "a-b.png").write_bytes(b"x")
    (tmp_path / "docs" / "wiki" / "Page.md").write_text(
        "![alt text here](images/a-b.png) ![x](https://example.org/i.png) ![y](images/sub/c.png)\n"
    )
    out = tmp_path / "out"
    result = subprocess.run(
        ["bash", str(copy), str(out)],
        capture_output=True,
        text=True,
        check=False,
        env={**CLEAN_ENV, "GITHUB_REPOSITORY": "someone/their-fork"},
    )
    assert result.returncode == 0, result.stderr
    assert (out / "a-b.png").read_bytes() == b"x"
    assert (out / "Page.md").read_text() == (
        "![alt text here](https://raw.githubusercontent.com/wiki/someone/their-fork/a-b.png)"
        " ![x](https://example.org/i.png) ![y](images/sub/c.png)\n"
    )


def test_no_argument_is_a_usage_error():
    result = run()
    assert result.returncode == 2
    assert "usage" in result.stderr
