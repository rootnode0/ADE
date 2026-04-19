import requests
import json
import time
import re
from typing import Optional, Dict, Any
from ai_dev_env.config.manager import config

class OllamaError(Exception):
    """Base class for Ollama client errors."""
    pass

class InfrastructureError(OllamaError):
    """HTTP 500, timeouts, etc."""
    pass

class ParsingError(OllamaError):
    """Invalid JSON response."""
    pass

class EmptyResponseError(OllamaError):
    """Model returned nothing."""
    pass

def generate(model: str, prompt: str, options: Optional[Dict[str, Any]] = None, system: Optional[str] = None) -> str:
    """
    Centralized Ollama API client for /api/generate.
    Ensures stream: false and handles errors deterministically.
    """
    url = f"{config.ollama_base_url}/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,  # NON-NEGOTIABLE
    }
    
    if system:
        payload["system"] = system
    
    if options:
        payload["options"] = options
    else:
        payload["options"] = {
            "temperature": 0.0,
            "num_ctx": config.context_length,
            "num_gpu": config.gpu_layers
        }

    max_retries = 3
    backoff = 2 # seconds

    for attempt in range(1, max_retries + 1):
        try:
            start_time = time.time()
            print(f"      [OLLAMA] Requesting {model} (prompt: {len(prompt)} chars)...")
            
            response = requests.post(url, json=payload, timeout=600)
            
            # 1. Infrastructure Check
            if response.status_code != 200:
                raise InfrastructureError(f"HTTP {response.status_code}: {response.text}")
            
            # 2. Parsing Check
            try:
                data = response.json()
            except json.JSONDecodeError:
                raise ParsingError(f"Invalid JSON response: {response.text[:200]}")
            
            # 3. Response Content Check
            raw_response = data.get("response", "")
            
            # Handle reasoning models (strip <think> tags)
            raw_response = re.sub(r"<think>.*?</think>", "", raw_response, flags=re.DOTALL).strip()
            
            if not raw_response:
                raise EmptyResponseError(f"Model {model} returned an empty response.")
            
            elapsed = time.time() - start_time
            print(f"      [OLLAMA] Received {len(raw_response)} chars in {elapsed:.2f}s")
            
            return raw_response

        except (InfrastructureError, ParsingError, EmptyResponseError) as e:
            print(f"      ! Ollama Error (attempt {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                raise
            time.sleep(backoff * attempt)
        except requests.exceptions.RequestException as e:
            print(f"      ! Connection Error (attempt {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                raise InfrastructureError(f"Connection failed: {e}")
            time.sleep(backoff * attempt)

    raise InfrastructureError("Unknown error in Ollama client.")
