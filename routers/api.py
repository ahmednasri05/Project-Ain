"""
Dashboard API Router
Provides REST endpoints for the Project Ain frontend dashboard.
All endpoints are prefixed with /api.
"""


import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from db.client import get_supabase_client
from services.pipeline import run_batch_pipeline
from services.dm_pipeline import run_dm_pipeline
from util.instagram import extract_shortcode as _extract_shortcode, is_instagram_url as _is_instagram_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")



# ── Request bodies ────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    url: str
    force: bool = False
    skip_sentiment: bool = False


# ── Reports ───────────────────────────────────────────────────────────────────

@router.get("/reports")
async def list_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    crime_classification: Optional[str] = None,
    in_egypt: Optional[str] = None,
    crime_category: Optional[int] = Query(None, ge=1, le=10),
    min_danger: Optional[int] = Query(None, ge=0, le=10),
    max_danger: Optional[int] = Query(None, ge=0, le=10),
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    sort_by: str = Query("processed_at", pattern="^(processed_at|danger_score|severity|mention_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    """
    Paginated, filterable list of processed crime reports.
    Returns data rows and total count for pagination.
    """
    def _query():
        supabase = get_supabase_client()

        q = supabase.table("processed_crime_reports").select(
            "id, reel_shortcode, approximate_location, rule_violated, severity, "
            "danger_score, crime_classification, crime_category, in_egypt, "
            "mention_count, overall_assessment, recommended_action, processed_at",
            count="exact",
        )

        if severity:
            q = q.eq("severity", severity)
        if crime_classification:
            q = q.eq("crime_classification", crime_classification)
        if in_egypt:
            q = q.eq("in_egypt", in_egypt)
        if crime_category is not None:
            q = q.filter("crime_category", "cs", f"{{{crime_category}}}")
        if min_danger is not None:
            q = q.gte("danger_score", min_danger)
        if max_danger is not None:
            q = q.lte("danger_score", max_danger)
        if from_date:
            q = q.gte("processed_at", from_date)
        if to_date:
            q = q.lte("processed_at", to_date)

        q = q.order(sort_by, desc=(sort_order == "desc"))
        offset = (page - 1) * limit
        q = q.range(offset, offset + limit - 1)

        response = q.execute()
        return response.data, response.count

    data, total = await asyncio.to_thread(_query)
    return {"data": data, "total": total or 0, "page": page, "limit": limit}


@router.get("/reports/{report_id}")
async def get_report(report_id: int):
    """Full single report including raw_analysis_data."""
    def _query():
        supabase = get_supabase_client()
        response = (
            supabase.table("processed_crime_reports")
            .select("*")
            .eq("id", report_id)
            .execute()
        )
        return response.data[0] if response.data else None

    report = await asyncio.to_thread(_query)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# ── Analyze (manual URL submission) ──────────────────────────────────────────

@router.post("/analyze")
async def analyze_url(body: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Queue a video URL for analysis.
    - Instagram URL / bare shortcode → full pipeline (Apify scrape, DB storage)
    - Direct CDN URL                 → DM pipeline (lightweight, no Apify)
    Returns immediately; processing happens in the background.
    """
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    if _is_instagram_url(url):
        shortcode = _extract_shortcode(url)
        background_tasks.add_task(run_batch_pipeline, [shortcode], body.skip_sentiment, body.force)
        logger.info(f"[API] Queued full pipeline for shortcode: {shortcode} (force={body.force}, skip_sentiment={body.skip_sentiment})")
        return {"queued": True, "type": "full", "identifier": shortcode}
    else:
        asset_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        background_tasks.add_task(run_dm_pipeline, url, "", asset_id)
        logger.info(f"[API] Queued DM pipeline for direct URL (asset_id: {asset_id})")
        return {"queued": True, "type": "dm", "identifier": asset_id}


# ── Pipeline runs ─────────────────────────────────────────────────────────────

@router.get("/pipeline-runs")
async def list_pipeline_runs(limit: int = Query(50, ge=1, le=200)):
    """Recent pipeline run rows, newest first."""
    def _query():
        supabase = get_supabase_client()
        response = (
            supabase.table("pipeline_runs")
            .select("*")
            .order("triggered_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    data = await asyncio.to_thread(_query)
    return {"data": data}


# ── Failed requests ───────────────────────────────────────────────────────────

@router.get("/failed-requests")
async def list_failed_requests():
    """All unresolved failed requests."""
    def _query():
        supabase = get_supabase_client()
        response = (
            supabase.table("failed_requests")
            .select("*")
            .eq("resolved", False)
            .order("failed_at", desc=True)
            .execute()
        )
        return response.data or []

    data = await asyncio.to_thread(_query)
    return {"data": data}


@router.post("/failed-requests/{request_id}/retry")
async def retry_failed_request(request_id: int, background_tasks: BackgroundTasks):
    """Mark a failed request as resolved and re-queue it through the full pipeline."""
    def _fetch_and_resolve():
        supabase = get_supabase_client()
        row_resp = (
            supabase.table("failed_requests")
            .select("shortcode")
            .eq("id", request_id)
            .execute()
        )
        if not row_resp.data:
            return None
        shortcode = row_resp.data[0]["shortcode"]
        supabase.table("failed_requests").update({
            "resolved": True,
        }).eq("id", request_id).execute()
        return shortcode

    shortcode = await asyncio.to_thread(_fetch_and_resolve)
    if not shortcode:
        raise HTTPException(status_code=404, detail="Failed request not found")

    background_tasks.add_task(run_batch_pipeline, [shortcode])
    logger.info(f"[API] Retrying shortcode: {shortcode} (failed_request id: {request_id})")
    return {"queued": True, "shortcode": shortcode}


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    min_danger: Optional[int] = None,
    max_danger: Optional[int] = None,
    crime_classification: Optional[str] = None,
    in_egypt: Optional[str] = None,
    crime_category: Optional[int] = None,
):
    """Aggregate stats for the dashboard header cards."""
    def _query():
        supabase = get_supabase_client()
        q = (
            supabase.table("processed_crime_reports")
            .select("danger_score, crime_classification, severity, crime_category, in_egypt")
        )
        if min_danger is not None:
            q = q.gte("danger_score", min_danger)
        if max_danger is not None:
            q = q.lte("danger_score", max_danger)
        if crime_classification:
            q = q.eq("crime_classification", crime_classification)
        if in_egypt:
            q = q.eq("in_egypt", in_egypt)
        if crime_category is not None:
            q = q.filter("crime_category", "cs", f"{{{crime_category}}}")
        return q.execute().data or []

    rows = await asyncio.to_thread(_query)

    total = len(rows)
    avg_danger = round(sum(r["danger_score"] for r in rows if r.get("danger_score") is not None) / total, 1) if total else 0

    by_classification: dict = {}
    by_severity: dict = {}
    by_crime_category: dict = {}
    for r in rows:
        cls = r.get("crime_classification") or "غير محدد"
        sev = r.get("severity") or "غير محدد"
        by_classification[cls] = by_classification.get(cls, 0) + 1
        by_severity[sev] = by_severity.get(sev, 0) + 1
        for cat in (r.get("crime_category") or []):
            by_crime_category[cat] = by_crime_category.get(cat, 0) + 1

    return {
        "total_reports": total,
        "avg_danger_score": avg_danger,
        "by_classification": by_classification,
        "by_severity": by_severity,
        "by_crime_category": by_crime_category,
    }
