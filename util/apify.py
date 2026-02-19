"""
Apify Client Utility
Runs the instagram-scraper actor and polls until results are ready.
"""

import asyncio
import os
import aiohttp
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
APIFY_BASE_URL = "https://api.apify.com/v2"
ACTOR_ID = "apify~instagram-scraper"

# Polling config
POLL_INTERVAL_SECONDS = 3
MAX_WAIT_SECONDS = 120


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
    params = {"token": APIFY_TOKEN}
    payload = {
        "directUrls": [url],
        "resultsType": "posts",
        "resultsLimit": 1,
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


async def _poll_run(run_id: str) -> str:
    """
    Poll the run status every POLL_INTERVAL_SECONDS until terminal state.

    Args:
        run_id: Apify run ID

    Returns:
        Final status string: "SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"
    """
    endpoint = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
    params = {"token": APIFY_TOKEN}
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


async def _fetch_results(run_id: str) -> list:
    """
    Fetch dataset items from a completed run.

    Args:
        run_id: Apify run ID

    Returns:
        List of raw result items from Apify
    """
    endpoint = f"{APIFY_BASE_URL}/actor-runs/{run_id}/dataset/items"
    params = {"token": APIFY_TOKEN, "format": "json"}

    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint, params=params) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Failed to fetch results ({response.status}): {text}")

            results = await response.json()
            
            # Debug: Save raw response to file for inspection
            import json
            debug_file = f"apify_debug_{run_id}.json"
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"[Apify] Debug: Saved raw response to {debug_file}")
            
            return results


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

    # 1. Start actor run
    run_id = await _start_actor_run(url)

    # 2. Poll until finished
    final_status = await _poll_run(run_id)

    if final_status != "SUCCEEDED":
        raise Exception(f"Apify run {run_id} ended with status: {final_status}")

    # 3. Fetch results
    items = await _fetch_results(run_id)

    if not items:
        print(f"[Apify] No results returned for: {url}")
        return None

    raw = items[0]

    # Debug: Log available fields to help diagnose missing videoUrl
    print(f"[Apify] Raw response has {len(raw)} fields")
    print(f"[Apify] All fields: {', '.join(sorted(raw.keys()))}")
    
    if "videoUrl" not in raw or not raw.get("videoUrl"):
        print(f"\n[Apify] ⚠️  WARNING: videoUrl missing or empty!")
        print(f"[Apify] Available video/URL fields:")
        for key in sorted(raw.keys()):
            if "video" in key.lower() or "url" in key.lower() or "display" in key.lower():
                value = raw[key]
                if isinstance(value, str) and len(value) > 100:
                    print(f"  - {key}: {value[:100]}...")
                else:
                    print(f"  - {key}: {value}")
    else:
        print(f"[Apify] videoUrl found: {raw['videoUrl'][:80]}..." if len(raw.get('videoUrl', '')) > 80 else f"[Apify] videoUrl found: {raw.get('videoUrl')}")

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
