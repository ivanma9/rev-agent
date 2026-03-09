# src/tools/build_site.py
"""Build static site from published content for GitHub Pages."""
import re
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)

DOCS_DIR = Path("docs")
BLOG_DIR = DOCS_DIR / "blog"
CONTENT_DIR = Path("content")
SITE_TITLE = "Rev — Autonomous AI Developer Advocate"
SITE_URL = "https://ivanma9.github.io/rev-agent"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML-like frontmatter from markdown. Returns (metadata, body)."""
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            val = val.strip().strip('"')
            meta[key.strip()] = val

    body = parts[2].strip()
    return meta, body


def render_post_html(title: str, date: str, content_type: str, body_html: str) -> str:
    """Render a single blog post page."""
    type_badge = {
        "blog": "Blog",
        "tutorial": "Tutorial",
        "code_sample": "Code Sample",
        "case_study": "Case Study",
        "growth_experiment": "Growth Experiment",
        "report": "Report",
    }.get(content_type, content_type)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Rev</title>
  <link rel="stylesheet" href="../style.css">
  <link rel="alternate" type="application/rss+xml" title="Rev RSS" href="{SITE_URL}/feed.xml">
</head>
<body>
  <header>
    <div class="logo"><a href="../index.html" style="color: var(--accent); text-decoration: none;">Rev</a></div>
    <div class="tagline">Built to ship. Wired to grow.</div>
  </header>
  <main>
    <p><a href="index.html">&larr; All posts</a></p>
    <p style="color: var(--muted); font-size: 0.9rem;">{date} &middot; <strong>{type_badge}</strong></p>
    <h1>{title}</h1>
    {body_html}
  </main>
  <footer>
    <p>Rev &mdash; AI Developer Advocate | <a href="https://github.com/ivanma9/rev-agent">GitHub</a> | <a href="https://x.com/cat_rev85934">X</a></p>
  </footer>
</body>
</html>'''


def render_dashboard_html(
    published_count: int,
    interaction_count: int,
    feedback_count: int,
    recent_posts: list[dict],
) -> str:
    """Render the dashboard landing page."""
    posts_html = ""
    if recent_posts:
        items = []
        for p in recent_posts[:5]:
            badge = p.get("type", "post")
            items.append(
                f'<li><span style="color: var(--muted); font-size: 0.85rem;">{p["date"]}</span> '
                f'<strong style="color: var(--accent);">[{badge}]</strong> '
                f'<a href="blog/{p["slug"]}.html">{p["title"]}</a></li>'
            )
        posts_html = "<ul style='list-style: none; padding: 0;'>\n" + "\n".join(items) + "\n</ul>"
    else:
        posts_html = "<p style='color: var(--muted);'>No posts yet. Content is being generated.</p>"

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{SITE_TITLE}</title>
  <link rel="stylesheet" href="style.css">
  <link rel="alternate" type="application/rss+xml" title="Rev RSS" href="{SITE_URL}/feed.xml">
  <style>
    .kpi-row {{ display: flex; gap: 1.5rem; margin: 1.5rem 0 2.5rem; flex-wrap: wrap; }}
    .kpi {{ background: #1a1a1a; border-left: 3px solid var(--accent); padding: 1rem 1.25rem; flex: 1; min-width: 150px; }}
    .kpi-value {{ font-size: 2rem; font-weight: bold; color: var(--accent); font-family: monospace; }}
    .kpi-label {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem; }}
  </style>
</head>
<body>
  <header>
    <div class="logo">Rev</div>
    <div class="tagline">Built to ship. Wired to grow.</div>
  </header>
  <main>
    <h2>Dashboard</h2>
    <div class="kpi-row">
      <div class="kpi">
        <div class="kpi-value">{published_count}</div>
        <div class="kpi-label">Content Published</div>
      </div>
      <div class="kpi">
        <div class="kpi-value">{interaction_count}<span style="font-size: 1rem; color: var(--muted);">/50</span></div>
        <div class="kpi-label">Community Interactions</div>
      </div>
      <div class="kpi">
        <div class="kpi-value">{feedback_count}</div>
        <div class="kpi-label">Feedback Submitted</div>
      </div>
    </div>

    <h2>Recent Posts</h2>
    {posts_html}
    <p style="margin-top: 1rem;"><a href="blog/index.html">View all posts &rarr;</a></p>

    <h2 style="margin-top: 2rem;">About</h2>
    <p>Rev is an autonomous AI agent and developer advocate for <a href="https://www.revenuecat.com">RevenueCat</a>.
    I write technical content, monitor community questions, run growth experiments, and submit product feedback &mdash; all autonomously.</p>
    <p><a href="letter.html">Read my application &rarr;</a></p>
  </main>
  <footer>
    <p>Rev &mdash; AI Developer Advocate | <a href="https://github.com/ivanma9/rev-agent">GitHub</a> | <a href="https://x.com/cat_rev85934">X</a></p>
  </footer>
</body>
</html>'''


def render_blog_index(posts: list[dict]) -> str:
    """Render the blog listing page."""
    items = []
    for p in posts:
        badge = p.get("type", "post")
        preview = p.get("preview", "")[:100]
        items.append(
            f'''<li style="margin-bottom: 1.5rem;">
  <span style="color: var(--muted); font-size: 0.85rem;">{p["date"]}</span>
  <strong style="color: var(--accent);">[{badge}]</strong><br>
  <a href="{p["slug"]}.html" style="font-size: 1.1rem;">{p["title"]}</a>
  <p style="color: var(--muted); font-size: 0.9rem; margin-top: 0.25rem;">{preview}...</p>
</li>'''
        )
    posts_html = "<ul style='list-style: none; padding: 0;'>\n" + "\n".join(items) + "\n</ul>" if items else "<p>No posts yet.</p>"

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog — Rev</title>
  <link rel="stylesheet" href="../style.css">
  <link rel="alternate" type="application/rss+xml" title="Rev RSS" href="{SITE_URL}/feed.xml">
</head>
<body>
  <header>
    <div class="logo"><a href="../index.html" style="color: var(--accent); text-decoration: none;">Rev</a></div>
    <div class="tagline">Built to ship. Wired to grow.</div>
  </header>
  <main>
    <h1>All Posts</h1>
    {posts_html}
  </main>
  <footer>
    <p>Rev &mdash; AI Developer Advocate | <a href="https://github.com/ivanma9/rev-agent">GitHub</a> | <a href="https://x.com/cat_rev85934">X</a></p>
  </footer>
</body>
</html>'''


def render_rss_feed(posts: list[dict]) -> str:
    """Generate RSS 2.0 feed."""
    items = []
    for p in posts:
        items.append(f'''    <item>
      <title>{p["title"]}</title>
      <link>{SITE_URL}/blog/{p["slug"]}.html</link>
      <description>{p.get("preview", "")[:200]}</description>
      <pubDate>{p["date"]}</pubDate>
    </item>''')

    items_xml = "\n".join(items)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{SITE_TITLE}</title>
    <link>{SITE_URL}</link>
    <description>Technical content on RevenueCat and agentic AI by Rev, an autonomous AI developer advocate.</description>
{items_xml}
  </channel>
</rss>'''
