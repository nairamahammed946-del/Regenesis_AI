import os
import secrets
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "ReGenesis AI"
    APP_VERSION: str = "2.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    SEED_DEMO_DATA: bool = True
    DEMO_MODE: bool = True

    # A random development key is safer than a committed predictable key.
    # Set SECRET_KEY in .env for stable tokens and all deployments.
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(48), min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24, ge=5, le=60 * 24 * 30)

    USE_SQLITE: bool = True
    SQLITE_DB_PATH: str = "regenesis_v2.db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "regenesis_ai"
    DATABASE_URL: Optional[str] = None

    @property
    def SYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            return url.replace("postgresql+asyncpg://", "postgresql://").replace("sqlite+aiosqlite:///", "sqlite:///")
        if self.USE_SQLITE:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(base_dir, self.SQLITE_DB_PATH).replace("\\", "/")
            return f"sqlite:///{db_path}"
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
    MAX_UPLOAD_SIZE: int = Field(default=50 * 1024 * 1024, ge=1024, le=500 * 1024 * 1024)
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp", "image/bmp"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"]
    CORS_ORIGINS: List[str] = ["http://127.0.0.1:8000", "http://localhost:8000"]
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Optional live web search (Tavily or Brave). Keep secrets in environment variables.
    WEB_SEARCH_ENABLED: bool = False
    WEB_SEARCH_PROVIDER: str = "tavily"
    TAVILY_API_KEY: Optional[str] = None
    BRAVE_SEARCH_API_KEY: Optional[str] = None
    WEB_SEARCH_TIMEOUT_SECONDS: int = Field(default=12, ge=3, le=60)

    # Free local LLM through Ollama (no cloud API key required)
    OLLAMA_ENABLED: bool = True
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen3:4b"
    OLLAMA_VISION_MODEL: str = "qwen2.5vl:3b"
    OLLAMA_TIMEOUT_SECONDS: int = Field(default=120, ge=10, le=600)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True, enable_decoding=False, env_ignore_empty=True)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                import json
                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

settings = Settings()
