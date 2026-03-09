# Phase 3 P0 Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix four broken/incomplete things in the production agent: 404 ingest URLs, PyGithub deprecation, over-broad community relevance filter, and product feedback never being submitted.

**Architecture:** Small targeted fixes to existing modules. No new architecture. Each fix is isolated to one file.

**Tech Stack:** Python 3.11+, PyGithub, httpx, sqlite3, existing project stack.

---

### Task 1: Fix 404 Ingest URLs

**Files:**
- Modify: `src/tools/ingest.py`

**Step 1: Write failing test**

```python
# tests/test_ingest.py — add to existing file
def test_all_docs_urls_return_200():
    from src.tools.ingest import DOCS_URLS
    import httpx
    for url in DOCS_URLS:
        r = httpx.get(url, follow_redirects=True, timeout=15)
        assert r.status_code == 200, f"URL returned {r.status_code}: {url}"
```

**Step 2: Run to verify it fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_ingest.py::test_all_docs_urls_return_200 -v
```
Expected: FAIL — two URLs return 404

**Step 3: Fix the URLs in src/tools/ingest.py**

Replace lines 9-10:
```python
# old (404):
"https://www.revenuecat.com/docs/sdk-guides/ios",
"https://www.revenuecat.com/docs/sdk-guides/android",

# new (200):
"https://www.revenuecat.com/docs/getting-started/installation/ios",
"https://www.revenuecat.com/docs/getting-started/installation/android",
```

**Step 4: Run test**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_ingest.py -v
```
Expected: ALL PASS

**Step 5: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat
git add src/tools/ingest.py tests/test_ingest.py
git commit -m "fix: update 404 ingest URLs to correct revenuecat docs paths"
```

---

### Task 2: Fix PyGithub Deprecation Warning

**Files:**
- Modify: `src/tools/community_monitor.py`
- Modify: `src/tools/publisher.py`

**Step 1: Write failing test**

```python
# tests/test_github_auth.py
import warnings
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_no_deprecation_warning_in_community_monitor():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from src.tools import community_monitor  # reimport triggers module-level code
        # The deprecation fires at Github() call time, not import time
        # so we check the Github instantiation
        import importlib
        import src.tools.community_monitor as cm
        importlib.reload(cm)
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)
                        and "login_or_token" in str(x.message)]
        assert len(dep_warnings) == 0

def test_github_auth_uses_token_class():
    from github import Auth
    import os
    token = os.getenv("GITHUB_TOKEN", "fake-token")
    auth = Auth.Token(token)
    assert auth is not None
```

**Step 2: Run to verify**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_github_auth.py -v
```
Expected: test_github_auth_uses_token_class PASSES, test_no_deprecation_warning may pass (warning fires at call time)

**Step 3: Fix community_monitor.py**

Replace line 48 in `src/tools/community_monitor.py`:
```python
# old:
g = Github(GITHUB_TOKEN)

# new — add import at top of file after `from github import Github`:
from github import Auth

# then in scan_github_issues():
g = Github(auth=Auth.Token(GITHUB_TOKEN))
```

**Step 4: Fix publisher.py**

Replace line 36 in `src/tools/publisher.py`:
```python
# old:
g = Github(GITHUB_TOKEN)

# new — add import at top of file after `from github import Github`:
from github import Auth

# then in publish_to_github():
g = Github(auth=Auth.Token(GITHUB_TOKEN))
```

**Step 5: Verify no warning in output**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && python -W error::DeprecationWarning -c "
from src.tools.community_monitor import scan_github_issues
from src.tools.publisher import title_to_slug
print('No deprecation warnings.')
"
```
Expected: prints "No deprecation warnings." without error

**Step 6: Run full tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/ -v
```
Expected: ALL PASS

**Step 7: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat
git add src/tools/community_monitor.py src/tools/publisher.py tests/test_github_auth.py
git commit -m "fix: update PyGithub auth to use Auth.Token() API"
```

---

### Task 3: Tighten Community Relevance Filter

**Problem:** `is_relevant_to_agents()` matches too broadly. "bot" matches "robot", "automated" matches CI automation PRs, "agent" matches "agent" in GitHub Actions. Result: 43 false positives from Renovate/CI PRs.

**Files:**
- Modify: `src/tools/community_monitor.py`
- Modify: `tests/test_community_monitor.py`

**Step 1: Write failing tests**

```python
# tests/test_community_monitor.py — replace existing tests with expanded set

import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_is_relevant_to_agents_true_positives():
    from src.tools.community_monitor import is_relevant_to_agents
    assert is_relevant_to_agents("How do I use RevenueCat with my AI agent?") is True
    assert is_relevant_to_agents("autonomous agent building subscription app with revenuecat") is True
    assert is_relevant_to_agents("using LangChain with RevenueCat for automated billing") is True
    assert is_relevant_to_agents("openai function calling with revenuecat") is True
    assert is_relevant_to_agents("building an LLM-powered paywall") is True
    assert is_relevant_to_agents("Add AGENTS.md for AI coding assistants") is True

def test_is_relevant_to_agents_false_positives():
    from src.tools.community_monitor import is_relevant_to_agents
    # These were incorrectly matching before
    assert is_relevant_to_agents("[RENOVATE] Update dependency gradle to v9.4.0") is False
    assert is_relevant_to_agents("feat: add CircleCI job for maestro E2E tests") is False
    assert is_relevant_to_agents("feat: add maestro E2E test app") is False
    assert is_relevant_to_agents("Github Action: Update permissions") is False
    assert is_relevant_to_agents("Bug in StoreKit receipt validation") is False
    assert is_relevant_to_agents("Crash when calling purchasePackage on Android") is False
    assert is_relevant_to_agents("[DO NOT MERGE] Bump fastlane from 2.229.1 to 2.232.2") is False
    assert is_relevant_to_agents("Fix video audio session category to use .playback") is False

def test_format_github_comment():
    from src.tools.community_monitor import format_github_comment
    comment = format_github_comment("Great question! Here's how...")
    assert "Rev" in comment
    assert len(comment) > 20
```

**Step 2: Run to verify failures**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_community_monitor.py -v
```
Expected: Several false positive tests FAIL

**Step 3: Rewrite is_relevant_to_agents() in src/tools/community_monitor.py**

Replace the `AGENT_KEYWORDS` list and `is_relevant_to_agents` function:

```python
# Require whole-word or phrase matches to avoid substring false positives
AGENT_PHRASES = [
    "ai agent", "ai-agent",
    "llm", "gpt-", "gpt4", "gpt3",
    "claude api", "anthropic",
    "openai",
    "langchain", "langgraph",
    "agentic",
    "copilot",
    "autonomous agent",
    "agents.md",                    # GitHub AGENTS.md files
]

# Single words that must match as whole words only
AGENT_KEYWORDS_WHOLE_WORD = [
    "agent",    # whole word: "AI agent" yes, "Github Actions agent" no
    "agents",
]

import re

def is_relevant_to_agents(text: str) -> bool:
    text_lower = text.lower()

    # Skip known noise patterns
    NOISE_PATTERNS = ["renovate", "dependabot", "bump ", "fastlane", "circleci",
                      "maestro", "github action", "github actions", "[do not merge]"]
    if any(noise in text_lower for noise in NOISE_PATTERNS):
        return False

    # Check phrases (substring match is fine for these — they're specific enough)
    if any(phrase in text_lower for phrase in AGENT_PHRASES):
        return True

    # Check single keywords as whole words only
    for kw in AGENT_KEYWORDS_WHOLE_WORD:
        if re.search(rf'\b{re.escape(kw)}\b', text_lower):
            return True

    return False
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_community_monitor.py -v
```
Expected: ALL PASS

**Step 5: Run full suite**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/ -v
```
Expected: ALL PASS

**Step 6: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat
git add src/tools/community_monitor.py tests/test_community_monitor.py
git commit -m "fix: tighten community relevance filter to reduce false positives"
```

---

### Task 4: Product Feedback Submission via Email

**Problem:** `generate_weekly_feedback()` adds items to SQLite but they're never submitted anywhere. Wire submissions to send via email (Gmail SMTP using existing `GMAIL` + `GMAIL_PASSWORD` credentials already in `.env`).

**Files:**
- Create: `src/tools/feedback_submitter.py`
- Create: `tests/test_feedback_submitter.py`
- Modify: `src/store.py` — add `mark_feedback_submitted(id)`

**Step 1: Add mark_feedback_submitted to store**

Add to `src/store.py`:
```python
def mark_feedback_submitted(self, feedback_id: int):
    self.conn.execute(
        "UPDATE feedback SET submitted=1 WHERE id=?",
        (feedback_id,)
    )
    self.conn.commit()
```

**Step 2: Write failing tests**

```python
# tests/test_feedback_submitter.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_format_feedback_email():
    from src.tools.feedback_submitter import format_feedback_email
    body = format_feedback_email([
        {"title": "Add Python SDK", "body": "We need a Python SDK for agent use cases."},
        {"title": "Better webhook docs", "body": "Retry logic is not documented."},
    ])
    assert "Add Python SDK" in body
    assert "Better webhook docs" in body
    assert "Rev" in body

def test_get_unsubmitted_feedback():
    from src.store import Store
    from src.tools.feedback_submitter import get_unsubmitted_feedback
    store = Store(":memory:")
    store.add_feedback("Test title", "Test body")
    items = get_unsubmitted_feedback(store)
    assert len(items) == 1
    assert items[0]["title"] == "Test title"

def test_mark_submitted_clears_queue():
    from src.store import Store
    store = Store(":memory:")
    store.add_feedback("Test", "Body")
    items = store.get_feedback(submitted=False)
    store.mark_feedback_submitted(items[0]["id"])
    assert len(store.get_feedback(submitted=False)) == 0
    assert len(store.get_feedback(submitted=True)) == 1
```

**Step 3: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_feedback_submitter.py -v
```
Expected: ImportError / failures

**Step 4: Create src/tools/feedback_submitter.py**

```python
# src/tools/feedback_submitter.py
"""Submit queued product feedback to RevenueCat via email."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
from src.store import Store

load_dotenv()

GMAIL = os.getenv("GMAIL")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
FEEDBACK_RECIPIENT = "product@revenuecat.com"  # update if different


def format_feedback_email(items: list[dict]) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"Hi RevenueCat team,",
        f"",
        f"Here are {len(items)} product feedback items from Rev (AI Developer Advocate) — Week of {date}:",
        f"",
    ]
    for i, item in enumerate(items, 1):
        lines += [
            f"---",
            f"## {i}. {item['title']}",
            f"",
            item["body"],
            f"",
        ]
    lines += [
        "---",
        "These are generated from active usage of the RevenueCat API and SDK as an agent developer.",
        "",
        "— Rev | AI Developer Advocate",
        "  GitHub: https://github.com/ivanma9/rev-agent",
    ]
    return "\n".join(lines)


def get_unsubmitted_feedback(store: Store) -> list[dict]:
    return store.get_feedback(submitted=False)


def submit_feedback_by_email(store: Store = None, dry_run: bool = False) -> dict:
    """Email unsubmitted feedback items to RevenueCat. Marks them submitted on success."""
    if store is None:
        store = Store()

    items = get_unsubmitted_feedback(store)
    if not items:
        print("No unsubmitted feedback to send.")
        return {"sent": 0, "items": []}

    body = format_feedback_email(items)
    subject = f"[Rev Agent] Product Feedback — {datetime.now().strftime('%Y-W%W')}"

    if dry_run:
        print(f"[DRY RUN] Would send {len(items)} feedback items to {FEEDBACK_RECIPIENT}")
        print(f"Subject: {subject}")
        print(body[:500])
        return {"sent": len(items), "dry_run": True}

    msg = MIMEMultipart()
    msg["From"] = GMAIL
    msg["To"] = FEEDBACK_RECIPIENT
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL, GMAIL_PASSWORD)
            server.send_message(msg)

        for item in items:
            store.mark_feedback_submitted(item["id"])

        print(f"✓ Sent {len(items)} feedback items to {FEEDBACK_RECIPIENT}")
        return {"sent": len(items), "items": [i["title"] for i in items]}

    except Exception as e:
        print(f"✗ Failed to send feedback: {e}")
        return {"sent": 0, "error": str(e)}


if __name__ == "__main__":
    store = Store()
    result = submit_feedback_by_email(store, dry_run=True)
    print(f"\nResult: {result}")
```

**Step 5: Wire into scheduler** — add weekly feedback submission job

In `src/scheduler.py`, add to `_run_weekly_report()`:
```python
def _run_weekly_report(self):
    log.info("Generating weekly report...")
    if self.dry_run:
        log.info("[DRY RUN] Would generate report and submit feedback")
        return
    from src.tools.weekly_report import save_and_publish_report
    from src.tools.feedback_submitter import submit_feedback_by_email
    save_and_publish_report(self.store)
    submit_feedback_by_email(self.store)
```

**Step 6: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_feedback_submitter.py tests/test_store.py -v
```
Expected: ALL PASS

**Step 7: Run full suite**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/ -v
```
Expected: ALL PASS

**Step 8: Test dry run manually**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && python -c "
from src.store import Store
from src.tools.product_feedback import generate_weekly_feedback
from src.tools.feedback_submitter import submit_feedback_by_email
store = Store()
generate_weekly_feedback(store)
submit_feedback_by_email(store, dry_run=True)
"
```
Expected: Prints email preview with 3 feedback items

**Step 9: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat
git add src/tools/feedback_submitter.py tests/test_feedback_submitter.py src/store.py src/scheduler.py
git commit -m "feat: product feedback email submission via gmail smtp"
```

---

## Summary

| Task | Fix | Impact |
|------|-----|--------|
| 1 | Fix 2 broken ingest URLs | Knowledge sync covers full docs |
| 2 | Update PyGithub auth API | Clean warnings-free output |
| 3 | Tighten relevance filter | Reduces 43 false positives to true agent issues |
| 4 | Email feedback submission | Feedback actually reaches RevenueCat |
