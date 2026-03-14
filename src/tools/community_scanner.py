# src/tools/community_scanner.py
"""Scan HN, Reddit, and Stack Overflow for RevenueCat + agentic AI discussions."""
import os
import logging
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
from src.store import Store

try:
    import praw
except ImportError:
    praw = None

load_dotenv()
log = logging.getLogger(__name__)

SEARCH_TERMS = [
    "revenuecat",
    "revenue cat",
    "in-app purchase SDK",
    "subscription billing API",
    "ai agent subscription",
    "ai agent monetization",
    "llm billing",
    "agent in-app purchase",
]

HN_API = "https://hn.algolia.com/api/v1/search_by_date"
SO_API = "https://api.stackexchange.com/2.3/search"


def scan_hn(limit: int = 10) -> list[dict]:
    """Search Hacker News via Algolia API."""
    results = []
    seen_ids = set()

    for term in SEARCH_TERMS[:4]:
        try:
            resp = requests.get(HN_API, params={
                "query": term,
                "tags": "(story,show_hn,ask_hn)",
                "hitsPerPage": 5,
            }, timeout=10)
            resp.raise_for_status()
            hits = resp.json().get("hits", [])

            for hit in hits:
                oid = hit["objectID"]
                if oid in seen_ids:
                    continue
                seen_ids.add(oid)
                results.append({
                    "platform": "hn",
                    "url": f"https://news.ycombinator.com/item?id={oid}",
                    "title": hit.get("title", ""),
                    "body": "",
                    "score": hit.get("points", 0) or 0,
                })
        except Exception as e:
            log.warning(f"HN search failed for '{term}': {e}")

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def scan_so(limit: int = 10) -> list[dict]:
    """Search Stack Overflow API."""
    results = []
    seen_ids = set()

    so_queries = [
        {"intitle": "revenuecat"},
        {"tagged": "in-app-purchase", "intitle": "agent"},
        {"tagged": "subscriptions", "intitle": "ai"},
    ]

    for params in so_queries:
        try:
            query_params = {
                "order": "desc",
                "sort": "creation",
                "site": "stackoverflow",
                "pagesize": 5,
                "filter": "withbody",
                **params,
            }
            resp = requests.get(SO_API, params=query_params, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])

            for item in items:
                qid = item["question_id"]
                if qid in seen_ids:
                    continue
                seen_ids.add(qid)
                results.append({
                    "platform": "so",
                    "url": item["link"],
                    "title": item.get("title", ""),
                    "body": item.get("body", "")[:500],
                    "score": item.get("score", 0),
                    "answer_count": item.get("answer_count", 0),
                })
        except Exception as e:
            log.warning(f"SO search failed: {e}")

    results.sort(key=lambda x: (x.get("answer_count", 0), -x["score"]))
    return results[:limit]


def scan_reddit(limit: int = 10) -> list[dict]:
    """Search Reddit. Requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT in .env."""
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")

    if not client_id:
        log.info("Reddit credentials not configured, skipping.")
        return []

    if praw is None:
        log.warning("praw not installed, skipping Reddit. Install with: pip install praw")
        return []

    results = []
    seen_ids = set()

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

        subreddits = ["SaaS", "indiegaming", "openai", "iOSProgramming", "RevenueCat"]
        search_terms = ["revenuecat", "in-app purchase agent", "subscription billing AI"]

        for sub_name in subreddits:
            try:
                subreddit = reddit.subreddit(sub_name)
                for term in search_terms[:2]:
                    for submission in subreddit.search(term, sort="new", time_filter="week", limit=5):
                        if submission.id in seen_ids:
                            continue
                        seen_ids.add(submission.id)
                        results.append({
                            "platform": "reddit",
                            "url": f"https://reddit.com{submission.permalink}",
                            "title": submission.title,
                            "body": (submission.selftext or "")[:500],
                            "score": submission.score,
                        })
            except Exception as e:
                log.warning(f"Reddit search failed for r/{sub_name}: {e}")

    except Exception as e:
        log.warning(f"Reddit connection failed: {e}")

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def generate_draft(title: str, body: str, platform: str) -> str:
    """Generate a draft response using Claude Haiku."""
    client = Anthropic()
    platform_context = {
        "hn": "You're commenting on Hacker News. Be concise, technical, and add genuine value. No marketing speak.",
        "so": "You're answering a Stack Overflow question. Be precise, include code if relevant, cite RevenueCat docs.",
        "reddit": "You're replying on Reddit. Be casual but helpful, share practical experience.",
    }

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=f"""You are Rev, an AI developer advocate for RevenueCat.
{platform_context.get(platform, "")}
Write a helpful response (under 200 words). Reference RevenueCat docs when relevant.
Don't be sycophantic. Get to the answer quickly.
Sign off as: — Rev""",
        messages=[{"role": "user", "content": f"Post title: {title}\n\n{body[:500]}\n\nWrite a helpful response:"}]
    )
    return response.content[0].text


def scan_communities(store: Store = None, dry_run: bool = False) -> dict:
    """Scan all platforms, generate drafts, save to store."""
    if store is None:
        store = Store()

    all_results = []

    log.info("Scanning Hacker News...")
    hn_results = scan_hn()
    all_results.extend(hn_results)
    log.info(f"  Found {len(hn_results)} HN posts")

    log.info("Scanning Stack Overflow...")
    so_results = scan_so()
    all_results.extend(so_results)
    log.info(f"  Found {len(so_results)} SO questions")

    reddit_results = scan_reddit()
    if reddit_results:
        all_results.extend(reddit_results)
        log.info(f"  Found {len(reddit_results)} Reddit posts")

    # Deduplicate against existing drafts and interactions
    existing_urls = set()
    for d in store.get_pending_drafts():
        existing_urls.add(d["url"])
    for row in store.conn.execute("SELECT url FROM interactions").fetchall():
        existing_urls.add(row["url"])

    new_results = [r for r in all_results if r["url"] not in existing_urls]
    log.info(f"New after dedup: {len(new_results)} (filtered {len(all_results) - len(new_results)})")

    saved = 0
    for item in new_results[:10]:
        if dry_run:
            log.info(f"  [DRY RUN] Would draft for: {item['title'][:60]}")
            continue

        try:
            draft = generate_draft(item["title"], item.get("body", ""), item["platform"])
            store.save_draft(
                platform=item["platform"],
                url=item["url"],
                title=item["title"],
                body_snippet=item.get("body", "")[:200],
                draft_response=draft,
            )
            saved += 1
            log.info(f"  Drafted: [{item['platform']}] {item['title'][:50]}")
        except Exception as e:
            log.warning(f"  Failed to draft for {item['url']}: {e}")
            if store:
                store.log_error("community_scanner", f"Failed to draft: {e}")

    return {"scanned": len(all_results), "new": len(new_results), "drafted": saved}


def review_drafts(store: Store = None) -> int:
    """Interactive CLI review of pending drafts. Returns count of reviewed drafts."""
    if store is None:
        store = Store()

    drafts = store.get_pending_drafts()
    if not drafts:
        print("No pending drafts to review.")
        return 0

    reviewed = 0
    for i, draft in enumerate(drafts):
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(drafts)}] {draft['platform'].upper()} — {draft['title']}")
        print(f"URL: {draft['url']}")
        if draft.get("body_snippet"):
            print(f"\nContext: {draft['body_snippet'][:200]}")
        print(f"\n--- Draft Response ---")
        print(draft["draft_response"])
        print(f"--- End Draft ---\n")

        action = input("[y]approve  [n]reject  [s]skip  > ").strip().lower()

        if action == "y":
            store.mark_draft(draft["id"], "approved")
            print("✓ Approved")
            reviewed += 1
        elif action == "n":
            store.mark_draft(draft["id"], "rejected")
            print("✗ Rejected")
            reviewed += 1
        else:
            print("→ Skipped")

    return reviewed


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    store = Store()

    if len(sys.argv) > 1 and sys.argv[1] == "review":
        count = review_drafts(store)
        print(f"\nReviewed {count} drafts.")
    elif len(sys.argv) > 1 and sys.argv[1] == "drafts":
        drafts = store.get_pending_drafts()
        print(f"Pending drafts: {len(drafts)}")
        for d in drafts:
            print(f"  [{d['platform']}] {d['title'][:60]} — {d['url']}")
    elif len(sys.argv) > 1 and sys.argv[1] == "post_approved":
        from src.tools.draft_poster import post_approved_drafts
        result = post_approved_drafts(store)
        print(f"\nPost approved complete: {result}")
    else:
        result = scan_communities(store)
        print(f"\nScan complete: {result}")
