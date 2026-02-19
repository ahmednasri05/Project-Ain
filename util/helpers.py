import os
import asyncio
import aiohttp
import aiofiles
from moviepy import VideoFileClip


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  
SAVE_DIR = os.path.join(BASE_DIR, "downloads")

async def download_video(media_url: str, media_id: str):
    os.makedirs(SAVE_DIR, exist_ok=True)
    filepath = os.path.join(SAVE_DIR, f"{media_id}.mp4")

    # Validate URL before attempting download
    if not media_url or not media_url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid or missing video URL: '{media_url}'")

    # Minimal headers that work with Instagram CDN
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.instagram.com/",
    }

    # Use streaming download to handle large files and avoid timeout
    async with aiohttp.ClientSession() as session:
        async with session.get(media_url, headers=headers, allow_redirects=True) as resp:
            if resp.status != 200:
                # Print more debug info for 403 errors
                resp_text = await resp.text()
                raise Exception(f"Failed to download video: {resp.status}\nResponse: {resp_text[:200]}")
            
            async with aiofiles.open(filepath, "wb") as f:
                # Stream the download in chunks
                async for chunk in resp.content.iter_chunked(8192):
                    await f.write(chunk)

    return filepath

async def extract_audio(video_path: str, filename: str, save_dir: str = SAVE_DIR):
    audio_path = os.path.join(save_dir, f"{filename}.mp3")
    clip = VideoFileClip(video_path)
    await asyncio.to_thread(clip.audio.write_audiofile, audio_path)
    clip.close()
    return audio_path

