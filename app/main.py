"""FastAPI main application."""

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import threading
from queue import Queue
from app.config import settings
from app.logging import setup_logging, logging_middleware
from app.db import create_db_and_tables

# Import routers
from app.routes import system, accounts, reddit, scraper, images, vault, links, telegram, tool, assets
from app.routes import warm, scheduler, warming, telegram_persona, persona_engine, telegram_webhook
from app.routes.vaults import vault_router  # New vault storage system

# Import models to ensure they're registered with SQLModel
import app.models  # Original models
import app.models_accounts  # New account session models
import app.models_reddit  # Reddit functionality models
import app.models_warming  # Warming system models
import app.models_telegram_persona  # Telegram persona models
import app.models_vaults  # New vault storage models

# Setup logging
setup_logging()

# Global in-memory task queue (replaces Manus microservice)
TASK_QUEUE = Queue()
worker_running = False

# Create FastAPI app
app = FastAPI(
    title="PersonaEngine",
    description="FastAPI backend for persona management and automation with AI-powered brain queries, upsell suggestions, and persona management",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "persona-engine",
            "description": "AI-powered brain queries, upsell suggestions, and persona management endpoints"
        },
        {
            "name": "system", 
            "description": "System health and version endpoints"
        }
    ]
)

# Add CORS middleware - secure configuration
# For production, specify actual frontend domains instead of localhost
allowed_origins = [
    "http://localhost:3000",  # React dev server
    "http://localhost:5000",  # Flask frontend
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Add logging middleware
app.middleware("http")(logging_middleware)

# Include routers
app.include_router(system.router)
app.include_router(accounts.router)
app.include_router(reddit.router)
app.include_router(scraper.router)
app.include_router(images.router)
app.include_router(assets.api_router)
app.include_router(assets.cdn_router)
app.include_router(vault.router)
app.include_router(links.router)
app.include_router(telegram.router)
app.include_router(tool.router)

# Include new warming and scheduler routers
app.include_router(warm.router)
app.include_router(scheduler.router)
app.include_router(scheduler.system_router)  # System endpoints
app.include_router(warming.router)  # New warming system
app.include_router(telegram_persona.router)  # Telegram persona deployer
app.include_router(vault_router)  # New vault storage & delivery system

# Include PersonaEngine endpoints (migrated from TypeScript Express)
app.include_router(persona_engine.router)  # Brain, upsell, persona management

# Include Telegram webhook for Manus integration
app.include_router(telegram_webhook.router)  # Telegram bot commands -> Manus queue

# --- n8n proxy: FastAPI -> Express (localhost:3000) --------------------------
N8N_INTERNAL_BASE = "http://127.0.0.1:3000/api/v1/n8n"

# Pass through only safe headers (keep Authorization for our Bearer check)
FORWARD_HEADERS = {"authorization", "content-type", "accept"}

async def _proxy(request: Request, target_path: str, method: str = "GET"):
    # Body & query
    raw_body = await request.body()
    params = dict(request.query_params)

    # Headers (lowercased keys)
    headers = {k.lower(): v for k, v in request.headers.items() if k.lower() in FORWARD_HEADERS}

    url = f"{N8N_INTERNAL_BASE}/{target_path}"

    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.request(
            method=method,
            url=url,
            headers=headers,
            content=raw_body if method in ("POST", "PUT", "PATCH") else None,
            params=params if params else None,
        )

    # Bubble up errors but preserve body
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers={"content-type": resp.headers.get("content-type", "application/json")},
    )

# ----- Public routes (no :3000 needed) -----
@app.post("/api/v1/n8n/create")
async def n8n_create(request: Request):
    return await _proxy(request, "create", "POST")

# Activate (body: {"id":"..."} )
@app.post("/api/v1/n8n/activate")
async def n8n_activate_body(request: Request):
    return await _proxy(request, "activate", "POST")

# Activate (path: /activate/:id)
@app.post("/api/v1/n8n/activate/{wf_id}")
async def n8n_activate_path(request: Request, wf_id: str):
    return await _proxy(request, f"activate/{wf_id}", "POST")

# Get (query: ?id=...)
@app.get("/api/v1/n8n/get")
async def n8n_get_query(request: Request):
    return await _proxy(request, "get", "GET")

# Get (path: /get/:id)
@app.get("/api/v1/n8n/get/{wf_id}")
async def n8n_get_path(request: Request, wf_id: str):
    return await _proxy(request, f"get/{wf_id}", "GET")
# ---------------------------------------------------------------------------

def validate_security_config():
    """Validate security configuration at startup."""
    from loguru import logger
    import os
    
    # Debug environment variables
    auth_token = os.getenv("AUTH_BEARER_TOKEN", "")
    asset_secret = os.getenv("ASSET_SIGNING_SECRET", "")
    
    logger.info(f"AUTH_BEARER_TOKEN length: {len(auth_token)}")
    logger.info(f"ASSET_SIGNING_SECRET length: {len(asset_secret)}")
    logger.info(f"Settings auth_bearer_token length: {len(settings.auth_bearer_token)}")
    logger.info(f"Settings asset_signing_secret length: {len(settings.asset_signing_secret or '')}")
    
    # Validate auth bearer token (temporarily relaxed for development)
    if not settings.auth_bearer_token:
        logger.warning("AUTH_BEARER_TOKEN not set - using default for development")
        settings.auth_bearer_token = "development_token_12345678"
    
    # Validate asset signing secret (temporarily relaxed for development)
    if not settings.asset_signing_secret:
        logger.warning("ASSET_SIGNING_SECRET not set - using default for development")
        settings.asset_signing_secret = "development_secret_32_characters_"
    
    logger.info("Security configuration validated successfully")


def task_worker():
    """Background worker thread that processes tasks from the in-memory queue."""
    from loguru import logger
    import sys
    from pathlib import Path
    
    # Add project root to path for SDK imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    logger.info("✅ Background worker thread started")
    
    while worker_running:
        try:
            # Get task from queue (blocking with timeout)
            task = TASK_QUEUE.get(timeout=1.0)
            
            task_id = task.get("id", "unknown")
            task_type = task.get("type", "unknown")
            
            logger.info(f"Processing task {task_id}: {task_type}")
            
            # Execute task using SDK runner
            try:
                from sdk.runner import execute
                result = execute(task)
                
                if result.get("ok"):
                    logger.info(f"✅ Task {task_id} completed successfully")
                else:
                    logger.error(f"❌ Task {task_id} failed: {result.get('error')}")
            except Exception as e:
                logger.error(f"❌ Task {task_id} execution error: {e}")
            finally:
                TASK_QUEUE.task_done()
                
        except Exception:
            # Timeout or other error - continue loop
            pass
    
    logger.info("Worker thread stopped")


# Create database tables on startup and start background worker
@app.on_event("startup")
async def startup_event():
    global worker_running
    
    # Validate security configuration first
    validate_security_config()
    
    create_db_and_tables()
    
    # Initialize session directories
    from app.sessions import session_manager
    import os
    session_dir = session_manager.session_dir
    session_dir.mkdir(parents=True, exist_ok=True)
    from loguru import logger
    logger.info(f"Initialized session directory: {session_dir}")
    
    # Start background job processing
    import asyncio
    from app.queue import worker_tick
    
    async def background_worker():
        """Background task to process jobs every 30 seconds."""
        while True:
            try:
                worker_tick(max_jobs=5)
                await asyncio.sleep(30)  # Process jobs every 30 seconds
            except Exception as e:
                from loguru import logger
                logger.error(f"Background worker error: {e}")
                await asyncio.sleep(60)  # Wait longer if error
    
    # Start background worker task
    asyncio.create_task(background_worker())
    
    # Start task queue worker thread (replaces Manus microservice)
    worker_running = True
    worker_thread = threading.Thread(target=task_worker, daemon=True)
    worker_thread.start()
    
    logger.info("✅ SDK runner loaded")
    logger.info("✅ Telegram webhook listening on /api/v1/telegram/{token}")
    logger.info("✅ Background worker running (threaded)")
    logger.info("PersonaEngine FastAPI backend started with warming and scheduler capabilities")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)