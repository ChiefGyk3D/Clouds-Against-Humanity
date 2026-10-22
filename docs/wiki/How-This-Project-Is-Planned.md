# How this project is planned

> Prerequisites: [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) and the [Roadmap](Roadmap.md). This page is about how the work is organized, not what the stages are.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

The work is planned the way a small team plans software: a written backlog, a size on every item, two-week sprints, a review at the end of each, and a definition of done. The plan lives in GitHub, next to the code, so a change to the plan is as visible as a change to the code.

- **The board:** the [Clouds Against Humanity project](https://github.com/users/ChiefGyk3D/projects/4) (All Items, Board, Roadmap, Sprint, Epics, Bugs, Blocked, By area, Security, Docs, Done log and Agents at work views, among others). It is laid out the same way as the board of the author's Hammunition suite, so one reading habit works for both.
- **The backlog:** the repository's [issues](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues), grouped into epics and milestones.
- **The board as code:** `board.yaml` in the repository root. It names every field, option, iteration and view, and [Scrum Around and Find Out](https://github.com/ChiefGyk3D/scrum-around-and-find-out) (SAFO) creates and checks the board from it.

## The shape of the plan

| Level | What it is | Where |
|---|---|---|
| Epic | One theme, such as stage 2 telemetry. Labeled `epic`, with sub-issues. Has a start and a target date that draw its bar on the Roadmap view | Issue |
| Milestone | The same theme as a release gate, with a due date | Milestone |
| Issue | One piece of work with a reason, a "done when" list and, where it applies, a gate | Issue, sub-issue of an epic |
| Sprint | A two-week slice, Tuesday to Monday | Board field |

The eight epics are operations and gates, stage 1 hardening, stage 2 telemetry, stage 3 workloads, the edge and DMZ, multi-cloud, learning and wiki, and process.

## Sprints and what "scheduled" means

Sprints run two weeks from a Tuesday. Sprint 1 starts on 2026-10-20; eight are defined, through 2027-02-08. Anything with a sprint is scheduled. Anything without one is backlog: wanted, ordered by priority, not promised.

Dates beyond the sprint calendar are **indicative**. A milestone for stage 3 or the edge carries a date so the Roadmap view has a shape, but those stages wait on a cost decision and on earlier stages, and the date moves at the sprint review when the facts do. A moved date is not a failure; a date nobody revisits is.

## Capacity

The maintainer has a day job and works on this in the evenings and at weekends, and has other projects. The plan is built so he can also rest:

- The sprint load counts the maintainer's own hours: the items whose Agent is **You**. About 10 to 12 hours is the ceiling for one sprint, less around holidays.
- Items worked by agents are limited by the agents' budgets and by review time, not by his hours. At most three agent items are in flight at once, each with its own branch and worktree.
- Sizes convert to hours so a sprint can be added up: **S** is about 2 hours, **M** about 5, **L** about 12 and **XL** about 30. An XL is split into smaller issues before it is scheduled; none sits in a sprint.

## The flow of an issue

| Status | Meaning |
|---|---|
| Backlog | Not scheduled |
| Next | Scheduled for a sprint |
| In progress | Being worked, or a draft pull request is open |
| In review | A pull request is open and checks and reviews are running |
| Blocked | Needs the maintainer or an answer from outside |
| Done | Closed or merged, with the date in **Done on** |

SAFO moves a card as GitHub events happen: an opened issue is Backlog, a ready pull request is In review, a merged one is Done. The sprint, size, area, kind, epic, priority and agent are set when an issue is planned. `safo reconcile` adds the missing pull-request cards and sets Done on from the close or merge date; it is not typed in by hand.

## The board: fields

| Field | What it holds |
|---|---|
| Status | Backlog, Next, In progress, In review, Blocked, Done (table above) |
| Area | The theme: operations and gates, stage 1 hardening, stage 2 telemetry, stage 3 workloads, edge and DMZ, multi-cloud, learning and wiki, process, security (threat models, hardening reviews, advisories), docs (wiki pages, specs and README) |
| Kind | Feature, Bug, Decision, Lesson, Chore, Docs, Release or Epic. A Decision is a ruling, a design note or an approval; a Lesson is wiki teaching |
| Epic | Which of the eight epic issues the card belongs to |
| Priority | P0 now, P1 soon, P2 later, P3 someday |
| Size | S, M, L, XL, as in the capacity section |
| Agent | Claude, Codex, Copilot or You |
| Sprint | S1 to S8, a two-week iteration |
| Start date, Target date | Draw the card's bar on the Roadmap view |
| Done on | The day the card closed or merged |
| Decision | A free-text line: the ruling, when the card is a decision |

Pull requests are cards too. A merged pull request is Done with its Done on date, an open one is In review, a draft is In progress. That is what makes the Done log a history of what actually shipped, and not only of what was planned.

## The board: views

| View | Shows |
|---|---|
| All Items | Everything, unfiltered |
| Board | Cards by Status, without Done |
| Roadmap | Bars from Start date to Target date, without Done |
| Sprint | The current sprint only |
| Sprint plan | A table for planning, without Done |
| Epics | The eight epic issues |
| Bugs | Kind Bug, without Done |
| Blocked: needs the maintainer | Status Blocked |
| By area | Open work grouped by Area |
| Security | Area Security, without Done |
| Docs | Area Docs, without Done |
| Backlog | Status Backlog |
| Done log | Everything with Status Done |
| Agents at work | In progress, In review and Next, grouped by Agent |

How to read three of them:

- **Done log:** sort by Done on, newest first. Each row is one thing that finished, with its Kind and Epic. A row that is a pull request says what changed; a row that is an issue says what was asked.
- **Agents at work:** which agent has what in flight. More than three agent items In progress or In review means the review queue, not the agents, is the limit.
- **Blocked: needs the maintainer:** every card waiting on a decision or a step only the maintainer can take (an approval, a console check, a rotation). If this view is empty, the agents are not waiting on anyone. If it is long, the next planning session starts here.

## Definition of ready

An issue goes into a sprint when it has a reason, a "done when" checklist, a size, an owner (the maintainer or an agent), and its gate named: the decision, approval or earlier issue it waits on. An issue that cannot say what done looks like is a question, not a task.

## Definition of done

A pull request closes its issue when all of these are true:

1. The checks are green, including the `CI green` gate and the secret scan.
2. Tests exist for what changed, and a test that should fail without the change was shown to fail.
3. The docs and the wiki say what is now true, including the Roadmap status line.
4. A change that touches live infrastructure shows its plan, and the maintainer read it. A plan that replaces a droplet is discarded unless that was the point.
5. Risky changes had a second review: an adversarial pass by an agent that did not write the code.
6. The maintainer merged it. Agents open pull requests; they do not decide what ships.

## Who does the work

Work is routed by what it is, from measurements recorded in SAFO:

| Kind of work | Goes to |
|---|---|
| Decisions, approvals, anything that changes a live account or a credential | The maintainer |
| Implementation from a written description, wiki pages, tests | A Sonnet agent |
| Security-sensitive changes | Built by one agent, attacked by another before merge |
| Text in, text out (summaries, triage, drafts) | The local model first, checked before anything is applied |

The Agent field on the board names the intended owner, and the Agents at work view groups by it:

| Agent | Used for |
|---|---|
| Claude | Technical and integration work, and the orchestration of the others |
| Codex | Adversarial code review |
| Copilot | Pull request review |
| ChatGPT | Public and non-technical wording |
| Ollama | Local text triage and summaries |
| RAG | Retrieval answers over the project's docs and issues |
| You | Maintainer-only steps |

 The maintainer-only steps carry the `needs-maintainer` label so they are easy to filter.

## The rhythm

- **Planning** (the first day of a sprint): pull the next ready items from the top of the backlog until the load is full. Check the maintainer's hours first.
- **During:** one branch per issue, one pull request per change, small enough to review.
- **Review** (the last day): post a project status update (`safo status --post` builds it from the board, counted in code), note what slipped and why, and re-order the next sprint. The first review is scheduled as an issue so the habit exists from day one.
- **Keeping the board current:** a user-owned GitHub Project cannot be written by an App, so the maintainer runs `safo --board board.yaml reconcile` from his own login on a timer. It adds new issues, marks closed ones Done and fills the area. No token is stored in CI.

## Writing style: American English

American English spelling is the standard for everything written in this repository: the README, the wiki, the docs, comments and commit text. The maintainer is American, and one spelling keeps search and review simple.

| Write | Not |
|---|---|
| defense, behavior, color, favor | `defence`, `behaviour`, `colour`, `favour` |
| organize, recognize, analyze, authorize | `organise`, `recognise`, `analyse`, `authorise` |
| center, meter, fiber | `centre`, `metre`, `fibre` |
| license (noun and verb), catalog, gray, program | `licence`, `catalogue`, `grey`, `programme` |
| labeled, canceled, modeling, traveling | `labelled`, `cancelled`, `modelling`, `travelling` |
| while, among, practice (noun and verb) | `whilst`, `amongst`, `practise` |

Exceptions, kept exactly as written: direct quotes and vendor text, code and configuration (identifiers, keys, command and file names, URLs), and product or proper names. A status value that a tool returns, such as the `cancelled` result of a GitHub job, is a literal, not prose. Inside code fences and inline code the spelling is left alone.

`tests/test_american_english.py` fails when a clear British spelling appears in any Markdown page, in a Python, HCL, YAML or shell comment or docstring, or in a threat-model description, outside code fences, inline code and URLs. `tests/test_markdown_anchors.py` checks that every link to a heading still points at one. If a page must keep one on purpose, add a line to `docs/american-english-allowlist.txt` with the page, the word and the reason.

## Feedback from readers

Readers are part of the plan. [Give feedback and open an issue](Give-Feedback-and-Open-an-Issue.md) explains how to report a mistake, a failed command or a question, and the repository has issue forms, a `SECURITY.md` and a `CONTRIBUTING.md` for it. A report becomes an issue like any other and goes through the flow above.

Every new lesson page ends with a one-line feedback footer placed just before its **Next** line, so a reader who finds a mistake is one click from the how-to:

```
Found a mistake or a command that failed? [Give feedback and open an issue](Give-Feedback-and-Open-an-Issue.md).
```

Lessons written before this footer existed get it as they are next edited; the foundations and deception lessons do not carry it yet.

## Changing the plan

Plans change in the open. To add work, open an issue with a reason and a "done when" list. To change the sequence or the board's shape, open a pull request: `board.yaml` is reviewed like code, and `safo --board board.yaml audit` reports where the live board differs from the file. A few settings (the Roadmap view's date fields, view grouping, adding an option to a field that already holds values and the project's built-in workflows) cannot be set through GitHub's API; `board.yaml` lists them under `ui_only` so they are checked by eye.

Next: [Roadmap](Roadmap.md).
