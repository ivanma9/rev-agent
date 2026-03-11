# Community Scanner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a multi-platform community scanner that monitors HN, Reddit, and Stack Overflow for RevenueCat + agentic AI discussions, generates draft responses, and provides a CLI review workflow.

**Architecture:** `src/tools/community_scanner.py` queries three platform APIs with shared search terms, filters for relevance using the existing `is_relevant_to_agents()` pattern, generates draft responses via Claude Haiku, and stores drafts in a new `drafts` table. A CLI `review` command lets the user approve/reject drafts one by one. The scheduler calls `scan_communities()` daily.

**Tech Stack:** Python 3.11+, requests (HN + SO APIs), praw (Reddit, optional), SQLite store, existing Anthropic client.

---

### Task 1: Drafts Table + Store Methods

**Files:**
- Modify: `src/store.py`
- Modify: `tests/test_store.py`

**Step 1: Write failing tests**

```python
# tests/test_store.py — add to existing file

def test_save_and_get_draft():
    from src.store import Store
    s = Store(":memory:")
    s.save_draft(
        platform="hn",
        url="https://news.ycombinator.com/item?id=123",
        title="AI agent billing with RevenueCat",
        body_snippet="How do you handle subscriptions in an AI agent?",
        draft_response="You can use RevenueCat's REST API..."
    )
    drafts = s.get_pending_drafts()
    assert len(drafts) == 1
    assert drafts[0]["platform"] == "hn"
    assert drafts[0]["status"] == "pending"
    assert "RevenueCat" in drafts[0]["draft_response"]


def test_get_pending_drafts_filters_by_platform():
    from src.store import Store
    s = Store(":memory:")
    s.save_draft("hn", "https://hn.com/1", "HN Post", "snippet", "draft")
    s.save_draft("so", "https://so.com/1", "SO Post", "snippet", "draft")
    hn_only = s.get_pending_drafts(platform="hn")
    assert len(hn_only) == 1
    assert hn_only[0]["platform"] == "hn"


def test_mark_draft_approved():
    from src.store import Store
    s = Store(":memory:")
    s.save_draft("hn", "https://hn.com/1", "Post", "snippet", "draft")
    drafts = s.get_pending_drafts()
    s.mark_draft(drafts[0]["id"], "approved")
    assert len(s.get_pending_drafts()) == 0


def test_draft_dedup_by_url():
    from src.store import Store
    s = Store(":memory:")
    s.save_draft("hn", "https://hn.com/1", "Post", "snippet", "draft")
    s.save_draft("hn", "https://hn.com/1", "Post", "snippet", "draft2")
    # Second save should be ignored (same URL)
    drafts = s.get_pending_drafts()
    assert len(drafts) == 1
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_store.py::test_save_and_get_draft -v 2>&1
```
Expected: AttributeError: 'Store' object has no attribute 'save_draft'

**Step 3: Implement store changes**

Add to `_init_tables` in `src/store.py`, inside the existing `executescript`:

```sql
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body_snippet TEXT,
    draft_response TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now'))
);
```

Add three methods to the Store class:

```python
def save_draft(self, platform: str, url: str, title: str, body_snippet: str, draft_response: str):
    """Save a draft response. Skips if URL already exists."""
    try:
        self.conn.execute(
            "INSERT OR IGNORE INTO drafts (platform, url, title, body_snippet, draft_response) VALUES (?, ?, ?, ?, ?)",
            (platform, url, title, body_snippet, draft_response)
        )
        self.conn.commit()
    except Exception:
        pass  # URL already exists

def get_pending_drafts(self, platform: str = None) -> list[dict]:
    if platform:
        rows = self.conn.execute(
            "SELECT * FROM drafts WHERE status = 'pending' AND platform = ? ORDER BY created_at DESC",
            (platform,)
        ).fetchall()
    else:
        rows = self.conn.execute(
            "SELECT * FROM drafts WHERE status = 'pending' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]

def mark_draft(self, draft_id: int, status: str):
    self.conn.execute(
        "UPDATE drafts SET status = ? WHERE id = ?",
        (status, draft_id)
    )
    self.conn.commit()
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_store.py -v 2>&1
```
Expected: ALL PASS (9 tests)

**Step 5: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add src/store.py tests/test_store.py && git commit -m "feat: drafts table and store methods for community scanner"
```

---

### Task 2: HN + SO Scanners

**Files:**
- Create: `src/tools/community_scanner.py`
- Create: `tests/test_community_scanner.py`

**Step 1: Write failing tests**

```python
# tests/test_community_scanner.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

from unittest.mock import patch, MagicMock
import json


def test_search_terms_exist():
    from src.tools.community_scanner import SEARCH_TERMS
    assert "revenuecat" in SEARCH_TERMS
    assert any("agent" in t for t in SEARCH_TERMS)


def test_scan_hn_parses_results():
    from src.tools.community_scanner import scan_hn
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "hits": [
            {
                "objectID": "123",
                "title": "Using RevenueCat with AI agents",
                "author": "dev123",
                "points": 42,
                "num_comments": 5,
                "created_at_i": 1710000000,
            }
        ]
    }
    fake_response.status_code = 200

    with patch("src.tools.community_scanner.requests.get", return_value=fake_response):
        results = scan_hn()
    assert len(results) == 1
    assert results[0]["platform"] == "hn"
    assert "revenuecat" in results[0]["title"].lower() or "RevenueCat" in results[0]["title"]
    assert "news.ycombinator.com" in results[0]["url"]


def test_scan_so_parses_results():
    from src.tools.community_scanner import scan_so
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "items": [
            {
                "question_id": 456,
                "title": "RevenueCat webhook with AI agent",
                "link": "https://stackoverflow.com/q/456",
                "score": 3,
                "answer_count": 0,
                "body": "How do I set up webhooks?",
            }
        ]
    }
    fake_response.status_code = 200

    with patch("src.tools.community_scanner.requests.get", return_value=fake_response):
        results = scan_so()
    assert len(results) == 1
    assert results[0]["platform"] == "so"
    assert "stackoverflow.com" in results[0]["url"]


def test_scan_hn_handles_api_error():
    from src.tools.community_scanner import scan_hn
    fake_response = MagicMock()
    fake_response.status_code = 500
    fake_response.raise_for_status.side_effect = Exception("Server error")

    with patch("src.tools.community_scanner.requests.get", return_value=fake_response):
        results = scan_hn()
    assert results == []
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_community_scanner.py -v 2>&1 | head -20
```
Expected: ImportError

**Step 3: Implement src/tools/community_scanner.py**

```python
# src/tools/community_scanner.py
"""Scan HN, Reddit, and Stack Overflow for RevenueCat + agentic AI discussions."""
import os
import logging
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
from src.store import Store

load_dotenv()
log = logging.getLogger(__name__)

client = Anthropic()

SEARCH_TERMS = [
    "revenuecat",
    "revenue cat",
    "in-app purchase SDK",
    "subscription billing API",
    "ai agent subscription",
    "ai agent monetization",
    "llm billing",
    "agent in-app purchase",
]

HN_API = "https://hn.algolia.com/api/v1/search_by_date"
SO_API = "https://api.stackexchange.com/2.3/search"


def scan_hn(limit: int = 10) -> list[dict]:
    """Search Hacker News via Algolia API."""
    results = []
    seen_ids = set()

    for term in SEARCH_TERMS[:4]:  # Top 4 terms to stay under rate limits
        try:
            resp = requests.get(HN_API, params={
                "query": term,
                "tags": "(story,show_hn,ask_hn)",
                "hitsPerPage": 5,
            }, timeout=10)
            resp.raise_for_status()
            hits = resp.json().get("hits", [])

            for hit in hits:
                oid = hit["objectID"]
                if oid in seen_ids:
                    continue
                seen_ids.add(oid)
                results.append({
                    "platform": "hn",
                    "url": f"https://news.ycombinator.com/item?id={oid}",
                    "title": hit.get("title", ""),
                    "body": "",
                    "score": hit.get("points", 0) or 0,
                })
        except Exception as e:
            log.warning(f"HN search failed for '{term}': {e}")

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def scan_so(limit: int = 10) -> list[dict]:
    """Search Stack Overflow API."""
    results = []
    seen_ids = set()

    so_queries = [
        {"intitle": "revenuecat"},
        {"tagged": "in-app-purchase", "intitle": "agent"},
        {"tagged": "subscriptions", "intitle": "ai"},
    ]

    for params in so_queries:
        try:
            query_params = {
                "order": "desc",
                "sort": "creation",
                "site": "stackoverflow",
                "pagesize": 5,
                "filter": "withbody",
                **params,
            }
            resp = requests.get(SO_API, params=query_params, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])

            for item in items:
                qid = item["question_id"]
                if qid in seen_ids:
                    continue
                seen_ids.add(qid)
                results.append({
                    "platform": "so",
                    "url": item["link"],
                    "title": item.get("title", ""),
                    "body": item.get("body", "")[:500],
                    "score": item.get("score", 0),
                    "answer_count": item.get("answer_count", 0),
                })
        except Exception as e:
            log.warning(f"SO search failed: {e}")

    # Prioritize unanswered questions
    results.sort(key=lambda x: (x.get("answer_count", 0), -x["score"]))
    return results[:limit]


def generate_draft(title: str, body: str, platform: str) -> str:
    """Generate a draft response using Claude Haiku."""
    platform_context = {
        "hn": "You're commenting on Hacker News. Be concise, technical, and add genuine value. No marketing speak.",
        "so": "You're answering a Stack Overflow question. Be precise, include code if relevant, cite RevenueCat docs.",
        "reddit": "You're replying on Reddit. Be casual but helpful, share practical experience.",
    }

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=f"""You are Rev, an AI developer advocate for RevenueCat.
{platform_context.get(platform, "")}
Write a helpful response (under 200 words). Reference RevenueCat docs when relevant.
Don't be sycophantic. Get to the answer quickly.
Sign off as: — Rev""",
        messages=[{"role": "user", "content": f"Post title: {title}\n\n{body[:500]}\n\nWrite a helpful response:"}]
    )
    return response.content[0].text


def scan_communities(store: Store = None, dry_run: bool = False) -> dict:
    """Scan all platforms, generate drafts, save to store."""
    if store is None:
        store = Store()

    all_results = []

    # HN
    log.info("Scanning Hacker News...")
    hn_results = scan_hn()
    all_results.extend(hn_results)
    log.info(f"  Found {len(hn_results)} HN posts")

    # SO
    log.info("Scanning Stack Overflow...")
    so_results = scan_so()
    all_results.extend(so_results)
    log.info(f"  Found {len(so_results)} SO questions")

    # Reddit (skip if no credentials)
    reddit_results = scan_reddit()
    if reddit_results:
        all_results.extend(reddit_results)
        log.info(f"  Found {len(reddit_results)} Reddit posts")

    # Deduplicate against existing drafts and interactions
    existing_urls = set()
    for d in store.get_pending_drafts():
        existing_urls.add(d["url"])
    for row in store.conn.execute("SELECT url FROM interactions").fetchall():
        existing_urls.add(row["url"])

    new_results = [r for r in all_results if r["url"] not in existing_urls]
    log.info(f"New after dedup: {len(new_results)} (filtered {len(all_results) - len(new_results)})")

    # Generate drafts
    saved = 0
    for item in new_results[:10]:  # Cap at 10 drafts per scan
        if dry_run:
            log.info(f"  [DRY RUN] Would draft for: {item['title'][:60]}")
            continue

        try:
            draft = generate_draft(item["title"], item.get("body", ""), item["platform"])
            store.save_draft(
                platform=item["platform"],
                url=item["url"],
                title=item["title"],
                body_snippet=item.get("body", "")[:200],
                draft_response=draft,
            )
            saved += 1
            log.info(f"  Drafted: [{item['platform']}] {item['title'][:50]}")
        except Exception as e:
            log.warning(f"  Failed to draft for {item['url']}: {e}")

    return {"scanned": len(all_results), "new": len(new_results), "drafted": saved}
```

NOTE: `scan_reddit()` is defined in Task 3. For now, add a stub at the top of the scan functions:

```python
def scan_reddit(limit: int = 10) -> list[dict]:
    """Search Reddit. Requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT in .env."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    if not client_id:
        log.info("Reddit credentials not configured, skipping.")
        return []
    # Full implementation in Task 3
    return []
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_community_scanner.py -v 2>&1
```
Expected: 4 PASSED

**Step 5: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add src/tools/community_scanner.py tests/test_community_scanner.py && git commit -m "feat: HN and SO community scanners with draft generation"
```

---

### Task 3: Reddit Scanner

**Files:**
- Modify: `src/tools/community_scanner.py`
- Modify: `tests/test_community_scanner.py`

**Step 1: Write failing tests**

```python
# tests/test_community_scanner.py — add to existing file

def test_scan_reddit_skips_without_credentials():
    from src.tools.community_scanner import scan_reddit
    with patch.dict(os.environ, {}, clear=True):
        results = scan_reddit()
    assert results == []


def test_scan_reddit_parses_results():
    from src.tools.community_scanner import scan_reddit
    mock_submission = MagicMock()
    mock_submission.id = "abc123"
    mock_submission.title = "Best subscription SDK for AI agents?"
    mock_submission.selftext = "Looking for something to handle billing..."
    mock_submission.score = 15
    mock_submission.url = "https://reddit.com/r/SaaS/comments/abc123"
    mock_submission.permalink = "/r/SaaS/comments/abc123/best_subscription_sdk"
    mock_submission.num_comments = 3

    mock_subreddit = MagicMock()
    mock_subreddit.search.return_value = [mock_submission]

    mock_reddit = MagicMock()
    mock_reddit.subreddit.return_value = mock_subreddit

    with patch.dict(os.environ, {"REDDIT_CLIENT_ID": "fake", "REDDIT_CLIENT_SECRET": "fake", "REDDIT_USER_AGENT": "fake"}):
        with patch("src.tools.community_scanner.praw.Reddit", return_value=mock_reddit):
            results = scan_reddit()

    assert len(results) >= 1
    assert results[0]["platform"] == "reddit"
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_community_scanner.py::test_scan_reddit_parses_results -v 2>&1
```
Expected: FAIL

**Step 3: Implement full scan_reddit**

Replace the stub `scan_reddit` in `src/tools/community_scanner.py`:

```python
def scan_reddit(limit: int = 10) -> list[dict]:
    """Search Reddit. Requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT in .env."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    if not client_id:
        log.info("Reddit credentials not configured, skipping.")
        return []

    try:
        import praw
    except ImportError:
        log.warning("praw not installed, skipping Reddit. Install with: pip install praw")
        return []

    results = []
    seen_ids = set()

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

        subreddits = ["SaaS", "indiegaming", "openai", "iOSProgramming", "RevenueCat"]
        search_terms = ["revenuecat", "in-app purchase agent", "subscription billing AI"]

        for sub_name in subreddits:
            try:
                subreddit = reddit.subreddit(sub_name)
                for term in search_terms[:2]:  # Limit queries per sub
                    for submission in subreddit.search(term, sort="new", time_filter="week", limit=5):
                        if submission.id in seen_ids:
                            continue
                        seen_ids.add(submission.id)
                        results.append({
                            "platform": "reddit",
                            "url": f"https://reddit.com{submission.permalink}",
                            "title": submission.title,
                            "body": (submission.selftext or "")[:500],
                            "score": submission.score,
                        })
            except Exception as e:
                log.warning(f"Reddit search failed for r/{sub_name}: {e}")

    except Exception as e:
        log.warning(f"Reddit connection failed: {e}")

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
```

Also add `import praw` handling — since praw is optional, the import is inside the function.

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_community_scanner.py -v 2>&1
```
Expected: 6 PASSED

**Step 5: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add src/tools/community_scanner.py tests/test_community_scanner.py && git commit -m "feat: reddit scanner with optional praw dependency"
```

---

### Task 4: CLI Review Command

**Files:**
- Modify: `src/tools/community_scanner.py`
- Modify: `tests/test_community_scanner.py`

**Step 1: Write failing tests**

```python
# tests/test_community_scanner.py — add to existing file

def test_review_drafts_approve(monkeypatch):
    from src.tools.community_scanner import review_drafts
    from src.store import Store

    store = Store(":memory:")
    store.save_draft("hn", "https://hn.com/1", "Test Post", "snippet", "My draft response")

    # Simulate user typing "y"
    inputs = iter(["y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    reviewed = review_drafts(store=store)
    assert reviewed == 1
    assert len(store.get_pending_drafts()) == 0


def test_review_drafts_reject(monkeypatch):
    from src.tools.community_scanner import review_drafts
    from src.store import Store

    store = Store(":memory:")
    store.save_draft("hn", "https://hn.com/1", "Test Post", "snippet", "My draft response")

    inputs = iter(["n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    reviewed = review_drafts(store=store)
    assert reviewed == 1
    # Draft should be rejected, not pending
    assert len(store.get_pending_drafts()) == 0


def test_review_drafts_skip(monkeypatch):
    from src.tools.community_scanner import review_drafts
    from src.store import Store

    store = Store(":memory:")
    store.save_draft("hn", "https://hn.com/1", "Test Post", "snippet", "My draft response")

    inputs = iter(["s"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    reviewed = review_drafts(store=store)
    assert reviewed == 0
    # Draft should still be pending
    assert len(store.get_pending_drafts()) == 1
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_community_scanner.py::test_review_drafts_approve -v 2>&1
```
Expected: FAIL

**Step 3: Add review_drafts to community_scanner.py**

```python
def review_drafts(store: Store = None) -> int:
    """Interactive CLI review of pending drafts. Returns count of reviewed drafts."""
    if store is None:
        store = Store()

    drafts = store.get_pending_drafts()
    if not drafts:
        print("No pending drafts to review.")
        return 0

    reviewed = 0
    for i, draft in enumerate(drafts):
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(drafts)}] {draft['platform'].upper()} — {draft['title']}")
        print(f"URL: {draft['url']}")
        if draft.get("body_snippet"):
            print(f"\nContext: {draft['body_snippet'][:200]}")
        print(f"\n--- Draft Response ---")
        print(draft["draft_response"])
        print(f"--- End Draft ---\n")

        action = input("[y]approve  [n]reject  [s]skip  > ").strip().lower()

        if action == "y":
            store.mark_draft(draft["id"], "approved")
            print("✓ Approved")
            reviewed += 1
        elif action == "n":
            store.mark_draft(draft["id"], "rejected")
            print("✗ Rejected")
            reviewed += 1
        else:
            print("→ Skipped")

    return reviewed
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_community_scanner.py -v 2>&1
```
Expected: 9 PASSED

**Step 5: Add `__main__` block**

```python
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    store = Store()

    if len(sys.argv) > 1 and sys.argv[1] == "review":
        count = review_drafts(store)
        print(f"\nReviewed {count} drafts.")
    elif len(sys.argv) > 1 and sys.argv[1] == "drafts":
        drafts = store.get_pending_drafts()
        print(f"Pending drafts: {len(drafts)}")
        for d in drafts:
            print(f"  [{d['platform']}] {d['title'][:60]} — {d['url']}")
    else:
        result = scan_communities(store)
        print(f"\nScan complete: {result}")
```

**Step 6: Run full suite**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/ -m "not integration" -v 2>&1 | tail -15
```
Expected: ALL PASS

**Step 7: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add src/tools/community_scanner.py tests/test_community_scanner.py && git commit -m "feat: CLI review command for community drafts"
```

---

### Task 5: Scheduler Wiring + Weekly Report Update

**Files:**
- Modify: `src/scheduler.py`
- Modify: `src/tools/weekly_report.py`
- Modify: `tests/test_scheduler.py`

**Step 1: Write failing test**

```python
# tests/test_scheduler.py — add to existing test
def test_scheduler_has_community_scan_task():
    from src.scheduler import TASK_KEYS
    assert "scan_communities" in TASK_KEYS
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_scheduler.py::test_scheduler_has_community_scan_task -v 2>&1
```
Expected: FAIL

**Step 3: Update scheduler**

In `src/scheduler.py`, add to `_build_tasks()`:

```python
"scan_communities": lambda: __import__("src.tools.community_scanner", fromlist=["scan_communities"]).scan_communities(store),
```

In `_run_community_scan()`, after the existing `scan_github_issues` call, add:

```python
from src.tools.community_scanner import scan_communities
scan_communities(self.store)
```

**Step 4: Update weekly report**

In `src/tools/weekly_report.py`, in `generate_weekly_report()`, after the "Community Engagement" section, add:

```python
# Pending drafts
drafts = store.get_pending_drafts()
if drafts:
    lines.append(f"- Pending draft responses: {len(drafts)}")
    for d in drafts[:3]:
        lines.append(f"  - [{d['platform']}] {d['title'][:50]}")
```

This requires importing `get_pending_drafts` — but it's already on the store object.

**Step 5: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/ -m "not integration" -v 2>&1 | tail -15
```
Expected: ALL PASS

**Step 6: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add src/scheduler.py src/tools/weekly_report.py tests/test_scheduler.py && git commit -m "feat: wire community scanner into scheduler and weekly report"
```

---

## Summary

| Task | Output |
|------|--------|
| 1 | Drafts table + store methods (save, get, mark) |
| 2 | HN + SO scanners with draft generation |
| 3 | Reddit scanner (optional praw) |
| 4 | CLI review command (approve/reject/skip) |
| 5 | Scheduler wiring + weekly report update |

**CLI usage:**
```bash
python -m src.tools.community_scanner              # scan all platforms
python -m src.tools.community_scanner drafts        # list pending drafts
python -m src.tools.community_scanner review        # interactive review
python -m src.scheduler scan_communities            # via scheduler run_now
```
