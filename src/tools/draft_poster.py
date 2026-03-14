# src/tools/draft_poster.py
"""Post approved community drafts to their respective platforms."""
import os
import logging
from src.store import Store

try:
    import praw
except ImportError:
    praw = None

log = logging.getLogger(__name__)


def _get_approved_drafts(store: Store) -> list[dict]:
    rows = store.conn.execute(
        "SELECT * FROM drafts WHERE status = 'approved' ORDER BY created_at"
    ).fetchall()
    return [dict(r) for r in rows]


def _dry_run_print(draft: dict, reason: str = "manual posting required"):
    print(f"\n[DRY RUN — {draft['platform'].upper()}] {reason}")
    print(f"URL: {draft['url']}")
    print(f"Title: {draft['title']}")
    print(f"\n--- Draft Response ---")
    print(draft["draft_response"])
    print(f"--- End Draft ---")


def _post_hn(draft: dict, store: Store) -> tuple[bool, bool]:
    """HN has no public comment API — always dry run. Returns (posted, dry_run)."""
    _dry_run_print(draft, reason="HN has no public API for programmatic posting")
    return False, True


def _post_so(draft: dict, store: Store) -> tuple[bool, bool]:
    """SO API requires OAuth write auth — always dry run. Returns (posted, dry_run)."""
    _dry_run_print(draft, reason="SO API requires OAuth write access")
    return False, True


def _post_reddit(draft: dict, store: Store) -> tuple[bool, bool]:
    """Post to Reddit via PRAW if configured, else dry run. Returns (posted, dry_run)."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")
    reddit_username = os.getenv("REDDIT_USERNAME")
    reddit_password = os.getenv("REDDIT_PASSWORD")

    if not client_id:
        _dry_run_print(draft, reason="Reddit credentials not configured")
        return False, True

    if praw is None:
        _dry_run_print(draft, reason="praw not installed (pip install praw)")
        return False, True

    if not reddit_username or not reddit_password:
        _dry_run_print(draft, reason="REDDIT_USERNAME / REDDIT_PASSWORD not set for write access")
        return False, True

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            username=reddit_username,
            password=reddit_password,
        )
        # Extract submission ID from URL like https://reddit.com/r/.../comments/<id>/...
        url = draft["url"]
        submission = reddit.submission(url=url)
        comment = submission.reply(draft["draft_response"])
        print(f"[POSTED — REDDIT] Comment posted: https://reddit.com{comment.permalink}")
        return True, False
    except Exception as e:
        log.warning(f"Reddit post failed for {draft['url']}: {e}")
        store.log_error("draft_poster", f"Reddit post failed for {draft['url']}: {e}")
        return False, False


_PLATFORM_HANDLERS = {
    "hn": _post_hn,
    "so": _post_so,
    "reddit": _post_reddit,
}


def post_approved_drafts(store: Store = None) -> dict:
    """
    Fetch all approved drafts and attempt to post them.
    HN and SO are always dry-run (print URL + text for manual posting).
    Reddit posts via PRAW if credentials are available, otherwise dry-run.
    Marks each draft as 'posted' after processing.

    Returns a summary dict with keys: posted, dry_run, errors.
    """
    if store is None:
        store = Store()

    drafts = _get_approved_drafts(store)
    if not drafts:
        print("No approved drafts to post.")
        return {"posted": 0, "dry_run": 0, "errors": 0}

    total_posted = 0
    total_dry_run = 0
    total_errors = 0

    for draft in drafts:
        platform = draft["platform"]
        handler = _PLATFORM_HANDLERS.get(platform)

        if handler is None:
            log.warning(f"Unknown platform '{platform}' for draft id={draft['id']}, skipping.")
            store.log_error("draft_poster", f"Unknown platform '{platform}' for draft id={draft['id']}")
            total_errors += 1
            continue

        try:
            was_posted, was_dry_run = handler(draft, store)
            store.mark_draft(draft["id"], "posted")
            if was_posted:
                total_posted += 1
            elif was_dry_run:
                total_dry_run += 1
        except Exception as e:
            log.error(f"Unexpected error posting draft id={draft['id']}: {e}")
            store.log_error("draft_poster", f"Unexpected error for draft id={draft['id']}: {e}")
            total_errors += 1

    summary = {"posted": total_posted, "dry_run": total_dry_run, "errors": total_errors}
    print(
        f"\nPost summary: {total_posted} posted, {total_dry_run} dry-run (manual), {total_errors} errors."
    )
    return summary
