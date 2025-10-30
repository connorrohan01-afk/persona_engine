"""Captcha solving providers with support for 2Captcha, CapMonster, AntiCaptcha, and mock."""

import asyncio
import time
from typing import Optional, Dict, Any
import httpx
from loguru import logger

from app.config import settings


class CaptchaProvider:
    """Base class for captcha providers."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.max_retries = 5
        self.polling_interval = 5  # seconds
        
    async def solve_captcha(self, site_key: str, url: str, dry: bool = False) -> Dict[str, Any]:
        """Solve a captcha and return the solution."""
        raise NotImplementedError


class MockCaptchaProvider(CaptchaProvider):
    """Mock captcha provider for testing and fallback."""
    
    async def solve_captcha(self, site_key: str, url: str, dry: bool = False) -> Dict[str, Any]:
        """Return a mock solution immediately."""
        logger.info(f"Mock captcha solve for site_key={site_key}, url={url}, dry={dry}")
        await asyncio.sleep(0.1)  # Simulate small delay
        return {
            "success": True,
            "solution": "MOCK-SOLUTION-123",
            "provider": "mock",
            "elapsed_seconds": 0.1
        }


class TwoCaptchaProvider(CaptchaProvider):
    """2Captcha provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "http://2captcha.com"
        
    async def solve_captcha(self, site_key: str, url: str, dry: bool = False) -> Dict[str, Any]:
        """Solve captcha using 2Captcha service."""
        if dry or not self.api_key:
            logger.info("2Captcha dry mode or no API key - returning mock solution")
            return await MockCaptchaProvider().solve_captcha(site_key, url, dry=True)
            
        start_time = time.time()
        
        try:
            # Submit captcha
            submit_data = {
                "key": self.api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": url,
                "json": 1
            }
            
            async with httpx.AsyncClient() as client:
                logger.info(f"Submitting captcha to 2Captcha for site_key={site_key}")
                response = await client.post(f"{self.base_url}/in.php", data=submit_data)
                response.raise_for_status()
                
                result = response.json()
                if result.get("status") != 1:
                    raise Exception(f"2Captcha submission failed: {result}")
                
                captcha_id = result["request"]
                logger.info(f"2Captcha captcha_id={captcha_id}, polling for solution...")
                
                # Poll for solution
                for attempt in range(self.max_retries):
                    await asyncio.sleep(self.polling_interval)
                    
                    get_params = {
                        "key": self.api_key,
                        "action": "get",
                        "id": captcha_id,
                        "json": 1
                    }
                    
                    response = await client.get(f"{self.base_url}/res.php", params=get_params)
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    if result.get("status") == 1:
                        elapsed = time.time() - start_time
                        logger.info(f"2Captcha solved in {elapsed:.1f}s")
                        return {
                            "success": True,
                            "solution": result["request"],
                            "provider": "2captcha",
                            "elapsed_seconds": elapsed
                        }
                    elif result.get("request") == "CAPCHA_NOT_READY":
                        continue
                    else:
                        raise Exception(f"2Captcha error: {result}")
                
                raise Exception("2Captcha solving timed out after max retries")
                
        except Exception as e:
            logger.error(f"2Captcha error: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": "2captcha",
                "elapsed_seconds": time.time() - start_time
            }


class CapMonsterProvider(CaptchaProvider):
    """CapMonster (CapSolver) provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "https://api.capsolver.com"
        
    async def solve_captcha(self, site_key: str, url: str, dry: bool = False) -> Dict[str, Any]:
        """Solve captcha using CapSolver service."""
        if dry or not self.api_key:
            logger.info("CapSolver dry mode or no API key - returning mock solution")
            return await MockCaptchaProvider().solve_captcha(site_key, url, dry=True)
            
        start_time = time.time()
        
        try:
            # Submit captcha
            submit_data = {
                "clientKey": self.api_key,
                "task": {
                    "type": "ReCaptchaV2TaskProxyless",
                    "websiteURL": url,
                    "websiteKey": site_key
                }
            }
            
            async with httpx.AsyncClient() as client:
                logger.info(f"Submitting captcha to CapSolver for site_key={site_key}")
                response = await client.post(f"{self.base_url}/createTask", json=submit_data)
                response.raise_for_status()
                
                result = response.json()
                if result.get("errorId") != 0:
                    raise Exception(f"CapSolver submission failed: {result}")
                
                task_id = result["taskId"]
                logger.info(f"CapSolver task_id={task_id}, polling for solution...")
                
                # Poll for solution
                for attempt in range(self.max_retries):
                    await asyncio.sleep(self.polling_interval)
                    
                    get_data = {
                        "clientKey": self.api_key,
                        "taskId": task_id
                    }
                    
                    response = await client.post(f"{self.base_url}/getTaskResult", json=get_data)
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    if result.get("status") == "ready":
                        elapsed = time.time() - start_time
                        logger.info(f"CapSolver solved in {elapsed:.1f}s")
                        return {
                            "success": True,
                            "solution": result["solution"]["gRecaptchaResponse"],
                            "provider": "capsolver",
                            "elapsed_seconds": elapsed
                        }
                    elif result.get("status") == "processing":
                        continue
                    else:
                        raise Exception(f"CapSolver error: {result}")
                
                raise Exception("CapSolver solving timed out after max retries")
                
        except Exception as e:
            logger.error(f"CapSolver error: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": "capsolver",
                "elapsed_seconds": time.time() - start_time
            }


class AntiCaptchaProvider(CaptchaProvider):
    """AntiCaptcha provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "https://api.anti-captcha.com"
        
    async def solve_captcha(self, site_key: str, url: str, dry: bool = False) -> Dict[str, Any]:
        """Solve captcha using AntiCaptcha service."""
        if dry or not self.api_key:
            logger.info("AntiCaptcha dry mode or no API key - returning mock solution")
            return await MockCaptchaProvider().solve_captcha(site_key, url, dry=True)
            
        start_time = time.time()
        
        try:
            # Submit captcha
            submit_data = {
                "clientKey": self.api_key,
                "task": {
                    "type": "NoCaptchaTaskProxyless",
                    "websiteURL": url,
                    "websiteKey": site_key
                }
            }
            
            async with httpx.AsyncClient() as client:
                logger.info(f"Submitting captcha to AntiCaptcha for site_key={site_key}")
                response = await client.post(f"{self.base_url}/createTask", json=submit_data)
                response.raise_for_status()
                
                result = response.json()
                if result.get("errorId") != 0:
                    raise Exception(f"AntiCaptcha submission failed: {result}")
                
                task_id = result["taskId"]
                logger.info(f"AntiCaptcha task_id={task_id}, polling for solution...")
                
                # Poll for solution
                for attempt in range(self.max_retries):
                    await asyncio.sleep(self.polling_interval)
                    
                    get_data = {
                        "clientKey": self.api_key,
                        "taskId": task_id
                    }
                    
                    response = await client.post(f"{self.base_url}/getTaskResult", json=get_data)
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    if result.get("status") == "ready":
                        elapsed = time.time() - start_time
                        logger.info(f"AntiCaptcha solved in {elapsed:.1f}s")
                        return {
                            "success": True,
                            "solution": result["solution"]["gRecaptchaResponse"],
                            "provider": "anticaptcha",
                            "elapsed_seconds": elapsed
                        }
                    elif result.get("status") == "processing":
                        continue
                    else:
                        raise Exception(f"AntiCaptcha error: {result}")
                
                raise Exception("AntiCaptcha solving timed out after max retries")
                
        except Exception as e:
            logger.error(f"AntiCaptcha error: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": "anticaptcha",
                "elapsed_seconds": time.time() - start_time
            }


def get_captcha_provider(provider_name: Optional[str] = None) -> CaptchaProvider:
    """Factory function to get the appropriate captcha provider."""
    provider_name = provider_name or settings.captcha_provider
    
    if provider_name == "2captcha":
        api_key = settings.captcha_key or settings.twocaptcha_api_key
        return TwoCaptchaProvider(api_key)
    elif provider_name in ["capmonster", "capsolver"]:
        api_key = settings.captcha_key or settings.capsolver_api_key
        return CapMonsterProvider(api_key)
    elif provider_name == "anticaptcha":
        api_key = settings.captcha_key or settings.anticaptcha_api_key
        return AntiCaptchaProvider(api_key)
    else:
        # Default to mock for unknown providers or when provider is "mock"
        return MockCaptchaProvider()


async def solve_captcha(site_key: str, url: str, provider: Optional[str] = None, dry: bool = False) -> Dict[str, Any]:
    """Convenience function to solve a captcha using the configured provider."""
    captcha_provider = get_captcha_provider(provider)
    return await captcha_provider.solve_captcha(site_key, url, dry)