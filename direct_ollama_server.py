#!/usr/bin/env python3
"""
Simple direct Ollama API server (no mem0 integration) for testing
"""

import json
import logging
import requests
from flask import Flask, request, jsonify, render_template_string

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

OLLAMA_HOST = "http://localhost:11434"
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Direct Ollama Test</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        h1 {
            color: #336b87;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }
        pre {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }
        button {
            background-color: #336b87;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover {
            background-color: #265a76;
        }
        #modelsContainer, #testResultContainer {
            margin-top: 20px;
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <h1>Direct Ollama API Test</h1>
    <p>This page tests direct connection to Ollama API at <span id="ollamaHost">${ollamaHost}</span></p>
    
    <button id="testConnectionBtn">Test Connection</button>
    <button id="fetchModelsBtn">Fetch Models</button>
    
    <div id="modelsContainer">
        <h2>Available Models</h2>
        <p>Click "Fetch Models" to see available models.</p>
    </div>
    
    <div id="testResultContainer">
        <h2>Test Results</h2>
        <p>Click "Test Connection" to check the Ollama API connection.</p>
    </div>
    
    <script>
        const ollamaHost = document.getElementById('ollamaHost').textContent;
        const testConnectionBtn = document.getElementById('testConnectionBtn');
        const fetchModelsBtn = document.getElementById('fetchModelsBtn');
        const modelsContainer = document.getElementById('modelsContainer');
        const testResultContainer = document.getElementById('testResultContainer');
        
        // Test basic Ollama connection
        testConnectionBtn.addEventListener('click', async () => {
            testResultContainer.innerHTML = '<h2>Test Results</h2><p>Testing connection...</p>';
            
            try {
                const response = await fetch('/api/test_connection');
                const data = await response.json();
                
                console.log('Connection test result:', data);
                
                let resultHtml = '<h2>Test Results</h2>';
                if (data.success) {
                    resultHtml += '<p style="color: green">✓ Connection successful!</p>';
                    resultHtml += `<pre>${JSON.stringify(data.result, null, 2)}</pre>`;
                } else {
                    resultHtml += `<p style="color: red">✗ Connection failed: ${data.error}</p>`;
                }
                
                testResultContainer.innerHTML = resultHtml;
            } catch (error) {
                console.error('Error testing connection:', error);
                testResultContainer.innerHTML = `<h2>Test Results</h2><p style="color: red">✗ Error: ${error.message}</p>`;
            }
        });
        
        // Fetch models
        fetchModelsBtn.addEventListener('click', async () => {
            modelsContainer.innerHTML = '<h2>Available Models</h2><p>Loading models...</p>';
            
            try {
                const response = await fetch('/api/models');
                const data = await response.json();
                
                console.log('Models data:', data);
                
                let modelsHtml = '<h2>Available Models</h2>';
                if (data.models && data.models.length > 0) {
                    modelsHtml += '<ul>';
                    data.models.forEach(model => {
                        const size = model.size ? `${(model.size / 1024 / 1024).toFixed(1)} MB` : 'unknown size';
                        const paramSize = model.details?.parameter_size || 'unknown params';
                        modelsHtml += `<li><strong>${model.name}</strong> (${paramSize}, ${size})</li>`;
                    });
                    modelsHtml += '</ul>';
                } else {
                    modelsHtml += '<p>No models found.</p>';
                }
                
                modelsContainer.innerHTML = modelsHtml;
            } catch (error) {
                console.error('Error fetching models:', error);
                modelsContainer.innerHTML = `<h2>Available Models</h2><p style="color: red">✗ Error: ${error.message}</p>`;
            }
        });
    </script>
</body>
</html>
"""

app = Flask(__name__)

@app.route('/')
def index():
    """Serve the index page."""
    return render_template_string(INDEX_HTML.replace('${ollamaHost}', OLLAMA_HOST))

@app.route('/api/test_connection')
def test_connection():
    """Test connection to Ollama API."""
    logger.info(f"Testing connection to Ollama at {OLLAMA_HOST}")
    
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        
        if response.status_code == 200:
            logger.info("Connection test successful")
            return jsonify({
                "success": True,
                "status_code": response.status_code,
                "result": response.json()
            })
        else:
            logger.error(f"Connection test failed with status code {response.status_code}")
            return jsonify({
                "success": False,
                "status_code": response.status_code,
                "error": f"Received status code {response.status_code}"
            })
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection test failed with error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route('/api/models')
def get_models():
    """Get models from Ollama API."""
    logger.info(f"Fetching models from Ollama at {OLLAMA_HOST}")
    
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Retrieved models: {json.dumps(data)[:200]}...")
            return jsonify(data)
        else:
            logger.error(f"Failed to get models: {response.status_code}")
            return jsonify({
                "error": f"Failed to get models: status code {response.status_code}"
            }), response.status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching models: {e}")
        return jsonify({
            "error": f"Error fetching models: {str(e)}"
        }), 500

if __name__ == "__main__":
    logger.info("Starting direct Ollama test server on http://localhost:5000")
    app.run(host='localhost', port=5000, debug=True, threaded=False)
