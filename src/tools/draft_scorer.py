# src/tools/draft_scorer.py
"""Score, edit, and auto-post community draft responses using Claude Haiku."""
import logging
from anthropic import Anthropic

log = logging.getLogger(__name__)

SCORE_THRESHOLD = 7.0
MAX_RETRIES = 3

_PLATFORM_CONTEXT = {
    "hn": "Hacker News — concise, technical, genuine value, no marketing speak.",
    "so": "Stack Overflow — precise, code-focused, cite docs, direct answers.",
    "reddit": "Reddit — casual but helpful, practical experience, relatable tone.",
}

_SCORE_TOOL = {
    "name": "submit_score",
    "description": "Submit the quality score for a draft response.",
    "input_schema": {
        "type": "object",
        "properties": {
            "relevance": {
                "type": "integer",
                "description": "0-2: How relevant is this to RevenueCat/IAP/subscription billing?",
            },
            "helpfulness": {
                "type": "integer",
                "description": "0-2: Does this actually help the person asking?",
            },
            "authenticity": {
                "type": "integer",
                "description": "0-2: Does it sound human and non-promotional/non-spammy?",
            },
            "platform_fit": {
                "type": "integer",
                "description": "0-2: Is the tone appropriate for the platform?",
            },
            "specificity": {
                "type": "integer",
                "description": "0-2: Does it cite concrete details rather than generic advice?",
            },
        },
        "required": ["relevance", "helpfulness", "authenticity", "platform_fit", "specificity"],
    },
}


def score_draft(title: str, body: str, draft_response: str, platform: str) -> float:
    """Score a draft 0-10 using Claude Haiku. Returns 0.0 on failure."""
    try:
        client = Anthropic()
        platform_ctx = _PLATFORM_CONTEXT.get(platform, platform)
        system = (
            "You are a quality reviewer for Rev, an AI developer advocate for RevenueCat.\n"
            "Score the draft response on 5 criteria (0-2 each, max 10 total):\n"
            "  relevance: genuinely related to RevenueCat / IAP / subscription billing\n"
            "  helpfulness: actually helps the person asking\n"
            "  authenticity: sounds human, not spammy or promotional\n"
            "  platform_fit: appropriate tone for the platform\n"
            "  specificity: cites concrete details, not generic advice\n"
            f"Platform context: {platform_ctx}\n"
            "Use the submit_score tool to return your scores."
        )
        user_content = (
            f"Post title: {title}\n\n"
            f"Post body: {body[:500]}\n\n"
            f"Draft response to score:\n{draft_response}"
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=system,
            tools=[_SCORE_TOOL],
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": user_content}],
        )
        # Find the tool_use block
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_score":
                inp = block.input
                total = sum(
                    min(2, max(0, int(inp.get(k, 0))))
                    for k in ["relevance", "helpfulness", "authenticity", "platform_fit", "specificity"]
                )
                return float(total)
        return 0.0
    except Exception as e:
        log.warning(f"score_draft failed: {e}")
        return 0.0


def edit_draft(title: str, body: str, draft_response: str, platform: str, score: float) -> str:
    """Improve a draft response using Claude Haiku. Returns original on failure."""
    try:
        client = Anthropic()
        platform_ctx = _PLATFORM_CONTEXT.get(platform, platform)
        system = (
            f"You are Rev, an AI developer advocate for RevenueCat.\n"
            f"Platform: {platform_ctx}\n"
            f"The current draft scored {score}/10. Improve it to score at least 7/10.\n"
            "Scoring rubric: relevance (0-2), helpfulness (0-2), authenticity (0-2), "
            "platform_fit (0-2), specificity (0-2).\n"
            "Return ONLY the improved draft text, nothing else."
        )
        user_content = (
            f"Post title: {title}\n\n"
            f"Post body: {body[:500]}\n\n"
            f"Current draft (scored {score}/10):\n{draft_response}\n\n"
            "Write an improved version:"
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        for block in response.content:
            if block.type == "text":
                return block.text
        return draft_response
    except Exception as e:
        log.warning(f"edit_draft failed: {e}")
        return draft_response


def _get_platform_handlers():
    """Return platform handlers dict, imported lazily to avoid circular imports."""
    from src.tools.draft_poster import _PLATFORM_HANDLERS as _handlers
    return _handlers


# Module-level reference used in tests (can be patched)
_PLATFORM_HANDLERS = None  # resolved at call time via _get_platform_handlers()


def score_and_post_pipeline(draft: dict, store) -> dict:
    """
    Score, optionally edit, and post a draft.
    Returns {"action": "posted"|"discarded", "score": float, "attempts": int}
    """
    import src.tools.draft_scorer as _self
    handlers = _self._PLATFORM_HANDLERS if _self._PLATFORM_HANDLERS is not None else _get_platform_handlers()

    current_response = draft["draft_response"]
    last_score = 0.0

    for attempt in range(1, MAX_RETRIES + 1):
        score = score_draft(draft["title"], draft["body_snippet"], current_response, draft["platform"])
        last_score = score
        store.update_draft_score(draft["id"], score, attempt)

        if score >= SCORE_THRESHOLD:
            store.update_draft_response(draft["id"], current_response)
            store.mark_draft(draft["id"], "approved")

            handler = handlers.get(draft["platform"])
            if handler:
                try:
                    result = handler(draft, store)
                    # Support 2-tuple (posted, dry_run) for now
                    if isinstance(result, tuple) and len(result) >= 3:
                        posted, dry_run, post_url = result[0], result[1], result[2]
                        if post_url:
                            store.record_post_url(draft["id"], post_url)
                    # 2-tuple
                except Exception as e:
                    log.error(f"Post handler failed for draft id={draft['id']}: {e}")
                    store.log_error("draft_scorer", f"Post handler failed for draft id={draft['id']}: {e}")

            store.mark_draft(draft["id"], "posted")
            return {"action": "posted", "score": score, "attempts": attempt}

        if attempt < MAX_RETRIES:
            current_response = edit_draft(
                draft["title"], draft["body_snippet"], current_response, draft["platform"], score
            )
            store.update_draft_response(draft["id"], current_response)

    store.mark_draft(draft["id"], "discarded")
    return {"action": "discarded", "score": last_score, "attempts": MAX_RETRIES}
