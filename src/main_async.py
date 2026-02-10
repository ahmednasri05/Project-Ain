"""
Crime Monitoring AI - Async Main Script
Process videos and audio to detect potential criminal activity.
Uses parallel processing for faster analysis.
"""

import logging
import asyncio
from pathlib import Path
from models.media_processor import MediaProcessor
from logging_config import setup_logging

# Configure logging
setup_logging(log_level="INFO", log_file="crime_monitoring.log")

logger = logging.getLogger(__name__)


async def main():
    """Main async function."""
    # Example usage
    video_path = r"C:\Users\shels\Documents\wezareit el dakhleya\dakhleyaVideos\blue car swerving\blue car swerving.mp4"
    audio_path = r"C:\Users\shels\Documents\wezareit el dakhleya\dakhleyaVideos\blue car swerving\blue car swerving.mp3"
    
    # Create processor
    processor = MediaProcessor()
    
    # Process video and audio in parallel
    results = await processor.process_media(
        video_path=video_path,
        audio_path=audio_path,
        output_dir="output"
    )
    
    # Print comprehensive summary
    print("\n" + "="*70)
    print("MEDIA ANALYSIS COMPLETE")
    print("="*70)
    
    print("\n📹 VIDEO ANALYSIS:")
    print(f"  Description: {results.video_analysis.description[:200]}...")
    print(f"  Danger Score: {results.video_analysis.danger_score}/10")
    
    print("\n🔍 DETECTED ENTITIES:")
    entities = results.video_analysis.detected_entities
    print(f"  People Count: {entities.people_count}")
    print(f"  Weapons: {len(entities.weapons)}")
    for weapon in entities.weapons:
        print(f"    - {weapon.type} at {weapon.timestamp} (confidence: {weapon.confidence:.2f})")
    print(f"  Vehicles: {len(entities.vehicles)}")
    for vehicle in entities.vehicles:
        plate_info = f" - Plate: {vehicle.license_plate.raw_text}" if vehicle.license_plate else ""
        print(f"    - {vehicle.color} {vehicle.type}{plate_info}")
    
    if results.video_analysis.scene_landmarks.identified_landmark:
        print("\n📍 LOCATION:")
        landmarks = results.video_analysis.scene_landmarks
        print(f"  Landmark: {landmarks.identified_landmark}")
        print(f"  Style: {landmarks.architectural_style}")
        print(f"  Confidence: {landmarks.confidence:.2f}")
    
    print("\n⚠️ POSSIBLE CRIMES:")
    if results.video_analysis.possible_crimes:
        for crime in results.video_analysis.possible_crimes:
            print(f"  - [{crime.timestamp}] {crime.rule_violated} ({crime.severity})")
            print(f"    {crime.content}")
    else:
        print("  No crimes detected")
    
    print("\n🎤 AUDIO ANALYSIS:")
    print(f"  Sentiment: {results.audio_analysis.sentiment}")
    print(f"  Language: {results.audio_analysis.language}")
    print(f"  Confidence: {results.audio_analysis.confidence:.2f}")
    print(f"\n  Transcript Preview:")
    transcript_lines = results.audio_analysis.transcript.split('\n')[:3]
    for line in transcript_lines:
        print(f"    {line}")
    if len(results.audio_analysis.transcript.split('\n')) > 3:
        print(f"    ... ({len(results.audio_analysis.transcript.split('\n')) - 3} more lines)")
    
    print("\n🔊 AUDIO EVENTS:")
    if results.audio_analysis.audio_events:
        for event in results.audio_analysis.audio_events:
            intensity = f" ({event.intensity})" if event.intensity else ""
            print(f"  - [{event.timestamp}] {event.event}{intensity}")
    else:
        print("  No significant audio events detected")
    
    print("\n📋 OVERALL ASSESSMENT:")
    print(f"  {results.overall_assessment}")
    
    if results.recommended_action:
        print("\n🎯 RECOMMENDED ACTION:")
        print(f"  {results.recommended_action}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())

