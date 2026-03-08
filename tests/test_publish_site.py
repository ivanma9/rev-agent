def test_render_produces_html():
    from src.tools.publish_site import render_letter_to_html
    html = render_letter_to_html("# Hello\n\nWorld\n\n```python\nprint('hi')\n```")
    assert "<h1>" in html
    assert "Hello" in html
    assert "World" in html

def test_render_handles_code_blocks():
    from src.tools.publish_site import render_letter_to_html
    html = render_letter_to_html("```python\nprint('hi')\n```")
    assert "<pre>" in html or "<code>" in html
