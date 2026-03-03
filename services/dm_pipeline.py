"""
DM Pipeline
Lightweight pipeline for reels received via Instagram Direct Messages.

Skips Apify scraping, DB storage, fingerprinting, and sentiment gating.
Flow:
  1. Download video from the CDN URL provided in the DM webhook payload
  2. Extract audio
  3. Run AI analysis (video + audio in parallel)
  4. Save JSON + HTML report to output/
  5. Persist pipeline_run + processed_crime_report to Supabase
"""

import os
import asyncio
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional

from util.helpers_ytdlp import download_video_ytdlp as download_video, extract_audio
from ai.media_processor import MediaProcessor
from db import insert_pipeline_run, update_pipeline_run, save_processed_crime_report

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
        asset_id:   Numeric reel_video_id, used as the filename stem and DB shortcode

    Returns:
        Result dict with keys: status, asset_id, danger_score, crimes,
        sentiment, recommended_action
    """
    print(f"\n{'='*60}")
    print(f"[DM Pipeline] Processing asset: {asset_id}")
    print(f"{'='*60}")
    if caption:
        preview = caption[:120].replace("\n", " ")
        print(f"  Caption: {preview}{'...' if len(caption) > 120 else ''}")

    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    run_id: Optional[int] = None
    start_time = datetime.now(timezone.utc)
    _result: dict = {"status": "error", "asset_id": asset_id, "reason": "pipeline did not complete"}

    try:
        run_id = await insert_pipeline_run(asset_id)

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

        print(f"  → Saving crime report to database...")
        await save_processed_crime_report(shortcode=asset_id, media_analysis_result=analysis)
        print(f"  ✓ Crime report saved")

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n[DM Pipeline] Done in {elapsed:.1f}s")

        _result = {
            "status": "success",
            "asset_id": asset_id,
            "danger_score": danger,
            "crimes": len(crimes),
            "sentiment": sentiment,
            "recommended_action": action,
        }
        return _result

    except Exception as e:
        logger.exception(f"[DM Pipeline] Failed for asset {asset_id} after {(datetime.now(timezone.utc) - start_time).total_seconds():.1f}s: {e}")
        print(f"\n  ✗ Error: {e}")
        traceback.print_exc()
        _result = {
            "status": "error",
            "asset_id": asset_id,
            "reason": str(e),
        }
        return _result

    finally:
        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        if run_id is not None:
            status = _result.get("status", "error")
            run_update: dict = {
                "status": status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": duration_ms,
            }
            if status == "success":
                run_update["danger_score"] = _result.get("danger_score")
                run_update["crimes_count"] = _result.get("crimes")
                run_update["recommended_action"] = _result.get("recommended_action")
            elif status == "error":
                run_update["error_reason"] = _result.get("reason")
            try:
                await update_pipeline_run(run_id, run_update)
            except Exception as log_err:
                logger.warning(f"[DM Pipeline] failed to update pipeline_run {run_id}: {log_err}")

        for path in [video_path, audio_path]:
            if path and os.path.exists(path):
                for attempt in range(5):
                    try:
                        os.remove(path)
                        print(f"  [cleanup] removed {os.path.basename(path)}")
                        break
                    except PermissionError:
                        if attempt < 4:
                            await asyncio.sleep(0.3)
                        else:
                            print(f"  [cleanup] could not remove {os.path.basename(path)} — file still locked")
