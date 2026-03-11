# src/tools/content_generator.py
from anthropic import Anthropic
from pathlib import Path
from src.store import Store
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

CONTENT_TYPES = ["blog", "tutorial", "code_sample", "case_study", "growth_experiment"]

SYSTEM_PROMPT = """You are Rev, an autonomous AI agent and developer advocate for RevenueCat.
Write technical content that is:
- Developer-first: concrete, practical, with real code
- Opinionated: strong takes, not wishy-washy
- Agentic-AI focused: always connect to the agent developer use case
- RevenueCat-specific: reference real APIs, SDKs, endpoints

Voice: senior dev advocate who ships things. No fluff, no corporate speak."""

TEMPLATES = {
    "blog": """Write a technical blog post (600-900 words) about: {topic}

Structure:
# [Compelling title]
## The Problem
## The Solution (with RevenueCat)
## Code Example
```python
# Real working code using RevenueCat API
```
## Key Takeaways

Sign off as: Rev | @rev_agent""",

    "tutorial": """Write a step-by-step tutorial (800-1200 words) about: {topic}

Structure:
# [Title: How to X with RevenueCat]
## Prerequisites
## Step 1: ...
## Step 2: ...
(include working code at each step)
## What's Next

Sign off as: Rev | @rev_agent""",

    "code_sample": """Write a focused code sample with explanation for: {topic}

Include:
- A complete, runnable Python script using RevenueCat's REST API
- Brief explanation of what it does and why
- Usage instructions

Sign off as: Rev | @rev_agent""",

    "case_study": """Write a growth-focused case study (500-700 words) about: {topic}

Structure:
# [Title]
## The Setup
## The Experiment
## Results & Learnings
## How to Replicate This

Sign off as: Rev | @rev_agent""",

    "growth_experiment": """Design a growth experiment brief (300-500 words) for: {topic}

Structure:
# Experiment: [Name]
## Hypothesis
## Method
## Success Metrics
## RevenueCat Integration Points
## Timeline

Sign off as: Rev | @rev_agent""",
}

CONTENT_TOOL = {
    "name": "publish_content",
    "description": "Submit the generated content with structured metadata.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Clean, compelling title for the content piece. No markdown. No '#' prefix."
            },
            "body": {
                "type": "string",
                "description": "The full content body in markdown format. Do NOT include the title as a heading — it will be added automatically."
            },
        },
        "required": ["title", "body"],
    },
}


def generate_content(topic: str, content_type: str = "blog", dry_run: bool = False) -> dict:
    """Generate content and return structured {title, body} dict."""
    if dry_run:
        return {"title": f"Dry Run: {content_type}", "body": f"Would generate {content_type} about: {topic}"}

    template = TEMPLATES.get(content_type, TEMPLATES["blog"])
    prompt = template.format(topic=topic)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        tools=[CONTENT_TOOL],
        tool_choice={"type": "tool", "name": "publish_content"},
        messages=[{"role": "user", "content": prompt}]
    )

    # Extract structured tool call result
    for block in response.content:
        if block.type == "tool_use" and block.name == "publish_content":
            return {"title": block.input["title"], "body": block.input["body"]}

    # Fallback: shouldn't happen with tool_choice forced
    text = response.content[0].text if response.content else ""
    return {"title": topic[:80], "body": text}

def generate_weekly_content(store: Store = None) -> list[dict]:
    """Generate 2 pieces of content for the week based on queue + trending topics."""
    if store is None:
        store = Store()

    DEFAULT_TOPICS = [
        ("How AI agents can use RevenueCat webhooks to trigger automated responses", "tutorial"),
        ("Building a subscription-aware agent with RevenueCat's CustomerInfo API", "code_sample"),
        ("RevenueCat Experiments API: letting your agent run A/B tests autonomously", "blog"),
        ("Using RevenueCat Charts API to give your agent revenue awareness", "tutorial"),
        ("How to build a paywall decision engine with RevenueCat Targeting", "blog"),
        ("RevenueCat + LangGraph: building a subscription management agent", "code_sample"),
        ("Growth experiment: programmatic SEO for agent developer tools", "growth_experiment"),
        ("Case study: what happens when an AI agent manages its own RevenueCat offerings", "case_study"),
    ]

    # Check queue for ideas first
    pending = store.get_pending_content()
    ideas = [(p["body"][:100], "blog") for p in pending if p["content_type"] == "idea"]

    topics_to_use = (ideas + DEFAULT_TOPICS)[:2]
    results = []

    for topic, content_type in topics_to_use:
        print(f"Generating {content_type}: {topic[:60]}...")
        result = generate_content(topic, content_type)
        title = result["title"]
        body = result["body"]
        store.queue_content(title=title, content_type=content_type, body=body)
        results.append({"topic": topic, "title": title, "content_type": content_type, "chars": len(body)})
        print(f"  ✓ Generated: {title} ({len(body)} chars)")

    return results

if __name__ == "__main__":
    store = Store()
    results = generate_weekly_content(store)
    print(f"\nGenerated {len(results)} pieces of content.")
    for r in results:
        print(f"  - [{r['content_type']}] {r['topic'][:60]}... ({r['chars']} chars)")
