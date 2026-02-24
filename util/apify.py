"""
Apify Client Utility
Runs the instagram-scraper actor and polls until results are ready.
"""

import asyncio
import os
import json
import re
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
MAX_WAIT_SECONDS = 300  # increased for large batches

# Request counter for token rotation (every 5 requests)
_request_counter = 0


def _get_next_token() -> str:
    """Rotates to the next token every 5 requests."""
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


def _bare_shortcode(value: str) -> str:
    """
    Extract bare shortcode from either a raw shortcode or a full Instagram URL.
    e.g. "https://www.instagram.com/reel/DRLS0KOAdv2/" → "DRLS0KOAdv2"
    e.g. "DRLS0KOAdv2" → "DRLS0KOAdv2"
    """
    if value.startswith("http"):
        match = re.search(r"/(?:reel|p|tv)/([A-Za-z0-9_-]+)", value)
        if match:
            return match.group(1)
    return value


async def _start_batch_run(urls: list[str]) -> tuple[str, str]:
    """
    Start the Apify instagram-scraper actor with one or more URLs.

    Args:
        urls: List of full Instagram permalinks

    Returns:
        (run_id, token) — token is stored so the same one is used for polling/fetching
    """
    endpoint = f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/runs"
    token = _get_next_token()
    params = {"token": token}
    payload = {
        "directUrls": urls,
        "resultsType": "posts",
        "resultsLimit": 1,      # 1 result per URL (we target specific posts)
        "includeComments": True,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, params=params, json=payload) as response:
            if response.status not in (200, 201):
                text = await response.text()
                raise Exception(f"Failed to start Apify run ({response.status}): {text}")

            data = await response.json()
            run_id = data["data"]["id"]
            print(f"[Apify] Run started: {run_id} ({len(urls)} URL(s))")
            return run_id, token


async def _poll_run(run_id: str, token: str) -> str:
    """
    Poll the run status every POLL_INTERVAL_SECONDS until terminal state.

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
    """Fetch dataset items from a completed run."""
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
    """
    return raw.get("latestComments") or raw.get("comments") or []


def _normalize_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Apify's raw output to the schema expected by save_reel().
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


async def scrape_reels_batch(shortcodes: list[str]) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Scrape multiple reels in a single Apify actor run.

    Args:
        shortcodes: List of bare shortcodes (already normalized — no full URLs).
                    Use _bare_shortcode() to normalize before calling this.

    Returns:
        Mapping of shortcode -> {"reel": ..., "comments": ...}
        Value is None for any shortcode that produced no result in the dataset.

    Example:
        results = await scrape_reels_batch(["DRLS0KOAdv2", "ABC123XYZ"])
        for sc, data in results.items():
            if data:
                print(sc, data["reel"]["ownerUsername"])
    """
    if not shortcodes:
        return {}

    urls = [_shortcode_to_url(sc) for sc in shortcodes]
    print(f"[Apify] Starting batch run for {len(urls)} URL(s)")

    run_id, token = await _start_batch_run(urls)
    final_status = await _poll_run(run_id, token)

    if final_status != "SUCCEEDED":
        raise Exception(f"Apify batch run {run_id} ended with status: {final_status}")

    items = await _fetch_results(run_id, token)

    # Index results by shortCode
    results_by_sc: Dict[str, Dict] = {}
    for item in items:
        sc = item.get("shortCode", "")
        if sc:
            reel = _normalize_payload(item)
            comments = _extract_comments(item)
            results_by_sc[sc] = {"reel": reel, "comments": comments}
            print(f"[Apify] ✓ @{reel['ownerUsername']} / {sc} ({len(comments)} comment(s))")

    # Build final mapping — None for any shortcode with no matching result
    final: Dict[str, Optional[Dict]] = {}
    for sc in shortcodes:
        r = results_by_sc.get(sc)
        if r is None:
            print(f"[Apify] ✗ No result for: {sc}")
        final[sc] = r

    return final


async def scrape_reel(shortcode: str) -> Optional[Dict[str, Any]]:
    """
    Scrape a single Instagram reel by shortcode or permalink.
    Thin wrapper around scrape_reels_batch kept for backward compatibility.

    Args:
        shortcode: Instagram shortcode (e.g. "DRLS0KOAdv2")
                   or full permalink (e.g. "https://www.instagram.com/reel/DRLS0KOAdv2/")

    Returns:
        Dict with keys "reel" and "comments", or None if no result found.
    """
    bare = _bare_shortcode(shortcode)
    results = await scrape_reels_batch([bare])
    return results.get(bare)
