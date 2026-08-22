"""
MCP (Model Context Protocol) Server for Video Editing Tools.

This module exposes video editing tools as MCP resources and tools,
allowing LLM agents to discover and invoke them programmatically.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from tools.base_tool import ToolRegistry, ToolResult
from tools.video_split_tool import VideoSplitTool
from tools.silence_removal_tool import SilenceRemovalTool
from tools.speed_adjust_tool import SpeedAdjustTool
from tools.vertical_crop_tool import VerticalCropTool
from tools.audio_mix_tool import AudioMixTool
from tools.transcription_tool import TranscriptionTool


class MCPServer:
    """
    MCP-compatible server that exposes video editing tools.
    
    This allows any MCP-compatible client (like LLM agents) to:
    1. Discover available tools
    2. Get tool schemas
    3. Invoke tools with parameters
    4. Receive structured results
    """
    
    def __init__(self):
        self.registry = ToolRegistry()
        self._register_default_tools()
        
    def _register_default_tools(self):
        """Register all available video editing tools."""
        tools = [
            VideoSplitTool(),
            SilenceRemovalTool(),
            SpeedAdjustTool(),
            VerticalCropTool(),
            AudioMixTool(),
            TranscriptionTool(),
        ]
        for tool in tools:
            self.registry.register(tool)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools with their schemas."""
        result = []
        for name, tool in self.registry._tools.items():
            result.append({
                "name": name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
                "outputSchema": tool.output_schema,
            })
        return result
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for a specific tool."""
        tool = self.registry.get(tool_name)
        if not tool:
            return None
        return {
            "name": name,
            "description": tool.description,
            "inputSchema": tool.input_schema,
            "outputSchema": tool.output_schema,
        }
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Dictionary with result or error
        """
        tool = self.registry.get(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
                "available_tools": self.registry.get_tool_names()
            }
        
        try:
            result = tool.execute(**arguments)
            return {
                "success": result.success,
                "output_path": result.output_path,
                "message": result.message,
                "metadata": result.metadata,
                "error": result.error,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "timestamp": datetime.now().isoformat()
            }
    
    def to_mcp_protocol(self) -> Dict[str, Any]:
        """
        Convert to MCP protocol format.
        
        Returns the server capabilities in MCP format.
        """
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": True
                },
                "resources": {}
            },
            "serverInfo": {
                "name": "antigenic-video-editor-mcp",
                "version": "1.0.0"
            },
            "tools": self.list_tools()
        }


# Singleton instance
_mcp_server: Optional[MCPServer] = None

def get_mcp_server() -> MCPServer:
    """Get or create the MCP server singleton."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server
