# SPDX-License-Identifier: Apache-2.0
"""The cryptography fundamentals lesson: its drill runs, its citations exist, it is registered and honest about what was run.

docs/wiki/Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md teaches symmetric and
asymmetric encryption, MACs, signatures, PKI, the three data states, key custody, the NIST defaults and the post-quantum
plan, with a table of where this project uses each. A drill whose output differs from the page, a cited file that does
not exist, a sample that contradicts itself, a missing registration or a real address would each teach the wrong thing.
"""

import hashlib
import math
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

from wikitext import page_text

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "docs" / "wiki"
NAME = "Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys"
PAGE = WIKI / f"{NAME}.md"
FENCE = re.compile(r"^[ ]*```(\w*)\n(.*?)^[ ]*```$", re.MULTILINE | re.DOTALL)
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#([^)]*))?\)")
ADDR = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PATH_TOKEN = re.compile(r"`((?:modules|stacks|scripts|docs|\.github|\.spacelift|tests)/[A-Za-z0-9_./-]+|board\.yaml|\.gitignore)`")
STATUS_WORDS = ("Read", "Run", "Listing read", "Title and header read", "**est.**", "General knowledge", "**Not run**", "Not run")
TOPICS = (
    "## What encryption is and is not",
    "## Symmetric and asymmetric: what each is good for",
    "### How they combine: a key exchange, then a symmetric cipher",
    "## Hashing is not encryption: salts, passwords and message authentication",
    "## Digital signatures",
    "## Certificates and PKI in plain words",
    "## Data at rest, in transit and in use",
    "## Where this shows up in this project",
    "## Key management and custody: the hard part",
    "## Common mistakes",
    "## Modern defaults per NIST",
    "## Post-quantum planning, as far as NIST publishes it",
    "## Free path: run the drill, then read a real certificate chain",
    "## Claims register",
)


def text() -> str:
    return page_text(PAGE)  # without the generated navigation blocks (issue #417)


def section(body: str, start: str, end: str) -> str:
    return body.split(start)[1].split(end)[0]


def table_rows(block: str) -> list[list[str]]:
    rows = [line for line in block.splitlines() if line.startswith("|") and not line.startswith("|---")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]]


def cited_paths(cell: str) -> list[str]:
    return PATH_TOKEN.findall(cell)


def rows_missing_citation(rows: list[list[str]]) -> list[str]:
    """A project row must cite files that exist, or start with None in its file column and say None in its status."""
    bad = []
    for r in rows:
        files, status = r[2], r[3]
        paths = cited_paths(files)
        if any(not (ROOT / p).exists() for p in paths):
            bad.append(r[0])
        elif files.startswith("None"):
            if "None" not in status:
                bad.append(r[0])
        elif not paths:
            bad.append(r[0])
    return bad


def project_rows(body: str) -> list[list[str]]:
    return table_rows(section(body, "## Where this shows up in this project", "Three honest observations"))


def register_rows(body: str) -> list[list[str]]:
    return table_rows(body.split("## Claims register")[1])


def rows_missing_status(rows: list[list[str]]) -> list[str]:
    return [r[0] for r in rows if not any(w in r[-1] for w in STATUS_WORDS)]


def slug(heading: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", heading.lower().replace(" ", "-"))


def headings(body: str) -> set[str]:
    return {slug(h) for h in re.findall(r"^#+ (.+)$", body, re.MULTILINE)}


def broken_chain(lines: list[str]) -> list[int]:
    """In an s_client chain listing, the issuer of each certificate must be the subject of the next one."""
    subjects = [m.group(1) for line in lines if (m := re.match(r"^ *\d s:(.*)$", line))]
    issuers = [m.group(1) for line in lines if (m := re.match(r"^ *i:(.*)$", line))]
    return [n for n in range(len(subjects) - 1) if issuers[n] != subjects[n + 1]]


def test_the_banner_says_what_was_and_was_not_run():
    body = text()
    assert body.startswith("# Cryptography fundamentals")
    assert "Status: unverified draft" in body
    assert "**Not run:**" in body and "2026-10-31" in body
    assert "sample from that date" in body


def test_every_topic_the_issue_asked_for_has_a_section():
    body = text()
    missing = [t for t in TOPICS if f"\n{t}\n" not in body]
    assert not missing, missing


def test_every_linked_wiki_page_exists_and_every_anchor_resolves():
    links = LINK.findall(text())
    assert len({t for t, _ in links}) >= 10, "the guard collected too few links"
    problems = []
    for target, anchor in links:
        path = WIKI / f"{target}.md"
        if not path.exists():
            problems.append(target)
        elif anchor and anchor not in headings(path.read_text(encoding="utf-8")):
            problems.append(f"{target}#{anchor}")
    assert not problems, problems
    named = {t for t, _ in links}
    for needed in ("Hashing-Encryption-and-Keys", "The-CIA-Triad-Confidentiality-Integrity-Availability"):
        assert needed in named, needed


def test_the_tor_and_i2p_lesson_is_named_in_plain_text_not_linked():
    # That lesson (issue 358) does not exist yet, and a link to a missing page would break the wiki.
    body = text()
    assert "Tor and I2P" in body
    assert not re.search(r"Tor[-A-Za-z0-9]*I2P[-A-Za-z0-9]*\.md", body)
    assert "Plan-for-Failure-Blast-Radius" not in body, "tests/test_blast_radius_lesson.py caps links to that lesson"


def test_the_lesson_is_registered_in_contents_and_reading_order_not_the_sidebar():
    nav = (WIKI / "_nav.yaml").read_text(encoding="utf-8")
    entry = nav.split(f"page: {NAME},")[1].split("\n")[0]
    assert 'status: "draft"' in entry
    assert "sidebar" not in entry, "new lessons are reached from Contents and Reading Order, not the sidebar"
    for special in ("Contents.md", "Reading-Order.md"):
        assert f"{NAME}.md" in (WIKI / special).read_text(encoding="utf-8"), special
    rows = [line for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines() if f"{NAME}.md" in line]
    assert len(rows) >= 5, "expected glossary rows for the new terms"


def test_glossary_rows_point_at_real_headings():
    anchors = set()
    for line in (WIKI / "Glossary.md").read_text(encoding="utf-8").splitlines():
        anchors.update(re.findall(rf"{NAME}\.md#([a-z0-9-]+)", line))
    assert anchors, "the guard collected nothing"
    assert anchors <= headings(text()), sorted(anchors - headings(text()))


def test_the_hashing_page_links_the_lesson():
    assert f"{NAME}.md" in (WIKI / "Hashing-Encryption-and-Keys.md").read_text(encoding="utf-8")


def test_no_addresses_and_no_em_dashes():
    body = text()
    assert not ADDR.findall(body)
    assert "—" not in body
    assert "Connecting to" not in body, "openssl prints the server address on stderr; the exercise discards stderr"


def test_the_address_guard_bites():
    assert ADDR.findall("ping 192.0.2.7")


def test_every_project_row_cites_an_existing_file_or_says_none():
    rows = project_rows(text())
    assert len(rows) >= 12, "the guard collected too few rows"
    assert not rows_missing_citation(rows)
    assert sum(r[2].startswith("None") for r in rows) >= 4, "the table should say None where nothing exists"
    wanted = ("Disk", "Droplet backups", "bucket", "OpenTofu state", "Doppler", "Twingate", "SSH", "Data in use", "post-quantum", "key custody")
    joined = " ".join(r[0] for r in rows)
    assert all(w in joined for w in wanted), [w for w in wanted if w not in joined]


def test_the_citation_guard_bites():
    rows = [
        ["a", "x", "`scripts/does_not_exist.py`", "Built"],
        ["b", "x", "`scripts/secret_rule.py`", "Built"],
        ["c", "x", "None here", "Built"],
        ["d", "x", "None; the design is in `docs/does/not/exist.md`", "None"],
        ["e", "x", "no path at all", "Built"],
    ]
    assert rows_missing_citation(rows) == ["a", "c", "d", "e"]


def test_every_repository_path_the_page_names_exists():
    paths = set(cited_paths(text()))
    assert len(paths) >= 8, "the guard collected too few paths"
    assert not [p for p in sorted(paths) if not (ROOT / p).exists()]


def test_project_claims_hold_in_the_files():
    # The table says these things; the files must still say them.
    def read(p: str) -> str:
        return (ROOT / p).read_text(encoding="utf-8")

    assert "backups    = false" in read("modules/twingate-connector/main.tf")
    doppler = read("scripts/spacelift/doppler-env.sh")
    assert "--proto '=https' --tlsv1.2" in doppler and "sha256sum -c" in doppler
    cloud_init = read("modules/twingate-bootstrap/cloud-init.yaml.tftpl")
    assert "PasswordAuthentication no" in cloud_init and "fingerprint" in cloud_init
    assert re.search(r'condition\s*=\s*var\.acl == "private"', read("modules/spaces-bucket/variables.tf"))
    assert "*.tfstate" in read(".gitignore")
    unencrypted = [p for p in ROOT.rglob("*.tf") if ".claude" not in p.parts and re.search(r"^\s*encryption\s*\{", p.read_text(encoding="utf-8"), re.MULTILINE)]
    assert not unencrypted, f"the page says no encryption block exists in any .tf file: {unencrypted}"


def test_the_nist_facts_are_stated_with_their_dates_and_sources():
    body = text()
    for needle in (
        "doi.org/10.6028/NIST.IR.8547",
        "FIPS 203",
        "FIPS 204",
        "FIPS 205",
        "ML-KEM",
        "ML-DSA",
        "SLH-DSA",
        "2024-08-13",
        "after 2030",
        "after 2035",
        "harvest now, decrypt later",
        "SP 800-57 Part 1 Rev. 5",
        "SP 800-131A Rev. 2",
        "SP 800-38D",
        "SP 800-52 Rev. 2",
        "RFC 8446",
        "RFC 5280",
        "RFC 9106",
        "OWASP",
    ):
        assert needle in body, needle


def test_every_claims_register_row_has_a_status():
    rows = register_rows(text())
    assert len(rows) >= 20, "the guard collected too few rows"
    assert not rows_missing_status(rows)
    joined = " ".join(r[1] for r in rows)
    assert "csrc.nist.gov" in joined and "rfc-editor.org" in joined and "doi.org/10.6028" in joined
    assert sum("2026-10-31" in r[-1] or "Read" in r[-1] for r in rows) >= 15
    assert any("Run" in r[-1] for r in rows) and any("Not run" in r[-1] for r in rows)


def test_the_register_guard_bites():
    assert rows_missing_status([["X", "y", "maybe"]]) == ["X"]


def test_the_tls_sample_is_dated_and_marked_a_sample():
    body = text()
    block = section(body, "### Exercise 2: read a real TLS certificate chain", "**Safe-use rules")
    assert "sample read on 2026-10-31" in block and "your output will differ" in block
    assert "2> /dev/null > s_client.txt" in block, "stderr must be discarded: it carries the server address"
    commands = next(b for t, b in FENCE.findall(block) if t == "bash")
    assert "openssl s_client -connect example.com:443" in commands


def test_the_sample_chain_is_consistent_with_itself():
    block = section(text(), "### Exercise 2: read a real TLS certificate chain", "**Safe-use rules")
    chain = next(b for t, b in FENCE.findall(block) if t == "text" and b.lstrip().startswith("0 s:"))
    lines = chain.splitlines()
    assert sum(1 for line in lines if re.match(r"^ *\d s:", line)) >= 3, "the guard collected too few certificates"
    assert not broken_chain(lines)


def test_the_chain_guard_bites():
    bad = [" 0 s:CN=a", "   i:CN=b", " 1 s:CN=z", "   i:CN=c"]
    assert broken_chain(bad) == [0]


def script() -> str:
    found = [textwrap.dedent(b) for t, b in FENCE.findall(text()) if t == "bash" and "# crypto_drill.sh - " in b]
    assert len(found) == 1, f"expected one crypto_drill.sh block, found {len(found)}"
    return found[0]


def shown_output() -> str:
    found = [b for t, b in FENCE.findall(text()) if t == "text" and b.startswith("== 1. Hashing")]
    assert len(found) == 1
    return found[0]


NEEDED = ("bash", "openssl", "gpg", "gpgconf", "sha256sum", "cmp", "od", "tr", "awk", "python3")


def test_every_tool_the_drill_needs_is_installed():
    # No skip: a runner without these must fail loudly, not quietly stop checking the page.
    missing = [t for t in NEEDED if shutil.which(t) is None]
    assert not missing, missing
    version = subprocess.run(["openssl", "version"], capture_output=True, text=True, check=True).stdout
    assert re.search(r"OpenSSL 3\.", version), f"the drill needs OpenSSL 3.x (kdf, mac, pkeyutl -rawin): {version}"


def run_drill() -> subprocess.CompletedProcess:
    # A short directory name: gpg-agent sockets live under the lab folder and have a path length limit.
    base = Path(tempfile.mkdtemp(prefix="cf"))
    try:
        path = base / "crypto_drill.sh"
        path.write_text(script())
        done = subprocess.run(["bash", str(path)], capture_output=True, text=True, timeout=180, check=False, env={**os.environ, "TMPDIR": str(base)})
        leftovers = [p.name for p in base.glob("tmp*")]
        assert not leftovers, f"the script must delete its own lab folder: {leftovers}"
        return done
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_the_drill_runs_and_its_output_matches_the_page():
    done = run_drill()
    assert done.returncode == 0, done.stderr
    got = [line.rstrip() for line in done.stdout.strip().splitlines()]
    want = [line.rstrip() for line in shown_output().strip().splitlines()]
    assert got == want


def test_the_drill_prints_only_version_independent_labels():
    shown = shown_output()
    for label in ("CHECK-OK", "CHECK-FAIL", "GPG-REFUSED", "VERIFY-OK", "VERIFY-FAIL"):
        assert label in shown, label
    # raw tool wording differs between OpenSSL, GnuPG and coreutils versions and must stay out of the compared text
    for raw in ("error 20", "error 62", "hostname mismatch", "verification failed", "Bad session key", "manipulated", "WARNING", "Verified Successfully", "FAILED"):
        assert raw not in shown, raw
    assert not any(line.startswith("gpg:") for line in shown.splitlines())


def test_the_prose_numbers_match_the_printed_output():
    body = text()
    shown = shown_output()
    same = re.search(r"same hex digit in the same place: (\d+) of 64", shown).group(1)
    assert f"{same} happen to line up by chance" in body
    assert "pay Alice 900 dollars" in shown and "the safe code is 4417" in shown


GENERIC_KEY = re.compile(
    r"""(?i)[\w.-]{0,50}?(?:access|auth|(?-i:[Aa]pi|API)|credential|creds|key|passw(?:or)?d|secret|token)(?:[ \t\w.-]{0,20})[\s'"]{0,3}"""
    r"""(?:=|>|:{1,3}=|\|\|:|<=|=>|:|\?=)(?:'|"|\s|=|`){0,5}([\w.=-]{10,150}|[a-z0-9][a-z0-9+/]{11,}={0,3})(?:['"\n\r\s`;]|$)"""
)


def entropy(s: str) -> float:
    return -sum(s.count(c) / len(s) * math.log2(s.count(c) / len(s)) for c in set(s))


def secret_looking(body: str) -> list[str]:
    """An approximation of gitleaks' generic-api-key rule: a keyword, an assignment, then a long high-entropy value."""
    return [m.group(1) for line in body.splitlines() for m in GENERIC_KEY.finditer(line) if entropy(m.group(1)) >= 3.5]


def test_no_long_random_looking_value_sits_next_to_a_secret_keyword():
    for name, body in (("page", text()), ("drill", script()), ("test", Path(__file__).read_text(encoding="utf-8"))):
        found = secret_looking(body)
        assert not found, f"{name}: {found}"


def test_the_secret_guard_bites():
    random_looking = hashlib.sha256(b"guard").hexdigest()  # built at run time so no literal sits in this file
    assert secret_looking(f"hmac, right key:  {random_looking}")
    assert secret_looking(f'API_TOKEN="{random_looking[:40]}"')
    assert not secret_looking('AES_K="$(derive demo-seed-one 32)"')
    assert not secret_looking("hmac, same key and same message twice: tags equal")


KEYWORD_NEAR_RUN = re.compile(
    r"(?i)(?:key|salt|secret|token|password|passphrase|nonce|iv).{0,40}?(?<![A-Za-z0-9+/])(?:[0-9A-Fa-f]{20,}|[A-Za-z0-9+/]{20,}={0,2})"
)
BARE_HEX = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{32,}(?![0-9A-Fa-f])")


def long_runs(body: str) -> list[str]:
    """Lines with a bare run of 32 or more hex digits, or 20 or more hex or base64 characters near a secret-sounding word."""
    return [line.strip() for line in body.splitlines() if BARE_HEX.search(line) or KEYWORD_NEAR_RUN.search(line)]


def test_no_long_hex_or_base64_run_appears_anywhere_in_the_page_the_drill_or_the_test():
    for name, body in (("page", text()), ("drill", script()), ("test", Path(__file__).read_text(encoding="utf-8"))):
        found = long_runs(body)
        assert not found, f"{name}: {found}"


def test_the_long_run_guard_bites():
    digest = hashlib.sha256(b"guard").hexdigest()
    assert long_runs(f"{digest}")
    assert long_runs(f"salt 1: {digest[:32]}")
    assert long_runs(f"the nonce is {digest[:24]}")
    assert not long_runs("first 8 hex digits: cbcc2a3b...")
    assert not long_runs("same password and different salts: derived keys differ")


def test_the_drill_never_touches_anything_outside_its_own_folder():
    body = script()
    assert "mktemp -d" in body and 'export GNUPGHOME="$lab/gnupg"' in body
    rm_lines = [line for line in body.splitlines() if re.search(r"\brm\b", line)]
    assert len(rm_lines) == 1 and 'rm -rf "$lab"' in rm_lines[0], rm_lines
    assert not re.search(r"\bsudo\b|\bcurl\b|\bwget\b|\bs_client\b|\bssh\b|\bchattr\b|~/|\$HOME", body)
    assert not re.search(r"\bgpg\b[^\n]*--(?:import|export|gen-key|full-generate-key|recv-keys|send-keys)", body)
