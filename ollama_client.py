"""
Ollama API client functions for mem0 + Ollama integration
"""

import requests
import logging
from typing import List, Dict, Any, Optional, Union

from config import OLLAMA_HOST, OLLAMA_MODEL

logger = logging.getLogger(__name__)

def get_available_models() -> List[Dict[str, Any]]:
    """Get available models from Ollama."""
    try:
        logger.info(f"Attempting to fetch models from {OLLAMA_HOST}/api/tags")
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Failed to get models: Status {response.status_code}, Response: {response.text}")
            return []
        
        logger.info(f"Received response from Ollama API: {response.status_code}")
        data = response.json()
        logger.info(f"Response data: {data}")
        
        models = data.get("models", [])
        logger.info(f"Retrieved {len(models)} models from Ollama: {[m.get('name') for m in models]}")
        
        model_details = []
        for model in models:
            name = model.get("name")
            # Extract details or provide defaults
            parameter_size = model.get("details", {}).get("parameter_size", "unknown")
            quantization = model.get("details", {}).get("quantization_level", "unknown") 
            families = model.get("details", {}).get("families", [])
            
            # Create model info object
            details = {
                "id": name,
                "name": name,
                "size": model.get("size", 0),
                "parameter_size": parameter_size,
                "quantization": quantization,
                "families": families,
                # Add raw model data for better compatibility
                "raw_model": model
            }
            model_details.append(details)
            logger.info(f"Added model: {name}")
        
        return model_details
    except requests.RequestException as e:
        logger.error(f"Request error while fetching models: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error while fetching models: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def check_ollama() -> bool:
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

def chat_with_ollama(
    messages: List[Dict[str, str]], 
    model: str = OLLAMA_MODEL,
    output_format: Optional[Union[str, Dict]] = None
) -> Dict[str, Any]:
    """
    Send a chat request to Ollama's API.
    
    Args:
        messages: List of message objects (role, content)
        model: Model to use for chat
        output_format: Optional format for structured output
    
    Returns:
        Dict with the Ollama API response
    """
    # Prepare request payload
    request_payload = {
        "model": model,
        "stream": False,
        "options": {
            "temperature": 0.7
        },
        "messages": messages
    }
    
    # Add format for structured output if specified
    if output_format:
        request_payload["format"] = output_format
        logger.info(f"Using structured output format: {output_format if isinstance(output_format, str) else 'custom JSON schema'}")
    
    api_url = f"{OLLAMA_HOST}/api/chat"
    
    # Make the API request
    logger.info(f"Sending request to Ollama API: {api_url}")
    
    try:
        response = requests.post(api_url, json=request_payload)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.RequestException as e:
        logger.error(f"Error making request to Ollama API: {e}")
        raise
