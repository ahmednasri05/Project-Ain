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

    async with aiohttp.ClientSession() as session:
        async with session.get(media_url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to download video: {resp.status}")
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(await resp.read())

    return filepath

async def extract_audio(video_path: str, filename: str, save_dir: str = SAVE_DIR):
    audio_path = os.path.join(save_dir, f"{filename}.mp3")
    clip = VideoFileClip(video_path)
    await asyncio.to_thread(clip.audio.write_audiofile, audio_path)
    clip.close()
    return audio_path

