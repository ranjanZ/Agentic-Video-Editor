"""
Video Editing Agent - AI agent for video editing tasks.

This agent understands natural language requests and orchestrates
video editing tools to accomplish user goals.
"""

import json
from typing import Any, Dict, List, Optional
from .base_agent import BaseAgent, AgentConfig, AgentMessage, AgentState


class VideoEditingAgent(BaseAgent):
    """
    AI agent specialized in video editing tasks.
    
    This agent can:
    - Understand natural language video editing requests
    - Plan sequences of tool invocations
    - Execute edits and report results
    - Handle multi-step workflows
    """
    
    def __init__(self, config: Optional[AgentConfig] = None, tools: Optional[Dict] = None):
        super().__init__(config or AgentConfig(name="video_editor"))
        
        # Register available tools
        if tools:
            for name, tool in tools.items():
                self.register_tool(name, tool)
        
        self._system_prompt = """You are an expert video editing assistant. 
You have access to the following tools:
- video_split: Split video into segments with speed-up and background music
- silence_removal: Remove silent portions from video using speech detection
- transcription: Convert speech to text
- speed_adjust: Change video playback speed
- vertical_crop: Convert video to 9:16 vertical format
- audio_mix: Add background music to video

Analyze user requests and determine which tools to use. Always explain your plan before executing."""
    
    @property
    def name(self) -> str:
        return "video_editing_agent"
    
    @property
    def description(self) -> str:
        return (
            "AI-powered video editing agent that understands natural language requests "
            "and orchestrates video processing tools to create edited videos."
        )
    
    def process(self, user_input: str) -> AgentMessage:
        """
        Process a user's natural language request.
        
        Args:
            user_input: User's request in natural language
            
        Returns:
            AgentMessage with response or action plan
        """
        self._update_state(AgentState.THINKING)
        self.add_message("user", user_input)
        self._current_iteration += 1
        
        # Simple rule-based planning (can be enhanced with LLM)
        plan = self._create_plan(user_input)
        
        if not plan:
            self._update_state(AgentState.WAITING_INPUT)
            return AgentMessage(
                role="assistant",
                content="I understand you want to edit a video. Could you provide more details about:\n"
                        "- The input video path\n"
                        "- What kind of edits you want (split, remove silence, add music, etc.)\n"
                        "- Any specific preferences (duration, output format, etc.)"
            )
        
        self._update_state(AgentState.EXECUTING)
        
        if self.config.require_confirmation:
            plan_description = self._describe_plan(plan)
            self._update_state(AgentState.WAITING_INPUT)
            return AgentMessage(
                role="assistant",
                content=f"I plan to do the following:\n{plan_description}\n\nShall I proceed?"
            )
        
        # Execute the plan
        result = self.execute_plan(plan)
        
        if result.get("success"):
            self._update_state(AgentState.COMPLETE)
            return AgentMessage(
                role="assistant",
                content=result.get("message", "Video editing completed successfully!"),
                metadata={"result": result}
            )
        else:
            self._update_state(AgentState.ERROR)
            return AgentMessage(
                role="assistant",
                content=f"Error during video editing: {result.get('error', 'Unknown error')}",
                metadata={"result": result}
            )
    
    def execute_plan(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a planned sequence of tool calls.
        
        Args:
            plan: List of tool call specifications
            
        Returns:
            Results of the execution
        """
        results = []
        current_input = None
        
        for step in plan:
            tool_name = step.get("tool")
            params = step.get("params", {})
            
            # Update input path if previous step produced output
            if current_input and "video_path" in params:
                params["video_path"] = current_input
            if current_input and "input_path" in params:
                params["input_path"] = current_input
            
            tool = self._tools.get(tool_name)
            if not tool:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' not found",
                    "results": results
                }
            
            try:
                result = tool.execute(**params)
                results.append({
                    "tool": tool_name,
                    "result": result.to_dict()
                })
                
                if not result.success:
                    return {
                        "success": False,
                        "error": result.error,
                        "results": results
                    }
                
                # Chain outputs to next step
                if result.output_path:
                    current_input = result.output_path
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "results": results
                }
        
        final_output = current_input
        return {
            "success": True,
            "message": f"Completed {len(plan)} step(s). Final output: {final_output}",
            "output_path": final_output,
            "results": results
        }
    
    def _create_plan(self, user_input: str) -> Optional[List[Dict[str, Any]]]:
        """
        Create a plan based on user input.
        
        This is a simple rule-based implementation. In production,
        this would use an LLM to understand intent and generate plans.
        """
        import re
        user_input_lower = user_input.lower()
        
        # Detect intent keywords
        wants_split = any(word in user_input_lower for word in ["split", "segments", "shorts", "reels"])
        wants_silence_removal = any(word in user_input_lower for word in ["silence", "pause", "cut silent"])
        wants_vertical = any(word in user_input_lower for word in ["vertical", "portrait", "9:16", "shorts"])
        wants_transcription = any(word in user_input_lower for word in ["transcribe", "text", "caption", "subtitle"])
        wants_speed = any(word in user_input_lower for word in ["speed", "fast", "slow", "time-lapse"])
        wants_music = any(word in user_input_lower for word in ["music", "background", "audio mix"])
        
        if not any([wants_split, wants_silence_removal, wants_vertical, wants_transcription, wants_speed, wants_music]):
            return None
        
        # Extract file paths from user input
        video_path = None
        audio_path = None
        output_dir = "./output"
        
        # Match file paths with extensions
        path_pattern = r'(/[^\s"\']+|[\w./\\]+\.(mp4|avi|mov|mkv|mp3|wav|ogg|flac))'
        paths = re.findall(path_pattern, user_input, re.IGNORECASE)
        
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        audio_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.aac'}
        
        for path_match in paths:
            path = path_match[0] if isinstance(path_match, tuple) else path_match
            lower_path = path.lower()
            
            if any(lower_path.endswith(ext) for ext in video_extensions):
                if not video_path:
                    video_path = path
            elif any(lower_path.endswith(ext) for ext in audio_extensions):
                if not audio_path:
                    audio_path = path
        
        # If we don't have required paths, return None to prompt for more info
        if wants_split and (not video_path or not audio_path):
            return None
        
        plan = []
        
        # Build plan based on detected intents
        if wants_transcription:
            plan.append({
                "tool": "transcription",
                "params": {"input_path": video_path or "{{video_path}}"}
            })
        
        if wants_silence_removal:
            plan.append({
                "tool": "silence_removal",
                "params": {
                    "video_path": video_path or "{{video_path}}",
                    "output_path": "{{temp_output}}_no_silence.mp4"
                }
            })
        
        if wants_vertical:
            plan.append({
                "tool": "vertical_crop",
                "params": {
                    "video_path": video_path or "{{video_path}}",
                    "output_path": "{{temp_output}}_vertical.mp4"
                }
            })
        
        if wants_speed and not wants_split:
            plan.append({
                "tool": "speed_adjust",
                "params": {
                    "video_path": video_path or "{{video_path}}",
                    "output_path": "{{temp_output}}_sped.mp4",
                    "speed_factor": 2.0
                }
            })
        
        if wants_split:
            plan.append({
                "tool": "video_split",
                "params": {
                    "video_path": video_path or "{{video_path}}",
                    "audio_path": audio_path or "{{audio_path}}",
                    "output_dir": output_dir
                }
            })
        
        if wants_music and not wants_split:
            plan.append({
                "tool": "audio_mix",
                "params": {
                    "video_path": video_path or "{{video_path}}",
                    "audio_path": audio_path or "{{audio_path}}",
                    "output_path": "{{temp_output}}_with_music.mp4"
                }
            })
        
        return plan if plan else None
    
    def _describe_plan(self, plan: List[Dict[str, Any]]) -> str:
        """Generate human-readable description of the plan."""
        descriptions = []
        for i, step in enumerate(plan, 1):
            tool = step.get("tool", "unknown")
            descriptions.append(f"{i}. {tool}")
        return "\n".join(descriptions)
