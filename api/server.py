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
from mcp.server import get_mcp_server

from agents.llm_agent import get_llm_agent
from agents.workflow_agent import WorkflowAgent


def create_app(config=None):
    """Create and configure the Flask application."""
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    app = Flask(__name__)
    CORS(app)
    
    # Serve the compiled Vite app. Browsers cannot execute the source TSX files.
    app.workspace_folder = os.path.join(base_dir, 'web', 'workspace', 'dist')
    app.static_folder = app.workspace_folder
    app.template_folder = app.workspace_folder
    
    # Configuration - use absolute paths
    app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'data', 'input')
    app.config['OUTPUT_FOLDER'] = os.path.join(base_dir, 'data', 'output')
    app.config['TEMP_FOLDER'] = os.path.join(base_dir, 'data', 'temp')
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max
    
    # Ensure directories exist
    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER'], app.config['TEMP_FOLDER']]:
        os.makedirs(folder, exist_ok=True)
    
    # Initialize MCP server (which initializes tool registry internally)
    mcp_server = get_mcp_server()
    tool_registry = mcp_server.registry
    
    # Initialize agents with shared tool registry via MCP server
    llm_agent = get_llm_agent()  # Uses MCP server internally
    workflow_agent = WorkflowAgent(mcp_server=mcp_server)
    
    # Store in app context
    app.mcp_server = mcp_server
    app.tool_registry = tool_registry
    app.llm_agent = llm_agent
    app.workflow_agent = workflow_agent
    app.active_jobs = {}
    
    # Routes
    
    @app.route('/')
    def index():
        """Serve the workspace chat interface as the main UI."""
        return send_from_directory(app.workspace_folder, 'index.html')
    
    @app.route('/workspace/')
    def workspace_index():
        """Alias for the workspace chat interface."""
        return send_from_directory(app.workspace_folder, 'index.html')

    @app.route('/favicon.ico')
    def favicon():
        """Avoid a noisy 404 when the browser requests the optional favicon."""
        return '', 204
    
    @app.route('/<path:filename>')
    def serve_workspace_static_files(filename):
        """Serve workspace static files (JS, CSS)."""
        # Check if file exists in workspace folder
        file_path = os.path.join(app.workspace_folder, filename)
        if os.path.exists(file_path):
            # Define custom MIME types for TypeScript/TSX files
            mime_types = {
                '.tsx': 'text/javascript',
                '.ts': 'text/javascript',
                '.jsx': 'text/javascript',
                '.js': 'text/javascript',
                '.css': 'text/css',
                '.html': 'text/html',
                '.json': 'application/json',
                '.woff': 'font/woff',
                '.woff2': 'font/woff2',
                '.ttf': 'font/ttf',
                '.eot': 'application/vnd.ms-fontobject',
                '.svg': 'image/svg+xml',
            }
            _, ext = os.path.splitext(filename)
            mime_type = mime_types.get(ext.lower(), 'application/octet-stream')
            return send_from_directory(app.workspace_folder, filename, mimetype=mime_type)
        return jsonify({'error': 'File not found'}), 404
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'service': 'antigenic-video-editor',
            'version': '1.0.0'
        })
    
    @app.route('/data/<folder_type>/<path:filename>', methods=['GET'])
    def serve_data_files(folder_type, filename):
        """Serve data files (output, temp, input)."""
        if folder_type == 'output':
            folder = app.config['OUTPUT_FOLDER']
        elif folder_type == 'temp':
            folder = app.config['TEMP_FOLDER']
        elif folder_type == 'input':
            folder = app.config['UPLOAD_FOLDER']
        else:
            return jsonify({'error': 'Invalid folder type'}), 400
        
        return send_from_directory(folder, filename)
    
    @app.route('/data/output', methods=['GET'])
    def list_output_files():
        """List and serve output files directory."""
        import os
        output_folder = app.config['OUTPUT_FOLDER']
        if not os.path.exists(output_folder):
            return jsonify({'error': 'Output folder not found'}), 404
        
        files = []
        for f in os.listdir(output_folder):
            file_path = os.path.join(output_folder, f)
            if os.path.isfile(file_path) and not f.startswith('.'):
                files.append({
                    'name': f,
                    'size': os.path.getsize(file_path),
                    'url': f'/data/output/{f}'
                })
        
        # Return HTML page with file listing if browser requests it
        if request.headers.get('Accept', '').includes('text/html'):
            html = f'''<!DOCTYPE html>
<html>
<head><title>Output Files - FrameForge</title>
<style>
body {{ font-family: system-ui, sans-serif; padding: 2rem; background: #0a0f1a; color: #e8eef8; }}
h1 {{ color: #ffb224; }}
.file-list {{ list-style: none; padding: 0; }}
.file-item {{ padding: 0.75rem 1rem; margin: 0.5rem 0; background: #111927; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }}
.file-item:hover {{ background: #1a2639; }}
.file-name {{ font-family: monospace; color: #3adbe6; }}
.file-size {{ color: #8899ac; font-size: 0.85em; }}
.download-btn {{ background: #ffb224; color: #0a0f1a; padding: 0.5rem 1rem; border-radius: 4px; text-decoration: none; font-weight: 600; }}
.download-btn:hover {{ background: #ffc952; }}
</style>
</head>
<body>
<h1>📁 Output Files</h1>
<p>Download your processed videos and audio files.</p>
<ul class="file-list">
{"".join(f'<li class="file-item"><span class="file-name">{f["name"]}</span><span class="file-size">{(f["size"]/1024/1024):.2f} MB</span><a href="{f["url"]}" class="download-btn" download>Download</a></li>' for f in files)}
</ul>
{files and '<p style="margin-top:2rem;"><a href="/" style="color:#3adbe6;">← Back to editor</a></p>' or '<p>No output files yet. Run a tool or use the chat to create one.</p>'}
</body>
</html>'''
            return html
        
        return jsonify({'files': files})
    
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
            'llm_agent': app.llm_agent.get_status(),
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
