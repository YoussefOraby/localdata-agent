from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5-coder:7b"
    FALLBACK_MODEL: str = "llama3.1:8b"
    LOG_DIR: str = "./logs"
    MAX_EXECUTION_TIMEOUT: int = 30
    MAX_CSV_SIZE_MB: int = 50


settings = Settings()
