"""The scripts on the logs, SIEM and detection lesson run, and print what the page says they print.

docs/wiki/Logs-SIEM-and-Detection-Basics.md teaches with Bash scripts the learner pastes into
files and with PowerShell twins of them. A lesson whose script is broken, or whose printed
output has drifted from what the script prints, teaches the wrong thing. These tests pull each
script out of the page, run the Bash ones in a temporary folder, and compare with the page.
The PowerShell twins are not run for their output; a parity test checks that their invented
data is the same data, and a parse check runs wherever pwsh exists.

Everything is invented data on localhost. The checks collect loosely (any fenced block) and
assert strictly (exactly one block per marker), and each has a negative case.
"""

import ipaddress
import re
import shutil
import subprocess
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parent.parent / "docs" / "wiki" / "Logs-SIEM-and-Detection-Basics.md"
FENCE = re.compile(r"^```(\w*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]


def text() -> str:
    return PAGE.read_text(encoding="utf-8")


def blocks(lang: str) -> list[str]:
    return [body for tag, body in FENCE.findall(text()) if tag == lang]


def one_block(lang: str, marker: str) -> str:
    found = [b for b in blocks(lang) if marker in b]
    assert len(found) == 1, f"expected one {lang} block with {marker!r}, found {len(found)}"
    return found[0]


def sh(folder: Path, command: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", command], cwd=folder, input=stdin, capture_output=True, text=True, timeout=60, check=False
    )


@pytest.fixture()
def lab(tmp_path):
    for name, marker in (
        ("mklogs.sh", "mklogs.sh - builds"),
        ("normalize.sh", "normalize.sh [WEB_CLOCK"),
        ("detect.sh", "detect.sh THRESHOLD"),
        ("mkbaseline.sh", "mkbaseline.sh - builds"),
    ):
        (tmp_path / name).write_text(one_block("bash", marker))
    made = sh(tmp_path, "bash mklogs.sh")
    assert made.returncode == 0, made.stderr
    return tmp_path


def run(lab: Path, command: str) -> str:
    done = sh(lab, command)
    assert done.returncode == 0, done.stderr
    return done.stdout


def on_page(output: str) -> None:
    assert output.strip() in text(), f"the page does not show this output:\n{output}"


# --- the data ---------------------------------------------------------------------------


def test_the_setup_output_is_what_the_page_shows(lab):
    on_page("wrote auth.log (17 lines) and access.log (6 lines)")
    assert (lab / "auth.log").read_text().count("\n") == 17
    assert (lab / "access.log").read_text().count("\n") == 6


def test_every_address_in_the_fake_logs_is_a_documentation_address(lab):
    found = 0
    for name in ("auth.log", "access.log"):
        for addr in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", (lab / name).read_text()):
            found += 1
            assert any(ipaddress.ip_address(addr) in net for net in DOC_NETS), addr
    assert found > 20


def test_the_powershell_twin_builds_the_same_data_as_the_bash_script(lab):
    ps = one_block("powershell", "mklogs.ps1 - builds")
    here = re.findall(r"= @'\n(.*?)\n'@", ps, re.DOTALL)
    assert len(here) == 2
    assert here[0] == (lab / "auth.log").read_text().rstrip("\n")
    assert here[1] == (lab / "access.log").read_text().rstrip("\n")


def test_the_baseline_twin_uses_the_same_arithmetic():
    sh_text = one_block("bash", "mkbaseline.sh - builds")
    ps_text = one_block("powershell", "mkbaseline.ps1 - SYNTHETIC")
    assert "8 + (d * 5) % 9" in sh_text and "d * 7 % 60" in sh_text
    assert "8 + ($d * 5) % 9" in ps_text and "$d * 7 % 60" in ps_text


# --- reading and finding (exercises 1 to 4) ----------------------------------------------


def test_the_failed_login_counts_on_the_page_are_right(lab):
    loose = run(lab, "grep -cE 'Failed password for [^ ]+ from' auth.log").strip()
    wide = run(lab, "grep -cE 'Failed password for (invalid user )?[^ ]+ from [0-9.]+' auth.log").strip()
    per_source = run(
        lab, "grep -oE 'Failed password.* from [0-9.]+' auth.log | awk '{print $NF}' | sort | uniq -c | sort -rn"
    )
    assert (loose, wide) == ("8", "12")  # the first pattern misses the invalid-user lines
    on_page(f"{loose}\n{wide}\n{per_source.rstrip()}")


def test_normalized_lines_interleave_the_two_sources_and_skip_the_cron_line(lab):
    out = run(lab, "bash normalize.sh")
    assert "CRON" not in out and "cron" not in out
    mine = [ln for ln in out.splitlines() if "src=203.0.113.9 " in ln]
    assert len(mine) == 9
    assert [ln.split(" ")[2] for ln in mine[:3]] == ["source=sshd", "source=web", "source=sshd"]
    on_page("\n".join(out.splitlines()[:4]))
    on_page("\n".join(" ".join([ln.split(" ")[0], ln.split(" ")[2]]) for ln in mine))
    assert "auth.log:6\naccess.log:3" in text()


def test_a_skewed_web_clock_reorders_the_story(lab):
    out = run(lab, "bash normalize.sh 420 | head -9 | cut -d' ' -f1,3,4")
    on_page(out)
    assert out.splitlines()[6].startswith("ts=2026-10-22T03:21:10Z source=web")
    # a large negative offset must wrap inside the day instead of printing a negative time
    early = run(lab, "bash normalize.sh -4000 | grep source=web | head -1")
    assert re.search(r"ts=2026-10-22T\d\d:\d\d:\d\dZ", early) and "T-" not in early


# --- the rule (exercises 5 to 7) ---------------------------------------------------------


def test_the_rule_fires_for_the_guesser_and_for_bob(lab):
    out = run(lab, "bash normalize.sh | bash detect.sh 5 60")
    assert out.count("ALERT brute_force") == 2
    assert "src=203.0.113.9 failures=5 window=60s at=2026-10-22T03:14:33Z" in out
    assert "src=192.0.2.10 failures=5" in out
    assert "198.51.100.23" not in out  # one failure is not five
    on_page(out + "exit=0")


def test_the_threshold_table_on_the_page_is_what_the_rule_does(lab):
    out = run(
        lab,
        'for n in 3 4 5 6 7; do echo "threshold=$n alerts=$(bash normalize.sh | bash detect.sh $n 60 | wc -l)"; done',
    )
    on_page(out)


def test_the_boundary_four_stays_quiet_and_five_fires(lab):
    def alerts(count: int) -> int:
        stdin = "".join(
            f"ts=2026-10-22T10:00:{i:02d}Z src=198.51.100.1 source=sshd action=login_failed user=x\n"
            for i in range(count)
        )
        done = sh(lab, "bash detect.sh 5 60", stdin)
        assert done.returncode == 0, done.stderr
        return done.stdout.count("ALERT")

    assert alerts(4) == 0
    assert alerts(5) == 1
    assert alerts(12) == 1  # the quiet period stops a repeat inside the window


def test_failures_older_than_the_window_do_not_count(lab):
    stdin = "".join(
        f"ts=2026-10-22T10:{m:02d}:00Z src=198.51.100.1 source=sshd action=login_failed user=x\n" for m in range(5)
    )
    assert sh(lab, "bash detect.sh 5 60", stdin).stdout == ""  # one a minute: never five inside 60 s
    assert sh(lab, "bash detect.sh 5 600", stdin).stdout.count("ALERT") == 1


def test_break_evade_and_defend_do_what_the_page_says(lab):
    break_cmd = one_block("bash", "198.51.100.88")
    evade_cmd = one_block("bash", "203.0.113.77")
    out = run(lab, break_cmd)  # the page block appends the lines, then runs the rule
    assert "198.51.100.88" not in out and out.count("ALERT") == 2
    assert "198.51.100.88" in run(lab, "bash normalize.sh | bash detect.sh 4 60")
    out = run(lab, evade_cmd)
    assert "203.0.113.77" not in out and out.count("ALERT") == 2
    wide = run(lab, "bash normalize.sh | bash detect.sh 5 7200")
    assert "src=203.0.113.77 failures=5 window=7200s at=2026-10-22T03:20:00Z" in wide
    assert "198.51.100.88" not in wide  # four guesses still slip under five
    on_page(wide)


def test_the_baseline_is_learned_and_the_off_hours_rule_fires(lab):
    learned = run(lab, "bash mkbaseline.sh")
    assert (lab / "hours.txt").read_text() == "alice 8 17\n"
    out = run(lab, "bash normalize.sh | bash detect.sh 5 60 hours.txt")
    assert out.count("off_hours") == 1 and "src=203.0.113.50" in out
    assert "198.51.100.7" not in out and "user=bob" not in out
    on_page(learned.rstrip() + "\n" + out.rstrip())


# --- hostile and odd input ----------------------------------------------------------------


def test_a_hostile_username_stays_data(lab):
    evil = "$(touch_pwned)_`touch_pwned2`_;touch_pwned3"
    (lab / "auth.log").write_text(
        f"Oct 22 03:00:00 demo-host sshd[1]: Failed password for {evil} from 203.0.113.1 port 1 ssh2\n"
    )
    (lab / "access.log").write_text("")
    out = run(lab, "bash normalize.sh | bash detect.sh 1 60")
    assert "ALERT brute_force" in out
    assert not list(lab.glob("pwned*"))


def test_input_spanning_two_days_is_refused_not_miscounted(lab):
    stdin = (
        "ts=2026-10-22T23:59:00Z src=198.51.100.1 source=sshd action=login_failed user=x\n"
        "ts=2026-10-23T00:00:30Z src=198.51.100.1 source=sshd action=login_failed user=x\n"
    )
    done = sh(lab, "bash detect.sh 2 60", stdin)
    assert done.returncode == 2 and "more than one day" in done.stderr


def test_lines_the_normalizer_does_not_understand_are_dropped_not_fatal(lab):
    (lab / "auth.log").write_text("garbage\n\nOct 22 03:00:00 demo-host sshd[1]: something else\n")
    (lab / "access.log").write_text("not a web line\n")
    done = sh(lab, "bash normalize.sh")
    assert done.returncode == 0 and done.stdout == ""


# --- the page keeps its promises ----------------------------------------------------------


def test_the_banner_says_what_was_not_run():
    banner = text().split("> **Status:", 1)[1].split("\n", 1)[0]
    assert "PowerShell" in banner and "not run" in banner.lower()
    assert "Wazuh" in banner and "applied" in banner


def test_the_powershell_detector_is_an_advanced_script_that_takes_pipeline_input():
    ps = one_block("powershell", "detect.ps1 [-Threshold")
    assert re.search(r"\[CmdletBinding\(\)\]\s*param\(", ps) and "ValueFromPipeline" in ps


def test_the_lesson_has_the_loop_and_the_flip():
    page = text()
    for word in ("**Build.**", "**Break.**", "**Detect.**", "**Evade.**", "**Defend.**", "### Flip the board"):
        assert word in page, word


def test_every_exercise_has_predict_do_check_and_undo():
    sections = re.split(r"^### Exercise \d+:", text(), flags=re.MULTILINE)[1:]
    assert len(sections) == 8
    for number, body in enumerate(sections, 1):
        body = body.split("\n## ", 1)[0]
        for part in ("**Predict.**", "**Do (Bash", "**Check.**", "**Undo.**"):
            assert part in body, f"exercise {number} lacks {part}"


@pytest.mark.skipif(not shutil.which("pwsh"), reason="no PowerShell on this machine")
def test_the_powershell_scripts_parse(tmp_path):
    for marker in ("mklogs.ps1 - builds", "normalize.ps1 [-WebOffset", "detect.ps1 [-Threshold", "mkbaseline.ps1 - SYNTHETIC"):
        path = tmp_path / marker.split(" ")[0]
        path.write_text(one_block("powershell", marker))
        cmd = (
            "$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
            f"'{path}',[ref]$null,[ref]$e);if($e){{$e;exit 1}}"
        )
        done = subprocess.run(["pwsh", "-NoProfile", "-Command", cmd], capture_output=True, text=True, check=False)
        assert done.returncode == 0, done.stdout + done.stderr
