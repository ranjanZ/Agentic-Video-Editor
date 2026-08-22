"""
Agents module for Antigenic Video Editor.

This module contains AI agents that can orchestrate video editing tasks
using natural language understanding and tool invocation.
"""

from .base_agent import BaseAgent, AgentConfig, AgentState
from .video_editing_agent import VideoEditingAgent
from .workflow_agent import WorkflowAgent

__version__ = "1.0.0"
__all__ = [
    "BaseAgent",
    "AgentConfig",
    "AgentState",
    "VideoEditingAgent",
    "WorkflowAgent",
]
