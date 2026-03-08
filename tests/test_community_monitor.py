# tests/test_community_monitor.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_is_relevant_to_agents():
    from src.tools.community_monitor import is_relevant_to_agents
    assert is_relevant_to_agents("How do I use RevenueCat with my AI agent?") is True
    assert is_relevant_to_agents("Bug in StoreKit receipt validation") is False
    assert is_relevant_to_agents("autonomous agent building app with revenuecat") is True

def test_format_github_comment():
    from src.tools.community_monitor import format_github_comment
    comment = format_github_comment("Great question! Here's how...")
    assert "Rev" in comment
    assert len(comment) > 20
