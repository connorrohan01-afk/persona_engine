"""
Production-ready image generation service with pluggable providers
"""
import os
import re
import json
import time
import base64
import hashlib
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, List
from PIL import Image, ImageDraw, ImageFont


# Blocked keywords for safety
BLOCKED_KEYWORDS = [
    'nsfw', 'nude', 'naked', 'porn', 'sexual', 'explicit', 'adult', 'xxx',
    'violence', 'blood', 'murder', 'kill', 'death', 'suicide', 'harm',
    'hate', 'racist', 'nazi', 'terrorist', 'drug', 'cocaine', 'heroin'
]


def ensure_dirs():
    """Create required directories if they don't exist"""
    os.makedirs('static/images', exist_ok=True)
    os.makedirs('data/images', exist_ok=True)


def slugify(text: str, max_length: int = 10) -> str:
    """Convert text to URL-friendly slug with max length"""
    # Remove non-alphanumeric characters and convert to lowercase
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
    # Replace spaces and hyphens with single hyphen
    slug = re.sub(r'[-\s]+', '-', slug)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    # Truncate to max length
    return slug[:max_length] if slug else 'image'


def check_prompt_safety(prompt: str) -> Optional[str]:
    """Check if prompt contains blocked keywords"""
    prompt_lower = prompt.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in prompt_lower:
            return f"blocked_keyword_{keyword}"
    return None


def validate_image_quality(image_path: str) -> bool:
    """Validate generated image meets quality requirements"""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            # Check minimum resolution
            if width < 512 or height < 512:
                return False
            return True
    except Exception as e:
        logging.error(f"Error validating image quality: {e}")
        return False


def generate_mock_image(prompt: str, size: str = "1024x1024") -> bytes:
    """Generate a mock image with prompt text using Pillow"""
    try:
        # Parse size
        width, height = map(int, size.split('x'))
        
        # Create image with gradient background
        image = Image.new('RGB', (width, height), color='#2a2a2a')
        draw = ImageDraw.Draw(image)
        
        # Try to load a better font, fall back to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Draw gradient effect
        for i in range(height):
            color_val = int(42 + (213 - 42) * (i / height))
            draw.rectangle([0, i, width, i+1], fill=(color_val//3, color_val//2, color_val))
        
        # Prepare text
        title = "GENERATED IMAGE"
        subtitle = f"Prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
        footer = f"Mock Provider • {size}"
        
        # Draw title
        if font:
            title_bbox = draw.textbbox((0, 0), title, font=font)
            title_width = title_bbox[2] - title_bbox[0]
            draw.text(((width - title_width) // 2, height // 2 - 80), title, 
                     fill='white', font=font)
            
            # Draw subtitle with smaller font
            try:
                small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except:
                small_font = font
                
            subtitle_bbox = draw.textbbox((0, 0), subtitle, font=small_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            draw.text(((width - subtitle_width) // 2, height // 2 - 20), subtitle, 
                     fill='#cccccc', font=small_font)
            
            # Draw footer
            try:
                tiny_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except:
                tiny_font = small_font
                
            footer_bbox = draw.textbbox((0, 0), footer, font=tiny_font)
            footer_width = footer_bbox[2] - footer_bbox[0]
            draw.text(((width - footer_width) // 2, height // 2 + 40), footer, 
                     fill='#888888', font=tiny_font)
        else:
            # Fallback without font
            draw.text((width//4, height//2 - 20), title, fill='white')
            draw.text((width//4, height//2 + 20), subtitle, fill='#cccccc')
        
        # Add decorative border
        border_width = 4
        draw.rectangle([0, 0, width, border_width], fill='#4a90e2')
        draw.rectangle([0, height-border_width, width, height], fill='#4a90e2')
        draw.rectangle([0, 0, border_width, height], fill='#4a90e2')
        draw.rectangle([width-border_width, 0, width, height], fill='#4a90e2')
        
        # Convert to bytes
        from io import BytesIO
        img_buffer = BytesIO()
        image.save(img_buffer, format='PNG', quality=95)
        return img_buffer.getvalue()
        
    except Exception as e:
        logging.error(f"Error generating mock image: {e}")
        # Ultra-fallback: minimal image
        image = Image.new('RGB', (512, 512), color='#666666')
        draw = ImageDraw.Draw(image)
        draw.text((50, 250), "Mock Image", fill='white')
        from io import BytesIO
        img_buffer = BytesIO()
        image.save(img_buffer, format='PNG')
        return img_buffer.getvalue()


def generate_openai_image(prompt: str, size: str = "1024x1024") -> Optional[bytes]:
    """Generate image using OpenAI API"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    
    try:
        # Use requests instead of heavy SDK
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "dall-e-3",  # Use DALL-E 3 for better quality
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json"
        }
        
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("data") and len(data["data"]) > 0:
                b64_data = data["data"][0].get("b64_json")
                if b64_data:
                    return base64.b64decode(b64_data)
        
        logging.error(f"OpenAI API error: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logging.error(f"Error calling OpenAI API: {e}")
        return None


def generate_stability_image(prompt: str, style: Optional[str] = None, size: str = "1024x1024") -> Optional[bytes]:
    """Generate image using Stability API"""
    api_key = os.environ.get("STABILITY_API_KEY")
    if not api_key:
        return None
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Parse size to width/height
        width, height = map(int, size.split('x'))
        
        payload = {
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": height,
            "width": width,
            "samples": 1,
            "steps": 30
        }
        
        # Add style if provided
        if style:
            payload["style_preset"] = style
        
        response = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("artifacts") and len(data["artifacts"]) > 0:
                b64_data = data["artifacts"][0].get("base64")
                if b64_data:
                    return base64.b64decode(b64_data)
        
        logging.error(f"Stability API error: {response.status_code} - {response.text}")
        return None
        
    except Exception as e:
        logging.error(f"Error calling Stability API: {e}")
        return None


def generate_image(prompt: str, style: Optional[str] = None, size: str = "1024x1024") -> Dict:
    """
    Main image generation function with pluggable providers
    
    Returns:
        {ok: bool, file_url?: str, meta_path?: str, error?: str, details?: str}
    """
    # Ensure directories exist
    ensure_dirs()
    
    # Safety check
    safety_error = check_prompt_safety(prompt)
    if safety_error:
        return {
            "ok": False,
            "error": "blocked_prompt",
            "details": f"Prompt contains blocked content: {safety_error}"
        }
    
    # Determine provider
    provider = os.environ.get("IMG_PROVIDER", "mock").lower()
    
    # Generate filename
    timestamp = int(time.time())
    slug = slugify(prompt)
    filename = f"{timestamp}_{slug}.png"
    file_path = os.path.join("static/images", filename)
    file_url = f"/static/images/{filename}"
    
    # Generate image bytes based on provider
    image_bytes = None
    actual_provider = provider
    
    if provider == "openai" and os.environ.get("OPENAI_API_KEY"):
        image_bytes = generate_openai_image(prompt, size)
        if not image_bytes:
            actual_provider = "mock"  # Fallback
    elif provider == "stability" and os.environ.get("STABILITY_API_KEY"):
        image_bytes = generate_stability_image(prompt, style, size)
        if not image_bytes:
            actual_provider = "mock"  # Fallback
    else:
        actual_provider = "mock"
    
    # Generate mock image if no provider worked or was selected
    if not image_bytes:
        image_bytes = generate_mock_image(prompt, size)
    
    try:
        # Save image
        with open(file_path, 'wb') as f:
            f.write(image_bytes)
        
        # Validate quality
        if not validate_image_quality(file_path):
            return {
                "ok": False,
                "error": "quality_check_failed",
                "details": "Generated image doesn't meet quality requirements"
            }
        
        # Get actual image dimensions
        with Image.open(file_path) as img:
            actual_width, actual_height = img.size
        
        # Create metadata
        metadata = {
            "prompt": prompt,
            "style": style,
            "requested_size": size,
            "actual_size": f"{actual_width}x{actual_height}",
            "provider": actual_provider,
            "width": actual_width,
            "height": actual_height,
            "created_at": datetime.now().isoformat(),
            "file_url": file_url,
            "filename": filename
        }
        
        # Save metadata
        meta_filename = f"{timestamp}_{slug}.json"
        meta_path = os.path.join("data/images", meta_filename)
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logging.info(f"Generated image: {filename} via {actual_provider} provider")
        
        return {
            "ok": True,
            "file_url": file_url,
            "meta_path": meta_path,
            "meta": {
                "size": f"{actual_width}x{actual_height}",
                "provider": actual_provider,
                "created_at": metadata["created_at"]
            }
        }
        
    except Exception as e:
        logging.error(f"Error saving image: {e}")
        return {
            "ok": False,
            "error": "save_failed",
            "details": str(e)
        }