"""
Example: Video Duplicate Detection Workflow
Demonstrates how to use perceptual hashing for duplicate detection.
"""

import asyncio
import sys
import os

# Add parent directory to path gg
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import generate_video_fingerprint, check_and_save_fingerprints
from db import download_and_upload_reel, save_reel


async def test_duplicate_detection(video_path: str):
    """
    Test function: Process the same video twice to demonstrate duplicate detection.
    First run: Should save as unique
    Second run: Should detect as duplicate and skip saving
    """
    print(f"\n{'='*60}")
    print(f"DUPLICATE DETECTION TEST")
    print(f"{'='*60}\n")
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return
    
    # Use filename as shortcode
    shortcode = os.path.splitext(os.path.basename(video_path))[0]
    
    # ========== FIRST RUN: Should save as unique ==========
    print(f"\n{'='*60}")
    print(f"FIRST RUN - Processing: {shortcode}")
    print(f"{'='*60}\n")
    
    try:
        # Generate fingerprints
        print("Step 1: Generating fingerprints...")
        fingerprints = await generate_video_fingerprint(video_path)
        print(f"✓ Generated {len(fingerprints)} fingerprints\n")
        
        # Check for duplicates and save if unique
        print("Step 2: Checking for duplicates...")
        result = await check_and_save_fingerprints(shortcode, fingerprints)
        
        if result['is_duplicate']:
            print("\n⚠ DUPLICATE DETECTED (unexpected on first run)")
            print(f"\nDuplicate Details:")
            for dup in result['duplicates']:
                print(f"  • Shortcode: {dup['shortcode']}")
                print(f"    Matching frames: {dup['matching_frames']}/{dup['total_frames_checked']}")
                print(f"    Similarity: {dup['similarity']:.1%}")
                print(f"    Best Hamming distance: {dup['best_hamming_distance']} bits")
        else:
            print("\n✅ UNIQUE VIDEO - SAVED TO DATABASE")
            print(f"\nSaved Details:")
            print(f"  • Shortcode: {result['shortcode']}")
            print(f"  • Fingerprints saved: {result['fingerprints_count']}")
        
    except Exception as e:
        print(f"\n❌ Error on first run: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== SECOND RUN: Should detect duplicate ==========
    print(f"\n\n{'='*60}")
    print(f"SECOND RUN - Processing same video: {shortcode}")
    print(f"{'='*60}\n")
    
    try:
        # Generate fingerprints again
        print("Step 1: Generating fingerprints...")
        fingerprints = await generate_video_fingerprint(video_path)
        print(f"✓ Generated {len(fingerprints)} fingerprints\n")
        
        # Check for duplicates (should find the first run)
        print("Step 2: Checking for duplicates...")
        result = await check_and_save_fingerprints(shortcode, fingerprints)
        
        if result['is_duplicate']:
            print("\n✅ DUPLICATE DETECTED (expected behavior)")
            print(f"❌ NOT SAVED TO DATABASE\n")
            print(f"Duplicate Details:")
            for dup in result['duplicates']:
                print(f"  • Original Shortcode: {dup['shortcode']}")
                print(f"    Matching frames: {dup['matching_frames']}/{dup['total_frames_checked']}")
                print(f"    Similarity: {dup['similarity']:.1%}")
                print(f"    Best Hamming distance: {dup['best_hamming_distance']} bits")
                print(f"    Average Hamming distance: {dup['avg_hamming_distance']} bits")
        else:
            print("\n⚠ NO DUPLICATE DETECTED (unexpected on second run)")
            print(f"  • Shortcode: {result['shortcode']}")
            print(f"  • Fingerprints saved: {result['fingerprints_count']}")
        
    except Exception as e:
        print(f"\n❌ Error on second run: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== SUMMARY ==========
    print(f"\n\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Video: {video_path}")
    print(f"Shortcode: {shortcode}")
    print(f"\n✓ First run: Video should be saved as unique")
    print(f"✓ Second run: Video should be detected as duplicate")
    print(f"{'='*60}\n")


async def main():
    """Run duplicate detection test."""
    print("\n" + "="*60)
    print("VIDEO DUPLICATE DETECTION TEST")
    print("="*60)
    
    # Example video path (replace with actual path)
    EXAMPLE_VIDEO = "path/to/video.mp4"
    
    # Check if example video exists
    if not os.path.exists(EXAMPLE_VIDEO):
        print(f"\n⚠ Example video not found: {EXAMPLE_VIDEO}")
        print("Please update EXAMPLE_VIDEO path in the script.")
        return
    
    # Run test
    try:
        await test_duplicate_detection(EXAMPLE_VIDEO)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

