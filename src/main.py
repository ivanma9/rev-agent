"""Rev — Phase 1: Application Orchestrator

Run this to execute the full application pipeline:
  ingest docs → synthesize POV → write letter → build site
"""
from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from src.tools.ingest import ingest_docs
from src.tools.synthesize import synthesize_pov
from src.tools.write_letter import write_application_letter
from src.tools.publish_site import build_site


def run_application(force_regenerate: bool = False) -> None:
    print("=== Rev — Application Agent ===\n")

    # Step 1: Ingest
    print("Step 1: Ingesting RevenueCat docs...")
    pages = ingest_docs()
    print(f"  ✓ {len(pages)} pages ingested\n")

    # Step 2: Synthesize POV (skip if already exists unless forced)
    synthesis_path = Path("knowledge/revenuecat/synthesis.md")
    if synthesis_path.exists() and not force_regenerate:
        print("Step 2: Loading existing POV synthesis...")
        pov = synthesis_path.read_text()
        print(f"  ✓ Loaded ({len(pov)} chars)\n")
    else:
        print("Step 2: Synthesizing technical POV...")
        pov = synthesize_pov(pages)
        print(f"  ✓ POV written ({len(pov)} chars)\n")

    # Step 3: Write letter (skip if already exists unless forced)
    letter_path = Path("output/application_letter.md")
    if letter_path.exists() and not force_regenerate:
        print("Step 3: Loading existing application letter...")
        letter = letter_path.read_text()
        print(f"  ✓ Loaded ({len(letter)} chars)\n")
    else:
        print("Step 3: Writing application letter...")
        letter = write_application_letter(pov)
        print(f"  ✓ Letter written ({len(letter)} chars)\n")

    # Step 4: Build site
    print("Step 4: Building site...")
    build_site()
    print("  ✓ Site built\n")

    print("=== Done ===")
    print("Site: https://ivanma9.github.io/rev-agent/letter.html")
    print("\nLetter preview (first 300 chars):")
    print(letter[:300])


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    run_application(force_regenerate=force)
