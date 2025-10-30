"""File utilities for reading, writing, and diffing text files."""

import hashlib
import os
from pathlib import Path
from typing import Optional


def read_text(path: str) -> str:
    """
    Read text file and return contents.
    
    Args:
        path: File path to read
        
    Returns:
        File contents as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_text(path: str, text: str) -> None:
    """
    Write text to file, creating parent directories if needed.
    
    Args:
        path: File path to write
        text: Text content to write
    """
    # Create parent directories if they don't exist
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def sha1(path: str) -> str:
    """
    Compute SHA1 hash of file contents.
    
    Args:
        path: File path to hash
        
    Returns:
        SHA1 hash as hex string
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    try:
        content = read_text(path)
        return hashlib.sha1(content.encode('utf-8')).hexdigest()
    except FileNotFoundError:
        return "FILE_NOT_FOUND"


def git_diff(path: str, max_lines: int = 120) -> Optional[str]:
    """
    Get git diff for a file (if in git repo).
    
    Args:
        path: File path to diff
        max_lines: Maximum number of diff lines to return
        
    Returns:
        Git diff output or None if not in git repo
    """
    import subprocess
    
    try:
        result = subprocess.run(
            ['git', 'diff', path],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            if len(lines) > max_lines:
                lines = lines[:max_lines] + [f'... (truncated, {len(lines) - max_lines} more lines)']
            return '\n'.join(lines)
        return None
        
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def count_line_changes(old_text: str, new_text: str) -> int:
    """
    Count number of lines changed between two texts.
    
    Args:
        old_text: Original text
        new_text: New text
        
    Returns:
        Number of lines that differ
    """
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    
    # Simple diff: count lines that are different
    max_len = max(len(old_lines), len(new_lines))
    changes = 0
    
    for i in range(max_len):
        old_line = old_lines[i] if i < len(old_lines) else None
        new_line = new_lines[i] if i < len(new_lines) else None
        
        if old_line != new_line:
            changes += 1
    
    return changes
