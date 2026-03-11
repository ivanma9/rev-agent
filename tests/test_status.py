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


def test_show_status_shows_recent_errors():
    from src.tools.status import format_status
    from src.store import Store
    s = Store(":memory:")
    s.log_error("publisher", "403 Forbidden")
    s.log_error("community", "Rate limited")
    output = format_status(s)
    assert "403 Forbidden" in output
    assert "Rate limited" in output
