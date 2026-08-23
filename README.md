# Antigenic Video Editor

An AI-powered agentic video editing platform that combines automated video processing with intelligent agents for natural language control. The system uses an MCP (Model Context Protocol) server architecture to expose video editing tools that can be called by AI agents.

## Features

### Core Video Processing Tools
- **Video Split**: Split long videos into segments with speed-up and background music (perfect for YouTube Shorts/Reels)
- **Silence Removal**: Automatically detect and remove silent portions using Whisper AI
- **Transcription**: Convert speech to text with timestamps
- **Speed Adjust**: Change video playback speed
- **Vertical Crop**: Convert landscape videos to 9:16 vertical format
- **Audio Mix**: Add background music with volume control and fade effects

### Agentic Capabilities
- **Natural Language Interface**: Describe what you want in plain English
- **MCP Server**: Tools exposed as MCP-compatible endpoints for LLM agents
- **Workflow Automation**: Pre-built workflows for common tasks
- **Tool Orchestration**: Agent automatically chains multiple tools together
- **Interactive Chat**: Get suggestions and confirmations before execution

### Web Interface
- **Main Interface** (`/`): Full-featured UI with all capabilities
- **Workspace Chat Interface** (`/workspace`): Modular chat-focused interface with separate JS modules
- Drag-and-drop file upload
- Real-time chat with AI agent
- Workflow templates
- Tool discovery

## Project Structure

```
antigenic-video-editor/
├── core/                    # Core video processing modules
│   ├── __init__.py
│   ├── video_utils.py       # MoviePy utilities and helpers
│   ├── process_video.py     # Main video processing pipeline
│   ├── video_silence_remover.py  # Silence removal using Whisper
│   └── vid_to_text.py       # Speech-to-text utilities
│
├── tools/                   # Modular tool implementations
│   ├── __init__.py
│   ├── base_tool.py         # Base tool class and registry
│   ├── video_split_tool.py
│   ├── silence_removal_tool.py
│   ├── transcription_tool.py
│   ├── speed_adjust_tool.py
│   ├── vertical_crop_tool.py
│   └── audio_mix_tool.py
│
├── agents/                  # AI agent implementations
│   ├── __init__.py
│   ├── base_agent.py        # Base agent class
│   ├── video_editing_agent.py  # Main editing agent
│   └── workflow_agent.py    # Workflow orchestration agent
│
├── api/                     # REST API server
│   ├── __init__.py
│   └── server.py            # Flask API endpoints
│
├── web/                     # Web interface
│   ├── templates/
│   │   └── index.html       # Main web UI
│   ├── workspace/           # Modular chat interface
│   │   ├── index.html       # Workspace chat UI
│   │   ├── chat_agent.js    # Chat agent client module
│   │   ├── video_processor.js # Video processing client module
│   │   └── app.js           # Main application logic
│   └── static/              # Static assets (CSS, images)
│
├── config/                  # Configuration files
│   └── default_config.yaml
│
├── data/                    # Data directories
│   ├── input/               # Uploaded files
│   ├── output/              # Processed outputs
│   └── temp/                # Temporary files
│
├── tests/                   # Test suite
├── docs/                    # Documentation
└── scripts/                 # Utility scripts
```

## Installation

### Prerequisites
- Python 3.8+
- FFmpeg
- Node.js (optional, for development)

### Install Dependencies

```bash
pip install moviepy openai-whisper flask flask-cors pydub pyyaml
```

## Usage

### Prerequisites

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Install FFmpeg** (required for video processing):
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

3. **Install Ollama and pull the LLM model** (for AI agent features):
```bash
# Install Ollama from https://ollama.ai
ollama pull qwen2.5:1.5b-instruct-q4_K_M
```

### Running the Application

#### Option 1: Main Web Interface
```bash
python -m api.server
```
Then open http://localhost:5000 in your browser.

#### Option 2: Workspace Chat Interface (Modular)
```bash
python -m api.server
```
Then open http://localhost:5000/workspace in your browser.

The workspace interface provides a cleaner, modular architecture with separate JavaScript modules:
- `chat_agent.js` - Handles communication with the AI agent
- `video_processor.js` - Manages tool execution and file uploads
- `app.js` - Main application logic integrating all modules

### API Endpoints

- `GET /api/health` - Health check
- `GET /api/tools` - List available tools
- `POST /api/tools/<name>` - Execute a tool
- `POST /api/agent/chat` - Chat with the AI agent
- `GET /api/workflows` - List workflows
- `POST /api/workflows/<name>` - Execute a workflow
- `POST /api/upload` - Upload files
- `GET /workspace/` - Access the modular chat interface
- `GET /workspace/<filename>` - Access workspace JavaScript modules

### Example: Using the Agent

```python
from agents.video_editing_agent import VideoEditingAgent
from tools.video_split_tool import VideoSplitTool
from tools.silence_removal_tool import SilenceRemovalTool

# Create agent with tools
agent = VideoEditingAgent(tools={
    'video_split': VideoSplitTool(),
    'silence_removal': SilenceRemovalTool(),
})

# Process natural language request
response = agent.process("Split my video into shorts and remove silence")
print(response.content)
```

### Example: Using Tools Directly

```python
from tools.silence_removal_tool import SilenceRemovalTool

tool = SilenceRemovalTool()
result = tool.execute(
    video_path="input.mp4",
    output_path="output.mp4",
    model_size="base"
)

if result.success:
    print(f"Done! Output: {result.output_path}")
else:
    print(f"Error: {result.error}")
```

## Adding New Features

### Creating a New Tool

```python
from tools.base_tool import BaseTool, ToolResult

class MyNewTool(BaseTool):
    @property
    def name(self): return "my_tool"
    
    @property
    def description(self): return "Does something useful"
    
    def execute(self, **kwargs) -> ToolResult:
        # Your implementation
        return ToolResult(success=True, output_path="...")
```

### Creating a New Agent

```python
from agents.base_agent import BaseAgent, AgentMessage

class MyAgent(BaseAgent):
    @property
    def name(self): return "my_agent"
    
    def process(self, user_input: str) -> AgentMessage:
        # Your implementation
        return AgentMessage(role="assistant", content="Response")
```

## Architecture Principles

1. **Modularity**: Each tool is self-contained and independently testable
2. **Composability**: Tools can be chained together by agents
3. **Extensibility**: Easy to add new tools and agents
4. **Scalability**: Clear separation between core logic, agents, and interfaces
5. **Agentic Design**: Natural language understanding drives automation

## License

MIT License
