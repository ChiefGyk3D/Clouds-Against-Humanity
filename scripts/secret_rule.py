"""The one rule for what counts as a missing or placeholder secret.

A required secret that is empty, unset or a placeholder means the project would
run with no security (or with a value everyone has read in the docs). Every
place that reads a required secret asks this rule and refuses on a bad value.

Definition (case-insensitive, after stripping whitespace). A value is rejected
when it is empty, or

  - starts with   your_  your-  changeme  change-me  replace-with  replace_with
                  xxx  dp.st.your
  - is wrapped in <...>
  - contains      example  placeholder  changeme
  - equals        todo  tbd  admin  password  secret  test

The OpenTofu validations carry PLACEHOLDER_RE2, the same rule as one pattern;
tests/test_secret_rule.py pins the copies to this file. The Spacelift hook
script (scripts/spacelift/doppler-env.sh) has a POSIX shell copy, pinned the
same way.

Command line, used by the lab shell scripts (the value arrives on standard
input so it never shows in a process list, and is never printed):

    printf '%s' "$VALUE" | python3 -I scripts/secret_rule.py NAME

Exit 0 when the value is usable, 1 when it is empty or a placeholder (the
message names NAME and never the value), 2 on bad usage.
"""

from __future__ import annotations

import re
import sys

# RE2-safe (no quote, no backslash) so it can sit inside an OpenTofu string.
PLACEHOLDER_RE2 = (
    "(?i)(^(your[_-]|changeme|change-me|replace[_-]with|xxx|dp[.]st[.]your"
    "|(todo|tbd|admin|password|secret|test)$)|^<.*>$|example|placeholder|changeme)"
)
_PLACEHOLDER = re.compile(PLACEHOLDER_RE2)


class SecretError(ValueError):
    """A required secret is empty, unset or a placeholder. Never holds the value."""


def is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    value = value.strip()
    return value == "" or _PLACEHOLDER.search(value) is not None


def require_secret(name: str, value: str | None) -> str:
    """Return value, or raise SecretError naming `name` (never the value)."""
    if is_placeholder(value):
        raise SecretError(
            f"{name} is empty or a placeholder. Set a real value (see README, Required secrets)."
        )
    assert value is not None
    return value


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", argv[1]):
        print("usage: secret_rule.py NAME   (the value is read from standard input)", file=sys.stderr)
        return 2
    try:
        require_secret(argv[1], sys.stdin.read().rstrip("\r\n"))
    except SecretError as err:
        print(err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
