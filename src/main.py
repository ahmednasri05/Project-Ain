"""
Crime Monitoring AI - Main Script
Process videos and audio to detect potential criminal activity.
"""

import logging
from models.aggregator import process_video
from logging_config import setup_logging

# Configure logging
setup_logging(log_level="INFO", log_file="crime_monitoring.log")

logger = logging.getLogger(__name__)

def main():
    # Example usage
    video_path = r"C:\Users\shels\Documents\wezareit el dakhleya\dakhleya videos\blue car swerving\blue car swerving.mp4"
    audio_path = r"C:\Users\shels\Documents\wezareit el dakhleya\dakhleya videos\blue car swerving\blue car swerving.mp3"
    
    # Process video and audio
    results = process_video(
        video_path=video_path,
        audio_path=audio_path,
        output_dir="output"
    )
    
    # Print summary
    print("\n" + "="*50)
    print("ANALYSIS COMPLETE")
    print("="*50)
    classification = results['crime_classification']
    print(f"\nCrime Detected: {classification['crime_detected']}")
    print(f"Confidence Level: {classification['confidence_level']}")
    print(f"Type of Crime: {classification['type_of_crime']}")
    print(f"Summary: {classification['summary']}")
    print(f"Key Evidence:")
    for evidence in classification['key_evidence']:
        print(f"  - {evidence}")

if __name__ == "__main__":
    main()

