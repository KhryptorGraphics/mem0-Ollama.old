# mem0-Ollama Implementation Details

This document provides a comprehensive overview of the web chat interface with mem0 integration for Ollama implementation.

## 1. System Architecture

The implementation consists of the following key components:

### Core Components
- **Web Chat Interface**: A responsive browser-based UI for interacting with the Ollama model
- **Flask API Server**: Backend server that handles requests between frontend and model
- **mem0 Integration**: Vector database for managing memories and context
- **Ollama Connection**: Integration with Ollama for local LLM inference

### Data Flow
1. User sends message through web interface
2. Flask API receives request
3. System retrieves relevant memories from mem0
4. Context built with memories and chat history
5. Request forwarded to Ollama
6. Response streamed back to web interface
7. Interactions stored in mem0 for future context

## 2. Key Files and Their Functions

### `api.py`
- Implements Flask server and routes
- Handles chat and memory API endpoints
- Manages WebSocket connections for streaming
- Proxies requests to Ollama for Docker support

### `memory_utils.py`
- Implements the `MemoryManager` class
- Handles vector storage and retrieval
- Manages memory states (active/inactive)
- Provides metadata handling for memories

### `templates.py`
- Contains HTML/CSS/JS for web interface
- Implements responsive chat UI
- Provides memory visualization components
- Contains model selection interface

### `ollama_client.py`
- HTTP client for Ollama API
- Formats prompts for different models
- Handles streaming responses
- Manages model loading and inference

### `main.py`
- Application entry point
- Configuration loading
- Server initialization
- Command-line interface

### `config.py`
- Central configuration management
- Environment variable integration
- Default system prompts
- Logging configuration

### `docker-compose.yml`
- Multi-container definition
- Service configuration
- Volume mapping
- Network configuration

## 3. Key Features

### Memory Management
- **Context Awareness**: System maintains awareness of previous conversations
- **Active/Inactive States**: Memories can be marked active or inactive based on relevance
- **Vector Similarity**: Retrieves memories based on semantic similarity
- **Visualization**: UI displays which memories are being used for context

### Web Interface
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Streaming**: Responses appear in real-time as they're generated
- **Model Selection**: Users can select from available Ollama models
- **System Prompt Customization**: Configurable system instructions

### Ollama Integration
- **Local LLM Inference**: No data sent to external APIs
- **Multi-model Support**: Works with any model available in Ollama
- **Streaming Generation**: Real-time token streaming
- **Docker Support**: Proxy endpoints for container networking

## 4. Setup and Deployment

### Standard Setup
- Clone repository
- Install dependencies
- Configure environment variables
- Run Flask server
- Access web interface

### Docker Deployment
- Build Docker images
- Launch with docker-compose
- Services automatically connected
- Persistent storage through volumes

## 5. Technical Implementation Details

### Memory Retrieval Algorithm
1. Embed user query into vector space
2. Search mem0 for similar vectors
3. Rank results by similarity score
4. Select top N memories
5. Mark selected memories as "active"
6. Include active memories in context

### Response Generation
1. Combine system prompt, active memories, and chat history
2. Format context for Ollama model
3. Send request to Ollama API
4. Stream tokens back to client
5. Update memory store with new interaction

### Memory States
- **Active**: Currently being used for context
- **Inactive**: Stored but not currently used
- **Archived**: Not used for regular retrieval but available for explicit search

## 6. Future Improvements
- Memory editing capabilities
- Enhanced vector search algorithms
- Multi-user support
- Fine-tuning interface for custom models
- Advanced memory management controls

---

This implementation provides a powerful, locally-hosted chat interface that combines the strengths of Ollama models with the context management capabilities of the mem0 vector database.
