# Data formats and config files: JSON, YAML, HCL and the rest

Side page to the start-from-zero pages. Read it after [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) (core step 5) and before the YAML workflow on [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) and the `.tf` files on [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) start to look like noise. It does not teach JSON from the ground up: [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md#json-in-five-minutes) does that in five minutes, and this page builds on it. Next: [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the Bash half was run, the PowerShell half was not.** On **2026-10-21** I ran every Bash command on this page on Linux, with Python 3.13.5, PyYAML 6.0.2, `jq` 1.7, `xmllint` (libxml 20914) and OpenTofu 1.12.6, and pasted the output, trimmed to the lines that matter. I did **not** run any PowerShell, on any system: every PowerShell block is written from Microsoft's documentation and marked **est.** (estimate) where I am least sure. I did not run `yamllint`, and I did not run anything on macOS or Windows. Standards and tool documentation were read on **2026-10-21**; see the [claims register](#claims-register). Output varies with your versions.

> **Prerequisites.** [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) (so "a file that describes infrastructure" is a familiar idea) and a terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md) goes deeper than [Git from zero](Git-From-Zero.md#what-a-terminal-is)). No account, no cloud and no money: every exercise runs on your own computer. About 2.5 hours with the exercises (est.). The reading and the exercises are free, and they stay free.

## What you will be able to do

- Say which format a file is (JSON, YAML, HCL, TOML, INI, CSV, XML) from a glance at its first lines, and name this repository's examples of each.
- Read and write JSON, YAML and HCL, and spot the classic mistakes: indentation, quotes, and trailing commas.
- Validate a file with a free tool on your own computer, read the error, and fix it.
- Explain the "Norway problem" (a value that quietly changes meaning because a parser guessed its type) and two relatives of it.
- Convert between formats (CSV to JSON, JSON to CSV, YAML to JSON) and say what is lost on the way.
- Explain why YAML in CI breaks on one space, and why a one-space mistake is sometimes worse when it does **not** break.
- Say why you never call an unsafe loader on a file you did not write.
- Read one short regular expression (a pattern for matching text) and write two.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| JSON | [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md#json-in-five-minutes): the shapes and three mistakes. | Reading and validating JSON files, duplicate keys, and where this repository uses it as configuration. |
| HCL | The [infrastructure as code](What-Is-Infrastructure-as-Code.md) page names it; [Terraform reference](Terraform-Reference.md) walks resources. | How to read a `variable` block and what the punctuation means. |
| YAML | [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) says a workflow is "a YAML file" and shows no YAML rules. | Indentation, types, quoting, anchors, and the gotchas. |
| Environment variables | [The terminal and your first script](Terminal-and-Your-First-Script.md#environment-variables-and-path). | One section here on how config reaches a program. |
| Validation and conversion | Nothing. | How to check a file before CI does, and how to convert one. |
| Regular expressions | Nothing; a pattern is used on the [CI page](CI-Tests-and-Cost-Gate.md) and in the stacks without being explained. | Two patterns, read and written. |

## Why there are so many formats

A **configuration file** is a text file that tells a program how to behave: which region, which size, which tests to run. A **data format** is an agreed way of writing structured information as text, so that two programs (or a program and a person) read it the same way. To **parse** a file is to read the text and turn it into the program's own structures: lists, named values, numbers. If the text breaks the format's rules, parsing fails and you get a **syntax error**.

There are many formats because they trade differently between two readers: a person who edits the file, and a program that reads it. The short field guide, with this repository's own examples:

| Format | Looks like | Good at | In this repository |
|---|---|---|---|
| **JSON** | `{ "stage": 1 }` | Programs talking to programs; strict and small. | `stacks/*/cost.json`, `docs/cost-prices.json`, `docs/settings.json` |
| **YAML** | `stage: 1` and indentation | People writing nested settings. | `.github/workflows/ci.yml`, `.spacelift/config.yml` |
| **HCL** (HashiCorp Configuration Language) | `variable "region" { ... }` | Describing infrastructure, with expressions. | every `.tf` file under `stacks/` and `modules/` |
| **TOML** | `[section]` and `key = "value"` | Simple settings files. | none in this repository; Python tools use it for their settings (est.) |
| **INI** | `[section]` and `key = value` | Very old, very simple settings. | none |
| **CSV** | `name,kind,size` | Tables: rows and columns. | none; it is how spreadsheets export |
| **XML** | `<resource name="a"/>` | Documents with a strict structure. | none |

A format is not the same thing as a **file extension**: the extension (`.json`, `.yml`) is a hint to people and tools, and the content decides. A file named `.yml` that contains JSON works as YAML, because JSON is close to a subset of YAML (est.; the YAML 1.2 specification says its goal was to make JSON a subset, which I did not read in full).

## JSON in this repository

You met JSON on the [APIs page](APIs-and-Tokens-From-Zero.md#json-in-five-minutes): objects in `{}`, arrays in `[]`, strings in double quotes, numbers, `true`, `false`, `null`. Here is the same thing as a configuration file. Each stack that costs money has a `cost.json` that lists what it builds. This is the one for `stacks/10-access`:

```json
{
  "stage": 1,
  "resources": [
    { "name": "connector-a", "kind": "droplet", "size": "s-1vcpu-1gb", "backups": false },
    { "name": "connector-b", "kind": "droplet", "size": "s-1vcpu-1gb", "backups": false }
  ]
}
```

It is an object with a number (`stage`) and an array (`resources`) of two objects. Two programs read this one file: the cost gate (see [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md)) prices it, and the stack's `main.tf` builds from it with one line of HCL (read in `stacks/10-access/main.tf`): `cost = jsondecode(file("${path.module}/cost.json"))`. One file, two readers, so the price and the machine cannot drift apart. That is the point of a data format.

What JSON does **not** allow, and which breaks files every day:

- **Comments.** There is no comment syntax at all.
- **Trailing commas.** `[1, 2, ]` is an error.
- **Single quotes.** Strings and names use double quotes only.
- **Repeated names.** The standard says names in an object "SHOULD be unique" ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)), which is not a ban. What a parser does with `{"size": "small", "size": "huge"}` is up to it. Python keeps the last one and says nothing (you will see that in Exercise 3). The cost gate refuses such a file on purpose, because "the value enforced would differ from the one a reviewer reads first" is how a limit gets bypassed (read in `scripts/cost_check.py`).

One more shape you will meet in logs: **JSON Lines**, one complete JSON object per line, no commas between them. A log shipper writes events this way because a program can read it line by line without loading the whole file.

## YAML: indentation is the structure

**YAML** ("YAML Ain't Markup Language") writes the same shapes as JSON with fewer symbols. A GitHub Actions **workflow** (a file that tells GitHub what to run when something happens) is YAML. A fragment of this repository's `.github/workflows/ci.yml`:

```yaml
permissions: {}

jobs:
  python:
    with:
      python-versions: '["3.12", "3.13"]'
```

How to read it:

- `name: value` is a **mapping**: a set of named values, like a JSON object. A colon followed by a space separates them.
- A line starting `- ` is an item in a **sequence** (a list), like a JSON array.
- **Indentation is the structure.** `python:` is inside `jobs:` because it is indented under it. There are no braces to tell you where a block ends; the next line that is indented less than it does. Use **spaces**, and use the same number at each level (two is the convention in this repository).
- `{}` is an empty mapping: `permissions: {}` grants nothing.
- `#` starts a comment, which JSON cannot do.
- The last line is a string that **contains JSON**. The single quotes make the whole thing one piece of text, and the shared workflow it is passed to parses the inside. YAML does not look inside.

YAML has two more features that cause trouble, covered below: **anchors** (a way to reuse a block) and **tags** (a way to say what type a value is).

### The types YAML guesses

In JSON `"3.10"` is text and `3.10` is a number, because the quotes say so. In YAML you often leave quotes off, so the parser **guesses** the type from the shape of the value. That is convenient and dangerous. Run on this repository's own workflow file, with PyYAML (the Python YAML library; this repository's CI installs `pyyaml==6.0.2`, read in `.github/workflows/ci.yml`), the top of `ci.yml` parses like this (trimmed):

```text
{'name': 'CI', True: {'push': {'branches': ['main']}, 'pull_request': None}, 'permissions': {}, ...
```

Look at the second key. The file says `on:`, which is how GitHub's [documentation](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions) writes it. This parser turned the word `on` into the boolean **True**. GitHub reads the file correctly; the lesson is for your own scripts: a generic loader may not hand you the text you wrote. The older YAML 1.1 type list counts `y`, `yes`, `on`, `no`, `off` and their capitalized forms as booleans ([yaml.org bool type](https://yaml.org/type/bool.html), read 2026-10-21), and the newer YAML 1.2 core schema only counts `true`, `True`, `TRUE`, `false`, `False` and `FALSE` ([YAML 1.2.2 spec](https://yaml.org/spec/1.2.2/), read 2026-10-21). Which rules a given tool follows varies, and I did not check which one GitHub's parser uses (est.).

That gives the famous **Norway problem**. Write a list of two-letter country codes:

```yaml
countries:
  - GB
  - NO
  - SE
```

and a YAML 1.1-style parser reads `NO` as the boolean false: `['GB', False, 'SE']` (you will run this in Exercise 6). Norway is gone from the list. Two relatives, from the same run:

- `python: 3.10` becomes the **number** `3.1`, so a CI matrix asks for Python 3.1. Quote it: `"3.10"`. This is why `ci.yml` quotes its list of versions.
- `mode: 0755` becomes `493`: a leading zero meant octal (base 8) to that parser. The YAML 1.2 table lists octal with a `0o` prefix, so a 1.2 parser would read the same text as 755. Same file, two answers.

The defense is unglamorous: **quote anything that is text**, even when you do not have to.

### Anchors and the other parts to be careful with

An **anchor** (`&name`) labels a block and an **alias** (`*name`) pastes it somewhere else. A common use is `<<: *name`, a **merge key** that copies a whole mapping in (a YAML 1.1 convention that not every parser supports; est.). It saves typing and costs reviewability:

```yaml
defaults: &defaults
  kind: droplet
  backups: false
a:
  <<: *defaults
  name: connector-a
```

A reviewer must follow the arrow to know what `a` is. A tool that reads an untrusted file has a worse problem: an alias can point at a huge nested structure, so a small file can expand into a very large one (est.; general knowledge). This repository's `tests/test_secret_separation.py` **refuses anchors and aliases** in `.spacelift/config.yml` outright, and refuses duplicate keys; both are read in that file's loader.

Duplicate keys deserve the same suspicion as in JSON: the YAML specification says mapping keys "must be unique" ([YAML 1.2.2](https://yaml.org/spec/1.2.2/)), yet PyYAML keeps the last one without a warning (you will see it in Exercise 7).

Two more habits. A string with a colon-space or a leading special character (`:`, `#`, `*`, `&`, `!`, `-`, `[`, `{`) needs quotes. And a `version: "1"` in `.spacelift/config.yml` is quoted on purpose: it is the text `1`, not the number (whether Spacelift would also accept the number I did not check).

## HCL and OpenTofu syntax

**HCL** is the language OpenTofu (and Terraform) files are written in. It looks like YAML crossed with JSON, and it has expressions, which JSON and YAML do not. The pieces:

- A **block** has a type, optional **labels** in quotes, and braces: `variable "region" { ... }`. `resource "digitalocean_droplet" "web" { ... }` has two labels.
- Inside a block, an **argument** is `name = value`. The `=` is HCL's separator, where YAML uses `:`.
- A **value** is a string in double quotes, a number, `true` or `false`, a **list** `["a", "b"]`, or an **object/map** `{ key = "v" }`. Commas and newlines both separate items.
- An **expression** computes a value: `var.region` reads a variable, `local.cost` reads a local value, `"${path.module}/cost.json"` builds a string around a value (`${...}` is interpolation), and functions such as `can(...)`, `regex(...)`, `jsondecode(...)` and `file(...)` are called with parentheses.
- Comments: `#`, `//` for one line, `/* ... */` for several ([OpenTofu syntax](https://opentofu.org/docs/language/syntax/configuration/)).
- `tofu fmt` rewrites a file into the standard layout, and `tofu fmt -check` only reports whether it is already formatted (exit code 0 if so).

The block you will read in Exercise 8 is a **variable**: a named input to a stack. Here is the same shape, in a small file you will build at run time, in a sample that mirrors the one in `stacks/00-foundation/variables.tf`:

```hcl
variable "region" {
  type        = string
  default     = "tor1"
  description = "A region slug, for example tor1."

  validation {
    condition     = can(regex("^[a-z]{3}[0-9]$", var.region))
    error_message = "region must be three lowercase letters and a digit."
  }
}
```

Read it top to bottom. `type = string` says the value is text. `default` is used when nobody supplies one. `description` is for people. The nested `validation` block is a rule that runs before anything is built: `condition` must come out true, or OpenTofu stops and prints `error_message`. Here `regex(...)` tests the value against a pattern and `can(...)` turns "the test raised an error" into plain false. A value that fails, such as `TORONTO`, stops the run **before** it touches a cloud. That is the cheapest place to catch a typo.

A value can come from several places. If none supplies one, the `default` is used. Otherwise OpenTofu uses the **last** value it finds in this order, from weakest to strongest: environment variables (`TF_VAR_region`), then `terraform.tfvars`, then `terraform.tfvars.json`, then `*.auto.tfvars` and `*.auto.tfvars.json` files, then `-var` and `-var-file` on the command line ([OpenTofu variables: precedence](https://opentofu.org/docs/language/values/variables/), read 2026-10-21). So an environment variable is the **weakest** source: a `-var` or a tfvars file overrides it (you will see that in Exercise 8). The `.tfvars` file is also HCL, but values only: a bare `region = "tor1"` per line. A `.tf.json` file is the JSON spelling of the same language ([OpenTofu JSON syntax](https://opentofu.org/docs/language/syntax/json/)). [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md) says which values must never be committed.

## TOML, INI, CSV and XML, a paragraph each

**TOML** ("Tom's Obvious, Minimal Language") is a settings format designed so it "maps unambiguously to a hash table" ([TOML 1.0](https://toml.io/en/v1.0.0)): `[section]` headers and `key = "value"` lines, with real types (strings are quoted, numbers are not) and no indentation rules. It is the kind of file a Python or Rust tool keeps its settings in. **INI** is the older cousin: `[section]` and `key = value`, with no standard that I could point you to (est.), so every program reads it slightly differently; Python's `configparser` returns every value as text, even `port = 8080` (you will see that in Exercise 9). **CSV** (comma-separated values) is a table: one row per line, columns separated by commas, a header row naming them. The catch is that a value may contain a comma, so it must be wrapped in double quotes, and a double quote inside is doubled ([RFC 4180](https://www.rfc-editor.org/rfc/rfc4180), read 2026-10-21): cutting each line at every comma by hand gets `"lab, east"` wrong, so use a real CSV reader. Spreadsheet programs also like to "helpfully" reinterpret values such as `0755` or a date when they open a CSV (est.), the same guessing problem as YAML's. **XML** wraps data in matching tags, `<resource name="a"/>`; it is older, wordier and strict (every tag must close, and a mismatch is an error), and you meet it in many enterprise tools, Windows and Java settings, and office documents. An XML parser that follows references to outside files can be tricked into reading a local file it should not (est.; a vulnerability class called XXE), so for untrusted XML use a parser configured to refuse that.

## Reading, validating and converting

Three verbs you use on every file:

- **Read**: open it and say what it is, as in Exercise 1.
- **Validate**: ask a program whether the text follows the format's rules. A **validator** (or **linter**, see [the terminal page](Terminal-and-Your-First-Script.md#lint-it)) reads without running or changing anything and exits `0` for good, nonzero for bad. Free tools already on most computers: `python3 -m json.tool` (JSON, Python's built-in; `python -m json.tool` on Windows), `ConvertFrom-Json` (PowerShell), `jq .`, `xmllint --noout`, `tofu fmt -check` and `tofu validate` (HCL), and a few lines of Python with PyYAML for YAML. `yamllint` is a dedicated YAML linter; I did not run it (est.).
- **Convert**: parse into one structure, then write that structure in another format. Every conversion drops something. YAML comments vanish in JSON. A CSV has no types, so every field arrives as text. JSON has no anchors, so a YAML merge key is expanded.

**Validity is not correctness.** A file can be perfect JSON and still wrong: `"backups": "false"` is valid text and a different type from `false`. For that you need a **schema**: a description of what a valid document looks like (which names, which types, which values). The standard for JSON is called JSON Schema (est.; I did not read it). This repository writes its checks as code: Exercise 2 ends with a ten-line check you can read in full.

## Config as code

Because configuration is just text, it can be treated like code: kept in git, changed by pull request, reviewed, tested, and rolled back. That is the thread through this wiki: [infrastructure as code](What-Is-Infrastructure-as-Code.md), [CI](CI-Tests-and-Cost-Gate.md), the [settings manifest](Settings-Reference.md). Three habits follow:

1. **One source of truth.** `cost.json` is read by both the cost gate and `main.tf`. `docs/settings.json` generates the Settings reference page, and CI runs the generator with `--check` so the page cannot go stale (read in `.github/workflows/ci.yml`).
2. **Validate before you merge.** CI parses the files, so a syntax error is caught on the pull request rather than in the middle of a deploy.
3. **Never put secrets in the file.** The `.spacelift/config.yml` file lists the **names** of the secrets a stack needs, for example `cah_doppler_env DIGITALOCEAN_TOKEN`, never a value. The values live in [Doppler](Doppler-and-Secrets.md).

### How a setting reaches a program

A third path besides files is the **environment variable**, a named value every program you start can read (the [terminal page](Terminal-and-Your-First-Script.md#environment-variables-and-path) covers it). OpenTofu reads `TF_VAR_region` as the variable `region`. The `.spacelift/config.yml` file uses this: its `TF_VAR_twingate_network=TWINGATE_NETWORK` entry means "fetch the Doppler secret named `TWINGATE_NETWORK` and export it as `TF_VAR_twingate_network`" (read in the comments of `scripts/spacelift/doppler-env.sh`). Prefer an environment variable to a command-line argument for a token: the arguments of a running program can usually be listed by other users on the machine and are saved in shell history, while an environment variable is not printed unless something prints it (est.; general behavior on Linux, which varies with how the machine is set up). Read [Where a secret must never live](APIs-and-Tokens-From-Zero.md#where-a-secret-must-never-live) for the longer list.

## Why YAML in CI breaks on one space

A CI workflow is YAML, and in YAML a space is a word of the language. There are three ways one space goes wrong, in order of how kind they are:

1. **A tab.** Indentation must use spaces; the YAML 1.2.2 specification says "tab characters must not be used in indentation". The parser stops with an error, and CI fails on the first line of the job. This one is loud, so it costs minutes.
2. **One space too many or too few at the wrong level.** Usually a parse error such as `mapping values are not allowed here`. Also loud.
3. **A shift to a different valid level.** The file still parses, and it now means something else. Moving the `env:` block of a step two spaces to the left makes it belong to the **job** instead of the step. No error. You will build this in Exercise 5, and it is the dangerous one, because nothing flags it and a normal review shows nearly the same text.

So the quiet failure is a review problem as much as a parsing one. Reviewers, note that `git diff -w` (and the "hide whitespace" toggle on a pull request, est.) **hides exactly the change that matters** in YAML. Exercise 5 shows it.

The defenses are cheap: an editor setting that turns the Tab key into spaces; a YAML linter or the project's own parse check in CI; and keeping each workflow short and flat so the nesting is easy to see.

## A safety note: never `yaml.load` on a file you do not trust

A YAML file can carry **tags** that say what Python object to build, and some loaders obey them. PyYAML's own documentation says: "It is not safe to call yaml.load with any data received from an untrusted source! yaml.load is as powerful as pickle.load and so may call any Python function" ([PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation), read 2026-10-21). In words: a loader that builds whatever the file asks for lets the file's author run code on your machine. The safe habit is to load with `yaml.safe_load`, which only builds plain lists, mappings, strings and numbers, and to treat **any** file from outside your control as hostile input: set a size cap, refuse duplicate keys and aliases (as this repository's loader does), and limit how deeply the file may nest. Exercise 10 shows `safe_load` refusing a tag. It does **not** run the dangerous case; that stays in words.

## Free theory path: a lab on your own computer

Everything in this section runs on your own computer, costs nothing, and touches no third-party server. Every exercise follows four steps: **predict** (write down what you expect first), **do**, **check**, **undo**. Commands are given for **Bash** (Linux, macOS Terminal, WSL, Git Bash) and **PowerShell** (Windows). The output shown is from the 2026-10-21 Bash run.

**You need:** a terminal; `python3` (on Windows `python` or `py -3`, depending on how it was installed); PyYAML for the YAML exercises (check with `python3 -c "import yaml"`; if that fails, install it into a virtual environment with `python3 -m venv .venv`, activate it, and run `python3 -m pip install pyyaml==6.0.2`, est.); and a clone of this repository so you can read its files. Optional extras that make some checks nicer: `jq`, `xmllint` and `tofu` (OpenTofu, [how it is installed](OpenTofu-Stacks-and-Modules.md)). Exercise 8 and parts of Exercise 9 are skipped, not failed, without them.

### Set up the lab folder

Put the path of your clone in `REPO`, make a scratch folder, and create the sample files. Everything is made at run time, so nothing here is a secret, and you can delete the folder at the end.

```bash
REPO=~/Clouds-Against-Humanity        # change to wherever your clone is
mkdir -p ~/formats-lab && cd ~/formats-lab
cp "$REPO/stacks/10-access/cost.json" good.json

cat > trailing.json <<'EOF'
{
  "stage": 1,
  "resources": [
    { "name": "connector-a", "kind": "droplet", "backups": false },
  ]
}
EOF
printf "{ 'stage': 1 }\n" > quotes.json
printf '{ "size": "small", "size": "huge" }\n' > dupe.json

cat > ok.yml <<'EOF'
jobs:
  test:
    runs-on: example-runner
    steps:
      - name: Test
        run: pytest
        env:
          MODE: strict
EOF
cat > shifted.yml <<'EOF'
jobs:
  test:
    runs-on: example-runner
    steps:
      - name: Test
        run: pytest
    env:
      MODE: strict
EOF
cat > onespace.yml <<'EOF'
jobs:
  test:
    runs-on: example-runner
    steps:
      - name: Test
        run: pytest
         env:
          MODE: strict
EOF
printf 'jobs:\n  test:\n\truns-on: example-runner\n' > tab.yml
cat > norway.yml <<'EOF'
countries:
  - GB
  - NO
  - SE
python: 3.10
mode: 0755
enabled: yes
quoted_version: "3.10"
EOF
cat > anchor.yml <<'EOF'
defaults: &defaults
  kind: droplet
  backups: false
a:
  <<: *defaults
  name: connector-a
b:
  <<: *defaults
  name: connector-b
  backups: true
EOF
printf 'size: small\nsize: huge\n' > dupe.yml
printf 'name,kind,size\nconnector-a,droplet,s-1vcpu-1gb\n"lab, east",droplet,s-1vcpu-512mb-10gb\n' > items.csv
ls
```

```powershell
$REPO = "$HOME\Clouds-Against-Humanity"      # change to wherever your clone is
New-Item -ItemType Directory -Force $HOME\formats-lab | Out-Null
Set-Location $HOME\formats-lab
Copy-Item "$REPO\stacks\10-access\cost.json" good.json

@'
{
  "stage": 1,
  "resources": [
    { "name": "connector-a", "kind": "droplet", "backups": false },
  ]
}
'@ | Set-Content -Encoding ascii trailing.json
"{ 'stage': 1 }" | Set-Content -Encoding ascii quotes.json
'{ "size": "small", "size": "huge" }' | Set-Content -Encoding ascii dupe.json

@'
jobs:
  test:
    runs-on: example-runner
    steps:
      - name: Test
        run: pytest
        env:
          MODE: strict
'@ | Set-Content -Encoding ascii ok.yml
@'
jobs:
  test:
    runs-on: example-runner
    steps:
      - name: Test
        run: pytest
    env:
      MODE: strict
'@ | Set-Content -Encoding ascii shifted.yml
@'
jobs:
  test:
    runs-on: example-runner
    steps:
      - name: Test
        run: pytest
         env:
          MODE: strict
'@ | Set-Content -Encoding ascii onespace.yml
"jobs:`n  test:`n`truns-on: example-runner" | Set-Content -Encoding ascii tab.yml
@'
countries:
  - GB
  - NO
  - SE
python: 3.10
mode: 0755
enabled: yes
quoted_version: "3.10"
'@ | Set-Content -Encoding ascii norway.yml
@'
defaults: &defaults
  kind: droplet
  backups: false
a:
  <<: *defaults
  name: connector-a
b:
  <<: *defaults
  name: connector-b
  backups: true
'@ | Set-Content -Encoding ascii anchor.yml
"size: small`nsize: huge" | Set-Content -Encoding ascii dupe.yml
@'
name,kind,size
connector-a,droplet,s-1vcpu-1gb
"lab, east",droplet,s-1vcpu-512mb-10gb
'@ | Set-Content -Encoding ascii items.csv
Get-ChildItem
```

(`-Encoding ascii` keeps PowerShell 5.1 from adding a byte-order mark, an invisible marker at the start of the file that Python's JSON reader rejects: `Unexpected UTF-8 BOM`. The PowerShell block is **est.**)

Now save two small Python helpers in the same folder with a plain-text editor (in Notepad choose "All files" so it does not add `.txt`).

`yamlcheck.py` parses each YAML file with the safe loader and shows what it means:

```python
# yamlcheck.py: parse each file with the safe loader and show what it means.
# Usage: python3 -I yamlcheck.py FILE.yml [FILE.yml ...]
import sys

import yaml

status = 0
for path in sys.argv[1:]:
    try:
        with open(path, encoding="utf-8") as f:
            print(path, "->", yaml.safe_load(f))
    except (OSError, yaml.YAMLError) as err:
        print(path, "-> ERROR:", str(err).replace("\n", " | "))
        status = 1
sys.exit(status)
```

`checkcost.py` is a tiny schema check for the `cost.json` shape (standard library only). It also refuses a repeated name, as the repository's cost gate does:

```python
# checkcost.py: a tiny schema check. Usage: python3 -I checkcost.py FILE.json
import json
import sys


def no_dupes(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key in an object")
    return dict(pairs)


def problems(data):
    out = []
    if not isinstance(data, dict):
        return ["top level must be an object"]
    if type(data.get("stage")) is not int:  # bool is a subclass of int, so isinstance would accept true
        out.append("stage must be a whole number")
    resources = data.get("resources")
    if not isinstance(resources, list):
        return out + ["resources must be a list"]
    for i, res in enumerate(resources):
        if not isinstance(res, dict):
            out.append(f"resources[{i}] must be an object")
            continue
        if not isinstance(res.get("name"), str) or res["name"] == "":
            out.append(f"resources[{i}].name must be a non-empty string")
        if res.get("kind") != "droplet":
            out.append(f"resources[{i}].kind must be 'droplet' here")
        if type(res.get("backups")) is not bool:
            out.append(f"resources[{i}].backups must be true or false")
    return out


try:
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f, object_pairs_hook=no_dupes)
except (OSError, ValueError) as err:
    print("FAIL:", err)
    sys.exit(1)
found = problems(data)
for line in found:
    print("FAIL:", line)
if found:
    sys.exit(1)
print("ok")
```

### Exercise 1: name that format (read only)

**Predict.** For each file, write down the format before you open it: `stacks/10-access/cost.json`, `.github/workflows/ci.yml`, `.spacelift/config.yml`, `stacks/00-foundation/variables.tf`, `stacks/00-foundation/terraform.tfvars.example`, `docs/settings.json`.

**Do (Bash).**

```bash
for f in stacks/10-access/cost.json .github/workflows/ci.yml .spacelift/config.yml \
         stacks/00-foundation/variables.tf stacks/00-foundation/terraform.tfvars.example docs/settings.json; do
  echo "=== $f"; head -n 4 "$REPO/$f" | cut -c1-90
done
```

**Do (PowerShell, est.).**

```powershell
foreach ($f in 'stacks\10-access\cost.json','.github\workflows\ci.yml','.spacelift\config.yml',
               'stacks\00-foundation\variables.tf','stacks\00-foundation\terraform.tfvars.example','docs\settings.json') {
  "=== $f"; Get-Content "$REPO\$f" -TotalCount 4
}
```

**Check.** `cost.json` and `settings.json` open with `{`: JSON. `ci.yml` opens with `name: CI`, and `config.yml` with `#` comment lines and then `version: "1"`: YAML (JSON could not start with a comment). `variables.tf` opens with `variable "region" {`: HCL. `terraform.tfvars.example` is `name = value` lines under comments: HCL, values only. If you guessed from the extension and the content disagreed, believe the content.

**Undo.** Nothing; you only read.

### Exercise 2: validate JSON, and read its shape

**Predict.** Does `good.json` (a copy of the real `cost.json`) validate? What will `python3 -m json.tool` print for a valid file?

**Do (Bash).**

```bash
python3 -m json.tool good.json | head -n 8; echo "exit=${PIPESTATUS[0]}"
python3 -I checkcost.py good.json; echo "exit=$?"
jq '.resources | length' good.json          # optional: needs jq
sed 's/"stage": 1/"stage": true/' good.json > stagebool.json
python3 -m json.tool stagebool.json > /dev/null; echo "syntax exit=$?"
python3 -I checkcost.py stagebool.json; echo "exit=$?"
```

**Do (PowerShell).**

```powershell
python -m json.tool good.json | Select-Object -First 8; "exit=$LASTEXITCODE"
python -I checkcost.py good.json; "exit=$LASTEXITCODE"
Get-Content good.json -Raw | ConvertFrom-Json | ConvertTo-Json -Depth 5      # est.
(Get-Content good.json -Raw | ConvertFrom-Json).resources.Count             # est.
(Get-Content good.json -Raw) -replace '"stage": 1','"stage": true' | Set-Content -Encoding ascii stagebool.json
python -m json.tool stagebool.json > $null; "syntax exit=$LASTEXITCODE"
python -I checkcost.py stagebool.json; "exit=$LASTEXITCODE"      # est.
```

**Check.** The first command prints the file re-indented with four spaces (`"stage": 1,` then `"resources": [` ...) and the exit code is `0`: valid JSON. (Reading `$LASTEXITCODE` after a pipe to `Select-Object` is **est.**; if it prints nothing useful, run the `json.tool` line without the pipe.) `checkcost.py` prints `ok`. `jq` prints `2`: two resources. The `stagebool.json` file, with `"stage": true`, is valid JSON (syntax exit `0`) but `checkcost.py` prints `FAIL: stage must be a whole number` and exits `1`: in Python `True` is a kind of integer (`bool` is a subclass of `int`), so the check uses an exact type test, `type(x) is int`, and not `isinstance`. In PowerShell, `ConvertFrom-Json` returns an object you can walk with dots (`.resources`), which is the same tree from the HCL and JSON sections ([ConvertFrom-Json](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/convertfrom-json), read 2026-10-21). The exit code is the part CI reads, as in [exit codes](Terminal-and-Your-First-Script.md#exit-codes-and-why-ci-lives-on-them).

**Undo.** Nothing.

### Exercise 3: break JSON on purpose

**Predict.** `trailing.json` has a comma after the last item; `quotes.json` uses single quotes; `dupe.json` repeats a name. Which of the three will the parser **accept**?

**Do (Bash).**

```bash
python3 -m json.tool trailing.json; echo "exit=$?"
python3 -m json.tool quotes.json;   echo "exit=$?"
python3 -m json.tool dupe.json;     echo "exit=$?"
python3 -I checkcost.py dupe.json;  echo "exit=$?"
```

**Do (PowerShell, est.).**

```powershell
foreach ($f in 'trailing.json','quotes.json','dupe.json') {
  python -m json.tool $f > $null; "$f exit=$LASTEXITCODE"
  try { Get-Content $f -Raw | ConvertFrom-Json -ErrorAction Stop | Out-Null; "$f PowerShell: accepted" }
  catch { "$f PowerShell: rejected: $($_.Exception.Message)" }
}
python -I checkcost.py dupe.json; "exit=$LASTEXITCODE"
```

**Check.** Python rejects the first two with a message that names the line and the column, and exits `1`:

```text
Illegal trailing comma before end of array: line 4 column 67 (char 99)
Expecting property name enclosed in double quotes: line 1 column 3 (char 2)
```

Count to that line and column in `trailing.json` and you land on the comma. `dupe.json` is **accepted** (exit `0`, and `json.tool` prints `"size": "huge"`: the first value silently vanished), which is why `checkcost.py` has to refuse it itself and says `FAIL: duplicate key in an object`. The PowerShell parser may accept or reject the first two depending on your PowerShell version (est.; the Windows PowerShell 5.1 and the current cross-platform PowerShell use different JSON readers). That is a real lesson: **parsers disagree about edge cases, so validate with the same tool your CI uses.**

**Undo.** Nothing; the samples stay in the lab folder.

### Exercise 4: read YAML safely, and meet `on: True`

**Predict.** What will the parsed key `on` look like in the real `ci.yml`: the text `on`, or something else?

**Do (Bash).**

```bash
python3 -I yamlcheck.py ok.yml
python3 -I yamlcheck.py "$REPO/.github/workflows/ci.yml" | cut -c1-110
```

**Do (PowerShell, est.).**

```powershell
python -I yamlcheck.py ok.yml
python -I yamlcheck.py "$REPO\.github\workflows\ci.yml" | ForEach-Object { $_.Substring(0, [Math]::Min(110, $_.Length)) }
```

**Check.** The first prints the nested structure of `ok.yml`: `{'jobs': {'test': {'runs-on': 'example-runner', 'steps': [{'name': 'Test', 'run': 'pytest', 'env': {'MODE': 'strict'}}]}}}`. The second prints a line that begins `.../ci.yml -> {'name': 'CI', True: {'push': {'branches': ['main']}, ...`. The key `on` became `True`. Nothing is wrong with the workflow; this is the parser's guess, and it is the first example of why you do not trust a YAML value you have not looked at.

**Undo.** Nothing.

### Exercise 5: break YAML on purpose, and watch git hide it

**Predict.** `tab.yml` uses a tab, `onespace.yml` has one space too many, and `shifted.yml` moves `env:` two spaces left. Which of the three will **not** produce an error?

**Do (Bash).**

```bash
python3 -I yamlcheck.py ok.yml shifted.yml onespace.yml tab.yml; echo "exit=$?"
git diff --no-index ok.yml shifted.yml; echo "exit=$?"
git diff --no-index -w ok.yml shifted.yml; echo "exit=$?"
```

**Do (PowerShell, est.).**

```powershell
python -I yamlcheck.py ok.yml shifted.yml onespace.yml tab.yml; "exit=$LASTEXITCODE"
git diff --no-index ok.yml shifted.yml; "exit=$LASTEXITCODE"
git diff --no-index -w ok.yml shifted.yml; "exit=$LASTEXITCODE"
```

**Check.** From the 2026-10-21 run:

```text
ok.yml -> {... 'steps': [{'name': 'Test', 'run': 'pytest', 'env': {'MODE': 'strict'}}]}}}
shifted.yml -> {... 'steps': [{'name': 'Test', 'run': 'pytest'}], 'env': {'MODE': 'strict'}}}}
onespace.yml -> ERROR: mapping values are not allowed here |   in "onespace.yml", line 7, column 13
tab.yml -> ERROR: while scanning for the next token | found character '\t' that cannot start any token |   in "tab.yml", line 3, column 1
```

Compare the first two lines. In `ok.yml`, `env` is inside the step; in `shifted.yml` it moved out to sit beside `steps`, so now it applies to the whole job. No error, different meaning. The tab and the extra space both fail, and both messages name a line and a column. The first `git diff` shows the two moved lines (exit `1`: git says "these differ"). The second, with `-w` (ignore whitespace), prints **nothing** and exits `0`: the one change that matters is invisible to it. In a YAML review, do not ignore whitespace.

**Undo.** Nothing.

### Exercise 6: the Norway problem and its relatives

**Predict.** For `norway.yml`: what do `NO`, `3.10`, `0755` and `yes` become? What happens to `"3.10"` in quotes?

**Do (Bash).**

```bash
python3 -I yamlcheck.py norway.yml
```

**Do (PowerShell, est.).**

```powershell
python -I yamlcheck.py norway.yml
```

**Check.**

```text
norway.yml -> {'countries': ['GB', False, 'SE'], 'python': 3.1, 'mode': 493, 'enabled': True, 'quoted_version': '3.10'}
```

`NO` became `False`, `3.10` became `3.1`, `0755` became `493`, `yes` became `True`, and only the quoted `"3.10"` stayed text. The parser was PyYAML 6.0.2; a different parser can answer differently, as the YAML section explained. Now fix the file: put quotes around `NO`, `3.10`, `0755` and `yes`, run it again, and check that each is text.

**Undo.** Nothing.

### Exercise 7: anchors and duplicate keys

**Predict.** In `anchor.yml`, what is the `backups` value of `a`, and of `b`? In `dupe.yml`, which `size` wins?

**Do (Bash).**

```bash
python3 -I yamlcheck.py anchor.yml dupe.yml
```

**Do (PowerShell, est.).**

```powershell
python -I yamlcheck.py anchor.yml dupe.yml
```

**Check.** `a` gets `kind: droplet` and `backups: False` from the anchor, and `b` gets `backups: True` because a value written next to the merge key overrides it. In `dupe.yml` the result is `{'size': 'huge'}`: the second value won and nothing said so. A reviewer who read the first line believes the size is `small`. This is why the repository's loader refuses duplicate keys and anchors in a security-relevant file.

**Undo.** Nothing.

### Exercise 8: read an HCL variable block

**Predict.** Open `stacks/00-foundation/variables.tf` in your clone and find `variable "region"`. Without running anything, answer: what is the default? Would `TOR1` pass? Would `toronto`? What does the block do when nobody sets a value?

**Do.** Read the block and its `validation` nested block (the sample earlier on this page has the same shape). Then, if you have OpenTofu, build and test the sample:

```bash
mkdir -p ~/formats-lab/tf && cd ~/formats-lab/tf
cp ../good.json cost.json
cat > variables.tf <<'EOF'
variable "region" {
  type        = string
  default     = "tor1"
  description = "A region slug, for example tor1."

  validation {
    condition     = can(regex("^[a-z]{3}[0-9]$", var.region))
    error_message = "region must be three lowercase letters and a digit."
  }
}

output "shout" {
  value = upper(var.region)
}
EOF
cat > main.tf <<'EOF'
locals {
  cost        = jsondecode(file("${path.module}/cost.json"))
  connector_a = one([for r in local.cost.resources : r if r.name == "connector-a"])
}

output "size_a" {
  value = local.connector_a.size
}
EOF
tofu fmt -check -diff; echo "fmt exit=$?"
tofu validate; echo "validate exit=$?"
tofu plan -no-color
tofu plan -no-color -var region=TORONTO; echo "exit=$?"
TF_VAR_region=nyc3 tofu plan -no-color
TF_VAR_region=TORONTO tofu plan -no-color -var region=nyc3    # -var beats the environment
cd ..
```

```powershell
New-Item -ItemType Directory -Force $HOME\formats-lab\tf | Out-Null
Set-Location $HOME\formats-lab\tf
Copy-Item ..\good.json cost.json
@'
variable "region" {
  type        = string
  default     = "tor1"
  description = "A region slug, for example tor1."

  validation {
    condition     = can(regex("^[a-z]{3}[0-9]$", var.region))
    error_message = "region must be three lowercase letters and a digit."
  }
}

output "shout" {
  value = upper(var.region)
}
'@ | Set-Content -Encoding ascii variables.tf
@'
locals {
  cost        = jsondecode(file("${path.module}/cost.json"))
  connector_a = one([for r in local.cost.resources : r if r.name == "connector-a"])
}

output "size_a" {
  value = local.connector_a.size
}
'@ | Set-Content -Encoding ascii main.tf
tofu fmt -check -diff; "fmt exit=$LASTEXITCODE"
tofu validate; "validate exit=$LASTEXITCODE"
tofu plan -no-color
tofu plan -no-color -var region=TORONTO; "exit=$LASTEXITCODE"
$env:TF_VAR_region = "nyc3"; tofu plan -no-color
$env:TF_VAR_region = "TORONTO"; tofu plan -no-color -var region=nyc3; Remove-Item Env:TF_VAR_region      # -var beats the environment
Set-Location ..
```

**Check.** The default is `tor1`; `TOR1` and `toronto` both fail the pattern (uppercase, and too many letters); with no value, the default is used. On the 2026-10-21 run (OpenTofu 1.12.6) `fmt -check` exits `0`, `validate` printed `Success! The configuration is valid.`, and the plain `plan` showed the outputs it would write, with no provider, no network and no cloud involved:

```text
Changes to Outputs:
  + shout  = "TOR1"
  + size_a = "s-1vcpu-1gb"
```

`shout` is `upper(var.region)` of the default and `size_a` came from `cost.json` through `jsondecode`: JSON read by HCL. The `TORONTO` run stopped with exit `1` and, among other lines:

```text
Error: Invalid value for variable

  on variables.tf line 1:
   1: variable "region" {
    │ var.region is "TORONTO"

region must be three lowercase letters and a digit.
```

and `TF_VAR_region=nyc3` produced `shout = "NYC3"`, the environment variable reaching the variable. The last command set the environment to the invalid `TORONTO` and `-var region=nyc3` on the command line: the plan succeeded with `NYC3`, because `-var` overrides the environment. To see `fmt` bite, add a badly spaced block and re-run `tofu fmt -check -diff`: it prints a diff and exits `3`. To see a syntax error, delete the last `}` of the `variable` block and run `tofu validate`: it reports `Unclosed configuration block` with the file and line, and exits `1`. Put the brace back.

**Undo.** Delete the folder: `rm -rf ~/formats-lab/tf` (Bash) or `Remove-Item -Recurse -Force $HOME\formats-lab\tf` (PowerShell). The run created no state file and no `.terraform` folder.

### Exercise 9: convert between formats

**Predict.** If you convert `items.csv` to JSON, will `connector-a`'s size be text or a number? Will `"lab, east"` stay one value?

**Do (Bash).**

```bash
python3 -I - <<'EOF'
import csv, json
with open("items.csv", newline="", encoding="utf-8") as f:
    print(json.dumps(list(csv.DictReader(f)), indent=2))
EOF
jq -r '.resources[] | [.name, .kind, .size, .backups] | @csv' good.json     # optional: needs jq
python3 -I - <<'EOF'
import json, yaml
with open("anchor.yml", encoding="utf-8") as f:
    print(json.dumps(yaml.safe_load(f)))
EOF
```

**Do (PowerShell, est.).**

```powershell
Import-Csv items.csv | ConvertTo-Json
(Get-Content good.json -Raw | ConvertFrom-Json).resources | Select-Object name,kind,size,backups | ConvertTo-Csv -NoTypeInformation
```

**Check.** The CSV becomes a list of two objects whose values are all text, and `"lab, east"` stays one value because the CSV reader obeys the quotes (cutting at every comma, `'"lab, east",droplet'.split(',')`, gives three pieces and a broken first one). The `jq` line prints `"connector-a","droplet","s-1vcpu-1gb",false` and a second row: a CSV has no types, so `false` is only a word in a column. The YAML-to-JSON line prints the merged structure with `backups` written out under both `a` and `b`: the anchor is gone, expanded. The [PowerShell cmdlets](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/import-csv) are `Import-Csv`, `ConvertTo-Json` and `ConvertTo-Csv`.

Two small ones to try if the tools are there, each from the Bash run: a TOML file read with Python's `tomllib` (`import tomllib; tomllib.load(open("t.toml","rb"))`) gives back typed values, while `configparser` on an INI file `[server]` / `port = 8080` gives `'8080'`, text. And `xmllint --noout file.xml` exits `0` for a well-formed XML file; with a mismatched tag it prints `Opening and ending tag mismatch` and a line number and exits `1`.

**Undo.** Nothing.

### Exercise 10: a safety note you can check

**Predict.** If a YAML file asks the loader to build a Python object by name, will `yaml.safe_load` do it?

**Do (Bash).**

```bash
python3 -I -c "
import yaml
try:
    yaml.safe_load('x: !!python/name:os.getcwd')
except yaml.YAMLError as err:
    print(type(err).__name__, '-', str(err).splitlines()[0])"
```

**Do (PowerShell, est.).**

```powershell
python -I -c "import yaml`ntry:`n    yaml.safe_load('x: !!python/name:os.getcwd')`nexcept yaml.YAMLError as err:`n    print(type(err).__name__, '-', str(err).splitlines()[0])"
```

**Check.** It prints `ConstructorError - could not determine a constructor for the tag 'tag:yaml.org,2002:python/name:os.getcwd'`. The safe loader has no way to build that object, so it refuses. You have just seen the protection; you have **not** seen the attack, and you should not try the unsafe loader on a file from anyone else. The rule in words: a YAML or JSON file from outside your control is **input to be validated, not instructions to be followed**: use the safe loader, cap the size, refuse duplicates and aliases, limit nesting, and validate the shape (as `checkcost.py` does) before using any value.

**Undo.** Nothing.

### Exercise 11: read a pattern, write two

A **regular expression** (regex) is a short pattern that describes which text matches, written with a few symbols: `[a-z]` is one lowercase letter, `{3}` means exactly three of the thing before it, `^` is the start of the text and `$` the end. The region check in Exercise 8 is a regex: `^[a-z]{3}[0-9]$` is "start, three lowercase letters, one digit, end".

**Predict.** Which of `tor1`, `TOR1`, `toronto`, `nyc3` and `ams33` match it?

**Do (Bash).**

```bash
for r in tor1 TOR1 toronto nyc3 ams33; do
  printf '%s\n' "$r" | grep -E '^[a-z]{3}[0-9]$' > /dev/null && echo "$r match" || echo "$r no match"
done
```

**Do (PowerShell).**

```powershell
foreach ($r in 'tor1','TOR1','toronto','nyc3','ams33') {
  if ($r -cmatch '^[a-z]{3}[0-9]$') { "$r match" } else { "$r no match" }
}
```

(`-cmatch` is the case-sensitive form; plain `-match` ignores case in PowerShell, so `TOR1` would match.)

**Check.** `tor1` and `nyc3` match; `TOR1`, `toronto` and `ams33` do not. Now **write two** yourself and test them against a few strings: one for a three-digit number (`^[0-9]{3}$`), and one for a droplet size such as `s-1vcpu-1gb` (the shape is `s-`, a digit, `vcpu-`, a digit, `gb`). Check each against one string it should match and one it should not. Regex is a sharp tool: a pattern written too loosely accepts text it should not, and a few badly written patterns can take very long on crafted input (est.; this is called catastrophic backtracking), so keep patterns anchored and simple, and prefer a plain check where one will do.

**Undo.** Nothing.

### Undo the whole lab

```bash
cd ~ && rm -rf ~/formats-lab
```

```powershell
Set-Location $HOME; Remove-Item -Recurse -Force $HOME\formats-lab
```

The lab left nothing behind: no setting changed and no account touched. If you made a virtual environment inside the folder for PyYAML, it went with the folder.

## Optional: the same ideas against a real account

None needed. Every exercise runs on your own computer, and this page has no cloud path, no account and no cost. If you want to see these formats on real infrastructure, the stage guides do that, with their own cost and teardown sections first; start from the [Reading order](Reading-Order.md).

## Build, break, detect, evade, defend

A small loop in the lab, all local. No real systems.

**Build.** A valid workflow-shaped YAML file (`ok.yml`) and a valid manifest (`good.json`), both of which parse and pass `checkcost.py`.

**Break.** Put a tab in the YAML (`tab.yml`), a trailing comma in the JSON (`trailing.json`).

**Detect.** Read the message. Both name a line and a column (`line 3, column 1`; `line 4 column 67`), and both exit nonzero, which is the number CI reads. A pull request that breaks syntax fails before merge.

**Evade.** Now make a file that is **valid and wrong**: `shifted.yml` (a block moved to a different level), `norway.yml` (a value whose type changed), `dupe.json` and `dupe.yml` (the second value hides the first), `"backups": "false"` (the right word in the wrong type). A syntax check passes every one of them. Try the last one: copy `good.json`, change one `false` to `"false"`, and run `python3 -m json.tool` (passes), then `checkcost.py` (fails with `resources[0].backups must be true or false`).

**Defend.**

- **Validate shape, not just syntax.** `checkcost.py` is a ten-line schema. This repository does the same with the cost gate for `cost.json` and with tests for its YAML.
- **Load strictly.** The repository's loaders refuse duplicate keys (JSON and YAML) and anchors in the Spacelift config; use `safe_load` on anything else.
- **Quote text.** Quote version numbers, country codes and anything that must stay text.
- **Run the formatter and the validator in CI.** `tofu fmt -check` and `tofu validate` for HCL, a parse check for YAML. The CI file here calls a shared OpenTofu workflow; what exactly that workflow runs lives there, and I did not read it.
- **Review whitespace in YAML.** Do not use `-w` on a YAML diff.
- **Keep secrets out.** Names in the file, values in Doppler.

**Flip the board.** You are now the person who wants to sneak a change past a reviewer. In which of the files above is a one-line change hardest to see? (The answer from this page: a shifted block, in a diff that ignores whitespace, or a duplicate key placed far below the first.) You are now the defender: what is the cheapest check that would catch it? (A strict loader that refuses duplicates, a schema that says where `env` may appear, and a review habit of reading the structure and not just the lines.) Write the answers in two sentences each; no real system is involved.

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| `Illegal trailing comma` or `Expecting property name enclosed in double quotes` | JSON: a trailing comma or single quotes. | The line and column in the message. |
| `found character '\t' that cannot start any token` | YAML: a tab. | Turn the editor's Tab key into spaces; search the file for a tab. |
| `mapping values are not allowed here` | YAML: a line indented one space too far. | The line named; compare it to its siblings. |
| A workflow runs but the setting is ignored or applies too widely | YAML: a block at the wrong level that still parses. | Print the parsed structure (Exercise 5), not only the text. |
| A version, country or setting changes value | YAML: an unquoted value read as a number or boolean. | Quote it. |
| `Unexpected UTF-8 BOM` | A Windows tool saved JSON with an invisible marker at the start. | Save as plain UTF-8 without a BOM (`-Encoding ascii` in PowerShell for ASCII content). |
| `Unclosed configuration block` | HCL: a missing `}`. | The file and line in the message; `tofu fmt` helps find it. |
| `Invalid value for variable` | A value failed the `validation` block. | Read `error_message`; it says what is allowed. |
| A CSV column count is wrong | A comma inside a value that was not quoted. | Use a CSV reader, not a split on commas. |

## Checkpoint

You are done when you can say, without looking:

- Which format a `.json`, a `.yml` and a `.tf` file in this repository is, and what each is used for.
- The three classic syntax mistakes (indentation, quotes, trailing commas), and which of them JSON forbids and YAML does not.
- What the Norway problem is, and what you do about it.
- Why a one-space shift can be worse than a tab.
- What `variable "region" { ... validation { ... } }` does.
- Why `yaml.safe_load` and not `yaml.load`.

## Claims register

All read-only requests, retrieved 2026-10-21. The commands were run on the author's Linux machine on the same date.

| Claim | Source | Status |
|---|---|---|
| JSON object names "SHOULD be unique"; a repeated name is not forbidden | [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259) | Read |
| The YAML 1.2 core schema has `true`/`True`/`TRUE`/`false`/`False`/`FALSE` as booleans and `0o` for octal; mapping keys "must be unique"; "tab characters must not be used in indentation" | [YAML 1.2.2 specification](https://yaml.org/spec/1.2.2/) | Read |
| The YAML 1.1 bool type lists `y`/`yes`/`on` and `n`/`no`/`off` and capitalized forms | [yaml.org bool type](https://yaml.org/type/bool.html) | Read (a draft-status page) |
| Which rules GitHub's own parser follows for `on` and `NO` | General knowledge | Not verified: **est.** |
| `yaml.load` on untrusted data is unsafe; use `safe_load` | [PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation) | Read (quoted above) |
| Workflow files use the `on:` key | [GitHub workflow syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions) | Read |
| CSV: fields with commas, quotes or line breaks are double-quoted; an inner quote is doubled | [RFC 4180](https://www.rfc-editor.org/rfc/rfc4180) | Read |
| TOML is designed to be easy to read and to map unambiguously to a hash table | [TOML 1.0.0](https://toml.io/en/v1.0.0) | Read |
| `python -m json.tool` validates and pretty-prints; Python's `json` module documents a "Repeated Names Within an Object" section and an option `--json-lines` | [Python json module](https://docs.python.org/3/library/json.html) | Read; behavior also run on Python 3.13.5 |
| `ConvertFrom-Json`, `ConvertTo-Json`, `Import-Csv` behavior and options | Microsoft Learn: [ConvertFrom-Json](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/convertfrom-json), [ConvertTo-Json](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/convertto-json), [Import-Csv](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/import-csv) | Cmdlet names and syntax read; **never run** |
| That PowerShell's JSON parser accepts or rejects a trailing comma or single quotes | General knowledge | Not verified: **est.** |
| OpenTofu comments (`#`, `//`, `/* */`), `tofu fmt -check`, `tofu validate`, `TF_VAR_` variables and variable precedence (environment weakest, `-var` strongest), `.tf.json` syntax | [syntax](https://opentofu.org/docs/language/syntax/configuration/), [fmt](https://opentofu.org/docs/cli/commands/fmt/), [validate](https://opentofu.org/docs/cli/commands/validate/), [variables](https://opentofu.org/docs/language/values/variables/), [JSON syntax](https://opentofu.org/docs/language/syntax/json/) | Read; behavior run on OpenTofu 1.12.6 |
| `cost.json` is read by `main.tf` through `jsondecode`; the loader refuses duplicate keys; the Spacelift config loader refuses anchors and duplicate keys; CI installs `pyyaml==6.0.2` and runs the settings generator with `--check` | `stacks/10-access/main.tf`, `scripts/cost_check.py`, `tests/test_secret_separation.py`, `.github/workflows/ci.yml` | Read in this repository |
| Aliases can expand a small file into a large one; XXE; catastrophic backtracking; `-w` on a pull request; arguments visible to other users; YAML 1.2's JSON-as-subset goal; JSON Schema; `yamllint`; `tomllib` first version | General knowledge | Not verified: **est.** |
| The Bash outputs on this page | Run on Linux, 2026-10-21 | Observed; they change with versions |

Not verified, plainly: the whole PowerShell track; macOS and Windows; `yamllint`; `jq` and `xmllint` only on the author's versions; what the shared OpenTofu workflow in `ci.yml` runs; which YAML version GitHub's parser implements.

Next: [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md), where the workflow file you can now read is first introduced, then [Variables, tfvars and secrets](Variables-Tfvars-and-Secrets.md) for the values that never belong in the file. It is a foundations side page on the [Reading order](Reading-Order.md).
