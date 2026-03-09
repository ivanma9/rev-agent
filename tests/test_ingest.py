import pytest
from src.tools.ingest import fetch_page, extract_text

@pytest.mark.integration
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

@pytest.mark.integration
def test_all_docs_urls_return_200():
    from src.tools.ingest import DOCS_URLS, fetch_page
    for url in DOCS_URLS:
        html = fetch_page(url)
        assert len(html) > 100, f"Got empty/tiny response from: {url}"
        assert "<" in html, f"Response doesn't look like HTML: {url}"
