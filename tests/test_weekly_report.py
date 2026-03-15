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


def test_weekly_report_includes_scorecard_section():
    from src.tools.weekly_report import generate_weekly_report
    from src.store import Store
    store = Store(":memory:")
    # Seed one posted draft with score=8.5
    store.save_draft("reddit", "https://reddit.com/r/test/1", "Test Post 1", "body snippet", "draft response")
    draft = store.get_draft_by_url("https://reddit.com/r/test/1")
    store.mark_draft(draft["id"], "posted")
    store.update_draft_score(draft["id"], 8.5, 1)
    # Seed one discarded draft
    store.save_draft("reddit", "https://reddit.com/r/test/2", "Test Post 2", "body snippet 2", "draft response 2")
    draft2 = store.get_draft_by_url("https://reddit.com/r/test/2")
    store.mark_draft(draft2["id"], "discarded")

    report = generate_weekly_report(store=store)
    assert "Auto-Post Scorecard" in report
    assert "success rate" in report.lower()


def test_weekly_report_scorecard_empty_state():
    from src.tools.weekly_report import generate_weekly_report
    from src.store import Store
    store = Store(":memory:")
    report = generate_weekly_report(store=store)
    assert "Auto-Post Scorecard" in report
    assert "0" in report
