"""
Example usage of the new modular analysis system.
Shows how to use individual analyzers or the integrated processor.
"""

import asyncio
import logging
from models.audio_analyzer import analyze_audio
from models.video_analyzer import analyze_video
from models.media_processor import process_media
from logging_config import setup_logging

# Configure logging
setup_logging(log_level="INFO", log_file="example.log")
logger = logging.getLogger(__name__)


async def example_individual_analysis():
    """Example: Using individual analyzers separately."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Individual Analysis")
    print("="*70)
    
    video_path = r"C:\Users\shels\Documents\wezareit el dakhleya\dakhleya videos\blue car swerving\blue car swerving.mp4"
    audio_path = r"C:\Users\shels\Documents\wezareit el dakhleya\dakhleya videos\blue car swerving\blue car swerving.mp3"
    
    # Analyze audio only
    print("\n🎤 Analyzing audio...")
    audio_result = await analyze_audio(audio_path, language="ar")
    print(f"   Transcript length: {len(audio_result.transcript)} chars")
    print(f"   Sentiment: {audio_result.sentiment}")
    print(f"   Events detected: {len(audio_result.audio_events)}")
    
    # Analyze video only
    print("\n📹 Analyzing video...")
    video_result = await analyze_video(video_path)
    print(f"   Danger score: {video_result.danger_score}/10")
    print(f"   People count: {video_result.detected_entities.people_count}")
    print(f"   Crimes detected: {len(video_result.possible_crimes)}")
    
    return audio_result, video_result


async def example_integrated_analysis():
    """Example: Using integrated processor for parallel analysis."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Integrated Parallel Analysis")
    print("="*70)
    
    video_path = r"C:\Users\shels\Documents\wezareit el dakhleya\dakhleya videos\blue car swerving\blue car swerving.mp4"
    audio_path = r"C:\Users\shels\Documents\wezareit el dakhleya\dakhleya videos\blue car swerving\blue car swerving.mp3"
    
    # Process both in parallel
    result = await process_media(
        video_path=video_path,
        audio_path=audio_path,
        output_dir="output",
        language="ar"
    )
    
    print(f"\n✅ Complete analysis saved to output/")
    print(f"   Video danger: {result.video_analysis.danger_score}/10")
    print(f"   Audio sentiment: {result.audio_analysis.sentiment}")
    print(f"   Overall: {result.overall_assessment[:100]}...")
    print(f"   Action: {result.recommended_action}")
    
    return result


async def example_video_only():
    """Example: Analyzing video without audio."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Video-Only Analysis")
    print("="*70)
    
    video_path = r"C:\Users\shels\Documents\wezareit el dakhleya\dakhleya videos\blue car swerving\blue car swerving.mp4"
    
    # Process video only (audio path will be checked, analysis continues if not found)
    result = await process_media(
        video_path=video_path,
        audio_path="nonexistent.mp3",  # Will handle gracefully
        output_dir="output"
    )
    
    print(f"\n✅ Video-only analysis complete")
    print(f"   Danger: {result.video_analysis.danger_score}/10")
    
    return result


async def main():
    """Run all examples."""
    print("\n" + "🚀 "*25)
    print("CRIME MONITORING AI - MODULAR ANALYSIS EXAMPLES")
    print("🚀 "*25 + "\n")
    
    # Example 1: Individual analyzers
    await example_individual_analysis()
    
    # Example 2: Integrated processor (recommended)
    await example_integrated_analysis()
    
    # Example 3: Video only
    # await example_video_only()
    
    print("\n" + "="*70)
    print("✅ All examples completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

