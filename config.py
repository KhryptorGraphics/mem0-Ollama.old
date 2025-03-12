"""
Configuration settings for mem0 + Ollama integration
"""

from typing import Dict, Any, Optional

# Configuration defaults
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3"  # Default model
QDRANT_HOST = "http://localhost:6333"
QDRANT_COLLECTION = "ollama_memories"
API_PORT = 8000  # Default port for API server

# Models with their embedding dimensions
MODEL_DIMENSIONS = {
    "llama3": 4096,
    "mistral": 4096,
    "gemma": 4096,
    "phi3": 2560,
    "qwen2": 4096,
    "nomic-embed-text": 768,
    "snowflake-arctic-embed": 1024,
    "all-minilm": 384,
    "llava": 4096
}

# Structured output formats
OUTPUT_FORMAT = None  # Default is None (no structured output)
OUTPUT_FORMATS = {
    "none": None,
    "json": "json",
    "sentiment": {
        "type": "object",
        "properties": {
            "sentiment": {
                "type": "string",
                "enum": ["positive", "neutral", "negative"]
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },
            "explanation": {
                "type": "string"
            }
        },
        "required": ["sentiment", "confidence", "explanation"]
    },
    "summary": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string"
            },
            "key_points": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        "required": ["summary", "key_points"]
    },
    "action_items": {
        "type": "object",
        "properties": {
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"]
                        }
                    },
                    "required": ["action", "priority"]
                }
            }
        },
        "required": ["action_items"]
    }
}
