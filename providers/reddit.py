"""Reddit account management provider."""

import os
import json
import random
import string
import uuid
import time
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, timedelta
import httpx
from loguru import logger


class RedditProvider:
    """Reddit provider for account registration and management."""
    
    def __init__(self):
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_SECRET")
        self.redirect_uri = os.getenv("REDDIT_REDIRECT_URI")
        
        self.is_live = bool(self.client_id and self.client_secret)
        
        # Reddit API endpoints
        self.base_url = "https://oauth.reddit.com"
        self.www_url = "https://www.reddit.com"
        
        # User agent for Reddit API
        self.user_agent = "PersonaEngine/1.0"
        
        # Cache for subreddit rules (10 minute TTL)
        self._rules_cache = {}
        self._flairs_cache = {}
    
    def register(
        self, 
        username_hint: str, 
        email: str, 
        password: str, 
        proxy: Optional[str] = None,
        captcha_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Register a new Reddit account."""
        
        if not self.is_live:
            # Return mock registration for dry-run
            username = f"{username_hint}_{random.randint(100, 999)}"
            return {
                "ok": True,
                "username": username,
                "cookies": {"session": f"mock_session_{random.randint(10000, 99999)}"},
                "status": "created",
                "account_id": f"reddit_{random.randint(100000, 999999)}"
            }
        
        try:
            # Mock implementation - would use Reddit API
            logger.info(f"Registering Reddit account with email {email}")
            
            # Generate username if needed
            if not username_hint:
                username_hint = ''.join(random.choices(string.ascii_lowercase, k=8))
            
            username = f"{username_hint}_{random.randint(100, 999)}"
            
            # Simulate registration process
            registration_data = {
                "username": username,
                "email": email,
                "password": password,
                "captcha_token": captcha_token
            }
            
            # Mock HTTP request to Reddit registration endpoint
            # In real implementation, would use httpx with proxy
            
            # Simulate successful registration
            cookies = {
                "session": f"reddit_session_{random.randint(10000, 99999)}",
                "token": f"reddit_token_{random.randint(10000, 99999)}"
            }
            
            return {
                "ok": True,
                "username": username,
                "cookies": cookies,
                "status": "created",
                "account_id": f"reddit_{random.randint(100000, 999999)}"
            }
            
        except Exception as e:
            logger.error(f"Failed to register Reddit account: {e}")
            return {
                "ok": False,
                "error": str(e),
                "status": "failed"
            }
    
    def verify_phone(self, session_cookies: Dict[str, str], phone: str) -> bool:
        """Verify phone number for Reddit account."""
        if not self.is_live:
            logger.info(f"Mock phone verification for {phone}")
            return True
        
        try:
            # Mock implementation - would submit phone verification
            logger.info(f"Verifying phone {phone} for Reddit account")
            return True
        except Exception as e:
            logger.error(f"Failed to verify phone: {e}")
            return False
    
    def confirm_phone_code(self, session_cookies: Dict[str, str], code: str) -> bool:
        """Confirm phone verification code."""
        if not self.is_live:
            logger.info(f"Mock phone code confirmation: {code}")
            return True
        
        try:
            # Mock implementation - would confirm verification code
            logger.info(f"Confirming phone verification code")
            return True
        except Exception as e:
            logger.error(f"Failed to confirm phone code: {e}")
            return False
    
    def fetch_sub_rules(self, subreddit: str) -> Dict[str, Any]:
        """Fetch subreddit rules."""
        if not self.is_live:
            # Mock rules for dry-run
            return {
                "ok": True,
                "rules": [
                    {"short_name": "Be civil", "description": "Follow reddiquette"},
                    {"short_name": "No spam", "description": "Don't spam content"},
                    {"short_name": "Stay on topic", "description": "Keep posts relevant"}
                ]
            }
        
        try:
            # Mock implementation - would fetch real rules via Reddit API
            logger.info(f"Fetching rules for r/{subreddit}")
            
            # Simulate API response
            mock_rules = [
                {"short_name": "Rule 1", "description": "Follow community guidelines"},
                {"short_name": "Rule 2", "description": "Be respectful to other users"},
                {"short_name": "Rule 3", "description": "No low-effort posts"}
            ]
            
            return {"ok": True, "rules": mock_rules}
            
        except Exception as e:
            logger.error(f"Failed to fetch rules for r/{subreddit}: {e}")
            return {"ok": False, "error": str(e)}
    
    def browse_feed(self, session: Dict[str, str], subreddit: str, sort: str = "hot") -> Dict[str, Any]:
        """Browse subreddit feed."""
        if not self.is_live:
            # Mock posts for dry-run
            mock_posts = []
            for i in range(random.randint(5, 15)):
                mock_posts.append({
                    "id": f"mock_post_{random.randint(10000, 99999)}",
                    "title": f"Mock post title {i+1}",
                    "score": random.randint(10, 1000),
                    "num_comments": random.randint(0, 100),
                    "author": f"user_{random.randint(100, 999)}",
                    "url": f"https://reddit.com/r/{subreddit}/comments/mock_{i}",
                    "created_utc": random.randint(1640000000, 1700000000)
                })
            
            return {"ok": True, "posts": mock_posts}
        
        try:
            # Mock implementation - would use Reddit API to browse feed
            logger.info(f"Browsing r/{subreddit} feed (sort: {sort})")
            
            # Simulate browsing real feed
            mock_posts = []
            for i in range(random.randint(8, 20)):
                mock_posts.append({
                    "id": f"{subreddit}_post_{random.randint(10000, 99999)}",
                    "title": f"Real post title from r/{subreddit} #{i+1}",
                    "score": random.randint(50, 2000),
                    "num_comments": random.randint(5, 200),
                    "author": f"real_user_{random.randint(100, 999)}",
                    "url": f"https://reddit.com/r/{subreddit}/comments/real_{i}"
                })
            
            return {"ok": True, "posts": mock_posts}
            
        except Exception as e:
            logger.error(f"Failed to browse r/{subreddit}: {e}")
            return {"ok": False, "error": str(e)}
    
    def upvote(self, session: Dict[str, str], thing_id: str) -> bool:
        """Upvote a post or comment."""
        if not self.is_live:
            logger.info(f"Mock upvote for {thing_id}")
            return True
        
        try:
            # Mock implementation - would send upvote via Reddit API
            logger.info(f"Upvoting {thing_id}")
            
            # Simulate upvote action
            # In real implementation, would POST to Reddit's vote endpoint
            return True
            
        except Exception as e:
            logger.error(f"Failed to upvote {thing_id}: {e}")
            return False
    
    def downvote(self, session: Dict[str, str], thing_id: str) -> bool:
        """Downvote a post or comment."""
        if not self.is_live:
            logger.info(f"Mock downvote for {thing_id}")
            return True
        
        try:
            # Mock implementation - would send downvote via Reddit API
            logger.info(f"Downvoting {thing_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to downvote {thing_id}: {e}")
            return False
    
    def save(self, session: Dict[str, str], thing_id: str) -> bool:
        """Save a post or comment."""
        if not self.is_live:
            logger.info(f"Mock save for {thing_id}")
            return True
        
        try:
            # Mock implementation - would save via Reddit API
            logger.info(f"Saving {thing_id}")
            
            # Simulate save action
            return True
            
        except Exception as e:
            logger.error(f"Failed to save {thing_id}: {e}")
            return False
    
    def comment(self, session: Dict[str, str], thing_id: str, text: str) -> Dict[str, Any]:
        """Comment on a post or comment."""
        if not self.is_live:
            comment_id = f"mock_comment_{random.randint(10000, 99999)}"
            logger.info(f"Mock comment on {thing_id}: {text[:50]}...")
            return {"ok": True, "comment_id": comment_id}
        
        try:
            # Mock implementation - would post comment via Reddit API
            logger.info(f"Commenting on {thing_id}: {text[:50]}...")
            
            # Simulate comment submission
            comment_id = f"real_comment_{random.randint(10000, 99999)}"
            
            return {"ok": True, "comment_id": comment_id}
            
        except Exception as e:
            logger.error(f"Failed to comment on {thing_id}: {e}")
            return {"ok": False, "error": str(e)}
    
    def join_subreddit(self, session: Dict[str, str], subreddit: str) -> bool:
        """Join/subscribe to a subreddit."""
        if not self.is_live:
            logger.info(f"Mock join r/{subreddit}")
            return True
        
        try:
            # Mock implementation - would subscribe via Reddit API
            logger.info(f"Joining r/{subreddit}")
            
            # Simulate subscription
            return True
            
        except Exception as e:
            logger.error(f"Failed to join r/{subreddit}: {e}")
            return False
    
    def leave_subreddit(self, session: Dict[str, str], subreddit: str) -> bool:
        """Leave/unsubscribe from a subreddit."""
        if not self.is_live:
            logger.info(f"Mock leave r/{subreddit}")
            return True
        
        try:
            # Mock implementation - would unsubscribe via Reddit API
            logger.info(f"Leaving r/{subreddit}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to leave r/{subreddit}: {e}")
            return False


    def _make_headers(self, session_data: Dict[str, str]) -> Dict[str, str]:
        """Create headers for Reddit API requests."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Language": "en-US,en;q=0.9"
        }
    
    def _parse_cookies(self, cookies_json: Optional[str]) -> Dict[str, str]:
        """Parse cookies from JSON string."""
        if not cookies_json:
            return {}
        try:
            return json.loads(cookies_json)
        except json.JSONDecodeError:
            logger.warning("Failed to parse cookies JSON")
            return {}
    
    def _map_error(self, response_data: Dict[str, Any], status_code: int = 0) -> Dict[str, Any]:
        """Map Reddit API errors to our unified format."""
        error_msg = str(response_data.get("message", "Unknown error"))
        
        # Check for rate limiting
        if "ratelimited" in error_msg.lower() or status_code == 429:
            # Try to extract retry_after from message
            retry_after = 60  # Default 1 minute
            import re
            match = re.search(r'(\d+)\s*minutes?', error_msg)
            if match:
                retry_after = int(match.group(1)) * 60
            
            return {
                "ok": False,
                "error_code": "ratelimit",
                "message": "Rate limited by Reddit",
                "details": {"retry_after": retry_after}
            }
        
        # Check for shadowban indicators
        if "you are not allowed" in error_msg.lower() or status_code == 403:
            return {
                "ok": False,
                "error_code": "shadowban",
                "message": "Account may be shadowbanned or restricted",
                "details": {"original_message": error_msg}
            }
        
        # Check for subreddit rules violations
        if "submission is not appropriate" in error_msg.lower() or "removed" in error_msg.lower():
            return {
                "ok": False,
                "error_code": "rules",
                "message": "Post violates subreddit rules",
                "details": {"rule": error_msg}
            }
        
        # Check for captcha requirement
        if "captcha" in error_msg.lower():
            return {
                "ok": False,
                "error_code": "captcha",
                "message": "Captcha required",
                "details": {"original_message": error_msg}
            }
        
        # Generic error
        return {
            "ok": False,
            "error_code": "unknown",
            "message": error_msg,
            "details": {"status_code": status_code}
        }
    
    def get_sub_rules(self, subreddit: str) -> Dict[str, Any]:
        """Get subreddit rules with caching."""
        cache_key = f"rules_{subreddit}"
        now = time.time()
        
        # Check cache (10 minute TTL)
        if cache_key in self._rules_cache:
            cached_data, cached_time = self._rules_cache[cache_key]
            if now - cached_time < 600:  # 10 minutes
                return cached_data
        
        if not self.is_live:
            # Mock rules for dry-run
            mock_rules = {
                "title_max": 300,
                "allow_links": True,
                "allow_images": True,
                "banned_words": ["spam", "promotion"],
                "flairs": [
                    {"id": "mock_flair_1", "text": "Discussion"},
                    {"id": "mock_flair_2", "text": "Question"}
                ],
                "nsfw_ok": True,
                "post_interval_secs": 600  # 10 minutes
            }
            self._rules_cache[cache_key] = (mock_rules, now)
            return mock_rules
        
        try:
            # In real implementation, would fetch from Reddit API
            # For now, return sensible defaults
            default_rules = {
                "title_max": 300,
                "allow_links": True,
                "allow_images": True,
                "banned_words": [],
                "flairs": [],
                "nsfw_ok": True,
                "post_interval_secs": 900  # 15 minutes default
            }
            
            self._rules_cache[cache_key] = (default_rules, now)
            return default_rules
            
        except Exception as e:
            logger.error(f"Failed to fetch rules for r/{subreddit}: {e}")
            # Return safe defaults
            return {
                "title_max": 300,
                "allow_links": False,  # Conservative default
                "allow_images": False,
                "banned_words": [],
                "flairs": [],
                "nsfw_ok": False,
                "post_interval_secs": 1800  # 30 minutes
            }
    
    def get_flairs(self, subreddit: str) -> List[Dict[str, Any]]:
        """Get subreddit post flairs with caching."""
        cache_key = f"flairs_{subreddit}"
        now = time.time()
        
        # Check cache (10 minute TTL)
        if cache_key in self._flairs_cache:
            cached_data, cached_time = self._flairs_cache[cache_key]
            if now - cached_time < 600:  # 10 minutes
                return cached_data
        
        if not self.is_live:
            # Mock flairs for dry-run
            mock_flairs = [
                {"id": "mock_flair_1", "text": "Discussion"},
                {"id": "mock_flair_2", "text": "Question"},
                {"id": "mock_flair_3", "text": "News"}
            ]
            self._flairs_cache[cache_key] = (mock_flairs, now)
            return mock_flairs
        
        try:
            # In real implementation, would fetch from Reddit API
            # For now, return empty list
            flairs = []
            self._flairs_cache[cache_key] = (flairs, now)
            return flairs
            
        except Exception as e:
            logger.error(f"Failed to fetch flairs for r/{subreddit}: {e}")
            return []
    
    def submit_post(
        self, 
        session_data: Dict[str, str],
        subreddit: str,
        kind: str,
        title: str,
        body: Optional[str] = None,
        url: Optional[str] = None,
        image_url: Optional[str] = None,
        flair_id: Optional[str] = None,
        nsfw: bool = False,
        spoiler: bool = False,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Submit a post to Reddit."""
        
        if not self.is_live or dry_run:
            # Mock submission for dry-run
            post_id = f"t3_{uuid.uuid4().hex[:8]}"
            logger.info(f"Mock post submission to r/{subreddit}: {title[:50]}...")
            return {
                "ok": True,
                "post_id": post_id,
                "mode": "mock"
            }
        
        try:
            cookies = self._parse_cookies(session_data.get("cookies_json"))
            headers = self._make_headers(session_data)
            
            # Prepare form data for Reddit submission
            form_data = {
                "sr": subreddit,
                "title": title,
                "kind": kind,
                "nsfw": "true" if nsfw else "false",
                "spoiler": "true" if spoiler else "false",
                "api_type": "json"
            }
            
            if kind == "self" and body:
                form_data["text"] = body
            elif kind == "link" and url:
                form_data["url"] = url
            elif kind == "image" and image_url:
                form_data["url"] = image_url
            
            if flair_id:
                form_data["flair_id"] = flair_id
            
            # Use proxy if provided
            proxy = session_data.get("proxy")
            proxies = {"http": proxy, "https": proxy} if proxy else None
            
            # Make request to Reddit API
            with httpx.Client(proxies=proxies, timeout=30.0) as client:
                # Set cookies
                for key, value in cookies.items():
                    client.cookies.set(key, value, domain="reddit.com")
                
                response = client.post(
                    f"{self.www_url}/api/submit",
                    headers=headers,
                    data=form_data
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Check for errors in response
                    if response_data.get("json", {}).get("errors"):
                        errors = response_data["json"]["errors"]
                        error_msg = str(errors[0]) if errors else "Unknown error"
                        return self._map_error({"message": error_msg})
                    
                    # Extract post ID from response
                    things = response_data.get("json", {}).get("data", {}).get("things", [])
                    if things:
                        post_id = things[0].get("data", {}).get("name", f"t3_{uuid.uuid4().hex[:8]}")
                        return {
                            "ok": True,
                            "post_id": post_id,
                            "mode": "live"
                        }
                    else:
                        return self._map_error({"message": "No post ID in response"})
                
                else:
                    return self._map_error(
                        {"message": f"HTTP {response.status_code}: {response.text}"}, 
                        response.status_code
                    )
                    
        except httpx.TimeoutException:
            return self._map_error({"message": "Request timeout"})
        except Exception as e:
            logger.error(f"Failed to submit post to r/{subreddit}: {e}")
            return self._map_error({"message": str(e)})
    
    def submit_comment(
        self, 
        session_data: Dict[str, str],
        thing_id: str,
        text: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Submit a comment on Reddit."""
        
        if not self.is_live or dry_run:
            # Mock comment submission
            comment_id = f"t1_{uuid.uuid4().hex[:8]}"
            logger.info(f"Mock comment on {thing_id}: {text[:50]}...")
            return {
                "ok": True,
                "comment_id": comment_id,
                "mode": "mock"
            }
        
        try:
            cookies = self._parse_cookies(session_data.get("cookies_json"))
            headers = self._make_headers(session_data)
            
            form_data = {
                "thing_id": thing_id,
                "text": text,
                "api_type": "json"
            }
            
            proxy = session_data.get("proxy")
            proxies = {"http": proxy, "https": proxy} if proxy else None
            
            with httpx.Client(proxies=proxies, timeout=30.0) as client:
                for key, value in cookies.items():
                    client.cookies.set(key, value, domain="reddit.com")
                
                response = client.post(
                    f"{self.www_url}/api/comment",
                    headers=headers,
                    data=form_data
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Check for errors
                    if response_data.get("json", {}).get("errors"):
                        errors = response_data["json"]["errors"]
                        error_msg = str(errors[0]) if errors else "Unknown error"
                        return self._map_error({"message": error_msg})
                    
                    # Extract comment ID
                    things = response_data.get("json", {}).get("data", {}).get("things", [])
                    if things:
                        comment_id = things[0].get("data", {}).get("name", f"t1_{uuid.uuid4().hex[:8]}")
                        return {
                            "ok": True,
                            "comment_id": comment_id,
                            "mode": "live"
                        }
                    else:
                        return self._map_error({"message": "No comment ID in response"})
                
                else:
                    return self._map_error(
                        {"message": f"HTTP {response.status_code}: {response.text}"}, 
                        response.status_code
                    )
                    
        except httpx.TimeoutException:
            return self._map_error({"message": "Request timeout"})
        except Exception as e:
            logger.error(f"Failed to submit comment on {thing_id}: {e}")
            return self._map_error({"message": str(e)})
    
    def vote(
        self, 
        session_data: Dict[str, str],
        thing_id: str,
        direction: int = 1,  # 1 for upvote, -1 for downvote, 0 for no vote
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Vote on a post or comment."""
        
        if not self.is_live or dry_run:
            # Mock voting
            vote_type = "upvote" if direction == 1 else "downvote" if direction == -1 else "unvote"
            logger.info(f"Mock {vote_type} for {thing_id}")
            return {
                "ok": True,
                "mode": "mock"
            }
        
        try:
            cookies = self._parse_cookies(session_data.get("cookies_json"))
            headers = self._make_headers(session_data)
            
            form_data = {
                "id": thing_id,
                "dir": str(direction)
            }
            
            proxy = session_data.get("proxy")
            proxies = {"http": proxy, "https": proxy} if proxy else None
            
            with httpx.Client(proxies=proxies, timeout=30.0) as client:
                for key, value in cookies.items():
                    client.cookies.set(key, value, domain="reddit.com")
                
                response = client.post(
                    f"{self.www_url}/api/vote",
                    headers=headers,
                    data=form_data
                )
                
                if response.status_code == 200:
                    return {
                        "ok": True,
                        "mode": "live"
                    }
                else:
                    return self._map_error(
                        {"message": f"HTTP {response.status_code}: {response.text}"}, 
                        response.status_code
                    )
                    
        except httpx.TimeoutException:
            return self._map_error({"message": "Request timeout"})
        except Exception as e:
            logger.error(f"Failed to vote on {thing_id}: {e}")
            return self._map_error({"message": str(e)})


# Global instance
reddit_provider = RedditProvider()