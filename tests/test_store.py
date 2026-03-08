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
