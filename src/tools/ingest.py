import httpx
from bs4 import BeautifulSoup
from pathlib import Path

DOCS_URLS = [
    "https://www.revenuecat.com/docs/",
    "https://www.revenuecat.com/docs/getting-started/quickstart",
    "https://www.revenuecat.com/docs/api-v1",
    "https://www.revenuecat.com/docs/sdk-guides/ios",
    "https://www.revenuecat.com/docs/sdk-guides/android",
]

def fetch_page(url: str) -> str:
    response = httpx.get(url, follow_redirects=True, timeout=15)
    response.raise_for_status()
    return response.text

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)

def ingest_docs(output_dir: str = "knowledge/revenuecat/docs") -> list[str]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    pages = []
    for url in DOCS_URLS:
        try:
            html = fetch_page(url)
            text = extract_text(html)
            slug = url.rstrip("/").split("/")[-1] or "index"
            path = Path(output_dir) / f"{slug}.txt"
            path.write_text(text)
            pages.append(text[:2000])
            print(f"✓ Ingested: {url}")
        except Exception as e:
            print(f"✗ Failed {url}: {e}")
    return pages

if __name__ == "__main__":
    pages = ingest_docs()
    print(f"\nIngested {len(pages)} pages.")
