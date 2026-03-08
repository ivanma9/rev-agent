# src/tools/knowledge_sync.py
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from src.tools.ingest import fetch_page, extract_text, DOCS_URLS
from src.store import Store
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

ADDITIONAL_URLS = [
    "https://www.revenuecat.com/blog/",
    "https://github.com/RevenueCat/purchases-ios/releases",
    "https://github.com/RevenueCat/purchases-android/releases",
    "https://github.com/RevenueCat/react-native-purchases/releases",
]

ALL_URLS = DOCS_URLS + ADDITIONAL_URLS

def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]

def detect_change(source: str, new_hash: str, previous_hashes: dict) -> bool:
    return previous_hashes.get(source) != new_hash

def generate_content_idea(source: str, old_text: str, new_text: str) -> str:
    """Ask Claude what changed and suggest content ideas."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""You are Rev, an AI developer advocate for RevenueCat.
A documentation page changed: {source}

Briefly describe what likely changed and suggest ONE content idea that would be valuable
to agent developers based on this change. Keep it under 100 words total.

New content snippet:
{new_text[:1000]}"""
        }]
    )
    return response.content[0].text

def sync_knowledge(store: Store = None, dry_run: bool = False) -> list[dict]:
    """Fetch all tracked pages, detect changes, queue content ideas."""
    if store is None:
        store = Store()

    changes = []
    output_dir = Path("knowledge/revenuecat/docs")
    output_dir.mkdir(parents=True, exist_ok=True)

    for url in ALL_URLS:
        try:
            html = fetch_page(url)
            text = extract_text(html)
            new_hash = hash_content(text)
            slug = url.rstrip("/").split("/")[-1] or "index"
            cache_path = output_dir / f"{slug}.txt"

            old_text = cache_path.read_text() if cache_path.exists() else ""
            old_hash = hash_content(old_text) if old_text else ""
            changed = detect_change(url, new_hash, {url: old_hash})

            if changed and not dry_run:
                cache_path.write_text(text)
                store.record_knowledge_check(url, new_hash, changed=True)

                if old_text:  # not first run
                    idea = generate_content_idea(url, old_text, text)
                    store.queue_content(
                        title=f"[Auto] Content idea from {slug} update",
                        content_type="idea",
                        body=idea
                    )
                    changes.append({"url": url, "idea": idea})
                    print(f"✓ Change detected: {url}")
            elif not dry_run:
                store.record_knowledge_check(url, new_hash, changed=False)

            changes.append({"url": url, "changed": changed, "hash": new_hash})

        except Exception as e:
            print(f"✗ Failed {url}: {e}")

    return changes

if __name__ == "__main__":
    store = Store()
    changes = sync_knowledge(store)
    changed = [c for c in changes if c.get("changed")]
    print(f"\nSync complete. {len(changed)} changes detected out of {len(changes)} sources.")
