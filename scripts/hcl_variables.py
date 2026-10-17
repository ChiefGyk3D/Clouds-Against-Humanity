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

- Literal values: strings, numbers, true/false/null, and lists and objects
  built from them (for defaults, and for the assignments of a tfvars file read
  by `parse_assignments`). A comment may follow any value.

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


NUMBER_RE = re.compile(r"-?[0-9]+(\.[0-9]+)?")
KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
MAX_DEPTH = 8


def _parse_value(text: str, i: int, depth: int = 0):
    """Parse one literal at text[i]; return (value, index after it)."""
    if depth > MAX_DEPTH:
        raise HclError("literal is nested too deeply")
    i = _skip_ws_comments(text, i)
    if i >= len(text):
        raise HclError("expected a value")
    c = text[i]
    if c == '"':
        end = _skip_string(text, i)
        return json.loads(text[i:end]), end
    if c == "[":
        out: list = []
        i += 1
        while True:
            i = _skip_ws_comments(text, i)
            if text.startswith("]", i):
                return out, i + 1
            value, i = _parse_value(text, i, depth + 1)
            out.append(value)
            i = _skip_ws_comments(text, i)
            if text.startswith(",", i):
                i += 1
            elif not text.startswith("]", i):
                raise HclError("list items must be separated by commas")
    if c == "{":
        obj: dict = {}
        i += 1
        while True:
            i = _skip_ws_comments(text, i)
            if text.startswith("}", i):
                return obj, i + 1
            if text.startswith('"', i):
                end = _skip_string(text, i)
                key = json.loads(text[i:end])
                i = end
            else:
                m = KEY_RE.match(text, i)
                if not m:
                    raise HclError("object key is not understood")
                key, i = m.group(0), m.end()
            i = _skip_ws_comments(text, i, newlines=False)
            if not (text.startswith("=", i) or text.startswith(":", i)):
                raise HclError(f"object key {key!r} has no value")
            if key in obj:
                raise HclError(f"object key {key!r} is repeated")
            obj[key], i = _parse_value(text, i + 1, depth + 1)
            i = _skip_ws_comments(text, i, newlines=False)
            if text.startswith(",", i):
                i += 1
            elif i < len(text) and text[i] == "}":
                continue
            elif i < len(text) and text[i] != "\n":
                raise HclError("object entries are separated by a comma or a new line")
    for word, value in (("true", True), ("false", False), ("null", None)):
        if text.startswith(word, i) and not re.match(
            r"[A-Za-z0-9_.-]", text[i + len(word) : i + len(word) + 1]
        ):
            return value, i + len(word)
    m = NUMBER_RE.match(text, i)
    if m and not re.match(r"[A-Za-z0-9_.-]", text[m.end() : m.end() + 1]):
        s = m.group(0)
        return (float(s) if "." in s else int(s)), m.end()
    raise HclError(f"not a simple literal: {text[i : i + 30]!r}")


def _literal(expr: str):
    """Evaluate a literal expression. Anything else is an HclError."""
    value, end = _parse_value(expr, 0)
    if _skip_ws_comments(expr, end) != len(expr):
        raise HclError(f"trailing text after a value: {expr[end:].strip()[:30]!r}")
    return value


def parse_assignments(text: str, source: str = "<text>") -> dict:
    """The top-level `name = literal` lines of a tfvars-style file.

    Fails closed: a block, a heredoc, a repeated name, a value that is not a
    simple literal, or anything else on a top-level line is an HclError.
    """
    out: dict = {}
    i = 0
    while True:
        i = _skip_ws_comments(text, i)
        if i >= len(text):
            return out
        m = NAME_RE.match(text, i)
        if not m:
            raise HclError(f"{source}: unexpected text at top level")
        name = m.group(0)
        i = _skip_ws_comments(text, m.end(), newlines=False)
        if not text.startswith("=", i) or text.startswith("==", i):
            raise HclError(f"{source}: {name}: expected '=' (blocks are not understood)")
        if name in out:
            raise HclError(f"{source}: {name} is assigned twice")
        start = _skip_ws_comments(text, i + 1, newlines=False)
        end = _read_expression(text, start)
        if not text[start:end].strip():
            raise HclError(f"{source}: {name}: empty value")
        try:
            out[name] = _literal(text[start:end])
        except HclError as exc:
            raise HclError(f"{source}: {name}: {exc}") from exc
        i = end


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
