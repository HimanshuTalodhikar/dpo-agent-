"""CLO Agent Platform — Central configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Settings
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseSettings(BaseSettings):
    """Database connection settings.

    Supports two modes:
    1. DATABASE_URL — direct connection string (local dev / docker)
    2. DB_USERNAME + DB_PASSWORD + DB_HOST + DB_PORT + DB_NAME — individual
       fields injected from AWS Secrets Manager at runtime (production ECS).

    The url property returns a full connection string, constructing one from
    individual fields when DATABASE_URL is not set.
    """

    model_config = SettingsConfigDict(env_prefix="")

    # Direct connection string (local dev / docker-compose)
    database_url: str = Field(
        default="",
        validation_alias="DATABASE_URL",
        description="Full async database URL",
    )
    # Individual fields injected from Secrets Manager (ECS production)
    db_username: str = Field(default="", validation_alias="DB_USERNAME")
    db_password: str = Field(default="", validation_alias="DB_PASSWORD")
    db_host: str = Field(default="", validation_alias="DB_HOST")
    db_port: int = Field(default=5432, validation_alias="DB_PORT")
    db_name: str = Field(default="", validation_alias="DB_NAME")
    # Pool settings
    pool_size: int = Field(default=5, ge=1, le=50)
    max_overflow: int = Field(default=10, ge=0, le=100)
    echo: bool = Field(default=False)

    @property
    def url(self) -> str:
        """Return full async database URL.

        Prefers DATABASE_URL env var; constructs from individual Secrets Manager
        fields when running in ECS.
        """
        if self.database_url:
            return self.database_url
        if self.db_username and self.db_host:
            host = self.db_host
            port = self.db_port or 5432
            name = self.db_name or "cloagent"
            return f"postgresql+asyncpg://{self.db_username}:{self.db_password}@{host}:{port}/{name}"
        # Fallback for local dev
        return "postgresql+asyncpg://cloagent:cloagent_secret@localhost:5433/cloagent"


class BedrockSettings(BaseSettings):
    """Amazon Bedrock LLM settings."""

    model_config = SettingsConfigDict(env_prefix="BEDROCK_")

    model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v1",
        description="Bedrock model identifier",
    )
    region: str = Field(default="us-east-1")
    endpoint_url: str | None = Field(default=None)
    max_tokens: int = Field(default=4096, ge=256, le=200000)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)



class GraphitiSettings(BaseSettings):
    """Graphiti + Amazon Neptune knowledge graph settings."""

    model_config = SettingsConfigDict(env_prefix="GRAPHITI_")

    neptune_host: str = Field(
        default="neptune-db://localhost:8182",
        description="Neptune connection URL (neptune-db:// or neptune-graph://)",
    )
    aoss_host: str = Field(default="")
    aoss_port: int = Field(default=443)
    aws_region: str = Field(default="us-east-1")
    graph_name: str = Field(default="govt-knowledge-base")
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    anthropic_api_key: str = Field(default="")
    anthropic_base_url: str = Field(default="https://api.anthropic.com")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514")
    openai_api_key: str = Field(default="")


class CodemaxSettings(BaseSettings):
    """Codemax LLM provider settings."""

    model_config = SettingsConfigDict(env_prefix="CODEMAX_", env_file=".env", extra="ignore")

    api_key: str = Field(default="")
    base_url: str = Field(default="https://api.codemax.pro")
    model: str = Field(default="claude-3-5-sonnet-20241022")
    timeout: float = Field(default=120.0)
    temperature: float = Field(default=0.3)
    max_tokens: int = Field(default=4096)
    top_p: float = Field(default=0.9)

class EmbeddingSettings(BaseSettings):
    """Embedding model settings."""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")

    model_id: str = Field(default="amazon.titan-embed-text-v2")
    dimensions: int = Field(default=1024)
    region: str = Field(default="us-east-1")
    endpoint_url: str | None = Field(default=None)


class S3Settings(BaseSettings):
    """Amazon S3 settings."""

    model_config = SettingsConfigDict(env_prefix="S3_")

    bucket: str = Field(default="cloagent-documents")
    region: str = Field(default="us-east-1")
    endpoint_url: str | None = Field(default=None)


class SecuritySettings(BaseSettings):
    """Security & secrets settings."""

    model_config = SettingsConfigDict(env_prefix="")

    aws_region: str = Field(default="us-east-1")
    aws_access_key_id: str | None = Field(default=None)
    aws_secret_access_key: SecretStr | None = Field(default=None)
    kms_key_id: str | None = Field(default=None)
    secret_manager_arn: str | None = Field(default=None)


class AppSettings(BaseSettings):
    """Application-level settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = Field(default="local")
    log_level: str = Field(default="INFO")
    use_mock_llm: bool = Field(default=True)
    mock_llm_url: str = Field(default="http://localhost:8080/v1/chat/completions")

    audit_enabled: bool = Field(default=True)

    # Retrieval settings
    retrieval_top_k: int = Field(default=10, ge=1, le=100)
    rerank_enabled: bool = Field(default=False)
    rerank_top_n: int = Field(default=5, ge=1, le=50)

    # Ingestion settings
    ingest_sample_docs: bool = Field(default=False)
    max_chunk_size: int = Field(default=512)
    chunk_overlap: int = Field(default=64)

    # Database
    database: Annotated[DatabaseSettings, Field(default_factory=DatabaseSettings)]

    # Bedrock
    bedrock: Annotated[BedrockSettings, Field(default_factory=BedrockSettings)]

    # Embeddings
    embedding: Annotated[EmbeddingSettings, Field(default_factory=EmbeddingSettings)]

    # LLM via Codemax
    codemax: Annotated[CodemaxSettings, Field(default_factory=CodemaxSettings)]

    # Knowledge Graph (Graphiti + Neptune)
    graphiti: Annotated[GraphitiSettings, Field(default_factory=GraphitiSettings)]

    # S3
    s3: Annotated[S3Settings, Field(default_factory=S3Settings)]

    # Security
    security: Annotated[SecuritySettings, Field(default_factory=SecuritySettings)]

    @model_validator(mode="after")
    def validate_environment(self) -> "AppSettings":
        valid = {"local", "production", "prod", "prod-aws"}
        if self.environment not in valid:
            raise ValueError(f"ENVIRONMENT must be one of {valid}, got '{self.environment}'")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Singleton accessor
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache
def get_settings() -> AppSettings:
    """Return the global settings singleton. Caches on first call."""
    return AppSettings()
