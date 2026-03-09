# src/tools/feedback_submitter.py
"""Submit queued product feedback to RevenueCat via email."""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
from src.store import Store

load_dotenv()

log = logging.getLogger(__name__)

GMAIL = os.getenv("GMAIL")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
FEEDBACK_RECIPIENT = "product@revenuecat.com"


def format_feedback_email(items: list[dict]) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "Hi RevenueCat team,",
        "",
        f"Here are {len(items)} product feedback items from Rev (AI Developer Advocate) — Week of {date}:",
        "",
    ]
    for i, item in enumerate(items, 1):
        lines += [
            "---",
            f"## {i}. {item['title']}",
            "",
            item["body"],
            "",
        ]
    lines += [
        "---",
        "These are generated from active usage of the RevenueCat API and SDK as an agent developer.",
        "",
        "— Rev | AI Developer Advocate",
        "  GitHub: https://github.com/ivanma9/rev-agent",
    ]
    return "\n".join(lines)


def get_unsubmitted_feedback(store: Store) -> list[dict]:
    return store.get_feedback(submitted=False)


def submit_feedback_by_email(store: Store = None, dry_run: bool = False) -> dict:
    """Email unsubmitted feedback items to RevenueCat. Marks them submitted on success."""
    if store is None:
        store = Store()

    items = get_unsubmitted_feedback(store)
    if not items:
        print("No unsubmitted feedback to send.")
        return {"sent": 0, "items": []}

    body = format_feedback_email(items)
    subject = f"[Rev Agent] Product Feedback — {datetime.now().strftime('%Y-W%W')}"

    if dry_run:
        print(f"[DRY RUN] Would send {len(items)} feedback items to {FEEDBACK_RECIPIENT}")
        print(f"Subject: {subject}")
        print(body[:500])
        return {"sent": len(items), "dry_run": True}

    msg = MIMEMultipart()
    msg["From"] = GMAIL
    msg["To"] = FEEDBACK_RECIPIENT
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL, GMAIL_PASSWORD)
            server.send_message(msg)

        log.info(f"Email sent successfully to {FEEDBACK_RECIPIENT} with {len(items)} items. Marking submitted...")

        for item in items:
            store.mark_feedback_submitted(item["id"])
            log.info(f"Marked submitted: {item['id']} — {item['title'][:50]}")

        print(f"Sent {len(items)} feedback items to {FEEDBACK_RECIPIENT}")
        return {"sent": len(items), "items": [i["title"] for i in items]}

    except Exception as e:
        print(f"Failed to send feedback: {e}")
        return {"sent": 0, "error": str(e)}


if __name__ == "__main__":
    store = Store()
    result = submit_feedback_by_email(store, dry_run=True)
    print(f"\nResult: {result}")
