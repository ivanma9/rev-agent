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
    from src.scheduler import TASKS
    assert "x_post" in TASKS
