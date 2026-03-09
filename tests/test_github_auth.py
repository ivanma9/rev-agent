# tests/test_github_auth.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

from unittest.mock import patch, MagicMock


def test_community_monitor_uses_auth_token():
    """Verify scan_github_issues builds Github with Auth.Token, not login_or_token."""
    from github import Auth
    with patch("src.tools.community_monitor.Github") as mock_github:
        mock_repo = MagicMock()
        mock_repo.get_issues.return_value = []
        mock_github.return_value.get_repo.return_value = mock_repo

        from src.tools.community_monitor import scan_github_issues
        from src.store import Store
        scan_github_issues(store=Store(":memory:"), post_comments=False)

        call_kwargs = mock_github.call_args
        # Should be called with auth= keyword, not positional token string
        assert call_kwargs is not None
        assert "auth" in call_kwargs.kwargs, f"Github called without auth= kwarg: {call_kwargs}"
        assert isinstance(call_kwargs.kwargs["auth"], Auth.Token)


def test_publisher_uses_auth_token():
    """Verify publish_to_github builds Github with Auth.Token, not login_or_token."""
    from github import Auth
    mock_repo = MagicMock()
    mock_repo.get_contents.side_effect = Exception("not found")
    mock_repo.create_file.return_value = {}

    with patch("src.tools.publisher.Github") as mock_github:
        mock_github.return_value.get_repo.return_value = mock_repo

        from src.tools.publisher import publish_to_github
        publish_to_github("Test Title", "# Body", "blog")

        call_kwargs = mock_github.call_args
        assert call_kwargs is not None
        assert "auth" in call_kwargs.kwargs, f"Github called without auth= kwarg: {call_kwargs}"
        assert isinstance(call_kwargs.kwargs["auth"], Auth.Token)
