"""Engagement analytics tool for Rev agent."""
from datetime import datetime, timedelta
from src.store import Store


def get_analytics_summary(store: Store) -> str:
    """Return a formatted analytics summary string."""
    top = store.get_top_content(limit=5, days=30)
    this_week = store.get_analytics(days=7)
    last_week_rows = _get_last_week_analytics(store)

    if not top and not this_week:
        return "No engagement data recorded yet."

    lines = ["Engagement Analytics", "=" * 40]

    # Top 5 content pieces
    lines.append("Top performing content (last 30 days):")
    if top:
        for i, row in enumerate(top, 1):
            title = row.get("title") or f"content #{row['content_id']}"
            lines.append(f"  {i}. {title[:60]}  ({row['total']} total)")
    else:
        lines.append("  (none)")

    # Platform breakdown
    lines.append("")
    lines.append("Platform breakdown (last 7 days):")
    platform_totals: dict[str, int] = {}
    for row in this_week:
        platform_totals[row["platform"]] = platform_totals.get(row["platform"], 0) + row["value"]

    platforms = ["hn", "so", "reddit", "github"]
    for p in platforms:
        count = platform_totals.get(p, 0)
        lines.append(f"  {p.upper():8s}: {count}")

    # Trend: this week vs last week
    this_week_total = sum(r["value"] for r in this_week)
    last_week_total = sum(r["value"] for r in last_week_rows)
    lines.append("")
    lines.append("Trend (this week vs last week):")
    lines.append(f"  This week: {this_week_total}  |  Last week: {last_week_total}")
    if last_week_total > 0:
        pct = (this_week_total - last_week_total) / last_week_total * 100
        direction = "up" if pct >= 0 else "down"
        lines.append(f"  Change: {direction} {abs(pct):.1f}%")

    return "\n".join(lines)


def _get_last_week_analytics(store: Store) -> list[dict]:
    """Fetch analytics rows from 8–14 days ago (last week window)."""
    cutoff_start = (datetime.now() - timedelta(days=14)).isoformat()
    cutoff_end = (datetime.now() - timedelta(days=7)).isoformat()
    rows = store.conn.execute(
        "SELECT * FROM analytics WHERE recorded_at > ? AND recorded_at <= ?",
        (cutoff_start, cutoff_end)
    ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    store = Store()
    print(get_analytics_summary(store))
