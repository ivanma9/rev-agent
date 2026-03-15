# Rev Agent — Phase 2: Production Autonomous Loop

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform Rev from a one-shot application pipeline into a fully autonomous agent that runs weekly job responsibilities: daily knowledge sync, content generation, community monitoring, product feedback, and weekly reports.

**Architecture:** A scheduler-driven agent loop using APScheduler. Each responsibility is an independent tool module triggered on a schedule. State is persisted in SQLite. Content is queued, generated via Claude API, and published to GitHub (as markdown files/gists). Community monitoring uses the GitHub API and web scraping. Weekly reports are compiled and saved as structured markdown.

**Tech Stack:** Python 3.11+, APScheduler, SQLite (via sqlite3), Claude API, GitHub API (PyGithub), httpx, BeautifulSoup4, existing project stack.

---

### Task 1: SQLite State Store

**Files:**
- Create: `src/store.py`
- Create: `tests/test_store.py`

**Step 1: Write failing tests**

```python
# tests/test_store.py
import os
import pytest

os.environ["REV_DB_PATH"] = ":memory:"

def test_init_creates_tables():
    from src.store import Store
    s = Store(":memory:")
    tables = s.tables()
    assert "content" in tables
    assert "knowledge_versions" in tables
    assert "interactions" in tables
    assert "feedback" in tables

def test_queue_and_get_content():
    from src.store import Store
    s = Store(":memory:")
    s.queue_content(title="Test post", content_type="blog", body="Hello world")
    items = s.get_pending_content()
    assert len(items) == 1
    assert items[0]["title"] == "Test post"

def test_mark_content_published():
    from src.store import Store
    s = Store(":memory:")
    s.queue_content(title="Test", content_type="blog", body="Body")
    items = s.get_pending_content()
    s.mark_published(items[0]["id"], url="https://example.com")
    assert len(s.get_pending_content()) == 0

def test_log_interaction():
    from src.store import Store
    s = Store(":memory:")
    s.log_interaction(platform="github", url="https://github.com/issue/1", summary="Commented on issue")
    count = s.interaction_count_this_week()
    assert count == 1

def test_add_feedback():
    from src.store import Store
    s = Store(":memory:")
    s.add_feedback(title="Missing webhook docs", body="The webhook docs don't cover retry logic.")
    items = s.get_feedback()
    assert len(items) == 1
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_store.py -v
```
Expected: ImportError

**Step 3: Implement src/store.py**

```python
# src/store.py
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import os

DEFAULT_DB_PATH = "data/rev.db"

class Store:
    def __init__(self, db_path: Optional[str] = None):
        path = db_path or os.getenv("REV_DB_PATH", DEFAULT_DB_PATH)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content_type TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                url TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                published_at TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                hash TEXT NOT NULL,
                checked_at TEXT DEFAULT (datetime('now')),
                changed INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                url TEXT,
                summary TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                submitted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()

    def tables(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return [r["name"] for r in rows]

    def queue_content(self, title: str, content_type: str, body: str):
        self.conn.execute(
            "INSERT INTO content (title, content_type, body) VALUES (?, ?, ?)",
            (title, content_type, body)
        )
        self.conn.commit()

    def get_pending_content(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM content WHERE status = 'pending' ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_published(self, content_id: int, url: str):
        self.conn.execute(
            "UPDATE content SET status='published', url=?, published_at=datetime('now') WHERE id=?",
            (url, content_id)
        )
        self.conn.commit()

    def log_interaction(self, platform: str, url: str, summary: str):
        self.conn.execute(
            "INSERT INTO interactions (platform, url, summary) VALUES (?, ?, ?)",
            (platform, url, summary)
        )
        self.conn.commit()

    def interaction_count_this_week(self) -> int:
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM interactions WHERE created_at > ?",
            (week_ago,)
        ).fetchone()
        return row["cnt"]

    def add_feedback(self, title: str, body: str):
        self.conn.execute(
            "INSERT INTO feedback (title, body) VALUES (?, ?)",
            (title, body)
        )
        self.conn.commit()

    def get_feedback(self, submitted: bool = False) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM feedback WHERE submitted = ? ORDER BY created_at",
            (1 if submitted else 0,)
        ).fetchall()
        return [dict(r) for r in rows]

    def record_knowledge_check(self, source: str, hash_val: str, changed: bool):
        self.conn.execute(
            "INSERT INTO knowledge_versions (source, hash, changed) VALUES (?, ?, ?)",
            (source, hash_val, 1 if changed else 0)
        )
        self.conn.commit()

    def get_published_content(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM content WHERE status='published' ORDER BY published_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_store.py -v
```
Expected: 5 PASSED

**Step 5: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat
git add src/store.py tests/test_store.py
git commit -m "feat: sqlite state store for agent memory"
```

---

### Task 2: Daily Knowledge Sync with Change Detection

**Files:**
- Create: `src/tools/knowledge_sync.py`
- Modify: `src/tools/ingest.py` — add `hash_content()` helper
- Create: `tests/test_knowledge_sync.py`

**Step 1: Write failing tests**

```python
# tests/test_knowledge_sync.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_hash_content_is_deterministic():
    from src.tools.knowledge_sync import hash_content
    assert hash_content("hello") == hash_content("hello")
    assert hash_content("hello") != hash_content("world")

def test_sync_returns_changes():
    from src.tools.knowledge_sync import sync_knowledge
    from src.store import Store
    store = Store(":memory:")
    # First sync — everything is "new"
    changes = sync_knowledge(store=store, dry_run=True)
    assert isinstance(changes, list)

def test_no_false_positives_on_second_sync(tmp_path):
    from src.tools.knowledge_sync import hash_content, detect_change
    content = "same content"
    h = hash_content(content)
    changed = detect_change("test_source", h, {})
    assert changed is True
    state = {"test_source": h}
    changed2 = detect_change("test_source", h, state)
    assert changed2 is False
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_knowledge_sync.py -v
```

**Step 3: Implement src/tools/knowledge_sync.py**

```python
# src/tools/knowledge_sync.py
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from src.tools.ingest import fetch_page, extract_text, DOCS_URLS
from src.store import Store
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

ADDITIONAL_URLS = [
    "https://www.revenuecat.com/blog/",
    "https://github.com/RevenueCat/purchases-ios/releases",
    "https://github.com/RevenueCat/purchases-android/releases",
    "https://github.com/RevenueCat/react-native-purchases/releases",
]

ALL_URLS = DOCS_URLS + ADDITIONAL_URLS

def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]

def detect_change(source: str, new_hash: str, previous_hashes: dict) -> bool:
    return previous_hashes.get(source) != new_hash

def generate_content_idea(source: str, old_text: str, new_text: str) -> str:
    """Ask Claude what changed and suggest content ideas."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""You are Rev, an AI developer advocate for RevenueCat.
A documentation page changed: {source}

Briefly describe what likely changed and suggest ONE content idea that would be valuable
to agent developers based on this change. Keep it under 100 words total.

New content snippet:
{new_text[:1000]}"""
        }]
    )
    return response.content[0].text

def sync_knowledge(store: Store = None, dry_run: bool = False) -> list[dict]:
    """Fetch all tracked pages, detect changes, queue content ideas."""
    if store is None:
        store = Store()

    changes = []
    output_dir = Path("knowledge/revenuecat/docs")
    output_dir.mkdir(parents=True, exist_ok=True)

    for url in ALL_URLS:
        try:
            html = fetch_page(url)
            text = extract_text(html)
            new_hash = hash_content(text)
            slug = url.rstrip("/").split("/")[-1] or "index"
            cache_path = output_dir / f"{slug}.txt"

            old_text = cache_path.read_text() if cache_path.exists() else ""
            old_hash = hash_content(old_text) if old_text else ""
            changed = detect_change(url, new_hash, {url: old_hash})

            if changed and not dry_run:
                cache_path.write_text(text)
                store.record_knowledge_check(url, new_hash, changed=True)

                if old_text:  # not first run
                    idea = generate_content_idea(url, old_text, text)
                    store.queue_content(
                        title=f"[Auto] Content idea from {slug} update",
                        content_type="idea",
                        body=idea
                    )
                    changes.append({"url": url, "idea": idea})
                    print(f"✓ Change detected: {url}")
            elif not dry_run:
                store.record_knowledge_check(url, new_hash, changed=False)

            changes.append({"url": url, "changed": changed, "hash": new_hash})

        except Exception as e:
            print(f"✗ Failed {url}: {e}")

    return changes

if __name__ == "__main__":
    store = Store()
    changes = sync_knowledge(store)
    changed = [c for c in changes if c.get("changed")]
    print(f"\nSync complete. {len(changed)} changes detected out of {len(changes)} sources.")
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_knowledge_sync.py -v
```
Expected: 3 PASSED

**Step 5: Run manually**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && python -m src.tools.knowledge_sync
```
Expected: Sync runs, reports changes/no-changes

**Step 6: Commit**
```bash
git add src/tools/knowledge_sync.py tests/test_knowledge_sync.py
git commit -m "feat: daily knowledge sync with change detection"
```

---

### Task 3: Content Generation Pipeline

**Files:**
- Create: `src/tools/content_generator.py`
- Create: `tests/test_content_generator.py`

**Step 1: Write failing tests**

```python
# tests/test_content_generator.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_generate_blog_post_dry_run():
    from src.tools.content_generator import generate_content
    result = generate_content(
        topic="How to use RevenueCat webhooks with AI agents",
        content_type="blog",
        dry_run=True
    )
    assert isinstance(result, str)
    assert len(result) > 50

def test_content_types():
    from src.tools.content_generator import CONTENT_TYPES
    assert "blog" in CONTENT_TYPES
    assert "tutorial" in CONTENT_TYPES
    assert "code_sample" in CONTENT_TYPES
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_content_generator.py -v
```

**Step 3: Implement src/tools/content_generator.py**

```python
# src/tools/content_generator.py
from anthropic import Anthropic
from pathlib import Path
from src.store import Store
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

CONTENT_TYPES = ["blog", "tutorial", "code_sample", "case_study", "growth_experiment"]

SYSTEM_PROMPT = """You are Rev, an autonomous AI agent and developer advocate for RevenueCat.
Write technical content that is:
- Developer-first: concrete, practical, with real code
- Opinionated: strong takes, not wishy-washy
- Agentic-AI focused: always connect to the agent developer use case
- RevenueCat-specific: reference real APIs, SDKs, endpoints

Voice: senior dev advocate who ships things. No fluff, no corporate speak."""

TEMPLATES = {
    "blog": """Write a technical blog post (600-900 words) about: {topic}

Structure:
# [Compelling title]
## The Problem
## The Solution (with RevenueCat)
## Code Example
```python
# Real working code using RevenueCat API
```
## Key Takeaways

Sign off as: Rev | @rev_agent""",

    "tutorial": """Write a step-by-step tutorial (800-1200 words) about: {topic}

Structure:
# [Title: How to X with RevenueCat]
## Prerequisites
## Step 1: ...
## Step 2: ...
(include working code at each step)
## What's Next

Sign off as: Rev | @rev_agent""",

    "code_sample": """Write a focused code sample with explanation for: {topic}

Include:
- A complete, runnable Python script using RevenueCat's REST API
- Brief explanation of what it does and why
- Usage instructions

Sign off as: Rev | @rev_agent""",

    "case_study": """Write a growth-focused case study (500-700 words) about: {topic}

Structure:
# [Title]
## The Setup
## The Experiment
## Results & Learnings
## How to Replicate This

Sign off as: Rev | @rev_agent""",

    "growth_experiment": """Design a growth experiment brief (300-500 words) for: {topic}

Structure:
# Experiment: [Name]
## Hypothesis
## Method
## Success Metrics
## RevenueCat Integration Points
## Timeline

Sign off as: Rev | @rev_agent""",
}

def generate_content(topic: str, content_type: str = "blog", dry_run: bool = False) -> str:
    if dry_run:
        return f"# Dry run\n\nWould generate {content_type} about: {topic}"

    template = TEMPLATES.get(content_type, TEMPLATES["blog"])
    prompt = template.format(topic=topic)

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def generate_weekly_content(store: Store = None) -> list[dict]:
    """Generate 2 pieces of content for the week based on queue + trending topics."""
    if store is None:
        store = Store()

    DEFAULT_TOPICS = [
        ("How AI agents can use RevenueCat webhooks to trigger automated responses", "tutorial"),
        ("Building a subscription-aware agent with RevenueCat's CustomerInfo API", "code_sample"),
        ("RevenueCat Experiments API: letting your agent run A/B tests autonomously", "blog"),
        ("Using RevenueCat Charts API to give your agent revenue awareness", "tutorial"),
        ("How to build a paywall decision engine with RevenueCat Targeting", "blog"),
        ("RevenueCat + LangGraph: building a subscription management agent", "code_sample"),
        ("Growth experiment: programmatic SEO for agent developer tools", "growth_experiment"),
        ("Case study: what happens when an AI agent manages its own RevenueCat offerings", "case_study"),
    ]

    # Check queue for ideas first
    pending = store.get_pending_content()
    ideas = [(p["body"][:100], "blog") for p in pending if p["content_type"] == "idea"]

    topics_to_use = (ideas + DEFAULT_TOPICS)[:2]
    results = []

    for topic, content_type in topics_to_use:
        print(f"Generating {content_type}: {topic[:60]}...")
        body = generate_content(topic, content_type)
        store.queue_content(title=topic[:80], content_type=content_type, body=body)
        results.append({"topic": topic, "content_type": content_type, "chars": len(body)})
        print(f"  ✓ Generated ({len(body)} chars)")

    return results

if __name__ == "__main__":
    store = Store()
    results = generate_weekly_content(store)
    print(f"\nGenerated {len(results)} pieces of content.")
    for r in results:
        print(f"  - [{r['content_type']}] {r['topic'][:60]}... ({r['chars']} chars)")
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_content_generator.py -v
```
Expected: 2 PASSED

**Step 5: Run manually**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && python -m src.tools.content_generator
```
Expected: 2 pieces of content generated and queued in DB

**Step 6: Commit**
```bash
git add src/tools/content_generator.py tests/test_content_generator.py
git commit -m "feat: weekly content generation pipeline"
```

---

### Task 4: GitHub Publisher

**Files:**
- Create: `src/tools/publisher.py`
- Create: `tests/test_publisher.py`

**Step 1: Write failing tests**

```python
# tests/test_publisher.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_slug_generation():
    from src.tools.publisher import title_to_slug
    slug = title_to_slug("How to Build a RevenueCat Agent")
    assert slug == "how-to-build-a-revenuecat-agent"
    assert " " not in slug

def test_format_for_github():
    from src.tools.publisher import format_for_github
    content = format_for_github(
        title="Test Post",
        body="# Hello\n\nWorld",
        content_type="blog"
    )
    assert "Test Post" in content
    assert "rev_agent" in content.lower() or "rev" in content.lower()
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_publisher.py -v
```

**Step 3: Implement src/tools/publisher.py**

```python
# src/tools/publisher.py
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os
from github import Github
from src.store import Store

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "ivanma9/rev-agent"
CONTENT_DIR = "content"

def title_to_slug(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug.strip())
    return slug[:60]

def format_for_github(title: str, body: str, content_type: str) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    header = f"""---
title: "{title}"
date: {date}
type: {content_type}
author: Rev
---

"""
    footer = f"\n\n---\n*Published by Rev | [@rev_agent](https://x.com/rev_agent) | [GitHub](https://github.com/ivanma9/rev-agent)*"
    return header + body + footer

def publish_to_github(title: str, body: str, content_type: str) -> str:
    """Publish content as a file in the GitHub repo. Returns the file URL."""
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)

    date = datetime.now().strftime("%Y-%m-%d")
    slug = title_to_slug(title)
    filename = f"{CONTENT_DIR}/{date}-{slug}.md"
    formatted = format_for_github(title, body, content_type)

    try:
        existing = repo.get_contents(filename)
        repo.update_file(
            filename,
            f"content: update {slug}",
            formatted,
            existing.sha
        )
    except Exception:
        repo.create_file(
            filename,
            f"content: publish {slug}",
            formatted
        )

    url = f"https://github.com/{GITHUB_REPO}/blob/main/{filename}"
    print(f"✓ Published: {url}")
    return url

def publish_pending(store: Store = None, limit: int = 2) -> list[dict]:
    """Publish up to `limit` pending content items to GitHub."""
    if store is None:
        store = Store()

    pending = [p for p in store.get_pending_content() if p["content_type"] != "idea"][:limit]
    published = []

    for item in pending:
        try:
            url = publish_to_github(item["title"], item["body"], item["content_type"])
            store.mark_published(item["id"], url=url)
            published.append({"title": item["title"], "url": url})
        except Exception as e:
            print(f"✗ Failed to publish '{item['title']}': {e}")

    return published

if __name__ == "__main__":
    store = Store()
    results = publish_pending(store)
    print(f"\nPublished {len(results)} pieces.")
    for r in results:
        print(f"  - {r['title'][:60]}: {r['url']}")
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_publisher.py -v
```
Expected: 2 PASSED

**Step 5: Commit**
```bash
git add src/tools/publisher.py tests/test_publisher.py
git commit -m "feat: github publisher for content"
```

---

### Task 5: Community Monitor (GitHub Issues)

**Files:**
- Create: `src/tools/community_monitor.py`
- Create: `tests/test_community_monitor.py`

**Step 1: Write failing tests**

```python
# tests/test_community_monitor.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_is_relevant_to_agents():
    from src.tools.community_monitor import is_relevant_to_agents
    assert is_relevant_to_agents("How do I use RevenueCat with my AI agent?") is True
    assert is_relevant_to_agents("Bug in StoreKit receipt validation") is False
    assert is_relevant_to_agents("autonomous agent building app with revenuecat") is True

def test_format_github_comment():
    from src.tools.community_monitor import format_github_comment
    comment = format_github_comment("Great question! Here's how...")
    assert "Rev" in comment
    assert len(comment) > 20
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_community_monitor.py -v
```

**Step 3: Implement src/tools/community_monitor.py**

```python
# src/tools/community_monitor.py
import os
from dotenv import load_dotenv
from github import Github
from anthropic import Anthropic
from src.store import Store

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REVENUECAT_REPOS = [
    "RevenueCat/purchases-ios",
    "RevenueCat/purchases-android",
    "RevenueCat/react-native-purchases",
    "RevenueCat/purchases-flutter",
]

AGENT_KEYWORDS = [
    "agent", "autonomous", "llm", "gpt", "claude", "ai app", "bot",
    "automated", "openai", "langchain", "agentic", "copilot"
]

client = Anthropic()

def is_relevant_to_agents(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in AGENT_KEYWORDS)

def format_github_comment(response_text: str) -> str:
    return f"{response_text}\n\n---\n*— Rev, AI Developer Advocate [@rev_agent](https://x.com/rev_agent)*"

def generate_response(issue_title: str, issue_body: str) -> str:
    """Generate a helpful response to a GitHub issue using Claude."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system="""You are Rev, an AI developer advocate for RevenueCat.
Write a helpful, technically accurate response to a GitHub issue.
Be concise (under 200 words), practical, and reference relevant RevenueCat docs when possible.
Don't be sycophantic. Get to the answer quickly.""",
        messages=[{
            "role": "user",
            "content": f"Issue: {issue_title}\n\n{issue_body[:500]}\n\nWrite a helpful response:"
        }]
    )
    return response.content[0].text

def scan_github_issues(store: Store = None, post_comments: bool = False) -> list[dict]:
    """Scan RevenueCat repos for agent-related issues and optionally respond."""
    if store is None:
        store = Store()

    g = Github(GITHUB_TOKEN)
    found = []

    for repo_name in REVENUECAT_REPOS:
        try:
            repo = g.get_repo(repo_name)
            issues = repo.get_issues(state="open", sort="created", direction="desc")

            for issue in list(issues)[:20]:  # check last 20 per repo
                if not is_relevant_to_agents(f"{issue.title} {issue.body or ''}"):
                    continue

                response_text = generate_response(issue.title, issue.body or "")
                comment_body = format_github_comment(response_text)

                if post_comments:
                    issue.create_comment(comment_body)
                    store.log_interaction(
                        platform="github",
                        url=issue.html_url,
                        summary=f"Commented on: {issue.title[:60]}"
                    )
                    print(f"✓ Commented on: {issue.html_url}")

                found.append({
                    "repo": repo_name,
                    "url": issue.html_url,
                    "title": issue.title,
                    "response": response_text,
                })

        except Exception as e:
            print(f"✗ Failed {repo_name}: {e}")

    return found

if __name__ == "__main__":
    store = Store()
    # Scan only, don't post (set post_comments=True when ready)
    issues = scan_github_issues(store, post_comments=False)
    print(f"\nFound {len(issues)} agent-related issues:")
    for i in issues:
        print(f"  [{i['repo']}] {i['title'][:60]}")
        print(f"    → {i['url']}")
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_community_monitor.py -v
```
Expected: 2 PASSED

**Step 5: Run scan manually (no posting)**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && python -m src.tools.community_monitor
```

**Step 6: Commit**
```bash
git add src/tools/community_monitor.py tests/test_community_monitor.py
git commit -m "feat: github community monitor for agent-related issues"
```

---

### Task 6: Weekly Report Generator

**Files:**
- Create: `src/tools/weekly_report.py`
- Create: `tests/test_weekly_report.py`

**Step 1: Write failing tests**

```python
# tests/test_weekly_report.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_generate_report_empty_store():
    from src.tools.weekly_report import generate_weekly_report
    from src.store import Store
    store = Store(":memory:")
    report = generate_weekly_report(store=store)
    assert isinstance(report, str)
    assert "Week" in report or "Report" in report
    assert len(report) > 100

def test_report_contains_sections():
    from src.tools.weekly_report import generate_weekly_report
    from src.store import Store
    store = Store(":memory:")
    store.log_interaction("github", "https://github.com/test", "Test interaction")
    store.add_feedback("Missing docs", "Webhook retry docs are missing")
    report = generate_weekly_report(store=store)
    assert "Content" in report or "content" in report
    assert "interaction" in report.lower() or "community" in report.lower()
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_weekly_report.py -v
```

**Step 3: Implement src/tools/weekly_report.py**

```python
# src/tools/weekly_report.py
from datetime import datetime
from pathlib import Path
from src.store import Store
from dotenv import load_dotenv

load_dotenv()

def generate_weekly_report(store: Store = None) -> str:
    if store is None:
        store = Store()

    date = datetime.now().strftime("%Y-%m-%d")
    week_num = datetime.now().isocalendar()[1]

    published = store.get_published_content(limit=10)
    pending = store.get_pending_content()
    interaction_count = store.interaction_count_this_week()
    feedback = store.get_feedback(submitted=False)

    # Build report
    lines = [
        f"# Rev Weekly Report — Week {week_num} ({date})",
        "",
        "## Content",
        f"- Published this week: {len(published)}",
        f"- In queue: {len(pending)}",
    ]

    if published:
        lines.append("")
        lines.append("**Published:**")
        for p in published[:5]:
            url = p.get("url", "—")
            lines.append(f"- [{p['title'][:60]}]({url})")

    lines += [
        "",
        "## Community Engagement",
        f"- Interactions this week: {interaction_count}",
        f"- Target: 50+",
        f"- Status: {'✅ On track' if interaction_count >= 50 else f'⚠️ Behind ({50 - interaction_count} to go)'}",
        "",
        "## Product Feedback",
        f"- Unsubmitted feedback items: {len(feedback)}",
    ]

    if feedback:
        lines.append("")
        lines.append("**Pending feedback:**")
        for f_item in feedback[:3]:
            lines.append(f"- {f_item['title']}")

    lines += [
        "",
        "## Growth Experiments",
        "- See content queue for experiment briefs",
        "",
        "## Next Week",
        "- Continue daily knowledge sync",
        "- Generate 2+ new content pieces",
        "- Target 50+ community interactions",
        "- Submit pending product feedback",
        "",
        "---",
        f"*Generated autonomously by Rev | {date}*"
    ]

    return "\n".join(lines)

def save_and_publish_report(store: Store = None) -> str:
    if store is None:
        store = Store()

    report = generate_weekly_report(store)
    date = datetime.now().strftime("%Y-%m-%d")

    # Save locally
    reports_dir = Path("output/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{date}-weekly-report.md"
    report_path.write_text(report)
    print(f"✓ Report saved: {report_path}")

    # Queue for GitHub publish
    store.queue_content(
        title=f"Weekly Report — {date}",
        content_type="report",
        body=report
    )

    return report

if __name__ == "__main__":
    store = Store()
    report = save_and_publish_report(store)
    print("\n" + report)
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_weekly_report.py -v
```
Expected: 2 PASSED

**Step 5: Run manually**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && python -m src.tools.weekly_report
```

**Step 6: Commit**
```bash
git add src/tools/weekly_report.py tests/test_weekly_report.py
git commit -m "feat: weekly async report generator"
```

---

### Task 7: Product Feedback Generator

**Files:**
- Create: `src/tools/product_feedback.py`
- Create: `tests/test_product_feedback.py`

**Step 1: Write failing tests**

```python
# tests/test_product_feedback.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_generate_feedback_dry_run():
    from src.tools.product_feedback import generate_feedback_item
    item = generate_feedback_item(
        observation="The webhook documentation doesn't cover retry logic for agent use cases.",
        dry_run=True
    )
    assert isinstance(item, dict)
    assert "title" in item
    assert "body" in item

def test_feedback_has_required_fields():
    from src.tools.product_feedback import generate_feedback_item
    item = generate_feedback_item(
        observation="No Python SDK available, only mobile SDKs.",
        dry_run=True
    )
    assert len(item["title"]) > 5
    assert len(item["body"]) > 20
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_product_feedback.py -v
```

**Step 3: Implement src/tools/product_feedback.py**

```python
# src/tools/product_feedback.py
from anthropic import Anthropic
from src.store import Store
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

DEFAULT_OBSERVATIONS = [
    "RevenueCat's REST API requires manual polling — there's no streaming or real-time push for agent use cases beyond webhooks.",
    "No official Python SDK exists. Agents building server-side logic must use REST directly, which is verbose.",
    "The Experiments API doesn't support programmatic traffic reallocation mid-experiment — agents can't auto-optimize.",
    "Webhook event types don't include offering impression events, so agents can't detect paywall views.",
    "The Charts API has no endpoint for cohort analysis, making it hard for agents to compute LTV segments automatically.",
]

def generate_feedback_item(observation: str, dry_run: bool = False) -> dict:
    if dry_run:
        return {
            "title": f"[Agent Feedback] {observation[:60]}",
            "body": f"**Observation:** {observation}\n\n**Impact:** High for agent developers.\n\n**Suggested fix:** Provide better tooling."
        }

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system="""You are Rev, an AI agent and RevenueCat power user.
Write structured product feedback in this exact format:
Title: [Short, actionable title under 60 chars]
Body: [2-3 paragraphs: what you observed, why it matters for agent developers, suggested improvement]""",
        messages=[{
            "role": "user",
            "content": f"Observation: {observation}\n\nWrite structured product feedback:"
        }]
    )

    text = response.content[0].text
    lines = text.strip().split("\n")
    title = lines[0].replace("Title:", "").strip() if lines else observation[:60]
    body = "\n".join(lines[1:]).replace("Body:", "").strip() if len(lines) > 1 else text

    return {"title": title, "body": body}

def generate_weekly_feedback(store: Store = None) -> list[dict]:
    """Generate 3 product feedback items from default observations."""
    if store is None:
        store = Store()

    results = []
    for obs in DEFAULT_OBSERVATIONS[:3]:
        item = generate_feedback_item(obs)
        store.add_feedback(title=item["title"], body=item["body"])
        results.append(item)
        print(f"✓ Feedback queued: {item['title'][:60]}")

    return results

if __name__ == "__main__":
    store = Store()
    items = generate_weekly_feedback(store)
    print(f"\nGenerated {len(items)} feedback items.")
    for item in items:
        print(f"\n### {item['title']}\n{item['body'][:200]}...")
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_product_feedback.py -v
```
Expected: 2 PASSED

**Step 5: Commit**
```bash
git add src/tools/product_feedback.py tests/test_product_feedback.py
git commit -m "feat: product feedback generator"
```

---

### Task 8: Autonomous Scheduler

**Files:**
- Create: `src/scheduler.py`
- Create: `tests/test_scheduler.py`
- Modify: `requirements.txt` — add apscheduler

**Step 1: Install APScheduler**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate
pip install apscheduler
pip freeze > requirements.txt
```

**Step 2: Write failing tests**

```python
# tests/test_scheduler.py
def test_scheduler_imports():
    from src.scheduler import RevScheduler
    s = RevScheduler(dry_run=True)
    assert s is not None

def test_scheduler_has_jobs():
    from src.scheduler import RevScheduler
    s = RevScheduler(dry_run=True)
    job_ids = s.job_ids()
    assert "daily_sync" in job_ids
    assert "weekly_content" in job_ids
    assert "weekly_report" in job_ids
    assert "community_scan" in job_ids
```

**Step 3: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_scheduler.py -v
```

**Step 4: Implement src/scheduler.py**

```python
# src/scheduler.py
"""Rev — Autonomous Scheduler

Runs the weekly job loop:
  Daily:   knowledge sync
  Monday:  generate content + feedback
  Tuesday: publish content
  Friday:  generate + publish weekly report
  Daily:   community scan (GitHub issues)
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from src.store import Store
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

class RevScheduler:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.store = Store()
        self._scheduler = BackgroundScheduler()
        self._register_jobs()

    def _register_jobs(self):
        # Daily: knowledge sync (6am UTC)
        self._scheduler.add_job(
            self._run_knowledge_sync,
            "cron", hour=6, minute=0,
            id="daily_sync", name="Daily Knowledge Sync"
        )
        # Monday 8am: generate content + feedback
        self._scheduler.add_job(
            self._run_weekly_content,
            "cron", day_of_week="mon", hour=8,
            id="weekly_content", name="Weekly Content Generation"
        )
        # Tuesday 10am: publish content
        self._scheduler.add_job(
            self._run_publish,
            "cron", day_of_week="tue", hour=10,
            id="weekly_publish", name="Publish Content"
        )
        # Daily: community scan (10am UTC)
        self._scheduler.add_job(
            self._run_community_scan,
            "cron", hour=10, minute=30,
            id="community_scan", name="Community Monitor"
        )
        # Friday 4pm: weekly report
        self._scheduler.add_job(
            self._run_weekly_report,
            "cron", day_of_week="fri", hour=16,
            id="weekly_report", name="Weekly Report"
        )

    def job_ids(self) -> list[str]:
        return [job.id for job in self._scheduler.get_jobs()]

    def _run_knowledge_sync(self):
        log.info("Running knowledge sync...")
        if self.dry_run:
            log.info("[DRY RUN] Would sync knowledge")
            return
        from src.tools.knowledge_sync import sync_knowledge
        sync_knowledge(self.store)

    def _run_weekly_content(self):
        log.info("Generating weekly content + feedback...")
        if self.dry_run:
            log.info("[DRY RUN] Would generate content")
            return
        from src.tools.content_generator import generate_weekly_content
        from src.tools.product_feedback import generate_weekly_feedback
        generate_weekly_content(self.store)
        generate_weekly_feedback(self.store)

    def _run_publish(self):
        log.info("Publishing pending content...")
        if self.dry_run:
            log.info("[DRY RUN] Would publish content")
            return
        from src.tools.publisher import publish_pending
        publish_pending(self.store)

    def _run_community_scan(self):
        log.info("Scanning community channels...")
        if self.dry_run:
            log.info("[DRY RUN] Would scan community")
            return
        from src.tools.community_monitor import scan_github_issues
        scan_github_issues(self.store, post_comments=True)

    def _run_weekly_report(self):
        log.info("Generating weekly report...")
        if self.dry_run:
            log.info("[DRY RUN] Would generate report")
            return
        from src.tools.weekly_report import save_and_publish_report
        save_and_publish_report(self.store)

    def start(self):
        log.info("Rev scheduler starting...")
        for job in self._scheduler.get_jobs():
            log.info(f"  Registered: {job.name} ({job.id})")
        self._scheduler.start()

    def stop(self):
        self._scheduler.shutdown()

def run_now(task: str):
    """Run a specific task immediately for testing."""
    store = Store()
    tasks = {
        "sync": lambda: __import__("src.tools.knowledge_sync", fromlist=["sync_knowledge"]).sync_knowledge(store),
        "content": lambda: __import__("src.tools.content_generator", fromlist=["generate_weekly_content"]).generate_weekly_content(store),
        "publish": lambda: __import__("src.tools.publisher", fromlist=["publish_pending"]).publish_pending(store),
        "community": lambda: __import__("src.tools.community_monitor", fromlist=["scan_github_issues"]).scan_github_issues(store, post_comments=False),
        "report": lambda: __import__("src.tools.weekly_report", fromlist=["save_and_publish_report"]).save_and_publish_report(store),
        "feedback": lambda: __import__("src.tools.product_feedback", fromlist=["generate_weekly_feedback"]).generate_weekly_feedback(store),
    }
    if task not in tasks:
        print(f"Unknown task. Available: {list(tasks.keys())}")
        return
    print(f"Running: {task}")
    result = tasks[task]()
    print(f"Done: {result}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run_now(sys.argv[1])
    else:
        scheduler = RevScheduler()
        try:
            scheduler.start()
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            scheduler.stop()
            print("Scheduler stopped.")
```

**Step 5: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_scheduler.py -v
```
Expected: 2 PASSED

**Step 6: Test running a task immediately**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && python -m src.scheduler content
```
Expected: Content generation runs immediately

**Step 7: Commit**
```bash
git add src/scheduler.py tests/test_scheduler.py requirements.txt
git commit -m "feat: autonomous weekly scheduler with apscheduler"
git push origin main
```

---

## Summary

| Task | Output |
|------|--------|
| 1 | SQLite state store (content, interactions, feedback, knowledge versions) |
| 2 | Daily knowledge sync with change detection + content idea generation |
| 3 | Weekly content generator (2+ pieces: blogs, tutorials, code samples) |
| 4 | GitHub publisher (markdown files in repo) |
| 5 | Community monitor (GitHub issues scanner + response generator) |
| 6 | Weekly report generator |
| 7 | Product feedback generator |
| 8 | APScheduler-based autonomous loop |

**To run Rev autonomously:**
```bash
python -m src.scheduler
```

**To run any task immediately:**
```bash
python -m src.scheduler sync      # knowledge sync
python -m src.scheduler content   # generate content
python -m src.scheduler publish   # publish to GitHub
python -m src.scheduler community # scan community
python -m src.scheduler report    # weekly report
python -m src.scheduler feedback  # product feedback
```
