# tests/test_scheduler.py
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

def test_scheduler_has_community_scan_task():
    from src.scheduler import TASK_KEYS
    assert "scan_communities" in TASK_KEYS

def test_task_keys_complete():
    from src.scheduler import TASK_KEYS
    expected = {"sync", "content", "publish", "community", "report",
                "feedback", "feedback_submit", "scan_communities", "build_site", "x_post"}
    assert expected == set(TASK_KEYS)
