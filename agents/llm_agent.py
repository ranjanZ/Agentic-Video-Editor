"""
LLM-powered Agent using Ollama for video editing.

This agent uses qwen2.5:1.5b-instruct-q4_K_M via Ollama to understand
user requests and orchestrate video editing tools.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from agents.base_agent import BaseAgent, AgentConfig, AgentMessage, AgentState
from llm.ollama_service import get_llm_service, LLMService
from mcp.server import get_mcp_server


class LLMAgent(BaseAgent):
    """
    LLM-powered video editing agent using Ollama.
    
    This agent:
    1. Uses qwen2.5:1.5b-instruct-q4_K_M for understanding requests
    2. Plans tool sequences using MCP-compatible tool definitions
    3. Executes tools and reports results with output paths
    4. Supports streaming responses for real-time feedback
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        super().__init__(config or AgentConfig(name="llm_video_editor"))
        
        self.llm_service = get_llm_service()
        self.mcp_server = get_mcp_server()
        
        # Get available tools from MCP server
        mcp_tools = self.mcp_server.list_tools()
        self._tool_definitions = mcp_tools
        self._tool_names = [t["name"] for t in mcp_tools]
        
        self._system_prompt = f"""You are an expert video editing assistant powered by AI.
You have access to these video editing tools: {', '.join(self._tool_names)}

Tool descriptions:
{json.dumps(self._tool_definitions, indent=2)}

When users ask for video editing:
1. Identify which tool(s) they need
2. Extract parameters from their request
3. If information is missing (like video path), ask for it
4. Execute tools in logical order
5. Report results clearly with output file paths

Always be helpful and concise. If you execute a tool, report the output_path so the user can find their edited video."""

    @property
    def name(self) -> str:
        return "llm_agent"
    
    @property
    def description(self) -> str:
        return "LLM-powered video editing agent using Ollama (qwen2.5:1.5b)"
    
    def process(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AgentMessage:
        """
        Process user request using LLM.
        
        Args:
            user_input: User's natural language request
            context: Optional context (conversation history, file paths, etc.)
            
        Returns:
            AgentMessage with response
        """
        self._update_state(AgentState.THINKING)
        self.add_message("user", user_input)
        self._current_iteration += 1
        
        context = context or {}
        tool_config = context.get("tool_config", {})
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        # Add context if provided
        if context:
            context_str = json.dumps(context, indent=2)
            messages.append({"role": "system", "content": f"Context: {context_str}"})
        
        # Handle simple transport/orientation commands without requiring Ollama.
        direct_calls = self._direct_tool_calls(user_input, context)
        if direct_calls:
            return self._execute_tool_calls(direct_calls, user_input, context, tool_config)

        # Get LLM response
        response = self.llm_service.chat(messages)
        
        if not response.get("success"):
            fallback_calls = self._fallback_tool_calls(user_input, context)
            if fallback_calls:
                return self._execute_tool_calls(fallback_calls, user_input, context, tool_config)
            self._update_state(AgentState.ERROR)
            return AgentMessage(role="assistant", content=f"Error: Could not process request - {response.get('error', 'Unknown error')}")
        
        llm_response = response["content"]
        
        # Try to parse tool calls from LLM response (check both parsed and direct tool_calls)
        tool_calls = response.get("tool_calls", [])
        if not tool_calls:
            tool_calls = self._parse_tool_calls(llm_response)
        
        if tool_calls:
            self._update_state(AgentState.EXECUTING)
            results = []
            
            for call in tool_calls:
                tool_name = call.get("tool")
                params = call.get("params", {})
                
                # Extract additional params from user input text
                extracted_params = self._extract_params_from_text(user_input, tool_name)
                params.update(extracted_params)
                
                # The editor context is authoritative. LLMs often invent stale demo paths.
                if context.get("video_path") and tool_name not in {"audio_mix", "transcription"}:
                    params["video_path"] = context["video_path"]
                if context.get("audio_path") and tool_name in {"audio_mix", "video_split", "transcription"}:
                    if tool_name == "transcription":
                        params["input_path"] = context["audio_path"]
                    else:
                        params["audio_path"] = context["audio_path"]
                if context.get("output_dir"):
                    params["output_dir"] = context["output_dir"]

                if tool_name == "silence_removal" and context.get("video_path"):
                    params["video_path"] = context["video_path"]
                if tool_name == "transcription" and context.get("video_path") and not context.get("audio_path"):
                    params["input_path"] = context["video_path"]

                # Resolve template values emitted by the model before calling a tool.
                for key in ("video_path", "input_path", "audio_path"):
                    if isinstance(params.get(key), str) and params[key].startswith("{{"):
                        fallback = context.get(key)
                        if key == "input_path":
                            fallback = context.get("audio_path") or context.get("video_path")
                        if fallback:
                            params[key] = fallback
                if isinstance(params.get("output_path"), str) and params["output_path"].startswith("{{"):
                    params.pop("output_path")

                # UI tool settings are authoritative for configurable operations.
                if tool_name == "silence_removal":
                    silence_config = tool_config.get("silence", {})
                    if silence_config.get("modelSize"):
                        params["model_size"] = silence_config["modelSize"]
                    if silence_config.get("paddingMs") is not None:
                        params["padding_ms"] = silence_config["paddingMs"]
                elif tool_name == "vertical_crop":
                    vertical_config = tool_config.get("vertical", {})
                    for key, config_key in (("width", "width"), ("height", "height"), ("fps", "fps")):
                        if vertical_config.get(config_key) is not None:
                            params[key] = vertical_config[config_key]
                elif tool_name == "transcription":
                    transcription_config = tool_config.get("transcribe", {})
                    if transcription_config.get("modelSize"):
                        params["model_size"] = transcription_config["modelSize"]
                    if transcription_config.get("language"):
                        params["language"] = transcription_config["language"]
                    if transcription_config.get("task"):
                        params["task"] = transcription_config["task"]
                    if transcription_config.get("wordTimestamps") is not None:
                        params["word_timestamps"] = transcription_config["wordTimestamps"]

                # Video tools need a concrete destination, not just a directory.
                if tool_name in {"vertical_crop", "silence_removal", "speed_adjust", "audio_mix"}:
                    if not params.get("output_path"):
                        import os
                        source = params.get("video_path") or params.get("input_path") or context.get("video_path") or "edited_video.mp4"
                        stem = os.path.splitext(os.path.basename(source))[0]
                        suffix = "_vertical_9x16" if tool_name == "vertical_crop" else f"_{tool_name}"
                        output_dir = params.get("output_dir") or "data/output"
                        params["output_path"] = os.path.join(output_dir, f"{stem}{suffix}.mp4")
                
                if tool_name == "speed_adjust":
                    params.setdefault("speed_factor", 1.0)

                # Validate required parameters for video_split tool
                if tool_name == "video_split":
                    missing_required = []
                    if not params.get("video_path"):
                        missing_required.append("video_path")
                    if not params.get("audio_path"):
                        missing_required.append("audio_path")
                    if not params.get("output_dir"):
                        missing_required.append("output_dir")
                    
                    if missing_required:
                        self._update_state(AgentState.WAITING_INPUT)
                        return AgentMessage(
                            role="assistant",
                            content=f"I need the following information to split your video:\n" +
                                    "\n".join(f"- {param}" for param in missing_required) +
                                    "\n\nPlease provide these details or upload the files."
                        )
                
                # Execute tool via MCP server
                result = self.mcp_server.call_tool(tool_name, params)
                results.append(result)
                
                if not result.get("success"):
                    self._update_state(AgentState.ERROR)
                    return AgentMessage(
                        role="assistant",
                        content=f"Error executing {tool_name}: {result.get('error', 'Unknown error')}",
                        metadata={"tool_results": results}
                    )
            
            # Build success response with output paths
            output_paths = [r.get("output_path") for r in results if r.get("output_path")]
            output_files = []
            for r in results:
                if r.get("metadata", {}).get("output_files"):
                    output_files.extend(r["metadata"]["output_files"])
            
            message = f"✅ Completed! {len(results)} tool(s) executed successfully.\n\n"
            if output_files:
                message += "Output files:\n"
                for path in output_files:
                    message += f"📁 {path}\n"
            elif output_paths:
                message += f"Output: {output_paths[0]}\n"
            
            self._update_state(AgentState.COMPLETE)
            return AgentMessage(
                role="assistant",
                content=message,
                metadata={
                    "tool_results": results,
                    "output_files": output_files or output_paths,
                    "llm_response": llm_response
                }
            )
        else:
            # No tool calls, just return LLM response
            self._update_state(AgentState.WAITING_INPUT)
            return AgentMessage(
                role="assistant",
                content=llm_response,
                metadata={"llm_response": llm_response}
            )

    def _direct_tool_calls(self, text: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return unambiguous commands that should not depend on an LLM."""
        lowered = text.lower()
        video_path = context.get("video_path")
        if not video_path:
            return []
        if "landscape" in lowered or "horizontal" in lowered:
            import os
            stem = os.path.splitext(os.path.basename(video_path))[0]
            return [{"tool": "landscape_crop", "params": {"video_path": video_path, "output_path": os.path.join(context.get("output_dir", "data/output"), f"{stem}_landscape.mp4")}}]
        if "speed" in lowered or "slow motion" in lowered or "time lapse" in lowered:
            return []
        return []

    def _fallback_tool_calls(self, text: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Keep common edits usable when Ollama is offline."""
        lowered = text.lower()
        video_path = context.get("video_path")
        if not video_path:
            return []
        if any(word in lowered for word in ("speed", "fast", "slow", "time-lapse", "timelapse")):
            import os
            return [{"tool": "speed_adjust", "params": {
                "video_path": video_path,
                "output_path": os.path.join(context.get("output_dir", "data/output"), "speed_adjusted.mp4"),
                "speed_factor": 1.0,
            }}]
        return []

    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]], user_input: str, context: Dict[str, Any], tool_config: Dict[str, Any]) -> AgentMessage:
        """Execute a normalized set of calls through the shared path."""
        self._update_state(AgentState.EXECUTING)
        results = []
        for call in tool_calls:
            tool_name = call.get("tool")
            params = dict(call.get("params", {}))
            if context.get("video_path") and tool_name not in {"audio_mix", "transcription"}:
                params["video_path"] = context["video_path"]
            if tool_name == "speed_adjust":
                params.setdefault("speed_factor", 1.0)
            if tool_name in {"landscape_crop", "vertical_crop", "speed_adjust"}:
                params.setdefault("output_path", f"{context.get('output_dir', 'data/output')}/{tool_name}.mp4")
            result = self.mcp_server.call_tool(tool_name, params)
            results.append(result)
            if not result.get("success"):
                self._update_state(AgentState.ERROR)
                return AgentMessage(role="assistant", content=f"Error executing {tool_name}: {result.get('error', 'Unknown error')}", metadata={"tool_results": results})
        outputs = [result.get("output_path") for result in results if result.get("output_path")]
        self._update_state(AgentState.COMPLETE)
        return AgentMessage(role="assistant", content=f"✅ Completed! {len(results)} tool(s) executed successfully.\n\nOutput: {outputs[0]}" if outputs else "✅ Completed.", metadata={"tool_results": results, "output_files": outputs})
    
    def _parse_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse tool calls from LLM response text.
        
        Looks for JSON-formatted tool calls in the response.
        """
        tool_calls = []
        
        # Try to find JSON objects that look like tool calls
        try:
            # Look for common patterns
            patterns = [
                '{"tool":',
                '"tool": "',
                '```json',
                'Tool call:',
                'Calling tool:'
            ]
            
            # Simple extraction: look for tool name and params
            for tool_info in self._tool_definitions:
                tool_name = tool_info["name"]
                if tool_name in response_text.lower():
                    # Found a tool reference, try to extract params
                    params = {}
                    
                    # Look for common parameter patterns
                    if "video" in response_text.lower() or "mp4" in response_text.lower():
                        # Would need more sophisticated parsing for actual paths
                        pass
                    
                    if params or tool_name in response_text:
                        tool_calls.append({
                            "tool": tool_name,
                            "params": params
                        })
            
            # If we found tools mentioned, also check for structured JSON
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                try:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict):
                        if "tool" in parsed:
                            tool_calls = [parsed]
                        elif "tools" in parsed:
                            tool_calls = parsed["tools"]
                    elif isinstance(parsed, list):
                        tool_calls = parsed
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            pass
        
        return tool_calls
    
    def _extract_params_from_text(self, text: str, tool_name: str) -> Dict[str, Any]:
        """Extract parameters from natural language text using regex patterns."""
        import re
        params = {}
        
        # Extract file paths (common patterns)
        path_pattern = r'(/[^\s"\']+|[\w./\\]+\.(mp4|avi|mov|mkv|mp3|wav|ogg|flac))'
        paths = re.findall(path_pattern, text, re.IGNORECASE)
        
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        audio_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.aac'}
        
        for path_match in paths:
            # Handle tuple match from regex
            path = path_match[0] if isinstance(path_match, tuple) else path_match
            lower_path = path.lower()
            
            if any(lower_path.endswith(ext) for ext in video_extensions):
                if 'video_path' not in params:
                    params['video_path'] = path
            elif any(lower_path.endswith(ext) for ext in audio_extensions):
                if 'audio_path' not in params:
                    params['audio_path'] = path
        
        # Extract output directory patterns
        output_patterns = [
            r'output[_\s]*dir(?:ectory)?[:\s]+([^\s,]+)',
            r'save[:\s]+([^\s,]+)',
            r'to[:\s]+([^\s,]+)'
        ]
        for pattern in output_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and 'output_dir' not in params:
                params['output_dir'] = match.group(1).strip('"\'')
        
        # Extract numeric parameters
        duration_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|seconds?|secs?)', text, re.IGNORECASE)
        if duration_match:
            value = float(duration_match.group(1))
            if 'minute' in duration_match.group(0).lower():
                params['max_segment_duration_minutes'] = value
            else:
                params['target_output_duration_seconds'] = value
        
        return params
    
    def chat_stream(self, user_input: str, context: Optional[Dict[str, Any]] = None):
        """
        Stream LLM response for real-time feedback.
        
        Yields chunks of the response as they're generated.
        """
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        response = self.llm_service.chat(messages, stream=True)
        
        if response.get("stream"):
            for chunk in response["response"]:
                yield chunk.decode('utf-8') if isinstance(chunk, bytes) else chunk
    
    def execute_plan(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a planned sequence of tool calls.
        
        Args:
            plan: List of tool call specifications with format:
                  [{"tool": "tool_name", "params": {...}}, ...]
        
        Returns:
            Results of the execution with success status and outputs
        """
        results = []
        success = True
        
        for step in plan:
            tool_name = step.get("tool")
            params = step.get("params", {})
            
            if not tool_name:
                results.append({
                    "success": False,
                    "error": "Missing tool name in plan step"
                })
                success = False
                continue
            
            # Execute tool via MCP server
            result = self.mcp_server.call_tool(tool_name, params)
            results.append(result)
            
            if not result.get("success"):
                success = False
                break
        
        return {
            "success": success,
            "results": results,
            "output_files": [r.get("output_path") for r in results if r.get("output_path")]
        }


# Singleton instance
_llm_agent: Optional[LLMAgent] = None

def get_llm_agent() -> LLMAgent:
    """Get or create the LLM agent singleton."""
    global _llm_agent
    if _llm_agent is None:
        _llm_agent = LLMAgent()
    return _llm_agent
