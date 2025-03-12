#!/usr/bin/env python3
"""
Main entry point for mem0 + Ollama integration

This script starts the web interface and API server for the mem0 + Ollama integration.
"""

import os
import sys
import argparse
import logging
from typing import Optional

from config import OLLAMA_HOST, OLLAMA_MODEL, QDRANT_HOST, API_PORT
from ollama_client import check_ollama
from memory_utils import check_qdrant, initialize_memory
from api import run_server

# Configure more detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Set specific module logging levels
logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask logs
logging.getLogger('ollama_client').setLevel(logging.DEBUG)  # More detailed Ollama client logs
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Start the mem0 + Ollama integration server")
    
    parser.add_argument(
        "--ollama-host", 
        type=str, 
        default=OLLAMA_HOST,
        help=f"Ollama API host (default: {OLLAMA_HOST})"
    )
    
    parser.add_argument(
        "--ollama-model", 
        type=str, 
        default=OLLAMA_MODEL,
        help=f"Ollama model to use (default: {OLLAMA_MODEL})"
    )
    
    parser.add_argument(
        "--qdrant-host", 
        type=str, 
        default=QDRANT_HOST,
        help=f"Qdrant host (default: {QDRANT_HOST})"
    )
    
    parser.add_argument(
        "--embed-model",
        type=str,
        default=None,
        help="Model to use for embeddings (defaults to ollama-model if not specified)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=API_PORT,
        help=f"Port for the API server (default: {API_PORT})"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode"
    )
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    # Override global settings with command line arguments
    if args.ollama_host != OLLAMA_HOST:
        logger.info(f"Using custom Ollama host: {args.ollama_host}")
        os.environ["OLLAMA_HOST"] = args.ollama_host
    
    if args.ollama_model != OLLAMA_MODEL:
        logger.info(f"Using custom Ollama model: {args.ollama_model}")
        os.environ["OLLAMA_MODEL"] = args.ollama_model
    
    if args.qdrant_host != QDRANT_HOST:
        logger.info(f"Using custom Qdrant host: {args.qdrant_host}")
        os.environ["QDRANT_HOST"] = args.qdrant_host
    
    # Directly test Ollama connection with request
    logger.info("Testing direct connection to Ollama...")
    try:
        import requests
        ollama_response = requests.get(f"{args.ollama_host}/api/tags", timeout=5)
        if ollama_response.status_code == 200:
            models_data = ollama_response.json()
            model_names = [model.get("name") for model in models_data.get("models", [])]
            logger.info(f"✅ Successfully connected to Ollama. Found models: {', '.join(model_names[:5])}{'...' if len(model_names) > 5 else ''}")
        else:
            logger.error(f"❌ Ollama responded with status code {ollama_response.status_code}")
    except Exception as e:
        logger.error(f"❌ Direct connection to Ollama failed: {str(e)}")
    
    # Check if Ollama is running and has the required model
    logger.info("Checking Ollama with helper function...")
    if not check_ollama():
        logger.error("Ollama check failed, but continuing.")
    else:
        logger.info("Ollama is running and ready.")
    
    # Check if Qdrant is running
    logger.info("Checking Qdrant...")
    if not check_qdrant():
        logger.error("Qdrant check failed, but continuing.")
    else:
        logger.info("Qdrant is running and ready.")
    
    # Initialize memory
    logger.info("Initializing memory system...")
    try:
        memory = initialize_memory(
            ollama_model=args.ollama_model,
            embed_model=args.embed_model
        )
        logger.info("Memory system initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize memory: {e}")
        logger.info("Memory system will be initialized when first needed.")
    
    # Start the API server
    logger.info(f"Starting API server on port {args.port}...")
    
    # Try running the server, but handle socket errors that can happen on some systems
    try:
        run_server(port=args.port, debug=args.debug)
    except OSError as e:
        logger.error(f"Failed to start server with error: {str(e)}")
        logger.info("Trying alternate host/port configuration...")
        
        # Try alternate port if the primary fails
        alternate_port = args.port + 1
        try:
            logger.info(f"Attempting to start on port {alternate_port}...")
            run_server(port=alternate_port, debug=args.debug)
        except Exception as e2:
            logger.error(f"All server start attempts failed: {str(e2)}")
            logger.info("Try running the direct_ollama_server.py script for a simplified test.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
