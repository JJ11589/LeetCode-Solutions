# INSTALL.md — Setup, Execution, Testing, Troubleshooting

## 1. How this actually works (read this first)

LeetCode does **not** offer a public, official API for "notify me when a
submission is accepted" or "give me my source code." There is no webhook.
So "fully automated, zero manual effort" in practice means:

- A **GitHub Action runs on a schedule** (every 30 minutes by default) and
  **polls** your recent accepted submissions using the same unofficial
  endpoints leetcode.com's own front-end uses.
- It needs your **logged-in session cookie** to read your submission source
  code (this is exactly what browser extensions like LeetHub do — there's no
  way around it, since your code is private to your account).
- Session cookies eventually expire (weeks, not forever) — when that
  happens the sync will fail with an auth error and you refresh one secret.
  This is the one piece of "manual work" left, and it's unavoidable without
  an official LeetCode API.

If you solve a problem and don't touch GitHub at all, within 30 minutes (or
on the next scheduled run) it will appear in your repo automatically.

---

## 2. Software required

- A GitHub account + a new (or existing) repository, e.g. `LeetCode-Solutions`
- Python 3.10+ (only needed for local testing — the Action installs its own)
- Git
- A browser, to extract your LeetCode session cookie once

---

## 3. Repository setup

```bash
# 1. Create a new repo on GitHub named LeetCode-Solutions (or anything you like)
# 2. Clone it locally
git clone https://github.com/<your-username>/LeetCode-Solutions.git
cd LeetCode-Solutions

# 3. Copy in everything from this project (scripts/, .github/, README.md, etc.)

# 4. Commit and push the skeleton
git add -A
git commit -m "chore: initial automation skeleton"
git push
```

---

## 4. Get your LeetCode session cookie + CSRF token

These are what let the script read *your* submissions — same as logging in
through a browser.

1. Open https://leetcode.com and log in normally.
2. Open DevTools (`F12` or `Cmd+Opt+I`) → **Application** tab (Chrome) or
   **Storage** tab (Firefox) → **Cookies** → `https://leetcode.com`.
3. Find and copy the **value** of:
   - `LEETCODE_SESSION`
   - `csrftoken`
4. Keep these secret — they're equivalent to your login session.

> These cookies typically last several weeks. When the workflow starts
> failing with an auth error (see Troubleshooting), repeat this step and
> update the GitHub secret.

---

## 5. Add GitHub repository secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name            | Value                                |
|-------------------------|---------------------------------------|
| `LEETCODE_USERNAME`     | Your LeetCode username (the one in `leetcode.com/<username>/`) |
| `LEETCODE_SESSION`      | The `LEETCODE_SESSION` cookie value  |
| `LEETCODE_CSRF_TOKEN`   | The `csrftoken` cookie value         |

`GITHUB_TOKEN` is provided automatically by Actions — you don't need to add it.

---

## 6. Execution

### Automatic (the whole point)
Once secrets are set, the workflow in `.github/workflows/sync.yml` runs
every 30 minutes on its own. Nothing else to do.

### Manual trigger (to test without waiting)
Repo → **Actions** tab → **Sync LeetCode Solutions** → **Run workflow**.

### Run locally (for development/debugging)
```bash
pip install -r requirements.txt
export LEETCODE_USERNAME=your_username
export LEETCODE_SESSION=...
export LEETCODE_CSRF_TOKEN=...

python scripts/sync.py --dry-run        # see what it WOULD do, writes nothing
python scripts/sync.py                  # actually write files
python scripts/sync.py --limit 50       # look further back than the default 20
```

---

## 7. Testing steps

1. Solve (or re-open and resubmit) any easy problem on LeetCode to generate
   a fresh accepted submission.
2. Run `python scripts/sync.py --dry-run` locally and confirm it logs the
   problem as "would write."
3. Run `python scripts/sync.py` for real and confirm:
   - A new folder appears under the right topic, e.g. `Arrays/0001_Two_Sum/`
   - It contains `solution.cpp` (or your language), `README.md`, `notes.md`
   - `stats/stats.json` updated
   - Root `README.md` table now lists it at the top
4. Push and confirm the GitHub Action's manual trigger reproduces the same
   result on GitHub's infrastructure (catches local-only env issues).
5. Let one scheduled run pass naturally and check the **Actions** tab log.

---

## 8. Folder/file structure produced

```
LeetCode-Solutions/
├── README.md                  # auto-generated, don't hand-edit
├── INSTALL.md
├── requirements.txt
├── .env.example
├── data/
│   └── state.json             # tracks which submission IDs are already synced
├── stats/
│   └── stats.json             # raw numbers behind the README's stats section
├── scripts/
│   ├── config.py
│   ├── leetcode_client.py
│   ├── generate_readme.py
│   ├── stats.py
│   └── sync.py
├── .github/workflows/sync.yml
├── Arrays/
│   └── 0001_Two_Sum/
│       ├── solution.cpp
│       ├── README.md
│       └── notes.md
├── Dynamic_Programming/
│   └── ...
└── ...
```

---

## 9. Customization

- **Change polling frequency:** edit the `cron` line in `sync.yml`. GitHub
  Actions free tier has limits on how often scheduled workflows realistically
  fire (don't expect second-level precision); every 15–30 min is reasonable.
- **Change default language / folder names:** edit `scripts/config.py`.
- **Change README layout:** edit `scripts/generate_readme.py` — it's plain
  Python string templates, nothing magic.
- **Add charts/heatmaps:** `stats/stats.json` has weekly/monthly buckets
  ready to feed into `matplotlib` or a GitHub-native contribution-graph
  action if you want a generated PNG in `assets/`.

---

## 10. Troubleshooting

**"Auth failed (403). Your LEETCODE_SESSION cookie has likely expired"**
→ Cookie expired. Repeat step 4 and update the `LEETCODE_SESSION` (and
  `csrftoken`) repository secrets.

**Workflow runs but "Nothing new to sync" every time, even after solving**
→ Confirm `LEETCODE_USERNAME` matches exactly the username in your profile
  URL. Also confirm the submission really shows "Accepted" — non-accepted
  runs are intentionally ignored.

**A problem synced but `solution.cpp` looks empty/truncated**
→ The submissions REST endpoint occasionally lags right after a submit.
  Re-run the workflow manually a minute later; it's safe to re-run (already
  synced IDs are skipped, but a failed fetch isn't marked synced so it'll
  retry automatically next run too).

**Premium-only problems**
→ `question_data()` will still return a difficulty/title/tags for most
  premium questions, but full statement content may be restricted. The repo
  will still generate folders/README, just with a shorter excerpt.

**Action runs but never commits**
→ Check the job log for "Nothing new to sync" — that's expected behavior,
  not a bug, if you haven't solved anything since the last run. The marker
  file `.sync_changed` only appears (and triggers a commit) when something
  was actually written.

**Rate limiting / "GraphQL HTTP 429"**
→ The client already retries with backoff. If it's persistent, raise the
  delay in `sync.py`'s `time.sleep(1)` between problems, or lower the
  schedule frequency.

**I want multiple languages per problem (e.g. both C++ and Python solutions)**
→ Currently one accepted solution per problem is synced (whichever LeetCode
  returns as most recent/matching). Re-running with `--force-resync` on a
  different submission, or extending `write_problem_files` to suffix
  `solution_<lang>.ext`, are the two ways to extend this — left as a
  straightforward enhancement in `scripts/sync.py`.
