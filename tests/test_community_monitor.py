import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_is_relevant_to_agents_true_positives():
    from src.tools.community_monitor import is_relevant_to_agents
    assert is_relevant_to_agents("How do I use RevenueCat with my AI agent?") is True
    assert is_relevant_to_agents("autonomous agent building subscription app with revenuecat") is True
    assert is_relevant_to_agents("using LangChain with RevenueCat for automated billing") is True
    assert is_relevant_to_agents("openai function calling with revenuecat") is True
    assert is_relevant_to_agents("building an LLM-powered paywall") is True
    assert is_relevant_to_agents("Add AGENTS.md for AI coding assistants") is True

def test_is_relevant_to_agents_false_positives():
    from src.tools.community_monitor import is_relevant_to_agents
    assert is_relevant_to_agents("[RENOVATE] Update dependency gradle to v9.4.0") is False
    assert is_relevant_to_agents("feat: add CircleCI job for maestro E2E tests") is False
    assert is_relevant_to_agents("feat: add maestro E2E test app") is False
    assert is_relevant_to_agents("Github Action: Update permissions") is False
    assert is_relevant_to_agents("Bug in StoreKit receipt validation") is False
    assert is_relevant_to_agents("Crash when calling purchasePackage on Android") is False
    assert is_relevant_to_agents("[DO NOT MERGE] Bump fastlane from 2.229.1 to 2.232.2") is False
    assert is_relevant_to_agents("Fix video audio session category to use .playback") is False

def test_format_github_comment():
    from src.tools.community_monitor import format_github_comment
    comment = format_github_comment("Great question! Here's how...")
    assert "Rev" in comment
    assert len(comment) > 20
