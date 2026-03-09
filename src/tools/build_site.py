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
