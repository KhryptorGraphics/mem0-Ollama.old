#!/usr/bin/env python3
"""
mem0 + Ollama + Qdrant Integration Example

This script demonstrates how to integrate mem0 with Ollama (for both embeddings and LLM)
and Qdrant (for vector storage), creating a persistent memory system for conversations.
"""

import os
import sys
import argparse
import requests
import logging
import json
import threading
import time
from flask import Flask, request, jsonify, Response, render_template_string, send_from_directory
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Check if mem0 is installed
try:
    from mem0 import Memory
except ImportError:
    print("The 'mem0ai' package is not installed. Installing it now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mem0ai"])
    from mem0 import Memory

# Check if Flask is installed
try:
    from flask import Flask
except ImportError:
    print("The 'flask' package is not installed. Installing it now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
    from flask import Flask, request, jsonify, Response, render_template_string, send_from_directory

# Configuration defaults
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3"  # Default model
QDRANT_HOST = "http://localhost:6333"
QDRANT_COLLECTION = "ollama_memories"
API_PORT = 8000  # Default port for API server

# Models with their embedding dimensions
MODEL_DIMENSIONS = {
    "llama3": 4096,
    "mistral": 4096,
    "gemma": 4096,
    "phi3": 2560,
    "qwen2": 4096,
    "nomic-embed-text": 768,
    "snowflake-arctic-embed": 1024,
    "all-minilm": 384,
    "llava": 4096
}

# Structured output formats
OUTPUT_FORMAT = None  # Default is None (no structured output)
OUTPUT_FORMATS = {
    "none": None,
    "json": "json",
    "sentiment": {
        "type": "object",
        "properties": {
            "sentiment": {
                "type": "string",
                "enum": ["positive", "neutral", "negative"]
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },
            "explanation": {
                "type": "string"
            }
        },
        "required": ["sentiment", "confidence", "explanation"]
    },
    "summary": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string"
            },
            "key_points": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        "required": ["summary", "key_points"]
    },
    "action_items": {
        "type": "object",
        "properties": {
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"]
                        }
                    },
                    "required": ["action", "priority"]
                }
            }
        },
        "required": ["action_items"]
    }
}

# HTML templates for the web interface
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mem0 + Ollama Chat</title>
    <style>
        :root {
            --primary: #4a6fa5;
            --secondary: #336b87;
            --background: #f5f5f5;
            --surface: #ffffff;
            --text: #333333;
            --error: #b71c1c;
            --success: #43a047;
            --user-msg: #e3f2fd;
            --assistant-msg: #f1f8e9;
            --memory-bg: #fffde7;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text);
            background-color: var(--background);
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }
        
        header {
            background-color: var(--primary);
            color: white;
            padding: 1rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        main {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 1rem;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
            box-sizing: border-box;
        }
        
        .chat-container {
            display: flex;
            flex: 1;
            gap: 1rem;
        }
        
        .chat-main {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--surface);
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .sidebar {
            width: 250px;
            background: var(--surface);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .chat-messages {
            flex: 1;
            padding: 1rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .message {
            padding: 1rem;
            border-radius: 8px;
            max-width: 80%;
            word-break: break-word;
        }
        
        .user {
            align-self: flex-end;
            background-color: var(--user-msg);
            border-bottom-right-radius: 0;
        }
        
        .assistant {
            align-self: flex-start;
            background-color: var(--assistant-msg);
            border-bottom-left-radius: 0;
        }
        
        .system {
            align-self: center;
            background-color: #f0f0f0;
            color: #666;
            font-style: italic;
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
        }
        
        .chat-form {
            display: flex;
            padding: 1rem;
            gap: 0.5rem;
            background-color: var(--surface);
            border-top: 1px solid #eee;
        }
        
        .chat-input {
            flex: 1;
            padding: 0.75rem;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 1rem;
        }
        
        button {
            background-color: var(--primary);
            color: white;
            border: none;
            border-radius: 4px;
            padding: 0.5rem 1rem;
            font-size: 1rem;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        button:hover {
            background-color: var(--secondary);
        }
        
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        
        .model-selector, .memory-controls, .format-selector {
            margin-bottom: 1.5rem;
        }
        
        select, input {
            width: 100%;
            padding: 0.5rem;
            margin-top: 0.5rem;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }
        
        .sidebar h3 {
            margin-top: 0;
            color: var(--primary);
            border-bottom: 1px solid #eee;
            padding-bottom: 0.5rem;
        }
        
        .memory-item {
            background-color: var(--memory-bg);
            padding: 0.75rem;
            border-radius: 4px;
            margin-bottom: 0.5rem;
            font-size: 0.85rem;
            border-left: 3px solid var(--secondary);
        }
        
        .memories-container {
            max-height: 300px;
            overflow-y: auto;
            margin-top: 1rem;
        }
        
        .loading {
            text-align: center;
            padding: 1rem;
            font-style: italic;
            color: #666;
        }
        
        pre {
            background-color: #f5f5f5;
            padding: 0.5rem;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 0.9rem;
        }
        
        code {
            font-family: 'Courier New', Courier, monospace;
            background-color: #f5f5f5;
            padding: 0.1rem 0.3rem;
            border-radius: 3px;
            font-size: 0.9rem;
        }
        
        .error {
            color: var(--error);
            padding: 1rem;
            background-color: #ffebee;
            border-radius: 4px;
            margin: 1rem 0;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .chat-container {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                order: 2;
            }
            
            .chat-main {
                order: 1;
            }
            
            .message {
                max-width: 90%;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>mem0 + Ollama Chat Interface</h1>
    </header>
    
    <main>
        <div class="chat-container">
            <div class="chat-main">
                <div class="chat-messages" id="chatMessages">
                    <div class="message system">
                        Welcome to mem0 + Ollama Chat! This interface connects to the Ollama API with mem0 memory integration.
                    </div>
                </div>
                
                <form class="chat-form" id="chatForm">
                    <input type="text" class="chat-input" id="messageInput" placeholder="Type your message..." required>
                    <button type="submit" id="sendButton">Send</button>
                </form>
            </div>
            
            <div class="sidebar">
                <div class="model-selector">
                    <h3>Model Settings</h3>
                    <label for="modelSelect">Select Model:</label>
                    <select id="modelSelect"></select>
                </div>
                
                <div class="format-selector">
                    <label for="formatSelect">Output Format:</label>
                    <select id="formatSelect">
                        <option value="none">None</option>
                        <option value="json">JSON</option>
                        <option value="sentiment">Sentiment Analysis</option>
                        <option value="summary">Summary</option>
                        <option value="action_items">Action Items</option>
                    </select>
                </div>
                
                <div class="memory-controls">
                    <h3>Memory Settings</h3>
                    <label for="modeSelect">Memory Mode:</label>
                    <select id="modeSelect">
                        <option value="search">Search</option>
                        <option value="user">User</option>
                        <option value="session">Session</option>
                        <option value="none">None</option>
                    </select>
                    
                    <div style="margin-top: 1rem;">
                        <button type="button" id="clearMemoriesBtn" class="secondary-btn">Clear Memories</button>
                    </div>
                </div>
                
                <div>
                    <h3>Recent Memories</h3>
                    <div class="memories-container" id="memoriesContainer">
                        <div class="memory-item">No memories yet.</div>
                    </div>
                </div>
            </div>
        </div>
    </main>
    
    <script>
        // Global state
        let conversationId = null;
        let userId = `web_user_${Date.now().toString(36)}`;
        
        // DOM elements
        const chatMessages = document.getElementById('chatMessages');
        const chatForm = document.getElementById('chatForm');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const modelSelect = document.getElementById('modelSelect');
        const formatSelect = document.getElementById('formatSelect');
        const modeSelect = document.getElementById('modeSelect');
        const clearMemoriesBtn = document.getElementById('clearMemoriesBtn');
        const memoriesContainer = document.getElementById('memoriesContainer');
        
        // Fetch available models
        async function fetchModels() {
            try {
                const response = await fetch('/api/models');
                const data = await response.json();
                
                // Clear select options
                modelSelect.innerHTML = '';
                
                // Add models to select
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.name;
                    option.textContent = `${model.name} (${model.parameter_size})`;
                    modelSelect.appendChild(option);
                });
                
                // Set default model
                if (data.default_model) {
                    modelSelect.value = data.default_model;
                }
                
                // If no models available
                if (data.models.length === 0) {
                    const option = document.createElement('option');
                    option.value = "llama3";
                    option.textContent = "llama3 (default)";
                    modelSelect.appendChild(option);
                }
            } catch (error) {
                console.error('Error fetching models:', error);
                addSystemMessage('Failed to load available models. Using default model.');
            }
        }
        
        // Add a message to the chat
        function addMessage(content, role) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', role);
            
            // Convert markdown-like syntax
            let formattedContent = content
                .replace(/```(.*?)```/gs, '<pre>$1</pre>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                .replace(/\*([^*]+)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>');
            
            messageDiv.innerHTML = formattedContent;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Add a system message
        function addSystemMessage(content) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', 'system');
            messageDiv.textContent = content;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Add a loading indicator
        function addLoadingIndicator() {
            const loadingDiv = document.createElement('div');
            loadingDiv.classList.add('loading');
            loadingDiv.id = 'loadingIndicator';
            loadingDiv.textContent = 'Thinking...';
            chatMessages.appendChild(loadingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Remove loading indicator
        function removeLoadingIndicator() {
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.remove();
            }
        }
        
        // Send a message to the API
        async function sendMessage(content) {
            try {
                addLoadingIndicator();
                sendButton.disabled = true;
                
                const payload = {
                    messages: [
                        { role: 'user', content }
                    ],
                    model: modelSelect.value,
                    format: formatSelect.value === 'none' ? null : formatSelect.value,
                    conversation_id: conversationId
                };
                
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });
                
                if (!response.ok) {
                    throw new Error(`API error: ${response.status}`);
                }
                
                const data = await response.json();
                
                // Update conversation ID
                conversationId = data.conversation_id;
                
                // Get the assistant's response
                const assistantContent = data.choices[0].message.content;
                
                // Update memories display
                updateMemoriesDisplay(data.memories || []);
                
                removeLoadingIndicator();
                addMessage(assistantContent, 'assistant');
                
            } catch (error) {
                console.error('Error sending message:', error);
                removeLoadingIndicator();
                addSystemMessage(`Error: ${error.message}`);
            } finally {
                sendButton.disabled = false;
            }
        }
        
        // Update the memories display
        function updateMemoriesDisplay(memories) {
            memoriesContainer.innerHTML = '';
            
            if (memories.length === 0) {
                const memoryItem = document.createElement('div');
                memoryItem.classList.add('memory-item');
                memoryItem.textContent = 'No memories found.';
                memoriesContainer.appendChild(memoryItem);
                return;
            }
            
            memories.forEach(memory => {
                const memoryItem = document.createElement('div');
                memoryItem.classList.add('memory-item');
                memoryItem.textContent = memory.memory || memory;
                memoriesContainer.appendChild(memoryItem);
            });
        }
        
        // Fetch user memories
        async function fetchMemories() {
            try {
                const response = await fetch(`/api/memories?user_id=${userId}`);
                const data = await response.json();
                
                updateMemoriesDisplay(data.memories || []);
            } catch (error) {
                console.error('Error fetching memories:', error);
            }
        }
        
        // Clear user memories
        async function clearMemories() {
            try {
                const response = await fetch(`/api/memories?user_id=${userId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    addSystemMessage('All memories have been cleared.');
                    updateMemoriesDisplay([]);
                } else {
                    throw new Error('Failed to clear memories.');
                }
            } catch (error) {
                console.error('Error clearing memories:', error);
                addSystemMessage(`Error: ${error.message}`);
            }
        }
        
        // Event Listeners
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (message) {
                addMessage(message, 'user');
                sendMessage(message);
                messageInput.value = '';
            }
        });
        
        clearMemoriesBtn.addEventListener('click', clearMemories);
        
        // Initialize the app
        function init() {
            fetchModels();
            fetchMemories();
            addSystemMessage(`Memory mode: ${modeSelect.value}`);
        }
        
        // Start the application
        init();
    </script>
</body>
</html>
"""

def get_available_models():
    """Get available models from Ollama."""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags")
        if response.status_code != 200:
            logger.error(f"Failed to get models: {response.text}")
            return []
        
        models = response.json().get("models", [])
        model_details = []
        for model in models:
            name = model.get("name")
            details = {
                "id": name,
                "name": name,
                "size": model.get("size", 0),
                "parameter_size": model.get("details", {}).get("parameter_size", "unknown"),
                "quantization": model.get("details", {}).get("quantization_level", "unknown"),
                "families": model.get("details", {}).get("families", [])
            }
            model_details.append(details)
        
        return model_details
    except Exception as e:
        logger.error(f"Error while fetching models: {e}")
        return []

def check_ollama():
    """Check if Ollama is running and has the required model."""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags")
        if response.status_code != 200:
            logger.error(f"Ollama is not running or not responding correctly at {OLLAMA_HOST}")
            return False
        
        # Check if the model is available
        models = response.json().get("models", [])
        model_names = [model.get("name") for model in models]
        
        if OLLAMA_MODEL not in model_names and f"{OLLAMA_MODEL}:latest" not in model_names:
            logger.warning(f"Model {OLLAMA_MODEL} not found in Ollama. Available models: {', '.join(model_names)}")
            logger.info(f"You may need to pull the model using: ollama pull {OLLAMA_MODEL}")
            return False
            
        return True
    except requests.RequestException as e:
        logger.error(f"Error connecting to Ollama: {e}")
        return False

def check_qdrant():
    """Check if Qdrant is running."""
    try:
        response = requests.get(f"{QDRANT_HOST}/dashboard/")
        return response.status_code == 200
    except requests.RequestException:
        try:
            # Try the collections endpoint if dashboard is not available
            response = requests.get(f"{QDRANT_HOST}/collections")
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Error connecting to Qdrant: {e}")
            return False

def initialize_memory(
    ollama_model: str = OLLAMA_MODEL,
    embed_model: Optional[str] = None,
    unified_memory: bool = True
) -> Memory:
    """
    Initialize the Memory object with Ollama and Qdrant configurations.
    
    Args:
        ollama_model: Ollama model to use for LLM
        embed_model: Ollama model to use for embeddings (defaults to same as ollama_model)
        unified_memory: Whether to use unified memory for all models
    
    Returns:
        Memory object configured with Ollama and Qdrant
    """
    if embed_model is None:
        # For embedding, prefer specialized embedding models if available
        try:
            embed_check = requests.get(f"{OLLAMA_HOST}/api/tags")
            available_models = [m.get("name") for m in embed_check.json().get("models", [])]
            
            if "nomic-embed-text" in available_models or "nomic-embed-text:latest" in available_models:
                embed_model = "nomic-embed-text"
                logger.info("Using nomic-embed-text model for embeddings")
            elif "snowflake-arctic-embed" in available_models or "snowflake-arctic-embed:latest" in available_models:
                embed_model = "snowflake-arctic-embed"
                logger.info("Using snowflake-arctic-embed model for embeddings")
            else:
                embed_model = ollama_model
                logger.info(f"Using {ollama_model} for embeddings (specialized embedding models not found)")
        except Exception:
            embed_model = ollama_model
            logger.info(f"Using {ollama_model} for embeddings")
    
    # Determine embedding dimensions based on model
    embed_dims = MODEL_DIMENSIONS.get(embed_model.split(':')[0], 768)
    
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": QDRANT_COLLECTION,
                "host": QDRANT_HOST.replace("http://", "").replace("https://", "").split(":")[0],
                "port": int(QDRANT_HOST.split(":")[-1]) if ":" in QDRANT_HOST else 6333,
                "embedding_model_dims": embed_dims,
                # "unified_memory" is not a supported field, removed
            },
        },
        "llm": {
            "provider": "ollama",
            "config": {
                "model": ollama_model,
                "temperature": 0.7,
                "max_tokens": 2000,
                "ollama_base_url": OLLAMA_HOST,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": embed_model,
                "ollama_base_url": OLLAMA_HOST,
                "embedding_dims": embed_dims,
            },
        },
    }
    
    logger.info("Initializing Memory with Ollama and Qdrant...")
    try:
        return Memory.from_config(config)
    except Exception as e:
        logger.error(f"Error initializing Memory: {e}")
        raise

def chat_with_memories(
    memory: Memory, 
    message: str, 
    user_id: str = "default_user", 
    memory_mode: str = "search", 
    output_format: Optional[Union[str, Dict]] = None,
    model: Optional[str] = None
) -> Dict:
    """
    Process a chat message, search for relevant memories, and generate a response.
    
    Args:
        memory: The Memory object
        message: User's message
        user_id: User ID for memory storage
        memory_mode: Memory mode to use ("search", "user", "session", "none")
        output_format: Optional format for structured output
        model: Optional model to use for this specific request
    
    Returns:
        Dict with response data including:
        - content: The assistant's response
        - memories: Any relevant memories found
        - model: The model used for the response
    """
    logger.info(f"Processing chat for user {user_id} with model {model or OLLAMA_MODEL}")
    
    # Use specified model or fall back to global default
    model_to_use = model or OLLAMA_MODEL
    
    relevant_memories = []
    memories_str = "Memory search disabled."
    
    try:
        if memory_mode == "search":
            # Retrieve relevant memories
            search_results = memory.search(query=message, user_id=user_id, limit=5)
            relevant_memories = search_results.get("results", [])
            
            if relevant_memories:
                logger.info(f"Found {len(relevant_memories)} relevant memories")
                memories_str = "\n".join(f"- {entry['memory']}" for entry in relevant_memories)
            else:
                logger.info("No relevant memories found")
                memories_str = "No relevant memories found."
        elif memory_mode == "user":
            # Get all memories for the user
            user_memories = memory.get_all(user_id=user_id, limit=5)
            if user_memories:
                logger.info(f"Found {len(user_memories)} user memories")
                memories_str = "\n".join(f"- {entry}" for entry in user_memories)
                relevant_memories = [{"memory": memory} for memory in user_memories]
            else:
                logger.info("No user memories found")
                memories_str = "No user memories found."
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}")
        memories_str = "Error retrieving memories."
    
    # Generate response using Ollama
    system_prompt = f"""You are a helpful AI assistant with memory capabilities.
Answer the question based on the user's query and relevant memories.

User Memories:
{memories_str}

Please be conversational and friendly in your responses.
If referring to a memory, try to naturally incorporate it without explicitly stating 'According to your memory...'"""
    
    try:
        # Create conversation history for context
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        # Prepare request payload based on whether structured output is requested
        request_payload = {
            "model": model_to_use,
            "stream": False,
            "options": {
                "temperature": 0.7
            }
        }
        
        # For chat API (preferred when available)
        if output_format:
            # Add format parameter for structured output
            request_payload["messages"] = messages
            request_payload["format"] = output_format
            api_url = f"{OLLAMA_HOST}/api/chat"
            
            logger.info(f"Using structured output format: {output_format if isinstance(output_format, str) else 'custom JSON schema'}")
        else:
            # For older versions or when structured output not needed
            api_url = f"{OLLAMA_HOST}/api/chat"
            request_payload["messages"] = messages
        
        # Make the API request
        logger.info(f"Sending request to Ollama API: {api_url}")
        api_response = requests.post(api_url, json=request_payload)
        
        if api_response.status_code == 200:
            result = api_response.json()
            
            if "message" in result and "content" in result["message"]:
                assistant_response = result["message"]["content"]
            else:
                assistant_response = result.get("response", "I couldn't generate a response.")
            
            # Create new memories from the conversation
            if memory_mode != "none":
                memory.add(
                    message=message,
