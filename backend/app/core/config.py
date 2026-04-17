"""
Application configuration — loaded from environment variables.

Uses pydantic-settings so all values are validated at startup.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseBackend(StrEnum):
    COUCHBASE = "couchbase"
    MEMORY = "memory"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: AppEnv = AppEnv.DEVELOPMENT
    app_secret_key: str = "dev-secret-key-change-in-production"
    log_level: str = "INFO"

    # Database backend selector
    # Defaults to "memory" in test env; "couchbase" otherwise
    @property
    def database_backend(self) -> DatabaseBackend:
        if self.app_env == AppEnv.TEST:
            return DatabaseBackend.MEMORY
        if self.couchbase_connection_string:
            return DatabaseBackend.COUCHBASE
        return DatabaseBackend.MEMORY

    # Couchbase / Capella
    couchbase_connection_string: str = ""
    couchbase_username: str = ""
    couchbase_password: str = ""
    couchbase_bucket: str = "banking-core"
    couchbase_vector_index: str = "banking-vector-index"

    # Capella AI Services
    capella_ai_endpoint: str = ""
    capella_ai_api_key: str = ""
    capella_model_id: str = "gpt-4o"
    capella_embedding_model_id: str = "text-embedding-3-small"

    # Fallback LLM (used in dev/test when Capella is not configured)
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Auth
    oidc_issuer_url: str = ""
    oidc_client_id: str = "fintech-agentic-app"
    oidc_client_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_public_key_path: str = ""
    jwt_expire_minutes: int = 60

    # Event bus
    eventing_enabled: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_transaction_topic: str = "banking.transactions"
    kafka_interaction_topic: str = "banking.interactions"

    # Observability
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "fintech-agentic-app"

    # CORS
    frontend_origin: str = "http://localhost:5173"
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == AppEnv.DEVELOPMENT

    @property
    def is_test(self) -> bool:
        return self.app_env == AppEnv.TEST

    @property
    def use_capella_ai(self) -> bool:
        return bool(self.capella_ai_endpoint and self.capella_ai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
