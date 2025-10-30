"""Reddit provider with PRAW-like wrapper and mock fallback."""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import httpx
from loguru import logger
import json
import base64

from app.config import settings
from app.reddit_utils import (
    rate_limiter, exponential_backoff, validate_subreddit_name,
    validate_post_title, validate_post_body, validate_url,
    clean_subreddit_name, format_reddit_url, generate_mock_reddit_id,
    generate_mock_fullname, should_retry_error
)


class RedditProvider:
    """Base Reddit provider interface."""
    
    def __init__(self):
        self.user_agent = settings.reddit_user_agent
        self.timeout = settings.reddit_timeout_s
        self.max_retries = settings.reddit_max_retries
    
    async def submit_post(
        self,
        subreddit: str,
        kind: str,
        title: str,
        body: Optional[str] = None,
        url: Optional[str] = None,
        nsfw: bool = False,
        spoiler: bool = False,
        flair_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a post to Reddit."""
        raise NotImplementedError
    
    async def get_posts(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 25,
        time_filter: str = "day"
    ) -> List[Dict[str, Any]]:
        """Get posts from a subreddit."""
        raise NotImplementedError
    
    async def get_user_info(self, username: str) -> Dict[str, Any]:
        """Get user information."""
        raise NotImplementedError


class MockRedditProvider(RedditProvider):
    """Mock Reddit provider for testing and fallback."""
    
    async def submit_post(
        self,
        subreddit: str,
        kind: str,
        title: str,
        body: Optional[str] = None,
        url: Optional[str] = None,
        nsfw: bool = False,
        spoiler: bool = False,
        flair_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock submit post implementation."""
        # Validate inputs
        if not validate_subreddit_name(subreddit):
            raise ValueError(f"Invalid subreddit name: {subreddit}")
        
        valid_title, title_error = validate_post_title(title)
        if not valid_title:
            raise ValueError(f"Invalid title: {title_error}")
        
        if kind == "text":
            valid_body, body_error = validate_post_body(body)
            if not valid_body:
                raise ValueError(f"Invalid body: {body_error}")
        elif kind == "link":
            if not url:
                raise ValueError("URL required for link posts")
            valid_url, url_error = validate_url(url)
            if not valid_url:
                raise ValueError(f"Invalid URL: {url_error}")
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        reddit_id = generate_mock_reddit_id()
        fullname = generate_mock_fullname("t3")
        permalink = f"/r/{clean_subreddit_name(subreddit)}/comments/{reddit_id}/"
        
        logger.info(f"Mock Reddit post: {kind} post to r/{subreddit} - {title}")
        
        return {
            "success": True,
            "id": reddit_id,
            "fullname": fullname,
            "permalink": permalink,
            "url": format_reddit_url(permalink),
            "title": title,
            "subreddit": clean_subreddit_name(subreddit),
            "created_utc": time.time(),
            "score": 1,
            "num_comments": 0
        }
    
    async def get_posts(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 25,
        time_filter: str = "day"
    ) -> List[Dict[str, Any]]:
        """Mock get posts implementation."""
        if not validate_subreddit_name(subreddit):
            raise ValueError(f"Invalid subreddit name: {subreddit}")
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        posts = []
        for i in range(min(limit, 5)):  # Return max 5 mock posts
            reddit_id = generate_mock_reddit_id()
            fullname = generate_mock_fullname("t3")
            permalink = f"/r/{clean_subreddit_name(subreddit)}/comments/{reddit_id}/"
            
            posts.append({
                "id": reddit_id,
                "fullname": fullname,
                "title": f"Mock post {i + 1} from r/{subreddit}",
                "author": "mock_user",
                "subreddit": clean_subreddit_name(subreddit),
                "permalink": permalink,
                "url": format_reddit_url(permalink),
                "created_utc": time.time() - (i * 3600),  # Posts from different hours
                "score": 10 + i,
                "num_comments": i * 2,
                "upvote_ratio": 0.85 + (i * 0.01),
                "over_18": False,
                "spoiler": False,
                "selftext": f"This is mock content for post {i + 1}",
                "post_hint": "text" if i % 2 == 0 else "link"
            })
        
        logger.info(f"Mock Reddit scrape: {len(posts)} posts from r/{subreddit}")
        return posts
    
    async def get_user_info(self, username: str) -> Dict[str, Any]:
        """Mock get user info implementation."""
        await asyncio.sleep(0.1)
        
        return {
            "name": username,
            "id": f"mock_{username}",
            "created_utc": time.time() - 86400 * 30,  # 30 days ago
            "link_karma": 100,
            "comment_karma": 250,
            "is_gold": False,
            "is_mod": False,
            "verified": True,
            "has_verified_email": True
        }


class LiveRedditProvider(RedditProvider):
    """Live Reddit provider using OAuth and Reddit API."""
    
    def __init__(self):
        super().__init__()
        self.client_id = settings.reddit_client_id
        self.client_secret = settings.reddit_client_secret
        self.username = settings.reddit_username
        self.password = settings.reddit_password
        self.redirect_uri = settings.reddit_redirect_uri
        
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        self.base_url = "https://oauth.reddit.com"
        self.auth_url = "https://www.reddit.com/api/v1"
    
    async def _get_access_token(self) -> str:
        """Get or refresh OAuth access token."""
        if self.access_token and self.token_expires_at:
            if time.time() < self.token_expires_at - 60:  # Refresh 1 min early
                return self.access_token
        
        # Get new token using password flow
        auth_data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password
        }
        
        # Basic auth header
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {auth_bytes}",
            "User-Agent": self.user_agent
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.auth_url}/access_token",
                data=auth_data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.token_expires_at = time.time() + token_data["expires_in"]
            
            logger.info("Reddit OAuth token refreshed")
            return self.access_token
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to Reddit API."""
        for attempt in range(self.max_retries + 1):
            try:
                # Check rate limits
                if not rate_limiter.can_make_request():
                    wait_time = rate_limiter.get_reset_time() - time.time()
                    if wait_time > 0:
                        logger.warning(f"Rate limited, waiting {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)
                
                # Get access token
                token = await self._get_access_token()
                
                headers = {
                    "Authorization": f"Bearer {token}",
                    "User-Agent": self.user_agent
                }
                
                async with httpx.AsyncClient() as client:
                    if method.upper() == "GET":
                        response = await client.get(
                            f"{self.base_url}{endpoint}",
                            params=params,
                            headers=headers,
                            timeout=self.timeout
                        )
                    else:
                        response = await client.post(
                            f"{self.base_url}{endpoint}",
                            data=data,
                            headers=headers,
                            timeout=self.timeout
                        )
                    
                    rate_limiter.record_request()
                    
                    if response.status_code == 429:  # Rate limited
                        retry_after = int(response.headers.get("retry-after", 60))
                        logger.warning(f"Rate limited, retry after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    response.raise_for_status()
                    return response.json()
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Reddit API error (attempt {attempt + 1}): {error_msg}")
                
                if attempt < self.max_retries and should_retry_error(error_msg):
                    await exponential_backoff(attempt + 1)
                    continue
                else:
                    raise
        
        raise Exception("Max retries exceeded")
    
    async def submit_post(
        self,
        subreddit: str,
        kind: str,
        title: str,
        body: Optional[str] = None,
        url: Optional[str] = None,
        nsfw: bool = False,
        spoiler: bool = False,
        flair_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a post to Reddit via API."""
        # Validate inputs
        if not validate_subreddit_name(subreddit):
            raise ValueError(f"Invalid subreddit name: {subreddit}")
        
        valid_title, title_error = validate_post_title(title)
        if not valid_title:
            raise ValueError(f"Invalid title: {title_error}")
        
        data = {
            "kind": kind,
            "sr": clean_subreddit_name(subreddit),
            "title": title,
            "nsfw": nsfw,
            "spoiler": spoiler,
            "api_type": "json"
        }
        
        if kind == "self" or kind == "text":
            if body:
                valid_body, body_error = validate_post_body(body)
                if not valid_body:
                    raise ValueError(f"Invalid body: {body_error}")
                data["text"] = body
        elif kind == "link":
            if not url:
                raise ValueError("URL required for link posts")
            valid_url, url_error = validate_url(url)
            if not valid_url:
                raise ValueError(f"Invalid URL: {url_error}")
            data["url"] = url
        
        if flair_id:
            data["flair_id"] = flair_id
        
        result = await self._make_request("POST", "/api/submit", data=data)
        
        if result.get("json", {}).get("errors"):
            errors = result["json"]["errors"]
            raise Exception(f"Reddit API errors: {errors}")
        
        post_data = result.get("json", {}).get("data", {})
        return {
            "success": True,
            "id": post_data.get("id"),
            "fullname": post_data.get("name"),
            "permalink": post_data.get("permalink"),
            "url": format_reddit_url(post_data.get("permalink", "")),
            "title": title,
            "subreddit": clean_subreddit_name(subreddit)
        }
    
    async def get_posts(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 25,
        time_filter: str = "day"
    ) -> List[Dict[str, Any]]:
        """Get posts from subreddit via API."""
        if not validate_subreddit_name(subreddit):
            raise ValueError(f"Invalid subreddit name: {subreddit}")
        
        params: Dict[str, Union[str, int]] = {
            "limit": min(limit, 100),  # Reddit API limit
            "raw_json": 1
        }
        
        if sort == "top":
            params["t"] = time_filter
        
        endpoint = f"/r/{clean_subreddit_name(subreddit)}/{sort}"
        result = await self._make_request("GET", endpoint, params=params)
        
        posts = []
        for child in result.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            posts.append({
                "id": post_data.get("id"),
                "fullname": post_data.get("name"),
                "title": post_data.get("title"),
                "author": post_data.get("author"),
                "subreddit": post_data.get("subreddit"),
                "permalink": post_data.get("permalink"),
                "url": format_reddit_url(post_data.get("permalink", "")),
                "created_utc": post_data.get("created_utc"),
                "score": post_data.get("score", 0),
                "num_comments": post_data.get("num_comments", 0),
                "upvote_ratio": post_data.get("upvote_ratio"),
                "over_18": post_data.get("over_18", False),
                "spoiler": post_data.get("spoiler", False),
                "selftext": post_data.get("selftext", ""),
                "post_hint": post_data.get("post_hint")
            })
        
        return posts
    
    async def get_user_info(self, username: str) -> Dict[str, Any]:
        """Get user info via API."""
        endpoint = f"/user/{username}/about"
        result = await self._make_request("GET", endpoint)
        
        user_data = result.get("data", {})
        return {
            "name": user_data.get("name"),
            "id": user_data.get("id"),
            "created_utc": user_data.get("created_utc"),
            "link_karma": user_data.get("link_karma", 0),
            "comment_karma": user_data.get("comment_karma", 0),
            "is_gold": user_data.get("is_gold", False),
            "is_mod": user_data.get("is_mod", False),
            "verified": user_data.get("verified", False),
            "has_verified_email": user_data.get("has_verified_email", False)
        }


def get_reddit_provider() -> RedditProvider:
    """Factory function to get appropriate Reddit provider."""
    # Check if required credentials are available
    required_fields = [
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_username,
        settings.reddit_password
    ]
    
    if all(field for field in required_fields):
        logger.info("Using live Reddit provider")
        return LiveRedditProvider()
    else:
        logger.info("Using mock Reddit provider (missing credentials)")
        return MockRedditProvider()


# Global provider instance
reddit_provider = get_reddit_provider()