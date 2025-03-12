# mem0-Ollama Integration

This repository contains an integration between [mem0](https://mem0.ai) (the memory layer for AI), [Ollama](https://ollama.ai) (local LLM runtime), and [Qdrant](https://qdrant.tech) (vector database) for building AI applications with long-term memory.

## Features

- Web-based chat interface with memory capabilities
- Integration with Ollama models for local LLM inference
- Persistent memory storage using Qdrant vector database
- Multiple memory modes: search, user, session, none
- Support for structured output formats
- Easy setup with provided scripts

## Quick Start

1. **Prerequisites**
   - [Docker](https://www.docker.com/products/docker-desktop/) for running Qdrant
   - [Ollama](https://ollama.ai/) for running LLMs locally
   - Python 3.9+ with pip

2. **Automated Setup**
   - On Windows:
     ```powershell
     .\setup-mem0-integration.ps1
     ```
   - On macOS/Linux:
     ```bash
     ./setup-mem0-integration.sh
     ```

3. **Start the Web Interface**
   ```bash
   python main.py
   ```

4. **Open the Web Interface**
   - Navigate to [http://localhost:8000](http://localhost:8000) in your browser

## Manual Setup

If you prefer to set up the components manually:

1. **Start Qdrant in Docker**
   ```bash
   docker run -d --name qdrant-mem0 -p 6333:6333 -p 6334:6334 qdrant/qdrant
   ```

2. **Install mem0**
   ```bash
   pip install mem0ai
   ```

3. **Set Up Ollama**
   - Make sure Ollama is running
   - Pull a model:
     ```bash
     ollama pull llama3
     ```

4. **Start the Server**
   ```bash
   python main.py
   ```

## Configuration

Edit `config.py` to change default settings:

- `OLLAMA_HOST`: URL for Ollama API (default: "http://localhost:11434")
- `OLLAMA_MODEL`: Default model to use (default: "llama3")
- `QDRANT_HOST`: URL for Qdrant (default: "http://localhost:6333")
- `QDRANT_COLLECTION`: Collection name for memories (default: "ollama_memories")
- `API_PORT`: Port for web interface (default: 8000)

## Files

- `main.py`: Main entry point for the web interface
- `api.py`: API server implementation
- `memory_utils.py`: Memory management utilities
- `ollama_client.py`: Ollama API client
- `templates.py`: HTML templates for web interface
- `config.py`: Configuration settings
- `docker-compose.yml`: Docker configuration for Qdrant
- `setup-mem0-integration.ps1`: Windows setup script
- `setup-mem0-integration.sh`: Unix setup script

## Advanced Usage

For more advanced usage, including API usage and direct examples, see [README-advanced.md](README-advanced.md).

## Memory Modes

- **Search**: Retrieves memories relevant to the current message
- **User**: Retrieves all memories for the current user
- **Session**: Maintains memories for the current conversation session
- **None**: Disables memory functionality

## License

MIT License
