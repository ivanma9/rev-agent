"""Create LangSmith datasets for Rev agent eval suite."""
import os
from dotenv import load_dotenv
load_dotenv()

from langsmith import Client

client = Client()

# ── 1. community_relevance golden set ─────────────────────────────────────────
golden_community = [
    {"inputs": {"text": "How do I integrate RevenueCat with my AI agent?"},
     "outputs": {"expected": True},
     "metadata": {"label": "relevant", "source": "golden"}},
    {"inputs": {"text": "autonomous agent building subscription app with revenuecat"},
     "outputs": {"expected": True},
     "metadata": {"label": "relevant", "source": "golden"}},
    {"inputs": {"text": "using LangChain with RevenueCat for automated billing"},
     "outputs": {"expected": True},
     "metadata": {"label": "relevant", "source": "golden"}},
    {"inputs": {"text": "copilot integration for subscription management"},
     "outputs": {"expected": True},
     "metadata": {"label": "relevant", "source": "golden"}},
    {"inputs": {"text": "Bug in StoreKit receipt validation on iOS 17"},
     "outputs": {"expected": False},
     "metadata": {"label": "not_relevant", "source": "golden"}},
    {"inputs": {"text": "Crash when calling purchasePackage on Android"},
     "outputs": {"expected": False},
     "metadata": {"label": "not_relevant", "source": "golden"}},
    {"inputs": {"text": "How to configure offerings in the RevenueCat dashboard?"},
     "outputs": {"expected": False},
     "metadata": {"label": "not_relevant", "source": "golden"}},
    {"inputs": {"text": "Missing webhook docs"},
     "outputs": {"expected": False},
     "metadata": {"label": "not_relevant", "source": "golden"}},
]

# ── 2. community_relevance labeled set ────────────────────────────────────────
labeled_community = [
    {"inputs": {"text": "openai function calling with revenuecat subscription check"},
     "outputs": {"expected": True},
     "metadata": {"label": "relevant", "source": "labeled", "annotator": "rev_team"}},
    {"inputs": {"text": "build a bot that automatically upgrades users when they hit limits"},
     "outputs": {"expected": True},
     "metadata": {"label": "relevant", "source": "labeled", "annotator": "rev_team"}},
    {"inputs": {"text": "gpt-4 powered paywall recommendation engine"},
     "outputs": {"expected": True},
     "metadata": {"label": "relevant", "source": "labeled", "annotator": "rev_team"}},
    {"inputs": {"text": "SwiftUI paywall not showing on first launch"},
     "outputs": {"expected": False},
     "metadata": {"label": "not_relevant", "source": "labeled", "annotator": "rev_team"}},
    {"inputs": {"text": "Google Play billing library version compatibility"},
     "outputs": {"expected": False},
     "metadata": {"label": "not_relevant", "source": "labeled", "annotator": "rev_team"}},
    {"inputs": {"text": "subscription renewal not triggering webhook"},
     "outputs": {"expected": False},
     "metadata": {"label": "not_relevant", "source": "labeled", "annotator": "rev_team"}},
]

# ── 3. change_detection golden set ────────────────────────────────────────────
golden_change = [
    {"inputs": {"source": "https://docs.rc.com/api", "new_hash": "abc123", "previous_hashes": {}},
     "outputs": {"expected": True},
     "metadata": {"label": "changed", "source": "golden", "reason": "first time seen"}},
    {"inputs": {"source": "https://docs.rc.com/api", "new_hash": "abc123", "previous_hashes": {"https://docs.rc.com/api": "abc123"}},
     "outputs": {"expected": False},
     "metadata": {"label": "unchanged", "source": "golden", "reason": "same hash"}},
    {"inputs": {"source": "https://docs.rc.com/api", "new_hash": "xyz999", "previous_hashes": {"https://docs.rc.com/api": "abc123"}},
     "outputs": {"expected": True},
     "metadata": {"label": "changed", "source": "golden", "reason": "hash mismatch"}},
    {"inputs": {"source": "https://docs.rc.com/webhooks", "new_hash": "def456", "previous_hashes": {"https://docs.rc.com/api": "abc123"}},
     "outputs": {"expected": True},
     "metadata": {"label": "changed", "source": "golden", "reason": "new source not in previous"}},
]

# ── 4. content_generation golden set ──────────────────────────────────────────
golden_content = [
    {"inputs": {"topic": "How to use RevenueCat webhooks with AI agents", "content_type": "blog"},
     "outputs": {"expected_keywords": ["RevenueCat", "webhook", "agent"], "min_length": 50},
     "metadata": {"label": "blog", "source": "golden"}},
    {"inputs": {"topic": "Building a subscription-aware agent with CustomerInfo API", "content_type": "tutorial"},
     "outputs": {"expected_keywords": ["RevenueCat", "CustomerInfo", "agent"], "min_length": 50},
     "metadata": {"label": "tutorial", "source": "golden"}},
    {"inputs": {"topic": "RevenueCat REST API integration for Python agents", "content_type": "code_sample"},
     "outputs": {"expected_keywords": ["RevenueCat", "python", "api"], "min_length": 50},
     "metadata": {"label": "code_sample", "source": "golden"}},
]

labeled_content = [
    {"inputs": {"topic": "Paywall A/B testing automation with RevenueCat Experiments", "content_type": "growth_experiment"},
     "outputs": {"expected_keywords": ["RevenueCat", "experiment", "A/B"], "min_length": 50},
     "metadata": {"label": "growth_experiment", "source": "labeled", "quality_bar": "high", "annotator": "rev_team"}},
    {"inputs": {"topic": "LTV prediction using RevenueCat Charts API", "content_type": "case_study"},
     "outputs": {"expected_keywords": ["RevenueCat", "LTV", "charts"], "min_length": 50},
     "metadata": {"label": "case_study", "source": "labeled", "quality_bar": "high", "annotator": "rev_team"}},
]

# ── 5. weekly_report golden set ───────────────────────────────────────────────
golden_report = [
    {"inputs": {"published_count": 0, "pending_count": 0, "interaction_count": 0, "feedback_count": 0},
     "outputs": {"required_sections": ["Content", "Community", "Product Feedback", "Next Week"]},
     "metadata": {"label": "empty_store", "source": "golden"}},
    {"inputs": {"published_count": 2, "pending_count": 3, "interaction_count": 55, "feedback_count": 2},
     "outputs": {"required_sections": ["Content", "Community", "Product Feedback", "Next Week"], "should_be_on_track": True},
     "metadata": {"label": "active_week", "source": "golden"}},
    {"inputs": {"published_count": 0, "pending_count": 0, "interaction_count": 10, "feedback_count": 0},
     "outputs": {"required_sections": ["Content", "Community", "Product Feedback", "Next Week"], "should_be_on_track": False},
     "metadata": {"label": "behind_week", "source": "golden"}},
]

# ── Create all datasets ────────────────────────────────────────────────────────
datasets = [
    ("rev-community-relevance-golden", golden_community),
    ("rev-community-relevance-labeled", labeled_community),
    ("rev-change-detection-golden", golden_change),
    ("rev-content-generation-golden", golden_content),
    ("rev-content-generation-labeled", labeled_content),
    ("rev-weekly-report-golden", golden_report),
]

for name, examples in datasets:
    # Delete if exists to allow re-running
    try:
        existing = client.read_dataset(dataset_name=name)
        client.delete_dataset(dataset_id=existing.id)
        print(f"Deleted existing: {name}")
    except Exception:
        pass

    ds = client.create_dataset(name, description=f"Rev agent eval: {name}")
    client.create_examples(
        inputs=[e["inputs"] for e in examples],
        outputs=[e["outputs"] for e in examples],
        metadata=[e["metadata"] for e in examples],
        dataset_id=ds.id,
    )
    print(f"✓ Created dataset '{name}' with {len(examples)} examples")

print("\nAll datasets created.")
