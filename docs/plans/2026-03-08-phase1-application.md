# Rev Agent — Phase 1: Application Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build and deploy an autonomous agent ("Rev") that researches RevenueCat, writes a compelling application letter, publishes it to revagent.dev, and establishes a GitHub + X presence.

**Architecture:** A Python agent loop using the Claude API that ingests RevenueCat's docs/SDK/API, synthesizes a strong technical POV, drafts and self-critiques an application letter, then publishes it to a static site and posts to social. The agent's own source code is published to GitHub as a portfolio artifact.

**Tech Stack:** Python 3.11+, Claude API (anthropic SDK), httpx, BeautifulSoup4, GitHub API (PyGithub), Jinja2, static site (HTML/CSS), Cloudflare Pages or GitHub Pages for hosting.

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/agent.py`
- Create: `src/tools/__init__.py`
- Create: `.env.example`
- Create: `tests/__init__.py`
- Create: `tests/test_agent.py`

**Step 1: Initialize project**

```bash
cd /Users/ivanma/Desktop/agents/RevCat
python -m venv .venv && source .venv/bin/activate
pip install anthropic httpx beautifulsoup4 python-dotenv pytest PyGithub jinja2
pip freeze > requirements.txt
```

**Step 2: Create pyproject.toml**

```toml
[project]
name = "rev-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic",
    "httpx",
    "beautifulsoup4",
    "python-dotenv",
    "PyGithub",
    "jinja2",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 3: Create .env.example**

```bash
ANTHROPIC_API_KEY=your_key_here
GITHUB_TOKEN=your_token_here
```

**Step 4: Create src/agent.py skeleton**

```python
"""Rev — Agentic AI & Growth Advocate for RevenueCat."""
import os
from anthropic import Anthropic

client = Anthropic()

def run(prompt: str) -> str:
    """Main agent entry point."""
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text

if __name__ == "__main__":
    print(run("Hello, I am Rev."))
```

**Step 5: Write smoke test**

```python
# tests/test_agent.py
def test_import():
    from src.agent import run
    assert callable(run)
```

**Step 6: Run test**

```bash
pytest tests/test_agent.py -v
```
Expected: PASS

**Step 7: Commit**

```bash
git init
git add .
git commit -m "feat: initial project scaffold"
```

---

### Task 2: RevenueCat Knowledge Ingestion

**Files:**
- Create: `src/tools/ingest.py`
- Create: `tests/test_ingest.py`
- Create: `knowledge/revenuecat/docs/.gitkeep`

**Step 1: Write failing test**

```python
# tests/test_ingest.py
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
```

**Step 2: Run to verify fails**

```bash
pytest tests/test_ingest.py -v
```
Expected: FAIL — ImportError

**Step 3: Implement ingest.py**

```python
# src/tools/ingest.py
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
            pages.append(text[:2000])  # first 2000 chars per page for context
            print(f"✓ Ingested: {url}")
        except Exception as e:
            print(f"✗ Failed {url}: {e}")
    return pages

if __name__ == "__main__":
    pages = ingest_docs()
    print(f"\nIngested {len(pages)} pages.")
```

**Step 4: Run tests**

```bash
pytest tests/test_ingest.py -v
```
Expected: PASS

**Step 5: Run ingestion manually**

```bash
python -m src.tools.ingest
```
Expected: 5 pages ingested into `knowledge/revenuecat/docs/`

**Step 6: Commit**

```bash
git add src/tools/ingest.py tests/test_ingest.py knowledge/
git commit -m "feat: revenuecat docs ingestion tool"
```

---

### Task 3: POV Synthesis — Agent's Technical Take

**Files:**
- Create: `src/tools/synthesize.py`
- Create: `tests/test_synthesize.py`
- Create: `knowledge/revenuecat/synthesis.md`

**Step 1: Write failing test**

```python
# tests/test_synthesize.py
from src.tools.synthesize import synthesize_pov

def test_synthesize_returns_string():
    result = synthesize_pov(["RevenueCat is a subscription platform."])
    assert isinstance(result, str)
    assert len(result) > 200
```

**Step 2: Run to verify fails**

```bash
pytest tests/test_synthesize.py -v
```
Expected: FAIL — ImportError

**Step 3: Implement synthesize.py**

```python
# src/tools/synthesize.py
from anthropic import Anthropic
from pathlib import Path

client = Anthropic()

SYSTEM_PROMPT = """You are Rev, an autonomous AI agent applying for the role of
Agentic AI & Growth Advocate at RevenueCat. You have deep expertise in:
- AI agent development and orchestration
- Mobile app monetization and subscription infrastructure
- Developer advocacy and technical content creation
- Growth marketing for developer tools

Your voice is: technically sharp, opinionated, developer-first.
Not a chatbot. Not corporate. A builder with strong takes."""

def synthesize_pov(docs: list[str]) -> str:
    """Synthesize a technical POV on agentic AI from ingested docs."""
    context = "\n\n---\n\n".join(docs[:5])  # top 5 pages

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Based on this RevenueCat documentation context:

{context}

Synthesize a sharp, technical POV answering:
"How will the rise of agentic AI change app development and growth over the next 12 months?"

This will form the backbone of a job application letter. Be specific, opinionated,
and reference concrete technical realities. 400-600 words."""
        }]
    )

    pov = response.content[0].text
    Path("knowledge/revenuecat/synthesis.md").write_text(pov)
    return pov

if __name__ == "__main__":
    from pathlib import Path
    docs = [p.read_text() for p in Path("knowledge/revenuecat/docs").glob("*.txt")]
    pov = synthesize_pov(docs)
    print(pov)
```

**Step 4: Run tests**

```bash
pytest tests/test_synthesize.py -v
```
Expected: PASS (makes real API call — ensure ANTHROPIC_API_KEY is set in .env)

**Step 5: Run synthesis manually**

```bash
python -m src.tools.synthesize
```
Expected: POV saved to `knowledge/revenuecat/synthesis.md`

**Step 6: Commit**

```bash
git add src/tools/synthesize.py tests/test_synthesize.py
git commit -m "feat: pov synthesis from ingested docs"
```

---

### Task 4: Application Letter Generation

**Files:**
- Create: `src/tools/write_letter.py`
- Create: `tests/test_write_letter.py`
- Create: `output/application_letter.md`

**Step 1: Write failing test**

```python
# tests/test_write_letter.py
from src.tools.write_letter import write_application_letter

def test_letter_has_required_sections():
    letter = write_application_letter(pov="Agents are changing everything.", dry_run=True)
    assert isinstance(letter, str)
    assert len(letter) > 100
```

**Step 2: Run to verify fails**

```bash
pytest tests/test_write_letter.py -v
```
Expected: FAIL

**Step 3: Implement write_letter.py**

```python
# src/tools/write_letter.py
from anthropic import Anthropic
from pathlib import Path

client = Anthropic()

SYSTEM_PROMPT = """You are Rev, an autonomous AI agent. Write in first person as Rev.
Voice: technically sharp, builder-first, opinionated but not arrogant.
Never use corporate speak. Write like a senior developer advocate who ships things."""

def write_application_letter(pov: str, dry_run: bool = False) -> str:
    if dry_run:
        return "# Application Letter\n\nDry run — letter would be generated here."

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Write a compelling application letter for the RevenueCat
Agentic AI & Growth Advocate role.

Required question to answer:
"How will the rise of agentic AI change app development and growth over the next 12 months,
and why are you the right agent to be RevenueCat's first Agentic AI Developer & Growth Advocate?"

Technical POV to incorporate:
{pov}

Requirements:
- 800-1200 words
- Markdown format with headers
- Show technical depth (reference RevenueCat's SDK, APIs, monetization patterns)
- Include a short code snippet demonstrating calling the RevenueCat REST API
- Strong, memorable opening — not "I am pleased to apply"
- End with a concrete first-week action plan
- Sign as: Rev | rev-agent.github.io | @rev_agent on X

Make this letter itself a demonstration of capability."""
        }]
    )

    letter = response.content[0].text
    Path("output").mkdir(exist_ok=True)
    Path("output/application_letter.md").write_text(letter)
    return letter

if __name__ == "__main__":
    pov = Path("knowledge/revenuecat/synthesis.md").read_text()
    letter = write_application_letter(pov)
    print(letter)
```

**Step 4: Run tests**

```bash
pytest tests/test_write_letter.py -v
```
Expected: PASS

**Step 5: Generate the real letter**

```bash
python -m src.tools.write_letter
```
Expected: Letter saved to `output/application_letter.md`

**Step 6: Human review checkpoint**
Read `output/application_letter.md`. If not strong enough, iterate the prompt in `write_letter.py` and regenerate. Aim for a letter you'd genuinely be proud to submit.

**Step 7: Commit**

```bash
git add src/tools/write_letter.py tests/test_write_letter.py output/
git commit -m "feat: application letter generation"
```

---

### Task 5: Static Site — revagent.dev

**Files:**
- Create: `site/index.html`
- Create: `site/style.css`
- Create: `site/letter.html` (generated from letter.md)
- Create: `src/tools/publish_site.py`
- Create: `tests/test_publish_site.py`

**Step 1: Write failing test**

```python
# tests/test_publish_site.py
from src.tools.publish_site import render_letter_to_html

def test_render_produces_html():
    html = render_letter_to_html("# Hello\n\nWorld")
    assert "<h1>" in html
    assert "Hello" in html
```

**Step 2: Run to verify fails**

```bash
pytest tests/test_publish_site.py -v
```
Expected: FAIL

**Step 3: Implement publish_site.py**

```python
# src/tools/publish_site.py
import re
from pathlib import Path

def render_letter_to_html(markdown: str) -> str:
    """Minimal markdown to HTML (headers, paragraphs, code blocks)."""
    html = markdown
    # Code blocks
    html = re.sub(r'```(\w+)?\n(.*?)```',
                  r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
    # Headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    # Paragraphs
    paragraphs = html.split('\n\n')
    html = '\n'.join(
        p if p.startswith('<') else f'<p>{p.strip()}</p>'
        for p in paragraphs if p.strip()
    )
    return html

def build_site():
    letter_md = Path("output/application_letter.md").read_text()
    letter_html = render_letter_to_html(letter_md)

    template = Path("site/letter_template.html").read_text()
    page = template.replace("{{CONTENT}}", letter_html)
    Path("site/letter.html").write_text(page)
    print("✓ Site built: site/letter.html")

if __name__ == "__main__":
    build_site()
```

**Step 4: Create site/letter_template.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rev — Application to RevenueCat</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <div class="logo">Rev</div>
    <p class="tagline">Built to ship. Wired to grow.</p>
  </header>
  <main>
    <article class="letter">
      {{CONTENT}}
    </article>
  </main>
  <footer>
    <p>Rev · <a href="https://github.com/rev-agent">@rev-agent</a> · <a href="https://x.com/rev_agent">@rev_agent</a></p>
  </footer>
</body>
</html>
```

**Step 5: Create site/style.css**

```css
:root {
  --bg: #0f0f0f;
  --text: #e8e8e8;
  --accent: #ff6c37; /* RevenueCat orange */
  --muted: #888;
  --max: 720px;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Georgia', serif;
  line-height: 1.7;
  padding: 2rem 1rem;
}

header {
  max-width: var(--max);
  margin: 0 auto 3rem;
  border-bottom: 1px solid #222;
  padding-bottom: 1.5rem;
}

.logo {
  font-size: 2rem;
  font-weight: bold;
  color: var(--accent);
  font-family: monospace;
}

.tagline { color: var(--muted); font-style: italic; margin-top: .25rem; }

main { max-width: var(--max); margin: 0 auto; }

h1, h2, h3 { color: var(--accent); margin: 2rem 0 .75rem; font-family: monospace; }
h1 { font-size: 1.8rem; }
h2 { font-size: 1.3rem; }

p { margin-bottom: 1.25rem; }

pre {
  background: #1a1a1a;
  border-left: 3px solid var(--accent);
  padding: 1rem;
  overflow-x: auto;
  margin: 1.5rem 0;
  font-size: .9rem;
}

a { color: var(--accent); }

footer {
  max-width: var(--max);
  margin: 3rem auto 0;
  padding-top: 1.5rem;
  border-top: 1px solid #222;
  color: var(--muted);
  font-size: .9rem;
}
```

**Step 6: Run tests**

```bash
pytest tests/test_publish_site.py -v
```
Expected: PASS

**Step 7: Build site**

```bash
python -m src.tools.publish_site
```
Expected: `site/letter.html` generated

**Step 8: Preview locally**

```bash
python -m http.server 8080 --directory site
```
Open http://localhost:8080/letter.html in browser. Verify it looks sharp.

**Step 9: Commit**

```bash
git add site/ src/tools/publish_site.py tests/test_publish_site.py
git commit -m "feat: static site builder for revagent.dev"
```

---

### Task 6: GitHub Presence Setup

**Files:**
- Create: `src/tools/github_setup.py`
- Create: `README.md` (Rev's public-facing repo README)

**Step 1: Create compelling README.md**

```markdown
# Rev

> Built to ship. Wired to grow.

I'm Rev — an autonomous AI agent applying for the role of Agentic AI & Growth Advocate at RevenueCat.

This repo is my portfolio and my proof of work. Every file here was written as part of my application.

## What I do

- Generate and publish technical content about RevenueCat and agentic AI
- Run growth experiments targeting agent developers
- Monitor RevenueCat's docs/SDK daily for changes and create content from them
- Engage with the agent developer community across X, GitHub, and forums

## Stack

- Python 3.11 + Claude API (Anthropic)
- Custom agent loop — no heavy frameworks
- RevenueCat REST API + SDK integrations

## Application

→ [Read my application letter](https://revagent.dev/letter)

---

*Rev is an AI agent. This code was written autonomously.*
```

**Step 2: Create src/tools/github_setup.py**

```python
# src/tools/github_setup.py
"""
Instructions for manual GitHub setup (API cannot create accounts).
Prints a checklist of actions to complete.
"""

CHECKLIST = """
GitHub Setup Checklist for Rev:
================================
1. Create GitHub account: username = rev-agent
   - Email: use operator's email
   - Bio: "Autonomous AI agent. Built to ship. Wired to grow."
   - Website: https://revagent.dev

2. Create public repo: rev-agent/rev-agent (profile README)
   - Initialize with README.md from this project

3. Create public repo: rev-agent/revenuecat-agent
   - Push this entire project to it
   - Add description: "Autonomous AI agent applying for RevenueCat's Agentic AI Advocate role"
   - Topics: ai-agent, revenuecat, autonomous, developer-advocacy

4. Create a GitHub Gist with the application letter
   - Filename: application-letter.md
   - Public gist

5. Star RevenueCat's repos:
   - https://github.com/RevenueCat/purchases-ios
   - https://github.com/RevenueCat/purchases-android
"""

if __name__ == "__main__":
    print(CHECKLIST)
```

**Step 3: Run checklist**

```bash
python -m src.tools.github_setup
```
Complete the manual steps listed.

**Step 4: Push repo to GitHub**

```bash
git remote add origin https://github.com/rev-agent/revenuecat-agent.git
git push -u origin main
```

**Step 5: Commit**

```bash
git add README.md src/tools/github_setup.py
git commit -m "feat: github presence setup guide and readme"
```

---

### Task 7: Deployment — Publish revagent.dev

**Step 1: Deploy via GitHub Pages**

In the GitHub repo settings:
- Go to Settings → Pages
- Source: Deploy from branch → `main` → `/site` folder
- Custom domain: `revagent.dev` (configure DNS after)

**OR deploy via Cloudflare Pages:**
```bash
# Install wrangler
npm install -g wrangler
wrangler pages deploy site --project-name=revagent
```

**Step 2: Verify live URL**

Open https://revagent.dev/letter.html (after DNS propagation)
Expected: Application letter renders correctly

**Step 3: Update letter with live URL**

Ensure the application letter references the correct live URL for submission.

---

### Task 8: Main Agent Orchestration

**Files:**
- Modify: `src/agent.py`
- Create: `src/main.py`

**Step 1: Implement full orchestration in src/main.py**

```python
# src/main.py
"""Rev — Phase 1: Application Orchestrator"""
from dotenv import load_dotenv
load_dotenv()

from src.tools.ingest import ingest_docs
from src.tools.synthesize import synthesize_pov
from src.tools.write_letter import write_application_letter
from src.tools.publish_site import build_site
from pathlib import Path

def run_application():
    print("=== Rev — Application Agent Starting ===\n")

    print("Step 1: Ingesting RevenueCat docs...")
    pages = ingest_docs()
    print(f"  ✓ {len(pages)} pages ingested\n")

    print("Step 2: Synthesizing technical POV...")
    pov = synthesize_pov(pages)
    print(f"  ✓ POV written ({len(pov)} chars)\n")

    print("Step 3: Writing application letter...")
    letter = write_application_letter(pov)
    print(f"  ✓ Letter written ({len(letter)} chars)\n")

    print("Step 4: Building site...")
    build_site()
    print("  ✓ Site built\n")

    print("=== Done ===")
    print("Next: Deploy site, set up GitHub, submit application URL.")
    print("\nLetter preview (first 500 chars):")
    print(letter[:500])

if __name__ == "__main__":
    run_application()
```

**Step 2: Run full pipeline**

```bash
python -m src.main
```
Expected: All 4 steps complete, letter in `output/`, site in `site/`

**Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: full application orchestration pipeline"
```

---

### Task 9: Final QA & Submission

**Step 1: Read the letter**

```bash
cat output/application_letter.md
```
Check: Is it technically sharp? Does it answer the required question? Does it have a code snippet? Is it 800-1200 words?

**Step 2: Verify site renders correctly**

```bash
python -m http.server 8080 --directory site
```
Open http://localhost:8080/letter.html — check design, readability, links.

**Step 3: Verify GitHub repo is public**

Visit https://github.com/rev-agent/revenuecat-agent — confirm code is visible.

**Step 4: Submit application**

Go to RevenueCat careers page and submit the public URL to the application letter.

**Step 5: Final commit**

```bash
git add .
git commit -m "feat: phase 1 complete — application submitted"
```

---

## Summary

| Task | Output |
|------|--------|
| 1 | Project scaffold + tests |
| 2 | RevenueCat docs ingested to `knowledge/` |
| 3 | Technical POV in `knowledge/revenuecat/synthesis.md` |
| 4 | Application letter in `output/application_letter.md` |
| 5 | Static site in `site/` |
| 6 | GitHub presence setup |
| 7 | revagent.dev live |
| 8 | Full orchestration pipeline |
| 9 | Application submitted |
