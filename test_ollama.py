#!/usr/bin/env python3
"""
Simple script to test connection to Ollama API
"""

import argparse
import json
import logging
import requests
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_ollama_connection(host="http://localhost:11434"):
    """Test the connection to the Ollama API."""
    logger.info(f"Testing connection to Ollama at {host}")
    
    # Test the /api/tags endpoint
    try:
        logger.info("Testing /api/tags endpoint...")
        response = requests.get(f"{host}/api/tags", timeout=10)
        
        if response.status_code == 200:
            logger.info(f"✅ Connection successful (Status: {response.status_code})")
            
            # Parse the response
            try:
                data = response.json()
                models = data.get("models", [])
                
                if models:
                    logger.info(f"✅ Found {len(models)} models:")
                    for model in models:
                        name = model.get("name", "unknown")
                        size = model.get("size", 0) / (1024 * 1024)  # Convert to MB
                        parameter_size = model.get("details", {}).get("parameter_size", "unknown")
                        
                        logger.info(f"  - {name} ({parameter_size}, {size:.1f} MB)")
                else:
                    logger.warning("⚠️ No models found in Ollama. You may need to pull a model.")
                    logger.info("Tip: Run 'ollama pull llama3' to get a model")
            except json.JSONDecodeError:
                logger.error("❌ Failed to parse JSON response")
                logger.info(f"Response content: {response.text[:1000]}")
        else:
            logger.error(f"❌ Ollama API responded with status code {response.status_code}")
            logger.info(f"Response content: {response.text[:1000]}")
            
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Connection refused. Is Ollama running at {host}?")
        logger.info("Tip: Run 'ollama serve' to start the Ollama server")
        return False
    except requests.exceptions.Timeout:
        logger.error(f"❌ Connection timed out. Ollama at {host} is not responding")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False
    
    # Test a simple chat completion
    try:
        logger.info("\nTesting a simple chat request...")
        
        # Find the first available model
        available_models = []
        try:
            resp = requests.get(f"{host}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                available_models = [m.get("name") for m in models]
        except Exception:
            pass
        
        model_to_test = available_models[0] if available_models else "llama3"
        logger.info(f"Using model: {model_to_test}")
        
        payload = {
            "model": model_to_test,
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": False
        }
        
        response = requests.post(f"{host}/api/chat", json=payload, timeout=20)
        
        if response.status_code == 200:
            logger.info(f"✅ Chat request successful (Status: {response.status_code})")
            
            try:
                data = response.json()
                if "message" in data and "content" in data["message"]:
                    content = data["message"]["content"]
                    logger.info(f"✅ Got response: \"{content[:100]}...\"")
                else:
                    logger.warning("⚠️ Response format unexpected")
                    logger.info(f"Response data: {data}")
            except json.JSONDecodeError:
                logger.error("❌ Failed to parse JSON response from chat request")
        else:
            logger.error(f"❌ Chat request failed with status code {response.status_code}")
            logger.info(f"Response content: {response.text[:1000]}")
    except Exception as e:
        logger.error(f"❌ Failed to test chat: {e}")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test connection to Ollama API")
    parser.add_argument(
        "--host", 
        type=str,
        default="http://localhost:11434",
        help="Ollama API host (default: http://localhost:11434)"
    )
    
    args = parser.parse_args()
    
    logger.info("===== Ollama Connection Test =====")
    success = test_ollama_connection(args.host)
    
    if success:
        logger.info("\n✅ Ollama connection test completed. Basic functionality appears to be working.")
        logger.info("If you're still having issues with the web interface, check browser console logs for more details.")
        sys.exit(0)
    else:
        logger.error("\n❌ Ollama connection test failed. Please check if Ollama is running correctly.")
        logger.info("Try these steps:")
        logger.info("1. Run 'ollama serve' in a terminal")
        logger.info("2. Ensure you've pulled at least one model with 'ollama pull llama3'")
        logger.info("3. Check for any firewall or network issues")
        sys.exit(1)
