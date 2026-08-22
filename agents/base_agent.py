"""
Base Agent class for the Antigenic Video Editor.

All video editing agents should inherit from this base class to ensure
consistent interfaces and capabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


class AgentState(Enum):
    """Agent execution states."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_INPUT = "waiting_input"
    ERROR = "error"
    COMPLETE = "complete"


@dataclass
class AgentConfig:
    """Configuration for agent behavior."""
    name: str = "agent"
    max_iterations: int = 10
    verbose: bool = True
    auto_execute: bool = False
    require_confirmation: bool = False
    llm_model: str = "gpt-4"
    temperature: float = 0.7
    system_prompt: Optional[str] = None


@dataclass
class AgentMessage:
    """Message passed between agent and user/system."""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
        }
        # Include output_files at top level if present in metadata
        if self.metadata and 'output_files' in self.metadata:
            result['output_files'] = self.metadata['output_files']
        return result


class BaseAgent(ABC):
    """
    Abstract base class for all video editing agents.
    
    Agents are responsible for:
    1. Understanding user intent (via LLM or other means)
    2. Planning a sequence of tool invocations
    3. Executing tools and handling results
    4. Communicating progress and results to the user
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.state = AgentState.IDLE
        self.message_history: List[AgentMessage] = []
        self._tools: Dict[str, Callable] = {}
        self._current_iteration = 0
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this agent."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this agent does."""
        pass
    
    @property
    def available_tools(self) -> List[str]:
        """List of tool names available to this agent."""
        return list(self._tools.keys())
    
    def register_tool(self, name: str, tool_func: Callable) -> None:
        """Register a tool function with the agent."""
        self._tools[name] = tool_func
    
    def unregister_tool(self, name: str) -> bool:
        """Remove a tool from the agent."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a message to the conversation history."""
        msg = AgentMessage(role=role, content=content, metadata=metadata or {})
        self.message_history.append(msg)
    
    def clear_history(self) -> None:
        """Clear the message history."""
        self.message_history = []
        self._current_iteration = 0
    
    @abstractmethod
    def process(self, user_input: str) -> AgentMessage:
        """
        Process user input and return a response.
        
        Args:
            user_input: User's natural language request
            
        Returns:
            AgentMessage with the agent's response
        """
        pass
    
    @abstractmethod
    def execute_plan(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a planned sequence of tool calls.
        
        Args:
            plan: List of tool call specifications
            
        Returns:
            Results of the execution
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "iteration": self._current_iteration,
            "max_iterations": self.config.max_iterations,
            "available_tools": self.available_tools,
            "message_count": len(self.message_history),
        }
    
    def _update_state(self, new_state: AgentState) -> None:
        """Update agent state."""
        self.state = new_state
    
    def _should_continue(self) -> bool:
        """Check if agent should continue processing."""
        return (
            self.state not in (AgentState.COMPLETE, AgentState.ERROR) and
            self._current_iteration < self.config.max_iterations
        )
