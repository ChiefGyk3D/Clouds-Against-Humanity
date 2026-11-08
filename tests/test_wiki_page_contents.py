# SPDX-License-Identifier: Apache-2.0
"""The generated in-page contents list on the longest wiki pages (issue #441).

What is proved:
- the slugger builds the anchors GitHub builds: lower case, spaces to hyphens, punctuation dropped, repeated
  headings suffixed -1, -2, headings inside code blocks ignored; it agrees with every anchor link already on
  the wiki and with the anchor checker's own slugger on every wiki page;
- a page gets the block exactly when its author text (generated blocks stripped) is over TOC_MIN_LINES, it sits
  right after the first heading and banners (the publish step puts the navigation block above it), lists the `##` headings (and `###` only on a page with few of them) as
  links that resolve, and adds no heading, table or prose;
- the generator is idempotent, --check fails when a block is stale, appears or should go away, and the page
  prose is never touched;
- tests/wikitext.py page_text() strips the block (and the navigation blocks) so a link count sees the author's text.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_wiki_nav as gwn
import test_markdown_anchors as anchor_checker
from test_wiki_page_nav import (
    manifest,
    pages_with_nav,
    published,
    small,
    text_of,
    write_tree,
)
from wikitext import page_text

WIKI = ROOT / "docs" / "wiki"
ANCHOR_LINK = re.compile(r"\]\((?:([A-Za-z0-9_-]+)\.md)?#([^)\s]+)\)")


def contents_block(text: str) -> str | None:
    if gwn.TOC_BEGIN not in text:
        return None
    assert text.count(gwn.TOC_BEGIN) == 1 and text.count(gwn.TOC_END) == 1
    return text.split(gwn.TOC_BEGIN, 1)[1].split(gwn.TOC_END, 1)[0]


def long_page(name: str, lines: int, sections: int = 8, extra: str = "") -> str:
    """A page whose author text is exactly `lines` lines long, with `sections` second-level headings."""
    head = [f"# {name}", "", "> **Banner.**", ""]
    for n in range(sections):
        head += [f"## Section {n + 1}", "", f"Text {n}.", ""]
    body = head + (extra.split("\n") if extra else [])
    while len(body) < lines:
        body.append(f"filler {len(body)}")
    return "\n".join(body[:lines]) + "\n"


def wired(tmp_path, page_lines: int, name: str = "T3", sections: int = 8):
    m, texts = small()
    texts[name] = long_page(name, page_lines, sections)
    wiki = write_tree(tmp_path, m, texts)
    return m, texts, wiki


# -- the slugger ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("heading", "anchor"),
    [
        ("Plain words", "plain-words"),
        ("Mixed CASE Heading", "mixed-case-heading"),
        ("What is `nmap -sV`?", "what-is-nmap--sv"),
        ("Using `curl`", "using-curl"),
        ("Q&A", "qa"),
        ("Tom & Jerry", "tom--jerry"),
        ("Step 1: install, then test (2 of 3)", "step-1-install-then-test-2-of-3"),
        ("2024 plans", "2024-plans"),
        ("Wait... what?!", "wait-what"),
        ("Trailing punctuation.", "trailing-punctuation"),
        ("A - B", "a---b"),
        ("snake_case_name", "snake_case_name"),
        ("Café résumé naïve", "café-résumé-naïve"),
        ("Café decomposed", "café-decomposed"),
        ("日本語 heading", "日本語-heading"),
        ("Rocket \U0001f680 launch", "rocket--launch"),
        ("[A link](Other.md) in a heading", "a-link-in-a-heading"),
        ("**Bold** and *italic*", "bold-and-italic"),
        ("<kbd>Ctrl</kbd> key", "ctrl-key"),
        ("Dash-separated and under_score", "dash-separated-and-under_score"),
    ],
)
def test_the_slugger_builds_the_anchor_github_builds(heading, anchor):
    assert gwn.heading_slug(heading) == anchor


def test_repeated_headings_get_numbered_suffixes_and_a_suffix_that_collides_moves_on():
    text = "# A\n\n## Setup\n\n## Setup\n\n### Setup\n\n## Setup 1\n\n## A\n\n## A-1\n"
    anchors = [a for _, _, a in gwn.page_headings(text)]
    assert anchors == ["a", "setup", "setup-1", "setup-2", "setup-1-1", "a-1", "a-1-1"]
    # The first heading counts too (a page title that repeats a section makes that section -1).
    assert [a for _, _, a in gwn.page_headings("# Intro\n\n## Intro\n")] == ["intro", "intro-1"]


def test_headings_inside_code_blocks_and_indented_code_are_not_headings():
    text = (
        "# Top\n\n```\n## Fenced\n```\n\n~~~bash\n## Tilde\n~~~\n\n"
        "````\n```\n## Still inside the long fence\n```\n````\n\n    ## Indented code\n\n"
        "## Real one\n\n#NoSpace\n\n####### seven hashes\n\n## Closed ##\n"
    )
    found = gwn.page_headings(text)
    assert [(lvl, t) for lvl, t, _ in found] == [(1, "Top"), (2, "Real one"), (2, "Closed")]


def test_a_heading_after_an_unclosed_fence_is_not_a_heading():
    assert [t for _, t, _ in gwn.page_headings("# Top\n\n```\n## Never closed\n")] == ["Top"]


def test_the_slugger_agrees_with_every_anchor_link_already_on_the_wiki():
    anchors_of = {p.stem: {a for _, _, a in gwn.page_headings(p.read_text(encoding="utf-8"))} for p in WIKI.glob("*.md")}
    checked = 0
    for page in sorted(WIKI.glob("*.md")):
        for target, frag in ANCHOR_LINK.findall(page_text(page)):
            dest = target or page.stem
            if dest in anchors_of:
                assert frag.lower() in anchors_of[dest], f"{page.name}: {target}#{frag}"
                checked += 1
    assert checked >= 100, f"the guard checked only {checked} anchor links"


def test_the_slugger_gives_the_same_anchors_as_the_anchor_checker_on_every_wiki_page():
    pages = 0
    for page in sorted(WIKI.glob("*.md")):
        text = page.read_text(encoding="utf-8")
        mine = {a for _, _, a in gwn.page_headings(text)}
        assert mine == anchor_checker.anchors(text), page.name
        pages += 1
    assert pages >= 140


def test_the_slugger_fails_on_a_wrong_rule():
    # The negative case: a slugger that keeps punctuation, or forgets repeats, would not equal these.
    assert gwn.heading_slug("A & B?") != "a-&-b?"
    assert [a for _, _, a in gwn.page_headings("## X\n\n## X\n")] != ["x", "x"]


# -- the committed wiki ------------------------------------------------------------------------------


def author_lines(name: str) -> int:
    return len(gwn.strip_generated(text_of(name)).splitlines())


def test_a_page_has_the_block_exactly_when_its_author_text_is_over_the_threshold():
    assert gwn.TOC_MIN_LINES == 300
    with_block, without, long_without_headings = [], [], []
    for name in pages_with_nav():
        text = text_of(name)
        long_enough = author_lines(name) > gwn.TOC_MIN_LINES
        has = gwn.TOC_BEGIN in text
        if long_enough and not has:
            # A long page with no ## or ### heading has nothing to list (the Glossary is one big table under its title).
            assert not [h for h in gwn.page_headings(gwn.strip_generated(text)) if h[0] in (2, 3)], name
            long_without_headings.append(name)
        else:
            assert has == long_enough, f"{name}: {author_lines(name)} author lines, block present={has}"
        (with_block if has else without).append(name)
    assert long_without_headings == ["Glossary"]
    assert len(with_block) >= 60, f"the guard saw only {len(with_block)} pages with a block"
    assert len(without) >= 50
    for name in sorted(set(gwn.wiki_pages(ROOT)) - set(pages_with_nav())):
        assert gwn.TOC_BEGIN not in text_of(name), name


def test_the_committed_blocks_are_what_the_generator_renders_and_a_second_run_changes_nothing():
    m = manifest()
    for name in pages_with_nav():
        text = text_of(name)
        once = gwn.apply_page_contents(text, gwn.render_page_contents(gwn.strip_generated(text)))
        assert once == text, name
        assert gwn.apply_page_contents(once, gwn.render_page_contents(gwn.strip_generated(once))) == once, name
        assert not gwn.has_nav_blocks(text), name
        assert gwn.apply_page_nav(once, gwn.render_page_nav(m, name)) == published(name), name


def test_the_block_sits_right_after_the_heading_and_banners_and_before_any_prose():
    seen = 0
    for name in pages_with_nav():
        text = text_of(name)
        if gwn.TOC_BEGIN not in text:
            continue
        seen += 1
        head = text.split(gwn.TOC_BEGIN, 1)[0].splitlines()
        assert head[0].startswith("# "), name
        assert all(not line.strip() or line.startswith(">") for line in head[1:]), f"{name}: prose before the block"
        assert text.split(gwn.TOC_BEGIN, 1)[0].endswith("\n\n"), name
    assert seen >= 60


def test_on_the_published_page_the_navigation_block_comes_first_then_the_contents_block():
    seen = 0
    for name in pages_with_nav():
        text = published(name)
        if gwn.TOC_BEGIN not in text:
            continue
        seen += 1
        top_end = text.index(gwn.NAV_END.format(where="top")) + len(gwn.NAV_END.format(where="top"))
        assert text[top_end:].startswith("\n\n" + gwn.TOC_BEGIN), name
        assert text.index(gwn.TOC_END) < text.index(gwn.NAV_BEGIN.format(where="bottom")), name
    assert seen >= 60


def test_every_second_level_heading_is_listed_with_a_link_that_resolves():
    total = 0
    for name in pages_with_nav():
        text = text_of(name)
        block = contents_block(text)
        if block is None:
            continue
        author = gwn.strip_generated(text)
        headings = gwn.page_headings(author)
        h2 = [(t, a) for lvl, t, a in headings if lvl == 2]
        links = re.findall(r"\]\(#([^)]+)\)", block)
        all_anchors = {a for _, _, a in headings}
        assert set(links) <= all_anchors, name
        assert [a for _, a in h2] == [a for a in links if a in {x for _, x in h2}], f"{name}: the ## headings are not listed in order"
        if len(h2) >= gwn.TOC_SUBHEADINGS_BELOW:
            assert len(links) == len(h2), f"{name}: a page with many ## sections lists only them"
        total += len(links)
    assert total >= 1000


def test_the_block_adds_no_heading_no_table_and_no_prose():
    for name in pages_with_nav():
        block = contents_block(text_of(name))
        if block is None:
            continue
        lines = [line for line in block.splitlines() if line.strip()]
        assert lines[0] == gwn.TOC_LABEL, name
        assert all(line.lstrip().startswith("- [") for line in lines[1:]), name
        assert not any(line.lstrip().startswith(("#", "|")) for line in lines), name


def test_the_page_prose_is_untouched_by_the_block():
    for name in pages_with_nav():
        text = text_of(name)
        if gwn.TOC_BEGIN not in text:
            continue
        stripped = gwn.strip_generated(text)
        assert gwn.TOC_BEGIN not in stripped and "GENERATED PAGE" not in stripped, name
        assert gwn.strip_page_contents(text).count("\n") < text.count("\n"), name


# -- rendering and the rules ----------------------------------------------------------------------------


def test_a_page_with_many_second_level_headings_lists_only_them():
    text = long_page("X", 320, sections=gwn.TOC_SUBHEADINGS_BELOW, extra="### Sub one\n\n### Sub two")
    block = gwn.render_page_contents(text)
    assert block.startswith(gwn.TOC_BEGIN) and block.endswith(gwn.TOC_END)
    assert "[Section 1](#section-1)" in block and "Sub one" not in block


def test_a_page_with_few_second_level_headings_nests_the_third_level_under_its_parent():
    extra = "### Sub one\n\n### Sub two\n\n## Last\n\n#### Too deep"
    text = long_page("X", 320, sections=2, extra=extra)
    block = gwn.render_page_contents(text)
    assert gwn.TOC_SUBHEADINGS_BELOW > 3
    lines = block.splitlines()
    assert "- [Section 2](#section-2)" in lines
    assert lines.index("  - [Sub one](#sub-one)") == lines.index("- [Section 2](#section-2)") + 1
    assert "  - [Sub two](#sub-two)" in lines
    assert "- [Last](#last)" in lines
    assert "Too deep" not in block


def test_a_third_level_heading_with_no_second_level_parent_is_listed_at_the_top_level():
    text = "# P\n\n### Orphan\n\n## Later\n\n" + "filler\n" * 320
    block = gwn.render_page_contents(text)
    assert "- [Orphan](#orphan)" in block.splitlines()


def test_a_heading_with_markup_gets_clean_link_text_and_the_right_anchor():
    text = long_page("X", 320, sections=0, extra="## Using `nmap` & [a link](Other.md)\n\n## Plain [x]\n")
    block = gwn.render_page_contents(text)
    assert "- [Using `nmap` & a link](#using-nmap--a-link)" in block.splitlines()


def test_duplicate_headings_link_to_their_own_suffixed_anchor():
    text = long_page("X", 320, sections=0, extra="## Setup\n\n## Setup\n\n## Setup\n")
    block = gwn.render_page_contents(text)
    assert block.count("(#setup)") == 1 and "(#setup-1)" in block and "(#setup-2)" in block


def test_the_threshold_is_exclusive_and_counts_author_lines_only():
    at = long_page("X", gwn.TOC_MIN_LINES)
    over = long_page("X", gwn.TOC_MIN_LINES + 1)
    assert gwn.render_page_contents(at) is None
    assert gwn.render_page_contents(over) is not None
    # A page 295 lines long carries nav blocks of more than 5 lines and is still under the threshold.
    m, _ = small()
    nav = gwn.render_page_nav(m, "T3")
    page = gwn.apply_page_nav(long_page("T3", gwn.TOC_MIN_LINES - 5), nav)
    assert len(page.splitlines()) > gwn.TOC_MIN_LINES
    assert gwn.render_page_contents(gwn.strip_generated(page)) is None


def test_a_long_page_with_no_listable_heading_gets_no_block():
    assert gwn.render_page_contents("# Title\n\n" + "prose\n" * 320) is None


def test_apply_inserts_once_replaces_in_place_and_removes_when_none():
    m, _ = small()
    original = long_page("T3", 320)
    block = gwn.render_page_contents(original)
    done = gwn.apply_page_contents(original, block)
    assert done.count(gwn.TOC_BEGIN) == 1 and done.count(gwn.TOC_END) == 1
    assert gwn.apply_page_contents(done, block) == done  # idempotent
    assert gwn.strip_generated(done) == original  # only the block was added
    assert gwn.strip_page_contents(done) == original
    stale = done.replace("[Section 2](#section-2)", "[Section TWO](#section-2)")
    assert gwn.apply_page_contents(stale, block) == done
    assert gwn.apply_page_contents(done, None) == original
    # The navigation block the publish step adds goes above it, and the contents block survives the round trip.
    published_text = gwn.apply_page_nav(done, gwn.render_page_nav(m, "T3"))
    assert published_text.index(gwn.NAV_END.format(where="top")) < published_text.index(gwn.TOC_BEGIN)
    assert gwn.strip_page_nav(published_text) == done


def test_apply_refuses_a_page_with_a_broken_or_misplaced_marker():
    original = long_page("T3", 320)
    block = gwn.render_page_contents(original)
    done = gwn.apply_page_contents(original, block)
    with pytest.raises(ValueError, match="marker"):
        gwn.apply_page_contents(done.replace(gwn.TOC_END, ""), block)
    with pytest.raises(ValueError, match="marker"):
        gwn.apply_page_contents(done + block, block)
    with pytest.raises(ValueError, match="heading"):
        gwn.apply_page_contents("no heading here\n" * 3, block)  # no first-level heading to put the block after
    swapped = done.replace(gwn.TOC_BEGIN, "@@").replace(gwn.TOC_END, gwn.TOC_BEGIN).replace("@@", gwn.TOC_END)
    with pytest.raises(ValueError, match="before"):
        gwn.apply_page_contents(swapped, block)


def test_a_heading_inside_the_generated_nav_or_contents_text_does_not_change_the_list():
    # The list is built from author text only: the generated blocks cannot feed back into themselves.
    m, _ = small()
    original = long_page("T3", 320)
    done = gwn.apply_page_contents(gwn.apply_page_nav(original, gwn.render_page_nav(m, "T3")), gwn.render_page_contents(original))
    assert gwn.render_page_contents(gwn.strip_generated(done)) == gwn.render_page_contents(original)


# -- --check, the rewrite and the staleness cases ---------------------------------------------------------------


def run(tmp_path, *flags) -> int:
    return gwn.main(["--root", str(tmp_path), *flags])


def prepare(tmp_path, lines: int):
    m, texts, wiki = wired(tmp_path, lines)
    (wiki / "Home.md").write_text(f"# Home\n\n{gwn.HOME_BEGIN}\n{gwn.HOME_END}\n", encoding="utf-8")
    return m, texts, wiki


def test_check_fails_until_the_block_is_written_then_passes_and_a_rerun_changes_nothing(tmp_path):
    _, texts, wiki = prepare(tmp_path, 330)
    assert run(tmp_path, "--check") == 1
    assert run(tmp_path) == 0
    assert run(tmp_path, "--check") == 0
    page = wiki / "T3.md"
    first = {p.name: p.read_bytes() for p in wiki.iterdir() if p.is_file()}
    assert gwn.TOC_BEGIN in page.read_text(encoding="utf-8")
    assert gwn.TOC_BEGIN not in (wiki / "T4.md").read_text(encoding="utf-8")
    assert run(tmp_path) == 0
    assert {p.name: p.read_bytes() for p in wiki.iterdir() if p.is_file()} == first
    assert gwn.strip_generated(page.read_text(encoding="utf-8")) == texts["T3"]


def test_a_stale_block_fails_check_and_a_rewrite_repairs_it(tmp_path):
    _, _, wiki = prepare(tmp_path, 330)
    assert run(tmp_path) == 0
    page = wiki / "T3.md"
    good = page.read_text(encoding="utf-8")
    page.write_text(good.replace("[Section 3](#section-3)", "[Section THREE](#section-3)"), encoding="utf-8")
    assert run(tmp_path, "--check") == 1  # a hand edit inside the block
    page.write_text(good.replace("## Section 4", "## Section 4 renamed"), encoding="utf-8")
    assert run(tmp_path, "--check") == 1  # a heading changed, the list did not
    page.write_text(good + "\n## Added later\n", encoding="utf-8")
    assert run(tmp_path, "--check") == 1  # a heading added
    assert run(tmp_path) == 0
    assert run(tmp_path, "--check") == 0
    assert "(#added-later)" in page.read_text(encoding="utf-8")


def test_a_page_that_grows_over_the_threshold_gets_a_block_and_one_that_shrinks_loses_it(tmp_path):
    _, _, wiki = prepare(tmp_path, gwn.TOC_MIN_LINES)
    assert run(tmp_path) == 0
    page = wiki / "T3.md"
    assert gwn.TOC_BEGIN not in page.read_text(encoding="utf-8")
    page.write_text(page.read_text(encoding="utf-8") + "one more line\n", encoding="utf-8")
    assert run(tmp_path, "--check") == 1
    assert run(tmp_path) == 0
    assert gwn.TOC_BEGIN in page.read_text(encoding="utf-8")
    page.write_text(page.read_text(encoding="utf-8").replace("one more line\n", ""), encoding="utf-8")
    assert run(tmp_path, "--check") == 1  # the block is there but the page is back at the threshold
    assert run(tmp_path) == 0
    assert gwn.TOC_BEGIN not in page.read_text(encoding="utf-8")
    assert run(tmp_path, "--check") == 0


def test_the_pages_another_generator_writes_whole_get_no_contents_block(tmp_path):
    m, texts = small()
    m["pages"]["ref"].append({"page": "Status", "title": "Status", "audience": "everyone", "desc": "x"})
    m["pages"]["ref"].sort(key=lambda e: e["title"])
    generated = "<!-- GENERATED from elsewhere. -->\n\n# Status\n\n## One\n\n" + "row\n" * 400
    texts["Status"] = generated
    wiki = write_tree(tmp_path, m, texts)
    assert run(tmp_path) == 0
    assert (wiki / "Status.md").read_text(encoding="utf-8") == generated


# -- tests/wikitext.py -----------------------------------------------------------------------------------------


def test_page_text_strips_the_contents_block_and_the_navigation_blocks(tmp_path):
    m, _ = small()
    original = long_page("T3", 320)
    with_nav = gwn.apply_page_nav(original, gwn.render_page_nav(m, "T3"))
    done = gwn.apply_page_contents(with_nav, gwn.render_page_contents(original))
    path = tmp_path / "T3.md"
    path.write_text(done, encoding="utf-8")
    assert "(#section-1)" in done and "](T2.md)" in done
    seen = page_text(path)
    assert seen == original
    assert "(#section-1)" not in seen and "GENERATED PAGE" not in seen and "](T2.md)" not in seen


def test_page_text_leaves_a_page_without_blocks_alone(tmp_path):
    path = tmp_path / "Plain.md"
    path.write_text("# Plain\n\n[a](#plain) text\n", encoding="utf-8")
    assert page_text(path) == "# Plain\n\n[a](#plain) text\n"


def test_page_text_on_the_committed_wiki_never_shows_a_generated_marker():
    shown = 0
    for page in sorted(WIKI.glob("*.md")):
        seen = page_text(page)
        assert "GENERATED PAGE NAV" not in seen and "GENERATED PAGE CONTENTS" not in seen, page.name
        shown += gwn.TOC_BEGIN in page.read_text(encoding="utf-8")
    assert shown >= 60


def test_strip_generated_handles_a_block_at_either_end_of_the_page():
    block = f"{gwn.TOC_BEGIN}\n{gwn.TOC_LABEL}\n\n- [A](#a)\n{gwn.TOC_END}"
    assert gwn.strip_page_contents(f"# T\n\n{block}\n\nbody\n") == "# T\n\nbody\n"
    assert gwn.strip_page_contents(f"# T\n\nbody\n\n{block}\n") == "# T\n\nbody\n"
    assert gwn.strip_page_contents("# T\n\nbody\n") == "# T\n\nbody\n"
