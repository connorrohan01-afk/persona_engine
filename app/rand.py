"""Random helpers for weighted selection, jitter, and human timing."""

import random
import asyncio
from typing import List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class WeightedItem:
    """Item with weight for weighted random selection."""
    item: Any
    weight: float


def weighted_random_choice(items: List[WeightedItem]) -> Optional[Any]:
    """Select random item based on weights.
    
    Args:
        items: List of WeightedItem objects
        
    Returns:
        Selected item or None if empty list
    """
    if not items:
        return None
    
    total_weight = sum(item.weight for item in items)
    if total_weight <= 0:
        return None
    
    rand = random.uniform(0, total_weight)
    current = 0
    
    for item in items:
        current += item.weight
        if rand <= current:
            return item.item
    
    # Fallback to last item (shouldn't happen)
    return items[-1].item


def weighted_random_sample(items: List[WeightedItem], k: int) -> List[Any]:
    """Select k random items based on weights without replacement.
    
    Args:
        items: List of WeightedItem objects
        k: Number of items to select
        
    Returns:
        List of selected items (may be fewer than k if not enough items)
    """
    if not items or k <= 0:
        return []
    
    k = min(k, len(items))
    remaining = items.copy()
    selected = []
    
    for _ in range(k):
        choice = weighted_random_choice(remaining)
        if choice is None:
            break
        
        selected.append(choice)
        # Remove selected item from remaining
        remaining = [item for item in remaining if item.item != choice]
    
    return selected


def jitter_seconds(min_seconds: int = 15, max_seconds: int = 120) -> int:
    """Generate random jitter in seconds for human timing.
    
    Args:
        min_seconds: Minimum jitter seconds
        max_seconds: Maximum jitter seconds
        
    Returns:
        Random number of seconds
    """
    return random.randint(min_seconds, max_seconds)


async def sleep_with_jitter(base_seconds: float = 0, min_jitter: int = 15, max_jitter: int = 120) -> None:
    """Sleep for base time plus random jitter.
    
    Args:
        base_seconds: Base sleep time in seconds
        min_jitter: Minimum jitter seconds to add
        max_jitter: Maximum jitter seconds to add
    """
    jitter = jitter_seconds(min_jitter, max_jitter)
    total_sleep = base_seconds + jitter
    await asyncio.sleep(total_sleep)


def human_delay_range() -> Tuple[int, int]:
    """Get human-like delay range in seconds.
    
    Returns:
        Tuple of (min_delay, max_delay) for human-like pauses
    """
    # Common human pause patterns
    patterns = [
        (2, 8),      # Quick scan
        (5, 15),     # Reading
        (10, 30),    # Thinking
        (15, 45),    # Careful consideration
        (30, 90),    # Distracted/multitasking
    ]
    
    return random.choice(patterns)


def random_time_in_window(window_start: str, window_end: str, base_date: Optional[datetime] = None) -> datetime:
    """Generate random time within a daily window.
    
    Args:
        window_start: Start time string like "08:00"
        window_end: End time string like "22:00"
        base_date: Base date to use (defaults to today)
        
    Returns:
        Random datetime within the window
    """
    if base_date is None:
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Parse time strings
    start_hour, start_minute = map(int, window_start.split(":"))
    end_hour, end_minute = map(int, window_end.split(":"))
    
    # Create datetime objects for window bounds
    window_start_dt = base_date.replace(hour=start_hour, minute=start_minute)
    window_end_dt = base_date.replace(hour=end_hour, minute=end_minute)
    
    # Handle overnight windows (end < start)
    if window_end_dt <= window_start_dt:
        window_end_dt += timedelta(days=1)
    
    # Generate random time within window
    total_seconds = (window_end_dt - window_start_dt).total_seconds()
    random_seconds = random.uniform(0, total_seconds)
    
    return window_start_dt + timedelta(seconds=random_seconds)


def is_time_in_window(check_time: datetime, window_start: str, window_end: str) -> bool:
    """Check if time falls within daily window.
    
    Args:
        check_time: Time to check
        window_start: Start time string like "08:00"
        window_end: End time string like "22:00"
        
    Returns:
        True if time is within window
    """
    # Extract time components
    check_hour = check_time.hour
    check_minute = check_time.minute
    check_total_minutes = check_hour * 60 + check_minute
    
    # Parse window times
    start_hour, start_minute = map(int, window_start.split(":"))
    end_hour, end_minute = map(int, window_end.split(":"))
    
    start_total_minutes = start_hour * 60 + start_minute
    end_total_minutes = end_hour * 60 + end_minute
    
    # Handle overnight windows
    if end_total_minutes <= start_total_minutes:
        # Overnight window: after start OR before end
        return check_total_minutes >= start_total_minutes or check_total_minutes <= end_total_minutes
    else:
        # Normal window: between start and end
        return start_total_minutes <= check_total_minutes <= end_total_minutes


def distribute_actions_over_day(count: int, window_start: str, window_end: str, 
                                base_date: Optional[datetime] = None) -> List[datetime]:
    """Distribute actions randomly over a day within the window.
    
    Args:
        count: Number of actions to distribute
        window_start: Start time string like "08:00"
        window_end: End time string like "22:00"
        base_date: Base date to use (defaults to today)
        
    Returns:
        List of datetime objects sorted chronologically
    """
    if count <= 0:
        return []
    
    times = []
    for _ in range(count):
        time = random_time_in_window(window_start, window_end, base_date)
        times.append(time)
    
    # Sort chronologically
    times.sort()
    return times


def exponential_backoff_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 300.0) -> float:
    """Calculate exponential backoff delay with jitter.
    
    Args:
        attempt: Attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Delay in seconds with jitter
    """
    # Exponential backoff: base_delay * 2^attempt
    delay = base_delay * (2 ** attempt)
    delay = min(delay, max_delay)
    
    # Add jitter (±25%)
    jitter_factor = random.uniform(0.75, 1.25)
    delay *= jitter_factor
    
    return delay