"""SMS provider for phone number verification."""

import os
import random
from typing import Dict, Optional
from loguru import logger


class SMSProvider:
    """SMS provider for managing phone number rentals and verification."""
    
    def __init__(self):
        # Check for various SMS provider configurations
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.fivesim_api_key = os.getenv("FIVESIM_API_KEY")
        self.sms_activate_api_key = os.getenv("SMS_ACTIVATE_API_KEY")
        
        self.is_live = bool(self.twilio_account_sid or self.fivesim_api_key or self.sms_activate_api_key)
    
    def rent_number(self, provider: str = "5sim", country: str = "US") -> Dict[str, Optional[str]]:
        """Rent a phone number for verification."""
        if not self.is_live:
            # Return mock number for dry-run
            phone = f"+1555{random.randint(1000000, 9999999)}"
            return {
                "phone": phone,
                "rental_id": f"mock_{random.randint(10000, 99999)}",
                "provider": provider
            }
        
        if provider == "twilio":
            return self._rent_twilio_number(country)
        elif provider == "5sim":
            return self._rent_5sim_number(country)
        elif provider == "sms-activate":
            return self._rent_sms_activate_number(country)
        else:
            logger.error(f"Unknown SMS provider: {provider}")
            return {"phone": None, "rental_id": None, "provider": provider}
    
    def submit_code(self, rental_id: str, code: str) -> bool:
        """Submit verification code for a rented number."""
        if not self.is_live:
            logger.info(f"Mock SMS verification: {rental_id} with code {code}")
            return True
        
        try:
            # Mock implementation - would submit to appropriate provider
            logger.info(f"Submitting verification code for rental {rental_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to submit verification code: {e}")
            return False
    
    def _rent_twilio_number(self, country: str) -> Dict[str, Optional[str]]:
        """Rent number using Twilio."""
        try:
            # Mock implementation - would use Twilio API
            phone = f"+1555{random.randint(1000000, 9999999)}"
            logger.info(f"Renting Twilio number: {phone}")
            
            return {
                "phone": phone,
                "rental_id": f"twilio_{random.randint(10000, 99999)}",
                "provider": "twilio"
            }
        except Exception as e:
            logger.error(f"Failed to rent Twilio number: {e}")
            return {"phone": None, "rental_id": None, "provider": "twilio"}
    
    def _rent_5sim_number(self, country: str) -> Dict[str, Optional[str]]:
        """Rent number using 5sim."""
        try:
            # Mock implementation - would use 5sim API
            phone = f"+1555{random.randint(1000000, 9999999)}"
            logger.info(f"Renting 5sim number: {phone}")
            
            return {
                "phone": phone,
                "rental_id": f"5sim_{random.randint(10000, 99999)}",
                "provider": "5sim"
            }
        except Exception as e:
            logger.error(f"Failed to rent 5sim number: {e}")
            return {"phone": None, "rental_id": None, "provider": "5sim"}
    
    def _rent_sms_activate_number(self, country: str) -> Dict[str, Optional[str]]:
        """Rent number using SMS-Activate."""
        try:
            # Mock implementation - would use SMS-Activate API
            phone = f"+1555{random.randint(1000000, 9999999)}"
            logger.info(f"Renting SMS-Activate number: {phone}")
            
            return {
                "phone": phone,
                "rental_id": f"smsactivate_{random.randint(10000, 99999)}",
                "provider": "sms-activate"
            }
        except Exception as e:
            logger.error(f"Failed to rent SMS-Activate number: {e}")
            return {"phone": None, "rental_id": None, "provider": "sms-activate"}


# Global instance
sms_provider = SMSProvider()