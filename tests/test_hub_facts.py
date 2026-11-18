"""The hub's facts: the Steps parser, commit counting, the internet check (no network needed)."""

import os
import subprocess
from datetime import date, timedelta

from lab_os.hub.commits import commits_per_day
from lab_os.hub.internet import check_once
from lab_os.hub.project import FOCUS_FILE, parse_steps, project_summary

SAMPLE = """\
# Current Focus: the sample hub

## Rules for this focus
1. **Not a step**: rules are numbered too.

## Steps (each one is a small, testable win)
0. **Settle before coding** (done 2026-11-09) (planning sessions):
   - notes
1. **Plain hub.** (done 2026-11-10) The page.
   1. **Indented**: a sub-list, not a step.
2. **Robot tools for AI.** The brain becomes an MCP server.

### Phase 2: the reveal
3. **The design.** Build to match.

### Step 2, concretely
- **Which AI:** not a step either.

## After this focus
4. **Not a step**: outside the Steps section.
"""


def test_steps_parser_reads_only_the_steps_section():
    steps = parse_steps(SAMPLE)
    assert [(s["n"], s["title"], s["done"]) for s in steps] == [
        (0, "Settle before coding", True),
        (1, "Plain hub", True),
        (2, "Robot tools for AI", False),
        (3, "The design", False),
    ]


def test_project_summary_names_the_first_step_not_done(tmp_path):
    f = tmp_path / "focus.md"
    f.write_text(SAMPLE)
    s = project_summary(f)
    assert s["available"]
    assert s["focus"] == "The sample hub"
    assert (s["step"], s["of"], s["next"]) == (2, 3, "Robot tools for AI")


def test_project_summary_when_everything_is_done(tmp_path):
    f = tmp_path / "focus.md"
    f.write_text("# Current Focus: x\n\n## Steps\n1. **One** (done 2026-01-01)\n")
    s = project_summary(f)
    assert (s["step"], s["of"], s["next"]) == (1, 1, None)


def test_project_summary_without_the_file(tmp_path):
    assert project_summary(tmp_path / "missing.md") == {"available": False}


def test_the_real_focus_file_has_steps():
    s = project_summary(FOCUS_FILE)
    assert s["available"] and s["of"] >= 1


def _git(repo, *args, when=None):
    env = os.environ | {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    if when:
        env |= {"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=env, capture_output=True)


def test_commits_are_counted_per_day(tmp_path):
    today = date(2026, 11, 9)
    _git(tmp_path, "init", "-q", "-b", "main")

    def commit_on(days_ago, hour=12):
        day = today - timedelta(days=days_ago)
        _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "c", when=f"{day}T{hour:02}:00:00")

    commit_on(20)  # outside a 14-day window
    commit_on(3)
    commit_on(1, 9)
    commit_on(1, 18)
    commit_on(0)
    _git(tmp_path, "checkout", "-q", "-b", "side")  # other branches count too
    commit_on(0, 15)

    c = commits_per_day(14, repo=tmp_path, today=today)
    assert c["available"] and c["days"] == 14
    assert len(c["per_day"]) == 14
    assert c["per_day"][0]["date"] == "2026-10-27" and c["per_day"][-1]["date"] == "2026-11-09"
    counts = {d["date"]: d["count"] for d in c["per_day"]}
    assert counts["2026-11-09"] == 2
    assert counts["2026-11-08"] == 2
    assert counts["2026-11-06"] == 1
    assert c["total"] == 5
    assert commits_per_day(30, repo=tmp_path, today=today)["total"] == 6


def test_merges_are_not_counted(tmp_path):
    today = date(2026, 11, 9)
    _git(tmp_path, "init", "-q", "-b", "main")
    when = f"{today}T12:00:00"
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "a", when=when)
    _git(tmp_path, "checkout", "-q", "-b", "side")
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "b", when=when)
    _git(tmp_path, "checkout", "-q", "main")
    _git(tmp_path, "merge", "-q", "--no-ff", "-m", "merge", "side", when=when)
    assert commits_per_day(7, repo=tmp_path, today=today)["total"] == 2


def test_commits_without_a_repo(tmp_path):
    assert commits_per_day(7, repo=tmp_path / "nothing")["available"] is False


async def test_internet_check_says_offline_when_nothing_answers():
    # port 9 on localhost: nothing listens there, so the connection is refused at once
    assert await check_once((("127.0.0.1", 9),)) is False


async def test_one_miss_while_online_is_tried_again(monkeypatch):
    # quick job 32: a single miss used to say "offline" for 30 s
    import lab_os.hub.internet as internet

    answers = [True, False, True, False, False]

    async def fake_check(targets):
        return answers.pop(0)

    monkeypatch.setattr(internet, "check_once", fake_check)
    monkeypatch.setattr(internet, "RETRY_S", 0)
    check = internet.InternetCheck()
    assert await check.step() is True
    assert await check.step() is True  # missed, then answered
    assert await check.step() is False and check.online is False  # missed twice
