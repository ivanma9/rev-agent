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

def test_submit_feedback_dry_run():
    from src.store import Store
    from src.tools.feedback_submitter import submit_feedback_by_email
    store = Store(":memory:")
    store.add_feedback("Test feedback", "Some body text here.")
    result = submit_feedback_by_email(store, dry_run=True)
    assert result["sent"] == 1
    assert result.get("dry_run") is True
    # Items should NOT be marked submitted in dry run
    assert len(store.get_feedback(submitted=False)) == 1

def test_submit_feedback_empty_store():
    from src.store import Store
    from src.tools.feedback_submitter import submit_feedback_by_email
    store = Store(":memory:")
    result = submit_feedback_by_email(store, dry_run=True)
    assert result["sent"] == 0
