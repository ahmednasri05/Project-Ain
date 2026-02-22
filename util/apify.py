"""
Apify Client Utility
Runs the instagram-scraper actor and polls until results are ready.
"""

import asyncio
import os
import json
import aiohttp
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Parse token list from environment variable
_apify_token_env = os.getenv("APIFY_API_TOKEN")
if _apify_token_env:
    try:
        APIFY_TOKENS = json.loads(_apify_token_env)
        if not isinstance(APIFY_TOKENS, list) or not APIFY_TOKENS:
            raise ValueError("APIFY_API_TOKEN must be a non-empty JSON array")
    except json.JSONDecodeError:
        # Fallback: treat as single token for backward compatibility
        APIFY_TOKENS = [_apify_token_env]
else:
    raise ValueError("APIFY_API_TOKEN environment variable not set")

APIFY_BASE_URL = "https://api.apify.com/v2"
ACTOR_ID = "apify~instagram-scraper"

# Polling config
POLL_INTERVAL_SECONDS = 3
MAX_WAIT_SECONDS = 120

# Request counter for token rotation (every 5 requests)
_request_counter = 0


def _get_next_token() -> str:
    """
    Get the next token in rotation.
    Rotates to the next token every 5 requests.
    """
    global _request_counter
    token_index = (_request_counter // 5) % len(APIFY_TOKENS)
    _request_counter += 1
    selected_token = APIFY_TOKENS[token_index]
    print(f"[Apify] Using token {token_index + 1}/{len(APIFY_TOKENS)} (request #{_request_counter})")
    return selected_token


def _shortcode_to_url(shortcode: str) -> str:
    """
    Accept either a raw shortcode or a full permalink and always return a full URL.
    e.g. "DRLS0KOAdv2" → "https://www.instagram.com/reel/DRLS0KOAdv2/"
    e.g. "https://www.instagram.com/reel/DRLS0KOAdv2/" → unchanged
    """
    if shortcode.startswith("http"):
        return shortcode
    return f"https://www.instagram.com/reel/{shortcode}/"


async def _start_actor_run(url: str) -> str:
    """
    Start the Apify instagram-scraper actor run.

    Args:
        url: Full Instagram permalink

    Returns:
        run_id: Apify run ID to poll
    """
    endpoint = f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/runs"
    token = _get_next_token()
    params = {"token": token}
    payload = {
        "directUrls": [url],
        "resultsType": "posts",
        "resultsLimit": 12,
        "includeComments": True,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, params=params, json=payload) as response:
            if response.status not in (200, 201):
                text = await response.text()
                raise Exception(f"Failed to start Apify run ({response.status}): {text}")

            data = await response.json()
            run_id = data["data"]["id"]
            print(f"[Apify] Run started: {run_id}")
            return run_id


async def _poll_run(run_id: str, token: str) -> str:
    """
    Poll the run status every POLL_INTERVAL_SECONDS until terminal state.

    Args:
        run_id: Apify run ID
        token: The token used to start the run

    Returns:
        Final status string: "SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"
    """
    endpoint = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
    params = {"token": token}
    terminal_states = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}

    elapsed = 0
    async with aiohttp.ClientSession() as session:
        while elapsed < MAX_WAIT_SECONDS:
            async with session.get(endpoint, params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Failed to poll run status ({response.status}): {text}")

                data = await response.json()
                status = data["data"]["status"]
                print(f"[Apify] Run {run_id} → {status} ({elapsed}s elapsed)")

                if status in terminal_states:
                    return status

            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS

    raise TimeoutError(f"Apify run {run_id} did not finish within {MAX_WAIT_SECONDS}s")


async def _fetch_results(run_id: str, token: str) -> list:
    """
    Fetch dataset items from a completed run.

    Args:
        run_id: Apify run ID
        token: The token used to start the run

    Returns:
        List of raw result items from Apify
    """
    endpoint = f"{APIFY_BASE_URL}/actor-runs/{run_id}/dataset/items"
    params = {"token": token, "format": "json"}

    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint, params=params) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Failed to fetch results ({response.status}): {text}")

            return await response.json()


def _extract_comments(raw: Dict[str, Any]) -> list:
    """
    Extract comments list from raw Apify result.
    Apify returns comments under 'latestComments' (or 'comments' in some actor versions).
    The structure already matches what save_comment_thread() expects.
    """
    return raw.get("latestComments") or raw.get("comments") or []


def _normalize_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Apify's raw output to the schema expected by save_reel() in db/instagram_db.py.

    Raw Apify field names already match the project's convention so this is mostly
    a passthrough with safety fallbacks for optional fields.
    """
    return {
        "id":               raw.get("id", ""),
        "shortCode":        raw.get("shortCode", ""),
        "caption":          raw.get("caption", ""),
        "ownerId":          raw.get("ownerId", ""),
        "ownerUsername":    raw.get("ownerUsername", ""),
        "timestamp":        raw.get("timestamp", ""),
        "videoUrl":         raw.get("videoUrl", ""),
        "videoViewCount":   raw.get("videoViewCount", 0),
        "videoPlayCount":   raw.get("videoPlayCount", 0),
        "likesCount":       raw.get("likesCount", -1),
        "commentsCount":    raw.get("commentsCount", 0),
        "videoDuration":    raw.get("videoDuration", 0.0),
    }


async def scrape_reel(shortcode: str) -> Optional[Dict[str, Any]]:
    """
    Main entry point: scrape a single Instagram reel by shortcode or permalink.
    Starts an Apify actor run, polls until done, and returns normalized payload.

    Args:
        shortcode: Instagram shortcode (e.g. "DRLS0KOAdv2")
                   or full permalink (e.g. "https://www.instagram.com/reel/DRLS0KOAdv2/")

    Returns:
        Dict with keys:
            "reel":     normalized reel dict ready for save_reel()
            "comments": list of comment dicts ready for bulk_save_comments()
        Or None if no results found.

    Example:
        result = await scrape_reel("DRLS0KOAdv2")
        print(result["reel"]["videoUrl"])
        print(len(result["comments"]), "comments")
    """
    url = _shortcode_to_url(shortcode)
    print(f"[Apify] Scraping: {url}")

    # 1. Start actor run (this will rotate the token)
    run_id = await _start_actor_run(url)
    
    # Store the token for this specific run
    token = APIFY_TOKENS[(_request_counter - 1) // 5 % len(APIFY_TOKENS)]

    # 2. Poll until finished
    final_status = await _poll_run(run_id, token)

    if final_status != "SUCCEEDED":
        raise Exception(f"Apify run {run_id} ended with status: {final_status}")

    # 3. Fetch results
    items = await _fetch_results(run_id, token)

    if not items:
        print(f"[Apify] No results returned for: {url}")
        return None

    raw = items[0]

    # 4. Normalize reel and extract comments
    reel = _normalize_payload(raw)
    comments = _extract_comments(raw)

    print(f"[Apify] Done → @{reel['ownerUsername']} / {reel['shortCode']} ({len(comments)} comments)")
    return {"reel": reel, "comments": comments}


async def scrape_reels(shortcodes: list[str]) -> list[Dict[str, Any]]:
    """
    Scrape multiple reels concurrently.

    Args:
        shortcodes: List of shortcodes or permalinks

    Returns:
        List of {"reel": ..., "comments": ...} dicts (failed entries filtered out)

    Example:
        results = await scrape_reels(["DRLS0KOAdv2", "ABC123XYZ"])
        for r in results:
            print(r["reel"]["shortCode"], len(r["comments"]), "comments")
    """
    results = await asyncio.gather(
        *[scrape_reel(sc) for sc in shortcodes],
        return_exceptions=True
    )

    payloads = []
    for shortcode, result in zip(shortcodes, results):
        if isinstance(result, Exception):
            print(f"[Apify] Error scraping {shortcode}: {result}")
        elif result is not None:
            payloads.append(result)

    return payloads
