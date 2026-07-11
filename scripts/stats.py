"""
stats.py
--------
Pure computation over the synced-problems list (no network calls).
Produces the numbers that generate_readme.py renders, plus a raw
stats/stats.json dump for anyone who wants to build their own dashboard
or chart on top of it.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

from config import STATS_DIR


def compute_stats(problems: list[dict]) -> dict:
    """problems: list of dicts (see generate_readme.progress_table docstring),
    each also carrying a unix 'timestamp' field."""
    total = len(problems)
    easy = sum(1 for p in problems if p["difficulty"] == "Easy")
    medium = sum(1 for p in problems if p["difficulty"] == "Medium")
    hard = sum(1 for p in problems if p["difficulty"] == "Hard")

    topic_counts: Counter[str] = Counter()
    for p in problems:
        for t in p["topics"]:
            topic_counts[t] += 1

    # Strong topics = most practiced (top 5), weak = topics with only 1 solve
    # and at least 3 topics total tracked, so the signal means something.
    strong_topics = [t for t, _ in topic_counts.most_common(5)]
    weak_topics = [t for t, c in topic_counts.items() if c == 1][:5]

    streak = _current_streak([p["timestamp"] for p in problems])
    weekly = _bucket_by_period(problems, "week")
    monthly = _bucket_by_period(problems, "month")

    stats = {
        "total": total,
        "easy": easy,
        "medium": medium,
        "hard": hard,
        "topic_counts": dict(topic_counts),
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "streak": streak,
        "weekly_progress": weekly,
        "monthly_progress": monthly,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return stats


def _current_streak(timestamps: list[int]) -> int:
    """Consecutive-day streak counting back from today (UTC)."""
    if not timestamps:
        return 0
    days = sorted({datetime.fromtimestamp(ts, tz=timezone.utc).date() for ts in timestamps}, reverse=True)
    today = datetime.now(timezone.utc).date()
    streak = 0
    cursor = today
    day_set = set(days)
    # Allow the streak to "start" from today or yesterday (in case the
    # action hasn't run yet today) and then walk backwards.
    if cursor not in day_set:
        cursor = cursor.fromordinal(cursor.toordinal() - 1)
        if cursor not in day_set:
            return 0
    while cursor in day_set:
        streak += 1
        cursor = cursor.fromordinal(cursor.toordinal() - 1)
    return streak


def _bucket_by_period(problems: list[dict], period: str) -> dict:
    buckets: dict[str, int] = defaultdict(int)
    for p in problems:
        dt = datetime.fromtimestamp(p["timestamp"], tz=timezone.utc)
        if period == "week":
            key = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
        else:
            key = dt.strftime("%Y-%m")
        buckets[key] += 1
    return dict(sorted(buckets.items()))


def write_stats_json(stats: dict) -> str:
    os.makedirs(STATS_DIR, exist_ok=True)
    path = os.path.join(STATS_DIR, "stats.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    return path
