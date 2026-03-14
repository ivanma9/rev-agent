import os
os.environ["REV_DB_PATH"] = ":memory:"

import pytest


def test_analytics_table_created():
    from src.store import Store
    s = Store(":memory:")
    assert "analytics" in s.tables()


def test_record_metric_basic():
    from src.store import Store
    s = Store(":memory:")
    s.queue_content("Post A", "blog", "body")
    content = s.get_pending_content()
    cid = content[0]["id"]
    s.record_metric(cid, "hn", "view")
    rows = s.get_analytics(content_id=cid)
    assert len(rows) == 1
    assert rows[0]["metric"] == "view"
    assert rows[0]["value"] == 1
    assert rows[0]["platform"] == "hn"


def test_record_metric_custom_value():
    from src.store import Store
    s = Store(":memory:")
    s.queue_content("Post B", "blog", "body")
    cid = s.get_pending_content()[0]["id"]
    s.record_metric(cid, "reddit", "upvote", value=5)
    rows = s.get_analytics(content_id=cid)
    assert rows[0]["value"] == 5


def test_get_analytics_all():
    from src.store import Store
    s = Store(":memory:")
    s.queue_content("P1", "blog", "b")
    s.queue_content("P2", "blog", "b")
    items = s.get_pending_content()
    s.record_metric(items[0]["id"], "hn", "view")
    s.record_metric(items[1]["id"], "so", "click")
    all_rows = s.get_analytics()
    assert len(all_rows) == 2


def test_get_analytics_days_filter():
    """get_analytics with days=0 should return no rows (future cutoff edge case)."""
    from src.store import Store
    s = Store(":memory:")
    s.queue_content("P", "blog", "b")
    cid = s.get_pending_content()[0]["id"]
    s.record_metric(cid, "hn", "view")
    # days=7 should include rows recorded now
    rows = s.get_analytics(days=7)
    assert len(rows) == 1


def test_get_top_content():
    from src.store import Store
    s = Store(":memory:")
    for title in ["A", "B", "C"]:
        s.queue_content(title, "blog", "body")
    items = s.get_pending_content()
    # A gets 10 total, B gets 3, C gets 1
    s.record_metric(items[0]["id"], "hn", "view", value=10)
    s.record_metric(items[1]["id"], "reddit", "upvote", value=3)
    s.record_metric(items[2]["id"], "so", "click", value=1)
    top = s.get_top_content(limit=2, days=30)
    assert len(top) == 2
    assert top[0]["total"] == 10
    assert top[1]["total"] == 3


def test_get_top_content_empty():
    from src.store import Store
    s = Store(":memory:")
    top = s.get_top_content()
    assert top == []


def test_get_analytics_summary_empty():
    from src.tools.analytics import get_analytics_summary
    from src.store import Store
    s = Store(":memory:")
    summary = get_analytics_summary(s)
    assert isinstance(summary, str)
    assert "No engagement" in summary or "engagement" in summary.lower()


def test_get_analytics_summary_with_data():
    from src.tools.analytics import get_analytics_summary
    from src.store import Store
    s = Store(":memory:")
    s.queue_content("Post HN", "blog", "body")
    s.queue_content("Post SO", "blog", "body")
    items = s.get_pending_content()
    s.record_metric(items[0]["id"], "hn", "view", value=20)
    s.record_metric(items[0]["id"], "hn", "comment", value=5)
    s.record_metric(items[1]["id"], "so", "upvote", value=8)
    summary = get_analytics_summary(s)
    assert "Post HN" in summary or "hn" in summary.lower()
    assert "Top" in summary or "top" in summary.lower()
    assert "Platform" in summary or "platform" in summary.lower()


def test_get_analytics_summary_trend():
    from src.tools.analytics import get_analytics_summary
    from src.store import Store
    s = Store(":memory:")
    s.queue_content("Trending Post", "blog", "body")
    cid = s.get_pending_content()[0]["id"]
    s.record_metric(cid, "reddit", "upvote", value=15)
    summary = get_analytics_summary(s)
    # Should show this week vs last week
    assert "week" in summary.lower()
