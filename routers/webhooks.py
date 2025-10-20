from fastapi import HTTPException, Query, Request, APIRouter
from fastapi.responses import PlainTextResponse, JSONResponse
import os
from util.graph_api import parse_webhook_data
from services.database import store_payload, store_media
from services.mention import process_mention



router = APIRouter(prefix="/webhooks")

@router.get("")
async def meta_webhook_verification(
    mode: str = Query(..., alias="hub.mode"),
    challenge: str = Query(..., alias="hub.challenge"),
    verify_token: str = Query(..., alias="hub.verify_token")
):
    if verify_token == os.getenv("VERIFY_TOKEN") and mode == "subscribe":
        return PlainTextResponse(content=challenge)
    else:
        raise HTTPException(status_code=403, detail="verificationfailed")
    return PlainTextResponse(content="done")


@router.post("")
async def mentionlistener(request: Request):
    data, parse_status, mediaid = await parse_webhook_data(request)
    store_payload(data, parse_status)
    if mediaid:
        videopath, audiopath = await process_mention(mediaid)
        store_media(mediaid, videopath, audiopath)
    return JSONResponse(content={"request arrived": True}, status_code=200)