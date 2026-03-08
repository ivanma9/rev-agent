# tests/test_product_feedback.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_generate_feedback_dry_run():
    from src.tools.product_feedback import generate_feedback_item
    item = generate_feedback_item(
        observation="The webhook documentation doesn't cover retry logic for agent use cases.",
        dry_run=True
    )
    assert isinstance(item, dict)
    assert "title" in item
    assert "body" in item

def test_feedback_has_required_fields():
    from src.tools.product_feedback import generate_feedback_item
    item = generate_feedback_item(
        observation="No Python SDK available, only mobile SDKs.",
        dry_run=True
    )
    assert len(item["title"]) > 5
    assert len(item["body"]) > 20
