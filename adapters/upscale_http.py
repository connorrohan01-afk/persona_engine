import os, time, requests
from pathlib import Path

UPSCALE_PROVIDER = os.getenv("UPSCALE_PROVIDER", "generic")   # "bigjpg" | "replicate" | "clipdrop" | "generic"
UPSCALE_URL      = os.getenv("UPSCALE_URL")                   # e.g. Bigjpg endpoint or your proxy
UPSCALE_KEY      = os.getenv("UPSCALE_KEY")                   # API key
UPSCALE_SCALE    = int(os.getenv("UPSCALE_SCALE", "2"))       # 2 or 4
UPSCALE_FACE     = os.getenv("UPSCALE_FACE", "true")          # "true"/"false"

def upscale_image(input_path: str, out_path: str) -> str:
    if not UPSCALE_URL:
        raise ValueError("UPSCALE_URL environment variable is required")
    
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(input_path, "rb") as f:
        files = {"image": (Path(input_path).name, f, "image/jpeg")}
        headers = {"Authorization": f"Bearer {UPSCALE_KEY}"} if UPSCALE_KEY else {}
        data = {"scale": UPSCALE_SCALE, "face_enhance": UPSCALE_FACE}

        # One-shot or "submit + poll" depending on provider
        r = requests.post(UPSCALE_URL, headers=headers, data=data, files=files, timeout=60)
        r.raise_for_status()
        # Handle either direct binary or JSON with url/base64:
        if r.headers.get("content-type","").startswith("image/"):
            open(out_path, "wb").write(r.content)
            return out_path
        j = r.json()
        # Normalize common shapes:
        if "image_url" in j:
            img = requests.get(j["image_url"], timeout=60); img.raise_for_status()
            open(out_path, "wb").write(img.content); return out_path
        if "result" in j and "image" in j["result"] and j["result"]["image"].startswith("http"):
            img = requests.get(j["result"]["image"], timeout=60); img.raise_for_status()
            open(out_path, "wb").write(img.content); return out_path
        raise RuntimeError(f"Upscale response not understood: {j}")