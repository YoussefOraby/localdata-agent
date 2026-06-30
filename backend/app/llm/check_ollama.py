#!/usr/bin/env python3
"""Check if Ollama is available and print model info."""

from app.llm.ollama_client import OllamaClient


def main():
    client = OllamaClient()
    available = client.is_available()
    model = client.get_model_name()

    print(f"Ollama base URL: {client.base_url}")
    print(f"Primary model: {model}")
    print(f"Fallback model: {client.fallback_model}")
    print(f"Available: {available}")

    if available:
        print("✓ Ollama is running and reachable.")
    else:
        print("✗ Ollama is not available.")
        print("  Make sure Ollama is installed and running:")
        print("  https://ollama.com/download")
        print(f"  Then pull the model: ollama pull {model}")


if __name__ == "__main__":
    main()
