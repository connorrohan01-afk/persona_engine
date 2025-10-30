import os
import requests
import logging
from typing import Dict

logger = logging.getLogger(__name__)

QODER_URL = os.environ.get("QODER_URL", "")

def send_message(payload: dict) -> dict:
    """Send a message to the Qoder service"""
    if not QODER_URL:
        return {"ok": False, "error": "QODER_URL not set"}
    
    url = f"{QODER_URL}/chat"
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"Qoder request successful: {response.status_code}")
            return {
                "ok": True, 
                "data": response.json()
            }
        else:
            logger.error(f"Qoder request failed: {response.status_code}")
            return {
                "ok": False, 
                "error": f"Qoder service returned {response.status_code}"
            }
    
    except requests.RequestException as e:
        logger.error(f"Qoder request failed: {str(e)}")
        return {"ok": False, "error": f"Request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error calling Qoder: {str(e)}")
        return {"ok": False, "error": f"Unexpected error: {str(e)}"}