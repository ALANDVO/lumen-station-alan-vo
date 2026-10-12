"""Application configuration and environment settings."""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import secrets


class Settings(BaseSettings):
    """Runtime settings for Lumen Station."""

    app_name: str = "Lumen Station"
    app_version: str = "1.0.0"
    host: str = "127.0.0.1"
    port: int = 8000
    environment: str = Field(default="development", alias="ENVIRONMENT")
    demo_mode: bool = Field(default=True, alias="DEMO_MODE")
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), alias="SECRET_KEY")
    database_path: str = Field(default="lumen_station.db", alias="DATABASE_PATH")

    # OIDC Configuration
    oidc_enabled: bool = Field(default=False, alias="OIDC_ENABLED")
    oidc_issuer_url: str = Field(default="", alias="OIDC_ISSUER_URL")
    oidc_client_id: str = Field(default="lumen-station", alias="OIDC_CLIENT_ID")
    oidc_client_secret: str = Field(default="", alias="OIDC_CLIENT_SECRET")
    oidc_redirect_uri: str = Field(default="http://127.0.0.1:8000/api/auth/callback", alias="OIDC_REDIRECT_URI")

    # LLM Settings (Keys only server-side, never exposed to clients)
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_provider: str = Field(default="openai-compatible", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")

    # Sandbox & Watchdog Defaults
    default_execution_timeout: int = Field(default=30, alias="DEFAULT_EXECUTION_TIMEOUT")
    max_chunk_bytes: int = Field(default=65536, alias="MAX_CHUNK_BYTES")
    max_output_bytes: int = Field(default=5242880, alias="MAX_OUTPUT_BYTES")

    @field_validator("demo_mode")
    @classmethod
    def validate_demo_mode_refusal(cls, value: bool, info) -> bool:
        env = info.data.get("environment", "development").lower()
        if env in {"production", "prod"} and value:
            raise ValueError("Startup refused: Demo mode cannot be enabled in production environments.")
        return value

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
