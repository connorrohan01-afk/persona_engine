"""SDK runner for file patching using Claude AI."""

import os
from typing import Dict, Any
from anthropic import Anthropic
from utils.files import read_text, write_text, sha1, count_line_changes


def patch_file(path: str, goal: str) -> Dict[str, Any]:
    """
    Patch a file using Claude AI based on a goal description.
    
    Args:
        path: File path to patch
        goal: Goal description for the patch
        
    Returns:
        Dict with:
            - ok: bool (success/failure)
            - lines_changed: int (number of lines changed)
            - sha1_before: str (hash before patch)
            - sha1_after: str (hash after patch)
            - error: str (error message if failed)
    """
    try:
        # Read original file
        try:
            original = read_text(path)
            sha1_before = sha1(path)
        except FileNotFoundError:
            # File doesn't exist, create new one
            original = ""
            sha1_before = "NEW_FILE"
        
        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {
                "ok": False,
                "error": "ANTHROPIC_API_KEY not configured",
                "lines_changed": 0,
                "sha1_before": sha1_before,
                "sha1_after": sha1_before
            }
        
        client = Anthropic(api_key=api_key)
        
        # Build prompt
        prompt = f"""Return ONLY the full new file content. File: {path}. Goal: {goal}. Original:
'''{original}'''"""
        
        # Call Claude
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract response
        new_content = message.content[0].text
        
        # Write new content
        write_text(path, new_content)
        sha1_after = sha1(path)
        
        # Count changes
        lines_changed = count_line_changes(original, new_content)
        
        return {
            "ok": True,
            "lines_changed": lines_changed,
            "sha1_before": sha1_before,
            "sha1_after": sha1_after
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "lines_changed": 0,
            "sha1_before": sha1_before if 'sha1_before' in locals() else "UNKNOWN",
            "sha1_after": sha1_before if 'sha1_before' in locals() else "UNKNOWN"
        }
