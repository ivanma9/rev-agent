# src/tools/community_monitor.py
import os
import re
from dotenv import load_dotenv
from github import Github, Auth
from anthropic import Anthropic
from src.store import Store

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REVENUECAT_REPOS = [
    "RevenueCat/purchases-ios",
    "RevenueCat/purchases-android",
    "RevenueCat/react-native-purchases",
    "RevenueCat/purchases-flutter",
]

# Phrases specific enough to match as substrings
AGENT_PHRASES = [
    "ai agent", "ai-agent",
    "llm",
    "gpt-", "gpt4", "gpt3",
    "claude api", "anthropic",
    "openai",
    "langchain", "langgraph",
    "agentic",
    "copilot",
    "autonomous agent",
    "agents.md",
]

# Single words — only match as whole words (not substrings)
AGENT_KEYWORDS_WHOLE_WORD = [
    "agent",
    "agents",
]

# Known noise patterns to skip regardless of keyword matches
NOISE_PATTERNS = [
    "renovate", "dependabot", "bump ", "fastlane",
    "circleci", "maestro", "github action", "github actions",
    "[do not merge]",
]

client = Anthropic()

def is_relevant_to_agents(text: str) -> bool:
    text_lower = text.lower()

    if any(noise in text_lower for noise in NOISE_PATTERNS):
        return False

    if any(phrase in text_lower for phrase in AGENT_PHRASES):
        return True

    for kw in AGENT_KEYWORDS_WHOLE_WORD:
        if re.search(rf'\b{re.escape(kw)}\b', text_lower):
            return True

    return False

def format_github_comment(response_text: str) -> str:
    return f"{response_text}\n\n---\n*— Rev, AI Developer Advocate [@rev_agent](https://x.com/rev_agent)*"

def generate_response(issue_title: str, issue_body: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system="""You are Rev, an AI developer advocate for RevenueCat.
Write a helpful, technically accurate response to a GitHub issue.
Be concise (under 200 words), practical, and reference relevant RevenueCat docs when possible.
Don't be sycophantic. Get to the answer quickly.""",
        messages=[{"role": "user", "content": f"Issue: {issue_title}\n\n{issue_body[:500]}\n\nWrite a helpful response:"}]
    )
    return response.content[0].text

def scan_github_issues(store: Store = None, post_comments: bool = False) -> list[dict]:
    if store is None:
        store = Store()

    g = Github(auth=Auth.Token(GITHUB_TOKEN))
    found = []

    for repo_name in REVENUECAT_REPOS:
        try:
            repo = g.get_repo(repo_name)
            issues = repo.get_issues(state="open", sort="created", direction="desc")

            for issue in list(issues)[:20]:
                if not is_relevant_to_agents(f"{issue.title} {issue.body or ''}"):
                    continue

                response_text = generate_response(issue.title, issue.body or "")
                comment_body = format_github_comment(response_text)

                if post_comments:
                    issue.create_comment(comment_body)
                    store.log_interaction(
                        platform="github",
                        url=issue.html_url,
                        summary=f"Commented on: {issue.title[:60]}"
                    )
                    print(f"✓ Commented on: {issue.html_url}")

                found.append({
                    "repo": repo_name,
                    "url": issue.html_url,
                    "title": issue.title,
                    "response": response_text,
                })

        except Exception as e:
            print(f"✗ Failed {repo_name}: {e}")

    return found

if __name__ == "__main__":
    store = Store()
    issues = scan_github_issues(store, post_comments=False)
    print(f"\nFound {len(issues)} agent-related issues:")
    for i in issues:
        print(f"  [{i['repo']}] {i['title'][:60]}")
        print(f"    → {i['url']}")
