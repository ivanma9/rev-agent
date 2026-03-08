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
