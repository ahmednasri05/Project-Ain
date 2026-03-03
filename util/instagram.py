"""
Instagram URL Utilities
Shared helpers for parsing Instagram URLs and shortcodes.
"""

import re


def extract_shortcode(input_str: str) -> str:
    """
    Normalize an Instagram URL or bare shortcode to just the shortcode.

    Handles plain shortcodes and all known Instagram URL formats:
        /reel/SHORTCODE/
        /p/SHORTCODE/          (older permalink format)
        /tv/SHORTCODE/         (IGTV)

    Examples:
        "DRLS0KOAdv2"                                    → "DRLS0KOAdv2"
        "https://www.instagram.com/reel/DRLS0KOAdv2/"   → "DRLS0KOAdv2"
        "https://www.instagram.com/p/DRLS0KOAdv2/"      → "DRLS0KOAdv2"
        "https://www.instagram.com/reel/DRLS0KOAdv2/?igsh=abc" → "DRLS0KOAdv2"

    Args:
        input_str: Raw Instagram URL or bare shortcode

    Returns:
        str: Bare shortcode
    """
    input_str = input_str.strip()
    if input_str.startswith("http"):
        match = re.search(r"/(?:reel|p|tv)/([A-Za-z0-9_-]+)", input_str)
        if match:
            return match.group(1)
        # URL recognised but pattern not matched — return as-is and let
        # the caller handle it; the shortcode check will simply find nothing.
    return input_str


def is_instagram_url(url: str) -> bool:
    """
    Return True if the URL points to Instagram (or is a bare shortcode).

    Args:
        url: Raw user input

    Returns:
        bool: True if the input is an Instagram URL or bare shortcode
    """
    url = url.strip()
    if not url.startswith("http"):
        return True
    return "instagram.com" in url
