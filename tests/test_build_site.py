# tests/test_build_site.py
import os
os.environ["REV_DB_PATH"] = ":memory:"


def test_parse_frontmatter():
    from src.tools.build_site import parse_frontmatter
    text = '''---
title: "Test Post"
date: 2026-03-09
type: blog
author: Rev
---

# Hello World

Body here.'''
    meta, body = parse_frontmatter(text)
    assert meta["title"] == "Test Post"
    assert meta["date"] == "2026-03-09"
    assert meta["type"] == "blog"
    assert "# Hello World" in body
    assert "---" not in body


def test_render_post_html():
    from src.tools.build_site import render_post_html
    html = render_post_html(
        title="Test Post",
        date="2026-03-09",
        content_type="blog",
        body_html="<p>Hello world</p>"
    )
    assert "Test Post" in html
    assert "2026-03-09" in html
    assert "<p>Hello world</p>" in html
    assert "style.css" in html or "style" in html
    assert "</html>" in html


def test_render_dashboard_html():
    from src.tools.build_site import render_dashboard_html
    html = render_dashboard_html(
        published_count=5,
        interaction_count=32,
        feedback_count=2,
        recent_posts=[
            {"title": "Post One", "date": "2026-03-09", "type": "blog", "slug": "post-one"},
            {"title": "Post Two", "date": "2026-03-08", "type": "tutorial", "slug": "post-two"},
        ]
    )
    assert "5" in html  # published count
    assert "32" in html  # interactions
    assert "Post One" in html
    assert "Post Two" in html
    assert "blog/post-one.html" in html
    assert "</html>" in html


def test_render_dashboard_empty():
    from src.tools.build_site import render_dashboard_html
    html = render_dashboard_html(
        published_count=0,
        interaction_count=0,
        feedback_count=0,
        recent_posts=[]
    )
    assert "0" in html
    assert "No posts yet" in html or "</html>" in html


def test_render_blog_index():
    from src.tools.build_site import render_blog_index
    posts = [
        {"title": "Post One", "date": "2026-03-09", "type": "blog", "slug": "post-one", "preview": "First post preview text"},
        {"title": "Post Two", "date": "2026-03-08", "type": "tutorial", "slug": "post-two", "preview": "Second post preview"},
    ]
    html = render_blog_index(posts)
    assert "Post One" in html
    assert "Post Two" in html
    assert "blog" in html.lower()
    assert "post-one.html" in html
    assert "</html>" in html


def test_build_full_site(tmp_path):
    from src.tools.build_site import build_full_site
    from src.store import Store

    store = Store(":memory:")
    # Seed some published content
    store.queue_content("Test Post", "blog", "# Hello\n\nWorld")
    items = store.get_pending_content()
    store.mark_published(items[0]["id"], url="https://example.com")
    store.log_interaction("github", "https://github.com/test", "test interaction")

    # Create a fake content file
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "2026-03-09-test-post.md").write_text('''---
title: "Test Post"
date: 2026-03-09
type: blog
author: Rev
---

# Hello

World''')

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "style.css").write_text("/* test */")

    build_full_site(store=store, content_dir=content_dir, docs_dir=docs_dir)

    assert (docs_dir / "index.html").exists()
    assert (docs_dir / "blog" / "index.html").exists()
    assert (docs_dir / "blog" / "test-post.html").exists()
    assert (docs_dir / "feed.xml").exists()

    # Verify dashboard has KPI data
    dashboard = (docs_dir / "index.html").read_text()
    assert "1" in dashboard  # 1 published


def test_render_rss_feed():
    from src.tools.build_site import render_rss_feed
    posts = [
        {"title": "Post One", "date": "2026-03-09", "type": "blog", "slug": "post-one", "preview": "Preview text"},
    ]
    xml = render_rss_feed(posts)
    assert "<?xml" in xml
    assert "<rss" in xml
    assert "Post One" in xml
    assert "<link>" in xml
