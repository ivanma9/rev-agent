"""Rev agent evaluators for LangSmith."""
from langsmith.schemas import Run, Example
from langsmith.evaluation.evaluator import EvaluationResult, EvaluationResults


# ── Community Relevance ────────────────────────────────────────────────────────

def eval_community_relevance_accuracy(run: Run, example: Example) -> dict:
    """Check if is_relevant_to_agents matches expected label."""
    actual = run.outputs.get("relevant") if run.outputs else None
    expected = example.outputs.get("expected") if example.outputs else None

    if actual is None or expected is None:
        return {"key": "relevance_accuracy", "score": None, "comment": "Missing output"}

    correct = bool(actual) == bool(expected)
    return {
        "key": "relevance_accuracy",
        "score": int(correct),
        "comment": f"Expected {expected}, got {actual}"
    }

def eval_no_false_positives(run: Run, example: Example) -> dict:
    """Penalize false positives (labeling irrelevant as relevant)."""
    actual = run.outputs.get("relevant") if run.outputs else None
    expected = example.outputs.get("expected") if example.outputs else None
    label = example.metadata.get("label", "") if example.metadata else ""

    if actual is None or expected is None:
        return {"key": "no_false_positive", "score": None}

    if label == "not_relevant" and bool(actual) is True:
        return {"key": "no_false_positive", "score": 0, "comment": "False positive: flagged irrelevant issue"}
    return {"key": "no_false_positive", "score": 1}


# ── Change Detection ───────────────────────────────────────────────────────────

def eval_change_detection_accuracy(run: Run, example: Example) -> dict:
    """Check if detect_change returns correct boolean."""
    actual = run.outputs.get("changed") if run.outputs else None
    expected = example.outputs.get("expected") if example.outputs else None

    if actual is None or expected is None:
        return {"key": "change_detection_accuracy", "score": None}

    correct = bool(actual) == bool(expected)
    reason = example.metadata.get("reason", "") if example.metadata else ""
    return {
        "key": "change_detection_accuracy",
        "score": int(correct),
        "comment": f"{reason} — expected {expected}, got {actual}"
    }


# ── Content Generation ─────────────────────────────────────────────────────────

def eval_content_has_keywords(run: Run, example: Example) -> dict:
    """Check content contains expected RevenueCat keywords."""
    content = run.outputs.get("content", "") if run.outputs else ""
    expected_keywords = example.outputs.get("expected_keywords", []) if example.outputs else []

    if not content or not expected_keywords:
        return {"key": "content_has_keywords", "score": None}

    content_lower = content.lower()
    found = [kw for kw in expected_keywords if kw.lower() in content_lower]
    score = len(found) / len(expected_keywords)
    return {
        "key": "content_has_keywords",
        "score": score,
        "comment": f"Found {len(found)}/{len(expected_keywords)} keywords: {found}"
    }

def eval_content_min_length(run: Run, example: Example) -> dict:
    """Check content meets minimum length."""
    content = run.outputs.get("content", "") if run.outputs else ""
    min_length = example.outputs.get("min_length", 50) if example.outputs else 50

    if not content:
        return {"key": "content_min_length", "score": 0, "comment": "Empty content"}

    meets = len(content) >= min_length
    return {
        "key": "content_min_length",
        "score": int(meets),
        "comment": f"Length {len(content)} vs min {min_length}"
    }

def eval_content_has_revenuecat_branding(run: Run, example: Example) -> dict:
    """Check content mentions Rev/rev_agent signature."""
    content = run.outputs.get("content", "") if run.outputs else ""
    has_branding = "rev" in content.lower()
    return {
        "key": "content_has_branding",
        "score": int(has_branding),
        "comment": "Rev branding present" if has_branding else "Missing Rev branding"
    }


# ── Weekly Report ──────────────────────────────────────────────────────────────

def eval_report_has_required_sections(run: Run, example: Example) -> dict:
    """Check report contains all required sections."""
    report = run.outputs.get("report", "") if run.outputs else ""
    required = example.outputs.get("required_sections", []) if example.outputs else []

    if not report or not required:
        return {"key": "report_sections", "score": None}

    found = [s for s in required if s.lower() in report.lower()]
    score = len(found) / len(required)
    missing = [s for s in required if s.lower() not in report.lower()]
    return {
        "key": "report_sections",
        "score": score,
        "comment": f"Found {len(found)}/{len(required)} sections. Missing: {missing}"
    }

def eval_report_on_track_status(run: Run, example: Example) -> dict:
    """Check report correctly shows on-track vs behind status."""
    report = run.outputs.get("report", "") if run.outputs else ""
    should_be_on_track = example.outputs.get("should_be_on_track") if example.outputs else None

    if should_be_on_track is None:
        return {"key": "report_on_track_status", "score": None, "comment": "N/A"}

    has_on_track = "✅" in report or "On track" in report
    has_behind = "⚠️" in report or "Behind" in report

    if should_be_on_track:
        correct = has_on_track and not has_behind
    else:
        correct = has_behind and not has_on_track

    return {
        "key": "report_on_track_status",
        "score": int(correct),
        "comment": f"Expected {'on-track' if should_be_on_track else 'behind'}, report shows: {'on-track' if has_on_track else 'behind'}"
    }


# ── Summary evaluators ─────────────────────────────────────────────────────────

def summary_precision_recall(runs, examples):
    """Precision and recall for community relevance classification."""
    tp = fp = fn = tn = 0
    for run, example in zip(runs, examples):
        actual = bool(run.outputs.get("relevant")) if run.outputs else False
        expected = bool(example.outputs.get("expected")) if example.outputs else False
        if actual and expected:
            tp += 1
        elif actual and not expected:
            fp += 1
        elif not actual and expected:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return EvaluationResults(results=[
        EvaluationResult(key="precision", score=precision),
        EvaluationResult(key="recall", score=recall),
        EvaluationResult(key="f1", score=f1),
    ])
