"""CLI status dashboard for Rev agent."""
from datetime import datetime, timedelta
from src.store import Store


def format_status(store: Store) -> str:
    """Format a single-screen status summary."""
    published = store.get_published_content()
    pending = store.get_pending_content()
    ideas = [p for p in pending if p["content_type"] == "idea"]
    non_ideas = [p for p in pending if p["content_type"] != "idea"]

    interactions = store.interaction_count_this_week()
    analytics_this_week = sum(r["value"] for r in store.get_analytics(days=7))
    feedback_pending = store.get_feedback(submitted=False)
    feedback_submitted = store.get_feedback(submitted=True)
    drafts = store.get_pending_drafts()
    errors = store.get_recent_errors(limit=5)

    # Last sync time
    last_sync = store.conn.execute(
        "SELECT checked_at FROM knowledge_versions ORDER BY checked_at DESC LIMIT 1"
    ).fetchone()
    sync_time = last_sync["checked_at"] if last_sync else "never"

    # Error count in last 7 days
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    error_count = store.conn.execute(
        "SELECT COUNT(*) as cnt FROM errors WHERE created_at > ?",
        (week_ago,)
    ).fetchone()["cnt"]

    lines = [
        "Rev Agent Status",
        "=" * 40,
        f"Content:      {len(published)} published | {len(non_ideas)} pending | {len(ideas)} ideas",
        f"Interactions: {interactions} this week (target: 50)",
        f"Engagement:   {analytics_this_week} metric events this week",
        f"Feedback:     {len(feedback_pending)} pending | {len(feedback_submitted)} submitted",
        f"Drafts:       {len(drafts)} pending review",
        f"Errors:       {error_count} in last 7 days",
        f"Last sync:    {sync_time}",
    ]

    if errors:
        lines.append("")
        lines.append("Recent errors:")
        for e in errors[:5]:
            lines.append(f"  [{e['source']}] {e['message'][:80]} ({e['created_at'][:16]})")

    if drafts:
        lines.append("")
        lines.append("Pending drafts:")
        for d in drafts[:3]:
            lines.append(f"  [{d['platform']}] {d['title'][:50]}")

    return "\n".join(lines)


if __name__ == "__main__":
    store = Store()
    print(format_status(store))
