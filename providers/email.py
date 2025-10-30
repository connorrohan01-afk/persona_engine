"""Email provider for creating temporary email addresses."""

import os
import random
import string
from typing import Dict, Optional
from loguru import logger


class EmailProvider:
    """Email provider for managing temporary email addresses."""
    
    def __init__(self):
        # Check for various email provider configurations
        self.gmail_credentials = os.getenv("GMAIL_CREDENTIALS")
        self.mailtm_api_key = os.getenv("MAILTM_API_KEY")
        self.email_forwarder_url = os.getenv("EMAIL_FORWARDER_URL")
        
        self.is_live = bool(self.gmail_credentials or self.mailtm_api_key or self.email_forwarder_url)
    
    def create_inbox(self, provider: str = "mailtm") -> Dict[str, Optional[str]]:
        """Create a temporary email inbox."""
        if not self.is_live:
            # Return mock email for dry-run
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            return {
                "address": f"{username}@mockmail.example.com",
                "inbox_id": f"mock_{random.randint(10000, 99999)}",
                "receive_url": f"https://mockmail.example.com/api/inbox/{username}"
            }
        
        if provider == "mailtm":
            return self._create_mailtm_inbox()
        elif provider == "gmail":
            return self._create_gmail_inbox()
        elif provider == "forwarder":
            return self._create_forwarder_inbox()
        else:
            logger.error(f"Unknown email provider: {provider}")
            return {"address": None, "inbox_id": None, "receive_url": None}
    
    def _create_mailtm_inbox(self) -> Dict[str, Optional[str]]:
        """Create Mail.tm inbox."""
        try:
            # Mock implementation - would use Mail.tm API
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            logger.info(f"Creating Mail.tm inbox for {username}")
            
            return {
                "address": f"{username}@10minutemail.com",
                "inbox_id": f"mailtm_{random.randint(10000, 99999)}",
                "receive_url": f"https://api.mail.tm/accounts/{username}/messages"
            }
        except Exception as e:
            logger.error(f"Failed to create Mail.tm inbox: {e}")
            return {"address": None, "inbox_id": None, "receive_url": None}
    
    def _create_gmail_inbox(self) -> Dict[str, Optional[str]]:
        """Create Gmail inbox using credentials."""
        try:
            # Mock implementation - would use Gmail API
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            logger.info(f"Creating Gmail inbox for {username}")
            
            return {
                "address": f"{username}@gmail.com",
                "inbox_id": f"gmail_{random.randint(10000, 99999)}",
                "receive_url": None  # Gmail uses different API
            }
        except Exception as e:
            logger.error(f"Failed to create Gmail inbox: {e}")
            return {"address": None, "inbox_id": None, "receive_url": None}
    
    def _create_forwarder_inbox(self) -> Dict[str, Optional[str]]:
        """Create email forwarder inbox."""
        try:
            # Mock implementation - would use custom forwarder service
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            logger.info(f"Creating forwarder inbox for {username}")
            
            return {
                "address": f"{username}@tempmail.example.com",
                "inbox_id": f"forwarder_{random.randint(10000, 99999)}",
                "receive_url": f"{self.email_forwarder_url}/api/inbox/{username}"
            }
        except Exception as e:
            logger.error(f"Failed to create forwarder inbox: {e}")
            return {"address": None, "inbox_id": None, "receive_url": None}


# Global instance
email_provider = EmailProvider()