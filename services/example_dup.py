"""
Example: Check for duplicate videos and download if unique
Uses video_fingerprint service to check duplicates and storage_utils to download.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.video_fingerprint import check_and_save_fingerprints
from db.storage_utils import download_and_upload_reel


async def check_and_download_if_unique(shortcode: str, video_url: str):
	"""
	Example workflow: Check if video is duplicate, download only if unique.
	
	Args:
		shortcode: Instagram reel shortcode
		video_url: URL of the video to download
	"""
	print(f"\n{'='*60}")
	print(f"Duplicate Check & Download: Reel {shortcode}")
	print(f"{'='*60}\n")
	
	# Example fingerprints (in real usage, you'd generate these from the video)
	# For demonstration, using placeholder fingerprints
	example_fingerprints = [
		{"timestamp_seconds": 0.0, "hash": "1100011101111000001110001100011101011011001110000000011111000011"},
		{"timestamp_seconds": 2.0, "hash": "1001111001010000001000011011110101011110100000000011000111111111"},
		{"timestamp_seconds": 4.0, "hash": "1001111001101000011000111001100110001100011001101101001010011101"},
		{"timestamp_seconds": 6.0, "hash": "1000100101110110001101001100100100100110001101001101110111001011"},
		{"timestamp_seconds": 8.0, "hash": "1011011101101100010000001010101110101101110101100101001000110001"},
		{"timestamp_seconds": 10.0, "hash": "1101001100111110011000011000010110011110011000110011111011000000"},
		{"timestamp_seconds": 12.0, "hash": "1100001100110100001111001101100011100110001001010001100111111010"},
		{"timestamp_seconds": 14.0, "hash": "1101110000100011000000111111110001001100000000010111111111101100"},
		{"timestamp_seconds": 16.0, "hash": "1101110100101001000000001110011011111111100111010000000001100111"},
		{"timestamp_seconds": 18.0, "hash": "1100010000111111001110111101000001000100110011110011101101100000"},
		{"timestamp_seconds": 20.0, "hash": "1100001100110100001111011100101111000010001101100001100111001011"},
	]
	
	print("Checking for duplicates...")
	result = await check_and_save_fingerprints(
		shortcode=shortcode,
		fingerprints=example_fingerprints,
		hamming_threshold=5,
		min_matching_frames=3
	)
	
	if result['is_duplicate']:
		print(f"\n⚠️  Video is a DUPLICATE!")
		print(f"Found {len(result['duplicates'])} similar video(s):")
		for dup in result['duplicates']:
			print(f"  - {dup['shortcode']}: {dup['matching_frames']} matching frames, "
			      f"similarity: {dup['similarity']}")
		print("\n❌ Skipping download.\n")
	else:
		print(f"\n✓ Video is UNIQUE! Fingerprints saved.")
		
	print(f"\n{'='*60}\n")


async def main():
	"""Run the duplicate check and download example."""
	# Example Instagram reel
	EXAMPLE_SHORTCODE = "DRLS0KOAdv2"
	EXAMPLE_VIDEO_URL = "C:/Users/shels/Documents/wezareit el dakhleya/dakhleyaVideos/blue car swerving/blue car swerving.mp4"
	
	await check_and_download_if_unique(EXAMPLE_SHORTCODE, EXAMPLE_VIDEO_URL)


if __name__ == "__main__":
	asyncio.run(main())