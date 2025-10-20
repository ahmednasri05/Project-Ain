from util.graph_api import get_media_info
from util.helpers import download_video, extract_audio
async def process_mention(mediaid: str):
    response = await get_media_info(mediaid)
    media_url = response.get("media_url")
    videopath = await download_video(media_url, mediaid)
    audiopath = await extract_audio(videopath, mediaid)
    return videopath, audiopath
