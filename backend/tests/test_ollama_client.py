from unittest.mock import patch

import pytest

from app.config import settings
from app.llm.ollama_client import OllamaClient


def test_client_initializes_from_settings():
    client = OllamaClient()
    assert client.base_url == settings.OLLAMA_BASE_URL
    assert client.model == settings.LLM_MODEL
    assert client.fallback_model == settings.FALLBACK_MODEL


def test_get_model_name():
    client = OllamaClient()
    assert client.get_model_name() == settings.LLM_MODEL


@patch("app.llm.ollama_client.OllamaClient._get_client")
def test_is_available_returns_false_when_ollama_not_running(mock_get_client):
    mock_get_client.return_value = None
    client = OllamaClient()
    assert client.is_available() is False


@patch("app.llm.ollama_client.OllamaClient._get_client")
def test_generate_returns_error_when_ollama_not_available(mock_get_client):
    mock_get_client.return_value = None
    client = OllamaClient()
    result = client.generate("test prompt")
    assert "Error" in result
    assert "not available" in result.lower()


def test_generate_fallback_on_failure():
    from unittest.mock import MagicMock

    mock_instance = MagicMock()
    mock_instance.generate.side_effect = [
        Exception("Model not found"),
        {"response": "fallback response"},
    ]

    client = OllamaClient()
    client.model = "nonexistent-model"
    client.fallback_model = "working-model"
    client._client = mock_instance

    result = client.generate("hello")
    assert result == "fallback response"


def test_generate_returns_error_when_both_models_fail():
    from unittest.mock import MagicMock

    mock_instance = MagicMock()
    mock_instance.generate.side_effect = Exception("All models failed")

    client = OllamaClient()
    client.model = "bad-model"
    client.fallback_model = "also-bad"
    client._client = mock_instance

    result = client.generate("hello")
    assert "Error" in result
    assert "All models failed" in result
