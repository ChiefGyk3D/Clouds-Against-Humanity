# SPDX-License-Identifier: Apache-2.0
"""Pages that were written beside their siblings no longer say the siblings may not exist (issue #444).

Several lessons were written while the pages they point at did not exist yet, so they carried notes such as "the link
may not resolve until the pages merge", "named in plain text, not linked" or "planned lesson". Every one of those pages
is in the wiki now. A note that says otherwise tells the reader a working link is dead, so each phrase below must be
gone, and each page that named its siblings in plain text must link them to a file that exists. The pages with their own
lesson test have their checks there; these are the pages that had none.
"""

import re
from pathlib import Path

from wikitext import page_text

WIKI = Path(__file__).resolve().parent.parent / "docs" / "wiki"
LINK = re.compile(r"\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)")

# page stem -> phrases that were true before the siblings existed and are false now
STALE = {
    "LAMP-and-LEMP-From-Zero": ("may not be merged yet", "links can be dead"),
    "WordPress-and-PHP-Security-WAF-and-Static-Sites": ("may not resolve until they are merged",),
    "WordPress-at-Scale-CDN-WAF-and-CI": ("may not open yet", "the same caution about links"),
    "DNS-Cloudflare-and-Hosting-Your-Own-Website": ("If it is not merged yet", "lead nowhere", "written at the same time", "once it is merged"),
    "Rate-Limiting-at-Every-Layer": ("may not resolve until", "written at the same time"),
    "IDS-and-IPS-Snort-and-Suricata": ("may not resolve until", "are written at the same time", "They may not resolve"),
    "File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh": ("may not resolve until", "same caveat"),
    "Packet-Filters-Compared-iptables-nftables-ufw-pf": ("may not resolve until", "being written at the same time"),
    "Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit": ("may not resolve until", "written at the same time as this one"),
    "Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS": ("may not resolve until lesson 2 merges", "written alongside this lesson", "when it merges"),
    "OpenTofu-From-Zero": ("may not resolve yet", "are written alongside this page"),
    "Plans-State-Drift-and-Recovery": ("may not be merged yet", "Planned lessons in this infrastructure-as-code track", "the link will resolve once it is"),
    "The-CIA-Triad-Confidentiality-Integrity-Availability": ("are not written yet", "named, not linked"),
    "Build-and-Destroy-Stack-Per-Service": ("being written at the same time", "a planned lesson", "once the lessons are merged"),
    "Spacelift-From-Zero": ("plain text here until they merge", "named but not linked", "not linked until it merges"),
}

# The infrastructure-as-code track: Spacelift from zero names all three of its siblings, and each must be a link.
TRACK = ("OpenTofu-From-Zero", "Plans-State-Drift-and-Recovery", "Build-and-Destroy-Stack-Per-Service")


def stale_phrases(body: str, phrases: tuple[str, ...]) -> list[str]:
    return [p for p in phrases if p in body]


def test_no_page_still_says_its_existing_siblings_may_not_exist():
    assert STALE, "the guard collected no pages"
    for stem, phrases in STALE.items():
        path = WIKI / f"{stem}.md"
        assert path.is_file(), stem
        assert not stale_phrases(page_text(path), phrases), (stem, stale_phrases(page_text(path), phrases))


def test_spacelift_from_zero_links_the_other_lessons_of_its_track():
    body = page_text(WIKI / "Spacelift-From-Zero.md")
    links = set(LINK.findall(body))
    for stem in TRACK:
        assert stem in links, f"{stem} exists and must be linked"
        assert (WIKI / f"{stem}.md").is_file(), stem


def test_the_guard_bites():
    assert stale_phrases("their links may not resolve until the pages merge", ("may not resolve until",))
    assert not stale_phrases("their links resolve", ("may not resolve until",))
    assert "stem" not in set(LINK.findall("see [x](other.md)"))
