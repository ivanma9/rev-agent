# tests/test_knowledge_sync.py
import os
os.environ["REV_DB_PATH"] = ":memory:"

def test_hash_content_is_deterministic():
    from src.tools.knowledge_sync import hash_content
    assert hash_content("hello") == hash_content("hello")
    assert hash_content("hello") != hash_content("world")

def test_sync_returns_changes():
    from src.tools.knowledge_sync import sync_knowledge
    from src.store import Store
    store = Store(":memory:")
    # First sync — everything is "new"
    changes = sync_knowledge(store=store, dry_run=True)
    assert isinstance(changes, list)

def test_no_false_positives_on_second_sync(tmp_path):
    from src.tools.knowledge_sync import hash_content, detect_change
    content = "same content"
    h = hash_content(content)
    changed = detect_change("test_source", h, {})
    assert changed is True
    state = {"test_source": h}
    changed2 = detect_change("test_source", h, state)
    assert changed2 is False
