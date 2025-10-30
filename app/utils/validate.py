"""Content validation helpers for Reddit posts and comments."""

import re
from typing import List, Dict, Any, Tuple, Optional


def validate_title(title: str, title_max: int = 300) -> Tuple[bool, Optional[str]]:
    """
    Validate post title length and format.
    
    Args:
        title: Post title to validate
        title_max: Maximum title length (default 300)
        
    Returns:
        Tuple of (is_valid, error_reason)
    """
    if not title or not title.strip():
        return False, "Title cannot be empty"
    
    title = title.strip()
    
    if len(title) > title_max:
        return False, f"Title too long ({len(title)} chars, max {title_max})"
    
    if len(title) < 3:
        return False, "Title too short (minimum 3 characters)"
    
    # Check for excessive caps (more than 70% uppercase)
    if title.isupper() and len(title) > 10:
        caps_ratio = sum(1 for c in title if c.isupper()) / len(title.replace(' ', ''))
        if caps_ratio > 0.7:
            return False, "Title has too many capital letters"
    
    return True, None


def validate_kind(kind: str, rules: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate post kind against subreddit rules.
    
    Args:
        kind: Post type ('link', 'self', 'image')
        rules: Subreddit rules dictionary
        
    Returns:
        Tuple of (is_valid, error_reason)
    """
    if kind not in ['link', 'self', 'image']:
        return False, f"Invalid post kind '{kind}', must be: link, self, or image"
    
    if kind == 'link' and not rules.get('allow_links', True):
        return False, "Link posts are not allowed in this subreddit"
    
    if kind == 'image' and not rules.get('allow_images', True):
        return False, "Image posts are not allowed in this subreddit"
    
    return True, None


def filter_banned(text: str, banned_words: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Check text for banned words.
    
    Args:
        text: Text to check
        banned_words: List of banned words/phrases
        
    Returns:
        Tuple of (is_clean, offending_word)
    """
    if not text or not banned_words:
        return True, None
    
    text_lower = text.lower()
    
    for banned_word in banned_words:
        if not banned_word:
            continue
            
        banned_lower = banned_word.lower()
        
        # Check for exact word matches (with word boundaries)
        pattern = r'\b' + re.escape(banned_lower) + r'\b'
        if re.search(pattern, text_lower):
            return False, banned_word
        
        # Also check for substring matches for phrases
        if ' ' in banned_word and banned_lower in text_lower:
            return False, banned_word
    
    return True, None


def choose_flair(flair_text: Optional[str], flairs: List[Dict[str, Any]]) -> Optional[str]:
    """
    Choose flair ID based on flair text.
    
    Args:
        flair_text: Requested flair text
        flairs: Available flairs list [{id, text}, ...]
        
    Returns:
        Flair ID if found, None otherwise
    """
    if not flair_text or not flairs:
        return None
    
    flair_text_lower = flair_text.lower().strip()
    
    # Try exact match first
    for flair in flairs:
        if flair.get('text', '').lower().strip() == flair_text_lower:
            return flair.get('id')
    
    # Try partial match
    for flair in flairs:
        flair_lower = flair.get('text', '').lower().strip()
        if flair_text_lower in flair_lower or flair_lower in flair_text_lower:
            return flair.get('id')
    
    return None


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format for link posts.
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, error_reason)
    """
    if not url:
        return False, "URL cannot be empty"
    
    url = url.strip()
    
    # Basic URL pattern check
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        return False, "Invalid URL format"
    
    if len(url) > 2000:
        return False, "URL too long (max 2000 characters)"
    
    return True, None


def validate_comment_text(text: str, min_length: int = 1, max_length: int = 10000) -> Tuple[bool, Optional[str]]:
    """
    Validate comment text.
    
    Args:
        text: Comment text to validate
        min_length: Minimum text length
        max_length: Maximum text length
        
    Returns:
        Tuple of (is_valid, error_reason)
    """
    if not text:
        return False, "Comment text cannot be empty"
    
    text = text.strip()
    
    if len(text) < min_length:
        return False, f"Comment too short (minimum {min_length} characters)"
    
    if len(text) > max_length:
        return False, f"Comment too long ({len(text)} chars, max {max_length})"
    
    return True, None


def validate_thing_id(thing_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Reddit thing ID format (t1_, t3_, etc.).
    
    Args:
        thing_id: Reddit thing ID to validate
        
    Returns:
        Tuple of (is_valid, error_reason)
    """
    if not thing_id:
        return False, "Thing ID cannot be empty"
    
    # Reddit thing IDs are like: t1_abc123, t3_def456
    pattern = r'^t[0-9]_[a-zA-Z0-9]+$'
    if not re.match(pattern, thing_id):
        return False, "Invalid Reddit thing ID format (expected: t[N]_[id])"
    
    return True, None


def sanitize_text(text: str) -> str:
    """
    Sanitize text for Reddit posts/comments.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove zero-width characters and other problematic unicode
    text = re.sub(r'[\u200b-\u200f\ufeff]', '', text)
    
    return text