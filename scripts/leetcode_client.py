"""
leetcode_client.py
-------------------
Thin client around LeetCode's (unofficial) GraphQL endpoint and the
session-authenticated submissions REST endpoint.

LeetCode does not publish an official public API for retrieving your own
accepted source code, so this client uses the same endpoints LeetCode's own
website calls in your browser. It needs your logged-in session cookie
(LEETCODE_SESSION) and CSRF token (csrftoken) to read your submissions.

These endpoints are not officially documented or guaranteed stable. If
LeetCode changes its site internals, this file is the only place you should
need to patch.
"""

from __future__ import annotations

import time
import logging
from typing import Any, Optional

import requests

log = logging.getLogger("leetcode_client")

GRAPHQL_URL = "https://leetcode.com/graphql"
BASE_URL = "https://leetcode.com"


class LeetCodeAuthError(RuntimeError):
    pass


class LeetCodeClient:
    def __init__(self, session_cookie: str, csrf_token: str, username: str, timeout: int = 15):
        if not session_cookie or not csrf_token:
            raise LeetCodeAuthError(
                "LEETCODE_SESSION and LEETCODE_CSRF_TOKEN are required. "
                "See INSTALL.md for how to extract them from your browser."
            )
        self.username = username
        self.timeout = timeout
        self.session = requests.Session()
        self.session.cookies.set("LEETCODE_SESSION", session_cookie, domain="leetcode.com")
        self.session.cookies.set("csrftoken", csrf_token, domain="leetcode.com")
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "x-csrftoken": csrf_token,
                "Referer": "https://leetcode.com",
                "User-Agent": "Mozilla/5.0 (compatible; LeetCodeSyncBot/1.0)",
            }
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _graphql(self, query: str, variables: dict, retries: int = 3) -> dict:
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                resp = self.session.post(
                    GRAPHQL_URL,
                    json={"query": query, "variables": variables},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    payload = resp.json()
                    if "errors" in payload:
                        raise RuntimeError(payload["errors"])
                    return payload["data"]
                if resp.status_code in (403, 401):
                    raise LeetCodeAuthError(
                        f"Auth failed ({resp.status_code}). Your LEETCODE_SESSION "
                        "cookie has likely expired — refresh it in the repo secrets."
                    )
                last_err = RuntimeError(f"GraphQL HTTP {resp.status_code}: {resp.text[:200]}")
            except requests.RequestException as e:
                last_err = e
            log.warning("GraphQL attempt %d/%d failed: %s", attempt, retries, last_err)
            time.sleep(2 * attempt)
        raise last_err  # type: ignore[misc]

    # ------------------------------------------------------------------ #
    # Public submission feed (last accepted submissions for a user)
    # ------------------------------------------------------------------ #
    def recent_accepted_submissions(self, limit: int = 20) -> list[dict]:
        """
        Public feed of the user's most recent ACCEPTED submissions.
        Does NOT include source code (LeetCode strips that from this query).
        Returns: [{id, title, titleSlug, timestamp}, ...] newest first.
        """
        query = """
        query recentAcSubmissions($username: String!, $limit: Int!) {
          recentAcSubmissionList(username: $username, limit: $limit) {
            id
            title
            titleSlug
            timestamp
          }
        }
        """
        data = self._graphql(query, {"username": self.username, "limit": limit})
        return data.get("recentAcSubmissionList") or []

    # ------------------------------------------------------------------ #
    # Question metadata
    # ------------------------------------------------------------------ #
    def question_data(self, title_slug: str) -> dict:
        """
        Fetch metadata for a problem: id, title, difficulty, topic tags, etc.
        """
        query = """
        query questionData($titleSlug: String!) {
          question(titleSlug: $titleSlug) {
            questionId
            questionFrontendId
            title
            titleSlug
            difficulty
            topicTags { name slug }
            content
            isPaidOnly
          }
        }
        """
        data = self._graphql(query, {"titleSlug": title_slug})
        q = data.get("question")
        if not q:
            raise RuntimeError(f"Could not fetch question data for slug '{title_slug}'")
        return q

    # ------------------------------------------------------------------ #
    # Source code of your own accepted submission
    # ------------------------------------------------------------------ #
    def submission_code(self, title_slug: str, target_timestamp: Optional[int] = None) -> Optional[dict]:
        """
        Hits the authenticated REST endpoint that backs the "Submissions" tab
        on a problem page. Returns the accepted submission closest to
        target_timestamp (or the most recent accepted one if not given).

        Returns dict with: code, lang, lang_name, runtime, memory, timestamp
        or None if nothing accepted was found.
        """
        url = f"{BASE_URL}/api/submissions/{title_slug}/"
        resp = self.session.get(url, timeout=self.timeout)
        if resp.status_code in (403, 401):
            raise LeetCodeAuthError(
                "Auth failed fetching submission code. Refresh LEETCODE_SESSION / "
                "LEETCODE_CSRF_TOKEN secrets."
            )
        resp.raise_for_status()
        payload = resp.json()
        submissions = payload.get("submissions_dump", [])

        accepted = [s for s in submissions if s.get("status_display") == "Accepted"]
        if not accepted:
            return None

        if target_timestamp is not None:
            accepted.sort(key=lambda s: abs(int(s["timestamp"]) - int(target_timestamp)))
        else:
            accepted.sort(key=lambda s: int(s["timestamp"]), reverse=True)

        best = accepted[0]
        return {
            "code": best.get("code", ""),
            "lang": best.get("lang", "cpp"),
            "lang_name": best.get("lang_name", best.get("lang", "cpp")),
            "runtime": best.get("runtime", "N/A"),
            "memory": best.get("memory", "N/A"),
            "timestamp": int(best.get("timestamp", target_timestamp or time.time())),
        }
