# src/tools/weekly_report.py
from datetime import datetime
from pathlib import Path
from src.store import Store
from dotenv import load_dotenv

load_dotenv()

def generate_weekly_report(store: Store = None) -> str:
    if store is None:
        store = Store()

    date = datetime.now().strftime("%Y-%m-%d")
    week_num = datetime.now().isocalendar()[1]

    published = store.get_published_content(limit=10)
    pending = store.get_pending_content()
    interaction_count = store.interaction_count_this_week()
    feedback = store.get_feedback(submitted=False)

    lines = [
        f"# Rev Weekly Report — Week {week_num} ({date})",
        "",
        "## Content",
        f"- Published this week: {len(published)}",
        f"- In queue: {len(pending)}",
    ]

    if published:
        lines.append("")
        lines.append("**Published:**")
        for p in published[:5]:
            url = p.get("url", "—")
            lines.append(f"- [{p['title'][:60]}]({url})")

    lines += [
        "",
        "## Community Engagement",
        f"- Interactions this week: {interaction_count}",
        f"- Target: 50+",
        f"- Status: {'✅ On track' if interaction_count >= 50 else f'⚠️ Behind ({50 - interaction_count} to go)'}",
    ]

    # Pending drafts
    drafts = store.get_pending_drafts()
    if drafts:
        lines.append(f"- Pending draft responses: {len(drafts)}")
        for d in drafts[:3]:
            lines.append(f"  - [{d['platform']}] {d['title'][:50]}")

    lines += [
        "",
        "## Product Feedback",
        f"- Unsubmitted feedback items: {len(feedback)}",
    ]

    if feedback:
        lines.append("")
        lines.append("**Pending feedback:**")
        for f_item in feedback[:3]:
            lines.append(f"- {f_item['title']}")

    # Errors
    errors = store.get_recent_errors(limit=5)
    lines += [
        "",
        "## Errors",
        f"- Errors in last 7 days: {len(errors)}",
    ]
    if errors:
        for e in errors[:3]:
            lines.append(f"  - [{e['source']}] {e['message'][:60]}")

    # Auto-Post Scorecard
    stats = store.get_draft_stats_this_week()
    posts_published = stats["posts_published"]
    drafts_created = stats["drafts_created"]
    discarded = stats["discarded"]
    avg_score = stats["avg_score_posted"]
    errors_this_week = stats["errors_this_week"]

    if drafts_created > 0:
        success_rate = f"{posts_published / drafts_created * 100:.0f}%"
    else:
        success_rate = "N/A"

    avg_score_str = f"{avg_score:.1f}/10" if avg_score is not None else "N/A"

    lines += [
        "",
        "## Auto-Post Scorecard",
        f"- Posts published this week: {posts_published}",
        f"- Communities scanned (drafts created): {drafts_created}",
        f"- Auto-post success rate: {success_rate} (posted / total drafts created)",
        f"- Discarded: {discarded}",
        f"- Avg score of posted drafts: {avg_score_str}",
        f"- Errors this week: {errors_this_week} (scheduler uptime proxy)",
    ]

    lines += [
        "",
        "## Growth Experiments",
        "- See content queue for experiment briefs",
        "",
        "## Next Week",
        "- Continue daily knowledge sync",
        "- Generate 2+ new content pieces",
        "- Target 50+ community interactions",
        "- Submit pending product feedback",
        "",
        "---",
        f"*Generated autonomously by Rev | {date}*"
    ]

    return "\n".join(lines)

def save_and_publish_report(store: Store = None) -> str:
    if store is None:
        store = Store()

    report = generate_weekly_report(store)
    date = datetime.now().strftime("%Y-%m-%d")

    reports_dir = Path("output/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{date}-weekly-report.md"
    report_path.write_text(report)
    print(f"✓ Report saved: {report_path}")

    store.queue_content(
        title=f"Weekly Report — {date}",
        content_type="report",
        body=report
    )

    return report

if __name__ == "__main__":
    store = Store()
    report = save_and_publish_report(store)
    print("\n" + report)
