"""Manus - Task queue management system with worker loop."""

import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify

# Import SDK runner
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from sdk import runner


app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "manus-secret-key")

# Configuration
QUEUE_FILE = Path("manus/queue.json")
LOGS_DIR = Path("logs")
MISSION_FILE = Path("MISSION.md")
BUDGETS_FILE = Path("budgets.json")
METRICS_FILE = Path("manus/metrics.json")
APPROVALS_FILE = Path("manus/approvals.json")

# Global state
worker_thread = None
worker_running = False
budgets_paused = False


def read_mission() -> Optional[str]:
    """Read MISSION.md if present."""
    if MISSION_FILE.exists():
        with open(MISSION_FILE, 'r') as f:
            return f.read()
    return None


def load_budgets() -> Dict[str, Any]:
    """Load budgets from budgets.json."""
    if not BUDGETS_FILE.exists():
        return {
            "daily_usd_cap": 10.0,
            "max_concurrency": 5,
            "token_cost_per_1k": 0.003,
            "alert_threshold": 0.8
        }
    
    try:
        with open(BUDGETS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load budgets: {e}")
        return {
            "daily_usd_cap": 10.0,
            "max_concurrency": 5,
            "token_cost_per_1k": 0.003,
            "alert_threshold": 0.8
        }


def load_metrics() -> Dict[str, Any]:
    """Load metrics from metrics.json."""
    if not METRICS_FILE.exists():
        return {
            "tokens_today": 0,
            "usd_spent_today": 0.0,
            "last_reset": datetime.utcnow().strftime("%Y-%m-%d"),
            "job_times": [],
            "job_results": []
        }
    
    try:
        with open(METRICS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load metrics: {e}")
        return {
            "tokens_today": 0,
            "usd_spent_today": 0.0,
            "last_reset": datetime.utcnow().strftime("%Y-%m-%d"),
            "job_times": [],
            "job_results": []
        }


def save_metrics(metrics: Dict[str, Any]) -> None:
    """Save metrics to metrics.json."""
    try:
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, 'w') as f:
            json.dump(metrics, f, indent=2)
    except Exception as e:
        print(f"ERROR: Failed to save metrics: {e}")


def reset_daily_metrics_if_needed(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Reset daily metrics if it's a new day."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    if metrics.get("last_reset") != today:
        metrics["tokens_today"] = 0
        metrics["usd_spent_today"] = 0.0
        metrics["last_reset"] = today
        # Keep job_times and job_results for 24h rolling window
        save_metrics(metrics)
    
    return metrics


def update_metrics(tokens: int, duration: float, success: bool) -> None:
    """Update metrics with job results."""
    metrics = load_metrics()
    metrics = reset_daily_metrics_if_needed(metrics)
    
    # Update token count
    metrics["tokens_today"] += tokens
    
    # Calculate USD spent
    budgets = load_budgets()
    token_cost = (tokens / 1000.0) * budgets.get("token_cost_per_1k", 0.003)
    metrics["usd_spent_today"] += token_cost
    
    # Add job time (keep last 1000 for p95 calculation)
    if "job_times" not in metrics:
        metrics["job_times"] = []
    metrics["job_times"].append({
        "duration": duration,
        "timestamp": datetime.utcnow().isoformat()
    })
    metrics["job_times"] = metrics["job_times"][-1000:]
    
    # Add job result (keep last 1000 for pass rate)
    if "job_results" not in metrics:
        metrics["job_results"] = []
    metrics["job_results"].append({
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    })
    metrics["job_results"] = metrics["job_results"][-1000:]
    
    save_metrics(metrics)


def calculate_p95_job_time() -> float:
    """Calculate 95th percentile job time."""
    metrics = load_metrics()
    job_times = metrics.get("job_times", [])
    
    if not job_times:
        return 0.0
    
    # Filter to last 24 hours
    cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_times = [
        jt["duration"] for jt in job_times
        if datetime.fromisoformat(jt["timestamp"]) > cutoff
    ]
    
    if not recent_times:
        return 0.0
    
    sorted_times = sorted(recent_times)
    p95_index = int(len(sorted_times) * 0.95)
    return sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]


def calculate_pass_rate_24h() -> float:
    """Calculate pass rate for last 24 hours."""
    metrics = load_metrics()
    job_results = metrics.get("job_results", [])
    
    if not job_results:
        return 100.0
    
    # Filter to last 24 hours
    cutoff = datetime.utcnow() - timedelta(hours=24)
    recent_results = [
        jr["success"] for jr in job_results
        if datetime.fromisoformat(jr["timestamp"]) > cutoff
    ]
    
    if not recent_results:
        return 100.0
    
    success_count = sum(1 for r in recent_results if r)
    return (success_count / len(recent_results)) * 100.0


def load_approvals() -> Dict[str, Any]:
    """Load approvals from approvals.json."""
    if not APPROVALS_FILE.exists():
        return {
            "pending": [],
            "approved": [],
            "rejected": []
        }
    
    try:
        with open(APPROVALS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load approvals: {e}")
        return {
            "pending": [],
            "approved": [],
            "rejected": []
        }


def save_approvals(approvals: Dict[str, Any]) -> None:
    """Save approvals to approvals.json."""
    try:
        APPROVALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(APPROVALS_FILE, 'w') as f:
            json.dump(approvals, f, indent=2)
    except Exception as e:
        print(f"ERROR: Failed to save approvals: {e}")


def requires_approval(task: Dict[str, Any]) -> bool:
    """Check if a task requires approval (touches protected files)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from sdk.runner import is_protected_path
    
    task_type = task.get("type")
    
    # Only claude.patch touches files
    if task_type == "claude.patch":
        file_path = task.get("file_path", "")
        if file_path and is_protected_path(file_path):
            return True
    
    return False


def check_budget_limits() -> Dict[str, Any]:
    """Check if budget limits are exceeded."""
    global budgets_paused
    
    budgets = load_budgets()
    metrics = load_metrics()
    metrics = reset_daily_metrics_if_needed(metrics)
    
    daily_cap = budgets.get("daily_usd_cap", 10.0)
    usd_spent = metrics.get("usd_spent_today", 0.0)
    
    # Check if daily cap exceeded
    if usd_spent >= daily_cap:
        budgets_paused = True
        return {
            "paused": True,
            "reason": "daily_usd_cap_exceeded",
            "usd_spent": usd_spent,
            "daily_cap": daily_cap
        }
    
    # Check if approaching limit
    alert_threshold = budgets.get("alert_threshold", 0.8)
    if usd_spent >= (daily_cap * alert_threshold):
        return {
            "paused": False,
            "warning": True,
            "reason": "approaching_daily_cap",
            "usd_spent": usd_spent,
            "daily_cap": daily_cap,
            "percentage": (usd_spent / daily_cap) * 100
        }
    
    budgets_paused = False
    return {
        "paused": False,
        "warning": False,
        "usd_spent": usd_spent,
        "daily_cap": daily_cap
    }


def load_queue() -> List[Dict[str, Any]]:
    """Load tasks from queue.json."""
    if not QUEUE_FILE.exists():
        return []
    
    try:
        with open(QUEUE_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"ERROR: Failed to load queue: {e}")
        return []


def save_queue(queue: List[Dict[str, Any]]) -> None:
    """Save tasks to queue.json."""
    try:
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(QUEUE_FILE, 'w') as f:
            json.dump(queue, f, indent=2)
    except Exception as e:
        print(f"ERROR: Failed to save queue: {e}")


def save_result(task_id: str, result: Dict[str, Any]) -> str:
    """Save task result to logs directory."""
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        log_file = LOGS_DIR / f"task_{task_id}_{timestamp}.json"
        
        with open(log_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        return str(log_file)
    except Exception as e:
        print(f"ERROR: Failed to save result: {e}")
        return ""


def worker_loop():
    """Worker loop that processes tasks from the queue."""
    global worker_running
    
    print("INFO: Worker loop started")
    
    while worker_running:
        try:
            # Load queue
            queue = load_queue()
            
            if not queue:
                # No tasks, sleep and continue
                time.sleep(1)
                continue
            
            # Pop first task
            task = queue.pop(0)
            task_id = task.get("id", "unknown")
            
            print(f"INFO: Processing task {task_id}: {task.get('type')}")
            
            # Save updated queue (task removed)
            save_queue(queue)
            
            # Execute task using SDK runner
            start_time = time.time()
            result = runner.execute(task)
            duration = time.time() - start_time
            
            # Extract token usage if available
            tokens_used = 0
            if "usage" in result:
                tokens_used = result["usage"].get("input_tokens", 0) + result["usage"].get("output_tokens", 0)
            
            # Update metrics
            success = result.get("ok", False)
            update_metrics(tokens_used, duration, success)
            
            # Add metadata to result
            result["task_id"] = task_id
            result["duration_seconds"] = round(duration, 3)
            result["completed_at"] = datetime.utcnow().isoformat() + "Z"
            result["original_task"] = task
            result["tokens_used"] = tokens_used
            
            # Save result to logs
            log_file = save_result(task_id, result)
            
            if result.get("ok"):
                print(f"INFO: Task {task_id} completed successfully in {duration:.2f}s ({tokens_used} tokens) -> {log_file}")
            else:
                print(f"ERROR: Task {task_id} failed: {result.get('error')} -> {log_file}")
            
        except Exception as e:
            print(f"ERROR: Worker loop error: {e}")
            time.sleep(1)
    
    print("INFO: Worker loop stopped")


@app.route("/enqueue", methods=["POST"])
def enqueue_task():
    """
    Enqueue a new task to the queue.
    
    POST /enqueue
    Body: {
        "type": "claude.plan" | "claude.patch" | "deploy.test",
        "id": "optional-task-id",
        ... task-specific parameters
    }
    """
    try:
        # Check budget limits first
        budget_status = check_budget_limits()
        
        if budget_status.get("paused"):
            return jsonify({
                "ok": False,
                "error": "enqueue_paused",
                "reason": budget_status.get("reason"),
                "message": f"Enqueue paused: {budget_status.get('reason')}",
                "usd_spent": budget_status.get("usd_spent"),
                "daily_cap": budget_status.get("daily_cap")
            }), 429  # Too Many Requests
        
        task = request.get_json()
        
        if not task:
            return jsonify({"ok": False, "error": "No task data provided"}), 400
        
        if "type" not in task:
            return jsonify({"ok": False, "error": "Task type is required"}), 400
        
        # Check max concurrency
        budgets = load_budgets()
        queue = load_queue()
        max_concurrency = budgets.get("max_concurrency", 5)
        
        if len(queue) >= max_concurrency:
            return jsonify({
                "ok": False,
                "error": "max_concurrency_exceeded",
                "message": f"Queue is full (max {max_concurrency} tasks)",
                "current_queue_length": len(queue),
                "max_concurrency": max_concurrency
            }), 429
        
        # Generate task ID if not provided
        if "id" not in task:
            task["id"] = f"task_{int(time.time() * 1000)}"
        
        # Add timestamp
        task["enqueued_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Check if task requires approval
        if requires_approval(task):
            # Add to pending approvals instead of queue
            approvals = load_approvals()
            approvals["pending"].append(task)
            save_approvals(approvals)
            
            print(f"INFO: Task {task['id']} pending approval: {task['type']} -> {task.get('file_path')}")
            
            return jsonify({
                "ok": True,
                "task_id": task["id"],
                "status": "pending_approval",
                "message": f"Task requires approval (protected file: {task.get('file_path')})",
                "approval_required": True
            })
        
        # Add task to queue
        queue.append(task)
        
        # Save queue
        save_queue(queue)
        
        print(f"INFO: Task {task['id']} enqueued: {task['type']}")
        
        response = {
            "ok": True,
            "task_id": task["id"],
            "queue_position": len(queue),
            "message": "Task enqueued successfully"
        }
        
        # Add warning if approaching budget
        if budget_status.get("warning"):
            response["warning"] = {
                "message": "Approaching daily budget cap",
                "usd_spent": budget_status.get("usd_spent"),
                "daily_cap": budget_status.get("daily_cap"),
                "percentage": budget_status.get("percentage")
            }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/queue", methods=["GET"])
def get_queue():
    """Get current queue status."""
    try:
        queue = load_queue()
        
        return jsonify({
            "ok": True,
            "queue_length": len(queue),
            "tasks": queue,
            "worker_running": worker_running
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/logs", methods=["GET"])
def list_logs():
    """List all log files."""
    try:
        if not LOGS_DIR.exists():
            return jsonify({"ok": True, "logs": []})
        
        log_files = []
        for log_file in sorted(LOGS_DIR.glob("*.json"), reverse=True):
            log_files.append({
                "filename": log_file.name,
                "path": str(log_file),
                "size": log_file.stat().st_size,
                "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            })
        
        return jsonify({
            "ok": True,
            "count": len(log_files),
            "logs": log_files[:50]  # Return latest 50
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/logs/<filename>", methods=["GET"])
def get_log(filename):
    """Get specific log file content."""
    try:
        log_file = LOGS_DIR / filename
        
        if not log_file.exists():
            return jsonify({"ok": False, "error": "Log file not found"}), 404
        
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        return jsonify({
            "ok": True,
            "filename": filename,
            "data": log_data
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/mission", methods=["GET"])
def get_mission():
    """Get MISSION.md content if present."""
    try:
        mission = read_mission()
        
        if mission:
            return jsonify({
                "ok": True,
                "mission": mission,
                "file": str(MISSION_FILE)
            })
        else:
            return jsonify({
                "ok": True,
                "mission": None,
                "message": "No MISSION.md file found"
            })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/status", methods=["GET"])
def get_status():
    """Get Manus system status."""
    try:
        queue = load_queue()
        approvals = load_approvals()
        
        # Count log files
        log_count = len(list(LOGS_DIR.glob("*.json"))) if LOGS_DIR.exists() else 0
        
        # Check mission
        has_mission = MISSION_FILE.exists()
        
        return jsonify({
            "ok": True,
            "worker_running": worker_running,
            "queue_length": len(queue),
            "pending_approvals": len(approvals.get("pending", [])),
            "logs_count": log_count,
            "has_mission": has_mission,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """
    Health endpoint with metrics and budget enforcement.
    
    Returns:
        - queue_depth: Number of tasks in queue
        - pass_rate_24h: Percentage of successful tasks in last 24 hours
        - p95_job_time: 95th percentile job execution time
        - tokens_today: Total tokens used today
        - budgets: Budget configuration and current status
    """
    try:
        queue = load_queue()
        metrics = load_metrics()
        metrics = reset_daily_metrics_if_needed(metrics)
        budgets = load_budgets()
        budget_status = check_budget_limits()
        
        # Calculate metrics
        queue_depth = len(queue)
        pass_rate_24h = calculate_pass_rate_24h()
        p95_job_time = calculate_p95_job_time()
        tokens_today = metrics.get("tokens_today", 0)
        usd_spent_today = metrics.get("usd_spent_today", 0.0)
        
        return jsonify({
            "ok": True,
            "queue_depth": queue_depth,
            "pass_rate_24h": round(pass_rate_24h, 2),
            "p95_job_time": round(p95_job_time, 3),
            "tokens_today": tokens_today,
            "usd_spent_today": round(usd_spent_today, 4),
            "budgets": {
                "daily_usd_cap": budgets.get("daily_usd_cap", 10.0),
                "max_concurrency": budgets.get("max_concurrency", 5),
                "token_cost_per_1k": budgets.get("token_cost_per_1k", 0.003),
                "paused": budget_status.get("paused", False),
                "pause_reason": budget_status.get("reason") if budget_status.get("paused") else None,
                "warning": budget_status.get("warning", False),
                "budget_used_percentage": round((usd_spent_today / budgets.get("daily_usd_cap", 10.0)) * 100, 2)
            },
            "worker_running": worker_running,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/worker/start", methods=["POST"])
def start_worker():
    """Start the worker loop."""
    global worker_thread, worker_running
    
    if worker_running:
        return jsonify({
            "ok": False,
            "message": "Worker is already running"
        })
    
    worker_running = True
    worker_thread = threading.Thread(target=worker_loop, daemon=True)
    worker_thread.start()
    
    return jsonify({
        "ok": True,
        "message": "Worker started successfully"
    })


@app.route("/worker/stop", methods=["POST"])
def stop_worker():
    """Stop the worker loop."""
    global worker_running
    
    if not worker_running:
        return jsonify({
            "ok": False,
            "message": "Worker is not running"
        })
    
    worker_running = False
    
    return jsonify({
        "ok": True,
        "message": "Worker stop signal sent"
    })


@app.route("/", methods=["GET"])
def index():
    """Root endpoint with system info."""
    mission = read_mission()
    
    return jsonify({
        "service": "Manus Task Queue System",
        "version": "1.0.0",
        "mission": mission[:200] + "..." if mission and len(mission) > 200 else mission,
        "endpoints": {
            "enqueue": "POST /enqueue - Add task to queue",
            "queue": "GET /queue - View current queue",
            "logs": "GET /logs - List log files",
            "mission": "GET /mission - View MISSION.md",
            "status": "GET /status - System status",
            "worker_start": "POST /worker/start - Start worker",
            "worker_stop": "POST /worker/stop - Stop worker"
        }
    })


if __name__ == "__main__":
    # Auto-start worker on launch
    worker_running = True
    worker_thread = threading.Thread(target=worker_loop, daemon=True)
    worker_thread.start()
    
    print("🚀 Manus Task Queue System")
    print("📋 Mission:", "loaded" if read_mission() else "not found")
    print("⚙️  Worker: started")
    print("🌐 Listening on port 5001")
    
    app.run(host="0.0.0.0", port=5001, debug=False)


@app.route("/approvals", methods=["GET"])
def get_approvals():
    """Get all pending approvals."""
    try:
        approvals = load_approvals()
        
        return jsonify({
            "ok": True,
            "pending": approvals.get("pending", []),
            "approved": approvals.get("approved", [])[-10:],  # Last 10
            "rejected": approvals.get("rejected", [])[-10:],  # Last 10
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/approve/<task_id>", methods=["POST"])
def approve_task(task_id: str):
    """Approve a pending task and add to queue."""
    try:
        approvals = load_approvals()
        pending = approvals.get("pending", [])
        
        # Find task
        task = None
        for i, t in enumerate(pending):
            if t.get("id") == task_id:
                task = pending.pop(i)
                break
        
        if not task:
            return jsonify({
                "ok": False,
                "error": "Task not found in pending approvals"
            }), 404
        
        # Add approval flag
        task["requires_approval"] = True
        task["approved_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Move to approved list
        if "approved" not in approvals:
            approvals["approved"] = []
        approvals["approved"].append({
            "task_id": task_id,
            "approved_at": task["approved_at"],
            "task_type": task.get("type"),
            "file_path": task.get("file_path")
        })
        
        # Save approvals
        save_approvals(approvals)
        
        # Add to queue
        queue = load_queue()
        queue.append(task)
        save_queue(queue)
        
        print(f"INFO: Task {task_id} approved and enqueued")
        
        return jsonify({
            "ok": True,
            "task_id": task_id,
            "message": "Task approved and enqueued",
            "queue_position": len(queue)
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/reject/<task_id>", methods=["POST"])
def reject_task(task_id: str):
    """Reject a pending task."""
    try:
        approvals = load_approvals()
        pending = approvals.get("pending", [])
        
        # Find task
        task = None
        for i, t in enumerate(pending):
            if t.get("id") == task_id:
                task = pending.pop(i)
                break
        
        if not task:
            return jsonify({
                "ok": False,
                "error": "Task not found in pending approvals"
            }), 404
        
        # Move to rejected list
        if "rejected" not in approvals:
            approvals["rejected"] = []
        approvals["rejected"].append({
            "task_id": task_id,
            "rejected_at": datetime.utcnow().isoformat() + "Z",
            "task_type": task.get("type"),
            "file_path": task.get("file_path"),
            "task": task
        })
        
        # Save approvals
        save_approvals(approvals)
        
        print(f"INFO: Task {task_id} rejected")
        
        return jsonify({
            "ok": True,
            "task_id": task_id,
            "message": "Task rejected"
        })
        
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
