"""Image generation providers for OpenAI, Replicate, Stability AI, and mock."""

import io
import base64
import random
from typing import Optional, Tuple, Dict, Any
import httpx
from PIL import Image, ImageDraw, ImageFont
from app.config import settings
from loguru import logger


class ImageProvider:
    """Base image generation provider."""
    
    def __init__(self):
        self.provider = settings.img_provider
        self.dry_run = self._should_dry_run()
    
    def _should_dry_run(self) -> bool:
        """Determine if we should run in dry-run mode."""
        if self.provider == "mock":
            return True
        
        # Check if we have the required API keys
        if self.provider == "openai" and not settings.openai_api_key:
            return True
        elif self.provider == "replicate" and not settings.replicate_api_token:
            return True
        elif self.provider == "stability" and not settings.stability_api_key:
            return True
        
        return False
    
    def generate_image(
        self, 
        prompt: str, 
        style: Optional[str] = None,
        width: int = 512,
        height: int = 512,
        dry: bool = False
    ) -> Tuple[bool, bytes, str, str]:
        """
        Generate an image from prompt.
        
        Returns:
            (success, image_bytes, mime_type, error_message)
        """
        # Force dry-run if explicitly requested or no valid provider
        if dry or self.dry_run:
            return self._generate_mock_image(prompt, width, height)
        
        # Validate and clamp dimensions
        width = max(256, min(2048, width))
        height = max(256, min(2048, height))
        
        try:
            if self.provider == "openai":
                return self._generate_openai(prompt, style, width, height)
            elif self.provider == "replicate":
                return self._generate_replicate(prompt, style, width, height)
            elif self.provider == "stability":
                return self._generate_stability(prompt, style, width, height)
            else:
                return self._generate_mock_image(prompt, width, height)
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return False, b"", "", str(e)
    
    def _generate_mock_image(self, prompt: str, width: int, height: int) -> Tuple[bool, bytes, str, str]:
        """Generate a mock placeholder image."""
        try:
            # Create a simple colored image with text
            img = Image.new('RGB', (width, height), color=(200, 200, 200))
            draw = ImageDraw.Draw(img)
            
            # Add "MOCK" text
            try:
                # Try to use a default font, fall back to basic if not available
                font = ImageFont.load_default()
            except:
                font = None
            
            text = "MOCK IMAGE"
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width = len(text) * 6  # Approximate
                text_height = 11
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            draw.text((x, y), text, fill=(100, 100, 100), font=font)
            
            # Add prompt text (truncated)
            prompt_text = prompt[:50] + "..." if len(prompt) > 50 else prompt
            if font:
                prompt_bbox = draw.textbbox((0, 0), prompt_text, font=font)
                prompt_width = prompt_bbox[2] - prompt_bbox[0]
            else:
                prompt_width = len(prompt_text) * 6
                
            prompt_x = (width - prompt_width) // 2
            prompt_y = y + text_height + 10
            
            if prompt_y + 20 < height:
                draw.text((prompt_x, prompt_y), prompt_text, fill=(150, 150, 150), font=font)
            
            # Save to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()
            
            logger.info(f"Generated mock image {width}x{height} for prompt: {prompt[:50]}")
            return True, image_bytes, "image/png", ""
            
        except Exception as e:
            logger.error(f"Failed to generate mock image: {e}")
            return False, b"", "", str(e)
    
    def _generate_openai(self, prompt: str, style: Optional[str], width: int, height: int) -> Tuple[bool, bytes, str, str]:
        """Generate image using OpenAI DALL-E."""
        try:
            # Use the new OpenAI SDK
            from openai import OpenAI
            
            client = OpenAI(api_key=settings.openai_api_key)
            
            # Adjust prompt based on style
            full_prompt = prompt
            if style:
                full_prompt = f"{style} style: {prompt}"
            
            # OpenAI DALL-E 3 supports specific sizes
            size = "1024x1024"  # Default
            if width == height:
                if width <= 512:
                    size = "1024x1024"
                elif width <= 1024:
                    size = "1024x1024"
                else:
                    size = "1024x1024"
            elif width > height:
                size = "1792x1024"
            else:
                size = "1024x1792"
            
            response = client.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                size=size,
                quality="standard",
                response_format="b64_json",
                n=1
            )
            
            if response.data and len(response.data) > 0:
                image_data = response.data[0]
                if hasattr(image_data, 'b64_json') and image_data.b64_json:
                    image_bytes = base64.b64decode(image_data.b64_json)
                else:
                    raise Exception("No b64_json data in OpenAI response")
            else:
                raise Exception("No image data in OpenAI response")
            
            # Resize if needed
            if size != f"{width}x{height}":
                img = Image.open(io.BytesIO(image_bytes))
                img = img.resize((width, height), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                image_bytes = buffer.getvalue()
            
            logger.info(f"Generated OpenAI image {width}x{height} for prompt: {prompt[:50]}")
            return True, image_bytes, "image/png", ""
            
        except Exception as e:
            logger.error(f"OpenAI image generation failed: {e}")
            return False, b"", "", str(e)
    
    def _generate_replicate(self, prompt: str, style: Optional[str], width: int, height: int) -> Tuple[bool, bytes, str, str]:
        """Generate image using Replicate."""
        try:
            # Use Replicate API
            import replicate
            
            # Set API token
            replicate.Client(api_token=settings.replicate_api_token)
            
            # Use SDXL model
            full_prompt = prompt
            if style:
                full_prompt = f"{style} style: {prompt}"
            
            output = replicate.run(
                "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                input={
                    "prompt": full_prompt,
                    "width": width,
                    "height": height,
                    "num_outputs": 1,
                    "guidance_scale": 7.5,
                    "num_inference_steps": 50
                }
            )
            
            # Download the image
            image_url = output[0]
            with httpx.Client() as client:
                response = client.get(image_url)
                response.raise_for_status()
                image_bytes = response.content
            
            logger.info(f"Generated Replicate image {width}x{height} for prompt: {prompt[:50]}")
            return True, image_bytes, "image/png", ""
            
        except Exception as e:
            logger.error(f"Replicate image generation failed: {e}")
            return False, b"", "", str(e)
    
    def _generate_stability(self, prompt: str, style: Optional[str], width: int, height: int) -> Tuple[bool, bytes, str, str]:
        """Generate image using Stability AI."""
        try:
            full_prompt = prompt
            if style:
                full_prompt = f"{style} style: {prompt}"
            
            url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
            
            headers = {
                "Authorization": f"Bearer {settings.stability_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            data = {
                "text_prompts": [{"text": full_prompt}],
                "cfg_scale": 7,
                "height": height,
                "width": width,
                "samples": 1,
                "steps": 30
            }
            
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=data, timeout=120)
                response.raise_for_status()
                
                result = response.json()
                image_data = result["artifacts"][0]["base64"]
                image_bytes = base64.b64decode(image_data)
            
            logger.info(f"Generated Stability AI image {width}x{height} for prompt: {prompt[:50]}")
            return True, image_bytes, "image/png", ""
            
        except Exception as e:
            logger.error(f"Stability AI image generation failed: {e}")
            return False, b"", "", str(e)


def check_nsfw_content(prompt: str) -> bool:
    """Basic NSFW content detection."""
    if settings.allow_nsfw:
        return False
    
    nsfw_keywords = [
        'nsfw', 'nude', 'naked', 'sex', 'sexual', 'erotic', 'porn', 'adult',
        'explicit', 'xxx', 'breast', 'ass', 'pussy', 'penis', 'vagina'
    ]
    
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in nsfw_keywords)


# Global provider instance
image_provider = ImageProvider()