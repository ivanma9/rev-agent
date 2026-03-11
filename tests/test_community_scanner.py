# tests/test_community_scanner.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

from unittest.mock import patch, MagicMock
import json


def test_search_terms_exist():
    from src.tools.community_scanner import SEARCH_TERMS
    assert "revenuecat" in SEARCH_TERMS
    assert any("agent" in t for t in SEARCH_TERMS)


def test_scan_hn_parses_results():
    from src.tools.community_scanner import scan_hn
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "hits": [
            {
                "objectID": "123",
                "title": "Using RevenueCat with AI agents",
                "author": "dev123",
                "points": 42,
                "num_comments": 5,
                "created_at_i": 1710000000,
            }
        ]
    }
    fake_response.status_code = 200

    with patch("src.tools.community_scanner.requests.get", return_value=fake_response):
        results = scan_hn()
    assert len(results) == 1
    assert results[0]["platform"] == "hn"
    assert "revenuecat" in results[0]["title"].lower() or "RevenueCat" in results[0]["title"]
    assert "news.ycombinator.com" in results[0]["url"]


def test_scan_so_parses_results():
    from src.tools.community_scanner import scan_so
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "items": [
            {
                "question_id": 456,
                "title": "RevenueCat webhook with AI agent",
                "link": "https://stackoverflow.com/q/456",
                "score": 3,
                "answer_count": 0,
                "body": "How do I set up webhooks?",
            }
        ]
    }
    fake_response.status_code = 200

    with patch("src.tools.community_scanner.requests.get", return_value=fake_response):
        results = scan_so()
    assert len(results) == 1
    assert results[0]["platform"] == "so"
    assert "stackoverflow.com" in results[0]["url"]


def test_scan_reddit_skips_without_credentials():
    from src.tools.community_scanner import scan_reddit
    with patch.dict(os.environ, {}, clear=True):
        results = scan_reddit()
    assert results == []


def test_scan_reddit_parses_results():
    from src.tools.community_scanner import scan_reddit
    mock_submission = MagicMock()
    mock_submission.id = "abc123"
    mock_submission.title = "Best subscription SDK for AI agents?"
    mock_submission.selftext = "Looking for something to handle billing..."
    mock_submission.score = 15
    mock_submission.url = "https://reddit.com/r/SaaS/comments/abc123"
    mock_submission.permalink = "/r/SaaS/comments/abc123/best_subscription_sdk"
    mock_submission.num_comments = 3

    mock_subreddit = MagicMock()
    mock_subreddit.search.return_value = [mock_submission]

    mock_reddit = MagicMock()
    mock_reddit.subreddit.return_value = mock_subreddit

    mock_praw = MagicMock()
    mock_praw.Reddit.return_value = mock_reddit

    with patch.dict(os.environ, {"REDDIT_CLIENT_ID": "fake", "REDDIT_CLIENT_SECRET": "fake", "REDDIT_USER_AGENT": "fake"}):
        with patch("src.tools.community_scanner.praw", mock_praw):
            results = scan_reddit()

    assert len(results) >= 1
    assert results[0]["platform"] == "reddit"


def test_scan_hn_handles_api_error():
    from src.tools.community_scanner import scan_hn
    fake_response = MagicMock()
    fake_response.status_code = 500
    fake_response.raise_for_status.side_effect = Exception("Server error")

    with patch("src.tools.community_scanner.requests.get", return_value=fake_response):
        results = scan_hn()
    assert results == []


def test_review_drafts_approve(monkeypatch):
    from src.tools.community_scanner import review_drafts
    from src.store import Store

    store = Store(":memory:")
    store.save_draft("hn", "https://hn.com/1", "Test Post", "snippet", "My draft response")

    inputs = iter(["y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    reviewed = review_drafts(store=store)
    assert reviewed == 1
    assert len(store.get_pending_drafts()) == 0


def test_review_drafts_reject(monkeypatch):
    from src.tools.community_scanner import review_drafts
    from src.store import Store

    store = Store(":memory:")
    store.save_draft("hn", "https://hn.com/1", "Test Post", "snippet", "My draft response")

    inputs = iter(["n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    reviewed = review_drafts(store=store)
    assert reviewed == 1
    assert len(store.get_pending_drafts()) == 0


def test_review_drafts_skip(monkeypatch):
    from src.tools.community_scanner import review_drafts
    from src.store import Store

    store = Store(":memory:")
    store.save_draft("hn", "https://hn.com/1", "Test Post", "snippet", "My draft response")

    inputs = iter(["s"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    reviewed = review_drafts(store=store)
    assert reviewed == 0
    assert len(store.get_pending_drafts()) == 1
