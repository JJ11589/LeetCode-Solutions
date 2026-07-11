"""
sync.py
-------
The main entry point. Run this on a schedule (see
.github/workflows/sync.yml) and it will:

  1. Pull your recent accepted LeetCode submissions.
  2. Skip ones already synced (tracked in data/state.json).
  3. Fetch full question metadata + your accepted source code for each new one.
  4. Create Topic/NNNN_Problem_Name/{solution.ext, README.md, notes.md}.
  5. Recompute stats and regenerate the root README.
  6. Exit 0 with "changes made" signalled via a marker file the workflow
     checks, so the Action only commits when there's something new.

Run manually:
    python scripts/sync.py
    python scripts/sync.py --limit 50          # look further back in history
    python scripts/sync.py --dry-run           # fetch + print, write nothing
    python scripts/sync.py --force-resync 1234567  # re-pull one submission id
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time

from config import (
    DEFAULT_LANG,
    LANG_EXT,
    LANG_MARKDOWN_FENCE,
    REPO_ROOT,
    ROOT_README,
    STATE_FILE,
    primary_topic_folder,
)
from leetcode_client import LeetCodeAuthError, LeetCodeClient
from generate_readme import (
    notes_template,
    problem_readme,
    root_readme,
    solution_file_header,
    fmt_date,
)
from stats import compute_stats, write_stats_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("sync")

CHANGED_MARKER = os.path.join(REPO_ROOT, ".sync_changed")


# --------------------------------------------------------------------- #
# State (which submission IDs we've already materialized to disk)
# --------------------------------------------------------------------- #
def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"synced_ids": [], "problems": []}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# --------------------------------------------------------------------- #
# Folder / file creation for a single problem
# --------------------------------------------------------------------- #
def write_problem_files(question: dict, submission: dict) -> dict:
    """Creates the Topic/NNNN_Title/ folder with solution + README + notes.
    Returns a small descriptor dict used for the root README table / stats.
    """
    topics = [t["name"] for t in question["topicTags"]]
    topic_folder = primary_topic_folder(question["topicTags"])

    safe_title = (
        question["title"].replace(" ", "_").replace("/", "-").replace(":", "")
        .replace("'", "").replace(",", "")
    )
    problem_dir_name = f"{int(question['questionFrontendId']):04d}_{safe_title}"
    problem_dir = os.path.join(REPO_ROOT, topic_folder, problem_dir_name)
    os.makedirs(problem_dir, exist_ok=True)

    lang_key = submission.get("lang", DEFAULT_LANG)
    ext = LANG_EXT.get(lang_key, "txt")
    fence = LANG_MARKDOWN_FENCE.get(lang_key, "")

    # solution.<ext>
    sol_path = os.path.join(problem_dir, f"solution.{ext}")
    comment_prefix = "#" if ext == "py" else "//"
    with open(sol_path, "w", encoding="utf-8") as f:
        f.write(solution_file_header(question, submission, comment_prefix))
        f.write(submission["code"].rstrip() + "\n")

    # README.md (per-problem)
    readme_path = os.path.join(problem_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(problem_readme(question, submission, topics))

    # notes.md (only created once — don't clobber manual notes on resync)
    notes_path = os.path.join(problem_dir, "notes.md")
    if not os.path.exists(notes_path):
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write(notes_template(question))

    rel_path = os.path.relpath(readme_path, REPO_ROOT).replace(os.sep, "/")

    return {
        "frontend_id": question["questionFrontendId"],
        "title": question["title"],
        "slug": question["titleSlug"],
        "difficulty": question["difficulty"],
        "topics": topics,
        "lang": submission.get("lang_name", lang_key),
        "date": fmt_date(submission["timestamp"]),
        "timestamp": int(submission["timestamp"]),
        "path": rel_path,
    }


# --------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="How many recent accepted submissions to scan")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print, write nothing to disk")
    args = parser.parse_args()

    username = os.environ.get("LEETCODE_USERNAME")
    session_cookie = os.environ.get("LEETCODE_SESSION")
    csrf_token = os.environ.get("LEETCODE_CSRF_TOKEN")

    if not username:
        log.error("LEETCODE_USERNAME is not set. See INSTALL.md.")
        sys.exit(1)

    try:
        client = LeetCodeClient(session_cookie, csrf_token, username)
    except LeetCodeAuthError as e:
        log.error(str(e))
        sys.exit(1)

    state = load_state()
    synced_ids = set(state.get("synced_ids", []))
    known_problems = {p["slug"]: p for p in state.get("problems", [])}

    log.info("Fetching last %d accepted submissions for '%s'...", args.limit, username)
    try:
        recent = client.recent_accepted_submissions(limit=args.limit)
    except LeetCodeAuthError as e:
        log.error(str(e))
        sys.exit(1)

    new_items = [s for s in recent if s["id"] not in synced_ids]
    if not new_items:
        log.info("Nothing new to sync. %d problems already tracked.", len(known_problems))
        return

    log.info("Found %d new accepted submission(s) to sync.", len(new_items))

    any_written = False
    for item in reversed(new_items):  # oldest-first so README ordering stays sane
        slug = item["titleSlug"]
        log.info("Syncing %s (%s)...", item["title"], slug)
        try:
            question = client.question_data(slug)
            if question.get("isPaidOnly"):
                log.warning("  '%s' is a premium-only question; metadata may be incomplete.", slug)
            submission = client.submission_code(slug, target_timestamp=int(item["timestamp"]))
        except LeetCodeAuthError as e:
            log.error(str(e))
            sys.exit(1)
        except Exception as e:
            log.error("  Failed to fetch data for %s: %s. Skipping.", slug, e)
            continue

        if not submission:
            log.warning("  No accepted source code found for %s via submissions API. Skipping.", slug)
            continue

        if args.dry_run:
            log.info("  [dry-run] Would write %s (%s)", question["title"], question["difficulty"])
        else:
            descriptor = write_problem_files(question, submission)
            known_problems[slug] = descriptor
            any_written = True

        synced_ids.add(item["id"])
        time.sleep(1)  # be polite to LeetCode's servers

    if args.dry_run:
        log.info("[dry-run] Done. No files written.")
        return

    if not any_written:
        log.info("No files were written (all skipped/failed).")
        return

    # ------------------------------------------------------------------ #
    # Regenerate stats + root README
    # ------------------------------------------------------------------ #
    problems_sorted = sorted(known_problems.values(), key=lambda p: p["timestamp"], reverse=True)
    stats = compute_stats(problems_sorted)
    write_stats_json(stats)

    with open(ROOT_README, "w", encoding="utf-8") as f:
        f.write(root_readme(username, stats, problems_sorted))

    state["synced_ids"] = sorted(synced_ids)
    state["problems"] = problems_sorted
    save_state(state)

    # Tell the GitHub Action there's something to commit.
    with open(CHANGED_MARKER, "w") as f:
        f.write("1")

    log.info("Sync complete. %d total problems tracked.", len(problems_sorted))


if __name__ == "__main__":
    main()
