"""
Base tool class and registry for the Antigenic Video Editor.

All video processing tools should inherit from BaseTool to ensure
consistent interfaces for agentic invocation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    output_path: Optional[str] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output_path": self.output_path,
            "message": self.message,
            "metadata": self.metadata,
            "error": self.error,
        }


class BaseTool(ABC):
    """
    Abstract base class for all video processing tools.
    
    Each tool should:
    1. Have a unique name
    2. Define input/output schemas
    3. Implement the execute method
    4. Provide a description for agent understanding
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this tool."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        pass
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        """JSON schema describing required inputs."""
        return {}
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        """JSON schema describing outputs."""
        return {}
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with the given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult with success status and output
        """
        pass
    
    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters before execution."""
        return True
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"


class ToolRegistry:
    """
    Central registry for all available tools.
    
    Agents can query this registry to discover available tools
    and their capabilities.
    """
    
    _instance: Optional["ToolRegistry"] = None
    _tools: Dict[str, BaseTool] = {}
    
    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict[str, str]]:
        """List all registered tools with their descriptions."""
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]
    
    def get_tool_names(self) -> List[str]:
        """Get list of all tool names."""
        return list(self._tools.keys())
    
    def unregister(self, name: str) -> bool:
        """Remove a tool from the registry."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False


def register_tool(tool_class):
    """Decorator to automatically register a tool class."""
    def wrapper(*args, **kwargs):
        instance = tool_class(*args, **kwargs)
        ToolRegistry().register(instance)
        return instance
    return wrapper
