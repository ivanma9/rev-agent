# Observability & Status Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add error logging to SQLite and a CLI status dashboard showing all KPIs at a glance.

**Architecture:** New `errors` table in the Store with `log_error(source, message)` and `get_recent_errors()`. A new `src/tools/status.py` prints a single-screen summary. Existing tool except blocks get `store.log_error()` calls. Weekly report gains an errors section.

**Tech Stack:** Python 3.11+, SQLite store, existing tools.

---

### Task 1: Errors Table + Store Methods

**Files:**
- Modify: `src/store.py`
- Modify: `tests/test_store.py`

**Step 1: Write failing tests**

```python
# tests/test_store.py — add to existing file

def test_log_error():
    from src.store import Store
    s = Store(":memory:")
    s.log_error("publisher", "Failed to publish: 403 Forbidden")
    errors = s.get_recent_errors()
    assert len(errors) == 1
    assert errors[0]["source"] == "publisher"
    assert "403" in errors[0]["message"]


def test_get_recent_errors_limit():
    from src.store import Store
    s = Store(":memory:")
    for i in range(10):
        s.log_error("test", f"Error {i}")
    errors = s.get_recent_errors(limit=5)
    assert len(errors) == 5


def test_get_recent_errors_empty():
    from src.store import Store
    s = Store(":memory:")
    errors = s.get_recent_errors()
    assert errors == []
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_store.py::test_log_error -v 2>&1
```
Expected: AttributeError

**Step 3: Implement**

Add to `_init_tables` in `src/store.py`, inside the existing `executescript`:

```sql
CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
```

Add two methods to the Store class:

```python
def log_error(self, source: str, message: str):
    self.conn.execute(
        "INSERT INTO errors (source, message) VALUES (?, ?)",
        (source, message)
    )
    self.conn.commit()

def get_recent_errors(self, limit: int = 10) -> list[dict]:
    rows = self.conn.execute(
        "SELECT * FROM errors ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    return [dict(r) for r in rows]
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_store.py -v 2>&1
```
Expected: ALL PASS (12 tests)

**Step 5: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add src/store.py tests/test_store.py && git commit -m "feat: errors table and store methods for observability"
```

---

### Task 2: CLI Status Dashboard

**Files:**
- Create: `src/tools/status.py`
- Create: `tests/test_status.py`

**Step 1: Write failing tests**

```python
# tests/test_status.py
import os
os.environ["REV_DB_PATH"] = ":memory:"


def test_show_status_returns_string():
    from src.tools.status import format_status
    from src.store import Store
    s = Store(":memory:")
    output = format_status(s)
    assert "Content" in output
    assert "Interactions" in output
    assert "Feedback" in output
    assert "Errors" in output


def test_show_status_with_data():
    from src.tools.status import format_status
    from src.store import Store
    s = Store(":memory:")
    s.queue_content("Test Post", "blog", "body")
    s.log_interaction("github", "https://github.com/test", "test")
    s.log_error("test", "Something broke")
    output = format_status(s)
    assert "1 pending" in output
    assert "1 this week" in output
    assert "1 in last 7 days" in output or "1" in output


def test_show_status_shows_recent_errors():
    from src.tools.status import format_status
    from src.store import Store
    s = Store(":memory:")
    s.log_error("publisher", "403 Forbidden")
    s.log_error("community", "Rate limited")
    output = format_status(s)
    assert "403 Forbidden" in output
    assert "Rate limited" in output
```

**Step 2: Run to verify fails**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_status.py -v 2>&1 | head -20
```
Expected: ImportError

**Step 3: Implement src/tools/status.py**

```python
# src/tools/status.py
"""CLI status dashboard for Rev agent."""
from datetime import datetime, timedelta
from src.store import Store


def format_status(store: Store) -> str:
    """Format a single-screen status summary."""
    published = store.get_published_content()
    pending = store.get_pending_content()
    ideas = [p for p in pending if p["content_type"] == "idea"]
    non_ideas = [p for p in pending if p["content_type"] != "idea"]

    interactions = store.interaction_count_this_week()
    feedback_pending = store.get_feedback(submitted=False)
    feedback_submitted = store.get_feedback(submitted=True)
    drafts = store.get_pending_drafts()
    errors = store.get_recent_errors(limit=5)

    # Last sync time
    last_sync = store.conn.execute(
        "SELECT checked_at FROM knowledge_versions ORDER BY checked_at DESC LIMIT 1"
    ).fetchone()
    sync_time = last_sync["checked_at"] if last_sync else "never"

    # Error count in last 7 days
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    error_count = store.conn.execute(
        "SELECT COUNT(*) as cnt FROM errors WHERE created_at > ?",
        (week_ago,)
    ).fetchone()["cnt"]

    lines = [
        "Rev Agent Status",
        "=" * 40,
        f"Content:      {len(published)} published | {len(non_ideas)} pending | {len(ideas)} ideas",
        f"Interactions: {interactions} this week (target: 50)",
        f"Feedback:     {len(feedback_pending)} pending | {len(feedback_submitted)} submitted",
        f"Drafts:       {len(drafts)} pending review",
        f"Errors:       {error_count} in last 7 days",
        f"Last sync:    {sync_time}",
    ]

    if errors:
        lines.append("")
        lines.append("Recent errors:")
        for e in errors[:5]:
            lines.append(f"  [{e['source']}] {e['message'][:80]} ({e['created_at'][:16]})")

    if drafts:
        lines.append("")
        lines.append("Pending drafts:")
        for d in drafts[:3]:
            lines.append(f"  [{d['platform']}] {d['title'][:50]}")

    return "\n".join(lines)


if __name__ == "__main__":
    store = Store()
    print(format_status(store))
```

**Step 4: Run tests**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/test_status.py -v 2>&1
```
Expected: 3 PASSED

**Step 5: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add src/tools/status.py tests/test_status.py && git commit -m "feat: CLI status dashboard"
```

---

### Task 3: Wire Error Logging Into Existing Tools

**Files:**
- Modify: `src/tools/publisher.py`
- Modify: `src/tools/community_monitor.py`
- Modify: `src/tools/community_scanner.py`
- Modify: `src/tools/feedback_submitter.py`
- Modify: `src/scheduler.py`
- Modify: `src/tools/weekly_report.py`

**Step 1: No new tests needed** — error logging is additive to existing except blocks. Existing tests still pass.

**Step 2: Add error logging to each tool**

In `src/tools/publisher.py`, in the `publish_pending` except block (around line 77):
```python
        except Exception as e:
            print(f"✗ Failed to publish '{item['title']}': {e}")
            if store:
                store.log_error("publisher", f"Failed to publish '{item['title'][:50]}': {e}")
```

In `src/tools/community_monitor.py`, in the `scan_github_issues` except block (around line 113):
```python
        except Exception as e:
            print(f"✗ Failed {repo_name}: {e}")
            if store:
                store.log_error("community_monitor", f"Failed {repo_name}: {e}")
```

In `src/tools/community_scanner.py`, in `scan_communities` draft generation except block:
```python
        except Exception as e:
            log.warning(f"  Failed to draft for {item['url']}: {e}")
            if store:
                store.log_error("community_scanner", f"Failed to draft: {e}")
```

In `src/tools/feedback_submitter.py`, in the `submit_feedback_by_email` except block (around line 90):
```python
    except Exception as e:
        log.error(f"Failed to send feedback: {e}")
        if store:
            store.log_error("feedback_submitter", f"Failed to send feedback: {e}")
        return {"sent": 0, "error": str(e)}
```

In `src/scheduler.py`, wrap each `_run_*` method's main body in try/except that logs errors. For example in `_run_knowledge_sync`:
```python
    def _run_knowledge_sync(self):
        log.info("Running knowledge sync...")
        if self.dry_run:
            log.info("[DRY RUN] Would sync knowledge")
            return
        try:
            from src.tools.knowledge_sync import sync_knowledge
            sync_knowledge(self.store)
        except Exception as e:
            log.error(f"Knowledge sync failed: {e}")
            self.store.log_error("scheduler", f"knowledge_sync failed: {e}")
```

Apply the same pattern to `_run_weekly_content`, `_run_publish`, `_run_community_scan`, `_run_weekly_report`. Note: `_run_publish` already has a try/except around `build_full_site` — add `self.store.log_error()` to that existing except block too.

In `src/tools/weekly_report.py`, after the "Product Feedback" section, add:
```python
    # Errors
    errors = store.get_recent_errors(limit=5)
    lines += [
        "",
        "## Errors",
        f"- Errors in last 7 days: {len(errors)}",
    ]
    if errors:
        for e in errors[:3]:
            lines.append(f"  - [{e['source']}] {e['message'][:60]}")
```

**Step 3: Run full test suite**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && source .venv/bin/activate && pytest tests/ -m "not integration" -v 2>&1 | tail -15
```
Expected: ALL PASS

**Step 4: Commit**
```bash
cd /Users/ivanma/Desktop/agents/RevCat && git add src/tools/publisher.py src/tools/community_monitor.py src/tools/community_scanner.py src/tools/feedback_submitter.py src/scheduler.py src/tools/weekly_report.py && git commit -m "feat: wire error logging into all tools and scheduler"
```

---

## Summary

| Task | Output |
|------|--------|
| 1 | Errors table + `log_error()` / `get_recent_errors()` |
| 2 | CLI status dashboard (`python -m src.tools.status`) |
| 3 | Error logging wired into publisher, community monitor, scanner, feedback, scheduler, weekly report |

**Usage:**
```bash
python -m src.tools.status    # show all KPIs at a glance
```
