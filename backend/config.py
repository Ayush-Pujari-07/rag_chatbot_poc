import os
from typing import Any

from pydantic import SecretStr


class Config:
    # Development-specific settings
    DEBUG: bool = True
    ENVIRONMENT: str = "DEV"

    APP_VERSION: str = "0.1.0"
    PROJECT_NAME: str = "RAG_ChatBot_PoC"
    SITE_DOMAIN: str = "localhost"

    # MongoDB URI
    MONGODB_URI: str | None = os.environ.get("MONGODB_URI")

    # Redis settings
    REDIS_HOST: str = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.environ.get("REDIS_PORT", 6379))

    # CORS settings
    CORS_ORIGINS: list[str] = ["*"]
    CORS_HEADERS: list[str] = ["*"]

    # OpenAI API Key
    OPENAI_API_KEY: SecretStr | None = SecretStr(os.environ.get("OPENAI_API_KEY", ""))


settings = Config()

# Application configurations
app_configs: dict[str, Any] = {"title": "App API"}
