"""
Video Fingerprinting Service
Generates perceptual hashes for duplicate video detection using frame sampling.
"""

import asyncio
import os
from typing import List, Dict, Any, Optional
import cv2
import imagehash
from PIL import Image


async def generate_video_fingerprint(
    video_path: str, 
    interval_seconds: int = 2
) -> List[Dict[str, Any]]:
    """
    Sample video frames and compute 64-bit perceptual hashes.
    
    Args:
        video_path: Path to video file
        interval_seconds: Sample interval in seconds (default: 2)
        
    Returns:
        List of fingerprints: [{"timestamp_seconds": float, "hash": str (64-bit binary)}]
        
    Example:
        fingerprints = await generate_video_fingerprint("video.mp4")
        # [{"timestamp_seconds": 0.0, "hash": "1101001..."}, ...]
    """
    def _extract_hashes():
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise Exception(f"Could not open video: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        print(f"Video info: {duration:.1f}s, {fps:.1f} fps, {total_frames} frames")
        
        hashes = []
        frame_step = int(fps * interval_seconds)
        
        current_frame = 0
        while current_frame < total_frames:
            # Set position to specific frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            success, frame = cap.read()
            
            if not success:
                break
            
            # Convert BGR (OpenCV) to RGB (PIL)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_frame)
            
            # Compute 64-bit perceptual hash
            hash_obj = imagehash.phash(pil_image)
            
            # Convert hex to 64-bit binary string for PostgreSQL BIT(64)
            hash_as_int = int(str(hash_obj), 16)
            binary_hash = bin(hash_as_int)[2:].zfill(64)
            
            hashes.append({
                "timestamp_seconds": round(current_frame / fps, 2),
                "hash": binary_hash
            })
            
            current_frame += frame_step
        
        cap.release()
        return hashes
    
    # Run in thread pool to avoid blocking
    return await asyncio.to_thread(_extract_hashes)


async def find_duplicate_videos(
    fingerprints: List[Dict[str, Any]],
    hamming_threshold: int = 5,
    min_matching_frames: int = 3
) -> List[Dict[str, Any]]:
    """
    Search database for videos with similar perceptual hashes using HNSW index.
    
    Args:
        fingerprints: List of {"timestamp_seconds": float, "hash": str}
        hamming_threshold: Maximum Hamming distance for match (default: 5)
        min_matching_frames: Minimum matching frames to consider duplicate (default: 3)
        
    Returns:
        List of duplicates: [{"shortcode": str, "matching_frames": int, "similarity": float, "best_distance": int}]
        
    Example:
        duplicates = await find_duplicate_videos(fingerprints)
        if duplicates:
            print(f"Found duplicate: {duplicates[0]['shortcode']}")
    """
    from db import get_supabase_client
    
    def _search_duplicates():
        supabase = get_supabase_client()
        
        # Dictionary to aggregate matches by shortcode
        video_matches = {}
        
        # Check each fingerprint hash against database using the stored procedure
        for fingerprint in fingerprints:
            hash_binary = fingerprint['hash']
            
            try:
                # Use the find_similar_videos stored procedure with HNSW index
                # This uses the <~> Hamming distance operator for efficient search
                response = supabase.rpc('find_similar_videos', {
                    'query_hash': hash_binary,
                    'max_distance': hamming_threshold,
                    'match_limit': 100  # Get up to 100 matches per frame
                }).execute()
                
                # Aggregate matches by shortcode
                if response.data:
                    for row in response.data:
                        shortcode = row['reel_shortcode']
                        distance = row['hamming_distance']
                        
                        if shortcode not in video_matches:
                            video_matches[shortcode] = {
                                'matching_frames': 0,
                                'distances': []
                            }
                        
                        video_matches[shortcode]['matching_frames'] += 1
                        video_matches[shortcode]['distances'].append(distance)
            
            except Exception as e:
                print(f"RPC error for hash {fingerprint['timestamp_seconds']}s: {e}")
                # Continue with other fingerprints even if one fails
                continue
        
        # Filter by minimum matching frames and format results
        duplicates = []
        for shortcode, data in video_matches.items():
            if data['matching_frames'] >= min_matching_frames:
                avg_distance = sum(data['distances']) / len(data['distances'])
                best_distance = min(data['distances'])
                
                # Calculate similarity score (0-1, where 1 is identical)
                similarity = 1 - (avg_distance / 64)
                
                duplicates.append({
                    'shortcode': shortcode,
                    'matching_frames': data['matching_frames'],
                    'total_frames_checked': len(fingerprints),
                    'similarity': round(similarity, 3),
                    'best_hamming_distance': best_distance,
                    'avg_hamming_distance': round(avg_distance, 2)
                })
        
        # Sort by matching frames (descending)
        duplicates.sort(key=lambda x: x['matching_frames'], reverse=True)
        
        return duplicates
    
    return await asyncio.to_thread(_search_duplicates)


async def save_video_hashes(
    shortcode: str,
    fingerprints: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Save video fingerprints to database.
    INTERNAL USE - Called by check_and_save_fingerprints after duplicate check.
    
    Args:
        shortcode: Instagram reel shortcode
        fingerprints: List of {"timestamp_seconds": float, "hash": str}
        
    Returns:
        {"saved": bool, "count": int}
    """
    from db import get_supabase_client
    
    def _insert():
        supabase = get_supabase_client()
        
        # Prepare payload
        payload = [
            {
                "reel_shortcode": shortcode,
                "timestamp_seconds": fp['timestamp_seconds'],
                "phash": fp['hash']
            }
            for fp in fingerprints
        ]
        
        # Batch insert
        response = supabase.table("video_frames").insert(payload).execute()
        
        return {
            "saved": True,
            "count": len(response.data) if response.data else 0
        }
    
    return await asyncio.to_thread(_insert)


async def check_and_save_fingerprints(
    shortcode: str,
    fingerprints: List[Dict[str, Any]],
    hamming_threshold: int = 5,
    min_matching_frames: int = 3
) -> Dict[str, Any]:
    """
    Main API: Check for duplicates FIRST, only save if no duplicates found.
    
    Args:
        shortcode: Instagram reel shortcode
        fingerprints: List of {"timestamp_seconds": float, "hash": str}
        hamming_threshold: Maximum Hamming distance for match (default: 5)
        min_matching_frames: Minimum matching frames to consider duplicate (default: 3)
        
    Returns:
        If duplicate:
            {
                "is_duplicate": True,
                "duplicates": [{"shortcode": str, "matching_frames": int, ...}]
            }
        
        If unique (saved):
            {
                "is_duplicate": False,
                "saved": True,
                "fingerprints_count": int,
                "shortcode": str
            }
    
    Example:
        result = await check_and_save_fingerprints("DRLS0KOAdv2", fingerprints)
        if result['is_duplicate']:
            print(f"Duplicate of: {result['duplicates'][0]['shortcode']}")
        else:
            print(f"Saved {result['fingerprints_count']} fingerprints")
    """
    print(f"\n{'='*60}")
    print(f"Checking {len(fingerprints)} fingerprints for duplicates...")
    print(f"{'='*60}")
    
    # Step 1: Check for duplicates
    duplicates = await find_duplicate_videos(
        fingerprints,
        hamming_threshold=hamming_threshold,
        min_matching_frames=min_matching_frames
    )
    
    # Step 2: Handle result
    if duplicates:
        print(f"\n⚠ DUPLICATE DETECTED!")
        print(f"  Found {len(duplicates)} matching video(s)")
        print(f"  Best match: {duplicates[0]['shortcode']}")
        print(f"  Matching frames: {duplicates[0]['matching_frames']}/{len(fingerprints)}")
        print(f"  Similarity: {duplicates[0]['similarity']:.1%}")
        print(f"{'='*60}\n")
        
        return {
            "is_duplicate": True,
            "duplicates": duplicates
        }
    else:
        print(f"\n✓ No duplicates found - saving fingerprints...")
        
        # Save to database
        save_result = await save_video_hashes(shortcode, fingerprints)
        
        print(f"✓ Saved {save_result['count']} fingerprints for {shortcode}")
        print(f"{'='*60}\n")
        
        return {
            "is_duplicate": False,
            "saved": True,
            "fingerprints_count": save_result['count'],
            "shortcode": shortcode
        }

