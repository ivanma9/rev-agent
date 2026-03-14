# src/scheduler.py
"""Rev — Task Runner

Runs individual tasks on demand (triggered by GitHub Actions cron workflows).

Available tasks: sync, content, publish, community, report, feedback,
                 feedback_submit, scan_communities, build_site, x_post
"""
from dotenv import load_dotenv
from src.store import Store
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

def _build_tasks(store: Store) -> dict:
    return {
        "sync": lambda: __import__("src.tools.knowledge_sync", fromlist=["sync_knowledge"]).sync_knowledge(store),
        "content": lambda: __import__("src.tools.content_generator", fromlist=["generate_weekly_content"]).generate_weekly_content(store),
        "publish": lambda: __import__("src.tools.publisher", fromlist=["publish_pending"]).publish_pending(store),
        "community": lambda: __import__("src.tools.community_monitor", fromlist=["scan_github_issues"]).scan_github_issues(store, post_comments=False),
        "report": lambda: __import__("src.tools.weekly_report", fromlist=["save_and_publish_report"]).save_and_publish_report(store),
        "feedback": lambda: __import__("src.tools.product_feedback", fromlist=["generate_weekly_feedback"]).generate_weekly_feedback(store),
        "feedback_submit": lambda: __import__("src.tools.feedback_submitter", fromlist=["submit_feedback_by_email"]).submit_feedback_by_email(store, dry_run=False),
        "scan_communities": lambda: __import__("src.tools.community_scanner", fromlist=["scan_communities"]).scan_communities(store),
        "build_site": lambda: __import__("src.tools.build_site", fromlist=["build_full_site"]).build_full_site(store),
        "x_post": lambda: __import__("src.tools.x_publisher", fromlist=["post_tweet"]).post_tweet(
            "Rev weekly update: content published, community monitored. "
            "github.com/ivanma9/rev-agent #RevenueCat #AgentDev",
            dry_run=False,
            store=store
        ),
    }

# Module-level for testability
def _get_task_keys() -> list[str]:
    """Return available task names without opening a real DB connection."""
    return list(_build_tasks(Store(":memory:")).keys())

TASK_KEYS = _get_task_keys()

def run_now(task: str):
    store = Store()
    tasks = _build_tasks(store)
    if task not in tasks:
        print(f"Unknown task. Available: {list(tasks.keys())}")
        return
    print(f"Running: {task}")
    result = tasks[task]()
    print(f"Done: {result}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        run_now(sys.argv[1])
    else:
        print("Available tasks:", TASK_KEYS)
        print("Usage: python -m src.scheduler <task>")
