# SPDX-License-Identifier: Apache-2.0
"""The wiki navigation manifest, Contents page and sidebar (issue #249).

What is proved:
- every wiki page is in docs/wiki/_nav.yaml exactly once, and every entry names a page that
  exists (no orphans, no dead entries, no duplicates);
- Contents.md and _Sidebar.md are exactly what gen_wiki_nav.py renders, so they are
  reproducible and --check passes on the committed files;
- Contents has a link for every page, and the sidebar fits its line budget;
- the manifest keeps its own rules: sorted groups stay sorted, statuses and audiences come
  from the allowed lists, descriptions stay one plain line;
- the checks bite: hostile manifests (duplicate key, orphan, dead entry, bad status, a pipe
  in a description, a stale generated file) are each refused.
"""

import copy
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_wiki_nav as gwn

WIKI = ROOT / "docs" / "wiki"
SIDEBAR_LINE_BUDGET = 230
COLLAPSED_ROW_BUDGET = 45
PAGE_LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")


def manifest() -> dict:
    return gwn.read_manifest(ROOT)


def pages_on_disk() -> set[str]:
    return gwn.wiki_pages(ROOT)


def minimal() -> dict:
    """A small valid manifest and the page set it covers, for the hostile tests."""
    m = {
        "groups": [
            {"id": "start", "title": "Start here", "order": "curated"},
            {"id": "core", "title": "Core path", "order": "curated", "numbered": True, "open": True},
            {"id": "ref", "title": "Reference", "order": "sorted"},
        ],
        "pages": {
            "start": [{"page": "Home", "title": "Home", "audience": "everyone", "desc": "The front door."}],
            "core": [{"page": "One", "title": "One", "audience": "newcomer", "desc": "The first page."}],
            "ref": [
                {"page": "Apple", "title": "Apple", "audience": "everyone", "desc": "A page."},
                {"page": "Berry", "title": "Berry", "audience": "builder", "status": "draft", "desc": "Another page."},
            ],
        },
    }
    return m


MINIMAL_PAGES = {"Home", "One", "Apple", "Berry"}


# -- the committed manifest -----------------------------------------------------------------


def test_the_committed_manifest_is_valid_against_the_pages_on_disk():
    assert gwn.validate(manifest(), pages_on_disk()) == []


def test_every_wiki_page_is_in_the_manifest_exactly_once():
    names = gwn.all_page_names(manifest())
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, f"listed more than once: {dupes}"
    assert not (pages_on_disk() - set(names)), f"orphans: {sorted(pages_on_disk() - set(names))}"


def test_every_manifest_entry_is_a_page_that_exists():
    dead = sorted(set(gwn.all_page_names(manifest())) - pages_on_disk())
    assert not dead, f"dead entries: {dead}"


def test_the_special_pages_are_not_listed():
    assert not set(gwn.all_page_names(manifest())) & gwn.SPECIAL


def test_the_manifest_has_the_themes_the_issue_asks_for():
    titles = " ".join(g["title"].lower() for g in gwn.groups_of(manifest()))
    for theme in (
        "start here", "core path", "os and linux", "networking", "identity and secrets",
        "infrastructure as code", "web hosting", "security tools", "network and host defense",
        "deception and honeypots", "enterprise practice", "data governance", "stage guides",
        "other clouds", "reference", "project process",
    ):
        assert theme in titles, f"no group for {theme!r}"


def test_the_core_path_matches_the_reading_order_table_in_order():
    reading = (WIKI / "Reading-Order.md").read_text()
    section = reading.split("## The core path", 1)[1].split("\n## ", 1)[0]
    in_reading_order = [PAGE_LINK.search(row).group(1) for row in section.splitlines() if re.match(r"\|\s*\d+\s*\|", row)]
    in_manifest = [e["page"] for e in gwn.entries(manifest(), "core")]
    assert in_manifest == in_reading_order


def test_status_markers_are_only_the_three_the_banners_support():
    used = {e["status"] for pages in manifest()["pages"].values() for e in pages if "status" in e}
    assert used <= set(gwn.STATUSES)
    assert used, "expected at least one page with a marker"


def test_pages_that_call_themselves_unverified_drafts_are_marked_draft():
    marked = {e["page"] for pages in manifest()["pages"].values() for e in pages if e.get("status") == "draft"}
    banner = re.compile(r"^> \*\*(Status: )?[Uu]nverified draft", re.MULTILINE)
    banner_pages = {p.stem for p in WIKI.glob("*.md") if banner.search(p.read_text())}
    assert banner_pages <= marked, f"banner says draft but the manifest does not: {sorted(banner_pages - marked)}"


def test_no_em_dashes_or_british_spellings_in_the_manifest():
    text = (WIKI / "_nav.yaml").read_text()
    assert "—" not in text and "–" not in text
    for word in ("defence", "colour", "behaviour", "licence", "analyse", "organise", "centre", "catalogue"):
        assert word not in text.lower(), word


# -- the generated files ---------------------------------------------------------------------


def test_contents_and_sidebar_are_what_the_generator_renders():
    m = manifest()
    assert (WIKI / "Contents.md").read_text() == gwn.render_contents(m)
    assert (WIKI / "_Sidebar.md").read_text() == gwn.render_sidebar(m)


def test_rendering_is_reproducible():
    m = manifest()
    assert gwn.render_contents(m) == gwn.render_contents(copy.deepcopy(m))
    assert gwn.render_sidebar(m) == gwn.render_sidebar(copy.deepcopy(m))


def test_check_passes_on_the_committed_files():
    assert gwn.check(ROOT) == []
    result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "gen_wiki_nav.py"), "--check"], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_contents_links_every_page():
    linked = set(PAGE_LINK.findall((WIKI / "Contents.md").read_text()))
    assert pages_on_disk() - {"Contents"} <= linked
    assert "Contents" in gwn.all_page_names(manifest())


def test_contents_has_one_entry_per_page():
    table_rows = [
        line for line in (WIKI / "Contents.md").read_text().splitlines()
        if line.startswith("| ") and "](" in line and "https://" not in line
    ]
    targets = [PAGE_LINK.search(row).group(1) for row in table_rows]
    assert sorted(targets) == sorted(pages_on_disk())


def test_contents_rows_carry_a_description_and_an_audience():
    for line in (WIKI / "Contents.md").read_text().splitlines():
        if line.startswith("| ["):
            cells = [c.strip() for c in line.strip("|").split("|")]
            assert len(cells) >= 4 and cells[-3] and cells[-2], line


def test_sidebar_stays_inside_its_line_budget():
    lines = (WIKI / "_Sidebar.md").read_text().splitlines()
    assert len(lines) <= SIDEBAR_LINE_BUDGET, f"{len(lines)} lines, budget {SIDEBAR_LINE_BUDGET}"


def test_collapsed_sidebar_fits_one_screen():
    """Rows a reader sees with every group closed: the top row, the open core path, and one summary per group."""
    text = re.sub(r"<!--.*?-->", "", (WIKI / "_Sidebar.md").read_text(), flags=re.DOTALL)
    visible, closed = 0, False
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith("<details>"):
            closed = True
        elif line.startswith(("<details open>", "</details>")):
            closed = False
        elif line.startswith("<summary>") or not closed:
            visible += 1
    assert visible <= COLLAPSED_ROW_BUDGET, f"{visible} rows visible when collapsed, budget {COLLAPSED_ROW_BUDGET}"


def test_only_the_core_path_is_open_by_default():
    text = (WIKI / "_Sidebar.md").read_text()
    assert text.count("<details open>") == 1
    opened = text.split("<details open>", 1)[1].split("</details>", 1)[0]
    assert "Core path" in opened and "Start-Here-If-You-Are-New.md" in opened


def test_sidebar_keeps_the_links_the_other_tests_and_pages_rely_on():
    text = (WIKI / "_Sidebar.md").read_text()
    for page in ("Home", "Contents", "Reading-Order", "Why-This-Exists", "Screenshots-Policy", "Repository-Growth", "Glossary"):
        assert f"({page}.md)" in text, page
    # The outside links are not key pages; they stay one click away on the Contents page (issue #362).
    contents = (WIKI / "Contents.md").read_text()
    assert "docs/stages/00-foundation.md" in contents and "docs/cost.md" in contents


def test_every_group_in_the_sidebar_is_a_details_block_with_a_summary():
    text = (WIKI / "_Sidebar.md").read_text()
    assert text.count("<details") == text.count("</details>") == text.count("<summary>")


def test_home_start_here_reading_order_and_readme_link_to_contents():
    for name in ("Home.md", "Start-Here-If-You-Are-New.md", "Reading-Order.md"):
        assert "(Contents.md)" in (WIKI / name).read_text(), name
    assert "/wiki/Contents)" in (ROOT / "README.md").read_text()


def test_ci_runs_the_check():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "python -I scripts/gen_wiki_nav.py --check" in ci


def test_the_publisher_copies_the_generated_pages_unchanged_in_kind():
    """gen-wiki.sh publishes every docs/wiki/*.md; the manifest is YAML and is not a page."""
    script = (ROOT / "scripts" / "gen-wiki.sh").read_text()
    assert 'for page in "$src"/*.md' in script
    assert not (WIKI / "_nav.yaml").name.endswith(".md")


# -- the collapsed sidebar (issue #362) ----------------------------------------------------------

SIDEBAR_HEADROOM = 40  # lines the committed sidebar must leave under the budget
SIDEBAR_GROUP_LINK = re.compile(r"\]\(Contents\.md#([a-z0-9-]+)\)")
SIDEBAR_ITEM = re.compile(r"^(- |\d+\. )")


def bulk_group(pages: int, **marks) -> dict:
    """A manifest whose 'ref' group has `pages` entries named P00, P01, ... (sorted order = write order)."""
    m = minimal()
    m["pages"]["ref"] = [
        {"page": f"P{i:02d}", "title": f"P{i:02d}", "audience": "everyone", "desc": "A page.", **marks.get(f"P{i:02d}", {})}
        for i in range(pages)
    ]
    return m


def ref_block(sidebar: str) -> str:
    return sidebar.split("<summary><b>Reference</b>", 1)[1].split("</details>", 1)[0]


def test_the_sidebar_leaves_room_for_forty_more_pages_under_the_budget():
    lines = (WIKI / "_Sidebar.md").read_text().splitlines()
    assert len(lines) <= SIDEBAR_LINE_BUDGET - SIDEBAR_HEADROOM, f"{len(lines)} lines"


def test_forty_more_unmarked_pages_do_not_grow_the_committed_sidebar():
    m = manifest()
    before = len(gwn.render_sidebar(m).splitlines())
    m["pages"]["os"] += [
        {"page": f"Extra{i}", "title": f"Extra {i:02d}", "audience": "learner", "desc": "x"} for i in range(40)
    ]
    after = len(gwn.render_sidebar(m).splitlines())
    assert after == before, "unmarked pages must not add sidebar lines once a group already shows its key pages"
    assert after <= SIDEBAR_LINE_BUDGET


def test_the_sidebar_never_lists_a_page_the_nav_does_not_know():
    listed = set(PAGE_LINK.findall((WIKI / "_Sidebar.md").read_text()))
    known = set(gwn.all_page_names(manifest())) | {"Contents"}
    assert listed, "expected the sidebar to link pages"
    assert listed <= known, f"sidebar links unknown pages: {sorted(listed - known)}"


def test_every_page_is_in_contents_and_every_sidebar_page_is_a_contents_row():
    in_contents = set(PAGE_LINK.findall((WIKI / "Contents.md").read_text()))
    assert pages_on_disk() - {"Contents"} <= in_contents
    sidebar_pages = set(PAGE_LINK.findall((WIKI / "_Sidebar.md").read_text()))
    assert sidebar_pages - {"Contents"} <= in_contents


def test_every_sidebar_group_ends_with_a_link_to_its_contents_anchor_and_the_anchor_exists():
    sidebar = (WIKI / "_Sidebar.md").read_text()
    contents = (WIKI / "Contents.md").read_text()
    headings = {gwn.slug(line[3:]) for line in contents.splitlines() if line.startswith("## ")}
    blocks = sidebar.split("<details")[1:]
    shown = [g for g in gwn.groups_of(manifest()) if g["id"] != gwn.TOP_GROUP]
    assert len(blocks) == len(shown) >= 10
    for group, block in zip(shown, blocks, strict=True):
        items = [line for line in block.split("</details>")[0].splitlines() if SIDEBAR_ITEM.match(line)]
        found = SIDEBAR_GROUP_LINK.findall(items[-1])
        assert found == [gwn.slug(group["title"])], f"{group['id']}: last item is {items[-1]!r}"
        assert found[0] in headings, f"{group['id']}: no Contents heading for #{found[0]}"


def test_group_titles_make_distinct_contents_anchors():
    slugs = [gwn.slug(g["title"]) for g in gwn.groups_of(manifest())]
    assert len(slugs) == len(set(slugs))


def test_a_group_with_no_marked_page_shows_its_first_pages_by_the_documented_default():
    m = bulk_group(12)
    shown = re.findall(r"\]\((P\d\d)\.md\)", ref_block(gwn.render_sidebar(m)))
    assert shown == [f"P{i:02d}" for i in range(gwn.DEFAULT_SIDEBAR_PAGES)]
    assert 1 <= gwn.DEFAULT_SIDEBAR_PAGES <= 6


def test_the_default_follows_display_order_for_a_sorted_group():
    m = bulk_group(8)
    m["pages"]["ref"].reverse()  # written out of order; a sorted group still shows the first in title order
    shown = re.findall(r"\]\((P\d\d)\.md\)", ref_block(gwn.render_sidebar(m)))
    assert shown == [f"P{i:02d}" for i in range(gwn.DEFAULT_SIDEBAR_PAGES)]


def test_marked_pages_replace_the_default_and_keep_display_order():
    m = bulk_group(12, P09={"sidebar": True}, P04={"sidebar": True})
    shown = re.findall(r"\]\((P\d\d)\.md\)", ref_block(gwn.render_sidebar(m)))
    assert shown == ["P04", "P09"]


def test_the_group_link_counts_every_page_and_points_at_the_contents_heading():
    m = bulk_group(12)
    sidebar = gwn.render_sidebar(m)
    last = [line for line in ref_block(sidebar).splitlines() if SIDEBAR_ITEM.match(line)][-1]
    assert "(Contents.md#reference)" in last and "12" in last
    assert "<b>Reference</b> (12)" in sidebar


def test_the_numbered_core_path_is_listed_in_full_with_its_contents_link():
    m = minimal()
    m["pages"]["core"] += [
        {"page": f"Step{i}", "title": f"Step {i}", "audience": "newcomer", "desc": "x"} for i in range(8)
    ]
    block = gwn.render_sidebar(m).split("<summary><b>Core path</b>", 1)[1].split("</details>", 1)[0]
    assert len(re.findall(r"^\d+\. \[", block, flags=re.MULTILINE)) == 9
    assert "(Contents.md#core-path)" in block


def test_a_sidebar_flag_must_be_true_or_false():
    m = minimal()
    m["pages"]["ref"][0]["sidebar"] = "yes"
    assert any("sidebar must be true or false" in p for p in gwn.validate(m, MINIMAL_PAGES))
    m["pages"]["ref"][0]["sidebar"] = True
    assert gwn.validate(m, MINIMAL_PAGES) == []


def test_two_groups_with_the_same_contents_anchor_are_refused():
    m = minimal()
    m["groups"].append({"id": "ref2", "title": "reference!", "order": "sorted"})
    assert any("same Contents anchor" in p for p in gwn.validate(m, MINIMAL_PAGES))


def test_the_committed_manifest_marks_key_pages():
    marked = [e["page"] for pages in manifest()["pages"].values() for e in pages if e.get("sidebar")]
    assert marked, "expected key pages to be marked"
    assert set(marked) <= pages_on_disk()


# -- the checks bite --------------------------------------------------------------------------


def test_minimal_fixture_is_valid():
    assert gwn.validate(minimal(), MINIMAL_PAGES) == []


def test_orphan_page_is_refused():
    problems = gwn.validate(minimal(), MINIMAL_PAGES | {"Lonely"})
    assert any("orphan: Lonely" in p for p in problems)


def test_dead_entry_is_refused():
    problems = gwn.validate(minimal(), MINIMAL_PAGES - {"Berry"})
    assert any("dead entry: Berry" in p for p in problems)


def test_page_listed_twice_is_refused():
    m = minimal()
    m["pages"]["core"].append(dict(m["pages"]["ref"][0]))
    assert any("listed twice" in p for p in gwn.validate(m, MINIMAL_PAGES))


def test_special_pages_cannot_be_listed():
    m = minimal()
    m["pages"]["ref"].append({"page": "_Sidebar", "title": "Zed", "audience": "everyone", "desc": "x"})
    assert any("wiki chrome" in p for p in gwn.validate(m, MINIMAL_PAGES | {"_Sidebar"}))


def test_unknown_status_audience_and_field_are_refused():
    m = minimal()
    m["pages"]["ref"][0]["status"] = "verified"
    m["pages"]["ref"][1]["audience"] = "wizards"
    m["pages"]["core"][0]["extra"] = 1
    joined = "\n".join(gwn.validate(m, MINIMAL_PAGES))
    assert "status 'verified'" in joined and "audience 'wizards'" in joined and "unknown field" in joined


@pytest.mark.parametrize("bad", ["a | b", "two\nlines", "em \u2014 dash", "x](y", "<b>x</b>", "use `code`", "", "  padded "])
def test_text_that_would_break_the_markdown_is_refused(bad):
    m = minimal()
    m["pages"]["ref"][0]["desc"] = bad
    assert gwn.validate(m, MINIMAL_PAGES)


def test_an_over_long_description_is_refused():
    m = minimal()
    m["pages"]["ref"][0]["desc"] = "word " * 60
    assert any("over" in p for p in gwn.validate(m, MINIMAL_PAGES))


def test_a_sorted_group_out_of_order_is_refused():
    m = minimal()
    m["pages"]["ref"].reverse()
    assert any("not in title order" in p for p in gwn.validate(m, MINIMAL_PAGES))


def test_undeclared_group_and_missing_start_group_are_refused():
    m = minimal()
    m["pages"]["mystery"] = [{"page": "Zed", "title": "Zed", "audience": "everyone", "desc": "x"}]
    assert any("not declared" in p for p in gwn.validate(m, MINIMAL_PAGES | {"Zed"}))
    m = minimal()
    m["groups"] = [g for g in m["groups"] if g["id"] != "start"]
    m["pages"].pop("start")
    assert any("'start' group is missing" in p for p in gwn.validate(m, MINIMAL_PAGES - {"Home"}))


def test_external_links_must_be_github_blob_or_tree_urls():
    m = minimal()
    m["links"] = {"ref": [{"url": "https://example.com/x", "title": "X", "audience": "everyone", "desc": "x"}]}
    assert any("url must be" in p for p in gwn.validate(m, MINIMAL_PAGES))


def test_duplicate_yaml_keys_are_refused():
    with pytest.raises(ValueError, match="duplicate key"):
        gwn.load_manifest("groups: []\ngroups: []\n")
    with pytest.raises(ValueError, match="duplicate key"):
        gwn.load_manifest("pages:\n  a:\n    - {page: X, page: Y}\n")


def test_yaml_tags_cannot_build_objects():
    with pytest.raises(Exception):  # noqa: B017 - any refusal of a python tag is the point
        gwn.load_manifest("x: !!python/object/apply:os.getcwd []\n")


def test_sorted_groups_render_in_title_order_even_if_written_out_of_order():
    m = minimal()
    m["pages"]["ref"].reverse()
    assert [e["page"] for e in gwn.entries(m, "ref")] == ["Apple", "Berry"]


def test_render_marks_numbered_groups_and_statuses():
    m = minimal()
    sidebar = gwn.render_sidebar(m)
    assert "1. [One](One.md)" in sidebar
    assert "- [Berry](Berry.md) (draft)" in sidebar
    assert sidebar.count("<details open>") == 1
    contents = gwn.render_contents(m)
    assert "| 1 | [One](One.md) | The first page. | newcomer |  |" in contents
    assert "| [Berry](Berry.md) | Another page. | builder | draft |" in contents


def test_check_reports_a_stale_generated_file(tmp_path):
    (tmp_path / "docs" / "wiki").mkdir(parents=True)
    for name in ("Home", "One", "Apple", "Berry"):
        (tmp_path / "docs" / "wiki" / f"{name}.md").write_text(f"# {name}\n")
    m = minimal()
    import yaml
    (tmp_path / "docs" / "wiki" / "_nav.yaml").write_text(yaml.safe_dump(m))
    assert gwn.main(["--root", str(tmp_path)]) == 1  # Contents is not listed yet, so the write is refused
    m["pages"]["start"].append({"page": "Contents", "title": "Contents", "audience": "everyone", "desc": "Index."})
    (tmp_path / "docs" / "wiki" / "_nav.yaml").write_text(yaml.safe_dump(m))
    assert gwn.main(["--root", str(tmp_path)]) == 0
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 0
    sidebar = tmp_path / "docs" / "wiki" / "_Sidebar.md"
    sidebar.write_text(sidebar.read_text() + "- [Hand edit](Home.md)\n")
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 1
    sidebar.unlink()
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 1


MALFORMED = {
    "bad indentation": "groups:\n  - {id: a}\n pages:\n    x: 1\n",
    "unterminated flow mapping": "groups:\n  - {id: a, title: \"x\"\npages: {}\n",
    "tab character": "groups:\n\t- {id: a}\n",
    "duplicate key": "groups: []\ngroups: []\n",
    "not a mapping": "- just\n- a list\n",
}


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_malformed_manifest_is_a_controlled_error_in_both_modes(name, tmp_path, capsys):
    (tmp_path / "docs" / "wiki").mkdir(parents=True)
    (tmp_path / "docs" / "wiki" / "_nav.yaml").write_text(MALFORMED[name])
    for argv in (["--root", str(tmp_path), "--check"], ["--root", str(tmp_path)]):
        assert gwn.main(argv) == 1
        err = capsys.readouterr().err
        assert "gen_wiki_nav:" in err and "Traceback" not in err
    assert gwn.check(tmp_path)[0].startswith("cannot read")


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_malformed_manifest_prints_no_traceback_from_the_command_line(name, tmp_path):
    (tmp_path / "docs" / "wiki").mkdir(parents=True)
    (tmp_path / "docs" / "wiki" / "_nav.yaml").write_text(MALFORMED[name])
    result = subprocess.run(
        [sys.executable, "-I", str(ROOT / "scripts" / "gen_wiki_nav.py"), "--check", "--root", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr and "gen_wiki_nav:" in result.stderr


def test_unreadable_bytes_are_a_controlled_error(tmp_path, capsys):
    (tmp_path / "docs" / "wiki").mkdir(parents=True)
    (tmp_path / "docs" / "wiki" / "_nav.yaml").write_bytes(b"groups: \xff\xfe\n")
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_grafana_and_conceptual_pages_carry_no_status_their_banner_does_not_support():
    status = {e["page"]: e.get("status") for pages in manifest()["pages"].values() for e in pages}
    for page in ("Grafana-Dashboards", "Twingate-Service-Accounts-in-CAH", "Zero-Trust-at-Home-Two-Connectors-and-Failover"):
        assert status[page] is None, page
