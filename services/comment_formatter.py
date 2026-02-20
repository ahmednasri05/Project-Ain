"""
Comment Parser Service
Formats Instagram comments for LLM sentiment analysis.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from db import fetch_comments_from_db


def build_comment_tree(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build a nested tree structure from flat comment list.
    
    Args:
        comments: Flat list of comments from database
        
    Returns:
        List of top-level comments with nested replies
    """
    # Create a mapping of comment ID to comment with replies
    comment_map = {}
    for comment in comments:
        comment_map[comment['id']] = {
            **comment,
            'replies': []
        }
    
    # Build the tree structure
    root_comments = []
    for comment in comments:
        if comment['parent_comment_id'] is None:
            # Top-level comment
            root_comments.append(comment_map[comment['id']])
        else:
            # Reply - add to parent's replies list
            parent_id = comment['parent_comment_id']
            if parent_id in comment_map:
                comment_map[parent_id]['replies'].append(comment_map[comment['id']])
    
    return root_comments


def format_comment_for_llm_text(
    comments: List[Dict[str, Any]], 
    include_metadata: bool = True,
    include_replies: bool = True,
    max_depth: int = 2
) -> str:
    """
    Format comments as a readable text string for LLM analysis.
    
    Args:
        comments: List of comment dictionaries (can be nested)
        include_metadata: Include username, likes, timestamp
        include_replies: Include nested replies
        max_depth: Maximum nesting depth to include
        
    Returns:
        Formatted text string ready for LLM
    """
    def _format_single_comment(comment: Dict[str, Any], depth: int = 0) -> str:
        indent = "  " * depth
        marker = "└─" if depth > 0 else "•"
        
        # Build the comment text
        text = comment.get('text_content', '').strip()
        if not text:
            text = "[empty comment]"
        
        lines = [f"{indent}{marker} {text}"]
        
        # Add metadata if requested
        if include_metadata:
            username = comment.get('owner_username', 'unknown')
            likes = comment.get('like_count', 0)
            timestamp = comment.get('posted_at', '')
            
            # Format timestamp
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    time_str = timestamp
            else:
                time_str = 'unknown'
            
            metadata = f"{indent}  [@{username}, {likes} likes, {time_str}]"
            lines.append(metadata)
        
        # Add replies if requested and within depth limit
        if include_replies and depth < max_depth:
            replies = comment.get('replies', [])
            if replies:
                for reply in replies:
                    lines.append(_format_single_comment(reply, depth + 1))
        
        return "\n".join(lines)
    
    if not comments:
        return "[No comments available]"
    
    formatted_comments = [_format_single_comment(comment) for comment in comments]
    return "\n\n".join(formatted_comments)


def format_comment_for_llm_json(
    comments: List[Dict[str, Any]],
    include_replies: bool = True,
    max_depth: int = 2
) -> Dict[str, Any]:
    """
    Format comments as JSON structure for LLM analysis.
    
    Args:
        comments: List of comment dictionaries (can be nested)
        include_replies: Include nested replies
        max_depth: Maximum nesting depth to include
        
    Returns:
        JSON-serializable dictionary
    """
    def _format_single_comment(comment: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        formatted = {
            "text": comment.get('text_content', '').strip(),
            "username": comment.get('owner_username', 'unknown'),
            "likes": comment.get('like_count', 0),
            "posted_at": comment.get('posted_at', ''),
        }
        
        # Add replies if requested and within depth limit
        if include_replies and depth < max_depth:
            replies = comment.get('replies', [])
            if replies:
                formatted['replies'] = [
                    _format_single_comment(reply, depth + 1) 
                    for reply in replies
                ]
        
        return formatted
    
    return {
        "total_comments": len(comments),
        "comments": [_format_single_comment(comment) for comment in comments]
    }


async def get_comments_for_sentiment_analysis(
    shortcode: str,
    format_type: str = "text",
    include_metadata: bool = True,
    include_replies: bool = True,
    max_depth: int = 2
) -> str | Dict[str, Any]:
    """
    Main function: Fetch and format comments for LLM sentiment analysis.
    
    Args:
        shortcode: Instagram reel shortcode
        format_type: "text" or "json"
        include_metadata: Include username, likes, timestamp (text format only)
        include_replies: Include nested replies
        max_depth: Maximum reply depth to include
        
    Returns:
        Formatted comments as text string or JSON dict
        
    Example:
        # Get as text for LLM
        comments_text = await get_comments_for_sentiment_analysis("DRLS0KOAdv2")
        sentiment = await sentiment_analyzer.analyze_sentiment(comments_text)
        
        # Get as JSON
        comments_json = await get_comments_for_sentiment_analysis(
            "DRLS0KOAdv2", 
            format_type="json"
        )
    """
    # Fetch from database
    flat_comments = await fetch_comments_from_db(shortcode)
    
    if not flat_comments:
        return "[No comments found]" if format_type == "text" else {"total_comments": 0, "comments": []}
    
    # Build tree structure
    comment_tree = build_comment_tree(flat_comments)
    
    # Format based on type
    if format_type == "json":
        return format_comment_for_llm_json(
            comment_tree,
            include_replies=include_replies,
            max_depth=max_depth
        )
    else:
        return format_comment_for_llm_text(
            comment_tree,
            include_metadata=include_metadata,
            include_replies=include_replies,
            max_depth=max_depth
        )


def extract_comment_texts_only(comments: List[Dict[str, Any]]) -> List[str]:
    """
    Extract only the text content from comments (flattened, no structure).
    Useful for minimal token usage in LLM.
    
    Args:
        comments: List of comment dictionaries
        
    Returns:
        List of comment text strings
    """
    texts = []
    
    def _extract_text(comment: Dict[str, Any]):
        text = comment.get('text_content', '').strip()
        if text:
            texts.append(text)
        
        # Recursively extract from replies
        for reply in comment.get('replies', []):
            _extract_text(reply)
    
    for comment in comments:
        _extract_text(comment)
    
    return texts

