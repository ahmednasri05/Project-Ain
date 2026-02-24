import logging
import os
import json
from datetime import datetime

from fastapi import BackgroundTasks, HTTPException, Query, Request, APIRouter
from fastapi.responses import PlainTextResponse, JSONResponse

from services.dm_pipeline import run_dm_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks")


@router.get("")
async def meta_webhook_verification(
    mode: str = Query(..., alias="hub.mode"),
    challenge: str = Query(..., alias="hub.challenge"),
    verify_token: str = Query(..., alias="hub.verify_token")
):
    if verify_token == os.getenv("VERIFY_TOKEN") and mode == "subscribe":
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=403, detail="verification failed")


@router.post("")
async def DMListener(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    # Persist raw payload for debugging
    os.makedirs("webhookpayloads", exist_ok=True)
    filename = f"webhookpayloads/{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Extract the ig_reel attachment from the DM payload, if present
    try:
        messaging = data["entry"][0]["messaging"][0]
        attachments = messaging.get("message", {}).get("attachments", [])
        reel_attachment = next(
            (a for a in attachments if a.get("type") == "ig_reel"), None
        )
    except (KeyError, IndexError):
        reel_attachment = None

    if reel_attachment:
        payload = reel_attachment["payload"]
        video_url = payload.get("url", "")
        caption   = payload.get("title", "")
        asset_id  = str(payload.get("reel_video_id", datetime.now().strftime("%Y%m%d_%H%M%S")))

        if video_url:
            background_tasks.add_task(run_dm_pipeline, video_url, caption, asset_id)
            logger.info(f"[DMListener] Queued DM pipeline for asset {asset_id}")
        else:
            logger.warning("[DMListener] ig_reel attachment received but URL is empty — skipping")
    else:
        logger.debug("[DMListener] No ig_reel attachment in payload — nothing to process")

    return JSONResponse(content={"received": True}, status_code=200)


# @router.post("")
# async def mentionlistener(request: Request):
#     data, parse_status, mediaid = await parse_webhook_data(request)
#     store_payload(data, parse_status)
#     if mediaid:
#         videopath, audiopath = await process_mention(mediaid)
#         store_media(mediaid, videopath, audiopath)
#     return JSONResponse(content={"request arrived": True}, status_code=200)