# Setup script for integrating mem0 with Ollama and Qdrant
# This script automates the installation and configuration process

# Parameters with default values
param (
    [string]$QdrantPort = "6333",
    [string]$QdrantContainerName = "qdrant-mem0",
    [string]$QdrantVolumeName = "qdrant-mem0-data",
    [string]$OllamaHost = "http://localhost:11434",
    [string]$OllamaModel = "llama3",
    [string]$EmbeddingModel = "nomic-embed-text"
)

# Function to check if a command exists
function Test-CommandExists {
    param ($command)
    $exists = $null -ne (Get-Command -Name $command -ErrorAction SilentlyContinue)
    return $exists
}

# Color output functions
function Write-ColorOutput {
    param ([string]$message, [string]$color)
    Write-Host $message -ForegroundColor $color
}
function Write-Success { param ([string]$message) Write-ColorOutput $message "Green" }
function Write-Info { param ([string]$message) Write-ColorOutput $message "Cyan" }
function Write-Warning { param ([string]$message) Write-ColorOutput $message "Yellow" }
function Write-Error { param ([string]$message) Write-ColorOutput $message "Red" }

# Function to handle errors and exit
function Exit-WithError {
    param ([string]$message)
    Write-Error $message
    exit 1
}

# Title banner
Write-Host "==============================================" -ForegroundColor Magenta
Write-Host "       mem0 + Ollama + Qdrant Setup          " -ForegroundColor Magenta
Write-Host "==============================================" -ForegroundColor Magenta
Write-Host ""

# Check prerequisites
Write-Info "Checking prerequisites..."

# Check if Docker is installed
if (-not (Test-CommandExists "docker")) {
    Write-Warning "Docker is not installed. Attempting to install..."
    
    # Check if winget is available
    if (Test-CommandExists "winget") {
        Write-Info "Installing Docker Desktop via winget..."
        winget install Docker.DockerDesktop
        if ($LASTEXITCODE -ne 0) {
            Exit-WithError "Failed to install Docker Desktop. Please install Docker manually and try again."
        }
        Write-Success "Docker Desktop installed. Please start Docker and run this script again."
        exit 0
    } else {
        Exit-WithError "Docker is not installed. Please install Docker Desktop manually from https://www.docker.com/products/docker-desktop/"
    }
}

# Check if Docker is running
try {
    $dockerStatus = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Exit-WithError "Docker is installed but not running. Please start Docker and try again."
    }
} catch {
    Exit-WithError "Failed to check Docker status. Please ensure Docker is running."
}
Write-Success "Docker is installed and running."

# Check if Ollama is installed and running
Write-Info "Checking Ollama..."
try {
    $ollamaResponse = Invoke-WebRequest -Uri "$OllamaHost/api/tags" -Method Get -ErrorAction SilentlyContinue
    if ($ollamaResponse.StatusCode -eq 200) {
        Write-Success "Ollama is running."
    } else {
        Exit-WithError "Ollama seems to be installed but returned an unexpected status. Please check if Ollama is properly running."
    }
} catch {
    Write-Warning "Ollama is not running or not accessible at $OllamaHost."
    Write-Info "Attempting to download and install Ollama..."
    
    # Download Ollama installer
    $ollamaInstallerUrl = "https://ollama.com/download/ollama-windows-amd64.exe"
    $ollamaInstallerPath = "$env:TEMP\ollama-installer.exe"
    
    try {
        Invoke-WebRequest -Uri $ollamaInstallerUrl -OutFile $ollamaInstallerPath
        Write-Info "Running Ollama installer..."
        Start-Process -FilePath $ollamaInstallerPath -Wait
        
        # Verify if Ollama was installed correctly
        $ollamaPath = "$env:LOCALAPPDATA\Ollama\ollama.exe"
        if (Test-Path $ollamaPath) {
            Write-Success "Ollama installed successfully."
            
            # Start Ollama service
            Write-Info "Starting Ollama service..."
            Start-Process -FilePath $ollamaPath -ArgumentList "serve" -WindowStyle Hidden
            
            # Wait for the service to start
            Start-Sleep -Seconds 5
            
            # Check if Ollama is now running
            try {
                $ollamaResponse = Invoke-WebRequest -Uri "$OllamaHost/api/tags" -Method Get -ErrorAction SilentlyContinue
                if ($ollamaResponse.StatusCode -eq 200) {
                    Write-Success "Ollama is now running."
                } else {
                    Exit-WithError "Ollama was installed but is not running properly. Please start Ollama manually and try again."
                }
            } catch {
                Exit-WithError "Ollama was installed but is not running properly. Please start Ollama manually and try again."
            }
        } else {
            Exit-WithError "Failed to install Ollama. Please install Ollama manually from https://ollama.com/"
        }
    } catch {
        Exit-WithError "Failed to download or install Ollama. Please install Ollama manually from https://ollama.com/"
    }
}

# Check if Python is installed
if (-not (Test-CommandExists "python")) {
    Write-Warning "Python is not installed. Attempting to install..."
    
    # Check if winget is available
    if (Test-CommandExists "winget") {
        Write-Info "Installing Python via winget..."
        winget install Python.Python.3.10
        if ($LASTEXITCODE -ne 0) {
            Exit-WithError "Failed to install Python. Please install Python 3.9+ manually and try again."
        }
        # Refresh environment variables
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        Write-Success "Python installed."
    } else {
        Exit-WithError "Python is not installed. Please install Python 3.9+ manually from https://www.python.org/downloads/"
    }
}

# Check Python version
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python ([0-9]+)\.([0-9]+)\.([0-9]+)") {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
        Exit-WithError "Python $major.$minor is not supported. Please install Python 3.9 or higher."
    }
    Write-Success "Python $major.$minor is installed."
} else {
    Exit-WithError "Failed to determine Python version."
}

# Setup Qdrant in Docker
Write-Info "Setting up Qdrant in Docker..."

# Check if the Qdrant container is already running
$containerExists = docker ps -a --filter "name=$QdrantContainerName" --format "{{.Names}}"
if ($containerExists -eq $QdrantContainerName) {
    $containerStatus = docker inspect --format "{{.State.Running}}" $QdrantContainerName
    if ($containerStatus -eq "true") {
        Write-Success "Qdrant container is already running."
    } else {
        Write-Info "Starting existing Qdrant container..."
        docker start $QdrantContainerName
        if ($LASTEXITCODE -ne 0) {
            Exit-WithError "Failed to start existing Qdrant container."
        }
        Write-Success "Qdrant container started."
    }
} else {
    # Create a Docker volume for Qdrant data persistence
    Write-Info "Creating Docker volume for Qdrant data..."
    docker volume create $QdrantVolumeName
    if ($LASTEXITCODE -ne 0) {
        Exit-WithError "Failed to create Docker volume for Qdrant."
    }
    
    # Pull and run the Qdrant container
    Write-Info "Pulling and running Qdrant container..."
    $port1 = $QdrantPort
    $port2 = [int]$QdrantPort + 1
    docker run -d --name $QdrantContainerName -p ${port1}:6333 -p ${port2}:6334 -v ${QdrantVolumeName}:/qdrant/storage qdrant/qdrant
    if ($LASTEXITCODE -ne 0) {
        Exit-WithError "Failed to start Qdrant container."
    }
    Write-Success "Qdrant container started."
}

# Verify Qdrant is accessible
Write-Info "Verifying Qdrant connection..."
try {
    $qdrantResponse = Invoke-WebRequest -Uri "http://localhost:$QdrantPort/dashboard/" -Method Get -ErrorAction SilentlyContinue
    if ($qdrantResponse.StatusCode -eq 200) {
        Write-Success "Qdrant is running and accessible."
    } else {
        Write-Warning "Qdrant responded with status code $($qdrantResponse.StatusCode). This might indicate an issue."
    }
} catch {
    try {
        # Try the collections endpoint if dashboard is not available
        $qdrantResponse = Invoke-WebRequest -Uri "http://localhost:$QdrantPort/collections" -Method Get -ErrorAction SilentlyContinue
        if ($qdrantResponse.StatusCode -eq 200) {
            Write-Success "Qdrant is running and accessible."
        } else {
            Write-Warning "Qdrant responded with status code $($qdrantResponse.StatusCode). This might indicate an issue."
        }
    } catch {
        Write-Warning "Could not connect to Qdrant, but container seems to be running. Will proceed anyway."
    }
}

# Install mem0 package
Write-Info "Installing mem0 package..."
python -m pip install --upgrade pip
python -m pip install mem0ai
if ($LASTEXITCODE -ne 0) {
    Exit-WithError "Failed to install mem0 package."
}
Write-Success "mem0 package installed."

# Check if Ollama has the required models
Write-Info "Checking for required Ollama models..."

# Function to check and pull models
function Get-OllamaModel {
    param (
        [string]$ModelName
    )
    
    try {
        $ollamaModels = Invoke-RestMethod -Uri "$OllamaHost/api/tags" -Method Get
        $modelExists = $false
        foreach ($model in $ollamaModels.models) {
            if ($model.name -eq $ModelName -or $model.name -eq ($ModelName + ":latest")) {
                $modelExists = $true
                break
            }
        }

        if (-not $modelExists) {
            Write-Info "Model $ModelName not found. Pulling model (this may take a while)..."
            $json = @{
                name = $ModelName
            } | ConvertTo-Json
            
            Invoke-RestMethod -Uri "$OllamaHost/api/pull" -Method Post -ContentType "application/json" -Body $json
            Write-Success "Model $ModelName pulled successfully."
        } else {
            Write-Success "Model $ModelName is already available."
        }
    } catch {
        Write-Warning "Failed to check or pull the Ollama model $ModelName. Error: $_"
        Write-Warning "Please ensure the model '$ModelName' is available in Ollama."
    }
}

# Check and pull the LLM model
Get-OllamaModel -ModelName $OllamaModel

# Check and pull the embedding model
Get-OllamaModel -ModelName $EmbeddingModel

# Create docker-compose.yml file if it doesn't exist
$dockerComposeFile = "docker-compose.yml"
if (-not (Test-Path $dockerComposeFile)) {
    Write-Info "Creating docker-compose.yml file..."
    $port1 = $QdrantPort
    $port2 = [int]$QdrantPort + 1
    
    $dockerComposeContent = @"
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant
    container_name: $QdrantContainerName
    ports:
      - "${port1}:6333"
      - "${port2}:6334"
    volumes:
      - ${QdrantVolumeName}:/qdrant/storage
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/readiness"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  ${QdrantVolumeName}:
    name: ${QdrantVolumeName}
"@
    Set-Content -Path $dockerComposeFile -Value $dockerComposeContent
    Write-Success "docker-compose.yml file created."
} else {
    Write-Info "docker-compose.yml file already exists. Skipping creation."
}

# Create integration guide
$integrationGuideFile = "mem0-integration-guide.md"
Write-Info "Creating integration guide..."
$integrationGuideContent = @'
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
'@

Set-Content -Path $integrationGuideFile -Value $integrationGuideContent
Write-Success "Integration guide created: $integrationGuideFile"

# Instructions for running the example
Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "             Setup Complete!                      " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Components installed:"
Write-Host "- Qdrant running in Docker container: $QdrantContainerName"
Write-Host "- mem0 Python package"
Write-Host "- Required Ollama models"
Write-Host ""
Write-Host "To test the integration, run the example script:"
Write-Host "  python mem0-ollama-example.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "For detailed information, refer to the integration guide:"
Write-Host "  $integrationGuideFile" -ForegroundColor Yellow
Write-Host ""
Write-Host "Qdrant UI is available at: http://localhost:$QdrantPort/dashboard/"
Write-Host "Ollama API is available at: $OllamaHost"
Write-Host ""
