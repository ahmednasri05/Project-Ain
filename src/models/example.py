"""
Simple example - Crime Monitoring AI

How to run:
    cd src
    python -m models.example
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.aggregator import process_video

# Your video and audio files
video_path = r"C:\Users\shels\Downloads\dakhleya videos\women brutality stairs\women brutality stairs.mp4"
audio_path = r"C:\Users\shels\Documents\wezareit el dakhleya\Gold thiefs.mp3"

# Run the pipeline
results = process_video(video_path, audio_path, output_dir="output")

# Print results
classification = results['crime_classification']
print("\n" + "="*50)
print("RESULTS")
print("="*50)
print(f"Crime Detected: {classification['crime_detected']}")
print(f"Confidence: {classification['confidence_level']}")
print(f"Type: {classification['type_of_crime']}")
print(f"Summary: {classification['summary']}")
print("="*50)

