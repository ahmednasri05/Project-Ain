"""
Example: Print comment text structure for a given Instagram reel
Uses the comment_parser service to fetch and format comments.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.comment_parser import get_comments_for_sentiment_analysis

async def print_comments_text_structure(shortcode: str):
    """
    Example workflow: Fetch comments for a reel and print the text structure.
    Args:
        shortcode: Instagram reel shortcode
    """
    print(f"\n{'='*60}")
    print(f"Comment Text Structure Example: Reel {shortcode}")
    print(f"{'='*60}\n")

    # Fetch and format comments (text structure)
    comments_text = await get_comments_for_sentiment_analysis(
        shortcode,
        format_type="text",
        include_metadata=True,
        include_replies=True,
        max_depth=2
    )

    print("Comments structure:\n")
    print(comments_text)
    print(f"\n{'='*60}\n")

async def main():
    """Run the simple comment text print example."""
    EXAMPLE_SHORTCODE = "DRLS0KOAdv2"

    await print_comments_text_structure(EXAMPLE_SHORTCODE)


if __name__ == "__main__":
    asyncio.run(main())
