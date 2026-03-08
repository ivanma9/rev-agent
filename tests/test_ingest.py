from src.tools.ingest import fetch_page, extract_text

def test_fetch_page_returns_html():
    html = fetch_page("https://www.revenuecat.com/docs/")
    assert len(html) > 100
    assert "<" in html

def test_extract_text_strips_tags():
    html = "<h1>Hello</h1><p>World</p>"
    text = extract_text(html)
    assert "Hello" in text
    assert "World" in text
    assert "<" not in text
