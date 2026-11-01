# SPDX-License-Identifier: Apache-2.0
"""The generated navigation blocks on every wiki page (issue #417).

What is proved:
- every page that should carry the blocks has exactly one top and one bottom block, in the right places, and
  Home, Contents and the pages another generator writes whole have none;
- the blocks are what the generator renders, so --check fails when one goes stale and running the generator
  twice changes nothing;
- previous and next agree (a page's next has it as previous), the first and last pages have one neighbor, and
  a group with no reading order has none;
- related targets exist, are not the page itself and do not repeat; the fallback rule is deterministic and
  never repeats a neighbor;
- the generator only ever adds the two blocks: stripping them gives the original page back, and a banner stays
  where it was;
- the checks bite: hostile manifests and hand-edited blocks are refused.
"""

import copy
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import gen_wiki_nav as gwn

WIKI = ROOT / "docs" / "wiki"
PAGE_LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
PREV = re.compile(r"Previous: \[[^\]]*\]\(([A-Za-z0-9_-]+)\.md\)")
NEXT = re.compile(r"Next: \[[^\]]*\]\(([A-Za-z0-9_-]+)\.md\)")


def manifest() -> dict:
    return gwn.read_manifest(ROOT)


def text_of(name: str) -> str:
    return (WIKI / f"{name}.md").read_text(encoding="utf-8")


def pages_with_nav() -> list[str]:
    return sorted(n for n in gwn.wiki_pages(ROOT) if gwn.has_page_nav(n, text_of(n)))


def block(text: str, where: str) -> str:
    begin, end = gwn.NAV_BEGIN.format(where=where), gwn.NAV_END.format(where=where)
    assert text.count(begin) == 1 and text.count(end) == 1, where
    return text.split(begin, 1)[1].split(end, 1)[0]


def small() -> tuple[dict, dict[str, str]]:
    """A manifest with a three-page numbered track, a sorted group and an unordered group, and page texts for it."""
    m = {
        "groups": [
            {"id": "start", "title": "Start here", "order": "curated"},
            {"id": "core", "title": "Core path", "order": "curated", "numbered": True, "open": True},
            {"id": "trk", "title": "Track X", "order": "curated", "numbered": True, "track": True},
            {"id": "loose", "title": "Loose pages", "order": "curated"},
            {"id": "ref", "title": "Reference", "order": "sorted"},
        ],
        "pages": {
            "start": [
                {"page": "Home", "title": "Home", "audience": "everyone", "desc": "The front door."},
                {"page": "Contents", "title": "Contents", "audience": "everyone", "desc": "Index."},
            ],
            "core": [{"page": "One", "title": "One", "audience": "newcomer", "desc": "The first page."}],
            "trk": [
                {"page": "T1", "title": "Tee one", "audience": "learner", "desc": "x", "subgroup": "Early"},
                {"page": "T2", "title": "Tee two", "audience": "learner", "desc": "x", "subgroup": "Early"},
                {"page": "T3", "title": "Tee three", "audience": "learner", "desc": "x", "subgroup": "Late"},
                {"page": "T4", "title": "Tee four", "audience": "learner", "desc": "x", "subgroup": "Late"},
                {"page": "T5", "title": "Tee five", "audience": "learner", "desc": "x"},
            ],
            "loose": [
                {"page": "L1", "title": "Loose one", "audience": "learner", "desc": "x"},
                {"page": "L2", "title": "Loose two", "audience": "learner", "desc": "x"},
            ],
            "ref": [
                {"page": "Zed", "title": "Zed", "audience": "everyone", "desc": "x"},
                {"page": "Apple", "title": "Apple", "audience": "everyone", "desc": "x"},
            ],
        },
    }
    m["pages"]["ref"].sort(key=lambda e: e["title"])
    texts = {
        n: f"# {n}\n\n> **Banner.**\n\n> Unfamiliar word? See the Glossary.\n\nBody of {n}.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
        for n in ("One", "T1", "T2", "T3", "T4", "T5", "L1", "L2", "Zed", "Apple")
    }
    texts["Home"] = f"# Home\n\n{gwn.HOME_BEGIN}\n{gwn.HOME_END}\n"
    texts["Contents"] = "# Contents\n"
    return m, texts


def write_tree(root: Path, m: dict, texts: dict[str, str]) -> Path:
    wiki = root / "docs" / "wiki"
    wiki.mkdir(parents=True)
    (wiki / "_nav.yaml").write_text(yaml.safe_dump(m), encoding="utf-8")
    for name, text in texts.items():
        (wiki / f"{name}.md").write_text(text, encoding="utf-8")
    return wiki


# -- the committed wiki ------------------------------------------------------------------------


def test_every_page_that_should_have_the_blocks_has_exactly_one_top_and_one_bottom():
    names = pages_with_nav()
    assert len(names) >= 140, f"the guard collected only {len(names)} pages"
    for name in names:
        text = text_of(name)
        for where in gwn.NAV_PLACES:
            assert text.count(gwn.NAV_BEGIN.format(where=where)) == 1, f"{name}: {where} BEGIN"
            assert text.count(gwn.NAV_END.format(where=where)) == 1, f"{name}: {where} END"
        assert text.index(gwn.NAV_BEGIN.format(where="top")) < text.index(gwn.NAV_BEGIN.format(where="bottom")), name
        assert text.rstrip("\n").endswith(gwn.NAV_END.format(where="bottom")), f"{name}: the bottom block is not last"


def test_home_contents_and_the_pages_other_generators_write_have_no_block():
    exempt = sorted(set(gwn.wiki_pages(ROOT)) - set(pages_with_nav()))
    assert {"Home", "Contents"} <= set(exempt)
    assert exempt == ["Contents", "Home", "Project-Status", "Repository-Growth", "Settings-Reference"]
    for name in exempt:
        assert "GENERATED PAGE NAV" not in text_of(name), name


def test_the_committed_blocks_are_what_the_generator_renders_and_a_second_run_changes_nothing():
    m = manifest()
    for name in pages_with_nav():
        text = text_of(name)
        assert gwn.apply_page_nav(text, gwn.render_page_nav(m, name)) == text, name
        again = gwn.apply_page_nav(text, gwn.render_page_nav(copy.deepcopy(m), name))
        assert again == text, f"{name}: not idempotent"


def test_stripping_the_blocks_and_inserting_them_again_gives_the_same_page():
    from wikitext import page_text

    m = manifest()
    for name in pages_with_nav():
        stripped = page_text(WIKI / f"{name}.md")
        assert "GENERATED PAGE NAV" not in stripped, name
        assert gwn.apply_page_nav(stripped, gwn.render_page_nav(m, name)) == text_of(name), name


def test_previous_and_next_agree_within_every_group_with_a_reading_order():
    m = manifest()
    prev, nxt, ordered_groups = {}, {}, 0
    for name in pages_with_nav():
        top = block(text_of(name), "top")
        found_p, found_n = PREV.findall(top), NEXT.findall(top)
        assert len(found_p) <= 1 and len(found_n) <= 1, name
        prev[name], nxt[name] = (found_p or [None])[0], (found_n or [None])[0]
        assert block(text_of(name), "bottom").count("Previous:") == len(found_p), name
    for g in gwn.groups_of(m):
        names = [e["page"] for e in gwn.entries(m, g["id"])]
        if not gwn.has_reading_order(g):
            assert all(prev.get(n) is None and nxt.get(n) is None for n in names), g["id"]
            continue
        ordered_groups += 1
        # The order includes pages that carry no block themselves (the status and growth pages): they are still
        # neighbors, so they are linked, and only the pages that carry a block are checked.
        for i, n in enumerate(names):
            if n in prev:
                assert nxt[n] == (names[i + 1] if i + 1 < len(names) else None), n
                assert prev[n] == (names[i - 1] if i else None), n
        if names[-1] in prev:
            assert nxt[names[-1]] is None, g["id"]
        if names[0] in prev:
            assert prev[names[0]] is None, g["id"]
    assert ordered_groups >= 7, "the guard saw too few groups with a reading order"


def test_a_page_next_has_it_as_previous():
    pairs = 0
    for name in pages_with_nav():
        following = NEXT.findall(block(text_of(name), "top"))
        if following and following[0] in pages_with_nav():  # a followed page that carries no block has no Previous to check
            assert PREV.findall(block(text_of(following[0]), "top")) == [name], name
            pairs += 1
    assert pairs >= 100


def test_the_breadcrumb_names_home_the_group_and_the_page_without_linking_the_page():
    m = manifest()
    homes = {e["page"]: (g, e) for g in gwn.groups_of(m) for e in gwn.entries(m, g["id"])}
    for name in pages_with_nav():
        g, e = homes[name]
        top = block(text_of(name), "top")
        assert f"[Home](Home.md) > [{g['title']}](Contents.md#{gwn.slug(g['title'])}) > {e['title']}\n" in top, name
        assert f"]({name}.md)" not in top, f"{name}: links itself"


def test_only_the_heading_and_leading_quote_banners_come_before_the_top_block():
    seen = 0
    for name in pages_with_nav():
        text = text_of(name)
        head = text.split(gwn.NAV_BEGIN.format(where="top"), 1)[0].splitlines()
        assert head[0].startswith("# "), name
        assert all(not line.strip() or line.startswith(">") for line in head[1:]), f"{name}: prose before the top block"
        seen += sum(1 for line in head if line.startswith("> **"))
    assert seen >= 20, "the guard found too few status banners above the block"


def test_every_related_target_exists_and_is_not_the_page_itself():
    m = manifest()
    names = set(gwn.all_page_names(m))
    shown = 0
    for name in pages_with_nav():
        part = block(text_of(name), "bottom").split("Related pages:", 1)
        if len(part) == 1:
            continue
        targets = PAGE_LINK.findall(part[1])
        shown += 1
        assert targets and len(targets) == len(set(targets)) <= gwn.RELATED_MAX, name
        assert name not in targets and set(targets) <= names, name
    assert shown >= 140


def test_the_pages_the_brief_names_have_a_hand_chosen_related_list():
    m = manifest()
    chosen = {e["page"]: e["related"] for g in ("privacy", "grc") for e in m["pages"][g] if "related" in e}
    for gid in ("privacy", "grc"):
        for e in m["pages"][gid]:
            assert e["page"] in chosen, f"{e['page']} has no related list"
            assert gwn.RELATED_MIN <= len(chosen[e["page"]]) <= gwn.RELATED_MAX
    assert len(chosen) == 24
    # Jumping between sections works: the lists cross the track boundary both ways.
    by_group = {e["page"]: gid for gid, pages in m["pages"].items() for e in pages}
    assert any(by_group[r] != "privacy" for p, rel in chosen.items() if by_group[p] == "privacy" for r in rel)
    assert any(by_group[r] != "grc" for p, rel in chosen.items() if by_group[p] == "grc" for r in rel)
    assert any(by_group[r] == "grc" for p, rel in chosen.items() if by_group[p] == "privacy" for r in rel)
    assert any(by_group[r] == "privacy" for p, rel in chosen.items() if by_group[p] == "grc" for r in rel)


def test_the_continuity_pages_link_each_other_and_the_cia_triad():
    m = manifest()
    related = {e["page"]: e["related"] for e in m["pages"]["grc"] if "related" in e}
    raid = next(p for p in related if p.startswith("RAID-Levels"))
    bcp = next(p for p in related if p.startswith("Business-Continuity"))
    cia = next(p for p in related if p.startswith("The-CIA-Triad"))
    backups = [p for p in related if p.startswith("Backups-")]
    assert len(backups) == 2
    assert {bcp, *backups} <= set(related[raid]) and cia in related[raid]
    assert {raid, *backups} <= set(related[bcp])
    assert bcp in related[backups[0]] and bcp in related[backups[1]]


# -- the fallback rule and the rendering -------------------------------------------------------


def test_the_fallback_is_the_nearest_pages_of_the_same_subgroup_first_and_never_a_neighbor():
    m, _ = small()
    # T2: previous T1, next T3 are shown beside it; the other subgroup pages follow by distance.
    assert gwn.related_for(m, "T2") == ["T4", "T5"]
    # T3: subgroup Late, neighbors T2 and T4 are left out; same-subgroup candidates are none, so the rest by distance.
    assert gwn.related_for(m, "T3") == ["T1", "T5"]
    # T1 is first: no previous, so only T2 is a neighbor.
    assert gwn.related_for(m, "T1") == ["T3", "T4", "T5"]
    for p in ("T1", "T2", "T3", "T4", "T5"):
        got = gwn.related_for(m, p)
        assert p not in got and len(got) == len(set(got)) <= gwn.RELATED_FALLBACK


def test_the_fallback_in_a_group_without_a_reading_order_keeps_every_other_page():
    m, _ = small()
    assert gwn.related_for(m, "L1") == ["L2"]
    assert gwn.related_for(m, "One") == []  # a group of one page has none
    assert "Related pages" not in gwn.render_page_nav(m, "One")["bottom"]


def test_a_related_list_replaces_the_fallback_in_the_order_written():
    m, _ = small()
    next(e for e in m["pages"]["trk"] if e["page"] == "T2")["related"] = ["Zed", "One", "L1"]
    assert gwn.related_for(m, "T2") == ["Zed", "One", "L1"]
    bottom = gwn.render_page_nav(m, "T2")["bottom"]
    assert bottom.index("(Zed.md)") < bottom.index("(One.md)") < bottom.index("(L1.md)")


def test_first_and_last_pages_have_one_neighbor_and_an_unordered_group_has_none():
    m, _ = small()
    first, last, mid = (gwn.render_page_nav(m, p)["top"] for p in ("T1", "T5", "T3"))
    assert "Previous:" not in first and "Next: [Tee two](T2.md)" in first
    assert "Next:" not in last and "Previous: [Tee four](T4.md)" in last
    assert "Previous: [Tee two](T2.md) / Next: [Tee four](T4.md)" in mid
    loose = gwn.render_page_nav(m, "L1")["top"]
    assert "Previous:" not in loose and "Next:" not in loose and "Loose one" in loose
    only = gwn.render_page_nav(m, "One")["top"]
    assert "Previous:" not in only and "Next:" not in only


def test_a_sorted_group_goes_in_title_order():
    m, _ = small()
    assert "Next: [Zed](Zed.md)" in gwn.render_page_nav(m, "Apple")["top"]
    assert "Previous: [Apple](Apple.md)" in gwn.render_page_nav(m, "Zed")["top"]


def test_the_bottom_block_lists_the_track_by_subgroup_and_does_not_link_the_page_itself():
    m, _ = small()
    bottom = gwn.render_page_nav(m, "T3")["bottom"]
    assert "- Early: [Tee one](T1.md) / [Tee two](T2.md)" in bottom
    assert "- Late: **Tee three** / [Tee four](T4.md)" in bottom
    assert "- Also here: [Tee five](T5.md)" in bottom
    assert "(T3.md)" not in bottom
    assert "In this track:" in bottom and "In this group:" not in bottom
    assert "In this group:" in gwn.render_page_nav(m, "L1")["bottom"]


# -- inserting, rewriting and the checks bite ---------------------------------------------------


def test_the_blocks_go_after_the_banners_and_stripping_them_gives_the_page_back():
    m, texts = small()
    for name in ("T2", "L1"):
        original = texts[name]
        done = gwn.apply_page_nav(original, gwn.render_page_nav(m, name))
        head = done.split(gwn.NAV_BEGIN.format(where="top"), 1)[0]
        assert head == f"# {name}\n\n> **Banner.**\n\n> Unfamiliar word? See the Glossary.\n\n"
        assert done.rstrip("\n").endswith(gwn.NAV_END.format(where="bottom"))
        assert gwn.strip_page_nav(done) == original
        assert gwn.apply_page_nav(done, gwn.render_page_nav(m, name)) == done


@pytest.mark.parametrize(
    "original",
    [
        "# Plain\n\nProse straight after the heading.\n\n## Section\n\ntext\n",
        "# Plain\n\n> **Banner only.**\n\nProse.\n",
        "# Plain\n",
        "# Plain\n\n> only a quote\n",
        "# Plain\nprose with no blank line\n",
    ],
)
def test_insertion_handles_every_page_shape_and_only_adds_the_two_blocks(original):
    m, _ = small()
    done = gwn.apply_page_nav(original, gwn.render_page_nav(m, "T2"))
    assert done.count("BEGIN GENERATED PAGE NAV") == 2 and done.endswith("\n")
    assert gwn.strip_page_nav(done).split() == original.split()  # same words in the same order
    for line in original.splitlines():
        assert line in done.splitlines()


def test_a_page_with_a_missing_or_repeated_marker_is_refused():
    m, texts = small()
    blocks = gwn.render_page_nav(m, "T2")
    done = gwn.apply_page_nav(texts["T2"], blocks)
    with pytest.raises(ValueError, match="marker"):
        gwn.apply_page_nav(done.replace(gwn.NAV_END.format(where="top"), ""), blocks)
    with pytest.raises(ValueError, match="marker"):
        gwn.apply_page_nav(done + blocks["top"], blocks)
    with pytest.raises(ValueError, match="heading"):
        gwn.apply_page_nav("no heading here\n", blocks)
    swapped = done.replace("PAGE NAV top", "PAGE NAV TMP").replace("PAGE NAV bottom", "PAGE NAV top").replace("PAGE NAV TMP", "PAGE NAV bottom")
    with pytest.raises(ValueError, match="top|before"):
        gwn.apply_page_nav(swapped, blocks)


def test_a_stale_block_fails_check_and_a_rerun_repairs_it_without_touching_the_page(tmp_path):
    m, texts = small()
    wiki = write_tree(tmp_path, m, texts)
    (wiki / "Home.md").write_text(f"# Home\n\n{gwn.HOME_BEGIN}\n{gwn.HOME_END}\n", encoding="utf-8")
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 1  # no blocks yet: stale
    assert gwn.main(["--root", str(tmp_path)]) == 0
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 0
    page = wiki / "T3.md"
    good = page.read_text(encoding="utf-8")
    assert good.count("GENERATED PAGE NAV top") == 2  # BEGIN and END
    # A hand edit inside a block, a block removed and a block moved are each refused.
    page.write_text(good.replace("Tee two", "Tee TWO"), encoding="utf-8")
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 1
    page.write_text(good.replace(gwn.NAV_END.format(where="bottom"), ""), encoding="utf-8")
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 1
    # Editing the manifest (a title) makes every block that shows it stale.
    page.write_text(good, encoding="utf-8")
    m2 = copy.deepcopy(m)
    next(e for e in m2["pages"]["trk"] if e["page"] == "T2")["title"] = "Tee second"
    (wiki / "_nav.yaml").write_text(yaml.safe_dump(m2), encoding="utf-8")
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 1
    # The rewrite repairs it and keeps the page body byte for byte.
    assert gwn.main(["--root", str(tmp_path)]) == 0
    assert gwn.main(["--root", str(tmp_path), "--check"]) == 0
    assert gwn.strip_page_nav(page.read_text(encoding="utf-8")) == texts["T3"]
    assert "Tee second" in page.read_text(encoding="utf-8")


def test_running_the_generator_twice_changes_nothing(tmp_path):
    m, texts = small()
    wiki = write_tree(tmp_path, m, texts)
    assert gwn.main(["--root", str(tmp_path)]) == 0
    first = {p.name: p.read_bytes() for p in wiki.iterdir() if p.is_file()}
    assert gwn.main(["--root", str(tmp_path)]) == 0
    assert {p.name: p.read_bytes() for p in wiki.iterdir() if p.is_file()} == first
    assert gwn.HOME_BEGIN.encode() in first["Home.md"]
    assert b"GENERATED PAGE NAV" not in first["Home.md"] and b"GENERATED PAGE NAV" not in first["Contents.md"]


def test_a_page_another_generator_writes_whole_is_left_alone(tmp_path):
    m, texts = small()
    m["pages"]["ref"].append({"page": "Status", "title": "Status", "audience": "everyone", "desc": "x"})
    m["pages"]["ref"].sort(key=lambda e: e["title"])
    generated = "<!-- GENERATED from elsewhere. -->\n\n# Status\n\nrows\n"
    texts["Status"] = generated
    wiki = write_tree(tmp_path, m, texts)
    assert gwn.main(["--root", str(tmp_path)]) == 0
    assert (wiki / "Status.md").read_text(encoding="utf-8") == generated
    assert "(Status.md)" in gwn.render_page_nav(m, "Apple")["top"]  # but it is still a neighbor


def test_a_page_that_cannot_take_the_blocks_stops_the_run_before_anything_is_written(tmp_path, capsys):
    m, texts = small()
    texts["T4"] = "no heading at all\n"
    wiki = write_tree(tmp_path, m, texts)
    before = {p.name: p.read_bytes() for p in wiki.iterdir() if p.is_file()}
    assert gwn.main(["--root", str(tmp_path)]) == 1
    assert "heading" in capsys.readouterr().err
    assert {p.name: p.read_bytes() for p in wiki.iterdir() if p.is_file()} == before


def test_strip_page_nav_removes_exactly_the_blocks():
    m, texts = small()
    done = gwn.apply_page_nav(texts["T1"], gwn.render_page_nav(m, "T1"))
    assert "GENERATED PAGE NAV" in done and "](T2.md)" in done
    assert gwn.strip_page_nav(done) == texts["T1"]
    assert gwn.strip_page_nav(texts["T1"]) == texts["T1"]
    assert "](T2.md)" not in gwn.strip_page_nav(done)


# -- the related field is validated --------------------------------------------------------------


def with_related(related) -> dict:
    m, _ = small()
    next(e for e in m["pages"]["trk"] if e["page"] == "T2")["related"] = related
    return m


PAGES = {"One", "T1", "T2", "T3", "T4", "T5", "L1", "L2", "Zed", "Apple", "Home", "Contents"}


def test_the_small_manifest_is_valid_with_a_good_related_list():
    assert gwn.validate(small()[0], PAGES) == []
    assert gwn.validate(with_related(["T1", "T3", "Zed"]), PAGES) == []
    assert gwn.validate(with_related(["T1", "T3", "T4", "T5", "Zed", "Apple"]), PAGES) == []


@pytest.mark.parametrize(
    ("related", "needle"),
    [
        (["T1", "T3", "Nowhere"], "'Nowhere' is not a page"),
        (["T1", "T2", "T3"], "lists the page itself"),
        (["T1", "T3", "T3"], "lists 'T3' twice"),
        (["T1", "T3"], "needs 3 to 6"),
        (["T1", "T3", "T4", "T5", "Zed", "Apple", "L1"], "needs 3 to 6"),
        ("T1", "must be a list"),
        ([1, 2, 3], "must be a list"),
    ],
)
def test_a_bad_related_list_is_refused(related, needle):
    assert any(needle in p for p in gwn.validate(with_related(related), PAGES))


def test_a_related_list_cannot_name_a_special_or_missing_page():
    problems = gwn.validate(with_related(["T1", "_Sidebar", "T3"]), PAGES)
    assert any("'_Sidebar' is not a page" in p for p in problems)
