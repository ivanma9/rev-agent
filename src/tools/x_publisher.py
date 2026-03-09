# src/tools/x_publisher.py
"""Post content to X (Twitter) via API v2."""
import os
import logging
from dotenv import load_dotenv
import tweepy
from src.store import Store

load_dotenv()
log = logging.getLogger(__name__)

MAX_TWEET_LEN = 280
# Reserve space for thread numbering " (N/M)" — max 8 chars
THREAD_BODY_LEN = MAX_TWEET_LEN - 8


def _get_client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    )


def split_into_thread(text: str) -> list[str]:
    """Split text into tweet-sized chunks. Adds (N/M) numbering if >1 tweet."""
    if len(text) <= MAX_TWEET_LEN:
        return [text]

    words = text.split()
    chunks = []
    current = []
    current_len = 0

    for word in words:
        # If a single word exceeds THREAD_BODY_LEN, split it char by char
        while len(word) > THREAD_BODY_LEN:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_len = 0
            chunks.append(word[:THREAD_BODY_LEN])
            word = word[THREAD_BODY_LEN:]

        if current_len + len(word) + (1 if current else 0) > THREAD_BODY_LEN:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += len(word) + (1 if len(current) > 1 else 0)

    if current:
        chunks.append(" ".join(current))

    total = len(chunks)
    if total == 1:
        return chunks

    return [f"{chunk} ({i+1}/{total})" for i, chunk in enumerate(chunks)]


def format_content_tweet(title: str, url: str, content_type: str) -> str:
    """Format a cross-post tweet for published content."""
    type_emoji = {
        "blog": "📝",
        "tutorial": "🧵",
        "code_sample": "💻",
        "case_study": "📊",
        "growth_experiment": "🧪",
        "report": "📋",
    }.get(content_type, "📄")

    text = f"{type_emoji} New from Rev:\n\n{title}\n\n{url}\n\n#RevenueCat #AgentDev"
    if len(text) > MAX_TWEET_LEN:
        max_title = MAX_TWEET_LEN - len(f"{type_emoji} New from Rev:\n\n\n\n{url}\n\n#RevenueCat #AgentDev") - 3
        text = f"{type_emoji} New from Rev:\n\n{title[:max_title]}...\n\n{url}\n\n#RevenueCat #AgentDev"
    return text


def post_tweet(
    text: str,
    dry_run: bool = False,
    store: Store = None,
) -> dict:
    """Post a tweet or thread. Returns result dict."""
    tweets = split_into_thread(text)
    total = len(tweets)

    if dry_run:
        log.info(f"[DRY RUN] Would post {total} tweet(s):")
        for i, t in enumerate(tweets):
            log.info(f"  [{i+1}/{total}] {t[:80]}...")
        if store:
            store.log_interaction(
                platform="x",
                url="https://x.com/cat_rev85934",
                summary=f"[DRY RUN] Posted thread ({total} tweets): {text[:60]}"
            )
        return {"posted": True, "dry_run": True, "tweet_count": total, "text": text}

    client = _get_client()
    tweet_ids = []
    reply_to = None

    try:
        for i, tweet_text in enumerate(tweets):
            if reply_to:
                response = client.create_tweet(
                    text=tweet_text,
                    in_reply_to_tweet_id=reply_to
                )
            else:
                response = client.create_tweet(text=tweet_text)

            tweet_id = response.data["id"]
            tweet_ids.append(tweet_id)
            reply_to = tweet_id
            log.info(f"Posted tweet {i+1}/{total}: {tweet_id}")

        url = f"https://x.com/cat_rev85934/status/{tweet_ids[0]}"
        if store:
            store.log_interaction(
                platform="x",
                url=url,
                summary=f"Posted thread ({total} tweets): {text[:60]}"
            )
        return {"posted": True, "dry_run": False, "tweet_count": total, "url": url, "ids": tweet_ids}

    except Exception as e:
        log.error(f"Failed to post tweet: {e}")
        return {"posted": False, "error": str(e)}


if __name__ == "__main__":
    result = post_tweet(
        "Rev here. Building autonomous developer advocacy for @RevenueCat. "
        "I write technical content, monitor community questions, and run growth experiments — all autonomously. "
        "Follow for weekly content on subscription APIs + agentic AI.\n\n"
        "github.com/ivanma9/rev-agent",
        dry_run=True
    )
    print(result)
