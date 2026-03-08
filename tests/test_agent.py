def test_import():
    from src.agent import run
    assert callable(run)
