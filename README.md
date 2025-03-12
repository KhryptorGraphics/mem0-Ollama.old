# mem0 + Ollama Integration

This project demonstrates the integration of [mem0](https://github.com/mem0ai/mem0) with [Ollama](https://ollama.ai/) and [Qdrant](https://qdrant.tech/) to create a chat application with persistent memory capabilities.

## Features

- Web-based chat interface
- Integration with Ollama for LLM inference
- Persistent memory using Qdrant vector database
- Structured output formats for sentiment analysis, summaries, etc.
- Multiple memory modes (search, user, session)

## Project Structure

The project is organized into modular components:

- `main.py` - Entry point for the application
- `config.py` - Configuration settings and constants
- `templates.py` - HTML and frontend code
- `ollama_client.py` - Functions for interacting with Ollama API
- `memory_utils.py` - Memory management functionality
- `api.py` - Flask API server with routes

## Requirements

- Python 3.8+
- Ollama running locally (or on a remote server)
- Qdrant running locally (or on a remote server)
- mem0 Python package
- Flask

## Installation

1. Clone this repository

2. Install required packages:
   ```
   pip install mem0ai flask requests
   ```

3. Ensure Ollama is running and has the required models:
   ```
   # Start Ollama (default: localhost:11434)
   ollama serve

   # Pull required models
   ollama pull llama3
   ollama pull nomic-embed-text  # optional, for better embeddings
   ```

4. Ensure Qdrant is running:
   ```
   # Using Docker (recommended)
   docker run -d -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant
   ```

## Usage

Run the application:

```
python main.py
```

Customize with command-line options:

```
python main.py --help
usage: main.py [-h] [--ollama-host OLLAMA_HOST] [--ollama-model OLLAMA_MODEL]
               [--qdrant-host QDRANT_HOST] [--embed-model EMBED_MODEL]
               [--port PORT] [--debug]

Start the mem0 + Ollama integration server

optional arguments:
  -h, --help            show this help message and exit
  --ollama-host OLLAMA_HOST
                        Ollama API host (default: http://localhost:11434)
  --ollama-model OLLAMA_MODEL
                        Ollama model to use (default: llama3)
  --qdrant-host QDRANT_HOST
                        Qdrant host (default: http://localhost:6333)
  --embed-model EMBED_MODEL
                        Model to use for embeddings (defaults to ollama-model if not specified)
  --port PORT           Port for the API server (default: 8000)
  --debug               Run in debug mode
```

## Web Interface

Once running, open your browser to http://localhost:8000 to access the chat interface.

The interface provides:
- Model selection
- Output format selection
- Memory mode selection
- Memory clearing functionality

## API Endpoints

- `GET /` - Web interface
- `GET /api/models` - Get available models
- `POST /api/chat` - Send chat message
- `GET /api/memories` - Retrieve memories for a user
- `DELETE /api/memories` - Clear memories for a user

## Memory Modes

- **Search**: Retrieve relevant memories based on the current query
- **User**: Show all memories for the current user
- **Session**: Use only memories from the current session
- **None**: Disable memory functionality

## Output Formats

- **None**: Standard text output
- **JSON**: Format response as JSON
- **Sentiment**: Analyze sentiment with confidence
- **Summary**: Generate a concise summary with key points
- **Action Items**: Extract action items with priority levels

## License

MIT License
