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
