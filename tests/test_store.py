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
    drafts = s.get_pending_drafts()
    assert len(drafts) == 1


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


# ── Task 1: new drafts columns ────────────────────────────────────────────────

def test_drafts_has_score_columns():
    """After migration, drafts table must have score, score_attempts, post_url."""
    from src.store import Store
    s = Store(":memory:")
    cols = [row[1] for row in s.conn.execute("PRAGMA table_info(drafts)").fetchall()]
    assert "score" in cols
    assert "score_attempts" in cols
    assert "post_url" in cols


def test_update_draft_score():
    from src.store import Store
    s = Store(":memory:")
    s.save_draft("hn", "https://hn.com/2", "Post", "snippet", "draft")
    draft_id = s.get_pending_drafts()[0]["id"]
    s.update_draft_score(draft_id, 8.5, 1)
    row = s.conn.execute("SELECT score, score_attempts FROM drafts WHERE id=?", (draft_id,)).fetchone()
    assert row["score"] == 8.5
    assert row["score_attempts"] == 1


def test_update_draft_response():
    from src.store import Store
    s = Store(":memory:")
    s.save_draft("hn", "https://hn.com/3", "Post", "snippet", "original draft")
    draft_id = s.get_pending_drafts()[0]["id"]
    s.update_draft_response(draft_id, "improved draft")
    row = s.conn.execute("SELECT draft_response FROM drafts WHERE id=?", (draft_id,)).fetchone()
    assert row["draft_response"] == "improved draft"


def test_record_post_url():
    from src.store import Store
    s = Store(":memory:")
    s.save_draft("reddit", "https://reddit.com/r/test/1", "Post", "snippet", "draft")
    draft_id = s.get_pending_drafts()[0]["id"]
    s.record_post_url(draft_id, "https://reddit.com/r/test/1/comment/abc")
    row = s.conn.execute("SELECT post_url FROM drafts WHERE id=?", (draft_id,)).fetchone()
    assert row["post_url"] == "https://reddit.com/r/test/1/comment/abc"


def test_get_draft_stats_this_week_empty():
    from src.store import Store
    s = Store(":memory:")
    stats = s.get_draft_stats_this_week()
    assert stats["posts_published"] == 0
    assert stats["drafts_created"] == 0
    assert stats["discarded"] == 0
    assert stats["avg_score_posted"] is None
    assert stats["errors_this_week"] == 0


def test_get_draft_stats_this_week_counts():
    from src.store import Store
    s = Store(":memory:")
    s.save_draft("hn", "https://hn.com/a", "Post A", "snip", "draft")
    s.save_draft("hn", "https://hn.com/b", "Post B", "snip", "draft")
    s.save_draft("hn", "https://hn.com/c", "Post C", "snip", "draft")
    drafts = s.get_pending_drafts()
    # Mark first as posted with score 9.0
    s.update_draft_score(drafts[0]["id"], 9.0, 1)
    s.mark_draft(drafts[0]["id"], "posted")
    # Mark second as discarded
    s.mark_draft(drafts[1]["id"], "discarded")
    # Log an error
    s.log_error("test_source", "some error")
    stats = s.get_draft_stats_this_week()
    assert stats["posts_published"] == 1
    assert stats["drafts_created"] == 3
    assert stats["discarded"] == 1
    assert stats["avg_score_posted"] == 9.0
    assert stats["errors_this_week"] == 1
