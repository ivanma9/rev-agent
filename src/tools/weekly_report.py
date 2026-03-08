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
        "",
        "## Product Feedback",
        f"- Unsubmitted feedback items: {len(feedback)}",
    ]

    if feedback:
        lines.append("")
        lines.append("**Pending feedback:**")
        for f_item in feedback[:3]:
            lines.append(f"- {f_item['title']}")

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
