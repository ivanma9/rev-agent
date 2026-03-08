def test_synthesize_returns_string():
    from src.tools.synthesize import synthesize_pov
    result = synthesize_pov(["RevenueCat is a subscription platform."])
    assert isinstance(result, str)
    assert len(result) > 200
