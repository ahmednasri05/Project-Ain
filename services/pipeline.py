"""
Main Pipeline
Orchestrates the full processing flow for Instagram reels:
  0. Shortcode existence check (bail if already in DB)
  1. Apify scrape (metadata + video URL + comments)
  2. Download video
  3. Extract audio
  4. Fingerprint + duplicate check
  5. Upload video to Supabase storage
  6. Save reel & comments to database
  6b. Save fingerprints
  6c. Comment sentiment gate (bail if SPAM_SARCASM)
  7. AI analysis (video + audio in parallel)
"""

import os
import re
import asyncio
import httpx
import aiohttp
from datetime import datetime, timezone
from typing import Optional, Dict, Any

MAX_ATTEMPTS = 3

# Exceptions that are transient and worth retrying.
# Anything not in this tuple is a permanent failure (bad data, auth error, etc.)
# and will not be retried.
RETRYABLE_ERRORS = (
    ConnectionError,
    TimeoutError,
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.NetworkError,
    aiohttp.ClientConnectionError,
    aiohttp.ServerDisconnectedError,
    aiohttp.ServerTimeoutError,
)

# Human-readable labels for each internal step number (used in failed_requests)
_STEP_LABELS = {
    1: "step_1_apify",
    2: "step_2_download",
    3: "step_3_audio",
    4: "step_4_fingerprint",
    5: "step_5_upload",
    6: "step_6_save_reel",
    7: "step_7_save_fingerprints",
    8: "step_8_sentiment",
    9: "step_9_ai_analysis",
}

from util.apify import scrape_reel, scrape_reels
from util.helpers_ytdlp import download_video_ytdlp as download_video, extract_audio
from db import (
    save_reel, bulk_save_comments, upload_to_supabase, get_storage_bucket,
    get_reel_by_shortcode, increment_mention_count,
    insert_pipeline_run, update_pipeline_run, insert_failed_request,
)
from .video_fingerprint import generate_video_fingerprint, check_for_duplicates, save_fingerprints
from .comment_formatter import get_comments_for_sentiment_analysis
from ai.media_processor import MediaProcessor
from ai.sentiment_analyzer import SentimentAnalyzer


def _extract_shortcode(input_str: str) -> str:
    """
    Normalize user input to a bare shortcode.
    Handles plain shortcodes and all known Instagram URL formats:
        /reel/SHORTCODE/
        /p/SHORTCODE/          (older permalink format)
        /tv/SHORTCODE/         (IGTV)

    Examples:
        "DRLS0KOAdv2"                                    → "DRLS0KOAdv2"
        "https://www.instagram.com/reel/DRLS0KOAdv2/"   → "DRLS0KOAdv2"
        "https://www.instagram.com/p/DRLS0KOAdv2/"      → "DRLS0KOAdv2"
        "https://www.instagram.com/reel/DRLS0KOAdv2/?igsh=abc" → "DRLS0KOAdv2"
    """
    input_str = input_str.strip()
    if input_str.startswith("http"):
        match = re.search(r"/(?:reel|p|tv)/([A-Za-z0-9_-]+)", input_str)
        if match:
            return match.group(1)
        # URL recognised but pattern not matched — return as-is and let
        # Apify handle it; the shortcode check will simply find nothing.
    return input_str


async def process_single_reel(
    shortcode: str,
    skip_sentiment: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Run the full pipeline for a single Instagram reel.

    Args:
        shortcode:       Instagram shortcode or full permalink
        skip_sentiment:  If True, bypass the comment sentiment gate (step 8)
                         and proceed directly to AI analysis. Useful for reels
                         where comments are absent, irrelevant, or already reviewed.
        force:           If True, skip the shortcode existence check (step 0) and
                         the fingerprint duplicate check (step 4), forcing full
                         reprocessing even if the reel is already in the database.
                         Does NOT increment mention_count — this is a manual operation.

    Returns:
        Result dict with keys:
            status: "success" | "already_processed" | "repost" | "filtered" | "error"
            shortcode: resolved Instagram shortcode
            + status-specific fields (see below)

    Success fields:
        reel_id, danger_score, crimes, sentiment, recommended_action

    Already-processed fields:
        reel_id (DB id of the existing record)

    Repost fields:
        original (shortcode of the original), similarity (0.0-1.0),
        comments_saved (int — new comments saved under the original incident)

    Filtered fields:
        reel_id, sentiment_label ("SPAM_SARCASM"), sentiment_explanation

    Error fields:
        reason (error message string)
    """
    print(f"\n{'='*60}")
    print(f"[Pipeline] Processing: {shortcode}")
    print(f"{'='*60}")

    # ── Persistent state (survives across retry iterations) ──────────
    video_path        = None
    audio_path        = None
    reel_payload      = None
    comments          = None
    fingerprints      = None
    reel_record       = None
    video_storage_path = None
    audio_storage_path = None

    _result: Dict[str, Any] = {"status": "error", "shortcode": shortcode, "reason": "pipeline did not complete"}
    _run_id:    Optional[int] = None
    _start_time = datetime.now()
    _attempts   = 0       # total retryable failures across all steps
    _current_step = 0     # which step to (re-)enter on next loop iteration

    try:
        # ── Step 0: Shortcode check (no retry — fast, non-destructive) ─
        shortcode = _extract_shortcode(shortcode)
        _result["shortcode"] = shortcode
        _run_id = await insert_pipeline_run(shortcode)

        print(f"\n[0/7] Checking if already processed...")
        if force:
            print(f"  – Skipped (--force flag)")
        else:
            existing = await get_reel_by_shortcode(shortcode)
            if existing:
                await increment_mention_count(shortcode)
                print(f"  ⚠ Already processed (DB id: {existing['id']}) — mention_count incremented")
                _result = {"status": "already_processed", "shortcode": shortcode, "reel_id": existing["id"]}
                return _result
            print(f"  ✓ Not seen before, continuing")

        _current_step = 1

        # ── Retry loop ────────────────────────────────────────────────
        # Each iteration executes exactly one step. On a retryable error
        # the step number stays the same and the loop retries it.
        # On success the step advances. Non-retryable errors propagate
        # immediately to the outer except.
        while True:

            try:
                # ── Step 1: Apify scrape ──────────────────────────────
                if _current_step == 1:
                    print("\n[1/7] Scraping with Apify...")
                    print(f"  → Input shortcode: '{shortcode}'")
                    result = await scrape_reel(shortcode)

                    if not result:
                        _result = {"status": "error", "shortcode": shortcode, "reason": "Apify returned no results"}
                        return _result

                    reel_payload = result["reel"]
                    comments     = result["comments"]
                    shortcode    = reel_payload["shortCode"]
                    print(f"  ✓ @{reel_payload['ownerUsername']} / {shortcode}")
                    print(f"  ✓ {len(comments)} comment(s) fetched")
                    _current_step = 2

                # ── Step 2: Download video ────────────────────────────
                elif _current_step == 2:
                    print("\n[2/7] Downloading video...")
                    if not reel_payload.get("videoUrl"):
                        raise ValueError("No video URL found in reel data.")
                    video_url = reel_payload["videoUrl"]
                    print(f"  → URL: {video_url}")
                    print(f"  → URL valid: {'YES' if video_url.startswith(('http://', 'https://')) else 'NO - MALFORMED!'}")
                    video_path = await download_video(video_url, shortcode)
                    print(f"  ✓ {video_path}")
                    _current_step = 3

                # ── Step 3: Extract audio ─────────────────────────────
                elif _current_step == 3:
                    print("\n[3/7] Extracting audio...")
                    audio_path = await extract_audio(video_path, shortcode)
                    if audio_path:
                        print(f"  ✓ {audio_path}")
                    else:
                        print(f"  – No audio track — audio analysis will be skipped")
                    _current_step = 4

                # ── Step 4: Fingerprint + duplicate check ─────────────
                elif _current_step == 4:
                    print("\n[4/7] Checking for duplicates...")
                    fingerprints = await generate_video_fingerprint(video_path)

                    if force:
                        print(f"  – Duplicate check skipped (--force flag)")
                    else:
                        dup_result = await check_for_duplicates(fingerprints)

                        if dup_result["is_duplicate"]:
                            original   = dup_result["duplicates"][0]["shortcode"]
                            similarity = dup_result["duplicates"][0]["similarity"]

                            if original == shortcode:
                                await increment_mention_count(shortcode)
                                print(f"  ⚠ Own fingerprints found — reel was processed before (filtered/interrupted)")
                                existing = await get_reel_by_shortcode(shortcode)
                                _result  = {"status": "already_processed", "shortcode": shortcode, "reel_id": existing["id"] if existing else None}
                                return _result

                            print(f"  ⚠ Repost of {original} ({similarity:.0%} similar)")
                            await increment_mention_count(original)
                            print(f"  ✓ mention_count incremented for {original}")

                            comments_saved = 0
                            if comments:
                                print(f"  → Saving {len(comments)} new comment(s) under original incident...")
                                comments_saved = await bulk_save_comments(comments, reel_shortcode=original, source_shortcode=shortcode)
                                print(f"  ✓ {comments_saved} comment(s) saved (source: {shortcode} → incident: {original})")
                            else:
                                print(f"  – No comments to save")

                            _result = {"status": "repost", "shortcode": shortcode, "original": original, "similarity": similarity, "comments_saved": comments_saved}
                            return _result

                        print(f"  ✓ Unique video")
                    _current_step = 5

                # ── Step 5: Upload to Supabase storage ───────────────
                elif _current_step == 5:
                    print("\n[5/7] Uploading to storage...")
                    bucket       = get_storage_bucket()
                    video_remote = f"videos/{shortcode}.mp4"

                    if audio_path:
                        audio_remote = f"audio/{shortcode}.mp3"
                        video_storage_path, audio_storage_path = await asyncio.gather(
                            upload_to_supabase(video_path, bucket, video_remote),
                            upload_to_supabase(audio_path, bucket, audio_remote),
                        )
                        print(f"  ✓ video → {bucket}/{video_storage_path}")
                        print(f"  ✓ audio → {bucket}/{audio_storage_path}")
                    else:
                        video_storage_path = await upload_to_supabase(video_path, bucket, video_remote)
                        audio_storage_path = None
                        print(f"  ✓ video → {bucket}/{video_storage_path}")
                        print(f"  – audio skipped (no audio track)")
                    _current_step = 6

                # ── Step 6: Save reel + comments to DB ───────────────
                elif _current_step == 6:
                    print("\n[6/7] Saving to database...")
                    reel_record = await save_reel(reel_payload, video_storage_path, audio_storage_path)
                    print(f"  ✓ Reel saved (DB id: {reel_record['id']})")

                    if comments:
                        total = await bulk_save_comments(comments, shortcode, source_shortcode=shortcode)
                        print(f"  ✓ {total} comment(s) saved")
                    else:
                        print("  – No comments to save")
                    _current_step = 7

                # ── Step 7: Save fingerprints ─────────────────────────
                elif _current_step == 7:
                    fp_result = await save_fingerprints(shortcode, fingerprints)
                    print(f"  ✓ {fp_result['fingerprints_count']} fingerprint(s) saved")
                    _current_step = 8

                # ── Step 8: Comment sentiment gate ────────────────────
                elif _current_step == 8:
                    if skip_sentiment:
                        print("\n[6c/7] Comment sentiment gate skipped (--skip-sentiment flag)")
                    elif comments:
                        print("\n[6c/7] Running comment sentiment gate...")
                        comments_text    = await get_comments_for_sentiment_analysis(shortcode)
                        sentiment_result = await SentimentAnalyzer().analyze_sentiment(comments_text)
                        print(f"  ✓ Sentiment label : {sentiment_result.label}")
                        print(f"  ✓ Explanation     : {sentiment_result.explanation}")

                        if sentiment_result.label == "SPAM_SARCASM":
                            print(f"  ⚠ Comments classified as SPAM_SARCASM — skipping AI analysis")
                            _result = {
                                "status": "filtered",
                                "shortcode": shortcode,
                                "reel_id": reel_record["id"],
                                "sentiment_label": sentiment_result.label,
                                "sentiment_explanation": sentiment_result.explanation,
                            }
                            return _result

                        print(f"  ✓ Gate passed ({sentiment_result.label}) — proceeding to AI analysis")
                    else:
                        print("\n[6c/7] Comment sentiment gate skipped (no comments)")
                    _current_step = 9

                # ── Step 9: AI analysis ───────────────────────────────
                elif _current_step == 9:
                    print("\n[7/7] Running AI analysis (video + audio in parallel)...")
                    processor = MediaProcessor()
                    analysis  = await processor.process_media(video_path=video_path, audio_path=audio_path, language="ar")

                    danger    = analysis.video_analysis.danger_score
                    crimes    = analysis.video_analysis.possible_crimes
                    sentiment = analysis.audio_analysis.sentiment
                    action    = analysis.recommended_action

                    print(f"  ✓ Danger score : {danger}/10")
                    print(f"  ✓ Crimes found : {len(crimes)}")
                    print(f"  ✓ Sentiment    : {sentiment}")
                    print(f"  ✓ Action       : {action}")

                    _result = {
                        "status": "success",
                        "shortcode": shortcode,
                        "reel_id": reel_record["id"],
                        "danger_score": danger,
                        "crimes": len(crimes),
                        "sentiment": sentiment,
                        "recommended_action": action,
                    }
                    return _result

            except RETRYABLE_ERRORS as e:
                _attempts += 1
                step_label = _STEP_LABELS.get(_current_step, f"step_{_current_step}")

                if _attempts >= MAX_ATTEMPTS:
                    print(f"\n  ✗ {step_label} failed after {MAX_ATTEMPTS} attempts: {e}")
                    print(f"  → Storing in failed_requests for manual reprocessing")
                    try:
                        await insert_failed_request(shortcode, str(e), step_label, _attempts)
                    except Exception as log_err:
                        print(f"  [logger] failed to write failed_request: {log_err}")
                    _result = {"status": "error", "shortcode": shortcode, "reason": f"Failed after {MAX_ATTEMPTS} attempts at {step_label}: {e}"}
                    return _result

                wait = 2 ** _attempts
                print(f"\n  ↻ {step_label} failed (attempt {_attempts}/{MAX_ATTEMPTS}): {e}")
                print(f"  → Retrying in {wait}s...")
                await asyncio.sleep(wait)
                # _current_step unchanged → same step retried on next iteration

    except Exception as e:
        print(f"\n  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        _result = {"status": "error", "shortcode": shortcode, "reason": str(e)}
        return _result

    finally:
        duration_ms = int((datetime.now() - _start_time).total_seconds() * 1000)
        if _run_id is not None:
            try:
                status = _result.get("status", "error")
                run_update: Dict[str, Any] = {
                    "status": status,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "duration_ms": duration_ms,
                }
                if status == "repost":
                    run_update["original_shortcode"] = _result.get("original")
                    run_update["similarity"] = _result.get("similarity")
                elif status == "filtered":
                    run_update["sentiment_label"] = _result.get("sentiment_label")
                    run_update["sentiment_explanation"] = _result.get("sentiment_explanation")
                elif status == "success":
                    run_update["danger_score"] = _result.get("danger_score")
                    run_update["crimes_count"] = _result.get("crimes")
                    run_update["recommended_action"] = _result.get("recommended_action")
                elif status == "error":
                    run_update["error_reason"] = _result.get("reason")
                await update_pipeline_run(_run_id, run_update)
            except Exception as log_err:
                print(f"  [logger] failed to update pipeline_runs: {log_err}")

        for path in [video_path, audio_path]:
            if path and os.path.exists(path):
                for _i in range(5):
                    try:
                        os.remove(path)
                        print(f"  [cleanup] removed {os.path.basename(path)}")
                        break
                    except PermissionError:
                        if _i < 4:
                            await asyncio.sleep(0.3)
                        else:
                            print(f"  [cleanup] could not remove {os.path.basename(path)} — file still locked")


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
        elif status == "already_processed":
            print(f"  –  {sc_label:<25} already in DB (id: {r['reel_id']})")
        elif status == "repost":
            print(f"  ⚠  {sc_label:<25} repost of {r['original']} ({r['similarity']:.0%}) — {r['comments_saved']} new comment(s) saved")
        elif status == "filtered":
            print(f"  –  {sc_label:<25} filtered ({r['sentiment_label']}) — {r['sentiment_explanation']}")
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
    print("Flags (append to input):")
    print("  --skip-sentiment   bypass comment sentiment gate")
    print("  --force            reprocess even if already in DB")
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

        # Parse flags from the input line
        skip_sentiment = "--skip-sentiment" in user_input
        force          = "--force" in user_input

        user_input = user_input.replace("--skip-sentiment", "").replace("--force", "")

        if skip_sentiment:
            print("  [flag] Sentiment gate will be bypassed")
        if force:
            print("  [flag] Force reprocessing — duplicate checks skipped")
        if skip_sentiment or force:
            print()

        shortcodes = [s.strip() for s in user_input.split(",") if s.strip()]

        if len(shortcodes) == 1:
            results = [await process_single_reel(shortcodes[0], skip_sentiment=skip_sentiment, force=force)]
        else:
            print(f"\n[Pipeline] Running {len(shortcodes)} reels concurrently...\n")
            raw_results = await asyncio.gather(
                *[process_single_reel(sc, skip_sentiment=skip_sentiment, force=force) for sc in shortcodes],
                return_exceptions=True,
            )
            results = list(raw_results)

        _print_summary(shortcodes, results)
