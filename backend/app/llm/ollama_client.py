import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.LLM_MODEL
        self.fallback_model = settings.FALLBACK_MODEL
        self._client: Optional["ollama.Client"] = None

    def _get_client(self):
        if self._client is None:
            try:
                import ollama
                self._client = ollama.Client(host=self.base_url)
            except ImportError:
                logger.warning("ollama package not installed")
                return None
        return self._client

    def is_available(self) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            client.list()
            return True
        except Exception as e:
            logger.debug("Ollama not available: %s", e)
            return False

    def get_model_name(self) -> str:
        return self.model

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        client = self._get_client()
        if client is None:
            return "Error: Ollama client is not available (package not installed)."

        models_to_try = [self.model, self.fallback_model]
        last_error = ""

        for model in models_to_try:
            try:
                options = {}
                if system_prompt:
                    options["system"] = system_prompt

                response = client.generate(model=model, prompt=prompt, options=options)
                return response.get("response", "")
            except Exception as e:
                last_error = str(e)
                logger.warning("Ollama generation failed with model %s: %s", model, e)
                if model == self.fallback_model:
                    break

        return f"Error: Ollama generation failed. {last_error}"
