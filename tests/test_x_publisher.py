# tests/test_x_publisher.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

from unittest.mock import MagicMock, patch


def test_split_into_thread_short():
    from src.tools.x_publisher import split_into_thread
    tweets = split_into_thread("Short tweet under 280 chars.")
    assert len(tweets) == 1
    assert tweets[0] == "Short tweet under 280 chars."


def test_split_into_thread_long():
    from src.tools.x_publisher import split_into_thread
    long_text = "A" * 300
    tweets = split_into_thread(long_text)
    assert len(tweets) > 1
    for t in tweets:
        assert len(t) <= 280


def test_split_into_thread_numbered():
    from src.tools.x_publisher import split_into_thread
    long_text = ("Word " * 60).strip()  # ~300 chars
    tweets = split_into_thread(long_text)
    if len(tweets) > 1:
        assert tweets[0].endswith("(1/2)") or "1/" in tweets[0]


def test_post_tweet_dry_run():
    from src.tools.x_publisher import post_tweet
    result = post_tweet("Hello from Rev!", dry_run=True)
    assert result["posted"] is True
    assert result["dry_run"] is True
    assert result["tweet_count"] == 1


def test_post_thread_dry_run():
    from src.tools.x_publisher import post_tweet
    long_text = ("Word " * 60).strip()
    result = post_tweet(long_text, dry_run=True)
    assert result["posted"] is True
    assert result["tweet_count"] >= 1


def test_post_tweet_logs_interaction():
    from src.tools.x_publisher import post_tweet
    from src.store import Store
    store = Store(":memory:")
    post_tweet("Test tweet", dry_run=True, store=store)
    assert store.interaction_count_this_week() == 1


def test_format_content_tweet():
    from src.tools.x_publisher import format_content_tweet
    text = format_content_tweet(
        title="How to use RevenueCat webhooks",
        url="https://github.com/ivanma9/rev-agent/blob/main/content/post.md",
        content_type="blog"
    )
    assert "RevenueCat" in text or "rev" in text.lower()
    assert "https://" in text
    assert len(text) <= 280
