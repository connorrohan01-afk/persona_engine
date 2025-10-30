import os
from flask import Flask, request, g, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import time
import logging
from functools import wraps
from collections import defaultdict
from typing import DefaultDict
import os
from database import db
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create the app
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https
app.secret_key = os.environ.get("SESSION_SECRET")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL") or "sqlite:///app.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Enable CORS for all routes
CORS(app)

# Blueprint registration moved to after database setup

# Create database tables
with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401
    db.create_all()

# Import and register the API blueprint - circular import now resolved via database.py
from api import api
app.register_blueprint(api)

# Environment variable checks and warnings
def check_environment():
    """Check for required environment variables and log warnings"""
    warnings = []
    
    # Check for Telegram bot token
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        warnings.append("⚠️  TELEGRAM_BOT_TOKEN not set - Telegram integration will fail")
    
    # Check for N8N webhook URL
    n8n_url = os.environ.get("N8N_WEBHOOK_URL")
    if not n8n_url:
        warnings.append("⚠️  N8N_WEBHOOK_URL not set - Brain automation is offline")
    
    # Log warnings
    if warnings:
        logging.warning("Environment variable warnings:")
        for warning in warnings:
            logging.warning(f"  {warning}")
        logging.warning("  Set these variables in Replit Secrets or .env file")
    else:
        logging.info("✅ All required environment variables are configured")

# Environment check will be run in main.py after app initialization

# Rate limiting storage
rate_limit_storage: DefaultDict[str, list[datetime]] = defaultdict(list)

def check_api_key():
    """Check API key authentication if APP_API_KEY is set"""
    app_api_key = os.environ.get("APP_API_KEY")
    
    if not app_api_key:
        return True  # No API key required
    
    # Check X-API-Key header
    provided_key = request.headers.get("X-API-Key")
    
    if not provided_key:
        return False
    
    return provided_key == app_api_key

def check_rate_limit(identifier: str, limit: int, window_seconds: int) -> bool:
    """Check if request is within rate limit"""
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=window_seconds)
    timestamps = rate_limit_storage[identifier]
    
    # purge old timestamps in place
    timestamps[:] = [ts for ts in timestamps if ts > window_start]
    
    if len(timestamps) >= limit:
        return False
    
    timestamps.append(now)
    return True

# Security and rate limiting middleware
@app.before_request
def security_and_rate_limit():
    g.start_time = time.time()
    
    # Skip security for health check and static files
    if request.path in ['/', '/healthz'] or request.path.startswith('/static/'):
        return
    
    # API key authentication
    if not check_api_key():
        return jsonify({
            "ok": False,
            "error": "invalid_api_key",
            "message": "Valid X-API-Key header required"
        }), 401
    
    # Rate limiting for API endpoints
    if request.path.startswith('/api/'):
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        
        # General API rate limit: 60 requests per minute
        if not check_rate_limit(f"api_{client_ip}", 60, 60):
            return jsonify({
                "ok": False,
                "error": "rate_limit_exceeded",
                "message": "API rate limit exceeded. Try again later."
            }), 429
        
        # Stricter limits for compute-intensive endpoints
        if request.path in ['/api/v1/brain', '/api/v1/brain/run'] and request.method == 'POST':
            if not check_rate_limit(f"brain_{client_ip}", 10, 60):
                return jsonify({
                    "ok": False,
                    "error": "brain_rate_limit_exceeded",
                    "message": "Brain API rate limit exceeded (10/min). Try again later."
                }), 429
    
    # Telegram-specific rate limiting
    if request.path == '/api/v1/hooks/telegram':
        # Extract chat_id from request if possible
        try:
            data = request.get_json()
            if data and 'message' in data and 'chat' in data['message']:
                chat_id = str(data['message']['chat']['id'])
                
                # 10 messages per minute per chat
                if not check_rate_limit(f"telegram_{chat_id}", 10, 60):
                    logging.warning(f"Telegram rate limit exceeded for chat {chat_id}")
                    return jsonify({"ok": True}), 200  # Still return 200 for Telegram
        except:
            pass  # Ignore errors in rate limiting

@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        logging.info(f"{request.method} {request.path} - {response.status_code} - {duration:.3f}s")
    return response

@app.route('/')
def home():
    return "Hello, Flask app is running!"

@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify(ok=True), 200


@app.get("/routes")
def routes():
    return jsonify(sorted([str(r.rule) for r in app.url_map.iter_rules()]))




@app.route('/docs')
def swagger_ui():
    """Serve Swagger UI for API documentation"""
    swagger_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Workflow Orchestration API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin:0; background: #fafafa; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
    window.onload = function() {
        const ui = SwaggerUIBundle({
            url: '/api-spec',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
            ],
            plugins: [
                SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "StandaloneLayout"
        });
    };
    </script>
</body>
</html>
    '''
    return swagger_html

@app.route('/api-spec')
def openapi_spec():
    """Generate OpenAPI 3.0 specification for the API"""
    
    # Check if API key is required
    api_key_required = bool(os.environ.get("APP_API_KEY"))
    
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Workflow Orchestration Platform API",
            "version": "1.0.0",
            "description": "A comprehensive Flask-based content automation platform with orchestration capabilities, Telegram integration, image generation services, and workflow automation.",
            "contact": {
                "name": "API Support"
            }
        },
        "servers": [
            {
                "url": "/api/v1",
                "description": "Production API"
            }
        ],
        "paths": {
            "/brain": {
                "post": {
                    "tags": ["Orchestration"],
                    "summary": "Execute workflow synchronously",
                    "description": "Execute a workflow with multiple actions synchronously and return results immediately",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/WorkflowRequest"},
                                "example": {
                                    "actions": [
                                        {
                                            "id": "generate_content",
                                            "type": "chat.generate",
                                            "params": {"prompt": "Write a tweet about automation"}
                                        },
                                        {
                                            "id": "create_image",
                                            "type": "image.generate", 
                                            "params": {"prompt": "{{generate_content.output.content}}", "size": "512x512"}
                                        }
                                    ]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Workflow completed successfully", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/WorkflowResponse"}}}},
                        "207": {"description": "Workflow completed with some failures"},
                        "400": {"description": "Invalid request"},
                        "429": {"description": "Rate limit exceeded"}
                    }
                }
            },
            "/brain/run": {
                "post": {
                    "tags": ["Orchestration"],
                    "summary": "Execute workflow asynchronously",
                    "description": "Schedule a workflow for async execution and return run_id immediately",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/WorkflowRequest"}
                            }
                        }
                    },
                    "responses": {
                        "202": {"description": "Workflow scheduled successfully"},
                        "400": {"description": "Invalid request"},
                        "429": {"description": "Rate limit exceeded"}
                    }
                }
            },
            "/workflows/presets": {
                "post": {
                    "tags": ["Presets"],
                    "summary": "Create or update workflow preset",
                    "description": "Save a reusable workflow template",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/PresetRequest"},
                                "example": {
                                    "name": "daily-content",
                                    "description": "Generate daily social media content",
                                    "workflow": {
                                        "actions": [
                                            {"id": "gen_post", "type": "chat.generate", "params": {"prompt": "Create a motivational quote"}},
                                            {"id": "make_image", "type": "image.generate", "params": {"prompt": "{{gen_post.output.content}}"}}
                                        ]
                                    },
                                    "tags": ["daily", "content"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "Preset created"},
                        "200": {"description": "Preset updated"},
                        "400": {"description": "Invalid request"}
                    }
                },
                "get": {
                    "tags": ["Presets"],
                    "summary": "List workflow presets",
                    "parameters": [
                        {"name": "active", "in": "query", "schema": {"type": "boolean", "default": True}},
                        {"name": "tag", "in": "query", "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 100}},
                        {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}}
                    ],
                    "responses": {
                        "200": {"description": "List of presets"}
                    }
                }
            },
            "/workflows/presets/{name}": {
                "get": {
                    "tags": ["Presets"],
                    "summary": "Get workflow preset by name",
                    "parameters": [{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Preset details"},
                        "404": {"description": "Preset not found"}
                    }
                },
                "delete": {
                    "tags": ["Presets"],
                    "summary": "Delete workflow preset",
                    "parameters": [{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Preset deleted"},
                        "404": {"description": "Preset not found"}
                    }
                }
            },
            "/workflows/run-preset/{name}": {
                "post": {
                    "tags": ["Presets"],
                    "summary": "Run workflow preset immediately",
                    "description": "Execute a saved preset synchronously",
                    "parameters": [{"name": "name", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "context": {"type": "object", "description": "Context overrides"},
                                        "metadata": {"type": "object", "description": "Metadata overrides"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Preset executed successfully"},
                        "404": {"description": "Preset not found"}
                    }
                }
            },
            "/workflows/runs": {
                "get": {
                    "tags": ["Runs"],
                    "summary": "List workflow runs",
                    "parameters": [
                        {"name": "status", "in": "query", "schema": {"type": "string", "enum": ["running", "completed", "failed", "cancelled"]}},
                        {"name": "preset", "in": "query", "schema": {"type": "string"}},
                        {"name": "triggered_by", "in": "query", "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50}},
                        {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}}
                    ],
                    "responses": {
                        "200": {"description": "List of workflow runs"}
                    }
                }
            },
            "/workflows/runs/{id}": {
                "get": {
                    "tags": ["Runs"],
                    "summary": "Get workflow run details",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
                        {"name": "steps", "in": "query", "schema": {"type": "boolean", "default": True}}
                    ],
                    "responses": {
                        "200": {"description": "Run details"},
                        "404": {"description": "Run not found"}
                    }
                }
            },
            "/workflows/runs/{id}/cancel": {
                "post": {
                    "tags": ["Runs"],
                    "summary": "Cancel workflow run",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "Run cancelled"},
                        "404": {"description": "Run not found"}
                    }
                }
            },
            "/hooks/telegram": {
                "post": {
                    "tags": ["Integrations"],
                    "summary": "Telegram webhook",
                    "description": "Webhook endpoint for Telegram bot integration. Supports commands: /start, /help, /run <preset>, /status <run-id>",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {
                                            "type": "object",
                                            "properties": {
                                                "chat": {"type": "object", "properties": {"id": {"type": "integer"}}},
                                                "text": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Message processed"}
                    }
                }
            },
            "/image-generator": {
                "post": {
                    "tags": ["Services"],
                    "summary": "Generate images",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["prompt"],
                                    "properties": {
                                        "prompt": {"type": "string"},
                                        "size": {"type": "string", "default": "1024x1024"},
                                        "style": {"type": "string"}
                                    }
                                },
                                "example": {
                                    "prompt": "A futuristic cityscape at sunset",
                                    "size": "1024x1024",
                                    "style": "photorealistic"
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Image generated successfully"}
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "WorkflowRequest": {
                    "type": "object",
                    "required": ["actions"],
                    "properties": {
                        "actions": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Action"}
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "trace_id": {"type": "string"},
                                "initial_context": {"type": "object"}
                            }
                        }
                    }
                },
                "Action": {
                    "type": "object",
                    "required": ["id", "type"],
                    "properties": {
                        "id": {"type": "string", "description": "Unique action identifier"},
                        "type": {"type": "string", "enum": ["chat.generate", "image.generate", "telegram.send", "vault.store", "vault.get", "qdrant.upsert", "qdrant.search", "reddit.scrape", "auto.post", "vault.manage", "chatbot.chat", "telegram.webhook", "endpoint.call"]},
                        "params": {"type": "object", "description": "Action parameters"},
                        "continue_on_error": {"type": "boolean", "default": False}
                    }
                },
                "WorkflowResponse": {
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean"},
                        "trace_id": {"type": "string"},
                        "results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "type": {"type": "string"},
                                    "status": {"type": "string"},
                                    "output": {"type": "object"},
                                    "ms": {"type": "number"}
                                }
                            }
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "total_actions": {"type": "integer"},
                                "completed_actions": {"type": "integer"},
                                "total_ms": {"type": "number"}
                            }
                        }
                    }
                },
                "PresetRequest": {
                    "type": "object",
                    "required": ["name", "workflow"],
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "workflow": {"$ref": "#/components/schemas/WorkflowRequest"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "created_by": {"type": "string"}
                    }
                }
            }
        }
    }
    
    # Add security schemes if API key is required
    if api_key_required:
        spec["components"]["securitySchemes"] = {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key"
            }
        }
        spec["security"] = [{"ApiKeyAuth": []}]
    
    return spec

# App is started via main.py - no need for __main__ runner here