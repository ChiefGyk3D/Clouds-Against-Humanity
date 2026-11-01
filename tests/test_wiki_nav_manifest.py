# SPDX-License-Identifier: Apache-2.0
"""The wiki navigation manifest, Contents page and sidebar (issue #249).

What is proved:
- every wiki page is in docs/wiki/_nav.yaml exactly once, and every entry names a page that
  exists (no orphans, no dead entries, no duplicates);
- Contents.md and _Sidebar.md are exactly what gen_wiki_nav.py renders, so they are
  reproducible and --check passes on the committed files;
- Contents has a link for every page, and the sidebar fits its line budget;
- the sidebar lists every page in a collapsible group and Home carries a generated map of every
  page between markers (issue #378);
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
    # Issue #416: the theme groups became topic tracks, so a theme is now a group title or a subgroup title.
    m = manifest()
    subgroups = [e["subgroup"] for pages in m["pages"].values() for e in pages if e.get("subgroup")]
    titles = " ".join([g["title"].lower() for g in gwn.groups_of(m)] + [s.lower() for s in subgroups])
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
    # Issue #378: a summary shares its line with <details>, and groups hold nested subgroups, so track depth.
    visible, stack = 0, []  # one flag per open <details> block we are inside: True when it is collapsed
    for line in text.splitlines():
        if not line.strip():
            continue
        hidden = any(stack)
        if line.startswith("</details>"):
            stack.pop()
            continue
        if line.startswith("<details"):
            if not hidden:
                visible += 1  # the summary of a block that is itself on screen
            stack.append(not line.startswith("<details open>"))
        elif not hidden:
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
    # The outside links are listed in the sidebar too (issue #378) and stay on the Contents page.
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

SIDEBAR_HEADROOM = 25  # lines (one page each, worst case) the committed sidebar must leave under the budget (issue #378)
# The collection floor for "something was collected": the core path, the five topic tracks, the security tools
# group and Reference. Issue #416 folded the 15 theme groups into the five tracks, so the old floor of 10 groups
# (a count of the theme groups) no longer describes the sidebar; the zip(strict=True) beside it still ties
# every sidebar block to a manifest group.
MIN_SIDEBAR_GROUPS = 8
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


def test_the_sidebar_leaves_room_for_twenty_five_more_pages_under_the_budget():
    # Issue #378: the sidebar lists every page, so it grows with the wiki. Subgroups pack several links per
    # line; the margin is 25 pages at the worst case of one line each (a page with no subgroup).
    lines = (WIKI / "_Sidebar.md").read_text().splitlines()
    assert len(lines) <= SIDEBAR_LINE_BUDGET - SIDEBAR_HEADROOM, f"{len(lines)} lines"


def test_twenty_five_more_unsubgrouped_pages_still_fit_the_budget():
    m = manifest()
    m["pages"]["foundations"] += [
        {"page": f"Extra{i}", "title": f"Extra {i:02d}", "audience": "learner", "desc": "x"} for i in range(25)
    ]
    assert len(gwn.render_sidebar(m).splitlines()) <= SIDEBAR_LINE_BUDGET


def test_each_added_page_adds_exactly_one_sidebar_line_and_is_listed():
    m = manifest()
    before = len(gwn.render_sidebar(m).splitlines())
    m["pages"]["foundations"] += [
        {"page": f"Extra{i}", "title": f"Extra {i:02d}", "audience": "learner", "desc": "x"} for i in range(5)
    ]
    sidebar = gwn.render_sidebar(m)
    assert len(sidebar.splitlines()) == before + 5
    for i in range(5):
        assert f"](Extra{i}.md)" in sidebar


def unlisted_in_sidebar(sidebar: str, m: dict) -> list[str]:
    """Every manifest page (and outside link) the sidebar text does not link."""
    listed = set(PAGE_LINK.findall(sidebar))
    missing = sorted(set(gwn.all_page_names(m)) - listed)
    for links in (m.get("links") or {}).values():
        missing += [e["url"] for e in links if e["url"] not in sidebar]
    return missing


def test_the_sidebar_lists_every_page_and_every_outside_link():
    sidebar = (WIKI / "_Sidebar.md").read_text()
    assert PAGE_LINK.findall(sidebar), "expected the sidebar to link pages"
    assert unlisted_in_sidebar(sidebar, manifest()) == []


def test_the_sidebar_listing_check_bites_when_a_page_or_link_is_dropped():
    m = manifest()
    sidebar = gwn.render_sidebar(m)
    victim = gwn.entries(m, "foundations")[0]["page"]
    outside = m["links"]["reference"][0]["url"]
    # Rows can hold several links (subgroups), so cut just the one link, not the whole line.
    cut = re.sub(rf"\[[^\]]*\]\({re.escape(victim)}\.md\)", "", sidebar)
    cut = "\n".join(line for line in cut.splitlines() if outside not in line)
    assert unlisted_in_sidebar(cut, m) == [victim, outside]


GROUP_START = re.compile(r"(?m)^<details(?: open)?><summary><b>")
LINK_ANY = re.compile(r"\]\((?:[A-Za-z0-9_-]+\.md(?:#[^)]*)?|https://[^)]+)\)")


def group_blocks(sidebar: str) -> list[str]:
    """The text of each top-level group (nested subgroup blocks stay inside their group)."""
    return [b.rsplit("</details>", 1)[0] for b in GROUP_START.split(sidebar)[1:]]


def test_the_sidebar_links_each_page_of_each_group_once_plus_the_full_list():
    m = manifest()
    blocks = group_blocks((WIKI / "_Sidebar.md").read_text())
    shown = [g for g in gwn.groups_of(m) if g["id"] != gwn.TOP_GROUP]
    assert len(blocks) == len(shown) >= MIN_SIDEBAR_GROUPS
    for group, block in zip(shown, blocks, strict=True):
        expected = len(gwn.entries(m, group["id"])) + len(gwn.link_entries(m, group["id"]))
        assert len(LINK_ANY.findall(block)) == expected + 1, f"{group['id']}: links do not match {expected} pages (+ the Full list link)"


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
    blocks = group_blocks(sidebar)
    shown = [g for g in gwn.groups_of(manifest()) if g["id"] != gwn.TOP_GROUP]
    assert len(blocks) == len(shown) >= MIN_SIDEBAR_GROUPS
    for group, block in zip(shown, blocks, strict=True):
        items = [line for line in block.splitlines() if SIDEBAR_ITEM.match(line)]
        found = SIDEBAR_GROUP_LINK.findall(items[-1])
        assert found == [gwn.slug(group["title"])], f"{group['id']}: last item is {items[-1]!r}"
        assert found[0] in headings, f"{group['id']}: no Contents heading for #{found[0]}"


def test_group_titles_make_distinct_contents_anchors():
    slugs = [gwn.slug(g["title"]) for g in gwn.groups_of(manifest())]
    assert len(slugs) == len(set(slugs))


def test_a_group_with_no_marked_page_lists_every_page_in_display_order():
    # Issue #378 replaced the "first three" default: every group lists every page.
    m = bulk_group(12)
    shown = re.findall(r"\]\((P\d\d)\.md\)", ref_block(gwn.render_sidebar(m)))
    assert shown == [f"P{i:02d}" for i in range(12)]


def test_display_order_for_a_sorted_group_is_title_order_in_the_sidebar():
    m = bulk_group(8)
    m["pages"]["ref"].reverse()  # written out of order; a sorted group still lists in title order
    shown = re.findall(r"\]\((P\d\d)\.md\)", ref_block(gwn.render_sidebar(m)))
    assert shown == [f"P{i:02d}" for i in range(8)]


def test_marked_pages_are_pinned_to_the_top_then_the_rest_follow_in_display_order():
    m = bulk_group(12, P09={"sidebar": True}, P04={"sidebar": True})
    shown = re.findall(r"\]\((P\d\d)\.md\)", ref_block(gwn.render_sidebar(m)))
    assert shown == ["P04", "P09"] + [f"P{i:02d}" for i in range(12) if i not in (4, 9)]
    assert len(shown) == len(set(shown)) == 12


def subgroup_manifest(pages: int = 12, **marks) -> dict:
    """bulk_group with every entry in one subgroup called 'Series' (unless a mark says otherwise)."""
    m = bulk_group(pages, **marks)
    for e in m["pages"]["ref"]:
        e.setdefault("subgroup", "Series")
    return m


def subgroup_block(sidebar: str) -> str:
    return ref_block(sidebar).split("<details><summary>", 1)[1]


def test_a_subgroup_is_a_nested_details_block_with_its_title_and_count():
    sidebar = gwn.render_sidebar(subgroup_manifest(12))
    assert "<details><summary>Series (12)</summary>\n\n- [P00](P00.md)" in sidebar
    assert sidebar.count("<details") == sidebar.count("</details>") == sidebar.count("<summary>")


def test_a_subgroup_packs_several_links_per_line_within_the_documented_limits():
    m = subgroup_manifest(23)
    lines = [ln for ln in subgroup_block(gwn.render_sidebar(m)).split("</details>", 1)[0].splitlines() if ln.startswith("- ")]
    assert len(lines) < 23 and len(lines) == -(-23 // gwn.SIDEBAR_PACK_LINKS)
    for ln in lines:
        assert 1 <= len(re.findall(r"\]\(P\d\d\.md\)", ln)) <= gwn.SIDEBAR_PACK_LINKS
        assert " · " in ln or ln.count("](") == 1
    shown = re.findall(r"\]\((P\d\d)\.md\)", "\n".join(lines))
    assert shown == [f"P{i:02d}" for i in range(23)]


def test_a_long_title_wraps_a_packed_line_by_characters_before_the_link_limit():
    m = subgroup_manifest(6)
    for e in m["pages"]["ref"]:
        e["title"] = "T" * (gwn.SIDEBAR_PACK_CHARS // 2 - 5)
    lines = [ln for ln in subgroup_block(gwn.render_sidebar(m)).split("</details>", 1)[0].splitlines() if ln.startswith("- ")]
    assert len(lines) == 3 and all(ln.count("](") == 2 for ln in lines)


def test_pinned_pages_come_first_inside_a_subgroup_and_ungrouped_pages_come_before_subgroups():
    m = subgroup_manifest(8, P06={"sidebar": True, "subgroup": "Series"}, P01={"subgroup": None})
    del m["pages"]["ref"][1]["subgroup"]  # P01 stays ungrouped
    shown = re.findall(r"\]\((P\d\d)\.md\)", ref_block(gwn.render_sidebar(m)))
    assert shown[0] == "P01"  # the ungrouped page is listed before the nested block
    assert shown[1] == "P06"  # then the pinned page leads its subgroup
    assert sorted(shown) == [f"P{i:02d}" for i in range(8)]


def test_a_subgroup_never_hides_the_full_list_link_which_stays_last():
    block = gwn.render_sidebar(subgroup_manifest(9)).split("<summary><b>Reference</b>", 1)[1].rsplit("</details>", 1)[0]
    items = [ln for ln in block.splitlines() if SIDEBAR_ITEM.match(ln)]
    assert "(Contents.md#reference)" in items[-1]


def test_a_subgroup_must_be_plain_text_and_is_refused_on_the_core_path_and_the_start_group():
    m = minimal()
    m["pages"]["ref"][0]["subgroup"] = "a | b"
    assert any("subgroup" in p for p in gwn.validate(m, MINIMAL_PAGES))
    m = minimal()
    m["pages"]["core"][0]["subgroup"] = "Early"
    assert any("numbered" in p and "subgroup" in p for p in gwn.validate(m, MINIMAL_PAGES))
    m = minimal()
    m["pages"]["start"][0]["subgroup"] = "Top"
    assert any("subgroup" in p for p in gwn.validate(m, MINIMAL_PAGES))
    m = minimal()
    m["pages"]["ref"][0]["subgroup"] = "Fine title"
    assert gwn.validate(m, MINIMAL_PAGES) == []


def test_the_committed_manifest_folds_pages_into_subgroups_and_the_core_path_stays_whole():
    m = manifest()
    assert sum(1 for pages in m["pages"].values() for e in pages if e.get("subgroup")) >= 30
    assert not any(e.get("subgroup") for e in m["pages"]["core"])
    sidebar = (WIKI / "_Sidebar.md").read_text()
    core = sidebar.split("<summary><b>Core path", 1)[1].split("</details>", 1)[0]
    assert "<details>" not in core and len(re.findall(r"^\d+\. \[", core, flags=re.MULTILINE)) == 21


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


# -- the Home page map (issue #378) -----------------------------------------------------------

HOME_SIZE_BUDGET = 100_000  # bytes; our own cap (the wiki docs state no size limit for a page), well under any render limit
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)


def home_text() -> str:
    return (WIKI / "Home.md").read_text(encoding="utf-8")


def map_region(text: str) -> str:
    assert text.count(gwn.HOME_BEGIN) == 1 and text.count(gwn.HOME_END) == 1, "Home needs exactly one pair of map markers"
    return text.split(gwn.HOME_BEGIN, 1)[1].split(gwn.HOME_END, 1)[0]


def pages_missing_from_home_map(text: str, m: dict) -> list[str]:
    """Manifest pages that the generated map region of a Home text does not link."""
    linked = set(PAGE_LINK.findall(map_region(text)))
    return sorted(set(gwn.all_page_names(m)) - linked)


def test_home_lists_every_manifest_page_in_its_map():
    region = map_region(home_text())
    assert PAGE_LINK.findall(region), "the guard collected no links from the Home map"
    assert pages_missing_from_home_map(home_text(), manifest()) == []


def test_the_home_map_check_bites_when_a_page_is_missing():
    m = manifest()
    victim = gwn.entries(m, "foundations")[0]["page"]
    cut = "\n".join(line for line in home_text().splitlines() if not (f"]({victim}.md)" in line and line.startswith(("- ", "1. ", "2. "))))
    assert pages_missing_from_home_map(cut, m) == [victim]


def test_home_matches_what_the_generator_renders_between_the_markers():
    m = manifest()
    text = home_text()
    assert gwn.apply_home_map(text, gwn.render_home_map(m)) == text


def test_home_map_groups_are_the_contents_groups_in_the_same_order():
    m = manifest()
    contents = [line[3:] for line in (WIKI / "Contents.md").read_text().splitlines() if line.startswith("## ") and line != "## Groups"]
    in_home = [mt.group(2) for mt in HEADING.finditer(map_region(home_text())) if mt.group(1) == "###" and mt.group(2) in contents]
    assert in_home == contents == [g["title"] for g in gwn.groups_of(m)]


def test_home_map_gives_every_page_its_manifest_description_and_status():
    region = map_region(home_text())
    for pages in manifest()["pages"].values():
        for e in pages:
            row = re.compile(rf"^(- |\d+\. )\[[^\]]*\]\({e['page']}\.md\)")
            line = next((ln for ln in region.splitlines() if row.match(ln)), None)
            assert line is not None, e["page"]
            assert line.endswith(f": {e['desc']}"), e["page"]
            if "status" in e:
                assert f"]({e['page']}.md) ({e['status']}): " in line, e["page"]
            else:
                assert f"]({e['page']}.md): " in line, e["page"]


def test_home_map_includes_the_outside_links_contents_has():
    region = map_region(home_text())
    urls = [e["url"] for links in manifest()["links"].values() for e in links]
    assert urls and all(f"]({u})" in region for u in urls)


def test_home_names_a_start_here_page_for_every_kind_of_reader():
    m = manifest()
    region = map_region(home_text())
    readers = m["readers"]
    assert {r["audience"] for r in readers} == set(gwn.AUDIENCES)
    for r in readers:
        line = next((ln for ln in region.splitlines() if ln.startswith(f"- **{r['who']}**")), None)
        assert line is not None and f"]({r['page']}.md)" in line, r["audience"]
    assert "Start here, by kind of reader" in region


def test_home_keeps_its_hand_written_intro_and_path_table():
    text = home_text()
    start = text.index(gwn.HOME_BEGIN)
    before = text[:start]
    assert before.startswith("# Clouds Against Humanity\n")
    assert "## Pick a path" in before and "| You are... | Start with | Then |" in before
    assert "## Current state" in text[text.index(gwn.HOME_END):]


def test_home_stays_inside_its_size_budget():
    size = len(home_text().encode("utf-8"))
    assert size <= HOME_SIZE_BUDGET, f"Home is {size} bytes, budget {HOME_SIZE_BUDGET}"


def test_home_has_no_duplicate_heading_anchors():
    anchors = [gwn.slug(mt.group(2)) for mt in HEADING.finditer(re.sub(r"```.*?```", "", home_text(), flags=re.DOTALL))]
    dupes = sorted({a for a in anchors if anchors.count(a) > 1})
    assert not dupes, f"duplicate Home anchors (GitHub would rename the second): {dupes}"


def test_apply_home_map_rewrites_only_between_the_markers():
    block = f"{gwn.HOME_BEGIN}\nNEW\n{gwn.HOME_END}"
    text = f"intro\n\n{gwn.HOME_BEGIN}\nOLD\n{gwn.HOME_END}\n\ntail\n"
    assert gwn.apply_home_map(text, block) == f"intro\n\n{block}\n\ntail\n"


@pytest.mark.parametrize(
    "text",
    [
        "no markers at all\n",
        f"{gwn.HOME_BEGIN}\nonly a begin\n",
        f"{gwn.HOME_END}\nend first\n{gwn.HOME_BEGIN}\n",
        f"{gwn.HOME_BEGIN}\na\n{gwn.HOME_END}\n{gwn.HOME_BEGIN}\nb\n{gwn.HOME_END}\n",
    ],
)
def test_missing_misordered_or_repeated_markers_are_refused(text):
    with pytest.raises(ValueError, match="marker"):
        gwn.apply_home_map(text, "x")


def test_a_new_manifest_page_lands_in_the_home_map():
    m = minimal()
    m["pages"]["ref"].append({"page": "Zed", "title": "Zed", "audience": "everyone", "desc": "The last page."})
    block = gwn.render_home_map(m)
    assert "- [Zed](Zed.md): The last page." in block
    assert "1. [One](One.md): The first page." in block
    assert "- [Berry](Berry.md) (draft): Another page." in block


def test_a_stale_or_unmarked_home_is_refused_by_check(tmp_path):
    wiki = tmp_path / "docs" / "wiki"
    wiki.mkdir(parents=True)
    import yaml
    m = minimal()
    m["pages"]["start"].append({"page": "Contents", "title": "Contents", "audience": "everyone", "desc": "Index."})
    (wiki / "_nav.yaml").write_text(yaml.safe_dump(m))
    for name in ("One", "Apple", "Berry", "Contents"):
        (wiki / f"{name}.md").write_text(f"# {name}\n")
    (wiki / "Home.md").write_text("# Home\n\nno markers yet\n")
    assert gwn.main(["--root", str(tmp_path)]) == 1  # no markers: the write is refused, nothing is invented
    (wiki / "Home.md").write_text(f"# Home\n\nhand-written\n\n{gwn.HOME_BEGIN}\n{gwn.HOME_END}\n\nmore\n")
    assert gwn.main(["--root", str(tmp_path)]) == 0
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 0
    home = (wiki / "Home.md").read_text()
    assert home.startswith("# Home\n\nhand-written\n\n") and home.endswith("\n\nmore\n") and "](Berry.md)" in home
    (wiki / "Home.md").write_text(home.replace("](Berry.md)", "](Apple.md)"))
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 1


def test_the_readers_block_must_cover_every_audience_once_with_known_pages():
    m = minimal()
    m["readers"] = [{"audience": "everyone", "who": "Anyone", "page": "Home"}]
    joined = "\n".join(gwn.validate(m, MINIMAL_PAGES))
    assert "readers: no start page for audience" in joined
    m["readers"] = [{"audience": a, "who": a.title(), "page": "Nowhere"} for a in gwn.AUDIENCES] + [{"audience": "wizards", "who": "W", "page": "Home"}]
    joined = "\n".join(gwn.validate(m, MINIMAL_PAGES))
    assert "'Nowhere'" in joined and "wizards" in joined
    m["readers"] = [{"audience": a, "who": a.title(), "page": "Home"} for a in gwn.AUDIENCES]
    assert gwn.validate(m, MINIMAL_PAGES) == []
    m["readers"].append({"audience": "builder", "who": "Again", "page": "Home"})
    assert any("twice" in p for p in gwn.validate(m, MINIMAL_PAGES))


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
    # Home carries the generated map between markers (issue #378); the fixture needs the pair.
    (tmp_path / "docs" / "wiki" / "Home.md").write_text(f"# Home\n\n{gwn.HOME_BEGIN}\n{gwn.HOME_END}\n")
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


# -- the five topic tracks (issue #416) -------------------------------------------------------------

# Each track and the pages the maintainer's brief names for it, as page-name prefixes (each prefix must pick
# out exactly one page of the track, so a renamed or moved page is noticed).
TRACKS = {
    "foundations": (
        "Track 1: Foundations",
        (
            "Terminal-and-Your-First-Script", "Linux-for-Enterprise-Beginners", "First-Hour-on-a-New-System",
            "Patch-Management", "Windows-Active-Directory", "Virtual-Machines-Hypervisors",
            "How-a-Web-Request-Works", "Subnets-NAT-and-Firewalls", "IPv6-Adoption", "LAMP-and-LEMP",
            "WordPress-and-PHP-Security", "APIs-and-Tokens-From-Zero", "Secrets-From-Day-One",
            "Hashing-Encryption-and-Keys", "OpenTofu-From-Zero", "Plans-State-Drift",
        ),
    ),
    "defend": (
        "Track 2: Defend and detect",
        (
            "Packet-Filters-Compared", "IDS-and-IPS", "File-Integrity-and-Alerting", "Rate-Limiting",
            "The-DMZ-and-Hardening", "Deception-and-Honeypots-Start-Here", "Deception-and-Honeypots-T-Pot",
            "Logs-SIEM-and-Detection", "Detection-and-Monitoring-Wazuh", "Wazuh-SIEM-and-Data-Pipelines",
            "Grafana-Basics", "Grafana-Dashboards", "Build-Your-Own-Mini-SOC",
        ),
    ),
    "privacy": (
        "Track 3: Privacy, anonymity and cryptocurrency",
        (
            "Tor-I2P-and-the-Darknet", "How-a-VPN-Works", "How-Tor-Works-in-Depth", "How-I2P-Works",
            "The-Darknet-Landscape", "Privacy-Security-and-Anonymity", "The-Browsing-Setups-Compared",
            "Cryptography-Fundamentals", "Privacy-vs-Security", "Radio-Off-Grid", "Blockchain-Fundamentals",
            "How-Bitcoin-Works", "How-Monero-Works", "Wallets-and-Key-Custody", "Running-Monero-Properly",
        ),
    ),
    "grc": (
        "Track 4: GRC and law",
        (
            "GRC-Governance-Risk", "US-Privacy-Law", "Privacy-Law-Around-the-World",
            "Cross-Tenant-Data-Governance", "Business-Continuity", "The-CIA-Triad", "Backups-Deep-Dive",
            "Backups-Recovery-and-Patching", "RAID-Levels",
        ),
    ),
    "build": (
        "Track 5: Build and operate",
        (
            "Fork-Private-Stacks", "Labs-Break-It", "Build-It-From-Zero", "Teardown-Checklist", "From-Commit-to-Pipeline",
            "Why-the-Clouds-Differ", "Provider-AWS-Account", "Provider-Azure-Account", "Provider-GCP-Account",
            "Enterprise-Networks", "Enterprise-Change-Management", "Working-in-a-Company", "Careers-Roles",
            "How-This-Project-Is-Planned", "Project-Status", "Repository-Growth", "Screenshots-Policy",
        ),
    ),
}
TRACK_ORDER = ["foundations", "tools", "defend", "privacy", "grc", "build"]


def track_problems(m: dict) -> list[str]:
    """Every way the manifest fails the five-track layout: a track missing or mis-shaped, or a named page not in it."""
    problems = []
    groups = {g["id"]: g for g in gwn.groups_of(m)}
    for gid, (title, prefixes) in TRACKS.items():
        group = groups.get(gid)
        if group is None:
            problems.append(f"no track {gid}")
            continue
        if group["title"] != title:
            problems.append(f"{gid}: title {group['title']!r}")
        if not (group.get("numbered") and group.get("track") and group.get("order") == "curated" and not group.get("open")):
            problems.append(f"{gid}: not a numbered, curated, closed track")
        names = [e["page"] for e in gwn.entries(m, gid)]
        for prefix in prefixes:
            hits = [n for n in names if n.startswith(prefix)]
            if len(hits) != 1:
                problems.append(f"{gid}: {prefix} matches {len(hits)} pages")
    return problems


def test_the_five_topic_tracks_exist_with_the_pages_the_brief_names():
    m = manifest()
    assert sum(len(prefixes) for _, prefixes in TRACKS.values()) >= 70, "the guard collected too few page names"
    assert track_problems(m) == []
    order = [g["id"] for g in gwn.groups_of(m)]
    assert [i for i in order if i in TRACK_ORDER] == TRACK_ORDER
    assert order.index("core") < order.index("foundations")  # the core path stays the first block


def test_the_track_check_bites_when_a_page_or_a_track_is_missing():
    m = manifest()
    victim = next(e for e in m["pages"]["privacy"] if e["page"].startswith("How-Monero-Works"))
    m["pages"]["privacy"].remove(victim)
    assert track_problems(m) == ["privacy: How-Monero-Works matches 0 pages"]
    m = manifest()
    m["groups"] = [g for g in m["groups"] if g["id"] != "grc"]
    assert track_problems(m) == ["no track grc"]
    m = manifest()
    next(g for g in m["groups"] if g["id"] == "build").pop("track")
    assert any("not a numbered, curated, closed track" in p for p in track_problems(m))


def test_every_page_is_in_exactly_one_group_and_one_track_at_most():
    m = manifest()
    homes: dict[str, list[str]] = {}
    for gid, group_entries in m["pages"].items():
        for e in group_entries:
            homes.setdefault(e["page"], []).append(gid)
    assert set(homes) == pages_on_disk()
    assert not {p: g for p, g in homes.items() if len(g) != 1}
    in_tracks = [p for p, g in homes.items() if g[0] in TRACKS]
    assert len(in_tracks) == sum(len(gwn.entries(m, gid)) for gid in TRACKS)
    assert len(in_tracks) >= 100, "the tracks should hold most of the wiki"


def test_the_core_path_is_unchanged_in_size_and_stays_numbered_and_open():
    m = manifest()
    core = next(g for g in gwn.groups_of(m) if g["id"] == "core")
    assert core.get("numbered") and core.get("open") and not core.get("track")
    assert len(gwn.entries(m, "core")) == 21


def test_the_security_tools_group_no_longer_holds_privacy_crypto_or_grc_pages():
    m = manifest()
    tools = {e["page"] for e in m["pages"]["tools"]}
    moved = {e["page"] for gid in ("privacy", "grc") for e in m["pages"][gid]}
    assert tools and not tools & moved
    assert len(tools) <= 8, "the basics group should stay a small block"
    for word in ("Tor", "I2P", "VPN", "Bitcoin", "Monero", "Blockchain", "Wallets", "GRC", "Privacy"):
        assert not [p for p in tools if word in p], word


def test_each_track_is_numbered_in_contents_and_home_and_folded_in_the_sidebar():
    m = manifest()
    contents, sidebar, home = gwn.render_contents(m), gwn.render_sidebar(m), gwn.render_home_map(m)
    titles = {gid: t for gid, (t, _) in TRACKS.items()}
    for gid, title in titles.items():
        first = gwn.entries(m, gid)[0]
        assert f"## {title}\n" in contents and f"### {title}\n" in home
        assert f"| 1 | [{first['title']}]({first['page']}.md)" in contents
        assert f"1. [{first['title']}]({first['page']}.md)" in home
        block = sidebar.split(f"<summary><b>{title}</b>", 1)[1].split("(Contents.md#", 1)[0]
        assert "<details><summary>" in block, f"{gid}: the sidebar block is not folded into subgroups"
        assert not re.search(r"^\d+\. ", block, flags=re.MULTILINE), f"{gid}: sidebar rows should not be numbered"
    assert re.search(r"^1\. \[", sidebar.split("<summary><b>Core path", 1)[1], flags=re.MULTILINE)


def test_a_topic_track_may_fold_into_subgroups_but_a_plain_numbered_group_may_not():
    m = minimal()
    m["groups"].append({"id": "trk", "title": "Track X", "order": "curated", "numbered": True, "track": True})
    m["pages"]["trk"] = [{"page": "Tee", "title": "Tee", "audience": "learner", "desc": "A track page.", "subgroup": "Theme"}]
    assert gwn.validate(m, MINIMAL_PAGES | {"Tee"}) == []
    sidebar = gwn.render_sidebar(m)
    assert "<details><summary>Theme (1)</summary>" in sidebar and "- [Tee](Tee.md)" in sidebar
    assert "| 1 | [Tee](Tee.md)" in gwn.render_contents(m)
    m["pages"]["core"][0]["subgroup"] = "Early"
    assert any("numbered" in p and "subgroup" in p for p in gwn.validate(m, MINIMAL_PAGES | {"Tee"}))


@pytest.mark.parametrize(
    "change",
    [
        {"numbered": False},
        {"order": "sorted"},
        {"open": True},
    ],
)
def test_a_track_must_be_numbered_curated_and_closed(change):
    m = minimal()
    m["groups"].append({"id": "trk", "title": "Track X", "order": "curated", "numbered": True, "track": True, **change})
    m["pages"]["trk"] = [{"page": "Tee", "title": "Tee", "audience": "learner", "desc": "A track page."}]
    assert any("topic track must be" in p for p in gwn.validate(m, MINIMAL_PAGES | {"Tee"}))


def test_the_home_goals_cover_every_track_and_the_three_goals_and_point_at_pages_in_them():
    m = manifest()
    region = map_region(home_text())
    assert "### Start here, by topic track and by goal" in region
    goals = m["goals"]
    assert len(goals) >= 8, "the guard collected too few goals"
    for r in goals:
        line = next((ln for ln in region.splitlines() if ln.startswith(f"- **{r['who']}**")), None)
        assert line is not None and f"]({r['page']}.md)" in line, r["who"]
    homes = {e["page"]: gid for gid, entries_ in m["pages"].items() for e in entries_}
    for number, gid in enumerate(("foundations", "defend", "privacy", "grc", "build"), start=1):
        track_goal = next(r for r in goals if r["who"].startswith(f"Track {number}"))
        assert homes[track_goal["page"]] == gid, track_goal
        assert track_goal["page"] == gwn.entries(m, gid)[0]["page"], "a track goal opens the track at its first page"
    whos = " ".join(r["who"].lower() for r in goals)
    for goal in ("privacy and anonymity", "cryptocurrency", "compliance and privacy law"):
        assert goal in whos, goal


def test_the_goals_list_is_validated():
    m = minimal()
    m["goals"] = [{"who": "Anyone", "page": "Home"}]
    assert gwn.validate(m, MINIMAL_PAGES) == []
    block = gwn.render_home_map(m)
    assert "### Start here, by topic track and by goal" in block and "- **Anyone**: [Home](Home.md)" in block
    m["goals"] = [{"who": "Anyone", "page": "Nowhere"}, {"who": "Anyone", "page": "Home"}, {"who": "Odd", "page": "Home", "x": 1}]
    joined = "\n".join(gwn.validate(m, MINIMAL_PAGES))
    assert "'Nowhere'" in joined and "listed twice" in joined and "unknown field" in joined
    m["goals"] = [{"who": "a | b", "page": "Home"}]
    assert gwn.validate(m, MINIMAL_PAGES)
    m["goals"] = "not a list"
    assert any("goals:" in p for p in gwn.validate(m, MINIMAL_PAGES))
    del m["goals"]
    assert "by topic track and by goal" not in gwn.render_home_map(m)
