from flask import Blueprint, request, jsonify
import logging
import json
import os
import re
import time
import hashlib
import requests
from typing import Optional, Dict, Any
from datetime import datetime
import threading
from collections import defaultdict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
import anthropic
from services.telegram_service import send_message, set_webhook, safe_send, send_photo
from services.qoder_client import send_message as qoder_send_message, QODER_URL
from services.image_service import generate_image
from services.orchestrator import orchestrator
from database import db
from models import WorkflowPreset, WorkflowRun, WorkflowRunStep

# Create API blueprint
api = Blueprint('api', __name__, url_prefix='/api/v1')

# Rate limiting storage (chat_id -> list of timestamps)
chat_rate_limits = defaultdict(list)

def check_rate_limit(chat_id: int, max_messages: int = 10, window_seconds: int = 10) -> bool:
    """Check if chat is within rate limit"""
    current_time = time.time()
    window_start = current_time - window_seconds
    
    # Clean old timestamps
    chat_rate_limits[chat_id] = [
        timestamp for timestamp in chat_rate_limits[chat_id]
        if timestamp > window_start
    ]
    
    # Check if within limit
    if len(chat_rate_limits[chat_id]) >= max_messages:
        return False
    
    # Record current message
    chat_rate_limits[chat_id].append(current_time)
    return True

def send_to_n8n_brain(chat_id: int, username: str, text: str, message_id: int, raw_update: dict) -> dict:
    """Send /run request to N8N webhook and handle response"""
    n8n_url = os.environ.get("N8N_WEBHOOK_URL")
    
    if not n8n_url:
        logging.warning("N8N_WEBHOOK_URL not set - brain is offline")
        return {"success": False, "error": "Brain offline - N8N_WEBHOOK_URL not set"}
    
    # Build JSON payload as specified
    payload = {
        "chat_id": chat_id,
        "username": username,
        "text": text,
        "raw_update": raw_update
    }
    
    start_time = time.time()
    
    try:
        logging.info(f"Sending /run request to N8N: chat_id={chat_id}, text={text[:50]}...")
        response = requests.post(
            n8n_url,
            json=payload,
            timeout=10,  # 10s timeout as specified
            headers={"Content-Type": "application/json"}
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        if response.status_code in [200, 201, 202]:
            logging.info(f"N8N brain responded in {duration_ms:.1f}ms with status {response.status_code}")
            
            try:
                response_data = response.json()
                return {
                    "success": True,
                    "reply_text": response_data.get("reply_text"),
                    "image_url": response_data.get("image_url"),
                    "duration_ms": duration_ms
                }
            except json.JSONDecodeError:
                logging.warning(f"N8N returned non-JSON response: {response.text[:200]}...")
                return {"success": False, "error": "Invalid JSON response from brain"}
                
        else:
            # Handle 4xx/5xx gracefully
            logging.warning(f"N8N brain returned {response.status_code} in {duration_ms:.1f}ms: {response.text[:200]}...")
            if response.status_code >= 500:
                return {"success": False, "error": "⚠️ Brain error, please try again"}
            elif response.status_code >= 400:
                return {"success": False, "error": "⚠️ Brain error, please try again"}
            else:
                return {"success": False, "error": "⚠️ Brain error, please try again"}
                
    except requests.Timeout:
        duration_ms = (time.time() - start_time) * 1000
        logging.warning(f"N8N brain request timed out after {duration_ms:.1f}ms")
        return {"success": False, "error": "⚠️ Brain error, please try again"}
        
    except requests.RequestException as e:
        duration_ms = (time.time() - start_time) * 1000
        logging.error(f"N8N brain request failed after {duration_ms:.1f}ms: {e}")
        return {"success": False, "error": "⚠️ Brain error, please try again"}

def handle_telegram_message(chat_id: int, username: str, text: str, message_id: int, raw_update: dict = None) -> Optional[str]:
    """Handle Telegram commands and return reply text"""
    text = text.strip()
    
    if text == "/start":
        return f"🤖 *Welcome to the Content Automation Brain!*\n\nYour chat ID: `{chat_id}`\n\nType `/help` to see available commands."
    
    elif text == "/help":
        return """🛠 *Available Commands:*

• `/start` - Welcome message + your chat ID
• `/help` - Show this help message  
• `/run <task>` - Send task to automation brain
• `/imagine <prompt>` - Generate image from prompt

*Examples:*
• `/run summarize the latest tech news`
• `/imagine cute robot holding coffee`"""
    
    elif text.startswith("/run "):
        task = text[5:].strip()  # Remove "/run " prefix
        if not task:
            return "❌ Please provide a task after `/run`\n\nExample: `/run summarize this article...`"
        
        # Send to N8N brain with raw update
        result = send_to_n8n_brain(chat_id, username, task, message_id, raw_update or {})
        
        if result["success"]:
            # Handle response from N8N
            reply_text = result.get("reply_text")
            image_url = result.get("image_url")
            
            # Send image if provided
            if image_url:
                photo_success = send_photo(str(chat_id), image_url)
                if not photo_success:
                    logging.warning(f"Failed to send image to chat {chat_id}: {image_url}")
            
            # Return reply text if provided, otherwise default success message
            if reply_text:
                return reply_text
            elif image_url:
                return None  # Image sent, no text reply needed
            else:
                return f"🧠 *Task processed:* {task[:100]}{'...' if len(task) > 100 else ''}\n\nCompleted successfully!"
        else:
            error_msg = result.get("error", "Unknown error")
            return f"❌ {error_msg}"
    
    elif text.startswith("/imagine "):
        prompt = text[9:].strip()  # Remove "/imagine " prefix
        if not prompt:
            return "❌ Please provide an image prompt after `/imagine`\n\nExample: `/imagine kawaii otter in a hoodie`"
        
        try:
            # Call our image generator API
            result = generate_image(prompt, style=None, size="1024x1024")
            
            if result.get('ok'):
                # Get the file URL and send it back
                file_url = result.get('file_url', '')
                if file_url.startswith('/'):
                    # Convert relative URL to absolute URL
                    base_url = "https://content-maestro-connorrohan01.replit.app"
                    file_url = f"{base_url}{file_url}"
                
                return f"🎨 *Generated image for:* {prompt}\n\n{file_url}"
            else:
                error_msg = result.get('details', result.get('error', 'Unknown error'))
                return f"❌ *Image generation failed:* {error_msg}"
                
        except Exception as e:
            logging.error(f"Image generation error: {e}")
            return "❌ *Image generation error*\n\nSomething went wrong. Please try again later."
    
    elif text.startswith("/"):
        return f"❓ *Unknown command:* `{text}`\n\nType `/help` to see available commands."
    
    # For non-command messages, send to brain  
    else:
        result = send_to_n8n_brain(chat_id, username, text, message_id, raw_update or {})
        
        if result["success"]:
            # Handle response from N8N
            reply_text = result.get("reply_text")
            image_url = result.get("image_url")
            
            # Send image if provided
            if image_url:
                photo_success = send_photo(str(chat_id), image_url)
                if not photo_success:
                    logging.warning(f"Failed to send image to chat {chat_id}: {image_url}")
            
            # Return reply text if provided
            return reply_text
        else:
            error_msg = result.get("error", "Unknown error")
            return f"❌ {error_msg}"

# Initialize background scheduler for async workflow execution
executors = {
    'default': ThreadPoolExecutor(10)  # Max 10 concurrent workflows
}
scheduler = BackgroundScheduler(executors=executors)
scheduler.start()

# Background job execution function
def execute_workflow_async(workflow_data, run_id, trace_id):
    """Execute a workflow asynchronously in background thread"""
    from app import app  # Import inside function to avoid circular import
    
    with app.app_context():
        try:
            # Get the run record
            workflow_run = WorkflowRun.query.filter_by(id=run_id).first()
            if not workflow_run:
                logging.error(f"Workflow run {run_id} not found during async execution")
                return
            
            actions = workflow_data.get('actions', [])
            context = workflow_data.get('metadata', {}).get('initial_context', {})
            
            start_time = time.time()
            results = []
            overall_success = True
            
            logging.info(f"brain.async.start: run_id={run_id}, trace_id={trace_id}, actions={len(actions)}")
            
            for action in actions:
                action_id = action['id']
                action_type = action['type']
                action_start = time.time()
                
                logging.info(f"brain.async.execute: action_id={action_id}, type={action_type}")
                
                # Create step record
                step = WorkflowRunStep(
                    run_id=workflow_run.id,
                    action_id=action_id,
                    action_type=action_type,
                    started_at=datetime.utcnow()
                )
                step.set_params_dict(action.get('params', {}))
                db.session.add(step)
                
                # Execute action
                result = orchestrator.dispatch(action, context)
                action_ms = (time.time() - action_start) * 1000
                
                # Update step record
                step.finished_at = datetime.utcnow()
                step.duration_ms = action_ms
                step.status = result.get("status", "unknown")
                step.set_output_dict(result.get("output", {}))
                if result.get("error"):
                    step.error_code = result["error"]
                    step.error_message = result.get("details", "")
                
                # Build result entry
                result_entry = {
                    "id": action_id,
                    "type": action_type,
                    "status": result.get("status", "unknown"),
                    "output": result.get("output", {}),
                    "ms": round(action_ms, 2)
                }
                
                # Add error information if present
                if result.get("error"):
                    result_entry["error"] = result["error"]
                if result.get("details"):
                    result_entry["details"] = result["details"]
                
                results.append(result_entry)
                
                # Add result to context for next actions
                context[action_id] = result
                
                # Check if we should continue on error
                if result.get("status") == "error":
                    overall_success = False
                    workflow_run.failed_actions += 1
                    continue_on_error = action.get("continue_on_error", False)
                    if not continue_on_error:
                        logging.warning(f"Stopping async execution at action {action_id} due to error: {result.get('error')}")
                        break
                else:
                    workflow_run.completed_actions += 1
                
                # Commit step
                db.session.commit()
                
                # Log completion
                status_emoji = "✅" if result.get("status") in ["ok", "mock"] else "❌"
                logging.info(f"brain.async.completed: {status_emoji} {action_id} ({action_type}) - {result.get('status')} in {action_ms:.1f}ms")
            
            # Finalize run
            total_ms = (time.time() - start_time) * 1000
            workflow_run.finished_at = datetime.utcnow()
            workflow_run.total_duration_ms = total_ms
            workflow_run.update_status()
            
            # Store final results
            response = {
                "ok": overall_success,
                "trace_id": trace_id,
                "results": results,
                "metadata": {
                    "total_actions": len(actions),
                    "completed_actions": workflow_run.completed_actions,
                    "failed_actions": workflow_run.failed_actions,
                    "total_ms": round(total_ms, 2)
                }
            }
            workflow_run.set_results_dict(response)
            db.session.commit()
            
            logging.info(f"brain.async.finished: run_id={run_id}, trace_id={trace_id}, success={overall_success}, actions={len(results)}/{len(actions)}, total_ms={total_ms:.1f}")
            
        except Exception as e:
            logging.error(f"Async workflow execution failed: {e}")
            if 'workflow_run' in locals():
                workflow_run.status = 'failed'
                workflow_run.error_message = str(e)
                workflow_run.finished_at = datetime.utcnow()
                db.session.commit()

def process_chatbot_message(user_id: str, message: str, context: Optional[dict] = None) -> dict:
    """Process a chatbot message and return the response"""
    if context is None:
        context = {}
    
    # If QODER_URL not set, return mock response
    if not QODER_URL:
        return {
            "ok": True,
            "reply": f"Qoder not connected yet, echo: {message}"
        }
    
    # Forward to Qoder service
    qoder_payload = {
        "user_id": user_id,
        "message": message,
        "context": context
    }
    
    result = qoder_send_message(qoder_payload)
    
    if result.get('ok'):
        return result.get('data', {})
    else:
        return result

def validate_json_request():
    """Validate that request contains valid JSON"""
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON"}), 400
        return data
    except Exception as e:
        return jsonify({"error": "Invalid JSON format"}), 400

@api.route('/image-generator', methods=['POST'])
def image_generator():
    """Production-ready image generator endpoint"""
    start_time = time.time()
    
    # Validate JSON request
    data = validate_json_request()
    if isinstance(data, tuple):  # Error response
        return data
    
    # Extract and validate required fields
    prompt = data.get('prompt', '').strip()
    style = data.get('style')
    size = data.get('size', '1024x1024')
    
    # Validate prompt
    if not prompt:
        return jsonify({
            "ok": False,
            "error": "prompt_required",
            "details": "prompt field is required and cannot be empty"
        }), 400
    
    # Validate size format
    if not re.match(r'^\d+x\d+$', size):
        return jsonify({
            "ok": False,
            "error": "invalid_size",
            "details": "size must be in format 'WIDTHxHEIGHT' (e.g., '1024x1024')"
        }), 400
    
    # Generate image
    try:
        result = generate_image(prompt, style, size)
        generation_ms = (time.time() - start_time) * 1000
        
        provider = os.environ.get("IMG_PROVIDER", "mock")
        
        if result.get('ok'):
            logging.info(f"Generated image successfully in {generation_ms:.2f}ms via {provider} provider")
            return jsonify({
                "ok": True,
                "file_url": result['file_url'],
                "meta": result['meta']
            }), 200
        else:
            logging.warning(f"Image generation failed after {generation_ms:.2f}ms: {result.get('error')}")
            return jsonify(result), 400
            
    except Exception as e:
        generation_ms = (time.time() - start_time) * 1000
        logging.error(f"Image generation error after {generation_ms:.2f}ms: {e}")
        return jsonify({
            "ok": False,
            "error": "internal_error",
            "details": "An unexpected error occurred during image generation"
        }), 500

@api.route('/reddit-scraper', methods=['POST'])
def reddit_scraper():
    """Reddit scraper endpoint"""
    data = validate_json_request()
    if isinstance(data, tuple):  # Error response
        return data
    
    return jsonify({
        "ok": True,
        "status": "ready",
        "echo": data
    }), 200

@api.route('/auto-poster', methods=['POST'])
def auto_poster():
    """Auto poster endpoint"""
    data = validate_json_request()
    if isinstance(data, tuple):  # Error response
        return data
    
    return jsonify({
        "ok": True,
        "status": "ready",
        "echo": data
    }), 200

@api.route('/vault-manager', methods=['POST'])
def vault_manager():
    """Vault manager endpoint"""
    data = validate_json_request()
    if isinstance(data, tuple):  # Error response
        return data
    
    return jsonify({
        "ok": True,
        "status": "ready",
        "echo": data
    }), 200

@api.route('/chatbot-engine', methods=['POST'])
def chatbot_engine():
    """Chatbot engine endpoint"""
    data = validate_json_request()
    if isinstance(data, tuple):  # Error response
        return data
    
    # Extract required fields
    user_id = data.get('user_id')
    message = data.get('message')
    context = data.get('context', {})
    
    # Validate required fields
    if not user_id or not message:
        return jsonify({"error": "user_id and message are required"}), 400
    
    # Process the message using the helper function
    result = process_chatbot_message(user_id, message, context)
    
    if result.get('ok'):
        return jsonify(result), 200
    else:
        return jsonify(result), 500

def handle_telegram_command(chat_id: str, text: str) -> str:
    """Handle Telegram bot commands"""
    text = text.strip()
    
    # /start command
    if text == '/start':
        return """🤖 *Welcome to the Workflow Orchestration Bot!*

I can help you manage and execute automated workflows. Here's what I can do:

• `/help` - Show this help message
• `/run <preset-name>` - Execute a saved workflow preset
• `/status <run-id>` - Check the status of a workflow run

*Available Presets:*
Use `/run` followed by a preset name to execute workflows instantly.

Get started by running `/help` for more details!"""

    # /help command
    elif text == '/help':
        return """📚 *Workflow Bot Help*

*Commands:*
• `/start` - Welcome message and overview
• `/help` - This help message  
• `/run <preset-name>` - Execute a workflow preset
• `/status <run-id>` - Check workflow execution status

*Examples:*
• `/run daily-content` - Run the "daily-content" preset
• `/status abc123-def456` - Check status of run abc123-def456

*Workflow Features:*
✅ Multi-step automation
✅ Error handling & recovery
✅ Real-time status tracking
✅ Context passing between steps
✅ 14+ action types (AI, images, social media, etc.)

For advanced features, use the web API at `/api/v1/brain`"""

    # /run command
    elif text.startswith('/run '):
        preset_name = text[5:].strip()  # Remove '/run ' prefix
        
        if not preset_name:
            return "❌ *Usage:* `/run <preset-name>`\n\nExample: `/run daily-content`"
        
        try:
            # Find preset
            preset = WorkflowPreset.query.filter_by(name=preset_name, is_active=True).first()
            
            if not preset:
                # List available presets
                presets = WorkflowPreset.query.filter_by(is_active=True).limit(10).all()
                if presets:
                    preset_list = '\n'.join([f"• `{p.name}` - {p.description or 'No description'}" for p in presets])
                    return f"❌ *Preset '{preset_name}' not found.*\n\n*Available presets:*\n{preset_list}"
                else:
                    return "❌ No workflow presets found. Create presets using the API at `/api/v1/workflows/presets`"
            
            # Execute preset asynchronously
            workflow = preset.get_workflow_dict()
            if not workflow.get('actions'):
                return f"❌ Preset '{preset_name}' has no actions to execute."
            
            # Generate trace ID
            import random
            trace_id = f"telegram_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # Create workflow run record
            workflow_run = WorkflowRun(
                preset_id=preset.id,
                trace_id=trace_id,
                status='running',
                total_actions=len(workflow['actions']),
                workflow_json=json.dumps(workflow),
                triggered_by='telegram',
                trigger_context=json.dumps({
                    'chat_id': chat_id,
                    'command': text,
                    'preset_name': preset_name
                })
            )
            db.session.add(workflow_run)
            db.session.commit()
            
            # Schedule async execution
            job_id = f"telegram_workflow_{workflow_run.id}"
            scheduler.add_job(
                execute_workflow_async,
                args=[workflow, workflow_run.id, trace_id],
                id=job_id,
                replace_existing=True
            )
            
            logging.info(f"Telegram triggered workflow: preset={preset_name}, run_id={workflow_run.id}, chat_id={chat_id}")
            
            return f"""🚀 *Workflow '{preset_name}' started!*

📋 *Details:*
• Run ID: `{workflow_run.id}`
• Actions: {len(workflow['actions'])}
• Status: Running

Use `/status {workflow_run.id}` to check progress.

⏱️ Estimated completion: {len(workflow['actions']) * 2} seconds"""

        except Exception as e:
            logging.error(f"Failed to run preset '{preset_name}' from Telegram: {e}")
            return f"❌ *Error running preset '{preset_name}':*\n\n{str(e)}"

    # /status command
    elif text.startswith('/status '):
        run_id = text[8:].strip()  # Remove '/status ' prefix
        
        if not run_id:
            return "❌ *Usage:* `/status <run-id>`\n\nExample: `/status abc123-def456`"
        
        try:
            # Find workflow run
            run = WorkflowRun.query.filter_by(id=run_id).first()
            
            if not run:
                return f"❌ *Workflow run '{run_id}' not found.*\n\nCheck your run ID and try again."
            
            # Format status response
            status_emoji = {
                'running': '🔄',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '⏹️'
            }.get(run.status, '❓')
            
            preset_info = f"\n📋 *Preset:* {run.preset.name}" if run.preset else ""
            
            progress = f"{run.completed_actions}/{run.total_actions}"
            duration_info = f"\n⏱️ *Duration:* {run.total_duration_ms/1000:.1f}s" if run.finished_at else ""
            
            result_msg = f"""🔍 *Workflow Status*

{status_emoji} *Status:* {run.status.title()}
🆔 *Run ID:* `{run.id}`
📊 *Progress:* {progress} actions{preset_info}
🕒 *Started:* {run.started_at.strftime('%H:%M:%S')}"""

            if run.finished_at:
                result_msg += f"\n🏁 *Finished:* {run.finished_at.strftime('%H:%M:%S')}"
                result_msg += duration_info
            
            if run.failed_actions > 0:
                result_msg += f"\n⚠️ *Failed Actions:* {run.failed_actions}"
            
            if run.error_message and run.status == 'failed':
                result_msg += f"\n❌ *Error:* {run.error_message[:100]}..."
            
            # Add recent steps info if running
            if run.status == 'running':
                recent_steps = WorkflowRunStep.query.filter_by(run_id=run_id)\
                                                   .order_by(WorkflowRunStep.started_at.desc())\
                                                   .limit(3).all()
                if recent_steps:
                    result_msg += "\n\n*Recent Steps:*"
                    for step in reversed(recent_steps):
                        status_icon = "✅" if step.status in ['ok', 'mock'] else "❌" if step.status == 'error' else "🔄"
                        result_msg += f"\n{status_icon} {step.action_type}"
            
            return result_msg

        except Exception as e:
            logging.error(f"Failed to get status for run '{run_id}': {e}")
            return f"❌ *Error getting status for run '{run_id}':*\n\n{str(e)}"

    # Unknown command
    else:
        if text.startswith('/'):
            return f"""❓ *Unknown command:* `{text}`

*Available commands:*
• `/start` - Welcome message
• `/help` - Show help
• `/run <preset-name>` - Run workflow preset
• `/status <run-id>` - Check workflow status

Type `/help` for more details."""
        else:
            # Non-command messages go to chatbot
            return None


@api.route('/hooks/telegram', methods=['POST'])
def telegram_hook():
    """Hardened Telegram webhook supporting all update shapes"""
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        # Log the full update for debugging
        logging.debug(f"Telegram update received: {json.dumps(data, default=str)[:500]}...")
        
        if not data:
            logging.info("Telegram webhook: empty payload, ignoring")
            return jsonify({"ok": True}), 200
        
        # Extract message object from various update types
        message_obj = None
        update_type = None
        
        # Check for different update types in priority order
        for key in ["message", "edited_message", "channel_post", "edited_channel_post", "callback_query"]:
            if key in data:
                update_type = key
                if key == "callback_query":
                    # For callback_query, the actual message is nested
                    message_obj = data[key].get('message')
                    if not message_obj:
                        logging.info("Telegram webhook: callback_query without message, ignoring")
                        return jsonify({"ok": True}), 200
                else:
                    message_obj = data[key]
                break
        
        if not message_obj:
            logging.info("Telegram webhook: no supported update type found, ignoring")
            return jsonify({"ok": True}), 200
        
        # Extract chat_id safely
        chat_id = None
        if update_type == "callback_query":
            # For callback_query: data.callback_query.message.chat.id
            chat_id = message_obj.get('chat', {}).get('id')
        else:
            # For other types: data.message.chat.id, data.edited_message.chat.id, etc.
            chat_id = message_obj.get('chat', {}).get('id')
        
        if not chat_id:
            logging.info(f"Telegram webhook: no chat.id in {update_type}, ignoring")
            return jsonify({"ok": True}), 200
        
        # Extract other fields
        message_id = message_obj.get('message_id', 0)
        username = message_obj.get('from', {}).get('username', 'unknown')
        
        # Get text content (from text, caption, or callback_query data)
        text = ''
        if update_type == "callback_query":
            # For callback queries, get the callback data
            text = data[update_type].get('data', '')
        else:
            # For other types, prefer text over caption
            text = message_obj.get('text') or message_obj.get('caption', '')
        
        if not text:
            logging.info(f"Telegram webhook: no text content in {update_type}, ignoring")
            return jsonify({"ok": True}), 200
        
        # Rate limiting: max 10 messages per 10 seconds per chat
        if not check_rate_limit(chat_id, max_messages=10, window_seconds=10):
            logging.warning(f"Rate limit exceeded for chat {chat_id}")
            safe_send(chat_id, "⚠️ Too many messages! Please slow down.")
            return jsonify({"ok": True}), 200
        
        # Log incoming message with update type and timing
        processing_time = (time.time() - start_time) * 1000
        logging.info(f"Telegram {update_type}: chat_id={chat_id}, username={username}, text={text[:100]}... (parsed in {processing_time:.1f}ms)")
        
        # Handle the command/message
        try:
            reply_text = handle_telegram_message(chat_id, username, text, message_id, data)
            
            if reply_text:
                success = safe_send(chat_id, reply_text)
                if not success:
                    logging.error(f"Failed to send reply to chat {chat_id}")
            
        except Exception as e:
            logging.error(f"Error handling {update_type} '{text[:50]}...': {e}")
            safe_send(chat_id, "❌ Something went wrong processing your message. Please try again.")
        
        total_time = (time.time() - start_time) * 1000
        logging.info(f"Telegram {update_type} completed in {total_time:.1f}ms")
        return jsonify({"ok": True}), 200
        
    except Exception as e:
        total_time = (time.time() - start_time) * 1000
        logging.error(f"Critical error in telegram webhook after {total_time:.1f}ms: {e}")
        return jsonify({"ok": True}), 200  # Always return 200 to avoid Telegram retries


@api.route('/hooks/telegram/test', methods=['GET'])
def telegram_test():
    """Send test message to specified chat_id"""
    chat_id = request.args.get('chat_id')
    
    if not chat_id:
        return jsonify({"error": "chat_id parameter required"}), 400
    
    try:
        chat_id = int(chat_id)
    except ValueError:
        return jsonify({"error": "chat_id must be integer"}), 400
    
    # Send test message
    success = safe_send(chat_id, "✅ Webhook test successful")
    
    if success:
        return jsonify({"sent": True, "chat_id": chat_id}), 200
    else:
        return jsonify({"error": "Failed to send message"}), 500

@api.route('/telegram/send', methods=['POST'])
def telegram_send():
    """Send a message via Telegram"""
    data = validate_json_request()
    if isinstance(data, tuple):  # Error response
        return data
    
    chat_id = data.get('chat_id')
    text = data.get('text')
    
    if not chat_id or not text:
        return jsonify({"error": "chat_id and text are required"}), 400
    
    result = send_message(str(chat_id), text)
    
    if result.get('ok'):
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@api.route('/telegram/set-webhook', methods=['POST'])
def telegram_set_webhook():
    """Set Telegram webhook URL"""
    data = validate_json_request()
    if isinstance(data, tuple):  # Error response
        return data
    
    base_url = data.get('base_url')
    
    if not base_url:
        return jsonify({"error": "base_url is required"}), 400
    
    result = set_webhook(base_url)
    
    if result.get('ok'):
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@api.route('/brain', methods=['POST'])
def brain():
    """Orchestration engine for executing action plans"""
    start_time = time.time()
    
    # Validate JSON request
    data = validate_json_request()
    if isinstance(data, tuple):  # Error response
        return data
    
    # Extract plan data
    actions = data.get("actions", [])
    metadata = data.get("metadata", {})
    trace_id = metadata.get("trace_id", f"trace_{int(time.time())}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}")
    
    # Validate actions list
    if not isinstance(actions, list) or len(actions) == 0:
        return jsonify({
            "ok": False,
            "error": "invalid_actions",
            "details": "actions must be a non-empty list"
        }), 400
    
    # Validate action schema
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            return jsonify({
                "ok": False,
                "error": "invalid_action_schema",
                "details": f"Action at index {i} must be an object"
            }), 400
        
        if "type" not in action:
            return jsonify({
                "ok": False,
                "error": "missing_action_type",
                "details": f"Action at index {i} must have a 'type' field"
            }), 400
        
        # Add default ID if missing
        if "id" not in action:
            action["id"] = f"action_{i}"
    
    # Execute actions in sequence
    results = []
    context = {}
    overall_success = True
    
    for i, action in enumerate(actions):
        action_id = action.get("id", f"action_{i}")
        action_type = action.get("type", "unknown")
        action_start = time.time()
        
        # Log action execution (without secrets)
        params_log = {k: v for k, v in action.get("params", {}).items() 
                     if not any(secret in k.lower() for secret in ['key', 'token', 'password', 'secret'])}
        logging.info(f"brain.execute: action_id={action_id}, type={action_type}, params={json.dumps(params_log)}")
        
        # Execute action
        result = orchestrator.dispatch(action, context)
        action_ms = (time.time() - action_start) * 1000
        
        # Build result entry
        result_entry = {
            "id": action_id,
            "type": action_type,
            "status": result.get("status", "unknown"),
            "output": result.get("output", {}),
            "ms": round(action_ms, 2)
        }
        
        # Add error information if present
        if result.get("error"):
            result_entry["error"] = result["error"]
        if result.get("details"):
            result_entry["details"] = result["details"]
        
        results.append(result_entry)
        
        # Add result to context for next actions
        context[action_id] = result
        
        # Check if we should continue on error
        if result.get("status") == "error":
            overall_success = False
            continue_on_error = action.get("continue_on_error", False)
            if not continue_on_error:
                logging.warning(f"Stopping execution at action {action_id} due to error: {result.get('error')}")
                break
        
        # Log completion
        status_emoji = "✅" if result.get("status") in ["ok", "mock"] else "❌"
        logging.info(f"brain.completed: {status_emoji} {action_id} ({action_type}) - {result.get('status')} in {action_ms:.1f}ms")
    
    # Calculate total execution time
    total_ms = (time.time() - start_time) * 1000
    
    # Build response
    response = {
        "ok": overall_success,
        "trace_id": trace_id,
        "results": results,
        "metadata": {
            "total_actions": len(actions),
            "completed_actions": len(results),
            "total_ms": round(total_ms, 2)
        }
    }
    
    # Log overall completion
    logging.info(f"brain.finished: trace_id={trace_id}, success={overall_success}, actions={len(results)}/{len(actions)}, total_ms={total_ms:.1f}")
    
    return jsonify(response), 200 if overall_success else 207  # 207 Multi-Status for partial success


@api.route('/brain/run', methods=['POST'])
def brain_async():
    """Execute workflows asynchronously - returns run_id immediately"""
    data = validate_json_request()
    if isinstance(data, tuple):  # Error response
        return data
    
    actions = data.get('actions', [])
    metadata = data.get('metadata', {})
    
    # Validate actions
    if not actions or not isinstance(actions, list):
        return jsonify({
            "ok": False,
            "error": "actions_required",
            "message": "At least one action is required"
        }), 400
    
    # Validate each action
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            return jsonify({
                "ok": False,
                "error": "invalid_action",
                "message": f"Action {i} must be an object"
            }), 400
        
        if not action.get('id') or not action.get('type'):
            return jsonify({
                "ok": False,
                "error": "invalid_action",
                "message": f"Action {i} must have 'id' and 'type' fields"
            }), 400
    
    try:
        # Generate IDs
        import random
        trace_id = metadata.get('trace_id') or f"async_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Create workflow run record
        workflow_run = WorkflowRun(
            trace_id=trace_id,
            status='running',
            total_actions=len(actions),
            workflow_json=json.dumps({
                'actions': actions,
                'metadata': metadata
            }),
            triggered_by='api_async',
            trigger_context=json.dumps({
                'endpoint': '/api/v1/brain/run',
                'initial_context': metadata.get('initial_context', {})
            })
        )
        db.session.add(workflow_run)
        db.session.commit()
        
        # Schedule async execution
        job_id = f"workflow_{workflow_run.id}"
        scheduler.add_job(
            execute_workflow_async,
            args=[{
                'actions': actions,
                'metadata': metadata
            }, workflow_run.id, trace_id],
            id=job_id,
            replace_existing=True
        )
        
        logging.info(f"Scheduled async workflow: run_id={workflow_run.id}, trace_id={trace_id}, actions={len(actions)}")
        
        return jsonify({
            "ok": True,
            "run_id": workflow_run.id,
            "trace_id": trace_id,
            "status": "scheduled",
            "message": f"Workflow scheduled for async execution with {len(actions)} actions",
            "status_url": f"/api/v1/workflows/runs/{workflow_run.id}",
            "metadata": {
                "total_actions": len(actions),
                "job_id": job_id
            }
        }), 202  # 202 Accepted
        
    except Exception as e:
        logging.error(f"Failed to schedule async workflow: {e}")
        return jsonify({
            "ok": False,
            "error": "scheduling_failed",
            "message": str(e)
        }), 500


# ============================================================================
# Workflow Presets Management Endpoints
# ============================================================================

@api.route('/workflows/presets', methods=['POST'])
def create_or_update_preset():
    """Create or update a workflow preset"""
    data = validate_json_request()
    if isinstance(data, tuple):  # Error response
        return data
    
    # Extract required fields
    name = data.get('name', '').strip()
    description = data.get('description', '')
    workflow = data.get('workflow', {})
    created_by = data.get('created_by', 'api')
    tags = data.get('tags', [])
    
    # Validate required fields
    if not name:
        return jsonify({
            "ok": False,
            "error": "name_required",
            "message": "Preset name is required"
        }), 400
    
    if not workflow or not isinstance(workflow, dict):
        return jsonify({
            "ok": False,
            "error": "workflow_required",
            "message": "Workflow object is required"
        }), 400
    
    # Validate workflow structure
    actions = workflow.get('actions', [])
    if not actions or not isinstance(actions, list):
        return jsonify({
            "ok": False,
            "error": "actions_required",
            "message": "Workflow must contain actions array"
        }), 400
    
    # Validate each action
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            return jsonify({
                "ok": False,
                "error": "invalid_action",
                "message": f"Action {i} must be an object"
            }), 400
        
        if not action.get('id') or not action.get('type'):
            return jsonify({
                "ok": False,
                "error": "invalid_action",
                "message": f"Action {i} must have 'id' and 'type' fields"
            }), 400
    
    try:
        # Check if preset exists
        existing_preset = WorkflowPreset.query.filter_by(name=name).first()
        
        if existing_preset:
            # Update existing preset
            existing_preset.description = description
            existing_preset.set_workflow_dict(workflow)
            existing_preset.created_by = created_by
            existing_preset.tags = ','.join(tags) if tags else ''
            existing_preset.updated_at = datetime.utcnow()
            preset = existing_preset
            created = False
        else:
            # Create new preset
            preset = WorkflowPreset(
                name=name,
                description=description,
                created_by=created_by,
                tags=','.join(tags) if tags else ''
            )
            preset.set_workflow_dict(workflow)
            db.session.add(preset)
            created = True
        
        db.session.commit()
        
        return jsonify({
            "ok": True,
            "created": created,
            "preset": preset.to_dict()
        }), 201 if created else 200
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to save preset: {e}")
        return jsonify({
            "ok": False,
            "error": "save_failed",
            "message": str(e)
        }), 500


@api.route('/workflows/presets', methods=['GET'])
def list_presets():
    """List all workflow presets"""
    try:
        # Query parameters
        active_only = request.args.get('active', 'true').lower() == 'true'
        tag_filter = request.args.get('tag', '').strip()
        limit = min(int(request.args.get('limit', 100)), 500)  # Max 500
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = WorkflowPreset.query
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        if tag_filter:
            query = query.filter(WorkflowPreset.tags.contains(tag_filter))
        
        # Order by updated_at descending
        query = query.order_by(WorkflowPreset.updated_at.desc())
        
        # Apply pagination
        total_count = query.count()
        presets = query.offset(offset).limit(limit).all()
        
        return jsonify({
            "ok": True,
            "presets": [preset.to_dict() for preset in presets],
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            }
        })
        
    except Exception as e:
        logging.error(f"Failed to list presets: {e}")
        return jsonify({
            "ok": False,
            "error": "query_failed",
            "message": str(e)
        }), 500


@api.route('/workflows/presets/<preset_name>', methods=['GET'])
def get_preset(preset_name):
    """Get a specific workflow preset by name"""
    try:
        preset = WorkflowPreset.query.filter_by(name=preset_name, is_active=True).first()
        
        if not preset:
            return jsonify({
                "ok": False,
                "error": "preset_not_found",
                "message": f"Preset '{preset_name}' not found"
            }), 404
        
        return jsonify({
            "ok": True,
            "preset": preset.to_dict()
        })
        
    except Exception as e:
        logging.error(f"Failed to get preset: {e}")
        return jsonify({
            "ok": False,
            "error": "query_failed",
            "message": str(e)
        }), 500


@api.route('/workflows/presets/<preset_name>', methods=['DELETE'])
def delete_preset(preset_name):
    """Soft delete a workflow preset (mark as inactive)"""
    try:
        preset = WorkflowPreset.query.filter_by(name=preset_name).first()
        
        if not preset:
            return jsonify({
                "ok": False,
                "error": "preset_not_found",
                "message": f"Preset '{preset_name}' not found"
            }), 404
        
        preset.is_active = False
        preset.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "ok": True,
            "message": f"Preset '{preset_name}' deleted"
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to delete preset: {e}")
        return jsonify({
            "ok": False,
            "error": "delete_failed",
            "message": str(e)
        }), 500


@api.route('/workflows/run-preset/<preset_name>', methods=['POST'])
def run_preset_immediately(preset_name):
    """Run a workflow preset immediately (synchronous execution)"""
    try:
        # Find preset
        preset = WorkflowPreset.query.filter_by(name=preset_name, is_active=True).first()
        
        if not preset:
            return jsonify({
                "ok": False,
                "error": "preset_not_found",
                "message": f"Preset '{preset_name}' not found"
            }), 404
        
        # Get workflow definition
        workflow = preset.get_workflow_dict()
        if not workflow.get('actions'):
            return jsonify({
                "ok": False,
                "error": "invalid_workflow",
                "message": "Preset workflow has no actions"
            }), 400
        
        # Get any overrides from request body
        data = request.get_json() or {}
        context_overrides = data.get('context', {})
        metadata_overrides = data.get('metadata', {})
        
        # Generate trace ID
        import random
        trace_id = f"preset_{int(time.time())}_{random.randint(10000, 99999)}"
        
        # Create workflow run record
        workflow_run = WorkflowRun(
            preset_id=preset.id,
            trace_id=trace_id,
            status='running',
            total_actions=len(workflow['actions']),
            workflow_json=json.dumps(workflow),
            triggered_by='api_preset',
            trigger_context=json.dumps({
                'preset_name': preset_name,
                'context_overrides': context_overrides,
                'metadata': metadata_overrides
            })
        )
        db.session.add(workflow_run)
        db.session.commit()
        
        # Execute workflow using existing brain logic
        start_time = time.time()
        context = context_overrides.copy()
        results = []
        overall_success = True
        
        logging.info(f"brain.start: preset={preset_name}, trace_id={trace_id}, actions={len(workflow['actions'])}")
        
        for action in workflow['actions']:
            action_id = action['id']
            action_type = action['type']
            action_start = time.time()
            
            logging.info(f"brain.execute: action_id={action_id}, type={action_type}, params={action.get('params', {})}")
            
            # Create step record
            step = WorkflowRunStep(
                run_id=workflow_run.id,
                action_id=action_id,
                action_type=action_type,
                started_at=datetime.utcnow()
            )
            step.set_params_dict(action.get('params', {}))
            db.session.add(step)
            
            # Execute action
            result = orchestrator.dispatch(action, context)
            action_ms = (time.time() - action_start) * 1000
            
            # Update step record
            step.finished_at = datetime.utcnow()
            step.duration_ms = action_ms
            step.status = result.get("status", "unknown")
            step.set_output_dict(result.get("output", {}))
            if result.get("error"):
                step.error_code = result["error"]
                step.error_message = result.get("details", "")
            
            # Build result entry
            result_entry = {
                "id": action_id,
                "type": action_type,
                "status": result.get("status", "unknown"),
                "output": result.get("output", {}),
                "ms": round(action_ms, 2)
            }
            
            # Add error information if present
            if result.get("error"):
                result_entry["error"] = result["error"]
            if result.get("details"):
                result_entry["details"] = result["details"]
            
            results.append(result_entry)
            
            # Add result to context for next actions
            context[action_id] = result
            
            # Check if we should continue on error
            if result.get("status") == "error":
                overall_success = False
                workflow_run.failed_actions += 1
                continue_on_error = action.get("continue_on_error", False)
                if not continue_on_error:
                    logging.warning(f"Stopping execution at action {action_id} due to error: {result.get('error')}")
                    break
            else:
                workflow_run.completed_actions += 1
            
            # Commit step
            db.session.commit()
            
            # Log completion
            status_emoji = "✅" if result.get("status") in ["ok", "mock"] else "❌"
            logging.info(f"brain.completed: {status_emoji} {action_id} ({action_type}) - {result.get('status')} in {action_ms:.1f}ms")
        
        # Calculate total execution time and finalize run
        total_ms = (time.time() - start_time) * 1000
        workflow_run.finished_at = datetime.utcnow()
        workflow_run.total_duration_ms = total_ms
        workflow_run.update_status()
        
        # Store final results
        response = {
            "ok": overall_success,
            "trace_id": trace_id,
            "preset_name": preset_name,
            "run_id": workflow_run.id,
            "results": results,
            "metadata": {
                "total_actions": len(workflow['actions']),
                "completed_actions": workflow_run.completed_actions,
                "failed_actions": workflow_run.failed_actions,
                "total_ms": round(total_ms, 2)
            }
        }
        workflow_run.set_results_dict(response)
        db.session.commit()
        
        # Log overall completion
        logging.info(f"brain.finished: preset={preset_name}, trace_id={trace_id}, success={overall_success}, actions={len(results)}/{len(workflow['actions'])}, total_ms={total_ms:.1f}")
        
        return jsonify(response), 200 if overall_success else 207
        
    except Exception as e:
        if 'workflow_run' in locals():
            workflow_run.status = 'failed'
            workflow_run.error_message = str(e)
            workflow_run.finished_at = datetime.utcnow()
            db.session.commit()
        
        logging.error(f"Failed to run preset: {e}")
        return jsonify({
            "ok": False,
            "error": "execution_failed",
            "message": str(e)
        }), 500


# ============================================================================
# Workflow Run Tracking Endpoints
# ============================================================================

@api.route('/workflows/runs', methods=['GET'])
def list_workflow_runs():
    """List recent workflow runs with pagination and filtering"""
    try:
        # Query parameters
        status_filter = request.args.get('status', '').strip()
        preset_filter = request.args.get('preset', '').strip()
        triggered_by_filter = request.args.get('triggered_by', '').strip()
        limit = min(int(request.args.get('limit', 50)), 200)  # Max 200
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = WorkflowRun.query
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        if preset_filter:
            # Join with WorkflowPreset to filter by preset name
            query = query.join(WorkflowPreset, WorkflowRun.preset_id == WorkflowPreset.id)\
                        .filter(WorkflowPreset.name == preset_filter)
        
        if triggered_by_filter:
            query = query.filter_by(triggered_by=triggered_by_filter)
        
        # Order by started_at descending
        query = query.order_by(WorkflowRun.started_at.desc())
        
        # Apply pagination
        total_count = query.count()
        runs = query.offset(offset).limit(limit).all()
        
        # Convert to dict format
        runs_data = []
        for run in runs:
            run_dict = run.to_dict(include_steps=False)
            # Add preset name if available
            if run.preset:
                run_dict['preset_name'] = run.preset.name
            runs_data.append(run_dict)
        
        return jsonify({
            "ok": True,
            "runs": runs_data,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            },
            "filters": {
                "status": status_filter or None,
                "preset": preset_filter or None,
                "triggered_by": triggered_by_filter or None
            }
        })
        
    except Exception as e:
        logging.error(f"Failed to list workflow runs: {e}")
        return jsonify({
            "ok": False,
            "error": "query_failed",
            "message": str(e)
        }), 500


@api.route('/workflows/runs/<run_id>', methods=['GET'])
def get_workflow_run(run_id):
    """Get detailed information about a specific workflow run including steps"""
    try:
        include_steps = request.args.get('steps', 'true').lower() == 'true'
        
        # Find the run
        run = WorkflowRun.query.filter_by(id=run_id).first()
        
        if not run:
            return jsonify({
                "ok": False,
                "error": "run_not_found",
                "message": f"Workflow run '{run_id}' not found"
            }), 404
        
        # Convert to dict with or without steps
        run_dict = run.to_dict(include_steps=include_steps)
        
        # Add preset information if available
        if run.preset:
            run_dict['preset_name'] = run.preset.name
            run_dict['preset_description'] = run.preset.description
        
        return jsonify({
            "ok": True,
            "run": run_dict
        })
        
    except Exception as e:
        logging.error(f"Failed to get workflow run: {e}")
        return jsonify({
            "ok": False,
            "error": "query_failed",
            "message": str(e)
        }), 500


@api.route('/workflows/runs/<run_id>/steps', methods=['GET'])
def get_workflow_run_steps(run_id):
    """Get detailed step information for a workflow run"""
    try:
        # Find the run
        run = WorkflowRun.query.filter_by(id=run_id).first()
        
        if not run:
            return jsonify({
                "ok": False,
                "error": "run_not_found",
                "message": f"Workflow run '{run_id}' not found"
            }), 404
        
        # Get steps ordered by started_at
        steps = WorkflowRunStep.query.filter_by(run_id=run_id)\
                                   .order_by(WorkflowRunStep.started_at.asc()).all()
        
        return jsonify({
            "ok": True,
            "run_id": run_id,
            "trace_id": run.trace_id,
            "steps": [step.to_dict() for step in steps],
            "summary": {
                "total_steps": len(steps),
                "completed_steps": sum(1 for step in steps if step.status in ['ok', 'mock']),
                "failed_steps": sum(1 for step in steps if step.status == 'error'),
                "total_duration_ms": sum(step.duration_ms or 0 for step in steps)
            }
        })
        
    except Exception as e:
        logging.error(f"Failed to get workflow run steps: {e}")
        return jsonify({
            "ok": False,
            "error": "query_failed",
            "message": str(e)
        }), 500


@api.route('/workflows/runs/<run_id>/cancel', methods=['POST'])
def cancel_workflow_run(run_id):
    """Cancel a running workflow (mark as cancelled)"""
    try:
        run = WorkflowRun.query.filter_by(id=run_id).first()
        
        if not run:
            return jsonify({
                "ok": False,
                "error": "run_not_found",
                "message": f"Workflow run '{run_id}' not found"
            }), 404
        
        if run.status != 'running':
            return jsonify({
                "ok": False,
                "error": "cannot_cancel",
                "message": f"Cannot cancel run with status '{run.status}'"
            }), 400
        
        # Update status to cancelled
        run.status = 'cancelled'
        run.finished_at = datetime.utcnow()
        if not run.error_message:
            run.error_message = "Cancelled by user request"
        
        db.session.commit()
        
        logging.info(f"Cancelled workflow run: {run_id}")
        
        return jsonify({
            "ok": True,
            "message": f"Workflow run '{run_id}' cancelled",
            "run": run.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to cancel workflow run: {e}")
        return jsonify({
            "ok": False,
            "error": "cancel_failed",
            "message": str(e)
        }), 500


@api.route('/health', methods=['GET'])
def health():
    return {"ok": True}


@api.route('/build', methods=['POST'])
def build():
    # shared-token check
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {os.getenv('REPLIT_SHARED_TOKEN')}":
        return jsonify({"status":"error","error":{"message":"unauthorized"}}), 401

    data = request.get_json(force=True) or {}
    name = data.get("name","")
    spec = data.get("spec","")

    # Stub workflow body
    return jsonify({
        "status": "ok",
        "result_type": "json",
        "result_payload": {
            "workflow_body": {
                "name": name or "Generated Workflow",
                "settings": {"timezone": "UTC"},
                "nodes": [],
                "connections": {}
            }
        }
    })