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
        
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        # Add context if provided
        if context:
            context_str = json.dumps(context, indent=2)
            messages.append({"role": "system", "content": f"Context: {context_str}"})
        
        # Get LLM response
        response = self.llm_service.chat(messages)
        
        if not response.get("success"):
            self._update_state(AgentState.ERROR)
            return AgentMessage(
                role="assistant",
                content=f"Error: Could not process request - {response.get('error', 'Unknown error')}"
            )
        
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
                
                # Inject context into parameters
                if context:
                    if "video_path" not in params and context.get("video_path"):
                        params["video_path"] = context["video_path"]
                    if "audio_path" not in params and context.get("audio_path"):
                        params["audio_path"] = context["audio_path"]
                    if "output_dir" not in params and context.get("output_dir"):
                        params["output_dir"] = context["output_dir"]
                
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
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            pass
        
        return tool_calls
    
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
