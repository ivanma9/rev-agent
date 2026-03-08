from anthropic import Anthropic
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
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
    context = "\n\n---\n\n".join(docs[:5])

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
    Path("knowledge/revenuecat").mkdir(parents=True, exist_ok=True)
    Path("knowledge/revenuecat/synthesis.md").write_text(pov)
    return pov

if __name__ == "__main__":
    docs = [p.read_text() for p in Path("knowledge/revenuecat/docs").glob("*.txt")]
    if not docs:
        docs = ["RevenueCat is a subscription management platform used by 40%+ of new subscription apps. It processes $10B+ in annual purchase volume. It provides SDKs for iOS, Android, Flutter, React Native, and a REST API."]
    pov = synthesize_pov(docs)
    print(pov)
