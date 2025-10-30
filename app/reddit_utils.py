"""Reddit utility functions for flair lookup, subreddit rules, backoff, and validation."""

import time
import asyncio
import mimetypes
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse
import re
import json
from loguru import logger

from app.config import settings


# Cache for subreddit rules and flair data
_subreddit_cache: Dict[str, Dict[str, Any]] = {}
_cache_ttl = 3600  # 1 hour TTL


class RedditRateLimiter:
    """Rate limiter for Reddit API requests."""
    
    def __init__(self):
        self.windows: Dict[str, Dict[str, Any]] = {}
        self.burst_limit = settings.reddit_rate_burst
        self.window_seconds = settings.reddit_rate_window_s
    
    def can_make_request(self, key: str = "global") -> bool:
        """Check if a request can be made within rate limits."""
        now = time.time()
        
        if key not in self.windows:
            self.windows[key] = {
                "start": now,
                "count": 0,
                "reset_at": now + self.window_seconds
            }
        
        window = self.windows[key]
        
        # Reset window if expired
        if now >= window["reset_at"]:
            window["start"] = now
            window["count"] = 0
            window["reset_at"] = now + self.window_seconds
        
        return window["count"] < self.burst_limit
    
    def record_request(self, key: str = "global") -> None:
        """Record that a request was made."""
        now = time.time()
        
        if key not in self.windows:
            self.windows[key] = {
                "start": now,
                "count": 0,
                "reset_at": now + self.window_seconds
            }
        
        self.windows[key]["count"] += 1
    
    def get_reset_time(self, key: str = "global") -> float:
        """Get when the rate limit resets for a key."""
        if key in self.windows:
            return self.windows[key]["reset_at"]
        return time.time()


# Global rate limiter instance
rate_limiter = RedditRateLimiter()


async def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> None:
    """Implement exponential backoff with jitter."""
    if attempt <= 0:
        return
    
    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
    # Add jitter (±25%)
    jitter = delay * 0.25 * (2 * time.time() % 1 - 0.5)  # Simple jitter using time
    delay = max(0.1, delay + jitter)
    
    logger.info(f"Backing off for {delay:.2f}s (attempt {attempt})")
    await asyncio.sleep(delay)


def validate_subreddit_name(subreddit: str) -> bool:
    """Validate subreddit name format."""
    if not subreddit:
        return False
    
    # Remove r/ prefix if present
    if subreddit.startswith("r/"):
        subreddit = subreddit[2:]
    
    # Check format: 3-21 characters, alphanumeric + underscore
    pattern = r'^[A-Za-z0-9_]{3,21}$'
    return bool(re.match(pattern, subreddit))


def validate_post_title(title: str) -> Tuple[bool, Optional[str]]:
    """Validate Reddit post title."""
    if not title:
        return False, "Title cannot be empty"
    
    if len(title) > 300:
        return False, "Title cannot exceed 300 characters"
    
    if len(title.strip()) < 1:
        return False, "Title cannot be only whitespace"
    
    # Check for common formatting issues
    if title.startswith(" ") or title.endswith(" "):
        return False, "Title cannot start or end with spaces"
    
    return True, None


def validate_post_body(body: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Validate Reddit post body text."""
    if body is None:
        return True, None
    
    if len(body) > 40000:
        return False, "Post body cannot exceed 40,000 characters"
    
    return True, None


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL for link posts."""
    if not url:
        return False, "URL cannot be empty"
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "Invalid URL format"
        
        if parsed.scheme not in ["http", "https"]:
            return False, "URL must use HTTP or HTTPS"
        
        return True, None
        
    except Exception as e:
        return False, f"URL validation error: {str(e)}"


def get_mime_type(url: str) -> Optional[str]:
    """Get MIME type from URL or filename."""
    try:
        # Try to get from URL extension
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        mime_type, _ = mimetypes.guess_type(path)
        return mime_type
        
    except Exception:
        return None


def is_image_url(url: str) -> bool:
    """Check if URL points to an image."""
    mime_type = get_mime_type(url)
    if mime_type:
        return mime_type.startswith("image/")
    
    # Fallback: check common image extensions
    image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"]
    return any(url.lower().endswith(ext) for ext in image_extensions)


def is_video_url(url: str) -> bool:
    """Check if URL points to a video."""
    mime_type = get_mime_type(url)
    if mime_type:
        return mime_type.startswith("video/")
    
    # Fallback: check common video extensions
    video_extensions = [".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"]
    return any(url.lower().endswith(ext) for ext in video_extensions)


def clean_subreddit_name(subreddit: str) -> str:
    """Clean and normalize subreddit name."""
    if not subreddit:
        return ""
    
    # Remove r/ prefix
    if subreddit.startswith("r/"):
        subreddit = subreddit[2:]
    
    # Convert to lowercase and strip whitespace
    return subreddit.lower().strip()


def format_reddit_url(path: str) -> str:
    """Format a Reddit URL path into a full URL."""
    if not path:
        return ""
    
    if path.startswith("http"):
        return path
    
    if not path.startswith("/"):
        path = "/" + path
    
    return f"https://reddit.com{path}"


def extract_reddit_id(fullname_or_url: str) -> Optional[str]:
    """Extract Reddit ID from fullname (t3_abc123) or URL."""
    if not fullname_or_url:
        return None
    
    # Handle fullname format (t3_abc123, t1_def456, etc.)
    if fullname_or_url.startswith("t"):
        parts = fullname_or_url.split("_", 1)
        if len(parts) == 2:
            return parts[1]
    
    # Handle Reddit URLs
    if "reddit.com" in fullname_or_url:
        # Extract from URLs like https://reddit.com/r/test/comments/abc123/title/
        match = re.search(r'/comments/([a-zA-Z0-9]+)/', fullname_or_url)
        if match:
            return match.group(1)
    
    return None


async def get_subreddit_info(subreddit: str, use_cache: bool = True) -> Dict[str, Any]:
    """Get cached or fresh subreddit information including rules and flairs."""
    subreddit = clean_subreddit_name(subreddit)
    cache_key = f"subreddit:{subreddit}"
    
    # Check cache
    if use_cache and cache_key in _subreddit_cache:
        cached = _subreddit_cache[cache_key]
        if time.time() - cached["cached_at"] < _cache_ttl:
            return cached["data"]
    
    # In a real implementation, this would fetch from Reddit API
    # For now, return a mock structure
    info = {
        "name": subreddit,
        "display_name": subreddit,
        "subscribers": 0,
        "over18": False,
        "allow_images": True,
        "allow_videos": True,
        "allow_polls": False,
        "submission_type": "any",  # any, link, self
        "rules": [],
        "flairs": []
    }
    
    # Cache the result
    _subreddit_cache[cache_key] = {
        "data": info,
        "cached_at": time.time()
    }
    
    logger.debug(f"Cached subreddit info for r/{subreddit}")
    return info


async def get_subreddit_flairs(subreddit: str) -> List[Dict[str, Any]]:
    """Get available post flairs for a subreddit."""
    info = await get_subreddit_info(subreddit)
    return info.get("flairs", [])


async def validate_flair_id(subreddit: str, flair_id: Optional[str]) -> bool:
    """Validate that a flair ID exists for the subreddit."""
    if not flair_id:
        return True  # No flair is valid
    
    flairs = await get_subreddit_flairs(subreddit)
    return any(flair.get("id") == flair_id for flair in flairs)


def generate_mock_reddit_id() -> str:
    """Generate a mock Reddit ID for testing."""
    import random
    import string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))


def generate_mock_fullname(kind: str = "t3") -> str:
    """Generate a mock Reddit fullname for testing."""
    return f"{kind}_{generate_mock_reddit_id()}"


def parse_reddit_timestamp(timestamp: Optional[float]) -> Optional[datetime]:
    """Parse Reddit UTC timestamp to datetime."""
    if timestamp is None:
        return None
    
    try:
        return datetime.utcfromtimestamp(timestamp)
    except (ValueError, OSError):
        return None


def format_reddit_score(score: int) -> str:
    """Format Reddit score for display."""
    if score >= 1000000:
        return f"{score / 1000000:.1f}M"
    elif score >= 1000:
        return f"{score / 1000:.1f}k"
    else:
        return str(score)


def calculate_hot_score(score: int, created_utc: datetime) -> float:
    """Calculate Reddit hot score algorithm approximation."""
    # Simplified version of Reddit's hot score
    # Real algorithm is more complex and includes other factors
    epoch = datetime(1970, 1, 1)
    td = created_utc - epoch
    epoch_seconds = td.total_seconds()
    
    # Hot score based on time and vote score
    order = max(1, abs(score))
    sign = 1 if score > 0 else -1 if score < 0 else 0
    
    return sign * order + epoch_seconds / 45000


def should_retry_error(error_message: str) -> bool:
    """Check if an error should trigger a retry."""
    retry_keywords = [
        "rate limit",
        "too many requests",
        "server error",
        "timeout",
        "connection",
        "503",
        "502",
        "500"
    ]
    
    error_lower = error_message.lower()
    return any(keyword in error_lower for keyword in retry_keywords)