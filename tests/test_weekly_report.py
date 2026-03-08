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
