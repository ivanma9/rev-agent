"""Rev — Agentic AI & Growth Advocate for RevenueCat."""
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
