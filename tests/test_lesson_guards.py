# SPDX-License-Identifier: Apache-2.0
"""One data-driven guard suite for every lesson page (issue #525).

It replaces the copy-pasted per-lesson guard files. Two layers:

1. GENERIC checks, run on every lesson page the discovery rule finds (see `lesson_pages`): no em dash, no address
   outside the page's allowlist, no identifier or private key (scripts/identifier_check.py), a status banner that
   says what was and was not run, a claims register whose rows all carry a known status, link targets and in-page
   anchors that exist, glossary anchors that resolve, registration in the navigation files, sibling lessons linked
   rather than named in plain text, and the UNTESTED or **est.** marks where the page says something was not run.
2. PER-LESSON rows in tests/lesson_guard_data.py (`PAGES`): the thresholds and the unique requirements the old
   per-lesson files held, as data. A row is a dict; `check_row` below is the only code that reads them.

Every failure names the page and the rule. Each guard has a negative case (`test_guard_bites_*`) proving it fires.
American English is guarded by tests/test_american_english.py and is not repeated here.
"""

from __future__ import annotations

import functools
import importlib.util
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from lesson_guard_data import DEFAULTS, NO_REGISTER, PAGES
from wikitext import gen_wiki_nav, page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"

_spec = importlib.util.spec_from_file_location("identifier_check", ROOT / "scripts" / "identifier_check.py")
ic = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("identifier_check", ic)
_spec.loader.exec_module(ic)

FENCE = re.compile(r"^[ ]*```(\w*)\n(.*?)^[ ]*```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")
OWN_ANCHOR = re.compile(r"\]\(#([^)\s]+)\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
BANNER = re.compile(r"^> \*\*Status:.*?(?=\n\n)", re.MULTILINE | re.DOTALL)
HONEST = re.compile(
    r"not run|nothing run|nothing was run|no command|was run|were run|run once|did not|not built|not applied|has not been|have not been|not seen to work|not verified|no \w+ was|not installed|not tested|written from reading",
    re.IGNORECASE,
)
NOT_RUN = re.compile(r"\*\*Not run:\*\*|nothing run|not run|did not run|no command on this page was run|has not been run|have not been run|not built", re.IGNORECASE)
MARKS = ("**est.**", "UNTESTED", "**Untested", "**not verified**", "Not verified, plainly")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
SIBLING_WORDING = ("plain text until", "They are not linked here")
NAV_PLACES = ("Contents.md", "_Sidebar.md", "Reading-Order.md")


# -- discovery ---------------------------------------------------------------------------------------------


@functools.cache
def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@functools.cache
def nav_entries() -> dict[str, str]:
    """page name -> its _nav.yaml line, for every entry that carries a `status`."""
    found = {}
    for line in read(WIKI / "_nav.yaml").splitlines():
        m = re.search(r"\bpage: ([^,]+),", line)
        if m and re.search(r'\bstatus: "', line):
            found[m.group(1)] = line
    return found


def lesson_pages() -> list[str]:
    """The discovery rule: a page is a lesson when its _nav.yaml entry carries a `status` AND the page has a
    `## Claims register` section. Those two together are what every old per-lesson file guarded; the status-only
    pages without a register (the cloud-provider and telemetry pages) are not lessons of this form."""
    names = []
    for name in nav_entries():
        page = WIKI / f"{name}.md"
        if page.exists() and "## Claims register" in read(page):
            names.append(name)
    return sorted(names)


LESSONS = lesson_pages()


def cfg(name: str) -> dict:
    return {**DEFAULTS, **PAGES.get(name, {}).get("config", {})}


@functools.cache
def text(name: str) -> str:
    return page_text(WIKI / f"{name}.md")


# -- helpers (each one has a negative case below) ------------------------------------------------------------


def register_rows(body: str) -> list[list[str]]:
    reg = body.split("## Claims register")[1]
    nxt = re.search(r"^## ", reg, re.MULTILINE)
    reg = reg[: nxt.start()] if nxt else reg
    rows = [line for line in reg.splitlines() if line.startswith("|") and not re.match(r"^\|[\s:|-]+\|?$", line)]
    return [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows[1:]]


def rows_with_bad_status(body: str, words: tuple[str, ...]) -> list[str]:
    bad = []
    for r in register_rows(body):
        status = r[-1] if len(r) >= 3 else ""
        if not status or not any(w in status for w in words):
            bad.append(r[0][:60])
    return bad


def addresses_outside(body: str, allow: tuple[str, ...]) -> list[str]:
    return sorted({a for a in ADDR.findall(body) if not any(re.fullmatch(p, a) for p in allow)})


def dead_links(body: str) -> list[str]:
    return sorted({t for t in LINK.findall(body) if not (WIKI / f"{t}.md").exists()})


def dead_own_anchors(body: str) -> list[str]:
    heads = {a for _, _, a in gen_wiki_nav.page_headings(body)}
    return sorted({a for a in OWN_ANCHOR.findall(body) if a not in heads})


def glossary_anchors(name: str) -> set[str]:
    found: set[str] = set()
    for line in read(WIKI / "Glossary.md").splitlines():
        found.update(re.findall(rf"{re.escape(name)}\.md#([a-z0-9_-]+)", line))
    return found


def glossary_rows(name: str) -> int:
    return sum(1 for line in read(WIKI / "Glossary.md").splitlines() if f"{name}.md" in line)


# The full identifier scan (every pattern, every tracked file) is the repository gate `identifier_check.py --root .`,
# which already covers these pages; running every pattern again per page would double its cost. This suite reuses the
# gate's own compiled patterns and allowlist for the kinds that are a secret and not just an identifier.
SECRET_KINDS = ("AWS access key id", "Azure subscription or tenant id")


def identifier_findings(body: str) -> list[str]:
    kinds = [kind for kind, rx in ic.PATTERNS if kind in SECRET_KINDS for m in rx.finditer(body) if not ic.is_allowed(m.group("v"))]
    if PRIVATE_KEY.search(body):
        kinds.append("private key block")
    return kinds


def banner_of(body: str) -> str:
    m = BANNER.search(body)
    return m.group(0) if m else ""


def strip_generated_comment_blocks(body: str) -> str:
    return re.sub(r"<!-- BEGIN GENERATED .*?<!-- END GENERATED [^>]*-->", "", body, flags=re.DOTALL)


def blocks(body: str, tag: str) -> list[str]:
    return [textwrap.dedent(b) for t, b in FENCE.findall(body) if t == tag]


def fail(name: str, rule: str, detail: object) -> str:
    return f"[{name}] rule '{rule}' failed: {detail}"


# -- the generic checks ----------------------------------------------------------------------------------------


def test_discovery_finds_every_page_the_old_files_guarded():
    # the pages the deleted per-lesson files named; a lesson that stops being discovered must fail loudly
    assert len(LESSONS) >= 50, f"discovery collected only {len(LESSONS)} lesson pages"
    missing = sorted(set(PAGES) - set(LESSONS))
    assert not missing, f"pages with guard rows that discovery no longer finds (status or claims register gone?): {missing}"


def test_every_status_page_is_a_lesson_or_listed_as_having_no_register():
    for name in nav_entries():
        if name in LESSONS:
            assert name not in NO_REGISTER, f"[{name}] rule 'discovery': now has a claims register; remove it from NO_REGISTER in tests/lesson_guard_data.py"
        else:
            assert name in NO_REGISTER, (
                f"[{name}] rule 'discovery': carries a status in _nav.yaml but has no '## Claims register'. "
                "A lesson that lost its register must get it back; a new page without one goes in NO_REGISTER in tests/lesson_guard_data.py"
            )
    assert not [n for n in NO_REGISTER if n not in nav_entries()], "NO_REGISTER names a page that no longer carries a status"


@pytest.mark.parametrize("name", LESSONS)
def test_page_title_and_no_em_dash(name):
    body = text(name)
    assert body.startswith("# "), fail(name, "title", "the page does not start with a level-1 heading")
    assert "—" not in body, fail(name, "no em dash", f"em dash at line {body[: body.index('—')].count(chr(10)) + 1}")


@pytest.mark.parametrize("name", LESSONS)
def test_page_addresses_are_documented_placeholders_only(name):
    body = text(name)
    c = cfg(name)
    exact = "addresses_allow" in PAGES.get(name, {}).get("config", {})  # an exact list replaces the shared defaults
    allow = tuple(c["addresses_allow"]) if exact else tuple(c["addresses_default"]) + tuple(c.get("addresses_extra", ()))
    found = addresses_outside(body, allow)
    assert not found, fail(name, "no addresses beyond the page's allowlist", found)
    for needed in c.get("addresses_require", ()):
        assert needed in ADDR.findall(body), fail(name, "address guard collected nothing", needed)


@pytest.mark.parametrize("name", LESSONS)
def test_page_has_no_identifier_or_private_key(name):
    kinds = identifier_findings(text(name))
    assert not kinds, fail(name, "no cloud identifier, key id or private key (scripts/identifier_check.py)", kinds)


@pytest.mark.parametrize("name", LESSONS)
def test_page_status_banner_says_what_was_and_was_not_run(name):
    body = text(name)
    banner = banner_of(body)
    nav_status = re.search(r'\bstatus: "([^"]*)"', nav_entries()[name]).group(1)
    assert banner, fail(name, "status banner", "no '> **Status:' blockquote")
    assert DATE.search(banner) or DATE.search(body[:3000]), fail(name, "status banner is dated", "no date near the banner")
    assert HONEST.search(banner), fail(name, "status banner says what was or was not run", banner[:120])
    if nav_status == "draft":
        assert "unverified draft" in banner, fail(name, "draft banner", "nav says draft but the banner does not say 'unverified draft'")
    assert NOT_RUN.search(body[:6000]) or "run" in banner.lower(), fail(name, "says what was not run", "no 'Not run' statement near the top")


@pytest.mark.parametrize("name", LESSONS)
def test_page_marks_what_was_not_run(name):
    body = text(name)
    if NOT_RUN.search(banner_of(body)) or "**Not run:**" in body:
        assert any(m in body for m in MARKS), fail(name, "an UNTESTED / **est.** / not-verified mark", "the page says something was not run but carries no mark")


@pytest.mark.parametrize("name", LESSONS)
def test_page_claims_register_rows_all_have_a_known_status(name):
    body = text(name)
    c = cfg(name)
    rows = register_rows(body)
    assert len(rows) >= c["min_register_rows"], fail(name, "claims register size", f"{len(rows)} rows, expected at least {c['min_register_rows']}")
    exact = "status_words" in PAGES.get(name, {}).get("config", {})  # an exact list replaces the shared vocabulary
    words = tuple(c["status_words"]) if exact else tuple(c["status_words"]) + tuple(c.get("status_extra", ()))
    bad = rows_with_bad_status(body, words)
    assert not bad, fail(name, f"claims register status in {words}", bad)


@pytest.mark.parametrize("name", LESSONS)
def test_page_links_and_anchors_resolve(name):
    body = text(name)
    c = cfg(name)
    links = set(LINK.findall(body))
    assert len(links) >= c["min_links"], fail(name, "link guard collected too few links", f"{len(links)} < {c['min_links']}")
    assert not dead_links(body), fail(name, "every linked wiki page exists", dead_links(body))
    assert not dead_own_anchors(body), fail(name, "every in-page anchor points at a heading", dead_own_anchors(body))
    for needed in c.get("must_link", ()):
        assert needed in links, fail(name, "required link present", needed)
    for prefix in c.get("must_link_prefix", ()):
        hits = [t for t in set(LINK.findall(strip_generated_comment_blocks(body))) if t.startswith(prefix)]
        assert hits, fail(name, "sibling lesson is linked, not named in plain text", prefix)
        assert all((WIKI / f"{t}.md").exists() for t in hits), fail(name, "sibling link target exists", prefix)


@pytest.mark.parametrize("name", LESSONS)
def test_page_does_not_say_siblings_are_plain_text(name):
    body = strip_generated_comment_blocks(text(name))
    found = [w for w in SIBLING_WORDING if w in body]
    assert not found, fail(name, "no 'plain text until' sibling wording", found)


@pytest.mark.parametrize("name", LESSONS)
def test_page_is_registered_and_glossary_anchors_resolve(name):
    c = cfg(name)
    line = nav_entries()[name]
    for extra in c.get("nav_contains", ()):
        assert extra in line, fail(name, "nav entry carries", extra)
    for special in NAV_PLACES:
        if special in c.get("nav_places_skip", ()):
            continue
        assert f"{name}.md" in read(WIKI / special), fail(name, "registered in navigation file", special)
    assert glossary_rows(name) >= c["min_glossary_rows"], fail(name, "glossary rows for the new terms", f"{glossary_rows(name)} < {c['min_glossary_rows']}")
    anchors = glossary_anchors(name)
    if c["min_glossary_rows"] > 0:
        assert anchors, fail(name, "glossary guard collected nothing", "no Glossary.md row links an anchor of this page")
    heads = {a for _, _, a in gen_wiki_nav.page_headings(text(name))}
    assert anchors <= heads, fail(name, "glossary anchors resolve", sorted(anchors - heads))


# -- the generic guards bite (negative cases) -------------------------------------------------------------------


REGISTER_BAD = "## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | maybe |\n| Z | y |  |\n"


def test_guard_bites_register_status():
    assert rows_with_bad_status(REGISTER_BAD, ("Read",)) == ["X", "Z"]
    assert rows_with_bad_status("## Claims register\n\n| Claim | Source | Status |\n|---|---|---|\n| X | y | Read |\n", ("Read",)) == []


def test_guard_bites_addresses():
    assert addresses_outside("ping 192.0.2.7", ()) == ["192.0.2.7"]
    assert addresses_outside("ping 127.0.0.1", (r"127\.0\.0\.1",)) == []
    assert addresses_outside("ping 127.0.0.2", (r"127\.0\.0\.1",)) == ["127.0.0.2"]


def test_guard_bites_links_and_anchors():
    assert dead_links("see [x](No-Such-Page-Anywhere.md)") == ["No-Such-Page-Anywhere"]
    assert dead_links(f"see [x]({LESSONS[0]}.md#a)") == []
    assert dead_own_anchors("# Title\n\n[x](#no-such-heading)") == ["no-such-heading"]
    assert dead_own_anchors("# Title\n\n[x](#title)") == []


def test_guard_bites_identifiers():
    assert identifier_findings("-----BEGIN RSA PRIVATE KEY-----")
    assert identifier_findings("key " + "AKIA" + "ABCDEFGHIJKLMNOP") == ["AWS access key id"]
    assert not identifier_findings("nothing secret here")


def test_guard_bites_banner():
    assert banner_of("# T\n\n> **Status: unverified draft. Nothing was run.**\n\ntext") != ""
    assert banner_of("# T\n\nno banner here") == ""
    assert not HONEST.search("> **Status: fine.**")


# -- per-lesson rows ---------------------------------------------------------------------------------------------


def section(body: str, start: str, end: str | None = None) -> str:
    assert start in body, f"section start {start!r} not found"
    rest = body.split(start, 1)[1]
    if end is not None:
        assert end in rest, f"section end {end!r} not found after {start!r}"
        rest = rest.split(end, 1)[0]
    return rest


def check_row(name: str, row: dict) -> None:
    """Evaluate one data row against its page. Every assertion message names the page, the row and the rule."""
    body = text(name)
    rid = f"[{name}] row '{row['id']}'"
    scope = section(body, row["start"], row.get("end")) if "start" in row else body
    for needle in row.get("contains", ()):
        assert needle in scope, f"{rid}: missing {needle!r}"
    for needle in row.get("contains_ci", ()):
        assert needle.lower() in scope.lower(), f"{rid}: missing (any case) {needle!r}"
    if "contains_any" in row:
        assert any(n in scope for n in row["contains_any"]), f"{rid}: none of {row['contains_any']} is present"
    for needle in row.get("absent", ()):
        assert needle not in scope, f"{rid}: must not contain {needle!r}"
    for needle, allowed in row.get("absent_except", ()):  # the needle may appear only inside the allowed phrase
        assert needle not in scope.replace(allowed, ""), f"{rid}: {needle!r} appears outside {allowed!r}"
    for needle, n in row.get("count_at_least", {}).items():
        assert scope.count(needle) >= n, f"{rid}: {needle!r} appears {scope.count(needle)} times, expected at least {n}"
    for pattern, n in row.get("regex_count_at_least", {}).items():
        got = len(re.findall(pattern, scope, re.MULTILINE))
        assert got >= n, f"{rid}: /{pattern}/ matched {got} times, expected at least {n}"
    for pattern in row.get("regex_absent", ()):
        assert not re.search(pattern, scope), f"{rid}: /{pattern}/ must not match"
    for pattern in row.get("regex_present", ()):
        assert re.search(pattern, scope), f"{rid}: /{pattern}/ must match"
    for first, second in row.get("order", ()):
        assert first in scope and second in scope, f"{rid}: order needles missing ({first!r}, {second!r})"
        assert scope.index(first) < scope.index(second), f"{rid}: {first!r} must come before {second!r}"
    for first, second in row.get("order_before_last", ()):  # first occurrence of `first` before the LAST `second`
        assert first in scope and second in scope, f"{rid}: order needles missing ({first!r}, {second!r})"
        assert scope.index(first) < scope.rindex(second), f"{rid}: {first!r} must come before the last {second!r}"
    if "startswith" in row:
        assert body.startswith(row["startswith"]), f"{rid}: page must start with {row['startswith']!r}"
    for target in row.get("links_in_scope", ()):
        assert f"]({target}.md)" in scope, f"{rid}: no link to {target}"
        assert (WIKI / f"{target}.md").exists(), f"{rid}: {target} does not exist"
    if "register_row" in row:  # the first register row whose first cell has all `select` words must also have the rest
        want = row["register_row"]
        picked = [r for r in register_rows(body) if all(w in r[0] for w in want["select"])]
        assert picked, f"{rid}: no claims register row selected by {want['select']}"
        assert all(w in picked[0][0] for w in want.get("first_has", ())), f"{rid}: register row {picked[0][0][:60]!r} lacks {want.get('first_has')}"
        assert all(w in picked[0][1] for w in want.get("second_has", ())), f"{rid}: register row source cell lacks {want.get('second_has')}"
    if "inbound_min" in row:
        skip = {"Glossary.md", "_Sidebar.md", "Reading-Order.md", "Contents.md", f"{name}.md"}
        inbound = [p.name for p in WIKI.glob("*.md") if p.name not in skip and f"{name}.md" in p.read_text(encoding="utf-8")]
        assert len(inbound) >= row["inbound_min"], f"{rid}: only {len(inbound)} inbound lessons link here: {inbound}"
    for lesson in row.get("inbound_all", ()):
        assert f"{name}.md" in page_text(WIKI / f"{lesson}.md"), f"{rid}: {lesson} does not link this lesson"
    urls = re.findall(r"\]\((https?://[^)]+)\)", body)
    if "urls_min" in row:
        assert len(urls) >= row["urls_min"], f"{rid}: the url guard collected {len(urls)} urls"
    if "url_forbid" in row:
        bad = urls_matching(urls, row["url_forbid"])
        assert not bad, f"{rid}: forbidden url form {bad}"
    if "code" in row:
        check_code(rid, body, row["code"])
    if "numbered_items_min" in row:
        got = len(re.findall(r"^\d+\. ", scope, re.MULTILINE))
        assert got >= row["numbered_items_min"], f"{rid}: {got} numbered items, expected at least {row['numbered_items_min']}"
    for vendor, must in row.get("vendor_sections", {}).items():
        sec = vendor_section(body, vendor)
        for needle in must:
            assert needle in sec, f"{rid}: section '### {vendor}' lacks {needle!r}"


def vendor_section(body: str, heading: str) -> str:
    start = body.index(f"### {heading}")
    first_line_end = body.index("\n", start) + 1
    rest = body[first_line_end:]
    nxt = re.search(r"^#{2,3} ", rest, re.MULTILINE)
    return body[start : first_line_end + (nxt.start() if nxt else len(rest))]


def urls_matching(urls: list[str], pattern: str) -> list[str]:
    return [u for u in urls if re.search(pattern, u, re.IGNORECASE)]


def matches_in(commands: str, pattern: str, flags: int = 0) -> list[str]:
    """Every match of `pattern` in the commands, as the line it starts on (the pattern may span a line break)."""
    found = []
    for m in re.finditer(pattern, commands, flags):
        start = commands.rfind("\n", 0, m.start()) + 1
        end = commands.find("\n", m.end())
        found.append(commands[start : end if end != -1 else len(commands)].strip())
    return found


def check_code(rid: str, body: str, code: dict) -> None:
    """A code-block guard: collect loosely (the blocks must contain `require`), assert strictly (nothing matches
    `forbid`; `count_at_least` maps a regex to a minimum), and prove the guard fires on every `bite_bad` sample
    and stays quiet on every `bite_good` sample."""
    flags = re.IGNORECASE if code.get("ignorecase") else 0
    tags = tuple(code.get("tags", ()))
    chunks = [b for t, b in FENCE.findall(body) if not tags or t in tags]
    cmds = "\n".join(textwrap.dedent(c) for c in chunks)
    for needle in code.get("require", ()):
        assert needle in cmds, f"{rid}: the code guard collected nothing ({needle!r} not in the {tags or 'all'} blocks)"
    for pattern, n in code.get("count_at_least", {}).items():
        got = len(re.findall(pattern, cmds, flags))
        assert got >= n, f"{rid}: the code guard collected {got} matches of /{pattern}/, expected at least {n}"
    bad = matches_in(cmds, code["forbid"], flags)
    assert not bad, f"{rid}: forbidden command in a code block: {bad}"
    for sample in code.get("bite_bad", ()):
        assert matches_in(sample, code["forbid"], flags), f"{rid}: the guard does not bite on {sample!r}"
    for sample in code.get("bite_good", ()):
        assert not matches_in(sample, code["forbid"], flags), f"{rid}: the guard fires on the allowed {sample!r}"


def _rows():
    for name, spec in sorted(PAGES.items()):
        for row in spec.get("rows", ()):
            yield pytest.param(name, row, id=f"{name[:40]}::{row['id']}")


@pytest.mark.parametrize(("name", "row"), list(_rows()))
def test_lesson_specific_row(name, row):
    check_row(name, row)


def test_every_row_has_an_id_and_something_to_assert():
    keys = {"contains", "absent", "count_at_least", "regex_count_at_least", "regex_absent", "regex_present", "order", "order_before_last", "contains_ci", "contains_any", "absent_except", "startswith", "links_in_scope", "register_row", "inbound_min", "inbound_all", "urls_min", "url_forbid", "code", "numbered_items_min", "vendor_sections"}
    ids = set()
    for name, spec in PAGES.items():
        for row in spec.get("rows", ()):
            assert row.get("id"), f"{name}: a row without an id"
            assert (name, row["id"]) not in ids, f"{name}: duplicate row id {row['id']}"
            ids.add((name, row["id"]))
            assert keys & set(row), f"{name}: row {row['id']} asserts nothing"


def test_row_engine_bites():
    page = LESSONS[0]
    with pytest.raises(AssertionError, match="missing"):
        check_row(page, {"id": "x", "contains": ["zzz-not-in-any-page-zzz"]})
    with pytest.raises(AssertionError, match="must not contain"):
        check_row(page, {"id": "x", "absent": ["# "]})
    with pytest.raises(AssertionError, match="must come before"):
        t = text(page)
        check_row(page, {"id": "x", "order": [(t[-30:].strip().splitlines()[-1][:20], t[:20])]})
    with pytest.raises(AssertionError, match="does not bite"):
        check_row(page, {"id": "x", "code": {"forbid": "zzz-never", "bite_bad": ["nothing"]}})
    assert matches_in("sudo flashrom -w x", r"\bsudo\b|\bflashrom\b")
    assert not matches_in("cat /sys/x", r"\bsudo\b|\bflashrom\b")
    assert urls_matching(["https://example.com/p?ref=abc"], r"[?&]ref=")
    assert not urls_matching(["https://example.com/p"], r"[?&]ref=")
    sample = "### A\nFirmware ME\n### B\nother\n"
    assert "Firmware ME" in vendor_section(sample, "A")
    assert "other" not in vendor_section(sample, "A")


# -- tests that run external tools: kept as code, listed in the PR body -------------------------------------------


def _first(body: str, tag: str, needle: str) -> str:
    return next(b for b in blocks(body, tag) if needle in b)


@pytest.mark.skipif(shutil.which("qemu-img") is None, reason="qemu-img is not installed")
def test_vm_exercise_3_runs_and_the_snapshot_round_trips(tmp_path):
    body = text("Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options")
    script = _first(body, "bash", "qemu-img create").replace("cd ~/vmlab", f"cd {tmp_path}")
    result = subprocess.run(["bash", "-eu", "-c", script], capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stderr
    assert "virtual size: 4 GiB" in result.stdout
    assert "clean-start" in result.stdout
    # the last listing, after the delete, shows no snapshot line after the final info block
    assert result.stdout.count("clean-start") == 1


@pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl is not installed")
def test_hsm_part_a_signs_verifies_and_fails_on_a_changed_message(tmp_path):
    body = text("Hardware-Security-Modules-What-They-Are-and-Building-Your-Own-with-pico2hsm")
    block = _first(body, "bash", "ecparam")
    steps = block.replace("mkdir -p ~/hsmlab && cd ~/hsmlab", f"cd {tmp_path}").split("# 4.")[0]  # up to the first verify
    ok = subprocess.run(["bash", "-eu", "-c", steps], capture_output=True, text=True, timeout=60, check=False)
    assert ok.returncode == 0, ok.stderr
    assert "Verified OK" in ok.stdout + ok.stderr
    bad = subprocess.run(
        ["bash", "-c", f"cd {tmp_path} && echo tamper >> msg.txt && openssl dgst -sha256 -verify pub.der -keyform DER -signature sig.bin msg.txt"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert bad.returncode != 0


@pytest.mark.skipif(shutil.which("ansible-playbook") is None, reason="ansible-playbook is not installed")
def test_ansible_playbook_is_idempotent_and_the_bad_task_is_not(tmp_path):
    body = text("Ansible-Configuration-Management-Versus-Provisioning")
    recap = re.compile(r"ok=(\d+)\s+changed=(\d+)")
    inventory = next(b for b in blocks(body, "ini") if "[lab]" in b)
    playbook = next(b for b in blocks(body, "yaml") if "Make a small config directory" in b)
    bad = next(b for b in re.findall(r"cat > bad\.yml <<'EOF'\n(.*?)\nEOF", "\n".join(blocks(body, "bash")), re.DOTALL))
    (tmp_path / "inventory.ini").write_text(inventory, encoding="utf-8")
    (tmp_path / "site.yml").write_text(playbook, encoding="utf-8")
    (tmp_path / "bad.yml").write_text(bad, encoding="utf-8")

    def run(play: str) -> tuple[int, int]:
        out = subprocess.run(["ansible-playbook", "-i", "inventory.ini", play], cwd=tmp_path, capture_output=True, text=True, timeout=120, check=False)
        assert out.returncode == 0, out.stdout + out.stderr
        m = recap.search(out.stdout)
        assert m, out.stdout
        return int(m.group(1)), int(m.group(2))

    assert run("site.yml") == (3, 3)
    assert run("site.yml") == (3, 0)
    assert run("bad.yml")[1] == 1 and run("bad.yml")[1] == 1
    assert (tmp_path / "sandbox" / "bad.conf").read_text(encoding="utf-8").count("retries = 3") == 2
