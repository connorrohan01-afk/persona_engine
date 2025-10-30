"""Session manager for account session lifecycle, cookies, and proxy assignment."""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from loguru import logger
from sqlmodel import select, desc

from app.config import settings
from app.models_accounts import AccountSession, SessionRecord, Proxy
from app.providers.proxy import assign_proxy_to_session, parse_proxy_string


class SessionManager:
    """Manager for account sessions, cookies, and proxy assignments."""
    
    def __init__(self, session_dir: Optional[str] = None):
        self.session_dir = Path(session_dir or settings.session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
    def get_account_session_dir(self, account_id: int) -> Path:
        """Get the session directory for a specific account."""
        account_dir = self.session_dir / str(account_id)
        account_dir.mkdir(parents=True, exist_ok=True)
        return account_dir
    
    def get_cookies_path(self, account_id: int) -> str:
        """Get the path to the cookies file for an account."""
        account_dir = self.get_account_session_dir(account_id)
        return str(account_dir / "cookies.json")
    
    async def new_session(
        self, 
        db_session,
        account: AccountSession, 
        proxy_string: Optional[str] = None,
        dry: bool = False
    ) -> Dict[str, Any]:
        """Create a new session for an account with optional proxy."""
        logger.info(f"Creating new session for account {account.id} (dry={dry})")
        
        # Create cookies file
        if account.id is None:
            raise ValueError("Account ID cannot be None")
        
        cookies_path = self.get_cookies_path(account.id)
        
        if dry:
            # In dry mode, create empty cookies dict
            cookies_data = {}
            logger.info(f"Dry mode: creating empty cookies file at {cookies_path}")
        else:
            # In normal mode, create with basic structure
            cookies_data = {
                "created_at": datetime.utcnow().isoformat(),
                "platform": account.platform,
                "username": account.username,
                "cookies": {}
            }
        
        # Write cookies file
        try:
            with open(cookies_path, 'w') as f:
                json.dump(cookies_data, f, indent=2)
            logger.info(f"Created cookies file: {cookies_path}")
        except Exception as e:
            logger.error(f"Failed to create cookies file: {e}")
            raise
        
        # Handle proxy assignment
        proxy_id = None
        proxy_info = None
        
        if proxy_string:
            # Use provided proxy
            proxy_data = parse_proxy_string(proxy_string)
            if proxy_data:
                # Check if proxy exists in database, add if not
                existing_proxy = db_session.exec(
                    select(Proxy).where(
                        Proxy.host == proxy_data["host"],
                        Proxy.port == proxy_data["port"]
                    )
                ).first()
                
                if existing_proxy:
                    proxy_id = existing_proxy.id
                    proxy_info = f"{existing_proxy.host}:{existing_proxy.port}"
                else:
                    # Add new proxy to database
                    new_proxy = Proxy(
                        host=proxy_data["host"],
                        port=proxy_data["port"],
                        user=proxy_data["user"],
                        password=proxy_data["password"],
                        healthy=True
                    )
                    db_session.add(new_proxy)
                    db_session.commit()
                    db_session.refresh(new_proxy)
                    proxy_id = new_proxy.id
                    proxy_info = f"{new_proxy.host}:{new_proxy.port}"
                    logger.info(f"Added new proxy to database: {proxy_info}")
        
        # Create session record
        session_record = SessionRecord(
            account_id=account.id,  # We already checked this is not None above
            tenant_id=account.tenant_id,
            status="active",
            cookies_path=cookies_path,
            proxy_id=proxy_id
        )
        
        db_session.add(session_record)
        db_session.commit()
        db_session.refresh(session_record)
        
        logger.info(f"Created session {session_record.id} for account {account.id}")
        
        return {
            "session_id": f"ses_{session_record.id}",
            "account_id": f"acc_{account.id}",
            "cookies_path": cookies_path,
            "proxy_id": f"prx_{proxy_id}" if proxy_id else None,
            "proxy": proxy_info,
            "status": session_record.status,
            "created_at": session_record.created_at.isoformat()
        }
    
    async def load_session(self, db_session, account_id: int) -> Optional[Dict[str, Any]]:
        """Load the most recent session for an account."""
        # Find the most recent session for this account
        session_record = db_session.exec(
            select(SessionRecord)
            .where(SessionRecord.account_id == account_id)
            .order_by(desc(SessionRecord.created_at))
        ).first()
        
        if not session_record:
            logger.warning(f"No session found for account {account_id}")
            return None
        
        # Get proxy info if assigned
        proxy_info = None
        if session_record.proxy_id:
            proxy = db_session.get(Proxy, session_record.proxy_id)
            if proxy:
                proxy_info = f"{proxy.host}:{proxy.port}"
        
        # Load cookies if file exists
        cookies_data = {}
        if session_record.cookies_path and os.path.exists(session_record.cookies_path):
            try:
                with open(session_record.cookies_path, 'r') as f:
                    cookies_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cookies from {session_record.cookies_path}: {e}")
        
        return {
            "session_id": f"ses_{session_record.id}",
            "account_id": f"acc_{account_id}",
            "status": session_record.status,
            "cookies_path": session_record.cookies_path,
            "proxy": proxy_info,
            "proxy_id": f"prx_{session_record.proxy_id}" if session_record.proxy_id else None,
            "cookies": cookies_data,
            "created_at": session_record.created_at.isoformat(),
            "updated_at": session_record.updated_at.isoformat()
        }
    
    async def update_session_status(
        self, 
        db_session, 
        session_id: int, 
        status: str
    ) -> bool:
        """Update the status of a session."""
        session_record = db_session.get(SessionRecord, session_id)
        if not session_record:
            logger.error(f"Session not found: {session_id}")
            return False
        
        session_record.status = status
        session_record.updated_at = datetime.utcnow()
        db_session.add(session_record)
        db_session.commit()
        
        logger.info(f"Updated session {session_id} status to {status}")
        return True
    
    async def assign_proxy(self, db_session, session_id: int) -> Optional[Dict[str, Any]]:
        """Assign a proxy to a session using least-used rotation."""
        session_record = db_session.get(SessionRecord, session_id)
        if not session_record:
            logger.error(f"Session not found: {session_id}")
            return None
        
        # Assign proxy using the proxy manager
        proxy_dict = await assign_proxy_to_session(db_session, session_record)
        
        if not proxy_dict:
            return None
        
        # Commit the session update
        db_session.commit()
        
        return {
            "proxy": proxy_dict["url"],
            "proxy_id": f"prx_{proxy_dict['id']}",
            "healthy": proxy_dict["healthy"],
            "assigned_at": datetime.utcnow().isoformat()
        }
    
    async def save_cookies(
        self, 
        account_id: int, 
        cookies: Dict[str, Any]
    ) -> bool:
        """Save cookies to the account's cookies file."""
        cookies_path = self.get_cookies_path(account_id)
        
        try:
            # Load existing cookies data
            existing_data = {}
            if os.path.exists(cookies_path):
                with open(cookies_path, 'r') as f:
                    existing_data = json.load(f)
            
            # Update cookies
            existing_data["cookies"] = cookies
            existing_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Save back to file
            with open(cookies_path, 'w') as f:
                json.dump(existing_data, f, indent=2)
            
            logger.info(f"Saved cookies for account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save cookies for account {account_id}: {e}")
            return False
    
    async def load_cookies(self, account_id: int) -> Dict[str, Any]:
        """Load cookies from the account's cookies file."""
        cookies_path = self.get_cookies_path(account_id)
        
        try:
            if not os.path.exists(cookies_path):
                logger.warning(f"Cookies file not found: {cookies_path}")
                return {}
            
            with open(cookies_path, 'r') as f:
                data = json.load(f)
                return data.get("cookies", {})
                
        except Exception as e:
            logger.error(f"Failed to load cookies for account {account_id}: {e}")
            return {}
    
    async def get_session_stats(self, db_session, tenant_id: str) -> Dict[str, Any]:
        """Get session statistics for a tenant."""
        total_sessions = db_session.exec(
            select(SessionRecord).where(SessionRecord.tenant_id == tenant_id)
        ).all()
        
        active_sessions = [s for s in total_sessions if s.status == "active"]
        sessions_with_proxy = [s for s in total_sessions if s.proxy_id is not None]
        
        return {
            "total_sessions": len(total_sessions),
            "active_sessions": len(active_sessions),
            "sessions_with_proxy": len(sessions_with_proxy),
            "session_statuses": {
                status: len([s for s in total_sessions if s.status == status])
                for status in set(s.status for s in total_sessions)
            }
        }


# Global session manager instance
session_manager = SessionManager()


def extract_session_id(session_id_string: str) -> int:
    """Extract numeric session ID from string format 'ses_123'."""
    if session_id_string.startswith("ses_"):
        return int(session_id_string[4:])
    return int(session_id_string)


def extract_account_id(account_id_string: str) -> int:
    """Extract numeric account ID from string format 'acc_123'."""
    if account_id_string.startswith("acc_"):
        return int(account_id_string[4:])
    return int(account_id_string)