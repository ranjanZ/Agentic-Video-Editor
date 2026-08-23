"""
Workflow Agent - Agent for managing complex video editing workflows.

This agent handles multi-step workflows with dependencies and conditional logic.
"""

from typing import Any, Dict, List, Optional
from .base_agent import BaseAgent, AgentConfig, AgentMessage, AgentState


class WorkflowAgent(BaseAgent):
    """
    Agent for orchestrating complex video editing workflows.
    
    This agent can:
    - Define workflow templates
    - Execute workflows with parameter substitution
    - Handle branching and conditional execution
    - Track workflow progress
    """
    
    def __init__(self, config: Optional[AgentConfig] = None, tools: Optional[Dict] = None, mcp_server=None):
        super().__init__(config or AgentConfig(name="workflow_agent"))
        
        # Store MCP server reference
        self.mcp_server = mcp_server
        
        # Register available tools (either directly or via MCP server)
        if tools:
            for name, tool in tools.items():
                self.register_tool(name, tool)
        elif mcp_server:
            # Get tools from MCP server
            mcp_tools = mcp_server.list_tools()
            # Tools will be called via MCP server during execution
        
        # Predefined workflow templates
        self._workflow_templates = {
            "shorts_from_long": self._shorts_workflow,
            "clean_speech": self._clean_speech_workflow,
            "full_production": self._full_production_workflow,
        }
    
    @property
    def name(self) -> str:
        return "workflow_agent"
    
    @property
    def description(self) -> str:
        return (
            "Agent that manages complex video editing workflows with multiple steps, "
            "handling dependencies and providing progress tracking."
        )
    
    def list_workflows(self) -> List[str]:
        """List available workflow templates."""
        return list(self._workflow_templates.keys())
    
    def get_workflow_template(self, name: str) -> Optional[callable]:
        """Get a workflow template by name."""
        return self._workflow_templates.get(name)
    
    def process(self, user_input: str) -> AgentMessage:
        """
        Process user request for workflow execution.
        
        Args:
            user_input: User's request
            
        Returns:
            AgentMessage with response
        """
        self.add_message("user", user_input)
        self._current_iteration += 1
        
        # Parse request
        user_input_lower = user_input.lower()
        
        # Check if user wants to list workflows
        if "list" in user_input_lower or "workflows" in user_input_lower:
            workflows = self.list_workflows()
            return AgentMessage(
                role="assistant",
                content=f"Available workflows:\n" + 
                        "\n".join(f"- {w}" for w in workflows)
            )
        
        # Try to match workflow
        matched_workflow = None
        params = {}
        
        for wf_name in self._workflow_templates.keys():
            if wf_name.replace("_", " ") in user_input_lower:
                matched_workflow = wf_name
                break
        
        if not matched_workflow:
            return AgentMessage(
                role="assistant",
                content="I can help you with these workflows:\n" +
                        "\n".join(f"- {w}" for w in self.list_workflows()) +
                        "\n\nPlease specify which workflow you'd like to run."
            )
        
        # Extract parameters from input or use defaults
        params = self._extract_params(user_input)
        
        # Get and execute workflow
        workflow_func = self._workflow_templates[matched_workflow]
        
        try:
            plan = workflow_func(params)
            
            if self.config.require_confirmation:
                return AgentMessage(
                    role="assistant",
                    content=f"Workflow '{matched_workflow}' will execute {len(plan)} steps.\n"
                            f"Plan: {self._describe_plan(plan)}\n\nProceed?"
                )
            
            result = self.execute_plan(plan)
            
            if result.get("success"):
                self._update_state(AgentState.COMPLETE)
                return AgentMessage(
                    role="assistant",
                    content=result.get("message", "Workflow completed!"),
                    metadata={"result": result}
                )
            else:
                self._update_state(AgentState.ERROR)
                return AgentMessage(
                    role="assistant",
                    content=f"Workflow failed: {result.get('error')}",
                    metadata={"result": result}
                )
                
        except Exception as e:
            self._update_state(AgentState.ERROR)
            return AgentMessage(
                role="assistant",
                content=f"Error executing workflow: {str(e)}"
            )
    
    def execute_plan(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a workflow plan."""
        results = []
        context = {}  # Store outputs for chaining
        
        for i, step in enumerate(plan):
            tool_name = step.get("tool")
            params = step.get("params", {})
            
            # Substitute context variables
            params = self._substitute_params(params, context)
            
            # Execute via MCP server if available, otherwise use registered tools
            if self.mcp_server:
                result_dict = self.mcp_server.call_tool(tool_name, params)
                result_success = result_dict.get("success", False)
                result_error = result_dict.get("error")
                result_output_path = result_dict.get("output_path")
                
                if not result_success:
                    return {"success": False, "error": result_error, "results": results}
                
                # Store output for next steps
                if result_output_path:
                    context[f"output_{i}"] = result_output_path
                    context["latest_output"] = result_output_path
                
                results.append({"step": i + 1, "tool": tool_name, "result": result_dict})
            else:
                tool = self._tools.get(tool_name)
                if not tool:
                    return {"success": False, "error": f"Tool '{tool_name}' not found"}
                
                try:
                    result = tool.execute(**params)
                    results.append({"step": i + 1, "tool": tool_name, "result": result.to_dict()})
                    
                    if not result.success:
                        return {"success": False, "error": result.error, "results": results}
                    
                    # Store output for next steps
                    if result.output_path:
                        context[f"output_{i}"] = result.output_path
                        context["latest_output"] = result.output_path
                        
                except Exception as e:
                    return {"success": False, "error": str(e), "results": results}
        
        return {
            "success": True,
            "message": f"Workflow completed successfully ({len(plan)} steps)",
            "output_path": context.get("latest_output"),
            "results": results
        }
    
    def _shorts_workflow(self, params: Dict) -> List[Dict]:
        """Workflow: Create shorts from long video."""
        return [
            {
                "tool": "video_split",
                "params": {
                    "video_path": params.get("video_path", ""),
                    "audio_path": params.get("audio_path", ""),
                    "output_dir": params.get("output_dir", "./output"),
                    "max_segment_duration_minutes": params.get("segment_duration", 20),
                    "target_output_duration_seconds": params.get("target_duration", 29),
                    "vertical_mode": params.get("vertical", True)
                }
            }
        ]
    
    def _clean_speech_workflow(self, params: Dict) -> List[Dict]:
        """Workflow: Remove silence from speech video."""
        return [
            {
                "tool": "silence_removal",
                "params": {
                    "video_path": params.get("video_path", ""),
                    "output_path": params.get("output_path", "./output_clean.mp4"),
                    "model_size": params.get("model_size", "base"),
                    "padding_ms": params.get("padding_ms", 200)
                }
            }
        ]
    
    def _full_production_workflow(self, params: Dict) -> List[Dict]:
        """Workflow: Full production pipeline."""
        temp_base = params.get("temp_prefix", "./temp")
        
        return [
            {
                "tool": "silence_removal",
                "params": {
                    "video_path": params.get("video_path", ""),
                    "output_path": f"{temp_base}_clean.mp4",
                    "model_size": params.get("model_size", "base")
                }
            },
            {
                "tool": "vertical_crop",
                "params": {
                    "video_path": f"{temp_base}_clean.mp4",
                    "output_path": f"{temp_base}_vertical.mp4"
                }
            },
            {
                "tool": "audio_mix",
                "params": {
                    "video_path": f"{temp_base}_vertical.mp4",
                    "audio_path": params.get("audio_path", ""),
                    "output_path": params.get("output_path", "./output_final.mp4"),
                    "music_volume": params.get("music_volume", 0.3)
                }
            }
        ]
    
    def _extract_params(self, user_input: str) -> Dict:
        """Extract parameters from user input."""
        # Simple extraction - in production use LLM or proper parsing
        params = {}
        
        # Look for file paths
        import re
        paths = re.findall(r'[/\w.-]+\.(mp4|avi|mov|mkv|mp3|wav)', user_input)
        if paths:
            if any(p.endswith(('.mp3', '.wav')) for p in paths):
                params['audio_path'] = next(p for p in paths if p.endswith(('.mp3', '.wav')))
            if any(p.endswith(('.mp4', '.avi', '.mov', '.mkv')) for p in paths):
                params['video_path'] = next(p for p in paths if p.endswith(('.mp4', '.avi', '.mov', '.mkv')))
        
        return params
    
    def _substitute_params(self, params: Dict, context: Dict) -> Dict:
        """Substitute context variables into parameters."""
        result = {}
        for key, value in params.items():
            if isinstance(value, str):
                for ctx_key, ctx_value in context.items():
                    value = value.replace(f"{{{ctx_key}}}", str(ctx_value))
                    value = value.replace(f"{{{{{ctx_key}}}}}", str(ctx_value))
            result[key] = value
        return result
    
    def _describe_plan(self, plan: List[Dict]) -> str:
        """Describe a plan in human-readable format."""
        lines = []
        for i, step in enumerate(plan, 1):
            lines.append(f"{i}. {step.get('tool')}")
        return "\n".join(lines)
