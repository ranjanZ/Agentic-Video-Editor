# Antigenic Video Editor - AI Agent Based Video Editor

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
- **Chat Agent Interface** (`/` or `/workspace`): Modern chat-focused UI for interacting with the AI agent
- Modular JavaScript architecture with separate modules for chat, video processing, and app logic
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
│   ├── video_split_tool.py  # Split video into segments
│   ├── silence_removal_tool.py
│   ├── transcription_tool.py
│   ├── speed_adjust_tool.py
│   ├── vertical_crop_tool.py
│   └── audio_mix_tool.py
│
├── agents/                  # AI agent implementations
│   ├── __init__.py
│   ├── base_agent.py        # Base agent class
│   ├── llm_agent.py         # LLM-powered agent using Ollama
│   ├── video_editing_agent.py
│   └── workflow_agent.py    # Workflow orchestration agent
│
├── mcp/                     # MCP Server implementation
│   ├── __init__.py
│   └── server.py            # MCP-compatible tool server
│
├── llm/                     # LLM services
│   ├── __init__.py
│   └── ollama_service.py    # Ollama integration
│
├── api/                     # REST API server
│   ├── __init__.py
│   └── server.py            # Flask API endpoints
│
├── web/                     # Web interface
│   └── workspace/           # Chat agent interface
│       ├── index.html       # Main chat UI
│       ├── chat_agent.js    # Chat agent client module
│       ├── video_processor.js # Video processing client module
│       └── app.js           # Main application logic
│
├── data/                    # Data directories
│   ├── input/               # Uploaded files
│   ├── output/              # Processed outputs
│   └── temp/                # Temporary files
│
├── config/                  # Configuration files
│   └── default_config.yaml
│
├── run.py                   # Main entry point
└── requirements.txt         # Python dependencies
```

## Installation

### Prerequisites

1. **Python 3.8+**
2. **FFmpeg** - Required for video processing
3. **Ollama** - For running the LLM agent locally

### Install FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install -y ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html or use chocolatey:
```bash
choco install ffmpeg
```

### Install Ollama

**Linux/macOS:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from https://ollama.ai/download

### Pull the LLM Model

```bash
ollama pull qwen2.5:1.5b-instruct-q4_K_M
```

Or use any other model:
```bash
ollama pull llama3.2:1b
```

### Install Python Dependencies

```bash
cd antigenic-video-editor
pip install -r requirements.txt
```

## Usage

### Start the Server

```bash
python run.py
```

The server will start on `http://localhost:5000`.

### Access the Chat Interface

Open your browser and navigate to:
- **Main Interface**: http://localhost:5000
- **Workspace**: http://localhost:5000/workspace

Both URLs serve the same chat agent interface built in `web/workspace/`.

### Using the Chat Agent

1. **Upload Files**: Drag and drop video/audio files into the upload zone
2. **Describe Your Task**: Type your video editing request in natural language
   - Example: "Split my video into shorts and add background music"
   - Example: "Remove silence from my video"
   - Example: "Convert this to vertical format for TikTok"
3. **View Results**: The agent will process your request and show the output video

### Running Tools Directly (Command Line)

Each tool can be executed directly from the command line with default input from `data/input/` folder. Default video: `data/input/input.mkv`, Default audio: `data/input/input_audio.mp3`.

**Quick Start:** Run any tool with `--help` to see all available options:
```bash
python -m tools.<tool_name> --help
```

#### 1. Video Split Tool
Split video into segments with speed-up and background music:
```bash
python -m tools.video_split_tool --video data/input/input.mkv --audio data/input/input_audio.mp3 --output-dir data/output --max-segment-minutes 20 --target-duration 29
```

#### 2. Silence Removal Tool
Remove silent portions from video using Whisper AI:
```bash
python -m tools.silence_removal_tool --video data/input/input.mkv --output data/output/no_silence_output.mp4 --model base --padding-ms 200
```

#### 3. Transcription Tool
Transcribe speech from video to text:
```bash
python -m tools.transcription_tool --input data/input/input.mkv --model base --task transcribe
```

#### 4. Speed Adjust Tool
Change video playback speed:
```bash
python -m tools.speed_adjust_tool --video data/input/input.mkv --output data/output/speed_adjusted_output.mp4 --speed 2.0
```

#### 5. Vertical Crop Tool
Convert landscape video to 9:16 vertical format:
```bash
python -m tools.vertical_crop_tool --video data/input/input.mkv --output data/output/vertical_output.mp4 --width 1080 --height 1920
```

#### 6. Landscape Crop Tool
Convert video to 16:9 landscape format:
```bash
python -m tools.landscape_crop_tool --video data/input/input.mkv --output data/output/landscape_output.mp4 --width 1920 --height 1080
```

#### 7. Audio Mix Tool
Add background music to video:
```bash
python -m tools.audio_mix_tool --video data/input/input.mkv --audio data/input/input_audio.mp3 --output data/output/audio_mixed_output.mp4 --music-volume 0.3
```

#### 8. Process Video Pipeline
Complete pipeline: split, speed-up, and add background music:
```bash
python -m tools.process_video_tool --video data/input/input.mkv --audio data/input/input_audio.mp3 --output-dir data/output --max-segment-minutes 20 --target-duration 29
```

**Note:** All tools use default paths from the `data/input/` folder if no arguments are provided. Simply run `python -m tools.<tool_name>` to execute with defaults.

### Example Commands

- "Split my video into 30-second segments with background music"
- "Remove all silent parts from the video"
- "Make this video vertical for Instagram Reels"
- "Add this audio track as background music at 40% volume"
- "Transcribe the speech in my video"

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/tools` - List available tools
- `POST /api/tools/<name>` - Execute a tool
- `POST /api/agent/chat` - Chat with the AI agent
- `GET /api/workflows` - List workflows
- `POST /api/workflows/<name>` - Execute a workflow
- `POST /api/upload` - Upload files
- `GET /data/output/<filename>` - Access processed output files

## Architecture

### MCP Server Pattern

The system uses a centralized MCP (Model Context Protocol) server to expose video editing tools:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  LLM Agent  │────▶│  MCP Server  │────▶│ Video Tools │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Tool Registry│
                    └──────────────┘
```

### Modular Design

All components are designed to be modular and reusable:

1. **Tools** (`tools/`): Each video editing operation is a standalone tool with a consistent interface
2. **MCP Server** (`mcp/server.py`): Central registry that exposes all tools via a unified API
3. **Agents** (`agents/`): 
   - `LLMAgent`: Uses Ollama LLM to understand natural language and call tools via MCP
   - `WorkflowAgent`: Executes predefined multi-step workflows
4. **API Server** (`api/server.py`): Flask backend that integrates MCP server and agents
5. **Web Interface** (`web/workspace/`): Modular JavaScript frontend with separate concerns

### Tool Flow

1. User sends natural language request via chat interface
2. LLM Agent parses the request and identifies required tools
3. Agent calls MCP server with tool name and parameters
4. MCP server validates parameters and executes the tool
5. Results are returned to the agent
6. Agent formats response and sends back to user

### Adding New Tools

```python
from tools.base_tool import BaseTool, ToolResult

class MyNewTool(BaseTool):
    @property
    def name(self): 
        return "my_tool"

    @property
    def description(self): 
        return "Does something useful"

    @property
    def input_schema(self):
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "A parameter"}
            },
            "required": ["param1"]
        }

    def execute(self, param1: str, **kwargs) -> ToolResult:
        # Your implementation
        return ToolResult(success=True, output_path="output.mp4")
```

Then register it in `mcp/server.py`:
```python
from tools.my_new_tool import MyNewTool

def _register_default_tools(self):
    tools = [
        # ... existing tools ...
        MyNewTool(),
    ]
    for tool in tools:
        self.registry.register(tool)
```

## Configuration

### Environment Variables

- `OLLAMA_HOST`: Ollama server host (default: http://localhost:11434)
- `LLM_MODEL`: Model to use (default: qwen2.5:1.5b-instruct-q4_K_M)

### Default Paths

- Upload folder: `data/input/`
- Output folder: `data/output/`
- Temp folder: `data/temp/`

## Troubleshooting

### Ollama Not Running

```bash
ollama serve
```

### FFmpeg Not Found

Ensure FFmpeg is installed and in your PATH:
```bash
which ffmpeg  # Linux/macOS
where ffmpeg  # Windows
```

### Model Not Found

Pull the required model:
```bash
ollama pull qwen2.5:1.5b-instruct-q4_K_M
```

### Port Already in Use

Change the port in `run.py`:
```python
run_server(host='0.0.0.0', port=8080, debug=True)
```

## License

MIT License
