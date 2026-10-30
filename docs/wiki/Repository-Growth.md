<!-- GENERATED from the metrics snapshot by scripts/gen_repo_metrics.py. Do not edit this
page by hand: the snapshot is refreshed with `python3 -I scripts/gen_repo_metrics.py --refresh`
from a login that can read the repository. CI fails when this page, the snapshot and the
picture disagree. -->

# Repository growth: stars, forks and work per week

> Prerequisites: [Project status](Project-Status.md), which counts the same issues and pull requests this page charts by week.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

**Generated at:** 2026-10-23T00:14:32Z (UTC), from `ChiefGyk3D/Clouds-Against-Humanity`, which was created on 2026-10-10 (day 0 on the chart). The numbers come from GitHub and drift: this is a snapshot, not a live counter.

![Hand-drawn style chart: cumulative stars and forks since the repository was created, and weekly merged pull requests and closed issues](https://raw.githubusercontent.com/ChiefGyk3D/Clouds-Against-Humanity/metrics/repo-growth.png)

*The picture is redrawn every three hours by a workflow and shows its own as-of date. The table and totals below are the last committed snapshot, taken 2026-10-23.*

## How the stars line is built

GitHub does not let the workflow's built-in token read when each star happened, so the scheduled run cannot rebuild the star history. Instead the line has two parts. Up to the baseline date it comes from per-star times, read by the maintainer with their own login. After that date it is one point per day, the repository's star count that day, recorded by the workflow and joined by straight (dashed) segments. Those later points are daily counts, not per-star times, and the picture says so under the as-of date. Forks, merged pull requests and closed issues are read fresh on every run.

The metrics branch is mutable, so nothing on it is trusted. Each run checks that its snapshot still has the committed baseline's star history, keeps every earlier daily point exactly (only today's point may be added or replaced), and descends from the exact branch commit it read; the push is an exact compare-and-swap that can only succeed as a fast-forward from that commit (no other force), and the branch keeps at most one small commit per run (a run every three hours, and none is pushed when the bundle is byte-identical to the branch). A branch that moved, lost a point, or went more than 14 days without an update makes the run fail instead of publishing. A deliberate reset, for example after a new baseline is committed, is a separate reviewed step: delete the `metrics` branch and the next run starts a ledger afresh from the new baseline date.

To backfill the baseline, run `python3 -I scripts/gen_repo_metrics.py --refresh` locally with your own login: it asks for every star's time stamp, moves the baseline date to today and drops the ledger it replaces. The workflow never asks for star times (`--no-star-times`, chosen automatically when `GITHUB_ACTIONS` is true).

*As of 2026-10-23, 13 days after the repository was created: 465 stars, 21 forks, 165 pull requests merged and 35 issues closed.*

## How to read it honestly

- **Stars measure attention, not use.** A star is a click. It says someone saw the project and liked the idea, not that they ran it, finished a lesson or would recommend it. Forks are a little closer to use, and still a weak signal.
- **Early numbers are noisy.** A repository that is a few days or weeks old can jump on one share or one post and then flatten. One chart of a short history proves very little; read the shape over months.
- **The numbers come from GitHub and drift.** Accounts get deleted and spam stars get removed, so a count can fall. Times are in UTC, and a week runs Monday to Sunday.
- **Throughput is not quality.** Pull requests merged and issues closed show how much moved, not how good it is.
- **Only counts per day are stored.** The snapshot has no user names, no addresses and no tokens, and CI checks that.

## The numbers behind the chart

This table is the text version of the picture, one row per week (UTC, Monday to Sunday). The last two columns are running totals at the end of that week.

| Week of | New stars | New forks | PRs merged | Issues closed | Stars so far | Forks so far |
|---|---|---|---|---|---|---|
| 2026-10-05 | 2 | 0 | 16 | 0 | 2 | 0 |
| 2026-10-12 | 230 | 12 | 67 | 8 | 232 | 12 |
| 2026-10-19 (partial) | 233 | 9 | 82 | 27 | 465 | 21 |

Totals: 465 stars, 21 forks, 165 merged pull requests, 35 closed issues.

## How the picture is published every three hours, and the risk that remains

A workflow draws the picture every three hours and pushes it to an orphan branch named `metrics`, never to `main`. One job (read-only) fetches counts and draws; a second job validates the result again and pushes it. The second job needs `contents: write`, and GitHub cannot limit the built-in token to one branch, so that token is **repository-wide**. The workflow narrows what it does with it: the job holds no other secret and runs only the checked-in publish script, which refuses to write any ref but `refs/heads/metrics`, passes the token to the git commands that talk to GitHub and nowhere else, and never writes it to disk. That is a limit on this script, not access control.

The control that holds is a repository ruleset: restrict creation and updates of the `metrics` branch to the GitHub Actions app, block deletion and keep `main` protected as it is (pull request, status checks, no force push). Without that ruleset, anything that can run code in the publish job could write any branch.

## Reproduce it

Run these from a login that can read the repository. They show the same data without the script:

```bash
gh api repos/ChiefGyk3D/Clouds-Against-Humanity --jq .created_at
gh api repos/ChiefGyk3D/Clouds-Against-Humanity/forks --paginate --jq '.[].created_at'
gh pr list --repo ChiefGyk3D/Clouds-Against-Humanity --state merged --limit 5000 --json mergedAt
gh issue list --repo ChiefGyk3D/Clouds-Against-Humanity --state closed --limit 5000 --json closedAt
gh api --paginate -X GET repos/ChiefGyk3D/Clouds-Against-Humanity/stargazers -H 'Accept: application/vnd.github.star+json' --jq '.[].starred_at'
python3 -I scripts/gen_repo_metrics.py --refresh   # does all of the above, draws the chart and rewrites this page
python3 -I scripts/gen_repo_metrics.py --check     # offline: the same check CI runs
```

Drawing needs matplotlib, which the repository does not depend on: use the system package (`python3-matplotlib` on Debian-based systems), or make a private virtual environment with `python3 -m pip install matplotlib` and run the script with that interpreter. The check needs only Python.

The same script works for any repository you can read: pass `--repo owner/name` with its own `--snapshot`, `--out` and `--page` paths (or `--no-page`). Run `python3 -I scripts/gen_repo_metrics.py --help` for the list.

Next: [Project status](Project-Status.md), which says what the work is doing right now.
