"""
LLM Service using Ollama for agentic video editing.

This module provides LLM capabilities using local Ollama models,
specifically optimized for qwen2.5:1.5b-instruct-q4_K_M.
"""

import json
import requests
from typing import Any, Dict, List, Optional, Generator
from datetime import datetime


class OllamaClient:
    """Client for interacting with Ollama LLM service."""
    
    def __init__(self, model: str = "qwen2.5:1.5b-instruct-q4_K_M", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.session = requests.Session()
        
    def check_health(self) -> bool:
        """Check if Ollama service is running."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> List[str]:
        """List available models."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except Exception:
            pass
        return []
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User prompt
            system: System prompt
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dictionary with response content and metadata
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120,
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                return {"stream": True, "response": response.iter_lines()}
            
            data = response.json()
            return {
                "success": True,
                "content": data.get("response", ""),
                "done": data.get("done", False),
                "total_duration": data.get("total_duration", 0),
                "load_duration": data.get("load_duration", 0),
                "prompt_eval_count": data.get("prompt_eval_count", 0),
                "eval_count": data.get("eval_count", 0),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """
        Chat with the LLM using message history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dictionary with response content and metadata
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                return {"stream": True, "response": response.iter_lines()}
            
            data = response.json()
            message = data.get("message", {})
            return {
                "success": True,
                "content": message.get("content", ""),
                "role": message.get("role", "assistant"),
                "done": data.get("done", False),
                "total_duration": data.get("total_duration", 0),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


class LLMService:
    """
    High-level LLM service for agentic video editing.
    
    Provides structured interfaces for:
    - Understanding user intents
    - Planning tool sequences
    - Extracting parameters from natural language
    """
    
    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()
        self.system_prompt = """You are an expert video editing assistant. 
Your role is to understand user requests and help them edit videos using available tools.

Available tools:
1. video_split - Split long videos into segments with speed-up and background music
2. silence_removal - Remove silent portions from video using speech detection  
3. speed_adjust - Change video playback speed (fast forward or slow motion)
4. vertical_crop - Convert landscape video to 9:16 vertical format for Shorts/Reels
5. audio_mix - Add background music to video
6. transcription - Convert speech to text for captions/subtitles

When users describe what they want to do, identify:
1. Which tool(s) to use
2. Required parameters (video path, audio path, output settings, etc.)
3. Any special preferences or constraints

Always respond in a helpful, clear manner. If you need more information, ask clarifying questions."""

    def understand_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze user input to understand their intent.
        
        Returns structured intent with detected tools and parameters.
        """
        prompt = f"""Analyze this video editing request and extract structured information:

User request: "{user_input}"

Respond ONLY with valid JSON in this exact format:
{{
    "intent": "brief description of what user wants",
    "tools_needed": ["tool_name1", "tool_name2"],
    "parameters": {{
        "video_path": "path or null if not provided",
        "audio_path": "path or null if not provided",
        "output_dir": "path or null if not provided",
        "preferences": {{}}
    }},
    "missing_info": ["list of required info not provided"],
    "confidence": 0.0-1.0
}}

If the request is unclear or not about video editing, set confidence low and explain in intent."""

        response = self.client.generate(prompt, system=self.system_prompt)
        
        if not response.get("success"):
            return {
                "success": False,
                "error": response.get("error"),
                "intent": "Could not understand request"
            }
        
        try:
            # Extract JSON from response
            content = response["content"]
            # Try to find JSON in the response
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                parsed = json.loads(json_str)
                return {"success": True, **parsed}
            else:
                return {
                    "success": False,
                    "intent": response["content"],
                    "confidence": 0.3
                }
        except json.JSONDecodeError:
            return {
                "success": False,
                "intent": response["content"],
                "confidence": 0.3
            }
    
    def plan_workflow(self, intent: Dict[str, Any], available_tools: List[str]) -> Dict[str, Any]:
        """
        Create a workflow plan based on detected intent.
        
        Returns ordered sequence of tool calls with parameters.
        """
        prompt = f"""Create a step-by-step workflow plan for this video editing intent:

Intent: {intent.get('intent', '')}
Tools needed: {intent.get('tools_needed', [])}
Available tools: {available_tools}
Known parameters: {json.dumps(intent.get('parameters', {}), indent=2)}

Respond ONLY with valid JSON in this exact format:
{{
    "steps": [
        {{
            "step_number": 1,
            "tool": "tool_name",
            "description": "what this step does",
            "parameters": {{}},
            "depends_on": [] 
        }}
    ],
    "estimated_steps": 0,
    "warnings": ["any warnings or considerations"]
}}

Order steps logically. If a step depends on output from a previous step, note it in depends_on."""

        response = self.client.generate(prompt, system=self.system_prompt)
        
        if not response.get("success"):
            return {"success": False, "error": response.get("error")}
        
        try:
            content = response["content"]
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                return {"success": True, **json.loads(json_str)}
            return {"success": False, "plan": response["content"]}
        except json.JSONDecodeError:
            return {"success": False, "plan": response["content"]}
    
    def chat(self, messages: List[Dict[str, str]], stream: bool = False) -> Dict[str, Any]:
        """
        Chat with the LLM using conversation history.
        
        Args:
            messages: List of {role, content} dicts
            stream: Whether to stream response
            
        Returns:
            Response dict with content
        """
        # Add system prompt if not present
        has_system = any(m.get("role") == "system" for m in messages)
        if not has_system:
            messages = [{"role": "system", "content": self.system_prompt}] + messages
        
        return self.client.chat(messages, stream=stream)


# Singleton instance
_llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    """Get or create the LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
