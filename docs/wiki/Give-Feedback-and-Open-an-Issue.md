# Give feedback and open an issue

> Prerequisites: none. If you can use a web browser you can do the main path. The command-line parts need a [terminal](Git-From-Zero.md#what-a-terminal-is) and are optional.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

This project is one person's open-source education effort. It will have mistakes: a claim that has gone out of date, a vendor page that changed after it was written, a command that works on my machine and not on yours. Those are exactly what I want to hear about, because you can see them and I cannot. You are not dead until you stop learning, and that includes the lessons themselves.

Reading the pages and doing the free exercises costs nothing, and so does giving feedback. Nothing here is sold and nothing is gated behind a report.

## What is welcome

- A command that failed or behaved differently on your computer.
- A claim that looks wrong or outdated, or a vendor page that has changed.
- An explanation that confused you. If you were lost, the page is at fault, not you.
- A topic you wish a lesson covered.
- A typo or a broken link.
- A question. If you are stuck, someone else probably is too.

## Never paste these

**Do not put any of these in an issue, a comment or a screenshot:**

- **Tokens, API keys, passwords and recovery codes**, even expired ones or ones you think are harmless.
- **Account, organization or tenant names**, and account IDs.
- **Real IP addresses and hostnames** of machines you own or work on. Use a placeholder such as `203.0.113.10` or `example.com`.
- **Your amateur radio callsign or grid square**, if you have one.
- **Anything from a real vendor console that identifies you**, such as an email address, a billing page or a project name.

An issue is public and stays visible even if you delete it later, because people may have copied it. If you already pasted something sensitive, treat it as exposed: revoke or rotate the token first, then edit the issue. Read your error text before posting and replace anything private with `REDACTED`.

## Open an issue in the web browser

An issue is a public note attached to this repository. This is the easiest route and needs a free GitHub account.

1. Sign in to GitHub, then open the [Issues tab of this repository](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues).
2. Click **New issue**.
3. Pick the form that fits: lesson feedback or error, a command did not work, a question, or a topic request. Click **Get started** next to it.
4. Fill in the title and the fields. The forms ask for the page name and what you expected.
5. Read it once more for anything on the never-paste list, then click **Submit new issue**.

Before step 4, glance at the search box at the top of the Issues tab. Someone may already have reported the same thing; if so, add a comment to that issue instead.

GitHub's own steps are in [Creating an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue).

## Open an issue from a terminal

The GitHub command-line tool, `gh`, can do the same thing. Install it and sign in first (`gh auth login`); its [installation page](https://cli.github.com/) has the steps. Check it with `gh --version`.

Bash (Linux, macOS, WSL, Git Bash):

```bash
gh issue create --repo ChiefGyk3D/Clouds-Against-Humanity \
  --title "[command] Git from zero, exercise 2 fails" \
  --body "Page: Git from zero, exercise 2
OS: Linux
Expected: the file is committed.
Happened: error text here (private parts replaced with REDACTED)."
```

PowerShell:

```powershell
gh issue create --repo ChiefGyk3D/Clouds-Against-Humanity `
  --title "[command] Git from zero, exercise 2 fails" `
  --body "Page: Git from zero, exercise 2`nOS: Windows (PowerShell)`nExpected: the file is committed.`nHappened: error text here (private parts replaced with REDACTED)."
```

Those commands are examples and were not run against the live repository (est.). `gh issue create` with no options asks you questions instead, which is gentler for a first time. The command-line route skips the forms, so the reminders above matter even more.

## What goes in a good report

| Include | Why |
|---|---|
| The page name | I can find the text you saw. |
| The step or exercise number | Pages change; a step number pins the spot. |
| Your operating system (and version if you know it) | Many failures are one operating system only. |
| What you expected | Shows what the page led you to believe. |
| What happened | The actual result, in your words. |
| The exact error text | Often the whole answer. Copy it, do not retype it, and remove anything private first. |

You do not need to know the fix, and you do not need to be sure you are right. "This confused me" is a complete report.

## Security problems do not go in a public issue

If you think you found a vulnerability, or you found a real secret in the repository, use GitHub's private reporting instead: the repository's **Security** tab, then **Report a vulnerability**. The repository's `SECURITY.md` says what to include. GitHub explains the feature in [Privately reporting a security vulnerability](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability).

Whether private vulnerability reporting is switched on for this repository is a repository setting that can only be seen and changed by the maintainer. This page was written without being able to confirm it. If the button is missing, `SECURITY.md` says to open a public issue that asks for a private channel and contains no details.

## What happens next

I read issues in the evenings and at weekends and I cannot promise a reply time. A report may become a fix, a question back to you, a note on the roadmap, or a polite "not for now". Anything useful becomes part of the planning described in [How this project is planned](How-This-Project-Is-Planned.md). If you would like to fix something yourself, [Git from zero](Git-From-Zero.md) and [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) show how a change is made.

## Sources

Retrieved 2026-10-22 from GitHub's documentation.

| Claim | Source |
|---|---|
| The steps to open an issue: the repository's Issues tab, then New issue | [Creating an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue) |
| Issue forms are YAML files in `.github/ISSUE_TEMPLATE`, and a `config.yml` there can turn blank issues off and add contact links | [Syntax for issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms) and [Configuring issue templates for your repository](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository) |
| Private vulnerability reporting and the Report a vulnerability button | [Privately reporting a security vulnerability](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) |
| A `SECURITY.md` file states how to report a vulnerability | [Adding a security policy to your repository](https://docs.github.com/en/code-security/getting-started/adding-a-security-policy-to-your-repository) |

The exact wording of the form buttons can change; if your screen differs, trust your screen and tell me.

Next: back to [Reading order](Reading-Order.md), or on to [Git from zero](Git-From-Zero.md) if you are new.
