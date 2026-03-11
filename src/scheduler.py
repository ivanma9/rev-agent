# src/scheduler.py
"""Rev — Autonomous Scheduler

Runs the weekly job loop:
  Daily:   knowledge sync
  Monday:  generate content + feedback
  Tuesday: publish content
  Friday:  generate + publish weekly report
  Daily:   community scan (GitHub issues)
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from src.store import Store
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

class RevScheduler:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.store = Store()
        self._scheduler = BackgroundScheduler()
        self._register_jobs()

    def _register_jobs(self):
        self._scheduler.add_job(
            self._run_knowledge_sync,
            "cron", hour=6, minute=0,
            id="daily_sync", name="Daily Knowledge Sync"
        )
        self._scheduler.add_job(
            self._run_weekly_content,
            "cron", day_of_week="mon", hour=8,
            id="weekly_content", name="Weekly Content Generation"
        )
        self._scheduler.add_job(
            self._run_publish,
            "cron", day_of_week="tue", hour=10,
            id="weekly_publish", name="Publish Content"
        )
        self._scheduler.add_job(
            self._run_community_scan,
            "cron", hour=10, minute=30,
            id="community_scan", name="Community Monitor"
        )
        self._scheduler.add_job(
            self._run_weekly_report,
            "cron", day_of_week="fri", hour=16,
            id="weekly_report", name="Weekly Report"
        )

    def job_ids(self) -> list[str]:
        return [job.id for job in self._scheduler.get_jobs()]

    def _run_knowledge_sync(self):
        log.info("Running knowledge sync...")
        if self.dry_run:
            log.info("[DRY RUN] Would sync knowledge")
            return
        from src.tools.knowledge_sync import sync_knowledge
        sync_knowledge(self.store)

    def _run_weekly_content(self):
        log.info("Generating weekly content + feedback...")
        if self.dry_run:
            log.info("[DRY RUN] Would generate content")
            return
        from src.tools.content_generator import generate_weekly_content
        from src.tools.product_feedback import generate_weekly_feedback
        generate_weekly_content(self.store)
        generate_weekly_feedback(self.store)

    def _run_publish(self):
        log.info("Publishing pending content...")
        if self.dry_run:
            log.info("[DRY RUN] Would publish content")
            return
        from src.tools.publisher import publish_pending
        publish_pending(self.store)
        try:
            from src.tools.build_site import build_full_site
            build_full_site(self.store)
        except Exception:
            log.exception("Site build failed after publish")

    def _run_community_scan(self):
        log.info("Scanning community channels...")
        if self.dry_run:
            log.info("[DRY RUN] Would scan community")
            return
        from src.tools.community_monitor import scan_github_issues
        scan_github_issues(self.store, post_comments=True)
        from src.tools.community_scanner import scan_communities
        scan_communities(self.store)

    def _run_weekly_report(self):
        log.info("Generating weekly report...")
        if self.dry_run:
            log.info("[DRY RUN] Would generate report and submit feedback")
            return
        from src.tools.weekly_report import save_and_publish_report
        from src.tools.feedback_submitter import submit_feedback_by_email
        save_and_publish_report(self.store)
        submit_feedback_by_email(self.store)

    def start(self):
        log.info("Rev scheduler starting...")
        for job in self._scheduler.get_jobs():
            log.info(f"  Registered: {job.name} ({job.id})")
        self._scheduler.start()

    def stop(self):
        self._scheduler.shutdown()

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
        scheduler = RevScheduler()
        try:
            scheduler.start()
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            scheduler.stop()
            print("Scheduler stopped.")
