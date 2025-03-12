"""
Memory management utilities for mem0 + Ollama integration
"""

import logging
import requests
import json
import time
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

def preprocess_user_message(message: str) -> str:
    """
    Preprocess user message to enhance it for better memory storage and retrieval.
    
    This function makes user messages more prominent in the vector store by:
    1. Adding emphasis markers
    2. Potentially repeating key phrases
    3. Formatting for better embedding
    
    Args:
        message: The original user message
        
    Returns:
        Enhanced version of the message optimized for embedding and retrieval
    """
    # Skip preprocessing for very short messages
    if len(message) < 5:
        return f"IMPORTANT USER QUERY: {message}"
        
    # For longer messages, enhance with emphasis and formatting
    enhanced = message.strip()
    
    # Add importance markers at the beginning and end
    enhanced = f"IMPORTANT USER INPUT: {enhanced} [USER QUERY END]"
    
    # If message is a question, emphasize it further
    if any(q in message for q in ["?", "what", "how", "why", "when", "where", "who", "which"]):
        enhanced = f"USER QUESTION: {enhanced}"
    
    return enhanced

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
        memory = Memory.from_config(config)
        # Initialize the memory status tracker after creating memory
        initialize_memory_status_tracking()
        return memory
    except Exception as e:
        logger.error(f"Error initializing Memory: {e}")
        raise

# Global constants
GLOBAL_MEMORY_ID = "global_memory_store"
MEMORY_COUNTER = {"active": 0, "inactive": 0, "total": 0}

# Key for storing memory status information in Qdrant
STATUS_KEY = "memory_status.json"

def initialize_memory_status_tracking():
    """Initialize the memory status tracking, loading any existing data."""
    try:
        # Try to load existing status from Qdrant or create a new one
        url = f"{QDRANT_HOST}/collections/{QDRANT_COLLECTION}/points/scroll"
        response = requests.post(url, json={"limit": 1000, "with_payload": True})
        
        if response.status_code == 200:
            data = response.json()
            active_count = 0
            inactive_count = 0
            
            # Count active and inactive memories
            for point in data.get("result", []):
                payload = point.get("payload", {})
                # Check if the memory is inactive
                is_inactive = payload.get("inactive", False)
                if is_inactive:
                    inactive_count += 1
                else:
                    active_count += 1
            
            # Update the global counter
            global MEMORY_COUNTER
            MEMORY_COUNTER["active"] = active_count
            MEMORY_COUNTER["inactive"] = inactive_count
            MEMORY_COUNTER["total"] = active_count + inactive_count
            
            logger.info(f"Initialized memory status tracking: {MEMORY_COUNTER}")
        else:
            logger.warning(f"Failed to initialize memory status. Using default values.")
    except Exception as e:
        logger.error(f"Error initializing memory status tracking: {e}")

def chat_with_memories(
    memory: Memory, 
    message: str, 
    user_id: str = "default_user",  # This parameter is kept for API compatibility but ignored
    memory_mode: str = "search",    # This parameter is kept for API compatibility but ignored
    output_format: Optional[Union[str, Dict]] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,       # Added temperature parameter
    max_tokens: int = 2000          # Added max tokens parameter
) -> Dict[str, Any]:
    """
    Process a chat message, search for relevant memories, and generate a response.
    Always uses a global memory store for all interactions.
    
    Args:
        memory: The Memory object
        message: User's message
        user_id: Ignored - always uses global memory ID
        memory_mode: Ignored - always uses search mode
        output_format: Optional format for structured output
        model: Optional model to use for this specific request
    
    Returns:
        Dict with response data including:
        - content: The assistant's response
        - memories: Any relevant memories found
        - model: The model used for the response
    """
    # Override any user_id with the global one
    user_id = GLOBAL_MEMORY_ID
        
    logger.info(f"Processing chat with global memory store using model {model or OLLAMA_MODEL}")
    
    # Use specified model or fall back to global default
    model_to_use = model or OLLAMA_MODEL
    
    relevant_memories = []
    memories_str = ""
    
    try:
        # Always retrieve relevant memories - increased limit from 5 to 20
        search_results = memory.search(query=message, user_id=user_id, limit=20)
        relevant_memories = search_results.get("results", [])
        
        if relevant_memories:
            logger.info(f"Found {len(relevant_memories)} relevant memories")
            memories_str = "\n".join(f"- {entry['memory']}" for entry in relevant_memories)
        else:
            logger.info("No relevant memories found")
            memories_str = "No relevant memories found."
            
        # Also get some user's recent memories regardless of relevance
        try:
            user_memories = memory.get_all(user_id=user_id, limit=5)
            if user_memories and not relevant_memories:
                logger.info(f"Using {len(user_memories)} user memories as fallback")
                memories_str = "\n".join(f"- {entry}" for entry in user_memories)
                relevant_memories = [{"memory": memory} for memory in user_memories]
        except Exception as user_mem_error:
            logger.error(f"Error retrieving user memories: {user_mem_error}")
    except Exception as e:
        logger.error(f"Error retrieving memories: {e}")
        memories_str = "Error retrieving memories, but continuing with chat."
        
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
        
        # Send chat request to Ollama with temperature and max_tokens
        result = chat_with_ollama(
            messages=messages,
            model=model_to_use,
            output_format=output_format,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Extract assistant response
        if "message" in result and "content" in result["message"]:
            assistant_response = result["message"]["content"]
        else:
            assistant_response = result.get("response", "I couldn't generate a response.")
        
        # Enhanced memory storage - store user and assistant messages separately for better retrieval
        try:
            # Process user message to make it more prominent in vector store
            enhanced_user_message = preprocess_user_message(message)
            
            # Store user message first (with clear prefix for better retrieval)
            metadata = {"active": True, "timestamp": time.time(), "type": "user_message"}
            memory.add(
                f"USER INPUT: {enhanced_user_message}",
                user_id=user_id,
                metadata=metadata
            )
            # Update memory counters
            global MEMORY_COUNTER
            MEMORY_COUNTER["active"] += 1
            MEMORY_COUNTER["total"] += 1
            logger.info(f"Successfully stored user message for {user_id}")
            
            # Then store assistant response separately (also with clear prefix)
            metadata = {"active": True, "timestamp": time.time(), "type": "assistant_response"}
            memory.add(
                f"ASSISTANT RESPONSE: {assistant_response}",
                user_id=user_id,
                metadata=metadata
            )
            # Update memory counters again
            MEMORY_COUNTER["active"] += 1
            MEMORY_COUNTER["total"] += 1
            logger.info(f"Successfully stored assistant response for {user_id}")
            
        except Exception as memory_error:
            logger.error(f"Error adding memory: {memory_error}")
            # Continue execution even if memory storage fails
        
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
