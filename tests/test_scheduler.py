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

def test_scheduler_run_now_has_x_post():
    from src.scheduler import TASK_KEYS, _build_tasks
    from src.store import Store
    assert "x_post" in TASK_KEYS
    # Also verify _build_tasks helper has all expected keys
    tasks = _build_tasks(Store(":memory:"))
    assert "x_post" in tasks
    assert "feedback_submit" in tasks
    assert "build_site" in tasks
    assert "sync" in tasks
