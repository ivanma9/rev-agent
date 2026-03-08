# src/tools/product_feedback.py
from anthropic import Anthropic
from src.store import Store
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

DEFAULT_OBSERVATIONS = [
    "RevenueCat's REST API requires manual polling — there's no streaming or real-time push for agent use cases beyond webhooks.",
    "No official Python SDK exists. Agents building server-side logic must use REST directly, which is verbose.",
    "The Experiments API doesn't support programmatic traffic reallocation mid-experiment — agents can't auto-optimize.",
    "Webhook event types don't include offering impression events, so agents can't detect paywall views.",
    "The Charts API has no endpoint for cohort analysis, making it hard for agents to compute LTV segments automatically.",
]

def generate_feedback_item(observation: str, dry_run: bool = False) -> dict:
    if dry_run:
        return {
            "title": f"[Agent Feedback] {observation[:60]}",
            "body": f"**Observation:** {observation}\n\n**Impact:** High for agent developers.\n\n**Suggested fix:** Provide better tooling."
        }

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system="""You are Rev, an AI agent and RevenueCat power user.
Write structured product feedback in this exact format:
Title: [Short, actionable title under 60 chars]
Body: [2-3 paragraphs: what you observed, why it matters for agent developers, suggested improvement]""",
        messages=[{"role": "user", "content": f"Observation: {observation}\n\nWrite structured product feedback:"}]
    )

    text = response.content[0].text
    lines = text.strip().split("\n")
    title = lines[0].replace("Title:", "").strip() if lines else observation[:60]
    body = "\n".join(lines[1:]).replace("Body:", "").strip() if len(lines) > 1 else text

    return {"title": title, "body": body}

def generate_weekly_feedback(store: Store = None) -> list[dict]:
    if store is None:
        store = Store()

    results = []
    for obs in DEFAULT_OBSERVATIONS[:3]:
        item = generate_feedback_item(obs)
        store.add_feedback(title=item["title"], body=item["body"])
        results.append(item)
        print(f"✓ Feedback queued: {item['title'][:60]}")

    return results

if __name__ == "__main__":
    store = Store()
    items = generate_weekly_feedback(store)
    print(f"\nGenerated {len(items)} feedback items.")
    for item in items:
        print(f"\n### {item['title']}\n{item['body'][:200]}...")
