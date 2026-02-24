"""
Generate an HTML report from an existing analysis JSON file.

Usage:
    python generate_report.py <path_to_json>
    python generate_report.py output/media_analysis_20260224_152302.json

The HTML report is saved alongside the JSON file with the same name.
"""

import sys
import json
from pathlib import Path

try:
    from db.client import SUPABASE_URL, get_storage_bucket
    def _supabase_video_url(video_path: str) -> str:
        shortcode = Path(video_path).stem
        bucket = get_storage_bucket()
        return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/videos/{shortcode}.mp4"
except ImportError:
    def _supabase_video_url(video_path: str):
        return None


def main():
    if len(sys.argv) < 2:
        # Default to the most recently modified JSON in output/
        json_files = sorted(Path("output").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not json_files:
            print("No JSON files found in output/. Pass a path explicitly.")
            sys.exit(1)
        json_path = json_files[0]
        print(f"No file specified — using most recent: {json_path}")
    else:
        json_path = Path(sys.argv[1])

    if not json_path.exists():
        print(f"File not found: {json_path}")
        sys.exit(1)

    from ai.schemas import MediaAnalysisResult
    from ai.report_generator import generate_html_report

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    result = MediaAnalysisResult(**data)

    video_url = _supabase_video_url(result.video_path) if result.video_path else None

    html_path = json_path.with_suffix(".html")
    generate_html_report(result, str(html_path), video_url=video_url)
    print(f"Report saved to: {html_path}")


if __name__ == "__main__":
    main()
