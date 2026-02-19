"""
Main Pipeline
Orchestrates the full processing flow for Instagram reels:
  1. Apify scrape (metadata + video URL + comments)
  2. Download video
  3. Extract audio
  4. Fingerprint + duplicate check
  5. Upload video to Supabase storage
  6. Save reel & comments to database
  7. AI analysis (video + audio in parallel)
"""

import os
import sys
import asyncio
from typing import Optional, Dict, Any

# Add src/ to path so MediaProcessor (and its relative imports) resolve correctly
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_BASE_DIR, "src"))

from util.apify import scrape_reel, scrape_reels
from util.helpers_ytdlp import download_video_ytdlp as download_video, extract_audio
from db import save_reel, bulk_save_comments, upload_to_supabase, get_storage_bucket
from .video_fingerprint import generate_video_fingerprint, check_and_save_fingerprints
from models.media_processor import MediaProcessor


async def process_single_reel(shortcode: str) -> Dict[str, Any]:
    """
    Run the full pipeline for a single Instagram reel.

    Args:
        shortcode: Instagram shortcode or full permalink

    Returns:
        Result dict with keys:
            status: "success" | "duplicate" | "error"
            shortcode: resolved Instagram shortcode
            + status-specific fields (see below)

    Success fields:
        reel_id, danger_score, crimes, sentiment, recommended_action

    Duplicate fields:
        original (shortcode of the original), similarity (0.0-1.0)

    Error fields:
        reason (error message string)
    """
    print(f"\n{'='*60}")
    print(f"[Pipeline] Processing: {shortcode}")
    print(f"{'='*60}")

    video_path = None
    audio_path = None

    try:
        # ── Step 1: Apify scrape ──────────────────────────────────────
        print("\n[1/7] Scraping with Apify...")
        print(f"  → Input shortcode: '{shortcode}'")
        result = await scrape_reel(shortcode)

        if not result:
            return {"status": "error", "shortcode": shortcode, "reason": "Apify returned no results"}

        reel_payload = result["reel"]
        comments = result["comments"]
        shortcode = reel_payload["shortCode"]  # use the canonical shortcode from Apify

        print(f"  ✓ @{reel_payload['ownerUsername']} / {shortcode}")
        print(f"  ✓ {len(comments)} comment(s) fetched")

        # ── Step 2: Download video ────────────────────────────────────
        print("\n[2/7] Downloading video...")
        if not reel_payload.get("videoUrl"):
            raise ValueError(f"No video URL found in reel data. Apify may have failed to scrape the video.")
        
        video_url = reel_payload['videoUrl']
        print(f"  → URL: {video_url}")
        print(f"  → URL valid: {'YES' if video_url.startswith(('http://', 'https://')) else 'NO - MALFORMED!'}")
        
        video_path = await download_video(video_url, shortcode)
        print(f"  ✓ {video_path}")

        # ── Step 3: Extract audio ─────────────────────────────────────
        print("\n[3/7] Extracting audio...")
        audio_path = await extract_audio(video_path, shortcode)
        print(f"  ✓ {audio_path}")

        # ── Step 4: Fingerprint + duplicate check ─────────────────────
        print("\n[4/7] Checking for duplicates...")
        fingerprints = await generate_video_fingerprint(video_path)
        dup_result = await check_and_save_fingerprints(shortcode, fingerprints)

        if dup_result["is_duplicate"]:
            original = dup_result["duplicates"][0]["shortcode"]
            similarity = dup_result["duplicates"][0]["similarity"]
            print(f"  ⚠ Duplicate of {original} ({similarity:.0%} similar) - skipping")
            return {
                "status": "duplicate",
                "shortcode": shortcode,
                "original": original,
                "similarity": similarity,
            }

        print(f"  ✓ Unique video ({dup_result['fingerprints_count']} fingerprints saved)")

        # ── Step 5: Upload video + audio to Supabase storage ─────────
        print("\n[5/7] Uploading to storage...")
        bucket = get_storage_bucket()
        video_remote = f"videos/{shortcode}.mp4"
        audio_remote = f"audio/{shortcode}.mp3"

        video_storage_path, audio_storage_path = await asyncio.gather(
            upload_to_supabase(video_path, bucket, video_remote),
            upload_to_supabase(audio_path, bucket, audio_remote),
        )
        print(f"  ✓ video → {bucket}/{video_storage_path}")
        print(f"  ✓ audio → {bucket}/{audio_storage_path}")

        # ── Step 6: Save reel + comments to DB ───────────────────────
        print("\n[6/7] Saving to database...")
        reel_record = await save_reel(reel_payload, video_storage_path, audio_storage_path)
        print(f"  ✓ Reel saved (DB id: {reel_record['id']})")

        if comments:
            total = await bulk_save_comments(comments, shortcode)
            print(f"  ✓ {total} comment(s) saved")
        else:
            print("  – No comments to save")

        # ── Step 7: AI analysis ───────────────────────────────────────
        print("\n[7/7] Running AI analysis (video + audio in parallel)...")
        processor = MediaProcessor()
        analysis = await processor.process_media(
            video_path=video_path,
            audio_path=audio_path,
            language="ar",
        )

        danger = analysis.video_analysis.danger_score
        crimes = analysis.video_analysis.possible_crimes
        sentiment = analysis.audio_analysis.sentiment
        action = analysis.recommended_action

        print(f"  ✓ Danger score : {danger}/10")
        print(f"  ✓ Crimes found : {len(crimes)}")
        print(f"  ✓ Sentiment    : {sentiment}")
        print(f"  ✓ Action       : {action}")

        return {
            "status": "success",
            "shortcode": shortcode,
            "reel_id": reel_record["id"],
            "danger_score": danger,
            "crimes": len(crimes),
            "sentiment": sentiment,
            "recommended_action": action,
        }

    except Exception as e:
        print(f"\n  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "shortcode": shortcode, "reason": str(e)}

    finally:
        # Always remove temp files regardless of success or failure
        for path in [video_path, audio_path]:
            if path and os.path.exists(path):
                os.remove(path)
                print(f"  [cleanup] removed {os.path.basename(path)}")


def _print_summary(shortcodes: list, results: list) -> None:
    """Print a formatted summary table after a batch run."""
    print(f"\n{'='*60}")
    print("BATCH SUMMARY")
    print(f"{'='*60}")
    for sc, r in zip(shortcodes, results):
        if isinstance(r, Exception):
            print(f"  ✗  {sc:<25} ERROR: {r}")
            continue
        status = r.get("status")
        sc_label = r.get("shortcode", sc)
        if status == "success":
            print(
                f"  ✓  {sc_label:<25} "
                f"danger={r['danger_score']}/10  "
                f"crimes={r['crimes']}  "
                f"action={r['recommended_action']}"
            )
        elif status == "duplicate":
            print(f"  ⚠  {sc_label:<25} duplicate of {r['original']} ({r['similarity']:.0%})")
        else:
            print(f"  ✗  {sc_label:<25} {r.get('reason', 'unknown error')}")
    print()


async def run_pipeline() -> None:
    """
    Interactive entry point.
    Prompts for one or more shortcodes/permalinks, processes them concurrently,
    then loops for the next batch.

    Usage:
        python app.py
    Input examples:
        DRLS0KOAdv2
        DRLS0KOAdv2, ABC123XYZ, GHI789
        https://www.instagram.com/reel/DRLS0KOAdv2/
    """
    print("\n" + "=" * 60)
    print("  PROJECT AIN — CYBERCRIME MONITORING PIPELINE")
    print("=" * 60)
    print("Enter one or more Instagram shortcodes or permalinks.")
    print("Separate multiple inputs with commas.")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("Shortcode(s) › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Exiting pipeline.")
            break

        shortcodes = [s.strip() for s in user_input.split(",") if s.strip()]

        if len(shortcodes) == 1:
            results = [await process_single_reel(shortcodes[0])]
        else:
            print(f"\n[Pipeline] Running {len(shortcodes)} reels concurrently...\n")
            raw_results = await asyncio.gather(
                *[process_single_reel(sc) for sc in shortcodes],
                return_exceptions=True,
            )
            results = list(raw_results)

        _print_summary(shortcodes, results)
