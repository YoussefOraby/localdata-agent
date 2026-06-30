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
        print("[OK] Ollama is running and reachable.")
        print()
        try:
            import ollama
            ollama_client = ollama.Client(host=client.base_url)
            models = ollama_client.list()
            local_models = models.get("models", [])
            if local_models:
                print(f"Available local models ({len(local_models)}):")
                for m in local_models:
                    name = m.get("name", m.get("model", "?"))
                    print(f"  - {name}")
            else:
                print("No models pulled yet. Run:")
                print(f"  ollama pull {model}")
                print(f"  ollama pull {client.fallback_model}")
        except Exception:
            print("Could not list models.")
    else:
        print("[FAIL] Ollama is not available.")
        print()
        print("  Make sure Ollama is installed and running:")
        print("  https://ollama.com/download")
        print()
        print("  Then pull the recommended models:")
        print(f"    ollama pull {model}")
        print(f"    ollama pull {client.fallback_model}")
        print()
        print("  To verify installation:")
        print("    ollama list")


if __name__ == "__main__":
    main()
