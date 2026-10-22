# SPDX-License-Identifier: Apache-2.0
"""No lab or lesson snippet may keep state in a predictable shared path or kill an unchecked pid.

Issue #260. A fixed name in a shared folder such as /tmp lets another local user plant a file, a
link or a pid file before the lab uses it. This test scans labs/ (every text file) and the fenced
code blocks of docs/wiki/*.md for three patterns:

  fixed-shared-path   /tmp/<name>, /var/tmp/<name>, /dev/shm/<name>, $TMPDIR/<name>, a quoted
                      "/tmp" in code, or a Windows temp folder joined to a fixed name
  kill-by-pattern     pkill, pgrep or killall with a literal (it can match your own shell)
  unchecked-pid-file  kill of a pid read straight from a file, in a file or code block that never
                      checks the pid is digits and the process identity (ps -o command=)

Safe forms are not flagged: mktemp (mktemp -d), $XDG_RUNTIME_DIR, $HOME/.cache, Python tempfile,
a per-user folder made with mkdir -m 700, and kill of a pid taken from $! in the same shell.

Exceptions live in docs/shared-temp-allowlist.txt, one per line, with a required reason:
    <path relative to the repository root>:<the matched text> | <reason>
A stale entry (one that no longer matches anything) also fails, so the list cannot rot.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST = ROOT / "docs" / "shared-temp-allowlist.txt"
SHARED = r"(?:/tmp|/var/tmp|/dev/shm)"

FIXED_PATH = re.compile(
    rf"(?<![\w.$/~-]){SHARED}/[\w.%{{$][^\s'\"`)]*"  # /tmp/name
    r"|\$\{?TMPDIR\}?/[\w.%{$][^\s'\"`)]*"  # $TMPDIR/name
    rf"|[\"']{SHARED}[\"']"  # Path("/tmp") in code
    r"|gettempdir\(\)"  # Python shared folder, then a fixed name
    r"|GetTempPath\(\)\)?[^\n]*[\"'][\w.-]+[\"']\)?"  # PowerShell, joined to a literal
)
# A line that makes its own random name is the safe form, even if it mentions /tmp.
RANDOM_NAME = re.compile(r"mktemp|mkdtemp|mkstemp|TemporaryDirectory|NamedTemporaryFile|NewGuid|GetRandomFileName")
KILL_BY_PATTERN = re.compile(r"\b(?:pkill|pgrep|killall)\b(?:\s+-\S+)*\s+(?![\"']?\$|-)\S+")
# kill ... $(cat X.pid), kill ... $(<X.pid), kill ... `cat X.pid`
KILL_PID_FILE = re.compile(r"\bkill\b[^\n;|&]*?(?:\$\(\s*(?:cat\s+)?<?\s*[^)\n]*pid|`\s*cat\s+[^`\n]*pid)")
PID_IS_DIGITS = re.compile(r"=~\s*\^\[0-9\]\+\$|\[\[:digit:\]\]|\^\\d\+\$|isdigit\(\)|\^\[0-9\]\+\\\$")
PID_IDENTITY = re.compile(r"ps\s+-o\s+command=|/proc/\$?\{?\w+\}?/cmdline|psutil|\.cmdline\(\)")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
TEXT_SUFFIXES = {".sh", ".ps1", ".py", ".yml", ".yaml", ".conf", ".template", ".md", ".txt", ".cfg", ".ini", ".json", ".toml", ""}


def code_units(text, markdown):
    """Yield (first_line_number, lines) for each unit checked for pid validation.

    A markdown file is split into its fenced blocks; anything else is one unit.
    """
    lines = text.splitlines()
    if not markdown:
        yield 1, lines
        return
    block, start, fence = [], 0, None
    for number, line in enumerate(lines, 1):
        m = FENCE.match(line)
        if fence is None and m:
            fence, start, block = m.group(1)[0], number + 1, []
        elif fence is not None and m and m.group(1)[0] == fence:
            yield start, block
            fence = None
        elif fence is not None:
            block.append(line)
    if fence is not None:
        yield start, block


def scan_text(text, markdown=False):
    """Return a list of (line_number, rule, matched_text) for one file's text."""
    found = []
    for first, block in code_units(text, markdown):
        joined = "\n".join(block)
        validated = bool(PID_IS_DIGITS.search(joined) and PID_IDENTITY.search(joined))
        for offset, line in enumerate(block):
            number = first + offset
            code = line.strip()
            if code.startswith(("#", "//")):
                continue
            if not RANDOM_NAME.search(line):
                found += [(number, "fixed-shared-path", m.group(0)) for m in FIXED_PATH.finditer(line)]
            found += [(number, "kill-by-pattern", m.group(0)) for m in KILL_BY_PATTERN.finditer(line)]
            if not validated:
                found += [(number, "unchecked-pid-file", m.group(0)) for m in KILL_PID_FILE.finditer(line)]
    return found


def scanned_files():
    for path in sorted((ROOT / "labs").rglob("*")):
        if path.is_file() and path.suffix in TEXT_SUFFIXES and path.stat().st_size < 1_000_000:
            yield path
    yield from sorted((ROOT / "docs" / "wiki").glob("*.md"))


def findings():
    out = []
    for path in scanned_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(ROOT).as_posix()
        out += [(rel, n, rule, hit) for n, rule, hit in scan_text(text, markdown=path.suffix == ".md")]
    return out


def parse_allowlist(text):
    """Return {(path, matched text): reason}; raise ValueError for a line with no reason."""
    entries = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, reason = line.partition(" | ")
        if not sep or not reason.strip():
            raise ValueError(f"line {number}: an allowlist entry needs ' | <reason>'")
        path, colon, hit = key.partition(":")
        if not colon or not path.strip() or not hit.strip():
            raise ValueError(f"line {number}: expected '<path>:<matched text> | <reason>'")
        entries[(path.strip(), hit.strip())] = reason.strip()
    return entries


def test_no_shared_temp_paths_or_unchecked_kills_in_labs_and_lessons():
    allowed = parse_allowlist(ALLOWLIST.read_text())
    bad = [
        f"{rel}:{n}  {rule}  {hit!r}" for rel, n, rule, hit in findings() if (rel, hit) not in allowed
    ]
    assert not bad, (
        "Use a private per-user folder (mkdir -m 700 under $XDG_RUNTIME_DIR or $HOME/.cache, or mktemp -d), "
        "check a pid file and the process before kill, and never pkill or pgrep with a literal. "
        "A true exception goes in docs/shared-temp-allowlist.txt with a reason.\n" + "\n".join(bad)
    )


def test_every_allowlist_entry_has_a_reason_and_still_matches_something():
    allowed = parse_allowlist(ALLOWLIST.read_text())
    live = {(rel, hit) for rel, _n, _rule, hit in findings()}
    stale = sorted(set(allowed) - live)
    assert not stale, f"allowlist entries that match nothing now (remove them): {stale}"


def test_allowlist_without_a_reason_is_rejected():
    for bad in ("a.md:/tmp/x", "a.md:/tmp/x | ", "a.md:/tmp/x |   ", "nocolon | reason"):
        try:
            parse_allowlist(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted: {bad!r}")
    assert parse_allowlist("# c\n\na.md:/tmp/x | it is data, not state\n") == {("a.md", "/tmp/x"): "it is data, not state"}


# ---- the scanner itself: it catches each banned pattern ----------------------------------------


def rules(text, markdown=False):
    return {rule for _n, rule, _hit in scan_text(text, markdown)}


def test_scanner_catches_fixed_shared_paths():
    for snippet in (
        "mkdir -p /tmp/lab",
        "echo hi > /tmp/lab.txt",
        "pid /tmp/nginx.pid;",
        "cd /var/tmp/work",
        "touch /dev/shm/state",
        'LAB="$TMPDIR/lab"',
        "LAB=${TMPDIR}/lab",
        'p = Path("/tmp") / "state"',
        "d = tempfile.gettempdir() + '/lab'",
        "$d = Join-Path ([IO.Path]::GetTempPath()) 'cah-lab'",
    ):
        assert "fixed-shared-path" in rules(snippet), snippet


def test_scanner_catches_kill_by_pattern():
    for snippet in ("pkill -f nginx", "pkill nginx", "pgrep -f 'my server'", "killall python3", "kill $(pgrep -f app.py)"):
        assert "kill-by-pattern" in rules(snippet), snippet


def test_scanner_catches_kill_of_an_unvalidated_pid_file():
    for snippet in (
        'kill "$(cat app.pid)"',
        "kill $(cat ~/lab/auth.pid)",
        'kill -9 "$(cat "$WORK/a.pid")" || true',
        'kill "$(<server.pid)"',
        "kill `cat app.pid`",
    ):
        assert "unchecked-pid-file" in rules(snippet), snippet


def test_scanner_catches_inside_a_fenced_block_but_not_in_prose():
    page = "Never use /tmp/lab in prose.\n\n```bash\nmkdir /tmp/lab\n```\n\nAfter the block /tmp/other is prose again.\n"
    hits = scan_text(page, markdown=True)
    assert [(n, rule, hit) for n, rule, hit in hits] == [(4, "fixed-shared-path", "/tmp/lab")]


# ---- the scanner ignores the safe forms --------------------------------------------------------


def test_scanner_ignores_safe_temp_forms():
    for snippet in (
        'LAB="$(mktemp -d)"',
        "tmp=$(mktemp -d /tmp/cah.XXXXXX)",
        'WORK="${XDG_RUNTIME_DIR:-$HOME/.cache}/cah-lab"',
        'mkdir -m 700 "$HOME/.cache/cah-lab"',
        "with tempfile.TemporaryDirectory() as tmp:",
        "fd, name = tempfile.mkstemp(prefix='x')",
        "home = Path(tempfile.mkdtemp(prefix='x', dir='/tmp'))",
        '$d = Join-Path ([IO.Path]::GetTempPath()) ("lab-" + [guid]::NewGuid())',
        "ls /tmp",
        "cat /etc/tmp.conf",
        "cp ./tmp/body lab/tmp/body",
        "# pkill -f nginx would match your own shell",
        'pkill -f "$name"',
    ):
        assert rules(snippet) == set(), snippet


def test_scanner_ignores_kill_of_a_child_pid_and_a_checked_pid_file():
    assert rules('python3 -m http.server & pid=$!\nkill "$pid"; wait "$pid"') == set()
    checked = (
        "pid_ok() {\n"
        '  [ -f "$1" ] && [ -O "$1" ] || return 1\n'
        '  pid="$(cat "$1")"\n'
        '  [[ "$pid" =~ ^[0-9]+$ ]] || return 1\n'
        '  [[ "$(ps -o command= -p "$pid")" == *moto.server* ]]\n'
        "}\n"
        'pid_ok a.pid && kill "$(cat a.pid)"\n'
    )
    assert rules(checked) == set()
    # Only a digits check, or only an identity check, is not enough.
    assert "unchecked-pid-file" in rules('[[ "$p" =~ ^[0-9]+$ ]]\nkill "$(cat a.pid)"')
    assert "unchecked-pid-file" in rules('ps -o command= -p 1\nkill "$(cat a.pid)"')


def test_the_checked_pid_pattern_is_per_fenced_block_in_a_page():
    good = "```bash\n" + '[[ "$p" =~ ^[0-9]+$ ]]; ps -o command= -p "$p"; kill "$(cat a.pid)"\n' + "```\n"
    other = "```bash\n" + 'kill "$(cat a.pid)"\n' + "```\n"
    assert rules(good, markdown=True) == set()
    assert rules(good + "\n" + other, markdown=True) == {"unchecked-pid-file"}
