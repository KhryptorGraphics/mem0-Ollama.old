"""
Memory management utilities for mem0 + Ollama integration
"""

import logging
import requests
from typing import Dict, List, Any, Optional, Union

from mem0 import Memory
from config import (
    OLLAMA_HOST, 
    OLLAMA_MODEL, 
    QDRANT_HOST, 
    QDRANT_COLLECTION,
    MODEL_DIMENSIONS
)

logger = logging.getLogger(__name__)

def check_qdrant() -> bool:
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
) -> Dict[str, Any]:
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
    # Ensure we always have a valid user_id (never None)
    if user_id is None or user_id == "":
        user_id = "default_user"
        
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
        
    # Generate system prompt with memory context
    system_prompt = f"""You are a helpful AI assistant with memory capabilities.
Answer the question based on the user's query and relevant memories.

User Memories:
{memories_str}

Please be conversational and friendly in your responses.
If referring to a memory, try to naturally incorporate it without explicitly stating 'According to your memory...'"""
    
    # Create message history for context
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]
    
    try:
        # Import here to avoid circular imports
        from ollama_client import chat_with_ollama
        
        # Send chat request to Ollama
        result = chat_with_ollama(
            messages=messages,
            model=model_to_use,
            output_format=output_format
        )
        
        # Extract assistant response
        if "message" in result and "content" in result["message"]:
            assistant_response = result["message"]["content"]
        else:
            assistant_response = result.get("response", "I couldn't generate a response.")
        
        # Store the conversation in memory
        if memory_mode != "none":
            memory.add(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": assistant_response}
                ],
                user_id=user_id
            )
        
        # Return formatted response
        return {
            "content": assistant_response,
            "memories": relevant_memories,
            "model": model_to_use,
            "choices": [
                {"message": {"content": assistant_response}}
            ],
            "conversation_id": user_id
        }
    except Exception as e:
        logger.error(f"Error in chat completion: {e}")
        raise
