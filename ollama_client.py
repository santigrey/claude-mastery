"""
ollama_client.py — Local inference fallback using Ollama on TheBeast.

When Anthropic API is down or overloaded, this module provides a 
drop-in compatible interface using llama3.1:8b running locally.

Architecture:
  Primary:  Anthropic Claude Sonnet (cloud)
  Fallback: Ollama llama3.1:8b on TheBeast (192.168.1.152)
"""

import json
import requests

OLLAMA_BASE_URL = "http://192.168.1.152:11434"
OLLAMA_MODEL    = "llama3.1:8b"


def is_ollama_available():
    """Check if Ollama on TheBeast is reachable."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def ollama_chat(messages, system=None, max_tokens=1024):
    """
    Send a chat request to Ollama on TheBeast.
    Returns a response object that mimics Anthropic's structure.
    """
    # Build message list
    ollama_messages = []

    if system:
        ollama_messages.append({"role": "system", "content": system})

    for msg in messages:
        if isinstance(msg["content"], str):
            ollama_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        elif isinstance(msg["content"], list):
            # Handle tool results — flatten to text for Ollama
            text_parts = []
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    text_parts.append(f"Tool result: {block.get('content', '')}")
            if text_parts:
                ollama_messages.append({
                    "role": "user",
                    "content": "\n".join(text_parts)
                })

    payload = {
        "model": OLLAMA_MODEL,
        "messages": ollama_messages,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.7
        }
    }

    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=120
    )
    r.raise_for_status()
    data = r.json()

    # Return a simple object that mimics Anthropic response structure
    return OllamaResponse(data["message"]["content"])


class OllamaResponse:
    """Mimics Anthropic message response structure for drop-in compatibility."""

    def __init__(self, text):
        self.stop_reason = "end_turn"
        self.model = OLLAMA_MODEL
        self.content = [OllamaTextBlock(text)]

    def __repr__(self):
        return f"OllamaResponse(model={self.model}, text={self.content[0].text[:50]}...)"


class OllamaTextBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


def smart_create(client, use_ollama_fallback=True, **kwargs):
    """
    Smart API call that tries Anthropic first, falls back to Ollama.
    
    Usage:
        response = smart_create(client, model="claude-sonnet-4-20250514", 
                                messages=[...], system="...")
    """
    from anthropic import _exceptions
    import time

    # Try Anthropic first
    try:
        return client.messages.create(**kwargs)

    except (_exceptions.OverloadedError, _exceptions.RateLimitError) as e:
        if not use_ollama_fallback:
            raise

        print(f"\n[FALLBACK] Anthropic overloaded — switching to Ollama on TheBeast...")

        if not is_ollama_available():
            print("[FALLBACK] Ollama not reachable either. Waiting 30s and retrying Anthropic...")
            time.sleep(30)
            return client.messages.create(**kwargs)

        return ollama_chat(
            messages=kwargs.get("messages", []),
            system=kwargs.get("system", None),
            max_tokens=kwargs.get("max_tokens", 1024)
        )


if __name__ == "__main__":
    print("Testing Ollama connection to TheBeast...")

    if is_ollama_available():
        print(f"Ollama is UP at {OLLAMA_BASE_URL}")
        response = ollama_chat(
            messages=[{"role": "user", "content": "In one sentence, what is a ReAct agent?"}],
            system="You are a senior AI engineer. Be direct and technical."
        )
        print(f"\nResponse: {response.content[0].text}")
        print(f"Stop reason: {response.stop_reason}")
    else:
        print("Ollama is NOT reachable. Check TheBeast.")
