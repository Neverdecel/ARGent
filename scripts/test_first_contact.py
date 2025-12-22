#!/usr/bin/env python3
"""Test script for first contact message generation.

Usage:
    # Test prompt only (no API call)
    python scripts/test_first_contact.py --prompt-only

    # Full generation with Gemini API
    python scripts/test_first_contact.py

    # Inside Docker container
    docker compose exec app python /app/scripts/test_first_contact.py
"""
import asyncio
import os
import sys

# Ensure we can import from src
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def test_prompt_only():
    """Test just the prompt generation (no API call)."""
    from argent.story import load_character, PromptBuilder

    persona = load_character("ember")
    builder = PromptBuilder()
    prompt = builder.build_first_contact_prompt(persona, "TEST-1234-ABCD-5678")

    print("=" * 70)
    print("FIRST CONTACT PROMPT")
    print("=" * 70)
    print(prompt)
    print("=" * 70)
    print(f"\nPrompt length: {len(prompt)} characters")


async def test_full_generation():
    """Test full generation with Gemini API."""
    from argent.agents.ember import EmberAgent
    from argent.story import PromptBuilder, load_character

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
        print("\nUsage:")
        print("  GEMINI_API_KEY=xxx python scripts/test_first_contact.py")
        return

    # First show the prompt
    persona = load_character("ember")
    builder = PromptBuilder()
    prompt = builder.build_first_contact_prompt(persona, "TEST-1234-ABCD-5678")

    print("=" * 70)
    print("SYSTEM PROMPT BEING SENT")
    print("=" * 70)
    print(prompt)
    print("=" * 70)

    # Now generate
    print("\nGenerating response from Gemini...")
    agent = EmberAgent(gemini_api_key=api_key)
    response = await agent.generate_first_contact("TEST-1234-ABCD-5678")

    print("\n" + "=" * 70)
    print("LLM RESPONSE")
    print("=" * 70)
    print(f"Subject: {response.subject}")
    print("-" * 70)
    print(response.content)
    print("=" * 70)

    # Analyze response
    print("\n--- ANALYSIS ---")
    issues = []
    content_lower = response.content.lower()

    if "sorry" in content_lower or "apologize" in content_lower or "apologies" in content_lower:
        issues.append("Contains apology (should NOT apologize)")
    if "mistake" in content_lower or "error" in content_lower:
        issues.append("Mentions mistake/error (should NOT)")
    if "wrong" in content_lower and "person" in content_lower:
        issues.append("Mentions wrong person (should NOT)")
    if "wasn't meant for you" in content_lower or "not meant for you" in content_lower:
        issues.append("Says 'not meant for you' (should NOT)")
    if len(response.content) > 200:
        issues.append(f"Too long ({len(response.content)} chars, target: <100)")

    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("No issues detected - response looks good!")


def main():
    if "--prompt-only" in sys.argv:
        test_prompt_only()
    elif "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
    else:
        asyncio.run(test_full_generation())


if __name__ == "__main__":
    main()
