# tests/test_content_generator.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_generate_blog_post_dry_run():
    from src.tools.content_generator import generate_content
    result = generate_content(
        topic="How to use RevenueCat webhooks with AI agents",
        content_type="blog",
        dry_run=True
    )
    assert isinstance(result, str)
    assert len(result) > 50

def test_content_types():
    from src.tools.content_generator import CONTENT_TYPES
    assert "blog" in CONTENT_TYPES
    assert "tutorial" in CONTENT_TYPES
    assert "code_sample" in CONTENT_TYPES
