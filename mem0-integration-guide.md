# Mem0 Integration with Ollama and Qdrant

This guide provides instructions for integrating mem0 (the memory layer for AI) with Ollama (local LLM runtime) and Qdrant (vector database) for building personalized AI applications with memory.

## Table of Contents

- [Automated Setup](#automated-setup)
- [Manual Setup](#manual-setup)
  - [Prerequisites](#prerequisites)
  - [Setting up Qdrant in Docker](#setting-up-qdrant-in-docker)
  - [Installing mem0](#installing-mem0)
  - [Integrating with Ollama](#integrating-with-ollama)
- [Running the Example](#running-the-example)
- [Advanced Configuration](#advanced-configuration)
- [Troubleshooting](#troubleshooting)

## Automated Setup

For quick setup, you can use the PowerShell script provided:

```powershell
# Run with default settings
.\setup-mem0-integration.ps1

# Or customize settings
.\setup-mem0-integration.ps1 -QdrantPort "6333" -QdrantContainerName "qdrant-mem0" -OllamaModel "llama3"
```

The script automatically:
- Checks prerequisites (Docker, Ollama, Python)
- Sets up Qdrant in a Docker container
- Installs the mem0 package
- Creates an example script for testing

## Manual Setup

If you prefer to set up the components manually or if you're not using Windows, follow these steps:

### Prerequisites

1. **Docker**: Required for running Qdrant
   - Download and install from [Docker's official website](https://www.docker.com/products/docker-desktop/)
   - Verify installation with: `docker --version`

2. **Ollama**: Local LLM runtime
   - Download and install from [Ollama's website](https://ollama.ai/)
   - Start the Ollama service
   - Verify it's running: `curl http://localhost:11434/api/tags`

3. **Python 3.9+**: Required for mem0
   - Download from [Python.org](https://www.python.org/downloads/)
   - Verify installation with: `python --version`

### Setting up Qdrant in Docker

1. Create a Docker volume for data persistence:
   ```bash
   docker volume create qdrant-mem0-data
   ```

2. Pull and run the Qdrant container:
   ```bash
   docker run -d --name qdrant-mem0 -p 6333:6333 -p 6334:6334 -v qdrant-mem0-data:/qdrant/storage qdrant/qdrant
   ```

3. Verify Qdrant is running:
   ```bash
   curl http://localhost:6333/dashboard/
   ```
   You can also open http://localhost:6333/dashboard/ in your browser to access the Qdrant UI.

### Installing mem0

1. Install the mem0 package using pip:
   ```bash
   pip install mem0ai
   ```

2. Verify installation:
   ```bash
   python -c "import mem0; print(mem0.__version__)"
   ```

### Integrating with Ollama

1. Ensure you have a suitable model in Ollama:
   ```bash
   # List available models
   curl http://localhost:11434/api/tags
   
   # Pull a model if needed
   curl -X POST http://localhost:11434/api/pull -d '{"name":"llama3"}'
   ```

2. Create a Python script for integration (example below).

## Running the Example

The example script (`mem0-ollama-example.py`) demonstrates how to:
1. Initialize mem0 with Qdrant as the vector database
2. Use Ollama for both embeddings and LLM capabilities
3. Store and retrieve memories for personalized conversations

Run the example:
```bash
python mem0-ollama-example.py
```

### Example Script Explanation

The example script:
1. Sets up a connection to Ollama and Qdrant
2. Initializes mem0 with those connections
3. Implements a chat loop that:
   - Takes user input
   - Searches for relevant memories
   - Generates responses based on those memories
   - Stores new memories from the conversation

## Advanced Configuration

### Custom Qdrant Configuration

You can modify the Qdrant configuration by mounting a custom config file:

```bash
docker run -d --name qdrant-mem0 \
  -p 6333:6333 \
  -p 6334:6334 \
  -v qdrant-mem0-data:/qdrant/storage \
  -v /path/to/config.yaml:/qdrant/config/production.yaml \
  qdrant/qdrant
```

### Using Different Ollama Models

To use a different Ollama model:

1. Pull the desired model:
   ```bash
   curl -X POST http://localhost:11434/api/pull -d '{"name":"phi3"}'
   ```

2. Update the `OLLAMA_MODEL` variable in your script.

### Memory Configuration Options

mem0 offers several configuration options:

```python
memory = Memory(
    vector_db="qdrant",              # Vector database
    qdrant_url="http://localhost:6333",  # Qdrant URL
    collection_name="custom_collection", # Collection name
    embedding_model="ollama",        # Embedding model source
    llm="ollama",                    # LLM for reasoning
    memory_decay=0.98,               # Memory decay rate (0-1)
    similarity_threshold=0.75        # Minimum similarity threshold
)
```

## Troubleshooting

### Qdrant Connection Issues

If you can't connect to Qdrant:

1. Verify the Docker container is running:
   ```bash
   docker ps | grep qdrant
   ```

2. Check container logs:
   ```bash
   docker logs qdrant-mem0
   ```

3. Ensure ports are not blocked by a firewall.

### Ollama Issues

If Ollama is not responding:

1. Check if the service is running:
   ```bash
   # Windows
   Get-Process | Where-Object { $_.ProcessName -like "*ollama*" }
   
   # Linux/macOS
   ps aux | grep ollama
   ```

2. Restart the Ollama service if needed.

3. Verify API accessibility:
   ```bash
   curl http://localhost:11434/api/tags
   ```

### mem0 Package Issues

If you encounter issues with mem0:

1. Verify you have the latest version:
   ```bash
   pip install --upgrade mem0ai
   ```

2. Check Python compatibility (3.9+ required).

3. Enable debug logging in mem0 (refer to documentation).
