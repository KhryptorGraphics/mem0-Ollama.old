#!/usr/bin/env python3
"""
mem0 OpenAI-Compatible API Server

This script creates an API server compatible with the OpenAI API format, but uses
mem0 + Ollama + Qdrant as the backend. This allows you to use any OpenAI-compatible
client software with your local Ollama models enhanced with mem0's memory capabilities.

Routes implemented:
- POST /v1/chat/completions
- POST /v1/embeddings

Compatible with most OpenAI client libraries and tools.
"""

import os
import sys
import time
import uuid
import json
import argparse
import logging
from typing import Dict, List, Any, Optional, Union, Literal
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, Request, Response, HTTPException, Depends, status, Body
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse
    import uvicorn
    from pydantic import BaseModel, Field, root_validator
except ImportError:
    logger.error("Required packages not installed. Installing dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]", "pydantic"])
    from fastapi import FastAPI, Request, Response, HTTPException, Depends, status, Body
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse
    import uvicorn
    from pydantic import BaseModel, Field, root_validator

try:
    from mem0 import Memory
except ImportError:
    logger.error("mem0ai package not installed. Installing it now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mem0ai"])
    from mem0 import Memory

# Default configuration
CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "log_level": "info",
    "allow_origin": "*",
    "api_keys": [],  # Optional API keys
    "ollama_base_url": "http://localhost:11434",
    "ollama_model": "llama3",
    "embedding_model": "nomic-embed-text",
    "qdrant_host": "localhost",
    "qdrant_port": 6333,
    "collection_name": "openai_compatible_memories",
    "default_user": "default",
    "search_limit": 5
}

# Model dimensions mapping for different embedding models
MODEL_DIMENSIONS = {
    "llama3": 4096,
    "mistral": 4096,
    "gemma": 4096,
    "nomic-embed-text": 768,
    "snowflake-arctic-embed": 1024,
    "all-minilm": 384,
    "openai": 1536  # OpenAI embeddings dimension
}

# Initialize FastAPI app
app = FastAPI(
    title="mem0 OpenAI-Compatible API",
    description="A local OpenAI-compatible API using mem0 + Ollama + Qdrant",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to appropriate origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global memory instance
memory_instance = None

# Pydantic models for API requests/responses
class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    # mem0-specific parameters
    enable_memory: Optional[bool] = True
    memory_search_limit: Optional[int] = 5

class EmbeddingRequest(BaseModel):
    model: str
    input: Union[str, List[str]]
    user: Optional[str] = None
    encoding_format: Optional[str] = "float"
    dimensions: Optional[int] = None

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: Optional[int] = 0
    total_tokens: int

class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Usage

class EmbeddingResponseData(BaseModel):
    embedding: List[float]
    index: int
    object: str = "embedding"

class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingResponseData]
    model: str
    usage: Usage

class StreamingChatResponseChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]

# API key verification dependency
async def verify_api_key(request: Request):
    if not CONFIG["api_keys"]:
        return True  # No API keys configured, allow all requests
    
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    
    # Extract the key from "Bearer sk-..."
    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:]
    else:
        api_key = auth_header
    
    if api_key not in CONFIG["api_keys"]:
        # Simulate OpenAI's behavior with a small delay and specific error format
        time.sleep(0.5)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return True

# Initialize memory with Ollama and Qdrant
def initialize_memory() -> Memory:
    global memory_instance
    
    if memory_instance:
        return memory_instance
    
    # Get embedding dimensions based on model
    embed_model = CONFIG["embedding_model"]
    model_name = embed_model.split(":")[0] if ":" in embed_model else embed_model
    embed_dims = MODEL_DIMENSIONS.get(model_name, 768)
    
    logger.info(f"Initializing mem0 with embedding model: {embed_model} ({embed_dims} dimensions)")
    
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": CONFIG["collection_name"],
                "host": CONFIG["qdrant_host"],
                "port": CONFIG["qdrant_port"],
                "embedding_model_dims": embed_dims,
                # "unified_memory" field is not supported in current mem0ai version
            },
        },
        "llm": {
            "provider": "ollama",
            "config": {
                "model": CONFIG["ollama_model"],
                "temperature": 0.7,
                "max_tokens": 2000,
                "ollama_base_url": CONFIG["ollama_base_url"],
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": CONFIG["embedding_model"],
                "ollama_base_url": CONFIG["ollama_base_url"],
                "embedding_dims": embed_dims,
            },
        },
    }
    
    try:
        memory_instance = Memory.from_config(config)
        return memory_instance
    except Exception as e:
        logger.error(f"Error initializing Memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize Memory: {str(e)}"
        )

# Estimate token counts (very rough estimation, adjust as needed)
def estimate_tokens(text: str) -> int:
    # Very simple estimation: ~4 characters per token on average
    return max(1, len(text) // 4)

# Helper to flatten conversation into a prompt
def prepare_memory_prompt(relevant_memories):
    if not relevant_memories or not relevant_memories.get("results"):
        return "No relevant memories found."
    
    memories_str = []
    for i, entry in enumerate(relevant_memories["results"]):
        # Include similarity score if available
        similarity = entry.get('similarity', 0) * 100
        memory_text = entry.get('memory', '')
        memories_str.append(f"Memory {i+1} [{similarity:.1f}%]: {memory_text}")
    
    return "\n".join(memories_str)

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse, dependencies=[Depends(verify_api_key)])
async def chat_completion(request: ChatCompletionRequest):
    memory = initialize_memory()
    
    # Prepare parameters
    user_id = request.user or CONFIG["default_user"]
    temperature = request.temperature or 0.7
    top_p = request.top_p or 1.0
    max_tokens = request.max_tokens or 2000
    enable_memory = request.enable_memory
    memory_search_limit = request.memory_search_limit or CONFIG["search_limit"]
    
    # Extract the last user message for memory search
    last_user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            last_user_message = msg.content
            break
    
    # Estimate token usage for prompt
    prompt_text = " ".join([msg.content for msg in request.messages])
    prompt_tokens = estimate_tokens(prompt_text)
    completion_tokens = 0
    
    # Search for relevant memories if enabled
    memory_context = ""
    if enable_memory and last_user_message:
        try:
            relevant_memories = memory.search(
                query=last_user_message, 
                user_id=user_id, 
                limit=memory_search_limit
            )
            memory_context = prepare_memory_prompt(relevant_memories)
            logger.info(f"Retrieved {len(relevant_memories.get('results', []))} memories for context")
        except Exception as e:
            logger.warning(f"Error retrieving memories: {e}")
            memory_context = "Error retrieving memories."
    
    # Enhance system message with memory context if available
    enhanced_messages = []
    system_message_found = False
    
    for msg in request.messages:
        if msg.role == "system":
            # Enhance system message with memory context
            system_message_found = True
            if memory_context and enable_memory:
                enhanced_content = f"{msg.content}\n\nRelevant memories from the user:\n{memory_context}"
                enhanced_messages.append({"role": "system", "content": enhanced_content})
            else:
                enhanced_messages.append({"role": msg.role, "content": msg.content})
        else:
            enhanced_messages.append({"role": msg.role, "content": msg.content})
    
    # Add a system message with memories if none exists
    if not system_message_found and memory_context and enable_memory:
        enhanced_messages.insert(0, {
            "role": "system", 
            "content": f"You are a helpful assistant with access to the user's memories. Consider these memories when responding:\n\n{memory_context}"
        })
    
    # Make the completion request to mem0 (which uses Ollama)
    try:
        if request.stream:
            # Not implementing streaming in this simplified version
            # Would require adapting mem0's streaming capabilities
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Streaming is not supported in this version"
            )
        else:
            # Get response from memory's chat method
            response_text = memory.chat(
                messages=enhanced_messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            )
            
            # Store the interaction in memory if enabled
            if enable_memory and last_user_message:
                try:
                    memory.add(
                        message=last_user_message,
                        response=response_text,
                        user_id=user_id
                    )
                    logger.info(f"Stored new memory for user {user_id}")
                except Exception as e:
                    logger.warning(f"Error storing memory: {e}")
            
            # Estimate completion tokens
            completion_tokens = estimate_tokens(response_text)
            
            # Format response in OpenAI-compatible format
            completion_id = f"chatcmpl-{str(uuid.uuid4())}"
            created_time = int(datetime.now().timestamp())
            
            response = {
                "id": completion_id,
                "object": "chat.completion",
                "created": created_time,
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_text
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            }
            
            return response
            
    except Exception as e:
        logger.error(f"Error generating completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating completion: {str(e)}"
        )

@app.post("/v1/embeddings", response_model=EmbeddingResponse, dependencies=[Depends(verify_api_key)])
async def create_embeddings(request: EmbeddingRequest):
    memory = initialize_memory()
    
    # Validate input
    if isinstance(request.input, str):
        texts = [request.input]
    else:
        texts = request.input
    
    if not texts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input cannot be empty"
        )
    
    user_id = request.user or CONFIG["default_user"]
    
    # Get embeddings using mem0's embedding capabilities
    try:
        embeddings = []
        total_tokens = 0
        
        for i, text in enumerate(texts):
            # Get embedding from memory's embedding provider
            embedding = memory.get_embeddings(text)
            
            # Estimate tokens
            tokens = estimate_tokens(text)
            total_tokens += tokens
            
            # Add to results
            embeddings.append({
                "embedding": embedding,
                "index": i,
                "object": "embedding"
            })
        
        # Format response in OpenAI-compatible format
        response = {
            "object": "list",
            "data": embeddings,
            "model": request.model,
            "usage": {
                "prompt_tokens": total_tokens,
                "total_tokens": total_tokens
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating embeddings: {str(e)}"
        )

@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    """List available models in an OpenAI-compatible format."""
    try:
        # Get available models from Ollama
        import requests
        response = requests.get(f"{CONFIG['ollama_base_url']}/api/tags")
        
        if response.status_code != 200:
            logger.error(f"Error fetching models from Ollama: {response.status_code}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error fetching models from Ollama"
            )
        
        ollama_models = response.json().get("models", [])
        
        # Format in OpenAI-compatible response
        models_data = []
        for model in ollama_models:
            model_id = model.get("name", "unknown")
            models_data.append({
                "id": model_id,
                "object": "model",
                "created": int(datetime.now().timestamp()),
                "owned_by": "local-ollama"
            })
        
        # Add a few fake OpenAI models to ensure compatibility with some clients
        compat_models = ["gpt-3.5-turbo", "gpt-4", "text-embedding-ada-002"]
        for model_id in compat_models:
            models_data.append({
                "id": model_id,
                "object": "model",
                "created": int(datetime.now().timestamp()),
                "owned_by": "openai-compatible"
            })
        
        return {
            "object": "list",
            "data": models_data
        }
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing models: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if mem0 is initialized
        memory = initialize_memory()
        
        # Check if Ollama is accessible
        import requests
        ollama_resp = requests.get(f"{CONFIG['ollama_base_url']}/api/tags")
        if ollama_resp.status_code != 200:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "error", "message": "Ollama service not available"}
            )
        
        # Check if Qdrant is accessible
        try:
            collections = memory.get_collections()
            if not collections:
                logger.warning("No collections found in Qdrant")
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "error", "message": f"Qdrant not available: {str(e)}"}
            )
        
        return {"status": "ok", "services": {"mem0": True, "ollama": True, "qdrant": True}}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "message": str(e)}
        )

@app.get("/")
async def root():
    """Basic information about the API."""
    return {
        "name": "mem0 OpenAI-Compatible API",
        "version": "1.0.0",
        "description": "A local OpenAI-compatible API using mem0 + Ollama + Qdrant",
        "endpoints": {
            "/v1/chat/completions": "Generate chat completions with memory-enhanced context",
            "/v1/embeddings": "Generate embeddings from text",
            "/v1/models": "List available models",
            "/health": "Health check endpoint"
        }
    }

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="mem0 OpenAI-Compatible API Server")
    parser.add_argument("--host", type=str, default=CONFIG["host"], help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=CONFIG["port"], help="Port to bind the server to")
    parser.add_argument("--log-level", type=str, default=CONFIG["log_level"], choices=["debug", "info", "warning", "error", "critical"], help="Logging level")
    parser.add_argument("--api-key", type=str, action="append", help="API key(s) for authentication (can be specified multiple times)")
    parser.add_argument("--ollama-url", type=str, default=CONFIG["ollama_base_url"], help="Ollama API base URL")
    parser.add_argument("--ollama-model", type=str, default=CONFIG["ollama_model"], help="Default Ollama model for chat completions")
    parser.add_argument("--embedding-model", type=str, default=CONFIG["embedding_model"], help="Model to use for embeddings")
    parser.add_argument("--qdrant-host", type=str, default=CONFIG["qdrant_host"], help="Qdrant host")
    parser.add_argument("--qdrant-port", type=int, default=CONFIG["qdrant_port"], help="Qdrant port")
    parser.add_argument("--collection", type=str, default=CONFIG["collection_name"], help="Qdrant collection name")
    parser.add_argument("--search-limit", type=int, default=CONFIG["search_limit"], help="Default number of memories to retrieve")
    
    args = parser.parse_args()
    
    # Update config with parsed arguments
    CONFIG["host"] = args.host
    CONFIG["port"] = args.port
    CONFIG["log_level"] = args.log_level
    CONFIG["ollama_base_url"] = args.ollama_url
    CONFIG["ollama_model"] = args.ollama_model
    CONFIG["embedding_model"] = args.embedding_model
    CONFIG["qdrant_host"] = args.qdrant_host
    CONFIG["qdrant_port"] = args.qdrant_port
    CONFIG["collection_name"] = args.collection
    CONFIG["search_limit"] = args.search_limit
    
    if args.api_key:
        CONFIG["api_keys"] = args.api_key
    
    return args

def main():
    """Main entry point."""
    args = parse_args()
    
    # Set log level
    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(level=log_level)
    
    logger.info(f"Starting mem0 OpenAI-Compatible API Server on {args.host}:{args.port}")
    logger.info(f"Using Ollama at {CONFIG['ollama_base_url']}")
    logger.info(f"Using Qdrant at {CONFIG['qdrant_host']}:{CONFIG['qdrant_port']}")
    
    if CONFIG["api_keys"]:
        logger.info(f"API key authentication enabled with {len(CONFIG['api_keys'])} key(s)")
    else:
        logger.warning("API key authentication is DISABLED. Anyone can access this API.")
    
    # Initialize memory when server starts
    try:
        initialize_memory()
        logger.info("Successfully initialized mem0 with Ollama and Qdrant")
    except Exception as e:
        logger.error(f"Failed to initialize mem0: {e}")
        sys.exit(1)
    
    # Start the server
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
