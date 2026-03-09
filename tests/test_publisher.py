# tests/test_publisher.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_slug_generation():
    from src.tools.publisher import title_to_slug
    slug = title_to_slug("How to Build a RevenueCat Agent")
    assert slug == "how-to-build-a-revenuecat-agent"
    assert " " not in slug

def test_format_for_github():
    from src.tools.publisher import format_for_github
    content = format_for_github(
        title="Test Post",
        body="# Hello\n\nWorld",
        content_type="blog"
    )
    assert "Test Post" in content
    assert "rev_agent" in content.lower() or "rev" in content.lower()

def test_publish_pending_cross_posts_to_x():
    from unittest.mock import patch, MagicMock
    from src.store import Store
    from src.tools.publisher import publish_pending

    store = Store(":memory:")
    store.queue_content("How to use webhooks", "blog", "# Body\n\nContent here.")

    mock_repo = MagicMock()
    mock_repo.get_contents.side_effect = Exception("not found")
    mock_repo.create_file.return_value = {}

    with patch("src.tools.publisher.Github") as mock_github, \
         patch("src.tools.publisher.post_tweet") as mock_post:
        mock_github.return_value.get_repo.return_value = mock_repo
        mock_post.return_value = {"posted": True, "dry_run": True, "tweet_count": 1}

        results = publish_pending(store=store, limit=1, x_dry_run=True)

        assert len(results) == 1
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs.get("dry_run") is True
        assert call_kwargs.kwargs.get("store") is store
