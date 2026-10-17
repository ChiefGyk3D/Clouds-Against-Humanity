"""A small, fail-closed reader for OpenTofu `variable` blocks.

It is not an HCL parser. It reads exactly the shapes this repository uses in
`variable` blocks and raises HclError on anything else, so a new shape cannot
slip past the settings coverage test unseen.

Understood:
- `variable "name" { ... }` at the top level of a .tf file, with the
  attributes type, default, description, sensitive, nullable and any number of
  `validation { ... }` blocks.
- Strings with backslash escapes, `#`, `//` and `/* */` comments, and
  multi-line expressions in brackets, braces or parentheses.

Refused (HclError): heredocs, `${` or `%{` template sequences inside a string,
unbalanced brackets, an unknown attribute or block inside a variable, a
repeated attribute, a duplicate variable name in one directory, a variable
label that is not a plain quoted name.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
ATTRIBUTES = frozenset({"type", "default", "description", "sensitive", "nullable"})
OPEN = {"{": "}", "[": "]", "(": ")"}
CLOSE = frozenset(OPEN.values())


class HclError(ValueError):
    """The file has a shape this reader does not understand."""


@dataclass
class Variable:
    name: str
    type: str | None = None
    has_default: bool = False
    default: object = None
    sensitive: bool = False
    description: str | None = None
    validations: int = 0
    source: str = ""
    raw: dict = field(default_factory=dict)


def _skip_string(text: str, i: int, lenient: bool = False) -> int:
    """Return the index after the string that starts at text[i] == '"'.

    Lenient mode is for blocks that are not variables (resources and so on),
    which are only skipped, never read: template sequences are stepped over.
    """
    i += 1
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == '"':
            return i + 1
        if c in "$%" and text[i + 1 : i + 2] == "{":
            if not lenient:
                raise HclError("template sequence inside a string is not understood")
            i = _read_balanced(text, i + 1, lenient=True)
            continue
        if c == "\n":
            raise HclError("newline inside a quoted string")
        i += 1
    raise HclError("unterminated string")


def _skip_ws_comments(text: str, i: int, newlines: bool = True) -> int:
    while i < len(text):
        c = text[i]
        if c in " \t\r" or (newlines and c == "\n"):
            i += 1
        elif c == "#" or text.startswith("//", i):
            while i < len(text) and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise HclError("unterminated block comment")
            i = end + 2
        else:
            break
    return i


HEREDOC_RE = re.compile(r"<<-?([A-Za-z_][A-Za-z0-9_]*)[ \t]*\n")


def _skip_heredoc(text: str, i: int) -> int:
    m = HEREDOC_RE.match(text, i)
    if not m:
        raise HclError("heredoc marker is not understood")
    end = re.compile(rf"^[ \t]*{m.group(1)}[ \t]*$", re.MULTILINE).search(text, m.end())
    if not end:
        raise HclError("unterminated heredoc")
    return end.end()


def _read_balanced(text: str, i: int, lenient: bool = False) -> int:
    """text[i] is an opener; return the index after its matching closer."""
    stack = [OPEN[text[i]]]
    i += 1
    while i < len(text):
        c = text[i]
        if c == '"':
            i = _skip_string(text, i, lenient)
            continue
        if c == "#" or text.startswith("//", i) or text.startswith("/*", i):
            i = _skip_ws_comments(text, i)
            continue
        if text.startswith("<<", i):
            if not lenient:
                raise HclError("heredoc is not understood")
            i = _skip_heredoc(text, i)
            continue
        if c in OPEN:
            stack.append(OPEN[c])
        elif c in CLOSE:
            if not stack or stack.pop() != c:
                raise HclError("mismatched bracket")
            if not stack:
                return i + 1
        i += 1
    raise HclError("unbalanced bracket")


def _read_expression(text: str, i: int) -> int:
    """Read an expression to the end of its logical line; return the end index."""
    while i < len(text):
        c = text[i]
        if c == "\n":
            return i
        if c == '"':
            i = _skip_string(text, i)
        elif c in OPEN:
            i = _read_balanced(text, i)
        elif c in CLOSE:
            raise HclError("unexpected closing bracket")
        elif c == "#" or text.startswith("//", i) or text.startswith("/*", i):
            i = _skip_ws_comments(text, i, newlines=False)
        elif text.startswith("<<", i):
            raise HclError("heredoc is not understood")
        else:
            i += 1
    return i


def _literal(expr: str):
    """Evaluate a literal: string, number, bool, null, [] or {}. Else HclError."""
    expr = expr.strip()
    if expr.startswith('"'):
        end = _skip_string(expr, 0)
        if expr[end:].strip():
            raise HclError(f"trailing text after string: {expr!r}")
        return json.loads(expr)
    if expr in ("true", "false"):
        return expr == "true"
    if expr == "null":
        return None
    if re.fullmatch(r"-?[0-9]+(\.[0-9]+)?", expr):
        return float(expr) if "." in expr else int(expr)
    if re.fullmatch(r"\[\s*\]", expr):
        return []
    if re.fullmatch(r"\{\s*\}", expr):
        return {}
    raise HclError(f"default is not a simple literal: {expr!r}")


def _normalize_type(expr: str) -> str:
    """Compact a type expression; a newline between attributes is a comma."""
    out = re.sub(r"\s*\n\s*", ",", expr.strip())
    out = re.sub(r"\s+", "", out)
    out = re.sub(r",+", ",", out)
    return re.sub(r"([{(\[]),|,([})\]])", r"\1\2", out)


def _parse_body(body: str, name: str, source: str) -> Variable:
    var = Variable(name=name, source=source)
    seen: set[str] = set()
    i = 0
    while True:
        i = _skip_ws_comments(body, i)
        if i >= len(body):
            break
        m = NAME_RE.match(body, i)
        if not m:
            raise HclError(f"{source}: variable {name}: unexpected text in body")
        key = m.group(0)
        i = _skip_ws_comments(body, m.end(), newlines=False)
        if body.startswith("=", i) and not body.startswith("==", i):
            if key not in ATTRIBUTES:
                raise HclError(f"{source}: variable {name}: unknown attribute {key}")
            if key in seen:
                raise HclError(f"{source}: variable {name}: repeated attribute {key}")
            seen.add(key)
            start = _skip_ws_comments(body, i + 1, newlines=False)
            end = _read_expression(body, start)
            expr = body[start:end].strip()
            if not expr:
                raise HclError(f"{source}: variable {name}: empty {key}")
            var.raw[key] = expr
            if key == "type":
                var.type = _normalize_type(expr)
            elif key == "default":
                var.has_default = True
                var.default = _literal(expr)
            elif key == "sensitive":
                if expr not in ("true", "false"):
                    raise HclError(
                        f"{source}: variable {name}: sensitive must be a bool literal"
                    )
                var.sensitive = expr == "true"
            elif key == "description":
                var.description = _literal(expr)
            i = end
        elif body.startswith("{", i):
            if key != "validation":
                raise HclError(f"{source}: variable {name}: unknown block {key}")
            i = _read_balanced(body, i)
            var.validations += 1
        else:
            raise HclError(f"{source}: variable {name}: cannot read {key!r}")
    if var.type is None:
        raise HclError(f"{source}: variable {name}: no type (every variable is typed)")
    return var


def parse_variables(text: str, source: str = "<text>") -> list[Variable]:
    """Return every top-level `variable` block in one .tf file's text."""
    out: list[Variable] = []
    i = 0
    while True:
        i = _skip_ws_comments(text, i)
        if i >= len(text):
            return out
        m = NAME_RE.match(text, i)
        if not m:
            raise HclError(f"{source}: unexpected text at top level")
        keyword = m.group(0)
        i = _skip_ws_comments(text, m.end(), newlines=False)
        labels: list[str] = []
        while text.startswith('"', i):
            end = _skip_string(text, i)
            labels.append(json.loads(text[i:end]))
            i = _skip_ws_comments(text, end, newlines=False)
        if text.startswith("=", i):
            # A top-level attribute (not valid in .tf, tolerated in tfvars-like text).
            raise HclError(f"{source}: top-level attribute {keyword} is not understood")
        if not text.startswith("{", i):
            raise HclError(f"{source}: block {keyword} has no body")
        end = _read_balanced(text, i, lenient=keyword != "variable")
        if keyword == "variable":
            if len(labels) != 1 or not NAME_RE.fullmatch(labels[0]):
                raise HclError(f"{source}: variable block needs one plain name label")
            out.append(_parse_body(text[i + 1 : end - 1], labels[0], source))
        i = end


def variables_in_dir(directory: Path) -> dict[str, Variable]:
    """All variables declared in the top-level *.tf files of a directory."""
    found: dict[str, Variable] = {}
    for tf in sorted(directory.glob("*.tf")):
        for var in parse_variables(tf.read_text(encoding="utf-8"), tf.name):
            if var.name in found:
                raise HclError(f"{directory}: duplicate variable {var.name}")
            found[var.name] = var
    return found


def variable_directories(root: Path) -> list[Path]:
    """Every stack and module directory that holds .tf files, sorted."""
    dirs = []
    for top in ("stacks", "modules"):
        base = root / top
        if not base.is_dir():
            continue
        for d in sorted(p for p in base.iterdir() if p.is_dir()):
            if any(d.glob("*.tf")):
                dirs.append(d)
            else:
                # modules/<provider>/<role>, such as modules/aws/vpc, and
                # stacks/<provider>/<NN-name>, such as stacks/aws/10-access.
                for sub in sorted(q for q in d.iterdir() if q.is_dir()):
                    if not sub.name.startswith(".") and any(sub.glob("*.tf")):
                        dirs.append(sub)
    return dirs
