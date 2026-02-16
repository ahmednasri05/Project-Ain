"""
Services Package
Business logic and utility services for the application.
"""

from .comment_parser import (
    get_comments_for_sentiment_analysis,
    format_comment_for_llm_text,
    format_comment_for_llm_json,
    create_sentiment_analysis_prompt,
    extract_comment_texts_only,
    fetch_comments_from_db,
    build_comment_tree
)

from .video_fingerprint import (
    generate_video_fingerprint,
    find_duplicate_videos,
    save_video_hashes,
    check_and_save_fingerprints
)

__all__ = [
    # Comment Parser
    "get_comments_for_sentiment_analysis",
    "format_comment_for_llm_text",
    "format_comment_for_llm_json",
    "create_sentiment_analysis_prompt",
    "extract_comment_texts_only",
    "fetch_comments_from_db",
    "build_comment_tree",
    # Video Fingerprinting
    "generate_video_fingerprint",
    "find_duplicate_videos",
    "save_video_hashes",
    "check_and_save_fingerprints",
]

