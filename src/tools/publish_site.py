import re
from pathlib import Path

def render_letter_to_html(markdown: str) -> str:
    """Convert markdown to HTML (headers, paragraphs, code blocks, bold, links)."""
    html = markdown
    # Fenced code blocks
    html = re.sub(
        r'```(?:\w+)?\n(.*?)```',
        r'<pre><code>\1</code></pre>',
        html, flags=re.DOTALL
    )
    # Bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    # Headers (order: h3 before h2 before h1)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    # Horizontal rules
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
    # Paragraphs (split on double newlines, wrap non-tag blocks)
    paragraphs = re.split(r'\n\n+', html)
    result = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith('<'):
            result.append(p)
        else:
            result.append(f'<p>{p}</p>')
    return '\n'.join(result)

def build_site(letter_path: str = "output/application_letter.md",
               template_path: str = "site/letter_template.html",
               output_path: str = "site/letter.html"):
    letter_md = Path(letter_path).read_text()
    letter_html = render_letter_to_html(letter_md)
    template = Path(template_path).read_text()
    page = template.replace("{{CONTENT}}", letter_html)
    Path(output_path).write_text(page)
    print(f"✓ Site built: {output_path}")

if __name__ == "__main__":
    build_site()
