# src/tools/publisher.py
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os
from github import Github
from src.store import Store

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = "ivanma9/rev-agent"
CONTENT_DIR = "content"

def title_to_slug(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug.strip())
    return slug[:60]

def format_for_github(title: str, body: str, content_type: str) -> str:
    date = datetime.now().strftime("%Y-%m-%d")
    header = f"""---
title: "{title}"
date: {date}
type: {content_type}
author: Rev
---

"""
    footer = f"\n\n---\n*Published by Rev | [@rev_agent](https://x.com/rev_agent) | [GitHub](https://github.com/ivanma9/rev-agent)*"
    return header + body + footer

def publish_to_github(title: str, body: str, content_type: str) -> str:
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)

    date = datetime.now().strftime("%Y-%m-%d")
    slug = title_to_slug(title)
    filename = f"{CONTENT_DIR}/{date}-{slug}.md"
    formatted = format_for_github(title, body, content_type)

    try:
        existing = repo.get_contents(filename)
        repo.update_file(filename, f"content: update {slug}", formatted, existing.sha)
    except Exception:
        repo.create_file(filename, f"content: publish {slug}", formatted)

    url = f"https://github.com/{GITHUB_REPO}/blob/main/{filename}"
    print(f"✓ Published: {url}")
    return url

def publish_pending(store: Store = None, limit: int = 2) -> list[dict]:
    if store is None:
        store = Store()

    pending = [p for p in store.get_pending_content() if p["content_type"] != "idea"][:limit]
    published = []

    for item in pending:
        try:
            url = publish_to_github(item["title"], item["body"], item["content_type"])
            store.mark_published(item["id"], url=url)
            published.append({"title": item["title"], "url": url})
        except Exception as e:
            print(f"✗ Failed to publish '{item['title']}': {e}")

    return published

if __name__ == "__main__":
    store = Store()
    results = publish_pending(store)
    print(f"\nPublished {len(results)} pieces.")
    for r in results:
        print(f"  - {r['title'][:60]}: {r['url']}")
