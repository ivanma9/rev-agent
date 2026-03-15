# tests/test_draft_scorer.py
"""Tests for draft_scorer — score_draft, edit_draft, score_and_post_pipeline."""
import pytest
from unittest.mock import MagicMock, patch


# ── Task 2: score_draft ───────────────────────────────────────────────────────

def _make_tool_use_response(relevance=2, helpfulness=2, authenticity=2,
                             platform_fit=2, specificity=2):
    """Build a mock Anthropic response with tool_use block."""
    tool_use = MagicMock()
    tool_use.type = "tool_use"
    tool_use.name = "submit_score"
    tool_use.input = {
        "relevance": relevance,
        "helpfulness": helpfulness,
        "authenticity": authenticity,
        "platform_fit": platform_fit,
        "specificity": specificity,
    }
    resp = MagicMock()
    resp.content = [tool_use]
    return resp


def test_score_draft_perfect_score():
    from src.tools.draft_scorer import score_draft
    with patch("src.tools.draft_scorer.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _make_tool_use_response()
        score = score_draft("Title", "Body", "Draft response", "hn")
    assert score == 10.0


def test_score_draft_partial_score():
    from src.tools.draft_scorer import score_draft
    with patch("src.tools.draft_scorer.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _make_tool_use_response(
            relevance=1, helpfulness=2, authenticity=1, platform_fit=2, specificity=1
        )
        score = score_draft("Title", "Body", "Draft", "so")
    assert score == 7.0


def test_score_draft_clamps_over_range():
    """Values > 2 should be clamped to 2."""
    from src.tools.draft_scorer import score_draft
    with patch("src.tools.draft_scorer.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _make_tool_use_response(
            relevance=5, helpfulness=5, authenticity=5, platform_fit=5, specificity=5
        )
        score = score_draft("Title", "Body", "Draft", "reddit")
    assert score == 10.0


def test_score_draft_returns_zero_on_exception():
    from src.tools.draft_scorer import score_draft
    with patch("src.tools.draft_scorer.Anthropic") as MockClient:
        MockClient.return_value.messages.create.side_effect = Exception("API error")
        score = score_draft("Title", "Body", "Draft", "hn")
    assert score == 0.0


def test_score_draft_returns_zero_on_missing_tool_use():
    """If response has no tool_use block, return 0.0."""
    from src.tools.draft_scorer import score_draft
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "some text"
    resp = MagicMock()
    resp.content = [text_block]
    with patch("src.tools.draft_scorer.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = resp
        score = score_draft("Title", "Body", "Draft", "hn")
    assert score == 0.0


# ── Task 3: edit_draft ────────────────────────────────────────────────────────

def test_edit_draft_returns_string():
    from src.tools.draft_scorer import edit_draft
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "Improved draft response."
    resp = MagicMock()
    resp.content = [text_block]
    with patch("src.tools.draft_scorer.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = resp
        result = edit_draft("Title", "Body", "Original draft", "hn", 5.0)
    assert result == "Improved draft response."


def test_edit_draft_returns_original_on_exception():
    from src.tools.draft_scorer import edit_draft
    with patch("src.tools.draft_scorer.Anthropic") as MockClient:
        MockClient.return_value.messages.create.side_effect = Exception("API error")
        result = edit_draft("Title", "Body", "Original draft", "hn", 5.0)
    assert result == "Original draft"


def test_edit_draft_uses_score_context():
    """Ensure score is included somewhere in the prompt."""
    from src.tools.draft_scorer import edit_draft
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "Better draft."
    resp = MagicMock()
    resp.content = [text_block]
    call_messages = []
    def capture_create(**kwargs):
        call_messages.append(kwargs)
        return resp
    with patch("src.tools.draft_scorer.Anthropic") as MockClient:
        MockClient.return_value.messages.create.side_effect = capture_create
        edit_draft("Title", "Body", "Draft", "reddit", 4.5)
    # The score should appear somewhere in system or messages
    all_text = str(call_messages)
    assert "4.5" in all_text


# ── Task 4: score_and_post_pipeline ──────────────────────────────────────────

def _make_draft(draft_id=1, platform="hn", score=None):
    return {
        "id": draft_id,
        "platform": platform,
        "url": "https://hn.com/item?id=1",
        "title": "Test Post",
        "body_snippet": "How do I handle subscriptions?",
        "draft_response": "You can use RevenueCat.",
    }


def test_pipeline_posts_on_high_score():
    """Draft with score >= 7 on first attempt should be posted."""
    from src.tools.draft_scorer import score_and_post_pipeline
    store = MagicMock()
    draft = _make_draft()

    handler = MagicMock(return_value=(True, False))
    with patch("src.tools.draft_scorer.score_draft", return_value=8.0), \
         patch("src.tools.draft_scorer._PLATFORM_HANDLERS", {"hn": handler}):
        result = score_and_post_pipeline(draft, store)

    assert result["action"] == "posted"
    assert result["score"] == 8.0
    assert result["attempts"] == 1
    store.mark_draft.assert_any_call(draft["id"], "approved")
    store.mark_draft.assert_any_call(draft["id"], "posted")


def test_pipeline_discards_after_max_retries():
    """Draft that never scores >= 7 should be discarded after MAX_RETRIES."""
    from src.tools.draft_scorer import score_and_post_pipeline, MAX_RETRIES
    store = MagicMock()
    draft = _make_draft()

    with patch("src.tools.draft_scorer.score_draft", return_value=5.0), \
         patch("src.tools.draft_scorer.edit_draft", return_value="edited draft"), \
         patch("src.tools.draft_scorer._PLATFORM_HANDLERS", {}):
        result = score_and_post_pipeline(draft, store)

    assert result["action"] == "discarded"
    assert result["attempts"] == MAX_RETRIES
    store.mark_draft.assert_called_with(draft["id"], "discarded")


def test_pipeline_posts_on_second_attempt():
    """Draft that fails first score but passes after edit should be posted on attempt 2."""
    from src.tools.draft_scorer import score_and_post_pipeline
    store = MagicMock()
    draft = _make_draft(platform="reddit")

    scores = iter([5.0, 8.0])
    handler = MagicMock(return_value=(True, False))

    with patch("src.tools.draft_scorer.score_draft", side_effect=scores), \
         patch("src.tools.draft_scorer.edit_draft", return_value="improved"), \
         patch("src.tools.draft_scorer._PLATFORM_HANDLERS", {"reddit": handler}):
        result = score_and_post_pipeline(draft, store)

    assert result["action"] == "posted"
    assert result["score"] == 8.0
    assert result["attempts"] == 2


def test_pipeline_updates_score_on_each_attempt():
    """store.update_draft_score should be called for each attempt."""
    from src.tools.draft_scorer import score_and_post_pipeline
    store = MagicMock()
    draft = _make_draft()

    with patch("src.tools.draft_scorer.score_draft", return_value=3.0), \
         patch("src.tools.draft_scorer.edit_draft", return_value="edited"), \
         patch("src.tools.draft_scorer._PLATFORM_HANDLERS", {}):
        score_and_post_pipeline(draft, store)

    assert store.update_draft_score.call_count == 3
