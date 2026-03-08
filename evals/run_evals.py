"""Run Rev agent evaluations against LangSmith datasets."""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from langsmith import evaluate
from langsmith import traceable
from src.tools.community_monitor import is_relevant_to_agents
from src.tools.knowledge_sync import detect_change
from src.tools.content_generator import generate_content
from src.tools.weekly_report import generate_weekly_report
from src.store import Store

from evals.evaluators import (
    eval_community_relevance_accuracy,
    eval_no_false_positives,
    eval_change_detection_accuracy,
    eval_content_has_keywords,
    eval_content_min_length,
    eval_content_has_revenuecat_branding,
    eval_report_has_required_sections,
    eval_report_on_track_status,
    summary_precision_recall,
)


# ── Targets ────────────────────────────────────────────────────────────────────

@traceable
def community_relevance_target(inputs: dict) -> dict:
    result = is_relevant_to_agents(inputs["text"])
    return {"relevant": result}

@traceable
def change_detection_target(inputs: dict) -> dict:
    result = detect_change(
        inputs["source"],
        inputs["new_hash"],
        inputs["previous_hashes"]
    )
    return {"changed": result}

@traceable
def content_generation_target(inputs: dict) -> dict:
    content = generate_content(
        topic=inputs["topic"],
        content_type=inputs["content_type"],
        dry_run=True  # use dry_run to avoid API calls during eval
    )
    return {"content": content}

@traceable
def weekly_report_target(inputs: dict) -> dict:
    store = Store(":memory:")
    # Seed store with the scenario data
    for _ in range(inputs.get("published_count", 0)):
        store.queue_content("Test", "blog", "body")
        items = store.get_pending_content()
        if items:
            store.mark_published(items[0]["id"], url="https://example.com")
    for _ in range(inputs.get("pending_count", 0)):
        store.queue_content("Pending", "blog", "body")
    for _ in range(inputs.get("interaction_count", 0)):
        store.log_interaction("github", "https://github.com/test", "test")
    for _ in range(inputs.get("feedback_count", 0)):
        store.add_feedback("Test feedback", "body")

    report = generate_weekly_report(store=store)
    return {"report": report}


# ── Run experiments ────────────────────────────────────────────────────────────

EXPERIMENTS = {
    "community-golden": {
        "target": community_relevance_target,
        "dataset": "rev-community-relevance-golden",
        "evaluators": [eval_community_relevance_accuracy, eval_no_false_positives],
        "summary_evaluators": [summary_precision_recall],
        "prefix": "community-relevance-golden",
    },
    "community-labeled": {
        "target": community_relevance_target,
        "dataset": "rev-community-relevance-labeled",
        "evaluators": [eval_community_relevance_accuracy, eval_no_false_positives],
        "prefix": "community-relevance-labeled",
    },
    "change-detection": {
        "target": change_detection_target,
        "dataset": "rev-change-detection-golden",
        "evaluators": [eval_change_detection_accuracy],
        "prefix": "change-detection-golden",
    },
    "content-golden": {
        "target": content_generation_target,
        "dataset": "rev-content-generation-golden",
        "evaluators": [eval_content_has_keywords, eval_content_min_length, eval_content_has_revenuecat_branding],
        "prefix": "content-gen-golden",
    },
    "content-labeled": {
        "target": content_generation_target,
        "dataset": "rev-content-generation-labeled",
        "evaluators": [eval_content_has_keywords, eval_content_min_length, eval_content_has_revenuecat_branding],
        "prefix": "content-gen-labeled",
    },
    "report-golden": {
        "target": weekly_report_target,
        "dataset": "rev-weekly-report-golden",
        "evaluators": [eval_report_has_required_sections, eval_report_on_track_status],
        "prefix": "weekly-report-golden",
    },
}

if __name__ == "__main__":
    target_exp = sys.argv[1] if len(sys.argv) > 1 else None

    to_run = {target_exp: EXPERIMENTS[target_exp]} if target_exp and target_exp in EXPERIMENTS else EXPERIMENTS

    for name, cfg in to_run.items():
        print(f"\n{'='*50}")
        print(f"Running: {name}")
        print(f"  Dataset: {cfg['dataset']}")
        print(f"  Evaluators: {[e.__name__ for e in cfg['evaluators']]}")
        results = evaluate(
            cfg["target"],
            data=cfg["dataset"],
            evaluators=cfg["evaluators"],
            summary_evaluators=cfg.get("summary_evaluators", []),
            experiment_prefix=cfg["prefix"],
        )
        print(f"✓ Done: {name}")

    print("\nAll experiments complete. View results at https://smith.langchain.com")
