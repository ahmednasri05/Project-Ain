
from db.models import payloads
from db.models import media
from datetime import datetime, timezone


def store_payload(data: dict, parse_status: bool):
    payloads.create_payload({
        "timestamp": datetime.now(timezone.utc),
        "payload": data,
        "parse_status": parse_status
        })


def store_media(media_id: str, video_path: str, audio_path: str):
    media.create_media_document({
        "media_id": media_id,
        "video_path": video_path,
        "audio_path": audio_path
    })