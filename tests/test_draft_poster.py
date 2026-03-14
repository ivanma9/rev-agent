# tests/test_draft_poster.py
"""Tests for draft_poster module."""
import pytest
from unittest.mock import patch, MagicMock
from src.store import Store
from src.tools.draft_poster import post_approved_drafts


def make_store():
    return Store(db_path=":memory:")


def seed_draft(store, platform="hn", url="https://news.ycombinator.com/item?id=123", status="approved"):
    store.save_draft(
        platform=platform,
        url=url,
        title="Test Post Title",
        body_snippet="Some context about RevenueCat",
        draft_response="Great question! RevenueCat handles this well. — Rev",
    )
    if status != "pending":
        draft = store.get_pending_drafts()[0]
        store.mark_draft(draft["id"], status)


class TestNoApprovedDrafts:
    def test_returns_empty_summary(self):
        store = make_store()
        result = post_approved_drafts(store)
        assert result["posted"] == 0
        assert result["dry_run"] == 0
        assert result["errors"] == 0

    def test_pending_drafts_not_posted(self):
        store = make_store()
        seed_draft(store, status="pending")
        result = post_approved_drafts(store)
        assert result["posted"] == 0
        assert result["dry_run"] == 0

    def test_rejected_drafts_not_posted(self):
        store = make_store()
        seed_draft(store, status="rejected")
        result = post_approved_drafts(store)
        assert result["posted"] == 0


class TestHNDryRun:
    def test_hn_prints_url_and_text(self, capsys):
        store = make_store()
        seed_draft(store, platform="hn", url="https://news.ycombinator.com/item?id=999")
        result = post_approved_drafts(store)
        captured = capsys.readouterr()
        assert "https://news.ycombinator.com/item?id=999" in captured.out
        assert "— Rev" in captured.out

    def test_hn_marked_as_posted(self):
        store = make_store()
        seed_draft(store, platform="hn", url="https://news.ycombinator.com/item?id=999")
        post_approved_drafts(store)
        rows = store.conn.execute(
            "SELECT status FROM drafts WHERE url='https://news.ycombinator.com/item?id=999'"
        ).fetchone()
        assert rows["status"] == "posted"

    def test_hn_dry_run_count(self):
        store = make_store()
        seed_draft(store, platform="hn", url="https://news.ycombinator.com/item?id=1")
        seed_draft(store, platform="hn", url="https://news.ycombinator.com/item?id=2")
        result = post_approved_drafts(store)
        assert result["dry_run"] == 2
        assert result["posted"] == 0


class TestSODryRun:
    def test_so_prints_url_and_text(self, capsys):
        store = make_store()
        seed_draft(store, platform="so", url="https://stackoverflow.com/questions/12345")
        result = post_approved_drafts(store)
        captured = capsys.readouterr()
        assert "https://stackoverflow.com/questions/12345" in captured.out
        assert "— Rev" in captured.out

    def test_so_marked_as_posted(self):
        store = make_store()
        seed_draft(store, platform="so", url="https://stackoverflow.com/questions/12345")
        post_approved_drafts(store)
        rows = store.conn.execute(
            "SELECT status FROM drafts WHERE url='https://stackoverflow.com/questions/12345'"
        ).fetchone()
        assert rows["status"] == "posted"

    def test_so_dry_run_count(self):
        store = make_store()
        seed_draft(store, platform="so", url="https://stackoverflow.com/questions/12345")
        result = post_approved_drafts(store)
        assert result["dry_run"] == 1
        assert result["posted"] == 0


class TestRedditDryRun:
    def test_reddit_dry_run_when_no_credentials(self, capsys):
        store = make_store()
        seed_draft(store, platform="reddit", url="https://reddit.com/r/SaaS/comments/abc123")
        with patch.dict("os.environ", {}, clear=False):
            # Ensure no reddit creds
            import os
            old = os.environ.pop("REDDIT_CLIENT_ID", None)
            old_secret = os.environ.pop("REDDIT_CLIENT_SECRET", None)
            old_ua = os.environ.pop("REDDIT_USER_AGENT", None)
            try:
                result = post_approved_drafts(store)
            finally:
                if old is not None:
                    os.environ["REDDIT_CLIENT_ID"] = old
                if old_secret is not None:
                    os.environ["REDDIT_CLIENT_SECRET"] = old_secret
                if old_ua is not None:
                    os.environ["REDDIT_USER_AGENT"] = old_ua
        captured = capsys.readouterr()
        assert "https://reddit.com/r/SaaS/comments/abc123" in captured.out
        assert result["dry_run"] == 1

    def test_reddit_dry_run_when_praw_unavailable(self, capsys):
        store = make_store()
        seed_draft(store, platform="reddit", url="https://reddit.com/r/SaaS/comments/xyz789")
        with patch("src.tools.draft_poster.praw", None):
            with patch.dict("os.environ", {
                "REDDIT_CLIENT_ID": "fakeid",
                "REDDIT_CLIENT_SECRET": "fakesecret",
                "REDDIT_USER_AGENT": "fakeagent",
            }):
                result = post_approved_drafts(store)
        captured = capsys.readouterr()
        assert "https://reddit.com/r/SaaS/comments/xyz789" in captured.out
        assert result["dry_run"] == 1

    def test_reddit_marked_as_posted_after_dry_run(self):
        store = make_store()
        seed_draft(store, platform="reddit", url="https://reddit.com/r/SaaS/comments/abc123")
        import os
        old = os.environ.pop("REDDIT_CLIENT_ID", None)
        try:
            post_approved_drafts(store)
        finally:
            if old is not None:
                os.environ["REDDIT_CLIENT_ID"] = old
        rows = store.conn.execute(
            "SELECT status FROM drafts WHERE url='https://reddit.com/r/SaaS/comments/abc123'"
        ).fetchone()
        assert rows["status"] == "posted"


class TestSummary:
    def test_summary_fields_present(self):
        store = make_store()
        result = post_approved_drafts(store)
        assert "posted" in result
        assert "dry_run" in result
        assert "errors" in result

    def test_mixed_platforms_summary(self):
        store = make_store()
        seed_draft(store, platform="hn", url="https://news.ycombinator.com/item?id=111")
        seed_draft(store, platform="so", url="https://stackoverflow.com/questions/111")
        import os
        old = os.environ.pop("REDDIT_CLIENT_ID", None)
        try:
            result = post_approved_drafts(store)
        finally:
            if old is not None:
                os.environ["REDDIT_CLIENT_ID"] = old
        assert result["dry_run"] == 2
        assert result["errors"] == 0
