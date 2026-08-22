"""
Flask REST API server for Antigenic Video Editor.

Provides endpoints for:
- Video processing operations
- Agent interactions
- Workflow management
- Status monitoring
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading
import uuid

from tools.base_tool import ToolRegistry
from tools.video_split_tool import VideoSplitTool
from tools.silence_removal_tool import SilenceRemovalTool
from tools.transcription_tool import TranscriptionTool
from tools.speed_adjust_tool import SpeedAdjustTool
from tools.vertical_crop_tool import VerticalCropTool
from tools.audio_mix_tool import AudioMixTool

from agents.video_editing_agent import VideoEditingAgent
from agents.workflow_agent import WorkflowAgent


def create_app(config=None):
    """Create and configure the Flask application."""
    
    app = Flask(__name__, static_folder='../web/static', template_folder='../web/templates')
    CORS(app)
    
    # Configuration
    app.config['UPLOAD_FOLDER'] = 'data/input'
    app.config['OUTPUT_FOLDER'] = 'data/output'
    app.config['TEMP_FOLDER'] = 'data/temp'
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
    
    # Ensure directories exist
    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], app.config['TEMP_FOLDER']]:
        os.makedirs(folder, exist_ok=True)
    
    # Initialize tool registry
    tool_registry = ToolRegistry()
    tool_registry.register(VideoSplitTool())
    tool_registry.register(SilenceRemovalTool())
    tool_registry.register(TranscriptionTool())
    tool_registry.register(SpeedAdjustTool())
    tool_registry.register(VerticalCropTool())
    tool_registry.register(AudioMixTool())
    
    # Initialize agents
    video_agent = VideoEditingAgent(tools={
        'video_split': VideoSplitTool(),
        'silence_removal': SilenceRemovalTool(),
        'transcription': TranscriptionTool(),
        'speed_adjust': SpeedAdjustTool(),
        'vertical_crop': VerticalCropTool(),
        'audio_mix': AudioMixTool(),
    })
    
    workflow_agent = WorkflowAgent(tools={
        'video_split': VideoSplitTool(),
        'silence_removal': SilenceRemovalTool(),
        'transcription': TranscriptionTool(),
        'speed_adjust': SpeedAdjustTool(),
        'vertical_crop': VerticalCropTool(),
        'audio_mix': AudioMixTool(),
    })
    
    # Store in app context
    app.tool_registry = tool_registry
    app.video_agent = video_agent
    app.workflow_agent = workflow_agent
    app.active_jobs = {}
    
    # Routes
    
    @app.route('/')
    def index():
        """Serve the main web interface."""
        return send_from_directory('../web/templates', 'index.html')
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'service': 'antigenic-video-editor',
            'version': '1.0.0'
        })
    
    @app.route('/data/output/<path:filename>', methods=['GET'])
    def serve_output(filename):
        """Serve output video files."""
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename)
    
    @app.route('/data/temp/<path:filename>', methods=['GET'])
    def serve_temp(filename):
        """Serve temporary video files."""
        return send_from_directory(app.config['TEMP_FOLDER'], filename)
    
    @app.route('/api/tools', methods=['GET'])
    def list_tools():
        """List all available tools."""
        tools = tool_registry.list_tools()
        return jsonify({'tools': tools})
    
    @app.route('/api/tools/<tool_name>', methods=['POST'])
    def execute_tool(tool_name):
        """Execute a specific tool."""
        tool = tool_registry.get(tool_name)
        if not tool:
            return jsonify({'error': f'Tool {tool_name} not found'}), 404
        
        data = request.json or {}
        result = tool.execute(**data)
        
        if result.success:
            return jsonify(result.to_dict())
        else:
            return jsonify(result.to_dict()), 400
    
    @app.route('/api/agent/chat', methods=['POST'])
    def agent_chat():
        """Chat with the video editing agent (LLM-powered)."""
        data = request.json
        user_input = data.get('message', '')
        context = data.get('context', {})  # Optional context with file paths
        
        if not user_input:
            return jsonify({'error': 'No message provided'}), 400
        
        # Use LLM agent for intelligent processing
        from agents.llm_agent import get_llm_agent
        llm_agent = get_llm_agent()
        
        response = llm_agent.process(user_input, context)
        
        result = response.to_dict()
        
        # Ensure output_files is in the response for frontend display
        if response.metadata and response.metadata.get('output_files'):
            result['output_files'] = response.metadata['output_files']
        
        return jsonify(result)
    
    @app.route('/api/agent/status', methods=['GET'])
    def agent_status():
        """Get agent status."""
        return jsonify({
            'video_agent': app.video_agent.get_status(),
            'workflow_agent': app.workflow_agent.get_status()
        })
    
    @app.route('/api/workflows', methods=['GET'])
    def list_workflows():
        """List available workflows."""
        workflows = app.workflow_agent.list_workflows()
        return jsonify({'workflows': workflows})
    
    @app.route('/api/workflows/<workflow_name>', methods=['POST'])
    def execute_workflow(workflow_name):
        """Execute a workflow."""
        data = request.json or {}
        user_input = f"Run {workflow_name} workflow"
        
        response = app.workflow_agent.process(user_input)
        
        if response.metadata.get('result', {}).get('success'):
            return jsonify(response.to_dict())
        else:
            return jsonify(response.to_dict()), 400
    
    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        """Upload a video or audio file."""
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filepath': filepath,
            'filename': filename
        })
    
    @app.route('/api/jobs', methods=['GET'])
    def list_jobs():
        """List active jobs."""
        return jsonify({'jobs': list(app.active_jobs.values())})
    
    @app.route('/api/jobs/<job_id>', methods=['GET'])
    def get_job_status(job_id):
        """Get job status."""
        job = app.active_jobs.get(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        return jsonify(job)
    
    return app


def run_server(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask server."""
    app = create_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
