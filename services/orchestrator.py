"""
Lightweight orchestration engine for "build by prompting"
Routes actions to appropriate services with mock fallbacks
"""
import os
import re
import json
import time
import logging
import requests
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from services.image_service import generate_image

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

class OrchestrationEngine:
    def __init__(self):
        self.vault_data = self._load_vault()
        self.qdrant_mock = self._load_qdrant_mock()
    
    def _load_vault(self) -> Dict[str, Any]:
        """Load vault data from file or initialize empty"""
        vault_path = 'data/vault.json'
        if os.path.exists(vault_path):
            try:
                with open(vault_path, 'r') as f:
                    return json.load(f)
            except:
                logging.warning(f"Failed to load {vault_path}, using empty vault")
        return {}
    
    def _save_vault(self):
        """Save vault data to file"""
        vault_path = 'data/vault.json'
        try:
            with open(vault_path, 'w') as f:
                json.dump(self.vault_data, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save vault: {e}")
    
    def _load_qdrant_mock(self) -> Dict[str, List[Dict]]:
        """Load mock Qdrant data from file or initialize empty"""
        qdrant_path = 'data/qdrant_mock.json'
        if os.path.exists(qdrant_path):
            try:
                with open(qdrant_path, 'r') as f:
                    return json.load(f)
            except:
                logging.warning(f"Failed to load {qdrant_path}, using empty collection")
        return {"brain": []}  # Default collection
    
    def _save_qdrant_mock(self):
        """Save mock Qdrant data to file"""
        qdrant_path = 'data/qdrant_mock.json'
        try:
            with open(qdrant_path, 'w') as f:
                json.dump(self.qdrant_mock, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save qdrant mock: {e}")
    
    def _generate_mock_vector(self, size: int = 768) -> List[float]:
        """Generate a deterministic mock vector"""
        import random
        random.seed(42)  # Deterministic for testing
        return [random.uniform(-1, 1) for _ in range(size)]
    
    def dispatch(self, action: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Dispatch action to appropriate handler
        
        Returns: {status: str, output: Any, error?: str, details?: str}
        """
        if context is None:
            context = {}
        
        action_type = action.get("type", "")
        params = action.get("params", {})
        action_id = action.get("id", f"action_{int(time.time())}")
        
        # Substitute context variables in params (simple {{key}} replacement)
        params = self._substitute_context(params, context)
        
        try:
            if action_type == "chat.generate":
                return self._handle_chat_generate(params)
            elif action_type == "image.generate":
                return self._handle_image_generate(params)
            elif action_type == "poster.publish":
                return self._handle_poster_publish(params)
            elif action_type == "vault.store":
                return self._handle_vault_store(params)
            elif action_type == "vault.get":
                return self._handle_vault_get(params)
            elif action_type == "telegram.send":
                return self._handle_telegram_send(params)
            elif action_type == "qdrant.upsert":
                return self._handle_qdrant_upsert(params)
            elif action_type == "qdrant.search":
                return self._handle_qdrant_search(params)
            elif action_type == "endpoint.call":
                return self._handle_endpoint_call(params)
            elif action_type == "reddit.scrape":
                return self._handle_reddit_scrape(params)
            elif action_type == "auto.post":
                return self._handle_auto_post(params)
            elif action_type == "vault.manage":
                return self._handle_vault_manage(params)
            elif action_type == "chatbot.chat":
                return self._handle_chatbot_chat(params)
            elif action_type == "telegram.webhook":
                return self._handle_telegram_webhook(params)
            else:
                return {
                    "status": "error",
                    "error": "unknown_action_type",
                    "details": f"Action type '{action_type}' is not supported"
                }
        except Exception as e:
            logging.error(f"Error executing action {action_id} ({action_type}): {e}")
            return {
                "status": "error",
                "error": "execution_failed",
                "details": str(e)
            }
    
    def _substitute_context(self, params: Any, context: Dict[str, Any]) -> Any:
        """Enhanced context variable substitution for {{key}} and {{key.path}} patterns"""
        if isinstance(params, dict):
            return {k: self._substitute_context(v, context) for k, v in params.items()}
        elif isinstance(params, list):
            return [self._substitute_context(item, context) for item in params]
        elif isinstance(params, str):
            # Enhanced substitution for {{key}} or {{key.path.to.value}}
            import re
            
            def replace_match(match):
                reference = match.group(1)  # Extract content between {{ and }}
                parts = reference.split('.')
                action_id = parts[0]
                
                if action_id not in context:
                    return match.group(0)  # Return original if action not found
                
                result = context[action_id]
                
                # Navigate through the path
                try:
                    for part in parts[1:]:
                        if isinstance(result, dict):
                            result = result.get(part, {})
                        else:
                            return str(result)  # If we can't navigate further, return current value
                    
                    # If no path specified, default to output
                    if len(parts) == 1 and isinstance(result, dict) and 'output' in result:
                        result = result['output']
                    
                    return str(result) if result is not None else ""
                except:
                    return match.group(0)  # Return original on error
            
            # Replace all {{...}} patterns
            params = re.sub(r'\{\{([^}]+)\}\}', replace_match, params)
        return params
    
    def _handle_chat_generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat.generate action - use existing content generator logic"""
        prompt = params.get("prompt", "")
        max_tokens = params.get("max_tokens", 150)
        
        if not prompt:
            return {
                "status": "error",
                "error": "missing_prompt",
                "details": "prompt parameter is required"
            }
        
        # Check if OpenAI API key is available
        if not os.environ.get("OPENAI_API_KEY"):
            # Mock response
            mock_content = f"Mock AI response to: {prompt[:50]}{'...' if len(prompt) > 50 else ''}"
            return {
                "status": "mock",
                "output": {
                    "content": mock_content,
                    "provider": "mock",
                    "tokens_used": len(mock_content.split())
                }
            }
        
        # Real OpenAI API call
        try:
            headers = {
                "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-5",  # the newest OpenAI model is "gpt-5" which was released August 7, 2025. do not change this unless explicitly requested by the user
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return {
                    "status": "ok",
                    "output": {
                        "content": content,
                        "provider": "openai",
                        "tokens_used": data.get("usage", {}).get("total_tokens", 0)
                    }
                }
            else:
                logging.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "error": "api_error",
                    "details": f"OpenAI API returned {response.status_code}"
                }
        
        except Exception as e:
            logging.error(f"OpenAI API exception: {e}")
            return {
                "status": "error",
                "error": "api_exception",
                "details": str(e)
            }
    
    def _handle_image_generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle image.generate action - use existing image service"""
        prompt = params.get("prompt", "")
        style = params.get("style")
        size = params.get("size", "1024x1024")
        
        if not prompt:
            return {
                "status": "error",
                "error": "missing_prompt",
                "details": "prompt parameter is required"
            }
        
        result = generate_image(prompt, style, size)
        
        if result.get("ok"):
            return {
                "status": "ok",
                "output": {
                    "file_url": result["file_url"],
                    "meta": result["meta"]
                }
            }
        else:
            return {
                "status": "error",
                "error": result.get("error", "generation_failed"),
                "details": result.get("details", "Image generation failed")
            }
    
    def _handle_poster_publish(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle poster.publish action - stub implementation for now"""
        platform = params.get("platform", "unknown")
        content = params.get("content", "")
        
        # Log the action for now (stub implementation)
        logging.info(f"poster.publish: platform={platform}, content_length={len(content)}")
        
        return {
            "status": "mock",
            "output": {
                "platform": platform,
                "post_id": f"mock_post_{int(time.time())}",
                "status": "published",
                "url": f"https://{platform}.com/posts/mock_post_{int(time.time())}"
            }
        }
    
    def _handle_vault_store(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle vault.store action - simple key-value storage"""
        key = params.get("key", "")
        value = params.get("value")
        
        if not key:
            return {
                "status": "error",
                "error": "missing_key",
                "details": "key parameter is required"
            }
        
        # Store with timestamp
        self.vault_data[key] = {
            "value": value,
            "stored_at": datetime.now().isoformat(),
            "type": type(value).__name__
        }
        
        self._save_vault()
        
        return {
            "status": "ok",
            "output": {
                "key": key,
                "stored": True,
                "stored_at": self.vault_data[key]["stored_at"]
            }
        }
    
    def _handle_vault_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle vault.get action - retrieve stored value"""
        key = params.get("key", "")
        default = params.get("default")
        
        if not key:
            return {
                "status": "error",
                "error": "missing_key",
                "details": "key parameter is required"
            }
        
        if key in self.vault_data:
            stored_item = self.vault_data[key]
            return {
                "status": "ok",
                "output": {
                    "key": key,
                    "value": stored_item["value"],
                    "stored_at": stored_item["stored_at"],
                    "found": True
                }
            }
        else:
            return {
                "status": "ok",
                "output": {
                    "key": key,
                    "value": default,
                    "found": False
                }
            }
    
    def _handle_telegram_send(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle telegram.send action - send message via Telegram API"""
        text = params.get("text", "")
        chat_id = params.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID")
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        
        if not text:
            return {
                "status": "error",
                "error": "missing_text",
                "details": "text parameter is required"
            }
        
        if not bot_token or not chat_id:
            # Mock response when credentials are missing
            logging.info(f"telegram.send (mock): {text[:50]}{'...' if len(text) > 50 else ''}")
            return {
                "status": "mock",
                "output": {
                    "message_id": f"mock_msg_{int(time.time())}",
                    "chat_id": chat_id or "unknown",
                    "sent": True,
                    "provider": "mock"
                }
            }
        
        # Real Telegram API call
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"  # Enable HTML formatting
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return {
                        "status": "ok",
                        "output": {
                            "message_id": data["result"]["message_id"],
                            "chat_id": data["result"]["chat"]["id"],
                            "sent": True,
                            "provider": "telegram"
                        }
                    }
                else:
                    return {
                        "status": "error",
                        "error": "telegram_api_error",
                        "details": data.get("description", "Unknown Telegram API error")
                    }
            else:
                return {
                    "status": "error",
                    "error": "telegram_http_error",
                    "details": f"HTTP {response.status_code}: {response.text}"
                }
        
        except Exception as e:
            logging.error(f"Telegram API exception: {e}")
            return {
                "status": "error",
                "error": "telegram_exception",
                "details": str(e)
            }
    
    def _handle_qdrant_upsert(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle qdrant.upsert action - vector database upsert"""
        collection = params.get("collection", os.environ.get("QDRANT_COLLECTION", "brain"))
        point_id = params.get("id", f"point_{int(time.time())}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}")
        vector = params.get("vector")
        payload = params.get("payload", {})
        
        qdrant_url = os.environ.get("QDRANT_URL")
        qdrant_api_key = os.environ.get("QDRANT_API_KEY")
        
        if not qdrant_url:
            # Mock upsert - save to local file
            if collection not in self.qdrant_mock:
                self.qdrant_mock[collection] = []
            
            # Generate mock vector if not provided
            if not vector:
                vector = self._generate_mock_vector()
            
            point = {
                "id": point_id,
                "vector": vector,
                "payload": payload,
                "upserted_at": datetime.now().isoformat()
            }
            
            # Remove existing point with same ID
            self.qdrant_mock[collection] = [p for p in self.qdrant_mock[collection] if p["id"] != point_id]
            # Add new point
            self.qdrant_mock[collection].append(point)
            
            self._save_qdrant_mock()
            
            return {
                "status": "mock",
                "output": {
                    "id": point_id,
                    "collection": collection,
                    "vector_size": len(vector),
                    "upserted": True,
                    "provider": "mock"
                }
            }
        
        # Real Qdrant API call
        try:
            headers = {"Content-Type": "application/json"}
            if qdrant_api_key:
                headers["api-key"] = qdrant_api_key
            
            # Ensure collection exists
            collection_url = f"{qdrant_url}/collections/{collection}"
            collection_check = requests.get(collection_url, headers=headers, timeout=10)
            
            if collection_check.status_code == 404:
                # Create collection
                create_payload = {
                    "vectors": {
                        "size": len(vector) if vector else 768,
                        "distance": "Cosine"
                    }
                }
                create_response = requests.put(collection_url, headers=headers, json=create_payload, timeout=10)
                if create_response.status_code not in [200, 201]:
                    return {
                        "status": "error",
                        "error": "collection_creation_failed",
                        "details": f"Failed to create collection: {create_response.text}"
                    }
            
            # Upsert point
            upsert_url = f"{qdrant_url}/collections/{collection}/points"
            upsert_payload = {
                "points": [{
                    "id": point_id,
                    "vector": vector or self._generate_mock_vector(),
                    "payload": payload
                }]
            }
            
            response = requests.put(upsert_url, headers=headers, json=upsert_payload, timeout=10)
            
            if response.status_code in [200, 201]:
                return {
                    "status": "ok",
                    "output": {
                        "id": point_id,
                        "collection": collection,
                        "upserted": True,
                        "provider": "qdrant"
                    }
                }
            else:
                return {
                    "status": "error",
                    "error": "qdrant_upsert_failed",
                    "details": f"HTTP {response.status_code}: {response.text}"
                }
        
        except Exception as e:
            logging.error(f"Qdrant upsert exception: {e}")
            return {
                "status": "error",
                "error": "qdrant_exception",
                "details": str(e)
            }
    
    def _handle_qdrant_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle qdrant.search action - vector similarity search"""
        collection = params.get("collection", os.environ.get("QDRANT_COLLECTION", "brain"))
        vector = params.get("vector")
        limit = params.get("limit", 3)
        score_threshold = params.get("score_threshold", 0.5)
        
        qdrant_url = os.environ.get("QDRANT_URL")
        qdrant_api_key = os.environ.get("QDRANT_API_KEY")
        
        if not qdrant_url:
            # Mock search - return top results from file
            if collection not in self.qdrant_mock:
                return {
                    "status": "mock",
                    "output": {
                        "collection": collection,
                        "results": [],
                        "provider": "mock"
                    }
                }
            
            # Return top N results (mock scoring)
            points = self.qdrant_mock[collection][:limit]
            results = []
            
            for i, point in enumerate(points):
                results.append({
                    "id": point["id"],
                    "score": 0.9 - (i * 0.1),  # Mock decreasing scores
                    "payload": point["payload"]
                })
            
            return {
                "status": "mock",
                "output": {
                    "collection": collection,
                    "results": results,
                    "provider": "mock"
                }
            }
        
        # Real Qdrant API call
        try:
            headers = {"Content-Type": "application/json"}
            if qdrant_api_key:
                headers["api-key"] = qdrant_api_key
            
            search_url = f"{qdrant_url}/collections/{collection}/points/search"
            search_payload = {
                "vector": vector or self._generate_mock_vector(),
                "limit": limit,
                "score_threshold": score_threshold,
                "with_payload": True
            }
            
            response = requests.post(search_url, headers=headers, json=search_payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for result in data.get("result", []):
                    results.append({
                        "id": result["id"],
                        "score": result["score"],
                        "payload": result.get("payload", {})
                    })
                
                return {
                    "status": "ok",
                    "output": {
                        "collection": collection,
                        "results": results,
                        "provider": "qdrant"
                    }
                }
            else:
                return {
                    "status": "error",
                    "error": "qdrant_search_failed",
                    "details": f"HTTP {response.status_code}: {response.text}"
                }
        
        except Exception as e:
            logging.error(f"Qdrant search exception: {e}")
            return {
                "status": "error",
                "error": "qdrant_exception",
                "details": str(e)
            }
    
    def _handle_endpoint_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic endpoint.call action - make HTTP requests to internal endpoints"""
        endpoint = params.get("endpoint", "")
        method = params.get("method", "POST").upper()
        payload = params.get("payload", {})
        
        if not endpoint:
            return {
                "status": "error",
                "error": "missing_endpoint",
                "details": "endpoint parameter is required"
            }
        
        # Ensure endpoint starts with /api/v1
        if not endpoint.startswith("/api/v1/"):
            endpoint = f"/api/v1/{endpoint.lstrip('/')}"
        
        try:
            base_url = "http://localhost:5000"
            full_url = f"{base_url}{endpoint}"
            
            if method == "POST":
                response = requests.post(full_url, json=payload, timeout=30)
            elif method == "GET":
                response = requests.get(full_url, params=payload, timeout=30)
            else:
                return {
                    "status": "error",
                    "error": "unsupported_method",
                    "details": f"HTTP method '{method}' is not supported"
                }
            
            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            if response.status_code < 400:
                return {
                    "status": "ok",
                    "output": {
                        "status_code": response.status_code,
                        "response": response_data,
                        "endpoint": endpoint
                    }
                }
            else:
                return {
                    "status": "error",
                    "error": "http_error",
                    "details": f"HTTP {response.status_code}: {response_data}"
                }
        
        except Exception as e:
            logging.error(f"Endpoint call exception: {e}")
            return {
                "status": "error",
                "error": "endpoint_exception",
                "details": str(e)
            }
    
    def _handle_reddit_scrape(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle reddit.scrape action - call reddit scraper endpoint"""
        return self._handle_endpoint_call({
            "endpoint": "/api/v1/reddit-scraper",
            "method": "POST",
            "payload": params
        })
    
    def _handle_auto_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle auto.post action - call auto poster endpoint"""
        return self._handle_endpoint_call({
            "endpoint": "/api/v1/auto-poster",
            "method": "POST",
            "payload": params
        })
    
    def _handle_vault_manage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle vault.manage action - call vault manager endpoint"""
        return self._handle_endpoint_call({
            "endpoint": "/api/v1/vault-manager",
            "method": "POST",
            "payload": params
        })
    
    def _handle_chatbot_chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chatbot.chat action - call chatbot engine endpoint"""
        return self._handle_endpoint_call({
            "endpoint": "/api/v1/chatbot-engine",
            "method": "POST",
            "payload": params
        })
    
    def _handle_telegram_webhook(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle telegram.webhook action - call telegram webhook endpoint"""
        return self._handle_endpoint_call({
            "endpoint": "/api/v1/hooks/telegram",
            "method": "POST",
            "payload": params
        })


# Global orchestrator instance
orchestrator = OrchestrationEngine()