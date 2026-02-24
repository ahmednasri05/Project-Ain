"""
DM Pipeline
Lightweight pipeline for reels received via Instagram Direct Messages.

Skips Apify scraping, DB storage, fingerprinting, and sentiment gating.
Flow:
  1. Download video from the CDN URL provided in the DM webhook payload
  2. Extract audio
  3. Run AI analysis (video + audio in parallel)
  4. Save JSON + HTML report to output/
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from util.helpers_ytdlp import download_video_ytdlp as download_video, extract_audio
from ai.media_processor import MediaProcessor

logger = logging.getLogger(__name__)


async def run_dm_pipeline(
    video_url: str,
    caption: str,
    asset_id: str,
) -> dict:
    """
    Run the DM pipeline for a single reel received via Instagram DM.

    Args:
        video_url:  Direct CDN URL from the webhook payload's attachments[].payload.url
        caption:    Reel caption from attachments[].payload.title
        asset_id:   Numeric reel_video_id, used as the filename stem

    Returns:
        Result dict with keys: status, asset_id, danger_score, crimes,
        sentiment, recommended_action, output_file
    """
    print(f"\n{'='*60}")
    print(f"[DM Pipeline] Processing asset: {asset_id}")
    print(f"{'='*60}")
    if caption:
        preview = caption[:120].replace("\n", " ")
        print(f"  Caption: {preview}{'...' if len(caption) > 120 else ''}")

    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    start_time = datetime.now()

    try:
        # ── Step 1: Download video ────────────────────────────────────
        print("\n[1/3] Downloading video...")
        print(f"  → URL: {video_url[:80]}...")
        video_path = await download_video(video_url, asset_id)
        print(f"  ✓ {video_path}")

        # ── Step 2: Extract audio ─────────────────────────────────────
        print("\n[2/3] Extracting audio...")
        audio_path = await extract_audio(video_path, asset_id)
        if audio_path:
            print(f"  ✓ {audio_path}")
        else:
            print("  – No audio track — audio analysis will be skipped")

        # ── Step 3: AI analysis ───────────────────────────────────────
        print("\n[3/3] Running AI analysis (video + audio in parallel)...")
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

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n[DM Pipeline] Done in {elapsed:.1f}s")

        return {
            "status": "success",
            "asset_id": asset_id,
            "danger_score": danger,
            "crimes": len(crimes),
            "sentiment": sentiment,
            "recommended_action": action,
        }

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.exception(f"[DM Pipeline] Failed for asset {asset_id} after {elapsed:.1f}s: {e}")
        print(f"\n  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "asset_id": asset_id,
            "reason": str(e),
        }
