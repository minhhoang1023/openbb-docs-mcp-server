#!/usr/bin/env python3
"""Test script to verify _find_section_content function"""

import httpx
import asyncio
from server import _find_section_content, FULL_DOCS_URL


async def test_section_extraction():
    """Test extracting specific sections from full docs"""

    # Section titles to test
    test_titles = [
        "Copilot Basics",
        "Generative UI",
        "Dashboards Overview"
    ]

    print("Fetching full documentation...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(FULL_DOCS_URL)
        response.raise_for_status()
        full_docs = response.text

    print(f"\nFull docs loaded: {len(full_docs)} characters\n")
    print("=" * 80)

    for title in test_titles:
        print(f"\n\nSearching for section: '{title}'")
        print("-" * 80)

        content = _find_section_content(full_docs, title)

        if content:
            print(f"✓ Found content for '{title}':")
            print(f"  Length: {len(content)} characters")
            print(f"  Preview (first 500 chars):\n")
            print(content[:500])
            print("\n...")
        else:
            print(f"✗ Section '{title}' not found in documentation")


if __name__ == "__main__":
    asyncio.run(test_section_extraction())
