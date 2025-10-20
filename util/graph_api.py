import aiohttp
import os
from dotenv import load_dotenv
from fastapi import Request, HTTPException

load_dotenv()
ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")

GRAPH_API_URL = "https://graph.instagram.com"

async def get_media_info(media_id: str):
    url = f"{GRAPH_API_URL}/{media_id}"
    params = {
        "fields": "media_type,media_url,caption,timestamp",
        "access_token": ACCESS_TOKEN
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Failed to fetch media info ({response.status}): {text}")
            return await response.json()


async def parse_webhook_data(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    parse_status = False
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            mediaid = value.get("media_id") or value.get("mediaid")
            if mediaid:
                parse_status = True
    return data, parse_status, mediaid if 'mediaid' in locals() else None