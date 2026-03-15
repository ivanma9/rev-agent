# Auto-Scoring & Auto-Post Pipeline

**Goal:** Replace human draft approval with an autonomous score → edit → post loop. Every draft is scored by Claude (0-10), auto-edited up to 3 times if below threshold, then posted or discarded — no human in the loop.

**Scorecard targets:**
- Posts published: 1+/week
- Communities scanned: 4/week  
- Responses posted: 2+/week
- Auto-post success rate: tracked in weekly report
- Scheduler uptime: >95%

## Pipeline

```
generate_draft() → score (0-10) → if ≥7 post
                                → if <7 edit → re-score (max 3 retries)
                                → if still <7 discard
```

## Scoring Rubric (Claude Haiku, 0-2 each = max 10)
- Relevance: genuinely related to RevenueCat / IAP / subscription billing
- Helpfulness: actually helps the person asking
- Authenticity: sounds human, not spammy or promotional
- Platform fit: appropriate tone for HN vs SO vs Reddit
- Specificity: cites concrete details, not generic advice

## Constants
- `SCORE_THRESHOLD = 7.0`
- `MAX_RETRIES = 3`

## Tasks

### Task 1 — Store Schema + Methods
**Files:** `src/store.py`, `tests/test_store.py`
- Add columns: `score REAL`, `score_attempts INTEGER DEFAULT 0`, `post_url TEXT`
- Add `_migrate_drafts_table()` using `PRAGMA table_info` + `ALTER TABLE ADD COLUMN`
- Add methods: `update_draft_score()`, `update_draft_response()`, `record_post_url()`
- Add `get_draft_stats_this_week()` for scorecard
- Tests: column existence, round-trip updates, discarded status

### Task 2 — score_draft()
**Files:** `src/tools/draft_scorer.py` (new), `tests/test_draft_scorer.py` (new)
- Claude Haiku returns JSON with 5 keys (0-2 each), sum = score
- Returns 0.0 on any failure, never raises
- Tests: correct sum, malformed JSON fallback, clamping

### Task 3 — edit_draft()
**Files:** `src/tools/draft_scorer.py`, `tests/test_draft_scorer.py`
- Claude Haiku improves draft given feedback string
- Returns original unchanged on failure
- Tests: returns string, fallback on error

### Task 4 — score_and_post_pipeline()
**Files:** `src/tools/draft_scorer.py`, `tests/test_draft_scorer.py`
- Orchestrates: score → if pass post, if fail edit → retry up to MAX_RETRIES → discard
- Returns `{"action": "posted"|"discarded", "score": float, "attempts": int}`
- Tests: posts on high score, discards after 3 retries, posts on 2nd attempt

### Task 5 — Wire into scan_communities()
**Files:** `src/tools/community_scanner.py`, `tests/test_community_scanner.py`
- Replace save-and-stop with score_and_post_pipeline()
- Expand return dict with `posted` and `discarded` counts
- Tests: pipeline called, counts correct

### Task 6 — Post URL 3-tuple in draft_poster
**Files:** `src/tools/draft_poster.py`, `tests/test_draft_poster.py`
- Change handler returns from (bool, bool) → (bool, bool, str|None)
- Reddit success returns permalink URL
- Tests: Reddit post returns URL

### Task 7 — Weekly Report Scorecard
**Files:** `src/tools/weekly_report.py`, `src/store.py`, `tests/test_weekly_report.py`
- Add "## Auto-Post Scorecard" section to report
- Surface: posts published, success rate, avg score, discarded count, errors
- Tests: scorecard section present, zero-state

### Task 8 — Full Suite Green
- Run all tests, verify no regressions
