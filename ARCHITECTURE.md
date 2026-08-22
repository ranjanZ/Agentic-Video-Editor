# Agentic Video Editor - Architecture & Changes

## Overview
This document describes the scalable agentic video editor architecture and recent fixes implemented.

## Recent Fixes (Completed)

### 1. ✅ Fixed Temporary Files in Root Directory
- **Issue**: Temporary videos were being saved in root folder (e.g., `segment_001_20min_sped_29sTEMP_MPY_wvf_snd.mp4`)
- **Fix**: Updated `tools/video_split_tool.py` to save all output files with timestamps in the `data/output/` directory
- **Filename Format**: `segment_{num}_{timestamp}_{duration}min_sped_{target}s.{format}`

### 2. ✅ Added DateTime to Output Filenames
- All output files now include timestamp in format `YYYYMMDD_HHMMSS`
- Prevents filename collisions and enables tracking

### 3. ✅ Video Display in Web Interface
- Added video player to chat interface
- Automatically detects video files (.mp4, .webm, .mov) and displays them with:
  - Embedded video player with controls
  - Download button
  - File path display
- Non-video files shown as file links

### 4. ✅ Static File Serving
- Added routes to serve output and temp files:
  - `/data/output/<filename>` - Serve processed videos
  - `/data/temp/<filename>` - Serve temporary files

## Scalable Architecture

### Repository Structure
```
agentic_video_editor/
├── core/                    # Core video processing utilities
│   ├── video_utils.py      # MoviePy wrappers, vertical transform, audio helpers
│   ├── process_video.py    # Main processing pipeline
│   └── vid_to_text.py      # Transcription utilities
│
├── tools/                   # Modular tool system (MCP-compatible)
│   ├── base_tool.py        # BaseTool class and ToolRegistry
│   ├── video_split_tool.py # Split + speed-up + music
│   ├── silence_removal_tool.py # Remove silent portions
│   ├── speed_adjust_tool.py # Speed control
│   ├── vertical_crop_tool.py # 9:16 conversion
│   ├── audio_mix_tool.py   # Background music mixing
│   └── transcription_tool.py # Speech-to-text
│
├── agents/                  # AI decision-making layer
│   ├── base_agent.py       # Agent base class
│   ├── llm_agent.py        # Ollama-powered agent (qwen2.5:1.5b)
│   ├── video_editing_agent.py # Specialized video editor
│   └── workflow_agent.py   # Multi-step workflows
│
├── mcp/                     # Model Context Protocol server
│   └── server.py           # Exposes tools as MCP resources
│
├── llm/                     # LLM service layer
│   └── ollama_service.py   # Ollama client for qwen2.5
│
├── api/                     # REST API
│   └── server.py           # Flask server with endpoints
│
├── web/                     # Frontend
│   ├── templates/
│   │   └── index.html      # Chat-based UI with video player
│   └── static/             # CSS, JS, assets
│
├── data/                    # Data directories
│   ├── input/              # Uploaded files
│   ├── output/             # Processed videos (with timestamps)
│   └── temp/               # Temporary processing files
│
├── config/                  # Configuration
│   └── default_config.yaml
│
└── tests/                   # Test suite
```

### Key Design Principles

#### 1. **Modular Tool System**
Each video editing function is a separate tool implementing `BaseTool`:
- Self-contained execution logic
- Standardized input/output schema
- Easy to add new tools without modifying existing code

#### 2. **MCP (Model Context Protocol) Compatible**
Tools are exposed via MCP server, enabling:
- LLM agents to discover available tools dynamically
- Structured tool invocation
- Interoperability with other MCP-compatible systems

#### 3. **Agentic Layer**
Two-tier agent system:
- **LLM Agent**: Uses qwen2.5:1.5b-instruct-q4_K_M via Ollama to understand requests
- **Video Editing Agent**: Specialized agent for video operations
- **Workflow Agent**: Orchestrates multi-step processes

#### 4. **Web Framework**
Flask-based API with:
- REST endpoints for tools and agents
- Chat interface for natural language control
- Manual control options
- Real-time video preview

### Adding New Features

To add a new video editing feature:

1. **Create Tool** (`tools/my_new_tool.py`):
```python
from .base_tool import BaseTool, ToolResult

class MyNewTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_new_tool"
    
    @property
    def description(self) -> str:
        return "Description of what this tool does"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_path": {"type": "string"},
                "param1": {"type": "number", "default": 1.0}
            },
            "required": ["video_path"]
        }
    
    def execute(self, video_path: str, param1: float = 1.0, **kwargs) -> ToolResult:
        # Implementation here
        return ToolResult(success=True, output_path=output_file)
```

2. **Register Tool** in `api/server.py`:
```python
from tools.my_new_tool import MyNewTool
tool_registry.register(MyNewTool())
```

3. **Update LLM Prompt** in `llm/ollama_service.py` to mention the new tool

4. **Agent automatically discovers** the tool via MCP server

### Current Tools

| Tool | Description |
|------|-------------|
| `video_split` | Split long videos into segments with speed-up and background music |
| `silence_removal` | Remove silent portions using Whisper speech detection |
| `speed_adjust` | Change playback speed (fast forward/slow motion) |
| `vertical_crop` | Convert landscape to 9:16 vertical format |
| `audio_mix` | Add background music with volume control |
| `transcription` | Convert speech to text for captions |

### Future Tool Ideas

- `scene_detection` - Auto-detect scene changes
- `color_correction` - Automatic color grading
- `subtitle_generator` - Burn subtitles into video
- `thumbnail_extractor` - Generate video thumbnails
- `noise_reduction` - Audio noise removal
- `face_tracking` - Auto-crop to follow speaker

## Usage

### Via Web Interface
1. Start server: `python3 api/server.py`
2. Open browser to `http://localhost:5000`
3. Upload video/audio files
4. Chat with AI agent or use manual tools

### Via API
```bash
# List tools
curl http://localhost:5000/api/tools

# Execute tool
curl -X POST http://localhost:5000/api/tools/video_split \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "data/input/video.mp4",
    "audio_path": "data/input/music.mp3",
    "output_dir": "data/output"
  }'

# Chat with agent
curl -X POST http://localhost:5000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Split this video into shorts with background music",
    "context": {"video_path": "data/input/video.mp4"}
  }'
```

## Configuration

Edit `config/default_config.yaml`:
```yaml
input_video_path: "data/input/video.mp4"
input_audio_path: "data/input/music.mp3"
output_dir: "data/output"
max_segment_duration_minutes: 20
target_output_duration_seconds: 29
vertical_mode: true
audio_volume: 0.4
```

## Dependencies

See `requirements.txt`:
- moviepy >= 2.0
- flask
- openai-whisper
- pyyaml
- requests (for Ollama)

## LLM Model

Uses `qwen2.5:1.5b-instruct-q4_K_M` via Ollama
- Lightweight (986 MB)
- Fast inference
- Good for tool selection and parameter extraction

Pull model: `ollama pull qwen2.5:1.5b-instruct-q4_K_M`
