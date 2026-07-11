"""
generate_readme.py
-------------------
Builds:
  1. The per-problem README.md (question metadata, approach, complexity).
  2. The root README.md (profile banner, stats, badges, progress table).

Nothing here talks to the network — it's pure string/template generation
from data that sync.py and stats.py hand it.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser

from config import DIFFICULTY_EMOJI, LANG_MARKDOWN_FENCE


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
class _HTMLToText(HTMLParser):
    """Very small HTML->plain-text converter for LeetCode's problem
    statement HTML, just enough for notes.md context (not a full
    re-publication of the statement — we keep it short)."""

    def __init__(self):
        super().__init__()
        self.chunks: list[str] = []

    def handle_data(self, data):
        self.chunks.append(data)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "".join(self.chunks)).strip()


def html_excerpt(html: str, max_chars: int = 280) -> str:
    parser = _HTMLToText()
    parser.feed(html or "")
    text = parser.text()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "…"
    return text


def fmt_date(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")


# ------------------------------------------------------------------ #
# Per-problem README
# ------------------------------------------------------------------ #
def problem_readme(question: dict, submission: dict, topics: list[str]) -> str:
    difficulty = question["difficulty"]
    emoji = DIFFICULTY_EMOJI.get(difficulty, "")
    frontend_id = question["questionFrontendId"]
    title = question["title"]
    slug = question["titleSlug"]
    lang_name = submission.get("lang_name", submission.get("lang", "cpp"))
    date_solved = fmt_date(submission["timestamp"])
    excerpt = html_excerpt(question.get("content", ""))

    topics_md = ", ".join(f"`{t}`" for t in topics) if topics else "`Uncategorized`"

    return f"""# {frontend_id}. {title}

{emoji} **Difficulty:** {difficulty}
**Topics:** {topics_md}
**Language:** {lang_name}
**Date Solved:** {date_solved}
**Status:** ✅ Accepted
**Runtime:** {submission.get('runtime', 'N/A')}
**Memory:** {submission.get('memory', 'N/A')}
**Problem Link:** https://leetcode.com/problems/{slug}/

---

## Problem Summary

> {excerpt}

*(Full statement on LeetCode — not reproduced here.)*

## Approach

<!-- Fill this in, or let your notes.md carry the detailed write-up. -->
_Describe the approach you used here._

## Complexity

- **Time Complexity:** `O(?)`
- **Space Complexity:** `O(?)`

## My Notes

See [`notes.md`](./notes.md) for revision notes, alternate approaches, and gotchas.
"""


def notes_template(question: dict) -> str:
    return f"""# Notes — {question['questionFrontendId']}. {question['title']}

## Key Insight


## Alternate Approaches


## Mistakes / Gotchas


## Revision Status
- [ ] Needs revision
- [ ] Comfortable
- [ ] Mastered
"""


def solution_file_header(question: dict, submission: dict, comment_prefix: str = "//") -> str:
    """A small header comment block prepended to the solution source file."""
    return (
        f"{comment_prefix} {question['questionFrontendId']}. {question['title']}\n"
        f"{comment_prefix} Difficulty: {question['difficulty']}\n"
        f"{comment_prefix} Link: https://leetcode.com/problems/{question['titleSlug']}/\n"
        f"{comment_prefix} Runtime: {submission.get('runtime', 'N/A')} | "
        f"Memory: {submission.get('memory', 'N/A')}\n\n"
    )


# ------------------------------------------------------------------ #
# Root README
# ------------------------------------------------------------------ #
ROOT_BANNER = """<div align="center">

# 🚀 LeetCode Solutions

### My competitive programming journey, fully automated.

</div>

"""


def badges(username: str, stats: dict) -> str:
    total = stats["total"]
    easy = stats["easy"]
    medium = stats["medium"]
    hard = stats["hard"]
    streak = stats.get("streak", 0)
    return (
        f"![Total Solved](https://img.shields.io/badge/Total_Solved-{total}-blue?style=for-the-badge)\n"
        f"![Easy](https://img.shields.io/badge/Easy-{easy}-brightgreen?style=for-the-badge)\n"
        f"![Medium](https://img.shields.io/badge/Medium-{medium}-yellow?style=for-the-badge)\n"
        f"![Hard](https://img.shields.io/badge/Hard-{hard}-red?style=for-the-badge)\n"
        f"![Streak](https://img.shields.io/badge/Current_Streak-{streak}_days-orange?style=for-the-badge)\n\n"
        f"[![LeetCode](https://img.shields.io/badge/LeetCode-{username}-FFA116?style=for-the-badge&logo=leetcode&logoColor=white)]"
        f"(https://leetcode.com/{username}/)\n"
        f"![Last Updated](https://img.shields.io/badge/Last_Updated-{datetime.now(timezone.utc).strftime('%Y--%m--%d')}-lightgrey?style=for-the-badge)\n"
    )


def topic_distribution_table(topic_counts: dict[str, int]) -> str:
    rows = sorted(topic_counts.items(), key=lambda kv: kv[1], reverse=True)
    lines = ["| Topic | Solved |", "|---|---|"]
    for topic, count in rows:
        lines.append(f"| {topic} | {count} |")
    return "\n".join(lines)


def progress_table(problems: list[dict], limit: int | None = None) -> str:
    """problems: newest-first list of dicts with keys
    {frontend_id, title, slug, difficulty, topics, lang, date, path}"""
    rows = problems[:limit] if limit else problems
    lines = ["| # | Question | Difficulty | Topic | Language | Date Solved |", "|---|---|---|---|---|---|"]
    for p in rows:
        emoji = DIFFICULTY_EMOJI.get(p["difficulty"], "")
        link = f"[{p['title']}]({p['path']})"
        topic = p["topics"][0] if p["topics"] else "Misc"
        lines.append(
            f"| {p['frontend_id']} | {link} | {emoji} {p['difficulty']} | {topic} | {p['lang']} | {p['date']} |"
        )
    return "\n".join(lines)


def root_readme(username: str, stats: dict, problems: list[dict]) -> str:
    """problems must be sorted newest-first."""
    recent = problems[:5]
    recent_lines = "\n".join(
        f"- **{p['frontend_id']}. [{p['title']}]({p['path']})** "
        f"({DIFFICULTY_EMOJI.get(p['difficulty'],'')} {p['difficulty']}) — {p['date']}"
        for p in recent
    )

    weak = stats.get("weak_topics", [])
    strong = stats.get("strong_topics", [])
    weak_md = ", ".join(weak) if weak else "_Not enough data yet_"
    strong_md = ", ".join(strong) if strong else "_Not enough data yet_"

    return f"""{ROOT_BANNER}
<div align="center">

{badges(username, stats)}

</div>

## 📊 Statistics

- **Total Problems Solved:** {stats['total']}
- **Easy:** {stats['easy']} &nbsp;|&nbsp; **Medium:** {stats['medium']} &nbsp;|&nbsp; **Hard:** {stats['hard']}
- **Primary Language:** C++ (others supported per-problem)
- **Current Streak:** {stats.get('streak', 0)} days
- **Last Updated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

### Topic Distribution

{topic_distribution_table(stats['topic_counts'])}

### 💪 Strong Topics
{strong_md}

### 🎯 Weak Topics (focus here)
{weak_md}

---

## 🕒 Recent Activity

{recent_lines if recent else '_No submissions synced yet._'}

---

## 📋 All Solved Problems

> Newest first. Auto-generated — do not edit by hand, edit `scripts/generate_readme.py` instead.

{progress_table(problems)}

---

## ⚙️ How this repo works

This repository is synced automatically by a GitHub Action
(`.github/workflows/sync.yml`) that polls my recently-accepted LeetCode
submissions, fetches the source code and problem metadata, organizes it by
topic, regenerates this README and the stats, and commits/pushes the result.
See [`scripts/`](./scripts) for the implementation and
[`INSTALL.md`](./INSTALL.md) for setup.

<div align="center">

_Generated automatically — last sync {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_

</div>
"""
