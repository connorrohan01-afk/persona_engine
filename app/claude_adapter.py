"""
Claude AI Adapter for PersonaEngine
Handles Claude API calls with system prompt injection and persona context
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from app.vault_context import build_brain_context, build_upsell_context


# =================== Configuration ===================

PROMPTS_DIR = Path("prompts")
BRAIN_SYSTEM_PROMPT = PROMPTS_DIR / "brain_system.txt"
UPSELL_SYSTEM_PROMPT = PROMPTS_DIR / "upsell_system.txt"


# =================== Prompt Loading ===================

def load_system_prompt(prompt_file: Path) -> str:
    """
    Load system prompt from file.
    
    Args:
        prompt_file: Path to prompt template file
        
    Returns:
        System prompt content
    """
    try:
        if prompt_file.exists():
            return prompt_file.read_text().strip()
        else:
            return "You are a helpful AI assistant."
    except Exception:
        return "You are a helpful AI assistant."


def inject_persona_context(prompt: str, persona_context: str, job_context: str = "") -> str:
    """
    Inject persona and job context into system prompt.
    
    Args:
        prompt: Base system prompt
        persona_context: Persona context string
        job_context: Job context string
        
    Returns:
        Enhanced prompt with context
    """
    if not persona_context and not job_context:
        return prompt
        
    context_lines = []
    
    if persona_context:
        context_lines.append(f"PERSONA CONTEXT: {persona_context}")
        
    if job_context:
        context_lines.append(f"JOB CONTEXT: {job_context}")
        
    context_block = "\n".join(context_lines)
    
    # Inject context before the main prompt
    return f"{context_block}\n\n{prompt}"


# =================== Brain AI Functions ===================

async def call_brain_ai(question: str, persona_id: Optional[str] = None, job_id: Optional[str] = None, mode: str = "fake") -> Dict[str, Any]:
    """
    Call Claude AI for brain queries with context injection.
    
    Args:
        question: User question
        persona_id: Optional persona context
        job_id: Optional job context 
        mode: Processing mode (live/fake)
        
    Returns:
        AI response data
    """
    if mode == "fake":
        return _fake_brain_response(question, persona_id, job_id)
        
    # Load context
    context = build_brain_context(persona_id, job_id)
    
    # Load and enhance system prompt
    base_prompt = load_system_prompt(BRAIN_SYSTEM_PROMPT)
    enhanced_prompt = inject_persona_context(
        base_prompt,
        context.get('persona_context', ''),
        context.get('job_context', '')
    )
    
    # Call Claude API
    try:
        # In production, this would make an actual Claude API call
        # For now, return enhanced fake response with context
        return {
            "answer": f"[LIVE MODE] Based on the context provided, {question[:50]}... (Claude response would go here)",
            "tokens_used": 150,
            "persona_context": context.get('persona_context'),
            "job_context": context.get('job_context')
        }
        
    except Exception as e:
        # Fallback to fake response on error
        return _fake_brain_response(question, persona_id, job_id, error=str(e))


def _fake_brain_response(question: str, persona_id: Optional[str] = None, job_id: Optional[str] = None, error: Optional[str] = None) -> Dict[str, Any]:
    """Generate fake brain response for testing."""
    context = build_brain_context(persona_id, job_id)
    
    if error:
        answer = f"[FAKE MODE - ERROR] Unable to process '{question[:30]}...' due to: {error}"
    else:
        # Build contextual fake response
        context_parts = []
        if context.get('persona_context'):
            context_parts.append(f"persona ({persona_id})")
        if context.get('job_context'):
            context_parts.append(f"job ({job_id})")
            
        context_suffix = f" with {', '.join(context_parts)}" if context_parts else ""
        
        answer = f"[FAKE MODE] This is a simulated brain response to: '{question}'{context_suffix}. " \
                f"In live mode, this would be processed by Claude AI with full context awareness " \
                f"and generate a thoughtful, personalized response based on the provided information."
    
    return {
        "answer": answer,
        "tokens_used": None,
        "persona_context": context.get('persona_context'),
        "job_context": context.get('job_context')
    }


# =================== Upsell AI Functions ===================

async def call_upsell_ai(user_id: str, persona_id: Optional[str] = None, job_id: Optional[str] = None, 
                        style: str = "studio", intent: str = "prints", mode: str = "fake") -> Dict[str, Any]:
    """
    Call Claude AI for upsell suggestions with context injection.
    
    Args:
        user_id: User identifier
        persona_id: Optional persona context
        job_id: Optional job context
        style: Style preference
        intent: Intent category
        mode: Processing mode (live/fake)
        
    Returns:
        Upsell suggestions data
    """
    if mode == "fake":
        return _fake_upsell_response(user_id, persona_id, job_id, style, intent)
        
    # Load rich context
    context = build_upsell_context(persona_id, job_id)
    
    # Load and enhance system prompt
    base_prompt = load_system_prompt(UPSELL_SYSTEM_PROMPT)
    enhanced_prompt = inject_persona_context(
        base_prompt,
        context.get('persona_summary', ''),
        context.get('job_summary', '')
    )
    
    # Build context for AI
    ai_context = {
        "user_id": user_id,
        "style": style,
        "intent": intent,
        "persona": context.get('persona_data'),
        "job": context.get('job_data'),
        "images_available": context.get('images_count', 0)
    }
    
    # Call Claude API
    try:
        # In production, this would make an actual Claude API call
        # For now, return enhanced fake response with context
        return {
            "suggestions": [
                {
                    "title": f"[LIVE MODE] Premium {style.title()} Package",
                    "description": f"Enhanced {intent} package tailored for your style preferences",
                    "price_range": "$200-500",
                    "confidence": 0.85
                }
            ],
            "context": context,
            "tokens_used": 200
        }
        
    except Exception as e:
        # Fallback to fake response on error
        return _fake_upsell_response(user_id, persona_id, job_id, style, intent, error=str(e))


def _fake_upsell_response(user_id: str, persona_id: Optional[str] = None, job_id: Optional[str] = None, 
                         style: str = "studio", intent: str = "prints", error: Optional[str] = None) -> Dict[str, Any]:
    """Generate fake upsell response for testing."""
    context = build_upsell_context(persona_id, job_id)
    
    if error:
        suggestions = [
            {
                "title": f"[FAKE MODE - ERROR] {style.title()} Package",
                "description": f"Unable to generate suggestions due to: {error}",
                "price_range": "$0",
                "confidence": 0.0
            }
        ]
    else:
        # Build contextual fake suggestions
        context_info = []
        if persona_id:
            context_info.append(f"persona {persona_id}")
        if job_id:
            context_info.append(f"job {job_id}")
            
        context_suffix = f" ({', '.join(context_info)})" if context_info else ""
        
        suggestions = [
            {
                "title": f"Premium {style.title()} Collection{context_suffix}",
                "description": f"Enhanced {intent} package with professional editing and delivery. "
                              f"Tailored for your specific style preferences and project context.",
                "price_range": "$150-300",
                "confidence": 0.92
            },
            {
                "title": f"Extended {intent.title()} License",
                "description": f"Commercial usage rights for your {style} style images. "
                              f"Perfect for business applications and marketing materials.",
                "price_range": "$75-150", 
                "confidence": 0.78
            },
            {
                "title": f"Rush Delivery Service",
                "description": f"Expedited processing and delivery within 24 hours. "
                              f"Get your {style} style {intent} ready for immediate use.",
                "price_range": "$50-100",
                "confidence": 0.65
            }
        ]
    
    return {
        "suggestions": suggestions,
        "context": context,
        "tokens_used": None
    }


# =================== Configuration Helpers ===================

def get_ai_config() -> Dict[str, Any]:
    """
    Get AI configuration and status.
    
    Returns:
        Configuration data
    """
    return {
        "brain_prompt_exists": BRAIN_SYSTEM_PROMPT.exists(),
        "upsell_prompt_exists": UPSELL_SYSTEM_PROMPT.exists(),
        "prompts_dir": str(PROMPTS_DIR),
        "claude_api_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        "mode_llm": os.getenv("MODE", "fake")
    }