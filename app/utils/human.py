"""Humanization utilities for realistic timing and behavior patterns."""

import random
import time
from typing import Dict, List, Any
from datetime import datetime, timedelta
from loguru import logger


def sleep_jitter(base_ms: int, spread: float = 0.3) -> int:
    """
    Add jitter to a base sleep time.
    
    Args:
        base_ms: Base sleep time in milliseconds
        spread: Jitter spread as percentage (0.3 = ±30%)
        
    Returns:
        Jittered sleep time in milliseconds
    """
    jitter = random.uniform(-spread, spread)
    result = int(base_ms * (1 + jitter))
    return max(100, result)  # Minimum 100ms


def human_wait(kind: str) -> int:
    """
    Get human-like wait time for different action types.
    
    Args:
        kind: Type of action (browse, read, scroll, click, etc.)
        
    Returns:
        Wait time in milliseconds
    """
    base_times = {
        "page_load": 2000,      # 2 seconds to load and scan page
        "read_post": 8000,      # 8 seconds to read a post
        "read_comment": 3000,   # 3 seconds to read a comment
        "scroll": 1500,         # 1.5 seconds between scrolls
        "click": 800,           # 0.8 seconds to process and click
        "type": 150,            # 150ms per character typed
        "browse": 5000,         # 5 seconds browsing between actions
        "vote": 1200,           # 1.2 seconds to decide and vote
        "save": 800,            # 0.8 seconds to save
        "join": 3000,           # 3 seconds to consider joining
        "comment_compose": 15000,  # 15 seconds to compose comment
        "post_compose": 45000,  # 45 seconds to compose post
    }
    
    base_time = base_times.get(kind, 2000)  # Default 2 seconds
    return sleep_jitter(base_time, spread=0.4)  # ±40% jitter


def human_sleep(kind: str) -> None:
    """
    Sleep for a human-like duration.
    
    Args:
        kind: Type of action to sleep for
    """
    wait_ms = human_wait(kind)
    time.sleep(wait_ms / 1000.0)
    logger.debug(f"Human wait: {kind} -> {wait_ms}ms")


def pick_subreddits(tier: str, n: int = 5) -> List[str]:
    """
    Pick subreddits for warming activities.
    
    Args:
        tier: Tier of subreddits ('safe', 'interest', 'niche')
        n: Number of subreddits to pick
        
    Returns:
        List of subreddit names
    """
    subreddit_pools = {
        "safe": [
            "askreddit", "pics", "funny", "mildlyinteresting", 
            "showerthoughts", "todayilearned", "lifeprotips",
            "explainlikeimfive", "wholesomememes", "aww",
            "gaming", "movies", "music", "books", "food",
            "earthporn", "natureisfuckinglit", "oddlysatisfying",
            "getmotivated", "upliftingnews", "humansbeingbros"
        ],
        "interest": [
            "technology", "science", "worldnews", "politics",
            "personalfinance", "fitness", "cooking", "diy",
            "art", "photography", "travel", "history",
            "philosophy", "psychology", "startups", "entrepreneur",
            "learnprogramming", "webdev", "datascience", "machinelearning"
        ],
        "niche": [
            "mechanicalkeyboards", "houseplants", "sourdough",
            "3dprinting", "arduino", "raspberry_pi", "homelab",
            "coffee", "tea", "cocktails", "breadit", "fermentation",
            "mycology", "bonsai", "cacti", "succulents", "orchids"
        ]
    }
    
    pool = subreddit_pools.get(tier, subreddit_pools["safe"])
    selected = random.sample(pool, min(n, len(pool)))
    
    logger.info(f"Picked {len(selected)} {tier} subreddits: {selected}")
    return selected


def generate_comment_text(context: str = "general") -> str:
    """
    Generate realistic comment text.
    
    Args:
        context: Context for the comment (general, positive, question, etc.)
        
    Returns:
        Generated comment text
    """
    templates = {
        "positive": [
            "This is really helpful, thanks for sharing!",
            "Great point! I hadn't thought of it that way.",
            "Thanks for the detailed explanation.",
            "This is exactly what I was looking for.",
            "Really appreciate you taking the time to write this out.",
            "This is super useful, saved for later!",
            "Wow, I learned something new today.",
            "This made my day, thank you!",
        ],
        "question": [
            "Has anyone else experienced this?",
            "What's been your experience with this?",
            "Any recommendations for someone just starting out?",
            "Is there a better way to approach this?",
            "What would you do in this situation?",
            "Can someone explain this in more detail?",
            "Where can I learn more about this topic?",
            "What are the pros and cons here?",
        ],
        "general": [
            "Interesting perspective!",
            "Good to know.",
            "Makes sense.",
            "I agree with this.",
            "Fair point.",
            "Well said.",
            "This is useful.",
            "Thanks for sharing.",
            "Good catch!",
            "Noted, thanks.",
        ]
    }
    
    pool = templates.get(context, templates["general"])
    comment = random.choice(pool)
    
    # Add occasional variations
    if random.random() < 0.1:  # 10% chance to add emphasis
        comment += " 👍"
    
    logger.debug(f"Generated {context} comment: {comment}")
    return comment


def generate_post_title(subreddit: str, post_type: str = "question") -> str:
    """
    Generate realistic post titles.
    
    Args:
        subreddit: Target subreddit
        post_type: Type of post (question, discussion, share)
        
    Returns:
        Generated post title
    """
    title_templates = {
        "question": [
            "Quick question about {topic}",
            "New to {topic}, need advice",
            "Help with {topic} - what am I doing wrong?",
            "Best practices for {topic}?",
            "Anyone have experience with {topic}?",
            "{topic} beginner - looking for guidance",
            "Stuck with {topic}, any suggestions?",
        ],
        "discussion": [
            "Let's discuss {topic}",
            "Thoughts on {topic}?",
            "What's your take on {topic}?",
            "{topic} - pros and cons?",
            "How do you approach {topic}?",
            "Community opinion on {topic}?",
        ],
        "share": [
            "Just learned about {topic}",
            "Sharing my experience with {topic}",
            "Found this useful for {topic}",
            "My journey with {topic}",
            "Tips for {topic} from a beginner",
        ]
    }
    
    # Simple topic extraction from subreddit
    topic = subreddit.replace("_", " ").replace("r/", "")
    
    template = random.choice(title_templates.get(post_type, title_templates["question"]))
    title = template.format(topic=topic)
    
    logger.debug(f"Generated {post_type} title for r/{subreddit}: {title}")
    return title


def randomize_schedule(base_hours: float) -> datetime:
    """
    Randomize a schedule around a base time.
    
    Args:
        base_hours: Base time in hours from now
        
    Returns:
        Randomized future datetime
    """
    # Add ±25% jitter to the base time
    jitter_hours = base_hours * random.uniform(-0.25, 0.25)
    total_hours = base_hours + jitter_hours
    
    # Ensure minimum of 5 minutes from now
    total_hours = max(total_hours, 5/60)
    
    scheduled_time = datetime.utcnow() + timedelta(hours=total_hours)
    
    logger.debug(f"Randomized schedule: {base_hours}h base -> {total_hours:.2f}h -> {scheduled_time.isoformat()}")
    return scheduled_time


def get_diurnal_multiplier() -> float:
    """
    Get time-of-day multiplier for activity levels.
    
    Returns:
        Multiplier for activity (1.0 = normal, <1.0 = more active, >1.0 = less active)
    """
    current_hour = datetime.utcnow().hour
    
    # Activity curve: higher activity 10am-8pm, lower at night
    if 6 <= current_hour <= 9:        # Early morning
        return 1.5
    elif 10 <= current_hour <= 20:    # Prime time
        return 0.8
    elif 21 <= current_hour <= 23:    # Evening
        return 1.2
    else:                             # Night/very early morning
        return 2.0


def should_be_active() -> bool:
    """
    Determine if this is a good time to be active based on diurnal patterns.
    
    Returns:
        True if should be active, False if should be quiet
    """
    multiplier = get_diurnal_multiplier()
    
    # Higher multiplier = less likely to be active
    activity_chance = 1.0 / multiplier
    
    # Base activity rate of 30%
    base_rate = 0.3
    
    result = random.random() < (base_rate * activity_chance)
    
    logger.debug(f"Activity check: multiplier={multiplier:.2f}, chance={activity_chance:.2f}, active={result}")
    return result


def get_typing_delay(text: str) -> float:
    """
    Calculate realistic typing delay for text.
    
    Args:
        text: Text to type
        
    Returns:
        Typing delay in seconds
    """
    # Base typing speed: 40 WPM = ~200 chars/minute = 3.33 chars/second
    base_chars_per_second = 3.33
    
    # Add thinking pauses for punctuation and spaces
    char_count = len(text)
    thinking_pauses = text.count('.') + text.count(',') + text.count('!') + text.count('?')
    space_pauses = text.count(' ')
    
    # Base typing time
    typing_time = char_count / base_chars_per_second
    
    # Add pause time (longer pauses for punctuation)
    pause_time = thinking_pauses * 0.5 + space_pauses * 0.1
    
    # Add random variance ±20%
    total_time = (typing_time + pause_time) * random.uniform(0.8, 1.2)
    
    return max(0.5, total_time)  # Minimum 0.5 seconds


def simulate_reading_time(content_length: int, content_type: str = "post") -> float:
    """
    Simulate realistic reading time.
    
    Args:
        content_length: Length of content in characters
        content_type: Type of content (post, comment, title)
        
    Returns:
        Reading time in seconds
    """
    # Reading speeds (characters per second)
    reading_speeds = {
        "title": 10,      # Fast scan of titles
        "comment": 8,     # Normal reading speed
        "post": 6,        # Slower, more careful reading
    }
    
    chars_per_second = reading_speeds.get(content_type, 8)
    base_time = content_length / chars_per_second
    
    # Add minimum time and jitter
    min_times = {"title": 0.5, "comment": 1.0, "post": 2.0}
    min_time = min_times.get(content_type, 1.0)
    
    reading_time = max(min_time, base_time * random.uniform(0.7, 1.3))
    
    return reading_time