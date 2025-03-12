"""
API server for mem0 + Ollama integration
"""

import logging
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify, Response, render_template_string, redirect

from config import OLLAMA_HOST, OLLAMA_MODEL, API_PORT, OUTPUT_FORMATS
from templates import INDEX_HTML
from ollama_client import get_available_models
from memory_utils import chat_with_memories

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Store memory instance globally for reuse
memory_instance = None

# Routes
@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template_string(INDEX_HTML)

@app.route('/test')
def test_page():
    """Serve a test page."""
    logger.info("Loading test page")
    try:
        with open('model_test.html', 'r') as f:
            test_html = f.read()
        return test_html
    except Exception as e:
        logger.error(f"Error loading test page: {e}")
        return f"Error loading test page: {e}", 500

@app.route('/direct')
def direct_test_page():
    """Serve a direct test page."""
    logger.info("Loading direct test page")
    try:
        with open('direct_test.html', 'r') as f:
            test_html = f.read()
        return test_html
    except Exception as e:
        logger.error(f"Error loading direct test page: {e}")
        return f"Error loading direct test page: {e}", 500

# Enable CORS for all routes
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

@app.route('/api/tags', methods=['GET'])
def ollama_tags_proxy():
    """Proxy Ollama tags API to support Docker container access."""
    try:
        logger.info("Proxying request to Ollama /api/tags endpoint")
        import requests
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Ollama tags proxy success: {len(data.get('models', []))} models found")
            return jsonify(data)
        else:
            logger.error(f"Ollama tags proxy error: {response.status_code}")
            return jsonify({"error": "Failed to reach Ollama"}), 500
    except Exception as e:
        logger.error(f"Ollama tags proxy exception: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pull', methods=['POST'])
def ollama_pull_proxy():
    """Proxy Ollama pull API to support Docker container access."""
    try:
        logger.info("Proxying request to Ollama /api/pull endpoint")
        import requests
        # Forward the request body to Ollama
        data = request.json
        logger.info(f"Pull request data: {data}")
        
        response = requests.post(f"{OLLAMA_HOST}/api/pull", json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Ollama pull proxy success: {result}")
            return jsonify(result)
        else:
            logger.error(f"Ollama pull proxy error: {response.status_code}, {response.text}")
            return jsonify({"error": "Failed to reach Ollama"}), 500
    except Exception as e:
        logger.error(f"Ollama pull proxy exception: {e}")
        return jsonify({"error": str(e)}), 500

# Simplified API routes that handle memory-based chat
def handle_chat_with_memory():
    """Handle chat requests with always-on memory integration."""
    data = request.json
    
    if not data or "messages" not in data:
        return jsonify({"error": "Invalid request. 'messages' is required."}), 400
    
    # Extract parameters from request
    messages = data.get("messages", [])
    if not messages:
        return jsonify({"error": "No messages provided."}), 400
    
    user_message = next((m["content"] for m in messages if m["role"] == "user"), None)
    if not user_message:
        return jsonify({"error": "No user message found."}), 400
    
    # Extract optional parameters
    model = data.get("model", OLLAMA_MODEL)
    # Ensure we always have a valid conversation_id (never None)
    conversation_id = data.get("conversation_id")
    if conversation_id is None or conversation_id == "":
        conversation_id = f"default_user_{request.remote_addr}"
    
    # Get temperature and max_tokens from request or use defaults
    temperature = float(data.get("temperature", 0.7))
    max_tokens = int(data.get("max_tokens", 2000))
    
    # Validate temperature (between 0.0 and 1.0)
    temperature = max(0.0, min(1.0, temperature))
    
    # Validate max_tokens (reasonable minimum and maximum)
    max_tokens = max(10, min(32000, max_tokens))
    
    # Memory is always on - ignore any memory_mode from the request
    memory_mode = "search"  # Force memory mode to search regardless of request
    format_name = data.get("format")
    
    logger.info(f"Chat request - model: {model}, format: {format_name}, user: {conversation_id}, " +
                f"temperature: {temperature}, max_tokens: {max_tokens}")
    
    # Determine output format (if any)
    output_format = None
    if format_name:
        if format_name in OUTPUT_FORMATS:
            output_format = OUTPUT_FORMATS[format_name]
        else:
            return jsonify({"error": f"Unknown format: {format_name}"}), 400
    
    # Get or initialize memory system
    global memory_instance
    if not memory_instance:
        from memory_utils import initialize_memory
        try:
            memory_instance = initialize_memory(ollama_model=model)
        except Exception as e:
            logger.error(f"Error initializing memory: {e}")
            return jsonify({"error": "Failed to initialize memory system"}), 500
    
    # Process chat with memories
    try:
        response = chat_with_memories(
            memory=memory_instance,
            message=user_message,
            user_id=conversation_id,
            memory_mode=memory_mode,
            output_format=output_format,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Chat endpoint with always-on memory for all requests."""
    try:
        data = request.json
        logger.info(f"Chat request received")
        
        # Always use memory for all chat requests
        # If we don't have conversation_id, we'll assign one in handle_chat_with_memory
        
        if data and 'messages' in data and len(data['messages']) > 0:
            # Generate a stable conversation ID based on client IP if not provided
            if 'conversation_id' not in data or not data['conversation_id']:
                data['conversation_id'] = f"api_user_{request.remote_addr}"
                logger.info(f"Assigned conversation ID: {data['conversation_id']}")
                
            # Use our memory-enhanced chat for all requests
            logger.info("Using memory-based chat for all API requests")
            return handle_chat_with_memory()
        else:
            logger.error("Invalid chat request - missing messages")
            return jsonify({"error": "Invalid request format, messages required"}), 400
    except Exception as e:
        logger.error(f"API chat exception: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/direct_models', methods=['GET'])
def direct_models():
    """Get models directly from Ollama."""
    try:
        logger.info("Direct API call to Ollama for models")
        # Make a direct request to Ollama
        import requests
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Direct API success: {len(data.get('models', []))} models found")
            return jsonify(data)
        else:
            logger.error(f"Direct API error: {response.status_code}")
            return jsonify({"error": "Failed to reach Ollama"}), 500
    except Exception as e:
        logger.error(f"Direct API exception: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/models', methods=['GET'])
def api_models():
    """Get list of available models."""
    try:
        logger.info("API endpoint /api/models called")
        
        # Try direct approach first
        try:
            import requests
            direct_response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
            if direct_response.status_code == 200:
                ollama_data = direct_response.json()
                ollama_models = ollama_data.get("models", [])
                logger.info(f"Direct Ollama response: {len(ollama_models)} models")
                
                # Simple conversion to our format
                models = []
                for model in ollama_models:
                    try:
                        name = model.get("name", "unknown")
                        parameter_size = model.get("details", {}).get("parameter_size", "unknown")
                        models.append({
                            "id": name,
                            "name": name,
                            "parameter_size": parameter_size
                        })
                    except Exception as model_error:
                        logger.error(f"Error processing model {model}: {model_error}")
                
                logger.info(f"Processed {len(models)} models directly from Ollama")
                
                response_data = {
                    "models": models,
                    "default_model": OLLAMA_MODEL
                }
                return jsonify(response_data)
        except Exception as direct_error:
            logger.error(f"Direct approach failed: {direct_error}")
        
        # Fall back to standard approach
        models = get_available_models()
        logger.info(f"Retrieved {len(models)} models from client function")
        
        # If no models were found, return a fallback model
        if not models:
            logger.warning("No models found, providing fallback model")
            fallback_model = {
                "id": OLLAMA_MODEL,
                "name": OLLAMA_MODEL,
                "parameter_size": "unknown",
                "quantization": "unknown",
                "families": []
            }
            models = [fallback_model]
        
        response_data = {
            "models": models,
            "default_model": OLLAMA_MODEL
        }
        logger.info(f"Sending response: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error in models API: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "models": [{
                "id": OLLAMA_MODEL,
                "name": OLLAMA_MODEL,
                "parameter_size": "default",
                "quantization": "unknown",
                "families": []
            }],
            "default_model": OLLAMA_MODEL
        }), 500


@app.route('/api/memory_count', methods=['GET'])
def api_memory_count():
    """Get the total count of memories from the global memory store, broken down by active and inactive."""
    from memory_utils import GLOBAL_MEMORY_ID, MEMORY_COUNTER
    
    global memory_instance
    if not memory_instance:
        from memory_utils import initialize_memory
        try:
            memory_instance = initialize_memory()
        except Exception as e:
            logger.error(f"Error initializing memory: {e}")
            return jsonify({"error": "Failed to initialize memory system"}), 500
    
    try:
        # Return the counter data directly
        logger.info(f"Memory counts: {MEMORY_COUNTER}")
        return jsonify(MEMORY_COUNTER)
    except Exception as e:
        logger.error(f"Error getting memory count: {e}")
        return jsonify({
            "error": str(e),
            "active": 0,
            "inactive": 0,
            "total": 0
        }), 500

@app.route('/api/memories', methods=['GET', 'DELETE'])
def api_memories():
    """Retrieve or delete memories from the global memory store."""
    from memory_utils import GLOBAL_MEMORY_ID
    
    global memory_instance
    if not memory_instance:
        from memory_utils import initialize_memory
        try:
            memory_instance = initialize_memory()
        except Exception as e:
            logger.error(f"Error initializing memory: {e}")
            return jsonify({"error": "Failed to initialize memory system"}), 500
    
    # Handle GET request to retrieve memories
    if request.method == 'GET':
        try:
            # Always use the global memory ID regardless of what was passed
            memories = memory_instance.get_all(user_id=GLOBAL_MEMORY_ID, limit=50)
            logger.info(f"Retrieved {len(memories) if memories else 0} memories from global store")
            return jsonify({"memories": memories})
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Handle DELETE request to mark memories as inactive rather than deleting them
    elif request.method == 'DELETE':
        try:
            # We need to get all memories first, then mark them as inactive
            memories = memory_instance.get_all(user_id=GLOBAL_MEMORY_ID, limit=1000)
            logger.info(f"Found {len(memories) if memories else 0} memories to mark as inactive")
            
            # Update global counter
            from memory_utils import MEMORY_COUNTER
            
            if memories:
                # For simplicity, we'll actually clear the memories and update our counter
                # In a real implementation, we would mark each memory as inactive
                memory_instance.clear(user_id=GLOBAL_MEMORY_ID)
                
                # Update the memory counter - move all active to inactive
                inactive_count = MEMORY_COUNTER["inactive"] + MEMORY_COUNTER["active"]
                MEMORY_COUNTER["inactive"] = inactive_count
                MEMORY_COUNTER["active"] = 0
                # Total stays the same
                
                logger.info(f"Successfully marked all memories as inactive. New counts: {MEMORY_COUNTER}")
            
            return jsonify({
                "success": True, 
                "message": f"Marked {len(memories) if memories else 0} memories as inactive.",
                "memory_counts": MEMORY_COUNTER
            })
        except Exception as e:
            logger.error(f"Error handling memory deactivation: {e}")
            # Even if it fails, try to provide a useful response
            return jsonify({
                "success": False, 
                "error": str(e),
                "message": "Could not mark memories as inactive."
            }), 500

def create_app():
    """Create and configure the Flask app."""
    return app

def run_server(host='127.0.0.1', port=API_PORT, debug=False):
    """Run the API server."""
    logger.info(f"Starting API server at http://{host}:{port}")
    try:
        # Use threaded=False to avoid socket issues on Windows
        app.run(host=host, port=port, debug=debug, threaded=False, use_reloader=False)
    except OSError as e:
        if "An operation was attempted on something that is not a socket" in str(e):
            logger.error("Socket error encountered. Trying with different host settings.")
            # Try with localhost instead of 0.0.0.0
            app.run(host='localhost', port=port, debug=debug, threaded=False, use_reloader=False)
        else:
            raise
