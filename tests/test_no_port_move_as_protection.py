"""No page may present moving a service to another port as a security control (issue #230).

The maintainer's position: changing a port (SSH is the usual example) is security through
obscurity, a flawed one-trick idea. A scanner checks every port in seconds and, once it finds the
service, goes straight to it. This test is a conservative phrase check over the wiki, the stage
guides and the README: any line that talks about moving a service to a different port must, on that
same line, also say it is not protection (or say why the move is functional). A line that does
neither fails, unless it is in ALLOWED with a reason.

It is a phrase check and not a proof: it catches the common wording, not every possible one.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = sorted((ROOT / "docs" / "wiki").glob("*.md")) + sorted((ROOT / "docs" / "stages").glob("*.md")) + [ROOT / "README.md"]
SKIP = {"Contents.md", "_Sidebar.md", "_Footer.md"}

# A line is about a port move when it matches one of these.
PORT_MOVE = re.compile(
    r"(non-?standard|odd|unusual|alternate|alternative|different|another|high|random|other than 22)\s+(tcp\s+)?port\b"
    r"|\b(move|moves|moved|moving|change|changes|changed|changing)\b[^.|]{0,40}\bport\b"
    r"|\bport\b[^.|]{0,20}\b(move|moved|change|changed)\b"
    r"|\bits own port\b",
    re.IGNORECASE,
)

# ... and only counts when it is about exposing or reaching a service, not (say) a switch port.
SERVICE = re.compile(r"\b(ssh|sshd|rdp|telnet|management|admin|service|daemon|login|server)\b", re.IGNORECASE)

# A line that says the move is not protection, or why it is functional, passes.
HONEST = re.compile(
    r"not (a |the )?(protection|defen[sc]e|security control|control|layer|substitute)"
    r"|obscurity|log noise|quieter|less noisy|for function|function choice|functional|because the imitation|because cowrie takes"
    r"|bought two seconds|does not (work|protect|stop|change)|no protection|adds no protection|nothing about who may",
    re.IGNORECASE,
)

# (file name, a substring of the line) -> why the line is a false positive. Keep it short.
ALLOWED: dict[tuple[str, str], str] = {}


def hits() -> list[tuple[str, int, str]]:
    found = []
    for path in FILES:
        if path.name in SKIP:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if PORT_MOVE.search(line) and SERVICE.search(line) and not HONEST.search(line):
                found.append((path.name, n, line.strip()))
    return found


def allowed(name: str, line: str) -> bool:
    return any(f == name and sub in line for (f, sub) in ALLOWED)


def test_no_line_presents_a_port_move_as_protection():
    bad = [(f, n, line[:160]) for f, n, line in hits() if not allowed(f, line)]
    assert not bad, "port move not marked as non-protection (add the disclaimer or an ALLOWED reason):\n" + "\n".join(f"{f}:{n}: {line}" for f, n, line in bad)


def test_every_allowlist_entry_still_matches_something_and_has_a_reason():
    live = hits()
    for (name, sub), reason in ALLOWED.items():
        assert len(reason) > 20, f"allowlist entry {name!r} needs a real reason"
        assert any(f == name and sub in line for f, _, line in live), f"stale allowlist entry: {name!r} / {sub!r}"


def test_the_checker_bites_on_a_protection_claim():
    assert PORT_MOVE.search("Move SSH to a non-standard port to keep attackers out.")
    assert not HONEST.search("Move SSH to a non-standard port to keep attackers out.")
    assert HONEST.search("A different port is not a security control.")
