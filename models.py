from datetime import datetime
from database import db
from sqlalchemy import func
import json
import uuid


class ContentTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    template_text = db.Column(db.Text, nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ContentTemplate {self.name}>'


class GeneratedContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('content_template.id'))
    status = db.Column(db.String(20), default='draft')  # draft, scheduled, published, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_for = db.Column(db.DateTime)
    published_at = db.Column(db.DateTime)
    
    template = db.relationship('ContentTemplate', backref='generated_contents')
    
    def __repr__(self):
        return f'<GeneratedContent {self.title}>'


class PlatformConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    platform_name = db.Column(db.String(50), nullable=False)
    is_connected = db.Column(db.Boolean, default=False)
    connection_details = db.Column(db.Text)  # JSON string for storing connection info
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<PlatformConnection {self.platform_name}>'


class PostAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('generated_content.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    shares = db.Column(db.Integer, default=0)
    comments = db.Column(db.Integer, default=0)
    engagement_rate = db.Column(db.Float, default=0.0)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    content = db.relationship('GeneratedContent', backref='analytics')
    
    def __repr__(self):
        return f'<PostAnalytics for content {self.content_id}>'


class WorkflowPreset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    workflow_json = db.Column(db.Text, nullable=False)  # JSON string of actions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))  # Optional user identifier
    is_active = db.Column(db.Boolean, default=True)
    tags = db.Column(db.String(500))  # Comma-separated tags
    
    # Relationship to runs
    runs = db.relationship('WorkflowRun', backref='preset', lazy=True, cascade='all, delete-orphan')
    
    def get_workflow_dict(self):
        """Parse workflow JSON into Python dict"""
        try:
            return json.loads(self.workflow_json)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_workflow_dict(self, workflow_dict):
        """Convert Python dict to JSON string"""
        self.workflow_json = json.dumps(workflow_dict, indent=2)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'workflow': self.get_workflow_dict(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'tags': self.tags.split(',') if self.tags else []
        }
    
    def __repr__(self):
        return f'<WorkflowPreset {self.name}>'


class WorkflowRun(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    preset_id = db.Column(db.Integer, db.ForeignKey('workflow_preset.id'), nullable=True)
    trace_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='running')  # running, completed, failed, cancelled
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    total_actions = db.Column(db.Integer, default=0)
    completed_actions = db.Column(db.Integer, default=0)
    failed_actions = db.Column(db.Integer, default=0)
    total_duration_ms = db.Column(db.Float, default=0.0)
    workflow_json = db.Column(db.Text)  # Snapshot of executed workflow
    results_json = db.Column(db.Text)  # Final results as JSON
    error_message = db.Column(db.Text)
    triggered_by = db.Column(db.String(100))  # 'api', 'telegram', 'schedule', etc.
    trigger_context = db.Column(db.Text)  # JSON context from trigger source
    
    # Relationship to steps
    steps = db.relationship('WorkflowRunStep', backref='run', lazy=True, cascade='all, delete-orphan')
    
    def get_workflow_dict(self):
        """Parse workflow JSON into Python dict"""
        try:
            return json.loads(self.workflow_json) if self.workflow_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def get_results_dict(self):
        """Parse results JSON into Python dict"""
        try:
            return json.loads(self.results_json) if self.results_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def get_trigger_context_dict(self):
        """Parse trigger context JSON into Python dict"""
        try:
            return json.loads(self.trigger_context) if self.trigger_context else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_results_dict(self, results_dict):
        """Convert results dict to JSON string"""
        self.results_json = json.dumps(results_dict)
    
    def update_status(self):
        """Update status based on step results"""
        if self.failed_actions > 0:
            self.status = 'failed'
        elif self.completed_actions == self.total_actions:
            self.status = 'completed'
        else:
            self.status = 'running'
    
    def to_dict(self, include_steps=False):
        result = {
            'id': self.id,
            'preset_id': self.preset_id,
            'trace_id': self.trace_id,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'total_actions': self.total_actions,
            'completed_actions': self.completed_actions,
            'failed_actions': self.failed_actions,
            'total_duration_ms': self.total_duration_ms,
            'workflow': self.get_workflow_dict(),
            'results': self.get_results_dict(),
            'error_message': self.error_message,
            'triggered_by': self.triggered_by,
            'trigger_context': self.get_trigger_context_dict()
        }
        
        if include_steps:
            result['steps'] = [step.to_dict() for step in self.steps]
        
        return result
    
    def __repr__(self):
        return f'<WorkflowRun {self.trace_id}>'


class WorkflowRunStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(36), db.ForeignKey('workflow_run.id'), nullable=False)
    action_id = db.Column(db.String(100), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # ok, error, mock
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    duration_ms = db.Column(db.Float, default=0.0)
    input_hash = db.Column(db.String(64))  # Hash of input parameters for caching
    params_json = db.Column(db.Text)  # Input parameters as JSON
    output_json = db.Column(db.Text)  # Output/result as JSON
    error_code = db.Column(db.String(50))
    error_message = db.Column(db.Text)
    
    def get_params_dict(self):
        """Parse params JSON into Python dict"""
        try:
            return json.loads(self.params_json) if self.params_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def get_output_dict(self):
        """Parse output JSON into Python dict"""
        try:
            return json.loads(self.output_json) if self.output_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_params_dict(self, params_dict):
        """Convert params dict to JSON string"""
        self.params_json = json.dumps(params_dict)
    
    def set_output_dict(self, output_dict):
        """Convert output dict to JSON string"""
        self.output_json = json.dumps(output_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'action_id': self.action_id,
            'action_type': self.action_type,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'duration_ms': self.duration_ms,
            'input_hash': self.input_hash,
            'params': self.get_params_dict(),
            'output': self.get_output_dict(),
            'error_code': self.error_code,
            'error_message': self.error_message
        }
    
    def __repr__(self):
        return f'<WorkflowRunStep {self.action_id}>'
