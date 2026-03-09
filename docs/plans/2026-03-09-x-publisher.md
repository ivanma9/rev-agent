# X/Twitter Publisher Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an X publisher that posts generated content as tweets/threads and cross-posts when GitHub content is published.

**Architecture:** `src/tools/x_publisher.py` wraps Tweepy v2 client. Content >280 chars is split into numbered threads. The GitHub publisher calls `x_publisher.cross_post()` after a successful publish. Scheduler gains an `x_post` run_now task. All posts are logged to the SQLite interactions table.

**Tech Stack:** Python 3.11+, tweepy 4.16, SQLite store, existing content_generator + publisher pipeline.

---

### Task 1: X Publisher Core

**Files:**
- Create: `src/tools/x_publisher.py`
- Create: `tests/test_x_publisher.py`

**Step 1: Write failing tests**

```python
# tests/test_x_publisher.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

from unittest.mock import MagicMock, patch


def test_split_into_thread_short():
    from src.tools.x_publisher import split_into_thread
    tweets = split_into_thread("Short tweet under 280 chars.")
    assert len(tweets) == 1
    assert tweets[0] == "Short tweet under 280 chars."


def test_split_into_thread_long():
    from src.tools.x_publisher import split_into_thread
    long_text = "A" * 300
    tweets = split_into_thread(long_text)
    assert len(tweets) > 1
    for t in tweets:
        assert len(t) <= 280


def test_split_into_thread_numbered():
    from src.tools.x_publisher import split_into_thread
    long_text = ("Word " * 60).strip()  # ~300 chars
    tweets = split_into_thread(long_text)
    if len(tweets) > 1:
        assert tweets[0].endswith("(1/2)") or "1/" in tweets[0]


def test_post_tweet_dry_run():
    from src.tools.x_publisher import post_tweet
    result = post_tweet("Hello from Rev!", dry_run=True)
    assert result["posted"] is True
    assert result["dry_run"] is True
    assert result["tweet_count"] == 1


def test_post_thread_dry_run():
    from src.tools.x_publisher import post_tweet
    long_text = ("Word " * 60).strip()
    result = post_tweet(long_text, dry_run=True)
    assert result["posted"] is True
    assert result["tweet_count"] >= 1


def test_post_tweet_logs_interaction():
    from src.tools.x_publisher import post_tweet
    from src.store import Store
    store = Store(":memory:")
    post_tweet("Test tweet", dry_run=True, store=store)
    assert store.interaction_count_this_week() == 1


def test_format_content_tweet():
    from src.tools.x_publisher import format_content_tweet
    text = format_content_tweet(
        title="How to use RevenueCat webhooks",
        url="https://github.com/ivanma9/rev-agent/blob/main/content/post.md",
        content_type="blog"
    )
    assert "RevenueCat" in text or "rev" in text.lower()
    assert "https://" in text
    assert len(text) <= 280
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_x_publisher.py -v 2>&1 | head -20
```
Expected: ImportError

**Step 3: Implement src/tools/x_publisher.py**

```python
# src/tools/x_publisher.py
"""Post content to X (Twitter) via API v2."""
import os
import logging
import textwrap
from dotenv import load_dotenv
import tweepy
from src.store import Store

load_dotenv()
log = logging.getLogger(__name__)

MAX_TWEET_LEN = 280
# Reserve space for thread numbering " (N/M)" — max 8 chars
THREAD_BODY_LEN = MAX_TWEET_LEN - 8


def _get_client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    )


def split_into_thread(text: str) -> list[str]:
    """Split text into tweet-sized chunks. Adds (N/M) numbering if >1 tweet."""
    if len(text) <= MAX_TWEET_LEN:
        return [text]

    # Split on word boundaries
    words = text.split()
    chunks = []
    current = []
    current_len = 0

    for word in words:
        # +1 for space
        if current_len + len(word) + 1 > THREAD_BODY_LEN:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += len(word) + 1

    if current:
        chunks.append(" ".join(current))

    total = len(chunks)
    if total == 1:
        return chunks

    return [f"{chunk} ({i+1}/{total})" for i, chunk in enumerate(chunks)]


def format_content_tweet(title: str, url: str, content_type: str) -> str:
    """Format a cross-post tweet for published content."""
    type_emoji = {
        "blog": "📝",
        "tutorial": "🧵",
        "code_sample": "💻",
        "case_study": "📊",
        "growth_experiment": "🧪",
        "report": "📋",
    }.get(content_type, "📄")

    text = f"{type_emoji} New from Rev:\n\n{title}\n\n{url}\n\n#RevenueCat #AgentDev"
    # Truncate title if needed to fit 280
    if len(text) > MAX_TWEET_LEN:
        max_title = MAX_TWEET_LEN - len(f"{type_emoji} New from Rev:\n\n\n\n{url}\n\n#RevenueCat #AgentDev") - 3
        text = f"{type_emoji} New from Rev:\n\n{title[:max_title]}...\n\n{url}\n\n#RevenueCat #AgentDev"
    return text


def post_tweet(
    text: str,
    dry_run: bool = False,
    store: Store = None,
) -> dict:
    """Post a tweet or thread. Returns result dict."""
    tweets = split_into_thread(text)
    total = len(tweets)

    if dry_run:
        log.info(f"[DRY RUN] Would post {total} tweet(s):")
        for i, t in enumerate(tweets):
            log.info(f"  [{i+1}/{total}] {t[:80]}...")
        if store:
            store.log_interaction(
                platform="x",
                url="https://x.com/cat_rev85934",
                summary=f"[DRY RUN] Posted thread ({total} tweets): {text[:60]}"
            )
        return {"posted": True, "dry_run": True, "tweet_count": total, "text": text}

    client = _get_client()
    tweet_ids = []
    reply_to = None

    try:
        for i, tweet_text in enumerate(tweets):
            if reply_to:
                response = client.create_tweet(
                    text=tweet_text,
                    in_reply_to_tweet_id=reply_to
                )
            else:
                response = client.create_tweet(text=tweet_text)

            tweet_id = response.data["id"]
            tweet_ids.append(tweet_id)
            reply_to = tweet_id
            log.info(f"Posted tweet {i+1}/{total}: {tweet_id}")

        url = f"https://x.com/cat_rev85934/status/{tweet_ids[0]}"
        if store:
            store.log_interaction(
                platform="x",
                url=url,
                summary=f"Posted thread ({total} tweets): {text[:60]}"
            )
        return {"posted": True, "dry_run": False, "tweet_count": total, "url": url, "ids": tweet_ids}

    except Exception as e:
        log.error(f"Failed to post tweet: {e}")
        return {"posted": False, "error": str(e)}


if __name__ == "__main__":
    result = post_tweet(
        "Rev here. Building autonomous developer advocacy for @RevenueCat. "
        "I write technical content, monitor community questions, and run growth experiments — all autonomously. "
        "Follow for weekly content on subscription APIs + agentic AI. 🤖\n\n"
        "github.com/ivanma9/rev-agent",
        dry_run=True
    )
    print(result)
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_x_publisher.py -v 2>&1
```
Expected: 7 PASSED

**Step 5: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add src/tools/x_publisher.py tests/test_x_publisher.py && git commit -m "feat: x publisher with thread splitting and dry_run support"
```

---

### Task 2: Cross-Post After GitHub Publish

**Files:**
- Modify: `src/tools/publisher.py`
- Modify: `tests/test_publisher.py`

**Step 1: Write failing test**

```python
# tests/test_publisher.py — add to existing file
def test_publish_pending_cross_posts_to_x():
    from unittest.mock import patch, MagicMock
    from src.store import Store
    from src.tools.publisher import publish_pending

    store = Store(":memory:")
    store.queue_content("How to use webhooks", "blog", "# Body\n\nContent here.")

    mock_repo = MagicMock()
    mock_repo.get_contents.side_effect = Exception("not found")
    mock_repo.create_file.return_value = {}

    with patch("src.tools.publisher.Github") as mock_github, \
         patch("src.tools.publisher.post_tweet") as mock_post:
        mock_github.return_value.get_repo.return_value = mock_repo
        mock_post.return_value = {"posted": True, "dry_run": True, "tweet_count": 1}

        results = publish_pending(store=store, limit=1, x_dry_run=True)

        assert len(results) == 1
        mock_post.assert_called_once()
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_publisher.py::test_publish_pending_cross_posts_to_x -v 2>&1
```
Expected: FAIL

**Step 3: Update src/tools/publisher.py**

Read the file first, then:

1. Add import at top: `from src.tools.x_publisher import post_tweet, format_content_tweet`
2. Add `x_dry_run: bool = False` parameter to `publish_pending()`
3. After `store.mark_published(item["id"], url=url)`, add cross-post call:

```python
# Cross-post to X
tweet_text = format_content_tweet(item["title"], url, item["content_type"])
x_result = post_tweet(tweet_text, dry_run=x_dry_run, store=store)
if x_result.get("posted"):
    log.info(f"Cross-posted to X: {x_result.get('url', '[dry run]')}")
```

Also add `import logging` and `log = logging.getLogger(__name__)` if not present.

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_publisher.py -v 2>&1
```
Expected: ALL PASS (3 tests)

**Step 5: Run full suite**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/ -m "not integration" -v 2>&1 | tail -10
```
Expected: ALL PASS

**Step 6: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add src/tools/publisher.py tests/test_publisher.py && git commit -m "feat: cross-post to x after github publish"
```

---

### Task 3: Wire X Publisher into Scheduler

**Files:**
- Modify: `src/scheduler.py`
- Modify: `tests/test_scheduler.py`

**Step 1: Write failing test**

```python
# tests/test_scheduler.py — add to existing tests
def test_scheduler_run_now_has_x_post():
    from src.scheduler import TASKS
    assert "x_post" in TASKS
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_scheduler.py::test_scheduler_run_now_has_x_post -v 2>&1
```
Expected: FAIL

**Step 3: Update src/scheduler.py**

Read the file first, then:

1. Add `x_post` to the `run_now` tasks dict:
```python
"x_post": lambda: __import__("src.tools.x_publisher", fromlist=["post_tweet"]).post_tweet(
    "Rev weekly update: content published, community monitored. "
    "github.com/ivanma9/rev-agent #RevenueCat #AgentDev",
    dry_run=False,
    store=store
),
```

2. Extract the tasks dict as a module-level `TASKS` variable so it's testable. Change `run_now` to:

```python
def _build_tasks(store: Store) -> dict:
    return {
        "sync": lambda: __import__("src.tools.knowledge_sync", fromlist=["sync_knowledge"]).sync_knowledge(store),
        "content": lambda: __import__("src.tools.content_generator", fromlist=["generate_weekly_content"]).generate_weekly_content(store),
        "publish": lambda: __import__("src.tools.publisher", fromlist=["publish_pending"]).publish_pending(store),
        "community": lambda: __import__("src.tools.community_monitor", fromlist=["scan_github_issues"]).scan_github_issues(store, post_comments=False),
        "report": lambda: __import__("src.tools.weekly_report", fromlist=["save_and_publish_report"]).save_and_publish_report(store),
        "feedback": lambda: __import__("src.tools.product_feedback", fromlist=["generate_weekly_feedback"]).generate_weekly_feedback(store),
        "feedback_submit": lambda: __import__("src.tools.feedback_submitter", fromlist=["submit_feedback_by_email"]).submit_feedback_by_email(store, dry_run=False),
        "x_post": lambda: __import__("src.tools.x_publisher", fromlist=["post_tweet"]).post_tweet(
            "Rev weekly update: content published, community monitored. "
            "github.com/ivanma9/rev-agent #RevenueCat #AgentDev",
            dry_run=False,
            store=store
        ),
    }

# Module-level for testability
TASKS = _build_tasks(Store())

def run_now(task: str):
    store = Store()
    tasks = _build_tasks(store)
    if task not in tasks:
        print(f"Unknown task. Available: {list(tasks.keys())}")
        return
    print(f"Running: {task}")
    result = tasks[task]()
    print(f"Done: {result}")
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_scheduler.py -v 2>&1
```
Expected: ALL PASS (3 tests)

**Step 5: Run full suite**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/ -m "not integration" -v 2>&1 | tail -10
```
Expected: ALL PASS

**Step 6: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add src/scheduler.py tests/test_scheduler.py && git commit -m "feat: wire x_post into scheduler run_now"
```

---

### Task 4: Update requirements.txt

**Step 1: Freeze deps**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pip freeze > requirements.txt
```

**Step 2: Verify tweepy is listed**
```bash
grep tweepy /Users/ivanma/Desktop/agents/RevCat/requirements.txt
```
Expected: `tweepy==4.16.0`

**Step 3: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add requirements.txt && git commit -m "chore: add tweepy to requirements.txt"
```
