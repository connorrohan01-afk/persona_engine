import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from adapters.upscale_http import upscale_image

def process_output(img_path, persona_id, job_id, style, idx):
    # polish paths
    base_dir = Path(f"vault/dev/{persona_id}/{job_id}/{style}")
    raw_path  = base_dir / f"raw_{idx:03d}.jpg"
    out_path  = base_dir / f"image_{idx:03d}.jpg"
    base_dir.mkdir(parents=True, exist_ok=True)

    # move raw → raw_path (if generator wrote elsewhere)
    Path(img_path).replace(raw_path)

    # upscale + (optional) face polish inside adapter/provider
    try:
        final_path = upscale_image(str(raw_path), str(out_path))
    except (ValueError, Exception) as e:
        # If upscaling fails (no URL configured), just copy raw to final
        print(f"Upscaling failed: {e}, copying raw to final")
        Path(raw_path).replace(out_path)
        final_path = str(out_path)

    # return record for manifest
    return {
        "file": str(Path(final_path)),
        "seed": None,           # fill if your generator returns it
        "provider": os.getenv("UPSCALE_PROVIDER","generic"),
        "scale": int(os.getenv("UPSCALE_SCALE","2")),
    }

def generate_fake_images(persona_id: str, job_id: str, style: str = "studio", count: int = 3):
    """Generate fake placeholder images for testing"""
    base_dir = Path(f"vault/dev/{persona_id}/{job_id}/{style}")
    base_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for i in range(1, count + 1):
        # Create a simple image with text
        img_width, img_height = 512, 512
        img = Image.new('RGB', (img_width, img_height), color='lightblue')
        draw = ImageDraw.Draw(img)
        
        # Try to use a default font, fallback to basic if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Draw text on the image
        text_lines = [
            f"FAKE IMAGE {persona_id}",
            f"Job: {job_id}",
            f"Style: {style}",
            f"Image {i:03d}"
        ]
        
        y_offset = img_height // 2 - 50
        for line in text_lines:
            if font:
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
            else:
                text_width = len(line) * 6  # rough estimate
            
            x = (img_width - text_width) // 2
            draw.text((x, y_offset), line, fill='darkblue', font=font)
            y_offset += 30
        
        # Save as temporary file first
        temp_path = base_dir / f"temp_{i:03d}.jpg"
        img.save(temp_path, 'JPEG', quality=85)
        
        # Process through upscaling pipeline
        result = process_output(str(temp_path), persona_id, job_id, style, i)
        results.append(result)
    
    return results

def run_fake_gen(persona_id: str, style: str, job_id: str, count: int = 3):
    """Main entry point for fake generation provider"""
    print(f"🎭 Running fake generation for {persona_id} (job: {job_id})")
    results = generate_fake_images(persona_id, job_id, style, count)
    return {
        "ok": True,
        "job_id": job_id,
        "persona": persona_id,
        "style": style,
        "count": len(results),
        "images": results
    }

if __name__ == "__main__":
    # Test the fake generator
    results = generate_fake_images("P0001", "20250927000000", "studio", 2)
    print("Generated fake images:", results)