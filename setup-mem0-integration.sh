#!/bin/bash
# Setup script for integrating mem0 with Ollama and Qdrant
# This script automates the installation and configuration process for Linux/macOS

# Default values
QDRANT_PORT="6333"
QDRANT_CONTAINER_NAME="qdrant-mem0"
QDRANT_VOLUME_NAME="qdrant-mem0-data"
OLLAMA_HOST="http://localhost:11434"
OLLAMA_MODEL="llama3"
EMBEDDING_MODEL="nomic-embed-text"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_info() {
    echo -e "${CYAN}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

print_error() {
    echo -e "${RED}$1${NC}"
}

exit_with_error() {
    print_error "$1"
    exit 1
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        return 1
    else
        return 0
    fi
}

# Banner
echo -e "${MAGENTA}=============================================${NC}"
echo -e "${MAGENTA}       mem0 + Ollama + Qdrant Setup          ${NC}"
echo -e "${MAGENTA}=============================================${NC}"
echo

# Check prerequisites
print_info "Checking prerequisites..."

# Check if Docker is installed
if ! check_command docker; then
    print_warning "Docker is not installed. Attempting to install..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        print_info "Please install Docker Desktop for Mac from https://www.docker.com/products/docker-desktop/"
        print_info "After installation, please run this script again."
        exit 1
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if check_command apt-get; then
            # Debian-based
            print_info "Installing Docker using apt..."
            sudo apt-get update
            sudo apt-get install -y docker.io docker-compose
            sudo systemctl enable --now docker
        elif check_command dnf; then
            # Fedora/RHEL
            print_info "Installing Docker using dnf..."
            sudo dnf -y install docker docker-compose
            sudo systemctl enable --now docker
        elif check_command pacman; then
            # Arch-based
            print_info "Installing Docker using pacman..."
            sudo pacman -Sy docker docker-compose
            sudo systemctl enable --now docker
        else
            print_error "Unsupported Linux distribution. Please install Docker manually and try again."
            print_info "Visit https://docs.docker.com/engine/install/ for installation instructions."
            exit 1
        fi
        
        # Add user to docker group
        sudo usermod -aG docker $USER
        print_info "Added current user to the docker group. You might need to log out and back in for this to take effect."
    else
        print_error "Unsupported operating system. Please install Docker manually and try again."
        exit 1
    fi
    
    if check_command docker; then
        print_success "Docker installed successfully."
    else
        exit_with_error "Failed to install Docker. Please install it manually and try again."
    fi
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    exit_with_error "Docker is installed but not running. Please start Docker and try again."
fi
print_success "Docker is installed and running."

# Check if Ollama is installed and running
print_info "Checking Ollama..."
if ! curl -s "$OLLAMA_HOST/api/tags" &> /dev/null; then
    print_warning "Ollama is not running or not accessible at $OLLAMA_HOST."
    if ! check_command ollama; then
        print_info "Attempting to install Ollama..."
        
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            if check_command brew; then
                brew install ollama
            else
                # Install Homebrew first
                print_info "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                if check_command brew; then
                    brew install ollama
                else
                    exit_with_error "Failed to install Homebrew. Please install Ollama manually from https://ollama.com/"
                fi
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            print_info "Installing Ollama for Linux..."
            curl -fsSL https://ollama.com/install.sh | sh
        else
            exit_with_error "Unsupported operating system. Please install Ollama manually from https://ollama.com/"
        fi
        
        if check_command ollama; then
            print_success "Ollama installed successfully."
        else
            exit_with_error "Failed to install Ollama. Please install it manually from https://ollama.com/"
        fi
    fi
    
    # Start Ollama
    print_info "Starting Ollama service..."
    ollama serve &> /dev/null &
    
    # Wait for Ollama to start
    print_info "Waiting for Ollama to start..."
    RETRY_COUNT=0
    MAX_RETRIES=10
    while ! curl -s "$OLLAMA_HOST/api/tags" &> /dev/null; do
        sleep 2
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            exit_with_error "Ollama failed to start. Please start Ollama manually and try again."
        fi
    done
fi
print_success "Ollama is running."

# Check if Python is installed
if ! check_command python3; then
    print_warning "Python is not installed. Attempting to install..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if check_command brew; then
            brew install python
        else
            exit_with_error "Homebrew is not installed. Please install Python manually from https://www.python.org/downloads/"
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if check_command apt-get; then
            # Debian-based
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip
        elif check_command dnf; then
            # Fedora/RHEL
            sudo dnf install -y python3 python3-pip
        elif check_command pacman; then
            # Arch-based
            sudo pacman -Sy python python-pip
        else
            exit_with_error "Unsupported Linux distribution. Please install Python manually."
        fi
    else
        exit_with_error "Unsupported operating system. Please install Python manually."
    fi
    
    if ! check_command python3; then
        exit_with_error "Failed to install Python. Please install Python 3.9+ manually."
    fi
fi

# Get Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    exit_with_error "Python $PYTHON_VERSION is not supported. Please install Python 3.9 or higher."
fi
print_success "Python $PYTHON_VERSION is installed."

# Setup Qdrant in Docker
print_info "Setting up Qdrant in Docker..."

# Check if the Qdrant container is already running
if docker ps -a --filter "name=$QDRANT_CONTAINER_NAME" --format "{{.Names}}" | grep -q "$QDRANT_CONTAINER_NAME"; then
    if docker inspect --format="{{.State.Running}}" $QDRANT_CONTAINER_NAME | grep -q "true"; then
        print_success "Qdrant container is already running."
    else
        print_info "Starting existing Qdrant container..."
        docker start $QDRANT_CONTAINER_NAME
        if [ $? -ne 0 ]; then
            exit_with_error "Failed to start existing Qdrant container."
        fi
        print_success "Qdrant container started."
    fi
else
    # Create a Docker volume for Qdrant data persistence
    print_info "Creating Docker volume for Qdrant data..."
    docker volume create $QDRANT_VOLUME_NAME
    if [ $? -ne 0 ]; then
        exit_with_error "Failed to create Docker volume for Qdrant."
    fi
    
    # Pull and run the Qdrant container
    print_info "Pulling and running Qdrant container..."
    docker run -d --name $QDRANT_CONTAINER_NAME -p $QDRANT_PORT:6333 -p $((QDRANT_PORT+1)):6334 -v $QDRANT_VOLUME_NAME:/qdrant/storage qdrant/qdrant
    if [ $? -ne 0 ]; then
        exit_with_error "Failed to start Qdrant container."
    fi
    print_success "Qdrant container started."
fi

# Verify Qdrant is accessible
print_info "Verifying Qdrant connection..."
if ! curl -s "http://localhost:$QDRANT_PORT/dashboard/" &> /dev/null && ! curl -s "http://localhost:$QDRANT_PORT/collections" &> /dev/null; then
    print_warning "Could not connect to Qdrant, but container seems to be running. Will proceed anyway."
else
    print_success "Qdrant is running and accessible."
fi

# Install mem0 package
print_info "Installing mem0 package..."
python3 -m pip install --upgrade pip
python3 -m pip install mem0ai
if [ $? -ne 0 ]; then
    exit_with_error "Failed to install mem0 package."
fi
print_success "mem0 package installed."

# Check if Ollama has the required models
print_info "Checking for required Ollama models..."

# Function to check and pull models
check_ollama_model() {
    local MODEL_NAME=$1
    local MODELS=$(curl -s "$OLLAMA_HOST/api/tags" | grep -o "\"name\":\"[^\"]*\"" | awk -F '"' '{print $4}')
    
    if ! echo "$MODELS" | grep -q "^$MODEL_NAME$" && ! echo "$MODELS" | grep -q "^$MODEL_NAME:latest$"; then
        print_info "Model $MODEL_NAME not found. Pulling model (this may take a while)..."
        ollama pull $MODEL_NAME
        print_success "Model $MODEL_NAME pulled successfully."
    else
        print_success "Model $MODEL_NAME is already available."
    fi
}

# Check and pull the LLM model
check_ollama_model $OLLAMA_MODEL

# Check and pull the embedding model
check_ollama_model $EMBEDDING_MODEL

# Create docker-compose.yml file if it doesn't exist
DOCKER_COMPOSE_FILE="docker-compose.yml"
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    print_info "Creating docker-compose.yml file..."
    cat > $DOCKER_COMPOSE_FILE << EOF
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant
    container_name: $QDRANT_CONTAINER_NAME
    ports:
      - "$QDRANT_PORT:6333"
      - "$((QDRANT_PORT+1)):6334"
    volumes:
      - $QDRANT_VOLUME_NAME:/qdrant/storage
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/readiness"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  $QDRANT_VOLUME_NAME:
    name: $QDRANT_VOLUME_NAME
EOF
    print_success "docker-compose.yml file created."
else
    print_info "docker-compose.yml file already exists. Skipping creation."
fi

# Create integration guide
INTEGRATION_GUIDE_FILE="mem0-integration-guide.md"
print_info "Creating integration guide..."
cat > $INTEGRATION_GUIDE_FILE << 'EOF'
# mem0 + Ollama + Qdrant Integration Guide

This guide explains how to set up and use mem0 with Ollama for LLM capabilities and embeddings, and Qdrant for vector storage.

## Architecture Overview

The integration consists of three main components:

1. **mem0**: The memory layer that provides APIs for adding, retrieving, and searching memories.
2. **Ollama**: A tool for running large language models locally, providing both text generation and embeddings.
3. **Qdrant**: A vector database that stores embeddings and enables semantic search.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Application │────▶│    mem0     │────▶│   Ollama    │
│             │◀────│ Memory API  │◀────│  (LLM/Emb)  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   Qdrant    │
                    │(Vector DB)  │
                    └─────────────┘
```

## Prerequisites

- Docker for running Qdrant
- Ollama for LLM capabilities
- Python 3.9+ with pip

## Installation

### 1. Qdrant Setup

Qdrant is run in a Docker container:

```bash
docker run -d --name qdrant-mem0 -p 6333:6333 -p 6334:6334 -v qdrant-mem0-data:/qdrant/storage qdrant/qdrant
```

### 2. Ollama Setup

Ollama should be installed and running on your system:

- Download from https://ollama.com/
- Run Ollama 
- Pull the required models:
  ```bash
  ollama pull llama3
  ollama pull nomic-embed-text
  ```

### 3. mem0 Installation

```bash
pip install mem0ai
```

## Configuration

The integration is configured via a Python dictionary:

```python
config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "ollama_memories",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 768,  # Depends on the embedding model
            "unified_memory": True,  # Whether to use same collection across models
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "llama3",
            "temperature": 0.7,
            "max_tokens": 2000,
            "ollama_base_url": "http://localhost:11434",
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": "http://localhost:11434",
        },
    },
}
```

## Usage Example

```python
from mem0 import Memory

# Initialize memory with config
memory = Memory.from_config(config)

# Add memories
memory.add("I visited Paris last summer", user_id="user123")

# Search for relevant memories
results = memory.search("What places have I visited?", user_id="user123")

# Chat with memory context
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What places have I been to?"}
]
response = memory.chat(messages=messages)
```

## Memory Modes

The integration supports different memory modes:

1. **Search**: Retrieves memories semantically related to the current query
2. **User**: Fetches all memories for a specific user
3. **Session**: Only uses memories from the current session
4. **None**: Disables memory retrieval

## Running the Example

We've provided an example script that demonstrates the integration:

```bash
python mem0-ollama-example.py --user your_user_id --model llama3
```

Additional options:
- `--embed-model`: Specify a different embedding model
- `--memory-mode`: Choose memory mode (search, user, session, none)
- `--unified`: Use unified memory across different models

## Troubleshooting

- **Qdrant connection issues**: Ensure Docker is running and the container is healthy
- **Ollama errors**: Make sure Ollama is running and the models are pulled
- **Embedding dimension mismatch**: Check the dimensions of your embedding model

## Advanced Configuration

### Custom Embedding Dimensions

Different embedding models produce vectors of different dimensions:
- LLaMA models: typically 4096 dimensions
- nomic-embed-text: 768 dimensions
- snowflake-arctic-embed: 1024 dimensions

Ensure the `embedding_model_dims` in your configuration matches the model you're using.

### Memory Isolation

By setting `unified_memory: false`, you can create isolated memory collections for different models.
EOF

# Set execute permissions
chmod +x $0
chmod +x mem0-ollama-example.py 2>/dev/null || true

# Instructions for running the example
echo
echo -e "${GREEN}===================================================${NC}"
echo -e "${GREEN}             Setup Complete!                       ${NC}"
echo -e "${GREEN}===================================================${NC}"
echo
echo "Components installed:"
echo "- Qdrant running in Docker container: $QDRANT_CONTAINER_NAME"
echo "- mem0 Python package"
echo "- Required Ollama models"
echo
echo "To test the integration, run the example script:"
echo -e "${YELLOW}  python3 mem0-ollama-example.py${NC}"
echo
echo "For detailed information, refer to the integration guide:"
echo -e "${YELLOW}  $INTEGRATION_GUIDE_FILE${NC}"
echo
echo "Qdrant UI is available at: http://localhost:$QDRANT_PORT/dashboard/"
echo "Ollama API is available at: $OLLAMA_HOST"
echo
