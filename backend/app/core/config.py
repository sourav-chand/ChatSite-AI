"""Centralized typed configuration via pydantic-settings + python-decouple."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from decouple import config as env
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    ENVIRONMENT: str = Field(default="dev")
    DEBUG: bool = Field(default=True)
    SECRET_KEY: str = Field(default="change-me")
    FRONTEND_URL: str = Field(default="http://localhost:4200")
    WIDGET_CDN_URL: str = Field(default="http://localhost:8000")

    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    QDRANT_URL: str
    QDRANT_API_KEY: str = ""

    OPENAI_API_KEY: str
    OPENAI_MODEL_CHAT: str = "gpt-4o"
    OPENAI_MODEL_EMBED: str = "text-embedding-3-small"
    GOOGLE_API_KEY: str = ""
    GOOGLE_MODEL_CHAT: str = "gemini-2.0-flash"

    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TTL_MIN: int = 15
    JWT_REFRESH_TTL_DAYS: int = 7
    JWT_PRIVATE_KEY_PATH: str = "./keys/jwt_private.pem"
    JWT_PUBLIC_KEY_PATH: str = "./keys/jwt_public.pem"
    JWT_ISSUER: str = "chatsite.ai"
    JWT_AUDIENCE: str = "chatsite-api"

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""

    EMAIL_HOST: str = "smtp.sendgrid.net"
    EMAIL_PORT: int = 587
    EMAIL_USER: str = "apikey"
    EMAIL_PASSWORD: str = ""
    EMAIL_FROM: str = "no-reply@chatsite.ai"

    CORS_ORIGINS: str = "http://localhost:4200"

    CRAWL_MAX_DEPTH: int = 4
    CRAWL_CONCURRENCY: int = 5
    CRAWL_REQUEST_DELAY: float = 1.0
    CRAWL_USER_AGENT: str = "ChatSiteBot/1.0"
    CRAWL_TIMEOUT_SEC: int = 20

    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    CHUNKING_STRATEGY: str = "recursive"

    RAG_TOP_K: int = 8
    RAG_SCORE_THRESHOLD: float = 0.72
    RAG_RERANK_TOP_K: int = 4
    RAG_MAX_QUERY_LEN: int = 500
    RAG_LLM_MAX_TOKENS: int = 800
    RAG_LLM_TEMPERATURE: float = 0.3
    RAG_HISTORY_TURNS: int = 6
    RAG_CONTEXT_TOKEN_LIMIT: int = 2000

    RATE_LIMIT_AUTH: str = "5/minute"
    RATE_LIMIT_CHAT: str = "30/minute"
    RATE_LIMIT_API: str = "60/minute"

    WIDGET_VERSION: str = "1.0.0"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
