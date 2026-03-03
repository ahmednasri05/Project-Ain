"""
Main Pipeline
Orchestrates the full processing flow for Instagram reels:
  0. Shortcode existence check (bail if already in DB)
  1. Apify batch scrape (single actor run for all reels)
  2. Download video
  3. Extract audio
  4. Fingerprint + duplicate check
  5. Upload video to Supabase storage
  6. Save reel & comments to database
  6b. Save fingerprints
  6c. Comment sentiment gate (bail if SPAM_SARCASM)
  7. AI analysis (video + audio in parallel)

Batch flow:
  - Step 0 runs concurrently for all shortcodes upfront.
  - Step 1 is a single Apify actor run for all remaining shortcodes.
    URLs missing from the results are retried as sub-batches (up to MAX_ATTEMPTS times).
    Retries run concurrently with the processing of URLs that already succeeded.
  - Steps 2-9 run concurrently, throttled by a shared semaphore (MAX_CONCURRENT_PIPELINES).
"""

import os
import asyncio
import traceback
import httpx
import aiohttp
from datetime import datetime, timezone
from typing import Optional, Dict, Any

MAX_ATTEMPTS = 3

# Maximum number of reels processed concurrently through steps 2-9.
# Prevents DNS exhaustion and Instagram CDN rate-limiting.
MAX_CONCURRENT_PIPELINES = 5

# Exceptions that are transient and worth retrying.
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

# Human-readable labels for each step (used in failed_requests)
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

from util.apify import scrape_reels_batch
from util.helpers_ytdlp import download_video_ytdlp as download_video, extract_audio
from util.instagram import extract_shortcode as _extract_shortcode
from db import (
    save_reel, bulk_save_comments, upload_to_supabase, get_storage_bucket,
    get_reel_by_shortcode, increment_mention_count,
    insert_pipeline_run, update_pipeline_run, insert_failed_request,
    save_processed_crime_report,
)
from .video_fingerprint import generate_video_fingerprint, check_for_duplicates, save_fingerprints
from .comment_formatter import get_comments_for_sentiment_analysis
from ai.media_processor import MediaProcessor
from ai.sentiment_analyzer import SentimentAnalyzer



async def _process_reel_from_data(
    shortcode: str,
    reel_payload: Dict[str, Any],
    comments: list,
    skip_sentiment: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Run steps 2-9 of the pipeline for a reel whose Apify data is already available.
    Step 0 (existence check) and step 1 (Apify scrape) are handled by run_batch_pipeline.

    Args:
        shortcode:      Bare Instagram shortcode (already normalized)
        reel_payload:   Normalized reel dict from scrape_reels_batch
        comments:       Comments list from scrape_reels_batch
        skip_sentiment: If True, bypass the comment sentiment gate (step 8)
        force:          If True, skip the fingerprint duplicate check (step 4)

    Returns:
        Result dict — same shape as process_single_reel:
            status: "success" | "already_processed" | "repost" | "filtered" | "error"
    """
    print(f"\n{'='*60}")
    print(f"[Pipeline] Processing: {shortcode}")
    print(f"{'='*60}")

    # Resolve shortcode from Apify's response (handles server-side redirects)
    shortcode = reel_payload.get("shortCode", shortcode)

    video_path         = None
    audio_path         = None
    fingerprints       = None
    reel_record        = None
    video_storage_path = None
    audio_storage_path = None

    _result: Dict[str, Any] = {"status": "error", "shortcode": shortcode, "reason": "pipeline did not complete"}
    _run_id:    Optional[int] = None
    _start_time = datetime.now(timezone.utc)
    _attempts   = 0
    _current_step = 2
    comment_summary: Optional[str] = None

    print(f"  ✓ @{reel_payload['ownerUsername']} / {shortcode}")
    print(f"  ✓ {len(comments)} comment(s) fetched")

    try:
        _run_id = await insert_pipeline_run(shortcode)

        while True:
            try:
                # ── Step 2: Download video ────────────────────────────
                if _current_step == 2:
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
                    comment_summary = None
                    if comments:
                        print("\n[8/9] Running comment sentiment gate...")
                        comments_text    = await get_comments_for_sentiment_analysis(shortcode)
                        sentiment_result = await SentimentAnalyzer().analyze_sentiment(comments_text)
                        print(f"  ✓ Sentiment label : {sentiment_result.label}")
                        print(f"  ✓ Explanation     : {sentiment_result.explanation}")
                        if sentiment_result.summary:
                            print(f"  ✓ Summary         : {sentiment_result.summary}")
                            comment_summary = sentiment_result.summary

                        if sentiment_result.label == "SPAM_SARCASM" and not skip_sentiment:
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
                        print("\n[8/9] Comment sentiment gate skipped (no comments)")
                    _current_step = 9

                # ── Step 9: AI analysis ───────────────────────────────
                elif _current_step == 9:
                    print("\n[7/7] Running AI analysis (video + audio in parallel)...")
                    processor = MediaProcessor()
                    analysis  = await processor.process_media(video_path=video_path, audio_path=audio_path, language="ar")

                    # Attach comment summary from sentiment gate (step 8)
                    if comment_summary:
                        analysis.comment_summary = comment_summary

                    danger    = analysis.video_analysis.danger_score
                    crimes    = analysis.video_analysis.possible_crimes
                    sentiment = analysis.audio_analysis.sentiment
                    action    = analysis.recommended_action

                    print(f"  ✓ Danger score : {danger}/10")
                    print(f"  ✓ Crimes found : {len(crimes)}")
                    print(f"  ✓ Sentiment    : {sentiment}")
                    print(f"  ✓ Action       : {action}")

                    print(f"  → Saving crime report to database...")
                    crime_report = await save_processed_crime_report(
                        shortcode=shortcode,
                        media_analysis_result=analysis
                    )
                    print(f"  ✓ Crime report saved (DB id: {crime_report['id']})")

                    _result = {
                        "status": "success",
                        "shortcode": shortcode,
                        "reel_id": reel_record["id"],
                        "report_id": crime_report["id"],
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

    except Exception as e:
        print(f"\n  ✗ Error: {e}")
        traceback.print_exc()
        _result = {"status": "error", "shortcode": shortcode, "reason": str(e)}
        step_label = _STEP_LABELS.get(_current_step, f"step_{_current_step}")
        try:
            await insert_failed_request(shortcode, str(e), step_label, _attempts or 1)
        except Exception as log_err:
            print(f"  [logger] failed to write failed_request: {log_err}")
        return _result

    finally:
        duration_ms = int((datetime.now(timezone.utc) - _start_time).total_seconds() * 1000)
        if _run_id is not None:
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

            for _attempt in range(3):
                try:
                    await update_pipeline_run(_run_id, run_update)
                    break
                except Exception as log_err:
                    if _attempt == 2:
                        print(f"  [logger] failed to update pipeline_runs after 3 attempts: {log_err}")
                    else:
                        await asyncio.sleep(1)

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


async def run_batch_pipeline(
    shortcodes: list[str],
    skip_sentiment: bool = False,
    force: bool = False,
) -> list[Dict[str, Any]]:
    """
    Full pipeline for one or more Instagram reels.

    Steps 0 and 1 run at the batch level (existence checks and a single Apify actor run).
    Steps 2-9 run concurrently per reel, throttled by a shared semaphore.

    Any URLs missing from the first Apify result are retried as shrinking sub-batches
    (up to MAX_ATTEMPTS times) concurrently with the processing of already-succeeded reels.

    Args:
        shortcodes:     List of shortcodes or permalinks (raw user input)
        skip_sentiment: If True, bypass the comment sentiment gate for all reels
        force:          If True, skip existence check and fingerprint duplicate check

    Returns:
        List of result dicts in the same order as the input shortcodes.
    """
    # ── Normalize ──────────────────────────────────────────────────────
    normalized = [_extract_shortcode(sc) for sc in shortcodes]

    # ── Step 0: Concurrent existence checks ────────────────────────────
    print(f"\n[0/7] Checking {len(normalized)} shortcode(s) against DB...")
    if force:
        existence_results = [None] * len(normalized)
        print(f"  – Skipped (--force flag)")
    else:
        existence_results = await asyncio.gather(
            *[get_reel_by_shortcode(sc) for sc in normalized]
        )

    results_map: Dict[str, Dict[str, Any]] = {}
    to_scrape: list[str] = []

    for sc, existing in zip(normalized, existence_results):
        if not force and existing:
            await increment_mention_count(sc)
            print(f"  ⚠ {sc} — already in DB (id: {existing['id']}) — mention_count incremented")
            results_map[sc] = {"status": "already_processed", "shortcode": sc, "reel_id": existing["id"]}
        else:
            to_scrape.append(sc)

    already_done = len(normalized) - len(to_scrape)
    if already_done:
        print(f"  → {already_done} skipped, {len(to_scrape)} new")

    if not to_scrape:
        return [results_map[sc] for sc in normalized]

    # ── Shared semaphore for steps 2-9 ─────────────────────────────────
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_PIPELINES)
    process_tasks: list[asyncio.Task] = []

    async def _launch(sc: str, apify_result: Dict[str, Any]) -> None:
        async with semaphore:
            result = await _process_reel_from_data(
                sc,
                apify_result["reel"],
                apify_result["comments"],
                skip_sentiment=skip_sentiment,
                force=force,
            )
        results_map[sc] = result

    # ── Step 1: First Apify batch run ───────────────────────────────────
    print(f"\n[1/7] Apify batch run for {len(to_scrape)} reel(s)...")
    try:
        first_batch = await scrape_reels_batch(to_scrape)
    except Exception as e:
        print(f"  ✗ Apify batch run failed entirely: {e}")
        for sc in to_scrape:
            results_map[sc] = {"status": "error", "shortcode": sc, "reason": f"Apify batch run failed: {e}"}
            try:
                await insert_failed_request(sc, str(e), "step_1_apify", 1)
            except Exception:
                pass
        return [results_map.get(sc, {"status": "error", "shortcode": sc, "reason": "unknown"}) for sc in normalized]

    first_succeeded = {sc: r for sc, r in first_batch.items() if r is not None}
    first_failed    = [sc for sc in to_scrape if first_batch.get(sc) is None]

    print(f"  → {len(first_succeeded)} succeeded, {len(first_failed)} missing")

    # Launch processing for successes immediately
    for sc, r in first_succeeded.items():
        process_tasks.append(asyncio.create_task(_launch(sc, r)))

    # ── Apify retry loop (runs concurrently with step 2-9 processing) ───
    async def _retry_apify(failed: list[str]) -> None:
        remaining = list(failed)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if not remaining:
                return
            wait = 2 ** attempt
            print(f"\n[Pipeline] Retrying {len(remaining)} Apify URL(s) in {wait}s (attempt {attempt}/{MAX_ATTEMPTS})...")
            await asyncio.sleep(wait)

            try:
                retry_batch = await scrape_reels_batch(remaining)
            except Exception as e:
                print(f"[Pipeline] Apify retry run failed: {e} — will try again")
                continue

            new_remaining = []
            for sc in remaining:
                r = retry_batch.get(sc)
                if r is not None:
                    process_tasks.append(asyncio.create_task(_launch(sc, r)))
                else:
                    new_remaining.append(sc)
            remaining = new_remaining

        # Permanently failed
        for sc in remaining:
            print(f"[Pipeline] ✗ {sc} — no Apify result after {MAX_ATTEMPTS} attempts → failed_requests")
            results_map[sc] = {
                "status": "error",
                "shortcode": sc,
                "reason": f"Apify returned no results after {MAX_ATTEMPTS} attempts",
            }
            try:
                await insert_failed_request(sc, "Apify returned no results", "step_1_apify", MAX_ATTEMPTS)
            except Exception as log_err:
                print(f"  [logger] failed to write failed_request for {sc}: {log_err}")

    if first_failed:
        retry_task = asyncio.create_task(_retry_apify(first_failed))
        # Awaiting this lets the event loop run the already-created process_tasks concurrently
        await retry_task

    # ── Wait for all processing tasks (initial + those added by retry) ──
    if process_tasks:
        await asyncio.gather(*process_tasks, return_exceptions=True)

    return [results_map.get(sc, {"status": "error", "shortcode": sc, "reason": "unknown"}) for sc in normalized]


async def process_single_reel(
    shortcode: str,
    skip_sentiment: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Run the full pipeline for a single Instagram reel.
    Delegates to run_batch_pipeline.

    Args:
        shortcode:       Instagram shortcode or full permalink
        skip_sentiment:  If True, bypass the comment sentiment gate
        force:           If True, skip existence check and fingerprint duplicate check

    Returns:
        Result dict with keys:
            status: "success" | "already_processed" | "repost" | "filtered" | "error"
            shortcode, + status-specific fields
    """
    results = await run_batch_pipeline([shortcode], skip_sentiment=skip_sentiment, force=force)
    return results[0] if results else {"status": "error", "shortcode": shortcode, "reason": "no result"}


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
    Prompts for one or more shortcodes/permalinks, processes them via run_batch_pipeline,
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

        if len(shortcodes) > 1:
            print(f"\n[Pipeline] Running {len(shortcodes)} reels (max {MAX_CONCURRENT_PIPELINES} processing at a time)...\n")

        results = await run_batch_pipeline(shortcodes, skip_sentiment=skip_sentiment, force=force)
        _print_summary(shortcodes, results)
