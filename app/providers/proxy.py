"""Proxy pool manager for rotating proxy assignments and health checking."""

import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import httpx
from loguru import logger
from sqlmodel import select, asc

from app.config import settings
from app.models_accounts import Proxy


class ProxyManager:
    """Proxy pool manager for proxy rotation and health checking."""
    
    def __init__(self, proxy_pool_file: Optional[str] = None):
        self.proxy_pool_file = proxy_pool_file or settings.proxy_pool_file
        self.health_check_timeout = 10  # seconds
        self.health_check_url = "http://httpbin.org/ip"  # Simple endpoint to test proxy
        
    def load_proxies_from_file(self) -> List[Dict[str, Any]]:
        """Load proxies from file. Format: host:port:user:pass per line."""
        proxies = []
        
        if not os.path.exists(self.proxy_pool_file):
            logger.warning(f"Proxy file not found: {self.proxy_pool_file}")
            return proxies
            
        try:
            with open(self.proxy_pool_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue  # Skip empty lines and comments
                        
                    parts = line.split(':')
                    if len(parts) < 2:
                        logger.warning(f"Invalid proxy format on line {line_num}: {line}")
                        continue
                    elif len(parts) == 2:
                        # host:port format
                        host, port = parts
                        user, password = None, None
                    elif len(parts) == 4:
                        # host:port:user:pass format
                        host, port, user, password = parts
                    else:
                        logger.warning(f"Invalid proxy format on line {line_num}: {line}")
                        continue
                    
                    try:
                        port = int(port)
                    except ValueError:
                        logger.warning(f"Invalid port number on line {line_num}: {port}")
                        continue
                    
                    proxies.append({
                        "host": host,
                        "port": port,
                        "user": user if user else None,
                        "password": password if password else None
                    })
                    
            logger.info(f"Loaded {len(proxies)} proxies from {self.proxy_pool_file}")
            
        except Exception as e:
            logger.error(f"Error loading proxies from file: {e}")
            
        return proxies
    
    async def sync_proxies_to_database(self, db_session) -> int:
        """Sync proxies from file to database. Returns number of new proxies added."""
        file_proxies = self.load_proxies_from_file()
        if not file_proxies:
            return 0
            
        # Get existing proxies from database
        existing_proxies = db_session.exec(select(Proxy)).all()
        existing_proxy_keys = {(p.host, p.port) for p in existing_proxies}
        
        new_proxies_added = 0
        
        for proxy_data in file_proxies:
            proxy_key = (proxy_data["host"], proxy_data["port"])
            
            if proxy_key not in existing_proxy_keys:
                # Add new proxy to database
                proxy = Proxy(
                    host=proxy_data["host"],
                    port=proxy_data["port"],
                    user=proxy_data["user"],
                    password=proxy_data["password"],
                    healthy=True  # Assume healthy initially
                )
                db_session.add(proxy)
                new_proxies_added += 1
                
        if new_proxies_added > 0:
            db_session.commit()
            logger.info(f"Added {new_proxies_added} new proxies to database")
            
        return new_proxies_added
    
    async def get_least_used_proxy(self, db_session) -> Optional[Proxy]:
        """Get the proxy that was used least recently."""
        proxies = db_session.exec(
            select(Proxy)
            .where(Proxy.healthy == True)
            .order_by(asc(Proxy.last_used_at))
        ).all()
        
        if not proxies:
            logger.warning("No healthy proxies available")
            return None
            
        return proxies[0]
    
    async def mark_proxy_used(self, db_session, proxy_id: int) -> bool:
        """Mark a proxy as used by updating its last_used_at timestamp."""
        proxy = db_session.get(Proxy, proxy_id)
        if not proxy:
            logger.error(f"Proxy not found: {proxy_id}")
            return False
            
        proxy.last_used_at = datetime.utcnow()
        db_session.add(proxy)
        db_session.commit()
        logger.info(f"Marked proxy {proxy_id} as used")
        return True
    
    async def test_proxy_health(self, proxy: Proxy) -> bool:
        """Test if a proxy is healthy by making a request through it."""
        proxy_url = self._format_proxy_url(proxy)
        
        try:
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=self.health_check_timeout
            ) as client:
                response = await client.get(self.health_check_url)
                success = response.status_code == 200
                
                if success:
                    logger.debug(f"Proxy {proxy.host}:{proxy.port} is healthy")
                else:
                    logger.warning(f"Proxy {proxy.host}:{proxy.port} returned status {response.status_code}")
                    
                return success
                
        except Exception as e:
            logger.warning(f"Proxy {proxy.host}:{proxy.port} health check failed: {e}")
            return False
    
    async def update_proxy_health(self, db_session, proxy_id: int, healthy: bool) -> bool:
        """Update the health status of a proxy."""
        proxy = db_session.get(Proxy, proxy_id)
        if not proxy:
            logger.error(f"Proxy not found: {proxy_id}")
            return False
            
        proxy.healthy = healthy
        db_session.add(proxy)
        db_session.commit()
        
        status = "healthy" if healthy else "unhealthy"
        logger.info(f"Marked proxy {proxy_id} as {status}")
        return True
    
    async def health_check_all_proxies(self, db_session) -> Dict[str, int]:
        """Health check all proxies and update their status. Returns counts."""
        proxies = db_session.exec(select(Proxy)).all()
        
        if not proxies:
            logger.info("No proxies to health check")
            return {"total": 0, "healthy": 0, "unhealthy": 0}
        
        healthy_count = 0
        unhealthy_count = 0
        
        # Test proxies in batches to avoid overwhelming them
        batch_size = 5
        for i in range(0, len(proxies), batch_size):
            batch = proxies[i:i + batch_size]
            
            # Test batch concurrently
            health_tasks = [self.test_proxy_health(proxy) for proxy in batch]
            health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
            
            # Update database with results
            for proxy, health_result in zip(batch, health_results):
                if isinstance(health_result, Exception):
                    healthy = False
                    logger.error(f"Health check exception for proxy {proxy.id}: {health_result}")
                else:
                    healthy = bool(health_result)
                
                if healthy != proxy.healthy:
                    await self.update_proxy_health(db_session, proxy.id, healthy)
                
                if healthy:
                    healthy_count += 1
                else:
                    unhealthy_count += 1
            
            # Small delay between batches
            if i + batch_size < len(proxies):
                await asyncio.sleep(1)
        
        logger.info(f"Health check completed: {healthy_count} healthy, {unhealthy_count} unhealthy")
        
        return {
            "total": len(proxies),
            "healthy": healthy_count,
            "unhealthy": unhealthy_count
        }
    
    def _format_proxy_url(self, proxy: Proxy) -> str:
        """Format proxy as URL for httpx."""
        if proxy.user and proxy.password:
            return f"http://{proxy.user}:{proxy.password}@{proxy.host}:{proxy.port}"
        else:
            return f"http://{proxy.host}:{proxy.port}"
    
    def get_proxy_dict(self, proxy: Proxy) -> Dict[str, Any]:
        """Get proxy as dictionary for API responses."""
        return {
            "id": proxy.id,
            "host": proxy.host,
            "port": proxy.port,
            "user": proxy.user,
            "healthy": proxy.healthy,
            "last_used_at": proxy.last_used_at.isoformat() if proxy.last_used_at else None,
            "url": f"{proxy.host}:{proxy.port}"
        }


# Global proxy manager instance
proxy_manager = ProxyManager()


async def assign_proxy_to_session(db_session, session_record) -> Optional[Dict[str, Any]]:
    """Assign the least used healthy proxy to a session."""
    proxy = await proxy_manager.get_least_used_proxy(db_session)
    
    if not proxy:
        logger.warning("No healthy proxies available for assignment")
        return None
    
    # Update session with proxy
    session_record.proxy_id = proxy.id
    session_record.updated_at = datetime.utcnow()
    db_session.add(session_record)
    
    # Mark proxy as used
    if proxy.id is not None:
        await proxy_manager.mark_proxy_used(db_session, proxy.id)
    
    logger.info(f"Assigned proxy {proxy.id} to session {session_record.id}")
    
    return proxy_manager.get_proxy_dict(proxy)


def parse_proxy_string(proxy_string: str) -> Optional[Dict[str, Any]]:
    """Parse proxy string in format host:port:user:pass or host:port."""
    if not proxy_string:
        return None
        
    parts = proxy_string.split(':')
    
    if len(parts) == 2:
        host, port = parts
        user, password = None, None
    elif len(parts) == 4:
        host, port, user, password = parts
    else:
        logger.warning(f"Invalid proxy string format: {proxy_string}")
        return None
    
    try:
        port = int(port)
    except ValueError:
        logger.warning(f"Invalid port number in proxy string: {port}")
        return None
    
    return {
        "host": host,
        "port": port,
        "user": user if user else None,
        "password": password if password else None
    }